"""统一错误码与异常处理。

错误体契约（开发规划 4.1）：
    {"code": "...", "message": "...", "details": {...}}
错误码：VALIDATION_ERROR / NOT_FOUND / CONFLICT / RATE_LIMITED /
       OCR_FAILED / AI_UNAVAILABLE / INTERNAL_ERROR / NOT_AUTHENTICATED
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("recall")

CODE_STATUS = {
    "VALIDATION_ERROR": 422,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "RATE_LIMITED": 429,
    "OCR_FAILED": 422,
    "AI_UNAVAILABLE": 503,
    "INTERNAL_ERROR": 500,
    "NOT_AUTHENTICATED": 401,
}


class ApiError(Exception):
    """业务异常：router/service 抛出，全局处理器统一转错误体。"""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = CODE_STATUS.get(code, 500)


def not_found(entity: str, entity_id: str) -> ApiError:
    return ApiError("NOT_FOUND", f"{entity}不存在：{entity_id}", {"entity": entity, "id": entity_id})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "请求参数校验失败",
                "details": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def internal_handler(request: Request, exc: Exception):
        # 不向前端暴露堆栈，仅落结构化日志
        logger.exception(
            "unhandled_error",
            extra={"request_id": getattr(request.state, "request_id", None), "path": request.url.path},
        )
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "服务内部错误，请稍后重试", "details": {}},
        )
