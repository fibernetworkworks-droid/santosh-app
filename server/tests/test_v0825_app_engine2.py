"""v0.825 APP ENGINE 2 (L9 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L9"): point at the app and change it.

Click -> source (every element of a PREVIEW build tagged with its file:line, never the live build), the theme file,
free style / words edits at that exact line (no model, Rs 0, Undo), the error collector inside the preview (mapped to
the app's own file and line through the hidden source map), and the HMR-gate idea: a change made inside a Hoola turn is
not built - not shown - until that turn has finished (a half-written change set is never on screen).
The box tests need the App Engine image; they skip, saying so, where it is not."""
import json
import os
import re
import time

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0814_app_engine import _box, _tool, ae_env  # noqa: F401  (fixture + helpers)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

PAGE = '''import { useEffect } from "react";
import { Card, CardTitle } from "@/components/ui/card";

export default function Home() {
  useEffect(() => {
    if (location.search.includes("boom")) setTimeout(() => { throw new Error("Planted error for the walk"); }, 50);
  }, []);
  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-semibold text-ink">Shop staff tasks</h1>
      <p>Two tasks left</p>
      <span className={"text-sm " + "text-muted"}>computed</span>
      <Card>
        <CardTitle>Today</CardTitle>
      </Card>
    </main>
  );
}
'''


def _app(boom=False):
    from app.appengine import service as AE
    aid = _tool(action="create", name="Shop staff tasks")["id"]
    _tool(action="write", app=aid, path="src/pages/Home.tsx", code=PAGE)
    return aid, AE._load(T, aid)


def _hs(r, needle):
    from app.appengine import service as AE
    lines = (AE.src_dir(r) / "src/pages/Home.tsx").read_text().split("\n")
    n = next(i for i, x in enumerate(lines, 1) if needle in x)
    return f"src/pages/Home.tsx:{n}:{lines[n - 1].index('<') + 1}"


# ---------------------------------------------------------------- 1. free edits at the exact line
def test_free_style_and_words_edit_the_exact_line_and_undo(ae_env):
    from app.appengine import pick as PK
    from app.appengine import service as AE
    aid, r = _app()
    h1 = _hs(r, "<h1")
    cur = PK.current(r, h1)
    assert cur["tag"] == "h1" and cur["editable_style"] and cur["values"]["size"] == "2xl" and cur["values"]["color"] == "ink"
    assert cur["text"] == "Shop staff tasks"
    out = PK.edit(T, aid, h1, {"color": "primary", "size": "3xl"}, "Staff tasks today")
    src = (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    assert out["free"] and '<h1 className="font-semibold text-primary text-3xl">Staff tasks today</h1>' in src
    assert "Rs 0" in out["say"] and AE._load(T, aid).dirty
    # an element with no className gets one; a component used on the page is edited where the PAGE uses it
    p = _hs(r, "<p>")
    PK.edit(T, aid, p, {"weight": "bold", "align": "center"})
    assert '<p className="font-bold text-center">Two tasks left</p>' in (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    ct = _hs(r, "<CardTitle>")
    PK.edit(T, aid, ct, {"color": "accent"})
    assert '<CardTitle className="text-accent">Today</CardTitle>' in (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    # computed classes / words in {} / values outside the tokens are refused and change nothing
    before = (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    with pytest.raises(PK.PickError, match="worked out in code"):
        PK.edit(T, aid, _hs(r, "<span"), {"color": "bad"})
    with pytest.raises(PK.PickError, match="not one of the app's choices"):
        PK.edit(T, aid, h1, {"color": "blue-500"})
    with pytest.raises(PK.PickError, match="< > { }"):
        PK.edit(T, aid, h1, None, "Hello {world}")
    with pytest.raises(PK.PickError, match="no source tag"):
        PK.edit(T, aid, "../../etc/passwd:1:1", {"color": "ink"})
    assert (AE.src_dir(r) / "src/pages/Home.tsx").read_text() == before
    # Undo walks back one free edit at a time
    assert "back as it was" in PK.undo(T, aid)["say"]
    assert "<CardTitle>Today</CardTitle>" in (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    PK.undo(T, aid)
    PK.undo(T, aid)
    assert "Shop staff tasks</h1>" in (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    with pytest.raises(PK.PickError, match="Nothing to undo"):
        PK.undo(T, aid)


def test_theme_file_static_tokens_and_the_template_refresh(ae_env):
    from app.appengine import service as AE
    from app.appengine import rules as RL
    aid, r = _app()
    th = json.loads((AE.src_dir(r) / ".hoola/theme.json").read_text())
    assert th["colors"]["primary"] and th["classes"]["radius"]["classes"] == ["rounded-none", "rounded-control", "rounded-card", "rounded-full"]
    assert "@theme static {" in (AE.src_dir(r) / "src/styles/tokens.css").read_text()
    _tool(action="tokens", app=aid, palette="night")
    assert json.loads((AE.src_dir(r) / ".hoola/theme.json").read_text())["colors"]["bg"] == "#0d0f14"
    assert "hoola.plugin.mjs" in RL.LOCKED
    (AE.src_dir(r) / "vite.config.ts").write_text("export default {};\n")      # an app made by an older version
    (AE.src_dir(r) / "hoola.plugin.mjs").unlink()
    AE._refresh_template(r)
    assert "hoolaSource()" in (AE.src_dir(r) / "vite.config.ts").read_text() and (AE.src_dir(r) / "hoola.plugin.mjs").exists()


def test_routes_for_the_studio(ae_env, monkeypatch):
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    c = TestClient(main.app)
    h = {"Authorization": f"Bearer {KEY}"}
    aid, r = _app()
    hs = _hs(r, "<h1")
    assert c.get(f"/api/appengine/{aid}/pick", params={"hs": hs}).status_code == 401
    assert c.get(f"/api/appengine/{aid}/pick", params={"hs": hs}, headers=h).json()["tag"] == "h1"
    assert c.post(f"/api/appengine/{aid}/edit", json={"hs": hs, "style": {"bg": "surface"}}, headers=h).json()["changed"]
    assert c.post(f"/api/appengine/{aid}/edit", json={"hs": "x", "style": {"bg": "surface"}}, headers=h).status_code == 400
    assert "back as it was" in c.post(f"/api/appengine/{aid}/undo", headers=h).json()["say"]
    assert c.post(f"/api/appengine/{aid}/preview-errors", content=b"{" + b" " * 70000 + b"}", headers=h).status_code == 413
    got = c.post(f"/api/appengine/{aid}/preview-errors", json={"items": [{"kind": "page", "m": "x is not defined card 4111 1111 1111 1111"}]}, headers=h).json()
    assert got["open"][0]["count"] == 1 and "4111" not in got["open"][0]["message"]          # masked before it is kept
    fp = got["open"][0]["fp"]
    assert c.post(f"/api/appengine/{aid}/errors/{fp}/dismissed", headers=h).json()["state"] == "dismissed"
    assert c.get(f"/api/appengine/{aid}/errors", headers=h).json()["errors"][0]["state"] == "dismissed"


# ---------------------------------------------------------------- 2. in the box
def test_preview_is_tagged_live_is_clean_and_errors_map_to_the_line(ae_env):
    _box()
    from app.appengine import pick as PK
    from app.appengine import service as AE
    aid, r = _app()
    assert _tool(action="build", app=aid)["built"]
    r = AE._load(T, aid)
    dist = AE.ver_dir(r, 1) / "dist"
    js = next((dist / "assets").glob("*.js"))
    code = js.read_text()
    hs = _hs(r, "<h1")
    assert f'"data-hs":"{hs}"' in code and '"data-hc":"Home"' in code
    assert f'"data-hs":"{_hs(r, "<CardTitle>")}"' in code                                     # the page's own line for a kit part
    assert (dist / "assets" / (js.name + ".map")).exists()
    with pytest.raises(AE.AppEngineError):
        AE.preview_file(r.preview_token, f"__app/assets/{js.name}.map")                      # maps stay on the server
    html = AE.preview_file(r.preview_token, "__app/")[0].decode()                             # v0.827: the app under its shell
    assert '<script src="__hoola/preview.js"></script>' in html
    assert b"ae-cmd" in AE.preview_file(r.preview_token, "__hoola/preview.js")[0]
    # an error at a real position of the built file maps back to the page's line
    lines = code.split("\n")
    gl = next(i for i, x in enumerate(lines, 1) if "Planted error for the walk" in x)
    gc = lines[gl - 1].index("Planted error for the walk") + 1
    stack = f"Error: Planted error for the walk\n    at http://h/api/app-preview/{r.preview_token}/assets/{js.name}:{gl}:{gc}"
    src = (AE.src_dir(r) / "src/pages/Home.tsx").read_text().split("\n")
    want = next(i for i, x in enumerate(src, 1) if "Planted error" in x)
    assert PK.map_stack(r, 1, stack) == ("src/pages/Home.tsx", want)
    got = PK.record(T, aid, [{"kind": "page", "m": "Planted error for the walk", "s": stack}], version=1)["open"][0]
    assert (got["file"], got["line"]) == ("src/pages/Home.tsx", want)
    PK.record(T, aid, [{"kind": "page", "m": "Planted error for the walk", "s": stack}], version=1)
    assert PK.errors(T, aid)[0]["count"] == 2                                                 # one card per fingerprint
    assert "Planted error for the walk" in AE.logs(T, aid)["say"]
    PK.record(T, aid, [], loaded=2)
    assert PK.errors(T, aid)[0]["state"] == "gone" and PK.errors(T, aid)[0]["gone_in"] == 2   # not seen since a newer version
    # publish = a CLEAN build: no tags, no maps, no helper
    AE.publish(T, aid, 1, confirm=True)
    live = list(AE.live_dir(r).rglob("*"))
    assert not any(p.suffix == ".map" for p in live)
    assert not any(b"data-hs" in p.read_bytes() for p in live if p.is_file())
    assert b"preview.js" not in AE.live_file(r.slug, "")[0] and b"preview.js" not in AE.live_file(r.slug, "__app/")[0]


def test_a_half_written_change_is_never_shown(ae_env, monkeypatch):
    """The HMR-gate idea: Hoola writes a page that imports a file it has not written yet - nothing is built while its
    turn runs; the turn ends - ONE build, with both files."""
    _box()
    from app.appengine import service as AE
    aid, r = _app()
    assert _tool(action="build", app=aid)["version"] == 1
    monkeypatch.setenv("HOOLA_APPENGINE_AUTOBUILD", "1")
    monkeypatch.setattr(AE, "DEBOUNCE", 0.3)
    monkeypatch.setattr(AE, "GATE_POLL", 0.3)
    running = {"c-turn": True}
    monkeypatch.setattr(AE, "_turn_running", lambda conv: running.get(conv, False))
    tok = AE.TURN_CONV.set("c-turn")
    try:
        AE.write(T, aid, "src/App.tsx", 'import Home from "./pages/Home";\nimport Extra from "./pages/Extra";\n'
                 'export default function App() { return <><Home /><Extra /></>; }\n')
        time.sleep(2.5)
        assert AE._load(T, aid).version == 1 and AE.get(T, aid, False)["held"]               # half a change: not built
        AE.write(T, aid, "src/pages/Extra.tsx", 'export default function Extra() { return <p className="text-muted">Extra part</p>; }\n')
        time.sleep(1.5)
        assert AE._load(T, aid).version == 1
    finally:
        AE.TURN_CONV.reset(tok)
    running["c-turn"] = False                                                                # the turn ends
    for _ in range(240):
        if AE._load(T, aid).version == 2 and not AE._load(T, aid).dirty:
            break
        time.sleep(0.5)
    r = AE._load(T, aid)
    assert r.version == 2 and json.loads(r.last_build)["ok"]                                 # one build, both files
    assert "Extra part" in next((AE.ver_dir(r, 2) / "dist" / "assets").glob("*.js")).read_text()
    assert [v["version"] for v in AE.versions(r)] == [2, 1]                                   # no half version in between
    # outside a turn (her own free edit in the Studio) the preview simply rebuilds after the pause
    from app.appengine import pick as PK
    PK.edit(T, aid, _hs(r, "<h1"), {"color": "accent"})
    for _ in range(240):
        if AE._load(T, aid).version == 3:
            break
        time.sleep(0.5)
    assert AE._load(T, aid).version == 3


# ---------------------------------------------------------------- 3. the Studio, in a real browser
def test_select_style_undo_and_try_to_fix_in_a_browser(arena_server, ae_env, monkeypatch):
    _box()
    base, browser, key = arena_server
    from app import turn_inbox
    from app.appengine import service as AE
    sent = []

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        sent.append(text)
        return "Looking at it."
    monkeypatch.setattr(turn_inbox, "run_owned", fake)
    aid = AE.create(T, "Shop staff tasks")["id"]                  # plain service calls: Playwright's loop is running here
    AE.write(T, aid, "src/pages/Home.tsx", PAGE)
    r = AE._load(T, aid)
    assert AE.build(T, aid)["built"]
    monkeypatch.setenv("HOOLA_APPENGINE_AUTOBUILD", "1")
    monkeypatch.setattr(AE, "DEBOUNCE", 0.3)
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/console/web#/app/{aid}")
    frame = page.frame_locator("#aeFrame").frame_locator("iframe")       # v0.827: Studio -> shell -> the sealed app
    frame.locator("h1", has_text="Shop staff tasks").wait_for(timeout=30000)
    page.keyboard.press("s")                                                                 # S = Select
    page.locator("[data-ae=select][aria-pressed=true]").wait_for()
    frame.locator("h1", has_text="Shop staff tasks").click()
    page.locator("#aeSel", has_text="src/pages/Home.tsx:").wait_for()
    page.locator("#aeSel [data-ae=pk-chip][data-ae-f=color][data-ae-v=accent]").click()
    accent = AE.get(T, aid)["theme"]["colors"]["accent"]
    fr = next((f for f in page.frames if "/__app/" in f.url), None)                     # the sealed app frame (v0.827)
    assert fr is not None
    rgb = fr.evaluate("getComputedStyle(document.querySelector('h1')).color")
    want = "rgb(%d, %d, %d)" % tuple(int(accent[i:i + 2], 16) for i in (1, 3, 5))
    assert rgb == want, (rgb, want)                                                            # drawn at once, nothing saved yet
    if shots:
        page.screenshot(path=os.path.join(shots, "ae9-1-select.png"))
    page.click("#aeSel [data-ae=pk-apply]")
    page.locator("#aeSel [data-ae=undo]").wait_for()
    assert "text-accent" in (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    page.wait_for_function("() => /Version 2/.test(document.getElementById('aeState')?.textContent || '')", timeout=90000)
    page.click("#aeSel [data-ae=pk-code]")
    page.locator(".ae-src .ln.hot", has_text="<h1").wait_for()
    if shots:
        page.screenshot(path=os.path.join(shots, "ae9-2-code-line.png"))
    page.click("[data-ae-tab=preview]")
    # an error in the preview: collected, mapped to the page's line, Try to fix sends it to Hoola
    page.evaluate("document.getElementById('aeFrame').src += '&boom=1'")
    page.locator(".ae-ebar", has_text="Planted error for the walk").wait_for(timeout=20000)
    assert "src/pages/Home.tsx:" in page.inner_text(".ae-ebar")
    if shots:
        page.screenshot(path=os.path.join(shots, "ae9-3-error.png"))
    page.click(".ae-ebar [data-ae=fixerr]")
    for _ in range(40):
        if sent:
            break
        time.sleep(0.25)
    assert sent and "Planted error for the walk" in sent[0] and re.search(r"src/pages/Home\.tsx line \d+", sent[0]), sent
    ctx.close()
    unplanned = [e for e in errors if "Planted error for the walk" not in e]                 # the planted one is the point
    assert not unplanned, unplanned
