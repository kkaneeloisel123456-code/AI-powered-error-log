"""pytest 共享夹具：临时数据目录 + TestClient + 已鉴权客户端。"""
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("RECALL_AI_MOCK", "true")
os.environ.setdefault("RECALL_OCR_MOCK", "true")


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("RECALL_DATA_DIR", str(tmp_path / "data"))
    return tmp_path / "data"


@pytest.fixture()
def client(data_dir: Path):
    from app.core.config import get_settings
    from app.db.session import reset_engine
    from app.main import create_app

    get_settings.cache_clear()
    reset_engine()
    # 聚合缓存为模块级全局，测试间必须清空（生产环境靠 TTL 自过期）
    from app.services.dashboard_service import invalidate_cache
    invalidate_cache()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
    reset_engine()
    invalidate_cache()


@pytest.fixture()
def token(data_dir: Path, client: TestClient) -> str:
    """读取本地 token 文件（应用启动时生成）。"""
    return (data_dir / "auth" / "token.key").read_text(encoding="utf-8").strip()


@pytest.fixture()
def auth_client(client: TestClient, token: str) -> TestClient:
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
