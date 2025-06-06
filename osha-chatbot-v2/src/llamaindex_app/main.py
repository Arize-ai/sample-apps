from .index_manager import IndexManager
from .instrumentation import setup_instrumentation
from .classifier import QueryClassifier, QueryCategory
from .config import Settings
import logging
import sys
import uuid
from typing import Tuple, Optional
from opentelemetry.trace.status import Status, StatusCode
from openinference.semconv.trace import SpanAttributes
from llama_index.core import Response
#guards
from .config import (
    validate_query_for_jailbreak, 
    validate_query_for_toxic_language
)
from guardrails import Guard
from guardrails.hub import DetectJailbreak, ToxicLanguage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)
def validate_interaction(query: str) -> Optional[str]:
    """
    Validate the user query for potential issues before processing
    
    :param query: Input query to validate
    :return: Error message if validation fails, None if query is valid
    """
    try:
        # Jailbreak detection
        jailbreak_guard = Guard().use(DetectJailbreak)
        jailbreak_guard.validate(query)
        
        # Toxic language detection
        toxic_guard = Guard().use(
            ToxicLanguage, 
            threshold=0.5,  # Adjust sensitivity as needed
            validation_method="sentence", 
            on_fail="exception"
        )
        toxic_guard.validate(query)
        
        # If both validations pass, return None (no error)
        return None
    
    except Exception as e:
        # Log the specific validation error
        logger.warning(f"Interaction validation failed: {str(e)}")
        
        # Return a generic error message
        if "jailbreak" in str(e).lower():
            return "Potential jailbreak attempt detected"
        elif "toxic" in str(e).lower():
            return "Toxic language is not allowed"
        else:
            return "Input validation failed"

def process_interaction(
    query_engine: any,
    classifier: QueryClassifier,
    tracer: any,
    query: str,
    session_id: str,
) -> Tuple[Optional[Response], Optional[str]]:
    # Validate the interaction first
    validation_error = validate_interaction(query)
    if validation_error:
        return None, validation_error

    # Continue with existing processing logic if validation passes
    with tracer.start_as_current_span(
        name="user_interaction",
        attributes={
            SpanAttributes.OPENINFERENCE_SPAN_KIND: "CHAIN",
            SpanAttributes.SESSION_ID: session_id,
            SpanAttributes.INPUT_VALUE: query,
        },
    ) as interaction_span:
        try:
            category, confidence = classifier.classify_query(query, interaction_span)
            interaction_span.set_attribute("query.category", category.value)
            interaction_span.set_attribute("classification.confidence", confidence)

            response = classifier.get_response(query, category, interaction_span)

            interaction_span.set_status(Status(StatusCode.OK))
            interaction_span.set_attribute(
                SpanAttributes.OUTPUT_VALUE, str(response.response)
            )
            interaction_span.set_attribute(
                "response_length", len(str(response.response))
            )

            if category == QueryCategory.ASSURANT_10K and response.source_nodes:
                interaction_span.set_attribute(
                    "source_count", len(response.source_nodes)
                )

            return response, None

        except Exception as e:
            logger.error(f"Error processing query in session {session_id}: {str(e)}")
            interaction_span.set_status(Status(StatusCode.ERROR))
            interaction_span.record_exception(e)
            return None, str(e)


def handle_session(query_engine: any, classifier: QueryClassifier, tracer: any) -> bool:
    session_id = str(uuid.uuid4())
    logger.info(f"Starting new session {session_id}")

    print(
        "\nWelcome! I'm here to help with questions about Assurant's recent 10-K reports and risk assessment."
    )
    print("\nAvailable commands:")
    print("- 'end': Conclude current session")
    print("- 'quit': Exit the application")
    print("- Any other input will be processed as a question\n")

    while True:
        query = input("\nEnter your question: ").strip()

        if query.lower() == "quit":
            logger.info(f"Quitting application from session {session_id}")
            return False

        elif query.lower() == "end":
            logger.info(f"Ending session {session_id}")
            print("\nSession concluded. Starting new session...\n")
            return True

        if not query:
            continue

        response, error = process_interaction(
            query_engine, classifier, tracer, query, session_id
        )

        if error:
            print(f"\nError: {error}")
        else:
            print("\nResponse:", response.response)
            if getattr(response, "source_nodes", None):
                print("\nSources:")
                for node in response.source_nodes:
                    print(f"- {node.metadata.get('file_name', 'Unknown source')}")
            print()


def init_azure_openai_client():
    """Initialize the Azure OpenAI client with DefaultAzureCredential."""
    from openai import AzureOpenAI
    from azure.identity import DefaultAzureCredential
    from .config import Settings
    
    settings = Settings()
    
    # Check for required settings
    if not settings.AZURE_OPENAI_ENDPOINT:
        raise ValueError("AZURE_OPENAI_ENDPOINT is not set in environment variables")
        
    if not settings.AZURE_OPENAI_API_VERSION:
        raise ValueError("AZURE_OPENAI_API_VERSION is not set in environment variables")
    
    if not settings.AZURE_OPENAI_DEPLOYMENT:
        raise ValueError("AZURE_OPENAI_DEPLOYMENT is not set in environment variables")
    
    logger.info("Initializing Azure OpenAI client with DefaultAzureCredential")
    
    # Try to use API key if available
    if settings.AZURE_OPENAI_API_KEY:
        logger.info("Using API key authentication for Azure OpenAI")
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION
        )
    else:
        # Use DefaultAzureCredential
        logger.info("Using DefaultAzureCredential for Azure OpenAI")
        try:
            default_credential = DefaultAzureCredential()
            client = AzureOpenAI(
                azure_ad_token_provider=default_credential.get_token("https://cognitiveservices.azure.com/.default").token,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION
            )
        except Exception as e:
            logger.error(f"Failed to authenticate with DefaultAzureCredential: {str(e)}")
            raise ValueError(
                "Authentication failed. Either provide AZURE_OPENAI_API_KEY or ensure "
                "your VPN/corporate network has proper Azure AD credentials configured."
            )
    
    return client


def main():
    try:
        tracer_provider = setup_instrumentation()
        tracer = tracer_provider.get_tracer("llamaindex_app")
        logger.info("Instrumentation initialized successfully")

        # Initialize Azure OpenAI client
        azure_client = init_azure_openai_client()
        logger.info("Azure OpenAI client initialized successfully")
        
        # Settings for the application
        settings = Settings()
        
        # Initialize index manager with Azure client
        index_manager = IndexManager(openai_client=azure_client)
        query_engine = index_manager.get_query_engine()

        # Initialize classifier with Azure client
        classifier = QueryClassifier(
            query_engine=query_engine,
            openai_client=azure_client,
            deployment=settings.AZURE_OPENAI_DEPLOYMENT
        )

        print("\nWelcome to the Assurant 10-K Analysis & Risk Assessment Expert App!")

        while True:
            should_continue = handle_session(query_engine, classifier, tracer)
            if not should_continue:
                print("\nGoodbye!")
                break

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()