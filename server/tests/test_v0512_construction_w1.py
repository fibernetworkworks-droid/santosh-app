import re
"""v0.512.0 Construction Wave 1: the tier gate (construction/gates.py), the register as data, the state
packs (maharashtra v0: schema, staleness, the determined tax rows), the store desk (#61 GRN / issue /
reconcile with wastage + reorder), the labour desk (#85 muster + licence calendar, #87 wage audit with
the rate SOURCE, #90 BOCW cess + Sec 393(1) TDS from the pack), the books (#91 + vendor ageing), the
customer desk (#92 demand DRAFT -> letter PDF -> send OWNER ONLY, receipts, #97/#98 handover + DLP
clock), quality (#75 ITP + hold points, NCR, #76 test lots with a human verdict, IS 456 Table 11 cube
DRAFT for M20+ with the below-M20 refusal, #78 punch over sitesup snags), meetings (#67 minutes +
actions), the sitesup voice_log (writes through the SAME service paths, the missing questions listed)
and progress variance (#64), the theka extensions (#62 rate basis + advances recovered oldest-first,
#71 wage_calc with the trail), and the tool layer (registry 551, handlers dispatch, VOICE_VIA_KAAM,
Hub rows, version pins)."""
import asyncio
from datetime import date

import pytest

T = "default"
DAY = date(2026, 11, 5)


@pytest.fixture
def cst(env, monkeypatch):
    from app import config
    from app.construction import common
    from app.construction import customer as C
    from app.construction import labour as L
    from app.construction import meetings as M
    from app.construction import quality as Q
    from app.construction import store as St
    monkeypatch.setattr(common, "today", lambda t: DAY)
    for mod in (St, L, C, Q, M):
        monkeypatch.setattr(mod, "today", lambda t: DAY)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


# ---------------------------------------------------------------- C0: register, gates, state packs
def test_register_counts_and_waves():
    from app.construction import register as R
    assert len(R.ROWS) == 123
    assert len(R.FIELDS) == 15
    assert R.WAVE1_IDS == [61, 62, 64, 67, 70, 71, 75, 78, 85, 87, 88, 90, 91, 92, 98]
    w1 = R.wave("1")
    assert len(w1) == 15 and {r["id"] for r in w1} == set(R.WAVE1_IDS)
    row = R.get(71)
    assert "Theka" in row["name"] and row["tier"] == "A" and row["human"] == "contractor"
    assert R.get(999) is None
    st = R.stats()
    assert st["total"] == 123 and st["by_wave"]["1"] == 15
    assert R.WAVE1_HOME[61] == "const_store" and "theka" in R.WAVE1_HOME[88]


def test_tier_c_gate_hits_and_legit_passes():
    from app.construction import gates
    for ask in ("sign the structural design certificate for me", "certify the measurement book",
                "file the permission application on the portal", "accept the concrete cubes today",
                "issue the termination notice to the sub", "decide the delay entitlement and deduct LD",
                "certify RERA escrow withdrawal for this quarter", "release the payment to the vendor",
                "approve the change order", "give the safety clearance for confined space"):
        refusal = gates.tier_c_check(ask)
        assert refusal and len(refusal) > 20, f"tier C missed: {ask}"
    for ask in ("banao RA bill", "record the wage payment I made", "grn: cement 200 bag aaya",
                "make the working paper for the delay claim", "draft the demand letter",
                "reconcile the store", "note: payment received yesterday"):
        assert gates.tier_c_check(ask) is None, ask
    assert len(gates.TIER_C) >= 20
    assert "PREPARE" in gates.LAW


def test_state_pack_schema_and_staleness():
    from app.construction import statepacks as SP
    pack = SP.load("maharashtra")
    assert pack["state"] == "maharashtra" and len(pack["rows"]) >= 5
    assert SP.row(pack, "bocw_cess")["value"] == 1.0
    assert SP.value(pack, "rera_escrow_pct") == 70.0
    assert SP.stale({**pack, "refresh_by": "2020-01-01"})
    assert not SP.stale(pack)
    for bad in ({"state": "x"}, {**pack, "rows": []},
                {**pack, "rows": [{"rule_id": "a", "value": 1}]}):
        with pytest.raises(SP.PackError):
            SP._validate(bad)
    with pytest.raises(SP.PackError):
        SP.load("uttarakhand")     # not built - refused honestly, never guessed


def test_tax_rows_carry_their_citations(cst):
    from app.construction import statepacks as SP
    t = SP.tax_rows("maharashtra")
    assert t["gst_works_contract"]["value"] == 18.0 and "clause" in t["bocw_cess"]
    assert t["it_tds_194c"]["value"]["individual"] == 1.0 and t["it_tds_194c"]["value"]["other"] == 2.0
    assert t["bocw_cess"]["checked_on"] == "2026-11-05"


def test_stale_pack_refuses_the_hisaab(cst, monkeypatch):
    from app.construction import statepacks as SP
    monkeypatch.setattr(SP, "load", lambda s: {"state": s, "rows": [], "checked_on": "2025-01-01",
                                               "refresh_by": "2025-06-01"})
    with pytest.raises(Exception) as ex:
        SP.tax_rows("maharashtra")
    assert "purana" in str(ex.value)


# ---------------------------------------------------------------- C3 store (#61)
def test_store_grn_issue_reconcile(cst):
    from app.construction import store as S
    S.upsert_lot(T, "Cement OPC 53", unit="bag", min_qty=50, max_qty=2000)
    r = S.grn(T, "Cement OPC 53", 200, rate=395, vendor="Ultra dealer", invoice_no="C-554", day="2026-11-01")
    assert "200" in r["say"] and r["balance"] == 200
    with pytest.raises(Exception):     # over-issue refused
        S.issue(T, "Cement OPC 53", 500, site="Slab A")
    r = S.issue(T, "Cement OPC 53", 40, site="Slab A", gang="Dooley", purpose="column casting", day="2026-11-02")
    assert r["balance"] == 160
    S.issue(T, "Cement OPC 53", 2, day="2026-11-02", waste=True)
    rec = S.reconcile(T, "Cement OPC 53")
    row = rec["items"][0]
    assert row["received"] == 200 and row["issued"] == 40 and row["waste"] == 2 and row["on_hand"] == 158
    assert row["wastage_pct"] == 1.0
    assert "DOBARA MANGWAO" not in rec["say"]          # 158 above the reorder level 50
    S.issue(T, "Cement OPC 53", 120, day="2026-11-03")  # now 38 < 50 -> alert
    rec = S.reconcile(T)
    assert "DOBARA MANGWAO" in rec["say"]
    lots = {x["item"]: x for x in S.lots(T)}
    assert lots["Cement OPC 53"]["balance"] == 38


# ---------------------------------------------------------------- C4 labour (#85, #87, #90)
def test_labour_muster_and_licence_calendar(cst):
    from app.construction import labour as L
    r = L.muster(T, "Slab A", day="2026-11-04", contractor="Ramesh", trade="mason", present=12, absent=2, ot_hours=3)
    assert "aaye 12" in r["say"] and "gayab 2" in r["say"]
    with pytest.raises(Exception):
        L.muster(T, "Slab A")                      # hazari chahiye
    with pytest.raises(Exception):
        L.licence(T, "contract_labour", number="CL-12", authority="Labour office")   # no expiry
    L.licence(T, "contract_labour", number="CL-12", authority="Labour Commissioner", holder="Ramesh",
              valid_from="2026-06-01", valid_to=str(DAY))
    day = L.day(T)
    assert any(x["number"] == "CL-12" for x in day["licences"])     # expiring today is inside the 30-day window


def test_wage_audit_carries_the_source_and_the_trail(cst):
    from app.construction import labour as L
    with pytest.raises(Exception):
        L.wage_audit(T, "Slab A", workers=10)      # no rate yet
    L.wage_rate(T, "mason", 900, basis="day", source="uski baat: agreement 1 Nov")
    r = L.wage_audit(T, "Slab A", day="2026-11-04", trade="mason", workers=10, ot_hours=8)
    assert r["gross"] == 9000 + (900 / 8) * 1.5 * 8
    assert r["trail"]["rate_row_id"] and "agreement" in r["trail"]["source"]
    assert "aapke tap" in r["say"]
    r2 = L.wage_paid(T, "Slab A", day="2026-11-04", trade="mason", amount=9900, workers=10)
    assert "wages diye gaye" in r2["say"]
    assert isinstance(L.day(T)["open_muster"], list)


def test_cess_tds_from_the_pack(cst):
    from app.construction import labour as L
    r = L.cess_tds(T, 100000, individual=False, pan_ok=True)
    assert r["cess"] == 1000.0 and r["tds"] == 2000.0
    assert L.cess_tds(T, 100000, individual=True)["tds"] == 1000.0
    assert "determined" in r["say"].lower()
    with pytest.raises(Exception):
        L.cess_tds(T, 0)


# ---------------------------------------------------------------- C4 books (#91)
def test_books_and_vendor_ageing(cst):
    from app.construction import books as B
    B.entry(T, "Sunrise heights", "in", 500000, head="receipt", party="customer flat 302", day="2026-10-01")
    B.entry(T, "Sunrise heights", "out", 120000, head="material", party="Steel trader", day="2026-10-05", settled=False)
    B.entry(T, "Sunrise heights", "out", 30000, head="labour", party="Ramesh", day="2026-09-01", settled=False)
    bk = B.book(T, "Sunrise heights")
    assert bk["in"] == 500000 and bk["out"] == 150000 and bk["balance"] == 350000
    assert bk["by_head"]["material"] == 120000
    ag = B.ageing(T, "Sunrise heights")
    assert ag["total"] == 150000 and ag["buckets"]["60+"] == 30000 and ag["buckets"]["31-60"] == 120000
    assert "Steel trader" in ag["parties"]
    r = B.settle(T, ref="Steel trader", day="2026-11-05")
    assert "settled" in r["say"]
    assert B.ageing(T, "Sunrise heights")["total"] == 30000
    with pytest.raises(Exception):
        B.entry(T, "Sunrise heights", "out", 999, head="nonsense")   # head gate
    with pytest.raises(Exception):
        B.entry(T, "Sunrise heights", "sideways", 999)               # side gate


# ---------------------------------------------------------------- C5 customer (#92, #97, #98)
def test_demand_draft_letter_and_owner_only_send(cst, env):
    from app.construction import customer as C
    r = C.demand(T, "Sunrise heights", "A-302", customer="Mrs Kulkarni", milestone="Plinth", amount=500000,
                 due="2026-11-15", interest_pct=1.25)
    did = r["demand_id"]
    assert "DRAFT" in r["say"] and "aapki haan" in r["say"]
    pdf = C.demand_letter(T, did)
    assert pdf[:5] == b"%PDF-" and b"%%EOF" in pdf and len(pdf) > 400
    from tests.test_life import conv_ctx
    non_owner = conv_ctx()
    non_owner.actor = "customer:x"
    with pytest.raises(Exception):
        C.demand_send(T, did, "customer:x")         # the card law: send is owner-only
    r = C.demand_send(T, did, "owner", on="2026-11-05")
    assert "BHEJ" in r["say"].upper()
    assert C.demands(T)[0]["status"] == "sent"
    C.receipt(T, demand_id=did, amount=480000, mode="neft", day="2026-11-12")
    assert C.demands(T)[0]["status"] == "part"
    C.receipt(T, demand_id=did, amount=20000, mode="upi", day="2026-11-13")
    assert C.demands(T)[0]["status"] == "paid"


def test_handover_and_dlp_clock(cst):
    from app.construction import customer as C
    r = C.handover(T, "Sunrise heights", "A-302", customer="Mrs Kulkarni",
                   items=[{"item": "Snag list clear", "done": True}, {"item": "Meter transfer", "done": False}])
    assert r["status"] in ("open", "ready")
    r = C.handover(T, "Sunrise heights", "A-302", items=[{"item": "Meter transfer", "done": True}],
                   keys_on="2026-11-20", utilities="meter + society NOC")
    assert r["status"] == "handed" and r["keys_on"] == "2026-11-20"
    t = C.dlp_open(T, "Sunrise heights", "A-302", issue="Bathroom leakage", trade="plumbing",
                   vendor="Vishwas plumbing", dlp_months=12, possession_on="2026-11-20")
    assert t["dlp_until"].startswith("2027-11-20")
    assert "window khuli" in t["say"]
    with pytest.raises(Exception):
        C.dlp_sent(T, t["ticket_id"], "customer:x")
    assert "Record" in C.dlp_sent(T, t["ticket_id"], "owner", day="2026-11-21")["say"]
    assert C.dlp_list(T)[0]["status"] == "vendor_sent"
    assert "band" in C.dlp_close(T, t["ticket_id"], day="2026-11-25")["say"]
    late = C.dlp_open(T, "Sunrise heights", "B-101", issue="Paint peel", dlp_months=12,
                      possession_on="2024-11-01")     # window khatam
    assert "KHATAM" in late["say"]


# ---------------------------------------------------------------- C6 quality (#75, #76, #78) + cube draft
def test_itp_holds_and_ncr(cst):
    from app.construction import quality as Q
    r = Q.itp(T, "Slab A", "Footing concrete M25",
              steps=[{"step": "Formwork line/level", "spec": "±5 mm", "hold": True},
                     {"step": "Rebar check", "spec": "drawing R-2", "hold": True},
                     {"step": "Pour", "spec": "", "hold": False}])
    assert r["steps"] == 3 and r["hold_points"] == 2 and "HOLD" in r["say"]
    with pytest.raises(Exception):
        Q.itp(T, "Slab A", "Footing concrete", steps=[])
    r = Q.itp_approve(T, r["itp_id"], "S. Deshmukh (QA manager)")
    assert "approved" in r["say"]
    n = Q.ncr(T, "Slab A", "Footing concrete", defect="Cover blocks missing at raft", spec="drawing R-2 / IS 456 cover",
              severity="major")
    assert n["ncr_id"] and "QA" in n["say"]
    assert "band" in Q.ncr_close(T, n["ncr_id"], action="Rework + recheck")["say"]
    day = Q.day(T)
    assert day["open_ncrs"] == 0


def test_test_lot_human_verdict(cst):
    from app.construction import quality as Q
    r = Q.test_lot(T, "Cement OPC 53", lot_no="L-2291", vendor="Ultra", test="28-day compressive",
                   lab="NABL Pune lab", result="54.2, 53.8, 54.6 N/mm2", tested_on="2026-11-04",
                   retest_due="2027-05-04", report_ref="R-77")
    assert "Verdict QC engineer" in r["say"]
    with pytest.raises(Exception):
        Q.test_lot(T, "Cement OPC 53", verdict="maybe")
    v = Q.lot_verdict(T, r["lot_id"], "pass", by="QC engineer")
    assert "pass" in v["say"].lower()
    from app.db import session
    from sqlalchemy import select
    from app.construction.models import CTestLot
    with session() as s:
        lots = s.scalars(select(CTestLot).where(CTestLot.tenant_id == T)).all()
    assert len(lots) == 1 and lots[0].verdict == "pass"


def test_cube_draft_is456_and_below_refuses(cst):
    from app.construction import quality as Q
    r = Q.cube_draft(T, "M25", [31, 32, 33])
    assert r["draft"] == "PASS (DRAFT)" and r["mean"] == 32.0
    r2 = Q.cube_draft(T, "M25", [25, 26, 27])
    assert r2["draft"] == "NOT MET (DRAFT)" and r2["mean"] == 26.0
    r3 = Q.cube_draft(T, "M25", [29, 20, 30])       # individual 20 < fck-4 (21)
    assert r3["draft"] == "NOT MET (DRAFT)" and not r3["individual_ok"]
    with pytest.raises(Exception) as ex:
        Q.cube_draft(T, "M15", [18, 19, 20])        # sigma route - refused, never guessed
    assert "sigma" in str(ex.value)
    assert "Acceptance QA engineer" in r["say"] or "QA engineer" in r["say"]


def test_punch_reads_sitesup_snags(cst):
    from app.sitesup import service as SS
    from app.construction import quality as Q
    SS.save_site(T, "Punch site")
    SS.snag(T, "Punch site", "Crack at beam column joint", location="2F", trade="civil")
    SS.snag(T, "Punch site", "Tap leaking", location="3F bath", trade="plumbing")
    p = Q.punch(T, "Punch site")
    assert p["open"] == 2 and p["total"] == 2
    assert sum(p["by_trade"].values()) == 2          # sitesup's own trade_of classifies the text


# ---------------------------------------------------------------- C6 meetings (#67)
def test_meetings_minutes_actions_chase(cst):
    from app.construction import meetings as M
    r = M.meet(T, "OAC #12", kind="oac", day="2026-11-05", site="Slab A", project="Sunrise heights",
               attendees="Meghana, S. Deshmukh, Ramesh",
               minutes=[{"text": "Slab 4 pouring starts 8 Nov", "by": "S. Deshmukh"}],
               actions=[{"what": "Steel indent close karo", "who": "Ramesh", "due": "2026-11-07"}])
    mid = r["meet_id"]
    assert "1 action" in r["say"]
    M.minute(T, mid, "Client approved the revised colour", by="Meghana")
    a = M.action(T, mid, what="Send aggregate sample", who="Hoola owner", due="2026-11-06")
    with pytest.raises(Exception):
        M.action_done(T, a["action_id"], "customer:x")
    M.action_done(T, a["action_id"], "owner")
    oa = M.open_actions(T)
    assert oa["open"] == 1 and oa["rows"][0]["who"] == "Ramesh"
    pdf = M.minutes_pdf(T, mid)
    assert pdf[:5] == b"%PDF-" and b"%%EOF" in pdf and len(pdf) > 400


# ---------------------------------------------------------------- C1 sitesup: voice log (#70) + variance (#64)
SITE_FIX = {"code": "A1", "name": "Slab casting", "unit": "cum", "qty": 60, "start": "2026-11-01", "finish": "2026-11-30"}


def test_voice_log_writes_through_the_service_paths(cst, env):
    from app.sitesup import service as SS
    SS.save_site(T, "Voice site")
    SS.plan(T, "Voice site", items=[SITE_FIX])
    r = SS.voice_log(T, "Voice site", day="2026-11-04",
                     activities=[{"activity": "Slab casting", "qty": 12, "note": "pump se", "delay": ""}],
                     rows=[{"contractor": "Ramesh", "trade": "mason", "count": 14, "hours": 8}],
                     mat_rows=[{"item": "Cement OPC 53", "qty": 90, "kind": "in", "challan": "C-771"}],
                     tb_row={"topic": "Height safety", "people": 14},
                     note="Sab theek")
    assert r["parts"] and r["missing"] == []      # everything was spoken, nothing left to ask
    assert "Roznama" in r["say"]
    # the rows really landed through the same paths (progress + labour + material + safety)
    from app.db import session
    from sqlalchemy import select
    from app.sitesup.models import SsLabour, SsMaterial, SsProgress, SsSafety
    with session() as s:
        assert s.scalars(select(SsProgress.id).where(SsProgress.day == "2026-11-04")).first()
        assert s.scalars(select(SsLabour.id).where(SsLabour.day == "2026-11-04")).first()
        assert s.scalars(select(SsMaterial.id).where(SsMaterial.day == "2026-11-04")).first()
        assert s.scalars(select(SsSafety.id).where(SsSafety.day == "2026-11-04")).first()
    with pytest.raises(Exception):
        SS.voice_log(T, "Voice site")     # khaali roznama refused
    r = SS.voice_log(T, "Voice site", day="2026-11-04",
                     activities=[{"activity": "Slab casting", "qty": 6}],
                     rows=[{"contractor": "Ramesh", "trade": "mason", "count": 10, "hours": 8}])
    assert any("maal" in m for m in r["missing"])   # the five-questions rule: maal / snag missing


def test_progress_variance_flags_behind(cst, env):
    from app.sitesup import service as SS
    SS.save_site(T, "Var site")
    SS.plan(T, "Var site", items=[{**SITE_FIX, "name": "Blockwork", "qty": 100}])
    SS.progress(T, "Var site", "Blockwork", 30, "2026-11-03")
    v = SS.progress_variance(T, "Var site")
    row = v["activities"][0]
    assert row["planned"] == 100 and row["done"] == 30 and row["pct"] == 30.0 and row["behind"]
    assert "PEECHHE" in v["say"]
    SS.progress(T, "Var site", "Blockwork", 70, "2026-11-04")     # 100% now
    v = SS.progress_variance(T, "Var site")
    assert not v["activities"][0]["behind"]


# ---------------------------------------------------------------- C2 theka (#62, #71)
def test_theka_sub_rate_basis_advances_recovered_oldest_first(cst, env):
    from app.theka import service as S
    S.save_sub(T, "Ramu", individual=True, pan_ok=True, work="brickwork", retention_pct=10, rate_basis="sqm")
    S.sub_advance(T, "Ramu", 20000, day="2026-10-01", note="site start advance")
    S.sub_advance(T, "Ramu", 5000, day="2026-10-20", note="material advance")
    r = S.sub_bill(T, "Ramu", 40000, day="2026-11-04", advance_recover=25000)     # both advances recovered in full
    # TDS: 40000 > 30000, individual, PAN ok -> 1% = 400; retention 10% = 4000; advance 25000
    assert r["tds"]["tds"] == 400 and r["net"] == 40000 - 400 - 4000 - 25000
    assert "advance katuayi 25,000" in r["say"] or "25,000" in r["say"]
    v = S.sub_open_advances(T, "Ramu")
    assert v == 0.0
    # recovering with nothing open recovers nothing - the bill just passes
    r2 = S.sub_bill(T, "Ramu", 10000, advance_recover=5000)
    assert r2["tds"]["tds"] == 0 and r2["net"] == 10000 - 1000        # TDS below threshold; retention 10%


def test_wage_calc_trail_math(cst, env):
    from app.theka import service as S
    with pytest.raises(Exception):
        S.wage_calc(T, workers=10, days=2)                    # rate chahiye
    r = S.wage_calc(T, gang="Dooley", workers=10, days=2, rate=800, ot_hours=8, advance_recover=3000)
    assert r["gross"] == 16000 + (800 / 8) * 1.5 * 8 * 10
    assert r["net"] == r["gross"] - 3000
    assert r["trail"]["ot_rule"].startswith("1.5 x")
    assert "aapke tap" in r["say"]


# ---------------------------------------------------------------- the tool layer
def test_registry_553_and_dispatch(env):
    from app.agent.tools import HANDLERS, TOOLS, TOOL_LABELS
    names = {t["name"] for t in TOOLS}
    for n in ("const_store", "const_store_dekho", "const_labour", "const_labour_dekho", "const_customer",
              "const_customer_dekho", "const_quality", "const_quality_dekho", "const_meet", "const_meet_dekho"):
        assert n in names and n in HANDLERS and n in TOOL_LABELS, n
    assert len(TOOLS) == 617, "616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " "581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 553 (v0.522) + crew_run (v0.523) + game_provenance (v0.535) + 2 from v0.533 CRAWL BRAIN (healed in v0.539: red on pristine main) + 1 reach (v0.559 REACH MANCH) + 1 speckit (v0.569 SPEC SUTRA)"


def test_const_store_tool_end_to_end(env):
    from tests.test_life import conv_ctx
    from app.agent.const_store_tools import STORE_HANDLERS
    ctx = conv_ctx()
    r = asyncio.run(STORE_HANDLERS["const_store"](ctx, "lot", item="Steel Fe500D", unit="kg", min_qty=500))
    assert "Steel Fe500D" in r["say"]
    r = asyncio.run(STORE_HANDLERS["const_store"](ctx, "grn", item="Steel Fe500D", qty=2000, rate=68,
                                                  vendor="JSW dealer", invoice_no="S-9", day="2026-11-01"))
    assert r["balance"] == 2000
    r = asyncio.run(STORE_HANDLERS["const_store_dekho"](ctx, "reconcile"))
    assert r["items"][0]["on_hand"] == 2000
    with pytest.raises(Exception) as ex:
        asyncio.run(STORE_HANDLERS["const_store"](ctx, "grn", item="", qty=5))
    assert "Item" in str(ex.value)


def test_tier_c_refusal_rides_the_tools(env):
    from tests.test_life import conv_ctx
    from app.agent.const_quality_tools import QUALITY_HANDLERS
    ctx = conv_ctx()
    # the cube DRAFT carries the law on its output: acceptance is the QA engineer's act
    r = asyncio.run(QUALITY_HANDLERS["const_quality"](ctx, "cube_draft", grade="M25", results=[30, 31, 32]))
    assert "QA engineer" in r["say"]
    # a tier-C ask through the gate gets the refusal, not the work
    from app.construction import gates
    refusal = gates.tier_c_check("certify the RA bill as passed")
    assert refusal and "billing engineer" in refusal
    refusal = gates.tier_c_check("release the payment to the vendor")
    assert refusal and "tap" in refusal


def test_voice_via_kaam_and_hub_rows(env):
    from app.voice import VOICE_VIA_KAAM
    for n in ("const_store", "const_labour", "const_customer", "const_quality", "const_meet",
              "const_store_dekho", "const_labour_dekho", "const_customer_dekho", "const_quality_dekho", "const_meet_dekho"):
        assert n in VOICE_VIA_KAAM, n
    from app.employee.hire import CATALOG, CONST_GROUP
    keys = ["const_store", "const_labour", "const_customer", "const_quality", "const_meet"]
    for k in keys:
        assert CATALOG[k]["live"] and CATALOG[k]["group"] == CONST_GROUP
        assert CATALOG[k]["never"]
    from app.employee import hire
    hire.ensure_table()
    r = hire.hire(T, "const_store")
    assert r["key"] == "const_store"
    assert "const_store" in hire.hired_keys(T)
    with pytest.raises(Exception):
        hire.hire(T, "nahi_hai_yeh")
    cat = hire.catalog(T)
    assert any(c["group"] == CONST_GROUP for c in cat)


def test_version_pins():
    from pathlib import Path
    REPO = Path(__file__).resolve().parents[2]
    from app.main import APP_VERSION
    assert APP_VERSION == "0.717.0"
    # v0.535: see test_v0501 - a literal version here broke on every bump. The check that matters is agreement.
    _v = re.search(r'APP_VERSION = "([0-9.]+)"', (REPO / "server" / "app" / "main.py").read_text()).group(1)
    assert _v and f"version: {_v}+" in (REPO / "pubspec.yaml").read_text(), f"pubspec must carry {_v}"
