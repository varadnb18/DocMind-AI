import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from contextlib import contextmanager
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
        self.pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=self.postgres_url,
            client_encoding='utf8'
        )
        self.init_tables()

    @contextmanager
    def get_connection(self):
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

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
                            embedding BYTEA,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Add embedding column if it doesn't exist (for existing databases)
                    cur.execute("""
                        ALTER TABLE document_chunks 
                        ADD COLUMN IF NOT EXISTS embedding BYTEA
                    """)

                    # Create query_results table with user_id & document_id
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS query_results (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                            document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                            query TEXT NOT NULL,
                            results JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Add document_id column if it doesn't exist (for existing databases)
                    cur.execute("""
                        ALTER TABLE query_results 
                        ADD COLUMN IF NOT EXISTS document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE
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
                        # Get embedding bytes if available
                        embedding_bytes = chunk.get('embedding_bytes')
                        cur.execute("""
                            INSERT INTO document_chunks (document_id, chunk_index, content, category, importance_score, metadata, vector_id, embedding)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            int(document_id),
                            int(i),
                            str(clean_chunk['content']),
                            str(clean_chunk.get('category', 'general')),
                            float(clean_chunk.get('importance_score', 0.5)),
                            json.dumps(clean_chunk.get('metadata', {})),
                            int(clean_chunk.get('vector_id')) if clean_chunk.get('vector_id') is not None else None,
                            psycopg2.Binary(embedding_bytes) if embedding_bytes is not None else None
                        ))
                    conn.commit()
        except Exception as e:
            logger.error("Failed to store enhanced chunks: %s", e)
            raise

    def get_chunks_by_vector_ids(self, vector_ids: List[int], user_id: int, document_id: int = None) -> List[Dict[str, Any]]:
        """Retrieve chunks only if they belong to the specified user (and optionally document)"""
        try:
            clean_vector_ids = [int(vid) for vid in vector_ids]
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT dc.*, d.filename, d.file_type
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE dc.vector_id = ANY(%s) AND d.user_id = %s
                    """
                    params = [clean_vector_ids, user_id]
                    
                    if document_id is not None:
                        query += " AND dc.document_id = %s"
                        params.append(document_id)
                        
                    query += " ORDER BY dc.vector_id"
                    
                    cur.execute(query, tuple(params))
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

    def store_query_result(self, user_id: int, query: str, results: List[Dict[str, Any]], document_id: Optional[int] = None):
        try:
            clean_results = self._convert_numpy_types(results)
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO query_results (user_id, document_id, query, results)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, document_id, str(query), json.dumps(clean_results)))
                    conn.commit()
        except Exception as e:
            logger.error("Failed to store query result: %s", e)
            raise

    def get_query_history(self, user_id: int, document_id: int) -> List[Dict[str, Any]]:
        """Fetch past queries and responses for a specific user and document"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT id, query, results, created_at
                        FROM query_results
                        WHERE user_id = %s AND document_id = %s
                        ORDER BY created_at ASC
                    """, (user_id, document_id))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error("Failed to fetch query history: %s", e)
            return []

    def delete_document(self, document_id: int, user_id: int):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM documents WHERE id = %s AND user_id = %s", (int(document_id), int(user_id)))
                    conn.commit()
        except Exception as e:
            logger.error("Failed to delete document: %s", e)
            raise

    # --- FAISS Rebuild Methods ---

    def get_all_user_ids(self) -> List[int]:
        """Get all user IDs that have uploaded documents"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT DISTINCT user_id FROM documents")
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get user IDs: {e}")
            return []

    def get_chunks_with_embeddings(self, user_id: int) -> List[Dict[str, Any]]:
        """Load all chunks that have stored embeddings for FAISS rebuilding"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT dc.id, dc.document_id, dc.chunk_index, dc.content,
                               dc.category, dc.importance_score, dc.metadata,
                               dc.vector_id, dc.embedding, d.filename
                        FROM document_chunks dc
                        JOIN documents d ON dc.document_id = d.id
                        WHERE d.user_id = %s AND dc.embedding IS NOT NULL
                        ORDER BY dc.id
                    """, (user_id,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to load embeddings for user {user_id}: {e}")
            return []

    def update_chunk_vector_ids(self, updates: List[tuple]):
        """Batch update vector_ids after FAISS rebuild. updates = [(chunk_id, new_vector_id), ...]"""
        if not updates:
            return
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for chunk_id, new_vector_id in updates:
                        cur.execute(
                            "UPDATE document_chunks SET vector_id = %s WHERE id = %s",
                            (int(new_vector_id), int(chunk_id))
                        )
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to update vector IDs: {e}")
            raise