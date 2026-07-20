# embeddings/embedding_manager.py
import numpy as np
from typing import List, Union
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmbeddingManager:
    def __init__(self):
        self.model_name = "models/gemini-embedding-001"
        self.dimension = 3072  # Gemini embedding dimension is 3072
        
        self.embeddings_client = GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=settings.GEMINI_API_KEY,
            task_type="retrieval_document"
        )
        self.query_client = GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=settings.GEMINI_API_KEY,
            task_type="retrieval_query"
        )

    def generate_embeddings(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Generate embeddings using LangChain GoogleGenerativeAIEmbeddings"""
        if isinstance(texts, str):
            texts = [texts]

        try:
            embeddings = self.embeddings_client.embed_documents(texts)
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Error generating embedding for texts: {str(e)}")
            # Return zero vectors as fallback
            return np.array([[0.0] * self.dimension for _ in texts])

    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for query text using LangChain"""
        try:
            embedding = self.query_client.embed_query(query)
            return np.array([embedding])
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            return np.array([[0.0] * self.dimension])

    def get_dimension(self) -> int:
        return self.dimension