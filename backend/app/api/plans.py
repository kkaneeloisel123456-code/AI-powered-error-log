"""复习计划路由（SM-2 每日/周度/考前）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_auth
from app.db.session import get_db
from app.schemas.reviews import ExamPlanOut, ExamPlanRequest, PlanItemAction, TodayPlanOut, WeekPlanOut
from app.services import plan_service

router = APIRouter(prefix="/api/v1/plans", tags=["plans"], dependencies=[Depends(require_auth)])


@router.get("/today", response_model=TodayPlanOut)
def today_plan(db: Session = Depends(get_db)):
    return plan_service.today_plan(db)


@router.get("/week", response_model=WeekPlanOut)
def week_plan(db: Session = Depends(get_db)):
    return plan_service.week_plan(db)


@router.post("/exam", response_model=ExamPlanOut)
def exam_plan(payload: ExamPlanRequest, db: Session = Depends(get_db)):
    return plan_service.exam_plan(db, payload.exam_date, payload.daily_target)


@router.patch("/items/{item_id}")
def update_plan_item(item_id: str, payload: PlanItemAction, db: Session = Depends(get_db)):
    return plan_service.update_plan_item(db, item_id, payload.action)
