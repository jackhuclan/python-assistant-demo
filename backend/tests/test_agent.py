"""Agent 编排层单元测试（不依赖 LLM）。"""
from app import agent, database


def test_rule_intent_refund():
    assert agent.rule_intent("我要退款") == "refund"


def test_rule_intent_order():
    assert agent.rule_intent("帮我查一下订单发货了没") == "order_query"


def test_rule_intent_tech():
    assert agent.rule_intent("软件一直报错打不开") == "tech_support"


def test_rule_intent_general():
    assert agent.rule_intent("今天天气怎么样") == "general"


def test_wants_human():
    assert agent.wants_human("转人工")
    assert agent.wants_human("请帮我接通人工客服")
    assert not agent.wants_human("如何申请退款")


def test_search_faqs_seeded():
    hits = agent.search_faqs("如何退款")
    assert len(hits) > 0
    assert any("退款" in h.question or "退款" in h.answer for h in hits)


def test_search_faqs_no_hit():
    assert agent.search_faqs("量子力学薛定谔方程的边界条件是什么") == []


def test_should_transfer_refund():
    assert agent.should_transfer("refund", 0.9, [], 0)


def test_should_transfer_low_confidence():
    assert agent.should_transfer("general", 0.2, [agent.FaqHit(1, "q", "a", 0.8)], 0)


def test_should_transfer_unresolved():
    assert agent.should_transfer("tech_support", 0.9, [], 1)
    assert not agent.should_transfer("tech_support", 0.9, [agent.FaqHit(1, "q", "a", 0.9)], 0)


def test_build_chat_messages_contains_faq():
    ctx = agent.AgentContext(intent="order_query", confidence=0.8)
    ctx.faq_hits = [agent.FaqHit(1, "如何查询订单", "进入我的订单页面", 0.9)]
    msgs = agent.build_chat_messages([{"role": "user", "content": "你好"}], "查订单", ctx)
    assert msgs[0]["role"] == "system"
    assert "如何查询订单" in msgs[0]["content"]
    assert msgs[-1] == {"role": "user", "content": "查订单"}


def test_database_seeded():
    conn = database.get_conn()
    count = conn.execute("SELECT COUNT(*) AS c FROM faqs").fetchone()["c"]
    assert count >= 8
