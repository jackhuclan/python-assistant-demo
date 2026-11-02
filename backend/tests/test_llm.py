"""LLM 客户端健壮性测试：模拟含空 choices 块的流式响应。"""
import json

import pytest

from app import llm


class _FakeStream:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        pass

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeClient:
    """替身 AsyncClient：不发起真实网络请求。"""

    last_lines: list[str] = []

    def __init__(self, **kwargs):
        pass

    def stream(self, method, url, headers=None, json=None):
        return _FakeStream(_FakeClient.last_lines)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def _sse_lines(*chunks: dict) -> list[str]:
    lines = [f"data: {json.dumps(c, ensure_ascii=False)}" for c in chunks]
    lines.append("data: [DONE]")
    return lines


@pytest.mark.asyncio
async def test_chat_stream_skips_empty_choices(monkeypatch):
    """空 choices 块（如 usage 统计）不应导致 IndexError。"""
    _FakeClient.last_lines = _sse_lines(
        {"choices": [{"delta": {"role": "assistant", "content": ""}}]},
        {"choices": []},  # 触发过 IndexError 的块
        {"choices": [{"delta": {"content": "你好"}}]},
        {"choices": [{"delta": {"content": "！"}}]},
        {"choices": [], "usage": {"total_tokens": 10}},
    )
    monkeypatch.setattr(llm.httpx, "AsyncClient", _FakeClient)
    out = [delta async for delta in llm.chat_stream([{"role": "user", "content": "hi"}])]
    assert out == ["你好", "！"]


@pytest.mark.asyncio
async def test_chat_once_missing_choices(monkeypatch):
    """非流式响应缺少 choices 时应抛 LLMError 而非裸异常。"""
    _FakeClient.last_lines = []

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": []}

    class _Client2:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            return _Resp()

    monkeypatch.setattr(llm.httpx, "AsyncClient", _Client2)
    with pytest.raises(llm.LLMError):
        await llm.chat_once([{"role": "user", "content": "hi"}])
