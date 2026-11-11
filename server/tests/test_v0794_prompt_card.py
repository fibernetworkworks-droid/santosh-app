"""v0.794 PROMPT NAAP (built as 0.785) (P0 of docs/HOOLA_PROMPTING_PLAN.md): the prompt card - her raw line vs a hand-filled brief,
through the real engines, scored the same way. These tests use NO model: the engines are replaced by fakes."""
import asyncio
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def pc(tmp_path, monkeypatch):
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path))
    from app.quality import promptcard as PC
    return PC


def test_the_set_is_60_valid_asks(pc):
    from app.quality.prompt_asks import ASKS, SECTIONS
    assert len(ASKS) == 60 and SECTIONS == ("web", "image", "script")
    for s in SECTIONS:
        sec = [a for a in ASKS if a["section"] == s]
        assert len(sec) == 20 and sum(a["lang"] == "hi" for a in sec) == 10
    assert pc.set_problems() == []
    for a in ASKS:                      # the brief is information, never magic words; no phone number anywhere
        low = a["brief"].lower()
        assert not any(m in low for m in pc.MAGIC), a["id"]
        assert not pc._PHONE.search(a["brief"]), a["id"]
        assert a["raw"].lower() in low or a["section"] == "image"       # her own words are kept in the brief


def test_free_card_is_ok_and_free(pc):
    card = pc.free_card()
    assert card["ok"] and card["calibration_ok"] == len(card["calibration"]) == 14
    assert card["engine_refusals"] == []            # no ask would be refused by the website / picture guards
    assert card["estimate"]["runs"] == {"web": 40, "image": 40, "script": 40}
    assert card["raw_already_says"] < 0.25          # the raw lines really are rough
    text = "\n".join(pc.lines(card))
    assert "ASSUMED" in text and "OK" in text


def test_scorer_reads_facts_and_inventions(pc):
    from app.quality.prompt_asks import ASKS
    ask = next(a for a in ASKS if a["id"] == "w03")
    plan = json.dumps({"pages": ["Services and prices", "Bridal packages", "Gallery", "Book appointment slot"],
                       "note": "haircut from Rs 350, bridal package ₹14,999, closed on Tuesday"})
    good = pc.score_text(ask, plan, ask["brief"], engine_ok=1.0)
    assert good["score"] == 100.0 and not good["invented"]
    bad = pc.score_text(ask, plan.replace("14,999", "12,999") + " call 9812345678, 20% off", ask["brief"], engine_ok=1.0)
    assert "14,999" in bad["facts_lost"]
    assert {"price 12999", "phone 9812345678", "percent 20"} <= set(bad["invented"])
    raw = pc.score_text(ask, json.dumps({"pages": ["Home", "About", "Services", "Contact"]}), ask["raw"], engine_ok=0.5)
    assert raw["score"] < 40 and "bridal" in raw["missed"]
    hi = next(a for a in ASKS if a["id"] == "s03")          # a Hinglish script may say the fact its own way
    assert pc.facts_kept("subah 5 baje se khula, pehla hafta free", hi["facts"]) == [True, True]


def test_an_engine_that_echoes_the_brief_gets_no_credit(pc, monkeypatch):
    """Found in the first dry run: the architect's plan carries HER words back (`words`), so the brief was scoring
    its own text. The echo is removed before scoring, and the web runner drops that field."""
    from app.quality.prompt_asks import ASKS
    from app.site import architect as A
    ask = next(a for a in ASKS if a["id"] == "w03")
    assert pc.score_text(ask, "PLAN\n" + ask["brief"], ask["brief"], engine_ok=1.0)["parts"]["must"] == 0.0
    same_plan = {"kind": "booking_site", "pages": [{"slug": "home", "title": "Home", "for": "public", "sections": ["hero", "cta", "faq"]}]}
    monkeypatch.setattr(A, "_ask", lambda *a, **k: dict(same_plan))
    scores = []
    for arm in ("raw", "brief"):
        text, depth = pc._web_plan(ask[arm])
        assert "WHAT IT IS" not in text
        scores.append(pc.score_text(ask, text, ask[arm], depth)["parts"]["must"])
    assert scores[0] == scores[1]           # the same plan = the same marks, whatever she typed


def test_decision_rule(pc):
    def pairs(r, b, n=10, her=None):
        return [{"raw": {"score": r}, "brief": {"score": b}, **({"her": her} if her else {})} for _ in range(n)]
    assert pc.decide(pairs(50, 75))["verdict"] == "BUILD"
    assert pc.decide(pairs(70, 72))["verdict"] == "DROP"
    assert pc.decide(pairs(60, 67))["verdict"] == "RETHINK"
    assert pc.decide(pairs(0, 100, n=7))["verdict"] == "NOT ENOUGH"
    her = pc.decide(pairs(50, 90, her="raw"))
    assert her["verdict"] == "DROP" and her["basis"] == "her"


def _fakes(pc, monkeypatch, cost_usd=0.01):
    """Engines that answer from the words they were given: the brief names more of what she wanted than the raw line."""
    from app import usage
    calls = []

    def _spend():
        acc = usage._RUN.get()
        if acc is not None:
            acc["usd"] += cost_usd
            acc["calls"] += 1

    async def text_engine(ask, arm):
        calls.append((ask["id"], arm))
        _spend()
        words = " ".join(a[0] for a in ask["must"]) if arm == "brief" else "home about contact"
        facts = " ".join(pc._alts(f)[0] for f in ask["facts"]) if arm == "brief" else ""
        filler = " word" * (ask.get("secs", 0) * 3)
        return {"text": f"{words} {facts}{filler}", "engine": 1.0 if arm == "brief" else 0.5, "given": ask[arm]}

    async def image_engine(ask, arm):
        calls.append((ask["id"], arm))
        _spend()
        n = len(ask["must"])
        return {"answers": [True] * n if arm == "brief" else [True] + [False] * (n - 1), "seen_text": "", "file": "x.png",
                "model": "fake", "flat_inr": 0.0, "given": ask[arm]}

    monkeypatch.setattr(pc, "RUNNERS", {"web": text_engine, "script": text_engine, "image": image_engine})
    monkeypatch.setattr(usage, "install", lambda: None)
    monkeypatch.setattr(usage, "usd_inr", lambda: 100.0)        # 0.01 usd a run = Rs 1 a run
    return calls


def test_live_card_pairs_every_ask_and_decides(pc, monkeypatch):
    calls = _fakes(pc, monkeypatch)
    card = asyncio.run(pc.live_card(pc.pick(limit=8), budget_inr=1000))
    assert card["asks"] == 24 and len(calls) == 48
    assert all(calls[i][0] == calls[i + 1][0] and (calls[i][1], calls[i + 1][1]) == ("raw", "brief")
               for i in range(0, len(calls), 2))                 # raw then brief, same ask
    assert [r["section"] for r in card["rows"][:3]] == ["web", "image", "script"]      # sections interleaved
    for s in ("web", "image", "script"):
        d = card["sections"][s]
        assert d["verdict"] == "BUILD" and d["pairs"] == 8 and d["gain"] > 10
        assert d["parts"]["brief"]["must"] == 1.0 and d["inr_per_run"] == 1.0
    assert card["inr"] == 48.0
    saved = pc.save(card, "t")
    assert pc.saved()[0]["file"] == saved["file"] and pc.saved()[0]["sections"]["web"]["verdict"] == "BUILD"
    text = "\n".join(pc.lines(card))
    assert "BUILD" in text and "filled BY HAND" in text


def test_budget_stops_with_equal_coverage(pc, monkeypatch):
    calls = _fakes(pc, monkeypatch, cost_usd=0.10)              # Rs 10 a run, Rs 20 a pair
    card = asyncio.run(pc.live_card(pc.pick(limit=5), budget_inr=130))
    assert card["inr"] <= 130 and card["stopped"].startswith("budget")
    assert len(calls) % 2 == 0                                   # never a raw run without its brief run
    assert card["sections"]["web"]["verdict"] == "NOT ENOUGH"    # too few pairs = no verdict, said so
    with pytest.raises(ValueError):
        asyncio.run(pc.live_card(pc.pick(limit=1), budget_inr=0))


def test_a_broken_engine_is_a_row_and_three_dead_pairs_stop(pc, monkeypatch):
    _fakes(pc, monkeypatch)

    async def dead(ask, arm):
        raise RuntimeError("engine down")
    monkeypatch.setattr(pc, "RUNNERS", {"web": dead, "script": dead, "image": dead})
    card = asyncio.run(pc.live_card(pc.pick(limit=4), budget_inr=500))
    assert card["asks"] == 3 and "three dead pairs" in card["stopped"]
    assert "ERROR engine down" in "\n".join(pc.lines(card))


def test_her_pick_outranks_the_checks(pc, monkeypatch):
    _fakes(pc, monkeypatch)
    card = asyncio.run(pc.live_card(pc.pick(limit=8, section="script"), budget_inr=500))
    assert card["sections"]["script"]["verdict"] == "BUILD"
    for a in pc.pick(limit=5, section="script"):
        pc.set_verdict(a["id"], "raw", "the raw one sounded more natural")
    again = pc.with_verdicts(card)
    assert again["sections"]["script"]["verdict"] == "DROP" and again["sections"]["script"]["basis"] == "her"
    with pytest.raises(ValueError):
        pc.set_verdict("s01", "maybe")
    with pytest.raises(ValueError):
        pc.set_verdict("nope", "raw")


def test_cli_and_route(pc, capsys):
    from app.quality.__main__ import main
    assert main(["prompt"]) == 0
    out = capsys.readouterr().out
    assert "Prompt card (free" in out and "saved: promptcard-free-" in out
    assert main(["prompt", "--live"]) == 2 and "--budget-inr" in capsys.readouterr().out
    assert main(["prompt", "verdict", "w01", "brief"]) == 0
    assert pc.verdicts()["w01"]["pick"] == "brief"
    assert main(["prompt", "--status"]) == 0
    src = (REPO / "server" / "app" / "quality" / "api.py").read_text()
    assert '@r.get("/prompt")' in src
    yml = (REPO / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert yml.count("prompt_card_check") == 2 and yml.count("prompt_card_try") == 2
    assert "--budget-inr 250" in yml                 # the VPS try can never run without a ceiling


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.802.0"
    assert "0.802.0+801" in (REPO / "pubspec.yaml").read_text()
