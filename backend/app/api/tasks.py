"""任务查询：轮询状态/进度/候选题，重试与取消。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_auth
from app.db.session import get_db
from app.services import import_service

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"], dependencies=[Depends(require_auth)])


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    return import_service.get_task_view(db, task_id)


@router.get("/{task_id}/candidates")
def get_candidates(task_id: str, db: Session = Depends(get_db)):
    return import_service.get_candidates(db, task_id)


@router.post("/{task_id}/retry")
def retry_task(task_id: str, db: Session = Depends(get_db)):
    return import_service.retry_task(db, task_id)


@router.post("/{task_id}/cancel", status_code=204)
def cancel_task(task_id: str, db: Session = Depends(get_db)):
    import_service.cancel_task(db, task_id)
