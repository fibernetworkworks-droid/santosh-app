"""HOOLA CODER observer - the note-taker engine (v0.473.0).

The claude-mem worker loop, ported to one async slot in the house worker:

  drain    -> the spool is the durable hand-off; events are grouped per conversation
  observe  -> batches of tool events ride ONE stateful conversation with the cheap brain
              (the RAM history is per-session; overflow recycles the oldest turns; a batch is
              confirmed only on parseable output - one fresh-context retry, then the batch is
              dropped and the next one moves on; nothing ever blocks a session for memory)
  summarize -> at session end, one checkpoint call writes request/investigated/learned/completed/
              next_steps (exactly one per conversation, rewritten each time)
  store    -> parser -> redaction already happened at capture -> store_observation (dedup ladder)

Failure ladder (all fail-open): no brain configured -> events stay spooled; model error -> batch
stays pending for the next tick; 3 consecutive failures -> the session parks for 10 minutes;
noise answers -> the batch is consumed for free. The spool file is consumed ONLY after the
observation row is committed, so a crash replays, never loses.
"""
from __future__ import annotations

import logging
import time

from . import capture, parser, prompts, spool, store
from .modes import load_mode

log = logging.getLogger("coder.observer")

MAX_CONVERSATION_CHARS = 400_000
FAILS_BEFORE_PARK = 3
PARK_S = 600
HISTORY_TAIL_FOR_SUMMARY = 24_000

_sessions: dict[str, dict] = {}          # conv -> state (RAM only; the spool is the durable layer)


def _session(conv: str, tenant: str) -> dict:
    s = _sessions.get(conv)
    if s is None:
        s = {"history": [], "pending": [], "end_files": [], "summary": False, "fails": 0,
             "parked_until": 0.0, "tenant": tenant, "seeded": False}
        _sessions[conv] = s
    if tenant:
        s["tenant"] = tenant
    return s


def _seed(s: dict, system: str) -> None:
    if not s["seeded"]:
        s["history"] = [{"role": "system", "content": system}]
        s["seeded"] = True


def _recycle(s: dict, system: str) -> None:
    """Overflow: keep the system prefix and the newest turns, note the trim. The system marker
    stays FIRST - the newest-first walk collects only real turns."""
    tail: list[dict] = []
    total = 0
    for m in reversed(s["history"]):
        if m["role"] == "system":
            continue
        if total + len(m["content"]) > MAX_CONVERSATION_CHARS // 2:
            break
        tail.append(m)
        total += len(m["content"])
    tail.reverse()
    s["history"] = [{"role": "system", "content": system}] + tail + \
        [{"role": "user", "content": "(earlier observed events were trimmed to fit)"}]


async def _call_brain(system: str, user: str, settings) -> str:
    """The cheapest existing path - the pakka._ask pattern: cheap brain first, Claude fallback.
    Tests inject here (monkeypatch observer._call_brain)."""
    from ..agent import llm
    msgs = [{"role": "user", "content": [{"type": "text", "text": user}]}]
    cheap = llm.cheap_brain()
    if cheap:
        try:
            blocks, _, _ = await llm.openai_create(cheap, system, [], msgs, prompts.MAX_OUTPUT_TOKENS)
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except Exception as e:
            log.info("coder cheap brain failed: %s", e)
    if getattr(settings, "anthropic_api_key", ""):
        from ..agent.santosh import get_client
        resp = await get_client().messages.create(model=settings.anthropic_model,
                                                  max_tokens=prompts.MAX_OUTPUT_TOKENS, system=system,
                                                  messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    raise RuntimeError("no coder brain available")


def _store_observations(conv: str, tenant: str, text: str, mode: dict, turn_id: str, actor: str,
                        discovery_tokens: int) -> int:
    if store.latest_prompt_private(conv):        # the whole-turn privacy gate (safe side)
        return 0
    valid_types = {t["id"] for t in mode["observation_types"]}
    valid_concepts = set(mode["observation_concepts"])
    obs = parser.parse_observations(text, valid_types, valid_concepts) or parser.salvage_prose(text)
    n = 0
    for o in obs:
        if store.store_observation(conv, tenant, o, turn_id=turn_id, actor=actor,
                                   discovery_tokens=discovery_tokens) is not None:
            n += 1
    return n


def _history_text(s: dict) -> str:
    return "\n".join(m["content"] for m in s["history"] if m["role"] == "user")[-HISTORY_TAIL_FOR_SUMMARY:]


def _last_ask(conv: str) -> str:
    try:
        with store.db() as c:
            r = c.execute("SELECT text FROM prompts WHERE conv=? AND private=0 ORDER BY id DESC LIMIT 1",
                          (conv,)).fetchone()
            return r[0] if r else ""
    except Exception:
        return ""


def _bump_session_observed(conv: str, n: int) -> None:
    try:
        with store.db(write=True) as c:
            c.execute("UPDATE sessions SET observed = observed + ? WHERE conv=?", (n, conv))
    except Exception:
        log.exception("coder session bump failed")


_SWEPT = {"done": False}


def _sweep_incognito() -> int:
    """v0.603 INCOGNITO SACH, once per process: before this version an incognito chat's asks, tool rows
    and observations reached the vault (the capture boundary never asked). Every vault conversation
    that is an incognito chat is forgotten whole. Cheap (one id list), idempotent, never raises."""
    if _SWEPT["done"]:
        return 0
    _SWEPT["done"] = True
    n = 0
    try:
        for conv in store.known_convs():
            if capture.secret(conv):
                got = store.forget_conv(conv)
                n += 1
                log.info("coder: incognito chat %s forgotten from the vault %s", conv, got)
    except Exception:
        log.exception("coder incognito sweep failed")
    return n


async def tick(settings, max_sessions: int = 3) -> dict:
    """One worker pass: drain the spool, observe what is ready, summarize what ended."""
    stats = {"drained": 0, "observed": 0, "summaries": 0, "noise": 0, "skipped": 0}
    if not getattr(settings, "coder_enabled", True):
        return stats
    try:
        store.ensure()
        spool.sweep()
    except Exception:
        log.exception("coder store ensure failed")
        return stats
    _sweep_incognito()
    events = spool.drain()
    stats["drained"] = len(events)
    now = time.time()
    touched: list[str] = []
    for ev in events:
        conv = str(ev.get("conv") or "")
        if not conv or spool.is_consumed(ev["_file"]):
            stats["skipped"] += 1
            continue
        if capture.secret(conv):               # v0.603 an incognito chat's event is dropped unread
            spool.consume(ev["_file"])
            stats["skipped"] += 1
            continue
        s = _session(conv, str(ev.get("tenant") or ""))
        if ev.get("kind") == "observation":
            s["pending"].append(ev)
        elif ev.get("kind") == "session_end":
            store.session_ended(conv)          # the row is closed even if the summary call fails
            s["end_files"].append(ev["_file"])
            s["summary"] = True
        elif ev.get("kind") == "summarize":
            s["end_files"].append(ev["_file"])
            s["summary"] = True
        touched.append(conv)

    # ---- observe: conversations with pending events, oldest first, bounded per tick
    work = [c for c in dict.fromkeys(touched)
            if _sessions[c]["pending"] and _sessions[c]["parked_until"] <= now][:max_sessions]
    for conv in work:
        s = _sessions[conv]
        try:   # the house usage gate (the enrich pattern): her plan pays for her own memory
            from .. import usage
            if not usage.allowed(s["tenant"], "coder"):
                continue
        except Exception:
            pass
        mode = load_mode()
        _seed(s, prompts.observer_system(mode))
        batch = s["pending"][:int(getattr(settings, "coder_batch_max", 6) or 6)]
        sys_p, user_p = prompts.observation_prompt(batch, mode)
        try:
            out = await _call_brain(sys_p, user_p, settings)
        except Exception as e:
            s["fails"] += 1
            log.info("coder observe failed (%s): %s", conv, e)
            if s["fails"] >= FAILS_BEFORE_PARK:
                s["parked_until"] = now + PARK_S
                s["fails"] = 0
            continue
        text = (out or "").strip()
        noise = not text or (parser.parse_skip(text) is not None
                             and not parser.parse_observations(text))
        if noise:
            for ev in batch:                       # pure noise: consume for free, keep talking
                spool.consume(ev["_file"])
            s["pending"] = s["pending"][len(batch):]
            stats["noise"] += len(batch)
        else:
            n = _store_observations(conv, s["tenant"], text, mode, str(batch[0].get("turn_id") or ""),
                                    str(batch[0].get("actor") or ""),
                                    discovery_tokens=(len(sys_p) + len(user_p) + len(text)) // 4)
            if n:
                stats["observed"] += n
                _bump_session_observed(conv, n)
            for ev in batch:                       # committed first, consumed after: crash = replay
                spool.consume(ev["_file"])
            s["pending"] = s["pending"][len(batch):]
            s["fails"] = 0
        s["history"].append({"role": "user", "content": user_p[-8000:]})
        s["history"].append({"role": "assistant", "content": text[:4000] or "(noise)"})
        if sum(len(m["content"]) for m in s["history"]) > MAX_CONVERSATION_CHARS:
            _recycle(s, prompts.observer_system(mode))

    # ---- summarize: conversations flagged and fully drained
    for conv in dict.fromkeys(touched):
        s = _sessions.get(conv)
        if not s or not s["summary"] or s["pending"] or s["parked_until"] > now:
            continue
        if getattr(settings, "coder_observe", True) is False:
            continue
        sys_p, user_p = prompts.summary_prompt(_last_ask(conv), _history_text(s))
        try:
            out = await _call_brain(sys_p, user_p, settings)
        except Exception as e:
            log.info("coder summary failed (%s): %s", conv, e)
            for f in s["end_files"]:    # never nag forever: this checkpoint is dropped, the
                spool.consume(f)        # next session_end re-arms a fresh one
            s["end_files"] = []
            s["summary"] = False
            continue
        summ = parser.parse_summary(out or "")
        if summ:
            store.store_summary(conv, s["tenant"], summ)
            stats["summaries"] += 1
        s["summary"] = False
        for f in s["end_files"]:
            spool.consume(f)
        s["end_files"] = []
    return stats


def reset_for_tests() -> None:
    """Test isolation: the RAM session state forgets every conversation."""
    _sessions.clear()
    _SWEPT["done"] = False
    capture._SECRET.clear()
