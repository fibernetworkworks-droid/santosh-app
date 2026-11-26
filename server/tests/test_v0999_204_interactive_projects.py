"""v0.999.204 PROJECTS, REDESIGNED (owner: "NOW DO SAME FOR PROJECTS SECTION" -> design
claude.ai/artifact/PGZ1YCtgGjMoqZWA1PuxWF -> "GO BUILD"): this month (made, minutes, credits, drafts, trash), folders (make,
rename, remove - the videos stay), many videos at once (move, voice, face, duplicate, trash; a video being made left out and
named), a trash with the days left, bring back, delete one now, empty after a clear warning. Batch / many names live in Apps."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactive import hub as H
from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import DRAFT, ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]


def _client():
    from app.main import app
    return TestClient(app)


def test_folders_and_many_at_once(ix, monkeypatch):
    a = S.draft("default", "Diwali offer on sweets")
    b = S.draft("default", "Gift boxes for Diwali")
    c = S.draft("default", "New clinic hours")
    cl = _client()
    f = cl.post("/api/interactive/hub/folders", json={"name": "Diwali sale"}).json()
    assert f["id"].startswith("fd_") and f["color"].startswith("#")
    assert cl.post("/api/interactive/hub/folders", json={"name": "diwali SALE"}).status_code == 422          # same name twice
    assert cl.post("/api/interactive/hub/folders", json={"name": ""}).status_code == 422
    r = cl.post("/api/interactive/hub/bulk", json={"ids": [a["id"], b["id"]], "action": "move", "value": f["id"]}).json()
    assert sorted(r["done"]) == sorted([a["id"], b["id"]])
    ps = {p["id"]: p for p in S._load("default")["projects"]}
    assert ps[a["id"]]["folder"] == f["id"] and ps[c["id"]].get("folder", "") == ""
    assert cl.post("/api/interactive/hub/bulk", json={"ids": [a["id"]], "action": "move", "value": "fd_none"}).status_code == 404
    # rename, then the voice and face for many
    assert cl.post("/api/interactive/hub/folders", json={"id": f["id"], "name": "Diwali 2026"}).json()["name"] == "Diwali 2026"
    from app.interactive import voice as VO
    monkeypatch.setattr(VO, "voice_info", lambda t, v: {"id": v} if v == "hv_charon" else (_ for _ in ()).throw(VO.VoiceError("not found")))
    assert cl.post("/api/interactive/hub/bulk", json={"ids": [a["id"], b["id"]], "action": "voice", "value": "hv_charon"}).json()["done"]
    assert {p["voice"] for p in S._load("default")["projects"] if p["id"] in (a["id"], b["id"])} == {"hv_charon"}
    assert cl.post("/api/interactive/hub/bulk", json={"ids": [a["id"]], "action": "voice", "value": "hv_nope"}).status_code == 404
    assert cl.post("/api/interactive/hub/bulk", json={"ids": [a["id"]], "action": "face", "value": "av_none"}).status_code == 404
    n = len(S._load("default")["projects"])
    cl.post("/api/interactive/hub/bulk", json={"ids": [c["id"]], "action": "duplicate"})
    assert len(S._load("default")["projects"]) == n + 1
    # a video being made is left out, named
    with S._LOCK:
        d = S._load("default")
        next(p for p in d["projects"] if p["id"] == b["id"])["status"] = "making"
        S._store("default", d)
    r = cl.post("/api/interactive/hub/bulk", json={"ids": [a["id"], b["id"]], "action": "voice", "value": ""}).json()
    assert r["done"] == [a["id"]] and r["skipped"][0]["id"] == b["id"] and "being made" in r["skipped"][0]["why"]
    # remove the folder: its videos stay, out of any folder
    assert cl.delete(f"/api/interactive/hub/folders?id={f['id']}").json()["freed"] == 2
    assert all(not p.get("folder") for p in S._load("default")["projects"]) and S._load("default")["folders"] == []
    assert cl.post("/api/interactive/hub/bulk", json={"ids": [], "action": "trash"}).status_code == 422
    assert cl.post("/api/interactive/hub/bulk", json={"ids": [a["id"]], "action": "explode"}).status_code == 422


def test_trash_one_for_good_and_the_month(ix):
    a = S.draft("default", "Old opening hours")
    cl = _client()
    cl.post("/api/interactive/hub/bulk", json={"ids": [a["id"]], "action": "trash"})
    assert S._load("default")["trash"][0]["id"] == a["id"] and "trashed_ts" in S._load("default")["trash"][0]
    assert cl.post("/api/interactive/hub/trash/purge", json={"id": a["id"]}).json()["ok"] is True
    assert S._load("default")["trash"] == []
    assert cl.post("/api/interactive/hub/trash/purge", json={"id": a["id"]}).status_code == 422
    u = H.usage("default")
    assert "credits" in u and u["credits"] == 0
    home = cl.get("/api/interactive/x/home").json()
    assert "folders" in home and "credits" in home["usage"]


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("projects (v0.999.204"):js.index("// ------------------------------------------------------------------ pages ---")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert "'Many names'" not in js and "hxBatch" not in js                      # batches live in Apps now
    for r in ("/folders", "/bulk", "/trash/purge", "/trash/empty", "/restore"):
        assert r in js, r
    for c in (".hx-pjfs", ".hx-pjf", ".hx-pjbulk", ".hx-pjt", ".hx-pjr", ".hx-pjtri", ".hx-pjleft"):
        assert f"#hxRoot {c}" in css, c


def _until(ok, wait=8.0):
    import time
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()


def _open(pg, base, vp):
    pg.goto(base + "/console/?v=interactive")
    pg.wait_for_selector("#hxRoot .hx-side [data-p=projects]", state="attached", timeout=25000)
    if vp["width"] < 900:
        pg.click("#hxRoot .hx-menu")
    pg.click("#hxRoot .hx-side [data-p=projects]")
    pg.wait_for_selector("#hxRoot .hx-pjpage", timeout=15000)


def test_projects_in_a_real_browser(ix_server, monkeypatch):
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    a = S.draft("default", "Diwali offer on sweets")
    S.save("default", a["id"], {"title": "Diwali offer: 20% off sweets"})
    b = S.draft("default", "Gift boxes for Diwali")
    S.save("default", b["id"], {"title": "Gift boxes from 499"})
    c = S.draft("default", "New clinic hours")
    S.save("default", c["id"], {"title": "New clinic hours"})
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        _open(pg, base, vp)
        if vp["width"] > 900:
            assert pg.locator(".hx-pjr:not(.hd)").count() == 3
            # choose two, make a new folder for them
            pg.check(f"[data-pjsel='{a['id']}']")
            pg.check(f"[data-pjsel='{b['id']}']")
            assert "2 chosen" in pg.inner_text(".hx-pjbulk")
            pg.click("[data-a=pjbulk][data-k=move]")
            pg.wait_for_selector("[role=menu]", timeout=5000)
            pg.locator("[role=menuitem]:has-text('A new folder')").first.click()
            pg.wait_for_selector("#hxPjFn", timeout=5000)
            pg.fill("#hxPjFn", "Diwali sale")
            assert "The 2 chosen videos go into it" in pg.inner_text("#hxDlg")
            pg.click("[data-a=pjfsave]")
            _until(lambda: pg.locator(".hx-pjr:not(.hd)").count() == 2)        # opened on the new folder
            assert "Diwali sale" in pg.inner_text(".hx-pjf.on")
            # search inside All videos, then trash one from the bar
            pg.click(".hx-pjfb[data-id=all]")
            pg.fill("#hxPjq", "clinic")
            assert pg.locator(".hx-pjr:not(.hd)").count() == 1
            pg.fill("#hxPjq", "")
            if shots:
                pg.check(f"[data-pjsel='{c['id']}']")
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix203-projects-1440.png", full_page=True)
                pg.uncheck(f"[data-pjsel='{c['id']}']")
            pg.check(f"[data-pjsel='{c['id']}']")
            pg.click("[data-a=pjbulk][data-k=trash]")
            _until(lambda: pg.locator(".hx-pjr:not(.hd)").count() == 2)
            assert "1" in pg.inner_text(".hx-pjtr")
            # the trash: days left, bring back, delete now
            pg.click(".hx-pjtr")
            pg.wait_for_selector(".hx-pjtri", timeout=5000)
            assert "30 days left" in pg.inner_text(".hx-pjtri")
            if shots:
                pg.wait_for_timeout(300)
                pg.screenshot(path=f"{shots}/ix203-trash-1440.png", full_page=True)
            pg.click("[data-a=restore]")
            _until(lambda: "The trash is empty" in pg.inner_text(".hx-pjpage"))
            pg.click("[data-a=ptab][data-val=Videos]")
            pg.wait_for_selector(".hx-pjfs", timeout=5000)
            assert pg.locator(".hx-pjr:not(.hd)").count() == 3
            # remove the folder: its videos stay
            pg.click(".hx-pjfm")
            pg.wait_for_selector("[role=menu]", timeout=5000)
            pg.locator("[role=menuitem]:has-text('Remove the folder')").first.click()
            _until(lambda: pg.locator(".hx-pjf").count() == 2)
            assert len(S._load("default")["projects"]) == 3
        else:
            assert pg.locator(".hx-pjr:not(.hd)").count() == 3
        if shots:
            pg.wait_for_timeout(400)
            pg.screenshot(path=f"{shots}/ix203-projects-{vp['width']}-end.png", full_page=True)
        assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
        ctx.close()
    assert not errors, errors
