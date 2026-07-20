import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "https://docmind-ai-backend-9wow.onrender.com",
        "https://doc-mind-ai-henna.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
async def rebuild_faiss_on_startup():
    """Rebuild FAISS indexes from PostgreSQL if local files were lost (e.g., Render restart)."""
    try:
        from app.services.query_service import query_service
        user_ids = query_service.postgres_db.get_all_user_ids()
        if not user_ids:
            logger.info("No users found, skipping FAISS rebuild")
            return
        
        for user_id in user_ids:
            from app.db.vectordb import FAISSManager
            vector_db = FAISSManager(query_service.embedding_manager.get_dimension(), user_id)
            if vector_db.get_total_vectors() == 0:
                query_service._rebuild_faiss(vector_db, user_id)
            else:
                logger.info(f"FAISS index for user {user_id} already has {vector_db.get_total_vectors()} vectors")
    except Exception as e:
        logger.error(f"FAISS rebuild on startup failed: {e}")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
