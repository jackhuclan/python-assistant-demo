"""FAQ 管理 API（管理后台专用）。"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .. import auth, database

router = APIRouter(prefix="/api/faqs")


def _require_admin(request: Request) -> JSONResponse | None:
    if not auth.verify_token(request.cookies.get(auth.COOKIE_NAME)):
        return JSONResponse({"error": "未登录或登录已过期"}, status_code=401)
    return None


@router.get("")
async def list_faqs(request: Request):
    if resp := _require_admin(request):
        return resp
    rows = database.execute(
        "SELECT id, question, answer, keywords, enabled, created_at FROM faqs ORDER BY id DESC", fetch="all"
    )
    return {"faqs": [
        {"id": r["id"], "question": r["question"], "answer": r["answer"],
         "keywords": r["keywords"], "enabled": bool(r["enabled"]), "createdAt": r["created_at"]}
        for r in rows
    ]}


@router.post("")
async def create_faq(request: Request):
    if resp := _require_admin(request):
        return resp
    body = await request.json()
    question = str(body.get("question") or "").strip()
    answer = str(body.get("answer") or "").strip()
    if not question or not answer:
        return JSONResponse({"error": "问题和答案不能为空"}, status_code=400)
    keywords = str(body.get("keywords") or "").strip()
    enabled = 1 if body.get("enabled", True) else 0
    result = database.execute(
        "INSERT INTO faqs (question, answer, keywords, enabled, created_at) VALUES (?,?,?,?,?)",
        (question, answer, keywords, enabled, database.now()),
    )
    return {"id": result["lastrowid"]}


@router.put("/{faq_id}")
async def update_faq(faq_id: int, request: Request):
    if resp := _require_admin(request):
        return resp
    body = await request.json()
    row = database.execute("SELECT id FROM faqs WHERE id = ?", (faq_id,), fetch="one")
    if row is None:
        return JSONResponse({"error": "FAQ 不存在"}, status_code=404)
    fields, params = [], []
    for col, key in (("question", "question"), ("answer", "answer"), ("keywords", "keywords")):
        if key in body:
            fields.append(f"{col} = ?")
            params.append(str(body[key]).strip())
    if "enabled" in body:
        fields.append("enabled = ?")
        params.append(1 if body["enabled"] else 0)
    if not fields:
        return JSONResponse({"error": "没有需要更新的字段"}, status_code=400)
    params.append(faq_id)
    database.execute(f"UPDATE faqs SET {', '.join(fields)} WHERE id = ?", tuple(params))
    return {"ok": True}


@router.delete("/{faq_id}")
async def delete_faq(faq_id: int, request: Request):
    if resp := _require_admin(request):
        return resp
    result = database.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
    if result["rowcount"] == 0:
        return JSONResponse({"error": "FAQ 不存在"}, status_code=404)
    return {"ok": True}
