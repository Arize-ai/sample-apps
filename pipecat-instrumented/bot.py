#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
import uuid
import webbrowser
import time

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomObject,
    DailyRoomParams,
)
from pipecat.services.deepgram.stt import DeepgramSTTService

# Load environment variables
load_dotenv()

# Import Arize AX tracing setup
from tracing_setup import (
    setup_arize_tracing,
    SessionTracer,
    with_context_propagation,
    add_session_metadata,
    trace_llm_interaction,
    trace_audio_processing,
    trace_pipeline_event,
    create_child_span_with_context,
    force_flush_traces,
    shutdown_tracing,
    get_tracer,
)
from opentelemetry import trace as trace_api
from opentelemetry import context as context_api

# Load configuration
load_dotenv()
logger.info("Starting Pipecat Voice Agent with Arize AX Tracing...")

# Initialize tracing with custom span processor to transform gen_ai spans
tracer_provider = setup_arize_tracing()

# Environment configuration
LOCAL_RUN = os.getenv("LOCAL_RUN", "false").lower() in ["true", "1"]


async def configure(aiohttp_session):
    """Configure Daily room for voice agent."""
    daily_rest_helper = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        aiohttp_session=aiohttp_session,
    )

    # Create a new Daily room with proper expiration time (Unix timestamp)
    # Set expiration to 5 minutes from now
    expiration_time = int(time.time()) + (60 * 5)  # Current Unix timestamp + 5 minutes

    params = DailyRoomParams(
        properties={
            "exp": expiration_time,  # Unix timestamp for 5 minutes from now
            "enable_chat": True,
            "enable_knocking": True,
            "enable_transcription": False,
        }
    )

    room: DailyRoomObject = await daily_rest_helper.create_room(params=params)
    token = await daily_rest_helper.get_token(room.url, 60 * 5)

    return (room.url, token)


@with_context_propagation
async def on_first_participant_joined(transport, participant):
    """Handle first participant joining the voice session."""
    participant_span = create_child_span_with_context(
        "participant_joined_processing",
        "CHAIN",
        **{
            "participant.id": participant.get("id", "unknown"),
            "event.type": "participant_joined",
        },
    )

    with participant_span:
        logger.info("First participant joined: {}", participant.get("id", "unknown"))

        # Add session metadata for this participant
        participant_id = participant.get("id", "unknown")
        add_session_metadata(
            participant_id=participant_id,
            participant_type="user",
            interaction_mode="voice",
        )

        # Trace pipeline event
        trace_pipeline_event(
            "participant_joined", participant_id=participant_id, transport_type="daily"
        )

        await transport.capture_participant_transcription(participant["id"])
        # await transport.capture_participant_video(participant["id"], framerate=0)


@with_context_propagation
async def on_participant_left(transport, participant, reason):
    """Handle participant leaving the voice session."""
    participant_span = create_child_span_with_context(
        "participant_left_processing",
        "CHAIN",
        **{
            "participant.id": participant.get("id", "unknown"),
            "leave.reason": str(reason),
            "event.type": "participant_left",
        },
    )

    with participant_span:
        logger.info(
            f"Participant left: {participant.get('id', 'unknown')}, reason: {reason}"
        )

        # Trace the session end event
        trace_pipeline_event(
            "participant_left",
            participant_id=participant.get("id", "unknown"),
            reason=str(reason),
        )

        await task.cancel()

        # Force flush traces when participant leaves to capture the session
        force_flush_traces()


@with_context_propagation
async def main(transport):
    """Main pipeline execution with comprehensive tracing."""
    # Explicitly get current span (should be transport_initialization) and use as parent
    tracer = get_tracer()
    current_span = trace_api.get_current_span()

    if current_span and current_span.is_recording():
        # Use the current active span (transport_initialization) as parent
        with trace_api.use_span(current_span):
            pipeline_span = create_child_span_with_context(
                "voice_pipeline_main",
                "CHAIN",
                **{"pipeline.type": "voice_agent", "transport.type": "daily"},
            )
    else:
        # Fallback if no current span
        pipeline_span = create_child_span_with_context(
            "voice_pipeline_main",
            "CHAIN",
            **{"pipeline.type": "voice_agent", "transport.type": "daily"},
        )

    with pipeline_span:
        # Create aiohttp session for services that need it
        async with aiohttp.ClientSession() as aiohttp_session:
            # Set the pipeline span as the active context for child spans
            tracer = get_tracer()
            pipeline_context = trace_api.set_span_in_context(pipeline_span)
            context_token = context_api.attach(pipeline_context)

            try:
                # Initialize services with tracing - now as children of voice_pipeline_main
                tts_span = create_child_span_with_context("tts_service_init", "CHAIN")
                with tts_span:
                    tts = ElevenLabsTTSService(
                        aiohttp_session=aiohttp_session,
                        api_key=os.getenv("ELEVENLABS_API_KEY"),
                        voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
                        model=os.getenv("ELEVENLABS_MODEL"),
                    )
                    # TTS operations will be traced via manual span creation

                    trace_audio_processing(
                        "tts_service_initialized",
                        {
                            "service": "elevenlabs",
                            "voice_id": os.getenv("ELEVENLABS_VOICE_ID"),
                            "model": os.getenv("ELEVENLABS_MODEL"),
                        },
                    )

                llm_span = create_child_span_with_context("llm_service_init", "CHAIN")
                with llm_span:
                    llm = OpenAILLMService(
                        api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo"
                    )
                    # LLM operations are traced via OpenInference instrumentation

                    trace_llm_interaction(
                        "LLM service initialized",
                        "OpenAI GPT-3.5-turbo service ready",
                        "gpt-3.5-turbo",
                    )

                stt_span = create_child_span_with_context("stt_service_init", "CHAIN")
                with stt_span:
                    stt = DeepgramSTTService(
                        api_key=os.getenv("DEEPGRAM_API_KEY"),
                        model="nova-2",
                        language="en",
                    )
                    # STT operations will be traced via manual span creation

                    trace_audio_processing(
                        "stt_service_initialized",
                        {"service": "deepgram", "model": "nova-2", "language": "en"},
                    )

                context_span = create_child_span_with_context(
                    "context_aggregator_init", "CHAIN"
                )
                with context_span:
                    context = OpenAILLMContext(
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful assistant. You are talking to a user over voice, so keep your responses brief and conversational. Respond as if you're having a friendly chat.",
                            }
                        ]
                    )
                    context_aggregator = llm.create_context_aggregator(context)
                    trace_pipeline_event(
                        "context_aggregator_initialized", message_count=1
                    )

                # Create pipeline with tracing
                pipeline_init_span = create_child_span_with_context(
                    "pipeline_creation", "CHAIN"
                )
                with pipeline_init_span:
                    pipeline = Pipeline(
                        [
                            transport.input(),
                            stt,
                            context_aggregator.user(),
                            llm,
                            tts,
                            transport.output(),
                            context_aggregator.assistant(),
                        ]
                    )
                    trace_pipeline_event("pipeline_created", component_count=6)

                # Set up event handlers
                transport.add_event_handler(
                    "on_first_participant_joined", on_first_participant_joined
                )
                transport.add_event_handler("on_participant_left", on_participant_left)

                # Create pipeline_execution span as child of voice_pipeline_main
                # This is now WITHIN the voice_pipeline_main context
                runner_span = create_child_span_with_context(
                    "pipeline_execution", "CHAIN"
                )

                # Set pipeline_execution as the active context for all operations within it
                execution_context = trace_api.set_span_in_context(runner_span)
                execution_token = context_api.attach(execution_context)

                try:
                    with runner_span:
                        global task
                        task = PipelineTask(
                            pipeline,
                            params=PipelineParams(
                                allow_interruptions=True,
                                enable_metrics=True,  # Enable for service-level tracing
                                enable_usage_metrics=True,  # Enable for token usage tracking
                            ),
                        )

                        trace_pipeline_event(
                            "pipeline_task_created", allow_interruptions=True
                        )

                        # Now run the pipeline within the pipeline_execution context
                        # This ensures TTS/STT operations are children of pipeline_execution
                        runner = PipelineRunner()
                        await runner.run(task)

                        trace_pipeline_event("pipeline_execution_completed")

                finally:
                    # Restore the pipeline_execution context
                    context_api.detach(execution_token)

            finally:
                # Restore the voice_pipeline_main context
                context_api.detach(context_token)


# Local development with session tracing
@with_context_propagation
async def local_daily():
    """Daily transport for local development with session-level tracing."""
    # Create a unique session ID for this development session
    session_id = f"local_session_{uuid.uuid4().hex[:8]}"

    # Use SessionTracer context manager to create a main session span
    with SessionTracer(session_id, "local_development") as session:
        logger.info(f"🚀 Starting local development session: {session_id}")

        # Add initial session metadata
        add_session_metadata(
            environment="local_development",
            agent_version="1.0.0",
            transport_type="daily",
        )

        try:
            # Configure Daily room with tracing
            config_span = create_child_span_with_context(
                "daily_room_configuration", "CHAIN"
            )
            with config_span:
                async with aiohttp.ClientSession() as aiohttp_session:
                    (room_url, token) = await configure(aiohttp_session)

                    trace_pipeline_event("daily_room_configured", room_url=room_url)

            # Create transport with tracing
            transport_span = create_child_span_with_context(
                "transport_initialization", "CHAIN"
            )
            with transport_span:
                transport = DailyTransport(
                    room_url,
                    token,
                    "Pipecat Local Bot",
                    params=DailyParams(
                        audio_in_enabled=True,
                        audio_out_enabled=True,
                        transcription_enabled=True,
                        vad_analyzer=SileroVADAnalyzer(),
                    ),
                )

                # Add transport metadata
                add_session_metadata(
                    room_url=room_url,
                    bot_name="Pipecat Local Bot",
                    vad_enabled=True,
                    transcription_enabled=True,
                )

                trace_pipeline_event(
                    "transport_initialized",
                    room_url=room_url,
                    bot_name="Pipecat Local Bot",
                )

                logger.warning(f"Talk to your voice agent here: {room_url}")
                webbrowser.open(room_url)

                # Run the main pipeline
                await main(transport)

        except Exception as e:
            logger.exception(f"Error in local development mode: {e}")
            # The SessionTracer context manager will handle error recording
            raise


# Production deployment with session tracing
@with_context_propagation
async def main_daily(room_url: str):
    """Production Daily transport with session-level tracing."""
    # Create a unique session ID for this production session
    session_id = f"prod_session_{uuid.uuid4().hex[:8]}"

    # Use SessionTracer context manager
    with SessionTracer(session_id, "production") as session:
        logger.info(f"🚀 Starting production session: {session_id}")

        # Add initial session metadata
        add_session_metadata(
            environment="production",
            agent_version="1.0.0",
            transport_type="daily",
            room_url=room_url,
        )

        try:
            transport_span = create_child_span_with_context(
                "production_transport_init", "CHAIN"
            )
            with transport_span:
                transport = DailyTransport(
                    room_url,
                    None,  # No token needed for production in some cases
                    "Pipecat Production Bot",
                    params=DailyParams(
                        audio_in_enabled=True,
                        audio_out_enabled=True,
                        transcription_enabled=True,
                        vad_analyzer=SileroVADAnalyzer(),
                    ),
                )

                add_session_metadata(
                    bot_name="Pipecat Production Bot", deployment_mode="production"
                )

                trace_pipeline_event("production_transport_initialized")

                await main(transport)

        except Exception as e:
            logger.exception(f"Error in production mode: {e}")
            # The SessionTracer context manager will handle error recording
            raise


# Required entry point for pipecat cloud platform
@with_context_propagation
async def bot(args):
    """
    Main bot entry point for pipecat cloud platform.
    This function is called by the platform with Daily session arguments.
    """
    # Create a unique session ID for this bot instance
    session_id = f"cloud_session_{uuid.uuid4().hex[:8]}"

    # Use SessionTracer context manager for comprehensive tracing
    with SessionTracer(session_id, "pipecat_cloud") as session:
        logger.info(f"🚀 Starting pipecat cloud session: {session_id}")

        # Add initial session metadata
        add_session_metadata(
            environment="pipecat_cloud",
            agent_version="1.0.0",
            transport_type="daily",
            room_url=getattr(args, "room_url", "unknown"),
            platform="pipecat_cloud",
        )

        try:
            transport_span = create_child_span_with_context(
                "cloud_transport_init", "CHAIN"
            )
            with transport_span:
                # Create transport with provided arguments
                transport = DailyTransport(
                    args.room_url,
                    args.token,
                    "Pipecat Cloud Bot",
                    params=DailyParams(
                        audio_in_enabled=True,
                        audio_out_enabled=True,
                        transcription_enabled=True,
                        vad_analyzer=SileroVADAnalyzer(),
                    ),
                )

                add_session_metadata(
                    bot_name="Pipecat Cloud Bot",
                    deployment_mode="cloud",
                    room_url=args.room_url,
                )

                trace_pipeline_event(
                    "cloud_transport_initialized",
                    room_url=args.room_url,
                    bot_name="Pipecat Cloud Bot",
                )

                # Run the main pipeline with comprehensive tracing
                await main(transport)

        except Exception as e:
            logger.exception(f"Error in pipecat cloud mode: {e}")
            # The SessionTracer context manager will handle error recording
            raise


# Entry points with proper tracing lifecycle
if LOCAL_RUN and __name__ == "__main__":
    logger.info("🚀 Running in local development mode with Arize AX tracing")
    try:
        import asyncio

        asyncio.run(local_daily())
    except Exception as e:
        logger.exception(f"Failed to run in local mode: {e}")
    finally:
        # Ensure all traces are flushed before exit
        logger.info("Ensuring all traces are flushed before exit...")
        force_flush_traces()
        shutdown_tracing()

elif __name__ == "__main__":
    # Check if this might be a local development attempt without LOCAL_RUN set
    daily_room_url = os.getenv("DAILY_ROOM_URL", "")

    if not daily_room_url:
        logger.error("❌ Missing configuration!")
        logger.error("")
        logger.error("For LOCAL DEVELOPMENT:")
        logger.error("  Set LOCAL_RUN=true and run: LOCAL_RUN=true python bot.py")
        logger.error("")
        logger.error("For PRODUCTION DEPLOYMENT:")
        logger.error("  Set DAILY_ROOM_URL environment variable")
        logger.error(
            "  Example: DAILY_ROOM_URL=https://your-room.daily.co python bot.py"
        )
        logger.error("")
        logger.error("💡 Tip: For local testing, use LOCAL_RUN=true python bot.py")
        exit(1)

    logger.info("🌐 Running in production mode with Arize AX tracing")
    try:
        import asyncio

        asyncio.run(main_daily(daily_room_url))
    except Exception as e:
        logger.exception(f"Failed to run in production mode: {e}")
    finally:
        force_flush_traces()
        shutdown_tracing()
