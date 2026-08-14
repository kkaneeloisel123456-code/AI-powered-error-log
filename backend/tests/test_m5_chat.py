"""M5 验收：AI 答疑 SSE、会话历史、加入错题本（PRD 7.8）。"""
import json

import pytest
from fastapi.testclient import TestClient


def _stream_chat(auth_client: TestClient, content: str, conversation_id: str | None = None):
    """消费 SSE 流，返回 (events, conversation_id)。"""
    with auth_client.stream("POST", "/api/v1/chat", json={
        "conversation_id": conversation_id, "content": content, "attachments": [],
    }) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        events = []
        buffer = ""
        for chunk in resp.iter_text():
            buffer += chunk
            while "\n\n" in buffer:
                frame, buffer = buffer.split("\n\n", 1)
                event, data = None, None
                for line in frame.split("\n"):
                    if line.startswith("event:"):
                        event = line[6:].strip()
                    elif line.startswith("data:"):
                        data = json.loads(line[5:].strip())
                events.append((event, data))
    return events, None


class TestChatStream:
    def test_stream_tokens_and_done(self, auth_client: TestClient):
        events, _ = _stream_chat(auth_client, "这道题为什么选 C？")
        assert events[0][0] == "token"
        assert events[0][1]["delta"]
        assert events[-1][0] == "done"
        conv_id = events[-1][1]["conversation_id"]
        assert conv_id.startswith("conv_")

    def test_empty_content_rejected(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/chat", json={"content": ""})
        assert resp.status_code == 422

    def test_conversation_created_with_messages(self, auth_client: TestClient):
        events, _ = _stream_chat(auth_client, "换一种解法")
        conv_id = events[-1][1]["conversation_id"]
        messages = auth_client.get(f"/api/v1/conversations/{conv_id}/messages").json()
        roles = [m["role"] for m in messages]
        assert "user" in roles and "assistant" in roles
        assert messages[-1]["content"]  # mock 回答有内容


class TestConversations:
    def test_list_create_update(self, auth_client: TestClient):
        created = auth_client.post("/api/v1/conversations").json()
        assert created["id"].startswith("conv_")
        listed = auth_client.get("/api/v1/conversations").json()
        assert any(c["id"] == created["id"] for c in listed)
        updated = auth_client.patch(f"/api/v1/conversations/{created['id']}",
                                    json={"title": "立体几何答疑"}).json()
        assert updated["title"] == "立体几何答疑"

    def test_search_conversations(self, auth_client: TestClient):
        c1 = auth_client.post("/api/v1/conversations").json()
        auth_client.patch(f"/api/v1/conversations/{c1['id']}", json={"title": "电磁感应"})
        auth_client.post("/api/v1/conversations")
        found = auth_client.get("/api/v1/conversations", params={"q": "电磁"}).json()
        assert len(found) == 1

    def test_clear_keeps_conversation(self, auth_client: TestClient):
        events, _ = _stream_chat(auth_client, "测试清空")
        conv_id = events[-1][1]["conversation_id"]
        resp = auth_client.post(f"/api/v1/conversations/{conv_id}/clear")
        assert resp.status_code == 204
        assert auth_client.get(f"/api/v1/conversations/{conv_id}/messages").json() == []

    def test_delete_removes_conversation(self, auth_client: TestClient):
        c = auth_client.post("/api/v1/conversations").json()
        resp = auth_client.delete(f"/api/v1/conversations/{c['id']}")
        assert resp.status_code == 204
        assert auth_client.get(f"/api/v1/conversations/{c['id']}/messages").status_code == 404


class TestExtractToMistake:
    def test_extract_and_import(self, auth_client: TestClient):
        """PRD 7.8-26 前置：对话 -> 提取题目草稿 -> 补答案 -> 归档，错题本数据独立。"""
        events, _ = _stream_chat(auth_client, "已知 f(x)=x²，求 f'(2) 的值。")
        conv_id = events[-1][1]["conversation_id"]
        assistant_id = events[-1][1]["message_id"]
        draft = auth_client.post("/api/v1/chat/extract", json={
            "conversation_id": conv_id, "message_id": assistant_id,
        }).json()
        assert draft["mock"] is True
        assert "f(x)" in draft["question_text"]
        assert draft["answer"] == ""  # mock 缺答案 -> 提示用户补充（PRD 5.1.3）

        # 补答案后归档
        created = auth_client.post("/api/v1/mistakes", json={
            "question_text": draft["question_text"],
            "answer_text": "4",
            "analysis": draft["analysis"],
            "subject_id": 1,
            "source": "chat",
        })
        assert created.status_code == 201
        assert created.json()["source"] == "chat"

        # 删除会话不影响错题本（PRD 7.8-26）
        auth_client.delete(f"/api/v1/conversations/{conv_id}")
        listed = auth_client.get("/api/v1/mistakes").json()
        assert listed["total"] == 1
