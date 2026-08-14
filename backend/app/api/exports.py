"""导出路由（Markdown 文件下载 / PDF 打印排版页）。

本地单机场景：导出页支持 ?token= 以支持 window.open 新标签打印
（默认仍要求 Bearer 头；token 仅本机使用，见 README）。
"""
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.core.auth import require_auth, verify_token
from app.core.errors import ApiError
from app.db.session import get_db
from app.services import export_service

router = APIRouter(prefix="/api/v1/export", tags=["export"])


def _auth_guard(request: Request, authorization: str | None, token: str | None) -> None:
    """Bearer 头或 ?token= 任一有效即放行（导出打印页需新标签打开）。"""
    if authorization and authorization.startswith("Bearer "):
        if verify_token(authorization.removeprefix("Bearer ").strip()):
            return
    if token and verify_token(token):
        return
    raise ApiError("NOT_AUTHENTICATED", "本地访问令牌无效", {})


def _filters(request: Request) -> dict:
    params = request.query_params
    f = {}
    for key in ("q", "subject_id", "status", "error_type", "tags", "source", "date_from", "date_to", "sort", "order"):
        value = params.get(key)
        if value is not None and value != "":
            f[key] = int(value) if key == "subject_id" else value
    return f


@router.get("/markdown")
def export_markdown(request: Request, db: Session = Depends(get_db),
                    authorization: str | None = Header(default=None),
                    token: str | None = Query(default=None)):
    _auth_guard(request, authorization, token)
    content, total = export_service.build_markdown(db, _filters(request))
    filename = f"Recall_错题_{date.today().strftime('%Y%m%d')}.md"
    ascii_name = f"Recall_export_{date.today().strftime('%Y%m%d')}.md"
    # RFC 5987：中文文件名 percent 编码，header 保持 ASCII
    disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'
    return PlainTextResponse(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": disposition},
    )


@router.get("/pdf", response_class=HTMLResponse)
def export_pdf(request: Request, db: Session = Depends(get_db),
               authorization: str | None = Header(default=None),
               token: str | None = Query(default=None)):
    _auth_guard(request, authorization, token)
    html, _ = export_service.build_pdf_html(db, _filters(request))
    return HTMLResponse(html)
