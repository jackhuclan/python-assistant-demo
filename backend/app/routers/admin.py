"""管理后台 API：登录、对话记录、客服工作台、满意度统计。"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .. import agent, auth, config, database

router = APIRouter(prefix="/api/admin")


def _require_admin(request: Request) -> JSONResponse | None:
    if not auth.verify_token(request.cookies.get(auth.COOKIE_NAME)):
        return JSONResponse({"error": "未登录或登录已过期"}, status_code=401)
    return None


# ---------- 登录 ----------

@router.post("/login")
async def login(request: Request):
    body = await request.json()
    if str(body.get("password") or "") != config.ADMIN_PASSWORD:
        return JSONResponse({"error": "密码错误"}, status_code=401)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        auth.COOKIE_NAME, auth.create_token(),
        httponly=True, samesite="lax", max_age=config.TOKEN_TTL_HOURS * 3600, path="/",
    )
    return resp


@router.post("/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.COOKIE_NAME, path="/")
    return resp


@router.get("/me")
async def me(request: Request):
    if resp := _require_admin(request):
        return resp
    return {"ok": True}


# ---------- 对话记录 ----------

@router.get("/conversations")
async def list_conversations(request: Request, status: str = "", intent: str = "", limit: int = 50, offset: int = 0):
    if resp := _require_admin(request):
        return resp
    limit = max(1, min(limit, 200))
    sql = """
        SELECT c.*, 
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count,
               (SELECT content FROM messages m WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_message,
               (SELECT rating FROM feedback f WHERE f.conversation_id = c.id) AS rating
        FROM conversations c WHERE 1=1
    """
    params: list = []
    if status:
        sql += " AND c.status = ?"
        params.append(status)
    if intent:
        sql += " AND c.intent = ?"
        params.append(intent)
    sql += " ORDER BY c.updated_at DESC LIMIT ? OFFSET ?"
    params += [limit, max(0, offset)]
    rows = database.execute(sql, tuple(params), fetch="all")
    return {"conversations": [
        {"id": r["id"], "visitorId": r["visitor_id"], "status": r["status"], "intent": r["intent"],
         "messageCount": r["message_count"], "lastMessage": r["last_message"],
         "rating": r["rating"], "createdAt": r["created_at"], "updatedAt": r["updated_at"]}
        for r in rows
    ]}


@router.get("/conversations/{conversation_id}")
async def conversation_detail(conversation_id: str, request: Request):
    if resp := _require_admin(request):
        return resp
    conv = database.execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,), fetch="one"
    )
    if conv is None:
        return JSONResponse({"error": "会话不存在"}, status_code=404)
    rows = database.execute(
        "SELECT id, role, content, intent, created_at FROM messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,), fetch="all",
    )
    return {
        "conversation": {"id": conv["id"], "visitorId": conv["visitor_id"], "status": conv["status"],
                         "intent": conv["intent"], "createdAt": conv["created_at"], "updatedAt": conv["updated_at"]},
        "messages": [
            {"id": r["id"], "role": r["role"], "content": r["content"],
             "intent": r["intent"], "createdAt": r["created_at"]}
            for r in rows
        ],
    }


# ---------- 客服工作台 ----------

@router.get("/workbench/pending")
async def pending_conversations(request: Request):
    if resp := _require_admin(request):
        return resp
    rows = database.execute(
        """SELECT c.*, 
                  (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count,
                  (SELECT content FROM messages m WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_message
           FROM conversations c
           WHERE c.status IN ('human_pending', 'human_active')
           ORDER BY CASE c.status WHEN 'human_pending' THEN 0 ELSE 1 END, c.updated_at DESC""",
        fetch="all",
    )
    return {"conversations": [
        {"id": r["id"], "visitorId": r["visitor_id"], "status": r["status"], "intent": r["intent"],
         "messageCount": r["message_count"], "lastMessage": r["last_message"], "updatedAt": r["updated_at"]}
        for r in rows
    ]}


@router.post("/conversations/{conversation_id}/reply")
async def reply(conversation_id: str, request: Request):
    if resp := _require_admin(request):
        return resp
    body = await request.json()
    content = str(body.get("content") or "").strip()
    if not content or len(content) > 4000:
        return JSONResponse({"error": "回复内容为空或超长"}, status_code=400)
    conv = database.execute(
        "SELECT status FROM conversations WHERE id = ?", (conversation_id,), fetch="one"
    )
    if conv is None:
        return JSONResponse({"error": "会话不存在"}, status_code=404)
    if conv["status"] not in ("human_pending", "human_active"):
        return JSONResponse({"error": "会话不在人工服务状态"}, status_code=409)
    ts = database.now()
    result = database.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?,?,?,?)",
        (conversation_id, "human_agent", content, ts),
    )
    database.execute(
        "UPDATE conversations SET status = 'human_active', updated_at = ? WHERE id = ?",
        (ts, conversation_id),
    )
    return {"messageId": result["lastrowid"]}


@router.post("/conversations/{conversation_id}/resolve")
async def resolve(conversation_id: str, request: Request):
    """人工处理完毕，交还机器人。"""
    if resp := _require_admin(request):
        return resp
    result = database.execute(
        "UPDATE conversations SET status = 'bot', unresolved_rounds = 0, updated_at = ? WHERE id = ? AND status IN ('human_pending','human_active')",
        (database.now(), conversation_id),
    )
    if result["rowcount"] == 0:
        return JSONResponse({"error": "会话不存在或不在人工服务状态"}, status_code=409)
    return {"ok": True}


# ---------- 满意度统计 ----------

@router.get("/stats")
async def stats(request: Request):
    if resp := _require_admin(request):
        return resp
    total_conv = database.execute("SELECT COUNT(*) AS c FROM conversations", fetch="one")["c"]
    total_msg = database.execute("SELECT COUNT(*) AS c FROM messages", fetch="one")["c"]
    transferred = database.execute(
        "SELECT COUNT(*) AS c FROM conversations WHERE intent = 'refund' OR status IN ('human_pending','human_active')",
        fetch="one",
    )["c"]
    fb = database.execute("SELECT rating, COUNT(*) AS c FROM feedback GROUP BY rating", fetch="all")
    total_fb = database.execute("SELECT COUNT(*) AS c, AVG(rating) AS a FROM feedback", fetch="one")
    distribution = {str(i): 0 for i in range(1, 6)}
    for row in fb:
        distribution[str(row["rating"])] = row["c"]
    intents = database.execute(
        "SELECT intent, COUNT(*) AS c FROM conversations WHERE intent IS NOT NULL GROUP BY intent",
        fetch="all",
    )
    return {
        "totalConversations": total_conv,
        "totalMessages": total_msg,
        "transferredConversations": transferred,
        "feedback": {
            "count": total_fb["c"] or 0,
            "avgRating": round(total_fb["a"], 2) if total_fb["a"] is not None else None,
            "distribution": distribution,
        },
        "intentDistribution": {r["intent"]: r["c"] for r in intents},
        "intentLabels": agent.INTENT_LABELS,
    }
