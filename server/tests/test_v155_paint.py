"""v0.155 Notebook Studio pages painted by Nano Banana (NotebookLM's way) + Gemini 3.8 Flash TTS for the hosts.
No network: the image model, the read-back and the TTS are faked; the HTML designer, Pillow, Chromium and ffmpeg are real."""
import asyncio
import io
import re

import pytest

from tests.test_v155_notebook import _made, _nb, ai  # noqa: F401  (fixture)
from tests.test_life import conv_ctx


def _png(w=2752, h=1536, colour=(30, 60, 160)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(b, "PNG")
    return b.getvalue()


class FakePainter:
    """paint(): returns a picture and remembers the prompt; read_text(): 'reads' back the words the prompt asked for,
    except for planned mistakes (first try of slide 2 drops the number) and a page that never reads right (slide 3)."""

    def __init__(self):
        self.calls = []          # (prompt, aspect, kind, refs)
        self.made = {}           # picture bytes -> the prompt it was painted from (pages are painted in parallel)

    def paint(self, prompt, aspect, kind="page", refs=None, size=""):
        self.calls.append((prompt, aspect, kind, list(refs or [])))
        n = len(self.calls)
        img = _png(*((1536, 2752) if aspect == "9:16" else (2752, 1536)), colour=(n % 250, 60, 160))
        self.made[img] = prompt
        return img, "gemini-3-pro-image"

    def read_text(self, img):
        p = self.made[img]
        words = re.findall(r'^- [^:]+: "(.*)"$', p, re.M)
        if "slide 3 of" in p:
            return "Lorem ipsum"                                    # never right -> HTML designer for this slide
        if "slide 2 of" in p and "earlier try" not in p:
            return "\n".join(w.replace("₹42L", "₹24L") for w in words)   # wrong number on the first try
        return "\n".join(words)


@pytest.fixture
def painter(ai, monkeypatch):
    from app.notebook import paint
    monkeypatch.setenv("NOTEBOOK_PAINT", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    from app.config import get_settings
    get_settings.cache_clear()
    fp = FakePainter()
    monkeypatch.setattr(paint, "paint", fp.paint)
    monkeypatch.setattr(paint, "read_text", fp.read_text)
    return fp


def test_slides_are_painted_checked_and_fall_back(painter):
    from app.notebook import studio
    from PIL import Image
    ctx = conv_ctx()
    nid = _nb(ctx)
    oid = studio.start("default", ctx.conversation_id, nid, "slides", {"style": "watercolor", "language": "hi"})["id"]
    o = _made(oid)
    files = o.files
    assert "slide-01.jpg" in files and "slide-02.jpg" in files            # painted
    assert "slide-03.png" in files and "slide-03.jpg" not in files        # failed its text check twice -> HTML designer
    assert "deck.pdf" in files and "deck.pptx" in files
    d = o.data["painted"]
    assert set(d) == {"1", "2"} and d["2"]["tries"] == 2                 # slide 2 repainted once with the miss named
    prompts = [c[0] for c in painter.calls]
    assert "watercolor" in prompts[0] and "Devanagari (Hindi)" in prompts[0] and '"FNW Q3"' in prompts[0]
    second = [c for c in painter.calls if "slide 2 of" in c[0]]
    assert "earlier try" in second[1][0] and "₹42l" in second[1][0].lower()
    assert all(c[3] for c in painter.calls if "slide 1 of" not in c[0])  # every later slide had slide 1 as the style reference
    assert not [c for c in painter.calls if "slide 1 of" in c[0]][0][3]
    im = Image.open(studio.core.out_dir("default", nid, oid) / "slide-01.jpg")
    assert im.size == (1920, 1080)
    v = studio.view(o)
    assert v["cover"].split("?")[0].endswith("slide-01.jpg")
    # revise slide 2: painted again with the deck's own look (slide 1 as reference)
    n = len(painter.calls)
    out = asyncio.run(studio.revise_slides("default", nid, oid, [{"n": 2, "instruction": "chhota karo"}]))
    new = painter.calls[n:]
    assert new and all("slide 2 of" in c[0] and c[3] for c in new)
    assert out["data"]["revised"] == [2]


def test_infographic_painted_and_text_checked(painter):
    from app.notebook import studio
    ctx = conv_ctx()
    nid = _nb(ctx)
    oid = studio.start("default", ctx.conversation_id, nid, "infographic", {"orientation": "portrait"})["id"]
    o = _made(oid)
    assert "infographic.jpg" in o.files and "infographic.pdf" in o.files and "infographic.png" not in o.files
    assert o.data["image"] == "infographic.jpg" and o.data["painted"]["model"] == "gemini-3-pro-image"
    p, aspect = painter.calls[0][0], painter.calls[0][1]
    assert aspect == "9:16" and '"₹42 lakh  —  revenue"' in p and "Takeaway" in p
    assert (studio.core.out_dir("default", nid, oid) / "infographic.pdf").read_bytes()[:4] == b"%PDF"


def test_check_needs_every_number():
    from app.notebook import paint
    import app.notebook.paint as pm
    pm_read = pm.read_text
    try:
        pm.read_text = lambda img: "FNW Q3 Revenue ₹24 lakh growth"
        r = paint.check(b"x", ["FNW Q3", "Revenue ₹42 lakh"])
        assert not r["ok"] and "42" in r["missing"]
        pm.read_text = lambda img: "fnw q3\nrevenue ₹42 lakh"
        assert paint.check(b"x", ["FNW Q3", "Revenue ₹42 lakh"])["ok"]
        pm.read_text = lambda img: None                                   # could not read: not blocked
        assert paint.check(b"x", ["anything"])["ok"]
    finally:
        pm.read_text = pm_read


def test_new_tts_gets_styles_tags_and_old_tts_gets_plain_text(ai, monkeypatch):
    from app.notebook import media, studio
    from app.notebook import service as ns
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setenv("NOTEBOOK_TTS_MODEL", "gemini-3.8-flash-tts")
    from app.config import get_settings
    get_settings.cache_clear()
    script = ("Ravi [excited, warm]: Namaste! <laugh> Aaj FNW ki baat.\nPriya [curious]: Revenue kitna? |haan|\n"
              "Ravi: 42 lakh. <short pause> 18 percent zyada.\nPriya [impressed]: Wah!")

    async def fake(system, prompt, max_tokens=4000):
        if "podcast scripts" in system:
            return script
        return await ai(system, prompt, max_tokens)
    monkeypatch.setattr(ns, "_llm", fake)
    seen = []
    monkeypatch.setattr(media, "tts_turns", lambda turns, voices=None, voice="", style="": seen.append((turns, voices)) or b"\x01\x00" * 24000)
    old = []
    monkeypatch.setattr(media, "tts_chunk", lambda text, voices=None, voice="": old.append(text) or b"\x01\x00" * 24000)
    media._NEW_TTS_OFF["until"] = 0
    ctx = conv_ctx()
    nid = _nb(ctx)
    oid = studio.start("default", ctx.conversation_id, nid, "audio", {})["id"]
    o = _made(oid)
    turns, voices = seen[0]
    assert voices == {"Ravi": "Charon", "Priya": "Kore"} and not old
    assert turns[0] == {"speaker": "Ravi", "style": "excited, warm", "text": "Namaste! <laugh> Aaj FNW ki baat."}
    assert turns[2]["style"] == ""
    assert "<laugh>" not in o.data["script"] and "[excited" not in o.data["script"] and o.data["script"].startswith("Ravi: Namaste!")
    # the new TTS refusing -> the older one, with the tags taken out (it would read them aloud)

    def boom(*a, **k):
        raise RuntimeError("400 unknown model")
    monkeypatch.setattr(media, "tts_turns", boom)
    media._NEW_TTS_OFF["until"] = 0
    oid2 = studio.start("default", ctx.conversation_id, nid, "audio", {})["id"]
    _made(oid2)
    assert old and "<laugh>" not in old[0] and "|haan|" not in old[0] and "Ravi: Namaste!" in old[0]
    media._NEW_TTS_OFF["until"] = 0
