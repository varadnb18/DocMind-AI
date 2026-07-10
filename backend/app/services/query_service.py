import logging
from typing import Dict, Any, List
from app.services.embedding_manager import EmbeddingManager
from app.db.vectordb import FAISSManager
from app.db.postgres import PostgresManager
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class QueryService:
    def __init__(self):
        self.embedding_manager = EmbeddingManager()
        self.postgres_db = PostgresManager()

    def _get_vector_db(self, user_id: int) -> FAISSManager:
        return FAISSManager(self.embedding_manager.get_dimension(), user_id)

    def process_query(self, query: str, user_id: int, top_k: int = 5) -> Dict[str, Any]:
        logger.info(f"Processing query: {query} for user {user_id}")
        try:
            # 1. Embed Query
            query_embedding = self.embedding_manager.generate_query_embedding(query)

            # 2. Search FAISS
            vector_db = self._get_vector_db(user_id)
            scores, vector_ids = vector_db.search(query_embedding, k=top_k)

            if not vector_ids or vector_ids[0] == -1:
                return {"error": "No relevant documents found"}

            # 3. Retrieve Chunks
            valid_vector_ids = [vid for vid in vector_ids if vid != -1]
            chunks = self.postgres_db.get_chunks_by_vector_ids(valid_vector_ids, user_id)

            if not chunks:
                return {"error": "No matching document chunks found"}

            # 4. Context Preparation
            context_parts = []
            for chunk, score in zip(chunks[:top_k], scores[:len(chunks)]):
                context_parts.append(
                    f"Source: {chunk['filename']}\n"
                    f"Content: {chunk['content']}\n"
                )
            context = "\n---\n".join(context_parts)

            # 5. Generate Answer (using Multi-LLM fallback)
            answer, provider = llm_service.generate_answer(query, context)

            # 6. Format response
            sources = [
                {
                    "filename": chunk["filename"],
                    "content": chunk["content"],
                    "score": float(score)
                }
                for chunk, score in zip(chunks, scores[:len(chunks)])
            ]
            
            # Optionally store query result
            self.postgres_db.store_query_result(user_id, query, sources)

            return {
                "query": query,
                "answer": answer,
                "provider_used": provider,
                "sources": sources
            }
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise

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
