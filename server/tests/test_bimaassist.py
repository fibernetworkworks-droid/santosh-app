"""Health-insurance Wave 2 (bima_assist): drafts and flags with a named decider; nothing decided, sent, filed or stored."""
import asyncio
import inspect

import pytest

from app.bimaassist import engines as E
from tests.test_life import conv_ctx


def test_plan_compare_and_material_facts():
    c = E.plan_compare([{"name": "A", "premium": 12000, "sum_insured": 500000, "copay_pct": 10}, {"name": "B", "premium": 15000, "sum_insured": 1000000, "copay_pct": 0}])
    rows = {r["attribute"]: r["better_on_paper"] for r in c["table"]}
    assert rows == {"premium": "A", "sum_insured": "B", "copay_pct": "B"} and "recommend" in c["note"].lower()
    with pytest.raises(ValueError):
        E.plan_compare([{"name": "A"}])
    m = E.material_facts([{"q": "Any pre-existing disease?", "answer": "No"}, {"q": "Address?", "answer": "x"}], "On metformin for diabetes since 2019")
    assert m["flags"] and m["flags"][0]["history_mentions"] == ["diabetes"] and "never answer" in m["note"].lower()
    assert E.material_facts([{"q": "Any ailment?", "answer": "no"}], "fit and healthy")["flags"] == []


def test_proposal_and_coverage():
    p = E.proposal_check({"name": "R", "dob": "1990-01-01", "age": 50})
    assert "nominee" in p["missing"] and p["contradictions"] and not p["declaration_signed"]
    pol = {"start": "2026-06-01", "initial_waiting_days": 30, "ped_waiting_months": 36, "specific_waiting": {"cataract": 24}, "sublimits": {"cataract": 40000},
           "room_rent_cap": 5000, "copay_pct": 10, "clauses": {"room_rent": "Cl 4.2: room rent up to 1% of SI"}}
    c = E.coverage_check(pol, {"admission": "2026-11-01", "diagnosis": "Cataract left eye", "amount": 60000, "is_ped": True, "room_charged": 8000})
    f = {x["check"]: x for x in c["findings"]}
    assert f["specific_waiting:cataract"]["status"] == "fails" and f["ped_waiting"]["status"] == "fails" and f["sublimit:cataract"]["status"] == "limits"
    assert f["room_rent"]["clause"].startswith("Cl 4.2") and "not given" in f["copay"]["clause"] and f["initial_waiting"]["status"] == "ok"
    mor = E.coverage_check({**pol, "moratorium_months": 5}, {"admission": "2026-11-01", "diagnosis": "x", "is_ped": True})
    assert any(x["check"] == "moratorium" for x in mor["findings"])


def test_preauth_query_timeline():
    r = E.preauth_checks({"start": "2026-01-01", "end": "2026-12-31"}, {"procedure": "Appendectomy", "estimate": 90000, "admission": "2026-11-02", "diagnosis": "appendicitis"}, {"appendectomy": 75000})
    res = {c["check"]: c["result"] for c in r["checks"]}
    assert res["policy in force on admission"] == "pass" and res["estimate vs package rate"] == "flag" and r["decider"].startswith("medical officer")
    assert E.preauth_checks({}, {"procedure": "x", "estimate": 1, "admission": "2026-11-02"})["checks"][0]["result"] == "unknown"
    q = E.query_reply(["Please send the ECG report", "Reason for ICU stay"], {"ECG": "normal sinus, 2026-11-02"})
    assert q["unanswered"] == ["Reason for ICU stay"]
    t = E.medical_timeline([{"date": "2026-11-05", "type": "discharge", "text": "d"}, {"date": "2026-11-01", "type": "admission", "text": "a"}, {"date": "2026-11-02", "type": "diagnosis", "text": "appendicitis"}],
                           2, {"appendicitis": ["appendectomy"]})
    assert t["timeline"][0]["date"] == "2026-11-01" and any("days between" in x for x in t["flags"]) and any("expected procedures" in x for x in t["flags"])


def test_letters_need_clause_and_never_send():
    with pytest.raises(ValueError):
        E.rejection_letter("C1", [{"reason": "PED not disclosed"}])
    l = E.rejection_letter("C1", [{"reason": "Waiting period", "clause_ref": "4.1", "clause_text": "24 months for cataract"}], ["claim form"])
    assert "4.1" in l["letter"] and "[name and designation" in l["letter"] and l["send"] is False
    g = E.grievance_reply("Claim short paid", ["paid 40000 of 60000"], "Cl 5")
    assert g["send"] is False and "40000" in g["letter"]


def test_ombudsman_wording_missell():
    o = E.ombudsman_packet(["policy copy", "claim form"], insurer_reply_on="2026-10-20", today="2026-11-05")
    assert "rejection / repudiation letter" in o["missing"] and o["days_left"] == 349 and o["verify"]
    w = E.wording_review("The company may, at its sole discretion, decide reasonable charges. Expenses for subrogation are not covered under any circumstance whatsoever in this policy.")
    assert "subrogation" in w["jargon"] and "sole discretion" in w["vague_terms"] and w["exclusion_sentences"]
    m = E.missell_review([{"id": 1, "text": "this is guaranteed, no medical needed"}, {"id": 2, "text": "hello"}], [{"id": "P", "issued": "2026-10-30", "proposal_dob": "1990-01-01", "id_dob": "1991-01-01"}], "2026-11-05")
    assert [h["call"] for h in m["phrase_hits"]] == [1] and m["free_look"][0]["free_look_days_left"] == 9 and m["discrepancies"]


def test_fhir_codemap_purity_and_wiring(env):
    f = E.fhir_claim({"id": "C1", "patient_id": "p", "insurer_id": "i", "provider_id": "h", "diagnosis_code": "K35", "total": 100, "service_date": "2026-11-02",
                      "items": [{"code": "x", "name": "bed", "amount": 60}, {"code": "y", "amount": 40}]})
    assert f["resource"]["resourceType"] == "Claim" and f["total_matches_items"] and f["submitted"] is False
    with pytest.raises(ValueError):
        E.fhir_claim({"id": 1})
    c = E.code_map(["A", "B", "C"], {"A": "P1", "B": ["P2", "P3"]})
    assert c["unmapped"] == ["C"] and c["ambiguous"] == ["B"]
    with pytest.raises(ValueError):
        E.code_map(["A"], {})
    src = inspect.getsource(E)
    for w in ("session(", "open(", "sqlite", "requests", "httpx"):
        assert w not in src
    from app.agent import tools as T
    assert "bima_assist" in T.HANDLERS
    from app.employee.hire import CATALOG
    assert CATALOG["bima_assist"]["group"] == "Health Insurance"
    from app import voice
    assert "bima_assist" in voice.VOICE_VIA_KAAM
    from app.agent.bimaassist_tools import _bima_assist
    from app.agent.tools import ToolError
    ctx = conv_ctx()
    assert asyncio.run(_bima_assist(ctx, "wording_review", text="x" * 40 + " reasonable"))["vague_terms"] == ["reasonable"]
    ctx.actor = "customer:1"
    with pytest.raises(ToolError):
        asyncio.run(_bima_assist(ctx, "rejection_letter", claim_id="1", reasons=[]))
