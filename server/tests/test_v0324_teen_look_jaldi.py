"""v0.324 TEEN LOOK JALDI (owner: "3 DESIGN IS TAKING TOO MUCH TIME"): the 3 looks were made one after another and every
Opus call inside a look waited for the one before (about 12 slow calls in a row). Now the pictures + the 3 art
directions run together, then every look's sections together, then the 3 screenshots together. These tests drive the
real look maker with a slow fake Opus: the calls overlap, the 3 looks still come out (hero + page top each, in their
own style), and every call made in a worker thread is still charged to her (the usage context follows the thread -
before, parallel section writing lost it, so an Arena run's budget undercounted)."""
import threading
import time

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


class Slow:
    def __init__(self, base):
        self.base, self.lock, self.now, self.peak, self.tenants = base, threading.Lock(), 0, 0, []

    def __call__(self, system, prompt, max_tokens=6000, kind="build", **kw):
        from app import usage
        with self.lock:
            self.now += 1
            self.peak = max(self.peak, self.now)
            self.tenants.append(usage.current()[0])
        try:
            time.sleep(0.4)
            return self.base(system, prompt, max_tokens, kind)
        finally:
            with self.lock:
                self.now -= 1


def test_three_looks_are_written_together_and_charged_to_her(site_env, monkeypatch):
    monkeypatch.setenv("SITE_LOOK_SECTIONS", "3")                            # the live setting: hero + 2 sections a look
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import ai as AI
    from app.site import service as S
    slow = Slow(site_env)
    monkeypatch.setattr(AI, "ask_json", slow)
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    t0 = time.time()
    S.approve_plan(T, v["id"])
    took = time.time() - t0
    r = S._load(v["id"])
    assert r.status == "looks", r.error
    import json
    looks = json.loads(r.looks)
    assert len(looks) == 3 and len({lk["style"] for lk in looks}) == 3
    assert all(lk["shots"] for lk in looks)                                   # every look has its screenshots
    n_calls = len(slow.tenants)
    assert n_calls >= 6 and slow.peak >= 3                                    # calls overlapped (were 1 at a time)
    assert took < n_calls * 0.4 + 60                                          # not the sum of every call
    assert set(slow.tenants) == {T}                                           # every thread's call charged to her
    hero_files = [p for p in (S.B.site_dir(T, r.id) / "looks").glob("*/hero.json")]
    assert len(hero_files) == 3


def test_in_ctx_carries_the_usage_scope_into_a_thread():
    from concurrent.futures import ThreadPoolExecutor
    from app import usage
    from app.site import service as S
    with usage.scope("t-arena", "site"):
        with ThreadPoolExecutor(2) as ex:
            plain = ex.submit(lambda: usage.current()[0]).result()
            kept = ex.submit(S._in_ctx(lambda: usage.current()[0])).result()
    assert kept == "t-arena" and plain != "t-arena"


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.334.0"
    assert "0.334.0+374" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
