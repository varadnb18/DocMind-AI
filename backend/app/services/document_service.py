import logging
from typing import Dict, Any, List
from fastapi import UploadFile, HTTPException
import time
from app.services.document_processor import DocumentProcessorFactory
from app.services.text_processor import TextProcessor
from app.services.embedding_manager import EmbeddingManager
from app.db.vectordb import FAISSManager
from app.db.postgres import PostgresManager
from app.services.llm_service import llm_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.text_processor = TextProcessor()
        self.embedding_manager = EmbeddingManager()
        self.postgres_db = PostgresManager()

    def _get_vector_db(self, user_id: int) -> FAISSManager:
        return FAISSManager(self.embedding_manager.get_dimension(), user_id)

    async def process_upload(self, file: UploadFile, user_id: int) -> Dict[str, Any]:
        logger.info(f"Processing uploaded file: {file.filename} for user {user_id}")
        try:
            content = await file.read()
            processor = DocumentProcessorFactory.get_processor(file.filename)
            text = processor.extract_text(content)

            if not text.strip():
                raise HTTPException(status_code=400, detail="No text content extracted")

            # Store Document
            doc_id = self.postgres_db.store_document(
                user_id=user_id,
                filename=file.filename,
                file_type=processor.get_file_type(),
                file_size=len(content),
                metadata={"original_length": len(text)}
            )

            # Preprocess and Chunk
            sections = self.text_processor.categorize_and_partition_document(
                text, metadata={"filename": file.filename, "document_id": doc_id}
            )
            
            if not sections:
                raise HTTPException(status_code=400, detail="No chunks generated")

            # Embeddings and FAISS
            texts = [s.content for s in sections]
            embs = self.embedding_manager.generate_embeddings(texts)
            
            meta_list = []
            for i, s in enumerate(sections):
                m = s.metadata.copy()
                m.update({
                    'document_id': doc_id,
                    'chunk_index': i,
                    'category': s.category,
                    'importance_score': s.importance_score
                })
                meta_list.append(m)
                
            vector_db = self._get_vector_db(user_id)
            vec_ids = vector_db.add_vectors_with_categories(embs, meta_list)

            # Store chunks in Postgres
            enhanced_chunks = [
                {
                    'content': s.content,
                    'category': s.category,
                    'importance_score': s.importance_score,
                    'metadata': s.metadata,
                    'vector_id': vec_ids[i]
                }
                for i, s in enumerate(sections)
            ]
            self.postgres_db.store_enhanced_chunks(doc_id, enhanced_chunks)
            self.postgres_db.mark_document_processed(doc_id)

            return {
                "document_id": doc_id,
                "chunks_created": len(sections),
                "status": "success"
            }
        except Exception as e:
            logger.exception("Upload processing failed")
            raise HTTPException(status_code=500, detail=str(e))

    def get_all_documents(self, user_id: int):
        return self.postgres_db.get_all_documents(user_id)

    def delete_document(self, doc_id: int, user_id: int):
        try:
            self.postgres_db.delete_document(doc_id, user_id)
            return {"status": "success", "message": f"Document {doc_id} deleted"}
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise HTTPException(status_code=500, detail=str(e))

document_service = DocumentService()
