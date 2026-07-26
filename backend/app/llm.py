from abc import ABC, abstractmethod

from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are an internal knowledge base assistant for a logistics \
company. Answer employee questions using ONLY the provided document excerpts \
(SOPs, policy manuals, training guides).

Rules:
- If the excerpts don't contain the answer, say so plainly and suggest who to \
contact (e.g. HR, Ops lead, Safety officer) rather than guessing.
- Be concise and practical — employees are reading this on the floor or on a break.
- Always cite the source document title(s) you used, in a short "Sources:" line \
at the end.
- Never invent policy details, numbers, or procedures not present in the excerpts.
"""


class LLMProvider(ABC):
    @abstractmethod
    def answer(self, question: str, context: str) -> str:
        ...


class ClaudeProvider(LLMProvider):
    def __init__(self):
        import anthropic

        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def answer(self, question: str, context: str) -> str:
        message = self.client.messages.create(
            model=settings.anthropic_model,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Document excerpts:\n\n{context}\n\nEmployee question: {question}",
                }
            ],
        )
        return "".join(block.text for block in message.content if block.type == "text")


class OpenAIProvider(LLMProvider):
    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.openai_api_key)

    def answer(self, question: str, context: str) -> str:
        completion = self.client.chat.completions.create(
            model=settings.openai_chat_model,
            max_tokens=800,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Document excerpts:\n\n{context}\n\nEmployee question: {question}",
                },
            ],
        )
        return completion.choices[0].message.content


class GroqProvider(LLMProvider):
    def __init__(self):
        from openai import OpenAI

        # Groq exposes an OpenAI-compatible chat completions API.
        self.client = OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")

    def answer(self, question: str, context: str) -> str:
        completion = self.client.chat.completions.create(
            model=settings.groq_model,
            max_tokens=800,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Document excerpts:\n\n{context}\n\nEmployee question: {question}",
                },
            ],
        )
        return completion.choices[0].message.content


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "openai":
        return OpenAIProvider()
    if settings.llm_provider == "groq":
        return GroqProvider()
    return ClaudeProvider()
