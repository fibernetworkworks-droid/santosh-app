"""Film Desk SALES layer (register docs/research/film_industry #84/#85 festivals, #22/#86 windows, #21/#23 waterfall): a festival tracker,
release windows with exclusivity + holdback checks, and a recoupment waterfall, all in CODE. Honest by construction: deadline, fee,
premiere rule and holdbacks are HER facts (never looked up or guessed), premiere trouble is a WARNING for a person, windows and the
waterfall are owner-only, the waterfall always adds back to the gross to the paisa, and nothing is submitted, signed, sent or paid."""
import asyncio
from datetime import date

import pytest

import app.filmdesk.models  # noqa: F401
from app.filmdesk import sales as SL
from tests.test_film_production_layer import BIG
from tests.test_kala_filmdesk import T, fd  # noqa: F401
from tests.test_life import conv_ctx

TODAY = date(2026, 11, 10)


# ---------------------------------------------------------------- festivals (pure)
def test_festival_entry_is_clean_and_never_invented():
    e = SL.norm_festival({"name": "  Pune   Film  Fest ", "deadline": "2026-11-15", "fee_inr": "1500", "requires": "WORLD"}, 3)
    assert e["id"] == "fs3" and e["name"] == "Pune Film Fest" and e["fee_inr"] == 1500.0 and e["requires"] == "world"
    u = SL.norm_festival({"name": "X", "deadline": "tomorrow", "fee_inr": "-5", "requires": "maybe"}, 1)
    assert u["deadline"] == "" and u["fee_inr"] is None and u["requires"] == "unknown"           # bad input becomes blank/unknown, not a guess
    with pytest.raises(ValueError):
        SL.norm_festival({"name": ""}, 1)
    with pytest.raises(ValueError):
        SL.norm_festival({"name": "X", "status": "won"}, 1)


def test_festival_view_days_left_and_deadline_flags():
    es = [SL.norm_festival({"name": "Near", "deadline": "2026-11-14"}, 1), SL.norm_festival({"name": "Late", "deadline": "2026-11-01"}, 2),
          SL.norm_festival({"name": "Far", "deadline": "2027-02-01", "requires": "none"}, 3),
          SL.norm_festival({"name": "Done", "deadline": "2026-10-01", "status": "submitted", "fee_inr": 800}, 4)]
    v = SL.festival_view(es, TODAY)
    by = {r["name"]: r for r in v["festivals"]}
    assert by["Near"]["days_left"] == 4 and by["Late"]["days_left"] == -9 and by["Far"]["days_left"] > 80
    assert any("Near" in f and "4 days" in f for f in v["flags"]) and any("Late" in f and "has passed" in f for f in v["flags"])
    assert not any("Done" in f and "passed" in f for f in v["flags"])                              # already submitted: no overdue nag
    assert v["fees_committed_inr"] == 800 and v["counts"]["submitted"] == 1 and "Hoola does not make them up" in v["note"]
    assert v["festivals"][0]["status"] in ("planned", "submitted")                                  # live ones sort first


def test_premiere_warning_is_a_warning_not_a_ruling():
    es = [SL.norm_festival({"name": "Goa", "status": "screened", "screened_on": "2026-10-20", "requires": "none"}, 1),
          SL.norm_festival({"name": "Berlin", "requires": "world", "event_date": "2027-02-10", "deadline": "2026-12-01"}, 2),
          SL.norm_festival({"name": "Local", "requires": "regional", "event_date": "2027-01-10"}, 3),
          SL.norm_festival({"name": "Mystery"}, 4)]
    v = SL.festival_view(es, TODAY)
    msgs = " | ".join(v["flags"])
    assert "Berlin needs a world premiere" in msgs and "Goa" in msgs and "not a decision" in msgs
    assert "Local needs" not in msgs                                                                    # a regional rule is not flagged by this heuristic
    assert "Mystery: premiere rule not recorded" in msgs                                              # unknown rule is named, not assumed


def test_packet_auto_from_film_and_her_ticks():
    proj = {"scenes_n": 5, "logline": "Ek chai wali", "runtime_s": None, "language": "Hindi"}
    e = SL.norm_festival({"name": "F"}, 1)
    e["ticks"] = {"poster": True}
    pk = {x["key"]: x for x in SL.festival_packet(proj, e)}
    assert pk["logline"]["done"] and pk["script"]["done"] and pk["language"]["done"] and not pk["runtime"]["done"]
    assert pk["poster"]["done"] and not pk["screener"]["done"] and pk["logline"]["auto"] and not pk["poster"]["auto"]


# ---------------------------------------------------------------- windows (pure)
def _w(i, **kw):
    base = {"medium": "svod", "territory": "india", "start": "2026-12-01", "end": "2027-11-30", "exclusive": True, "licensee": f"L{i}"}
    return SL.norm_window({**base, **kw}, i)


def test_window_normalisation_and_errors():
    w = SL.norm_window({"medium": "SVOD", "territory": "India, UAE ; india", "start": "2026-12-01"}, 1)
    assert w["territory"] == ["india", "uae"] and w["end"] == "" and w["exclusive"] is False
    assert SL.norm_window({"medium": "tv", "start": "2026-12-01"}, 2)["territory"] == ["world"]
    for bad in ({"medium": "radio", "start": "2026-12-01"}, {"medium": "tv"}, {"medium": "tv", "start": "2026-12-05", "end": "2026-12-01"}):
        with pytest.raises(ValueError):
            SL.norm_window(bad, 1)


def test_exclusive_overlap_conflicts():
    a, b = _w(1), _w(2, start="2027-06-01", end="2028-05-31")                                       # overlap Jun-Nov 2027, both exclusive, same medium
    r = SL.check_windows([a, b])
    assert [c["kind"] for c in r["conflicts"]] == ["exclusive_overlap"] and not r["clear"]
    assert SL.check_windows([a, _w(3, territory="uae")])["clear"]                                    # different territory: fine
    assert SL.check_windows([a, _w(4, medium="tv")])["clear"]                                        # different medium: fine
    assert SL.check_windows([a, _w(5, start="2027-12-01", end="2028-11-30")])["clear"]               # back to back: fine
    assert not SL.check_windows([_w(6, exclusive=False, territory="world"), _w(7, exclusive=False)])["conflicts"]      # nobody exclusive: fine
    assert SL.check_windows([_w(8, territory="world"), _w(9, territory="uae")])["conflicts"]          # 'world' overlaps everything
    open_end = _w(10, end="")
    assert SL.check_windows([open_end, _w(11, start="2035-01-01", end="")])["conflicts"]             # an open-ended licence never ends


def test_holdbacks_are_her_rules():
    th = _w(1, medium="theatrical", start="2026-12-01", end="2027-01-31", exclusive=False)
    ott = _w(2, medium="svod", start="2027-01-10", end="2027-12-31", exclusive=False)
    rules = [{"after": "theatrical", "before": "svod", "days": 56}]
    r = SL.check_windows([th, ott], rules)
    v = r["holdback_violations"][0]
    assert v["earliest"] == "2027-01-26" and "cannot be before" in v["why"] and not r["clear"]
    assert SL.check_windows([th, _w(3, medium="svod", start="2027-01-26", exclusive=False)], rules)["clear"]
    assert SL.check_windows([th, ott])["clear"]                                                      # no rules given: nothing assumed
    bad = SL.check_windows([th, ott], [{"after": "nope", "before": "svod", "days": 5}, {"after": "tv"}])
    assert len(bad["rule_problems"]) == 2 and not bad["clear"]


# ---------------------------------------------------------------- waterfall (pure)
def test_waterfall_ties_to_the_gross_to_the_paisa():
    out = SL.waterfall(1000000, [{"name": "Distributor fee", "kind": "percent_of_gross", "value": 20},
                                 {"name": "P&A", "kind": "fixed_inr", "value": 150000},
                                 {"name": "Sales agent", "kind": "percent_of_remaining", "value": 10, "cap_inr": 50000}],
                       [{"name": "A", "invested_inr": 300000, "premium_pct": 10}, {"name": "B", "invested_inr": 200000}],
                       [{"name": "Producer", "pct": 60}, {"name": "Director", "pct": 40}])
    tiers = {t["name"]: t for t in out["tiers"]}
    assert tiers["Distributor fee"]["amount_inr"] == 200000 and tiers["P&A"]["amount_inr"] == 150000
    assert tiers["Sales agent"]["amount_inr"] == 50000                                                # 10% of 650000 = 65000, capped at 50000
    assert tiers["Investor recoup"]["amount_inr"] == 530000 and out["investors_fully_recouped"] is True
    assert out["net_after_recoup_inr"] == 1000000 - 200000 - 150000 - 50000 - 530000 == 70000
    assert [(s["name"], s["amount_inr"]) for s in out["profit_split"]] == [("Producer", 42000.0), ("Director", 28000.0)]
    assert out["ties_to_gross"] and out["unallocated_inr"] == 0 and "contract" in out["note"]


def test_waterfall_shortfall_and_rounding():
    short = SL.waterfall(100000, [{"name": "Fee", "kind": "fixed_inr", "value": 40000}],
                         [{"name": "A", "invested_inr": 50000}, {"name": "B", "invested_inr": 50000}], [{"name": "P", "pct": 100}])
    assert short["investors_fully_recouped"] is False and short["net_after_recoup_inr"] == 0 and short["ties_to_gross"]
    lines = {x["name"]: x for x in short["tiers"][1]["lines"]}
    assert lines["A"]["paid_inr"] == 30000 and lines["B"]["paid_inr"] == 30000 and lines["A"]["shortfall_inr"] == 20000
    odd = SL.waterfall(100000.01, [], [{"name": f"I{i}", "invested_inr": 100} for i in range(3)], [{"name": "A", "pct": 33.33},
                                                                                                  {"name": "B", "pct": 33.33},
                                                                                                  {"name": "C", "pct": 33.34}])
    assert odd["ties_to_gross"] and abs(sum(s["amount_inr"] for s in odd["profit_split"]) - odd["net_after_recoup_inr"]) < 0.005
    over = SL.waterfall(1000, [{"name": "Huge", "kind": "fixed_inr", "value": 5000}])
    assert over["tiers"][0]["amount_inr"] == 1000 and over["net_after_recoup_inr"] == 0              # a deduction can never exceed what is left


def test_waterfall_refuses_bad_input_and_bad_shares():
    with pytest.raises(ValueError):
        SL.waterfall(None)
    with pytest.raises(ValueError):
        SL.waterfall(1000, [{"name": "x", "kind": "magic", "value": 5}])
    with pytest.raises(ValueError):
        SL.waterfall(1000, None, [{"name": "", "invested_inr": 5}])
    bad = SL.waterfall(1000, None, None, [{"name": "A", "pct": 60}, {"name": "B", "pct": 30}])
    assert bad["profit_split"] == [] and bad["unallocated_inr"] == 1000 and "100%" in bad["problems"][0] and bad["ties_to_gross"]


# ---------------------------------------------------------------- service + tool
def _film(S):
    p = S.project_new(T, title="Chai Aur Patang", logline="Ek chai wali aur ek bachcha, patang ke bahane dosti", fmt="short")
    num = p["project"]["number"]
    S.script_set(T, num, BIG)
    return num


def test_service_festival_flow(fd, monkeypatch):
    S = fd
    monkeypatch.setattr(S, "today", lambda tenant: TODAY)
    num = _film(S)
    r = S.festival_op(T, num, "add", name="Pune Fest", deadline="2026-11-14", fee_inr=1000, requires="world")
    assert r["festivals"][0]["id"] == "fs1" and r["festivals"][0]["days_left"] == 4 and r["festivals"][0]["packet"]["total"] == 12
    S.festival_op(T, num, "add", name="Goa Fest", status="screened", screened_on="2026-10-30", requires="none")
    S.festival_op(T, num, "tick", entry="fs1", key="poster")
    v = S.festival_view(T, num)
    pune = next(x for x in v["festivals"] if x["id"] == "fs1")
    assert {i["key"]: i["done"] for i in pune["packet"]["items"]}["poster"] and any("not a decision" in f for f in v["flags"])
    with pytest.raises(S.FilmError):
        S.festival_op(T, num, "tick", entry="fs1", key="nonsense")
    S.festival_op(T, num, "update", entry="fs1", status="submitted", submitted_on="2026-11-09")
    assert S.festival_view(T, num)["fees_committed_inr"] == 1000.0
    S.festival_op(T, num, "remove", entry="fs2")
    assert [x["id"] for x in S.festival_view(T, num)["festivals"]] == ["fs1"]
    r3 = S.festival_op(T, num, "add", name="Third")
    assert r3["festivals"][-1]["id"] == "fs2" or r3["festivals"][-1]["id"] == "fs3"                    # ids never collide with a live one
    with pytest.raises(S.FilmError):
        S.festival_op(T, num, "update", entry="fs99", status="rejected")
    with pytest.raises(S.FilmError):
        S.festival_op(T, num, "add", name="")


def test_service_windows_and_waterfall_are_owner_only(fd):
    S = fd
    num = _film(S)
    with pytest.raises(S.FilmError):
        S.window_op(T, num, "add", actor="staff:s1", medium="svod", start="2026-12-01")
    with pytest.raises(S.FilmError):
        S.waterfall_run(T, num, 1000, actor="staff:s1")
    S.window_op(T, num, "add", medium="theatrical", territory="india", start="2026-12-01", end="2027-01-31")
    r = S.window_op(T, num, "add", medium="svod", territory="india", start="2027-01-10", exclusive=True, licensee="Platform A")
    S.window_op(T, num, "holdbacks", holdbacks=[{"after": "theatrical", "before": "svod", "days": 56}])
    v = S.windows_view(T, num)
    assert len(v["windows"]) == 2 and v["check"]["holdback_violations"] and not v["check"]["clear"] and r["say"]
    S.window_op(T, num, "remove", entry="w2")
    assert S.windows_view(T, num)["check"]["clear"]
    with pytest.raises(S.FilmError):
        S.window_op(T, num, "add", medium="radio", start="2026-12-01")
    with pytest.raises(S.FilmError):
        S.waterfall_view(T, num)                                                                      # nothing calculated yet
    w = S.waterfall_run(T, num, 500000, [{"name": "Fee", "kind": "percent_of_gross", "value": 10}],
                        [{"name": "Inv", "invested_inr": 100000, "premium_pct": 20}], [{"name": "P", "pct": 100}])
    assert w["ties_to_gross"] and S.waterfall_view(T, num)["gross_inr"] == 500000 and "investors fully recouped" in w["say"]
    with pytest.raises(S.FilmError):
        S.waterfall_run(T, num, "lots")


def test_tools_expose_the_sales_layer(fd, monkeypatch):
    from app.agent import filmdesk_tools as FT
    from app.agent.tools import ToolError
    S = fd
    monkeypatch.setattr(S, "today", lambda tenant: TODAY)
    assert {"festival", "window", "waterfall"} <= set(FT._ACTIONS) and {"window", "waterfall"} <= FT._OWNER_ONLY
    assert "festival" not in FT._OWNER_ONLY                                                           # the crew may keep the festival diary
    props = FT.FILMDESK_TOOLS[0]["input_schema"]["properties"]
    assert {"op", "entry", "requires", "medium", "territory", "holdbacks", "gross_inr", "deductions", "investors", "shares"} <= set(props)
    num = _film(S)
    ctx = conv_ctx()
    f = asyncio.run(FT._film_desk(ctx, action="festival", project=num, op="add", name="Pune Fest", deadline="2026-11-14"))
    assert f["festivals"][0]["name"] == "Pune Fest"
    assert asyncio.run(FT._film_desk_dekho(ctx, what="festivals", project=num))["festivals"]
    w = asyncio.run(FT._film_desk(ctx, action="window", project=num, op="add", medium="tv", start="2027-03-01"))
    assert w["windows"] and asyncio.run(FT._film_desk_dekho(ctx, what="windows", project=num))["check"]["clear"]
    g = asyncio.run(FT._film_desk(ctx, action="waterfall", project=num, gross_inr=100000, shares=[{"name": "P", "pct": 100}]))
    assert g["profit_split"][0]["amount_inr"] == 100000 and asyncio.run(FT._film_desk_dekho(ctx, what="waterfall", project=num))["ties_to_gross"]
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    assert asyncio.run(FT._film_desk(staff, action="festival", project=num, op="add", name="Staff entry"))["festivals"]
    for act, kw in (("window", {"op": "add", "medium": "tv", "start": "2027-03-01"}), ("waterfall", {"gross_inr": 5})):
        with pytest.raises(ToolError):
            asyncio.run(FT._film_desk(staff, action=act, project=num, **kw))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(FT._film_desk(cust, action="festival", project=num, op="add", name="x"))
