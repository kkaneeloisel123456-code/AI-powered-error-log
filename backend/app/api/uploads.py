"""图片上传：创建 OCR 任务（multipart，EX-01/02 校验）。"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import require_auth
from app.db.session import get_db
from app.schemas.imports import UploadResponse
from app.services import import_service
from app.tasks.runner import schedule_ocr_task

router = APIRouter(prefix="/api/v1", tags=["uploads"], dependencies=[Depends(require_auth)])


@router.post("/uploads", response_model=UploadResponse, status_code=201)
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    client_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    client_id = client_id or uuid.uuid4().hex
    content = await file.read()
    task = import_service.validate_and_store_image(db, file.filename or "image", content, client_id)
    db.flush()
    # 先提交任务行：依赖清理晚于 BackgroundTasks 执行，未提交后台任务读不到
    db.commit()
    if task.status in ("uploaded", "queued"):
        schedule_ocr_task(task.id, background_tasks)
    progress = __import__("json").loads(task.progress_json or "{}")
    return {"task_id": task.id, "status": task.status, "progress": progress}
