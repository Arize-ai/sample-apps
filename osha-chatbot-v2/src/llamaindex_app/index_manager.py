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
    def __init__(self, bedrock_client=None):
        self.settings = Settings()
        self.bedrock_client = bedrock_client
        with suppress_tracing():
            self._configure_llama_settings()
            self.storage_path = Path(self.settings.STORAGE_DIR)
            self.index = self.load_or_create_index()

    def _configure_llama_settings(self):
        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5"
        )
        LlamaSettings.chunk_size = self.settings.CHUNK_SIZE
        LlamaSettings.chunk_overlap = self.settings.CHUNK_OVERLAP

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def load_or_create_index(self):
        kb_file = self.storage_path / "osha100.json"

        if kb_file.exists():
            storage_context = StorageContext.from_defaults(
                persist_dir=str(self.storage_path)
            )
            return load_index_from_storage(storage_context)

        if not self.storage_path.exists():
            self.storage_path.mkdir(parents=True, exist_ok=True)

        try:
            documents = SimpleDirectoryReader(
                input_dir=self.settings.DATA_PATH
            ).load_data()
            index = VectorStoreIndex.from_documents(documents, settings=LlamaSettings)
            index.storage_context.persist(persist_dir=str(self.storage_path))
            return index
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise

    def get_query_engine(self):
        retriever = self.index.as_retriever(similarity_top_k=3)
        return QueryEngine(retriever=retriever)


# previous llama abstraction for Bedrock
# from llama_index.core import (
#     SimpleDirectoryReader,
#     VectorStoreIndex,
#     StorageContext,
#     load_index_from_storage,
#     Settings as LlamaSettings,
# )
# from llama_index.llms.bedrock import Bedrock
# from llama_index.embeddings.huggingface import HuggingFaceEmbedding
# from pathlib import Path
# import logging
# from .config import Settings
# from phoenix.trace import suppress_tracing
# from tenacity import retry, stop_after_attempt, wait_exponential
# import httpx

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# class IndexManager:
#     def __init__(self, bedrock_client=None):
#         self.settings = Settings()
#         self.bedrock_client = bedrock_client
#         with suppress_tracing():
#             self._configure_llama_settings()
#             self.storage_path = Path(self.settings.STORAGE_DIR)
#             self.index = self.load_or_create_index()

#     def _configure_llama_settings(self):
#         client = httpx.Client(
#             timeout=httpx.Timeout(
#                 connect=5.0,
#                 read=30.0,
#                 write=30.0,
#                 pool=30.0,
#             )
#         )

#         logger.info("Configuring Bedrock models...")
#         LlamaSettings.llm = Bedrock(
#             client=self.bedrock_client,
#             model=self.settings.MODEL,
#             context_size=200000,
#         )

#         LlamaSettings.embed_model = HuggingFaceEmbedding(
#             model_name="BAAI/bge-small-en-v1.5"
#         )

#         LlamaSettings.chunk_size = self.settings.CHUNK_SIZE
#         LlamaSettings.chunk_overlap = self.settings.CHUNK_OVERLAP

#     @retry(
#         stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
#     )
#     def load_or_create_index(self):
#         kb_file = self.storage_path / "osha100.json"  # change me for different docs

#         if kb_file.exists():
#             logger.info("Loading existing index from documents...")
#             storage_context = StorageContext.from_defaults(
#                 persist_dir=str(self.storage_path)
#             )
#             return load_index_from_storage(storage_context)

#         logger.info("Creating new index...")
#         if not self.storage_path.exists():
#             self.storage_path.mkdir(parents=True, exist_ok=True)

#         try:
#             documents = SimpleDirectoryReader(
#                 input_dir=self.settings.DATA_PATH
#             ).load_data()

#             logger.info(f"Loaded {len(documents)} documents, creating index...")

#             index = VectorStoreIndex.from_documents(documents, settings=LlamaSettings)

#             logger.info("Persisting index...")
#             index.storage_context.persist(persist_dir=str(self.storage_path))

#             return index

#         except Exception as e:
#             logger.error(f"Error creating index: {str(e)}")
#             raise

#     def get_query_engine(self):
#         return self.index.as_query_engine(streaming=False, propagate_trace_context=True)
