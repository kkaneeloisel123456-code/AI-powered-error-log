"""录入 DTO（开发规划 4.3 契约）。"""
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    task_id: str
    status: str
    progress: dict


class CandidateIn(BaseModel):
    question_text: str = Field(min_length=1)
    options: list[str] = []
    answer: str = ""
    analysis: str = ""
    knowledge_point: str = ""
    difficulty: str = "medium"
    error_type: str = "other"
    tags: list[str] = []
    subject_id: int | None = None
    confidence_fields: list[str] = []
    task_id: str | None = None


class ImportRequest(BaseModel):
    candidates: list[CandidateIn] = Field(min_length=1)
    idempotency_key: str | None = None
    task_id: str | None = None


class ImportResponse(BaseModel):
    imported: int
    duplicates: int
    mistake_ids: list[str]


class TextImportRequest(BaseModel):
    question_text: str = Field(min_length=1)
    options: list[str] = []
    answer_text: str = ""
    analysis: str = ""
    use_ai: bool = True


class TextSuggestResponse(BaseModel):
    subject_id: int | None = None
    subject_name: str = ""
    kp_id: int | None = None
    kp_name: str = ""
    error_type: str = "other"
    difficulty: str = "medium"
    mock: bool = False
