"""v0.648 KAAM KA HISAAB: one honest list of her work, running and finished, for every surface.

Owner (7 Nov 2026) after the work audit: "FIND HOW HOOLA HANDLE THE PAST COMPLETED WORK AND CURRENT WORK IN ALL
SURFACES" -> GO on the four fixes. Before: finished work was only visible by scrolling a chat (the phone / console
'Today' pages and the live strips showed running or waiting work only), and a call's brain saw jobs of the last 6 h only
(the 7-day diary is too slow for a call, v0.644) - "kal jo kaam diya tha" needed extra tool steps.

Two readers over the stores that already exist (nothing new is written):
  * `listing(tenant)` - the Kaam list (GET /api/kaam/list): running + waiting for her (job tracker, `kaam_jobs`) and
    finished in the last 7 days (tracked jobs that ended + the chat task log `TaskRun`, talk excluded), each row with
    the conversation it came from (a call record or a chat) so a tap opens it.
  * `brief(tenant, conv)` - for a call's brain turn: ~10 short lines of what finished this week in the same memory
    scope, from two small indexed queries (fast enough for the call's 2.5 s memory wait).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from .db import session

log = logging.getLogger("santosh.kaamlist")
STATS: dict[str, int] = {"lists": 0, "briefs": 0}
OUTCOME = {"done": "done", "partial": "partly done", "stuck": "stuck", "stopped": "stopped"}
STATE = {"working": "running", "waiting": "needs your answer", "done": "done", "failed": "ran into a problem",
         "stopped": "stopped"}


def _utc(d: datetime | None) -> datetime:
    if d is None:
        return datetime.now(timezone.utc)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _clip(s: Any, n: int) -> str:
    t = re.sub(r"\s+", " ", str(s or "")).strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _calls(ids: set[str]) -> set[str]:
    if not ids:
        return set()
    from .db import Conversation
    with session() as s:
        return set(s.scalars(select(Conversation.id).where(Conversation.id.in_(list(ids)),
                                                           Conversation.kind == "call")).all())


def _jobs(tenant: str, since: datetime) -> list[dict[str, Any]]:
    from .kaamwatch import KaamJob, _row_view
    with session() as s:
        rows = s.scalars(select(KaamJob).where(KaamJob.tenant_id == tenant, KaamJob.updated_at >= since)
                         .order_by(KaamJob.updated_at.desc()).limit(80)).all()
        return [_row_view(r) for r in rows]


def _runs(tenant: str, since: datetime, limit: int = 60) -> list[Any]:
    from .agent.pakka import TaskRun
    with session() as s:
        rows = s.scalars(select(TaskRun).where(TaskRun.tenant_id == tenant, TaskRun.created_at >= since,
                                               TaskRun.outcome != "talk")
                         .order_by(TaskRun.created_at.desc()).limit(limit)).all()
        for r in rows:
            s.expunge(r)
        return rows


def _is_work(r) -> bool:
    """v0.662 a finished task row that is real work: not a routine / goal / worker prompt ("[Automatic job...", "[Goal
    jaari..."), and not a question answered only by READ tools (weather, 'mera calendar batao')."""
    req = (getattr(r, "request", "") or "").lstrip()
    if req.startswith("["):
        return False
    try:
        import json as _json
        tools = [t for t in _json.loads(getattr(r, "tools", "") or "[]") if isinstance(t, str)]
    except Exception:
        tools = []
    if tools:
        from .agent import draftcheck
        if all(draftcheck._is_read(t) for t in tools):
            return False
    return True


def listing(tenant: str, days: int = 7) -> dict[str, Any]:
    """Running, waiting for her, and finished in the last `days` days, newest first."""
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(int(days), 30)))
    running, waiting, done = [], [], []
    for j in _jobs(tenant, since):
        stuck = j["state"] == "working" and j["minutes_since_change"] >= 15
        row = {"source": "job", "kind": j["kind"], "label": j["label"], "title": j["title"] or j["label"],
               "started_at": j.get("started_at") or j["updated_at"],
               "state": j["state"], "stuck": stuck,
               "say": (f"stuck (for {j['minutes_since_change']} min)" if stuck else STATE.get(j["state"], j["state"])),
               "detail": j["stage"] or j["detail"],
               "pct": j["pct"], "link": j["link"], "conversation_id": j["conversation_id"], "at": j["updated_at"]}
        (running if j["state"] == "working" else waiting if j["state"] == "waiting" else done).append(row)
    jobs_by_conv: dict[str, list[datetime]] = {}
    for x in running + waiting + done:
        if x["conversation_id"]:
            try:
                jobs_by_conv.setdefault(x["conversation_id"], []).append(datetime.fromisoformat(x.get("started_at") or x["at"]))
            except Exception:
                pass
    for r in _runs(tenant, since):
        if not _is_work(r):
            continue          # v0.662 a question answered by reading, or a routine / goal round prompt, is not "her work done"
        rat = _utc(r.created_at)
        if any(timedelta(seconds=-60) <= (j - rat) <= timedelta(seconds=(r.seconds or 0) + 180)
               for j in jobs_by_conv.get(getattr(r, "conversation_id", "") or "", [])):
            continue          # v0.662 this turn STARTED a tracked job - the job's own row tells its true state (no "ho gaya" twice)
        done.append({"source": "task", "kind": "task", "label": "Task", "title": _clip(r.request, 160) or "Task",
                     "state": "done" if r.outcome == "done" else ("failed" if r.outcome == "stuck" else r.outcome),
                     "say": OUTCOME.get(r.outcome, r.outcome), "detail": _clip(r.left, 160) and f"pending: {_clip(r.left, 150)}",
                     "pct": -1, "link": "", "conversation_id": getattr(r, "conversation_id", "") or "",
                     "at": _utc(r.created_at).isoformat()})
    try:   # v0.662 the cards that wait for HER tap are her waiting work too (they were missing from this list)
        from .events import waiting_cards
        for c in waiting_cards(tenant, 20, max_age_h=days * 24):
            waiting.append({"source": "card", "kind": c["kind"], "label": "Card", "title": c["title"], "state": "waiting",
                            "stuck": False, "say": f"needs your OK (for {c['age_h']} h)", "detail": "",
                            "pct": -1, "link": "", "conversation_id": c.get("conversation_id", ""),
                            "at": c.get("at", "")})
    except Exception:
        log.exception("kaam list: waiting cards failed")
    done.sort(key=lambda x: x["at"], reverse=True)
    done = done[:60]
    calls = _calls({x["conversation_id"] for x in running + waiting + done if x["conversation_id"]})
    for x in running + waiting + done:
        x["from_call"] = x["conversation_id"] in calls
    STATS["lists"] += 1
    return {"running": running, "waiting": waiting, "done": done, "days": days,
            "counts": {"running": len(running), "waiting": len(waiting), "done": len(done)}}


def brief(tenant: str, conversation_id: str, days: int = 7, n: int = 10, max_chars: int = 1400) -> str:
    """A call brain turn's 'done this week' lines (same memory scope as the call), newest first."""
    if not tenant:
        return ""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        from .fence import chats_in, visible
        allowed = chats_in(tenant, conversation_id) if conversation_id else None
        from .yaad import _when
        items: list[tuple[datetime, str]] = []
        for r in _runs(tenant, since, 40):
            if not visible(getattr(r, "conversation_id", None), allowed):
                continue
            line = f"{_when(r.created_at, tenant)} · {_clip(r.request, 100)} → {OUTCOME.get(r.outcome, r.outcome)}"
            if r.left:
                line += f"; pending: {_clip(r.left, 70)}"
            items.append((_utc(r.created_at), line))
        for j in _jobs(tenant, since):
            if j["state"] not in ("done", "failed", "stopped") or not visible(j["conversation_id"], allowed):
                continue
            at = datetime.fromisoformat(j["updated_at"])
            items.append((at, f"{_when(at, tenant)} · {j['label']} {_clip(j['title'], 90)} → {STATE.get(j['state'], j['state'])}"))
    except Exception:
        log.exception("kaam brief failed")
        return ""
    if not items:
        return ""
    items.sort(key=lambda x: x[0], reverse=True)
    body = "\n".join("- " + t for _, t in items[:n])[:max_chars]
    STATS["briefs"] += 1
    return ("IS HAFTE KA KIYA HUA KAAM (work done this week, newest first; for 'the work I gave yesterday / last week' - answer from here, "
            "kaam_status / yaad_khojo only for older or deeper detail):\n" + body)
