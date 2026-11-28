"""Paste reader: blanks in a prompt she pasted from somewhere else.

Prompts found online mark their blanks in many shapes - [[name]], {{name}}, [NAME], {Your Name}, <TOPIC>, %CITY%,
${name} or ${name:default}. Each one found becomes a named blank she fills; a blank she leaves empty stays in the text
as [Name], so the tool reading the prompt sees an open part instead of a made-up value. Nothing here calls a model.

The patterns and the false-positive rules are ported from prompts.chat's variable detector
(src/lib/variable-detection.ts, MIT licence, see THIRD_PARTY_NOTICES.md), with two additions: a Markdown link text
"[words](...)" and a ticked box "[x]" are not blanks."""
from __future__ import annotations

import re
from typing import Any

MAX_BLANKS = 12
MAX_VALUE = 120

# most specific first; ${...} is a blank too here (prompts.chat's own format)
_PATTERNS: list[tuple[str, re.Pattern[str], bool]] = [
    ("dollar_curly", re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_ ]*?)(?::([^}]*))?\}"), True),
    ("double_bracket", re.compile(r"\[\[\s*([a-zA-Z_][a-zA-Z0-9_ ]*?)(?:\s*:\s*([^\]]*?))?\s*\]\]"), True),
    ("double_curly", re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_ ]*?)(?:\s*:\s*([^}]*?))?\s*\}\}"), True),
    ("single_bracket", re.compile(r"\[([A-Z][A-Z0-9_ ]*|[A-Za-z][a-zA-Z0-9_]*(?: +[A-Za-z][a-zA-Z0-9_]*)*)\]"), False),
    ("single_curly", re.compile(r"\{([A-Z][A-Z0-9_ ]*|[A-Za-z][a-zA-Z0-9_]*(?: +[A-Za-z][a-zA-Z0-9_]*)*)\}"), False),
    ("angle_bracket", re.compile(r"<([A-Z][A-Z0-9_ ]*|[a-zA-Z_][a-zA-Z0-9_ ]*)>"), False),
    ("percent", re.compile(r"%([a-zA-Z_][a-zA-Z0-9_]*)%"), False),
]

_FALSE = set(
    "div span p a br hr img input button h1 h2 h3 h4 h5 h6 ul ol li table tr td th thead tbody form label select option "
    "textarea script style link meta head body html section article nav header footer main aside figure figcaption "
    "strong em code pre blockquote cite abbr address b i u if else for while switch case break return function class "
    "const let var import export default try catch finally throw new this null undefined true false typeof instanceof "
    "type id key value data items properties x".split())


def key_of(name: str) -> str:
    k = re.sub(r"[^a-z0-9]+", "_", str(name or "").lower()).strip("_")
    return k[:40] or "blank"


def _label(name: str) -> str:
    n = re.sub(r"[_\s]+", " ", str(name or "")).strip()
    if n.isupper() and len(n) > 1:
        n = n.lower()
    return (n[:1].upper() + n[1:])[:60] if n else "Blank"


def _in_json_string(text: str, i: int) -> bool:
    inside = False
    for j in range(i):
        if text[j] == '"' and (j == 0 or text[j - 1] != "\\"):
            inside = not inside
    return inside


def find(text: str) -> list[dict[str, Any]]:
    """Every blank-looking part, in order: {original, name, key, label, default, pattern, start, end}."""
    text = str(text or "")
    seen: list[tuple[int, int]] = []
    out: list[dict[str, Any]] = []
    for pattern, rx, has_default in _PATTERNS:
        for m in rx.finditer(text):
            a, b = m.span()
            if any(a < e and b > s for s, e in seen):
                continue
            name = m.group(1).strip()
            if len(name) < 2 or (name.lower() in _FALSE and not (name.isupper() and len(name) > 1)):
                continue
            if pattern == "angle_bracket" and not name[:1].isupper() and " " not in name:
                continue
            if pattern in ("single_curly", "single_bracket") and _in_json_string(text, a) \
                    and not name[:1].isupper() and " " not in name:
                continue
            if pattern == "single_bracket" and text[b:b + 1] == "(":      # a Markdown link's words
                continue
            default = (m.group(2) or "").strip()[:MAX_VALUE] if has_default and m.lastindex and m.lastindex >= 2 else ""
            out.append({"original": m.group(0), "name": name, "key": key_of(name), "label": _label(name),
                        "default": default, "pattern": pattern, "start": a, "end": b})
            seen.append((a, b))
    return sorted(out, key=lambda x: x["start"])


def blanks(text: str, limit: int = MAX_BLANKS) -> list[dict[str, str]]:
    """One entry per distinct blank (a name used twice is asked once): {key, label, eg}."""
    got: dict[str, dict[str, str]] = {}
    for v in find(text):
        if v["key"] not in got:
            got[v["key"]] = {"key": v["key"], "label": v["label"], "eg": v["default"]}
        elif v["default"] and not got[v["key"]]["eg"]:
            got[v["key"]]["eg"] = v["default"]
    return list(got.values())[:limit]


def fill(text: str, values: dict[str, Any] | None = None) -> dict[str, Any]:
    """Her values put into the text. An empty blank becomes [Label] (never its default, never a guess).
    Returns {text, filled: [keys], open: [labels]}."""
    text = str(text or "")
    values = {str(k): str(v or "").strip()[:MAX_VALUE] for k, v in (values or {}).items()}
    filled, open_ = [], []
    parts, last = [], 0
    for v in find(text):
        parts.append(text[last:v["start"]])
        got = values.get(v["key"], "")
        if got:
            parts.append(got)
            filled.append(v["key"])
        else:
            parts.append(f"[{v['label']}]")
            open_.append(v["label"])
        last = v["end"]
    parts.append(text[last:])
    return {"text": "".join(parts), "filled": list(dict.fromkeys(filled)), "open": list(dict.fromkeys(open_))}
