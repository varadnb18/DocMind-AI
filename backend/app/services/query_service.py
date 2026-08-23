import logging
import numpy as np
from typing import Dict, Any, List
from app.services.embedding_manager import EmbeddingManager
from app.db.vectordb import FAISSManager
from app.db.postgres import PostgresManager
from app.services.llm_service import llm_service
from app.services.retriever import CustomFAISSRetriever

logger = logging.getLogger(__name__)

class QueryService:
    def __init__(self):
        self.embedding_manager = EmbeddingManager()
        self.postgres_db = PostgresManager()

    def _get_vector_db(self, user_id: int) -> FAISSManager:
        vector_db = FAISSManager(self.embedding_manager.get_dimension(), user_id)
        # If FAISS is empty after restart, rebuild from PostgreSQL
        if vector_db.get_total_vectors() == 0:
            self._rebuild_faiss(vector_db, user_id)
        return vector_db

    def _rebuild_faiss(self, vector_db: FAISSManager, user_id: int):
        """Rebuild FAISS index from embeddings stored in PostgreSQL"""
        chunks = self.postgres_db.get_chunks_with_embeddings(user_id)
        if not chunks:
            return
        logger.info(f"Rebuilding FAISS index for user {user_id} from {len(chunks)} stored embeddings")
        embeddings = np.array([np.frombuffer(bytes(c['embedding']), dtype=np.float32) for c in chunks])
        metadata_list = [{
            'document_id': c['document_id'],
            'chunk_index': c['chunk_index'],
            'category': c.get('category', 'general'),
            'importance_score': c.get('importance_score', 0.5),
            'filename': c.get('filename', ''),
        } for c in chunks]
        new_ids = vector_db.rebuild_from_stored(embeddings, metadata_list)
        # Update vector_ids in PostgreSQL to match new FAISS IDs
        updates = [(c['id'], new_id) for c, new_id in zip(chunks, new_ids)]
        self.postgres_db.update_chunk_vector_ids(updates)
        logger.info(f"FAISS rebuild complete for user {user_id}: {len(new_ids)} vectors")

    def process_query(self, query: str, user_id: int, top_k: int = 5, document_id: int = None) -> Dict[str, Any]:
        logger.info(f"Processing query: {query} for user {user_id}, document {document_id}")
        try:
            # 0. Check for Pre-Computed Summary Intent
            query_lower = query.lower().strip()
            summary_keywords = {"summarize", "summary", "overview", "what is this document about", "give me a summary"}
            if document_id and any(kw in query_lower for kw in summary_keywords):
                cached_summary = self.postgres_db.get_document_summary(document_id, user_id)
                if cached_summary:
                    logger.info(f"Serving pre-computed summary for document {document_id}")
                    payload = {
                        "answer": cached_summary,
                        "provider_used": "Pre-Computed Summary (PostgreSQL)",
                        "sources": []
                    }
                    self.postgres_db.store_query_result(user_id, query, payload, document_id)
                    return {
                        "query": query,
                        "answer": cached_summary,
                        "provider_used": "Pre-Computed Summary (PostgreSQL)",
                        "sources": []
                    }

            # 1. Initialize Custom LangChain Retriever
            vector_db = self._get_vector_db(user_id)
            retriever = CustomFAISSRetriever(
                vector_db=vector_db,
                postgres_db=self.postgres_db,
                embedding_manager=self.embedding_manager,
                user_id=user_id,
                k=top_k,
                document_id=document_id
            )

            # 2. Retrieve documents (this handles FAISS and Postgres lookup internally)
            docs = retriever.invoke(query)

            if not docs:
                answer = "I could not find any relevant information in the document to answer your query."
                provider = "System"
                payload = {"answer": answer, "provider_used": provider, "sources": []}
                self.postgres_db.store_query_result(user_id, query, payload, document_id)
                return {
                    "query": query,
                    "answer": answer,
                    "provider_used": provider,
                    "sources": []
                }

            # 3. Generate Answer using LangChain Chat Models
            answer, provider = llm_service.generate_answer(query, docs)

            # 4. Format response
            sources = [
                {
                    "filename": doc.metadata.get("filename", ""),
                    "content": doc.page_content,
                    "score": doc.metadata.get("score", 0.0)
                }
                for doc in docs
            ]
            
            # Store query result with answer, provider, sources & document_id
            payload = {
                "answer": answer,
                "provider_used": provider,
                "sources": sources
            }
            self.postgres_db.store_query_result(user_id, query, payload, document_id)

            return {
                "query": query,
                "answer": answer,
                "provider_used": provider,
                "sources": sources
            }
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise

    def get_document_history(self, user_id: int, document_id: int) -> List[Dict[str, Any]]:
        raw_history = self.postgres_db.get_query_history(user_id, document_id)
        chat_messages = []
        for item in raw_history:
            query = item.get("query")
            results = item.get("results")
            
            answer = ""
            provider = ""
            sources = []

            if isinstance(results, dict):
                answer = results.get("answer", "")
                provider = results.get("provider_used", "")
                sources = results.get("sources", [])
            elif isinstance(results, list):
                sources = results
            
            chat_messages.append({"role": "user", "content": query})
            if answer:
                chat_messages.append({
                    "role": "bot",
                    "content": answer,
                    "provider": provider,
                    "sources": sources
                })
        return chat_messages

    def process_multiple_queries(self, queries: List[str], user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        results = []
        for q in queries:
            try:
                res = self.process_query(q, user_id, top_k)
                results.append(res)
            except Exception as e:
                results.append({
                    "query": q,
                    "answer": f"Error: {str(e)}",
                    "provider_used": "None",
                    "sources": []
                })
        return results

query_service = QueryService()
