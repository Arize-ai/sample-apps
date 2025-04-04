# this is for phoenix
from openinference.semconv.resource import ResourceAttributes
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from phoenix.config import get_env_host, get_env_port
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def setup_instrumentation():
    try:
        load_dotenv()  # Load environment variables

        # Phoenix Configuration
        resource = Resource(
            attributes={ResourceAttributes.PROJECT_NAME: "10k-chatbot"}
        )
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)

        collector_endpoint = f"http://{get_env_host()}:{get_env_port()}/v1/traces"
        span_exporter = OTLPSpanExporter(endpoint=collector_endpoint)
        span_processor = SimpleSpanProcessor(span_exporter)

        trace.get_tracer_provider().add_span_processor(span_processor)

        # Initialize LlamaIndex instrumentation
        LlamaIndexInstrumentor().instrument(
            tracer_provider=tracer_provider, propagate_context=True
        )

        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info("Instrumentation setup complete with Phoenix configuration")
        return tracer_provider

    except Exception as e:
        logger.error(f"Failed to setup instrumentation: {e}")
        raise


# # Use this to send to Arize
# from opentelemetry.trace import set_tracer_provider
# from opentelemetry.sdk.resources import Resource
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import (
#     BatchSpanProcessor,
# )  # OLTP better to use in production or mature development
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
# from openinference.instrumentation.openai import OpenAIInstrumentor
# from dotenv import load_dotenv
# import logging
# import os

# logger = logging.getLogger(__name__)


# def setup_instrumentation():
#     try:
#         load_dotenv()  # Load environment variables

#         arize_space_id = os.getenv("ARIZE_SPACE_ID")
#         arize_api_key = os.getenv("ARIZE_API_KEY")
#         arize_model_id = os.getenv("ARIZE_MODEL_ID", "default_model")

#         if not arize_space_id or not arize_api_key:
#             raise ValueError(
#                 "ARIZE_SPACE_ID and ARIZE_API_KEY must be set as environment variables."
#             )

#         headers = f"space_id={arize_space_id},api_key={arize_api_key}"
#         os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = headers

#         trace_attributes = {
#             "model_id": arize_model_id,  # This is how your model will show up in Arize
#         }

#         endpoint = "https://otlp.arize.com/v1"

#         span_exporter = OTLPSpanExporter(endpoint=endpoint)
#         span_processor = BatchSpanProcessor(span_exporter)

#         tracer_provider = TracerProvider(resource=Resource(attributes=trace_attributes))

#         tracer_provider.add_span_processor(span_processor)
#         set_tracer_provider(tracer_provider)

#         # Initialize LlamaIndex instrumentation
#         LlamaIndexInstrumentor().instrument(
#             tracer_provider=tracer_provider, propagate_context=True
#         )

#         OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

#         logger.info("Instrumentation setup complete with configurations")
#         return tracer_provider

#     except Exception as e:
#         logger.error(f"Failed to setup instrumentation: {e}")
#         raise
