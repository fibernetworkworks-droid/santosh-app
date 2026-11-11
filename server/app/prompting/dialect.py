"""A brief -> the exact wording each Hoola engine wants. One function per engine, written from that engine's own
needs (and, for pictures, the picture-model vendor's published guide: a described scene, not keywords; positive
wording; exact words in quotes). Nothing is added that she did not see on the page, and no magic phrase ever."""
from __future__ import annotations

from typing import Any

from . import anatomy as A

DIALECT_V = {"web": "web-1", "image": "image-1", "script": "script-1"}
SIZE_WORD = {"1:1": "square", "4:5": "tall 4:5", "3:4": "tall 3:4", "9:16": "vertical 9:16", "16:9": "wide 16:9"}


def _v(b: dict[str, Any], k: str) -> str:
    return ((b.get("slots") or {}).get(k) or {}).get("value", "")


def _facts(b: dict[str, Any]) -> str:
    return "; ".join(f["text"] for f in (b.get("facts") or []) if f["kind"] != "words")


def _blanks(b: dict[str, Any]) -> str:
    return ", ".join(A.slot(b["section"], k)["label"].lower() for k in (b.get("missing") or []))


def web(b: dict[str, Any]) -> dict[str, Any]:
    lines = [b["intent"], ""]
    for key, head in (("what", "WHAT IT IS"), ("who", "WHO VISITS"), ("action", "THE ONE KEY ACTION"), ("pages", "PAGES"),
                      ("style", "STYLE"), ("content", "CONTENT TO SHOW")):
        if _v(b, key):
            lines.append(f"{head}: {_v(b, key)}.")
    if _facts(b):
        lines.append(f"FACTS (use exactly, invent nothing else): {_facts(b)}.")
    if _blanks(b):
        lines.append(f"NOT DECIDED YET (leave a clearly marked sample I can replace): {_blanks(b)}.")
    lines.append("MUST NOT: invent prices, phone numbers, reviews or awards; leave a marked blank where a fact is missing.")
    text = "\n".join(lines)[:A.SECTIONS["web"]["limit"]]
    return {"prompt": text, "fields": {}, "run": {"to": "web", "text": text, "label": "Open in Web Studio"}}


def image(b: dict[str, Any]) -> dict[str, Any]:
    style, subject = _v(b, "style") or "Picture", _v(b, "subject") or b["intent"]
    first = f"{style[0].upper() + style[1:]} of {subject}" + (f", {_v(b, 'scene')}" if _v(b, "scene") else "") + "."
    parts = [first]
    for key, head in (("composition", "Composition"), ("light", "Light"), ("colours", "Colours")):
        if _v(b, key):
            parts.append(f"{head}: {_v(b, key)}.")
    words = _v(b, "words")
    if words:
        parts.append(f'The exact words "{words}" are written on the picture, large and clearly readable, spelled exactly as given; no other text.')
    else:
        parts.append("No text, letters or logo anywhere in the picture.")
    extra = [f["text"] for f in (b.get("facts") or []) if f["kind"] != "words" and f["text"].lower() not in words.lower()]
    if extra and words:
        parts.append("Do not write any price, number or date that is not inside the quoted words.")
    size = _v(b, "size")
    text = " ".join(parts)[:A.SECTIONS["image"]["limit"]]
    ask = f"Make this picture ({SIZE_WORD.get(size, size)}):\n{text}" if size else f"Make this picture:\n{text}"
    return {"prompt": text, "fields": {"aspect": size}, "run": {"to": "chat", "text": ask, "label": "Put in the Hoola chat"}}


def script(b: dict[str, Any]) -> dict[str, Any]:
    plat, length = _v(b, "platform"), _v(b, "length")
    lines = [b["intent"], ""]
    if plat or length:
        lines.append("PLATFORM: " + ", ".join(x for x in (plat, length) if x) + ".")
    for key, head in (("audience", "AUDIENCE"), ("hook", "OPENING HOOK (first 3 seconds)"), ("message", "THE ONE MESSAGE")):
        if _v(b, key):
            lines.append(f"{head}: {_v(b, key)}.")
    if _facts(b):
        lines.append(f"FACTS (say exactly, invent no other price, number or claim): {_facts(b)}.")
    else:
        lines.append("FACTS: none given - say no price, number or offer.")
    if _v(b, "cta"):
        lines.append(f"CALL TO ACTION (the last line): {_v(b, 'cta')}.")
    if _v(b, "tone"):
        lines.append(f"TONE: {_v(b, 'tone')}.")
    text = "\n".join(lines)[:A.SECTIONS["script"]["limit"]]
    fields = {"fmt": plat, "length": length, "language": _v(b, "language"), "tone": _v(b, "tone")}
    ask = "Write this script" + (f" in {fields['language']}" if fields["language"] else "") + ":\n" + text
    return {"prompt": text, "fields": fields, "run": {"to": "chat", "text": ask, "label": "Put in the Hoola chat"}}


RENDER = {"web": web, "image": image, "script": script}


def render(brief: dict[str, Any]) -> dict[str, Any]:
    out = RENDER[brief["section"]](brief)
    out.update({"dialect": DIALECT_V[brief["section"]], "engine": A.SECTIONS[brief["section"]]["engine"],
                "chars": len(out["prompt"])})
    return out
