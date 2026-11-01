# schemas/chat.py
from pydantic import BaseModel, Field, field_validator

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Question posée à l'assistant UNIDET",
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La question ne peut pas être vide.")
        return value


class Source(BaseModel):
    title: str
    url: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
