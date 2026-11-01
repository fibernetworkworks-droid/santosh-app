"""v0.365 SOCIAL MEDIA MANAGER Phase 4 - 24/7 + reports: plan posts go on their own only by trust (Saathi / Bharosa, daily
cap, quiet hours; Seekh = her OK on the day), pause + emergency stop (also stops automatic replies), morning note only when
something needs her, weekly two-line pulse, monthly PDF against the baseline, best-time engine fed to the planner, boost-worthy
flags with a plan she runs herself. Meta is a mock transport."""
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from tests import test_v0353_social_manager as P1
from tests import test_v0355_social_publish as P2
from tests.test_v0353_social_manager import social  # noqa: F401  (the shared fixture)

T = "default"
IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture
def pub(social, monkeypatch, tmp_path):
    from app.social import meta as M
    from app.social import publish as SP
    from app.social import pulse as PU
    monkeypatch.setenv("SOCIAL_DIR", str(tmp_path / "social"))
    M.set_http(httpx.Client(transport=httpx.MockTransport(P2.handler)))
    monkeypatch.setattr(M, "_sleep", lambda s: None)
    P2.LOG.clear()
    P2.IGS.clear()
    D = social
    P1._hire_and_setup(D)
    D.finish_link("instagram", "IGCODE", P1._state_from(D.connect_url(T, "instagram")), background=False)
    return D, SP, PU


def _trust(level):
    from app.employee import hire
    hire.save_settings(T, "social", trust=level)


def _plan_posts(D, SP, slots):
    """Posts approved only as part of the plan (approve_calendar), each with a picture."""
    with D.session() as s:
        for old in s.scalars(D.select(D.SocialPost).where(D.SocialPost.tenant_id == T)).all():
            s.delete(old)
    ids = [P2._post(D, platforms="instagram", slot=x) for x in slots]
    a = SP.add_asset(T, P2._jpeg())
    for pid in ids:
        SP.attach(T, pid, [a["id"]])
    D.approve_calendar(T)
    return ids


def _status(D, pid):
    return next(p for p in D.calendar(T) if p["id"] == pid)


def test_seekh_plan_post_waits_for_her_ok_then_goes(pub):
    D, SP, PU = pub
    [pid] = _plan_posts(D, SP, ["2026-11-08T12:00"])
    assert _status(D, pid)["plan_only"]
    at = datetime(2026, 11, 8, 12, 5, tzinfo=IST)
    assert SP.run_publisher(T, at) == {"sent": 0, "failed": 0}          # Seekh: the plan OK is not enough
    assert [w["id"] for w in PU.waiting_ok(T, "2026-11-08")] == [pid]
    D.set_post(T, pid, status="approved")                              # her one-tap OK on the day
    assert not _status(D, pid)["plan_only"]
    assert SP.run_publisher(T, at)["sent"] == 1


def test_saathi_plan_posts_go_alone_within_cap_and_outside_quiet_hours(pub, monkeypatch):
    D, SP, PU = pub
    _trust("saathi")
    monkeypatch.setitem(PU.POST_CAP, "saathi", 2)
    ids = _plan_posts(D, SP, ["2026-11-08T23:30", "2026-11-09T08:00", "2026-11-09T08:30", "2026-11-09T09:00"])
    told = []
    monkeypatch.setattr(PU, "_say", lambda t, kind, text, conv="": told.append((kind, text)))
    r = SP.run_publisher(T, datetime(2026, 11, 8, 23, 45, tzinfo=IST))
    assert r == {"sent": 0, "failed": 0}                               # 23:45 = quiet hours
    monkeypatch.setattr(SP, "now", lambda: datetime(2026, 11, 9, 9, 5, tzinfo=IST))   # the send time on the test's day
    r = SP.run_publisher(T, datetime(2026, 11, 9, 9, 5, tzinfo=IST))
    assert r["sent"] == 2                                              # cap 2 a day, oldest first
    st = [_status(D, i)["status"] for i in ids]
    assert st[:2] == ["published", "published"] and st[2:] == ["approved", "approved"]
    assert any(k == "social_day" and "approved plan" in t for k, t in told)    # Saathi: told the same day
    PU.set_settings(T, quiet=[0, 0])
    assert SP.run_publisher(T, datetime(2026, 11, 9, 9, 30, tzinfo=IST))["sent"] == 0     # still capped today


def test_her_own_ok_is_never_held_by_trust_or_quiet(pub):
    D, SP, PU = pub
    pid = P2._post(D, platforms="instagram", slot="2026-11-08T23:30")
    SP.attach(T, pid, [SP.add_asset(T, P2._jpeg())["id"]])
    D.set_post(T, pid, status="approved")
    assert SP.run_publisher(T, datetime(2026, 11, 8, 23, 40, tzinfo=IST))["sent"] == 1


def test_pause_and_emergency_stop(pub):
    D, SP, PU = pub
    _trust("bharosa")
    ids = _plan_posts(D, SP, ["2026-11-08T12:00", "2026-11-10T12:00"])
    PU.set_settings(T, paused=True)
    assert SP.run_publisher(T, datetime(2026, 11, 8, 12, 5, tzinfo=IST))["sent"] == 0
    PU.set_settings(T, paused=False)
    assert SP.run_publisher(T, datetime(2026, 11, 8, 12, 6, tzinfo=IST))["sent"] == 1
    r = PU.set_settings(T, stop=True)
    assert r["paused"] and r["back_to_draft"] == 1 and _status(D, ids[1])["status"] == "draft"
    assert _status(D, ids[0])["status"] == "published"                 # what already went out stays
    with pytest.raises(D.SocialError):
        PU.set_settings(T, quiet=[25, 7])
    ev = [e["text"] for e in D.desk_view(T)["events"]]
    assert any("Emergency stop" in t for t in ev) and any("Resumed" in t for t in ev)


def test_pause_also_stops_automatic_replies(pub):
    D, SP, PU = pub
    from tests import test_v0364_social_inbox as P3
    from app.social import inbox as IB
    from app.social import meta as M
    M.set_http(httpx.Client(transport=httpx.MockTransport(P3.handler)))
    P3.SENT.clear()
    D.finish_link("instagram", "IGCODE", P1._state_from(D.connect_url(T, "instagram")), background=False)
    _trust("saathi")
    PU.set_settings(T, paused=True)
    IB.run_inbox(T)
    assert P3.SENT == [] and IB.counts(T)["needs"] >= 5


def test_best_times_and_planner_use_them(pub):
    D, SP, PU = pub
    bt = PU.best_times(T)
    assert bt["posts"] == 8 and bt["slots"] and bt["sure"] == "low"
    assert all(set(x) >= {"day", "band", "lift", "posts"} for x in bt["slots"])
    assert bt["slots"][0]["lift"] >= bt["slots"][-1]["lift"]
    inp = D._plan_inputs(T)
    assert "best_times" in inp and inp["best_times"]["sure"] == "low"
    inp["best_times"] = {"by_day": {d: 18 for d in PU.DAYS}, "sure": "high"}
    plan = D._rules_plan(inp)
    assert {p["time"] for p in plan["posts"]} == {"18:00"}


def test_boost_flags_told_once(pub):
    D, SP, PU = pub
    with D.session() as s:
        m = s.scalars(D.select(D.SocialMedia).where(D.SocialMedia.media_id == "m1")).first()
        m.likes, m.posted_at = 900, D.now() - timedelta(days=2)
    flags = PU.boost_flags(T)
    assert flags and flags[0]["id"] == "m1" and flags[0]["times"] >= 2 and "Hoola" not in flags[0]["plan"]
    assert "Akola" in flags[0]["plan"] and "Rs 300 a day" in flags[0]["plan"]
    assert PU.flag_boosts(T) == 1 and PU.flag_boosts(T) == 0
    assert any(e["text"].startswith("Boost-worthy") for e in D.desk_view(T)["events"])


def test_morning_note_only_when_needed_and_weekly_pulse(pub, monkeypatch):
    D, SP, PU = pub
    told = []
    monkeypatch.setattr(PU, "_say", lambda t, kind, text, conv="": told.append((kind, text)))
    monkeypatch.setattr(D, "_occasions", lambda t, start, days=30: {})
    assert PU.morning(T) == {"sent": False}                            # nothing needs her -> silence
    today = D._local(T).strftime("%Y-%m-%dT09:00")
    _plan_posts(D, SP, [today])
    r = PU.morning(T)
    assert r["sent"] and "wait for your OK" in r["text"] and told[-1][0] == "social_day"
    w = PU.weekly_pulse(T)
    assert w["text"].count("\n") == 1 and "interactions" in w["text"] and told[-1][0] == "social_week"


def test_monthly_pdf_against_baseline(pub):
    D, SP, PU = pub
    title, md = PU.report_markdown(T)
    assert "social media report" in title and "> [!KEY]" in md and "| Measure | Baseline | Now | Change |" in md
    assert "# Best posts this month" in md and "# Next month" in md and "Not working if" in md
    made = []

    def fake(t, text, kw, author, who):
        made.append((t, author))
        return {"data": b"%PDF-1.7 test", "pages": 3}
    r = PU.monthly_report(T, make=fake)
    assert r["pages"] == 3 and made[0][1] == "Hoola Social Media Manager"
    assert any(e["kind"] == "report" for e in D.desk_view(T)["events"])


def test_scheduler_morning_and_monthly(pub):
    D, SP, PU = pub
    d1 = datetime(2026, 12, 1, 9, 30, tzinfo=IST)
    jobs = D.due_jobs(T, d1)
    assert "morning" in jobs and "monthly" in jobs
    assert "morning" not in D.due_jobs(T, datetime(2026, 12, 1, 8, 0, tzinfo=IST))
    with D.session() as s:
        d = s.get(D.SocialDesk, T)
        st = json.loads(d.stamps)
        st["baseline_month"] = "2026-12"
        d.stamps = json.dumps(st)
    assert "monthly" not in D.due_jobs(T, d1)                          # not in the month the baseline was taken
    assert any(x["job"] == "Monthly PDF report" for x in D.desk_view(T)["schedule"])


def test_api_settings_and_desk_view(pub):
    D, SP, PU = pub
    from app import main
    with TestClient(main.app) as c:
        assert c.post("/api/social/settings", json={"paused": True}).json()["paused"] is True
        v = c.get("/api/social/desk").json()
        assert v["pulse"]["settings"]["paused"] and "best_times" in v["pulse"] and "boosts" in v["pulse"]
        assert c.post("/api/social/settings", json={"quiet": [22, 6]}).json()["quiet"] == [22, 6]
        assert c.post("/api/social/settings", json={"quiet": [30, 6]}).status_code == 400
        assert c.post("/api/social/settings", json={"stop": True}).json()["paused"] is True
        assert c.post("/api/social/run/morning").status_code == 200
        assert c.post("/api/social/run/nope").status_code == 404


def test_console_phone_privacy_wired():
    root = P1.ROOT
    js = (root / "server/app/static/console/employees.js").read_text()
    assert "/api/social/settings" in js and "data-scok" in js and "Emergency stop" in js and "Best times for you" in js and "data-scrun=\"monthly\"" in js
    dart = (root / "lib/ui/employees_screen.dart").read_text()
    assert "socialSettings(" in dart and "OK to post" in dart and "Emergency stop" in dart and "Worth a boost" in dart
    assert "/api/social/settings" in (root / "lib/api.dart").read_text()
    assert "case 'social_week':" in (root / "lib/ui/chat_screen.dart").read_text()
    from app import push
    assert {"social_day", "social_week"} <= push.PUSH_KINDS
    pv = (root / "server/app/static/privacy.html").read_text()
    assert "pause all posting" in pv
