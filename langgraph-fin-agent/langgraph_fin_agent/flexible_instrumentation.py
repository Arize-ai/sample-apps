"""
Flexible OpenTelemetry instrumentation that allows runtime configuration
without relying on global state.
"""

from typing import Optional, Dict, Any, List
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Tracer
from openinference.instrumentation.langchain import LangChainInstrumentor
import logging
import os
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class TracerConfig:
    """Configuration for OpenTelemetry tracer"""

    space_id: Optional[str] = None
    api_key: Optional[str] = None
    model_id: str = "default_model"
    endpoint: str = "https://otlp.arize.com/v1"
    additional_attributes: Optional[Dict[str, Any]] = None
    use_env_headers: bool = False  # Option to use environment variable for headers

    @classmethod
    def from_env(cls, use_env_headers: bool = True) -> "TracerConfig":
        """Create configuration from environment variables

        Args:
            use_env_headers: If True, use environment variable for headers (default).
                           This matches the original implementation behavior.
        """
        return cls(
            space_id=os.getenv("ARIZE_SPACE_ID"),
            api_key=os.getenv("ARIZE_API_KEY"),
            model_id=os.getenv("ARIZE_MODEL_ID", "default_model"),
            use_env_headers=use_env_headers,
        )


class FlexibleInstrumentation:
    """
    A flexible instrumentation manager that allows runtime configuration
    without relying on global state.
    """

    def __init__(self):
        self._tracer_provider: Optional[TracerProvider] = None
        self._span_processors: List[BatchSpanProcessor] = []
        self._langchain_instrumentor: Optional[LangChainInstrumentor] = None
        self._is_configured = False
        self._env_var_key: Optional[str] = None  # Track environment variable we set

    def configure(self, config: TracerConfig) -> TracerProvider:
        """
        Configure or reconfigure the instrumentation with new settings.

        Args:
            config: TracerConfig object with configuration settings

        Returns:
            The configured TracerProvider
        """
        # Shutdown existing configuration if any
        if self._is_configured:
            self.shutdown()

        if not config.space_id or not config.api_key:
            raise ValueError(
                "ARIZE_SPACE_ID and ARIZE_API_KEY must be provided in configuration."
            )

        # Set headers for authentication
        if config.use_env_headers:
            # Use environment variable approach (like original implementation)
            headers_str = f"space_id={config.space_id},api_key={config.api_key}"
            os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = headers_str
            logger.info("Set OTEL_EXPORTER_OTLP_TRACES_HEADERS environment variable")
            # Store the env var key so we can clean it up later
            self._env_var_key = "OTEL_EXPORTER_OTLP_TRACES_HEADERS"
            # Don't pass headers directly when using env var
            span_exporter = OTLPSpanExporter(endpoint=config.endpoint)
        else:
            # Pass headers directly as tuple of tuples for gRPC
            headers = (
                ("space_id", config.space_id),
                ("api_key", config.api_key),
            )
            logger.info("Passing headers directly to exporter")
            span_exporter = OTLPSpanExporter(endpoint=config.endpoint, headers=headers)

        # Create trace attributes
        trace_attributes = {
            "model_id": config.model_id,
        }
        if config.additional_attributes:
            trace_attributes.update(config.additional_attributes)
        span_processor = BatchSpanProcessor(span_exporter)

        # Create tracer provider
        self._tracer_provider = TracerProvider(
            resource=Resource(attributes=trace_attributes)
        )
        self._tracer_provider.add_span_processor(span_processor)
        self._span_processors.append(span_processor)

        # Initialize instrumentors with the specific tracer provider
        self._langchain_instrumentor = LangChainInstrumentor()
        self._langchain_instrumentor.instrument(tracer_provider=self._tracer_provider)

        self._is_configured = True
        logger.info("Flexible instrumentation configured successfully")
        logger.info(f"Endpoint: {config.endpoint}")
        logger.info(f"Model ID: {config.model_id}")
        logger.info(
            f"Using {'environment variable' if config.use_env_headers else 'direct'} headers"
        )

        return self._tracer_provider

    def get_tracer(self, name: str = "langgraph_fin_agent") -> Optional[Tracer]:
        """
        Get a tracer instance.

        Args:
            name: Name for the tracer

        Returns:
            Tracer instance or None if not configured
        """
        if not self._tracer_provider:
            logger.warning("Instrumentation not configured. Call configure() first.")
            return None
        return self._tracer_provider.get_tracer(name)

    def reconfigure(self, config: TracerConfig) -> TracerProvider:
        """
        Reconfigure the instrumentation with new settings.
        This will shutdown the existing configuration and create a new one.

        Args:
            config: New TracerConfig object

        Returns:
            The newly configured TracerProvider
        """
        logger.info("Reconfiguring instrumentation...")
        return self.configure(config)

    def shutdown(self):
        """Shutdown the instrumentation and clean up resources"""
        if self._is_configured:
            try:
                # Uninstrument the instrumentors
                if self._langchain_instrumentor:
                    self._langchain_instrumentor.uninstrument()

                # Shutdown span processors
                for processor in self._span_processors:
                    processor.shutdown()

                # Clean up environment variable if we set one
                if self._env_var_key and self._env_var_key in os.environ:
                    del os.environ[self._env_var_key]
                    logger.info(f"Cleaned up environment variable: {self._env_var_key}")

                # Clear references
                self._tracer_provider = None
                self._span_processors.clear()
                self._langchain_instrumentor = None
                self._is_configured = False
                self._env_var_key = None

                logger.info("Instrumentation shutdown complete")
            except Exception as e:
                logger.error(f"Error during instrumentation shutdown: {e}")

    def is_configured(self) -> bool:
        """Check if instrumentation is currently configured"""
        return self._is_configured

    @contextmanager
    def temporary_config(self, config: TracerConfig):
        """
        Context manager for temporary instrumentation configuration.
        Useful for testing or specific operations with different settings.

        Args:
            config: Temporary TracerConfig to use
        """
        # Save current state
        was_configured = self._is_configured
        old_provider = self._tracer_provider

        try:
            # Apply new configuration
            self.configure(config)
            yield self._tracer_provider
        finally:
            # Restore previous state
            self.shutdown()
            if was_configured and old_provider:
                # Note: We can't perfectly restore the old state, but we can
                # indicate that reconfiguration is needed
                logger.warning("Temporary configuration ended. Reconfiguration needed.")


# Global instance (but not globally configured)
_instrumentation_manager = FlexibleInstrumentation()


def get_instrumentation_manager() -> FlexibleInstrumentation:
    """Get the global instrumentation manager instance"""
    return _instrumentation_manager


def setup_flexible_instrumentation(
    config: Optional[TracerConfig] = None,
) -> TracerProvider:
    """
    Setup instrumentation with optional configuration.

    Args:
        config: Optional TracerConfig. If not provided, will use environment variables.

    Returns:
        Configured TracerProvider
    """
    if config is None:
        config = TracerConfig.from_env()

    manager = get_instrumentation_manager()
    return manager.configure(config)
