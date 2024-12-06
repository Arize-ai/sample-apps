# src/llamaindex_app/verify_setup.py
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_setup():
    # Check .env file
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY not found in .env file")
        return False
    if not api_key.startswith("sk-"):
        logger.error(
            "❌ OPENAI_API_KEY appears to be invalid (should start with 'sk-')"
        )
        return False
    logger.info("✅ OpenAI API key found")

    # Check data directory
    data_path = Path("data")
    if not data_path.exists():
        logger.error("❌ 'data' directory not found")
        return False
    if not any(data_path.iterdir()):
        logger.error("❌ No files found in 'data' directory")
        return False
    logger.info(
        f"✅ Found files in data directory: {[f.name for f in data_path.iterdir()]}"
    )

    # Check storage directory
    storage_path = Path("storage")
    if not storage_path.exists():
        storage_path.mkdir(parents=True)
        logger.info("✅ Created 'storage' directory")
    else:
        logger.info("✅ 'storage' directory exists")

    return True


if __name__ == "__main__":
    if verify_setup():
        logger.info("✅ All checks passed! You can now run the main application.")
    else:
        logger.error(
            "❌ Please fix the above issues before running the main application."
        )
