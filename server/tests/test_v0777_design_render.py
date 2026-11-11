"""v0.777 HOOLA DESIGN, the renderer and the layout engine (docs/HOOLA_DESIGN_PLAN.md section 3): hd-layout.js + hd-render.js.

The real test is JavaScript - server/tests/web/design_render_test.js - and runs in a REAL browser (node + playwright,
Chromium) against the real hd-math.js / hd-core.js: a scripted document with every node type, paint and effect is
painted and checked by reading canvas pixels, by hit tests and by layout numbers; edits and pans are checked against
a full repaint (no stale pixels, with and without the bitmap cache); PNG / SVG export; and speed: 5,000 mixed nodes
while panning (must stay under 16 ms a frame) and 20,000 nodes zoomed out. This file runs it so CI covers it, prints
the measured frame times, and skips cleanly where node, playwright or Chromium is missing."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
JS_TEST = HERE / "web" / "design_render_test.js"
DESIGN = HERE.parent / "app" / "static" / "console" / "design"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")
OWN = ("hd-layout.js", "hd-render.js")


def test_the_two_files_are_plain_strict_scripts():
    for name in OWN:
        text = (DESIGN / name).read_text(encoding="utf-8")
        assert "'use strict';" in text and text.rstrip().endswith("})();"), name
        assert "eval(" not in text and "new Function" not in text and "import(" not in text, name     # strict CSP: script-src 'self'
        assert "innerHTML" not in text and "document.write" not in text and "insertAdjacentHTML" not in text, name
        assert text.isascii(), f"{name}: keep the source ASCII (\\uXXXX escapes), it must not depend on the served charset"
        # nothing is drawn with DOM: the only elements these files ever make are canvases and a font stylesheet link
        made = set(re.findall(r"createElement\('([a-z]+)'\)", text))
        assert made <= {"canvas", "link"}, (name, made)
    render = (DESIGN / "hd-render.js").read_text(encoding="utf-8")
    api = render[render.index("const api = HD.render = {"):]
    for fn in ("init", "view", "setView", "zoomToFit", "invalidate", "screenToWorld", "worldToScreen", "hitTest", "nodesInRect",
               "addOverlay", "drawNode", "toCanvas", "toSVG", "image"):
        assert re.search(rf"\b{fn}\b", api[:900]), f"HD.render.{fn} is in the contract"
    layout = (DESIGN / "hd-layout.js").read_text(encoding="utf-8")
    assert "HD.layout = {" in layout and "measureText," in layout and "run(changedIds, changedProps)" in layout
    # the asset is fetched with the console token as a Bearer header, never in the address; font families are whitelisted
    assert "'hoola.console.token'" in render and "Authorization: 'Bearer ' + token" in render and "token=" not in render
    assert "/^[A-Za-z0-9 ]+$/" in render and "fonts.googleapis.com/css?family=" in render
    # every write of the layout engine goes through the one guarded writer (only real changes reach the store)
    assert len(re.findall(r"(?<![A-Za-z])s\.set\(", layout)) == 1 and "Math.abs(cur - v) > EPS" in layout


@needs_node
def test_both_files_parse():
    for name in OWN:
        run = subprocess.run([NODE, "--check", str(DESIGN / name)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]


@needs_node
def test_renderer_and_layout_in_a_real_browser(capsys):
    env = os.environ.copy()
    if env.get("HOOLA_CHROMIUM"):
        env["CHROMIUM_EXECUTABLE"] = env["HOOLA_CHROMIUM"]
    run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=900, env=env)
    if run.returncode == 77 and not env.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
        env["HOOLA_CHROMIUM"] = SANDBOX_CHROME                       # the same fallback the other browser walks use
        run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=900, env=env)
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    assert run.returncode == 0, (run.stdout[-1500:] + "\n" + run.stderr[-4000:])
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["checks"] >= 12, report["checks"]
    perf = report["perf"]
    with capsys.disabled():
        print("\nHOOLA DESIGN renderer, measured (ms per frame, 1280x800):")
        for key in ("n5000_cards", "n5000_flat", "n20000_cards", "n20000_flat"):
            p = perf[key]
            print(f"  {key}: pan at 100% avg {p['pan100']['avg']} (p90 {p['pan100']['p90']}), pan zoomed out avg "
                  f"{p['panZoomedOut']['avg']}, full repaint zoomed out avg {p['repaintZoomedOut']['avg']}, drag one node avg {p['drag']['avg']}")
        for key, r in perf["raf"].items():
            print(f"  real frames {key}: gap avg {r['frameGap']['avg']} max {r['frameGap']['max']}, renderer {r['rendererMs']['avg']} ms a frame")
        print(f"  zooming 20,000 nodes: avg {perf['zoom20000']['avg']} (max {perf['zoom20000']['max']}), frames {perf['zoomModes']}")
    # the target of the plan, said out loud: 5,000 nodes pan under one 60 Hz frame
    assert perf["n5000_cards"]["pan100"]["avg"] < 16 and perf["n5000_flat"]["pan100"]["avg"] < 16, perf
    assert report["incremental_cached"].get("part", 0) > 15 and report["incremental_direct"].get("part", 0) > 15
