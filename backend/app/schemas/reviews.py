"""复习 DTO（开发规划 4.3 契约）。"""
from datetime import date

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    subject_ids: list[int] = []
    count: int = Field(default=5, ge=1, le=20)
    difficulty: str = "auto"  # easy/medium/hard/auto
    scope: str = "due"  # all/due/weak/manual
    mistake_ids: list[str] = []


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str


class GenerateRequest(BaseModel):
    session_id: str
    replace_variant_id: str | None = None


class VariantOut(BaseModel):
    variant_id: str
    source_mistake_id: str
    question_text: str
    options: list[str] = []
    answer: str = ""
    analysis: str = ""
    knowledge_point: str = ""


class GenerateResponse(BaseModel):
    session_id: str
    status: str
    variants: list[dict]
    replace_left: int


class AnswerIn(BaseModel):
    variant_id: str
    answer: str = ""
    unsure: bool = False


class SubmitRequest(BaseModel):
    answers: list[AnswerIn] = []
    confirm_submit: bool = True


class SubmitResponse(BaseModel):
    session_id: str
    status: str


class RegradeRequest(BaseModel):
    variant_id: str


class PlanItemOut(BaseModel):
    id: str
    mistake_id: str
    due_date: str
    interval_days: int
    ease_factor: float
    status: str
    last_quality: int | None
    question_excerpt: str
    subject_name: str
    knowledge_point: str
    mistake_status: str


class TodayPlanOut(BaseModel):
    date: str
    due_count: int
    estimated_minutes: int
    items: list[PlanItemOut]


class WeekPlanOut(BaseModel):
    start: str
    days: list[dict]


class ExamPlanRequest(BaseModel):
    exam_date: date
    daily_target: int = Field(default=10, ge=1, le=100)


class ExamPlanOut(BaseModel):
    exam_date: str
    daily_target: int
    total: int
    items: list[dict]


class PlanItemAction(BaseModel):
    action: str = Field(pattern="^(complete|skip|reset)$")
