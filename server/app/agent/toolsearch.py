"""v0.563 CLAUDE KA AUZAAR - tools chosen the way Claude chooses them (Anthropic: "Tool search tool", custom
implementation). Before this, a Claude turn saw only the admitted families (~58 tools); every other tool was invisible
until `tool_search` ADDED its family to the request - which rewrote the tool list mid-turn (a prompt-cache rewrite,
and a changed tool set is one of the things that invalidates preserved thinking).

Now, on a Claude turn:
- the request declares EVERY tool she may use: the admitted ones load as before, all the rest go in with
  `defer_loading: true` - known to the API, not in the model's context (deferred tools do not count as input tokens and
  sit outside the cached prefix);
- the tool list is built ONCE per turn and never changes, so the cache and thinking hold for the whole turn;
- `tool_search` answers with `tool_reference` blocks; the API expands them into the full definitions and the model
  calls the tool in its next step. The search is Hoola's own: her Hinglish family words + the exact tool name + a BM25
  ranking over each tool's name, description and argument names / descriptions (the fields Claude's built-in search
  reads);
- a model / API that refuses deferred tools or tool references gets the old path back for this process (the
  refusal ladder), and a tool reference whose tool no longer exists is turned into a line of text, so an old chat can
  never be broken by a renamed tool.
Other brains (GLM / OmniRoute) never see a deferred tool or a reference.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any

log = logging.getLogger("santosh.toolsearch")

NATIVE: dict[str, Any] = {"ok": True, "turns": 0, "searches": 0, "refs": 0, "refused": 0, "dangling": 0}
MAX_REFS = 25          # a family can be big (mail 23): the whole family, then the best BM25 matches
BM25_TOP = 6
_WORD = re.compile(r"[a-z0-9]+")
_WORDS_ID = re.compile(r"[a-z][a-z0-9_]{2,}")


def on(settings, brain: str) -> bool:
    return brain == "claude" and bool(NATIVE["ok"]) and bool(getattr(settings, "tool_search_native", True))


def build(shown: list[dict]) -> list[dict]:
    """The turn's whole tool list: what is in view first (unchanged), then every other registered tool deferred."""
    from .tools import TOOLS
    have = {t.get("name") for t in shown}
    deferred = [{**t, "defer_loading": True} for t in TOOLS if t.get("name") not in have]
    return list(shown) + deferred


def loaded(tools: list[dict] | None) -> list[dict]:
    """Only the tools that are in the model's context (for size estimates and non-Claude brains)."""
    return [t for t in (tools or []) if not (isinstance(t, dict) and t.get("defer_loading"))]


# --------------------------------------------------------------------------------------------------- the search
def _doc(t: dict) -> str:
    parts = [t.get("name", "").replace("_", " "), t.get("name", ""), str(t.get("description") or "")]
    props = ((t.get("input_schema") or {}).get("properties") or {})
    for k, v in props.items():
        parts.append(k.replace("_", " "))
        if isinstance(v, dict):
            parts.append(str(v.get("description") or ""))
    return " ".join(parts).lower()


_INDEX: dict[str, Any] = {}


def _index():
    from .tools import TOOLS
    if _INDEX.get("n") == len(TOOLS):
        return _INDEX
    docs = {t["name"]: _WORD.findall(_doc(t)) for t in TOOLS if t.get("name")}
    df: dict[str, int] = {}
    for words in docs.values():
        for w in set(words):
            df[w] = df.get(w, 0) + 1
    avg = sum(len(w) for w in docs.values()) / max(1, len(docs))
    _INDEX.update(n=len(TOOLS), docs=docs, df=df, avg=avg, N=len(docs))
    return _INDEX


def bm25(query: str, limit: int = BM25_TOP, k1: float = 1.2, b: float = 0.75) -> list[str]:
    ix = _index()
    q = [w for w in _WORD.findall((query or "").lower()) if len(w) > 1]
    if not q:
        return []
    scores: list[tuple[float, str]] = []
    for name, words in ix["docs"].items():
        if not words:
            continue
        tf: dict[str, int] = {}
        for w in words:
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        for w in q:
            f = tf.get(w)
            if not f:
                continue
            idf = math.log(1 + (ix["N"] - ix["df"][w] + 0.5) / (ix["df"][w] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(words) / ix["avg"]))
        if s > 0:
            scores.append((s, name))
    scores.sort(key=lambda x: (-x[0], x[1]))
    return [n for _, n in scores[:limit]]


def find(need: str, families: set[str]) -> list[str]:
    """Tool names for `need`: a tool named exactly first, then the BM25 best, then the rest of the matched families
    (registry order) - so a big family (mail 23) never pushes the best match off the list."""
    from .tools import FAMILY_OF, TOOLS
    low = (need or "").lower()
    out: list[str] = [n for n in _WORDS_ID.findall(low) if n in FAMILY_OF]
    for n in bm25(need):
        if n not in out:
            out.append(n)
    for t in TOOLS:
        if FAMILY_OF.get(t["name"]) in families and t["name"] not in out:
            out.append(t["name"])
    return out[:MAX_REFS]


def answer(names: list[str], loaded_names: set[str]) -> list[dict]:
    """The tool_result content: one tool_reference per tool that is not already in view."""
    refs = [{"type": "tool_reference", "tool_name": n} for n in names if n not in loaded_names]
    NATIVE["refs"] += len(refs)
    NATIVE["searches"] += 1
    return refs


# --------------------------------------------------------------------------------------------- request hygiene
def _ref_text(names: list[str]) -> str:
    return "[tool_search ne yeh tools khole the: " + ", ".join(names) + "]"


def fit_refs(history: list[dict], tools: list[dict] | None, keep: bool = True) -> list[dict]:
    """A tool_reference must name a tool in THIS request's list, or the API refuses the whole call. References that
    cannot resolve (keep=False: a brain / path without tool search; or a tool renamed since) become one line of text.
    Returns the SAME list when nothing changes (the happy path stays byte-identical)."""
    names = {t.get("name") for t in (tools or []) if isinstance(t, dict)}
    changed = False
    out: list[dict] = []
    for m in history:
        c = m.get("content") if isinstance(m, dict) else None
        if not (isinstance(c, list) and m.get("role") == "user"):
            out.append(m)
            continue
        nb = []
        mchanged = False
        for blk in c:
            if isinstance(blk, dict) and blk.get("type") == "tool_result" and isinstance(blk.get("content"), list):
                inner = blk["content"]
                refs = [x for x in inner if isinstance(x, dict) and x.get("type") == "tool_reference"]
                if refs:
                    bad = [r for r in refs if not keep or r.get("tool_name") not in names]
                    if bad:   # one unresolvable reference: the whole answer becomes text (never a mixed list)
                        NATIVE["dangling"] += len(bad)
                        blk = {**blk, "content": _ref_text([str(r.get("tool_name")) for r in refs])}
                        mchanged = True
            nb.append(blk)
        if mchanged:
            changed = True
            out.append({**m, "content": nb})
        else:
            out.append(m)
    return out if changed else history


def refused(e: Exception) -> bool:
    s = str(e).lower()
    return ("400" in s or "invalid" in s) and any(k in s for k in ("defer_loading", "tool_reference",
                                                                   "tool reference", "deferred"))


def downgrade(kw: dict[str, Any]) -> dict[str, Any]:
    """The refusal ladder: the same call without deferred tools or references; off for this process."""
    NATIVE["ok"] = False
    NATIVE["refused"] += 1
    kw = dict(kw)
    kw["tools"] = loaded(kw.get("tools"))
    kw["messages"] = fit_refs(kw.get("messages") or [], [], keep=False)
    return kw
