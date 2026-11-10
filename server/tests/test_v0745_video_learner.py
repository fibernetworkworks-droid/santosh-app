"""v0.745 VIDEO LEARNER REDESIGN (owner: "make all screen perfect and all feature functional" -> the approved canvas
-> "go"): live-streamed notes, Stop, the task page's own doors (detail / remove / proven), failures kept on the list,
and the four-screen page itself walked in a real browser."""
from __future__ import annotations

import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app import seekh as K
from app import seekh_console as SC
from tests.test_v0718_seekh_console import GOOD, client, wait_done
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401


@pytest.fixture()
def lv(env, monkeypatch, tmp_path):
    SC._JOBS.clear()
    monkeypatch.setattr(K, "_dir", lambda: tmp_path)
    monkeypatch.setattr(K, "_operator_home", lambda tenant: tmp_path / "op")
    (tmp_path / "op").mkdir()
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))
    yield tmp_path
    SC._JOBS.clear()


def test_stream_text_feeds_the_live_sink_and_honours_stop():
    class Chunk:
        def __init__(self, t): self.text = t

    class Models:
        def generate_content_stream(self, **kw): return iter([Chunk("1. [0:05] Open"), Chunk(" the site\n2. [0:20] Click")])
        def generate_content(self, **kw): raise AssertionError("must stream when a sink is set")

    class Client: models = Models()
    got = []
    K._LIVE.on_text, K._LIVE.cancel = got.append, None
    try:
        assert K._stream_text(Client(), "m", "c") == "1. [0:05] Open the site\n2. [0:20] Click"
        assert got == ["1. [0:05] Open", "1. [0:05] Open the site\n2. [0:20] Click"]
        ev = threading.Event(); ev.set(); K._LIVE.cancel = ev
        with pytest.raises(K.SeekhStopped):
            K._stream_text(Client(), "m", "c")
    finally:
        K._LIVE.on_text = K._LIVE.cancel = None


def test_live_notes_reach_the_page_then_stop_keeps_nothing(lv, monkeypatch):
    gate = threading.Event()

    def perceive(vid, tenant):          # writes a first note, then waits until the test has seen it
        K._LIVE.on_text("1. [0:05] Open the scholarship site")
        for _ in range(200):
            K._check_stop()
            if gate.is_set():
                break
            time.sleep(0.02)
        return "1. [0:05] Open the scholarship site"
    monkeypatch.setattr(K, "_perceive_youtube", perceive)
    c = client()
    jid = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()["id"]
    for _ in range(100):
        snap = c.get(f"/api/seekh/console/progress?id={jid}").json()
        if snap["perception"]:
            break
        time.sleep(0.02)
    assert snap["perception"] == "1. [0:05] Open the scholarship site" and not snap["done"]
    assert "partial" not in [s["k"] for s in snap["stages"]]          # live text is never a stage row
    assert snap["ref"] == "https://youtu.be/dQw4w9WgXcQ"
    assert c.post("/api/seekh/console/stop", json={"id": jid}).json()["ok"]
    out = wait_done(c, jid)
    assert out["stopped"] and out["result"] is None
    assert K.listing("default")["total"] == 0                          # Stop keeps nothing, not even a failure row


def test_failure_stays_on_the_list_and_does_not_count_today(lv, monkeypatch):
    def boom(vid, tenant):
        raise K.SeekhError("Google could not watch this video (it may be private).")
    monkeypatch.setattr(K, "_perceive_youtube", boom)
    c = client()
    jid = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ", "title": "IRCTC"}).json()["id"]
    out = wait_done(c, jid)
    assert out["error"] and not out["stopped"]
    w = c.get("/api/seekh/console/watches").json()
    row = w["watches"][0]
    assert row["status"] == "failed" and "private" in row["error"] and row["title"] == "IRCTC" and w["today"] == 0
    assert c.delete(f"/api/seekh/console/task?id={row['id']}").json()["ok"]
    assert c.get("/api/seekh/console/watches").json()["total"] == 0


def test_task_detail_proven_and_remove(lv, monkeypatch):
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: "1. [0:12] login")
    c = client()
    jid = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()["id"]
    pid = wait_done(c, jid)["result"]["procedure_id"]
    t = c.get(f"/api/seekh/console/task?id={pid}").json()
    assert t["status"] == "learned" and t["site"] == "scholarships.gov.in"
    assert [s["evidence"][0] for s in t["detail"]["steps"]] == ["0:12", "1:04", "2:41"]
    assert t["detail"]["steps"][1]["value_var"] == "full_name" and t["detail"]["gotchas"]
    assert c.post("/api/seekh/console/proven", json={"id": pid, "ok": True}).json()["wins"] == 1
    from app import procedures as pr
    assert next(p for p in pr.listing("default") if p["id"] == pid)["wins"] == 1   # the chat's hints learn it too
    recipe = (lv / "op")
    assert c.delete(f"/api/seekh/console/task?id={pid}").json()["ok"]
    assert c.get(f"/api/seekh/console/task?id={pid}").status_code == 404
    assert not any(p["id"] == pid for p in pr.listing("default"))
    assert not any(recipe.rglob("*.json")) or all(json.loads(p.read_text()).get("runs") for p in recipe.rglob("*.json"))


def test_old_rows_still_open_from_their_procedure(lv):
    from app import procedures as pr
    p = pr.save_video("default", "Old task", "seekh: video Old task",
                      [{"tool": "", "label": "1. open: login page opens [0:12]"}], ["OTP takes 6 digits"])
    K._save("default", [{"ts": "2026-11-01T10:00:00", "day": "2026-11-01", "source": "youtube:dQw4w9WgXcQ",
                         "title": "Old task", "procedure_id": p["id"], "steps": 1, "confidence": 0.7}])
    t = K.task("default", p["id"])
    assert t["detail"]["steps"][0]["evidence"] == ["0:12"] and "login page opens" in t["detail"]["steps"][0]["note"]


def test_console_csp_allows_only_the_youtube_player_and_thumbnails():
    from app import main
    assert "https://i.ytimg.com" in main._CONSOLE_CSP and "frame-src 'self' blob: https://www.youtube-nocookie.com" in main._CONSOLE_CSP
    assert "youtube.com " not in main._CONSOLE_CSP.replace("youtube-nocookie.com", "")


WATCHES = {"enabled": True, "max_per_day": 20, "today": 1, "running": "", "total": 3, "watches": [
    {"id": "p1", "procedure_id": "p1", "status": "learned", "title": "Fill the NSP scholarship form", "source": "youtube:dQw4w9WgXcQ",
     "ts": "2026-11-10T14:14:00", "steps": 3, "confidence": 0.82, "kind": "website_work", "site": "scholarships.gov.in", "wins": 0, "fails": 0},
    {"id": "p2", "procedure_id": "p2", "status": "learned", "title": "Download GST return", "source": "youtube:aaaaaaaaaaa",
     "ts": "2026-11-09T10:00:00", "steps": 6, "confidence": 0.9, "kind": "website_work", "site": "gst.gov.in", "wins": 2, "fails": 0},
    {"id": "f1", "status": "failed", "title": "<b>IRCTC</b>", "source": "youtube:bbbbbbbbbbb", "error": "The video is private.",
     "ts": "2026-11-10T09:00:00", "steps": 0, "confidence": 0}]}
TASK = {**WATCHES["watches"][0], "detail": {"steps": [
    {"n": 1, "action": "open", "note": "Open the site", "evidence": ["0:12"], "value_hint": "", "value_var": ""},
    {"n": 2, "action": "fill", "note": "Type the name", "evidence": ["1:04"], "value_hint": "as printed on Aadhaar", "value_var": "full_name"}],
    "preconditions": ["Aadhaar ready"], "gotchas": ["OTP takes 6 digits"], "unsure": []}}


def test_the_page_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/api/seekh/console/watches", lambda r: r.fulfill(json=WATCHES))
    pg.route("**/api/seekh/console/task?id=p1", lambda r: r.fulfill(json=TASK))
    pg.goto(base + "/console/")
    pg.wait_for_selector("#composer")
    pg.evaluate("document.querySelector('[data-v=\"seekh\"]') ? document.querySelector('[data-v=\"seekh\"]').click() : null")
    for _ in range(80):
        if pg.locator(".skv-row").count() == 3:
            break
        if pg.locator("[data-v='seekh']").count() == 0:
            pg.evaluate("location.hash='#seekh'")
        pg.wait_for_timeout(100)
    if pg.locator(".skv-row").count() != 3:          # the hub card may need the hub open first
        pg.evaluate("document.querySelector('.sn[data-v=\"hire\"]')?.click()")
        pg.wait_for_timeout(500)
        pg.locator(".ae-seekh").first.click()
        pg.wait_for_selector(".skv-row")
    home = pg.locator(".skv").text_content()
    assert "Your learned tasks" in home and "1 of 20 videos learned today" in home
    assert "Proven · worked 2 times" in home and "Learned · not tried yet" in home and "Could not learn" in home
    assert "<b>IRCTC</b>" in home                                       # her data shown as text, never markup
    assert pg.locator(".skv-thumb img").count() == 2                    # YouTube thumbnails for the two learned ones
    pg.locator(".skv-filters [data-filter=proven]").click()
    assert pg.locator(".skv-row").count() == 1
    pg.locator(".skv-filters [data-filter=all]").click()
    pg.locator(".skv-title", has_text="Fill the NSP").click()
    pg.wait_for_selector(".skv-steps li")
    page = pg.locator(".skv").text_content()
    assert "The steps Hoola learned" in page and "Before you start" in page and "Watch out" in page
    assert pg.locator(".skv-steps .skv-ts").first.text_content() == "0:12"
    assert pg.locator("#skvForm input[data-label='Full name']").count() == 1   # a box for what the task needs
    assert "82%" in page
    assert not errs, errs
    ctx.close()
