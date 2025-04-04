import streamlit as st
import os
import sys
import uuid
import logging
from pathlib import Path

# Configure page first (must be the first Streamlit command)
st.set_page_config(
    page_title="Assurant 10-K Analysis & Risk Assessment App",
    page_icon="📊",
    layout="wide"
)

# Suppress PyTorch warnings that might appear in the console
os.environ['PYTHONWARNINGS'] = 'ignore::RuntimeWarning'

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add project directories to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))  # Add the project root first
logger.info(f"Added project root to path: {project_root}")

# Import the necessary modules using direct imports
try:
    # Use absolute imports based on the project structure
    from src.llamaindex_app.main import init_azure_openai_client, setup_instrumentation, process_interaction
    from src.llamaindex_app.classifier import QueryClassifier
    from src.llamaindex_app.index_manager import IndexManager
    from src.llamaindex_app.config import Settings
    logger.info("Successfully imported all required modules")
except ImportError as e:
    logger.error(f"Import error: {e}")

def init_app():
    """Initialize everything just once using st.session_state."""
    if "initialized" not in st.session_state:
        try:
            st.session_state["initialized"] = True
            logger.info("Starting app initialization")
            
            # Load settings
            settings = Settings()
            st.session_state["settings"] = settings
            
            # (1) instrumentation (if needed)
            with st.spinner("Setting up instrumentation..."):
                tracer_provider = setup_instrumentation()
                st.session_state["tracer"] = tracer_provider.get_tracer("llamaindex_app")
                logger.info("Instrumentation setup complete")

            # (2) azure client
            with st.spinner("Initializing Azure OpenAI client..."):
                azure_client = init_azure_openai_client()
                st.session_state["azure_client"] = azure_client
                # Store deployment name separately
                st.session_state["azure_deployment"] = settings.AZURE_OPENAI_DEPLOYMENT
                logger.info("Azure OpenAI client initialized")

            # (3) index manager & query engine
            with st.spinner("Loading index and query engine..."):
                index_manager = IndexManager(openai_client=azure_client)
                query_engine = index_manager.get_query_engine()
                st.session_state["query_engine"] = query_engine
                logger.info("Index and query engine loaded")

            # (4) classifier
            with st.spinner("Initializing query classifier..."):
                classifier = QueryClassifier(
                    query_engine=query_engine,
                    openai_client=azure_client,
                    deployment=st.session_state["azure_deployment"]  # Use the stored deployment name
                )
                st.session_state["classifier"] = classifier
                logger.info("Query classifier initialized")

            st.session_state["chat_history"] = []  # store chat Q&A pairs
            logger.info("App initialization complete")
            st.success("App initialized successfully!")
            
        except Exception as e:
            st.error(f"Failed to initialize app: {str(e)}")
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            st.session_state["initialization_error"] = str(e)
            return False
        
        return True
    
    return "initialized" in st.session_state and st.session_state["initialized"]

def main():
    """Main Streamlit app function."""
    st.title("Assurant 10-K Analysis & Risk Assessment App")
    
    # Sidebar with app info
    with st.sidebar:
        st.subheader("About this app")
        st.write("""
        This application analyzes Assurant's 10-K reports and provides risk assessment.
        
        You can ask questions about:
        - Assurant's financial performance
        - Risk factors
        - Business operations
        - Market trends
        """)
        
        # Debug section in sidebar
        if st.checkbox("Show debug info"):
            st.subheader("Debug Information")
            st.write("Python Path:")
            for path in sys.path:
                st.write(f"- {path}")
            
            # Display environment variables (without sensitive values)
            st.write("Environment Variables:")
            safe_vars = {
                k: (v if not any(secret in k.lower() for secret in ["key", "secret", "password", "token"]) else "****") 
                for k, v in os.environ.items()
                if k.startswith(("AZURE_", "OPENAI_", "LLAMAINDEX_"))
            }
            for k, v in safe_vars.items():
                st.write(f"- {k}: {v}")
            
            # Also display settings from the Settings class
            if "settings" in st.session_state:
                settings = st.session_state["settings"]
                st.write("App Settings:")
                st.write(f"- Azure Deployment: {settings.AZURE_OPENAI_DEPLOYMENT}")
                st.write(f"- Azure Endpoint: {settings.AZURE_OPENAI_ENDPOINT if settings.AZURE_OPENAI_ENDPOINT else 'Not set'}")
                st.write(f"- Azure API Version: {settings.AZURE_OPENAI_API_VERSION if settings.AZURE_OPENAI_API_VERSION else 'Not set'}")

    # Check if the required modules are properly imported
    if 'src.llamaindex_app.classifier' not in sys.modules:
        st.error("Failed to import required modules. Please check your project structure and try again.")
        st.info("""
        Troubleshooting steps:
        1. Ensure you have proper __init__.py files in src/ and src/llamaindex_app/ directories
        2. Verify that all Python modules are in the correct locations
        3. Check that your imports use absolute paths (src.llamaindex_app.module)
        4. Make sure all requirements are installed
        """)
        return

    # Initialize the app
    initialization_status = init_app()
    
    if initialization_status is False:
        st.error(f"Initialization failed: {st.session_state.get('initialization_error', 'Unknown error')}")
        st.warning("Please check your environment variables and connection settings.")
        return
    
    # Query section
    st.subheader("Ask a question about Assurant's 10-K")
    user_question = st.text_input("Your question:", placeholder="e.g., How did Assurant perform last quarter?")
    submit = st.button("Submit Question")

    if submit and user_question.strip():
        # retrieve references from st.session_state
        query_engine = st.session_state["query_engine"]
        classifier = st.session_state["classifier"]
        tracer = st.session_state["tracer"]

        session_id = str(uuid.uuid4())

        with st.spinner("Analyzing your question..."):
            try:
                # Log the question being processed
                logger.info(f"Processing query: {user_question}")
                
                response, error = process_interaction(
                    query_engine,
                    classifier,
                    tracer,
                    user_question,
                    session_id
                )

                # Store in st.session_state so we can display entire conversation
                if error:
                    st.session_state["chat_history"].append(("user", user_question))
                    st.session_state["chat_history"].append(("assistant", f"Error: {error}"))
                    st.error(f"Error: {error}")
                    logger.error(f"Query processing error: {error}")
                else:
                    st.session_state["chat_history"].append(("user", user_question))
                    st.session_state["chat_history"].append(("assistant", response.response))
                    logger.info("Query processed successfully")

                    # If there are any sources
                    if getattr(response, "source_nodes", None):
                        source_text = "\n".join(
                            f"- {node.metadata.get('file_name', 'Unknown source')}"
                            for node in response.source_nodes
                        )
                        st.session_state["chat_history"].append(("assistant_sources", source_text))
                        logger.info(f"Found {len(response.source_nodes)} source nodes")
            except Exception as e:
                st.error(f"Error processing your question: {str(e)}")
                logger.error(f"Process interaction error: {str(e)}", exc_info=True)
                st.session_state["chat_history"].append(("user", user_question))
                st.session_state["chat_history"].append(("assistant", f"Error processing your question: {str(e)}"))

    # Display the chat history
    st.subheader("Conversation")
    history_container = st.container()
    
    with history_container:
        for idx, (role, content) in enumerate(st.session_state.get("chat_history", [])):
            if role == "user":
                st.markdown(f"**You**: {content}")
            elif role == "assistant":
                st.markdown(f"**Assistant**: {content}")
            elif role == "assistant_sources":
                with st.expander("View Sources"):
                    st.markdown(content)
            
            # Add a separator between conversations
            if idx < len(st.session_state.get("chat_history", [])) - 1 and role == "assistant":
                st.markdown("---")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled exception in main app: {str(e)}", exc_info=True)
        st.error(f"An unexpected error occurred: {str(e)}")
        st.warning("Please check the logs for more details.")