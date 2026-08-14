"""题目导入：候选题确认导入（幂等去重）+ 文本录入 AI 补全。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_auth
from app.db.session import get_db
from app.schemas.imports import ImportRequest, ImportResponse, TextImportRequest, TextSuggestResponse
from app.services import import_service

router = APIRouter(prefix="/api/v1/problems", tags=["problems"], dependencies=[Depends(require_auth)])


@router.post("/import", response_model=ImportResponse, status_code=201)
def import_problems(payload: ImportRequest, db: Session = Depends(get_db)):
    candidates = [c.model_dump() for c in payload.candidates]
    result = import_service.import_candidates(db, candidates, payload.idempotency_key)
    if payload.task_id:
        import_service.mark_source_task_done(db, payload.task_id)
    return result


@router.post("/text", response_model=TextSuggestResponse)
def text_import(payload: TextImportRequest, db: Session = Depends(get_db)):
    """文本录入：AI 补全归档字段（不落库，确认后走 POST /mistakes）。"""
    return import_service.text_suggest(db, payload.model_dump())
