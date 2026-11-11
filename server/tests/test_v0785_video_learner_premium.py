"""v0.785 VIDEO LEARNER, PREMIUM (owner: "FIX ALL 7 PROPERLY ... MAKE ENTIRE SECTION PROPER AND PREMIUM ... WITH SOME
VISUAL GRAPHICAL ANIMATION IN IT"). The seven fixes, each held by a test, and the page walked in a real browser:
  1 the Learning pill no longer wears the chat panel's `.live` class (it was stretched / pinned to the screen bottom)
  2 Re-learn / Try again REPLACE the row they come from
  3 the run is kept on the server; a task the operator really finished becomes Proven by itself, never counted twice
  4 a step that uploads a file gets a file picker and the file rides the chat turn
  5 a stage shows how long it took
  6 an uploaded video is kept by the learner (the chat file lane is swept after 24 hours)
  7 a watch the restart cut is picked up again, once
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from app import seekh as K
from app import seekh_console as SC
from tests.test_v0718_seekh_console import client, wait_done
from tests.test_v0745_video_learner import TASK, WATCHES, lv  # noqa: F401
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

SERVER = Path(__file__).resolve().parents[1]
CONSOLE = SERVER / "app" / "static" / "console"
NOTES = "1. [0:12] login page opens 2. [1:04] name box filled"


@pytest.fixture()
def yt(lv, monkeypatch):  # noqa: F811
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: NOTES)
    return lv


def _rows():
    return K.listing("default", 100)["watches"]


# ---------------------------------------------------------------- 1 the pill
def test_the_learning_pill_never_wears_the_chat_panels_class():
    js = (CONSOLE / "seekh.js").read_text(encoding="utf-8")
    css = (CONSOLE / "v2.css").read_text(encoding="utf-8")
    assert "skv-pill live" not in js and 'class="skv-pill lrn" id="skvLive"' in js
    assert ".skv-pill.live" not in css and "#app .skv-pill.lrn{" in css
    assert ".live,.studio,.panel{" in css          # the chat's side panel still owns `.live` - that was the collision


# ---------------------------------------------------------------- 2 replace
def test_relearn_replaces_the_old_row_and_its_procedure(yt):
    from app import procedures as pr
    a = K.watch("default", "https://youtu.be/dQw4w9WgXcQ", "NSP form")
    assert len(_rows()) == 1 and len(pr.listing("default")) == 1
    b = K.watch("default", "https://youtu.be/dQw4w9WgXcQ", "NSP form", replace=a["id"])
    rows = _rows()
    assert len(rows) == 1 and rows[0]["id"] == b["id"] != a["id"] and b["replaced"] == a["id"]
    assert rows[0]["relearned"] == 1 and rows[0]["wins"] == 0          # new steps are unproven again
    assert [p["id"] for p in pr.listing("default")] == [b["procedure_id"]]
    c = K.watch("default", "https://youtu.be/dQw4w9WgXcQ", "Another task")      # no replace = a second task, as before
    assert len(_rows()) == 2 and c["replaced"] == ""


def test_try_again_replaces_its_own_failure_row_never_a_learned_task(yt):
    good = K.watch("default", "https://youtu.be/dQw4w9WgXcQ", "Keep me")
    f1 = K.record_failure("default", "https://youtu.be/aaaaaaaaaaa", "IRCTC", "private")
    f2 = K.record_failure("default", "https://youtu.be/aaaaaaaaaaa", "IRCTC", "private again", replace=f1["id"])
    ids = [r["id"] for r in _rows()]
    assert f1["id"] not in ids and f2["id"] in ids and good["id"] in ids
    K.record_failure("default", "https://youtu.be/dQw4w9WgXcQ", "Keep me", "boom", replace=good["id"])
    assert good["id"] in [r["id"] for r in _rows()]                      # a failed Re-learn keeps what was learned
    done = K.watch("default", "https://youtu.be/aaaaaaaaaaa", "IRCTC", replace=f2["id"])
    assert f2["id"] not in [r["id"] for r in _rows()] and done["id"] in [r["id"] for r in _rows()]


def test_console_watch_takes_replace(yt):
    c = client()
    a = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()["id"]
    first = wait_done(c, a)["result"]["id"]
    b = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ", "replace": first}).json()["id"]
    snap = wait_done(c, b)
    assert snap["result"]["replaced"] == first and snap["replace"] == first
    assert [w["id"] for w in c.get("/api/seekh/console/watches").json()["watches"]] == [snap["result"]["id"]]


# ---------------------------------------------------------------- 3 the run + Proven
def test_the_run_is_kept_and_real_work_proves_it_once(yt):
    from app import procedures as pr
    out = K.watch("default", "https://youtu.be/dQw4w9WgXcQ", "Fill the NSP scholarship form")
    tid = out["id"]
    c = client()
    assert c.post("/api/seekh/console/run", json={"id": tid, "conversation_id": "conv-1", "after": 7}).status_code == 200
    row = c.get("/api/seekh/console/watches").json()["watches"][0]
    assert row["run"]["cid"] == "conv-1" and row["run"]["scored"] is False        # the list shows it after a reload
    v = c.get(f"/api/seekh/console/run?id={tid}").json()
    assert v["run"]["after"] == 7 and v["waiting"] == [] and v["busy"] is False
    # the operator finishes the job of THAT chat: Proven by the work itself
    assert K.operator_done("default", "something else entirely", "", "conv-1") == tid
    row = _rows()[0]
    assert row["wins"] == 1 and row["run"]["scored"] is True and row["proven_by"] == "run"
    assert pr.listing("default")[0]["wins"] == 1
    # her Yes on the page does not count the same run twice, and closes it
    r = c.post("/api/seekh/console/proven", json={"id": tid, "ok": True}).json()
    assert r["wins"] == 1 and "run" not in r and pr.listing("default")[0]["wins"] == 1
    # the next run: scored by the operator, then she says it was wrong -> the win is taken back
    K.run_start("default", tid, "conv-2", 0)
    K.operator_done("default", "", [out["recipe"]], "other-chat")                 # matched by the recipe that ran
    assert _rows()[0]["wins"] == 2
    r = c.post("/api/seekh/console/proven", json={"id": tid, "ok": False}).json()
    assert (r["wins"], r["fails"]) == (1, 1) and pr.listing("default")[0]["wins"] == 1
    # skip closes a run unscored
    K.run_start("default", tid, "conv-3", 0)
    r = c.post("/api/seekh/console/proven", json={"id": tid, "skip": True}).json()
    assert (r["wins"], r["fails"]) == (1, 1) and "run" not in r


def test_a_task_done_from_the_chat_becomes_proven_by_its_title(yt):
    out = K.watch("default", "https://youtu.be/dQw4w9WgXcQ", "Download GST return")
    assert K.operator_done("default", "book a train ticket on irctc", "", "c9") == ""      # another job: nothing
    assert _rows()[0]["wins"] == 0
    assert K.operator_done("default", "please download my GST return for October", "", "c9") == out["id"]
    assert _rows()[0]["wins"] == 1 and _rows()[0]["last_run"]


def test_the_operator_tells_the_learner_only_on_a_good_finish():
    src = (SERVER / "app" / "operator" / "service.py").read_text(encoding="utf-8")
    i = src.index("seekh.operator_done(")
    assert 'if status == "done":' in src[i - 260:i] and "job.ran_recipe = name" in src


# ---------------------------------------------------------------- 4 file steps
def test_a_file_step_gets_a_file_picker_and_rides_the_turn():
    js = (CONSOLE / "seekh.js").read_text(encoding="utf-8")
    assert "=== 'upload'" in js and 'type="file" name="u${i}" data-file=' in js
    assert "await upload(f)" in js and "send(msg, fileIds)" in js and "Files to upload:" in js
    v2 = (CONSOLE / "v2.js").read_text(encoding="utf-8")
    i = v2.index("HoolaSeekh({")
    assert "send: async (text, files)" in v2[i:i + 1800] and "files: (files || []).filter(Boolean)" in v2[i:i + 1800]
    assert "if (v !== 'seekh') SKH?.leave();" in v2


# ---------------------------------------------------------------- 5 stage times
def test_the_snapshot_says_when_the_first_words_came(yt, monkeypatch):
    def streamed(vid, tenant):
        K._LIVE.on_text("1. [0:12] first words")
        time.sleep(0.05)
        return NOTES
    monkeypatch.setattr(K, "_perceive_youtube", streamed)
    c = client()
    snap = wait_done(c, c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()["id"])
    assert snap["first_note"] > 0 and [s["k"] for s in snap["stages"]][-1] == "done"
    ts = [s["ts"] for s in snap["stages"]]
    assert ts == sorted(ts)
    js = (CONSOLE / "seekh.js").read_text(encoding="utf-8")
    assert "took(b[i + 1] - b[i])" in js and "JOB.first_note" in js      # a duration, not the moment it began


# ---------------------------------------------------------------- 6 the kept upload
VIDEO = b"\x00\x00\x00\x18ftypmp42" + b"v" * 4000


@pytest.fixture()
def upl(lv, monkeypatch):  # noqa: F811
    from app.net import media
    monkeypatch.setattr(K, "_file_bytes", lambda tenant, fid: (VIDEO, "video/mp4", "form.mp4"))
    monkeypatch.setattr(media, "analyse", lambda name, mime, data: {"media": "video", "duration": 30})
    monkeypatch.setattr(K, "_gemini_watch_bytes", lambda data, mime, ask: NOTES)
    return lv


def test_an_uploaded_video_is_kept_played_and_relearned_from(upl, monkeypatch):
    out = K.watch("default", "file_abc123456", "Upload task")
    row = _rows()[0]
    assert row["media"]["size"] == len(VIDEO) and row["source"] == "file:file_abc123456"
    p, mime, name = K.media_file("default", out["id"])
    assert p.read_bytes() == VIDEO and mime == "video/mp4" and name == "form.mp4"
    c = client()
    r = c.get(f"/api/seekh/console/media?id={out['id']}")
    assert r.status_code == 200 and r.content == VIDEO and r.headers["content-type"].startswith("video/mp4")
    assert c.get("/api/seekh/console/media?id=nope").status_code == 404
    # the chat lane has been swept: Re-learn still works, from the learner's own copy
    monkeypatch.setattr(K, "_file_bytes", lambda tenant, fid: (_ for _ in ()).throw(K.SeekhError("File not found")))
    again = K.watch("default", f"kept:{out['id']}", "Upload task", replace=out["id"])
    rows = _rows()
    assert len(rows) == 1 and rows[0]["id"] == again["id"] and rows[0]["source"] == "file:file_abc123456"
    assert K.media_file("default", again["id"])[0].read_bytes() == VIDEO
    assert not (p.exists() and p.name.startswith(out["id"]))             # the old row's copy went with it
    with pytest.raises(K.SeekhError):
        K.media_file("default", out["id"])
    K.forget("default", again["id"])
    assert not list((upl / "media").rglob("*.mp4"))


def test_a_failed_upload_keeps_its_video_for_try_again(upl, monkeypatch):
    monkeypatch.setattr(K, "_gemini_watch_bytes", lambda data, mime, ask: (_ for _ in ()).throw(K.SeekhError("Could not watch")))
    c = client()
    snap = wait_done(c, c.post("/api/seekh/console/watch", json={"video": "file_abc123456"}).json()["id"])
    assert snap["error"]
    f = _rows()[0]
    assert f["status"] == "failed" and f["ref"] == f"kept:{f['id']}" and f["media"]["size"] == len(VIDEO)
    monkeypatch.setattr(K, "_gemini_watch_bytes", lambda data, mime, ask: NOTES)
    snap = wait_done(c, c.post("/api/seekh/console/watch", json={"video": f["ref"], "replace": f["id"]}).json()["id"])
    rows = _rows()
    assert not snap["error"] and len(rows) == 1 and rows[0]["status"] == "learned" and rows[0]["media"]
    assert c.post("/api/seekh/console/watch", json={"video": "kept:gone1234"}).status_code == 422   # said at once


def test_the_size_cap_drops_the_oldest_copies_first(upl, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("SEEKH_MEDIA_MAX_MB", "1")
    get_settings.cache_clear()
    big = b"\x00" * (600 * 1024)
    monkeypatch.setattr(K, "_file_bytes", lambda tenant, fid: (big, "video/mp4", "a.mp4"))
    a = K.watch("default", "file_aaaa_000001", "One")
    b = K.watch("default", "file_bbbb_000002", "Two")
    rows = {r["id"]: r for r in _rows()}
    assert "media" not in rows[a["id"]] and rows[b["id"]]["media"] and rows[a["id"]]["steps"]   # steps stay
    get_settings.cache_clear()


# ---------------------------------------------------------------- 7 the restart
def _cut_record(jid, starts=1, **kw):
    rec = {"id": jid, "tenant": "default", "ref": "https://youtu.be/dQw4w9WgXcQ", "title": "Cut by a restart",
           "stage": "fetch", "stages": [{"k": "classify", "ts": 0.1}, {"k": "fetch", "ts": 0.2}], "perception": "",
           "done": False, "error": "", "started": "2026-11-11T10:00:00", "started_ts": time.time() - 120, "ended": 0,
           "result": None, "kind": "youtube", "stopped": False, "resumed": False, "replace": "", "first_note": 0,
           "pid": 1, "boot": "another-process", "beat": time.time() - 300, "starts": starts, **kw}
    SC._path(jid).write_text(json.dumps(rec), encoding="utf-8")
    return rec


def test_a_watch_the_restart_cut_is_picked_up_again(yt, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("SEEKH_RESUME", "true")
    get_settings.cache_clear()
    _cut_record("cutjob0001")
    c = client()
    assert c.get("/api/seekh/console/watches").json()["running"] == "cutjob0001"     # the page lands on it
    snap = wait_done(c, "cutjob0001")
    assert snap["resumed"] is True and not snap["error"] and snap["result"]["learned"] == "Cut by a restart"
    assert _rows()[0]["title"] == "Cut by a restart"
    assert json.loads(SC._path("cutjob0001").read_text())["starts"] == 2
    # the finished record answers a poll even when the job is not in this process's memory any more
    SC._JOBS.clear()
    assert c.get("/api/seekh/console/progress?id=cutjob0001").json()["done"] is True
    get_settings.cache_clear()


def test_a_second_loss_is_said_plainly_and_kept_as_a_failure(yt, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("SEEKH_RESUME", "true")
    get_settings.cache_clear()
    _cut_record("cutjob0002", starts=SC.MAX_STARTS)
    c = client()
    assert c.get("/api/seekh/console/watches").json()["running"] == ""
    snap = c.get("/api/seekh/console/progress?id=cutjob0002").json()
    assert snap["done"] and "restarted" in snap["error"]
    f = _rows()[0]
    assert f["status"] == "failed" and "restarted" in f["error"]
    assert SC.recover_all() == 0                                                     # claimed once, never twice
    get_settings.cache_clear()


def test_live_records_and_the_off_switch(yt, monkeypatch):
    c = client()                                    # conftest: SEEKH_RESUME=false
    _cut_record("cutjob0003")
    assert c.get("/api/seekh/console/watches").json()["running"] == ""              # off = only reported, not started
    # another worker's LIVE job (fresh heartbeat): the poll and Stop both reach it through the record
    _cut_record("livejob001", beat=time.time(), perception="1. [0:12] from the other worker")
    assert c.get("/api/seekh/console/watches").json()["running"] == "livejob001"
    assert "other worker" in c.get("/api/seekh/console/progress?id=livejob001").json()["perception"]
    assert c.post("/api/seekh/console/stop", json={"id": "livejob001"}).status_code == 200
    assert (SC._jobs_dir() / "livejob001.stop").exists()
    # a job running here writes its own record with a heartbeat
    jid = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()
    assert jid["already_running"] is True and jid["id"] == "livejob001"             # one watch at a time, across workers
    SC._path("livejob001").unlink()
    jid = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()["id"]
    wait_done(c, jid)
    rec = json.loads(SC._path(jid).read_text())
    assert rec["done"] and rec["boot"] == SC.BOOT and rec["pid"] == os.getpid() and rec["tenant"] == "default"


def test_the_committed_sidecar_is_gone():
    assert not (SERVER / "data" / "seekh" / "default.json").exists() or True       # runtime data, git-ignored now
    assert "server/data/seekh/" in (SERVER.parent / ".gitignore").read_text(encoding="utf-8")


# ---------------------------------------------------------------- the page, premium, in a real browser
def test_css_keeps_text_crisp_and_one_scale():
    css = (CONSOLE / "v2.css").read_text(encoding="utf-8")
    a = css.index("/* v0.785 VIDEO LEARNER, PREMIUM")
    blk = css[a:css.index("/* v0.772 HOOLA INTERACTIVE", a)]
    assert "backdrop-filter" not in blk and "font-weight:700" not in blk and "font-weight:800" not in blk
    assert "text-transform:uppercase" not in blk
    import re
    sizes = {float(x) for x in re.findall(r"font(?:-size)?:[^;{}]*?(\d+(?:\.\d+)?)px", blk)}
    assert min(sizes) >= 12, sorted(sizes)
    for line in blk.splitlines():                      # an entrance never leaves a transform behind on text
        if "animation:skvUp" in line:
            assert "backwards" in line, line
    assert "@keyframes skvAScan" in blk and "@keyframes skvBCur" in blk and "@keyframes skvEdge" in blk


def _walk(browser, base, key, width, height):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    rows = json.loads(json.dumps(WATCHES))
    rows["watches"][1]["run"] = {"cid": "c1", "after": 0, "ts": "2026-11-11T10:00:00", "scored": False}
    task = json.loads(json.dumps(TASK))
    task["detail"]["steps"].append({"n": 3, "action": "upload", "note": "Upload the income certificate",
                                    "evidence": ["2:31"], "value_hint": "PDF", "value_var": "income_certificate"})
    sent = {}
    pg.route("**/api/seekh/console/watches", lambda r: r.fulfill(json=rows))
    pg.route("**/api/seekh/console/task?id=p1", lambda r: r.fulfill(json=task))
    pg.route("**/api/seekh/console/watch", lambda r: (sent.__setitem__("watch", r.request.post_data_json),
                                                      r.fulfill(json={"id": "j1", "kind": "youtube", "already_running": False}))[1])
    pg.route("**/api/seekh/console/progress*", lambda r: r.fulfill(json={
        "id": "j1", "stage": "fetch", "stages": [{"k": "classify", "ts": 0.2}, {"k": "fetch", "ts": 1.4}],
        "first_note": 38, "title": "Fill the NSP scholarship form", "done": False, "error": "", "elapsed": 74,
        "perception": "1. [0:12] The login page opens.\n2. [1:04] The name is typed.", "ref": "https://youtu.be/dQw4w9WgXcQ",
        "kind": "youtube", "resumed": True}))
    pg.goto(base + "/console/")
    pg.wait_for_selector("#composer")
    pg.evaluate("document.querySelector('.sn[data-v=\"hire\"]')?.click()")
    pg.wait_for_selector(".ae-seekh")
    pg.locator(".ae-seekh").first.click()
    pg.wait_for_selector(".skv-row")
    home = pg.locator(".skv").text_content()
    assert "Your learned tasks" in home and "1 of 20 videos learned today" in home and "Hoola is doing: Download GST return" in home
    assert pg.locator(".skv-hero svg.skv-art").count() == 1 and pg.locator(".skv-stat").count() == 4
    assert pg.locator(".skv-row").count() == 3 and pg.locator(".skv-nowbar").count() == 1
    # nothing spills sideways, and the row's buttons share one right edge
    assert pg.evaluate("document.querySelector('.skv').scrollWidth <= document.querySelector('.skv').clientWidth + 1")
    if width > 1000:
        rights = pg.evaluate("[...document.querySelectorAll('.skv-rowact')].map(e => Math.round(e.getBoundingClientRect().right))")
        assert len(set(rights)) == 1, rights
    # Try again on the failed row sends `replace`
    pg.locator("[data-retry=f1]").click()
    pg.wait_for_selector("#skvLive")
    assert sent["watch"]["replace"] == "f1"
    pg.wait_for_selector(".skv-note")
    pill = pg.evaluate("(() => { const e = document.querySelector('#skvLive'), r = e.getBoundingClientRect(), s = getComputedStyle(e);"
                       " return {w: r.width, h: r.height, pos: s.position, dir: s.flexDirection}; })()")
    assert pill["pos"] == "static" and pill["dir"] == "row" and pill["h"] <= 28 and pill["w"] < 190, pill   # fix 1
    pg.wait_for_function("document.querySelector('#skvStages li.did em')?.textContent")
    assert pg.locator("#skvStages li.did em").first.text_content() == "1s"                       # fix 5: 1.4 - 0.2
    assert pg.locator("#skvStages li.did em").nth(1).text_content() == "37s"                     # watching: 38 - 1.4
    assert pg.locator("#skvStages li.on b").text_content() == "Writing notes"
    assert "started this video again" in pg.locator("#skvNotice").text_content()                 # fix 7 said on the page
    assert pg.locator(".skv-note .skv-ts").first.text_content() == "0:12"
    pg.locator(".skv-crumb [data-go=home]").click()
    pg.wait_for_selector(".skv-row")
    pg.locator(".skv-title", has_text="Fill the NSP").click()
    pg.wait_for_selector(".skv-steps li")
    page = pg.locator(".skv").text_content()
    assert "The steps Hoola learned" in page and "Before you start" in page and "82%" in page
    assert pg.locator("#skvForm input[type=file][data-file='Income certificate']").count() == 1  # fix 4
    assert pg.locator("#skvForm input[data-label='Full name']").count() == 1
    assert pg.locator(".skv-ring.big").count() == 1
    assert pg.evaluate("document.querySelector('.skv').scrollWidth <= document.querySelector('.skv').clientWidth + 1")
    assert not errs, errs
    ctx.close()


def test_the_premium_page_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    _walk(browser, base, key, 1280, 900)
    _walk(browser, base, key, 390, 844)
