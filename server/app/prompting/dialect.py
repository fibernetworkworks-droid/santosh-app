"""A brief -> the exact wording each Hoola engine wants. One function per engine, written from that engine's own
needs (and, for pictures, the picture-model vendor's published guide: a described scene, not keywords; positive
wording; exact words in quotes). Nothing is added that she did not see on the page, and no magic phrase ever."""
from __future__ import annotations

from typing import Any

from . import anatomy as A

DIALECT_V = {"web": "web-1", "image": "image-1", "script": "script-1", "app": "app-1", "video": "video-1",
             "music": "music-1", "marketing": "marketing-1", "doc": "doc-1", "code": "code-1", "research": "research-1",
             "data": "data-1", "aiapp": "aiapp-1", "chat": "chat-1"}
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


def _lines(b: dict[str, Any], pairs) -> list[str]:
    return [f"{head}: {_v(b, key)}." for key, head in pairs if _v(b, key)]


def app(b: dict[str, Any]) -> dict[str, Any]:
    """App Studio's architect reads users, their main job, what is kept and how money moves (the naksha spec)."""
    lines = [b["intent"], ""] + _lines(b, (("what", "WHAT IT IS"), ("users", "WHO USES IT"),
                                           ("job", "MUST WORK ON DAY 1"), ("lists", "WHAT IT KEEPS"),
                                           ("money", "MONEY"), ("alerts", "UPDATES TO USERS"),
                                           ("platform", "PHONES"), ("language", "APP LANGUAGE")))
    if _facts(b):
        lines.append(f"FACTS (use exactly, invent nothing else): {_facts(b)}.")
    if _blanks(b):
        lines.append(f"NOT DECIDED YET (ask me before building): {_blanks(b)}.")
    lines.append("MUST NOT: invent prices, products or staff names; money goes to my own account only.")
    text = "\n".join(lines)[:A.SECTIONS["app"]["limit"]]
    return {"prompt": text, "fields": {"platform": _v(b, "platform")},
            "run": {"to": "app", "text": text, "label": "Open in App Studio"}}


VIDEO_SIZE = {"9:16": "vertical 9:16", "16:9": "wide 16:9", "1:1": "square 1:1"}


def video(b: dict[str, Any]) -> dict[str, Any]:
    """Video models want ONE shot described as a scene: subject, one action, one camera move, place, light, look.
    Length and shape are SETTINGS, never words in the prompt (said so by the engines' own guides)."""
    subject, action = _v(b, "subject") or b["intent"], _v(b, "action")
    first = subject + (f" - {action}" if action else "") + (f", {_v(b, 'place')}" if _v(b, "place") else "") + "."
    parts = [first[0].upper() + first[1:]]
    for key, head in (("camera", "Camera"), ("light", "Light"), ("style", "Look")):
        if _v(b, key):
            parts.append(f"{head}: {_v(b, key)}.")
    parts.append("One continuous shot. No text, captions or logo on screen.")
    text = " ".join(parts)[:A.SECTIONS["video"]["limit"]]
    size, length = _v(b, "size"), _v(b, "length")
    sets = ", ".join(x for x in (VIDEO_SIZE.get(size, size), length) if x)
    ask = "Make this video clip" + (f" ({sets})" if sets else "") + ". Show me the price before you make it:\n" + text
    return {"prompt": text, "fields": {"aspect": size, "seconds": _num_s(length)},
            "run": {"to": "chat", "text": ask, "label": "Put in the Hoola chat"}}


def _num_s(v: str) -> int:
    import re
    m = re.search(r"\d+", v or "")
    return int(m.group(0)) if m else 0


def music(b: dict[str, Any]) -> dict[str, Any]:
    """Music models want genre, mood, instruments, tempo and the voice as a short description; lyrics apart."""
    desc = ", ".join(x for x in (_v(b, "genre"), _v(b, "mood") and _v(b, "mood").lower() + " mood", _v(b, "instruments"),
                                 _v(b, "tempo") and _v(b, "tempo").lower() + " tempo", _v(b, "vocals"),
                                 _v(b, "language") and "sung in " + _v(b, "language")) if x)
    use = _v(b, "use")
    text = (f"{use}: " if use else "") + (desc or b["intent"])
    lyrics = _v(b, "lyrics")
    if lyrics:
        text += f'\nLYRICS (sing exactly these words): "{lyrics}"'
    elif not _v(b, "vocals").lower().startswith("instrumental"):
        text += "\nLYRICS: write short, simple lines; no brand claims, prices or numbers I did not give."
    if _v(b, "length"):
        text += f"\nLENGTH: {_v(b, 'length')}."
    text = text[:A.SECTIONS["music"]["limit"]]
    return {"prompt": text, "fields": {"length": _v(b, "length")},
            "run": {"to": "chat", "text": "Make this music. Show me the price first:\n" + text, "label": "Put in the Hoola chat"}}


CHANNEL_RULES = {
    "WhatsApp message": "Under 120 words, one clear line per idea, at most 2 emoji, end with how to stop getting messages "
                        "(Reply STOP).",
    "Email": "A subject under 45 characters, a first line that works as the preview, one button or link, short paragraphs, "
             "an unsubscribe line.",
    "SMS": "Under 160 characters in all, plain text, the sender name first.",
    "Instagram caption": "First line is the hook, under 150 words, 3 to 5 hashtags at the end.",
    "Facebook / Google ad": "A headline under 30 characters and a description under 90; no claims I did not give.",
}


def marketing(b: dict[str, Any]) -> dict[str, Any]:
    ch = _v(b, "channel")
    lines = [b["intent"], ""] + _lines(b, (("channel", "CHANNEL"), ("audience", "FOR"), ("offer", "THE OFFER / NEWS"),
                                           ("action", "WHAT THEY SHOULD DO"), ("tone", "TONE"),
                                           ("language", "LANGUAGE"), ("sender", "SIGNED AS")))
    if ch in CHANNEL_RULES:
        lines.append("RULES FOR THIS CHANNEL: " + CHANNEL_RULES[ch])
    lines.append(f"FACTS (use exactly, invent no other price, date or claim): {_facts(b)}." if _facts(b)
                 else "FACTS: none given - say no price, discount or date.")
    lines.append("Write a DRAFT only. Do not send it to anyone.")
    text = "\n".join(lines)[:A.SECTIONS["marketing"]["limit"]]
    return {"prompt": text, "fields": {"channel": ch},
            "run": {"to": "chat", "text": "Draft this message (do not send):\n" + text, "label": "Put in the Hoola chat"}}


FORMAT_ASK = {"PDF": "as a PDF", "Word document": "as a Word document", "Text in the chat": "as text in the chat"}


def doc(b: dict[str, Any]) -> dict[str, Any]:
    kind = _v(b, "kind") or "document"
    lines = [b["intent"], ""] + _lines(b, (("kind", "DOCUMENT"), ("reader", "READER"), ("purpose", "IT MUST"),
                                           ("content", "MUST INCLUDE"), ("parts", "PARTS"), ("tone", "TONE"),
                                           ("length", "LENGTH"), ("sender", "FROM")))
    if _facts(b):
        lines.append(f"FACTS AND NUMBERS (use exactly, invent nothing else): {_facts(b)}.")
    lines.append("Where a number, name or date is missing, leave a clearly marked blank like [amount] - never make one up.")
    text = "\n".join(lines)[:A.SECTIONS["doc"]["limit"]]
    fmt = _v(b, "format")
    ask = f"Make this {kind.lower()}" + (f" {FORMAT_ASK[fmt]}" if fmt in FORMAT_ASK else "") + ":\n" + text
    return {"prompt": text, "fields": {"format": fmt},
            "run": {"to": "chat", "text": ask, "label": "Put in the Hoola chat"}}


def code(b: dict[str, Any]) -> dict[str, Any]:
    """Hoola Code (Claude Code style): the task, where, what done means and the check that proves it; no role-play,
    no 'think step by step' (current models gain nothing from it)."""
    lines = [b["intent"], ""] + _lines(b, (("kind", "JOB"), ("task", "THE PROBLEM / THE ASK"), ("where", "WHERE"),
                                           ("done", "DONE WHEN"), ("check", "PROVE IT WITH"), ("rules", "RULES"),
                                           ("avoid", "DO NOT TOUCH")))
    if _blanks(b):
        lines.append(f"NOT DECIDED YET (ask me one question before you change code): {_blanks(b)}.")
    text = "\n".join(lines)[:A.SECTIONS["code"]["limit"]]
    return {"prompt": text, "fields": {}, "run": {"to": "code", "text": text, "label": "Open in Hoola Code"}}


def research(b: dict[str, Any]) -> dict[str, Any]:
    lines = [b["intent"], ""] + _lines(b, (("question", "QUESTION"), ("decision", "I WILL DECIDE"), ("parts", "ANSWER THESE"),
                                           ("sources", "TRUST"), ("region", "FOR"), ("asof", "AS OF"), ("form", "ANSWER AS")))
    lines.append("Every figure must come from a page you opened - give its link and date. Say plainly what you could not confirm.")
    text = "\n".join(lines)[:A.SECTIONS["research"]["limit"]]
    return {"prompt": text, "fields": {}, "run": {"to": "chat", "text": "Research this:\n" + text, "label": "Put in the Hoola chat"}}


def data(b: dict[str, Any]) -> dict[str, Any]:
    lines = [b["intent"], ""] + _lines(b, (("data", "DATA"), ("question", "QUESTION"), ("output", "GIVE ME"),
                                           ("period", "PERIOD"), ("checks", "MUST MATCH")))
    if _facts(b):
        lines.append(f"FIGURES I GAVE (use exactly): {_facts(b)}.")
    lines.append("Work every number out in Python on the data itself and show how; never estimate a number.")
    text = "\n".join(lines)[:A.SECTIONS["data"]["limit"]]
    return {"prompt": text, "fields": {}, "run": {"to": "chat", "text": text, "label": "Put in the Hoola chat"}}


def aiapp(b: dict[str, Any]) -> dict[str, Any]:
    """The soul of an AI that answers HER customers: role, facts, never-say, hand-off - drafted, never published here."""
    lines = [b["intent"], ""] + _lines(b, (("role", "ITS JOB"), ("business", "THE BUSINESS"), ("knows", "IT KNOWS ONLY"),
                                           ("never", "IT MUST NEVER"), ("handoff", "HAND OVER TO ME WHEN"),
                                           ("tone", "TONE"), ("language", "LANGUAGE"), ("channel", "ANSWERS ON")))
    lines.append("Answer only from these facts; when a question is not covered, say so and hand over. Never invent a price, "
                 "time or offer.")
    text = "\n".join(lines)[:A.SECTIONS["aiapp"]["limit"]]
    return {"prompt": text, "fields": {},
            "run": {"to": "chat", "text": "Plan this AI app for my customers (draft it, do not publish):\n" + text,
                    "label": "Put in the Hoola chat"}}


def chat(b: dict[str, Any]) -> dict[str, Any]:
    lines = [_v(b, "goal") or b["intent"]]
    for key, head in (("context", "Background"), ("form", "Answer as"), ("example", "Like this example"), ("avoid", "Avoid")):
        if _v(b, key):
            lines.append(f"{head}: {_v(b, key)}.")
    if _facts(b):
        lines.append(f"Use these exactly: {_facts(b)}.")
    text = "\n".join(lines)[:A.SECTIONS["chat"]["limit"]]
    return {"prompt": text, "fields": {}, "run": {"to": "chat", "text": text, "label": "Put in the Hoola chat"}}


RENDER = {"web": web, "image": image, "script": script, "app": app, "video": video, "music": music,
          "marketing": marketing, "doc": doc, "code": code, "research": research, "data": data, "aiapp": aiapp,
          "chat": chat}


def render(brief: dict[str, Any]) -> dict[str, Any]:
    out = RENDER[brief["section"]](brief)
    out.update({"dialect": DIALECT_V[brief["section"]], "engine": A.SECTIONS[brief["section"]]["engine"],
                "chars": len(out["prompt"])})
    return out
