"""v0.825 HOOLA DESIGN D9a, the WebGL2 tile renderer (docs/HOOLA_DESIGN_PLAN.md section 8): hd-render-gl.js behind the
same HD.render contract, switched in by hd-render.js.

The real test is JavaScript - server/tests/web/design_gl_test.js - and runs in a REAL browser (node + playwright,
Chromium, WebGL2 through SwiftShader): the same scripted page (every node type, paint and effect) drawn by the WebGL2
tiles and by Canvas2D and compared pixel by pixel at six views and two pixel ratios; the GPU fast path for plain shapes;
edits that repaint only the changed part of a tile; a pan over made tiles that paints nothing; the setting (gl / 2d / auto);
a lost WebGL context falling back to Canvas2D with no error; export + hit tests the same in both modes; and the speed of
both renderers at 5,000 / 20,000 / 100,000 layers. This file runs it, prints the measured numbers, and skips cleanly
where node, playwright, Chromium or WebGL2 is missing."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
JS_TEST = HERE / "web" / "design_gl_test.js"
DESIGN = HERE.parent / "app" / "static" / "console" / "design"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")


def test_gl_file_is_a_plain_strict_script_and_wired_in():
    text = (DESIGN / "hd-render-gl.js").read_text(encoding="utf-8")
    assert "'use strict';" in text and text.rstrip().endswith("})();")
    assert "eval(" not in text and "new Function" not in text and "import(" not in text      # strict CSP: script-src 'self'
    assert "innerHTML" not in text and "document.write" not in text and "insertAdjacentHTML" not in text
    assert text.isascii()
    assert set(re.findall(r"createElement\('([a-z]+)'\)", text)) <= {"canvas"}
    # one instanced draw call composes the tiles; tiles live in a texture array with an LRU budget; context loss handled
    assert "drawArraysInstanced" in text and "TEXTURE_2D_ARRAY" in text and "budgetMB: 256" in text
    assert "webglcontextlost" in text and "host.lost(" in text
    # the tiles are painted by hd-render.js's own code (one set of painting rules for both renderers)
    assert "host.tilePaint(" in text and "host.tileShapes(" in text
    render = (DESIGN / "hd-render.js").read_text(encoding="utf-8")
    assert "localStorage.getItem('hd.renderer')" in render and "sessionStorage.setItem('hd.renderer.lost'" in render
    assert "function tilePaint(" in render and "function glFrame(" in render
    # export and hit tests never go through the GL path
    for fn in ("function toCanvas(", "function toSVG(", "function hitTest("):
        body = render[render.index(fn):render.index(fn) + 1500]
        assert "gl." not in body and "glEngine" not in body, fn
    html = (DESIGN / "design.html").read_text(encoding="utf-8")
    i, j = html.index("hd-render.js?v="), html.index("hd-render-gl.js?v=")
    assert i < j and html[i:].split("\n")[1].strip().startswith('<script src="/static/console/design/hd-render-gl.js?v=')
    stamp = re.search(r"hd-render\.js\?v=([0-9.]+)", html).group(1)
    assert f"hd-render-gl.js?v={stamp}" in html


@needs_node
def test_gl_file_parses():
    for name in ("hd-render-gl.js", "hd-render.js"):
        run = subprocess.run([NODE, "--check", str(DESIGN / name)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]


@needs_node
def test_webgl_tiles_in_a_real_browser(capsys):
    env = os.environ.copy()
    if env.get("HOOLA_CHROMIUM"):
        env["CHROMIUM_EXECUTABLE"] = env["HOOLA_CHROMIUM"]
    run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=2400, env=env)
    if run.returncode == 77 and not env.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
        env["HOOLA_CHROMIUM"] = SANDBOX_CHROME
        run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=2400, env=env)
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    assert run.returncode == 0, (run.stdout[-1500:] + "\n" + run.stderr[-4000:])
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["checks"] >= 6, report["checks"]
    with capsys.disabled():
        print("\nHOOLA DESIGN WebGL2 tiles vs Canvas2D (headless Chromium, SwiftShader = the GPU emulated on the CPU), 1280x800:")
        for set_name, views in report["pixels"].items():
            worst = max(views.values(), key=lambda d: d["n24"])
            print(f"  pixels {set_name}: worst view {worst['n24']} px over 24 levels, {worst['n100']} over 100, of {worst['px']}")
        for key, p in report["perf"].items():
            line = f"  {key}: first paint {p['firstPaint']} ms, complete {p['complete']} ms; pan avg {p['pan100']['ms']['avg']} p95 {p['pan100']['ms']['p95']} (cpu {p['pan100']['cpuMs']['avg']})"
            line += f"; pan over made tiles avg {p['composite']['ms']['avg']} (cpu {p['composite']['cpuMs']['avg']}); zoom avg {p['zoom']['ms']['avg']} p95 {p['zoom']['ms']['p95']}"
            if p.get("gl"):
                line += f"; textures {p['gl']['texMB']} MB, tiles a frame while panning max {p['pan100']['tiles']['max']}"
            print(line)
    for set_name, views in report["pixels"].items():
        for name, d in views.items():
            assert d["n100"] == 0, (set_name, name, d)
    if report["perf"]:
        big = report["perf"].get("gl_100000")
        if big:
            # the work the CPU does for a frame over made tiles: one draw call (the rest is the GPU, here emulated)
            assert big["composite"]["tiles"]["max"] == 0 and big["composite"]["cpuMs"]["avg"] < 8, big["composite"]
