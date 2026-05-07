# PitchAgent ⚡

An AI-powered full-stack app that lets sales teams send prospects a personalized RAG chatbot demo trained on their own website and product docs. The prospect experiences the product with their own data before a single sales call happens.

## 🧩 Core Idea

Instead of building a custom demo for every prospect, PitchAgent:

1. Crawls the prospect's website via Firecrawl
2. Accepts optional PDF uploads (up to 5 files, 25 MB each)
3. Indexes everything into an OpenAI Vector Store
4. Generates a password-protected chat link
5. Answers questions using OpenAI Responses API + `file_search` with citations
6. Expires demos after 7 days, cleaned up via maintenance endpoint or job trigger

If it's not in the indexed content, it doesn't appear in the answer.

## 🌟 Why This Project Matters

Most sales demo tools:

* Require manual setup per prospect
* Have no knowledge grounding
* Can't cite sources
* Need ongoing maintenance

PitchAgent:

* Creates a demo in one form submission
* Grounds every answer in crawled/uploaded content
* Provides file-level citations with source URLs
* Cleans up expired demos and vector stores via a maintenance endpoint or scheduled job

This is how prospect demos should actually work.

## 🏗️ Architecture Overview

```
Internal Console (Next.js)
        ↓
  POST /api/v1/demos
        ↓
  Firecrawl (website → markdown)
  + PDF uploads (validated)
        ↓
  OpenAI Vector Store (file_search index)
        ↓
  Chat link + password generated
        ↓
  Prospect opens /demos/{slug}/chat
        ↓
  POST /api/v1/demos/{slug}/query
        ↓
  OpenAI Responses API (file_search)
        ↓
  Answer with citations
```

The LLM only sees indexed content. No hallucination path exists.

## 🧠 How It Works

**Demo Creation:**
Sales rep fills out prospect name + company URL + optional PDFs → backend crawls the site, uploads all content to a dedicated vector store, generates a unique slug and password.

**Chat Session:**
Prospect authenticates with the generated password → asks questions → OpenAI Responses API searches the vector store → returns grounded answers with citation references mapped back to original filenames and source URLs.

**Lifecycle:**
Demos expire after 7 days. The maintenance endpoint marks them expired and deletes their OpenAI vector stores to avoid orphaned resources.

## ⚙️ Tech Stack

* **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4
* **Backend:** FastAPI, SQLAlchemy, Alembic
* **Database:** PostgreSQL (via `psycopg`)
* **AI:** OpenAI Responses API + Vector Stores (`file_search`)
* **Web Crawl:** Firecrawl

## 🧾 Setup Instructions

```bash
git clone https://github.com/disastrousDEVIL/PitchAgent.git
cd PitchAgent

# Backend
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend
npm install
```

## 🔐 Environment Variables

Create a `.env` file in `backend/`:

```bash
cp backend/.env.example backend/.env
```

```
OPENAI_API_KEY=sk-your-openai-key
OPENAI_DEFAULT_MODEL=gpt-5.4-mini-2026-03-17
DATABASE_URL=postgresql+psycopg://user@localhost:5432/instarag
FIRECRAWL_API_KEY=fc-your-firecrawl-key
```

**Frontend** (optional, defaults shown):

Create a `.env.local` file in `frontend/`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## 🚀 Running the App

**Backend:**

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`

**Frontend:**

```bash
cd frontend
npm run dev
```

Frontend runs on `http://localhost:3000`

## 🧪 API Endpoints

### 1. Health Check

`GET /api/v1/health`

Response:

```json
{
  "status": "ok"
}
```

### 2. List Active Demos

`GET /api/v1/demos`

Response:

```json
[
  {
    "id": "a1b2c3d4-...",
    "prospect_name": "Acme Corp",
    "company_url": "https://acme.com",
    "public_slug": "xK9mP2qR",
    "chat_url": "/demos/xK9mP2qR/chat",
    "status": "active",
    "expires_at": "2026-05-14T12:00:00"
  }
]
```

### 3. Create a Demo

`POST /api/v1/demos` (multipart form-data)

Request fields:

* `prospect_name` (required)
* `company_url` (required)
* `logo_url` (optional)
* `files` (optional — up to 5 PDFs, 25 MB each)

Response:

```json
{
  "id": "a1b2c3d4-...",
  "prospect_name": "Acme Corp",
  "public_slug": "xK9mP2qR",
  "chat_url": "/demos/xK9mP2qR/chat",
  "generated_password": "r4Nd0mP4ss",
  "vector_store_id": "vs_abc123",
  "pages_crawled": 12,
  "indexed_files": [
    { "source": "url", "original_name": "acme.com.md", "pages_crawled": 12 },
    { "source": "pdf", "original_name": "pricing.pdf" }
  ]
}
```

### 4. Get Demo Metadata

`GET /api/v1/demos/{slug}`

### 5. Authenticate Demo

`POST /api/v1/demos/{slug}/auth`

Request:

```json
{
  "access_password": "r4Nd0mP4ss"
}
```

Response:

```json
{
  "authenticated": true,
  "requires_password": true
}
```

### 6. Ask a Question

`POST /api/v1/demos/{slug}/query`

Request:

```json
{
  "question": "What does Acme Corp's pricing look like?",
  "access_password": "r4Nd0mP4ss"
}
```

Response:

```json
{
  "answer": "Acme Corp offers three tiers: Starter at $29/mo, Pro at $99/mo, and Enterprise with custom pricing.",
  "citations": [
    { "filename": "acme.com.md", "number": 1 },
    { "filename": "pricing.pdf", "number": 2 }
  ],
  "response_id": "resp_abc123"
}
```

### 7. Disable a Demo

`DELETE /api/v1/demos/{demo_id}`

Marks the demo as disabled and attempts to delete its OpenAI vector store (best effort).

### 8. Expire Overdue Demos

`POST /api/v1/demos/maintenance/expire`

Response:

```json
{
  "expired_count": 3,
  "failed_delete_count": 0
}
```

## 🧾 Folder Structure

```
PitchAgent/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI wiring + CORS
│   │   ├── core/config.py          # env loading
│   │   ├── api/v1/endpoints/
│   │   │   ├── demos.py            # all demo CRUD + query endpoints
│   │   │   └── health.py           # health check
│   │   ├── models/demo.py          # SQLAlchemy ORM models
│   │   ├── schemas/demo.py         # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── firecrawl_service.py          # website crawling
│   │   │   ├── vector_store_service.py       # OpenAI vector store ops
│   │   │   ├── responses_agent_service.py    # OpenAI Responses API
│   │   │   ├── demo_lifecycle_service.py     # expiry + cleanup
│   │   │   └── demo_prompt.py                # system prompt builder
│   │   ├── jobs/expire_demos.py    # expiration job
│   │   └── db/                     # session + base
│   ├── alembic/                    # DB migrations
│   └── requirements.txt
│
├── frontend/
│   └── src/app/
│       ├── page.tsx                # internal console (demo list + create modal)
│       └── demos/[slug]/chat/
│           └── page.tsx            # public chat UI (password gate + conversation)
│
└── README.md
```

## 📸 UI Screenshots (Placeholders)

Replace these with actual screenshots.

### 1. Internal Console — Demo List
![Demo List](docs/images/console-demo-list.png)

### 2. Create Demo Modal
![Create Demo](docs/images/create-demo-modal.png)

### 3. Chat — Password Screen
![Password Screen](docs/images/chat-password-screen.png)

### 4. Chat — Conversation with Citations
![Chat Conversation](docs/images/chat-conversation.png)

## 📌 Status

* ✅ Website crawling via Firecrawl
* ✅ PDF upload and indexing
* ✅ OpenAI Vector Store integration
* ✅ Grounded answers with citations
* ✅ Password-protected demo links
* ✅ Auto-expiry with vector store cleanup
* ✅ Internal demo management console
* ✅ Production-ready v1

## 🪄 License

This project is licensed under the MIT License.
You are free to use, modify, and distribute this software with attribution.

## 👤 Author

* **Krish Batra**
* Website: [vybecode.in](https://www.vybecode.in/)
* Email: [krishbatra3@gmail.com](mailto:krishbatra3@gmail.com)
* LinkedIn: [linkedin.com/in/krish-batra](https://www.linkedin.com/in/krish-batra/)
