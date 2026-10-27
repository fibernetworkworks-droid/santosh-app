"""v0.86 Anthropic prompt caching: the big, unchanging part of every request (the ~200 tool definitions, then the
system prompt + conversation so far inside one turn) is read from Anthropic's cache instead of being processed again.
Each agent step then starts answering much sooner (and costs less). Pure request shaping; nothing else changes."""
from __future__ import annotations

from typing import Any

_EPH = {"type": "ephemeral"}
_NO_CACHE = {"thinking", "redacted_thinking"}


def tools(defs: list[dict] | None) -> list[dict] | None:
    """Copy of the tool list with a cache breakpoint on the last tool (tools are the first part of the prompt)."""
    if not defs:
        return defs
    out = list(defs)
    out[-1] = {**out[-1], "cache_control": _EPH}
    return out


def messages(history: list[dict]) -> list[dict]:
    """Copy of the conversation with a breakpoint on its newest block: the next step of the same turn re-reads
    everything before it from the cache."""
    if not history:
        return history
    out = list(history)
    for mi in range(len(out) - 1, max(-1, len(out) - 3), -1):
        m = out[mi]
        content = m.get("content")
        if isinstance(content, str):
            if not content.strip():
                continue
            out[mi] = {**m, "content": [{"type": "text", "text": content, "cache_control": _EPH}]}
            return out
        if isinstance(content, list):
            for bi in range(len(content) - 1, -1, -1):
                b = content[bi]
                if not isinstance(b, dict) or b.get("type") in _NO_CACHE:
                    continue
                if b.get("type") == "text" and not str(b.get("text", "")).strip():
                    continue
                blocks = list(content)
                blocks[bi] = {**b, "cache_control": _EPH}
                out[mi] = {**m, "content": blocks}
                return out
    return out


def system_prompt(system: Any) -> Any:
    """v0.189 the third breakpoint: the system prompt is the biggest constant prefix of all (persona, rules, tools
    guidance, memory summary) and never changes inside a turn - cache it like everything before the newest block.
    Anthropic allows up to 4 breakpoints; we use 3 (system, last tool, newest message). A non-string system passes
    through untouched."""
    if isinstance(system, str) and system.strip():
        return [{"type": "text", "text": system, "cache_control": _EPH}]
    return system


def shape(kw: dict[str, Any], on: bool = True) -> dict[str, Any]:
    """messages.create(**kw) arguments with caching breakpoints (off -> unchanged)."""
    if not on:
        return kw
    kw = dict(kw)
    if kw.get("system") is not None:
        kw["system"] = system_prompt(kw["system"])
    if kw.get("tools"):
        kw["tools"] = tools(kw["tools"])
    if kw.get("messages"):
        kw["messages"] = messages(kw["messages"])
    return kw
