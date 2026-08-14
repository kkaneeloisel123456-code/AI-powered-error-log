"""M4 验收：数据看板、知识图谱、导出、备份（PRD 7.6/7.7）。"""
import io
import zipfile

import pytest
from fastapi.testclient import TestClient


def _create(auth_client: TestClient, question: str, subject_id: int = 1,
            kp_id: int | None = None, error_type: str = "calculation", status: str = "pending") -> dict:
    resp = auth_client.post("/api/v1/mistakes", json={
        "question_text": question,
        "answer_text": "B",
        "subject_id": subject_id,
        "kp_id": kp_id,
        "error_type": error_type,
        "status": status,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _kp_id(auth_client: TestClient, subject_name: str, kp_name: str) -> int:
    kps = auth_client.get("/api/v1/knowledge-points").json()
    return next(k["id"] for k in kps if k["name"] == kp_name)


@pytest.fixture()
def seeded(auth_client: TestClient):
    kp1 = _kp_id(auth_client, "物理", "牛顿运动定律")
    kp2 = _kp_id(auth_client, "数学", "函数与导数")
    _create(auth_client, "物理题一：牛顿第二定律应用", subject_id=4, kp_id=kp1, error_type="knowledge")
    _create(auth_client, "物理题二：摩擦力计算", subject_id=4, kp_id=kp1, error_type="calculation", status="wrong")
    _create(auth_client, "数学题一：求导数", subject_id=1, kp_id=kp2, error_type="logic", status="mastered")
    return {"kp1": kp1, "kp2": kp2}


class TestDashboardSummary:
    def test_summary_shape(self, auth_client: TestClient, seeded):
        body = auth_client.get("/api/v1/dashboard/summary?range_days=7").json()
        assert body["range_days"] == 7
        assert body["totals"]["mistakes"] == 3
        assert len(body["trend"]) == 7  # 近 7 天逐日
        today = body["trend"][-1]
        assert today["created"] == 3
        assert set(body) >= {"subjects", "errors", "statuses", "weak_points"}

    def test_subject_distribution(self, auth_client: TestClient, seeded):
        body = auth_client.get("/api/v1/dashboard/summary").json()
        subjects = {s["name"]: s["value"] for s in body["subjects"]}
        assert subjects.get("物理") == 2
        assert subjects.get("数学") == 1

    def test_error_distribution_top5(self, auth_client: TestClient, seeded):
        body = auth_client.get("/api/v1/dashboard/summary").json()
        errors = {e["type"]: e["value"] for e in body["errors"]}
        assert errors["knowledge"] == 1
        assert errors["calculation"] == 1
        assert errors["logic"] == 1
        assert len(body["errors"]) <= 5

    def test_status_distribution(self, auth_client: TestClient, seeded):
        body = auth_client.get("/api/v1/dashboard/summary").json()
        statuses = {s["status"]: s["value"] for s in body["statuses"]}
        assert statuses["pending"] == 1
        assert statuses["wrong"] == 1
        assert statuses["mastered"] == 1

    def test_weak_point_ranking(self, auth_client: TestClient, seeded):
        body = auth_client.get("/api/v1/dashboard/summary").json()
        assert body["weak_points"]
        top = body["weak_points"][0]
        assert top["name"] == "牛顿运动定律"  # 2 题 > 1 题
        assert top["mistake_count"] == 2
        assert "score" in top

    def test_range_30(self, auth_client: TestClient, seeded):
        body = auth_client.get("/api/v1/dashboard/summary?range_days=30").json()
        assert len(body["trend"]) == 30

    def test_invalid_range(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/dashboard/summary?range_days=99")
        assert resp.status_code == 422

    def test_empty_dashboard(self, auth_client: TestClient):
        body = auth_client.get("/api/v1/dashboard/summary").json()
        assert body["totals"]["mistakes"] == 0
        assert body["weak_points"] == []


class TestKnowledgeGraph:
    def test_graph_nodes_and_edges(self, auth_client: TestClient, seeded):
        body = auth_client.get("/api/v1/graph/knowledge").json()
        nodes = {n["name"]: n for n in body["nodes"]}
        assert "牛顿运动定律" in nodes
        assert nodes["牛顿运动定律"]["value"] == 2  # 节点大小映射错题数
        assert nodes["牛顿运动定律"]["mastery"] == 0.0
        assert nodes["函数与导数"]["value"] == 1
        assert nodes["函数与导数"]["mastery"] == 1.0  # 颜色映射掌握度
        # 父子边
        hierarchy = [e for e in body["edges"] if e["type"] == "hierarchy"]
        assert hierarchy

    def test_graph_subject_filter(self, auth_client: TestClient, seeded):
        body = auth_client.get("/api/v1/graph/knowledge?subject_id=4").json()
        names = {n["name"] for n in body["nodes"]}
        assert "牛顿运动定律" in names
        assert "函数与导数" not in names

    def test_graph_empty(self, auth_client: TestClient):
        body = auth_client.get("/api/v1/graph/knowledge").json()
        assert body["nodes"] == []
        assert body["edges"] == []

    def test_kp_filter_on_mistakes_list(self, auth_client: TestClient, seeded):
        """PRD 7.6-19：点击知识点节点联动该知识点错题列表。"""
        body = auth_client.get(f"/api/v1/mistakes?kp_id={seeded['kp1']}").json()
        assert body["total"] == 2
        assert all("物理" in it["question_excerpt"] for it in body["items"])


class TestExport:
    def test_markdown_export_template(self, auth_client: TestClient, seeded):
        resp = auth_client.get("/api/v1/export/markdown")
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        assert "filename*=UTF-8''" in resp.headers["content-disposition"]  # RFC 5987 中文文件名
        content = resp.text
        assert "Recall 错题导出" in content
        assert "物理题一：牛顿第二定律应用" in content
        assert "**答案**" in content
        assert "复习次数" in content

    def test_markdown_export_respects_filters(self, auth_client: TestClient, seeded):
        resp = auth_client.get("/api/v1/export/markdown", params={"status": "wrong"})
        assert "物理题二：摩擦力计算" in resp.text
        assert "物理题一" not in resp.text

    def test_markdown_export_requires_auth(self, auth_client: TestClient):
        client = TestClient(auth_client.app)
        resp = client.get("/api/v1/export/markdown")
        assert resp.status_code == 401

    def test_pdf_export_html_paper_style(self, auth_client: TestClient, seeded):
        resp = auth_client.get("/api/v1/export/pdf")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        html = resp.text
        assert "@page" in html and "A4" in html  # A4 排版
        assert "#F7F4EE" in html  # 纸感米白
        assert "物理题一" in html
        assert "共 <b>3</b> 题" in html  # 封面统计摘要

    def test_pdf_token_query_auth(self, auth_client: TestClient, token: str):
        """新标签打印场景：?token= 放行。"""
        client = TestClient(auth_client.app)
        resp = client.get(f"/api/v1/export/pdf?token={token}")
        assert resp.status_code == 200


class TestBackup:
    def test_backup_zip_contains_db_and_uploads(self, auth_client: TestClient, seeded):
        resp = auth_client.get("/api/v1/settings/backup")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = zf.namelist()
            assert "recall.sqlite3" in names
            assert zf.testzip() is None

    def test_restore_invalid_zip_rejected(self, auth_client: TestClient):
        resp = auth_client.post(
            "/api/v1/settings/backup/restore",
            files={"file": ("bad.zip", b"not a zip", "application/zip")},
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_restore_valid_backup(self, auth_client: TestClient, seeded):
        backup = auth_client.get("/api/v1/settings/backup").content
        resp = auth_client.post(
            "/api/v1/settings/backup/restore",
            files={"file": ("Recall_backup.zip", backup, "application/zip")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["restored"] is True
        assert body["restart_required"] is True
