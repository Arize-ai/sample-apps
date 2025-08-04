"""
Arize AX Tracing Setup for Pipecat Voice Agent

This module configures OpenTelemetry tracing to send telemetry data to Arize AX
for comprehensive observability of the voice agent pipeline.

Pure OpenInference Conventions for GenAI Use Cases:
- CHAIN: Used for ALL manual operations (pipeline, session, LLM service setup, etc.)
- Auto-instrumented spans: Keep their appropriate kinds (ChatCompletion=LLM, etc.)
- Attributes: Only OpenInference semantic conventions (SpanAttributes.*)
- Custom data: Stored in SpanAttributes.METADATA for proper categorization
"""

import os
import logging
import atexit
import asyncio
import json
from typing import Optional, Callable, Any
from functools import wraps
from opentelemetry import trace as trace_api
from opentelemetry import context as context_api
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan
from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
from openinference.instrumentation.openai import OpenAIInstrumentor
from arize.otel import register

# For overriding Pipecat's internal tracing
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Global tracer provider and tracer
_tracer_provider = None
_tracer = None

# OpenInferenceOnlyProcessor removed - no longer needed since we disable
# competing auto-instrumentations at the source using OTEL_PYTHON_DISABLED_INSTRUMENTATIONS

def accept_current_state():
    """
    Set up manual span creation for TTS and STT operations.
    
    The strategy is:
    1. Our manual spans use proper OpenInference conventions (CHAIN)
    2. ChatCompletion spans use proper OpenInference conventions (LLM) 
    3. TTS/STT spans are manually created by monkey patching service methods
    4. All spans get exported to Arize
    """
    logger.info("🚀 Setting up manual span creation for TTS/STT operations")
    logger.info("📊 Strategy:")
    logger.info("   • Manual spans: OpenInference CHAIN ✅")
    logger.info("   • ChatCompletion spans: OpenInference LLM ✅") 
    logger.info("   • TTS/STT spans: Manual creation via monkey patching ✅")
    logger.info("   • Arize export: All spans sent as-is ✅")

class _NoOpSpan:
    """No-op span that doesn't create any traces"""
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def set_attribute(self, *args):
        pass
    
    def set_attributes(self, *args):
        pass
    
    def record_exception(self, *args):
        pass
    
    def set_status(self, *args):
        pass
    
    def add_event(self, *args):
        pass

# Removed problematic GenAISpanKindProcessor - it was causing issues

def patch_pipecat_span_creation():
    """
    Monkey patch TTS and STT service methods to create manual spans for every operation.
    """
    logger.info("🔧 Patching TTS and STT services to create manual spans")
    
    try:
        # Import the service classes
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        from pipecat.services.deepgram.stt import DeepgramSTTService
        import asyncio
        import functools
        from opentelemetry import context as context_api
        
        # Store original methods
        original_run_tts = ElevenLabsTTSService.run_tts
        original_handle_transcription = DeepgramSTTService._handle_transcription
        
        @functools.wraps(original_run_tts)
        async def traced_run_tts(self, text: str):
            """Wrapped TTS method with manual span creation"""
            tracer = get_tracer()
            if not tracer:
                # Fallback to original if no tracer
                async for frame in original_run_tts(self, text):
                    yield frame
                return
            
            # Explicitly use the current active span as parent (should be pipeline_execution)
            current_span = trace_api.get_current_span()
            if current_span and current_span.is_recording():
                with trace_api.use_span(current_span):
                    with tracer.start_as_current_span(
                        "tts",
                        attributes={
                            SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                            SpanAttributes.INPUT_VALUE: text[:500],  # Truncate long text
                            "service.name": "elevenlabs",
                            "voice.id": getattr(self, '_voice_id', 'unknown'),
                            "model": getattr(self, 'model_name', 'unknown'),
                            "character_count": len(text)
                        }
                    ) as span:
                        try:
                            # Call original method and yield frames
                            async for frame in original_run_tts(self, text):
                                yield frame
                            
                            # Mark span as successful
                            span.set_status(trace_api.Status(trace_api.StatusCode.OK))
                            
                        except Exception as e:
                            span.record_exception(e)
                            span.set_status(trace_api.Status(trace_api.StatusCode.ERROR, str(e)))
                            raise
            else:
                # Fallback if no current span
                with tracer.start_as_current_span(
                    "tts",
                    attributes={
                        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                        SpanAttributes.INPUT_VALUE: text[:500],  # Truncate long text
                        "service.name": "elevenlabs",
                        "voice.id": getattr(self, '_voice_id', 'unknown'),
                        "model": getattr(self, 'model_name', 'unknown'),
                        "character_count": len(text)
                    }
                ) as span:
                    try:
                        # Call original method and yield frames
                        async for frame in original_run_tts(self, text):
                            yield frame
                        
                        # Mark span as successful
                        span.set_status(trace_api.Status(trace_api.StatusCode.OK))
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(trace_api.Status(trace_api.StatusCode.ERROR, str(e)))
                        raise
        
        @functools.wraps(original_handle_transcription)
        async def traced_handle_transcription(self, transcript: str, is_final: bool, language=None):
            """Wrapped STT method with manual span creation"""
            tracer = get_tracer()
            if not tracer:
                # Fallback to original if no tracer
                return await original_handle_transcription(self, transcript, is_final, language)
            
            # Only create spans for final transcriptions to avoid spam
            if not is_final:
                return await original_handle_transcription(self, transcript, is_final, language)
            
            # Explicitly use the current active span as parent (should be pipeline_execution)
            current_span = trace_api.get_current_span()
            if current_span and current_span.is_recording():
                with trace_api.use_span(current_span):
                    with tracer.start_as_current_span(
                        "stt",
                        attributes={
                            SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                            SpanAttributes.OUTPUT_VALUE: transcript[:500],  # Truncate long transcript
                            "service.name": "deepgram", 
                            "model": getattr(self, 'model_name', 'unknown'),
                            "is_final": is_final,
                            "language": str(language) if language else None,
                            "character_count": len(transcript)
                        }
                    ) as span:
                        try:
                            # Call original method
                            result = await original_handle_transcription(self, transcript, is_final, language)
                            
                            # Mark span as successful
                            span.set_status(trace_api.Status(trace_api.StatusCode.OK))
                            return result
                            
                        except Exception as e:
                            span.record_exception(e)
                            span.set_status(trace_api.Status(trace_api.StatusCode.ERROR, str(e)))
                            raise
            else:
                # Fallback if no current span
                with tracer.start_as_current_span(
                    "stt",
                    attributes={
                        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                        SpanAttributes.OUTPUT_VALUE: transcript[:500],  # Truncate long transcript
                        "service.name": "deepgram", 
                        "model": getattr(self, 'model_name', 'unknown'),
                        "is_final": is_final,
                        "language": str(language) if language else None,
                        "character_count": len(transcript)
                    }
                ) as span:
                    try:
                        # Call original method
                        result = await original_handle_transcription(self, transcript, is_final, language)
                        
                        # Mark span as successful
                        span.set_status(trace_api.Status(trace_api.StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(trace_api.Status(trace_api.StatusCode.ERROR, str(e)))
                        raise
        
        # Apply the patches
        ElevenLabsTTSService.run_tts = traced_run_tts
        DeepgramSTTService._handle_transcription = traced_handle_transcription
        
        logger.info("✅ Successfully patched TTS and STT services for manual span creation")
        
    except Exception as e:
        logger.warning(f"Failed to patch TTS/STT services: {e}")
        raise

def setup_arize_tracing():
    """
    Set up Arize AX tracing with proper configuration for development and production.
    """
    global _tracer_provider, _tracer
    
    try:
        # STEP 1: Set up enhanced tracing strategy  
        accept_current_state()
        
        # STEP 2: Minimal instrumentation disabling - only disable truly competing ones
        disabled_instrumentations = [
            "traceloop-sdk"  # Only disable traceloop which can conflict
        ]
        
        # Let Pipecat's native tracing work by not disabling its instrumentations
        existing_disabled = os.getenv("OTEL_PYTHON_DISABLED_INSTRUMENTATIONS", "")
        if existing_disabled:
            all_disabled = f"{existing_disabled},{','.join(disabled_instrumentations)}"
        else:
            all_disabled = ",".join(disabled_instrumentations)
        
        os.environ["OTEL_PYTHON_DISABLED_INSTRUMENTATIONS"] = all_disabled
        logger.info(f"🚫 Minimal disabled instrumentations: {all_disabled}")
        logger.info("🔧 Allowing Pipecat's native TTS/STT instrumentation to work")
        
        # Get configuration from environment
        space_id = os.getenv("ARIZE_SPACE_ID")
        api_key = os.getenv("ARIZE_API_KEY") 
        project_name = os.getenv("ARIZE_PROJECT_NAME", "pipecat-voice-agent")
        is_development = os.getenv("DEVELOPMENT", "false").lower() == "true" or os.getenv("LOCAL_RUN", "false").lower() == "true"
        
        if not space_id or not api_key:
            logger.warning("Arize credentials not found in environment. Tracing will be disabled.")
            return None
            
        logger.info(f"🔭 Initializing Arize AX Tracing (Native Mode) 🔭")
        logger.info(f"|  Project: {project_name}")
        logger.info(f"|  Development Mode: {is_development}")
        logger.info(f"|  Mode: OpenInference + Native Pipecat spans")
        
        # STEP 3: Register with Arize using their helper function
        _tracer_provider = register(
            space_id=space_id,
            api_key=api_key,
            project_name=project_name,
            # Use immediate export in development for better debugging
            batch=not is_development,
            log_to_console=is_development
        )
        
        # Set as global tracer provider
        trace_api.set_tracer_provider(_tracer_provider)
        
        # Get tracer
        _tracer = trace_api.get_tracer(__name__)
        
        # STEP 4: Only instrument OpenAI with OpenInference (creates proper LLM spans)
        try:
            OpenAIInstrumentor().instrument(tracer_provider=_tracer_provider)
            logger.info("✅ OpenInference OpenAI instrumentation enabled (LLM spans)")
        except Exception as e:
            logger.warning(f"Failed to instrument OpenAI with OpenInference: {e}")
        
        # STEP 5: Create manual spans for TTS and STT operations
        try:
            patch_pipecat_span_creation()
            logger.info("🔧 Manual TTS/STT span creation enabled")
                
        except Exception as e:
            logger.warning(f"Failed to set up manual span creation: {e}")
            
        logger.info("🎯 Manual span creation mode: Create spans for every TTS/STT operation")
        logger.info("📝 Manual spans: OpenInference CHAIN kind ✅")
        logger.info("🤖 ChatCompletion spans: OpenInference LLM kind ✅")
        logger.info("🔧 TTS/STT spans: Manual span creation ✅")
        
        logger.info("✅ Arize AX tracing initialized successfully")
        
        # Register cleanup on exit
        atexit.register(shutdown_tracing)
        
        return _tracer_provider
        
    except Exception as e:
        logger.error(f"Failed to initialize Arize AX tracing: {e}")
        return None

def get_tracer():
    """Get the configured tracer instance."""
    return _tracer or trace_api.get_tracer(__name__)

def force_flush_traces():
    """Force flush all pending traces to Arize AX."""
    try:
        if _tracer_provider and hasattr(_tracer_provider, 'force_flush'):
            _tracer_provider.force_flush(timeout_millis=5000)
            logger.debug("✅ Traces flushed to Arize AX")
    except Exception as e:
        logger.debug(f"Trace flush failed (this is normal on shutdown): {e}")

def shutdown_tracing():
    """Gracefully shutdown tracing infrastructure."""
    try:
        if _tracer_provider and hasattr(_tracer_provider, 'shutdown'):
            _tracer_provider.shutdown()
            logger.debug("✅ Tracing infrastructure shut down")
    except Exception as e:
        logger.debug(f"Tracing shutdown failed (this is normal): {e}")

def capture_current_context():
    """Capture the current OpenTelemetry context for async propagation."""
    return context_api.get_current()

def with_context_propagation(func: Callable) -> Callable:
    """
    Decorator that ensures proper context propagation for async functions.
    Based on Arize documentation for async context propagation.
    """
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Capture the current context before the async call
            current_context = capture_current_context()
            
            # Attach the context in this async function
            token = context_api.attach(current_context)
            try:
                return await func(*args, **kwargs)
            finally:
                context_api.detach(token)
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return sync_wrapper

def trace_voice_agent_operation(operation_name: str, span_kind: str = "CHAIN"):
    """
    Decorator for tracing voice agent operations with proper async context propagation.
    
    Args:
        operation_name: Name of the operation being traced
        span_kind: OpenInference span kind. Use "CHAIN" for general operations, "LLM" for LLM calls
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            # Determine span kind
            span_kind_value = getattr(OpenInferenceSpanKindValues, span_kind.upper(), OpenInferenceSpanKindValues.CHAIN).value
            
            with tracer.start_as_current_span(
                operation_name,
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: span_kind_value,
                }
            ) as span:
                # Add function metadata using OpenInference conventions
                metadata = {"function_name": func.__name__, "operation_type": operation_name}
                span.set_attribute(SpanAttributes.METADATA, json.dumps(metadata))
                
                try:
                    if asyncio.iscoroutinefunction(func):
                        # For async functions, we need to run them with proper context propagation
                        current_context = context_api.get_current()
                        
                        async def async_wrapper():
                            token = context_api.attach(current_context)
                            try:
                                return await func(*args, **kwargs)
                            finally:
                                context_api.detach(token)
                        
                        # Return the coroutine
                        return async_wrapper()
                    else:
                        # For sync functions, run directly
                        result = func(*args, **kwargs)
                        span.set_attribute(SpanAttributes.OUTPUT_VALUE, str(result)[:500])  # Truncate large outputs
                        return result
                        
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace_api.Status(trace_api.StatusCode.ERROR, str(e)))
                    raise
                
        return wrapper
    return decorator

def create_session_span(session_id: str, session_type: str = "voice_agent") -> trace_api.Span:
    """
    Create a main session span that will be the parent for all operations.
    This ensures all traces are connected under one main trace.
    """
    tracer = get_tracer()
    
    session_span = tracer.start_span(
        f"pipecat_session_{session_type}",
        attributes={
            SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
            "session.id": session_id,
            "session.type": session_type,
            "agent.name": "pipecat-voice-agent",
            "agent.version": "1.0.0"
        }
    )
    
    # Set this span as the current span in context
    context_with_span = trace_api.set_span_in_context(session_span)
    context_api.attach(context_with_span)
    
    return session_span

def end_session_span(session_span: trace_api.Span, session_summary: str = "Session completed"):
    """
    End the session span and ensure all traces are flushed.
    """
    try:
        session_span.set_attribute(SpanAttributes.OUTPUT_VALUE, session_summary)
        session_span.set_status(trace_api.Status(trace_api.StatusCode.OK))
        session_span.end()
        
        # Force flush on session end to ensure all data is sent
        force_flush_traces()
        
    except Exception as e:
        logger.error(f"Error ending session span: {e}")

def add_session_metadata(**metadata):
    """Add metadata to the current span context."""
    current_span = trace_api.get_current_span()
    if current_span and current_span.is_recording():
        for key, value in metadata.items():
            if value is not None:
                current_span.set_attribute(f"session.{key}", str(value))

def trace_llm_interaction(prompt: str, response: str, model: str = "unknown"):
    """Add LLM interaction tracing to current span using OpenInference conventions."""
    current_span = trace_api.get_current_span()
    if current_span and current_span.is_recording():
        current_span.add_event(
            "llm_interaction",
            attributes={
                SpanAttributes.LLM_MODEL_NAME: model,
                SpanAttributes.INPUT_VALUE: prompt[:500],  # Truncate for readability
                SpanAttributes.OUTPUT_VALUE: response[:500]
            }
        )

def trace_audio_processing(operation: str, details: dict = None):
    """Add audio processing events to current span using OpenInference conventions."""
    current_span = trace_api.get_current_span()
    if current_span and current_span.is_recording():
        # Use metadata for custom audio processing attributes
        metadata = {"audio_operation": operation}
        if details:
            for key, value in details.items():
                metadata[f"audio_{key}"] = str(value)
        
        current_span.add_event(
            "audio_processing", 
            attributes={SpanAttributes.METADATA: json.dumps(metadata)}
        )

def trace_pipeline_event(event_name: str, **attributes):
    """Add pipeline events to current span using OpenInference conventions."""
    current_span = trace_api.get_current_span()
    if current_span and current_span.is_recording():
        # Use metadata for pipeline-specific attributes
        metadata = {}
        for key, value in attributes.items():
            metadata[f"pipeline_{key}"] = str(value) if value is not None else "None"
        
        current_span.add_event(
            event_name, 
            attributes={SpanAttributes.METADATA: json.dumps(metadata)}
        )

def create_llm_operation_span(operation_name: str, model: str, input_text: str = None):
    """Create a CHAIN span for LLM operations using pure OpenInference conventions."""
    tracer = get_tracer()
    if not tracer:
        return None
    
    current_context = context_api.get_current()
    
    span = tracer.start_span(
        operation_name,
        context=current_context,
        attributes={
            SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
            SpanAttributes.LLM_MODEL_NAME: model,
        }
    )
    
    if input_text:
        span.set_attribute(SpanAttributes.INPUT_VALUE, input_text[:500])  # Truncate
    
    return span

def create_tts_operation_span(operation_name: str, text: str, voice_id: str = None, model: str = None):
    """Create a CHAIN span for TTS operations using pure OpenInference conventions."""
    tracer = get_tracer()
    if not tracer:
        return None
    
    current_context = context_api.get_current()
    
    attributes = {
        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
        SpanAttributes.INPUT_VALUE: text[:500],  # Truncate for readability
    }
    
    # Add TTS-specific metadata
    metadata = {"operation_type": "text_to_speech"}
    if voice_id:
        metadata["voice_id"] = voice_id
    if model:
        metadata["model"] = model
        
    attributes[SpanAttributes.METADATA] = json.dumps(metadata)
    
    span = tracer.start_span(
        operation_name,
        context=current_context,
        attributes=attributes
    )
    
    return span

def finish_llm_span(span, output_text: str = None, token_usage: dict = None):
    """Finish an LLM span with output and token usage information."""
    if not span or not span.is_recording():
        return
        
    if output_text:
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, output_text[:500])  # Truncate
    
    if token_usage:
        if 'prompt_tokens' in token_usage:
            span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, token_usage['prompt_tokens'])
        if 'completion_tokens' in token_usage:
            span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, token_usage['completion_tokens'])
        if 'total_tokens' in token_usage:
            span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_TOTAL, token_usage['total_tokens'])
    
    span.set_status(trace_api.Status(trace_api.StatusCode.OK))
    span.end()

def finish_tts_span(span, duration: float = None, character_count: int = None):
    """Finish a TTS span with duration and character count information."""
    if not span or not span.is_recording():
        return
    
    metadata = {}
    if duration:
        metadata["duration_seconds"] = duration
    if character_count:
        metadata["character_count"] = character_count
        
    if metadata:
        span.set_attribute(SpanAttributes.METADATA, json.dumps(metadata))
    
    span.set_status(trace_api.Status(trace_api.StatusCode.OK))
    span.end()

# Context manager for session-level tracing
class SessionTracer:
    def __init__(self, session_id: str, session_type: str = "voice_agent"):
        self.session_id = session_id
        self.session_type = session_type
        self.session_span = None
        self.original_context = None
        
    def __enter__(self):
        self.original_context = context_api.get_current()
        self.session_span = create_session_span(self.session_id, self.session_type)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            if self.session_span:
                self.session_span.record_exception(exc_val)
                self.session_span.set_status(trace_api.Status(trace_api.StatusCode.ERROR, str(exc_val)))
                end_session_span(self.session_span, f"Session failed: {exc_val}")
        else:
            if self.session_span:
                end_session_span(self.session_span, "Session completed successfully")
        
        # Restore original context
        if self.original_context:
            context_api.attach(self.original_context)

def create_child_span_with_context(name: str, span_kind: str = "CHAIN", **attributes):
    """
    Create a child span that properly inherits from the current context.
    Useful for manual span creation in async operations.
    
    Args:
        name: Name of the span
        span_kind: OpenInference span kind ("CHAIN" for general ops, "LLM" for LLM calls)
        **attributes: Additional span attributes
    """
    tracer = get_tracer()
    
    # Get current context to ensure proper parent-child relationship
    current_context = context_api.get_current()
    
    span_kind_value = getattr(OpenInferenceSpanKindValues, span_kind.upper(), OpenInferenceSpanKindValues.CHAIN).value
    
    # Create span with current context as parent
    span = tracer.start_span(
        name,
        context=current_context,
        attributes={
            SpanAttributes.OPENINFERENCE_SPAN_KIND: span_kind_value,
            **attributes
        }
    )
    
    return span 