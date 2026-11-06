"""v0.586.0 Construction Wave 4 - the remaining seats (owner: 'GO WAVE 4'; plan
docs/CONSTRUCTION_EMPLOYEE_PLAN.md Wave-4 mapping; the 47 register rows outside Waves 1-3.5 except
the four design-discipline rows 8/14/15/17 that DESIGN_DESK_PLAN.md owns, plan §4 anti-duplication).

Five NEW desks: const_land (#1-#6 parcels/title/records/FSI/finance/JV), const_plan (#42/#43/#63/
#65/#66/#68/#69/#79/#80 - baseline variance, P x I risks, cash-flow, EVM, plant bookings; criticality
NEVER computed), const_ehs (#83/#84/#86 training expiry, fed limits, camp checks by name),
const_studio (#119/#120 registers, no rendering), const_learn (#121/#122/#123 marks fed, pass line
hers, advice tier C). Extensions on six existing desks: approvals screener (#33), QS cost plan/VE/
GST (#40/#89), contracts LD + arbitration bundle (#48/#50), tender purchase/expediting/EXIM
(#57/#59/#60), quality material tests (#76), customer sales/AFS/handover/investor (#94-#99). The FM
rows (#102-#108) ride the EXISTING property/society seats (plan §12) as the const_fm tools on the
new fm_work duty. Four rows were already shipped elsewhere (#7/#13/#100/#101). Gates 33 -> 40, the
india pack 18 -> 19 (works-contract GST rate row), registry 581 -> 593 (six new do+dekho tools),
VOICE_VIA_KAAM unchanged, Hub rows carry the new lines, version pins."""
import asyncio

import pytest

T = "default"


@pytest.fixture
def cst(env, monkeypatch):
    from app import config
    from app.construction import common
    from app.construction import ehs, fm, planwork
    monkeypatch.setattr(common, "today", lambda t: __import__("datetime").date(2026, 11, 6))
    for mod in (planwork, ehs, fm):
        monkeypatch.setattr(mod, "today", lambda t: __import__("datetime").date(2026, 11, 6))
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


# ---------------------------------------------------------------- register + gates + pack
def test_register_wave4(env):
    from app.construction import register as R
    assert len(R.WAVE4_IDS) == 47 and set(R.WAVE4_HOME) == set(R.WAVE4_IDS)
    w = R.wave("4")
    assert len(w) == 47 and {r["id"] for r in w} == set(R.WAVE4_IDS)
    assert "const_land" in R.WAVE4_HOME[1] and "const_plan" in R.WAVE4_HOME[63]
    assert "const_ehs" in R.WAVE4_HOME[83] and "const_studio" in R.WAVE4_HOME[119]
    assert "const_learn" in R.WAVE4_HOME[121]
    assert "screener" in R.WAVE4_HOME[33] and "const_qs" in R.WAVE4_HOME[40]
    assert "const_contracts" in R.WAVE4_HOME[48] and "const_tender" in R.WAVE4_HOME[57]
    assert "const_quality" in R.WAVE4_HOME[76] and "const_customer" in R.WAVE4_HOME[94]
    assert "architect_assistant" in R.WAVE4_HOME[7] and "society_manager" in R.WAVE4_HOME[101]
    assert "const_fm" in R.WAVE4_HOME[102] and "const_fm" in R.WAVE4_HOME[108]
    assert R.get(1)["wave"] == "4" and R.get(123)["tier"] == "A/B"
    # the four design-discipline rows stay with DESIGN_DESK_PLAN (plan §4)
    assert [r[0] for r in R.ROWS if not r[5]] == [8, 14, 15, 17]
    # waves 1-3.5 unchanged
    for wv, n in (("1", 15), ("2", 29), ("3", 23), ("3.5", 5)):
        assert len(R.wave(wv)) == n, wv
    st = R.stats()
    assert st["by_wave"]["4"] == 47


def test_gates_wave4(env):
    from app.construction.gates import TIER_C, tier_c_check
    assert len(TIER_C) == 40, "33 after Wave 3.5 + title/critical-path/site-safe/tax-advice/" \
                              "RERA-ad/structural-audit/GST-return"
    for ask in ("certify a clear title for survey 112", "declare the critical path for me",
                "declare the site safe so work can resume", "give tax or investment advice on this deal",
                "advertise the project without its RERA number", "certify the structural audit",
                "file the GST return today"):
        assert tier_c_check(ask), ask
    # the Wave-3 / 3.5 refusals still ride
    assert tier_c_check("approve the as-built set")
    assert tier_c_check("order formwork striking")
    assert tier_c_check("certify a survey")
    assert tier_c_check("decide delay entitlement")


def test_india_pack_19_rows_with_gst(env):
    from app.construction import statepacks as SP
    pack = SP.load("india")
    assert len(pack["rows"]) == 19, "18 (Waves 3/3.5) + the works-contract GST rate row"
    r = SP.rule_cited("india", "gst_works_contract_pct")
    assert float(r["value"]) == 18.0 and "11/2017-IGST" in r["source"]
    assert "verify" in r["source"], "the row itself says to verify before reliance"
    assert float(SP.rule_value("india", "is456_strike_slab_soffit", 0.0)) == 72.0


# ---------------------------------------------------------------- const_land
def test_land_flow(cst):
    from app.construction import land as L
    with pytest.raises(L.CstError):
        L.parcel_add(T, "Sunshine Plot", "112/1", "Wadgaon", 0.0, "")      # no area, no source
    p = L.parcel_add(T, "Sunshine Plot", "112/1", "Wadgaon", 4046.0, "7/12 sheet 2024")
    assert p["area_source"] == "7/12 sheet 2024"
    with pytest.raises(L.CstError) as ex:                                  # the name law
        L.item_add(T, "Sunshine Plot", "title", [["7/12", "received"]], by="")
    assert "naam" in str(ex.value).lower()
    L.item_add(T, "Sunshine Plot", "title", [["7/12", "received"], ["Index II", "pending"]],
               by="Adv. R. Kulkarni")
    L.item_add(T, "Sunshine Plot", "record", [["7/12", 2000.0, "2024-03-01"],
                                              ["mutation-45", 2046.0, "2024-06-11"]])
    rec = L.records_recon(T, "Sunshine Plot")
    assert rec["parcels"][0]["records_total"] == 4046.0
    assert rec["parcels"][0]["verdict"] == "match"
    with pytest.raises(L.CstError):                                        # FSI needs its source
        L.feasibility(T, "Sunshine Plot", 4046.0, 2.0, "")
    f = L.feasibility(T, "Sunshine Plot", 4046.0, 2.0, "DCR 6.1 residential zone")
    assert f["permissible_builtup"] == 8092.0
    with pytest.raises(L.CstError):
        L.item_add(T, "Sunshine Plot", "jv", [["landowner", 60.0]])        # JV needs the deed source
    L.item_add(T, "Sunshine Plot", "jv", [["landowner", 60.0], ["developer", 40.0]],
               source="JV deed 12/2024")
    jv = L.jv_entitlement(T, "Sunshine Plot", 8000.0)
    assert jv["share_total_pct"] == 100.0 and jv["shares"][1]["area"] == 3200.0
    L.item_add(T, "Sunshine Plot", "funding", [["own", 200.0]], source="sanction note")
    L.item_add(T, "Sunshine Plot", "funding", [["HDFC", 800.0]], source="term sheet")
    L.item_add(T, "Sunshine Plot", "finance", [["land", 600.0], ["construction", 400.0]],
               source="cost sheet v1")
    fin = L.finance_sum(T, "Sunshine Plot", 9.5, "sanction letter", years=2.0)
    assert fin["cost_total"] == 1000.0 and fin["equity"] == 200.0 and fin["debt"] == 800.0
    assert fin["interest_outgo_simple"] == 152.0 and "CFO" in fin["said"]


# ---------------------------------------------------------------- const_plan
def test_plan_schedule_and_risks(cst):
    from app.construction import planwork as P
    P.activity_add(T, "Tower A", [["A1", "excavation", "2026-10-01", "2026-10-20"],
                                  ["A2", "raft", "2026-10-21", "2026-11-10"]])
    P.activity_update(T, "Tower A", "A1", act_finish="2026-10-25", pct=100)
    v = P.variance(T, "Tower A")
    a1 = next(x for x in v["activities"] if x["code"] == "A1")
    assert a1["slip_days"] == 5 and a1["state"] == "LATE"
    assert "critical" in v["said"].lower() and "NAHI" in v["said"]
    with pytest.raises(P.CstError):
        P.risk_add(T, "Tower A", [["crane strike", 9, 3, "SM", ""]])       # P must be 1-5, HER marks
    P.risk_add(T, "Tower A", [["crane strike", 2, 4, "SM", "2026-11-20"],
                              ["cement shortage", 3, 3, "MM", ""]])
    b = P.risk_board(T, "Tower A")
    assert b["top"]["risk"] == "cement shortage" and b["top"]["score"] == 9


def test_plan_money_and_plant(cst):
    from app.construction import planwork as P
    cf = P.cashflow(T, "Tower A", [["2026-11", 100.0], ["2026-12", 150.0]],
                    [["2026-11", 110.0], ["2026-12", 90.0]])
    assert cf["total_planned"] == 250.0 and cf["total_actual"] == 200.0 and cf["total_var"] == -50.0
    e = P.evm(T, "Tower A", 1000.0, [["2026-11", 100.0, 90.0, 120.0]])
    assert e["cum"]["spi"] == 0.9 and e["cum"]["cpi"] == 0.75 and e["pct_complete"] == 9.0
    assert "EAC" in e["said"]
    assert P.plant_add(T, "Tower A", [["TC-1", "tower crane", "hired"]])["rows"] == 1
    P.plant_book(T, "Tower A", "TC-1", "2026-11-10", "2026-11-15", "Tower A")
    clash = P.plant_book(T, "Tower A", "TC-1", "2026-11-14", "2026-11-20", "Tower B")
    assert len(clash["double_booked_with"]) == 1 and "SAVADHAN" in clash["said"]
    u = P.plant_util(T, "Tower A", "TC-1", working_days=30)
    assert u["booked_days"] == 13 and u["utilisation_pct"] == 43.3
    d = P.dashboard(T, "Tower A")
    assert d["evm_cum"]["cpi"] == 0.75 and "nahi nikalta" in d["said"]


# ---------------------------------------------------------------- const_ehs
def test_ehs_flow(cst):
    from app.construction import ehs as E
    E.training_add(T, "Site 9", [["Ramesh", "mason", "scaffold safety", "2026-05-01", "2026-10-30"],
                                 ["Suresh", "helper", "first aid", "2026-10-20", "2027-01-15"]])
    d = E.training_due(T, "Site 9")
    assert [x["name"] for x in d["expired"]] == ["Ramesh"] and d["valid"] == 1
    with pytest.raises(E.CstError):                                        # limits need a source
        E.env_add(T, "Site 9", "env_limit", [["PM10", 100.0, "ug/m3"]], source="")
    E.env_add(T, "Site 9", "env_limit", [["PM10", 100.0, "ug/m3"]], source="NAAQS CPCB 2009")
    E.env_add(T, "Site 9", "env_read", [["PM10", 142.0, "ug/m3"], ["noise day", 71.0, "dB(A)"]])
    c = E.env_check(T, "Site 9")
    assert c["exceeds"] == 1 and c["rows"][0]["verdict"] == "EXCEEDS"
    assert c["rows"][1]["verdict"] == "NO LIMIT FED"
    E.camp_add(T, "Site 9", [["Block A", 50, 44]])
    with pytest.raises(E.CstError) as ex:                                  # the name law
        E.camp_check(T, "Site 9", [["drinking water", "ok"]], by="")
    assert "naam" in str(ex.value).lower()
    ck = E.camp_check(T, "Site 9", [["drinking water", "ok"]], by="Welfare Officer S. Pawar")
    assert ck["by"] == "Welfare Officer S. Pawar"


# ---------------------------------------------------------------- const_studio + const_learn
def test_studio_flow(cst):
    from app.construction import studio as ST
    st = ST.shot_add(T, "Sunshine", [["drone-001", "aerial approach", "golden hour", "brochure"]])
    assert len(st["ids"]) == 1
    ST.shot_asset(T, "Sunshine", "drone-001", [["site model", "yes", "ready"],
                                               ["landscape set dressing", "yes", "pending"]])
    rep = ST.report_add(T, "Sunshine", "Investor deck Nov", [["site status", "photo", "pending"]])
    assert rep["rows"] == 1
    s = ST.studio_status(T, "Sunshine")
    assert any(g["pending"] >= 1 for g in s["groups"])
    assert "render" in ST.shot_add(T, "Sunshine", [["x", "y", "z", "w"]])["said"]


def test_learn_flow(cst):
    from app.construction import learn as LE
    LE.trainee_add(T, "Skill centre", [["Amit", "bar bender", "B-7"]])
    LE.assess_add(T, "Skill centre", [["Amit", "rebar marks", 18.0, 25.0],
                                      ["Amit", "safety", 22.0, 25.0]])
    s = LE.assess_sum(T, "Skill centre", pass_pct=70.0)
    assert s["results"][0]["avg_pct"] == 80.0 and s["results"][0]["verdict"] == "pass"
    LE.topic_add(T, "Skill centre", [["bar bending schedule", "ITI sem-2", "done"]])
    LE.quiz_add(T, "Skill centre", "bar bending schedule",
                [["standard cover for footing?", "50mm", "40mm", "75mm", "20mm"]])
    sc = LE.quiz_score(T, "Skill centre", "bar bending schedule", [["Amit", "50mm"]])
    assert sc["results"][0]["score"] == 1 and sc["results"][0]["pct"] == 100.0
    cc = LE.coach_check(T, "Skill centre", [["books up to date", "yes"], ["GST filings", "late"]])
    assert "CA" in cc["said"] and "tier C" in cc["said"]


# ---------------------------------------------------------------- const_fm (the existing seats)
def test_fm_flow(cst):
    from app.construction import fm as F
    w = F.wo_add(T, "Green Residency", "Lobby A", "seepage on wall", "high")
    with pytest.raises(F.CstError) as ex:                                  # the name law
        F.wo_update(T, w["id"], "done", by="")
    assert "naam" in str(ex.value).lower()
    assert F.wo_update(T, w["id"], "done", by="J. Kamble")["status"] == "done"
    F.ppm_add(T, "Green Residency", [["DG set", "oil change", 30, "2026-09-20"],
                                     ["lift 1", "monthly check", 30, "2026-11-01"]])
    d = F.ppm_due(T, "Green Residency")
    dg = next(x for x in d["rows"] if x["asset"] == "DG set")
    assert dg["verdict"] == "OVERDUE" and dg["next_due"] == "2026-10-20"
    F.comp_add(T, "Green Residency", [["lift", "LEM-2025-77", "SkyLift", "2025-12-10", "2026-12-10"]])
    assert F.comp_due(T, "Green Residency")["overdue"] == 0
    F.roster_add(T, "Green Residency", [["gate", "Mon", "day", "Ganpat"],
                                        ["gate", "Mon", "night", ""]])
    assert F.roster_gap(T, "Green Residency")["gaps"][0]["shift"] == "night"
    F.audit_add(T, "Green Residency", [["Tower 1", "structural", "2020-06-01", 5, "SES consultants"]])
    a = F.audit_due(T, "Green Residency")
    assert a["rows"][0]["verdict"] == "OVERDUE" and "engineer" in a["said"]
    assert F.asset_add(T, "Green Residency", [["fire pump", "basement", "FM", "2027-01-01"]])["rows"] == 1


def test_fm_tools_on_existing_seats(env):
    import app.employee.roles as R
    assert "const_fm" in str(R.ROLES["society_manager"]["duties"]) or \
        any("const_fm" in str(R.DUTIES.get(d, {})) for d in R.ROLES["society_manager"]["duties"])
    assert any("const_fm" in str(R.DUTIES.get(d, {})) for d in R.ROLES["property_manager"]["duties"])


# ---------------------------------------------------------------- the six extensions
def test_ext_screener_and_qs(env):
    from app.construction import approvals as A
    from app.construction import qs as Q
    s = A.screener_add(T, "Riverside", [["Heritage committee NOC", "unsure", "plot near fort line", "site plan"],
                                        ["CRZ clearance", "no", "beyond 500 m CRZ line", ""]], by="Liaison V. Joshi")
    assert s["unsure"] == 1 and "fetch" in s["said"]
    with pytest.raises(A.CstError):
        A.screener_add(T, "Riverside", [["AAI", "maybe", "", ""]], by="X")   # applies is a mark
    cp = Q.cost_plan(T, "Riverside", [["civil", 500.0, 540.0], ["mep", 200.0, 190.0]])
    assert cp["total_var"] == 30.0 and cp["rows"][0]["verdict"] == "over"
    Q.ve_option(T, "Riverside", [["fly-ash bricks instead", 40.0, "needs sample approval"]])
    g = Q.gst_row(T, "Riverside", "RA-3", [[1000.0, 0.0, "no"]])            # rate from the pack row
    assert g["rows"][0]["rate_pct"] == 18.0 and g["tax_total"] == 180.0
    assert "11/2017-IGST" in g["rate_source"]
    g2 = Q.gst_row(T, "Riverside", "RA-3", [[500.0, 12.0, "yes"]], source="Works contract 12% as fed")
    assert g2["rows"][0]["rate_pct"] == 12.0
    with pytest.raises(Q.CstError):
        Q.gst_sum(T, "Riverside", "RA-3", itc=50.0, itc_source="")           # ITC needs its source
    gs = Q.gst_sum(T, "Riverside", "RA-3", itc=50.0, itc_source="GSTR-2B Oct")
    assert gs["output_tax"] == 240.0 and gs["net_payable"] == 190.0


def test_ext_contracts_tender(env):
    from app.construction import contracts as K
    from app.construction import tender as TD
    with pytest.raises(K.CstError):
        K.ld_calc(T, "Riverside", "WO-1", 30, 0.5, 1000.0, 5.0, sources="")  # the clause is required
    ld = K.ld_calc(T, "Riverside", "WO-1", 30, 0.5, 1000.0, 5.0, sources="cl 2.2 LD clause")
    assert ld["weeks"] == 4.29 and ld["capped"] is False and ld["ld_applied"] == 21.45
    ld2 = K.ld_calc(T, "Riverside", "WO-2", 200, 0.5, 1000.0, 5.0, sources="cl 2.2")
    assert ld2["capped"] is True and ld2["ld_applied"] == 50.0
    K.arb_bundle_add(T, "Riverside", "Claim-1", [["2026-08-01", "site handover letter", "Ex-1"]],
                     by="PM S. Rao")
    assert len(K.arb_bundle(T, "Riverside", "Claim-1")["rows"]) == 1
    pu = TD.purchase_add(T, "Riverside", [["rebar 12mm", 10.0, "MT", "2026-12-01", "PO-77", "2026-11-01", "JSW"]])
    assert pu["rows"] == 1 and pu["without_po"] == 0
    ex = TD.expedite_add(T, "Riverside", "PO-77", "2026-12-05", "2026-12-01")
    assert ex["verdict"].startswith("LATE")
    assert TD.expedite_board(T, "Riverside")["late_count"] == 1
    assert TD.exim_add(T, "Riverside", [["SH-9", "2026-10-01", "2026-10-09", "BOE original"]])["rows"] == 1


def test_ext_quality_customer(env):
    from app.construction import quality as Q
    from app.construction import customer as C
    with pytest.raises(Q.CstError):
        Q.mtest_add(T, "Site 9", [["cube M25", "C-1", "SGL", 28.1, 25.0, "avg", "IS 456"]])  # op bad
    m = Q.mtest_add(T, "Site 9", [["cube M25", "C-1", "SGL", 28.1, 25.0, "min", "IS 456 cl 15.3"],
                                  ["silt content", "S-2", "site lab", 9.0, 8.0, "max", "IS 383"]])
    assert m["fails"] == 1 and "QC engineer" in m["said"]
    assert len(Q.mtest_list(T, "Site 9", only_fails=True)["rows"]) == 1
    C.lead_add(T, "Sunshine", [["Mrs. Iyer", "98...", "site visit", "A-402", "negotiation"]])
    C.inventory_mark(T, "Sunshine", "A-402", "booked")
    inv = C.inventory_sum(T, "Sunshine")
    assert inv["units"] == {"booked": 1}
    C.mkt_asset(T, "Sunshine", [["brochure v2", "draft", "P52100001234"]])
    C.afs_doc(T, "Sunshine", "A-402", [["AFS signed", "done"]], by="Legal S. Iyer")
    h = C.handover_unit(T, "Sunshine", "A-402", [["maintenance", 24000.0, 24000.0],
                                                 ["club deposit", 10000.0, 0.0]], snags_ref="PUNCH-7")
    assert h["balance"] == 10000.0 and "aapka" in h["said"]
    ip = C.investor_pack(T, "Sunshine", [["Q1", 100.0, 90.0]], [["plinth done", "yes"]])
    assert ip["variance"] == -10.0 and "khaali" in ip["said"]


# ---------------------------------------------------------------- wiring + pins
def test_registry_593_and_new_tools(env):
    from app.agent.tools import HANDLERS, TOOLS, TOOL_LABELS
    assert len(TOOLS) == 606, "581 + const_land/plan/ehs/studio/learn/fm (do + dekho)"
    new = ["const_land", "const_land_dekho", "const_plan", "const_plan_dekho", "const_ehs",
           "const_ehs_dekho", "const_studio", "const_studio_dekho", "const_learn",
           "const_learn_dekho", "const_fm", "const_fm_dekho"]
    names = {t["name"] for t in TOOLS}
    for n in new:
        assert n in names and n in HANDLERS and n in TOOL_LABELS, n


def test_extension_actions_in_enums(env):
    from app.agent import tools as TP
    enums = {}
    for t in TP.TOOLS:
        en = (t.get("input_schema") or {}).get("properties", {}).get("action", {}).get("enum", [])
        if en:
            enums[t["name"]] = en
    assert "screener_add" in enums["const_approvals"] and "screener_list" in enums["const_approvals"]
    for a in ("cost_plan", "ve_option", "gst_row", "gst_sum"):
        assert a in enums["const_qs"], a
    for a in ("ld_calc", "arb_bundle_add", "arb_bundle"):
        assert a in enums["const_contracts"], a
    for a in ("purchase_add", "expedite_add", "expedite_board", "exim_add"):
        assert a in enums["const_tender"], a
    assert "mtest_add" in enums["const_quality"]
    for a in ("lead_add", "inventory_mark", "mkt_asset", "afs_doc", "handover_unit", "investor_pack"):
        assert a in enums["const_customer"], a


def test_tools_end_to_end_w4(env):
    from tests.test_life import conv_ctx
    from app.agent.const_land_tools import LAND_HANDLERS
    from app.agent.const_fm_tools import FM_HANDLERS
    ctx = conv_ctx()
    p = asyncio.run(LAND_HANDLERS["const_land"](ctx, "parcel_add", project="Sunshine",
                                                survey_no="99", village="Urse", area=2000.0,
                                                area_source="7/12"))
    assert p["ok"] and p["area_source"] == "7/12"
    jv = asyncio.run(LAND_HANDLERS["const_land"](
        ctx, "item_add", project="Sunshine", kind="jv",
        rows=[["owner", 60.0], ["dev", 40.0]], source="deed 2024"))
    assert jv["rows"] == 2
    w = asyncio.run(FM_HANDLERS["const_fm"](ctx, "wo_add", project="Green", location="lobby",
                                            issue="light out"))
    d = asyncio.run(FM_HANDLERS["const_fm"](ctx, "wo_update", wo=w["id"], status="in_progress",
                                            by="Kamlesh"))
    assert d["status"] == "in_progress"
    lst = asyncio.run(FM_HANDLERS["const_fm_dekho"](ctx, "wo"))
    assert len(lst["wo"]) == 1


def test_voice_via_kaam_unchanged(env):
    from app.voice import VOICE_VIA_KAAM
    for n in ("const_bim", "const_survey", "const_predesign", "const_green"):
        assert n in VOICE_VIA_KAAM, n
    for n in ("const_land", "const_plan", "const_ehs"):
        assert n not in VOICE_VIA_KAAM, "new desks need an explicit voice admission first"


def test_hub_rows_carry_w4(env):
    from app.employee.hire import CATALOG
    for key, marker in (("const_land", "7/12"), ("const_plan", "P x I"), ("const_ehs", "expired"),
                        ("const_studio", "Shot briefs"), ("const_learn", "pass line"),
                        ("const_qs", "GST"), ("const_contracts", "LD calculator"),
                        ("const_tender", "expediting"), ("const_quality", "Material test"),
                        ("const_customer", "RERA number"), ("const_approvals", "Heritage")):
        assert any(marker.lower() in str(x).lower() for x in CATALOG[key]["does"]), (key, marker)
    assert any("tier C" in x for x in CATALOG["const_land"]["never"])
    assert len(CATALOG) == 83, "73 (68 + five Wave-4 desks) + their chain to v0.609 (dukaan/retail/bima/risk/paisa/sandarbh...)"


def test_version_pins():
    from pathlib import Path
    REPO = Path(__file__).resolve().parents[2]
    from app.main import APP_VERSION
    assert APP_VERSION == "0.634.0"
    assert 'APP_VERSION = "0.634.0"' in (REPO / "server" / "app" / "main.py").read_text()
    assert "version: 0.634.0+640" in (REPO / "pubspec.yaml").read_text()
