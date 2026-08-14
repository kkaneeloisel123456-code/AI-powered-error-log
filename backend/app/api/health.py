"""健康检查与运行模式信息。"""
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["health"])

VERSION = "0.1.0"


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": VERSION,
        "mock": {"ai": settings.ai_mock, "ocr": settings.ocr_mock},
        "bind": f"{settings.host}:{settings.port}",
    }
