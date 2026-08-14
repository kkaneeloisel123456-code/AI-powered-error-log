"""设置路由：学科配置、API Key（加密+掩码）、隐私、默认复习配置、测试连接、备份恢复。"""
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai.gateway import get_gateway
from app.core.auth import require_auth
from app.db.session import get_db
from app.schemas.settings import SettingsOut, SettingsUpdate, TestAiRequest, TestAiResponse
from app.services import backup_service, settings_service

router = APIRouter(prefix="/api/v1/settings", tags=["settings"], dependencies=[Depends(require_auth)])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return settings_service.get_settings_view(db)


@router.patch("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    return settings_service.update_settings(db, payload.model_dump(exclude_none=True))


@router.post("/test-ai", response_model=TestAiResponse)
async def test_ai(payload: TestAiRequest):
    gateway = get_gateway()
    result = await gateway.ping(
        base_url=payload.base_url, model=payload.model, api_key=payload.api_key,
    )
    return TestAiResponse(**result)


@router.get("/backup")
def download_backup():
    content, name = backup_service.create_backup()
    return Response(
        content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/backup/restore")
async def restore_backup(file: UploadFile = File(...)):
    content = await file.read()
    return backup_service.restore_backup(content)
