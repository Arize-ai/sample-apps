import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Set Hugging Face cache directory
os.environ["TRANSFORMERS_CACHE"] = "/app/models"
os.environ["HF_HOME"] = "/app/models"

from backend.utils.env_manager import EnvironmentManager, validate_env_overrides
from backend.utils.session_manager import SessionManager
from src.llamaindex_app.classifier import QueryClassifier
from src.llamaindex_app.flexible_instrumentation import (
    TracerConfig,
    get_instrumentation_manager,
    setup_flexible_instrumentation,
)
from src.llamaindex_app.index_manager import IndexManager
from src.llamaindex_app.main import init_openai_client, process_interaction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session manager
session_manager = SessionManager(cache_ttl_minutes=30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Initialize with default environment
    default_components = initialize_app()
    # Store default components in app_state for backward compatibility
    app_state.update(default_components)
    app_state["initialized"] = True
    yield
    # Shutdown (if needed)
    session_manager.clear_cache()


app = FastAPI(title="Assurant Chatbot API", lifespan=lifespan)

# Get allowed origins from environment variable or use default
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS", "https://ui-rag-whisperer.vercel.app"
).split(",")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize app state
app_state = {
    "initialized": False,
    "query_engine": None,
    "classifier": None,
    "tracer": None,
    "openai_client": None,
}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    env_overrides: Optional[Dict[str, str]] = (
        None  # New field for environment variables
    )


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None
    session_id: str


def has_valid_arize_config(
    env_overrides: Optional[Dict[str, str]] = None,
) -> tuple[bool, Dict[str, str]]:
    """
    Check if we have valid Arize configuration either from overrides or environment.

    Returns:
        tuple: (has_valid_config, effective_config_dict)
    """
    effective_config = {}

    # Helper function to get non-empty value
    def get_non_empty_value(override_key: str, env_key: str, default: str = "") -> str:
        if env_overrides and override_key in env_overrides:
            override_val = env_overrides.get(override_key, "").strip()
            if override_val:
                return override_val
        return os.getenv(env_key, default).strip()

    # Get effective values
    effective_config["space_id"] = get_non_empty_value(
        "ARIZE_SPACE_ID", "ARIZE_SPACE_ID"
    )
    effective_config["api_key"] = get_non_empty_value("ARIZE_API_KEY", "ARIZE_API_KEY")
    effective_config["model_id"] = get_non_empty_value(
        "ARIZE_MODEL_ID", "ARIZE_MODEL_ID", "default_model"
    )

    # Check if we have the required values
    has_valid = bool(effective_config["space_id"] and effective_config["api_key"])

    return has_valid, effective_config


def initialize_app(env_overrides: Optional[Dict[str, str]] = None):
    """Initialize the application components with optional environment overrides."""
    # For now, disable caching to ensure proper instrumentation reconfiguration
    # TODO: Implement smarter caching that handles instrumentation state properly
    # cached_components = session_manager.get_cached_components(env_overrides)
    # if cached_components:
    #     logger.info("Using cached components for this configuration")
    #     return cached_components

    try:

        # Setup flexible instrumentation
        # Always shutdown any existing instrumentation to ensure clean state
        manager = get_instrumentation_manager()
        if manager.is_configured():
            logger.info("Shutting down existing instrumentation before reconfiguring")
            manager.shutdown()

        has_valid_config, arize_config = has_valid_arize_config(env_overrides)

        if has_valid_config:
            # We have valid Arize configuration (either from overrides or environment)
            config = TracerConfig(
                space_id=arize_config["space_id"],
                api_key=arize_config["api_key"],
                model_id=arize_config["model_id"],
                use_env_headers=True,  # Use environment variable headers for compatibility
            )
            tracer_provider = manager.configure(config)

            # Determine source of configuration for logging
            has_overrides = env_overrides and any(
                key.startswith("ARIZE_") and env_overrides.get(key, "").strip()
                for key in env_overrides.keys()
            )
            source = (
                "overrides + environment fallback"
                if has_overrides
                else "environment variables"
            )
            logger.info(
                f"Using Arize configuration from {source}: model_id={arize_config['model_id']}"
            )
        else:
            # No valid Arize configuration available
            logger.warning(
                "No valid Arize configuration found (missing ARIZE_SPACE_ID or ARIZE_API_KEY)"
            )
            logger.info(
                "Instrumentation will be set up but may not export traces successfully"
            )
            # Still set up instrumentation with whatever we have (might be empty/test config)
            tracer_provider = setup_flexible_instrumentation()

        tracer = tracer_provider.get_tracer("llamaindex_app")

        # Initialize OpenAI client
        openai_client = init_openai_client()

        # Initialize index manager & query engine
        index_manager = IndexManager(openai_client=openai_client)
        query_engine = index_manager.get_query_engine()

        # Initialize classifier
        classifier = QueryClassifier(
            query_engine=query_engine, openai_client=openai_client
        )

        # Create components dictionary
        components = {
            "query_engine": query_engine,
            "classifier": classifier,
            "tracer": tracer,
            "openai_client": openai_client,
        }

        # Cache the components - disabled for now to ensure proper reconfiguration
        # session_manager.cache_components(env_overrides, components)

        logger.info(
            f"Application initialized successfully with env_overrides: {list(env_overrides.keys()) if env_overrides else 'default'}"
        )

        return components

    except Exception as e:
        logger.error(f"Failed to initialize app: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return the response."""
    # Validate and filter environment overrides
    env_overrides = validate_env_overrides(request.env_overrides)

    # Use temporary environment variables if provided
    with EnvironmentManager.temporary_env_vars(env_overrides):
        # Initialize or get cached components for this environment configuration
        components = initialize_app(env_overrides)

        session_id = request.session_id or str(uuid.uuid4())

        try:
            response, error = process_interaction(
                components["query_engine"],
                components["classifier"],
                components["tracer"],
                request.message,
                session_id,
            )

            if error:
                raise HTTPException(status_code=400, detail=error)

            sources = None
            if hasattr(response, "source_nodes") and response.source_nodes:
                sources = [
                    node.metadata.get("file_name", "Unknown source")
                    for node in response.source_nodes
                ]

            return ChatResponse(
                response=response.response, sources=sources, session_id=session_id
            )

        except Exception as e:
            logger.error(f"Error processing chat request: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "initialized": app_state["initialized"]}


@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check current configuration status."""
    try:
        # Check Arize configuration
        has_valid_config, arize_config = has_valid_arize_config()

        # Check instrumentation manager status
        manager = get_instrumentation_manager()
        instrumentation_status = {
            "is_configured": manager.is_configured(),
            "has_valid_arize_config": has_valid_config,
        }

        # Safe config info (no sensitive data)
        safe_config = {
            "space_id_present": bool(arize_config.get("space_id")),
            "api_key_present": bool(arize_config.get("api_key")),
            "model_id": arize_config.get("model_id", "not_set"),
        }

        return {
            "instrumentation": instrumentation_status,
            "arize_config": safe_config,
            "environment_vars": {
                "ARIZE_SPACE_ID_set": bool(os.getenv("ARIZE_SPACE_ID")),
                "ARIZE_API_KEY_set": bool(os.getenv("ARIZE_API_KEY")),
                "ARIZE_MODEL_ID": os.getenv("ARIZE_MODEL_ID", "not_set"),
            },
        }
    except Exception as e:
        return {"error": str(e), "status": "debug_failed"}
