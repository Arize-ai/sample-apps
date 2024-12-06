# from pydantic_settings import BaseSettings
# from pathlib import Path
# from enum import Enum
# from typing import Optional


# class BedrockModels(str, Enum):
#     CLAUDE = "anthropic.claude-3-haiku-20240307-v1:0"


# CLASSIFICATION_PROMPT = """You are a query classifier for OSHA and risk assessment application.
# Analyze the following query and respond with a JSON object containing two fields:
# 1. 'category': Must be exactly one of: "OSHA", "risk_assessment", or "out_of_scope"
# 2. 'confidence': A number between 0 and 1 indicating your confidence in the classification

# Guidelines:
# - OSHA: Questions about compliance with OSHA regulations, guidelines, standards and compliance
# - risk_assessment: Queries about business risk scoring, risk profiles, historical trends, risk analysis
# - out_of_scope: Questions unrelated to OSHA or risk assessment

# Query: {query}

# Respond with ONLY a valid JSON object in this exact format:
# {{"category": "<category>", "confidence": <confidence>}}"""


# class PromptTemplates:
#     RAG = """You are an OSHA regulations expert. Provide a clear, accurate answer based on the provided context.
#     Context: {context}
#     Question: {query}
#     Cite specific OSHA standards when applicable."""


# class Settings(BaseSettings):
#     # Common settings
#     DATA_PATH: str = str(Path("data").absolute())
#     STORAGE_DIR: str = str(Path("storage").absolute())
#     CHUNK_SIZE: int = 1024
#     CHUNK_OVERLAP: int = 20
#     COLLECTOR_ENDPOINT: str
#     PROMPTS: PromptTemplates = PromptTemplates()

#     # AWS/Bedrock settings
#     AWS_ACCESS_KEY_ID: Optional[str] = None
#     AWS_SECRET_ACCESS_KEY: Optional[str] = None
#     AWS_SESSION_TOKEN: Optional[str] = None
#     MODEL: str = BedrockModels.CLAUDE.value
#     AWS_REGION: str = "us-east-1"

#     # Arize settings
#     ARIZE_SPACE_ID: str
#     ARIZE_API_KEY: str
#     ARIZE_MODEL_ID: str

#     # API Settings
#     API_TIMEOUT: int = 60
#     API_MAX_RETRIES: int = 3
#     API_RETRY_DELAY: int = 1

#     # Phoenix settings
#     phoenix_project_name: str = "verisk_assistant"

#     class Config:
#         env_file = ".env"
#         env_file_encoding = "utf-8"
#         extra = "allow"

from pydantic_settings import BaseSettings
from pathlib import Path
from enum import Enum
from typing import Optional


class BedrockModels(str, Enum):
    CLAUDE = "anthropic.claude-3-haiku-20240307-v1:0"


TEMPLATE_VERSION = "1.0.0"

CLASSIFICATION_PROMPT = """You are a query classifier for OSHA and risk assessment application. 
Analyze the following query and respond with a JSON object containing two fields:
1. 'category': Must be exactly one of: "OSHA", "risk_assessment", or "out_of_scope"
2. 'confidence': A number between 0 and 1 indicating your confidence in the classification

Guidelines:
- OSHA: Questions about compliance with OSHA regulations, guidelines, standards and compliance
- risk_assessment: Queries about business risk scoring, risk profiles, historical trends, risk analysis
- out_of_scope: Questions unrelated to OSHA or risk assessment

Query: {query}

Respond with ONLY a valid JSON object in this exact format:
{{"category": "<category>", "confidence": <confidence>}}"""

RAG_PROMPT = """You are an OSHA regulations expert. Provide a clear, accurate answer based on the provided contexts.

Context 1: {context_1}

Context 2: {context_2}

Context 3: {context_3}

Question: {query}

Cite specific OSHA standards when applicable."""


class Settings(BaseSettings):
    # Common settings
    DATA_PATH: str = str(Path("data").absolute())
    STORAGE_DIR: str = str(Path("storage").absolute())
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 20
    COLLECTOR_ENDPOINT: str = "https://otlp.arize.com/v1"

    # AWS/Bedrock settings
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None
    MODEL: str = BedrockModels.CLAUDE.value
    AWS_REGION: str = "us-east-1"

    # Arize settings
    ARIZE_SPACE_ID: str
    ARIZE_API_KEY: str
    ARIZE_MODEL_ID: str

    # API Settings
    API_TIMEOUT: int = 60
    API_MAX_RETRIES: int = 3
    API_RETRY_DELAY: int = 1

    # Phoenix settings
    phoenix_project_name: str = "verisk_assistant"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"
