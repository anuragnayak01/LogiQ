from openai import OpenAI

from app.config import get_settings

settings = get_settings()
_client = OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Uses OpenAI embeddings regardless of which
    LLM provider is chosen for chat, since Anthropic has no first-party
    embeddings endpoint. Swap this function out if you'd rather run a
    local embedding model (e.g. sentence-transformers / fastembed)."""
    response = _client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in response.data]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
