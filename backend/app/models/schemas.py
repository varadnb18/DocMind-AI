from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Any, Dict

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    processed: bool
    upload_time: Any

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

class MultipleQueryRequest(BaseModel):
    queries: List[str]
    top_k: int = 5

class QuerySource(BaseModel):
    filename: str
    content: str
    score: float

class QueryResponse(BaseModel):
    query: str
    answer: str
    provider_used: str
    sources: List[QuerySource]

class MultipleQueryResponse(BaseModel):
    results: List[QueryResponse]
