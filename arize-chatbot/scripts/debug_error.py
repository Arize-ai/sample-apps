#!/usr/bin/env python3
"""Debug script to identify the ARIZE error"""

import sys
import logging
import traceback
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def test_query_processing():
    """Test the query processing to identify where the ARIZE error occurs"""
    try:
        # Import after setting up the path
        from src.llamaindex_app.main import init_openai_client
        from src.llamaindex_app.index_manager import IndexManager
        from src.llamaindex_app.classifier import QueryClassifier
        from src.llamaindex_app.instrumentation import setup_instrumentation
        from src.llamaindex_app.config import Settings

        logger.info("Starting debug test...")

        settings = Settings()

        # Initialize instrumentation
        tracer_provider = setup_instrumentation()
        tracer = tracer_provider.get_tracer("debug_test")

        # Initialize OpenAI client
        logger.info("Initializing OpenAI client...")
        openai_client = init_openai_client()

        # Initialize index manager
        logger.info("Initializing index manager...")
        index_manager = IndexManager(openai_client=openai_client)
        query_engine = index_manager.get_query_engine()

        # Initialize classifier
        logger.info("Initializing classifier...")
        classifier = QueryClassifier(
            query_engine=query_engine, openai_client=openai_client
        )

        # Test query
        test_query = "What is Arize?"
        logger.info(f"Testing with query: {test_query}")

        # Test classification
        with tracer.start_as_current_span("test_classification") as span:
            try:
                category, confidence = classifier.classify_query(test_query, span)
                logger.info(
                    f"Classification result: {category.value} (confidence: {confidence})"
                )
            except Exception as e:
                logger.error(f"Classification error: {type(e).__name__}: {str(e)}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                raise

        # Test response generation
        with tracer.start_as_current_span("test_response") as span:
            try:
                response = classifier.get_response(test_query, category, span)
                logger.info(
                    f"Response generated successfully: {response.response[:100]}..."
                )
            except Exception as e:
                logger.error(f"Response generation error: {type(e).__name__}: {str(e)}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")

                # Check if this is where we get "ARIZE"
                if str(e) == "ARIZE":
                    logger.error("Found the ARIZE error!")
                    logger.error(f"Exception type: {type(e)}")
                    logger.error(f"Exception args: {e.args}")
                raise

    except Exception as e:
        logger.error(f"Test failed with error: {type(e).__name__}: {str(e)}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")

        # Additional debugging for the specific ARIZE error
        if str(e) == "ARIZE":
            logger.error("=== ARIZE ERROR DEBUG INFO ===")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception module: {type(e).__module__}")
            logger.error(f"Exception args: {e.args}")
            logger.error(f"Exception attributes: {dir(e)}")

            # Try to get more context
            if hasattr(e, "__cause__"):
                logger.error(f"Caused by: {e.__cause__}")
            if hasattr(e, "__context__"):
                logger.error(f"Context: {e.__context__}")


if __name__ == "__main__":
    test_query_processing()
