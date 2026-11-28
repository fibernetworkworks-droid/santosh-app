"""v0.999.38 SOCIAL DESK - the Social Media Manager's own tool (its chat, a call started from it, any chat of hers).

Before this the Social Media Manager had screens and 24/7 jobs but no tool: its chat could talk about the desk and change
nothing. `social_desk` reads the desk and edits what is still a draft: a post's caption / hook / hashtags / time / where it
goes, a reply draft in the inbox, and starts the desk's own runs (refresh numbers, rewrite the calendar draft, check the
inbox). It NEVER posts, sends a reply, approves a post, hides a comment or starts an ad: those stay her taps on the desk
(the house gate: a 'yes' in words never puts anything live - v0.999.12). An edit to an approved post sends it back to
draft, so it needs her OK again (social.desk.set_post's own rule).
"""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SOCIALDESK_TOOLS = [
    {"name": "social_desk", "description": (
        "HER Social Media Manager desk (Instagram, Facebook Page, WhatsApp Business, LinkedIn, YouTube) - only when she has "
        "hired it. action=read: what=summary (accounts, numbers, strategy, posts waiting, inbox counts, best times) | calendar "
        "(every planned post with its id) | inbox (box needs|leads|complaints|done: comments and DMs with their drafted "
        "replies and ids) | growth (competitors, hashtags, customers tagging her, hook styles). action=edit_post: post_id + "
        "any of caption, hook, hashtags [..], slot (YYYY-MM-DDTHH:MM, India time), platforms [instagram|facebook|linkedin|"
        "youtube], status draft|skipped -> changes a planned post; an approved post goes back to draft and needs her OK "
        "again. action=draft_reply: item_id, text -> rewrites the drafted reply to a comment / DM (it is NOT sent). "
        "action=ignore: item_id -> no reply needed. action=run: job daily (refresh numbers) | plan (rewrite the calendar "
        "draft; approved posts stay) | inbox (read new comments + DMs now) | growth (competitors, hashtags, tags) | monthly "
        "(this month's PDF). It cannot post, send a reply, approve a post or start an ad: tell her to tap OK / Send / "
        "Publish now / Start on her Social desk. Use only facts from her profile - never invent prices or offers."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["read", "edit_post", "draft_reply", "ignore", "run"]},
         "what": {"type": "string", "enum": ["summary", "calendar", "inbox", "growth"]},
         "box": {"type": "string", "enum": ["needs", "leads", "complaints", "done"]},
         "post_id": {"type": "string"}, "item_id": {"type": "string"},
         "caption": {"type": "string"}, "hook": {"type": "string"}, "text": {"type": "string"},
         "hashtags": {"type": "array", "items": {"type": "string"}},
         "platforms": {"type": "array", "items": {"type": "string"}},
         "slot": {"type": "string"}, "status": {"type": "string", "enum": ["draft", "skipped"]},
         "job": {"type": "string", "enum": ["daily", "plan", "inbox", "growth", "monthly"]}},
         "required": ["action"]}},
]
SOCIALDESK_LABELS = {"social_desk": "Working on your social media desk"}

RUN_JOBS = ("daily", "plan", "inbox", "growth", "monthly")


def _cut(s: Any, n: int = 400) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[:n - 1] + "…"


def summary(tenant: str) -> dict[str, Any]:
    from ..social import desk as D
    d = D.desk_view(tenant)
    if not d.get("hired"):
        return {"hired": False, "say": "The Social Media Manager is not hired. She can hire it from AI Employees."}
    cal = d.get("calendar") or []
    pl = d.get("pulse") or {}
    stg = d.get("strategy") or {}
    return {
        "hired": True, "onboarded": d.get("onboarded"), "status": d.get("status"), "state": d.get("state"), "trust": d.get("trust"),
        "business": (d.get("profile") or {}).get("business", ""), "facts": _cut((d.get("profile") or {}).get("facts", ""), 800),
        "accounts": [{"platform": a.get("platform"), "handle": a.get("handle") or a.get("name"), "status": a.get("status"),
                      "followers": a.get("followers")} for a in d.get("accounts") or []],
        "numbers": [{"name": k.get("name"), "now": k.get("now"), "was": k.get("baseline"), "change_pct": k.get("change_pct")}
                    for k in d.get("kpis") or []],
        "strategy": {"judged_on": stg.get("goal_metric"), "pillars": [p.get("name") for p in stg.get("pillars") or []],
                     "rhythm": stg.get("rhythm"), "best_hours": stg.get("best_hours")},
        "calendar_status": d.get("calendar_status"),
        "posts": {"total": len(cal), "drafts": sum(p["status"] == "draft" for p in cal),
                  "approved": sum(p["status"] == "approved" for p in cal),
                  "posted": sum(p["status"] == "published" for p in cal)},
        "waiting_ok_today": [{"id": p.get("id"), "hook": p.get("hook")} for p in pl.get("waiting_ok") or []][:6],
        "posting_paused": bool((pl.get("settings") or {}).get("paused")),
        "best_times": ((pl.get("best_times") or {}).get("slots") or [])[:4],
        "worth_a_boost": pl.get("boosts") or [],
        "inbox": d.get("inbox") or {},
        "recent": [f"{e.get('at', '')[:10]} {e.get('text', '')}" for e in (d.get("events") or [])[:6]],
    }


def _calendar(tenant: str) -> dict[str, Any]:
    from ..social import desk as D
    return {"posts": [{"id": p["id"], "when": p["slot"], "format": p["format"], "where": p["platforms"], "status": p["status"],
                       "hook": p["hook"], "caption": _cut(p["caption"], 500), "hashtags": p["hashtags"][:15],
                       "pillar": p["pillar"], "occasion": p["occasion"], "problems": p["problems"]}
                      for p in D.calendar(tenant)][:60]}


def _inbox(tenant: str, box: str) -> dict[str, Any]:
    from ..social import inbox as I
    v = I.view(tenant, box if box in ("needs", "leads", "complaints", "done") else "needs", limit=30)
    return {"box": v["box"], "counts": v["counts"],
            "items": [{"id": m["id"], "where": f"{m['platform']} {m['kind']}", "from": m["author"], "text": _cut(m["text"], 300),
                       "kind": m["cls"], "status": m["status"], "draft": m["draft"], "needs_her": m["needs_her"],
                       "dm_closed": m["dm_closed"]} for m in v["items"]]}


def _growth(tenant: str) -> dict[str, Any]:
    from ..social import desk as D
    return D.desk_view(tenant).get("growth") or {}


def _do(ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
    from ..employee import hire
    from ..social import desk as D
    from ..social.desk import SocialError
    t = ctx.tenant_id
    if not hire.is_hired(t, D.KEY):
        raise ToolError("The Social Media Manager is not hired. She can hire it from AI Employees.")
    act = str(a.get("action") or "")
    try:
        if act == "read":
            what = str(a.get("what") or "summary")
            if what == "calendar":
                return _calendar(t)
            if what == "inbox":
                return _inbox(t, str(a.get("box") or "needs"))
            if what == "growth":
                return _growth(t)
            return summary(t)
        if ctx.actor not in ("owner",) and not str(ctx.actor).startswith("approved:"):
            raise ToolError("Only the owner can change the Social desk.")
        if act == "edit_post":
            st = str(a.get("status") or "")
            if st not in ("", "draft", "skipped"):        # her OK is her tap on the desk, never the chat's
                raise ToolError("The chat cannot approve or post. She taps OK / Publish now on the Social desk.")
            pid = str(a.get("post_id") or "")
            if not pid:
                raise ToolError("post_id is needed (read what=calendar for the ids).")
            r = D.set_post(t, pid, status=st, caption=a.get("caption"), hook=a.get("hook"),
                           slot=a.get("slot") or None,
                           hashtags=a.get("hashtags") if isinstance(a.get("hashtags"), list) else None,
                           platforms=a.get("platforms") if isinstance(a.get("platforms"), list) else None)
            return {**r, "note": "Changed in the calendar. It goes out only after her OK on the Social desk."}
        if act == "draft_reply":
            from ..social import inbox as I
            iid, text = str(a.get("item_id") or ""), str(a.get("text") or "").strip()
            if not iid or not text:
                raise ToolError("item_id and text are needed.")
            r = I.set_item(t, iid, draft=text)
            return {**r, "note": "Draft saved, NOT sent. She taps Send reply in the Social desk inbox."}
        if act == "ignore":
            from ..social import inbox as I
            return I.set_item(t, str(a.get("item_id") or ""), status="ignored")
        if act == "run":
            job = str(a.get("job") or "")
            if job not in RUN_JOBS:
                raise ToolError("job: " + " | ".join(RUN_JOBS))
            if not D.accounts(t):
                raise ToolError("First connect Instagram or a Facebook Page on the Social desk.")
            import threading
            threading.Thread(target=lambda: D.run_now(t, job), daemon=True).start()
            return {"started": job, "note": "Running in the background; the desk updates by itself."}
    except SocialError as e:
        raise ToolError(str(e)) from e
    raise ToolError("action: read | edit_post | draft_reply | ignore | run")


async def social_desk(ctx: Ctx, **args: Any) -> dict[str, Any]:
    out = await asyncio.to_thread(_do, ctx, dict(args))
    try:
        from .. import socialchat
        socialchat.forget(ctx.tenant_id)
    except Exception:   # noqa: BLE001
        pass
    return out


SOCIALDESK_HANDLERS = {"social_desk": social_desk}
