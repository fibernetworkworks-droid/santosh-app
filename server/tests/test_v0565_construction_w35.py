"""v0.565.0 Construction Wave 3.5 - the five Wave-3 stragglers homed (owner: 'GO WAVE 3.5'; plan
docs/CONSTRUCTION_EMPLOYEE_PLAN.md §7; register ids 25, 27, 74, 77, 109 per §5's original mapping).
#25 as-built set register (const_bim): HER required list, marks by name, completeness arithmetic,
approval reserved (tier C). #27 GIS (const_survey): GeoJSON rings read as text, areas ONLY in
projected metres (degree layers REFUSE - a degree has no square metres), overlay values recorded as
HER readings, maps never fetched. #74 formwork & scaffold (const_predesign): contact area by
geometry on HER dims, striking time vs the IS 456 cl 11.3 Table 10 pack rows (OPC + ambient > 15
degC ONLY - outside scope refused), props vs the supplier table's allowable (source required),
scaffold tag register by name, striking order + tag reserved (tier C). #77 setting-out
(const_survey): design sheets, as-laid vs design plan deviations, level checks with the sign kept.
#109 digital twin (const_bim): the DATA-LINK register asset -> IFC GUID, sensor feed rows with
sourced bands flagged, COBie Component CSV check; the twin is a register, never a live 3D view.
Plus: 7 IS 456 Table 10 rows join the national pack (11 -> 18), three new tier-C rows (33 total),
registry STILL 580 (no new tools - the three desks grew actions), VOICE_VIA_KAAM unchanged, Hub rows
carry the new lines, version pins."""
import asyncio
from datetime import date

import pytest

T = "default"
DAY = date(2026, 11, 5)


@pytest.fixture
def cst(env, monkeypatch):
    from app import config
    from app.construction import bim as B
    from app.construction import common
    from app.construction import predesign as P
    from app.construction import survey as S
    monkeypatch.setattr(common, "today", lambda t: DAY)
    for mod in (B, P, S):
        monkeypatch.setattr(mod, "today", lambda t: DAY)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


# ---------------------------------------------------------------- register + gates
def test_register_wave35(env):
    from app.construction import register as R
    assert R.WAVE35_IDS == [25, 27, 74, 77, 109]
    w = R.wave("3.5")
    assert len(w) == 5 and {r["id"] for r in w} == set(R.WAVE35_IDS)
    assert set(R.WAVE35_HOME) == set(R.WAVE35_IDS)
    for rid in R.WAVE35_IDS:
        assert R.WAVE35_HOME[rid], rid
    assert "const_bim" in R.WAVE35_HOME[25] and "as-built" in R.WAVE35_HOME[25]
    assert "const_survey" in R.WAVE35_HOME[27] and "const_survey" in R.WAVE35_HOME[77]
    assert "const_predesign" in R.WAVE35_HOME[74] and "const_bim" in R.WAVE35_HOME[109]
    assert R.get(25)["wave"] == "3.5" and R.get(109)["tier"] == "B"
    assert len(R.wave("3")) == 23          # Wave 3 unchanged
    st = R.stats()
    assert st["by_wave"]["3.5"] == 5


def test_gates_wave35(env):
    from app.construction.gates import TIER_C, tier_c_check
    assert len(TIER_C) == 33, "30 before Wave 3.5 + as-built / striking / scaffold"
    for ask in ("approve the as-built set before handover", "order formwork striking tomorrow",
                "tag a scaffold safe for use"):
        assert tier_c_check(ask), ask
    # the Wave-3 refusals still ride
    assert tier_c_check("certify a survey for the court")
    assert tier_c_check("certify an area statement")


def test_india_pack_18_rows_with_strike(env):
    from app.construction import statepacks as SP
    pack = SP.load("india")
    assert len(pack["rows"]) == 18, "11 national rows + 7 IS 456 Table 10 striking rows (Wave 3.5)"
    r = SP.rule_cited("india", "is456_strike_slab_soffit")
    assert float(r["value"]) == 72.0 and "Table 10" in r["source"]
    assert "OPC" in r["source"]
    for rid, mn in (("is456_strike_vertical", 16.0), ("is456_strike_beam_soffit", 168.0),
                    ("is456_strike_props_beam_gt6m", 504.0)):
        assert float(SP.rule_value("india", rid, 0.0)) == mn, rid


# ---------------------------------------------------------------- #25 as-built (const_bim)
def test_asbuilt_flow(cst):
    from app.construction import bim as B
    st = B.asbuilt_set(T, "Palm Heights", "Handover set A",
                       ["AB-STR-001 | Structural as-built", "AB-MEP-001", "AB-ARC-001"])
    sid = st["set_id"]
    assert st["required"] == 3
    with pytest.raises(B.CstError) as ex:            # the name law
        B.asbuilt_mark(T, sid, "AB-STR-001", "received", by="")
    assert "naam" in str(ex.value)
    B.asbuilt_mark(T, sid, "ab-str-001", "received", by="S. Deshmukh")   # code match is case-free
    B.asbuilt_mark(T, sid, "AB-MEP-001", "na", by="S. Deshmukh", note="design-build package")
    chk = B.asbuilt_check(T, sid)
    assert chk["required"] == 3 and chk["received"] == 1 and chk["na"] == 1 and chk["pending"] == 1
    assert chk["completeness_pct"] == 50.0 and chk["missing"] == ["AB-ARC-001"]
    with pytest.raises(B.CstError):
        B.asbuilt_mark(T, sid, "NO-SUCH-CODE", "received", by="X")
    assert "site architect" in chk["say"] and "tier C" in chk["say"]


# ---------------------------------------------------------------- #27 GIS (const_survey)
_GEO_M = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [
        [[5000.0, 2000.0], [5100.0, 2000.0], [5100.0, 2100.0], [5000.0, 2100.0], [5000.0, 2000.0]]]}},
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [
        [[6000.0, 2000.0], [6050.0, 2000.0], [6050.0, 2040.0], [6000.0, 2040.0], [6000.0, 2000.0]],
        [[6010.0, 2010.0], [6020.0, 2010.0], [6020.0, 2020.0], [6010.0, 2010.0], [6010.0, 2020.0]]]}}]}

_GEO_DEG = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [
    [[73.85, 18.52], [73.86, 18.52], [73.86, 18.53], [73.85, 18.53], [73.85, 18.52]]]}}


def test_gis_flow(cst):
    import json
    from app.construction import survey as S
    lay = S.gis_add(T, "Palm Heights", "plot boundary UTM43N", json.dumps(_GEO_M),
                    crs="EPSG:32643 (UTM 43N)", units="m")
    lid = lay["layer_id"]
    assert lay["polygons"] == 2 and lay["vertices"] == 15 and lay["holes"] == 1
    ar = S.gis_area(T, lid)
    assert ar["area_m2"] == 12000.0            # 100x100 + 50x40 = 10000 + 2000, outer rings only
    assert ar["holes_not_subtracted"] == 1
    ar2 = S.gis_area(T, lid, record_m2=12100.0, record_source="7/12 record 2024")
    assert ar2["diff_pct"] == round(abs(12000.0 - 12100.0) / 12100.0 * 100.0, 3) and ar2["verdict"] == "within"
    deg = S.gis_add(T, "Palm Heights", "plot WGS84", json.dumps(_GEO_DEG))     # no units -> deg
    assert deg["units"] == "deg"
    with pytest.raises(S.CstError) as ex:      # THE refusal: degrees have no square metres
        S.gis_area(T, deg["layer_id"])
    assert "shoelace" in str(ex.value) and "GALAT" in str(ex.value)
    with pytest.raises(S.CstError):
        S.gis_overlay(T, "Palm Heights", lid, "flood", "zone III", source="")
    ov = S.gis_overlay(T, "Palm Heights", lid, "flood", "Zone III per map sheet", source="NDMA atlas, read by planner")
    assert ov["overlay_id"]
    with pytest.raises(S.CstError):
        S.gis_add(T, "Palm Heights", "bad", "{not json")


# ---------------------------------------------------------------- #77 setting-out (const_survey)
def test_setout_and_levels(cst):
    from app.construction import survey as S
    sh = S.setout_add(T, "Palm Heights", "Grid setting out",
                      ["A1,0,0,100.0", "A2,20,0,100.0", "B1,0,15,100.15", "B2,20,15,100.15"])
    jid = sh["job_id"]
    assert sh["points"] == 4
    chk = S.setout_check(T, "Palm Heights", jid,
                         ["A1,0,0", "A2,20,0.04", "B1,0,15", "X9,1,1"], tolerance_mm=25.0)
    assert chk["points"] == 3 and chk["out_of_tolerance"] == 1     # A2 staked 40 mm off
    assert chk["worst"][0]["point"] == "A2" and abs(chk["worst"][0]["dev_mm"] - 40.0) < 0.01
    assert chk["missing_in_sheet"] == ["X9"]
    lv = S.level_check(T, "Palm Heights", jid, ["A1,100.03", "A2,99.99", "B1,100.15"], tolerance_mm=25.0)
    assert lv["points"] == 3 and lv["out_of_tolerance"] == 1
    rows = {r["point"]: r for r in lv["rows"]}
    assert rows["A1"]["dz_mm"] == 30.0 and rows["A1"]["verdict"] == "out"    # sign kept: + up
    assert rows["A2"]["dz_mm"] == -10.0 and rows["A2"]["verdict"] == "ok"    # - down
    lv2 = S.level_check(T, "Palm Heights", jid, ["B2,100.20"], tolerance_mm=25.0)
    assert lv2["points"] == 1 and lv2["out_of_tolerance"] == 1 and lv2["rows"][0]["dz_mm"] == 50.0


# ---------------------------------------------------------------- #74 formwork (const_predesign)
def test_form_area(cst):
    from app.construction import predesign as P
    r = P.form_area(T, "Palm Heights", "Slump 3-7", [
        ["slab", 10.0, 8.0, 0.0, 1],        # soffit 80
        ["beam", 6.0, 0.3, 0.5, 2],         # (1.8 + 6.0) x 2 = 15.6
        ["column", 0.3, 0.3, 3.0, 4],       # 2 x 0.6 x 3 = 3.6 x 4 = 14.4
        ["wall", 5.0, 0.0, 3.0, 1],         # 2 x 5 x 3 = 30
    ])
    assert r["total_m2"] == 140.0
    by = {row["kind"]: row["area_m2"] for row in r["rows"]}
    assert by["slab"] == 80.0 and by["beam"] == 15.6 and by["column"] == 14.4 and by["wall"] == 30.0
    with pytest.raises(P.CstError):
        P.form_area(T, "Palm Heights", "bad", [["arch", 1, 2, 3, 1]])


def test_strike_check(cst):
    from app.construction import predesign as P
    ok = P.strike_check(T, "Palm Heights", "vertical", "opc", 35.0, 20.0)
    assert ok["verdict"] == "ok" and ok["min_h"] == 16.0
    short = P.strike_check(T, "Palm Heights", "slab_soffit", "opc", 30.0, 48.0)
    assert short["verdict"] == "short" and short["min_h"] == 72.0
    with pytest.raises(P.CstError) as ex:      # blending cement outside Table 10's scope
        P.strike_check(T, "Palm Heights", "vertical", "ppc", 30.0, 48.0)
    assert "OPC" in str(ex.value)
    with pytest.raises(P.CstError) as ex2:     # ambient <= 15 degC outside scope
        P.strike_check(T, "Palm Heights", "vertical", "opc", 12.0, 48.0)
    assert "15" in str(ex2.value)
    props = P.props_check(T, "Palm Heights", "tower props", 3.2, 4.5, "Acrow supplier table 2026")
    assert props["verdict"] == "ok"
    with pytest.raises(P.CstError):
        P.props_check(T, "Palm Heights", "tower props", 3.2, 4.5, "")
    over = P.props_check(T, "Palm Heights", "beam backs", 5.0, 4.5, "supplier table")
    assert over["verdict"] == "exceeds"


def test_scaffold_tags(cst):
    from app.construction import predesign as P
    with pytest.raises(P.CstError) as ex:      # the name law
        P.scaffold_tag(T, "Palm Heights", "SC-01", "ok", checked_by="")
    assert "NAAM" in str(ex.value)
    P.scaffold_tag(T, "Palm Heights", "SC-01", "ok", "M. Sayyed", next_check="2026-11-12")
    P.scaffold_tag(T, "Palm Heights", "SC-02", "defective", "M. Sayyed", note="tie rod missing")
    d = P.day(T)
    assert d["scaffold_tags"] == 2 and d["scaffold_defective"] == 1


# ---------------------------------------------------------------- #109 twin (const_bim)
def test_twin_and_cobie(cst):
    from app.construction import bim as B
    with pytest.raises(B.CstError):
        B.twin_asset(T, "Palm Heights", "CH-01", guid="")        # the LINK is the point
    tw = B.twin_asset(T, "Palm Heights", "CH-01", "0ChillerGUID000000000", name="Chiller 1",
                      kind="chiller", space="Basement")
    assert tw["twin_id"]
    rd = B.twin_read(T, "Palm Heights", [["CH-01", "supply_temp", 7.2], ["CH-01", "supply_temp", 9.8]],
                     unit="degC", band_min=6.0, band_max=8.0, band_source="OEM design sheet")
    assert rd["rows"] == 2 and rd["out_of_band"] == 1
    with pytest.raises(B.CstError) as ex:      # band without a source refuses
        B.twin_read(T, "Palm Heights", [["CH-01", "supply_temp", 7.0]], band_min=6.0, band_max=8.0)
    assert "SOURCE" in str(ex.value)
    B.twin_read(T, "Palm Heights", [["CH-01", "kw", 310.0]])    # no band -> plain record
    good = "AssetIdentifier,TypeName,Space,InstallationDate\nCH-01,Chiller,Basement,2026-10-01\nCH-02,,Basement,2026-10-01\n"
    cb = B.cobie_check(T, "Palm Heights", good)
    assert cb["rows"] == 2 and cb["missing_required_fields"] == 1
    with pytest.raises(B.CstError) as ex2:
        B.cobie_check(T, "Palm Heights", "AssetIdentifier,TypeName\nCH-01,Chiller\n")
    assert "Space" in str(ex2.value)


# ---------------------------------------------------------------- tool layer (registry UNCHANGED)
def test_registry_580_and_schemas(env):
    from app.agent.tools import HANDLERS, TOOLS, TOOL_LABELS
    names = {t["name"] for t in TOOLS}
    for n in ("const_bim", "const_bim_dekho", "const_predesign", "const_predesign_dekho",
              "const_survey", "const_survey_dekho"):
        assert n in names and n in HANDLERS and n in TOOL_LABELS, n
    assert len(TOOLS) == 586, "581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 581 = 580 (their 0.569 base, incl. this lane's 10 Wave-3 tools) + 1 speckit v0.569 - Wave 3.5 grows ACTIONS, not tools"
    by_name = {t["name"]: t for t in TOOLS}
    for n in ("const_bim", "const_survey", "const_predesign"):
        assert by_name[n]["input_schema"]["properties"]["action"]["enum"], n
    assert set(by_name["const_bim"]["input_schema"]["properties"]["action"]["enum"]) >= {
        "asbuilt_set", "asbuilt_mark", "asbuilt_check", "twin_asset", "twin_read", "cobie_check"}
    assert set(by_name["const_survey"]["input_schema"]["properties"]["action"]["enum"]) >= {
        "gis_add", "gis_area", "gis_overlay", "setout_add", "setout_check", "level_check"}
    assert set(by_name["const_predesign"]["input_schema"]["properties"]["action"]["enum"]) >= {
        "form_area", "strike_check", "props_check", "scaffold_tag"}


def test_bim_tool_end_to_end_w35(env):
    from tests.test_life import conv_ctx
    from app.agent.const_bim_tools import BIM_HANDLERS
    ctx = conv_ctx()
    st = asyncio.run(BIM_HANDLERS["const_bim"](ctx, "asbuilt_set", project="Palm Heights",
                                               name="Handover B", required=["AB-STR-001", "AB-ARC-001"]))
    mk = asyncio.run(BIM_HANDLERS["const_bim"](ctx, "asbuilt_mark", set=st["set_id"],
                                               code="AB-STR-001", status="received", by="S. Deshmukh"))
    assert mk["status"] == "received"
    chk = asyncio.run(BIM_HANDLERS["const_bim"](ctx, "asbuilt_check", set=st["set_id"]))
    assert chk["completeness_pct"] == 50.0
    docs = asyncio.run(BIM_HANDLERS["const_bim_dekho"](ctx, "asbuilt", set=st["set_id"]))
    assert len(docs["docs"]) == 2
    tw = asyncio.run(BIM_HANDLERS["const_bim"](ctx, "twin_asset", project="Palm Heights",
                                               asset_id="LIFT-1", guid="0LiftGUID00000000000", kind="lift"))
    assert tw["twin_id"]
    rd = asyncio.run(BIM_HANDLERS["const_bim"](ctx, "twin_read", project="Palm Heights",
                                               rows=[["LIFT-1", "rides_today", 120.0]], unit="count"))
    assert rd["rows"] == 1
    twins = asyncio.run(BIM_HANDLERS["const_bim_dekho"](ctx, "twins", project="Palm Heights"))
    assert len(twins["twins"]) == 1 and twins["twins"][0]["asset_id"] == "LIFT-1"


def test_survey_tool_end_to_end_w35(env):
    import json
    from tests.test_life import conv_ctx
    from app.agent.const_survey_tools import SURVEY_HANDLERS
    ctx = conv_ctx()
    lay = asyncio.run(SURVEY_HANDLERS["const_survey"](ctx, "gis_add", project="Palm Heights",
                                                      name="plot UTM", geojson=json.dumps(_GEO_M),
                                                      crs="EPSG:32643", units="m"))
    ar = asyncio.run(SURVEY_HANDLERS["const_survey"](ctx, "gis_area", layer=lay["layer_id"]))
    assert ar["area_m2"] == 12000.0
    ov = asyncio.run(SURVEY_HANDLERS["const_survey"](ctx, "gis_overlay", project="Palm Heights",
                                                     layer=lay["layer_id"], hazard="seismic",
                                                     zone_value="Zone III", source="IS 1893 map, read by planner"))
    assert ov["overlay_id"]
    with pytest.raises(Exception) as ex:
        asyncio.run(SURVEY_HANDLERS["const_survey"](ctx, "gis_area",
                                                    layer=asyncio.run(SURVEY_HANDLERS["const_survey"](
                                                        ctx, "gis_add", project="P", name="deg",
                                                        geojson=json.dumps(_GEO_DEG)))["layer_id"]))
    assert "shoelace" in str(ex.value)
    sh = asyncio.run(SURVEY_HANDLERS["const_survey"](ctx, "setout_add", project="Palm Heights",
                                                     name="grid", design_rows=["A1,0,0,100", "A2,20,0,100"]))
    chk = asyncio.run(SURVEY_HANDLERS["const_survey"](ctx, "setout_check", project="Palm Heights",
                                                      job=sh["job_id"], aslaid_rows=["A1,0,0", "A2,20,0.05"],
                                                      tolerance_mm=25.0))
    assert chk["out_of_tolerance"] == 1 and chk["worst"][0]["point"] == "A2"
    lv = asyncio.run(SURVEY_HANDLERS["const_survey"](ctx, "level_check", project="Palm Heights",
                                                     job=sh["job_id"], obs_rows=["A1,100.04"], tolerance_mm=25.0))
    assert lv["rows"][0]["dz_mm"] == 40.0 and lv["rows"][0]["verdict"] == "out"


def test_predesign_tool_end_to_end_w35(env):
    from tests.test_life import conv_ctx
    from app.agent.const_predesign_tools import PREDESIGN_HANDLERS
    ctx = conv_ctx()
    fa = asyncio.run(PREDESIGN_HANDLERS["const_predesign"](ctx, "form_area", project="Palm Heights",
                                                           name="slab 3",
                                                           rows=[["slab", 10.0, 8.0, 0.0, 1]]))
    assert fa["total_m2"] == 80.0
    sc = asyncio.run(PREDESIGN_HANDLERS["const_predesign"](ctx, "strike_check", project="Palm Heights",
                                                           element_kind="vertical", cement="opc",
                                                           ambient_c=32.0, age_h=20.0))
    assert sc["verdict"] == "ok"
    with pytest.raises(Exception) as ex:
        asyncio.run(PREDESIGN_HANDLERS["const_predesign"](ctx, "strike_check", project="Palm Heights",
                                                          element_kind="vertical", cement="ppc",
                                                          ambient_c=32.0, age_h=48.0))
    assert "OPC" in str(ex.value)
    tg = asyncio.run(PREDESIGN_HANDLERS["const_predesign"](ctx, "scaffold_tag", project="Palm Heights",
                                                           scaffold_id="SC-9", status="ok",
                                                           checked_by="M. Sayyed"))
    assert tg["tag_id"]
    scaffolds = asyncio.run(PREDESIGN_HANDLERS["const_predesign_dekho"](ctx, "scaffolds"))
    assert len(scaffolds["scaffolds"]) == 1
    d = asyncio.run(PREDESIGN_HANDLERS["const_predesign_dekho"](ctx, "day"))
    assert d["scaffold_tags"] == 1


def test_voice_via_kaam_unchanged(env):
    from app.voice import VOICE_VIA_KAAM
    for n in ("const_bim", "const_predesign", "const_survey"):
        assert n in VOICE_VIA_KAAM, n


def test_hub_rows_carry_w35(env):
    from app.employee.hire import CATALOG
    for key, marker in (("const_bim", "as-built set register"), ("const_bim", "twin"),
                        ("const_predesign", "striking time"), ("const_predesign", "scaffold tag"),
                        ("const_survey", "GIS layers"), ("const_survey", "Setting-out")):
        assert any(marker.lower() in str(x).lower() for x in CATALOG[key]["does"]), (key, marker)
    assert any("tier C" in x for x in CATALOG["const_predesign"]["never"])


def test_version_pins():
    from pathlib import Path
    REPO = Path(__file__).resolve().parents[2]
    from app.main import APP_VERSION
    assert APP_VERSION == "0.602.0"
    assert 'APP_VERSION = "0.602.0"' in (REPO / "server" / "app" / "main.py").read_text()
    assert "version: 0.602.0+608" in (REPO / "pubspec.yaml").read_text()
