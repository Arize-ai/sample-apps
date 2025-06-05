from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    initialize_app()
    yield
    # Shutdown (if needed)

app = FastAPI(title="Assurant Chatbot API", lifespan=lifespan)

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

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None
    session_id: str

def initialize_app():
    """Initialize the application components."""
    if not app_state["initialized"]:
        try:
            # Load settings
            settings = Settings()
            
            # Setup instrumentation
            tracer_provider = setup_instrumentation()
            app_state["tracer"] = tracer_provider.get_tracer("llamaindex_app")
            
            # Initialize OpenAI client
            app_state["openai_client"] = init_openai_client()
            
            # Initialize index manager & query engine
            index_manager = IndexManager(openai_client=app_state["openai_client"])
            app_state["query_engine"] = index_manager.get_query_engine()
            
            # Initialize classifier
            app_state["classifier"] = QueryClassifier(
                query_engine=app_state["query_engine"],
                openai_client=app_state["openai_client"]
            )
            
            app_state["initialized"] = True
            logger.info("Application initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize app: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return the response."""
    if not app_state["initialized"]:
        initialize_app()
    
    else:
        logger.info("App already initialized")
    
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        response, error = process_interaction(
            app_state["query_engine"],
            app_state["classifier"],
            app_state["tracer"],
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