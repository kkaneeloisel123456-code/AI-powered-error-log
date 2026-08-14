"""M0 验收：健康检查、启动引导、Token 鉴权、学科种子。"""
from fastapi.testclient import TestClient


class TestHealth:
    def test_health_ok(self, client: TestClient):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body
        assert set(body["mock"]) == {"ai", "ocr"}

    def test_root_docs(self, client: TestClient):
        assert client.get("/docs").status_code == 200


class TestAuthBootstrap:
    def test_token_file_created(self, data_dir, client: TestClient):
        assert (data_dir / "auth" / "token.key").exists()

    def test_status_without_token(self, client: TestClient):
        body = client.get("/api/v1/auth/status").json()
        assert body == {"configured": True, "authenticated": False}

    def test_setup_reveals_token_once(self, client: TestClient, token: str):
        first = client.post("/api/v1/auth/setup").json()
        assert first["token"] == token  # 首次揭示
        assert first["token_masked"].startswith(token[:6])
        second = client.post("/api/v1/auth/setup").json()
        assert second["token"] is None  # 之后仅掩码

    def test_verify_wrong_token_rejected(self, client: TestClient):
        resp = client.post("/api/v1/auth/verify-token", json={"token": "wrong-token"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "NOT_AUTHENTICATED"

    def test_verify_correct_token(self, client: TestClient, token: str):
        resp = client.post("/api/v1/auth/verify-token", json={"token": token})
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_protected_requires_auth(self, client: TestClient):
        resp = client.get("/api/v1/auth/verify")
        assert resp.status_code == 401

    def test_verify_with_bearer_ok(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/auth/verify")
        assert resp.status_code == 200


class TestSeed:
    def test_builtin_subjects_seeded(self, client: TestClient, token: str):
        """种子学科数量正确，知识树节点存在（M1 提供查询接口前直接查库）。"""
        from app.db.session import get_sessionmaker
        from app.db.models import Subject, KnowledgePoint

        db = get_sessionmaker()()
        try:
            subjects = db.query(Subject).order_by(Subject.sort_order).all()
            assert len(subjects) >= 9
            assert any(s.name == "物理" for s in subjects)
            kps = db.query(KnowledgePoint).count()
            assert kps > 30  # 内置知识树
        finally:
            db.close()

    def test_seed_idempotent(self, client: TestClient):
        """重复调用种子不产生重复数据（幂等）。"""
        from app.db.seed import seed_if_empty
        from app.db.session import get_sessionmaker
        from app.db.models import Subject

        db = get_sessionmaker()()
        try:
            count_before = db.query(Subject).count()
            seed_if_empty(db)
            count_after = db.query(Subject).count()
            assert count_before == count_after
        finally:
            db.close()


class TestErrorContract:
    def test_404_error_body(self, client: TestClient):
        resp = client.get("/api/v1/no-such-route")
        assert resp.status_code == 404

    def test_error_body_shape(self, client: TestClient, token: str):
        resp = client.post("/api/v1/auth/verify-token", json={"token": "bad"})
        body = resp.json()
        assert set(body) == {"code", "message", "details"}
