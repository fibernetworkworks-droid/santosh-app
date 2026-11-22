"""v0.999.123 D10: proof + default. The same briefs built on the old engine and the new one, photographed by one
photographer, scored by one scorer and one critic, the order alternating; her pick per pair outranks the numbers;
blind Arena duels of the new engine's websites; a recommendation made by code that never decides; and HER tap,
bound to the evidence she saw, making the new engine the default for NEW websites (or back)."""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from app.quality import proofcard as PC
from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def _isolate(monkeypatch, root):
    """The card's files and her decision in a folder of this test (the server keeps them under data/)."""
    from app.site import enginedefault as ED
    (root / "quality").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(PC.DC, "_dir", lambda: root / "quality")
    monkeypatch.setattr(ED, "_file", lambda: root / "engine-default.json")
    ED._CACHE["mtime"] = None
    ED.FORCE["engine"] = ""


@pytest.fixture
def data(tmp_path, monkeypatch):
    from app.site import enginedefault as ED
    _isolate(monkeypatch, tmp_path / "data")
    yield tmp_path
    ED.FORCE["engine"] = ""
    ED._CACHE["mtime"] = None


def _run(ask, eng, design, built=True, site=""):
    return {"engine": eng, "built": built, "seconds": 300, "inr": 10.0, "purpose": ask["purpose"][0], "kind": "brochure",
            "text": " ".join(ask["must"]), "gate_fails": 0, "look_tells": 1, "site": site or f"site_{eng}_{ask['id']}",
            "shots": [{"file": f"{ask['id']}-{eng}-1.jpg", "what": "the home page"}],
            "critic": {"scores": {k: design for k in PC.DC.CRITERIA}, "design": float(design), "ai_made": False, "problems": []}}


def _card(data, designs=((6, 8), (7, 7), (8, 6)), running=False):
    asks = PC.DC.pick(len(designs))
    pairs = [PC.pair_of(a, _run(a, "old", o), _run(a, "new", n)) for a, (o, n) in zip(asks, designs)]
    run = "proofcard-20261122-101010"
    card = {"kind": "live", "set": PC.SET_V, "version": "x", "run": run, "pairs": pairs, "running": running,
            "planned": len(pairs), "spent_inr": 60.0, "budget_inr": 450.0}
    card.update(PC.summarise(pairs))
    (PC._dir() / f"{run}.json").write_text(json.dumps(card))
    return run, asks


# ---------------------------------------------------------------- 1. the card
def test_the_free_card_and_its_planted_pairs():
    c = PC.free_card()
    assert c["verdict"] == "PASS" and all(x["ok"] for x in c["calibration"]), [x for x in c["calibration"] if not x["ok"]]
    assert PC.order(0) == ("old", "new") and PC.order(1) == ("new", "old")      # neither engine always goes first


def test_the_card_builds_each_brief_on_both_engines_and_forces_only_its_own_process(data):
    from app.site import enginedefault as ED
    from app.site import prototype as PT
    seen: list[tuple[str, str, bool]] = []

    def runner(a, eng):
        seen.append((a["id"], eng, PT.react_on()))
        return _run(a, eng, 8 if eng == "new" else 6)
    PC.force("new")                                    # the runner sets the engine itself in the real card
    asks = PC.DC.pick(2)
    card = PC.live_card(asks, 100.0, runner=lambda a, eng: (PC.force(eng), runner(a, eng))[1])
    assert [(i, e) for i, e, _ in seen] == [(asks[0]["id"], "old"), (asks[0]["id"], "new"), (asks[1]["id"], "new"), (asks[1]["id"], "old")]
    assert all(r == (e == "new") for _, e, r in seen)  # each build on the engine it was asked for
    assert ED.FORCE["engine"] == "" and PT.react_on() is False                 # nothing left forced after the card
    assert card["critic"]["new"] == 2 and card["new"]["design"] == 8.0 and card["old"]["design"] == 6.0
    assert card["recommendation"]["ready"] is False and "compare" in card["recommendation"]["say"]   # she has not looked


# ---------------------------------------------------------------- 2. her picks, the evidence and her decision
def test_her_tap_on_the_evidence_she_saw_makes_the_new_engine_the_default(data):
    from app.site import enginedefault as ED
    from app.site import prototype as PT
    assert ED.view()["new_sites_on"] == "old" and PT.react_on() is False
    with pytest.raises(ED.DefaultError):
        ED.decide(True, "x")                           # no proof card yet
    run, asks = _card(data)
    ev = ED.evidence()
    assert ev["card"]["run"] == run and ev["hash"]
    PC.set_pick(run, asks[0]["id"], "new")
    with pytest.raises(ED.DefaultError) as e:
        ED.decide(True, ev["hash"])                    # her pick changed the evidence: she looks again
    assert e.value.code == 409
    ev = ED.evidence()
    assert ev["card"]["her"]["new"] == 1 and ev["recommendation"]["ready"] is True
    out = ED.decide(True, ev["hash"], run)
    assert out["engine"] == "new" and out["new_sites_on"] == "new" and "already built stay" in out["say"]
    assert PT.react_on() is True                       # the next NEW build is on the new engine
    ED.FORCE["engine"] = "old"
    assert PT.react_on() is False                      # the proof card's own builds are never steered by it
    ED.FORCE["engine"] = ""
    back = ED.decide(False)
    assert back["engine"] == "old" and PT.react_on() is False
    assert [h["engine"] for h in ED.state()["history"]] == ["new", "old"]


def test_a_running_card_is_not_decided_on_and_she_may_go_against_the_numbers(data):
    from app.site import enginedefault as ED
    run, asks = _card(data, ((8, 6), (8, 6)), running=True)
    with pytest.raises(ED.DefaultError):
        ED.decide(True, ED.evidence()["hash"])
    _card(data, ((8, 6), (8, 6)))
    ev = ED.evidence()
    assert ev["recommendation"]["ready"] is False and "lower" in " ".join(ev["recommendation"]["why"])
    assert ED.decide(True, ev["hash"])["engine"] == "new"          # her verdict outranks the numbers


def test_the_owner_routes(data):
    from app.main import app
    c = TestClient(app)
    run, asks = _card(data)
    g = c.get("/api/proofcard").json()
    assert g["card"]["run"] == run and g["engine"]["new_sites_on"] == "old" and g["card"]["hash"]
    assert c.post("/api/proofcard/pick", json={"run": run, "id": asks[0]["id"], "pick": "maybe"}).status_code == 400
    assert c.post("/api/proofcard/pick", json={"run": run, "id": asks[0]["id"], "pick": "new"}).status_code == 200
    h = c.get("/api/engine-default").json()["evidence"]["hash"]
    assert c.post("/api/engine-default", json={"go": True, "hash": "stale"}).status_code == 409
    assert c.post("/api/engine-default", json={"go": True, "hash": h}).json()["engine"] == "new"
    assert c.post("/api/engine-default", json={"go": False}).json()["engine"] == "old"
    assert c.get("/api/proofcard/shot/" + run + "/../../x.jpg").status_code == 404
    page = c.get("/console/proofcard")
    assert page.status_code == 200 and "proofcard.js" in page.text


# ---------------------------------------------------------------- 3. Arena duels of the new engine's websites
def test_a_blind_duel_of_the_new_engines_website(data, site_env, monkeypatch):  # noqa: F811
    from app.site import arena as AR
    run, asks = _card(data)
    monkeypatch.setattr(AR, "_home_shots", lambda site: [b"phone", b"desk"])
    got = PC.duel(run, asks[0]["id"], "lovable", "https://example.org/", shots=lambda url: [b"p", b"d"],
                  judge_fn=lambda a, b: {"winner": "a" if a == [b"phone", b"desk"] else "b", "why": "clearer", "a": {}, "b": {}})
    assert got["winner"] == "hoola"
    with pytest.raises(ValueError):
        PC.duel(run, asks[0]["id"], "lovable", "http://insecure.example/")
    d = PC.load(run)["duels"]
    assert d["lovable"]["hoola"] == 1 and d["lovable"]["duels"] == 1
    src = (PC.Path(PC.__file__).resolve().parents[1] / "site" / "arena.py").read_text()
    assert "RH.is_react(r)" in src.split("def _home_shots")[1][:600] and "PC.home_pair(d)" in src


# ---------------------------------------------------------------- 4. one brief on both engines, in the box
def test_one_brief_built_on_both_engines_and_photographed_the_same_way(ae_env, data, monkeypatch):  # noqa: F811
    _box()
    from app.site import ai as AI
    from app.site import architect as ARC
    from app.site import service as S
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))

    def build_now(tenant, ask, *a, **k):               # the Studio's plain build path (the fake model has no architect)
        v = S.new(tenant, ask, name="Sunrise Bakery", answers={"phone": "9876543210", "address": "Pune"})
        S.approve_plan(tenant, v["id"], pages=["contact"])
        r = S._load(v["id"])
        from app.site import prototype as PT
        if PT.react_on():                               # the new engine: the prototype of her pages, then her tap
            from tests.test_v0999_82_signin import _portal
            PT._write_version(r, _portal(), "test", "hoola")
            PT.approve(tenant, v["id"], PT.meta(S._load(v["id"]))["hash"])
        else:
            S.choose_look(tenant, v["id"], 0)
        return {"id": v["id"]}
    monkeypatch.setattr(ARC, "build_now", build_now)
    ask = {**PC.DC.pick(1)[0], "ask": "A website for Sunrise Bakery in Pune: breads, cakes, order online."}
    run_dir = PC._dir() / "proofcard-20261122-000000"
    run_dir.mkdir(parents=True, exist_ok=True)
    old = PC.run_one(ask, "old", run_dir, critic_on=False, limit_s=600)
    new = PC.run_one(ask, "new", run_dir, critic_on=False, limit_s=900)
    assert old["built"] and old["react"] is False, old.get("error")
    assert new["built"] and new["react"] is True, new.get("error")
    for r in (old, new):                                # the same pictures of both
        assert [s["what"] for s in r["shots"]][:3] == ["the home page on a computer, first screen",
                                                       "the home page on a computer, down the page in columns",
                                                       "the home page on a phone, down the page screen by screen"]
        assert all((run_dir / s["file"]).stat().st_size > 2000 for s in r["shots"])
    assert "Sunrise" in old["text"] and new["text"]


# ---------------------------------------------------------------- 5. the owner page in a real browser
def test_the_owner_page_shows_both_takes_her_pick_and_her_decision(arena_server, monkeypatch, tmp_path):  # noqa: F811
    from tests.test_chatkit_webstudio import _open
    from app.site import enginedefault as ED
    base, browser, key = arena_server
    _isolate(monkeypatch, tmp_path / "data")
    run, asks = _card(None)
    errors: list[str] = []
    ctx, pg = _open(browser, key, base + "/console/proofcard", errors)
    try:
        pg.locator('[data-decide="old"]').wait_for(timeout=30000)
        first = pg.locator(f'[data-pair="{asks[0]["id"]}"]')
        assert first.locator('[data-engine="old"]').count() == 1 and first.locator('[data-engine="new"]').count() == 1
        first.get_by_role("button", name="The new one").click()
        pg.get_by_text("You picked the new one 1").wait_for(timeout=15000)
        pg.get_by_role("button", name="Make the new engine the default for new websites").click()
        pg.locator('[data-decide="new"]').wait_for(timeout=15000)
        assert ED.new_default() is True
        pg.get_by_role("button", name="Back to the old engine").click()
        pg.locator('[data-decide="old"]').wait_for(timeout=15000)
        assert ED.new_default() is False
    finally:
        ctx.close()
        ED._CACHE["mtime"] = None
    assert not errors, errors
