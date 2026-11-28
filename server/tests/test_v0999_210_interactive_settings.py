"""v0.999.210 SETTINGS, REDESIGNED (owner: "NOW DO SAME FOR SETTINGS SECTION" -> design claude.ai/artifact/LZBJ9AF2Y9LgcZq6sJBywR
-> "GO BUILD"): her starting choices for new videos saved to her account (checked one by one, a refused one said), the
folder new videos land in, this month's usage, what is kept and the trash with days left, and what this server can do."""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactive import hub as H
from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]


def _client():
    from app.main import app
    return TestClient(app)


def test_starting_choices_live_on_her_account(ix):
    cl = _client()
    p = cl.get("/api/interactive/x/settings").json()["prefs"]
    assert p["saved"] is False and p["lang"] == "auto" and p["kind"] == "presenter" and p["len"] == 30
    r = cl.put("/api/interactive/x/settings", json={"kind": "reel", "len": 15, "lang": "es"}).json()
    assert r["refused"] == [] and r["prefs"]["kind"] == "reel" and r["prefs"]["len"] == 15 and r["prefs"]["lang"] == "es"
    assert r["prefs"]["saved"] is True and r["prefs"]["updated"]
    # each bad choice is refused in plain words; the good ones still save
    r = cl.put("/api/interactive/x/settings", json={"len": 17, "kind": "opera", "face": "av_nope", "lang": "zz-nope", "folder": "fd_x",
                                                     "voice": ""}).json()
    assert {x["key"] for x in r["refused"]} == {"len", "kind", "face", "lang", "folder"}
    assert all(x["why"] and "_" not in x["why"] for x in r["refused"])
    assert r["prefs"]["kind"] == "reel" and r["prefs"]["len"] == 15                  # unchanged
    # the folder she picks is where a new video lands
    f = H.folder_save("default", "Summer campaign")
    assert cl.put("/api/interactive/x/settings", json={"folder": f["id"]}).json()["refused"] == []
    v = S.draft("default", "Summer offers at the bakery", think=lambda a, b: {"title": "Summer", "scenes": [{"say": "Fresh bread today."}]})
    assert v["folder"] == f["id"]
    # a removed folder is never a default
    H.folder_delete("default", f["id"])
    assert cl.get("/api/interactive/x/settings").json()["prefs"]["folder"] == ""
    # back to Hoola's starting choices; /home carries them for first paint
    r = cl.post("/api/interactive/x/settings/reset").json()["prefs"]
    assert r["kind"] == "presenter" and r["len"] == 30 and r["lang"] == "auto" and r["saved"] is True
    assert cl.get("/api/interactive/x/home").json()["prefs"]["kind"] == "presenter"


def test_usage_kept_and_this_server(ix):
    cl = _client()
    d = S._load("default")
    month = time.strftime("%Y-%m")
    y, m = (int(x) for x in month.split("-"))
    before = f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"
    mk = lambda pid, made, secs, cr, lang="en": {"id": pid, "title": f"Video {pid}", "lang": lang, "status": "ready", "scenes": [],
                                                 "video": {"made": made, "duration": secs, "credits": cr}}
    d["projects"] = [mk("iv_a", f"{month}-02T10:00:00Z", 30, 1500), mk("iv_b", f"{month}-03T10:00:00Z", 60, 2000, "hi"),
                     mk("iv_c", f"{before}-20T10:00:00Z", 20, 900)]
    d["trash"] = [{**mk("iv_t", f"{before}-01T10:00:00Z", 10, 100), "trashed_ts": time.time() - 3 * 86400}]
    S._store("default", d)
    v = cl.get("/api/interactive/x/settings").json()
    u = v["usage"]
    assert u["videos"] == 2 and u["videos_before"] == 2 and u["minutes"] == 1.5 and u["credits"] == 3500
    assert u["recent"][0]["credits"] in (1500, 2000) and u["recent"][0]["lang"]
    assert {x["lang"] for x in u["by_language"]} == {S.lang_label("en"), S.lang_label("hi")}
    k = v["kept"]
    assert k["stored"] == 3 and k["max"] == S.MAX_VIDEOS and k["trash"][0]["days_left"] == H.TRASH_DAYS - 3
    assert {t["k"] for t in k["things"]} == {"Faces", "Your templates", "Folders", "Live agents"}
    caps = {c["id"]: c for c in v["server"]["caps"]}
    assert set(caps) == {"draw", "voice", "faces", "captions", "lab", "busy"}
    txt = str(v["server"])
    assert "KEY" not in txt and "_API" not in txt and "api_key" not in txt.lower()
    assert {x["k"] for x in v["server"]["limits"]} >= {"Finished videos kept", "Days in Trash", "App keys"}


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("settings (v0.999.210"):js.index("// ---- developers (v0.999.209")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert "settings() { return stPage(); }" in js and "settings() { stLoad(); }" in js
    assert "store.set('hx.set', SET); clearTimeout(prefT)" in js and "prefApply(D.prefs)" in js
    for r in ("/settings", "/settings/reset", "/engines/default", "/restore", "/trash/empty"):
        assert r in js, r
    for c in (".hx-stpage", ".hx-stgrid", ".hx-stfields", ".hx-stprev", ".hx-sttab", ".hx-stcap", ".hx-stthings"):
        assert f"#hxRoot {c}" in css, c


def _until(ok, wait=8.0):
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()


def test_settings_in_a_real_browser(ix_server):
    base, browser, key = ix_server
    p = S.draft("default", "Old price list for the shop", think=lambda a, b: {"title": "Old price list", "scenes": [{"say": "Prices."}]})
    H.trash("default", p["id"])
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/?v=interactive")
        pg.wait_for_selector("#hxRoot .hx-side [data-p=settings]", state="attached", timeout=25000)
        if vp["width"] < 900:
            pg.click("#hxRoot .hx-menu")
        pg.click("#hxRoot .hx-side [data-p=settings]")
        pg.wait_for_selector("#hxRoot .hx-stpage .hx-stfields", timeout=15000)
        if vp["width"] > 900:
            assert "Every new video starts with" in pg.inner_text(".hx-stpage")
            pg.click("[data-a=stkind][data-val=reel]")
            pg.click("[data-a=stlen][data-val='15']")
            _until(lambda: S._load("default").get("prefs", {}).get("len") == 15)
            assert S._load("default")["prefs"]["kind"] == "reel"
            assert "tall 9:16" in pg.inner_text(".hx-stprev")
            if shots:
                pg.wait_for_timeout(500)
                pg.screenshot(path=f"{shots}/ix210-set-1440.png", full_page=True)
            pg.click("[data-a=streset]")
            _until(lambda: S._load("default")["prefs"]["kind"] == "presenter")
            # usage
            pg.click("[data-a=sttab][data-val=usage]")
            pg.wait_for_selector(".hx-stpage .hx-dvstats", timeout=5000)
            assert "Minutes by language" in pg.inner_text(".hx-stpage")
            # kept + trash: bring back, then delete all asks first
            pg.click("[data-a=sttab][data-val=kept]")
            pg.wait_for_selector(".hx-sttr", timeout=5000)
            assert "Old price list" in pg.inner_text(".hx-sttr") and "days left" in pg.inner_text(".hx-sttr")
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix210-set-kept.png", full_page=True)
            pg.click("[data-a=stemptyask]")
            pg.wait_for_selector("#hxDlg [data-a=stempty]", timeout=5000)
            pg.click("#hxDlg .hx-dlgf [data-a=dlgx]")
            pg.click("[data-a=strestore]")
            _until(lambda: not S._load("default")["trash"])
            # this server
            pg.click("[data-a=sttab][data-val=server]")
            pg.wait_for_selector(".hx-stcap", timeout=5000)
            txt = pg.inner_text(".hx-stpage")
            assert "Drawing the video" in txt and "Limits" in txt and "_KEY" not in txt
            pg.click("[data-a=stcheck]")
            if shots:
                pg.wait_for_timeout(500)
                pg.screenshot(path=f"{shots}/ix210-set-server.png", full_page=True)
        else:
            assert pg.evaluate("document.documentElement.scrollWidth") <= 392
            if shots:
                pg.wait_for_timeout(700)
                pg.screenshot(path=f"{shots}/ix210-set-390.png", full_page=True)
        ctx.close()
    assert not errors, errors
