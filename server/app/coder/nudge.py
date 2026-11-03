"""HOOLA NUDGE (v0.478.0) - the self-teaching fork, Hermes's background review ported.

Every coder_nudge_every turns (default 10, Hermes's nudge_interval) ONE quiet reflection run
wakes up BETWEEN turns, rereads the conversation's redacted digest from the vault, and writes
what it learned: durable observations (the same XML ladder the session observer uses) and,
when the stretch shows a repeatable CLASS of task, a skill (SKILL.md via skills_store).

Hermes's shape, kept and adapted (the deviations are the pinned decisions):
  fork between turns   a background asyncio task, never inside the live turn
  ONE combined pass    Hermes runs two 10-turn counters (memory + skills) with two prompts; on
                       the pinned cheap brain one combined call is the cost-right shape
  stable prefix        Hermes forks with the parent's cached system prompt to hit the same
                       prefix cache; the cheap brain costs pennies, so we take prompt STABILITY
                       (prompts.REFLECTION_SYSTEM never changes) instead of cache inheritance
  dispatch whitelist   Hermes denies non-whitelisted tools at dispatch; the fork here has NO
                       tool loop at all - its output is parsed into at most 4 writes (memory
                       rows + skill files), so nothing else is even possible
  read-before-write    an update is legal only for a skill whose name rode in the digest
  no recursion         the fork cannot spawn anything and never fires from its own writes
  cancel on live turn  Hermes waits up to 2.0s for the fork to acknowledge cancellation; voice
                       latency is sacred, so Hoola's live turn NEVER waits: a poke() stamps the
                       arrival and the fork DROPS its writes if the stamp moved (zero latency,
                       strictly safer)
  privacy              the digest is built ONLY from rows the vault already redacted; a wholly
                       <private> latest ask skips the run entirely - the privacy gate extends
                       to the fork
  same funnel          writes ride store.store_observation (dedup ladder, redaction already
                       done) with actor='nudge', and skills_store.apply (atomic, linted)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time

from . import parser, prompts, skills_store, store

log = logging.getLogger("coder.nudge")

COOLDOWN_S = 300                 # never twice within 5 minutes even if turns burn fast
DIGEST_ROWS = 24                 # Hermes _digest_history tail=24
_SKILL_RE = re.compile(r"<skill\b([^>]*)>(.*?)</skill>", re.DOTALL)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

_BG: set = set()                 # running forks (GC protection, the santosh._bg pattern)

_counts: dict[tuple[str, str], int] = {}
_last_fired: dict[tuple[str, str], float] = {}
_live_at: dict[str, float] = {}
_stats = {"runs": 0, "observations": 0, "skills": 0, "dropped": 0, "skipped": 0}


# ---------------------------------------------------------------- knobs

def _settings():
    try:
        from ..config import get_settings
        return get_settings()
    except Exception:
        return None


def armed() -> bool:
    st = _settings()
    return bool(st is not None and getattr(st, "coder_enabled", True)
                and getattr(st, "coder_nudge", False))


def _every() -> int:
    st = _settings()
    try:
        return max(2, int(getattr(st, "coder_nudge_every", 10) or 10))
    except Exception:
        return 10


def _max_writes() -> int:
    st = _settings()
    try:
        return max(1, int(getattr(st, "coder_nudge_max_writes", 4) or 4))
    except Exception:
        return 4


def stats() -> dict:
    return dict(_stats)


# ---------------------------------------------------------------- live-turn coupling

def poke(conv: str) -> None:
    """A LIVE turn began. Any fork already thinking about this conversation will see the stamp
    move and drop its writes (Hermes cancels the fork; we drop instead of waiting - zero latency)."""
    _live_at[conv] = time.time()


def reset_counter(tenant: str, conv: str) -> None:
    """Hermes's rule: the counter resets whenever skill_manage is used (a skill was just
    authored; reflecting again right away would only re-derive it)."""
    _counts.pop((tenant, conv), None)


def count_turn(tenant: str, conv: str) -> None:
    """One completed turn. Fires the fork at the interval, cooldown-guarded, background."""
    if not conv or not armed():
        return
    key = (tenant, conv)
    _counts[key] = _counts.get(key, 0) + 1
    if _counts[key] < _every():
        return
    if time.time() - _last_fired.get(key, 0.0) < COOLDOWN_S:
        return
    _counts[key] = 0
    _last_fired[key] = time.time()
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return                     # a sync caller (tests/tools): the next live turn fires it
    t = asyncio.ensure_future(reflect(tenant, conv))
    _BG.add(t)
    t.add_done_callback(_BG.discard)


# ---------------------------------------------------------------- digest (redacted rows only)

def build_digest(conv: str) -> tuple[str, str]:
    """The redacted stretch, oldest first: her asks, the tool calls, what the observer learned.
    Every line comes from the vault (already redacted at capture); raw turns never pass here."""
    lines: list[str] = []
    try:
        with store.db() as c:
            asks = c.execute("SELECT n, text FROM prompts WHERE conv=? AND private=0 "
                             "ORDER BY id DESC LIMIT ?", (conv, DIGEST_ROWS // 3)).fetchall()
            tools = c.execute("SELECT tool, line, ok FROM tool_uses WHERE conv=? "
                              "ORDER BY id DESC LIMIT ?", (conv, DIGEST_ROWS // 2)).fetchall()
        for r in reversed(asks):
            lines.append(f"[she asked] {str(r['text'])[:300]}")
        for r in reversed(tools):
            lines.append(f"[tool] {r['tool']}: {str(r['line'] or '')[:200]}"
                         + ("" if r["ok"] else " (failed)"))
    except Exception:
        log.exception("nudge digest read failed")
    last_ask = ""
    for ln in lines:
        if ln.startswith("[she asked] "):
            last_ask = ln[len("[she asked] "):]
    return "\n".join(lines), last_ask


# ---------------------------------------------------------------- the fork

async def reflect(tenant: str, conv: str) -> None:
    """One reflection run. Best-effort end to end: any failure just means nothing was learned."""
    st = _settings()
    if st is None or not armed():
        return
    try:   # the house usage gate (the observer's rule): her plan pays for her own memory
        from .. import usage
        if not usage.allowed(tenant, "coder"):
            return
    except Exception:
        pass
    try:
        store.ensure()
        if store.latest_prompt_private(conv):    # the privacy gate extends to the fork
            _stats["skipped"] += 1
            return
        digest, last_ask = build_digest(conv)
        if not digest.strip():
            _stats["skipped"] += 1
            return
        skills_now = skills_store.listing(tenant)
        stamp0 = _live_at.get(conv, 0.0)         # the stamp this run must survive
        from .observer import _call_brain        # the same cheap brain + fallback, nothing new
        out = await _call_brain(prompts.reflection_system(),
                                prompts.reflection_user(digest, skills_now, last_ask), st)
    except Exception as e:
        log.info("nudge reflect failed (%s): %s", conv, e)
        return
    text = (out or "").strip()
    if not text or parser.parse_skip(text) is not None:
        return
    # THE WRITE GATE: a live turn began while we were thinking -> drop everything. Hermes waits
    # 2.0s for the fork to notice; we never make the live turn wait, so the fork self-drops.
    if _live_at.get(conv, 0.0) != stamp0:
        _stats["dropped"] += 1
        return
    _stats["runs"] += 1
    budget = _max_writes()
    try:
        mode = None
        try:
            from .modes import load_mode
            mode = load_mode()
        except Exception:
            mode = None
        valid_types = {t["id"] for t in mode["observation_types"]} if mode else set()
        valid_concepts = set(mode["observation_concepts"]) if mode else set()
        obs = parser.parse_observations(text, valid_types, valid_concepts) or \
            parser.salvage_prose(text)
        for o in obs[:budget]:
            if store.store_observation(conv, tenant, o, actor="nudge") is not None:
                _stats["observations"] += 1
                budget -= 1
        for sk in _parse_skills(text)[:max(0, budget)]:
            action, name, desc, body = sk
            if action == "update" and not any(s["name"] == name for s in skills_now):
                continue                          # read-before-write: update only a listed skill
            if action == "update":
                try:
                    skills_store.read(tenant, name)   # the honest read: the fork opens the file
                except skills_store.SkillError:
                    continue                          # vanished between list and write: skip it
            res = skills_store.apply(tenant, [{"action": action, "name": name,
                                               "description": desc, "body": body}])
            if res.get("ok"):
                _stats["skills"] += 1
                budget -= 1
            else:
                log.info("nudge skill write refused (%s): %s", name, res.get("error"))
    except Exception:
        log.exception("nudge writes failed (session continues)")


def _parse_skills(text: str) -> list[tuple[str, str, str, str]]:
    """<skill action=".." name=".." description="..">body</skill> -> op tuples, order kept."""
    out: list[tuple[str, str, str, str]] = []
    for m in _SKILL_RE.finditer(text or ""):
        attrs = dict(_ATTR_RE.findall(m.group(1) or ""))
        action = str(attrs.get("action") or "").strip()
        name = str(attrs.get("name") or "").strip()
        desc = str(attrs.get("description") or "").strip()
        body = (m.group(2) or "").strip()
        if action in ("create", "update") and name:
            out.append((action, name, desc, body))
    return out


def reset_for_tests() -> None:
    """Test isolation: forget counters, stamps and stats."""
    _counts.clear()
    _last_fired.clear()
    _live_at.clear()
    for k in _stats:
        _stats[k] = 0
