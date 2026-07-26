-- Internal Knowledge Base RAG Agent — Postgres + pgvector schema
-- Run once against your existing Postgres database.

CREATE EXTENSION IF NOT EXISTS vector;

-- Source documents (SOPs, policy manuals, training guides)
CREATE TABLE IF NOT EXISTS kb_documents (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    doc_type    TEXT NOT NULL DEFAULT 'sop',   -- sop | policy | training
    source_path TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Chunked + embedded content. Embedding dimension defaults to 1536
-- (OpenAI text-embedding-3-small). Change the dimension below if you
-- swap embedding providers/models.
CREATE TABLE IF NOT EXISTS kb_chunks (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content     TEXT NOT NULL,
    embedding   VECTOR(1536) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Approximate nearest-neighbor index for cosine similarity search.
-- lists ~ sqrt(row_count) is a reasonable default; tune once you know volume.
CREATE INDEX IF NOT EXISTS kb_chunks_embedding_idx
    ON kb_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Simple chat log, useful for the "product demo" and for the
-- "key learnings" section (what employees actually ask).
CREATE TABLE IF NOT EXISTS kb_chat_log (
    id          SERIAL PRIMARY KEY,
    session_id  TEXT,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    sources     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
