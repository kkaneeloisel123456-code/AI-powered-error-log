"""AI 答疑路由：POST /chat（SSE）+ 会话历史管理 + 题目提取。"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import require_auth
from app.db.session import get_db
from app.schemas.chat import (
    ChatRequest,
    ConversationOut,
    ConversationUpdate,
    ExtractRequest,
    ExtractResponse,
    MessageOut,
)
from app.services import chat_service

router = APIRouter(prefix="/api/v1", tags=["chat"], dependencies=[Depends(require_auth)])


@router.post("/chat")
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    conv, messages, _ = chat_service._build_context(db, payload.conversation_id, payload.content)

    async def event_stream():
        async for event, data in chat_service.stream_answer(db, conv, messages, payload.content):
            yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(q: str | None = None, db: Session = Depends(get_db)):
    return chat_service.list_conversations(db, q)


@router.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(db: Session = Depends(get_db)):
    conv = chat_service.create_conversation(db)
    return {"id": conv["id"], "title": conv["title"], "created_at": "", "updated_at": "",
            "archived": False, "message_count": 0}


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    return chat_service.get_messages(db, conversation_id)


@router.patch("/conversations/{conversation_id}")
def update_conversation(conversation_id: str, payload: ConversationUpdate, db: Session = Depends(get_db)):
    return chat_service.update_conversation(db, conversation_id, payload.model_dump(exclude_none=True))


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    chat_service.delete_conversation(db, conversation_id)


@router.post("/conversations/{conversation_id}/clear", status_code=204)
def clear_conversation(conversation_id: str, db: Session = Depends(get_db)):
    chat_service.clear_conversation(db, conversation_id)


@router.post("/chat/extract", response_model=ExtractResponse)
def extract(payload: ExtractRequest, db: Session = Depends(get_db)):
    return chat_service.extract_question(db, payload.conversation_id, payload.message_id)
