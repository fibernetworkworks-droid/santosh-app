"""v0.999.39 PROOF (P12 of docs/HOOLA_PROMPTING_PLAN.md): the P0 card again with Hoola's OWN brief as a third arm, the
sections the live card cannot run listed with their code checks, and up to ten users' four numbers first half vs second
half (numbered, never named). No real model or engine runs here."""
import asyncio
import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[2]
CON = REPO / "server" / "app" / "static" / "console"
KEY = "test-key-proof"
H = {"Authorization": f"Bearer {KEY}"}


@pytest.fixture
def pp(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.prompting import brief as B
    from app.prompting import context as C
    from app.quality import promptproof as PP
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    monkeypatch.setattr(B, "ASK", [lambda s, p: {}])
    yield PP
    get_settings.cache_clear()


def test_free_proof_hoola_against_raw_and_hand(pp):
    f = pp.free_proof()
    assert set(f["sections"]) == {"web", "script"} and f["errors"] == 0
    for d in f["sections"].values():
        assert d["asks"] == 20 and d["invented"] == 0 and d["magic"] == 0
        assert d["raw"] <= d["hoola"] <= d["hand"]                           # her words are never lost
    nc = {n["section"]: n for n in f["not_covered"]}
    assert set(nc) == {"app", "video", "music", "marketing", "doc", "code", "research", "data", "aiapp", "chat"}
    assert all(n["recipes_ok"] == n["recipes"] for n in nc.values())


def test_users_table_first_half_against_second(pp):
    from app.db import now, session
    from app.prompting import ledger as L
    L.ensure_table()
    with session() as s:
        for u in range(12):
            for i in range(12 if u < 11 else 6):                             # user 11 has too few judged runs
                kept = i >= 6 if u % 2 == 0 else i < 6                       # even users improve, odd users drop
                s.add(L.PromptRun(id=f"prn_p{u}_{i}", tenant_id=f"tenant_{u}", section="image", grade="kept" if kept else "redone",
                                  status="settled", handed_at=now() - timedelta(days=30 - i)))
        s.add(L.PromptRun(id="prn_card", tenant_id="__promptcard__", section="image", grade="kept", status="settled",
                          handed_at=now() - timedelta(days=1)))
    t = pp.users_table()
    assert t["have"] == 11 and len(t["users"]) == 10 and t["want"] == 10
    assert [x["user"] for x in t["users"]] == [f"User {n}" for n in range(1, 11)]
    blob = json.dumps(t)
    assert "tenant_" not in blob and "__promptcard__" not in blob             # numbered, never named
    rates = [(x["before"]["kept_rate"], x["after"]["kept_rate"]) for x in t["users"]]
    assert (0, 100) in rates and (100, 0) in rates
    assert "not 'life before Hoola'" in t["note"]


def test_live_proof_adds_hoolas_arm(pp, monkeypatch):
    from app.quality import promptcard as PC
    from app.quality.prompt_asks import ASKS

    async def fake_arm(ask, arm):
        return {"score": 40.0 if arm == "raw" else 80.0, "inr": 1.0}

    async def fake_hoola(ask):
        return {"score": 70.0, "inr": 1.5}
    monkeypatch.setattr(PC, "_arm", fake_arm)
    monkeypatch.setattr(pp, "_run_hoola", fake_hoola)
    with pytest.raises(ValueError, match="budget"):
        asyncio.run(pp.live_proof(ASKS[:3]))
    card = asyncio.run(pp.live_proof(PC.pick(limit=2), budget_inr=200))
    for s in ("web", "image", "script"):
        d = card["sections"][s]
        assert d["pairs"] == 2 and d["hand_gain"] == 40.0 and d["hoola_gain"] == 30.0 and d["share_of_ceiling"] == 0.75
        assert d["hoola_wins"] == 2
    assert card["inr"] == 6 * 3.5
    small = asyncio.run(pp.live_proof(PC.pick(limit=2), budget_inr=80))      # the ceiling stops new rows before they start
    assert small["stopped"].startswith("budget") and sum(d.get("pairs", 0) for d in small["sections"].values()) < 6
    assert any("% of the ceiling" in x for x in pp.lines(card))


def test_proof_route_owner_only(pp, monkeypatch):
    import app.main as M
    c = TestClient(M.app)
    r = c.get("/api/prompting/proof", headers=H).json()
    assert r["kind"] == "proof" and r["free"]["sections"]["web"]["asks"] == 20 and r["lines"][0].startswith("Prompt PROOF")
    monkeypatch.setattr(M, "_resolve_tenant", lambda req: "someone_else")
    assert c.get("/api/prompting/proof", headers=H).status_code == 403


def test_wiring():
    js = (CON / "prompting.js").read_text()
    assert "/api/prompting/proof" in js and "hpProof" in js
    ops = (REPO / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "prompt_proof)" in ops and "--budget-inr 300" in ops
    cli = (REPO / "server" / "app" / "quality" / "__main__.py").read_text()
    assert 'argv[0] == "proof"' in cli
