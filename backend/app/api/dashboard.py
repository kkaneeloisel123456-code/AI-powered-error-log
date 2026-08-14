"""看板聚合与知识图谱路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_auth
from app.db.session import get_db
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1", tags=["dashboard"], dependencies=[Depends(require_auth)])


@router.get("/dashboard/summary")
def summary(range_days: int = 7, db: Session = Depends(get_db)):
    if range_days not in (7, 30):
        from app.core.errors import ApiError
        raise ApiError("VALIDATION_ERROR", "range_days 仅支持 7 / 30", {"field": "range_days"})
    return dashboard_service.summary(db, range_days)


@router.get("/graph/knowledge")
def knowledge_graph(subject_id: int | None = None, db: Session = Depends(get_db)):
    return dashboard_service.knowledge_graph(db, subject_id)
