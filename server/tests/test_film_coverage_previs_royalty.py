"""Film Desk SCRIPT COVERAGE + PREVIS + ROYALTY terms (register docs/research/film_industry): all in CODE, read-only except the royalty book.
Honest by construction: coverage returns counts and flagged HEURISTICS and never a reader's verdict; previs checks the shot list and
says what it does not check; the royalty module ships NO guild rate table - every term is hers and must name its contract source - and its
statement is exact to the paisa, owner-only, and pays nothing."""
import asyncio

import pytest

import app.filmdesk.models  # noqa: F401
from app.filmdesk import coverage as CV
from app.filmdesk import guild as GD
from app.filmdesk import previs as PV
from app.filmdesk import rules as R
from tests.test_film_production_layer import BIG
from tests.test_kala_filmdesk import T, fd  # noqa: F401
from tests.test_life import conv_ctx

SCRIPT = """INT. CHAI STALL - DAY
Meena opens the stall. She thinks about her late husband.

MEENA
Subah ho gayi.

EXT. STREET - DAY
Raju runs with a kite.

RAJU: Didi, patang!
MEENA: Raju, ruko!
RAJU: Nahi!

INT. CHAI STALL
Raju returns.

RAJU: Chai!
MEENA: Lo.
RAJU: Shukriya.
GUARD: Hmm.
"""


# ---------------------------------------------------------------- coverage (pure)
def test_coverage_counts_and_cast_table():
    scenes = R.parse_script(SCRIPT)
    c = CV.coverage(scenes, SCRIPT, 60)
    assert c["scenes"] == 3 and c["characters_n"] >= 3 and c["estimated_seconds"] == sum(s["seconds"] for s in scenes)
    cast = {x["name"]: x for x in c["cast_table"]}
    assert cast["Raju"]["lines"] == 4 and cast["Raju"]["scenes_n"] == 2 and cast["Raju"]["first_scene"] == 2
    assert abs(sum(x["dialogue_pct"] for x in c["cast_table"]) - 100.0) < 0.3                       # shares add up
    assert c["most_dialogue"] == "Meena" and "zaroori nahi" in c["most_dialogue_note"]
    assert c["places_n"] == 2 and c["company_moves"] >= 1 and c["scene_table"][1]["dialogue_lines"] == 3


def test_coverage_flags_are_labelled_and_never_a_verdict():
    c = CV.coverage(R.parse_script(SCRIPT), SCRIPT, 600)
    text = " | ".join(f["text"] for f in c["flags"])
    assert {f["kind"] for f in c["flags"]} <= {"measured", "heuristic"}
    assert "Scene 3" in text and "INT/EXT" in text                                                  # scene 3 heading has no time of day
    assert "Guard" in text and "ek line" in text                                                    # one-line, one-scene role
    assert "soch / ehsaas" in text and "scene 1" in text                                            # 'thinks' in an action line
    assert "target 600 s" in text                                                                   # runtime target far off
    assert "pass" in c["kind_note"].lower() and "insaan" in c["kind_note"]
    for bad in ("recommend", "greenlight"):
        assert bad not in " ".join(f["text"].lower() for f in c["flags"])


def test_coverage_spots_the_same_character_spelled_twice():
    s = """INT. A - DAY\nMEENA: Hi\nRAJU: Hi\n\nINT. B - DAY\nMeenaa: Bye\nRaju: Bye\n"""
    c = CV.coverage(R.parse_script(s), s)
    assert any("ek hi kirdaar" in f["text"] and f["kind"] == "heuristic" for f in c["flags"])


def test_coverage_themes_are_word_counts_not_a_rating():
    s = "INT. BAR - NIGHT\nHe drinks sharab and a gun is shown. Blood on the floor.\n\nRAJU: Maar do!\n"
    c = CV.coverage(R.parse_script(s), s)
    assert c["theme_hits"]["violence"] >= 3 and c["theme_hits"]["substance"] >= 1 and "rating nahi" in c["theme_note"]


def test_coverage_empty_script_says_so():
    assert CV.coverage([])["scenes"] == 0 and "script" in CV.coverage([])["note"]


# ---------------------------------------------------------------- previs (pure)
def _shots():
    return [
        {"id": "sc1s1", "scene": "sc1", "camera": "static", "duration": 5, "characters": ["Meena"], "dialogue": None, "speaker": None},
        {"id": "sc1s2", "scene": "sc1", "camera": "close_up", "duration": 2, "characters": ["Meena"],
         "dialogue": "Subah ho gayi aaj bhi koi nahi aaya yahan par", "speaker": "Meena"},
        {"id": "sc2s1", "scene": "sc2", "camera": "drone", "duration": 5, "characters": ["Zorro"], "dialogue": "Hi", "speaker": None},
    ]


def test_previs_timeline_and_flags():
    scenes = R.parse_script(SCRIPT)
    v = PV.previs(_shots(), scenes, 600)
    assert v["shots"] == 3 and v["total_seconds"] == 12 and [r["start_s"] for r in v["timeline"]] == [0, 5, 7]
    text = " | ".join(f["text"] for f in v["flags"])
    assert "sc1s2: dialogue ko" in text and "sc2s1: dialogue hai par bolne wala" in text and "Zorro" in text
    assert "Scene 3" in text and "koi shot nahi" in text and "target 600 s" in text
    assert any("drone" in g for g in v["gear"]) and "Drone shot hai" in text
    assert "180 degree" in v["note"]


def test_previs_monotony_and_missing_camera():
    scenes = R.parse_script(SCRIPT)
    shots = [{"id": f"sc1s{i}", "scene": "sc1", "camera": "static", "duration": 4, "characters": [], "dialogue": None} for i in range(1, 5)]
    shots.append({"id": "sc2s1", "scene": "sc2", "camera": None, "duration": 4, "characters": [], "dialogue": None})
    text = " | ".join(f["text"] for f in PV.previs(shots, scenes)["flags"])
    assert "4 shot lagataar 'static'" in text and "sc2s1: camera tay nahi" in text
    assert PV.previs([], scenes)["shots"] == 0


# ---------------------------------------------------------------- royalty (pure)
def _term(**k):
    base = {"party": "Writer A", "role": "writer", "basis": "percent_of_gross", "rate": 2, "source": "Writer agreement cl. 7(b)"}
    return GD.norm_term({**base, **k}, k.pop("seq", 1) if "seq" in k else 1)


def test_term_needs_a_source_and_has_no_builtin_rates():
    with pytest.raises(ValueError):
        GD.norm_term({"party": "A", "basis": "flat_inr", "rate": 100}, 1)                          # no source = refused
    for bad in ({"party": "", "basis": "flat_inr", "rate": 1, "source": "x"}, {"party": "A", "basis": "magic", "rate": 1, "source": "x"},
                {"party": "A", "basis": "flat_inr", "source": "x"}, {"party": "A", "basis": "percent_of_gross", "rate": 150, "source": "x"}):
        with pytest.raises(ValueError):
            GD.norm_term(bad, 1)
    import inspect
    assert "RATE_TABLE" not in inspect.getsource(GD) and "bargain" not in GD.__doc__.lower() and "NO guild rate table" in GD.__doc__


def test_statement_exact_threshold_cap_floor_and_windows():
    terms = [GD.norm_term({"party": "Writer A", "basis": "percent_of_gross", "rate": 2.5, "threshold_inr": 100000, "applies_to": "svod, tv",
                           "source": "cl 7"}, 1),
             GD.norm_term({"party": "Composer B", "basis": "flat_inr", "rate": 5000, "source": "cl 3"}, 2),
             GD.norm_term({"party": "Singer C", "basis": "per_unit", "rate": 0.5, "applies_to": "music", "cap_inr": 1000, "source": "cl 9"}, 3),
             GD.norm_term({"party": "Dir D", "basis": "percent_of_net", "rate": 5, "source": "cl 1", "end": "2026-12-31"}, 4)]
    recs = [GD.norm_receipt({"medium": "svod", "amount_inr": 333333.33, "net_inr": 300000, "period": "2026-11-01"}, 1),
            GD.norm_receipt({"medium": "tv", "amount_inr": 66666.67, "net_inr": 60000, "period": "2027-02-01"}, 2),
            GD.norm_receipt({"medium": "music", "amount_inr": 5000, "units": 4000, "period": "2026-11-05"}, 3)]
    st = GD.statement(terms, recs)
    by = {x["party"]: x["amount_inr"] for x in st["by_party"]}
    assert by["Writer A"] == 7500.0                                                                   # (333333.33+66666.67-100000)*2.5%
    assert by["Composer B"] == 5000.0 and by["Singer C"] == 1000.0                                    # flat; per-unit capped at 1000
    assert next(l for l in st["lines"] if l["party"] == "Singer C")["capped"] is True
    dline = next(l for l in st["lines"] if l["party"] == "Dir D")                                     # net missing on the music line? no: window drops tv
    assert dline["problem"] and "net_inr" in dline["problem"]                                         # music receipt has no net -> not guessed
    assert st["total_inr"] == 13500.0 and st["gross_receipts_inr"] == 405000.0 and "guild" in st["note"]
    assert any("Dir D" in p for p in st["problems"])


def test_statement_says_when_nothing_applies():
    st = GD.statement([GD.norm_term({"party": "A", "basis": "flat_inr", "rate": 10, "applies_to": "tv", "source": "x"}, 1)],
                      [GD.norm_receipt({"medium": "svod", "amount_inr": 100}, 1)])
    assert st["total_inr"] == 0 and st["lines"][0]["problem"] and st["lines"][0]["amount_inr"] == 0.0


# ---------------------------------------------------------------- service + tool + api
def _film(S):
    p = S.project_new(T, title="Chai Aur Patang", logline="Ek chai wali aur ek bachcha, patang ke bahane dosti", fmt="short")
    num = p["project"]["number"]
    S.script_set(T, num, BIG)
    return num


def test_service_coverage_previs_and_royalty_flow(fd):
    S = fd
    num = _film(S)
    cv = S.coverage_view(T, num)
    assert cv["scenes"] >= 6 and cv["project"]["number"] == num and cv["cast_table"]
    assert S.previs_view(T, num)["shots"] == 0                                                         # no shots yet: says so
    S.shots_make(T, num, use_model=False)
    pv = S.previs_view(T, num)
    assert pv["shots"] > 0 and pv["timeline"][0]["start_s"] == 0
    with pytest.raises(S.FilmError):
        S.royalty_op(T, num, "add", actor="staff:s1", party="A", basis="flat_inr", rate=1, source="x")  # owner only
    with pytest.raises(S.FilmError):
        S.royalty_op(T, num, "add", party="A", basis="flat_inr", rate=1)                                # no source
    S.royalty_op(T, num, "add", party="Writer A", role="writer", basis="percent_of_gross", rate=2, source="cl 7")
    r = S.royalty_op(T, num, "receipt", medium="svod", amount_inr=100000, period="2026-11-01")
    assert r["by_party"][0]["amount_inr"] == 2000.0 and r["say"]
    S.royalty_op(T, num, "update", entry="gt1", rate=3)
    assert S.royalties_view(T, num)["total_inr"] == 3000.0
    S.royalty_op(T, num, "unreceipt", entry="rc1")
    assert S.royalties_view(T, num)["total_inr"] == 0.0 and S.royalties_view(T, num)["problems"]
    S.royalty_op(T, num, "remove", entry="gt1")
    assert S.royalties_view(T, num)["terms"] == []
    with pytest.raises(S.FilmError):
        S.royalty_op(T, num, "update", entry="gt9", rate=1)


def test_tools_expose_coverage_previs_and_royalty(fd):
    from app.agent import filmdesk_tools as FT
    from app.agent.tools import ToolError
    S = fd
    num = _film(S)
    assert "royalty" in FT._ACTIONS and "royalty" in FT._OWNER_ONLY
    props = FT.FILMDESK_TOOLS[0]["input_schema"]["properties"]
    assert {"party", "basis", "rate", "threshold_inr", "cap_inr", "source", "amount_inr", "applies_to"} <= set(props)
    ctx = conv_ctx()
    assert asyncio.run(FT._film_desk_dekho(ctx, what="coverage", project=num))["scenes"] >= 6
    assert asyncio.run(FT._film_desk_dekho(ctx, what="previs", project=num))["shots"] == 0
    g = asyncio.run(FT._film_desk(ctx, action="royalty", project=num, op="add", party="W", basis="flat_inr", rate=100, source="cl 1"))
    assert g["terms"][0]["party"] == "W"
    assert asyncio.run(FT._film_desk_dekho(ctx, what="royalties", project=num))["terms"]
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(ToolError):
        asyncio.run(FT._film_desk(staff, action="royalty", project=num, op="add", party="x", basis="flat_inr", rate=1, source="s"))
    with pytest.raises(ToolError):
        asyncio.run(FT._film_desk_dekho(staff, what="royalties", project=num))
    assert asyncio.run(FT._film_desk_dekho(staff, what="coverage", project=num))["scenes"] >= 6       # reading coverage is fine for the crew


def test_api_routes_exist_for_every_producer_layer():
    import app.filmdesk.api as A
    r = A.make_router(lambda: None, lambda: "t")
    paths = {(m, x.path) for x in r.routes for m in x.methods}
    for suffix in ("coverage", "previs", "schedule", "festivals", "windows", "waterfall", "deliverables", "localisation", "royalties"):
        assert ("GET", f"/api/filmdesk/projects/{{ref}}/{suffix}") in paths, suffix
    for suffix in ("schedule", "callsheet", "budget-plan", "festivals", "windows", "waterfall", "deliverables", "localisation", "royalties"):
        assert ("POST", f"/api/filmdesk/projects/{{ref}}/{suffix}") in paths, suffix
