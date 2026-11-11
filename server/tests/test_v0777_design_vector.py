"""v0.777 HOOLA DESIGN, phase D2 "design depth" (docs/HOOLA_DESIGN_PLAN.md): hd-vector.js + the D2 parts of
hd-render.js / hd-layout.js.

The real test is JavaScript - server/tests/web/design_vector_test.js - and runs in a REAL browser (node + playwright,
Chromium) against the real editor with the mock server of design_ui_test.js: the path parser, vector edit mode driven
with the mouse (drag a point, add, delete, smooth, bend, close; one undo step a gesture; the box hugs the path and
nothing else moves), Edit shape, the four boolean groups compared pixel for pixel with a compositing reference, their
stroke / hit test / SVG, Flatten, masks, rulers and guides (pull, snap, remove), layout grids (panel, Shift+G, never in
an export), gradient handles on the canvas, the Alt distances, and the renderer / layout fixes (elliptical radial
gradients, text strokes inside / outside, shadow spread, paths that do not start at 0,0, instances laid out again,
turned children in auto layout), in light and in dark. This file runs it so CI covers it and skips cleanly where node,
playwright or Chromium is missing."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
JS_TEST = HERE / "web" / "design_vector_test.js"
DESIGN = HERE.parent / "app" / "static" / "console" / "design"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")


def test_the_file_is_a_plain_strict_script():
    text = (DESIGN / "hd-vector.js").read_text(encoding="utf-8")
    assert "'use strict';" in text and text.rstrip().endswith("})();")
    assert "eval(" not in text and "new Function" not in text and "import(" not in text          # strict CSP: script-src 'self'
    assert "innerHTML" not in text and "document.write" not in text and "insertAdjacentHTML" not in text
    assert text.isascii(), "keep the source ASCII (\\uXXXX escapes)"
    # nothing is drawn with DOM: the only elements made here go through HD.ui.h (the edit bar, the panel sections)
    assert not re.findall(r"createElement\(", text)
    # every edit is a store transaction; the shared geometry is the renderer's (one copy)
    assert "HD.render.geom" in text and "boolCompute" not in text
    render = (DESIGN / "hd-render.js").read_text(encoding="utf-8")
    for name in ("parsePath", "segsToD", "pathBBox", "vectorSegs", "outlineSegs", "boolPath", "combine", "gridSpans"):
        assert re.search(rf"\b{name}\b", render[render.index("geom: {"):render.index("get canvas()")]), f"HD.render.geom.{name}"
    # the plan documents the new properties
    plan = (HERE.parent.parent / "docs" / "HOOLA_DESIGN_PLAN.md").read_text(encoding="utf-8")
    assert "`bool`" in plan and "`guides`" in plan and "hd-vector.js" in plan


@needs_node
def test_it_parses():
    run = subprocess.run([NODE, "--check", str(DESIGN / "hd-vector.js")], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr[-2000:]


@needs_node
def test_design_depth_in_a_real_browser():
    env = os.environ.copy()
    if env.get("HOOLA_CHROMIUM"):
        env["CHROMIUM_EXECUTABLE"] = env["HOOLA_CHROMIUM"]
    run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=600, env=env)
    if run.returncode == 77 and not env.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
        env["CHROMIUM_EXECUTABLE"] = SANDBOX_CHROME                  # the same fallback the other browser walks use
        run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=600, env=env)
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    assert run.returncode == 0, (run.stdout[-1500:] + "\n" + run.stderr[-4000:])
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["checks"] >= 11, report["checks"]
    # the boolean engine against the compositing reference: the outline is the composited area, as curves
    for op, r in report["bool"].items():
        assert r["bad"] <= r["area"] * 0.004 + 40 and r["curves"] >= 2, (op, r)
