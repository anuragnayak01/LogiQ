from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.db import document_exists, init_schema, list_documents
from app.ingestion import ingest_text
from app.models import ChatRequest, ChatResponse
from app.rag import answer_question
from app.seed_data import SEED_DOCUMENTS

settings = get_settings()

app = FastAPI(title="Internal Knowledge Base Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # Idempotent: safe to run on every deploy/restart, never touches existing data.
    if settings.database_url:
        init_schema()


def _check_admin_key(x_admin_key: str | None):
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY not configured on the server")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="invalid or missing X-Admin-Key header")


class IngestRequest(BaseModel):
    title: str
    doc_type: str  # sop | policy | training
    content: str


@app.get("/health")
def health():
    return {"status": "ok", "llm_provider": settings.llm_provider}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")
    result = answer_question(req.question, req.session_id)
    return result


@app.post("/admin/seed")
def admin_seed(x_admin_key: str | None = Header(default=None)):
    """Load the 3 built-in sample docs (SOP / policy / training) so you have
    real, queryable data immediately after deploy -- no local files needed.
    Safe to call more than once: skips titles that already exist."""
    _check_admin_key(x_admin_key)
    results = []
    for doc in SEED_DOCUMENTS:
        if document_exists(doc["title"]):
            results.append({"title": doc["title"], "status": "already_exists"})
            continue
        result = ingest_text(doc["title"], doc["doc_type"], doc["content"])
        results.append({**result, "status": "ingested"})
    return {"results": results}


@app.post("/admin/ingest")
def admin_ingest(req: IngestRequest, x_admin_key: str | None = Header(default=None)):
    """Ingest one real document by sending its title/type/text as JSON --
    use this to swap in your actual SOPs/policies once the sample data
    round-trip is verified."""
    _check_admin_key(x_admin_key)
    if req.doc_type not in ("sop", "policy", "training"):
        raise HTTPException(status_code=400, detail="doc_type must be sop, policy, or training")
    result = ingest_text(req.title, req.doc_type, req.content)
    return result


@app.get("/admin/documents")
def admin_documents(x_admin_key: str | None = Header(default=None)):
    """List what's currently in the knowledge base -- use this to verify
    data landed after seeding or ingesting."""
    _check_admin_key(x_admin_key)
    return {"documents": list_documents()}
