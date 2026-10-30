"""v0.303 PREMIUM + ADVANCED CREATE: hero with the makers as tabs, sideways rails, varied art; Image: style tiles,
drawn shapes, Enhance (a picture description from the server), "Keep out of the picture"; Video: camera presets;
My creations: search + sort. Every control does real work - nothing is decoration."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _js() -> str:
    return (CON / "studio.js").read_text()


def test_image_enhance_writes_a_picture_description(monkeypatch):
    from app.studio import service as ss
    seen = {}

    async def fake_write(system, prompt, max_tokens=0):
        seen["system"], seen["prompt"] = system, prompt
        return "Brief: A clay kulhad of masala chai on a teak table, steam, warm side light"
    monkeypatch.setattr(ss, "_write", fake_write)
    r = asyncio.run(ss.improve_brief("chai poster", "Hindi", 30, "image"))
    assert r["brief"].startswith("A clay kulhad")                      # the "Brief:" label is stripped
    assert seen["system"] is ss.IMAGE_IMPROVE_SYSTEM and "picture" in seen["prompt"]
    asyncio.run(ss.improve_brief("chai ad film", "Hindi", 30))           # the video path is unchanged
    assert seen["system"] is ss.IMPROVE_SYSTEM and "seconds" in seen["prompt"]


def test_a_model_outage_is_a_plain_line(monkeypatch):
    from app.studio import service as ss

    async def broken(*a, **k):
        raise RuntimeError("401 invalid key")
    monkeypatch.setattr(ss, "_write", broken)
    with pytest.raises(ss.StudioJobError):
        asyncio.run(ss.improve_brief("chai poster", "Hindi", 30, "image"))


def test_improve_route_takes_the_kind():
    main = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text()
    assert 'kind: str = Field(default="video", pattern="^(video|image)$")' in main
    assert "ss.improve_brief)(body.brief, body.language, body.seconds, body.kind)" in main


def test_home_is_premium():
    js = _js()
    assert 'class="modes" role="tablist"' in js and "data-mode=" in js and "MODE_HINT" in js
    assert "${rail(QUICK.map(" in js and "${rail(STARTERS.map(" in js and "data-rail" in js
    assert "Math.imul(s, 16777619)" in js                               # neighbouring seeds get different palettes
    assert "menu(e.currentTarget, AGENTS.map(" in js                    # the dropdown stays for narrow screens


def test_image_and_video_controls_are_real():
    js = _js()
    assert "data-isty=" in js and "STYLE_ART" in js and "style: IMG.style" in js
    assert "ratioI(a)" in js and "data-ienh" in js and "kind: 'image'" in js
    assert "if (IMG.avoid) prompt += `\\nAvoid: ${IMG.avoid}.`" in js     # the advanced field really reaches the engine
    assert "const CAMS = [" in js and "if (cam) brief += `\\nCamera: ${cam}.`" in js


def test_library_search_and_sort():
    js = _js()
    assert 'id="libq"' in js and "LIBS = {new: 'Newest first', old: 'Oldest first', az: 'Name A–Z'}" in js
    assert "Nothing matches" in js


def test_css_is_crisp():
    css = (CON / "studio.css").read_text()
    blk = css[css.index("v0.303 PREMIUM + ADVANCED CREATE"):]
    assert ".modes{" in blk and ".rail .rtrack{" in blk and ".stys{" in blk and ".rbox{" in blk and ".libbar{" in blk
    assert "backdrop-filter" not in blk and "infinite" not in blk
