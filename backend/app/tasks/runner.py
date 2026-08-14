"""异步任务执行器（开发规划 3.4 / PRD 8.8）。

- OCR 任务状态机：uploaded -> ocr_running -> splitting -> awaiting_confirm -> done
                    `-----------------------------> failed（可重试/换图/文本兜底）
- 任务持久化到 tasks 表（幂等键 + 重启恢复扫描），不引入 Celery；
- 前端通过 GET /tasks/{id} 轮询进度。
"""
import json
import logging

from fastapi import BackgroundTasks

from app.core.errors import ApiError
from app.db.models import Task
from app.db.session import get_sessionmaker, session_scope
from app.ocr.client import get_ocr_client
from app.ai.gateway import get_gateway
from app.ai.prompts import SPLIT_PROMPT

logger = logging.getLogger("recall")

INTERRUPTIBLE_STATUSES = {"uploaded", "queued", "ocr_running", "splitting"}


def _update_task(db, task: Task, status: str, progress: dict | None = None,
                 error: str | None = None, result: dict | None = None) -> None:
    task.status = status
    if progress is not None:
        task.progress_json = json.dumps(progress, ensure_ascii=False)
    if error is not None:
        task.error = error
    if result is not None:
        task.result_json = json.dumps(result, ensure_ascii=False)


def schedule_ocr_task(task_id: str, background_tasks: BackgroundTasks) -> None:
    background_tasks.add_task(run_ocr_task, task_id)


def run_ocr_task(task_id: str) -> None:
    """OCR -> AI 拆题流水线（独立事务执行，服务重启后可恢复）。"""
    with session_scope() as db:
        task = db.get(Task, task_id)
        if task is None or task.status in ("done", "failed"):
            return
        payload = json.loads(task.payload_json or "{}")
        image_path = payload.get("image_path", "")
        try:
            _update_task(db, task, "ocr_running", {"phase": "ocr_running", "percent": 10})
            db.commit()
            ocr_text = _run_ocr(image_path)
            _update_task(db, task, "splitting", {"phase": "splitting", "percent": 50})
            db.commit()
            candidates = _split_candidates(ocr_text)
            if not candidates:
                raise ApiError("OCR_FAILED", "未识别到清晰文字，请重拍或换图；可改用文本录入", {})
            _update_task(db, task, "awaiting_confirm",
                         {"phase": "awaiting_confirm", "percent": 70},
                         result={"ocr_text": ocr_text, "candidates": candidates})
        except ApiError as err:
            _update_task(db, task, "failed", {"phase": "failed", "percent": 100}, error=err.message)
            logger.warning("ocr_task_failed", extra={"task_id": task_id, "error": err.code})
        except Exception as err:  # 意外异常也落 failed，不丢任务
            _update_task(db, task, "failed", {"phase": "failed", "percent": 100}, error=str(err))
            logger.exception("ocr_task_error", extra={"task_id": task_id})


def _run_ocr(image_path: str) -> str:
    import asyncio
    from pathlib import Path
    client = get_ocr_client()
    return asyncio.run(client.recognize(Path(image_path)))


def _split_candidates(ocr_text: str) -> list[dict]:
    """AI 拆题；mock 模式按题号切分内置样例。"""
    from app.core.config import get_settings
    settings = get_settings()
    if settings.ai_mock:
        return _mock_split(ocr_text)
    gateway = get_gateway()
    import asyncio
    raw = asyncio.run(gateway.complete_json([
        {"role": "system", "content": "只输出 JSON 数组"},
        {"role": "user", "content": SPLIT_PROMPT + ocr_text},
    ]))
    candidates = []
    for item in raw if isinstance(raw, list) else []:
        conf = item.get("confidence", {})
        confidence_fields = [k for k, v in conf.items() if isinstance(v, (int, float)) and v < 0.7]
        candidates.append({
            "question_text": (item.get("question_text") or "").strip(),
            "options": item.get("options") or [],
            "answer": (item.get("answer") or "").strip(),
            "analysis": (item.get("analysis") or "").strip(),
            "knowledge_point": (item.get("knowledge_point") or "").strip(),
            "confidence_fields": confidence_fields,
        })
    return [c for c in candidates if c["question_text"]]


def _mock_split(ocr_text: str) -> list[dict]:
    """mock 拆题：按「第N题」切分，第 1 题答案低置信（演示高亮流程）。"""
    import re
    parts = re.split(r"第\s*(\d+)\s*题[:：]?", ocr_text)
    candidates = []
    idx = 0
    for i in range(1, len(parts), 2):
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if not body:
            continue
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        options = [ln for ln in lines if re.match(r"^[A-D][.、]", ln)]
        question_lines = [ln for ln in lines if not re.match(r"^[A-D][.、]", ln)]
        candidates.append({
            "question_text": " ".join(question_lines),
            "options": options,
            "answer": "B" if idx == 0 else "",
            "analysis": "（演示模式）由动能定理 / 导数单调性分析可得，配置 DeepSeek Key 后获得真实解析。",
            "knowledge_point": "牛顿运动定律" if idx == 0 else "函数与导数",
            "confidence_fields": ["answer", "analysis"] if idx == 0 else [],
        })
        idx += 1
    return candidates


def recover_interrupted_tasks() -> None:
    """重启恢复：uploaded/ocr_running/splitting 状态的任务重新入队（R6 缓解）。"""
    with session_scope() as db:
        tasks = db.query(Task).filter(Task.status.in_(INTERRUPTIBLE_STATUSES),
                                      Task.type == "ocr").all()
        for task in tasks:
            task.status = "queued"
        db.commit()
    if tasks:
        logger.info("recovered_interrupted_tasks", extra={"count": len(tasks)})
        # 恢复后逐个重跑（单机串行）
        from app.services.import_service import run_pending_ocr_tasks
        run_pending_ocr_tasks()
