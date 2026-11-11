"""v0.542 NAKSHA (App Sahayak Pillar K, Phase 62): her one line -> a spec -> the app, one module at a time.

The thing worth testing here is not that a model can write a plan - it is that the plan CANNOT promise what Hoola
cannot build, that her Haan is per module and does not carry over when the module changes underneath it, that a
build really drives the engines (lists appear, a brain is drafted, a second app is made) and really proves itself,
and that a change rebuilds only what it touched. Every test below fails if that stops being true.

The author is injected (`ask=`), so none of this needs a model: a real spec written by hand goes through the real
checker and the real engines.
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


def _spec(**over):
    """A small, real naksha: one module that stands alone, one that needs it."""
    base = {
        "one_line": "Sharma Kirana ki app: ghar pe delivery",
        "user_types": [{"key": "customer", "label": "Customer", "role": "member", "app": "main", "who": "Jo saman mangati hai"},
                       {"key": "rider", "label": "Rider", "role": "staff", "app": "rider", "who": "Jo pahunchata hai"}],
        "modules": [
            {"key": "complaints", "label": "Shikayat", "why": "Customer apni shikayat bhej sake", "needs": [],
             "parts": {"lists": [{"key": "complaints", "label": "Shikayat",
                                  "rules": {"create": "member", "read": "own", "update": "admin", "delete": "admin"},
                                  "fields": [{"key": "name", "label": "Naam", "type": "text", "required": True},
                                             {"key": "phone", "label": "Phone", "type": "phone", "required": True,
                                              "private": True},
                                             {"key": "what", "label": "Kya hua", "type": "long_text"}]}],
                       "stories": [{"as": "customer", "want": "apni shikayat bhejun", "so_that": "theek ho jaye"}]}},
            {"key": "followup", "label": "Follow up", "why": "Staff shikayat par kaam kare", "needs": ["complaints"],
             "parts": {"push": True,
                       "stories": [{"as": "staff", "want": "shikayat dekhun", "so_that": "jawab de sakun"}]}},
        ],
        "questions": [{"ask": "Delivery sirf Pune mein?", "changes": "complaints"},
                      {"ask": "Aapka pasandeeda rang?", "changes": ""}],
        "release": [{"phase": "Pehle", "modules": ["complaints"], "why": "Isi se shuru"}],
    }
    base.update(over)
    return base


def _ask(spec):
    return lambda system, prompt: spec


# ---------------------------------------------------------------- the checker is the promise
def test_the_naksha_cannot_promise_what_hoola_cannot_build(droid_env):
    from app.appmaker import architect as AR
    bad = _spec(modules=[
        {"key": "ai_bot", "label": "AI bot", "why": "...", "parts": {"chatbot": True}},
        {"key": "fields", "label": "Fields", "why": "...",
         "parts": {"lists": [{"key": "x", "fields": [{"key": "f", "type": "hologram"}]}]}},
        {"key": "faces", "label": "Faces", "why": "...", "parts": {"faces": ["spaceship"]}},
        {"key": "conn", "label": "Conn", "why": "...", "parts": {"connect": ["telepathy"]}},
    ])
    got = AR.check(bad)
    joined = " ".join(got["errors"])
    assert "chatbot" in joined, got["errors"]
    assert "hologram" in joined and "spaceship" in joined and "telepathy" in joined
    assert got["spec"]["modules"] == []

    ok = AR.check(_spec())
    assert ok["errors"] == [], ok["errors"]
    assert [m["key"] for m in ok["spec"]["modules"]] == ["complaints", "followup"]


def test_a_module_may_not_need_one_that_comes_later(droid_env):
    from app.appmaker import architect as AR
    s = _spec()
    s["modules"][0]["needs"] = ["followup"]           # the first needs the second
    got = AR.check(s)
    assert any("baad mein aata hai" in e or "iske baad" in e for e in got["errors"]), got["errors"]


def test_only_a_question_that_changes_the_build_survives(droid_env):
    from app.appmaker import architect as AR
    got = AR.check(_spec())
    asks = [q["ask"] for q in got["spec"]["questions"]]
    assert "Delivery sirf Pune mein?" in asks
    assert not any("rang" in a for a in asks), "a question that changes nothing is not a question"
    assert any("hata diya" in w for w in got["warnings"])


def test_a_private_field_stays_private_through_the_build(droid_env):
    from app.appmaker import architect as AR
    from app.appmaker import backend as BE
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    AR.plan(r, "shikayat", ask=_ask(_spec()))
    AR.approve(_app(aid), "complaints")
    AR.build(_app(aid), "complaints", run_tests=False)
    coll = next(c for c in BE.schema(_app(aid))["collections"] if c["key"] == "complaints")
    phone = next(f for f in coll["fields"] if f["key"] == "phone")
    assert phone.get("private") is True, phone


# ---------------------------------------------------------------- her Haan, per module
def test_her_haan_is_per_module_and_respects_the_order(droid_env):
    import pytest
    from app.appmaker import architect as AR
    from app.site import webapp as W
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    out = AR.plan(r, "shikayat", ask=_ask(_spec()))
    assert len(out["modules"]) == 2 and all(m["state"] == "waiting" for m in out["modules"])

    with pytest.raises(W.AppError):                   # a module that needs an unbuilt one cannot be approved
        AR.approve(_app(aid), "followup")
    with pytest.raises(W.AppError):                   # a stale hash is never approved blind
        AR.approve(_app(aid), "complaints", "deadbeefdeadbeef")

    AR.approve(_app(aid), "complaints", out["hash"])
    assert AR.card(_app(aid))["modules"][0]["state"] == "approved"
    with pytest.raises(W.AppError):                   # building an unapproved module is refused
        AR.build(_app(aid), "followup")


def test_her_haan_does_not_carry_over_when_the_module_changes(droid_env):
    from app.appmaker import architect as AR
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    out = AR.plan(r, "shikayat", ask=_ask(_spec()))
    AR.approve(_app(aid), "complaints", out["hash"])
    assert AR.card(_app(aid))["modules"][0]["state"] == "approved"

    changed = _spec()
    changed["modules"][0]["parts"]["lists"][0]["fields"].append({"key": "area", "label": "Area", "type": "text"})
    got = AR.revise(_app(aid), "area bhi poochho", ask=_ask(changed))
    assert "complaints" in got["touched"]
    assert AR.card(_app(aid))["modules"][0]["state"] == "waiting", "she approved a different module"


# ---------------------------------------------------------------- the build drives the real engines
def test_building_a_module_really_changes_the_app(droid_env):
    from app.appmaker import architect as AR
    from app.appmaker import backend as BE
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    out = AR.plan(r, "shikayat", ask=_ask(_spec()))
    before = {c["key"] for c in BE.schema(_app(aid))["collections"]}
    assert "complaints" not in before

    AR.approve(_app(aid), "complaints", out["hash"])
    got = AR.build(_app(aid), "complaints", run_tests=False)
    assert got["ok"], got
    after = {c["key"] for c in BE.schema(_app(aid))["collections"]}
    assert "complaints" in after, "the list the naksha promised is not in her app"
    assert AR.card(_app(aid))["modules"][0]["state"] == "built"
    assert AR.changelog(_app(aid))[0]["module"] == "complaints"
    assert "ban gaya" in AR.changelog(_app(aid))[0]["said"]


def test_a_built_module_is_proved_by_its_own_stories(droid_env):
    """Pillar J, used by Pillar K: the module's stories become scenario tests and are RUN against a real server."""
    from app.appmaker import architect as AR
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    out = AR.plan(r, "shikayat", ask=_ask(_spec()))
    AR.approve(_app(aid), "complaints", out["hash"])
    got = AR.build(_app(aid), "complaints")           # run_tests on
    assert got["proof"]["ran"] is True, got["proof"]
    assert got["proof"]["pass"] >= 1 and got["proof"]["fail"] == 0, got["proof"]
    assert "kahaniyan pass" in got["says"]
    assert got["ok"] is True


def test_a_part_that_needs_her_key_is_named_and_never_pretended(droid_env):
    from app.appmaker import architect as AR
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    s = _spec()
    s["modules"] = [{"key": "paisa", "label": "Online payment", "why": "Customer app se hi pay kare", "needs": [],
                     "parts": {"pay": {"what": "order ka paisa"}, "connect": ["shiprocket"], "track": True}}]
    out = AR.plan(r, "online payment", ask=_ask(s))
    assert out["modules"][0]["setup"], "a module needing her keys must say so BEFORE she approves it"
    AR.approve(_app(aid), "paisa", out["hash"])
    got = AR.build(_app(aid), "paisa", run_tests=False)
    joined = " ".join(got["next_steps"])
    assert "gateway" in joined and "shiprocket" in joined and "tracking" in joined
    assert not any("pay" in d for d in got["done"]), "a payment nobody configured must not read as done"


# ---------------------------------------------------------------- a change rebuilds only what it touched
def test_a_change_leaves_the_untouched_modules_alone(droid_env):
    from app.appmaker import architect as AR
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    out = AR.plan(r, "shikayat", ask=_ask(_spec()))
    for key in ("complaints", "followup"):
        AR.approve(_app(aid), key, AR.card(_app(aid))["hash"])
        got = AR.build(_app(aid), key, run_tests=False)
        assert got["ok"], got          # instant push is not set up on this machine: that is a NEXT STEP, not a break
    assert all(m["state"] == "built" for m in AR.card(_app(aid))["modules"])

    changed = _spec()
    changed["modules"][1]["parts"]["track"] = True            # only the SECOND module changes
    got = AR.revise(_app(aid), "rider ki location bhi", ask=_ask(changed))
    assert got["touched"] == ["followup"], got
    states = {m["key"]: m["state"] for m in AR.card(_app(aid))["modules"]}
    assert states["complaints"] == "built", "an untouched module must not be disturbed"
    assert states["followup"] == "changed"
    assert "Badlav" in AR.changelog(_app(aid))[0]["said"]


def test_a_new_module_is_added_and_a_dropped_one_is_reported(droid_env):
    from app.appmaker import architect as AR
    aid, _c, _k, _b = _built(droid_env)
    r = _app(aid)
    AR.plan(r, "shikayat", ask=_ask(_spec()))
    s = _spec()
    s["modules"] = [s["modules"][0], {"key": "rating", "label": "Rating", "why": "Customer raay de", "needs": ["complaints"],
                                      "parts": {"stories": [{"as": "customer", "want": "raay dun"}]}}]
    got = AR.revise(_app(aid), "rating bhi chahiye", ask=_ask(s))
    assert got["added"] == ["rating"] and got["removed"] == ["followup"]


# ---------------------------------------------------------------- the surfaces
def test_the_routes_and_the_tool_are_reachable(droid_env):
    import asyncio
    import pytest
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.main import app
    aid, conv, _k, _b = _built(droid_env)
    c = TestClient(app)
    paths = {getattr(x, "path", "") for x in app.routes}
    assert "/api/apps/{ref}/naksha" in paths and "/api/apps/{ref}/naksha/{what}" in paths
    assert c.get(f"/api/apps/{aid}/naksha").status_code == 200
    assert c.post(f"/api/apps/{aid}/naksha/nope").status_code == 404

    ctx = Ctx(tenant_id=T, conversation_id=conv)
    card = asyncio.run(dispatch("app_dekho", {"what": "naksha", "app": aid}, ctx))
    assert card["has"] is False and "naksha" in card["says"]
    with pytest.raises(ToolError):              # approving a module is HER tap, never the tool's
        asyncio.run(dispatch("app_banao", {"action": "naksha_ok", "app": aid, "module": "x"}, ctx))


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.813.0"
