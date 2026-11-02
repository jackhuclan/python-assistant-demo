"""LLM 客户端：OpenAI 兼容接口（支持流式 / 非流式）。"""
import json
from collections.abc import AsyncIterator

import httpx

from . import config


class LLMError(Exception):
    """LLM 调用失败（网络/超时/接口错误）。"""


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.LLM_API_KEY}",
    }


async def chat_once(messages: list[dict], *, temperature: float = 0.6, max_tokens: int = 2048) -> str:
    """非流式调用，返回完整文本（用于意图识别等一次性任务）。"""
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
        "temperature": temperature,
    }
    try:
        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT) as client:
            resp = await client.post(
                f"{config.LLM_BASE_URL}/chat/completions", headers=_headers(), json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("LLM 返回缺少 choices")
        return ((choices[0].get("message") or {}).get("content") or "").strip()
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise LLMError(f"LLM 调用失败: {exc}") from exc


async def chat_stream(messages: list[dict], *, temperature: float = 0.6, max_tokens: int = 4096) -> AsyncIterator[str]:
    """流式调用，逐段 yield 文本增量。"""
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": temperature,
    }
    try:
        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT) as client:
            async with client.stream(
                "POST", f"{config.LLM_BASE_URL}/chat/completions", headers=_headers(), json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except ValueError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue  # 跳过 choices 为空的块（如 usage 统计块）
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM 流式调用失败: {exc}") from exc
