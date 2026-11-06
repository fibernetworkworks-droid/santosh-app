"""HOOLA CODER capture - the fail-open hooks (v0.473.0).

The three boundary taps, each one wrapped so thoroughly that a memory failure is invisible to
the session it watches (the claude-mem rule: capture can never break the work):

  tool_observed    called from agent/santosh.py::_run_tool AFTER the result is scrubbed - the
                   single funnel every tool call (main agent AND team crew) passes through.
  turn_prompt      her exact ask, redacted; an empty-after-strip prompt marks the turn private.
  session_started / session_ended   chat conversation create / voice Call.run + finally.

Redaction happens HERE, before anything is spooled or stored: <private> blocks are stripped,
secret-shaped strings are masked. There is no path from a tool result to disk that skips this.
"""
from __future__ import annotations

import json
import logging
import time

from . import spool, store
from .redact import redact, redact_secrets, strip_private

log = logging.getLogger("coder.capture")

_SKIP_TOOLS = frozenset({"memory_search", "kaam_status", "TodoWrite", "AskUserQuestion"})


def _on() -> bool:
    """The kill switch read at every boundary: coder_enabled=false means nothing is written."""
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "coder_enabled", True))
    except Exception:
        return False


def _brief(args) -> str:
    try:
        return json.dumps(redact(args), ensure_ascii=False, default=str)[:1200]
    except Exception:
        return redact_secrets(str(args))[:1200]


def _line(out) -> str:
    try:
        raw = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, default=str)
    except Exception:
        raw = str(out)
    return redact_secrets(raw)[:400]


def tool_observed(tenant: str, conv: str, tool: str, args, out, ok: bool, ms: int, turn_id: str = "",
                  actor: str = "") -> None:
    """One completed tool call -> tool_uses row + spool observation event. Best-effort, always."""
    try:
        if not conv or tool in _SKIP_TOOLS or not _on():
            return
        store.ensure()
        store.note_tool_use(conv, tenant, tool, _brief(args), ok, ms, _line(out), turn_id)
        spool.spool_event("observation", {
            "conv": conv, "tenant": tenant, "tool": tool, "args": redact(args),
            "result": _line(out) if not ok else redact_secrets(
                out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, default=str))[:8000],
            "ok": bool(ok), "ms": int(ms), "turn_id": turn_id, "actor": actor,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "seq": round(time.time() * 1000),
        })
    except Exception:
        log.exception("coder capture failed (session continues)")


def turn_prompt(tenant: str, conv: str, text: str) -> None:
    """Her ask (redacted at the store). Private turns are marked, never stored with their words."""
    try:
        if not conv or not _on():
            return
        store.ensure()
        store.note_prompt(conv, strip_private(text or ""))
    except Exception:
        log.exception("coder prompt capture failed")


def session_started(tenant: str, conv: str, platform: str) -> None:
    try:
        if not conv or not _on():
            return
        store.ensure()
        store.session_started(conv, tenant, platform)
    except Exception:
        log.exception("coder session start failed")


def session_ended(tenant: str, conv: str) -> None:
    """The checkpoint trigger: mark the row completed and arm the summary call."""
    try:
        if not conv or not _on():
            return
        store.ensure()
        spool.spool_event("session_end", {"conv": conv, "tenant": tenant,
                                          "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                          "seq": round(time.time() * 1000)})
    except Exception:
        log.exception("coder session end failed")


def save_memory(tenant: str, conv: str, text: str, title: str | None = None) -> int | None:
    """The manual note (claude-mem's save_memory): a durable observation written by the agent
    itself, same redaction, same dedup ladder."""
    try:
        if not _on():
            return None
        t = strip_private(text or "").strip()
        if not t:
            return None
        store.ensure()
        return store.store_observation(conv, tenant, {
            "type": "decision", "title": (title or t)[:120], "subtitle": "", "facts": [],
            "narrative": t[:8000], "concepts": [], "files_read": [], "files_modified": [],
        }, actor="manual")
    except Exception:
        log.exception("coder save_memory failed")
        return None
