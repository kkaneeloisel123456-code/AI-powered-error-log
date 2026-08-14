"""M1 验收：错题 CRUD、列表检索、批量操作、审计（PRD 7.3）。"""
import pytest
from fastapi.testclient import TestClient


def _create(auth_client: TestClient, **overrides) -> dict:
    payload = {
        "question_text": "一物体在粗糙水平面上滑行，已知初速度为 4m/s，摩擦因数 0.2，求滑行距离。",
        "options": ["A. 2m", "B. 4m", "C. 8m", "D. 16m"],
        "answer_text": "B",
        "analysis": "由动能定理：-μmgs = 0 - 1/2 mv²，解得 s = 4m",
        "subject_id": 1,
        "error_type": "calculation",
        "tags": [],
        **overrides,
    }
    resp = auth_client.post("/api/v1/mistakes", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestMistakeCrud:
    def test_create_and_detail(self, auth_client: TestClient):
        created = _create(auth_client)
        assert created["id"].startswith("m_")
        assert created["status"] == "pending"
        assert created["color"] == "#6B7280"  # 未开始灰
        assert created["subject_name"] == "数学"

        detail = auth_client.get(f"/api/v1/mistakes/{created['id']}").json()
        assert detail["question_text"].startswith("一物体")
        assert detail["options"] == ["A. 2m", "B. 4m", "C. 8m", "D. 16m"]
        assert "动能定理" in detail["analysis"]

    def test_create_empty_question_rejected(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/mistakes", json={
            "question_text": "", "subject_id": 1,
        })
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_invalid_subject_rejected(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/mistakes", json={
            "question_text": "题目", "subject_id": 9999,
        })
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_update_status_syncs_color_and_audits(self, auth_client: TestClient):
        created = _create(auth_client)
        resp = auth_client.patch(f"/api/v1/mistakes/{created['id']}", json={"status": "mastered"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "mastered"
        assert body["color"] == "#16A34A"  # 已掌握绿（颜色跟随状态）

        from app.db.session import get_sessionmaker
        from app.db.models import AuditLog
        db = get_sessionmaker()()
        try:
            logs = db.query(AuditLog).filter(AuditLog.entity_id == created["id"]).all()
            assert any(l.action == "status_change" for l in logs)  # 手动调整记录在案
        finally:
            db.close()

    def test_update_custom_color_only(self, auth_client: TestClient):
        created = _create(auth_client)
        body = auth_client.patch(f"/api/v1/mistakes/{created['id']}", json={"color": "#2563EB"}).json()
        assert body["color"] == "#2563EB"
        assert body["status"] == "pending"  # 自定义颜色不影响状态

    def test_update_question_fields(self, auth_client: TestClient):
        created = _create(auth_client)
        body = auth_client.patch(f"/api/v1/mistakes/{created['id']}", json={
            "question_text": "修改后的题干", "tags": ["月考", "易错"], "error_type": "logic",
        }).json()
        assert body["question_text"] == "修改后的题干"
        assert body["tags"] == ["月考", "易错"]
        assert body["error_type"] == "logic"

    def test_delete_removes_mistake_and_plan_items(self, auth_client: TestClient):
        created = _create(auth_client)
        resp = auth_client.delete(f"/api/v1/mistakes/{created['id']}")
        assert resp.status_code == 204
        assert auth_client.get(f"/api/v1/mistakes/{created['id']}").status_code == 404

    def test_delete_unknown_404(self, auth_client: TestClient):
        resp = auth_client.delete("/api/v1/mistakes/m_not_exist")
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"


def _subject_id_by_name(auth_client: TestClient, name: str) -> int:
    return next(s["id"] for s in auth_client.get("/api/v1/subjects").json() if s["name"] == name)


class TestMistakeList:
    @pytest.fixture(autouse=True)
    def _seed(self, auth_client: TestClient):
        physics_id = _subject_id_by_name(auth_client, "物理")
        _create(auth_client, question_text="动能定理综合题", tags=["周测"], error_type="calculation")
        _create(auth_client, question_text="电磁感应习题", subject_id=physics_id, tags=["月考"],
                error_type="concept", status="wrong")
        _create(auth_client, question_text="导数与极值", error_type="logic")
        self.physics_id = physics_id
        yield

    def test_list_pagination_contract(self, auth_client: TestClient):
        body = auth_client.get("/api/v1/mistakes?page=1&page_size=20").json()
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert len(body["items"]) == 3
        item = body["items"][0]
        assert set(item) >= {"id", "subject_id", "question_excerpt", "status", "color", "tags",
                             "last_reviewed_at", "review_count"}

    def test_search_keyword(self, auth_client: TestClient):
        body = auth_client.get("/api/v1/mistakes", params={"q": "动能"}).json()
        assert body["total"] == 1
        assert "动能定理" in body["items"][0]["question_excerpt"]

    def test_filter_subject_status_error_type(self, auth_client: TestClient):
        body = auth_client.get("/api/v1/mistakes", params={
            "subject_id": self.physics_id, "status": "wrong", "error_type": "concept",
        }).json()
        assert body["total"] == 1
        assert body["items"][0]["subject_id"] == self.physics_id

    def test_filter_tags(self, auth_client: TestClient):
        body = auth_client.get("/api/v1/mistakes", params={"tags": "周测"}).json()
        assert body["total"] == 1

    def test_sort_by_review_count_desc(self, auth_client: TestClient):
        body = auth_client.get("/api/v1/mistakes?sort=review_count&order=desc").json()
        assert body["total"] == 3

    def test_invalid_sort_rejected(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/mistakes?sort=hacker")
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_page_size_capped(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/mistakes?page_size=999")
        assert resp.status_code == 422  # le=100


class TestMistakeBatch:
    @pytest.fixture(autouse=True)
    def _seed(self, auth_client: TestClient):
        self.ids = [_create(auth_client, question_text=f"批量题 {i}")["id"] for i in range(3)]
        yield

    def test_batch_set_status(self, auth_client: TestClient):
        body = auth_client.post("/api/v1/mistakes/batch",
                                json={"action": "set_status", "ids": self.ids[:2], "value": "fixing"}).json()
        assert body["updated"] == 2
        for mid in self.ids[:2]:
            detail = auth_client.get(f"/api/v1/mistakes/{mid}").json()
            assert detail["status"] == "fixing"
            assert detail["color"] == "#EA8C00"  # 待巩固橙

    def test_batch_add_tags(self, auth_client: TestClient):
        body = auth_client.post("/api/v1/mistakes/batch",
                                json={"action": "add_tags", "ids": self.ids, "value": "期中"}).json()
        assert body["updated"] == 3
        detail = auth_client.get(f"/api/v1/mistakes/{self.ids[0]}").json()
        assert "期中" in detail["tags"]

    def test_batch_delete(self, auth_client: TestClient):
        body = auth_client.post("/api/v1/mistakes/batch",
                                json={"action": "delete", "ids": self.ids}).json()
        assert body["deleted"] == 3
        assert auth_client.get(f"/api/v1/mistakes/{self.ids[0]}").status_code == 404

    def test_batch_invalid_action(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/mistakes/batch",
                                json={"action": "drop_table", "ids": self.ids})
        assert resp.status_code == 422


class TestSubjects:
    def test_list_subjects_with_counts(self, auth_client: TestClient):
        _create(auth_client, subject_id=1)
        subjects = auth_client.get("/api/v1/subjects").json()
        assert len(subjects) >= 9
        math = next(s for s in subjects if s["name"] == "数学")
        assert math["mistake_count"] == 1

    def test_knowledge_points_tree(self, auth_client: TestClient):
        physics_id = _subject_id_by_name(auth_client, "物理")
        kps = auth_client.get(f"/api/v1/knowledge-points?subject_id={physics_id}").json()
        assert len(kps) > 5
        l1 = [k for k in kps if k["level"] == 1]
        l2 = [k for k in kps if k["level"] == 2]
        assert l1 and l2
        assert any(k["parent_id"] for k in l2)
        assert all(k["path"].startswith("/") for k in kps)

    def test_create_duplicate_subject_conflict(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/subjects", json={"name": "数学"})
        assert resp.status_code == 409
        assert resp.json()["code"] == "CONFLICT"

    def test_delete_subject_with_mistakes_conflict(self, auth_client: TestClient):
        _create(auth_client, subject_id=1)
        math = next(s for s in auth_client.get("/api/v1/subjects").json() if s["name"] == "数学")
        resp = auth_client.delete(f"/api/v1/subjects/{math['id']}")
        assert resp.status_code == 409


class TestSettingsApi:
    def test_get_settings_shape(self, auth_client: TestClient):
        body = auth_client.get("/api/v1/settings").json()
        assert set(body) == {"ai", "privacy", "default_review", "token_masked", "version"}
        assert body["ai"]["mock"] is True
        assert body["token_masked"].startswith("••") is False  # 掩码格式：前6+••••+后4
        assert "••••" in body["token_masked"]

    def test_set_api_key_masked(self, auth_client: TestClient):
        resp = auth_client.patch("/api/v1/settings", json={"api_key": "sk-test-1234567890"})
        body = resp.json()
        assert body["ai"]["has_api_key"] is True
        assert "sk-test" not in body["ai"]["api_key_masked"]  # 前端只见掩码

        from app.ai.gateway import AiGateway
        from app.db.session import get_sessionmaker
        db = get_sessionmaker()()
        try:
            assert AiGateway.get_api_key(db) == "sk-test-1234567890"  # 落盘为加密
        finally:
            db.close()

    def test_privacy_update(self, auth_client: TestClient):
        body = auth_client.patch("/api/v1/settings", json={
            "privacy": {"send_question_to_ai": False, "lan_enabled": False},
        }).json()
        assert body["privacy"]["send_question_to_ai"] is False

    def test_test_ai_mock(self, auth_client: TestClient):
        body = auth_client.post("/api/v1/settings/test-ai", json={}).json()
        assert body["ok"] is True
        assert body["mock"] is True
