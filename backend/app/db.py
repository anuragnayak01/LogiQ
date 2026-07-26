import json
from contextlib import contextmanager
from pathlib import Path

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from app.config import get_settings

settings = get_settings()

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


@contextmanager
def get_conn():
    """Yield a psycopg connection with pgvector types registered."""
    conn = psycopg.connect(settings.database_url, autocommit=True)
    register_vector(conn)
    try:
        yield conn
    finally:
        conn.close()


def init_schema() -> None:
    """Idempotently create the extension/tables/index if they don't exist yet.
    Safe to call on every app startup -- schema.sql uses CREATE ... IF NOT EXISTS
    throughout, so this never touches existing data."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def document_exists(title: str) -> bool:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM kb_documents WHERE title = %s LIMIT 1", (title,))
        return cur.fetchone() is not None


def list_documents() -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.title, d.doc_type, d.created_at, count(c.id) AS chunk_count
            FROM kb_documents d
            LEFT JOIN kb_chunks c ON c.document_id = d.id
            GROUP BY d.id
            ORDER BY d.created_at DESC
            """
        )
        cols = ["id", "title", "doc_type", "created_at", "chunk_count"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def insert_document(title: str, doc_type: str, source_path: str | None = None) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO kb_documents (title, doc_type, source_path)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (title, doc_type, source_path),
        )
        return cur.fetchone()[0]


def insert_chunks(document_id: int, chunks: list[str], embeddings: list[list[float]]) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        rows = [
            (document_id, i, chunk, Vector(embedding))
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]
        cur.executemany(
            """
            INSERT INTO kb_chunks (document_id, chunk_index, content, embedding)
            VALUES (%s, %s, %s, %s)
            """,
            rows,
        )


def search_chunks(query_embedding: list[float], top_k: int) -> list[dict]:
    """Cosine-similarity nearest neighbor search over kb_chunks."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                c.id,
                c.content,
                c.chunk_index,
                d.title,
                d.doc_type,
                1 - (c.embedding <=> %s) AS similarity
            FROM kb_chunks c
            JOIN kb_documents d ON d.id = c.document_id
            ORDER BY c.embedding <=> %s
            LIMIT %s
            """,
            (Vector(query_embedding), Vector(query_embedding), top_k),
        )
        cols = ["id", "content", "chunk_index", "title", "doc_type", "similarity"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def log_chat(session_id: str, question: str, answer: str, sources: list[dict]) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO kb_chat_log (session_id, question, answer, sources)
            VALUES (%s, %s, %s, %s)
            """,
            (session_id, question, answer, json.dumps(sources)),
        )
