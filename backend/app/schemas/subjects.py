"""学科与知识点 DTO。"""
from pydantic import BaseModel, Field


class KnowledgePointOut(BaseModel):
    id: int
    subject_id: int
    parent_id: int | None
    name: str
    level: int
    path: str


class SubjectOut(BaseModel):
    id: int
    name: str
    sort_order: int
    is_active: bool
    mistake_count: int = 0


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class SubjectUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
