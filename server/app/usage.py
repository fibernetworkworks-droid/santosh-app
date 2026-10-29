"""v0.98 Know the cost: what Hoola's AI costs per owner, per day, per feature, with a monthly budget.

From the Grok Bot study (Claude Doc "Grok Bot teardown: what Hoola should take", idea 4; Grok Bot's
GetDailySpendByCategory). Every paid model call is counted where it happens, in ONE place each, without touching the
~20 modules that call models:

  * Claude: `anthropic` Messages.create / AsyncMessages.create are wrapped once (`install`): `usage` on the reply
    (input / output / cache write / cache read tokens).
  * Gemini: google-genai Models.generate_content / AsyncModels.generate_content wrapped: `usage_metadata` (prompt,
    candidates + thinking tokens, audio parts priced as audio).
  * The cheap brain (OpenAI-compatible, `agent/llm.openai_create`): its `usage` block.
  * Voice calls (Gemini Live): per minute of audio really streamed each way (`voice.Call` counts the bytes).
  * Video Studio's OpenRouter spend is already a real ledger; the report adds it.

Who and what: a context (`scope` / `bind`) carries the owner and the feature (chat, call, routine, employee, website, pc,
video, motion, studio, network, lekhak, reels...). The HTTP middleware sets the owner (resolved lazily, only when a model
is really called) and a feature from the API path; chat turns, calls and background jobs set their own.

Money: USD prices per 1M tokens / per minute (PRICES, from the official price pages on 22 Oct 2026; override with
USAGE_PRICES JSON), shown in rupees at USAGE_USD_INR. Budget per owner per calendar month (IST): her own limit
(Profile > Kharcha) and / or the server's USAGE_MONTH_USD ceiling - the lower one counts. 80% = one warning (chat + push);
100% = background work (routines, team / customer turns, website jobs, video / motion jobs, avatar look-ups) pauses until
the next month or a higher limit; her own chat and calls keep working, and she is told plainly.
Counts only: no prompt or reply text is ever stored here.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import DateTime, Float, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, now, session

log = logging.getLogger("santosh.usage")
IST = timezone(timedelta(hours=5, minutes=30))

# USD per 1M tokens; live models also per minute of audio. Longest matching prefix wins.
PRICES: dict[str, dict[str, float]] = {
    "claude-sonnet-5-5": {"in": 2.0, "out": 10.0, "cache_write": 2.5, "cache_read": 0.10},
    "claude-sonnet-5": {"in": 2.0, "out": 10.0, "cache_write": 2.5, "cache_read": 0.20},
    "claude-opus-5-5": {"in": 4.0, "out": 20.0, "cache_write": 5.0, "cache_read": 0.20},
    "claude-opus-5": {"in": 5.0, "out": 25.0, "cache_write": 6.25, "cache_read": 0.50},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cache_write": 0.125, "cache_read": 0.01},
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0, "cache_write": 1.25, "cache_read": 0.10},
    "claude-sonnet-4": {"in": 3.0, "out": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "claude-opus-4": {"in": 5.0, "out": 25.0, "cache_write": 6.25, "cache_read": 0.50},
    "claude": {"in": 2.0, "out": 10.0, "cache_write": 2.5, "cache_read": 0.10},
    "gemini-3.8-live": {"in": 0.75, "out": 4.5, "audio_in": 3.0, "audio_out": 12.0, "audio_in_min": 0.005, "audio_out_min": 0.018},
    "gemini-3.1-flash-live": {"in": 0.75, "out": 4.5, "audio_in": 3.0, "audio_out": 12.0, "audio_in_min": 0.005, "audio_out_min": 0.018},
    "gemini-3.8-flash": {"in": 0.75, "out": 3.75},
    "gemini-3.6-flash": {"in": 0.75, "out": 3.75},
    "gemini-2.5-flash-preview-tts": {"in": 0.50, "out": 10.0, "audio_out": 10.0},
    "gemini-3.1-flash-tts": {"in": 1.0, "out": 20.0, "audio_out": 20.0},
    "lyria": {"audio_out_min": 0.08},          # v0.258 a Lyria song is counted as one "minute" = studio MUSIC_USD per song
    "gemini-2.5-flash-image": {"in": 0.30, "out": 30.0},
    "gemini-3.1-flash-lite-image": {"in": 0.25, "out": 30.0},       # ~$0.034 per 1K picture
    "gemini-nano-banana-2.1": {"in": 1.50, "out": 30.0},
    "gemini-3.1-flash-image": {"in": 0.50, "out": 60.0},            # ~$0.067 per 1K picture
    "gemini-3-pro-image": {"in": 2.0, "out": 120.0},                # ~$0.134 per 1K / 2K picture
    "gemini-2.5-flash-lite": {"in": 0.10, "out": 0.40, "audio_in": 0.30},
    "gemini-2.5-flash": {"in": 0.30, "out": 2.50, "audio_in": 1.0},
    "gemini-2.5-pro": {"in": 1.25, "out": 10.0},
    "gemini": {"in": 0.75, "out": 3.75, "audio_in": 3.0},
    "glm": {"in": 0.60, "out": 2.20},
    "*": {"in": 1.0, "out": 4.0},        # an unknown model: counted, marked as an estimate
}
STATS = {"recorded": 0, "flushes": 0, "paused": 0, "warned": 0, "unknown_models": 0}
BACKGROUND = {"routine", "employee", "website", "video", "motion", "studio", "network", "draft_check"}
FEATURE_LABEL = {"chat": "Chat", "call": "Voice call", "routine": "Routines", "employee": "Team / graahak", "website":
                 "Website jobs", "pc": "PC par kaam", "video": "Video editor", "motion": "Motion reels", "studio":
                 "Video Studio", "create": "Create Studio", "network": "Hoola Network", "lekhak": "Typist / translator", "reels": "Reels",
                 "notebook": "Notebook", "voiceid": "Awaaz Pehchaan", "other": "Baaki"}

_CTX: contextvars.ContextVar[dict | None] = contextvars.ContextVar("hoola_usage", default=None)
_BUF: dict[tuple, dict[str, float]] = {}
_LOCK = threading.Lock()
_LAST_FLUSH = [time.time()]
_FLUSH_LOCK = threading.Lock()   # one flush at a time: a report waits for a flush already writing
_INSTALLED = [False]


class UsageDay(Base):
    __tablename__ = "usage_days"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)          # IST date
    feature: Mapped[str] = mapped_column(String(24))
    model: Mapped[str] = mapped_column(String(80))
    calls: Mapped[int] = mapped_column(Integer, default=0)
    tok_in: Mapped[int] = mapped_column(Integer, default=0)
    tok_out: Mapped[int] = mapped_column(Integer, default=0)
    tok_cache: Mapped[int] = mapped_column(Integer, default=0)
    seconds: Mapped[float] = mapped_column(Float, default=0.0)
    usd: Mapped[float] = mapped_column(Float, default=0.0)


class UsageBudget(Base):
    __tablename__ = "usage_budgets"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    month_usd: Mapped[float] = mapped_column(Float, default=0.0)     # her own limit (0 = none)
    warned: Mapped[str] = mapped_column(String(7), default="")      # YYYY-MM already warned at 80%
    stopped: Mapped[str] = mapped_column(String(7), default="")     # YYYY-MM already told about the pause
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


# ---------------------------------------------------------------- who / what
def bind(tenant: str | None = None, feature: str | None = None, resolver: Callable[[], str] | None = None) -> None:
    """Set the owner / feature for everything after this in the current task (and tasks / threads it starts)."""
    cur = dict(_CTX.get() or {})
    if tenant is not None:
        cur["tenant"], cur["resolver"] = tenant, None
    if resolver is not None and not cur.get("tenant"):
        cur["resolver"] = resolver
    if feature is not None:
        cur["feature"] = feature
    _CTX.set(cur)


@contextmanager
def scope(tenant: str | None = None, feature: str | None = None):
    tok = _CTX.set(dict(_CTX.get() or {}))
    try:
        bind(tenant, feature)
        yield
    finally:
        _CTX.reset(tok)


def current() -> tuple[str, str]:
    cur = _CTX.get() or {}
    tenant = cur.get("tenant") or ""
    if not tenant and cur.get("resolver"):
        try:
            tenant = cur["resolver"]() or ""
        except Exception:
            tenant = ""
        cur["tenant"] = tenant
    return tenant, cur.get("feature") or "other"


def feature_for_path(path: str) -> str:
    p = path.split("?")[0]
    for prefix, feat in (("/api/voice", "call"), ("/api/lekhak", "lekhak"), ("/api/reels", "reels"), ("/api/net", "network"),
                         ("/api/video", "video"), ("/api/motion", "motion"), ("/api/studio", "studio"), ("/api/create", "create"),
                         ("/api/operator", "website"), ("/api/sites", "site"), ("/api/apps", "app"), ("/api/blender3d", "3d"), ("/api/notebook", "notebook"), ("/api/voiceid", "voiceid"), ("/api/gyaan", "gyaan"),
                         ("/api/conversations", "chat"), ("/api/forms", "chat")):
        if p.startswith(prefix):
            return feat
    return "other"


# ---------------------------------------------------------------- prices
def _prices() -> dict[str, dict[str, float]]:
    raw = os.environ.get("USAGE_PRICES") or ""
    if not raw:
        return PRICES
    try:
        extra = json.loads(raw)
        return {**PRICES, **{str(k): dict(v) for k, v in extra.items()}}
    except (ValueError, AttributeError, TypeError):
        log.warning("USAGE_PRICES is not valid JSON; using the built-in prices")
        return PRICES


def price_of(model: str) -> tuple[dict[str, float], bool]:
    """(prices, known). Longest prefix of the model name; '*' when nothing matches."""
    m = (model or "").lower().strip()
    if "/" in m:
        m = m.rsplit("/", 1)[-1]
    table = _prices()
    best = ""
    for k in table:
        if k != "*" and m.startswith(k) and len(k) > len(best):
            best = k
    if best:
        return table[best], True
    STATS["unknown_models"] += 1
    return table["*"], False


def cost(model: str, tok_in: int = 0, tok_out: int = 0, cache_read: int = 0, cache_write: int = 0,
         audio_in: int = 0, audio_out: int = 0, sec_in: float = 0.0, sec_out: float = 0.0) -> float:
    p, _ = price_of(model)
    usd = (tok_in * p.get("in", 0) + tok_out * p.get("out", 0) + cache_read * p.get("cache_read", p.get("in", 0) * 0.1)
           + cache_write * p.get("cache_write", p.get("in", 0) * 1.25)
           + audio_in * p.get("audio_in", p.get("in", 0)) + audio_out * p.get("audio_out", p.get("out", 0))) / 1e6
    usd += sec_in / 60 * p.get("audio_in_min", 0) + sec_out / 60 * p.get("audio_out_min", 0)
    return round(usd, 8)


def usd_inr() -> float:
    try:
        from .config import get_settings
        return float(getattr(get_settings(), "usage_usd_inr", 0) or 0) or 88.0
    except Exception:
        return 88.0


# ---------------------------------------------------------------- recording
def record(model: str, tok_in: int = 0, tok_out: int = 0, cache_read: int = 0, cache_write: int = 0,
           audio_in: int = 0, audio_out: int = 0, sec_in: float = 0.0, sec_out: float = 0.0,
           tenant: str | None = None, feature: str | None = None) -> float:
    """Count one model call (never raises; the work must never fail because of counting)."""
    try:
        t, f = current()
        tenant = tenant if tenant is not None else t
        feature = feature or f
        usd = cost(model, tok_in, tok_out, cache_read, cache_write, audio_in, audio_out, sec_in, sec_out)
        day = datetime.now(IST).date().isoformat()
        key = (tenant or "", day, feature, (model or "?")[:80])
        with _LOCK:
            b = _BUF.setdefault(key, {"calls": 0, "tok_in": 0, "tok_out": 0, "tok_cache": 0, "seconds": 0.0, "usd": 0.0})
            b["calls"] += 1
            b["tok_in"] += int(tok_in + audio_in)
            b["tok_out"] += int(tok_out + audio_out)
            b["tok_cache"] += int(cache_read + cache_write)
            b["seconds"] += float(sec_in + sec_out)
            b["usd"] += usd
        STATS["recorded"] += 1
        hit = _STATE_CACHE.get(tenant or "")
        if hit:        # keep the cached month total current without a database read on every call
            st = dict(hit[1])
            st["spent_usd"] = round(st["spent_usd"] + usd, 6)
            lim = st["limit_usd"]
            st["pct"] = round(100 * st["spent_usd"] / lim, 1) if lim else 0.0
            st["over"], st["warn"] = bool(lim) and st["spent_usd"] >= lim, bool(lim) and st["pct"] >= 80
            _STATE_CACHE[tenant] = (hit[0], st)
        if time.time() - _LAST_FLUSH[0] > 30 or len(_BUF) > 200:
            flush()
        if tenant:
            _after(tenant)
        return usd
    except Exception:
        log.exception("usage record failed")
        return 0.0


def flush() -> None:
    with _FLUSH_LOCK:
        _flush()


def _flush() -> None:
    with _LOCK:
        items = list(_BUF.items())
        _BUF.clear()
        _LAST_FLUSH[0] = time.time()
    if not items:
        return
    try:
        with session() as s:
            for (tenant, day, feature, model), v in items:
                row = s.scalars(select(UsageDay).where(UsageDay.tenant_id == tenant, UsageDay.day == day,
                                                       UsageDay.feature == feature, UsageDay.model == model)).first()
                if row is None:
                    row = UsageDay(tenant_id=tenant, day=day, feature=feature, model=model, calls=0, tok_in=0, tok_out=0,
                                   tok_cache=0, seconds=0.0, usd=0.0)
                    s.add(row)
                row.calls += int(v["calls"])
                row.tok_in += int(v["tok_in"])
                row.tok_out += int(v["tok_out"])
                row.tok_cache += int(v["tok_cache"])
                row.seconds += float(v["seconds"])
                row.usd += float(v["usd"])
        STATS["flushes"] += 1
    except Exception:
        log.exception("usage flush failed")
        with _LOCK:            # keep the numbers for the next try
            for k, v in items:
                b = _BUF.setdefault(k, {"calls": 0, "tok_in": 0, "tok_out": 0, "tok_cache": 0, "seconds": 0.0, "usd": 0.0})
                for f in b:
                    b[f] += v[f]


def from_anthropic(model: str, resp: Any) -> None:
    u = getattr(resp, "usage", None)
    if u is None:
        return
    g = (lambda k: int(getattr(u, k, 0) or 0)) if not isinstance(u, dict) else (lambda k: int(u.get(k) or 0))
    record(getattr(resp, "model", None) or model or "claude", tok_in=g("input_tokens"), tok_out=g("output_tokens"),
           cache_read=g("cache_read_input_tokens"), cache_write=g("cache_creation_input_tokens"))


def from_gemini(model: str, resp: Any) -> None:
    u = getattr(resp, "usage_metadata", None)
    if u is None:
        return
    prompt = int(getattr(u, "prompt_token_count", 0) or 0)
    out = int(getattr(u, "candidates_token_count", 0) or 0) + int(getattr(u, "thoughts_token_count", 0) or 0)
    cached = int(getattr(u, "cached_content_token_count", 0) or 0)
    audio_in = sum(int(getattr(d, "token_count", 0) or 0) for d in (getattr(u, "prompt_tokens_details", None) or [])
                   if "AUDIO" in str(getattr(d, "modality", "")).upper())
    audio_out = sum(int(getattr(d, "token_count", 0) or 0) for d in (getattr(u, "candidates_tokens_details", None) or [])
                    if "AUDIO" in str(getattr(d, "modality", "")).upper())
    record(model or "gemini", tok_in=max(0, prompt - audio_in - cached), tok_out=max(0, out - audio_out),
           cache_read=cached, audio_in=audio_in, audio_out=audio_out)


def from_openai(model: str, usage: dict | None) -> None:
    if not usage:
        return
    cached = int(((usage.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0)
    record(usage.get("model") or model or "glm", tok_in=max(0, int(usage.get("prompt_tokens") or 0) - cached),
           tok_out=int(usage.get("completion_tokens") or 0), cache_read=cached)


def install() -> None:
    """Wrap the SDKs once (idempotent): every Claude / Gemini call anywhere in Hoola is counted."""
    if _INSTALLED[0]:
        return
    _INSTALLED[0] = True
    try:
        from anthropic.resources import AsyncMessages, Messages
        a_orig, s_orig = AsyncMessages.create, Messages.create

        async def a_create(self, *a, **kw):
            r = await a_orig(self, *a, **kw)
            if not kw.get("stream"):
                from_anthropic(kw.get("model", ""), r)
            return r

        def s_create(self, *a, **kw):
            r = s_orig(self, *a, **kw)
            if not kw.get("stream"):
                from_anthropic(kw.get("model", ""), r)
            return r
        AsyncMessages.create, Messages.create = a_create, s_create
    except Exception:
        log.exception("usage: anthropic not wrapped")
    try:
        from google.genai.models import AsyncModels, Models
        ga_orig, gs_orig = AsyncModels.generate_content, Models.generate_content

        async def ga(self, *a, **kw):
            r = await ga_orig(self, *a, **kw)
            from_gemini(str(kw.get("model") or (a[0] if a else "")), r)
            return r

        def gs(self, *a, **kw):
            r = gs_orig(self, *a, **kw)
            from_gemini(str(kw.get("model") or (a[0] if a else "")), r)
            return r
        AsyncModels.generate_content, Models.generate_content = ga, gs
    except Exception:
        log.exception("usage: google-genai not wrapped")


# ---------------------------------------------------------------- budget
def _month() -> str:
    return datetime.now(IST).strftime("%Y-%m")


def month_usd(tenant: str) -> float:
    """This calendar month (IST) so far: counted calls + Video Studio's real OpenRouter ledger."""
    flush()
    m = _month()
    with session() as s:
        rows = s.scalars(select(UsageDay.usd).where(UsageDay.tenant_id == tenant, UsageDay.day >= f"{m}-01")).all()
    total = float(sum(rows))
    try:
        from .studio import service as ss
        total += float(ss.month_spent(tenant) or 0)
    except Exception:
        pass
    return round(total, 6)


def limit_usd(tenant: str) -> tuple[float, str]:
    """(limit, whose): the lower of her own limit and the server's ceiling; 0 = no limit."""
    own = 0.0
    with session() as s:
        b = s.get(UsageBudget, tenant)
        if b is not None:
            own = float(b.month_usd or 0)
    try:
        from .config import get_settings
        server = float(getattr(get_settings(), "usage_month_usd", 0) or 0)
    except Exception:
        server = 0.0
    if own and server:
        return (own, "aapki") if own <= server else (server, "server")
    return (own, "aapki") if own else ((server, "server") if server else (0.0, ""))


_STATE_CACHE: dict[str, tuple[float, dict]] = {}


def state(tenant: str, fresh: bool = False) -> dict[str, Any]:
    """{spent, limit, pct, over, warn} for this month (cached 30 s)."""
    hit = _STATE_CACHE.get(tenant)
    if hit and not fresh and time.time() - hit[0] < 30:
        return hit[1]
    lim, whose = limit_usd(tenant)
    spent = month_usd(tenant)
    pct = round(100 * spent / lim, 1) if lim else 0.0
    out = {"spent_usd": round(spent, 4), "limit_usd": lim, "limit_by": whose, "pct": pct,
           "over": bool(lim) and spent >= lim, "warn": bool(lim) and pct >= 80}
    _STATE_CACHE[tenant] = (time.time(), out)
    return out


def allowed(tenant: str, feature: str) -> bool:
    """False = this background work must wait (the month's limit is used up). Her own chat / calls always run."""
    if not tenant or feature not in BACKGROUND:
        return True
    st = state(tenant)
    if st["over"]:
        STATS["paused"] += 1
        return False
    return True


def blocked_text(tenant: str) -> str:
    st = state(tenant)
    inr = usd_inr()
    return (f"Is mahine ka AI kharcha seema tak pahunch gaya (₹{st['spent_usd'] * inr:,.0f} / ₹{st['limit_usd'] * inr:,.0f}), "
            "isliye background kaam (routine, website / video jobs, team ke kaam) agle mahine tak ruke hain. Aapki apni chat "
            "aur call chalti rahegi. Seema badhani ho to Profile > Kharcha.")


def _after(tenant: str) -> None:
    """80% -> one warning a month; 100% -> one plain line about the pause."""
    st = state(tenant)
    if not st["limit_usd"] or not (st["warn"] or st["over"]):
        return
    m = _month()
    with session() as s:
        b = s.get(UsageBudget, tenant)
        if b is None:
            b = UsageBudget(tenant_id=tenant, month_usd=0.0)
            s.add(b)
        say = ""
        inr = usd_inr()
        if st["over"] and b.stopped != m:
            b.stopped = b.warned = m
            say = blocked_text(tenant)
        elif st["warn"] and not st["over"] and b.warned != m:
            b.warned = m
            say = (f"Is mahine ka AI kharcha {st['pct']:.0f}% ho gaya (₹{st['spent_usd'] * inr:,.0f} / "
                   f"₹{st['limit_usd'] * inr:,.0f}). Poora hone par background kaam ruk jayenge; Profile > Kharcha mein dekhiye.")
    if say:
        STATS["warned"] += 1
        try:
            from .events import notify
            from .net.service import home_conv
            conv = home_conv(tenant)
            if conv:
                notify(conv, say)
        except Exception:
            log.exception("usage warning failed")


def set_limit(tenant: str, month_usd: float | None = None, month_inr: float | None = None) -> dict[str, Any]:
    v = float(month_usd if month_usd is not None else (float(month_inr or 0) / usd_inr()))
    if v < 0:
        raise ValueError("limit can't be negative")
    with session() as s:
        b = s.get(UsageBudget, tenant)
        if b is None:
            b = UsageBudget(tenant_id=tenant)
            s.add(b)
        b.month_usd = round(v, 4)
        b.stopped = ""          # a new limit: tell again if it is reached
    _STATE_CACHE.pop(tenant, None)
    return report(tenant)


# ---------------------------------------------------------------- report
def report(tenant: str, days: int = 30) -> dict[str, Any]:
    flush()
    days = max(1, min(int(days or 30), 120))
    today = datetime.now(IST).date()
    since = (today - timedelta(days=days - 1)).isoformat()
    with session() as s:
        rows = s.scalars(select(UsageDay).where(UsageDay.tenant_id == tenant, UsageDay.day >= since)).all()
        data = [(r.day, r.feature, r.model, r.calls, r.tok_in, r.tok_out, r.tok_cache, r.seconds, r.usd) for r in rows]
    inr = usd_inr()
    by_day: dict[str, float] = {}
    by_feat: dict[str, dict[str, float]] = {}
    by_model: dict[str, dict[str, float]] = {}
    for day, feat, model, calls, ti, to, tc, sec, usd in data:
        by_day[day] = by_day.get(day, 0) + usd
        f = by_feat.setdefault(feat, {"usd": 0.0, "calls": 0})
        f["usd"] += usd
        f["calls"] += calls
        mm = by_model.setdefault(model, {"usd": 0.0, "calls": 0, "tok_in": 0, "tok_out": 0, "seconds": 0.0})
        mm["usd"] += usd
        mm["calls"] += calls
        mm["tok_in"] += ti
        mm["tok_out"] += to
        mm["seconds"] += sec
    total = sum(by_day.values())
    st = state(tenant, fresh=True)
    first = today.replace(day=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    elapsed = (today - first).days + 1
    month_days = (nxt - first).days
    projected = st["spent_usd"] / elapsed * month_days if elapsed else 0.0
    feats = sorted(({"feature": k, "label": FEATURE_LABEL.get(k, k), "usd": round(v["usd"], 4), "inr": round(v["usd"] * inr, 2),
                     "calls": int(v["calls"]), "share": round(100 * v["usd"] / total, 1) if total else 0.0}
                    for k, v in by_feat.items()), key=lambda x: -x["usd"])
    models = sorted(({"model": k, "usd": round(v["usd"], 4), "inr": round(v["usd"] * inr, 2), "calls": int(v["calls"]),
                      "tok_in": int(v["tok_in"]), "tok_out": int(v["tok_out"]), "minutes": round(v["seconds"] / 60, 1),
                      "estimate": not price_of(k)[1]} for k, v in by_model.items()), key=lambda x: -x["usd"])
    daily = [{"day": (today - timedelta(days=i)).isoformat(),
              "inr": round(by_day.get((today - timedelta(days=i)).isoformat(), 0.0) * inr, 2)} for i in range(days - 1, -1, -1)]
    say = (f"Is mahine ab tak ₹{st['spent_usd'] * inr:,.0f}"
           + (f" / seema ₹{st['limit_usd'] * inr:,.0f} ({st['pct']:.0f}%)" if st["limit_usd"] else "")
           + f"; isi raftaar se mahine ke ant tak ~₹{projected * inr:,.0f}."
           + (f" Sabse zyada: {feats[0]['label']} ({feats[0]['share']:.0f}%)." if feats else ""))
    try:   # v0.161 her thumbs on replies in the same window
        from .livereply import feedback_counts
        thumbs = feedback_counts(tenant, datetime.combine(today - timedelta(days=days - 1), datetime.min.time(), IST)
                                 .astimezone(timezone.utc))
    except Exception:
        log.exception("usage: reply feedback")
        thumbs = {"up": 0, "down": 0}
    return {"days": days, "usd_inr": inr, "total_usd": round(total, 4), "total_inr": round(total * inr, 2),
            "month": {**st, "spent_inr": round(st["spent_usd"] * inr, 2), "limit_inr": round(st["limit_usd"] * inr, 2),
                      "projected_usd": round(projected, 4), "projected_inr": round(projected * inr, 2)},
            "features": feats, "models": models, "daily": daily, "say": say, "replies": thumbs,
            "note": "Andaaza: official price list (22 Oct 2026) se; asli bill provider ke dashboard par."}


def all_tenants(days: int = 30) -> list[dict[str, Any]]:
    """Server owner's view: spend per owner (counts only)."""
    flush()
    since = (datetime.now(IST).date() - timedelta(days=max(1, int(days)) - 1)).isoformat()
    with session() as s:
        rows = s.execute(select(UsageDay.tenant_id, UsageDay.usd, UsageDay.calls).where(UsageDay.day >= since)).all()
    agg: dict[str, dict[str, float]] = {}
    for t, usd, calls in rows:
        a = agg.setdefault(t or "(unknown)", {"usd": 0.0, "calls": 0})
        a["usd"] += usd
        a["calls"] += calls
    inr = usd_inr()
    return sorted(({"tenant": t, "usd": round(v["usd"], 4), "inr": round(v["usd"] * inr, 2), "calls": int(v["calls"])}
                   for t, v in agg.items()), key=lambda x: -x["usd"])
