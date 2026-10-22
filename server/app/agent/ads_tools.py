"""v0.111 Ads Sahayak tools (performance marketer). `ads` reads reports, plans changes, writes copies; `ads_dekho` only
reads. Budget / pause / resume changes are only PROPOSED: they happen on her tap in the app, never from here."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

ADS_TOOLS = [
    {"name": "ads", "description": (
        "Performance marketer for HER ads (Meta / Facebook / Instagram, Google Ads). "
        "action=import: file_id of the ad report she sent (Ads Manager / Google Ads export CSV or Excel; platform meta|google "
        "guessed) -> numbers + money leaks. action=fetch: pull the last N days from her joined Meta ad account (days). "
        "action=plan: concrete changes from the leaks (pause losers, cut ~20 %, raise winners ~20 % with the money saved; "
        "extra = more daily rupees she said she will add) -> a card; NOTHING changes until she taps Haan in the app (never "
        "say a change was made). action=done: change (number / id) she did herself in Ads Manager. action=copies: brief "
        "(offer in her words), platform meta|google, campaign, n, lang, landing -> ad copies to TEST (limits + claim checks); "
        "she puts them live herself. action=live: test (+ labels) she started. action=result: test + results {A: "
        "{impressions, clicks, results, spend}, ...} (or none: taken from imported ads named with the test number) -> winner "
        "only when the difference is real. action=sale: campaign, count, value, day (her real sales -> true cost per sale). "
        "action=settings (owner only): business, segment (real_estate | education | clinic | finance | ecommerce | "
        "home_services | isp | local | general), offer, target_cpl, target_roas, avg_order, margin_pct, close_pct, "
        "month_budget, max_step_pct, report_day (0 = Monday), report_time, rules. Meta is joined only in the app (Niyam > "
        "Meta: account id + token); never ask for a token in chat. action=meta_forget (owner only)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["import", "fetch", "plan", "done", "copies", "live", "result", "sale", "settings",
                                               "meta_forget"]},
         "file_id": {"type": "string"}, "platform": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
         "days": {"type": "integer"}, "extra": {"type": "number"}, "change": {"type": "string"}, "brief": {"type": "string"},
         "campaign": {"type": "string"}, "n": {"type": "integer"}, "lang": {"type": "string"}, "landing": {"type": "string"},
         "test": {"type": "string"}, "labels": {"type": "array", "items": {"type": "string"}},
         "results": {"type": "object"}, "count": {"type": "integer"}, "value": {"type": "number"}, "day": {"type": "string"},
         "note": {"type": "string"}, "business": {"type": "string"}, "segment": {"type": "string"}, "offer": {"type": "string"},
         "target_cpl": {"type": "number"}, "target_roas": {"type": "number"}, "avg_order": {"type": "number"},
         "margin_pct": {"type": "number"}, "close_pct": {"type": "number"}, "month_budget": {"type": "number"},
         "max_step_pct": {"type": "integer"}, "report_day": {"type": "integer"}, "report_time": {"type": "string"},
         "rules": {"type": "array", "items": {"type": "string"}}},
         "required": ["action"]}},
    {"name": "ads_dekho", "description": (
        "Read her ads work (nothing changes). what=report (days, platform: spend, results, cost per result vs her target, "
        "leaks with rupees, winners, notes, true cost per sale) | leaks | changes (status waiting|applied|manual|done|rejected) "
        "| tests | settings | benchmarks (India 2025 guide numbers, an estimate only)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["report", "leaks", "changes", "tests", "settings", "benchmarks"]},
         "days": {"type": "integer"}, "platform": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
ADS_LABELS = {"ads": "Ads ka hisaab dekh raha hoon", "ads_dekho": "Ads report dekh raha hoon"}
_OWNER_ONLY = {"settings", "meta_forget"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..ads import service as A
    actor = getattr(ctx, "actor", "owner") or "owner"
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action in _OWNER_ONLY and actor != "owner" and not actor.startswith("approved:"):
            raise ToolError("Yeh sirf owner kar sakti hain.")
        if action == "import":
            r = A.import_report(t, _s(a.get("file_id")), platform=_s(a.get("platform")), start=_s(a.get("start")),
                                end=_s(a.get("end")), conv=conv)
            return r | {"report": _short(r["report"])}
        if action == "fetch":
            r = A.fetch_meta(t, int(a.get("days") or 14), conv)
            return r | {"report": _short(r["report"])}
        if action == "plan":
            r = A.make_plan(t, int(a.get("days") or 14), conv, float(a.get("extra") or 0))
            return r | {"note": "Card sent. She decides each change in the app; nothing is applied from chat."}
        if action == "done":
            ref = _s(a.get("change"))
            cid = _change_id(t, ref)
            return A.mark_done(t, cid)
        if action == "copies":
            return A.write_copies(t, _s(a.get("brief")), _s(a.get("platform")) or "meta", _s(a.get("campaign")),
                                  int(a.get("n") or 4), _s(a.get("lang")), _s(a.get("landing")), conv)
        if action == "live":
            return A.test_live(t, _s(a.get("test")), a.get("labels"))
        if action == "result":
            return A.test_result(t, _s(a.get("test")), a.get("results") if isinstance(a.get("results"), dict) else None)
        if action == "sale":
            return A.add_sale(t, _s(a.get("campaign")), int(a.get("count") or 1), float(a.get("value") or 0), _s(a.get("day")),
                              _s(a.get("platform")), _s(a.get("note")))
        if action == "settings":
            keys = ("business", "segment", "offer", "target_cpl", "target_roas", "avg_order", "margin_pct", "close_pct",
                    "month_budget", "max_step_pct", "report_day", "report_time", "rules")
            return {"settings": A.save_settings(t, **{k: a[k] for k in keys if k in a}), "say": "Save."}
        if action == "meta_forget":
            return A.forget_meta(t)
    except A.AdsError as e:
        raise ToolError(str(e))
    raise ToolError("action = import | fetch | plan | done | copies | live | result | sale | settings | meta_forget")


def _change_id(tenant: str, ref: str) -> str:
    from ..ads import service as A
    for c in A.changes(tenant, limit=200):
        if ref and (c["id"] == ref or c["number"].lower() == ref.lower()):
            return c["id"]
    raise ToolError(f"Badlav '{ref}' nahi mila.")


def _short(rep: dict) -> dict:
    if rep.get("empty"):
        return rep
    return {k: rep.get(k) for k in ("from", "to", "total", "target", "target_from", "max_cpl", "waste", "notes", "money", "say")} | {
        "leaks": [{k: l.get(k) for k in ("kind", "name", "campaign", "platform", "waste", "text", "fix")} for l in rep["leaks"][:12]],
        "winners": rep["winners"][:6]}


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..ads import rules as R
    from ..ads import service as A
    t = ctx.tenant_id
    try:
        if what in ("report", "leaks"):
            rep = A.analyse(t, int(a.get("days") or 30), _s(a.get("platform")))
            if what == "leaks" and not rep.get("empty"):
                return {"leaks": _short(rep)["leaks"], "waste": rep["waste"], "say": rep["say"]}
            return _short(rep)
        if what == "changes":
            return {"changes": A.changes(t, _s(a.get("status")))}
        if what == "tests":
            return {"tests": A.tests(t)}
        if what == "settings":
            return A.settings(t)
        if what == "benchmarks":
            return {"segments": R.SEGMENTS, "note": R.BENCH_NOTE, "learning_events": R.LEARNING_EVENTS,
                    "budget_step_pct": R.MAX_STEP_PCT, "limits": R.LIMITS}
    except A.AdsError as e:
        raise ToolError(str(e))
    raise ToolError("what = report | leaks | changes | tests | settings | benchmarks")


async def ads(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def ads_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


ADS_HANDLERS = {"ads": ads, "ads_dekho": ads_dekho}
