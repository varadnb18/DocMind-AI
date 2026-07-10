# DocMind AI

DocMind AI is a full-stack Retrieval-Augmented Generation (RAG) application that allows users to upload documents (PDF, DOCX, TXT) and chat with them using Google's powerful Gemini LLMs. It features isolated multi-user authentication, ensuring that users can only search and interact with their own uploaded documents.

## 🌟 Features

*   **Multi-User Authentication**: Secure JWT-based login and registration. Each user has isolated data and vector indexes.
*   **Intelligent Document Processing**: Automatically extracts text, chunks it logically, and stores it for vector search.
*   **High-Performance Vector Search**: Uses FAISS to perform ultra-fast similarity searches over document embeddings.
*   **Generative Q&A**: Uses Google's Gemini models to generate accurate, context-aware answers based strictly on the uploaded document contents.
*   **Modern UI**: A responsive, beautiful React frontend styled with Tailwind CSS.

---

## 🏗️ Architecture

Below is the high-level architecture diagram demonstrating how data flows through the application during a Chat / Query request:

```mermaid
flowchart TD
    subgraph Frontend [React / Vite Frontend]
        UI[User Interface]
        AuthCtx[Auth Context & Interceptor]
    end

    subgraph Backend [FastAPI Backend]
        API[API Router]
        Auth[JWT Authentication]
        DocService[Document Service]
        QueryService[Query Service]
        EmbedMgr[Embedding Manager - Gemini]
        LLM[LLM Service - Gemini]
    end

    subgraph Storage [Data Storage]
        PG[(PostgreSQL\nUsers, Metadata, Chunks)]
        FAISS[(FAISS\nVector Indexes)]
    end

    %% Flow
    UI -- "1. Upload Doc / Send Query\n+ JWT Token" --> AuthCtx
    AuthCtx -- "2. HTTP Request" --> API
    API -- "3. Validate Token" --> Auth
    Auth -. "Valid" .-> API
    
    API -- "4. Route Request" --> QueryService
    QueryService -- "5. Embed Query" --> EmbedMgr
    EmbedMgr -- "6. Returns 3072-dim Vector" --> QueryService
    
    QueryService -- "7. Vector Search (by user_id)" --> FAISS
    FAISS -- "8. Returns Vector IDs" --> QueryService
    
    QueryService -- "9. Fetch Text Chunks" --> PG
    PG -- "10. Returns Text Context" --> QueryService
    
    QueryService -- "11. Pass Context + Query" --> LLM
    LLM -- "12. Generates Answer" --> QueryService
    QueryService -- "13. JSON Response" --> UI
```

### Components:
*   **Frontend**: Built with React, Vite, and Tailwind CSS. Uses `axios` with interceptors to automatically attach JWT bearer tokens to all backend requests.
*   **Backend**: Built with FastAPI. Handles file parsing (PDF/DOCX), chunking, and orchestration.
*   **PostgreSQL**: A relational database storing `users`, `documents`, and `document_chunks`. Every row is tied to a specific `user_id`.
*   **FAISS**: An in-memory vector database built by Meta. For multi-user isolation, the application saves a unique physical file per user (e.g., `faiss_index_1`).
*   **Google Gemini API**: Used for both converting text into numerical vectors (`gemini-embedding-001`) and generating the final human-readable answers (`gemini-1.5-pro` & `gemini-1.5-flash`).

---

## 🚀 Getting Started

### Prerequisites
*   Node.js & npm
*   Python 3.12+
*   PostgreSQL running locally (or remotely)
*   A Google Gemini API Key

### 1. Database Setup
Ensure PostgreSQL is running. The backend will automatically create the required tables (`users`, `documents`, `query_results`, `document_chunks`) when you first start the FastAPI server.

### 2. Backend Setup
Navigate to the `backend` directory and set up your Python environment:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate  # Windows
# source .venv/bin/activate # Mac/Linux

pip install -r requirements.txt
```

Create a `.env` file inside the `backend` folder:
```env
DATABASE_URL=postgresql://postgres:password@localhost/dbname
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_random_secret_jwt_key
```

Run the backend server:
```bash
uvicorn app.main:app --reload
```
*The API will be available at `http://localhost:8000`*

### 3. Frontend Setup
Navigate to the `frontend` directory:

```bash
cd frontend
npm install
```

Create a `.env` file inside the `frontend` folder:
```env
VITE_API_URL=http://localhost:8000
```

Start the Vite development server:
```bash
npm run dev
```
*The app will be available at `http://localhost:5173`*

---

## 🔒 Security & Data Isolation
Because this is a multi-user platform, data leakage is prevented via:
1.  **Row-level filtering**: Every Postgres SQL query enforces `WHERE user_id = %s`.
2.  **Physical Vector Isolation**: FAISS does not have built-in row-level security, so we instantiate completely separate `faiss_index_{user_id}` files on the disk for each user. A user querying their data only loads their personal FAISS index into memory.

## 🤝 For Beginners
If you are learning from this project, start by exploring the following files:
*   `backend/app/core/auth.py`: Learn how JSON Web Tokens (JWT) are generated and validated.
*   `backend/app/api/routes.py`: See how `Depends(get_current_user)` protects the routes.
*   `frontend/src/context/AuthContext.jsx`: Understand how React Context manages global state and how Axios Interceptors automatically attach tokens to your requests.
