"""GRAPHICS DESK: the Graphics Engine Programmer's own section, built like the finance desks - its own chat (kind 'graphics') with
the desk block + the graphics tool in view; shaders checked in code (GLSL ES 3.00 rules, unused uniforms, float ==) and kept with
versions + a golden picture compared by her browser's WebGL2; the CPU path tracer (the white furnace keeps its energy exactly, the
same seed gives the same picture); PSNR / SSIM / heat map; Vulkan / D3D12 / Metal / OpenGL validation grouped; PresentMon frame
times (lows, stutters, CPU- or GPU-bound) and GPU passes; walked in a browser."""
from __future__ import annotations

import base64
import os
import random
import tempfile

import pytest
from fastapi.testclient import TestClient

T = "default"

VK_LOG = """[Validation] Validation Error: [ VUID-vkCmdDraw-None-02699 ] Object 0: handle = 0x55a1b2c3d4e0, type = VK_OBJECT_TYPE_DESCRIPTOR_SET; | MessageID = 0x1c2a | vkCmdDraw(): the descriptor set 0 binding 1 was never updated. The Vulkan spec states: Descriptors in each bound descriptor set must be valid (https://www.khronos.org/registry/vulkan/specs/)
[Validation] Validation Error: [ VUID-vkCmdDraw-None-02699 ] Object 0: handle = 0x55a1b2c3d4f0, type = VK_OBJECT_TYPE_DESCRIPTOR_SET; | MessageID = 0x1c2a | vkCmdDraw(): the descriptor set 0 binding 1 was never updated.
[Validation] Validation Error: [ SYNC-HAZARD-WRITE-AFTER-READ ] Object 0: handle = 0x5611aa; | MessageID = 0x376b | vkCmdCopyBuffer(): Hazard WRITE_AFTER_READ for dstBuffer, region 0.
[Validation] Validation Performance Warning: [ BestPractices-vkCreateImage-small-dedicated ] vkCreateImage(): small dedicated allocation.
D3D12 ERROR: ID3D12CommandList::DrawInstanced: The resource state (0x0) is invalid for use as a shader resource. [ EXECUTION ERROR #538: INVALID_SUBRESOURCE_STATE ]
-[MTLDebugRenderCommandEncoder setVertexBuffer:offset:atIndex:]:1625: failed assertion `Set Vertex Buffer Validation index(31) must be < 31.'
"""
BAD_SHADER = """#version 300 es
uniform float u_unused;
uniform vec2 u_res;
void main() {
    vec2 uv = gl_FragCoord.xy / u_res;
    if (uv.x == 0.5) { }
    gl_FragColor = texture2D(tex, uv);
}
"""


def _frames_csv() -> str:
    random.seed(4)
    rows = ["Application,ProcessID,MsBetweenPresents,CPUBusy,GPUBusy"]
    for i in range(600):
        ms = 33.0 if i in (200, 410) else 7.6 + random.random() * 0.8
        rows.append(f"game.exe,4321,{ms:.3f},3.1,7.2")
    return "\n".join(rows)


@pytest.fixture
def gx(env):
    from app import gfxchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "graphics_eng", trust="seekh")


# ---------------------------------------------------------------- the readers (pure code)
def test_path_tracer_compare_and_shader_check():
    from app.gfxdesk import compare, pathtrace, shaders
    sc = pathtrace.SCENES["furnace"]["scene"]
    r = pathtrace.render(sc)
    f = pathtrace.furnace_check(r, 0.5)
    assert f["energy"] == "conserved" and f["max_deviation"] < 0.02 and r["nan_paths"] == 0
    small = {**pathtrace.SCENES["spheres"]["scene"], "width": 64, "height": 40, "samples": 4}
    a, b = pathtrace.render(small), pathtrace.render(small)
    assert a["png"] == b["png"]                                                     # the same seed, the same picture
    same = compare.compare(a["png"], b["png"])
    assert same["identical"] and same["passed"] and same["psnr"] is None
    x = compare.load(a["png"])
    y = x.copy()
    y[10:20, 10:30] = 1.0
    d = compare.compare(x, y)
    assert not d["passed"] and d["psnr"] < 35 and d["over_share"] > 0.05 and d["worst"][0]["x"] <= 16 and d["heatmap"].startswith("data:image/png")
    assert compare.compare(x, y, blur=2)["mean_error"] < d["mean_error"] * 1.2
    with pytest.raises(compare.CompareError):
        compare.compare(x, x[:20])
    with pytest.raises(pathtrace.SceneError):
        pathtrace.check({**small, "width": 5000})
    ok = shaders.lint(shaders.STARTER)
    assert ok["counts"]["error"] == 0 and ok["version"] == "300 es"
    bad = shaders.lint(BAD_SHADER)
    txt = " ".join(i["text"] for i in bad["issues"])
    assert bad["counts"]["error"] >= 3 and "precision" in txt and "gl_FragColor" in txt and "texture2D" in txt
    assert "u_unused" in txt and "with ==" in txt and "u_res" not in txt.split("u_unused")[0]
    assert shaders.lint("@fragment fn main() -> @location(0) vec4f { return vec4f(1.0); }")["lang"] == "wgsl"


def test_validation_and_frame_readers():
    from app.gfxdesk import frames, vklog
    v = vklog.parse(VK_LOG)
    ids = [g["id"] for g in v["groups"]]
    assert v["messages"] == 6 and v["errors"] == 5 and v["warnings"] == 1 and v["apis"] == ["Direct3D 12", "Metal", "Vulkan"]
    g0 = v["groups"][0]
    assert g0["id"] == "VUID-vkCmdDraw-None-02699" and g0["count"] == 2 and g0["calls"] == ["vkCmdDraw"] and g0["category"] == "descriptor"
    assert g0["link"].endswith("#VUID-vkCmdDraw-None-02699") and "0x55a1" not in g0["text"] and g0["rule"].startswith("Descriptors in each")
    cat = {g["id"]: g["category"] for g in v["groups"]}
    assert cat["SYNC-HAZARD-WRITE-AFTER-READ"] == "sync" and cat["BestPractices-vkCreateImage-small-dedicated"] == "perf"
    assert cat["#538 INVALID_SUBRESOURCE_STATE"] == "layout" and ids[-1].startswith("BestPractices")
    assert vklog.parse("nothing here")["messages"] == 0
    fr = frames.analyse(_frames_csv(), 60)
    assert fr["ok"] and fr["frames"] == 600 and fr["column"] == "msbetweenpresents" and fr["stutters"] == 2 and fr["bound"] == "GPU"
    assert 110 < fr["avg_fps"] < 130 and fr["low01_fps"] < 40 and fr["over_budget"] < 0.01
    plain = frames.analyse(" ".join(["16.7"] * 50 + ["50"]), 60)
    assert plain["column"] == "numbers" and plain["stutters"] == 1
    assert not frames.analyse("1 2 3", 60)["ok"]
    ps = frames.passes("Shadows, 2.1\nGBuffer, 4.0\nLighting: 6.5 ms\nPost | 1.2", 60)
    assert ps["passes"][0]["name"] == "Lighting" and ps["total_ms"] == 13.8 and not ps["over"]


def test_hire_chat_wiring_store_and_guards(gx):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert gx.summary(T)["hired"] is False and "Hire me from AI Employees" in gx.greeting(T)
    with pytest.raises(PermissionError):
        gx.do(T, "add", {"kind": "vklog", "text": "x"})
    _hire()
    d = gx.summary(T)
    assert d["hired"] and "never runs anything on your machines" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"shaders", "settings"}
    chat = gx.current(T)
    assert gx.is_graphics(chat["id"]) and gx.owns(T, chat["id"]) and "<graphics_desk>" in gx.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_gxc.is_graphics(conversation_id)" in src and "adm.admit_families(_gxc.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"graphics"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/graphics")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "gxdesk.js" in r.text
    html = (root / "server/app/static/console/gxdesk.html").read_text()
    for x in ("chatkit.js", "gxdesk.css", "gxdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/graphics')" in (root / "server/app/static/console/v2.js").read_text()
    assert "graphics_eng: 'gxdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["graphics_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["gfx_desk"] in gx.FAMILIES and "gfx_desk" in HANDLERS
    # a shader: versions, the golden picture and a test against it
    s = gx.do(T, "add", {"kind": "shader", "title": "Sphere"})
    assert s["number"] == "S-0001" and len(s["versions"]) == 1 and s["result"]["counts"]["error"] == 0
    from app.gfxdesk import pathtrace
    ref = gx.do(T, "render", {"scene": {**pathtrace.SCENES["spheres"]["scene"], "width": 32, "height": 32, "samples": 2}})
    png = ref["png"]
    s = gx.do(T, "run", {"id": s["id"], "ok": True, "log": "", "png": png, "version": 1, "golden": True})
    assert s["golden"]["png"] == png and s["result"]["test"] == "golden set"
    s = gx.do(T, "save_shader", {"id": s["id"], "src": BAD_SHADER, "note": "port"})
    assert len(s["versions"]) == 2 and s["result"]["test"] == "not run" and s["brief"]["errors"] >= 3
    assert len(gx.do(T, "save_shader", {"id": s["id"], "src": BAD_SHADER})["versions"]) == 2           # no change = no version
    s = gx.do(T, "run", {"id": s["id"], "ok": False, "log": "ERROR: 0:7: 'gl_FragColor' : undeclared identifier\n", "version": 2})
    assert s["result"]["compile"]["errors"][0]["line"] == 7 and s["result"]["test"] == "does not compile"
    from app.gfxdesk import compare as CMP
    arr = CMP.load(png)
    arr[:16] = 0
    from PIL import Image
    import io as _io
    buf = _io.BytesIO()
    Image.fromarray((arr * 255).astype("uint8")).save(buf, format="PNG")
    changed_png = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    s = gx.do(T, "run", {"id": s["id"], "ok": True, "png": changed_png, "version": 2})
    assert s["result"]["test"] == "failed" and not s["result"]["diff"]["passed"]
    assert any("no longer matches" in n["say"] for n in gx.summary(T)["desk"]["needs"])
    # images, validation, frames
    c = gx.do(T, "add", {"kind": "compare", "a": png, "b": png, "a_name": "ref.png"})
    assert c["number"] == "I-0001" and c["status"] == "fixed" and c["result"]["identical"]
    c2 = gx.do(T, "add", {"kind": "compare", "a": png, "b": changed_png})
    assert c2["status"] == "open" and any("images differ" in n["say"] for n in gx.summary(T)["desk"]["needs"])
    v = gx.do(T, "add", {"kind": "vklog", "text": VK_LOG})
    assert v["number"] == "V-0001" and v["brief"]["errors"] == 5
    f = gx.do(T, "add", {"kind": "frames", "text": _frames_csv()})
    assert f["brief"]["bound"] == "GPU" and f["brief"]["stutters"] == 2
    p = gx.do(T, "add", {"kind": "passes", "text": "A, 9\nB, 9"})
    assert p["brief"]["over"] and any("over the frame budget" in n["say"] for n in gx.summary(T)["desk"]["needs"])
    st = gx.do(T, "settings", {"api": "d3d12", "target_fps": "144", "psnr_min": "40"})
    assert st["api"] == "d3d12" and st["target_fps"] == 144 and st["psnr_min"] == 40
    assert "API d3d12" in (gx.forget(T) or gx.block(T))
    # guards
    with pytest.raises(PermissionError):
        gx.do(T, "settings", {"engine": "my password is hunter2"})
    assert gx.do(T, "add", {"kind": "vklog", "text": "password: hunter2 in a log is data"})["kind"] == "vklog"
    with pytest.raises(gx.GxDeskError):
        gx.do(T, "settings", {"api": "glide"})
    with pytest.raises(gx.GxDeskError):
        gx.do(T, "settings", {"target_fps": "5"})
    with pytest.raises(gx.GxDeskError):
        gx.do(T, "add", {"kind": "frames", "text": "   "})
    with pytest.raises(gx.GxDeskError):
        gx.do(T, "add", {"kind": "compare", "a": png, "b": "data:image/png;base64,AAAA"})
    with pytest.raises(gx.GxDeskError):
        gx.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "graphics_eng")
    assert gx.do(T, "get", {"id": v["id"]})["id"] == v["id"] and gx.do(T, "lint", {"src": BAD_SHADER})["counts"]["error"] >= 3
    with pytest.raises(PermissionError):
        gx.do(T, "add", {"kind": "vklog", "text": VK_LOG})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def gx_server(gx, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"], args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(gx, gx_server):
    base, browser, key = gx_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and "WebGL" not in m.text and errs.append("console: " + m.text))
    pg.goto(base + "/console/graphics")
    pg.wait_for_selector(".gx-starts", timeout=20000)
    # a shader: run it in this browser, set the golden picture, change it, test again
    go(pg, "#/shaders", "[data-newshader]")
    pg.click("[data-newshader]")
    pg.wait_for_selector("#gxCanvas", timeout=30000)
    gl = pg.evaluate("!!document.createElement('canvas').getContext('webgl2')")
    if gl:
        pg.click("[data-shgold]")
        pg.wait_for_selector("text=Golden picture set", timeout=30000)
        assert "Compiled and linked" in pg.inner_text("#gxPage")
        src = pg.input_value("#gxSrc").replace("vec3(0.85, 0.45, 0.25)", "vec3(0.2, 0.6, 0.95)")
        pg.fill("#gxSrc", src)
        pg.fill("#gxNote", "blue")
        pg.click("[data-shsave]")
        pg.wait_for_selector("#toast:has-text('Saved as version 2')", timeout=20000)
        pg.click("[data-shtest]")
        pg.wait_for_selector(".gx-trio figure:nth-child(3)", timeout=30000)
        assert "Does not match the golden picture" in pg.inner_text("#gxPage")
        pg.fill("#gxSrc", src.replace("fragColor = vec4", "fragColor = vec5"))
        pg.click("[data-shrun]")
        pg.wait_for_selector("#gxGlNote:not([hidden])", timeout=20000)
    else:
        pg.click("[data-shrun]")
        pg.wait_for_selector("#toast:has-text('no WebGL2')", timeout=20000)
    snap(pg, "gx-shader-1440")
    # images: render a reference, compare it with itself from a file
    go(pg, "#/images", "[data-ref=spheres]")
    pg.click("[data-ref=spheres]")
    pg.wait_for_selector(".gx-refimg img", timeout=60000)
    png = pg.get_attribute(".gx-refimg img", "src")
    fn = os.path.join(tempfile.mkdtemp(), "render.png")
    open(fn, "wb").write(base64.b64decode(png.split(",", 1)[1]))
    pg.select_option("#gxA", "ref:spheres")
    pg.set_input_files("input[data-imgto=b]", fn)
    pg.wait_for_selector("#gxBpick:has-text('render.png')")
    snap(pg, "gx-images-1440")
    pg.click("form[data-form=compare] [type=submit]")
    pg.wait_for_selector(".gx-sum", timeout=60000)
    assert "The same image." in pg.inner_text(".gx-sum")
    snap(pg, "gx-compare-1440")
    # validation
    go(pg, "#/validation", "form[data-form=add]")
    pg.fill("form[data-form=add] [name=text]", VK_LOG)
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector(".gx-msg", timeout=30000)
    pg.click(".gx-msg summary")
    assert "Open in the Vulkan spec" in pg.inner_text("#gxPage") and "Descriptors and bindings" in pg.inner_text("#gxPage")
    snap(pg, "gx-validation-1440")
    # frames
    go(pg, "#/frames", "form[data-form=add]")
    pg.fill("form[data-kind=frames] [name=text]", _frames_csv())
    pg.click("form[data-kind=frames] [type=submit]")
    pg.wait_for_selector(".gx-fchart", timeout=30000)
    assert "GPU-bound" in pg.inner_text(".gx-sum")
    snap(pg, "gx-frames-1440")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.select_option("form[data-form=settings] [name=api]", "metal")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    assert "Metal" in pg.inner_text("#gxSite")
    go(pg, "#/today", ".gx-list")
    snap(pg, "gx-today-1440")
    for route, sel in (("#/today", ".gx-list"), ("#/shaders", ".gx-item"), ("#/images", ".gx-refs"), ("#/validation", ".gx-item"),
                       ("#/frames", ".gx-item"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#gxPage *')].filter(e => !e.closest('pre,textarea,table') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    go(pg, "#/shaders", ".gx-item")
    pg.click(".gx-item")
    pg.wait_for_selector("#gxCanvas", timeout=20000)
    w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert w[0] <= w[1] + 1, w
    snap(pg, "gx-shader-390")
    go(pg, "#/frames", ".gx-item")
    pg.click(".gx-item")
    pg.wait_for_selector(".gx-sum", timeout=20000)
    snap(pg, "gx-frames-390")
    assert not errs, errs
