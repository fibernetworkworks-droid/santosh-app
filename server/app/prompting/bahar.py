"""P11 BAHAR (docs/HOOLA_PROMPTING_PLAN.md part 3 shelf 14 + part 12 decision 4): a brief written out for an AI tool she
uses OUTSIDE Hoola - ChatGPT, Claude, Gemini, or any picture tool. Copy only: nothing is sent anywhere, and no ledger row
is written, because Hoola cannot see or judge a result made outside Hoola (the page says so).

Each wording follows that vendor's OWN published prompting guide, in the parts every one of them states:
  ChatGPT (OpenAI prompt engineering guide): instructions first, context separated by clear delimiters, say the output
          format, be specific about length and audience.
  Claude  (Anthropic prompt engineering docs): clear direct instructions, the parts wrapped in XML tags, say what to do
          rather than what not to do.
  Gemini  (Google's prompting guide): persona, task, context, format as named parts.
  Picture (the picture vendor guide Hoola's own image dialect already follows): a described scene in full sentences,
          positive wording, exact words in quotes, the shape said in words.
Nothing is added that she did not see on the page, and no magic phrase ever. Her facts go in unchanged; a part she
left empty is marked [fill in: ...] so the outside tool does not invent it."""
from __future__ import annotations

from typing import Any

from . import anatomy as A

TARGETS: dict[str, dict[str, Any]] = {
    "chatgpt": {"label": "ChatGPT", "kinds": "text"},
    "claude": {"label": "Claude", "kinds": "text"},
    "gemini": {"label": "Gemini", "kinds": "text"},
    "picture": {"label": "Any picture tool", "kinds": "picture"},
}
PICTURE_SECTIONS = ("image", "video")
NOTE = ("Copy only. Nothing is sent from here. Hoola cannot see or check a result made in another tool, so it is not "
        "counted in your results.")


def targets(section: str) -> list[dict[str, str]]:
    out = []
    for k, t in TARGETS.items():
        if t["kinds"] == "picture" and section not in PICTURE_SECTIONS:
            continue
        out.append({"key": k, "label": t["label"]})
    return out


def _parts(b: dict[str, Any]) -> list[tuple[str, str]]:
    """(label, value) for every filled part in the section's own order, then [fill in] for each missing required part."""
    sec = b["section"]
    slots = b.get("slots") or {}
    out = []
    for sl in A.slots(sec):
        v = (slots.get(sl["key"]) or {}).get("value", "")
        if v:
            out.append((sl["label"], str(v)))
    for k in b.get("missing") or []:
        sl = A.slot(sec, k)
        if sl:
            out.append((sl["label"], f"[fill in: {sl['label'].lower()}]"))
    return out


def _facts(b: dict[str, Any]) -> list[str]:
    return [f["text"] for f in (b.get("facts") or []) if f.get("text")]


def _chatgpt(b, label, parts, facts):
    lines = [f"Task: {b['intent']}", "", '"""']
    lines += [f"{k}: {v}" for k, v in parts]
    lines.append('"""')
    if facts:
        lines += ["", "Use these facts exactly as written, and do not invent any other prices, numbers or names:"]
        lines += [f"- {f}" for f in facts]
    lines += ["", f"Give the result as {A.SECTIONS[b['section']]['makes']}. Where something is marked [fill in], "
              "leave it as a clear blank instead of guessing."]
    return "\n".join(lines)


def _claude(b, label, parts, facts):
    lines = [f"Please make {A.SECTIONS[b['section']]['makes']}.", "", "<task>", b["intent"], "</task>", "", "<details>"]
    lines += [f"{k}: {v}" for k, v in parts]
    lines.append("</details>")
    if facts:
        lines += ["", "<facts>"] + facts + ["</facts>", "",
                  "Use the facts inside <facts> exactly as written. Use only the prices, numbers and names given here."]
    lines += ["", "Where something is marked [fill in], leave it as a clear blank."]
    return "\n".join(lines)


def _gemini(b, label, parts, facts):
    lines = [f"Persona: you are helping a small business owner make {A.SECTIONS[b['section']]['makes']}.", "",
             f"Task: {b['intent']}", "", "Context:"]
    lines += [f"- {k}: {v}" for k, v in parts]
    if facts:
        lines += ["- Facts to keep exactly as written: " + "; ".join(facts)]
    lines += ["", f"Format: {A.SECTIONS[b['section']]['makes']}, ready to use. Use only the prices, numbers and names "
              "given here; leave anything marked [fill in] as a clear blank."]
    return "\n".join(lines)


SHAPE_WORD = {"1:1": "a square picture", "4:5": "a tall 4:5 picture", "9:16": "a tall 9:16 vertical picture",
              "16:9": "a wide 16:9 picture", "3:4": "a tall 3:4 picture"}


def _picture(b, label, parts, facts):
    slots = b.get("slots") or {}
    v = lambda k: str((slots.get(k) or {}).get("value", ""))   # noqa: E731
    sentences = []
    subject = v("subject") or b["intent"]
    head = subject[0].upper() + subject[1:] if subject else subject
    scene = v("scene") or v("action")
    sentences.append(f"{head}{', ' + scene if scene else ''}.")
    if v("style"):
        sentences.append(f"Style: {v('style').lower()}.")
    for k, word in (("composition", "Layout"), ("light", "Light"), ("colours", "Colours"), ("camera", "Camera")):
        if v(k):
            sentences.append(f"{word}: {v(k)}.")
    if v("words"):
        sentences.append(f'The picture shows these exact words: "{v("words")}".')
    if v("size") in SHAPE_WORD:
        sentences.append(f"Make it {SHAPE_WORD[v('size')]}.")
    elif v("size"):
        sentences.append(f"Shape: {v('size')}.")
    if v("length"):
        sentences.append(f"Length: {v('length')}.")
    return " ".join(sentences)


WRITE = {"chatgpt": _chatgpt, "claude": _claude, "gemini": _gemini, "picture": _picture}


def export(brief: dict[str, Any], target: str) -> dict[str, Any]:
    from . import brief as B
    if target not in TARGETS:
        raise ValueError("Choose ChatGPT, Claude, Gemini or a picture tool.")
    b = B.validate(brief)
    if TARGETS[target]["kinds"] == "picture" and b["section"] not in PICTURE_SECTIONS:
        raise ValueError("A picture tool takes picture and video-clip prompts only.")
    prompt = WRITE[target](b, TARGETS[target]["label"], _parts(b), _facts(b))
    return {"target": target, "label": TARGETS[target]["label"], "prompt": prompt, "chars": len(prompt), "note": NOTE,
            "blanks": [A.slot(b["section"], k)["label"] for k in (b.get("missing") or []) if A.slot(b["section"], k)]}
