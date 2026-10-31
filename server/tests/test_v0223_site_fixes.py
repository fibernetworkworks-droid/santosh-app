"""v0.223 Website Sahayak phase 1 fixes: a queued change runs after the build (no site stuck in 'building'), a job that
died with the process is restarted once then failed plainly, at most SITE_WORKERS builds at once, a deleted site is taken
off the internet, her answers fill the blanks already written (launch unblocked), the uptime check / bots are not
visitors, a site's address never reaches Hoola's API, re-joining a domain removes the old Cloudflare hostnames, site
numbers never repeat after a delete."""
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import session
from tests.test_life import conv_ctx
from tests.test_v121_site import site_env  # noqa: F401  (fixture)
from tests.test_v122_hosting import HOOLA_TOKEN, _ready_site, host_env  # noqa: F401  (fixture)

T = "default"
HOST = "sharma-sweets.hoolasites.in"
REPO = Path(__file__).resolve().parents[2]


def _site_row(sid):
    from app.site.models import Site
    with session() as s:
        r = s.get(Site, sid)
        s.expunge(r)
        return r


def _wait(fn, secs=10.0):
    t = time.time()
    while time.time() - t < secs:
        if fn():
            return True
        time.sleep(0.05)
    return False


# ---------------------------------------------------------------- 1. jobs: queue, restart, slots
def test_queued_change_runs_after_the_build_in_thread_mode(site_env, monkeypatch):
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210"})
    monkeypatch.setenv("SITE_WORKER", "true")
    gate = threading.Event()
    runs = []

    def fake_build(site_id, only=None, note="", extra=None):
        runs.append(note)
        S._save(site_id, status="building", look={"tokens": {"bg": "#fff"}})
        if len(runs) == 1:
            gate.wait(5)                    # she asks for a change while this build runs
        S._save(site_id, status="ready", version=len(runs))
    monkeypatch.setattr(S, "run_build", fake_build)
    S._save(v["id"], status="ready", look={"tokens": {"bg": "#fff"}}, version=1)
    site_env.change = {"say": "Rang badal raha hoon", "sections": []}
    assert S._start(v["id"], "build", note="first") is True
    assert _wait(lambda: S.busy(v["id"]))
    assert S._start(v["id"], "build") is False             # a second job is refused while one runs
    out = S.change(T, v["id"], "rang halka karo")
    assert "queue" in out["say"].lower()
    gate.set()
    assert _wait(lambda: len(runs) == 2 and not S.busy(v["id"])), runs
    r = _site_row(v["id"])
    assert r.status == "ready" and r.queued == "[]"         # before v0.223: stuck 'building' forever, queue lost


def test_dead_job_restarts_once_then_fails_plainly(site_env, monkeypatch):
    from app.site import service as S
    from app.site.models import Site
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets")
    started = []
    monkeypatch.setattr(S, "_start", lambda sid, job, **kw: started.append((sid, job)) or True)
    old = datetime.now(timezone.utc) - timedelta(hours=2)

    def stuck(**kw):
        with session() as s:
            r = s.get(Site, v["id"])
            for k, val in {"status": "building", "look": '{"tokens": {"bg": "#fff"}}', **kw}.items():
                setattr(r, k, val)
            r.updated_at = old
    stuck()
    assert S.recover_stuck() == 1 and started == [(v["id"], "build")]
    assert _site_row(v["id"]).recovered == 1
    stuck()                                                  # died again: no endless restarts
    assert S.recover_stuck() == 1 and len(started) == 1
    r = _site_row(v["id"])
    assert r.status == "failed" and "Phir se chalao" in r.error
    S.resume(T, v["id"])                                     # her resume still works
    assert started[-1] == (v["id"], "build")
    stuck(stop=True, recovered=1)                            # she had pressed Rokiye: stopped, not failed
    S.recover_stuck()
    assert _site_row(v["id"]).status == "stopped"
    # generating looks (no looks yet) is a job; 3 looks waiting for her choice is not
    stuck(status="looks", look="{}", looks="[]", recovered=0, stop=False)
    S.recover_stuck()
    assert started[-1] == (v["id"], "looks")
    stuck(status="looks", looks='[{"style": "x"}]', recovered=0)
    n = len(started)
    assert S.recover_stuck() == 0 and len(started) == n
    # a fresh row of this process is a live job, never touched
    with session() as s:
        r = s.get(Site, v["id"])
        r.status, r.updated_at = "building", datetime.now(timezone.utc)
    assert S.recover_stuck() == 0


def test_only_site_workers_builds_at_once(site_env, monkeypatch):
    from app.site import service as S
    monkeypatch.setenv("SITE_WORKER", "true")
    monkeypatch.setenv("SITE_WORKERS", "1")
    monkeypatch.setattr(S, "_SLOTS", None)
    now_running, peak, lock = [0], [0], threading.Lock()

    def fake_build(site_id, only=None, note="", extra=None):
        with lock:
            now_running[0] += 1
            peak[0] = max(peak[0], now_running[0])
        time.sleep(0.2)
        with lock:
            now_running[0] -= 1
    monkeypatch.setattr(S, "run_build", fake_build)
    ids = [S.new(T, "mithai dukaan ki website", "", name=f"Shop {i}")["id"] for i in range(3)]
    for i in ids:
        assert S._start(i, "build")
    assert _wait(lambda: not any(S.busy(i) for i in ids))
    assert peak[0] == 1
    monkeypatch.setattr(S, "_SLOTS", None)


def test_numbers_never_repeat_after_delete(site_env):
    from app.site import service as S
    a = S.new(T, "mithai dukaan ki website", "", name="A")
    b = S.new(T, "mithai dukaan ki website", "", name="B")
    S.delete(T, a["id"])
    c = S.new(T, "mithai dukaan ki website", "", name="C")
    assert c["number"] != b["number"]


# ---------------------------------------------------------------- 2. her answers fill the written blanks
def test_answer_fills_blanks_and_unblocks_launch(host_env):
    from app.site import hosting as H
    from app.site import service as S
    host_env["ai"].blank = True
    g, _ = _ready_site("Glow Salon", "salon ki website")
    assert any("[blank]" in b for b in H.launch_request(T, g["id"])["blockers"])
    r = _site_row(g["id"])
    # one section also waits for her email
    key = next(k for k in S._sections(r) if not k.endswith("__hero"))
    sec = S._sections(r)[key]
    sec["html"] = sec["html"].replace("</p>", ' <em class="blank">[email]</em></p>', 1)
    S._sec_path(r, key).write_text(__import__("json").dumps(sec))
    host_env["ai"].blank = False                            # the rewrite now knows the year
    out = S.answer(T, g["id"], {"email": "glow@salon.in", "about": "Since 1995 in Akot"})
    assert "bhar" in out["say"]
    r = _site_row(g["id"])
    assert r.status == "ready" and r.version == 2
    html = "".join(x["html"] for x in S._sections(r).values())
    assert "glow@salon.in" in html and 'class="blank"' not in html
    card = H.launch_request(T, g["id"])
    assert not card["blockers"], card["blockers"]


def test_blank_labels_map_only_to_exact_facts():
    from app.site import service as S
    f = {"phone": "9876543210", "email": "a@b.in", "address": "Main Rd"}
    assert S._blank_fact("phone", f) == "9876543210" and S._blank_fact("WhatsApp", f) == "9876543210"
    assert S._blank_fact("Email", f) == "a@b.in" and S._blank_fact("address", f) == "Main Rd"
    assert S._blank_fact("registration number", f) == "" and S._blank_fact("year", f) == ""


# ---------------------------------------------------------------- 3. hosting
def _launch(c, g):
    card = c.post(f"/api/sites/{g['id']}/launch-request", json={}).json()
    assert c.post(f"/api/sites/{g['id']}/launch", json={"hash": card["hash"]}).status_code == 200


def test_delete_takes_the_site_off_the_internet(host_env):
    from app.main import app
    from app.site import hosting as H
    from app.site import service as S
    from app.site.hosting_models import SiteHost
    c = TestClient(app)
    g, _ = _ready_site()
    _launch(c, g)
    assert c.get("/", headers={"host": HOST}).status_code == 200
    out = S.delete(T, g["id"])
    assert "band" in out["say"]
    assert HOST not in H.host_map(force=True)
    assert not (H.hosted_root() / HOST).exists()
    with session() as s:
        assert {x.status for x in s.scalars(select(SiteHost)).all()} == {"removed"}


def test_uptime_check_and_bots_are_not_visitors(host_env):
    from app.main import app
    from app.site import care
    from app.site import hosting as H
    c = TestClient(app)
    g, _ = _ready_site()
    _launch(c, g)
    for ua in ("HoolaUptime/1.0", "Googlebot/2.1", "facebookexternalhit/1.1", "curl/8.1"):
        assert c.get("/", headers={"host": HOST, "user-agent": ua}).status_code == 200
    c.get("/", headers={"host": HOST, "user-agent": "Mozilla/5.0 (Linux; Android 14) Chrome/130"})
    care.flush()
    assert care.report(T, g["id"])["views"] == 1
    assert H.is_bot("HoolaUptime/1.0") and not H.is_bot("Mozilla/5.0 (iPhone) Safari")


def test_site_address_never_reaches_hoola_api(host_env):
    from app.main import app
    c = TestClient(app)
    g, _ = _ready_site()
    _launch(c, g)
    for m, path in (("post", "/api/console/login"), ("put", "/api/sites-keys/cloudflare"), ("delete", f"/api/sites/{g['id']}")):
        assert getattr(c, m)(path, headers={"host": HOST}).status_code == 404
    r = c.post(f"/api/site-forms/{g['id']}", headers={"host": HOST}, json={"name": "Ravi", "phone": "9822012345"})
    assert r.status_code == 200                              # her own enquiry form still posts
    assert c.get("/api/sites", headers={"host": "api.hoola.example"}).status_code != 404   # the API host is untouched


def test_rejoining_a_domain_drops_the_old_cloudflare_hostnames(host_env):
    from app.config import get_settings
    from app.site import hosting as H
    mp, cloud = host_env["monkeypatch"], host_env["cloud"]
    mp.setenv("SITES_CF_TOKEN", HOOLA_TOKEN)
    mp.setenv("SITES_CF_ZONE_ID", "zHOOLA")
    mp.setenv("SITES_ORIGIN", "origin.hoolasites.in")
    get_settings.cache_clear()
    g, _ = _ready_site()
    H.connect_domain(T, g["id"], "sharmasweets.in")
    first = {h["hostname"] for h in cloud.custom.values()}
    assert "www.sharmasweets.in" in first
    H.connect_domain(T, g["id"], "sharmasweets.in")          # same domain again: same hostnames kept, nothing lost
    assert {h["hostname"] for h in cloud.custom.values()} == first
    H.connect_domain(T, g["id"], "mithaighar.in")             # another domain: the old ones leave Cloudflare
    names = {h["hostname"] for h in cloud.custom.values()}
    assert "www.mithaighar.in" in names and not names & first, names


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.336.0"
    assert "0.336.0+376" in (REPO / "pubspec.yaml").read_text()
