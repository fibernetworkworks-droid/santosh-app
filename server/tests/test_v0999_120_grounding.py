"""v0.999.120 ULTIMATE PC PLAN P4 - seeing and pointing: click the words on the screen (OCR, free) or a described thing
(her grounding model on a GPU, off until PC_GROUNDING_URL is set)."""
from __future__ import annotations

import asyncio
import io

from PIL import Image

from app.pc import grounding as G
from app.pc import operator as op_mod


def _png(w=1280, h=800) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(b, "PNG")
    return b.getvalue()


def _ocr(words):
    """words = [(text, left, top, width, height, line_key)]"""
    d = {k: [] for k in ("text", "conf", "block_num", "par_num", "line_num", "left", "top", "width", "height")}
    for t, x, y, w, h, ln in words:
        for k, v in (("text", t), ("conf", 92), ("block_num", 1), ("par_num", 1), ("line_num", ln), ("left", x), ("top", y),
                     ("width", w), ("height", h)):
            d[k].append(v)
    return d


SCREEN = [("File", 10, 5, 30, 14, 1), ("Edit", 50, 5, 30, 14, 1),
          ("Download", 400, 300, 90, 18, 2), ("report", 495, 300, 60, 18, 2),
          ("Save", 600, 700, 40, 18, 3), ("Save", 900, 700, 40, 18, 4),
          ("Continue", 640, 500, 80, 18, 5), ("junk", 1, 1, 1, 1, 6)]


def test_find_text_matches_lines_words_and_close_spellings(monkeypatch):
    monkeypatch.setattr(G, "_data", lambda b: _ocr(SCREEN))
    m = G.find_text(b"x", "Download report")
    assert m == [{"x": 477, "y": 309, "seen": "Download report", "how": "exact"}]
    assert G.find_text(b"x", "download")[0]["how"] == "words"
    assert G.find_text(b"x", "Continu")[0]["seen"] == "Continue"        # a close spelling
    saves = G.find_text(b"x", "Save")
    assert len(saves) == 2 and G.pick(saves, None) == (None, "twins") and G.pick(saves, 2)[0]["x"] == 920
    assert G.find_text(b"x", "Checkout") == []


def test_point_answers_in_pixels_and_in_1000_space():
    assert G.parse_point("click(start_box='<|box_start|>(500,250)<|box_end|>')", 1280, 800) == (640, 200)
    assert G.parse_point("[1100, 700]", 1280, 800) == (1100, 700)
    assert G.parse_point("I cannot see it", 1280, 800) is None
    assert G.parse_point("(5000, 10)", 1280, 800) is None


def _run(name, a, monkeypatch, frame=None):
    clicks = []

    async def fake_pc(op, action, args=None, timeout=30, log=True):
        clicks.append((action, args))
        return {}
    monkeypatch.setattr(op_mod, "_pc", fake_pc)
    op = op_mod.Op(id="g1", tenant="t", conv="c", task="x")
    op.frame = frame if frame is not None else _png()
    return asyncio.run(op_mod._do(op, name, a)), clicks


def test_click_text_clicks_the_centre_and_refuses_twins(monkeypatch):
    monkeypatch.setattr(G, "_data", lambda b: _ocr(SCREEN))
    out, clicks = _run("click_text", {"text": "Download report"}, monkeypatch)
    assert out.startswith("clicked 'Download report' at (477,309)") and clicks == [("control", {"op": "click", "x": 477, "y": 309})]
    out, clicks = _run("click_text", {"text": "Save"}, monkeypatch)
    assert out.startswith("NOT clicked") and "nth=" in out and clicks == []
    out, clicks = _run("click_text", {"text": "Save", "nth": 1, "double": True}, monkeypatch)
    assert clicks == [("control", {"op": "double_click", "x": 620, "y": 709})]
    out, clicks = _run("click_text", {"text": "Pay now"}, monkeypatch)
    assert "never guess pixels" in out and clicks == []
    out, _ = _run("click_text", {"text": "x"}, monkeypatch, frame=b"")
    assert out.startswith("No screenshot yet")


def test_point_uses_her_grounding_server(monkeypatch):
    async def ask(img, desc):
        assert desc == "the red X of the dialog"
        return "(500,500)"
    monkeypatch.setattr(G, "_ask_point", ask)
    out, clicks = _run("point", {"description": "the red X of the dialog"}, monkeypatch)
    assert clicks == [("control", {"op": "click", "x": 640, "y": 400})] and out.startswith("clicked at (640,400)")


def test_tools_offered_only_when_they_can_work(monkeypatch):
    op = op_mod.Op(id="g2", tenant="t", conv="c", task="x")
    monkeypatch.setattr(G, "ocr_ready", lambda: False)
    monkeypatch.delenv("PC_GROUNDING_URL", raising=False)
    names = {t.get("name") for t in op_mod._tools_for(op)}
    assert "click_text" not in names and "point" not in names
    monkeypatch.setattr(G, "ocr_ready", lambda: True)
    monkeypatch.setenv("PC_GROUNDING_URL", "https://gpu.example/v1")
    names = {t.get("name") for t in op_mod._tools_for(op)}
    assert {"click_text", "point"} <= names
    op.bg = True                     # background mode never takes her mouse
    assert not {"click_text", "point"} & {t.get("name") for t in op_mod._tools_for(op)}
