"""看板聚合（PRD 5.6）+ 聚合缓存（规划 5.3：预聚合/缓存，避免大表全扫）。"""
import time
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Mistake, ReviewLog, Subject

_CACHE: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 15.0


def invalidate_cache() -> None:
    _CACHE.clear()


def _cached(key: str, build):
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    value = build()
    _CACHE[key] = (now, value)
    return value


def summary(db: Session, range_days: int = 7) -> dict:
    return _cached(f"summary:{range_days}", lambda: _build_summary(db, range_days))


def _build_summary(db: Session, range_days: int) -> dict:
    today = date.today()
    start = today - timedelta(days=range_days - 1)

    # ---- 趋势：每日录入数 / 复习数 / 正确率 ----
    days = [start + timedelta(days=i) for i in range(range_days)]
    created_rows = db.execute(
        select(func.date(Mistake.created_at), func.count(Mistake.id))
        .where(Mistake.created_at >= datetime.combine(start, datetime.min.time()))
        .group_by(func.date(Mistake.created_at))
    ).all()
    created_map = {str(d): c for d, c in created_rows}
    review_rows = db.execute(
        select(func.date(ReviewLog.reviewed_at), func.count(ReviewLog.id),
               func.sum(func.cast(ReviewLog.is_correct, __import__("sqlalchemy").Integer)))
        .where(ReviewLog.reviewed_at >= datetime.combine(start, datetime.min.time()))
        .group_by(func.date(ReviewLog.reviewed_at))
    ).all()
    review_map = {str(d): (c, int(r or 0)) for d, c, r in review_rows}
    trend = []
    for d in days:
        key = d.isoformat()
        total_reviews, correct_reviews = review_map.get(key, (0, 0))
        trend.append({
            "date": key,
            "created": created_map.get(key, 0),
            "reviewed": total_reviews,
            "accuracy": round(correct_reviews / total_reviews * 100) if total_reviews else 0,
        })

    # ---- 学科分布 ----
    subject_rows = db.execute(
        select(Mistake.subject_id, func.count(Mistake.id)).group_by(Mistake.subject_id)
    ).all()
    subject_names = {s.id: s.name for s in db.query(Subject).all()}
    subjects = [{"name": subject_names.get(sid, "未知"), "value": count}
                for sid, count in subject_rows]

    # ---- 错因分布（Top 5）----
    error_rows = db.execute(
        select(Mistake.error_type, func.count(Mistake.id)).group_by(Mistake.error_type)
    ).all()
    errors = [{"type": et, "value": count} for et, count in
              sorted(error_rows, key=lambda x: x[1], reverse=True)[:5]]

    # ---- 掌握状态分布 ----
    status_rows = db.execute(
        select(Mistake.status, func.count(Mistake.id)).group_by(Mistake.status)
    ).all()
    statuses = [{"status": st, "value": count} for st, count in status_rows]

    # ---- 薄弱点排行：错题数 × 近 30 天复错率加权 ----
    kp_mistakes = db.execute(
        select(Mistake.kp_id, func.count(Mistake.id))
        .where(Mistake.kp_id.isnot(None))
        .group_by(Mistake.kp_id)
    ).all()
    recent_wrong = db.execute(
        select(ReviewLog.mistake_id)
        .where(ReviewLog.is_correct.is_(False),
               ReviewLog.reviewed_at >= datetime.now() - timedelta(days=30))
    ).all()
    recent_wrong_ids = {row[0] for row in recent_wrong}
    weak_rows = []
    from app.db.models import KnowledgePoint
    for kp_id, count in kp_mistakes:
        wrong_count = db.scalar(
            select(func.count(Mistake.id)).where(Mistake.kp_id == kp_id,
                                                 Mistake.id.in_(recent_wrong_ids or [""]))
        ) or 0
        kp = db.get(KnowledgePoint, kp_id)
        if kp is None:
            continue
        score = round(count + wrong_count * 3, 2)
        weak_rows.append({
            "kp_id": kp_id,
            "name": kp.name,
            "subject_name": subject_names.get(kp.subject_id, ""),
            "mistake_count": count,
            "recent_wrong": wrong_count,
            "score": score,
        })
    weak_rows.sort(key=lambda x: x["score"], reverse=True)
    return {
        "range_days": range_days,
        "totals": {
            "mistakes": db.scalar(select(func.count(Mistake.id))) or 0,
            "reviews": db.scalar(select(func.count(ReviewLog.id))) or 0,
        },
        "trend": trend,
        "subjects": subjects,
        "errors": errors,
        "statuses": statuses,
        "weak_points": weak_rows[:10],
    }


def knowledge_graph(db: Session, subject_id: int | None = None) -> dict:
    return _cached(f"graph:{subject_id}", lambda: _build_graph(db, subject_id))


def _build_graph(db: Session, subject_id: int | None) -> dict:
    """知识图谱（PRD 8.9）：节点=知识点（大小=错题数，颜色=掌握度），边=父子关系。

    节点包含：有错题的知识点 + 其祖先链（value=0，保证层级边连通）；
    共现边依赖多知识点题目，MVP 单知识点模型下暂无（M4 文档记录）。
    """
    from app.db.models import KnowledgePoint
    stmt = select(KnowledgePoint)
    if subject_id:
        stmt = stmt.where(KnowledgePoint.subject_id == subject_id)
    kps = list(db.scalars(stmt).all())
    kp_map = {kp.id: kp for kp in kps}

    nodes = []
    for kp in kps:
        mistakes = db.execute(
            select(Mistake.status, func.count(Mistake.id))
            .where(Mistake.kp_id == kp.id)
            .group_by(Mistake.status)
        ).all()
        counts = dict(mistakes)
        total = sum(counts.values())
        if total == 0:
            continue
        avg_mastery = db.scalar(select(func.avg(Mistake.mastery)).where(Mistake.kp_id == kp.id)) or 0
        nodes.append({
            "id": kp.id,
            "name": kp.name,
            "level": kp.level,
            "subject_id": kp.subject_id,
            "value": total,                       # 节点大小映射错题数
            "mastery": round(float(avg_mastery), 2),  # 颜色映射掌握度
            "status_counts": counts,
        })
    ids = {n["id"] for n in nodes}
    # 祖先链补全（value=0）：保证父子边连通
    for kp in list(nodes):
        parent_id = kp_map[kp["id"]].parent_id
        while parent_id and parent_id not in ids:
            ancestor = kp_map.get(parent_id)
            if ancestor is None:
                break
            nodes.append({
                "id": ancestor.id, "name": ancestor.name, "level": ancestor.level,
                "subject_id": ancestor.subject_id, "value": 0, "mastery": 0.0,
                "status_counts": {},
            })
            ids.add(ancestor.id)
            parent_id = ancestor.parent_id
    edges = []
    for node in nodes:
        parent_id = kp_map[node["id"]].parent_id
        if parent_id and parent_id in ids:
            edges.append({"source": parent_id, "target": node["id"], "type": "hierarchy"})
    return {"subject_id": subject_id, "nodes": nodes, "edges": edges}
