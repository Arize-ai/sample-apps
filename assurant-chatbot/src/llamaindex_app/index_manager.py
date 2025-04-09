from pathlib import Path
import logging
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings as LlamaSettings,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from phoenix.trace import suppress_tracing
from tenacity import retry, stop_after_attempt, wait_exponential
from src.llamaindex_app.config import Settings

logger = logging.getLogger(__name__)


class QueryEngine:
    def __init__(self, retriever):
        self.retriever = retriever

    def retrieve(self, query: str):
        return self.retriever.retrieve(query)


class IndexManager:
    def __init__(self, openai_client=None):
        self.settings = Settings()
        self.openai_client = openai_client
        with suppress_tracing():
            self._configure_llama_settings()
            self.storage_path = Path(self.settings.STORAGE_DIR)
            self.index = self.load_or_create_index()

    def _configure_llama_settings(self):
        """Configure LlamaIndex settings for OpenAI."""
        # Set the embedding model
        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5"
        )
        
        # Set chunking parameters
        LlamaSettings.chunk_size = self.settings.CHUNK_SIZE
        LlamaSettings.chunk_overlap = self.settings.CHUNK_OVERLAP
        
        # Configure OpenAI for LlamaIndex if needed
        if self.openai_client:
            try:
                # Configure LlamaIndex to use OpenAI
                LlamaSettings.llm = LlamaOpenAI(
                    model=self.settings.OPENAI_MODEL,
                    api_key=self.settings.OPENAI_API_KEY
                )
                logger.info("OpenAI LLM configured for LlamaIndex")
            except ImportError:
                logger.warning("Could not import OpenAI from llama_index. Make sure llama-index-llms-openai is installed.")
                logger.warning("To install: pip install llama-index-llms-openai")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def load_or_create_index(self):
        if not self.storage_path.exists():
            self.storage_path.mkdir(parents=True, exist_ok=True)
        elif any(self.storage_path.iterdir()):
            # Clear existing index files if they exist
            logger.info("Removing existing index...")
            for file in self.storage_path.iterdir():
                file.unlink()
        
        try:
            logger.info("Creating new index from specific PDF files...")
            
            # Determine the correct data path
            project_root = Path(__file__).parent.parent.parent  # Go up from src/llamaindex_app to the project root
            data_path = project_root / "data"
            
            logger.info(f"Using data path: {data_path}")
            
            # Specify exact filenames
            filenames = ["AIZ 10K - 2023.pdf", "AIZ 10K - 2024.pdf"]
            
            # Check if files exist
            pdf_files = []
            for filename in filenames:
                file_path = data_path / filename
                logger.info(f"Checking for file: {file_path}")
                if file_path.exists():
                    pdf_files.append(str(file_path))
                    logger.info(f"File found: {file_path}")
                else:
                    logger.error(f"File not found: {file_path}")
                    # List files in the data directory to help debug
                    if data_path.exists():
                        logger.info(f"Files in data directory: {[f.name for f in data_path.iterdir() if f.is_file()]}")
                    else:
                        logger.error(f"Data directory does not exist: {data_path}")
            
            # If we found at least one file, create index with what we have
            if pdf_files:
                documents = SimpleDirectoryReader(
                    input_files=pdf_files
                ).load_data()
                
                logger.info(f"Loaded {len(documents)} documents, creating index...")
                index = VectorStoreIndex.from_documents(documents, settings=LlamaSettings)
                
                logger.info("Persisting index to storage...")
                index.storage_context.persist(persist_dir=str(self.storage_path))
                
                return index
            else:
                # If no files found, create a minimal index with a placeholder document
                logger.warning("No PDF files found, creating minimal index with placeholder")
                from llama_index.core.schema import Document
                placeholder_doc = Document(text="No Assurant 10-K data available. This is a placeholder index.")
                index = VectorStoreIndex.from_documents([placeholder_doc], settings=LlamaSettings)
                index.storage_context.persist(persist_dir=str(self.storage_path))
                return index
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise

    def get_query_engine(self):
        retriever = self.index.as_retriever(similarity_top_k=3)
        return QueryEngine(retriever=retriever)