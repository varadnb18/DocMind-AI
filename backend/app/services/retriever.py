from typing import List, Any
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import Field
from app.db.vectordb import FAISSManager
from app.db.postgres import PostgresManager
from app.services.embedding_manager import EmbeddingManager
import logging

logger = logging.getLogger(__name__)

class CustomFAISSRetriever(BaseRetriever):
    """
    Custom LangChain Retriever that wraps our existing FAISS + PostgreSQL architecture.
    This allows us to use `retriever.invoke(query)` while keeping our persistence logic 100% intact.
    """
    
    vector_db: Any = Field(description="The FAISSManager instance")
    postgres_db: Any = Field(description="The PostgresManager instance")
    embedding_manager: Any = Field(description="The EmbeddingManager instance")
    user_id: int = Field(description="The user ID to restrict search to")
    k: int = Field(default=5, description="Number of documents to return")
    document_id: Any = Field(default=None, description="Optional document ID to restrict search to")

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        
        logger.info(f"CustomFAISSRetriever: searching for '{query}' (user_id={self.user_id}, k={self.k})")
        
        # 1. Embed Query
        query_embedding = self.embedding_manager.generate_query_embedding(query)

        # 2. Search FAISS (request more if filtering by a specific document to ensure we find its chunks)
        search_k = self.k * 20 if self.document_id else self.k * 4
        scores, vector_ids = self.vector_db.search(query_embedding, k=search_k)

        if not vector_ids or vector_ids[0] == -1:
            return []

        # 3. Retrieve Chunks from Postgres (filters by user_id and optionally document_id)
        valid_vector_ids = [vid for vid in vector_ids if vid != -1]
        chunks_from_db = self.postgres_db.get_chunks_by_vector_ids(valid_vector_ids, self.user_id, self.document_id)

        if not chunks_from_db:
            return []

        # Map chunks back to their FAISS scores and sort by score
        chunk_map = {chunk['vector_id']: chunk for chunk in chunks_from_db}
        
        valid_chunks = []
        valid_scores = []
        for vid, score in zip(valid_vector_ids, scores):
            if vid in chunk_map:
                valid_chunks.append(chunk_map[vid])
                valid_scores.append(score)
                if len(valid_chunks) == self.k:
                    break

        if not valid_chunks:
            return []

        # 4. Convert to LangChain Documents
        documents = []
        for chunk, score in zip(valid_chunks, valid_scores):
            metadata = {
                **(chunk.get('metadata') or {}),
                "filename": chunk.get("filename"),
                "category": chunk.get("category"),
                "importance_score": chunk.get("importance_score"),
                "score": float(score)
            }
            doc = Document(page_content=chunk["content"], metadata=metadata)
            documents.append(doc)

        return documents
