"""v0.655 KAAM DIKHE: the Web Studio shows the job's real steps with their times (her screenshot: '3 looks bana raha
hoon 0%' and nothing else for minutes)."""
import time

from fastapi.testclient import TestClient

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_activity_steps_counts_and_new_run(tmp_path, monkeypatch):
    from app.site import activity as A
    from app.site import build as B
    monkeypatch.setattr(B, "site_dir", lambda t, s: tmp_path)
    A.step(T, "x", "3 looks soch raha hoon", "3 design")
    A.step(T, "x", "Tasveeren bana raha hoon", "", key="photos", done=1, total=4, alongside=True)
    a = A.read(T, "x")
    assert [s["label"] for s in a["steps"]] == ["Planning three designs", "Making photos for your business"]
    assert all(s["state"] == "run" for s in a["steps"])          # the photos run beside the designs
    A.step(T, "x", "Tasveeren bana raha hoon", "", key="photos", done=3, total=4, alongside=True)
    A.step(T, "x", "3 looks ban rahe hain", "", key="tops", done=0, total=6)
    A.step(T, "x", "3 looks ban rahe hain", "Look 1: Hero written", key="tops", done=1, total=6)
    a = A.read(T, "x")
    assert len(a["steps"]) == 3 and a["steps"][1]["done"] == 3
    assert [s["state"] for s in a["steps"]] == ["done", "done", "run"] and a["steps"][0]["end"] >= a["steps"][0]["at"]
    assert a["steps"][2]["done"] == 1 and a["steps"][2]["note"] == "Look 1: Hero written" and abs(a["now"] - time.time()) < 5
    A.end(T, "x", "Look chuniye", "3 looks taiyaar")
    a = A.read(T, "x")
    assert a["ended"] and all(s["state"] == "done" for s in a["steps"]) and a["steps"][-1]["final"]
    A.step(T, "x", "Design kit bana raha hoon")                 # the next job (the build) starts its own log
    a = A.read(T, "x")
    assert [s["label"] for s in a["steps"]] == ["Making the design kit"] and not a.get("ended")


def test_looks_and_build_leave_a_timed_log(site_env, monkeypatch):
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    v = S.new(T, "pet clinic Nagpur: vaccination, grooming, shop. Phone 98765 43210", "", name="PawCare")
    assert c.post(f"/api/sites/{v['id']}/plan", json={}).status_code == 200
    a = S.get(T, v["id"])["activity"]
    labels = [s["label"] for s in a["steps"]]
    assert labels[0] == "Planning three designs" and "Writing the top of every look" in labels
    assert "Putting the 3 looks together and taking screenshots" in labels and "Writing every page for the looks" in labels
    tops = next(s for s in a["steps"] if s["label"] == "Writing the top of every look")
    assert tops["total"] >= 3 and tops["done"] == tops["total"]
    assert a["ended"] and a["steps"][-1]["label"] == "Three looks ready: pick one"
    assert all(s["state"] == "done" and s["end"] >= s["at"] for s in a["steps"])
    assert c.post(f"/api/sites/{v['id']}/look", json={"index": 1}).status_code == 200
    b = S.get(T, v["id"])["activity"]
    assert b["started"] > a["started"] and b["steps"][-1]["label"] == "Website ready"


def test_studio_draws_steps_and_timers():
    from pathlib import Path
    js = (Path(__file__).parents[1] / "app/static/console/webstudio.js").read_text()
    for marker in ("actPanel(", "stepList(", "data-t0", "Working for", "steps so far", "drawActivity()", "tickClocks"):
        assert marker in js, marker
    assert "}, 2000);" in js     # polls every 2 s while working
