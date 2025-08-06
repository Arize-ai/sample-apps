#!/usr/bin/env python3
"""
Simple startup script for the GuardRails server
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the server"""
    try:
        # Check if OPENAI_API_KEY is set
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY environment variable is not set!")
            logger.error(
                "Please set your OpenAI API key: export OPENAI_API_KEY=your-api-key"
            )
            sys.exit(1)

        # Import and run the server
        from server import app
        import uvicorn

        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", 8000))

        logger.info(f"Starting GuardRails server on {host}:{port}")
        logger.info("Available endpoints:")
        logger.info(f"  - Root: http://{host}:{port}/")
        logger.info(f"  - Guards list: http://{host}:{port}/guards")
        logger.info(f"  - Health check: http://{host}:{port}/health")
        logger.info("Guard endpoints:")
        logger.info(
            f"  - Gibberish Guard: http://{host}:{port}/guards/gibberish_guard/openai/v1/chat/completions"
        )
        logger.info(
            f"  - Topic Guard: http://{host}:{port}/guards/restrict_to_topic/openai/v1/chat/completions"
        )
        logger.info(
            f"  - Embeddings Guard: http://{host}:{port}/guards/dataset_embeddings_guard/openai/v1/chat/completions"
        )
        logger.info(
            f"  - PII Guard: http://{host}:{port}/guards/pii_detection_guard/openai/v1/chat/completions"
        )

        uvicorn.run(app, host=host, port=port, log_level="info")

    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(
            "Please install the required dependencies: pip install -r requirements.txt"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
