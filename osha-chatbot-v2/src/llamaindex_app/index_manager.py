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
from llama_index.llms.azure_openai import AzureOpenAI as LlamaAzureOpenAI
from phoenix.trace import suppress_tracing
from tenacity import retry, stop_after_attempt, wait_exponential
from .config import Settings

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
        """Configure LlamaIndex settings for Azure OpenAI."""
        # Set the embedding model
        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5"
        )
        
        # Set chunking parameters
        LlamaSettings.chunk_size = self.settings.CHUNK_SIZE
        LlamaSettings.chunk_overlap = self.settings.CHUNK_OVERLAP
        
        # Configure Azure OpenAI for LlamaIndex if needed
        if self.openai_client:
            try:
                # Configure LlamaIndex to use Azure OpenAI
                LlamaSettings.llm = LlamaAzureOpenAI(
                    model=self.settings.AZURE_OPENAI_MODEL,
                    deployment_name=self.settings.AZURE_OPENAI_DEPLOYMENT,
                    api_key=self.settings.AZURE_OPENAI_API_KEY,  # Will be None for VPN auth
                    azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
                    api_version=self.settings.AZURE_OPENAI_API_VERSION,
                )
                logger.info("Azure OpenAI LLM configured for LlamaIndex")
            except ImportError:
                logger.warning("Could not import AzureOpenAI from llama_index. Make sure llama-index-llms-azure-openai is installed.")
                logger.warning("To install: pip install llama-index-llms-azure-openai")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def load_or_create_index(self):
        #kb_file = self.storage_path / "osha100.json"
        index_exists = self.storage_path.exists() and any(self.storage_path.iterdir())

        if index_exists:
            logger.info("Loading existing index from storage...")
            storage_context = StorageContext.from_defaults(
                persist_dir=str(self.storage_path)
            )
            return load_index_from_storage(storage_context)

        if not self.storage_path.exists():
            self.storage_path.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Creating new index from documents in {self.settings.DATA_PATH}...")
            documents = SimpleDirectoryReader(
                input_dir=self.settings.DATA_PATH
            ).load_data()
            
            logger.info(f"Loaded {len(documents)} documents, creating index...")
            index = VectorStoreIndex.from_documents(documents, settings=LlamaSettings)
            
            logger.info("Persisting index to storage...")
            index.storage_context.persist(persist_dir=str(self.storage_path))
            
            return index
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise

    def get_query_engine(self):
        retriever = self.index.as_retriever(similarity_top_k=3)
        return QueryEngine(retriever=retriever)