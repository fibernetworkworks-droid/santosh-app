"""v0.543.0 P3 THE SCRAPE LANE - the Google Maps PUBLIC LISTING grid, tests against a RECORDED-SHAPE fixture
with ZERO network: the fetch / robots / politeness boundaries are faked at module level (scrape._get,
scrape._robots_ok, scrape.GOOGLE_MIN_INTERVAL) while the parser constants, the grid math, the opt-in walls, the
caps, the block abort, the layout tripwire, the resume, the store writes, the run card, the tool and the API
run FOR REAL.

The fixture is built to the parser's own named constants (gmaps_parse.IDX_*, each with its sample) - the plan's
"loud-fail constants" law: a Google layout change breaks these expectations LOUDLY here, and in production the
APP_INITIALIZATION_STATE tripwire aborts the run instead of quietly harvesting nothing. Review TEXT is planted
in the fixture to prove it is NEVER read (rules.STORE_BOUNDARY)."""
import asyncio
import json
import time

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)
from tests.test_api import client  # noqa: F401

from app.leads import grid as G
from app.leads import gmaps_parse as GP
from app.leads import scrape as SC
from app.leads import service as S
from app.leads.models import ensure_tables

CENTER = {"lat": 18.5204, "lng": 73.8567, "name": "Pune"}


# ================================================================ the recorded-shape fixture
def _entry(name="Sharma Dental Clinic", kgmid="0x3bde7c9b1a2b3c4d:0x5f6e7d8c9b0a1b2c",
           place_id="ChIJN1t_tDeuEmsRUsoyG82frLA4", cid=2384729384, phone="+91 98765 43210",
           website="http://www.sharmadental.in", rating=4.5, reviews=128,
           lat=18.5204, lng=73.8567, address="Shop 4, MG Road, Pune, Maharashtra 411001"):
    """One listing array, built EXACTLY to the parser's named constants - each value is the constant's proof
    sample. Review TEXT is planted at index 48 to prove the reader never touches it."""
    a = [None] * 275
    a[1] = kgmid                                     # KGMID_RE shape match among the first KGMID_SCAN strings
    a[2] = address                                   # IDX_ADDRESS
    a[3] = [17, lat, lng, 0]                         # IDX_COORDS: lat at [1], lng at [2]
    a[4] = rating                                    # IDX_RATING
    a[7] = website                                   # IDX_WEBSITE
    a[9] = place_id                                  # IDX_PLACE_ID (ChIJ shape-checked)
    a[10] = cid                                      # IDX_CID (positive int shape-checked)
    a[11] = name                                     # IDX_TITLE (the shape test's anchor)
    a[14] = ["Dentist", "Dental clinic"]             # IDX_CATEGORIES
    a[48] = ["Great service, very caring staff - the best dentist in Pune!",
             "Excellent root canal treatment, highly recommended"]   # review TEXT - STORE_BOUNDARY says NO
    a[178] = phone                                   # IDX_PHONE
    a[269] = reviews                                 # IDX_REVIEW_COUNT - the COUNT only
    return a


def _page(entries, page=0):
    """A /maps/search-shaped page: the payload rides as nested JSON-encoded strings inside
    window.APP_INITIALIZATION_STATE (the shape the parser's walker decodes). The visible chrome is real too -
    a search page carries headers/nav (a script-only page IS the block detector's 'empty shell', by design)."""
    payload = json.dumps([["junk header row"], json.dumps(entries)])
    init = [None, "AF_initDataCallback", None, payload, f"!7i20!8i{20 + 20 * page}"]
    return ("<!doctype html><html><head><title>dental clinic near Pune - Google Maps</title></head><body>"
            '<div role="navigation"><a href="/maps">Maps</a> <a href="/maps/@18.52,73.85,15z">Pune</a> '
            '<a href="/preferences">Settings</a><h1>Google Maps</h1>'
            "<p>dental clinic near Pune</p></div>"
            "<script>window.APP_INITIALIZATION_STATE=" + json.dumps(init) +
            ";window.APP_FLAGS='';</script></body></html>")


WALL = ("<html><head><title>Sorry</title></head><body>Our systems have detected unusual traffic from your "
        "computer network. Please try your request again later.</body></html>")
DEAD = "<html><body><p>consent page - nothing here</p></body></html>"      # no init state at all


class _P:
    def __init__(self, url, html, status=200):
        self.url, self.html_content, self.status = url, html, status


def fake_fetch(monkeypatch, overrides=None, default=None, interval=0.0):
    """The network boundary: scrape._get answers from the recorded world. `overrides` maps cell (i,j) -> html;
    everything else gets `default` (3 fixture listings). Returns the fetch log (the exact URLs, in order)."""
    calls: list[str] = []

    def fake_get(url, tenant_id, **k):
        calls.append(url)
        hit = (overrides or {}).get(url, default)
        if hit is None:
            raise ConnectionError(f"fixture world has no page for {url}")
        html, status = hit if isinstance(hit, tuple) else (hit, 200)
        return _P(url, html, status)

    monkeypatch.setattr(SC, "_get", fake_get)
    monkeypatch.setattr(SC, "_robots_ok", lambda u: True)   # the robots POLICY is tested separately below
    monkeypatch.setattr(SC, "GOOGLE_MIN_INTERVAL", interval)
    SC._LAST_HIT.clear()
    return calls


def _cell_urls(sweep_km=1.0, zoom=15, query="dental clinic"):
    cells = G.bbox_cells(CENTER, sweep_km, zoom)
    return cells, {GP.search_url(query, c["lat"], c["lng"], c["zoom"], 0): (c["i"], c["j"]) for c in cells}


def optin(tenant="t1", on=True):
    return S.set_scrape_optin(tenant, on, "owner")


DEFAULT_PAGE = _page([_entry(), _entry(name="Patil Dental Care", kgmid="0x3bde7c9b1a2b3c4e:0x5f6e7d8c9b0a1b2d",
                                       place_id="ChIJX1t_tDeuEmsRUsoyG82frLB9", cid=2384729385,
                                       phone="+91 98765 43211", website="", rating=4.1, reviews=57,
                                       lat=18.5211, lng=73.8571, address="Shop 9, FC Road, Pune 411005"),
                      _entry(name="Kirita Clinic", kgmid="", place_id="", cid=0, phone="9876500002",
                             website="", rating=None, reviews=None, lat=18.5219, lng=73.8579,
                             address="Lane 3, Kothrud, Pune")])   # no ids -> phone key


# ================================================================ the URL builder (the one-line correction point)
def test_search_url_paging_sample():
    u0 = GP.search_url("dentists", 18.5204, 73.8567, 15)
    u1 = GP.search_url("dentists", 18.5204, 73.8567, 15, page=1)
    assert u0 == ("https://www.google.com/maps/search/dentists/@18.520400,73.856700,15z"
                  "?hl=en&gl=in&pb=!7i20!8i20")
    assert u1.endswith("pb=!7i20!8i40") and GP.search_url("dentists", 18.5204, 73.8567, 15, page=2).endswith("!8i60")
    assert quote_in(u0, "dentists")


def quote_in(url, q):
    from urllib.parse import quote_plus
    return quote_plus(q) in url


# ================================================================ the parser (constants + loud tripwire)
def test_parser_reads_every_constant_from_the_fixture():
    rows = GP.places(_page([_entry()]))
    assert len(rows) == 1
    r = rows[0]
    assert r["name"] == "Sharma Dental Clinic"                       # IDX_TITLE 11
    assert r["address"] == "Shop 4, MG Road, Pune, Maharashtra 411001"   # IDX_ADDRESS 2
    assert (r["lat"], r["lng"]) == (18.5204, 73.8567)                # IDX_COORDS 3 -> [1],[2]
    assert r["rating"] == 4.5 and r["review_count"] == 128           # IDX_RATING 4, IDX_REVIEW_COUNT 269
    assert r["website"] == "http://www.sharmadental.in" and r["phone"] == "+91 98765 43210"   # 7, 178
    assert r["category"] == "Dentist, Dental clinic"                 # IDX_CATEGORIES 14
    assert r["place_id"] == "ChIJN1t_tDeuEmsRUsoyG82frLA4"           # IDX_PLACE_ID 9
    assert r["cid"] == "2384729384" and r["kgmid"].startswith("0x")  # IDX_CID 10 + the kgmid SHAPE scan
    assert r["parser_version"] == "v0.543.0-gm1"


def test_parser_never_reads_the_review_text_store_boundary():
    rows = GP.places(_page([_entry()]))
    blob = json.dumps(rows, ensure_ascii=False)
    assert "Great service" not in blob and "root canal" not in blob   # the wall the plan wrote in section 8


def test_parser_loud_when_there_is_no_init_state():
    with pytest.raises(GP.GmapsParseError, match="APP_INITIALIZATION_STATE"):
        GP.places(DEAD)
    with pytest.raises(GP.GmapsParseError):
        GP.places("<html><script>window.APP_INITIALIZATION_STATE=[1,2,{\"o\":")   # unclosed


def test_parser_bracket_in_a_title_cannot_end_the_scan_early():
    e = _entry(name="Sharma [Dental] Clinic \"and Sons\"")
    rows = GP.places(_page([e]))
    assert rows and rows[0]["name"] == 'Sharma [Dental] Clinic "and Sons"'


def test_parser_shape_test_rejects_what_is_not_a_listing():
    assert GP.places(_page([])) == []                    # a valid search page, honestly empty (sparse cell)
    assert GP.places(_page([["short", "arrays"], [None] * 40, "a string"])) == []
    rows = GP.places(_page([_entry(kgmid="")]))          # kgmid optional: the rest still reads
    assert rows and rows[0]["kgmid"] == "" and rows[0]["place_id"].startswith("ChIJ")


def test_ids_by_shape_not_by_position():
    a = _entry()
    a[1], a[5] = None, a[1]                              # the kgmid MOVED to index 5 - the shape finds it
    rows = GP.places(_page([a]))
    assert rows[0]["kgmid"].startswith("0x3bde")
    rows2 = GP.places(_page([_entry(place_id="0xaaaaaa:0xbbbbbb")]))   # a ChIJ-less entry: the 0x string is kgmid, NOT place_id
    assert rows2[0]["place_id"] == "" and rows2[0]["kgmid"].startswith("0x")
    rows3 = GP.places(_page([_entry(cid=-5)]))           # a negative int is not a cid
    assert rows3[0]["cid"] == ""


# ================================================================ the grid math (zoom ladder, measured yield)
def test_grid_cells_cover_the_bbox_at_the_zooms_cell_size():
    cells = G.bbox_cells(CENTER, 3.0, 15)
    assert len(cells) == 49                              # ceil(3/1)=3 -> 7x7, zoom 15 = 1 km cells
    assert all(c["zoom"] == 15 and c["cell_km"] == 1.0 and c["status"] == "pending" for c in cells)
    assert G.cell_km(17) == 0.25 and G.cell_km(13) == 4.0
    with pytest.raises(G.GridError, match="ladder"):
        G.cell_km(20)


def test_grid_refuses_past_the_ceiling_with_the_count_named():
    with pytest.raises(G.GridError, match=r"\b625\b"):   # sweep 3 km @ zoom 17 (0.25 km cells) = 25x25
        G.bbox_cells(CENTER, 3.0, 17)
    with pytest.raises(G.GridError, match="ceiling"):
        G.bbox_cells(CENTER, 3.0, 15, max_cells=10)


def test_choose_zoom_is_measured_yield_never_hope():
    assert G.choose_zoom([20, 20, 20, 19], 15)["step"] == "finer"
    assert G.choose_zoom([0, 0, 1, 0], 15)["step"] == "coarser"
    assert G.choose_zoom([10, 12, 9], 15)["step"] == "stay"
    assert G.choose_zoom([25, 25], 17)["step"] == "finest"      # the edge says so, no pretend step
    assert G.choose_zoom([0, 0], 13)["step"] == "coarsest"
    assert G.choose_zoom([], 15)["step"] == "coarser"           # an empty run measured nothing -> sparse


# ================================================================ the opt-in (the permission slip, OFF by default)
def test_scrape_optin_default_off_and_the_flip_records_the_walls(env):
    ensure_tables()
    assert S.scrape_opted_in("t1") is False              # no row = OFF, the amended rule's default
    out = optin("t1", True)
    assert out["ok"] and out["scrape_optin"] is True and out["actor"] == "owner"
    assert any("PUBLIC BUSINESS LISTING DATA" in w for w in out["walls"])        # the amended rule text
    assert any("review TEXT" in w for w in out["walls"])                         # the store boundary
    assert any("kisi ko message" in w and "nahi bhejta" in w for w in out["walls"])   # the never-sends wall
    assert S.scrape_opted_in("t1") is True
    off = optin("t1", False)
    assert off["scrape_optin"] is False and S.scrape_opted_in("t1") is False


def test_scrape_run_refuses_without_optin_and_leaves_no_run_row(env):
    ensure_tables()
    with pytest.raises(S.LeadsError, match="opt-in"):
        asyncio.run(S.run_scrape("t1", "dentists Pune", "dental clinic", center=CENTER))
    assert S.runs("t1") == []                            # nothing ran - no receipt is manufactured


def test_plan_refuses_scrape_until_opted_in_then_carries_the_cap_check(env):
    ensure_tables()
    p = S.plan("t1", "Nagpur contractors", ["SCRAPE"], "Nagpur")
    assert p["ok"] is False and p["refused_lanes"] == ["SCRAPE"]
    assert "OFF" in p["why"][0] and p["opt_in"]["how"].startswith("leads_run action=scrape_optin")
    optin("t1", True)
    p2 = S.plan("t1", "Nagpur contractors", ["SCRAPE"], "Nagpur")
    assert p2["ok"] is True and "cap_check" in p2


def test_her_data_is_pinned_to_the_her_data_lane(env):
    ensure_tables()
    with pytest.raises(S.LeadsError, match="HER_DATA"):
        S.run_her_data("t1", "x", [], "f.csv", lanes=["SCRAPE"])
    with pytest.raises(S.LeadsError, match="HER_DATA"):
        S.run_her_data("t1", "x", [], "f.csv", lanes=["REGISTRY"])


# ================================================================ the runner (caps, block abort, resume, bill)
def test_scrape_run_happy_path_provenance_and_dedup(env, monkeypatch):
    ensure_tables()
    optin("t1", True)
    cells, _ = _cell_urls()
    calls = fake_fetch(monkeypatch, default=DEFAULT_PAGE)
    out = asyncio.run(S.run_scrape("t1", "Pune dentists", "dental clinic", center=CENTER, sweep_km=1.0, zoom=15,
                                   max_rows=1000))
    assert out["ok"] is True and out["run"]["status"] == "DONE", out.get("error") or json.dumps(out, default=str)[:300]
    assert out["run"]["lanes"] == ["SCRAPE"]
    assert len(calls) == len(cells)                      # 9 cells, one page each (3 < 20 = last page)
    card = out["run"]
    assert card["found"] == 27 and card["duped"] == 24 and card["kept"] == 3   # 3 businesses, seen 9 times
    assert card["bill"]["inr"] == 0.0 and card["bill"]["http_requests"] == len(cells)
    assert card["bill"]["ladder"]["median_yield"] == 3.0 and card["bill"]["geocode_inr"] == 0.0
    assert out["cells"]["done"] == len(cells)
    rows = S.rows("t1", lane="SCRAPE")["rows"]
    assert len(rows) == 3
    by_name = {r["name"]: r for r in rows}
    assert by_name["Sharma Dental Clinic"]["key_type"] == "kgmid"            # the strongest id wins
    assert by_name["Sharma Dental Clinic"]["phone"] == "919876543210"        # E.164, the house law
    assert by_name["Sharma Dental Clinic"]["source_lane"] == "SCRAPE"
    assert by_name["Sharma Dental Clinic"]["parser_version"] == "v0.543.0-gm1"
    assert "/maps/search/" in by_name["Sharma Dental Clinic"]["source_url"]  # the exact page it was read from
    assert by_name["Kirita Clinic"]["key_type"] == "phone_e164"              # no ids -> the phone keys it
    assert all("Great service" not in json.dumps(r) for r in rows)           # the store boundary held
    plan_json = card["plan"]
    assert plan_json["kind"] == "scrape" and all(c["status"] == "done" for c in plan_json["cells"])
    assert plan_json["politeness"]["per_host_1s"] == SC.GOOGLE_MIN_INTERVAL


def test_scrape_cap_refused_at_plan_time_and_cell_ceiling(env, monkeypatch):
    ensure_tables()
    optin("t1", True)
    monkeypatch.setattr(env["settings"], "leads_max_rows_per_run", 100)
    out = asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, max_rows=200))
    assert out["ok"] is False and out["run"]["status"] == "REFUSED" and "100" in out["run"]["error"]
    # the row cap refuses BEFORE the grid is even built - with the ask under the cap, the cell ceiling speaks
    with pytest.raises(S.LeadsError, match=r"\b160801\b"):
        asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, sweep_km=50.0, zoom=17,
                                 max_rows=50))
    assert all(r["status"] != "DONE" for r in S.runs("t1"))                  # no grid was ever built into a run


def test_scrape_unknown_zoom_and_missing_where_refused(env):
    ensure_tables()
    optin("t1", True)
    with pytest.raises(S.LeadsError, match="ladder"):
        asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, zoom=20))
    with pytest.raises(S.LeadsError, match="Kaunsa"):
        asyncio.run(S.run_scrape("t1", "ask", "dental clinic"))   # no near, no center: the ONE question
    with pytest.raises(S.LeadsError, match="Query"):
        asyncio.run(S.run_scrape("t1", "ask", "", center=CENTER))


def test_scrape_block_wall_aborts_the_run_with_the_wall_named(env, monkeypatch):
    ensure_tables()
    optin("t1", True)
    cells, url_of = _cell_urls()
    blocked_url = [u for u, ij in url_of.items() if ij == (cells[1]["i"], cells[1]["j"])][0]
    calls = fake_fetch(monkeypatch, overrides={blocked_url: WALL}, default=DEFAULT_PAGE)
    out = asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, sweep_km=1.0))
    assert out["ok"] is False and out["run"]["status"] == "ABORTED"
    assert "unusual traffic" in out["error"] and "block wall" in out["error"]
    assert len(calls) == 2                                # the run STOPPED at the wall - it did not muscle on
    assert out["cells"]["done"] == 1 and out["bill"]["http_requests"] == 2
    rows = S.rows("t1", lane="SCRAPE")["rows"]
    assert len(rows) == 3                                 # what came before the wall stays, provenance intact
    plan_json = out["run"]["plan"]
    st = {(c["i"], c["j"]): c["status"] for c in plan_json["cells"]}
    assert st[(cells[0]["i"], cells[0]["j"])] == "done" and st[(cells[1]["i"], cells[1]["j"])] == "blocked"


def test_scrape_parse_tripwire_aborts_two_dead_cells(env, monkeypatch):
    ensure_tables()
    optin("t1", True)
    calls = fake_fetch(monkeypatch, default=DEAD)         # every page: no APP_INITIALIZATION_STATE at all
    out = asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, sweep_km=1.0))
    assert out["ok"] is False and out["run"]["status"] == "ABORTED"
    assert "layout badla" in out["error"]
    assert len(calls) == 2                                # the tripwire fired after TWO consecutive dead cells


def test_scrape_resume_continues_the_grid_and_a_done_run_is_a_no_op(env, monkeypatch):
    ensure_tables()
    optin("t1", True)
    cells, url_of = _cell_urls()
    blocked_url = [u for u, ij in url_of.items() if ij == (cells[1]["i"], cells[1]["j"])][0]
    calls1 = fake_fetch(monkeypatch, overrides={blocked_url: WALL}, default=DEFAULT_PAGE)
    out1 = asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, sweep_km=1.0))
    assert out1["run"]["status"] == "ABORTED" and len(calls1) == 2
    calls2 = fake_fetch(monkeypatch, default=DEFAULT_PAGE)                     # the wall is gone now
    out2 = asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, sweep_km=1.0,
                                    resume_run_id=out1["run"]["id"]))
    assert out2["ok"] is True and out2["run"]["status"] == "DONE" and not out2.get("no_op")
    assert len(calls2) == len(cells) - 1                  # only the DONE cell is skipped - the BLOCKED cell is
    # retried (that is WHY she resumes: the wall lifted); rows already kept are counted duped, never re-written
    assert out2["cells"]["done"] == len(cells)
    calls3 = fake_fetch(monkeypatch, default=DEFAULT_PAGE)
    out3 = asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, sweep_km=1.0,
                                    resume_run_id=out2["run"]["id"]))
    assert out3.get("no_op") is True and calls3 == []     # the BADA CATALOGUE idempotency law: zero fetches
    with pytest.raises(S.LeadsError, match="nahi mila"):
        asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, resume_run_id="lr_nope"))
    with pytest.raises(S.LeadsError, match="SCRAPE lane ka nahi"):
        other = S.run_her_data("t1", "x", [{"name": "A", "phone": "9876500003"}], "f.csv")
        asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, resume_run_id=other["run"]["id"]))


def test_scrape_max_rows_bound_stops_the_grid_midway(env, monkeypatch):
    ensure_tables()
    optin("t1", True)
    fake_fetch(monkeypatch, default=DEFAULT_PAGE)
    out = asyncio.run(S.run_scrape("t1", "ask", "dental clinic", center=CENTER, sweep_km=1.0, max_rows=4))
    assert out["ok"] is True and out["stopped_by_bound"] is True
    assert out["run"]["found"] == 4                       # 4 seen, then the loop stopped - never a quiet walk-on


def test_scrape_politeness_and_the_robots_policy(env, monkeypatch):
    import app.agent.scrape_tools as ST
    assert SC.MAX_CONCURRENCY == 2 and SC.GOOGLE_MIN_INTERVAL >= 1.0    # the plan's named ceilings, unpached
    monkeypatch.setattr(SC, "GOOGLE_MIN_INTERVAL", 0.05)
    SC._LAST_HIT.clear()
    t0 = time.monotonic()
    SC._polite("www.google.com")
    SC._polite("www.google.com")
    assert time.monotonic() - t0 >= 0.04                  # the same host waited its turn (1 req/s)
    SC._LAST_HIT.clear()
    def boom(url, timeout=8):                             # the non-Google gate WOULD be consulted
        raise AssertionError("non-google host must pass through scrape_tools._robots_allowed")
    monkeypatch.setattr(ST, "_robots_allowed", boom)
    assert SC._robots_ok("https://www.google.com/maps/search/x") is True     # owner ask 5 Nov 2026 (amended rule)
    with pytest.raises(AssertionError):
        SC._robots_ok("https://www.justdial.com/Pune/dentists")              # every non-Google host obeys robots
    monkeypatch.setattr(SC, "GOOGLE_MIN_INTERVAL", 1.0)   # restore the constant for the module-shape asserts


# ================================================================ the surface (tool + API + card)
def test_leads_run_tool_scrape_and_optin(env, monkeypatch):
    from app.agent.leads_tools import LEADS_HANDLERS

    class _C:                                             # the duck-typed Ctx the handler reads
        tenant_id, conversation_id, actor = "t1", "c1", "owner"

    ensure_tables()
    with pytest.raises(Exception, match="opt-in"):
        asyncio.run(LEADS_HANDLERS["leads_run"](_C(), action="scrape", ask="x", query="dental clinic",
                                                center=CENTER))
    out = asyncio.run(LEADS_HANDLERS["leads_run"](_C(), action="scrape_optin", ask="scrape on karo", on=True))
    assert out["scrape_optin"] is True and out["walls"]
    cells, _ = _cell_urls()
    fake_fetch(monkeypatch, default=DEFAULT_PAGE)
    out2 = asyncio.run(LEADS_HANDLERS["leads_run"](_C(), action="scrape", ask="Pune dentists",
                                                   query="dental clinic", center=CENTER, sweep_km=1.0))
    assert out2["ok"] is True and out2["run"]["status"] == "DONE" and out2["run"]["lanes"] == ["SCRAPE"]


def test_scrape_through_the_api(env, monkeypatch):
    ensure_tables()
    with client(monkeypatch, env, api_key="secret") as c:
        h = {"Authorization": "Bearer secret"}
        bad = c.post("/api/leads/runs/scrape", headers=h,
                     json={"ask": "x", "query": "dental clinic", "center": CENTER})
        assert bad.status_code == 400 and "opt-in" in bad.json()["detail"]
        flip = c.post("/api/leads/scrape-optin", headers=h, json={"on": True})
        assert flip.status_code == 200 and flip.json()["scrape_optin"] is True
        cells, _ = _cell_urls()
        fake_fetch(monkeypatch, default=DEFAULT_PAGE)
        ok = c.post("/api/leads/runs/scrape", headers=h,
                    json={"ask": "Pune dentists", "query": "dental clinic", "center": CENTER, "sweep_km": 1.0})
        assert ok.status_code == 200 and ok.json()["run"]["status"] == "DONE"
        got = c.get("/api/leads/rows", headers=h, params={"lane": "SCRAPE"}).json()
        assert got["total"] == 3 and got["rows"][0]["source_lane"] == "SCRAPE"
        off = c.post("/api/leads/scrape-optin", headers=h, json={"on": False})
        assert off.status_code == 200 and off.json()["scrape_optin"] is False


def test_card_guards_carry_the_scrape_walls(env):
    from app.quality import leadscard
    card = leadscard.free_card()
    g = card["guards"]
    for k in ("scrape_built", "scrape_opt_in_default_off", "scrape_optin_refused", "scrape_uses_existing_stack",
              "scrape_politeness", "scrape_faces_public_site", "scrape_abort_on_block", "scrape_store_boundary",
              "rule_text_amended", "lane_refused_by_name", "no_second_google_client", "cap_refuses"):
        assert g[k] is True, f"guard {k} = {g[k]}"
    assert card["set"] == 6 and card["guards_ok"] == len(g)   # v0.545.0: set v6 - the outreach handoff walls joined


def test_amended_rule_text_is_the_only_scrape_rule():
    # the plan's non-negotiable, checked twice: the leadscard guard AND this test read the same file
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    flat = " ".join((root / "CLAUDE.md").read_text(encoding="utf-8").split())   # wrap-tolerant, like the card
    assert "A LEADS scrape lane for PUBLIC BUSINESS LISTING DATA is allowed BY THE OWNER'S EXPLICIT ASK" in flat
    assert "opt-in per tenant and OFF by default" in flat
    assert "Official routes only: no scraping, no unofficial MCP" not in flat   # the old blanket ban is GONE
    from app.leads import rules as R
    assert R.SCRAPE_RULE_TEXT.split("allowed BY THE OWNER")[0] and R.LANE_BUILT["SCRAPE"] == "P3"


def test_no_second_fetch_client_in_the_scrape_lane():
    import inspect
    for mod in (SC, GP):
        src = inspect.getsource(mod).lower()
        assert "httpx" not in src and "aiohttp" not in src and "requests.get" not in src
        assert "playwright" not in src
