"""复习闭环业务：会话创建、题目检索、变体题生成、交卷批改、报告、重批。

复习会话状态机（开发规划 3.4）：
created -> generating -> answering -> submitting -> grading -> done
"""
import asyncio
import json
import re
import threading
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.gateway import get_gateway
from app.ai.prompts import GRADING_PROMPT, VARIANT_PROMPT
from app.core.errors import ApiError, not_found
from app.db.base import gen_id
from app.db.models import KnowledgePoint, Mistake, PlanItem, Problem, ReviewLog, Task, Variant
from app.db.session import session_scope
from app.services import plan_service

MAX_REPLACES = 3  # 换一题上限（PRD 5.4）


# ---------- 会话与题目检索 ----------

def create_session(db: Session, payload: dict) -> dict:
    subject_ids = payload.get("subject_ids") or []
    count = payload.get("count") or 5
    difficulty = payload.get("difficulty") or "auto"
    scope = payload.get("scope") or "due"
    mistake_ids = payload.get("mistake_ids") or []

    source_mistakes = _retrieve_mistakes(db, subject_ids, count, scope, mistake_ids)
    if not source_mistakes:
        raise ApiError("VALIDATION_ERROR", "没有符合条件的错题，请先录入或调整范围", {"field": "scope"})

    session = Task(id=gen_id("rev"), type="review", status="generating",
                   payload_json=json.dumps({
                       "config": {"subject_ids": subject_ids, "count": count,
                                  "difficulty": difficulty, "scope": scope},
                       "source_mistake_ids": [m.id for m in source_mistakes],
                       "variants": [],
                       "answers": {},
                       "replace_count": 0,
                       "started_at": datetime.now().isoformat(),
                   }, ensure_ascii=False))
    db.add(session)
    db.flush()
    db.commit()
    # 变体生成在后台线程执行（mock 即时、真实 AI 异步）
    threading.Thread(target=_generate_variants_task, args=(session.id,), daemon=True).start()
    return {"session_id": session.id, "status": "generating"}


def _retrieve_mistakes(db: Session, subject_ids: list[int], count: int, scope: str,
                       mistake_ids: list[str]) -> list[Mistake]:
    """题目检索（T-M3-02）：到期优先 + 薄弱加权；相似度在向量服务接入前用薄弱加权兜底。"""
    stmt = select(Mistake)
    if mistake_ids:
        return list(db.query(Mistake).filter(Mistake.id.in_(mistake_ids)).limit(count).all())
    if subject_ids:
        stmt = stmt.where(Mistake.subject_id.in_(subject_ids))
    if scope == "due":
        due_ids = select(PlanItem.mistake_id).where(PlanItem.due_date <= date.today(),
                                                    PlanItem.status == "pending")
        stmt = stmt.where(Mistake.id.in_(due_ids))
        rows = list(db.scalars(stmt.limit(200)).all())
    elif scope == "weak":
        rows = list(db.scalars(stmt.where(Mistake.status.in_(("wrong", "fixing"))).limit(200)).all())
    else:  # all
        rows = list(db.scalars(stmt.limit(200)).all())

    def weakness(m: Mistake) -> float:
        return m.wrong_count * 2 + (1 - m.mastery) * 10

    rows.sort(key=lambda m: weakness(m), reverse=True)
    return rows[:count]


# ---------- 变体题生成 ----------

def _generate_variants_task(session_id: str) -> None:
    with session_scope() as db:
        session = db.get(Task, session_id)
        if session is None:
            return
        payload = json.loads(session.payload_json)
        try:
            variants = []
            for mid in payload["source_mistake_ids"]:
                mistake = db.get(Mistake, mid)
                if mistake is None:
                    continue
                variant = _make_variant(db, mistake, 0)
                if variant:
                    variants.append(variant)
            payload["variants"] = variants
            session.payload_json = json.dumps(payload, ensure_ascii=False)
            session.status = "answering"
        except ApiError as err:
            session.status = "failed"
            session.error = err.message


def _make_variant(db: Session, mistake: Mistake, seed: int) -> dict | None:
    """变体题：mock 换数字；真实模式走 AiGateway（考点一致、数值情境替换）。"""
    problem = mistake.problem
    from app.core.config import get_settings
    settings = get_settings()
    if settings.ai_mock:
        text = re.sub(r"\d+(\.\d+)?", lambda m: str(round(float(m.group()) * (seed + 2), 2)),
                      problem.question_text)
        options = [re.sub(r"\d+(\.\d+)?",
                          lambda m: str(round(float(m.group()) * (seed + 2), 2)), opt)
                   for opt in (json.loads(problem.options_json or "[]") if problem.options_json else [])]
        return {
            "variant_id": gen_id("v"),
            "source_mistake_id": mistake.id,
            "question_text": f"【变式】{text}",
            "options": options,
            "answer": problem.answer_text,
            "analysis": f"（变式）{problem.analysis}",
            "knowledge_point": "",
        }
    gateway = get_gateway()
    raw = asyncio.run(gateway.complete_json([
        {"role": "system", "content": "只输出 JSON"},
        {"role": "user", "content": VARIANT_PROMPT + json.dumps({
            "question_text": problem.question_text,
            "options": json.loads(problem.options_json or "[]") if problem.options_json else [],
            "answer": problem.answer_text,
            "analysis": problem.analysis,
        }, ensure_ascii=False)},
    ]))
    return {
        "variant_id": gen_id("v"),
        "source_mistake_id": mistake.id,
        "question_text": (raw.get("question_text") or "").strip(),
        "options": raw.get("options") or [],
        "answer": (raw.get("answer") or "").strip(),
        "analysis": (raw.get("analysis") or "").strip(),
        "knowledge_point": "",
    }


def get_variants(db: Session, session_id: str, replace_variant_id: str | None = None) -> dict:
    session = _get_session(db, session_id)
    payload = json.loads(session.payload_json)
    variants = payload.get("variants", [])
    replace_left = MAX_REPLACES - payload.get("replace_count", 0)
    if replace_variant_id:
        if payload.get("replace_count", 0) >= MAX_REPLACES:
            raise ApiError("RATE_LIMITED", "换题次数已用完（每题最多换 3 次）", {})
        idx = next((i for i, v in enumerate(variants) if v["variant_id"] == replace_variant_id), None)
        if idx is None:
            raise not_found("变体题", replace_variant_id)
        source = db.get(Mistake, variants[idx]["source_mistake_id"])
        new_variant = _make_variant(db, source, payload.get("replace_count", 0) + 1)
        if new_variant:
            new_variant["variant_id"] = replace_variant_id  # 保持 ID 稳定，前端作答引用不变
            variants[idx] = new_variant
            payload["replace_count"] = payload.get("replace_count", 0) + 1
            payload["variants"] = variants
            session.payload_json = json.dumps(payload, ensure_ascii=False)
        replace_left = MAX_REPLACES - payload["replace_count"]
    return {"session_id": session_id, "status": session.status, "variants": variants,
            "replace_left": replace_left}


def _get_session(db: Session, session_id: str) -> Task:
    session = db.get(Task, session_id)
    if session is None or session.type != "review":
        raise not_found("复习会话", session_id)
    return session


# ---------- 提交与批改 ----------

def submit_answers(db: Session, session_id: str, answers: list[dict]) -> dict:
    session = _get_session(db, session_id)
    payload = json.loads(session.payload_json)
    variants = payload.get("variants", [])
    answer_map = {a["variant_id"]: a for a in answers}
    # 未作答按错误计（EX-08：确认交卷后未答题按错误处理）
    for variant in variants:
        if variant["variant_id"] not in answer_map:
            answer_map[variant["variant_id"]] = {"variant_id": variant["variant_id"],
                                                 "answer": "", "unsure": False}
    payload["answers"] = answer_map
    session.status = "submitting"
    session.payload_json = json.dumps(payload, ensure_ascii=False)
    db.flush()
    db.commit()
    threading.Thread(target=_grading_task, args=(session_id,), daemon=True).start()
    return {"session_id": session_id, "status": "grading"}


def _grading_task(session_id: str) -> None:
    with session_scope() as db:
        session = db.get(Task, session_id)
        if session is None:
            return
        payload = json.loads(session.payload_json)
        try:
            items = []
            for variant in payload.get("variants", []):
                answer = payload["answers"].get(variant["variant_id"], {})
                source = db.get(Mistake, variant["source_mistake_id"])
                graded = _grade_variant(source, variant, answer.get("answer", ""),
                                        bool(answer.get("unsure")))
                items.append(graded)
            report = _build_report(db, session, payload, items)
            payload["report"] = report
            session.payload_json = json.dumps(payload, ensure_ascii=False)
            session.status = "done"
        except ApiError as err:
            # EX-10：批改服务不可用，任务保留可重放
            session.status = "failed"
            session.error = err.message
            payload["pending_answers"] = payload.get("answers", {})
            session.payload_json = json.dumps(payload, ensure_ascii=False)


def _grade_variant(source: Mistake | None, variant: dict, student_answer: str, unsure: bool) -> dict:
    from app.core.config import get_settings
    settings = get_settings()
    correct_answer = variant.get("answer") or ""
    if not student_answer.strip():
        quality = 0
        is_correct = False
        analysis = "未作答。"
        error_type = "other"
    elif settings.ai_mock:
        norm_student = re.sub(r"\s+", "", student_answer).upper()
        norm_correct = re.sub(r"\s+", "", correct_answer).upper()
        is_correct = norm_student == norm_correct
        quality = 5 if (is_correct and not unsure) else (4 if is_correct else (2 if norm_student in norm_correct or norm_correct in norm_student else 1))
        analysis = "（演示模式批改）答案正确。" if is_correct else f"（演示模式批改）答案不正确，正确答案：{correct_answer}。"
        error_type = "none" if is_correct else "knowledge"
    else:
        gateway = get_gateway()
        raw = asyncio.run(gateway.complete_json([
            {"role": "system", "content": "只输出 JSON"},
            {"role": "user", "content": GRADING_PROMPT + json.dumps({
                "original": {"question_text": source.problem.question_text if source else "",
                             "answer": source.problem.answer_text if source else ""},
                "variant": variant,
                "student_answer": student_answer,
                "unsure": unsure,
            }, ensure_ascii=False)},
        ]))
        is_correct = bool(raw.get("is_correct"))
        quality = int(raw.get("quality", 0))
        analysis = raw.get("analysis") or ""
        error_type = raw.get("error_type") or "none"
    return {
        "variant_id": variant["variant_id"],
        "source_mistake_id": variant["source_mistake_id"],
        "is_correct": is_correct,
        "quality": quality,
        "my_answer": student_answer,
        "correct_answer": correct_answer,
        "analysis": analysis,
        "error_type": error_type,
        "knowledge_point": variant.get("knowledge_point") or "",
        "question_excerpt": (variant.get("question_text") or "")[:60],
    }


def _build_report(db: Session, session: Task, payload: dict, items: list[dict]) -> dict:
    correct = sum(1 for it in items if it["is_correct"])
    wrong = len(items) - correct
    score = round(100 * correct / len(items)) if items else 0
    started = datetime.fromisoformat(payload.get("started_at", datetime.now().isoformat()))
    duration_s = int((datetime.now() - started).total_seconds())
    weak_points: list[str] = []
    # 应用 SM-2 + 写复习记录
    for it in items:
        source = db.get(Mistake, it["source_mistake_id"])
        if source is None:
            continue
        if not it["is_correct"] and source.kp_id:
            kp = db.get(KnowledgePoint, source.kp_id)
            if kp:
                weak_points.append(kp.name)
        log = ReviewLog(mistake_id=source.id, session_id=session.id, variant_id=it["variant_id"],
                        answer=it["my_answer"], is_correct=it["is_correct"],
                        quality=it["quality"], score=score, duration_s=duration_s // max(len(items), 1),
                        reviewed_at=datetime.now())
        db.add(log)
        is_first_review = source.review_count == 0  # 自增前判定首次
        source.review_count += 1
        if it["is_correct"]:
            source.correct_count += 1
        else:
            source.wrong_count += 1
        source.last_reviewed_at = datetime.now()
        if source.correct_count + source.wrong_count > 0:
            source.mastery = source.correct_count / (source.correct_count + source.wrong_count)
        plan_service.apply_review_result(db, source, it["quality"], it["is_correct"],
                                         is_first=is_first_review)

    # 与上次对比
    last = db.query(ReviewLog).filter(ReviewLog.session_id != session.id) \
        .order_by(ReviewLog.reviewed_at.desc()).first()
    compared_last = None
    if last and last.score is not None:
        compared_last = {"score_delta": score - int(last.score)}
    return {
        "score": score,
        "correct": correct,
        "wrong": wrong,
        "duration_s": duration_s,
        "weak_points": list(dict.fromkeys(weak_points))[:3],
        "compared_last": compared_last,
        "items": items,
        "session_id": session.id,
    }


def get_result(db: Session, session_id: str) -> dict:
    session = _get_session(db, session_id)
    if session.status in ("failed",) and session.error:
        raise ApiError("AI_UNAVAILABLE", session.error, {})
    if session.status != "done":
        return {"session_id": session_id, "status": session.status, "report": None}
    payload = json.loads(session.payload_json)
    return {"session_id": session_id, "status": "done", "report": payload.get("report")}


def regrade_item(db: Session, session_id: str, variant_id: str) -> dict:
    """不认可重新批改（PRD 7.4-14：不重复计入复习统计）。"""
    session = _get_session(db, session_id)
    payload = json.loads(session.payload_json)
    report = payload.get("report")
    if not report:
        raise ApiError("CONFLICT", "批改尚未完成，无法重新批改", {})
    idx = next((i for i, it in enumerate(report["items"]) if it["variant_id"] == variant_id), None)
    if idx is None:
        raise not_found("批改条目", variant_id)
    item = report["items"][idx]
    variant = next(v for v in payload["variants"] if v["variant_id"] == variant_id)
    source = db.get(Mistake, item["source_mistake_id"])
    # 重新批改：翻转判定时修正统计与 SM-2（以重批结果覆盖原记录）
    flipped = False
    from app.core.config import get_settings
    if get_settings().ai_mock:
        # mock 重批：视为复核通过（认可当前结果）
        pass
    else:
        new_item = _grade_variant(source, variant, item["my_answer"], False)
        if new_item["is_correct"] != item["is_correct"]:
            flipped = True
            log = db.query(ReviewLog).filter(ReviewLog.session_id == session_id,
                                             ReviewLog.variant_id == variant_id).first()
            if log:
                log.is_correct = new_item["is_correct"]
                log.quality = new_item["quality"]
            if source:
                if new_item["is_correct"]:
                    source.wrong_count -= 1
                    source.correct_count += 1
                else:
                    source.correct_count -= 1
                    source.wrong_count += 1
                if source.correct_count + source.wrong_count > 0:
                    source.mastery = source.correct_count / (source.correct_count + source.wrong_count)
                plan_service.apply_review_result(db, source, new_item["quality"], new_item["is_correct"])
        item.update(new_item)
    report["items"][idx] = item
    payload["report"] = report
    session.payload_json = json.dumps(payload, ensure_ascii=False)
    return {"session_id": session_id, "report": report, "flipped": flipped}
