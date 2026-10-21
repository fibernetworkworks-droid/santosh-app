"""v0.91 Secrets never reach the model through a tool's answer (idea from OpenDots' computer gateway, which removes its
own tokens from anything an upstream service echoes back).

A website, an MCP server, a public API or a PC app can print back what it was sent: an Authorization header, an
error page with the request in it, a debug dump. Before any tool result goes to the chat model or the voice call,
`scrub()` replaces:
  * the exact values of this server's own keys / tokens / secrets (from settings: every field whose name says key,
    token, secret or password, 12+ characters), and
  * well-known key shapes (Anthropic / OpenAI / Google / GitHub / Slack / Stripe / Razorpay / AWS keys, JWTs,
    "Bearer <long token>", private-key blocks)
with "[key hataya]". Ordinary text, numbers and links are never touched.
"""
from __future__ import annotations

import re
import time
from typing import Any

MARK = "[key hataya]"
_NAME = re.compile(r"(key|token|secret|password)", re.I)
_SKIP_NAMES = re.compile(r"(_file|_files|_path|_header|max_tokens|_tokens$|verify_token)", re.I)
PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bsk-(?:proj-|live_|test_)?[A-Za-z0-9_\-]{24,}"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"\b(?:rk|sk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\brzp_(?:live|test)_[A-Za-z0-9]{10,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/\-]{24,}=*"),
]
_cache: tuple[float, list[str]] = (0.0, [])
STATS = {"scrubbed": 0}


def _own_secrets() -> list[str]:
    """The exact values of this server's keys (longest first), refreshed every minute."""
    global _cache
    if time.monotonic() - _cache[0] < 60:
        return _cache[1]
    vals: set[str] = set()
    try:
        from .config import get_settings
        for name, v in get_settings().model_dump().items():
            if not isinstance(v, str) or len(v.strip()) < 12 or not _NAME.search(name) or _SKIP_NAMES.search(name):
                continue
            vals.add(v.strip())
    except Exception:
        pass
    out = sorted(vals, key=len, reverse=True)
    _cache = (time.monotonic(), out)
    return out


def text(s: str) -> str:
    if not s or len(s) < 12:
        return s
    out = s
    for v in _own_secrets():
        if v in out:
            out = out.replace(v, MARK)
    for p in PATTERNS:
        if p.search(out):
            out = p.sub(lambda m: (m.group(1) + " " + MARK) if m.re.groups and m.group(1) else MARK, out)
    if out != s:
        STATS["scrubbed"] += 1
    return out


def scrub(obj: Any, _depth: int = 0) -> Any:
    """The same value with every secret replaced (dicts / lists walked; bytes and other types left as they are)."""
    if _depth > 12:
        return obj
    if isinstance(obj, str):
        return text(obj)
    if isinstance(obj, dict):
        return {k: scrub(v, _depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(v, _depth + 1) for v in obj]
    if isinstance(obj, tuple):
        return tuple(scrub(v, _depth + 1) for v in obj)
    return obj


def forget() -> None:
    """Settings changed (tests): read the key values again next time."""
    global _cache
    _cache = (0.0, [])
