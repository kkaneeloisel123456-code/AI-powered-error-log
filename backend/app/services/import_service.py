"""录入业务：上传校验、OCR 任务、候选题、导入（幂等+去重）、文本录入 AI 补全。"""
import asyncio
import hashlib
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gateway import get_gateway
from app.ai.prompts import CLASSIFY_PROMPT
from app.core.config import get_settings
from app.core.errors import ApiError, not_found
from app.db.base import gen_id
from app.db.models import KnowledgePoint, Mistake, Problem, STATUS_COLORS, Task
from app.db.session import get_sessionmaker, session_scope
from app.services.mistake_service import serialize_detail
from app.tasks.runner import run_ocr_task

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB


# ---------- 上传与任务 ----------

def validate_and_store_image(db: Session, filename: str, content: bytes, client_id: str) -> Task:
    """校验（EX-01/02）→ 落盘 → 创建/复用任务（幂等）。"""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise ApiError("VALIDATION_ERROR", "仅支持 JPG / PNG / WebP / HEIC 图片，大小不超过 10MB",
                       {"field": "file"})
    if len(content) > MAX_SIZE:
        raise ApiError("VALIDATION_ERROR", "图片过大，请压缩后上传（≤10MB）", {"field": "file"})

    # 幂等：同 client_id 未完成的任务直接复用（前端重试不产生重复任务）
    existing = db.scalar(select(Task).where(Task.idempotency_key == f"upload:{client_id}",
                                            Task.type == "ocr").order_by(Task.created_at.desc()))
    if existing and existing.status not in ("done", "failed"):
        return existing

    task = Task(id=gen_id("task"), type="ocr", status="uploaded",
                idempotency_key=f"upload:{client_id}",
                payload_json=json.dumps({}),
                progress_json=json.dumps({"phase": "uploaded", "percent": 0}))
    db.add(task)
    db.flush()
    settings = get_settings()
    image_path = settings.upload_dir / f"{task.id}{ext}"
    image_path.write_bytes(content)
    task.payload_json = json.dumps({"image_path": str(image_path), "client_id": client_id,
                                    "filename": filename})
    return task


def get_task_view(db: Session, task_id: str) -> dict:
    task = db.get(Task, task_id)
    if task is None:
        raise not_found("任务", task_id)
    result_url = None
    if task.status in ("awaiting_confirm", "done"):
        result_url = f"/api/v1/tasks/{task_id}/candidates"
    return {
        "task_id": task.id,
        "type": task.type,
        "status": task.status,
        "progress": json.loads(task.progress_json or "{}"),
        "result_url": result_url,
        "error": task.error,
    }


def get_candidates(db: Session, task_id: str) -> dict:
    task = db.get(Task, task_id)
    if task is None:
        raise not_found("任务", task_id)
    if task.status == "failed":
        raise ApiError("OCR_FAILED", task.error or "识别失败，请重试", {"task_id": task_id})
    result = json.loads(task.result_json or "{}")
    return {
        "task_id": task_id,
        "status": task.status,
        "candidates": result.get("candidates", []),
    }


def retry_task(db: Session, task_id: str) -> dict:
    task = db.get(Task, task_id)
    if task is None:
        raise not_found("任务", task_id)
    task.status = "queued"
    task.error = None
    db.commit()
    from app.tasks.runner import run_ocr_task
    # 单机场景：同步后台线程执行（BackgroundTasks 无法从 service 触发）
    import threading
    threading.Thread(target=run_ocr_task, args=(task_id,), daemon=True).start()
    return get_task_view(db, task_id)


def cancel_task(db: Session, task_id: str) -> None:
    task = db.get(Task, task_id)
    if task is None:
        raise not_found("任务", task_id)
    if task.status in ("uploaded", "queued", "ocr_running", "splitting"):
        task.status = "failed"
        task.error = "任务已取消"


def run_pending_ocr_tasks() -> None:
    """恢复/排队任务执行（单机串行，R6/PRD 8.8）。"""
    import threading
    with session_scope() as db:
        pending = db.query(Task).filter(Task.type == "ocr", Task.status.in_(("uploaded", "queued"))).all()
        ids = [t.id for t in pending]
    for task_id in ids:
        threading.Thread(target=run_ocr_task, args=(task_id,), daemon=True).start()


# ---------- 候选导入 ----------

def _question_hash(question_text: str) -> str:
    normalized = re.sub(r"\s+", "", question_text)
    return hashlib.sha256(normalized.encode()).hexdigest()


def resolve_kp(db: Session, kp_name: str, subject_id: int | None = None) -> tuple[int | None, int | None]:
    """知识点名 -> (kp_id, subject_id)。"""
    if not kp_name:
        return None, subject_id
    stmt = select(KnowledgePoint).where(KnowledgePoint.name == kp_name)
    kp = db.scalar(stmt)
    if kp is None:
        stmt = select(KnowledgePoint).where(KnowledgePoint.name.like(f"%{kp_name}%"))
        kp = db.scalar(stmt)
    if kp:
        return kp.id, kp.subject_id
    return None, subject_id


def import_candidates(db: Session, candidates: list[dict], idempotency_key: str | None) -> dict:
    """确认导入：题干去重 + 幂等键 + 任务完成标记。"""
    if idempotency_key:
        existing = db.scalar(select(Task).where(Task.idempotency_key == f"import:{idempotency_key}",
                                                Task.type == "import"))
        if existing:
            return json.loads(existing.result_json or "{}")

    imported, duplicates = 0, 0
    mistake_ids: list[str] = []
    for cand in candidates:
        question_text = (cand.get("question_text") or "").strip()
        if not question_text:
            raise ApiError("VALIDATION_ERROR", "题干不能为空", {"field": "question_text"})
        if db.scalar(select(Problem).where(Problem.question_text == question_text)):
            duplicates += 1
            continue
        kp_id, subject_id = resolve_kp(db, cand.get("knowledge_point") or "", cand.get("subject_id"))
        if not subject_id:
            # 默认归入第一个学科，允许后续编辑（MVP 单用户场景兜底）
            from app.db.models import Subject
            first = db.scalar(select(Subject).order_by(Subject.sort_order).limit(1))
            if first is None:
                raise ApiError("VALIDATION_ERROR", "请先创建学科", {})
            subject_id = first.id
        problem = Problem(
            id=gen_id("p"),
            source_type="image",
            question_text=question_text,
            options_json=json.dumps(cand.get("options") or [], ensure_ascii=False),
            answer_text=(cand.get("answer") or "").strip(),
            analysis=(cand.get("analysis") or "").strip(),
            difficulty=(cand.get("difficulty") or "medium"),
        )
        db.add(problem)
        db.flush()
        mistake = Mistake(
            id=gen_id("m"),
            problem_id=problem.id,
            subject_id=subject_id,
            kp_id=kp_id,
            error_type=(cand.get("error_type") or "other"),
            status="pending",
            color=STATUS_COLORS["pending"],
            tags_json=json.dumps(cand.get("tags") or [], ensure_ascii=False),
            source="image",
            source_meta=json.dumps({"task_id": cand.get("task_id", "")}, ensure_ascii=False),
            first_seen_at=datetime.now(),
        )
        db.add(mistake)
        db.flush()
        # 新错题默认次日进入复习计划（PRD 5.5）
        from app.services.plan_service import ensure_plan_item
        ensure_plan_item(db, mistake, due=date.today() + timedelta(days=1))
        imported += 1
        mistake_ids.append(mistake.id)

    result = {"imported": imported, "duplicates": duplicates, "mistake_ids": mistake_ids}
    if idempotency_key:
        db.add(Task(id=gen_id("task"), type="import", status="done",
                    idempotency_key=f"import:{idempotency_key}",
                    result_json=json.dumps(result, ensure_ascii=False)))
    return result


def mark_source_task_done(db: Session, task_id: str) -> None:
    task = db.get(Task, task_id)
    if task and task.status == "awaiting_confirm":
        task.status = "done"
        task.progress_json = json.dumps({"phase": "done", "percent": 100})


# ---------- 文本录入 + AI 补全 ----------

def text_suggest(db: Session, payload: dict) -> dict:
    """AI 自动归类：学科/知识点/错因/难度建议（结果用户可修改后确认）。"""
    question = payload["question_text"]
    settings = get_settings()
    if settings.ai_mock:
        subject_id, kp_id, kp_name = _mock_classify(db, question)
        return {
            "subject_id": subject_id, "subject_name": "",
            "kp_id": kp_id, "kp_name": kp_name,
            "error_type": _mock_error_type(question),
            "difficulty": "medium",
            "mock": True,
        }
    gateway = get_gateway()
    raw = asyncio.run(gateway.complete_json([
        {"role": "system", "content": "只输出 JSON"},
        {"role": "user", "content": CLASSIFY_PROMPT + question
         + f"\n答案：{payload.get('answer_text', '')}\n解析：{payload.get('analysis', '')[:200]}"},
    ]))
    kp_id, subject_id = resolve_kp(db, raw.get("knowledge_point", ""))
    return {
        "subject_id": subject_id,
        "kp_id": kp_id,
        "kp_name": raw.get("knowledge_point", ""),
        "error_type": raw.get("error_type", "other"),
        "difficulty": raw.get("difficulty", "medium"),
        "mock": False,
    }


def _mock_classify(db: Session, question: str) -> tuple[int | None, int | None, str]:
    """mock 归档：按知识点名称关键词匹配内置知识树（全名优先，其次分词片段）。"""
    kps = db.query(KnowledgePoint).all()
    best: tuple[int, int, str, int] | None = None  # (subject, kp, name, matched_len)
    for kp in kps:
        if not kp.name:
            continue
        if kp.name in question:
            if best is None or len(kp.name) > best[3]:
                best = (kp.subject_id, kp.id, kp.name, len(kp.name))
            continue
        # 分词片段匹配（如「函数与导数」拆出「函数」/「导数」）
        for token in kp.name.split("与"):
            if len(token) >= 2 and token in question:
                if best is None or len(token) > best[3]:
                    best = (kp.subject_id, kp.id, kp.name, len(token))
    if best:
        return best[0], best[1], best[2]
    return None, None, ""


def _mock_error_type(question: str) -> str:
    if any(w in question for w in ("计算", "求", "解")):
        return "calculation"
    if any(w in question for w in ("概念", "定义", "性质")):
        return "concept"
    return "knowledge"
