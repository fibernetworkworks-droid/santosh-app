"""v0.264 OPENAI VOICE: which engine speaks her call - Gemini (default, today's voice) or OpenAI "real voice".

The owner's rule: the existing Gemini voice stays exactly as it is; a user who wants the more human voice can pick
OpenAI. The choice is per user (`data/voice_engine/<tenant>.json`). OpenAI is used only when ALL of these hold,
else the call quietly runs on Gemini (and says why in one line):
- she picked it, an OPENAI_API_KEY is set on the server, and she is allowed (trial: only the main tenant);
- the app's OpenAI spend this month is under VOICE_OPENAI_MONTH_USD;
- her OpenAI minutes this month are under VOICE_OPENAI_USER_MIN.
Spend and minutes are counted per calendar month (IST) in `data/voice_engine/usage-YYYY-MM.json` - numbers only.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import get_settings

DIR = Path("data") / "voice_engine"
ENGINES = ("gemini", "openai")
_LOCK = threading.Lock()


def _slug(tenant: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", tenant or "main")[:80] or "main"


def _month() -> str:
    from .usage import IST
    return datetime.now(IST).strftime("%Y-%m")


def _read(p: Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        d = {}
    return d if isinstance(d, dict) else {}


def _write(p: Path, d: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d), encoding="utf-8")
    tmp.replace(p)


def chosen(tenant: str) -> str:
    return str(_read(DIR / f"{_slug(tenant)}.json").get("engine") or "gemini")


def allowed(tenant: str) -> bool:
    """Trial gate: "" = only the main tenant (the owner), "*" = everyone, else a comma list of tenants."""
    st = get_settings()
    who = (st.voice_openai_tenants or "").strip()
    if who == "*":
        return True
    if not who:
        return tenant == st.tenant_id
    return tenant in {w.strip() for w in who.split(",") if w.strip()}


def choose(tenant: str, engine: str) -> dict[str, Any]:
    if engine not in ENGINES:
        raise ValueError("engine must be gemini or openai")
    if engine == "openai" and not allowed(tenant):
        raise PermissionError("Real voice (OpenAI) abhi trial mein hai - sirf owner ke liye.")
    with _LOCK:
        _write(DIR / f"{_slug(tenant)}.json", {"engine": engine})
    return view(tenant)


def _usage() -> dict:
    return _read(DIR / f"usage-{_month()}.json")


def add_usage(tenant: str, usd: float = 0.0, seconds: float = 0.0) -> None:
    """Count OpenAI spend (app-wide) and her minutes for this month. Never raises into a call."""
    try:
        with _LOCK:
            p = DIR / f"usage-{_month()}.json"
            d = _read(p)
            d["usd"] = round(float(d.get("usd") or 0) + max(0.0, usd), 6)
            per = d.setdefault("seconds", {})
            per[tenant] = round(float(per.get(tenant) or 0) + max(0.0, seconds), 1)
            _write(p, d)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("openai voice usage not counted")


def pick(tenant: str) -> tuple[str, str]:
    """(engine, why) for her next call. why is "" when she gets what she chose, else the one plain line."""
    if chosen(tenant) != "openai":
        return "gemini", ""
    st = get_settings()
    if not st.openai_api_key:
        return "gemini", "Real voice ke liye server par OpenAI key nahi hai - abhi Gemini awaaz."
    if not allowed(tenant):
        return "gemini", "Real voice abhi trial mein hai - abhi Gemini awaaz."
    u = _usage()
    if st.voice_openai_month_usd <= 0 or float(u.get("usd") or 0) >= st.voice_openai_month_usd:
        return "gemini", "Is mahine ka real voice budget poora ho gaya - abhi Gemini awaaz."
    mins = float((u.get("seconds") or {}).get(tenant) or 0) / 60
    if st.voice_openai_user_min and mins >= st.voice_openai_user_min:
        return "gemini", "Is mahine ke real voice minute poore ho gaye - abhi Gemini awaaz."
    return "openai", ""


def _inr() -> float:
    from .usage import usd_inr
    return usd_inr()


def view(tenant: str) -> dict[str, Any]:
    st = get_settings()
    u = _usage()
    eng, why = pick(tenant)
    return {"chosen": chosen(tenant), "will_use": eng, "why": why, "allowed": allowed(tenant),
            "openai_ready": bool(st.openai_api_key), "model": st.voice_openai_model,
            "month": _month(), "month_usd": round(float(u.get("usd") or 0), 4), "month_budget_usd": st.voice_openai_month_usd,
            "month_inr": round(float(u.get("usd") or 0) * _inr(), 2),                     # v0.274 the phone shows rupees
            "month_budget_inr": round(st.voice_openai_month_usd * _inr()),
            "my_minutes": round(float((u.get("seconds") or {}).get(tenant) or 0) / 60, 1),
            "my_minutes_cap": st.voice_openai_user_min}
