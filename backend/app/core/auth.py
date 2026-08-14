"""单用户本地 Token 鉴权（T-M1-01）。

- Token 首次启动时生成并写入 data/auth/token.key（仅本机可读）；
- 首次通过 POST /auth/setup 揭示一次，之后设置页仅展示掩码；
- 受保护接口要求 Authorization: Bearer <local_token>。
"""
import secrets
import time

from fastapi import Depends, Header

from app.core.config import get_settings
from app.core.errors import ApiError


def ensure_token_file() -> str:
    """确保 token 文件存在，返回当前 token。"""
    path = get_settings().token_file
    if not path.exists():
        path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def verify_token(token: str) -> bool:
    expected = ensure_token_file()
    return secrets.compare_digest(token.encode(), expected.encode())


async def require_auth(authorization: str | None = Header(default=None)) -> str:
    """FastAPI 依赖：校验 Bearer token，返回 token 原文。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("NOT_AUTHENTICATED", "未登录：缺少本地访问令牌", {})
    token = authorization.removeprefix("Bearer ").strip()
    # 恒定时间比较，防时序侧信道
    if not secrets.compare_digest(token.encode(), ensure_token_file().encode()):
        raise ApiError("NOT_AUTHENTICATED", "本地访问令牌无效", {})
    return token


def mask_token(token: str) -> str:
    return f"{token[:6]}••••{token[-4:]}" if len(token) > 14 else "••••••••"


def is_rate_limited(key: str, limit: int, window_s: float = 60.0) -> bool:
    """进程内简易限流（登录尝试等），MVP 单机够用。"""
    state: dict[str, list[float]] = getattr(is_rate_limited, "_state", {})
    now = time.monotonic()
    hits = [t for t in state.get(key, []) if now - t < window_s]
    if len(hits) >= limit:
        state[key] = hits
        return True
    hits.append(now)
    state[key] = hits
    return False
