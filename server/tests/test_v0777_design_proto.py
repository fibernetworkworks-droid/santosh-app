"""v0.777 HOOLA DESIGN, phase D6 "prototype" (docs/HOOLA_DESIGN_PLAN.md section 2 "prototype"): hd-proto.js + design-proto.css.

The real test is JavaScript - server/tests/web/design_proto_test.js - and runs in a REAL browser (node + playwright,
Chromium) against the real editor files and the mock server of design_ui_test.js: an interaction is wired by dragging
the + handle on the canvas and edited in the popover and the Prototype tab (one undo step each); then the player plays
a three-screen flow by real clicks (home -> detail -> overlay -> back), smart animate is stopped half way on the
player's own clock (the matched layer sits between its two boxes, read from the canvas pixels too), a frame scrolls
under a fixed header (wheel + a touch drag that glides), hover / press / drag / delay / key triggers fire, a link asks
first and only https is offered, a reload on the player address restores it, a view-only file plays but can not be
edited, reduced motion turns smart animate into a dissolve - and the document is byte-identical before and after
playing (store, server copy, op log). This file runs it so CI covers it and skips cleanly where node, playwright or
Chromium is missing."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
JS_TEST = HERE / "web" / "design_proto_test.js"
DESIGN = HERE.parent / "app" / "static" / "console" / "design"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")


def test_the_file_is_a_plain_strict_script():
    text = (DESIGN / "hd-proto.js").read_text(encoding="utf-8")
    assert "'use strict';" in text and text.rstrip().endswith("})();")
    assert "eval(" not in text and "new Function" not in text and "import(" not in text          # strict CSP: script-src 'self'
    assert "innerHTML" not in text and "document.write" not in text and "insertAdjacentHTML" not in text
    assert text.isascii(), "keep the source ASCII (\\uXXXX escapes), it must not depend on the served charset"
    # the page loads it after the shell and before the app, with its own stylesheet
    html = (DESIGN / "design.html").read_text(encoding="utf-8")
    assert html.index("hd-ui.js") < html.index("hd-proto.js") < html.index("hd-app.js") and "design-proto.css" in html
    # it plugs in through the extension points, never by reaching into the shell
    assert "ui.hook('present'" in text and "ui.registerPanel('right', 'prototype'" in text and "HD.render.addOverlay(drawWires)" in text
    # every frame is painted by the real renderer, on the player's own canvas
    assert "HD.render.drawNode(ctx, id)" in text and "HD.render.init" not in text
    # the player never writes: every store write sits behind the one guarded writer of the editor part
    player = text[text.index("the player */"):text.index("the editor: wiring on the canvas")]
    for word in ("st().tx(", "st().set(", "st().create(", "st().remove(", "st().move(", "setProps(", "writeReactions(", "addReaction(", "st().undo(", "st().redo(", "HD.store."):
        assert word not in player, f"the player must not call {word}"
    assert len(re.findall(r"st\(\)\.tx\(", text)) == 1 and len(re.findall(r"st\(\)\.set\(", text)) == 1
    # a link is opened only when it is https, only after the viewer said yes, and without an opener
    assert "u.protocol === 'https:'" in text and "window.open(href, '_blank', 'noopener,noreferrer')" in text
    assert len(re.findall(r"window\.open\(", text)) == 1
    # no artwork of anyone else: the device outlines are drawn here with plain shapes
    assert "drawImage(" in text and "new Image" not in text and ".png" not in text and ".svg'" not in text
    css = (DESIGN / "design-proto.css").read_text(encoding="utf-8")
    assert "text-transform" not in css and "backdrop-filter" not in css
    assert not re.search(r"font-weight:\s*(700|800|900|bold)", css) and not re.search(r"font-size:\s*(\d|1[01])(\.\d+)?px", css)


@needs_node
def test_it_parses():
    for name in ("hd-proto.js",):
        run = subprocess.run([NODE, "--check", str(DESIGN / name)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]
    run = subprocess.run([NODE, "--check", str(JS_TEST)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr[-2000:]


@needs_node
def test_prototype_in_a_real_browser():
    env = os.environ.copy()
    if env.get("HOOLA_CHROMIUM"):
        env["CHROMIUM_EXECUTABLE"] = env["HOOLA_CHROMIUM"]
    run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=900, env=env)
    if run.returncode == 77 and not env.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
        env["CHROMIUM_EXECUTABLE"] = SANDBOX_CHROME                  # the same fallback the other browser walks use
        run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=900, env=env)
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    assert run.returncode == 0, (run.stdout[-1500:] + "\n" + run.stderr[-4000:])
    lines = run.stdout.strip().splitlines()
    assert "design_proto_test: ok" in lines
    report = json.loads(lines[-1])
    assert report["checks"] >= 150, report["checks"]
