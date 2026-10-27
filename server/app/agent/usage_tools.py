"""v0.98 Tool `ai_kharcha`: what Hoola's AI has cost this month, where it went, and her monthly limit (chat + calls)."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

USAGE_TOOLS = [
    {"name": "ai_kharcha", "description": (
        "Hoola's own AI cost for her (Claude, Gemini, voice-call minutes, AI video): action=report (this month so far in ₹, "
        "the limit, % used, end-of-month estimate, which features cost most, days=7|30) or action=limit (set her monthly "
        "limit in rupees, limit_inr; 0 = no limit; only she can set it). Use for 'kitna kharcha hua', 'AI ka bill', "
        "'seema rakho ₹2000'. Read the numbers in one or two lines; they are estimates from official price lists."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["report", "limit"]},
         "days": {"type": "integer"},
         "limit_inr": {"type": "number"}},
         "required": ["action"]}},
]
USAGE_LABELS = {"ai_kharcha": "AI ka kharcha dekh raha hoon"}


async def ai_kharcha(ctx: Ctx, action, days: int = 30, limit_inr=None, **_):
    from .. import usage
    if action == "limit":
        if (getattr(ctx, "actor", "owner") or "owner") != "owner":
            raise ToolError("Kharche ki seema sirf owner badal sakti hain.")
        if limit_inr is None or float(limit_inr) < 0:
            raise ToolError("limit_inr dijiye (rupaye mein; 0 = koi seema nahi).")
        r = await asyncio.to_thread(usage.set_limit, ctx.tenant_id, None, float(limit_inr))
    else:
        r = await asyncio.to_thread(usage.report, ctx.tenant_id, int(days or 30))
    m = r["month"]
    return {"say": r["say"], "month_spent_inr": m["spent_inr"], "limit_inr": m["limit_inr"], "pct": m["pct"],
            "projected_inr": m["projected_inr"], "top": [{k: f[k] for k in ("label", "inr", "share")} for f in r["features"][:4]],
            "note": r["note"]}


USAGE_HANDLERS = {"ai_kharcha": ai_kharcha}
