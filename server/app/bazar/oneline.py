"""v0.774 CONNECTORS PAGE: the short one-line description shown under every connector card.

Composio's catalogue (and the featured / directory lists) carry descriptions of very different lengths - some are one
clean phrase, some are a paragraph of marketing text. The console card shows ONE calm line, so it is made here, once,
on the server (tested), and every connector list carries it as `line` beside the full `does` text:

- whitespace / markdown / links tidied, the first sentence kept;
- a leading "<App> is a / an / the ..." is dropped, so the line says what the app DOES ("Channel-based messaging
  platform" rather than "Slack is a channel-based messaging platform");
- cut at a word boundary under `limit` characters with an ellipsis, never mid-word;
- an empty description gets an honest fallback from the category, never an invented claim.
"""
from __future__ import annotations

import re

LIMIT = 90
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")          # [text](url) -> text
_URL = re.compile(r"https?://\S+")
_MARK = re.compile(r"[*_`#>]+")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])")


def oneline(text: str, name: str = "", limit: int = LIMIT, category: str = "") -> str:
    t = _LINK.sub(r"\1", str(text or ""))
    t = _URL.sub("", t)
    t = _MARK.sub("", t)
    t = re.sub(r"\s+", " ", t).strip(" -–—:;,")
    if not t or t.lower() in ("its tools", "(no description published)"):
        cat = (category or "").strip()
        return f"{cat} app" if cat else "Connect your account and Hoola works inside it"
    t = _SENT.split(t, maxsplit=1)[0].strip()
    nm = (name or "").strip()
    if nm:
        m = re.match(rf"^{re.escape(nm)}(?:\s*\([^)]*\))?\s+(?:is|are)\s+(?:an?|the)\s+(.+)$", t, re.I)
        if m and len(m.group(1)) > 8:
            rest = m.group(1)
            t = rest[0].upper() + rest[1:]
    if len(t) > limit:
        cut = t[:limit - 1]
        sp = cut.rfind(" ")
        if sp > limit * 0.55:
            cut = cut[:sp]
        t = cut.rstrip(" ,;:-–—(") + "…"
    return t.rstrip(".") if not t.endswith("…") else t
