"""v0.999.120 ULTIMATE PC PLAN P4 - seeing and pointing (docs/HOOLA_ULTIMATE_PC_PLAN.md).

The model often knows WHAT to press ("the blue Submit button", "the word Download") but guesses the pixels. Two new
screen tools turn words into a click, both on the screenshot the model just saw, both through the normal click path:
1. click_text {text, nth?, button?, double?} - OCR (tesseract on the server, free, no GPU) reads every word on the
   screenshot with its box; the text she named is matched (exact line, then words in order, then a close spelling) and
   its centre is clicked. Two equal matches and no nth = refused with both positions listed, never clicked by luck.
2. point {description, button?, double?} - a grounding model (UI-TARS 1.5 7B or any OpenAI-compatible vision model that
   answers a point) on a GPU HER server runs. OFF until PC_GROUNDING_URL is set in the VPS .env (PC_GROUNDING_MODEL,
   PC_GROUNDING_KEY there too, never in chat). It answers a point in 0-1000 space or pixels; both are understood.
Both tools are offered only when they can work (tesseract installed / the URL set), and never in background mode."""
from __future__ import annotations

import base64
import difflib
import io
import logging
import os
import re
import shutil

log = logging.getLogger("santosh.pc.grounding")

MIN_CONF = 40
ANSWER = re.compile(r"\(?\s*(\d{1,5}(?:\.\d+)?)\s*,\s*(\d{1,5}(?:\.\d+)?)\s*\)?")

CLICK_TEXT_TOOL = {"name": "click_text", "description": (
    "Click on a piece of TEXT you can see on the screenshot (a button label, a link, a menu word, a file name): the PC "
    "reads the screen's words with their positions and clicks the centre of the one you name - no pixel guessing. Use "
    "it for desktop apps and pages where page_elements / ax_snapshot do not list the thing. nth=2 picks the second of "
    "equal matches (top to bottom, left to right)."),
    "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "nth": {"type": "integer"},
                                                     "button": {"type": "string", "enum": ["left", "right"]},
                                                     "double": {"type": "boolean"}}, "required": ["text"]}}
POINT_TOOL = {"name": "point", "description": (
    "Click a thing on the screen by DESCRIBING it ('the red X at the top right of the dialog', 'the search icon'): a "
    "grounding model finds it on the screenshot and the PC clicks there. For icons and pictures without words; for "
    "words use click_text."),
    "input_schema": {"type": "object", "properties": {"description": {"type": "string"},
                                                     "button": {"type": "string", "enum": ["left", "right"]},
                                                     "double": {"type": "boolean"}}, "required": ["description"]}}


def ocr_ready() -> bool:
    try:
        import pytesseract  # noqa: F401
    except Exception:   # noqa: BLE001
        return False
    return bool(shutil.which("tesseract"))


def point_ready() -> bool:
    return bool(os.environ.get("PC_GROUNDING_URL", "").strip())


# ---------------------------------------------------------------- OCR

def _data(img_bytes: bytes) -> dict:
    """pytesseract.image_to_data as a dict (a seam for tests)."""
    import pytesseract
    from PIL import Image
    return pytesseract.image_to_data(Image.open(io.BytesIO(img_bytes)), output_type=pytesseract.Output.DICT)


def lines(img_bytes: bytes) -> list[dict]:
    """Every OCR line: text, its words (each with a box) and the line's box."""
    d = _data(img_bytes)
    rows: dict[tuple, dict] = {}
    for i, w in enumerate(d.get("text") or []):
        w = str(w or "").strip()
        try:
            conf = float(d["conf"][i])
        except (TypeError, ValueError, KeyError, IndexError):
            conf = -1
        if not w or conf < MIN_CONF:
            continue
        key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        box = (int(d["left"][i]), int(d["top"][i]), int(d["width"][i]), int(d["height"][i]))
        rows.setdefault(key, {"words": []})["words"].append({"text": w, "box": box})
    out = []
    for r in rows.values():
        ws = r["words"]
        x0 = min(b["box"][0] for b in ws)
        y0 = min(b["box"][1] for b in ws)
        x1 = max(b["box"][0] + b["box"][2] for b in ws)
        y1 = max(b["box"][1] + b["box"][3] for b in ws)
        out.append({"text": " ".join(b["text"] for b in ws), "words": ws, "box": (x0, y0, x1 - x0, y1 - y0)})
    return sorted(out, key=lambda r: (r["box"][1], r["box"][0]))


def _norm(s: str) -> str:
    return re.sub(r"[^\w]+", " ", str(s or "").lower()).strip()


def _centre(boxes: list[tuple]) -> tuple[int, int]:
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return (x0 + x1) // 2, (y0 + y1) // 2


def find_text(img_bytes: bytes, text: str) -> list[dict]:
    """Matches of `text` on the screen, best kind first: {x, y, seen, how}."""
    want = _norm(text).split()
    if not want:
        return []
    exact, seq, close = [], [], []
    for ln in lines(img_bytes):
        ws = [_norm(w["text"]) for w in ln["words"]]
        n = len(want)
        for i in range(len(ws) - n + 1):
            if ws[i:i + n] == want:
                x, y = _centre([w["box"] for w in ln["words"][i:i + n]])
                (exact if n == len(ws) else seq).append({"x": x, "y": y, "seen": ln["text"], "how": "exact" if n == len(ws) else "words"})
        joined = " ".join(ws)
        if not any(m["seen"] == ln["text"] for m in exact + seq) and \
                difflib.SequenceMatcher(None, joined, " ".join(want)).ratio() >= 0.84:
            x, y = _centre([ln["box"]])
            close.append({"x": x, "y": y, "seen": ln["text"], "how": "close"})
    return exact or seq or close


def pick(matches: list[dict], nth: int | None) -> tuple[dict | None, str]:
    if not matches:
        return None, "not found"
    if nth:
        if 1 <= nth <= len(matches):
            return matches[nth - 1], ""
        return None, f"only {len(matches)} match(es)"
    if len(matches) > 1:
        return None, "twins"
    return matches[0], ""


# ---------------------------------------------------------------- the grounding model

def parse_point(text: str, width: int, height: int) -> tuple[int, int] | None:
    """'(512,300)' / 'click(start_box='<|box_start|>(512,300)<|box_end|>')' / '[512, 300]' -> pixels. Numbers that fit
    0-1000 on a larger screen are read as UI-TARS' 0-1000 space."""
    m = ANSWER.search(str(text or ""))
    if not m:
        return None
    x, y = float(m.group(1)), float(m.group(2))
    if x <= 1000 and y <= 1000 and (width > 1000 or height > 1000):
        x, y = x / 1000 * width, y / 1000 * height
    if x < 0 or y < 0 or x > width or y > height:
        return None
    return int(round(x)), int(round(y))


async def _ask_point(img_bytes: bytes, description: str) -> str:
    """One OpenAI-compatible call to her grounding server. Tests patch this."""
    import httpx
    url = os.environ.get("PC_GROUNDING_URL", "").rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    key = os.environ.get("PC_GROUNDING_KEY", "")
    body = {"model": os.environ.get("PC_GROUNDING_MODEL", "ui-tars-1.5-7b"), "temperature": 0, "max_tokens": 64,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(img_bytes).decode()}},
                {"type": "text", "text": "Output only the click point (x,y) of: " + str(description)[:300]}]}]}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(url, json=body, headers={"Authorization": f"Bearer {key}"} if key else {})
        r.raise_for_status()
        return str(((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "")


def size_of(img_bytes: bytes) -> tuple[int, int]:
    from PIL import Image
    with Image.open(io.BytesIO(img_bytes)) as im:
        return im.size
