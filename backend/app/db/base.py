"""SQLAlchemy 声明式基类与通用工具。"""
import secrets
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def gen_id(prefix: str) -> str:
    """业务 ID：前缀 + 随机串（契约样例：m_1 / task_9f2c1 / rev_01）。

    8 字节 hex（64 位熵）：万级并发批量插入也不会碰撞（4 字节仅 32 位，压测时已实测碰撞）。
    """
    return f"{prefix}_{secrets.token_hex(8)}"


def utcnow() -> datetime:
    """本地时间（无时区），符合契约「ISO 8601 本地时区」。"""
    return datetime.now()


def str_pk(prefix: str) -> Mapped[str]:
    return mapped_column(String(32), primary_key=True, default=lambda: gen_id(prefix))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, server_default=func.now())
