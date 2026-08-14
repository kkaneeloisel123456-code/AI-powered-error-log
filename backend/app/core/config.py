"""应用配置（pydantic-settings，环境变量 .env 覆盖）。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Recall 本地单机配置。所有路径默认为项目 data/ 目录。"""

    # 数据与监听
    data_dir: Path = Path(__file__).resolve().parents[3] / "data"
    host: str = "127.0.0.1"  # 隐私默认：仅本机监听，局域网访问需显式开启
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    timezone: str = "Asia/Shanghai"

    # DeepSeek（OpenAI 兼容协议）
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout_connect: float = 10.0
    deepseek_timeout_generate: float = 60.0

    # 降级开关（风险 R1/R2 缓解：mock 保证主流程可演示）
    ai_mock: bool = True
    ocr_mock: bool = True

    log_level: str = "INFO"

    class Config:
        env_prefix = "RECALL_"
        env_file = ".env"
        extra = "ignore"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "recall.sqlite3"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def token_file(self) -> Path:
        return self.data_dir / "auth" / "token.key"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.upload_dir, self.backup_dir, self.token_file.parent):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
