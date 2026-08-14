"""错题 DTO（开发规划 4.4 契约）。"""
from datetime import datetime

from pydantic import BaseModel, Field


class MistakeListItem(BaseModel):
    """GET /mistakes 列表项（契约样例）。"""
    id: str
    subject_id: int
    subject_name: str = ""
    kp_id: int | None = None
    knowledge_point: str = ""
    question_excerpt: str
    status: str
    color: str
    tags: list[str] = []
    error_type: str
    source: str
    last_reviewed_at: datetime | None = None
    review_count: int
    correct_count: int
    wrong_count: int
    mastery: float
    created_at: datetime


class MistakeListResponse(BaseModel):
    items: list[MistakeListItem]
    total: int
    page: int
    page_size: int


class MistakeDetail(MistakeListItem):
    question_text: str
    options: list[str] = []
    answer_text: str
    analysis: str
    difficulty: str
    source_image_url: str | None = None
    note: str = ""
    first_seen_at: datetime | None = None
    due_date: str | None = None  # 最近待复习计划项到期日（ISO 日期）


class MistakeCreate(BaseModel):
    """新建错题（手工新建 / 文本录入共用）。"""
    question_text: str = Field(min_length=1)
    options: list[str] = []
    answer_text: str = ""
    analysis: str = ""
    difficulty: str = "medium"
    subject_id: int
    kp_id: int | None = None
    error_type: str = "other"
    status: str = "pending"
    color: str | None = None
    tags: list[str] = []
    note: str = ""
    source: str = "text"


class MistakeUpdate(BaseModel):
    """PATCH /mistakes/{id}：全字段可选。"""
    question_text: str | None = None
    options: list[str] | None = None
    answer_text: str | None = None
    analysis: str | None = None
    difficulty: str | None = None
    subject_id: int | None = None
    kp_id: int | None = None
    error_type: str | None = None
    status: str | None = None
    color: str | None = None
    tags: list[str] | None = None
    note: str | None = None


class MistakeBatchRequest(BaseModel):
    """POST /mistakes/batch：批量删除/改状态/打标签。"""
    action: str = Field(pattern="^(delete|set_status|set_color|add_tags|remove_tags)$")
    ids: list[str] = Field(min_length=1)
    value: str | None = None  # set_status/set_color/tags 时的值（tags 用逗号分隔）


class MistakeBatchResponse(BaseModel):
    updated: int
    deleted: int = 0
