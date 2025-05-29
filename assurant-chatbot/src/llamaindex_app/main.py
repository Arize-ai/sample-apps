from src.llamaindex_app.index_manager import IndexManager
from src.llamaindex_app.classifier import QueryClassifier, QueryCategory
from src.llamaindex_app.config import Settings
from src.llamaindex_app.config import validate_query_for_jailbreak, validate_query_for_toxic_language

import logging
import sys
import uuid
from typing import Tuple, Optional
from llama_index.core import Response
# guards
from src.llamaindex_app.config import (
    validate_query_for_jailbreak, 
    validate_query_for_toxic_language
)

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
        jailbreak_check = validate_query_for_jailbreak(query)
        toxic_check = validate_query_for_toxic_language(query)
        
        if jailbreak_check == False:
            logger.warning(f"Interaction validation failed: Potential jailbreak attempt detected")
            return "Potential jailbreak attempt detected"
        if toxic_check == False:
            logger.warning(f"Interaction validation failed: Toxic language is not allowed")
            return "Toxic language is not allowed"
            # If both validations pass, return None (no error)
            return None
    
    except Exception as e:
        # Log the specific validation error
        logger.warning(f"Interaction validation failed: {str(e)}")
        return "Input validation failed"

def process_interaction(
    query_engine: any,
    classifier: QueryClassifier,
    query: str,
    session_id: str,
) -> Tuple[Optional[Response], Optional[str]]:
    # Validate the interaction first

        try:
            validation_error = validate_interaction(query)
            if validation_error:
                return None, validation_error
            category, confidence = classifier.classify_query(query)
            

            response = classifier.get_response(query, category)

            return response, None

        except Exception as e:
            logger.error(f"Error processing query in session {session_id}: {str(e)}")
            return None, str(e)


def handle_session(query_engine: any, classifier: QueryClassifier) -> bool:
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
            query_engine, classifier, query, session_id
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


def init_openai_client():
    """Initialize the OpenAI client with API key."""
    from openai import OpenAI
    from src.llamaindex_app.config import Settings
    
    settings = Settings()
    
    # Check for required setting
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in environment variables")
    
    logger.info("Initializing OpenAI client")
    
    client_kwargs = {
        "api_key": settings.OPENAI_API_KEY,
    }
    
    # Add optional organization ID if provided
    if settings.OPENAI_ORG_ID:
        client_kwargs["organization"] = settings.OPENAI_ORG_ID
        
    # Add custom base URL if provided
    if settings.OPENAI_BASE_URL:
        client_kwargs["base_url"] = settings.OPENAI_BASE_URL
    
    try:
        client = OpenAI(**client_kwargs)
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        raise ValueError(f"OpenAI client initialization failed: {str(e)}")


def main():
    try:

        logger.info("Instrumentation initialized successfully")

        # Initialize OpenAI client
        openai_client = init_openai_client()
        logger.info("OpenAI client initialized successfully")
        
        # Settings for the application
        settings = Settings()
        
        # Initialize index manager with OpenAI client
        index_manager = IndexManager(openai_client=openai_client)
        query_engine = index_manager.get_query_engine()

        # Initialize classifier with OpenAI client
        classifier = QueryClassifier(
            query_engine=query_engine,
            openai_client=openai_client
        )

        print("\nWelcome to the Assurant 10-K Analysis & Risk Assessment Expert App!")

        while True:
            should_continue = handle_session(query_engine, classifier)
            if not should_continue:
                print("\nGoodbye!")
                break

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
