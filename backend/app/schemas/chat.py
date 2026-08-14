"""对话 DTO。"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    content: str = Field(min_length=1)
    attachments: list[str] = []  # MVP：图片不随文本外发（隐私默认），仅占位


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    meta_json: str | None = None
    created_at: str


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    archived: bool
    message_count: int


class ConversationUpdate(BaseModel):
    title: str | None = None
    archived: bool | None = None


class ExtractRequest(BaseModel):
    conversation_id: str
    message_id: str


class ExtractResponse(BaseModel):
    question_text: str
    options: list[str] = []
    answer: str = ""
    analysis: str = ""
    mock: bool = False
