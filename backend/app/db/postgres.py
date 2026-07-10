import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import json
import numpy as np
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class PostgresManager:
    def __init__(self):
        self.postgres_url = settings.POSTGRES_URL
        logger.info("Initializing PostgresManager with URL")
        self.init_tables()

    def get_connection(self):
        conn = psycopg2.connect(
            self.postgres_url,
            client_encoding='utf8'
        )
        conn.set_client_encoding('UTF8')
        return conn

    def _convert_numpy_types(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        return obj

    def init_tables(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Create users table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(255) UNIQUE NOT NULL,
                            hashed_password VARCHAR(255) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Create documents table with user_id
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS documents (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                            filename VARCHAR(255),
                            document_url TEXT,
                            file_type VARCHAR(50) NOT NULL,
                            file_size INTEGER,
                            categories JSONB,
                            processing_time FLOAT,
                            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            processed BOOLEAN DEFAULT FALSE,
                            metadata JSONB
                        )
                    """)

                    # Create document_chunks table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS document_chunks (
                            id SERIAL PRIMARY KEY,
                            document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                            chunk_index INTEGER NOT NULL,
                            content TEXT NOT NULL,
                            category VARCHAR(100),
                            importance_score FLOAT,
                            metadata JSONB,
                            vector_id INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Create query_results table with user_id
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS query_results (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                            query TEXT NOT NULL,
                            results JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    conn.commit()
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error("Error initializing tables: %s", e, exc_info=True)
            raise

    # --- User Methods ---
    
    def create_user(self, username: str, hashed_password: str) -> int:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO users (username, hashed_password)
                        VALUES (%s, %s)
                        RETURNING id
                    """, (username, hashed_password))
                    user_id = cur.fetchone()[0]
                    conn.commit()
            return user_id
        except Exception as e:
            logger.error("Failed to create user: %s", e)
            raise

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                    return cur.fetchone()
        except Exception as e:
            logger.error("Failed to get user: %s", e)
            raise

    # --- Document Methods ---

    def store_document(self, user_id: int, filename: str, file_type: str, file_size: int, metadata: Dict[str, Any] = None) -> int:
        try:
            clean_metadata = self._convert_numpy_types(metadata or {})
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO documents (user_id, filename, file_type, file_size, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, (user_id, filename, file_type, int(file_size), json.dumps(clean_metadata)))
                    document_id = cur.fetchone()[0]
                    conn.commit()
            return document_id
        except Exception as e:
            logger.error("Failed to store document: %s", e)
            raise

    def store_enhanced_chunks(self, document_id: int, chunks: List[Dict[str, Any]]):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for i, chunk in enumerate(chunks):
                        clean_chunk = self._convert_numpy_types(chunk)
                        cur.execute("""
                            INSERT INTO document_chunks (document_id, chunk_index, content, category, importance_score, metadata, vector_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            int(document_id),
                            int(i),
                            str(clean_chunk['content']),
                            str(clean_chunk.get('category', 'general')),
                            float(clean_chunk.get('importance_score', 0.5)),
                            json.dumps(clean_chunk.get('metadata', {})),
                            int(clean_chunk.get('vector_id')) if clean_chunk.get('vector_id') is not None else None
                        ))
                    conn.commit()
        except Exception as e:
            logger.error("Failed to store enhanced chunks: %s", e)
            raise

    def get_chunks_by_vector_ids(self, vector_ids: List[int], user_id: int) -> List[Dict[str, Any]]:
        """Retrieve chunks only if they belong to the specified user"""
        try:
            clean_vector_ids = [int(vid) for vid in vector_ids]
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT dc.*, d.filename, d.file_type
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE dc.vector_id = ANY(%s) AND d.user_id = %s
                        ORDER BY dc.vector_id
                    """, (clean_vector_ids, user_id))
                    rows = [dict(row) for row in cur.fetchall()]
            return rows
        except Exception as e:
            logger.error("Failed to retrieve chunks: %s", e)
            raise

    def get_all_documents(self, user_id: int):
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT id, filename, file_type, file_size, processed, upload_time 
                        FROM documents 
                        WHERE user_id = %s
                        ORDER BY upload_time DESC
                    """, (user_id,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching documents: {e}")
            return []

    def mark_document_processed(self, document_id: int):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE documents SET processed = TRUE WHERE id = %s", (int(document_id),))
                    conn.commit()
        except Exception as e:
            logger.error("Failed to mark document processed: %s", e)
            raise

    def store_query_result(self, user_id: int, query: str, results: List[Dict[str, Any]]):
        try:
            clean_results = self._convert_numpy_types(results)
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO query_results (user_id, query, results)
                        VALUES (%s, %s, %s)
                    """, (user_id, str(query), json.dumps(clean_results)))
                    conn.commit()
        except Exception as e:
            logger.error("Failed to store query result: %s", e)
            raise

    def delete_document(self, document_id: int, user_id: int):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM documents WHERE id = %s AND user_id = %s", (int(document_id), int(user_id)))
                    conn.commit()
        except Exception as e:
            logger.error("Failed to delete document: %s", e)
            raise