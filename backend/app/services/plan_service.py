"""SM-2 复习计划（PRD 8.7 算法规格 + 5.5 业务规则）。

质量分 q：5 完全正确且有把握 / 4 正确但不确定 / 3 答案对步骤有误 / 2 部分对 / 1 完全错 / 0 未作答
通过 q>=3：首次间隔 1 天；后续 = round(上次间隔 × EF)
失败 q<3：间隔重置 1 天，状态回到「未掌握」
EF' = EF + (0.1 - (5-q)(0.08 + (5-q)0.02))，下限 1.3
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgePoint, Mistake, PlanItem, ReviewLog, STATUS_COLORS

EF_MIN = 1.3
MINUTES_PER_QUESTION = 2


def today() -> date:
    return date.today()


def update_ease_factor(ef: float, q: int) -> float:
    return max(EF_MIN, ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))


def next_interval(current_interval: int | None, ef: float, is_first: bool, q: int) -> int:
    if q < 3:
        return 1
    if is_first or not current_interval:
        return 1
    return max(1, round(current_interval * ef))


def ensure_plan_item(db: Session, mistake: Mistake, due: date, interval_days: int = 1,
                     ease_factor: float = 2.5) -> PlanItem:
    """新错题默认次日进入计划（PRD 5.5）。已有待复习项时不重复创建。"""
    existing = db.scalar(select(PlanItem).where(PlanItem.mistake_id == mistake.id,
                                                PlanItem.status == "pending").limit(1))
    if existing:
        return existing
    item = PlanItem(mistake_id=mistake.id, due_date=due, interval_days=interval_days,
                    ease_factor=ease_factor, status="pending")
    db.add(item)
    return item


def apply_review_result(db: Session, mistake: Mistake, q: int, is_correct: bool,
                        is_first: bool | None = None) -> PlanItem:
    """批改结果 -> SM-2 计划更新（PRD 8.7 / 7.5-16/17）。

    is_first：是否首次复习。调用方需在自增 review_count 之前传入；
    缺省时按 review_count==0 推断（兼容手动/跳过路径）。
    """
    active = db.scalar(select(PlanItem).where(PlanItem.mistake_id == mistake.id,
                                              PlanItem.status == "pending").limit(1))
    old_interval = active.interval_days if active else None
    old_ef = active.ease_factor if active else 2.5
    if is_first is None:
        is_first = (mistake.review_count == 0) or active is None or old_interval is None

    # 状态流转（PRD 3.3）
    if q >= 3:
        ef = update_ease_factor(old_ef, q)
        interval = next_interval(old_interval, ef, is_first, q)
        due = today() + timedelta(days=interval)
        # 已掌握：连续 2 次 q>=4 且间隔 >= 30 天
        consecutive = _consecutive_good(db, mistake.id, q)
        if consecutive >= 2 and interval >= 30:
            _set_status(db, mistake, "mastered")
        else:
            _set_status(db, mistake, "fixing")  # 待巩固（首次通过仍需周期复习）
    else:
        ef = old_ef
        interval = 1
        due = today() + timedelta(days=1)
        _set_status(db, mistake, "wrong")  # 答错间隔重置 1 天，状态回未掌握

    if active:
        active.status = "completed"
        active.reviewed_at = datetime.now()
        active.last_quality = q
    new_item = PlanItem(mistake_id=mistake.id, due_date=due, interval_days=interval,
                        ease_factor=ef, status="pending", last_quality=q)
    db.add(new_item)
    return new_item


def _set_status(db: Session, mistake: Mistake, status: str) -> None:
    mistake.status = status
    mistake.color = STATUS_COLORS[status]


def _consecutive_good(db: Session, mistake_id: str, current_q: int) -> int:
    """连续 q>=4 次数（含本次）。"""
    if current_q < 4:
        return 0
    logs = db.query(ReviewLog).filter(ReviewLog.mistake_id == mistake_id) \
        .order_by(ReviewLog.reviewed_at.desc()).limit(5).all()
    count = 1
    for log in logs:
        if log.quality is not None and log.quality >= 4:
            count += 1
        else:
            break
    return count


# ---------- 计划查询 ----------

def _due_count(db: Session, d: date) -> int:
    return db.scalar(select(func.count(PlanItem.id)).where(
        PlanItem.due_date <= d, PlanItem.status == "pending")) or 0


def today_plan(db: Session) -> dict:
    rows = db.execute(
        select(PlanItem, Mistake, KnowledgePoint)
        .join(Mistake, PlanItem.mistake_id == Mistake.id)
        .join(KnowledgePoint, Mistake.kp_id == KnowledgePoint.id, isouter=True)
        .where(PlanItem.due_date <= today(), PlanItem.status == "pending")
        .order_by(PlanItem.due_date, Mistake.wrong_count.desc())
        .limit(100)
    ).all()
    items = [_serialize_item(db, item, mistake, kp) for item, mistake, kp in rows]
    return {
        "date": today().isoformat(),
        "due_count": len(items),
        "estimated_minutes": len(items) * MINUTES_PER_QUESTION,
        "items": items,
    }


def week_plan(db: Session) -> dict:
    days = []
    for offset in range(7):
        d = today() + timedelta(days=offset)
        days.append({
            "date": d.isoformat(),
            "count": _due_count(db, d),
            "suggested": min(_due_count(db, d), 10),
        })
    return {"start": today().isoformat(), "days": days}


def exam_plan(db: Session, exam_date: date, daily_target: int) -> dict:
    """考前计划：按 (薄弱度权重 0.6 + 到期紧急度 0.4) 排序填充每日目标题量。"""
    rows = db.execute(
        select(PlanItem, Mistake)
        .join(Mistake, PlanItem.mistake_id == Mistake.id)
        .where(PlanItem.status == "pending")
    ).all()
    days_until = max((exam_date - today()).days, 0)
    scored = []
    for item, mistake in rows:
        weakness = mistake.wrong_count * 2 + (1 - mistake.mastery) * 10
        urgency = max(days_until - (item.due_date - today()).days, 0)
        scored.append((weakness * 0.6 + urgency * 0.4, item, mistake))
    scored.sort(key=lambda x: x[0], reverse=True)
    daily_target = max(daily_target, 1)
    # 按每日目标题量分桶
    result_items = []
    for i, (score, item, mistake) in enumerate(scored):
        day = i // daily_target + 1
        if day > days_until:
            day = days_until
        result_items.append({
            "plan_item_id": item.id,
            "mistake_id": mistake.id,
            "day_offset": day,
            "due_date": item.due_date.isoformat(),
            "question_excerpt": (mistake.problem.question_text or "")[:60],
            "score": round(score, 2),
        })
    return {"exam_date": exam_date.isoformat(), "daily_target": daily_target,
            "total": len(result_items), "items": result_items}


def _serialize_item(db: Session, item: PlanItem, mistake: Mistake, kp) -> dict:
    kp_name = kp.name if kp else ""
    return {
        "id": item.id,
        "mistake_id": mistake.id,
        "due_date": item.due_date.isoformat(),
        "interval_days": item.interval_days,
        "ease_factor": item.ease_factor,
        "status": item.status,
        "last_quality": item.last_quality,
        "question_excerpt": (mistake.problem.question_text or "")[:60],
        "subject_name": mistake.subject.name if mistake.subject else "",
        "knowledge_point": kp_name,
        "mistake_status": mistake.status,
    }


def update_plan_item(db: Session, item_id: str, action: str) -> dict:
    """完成/跳过/恢复（PRD 5.5：跳过计入统计并可恢复）。"""
    item = db.get(PlanItem, item_id)
    if item is None:
        from app.core.errors import not_found
        raise not_found("计划项", item_id)
    mistake = db.get(Mistake, item.mistake_id)
    if action == "complete":
        item.status = "completed"
        item.reviewed_at = datetime.now()
        next_item = PlanItem(mistake_id=item.mistake_id,
                             due_date=today() + timedelta(days=max(item.interval_days, 1)),
                             interval_days=max(item.interval_days, 1),
                             ease_factor=item.ease_factor, status="pending")
        db.add(next_item)
    elif action == "skip":
        item.status = "skipped"
        item.reviewed_at = datetime.now()
        next_item = PlanItem(mistake_id=item.mistake_id,
                             due_date=today() + timedelta(days=1),
                             interval_days=1, ease_factor=item.ease_factor, status="pending")
        db.add(next_item)
    elif action == "reset":
        item.status = "pending"
    else:
        from app.core.errors import ApiError
        raise ApiError("VALIDATION_ERROR", f"不支持的操作：{action}", {"field": "action"})
    return {"id": item.id, "status": item.status}
