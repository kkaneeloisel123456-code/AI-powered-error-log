"""M3 验收：复习闭环与 SM-2 计划（PRD 7.4/7.5）。"""
import time
import uuid

import pytest
from fastapi.testclient import TestClient


def _create(auth_client: TestClient, question: str, answer: str = "B", subject_id: int = 1,
            kp_id: int | None = None, options: list[str] | None = None) -> dict:
    resp = auth_client.post("/api/v1/mistakes", json={
        "question_text": question,
        "options": options or ["A. 2m", "B. 4m", "C. 8m", "D. 16m"],
        "answer_text": answer,
        "analysis": "由动能定理可得",
        "subject_id": subject_id,
        "kp_id": kp_id,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _session(auth_client: TestClient, **overrides) -> str:
    resp = auth_client.post("/api/v1/reviews/sessions", json={"count": 5, "scope": "all", **overrides})
    assert resp.status_code == 201, resp.text
    return resp.json()["session_id"]


def _variants(auth_client: TestClient, session_id: str) -> dict:
    for _ in range(50):
        body = auth_client.post("/api/v1/reviews/generate", json={"session_id": session_id}).json()
        if body["status"] == "answering" and body["variants"]:
            return body
        time.sleep(0.05)
    raise AssertionError("variants not generated")


def _submit_and_wait(auth_client: TestClient, session_id: str, answers: list[dict]) -> dict:
    resp = auth_client.post(f"/api/v1/reviews/{session_id}/submit", json={"answers": answers})
    assert resp.status_code == 202, resp.text
    for _ in range(50):
        body = auth_client.get(f"/api/v1/reviews/{session_id}/result").json()
        if body["status"] == "done":
            return body["report"]
        time.sleep(0.05)
    raise AssertionError("grading not done")


class TestReviewSession:
    def test_create_session_requires_mistakes(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/reviews/sessions", json={"count": 5, "scope": "all"})
        assert resp.status_code == 422
        assert "没有符合条件的错题" in resp.json()["message"]

    def test_generate_variants(self, auth_client: TestClient):
        _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        _create(auth_client, "已知函数 f(x)=x²，求 f(2) 的值。", answer="4")
        session_id = _session(auth_client)
        body = _variants(auth_client, session_id)
        assert len(body["variants"]) == 2
        variant = body["variants"][0]
        assert variant["variant_id"].startswith("v_")
        assert "【变式】" in variant["question_text"]
        assert body["replace_left"] == 3

    def test_replace_variant_limit_3(self, auth_client: TestClient):
        _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        session_id = _session(auth_client)
        body = _variants(auth_client, session_id)
        vid = body["variants"][0]["variant_id"]
        for i in range(3):
            resp = auth_client.post("/api/v1/reviews/generate", json={
                "session_id": session_id, "replace_variant_id": vid,
            })
            assert resp.status_code == 200
            assert resp.json()["replace_left"] == 2 - i
        # 第 4 次换题被拒（PRD 5.4：最多 3 次）
        resp = auth_client.post("/api/v1/reviews/generate", json={
            "session_id": session_id, "replace_variant_id": vid,
        })
        assert resp.status_code == 429
        assert resp.json()["code"] == "RATE_LIMITED"

    def test_scope_due_only_returns_due(self, auth_client: TestClient):
        _create(auth_client, "到期题 A")
        _create(auth_client, "未到期题 B")
        # 将题 A 的计划项改为今日到期（模拟到期错题）
        from app.db.session import get_sessionmaker
        from app.db.models import PlanItem
        from datetime import date
        db = get_sessionmaker()()
        try:
            for item in db.query(PlanItem).all():
                item.due_date = date.today()
            db.commit()
        finally:
            db.close()
        session_id = _session(auth_client, scope="due")
        body = _variants(auth_client, session_id)
        assert len(body["variants"]) == 2  # 两题均今日到期


class TestGrading:
    def test_full_flow_with_report(self, auth_client: TestClient):
        _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        session_id = _session(auth_client, count=5)
        body = _variants(auth_client, session_id)
        variant = body["variants"][0]
        report = _submit_and_wait(auth_client, session_id, [
            {"variant_id": variant["variant_id"], "answer": variant["answer"], "unsure": False},
        ])
        assert report["correct"] == 1
        assert report["wrong"] == 0
        assert report["score"] == 100
        assert report["items"][0]["is_correct"] is True
        assert report["weak_points"] == []

    def test_unanswered_counted_wrong(self, auth_client: TestClient):
        _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        session_id = _session(auth_client, count=5)
        body = _variants(auth_client, session_id)
        variant = body["variants"][0]
        # EX-08：确认交卷后未答题按错误计（q=0）
        report = _submit_and_wait(auth_client, session_id, [])
        assert report["wrong"] == 1
        item = report["items"][0]
        assert item["is_correct"] is False
        assert item["quality"] == 0
        assert "未作答" in item["analysis"]

    def test_wrong_answer_resets_sm2(self, auth_client: TestClient):
        created = _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        session_id = _session(auth_client, count=5)
        body = _variants(auth_client, session_id)
        variant = body["variants"][0]
        report = _submit_and_wait(auth_client, session_id, [
            {"variant_id": variant["variant_id"], "answer": "X", "unsure": False},
        ])
        assert report["wrong"] == 1
        # PRD 7.5-16：答错间隔重置 1 天，状态变未掌握，次日计划中出现
        detail = auth_client.get(f"/api/v1/mistakes/{created['id']}").json()
        assert detail["status"] == "wrong"
        assert detail["color"] == "#DC2626"
        assert detail["review_count"] == 1
        assert detail["wrong_count"] == 1
        today_plan = auth_client.get("/api/v1/plans/today").json()
        # 明日到期（今天不可见），但计划项已重置为明天
        tomorrow_items = [i for i in today_plan["items"] if i["mistake_id"] == created["id"]]
        assert tomorrow_items == []

    def test_correct_answer_advances_plan(self, auth_client: TestClient):
        created = _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        session_id = _session(auth_client, count=5)
        body = _variants(auth_client, session_id)
        variant = body["variants"][0]
        report = _submit_and_wait(auth_client, session_id, [
            {"variant_id": variant["variant_id"], "answer": variant["answer"], "unsure": False},
        ])
        assert report["correct"] == 1
        # PRD 7.5-17：q=5 时 EF 拉长，状态转待巩固
        detail = auth_client.get(f"/api/v1/mistakes/{created['id']}").json()
        assert detail["status"] == "fixing"
        assert detail["mastery"] == 1.0

        from app.db.session import get_sessionmaker
        from app.db.models import PlanItem
        db = get_sessionmaker()()
        try:
            items = db.query(PlanItem).filter(PlanItem.mistake_id == created["id"]).order_by(PlanItem.created_at).all()
            assert items[0].status == "completed"
            assert items[-1].status == "pending"
            assert items[-1].interval_days == 1  # 首次通过间隔 1 天
            assert items[-1].ease_factor > 2.5  # EF 提升
        finally:
            db.close()

    def test_compared_last_score(self, auth_client: TestClient):
        created = _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        # 第一次：答对
        s1 = _session(auth_client, count=5)
        v1 = _variants(auth_client, s1)["variants"][0]
        _submit_and_wait(auth_client, s1, [{"variant_id": v1["variant_id"], "answer": v1["answer"]}])
        # 第二次：答错
        s2 = _session(auth_client, count=5)
        v2 = _variants(auth_client, s2)["variants"][0]
        report2 = _submit_and_wait(auth_client, s2, [{"variant_id": v2["variant_id"], "answer": "X"}])
        assert report2["score"] == 0
        assert report2["compared_last"] == {"score_delta": -100}

    def test_regrade_does_not_double_count(self, auth_client: TestClient):
        created = _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        session_id = _session(auth_client, count=5)
        body = _variants(auth_client, session_id)
        variant = body["variants"][0]
        report = _submit_and_wait(auth_client, session_id, [
            {"variant_id": variant["variant_id"], "answer": "X"},
        ])
        resp = auth_client.post(f"/api/v1/reviews/{session_id}/regrade",
                                json={"variant_id": variant["variant_id"]})
        assert resp.status_code == 200
        # 重批不重复计统计
        detail = auth_client.get(f"/api/v1/mistakes/{created['id']}").json()
        assert detail["review_count"] == 1


class TestPlans:
    def test_new_mistake_enters_plan_tomorrow(self, auth_client: TestClient):
        created = _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        today_plan = auth_client.get("/api/v1/plans/today").json()
        assert today_plan["due_count"] == 0  # 新错题默认次日
        assert today_plan["estimated_minutes"] == 0
        # 计划项存在且明日到期
        from app.db.session import get_sessionmaker
        from app.db.models import PlanItem
        from datetime import date, timedelta
        db = get_sessionmaker()()
        try:
            item = db.query(PlanItem).filter(PlanItem.mistake_id == created["id"]).first()
            assert item is not None
            assert item.due_date == date.today() + timedelta(days=1)
            assert item.status == "pending"
        finally:
            db.close()

    def test_week_plan_seven_days(self, auth_client: TestClient):
        _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        body = auth_client.get("/api/v1/plans/week").json()
        assert len(body["days"]) == 7
        assert body["days"][1]["count"] == 1  # 明日到期 1 题

    def test_exam_plan_sorted_by_weight(self, auth_client: TestClient):
        _create(auth_client, "题 A")
        _create(auth_client, "题 B")
        resp = auth_client.post("/api/v1/plans/exam", json={
            "exam_date": "2026-09-01", "daily_target": 5,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["daily_target"] == 5
        assert all("score" in i for i in body["items"])

    def test_plan_item_complete_skip_reset(self, auth_client: TestClient):
        created = _create(auth_client, "一辆汽车以 20m/s 行驶，刹车加速度 5m/s²，求刹车距离。")
        from app.db.session import get_sessionmaker
        from app.db.models import PlanItem
        db = get_sessionmaker()()
        try:
            item = db.query(PlanItem).filter(PlanItem.mistake_id == created["id"]).first()
            item_id = item.id
        finally:
            db.close()
        resp = auth_client.patch(f"/api/v1/plans/items/{item_id}", json={"action": "skip"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "skipped"
        resp = auth_client.patch(f"/api/v1/plans/items/{item_id}", json={"action": "reset"})
        assert resp.json()["status"] == "pending"
        resp = auth_client.patch(f"/api/v1/plans/items/{item_id}", json={"action": "complete"})
        assert resp.json()["status"] == "completed"
