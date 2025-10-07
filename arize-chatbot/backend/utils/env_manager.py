import os
from contextlib import contextmanager
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Manages temporary environment variable overrides with automatic restoration."""

    @staticmethod
    @contextmanager
    def temporary_env_vars(overrides: Optional[Dict[str, str]] = None):
        """
        Context manager that temporarily sets environment variables and restores them afterwards.

        Args:
            overrides: Dictionary of environment variables to temporarily set
        """
        if not overrides:
            # If no overrides provided, just yield without changing anything
            yield
            return

        # Store original values
        original_values = {}
        variables_to_restore = []

        try:
            # Set temporary values
            for key, value in overrides.items():
                if value is not None:  # Only override if a value is provided
                    original_values[key] = os.environ.get(key)
                    variables_to_restore.append(key)
                    os.environ[key] = value
                    logger.info(f"Temporarily set {key}")

            yield

        finally:
            # Restore original values
            for key in variables_to_restore:
                if original_values[key] is None:
                    # Variable didn't exist before, remove it
                    os.environ.pop(key, None)
                else:
                    # Restore original value
                    os.environ[key] = original_values[key]
                logger.info(f"Restored {key}")


def validate_env_overrides(
    overrides: Optional[Dict[str, str]],
) -> Optional[Dict[str, str]]:
    """
    Validates and filters environment variable overrides.

    Args:
        overrides: Dictionary of potential environment variable overrides

    Returns:
        Filtered dictionary containing only valid overrides
    """
    if not overrides:
        return None

    # List of allowed environment variables that can be overridden
    allowed_vars = {
        "ARIZE_SPACE_ID",
        "ARIZE_MODEL_ID",
        "ARIZE_API_KEY",
        "OPENAI_API_KEY",
    }

    # Filter to only allowed variables
    filtered = {
        key: value
        for key, value in overrides.items()
        if key in allowed_vars and value is not None and value.strip()
    }

    return filtered if filtered else None
