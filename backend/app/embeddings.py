from app.config import get_settings

settings = get_settings()

_fastembed_model = None  # lazy-loaded, downloads weights once on first use


def _get_fastembed_model():
    global _fastembed_model
    if _fastembed_model is None:
        from fastembed import TextEmbedding

        _fastembed_model = TextEmbedding(model_name=settings.embedding_model)
    return _fastembed_model


def _embed_fastembed(texts: list[str]) -> list[list[float]]:
    model = _get_fastembed_model()
    return [vec.tolist() for vec in model.embed(texts)]


def _embed_openai(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in response.data]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Defaults to a free local model (fastembed,
    BAAI/bge-small-en-v1.5, 384-dim) so the whole stack can run at zero cost.
    Set EMBEDDING_PROVIDER=openai in .env to use OpenAI's embedding API
    instead (requires OPENAI_API_KEY and EMBEDDING_DIM=1536)."""
    if settings.embedding_provider == "openai":
        return _embed_openai(texts)
    return _embed_fastembed(texts)


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
