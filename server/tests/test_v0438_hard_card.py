"""v0.438 SOCH KE JAWAB step 7 - the HARD CARD (owner: "GO STEP 7").

28 hard asks with known right answers (13 money maths, 6 word problems / logic, 2 proofs, 5 rules / decisions /
diagnosis / plans, 2 research), the key computed in Python (re-derived here so a wrong key can never pass a wrong
answer). free_card pins that every ask is spotted, gets pylab and its own recipe line; live_card runs the REAL turn on
tenant __quality__ and scores it in code (numbers within tolerance, read the Indian way; must-have points; pylab for a
calculation; 2+ source links for research; did the self-check run); optional Opus judge for the open asks.
"""
import asyncio
import math

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, txt  # noqa: F401


def _item(i):
    from app.quality import hard_card as H
    return next(a for a in H.SET if a["id"] == i)


# ---------------------------------------------------------------- the set and its key
def test_the_set_is_whole():
    from app.quality import hard_card as H
    ids = [a["id"] for a in H.SET]
    assert len(ids) == len(set(ids)) == 28
    kinds = {a["kind"] for a in H.SET}
    assert {"calc", "proof", "rules", "decision", "diagnosis", "plan", "research"} <= kinds
    assert all(a["expect"] for a in H.SET) and 8 <= len(H.QUICK) <= 12
    for a in H.SET:
        for e in a["expect"]:
            assert ("num" in e and e["num"]) or ("any" in e and e["any"]), a["id"]


def test_the_answer_key_is_right():
    P, r, n = 2_000_000, 0.09 / 12, 240
    emi = P * r * (1 + r) ** n / ((1 + r) ** n - 1)
    keys = {
        "emi": [emi, emi * n - P],
        "breakeven": [80000 / (450 - 260)],
        "cagr": [((95 / 40) ** 0.25 - 1) * 100],
        "doubling": [math.log(2) / math.log(1.15)],
        "fd_quarterly": [500000 * 1.02 ** 20],
        "gst_add": [4500 * 1.18, 4500 * 0.18],
        "real_return": [(1.07 / 1.06 - 1) * 100],
        "discounts": [(1 - 0.8 * 0.9) * 100],
        "price_volume": [((110 - 82) * 94 / (18 * 100) - 1) * 100],
        "dice": [(1 - (5 / 6) ** 4) * 100],
        "unit_econ": [120 - 70 - 15, (120 - 70 - 15) * 300],
        "workers": [3 * 12 / 4],
        "trains": [300 / (60 + 40)],
    }
    from app.quality import hard_card as H
    for i, vals in keys.items():
        nums = [e for e in _item(i)["expect"] if "num" in e]
        for v, want in zip(vals, nums):
            assert H._num_ok(want, [v]), (i, v, want)


# ---------------------------------------------------------------- reading answers
@pytest.mark.parametrize("text,want", [
    ("EMI **₹17,994.52** mahina", [17994.52]), ("kul byaaj ₹23.19 lakh", [2319000.0]),
    ("limit 1.5 crore hai", [15000000.0]), ("x = -12", [-12.0]), ("probability 51.77%", [51.77]),
    ("Rs 5,310 total, GST 810", [5310.0, 810.0]), ("about 10k a day", [10000.0]),
])
def test_numbers_are_read_the_indian_way(text, want):
    from app.quality import hard_card as H
    assert H.numbers(text) == want


def test_scoring_right_wrong_and_behaviour():
    from app.quality import hard_card as H
    ok = H.score_answer(_item("emi"), "EMI ₹17,994.52 hogi, kul byaaj ₹23,18,684.59.", ["pylab", "jaanch"])
    assert ok["right"] and ok["behaviour_ok"] and ok["checked"]
    bad = H.score_answer(_item("emi"), "EMI lagbhag 18,500 hogi.", [])
    assert not bad["right"] and bad["behaviour"] == ["pylab not used"] and len(bad["misses"]) == 2
    proof = H.score_answer(_item("root2"), "Maan lo √2 = p/q lowest terms mein... p even, q even - contradiction.", [])
    assert proof["right"] and proof["behaviour_ok"]                   # a proof needs no pylab
    res = H.score_answer(_item("research_cpi"), "CPI 3.1% (MoSPI) https://mospi.gov.in/a https://rbi.org.in/b", [])
    assert res["right"] and res["behaviour_ok"] and res["links"] == 2
    thin = H.score_answer(_item("research_cpi"), "CPI 3.1% as per MoSPI.", [])
    assert thin["right"] and thin["behaviour"] == ["0 source link(s)"]


# ---------------------------------------------------------------- the free card
def test_free_card_every_ask_is_spotted_with_pylab_and_its_recipe_line():
    from app.quality import hard_card as H
    c = H.free_card()
    assert (c["hard"], c["pylab"], c["kind_lines"]) == (28, 28, 28)
    assert c["research_ok"] == c["research_asks"] == 2
    assert H.lines(c)[0].startswith("Hard card (free, set v1): spotted hard 28/28")


# ---------------------------------------------------------------- the live card (scripted brain)
def test_live_card_scores_real_turns(gz, monkeypatch):  # noqa: F811
    from app.config import get_settings
    from app.quality import hard_card as H
    monkeypatch.setattr(get_settings(), "draft_check", False)
    _set_brain(monkeypatch, FakeBrain([
        ([txt("EMI **₹17,994.52** mahina hogi; 20 saal mein kul byaaj ₹23,18,684.59.")], "end_turn"),
        ([txt("Kul discount 30% hua.")], "end_turn"),
    ]))
    card = asyncio.run(H.live_card([_item("emi"), _item("discounts")], tenant="default"))
    rows = {r["id"]: r for r in card["rows"]}
    assert rows["emi"]["right"] and not rows["discounts"]["right"]
    assert card["right"] == 1 and card["calc_asks"] == 2 and card["pylab_used"] == 0 and card["errors"] == 0
    ln = H.lines(card)
    assert "RIGHT 1/2" in ln[0] and any("discounts: missed number 28" in x for x in ln)


def test_judge_only_for_open_asks(gz, monkeypatch):  # noqa: F811
    from app.config import get_settings
    from app.quality import hard_card as H
    monkeypatch.setattr(get_settings(), "draft_check", False)   # live, the self-check runs and draftcheck skips
    _set_brain(monkeypatch, FakeBrain([
        ([txt("Composition: 1.5 crore tak, 1% tax, ITC nahi milta. CA se confirm karein.")], "end_turn"),
        ([txt('{"score": 8, "why": "right limits"}')], "end_turn"),
    ]))
    card = asyncio.run(H.live_card([_item("gst_scheme")], judge=True, tenant="default"))
    assert card["rows"][0]["right"] and card["rows"][0]["judge"] == {"score": 8, "why": "right limits"}
    assert card["judge_avg"] == 8.0


def test_pick_and_save(env, monkeypatch, tmp_path):
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path / "q"))
    from app.quality import hard_card as H
    assert [a["id"] for a in H.pick(only="emi,cagr")] == ["emi", "cagr"]
    assert all(a.get("quick") for a in H.pick(quick=True)) and len(H.pick(limit=3)) == 3
    c = H.save(H.free_card(H.pick(limit=2)), "t")
    assert c["file"].startswith("hardcard-free-") and H.saved()[0]["file"] == c["file"]


def test_vps_ops_has_the_job():
    from pathlib import Path
    wf = (Path(__file__).resolve().parents[2] / ".github/workflows/vps-ops.yml").read_text()
    assert "          - hard_card\n" in wf and "app.quality hardcard --live --quick" in wf


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.808.0"
