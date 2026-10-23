"""Gyaan answers: numbered sources for one turn, and the checks run on the final reply before she sees it.

- every `gyaan_khojo` call in a turn numbers its hits [1], [2] ... (continuing across calls in the same turn)
- the final reply: markdown images removed, links that came from retrieved text (not from her own message) removed - the
  EchoLeak class of attack where a poisoned document makes the answer carry a data-stealing link
- every number in a sentence that cites [n] must be in that source (or in her own words); if not, a plain note says so
- the app gets a `gyaan_sources` card with the sources the answer really cited (tap = the snippet / the file)."""
from __future__ import annotations

import re
import threading
import time
from typing import Any

from . import norm

_TURN: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
STATS = {"answers": 0, "cited": 0, "uncited": 0, "links_removed": 0, "numbers_flagged": 0}
_URL = re.compile(r"https?://[^\s)>\]]+")


def begin(conv: str) -> None:
    with _LOCK:
        _TURN.pop(conv, None)
        for k in [k for k, v in _TURN.items() if time.time() - v["at"] > 3600]:
            _TURN.pop(k, None)


def register(conv: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give this call's hits their [n] numbers; returns what the model sees (trimmed, numbered)."""
    with _LOCK:
        t = _TURN.setdefault(conv, {"hits": {}, "next": 1, "at": time.time()})
        out = []
        for h in hits:
            # the same chunk found again in this turn keeps its number
            n = next((k for k, v in t["hits"].items() if v["chunk_id"] == h["chunk_id"]), None)
            if n is None:
                n = t["next"]
                t["next"] += 1
                t["hits"][n] = h
            out.append({"n": n, "title": h["title"], "source": h["source"], "page": h.get("page") or None,
                        "date": h.get("at") or None, "text": h["text"][:900]})
        return out


def used(conv: str) -> bool:
    return bool(_TURN.get(conv, {}).get("hits"))


def finish(conv: str, text: str, user_text: str = "") -> tuple[str, list[dict[str, Any]]]:
    with _LOCK:
        t = _TURN.get(conv)
        hits = dict(t["hits"]) if t else {}
    if not hits or not text:
        return text, []
    STATS["answers"] += 1
    out = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    from_sources = {u.rstrip(".,") for h in hits.values() for u in _URL.findall(h["text"])}
    hers = set(_URL.findall(user_text or ""))

    def _md(m: re.Match) -> str:
        url = m.group(2).rstrip(".,")
        if url in from_sources and url not in hers:
            STATS["links_removed"] += 1
            return m.group(1)
        return m.group(0)
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", _md, out)

    def _bare(m: re.Match) -> str:
        url = m.group(0).rstrip(".,")
        if url in from_sources and url not in hers:
            STATS["links_removed"] += 1
            return "(link hataya)"
        return m.group(0)
    out = _URL.sub(_bare, out)
    cited = sorted({int(x) for x in re.findall(r"\[(\d{1,3})\]", out) if int(x) in hits})
    STATS["cited" if cited else "uncited"] += 1
    # numbers in a cited sentence must be in the cited source(s) or in her own question
    her_nums = set(norm.numbers(user_text))
    missing: list[str] = []
    for sent in re.split(r"(?<=[.!?।])\s+|\n", out):
        refs = [int(x) for x in re.findall(r"\[(\d{1,3})\]", sent) if int(x) in hits]
        if not refs:
            continue
        have = set().union(*[set(norm.numbers(hits[r]["text"])) for r in refs]) | her_nums
        for n in norm.numbers(re.sub(r"\[\d{1,3}\]", "", sent)):
            digits = n.replace(".", "")
            if len(digits) >= 2 and n not in have and n not in missing:
                missing.append(n)
    if missing:
        STATS["numbers_flagged"] += 1
        out = out.rstrip() + f"\n\n(Dhyaan: {', '.join(missing[:5])} source mein nahi mila; ek baar khud dekh lijiye.)"
    sources = []
    for n in cited:
        h = hits[n]
        sources.append({"n": n, "title": h["title"], "source": h["source"], "page": h.get("page") or 0, "at": h.get("at") or "",
                        "snippet": h["text"][:420], "link": h.get("link") or "", "file_id": h.get("file_id") or "",
                        "doc_id": h.get("doc_id") or ""})
    return out, sources
