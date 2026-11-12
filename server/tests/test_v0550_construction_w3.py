"""v0.550.0 Construction Wave 3 - model-level and certificate-adjacent (plan docs/CONSTRUCTION_EMPLOYEE_PLAN.md
§7 C11-C15; owner: 'Wave 3 (IFC/BCF/IDS, pre-design, survey)'). The register's Wave-3 home map (23 IDs),
the tier-C edges (area statement / survey certification joins the law), the national `india.json` pack
(IS 875 / IS 456 / CPHEEO rows with citations), the IFC STEP reader with the honest limits (GUID'd
products only, declared quantities, axis-aligned placements, rotation ignored), the BIM desk (health,
ISO 19650 naming, CDE supersede, clash candidates + BCF 2.1 zip, IDS subset with UNVERIFIED facets,
4D mapping + 5D rows on the model's own quantities, qty x rate only with a source), the pre-design desk
(IS 875 loads, IS 456 cl 39.3 sizing with the 50 mm rounding shown, cl 23.2.1 depth route refusing
spans over 10 m, MEP factors FED with sources, fire rules needing clause + source), the survey desk
(coords + LandXML CgPoints, loop traverse, shoelace boundary vs the 7/12, grid volumes with cut/fill
separate, CSV deviations with RMS, RERA carpet under HER wall policy against the pack tolerance row
with the discrepancy pack sign line EMPTY), the delay desk (criticality = HER marks, no CPM, slip days,
notice-compliance arithmetic, the working paper for the forensic planner), the green desk (tariff
slab walk, EPI benchmark, ECBC/daylight rows, model-input register - EnergyPlus not run, EPD carbon
hot-spots, CPHEEO water + RWH, credits sum, Cx scripts + issues, T&C tolerance, M&V least-squares with
r2 and the savings identity), the incident investigations on const_quality (#82 - close needs the
safety head's name, open actions block), and the tool layer (registry 579, dispatch end-to-end,
VOICE_VIA_KAAM, Hub rows, version pins)."""
import asyncio
import io
import zipfile
from datetime import date

import pytest

T = "default"
DAY = date(2026, 11, 5)


@pytest.fixture
def cst(env, monkeypatch):
    from app import config
    from app.construction import bim as B
    from app.construction import common
    from app.construction import delay as D
    from app.construction import green as G
    from app.construction import predesign as P
    from app.construction import quality as Q
    from app.construction import survey as S
    monkeypatch.setattr(common, "today", lambda t: DAY)
    for mod in (B, P, S, D, G, Q):
        monkeypatch.setattr(mod, "today", lambda t: DAY)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def _ifc(n_walls: int = 1, with_volume: bool = False, step: float = 6.0) -> str:
    """A schema-correct IFC4 mini-model: project, storey, space (with quantities), n walls (placed
    `step` m apart along x, with base quantities, optionally a Volume) - GUIDs exactly 22 chars."""
    lines = ["ISO-10303-21;", "HEADER;", "FILE_DESCRIPTION((''),'2;1');",
             "FILE_NAME('a.ifc','2026-11-05T00:00:00',(''),'','','','');", "FILE_SCHEMA(('IFC4'));",
             "ENDSEC;", "DATA;",
             "#1=IFCPROJECT('0ProjGUID0000000000000',$,'Demo Project',$,$,$,$,(#2),#5);",
             "#2=IFCGEOMETRICREPRESENTATIONCONTEXT($,$,3,1.E-05,#3,$);",
             "#3=IFCAXIS2PLACEMENT3D(#4,$,$);", "#4=IFCCARTESIANPOINT((0.,0.,0.));",
             "#5=IFCUNITASSIGNMENT((#6));", "#6=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);",
             "#10=IFCBUILDINGSTOREY('0StoreyGUID00000000000',$,'Ground Floor',$,$,$,$,$,.ELEMENT.);",
             "#11=IFCSPACE('0SpaceGUID000000000000',$,'Lobby 101',$,$,$,$,$,.ELEMENT.,.INTERNAL.,$);",
             "#12=IFCELEMENTQUANTITY('0QtyGUID00000000000000',$,'Qto_SpaceBaseQuantities',$,(#13,#14));",
             "#13=IFCQUANTITYAREA('NetFloorArea','',$,42.5);",
             "#14=IFCQUANTITYVOLUME('NetVolume','',$,110.5);",
             "#15=IFCRELDEFINESBYPROPERTIES('0RelDefGUID00000000000',$,$,$,(#11),#12);",
             "#25=IFCRELAGGREGATES('0RelAggGUID00000000000',$,$,$,#1,(#10));",
             "#26=IFCRELCONTAINEDINSPATIALSTRUCTURE('0RelConGUID00000000000',$,$,$,(#11),#10);"]
    nid = 30
    for i in range(n_walls):
        x = 2.0 + i * step
        qvol = f"#{nid + 8}=IFCQUANTITYVOLUME('NetVolume','',$,{6.0 * 0.23 * 3.0:.3f});" if with_volume else ""
        lines += [
            f"#{nid}=IFCWALL('{('0WallGUID' + str(i)).ljust(22, '0')}',$,'Wall {i + 1}',$,$,#{nid + 1},$,$,.STANDARD.);",
            f"#{nid + 1}=IFCLOCALPLACEMENT($,#{nid + 2});",
            f"#{nid + 2}=IFCAXIS2PLACEMENT3D(#{nid + 3},$,$);",
            f"#{nid + 3}=IFCCARTESIANPOINT(({x}.,3.,0.));",
            f"#{nid + 4}=IFCELEMENTQUANTITY('{('0QtyW' + str(i)).ljust(22, '0')}',$,'Qto_WallBaseQuantities',$,"
            f"(#{nid + 5},#{nid + 6},#{nid + 7}{',#' + str(nid + 8) if with_volume else ''}));",
            f"#{nid + 5}=IFCQUANTITYLENGTH('Length','',$,6.0);",
            f"#{nid + 6}=IFCQUANTITYLENGTH('Width','',$,0.23);",
            f"#{nid + 7}=IFCQUANTITYLENGTH('Height','',$,3.0);"] + ([qvol] if with_volume else []) + [
            f"#{nid + 9}=IFCRELDEFINESBYPROPERTIES('{('0RelDf' + str(i)).ljust(22, '0')}',$,$,$,(#{nid}),#{nid + 4});",
            f"#{nid + 10}=IFCRELCONTAINEDINSPATIALSTRUCTURE('{('0RelCw' + str(i)).ljust(22, '0')}',$,$,$,(#{nid}),#10);"]
        nid += 20
    return "\n".join(lines) + "\nENDSEC;\nEND-ISO-10303-21;\n"


IDS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ids:Ids xmlns:ids="http://identifier.buildingsmart.org/uri/hoola/walls/1.0">
 <ids:Specifications>
  <ids:Specification name="Walls carry base quantities">
   <ids:Applicability><ids:Entity name="IFCWALL"/></ids:Applicability>
   <ids:Requirements><ids:Property name="Length"/></ids:Requirements>
  </ids:Specification>
  <ids:Specification name="Fire rating declared">
   <ids:Requirements><ids:Property propertySet="Pset_WallCommon" name="FireRating"/></ids:Requirements>
  </ids:Specification>
 </ids:Specifications>
</ids:Ids>"""


# ---------------------------------------------------------------- register, homes, packs, gates
def test_register_wave3_homes():
    from app.construction import register as R
    assert len(R.ROWS) == 123
    w3 = R.wave("3")
    assert len(w3) == 23 and {r["id"] for r in w3} == set(R.WAVE3_IDS)
    assert set(R.WAVE3_HOME) == set(R.WAVE3_IDS)
    for rid in (10, 11, 12, 18, 19, 20, 21, 22, 23, 24, 26, 47, 82, 104, 110, 111, 112, 113, 114,
                115, 116, 117, 118):
        assert R.WAVE3_HOME[rid], rid
    assert R.WAVE3_HOME[20] == "const_bim (clash, BCF)" and R.WAVE3_HOME[26] == "const_survey (RERA carpet)"
    assert R.WAVE3_HOME[82] == "const_quality (incident investigation)"
    for rid in (25, 27, 74, 77, 109):          # the plan's stragglers shipped as Wave 3.5
        assert R.get(rid)["wave"] == "3.5", rid   # v0.570.0: shipped (re-healed after every collision)


def test_wave3_tier_c_edges():
    from app.construction import gates
    hits = {
        "certify the carpet area statement for unit 402": ("surveyor", "architect"),
        "certify the survey and give me the certificate": ("licensed surveyor",),
        "sign the stability certificate for the tower": ("engineer",),
        "certify the green rating submission": ("assessor",),
        "certify the commissioning of the chiller plant": ("Cx authority",),
        "certify the energy audit": ("certified auditor",),
        "decide the delay entitlement for the monsoon claim": ("advocate", "counsel"),
    }
    for ask, needles in hits.items():
        refusal = gates.tier_c_check(ask)
        assert refusal, ask
        for n in needles:
            assert n in refusal, (ask, n)
    for ask in ("read the ifc and list the clash candidates", "compute the slab load take-down",
                "record the incident timeline", "prepare the delay working paper"):
        assert gates.tier_c_check(ask) is None, ask


def test_india_pack_rows():
    from app.construction import statepacks as SP
    pack = SP.load("india")
    assert not SP.stale(pack)
    assert len(pack["rows"]) == 19        # 11 + 7 striking (Wave 3.5) + 1 GST rate (Wave 4)
    assert SP.value(pack, "is875_p1_rcc") == 25.0 and SP.value(pack, "is875_p2_office") == 3.0
    assert SP.value(pack, "is456_beam_ss") == 20.0 and SP.value(pack, "cpheeo_lpcd") == 135.0
    r = SP.row(pack, "is456_beam_ss")
    assert "23.2.1" in r["source"] and "IS 456:2000" in r["source"]
    # the state pack wins, the national pack fills in, a missing rule refuses to be cited
    assert SP.rule_value("maharashtra", "rera_carpet_tolerance_pct") == 3.0
    assert SP.rule_value("maharashtra", "cpheeo_lpcd") == 135.0
    with pytest.raises(SP.PackError) as ex:
        SP.rule_cited("maharashtra", "no_such_rule_anywhere")
    assert "bina clause" in str(ex.value)
    m = SP.load("maharashtra")
    assert len(m["rows"]) == 7 and SP.row(m, "rera_carpet_tolerance_pct")["value"] == 3.0


# ---------------------------------------------------------------- C11: the BIM desk
def test_bim_ifc_read_and_health(cst):
    from app.construction import bim as B
    r = B.ifc_add(T, "Tower A", "arch v3", _ifc(n_walls=2))
    assert r["schema"] == "IFC4" and r["spaces"] == 1 and r["storeys"] == 1 and r["elements"] == 2
    assert "rotation" in r["say"], r["say"]
    h = B.health(T, r["model_id"])
    assert h["spaces"] == 1 and h["elements"] == 2 and h["without_placement"] == 0
    with pytest.raises(Exception) as ex:
        B.ifc_add(T, "Tower A", "pdf nonsense", "this is a pdf, not a model")
    assert "IFC (STEP) text nahi" in str(ex.value)
    with pytest.raises(Exception):
        B.health(T, "no-such-model")


def test_bim_naming_cde_transmit(cst):
    from app.construction import bim as B
    n = B.naming_check(["P01-ACME-ZZ-GF-STR-SM-0001.ifc", "final-final.ifc"])
    assert n["rows"][0]["verdict"] == "ok" and n["rows"][1]["missing"]
    c1 = B.cde_add(T, "Tower A", "P01-ACME-ZZ-GF-STR-SM-0001", "GA plan", "P01", "shared")
    assert c1["superseded"] == 0
    c2 = B.cde_add(T, "Tower A", "P01-ACME-ZZ-GF-STR-SM-0001", "GA plan", "P02", "wip")
    assert c2["superseded"] == 1, "same code, new rev supersedes"
    with pytest.raises(Exception):
        B.cde_add(T, "Tower A", "x", "y", "", "published-but-wrong-status")
    tr = B.transmit(T, "Tower A", ["P01-ACME-ZZ-GF-STR-SM-0001"], "Structural consultant")
    assert tr["codes"] and tr["day"] == DAY.isoformat()


def test_bim_clash_bcf_and_ids(cst):
    from app.construction import bim as B
    # one wall alone: no pair to check; the space is spatial, not clash-scanned
    r = B.ifc_add(T, "Tower A", "struct v1", _ifc(n_walls=1))
    scan = B.clash_scan(T, r["model_id"], clearance_m=0.0)
    assert scan["boxes"] == 1 and scan["candidates"] == 0 and scan["not_checkable"] == 0
    # two walls at the SAME placement -> one AABB candidate
    r2 = B.ifc_add(T, "Tower A", "struct clash", _ifc(n_walls=2, step=0.0))
    scan2 = B.clash_scan(T, r2["model_id"])
    assert scan2["candidates"] == 1, scan2
    cid = _first_clash_id(r2["model_id"])
    mark = B.clash_mark(T, cid, "assigned", "Ravi (BIM coordinator)")
    assert "assigned" in mark["say"]
    with pytest.raises(Exception) as ex:
        B.clash_mark(T, cid, "resolved", "")
    assert "naam" in str(ex.value)
    bcf = B.bcf_export(T, r2["model_id"])
    assert bcf["topics"] == 1 and bcf["file"]["name"].endswith(".bcf")
    with pytest.raises(Exception):
        B.bcf_export(T, r["model_id"])              # no open candidates -> honest refusal
    ids = B.ids_check(T, r2["model_id"], IDS_XML)
    specs = ids["specs"]
    assert specs[0]["pass"] == 2 and specs[0]["fail"] == 0    # both walls carry Length
    assert specs[1]["fail"] == 2      # FireRating absent on every element -> fail, never a pass
    assert "UNVERIFIED" in ids["say"] or "subset" in ids["say"]


def test_bcf_zip_structure(cst):
    from app.construction import bim as B
    r = B.ifc_add(T, "Tower A", "bcf zip", _ifc(n_walls=2, step=0.0))
    B.clash_scan(T, r["model_id"])
    from sqlalchemy import select
    from app.db import session
    from app.construction.models import CBimClash, CBimModel
    with session() as s:
        m = s.get(CBimModel, r["model_id"])
        rows = s.scalars(select(CBimClash).where(CBimClash.model_id == r["model_id"])).all()
    data = B._bcf_zip(m, rows)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert "project.bcfp" in z.namelist() and "markup.xml" in z.namelist()
        markup = z.read("markup.xml").decode()
        assert "<Topic " in markup and 'TopicType="Clash"' in markup and "Version=\"2.1\"" in markup
        assert "the BIM coordinator decides" in markup


def _first_clash_id(model_id: str) -> str:
    from sqlalchemy import select
    from app.db import session
    from app.construction.models import CBimClash
    with session() as s:
        return s.scalars(select(CBimClash).where(CBimClash.tenant_id == T,
                                                 CBimClash.model_id == model_id)).first().id


def test_bim_4d_5d(cst):
    from app.construction import bim as B
    r = B.ifc_add(T, "Tower A", "v5d", _ifc(n_walls=1))
    lk = B.link4d(T, r["model_id"], "Ground floor walls", "class", "IFCWALL", "2026-11-01", "2026-11-10")
    assert lk["elements"] == 1
    rep = B.report4d(T, r["model_id"])
    assert rep["links"][0]["activity"] == "Ground floor walls"
    with pytest.raises(Exception) as ex:
        B.qty5d(T, r["model_id"])
    assert "IfcElementQuantity" in str(ex.value)    # no Volume/Area -> honest refusal, no invented qty
    r2 = B.ifc_add(T, "Tower A", "v5d-with-vol", _ifc(n_walls=1, with_volume=True))
    q = B.qty5d(T, r2["model_id"])
    assert q["taken"] == 1 and abs(q["rows"][0]["qty"] - round(6.0 * 0.23 * 3.0, 3)) < 1e-9
    assert q["rows"][0]["source_ref"].startswith("IFC IfcQuantityVolume")
    with pytest.raises(Exception) as ex:
        B.cost5d(T, q["rows"][0]["takeoff_id"], 8500.0, "")
    assert "SOURCE" in str(ex.value)
    cost = B.cost5d(T, q["rows"][0]["takeoff_id"], 8500.0, "SOR 2.4")
    assert cost["amount"] == round(q["rows"][0]["qty"] * 8500.0, 2)


# ---------------------------------------------------------------- C12: pre-design
def test_predesign_structural(cst):
    from app.construction import predesign as P
    r = P.slab_load(T, "Tower A", "Slab GF", "residential", 0.15, 1.5)
    assert r["dl_kn_m2"] == round(0.15 * 25.0 + 1.5, 3) and r["total_kn_m2"] == r["dl_kn_m2"] + 2.0
    assert "IS 875" in r["say"] or "PRELIMINARY" in r["say"]
    with pytest.raises(Exception):
        P.slab_load(T, "Tower A", "x", "cinema", 0.15)       # occupancy not in the pack -> refuse
    cl = P.column_load(T, "Tower A", "C1", 25.0, 8, 12.5, beam_add_kn=40.0)
    assert cl["pu_kn"] == round(25.0 * 8 * 12.5 + 40.0, 2)
    cs = P.column_size(T, "Tower A", "C1", 1500.0, 20.0, 500.0, 1.0)
    ac = 1500.0 / (0.4 * 20.0 + 0.67 * 500.0 * 0.01)          # cl 39.3, p = 1%
    side = -(-int(ac ** 0.5 * 1000) // 50) * 0                  # placeholder replaced below
    import math as _m
    side = _m.ceil(_m.sqrt(ac) / 50.0) * 50
    assert cs["ac_mm2"] == round(ac, 0) and cs["side_mm"] == side and cs["side_mm"] % 50 == 0
    assert "PRELIMINARY" in cs["say"] and "short, braced" in cs["say"]
    bd = P.beam_depth(T, "Tower A", "B1", 6.0, "simply_supported", 350.0)
    assert bd["depth_min_mm"] == 300.0 and bd["verdict"] == "ok"
    bd2 = P.beam_depth(T, "Tower A", "B2", 5.0, "continuous")     # no depth fed -> the min is the paper
    assert bd2["verdict"] == "no_depth_fed" and bd2["depth_min_mm"] == round(5000 / 26, 0)
    with pytest.raises(Exception) as ex:
        P.beam_depth(T, "Tower A", "B3", 12.0, "simply_supported", 700.0)
    assert "modification factors" in str(ex.value)          # > 10 m is the engineer's, never guessed


def test_predesign_mep_fire(cst):
    from app.construction import predesign as P
    e = P.mep_elec(T, "Tower A", "Feeder 1", 120.0, 0.65, 0.9, 0.8)
    assert e["kva"] == round(120 * 0.65 * 0.9 / 0.8, 2)
    w = P.mep_water(T, "Tower A", "Domestic", 250)
    assert w["kld"] == round(250 * 135 / 1000, 2) and "135" in w["say"]   # CPHEEO row cited in the store
    with pytest.raises(Exception) as ex:
        P.mep_hvac(T, "Tower A", "Lobby", 500.0, 0.15, "")
    assert "SOURCE" in str(ex.value)
    h = P.mep_hvac(T, "Tower A", "Lobby", 500.0, 0.15, "consultant note 12 Oct")
    assert h["tr"] == 75.0
    with pytest.raises(Exception) as ex:
        P.rule_add(T, "fire", "travel_max", "travel distance", 30.0, "m", "max", "", "guess")
    assert "Clause aur source" in str(ex.value)
    P.rule_add(T, "fire", "travel_max", "max travel distance to exit", 30.0, "m", "max",
               "NBC 2016 Part 4 cl 4.4", "fire consultant row (re-check)")
    ok = P.fire_check(T, "Tower A", "travel_max", 28.0)
    assert ok["verdict"] == "ok" and ok["margin"] == 2.0
    bad = P.fire_check(T, "Tower A", "travel_max", 35.0)
    assert bad["verdict"] == "breach" and "consultant" in bad["say"]
    with pytest.raises(Exception) as ex:
        P.fire_check(T, "Tower A", "no_such_fire_rule", 10.0)
    assert "rule_add" in str(ex.value)
    with pytest.raises(Exception) as ex:
        P.fire_demand(T, "Tower A", "Sprinkler", 0.2, 2000.0, 60)
    assert "SOURCE" in str(ex.value)
    fd = P.fire_demand(T, "Tower A", "Sprinkler", 0.2, 2000.0, 60, 450.0, "NBC hazard OH1 row")
    assert fd["lpm"] == 850.0 and fd["litres"] == 51000.0
    d = P.day(T)
    assert d["calcs"].get("fire_check") == 2 and "PRELIMINARY" in d["say"]


# ---------------------------------------------------------------- C13a: survey
def test_survey_points_traverse_area(cst):
    from app.construction import survey as S
    job = S.pts_add(T, "Shivneri", "Plot survey", "coords",
                    "P1,0,0,10\nP2,10,0,11\nP3,10,10,10.5\nP4,0,10,10.2")
    assert job["points"] == 4
    lx = S.pts_add(T, "Shivneri", "LandXML job", "landxml",
                   '<CgPoints><CgPoint name="L1">100.0 200.0 0.0</CgPoint>'
                   '<CgPoint name="L2">110.0 200.0 0.0</CgPoint></CgPoints>')
    assert lx["points"] == 2
    with pytest.raises(Exception):
        S.pts_add(T, "Shivneri", "bad", "coords", "garbage without numbers")
    tr = S.traverse(T, "Shivneri", job["job_id"], ["P1", "P2", "P3", "P4", "P1"])
    assert tr["closing_error_m"] == 0.0 and tr["perimeter_m"] == 40.0
    tr2 = S.traverse(T, "Shivneri", job["job_id"], ["P1", "P2", "P3", "P4"])
    assert tr2["closing_error_m"] == 10.0 and tr2["perimeter_m"] == 40.0  # loop: closing leg implied
    assert tr2["precision"] == "1 in 4"
    ar = S.area_shoelace(T, "Shivneri", job["job_id"], ["P1", "P2", "P3", "P4"])
    assert ar["area_m2"] == 100.0 and ar["area_ha"] == 0.01
    with pytest.raises(Exception) as ex:
        S.area_shoelace(T, "Shivneri", job["job_id"], ["P1", "P2", "P3", "P4"], record_m2=98.0)
    assert "SOURCE" in str(ex.value)
    bd = S.area_shoelace(T, "Shivneri", job["job_id"], ["P1", "P2", "P3", "P4"], record_m2=98.0,
                         record_source="7/12 no 112", tolerance_pct=2.0)
    assert bd["verdict"] == "exceeds" and bd["diff_pct"] == round(2.0 / 98.0 * 100.0, 3)
    with pytest.raises(Exception):
        S.traverse(T, "Shivneri", job["job_id"], ["P1", "P9"])


def test_survey_volume_deviation_carpet(cst):
    from app.construction import survey as S
    vol = S.volume_grid(T, "Shivneri", "Cut Q1", [10.0, 9.0, 11.0, 8.5], 10.0, 4.0)
    assert vol["cut_m3"] == 4.0 and vol["fill_m3"] == 10.0 and vol["net_m3"] == -6.0
    dev = S.deviations(T, "Shivneri", "Scan 1",
                       [[0, 0, 10.0, 0, 0, 10.0], [1, 1, 10.02, 1, 1, 10.0], [2, 2, 10.10, 2, 2, 10.0]], 25.0)
    assert dev["points"] == 3 and dev["out_of_tolerance"] == 1 and dev["rms_mm"] == round(
        (0.0 + 20.0 ** 2 + 100.0 ** 2) ** 0.5 / 3 ** 0.5, 1)
    with pytest.raises(Exception):
        S.deviations(T, "Shivneri", "Scan 2", [[0, 0, 10.0]], 25.0)
    with pytest.raises(Exception) as ex:
        S.carpet_new(T, "Shivneri", "A-402", "")
    assert "Wall policy" in str(ex.value)
    cp = S.carpet_new(T, "Shivneri", "A-402", "internal walls included at 100 mm", 30.0, "agreement page 4")
    S.carpet_room(T, cp["carpet_id"], "Living", 4.0, 3.5)
    S.carpet_room(T, cp["carpet_id"], "Bed 1", 3.6, 3.2)
    S.carpet_room(T, cp["carpet_id"], "Kitchen", 2.4, 2.1)
    calc = S.carpet_calc(T, cp["carpet_id"])           # tolerance from the MahaRERA pack row (3%)
    assert calc["computed_m2"] == 30.56
    assert calc["verdict"] == "within"                 # |30.56 - 30| / 30 = 1.867% < 3%
    assert calc["diff_pct"] == round(0.56 / 30.0 * 100.0, 3) == 1.867
    assert calc["tolerance_pct"] == 3.0
    pk = S.carpet_pack(T, cp["carpet_id"])
    assert pk["file"]["name"].endswith(".pdf") or pk["file"].get("name", "").endswith(".pdf")


def test_carpet_exceeds_and_pack(cst):
    from app.construction import survey as S
    cp = S.carpet_new(T, "Shivneri", "B-101", "external walls excluded, internal included", 40.0, "agn")
    S.carpet_room(T, cp["carpet_id"], "Room", 6.0, 5.0)     # 30.0 vs declared 40.0 = 25% -> exceeds
    calc = S.carpet_calc(T, cp["carpet_id"])
    assert calc["verdict"] == "exceeds" and calc["diff_pct"] == 25.0
    pk = S.carpet_pack(T, cp["carpet_id"])
    assert "sign" in pk["say"] or "khaali" in pk["say"]


# ---------------------------------------------------------------- C13b: delay
def test_delay_flow(cst):
    from app.construction import delay as D
    with pytest.raises(Exception):
        D.prog_add(T, "Shivneri", "baseline", [{"activity": "FO", "start": "nope", "finish": "2026-02-01"}])
    D.prog_add(T, "Shivneri", "baseline", [
        {"activity": "Foundations", "start": "2026-01-01", "finish": "2026-02-01", "critical": True},
        {"activity": "GF slab", "start": "2026-02-01", "finish": "2026-03-01"}])
    D.prog_add(T, "Shivneri", "asbuilt", [
        {"activity": "Foundations", "start": "2026-01-01", "finish": "2026-02-20"},
        {"activity": "GF slab", "start": "2026-02-21", "finish": "2026-03-01"}])
    D.window_add(T, "Shivneri", "Monsoon W1", "2026-01-01", "2026-03-01")
    imp = D.impact(T, "Shivneri")
    assert imp["rows"][0]["slip_days"] == 19 and imp["rows"][0]["critical_her_mark"] is True
    assert imp["critical_slipped"] == 1 and imp["windows"] == ["Monsoon W1"]
    nc = D.notice_check(T, "Shivneri", "rain halt", "2026-07-01", "2026-07-08", 10, "Cl 20.1")
    assert nc["verdict"] == "in-window" and nc["taken_days"] == 7
    late = D.notice_check(T, "Shivneri", "steel delay", "2026-07-01", "2026-07-25", 10, "Cl 20.1")
    assert late["verdict"] == "late" and "14" in late["say"]
    pre = D.notice_check(T, "Shivneri", "odd", "2026-07-10", "2026-07-01", 10, "Cl 20.1")
    assert pre["verdict"] == "pre-dated"
    with pytest.raises(Exception) as ex:
        D.notice_check(T, "Shivneri", "x", "2026-07-01", "2026-07-08", 10, "")
    assert "reference" in str(ex.value)
    pk = D.pack(T, "Shivneri", "S. Joshi (forensic planner)")
    assert pk["file"]["name"].endswith(".pdf") and "counsel" in pk["say"] or "entitlement" in pk["say"]


# ---------------------------------------------------------------- C15: green
def test_green_energy_desk(cst):
    from app.construction import green as G
    G.meter_add(T, "Site A", "M1", 1200, "2026-10-01")
    G.meter_add(T, "Site A", "M1", 1300, "2026-11-01")
    with pytest.raises(Exception):
        G.tariff_add(T, "X", [{"from_kwh": 0, "to_kwh": 100, "rate": 4.0}], "")   # no source
    G.tariff_add(T, "MSEDCL", [{"from_kwh": 0, "to_kwh": 100, "rate": 4.0, "fixed_rs": 90},
                               {"from_kwh": 100, "to_kwh": 0, "rate": 7.0, "fixed_rs": 120}], "Oct bill")
    b = G.bill(T, "MSEDCL", 250)
    assert b["total_rs"] == round(100 * 4.0 + 150 * 7.0 + 90 + 120, 2)
    with pytest.raises(Exception) as ex:
        G.benchmark(T, "Site A", 100, 2.0, "")
    assert "SOURCE" in str(ex.value)
    bm = G.benchmark(T, "Site A", 100, 12.5, "her 2025 data")
    assert bm["epi_kwh_m2_mo"] == 12.5 and bm["vs_benchmark_pct"] == 0.0


def test_green_rules_carbon_water(cst):
    from app.construction import green as G
    with pytest.raises(Exception):
        G.rule_add(T, "ecbc", "wwr", "WWR max", 40.0, "%", "max", "", "memory")
    G.rule_add(T, "ecbc", "ecbc_wwr_max", "WWR max", 40.0, "%", "max", "ECBC 2017 Table 3.2", "her ECBC row")
    assert G.check(T, "P", "ecbc_wwr_max", 35.0)["verdict"] == "ok"
    assert G.check(T, "P", "ecbc_wwr_max", 45.0)["verdict"] == "breach"
    dl = G.daylight(T, "P", "Class 1", 6.0, 40.0, "ecbc_wwr_max")
    assert dl["wfr_pct"] == 15.0
    mi = G.model_inputs(T, "P", [{"param": "U-wall", "value": 0.44, "unit": "W/m2K", "source": "EPD wall"}])
    assert mi["rows"][0]["source"] == "EPD wall" and "EnergyPlus" in mi["say"]
    with pytest.raises(Exception):
        G.model_inputs(T, "P", [{"param": "x", "value": 1}])
    with pytest.raises(Exception):
        G.carbon_add(T, "P", "cement", 100, "t", 250.0, "")     # factor without source
    G.carbon_add(T, "P", "cement", 200, "t", 250.0, "EPD-123")
    G.carbon_add(T, "P", "steel", 50, "t", 1800.0, "EPD-456")
    hs = G.carbon_hotspots(T, "P")
    assert hs["total_kgco2e"] == 140000.0 and hs["rows"][0]["material"] == "steel"
    assert hs["rows"][0]["share_pct"] == round(90000 / 140000 * 100, 1)
    wd = G.water_demand(T, "P", "Domestic", 100)
    assert wd["kld"] == 13.5 and "CPHEEO" in wd["is_ref"]
    with pytest.raises(Exception):
        G.rwh(T, "P", "RWH", 500, 0.9, 1000, "")
    rw = G.rwh(T, "P", "RWH", 500, 0.9, 1000, "IMD Pune 2025")
    assert rw["harvest_m3_yr"] == 450.0 and "IMD Pune" in rw["say"]


def test_green_credits_cx_tc_mv(cst):
    from app.construction import green as G
    with pytest.raises(Exception):
        G.credit_add(T, "P", "BREEAM", "x", 2, 1)
    G.credit_add(T, "P", "IGBC", "Site selection", 2, 2, "ev-1")
    G.credit_add(T, "P", "IGBC", "Water efficiency", 3, 1)
    with pytest.raises(Exception):
        G.credit_add(T, "P", "IGBC", "Over-claim", 1, 5)
    sc = G.credits_score(T, "P")
    assert sc["ratings"]["IGBC"]["claimed"] == 3.0 and sc["ratings"]["IGBC"]["pct"] == 60.0
    assert "assessor" in sc["say"]
    cx = G.cx_add(T, "P", "Chiller", "Flow test", ["start", "read", "compare"], "first")
    with pytest.raises(Exception):
        G.cx_add(T, "P", "Chiller", "Empty", [])
    green_issue = G.cx_issue(T, cx["cx_id"], "major", "flow low")
    assert green_issue["issue_id"]
    G.cx_status(T, cx["cx_id"], "failed")
    ok = G.tc_add(T, "P", "AHU", "TC-9", "TUV", "2026-11-01", 96.0, 100.0, 5.0, "l/s")
    assert ok["verdict"] == "ok" and ok["dev_pct"] == 4.0
    bad = G.tc_add(T, "P", "Pump", "TC-10", "SGS", "2026-11-02", 120.0, 100.0, 5.0, "l/s")
    assert bad["verdict"] == "exceeds"
    with pytest.raises(Exception):
        G.mv_add(T, "P", "E", [{"driver": 1, "kwh": 10}], [{"driver": 1, "kwh": 9}])
    mv = G.mv_add(T, "P", "C", [{"driver": 10, "kwh": 1100}, {"driver": 12, "kwh": 1300},
                                {"driver": 14, "kwh": 1500}], [{"driver": 11, "kwh": 1000}])
    sv = G.mv_savings(T, mv["mv_id"])
    assert abs(sv["b"] - 100.0) < 1e-6 and abs(sv["a"] - 100.0) < 1e-6 and sv["r2"] == 1.0
    assert sv["per_period"][0]["savings_kwh"] == 200.0 and sv["warn"] == ""
    weak = G.mv_add(T, "P", "C", [{"driver": 10, "kwh": 1000}, {"driver": 12, "kwh": 990},
                                  {"driver": 14, "kwh": 1010}], [{"driver": 11, "kwh": 1000}])
    sv2 = G.mv_savings(T, weak["mv_id"])
    assert sv2["warn"] and "Model weak" in sv2["warn"]
    d = G.day(T)
    assert "tc_exceeds" in d and d["cx_issues_open"] == 1 and d["credits_without_evidence"] >= 1


# ---------------------------------------------------------------- #82: incidents on the quality desk
def test_incident_flow(cst):
    from app.construction import quality as Q
    inc = Q.incident_open(T, "Tower B", "injury", "minor", "Worker slipped on the stair landing",
                          reported_by="Ganesh")
    q = Q.incident_questions()
    assert len(q["questions"]) == 6 and "safety head" in q["say"]
    Q.incident_row(T, inc["incident_id"], "timeline", "10:12 slip heard", at="10:12")
    Q.incident_row(T, inc["incident_id"], "witness", "Was carrying tiles, no handrail feel")
    Q.incident_row(T, inc["incident_id"], "why", "Why did he slip?", answer="Wet surface")
    Q.incident_row(T, inc["incident_id"], "action", "Fix landing drainage", owner="Site engineer",
                   due="2026-11-10")
    with pytest.raises(Exception) as ex:
        Q.incident_close(T, inc["incident_id"], "wet surface + missing drainage slope", "")
    assert "NAAM" in str(ex.value)                      # no findings without the safety head's name
    with pytest.raises(Exception) as ex:
        Q.incident_close(T, inc["incident_id"], "", "Meera (safety head)")
    assert "Root cause" in str(ex.value)
    with pytest.raises(Exception) as ex:
        Q.incident_close(T, inc["incident_id"], "wet surface", "Meera (safety head)")
    assert "corrective action" in str(ex.value)          # open actions block the close
    d = Q.day(T)
    assert d["incidents_open"] == 1


def test_incident_close_and_pack(cst):
    from app.construction import quality as Q
    inc = Q.incident_open(T, "Tower B", "near_miss", "minor", "Crane load swung near workers")
    Q.incident_row(T, inc["incident_id"], "action", "Re-brief rigger", owner="Rigging lead", due="2026-11-06",
                   status="done")
    cl = Q.incident_close(T, inc["incident_id"], "tag line not used", "Meera (safety head)")
    assert "Meera (safety head)" in cl["say"]
    with pytest.raises(Exception):
        Q.incident_row(T, inc["incident_id"], "timeline", "late note")   # closed = no new rows
    pk = Q.incident_pack(T, inc["incident_id"])
    assert pk["file"]["name"].endswith(".pdf") and pk["status"] == "closed"


# ---------------------------------------------------------------- the tool layer
def test_registry_579_and_dispatch(env):
    from app.agent.tools import HANDLERS, TOOLS, TOOL_LABELS
    names = {t["name"] for t in TOOLS}
    for n in ("const_bim", "const_bim_dekho", "const_predesign", "const_predesign_dekho", "const_survey",
              "const_survey_dekho", "const_delay", "const_delay_dekho", "const_green", "const_green_dekho"):
        assert n in names and n in HANDLERS and n in TOOL_LABELS, n
    assert len(TOOLS) == 629, "626 + 1 app_engine (v0.824 APP ENGINE 1: the Web Studio React app lane - one new tool). 625 + 1 hoola_design (v0.817.0 HOOLA DESIGN: the design editor's one tool). 624 + 1 ai_app (v0.785 HOOLA AI APPS). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " "581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 570 (their 0.559 base) + 10 construction Wave 3 + 1 speckit (v0.569 SPEC SUTRA)"


def test_bim_tool_end_to_end(env):
    from tests.test_life import conv_ctx
    from app.agent.const_bim_tools import BIM_HANDLERS
    ctx = conv_ctx()
    r = asyncio.run(BIM_HANDLERS["const_bim"](ctx, "ifc_add", project="Tower A", name="arch",
                                              ifc_text=_ifc(n_walls=1)))
    assert r["schema"] == "IFC4" and r["model_id"]
    h = asyncio.run(BIM_HANDLERS["const_bim_dekho"](ctx, "health", model=r["model_id"]))
    assert h["spaces"] == 1
    nm = asyncio.run(BIM_HANDLERS["const_bim"](ctx, "naming", filenames=["P01-A-ZZ-GF-STR-SM-0001.ifc"]))
    assert nm["violations"] == 0


def test_predesign_survey_delay_green_tools_end_to_end(env):
    from tests.test_life import conv_ctx
    from app.agent.const_delay_tools import DELAY_HANDLERS
    from app.agent.const_green_tools import GREEN_HANDLERS
    from app.agent.const_predesign_tools import PREDESIGN_HANDLERS
    from app.agent.const_survey_tools import SURVEY_HANDLERS
    ctx = conv_ctx()
    r = asyncio.run(PREDESIGN_HANDLERS["const_predesign"](ctx, "slab_load", project="A", name="S1",
                                                          occupancy="office", thickness_m=0.15))
    assert r["total_kn_m2"] == round(3.0 + 0.15 * 25.0 + 1.0, 3)
    with pytest.raises(Exception) as ex:
        asyncio.run(PREDESIGN_HANDLERS["const_predesign"](ctx, "mep_hvac", project="A", name="H",
                                                          area_m2=100, tr_per_m2=0.1, source=""))
    assert "SOURCE" in str(ex.value)
    job = asyncio.run(SURVEY_HANDLERS["const_survey"](ctx, "pts_add", project="P", name="J1",
                                                      source_kind="coords", text="a,0,0,1\nb,10,0,2\nc,10,10,3"))
    ar = asyncio.run(SURVEY_HANDLERS["const_survey"](ctx, "area", project="P", job=job["job_id"],
                                                     order=["a", "b", "c", "a"]))
    assert ar["area_m2"] == 50.0
    d1 = asyncio.run(DELAY_HANDLERS["const_delay"](ctx, "prog_add", project="P", kind="baseline",
                                                   rows=[{"activity": "A", "start": "2026-01-01",
                                                          "finish": "2026-02-01", "critical": True}]))
    assert d1["rows"] == 1
    asyncio.run(DELAY_HANDLERS["const_delay"](ctx, "prog_add", project="P", kind="asbuilt",
                                              rows=[{"activity": "A", "start": "2026-01-01",
                                                     "finish": "2026-02-05"}]))
    imp = asyncio.run(DELAY_HANDLERS["const_delay_dekho"](ctx, "impact", project="P"))
    assert "rows" in imp and imp["rows"][0]["slip_days"] == 4
    asyncio.run(GREEN_HANDLERS["const_green"](ctx, "meter_add", site="S", meter="M1", kwh=100))
    tar = asyncio.run(GREEN_HANDLERS["const_green"](ctx, "tariff_add", name="T", source="bill",
                                                    rows=[{"from_kwh": 0, "to_kwh": 0, "rate": 5.0}]))
    b = asyncio.run(GREEN_HANDLERS["const_green"](ctx, "bill", name="T", kwh_month=80))
    assert b["total_rs"] == 400.0


def test_voice_via_kaam_and_hub_rows(env):
    from app.voice import VOICE_VIA_KAAM
    for n in ("const_bim", "const_bim_dekho", "const_predesign", "const_predesign_dekho", "const_survey",
              "const_survey_dekho", "const_delay", "const_delay_dekho", "const_green", "const_green_dekho"):
        assert n in VOICE_VIA_KAAM, n
    from app.employee import hire
    from app.employee.hire import CATALOG, CONST_GROUP
    keys = ["const_bim", "const_predesign", "const_survey", "const_delay", "const_green"]
    for k in keys:
        assert CATALOG[k]["live"] and CATALOG[k]["group"] == CONST_GROUP, k
        assert CATALOG[k]["never"] and CATALOG[k]["does"]
    assert any("IFC" in x for x in CATALOG["const_bim"]["never"])
    assert any("entitlement" in x for x in CATALOG["const_delay"]["never"])
    hire.ensure_table()
    r = hire.hire(T, "const_bim")
    assert r["key"] == "const_bim" and "const_bim" in hire.hired_keys(T)
    cat = hire.catalog(T)
    const_rows = [c for c in cat if c["group"] == CONST_GROUP]
    assert len(const_rows) >= 16          # 11 from Waves 1-2 + 5 Wave 3 (+ the two re-parented originals)


def test_version_pins():
    from pathlib import Path
    REPO = Path(__file__).resolve().parents[2]
    from app.main import APP_VERSION
    assert APP_VERSION == "0.872.0"
    assert 'APP_VERSION = "0.872.0"' in (REPO / "server" / "app" / "main.py").read_text()
    assert "version: 0.872.0+871" in (REPO / "pubspec.yaml").read_text()
