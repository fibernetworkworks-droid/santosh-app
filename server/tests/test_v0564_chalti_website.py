"""v0.564 CHALTI WEBSITE (web Step 7 part 2 = W14): her visitors' JavaScript errors + real-visit speed (bands, p75), AI cost
per site, alerts in her chat (error spike / slow, against her OWN history, once a day), and the nightly backup RESTORE TEST
(downloaded back, unpacked, compared byte for byte with the live files)."""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v121_site import T, _events, site_env  # noqa: F401  (fixture)

IST = timezone(timedelta(hours=5, minutes=30))


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.703.0"


def _site(S):
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    return v["id"]


def _fresh(OPS):
    OPS._BUF.clear()
    OPS._IP.clear()
    OPS._SITES.update({"at": 0.0, "map": {}})


def test_a_beacon_keeps_only_the_error_never_the_visitor(site_env):
    from app.site import ops as OPS
    from app.site import service as S
    sid = _site(S)
    _fresh(OPS)
    body = {"p": "/products/?q=ramesh@gmail.com#x", "e": [
        {"m": "TypeError: x is undefined for ramesh@gmail.com order 9876543210123", "f": "https://site.in/assets/site.js?v=2", "l": 41},
        {"m": "Uncaught Error at https://site.in/pay?token=abc123", "f": "", "l": 0}] + [{"m": f"e{i}", "f": "a.js", "l": i} for i in range(9)]}
    assert OPS.record(sid, json.dumps(body), "1.2.3.4")
    OPS.flush()
    s = OPS.summary(sid, 7)
    assert s["errors"] == 5                                         # at most 5 a page view
    keys = [k for k, _ in s["top_errors"]]
    first = next(k for k in keys if k.startswith("TypeError"))
    assert "ramesh" not in first and "[email]" in first and "[n]" in first and first.endswith("| site.js:41")
    assert any(k.startswith("Uncaught Error at https://site.in/pay") and "token" not in k for k in keys)
    assert s["error_pages"][0][0] == "/products/"                   # no query string, no fragment kept
    # an unknown site, a broken body, an oversized body: nothing counted, nothing raised
    assert not OPS.record("site_nope", json.dumps(body), "1.2.3.4")
    assert not OPS.record(sid, "{not json", "1.2.3.4")
    assert not OPS.record(sid, "x" * (OPS.MAX_BODY + 1), "1.2.3.4")
    # a flood from one address is cut at the cap
    _fresh(OPS)
    ok = sum(OPS.record(sid, json.dumps({"p": "/", "e": [{"m": "boom"}]}), "9.9.9.9") for _ in range(OPS.IP_CAP + 20))
    assert ok == OPS.IP_CAP


def test_speed_is_kept_as_bands_and_read_back_as_p75(site_env):
    from app.site import ops as OPS
    from app.site import service as S
    sid = _site(S)
    _fresh(OPS)
    for i in range(100):                                            # 80 fast visits, 20 slow ones
        lcp = 1500 if i < 80 else 7000
        assert OPS.record(sid, json.dumps({"p": "/", "s": {"ttfb": 150, "fcp": 900, "lcp": lcp, "cls": 0.02}}), f"10.0.0.{i}")
    OPS.flush()
    sp = OPS.summary(sid, 7)["speed"]
    assert sp["samples"] == 100 and sp["inp"] == "not measured"
    assert sp["lcp"]["p75"] == "at most 1.8 s" and sp["lcp"]["grade"] == "good"
    assert sp["ttfb"]["p75"] == "at most 200 ms" and sp["cls"]["p75"] == "at most 0.025"
    assert OPS.p75([0, 0, 0]) is None and OPS.band("lcp", 99999) == len(OPS.MS_EDGES)
    assert OPS.band_label("lcp", len(OPS.MS_EDGES)) == "over 10 s"
    # a browser that cannot measure LCP / CLS sends nothing for them: never a fake 0
    _fresh(OPS)
    OPS.record(sid, json.dumps({"p": "/", "s": {"ttfb": 300}}), "11.0.0.1")
    OPS.flush()
    with __import__("app.db", fromlist=["session"]).session() as s:
        rows = s.scalars(__import__("sqlalchemy").select(OPS.SiteOpsDay).where(OPS.SiteOpsDay.site_id == sid)).all()
        assert len(rows) == 1                                       # one row a site a day (unique index + retry)
        assert sum(json.loads(rows[0].speed)["cls"]) == 100 and sum(json.loads(rows[0].speed)["ttfb"]) == 101


def test_routes_beacon_204_and_her_ops_view(site_env):
    from app.main import app
    from app.site import ops as OPS
    from app.site import service as S
    sid = _site(S)
    _fresh(OPS)
    c = TestClient(app)
    r = c.post(f"/api/site-ops/{sid}/beacon", content=json.dumps({"p": "/", "e": [{"m": "ReferenceError: foo"}],
                                                                   "s": {"lcp": 2100, "ttfb": 120}}),
               headers={"Content-Type": "text/plain;charset=UTF-8"})
    assert r.status_code == 204 and r.content == b""
    assert c.post("/api/site-ops/nope/beacon", content=b"garbage").status_code == 204     # never an error at a visitor
    d = c.get(f"/api/sites/{sid}/ops?days=7").json()
    assert d["errors"] == 1 and d["top_errors"][0][0] == "ReferenceError: foo"
    assert d["speed"]["lcp"]["p75"] == "at most 2.5 s" and d["speed"]["lcp"]["grade"] == "good"
    assert "ai_inr" in d["cost"] and "not split per site" in d["cost"]["note"]
    assert d["backup"]["enabled"] is False and d["backup"]["restore_test"] is None
    assert "1 galtiyan" in d["say"] and "2.5 s" in d["say"]
    # Hoola reads the same thing in chat
    import asyncio
    from app.agent.site_tools import SITE_HANDLERS
    from tests.test_life import conv_ctx
    got = asyncio.run(SITE_HANDLERS["website_dekho"](conv_ctx(), "ops", site=sid, days=7))
    assert got["errors"] == 1 and got["speed"]["lcp"]["grade"] == "good"


def test_built_pages_carry_the_beacon_address_but_edit_builds_do_not(site_env):
    from app.site import build as B
    from app.site import gates as G
    from app.site import service as S
    sid = _site(S)
    r = S._load(sid)
    out = S._assemble_live(r)
    home = (out / "index.html").read_text()
    assert f'<meta name="hoola-ops" content="' in home and f"/api/site-ops/{sid}/beacon" in home
    js = (out / "assets" / "hoola-site.js").read_text()
    for must in ("sendBeacon", "supportedEntryTypes", "largest-contentful-paint", "layout-shift", "unhandledrejection",
                 "meta[name=\"hoola-ops\"]", ">= 5", "AbortError"):
        assert must in js, must
    assert "document.cookie" not in js.split("CHALTI WEBSITE")[1] and "localStorage" not in js.split("CHALTI WEBSITE")[1]
    # the beacon rides the address her forms already post to, so the site's CSP + the safety gates still pass
    csp = (out / "_headers").read_text()
    assert "connect-src 'self'" in csp
    res = G.scan(out, S._ctx(r), {"source": "hoola", "blocking": []}, S.form_endpoint(r))
    assert not [x for x in res["rows"] if x["state"] == "fail"]
    # Edit mode never reports
    site = {"edit": True, "ops_api": "/api/site-ops/x/beacon"}
    meta = []
    if site.get("ops_api") and not site.get("edit"):
        meta.append("x")
    assert not meta and "not site.get(\"edit\")" in Path(B.__file__).read_text()


def _day_row(OPS, sid, tenant, day, errors=0, samples=0, lcp_ms=None):
    from app.db import session
    OPS.ensure_tables()
    sp = {m: [0] * (len(e) + 1) for m, e in OPS.METRICS.items()}
    if lcp_ms is not None:
        sp["lcp"][OPS.band("lcp", lcp_ms)] = samples
    with session() as s:
        s.add(OPS.SiteOpsDay(site_id=sid, tenant_id=tenant, day=day, errors=errors, samples=samples, speed=json.dumps(sp),
                             err_top=json.dumps({"TypeError: x | site.js:4": errors})))


def test_alerts_compare_with_her_own_week_and_speak_once_a_day(site_env):
    from app.site import ops as OPS
    from app.site import service as S
    sid = _site(S)
    _fresh(OPS)
    now = datetime(2026, 11, 20, 12, 0, tzinfo=IST)
    day = now.strftime("%Y-%m-%d")
    for i in range(1, 8):                                            # her usual week: ~20 errors a day, LCP ~2 s
        _day_row(OPS, sid, T, (now - timedelta(days=i)).strftime("%Y-%m-%d"), errors=20, samples=60, lcp_ms=2000)
    _day_row(OPS, sid, T, day, errors=45, samples=60, lcp_ms=2400)  # 45 >= 25 but < 3 x 20: not a spike for HER
    assert OPS.check_alerts(now) == []
    from app.db import session
    with session() as s:
        row = s.scalars(__import__("sqlalchemy").select(OPS.SiteOpsDay).where(OPS.SiteOpsDay.day == day)).first()
        row.errors, sp = 80, json.loads(row.speed)
        sp["lcp"] = [0] * (len(OPS.MS_EDGES) + 1)
        sp["lcp"][OPS.band("lcp", 7000)] = 60
        row.speed = json.dumps(sp)
    said = OPS.check_alerts(now)
    assert {x["kind"] for x in said} == {"errors", "slow"}
    assert OPS.check_alerts(now) == []                               # once a day each
    ev = [e for e in _events("site_ops") if e.get("site") == sid]
    assert len(ev) == 2 and all(e["push"] for e in ev)
    err = next(e for e in ev if e["kind"] == "errors")
    assert "80 JavaScript galtiyan" in err["say"] and "aam din ~20" in err["say"] and "TypeError" in err["say"]
    slow = next(e for e in ev if e["kind"] == "slow")
    assert "at most 10 s" in slow["say"] and "pichhle hafte at most 2.5 s" in slow["say"]
    from app.push import render
    title, _body = render("site_ops", err, "Sharma Sweets")
    assert "galtiyan" in title


def test_a_new_site_with_no_history_still_hears_about_a_real_spike(site_env):
    from app.site import ops as OPS
    from app.site import service as S
    sid = _site(S)
    _fresh(OPS)
    now = datetime(2026, 11, 21, 12, 0, tzinfo=IST)
    _day_row(OPS, sid, T, now.strftime("%Y-%m-%d"), errors=24, samples=10, lcp_ms=9000)
    assert OPS.check_alerts(now) == []                               # under 25 errors, under 30 measured visits: quiet
    _fresh(OPS)
    OPS._BUF[(sid, T, now.strftime("%Y-%m-%d"))] = {"errors": 1, "top": {}, "pages": {}, "samples": 25, "dropped": 0,
                                                     "speed": {m: ([0] * OPS.band("lcp", 9000) + [25] + [0] * (len(OPS.MS_EDGES) - OPS.band("lcp", 9000)))
                                                               if m == "lcp" else [0] * (len(e) + 1) for m, e in OPS.METRICS.items()}}
    assert {x["kind"] for x in OPS.check_alerts(now)} == {"errors", "slow"}


def _tree(root: Path, files: dict[str, str], when: float):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        os.utime(p, (when, when))


def test_the_restore_comparison_is_byte_for_byte_and_honest_about_time(tmp_path):
    from app.site import ops as OPS
    taken = time.time() - 3600
    old = taken - 60
    live = tmp_path / "live"
    _tree(live, {"a.in/index.html": "<h1>A</h1>", "a.in/assets/site.css": "body{}", "b.in/index.html": "<h1>B</h1>",
                 "b.in/about/index.html": "about"}, old)
    back = tmp_path / "back" / "hosted"
    _tree(back, {"a.in/index.html": "<h1>A</h1>", "a.in/assets/site.css": "body{}", "b.in/index.html": "<h1>B</h1>",
                 "b.in/about/index.html": "about"}, old)
    res = OPS.compare(tmp_path / "back", live, taken)
    assert res["ok"] and res["sites"] == 2 and res["files_checked"] == 4
    # a file edited AFTER the backup is not the backup's fault; a file that came back different IS
    _tree(live, {"a.in/assets/site.css": "body{color:red}"}, time.time())
    assert OPS.compare(tmp_path / "back", live, taken)["ok"]
    _tree(back, {"b.in/about/index.html": "abuot"}, old)
    res = OPS.compare(tmp_path / "back", live, taken)
    assert not res["ok"] and res["bad"] == ["b.in"] and res["detail"]["b.in"]["changed"] == ["about/index.html"]
    # a whole site missing from the archive, or its front page missing
    (back / "b.in" / "about" / "index.html").write_text("about")
    os.utime(back / "b.in" / "about" / "index.html", (old, old))
    (back / "a.in" / "index.html").unlink()
    res = OPS.compare(tmp_path / "back", live, taken)
    assert res["bad"] == ["a.in"] and res["detail"]["a.in"]["missing"] == ["index.html"]
    # a site published after the backup is not counted against it
    _tree(live, {"c.in/index.html": "new"}, time.time())
    (live / "c.in").touch()
    assert "c.in" not in OPS.compare(tmp_path / "back", live, taken)["bad"]


def test_a_failed_restore_test_tells_that_sites_owner_once(site_env, monkeypatch, tmp_path):
    from app.db import session
    from app.site import backup as BK
    from app.site import ops as OPS
    from app.site import service as S
    from app.site.hosting_models import SiteHost
    sid = _site(S)
    with session() as s:
        s.add(SiteHost(tenant_id=T, site_id=sid, hostname="sharma.example.in", status="active", role="main"))
    hosted = tmp_path / "hosted"
    _tree(hosted, {"sharma.example.in/index.html": "<h1>Sharma</h1>"}, time.time() - 7200)
    monkeypatch.setattr(BK, "enabled", lambda: True)
    monkeypatch.setattr(BK, "status", lambda: {"enabled": True, "last": {"ok": True, "day": "2026-11-20", "at": time.time() - 3600}})
    monkeypatch.setattr(BK, "_roots", lambda: (hosted, tmp_path / "sites"))
    monkeypatch.setattr(OPS, "_state", lambda: tmp_path / "rt.json")

    def bad_restore(day, into):                                      # the archive came back without her front page
        (into / "hosted" / "sharma.example.in").mkdir(parents=True)
        return {"restored": 1}
    monkeypatch.setattr(BK, "restore", bad_restore)
    res = OPS.restore_test()
    assert res["ok"] is False and res["bad"] == ["sharma.example.in"] and res["day"] == "2026-11-20"
    assert OPS.restore_status()["ok"] is False
    ev = [e for e in _events("site_ops") if e.get("kind") == "backup"]
    assert len(ev) == 1 and ev[0]["site"] == sid and "backup" in ev[0]["say"]
    OPS.restore_test()                                               # said once that day
    assert len([e for e in _events("site_ops") if e.get("kind") == "backup"]) == 1
    assert OPS.owner_view(T, sid, 7)["backup"]["restore_test"]["ok"] is False

    def good_restore(day, into):
        _tree(into / "hosted", {"sharma.example.in/index.html": "<h1>Sharma</h1>"}, time.time() - 7200)
        return {"restored": 1}
    monkeypatch.setattr(BK, "restore", good_restore)
    res = OPS.restore_test()
    assert res["ok"] and res["files_checked"] == 1 and OPS.owner_view(T, sid, 7)["backup"]["restore_test"]["ok"]

    def gone(day, into):
        raise BK.BackupError("404 from the bucket")
    monkeypatch.setattr(BK, "restore", gone)
    assert OPS.restore_test()["ok"] is False and OPS.restore_status()["bad"] == ["(download)"]


def test_the_nightly_test_waits_for_that_nights_backup(monkeypatch, tmp_path):
    from app.site import backup as BK
    from app.site import ops as OPS
    ran = []
    monkeypatch.setattr(BK, "enabled", lambda: True)
    monkeypatch.setattr(OPS, "_state", lambda: tmp_path / "rt.json")
    monkeypatch.setattr(OPS, "restore_test", lambda day="": ran.append(day) or {"ok": True, "day": day})
    t = datetime(2026, 11, 20, 3, 30, tzinfo=IST)
    monkeypatch.setattr(BK, "status", lambda: {"last": {"ok": True, "day": "2026-11-20"}})
    assert OPS.daily_restore_test(t) is None                        # before 04:00
    monkeypatch.setattr(BK, "status", lambda: {"last": {"ok": True, "day": "2026-11-19"}})
    assert OPS.daily_restore_test(t.replace(hour=5)) is None         # tonight's backup not done yet
    monkeypatch.setattr(BK, "status", lambda: {"last": {"ok": True, "day": "2026-11-20"}})
    assert OPS.daily_restore_test(t.replace(hour=5))["ok"] and ran == ["2026-11-20"]
    (tmp_path / "rt.json").write_text(json.dumps({"day": "2026-11-20", "ok": True}))
    assert OPS.daily_restore_test(t.replace(hour=6)) is None         # once a night
    src = Path(BK.__file__).read_text()
    assert '"at": taken' in src                                      # the backup records when it was taken


def test_wiring():
    root = Path(__file__).resolve().parents[1] / "app"
    assert "site_ops.tick" in (root / "worker.py").read_text()
    assert "from .site import ops as _site_ops" in (root / "db.py").read_text()
    assert '"/api/site-ops/{site_id}/beacon"' in (root / "main.py").read_text()
    assert '"/api/sites/{ref}/ops"' in (root / "main.py").read_text()
    assert '"site_ops"' in (root / "push.py").read_text()
    b = (root / "static" / "console" / "build.js").read_text()
    assert "loadOps(o, box" in b and "Running health" in b and "INP" in b
    assert '"ops"' in (root / "agent" / "site_tools.py").read_text()
