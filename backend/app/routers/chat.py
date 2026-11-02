"""用户侧聊天 API：SSE 流式对话、人工消息轮询、满意度评价。"""
import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .. import agent, config, database, llm

router = APIRouter(prefix="/api/chat")

TRANSFER_NOTICE = "检测到您的问题需要人工处理，已为您转接人工客服，请稍候，人工客服会直接在本对话中回复您。"


@router.post("/start")
async def start_conversation(request: Request):
    body = await request.json()
    visitor_id = str(body.get("visitorId") or database.new_id())[:64]
    cid = database.new_id()
    ts = database.now()
    database.execute(
        "INSERT INTO conversations (id, visitor_id, status, created_at, updated_at) VALUES (?,?,?,?,?)",
        (cid, visitor_id, "bot", ts, ts),
    )
    return {"conversationId": cid, "visitorId": visitor_id}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/{conversation_id}/message")
async def send_message(conversation_id: str, request: Request):
    body = await request.json()
    content = str(body.get("content") or "").strip()
    if not content or len(content) > 4000:
        return JSONResponse({"error": "消息内容为空或超长"}, status_code=400)

    conv = database.execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,), fetch="one"
    )
    if conv is None:
        return JSONResponse({"error": "会话不存在"}, status_code=404)

    async def event_stream():
        ts = database.now()
        database.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?,?,?,?)",
            (conversation_id, "user", content, ts),
        )
        database.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (ts, conversation_id)
        )

        # 人工接管中：不再由机器人回复，等客服处理
        if conv["status"] in ("human_pending", "human_active"):
            yield _sse("queued", {"message": "消息已发送，人工客服正在处理中，请稍候。"})
            yield _sse("done", {})
            return

        ctx = agent.AgentContext()
        ctx.intent, ctx.confidence = await agent.detect_intent(content)
        ctx.faq_hits = agent.search_faqs(content)

        yield _sse("meta", {
            "intent": ctx.intent,
            "intentLabel": agent.INTENT_LABELS.get(ctx.intent, ctx.intent),
            "confidence": round(ctx.confidence, 2),
            "faqHits": [{"id": h.id, "question": h.question, "score": round(h.score, 2)} for h in ctx.faq_hits],
        })

        if agent.wants_human(content) or agent.should_transfer(
            ctx.intent, ctx.confidence, ctx.faq_hits, conv["unresolved_rounds"]
        ):
            ctx.transfer = True
            ts2 = database.now()
            database.execute(
                "UPDATE conversations SET status = 'human_pending', intent = ?, unresolved_rounds = 0, updated_at = ? WHERE id = ?",
                (ctx.intent, ts2, conversation_id),
            )
            database.execute(
                "INSERT INTO messages (conversation_id, role, content, intent, created_at) VALUES (?,?,?,?,?)",
                (conversation_id, "assistant", TRANSFER_NOTICE, ctx.intent, ts2),
            )
            yield _sse("delta", {"content": TRANSFER_NOTICE})
            yield _sse("transfer", {"message": TRANSFER_NOTICE})
            yield _sse("done", {"transferred": True})
            return

        history_rows = database.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, config.MAX_HISTORY_TURNS * 2 + 1),
            fetch="all",
        )
        history = [{"role": r["role"] if r["role"] != "human_agent" else "assistant", "content": r["content"]}
                   for r in reversed(history_rows)]
        history = history[:-1]  # 去掉刚插入的当前用户消息

        messages = agent.build_chat_messages(history, content, ctx)
        full_reply = ""
        try:
            async for delta in llm.chat_stream(messages):
                full_reply += delta
                yield _sse("delta", {"content": delta})
        except llm.LLMError:
            fallback = (
                ctx.faq_hits[0].answer if ctx.faq_hits
                else "抱歉，系统暂时遇到了一点问题。您可以稍后重试，或回复「转人工」获取人工客服帮助。"
            )
            full_reply = full_reply or fallback
            yield _sse("delta", {"content": fallback if not full_reply else ""})

        ts3 = database.now()
        database.execute(
            "INSERT INTO messages (conversation_id, role, content, intent, created_at) VALUES (?,?,?,?,?)",
            (conversation_id, "assistant", full_reply, ctx.intent, ts3),
        )
        unresolved = conv["unresolved_rounds"]
        if not ctx.faq_hits and ctx.intent in ("order_query", "tech_support"):
            unresolved += 1
        else:
            unresolved = 0
        database.execute(
            "UPDATE conversations SET intent = ?, unresolved_rounds = ?, updated_at = ? WHERE id = ?",
            (ctx.intent, unresolved, ts3, conversation_id),
        )
        yield _sse("done", {"transferred": False})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })


@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: str, afterId: int = 0):
    rows = database.execute(
        "SELECT id, role, content, intent, created_at FROM messages WHERE conversation_id = ? AND id > ? ORDER BY id",
        (conversation_id, afterId),
        fetch="all",
    )
    conv = database.execute(
        "SELECT status FROM conversations WHERE id = ?", (conversation_id,), fetch="one"
    )
    if conv is None:
        return JSONResponse({"error": "会话不存在"}, status_code=404)
    return {
        "status": conv["status"],
        "messages": [
            {"id": r["id"], "role": r["role"], "content": r["content"],
             "intent": r["intent"], "createdAt": r["created_at"]}
            for r in rows
        ],
    }


@router.post("/{conversation_id}/feedback")
async def submit_feedback(conversation_id: str, request: Request):
    body = await request.json()
    try:
        rating = int(body.get("rating"))
    except (TypeError, ValueError):
        return JSONResponse({"error": "评分无效"}, status_code=400)
    if not 1 <= rating <= 5:
        return JSONResponse({"error": "评分需在 1-5 之间"}, status_code=400)
    comment = str(body.get("comment") or "")[:500]
    conv = database.execute(
        "SELECT id FROM conversations WHERE id = ?", (conversation_id,), fetch="one"
    )
    if conv is None:
        return JSONResponse({"error": "会话不存在"}, status_code=404)
    ts = database.now()
    database.execute(
        "INSERT OR REPLACE INTO feedback (conversation_id, rating, comment, created_at) VALUES (?,?,?,?)",
        (conversation_id, rating, comment, ts),
    )
    database.execute(
        "UPDATE conversations SET status = 'closed', updated_at = ? WHERE id = ?", (ts, conversation_id)
    )
    return {"ok": True}
