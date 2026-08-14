"""单用户启动引导与本地 Token 鉴权（T-M1-01 前置，M0 落地骨架）。"""
import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import ensure_token_file, is_rate_limited, mask_token, require_auth, verify_token
from app.db.models import Setting
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class SetupResponse(BaseModel):
    configured: bool
    token: str | None = None  # 仅首次揭示一次，之后为 null
    token_masked: str


def _token_revealed(db: Session) -> bool:
    row = db.get(Setting, "auth")
    if row is None:
        return False
    value = json.loads(row.value_json)
    return bool(value.get("token_revealed", False))


@router.get("/status")
def status(request: Request, db: Session = Depends(get_db)) -> dict:
    authenticated = False
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        authenticated = verify_token(auth.removeprefix("Bearer ").strip())
    return {"configured": True, "authenticated": authenticated}


@router.post("/setup", response_model=SetupResponse)
def setup(db: Session = Depends(get_db)) -> SetupResponse:
    """首次进入：揭示本地 Token 一次；之后仅返回掩码。"""
    token = ensure_token_file()
    row = db.get(Setting, "auth")
    revealed = False
    if row is not None:
        value = json.loads(row.value_json)
        revealed = bool(value.get("token_revealed", False))
    if not revealed:
        value = {"token_revealed": True}
        if row is None:
            db.add(Setting(key="auth", value_json=json.dumps(value)))
        else:
            row.value_json = json.dumps(value)
    return SetupResponse(configured=True, token=None if revealed else token, token_masked=mask_token(token))


class VerifyRequest(BaseModel):
    token: str


@router.get("/verify")
def verify(_: str = Depends(require_auth)) -> dict:
    # 能走到这里说明 Bearer 头已通过 require_auth
    return {"valid": True}


@router.post("/verify-token")
def verify_token_body(payload: VerifyRequest) -> dict:
    """登录页入口：提交 Token 换取有效状态（限流防爆破）。"""
    if is_rate_limited("auth_verify", limit=10, window_s=60):
        from app.core.errors import ApiError
        raise ApiError("RATE_LIMITED", "尝试次数过多，请稍后再试", {})
    if not verify_token(payload.token):
        from app.core.errors import ApiError
        raise ApiError("NOT_AUTHENTICATED", "本地访问令牌无效", {})
    return {"valid": True, "token": payload.token}
