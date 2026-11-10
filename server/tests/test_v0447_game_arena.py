"""v0.447 TWO DEFECTS + THE GAME ARENA (docs/GAME_MOAT_PLAN.md).

The two defects the moat research found live in shipped code:
1. The money-game guard missed the test the Indian Rules actually turn on - Rule 9's rewards that are TRANSFERABLE,
   REDEEMABLE or MONETISABLE OUTSIDE the game. "coins players can withdraw to UPI" passed, and offering such a game is
   cognisable and non-bailable for whoever publishes it. Both doors are checked: the brief AND the Game Bible's economy.
2. /mcp/gamedesk implemented only the `initialize` handshake, which the current MCP revision (2026-07-28) REMOVED - a
   modern-only client fails against a legacy server. Both eras now answer.

And the Arena itself: a fixed seeded brief set, a card measured by PLAYING (the QA bots, not a look), originality as
distance from every other game of the run, run-vs-run comparison, blind duels - and `fun` reported NOT ASSESSED.
"""
import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)


# ================================================================ defect 1: the money-out guard
CASH_OUT = ["a ludo game where players collect coins and withdraw them to UPI",
            "ek ludo game jisme coins ko paise mein badal sakte hain",
            "puzzle game, points redeem for cash",
            "collect gems and cash out to your bank account",
            "trade skins with other players for real cash",
            "play to earn runner game", "entry fee tournament with a prize", "an NFT racing game",
            "coins jeeto aur paise nikal sakte ho", "tokens transferable to Paytm",
            "a carrom game where the winner's points are paid out by PhonePe"]
FINE = ["a ludo game where players collect coins to unlock new boards",
        "a shop game where the player buys items with coins",
        "a runner game, score goes up, best score saved",
        "ek rickshaw racing game Mumbai ki sadkon par",
        "match-3 with 100 levels, coins buy power-ups",
        "a cricket game with a score and a leaderboard",
        "idle factory game, earn coins, buy upgrades, prestige",
        "a quiz game for class 7 science",
        "a shop billing game where the customer pays rupees for vegetables in the game",
        "tower defence, gems from levels buy towers"]


def test_a_game_whose_reward_leaves_the_game_as_money_is_refused():
    from app.gamedesk import service as G
    for brief in CASH_OUT:
        why = G.problem(brief)
        assert why, f"NOT REFUSED (a non-bailable offence for whoever publishes it): {brief!r}"
        assert "non-bailable" in why or "money games band" in why, (brief, why)
    for brief in FINE:                                   # an in-game economy is normal and must still build
        assert G.problem(brief) == "", f"false alarm: {brief!r} -> {G.problem(brief)}"


def test_the_bible_is_the_other_door_and_is_checked_too():
    from app.gamedesk import bible as B
    ok = B.empty()
    assert B.money_out(ok) == "" and not B.check(ok)["errors"]
    withdrawable = B.empty()
    withdrawable["economy"] = {"currency": "coins", "withdrawable": True}
    noted = B.empty()
    noted["economy"] = {"currency": "coins", "note": "coins can be redeemed for cash"}
    item = B.empty()
    item["entities"]["item"] = [{"id": "gem", "name": "Gem", "notes": "trade gems for real cash on UPI"}]
    for name, data in (("a withdrawable key", withdrawable), ("the economy's own words", noted), ("an item's notes", item)):
        assert B.money_out(data), name
        assert any("non-bailable" in e for e in B.check(data)["errors"]), name
    good = B.empty()
    good["economy"] = {"currency": "coins"}
    good["entities"]["item"] = [{"id": "pw", "name": "Power up", "notes": "costs 50 coins in the shop"}]
    assert B.money_out(good) == "" and not B.check(good)["errors"]


# ================================================================ defect 2: both MCP eras
def _tok(tenant="default"):
    from app.gamedesk import editor as E
    return E.create_token(tenant, "t")["token"]


def _post(c, tok, body, hdr=None):
    h = {"Authorization": f"Bearer {tok}"}
    h.update(hdr or {})
    return c.post("/mcp/gamedesk", json=body, headers=h)


def test_the_current_mcp_revision_works_without_the_removed_handshake(gd):  # noqa: F811
    from app.gamedesk import editor as E
    from app.main import app
    c, tok = TestClient(app), _tok()
    assert "2026-07-28" in E.PROTOCOLS and E.MODERN[0] == "2026-07-28"
    # server/discover is MUST-implement in the current revision
    r = _post(c, tok, {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": {E.PV_KEY: "2026-07-28"}}})
    res = r.json()["result"]
    assert "2026-07-28" in res["supportedVersions"] and res["resultType"] == "complete"
    assert res["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "hoola-gamedesk"
    assert "hoola_studio_next" in res["tools"] and res["ttlMs"] and r.headers["mcp-protocol-version"] == "2026-07-28"
    # a version declared in _meta, and a version declared only in the HTTP header
    for body, hdr in (({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"_meta": {E.PV_KEY: "2026-07-28"}}}, None),
                      ({"jsonrpc": "2.0", "id": 3, "method": "tools/list"}, {"MCP-Protocol-Version": "2026-07-28"})):
        got = _post(c, tok, body, hdr).json()["result"]["tools"]
        assert len(got) >= 13
    # an unsupported version is the spec's own error, listing what we do support
    e = _post(c, tok, {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {"_meta": {E.PV_KEY: "1900-01-01"}}}).json()["error"]
    assert e["code"] == E.UNSUPPORTED == -32022 and "2026-07-28" in e["data"]["supported"] and e["data"]["requested"] == "1900-01-01"
    # the legacy handshake still answers, so a dual-era client keeps working
    old = _post(c, tok, {"jsonrpc": "2.0", "id": 5, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}).json()
    assert old["result"]["protocolVersion"] == "2025-06-18" and old["result"]["instructions"]
    # and a real tool call carrying the modern version works end to end
    out = _post(c, tok, {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                         "params": {"name": "hoola_projects", "arguments": {}, "_meta": {E.PV_KEY: "2026-07-28"}}}).json()
    assert out["result"]["isError"] is False


# ================================================================ the Arena: the fixed brief set
def test_the_brief_set_is_fixed_and_seeded():
    from app.gamedesk import arena as A
    bs = A.brief_set()
    assert len(bs) == len(A.GENRES) * len(A.SETTINGS) == 500
    assert [b["id"] for b in A.brief_set()] == [b["id"] for b in bs]        # stable forever
    assert len({b["id"] for b in bs}) == len(bs)
    assert all(b["orientation"] in ("portrait", "landscape") and b["brief"] for b in bs)
    a1, a2, other = A.pick(10, 1), A.pick(10, 1), A.pick(10, 2)
    assert [x["id"] for x in a1] == [x["id"] for x in a2]                  # same seed = the same work
    assert [x["id"] for x in a1] != [x["id"] for x in other]
    assert len({x["genre"] for x in a1}) >= 8                              # spread across genres
    cat = A.catalogue("runner", 5)
    assert cat["total"] == 500 and all(b["genre"] == "runner" for b in cat["briefs"])


# ================================================================ originality, measured
def test_originality_counts_only_the_axes_that_have_evidence():
    from app.gamedesk import arena as A
    taps = {"main.gd": "extends Node\nfunc _unhandled_input(e):\n\tif e is InputEventScreenTouch:\n\t\tvar a := Area2D.new()\n"}
    keys = {"main.gd": "extends Node\nfunc _input(e):\n\tvar l := Label.new()\n"}
    d1, d2 = A.dna(taps, "tap to collect coins and dodge"), A.dna(keys, "drive and aim, then shoot")
    assert A.closeness(d1, d1) == 1.0, "a game must be identical to itself (an empty axis is no evidence, not a difference)"
    assert A.closeness(d1, d2) < 0.3
    assert A.closeness({}, {}) == 0.0 and A.closeness(d1, {}) == 0.0
    rich = A.dna(taps, "tap to collect coins and dodge", {"entities": {"enemy": [1, 2]}, "style": {"palette": ["#FF0000"]}})
    assert A.closeness(rich, rich) == 1.0 and A.closeness(rich, d1) < 1.0  # a Bible is more evidence, not less alike
    same = A.sameness({"a": d1, "b": d2, "c": d1})
    assert same["a"] == 1.0 and same["b"] < 0.3                            # a is a twin of c; b is its own thing
    assert "collect" in d1["verbs"] and "Area2D" in d1["nodes"] and "InputEventScreenTouch" in d1["inputs"]


def test_the_judge_output_is_cleaned_and_never_invented():
    from app.gamedesk import arena as A
    assert A.parse_json('```json\n{"scores": {"looks": 7}, "overall": 6.5}\n```') == {"scores": {"looks": 7}, "overall": 6.5}
    assert A.parse_json("the model chatted instead") == {} and A.parse_json("") == {}
    out = A.clean_scores({"scores": {c: 99 for c in A.CRITERIA}, "overall": -5, "worst": "x" * 400})
    assert all(v == 10.0 for v in out["scores"].values()) and out["overall"] == 0.0 and len(out["worst"]) == 200
    assert A.clean_scores({"scores": {c: 6 for c in A.CRITERIA}})["overall"] == 6.0   # averaged when not given
    assert A.judge([], {}, {}) is None                                     # no frames = no score, never a guess


# ================================================================ the card is measured by playing
def test_the_card_is_engine_facts_and_fun_is_not_assessed():
    from app.gamedesk import arena as A
    b = A.brief_set()[0]
    played = {"started": True, "responds": True, "errors": 0, "reached_end": True, "fps": 58.0, "load_s": 2.1,
              "events": ["game_over", "score"], "state_keys": ["score"]}
    c = A.card(b, "g1", played, 12.5, 3.0, {"scores": {k: 6 for k in A.CRITERIA}, "overall": 6.0}, {"verbs": ["tap"]}, None)
    assert c["playable"] is True and c["fps"] == 58.0 and c["inr"] == 12.5
    assert "NOT ASSESSED" in c["fun"] and "a real player has to say" in c["fun"]
    broke = A.card(b, "", {"started": False, "errors": 2, "responds": False, "reached_end": False}, 0, 0, None, None, None)
    assert broke["playable"] is False
    runs = A.card(b, "g2", {"started": True, "responds": False, "errors": 0, "reached_end": False}, 1, 1, None, None, None)
    assert runs["playable"] is False, "a game that starts but answers no input is NOT playable"
    s = A.summarize([c, broke, runs])
    assert s["games"] == 3 and s["started_pct"] == 66.7 and s["playable_pct"] == 33.3 and s["responds_pct"] == 33.3
    assert s["judge"] == 6.0 and s["fun"] == "NOT ASSESSED" and s["total_inr"] == 13.5


def test_responds_is_measured_against_the_idle_run(monkeypatch, tmp_path):
    """RESPONDS must mean 'an input changed something the idle run never saw' - not merely 'the bots ran'."""
    from app.gamedesk import arena as A
    from app.gamedesk import qa as Q
    plans = {"idle": {"state": {"score": 0}, "events": ["ready"]},
             "monkey": {"state": {"score": 7}, "events": ["ready", "game_over"]},
             "keys": {"state": {"score": 0}, "events": ["ready"]}}

    def fake(build, out, orientation, bot, seed=1, seconds=10, profile="desktop", actions=None):
        p = plans[bot]
        return {"bot": bot, "profile": profile, "ok": True, "load_s": 1.0, "fps": [60, 59], "frames": 600,
                "errors": [], "shots": [], "state": p["state"], "events": p["events"]}
    monkeypatch.setattr(Q, "run_bot", fake)
    got = A.play(tmp_path, "portrait", tmp_path / "o")
    assert got["started"] and got["responds"] is True and got["reached_end"] is True and got["fps"] == 59.5
    plans["monkey"] = plans["keys"] = dict(plans["idle"])                  # nothing an input did changed anything
    dead = A.play(tmp_path, "portrait", tmp_path / "o2")
    assert dead["started"] and dead["responds"] is False and dead["reached_end"] is False


# ================================================================ a whole run, with a stubbed builder
def test_a_run_builds_judges_scores_originality_and_compares(gd, monkeypatch, tmp_path):  # noqa: F811
    from app.gamedesk import arena as A
    A.ensure_tables()
    made: list[str] = []

    def one(b):
        made.append(b["id"])
        return f"game-{b['id']}", 3.0, 1.0
    cards = {}

    def card_for(b, builder=None):
        gid, inr, mins = one(b)
        played = {"started": True, "responds": True, "errors": 0, "reached_end": True, "fps": 60.0, "load_s": 1.0,
                  "events": ["game_over"], "state_keys": ["score"], "shots": []}
        d = {"verbs": ["tap"], "nodes": ["Area2D"], "inputs": ["InputEventScreenTouch"], "ends": ["game_over"],
             "entity_kinds": [], "palette": []} if b["genre"] != "quiz" else \
            {"verbs": ["answer"], "nodes": ["Button"], "inputs": ["_input"], "ends": ["score"], "entity_kinds": [], "palette": []}
        c = A.card(b, gid, played, inr, mins, {"scores": {k: 6 for k in A.CRITERIA}, "overall": 6.0}, d, None)
        cards[b["id"]] = c
        return c
    monkeypatch.setattr(A, "_one_card", card_for)
    monkeypatch.setattr(A, "_spent_inr", lambda: 0.0)
    r = A.start(n=4, seed=3, note="first run", background=False)
    A._go(r["id"])                                                         # run it in this thread, deterministically
    v = A.view(r["id"])
    assert v["status"] == "done" and len(v["items"]) == 4 and len(made) == 4
    assert v["summary"]["playable_pct"] == 100.0 and v["summary"]["judge"] == 6.0
    assert all(it.get("sameness") is not None for it in v["items"]), "originality is scored after the whole run"
    twins = [it for it in v["items"] if it["genre"] != "quiz"]
    if len(twins) > 1:
        assert max(it["sameness"] for it in twins) == 1.0                  # same DNA twice = caught, not praised
    A.start(n=2, background=False)                                         # left running: one run at a time
    with pytest.raises(A.ArenaError, match="pehle se"):
        A.start(n=2, background=False)
    A.finish_running()
    r2 = A.start(n=4, seed=3, note="second run", background=False)
    A._go(r2["id"])
    cmp = A.compare(r["id"], r2["id"])
    assert "the same work judged twice" in cmp["note"]
    for row in cmp["rows"]:
        assert row["verdict"] == "same"
    r3 = A.start(n=2, seed=9, background=False)
    A._go(r3["id"])
    assert "DIFFERENT seed" in A.compare(r["id"], r3["id"])["note"]        # an unfair comparison says so
    assert A.runs(5)[0]["number"] and A.stop(r["id"])["stopping"] is True


def test_lower_is_better_is_the_right_way_round(gd, monkeypatch):  # noqa: F811
    """A run of TWINS must score worse on same-ness than a run of different games, and compare() must say so."""
    from app.gamedesk import arena as A
    A.ensure_tables()
    monkeypatch.setattr(A, "_spent_inr", lambda: 0.0)
    tap = {"verbs": ["tap"], "nodes": ["Area2D"], "inputs": ["InputEventScreenTouch"], "ends": ["game_over"],
           "entity_kinds": [], "palette": []}
    other = {"verbs": ["answer"], "nodes": ["Button"], "inputs": ["_input"], "ends": ["score"],
             "entity_kinds": [], "palette": []}
    ids = []
    for twins in (True, False):
        seen = {"n": 0}

        def mk(b, builder=None, twins=twins, seen=seen):
            seen["n"] += 1
            d = tap if (twins or seen["n"] == 1) else other
            return A.card(b, "g", {"started": True, "responds": True, "errors": 0, "reached_end": True, "fps": 60},
                          1.0, 1.0, {"scores": {k: 6.0 for k in A.CRITERIA}, "overall": 6.0}, d, None)
        monkeypatch.setattr(A, "_one_card", mk)
        r = A.start(n=2, seed=1, background=False)
        A._go(r["id"])
        ids.append(r["id"])
    twin_run, varied_run = (A.view(i)["summary"] for i in ids)
    assert twin_run["sameness"] == 1.0 and varied_run["sameness"] < 0.3
    rows = {x["metric"]: x for x in A.compare(ids[0], ids[1])["rows"]}
    assert rows["sameness"]["verdict"] == "better", "less same-ness must read BETTER, not just different"
    assert rows["judge"]["verdict"] == "same"
    assert "sameness" in A.LOWER_BETTER and "inr" in A.LOWER_BETTER and "fps" not in A.LOWER_BETTER


def test_one_game_has_no_originality_number(gd, monkeypatch):  # noqa: F811
    """With nothing to compare against, same-ness is None - 0.0 would read as 'perfectly original'."""
    from app.gamedesk import arena as A
    d = {"verbs": ["tap"], "nodes": ["Area2D"], "inputs": [], "ends": [], "entity_kinds": [], "palette": []}
    assert A.sameness({"only": d}) == {"only": None}
    assert A.sameness({}) == {}
    assert A.sameness({"a": d, "b": d}) == {"a": 1.0, "b": 1.0}


# ================================================================ API, tool, routing, console
def test_api_tool_and_console(gd, monkeypatch):  # noqa: F811
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.gamedesk import arena as A
    from app.main import app
    A.ensure_tables()
    monkeypatch.setattr(A, "_go", lambda rid, builder=None: None)
    c = TestClient(app)
    d = c.get("/api/gamedesk/arena").json()
    assert d["total_briefs"] == 500 and "runner" in d["genres"] and "rivals" in d["duels"]
    assert c.get("/api/gamedesk/arena/briefs?genre=match3&limit=3").json()["briefs"][0]["genre"] == "match3"
    started = c.post("/api/gamedesk/arena", json={"n": 2, "seed": 5, "note": "api"}).json()
    assert started["status"] == "running" and started["seed"] == 5
    assert c.get(f"/api/gamedesk/arena/{started['id']}").json()["number"] == started["number"]
    assert c.post(f"/api/gamedesk/arena/{started['id']}/stop").json()["stopping"] is True
    assert c.get("/api/gamedesk/arena/nope").status_code == 400
    assert c.post("/api/gamedesk/arena/duel", json={"brief": "nope", "rival": "x", "url": "https://e.in/g"}).status_code == 400
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    out = asyncio.run(tools.HANDLERS["game_arena"](ctx, action="status"))
    assert out["total_briefs"] == 500 and out["set"] == A.SET_V
    assert asyncio.run(tools.HANDLERS["game_arena"](ctx, action="briefs", genre="idle"))["briefs"][0]["genre"] == "idle"
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_arena"](staff, action="start"))
    other = Ctx(tenant_id="t2", conversation_id="c1")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_arena"](other, action="status"))
    assert tools.FAMILY_OF["game_arena"] == "gamedesk"
    desc = next(t for t in tools.TOOLS if t["name"] == "game_arena")["description"]
    assert "NOT ASSESSED" in desc and "4.3(b)" in desc
    for ask in ("game arena chalao", "hoola ke games ka score dekho"):
        assert "gamedesk" in admit.route(ask), ask
    emp = (Path(__file__).resolve().parents[2] / "server/app/static/console/employees.js").read_text()
    assert "gsArena" in emp and "arena: gsArena" in emp and 'data-gs-role="arena"' in emp and "NOT ASSESSED" in emp
