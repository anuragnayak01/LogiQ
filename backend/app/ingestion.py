from app.config import get_settings
from app.db import insert_chunks, insert_document
from app.embeddings import embed_texts

settings = get_settings()


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Simple sliding-window character chunker. Good enough for SOP/policy
    text; swap for a semantic/markdown-aware chunker if documents get long
    or highly structured."""
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if c]


def ingest_text(title: str, doc_type: str, content: str, source_path: str | None = None) -> dict:
    """Chunk, embed, and store one document's text. Used by the CLI ingester
    and by the /admin/ingest API route."""
    chunks = chunk_text(content, settings.chunk_size, settings.chunk_overlap)
    embeddings = embed_texts(chunks)
    document_id = insert_document(title=title, doc_type=doc_type, source_path=source_path)
    insert_chunks(document_id, chunks, embeddings)
    return {"document_id": document_id, "title": title, "doc_type": doc_type, "chunks": len(chunks)}
