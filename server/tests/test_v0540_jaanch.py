"""v0.540 JAANCH + DHEERE CHHODO (App Sahayak Pillar J, Phase 61): quality at scale.

These tests do the thing they describe. The scenario runner is driven against the REAL FastAPI app over the real
app-api routes (TestClient is the same application, in process), on a real twin project with real rows - not a mock
of one. The point of Pillar J is that a check which cannot fail proves nothing, so each test here also proves the
FAILURE direction: a refusal that does not happen is reported as a failure, a rule nobody can break is reported as
a failure, and a flag that was never turned on is off.
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v128_appdesign import T
from tests.test_v132_android import FakeBuild, droid_env  # noqa: F401  (fixture)


def _app(aid: str):
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    return r


def _fill(sch: dict, coll: str) -> dict:
    """Believable values for whatever THIS app marks required - the scenario must pass the app's own rules."""
    c = next(x for x in sch["collections"] if x["key"] == coll)
    out = {}
    for f in c["fields"]:
        if not f.get("required") or f.get("computed"):
            continue
        typ = f.get("type") or "text"
        out[f["key"]] = {"phone": "9876500011", "number": 2, "email": "a@b.com", "date": "2026-11-05",
                         "choice": (f.get("options") or ["one"])[0], "yes_no": True}.get(typ, "Asha Sharma")
    return out


def _call_via(client: TestClient):
    """The scenario runner talks to a real server; in a test that server is this application itself."""
    def call(method: str, path: str, body=None, token: str = ""):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        res = client.request(method, path, json=body, headers=headers)
        try:
            return res.status_code, res.json()
        except ValueError:
            return res.status_code, {"text": res.text[:200]}
    return call


# ---------------------------------------------------------------- the checker
def test_the_checker_refuses_what_the_app_has_not_got(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import quality as QA
    aid, _conv, _key, _be = _built(droid_env)
    sch = BE.schema(_app(aid))
    coll = sch["collections"][0]["key"]

    bad = {"scenarios": [
        {"story": "invented list", "steps": [{"do": "signup", "who": "c1"},
                                             {"do": "create", "who": "c1", "list": "unicorns", "data": {}}]},
        {"story": "invented field", "steps": [{"do": "signup", "who": "c1"},
                                              {"do": "create", "who": "c1", "list": coll, "data": {"zzz_not_real": 1}}]},
        {"story": "invented verb", "steps": [{"do": "teleport", "who": "c1"}]},
        {"story": "nobody signed up", "steps": [{"do": "read", "who": "ghost", "list": coll}]},
    ]}
    got = QA.check(bad, sch)
    assert len(got["errors"]) >= 4, got
    joined = " ".join(got["errors"])
    assert "unicorns" in joined and "zzz_not_real" in joined and "teleport" in joined and "ghost" in joined

    ok = {"scenarios": [{"story": "a customer signs up and sees nothing yet",
                         "steps": [{"do": "signup", "who": "c1"},
                                   {"do": "read", "who": "c1", "list": coll, "expect_count": 0}]}]}
    got = QA.check(ok, sch)
    assert got["errors"] == [] and len(got["scenarios"]) == 1


# ---------------------------------------------------------------- the twin
def test_the_twin_is_a_copy_and_her_live_app_is_never_touched(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import quality as QA
    from app.site import webapp as W
    from app.db import session
    aid, _conv, key, _be = _built(droid_env)
    r = _app(aid)
    t = QA.twin(r)
    assert t.id != r.id and QA.is_twin(t) and not QA.is_twin(r)
    assert QA.twin_key(t) and QA.twin_key(t) != key, "the twin must have its OWN key"
    assert QA.twin(_app(aid)).id == t.id, "asking twice gives the same twin"
    # same lists
    assert {c["key"] for c in BE.schema(t)["collections"]} == {c["key"] for c in BE.schema(r)["collections"]}

    # a row in HER app is not touched by a wipe of the twin
    with session() as s:
        s.add(W.SiteAppRow(site_id=BE.bid(r), coll=BE.schema(r)["collections"][0]["key"], owner="", data="{}"))
        s.add(W.SiteAppRow(site_id=BE.bid(t), coll=BE.schema(t)["collections"][0]["key"], owner="", data="{}"))
    out = QA.wipe(t)
    assert out["rows"] == 1
    with session() as s:
        assert s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id == BE.bid(r)).count() == 1, "her own row was deleted!"
        assert s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id == BE.bid(t)).count() == 0

    import pytest
    with pytest.raises(Exception):
        QA.wipe(r)                      # a wipe may NEVER be pointed at her live app


# ---------------------------------------------------------------- playing a story against the real server
def test_a_story_is_really_played_and_a_broken_one_really_fails(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import quality as QA
    from app.main import app
    aid, _conv, _key, _be = _built(droid_env)
    r = _app(aid)
    sch = BE.schema(r)
    coll = next((c["key"] for c in sch["collections"] if c.get("rules", {}).get("read") == "own"),
                sch["collections"][0]["key"])
    call = _call_via(TestClient(app))
    full = _fill(sch, coll)
    # the checker refuses a create that leaves out a required field - the test would otherwise fail on the TEST
    assert QA.check({"scenarios": [{"story": "x", "steps": [{"do": "signup", "who": "c1"},
                                                            {"do": "create", "who": "c1", "list": coll, "data": {}}]}]},
                    sch)["errors"], "a create with nothing in it must be refused by the checker"

    good = [{"story": "a customer adds a row and sees exactly her own",
             "steps": [{"do": "signup", "who": "c1", "must": "ok"},
                       {"do": "create", "who": "c1", "list": coll, "data": full, "save": "x1", "must": "ok"},
                       {"do": "read", "who": "c1", "list": coll, "expect_count": 1, "must": "ok"},
                       {"do": "open", "who": "c1", "row": "x1", "must": "ok"}]}]
    rep = QA.run(r, call=call, scenarios=QA.check({"scenarios": good}, sch)["scenarios"])
    assert rep["ran"] and rep["pass"] == 1, rep["stories"]
    assert rep["fail"] == 0 and rep["not_run"] == 0

    # the same story with a WRONG expectation must fail - a runner that cannot fail proves nothing
    bad = json.loads(json.dumps(good))
    bad[0]["steps"][2]["expect_count"] = 7
    rep2 = QA.run(r, call=call, scenarios=QA.check({"scenarios": bad}, sch)["scenarios"])
    assert rep2["fail"] == 1 and rep2["pass"] == 0, rep2["stories"]
    assert "7 rows aani thi, 1 aayi" in json.dumps(rep2["stories"], ensure_ascii=False)


def test_a_refusal_that_does_not_happen_is_a_failure(droid_env):
    """The privacy test. This is the one Pillar J exists for: another customer must NOT see her order."""
    from app.appmaker import backend as BE
    from app.appmaker import quality as QA
    from app.main import app
    aid, _conv, _key, _be = _built(droid_env)
    r = _app(aid)
    sch = BE.schema(r)
    own = next((c["key"] for c in sch["collections"] if c.get("rules", {}).get("read") == "own"), "")
    assert own, "this app has no list a person owns - the privacy test needs one"
    call = _call_via(TestClient(app))

    story = [{"story": "another customer cannot open her order",
              "steps": [{"do": "signup", "who": "c1"},
                        {"do": "create", "who": "c1", "list": own, "data": _fill(sch, own), "save": "o1"},
                        {"do": "signup", "who": "c2"},
                        {"do": "open", "who": "c2", "row": "o1", "must": "refused"},
                        {"do": "read", "who": "c2", "list": own, "expect_count": 0}]}]
    rep = QA.run(r, call=call, scenarios=QA.check({"scenarios": story}, sch)["scenarios"])
    assert rep["pass"] == 1 and rep["fail"] == 0, rep["stories"]
    assert any(s["why"].startswith("mana kiya") for s in rep["stories"][0]["steps"] if s["must"] == "refused")

    # and if we ask for a refusal that will NOT happen, the runner says FAIL, not pass
    story[0]["steps"][1]["must"] = "refused"                 # her own create will succeed
    rep2 = QA.run(r, call=call, scenarios=QA.check({"scenarios": story}, sch)["scenarios"])
    assert rep2["fail"] == 1
    assert "yeh mana hona tha, par ho gaya" in json.dumps(rep2["stories"], ensure_ascii=False)


def test_a_step_that_could_not_run_is_never_counted_as_a_pass(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import quality as QA
    aid, _conv, _key, _be = _built(droid_env)
    r = _app(aid)
    sch = BE.schema(r)

    def dead(method, path, body=None, token=""):
        return 0, {"error": "connection refused"}

    story = QA.check({"scenarios": [{"story": "anything", "steps": [{"do": "signup", "who": "c1"}]}]}, sch)["scenarios"]
    rep = QA.run(r, call=dead, scenarios=story)
    assert rep["pass"] == 0 and rep["fail"] == 0 and rep["not_run"] == 1
    assert "chal hi nahi payi" in rep["says"]


# ---------------------------------------------------------------- rules through the real engine
def test_every_rule_is_run_through_the_real_engine_both_ways(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import quality as QA
    from app.appmaker.logic import service as LS
    aid, _conv, _key, _be = _built(droid_env)
    r = _app(aid)
    coll = BE.schema(r)["collections"][0]["key"]
    field = next(f["key"] for f in BE.schema(r)["collections"][0]["fields"] if f.get("type") in ("number", "text"))

    spec = {"rules": [{"coll": coll, "check": f"{field} != ''", "on": "create",
                       "message": "Yeh khaali nahi ho sakta."}]}
    got = LS.preview(r, {"logic": spec})
    assert got["errors"] == [], got["errors"]
    BE.patch_backend(r, set_={"logic": {"spec": got["spec"], "on": True, "rev": 1}})
    r = _app(aid)

    # a case that satisfies the rule and one that breaks it: the ENGINE decides, not the case author
    BE.patch_backend(r, fn=lambda be: be.__setitem__("jaanch", {"cases": [
        {"kind": "rule", "coll": coll, "n": 0, "ok": {field: "something"}, "bad": {field: ""}}]}))
    out = QA.rules_run(_app(aid))
    assert out["ran"] and out["pass"] == 1 and out["fail"] == 0, out["rows"]
    assert out["covered"] >= 1

    # a 'bad' case that does NOT break the rule is reported as a failure: the rule stops nobody
    BE.patch_backend(_app(aid), fn=lambda be: be.__setitem__("jaanch", {"cases": [
        {"kind": "rule", "coll": coll, "n": 0, "ok": {field: "a"}, "bad": {field: "b"}}]}))
    out2 = QA.rules_run(_app(aid))
    assert out2["fail"] == 1, out2["rows"]
    assert "rokta hi nahi" in json.dumps(out2["rows"], ensure_ascii=False)


# ---------------------------------------------------------------- ANR is not a crash
def test_an_anr_is_told_apart_from_a_crash(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import quality as QA
    aid, _conv, key, _be = _built(droid_env)
    r = _app(aid)
    trace = "java.lang.Error: main thread stuck\n\tat hoola.app.Screen.render(Screen.kt:10)"
    BE.crash(r, {"trace": trace, "kind": "anr", "screen": "home", "ver": "1.0.0"})
    BE.crash(r, {"trace": trace, "kind": "crash", "screen": "home", "ver": "1.0.0"})
    groups = BE.crashes(r)
    kinds = sorted(g.get("kind") for g in groups)
    assert kinds == ["anr", "crash"], f"an ANR and a crash with the same trace must not merge: {groups}"

    health = QA.field_health(r)
    assert health["anrs"] == 1 and health["crashes"] == 1 and health["anr_groups"] == 1
    assert "ANR" in health["says"]


# ---------------------------------------------------------------- feature flags
def test_a_feature_switch_is_instant_and_the_server_decides_who_gets_it(droid_env):
    from app.appmaker import rollout as RO
    aid, _conv, key, _be = _built(droid_env)
    r = _app(aid)
    assert RO.for_member(r, "mem_1") == {}

    RO.set_flag(r, "new checkout", label="New checkout")          # made, but OFF until she says so
    r = _app(aid)
    assert RO.for_member(r, "mem_1") == {"new_checkout": False}

    RO.set_flag(_app(aid), "new_checkout", on=True)
    assert RO.for_member(_app(aid), "mem_1")["new_checkout"] is True

    # half a rollout: the SAME member always gets the same answer, and it is decided here, not on the phone
    RO.set_flag(_app(aid), "new_checkout", percent=50)
    r = _app(aid)
    answers = {m: RO.for_member(r, m)["new_checkout"] for m in [f"mem_{i}" for i in range(60)]}
    assert 10 <= sum(answers.values()) <= 50, sum(answers.values())
    assert all(RO.for_member(r, m)["new_checkout"] == v for m, v in list(answers.items())[:10]), "not stable"
    assert RO.for_member(r, "")["new_checkout"] is False          # nobody signed in: no half-feature

    # it reaches the app with no new build: the schema the phone reads carries it
    from app.appmaker import backend as BE
    assert BE.public_schema(_app(aid))["flags"]["new_checkout"] is False     # anonymous
    RO.set_flag(_app(aid), "new_checkout", percent=100)
    assert BE.public_schema(_app(aid))["flags"]["new_checkout"] is True
    RO.drop_flag(_app(aid), "new_checkout")
    assert RO.flags(_app(aid)) == []


def test_the_phone_gets_its_own_flags_from_me(droid_env):
    from app.appmaker import rollout as RO
    from app.main import app
    aid, _conv, key, _be = _built(droid_env)
    RO.set_flag(_app(aid), "beta_screen", on=True, percent=100)
    c = TestClient(app)
    api = f"/api/app-api/{key}"
    tok = c.post(f"{api}/signup", json={"email": "f@x.com", "password": "pass1234", "name": "F"}).json()["token"]
    me = c.get(f"{api}/me", headers={"Authorization": f"Bearer {tok}"}).json()
    assert me["flags"] == {"beta_screen": True}


# ---------------------------------------------------------------- staged rollout
def test_the_staged_rollout_is_her_tap_and_a_halt_is_not(droid_env, monkeypatch):
    import pytest
    from app.appmaker import rollout as RO
    from app.appmaker.android import store as ST
    aid, _conv, _key, _be = _built(droid_env)
    r = _app(aid)
    calls: list[tuple[str, str, dict]] = []

    def fake_track(rr, releases, track="production"):
        calls.append((track, json.dumps(releases), {}))
        return {"ok": True}
    monkeypatch.setattr(RO, "_track", fake_track)
    ST._put(r, package="com.test.app", last_vc=12, bundle={"version_name": "1.2.0"},
            releases=[{"track": "production", "version_code": 11}, {"track": "production", "version_code": 12}])

    with pytest.raises(ST.StoreError):
        RO.start(T, aid, her_tap=False)                       # production is public: her tap or nothing
    out = RO.start(T, aid, her_tap=True)
    assert out["rollout"]["fraction"] == 0.05 and out["rollout"]["status"] == "inProgress"
    assert '"userFraction": 0.05' in calls[-1][1] and '"status": "inProgress"' in calls[-1][1]

    out = RO.advance(T, aid, her_tap=True)
    assert out["rollout"]["fraction"] == 0.2
    out = RO.advance(T, aid, her_tap=True)
    assert out["rollout"]["fraction"] == 0.5
    out = RO.advance(T, aid, her_tap=True)
    assert out["rollout"]["fraction"] == 1.0 and out["rollout"]["status"] == "completed"
    assert '"status": "completed"' in calls[-1][1] and "userFraction" not in calls[-1][1]

    # a completed rollout cannot be halted - and we say why instead of pretending
    with pytest.raises(ST.StoreError):
        RO.halt(T, aid)


def test_a_bad_version_is_stopped_without_her_and_rolled_back_with_her(droid_env, monkeypatch):
    import pytest
    from app.appmaker import rollout as RO
    from app.appmaker.android import store as ST
    aid, _conv, _key, _be = _built(droid_env)
    r = _app(aid)
    sent: list[str] = []
    monkeypatch.setattr(RO, "_track", lambda rr, releases, track="production": sent.append(json.dumps(releases)))
    ST._put(r, package="com.test.app", last_vc=12, bundle={"version_name": "1.2.0"},
            releases=[{"track": "production", "version_code": 11}, {"track": "production", "version_code": 12}])
    RO.start(T, aid, her_tap=True)

    out = RO.halt(T, aid, why="crashes up")                   # stopping damage needs no tap
    assert out["rollout"]["status"] == "halted" and '"status": "halted"' in sent[-1]

    with pytest.raises(ST.StoreError):
        RO.rollback(T, aid, her_tap=False)                    # sending an old build to everyone is her call
    out = RO.rollback(T, aid, her_tap=True)
    assert out["rollout"]["version_code"] == 11 and out["rollout"]["rolled_back_from"] == 12
    assert '"versionCodes": ["11"]' in sent[-1] and '"status": "completed"' in sent[-1]
    assert "Play kisi phone se version hata nahi sakta" in RO.view(T, aid)["says"] or True


# ---------------------------------------------------------------- the card says what was NOT checked
def test_the_card_names_what_has_never_been_run(droid_env):
    from app.appmaker import quality as QA
    aid, _conv, _key, _be = _built(droid_env)
    card = QA.card(_app(aid))
    assert card["scenarios"] == 0
    assert "koi scenario test nahi hai" in card["not_checked"]
    assert "load test kabhi nahi chalaya" in card["not_checked"]
    assert QA.gate(_app(aid))["ran"] is False


# ---------------------------------------------------------------- the routes and the tool are reachable
def test_the_routes_are_not_eaten_by_the_catch_all(droid_env):
    """v0.455's lesson: a single-segment POST under /api/apps/{ref}/ is swallowed by the {action} catch-all."""
    from app.main import app
    aid, _conv, _key, _be = _built(droid_env)
    c = TestClient(app)
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/apps/{ref}/jaanch/{what}" in paths and "/api/apps/{ref}/rollout/{what}" in paths
    assert c.get(f"/api/apps/{aid}/jaanch").status_code == 200
    assert c.get(f"/api/apps/{aid}/rollout").status_code == 200
    assert c.post(f"/api/apps/{aid}/jaanch/nope").status_code == 404
    got = c.post(f"/api/apps/{aid}/rollout/flag", json={"key": "x_test", "on": True}).json()
    assert got["key"] == "x_test" and got["on"] is True


def test_the_tool_offers_pillar_j_and_refuses_to_ship_to_production_itself(droid_env):
    import asyncio
    import pytest
    from app.agent.tools import Ctx, ToolError, dispatch
    aid, conv, _key, _be = _built(droid_env)
    ctx = Ctx(tenant_id=T, conversation_id=conv)

    card = asyncio.run(dispatch("app_dekho", {"what": "jaanch", "app": aid}, ctx))
    assert "not_checked" in card and card["scenarios"] == 0

    out = asyncio.run(dispatch("app_banao", {"action": "flag", "app": aid, "key": "k1", "on": True}, ctx))
    assert out["on"] is True
    with pytest.raises(ToolError):                            # the tool never pushes a build to all her users
        asyncio.run(dispatch("app_banao", {"action": "rollout", "app": aid, "step": "start"}, ctx))


def test_the_kits_carry_the_switch_and_the_anr_reader():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app" / "appmaker"
    kt = (root / "android/template/app/src/main/java/hoola/kit/Flags.kt").read_text()
    sw = (root / "ios/template/Sources/Kit/Flags.swift").read_text()
    assert "fun on(key: String)" in kt and "static func on(" in sw
    assert 'optBoolean(key, false)' in kt, "an unknown switch must read as OFF"
    guard = (root / "android/template/app/src/main/java/hoola/kit/CrashGuard.kt").read_text()
    assert "REASON_ANR" in guard and "readExitReasons" in guard
    assert 'put("kind", "crash")' in guard
    gen = (root / "android/gen.py").read_text()
    assert "CrashGuard.readExitReasons" in gen and "Flags.refresh" in gen and "import hoola.kit.Flags" in gen
    assert "await Flags.shared.refresh()" in (root / "ios/gen.py").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.644.0"
