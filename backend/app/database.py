"""SQLite 持久化层：会话 / 消息 / FAQ / 满意度反馈。"""
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    visitor_id  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'bot',            -- bot/human_pending/human_active/closed
    intent      TEXT,
    unresolved_rounds INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,                       -- user/assistant/human_agent
    content         TEXT NOT NULL,
    intent          TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, id);
CREATE TABLE IF NOT EXISTS faqs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    question   TEXT NOT NULL,
    answer     TEXT NOT NULL,
    keywords   TEXT NOT NULL DEFAULT '',
    enabled    INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL UNIQUE,
    rating          INTEGER NOT NULL,                    -- 1~5
    comment         TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);
"""

SEED_FAQS = [
    ("如何申请退款？", "您可以在「我的订单」中选择对应订单发起退款申请，审核通过后 1-3 个工作日内原路退回。如需人工协助，请回复「转人工」。", "退款,退货,退钱,退费"),
    ("退款多久到账？", "退款审核通过后 1-3 个工作日原路退回，具体到账时间以支付渠道为准（支付宝/微信一般 24 小时内）。", "退款,到账,多久"),
    ("如何查询订单状态？", "进入「我的订单」页面即可查看全部订单及当前状态（待支付/已发货/已完成）。您也可以直接告诉我订单号，我帮您查询。", "订单,查询,物流,发货"),
    ("订单可以修改收货地址吗？", "订单发货前可以在订单详情页修改收货地址；已发货订单无法修改，可联系快递客服改派。", "地址,收货,修改,订单"),
    ("软件无法登录怎么办？", "请先尝试：1. 检查网络连接；2. 清除浏览器缓存后重试；3. 确认账号密码是否正确。若仍无法登录，请回复「转人工」或描述具体报错信息。", "登录,无法登录,报错,密码"),
    ("系统报错 code 500 是什么意思？", "code 500 表示服务端内部错误，通常是临时故障。请稍后重试；若持续出现，请截图报错页面并转人工反馈给技术支持。", "报错,500,错误,故障"),
    ("如何联系人工客服？", "直接在对话框输入「转人工」即可转接人工客服，工作时间为 9:00-18:00。", "人工,客服,转人工"),
    ("支持哪些支付方式？", "目前支持微信支付、支付宝和银联银行卡支付。", "支付,付款,微信,支付宝"),
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def new_id() -> str:
    return uuid.uuid4().hex


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(SCHEMA)
        _conn.commit()
        _seed_faqs()
    return _conn


def _seed_faqs() -> None:
    row = _conn.execute("SELECT COUNT(*) AS c FROM faqs").fetchone()
    if row and row["c"] == 0:
        ts = now()
        _conn.executemany(
            "INSERT INTO faqs (question, answer, keywords, enabled, created_at) VALUES (?,?,?,1,?)",
            [(q, a, k, ts) for q, a, k in SEED_FAQS],
        )
        _conn.commit()


def execute(sql: str, params: tuple = (), *, fetch: str | None = None):
    with _lock:
        conn = get_conn()
        cur = conn.execute(sql, params)
        if fetch is None:
            conn.commit()
            return {"lastrowid": cur.lastrowid, "rowcount": cur.rowcount}
        if fetch == "one":
            return cur.fetchone()
        return cur.fetchall()
