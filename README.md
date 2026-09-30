# DocNexus AI

An agentic AI-powered intelligent document management platform for the Information Retrieval and Web Analytics module.

---

## Project Overview

DocNexus AI allows authenticated users to upload PDF documents, extract intelligence, index content for retrieval, ask document-grounded questions, and receive verified answers with traceable citations. The system is built around four interacting intelligent agents coordinated by a query router.

---

## Architecture

```
React / TypeScript Frontend (Vite)
         |  REST / JSON
         v
FastAPI Backend
         |
         +-- Orchestrator & Query Router Agent  (Member 1)
         |
         +-- Document Intelligence Agent        (Member 2)
         |    +-- PyMuPDF extraction
         |    +-- spaCy NLP (NER, keywords, summarization, classification)
         |    +-- Processed artifact storage
         |
         +-- Information Retrieval Agent        (Member 3)
         |    +-- Sentence Transformers embeddings
         |    +-- ChromaDB vector store
         |    +-- BM25 keyword retrieval
         |    +-- Hybrid retrieval (min-max normalized)
         |
         +-- Answer & Verification Agent        (Member 4)
              +-- Gemini LLM (google-genai)
              +-- Evidence-grounded answer generation
              +-- Server-side citation validation
              +-- Claim verification + repair

Application database:  MongoDB Atlas
Vector database:       ChromaDB  (storage/chroma/)
Uploaded PDFs:         storage/uploads/<user_id>/
Processed artifacts:   storage/processed/<user_id>/<document_id>/
CUAD evaluation data:  data/evaluation/  (not mixed with uploads)
```

---

## Main Features

- Secure user registration and login with Argon2 password hashing and JWT authentication
- PDF upload with magic-byte validation, SHA-256 checksum, and path-traversal prevention
- Page-aware PDF text extraction (PyMuPDF) with OCR detection
- Named Entity Recognition, keyword extraction, extractive summarization, document classification (spaCy)
- Semantic search via Sentence Transformers and ChromaDB
- BM25 keyword search via rank-bm25
- Hybrid retrieval with min-max normalization (`0.6 × semantic + 0.4 × BM25`)
- Gemini-powered document-grounded QA with evidence-only constraints
- Server-side citation resolution (filename + page — never invented)
- Claim verification and one-attempt repair
- Safe abstention when evidence is insufficient
- Per-user document isolation enforced on every API endpoint

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| Backend | FastAPI, Python 3.13 |
| Application DB | MongoDB Atlas (pymongo) |
| Vector DB | ChromaDB (persistent) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| NLP | spaCy en_core_web_sm |
| Lexical Retrieval | rank-bm25 (BM25Okapi) |
| LLM | Google Gemini 2.5 Flash (google-genai) |
| Auth | PyJWT + pwdlib[argon2] |
| PDF Extraction | PyMuPDF |
| Validation | Pydantic v2 + pydantic-settings |
| Testing | pytest + httpx |

---

## Agent Roles

| Agent | Member | Responsibility |
|---|---|---|
| Orchestrator & Query Router | Member 1 | Intent classification, workflow routing, typed AgentMessage contracts |
| Document Intelligence Agent | Member 2 | PDF extraction, NLP pipeline, processed artifact storage |
| Information Retrieval Agent | Member 3 | Chunking, embeddings, ChromaDB, BM25, hybrid retrieval, IR metrics |
| Answer & Verification Agent | Member 4 | Gemini RAG, citation validation, claim verification, hallucination control |

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB Atlas account with a cluster
- Google Gemini API key (https://aistudio.google.com/app/apikey)

### Backend Setup

```powershell
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install spaCy English model
python -m spacy download en_core_web_sm
```

### Environment Configuration

```powershell
# Copy the example and fill in real values
copy .env.example .env
```

Edit `backend/.env`:

```
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
GEMINI_API_KEY=<your Gemini API key>
```

### MongoDB Atlas Setup

1. Create a free cluster at https://cloud.mongodb.com
2. Under **Security → Database Access**: create a user with read/write permissions
3. Under **Security → Network Access**: add your current IP address
4. Under **Database → Connect → Drivers**: copy the Python connection string

### Start Backend

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs

### Frontend Setup

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend: http://localhost:5173

---

## Running Tests

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: **73 passed, 0 failed, 0 skipped**

Tests mock MongoDB and Gemini — no external services required.

---

## Dataset Note

The CUAD contract dataset under `data/raw/` and `data/selected/` is used for evaluation only. These directories are gitignored. Runtime user uploads go to `storage/uploads/` and are never mixed with evaluation data.

Evaluation templates are in `data/evaluation/`. Fill in real MongoDB document IDs after processing evaluation PDFs to compute Precision@K, Recall@K, and MRR.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | / | API status |
| GET | /health | Database health check |
| POST | /auth/register | Register user |
| POST | /auth/login | Login and get JWT |
| GET | /auth/me | Get current user |
| POST | /documents/upload | Upload a PDF |
| GET | /documents | List user documents |
| GET | /documents/{id} | Get document metadata |
| DELETE | /documents/{id} | Delete document + index |
| POST | /documents/{id}/process | Extract and analyse PDF |
| GET | /documents/{id}/intelligence | Get NLP results |
| POST | /documents/{id}/index | Index for retrieval |
| GET | /documents/{id}/index-status | Check index status |
| DELETE | /documents/{id}/index | Remove from index |
| POST | /retrieval/search | Search (semantic/bm25/hybrid) |
| POST | /answers/query | Grounded QA with citations |
| POST | /orchestrator/route | Route a query to an agent |

---

## Responsible AI

| Principle | Implementation |
|---|---|
| Transparency | Every answer includes filename + page citations resolved server-side |
| Explainability | NLP pipeline is rule-based and fully visible (frequency scoring, spaCy) |
| Hallucination control | Evidence-only prompt; Gemini cannot use general knowledge |
| Safe abstention | Returns fixed message when evidence is insufficient |
| Privacy | Passwords hashed with Argon2; JWTs not stored server-side |
| User data protection | Per-user file directories; authorization checked on every endpoint |
| Prompt injection resistance | Document text HTML-escaped and XML-delimited before LLM |
| Source verification | Citations resolved against server-controlled metadata only |

---

## Security

- JWT Bearer authentication required on all document and retrieval endpoints
- Argon2 password hashing via pwdlib
- PDF magic-byte (`%PDF-`) and MIME type validation
- UUID-based stored filenames — original filename never used on disk
- Path-traversal prevention with `is_relative_to()` on all file operations
- MongoDB errors caught globally — connection details never exposed to API responses
- CORS restricted to configured frontend origin

---

## Team Responsibilities

| Member | Components |
|---|---|
| Member 1 | Orchestrator, FastAPI integration, MongoDB foundation, authentication, authorization, upload/storage, frontend integration |
| Member 2 | Document Intelligence Agent, PDF extraction, NLP, NER, keyword extraction, summarization, document classification |
| Member 3 | Information Retrieval Agent, chunking, embeddings, ChromaDB, BM25, hybrid retrieval, IR evaluation |
| Member 4 | Answer & Verification Agent, Gemini integration, RAG answer generation, citation validation, hallucination control |

---

## Contributors

University group project — Information Retrieval and Web Analytics module.
