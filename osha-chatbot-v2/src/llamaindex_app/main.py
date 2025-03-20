from .index_manager import IndexManager
from .instrumentation import setup_instrumentation
from .classifier import QueryClassifier, QueryCategory
from .config import BedrockModels
from llama_index.core import Response
import logging
import sys
import uuid
from typing import Tuple, Optional
from opentelemetry.trace.status import Status, StatusCode
from openinference.semconv.trace import SpanAttributes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def process_interaction(
    query_engine: any,
    classifier: QueryClassifier,
    tracer: any,
    query: str,
    session_id: str,
) -> Tuple[Optional[Response], Optional[str]]:
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

            if category == QueryCategory.OSHA and response.source_nodes:
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
        "\nWelcome! I'm here to help with business risk assessment and OSHA-related questions."
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


def init_bedrock_client():
    import os
    import boto3

    session = boto3.Session(
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.environ["AWS_SESSION_TOKEN"],
        region_name=os.environ["AWS_REGION"],
    )
    return session.client("bedrock-runtime")


def main():
    try:
        tracer_provider = setup_instrumentation()
        tracer = tracer_provider.get_tracer("llamaindex_app")
        logger.info("Instrumentation initialized successfully")

        bedrock_client = init_bedrock_client()
        index_manager = IndexManager(bedrock_client=bedrock_client)
        query_engine = index_manager.get_query_engine()

        model = BedrockModels.CLAUDE.value
        classifier = QueryClassifier(
            query_engine=query_engine,
            bedrock_client=bedrock_client,
            model=model,
        )

        print("\nWelcome to the OSHA + Business Risk Assessment Expert App!")

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
