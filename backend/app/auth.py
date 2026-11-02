"""管理后台鉴权：HMAC 签名令牌 + HttpOnly Cookie（不引入额外依赖）。"""
import hashlib
import hmac
import time

from . import config

COOKIE_NAME = "csa_token"


def _sign(payload: str) -> str:
    return hmac.new(config.JWT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token() -> str:
    exp = str(int(time.time()) + config.TOKEN_TTL_HOURS * 3600)
    return f"{exp}.{_sign(exp)}"


def verify_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    exp, sig = token.split(".", 1)
    if not exp.isdigit() or int(exp) < time.time():
        return False
    return hmac.compare_digest(sig, _sign(exp))
