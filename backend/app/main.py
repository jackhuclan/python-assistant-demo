"""智能客服 Agent 后端入口。"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import database
from .routers import admin, chat, faq

app = FastAPI(title="智能客服 Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(faq.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup() -> None:
    database.get_conn()  # 初始化数据库与预置 FAQ


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---- 托管前端构建产物（frontend/dist），SPA 回退到 index.html ----
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return HTMLResponse("Not Found", status_code=404)
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
