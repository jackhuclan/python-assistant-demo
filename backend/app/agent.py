"""Agent 编排层：意图识别 → FAQ 检索 → 回答生成 → 转人工判定。"""
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field

from . import config, database, llm

INTENTS = ("refund", "order_query", "tech_support", "general")

INTENT_LABELS = {
    "refund": "退款",
    "order_query": "查询订单",
    "tech_support": "技术支持",
    "general": "一般咨询",
}

INTENT_RULES = {
    "refund": ("退款", "退钱", "退货", "退单", "退费", "返现", "给我退"),
    "order_query": ("订单", "物流", "发货", "快递", "收货", "签收", "我的单"),
    "tech_support": ("报错", "故障", "崩溃", "无法登录", "登录不上", "闪退", "bug", "安装", "异常", "坏了", "用不了"),
}

TRANSFER_WORDS = ("转人工", "人工客服", "真人客服", "找人工", "人工服务")

SYSTEM_PROMPT = (
    "你是一名专业的智能客服助手。请根据 FAQ 知识库内容和对话历史，用简洁、友好、专业的中文回答用户问题。"
    "规则：1. 优先依据 FAQ 内容回答，不要编造事实；2. 如果 FAQ 和历史信息不足以解决问题，"
    "请如实告知并建议用户回复「转人工」；3. 回答控制在 200 字以内。"
)


# ---------- 意图识别 ----------

def rule_intent(text: str) -> str | None:
    """关键词规则兜底：LLM 不可用时使用。"""
    if any(w in text for w in TRANSFER_WORDS):
        return None  # 转人工单独处理，不算意图
    scores = {name: sum(1 for w in words if w in text) for name, words in INTENT_RULES.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "general"


async def detect_intent(text: str) -> tuple[str, float]:
    """返回 (intent, confidence)。LLM 失败时降级为规则识别。"""
    try:
        raw = await llm.chat_once(
            [
                {
                    "role": "system",
                    "content": (
                        "你是意图分类器。将用户消息分类为以下意图之一："
                        "refund(退款/退货)、order_query(查询订单/物流)、tech_support(技术问题/报错)、"
                        "general(其他咨询/闲聊)。只输出 JSON：{\"intent\":\"...\",\"confidence\":0到1的小数}"
                    ),
                },
                {"role": "user", "content": text[:500]},
            ],
            temperature=0.1,
            max_tokens=512,
        )
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            intent = data.get("intent", "general")
            if intent not in INTENTS:
                intent = "general"
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.8))))
            return intent, confidence
    except (llm.LLMError, ValueError, TypeError):
        pass
    return rule_intent(text) or "general", 0.6


# ---------- FAQ 检索（纯 Python 字符 bigram 余弦相似度）----------

def _bigrams(text: str) -> Counter:
    cleaned = re.sub(r"[\s\W]+", "", text.lower())
    return Counter(cleaned[i : i + 2] for i in range(len(cleaned) - 1)) if len(cleaned) > 1 else Counter([cleaned])


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    return dot / (math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values())))


@dataclass
class FaqHit:
    id: int
    question: str
    answer: str
    score: float


def search_faqs(query: str, top_k: int = 3) -> list[FaqHit]:
    rows = database.execute(
        "SELECT id, question, answer, keywords FROM faqs WHERE enabled = 1", fetch="all"
    )
    q_bigrams = _bigrams(query)
    hits: list[FaqHit] = []
    for row in rows:
        score = _cosine(q_bigrams, _bigrams(row["question"]))
        for kw in (row["keywords"] or "").split(","):
            kw = kw.strip()
            if kw and kw in query:
                score += 0.35  # 关键词命中加权
        hits.append(FaqHit(id=row["id"], question=row["question"], answer=row["answer"], score=min(score, 1.0)))
    hits.sort(key=lambda h: h.score, reverse=True)
    return [h for h in hits[:top_k] if h.score >= config.FAQ_HIT_THRESHOLD]


# ---------- 转人工判定 ----------

def wants_human(text: str) -> bool:
    return any(w in text for w in TRANSFER_WORDS)


def should_transfer(intent: str, confidence: float, hits: list[FaqHit], unresolved_rounds: int) -> bool:
    if intent == "refund":
        return True
    if confidence < config.INTENT_CONFIDENCE_THRESHOLD:
        return True
    if not hits and intent in ("order_query", "tech_support"):
        return unresolved_rounds + 1 >= config.UNRESOLVED_ROUNDS_TO_TRANSFER
    return False


# ---------- 提示词构建 ----------

@dataclass
class AgentContext:
    intent: str = "general"
    confidence: float = 0.0
    faq_hits: list[FaqHit] = field(default_factory=list)
    transfer: bool = False


def build_chat_messages(history: list[dict], user_text: str, ctx: AgentContext) -> list[dict]:
    """history: [{role, content}]（不含当前消息），近 N 轮。"""
    faq_block = (
        "\n\n".join(f"[FAQ{i+1}] 问：{h.question}\n答：{h.answer}" for i, h in enumerate(ctx.faq_hits))
        or "（无命中的 FAQ）"
    )
    system = (
        f"{SYSTEM_PROMPT}\n\n当前识别意图：{INTENT_LABELS.get(ctx.intent, ctx.intent)}（置信度 {ctx.confidence:.2f}）\n"
        f"FAQ 知识库检索结果：\n{faq_block}"
    )
    trimmed = history[-config.MAX_HISTORY_TURNS * 2 :]
    return [{"role": "system", "content": system}, *trimmed, {"role": "user", "content": user_text}]
