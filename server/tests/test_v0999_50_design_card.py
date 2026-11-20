"""v0.999.50 D0 DESIGN CARD (docs/WEB_DESIGN_ENGINE_PLAN.md phase D0, owner: "GO D0"): today's Web Studio websites
measured the same way every run - 40 briefs (20 business + 20 not) through the Studio's own Build path, scored in code,
the design judged by a critic of another company from screenshots, her Good / OK / Bad on the owner page.
No model and no site build here: the runner, the critic and the clock are fakes; the live card is a VPS job."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v121_site import site_env  # noqa: F401  (fixture)

from app.quality import designcard as DC
from app.quality.design_asks import ASKS

ROOT = Path(__file__).resolve().parents[1] / "app"


@pytest.fixture
def qdir(tmp_path, monkeypatch):
    monkeypatch.setattr(DC, "_dir", lambda: tmp_path)
    return tmp_path


def test_the_40_briefs():
    from app.site import architect as AR
    assert len(ASKS) == 40 and DC.set_problems() == []
    assert sum(a["group"] == "business" for a in ASKS) == 20 and sum(a["group"] == "other" for a in ASKS) == 20
    others = [a for a in ASKS if a["group"] == "other"]
    assert all("business" not in a["purpose"] and "" not in a["purpose"] for a in others)   # O1: never a business plan
    assert all(p in AR.PURPOSES for a in ASKS for p in a["purpose"] if p)
    kinds = {p for a in others for p in a["purpose"]}
    assert {"personal", "event", "creator", "community", "education", "tool", "game", "product", "ai_app"} <= kinds
    bad = [dict(ASKS[0]), dict(ASKS[0])]
    assert any("duplicate" in p for p in DC.set_problems(bad))


def test_business_and_other_take_turns():
    order = DC.pick()
    assert [a["group"] for a in order[:4]] == ["business", "other", "business", "other"] and len(order) == 40
    assert [a["id"] for a in DC.pick(4)] == ["b01", "o01", "b02", "o02"]
    assert [a["id"] for a in DC.pick(group="other")][:2] == ["o01", "o02"]


def test_calibration_every_planted_case_behaves():
    cal = DC.calibration()
    assert cal and all(c["ok"] for c in cal), [c for c in cal if not c["ok"]]
    card = DC.free_card()
    assert card["verdict"] == "PASS" and card["critic"]["critic"]


def test_the_critic_reader_never_guesses():
    good = json.dumps({"scores": {k: 7 for k in DC.CRITERIA}, "looks_ai_made": False, "problems": ["a", "b", "c", "d"]})
    got = DC.parse_critic("Sure:\n" + good, photos_off=True)
    assert got["design"] == 7.0 and len(got["problems"]) == 3 and got["ai_made"] is False
    for raw in ("no json at all", json.dumps({"scores": {k: 0 for k in DC.CRITERIA}}), json.dumps({"scores": "great"}), "{bad json"):
        with pytest.raises(DC.CriticError):
            DC.parse_critic(raw)


def test_critic_call_goes_past_the_doors_and_a_failure_is_no_score(monkeypatch):
    monkeypatch.setattr(DC, "_spent", lambda: 0.0)
    seen = {}

    async def fake(ask, purpose, images, photos_off):
        from app import glmdoor
        from app import usage as U
        seen["claude_only"], seen["bypass"] = glmdoor.CLAUDE_ONLY.get(), U.ONE_MODEL_BYPASS.get()
        return json.dumps({"scores": {k: 6 for k in DC.CRITERIA}, "problems": ["the hero is flat"]})
    ask = ASKS[0]
    imgs = [("home", b"x")]
    assert DC.critic(ask, "business", [], call=fake)["error"]                    # no screenshots = no score
    got = DC.critic(ask, "business", imgs, call=fake)
    assert got["design"] == 6.0 and got["problems"] == ["the hero is flat"]
    src = (ROOT / "quality" / "designcard.py").read_text()
    assert "glmdoor.CLAUDE_ONLY.set(True)" in src and "U.ONE_MODEL_BYPASS.set(True)" in src   # the real call pins Claude

    async def broken(*a):
        return "it looks nice"
    bad = DC.critic(ask, "business", imgs, call=broken)
    assert bad.get("error") and "design" not in bad


def test_screenshots_for_the_critic(tmp_path):
    from PIL import Image
    shots = tmp_path / "live"
    shots.mkdir()
    Image.new("RGB", (1440, 900), "white").save(shots / "home-1440.jpg")
    Image.new("RGB", (390, 3000), "white").save(shots / "home-390-full.jpg")
    Image.new("RGB", (1440, 900), "white").save(shots / "about-1440.jpg")
    Image.new("RGB", (1440, 900), "white").save(shots / "rsvp-1440.jpg")
    imgs = DC.screenshots(shots, ["home", "about", "rsvp", "gallery"])
    assert [n for n, _ in imgs][0].startswith("home on a computer") and len(imgs) == 4
    strip = DC.phone_strip(shots / "home-390-full.jpg")
    assert strip.size == (4 * 390 + 3 * 16, 844)                                  # 4 phone screens side by side
    import io
    assert max(Image.open(io.BytesIO(imgs[1][1])).size) <= DC.IMG_EDGE


def test_drive_taps_build_on_the_ready_prototype_once(monkeypatch):
    from app.site import prototype as PT
    from app.site import service as S

    class R:
        status, looks = "prototype", "[]"
    state = {"r": R(), "taps": []}
    monkeypatch.setattr(S, "_load", lambda sid: state["r"])
    monkeypatch.setattr(S, "busy", lambda sid: False)
    monkeypatch.setattr(PT, "meta", lambda r: {"status": "ready", "hash": "h1"})

    def approve(tenant, sid, h):
        state["taps"].append((tenant, sid, h))
        state["r"].status = "ready"
    monkeypatch.setattr(PT, "approve", approve)
    assert DC._drive("s1", limit_s=5, sleep_s=0) == "ready"
    assert state["taps"] == [(DC.TENANT, "s1", "h1")]


def test_live_card_budget_photos_and_save(qdir, monkeypatch):
    from app.config import get_settings
    st = get_settings()
    before = st.site_ai_photos
    spent = {"v": 0.0}
    monkeypatch.setattr(DC, "_spent", lambda: spent["v"])
    seen = []

    def runner(a):
        seen.append((a["id"], get_settings().site_ai_photos))
        spent["v"] += 60.0
        return {"built": True, "seconds": 300, "inr": 60.0, "purpose": a["purpose"][0], "text": " ".join(a["must"]),
                "critic": {"scores": {k: 6 for k in DC.CRITERIA}, "design": 6.0, "inr": 2.0}}
    card = DC.live_card(DC.pick(4), budget_inr=100, runner=runner, label="t")
    assert [i for i, _ in seen] == ["b01", "o01"] and all(p == 0 for _, p in seen)   # photos off while it runs
    assert get_settings().site_ai_photos == before                                    # and back after
    assert card["ran"] == 2 and card["planned"] == 4 and card["all"]["design"] == 6.0 and not card["running"]
    assert sum(1 for r in card["rows"] if r["skipped"]) == 2
    saved = json.loads(Path(card["file"]).read_text())
    assert saved["set"] == "d0-1" and saved["running"] is False
    with pytest.raises(ValueError):
        DC.live_card(DC.pick(1), budget_inr=0, runner=runner)


def test_her_verdict_outranks_and_shots_are_fenced(qdir, monkeypatch):
    monkeypatch.setattr(DC, "_spent", lambda: 0.0)
    card = DC.live_card(DC.pick(2), budget_inr=50, runner=lambda a: {"built": True, "purpose": a["purpose"][0],
                                                                       "text": " ".join(a["must"]), "seconds": 60, "inr": 1})
    run = card["run"]
    DC.set_verdict(run, "b01", "good", "clean")
    DC.set_verdict(run, "o01", "bad")
    got = DC.load()
    assert got["all"]["her_good"] == 1 and got["all"]["her_bad"] == 1 and got["verdicts"]["b01"]["note"] == "clean"
    with pytest.raises(ValueError):
        DC.set_verdict(run, "b01", "great")
    with pytest.raises(ValueError):
        DC.set_verdict("../etc", "b01", "good")
    (qdir / run / "b01-1.jpg").write_bytes(b"jpg")
    assert DC.shot_path(run, "b01-1.jpg") is not None
    assert DC.shot_path(run, "../x.jpg") is None and DC.shot_path("../" + run, "b01-1.jpg") is None


def test_compare_the_right_way_round():
    a = {"set": "d0-1", "all": {"design": 5.5, "median_minutes": 12, "ai_made": 10}}
    b = {"set": "d0-1", "all": {"design": 6.5, "median_minutes": 14, "ai_made": 4}}
    v = {x["metric"]: x["verdict"] for x in DC.compare(a, b)}
    assert v == {"design": "better", "median_minutes": "worse", "ai_made": "better"}
    assert DC.compare(a, {**b, "set": "d1"})[0]["verdict"].startswith("different")


def test_owner_routes_and_page(site_env, qdir, monkeypatch):
    from app.main import app, current_tenant
    c = TestClient(app)
    d = c.get("/api/designcard").json()
    assert d["card"] is None and len(d["briefs"]) == 40 and d["critic"]["critic"]
    assert c.get("/api/designcard/shot/designcard-1/b01-1.jpg").status_code == 404
    assert c.post("/api/designcard/verdict", json={"run": "x", "id": "b01", "verdict": "good"}).status_code == 400
    page = c.get("/console/designcard")
    assert page.status_code == 200 and "designcard.js" in page.text and "Content-Security-Policy" in page.headers
    app.dependency_overrides[current_tenant] = lambda: "someone-else"
    try:
        assert c.get("/api/designcard").status_code == 403
        assert c.post("/api/designcard/verdict", json={}).status_code == 403
    finally:
        app.dependency_overrides.pop(current_tenant, None)


def test_the_server_restart_never_takes_over_a_card_site():
    src = (ROOT / "site" / "service.py").read_text()
    i = src.index("def recover_stuck")
    assert 'r.tenant_id == "__designcard__"' in src[i:i + 3000] and DC.TENANT == "__designcard__"


def test_wiring():
    main = (ROOT / "quality" / "__main__.py").read_text()
    assert 'argv[0] == "design"' in main and "_designcard" in main
    ops = (ROOT.parents[1] / ".github" / "workflows" / "vps-ops.yml").read_text()
    for job in ("design_card_check", "design_card_try", "design_card"):
        assert f"          - {job}\n" in ops and f"              {job})" in ops
    assert "--limit 4 --budget-inr 300" in ops and "nohup setsid .venv/bin/python -m app.quality design --live" in ops
    js = (ROOT / "static" / "console" / "designcard.js").read_text()
    assert "/api/designcard/verdict" in js and "innerHTML = '<h1>" in js and "eval(" not in js
