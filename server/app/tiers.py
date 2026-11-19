"""v1.0 MODEL TIERS (owner: "GO BUILD THE TIERS"; tables in docs/research/claude_chat/11-14).

Each user picks ONE tier: ULTRA (the best models, burns credit fast), HIGH, MEDIUM or LOW. '' = Hoola's normal setup
(today's models, nothing changes). The tier decides the model for every kind of work that runs through OpenRouter:

  chat reply (the writer) / writing / maths / facts / exact formats / pictures / PDFs / research / code / long tool
  jobs (AI employee work) / the voice call's brain / Hoola Code / Web Studio / the video studio's quality

The picks come from the LMArena boards of 11 Nov 2026 and OpenRouter's maker prices of 19 Nov 2026 (quality bands
= points below the best: ULTRA < 25, HIGH 25-50, MEDIUM 50-80, LOW 80+; inside a band the cheapest). Each job has a
main model and a backup from another company.

Rules kept in code:
- Her own model in the dropdown always wins over the tier (she chose it).
- ULTRA is chosen only with confirm_ultra = she saw the credit warning (`set_tier`).
- Every OpenRouter call of a tier model carries a price ceiling (provider.max_price = 1.25 x the maker's own price),
  so OpenRouter can no longer route it to a provider charging 2-19x more; a call no provider can serve under the
  ceiling is asked again once without it (`llm`).
- The tier only applies where the server's chat runs through OpenRouter (`offered`), like the model dropdown.
Stored per tenant in data/model_tier/<tenant>.json. Switch `model_tiers` (default on).
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import re
import threading
from pathlib import Path
from typing import Any

from .config import get_settings

ORDER = ["ultra", "high", "medium", "low"]
_LOCK = threading.Lock()
# the tier THIS turn / call runs at ('' = none), set by santosh._run_turn; read by llm (price ceiling) and the Box
NOW: contextvars.ContextVar[str] = contextvars.ContextVar("hoola_tier_now", default="")

INR = 88.0

# v0.999.21 THE DOOR FOLLOWS HER TIER: a feature that calls a model through the shared door (every Claude-style call)
# names its kind of work here (`job`); the door then asks her tier's model for that job on OpenRouter, the backup next,
# and today's path only when both fail. '' = no job named = the door as before.
JOB: contextvars.ContextVar[str] = contextvars.ContextVar("hoola_door_job", default="")
# the one model the door is asking right now (set per attempt, so a failed main is never asked again by the old path)
JOB_PICK: contextvars.ContextVar[str] = contextvars.ContextVar("hoola_door_pick", default="")
# models that take text only (OpenRouter's list, 19 Nov 2026): skipped for a call that carries a picture / PDF
TEXT_ONLY = {"z-ai/glm-5.3"}

# maker's own standard price, $ per million tokens (in, out) - OpenRouter endpoints API, 19 Nov 2026
PRICE: dict[str, tuple[float, float]] = {
    "google/gemini-4-argon": (2.0, 10.0),
    "google/gemini-3.8-flash": (0.75, 3.75),
    "anthropic/claude-opus-5.5": (4.0, 20.0),
    "anthropic/claude-fable-5.2": (8.0, 40.0),
    "anthropic/claude-fable-5.1": (10.0, 50.0),
    "anthropic/claude-fable-5": (10.0, 50.0),
    "anthropic/claude-opus-5": (5.0, 25.0),
    "anthropic/claude-opus-4.6": (5.0, 25.0),
    "anthropic/claude-sonnet-5.5": (2.0, 10.0),
    "anthropic/claude-haiku-5.5": (0.10, 0.50),
    "qwen/qwen3.8-max-0902": (2.0, 6.0),
    "qwen/qwen4-max": (1.425, 4.275),
    "qwen/qwen3.8-27b": (0.425, 2.55),
    "meta/muse-spark-1.3": (1.25, 4.25),
    "openai/gpt-6.1-terra": (1.0, 5.0),
    "openai/gpt-6-luna": (0.10, 0.50),
    "openai/gpt-5.6-luna": (0.20, 1.20),
    "z-ai/glm-5.3": (1.40, 4.40),
    "z-ai/glm-5.3-flash": (0.15, 0.50),
    "deepseek/deepseek-v4.1-flash-1017": (0.30, 1.20),
    "xiaomi/mimo-v2.6-flash": (0.14, 0.28),
    "tencent/hy4": (0.417, 1.25),
    "google/gemini-4-hydrogen": (1.5, 7.5),
    "openai/gpt-6.1-sol": (2.0, 10.0),
}

ARGON, FLASH38, OPUS55, FABLE52 = "google/gemini-4-argon", "google/gemini-3.8-flash", "anthropic/claude-opus-5.5", \
    "anthropic/claude-fable-5.2"
SONNET55, HAIKU55, QMAX, TERRA = "anthropic/claude-sonnet-5.5", "anthropic/claude-haiku-5.5", "qwen/qwen3.8-max-0902", \
    "openai/gpt-6.1-terra"
LUNA6, GLMF, GLM, DSF = "openai/gpt-6-luna", "z-ai/glm-5.3-flash", "z-ai/glm-5.3", "deepseek/deepseek-v4.1-flash-1017"
MIMOF, HYDRO = "xiaomi/mimo-v2.6-flash", "google/gemini-4-hydrogen"

# job -> tier -> [main, backup (another company)]
TABLE: dict[str, dict[str, list[str]]] = {
    # v0.999.11 the writer of every chat turn: good words AND good tool calls (it picks and fills the tools itself) -
    # chat / Hindi boards + tau2 + the agent board's "follows her" / "no invented tools" (doc 15)
    "chat":     {"ultra": [OPUS55, ARGON], "high": [HYDRO, TERRA], "medium": [GLM, DSF], "low": [DSF, GLMF]},
    "write":    {"ultra": [ARGON, OPUS55], "high": [FLASH38, QMAX], "medium": [GLM, DSF], "low": [DSF, GLMF]},
    "reason":   {"ultra": [ARGON, OPUS55], "high": [GLMF, FLASH38], "medium": [GLMF, DSF], "low": [LUNA6, HAIKU55]},
    "facts":    {"ultra": [OPUS55, ARGON], "high": [GLMF, FLASH38], "medium": [MIMOF, DSF], "low": [LUNA6, HAIKU55]},
    "extract":  {"ultra": [ARGON, OPUS55], "high": [FLASH38, QMAX], "medium": [GLMF, DSF], "low": [LUNA6, HAIKU55]},
    "image_in": {"ultra": ["anthropic/claude-fable-5", FLASH38], "high": [FLASH38, QMAX], "medium": [GLMF, FLASH38],
                 "low": [LUNA6, HAIKU55]},
    "pdf":      {"ultra": ["anthropic/claude-fable-5.1", FLASH38],
                 "high": [FLASH38, "meta/muse-spark-1.3"], "medium": ["openai/gpt-5.6-luna", FLASH38],
                 "low": [LUNA6, HAIKU55]},
    "research": {"ultra": [QMAX, "anthropic/claude-opus-4.6"], "high": [QMAX, FLASH38], "medium": [GLMF, DSF],
                 "low": [LUNA6, HAIKU55]},
    "code":     {"ultra": [OPUS55, ARGON], "high": [SONNET55, TERRA], "medium": [DSF, GLMF], "low": [MIMOF, HAIKU55]},
    "employee": {"ultra": [FABLE52, "google/gemini-4-hydrogen"], "high": [TERRA, ARGON], "medium": [DSF, "tencent/hy4"],
                 "low": [LUNA6, HAIKU55]},
    "call":     {"ultra": [ARGON, OPUS55], "high": [FLASH38, QMAX], "medium": [GLMF, DSF], "low": [HAIKU55, LUNA6]},
    "hoola_code": {"ultra": [FABLE52, "google/gemini-4-hydrogen"], "high": [TERRA, SONNET55], "medium": [DSF, "qwen/qwen3.8-27b"],
                   "low": [LUNA6, HAIKU55]},
    "web":      {"ultra": [OPUS55, "openai/gpt-6.1-sol"], "high": [SONNET55, "qwen/qwen4-max"], "medium": ["qwen/qwen4-max", DSF],
                 "low": [DSF, MIMOF]},
}

# the Box's kinds (pipeline/kinds.py) -> the job above
KIND_JOB = {"chat": "chat", "summarise": "chat", "read.long": "chat", "write": "write", "write.lang": "write",
            "reason": "reason", "facts": "facts", "extract": "extract", "read.image": "image_in", "read.pdf": "pdf",
            "research": "research", "code": "code", "tools": "employee",
            # v0.999.17 the Box's own names for these kinds (kinds.SAME): a small code fix / a translation / the planner
            "code.small": "code", "translate": "write", "plan": "reason"}

# the video studio (studio/service.py prefs): Hoola Auto's own quality ladder + how it chooses + the picture size
VIDEO = {"ultra": {"quality": "premium", "auto": "quality", "resolution": "4k"},
         "high": {"quality": "final", "auto": "quality", "resolution": "720p"},
         "medium": {"quality": "final", "auto": "value", "resolution": "720p"},
         "low": {"quality": "draft", "auto": "cheap", "resolution": "480p"}}

LABEL = {"ultra": "ULTRA", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
LINE = {"ultra": "The best models in every field. Burns credit fast: up to 20-70x MEDIUM.",
        "high": "Near the best at a fraction of the price.",
        "medium": "Good everyday quality, low cost.",
        "low": "The cheapest models that still do the job."}
ULTRA_WARNING = ("ULTRA uses the most expensive models (Claude Opus / Fable, Gemini 4 Argon). A chat reply costs about "
                 "Rs 8.5, a long AI-employee job about Rs 500-800, a 30-second 4K video about Rs 550. Credit runs "
                 "out about 20-70x faster than MEDIUM.")
# what one thing costs in each tier, Rs (docs 11-14)
COST = {"ultra": {"reply": "Rs 8.5", "employee_job": "Rs 497-794", "call_minute": "Rs 8.6", "reel_30s": "Rs 550"},
        "high": {"reply": "Rs 3.2", "employee_job": "Rs 62-77", "call_minute": "Rs 4.0", "reel_30s": "Rs 184"},
        "medium": {"reply": "Rs 0.2-2.8", "employee_job": "Rs 12", "call_minute": "Rs 2.7", "reel_30s": "Rs 79"},
        "low": {"reply": "Rs 0.1", "employee_job": "Rs 7", "call_minute": "Rs 2.6", "reel_30s": "Rs 61"}}


class TierError(ValueError):
    pass


# ---------------------------------------------------------------- the choice

def on() -> bool:
    return bool(getattr(get_settings(), "model_tiers", True))


def offered() -> tuple[bool, str]:
    if not on():
        return False, "Model tiers are switched off on this server."
    try:
        from .agent import llm
        from .agent import providers as pv
        if not pv.key_of("openrouter"):
            return False, "Model tiers need the server's OpenRouter key."
        if not llm.glm_ready() or (get_settings().chat_llm or "auto").lower() == "claude":
            return False, "Model tiers work when the chat runs through OpenRouter."
    except Exception:   # noqa: BLE001
        return False, "Model tiers need the server's OpenRouter key."
    return True, ""


def _dir() -> Path:
    d = str(getattr(get_settings(), "model_tier_dir", "") or "")
    return Path(d) if d else Path("data") / "model_tier"


def _file(tenant: str) -> Path:
    return _dir() / (re.sub(r"[^A-Za-z0-9_-]+", "_", tenant or "main")[:80] + ".json")


def chosen(tenant: str) -> str:
    """Her tier, '' = Hoola's normal setup (also when tiers are off or not offered)."""
    if not offered()[0]:
        return ""
    try:
        t = str(json.loads(_file(tenant).read_text()).get("tier") or "").lower()
    except Exception:   # noqa: BLE001
        t = ""
    if t in ORDER and locked(tenant):
        return ""                            # v0.999.25 Free = Normal only, until she buys credits
    return t if t in ORDER else ""


def locked(tenant: str) -> bool:
    """v0.999.25 HOOLA CREDITS: every tier but Normal is locked while she has no paid credits (credits on)."""
    try:
        from .credits import wallet as _cw
        return not _cw.unlocked(tenant)
    except Exception:   # noqa: BLE001
        return False


def set_tier(tenant: str, tier: str, confirm_ultra: bool = False) -> dict[str, Any]:
    ok, why = offered()
    if not ok:
        raise TierError(why)
    tier = (tier or "").strip().lower()
    if tier and tier not in ORDER:
        raise TierError("Pick ULTRA, HIGH, MEDIUM, LOW or Hoola's normal setup.")
    if tier and locked(tenant):
        raise TierError("Buy credits to use this tier. Free works on Normal.")
    if tier == "ultra" and not confirm_ultra:
        raise TierError(ULTRA_WARNING + " Choose ULTRA again with confirm to turn it on.")
    with _LOCK:
        _dir().mkdir(parents=True, exist_ok=True)
        tmp = _file(tenant).with_suffix(".tmp")
        tmp.write_text(json.dumps({"tier": tier}))
        tmp.replace(_file(tenant))
    return view(tenant)


def for_tenant() -> str:
    """The tier of whoever this work is for: the turn's tier, else the usage owner's choice (threads, studios)."""
    try:   # v0.999.25 an AI employee's work in this turn runs on its package's tier
        from .credits import wallet as _cw
        _t = _cw.TURN.get() or {}
        if _t.get("employee"):
            from . import usage as _u
            _pt = _cw.pack_tier(_u.current()[0], _t["employee"])
            if _pt:
                return _pt
    except Exception:   # noqa: BLE001
        pass
    t = NOW.get()
    if t:
        return t
    try:
        from . import usage
        return chosen(usage.current()[0])
    except Exception:   # noqa: BLE001
        return ""


# ---------------------------------------------------------------- the models

def models(tier: str, job: str) -> list[str]:
    return list((TABLE.get(job) or {}).get((tier or "").lower()) or [])


def model(tier: str, job: str) -> str:
    m = models(tier, job)
    return m[0] if m else ""


@contextlib.contextmanager
def job(name: str):
    """The calls inside are this kind of work for the door ('web' building, 'write', 'research', 'facts' ...)."""
    tok = JOB.set(name or "")
    try:
        yield
    finally:
        JOB.reset(tok)


# v0.999.23 EVERY FEATURE FOLLOWS HER TIER (owner: "CHECK EVERY CHAT SECTION TOOLS AND FEATURE DEPLOY IT EVERWHERE ---
# EXPECT ..."): a call through the shared door whose feature named no job now runs on her tier's AI-employee row (the
# desks, Kalam, SEO / social plans, enterprise papers, the rest). Not moved, as she said: a turn that already has its
# model (the chat writer, the Box's hand-over, a call's brain), Hoola PC / her PC (frozen code, feature "pc"), the
# hard-ask judge and anything else wrapped in job(OFF), and calls that must stay Claude's own (glmdoor.CLAUDE_ONLY).
# The call's voice, pictures / music / voice-over / Cinema, SEO AI visibility and embeddings never use this door.
OFF = "off"
DEFAULT_JOB = "employee"
NO_DEFAULT_FEATURES = {"pc"}


def _default_job() -> str:
    try:   # v0.999.25 an AI employee's work (after its tool ran in this turn) = the employee row, on its package's tier
        from .credits import wallet as _cw
        if (_cw.TURN.get() or {}).get("employee"):
            return DEFAULT_JOB
    except Exception:   # noqa: BLE001
        pass
    try:
        from .agent import llm
        if (llm.MODEL_NOW.get() or "").strip():
            return ""                        # the turn already runs on its own model (writer / hand-over / call brain)
    except Exception:   # noqa: BLE001
        pass
    try:
        from . import usage
        if usage.current()[1] in NO_DEFAULT_FEATURES:
            return ""
    except Exception:   # noqa: BLE001
        pass
    return DEFAULT_JOB


def door_models(media: bool = False) -> list[str]:
    """Her tier's models for the job the running feature named, else the AI-employee row ([] = OFF, a turn with its
    own model, Hoola PC, no tier, or tiers not offered)."""
    j = JOB.get()
    if j == OFF:
        return []
    if not j:
        j = _default_job()
    if not j or j not in TABLE:
        return []
    try:
        t = for_tenant()
        if not t or not offered()[0]:
            return []
    except Exception:   # noqa: BLE001
        return []
    ms = models(t, j)
    return [m for m in ms if m not in TEXT_ONLY] if media else ms


def job_model() -> str:
    """'openrouter:<id>' the door / the OpenAI-style brain must use now for a named job, '' = as before."""
    p = JOB_PICK.get()
    if p:
        return "openrouter:" + p
    ms = door_models()
    return "openrouter:" + ms[0] if ms else ""


def job_of(kind: str) -> str:
    return KIND_JOB.get(kind or "", "")


def video_prefs(tenant: str) -> dict[str, str]:
    """The video studio's starting prefs for her tier ({} = Hoola Auto as today). Her own choices win over these."""
    return dict(VIDEO.get(chosen(tenant)) or {})


def rs_step(mid: str) -> float | None:
    p = PRICE.get(mid)
    return round((20000 * p[0] + 800 * p[1]) / 1e6 * INR, 2) if p else None


def cap(mid: str) -> dict[str, float] | None:
    """OpenRouter provider.max_price for this model ($ per million tokens): 1.25 x the maker's own price."""
    if not bool(getattr(get_settings(), "model_price_cap", True)):
        return None
    p = PRICE.get((mid or "").split(":", 1)[-1] if (mid or "").startswith("openrouter:") else (mid or ""))
    if not p:
        return None
    x = float(getattr(get_settings(), "model_price_cap_x", 1.25) or 1.25)
    return {"prompt": round(p[0] * x, 4), "completion": round(p[1] * x, 4)}


def with_cap(mid: str, extra: dict) -> dict:
    """The request's extra fields with the price ceiling added (a known model only; nothing else changes)."""
    c = cap(mid)
    if not c:
        return extra
    prov = dict(extra.get("provider") or {})
    prov.setdefault("max_price", c)
    return {**extra, "provider": prov}


def apply_box(pick: dict, tier: str, kind: str, doc: dict | None, need: dict) -> dict:
    """The Box's pick for one part, replaced by her tier's models for that kind of work (those it can do)."""
    job = job_of(kind)
    if (need or {}).get("surface") == "call" and job in ("chat", "write", "extract", ""):
        job = "call"                               # a live call's brain answers fast: the tier's call model
    ids = models(tier, job) if job else []
    if not ids:
        return pick
    from .pipeline import choose as C
    mods = (doc or {}).get("models") or {}
    ok = []
    for mid in ids:
        m = {"id": mid, "route": "openrouter", "status": "ready", "level": pick.get("level_used") or need.get("level"),
             "name": mid, "points": None}
        info = mods.get(mid)
        if info is not None and C._can(m, info, kind, need).strip():
            continue
        ok.append(m)
    if not ok:
        return pick
    old = [b for b in [pick.get("model")] + list(pick.get("backups") or []) if b and b.get("id") not in ids]
    return {**pick, "model": C._public(ok[0]), "backups": [C._public(b) for b in ok[1:]] + old[:1],
            "why": list(pick.get("why") or []) + [f"her tier {LABEL[tier]}: {job}"]}


def view(tenant: str) -> dict[str, Any]:
    ok, why = offered()
    sel = chosen(tenant) if ok else ""
    tiers = []
    for t in ORDER:
        tiers.append({"id": t, "label": LABEL[t], "line": LINE[t], "selected": t == sel, "cost": COST[t],
                      "models": {j: [{"id": m, "rs_step": rs_step(m)} for m in models(t, j)] for j in TABLE},
                      "video": VIDEO[t]})
    lk = locked(tenant)
    return {"available": ok, "reason": why, "selected": sel, "tiers": tiers, "ultra_warning": ULTRA_WARNING, "locked": lk,
            "note": "Your own model in the model list always wins over the tier."}
