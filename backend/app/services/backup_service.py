"""备份与恢复（PRD 5.7 / 规划 2.6）：SQLite + 图片打包为 zip；导入前格式校验。"""
import io
import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import ApiError

logger = logging.getLogger("recall")


def create_backup() -> tuple[bytes, str]:
    settings = get_settings()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if settings.db_path.exists():
            zf.write(settings.db_path, "recall.sqlite3")
        if settings.upload_dir.exists():
            for f in settings.upload_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f"uploads/{f.relative_to(settings.upload_dir)}")
    name = f"Recall_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return buf.getvalue(), name


def restore_backup(content: bytes) -> dict:
    """恢复：先校验 zip 含 recall.sqlite3，再整体替换数据文件（需重启生效）。"""
    settings = get_settings()
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            if "recall.sqlite3" not in names:
                raise ApiError("VALIDATION_ERROR", "备份包无效：缺少 recall.sqlite3", {})
            bad = zf.testzip()
            if bad:
                raise ApiError("VALIDATION_ERROR", f"备份包损坏：{bad}", {})
    except ApiError:
        raise
    except zipfile.BadZipFile as err:
        raise ApiError("VALIDATION_ERROR", "备份包无效：不是有效的 zip 文件", {}) from err

    # 写入 staging 目录后替换（失败可回滚）
    staging = settings.data_dir / f".restore_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    staging.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        zf.extractall(staging)
    try:
        db_src = staging / "recall.sqlite3"
        shutil.copy2(db_src, settings.db_path)
        upload_src = staging / "uploads"
        if upload_src.exists():
            shutil.rmtree(settings.upload_dir, ignore_errors=True)
            shutil.copytree(upload_src, settings.upload_dir)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    logger.info("backup_restored")
    return {"restored": True, "restart_required": True}
