"""AI 答疑：SSE 流式、会话历史管理、上下文截断、题目提取。"""
import asyncio
import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.gateway import get_gateway
from app.ai.prompts import CHAT_PROMPT, EXTRACT_PROMPT
from app.core.config import get_settings
from app.core.errors import ApiError, not_found
from app.db.models import Conversation, Message

MAX_CONTEXT_ROUNDS = 20  # PRD 5.8：最近 20 轮


def list_conversations(db: Session, q: str | None = None) -> list[dict]:
    stmt = select(Conversation).where(Conversation.archived.is_(False))
    if q:
        stmt = stmt.where(Conversation.title.like(f"%{q}%"))
    convs = db.scalars(stmt.order_by(Conversation.updated_at.desc()).limit(100)).all()
    counts = dict(db.execute(
        select(Message.conversation_id, func.count(Message.id)).group_by(Message.conversation_id)
    ).all())
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat(),
         "updated_at": c.updated_at.isoformat(), "archived": c.archived,
         "message_count": counts.get(c.id, 0)}
        for c in convs
    ]


def get_messages(db: Session, conversation_id: str) -> list[dict]:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise not_found("会话", conversation_id)
    rows = db.query(Message).filter(Message.conversation_id == conversation_id) \
        .order_by(Message.created_at).all()
    return [
        {"id": m.id, "conversation_id": m.conversation_id, "role": m.role,
         "content": m.content, "meta_json": m.meta_json,
         "created_at": m.created_at.isoformat()}
        for m in rows
    ]


def create_conversation(db: Session) -> dict:
    conv = Conversation(title="新对话")
    db.add(conv)
    db.flush()
    return {"id": conv.id, "title": conv.title}


def update_conversation(db: Session, conversation_id: str, payload: dict) -> dict:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise not_found("会话", conversation_id)
    if payload.get("title"):
        conv.title = payload["title"]
    if payload.get("archived") is not None:
        conv.archived = payload["archived"]
    return {"id": conv.id, "title": conv.title, "archived": conv.archived}


def delete_conversation(db: Session, conversation_id: str) -> None:
    """删除会话：会话与消息移除，错题本数据不受影响（PRD 7.8-26）。"""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise not_found("会话", conversation_id)
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conv)


def clear_conversation(db: Session, conversation_id: str) -> None:
    """清空消息（保留会话）。"""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise not_found("会话", conversation_id)
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()


def _build_context(db: Session, conversation_id: str | None, content: str) -> tuple[Conversation, list[dict], str]:
    """会话上下文：最近 20 轮消息 + 本轮用户输入。"""
    if conversation_id:
        conv = db.get(Conversation, conversation_id)
        if conv is None:
            raise not_found("会话", conversation_id)
    else:
        conv = Conversation(title=content[:24] or "新对话")
        db.add(conv)
        db.flush()
    history = db.query(Message).filter(Message.conversation_id == conv.id) \
        .order_by(Message.created_at.desc()).limit(MAX_CONTEXT_ROUNDS * 2).all()
    history = list(reversed(history))
    messages = [{"role": "system", "content": CHAT_PROMPT}]
    for m in history:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": content})
    return conv, messages, history[-1].content if history else ""


async def stream_answer(db: Session, conv: Conversation, messages: list[dict], user_content: str):
    """SSE 流式：yield (event, data)。失败保留已渲染部分（EX-06 语义）。"""
    user_msg = Message(conversation_id=conv.id, role="user", content=user_content)
    db.add(user_msg)
    db.flush()
    user_msg_id = user_msg.id

    assistant = Message(conversation_id=conv.id, role="assistant", content="")
    db.add(assistant)
    db.flush()
    assistant_id = assistant.id
    full = ""
    try:
        gateway = get_gateway()
        async for delta in gateway.stream(messages):
            full += delta
            assistant.content = full
            yield "token", {"delta": delta}
        conv.title = conv.title if conv.title != "新对话" else user_content[:24]
        db.flush()
        db.commit()
        yield "done", {"conversation_id": conv.id, "message_id": assistant_id,
                       "user_message_id": user_msg_id}
    except ApiError as err:
        # 已渲染部分保留（用户可「继续生成」）
        if full:
            assistant.content = full
            db.commit()
        yield "error", {"code": err.code, "message": err.message}
    finally:
        if assistant.content:
            db.commit()


def extract_question(db: Session, conversation_id: str, message_id: str) -> dict:
    """加入错题本：从该轮问答提取题目草稿（PRD 5.1.3）。"""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise not_found("会话", conversation_id)
    msg = db.get(Message, message_id)
    if msg is None or msg.conversation_id != conversation_id:
        raise not_found("消息", message_id)
    if msg.role != "assistant":
        raise ApiError("VALIDATION_ERROR", "请对 AI 回答执行「加入错题本」", {})
    # 找对应的用户提问（该消息之前最近一条 user 消息）
    user_msg = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.role == "user",
        Message.created_at < msg.created_at,
    ).order_by(Message.created_at.desc()).first()
    pair = f"问题：{user_msg.content if user_msg else ''}\n讲解：{msg.content[:1000]}"
    settings = get_settings()
    if settings.ai_mock:
        return {
            "question_text": (user_msg.content if user_msg else "").strip(),
            "options": [],
            "answer": "",
            "analysis": msg.content[:300],
            "mock": True,
        }
    gateway = get_gateway()
    raw = asyncio.run(gateway.complete_json([
        {"role": "system", "content": "只输出 JSON"},
        {"role": "user", "content": EXTRACT_PROMPT + pair},
    ]))
    return {
        "question_text": (raw.get("question_text") or "").strip(),
        "options": raw.get("options") or [],
        "answer": (raw.get("answer") or "").strip(),
        "analysis": (raw.get("analysis") or "").strip(),
        "mock": False,
    }
