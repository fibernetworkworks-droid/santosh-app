"""v0.307 HOOLA DESIGN ARENA: a fixed, seeded set of 1,000 Indian business briefs; a run builds n of them end to end as
the hidden __arena__ tenant and scores each (independent judge, checks, originality, rupees, minutes); runs compare
metric by metric the right way round; blind duels against another builder's site keep Hoola's side hidden from the
judge; owner only; only public addresses are ever screenshotted."""
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_v121_site import site_env  # noqa: F401  (fixture)


def test_brief_set_is_fixed_and_spread():
    from app.site import arena as A
    s1, s2 = A.brief_set(), A.brief_set()
    assert len(s1) == 1000 and s1 == s2 and len({b["id"] for b in s1}) == 1000
    assert all(b["id"].startswith(f"s{A.SET_V}-") and b["facts"]["phone"].startswith("9") for b in s1)
    p = A.pick(12, 1)
    assert p == A.pick(12, 1) and p != A.pick(12, 2)
    assert len({b["industry"] for b in p}) == 12                          # one per industry before any repeats


def test_summary_and_compare_read_the_right_way_round():
    from app.site import arena as A
    cards = [{"status": "ready", "blocking": 0, "performance": 90, "lcp_ms": 1800, "inr": 120, "sameness": 1.0,
              "judge": {"overall": 7.0, "scores": {c: 7.0 for c in A.CRITERIA}}},
             {"status": "ready", "blocking": 2, "performance": 70, "lcp_ms": 2600, "inr": 180, "sameness": 3.0,
              "judge": {"overall": 8.0, "scores": {c: 8.0 for c in A.CRITERIA}}}]
    s = A.summarize(cards)
    assert s["judge"] == 7.5 and s["no_blocking_pct"] == 50.0 and s["inr"] == 150 and s["total_inr"] == 300
    new = {**s, "judge": 8.1, "lcp_ms": 2000, "inr": 170, "sameness": 1.5}
    c = A.compare(s, new)["metrics"]
    assert c["judge"]["verdict"] == "behtar" and c["lcp_ms"]["verdict"] == "behtar"          # lower LCP = better
    assert c["inr"]["verdict"] == "bura" and c["sameness"]["verdict"] == "behtar"
    assert "judge 7.5/10" in A.report_text(s)
    assert A.clean_scores({"scores": {"typography": 12, "trust": "x"}})["scores"] == {"typography": 10.0}


def test_a_run_builds_real_sites_scores_them_and_respects_the_budget(site_env, monkeypatch):
    from app.db import session
    from app.site import arena as A
    from app.site import service as S
    A.ensure_tables()
    monkeypatch.setattr(A, "judge", lambda imgs: {"scores": {c: 7.5 for c in A.CRITERIA}, "overall": 7.5, "best": "", "worst": ""})
    with session() as s:
        run = A.ArenaRun(version="t", seed=3, n=2, budget_inr=1000)
        s.add(run)
        s.flush()
        rid = run.id
    A._go(rid)                                           # the real builder: new -> plan -> looks -> look 0 -> build
    cards = A.items(rid)
    assert len(cards) == 2 and all(c["status"] == "ready" and c["site"] for c in cards)
    assert all(S._load(c["site"]).tenant_id == A.TENANT for c in cards)          # never her sites
    assert all(isinstance(c["blocking"], int) and c["judge"]["overall"] == 7.5 for c in cards)
    run = next(x for x in A.runs() if x["run"] == rid)
    assert run["status"] == "done" and run["summary"]["sites"] == 2 and run["summary"]["judge"] == 7.5
    # the budget stops a run between sites
    calls = []
    monkeypatch.setattr(A, "build_one", lambda b: calls.append(b["id"]) or (cards[0]["site"], 50.0, 1.0))
    with session() as s:
        r2 = A.ArenaRun(version="t", seed=4, n=5, budget_inr=40)
        s.add(r2)
        s.flush()
        rid2 = r2.id
    A._go(rid2)
    assert len(calls) == 1 and next(x for x in A.runs() if x["run"] == rid2)["status"] == "stopped"


def test_blind_duel_hides_hoola_and_counts_per_rival(site_env, monkeypatch):
    from app.db import session
    from app.site import arena as A
    A.ensure_tables()
    monkeypatch.setattr(A, "_home_shots", lambda site: [b"hoola-phone", b"hoola-desk"])
    seen = []

    def judge_fn(a, b):
        seen.append((a[0], b[0]))
        return {"a": {"scores": {"trust": 8}, "overall": 8}, "b": {"scores": {"trust": 6}, "overall": 6}, "winner": "a", "why": "A clearer"}
    r1 = A.duel("s1-bakery", "lovable", "https://example.com", "site_x", seed=1,
                shots=lambda u: [b"rival-phone", b"rival-desk"], judge_fn=judge_fn)
    r2 = A.duel("s1-bakery", "lovable", "https://example.com", "site_x", seed=2,
                shots=lambda u: [b"rival-phone", b"rival-desk"], judge_fn=judge_fn)
    for (a, _b), r in zip(seen, (r1, r2)):
        assert r["winner"] == ("hoola" if a == b"hoola-phone" else "rival")              # the side, not the name, won
    assert {r1["hoola_was"], r2["hoola_was"]} == {"a", "b"}                            # Hoola is not always A
    t = A.duel_table()["lovable"]
    assert t["duels"] == 2 and t["hoola"] + t["rival"] == 2
    from app import web as WB
    with pytest.raises(Exception):
        WB._check_url("http://127.0.0.1:8077/healthz")                                 # never a private address
    with pytest.raises(ValueError):
        A.duel("no-such-brief", "lovable", "https://example.com")


def test_api_is_owner_only(site_env, monkeypatch):
    from app.main import app, current_tenant
    c = TestClient(app)
    b = c.get("/api/arena/briefs?n=3&seed=1").json()
    assert b["total"] == 1000 and len(b["briefs"]) == 3
    assert "runs" in c.get("/api/arena/runs").json()
    app.dependency_overrides[current_tenant] = lambda: "someone-else"      # another Hoola user
    try:
        assert c.get("/api/arena/runs").status_code == 403
        assert c.post("/api/arena/start", json={"n": 1}).status_code == 403
    finally:
        app.dependency_overrides.pop(current_tenant, None)


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.314.0"
    assert "0.314.0+354" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
    assert json  # noqa
