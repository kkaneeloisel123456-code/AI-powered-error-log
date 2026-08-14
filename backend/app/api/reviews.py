"""复习路由（薄层）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_auth
from app.db.session import get_db
from app.schemas.reviews import (
    GenerateRequest,
    GenerateResponse,
    RegradeRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SubmitRequest,
    SubmitResponse,
)
from app.services import review_service

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"], dependencies=[Depends(require_auth)])


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
def create_session(payload: SessionCreateRequest, db: Session = Depends(get_db)):
    return review_service.create_session(db, payload.model_dump())


@router.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest, db: Session = Depends(get_db)):
    return review_service.get_variants(db, payload.session_id, payload.replace_variant_id)


@router.post("/{session_id}/submit", response_model=SubmitResponse, status_code=202)
def submit(session_id: str, payload: SubmitRequest, db: Session = Depends(get_db)):
    return review_service.submit_answers(db, session_id, [a.model_dump() for a in payload.answers])


@router.get("/{session_id}/result")
def result(session_id: str, db: Session = Depends(get_db)):
    return review_service.get_result(db, session_id)


@router.post("/{session_id}/regrade")
def regrade(session_id: str, payload: RegradeRequest, db: Session = Depends(get_db)):
    return review_service.regrade_item(db, session_id, payload.variant_id)
