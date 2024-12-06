# src/llamaindex_app/__init__.py
"""LlamaIndex terminal application package."""

__version__ = "0.1.0"

from .classifier import QueryClassifier, QueryCategory
from .index_manager import IndexManager
from .instrumentation import setup_instrumentation

__all__ = ["QueryClassifier", "QueryCategory", "IndexManager", "setup_instrumentation"]
