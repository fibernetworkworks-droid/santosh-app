"""v0.560 EK DARWAZA - one door for every specialist engine's Claude call (owner: "BUILD THE 3 FIXES" after the structure
audit showed the website / app helper did it the Claude way and the rest did not).

What every engine call gets here, the way Anthropic documents it for Claude:
- the MODEL from settings (never a model name written into the engine), with the chat model as the fallback;
- ADAPTIVE THINKING + an EFFORT per job kind (Claude decides how much to think; the job sets how hard), with ROOM for
  the thinking added to max_tokens, capped so a non-streamed call stays under the SDK's 10-minute limit;
- HER SKILLS: the engines cannot call skill_manage (no tool loop), so the top matching skill's TEXT rides in the
  system prompt - Claude's level 2 (load the full skill when it is relevant) - bounded, matched on the job's own words;
- a REFUSAL LADDER: a model / API that refuses `thinking` or `output_config` is retried once without it, and that
  field is not sent again in this process.

Usage: kw = door.shape(job, model, max_tokens, system, messages); msg = door.create(client, kw)  (or await acreate).
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("santosh.door")

# job kind -> (effort, extra room for thinking). Effort per Anthropic: low ... medium ... high ... xhigh ... max.
JOBS: dict[str, tuple[str, int]] = {
    "game_design": ("high", 6000), "game_code": ("high", 8000), "game_plan": ("medium", 3000),
    "game_review": ("medium", 3000), "game_scene": ("high", 6000),
    "cad": ("high", 8000), "cad_look": ("medium", 2500),
    "blender": ("high", 6000), "blender_look": ("medium", 2000),
    "motion": ("medium", 4000), "notebook": ("high", 6000), "studio_plan": ("high", 6000),
    "page": ("medium", 2000),
}
NONSTREAM_CAP = 21000            # the SDK refuses a non-streamed request it expects to run past 10 minutes
SKILL_CHARS = 2400               # the matched skill's text that rides into an engine's system prompt
_OFF: set[str] = set()           # fields this API / model refused once: not sent again in this process
STATS: dict[str, int] = {"calls": 0, "thinking": 0, "refused": 0, "skills": 0}


def _settings():
    from ..config import get_settings
    return get_settings()


def model_for(setting: str = "", default: str = "") -> str:
    """The model an engine runs on: its own setting, else the house's strong model, else the chat model."""
    st = _settings()
    return (getattr(st, setting, "") if setting else "") or default or \
        getattr(st, "agent_hard_model", "") or st.anthropic_model


def thinking_on() -> bool:
    return str(getattr(_settings(), "engine_thinking", "adaptive") or "off").lower() == "adaptive" and \
        "thinking" not in _OFF


def skills_for(text: str, tenant: str = "") -> str:
    """Her top matching skill, in full (bounded), for an engine that cannot read skills itself. '' when none."""
    try:
        from ..coder import inject, store
        if not inject._skills_enabled():
            return ""
        if not tenant:
            from .. import usage
            tenant = usage.current()[0] or ""
        rows = inject._matched(tenant, str(text or "")[:1200]) if tenant else []
        if not rows:
            return ""
        r = rows[0]
        body = str(r.get("body") or "")
        if not body:
            got = store.skills_search(tenant, r["name"], limit=1)
            body = str((got[0] if got else {}).get("body") or "")
        if not body:
            return ""
        store.skill_use_mark(tenant, r["name"], "shown", surface="engine")
        STATS["skills"] += 1
        return (f"\n\nHER SKILL '{r['name']}' fits this job - follow it where it applies (her saved way of working):\n"
                + body[:SKILL_CHARS])
    except Exception:
        log.debug("engine skills lookup failed", exc_info=True)
        return ""


def _text_of(messages: list[dict]) -> str:
    out = []
    for m in messages or []:
        c = m.get("content") if isinstance(m, dict) else ""
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, list):
            out += [str(b.get("text") or "") for b in c if isinstance(b, dict) and b.get("type") == "text"]
    return " ".join(out)


def shape(job: str, model: str, max_tokens: int, system: str, messages: list[dict],
          skills: bool = True, tenant: str = "") -> dict[str, Any]:
    """The request kwargs for one engine call, built the Claude way."""
    STATS["calls"] += 1
    effort, room = JOBS.get(job, ("medium", 2000))
    sys = str(system or "")
    if skills:
        sys += skills_for(_text_of(messages), tenant)
    kw: dict[str, Any] = {"model": model, "max_tokens": int(max_tokens), "messages": messages}
    if sys.strip():
        kw["system"] = sys
    if thinking_on():
        kw["thinking"] = {"type": "adaptive"}
        kw["max_tokens"] = int(max_tokens) + room
        STATS["thinking"] += 1
    if effort and "output_config" not in _OFF:
        kw["output_config"] = {"effort": effort}
    kw["max_tokens"] = min(kw["max_tokens"], NONSTREAM_CAP)
    return kw


def _to_api(kw: dict[str, Any]) -> dict[str, Any]:
    out = dict(kw)
    oc = out.pop("output_config", None)
    if oc:
        out["extra_body"] = {**(out.get("extra_body") or {}), "output_config": oc}
    return out


def _refused(e: Exception) -> str:
    s = str(e).lower()
    if "400" not in s and "invalid" not in s and "not supported" not in s and "unexpected" not in s:
        return ""
    for f in ("output_config", "effort", "thinking"):
        if f in s:
            return "output_config" if f == "effort" else f
    return ""


def _strip(kw: dict[str, Any], field: str) -> dict[str, Any]:
    kw = dict(kw)
    kw.pop(field, None)
    return kw


def create(client, kw: dict[str, Any]):
    """client.messages.create(**kw) with the refusal ladder (sync)."""
    for _ in range(3):
        try:
            return client.messages.create(**_to_api(kw))
        except Exception as e:   # noqa: BLE001
            f = _refused(e)
            if not f or f not in kw:
                raise
            _OFF.add(f)
            STATS["refused"] += 1
            log.warning("engine call refused %s, retrying without it: %s", f, str(e)[:160])
            kw = _strip(kw, f)
    return client.messages.create(**_to_api(kw))


async def acreate(client, kw: dict[str, Any]):
    """await client.messages.create(**kw) with the refusal ladder (async)."""
    for _ in range(3):
        try:
            return await client.messages.create(**_to_api(kw))
        except Exception as e:   # noqa: BLE001
            f = _refused(e)
            if not f or f not in kw:
                raise
            _OFF.add(f)
            STATS["refused"] += 1
            log.warning("engine call refused %s, retrying without it: %s", f, str(e)[:160])
            kw = _strip(kw, f)
    return await client.messages.create(**_to_api(kw))
