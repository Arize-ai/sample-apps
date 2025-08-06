import os
import nltk
from guardrails import Guard
from guardrails.hub import RestrictToTopic, ArizeDatasetEmbeddings, DetectPII

# Set NLTK data path for Cloud Run
nltk_data_path = os.environ.get("NLTK_DATA", "/opt/nltk_data")
if nltk_data_path not in nltk.data.path:
    nltk.data.path.insert(0, nltk_data_path)


# Ensure NLTK data is available
def ensure_nltk_data():
    """Ensure required NLTK data is downloaded"""
    try:
        # Try to use the tokenizer to see if data is available
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        print("NLTK punkt_tab data not found. Downloading...")
        try:
            nltk.download("punkt_tab", quiet=True)
            print("NLTK punkt_tab data downloaded successfully!")
        except Exception as e:
            print(f"Failed to download punkt_tab, trying punkt: {e}")
            try:
                nltk.download("punkt", quiet=True)
                print("NLTK punkt data downloaded successfully!")
            except Exception as e2:
                print(f"Failed to download NLTK data: {e2}")
                raise


# Download NLTK data if needed
ensure_nltk_data()


def return_failure_message(value, fail_result):
    return "Sorry, I can't help with that."


# First guard: Restrict to topic
topic_guard = Guard()
topic_guard.name = "restrict_to_topic"
topic_guard.use(
    RestrictToTopic(
        valid_topics=["finance"],
        invalid_topis=["cooking", "food"],
        disable_classifier=True,
        disable_llm=False,
        llm_callable="gpt-4o",
        on_fail=return_failure_message,
    )
)

# Third guard: Dataset embeddings validation
embeddings_guard = Guard()
embeddings_guard.name = "dataset_embeddings_guard"
embeddings_guard.use(
    ArizeDatasetEmbeddings(
        on_fail=return_failure_message,
        threshold=0.3,
    )
)

# Fourth guard: PII detection
pii_guard = Guard()
pii_guard.name = "pii_detection_guard"
pii_guard.use(
    DetectPII(
        on_fail=return_failure_message,
        pii_entities=[
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "US_SSN",
            "US_BANK_NUMBER",
            "CREDIT_CARD",
            "US_ITIN",
        ],
    )
)
