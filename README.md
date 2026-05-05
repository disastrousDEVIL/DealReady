# InstaRAG

Instant RAG-powered chatbot demos for sales teams. Paste a prospect URL and optionally upload PDFs, then index the content into an OpenAI vector store and query it through the Responses API.

## Architecture

- **Backend**: FastAPI
- **Data ingestion**: Firecrawl crawl for URLs, OpenAI file upload for PDFs and crawled Markdown
- **Retrieval**: OpenAI vector stores with `file_search`
- **Chat**: OpenAI Responses API with optional `previous_response_id`

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
```

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in your API keys.
