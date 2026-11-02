"""API 集成测试（mock LLM）。"""
import json

import pytest
from fastapi.testclient import TestClient

from app import llm


@pytest.fixture()
def client(monkeypatch):
    from app.main import app

    async def fake_chat_once(messages, **kwargs):
        system = messages[0]["content"]
        if "意图分类器" in system:
            text = messages[-1]["content"]
            if "退款" in text or "退钱" in text:
                return '{"intent": "refund", "confidence": 0.95}'
            if "订单" in text or "物流" in text:
                return '{"intent": "order_query", "confidence": 0.9}'
            if "报错" in text or "登录" in text:
                return '{"intent": "tech_support", "confidence": 0.9}'
            return '{"intent": "general", "confidence": 0.85}'
        return "这是模拟的回答。"

    async def fake_chat_stream(messages, **kwargs):
        for piece in ["这是", "模拟", "回答"]:
            yield piece

    monkeypatch.setattr(llm, "chat_once", fake_chat_once)
    monkeypatch.setattr(llm, "chat_stream", fake_chat_stream)
    with TestClient(app) as c:
        yield c


def _send(client: TestClient, cid: str, text: str):
    resp = client.post(f"/api/chat/{cid}/message", json={"content": text})
    assert resp.status_code == 200
    events = {}
    for block in resp.text.split("\n\n"):
        event, data = None, None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        if event and data:
            events[event] = json.loads(data)
    return events


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_chat_flow(client):
    cid = client.post("/api/chat/start", json={}).json()["conversationId"]
    events = _send(client, cid, "如何申请退款？")  # 退款 → 转人工
    assert events["meta"]["intent"] == "refund"
    assert events["transfer"] is not None

    # 转人工后，普通消息进入排队，机器人不回复
    events2 = _send(client, cid, "你好")
    assert "queued" in events2
    assert "meta" not in events2


def test_chat_normal_reply(client):
    cid = client.post("/api/chat/start", json={}).json()["conversationId"]
    events = _send(client, cid, "今天天气不错")
    assert "meta" in events
    assert events["meta"]["intent"] == "general"
    assert "delta" in events
    assert "transfer" not in events


def test_messages_and_feedback(client):
    cid = client.post("/api/chat/start", json={}).json()["conversationId"]
    _send(client, cid, "你好")
    data = client.get(f"/api/chat/{cid}/messages").json()
    assert data["status"] == "bot"
    roles = [m["role"] for m in data["messages"]]
    assert roles == ["user", "assistant"]

    resp = client.post(f"/api/chat/{cid}/feedback", json={"rating": 5, "comment": "很好"})
    assert resp.json()["ok"]
    assert client.get(f"/api/chat/{cid}/messages").json()["status"] == "closed"
    assert client.post(f"/api/chat/{cid}/feedback", json={"rating": 9}).status_code == 400


def _login(client: TestClient):
    resp = client.post("/api/admin/login", json={"password": "test-pass"})
    assert resp.json()["ok"]


def test_admin_auth(client):
    assert client.get("/api/admin/stats").status_code == 401
    assert client.post("/api/admin/login", json={"password": "wrong"}).status_code == 401
    _login(client)
    assert client.get("/api/admin/me").json()["ok"]


def test_faq_crud(client):
    _login(client)
    fid = client.post("/api/faqs", json={"question": "测试问题？", "answer": "测试答案", "keywords": "测试"}).json()["id"]
    faqs = client.get("/api/faqs").json()["faqs"]
    assert any(f["id"] == fid for f in faqs)
    client.put(f"/api/faqs/{fid}", json={"question": "改过的问题？", "enabled": False})
    faq = next(f for f in client.get("/api/faqs").json()["faqs"] if f["id"] == fid)
    assert faq["question"] == "改过的问题？"
    assert not faq["enabled"]
    assert client.delete(f"/api/faqs/{fid}").json()["ok"]
    assert client.delete(f"/api/faqs/{fid}").status_code == 404


def test_workbench_full_loop(client):
    _login(client)
    # 用户触发转人工
    cid = client.post("/api/chat/start", json={}).json()["conversationId"]
    _send(client, cid, "我要退款")

    pending = client.get("/api/admin/workbench/pending").json()["conversations"]
    assert any(c["id"] == cid for c in pending)

    # 客服回复 → 用户轮询可见 → 交还机器人
    assert client.post(f"/api/admin/conversations/{cid}/reply", json={"content": "您好，人工客服为您服务"}).json()["messageId"]
    data = client.get(f"/api/chat/{cid}/messages").json()
    assert any(m["role"] == "human_agent" for m in data["messages"])
    assert client.post(f"/api/admin/conversations/{cid}/resolve").json()["ok"]
    assert client.get(f"/api/chat/{cid}/messages").json()["status"] == "bot"


def test_stats(client):
    _login(client)
    stats = client.get("/api/admin/stats").json()
    assert stats["totalConversations"] >= 1
    assert set(stats["feedback"]["distribution"].keys()) == {"1", "2", "3", "4", "5"}
