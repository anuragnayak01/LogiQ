from app.config import get_settings
from app.db import log_chat, search_chunks
from app.embeddings import embed_query
from app.llm import get_llm_provider

settings = get_settings()


def build_context(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        parts.append(
            f"[Source: {c['title']} ({c['doc_type']}), chunk {c['chunk_index']}, "
            f"similarity {c['similarity']:.2f}]\n{c['content']}"
        )
    return "\n\n---\n\n".join(parts)


def answer_question(question: str, session_id: str = "demo") -> dict:
    query_embedding = embed_query(question)
    chunks = search_chunks(query_embedding, top_k=settings.top_k)

    if not chunks:
        answer = (
            "I couldn't find anything in the knowledge base for that. "
            "Try rephrasing, or check with your supervisor / HR directly."
        )
        log_chat(session_id, question, answer, [])
        return {"answer": answer, "sources": []}

    context = build_context(chunks)
    llm = get_llm_provider()
    answer = llm.answer(question, context)

    sources = [
        {"title": c["title"], "doc_type": c["doc_type"], "similarity": round(c["similarity"], 3)}
        for c in chunks
    ]
    log_chat(session_id, question, answer, sources)
    return {"answer": answer, "sources": sources}
