"""v0.999.209 DEVELOPERS, REDESIGNED (owner: "NOW DEVLOPER SECTION" -> design claude.ai/artifact/GEoE5TiJyZoAVeijrfxBVo
-> "GO BUILD"): what her apps did this month, the four steps, app keys with their calls this hour of the limit and a
rename, webhooks with their recent deliveries, a key and a signing secret shown once, and the API with real requests."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactive import apps as AP
from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]


def _client():
    from app.main import app
    return TestClient(app)


def test_keys_count_calls_and_rename(ix):
    cl = _client()
    k = cl.post("/api/interactive/x/apps/keys", json={"name": "Shop website"}).json()
    assert k["key"].startswith("hi_live_") and "Copy this key now" in k["note"]
    h = {"Authorization": f"Bearer {k['key']}"}
    for _ in range(3):
        assert cl.get("/api/interactive/v1/engines", headers=h).status_code == 200
    v = cl.get("/api/interactive/x/apps").json()
    row = next(x for x in v["keys"] if x["id"] == k["id"])
    assert row["calls"] == 3 and row["calls_month"] == 3 and row["calls_hour"] == 3
    assert v["month"]["calls"] == 3 and v["base"].endswith("/api/interactive") and "sha" not in str(v)
    r = cl.patch("/api/interactive/x/apps/keys", json={"id": k["id"], "name": "  Nightly   report "}).json()
    assert r["name"] == "Nightly report" and "key" not in r
    assert cl.patch("/api/interactive/x/apps/keys", json={"id": k["id"], "name": " "}).status_code in (409, 422)
    assert cl.patch("/api/interactive/x/apps/keys", json={"id": "nope", "name": "x"}).status_code in (404, 409, 422)
    # a video asked through the API is counted for this month only when the make really starts
    AP.count_video("default")
    assert cl.get("/api/interactive/x/apps").json()["month"]["videos"] == 1


def test_webhook_keeps_recent_deliveries(ix, monkeypatch):
    from app.vocal import apps as VA
    AP.SYNC = True
    monkeypatch.setattr(VA, "WAITS", (0,))
    seen = []

    class R:
        def __init__(self, code):
            self.status_code = code

    codes = iter([200, 503, 200])
    monkeypatch.setattr(VA, "_http_post", lambda url, body, headers: (seen.append(headers), R(next(codes)))[1])
    hk = AP.hook_add("default", "https://example.com/hook", ["video.ready"])
    assert hk["secret"].startswith("whsec_") and hk["events"] == ["video.ready"]
    AP.hook_test("default", hk["id"])
    p = S.draft("default", "Summer offers at the bakery")
    AP.notify("default", "video.ready", {**p, "status": "ready"})
    AP.notify("default", "video.failed", p)                         # not one of its events: nothing sent
    AP.notify("default", "video.ready", {**p, "status": "ready"})
    v = _client().get("/api/interactive/x/apps").json()["hooks"][0]
    assert [x["status"] for x in v["log"]] == ["200", "503", "200"]
    assert v["log"][0]["event"] == "video.ready" and v["log"][0]["title"] == p["title"] and v["log"][-1]["event"] == "test"
    assert "secret" not in v and all(s.get("X-Hoola-Signature", "").startswith("t=") for s in seen)
    h = S._load("default")
    rows = AP._apps(h)["hooks"][0]
    rows["log"] = [{"at": "", "event": "test", "status": "200", "title": ""}] * 15
    S._store("default", h)
    assert len(_client().get("/api/interactive/x/apps").json()["hooks"][0]["log"]) == AP.MAX_LOG


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("developers (v0.999.209"):js.index("// ---- engines (v0.999.208")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert "developers() { return dvPage(); }" in js and "UI.newKey" not in js and 'id="hxKeyName"' not in js
    for r in ("/apps/keys", "/apps/hooks", "/apps/hooks/test", "'PATCH'"):
        assert r in js, r
    for c in (".hx-dvstats", ".hx-dvsteps", ".hx-dvcard", ".hx-dvrate", ".hx-dvlog", ".hx-dvcode", ".hx-dvapi", ".hx-dvkey", ".hx-dvevs"):
        assert f"#hxRoot {c}" in css, c


def _until(ok, wait=8.0):
    import time
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()


def test_developers_in_a_real_browser(ix_server, monkeypatch):
    from app.vocal import apps as VA
    AP.SYNC = True
    monkeypatch.setattr(VA, "WAITS", (0,))

    class R:
        status_code = 200

    monkeypatch.setattr(VA, "_http_post", lambda url, body, headers: R())
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/?v=interactive")
        pg.wait_for_selector("#hxRoot .hx-side [data-p=developers]", state="attached", timeout=25000)
        if vp["width"] < 900:
            pg.click("#hxRoot .hx-menu")
        pg.click("#hxRoot .hx-side [data-p=developers]")
        pg.wait_for_selector("#hxRoot .hx-dvpage .hx-dvsteps", timeout=15000)
        if vp["width"] > 900:
            assert "No app keys yet" in pg.inner_text(".hx-dvpage")
            # a key: named, shown once, a first call with it ready to paste
            pg.click(".hx-dvhead [data-a=dvkeyask]")
            pg.fill("#hxDvName", "Shop website")
            pg.click("#hxDlg [data-a=keynew]")
            pg.wait_for_selector("#hxDlg .hx-dvonce", timeout=8000)
            full = pg.inner_text("#hxDlg .hx-dvkey code")
            assert full.startswith("hi_live_") and full in pg.inner_text("#hxDlg .hx-dvcode")
            pg.click("#hxDlg [data-a=dvlang][data-val=py]")
            _until(lambda: "requests.get" in pg.inner_text("#hxDlg .hx-dvcode"))
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix209-dev-key.png")
            pg.click("#hxDlg .hx-dlgf [data-a=dlgx]")
            _until(lambda: "Shop website" in pg.inner_text(".hx-dvcols"))
            assert full not in pg.inner_text(".hx-dvpage")                          # never shown again
            # rename it
            pg.click(".hx-dvcard [data-a=dvren]")
            pg.fill("#hxDvRn", "Nightly report")
            pg.click("#hxDlg [data-a=dvrensave]")
            _until(lambda: "Nightly report" in pg.inner_text(".hx-dvcols"))
            # a webhook: address, events, secret once, a test answered
            pg.click("[data-a=dvhookask]")
            pg.fill("#hxDvUrl", "https://example.com/hoola")
            pg.uncheck("#hxDlg input[value='video.failed']")
            pg.click("#hxDlg [data-a=hooknew]")
            pg.wait_for_selector("#hxDlg .hx-dvkey", timeout=8000)
            assert pg.inner_text("#hxDlg .hx-dvkey code").startswith("whsec_")
            pg.click("#hxDlg .hx-dlgf [data-a=dlgx] >> nth=-1")
            _until(lambda: "example.com/hoola" in pg.inner_text(".hx-dvcols"))
            assert "video.failed" not in pg.inner_text(".hx-dvcols")
            pg.click(".hx-dvcard [data-a=hooktest]")
            _until(lambda: "Recent deliveries" in pg.inner_text(".hx-dvcols"))
            assert "200 OK" in pg.inner_text(".hx-dvcols")
            if shots:
                pg.wait_for_timeout(500)
                pg.screenshot(path=f"{shots}/ix209-dev-1440.png", full_page=True)
            # the API: a real request for the chosen call, in her server's address
            pg.click(".hx-dvhead [data-a=dvtab]")
            pg.wait_for_selector(".hx-dvapi", timeout=5000)
            assert "requests.post" in pg.inner_text(".hx-dvpair")                       # the language she picked stays
            pg.click(".hx-dvdoc [data-a=dvlang][data-val=curl]")
            req = pg.inner_text(".hx-dvpair .hx-dvcode >> nth=0")
            assert "curl -X POST" in req and base in req and "/api/interactive/v1/videos" in req
            pg.click("[data-a=dvdoor][data-val='3']")
            _until(lambda: "quote_key" in pg.inner_text(".hx-dvpair"))
            assert "hmac" in pg.inner_text(".hx-dvdoc").lower()
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix209-dev-api.png", full_page=True)
            # removing a key asks first
            pg.click("[data-a=dvtab][data-val=over] >> nth=0")
            pg.click(".hx-dvcard [data-a=dvdel][data-val=key]")
            pg.click("#hxDlg [data-a=keydel]")
            _until(lambda: "No app keys yet" in pg.inner_text(".hx-dvpage"))
        else:
            assert pg.evaluate("document.documentElement.scrollWidth") <= 392
            if shots:
                pg.wait_for_timeout(700)
                pg.screenshot(path=f"{shots}/ix209-dev-390.png", full_page=True)
        ctx.close()
    assert not errors, errors
