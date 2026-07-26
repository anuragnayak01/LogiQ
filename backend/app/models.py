from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    session_id: str = "demo"


class Source(BaseModel):
    title: str
    doc_type: str
    similarity: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
