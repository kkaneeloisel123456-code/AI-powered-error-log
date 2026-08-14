"""学科与知识点管理。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, not_found
from app.db.models import KnowledgePoint, Mistake, Subject


def list_subjects(db: Session) -> list[dict]:
    counts = dict(
        db.execute(
            select(Mistake.subject_id, func.count(Mistake.id)).group_by(Mistake.subject_id)
        ).all()
    )
    return [
        {
            "id": s.id,
            "name": s.name,
            "sort_order": s.sort_order,
            "is_active": s.is_active,
            "mistake_count": counts.get(s.id, 0),
        }
        for s in db.query(Subject).order_by(Subject.sort_order, Subject.id).all()
    ]


def list_knowledge_points(db: Session, subject_id: int | None = None) -> list[dict]:
    stmt = select(KnowledgePoint).order_by(KnowledgePoint.level, KnowledgePoint.id)
    if subject_id:
        stmt = stmt.where(KnowledgePoint.subject_id == subject_id)
    return [
        {"id": kp.id, "subject_id": kp.subject_id, "parent_id": kp.parent_id,
         "name": kp.name, "level": kp.level, "path": kp.path}
        for kp in db.scalars(stmt).all()
    ]


def create_subject(db: Session, name: str) -> Subject:
    if db.scalar(select(Subject).where(Subject.name == name)):
        raise ApiError("CONFLICT", f"学科已存在：{name}", {"name": name})
    max_order = db.scalar(select(func.max(Subject.sort_order))) or 0
    subject = Subject(name=name, sort_order=max_order + 1)
    db.add(subject)
    db.flush()
    return subject


def update_subject(db: Session, subject_id: int, payload: dict) -> Subject:
    s = db.get(Subject, subject_id)
    if s is None:
        raise not_found("学科", str(subject_id))
    if payload.get("name") and payload["name"] != s.name:
        if db.scalar(select(Subject).where(Subject.name == payload["name"])):
            raise ApiError("CONFLICT", f"学科已存在：{payload['name']}", {"name": payload["name"]})
        s.name = payload["name"]
    if "sort_order" in payload and payload["sort_order"] is not None:
        s.sort_order = payload["sort_order"]
    if "is_active" in payload and payload["is_active"] is not None:
        s.is_active = payload["is_active"]
    return s


def delete_subject(db: Session, subject_id: int) -> None:
    s = db.get(Subject, subject_id)
    if s is None:
        raise not_found("学科", str(subject_id))
    count = db.scalar(select(func.count(Mistake.id)).where(Mistake.subject_id == subject_id)) or 0
    if count:
        raise ApiError("CONFLICT", f"该学科下还有 {count} 道错题，无法删除", {"count": count})
    db.query(KnowledgePoint).filter(KnowledgePoint.subject_id == subject_id).delete()
    db.delete(s)
