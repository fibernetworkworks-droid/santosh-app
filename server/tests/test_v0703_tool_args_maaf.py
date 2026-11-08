"""v0.703 TOOL ARGS MAAF: her G8 run - kaam_plan step without `state` (x3) and email_draft without `to` (x2)
stalled a simple draft. A missing state now means done (with a note) / current; email_draft takes recipient
aliases and a missing `to` says exactly how to retry."""
import asyncio
import pytest


def test_kaam_plan_step_without_state_defaults(env):
    from app.agent import goal_tools as gt, goal as g
    from app.agent.tools import Ctx  # noqa
    ctx = Ctx(tenant_id="t1", conversation_id="c1")
    asyncio.run(gt.kaam_plan(ctx, action="set", goal="draft a mail", steps=["find contact", "write draft"]))
    v = asyncio.run(gt.kaam_plan(ctx, action="step", n=1, reason="contact mil gaya"))
    a = g.active_for("c1")
    assert a["steps"][0]["state"] == "done"
    asyncio.run(gt.kaam_plan(ctx, action="step", n=2))
    assert g.active_for("c1")["steps"][1]["state"] == "current"
    asyncio.run(gt.kaam_plan(ctx, action="step", n=2, state="completed"))
    assert g.active_for("c1")["steps"][1]["state"] == "done"


def test_email_draft_missing_to_hint():
    src = open("app/agent/email_tools.py").read()
    assert "call email_draft again with to=" in src
    assert '"recipient", "recipients", "to_email"' in src
