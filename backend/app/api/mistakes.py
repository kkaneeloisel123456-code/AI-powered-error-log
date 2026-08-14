"""错题路由（薄层：参数解析 + 响应组装，业务在 service）。"""
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.auth import require_auth
from app.db.session import get_db
from app.schemas.mistakes import (
    MistakeBatchRequest,
    MistakeBatchResponse,
    MistakeCreate,
    MistakeDetail,
    MistakeListResponse,
    MistakeUpdate,
)
from app.services import mistake_service

router = APIRouter(prefix="/api/v1/mistakes", tags=["mistakes"],
                   dependencies=[Depends(require_auth)])


@router.get("", response_model=MistakeListResponse)
def list_mistakes(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="题干关键词/知识点/错因/标签/来源"),
    subject_id: int | None = None,
    status: str | None = None,
    color: str | None = None,
    error_type: str | None = None,
    tags: str | None = Query(default=None, description="逗号分隔多标签"),
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    kp_id: int | None = Query(default=None, description="知识点联动筛选（看板图谱点击）"),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return mistake_service.list_mistakes(
        db, q=q, subject_id=subject_id, status=status, color=color, error_type=error_type,
        tags=tags, source=source, date_from=date_from, date_to=date_to, kp_id=kp_id,
        sort=sort, order=order, page=page, page_size=page_size,
    )


@router.post("", response_model=MistakeDetail, status_code=201)
def create_mistake(
    payload: MistakeCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    mistake = mistake_service.create_mistake(db, payload.model_dump(),
                                             idempotency_key=idempotency_key)
    db.flush()
    return mistake_service.serialize_detail(db, mistake)


@router.get("/{mistake_id}", response_model=MistakeDetail)
def get_mistake(mistake_id: str, db: Session = Depends(get_db)):
    return mistake_service.serialize_detail(db, mistake_service.get_mistake(db, mistake_id))


@router.patch("/{mistake_id}", response_model=MistakeDetail)
def update_mistake(mistake_id: str, payload: MistakeUpdate, db: Session = Depends(get_db)):
    return mistake_service.update_mistake(db, mistake_id, payload.model_dump(exclude_none=True))


@router.delete("/{mistake_id}", status_code=204)
def delete_mistake(mistake_id: str, db: Session = Depends(get_db)):
    mistake_service.delete_mistake(db, mistake_id)


@router.post("/batch", response_model=MistakeBatchResponse)
def batch_operate(payload: MistakeBatchRequest, db: Session = Depends(get_db)):
    return mistake_service.batch_operate(db, payload.action, payload.ids, payload.value)
