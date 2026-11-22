"""ONE ENGINE (owner: "GO ONE ENGINE"): the new engine's builder box is checked before every build and every 10
minutes, an image that is missing / old is rebuilt by itself (one rebuild at a time, the owner told), what code cannot
fix (Docker down, a full disk) is told plainly, and the default cannot switch to an engine that cannot build."""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "app"


@pytest.fixture()
def care(env, monkeypatch):
    monkeypatch.setenv("APP_ENGINE_BOX_CARE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.appengine import boxcare as B
    B.STATE.update({"checked_at": 0.0, "last": {}, "repairing": False, "repaired_at": 0.0, "failed_at": 0.0,
                    "fail_why": "", "repairs": 0, "told": {}})
    told: list[tuple[str, str]] = []
    from app.aiapps import ops as OPS
    monkeypatch.setattr(OPS, "_note", lambda tenant, text: told.append((tenant, text)))
    monkeypatch.setattr(B, "disk_free_gb", lambda path="": 40.0)
    yield B, told
    get_settings.cache_clear()


class FakeBox:
    """The box as `runner.available` sees it: docker answering or not, the image there or not."""
    def __init__(self, docker=True, image=False, build_ok=True, build_s=0.0):
        self.docker, self.image, self.build_ok, self.build_s, self.builds = docker, image, build_ok, build_s, 0

    def available(self):
        if not self.docker:
            return {"ok": False, "runner": "box", "fix": "docker", "why": "the docker daemon is not answering"}
        if not self.image:
            return {"ok": False, "runner": "box", "fix": "image", "why": "the App Engine image is not built yet: run setup"}
        return {"ok": True, "runner": "box", "image": "hoola-appengine:base", "rev": "2", "why": ""}

    def build(self, nocache=False, prebuilt=""):
        self.builds += 1
        time.sleep(self.build_s)
        if self.build_ok:
            self.image = True
            return {"ok": True, "seconds": self.build_s}
        return {"ok": False, "why": "the image did not build (read the log)"}


def _wire(monkeypatch, fb):
    from app.appengine import image as IMG
    from app.appengine import runner as R
    monkeypatch.setattr(R, "available", fb.available)
    monkeypatch.setattr(IMG, "build", fb.build)


def test_available_names_what_code_can_fix(env, monkeypatch):
    from app.appengine import image as IMG
    from app.appengine import runner as R
    from app.devlab import box
    monkeypatch.setattr(R, "mode", lambda: "box")
    monkeypatch.setattr(box, "docker", lambda: "/usr/bin/docker")
    monkeypatch.setattr(box, "_run", lambda argv, t: (0, "29.0", 0.1))
    monkeypatch.setattr(box, "has_image", lambda name: False)
    assert R.available()["fix"] == "image"
    monkeypatch.setattr(box, "has_image", lambda name: True)
    monkeypatch.setattr(IMG, "rev", lambda: "1")
    a = R.available()
    assert a["fix"] == "image" and "older" in a["why"]
    monkeypatch.setattr(box, "_run", lambda argv, t: (1, "", 0.1))
    assert R.available()["fix"] == "docker"
    monkeypatch.setattr(box, "docker", lambda: "")
    assert R.available()["fix"] == "docker"


def test_a_missing_image_is_rebuilt_once_and_she_is_told(care, monkeypatch):
    B, told = care
    fb = FakeBox(image=False)
    _wire(monkeypatch, fb)
    r = B.ensure("a build")
    assert r["ok"] and r.get("repaired") and fb.builds == 1
    assert told and "rebuilt it by itself" in told[-1][1]
    assert B.ensure("a build")["ok"] and fb.builds == 1          # ready now: no second rebuild
    assert B.status()["repairs"] == 1


def test_builds_at_once_wait_for_the_same_rebuild(care, monkeypatch):
    B, _ = care
    fb = FakeBox(image=False, build_s=0.3)
    _wire(monkeypatch, fb)
    out = []
    ts = [threading.Thread(target=lambda: out.append(B.ensure("a build"))) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert fb.builds == 1 and len(out) == 4 and all(o["ok"] for o in out)


def test_a_failed_rebuild_is_not_looped(care, monkeypatch):
    B, told = care
    fb = FakeBox(image=False, build_ok=False)
    _wire(monkeypatch, fb)
    r = B.ensure("a build")
    assert not r["ok"] and fb.builds == 1
    assert any("could not rebuild it" in t for _, t in told)
    r2 = B.ensure("a build")                                     # within 30 minutes: not tried again
    assert not r2["ok"] and fb.builds == 1 and "tried again later" in r2["why"]
    B.STATE["failed_at"] = time.time() - B.FAIL_WAIT_S - 1       # 30 minutes later: tried again
    fb.build_ok = True
    assert B.ensure("a build")["ok"] and fb.builds == 2


def test_docker_down_is_told_not_rebuilt(care, monkeypatch):
    B, told = care
    fb = FakeBox(docker=False)
    _wire(monkeypatch, fb)
    r = B.ensure("a build")
    assert not r["ok"] and not r["fixable"] and fb.builds == 0
    assert told and "cannot build right now" in told[-1][1] and "Back to the old engine" in told[-1][1]
    B.ensure("a build")
    assert len(told) == 1                                        # the same problem: told once in 6 hours


def test_runner_build_repairs_before_the_build(care, monkeypatch):
    B, _ = care
    from app.appengine import runner as R
    from app.devlab import box
    fb = FakeBox(image=False)
    _wire(monkeypatch, fb)
    monkeypatch.setattr(R, "mode", lambda: "box")
    monkeypatch.setattr(box, "docker", lambda: "/usr/bin/docker")
    ran = []
    monkeypatch.setattr(box, "_run", lambda argv, t: (ran.append(argv) or (1, "boom", 0.1)))
    res = R.build(Path("/tmp"), wait=1.0)                        # a real failed build, not "the image is not built"
    assert fb.builds == 1 and ran and res["ok"] is False and res["queued"] is False


def test_with_care_off_the_build_says_why(env, monkeypatch):
    from app.appengine import runner as R
    fb = FakeBox(image=False)
    _wire(monkeypatch, fb)
    monkeypatch.setattr(R, "mode", lambda: "box")
    with pytest.raises(RuntimeError, match="not built yet"):
        R.build(Path("/tmp"), wait=1.0)
    assert fb.builds == 0


def test_the_default_cannot_switch_to_a_box_that_cannot_build(care, monkeypatch):
    B, _ = care
    from app.site import enginedefault as ED
    fb = FakeBox(docker=False)
    _wire(monkeypatch, fb)
    monkeypatch.setattr(ED, "evidence", lambda run="": {"card": {"run": "r", "running": False}, "hash": "h1",
                                                         "recommendation": {}})
    with pytest.raises(ED.DefaultError, match="cannot build on this server"):
        ED.decide(True, "h1", "r")
    assert ED.state()["engine"] == "old"
    fb.docker = True                                            # docker back, image missing: rebuilt, then switched
    v = ED.decide(True, "h1", "r")
    assert v["engine"] == "new" and fb.builds == 1
    assert ED.decide(False)["engine"] == "old"                   # going back never needs the box


def test_the_ten_minute_look_only_while_the_new_engine_builds(care, monkeypatch):
    B, told = care
    fb = FakeBox(image=False)
    _wire(monkeypatch, fb)
    monkeypatch.setattr(B, "_tick_at", 0.0)
    monkeypatch.setattr(B, "in_use", lambda: False)
    assert B.tick() is None and fb.builds == 0
    monkeypatch.setattr(B, "in_use", lambda: True)
    assert B.tick()["ok"] and fb.builds == 1
    assert B.tick() is None                                      # not again within 10 minutes
    monkeypatch.setattr(B, "_tick_at", 0.0)
    monkeypatch.setattr(B, "disk_free_gb", lambda path="": 1.2)
    c = B.tick()
    assert c["ok"] and c["disk_low"] and any("nearly full" in t for _, t in told)


def test_owner_page_and_wiring(care, monkeypatch):
    B, _ = care
    from app.site import enginedefault as ED
    _wire(monkeypatch, FakeBox(image=True))
    v = ED.view_with_box()
    assert v["box"]["ok"] and v["box"]["care"] and v["box"]["disk_free_gb"] == 40.0
    js = (ROOT / "static/console/proofcard.js").read_text()
    assert "function boxHtml" in js and "boxHtml(eng.box)" in js and "Website builder" in js
    assert "ED.view_with_box()" in (ROOT / "main.py").read_text()
    w = (ROOT / "worker.py").read_text()
    assert "appengine_box_jobs," in w and "async def appengine_box_jobs" in w
    assert "APP_ENGINE_BOX_CARE" in (ROOT.parent / "tests/conftest.py").read_text()
