"""Recall FastAPI 入口：中间件、路由注册、启动引导。"""
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import ensure_token_file
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import install_request_id_middleware, setup_logging
from app.db.seed import seed_if_empty
from app.db.session import get_sessionmaker

_BACKEND_DIR = Path(__file__).resolve().parents[1]


def run_migrations() -> None:
    """启动时自动迁移到 head（T-M0-04：迁移基线）。"""
    settings = get_settings()
    cfg = AlembicConfig(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{settings.db_path}")
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.ensure_dirs()
    setup_logging(settings.log_level)
    ensure_token_file()
    run_migrations()
    db = get_sessionmaker()()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    # 重启恢复：中断的 OCR 任务重新入队（R6）
    from app.tasks.runner import recover_interrupted_tasks
    recover_interrupted_tasks()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    settings.ensure_dirs()
    app = FastAPI(
        title="Recall - AI 智能错题本",
        version="0.1.0",
        description="单用户本地部署：错题录入、复习、计划、看板、AI 答疑",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_request_id_middleware(app)
    register_exception_handlers(app)

    # 路由注册（按里程碑逐步挂载）
    from app.api import (auth, chat, dashboard, exports, health, mistakes, plans, problems,
                         reviews, settings, subjects, tasks, uploads)
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(mistakes.router)
    app.include_router(subjects.router)
    app.include_router(settings.router)
    app.include_router(uploads.router)
    app.include_router(tasks.router)
    app.include_router(problems.router)
    app.include_router(reviews.router)
    app.include_router(plans.router)
    app.include_router(dashboard.router)
    app.include_router(exports.router)
    app.include_router(chat.router)

    # 原题图片静态服务（仅本机监听，隐私默认）
    from fastapi.staticfiles import StaticFiles
    app.mount("/api/v1/files", StaticFiles(directory=str(get_settings().upload_dir)), name="files")

    return app


app = create_app()
