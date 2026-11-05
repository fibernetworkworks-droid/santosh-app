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
        "month_budget, max_step_pct, report_day (0 = Monday), report_time, rules. Meta is joined only in the app (Ads desk > "
        "'Connect with Facebook', one tap); never ask for a token in chat. action=meta_forget (owner only). "
        "action=meta_draft (owner only): a NEW Facebook / Instagram ad as a draft in Hoola - goal whatsapp (chats on her "
        "WhatsApp) | messenger | instagram (DMs) | website (link) | boost (post_id of her Page post), text, headline, "
        "description, cities (names, else all India), radius_km, age_min, age_max, gender all|men|women, platforms "
        "both|facebook|instagram, daily (her currency a day), days. Nothing reaches Meta: she adds the photo, checks, "
        "creates it PAUSED and taps Start herself in the app (Social Desk > Facebook & Instagram ads); say that. "
        "action=google_draft (owner only): a NEW Google ad draft in Hoola - kind search (keywords = what people type on "
        "Google, negatives, headlines up to 15 x 30 letters, descriptions 2-4 x 90, link, cities) | pmax (Performance Max "
        "over Search / YouTube / Maps / Gmail: headlines 3-5 x 30, long_headline, descriptions, link, cities; she adds "
        "photos + logo in the app) | youtube (video_id); daily, days. Nothing reaches Google: she checks, creates it "
        "PAUSED and taps Start in the app (Social Desk > Google ads). action=google_ideas: seeds (words) and/or link, "
        "cities -> Google Keyword Planner ideas (monthly searches, competition, bid range), read-only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["import", "fetch", "plan", "done", "copies", "live", "result", "sale", "settings",
                                               "meta_forget", "meta_draft", "google_draft", "google_ideas"]},
         "file_id": {"type": "string"}, "platform": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
         "days": {"type": "integer"}, "extra": {"type": "number"}, "change": {"type": "string"}, "brief": {"type": "string"},
         "campaign": {"type": "string"}, "n": {"type": "integer"}, "lang": {"type": "string"}, "landing": {"type": "string"},
         "test": {"type": "string"}, "labels": {"type": "array", "items": {"type": "string"}},
         "results": {"type": "object"}, "count": {"type": "integer"}, "value": {"type": "number"}, "day": {"type": "string"},
         "note": {"type": "string"}, "business": {"type": "string"}, "segment": {"type": "string"}, "offer": {"type": "string"},
         "target_cpl": {"type": "number"}, "target_roas": {"type": "number"}, "avg_order": {"type": "number"},
         "margin_pct": {"type": "number"}, "close_pct": {"type": "number"}, "month_budget": {"type": "number"},
         "max_step_pct": {"type": "integer"}, "report_day": {"type": "integer"}, "report_time": {"type": "string"},
         "rules": {"type": "array", "items": {"type": "string"}},
         "goal": {"type": "string", "enum": ["whatsapp", "messenger", "instagram", "website", "boost"]},
         "text": {"type": "string"}, "headline": {"type": "string"}, "description": {"type": "string"},
         "link": {"type": "string"}, "post_id": {"type": "string"}, "cities": {"type": "array", "items": {"type": "string"}},
         "radius_km": {"type": "integer"}, "age_min": {"type": "integer"}, "age_max": {"type": "integer"},
         "gender": {"type": "string"}, "platforms": {"type": "string"}, "daily": {"type": "integer"},
         "kind": {"type": "string", "enum": ["search", "pmax", "youtube"]}, "keywords": {"type": "array", "items": {"type": "string"}},
         "negatives": {"type": "array", "items": {"type": "string"}}, "headlines": {"type": "array", "items": {"type": "string"}},
         "descriptions": {"type": "array", "items": {"type": "string"}}, "long_headline": {"type": "string"},
         "video_id": {"type": "string"}, "seeds": {"type": "array", "items": {"type": "string"}}},
         "required": ["action"]}},
    {"name": "ads_dekho", "description": (
        "Read her ads work (nothing changes). what=report (days, platform: spend, results, cost per result vs her target, "
        "leaks with rupees, winners, notes, true cost per sale) | leaks | changes (status waiting|applied|manual|done|rejected) "
        "| tests | settings | benchmarks (India 2025 guide numbers, an estimate only) | meta_ads (her Facebook / Instagram ad "
        "drafts and their status: draft, checked, created = in Meta paused, running, paused, ended)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["report", "leaks", "changes", "tests", "settings", "benchmarks", "meta_ads"]},
         "days": {"type": "integer"}, "platform": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
ADS_LABELS = {"ads": "Ads ka hisaab dekh raha hoon", "ads_dekho": "Ads report dekh raha hoon"}
_OWNER_ONLY = {"settings", "meta_forget", "meta_draft", "google_draft"}


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
        if action == "meta_draft":
            from ..ads import metaads as M
            keys = ("text", "headline", "description", "link", "post_id", "cities", "radius_km", "age_min", "age_max",
                    "gender", "platforms", "daily", "days")
            try:
                d = M.new_draft(t, _s(a.get("goal")) or "whatsapp", **{k: a[k] for k in keys if a.get(k) is not None})
            except M.MetaAdsError as e:
                raise ToolError(str(e))
            return {"draft": d, "say": "Draft Hoola mein bana - Meta mein abhi kuch nahi gaya. App mein Social Desk > Facebook & "
                    "Instagram ads par photo jodiye, 'Check with Meta', phir 'Create (paused)' aur Start - sab aapke tap par."}
        if action in ("google_draft", "google_ideas"):
            from ..ads import gads as G
            try:
                if action == "google_ideas":
                    return G.keyword_ideas(t, a.get("seeds") or a.get("keywords") or [], _s(a.get("link")),
                                           a.get("cities") or [], _s(a.get("lang")) or "en")
                keys = ("headlines", "descriptions", "long_headline", "keywords", "negatives", "cities", "daily", "days")
                kw = {k: a[k] for k in keys if a.get(k) is not None}
                if a.get("link"):
                    kw["final_url"] = _s(a.get("link"))
                d = G.new_draft(t, _s(a.get("video_id")), _s(a.get("kind")) or "search", **kw)
            except G.GAdsError as e:
                raise ToolError(str(e))
            return {"draft": d, "say": "Draft Hoola mein bana - Google mein abhi kuch nahi gaya. App mein Social Desk > Google ads "
                    "par dekhiye, 'Check with Google', phir 'Create (paused)' aur Start - sab aapke tap par."}
    except A.AdsError as e:
        raise ToolError(str(e))
    raise ToolError("action = import | fetch | plan | done | copies | live | result | sale | settings | meta_forget | meta_draft "
                    "| google_draft | google_ideas")


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
        if what == "meta_ads":
            from ..ads import metaads as M
            v = M.view(t)
            return {"linked": bool(v["account"]), "drafts": v["drafts"], "cap": v["cap"]}
        if what == "benchmarks":
            return {"segments": R.SEGMENTS, "note": R.BENCH_NOTE, "learning_events": R.LEARNING_EVENTS,
                    "budget_step_pct": R.MAX_STEP_PCT, "limits": R.LIMITS}
    except A.AdsError as e:
        raise ToolError(str(e))
    raise ToolError("what = report | leaks | changes | tests | settings | benchmarks | meta_ads")


async def ads(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def ads_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


ADS_HANDLERS = {"ads": ads, "ads_dekho": ads_dekho}
