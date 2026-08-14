"""M2 验收：识图录入（PRD 7.1/7.2）与 EX-01~07 异常矩阵。"""
import io
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image


def _make_png(size_kb: int = 8) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _upload(auth_client: TestClient, content: bytes, filename: str = "exam.png", client_id: str | None = None) -> dict:
    client_id = client_id or uuid.uuid4().hex
    resp = auth_client.post(
        "/api/v1/uploads",
        files={"file": (filename, content, "image/png")},
        data={"client_id": client_id},
    )
    return {"status_code": resp.status_code, **resp.json()} if resp.status_code < 400 else {"status_code": resp.status_code, **resp.json()}


def _wait_awaiting(auth_client: TestClient, task_id: str, timeout_s: float = 10.0) -> dict:
    started = time.monotonic()
    while time.monotonic() - started < timeout_s:
        body = auth_client.get(f"/api/v1/tasks/{task_id}").json()
        if body["status"] in ("awaiting_confirm", "failed", "done"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"task {task_id} timeout, last={body['status']}")


class TestUploadValidation:
    def test_ex01_invalid_format_blocked(self, auth_client: TestClient):
        resp = auth_client.post(
            "/api/v1/uploads",
            files={"file": ("anim.gif", b"GIF89a", "image/gif")},
            data={"client_id": uuid.uuid4().hex},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert "JPG / PNG / WebP / HEIC" in body["message"]

    def test_ex02_too_large_blocked(self, auth_client: TestClient):
        big = b"x" * (10 * 1024 * 1024 + 1)
        resp = auth_client.post(
            "/api/v1/uploads",
            files={"file": ("big.png", big, "image/png")},
            data={"client_id": uuid.uuid4().hex},
        )
        assert resp.status_code == 422
        assert "10MB" in resp.json()["message"]


class TestOcrPipeline:
    def test_upload_creates_task_and_runs(self, auth_client: TestClient):
        uploaded = _upload(auth_client, _make_png())
        assert uploaded["status_code"] == 201
        assert uploaded["task_id"].startswith("task_")
        # TestClient 同步执行 BackgroundTasks：上传返回后即可轮询
        body = _wait_awaiting(auth_client, uploaded["task_id"])
        assert body["status"] == "awaiting_confirm"
        assert body["progress"]["phase"] == "awaiting_confirm"
        assert body["result_url"].endswith("/candidates")

    def test_candidates_contain_two_questions(self, auth_client: TestClient):
        uploaded = _upload(auth_client, _make_png())
        _wait_awaiting(auth_client, uploaded["task_id"])
        body = auth_client.get(f"/api/v1/tasks/{uploaded['task_id']}/candidates").json()
        assert len(body["candidates"]) == 2
        first = body["candidates"][0]
        assert first["question_text"]
        assert first["options"]
        assert first["confidence_fields"]  # mock 第 1 题答案低置信（EX-04 高亮）

    def test_upload_idempotent_same_client_id(self, auth_client: TestClient):
        client_id = uuid.uuid4().hex
        first = _upload(auth_client, _make_png(), client_id=client_id)
        second = _upload(auth_client, _make_png(), client_id=client_id)
        assert first["task_id"] == second["task_id"]  # 重试不产生重复任务

    def test_ex03_ocr_failed_and_retry(self, auth_client: TestClient, monkeypatch):
        from app.tasks import runner
        monkeypatch.setattr(runner, "_run_ocr", lambda _path: "")
        uploaded = _upload(auth_client, _make_png())
        body = _wait_awaiting(auth_client, uploaded["task_id"])
        assert body["status"] == "failed"
        assert "未识别到清晰文字" in body["error"]

        # 恢复后重试成功
        monkeypatch.setattr(runner, "_run_ocr", lambda _path: "第1题：测试题干 A. 1 B. 2")
        retry = auth_client.post(f"/api/v1/tasks/{uploaded['task_id']}/retry").json()
        assert retry["status"] in ("queued", "ocr_running", "splitting")
        final = _wait_awaiting(auth_client, uploaded["task_id"])
        assert final["status"] == "awaiting_confirm"

    def test_cancel_task(self, auth_client: TestClient):
        uploaded = _upload(auth_client, _make_png())
        resp = auth_client.post(f"/api/v1/tasks/{uploaded['task_id']}/cancel")
        assert resp.status_code == 204

    def test_unknown_task_404(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/tasks/task_none")
        assert resp.status_code == 404


class TestImportCandidates:
    @pytest.fixture(autouse=True)
    def _upload_and_get(self, auth_client: TestClient):
        uploaded = _upload(auth_client, _make_png())
        _wait_awaiting(auth_client, uploaded["task_id"])
        body = auth_client.get(f"/api/v1/tasks/{uploaded['task_id']}/candidates").json()
        self.task_id = uploaded["task_id"]
        self.candidates = body["candidates"]
        yield

    def test_import_all_candidates(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/problems/import", json={
            "candidates": self.candidates, "task_id": self.task_id,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["imported"] == 2
        assert body["duplicates"] == 0
        assert len(body["mistake_ids"]) == 2
        # 任务完结
        task = auth_client.get(f"/api/v1/tasks/{self.task_id}").json()
        assert task["status"] == "done"
        # 新错题进入错题本
        listed = auth_client.get("/api/v1/mistakes").json()
        assert listed["total"] == 2

    def test_reimport_duplicates_detected(self, auth_client: TestClient):
        auth_client.post("/api/v1/problems/import", json={"candidates": self.candidates})
        resp = auth_client.post("/api/v1/problems/import", json={
            "candidates": self.candidates,
        })
        body = resp.json()
        assert body["imported"] == 0
        assert body["duplicates"] == 2  # 同题干去重

    def test_import_idempotency_key(self, auth_client: TestClient):
        first = auth_client.post("/api/v1/problems/import", json={
            "candidates": self.candidates, "idempotency_key": "imp_001",
        }).json()
        second = auth_client.post("/api/v1/problems/import", json={
            "candidates": self.candidates, "idempotency_key": "imp_001",
        }).json()
        assert first == second  # 重复请求不产生重复数据

    def test_import_empty_question_rejected(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/problems/import", json={
            "candidates": [{"question_text": ""}],
        })
        assert resp.status_code == 422


class TestTextImport:
    def test_text_suggest_mock_classify(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/problems/text", json={
            "question_text": "已知函数 f(x)=x³-3x，求 f(x) 的单调区间。",
            "options": [], "answer_text": "", "analysis": "",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["mock"] is True
        assert body["kp_name"] == "函数与导数"
        assert body["subject_id"] is not None

    def test_text_suggest_empty_question_rejected(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/problems/text", json={"question_text": ""})
        assert resp.status_code == 422  # EX-07 后端兜底

    def test_text_flow_to_mistake(self, auth_client: TestClient):
        """文本录入闭环：AI 补全 -> 用户确认 -> POST /mistakes 归档。"""
        suggest = auth_client.post("/api/v1/problems/text", json={
            "question_text": "已知函数 f(x)=x³-3x，求 f(x) 的单调区间。",
            "answer_text": "(-∞,-1) 与 (1,+∞) 递增", "analysis": "求导判断符号",
        }).json()
        created = auth_client.post("/api/v1/mistakes", json={
            "question_text": "已知函数 f(x)=x³-3x，求 f(x) 的单调区间。",
            "answer_text": "(-∞,-1) 与 (1,+∞) 递增",
            "analysis": "求导判断符号",
            "subject_id": suggest["subject_id"],
            "kp_id": suggest["kp_id"],
            "error_type": suggest["error_type"],
            "source": "text",
        })
        assert created.status_code == 201
        assert created.json()["kp_id"] == suggest["kp_id"]
