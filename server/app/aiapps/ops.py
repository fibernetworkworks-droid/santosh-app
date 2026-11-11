"""v0.772 HOOLA AI APPS - D3 run & improve: what her app said, her corrections, its numbers, its gaps, its cost alerts.

  logs     - every question and answer (masked), newest first, filterable by outcome / words.
  correct  - HER better answer for one logged question: saved as her approved answer (gyaan annotations), so the
             next time anyone asks it, the app serves her words first; the logged row is marked corrected.
  stats    - per day and totals: messages, sessions, answered share, unknown, refused, actions, speed, rupees this
             month against the monthly cap, satisfaction (None until a visitor rates - never a made-up 0%).
  gaps     - the questions it could not answer, grouped, the most asked first: what she should teach it next.
  tick     - the worker's look: at 80% and at 100% of an app's monthly cap ONE note into her chat, never the same kind
             twice in a month. Hidden test tenants ('__...') are never told anything.

Counts in stats / gaps are what CUSTOMERS asked (page, embed, WhatsApp, API, MCP); her own preview / trial / proof
questions are left out so they do not skew the numbers. Logs show everything, with the channel on each row.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, func, select

from ..db import new_id, session
from . import runtime as RT
from . import store as ST
from .models import AiApp, AiAppMessage, ensure_tables

log = logging.getLogger("santosh.aiapps.ops")

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:                                       # noqa: BLE001
    IST = timezone(timedelta(hours=5, minutes=30))

ANSWERED = ("answered", "annotated", "model", "action")
OUTCOMES = ("answered", "annotated", "model", "unknown", "refused", "action", "cap", "paused", "error")
MAX_LOGS = 500
MAX_ANSWER = 2000

# a corrected answer must never carry or ask for a secret (it is served word for word to every customer)
_ASK_SECRET = re.compile(r"\b(send|share|tell|give|type|enter|reply with|bhejo|bhej do|batao|bataiye|dijiye)\b.{0,25}"
                         r"\b(otp|pin|cvv|password|passcode|card number|card no)\b|\b(otp|pin|cvv|password|card number)\b.{0,25}"
                         r"\b(send|share|bhejo|batao|bataiye|dijiye|chahiye)\b", re.I)
_SECRET_VALUE = re.compile(r"\b(otp|pin|cvv|password|passcode|passwd)\b(\W{0,4}(is|hai|:|=)?\W{0,3})(\S+)", re.I)
_NEGATED = re.compile(r"\b(never|don'?t|do not|not|no one|nobody|mat|kabhi|na)\b", re.I)

# ---------------------------------------------------------------- the alerts table (owned here, self-heals)
_META = MetaData()
ALERTS = Table(
    "ai_app_alerts", _META,
    Column("id", String(40), primary_key=True),
    Column("app_id", String(40), index=True),
    Column("tenant_id", String(64), index=True),
    Column("month", String(7)),                      # YYYY-MM (UTC, as month_spend)
    Column("kind", String(8)),                       # "80" | "100"
    Column("percent", Integer, default=0),
    Column("created_at", DateTime(timezone=True)),
)
_READY: set[int] = set()


def ensure_alerts() -> None:
    from .. import db as _db
    ensure_tables()
    eng = getattr(_db, "_engine", None)
    if eng is None:
        _db.init_db()
        eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    ALERTS.create(eng, checkfirst=True)
    _READY.add(id(eng))


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _iso(d: datetime | None) -> str:
    d = _utc(d)
    return d.isoformat() if d else ""


def _j(s: str | None, d: Any) -> Any:
    try:
        v = json.loads(s or "")
        return v if v is not None else d
    except (TypeError, ValueError):
        return d


def _cap_of(a: AiApp) -> float:
    """The cap that really applies: the LIVE soul's (it answers the public), else the draft's."""
    sl, _v = ST.live_soul(a)
    if not sl:
        sl = ST.draft_soul(a)
    try:
        return float((sl.get("limits") or {}).get("monthly_cap_inr", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------- logs
def _mask_log(text: str) -> str:
    """The log she reads: the house mask, plus the value after an OTP / PIN / password word (a refused question
    still carried it)."""
    t = RT._mask(text or "")
    return _SECRET_VALUE.sub(lambda m: m.group(1) + m.group(2) + "******", t)


def logs(tenant: str, ref: str, outcome: str = "", q: str = "", limit: int = 100, channel: str = "") -> list[dict[str, Any]]:
    a = ST.row(tenant, ref)
    outcome = (outcome or "").strip().lower()
    if outcome and outcome not in OUTCOMES:
        raise ST.AppError(f"outcome: {', '.join(OUTCOMES)}")
    limit = max(1, min(int(limit or 100), MAX_LOGS))
    with session() as s:
        qy = s.query(AiAppMessage).filter(AiAppMessage.app_id == a.id, AiAppMessage.tenant_id == tenant)
        if outcome:
            qy = qy.filter(AiAppMessage.outcome == outcome)
        if channel:
            qy = qy.filter(AiAppMessage.channel == channel)
        words = (q or "").strip()[:100]
        if words:
            like = f"%{words}%"
            qy = qy.filter((AiAppMessage.question.ilike(like)) | (AiAppMessage.answer.ilike(like)))
        rows = qy.order_by(AiAppMessage.created_at.desc(), AiAppMessage.id.desc()).limit(limit).all()
        out = [{"id": m.id, "session_id": m.session_id, "channel": m.channel, "version": m.version,
                "question": _mask_log(m.question or ""), "answer": m.answer or "", "outcome": m.outcome,
                "sources": _j(m.sources, []), "action": _j(m.action, None) if m.action else None,
                "feedback": m.feedback or 0, "corrected": m.corrected or "", "inr": round(float(m.inr or 0), 4),
                "ms": m.ms or 0, "at": _iso(m.created_at)} for m in rows]
    return out


# ---------------------------------------------------------------- correct (her better answer)
def _unsafe(text: str) -> bool:
    if RT._secret(text):
        return True
    for part in re.split(r"(?<=[.!?\n])\s+", text):
        if _ASK_SECRET.search(part) and not _NEGATED.search(part):
            return True
    return False


def correct(tenant: str, ref: str, message_id: str, answer: str) -> dict[str, Any]:
    a = ST.row(tenant, ref)
    ans = str(answer or "").strip()
    if not ans:
        raise ST.AppError("Write the answer it should give.", 422)
    if len(ans) > MAX_ANSWER:
        raise ST.AppError(f"Keep the answer under {MAX_ANSWER} characters.", 422)
    if _unsafe(ans):
        raise ST.AppError("That answer has an OTP, PIN, password or card number in it (or asks for one). "
                          "Customers must never be asked for those - write it without.", 422)
    with session() as s:
        m = s.get(AiAppMessage, message_id)
        if m is None or m.app_id != a.id or m.tenant_id != tenant:
            raise ST.AppError("That logged answer was not found.", 404)
        question = m.question or ""
    if not question.strip():
        raise ST.AppError("That log row has no question to attach the answer to.", 422)
    from ..gyaan import annotations as AN
    got = AN.save(tenant, question, ans, note=f"ai app {a.id}")
    if not got.get("ok"):
        raise ST.AppError(f"It could not be saved: {got.get('error') or 'unknown reason'}", 422)
    with session() as s:
        m = s.get(AiAppMessage, message_id)
        if m is not None:
            m.corrected = ans[:4000]
    return {"ok": True, "message_id": message_id, "pair_id": got.get("id", ""),
            "says": "Saved as your approved answer. The next time anyone asks this, the app answers with your words."}


# ---------------------------------------------------------------- stats
def _day(d: datetime | None) -> str:
    d = _utc(d)
    return d.astimezone(IST).date().isoformat() if d else ""


def _block() -> dict[str, Any]:
    return {"messages": 0, "sessions": set(), "answered": 0, "unknown": 0, "refused": 0, "actions": 0, "ms": 0,
            "good": 0, "bad": 0}


def _finish(b: dict[str, Any]) -> dict[str, Any]:
    n = b["messages"]
    rated = b["good"] + b["bad"]
    return {"messages": n, "sessions": len(b["sessions"]),
            "answered_share": round(b["answered"] / n, 4) if n else None,
            "unknown": b["unknown"], "refused": b["refused"], "actions": b["actions"],
            "avg_ms": int(round(b["ms"] / n)) if n else 0,
            "satisfaction": round(b["good"] / rated, 4) if rated else None, "ratings": rated}


def stats(tenant: str, ref: str, days: int = 7) -> dict[str, Any]:
    a = ST.row(tenant, ref)
    days = max(1, min(int(days or 7), 90))
    today = datetime.now(IST).date()
    first = today - timedelta(days=days - 1)
    since = datetime(first.year, first.month, first.day, tzinfo=IST).astimezone(timezone.utc)
    with session() as s:
        rows = (s.query(AiAppMessage.session_id, AiAppMessage.outcome, AiAppMessage.ms, AiAppMessage.feedback,
                        AiAppMessage.created_at)
                .filter(AiAppMessage.app_id == a.id, AiAppMessage.tenant_id == tenant,
                        AiAppMessage.channel.in_(RT.PUBLIC), AiAppMessage.created_at >= since).all())
    per = {(first + timedelta(days=i)).isoformat(): _block() for i in range(days)}
    tot = _block()
    for sid, outcome, ms, fb, at in rows:
        d = _day(at)
        for b in (per.get(d), tot):
            if b is None:
                continue
            b["messages"] += 1
            if sid:
                b["sessions"].add(sid)
            if outcome in ANSWERED:
                b["answered"] += 1
            if outcome == "unknown":
                b["unknown"] += 1
            if outcome == "refused":
                b["refused"] += 1
            if outcome == "action":
                b["actions"] += 1
            b["ms"] += int(ms or 0)
            if (fb or 0) > 0:
                b["good"] += 1
            elif (fb or 0) < 0:
                b["bad"] += 1
    total = _finish(tot)
    spend = round(RT.month_spend(a.id), 2)
    cap = _cap_of(a)
    total["inr_month"] = spend
    total["cap_inr"] = cap
    total["cap_percent"] = round(100.0 * spend / cap, 1) if cap > 0 else None
    says = []
    if not total["messages"]:
        says.append(f"No customer questions in the last {days} days.")
    else:
        says.append(f"{total['messages']} questions, {int(round(100 * total['answered_share']))}% answered.")
    says.append("No ratings yet." if total["satisfaction"] is None
                else f"{int(round(100 * total['satisfaction']))}% of rated answers were good.")
    says.append(f"Rs {spend:,.2f} of its Rs {cap:,.0f} monthly limit used this month." if cap > 0
                else f"Rs {spend:,.2f} used this month.")
    return {"app_id": a.id, "days": days, "totals": total,
            "per_day": [{"day": d, **_finish(b)} for d, b in per.items()], "says": " ".join(says)}


# ---------------------------------------------------------------- gaps (what it could not answer)
_STOP = {"a", "an", "the", "is", "are", "do", "does", "you", "your", "i", "me", "my", "to", "of", "for", "in", "on", "at",
         "and", "or", "it", "can", "what", "please", "hai", "kya", "ka", "ki", "ke", "se", "mein", "ko", "aap", "hi"}


def norm(text: str) -> str:
    t = re.sub(r"[^\w\s]", " ", str(text or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def _words(n: str) -> set[str]:
    w = {x for x in n.split() if x not in _STOP}
    return w or set(n.split())


def gaps(tenant: str, ref: str, days: int = 30, limit: int = 50) -> list[dict[str, Any]]:
    a = ST.row(tenant, ref)
    days = max(1, min(int(days or 30), 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with session() as s:
        rows = (s.query(AiAppMessage.question, AiAppMessage.created_at)
                .filter(AiAppMessage.app_id == a.id, AiAppMessage.tenant_id == tenant,
                        AiAppMessage.outcome == "unknown", AiAppMessage.channel.in_(RT.PUBLIC),
                        AiAppMessage.created_at >= since)
                .order_by(AiAppMessage.created_at.asc()).limit(5000).all())
    groups: list[dict[str, Any]] = []
    for q, at in rows:
        n = norm(q)
        if not n:
            continue
        ws = _words(n)
        best, score = None, 0.0
        for g in groups:
            if g["norm"] == n:
                best, score = g, 1.0
                break
            inter = len(ws & g["words"])
            j = inter / len(ws | g["words"]) if ws | g["words"] else 0.0
            if j > score:
                best, score = g, j
        if best is not None and score >= 0.6:
            best["count"] += 1
            best["last"] = max(best["last"], _iso(at))
            best["example"] = _mask_log(q)              # the newest wording she will recognise
        else:
            groups.append({"norm": n, "words": ws, "count": 1, "last": _iso(at), "example": _mask_log(q)})
    groups.sort(key=lambda g: (g["count"], g["last"]), reverse=True)
    return [{"question": g["example"], "count": g["count"], "last_asked": g["last"], "key": g["norm"]}
            for g in groups[:max(1, min(int(limit or 50), 200))]]


# ---------------------------------------------------------------- the cost alerts (worker)
def _note(tenant: str, text: str) -> None:
    """Into HER chat, the way the other background desks do it (her 'Hoola updates' chat)."""
    from ..events import notify
    conv = ""
    try:
        from ..convs import notice_chat
        conv = notice_chat(tenant)
    except Exception:                                   # noqa: BLE001
        conv = ""
    if not conv:
        from ..net.service import home_conv
        conv = home_conv(tenant)
    notify(conv, text)


def _month(at: datetime) -> str:
    return at.astimezone(timezone.utc).strftime("%Y-%m")     # the same month runtime.month_spend counts


def tick(at: datetime | None = None) -> dict[str, Any]:
    """One look over every app that spent money this month. At 80% / 100% of its cap: one note each, once a month."""
    ensure_alerts()
    at = _utc(at) or datetime.now(timezone.utc)
    start = at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month = _month(at)
    sent: list[dict[str, Any]] = []
    with session() as s:
        spent = (s.query(AiAppMessage.app_id, func.coalesce(func.sum(AiAppMessage.inr), 0.0))
                 .filter(AiAppMessage.created_at >= start, AiAppMessage.inr > 0)
                 .group_by(AiAppMessage.app_id).all())
    for app_id, inr in spent:
        try:
            with session() as s:
                a = s.get(AiApp, app_id)
                if a is None:
                    continue
                s.expunge(a)
            if (a.tenant_id or "").startswith("__"):
                continue
            cap = _cap_of(a)
            if cap <= 0:
                continue
            pct = 100.0 * float(inr or 0) / cap
            if pct < 80:
                continue
            with session() as s:
                told = {r[0] for r in s.execute(select(ALERTS.c.kind).where(
                    ALERTS.c.app_id == a.id, ALERTS.c.month == month)).all()}
            kind = "100" if pct >= 100 else "80"
            if kind in told:
                continue
            if kind == "100":
                text = (f"{a.name} reached its limit; it now hands every new question to your team until next month "
                        f"or until you raise the limit (Rs {cap:,.0f} a month).")
            else:
                text = f"{a.name} has used {int(pct)}% of its Rs {cap:,.0f} monthly limit."
            with session() as s:
                kinds = [kind] + (["80"] if kind == "100" and "80" not in told else [])
                for k in kinds:                         # past 100% the 80% note would only be noise: marked told too
                    s.execute(ALERTS.insert().values(id=new_id("aal"), app_id=a.id, tenant_id=a.tenant_id, month=month,
                                                     kind=k, percent=int(pct), created_at=at))
            try:
                _note(a.tenant_id, text)
            except Exception:                           # noqa: BLE001
                log.debug("ai app alert note", exc_info=True)
            sent.append({"app_id": a.id, "kind": kind, "percent": int(pct), "text": text})
        except Exception:                               # noqa: BLE001
            log.debug("ai app alert %s", app_id, exc_info=True)
    return {"sent": len(sent), "alerts": sent}


def forget_alerts(app_id: str) -> None:
    """Called after an app is deleted (its alert rows have no meaning left)."""
    ensure_alerts()
    with session() as s:
        s.execute(ALERTS.delete().where(ALERTS.c.app_id == app_id))
