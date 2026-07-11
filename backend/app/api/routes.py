from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from pydantic import BaseModel

from app.models.schemas import (
    DocumentResponse, 
    QueryRequest, 
    QueryResponse, 
    MultipleQueryRequest, 
    MultipleQueryResponse
)
from app.services.document_service import document_service
from app.services.query_service import query_service
from app.core.auth import get_current_user, get_password_hash, verify_password, create_access_token
from app.db.postgres import PostgresManager

router = APIRouter()
auth_db = PostgresManager()

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "API is running"}

# --- AUTH ROUTES ---

@router.post("/auth/register")
def register(user: UserCreate):
    existing_user = auth_db.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    user_id = auth_db.create_user(user.username, hashed_password)
    return {"message": "User created successfully", "user_id": user_id}

@router.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth_db.get_user_by_username(form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": str(user['id'])})
    return {"access_token": access_token, "token_type": "bearer"}

# --- PROTECTED ROUTES ---

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...), 
    current_user_id: int = Depends(get_current_user)
):
    try:
        result = await document_service.process_upload(file, current_user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(current_user_id: int = Depends(get_current_user)):
    docs = document_service.get_all_documents(current_user_id)
    return docs

@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, current_user_id: int = Depends(get_current_user)):
    return document_service.delete_document(doc_id, current_user_id)

@router.post("/query", response_model=QueryResponse)
async def query_document(
    request: QueryRequest, 
    current_user_id: int = Depends(get_current_user)
):
    try:
        result = query_service.process_query(request.query, current_user_id, request.top_k)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/multiple-queries", response_model=MultipleQueryResponse)
async def multiple_queries(
    request: MultipleQueryRequest, 
    current_user_id: int = Depends(get_current_user)
):
    try:
        results = query_service.process_multiple_queries(request.queries, current_user_id, request.top_k)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
