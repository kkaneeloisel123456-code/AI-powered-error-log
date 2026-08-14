"""学科与知识点路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_auth
from app.db.session import get_db
from app.schemas.subjects import KnowledgePointOut, SubjectCreate, SubjectOut, SubjectUpdate
from app.services import subject_service

router = APIRouter(prefix="/api/v1", tags=["subjects"], dependencies=[Depends(require_auth)])


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    return subject_service.list_subjects(db)


@router.post("/subjects", response_model=SubjectOut, status_code=201)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    subject = subject_service.create_subject(db, payload.name)
    return {"id": subject.id, "name": subject.name, "sort_order": subject.sort_order,
            "is_active": subject.is_active, "mistake_count": 0}


@router.patch("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(subject_id: int, payload: SubjectUpdate, db: Session = Depends(get_db)):
    subject = subject_service.update_subject(db, subject_id, payload.model_dump(exclude_none=True))
    return {"id": subject.id, "name": subject.name, "sort_order": subject.sort_order,
            "is_active": subject.is_active, "mistake_count": 0}


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    subject_service.delete_subject(db, subject_id)


@router.get("/knowledge-points", response_model=list[KnowledgePointOut])
def list_knowledge_points(subject_id: int | None = None, db: Session = Depends(get_db)):
    return subject_service.list_knowledge_points(db, subject_id)
