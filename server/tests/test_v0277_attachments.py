"""v0.277 ATTACHMENTS LIKE CLAUDE: her files as tiles in the composer tray and above her sent bubble, a full-screen
viewer for pictures / video, documents in the workspace reader, a snippet for text tiles."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


def test_snippet_keeps_the_first_lines_only():
    from app import chatfiles
    data = ("﻿Meeting notes\r\n" + "\n".join(f"line {i}" for i in range(40))).encode()
    s = chatfiles.snippet(data)
    assert s.startswith("Meeting notes\nline 0")
    assert s.count("\n") <= 7 and len(s) <= chatfiles.SNIPPET_CHARS


def test_text_file_gets_a_snippet_and_the_bubble_shows_it(env):
    from app import chatfiles
    out = chatfiles.store("default", "pasted-text-2026-10-30.txt", b"Diwali plan\n1. Broadcast\n2. Banner\n", "text/plain")
    assert out["media"] == "text" and out["snippet"].startswith("Diwali plan")
    shown = chatfiles.shown("default", [out["file_id"]])
    assert shown[0]["snippet"].startswith("Diwali plan") and shown[0]["name"].startswith("pasted-text")


def test_picture_keeps_its_preview_and_shape_for_the_tile(env):
    import io

    from PIL import Image

    from app import chatfiles
    buf = io.BytesIO()
    Image.new("RGB", (800, 400), (200, 90, 40)).save(buf, "PNG")
    out = chatfiles.store("default", "shop.png", buf.getvalue(), "image/png")
    m = chatfiles.shown("default", [out["file_id"]])[0]
    assert m["media"] == "image" and m["preview"] and (m["width"], m["height"]) == (800, 400)
    assert "snippet" not in m


def test_console_loads_attach_before_v2():
    html = (CON / "v2.html").read_text()
    a, v = html.index("/static/console/attach.js?v="), html.index("/static/console/v2.js?v=")
    assert a < v


def test_attach_module_shape():
    js = (CON / "attach.js").read_text()
    assert "window.HoolaAttach = ctx =>" in js
    for part in ("function tray(", "function sent(", "function view(", "function lightbox(", "function upload(",
                 "x.upload.onprogress", "data-retry", "data-rm", "/api/panel/files/"):
        assert part in js, part
    assert "localStorage" not in js and "?token" not in js         # her login never goes into a URL or storage


def test_v2_uses_the_tiles():
    js = (CON / "v2.js").read_text()
    assert "HoolaAttach({" in js and "ATT.sent(files)" in js and "ATT.tray(FILES)" in js
    assert "ATT.upload(origin, item.local" in js and "function sendOne(" in js
    assert "d._tiles?.remove()" in js                              # a taken-back message takes its tiles with it
    assert "FILE_ONLY" in js and "classList.add('fonly')" in js


def test_tile_css_is_crisp():
    css = (CON / "v2.css").read_text()
    block = css[css.index("v0.277 ATTACHMENTS LIKE CLAUDE"):]
    assert ".mua{" in block and ".albx{" in block and ".atray{" in block
    assert "backdrop-filter" not in block and "infinite" not in block   # CRISP TEXT rule


def test_js_parses():
    for f in ("attach.js", "v2.js"):
        r = subprocess.run(["node", "--check", str(CON / f)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
