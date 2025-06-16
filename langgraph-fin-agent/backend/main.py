from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import logging
import os
import asyncio
from contextlib import asynccontextmanager

# Set up environment
import dotenv
dotenv.load_dotenv()

from langgraph_fin_agent.graph import build_app
from langchain_core.messages import HumanMessage
from backend.utils.env_manager import EnvironmentManager, validate_env_overrides
from backend.utils.session_manager import SessionManager
from langgraph_fin_agent.flexible_instrumentation import (
    get_instrumentation_manager,
    TracerConfig,
    setup_flexible_instrumentation
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session manager
session_manager = SessionManager(cache_ttl_minutes=30)

def has_valid_arize_config(env_overrides: Optional[Dict[str, str]] = None) -> tuple[bool, Dict[str, str]]:
    """
    Check if we have valid Arize configuration either from overrides or environment.
    
    Returns:
        tuple: (has_valid_config, effective_config_dict)
    """
    effective_config = {}
    
    # Helper function to get non-empty value
    def get_non_empty_value(override_key: str, env_key: str, default: str = '') -> str:
        if env_overrides and override_key in env_overrides:
            override_val = env_overrides.get(override_key, '').strip()
            if override_val:
                return override_val
        return os.getenv(env_key, default).strip()
    
    # Get effective values
    effective_config['space_id'] = get_non_empty_value('ARIZE_SPACE_ID', 'ARIZE_SPACE_ID')
    effective_config['api_key'] = get_non_empty_value('ARIZE_API_KEY', 'ARIZE_API_KEY')
    effective_config['model_id'] = get_non_empty_value('ARIZE_MODEL_ID', 'ARIZE_MODEL_ID', 'langgraph_finance_agent')
    
    # Check if we have the required values
    has_valid = bool(effective_config['space_id'] and effective_config['api_key'])
    
    return has_valid, effective_config

def initialize_langgraph_app(env_overrides: Optional[Dict[str, str]] = None):
    """Initialize the LangGraph application components with optional environment overrides."""
    # For now, disable caching to ensure proper instrumentation reconfiguration
    # TODO: Implement smarter caching that handles instrumentation state properly
    # cached_components = session_manager.get_cached_components(env_overrides)
    # if cached_components:
    #     logger.info("Using cached LangGraph components for this configuration")
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
                space_id=arize_config['space_id'],
                api_key=arize_config['api_key'],
                model_id=arize_config['model_id'],
                use_env_headers=True  # Use environment variable headers for compatibility
            )
            tracer_provider = manager.configure(config)
            
            # Determine source of configuration for logging
            has_overrides = env_overrides and any(
                key.startswith('ARIZE_') and env_overrides.get(key, '').strip()
                for key in env_overrides.keys()
            )
            source = "overrides + environment fallback" if has_overrides else "environment variables"
            logger.info(f"Using Arize configuration from {source}: model_id={arize_config['model_id']}")
        else:
            # No valid Arize configuration available
            logger.warning("No valid Arize configuration found (missing ARIZE_SPACE_ID or ARIZE_API_KEY)")
            logger.info("Instrumentation will be set up but may not export traces successfully")
            # Still set up instrumentation with whatever we have (might be empty/test config)
            tracer_provider = setup_flexible_instrumentation()
        
        tracer = tracer_provider.get_tracer("langgraph_fin_agent")
        
        # Initialize LangGraph app with current environment
        langgraph_app = build_app()
        
        # Create components dictionary
        components = {
            "langgraph_app": langgraph_app,
            "tracer": tracer
        }
        
        # Cache the components - disabled for now to ensure proper reconfiguration
        # session_manager.cache_components(env_overrides, components)
        
        logger.info(f"LangGraph Finance Agent initialized successfully with env_overrides: {list(env_overrides.keys()) if env_overrides else 'default'}")
        
        return components
        
    except Exception as e:
        logger.error(f"Failed to initialize LangGraph app: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Initialize with default environment
    default_components = initialize_langgraph_app()
    # Store default components in app_state for backward compatibility
    app_state.update(default_components)
    app_state["initialized"] = True
    app.state.default_components = default_components
    logger.info("LangGraph Finance Agent initialized successfully")
    yield
    # Shutdown
    session_manager.clear_cache()
    logger.info("Application shutting down")

app = FastAPI(title="LangGraph Finance Agent API", lifespan=lifespan)

# Get allowed origins from environment variable or use default
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize app state for backward compatibility
app_state = {
    "initialized": False,
    "langgraph_app": None,
    "tracer": None
}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    env_overrides: Optional[Dict[str, str]] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class FinanceQueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None
    env_overrides: Optional[Dict[str, str]] = None

class FinanceQueryResponse(BaseModel):
    result: Any
    thread_id: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a finance chat message and return the response."""
    # Validate and filter environment overrides
    env_overrides = validate_env_overrides(request.env_overrides)
    
    # Use temporary environment variables if provided
    with EnvironmentManager.temporary_env_vars(env_overrides):
        # Initialize or get cached components for this environment configuration
        components = initialize_langgraph_app(env_overrides)
        langgraph_app = components["langgraph_app"]
        
        session_id = request.session_id or str(uuid.uuid4())
        
        try:
            # Create inputs for the graph
            inputs = {"messages": [HumanMessage(content=request.message)]}
            config = {"configurable": {"thread_id": session_id}}
            
            # Process the message through the graph
            response_content = ""
            async for chunk in langgraph_app.astream(inputs, config, stream_mode="values"):
                if "messages" in chunk and len(chunk["messages"]) > 0:
                    last_message = chunk["messages"][-1]
                    response_content = last_message.content
            
            return ChatResponse(
                response=response_content,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Error processing chat request: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/finance-query", response_model=FinanceQueryResponse)
async def finance_query(request: FinanceQueryRequest):
    """Process a finance query and return detailed results."""
    # Validate and filter environment overrides
    env_overrides = validate_env_overrides(request.env_overrides)
    
    # Use temporary environment variables if provided
    with EnvironmentManager.temporary_env_vars(env_overrides):
        # Initialize or get cached components for this environment configuration
        components = initialize_langgraph_app(env_overrides)
        langgraph_app = components["langgraph_app"]
        
        thread_id = request.thread_id or str(uuid.uuid4())
        
        try:
            # Create inputs for the graph
            inputs = {"messages": [HumanMessage(content=request.query)]}
            config = {"configurable": {"thread_id": thread_id}}
            
            # Process the query through the graph
            final_result = None
            async for chunk in langgraph_app.astream(inputs, config, stream_mode="values"):
                final_result = chunk
            
            return FinanceQueryResponse(
                result=final_result,
                thread_id=thread_id
            )
            
        except Exception as e:
            logger.error(f"Error processing finance query: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "initialized": app_state["initialized"], "service": "langgraph-finance-agent"}

@app.get("/api/status")
async def status():
    """Get the status of the finance agent service."""
    try:
        # Check if components are available
        has_default_components = hasattr(app.state, 'default_components') and app.state.default_components is not None
        
        return {
            "status": "ready" if has_default_components else "initializing",
            "components_available": has_default_components,
            "service": "langgraph-finance-agent",
            "cache_stats": {
                "cached_configurations": len(session_manager._cache)
            }
        }
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        return {"status": "error", "error": str(e)}

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
            "space_id_present": bool(arize_config.get('space_id')),
            "api_key_present": bool(arize_config.get('api_key')),
            "model_id": arize_config.get('model_id', 'not_set'),
        }
        
        # Check environment variables
        environment_vars = {
            "OPENAI_API_KEY_set": bool(os.getenv("OPENAI_API_KEY")),
            "ARIZE_API_KEY_set": bool(os.getenv("ARIZE_API_KEY")),
            "ARIZE_SPACE_ID_set": bool(os.getenv("ARIZE_SPACE_ID")),
            "ARIZE_MODEL_ID": os.getenv("ARIZE_MODEL_ID", "not_set"),
            "FMP_API_KEY_set": bool(os.getenv("FMP_API_KEY")),
        }
        
        # Cache information
        cache_info = {
            "total_cached_configs": len(session_manager._cache),
            "cache_ttl_minutes": session_manager._cache_ttl.seconds // 60,
        }
        
        return {
            "instrumentation": instrumentation_status,
            "arize_config": safe_config,
            "environment_vars": environment_vars,
            "cache_info": cache_info,
            "service": "langgraph-finance-agent"
        }
    except Exception as e:
        return {"error": str(e), "status": "debug_failed"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port) 