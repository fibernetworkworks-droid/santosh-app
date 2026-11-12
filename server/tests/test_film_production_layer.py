"""Film Desk PRODUCTION layer (register docs/research/film_industry #24-27, #13): shooting schedule, day-out-of-days, call sheet and a
rate-card budget, all in CODE. Honest by construction: guessed hours are returned as assumptions, an unknown address/contact stays a
blank, the budget total only counts rates she gave, the budget is owner-only, a new schedule makes an old budget stale, nothing is
sent or paid (the call sheet is a file + text; reaching the cast stays the existing message CARD)."""
import asyncio
from datetime import date

import pytest

import app.filmdesk.models  # noqa: F401
from app.filmdesk import production as P
from app.filmdesk import rules as R
from tests.test_kala_filmdesk import T, fd  # noqa: F401  (the Film Desk fixture)
from tests.test_life import conv_ctx

BIG = """INT. CHAI STALL - DAY
Meena opens the stall.

MEENA
Subah ho gayi.

EXT. STREET - DAY
Raju runs with a kite.

RAJU: Didi, patang!

INT. CHAI STALL - NIGHT
Rain falls. Meena closes up.

MEENA
Aaj bhi koi nahi aaya.

INT. HOME - NIGHT
Meena counts coins.

EXT. STREET - NIGHT
Raju looks for Meena.

RAJU: Didi kahan ho?

INT. CHAI STALL - DAY
Raju returns with tea glasses.

RAJU: Chai!
"""


def _scenes():
    return R.parse_script(BIG)


# ---------------------------------------------------------------- pure schedule
def test_schedule_groups_by_place_and_day_before_night():
    sch = P.build_schedule(_scenes())
    parts = [d["part"] for d in sch["days"]]
    assert parts == sorted(parts, key={"day": 0, "night": 1}.get)               # every day shoot before any night shoot
    stall_day = [d for d in sch["days"] if d["part"] == "day" and "CHAI STALL" in d["places"]]
    assert len(stall_day) == 1                                                  # both daylight stall scenes land on one day
    assert {s["n"] for s in stall_day[0]["scenes"]} >= {1, 6}
    assert sch["assumptions"]["assumed"] is True and "estimates" in sch["assumptions"]["note"]
    assert sch["shoot_days"] == len(sch["days"]) and sch["night_days"] == parts.count("night")
    assert all(d["hours"] <= sch["assumptions"]["day_hours"] for d in sch["days"] if len(d["scenes"]) > 1)


def test_schedule_respects_day_length_and_flags_long_scene():
    sc = _scenes()
    sch = P.build_schedule(sc, day_hours=3, setup_hours=1.5, hours_per_screen_minute=1)
    assert sch["shoot_days"] > P.build_schedule(sc)["shoot_days"]               # a shorter day needs more days
    long = [dict(x) for x in sc]
    long[0]["seconds"] = 3600
    sch2 = P.build_schedule(long, day_hours=8)
    assert any("longer than one day" in f for f in sch2["flags"])
    with pytest.raises(ValueError):
        P.build_schedule([])


def test_schedule_missing_time_is_flagged_not_hidden():
    sch = P.build_schedule(R.parse_script("INT. KITCHEN\nAsha cooks.\n\nINT. ROOM - NIGHT\nAsha sleeps."))
    assert any("taken as day" in f for f in sch["flags"])


def test_schedule_dates_skip_days_off_blocked_and_unavailable():
    sc = _scenes()
    base = P.build_schedule(sc, start_date="2026-11-02")                         # a Monday
    dates = [d["date"] for d in base["days"]]
    assert dates[0] == "2026-11-02" and dates == sorted(dates)
    sch = P.build_schedule(sc, start_date="2026-11-02", days_off=["sat", "sun"], blocked_dates=["2026-11-03"])
    for d in sch["days"]:
        dt = date.fromisoformat(d["date"])
        assert dt.weekday() < 5 and d["date"] != "2026-11-03"
    # Raju cannot work the first two dates: his days move later, the rest keep going (no day is dropped)
    una = P.build_schedule(sc, start_date="2026-11-02", unavailable={"raju": ["2026-11-02", "2026-11-03"]})
    for d in una["days"]:
        if "Raju" in d["cast"]:
            assert d["date"] not in ("2026-11-02", "2026-11-03")
    assert una["shoot_days"] == base["shoot_days"] and not una["unscheduled"]
    assert len({d["date"] for d in una["days"]}) == una["shoot_days"]           # one shoot day per date


def test_day_out_of_days_codes_and_hold():
    sch = {"days": [{"order": 1, "date": "", "cast": ["A", "B"]}, {"order": 2, "date": "", "cast": ["A"]},
                    {"order": 3, "date": "", "cast": ["B"]}, {"order": 4, "date": "", "cast": ["A", "B"]}]}
    d = P.day_out_of_days(sch)
    rows = {r["who"]: r["cells"] for r in d["grid"]}
    assert rows["A"] == ["SW", "W", "H", "WF"] and rows["B"] == ["SW", "H", "W", "WF"]
    one = P.day_out_of_days({"days": [{"order": 1, "date": "", "cast": ["C"]}, {"order": 2, "date": "", "cast": []}]})
    assert one["grid"][0]["cells"] == ["SWF", ""]
    summ = {x["who"]: x for x in d["summary"]}
    assert summ["A"]["work_days"] == 3 and summ["A"]["hold_days"] == 1 and "no price" in d["note"]


def test_call_sheet_never_invents_details():
    sch = P.build_schedule(_scenes(), start_date="2026-11-02")
    day = sch["days"][0]
    cs = P.call_sheet({"title": "Chai", "number": "F-0001"}, day)
    assert cs["unit_call"] == "07:00" and "[fill in the address]" in cs["text"] and cs["blanks"]
    assert all(c["call_is_default"] for c in cs["cast"]) and "real source" in cs["text"]
    cs2 = P.call_sheet({"title": "Chai"}, day, call_time="6.30", cast_calls={"meena": "05:45", "x": "99:99"},
                       location_address={"chai stall": "Kothrud, Pune"}, contacts={"1st AD": "98200 00000"}, notes="Baarish cover")
    assert cs2["unit_call"] == "06:30" and "Kothrud, Pune" in cs2["text"] and "98200 00000" in cs2["text"]
    assert cs2["blanks"] == [] and "Baarish cover" in cs2["text"]
    assert any(c["who"] == "Meena" and c["call"] == "05:45" and not c["call_is_default"] for c in cs2["cast"])
    assert P._clock("25:00") == "" and P._clock("7:5") == "" and P._clock("07:05") == "07:05"


def test_budget_counts_only_her_rates():
    sch = P.build_schedule(_scenes())
    dd = P.day_out_of_days(sch)
    empty = P.budget_from_rates(sch, dd, {})
    assert empty["subtotal_inr"] == 0 and len(empty["missing_rates"]) == 8 and empty["contingency_inr"] is None
    b = P.budget_from_rates(sch, dd, {"crew": 10000, "food": "500", "cast": -5, "equipment": "abc", "extra:Permit": 2500}, 10)
    by = {x["key"]: x for x in b["lines"]}
    assert by["crew"]["amount_inr"] == 10000 * sch["shoot_days"] and by["food"]["amount_inr"] == 500 * sch["shoot_days"]
    assert by["cast"]["rate_inr"] is None and by["equipment"]["rate_inr"] is None            # bad rates are ignored, not guessed
    assert by["extra:Permit"]["amount_inr"] == 2500 and "Permit" in by["extra:Permit"]["head"]
    sub = 10000 * sch["shoot_days"] + 500 * sch["shoot_days"] + 2500
    assert b["subtotal_inr"] == sub and b["contingency_inr"] == round(sub * 0.10, 2) and b["total_inr"] == round(sub * 1.1, 2)
    assert "Cast (working days)" in b["missing_rates"] and "at least" in b["say"].lower()


# ---------------------------------------------------------------- service + tools
def _film_with_big_script(S):
    p = S.project_new(T, title="Chai Aur Patang", logline="Ek chai wali aur ek bachcha, patang ke bahane dosti", fmt="short")
    num = p["project"]["number"]
    S.script_set(T, num, BIG)
    return num


def test_service_schedule_saved_callsheet_file_and_stale_budget(fd):
    S = fd
    num = _film_with_big_script(S)
    with pytest.raises(S.FilmError):
        S.plan_view(T, num, "schedule")                                           # nothing planned yet: honest error
    r = S.plan_schedule(T, num, start_date="2026-11-02", days_off=["sun"])
    assert r["shoot_days"] >= 2 and r["dood"]["grid"] and r["assumptions"]["assumed"] is True
    assert S.plan_view(T, num, "schedule")["days"][0]["date"] == "2026-11-02"
    assert S.plan_view(T, num, "dood")["summary"]
    cs = S.plan_view(T, num, "callsheet", 1)
    assert cs["unit_call"] == "07:00"
    out = S.plan_callsheet(T, num, 1, conv="", call_time="06:00", contacts={"1st AD": "9820000000"})
    assert out["unit_call"] == "06:00" and "9820000000" in out["text"]
    assert out["file"] is not None and S.STORED and S.STORED[-1][0].startswith("CallSheet_F-0001_Day1") and S.STORED[-1][1][:4] == b"%PDF"
    with pytest.raises(S.FilmError):
        S.plan_callsheet(T, num, 99)
    with pytest.raises(S.FilmError):
        S.plan_callsheet(T, num, "")
    with pytest.raises(S.FilmError):
        S.plan_budget(T, num, {"crew": 1000}, actor="staff:s1")                   # money numbers: owner only
    b = S.plan_budget(T, num, {"crew": 12000}, 5)
    assert b["subtotal_inr"] == 12000 * r["shoot_days"] and S.plan_view(T, num, "plan_budget")["total_inr"] == b["total_inr"]
    b2 = S.plan_budget(T, num, {"food": 400})                                    # rates MERGE with the earlier card
    assert b2["subtotal_inr"] == (12000 + 400) * r["shoot_days"] and b2["contingency_pct"] == 5
    S.plan_schedule(T, num, day_hours=2)                                          # a new schedule: the old budget is stale
    with pytest.raises(S.FilmError):
        S.plan_view(T, num, "plan_budget")
    nb = S.plan_budget(T, num, None)                                              # saved rates still apply to the new plan
    assert nb["quantities"]["shoot_days"] > r["shoot_days"] and nb["subtotal_inr"] > b2["subtotal_inr"]


def test_old_rows_with_null_plan_still_work(fd):
    from app.db import session
    from app.filmdesk.models import FilmProject
    S = fd
    num = _film_with_big_script(S)
    with session() as s:
        p = s.query(FilmProject).filter(FilmProject.number == num).one()
        p.plan = None                                                              # a row from before this column existed
    assert S.plan_schedule(T, num)["shoot_days"] >= 1


def test_no_script_is_an_honest_error(fd):
    S = fd
    p = S.project_new(T, title="Khali", logline="Ek vichaar jisme abhi script nahi hai", fmt="short")
    with pytest.raises(S.FilmError):
        S.plan_schedule(T, p["project"]["number"])


def test_tools_expose_the_layer_and_guard_roles(fd):
    from app.agent import filmdesk_tools as FT
    from app.agent.tools import ToolError
    S = fd
    assert {"schedule", "callsheet", "budget_plan"} <= set(FT._ACTIONS) and "budget_plan" in FT._OWNER_ONLY
    props = FT.FILMDESK_TOOLS[0]["input_schema"]["properties"]
    assert {"start_date", "days_off", "unavailable", "rates", "contingency_pct", "day", "cast_calls"} <= set(props)
    num = _film_with_big_script(S)
    ctx = conv_ctx()
    r = asyncio.run(FT._film_desk(ctx, action="schedule", project=num, start_date="2026-11-02"))
    assert r["shoot_days"] >= 2
    seen = asyncio.run(FT._film_desk_dekho(ctx, what="dood", project=num))
    assert seen["grid"]
    cs = asyncio.run(FT._film_desk(ctx, action="callsheet", project=num, day=1))
    assert cs["file"] is not None
    bud = asyncio.run(FT._film_desk(ctx, action="budget_plan", project=num, rates={"crew": 9000}))
    assert bud["subtotal_inr"] > 0
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    assert asyncio.run(FT._film_desk(staff, action="schedule", project=num))["shoot_days"] >= 1       # staff may plan the shoot
    with pytest.raises(ToolError):
        asyncio.run(FT._film_desk(staff, action="budget_plan", project=num, rates={"crew": 1}))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(FT._film_desk(cust, action="schedule", project=num))
