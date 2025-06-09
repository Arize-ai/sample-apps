from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import logging
import os
from contextlib import asynccontextmanager

# Set Hugging Face cache directory
os.environ['TRANSFORMERS_CACHE'] = '/app/models'
os.environ['HF_HOME'] = '/app/models'

from src.llamaindex_app.main import init_openai_client, setup_instrumentation, process_interaction
from src.llamaindex_app.classifier import QueryClassifier
from src.llamaindex_app.index_manager import IndexManager
from src.llamaindex_app.config import Settings
from backend.utils.env_manager import EnvironmentManager, validate_env_overrides
from backend.utils.session_manager import SessionManager

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

app = FastAPI(title="Arize Chatbot API", lifespan=lifespan)

# Get allowed origins from environment variable or use default
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "https://ui-rag-whisperer.vercel.app").split(",")

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
    "openai_client": None
}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    env_overrides: Optional[Dict[str, str]] = None  # New field for environment variables

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None
    session_id: str

def initialize_app(env_overrides: Optional[Dict[str, str]] = None):
    """Initialize the application components with optional environment overrides."""
    # Check if we have cached components for this configuration
    cached_components = session_manager.get_cached_components(env_overrides)
    if cached_components:
        return cached_components
    
    try:
        # Load settings
        settings = Settings()
        
        # Setup instrumentation
        tracer_provider = setup_instrumentation()
        tracer = tracer_provider.get_tracer("llamaindex_app")
        
        # Initialize OpenAI client
        openai_client = init_openai_client()
        
        # Initialize index manager & query engine
        index_manager = IndexManager(openai_client=openai_client)
        query_engine = index_manager.get_query_engine()
        
        # Initialize classifier
        classifier = QueryClassifier(
            query_engine=query_engine,
            openai_client=openai_client
        )
        
        # Create components dictionary
        components = {
            "query_engine": query_engine,
            "classifier": classifier,
            "tracer": tracer,
            "openai_client": openai_client
        }
        
        # Cache the components
        session_manager.cache_components(env_overrides, components)
        
        logger.info(f"Application initialized successfully with env_overrides: {list(env_overrides.keys()) if env_overrides else 'default'}")
        
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
                session_id
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
                response=response.response,
                sources=sources,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Error processing chat request: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "initialized": app_state["initialized"]}