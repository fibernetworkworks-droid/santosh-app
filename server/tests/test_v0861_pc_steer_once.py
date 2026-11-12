"""v0.861 PC EK BAAR: her 11:29 pizza run - the chat brain re-sent its own steps into the running PC task every
15-20 s, each one interrupting it. Hoola's words go in ONCE per ask of hers; a repeat waits and says do not repeat."""
import asyncio
import types

from app.agent import pc_tools
from app.agent.santosh import ASK_NOW
from app.pc import operator


def _op():
    op = operator.Op(id="pcop_once", tenant="t_once", conv="c_once", task="Swiggy pe biryani")
    op.task_obj = types.SimpleNamespace(done=lambda: False)
    operator.OPS[op.id] = op
    return op


def test_same_ask_passes_words_in_once():
    op = _op()
    ctx = types.SimpleNamespace(tenant_id="t_once", conversation_id="c_once")
    try:
        ASK_NOW.set("biryani order karo")
        r1 = asyncio.run(pc_tools.pc_do(ctx, "Step 3: address check karo", _wait=0))
        r2 = asyncio.run(pc_tools.pc_do(ctx, "Status check only", _wait=0))
        assert r1["steered"] and not r2["steered"]
        assert len(op.notes) == 1 and "Do NOT call pc_do again" in r2["say"]
        ASK_NOW.set("Cash on delivery karo")                  # her NEW words do go in
        r3 = asyncio.run(pc_tools.pc_do(ctx, "Cash on delivery chuno", _wait=0))
        assert r3["steered"] and len(op.notes) == 2
    finally:
        operator.OPS.pop(op.id, None)
        ASK_NOW.set("")


def test_round_without_her_words_is_rate_limited():
    op = _op()
    ctx = types.SimpleNamespace(tenant_id="t_once", conversation_id="c_once")
    try:
        ASK_NOW.set("")
        asyncio.run(pc_tools.pc_do(ctx, "Proceed to Pay dabao", _wait=0))
        r = asyncio.run(pc_tools.pc_do(ctx, "Report the screen", _wait=0))
        assert len(op.notes) == 1 and not r["steered"]
    finally:
        operator.OPS.pop(op.id, None)
