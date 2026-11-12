"""v0.841 PROOF (L15 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L15"): the Studio card (L0, built here for the first time) and the
three proof apps - a clinic (appointment requests saved through Cloud), a coaching portal with roles and payment records, a
dispatch dashboard. The card's free half is checked here (ask set, calibrated scorer, interleave + budget stop with stub engines);
the proof apps are built in the Docker box and walked in Chromium (skipped where the box is not)."""
import json

import pytest

from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture + helper)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_the_ask_set_and_the_scorer_are_calibrated():
    from app.quality import studiocard as SC
    assert len(SC.ASKS) == 30 and SC.set_problems() == []
    assert {k: sum(1 for a in SC.ASKS if a["kind"] == k) for k in ("brochure", "shop", "portal", "saas")} == {"brochure": 10, "shop": 8, "portal": 8, "saas": 4}
    assert sum(1 for a in SC.ASKS if a.get("edit")) == 3
    cal = SC.calibration()
    assert len(cal) == 9 and all(c["ok"] for c in cal), cal                     # each planted fault fails for ITS OWN reason
    bad = [dict(a) for a in SC.ASKS]
    bad[0]["engine"] = "app"
    bad.append(dict(bad[1]))
    probs = SC.set_problems(bad)
    assert any("engine does not fit" in p for p in probs) and any("duplicate" in p for p in probs) and any("brochure: 11" in p for p in probs)
    fc = SC.free_card()
    assert fc["verdict"] == "PASS" and "needs a model" in fc["live"]


def test_live_card_interleaves_stops_at_the_budget_and_compares(monkeypatch):
    from app.quality import studiocard as SC
    spent = {"v": 0.0}
    monkeypatch.setattr(SC, "_spent", lambda: spent["v"])
    ran = []

    def mk(engine, inr):
        def run(a):
            ran.append(a["id"])
            spent["v"] += inr
            r = {"built": True, "seconds": 60, "inr": inr, "errors": 0, "gate_fails": 0, "design_fails": 0, "text": " ".join(a["must"])}
            if a.get("edit"):
                r["edit"] = {"ok": True, "seconds": 1.5, "inr": 0}
            if a["id"] == "p02":
                raise RuntimeError("box down")
            return r
        return run
    items = [a for a in SC.ASKS if a["id"] in ("b01", "b02", "b03", "p01", "p02", "p03")]
    card = SC.live_card(items, 150.0, {"site": mk("site", 30), "app": mk("app", 50)})
    assert ran[:4] == ["b01", "p01", "b02", "p02"]                              # site and app take turns
    assert card["ran"] < 6 and card["spent_inr"] >= 150 and any(r["skipped"] for r in card["rows"])    # it stopped itself at the budget
    crashed = next(r for r in card["rows"] if r["id"] == "p02")
    assert not crashed["ok"] and any("box down" in x for x in crashed["reasons"])
    assert card["site"]["median_edit_s"] == 1.5 and card["all"]["passed"] >= 2
    with pytest.raises(ValueError, match="budget"):
        SC.live_card(items, 0)
    a = SC.summarise([SC.score_run(items[0], mk("site", 30)(items[0]))])
    spent["v"] = 0
    b = SC.summarise([SC.score_run(items[0], {**mk("site", 10)(items[0])})])
    verdicts = {(x["engine"], x["metric"]): x["verdict"] for x in SC.compare(a, b)}
    assert verdicts[("site", "median_inr")] == "better" and verdicts[("site", "passed")] == "same"


def test_cli_and_card_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.quality import __main__ as M
    from app.quality import studiocard as SC
    assert M._studiocard(["--live"]) == 2                                          # a live card needs a budget
    assert M._studiocard([]) == 0
    c = SC.save(SC.summarise([], "live"), "x")
    assert c["file"].endswith("-x.json") and json.load(open(c["file"]))["kind"] == "live"


def test_three_proof_apps_are_in_the_proof_set():
    from app.appengine import proof as P
    from app.appengine import proof_apps as PA
    keys = [a["key"] for a in PA.ASKS]
    assert {"clinic", "portal", "dispatch"} <= set(keys) and len(keys) == 7
    assert set(P.RULE_CHECKS) == {"portal", "dispatch"}
    portal = next(a for a in PA.ASKS if a["key"] == "portal")
    pay = next(c for c in portal["cloud"] if c["key"] == "payments")
    assert pay["rules"] == {"create": "member", "read": "own", "update": "admin", "delete": "admin"}     # students: own only; the office confirms


def test_portal_and_dispatch_are_built_walked_and_their_rules_hold(ae_env, monkeypatch):
    _box()
    import os
    from app.appengine import proof as P
    from app.appengine import proof_apps as PA
    from app.appengine import service as AE
    from tests.test_v0814_app_engine import _tool
    srv, port = P._server()
    try:
        for key in ("portal", "dispatch"):
            ask = next(a for a in PA.ASKS if a["key"] == key)
            aid = _tool(action="create", name=ask["name"], brief=ask["brief"], palette=ask["palette"])["id"]
            _tool(action="cloud_change", app=aid, changes=ask["cloud"])
            for path, code in ask["files"].items():
                _tool(action="write", app=aid, path=path, code=code)
            b = AE.wait_build(T, aid)
            r = AE._load(T, aid)
            assert b.get("built") and json.loads(r.last_build)["types_ok"], b.get("say")
            assert AE.check_all(r)["ok"], AE.check_all(r)["problems"][:3]
            assert P.RULE_CHECKS[key](r), key
            if os.environ.get("HOOLA_CHROMIUM") or True:
                w = P._walk(f"http://127.0.0.1:{port}/api/app-preview/{r.preview_token}/", ask["must"], ask["click"], ask["fill"], ask["after_fill"], ask["click"][0])
                assert not w["errors"] and not w["missing"] and w["clicked"] and w["filled"] and not w["phone_overflow"], w
    finally:
        srv.shutdown()
