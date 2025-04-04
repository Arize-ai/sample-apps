from pydantic_settings import BaseSettings
from pathlib import Path
from enum import Enum
from typing import Optional


class AzureOpenAIModels(str, Enum):
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_35_TURBO = "gpt-35-turbo"


TEMPLATE_VERSION = "1.0.0"

CLASSIFICATION_PROMPT = """You are a query classifier for Assurant's 10-K reports and risk assessment application. 
Analyze the following query and respond with a JSON object containing two fields:
1. 'category': Must be exactly one of: "assurant_10k", "risk_assessment", or "out_of_scope"
2. 'confidence': A number between 0 and 1 indicating your confidence in the classification

Guidelines:
- assurant_10k: Questions about information in Assurant's recent 10-K reports, including financial data, business operations, market position, corporate governance, or risk factors
- risk_assessment: Queries about business risk scoring, risk profiles, historical trends, or comparative risk analysis related to Assurant or the insurance industry
- out_of_scope: Questions unrelated to Assurant's 10-K reports or risk assessment

Query: {query}

Respond with ONLY a valid JSON object in this exact format:
{{"category": "<category>", "confidence": <confidence>}}"""

RAG_PROMPT = """You are a financial analyst specializing in insurance companies with expert knowledge of Assurant's recent 10-K reports. Provide a clear, accurate answer based on the provided contexts from Assurant's 10-K filings.

Context 1: {context_1}

Context 2: {context_2}

Context 3: {context_3}

Question: {query}

When applicable, cite specific sections, page numbers, or fiscal years from the 10-K reports. Compare data across the two most recent reports when relevant to show trends or changes. Present financial data clearly and accurately."""


class Settings(BaseSettings):
    # Common settings
    DATA_PATH: str = str(Path(__file__).parent.parent / "data")
    STORAGE_DIR: str = str(Path("storage").absolute())
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 20
    COLLECTOR_ENDPOINT: str = "https://otlp.arize.com/v1"

    # Azure OpenAI settings
    AZURE_OPENAI_API_KEY: Optional[str] = None  # Optional for VPN authentication
    AZURE_OPENAI_ENDPOINT: str  # Required
    AZURE_OPENAI_API_VERSION: str = "2023-12-01-preview"
    AZURE_OPENAI_DEPLOYMENT: str  # Required
    AZURE_OPENAI_MODEL: str = AzureOpenAIModels.GPT_4_TURBO.value

    # Arize settings
    ARIZE_SPACE_ID: str
    ARIZE_API_KEY: str
    ARIZE_MODEL_ID: str

    # API Settings
    API_TIMEOUT: int = 60
    API_MAX_RETRIES: int = 3
    API_RETRY_DELAY: int = 1

    # Phoenix settings
    phoenix_project_name: str = "10k-chatbot"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

from guardrails.hub import DetectJailbreak, ToxicLanguage
from guardrails import Guard

def validate_query_for_jailbreak(query: str) -> bool:
    """
    Validate input for potential jailbreak attempts
    
    :param query: Input query to validate
    :return: True if safe, False if jailbreak detected
    """
    try:
        guard = Guard().use(DetectJailbreak)
        guard.validate(query)
        return True
    except Exception:
        return False

def validate_query_for_toxic_language(query: str) -> bool:
    """
    Validate input for toxic language
    
    :param query: Input query to validate
    :return: True if safe, False if toxic language detected
    """
    try:
        guard = Guard().use(
            ToxicLanguage, 
            threshold=0.5,  # Adjust sensitivity as needed
            validation_method="sentence", 
            on_fail="exception"
        )
        guard.validate(query)
        return True
    except Exception:
        return False