"""核心数据模型（PRD 8.4 / 开发规划 4.4 冻结版）。

表：subjects / knowledge_points / problems / mistakes / variants /
    review_logs / plan_items / conversations / messages / tasks /
    settings / audit_logs

索引策略（PRD 8.4）：
    mistakes (subject_id, status)、(kp_id)、(created_at) 复合索引；
    plan_items (due_date, status)；列表查询强制分页。
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, str_pk

# ---- 状态常量（PRD 3.3）----
MISTAKE_STATUSES = ("pending", "wrong", "fixing", "mastered")  # 未开始/未掌握/待巩固/已掌握
STATUS_COLORS = {
    "pending": "#6B7280",   # 灰
    "wrong": "#DC2626",     # 红
    "fixing": "#EA8C00",    # 橙
    "mastered": "#16A34A",  # 绿
}
ERROR_TYPES = ("knowledge", "logic", "reading", "calculation", "concept", "careless", "other")
# 知识性/逻辑/审题/计算/概念混淆/粗心/其他
PLAN_ITEM_STATUSES = ("pending", "completed", "skipped")
TASK_STATUSES = ("uploaded", "ocr_running", "splitting", "awaiting_confirm", "done", "failed",
                 "queued", "grading", "generating")


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class KnowledgePoint(Base):
    """学科下的层级知识树节点（用于归档、图谱与计划加权）。"""
    __tablename__ = "knowledge_points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    path: Mapped[str] = mapped_column(String(512), default="")  # 如 /力学/牛顿运动定律

    __table_args__ = (Index("ix_kp_subject", "subject_id"), Index("ix_kp_parent", "parent_id"))


class Problem(Base):
    """题目（与错题解耦，同一题可被多次记录）。"""
    __tablename__ = "problems"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: __import__("app.db.base", fromlist=["gen_id"]).gen_id("p"))
    source_type: Mapped[str] = mapped_column(String(16), default="text")  # image/text/chat/variant
    source_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # ["A...", ...]
    answer_text: Mapped[str] = mapped_column(Text, default="")
    analysis: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(8), default="medium")  # easy/medium/hard
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Mistake(Base, TimestampMixin):
    """错题条目（用户视角）。"""
    __tablename__ = "mistakes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: __import__("app.db.base", fromlist=["gen_id"]).gen_id("m"))
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    kp_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True)
    error_type: Mapped[str] = mapped_column(String(16), default="other")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    color: Mapped[str] = mapped_column(String(16), default=STATUS_COLORS["pending"])
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # ["周测", ...]
    source: Mapped[str] = mapped_column(String(16), default="image")  # image/text/chat
    source_meta: Mapped[str | None] = mapped_column(Text, nullable=True)  # 任务/会话来源 JSON
    note: Mapped[str] = mapped_column(Text, default="")
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1

    problem: Mapped[Problem] = relationship(lazy="joined")
    subject: Mapped[Subject] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_mistakes_subject_status", "subject_id", "status"),
        Index("ix_mistakes_kp", "kp_id"),
        Index("ix_mistakes_created", "created_at"),
        Index("ix_mistakes_last_reviewed", "last_reviewed_at"),
    )


class Variant(Base):
    """AI 变体题（同源变式）。"""
    __tablename__ = "variants"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: __import__("app.db.base", fromlist=["gen_id"]).gen_id("v"))
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_text: Mapped[str] = mapped_column(Text, default="")
    analysis: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(8), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ReviewLog(Base):
    """复习记录（删除错题后保留，可审计）。"""
    __tablename__ = "review_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mistake_id: Mapped[str] = mapped_column(String(32), nullable=False)  # 有意不加 FK：错题删除后记录保留
    session_id: Mapped[str] = mapped_column(String(32), default="")
    variant_id: Mapped[str] = mapped_column(String(32), default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    quality: Mapped[int] = mapped_column(Integer, default=0)  # q 0-5
    score: Mapped[float] = mapped_column(Float, default=0.0)
    duration_s: Mapped[int] = mapped_column(Integer, default=0)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (Index("ix_review_logs_mistake", "mistake_id"),)


class PlanItem(Base):
    """SM-2 复习计划项。"""
    __tablename__ = "plan_items"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: __import__("app.db.base", fromlist=["gen_id"]).gen_id("plan"))
    mistake_id: Mapped[str] = mapped_column(ForeignKey("mistakes.id"), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)  # EF，下限 1.3
    status: Mapped[str] = mapped_column(String(16), default="pending")
    last_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (Index("ix_plan_items_due_status", "due_date", "status"), Index("ix_plan_items_mistake", "mistake_id"))


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: __import__("app.db.base", fromlist=["gen_id"]).gen_id("conv"))
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: __import__("app.db.base", fromlist=["gen_id"]).gen_id("msg"))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user/assistant/system
    content: Mapped[str] = mapped_column(Text, default="")
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (Index("ix_messages_conv_created", "conversation_id", "created_at"),)


class Task(Base):
    """异步任务表（状态机持久化，重启可恢复；幂等键去重）。"""
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: __import__("app.db.base", fromlist=["gen_id"]).gen_id("task"))
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # ocr/grading/variant
    status: Mapped[str] = mapped_column(String(24), default="queued")
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # {"phase": ..., "percent": ...}
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (Index("ix_tasks_idempotency", "idempotency_key"), Index("ix_tasks_status", "status"))


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, default="null")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class AuditLog(Base):
    """手动调整记录（PRD 5.2：手动调整记录在案）。"""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)  # mistake/plan_item/setting
    entity_id: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # status_change/color_change/edit/...
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)
