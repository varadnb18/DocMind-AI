import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    API_TITLE: str = "DocMind AI API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "AI Document Intelligence Platform"

    FAISS_INDEX_PATH: str = "./data/faiss_index"
    POSTGRES_URL: str

    GROQ_API_KEY: str
    GEMINI_API_KEY: str
    OPENAI_API_KEY: str

    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_TOKENS: int = 2048

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
