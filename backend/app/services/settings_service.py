"""设置读取/更新：AI 配置（Key 加密 + 掩码）、隐私、默认复习配置。"""
import json

from sqlalchemy.orm import Session

from app.ai.gateway import AiGateway
from app.core.auth import ensure_token_file, mask_token
from app.core.config import get_settings
from app.core.crypto import mask_secret
from app.db.models import Setting
from app.db.seed import DEFAULT_SETTINGS


def _get(db: Session, key: str) -> dict:
    row = db.get(Setting, key)
    if row is None:
        return dict(DEFAULT_SETTINGS.get(key, {}))
    try:
        value = json.loads(row.value_json)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _set(db: Session, key: str, value: dict) -> None:
    row = db.get(Setting, key)
    data = json.dumps(value, ensure_ascii=False)
    if row is None:
        db.add(Setting(key=key, value_json=data))
    else:
        row.value_json = data


def get_settings_view(db: Session) -> dict:
    settings = get_settings()
    ai = _get(db, "ai")
    privacy = _get(db, "privacy")
    default_review = _get(db, "default_review")
    api_key = AiGateway.get_api_key(db)
    return {
        "ai": {
            "provider": "deepseek",
            "base_url": settings.deepseek_base_url,
            "model": settings.deepseek_model,
            "api_key_masked": mask_secret(api_key) if api_key else "",
            "has_api_key": bool(api_key),
            "mock": settings.ai_mock,
        },
        "privacy": {
            "send_question_to_ai": privacy.get("send_question_to_ai", True),
            "lan_enabled": privacy.get("lan_enabled", False),
        },
        "default_review": default_review,
        "token_masked": mask_token(ensure_token_file()),
        "version": "0.1.0",
    }


def update_settings(db: Session, payload: dict) -> dict:
    """部分更新；API Key 单独加密落盘。"""
    if "api_key" in payload and payload["api_key"]:
        AiGateway.set_api_key(db, payload["api_key"])
    if "ai" in payload and payload["ai"]:
        ai = payload["ai"]
        allowed = {k: v for k, v in ai.items() if k in ("provider", "base_url", "model") and v}
        if allowed:
            _set(db, "ai", {**_get(db, "ai"), **allowed})
    if "privacy" in payload and payload["privacy"]:
        _set(db, "privacy", {**_get(db, "privacy"), **payload["privacy"]})
    if "default_review" in payload and payload["default_review"]:
        _set(db, "default_review", {**_get(db, "default_review"), **payload["default_review"]})
    return get_settings_view(db)
