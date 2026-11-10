"""v0.718 SEEKH MANCH ON THE CONSOLE - the HOOLA AI Video Learner panel, end to end
(owner: "NOW WE WILL DEVELOP A CONSOLE PAGE FOR IT - CHECK THE EXISTING CONSOLE DESIGN AND IN AI EMPLOYEE
SECTION BUILD THE HOOLA AI VIDEO LEARNER. In that, a panel where user can load a video and HOOLA AI will
see this and note in REALTIME. Once done, HOOLA AI will prepare a MEMORY for this. And IN THIS PAGE ONLY
user will tell HOOLA to PERFORM THIS TASK NOW - then HOOLA will use HIS BROWSER for doing that task"
+ "PERFECT START THE DEPLOYMENT" on the prototype shown in chat; born as v0716 in the collision round - their NAYA ROOP and FILE CARD SAHI took the next two version slots while it sat built, REBASE PROTOCOL onto their tip with their code kept whole; ships as v0718).

WHAT THIS SUITE HOLDS:
- the lane (/api/seekh/console/*): key-protected, tenant-scoped, one watch at a time (a second start
  ADOPTS the running job, a reload re-adopts it), the progress pulse, honest 404 / 422 / 403 / 401;
- the job lifecycle: every stage the panel shows is a REAL boundary of seekh.watch (classify -> fetch ->
  notes -> distill_start -> distill -> memory -> done) - patched at the module seam exactly like the
  v0713 suite (the perception and distill doors), zero network;
- PERFORM IS NOT AN ENDPOINT: the panel composes one honest chat turn (the same door the composer uses),
  so the task runs through the agent and the computer operator's own browser - pinned by test;
- the console files: the #v-seekh view, seekh.js (the panel), the hub card inside AI Employees, the v2.js
  wiring, the styles; the frozen PC zone is untouched (the lane never imports the operator stack - seekh.py
  is the only one that saves through its public Memory door, and that was v0.713).
"""
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import seekh as K
from app import seekh_console as SC
from app.agent import tools as T

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"
CONSOLE = SERVER / "app" / "static" / "console"

# the same well-formed distill result the v0713 suite uses (what brain.think would answer)
GOOD = {
    "title": "NSP scholarship form bharne ka tareeka",
    "kind": "website_work", "site": "scholarships.gov.in", "start_url": "https://scholarships.gov.in/",
    "steps": [
        {"n": 1, "action": "open", "target": None, "evidence": ["0:12"], "note": "login page opens"},
        {"n": 2, "action": "fill", "target": {"role": "textbox", "name": "Applicant Name"},
         "value_var": "full_name", "value_hint": "as printed on Aadhaar", "evidence": ["1:04"], "note": ""},
        {"n": 3, "action": "click", "target": {"role": "button", "name": "Submit"}, "evidence": ["2:41"],
         "note": "final submit"},
    ],
    "preconditions": ["Aadhaar ready", "mobile with OTP in reach"],
    "gotchas": ["OTP box takes only 6 digits"],
    "variables": {"full_name": {"field": "Applicant Name", "why": "differs per person"}},
    "confidence": 0.78, "unsure": ["could not read the menu label at 2:10 (blurry)"],
}


@pytest.fixture()
def seekh_env(env, monkeypatch):
    """Fresh job ring + instant doors: the whole suite is offline, the thread finishes in milliseconds."""
    SC._JOBS.clear()
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: "1. [0:12] login page opens 2. [1:04] name box filled")
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))
    yield
    SC._JOBS.clear()


def client():
    return TestClient(__import__("app.main", fromlist=["app"]).app)


def wait_done(c, jid, deadline_s=15.0):
    """The panel's 1.2 s pulse, run to the end."""
    end = time.time() + deadline_s
    last = {}
    while time.time() < end:
        last = c.get(f"/api/seekh/console/progress?id={jid}").json()
        if last.get("done"):
            return last
        time.sleep(0.05)
    return last


# ---------------------------------------------------------------- 1. the lane (8)

def test_router_mounted_with_three_doors():
    paths = {getattr(r, "path", "") for r in __import__("app.main", fromlist=["app"]).app.routes}
    assert "/api/seekh/console/watch" in paths
    assert "/api/seekh/console/progress" in paths
    assert "/api/seekh/console/watches" in paths


def test_key_protected(env, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("API_KEY", "test-key-0718")
    get_settings.cache_clear()
    c = client()
    assert c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).status_code == 401
    assert c.get("/api/seekh/console/watches").status_code == 401
    assert c.get("/api/seekh/console/progress?id=x").status_code == 401


def test_watch_needs_a_video(seekh_env):
    c = client()
    r = c.post("/api/seekh/console/watch", json={})
    assert r.status_code == 422 and "Which video" in r.json()["detail"]


def test_watch_junk_is_honest(seekh_env):
    r = client().post("/api/seekh/console/watch", json={"video": "yeh video dekho!! @#$"})
    assert r.status_code == 422 and "does not look like a video" in r.json()["detail"]


def test_watch_off_is_403(env, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("SEEKH_ENABLED", "false")
    get_settings.cache_clear()
    r = client().post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 403 and "switched off" in r.json()["detail"]


def test_unknown_progress_is_404(seekh_env):
    r = client().get("/api/seekh/console/progress?id=nope")
    assert r.status_code == 404 and "restart" in r.json()["detail"]


def test_perform_is_not_an_endpoint(seekh_env):
    """The panel composes one honest chat turn; the operator lane is the only doer. No perform route, ever."""
    paths = {getattr(r, "path", "") for r in __import__("app.main", fromlist=["app"]).app.routes}
    assert not any("perform" in p for p in paths if p.startswith("/api/seekh"))


def test_the_lane_never_imports_the_operator_stack():
    """The frozen zone law: seekh.py (v0.713) is the only saver through the public Memory door."""
    src = (SERVER / "app" / "seekh_console.py").read_text(encoding="utf-8")
    imports = [l.strip() for l in src.splitlines() if l.strip().startswith(("from ", "import "))]
    assert not any("operator" in l or ".pc" in l or "desktop" in l for l in imports), imports


# ---------------------------------------------------------------- 2. the job lifecycle (6)

def test_watch_to_memory_end_to_end(seekh_env):
    c = client()
    r = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ", "title": "Scholarship form"})
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "youtube" and not r.json()["already_running"]
    out = wait_done(c, r.json()["id"])
    assert out["done"] and not out["error"], out
    # every stage the panel shows, in the pipeline's own order
    assert [s["k"] for s in out["stages"]] == ["classify", "fetch", "notes", "distill_start", "distill", "memory", "done"]
    assert out["perception"].startswith("1. [0:12]")
    res = out["result"]
    assert res["learned"] == "Scholarship form" and res["kind"] == "website_work"
    assert [s["evidence"][0] for s in res["steps"]] == ["0:12", "1:04", "2:41"]
    assert res["recipe"] and "NOT proven" in res["note_for_you"]
    # the two real memories landed (the v0.713 organs, unchanged)
    from app import procedures as pr
    rows = pr.listing("default")
    assert rows and rows[0]["title"] == "Scholarship form" and rows[0]["wins"] == 0
    st = K.listing("default")
    assert st["total"] == 1 and st["watches"][0]["source"] == "youtube:dQw4w9WgXcQ"


def test_the_two_memories_are_written_once(seekh_env):
    """A console watch is exactly one seekh.watch: the procedure row and the sidecar row, never two."""
    c = client()
    r = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"})
    out = wait_done(c, r.json()["id"])
    assert out["done"]
    from app import procedures as pr
    assert len(pr.listing("default")) == 1
    assert K.listing("default")["total"] == 1


def test_error_is_honest(seekh_env, monkeypatch):
    def boom(vid, tenant):
        raise K.SeekhError("Could not watch the video (the file is broken)")
    monkeypatch.setattr(K, "_perceive_youtube", boom)
    c = client()
    r = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"})
    out = wait_done(c, r.json()["id"])
    assert out["done"] and out["stage"] == "error"
    assert "broken" in out["error"] and out["result"] is None


def test_one_watch_at_a_time_adopts_the_running_job(seekh_env, monkeypatch):
    def slow(vid, tenant):
        time.sleep(1.2)
        return "1. [0:12] slow notes"
    monkeypatch.setattr(K, "_perceive_youtube", slow)
    c = client()
    first = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()
    second = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()
    assert second["id"] == first["id"] and second["already_running"] is True
    out = wait_done(c, first["id"])
    assert out["done"] and not out["error"]


def test_a_reload_adopts_the_running_job(seekh_env, monkeypatch):
    def slow(vid, tenant):
        time.sleep(1.0)
        return "1. [0:20] notes"
    monkeypatch.setattr(K, "_perceive_youtube", slow)
    c = client()
    r = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()
    adopted = c.get("/api/seekh/console/progress?id=").json()      # the empty id after a page reload
    assert adopted["id"] == r["id"] and not adopted["done"]
    assert wait_done(c, r["id"])["done"]


def test_watches_lists_the_sidecar_with_caps(seekh_env):
    c = client()
    r = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"})
    wait_done(c, r.json()["id"])
    w = c.get("/api/seekh/console/watches").json()
    assert w["enabled"] is True and w["today"] == 1 and w["total"] == 1 and w["running"] == ""
    assert w["watches"][0]["title"] == "NSP scholarship form bharne ka tareeka"
    assert w["watches"][0]["steps"] == 3


# ---------------------------------------------------------------- 3. the progress door (4)

def test_snapshot_shape_is_what_the_panel_reads(seekh_env):
    c = client()
    jid = c.post("/api/seekh/console/watch", json={"video": "https://youtu.be/dQw4w9WgXcQ"}).json()["id"]
    snap = c.get(f"/api/seekh/console/progress?id={jid}").json()
    assert set(snap) >= {"id", "stage", "stages", "title", "perception", "done", "error", "elapsed", "started", "result"}
    assert all({"k", "ts"} <= set(s) for s in snap["stages"])


def test_tenant_isolation_of_the_job_ring(seekh_env):
    """A job is only ever adopted by its own tenant (the unit truth under the dependency)."""
    import uuid
    with SC._LOCK:
        for t in ("tenant-a", "tenant-b"):
            SC._JOBS[uuid.uuid4().hex[:8]] = {"id": "x", "tenant": t, "stage": "fetch", "stages": [],
                                              "started": time.time(), "started_iso": "", "title": "",
                                              "perception": "", "done": False, "error": "", "result": None,
                                              "ended": 0.0}
    assert SC._running_for("tenant-a") and SC._running_for("tenant-b")
    assert SC._running_for("tenant-a") != SC._running_for("tenant-b")
    assert SC._running_for("tenant-c") == ""


def test_on_stage_is_a_noop_without_a_sink(seekh_env):
    """The v0.713 callers (the tool, the old tests) pass no callback - watch still works."""
    out = K.watch("default", "https://youtu.be/dQw4w9WgXcQ")
    assert out["learned"] == "NSP scholarship form bharne ka tareeka"


def test_a_broken_sink_never_breaks_the_watch(seekh_env, monkeypatch):
    def bad_sink(stage, data):
        raise RuntimeError("UI sank")
    out = K.watch("default", "https://youtu.be/dQw4w9WgXcQ", on_stage=bad_sink)
    assert out["procedure_id"] and out["steps"]


# ---------------------------------------------------------------- 4. the console files (7)

def test_view_and_script_in_v2html():
    html = (CONSOLE / "v2.html").read_text(encoding="utf-8")
    assert 'id="v-seekh"' in html and 'aria-label="Video Learner"' in html
    assert '<script src="/static/console/seekh.js?v=' in html


def test_the_panel_pins():
    """v0.745 the redesigned page: the four screens, the real stages, the honest run and the limits."""
    js = (CONSOLE / "seekh.js").read_text(encoding="utf-8")
    assert "window.HoolaSeekh" in js
    assert "'Opened the video'" in js and "'Watching'" in js and "'Writing notes'" in js and "'Saving to memory'" in js
    assert "Hoola's notes" in js and "Your learned tasks" in js and "The steps Hoola learned" in js
    assert "Do it now" in js and "Did it work?" in js
    # the run: one honest chat turn, her own browser, she is asked before anything is sent
    i = js.index("Do the learned task")
    assert "own browser" in js[i:i + 700] and "Ask me before sending or submitting anything" in js[i:i + 700]
    # the pulse and the honest limits
    assert "1200" in js and "25 MB" in js
    # every server value goes through esc()
    assert "esc(r.title" in js and "esc(t.title" in js


def test_hub_card_inside_ai_employees():
    js = (CONSOLE / "employees.js").read_text(encoding="utf-8")
    assert "HOOLA AI Video Learner" in js
    i = js.index("ae-seekh")
    card = js[i:i + 900]
    assert 'data-v="seekh"' in card and "Open Video Learner" in card
    assert "Teach Hoola any task from a video" in card and "its own browser" in card


def test_v2js_wiring():
    js = (CONSOLE / "v2.js").read_text(encoding="utf-8")
    assert "IC.seekh" in js
    assert "seekh:'· Video Learner'" in js
    assert "SKH?.open($('#seekh'))" in js
    assert "window.HoolaSeekh" in js and "HoolaSeekh({" in js
    # the panel's send/upload ride the chat doors (no new server surface)
    i = js.index("HoolaSeekh({")
    wiring = js[i:i + 1400]
    assert "/api/conversations\"?reuse=1" in wiring.replace("`", "").replace("${", "") or "reuse=1" in wiring
    assert "/messages" in wiring and "/files" in wiring


def test_styles_exist():
    css = (CONSOLE / "v2.css").read_text(encoding="utf-8")
    for cls in (".sk-card", ".sk-steps", ".sk-notes", ".sk-msteps", ".sk-conf", ".ae-seekh", ".sk-sent"):
        assert cls in css, cls


def test_no_new_tool_road_the_registry_stays():
    assert len(T.TOOLS) == 621, "the console page adds NO tool - it drives the v0.713 seekh_video organs"


def test_version_pins():
    main = (SERVER / "app" / "main.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.760.0"' in main and "SEEKH MANCH ON THE CONSOLE v0.718.0" in main
    pub = ROOT / "pubspec.yaml"
    assert "version: 0.760.0+759" in pub.read_text(encoding="utf-8")
    html = (CONSOLE / "v2.html").read_text(encoding="utf-8")
    assert "console/seekh.js?v=0.748.0" in html and "console/v2.js?v=0.748.0" in html
