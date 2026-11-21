"""v0.990 B3 PROVE THE RULES (owner: "GO B3" on docs/research/lovable/03_backend_vs_hoola.md, gap 4).

A website's data rules are PLAYED through the real engine (App Sahayak's create / rows / update / delete) on a throwaway
copy by a visitor, two members and an admin; a failing rule blocks going live; the tests run again after a list / rule
change and before going live when the rules changed; her rows and members are never touched."""
from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import T, app_site  # noqa: F401  (fixture)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.69"


def _linked(sid):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    S.design_app(T, sid, "customers apna order track karein")
    c.post(f"/api/sites/{sid}/link-app")
    return c, S._load(sid)


def _count(model, **kw):
    from app.db import session
    with session() as s:
        return s.query(model).filter_by(**kw).count()


def test_rules_pass_on_the_real_engine_and_nothing_of_hers_moves(app_site):
    from app.appmaker.models import AppProject
    from app.site import applink as AL
    from app.site import rulecheck as RC
    from app.site import webapp as W
    c, r = _linked(app_site)
    main = AL.project(r)
    rows0, mem0 = _count(W.SiteAppRow, site_id="app:" + main.id), _count(W.SiteAppMember, site_id="app:" + main.id)
    out = RC.run(r)
    assert out["ran"] and out["ok"], out["failed"]
    assert out["lists"] == 2 and out["count"] >= 20
    names = {(x["list"], x["check"]) for x in out["checks"]}
    assert ("orders", "see as another member") in names                                # own: hidden from another member
    assert ("orders", "staff-only field 'status' set by a member") in names            # admin_only choice never set by a member
    assert ("notices", "add as its owner (a member)") in names                          # admin-only add refused to a member
    assert next(x for x in out["checks"] if x["check"] == "see as another member" and x["list"] == "orders")["got"] == "0"
    assert out["say"].startswith("Rule tests passed")
    # her data untouched; the throwaway copy is gone
    assert _count(W.SiteAppRow, site_id="app:" + main.id) == rows0
    assert _count(W.SiteAppMember, site_id="app:" + main.id) == mem0
    assert _count(AppProject, status="twin") == 0
    # kept and reused while the rules are the same
    assert RC.last(r)["at"] == out["at"] and RC.current(r)["at"] == out["at"]
    got = c.get(f"/api/sites/{app_site}/rule-tests").json()
    assert got["ok"] and got["at"] == out["at"]
    assert c.post(f"/api/sites/{app_site}/rule-tests").json()["at"] != ""


def test_a_broken_rule_is_caught_and_blocks_going_live(app_site, monkeypatch):
    from app.site import hosting as H
    from app.site import rulecheck as RC
    from app.site import webapp as W
    _c, r = _linked(app_site)
    real = W._can_read
    # the engine leaks: an "own" list shows one member's entries to another
    monkeypatch.setattr(W, "_can_read", lambda c, who, row: True if c["rules"]["read"] == "own" and who.m else real(c, who, row))
    orig_rows = W.rows

    def leaky(site_id, schema, key, who, limit=200):
        c = W.coll(schema, key)
        if c["rules"]["read"] != "own" or who.m is None:
            return orig_rows(site_id, schema, key, who, limit)
        with W.session() as s:
            got = s.query(W.SiteAppRow).filter_by(site_id=site_id, coll=key).all()
            for x in got:
                s.expunge(x)
        return [W.row_view(c, x, who) for x in got]
    monkeypatch.setattr(W, "rows", leaky)
    out = RC.run(r)
    assert not out["ok"]
    bad = out["failed"][0]
    assert bad["list"] == "orders" and bad["check"] == "see as another member" and bad["want"] == "0" and bad["got"] == "1"
    assert "Rule tests FAILED" in out["say"] and "another member" in out["say"]
    blk = H.blockers(r)
    assert any("Rule tests FAILED" in b for b in blk)
    monkeypatch.setattr(W, "rows", orig_rows)
    monkeypatch.setattr(W, "_can_read", real)
    RC.run(r)
    assert not any("Rule tests" in b for b in H.blockers(r))


def test_a_rule_change_makes_the_result_stale_and_it_runs_again(app_site, monkeypatch):
    from app.appmaker import backend as BE
    from app.site import applink as AL
    from app.site import rulecheck as RC
    _c, r = _linked(app_site)
    first = RC.run(r)
    fp = first["fp"]
    BE.change_schema(AL.project(r), {"add_list": [{"key": "feedback", "label": "Feedback", "rules": {"create": "public", "read": "admin"},
                                                    "fields": [{"key": "note", "type": "text"},
                                                               {"key": "secret", "type": "text", "private": True}]}]}, "test")
    again = RC.current(r)
    assert again["fp"] != fp and again["lists"] == 3 and again["ok"], again["failed"]
    names = {x["check"] for x in again["checks"] if x["list"] == "feedback"}
    assert {"add as a visitor", "see as a visitor", "see as the admin"} <= names
    assert "private field 'secret' as the admin" in names                              # the admin sees it; only the admin can read here


def test_after_a_change_the_tests_run_in_the_background(app_site, monkeypatch):
    import threading
    from app.config import get_settings
    from app.site import applink as AL
    from app.site import rulecheck as RC
    _c, r = _linked(app_site)
    monkeypatch.setattr(get_settings(), "site_rule_tests_bg", True)
    assert RC.last(r) is None
    RC.after_change(AL.project(r))
    for t in threading.enumerate():
        if t.name == "rule-tests":
            t.join(60)
    got = RC.last(r)
    assert got and got["ok"] and got["lists"] == 2
    monkeypatch.setattr(get_settings(), "site_rule_tests_bg", False)
    import os
    os.remove(RC._site_file(r))
    RC.after_change(AL.project(r))                                                       # switched off: nothing runs
    assert RC.last(r) is None


def test_a_website_without_lists_has_nothing_to_test(site_env):
    from tests.test_life import conv_ctx
    from app.site import rulecheck as RC
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    r = S._load(v["id"])
    out = RC.run(r)
    assert out["ok"] and out["lists"] == 0 and "no data lists" in out["say"]
    assert RC.blocker(r) == ""


def test_hooks_are_wired():
    import inspect
    from app.appmaker import backend as BE
    from app.appmaker.logic import service as LS
    from app.site import hosting as H
    assert "RC.after_change(r)" in inspect.getsource(BE.change_schema)
    assert "RC.after_change(r)" in inspect.getsource(LS.apply)
    assert "RC.blocker(r)" in inspect.getsource(H.blockers)
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "webstudio.js").read_text()
    assert 'data-coll="__rules">Rule tests' in js and "/rule-tests`" in js and "key === '__rules'" in js
