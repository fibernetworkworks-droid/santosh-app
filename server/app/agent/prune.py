"""v0.189 Context hygiene for long turns: old tool results leave the model's request, the newest step stays whole.

Why: every tool result is capped at 6,000 characters when it is born (`santosh._short`), but it then sits in the
history FOREVER at that size - and the history rides into every one of the up-to-24 (goal mode: 80) model calls of
a turn. A research turn that touched 15 pages carries ~90 KB of stale page text into every later call, and the
production brain (no prompt cache) pays for it in TTFT every single step. The dsh harness solves exactly this with
its tool-result pruner (trim >8192 chars to head 4096 + tail 1024, newest untouched); Claude Code microcompacts the
same way. This is that idea, sized for Hoola:

- results of the NEWEST step (the last assistant->tool_result pair) stay exactly as they are: the model is about
  to reason over them;
- every OLDER tool_result string longer than PRUNE_OLD_RESULT_CHARS keeps its head and tail and a one-line marker
  in between - the facts she asked about were already used and answered in the assistant messages that followed;
- her own messages (plain text, and the memory / goal / kaam blocks) are never touched;
- pure projection: the history list and every dict inside it are shared with `_save` and the cache shaper, so
  pruned blocks are COPIES, never in-place edits. Calling it twice returns the same shape (idempotent).

The pruner never sees the database: `_save` has already stored the full results before the next step begins, and
the next turn reloads them from the DB fresh. Nothing is lost; the model just stops re-reading old middle sections.
"""
from __future__ import annotations

import os

MARK = "\n[…beech ka hissa hata diya gaya hai; poora natija pehle hi padh liya gaya tha…]\n"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except Exception:
        return default


OLD_RESULT_MAX = _env_int("PRUNE_OLD_RESULT_CHARS", 3500)   # older steps: trim above this
OLD_KEEP_HEAD = _env_int("PRUNE_OLD_HEAD_CHARS", 2800)
OLD_KEEP_TAIL = _env_int("PRUNE_OLD_TAIL_CHARS", 500)
STATS: dict[str, int] = {"calls": 0, "trimmed": 0, "chars_saved": 0}


def _trim(text: str) -> str:
    head, tail = OLD_KEEP_HEAD, OLD_KEEP_TAIL
    if len(text) <= head + tail + len(MARK) + 100:
        return text
    return text[:head] + MARK + (text[-tail:] if tail else "")


def _has_tool_result(content) -> bool:
    return isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content)


def prune_history(history: list[dict]) -> list[dict]:
    """The same conversation with old, big tool results shortened. A new list; the input is left untouched."""
    STATS["calls"] += 1
    n = len(history)
    out: list[dict] = []
    for i, m in enumerate(history):
        if not isinstance(m, dict):
            out.append(m)
            continue
        content = m.get("content")
        if m.get("role") != "user" or not _has_tool_result(content):
            out.append(m)
            continue
        if i >= n - 2:                 # the newest step's results: the model is about to use them
            out.append(m)
            continue
        blocks: list = []
        changed = False
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_result" and isinstance(b.get("content"), str) \
                    and len(b["content"]) > OLD_RESULT_MAX:
                new = _trim(b["content"])
                if new != b["content"]:
                    STATS["trimmed"] += 1
                    STATS["chars_saved"] += len(b["content"]) - len(new)
                    blocks.append({**b, "content": new})
                    changed = True
                    continue
            blocks.append(b)
        out.append({**m, "content": blocks} if changed else m)
    return out
