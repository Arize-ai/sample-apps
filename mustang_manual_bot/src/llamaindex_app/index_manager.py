from pathlib import Path
import logging
import os
from datetime import datetime
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings as LlamaSettings,
)
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
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
    def __init__(self, openai_client=None, force_rebuild=False):
        self.settings = Settings()
        self.openai_client = openai_client
        self.force_rebuild = force_rebuild
        with suppress_tracing():
            self._configure_llama_settings()
            self.storage_path = Path(self.settings.STORAGE_DIR)
            self.data_path = self._get_data_path()
            self.index = self.load_or_create_index()

    def _configure_llama_settings(self):
        """Configure LlamaIndex settings for OpenAI."""
        # Configure BGE-small embedding model to match pre-vectorized data
        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5"
        )
        logger.info("Configured BGE-small embedding model for queries")
        
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

    def _get_data_path(self):
        """Get the data directory path."""
        project_root = Path(__file__).parent.parent.parent  # Go up from src/llamaindex_app to the project root
        return project_root / "data"

    def _get_pdf_files(self):
        """Get the list of PDF files to index."""
        filenames = [
            "2016-Mustang-Owners-Manual-version-2_om_EN-US_11_2015.pdf", 
            "2017-Ford-Mustang-Owners-Manual-version-2_om_EN-US_EN-CA_12_2016.pdf", 
            "2018-Ford-Mustang-Owners-Manual-version-3_om_EN-US_03_2018.pdf", 
            "2019-Ford-Mustang-Owners-Manual-version-2_om_EN-US_01_2019.pdf", 
            "2020-Ford-Mustang-Owners-Manual-version-2_om_EN-US_12_2019.pdf", 
            "2021-Ford-Mustang-Owners-Manual-version-2_om_EN-US_03_2021.pdf", 
            "2022-Ford-Mustang-Owners-Manual-version-1_om_EN-US_11_2021.pdf", 
            "2023_Ford_Mustang_Owners_Manual_version_1_om_EN-US.pdf", 
            "2024_Ford_Mustang_Owners_Manual_version_1_om_EN-US.pdf", 
            "2025_MustangS650_OM_ENG_version1.pdf"
        ]
        
        pdf_files = []
        for filename in filenames:
            file_path = self.data_path / filename
            if file_path.exists():
                pdf_files.append(str(file_path))
            else:
                logger.warning(f"PDF file not found: {file_path}")
        
        return pdf_files

    def _index_exists_and_valid(self):
        """Check if a valid index exists in storage."""
        if not self.storage_path.exists():
            logger.info("Storage directory does not exist")
            return False
        
        # Check for required index files
        required_files = ['default__vector_store.json', 'index_store.json', 'docstore.json']
        for file_name in required_files:
            file_path = self.storage_path / file_name
            if not file_path.exists():
                logger.info(f"Required index file missing: {file_name}")
                return False
            if file_path.stat().st_size == 0:
                logger.info(f"Required index file is empty: {file_name}")
                return False
        
        logger.info("Valid index files found in storage")
        return True

    def _should_rebuild_index(self):
        """Determine if the index should be rebuilt based on file modifications."""
        if self.force_rebuild:
            logger.info("Force rebuild requested")
            return True
        
        if not self._index_exists_and_valid():
            logger.info("Index does not exist or is invalid, rebuild required")
            return True
        
        # Check if any source files are newer than the index
        try:
            # Get the oldest modification time of index files
            index_files = ['default__vector_store.json', 'index_store.json', 'docstore.json']
            oldest_index_time = None
            
            for file_name in index_files:
                file_path = self.storage_path / file_name
                if file_path.exists():
                    file_time = file_path.stat().st_mtime
                    if oldest_index_time is None or file_time < oldest_index_time:
                        oldest_index_time = file_time
            
            if oldest_index_time is None:
                logger.info("Could not determine index modification time, rebuilding")
                return True
            
            # Check if any PDF files are newer than the index
            pdf_files = self._get_pdf_files()
            for pdf_file in pdf_files:
                pdf_path = Path(pdf_file)
                if pdf_path.exists():
                    pdf_time = pdf_path.stat().st_mtime
                    if pdf_time > oldest_index_time:
                        logger.info(f"PDF file {pdf_file} is newer than index, rebuild required")
                        return True
            
            logger.info("Index is up to date, no rebuild required")
            return False
        
        except Exception as e:
            logger.warning(f"Error checking file modification times: {e}, rebuilding index")
            return True

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def load_or_create_index(self):
        """Load existing index or create new one if necessary."""
        
        # Check if we should rebuild the index
        if not self._should_rebuild_index():
            try:
                logger.info("Loading existing index from storage...")
                storage_context = StorageContext.from_defaults(
                    persist_dir=str(self.storage_path)
                )
                index = load_index_from_storage(storage_context)
                logger.info("Successfully loaded existing index")
                return index
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}")
                logger.info("Will create new index instead")
        
        # Create new index
        return self._create_new_index()

    def _create_new_index(self):
        """Create a new index from PDF files."""
        logger.info("Creating new index from PDF files...")
        
        # Ensure storage directory exists
        if not self.storage_path.exists():
            self.storage_path.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Using data path: {self.data_path}")
            
            # Get PDF files
            pdf_files = self._get_pdf_files()
            
            if not pdf_files:
                raise ValueError("No PDF files found to index")
            
            logger.info(f"Found {len(pdf_files)} PDF files to index")
            for pdf_file in pdf_files:
                logger.info(f"  - {Path(pdf_file).name}")
            
            # Load documents
            documents = SimpleDirectoryReader(
                input_files=pdf_files
            ).load_data()
            
            logger.info(f"Loaded {len(documents)} documents, creating index...")
            index = VectorStoreIndex.from_documents(documents, settings=LlamaSettings)
            
            logger.info("Persisting index to storage...")
            index.storage_context.persist(persist_dir=str(self.storage_path))
            
            logger.info("Index created and persisted successfully")
            return index
            
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise

    def get_query_engine(self):
        retriever = self.index.as_retriever(similarity_top_k=3)
        return QueryEngine(retriever=retriever)

    def rebuild_index(self):
        """Force rebuild the index."""
        logger.info("Forcing index rebuild...")
        self.force_rebuild = True
        self.index = self._create_new_index()
        self.force_rebuild = False
        logger.info("Index rebuild completed")
        return self.index
