import logging
import numpy as np
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

    def process_query(self, query: str, user_id: int, top_k: int = 5) -> Dict[str, Any]:
        logger.info(f"Processing query: {query} for user {user_id}")
        try:
            # 1. Embed Query
            query_embedding = self.embedding_manager.generate_query_embedding(query)

            # 2. Search FAISS (request more in case some docs were deleted)
            vector_db = self._get_vector_db(user_id)
            scores, vector_ids = vector_db.search(query_embedding, k=top_k * 4)

            if not vector_ids or vector_ids[0] == -1:
                return {"error": "No relevant documents found"}

            # 3. Retrieve Chunks
            valid_vector_ids = [vid for vid in vector_ids if vid != -1]
            chunks_from_db = self.postgres_db.get_chunks_by_vector_ids(valid_vector_ids, user_id)

            if not chunks_from_db:
                return {"error": "No matching document chunks found in database (they may have been deleted). Please upload your document again."}

            # Map chunks back to their FAISS scores and sort by score
            chunk_map = {chunk['vector_id']: chunk for chunk in chunks_from_db}
            
            valid_chunks = []
            valid_scores = []
            for vid, score in zip(valid_vector_ids, scores):
                if vid in chunk_map:
                    valid_chunks.append(chunk_map[vid])
                    valid_scores.append(score)
                    if len(valid_chunks) == top_k:
                        break
            
            if not valid_chunks:
                return {"error": "No valid chunks found after filtering."}

            # 4. Context Preparation
            context_parts = []
            for chunk, score in zip(valid_chunks, valid_scores):
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
                for chunk, score in zip(valid_chunks, valid_scores)
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
