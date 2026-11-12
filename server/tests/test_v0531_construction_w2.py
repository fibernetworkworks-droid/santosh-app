"""v0.531.0 Construction Wave 2 - the file-builders and checkers (plan docs/CONSTRUCTION_EMPLOYEE_PLAN.md
§7 C7-C10; owner: 'Wave 2 - the file-builders and checkers: 9, 16, 28, 29, 35, 36, 37-39, 44-46, 52-56,
72, 73, 81, 93'). The register's Wave-2 home map, the tier-C edges on the new desks, the state pack's
RERA rows, the IS 1200 formula library with the bit-for-bit recompute law (C8), the QS desk (takeoff /
rates / BOQ / abstract / cost control / retention / PV), the approvals office (checklist from DATA, the
packet with the empty sign line, the statutory calendar) (C7), RERA & escrow (the % is the promoter's,
withdrawals need the certificate ref, reconcile cites the pack) (C9), contracts (variation approval is
the client's, claims carry the matrix + notice arithmetic, entitlement stays with counsel), tendering
(bid/no-bid is hers, every pack row sourced, vendor ratings hers), drawing QA (rules need clause +
source, verdict is arithmetic, review pack sign line empty), EHS permits & toolbox (#81), and the tool
layer (registry 566, dispatch end-to-end, VOICE_VIA_KAAM, Hub rows, version pins)."""
import asyncio
from datetime import date

import pytest

T = "default"
DAY = date(2026, 11, 5)


@pytest.fixture
def cst(env, monkeypatch):
    from app import config
    from app.construction import approvals as A
    from app.construction import common
    from app.construction import contracts as K
    from app.construction import drawqa as D
    from app.construction import quality as Q
    from app.construction import qs as QS
    from app.construction import rera as R
    from app.construction import tender as Td
    monkeypatch.setattr(common, "today", lambda t: DAY)
    for mod in (A, QS, R, K, Td, D, Q):
        monkeypatch.setattr(mod, "today", lambda t: DAY)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


# ---------------------------------------------------------------- C0 glue: register, homes, pack rows
def test_register_wave2_homes():
    from app.construction import register as R
    assert len(R.ROWS) == 123
    w2 = R.wave("2")
    assert len(w2) == 29 and {r["id"] for r in w2} == set(R.WAVE2_IDS)
    assert set(R.WAVE2_HOME) == set(R.WAVE2_IDS)
    # the member list the owner waved, every one homed
    for rid in (9, 16, 28, 29, 35, 36, 37, 38, 39, 44, 45, 46, 52, 53, 54, 55, 56, 72, 73, 81, 93):
        assert R.WAVE2_HOME[rid], rid
    assert R.WAVE2_HOME[37] == "const_qs (takeoff)" and R.WAVE2_HOME[93] == "const_rera (escrow)"
    assert R.get(33)["wave"] == "4"          # v0.586.0: shipped on the approvals desk (Wave 4)
    assert R.get(48)["wave"] == "4" and R.get(50)["wave"] == "4"   # v0.586.0: shipped (Wave 4)


def test_wave2_tier_c_edges():
    from app.construction import gates
    hits = {
        "file the building permission application on the MCGM portal": ("DSC", "licensee"),
        "certify the RERA percentage completion for Q4": ("promoter", "declaration"),
        "certify RERA escrow withdrawal": ("CA / architect / engineer",),
        "approve the change order for the extra work": ("client",),
        "decide the delay entitlement for the claim": ("advocate", "counsel"),
        "issue the variation notice to the client": ("advocate",),
        "give the permit-to-work for the excavation": ("safety officer",),
        "accept the concrete cubes from the pour": ("QA engineer",),
    }
    for ask, needles in hits.items():
        refusal = gates.tier_c_check(ask)
        assert refusal, ask
        for n in needles:
            assert n in refusal, (ask, n)
    # the desk's own work passes the gate: prepare, assemble, record
    for ask in ("assemble the oc packet checklist", "record the muster for today", "draft the variation paper",
                "add the bye-law rule with its clause"):
        assert gates.tier_c_check(ask) is None, ask


def test_statepack_rera_rows(cst):
    from app.construction import statepacks as SP
    pack = SP.load("maharashtra")
    assert not SP.stale(pack)
    assert SP.value(pack, "rera_escrow_pct") == 70.0
    assert SP.value(pack, "rera_ca_audit_months") == 6
    r = SP.row(pack, "rera_ca_audit_months")
    assert "s.4(2)(l)(D)" in r["source"] and r["checked_on"] and "six months" in r["clause"]
    assert len(pack["rows"]) == 7        # v0.555: rera_carpet_tolerance_pct joined the pack


# ---------------------------------------------------------------- C8: the IS 1200 library + the trail law
def test_is1200_library_trails():
    from app.construction import is1200 as M
    t = M.earthwork(10, 4, 2, lead_m=30, lift_m=1.5)
    assert t["qty"] == 80.0 and t["unit"] == "m3" and "Part 1" in t["is_ref"] and t["inputs"]["lead_m"] == 30
    t = M.concrete(10, 5, 0.2, openings_m2=0.05)
    assert t["qty"] == 10.0 and "<= 0.1 m2" in t["formula"]      # small openings never deducted
    t = M.concrete(10, 5, 0.2, openings_m2=0.5)
    assert t["qty"] == round(10.0 - 0.5 * 0.2, 3)
    t = M.brickwork(20, 3, 0.23, openings_m2=2.0)
    assert t["qty"] == round(20 * 3 * 0.23 - 2.0 * 0.23, 3)
    t = M.plaster(6, 3, openings_m2=2.0)                          # 0.5-3 m2: half deducted
    assert t["qty"] == 17.0 and "50%" in t["formula"]
    t = M.plaster(6, 3, openings_m2=0.4)
    assert t["qty"] == 18.0
    t = M.plaster(6, 3, openings_m2=4.0)
    assert t["qty"] == 14.0
    t = M.formwork(10, 3)
    assert t["qty"] == 30.0 and "Part 5" in t["is_ref"]
    t = M.steel_weight(12, 16, nos=4)
    assert t["qty"] == round(4 * 12 * 16 * 16 / 162.0, 3) and "Part 8" in t["is_ref"]
    for bad in (lambda: M.earthwork(0, 1, 1), lambda: M.concrete(-1, 1, 1)):
        with pytest.raises(ValueError):
            bad()
    with pytest.raises(ValueError) as ex:
        M.compute("painting", {"length": 1, "height": 1})
    assert "library mein nahi" in str(ex.value)                   # absent formula refuses, never improvises
    assert set(M.TRAIL_KEYS) == {"qty", "unit", "formula", "inputs", "is_ref"}


def test_is1200_recompute_bit_for_bit():
    from app.construction import is1200 as M
    t = M.brickwork(20, 3, 0.23, openings_m2=2.0)
    again = M.recompute({"kind": "brickwork", "inputs": t["inputs"]})
    assert again == t["qty"] and again is t["qty"] or again == t["qty"]   # the float is THE SAME value
    t2 = M.steel_weight(12.5, 8, nos=112)
    assert M.recompute({"kind": "steel", "inputs": t2["inputs"]}) == t2["qty"]
    b = M.bbs([{"shape": "straight", "dia": 12, "length": 8, "nos": 20},
               {"shape": "stirrup", "dia": 8, "length": 1.2, "nos": 60}])
    assert b["total_kg"] == round(20 * 8 * 144 / 162.0 + 60 * 1.2 * 64 / 162.0, 2)
    assert "Site engineer" in b["say"] or "site engineer" in b["say"]
    with pytest.raises(ValueError):
        M.bbs([])                                                  # khaali schedule draft nahi hota
    with pytest.raises(ValueError):
        M.bbs(["straight"])                                        # a bare string is not a bar


def test_qs_takeoff_rate_boq_abstract_trail(cst):
    from app.construction import qs as QS
    r = QS.takeoff(T, "Tower A", "Footing PCC M10", "concrete", {"length": 10, "breadth": 5, "depth": 0.2})
    assert r["qty"] == 10.0 and "billing engineer" in r["say"]
    tid = r["takeoff_id"]
    rc = QS.recompute(T, tid)
    assert rc["bit_for_bit"] and rc["stored"] == rc["recomputed"]
    with pytest.raises(Exception):
        QS.takeoff(T, "Tower A", "x", "painting", {"length": 1, "height": 1})
    rr = QS.rate_buildup(T, "PCC 1:4:8", "m3",
                         [{"head": "cement", "qty": 0.32, "unit": "bag", "rate": 380, "source": "quote Shivam"},
                          {"head": "aggregate", "qty": 0.9, "unit": "m3", "rate": 1400, "source": "SOR 2.4"}],
                         overhead_pct=10, profit_pct=8, source="SOR 2.4 + quote")
    assert rr["rate"] == round((0.32 * 380 + 0.9 * 1400) * 1.10 * 1.08, 2) == 1641.34
    with pytest.raises(Exception) as ex:
        QS.rate_buildup(T, "no source", "m3", [{"head": "cement", "qty": 1, "rate": 1}], source="")
    assert "SOURCE" in str(ex.value)
    QS.boq_add(T, "Tower A", "Footing PCC M10", "m3", qty=10, rate=rr["rate"], head="substructure",
               takeoff_id=tid, rate_id=rr["rate_id"])
    ab = QS.abstract(T, "Tower A")
    assert ab["lines"] == 1 and ab["by_head"]["substructure"] == round(10 * rr["rate"], 2)
    assert ab["total"] == ab["by_head"]["substructure"]
    b = QS.budget(T, "Tower A", "substructure", budget=100000, committed=60000, actual=110000)
    assert b["variance"] == -10000 and "OVER" in b["say"]
    d = QS.day(T, "Tower A")
    assert d["takeoffs"] == 1 and d["boq_lines"] == 1 and d["over_budget"] == 1


def test_retention_and_pv_are_working_papers(cst):
    from app.construction import qs as QS
    r = QS.retention(1000000, 5)
    assert r["held"] == 50000 and r["payable"] == 950000 and "DRAFT" in r["say"]
    with pytest.raises(Exception):
        QS.retention(1000, 0)                                     # her contract's % or nothing
    pv = QS.price_variation(500000, 70, 300, 330)
    assert pv["pv"] == round(500000 * 0.70 * 0.10, 2) and "DRAFT" in pv["say"]
    with pytest.raises(Exception):
        QS.price_variation(1000, 70, 0, 330)


# ---------------------------------------------------------------- C7: the approvals office
def test_approvals_file_checklist_packet_calendar(cst, env):
    from app.construction import approvals as A
    f = A.file_new(T, "Shivneri Heights", "MCGM", "building permission", licensee="Ar. Deshpande")
    assert f["checklist_items"] == len(A.STARTER["building_permission"])
    fid = f["file_id"]
    ch = A.checklist(T, file_id=fid)
    assert len(ch["items"]) == f["checklist_items"] and "MCGM" in ch["say"]
    st = A.checklist(T, purpose="fire noc")
    assert len(st["items"]) == len(A.STARTER["fire_noc"]) and "STARTER" in st["say"]
    A.doc_add(T, fid, "drawing", "Proposed plan L1-L8", ref="DWG-A01 rev 2")
    A.doc_needed(T, fid, "noc", "Fire NOC (awaiting)")
    A.check_mark(T, fid, "7-12", done=True)
    pk = A.packet(T, fid)
    assert pk["gaps"] and pk["file"]["name"].endswith(".pdf")
    assert "OWNER" in pk["say"] or "licensee" in pk["say"]
    assert "jama" not in pk["say"].lower() or "nahi" in pk["say"]   # filing stays the human's act
    m = A.file_mark(T, fid, "submitted", ref_no="BP/2026/4471", on="2026-11-05")
    assert m["status"] == "submitted"
    m = A.file_mark(T, fid, "approved", on="2027-01-10", valid_till="2029-01-10")
    assert "calendar" in m["say"]
    # #34 the approved file's validity landed on the statutory calendar
    cd = A.cal_due(T, days=1000)
    assert any("validity" in x["item"] for x in cd["soon"] + cd["late"])
    c = A.cal_add(T, "MahaRERA", "Quarterly progress update", due_on="2027-01-20")
    assert "compliance officer" in c["say"] or "haan" in c["say"]
    late = A.cal_add(T, "Fire", "old renewal", due_on="2026-10-01")
    cd = A.cal_due(T, days=30)
    assert cd["late"] and cd["late"][0]["late_by"] > 0
    A.cal_done(T, late["cal_id"], on="2026-11-05")
    assert not [x for x in A.cal_due(T, days=30)["late"] if x["item"] == "old renewal"]
    d = A.day(T)
    assert d["open_files"] == 0 and d["missing_papers"] >= 1    # approved file closed; its NOC still awaited


# ---------------------------------------------------------------- C9: RERA & escrow
def test_rera_project_update_forms_escrow(cst, env):
    from app.construction import rera as R
    p = R.project_reg(T, "Shivneri Heights", maha_rera="P51700049999", promoter="Shivneri Builders LLP",
                      start_on="2026-01-15", complete_on="2028-06-30", escrow_acct="HDFC 5010...")
    pid = p["rera_project_id"]
    u = R.update_draft(T, pid, "2026-Q4", pct_complete=34.0, units_booked=41, units_delivered=12)
    assert "34" in u["say"] and "nahi nikalta" in u["say"]         # her number, never computed
    fp = R.form_pack(T, pid, "Form 4", "engineer's completion certificate", period="phase 1",
                     data=[{"item": "floors done", "value": "8 of 12", "source": "site diary"}],
                     prepared_for="Er. Kulkarni")
    assert fp["rows"] == 1 and "khaali" in fp["say"]
    with pytest.raises(Exception) as ex:
        R.form_pack(T, pid, "Form 3", "quarterly", data=[{"item": "x", "value": "1", "source": "y"}], prepared_for="")
    assert "professional" in str(ex.value)
    with pytest.raises(Exception) as ex:
        R.form_pack(T, pid, "Form 3", "quarterly", data=[{"item": "x", "value": "1"}], prepared_for="CA Mehta")
    assert "source" in str(ex.value)
    R.escrow_in(T, pid, 5000000, day="2026-11-01", ref="UTR-99")
    with pytest.raises(Exception) as ex:
        R.escrow_withdraw(T, pid, 500000)                          # no certificate, no row
    assert "certificate" in str(ex.value)
    w = R.escrow_withdraw(T, pid, 500000, certificate_ref="CA-Mehta/2026/11")
    assert "certificate" in w["say"]
    rc = R.reconcile(T, pid)
    assert rc["receipts"] == 5000000 and rc["reserve"] == 3500000 and rc["withdrawn"] == 500000
    assert rc["headroom"] == 3000000 and "s.4(2)(l)(D)" in rc["source"]["source"]
    assert rc["audit_due"] == "2027-09-30"                         # FY end 2027-03-31 + 6 months (pack row)
    assert "QUARTERLY UPDATE" in rc["say"] or "audit" in rc["say"]
    d = R.day(T)
    assert d["projects"] == 1 and d["draft_updates"] == 1 and d["uncertified_withdrawals"] == 0


# ---------------------------------------------------------------- C10: contracts, tender, drawqa, EHS
def test_contracts_obligations_variations_claims(cst, env):
    from app.construction import contracts as K
    c = K.contract_new(T, "RCC framework Tower A", "Shree Constructions", "contractor", value=24000000,
                       signed_on="2026-08-01", start_on="2026-08-15", end_on="2027-08-14", notice_days=30)
    cid = c["contract_id"]
    K.oblig_add(T, cid, "submit RA bill by the 5th", due_on="2026-11-05", owner_side=True)
    K.oblig_add(T, cid, "client: hand over clear site", due_on="2026-10-01", owner_side=False)
    od = K.oblig_due(T, days=7)
    assert od["late"] and od["late"][0]["side"] == "unka" and od["soon"]
    v = K.variation_draft(T, cid, "Additional coping on terrace", basis="SOR 12.7", qty=45, rate=890)
    assert v["amount"] == 40050 and "client" in v["say"]
    with pytest.raises(Exception) as ex:
        K.variation_mark(T, v["variation_id"], "approved", approved_by="")
    assert "naam" in str(ex.value).lower()
    K.variation_mark(T, v["variation_id"], "approved", approved_by="Shivneri LLP (client)")
    cl = K.claim_paper(T, cid, "owner-held site 22 days", event_on="2026-09-01", noticed_on="2026-09-12",
                       matrix=[{"event": "site handover late", "clause": "cl 4.2 GCC", "effect": "EOT + cost",
                                "evidence": "site diary Sep"}])
    nc = cl["notice_compliance"]
    assert nc["days_taken"] == 11 and nc["in_time"] and nc["window_days"] == 30
    assert "advocate" in cl["say"]
    late_claim = K.claim_paper(T, cid, "late claim", event_on="2026-08-01", noticed_on="2026-09-15",
                               matrix=[{"event": "e", "clause": "cl 1", "effect": "x", "evidence": "y"}])
    assert late_claim["notice_compliance"]["in_time"] is False
    with pytest.raises(Exception):
        K.claim_paper(T, cid, "no matrix", event_on="2026-08-01")
    d = K.day(T)
    assert d["open_contracts"] == 1 and d["variations_open"] == 0   # approved variation left the chase


def test_tender_watch_bid_sheet_packs_vendors(cst, env):
    from app.construction import tender as Td
    t = Td.tender_add(T, "PMAY school block", "ZP Pune", due_on="2026-11-20", emd=250000, scope="RCC + finishing")
    tid = t["tender_id"]
    d = Td.due(T, days=30)
    assert d["due"][0]["in_days"] == 15
    with pytest.raises(Exception) as ex:
        Td.bid_sheet(T, tid, "maybe", reasons=[])
    assert "bid | no_bid" in str(ex.value)
    b = Td.bid_sheet(T, tid, "bid", reasons=[{"factor": "margin >= 12%", "note": "QS rate se dekha"},
                                             {"factor": "EMD float ok", "note": "cash flow"}])
    assert b["factors"] == 2 and "aapki" in b["say"]
    pq = Td.pack(T, tid, "prequal", rows=[{"item": "similar works", "value": "3 school blocks", "source": "work orders"}])
    with pytest.raises(Exception):
        Td.pack(T, tid, "prequal", rows=[{"item": "turnover", "value": "12 Cr"}])   # no source, no row
    pp = Td.pack(T, tid, "price", rows=[{"item": "RCC m3", "value": "8450", "source": "QS rate_id cqr.."}])
    assert "bid manager" in pp["say"]
    Td.tender_mark(T, tid, "submitted", ref="ZP/2026/88")
    v = Td.vendor_add(T, "Shree Constructions", scope="RCC", rating="preferred")
    Td.vendor_rate(T, v["vendor_id"], "watch", note="2 delays in Oct")
    vs = Td.vendors(T)
    assert vs["vendors"][0]["rating"] == "watch"
    with pytest.raises(Exception):
        Td.vendor_add(T, "x", rating="best")                       # her scale, not Hoola's


def test_drawqa_rules_checks_review_pack(cst, env):
    from app.construction import drawqa as D
    w = D.dwg_add(T, "Shivneri Heights", "A-05", rev="2", kind="plan", scale_as_noted="1:100", source="Architect drop")
    wid = w["drawing_id"]
    assert "document-level" in w["say"].lower() and "model" in w["say"].lower()
    with pytest.raises(Exception) as ex:
        D.rule_add(T, "front_setback", "Front setback min", 3.0, "m", clause="", source="")
    assert "Clause" in str(ex.value) or "clause" in str(ex.value)
    D.rule_add(T, "front_setback", "Front setback min", 3.0, "m", clause="UDCPR 6.1", source="DCPR as adopted",
               checked_on="2026-11-01", direction="min")
    D.rule_add(T, "far_max", "FAR max", 2.5, "-", clause="UDCPR 6.1", source="DCPR as adopted")
    ok = D.check(T, wid, "front_setback", declared=3.6)     # min rule: above the minimum is WITHIN
    assert ok["verdict"] == "ok" and ok["margin"] == 0.6 and "architect" in ok["say"]
    br = D.check(T, wid, "far_max", declared=2.9)           # max rule: above the cap breaches
    assert br["verdict"] == "breach" and "ARITHMETIC" in br["say"].upper()
    low = D.check(T, wid, "front_setback", declared=2.2)    # min rule: below the minimum breaches
    assert low["verdict"] == "breach"
    with pytest.raises(Exception) as ex:
        D.check(T, wid, "height_limit", declared=15)
    assert "rule_add" in str(ex.value)                              # no rule, no check, no guess
    rp = D.review_pack(T, wid)
    assert rp["breaches"] == 2 and rp["file"]["name"].endswith(".pdf") and "khaali" in rp["say"]
    D.dwg_mark(T, wid, "returned", note="setback note to architect")
    d = D.day(T)
    assert d["drawings"] == 1 and d["checks"] == 3 and d["breaches"] == 2


def test_ehs_permits_and_toolbox(cst, env):
    from app.construction import quality as Q
    p = Q.permit_draft(T, "Tower B", "excavation", "2.5 m gadda - fall hazard",
                       controls=[{"control": "barricade + night lamps", "done": True},
                                 {"control": "ladder access", "done": False}], valid_till="2026-11-07")
    pid = p["permit_id"]
    assert "SAFETY OFFICER" in p["say"]
    with pytest.raises(Exception) as ex:
        Q.permit_issue(T, pid, issued_by="")
    assert "naam" in str(ex.value)
    i = Q.permit_issue(T, pid, issued_by="Smt. Jadhav (Safety Officer)")
    assert "ISSUED" in i["say"] and "Jadhav" in i["say"]
    tb = Q.toolbox_log(T, "Tower B", "height work - full body harness", attendees=18, gang="Dooley")
    assert "18" in tb["say"]
    with pytest.raises(Exception):
        Q.permit_draft(T, "Tower B", "welding", "sparks", controls=[{"control": "x"}])   # kind is a closed list
    Q.permit_close(T, pid)
    d = Q.day(T)
    assert "permits_expired" in d
    from app.agent.const_quality_tools import QUALITY_HANDLERS
    from tests.test_life import conv_ctx
    ctx = conv_ctx()
    r = asyncio.run(QUALITY_HANDLERS["const_quality_dekho"](ctx, "permits"))
    assert r["permits"] == [] or r["permits"][0]["status"] == "closed"


# ---------------------------------------------------------------- the tool layer
def test_registry_566_and_dispatch(env):
    from app.agent.tools import HANDLERS, TOOLS, TOOL_LABELS
    names = {t["name"] for t in TOOLS}
    for n in ("const_approvals", "const_approvals_dekho", "const_qs", "const_qs_dekho", "const_rera",
              "const_rera_dekho", "const_contracts", "const_contracts_dekho", "const_tender",
              "const_tender_dekho", "const_drawqa", "const_drawqa_dekho"):
        assert n in names and n in HANDLERS and n in TOOL_LABELS, n
    assert len(TOOLS) == 629, "626 + 1 app_engine (v0.824 APP ENGINE 1: the Web Studio React app lane - one new tool). 625 + 1 hoola_design (v0.817.0 HOOLA DESIGN: the design editor's one tool). 624 + 1 ai_app (v0.785 HOOLA AI APPS). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " "581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 556 (their chain) + 12 construction Wave 2 + 1 reach (v0.559 REACH MANCH) + 1 speckit (v0.569 SPEC SUTRA)"


def test_qs_tool_end_to_end(env):
    from tests.test_life import conv_ctx
    from app.agent.const_qs_tools import QS_HANDLERS
    ctx = conv_ctx()
    r = asyncio.run(QS_HANDLERS["const_qs"](ctx, "takeoff", project="Tower A", item="Brick wall 230",
                                            kind="brickwork", params={"length": 20, "height": 3, "thickness": 0.23}))
    assert r["qty"] == 13.8 and "IS 1200 (Part 3)" in r["is_ref"]
    r2 = asyncio.run(QS_HANDLERS["const_qs"](ctx, "recompute", takeoff=r["takeoff_id"]))
    assert r2["bit_for_bit"]
    r3 = asyncio.run(QS_HANDLERS["const_qs"](ctx, "bbs", bars=[{"shape": "straight", "dia": 12, "length": 8, "nos": 20}]))
    assert r3["total_kg"] == round(20 * 8 * 144 / 162.0, 2)
    with pytest.raises(Exception) as ex:
        asyncio.run(QS_HANDLERS["const_qs"](ctx, "retention", amount=1000, pct=0))
    assert "contract" in str(ex.value)


def test_approvals_and_rera_tools_end_to_end(env):
    from tests.test_life import conv_ctx
    from app.agent.const_approvals_tools import APPROVALS_HANDLERS
    from app.agent.const_rera_tools import RERA_HANDLERS
    ctx = conv_ctx()
    f = asyncio.run(APPROVALS_HANDLERS["const_approvals"](ctx, "file", project="Shivneri", authority="MCGM",
                                                          purpose="building permission"))
    pk = asyncio.run(APPROVALS_HANDLERS["const_approvals"](ctx, "packet", file=f["file_id"]))
    assert pk["file"]["name"].endswith(".pdf") and isinstance(pk["gaps"], list)
    with pytest.raises(Exception) as ex:
        asyncio.run(APPROVALS_HANDLERS["const_approvals"](ctx, "file", project="", authority="", purpose=""))
    assert "bataiye" in str(ex.value)
    p = asyncio.run(RERA_HANDLERS["const_rera"](ctx, "project", name="Shivneri Heights", maha_rera="P51700049999"))
    with pytest.raises(Exception) as ex:
        asyncio.run(RERA_HANDLERS["const_rera"](ctx, "escrow_withdraw", rera_project=p["rera_project_id"],
                                                amount=100))
    assert "certificate" in str(ex.value)
    rc = asyncio.run(RERA_HANDLERS["const_rera_dekho"](ctx, "reconcile", rera_project=p["rera_project_id"]))
    assert rc["reserve"] == 0 and rc["reserve_pct"] == 70.0


def test_tier_c_rides_the_wave2_tools(env):
    from app.construction import gates
    # the new desks' refusals come from the ONE law, verbatim, through every tool's guard
    for ask in ("file the permission application on her behalf", "certify the escrow withdrawal",
                "approve the change order", "decide the delay entitlement"):
        r = gates.tier_c_check(ask)
        assert r and ("licensee" in r or "promoter" in r or "CA" in r or "client" in r or "advocate" in r), ask
    # and the guard is called by every Wave-2 tool file (the guard text rides the errors)
    from app.agent.const_contracts_tools import CONTRACTS_HANDLERS
    from tests.test_life import conv_ctx
    ctx = conv_ctx()
    with pytest.raises(Exception):
        asyncio.run(CONTRACTS_HANDLERS["const_contracts"](ctx, "contract", name="", party=""))


def test_voice_via_kaam_and_hub_rows(env):
    from app.voice import VOICE_VIA_KAAM
    for n in ("const_approvals", "const_approvals_dekho", "const_qs", "const_qs_dekho", "const_rera",
              "const_rera_dekho", "const_contracts", "const_contracts_dekho", "const_tender",
              "const_tender_dekho", "const_drawqa", "const_drawqa_dekho"):
        assert n in VOICE_VIA_KAAM, n
    from app.employee.hire import CATALOG, CONST_GROUP
    keys = ["const_approvals", "const_qs", "const_rera", "const_contracts", "const_tender", "const_drawqa"]
    for k in keys:
        assert CATALOG[k]["live"] and CATALOG[k]["group"] == CONST_GROUP
        assert CATALOG[k]["never"] and CATALOG[k]["does"]
    # #81 rides const_quality's never-list now
    assert any("permit" in x for x in CATALOG["const_quality"]["never"])
    from app.employee import hire
    hire.ensure_table()
    r = hire.hire(T, "const_qs")
    assert r["key"] == "const_qs" and "const_qs" in hire.hired_keys(T)
    cat = hire.catalog(T)
    const_rows = [c for c in cat if c["group"] == CONST_GROUP]
    assert len(const_rows) >= 11


def test_version_pins():
    from pathlib import Path
    REPO = Path(__file__).resolve().parents[2]
    from app.main import APP_VERSION
    assert APP_VERSION == "0.874.0"
    assert 'APP_VERSION = "0.874.0"' in (REPO / "server" / "app" / "main.py").read_text()
    assert "version: 0.874.0+873" in (REPO / "pubspec.yaml").read_text()
