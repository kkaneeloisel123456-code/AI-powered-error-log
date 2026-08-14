"""错题业务逻辑（列表检索、CRUD、批量、审计）。SQL 统一收敛在 service。"""
import json
from datetime import datetime

from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import ApiError, not_found
from app.db.base import gen_id
from app.db.models import (
    MISTAKE_STATUSES,
    STATUS_COLORS,
    AuditLog,
    KnowledgePoint,
    Mistake,
    PlanItem,
    Problem,
    Subject,
)

SORT_FIELDS = {"created_at", "last_reviewed_at", "mastery", "review_count", "due_date"}


def _tags(obj: Mistake) -> list[str]:
    try:
        return json.loads(obj.tags_json) if obj.tags_json else []
    except json.JSONDecodeError:
        return []


def _due_date(db: Session, mistake_id: str) -> str | None:
    """最近一条待复习计划项的到期日（ISO 日期）。"""
    row = db.scalar(
        select(PlanItem.due_date)
        .where(PlanItem.mistake_id == mistake_id, PlanItem.status == "pending")
        .order_by(PlanItem.due_date)
        .limit(1)
    )
    return row.isoformat() if row else None


def serialize_list_item(m: Mistake) -> dict:
    return {
        "id": m.id,
        "subject_id": m.subject_id,
        "subject_name": m.subject.name if m.subject else "",
        "kp_id": m.kp_id,
        "knowledge_point": "",
        "question_excerpt": (m.problem.question_text or "")[:80],
        "status": m.status,
        "color": m.color,
        "tags": _tags(m),
        "error_type": m.error_type,
        "source": m.source,
        "last_reviewed_at": m.last_reviewed_at,
        "review_count": m.review_count,
        "correct_count": m.correct_count,
        "wrong_count": m.wrong_count,
        "mastery": m.mastery,
        "created_at": m.created_at,
    }


def serialize_detail(db: Session, m: Mistake) -> dict:
    data = serialize_list_item(m)
    kp = db.get(KnowledgePoint, m.kp_id) if m.kp_id else None
    data["knowledge_point"] = kp.name if kp else ""
    problem = m.problem
    options = []
    try:
        options = json.loads(problem.options_json) if problem.options_json else []
    except json.JSONDecodeError:
        pass
    data.update({
        "question_text": problem.question_text,
        "options": options,
        "answer_text": problem.answer_text,
        "analysis": problem.analysis,
        "difficulty": problem.difficulty,
        "source_image_url": None,
        "note": m.note,
        "first_seen_at": m.first_seen_at,
        "due_date": _due_date(db, m.id),
    })
    from app.core.config import get_settings
    if problem.source_image_path:
        rel = problem.source_image_path.replace("\\", "/")
        data["source_image_url"] = f"/api/v1/files/{rel}"
    return data


def list_mistakes(db: Session, *, q: str | None = None, subject_id: int | None = None,
                  status: str | None = None, color: str | None = None, error_type: str | None = None,
                  tags: str | None = None, source: str | None = None,
                  date_from: str | None = None, date_to: str | None = None,
                  kp_id: int | None = None,
                  sort: str = "created_at", order: str = "desc",
                  page: int = 1, page_size: int = 20) -> dict:
    """列表：多条件组合检索 + 排序 + 分页（复合索引，万级 < 500ms）。"""
    if sort not in SORT_FIELDS:
        raise ApiError("VALIDATION_ERROR", f"不支持的排序字段：{sort}", {"field": "sort"})
    if order not in ("asc", "desc"):
        raise ApiError("VALIDATION_ERROR", "order 仅支持 asc / desc", {"field": "order"})
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    kp_alias = aliased(KnowledgePoint)
    stmt = select(Mistake)
    if q:
        like = f"%{q}%"
        stmt = stmt.join(Problem, Mistake.problem_id == Problem.id).join(
            kp_alias, Mistake.kp_id == kp_alias.id, isouter=True
        )
        stmt = stmt.where(or_(
            Problem.question_text.like(like),
            kp_alias.name.like(like),
            Mistake.tags_json.like(like),
            Mistake.source.like(like),
            Mistake.error_type.like(like),
        ))
    if subject_id:
        stmt = stmt.where(Mistake.subject_id == subject_id)
    if status:
        stmt = stmt.where(Mistake.status == status)
    if color:
        stmt = stmt.where(Mistake.color == color)
    if error_type:
        stmt = stmt.where(Mistake.error_type == error_type)
    if tags:
        for tag in tags.split(","):
            stmt = stmt.where(Mistake.tags_json.like(f'%"{tag.strip()}"%'))
    if source:
        stmt = stmt.where(Mistake.source == source)
    if kp_id:
        stmt = stmt.where(Mistake.kp_id == kp_id)
    if date_from:
        stmt = stmt.where(Mistake.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(Mistake.created_at <= datetime.fromisoformat(date_to))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    sort_col = {
        "created_at": Mistake.created_at,
        "last_reviewed_at": Mistake.last_reviewed_at,
        "mastery": Mistake.mastery,
        "review_count": Mistake.review_count,
        "due_date": None,
    }[sort]
    if sort == "due_date":
        due_sub = (
            select(PlanItem.mistake_id, func.min(PlanItem.due_date).label("due"))
            .where(PlanItem.status == "pending")
            .group_by(PlanItem.mistake_id)
            .subquery()
        )
        stmt = stmt.join(due_sub, due_sub.c.mistake_id == Mistake.id, isouter=True)
        sort_col = due_sub.c.due
    stmt = stmt.order_by(sort_col.desc() if order == "desc" else sort_col.asc()) \
        .offset((page - 1) * page_size).limit(page_size)

    items = [serialize_list_item(m) for m in db.scalars(stmt).all()]
    # 知识点名称批量填充（避免 N+1）
    kp_ids = {it["kp_id"] for it in items if it["kp_id"]}
    kp_names = {
        kp.id: kp.name
        for kp in db.query(KnowledgePoint).filter(KnowledgePoint.id.in_(kp_ids)).all()
    } if kp_ids else {}
    for it in items:
        it["knowledge_point"] = kp_names.get(it["kp_id"], "")
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_mistake(db: Session, mistake_id: str) -> Mistake:
    m = db.get(Mistake, mistake_id)
    if m is None:
        raise not_found("错题", mistake_id)
    return m


def create_mistake(db: Session, payload: dict, *, source: str = "text", idempotency_key: str | None = None) -> Mistake:
    if payload["subject_id"] and db.get(Subject, payload["subject_id"]) is None:
        raise ApiError("VALIDATION_ERROR", "学科不存在", {"field": "subject_id"})
    status = payload.get("status") or "pending"
    if status not in MISTAKE_STATUSES:
        raise ApiError("VALIDATION_ERROR", f"非法状态：{status}", {"field": "status"})
    source = payload.get("source") or source  # 对话/识图/文本入口均记录真实来源
    problem = Problem(
        id=gen_id("p"),
        source_type="text" if source in ("text", "chat") else source,
        question_text=payload["question_text"],
        options_json=json.dumps(payload.get("options") or [], ensure_ascii=False),
        answer_text=payload.get("answer_text") or "",
        analysis=payload.get("analysis") or "",
        difficulty=payload.get("difficulty") or "medium",
    )
    db.add(problem)
    db.flush()
    mistake = Mistake(
        id=gen_id("m"),
        problem_id=problem.id,
        subject_id=payload["subject_id"],
        kp_id=payload.get("kp_id"),
        error_type=payload.get("error_type") or "other",
        status=status,
        color=payload.get("color") or STATUS_COLORS[status],
        tags_json=json.dumps(payload.get("tags") or [], ensure_ascii=False),
        source=source,
        note=payload.get("note") or "",
        first_seen_at=datetime.now(),
        mastery=1.0 if status == "mastered" else 0.0,
    )
    db.add(mistake)
    db.flush()
    # 新错题默认次日进入复习计划（PRD 5.5）
    from app.services.plan_service import ensure_plan_item
    from datetime import date, timedelta
    ensure_plan_item(db, mistake, due=date.today() + timedelta(days=1))
    return mistake


def update_mistake(db: Session, mistake_id: str, payload: dict) -> dict:
    """编辑错题；状态/颜色手动调整写入审计（PRD 5.2）。"""
    m = get_mistake(db, mistake_id)
    changed = {}
    for field in ("question_text", "options", "answer_text", "analysis", "difficulty",
                  "subject_id", "kp_id", "error_type", "tags", "note"):
        if field in payload and payload[field] is not None:
            changed[field] = payload[field]

    # 状态与颜色联动：改状态 -> 颜色跟随（除非用户同时指定颜色）；改颜色 -> 仅视觉
    status_changed = color_changed = False
    if payload.get("status") and payload["status"] != m.status:
        if payload["status"] not in MISTAKE_STATUSES:
            raise ApiError("VALIDATION_ERROR", f"非法状态：{payload['status']}", {"field": "status"})
        db.add(AuditLog(entity_type="mistake", entity_id=m.id, action="status_change",
                        before_json=json.dumps({"status": m.status, "color": m.color}),
                        after_json=json.dumps({"status": payload["status"],
                                               "color": payload.get("color") or STATUS_COLORS[payload["status"]]})))
        m.status = payload["status"]
        m.color = payload.get("color") or STATUS_COLORS[payload["status"]]
        if payload["status"] == "mastered":
            m.mastery = 1.0  # 手动标记已掌握：掌握度同步（PRD 7.3-8 看板立即更新）
        status_changed = True
    if payload.get("color") and payload["color"] != m.color:
        db.add(AuditLog(entity_type="mistake", entity_id=m.id, action="color_change",
                        before_json=json.dumps({"color": m.color}),
                        after_json=json.dumps({"color": payload["color"]})))
        m.color = payload["color"]
        color_changed = True

    if changed:
        if "options" in changed:
            m.problem.options_json = json.dumps(changed["options"], ensure_ascii=False)
            changed.pop("options")
        for k, v in changed.items():
            if k in ("question_text", "answer_text", "analysis", "difficulty"):
                setattr(m.problem, k, v)
            elif k == "tags":
                m.tags_json = json.dumps(v, ensure_ascii=False)
            else:
                setattr(m, k, v)
        db.add(AuditLog(entity_type="mistake", entity_id=m.id, action="edit",
                        before_json="{}", after_json=json.dumps({k: str(v)[:200] for k, v in changed.items()})))
    return serialize_detail(db, m)


def delete_mistake(db: Session, mistake_id: str) -> None:
    """删除：错题 + 关联计划项移除；复习记录保留（PRD 5.2）。"""
    m = get_mistake(db, mistake_id)
    db.query(PlanItem).filter(PlanItem.mistake_id == mistake_id).delete()
    db.delete(m)


def batch_operate(db: Session, action: str, ids: list[str], value: str | None = None) -> dict:
    """批量：删除/改状态/改颜色/打标签（幂等：只影响存在的行）。"""
    result = {"updated": 0, "deleted": 0}
    for mid in ids:
        m = db.get(Mistake, mid)
        if m is None:
            continue
        if action == "delete":
            db.query(PlanItem).filter(PlanItem.mistake_id == mid).delete()
            db.delete(m)
            result["deleted"] += 1
            continue
        if action == "set_status":
            if not value or value not in MISTAKE_STATUSES:
                raise ApiError("VALIDATION_ERROR", f"非法状态：{value}", {"field": "value"})
            db.add(AuditLog(entity_type="mistake", entity_id=mid, action="batch_status",
                            before_json=json.dumps({"status": m.status}),
                            after_json=json.dumps({"status": value})))
            m.status = value
            m.color = STATUS_COLORS[value]
        elif action == "set_color":
            if not value:
                raise ApiError("VALIDATION_ERROR", "缺少颜色值", {"field": "value"})
            m.color = value
        elif action in ("add_tags", "remove_tags"):
            if not value:
                raise ApiError("VALIDATION_ERROR", "缺少标签值", {"field": "value"})
            tags = _tags(m)
            for tag in [t.strip() for t in value.split(",") if t.strip()]:
                if action == "add_tags" and tag not in tags:
                    tags.append(tag)
                if action == "remove_tags" and tag in tags:
                    tags.remove(tag)
            m.tags_json = json.dumps(tags, ensure_ascii=False)
        result["updated"] += 1
    return result
