"""v0.777 HOOLA DESIGN, phase D4 "hand-off" (docs/HOOLA_DESIGN_PLAN.md): hd-export.js + design-export.css.

The real test is JavaScript - server/tests/web/design_export_test.js - and runs in a REAL browser (node + playwright,
Chromium) against the real editor with the mock server of design_ui_test.js: PNG / JPG export sizes and pixel colours
(a 1080 x 1080 frame at 1x is 1080 x 1080 px), the refusal of a picture too big for a browser, the Export section and
the Export dialog through their controls, Copy as PNG, an SVG export imported again (same geometry), a hostile SVG
(nothing runs, nothing is fetched), a real-world style SVG compared number by number and pixel by pixel with the
browser's own drawing of it, picture import (picker, drop, paste, one undo step), the Inspect tab with CSS / Flutter /
Tailwind for an auto layout card (the CSS is put on real elements and compared with the canvas), and Save a copy /
Import a copy (.hoola.json).

This file runs it so CI covers it, and then opens what the browser DOWNLOADED with Python's own readers: the ZIP with
zipfile (CRC check, UTF-8 names), the PDF with pypdf (pages at the frames' sizes in points, one JPEG each at 2x), the
PNGs inside the ZIP by their headers, and the .hoola.json copy. It skips cleanly where node, playwright or Chromium is
missing."""
import io
import json
import os
import re
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
JS_TEST = HERE / "web" / "design_export_test.js"
DESIGN = HERE.parent / "app" / "static" / "console" / "design"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")


def test_the_file_is_a_plain_strict_script():
    text = (DESIGN / "hd-export.js").read_text(encoding="utf-8")
    assert "'use strict';" in text and text.rstrip().endswith("})();")
    assert "eval(" not in text and "new Function" not in text and "import(" not in text          # strict CSP: script-src 'self'
    assert "new Worker" not in text and "importScripts" not in text                               # no worker (a blob: worker is not allowed)
    assert "innerHTML" not in text and "outerHTML" not in text and "document.write" not in text and "insertAdjacentHTML" not in text
    assert text.isascii(), "keep the source ASCII (\\uXXXX escapes), it must not depend on the served charset"
    # the SVG is read from an INERT document made by DOMParser and never adopted into the page
    assert "new DOMParser().parseFromString(text, 'image/svg+xml')" in text
    assert "importNode" not in text and "adoptNode" not in text and "createContextualFragment" not in text
    # no attribute that can carry code is ever read: the importer only asks for the names in its own lists
    reader = text[text.index("function svgRead("):text.index("const ROOT_STYLE")]
    asked = set(re.findall(r"getAttribute(?:NS)?\((?:[A-Z_]+|'[^']*'), ?'([^']+)'\)|getAttribute\('([^']+)'\)", reader))
    names = {a or b for a, b in asked}
    assert names and not any(n.lower().startswith("on") for n in names), names
    assert "'script'" not in reader and "script: 1" in text[text.index("const NEVER"):text.index("const QUIET")]
    # the only addresses it follows: '#id' inside the same file, and a picture in a data: address
    assert "/^data:(image\\/(?:png|jpe?g|webp|gif))" in reader and "fetch(" not in reader and "XMLHttpRequest" not in text
    # the API other phases and the tests use
    api = text[text.index("HD.handoff = {"):]
    for name in ("zip", "pdf", "crc32", "renderOne", "plan", "exportNow", "exportDialog", "copyPng", "copySvg", "svgRead", "importSvg",
                 "importImages", "placeFiles", "saveCopy", "importCopy"):
        assert re.search(rf"\b{name}: ", api), f"HD.handoff.{name} is part of the API"
    for hook in ("ui.hook('export'", "ui.hook('exportSection'", "ui.hook('importSvg'", "ui.registerPanel('right', 'inspect'"):
        assert hook in text, hook
    # the token travels as a header or a WebSocket subprotocol, never in an address
    assert "token=" not in text and "'hoola-key.' + token" in text
    css = (DESIGN / "design-export.css").read_text(encoding="utf-8")
    assert css.isascii() and "backdrop-filter" not in css and "text-transform:uppercase" not in css
    assert not re.search(r"font-weight:\s*(700|800|900|bold)", css), "no weight above 600"
    assert not re.search(r"font-size:\s*(\d|1[01])(\.\d+)?px", css) and not re.search(r"font:\s*(\d|1[01])(\.\d+)?px", css), "nothing under 12px"
    assert all(sel.startswith((".hdx-", "/*")) for sel in re.findall(r"^([^\s{}][^{}\n]*)\{", css, re.M)), "its styles stay under its own .hdx- names"


@needs_node
def test_the_file_parses():
    for name in ("hd-export.js",):
        run = subprocess.run([NODE, "--check", str(DESIGN / name)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]
    run = subprocess.run([NODE, "--check", str(JS_TEST)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr[-2000:]


def _png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR", "a real PNG"
    return struct.unpack(">II", data[16:24])


def _jpeg_size(data: bytes) -> tuple[int, int]:
    assert data[:3] == b"\xff\xd8\xff", "a real JPEG"
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + length
    raise AssertionError("no frame header in the JPEG")


@needs_node
def test_export_import_inspect_in_a_real_browser(tmp_path, capsys):
    env = os.environ.copy()
    env["DESIGN_EXPORT_OUT"] = str(tmp_path)
    if env.get("HOOLA_CHROMIUM"):
        env["CHROMIUM_EXECUTABLE"] = env["HOOLA_CHROMIUM"]
    run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=900, env=env)
    if run.returncode == 77 and not env.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
        env["CHROMIUM_EXECUTABLE"] = SANDBOX_CHROME                  # the same fallback the other browser walks use
        run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=900, env=env)
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    assert run.returncode == 0, (run.stdout[-1500:] + "\n" + run.stderr[-4000:])
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["checks"] >= 150, report["checks"]
    files = report["files"]

    # ---- the ZIP the Export button of the Design panel made: opened by Python's own reader
    with zipfile.ZipFile(files["section.zip"]["path"]) as z:
        assert z.testzip() is None, "every CRC in the ZIP is right"
        assert z.namelist() == ["Post 1080.png", "Post 1080-small.jpg"]
        assert all(i.compress_type == zipfile.ZIP_STORED and i.flag_bits & 0x800 for i in z.infolist()), "stored, names flagged UTF-8"
        assert _png_size(z.read("Post 1080.png")) == (1080, 1080), "the 1080 x 1080 frame at 1x, as a file on disk"
        assert _jpeg_size(z.read("Post 1080-small.jpg")) == (512, 512), "the fixed-width JPG"
    with zipfile.ZipFile(files["unit.zip"]["path"]) as z:                      # the writer alone: a Devanagari folder and name, binary, empty
        assert z.testzip() is None
        assert z.namelist() == ["पोस्टर/नमस्ते.txt", "a b.bin", "empty.txt"]
        assert z.read(z.namelist()[0]).decode("utf-8") == "namaste नमस्ते"
        assert z.read("a b.bin") == bytes([0, 255, 1, 254]) and z.read("empty.txt") == b""

    # ---- the PDF of all frames: parsed by pypdf
    pypdf = pytest.importorskip("pypdf")
    data = Path(files["frames.pdf"]["path"]).read_bytes()
    assert data.startswith(b"%PDF-1.4\n") and data.rstrip().endswith(b"%%EOF")
    reader = pypdf.PdfReader(io.BytesIO(data), strict=True)                    # strict: a wrong xref offset or object is an error, not a repair
    sizes = [(float(p.mediabox.width), float(p.mediabox.height)) for p in reader.pages]
    assert sizes == [(1080.0, 1080.0), (540.0, 960.0), (595.0, 842.0)], "one page per frame, at its size in points"
    assert reader.metadata.title == "Shop poster" and reader.metadata.producer == "Hoola Design"
    for page, (w, h) in zip(reader.pages, sizes):
        xobj = page["/Resources"]["/XObject"]["/Im0"]
        assert xobj["/Filter"] == "/DCTDecode" and xobj["/ColorSpace"] == "/DeviceRGB" and xobj["/BitsPerComponent"] == 8
        assert (xobj["/Width"], xobj["/Height"]) == (int(w * 2), int(h * 2)), "the page picture is a JPEG at 2x"
        raw = xobj._data                                                       # the stream as stored = the JPEG file itself
        assert _jpeg_size(raw) == (int(w * 2), int(h * 2)) and len(raw) == xobj["/Length"]
        assert page.get_contents().get_data().split() == [b"q", str(int(w)).encode(), b"0", b"0", str(int(h)).encode(), b"0", b"0", b"cm", b"/Im0", b"Do", b"Q"]
        assert page.extract_text().strip() == "", "said plainly: an image PDF, no selectable text"

    # ---- the .hoola.json copy
    copy = json.loads(Path(files["copy.hoola.json"]["path"]).read_text(encoding="utf-8"))
    assert copy["format"] == "hoola-design" and copy["version"] == 1 and copy["nodes"]["0:0"]["type"] == "DOCUMENT"
    assert copy["node_count"] == len(copy["nodes"]) and all("parent" in n or i == "0:0" for i, n in copy["nodes"].items())
    with capsys.disabled():
        print(f"\nHOOLA DESIGN hand-off: {report['checks']} browser checks; SVG import {report['svg']['layers']} layers, "
              f"mean pixel difference to the browser's own drawing {report['svg']['mean_diff']} of 255 ({report['svg']['pixels_off']} pixels off); "
              f"generated CSS vs canvas {report['css']['mean_diff']} of 255 ({report['css']['pixels_off']} pixels off); "
              f"20,000-shape SVG imported in {report['cap_ms']} ms; copy of {report['copy']['layers']} layers = {report['copy']['bytes']} bytes")
