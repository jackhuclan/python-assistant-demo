"""应用配置：全部敏感信息走环境变量或 .env 文件，不写入代码。"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """极简 .env 加载器（KEY=VALUE，支持注释），避免额外依赖。"""
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()

# ---- LLM（OpenAI 兼容接口）----
LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "http://192.168.3.184:3001/v1")
LLM_API_KEY: str = os.environ.get("LLM_API_KEY", "")
LLM_MODEL: str = os.environ.get("LLM_MODEL", "deepseek-v4.1-flash")
LLM_TIMEOUT: float = float(os.environ.get("LLM_TIMEOUT", "60"))

# ---- 管理后台 ----
ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "admin123")
JWT_SECRET: str = os.environ.get("JWT_SECRET", "csa-change-me-in-production")
TOKEN_TTL_HOURS: int = int(os.environ.get("TOKEN_TTL_HOURS", "24"))

# ---- 数据库 ----
DB_PATH: str = os.environ.get("DB_PATH", str(BACKEND_DIR / "data" / "csa.db"))

# ---- Agent 策略 ----
FAQ_HIT_THRESHOLD: float = float(os.environ.get("FAQ_HIT_THRESHOLD", "0.25"))
INTENT_CONFIDENCE_THRESHOLD: float = float(os.environ.get("INTENT_CONFIDENCE_THRESHOLD", "0.4"))
MAX_HISTORY_TURNS: int = int(os.environ.get("MAX_HISTORY_TURNS", "10"))
UNRESOLVED_ROUNDS_TO_TRANSFER: int = int(os.environ.get("UNRESOLVED_ROUNDS_TO_TRANSFER", "2"))
