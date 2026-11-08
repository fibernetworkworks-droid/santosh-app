"""v0.541.0 OFFICIAL LANES - the REGISTRY lane (IndiaMART's own MCP server, through the existing app/indiamart.py)
and the OFFICIAL_API lane (Places through the EXISTING maps tools: maps.resolve / maps.nearby / maps.place_details,
billed under the mapsbill cap - NO second Google client). Everything runs OFFLINE against a fresh DB: the lanes'
network functions are faked at the module boundary, while the caps, the deduper, the provenance gate and the
mapsbill charge path run FOR REAL."""
import asyncio

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)
from tests.test_api import client  # noqa: F401

from app import leadscap, mapsbill
from app.leads import service as S
from app.leads.models import ensure_tables


# ---------------------------------------------------------------- fixtures at the module boundary
def _im(pid, company, city, phone="", location="", title=""):
    """A product shaped exactly like indiamart.search's own output (indiamart._product)."""
    return {"id": pid, "title": title or f"{company} - product {pid}", "price": "₹100", "price_value": 100.0,
            "unit": "bag", "image": "", "img": "", "brand": "", "category": "Cement", "company": company,
            "city": city, "location": location, "in_city": True, "phone": phone, "specs": [], "moq": "",
            "moq_unit": "", "rating": "", "rating_count": "", "gst_verified": True, "trust_seal": False,
            "member_since": "", "response_rate": "", "url": f"https://www.indiamart.com/{pid}/",
            "description": ""}


def fake_indiamart(monkeypatch, products_by_city, calls):
    from app import indiamart

    async def fake_search(search_term, query="", city="", brand="", specifications=None, min_price=None,
                          max_price=None, biztype=""):
        calls.append({"term": search_term, "city": city, "biztype": biztype})
        return {"search_term": search_term, "city": city, "filters": {}, "exact": None,
                "products": list(products_by_city.get(city, [])), "stats": {"priced": 0}, "at": ""}

    monkeypatch.setattr(indiamart, "search", fake_search)


def _pl(pid, name, phone="", website="", rating=None, reviews=None):
    """A place shaped like maps.nearby's own output (_place_row) - the PRO tier carries NO phone / website /
    rating: those are the expensive fields bought per place by place_details."""
    out = {"place_id": pid, "name": name, "address": f"{name}, FC Road, Pune", "lat": 18.5204, "lng": 73.8567,
           "type": "pharmacy", "maps_link": f"https://maps.google.com/?cid={pid}"}
    for k, v in (("phone", phone), ("website", website), ("rating", rating), ("reviews", reviews)):
        if v not in ("", None):
            out[k] = v
    return out


def fake_maps(monkeypatch, env, nearby_pages, details_calls, resolve="unset"):
    """Fake at the honest boundary: maps.resolve at module level (it never touches the cap here), and the HTTP
    TRANSPORT for everything else - so the REAL maps.nearby / maps.place_details / mapsbill.charge path runs and
    the cap tests exercise the actual charge-before-the-call machinery, not a stand-in. `resolve=None` makes the
    centre unresolvable; "unset" uses the default Pune centre."""
    import httpx
    from app import maps
    monkeypatch.setattr(env["settings"], "google_maps_api_key", "test-key")

    async def fake_resolve(text, tenant_id="", near=None):
        if resolve == "unset":
            return {"lat": 18.5204, "lng": 73.8567, "name": str(text), "address": str(text)}
        return resolve
    monkeypatch.setattr(maps, "resolve", fake_resolve)

    def _place_json(p):
        out = {"id": p["place_id"], "displayName": {"text": p["name"]},
               "formattedAddress": p.get("address", ""),
               "location": {"latitude": p.get("lat"), "longitude": p.get("lng")},
               "primaryTypeDisplayName": {"text": p.get("type", "")}}
        if p.get("maps_link"):
            out["googleMapsUri"] = p["maps_link"]
        return out

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "places:searchnearby" in u.lower():          # the real URL is places:searchNearby - match loosely
            page = nearby_pages.pop(0) if nearby_pages else []
            return httpx.Response(200, json={"places": [_place_json(p) for p in page]})
        if "/places/" in u and request.method == "GET":          # place details (case-sensitive: place ids are)
            pid = u.rsplit("/places/", 1)[1].split("?")[0]
            details_calls.append(pid)
            return httpx.Response(200, json={"id": pid, "displayName": {"text": f"Place {pid}"},
                                             "formattedAddress": "FC Road, Pune",
                                             "location": {"latitude": 18.5204, "longitude": 73.8567},
                                             "nationalPhoneNumber": "+91 98765 11111",
                                             "websiteUri": "https://medplus.in",
                                             "rating": 4.5, "userRatingCount": 120})
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(maps, "_client", lambda: client)


# ================================================================ the REGISTRY lane (IndiaMART)
def test_indiamart_keeps_sellers_and_dedups_products(env, monkeypatch):
    calls: list[dict] = []
    fake_indiamart(monkeypatch, {"Pune": [
        _im("p1", "Balaji Traders", "Pune", phone="+91 98765 00001"),
        _im("p1b", "Balaji Traders", "Pune", phone="+91 98765 00001", title="Balaji OPC 50kg"),   # same business
        _im("p2", "Deshmukh Hardware", "Pune", location="Market Yard, Pune"),                     # no phone
        _im("p3", "Kisan Agro", "Pune"),                                                          # phone AND location missing
    ]}, calls)
    out = asyncio.run(S.run_indiamart("t1", "cement sellers Pune", "cement", city="Pune", place="Pune",
                                      max_rows=100))
    assert out["ok"] is True
    r = out["run"]
    assert r["status"] == "DONE" and r["found"] == 4 and r["kept"] == 3 and r["duped"] == 1 and r["refused"] == 0
    store = S.rows("t1")
    assert store["total"] == 3
    a = next(x for x in store["rows"] if x["name"] == "Balaji Traders")
    assert a["key_type"] == "phone_e164" and a["key_value"] == "919876500001"      # E.164 house law
    b = next(x for x in store["rows"] if x["name"] == "Deshmukh Hardware")
    assert b["key_type"] == "name_address" and b["address"] == "Market Yard, Pune"
    c = next(x for x in store["rows"] if x["name"] == "Kisan Agro")
    assert c["key_type"] == "name_address"                                         # name + city fallback key
    for x in store["rows"]:
        assert x["source_lane"] == "REGISTRY" and x["source_url"].startswith("https://www.indiamart.com/")
        assert x["parser_version"].startswith("v0.689")
    assert r["bill"]["lane"] == "REGISTRY" and r["bill"]["calls"] == 1 and r["bill"]["inr"] == 0.0
    assert calls[0]["term"] == "cement" and calls[0]["city"] == "Pune"


def test_indiamart_re_run_is_a_no_op(env, monkeypatch):
    fake_indiamart(monkeypatch, {"Pune": [_im("p1", "Balaji Traders", "Pune", phone="98765000001"),
                                          _im("p2", "Deshmukh Hardware", "Pune", location="Market Yard")]}, [])
    asyncio.run(S.run_indiamart("t1", "ask", "cement", city="Pune", place="Pune"))
    again = asyncio.run(S.run_indiamart("t1", "same ask again", "cement", city="Pune", place="Pune"))
    assert again["run"]["kept"] == 0 and again["run"]["duped"] == 2 and again["run"]["status"] == "DONE"
    assert S.rows("t1")["total"] == 2


def test_indiamart_phone_dedups_across_lanes(env, monkeypatch):
    # the same BUSINESS arriving from her file and from IndiaMART collapses to ONE row (the phone is the key)
    S.run_her_data("t1", "her file", [{"name": "Balaji Traders", "phone": "98765 00001", "city": "Pune"}], "f.csv")
    fake_indiamart(monkeypatch, {"Pune": [_im("p1", "Balaji Traders", "Pune", phone="+919876500001")]}, [])
    out = asyncio.run(S.run_indiamart("t1", "cement", "cement", city="Pune", place="Pune"))
    assert out["run"]["kept"] == 0 and out["run"]["duped"] == 1
    assert S.rows("t1")["total"] == 1


def test_indiamart_without_a_place_gets_the_one_question(env):
    with pytest.raises(S.LeadsError, match="Kaunsa business"):
        asyncio.run(S.run_indiamart("t1", "cement sellers", "cement"))


def test_indiamart_max_rows_is_a_bound_not_a_truncation(env, monkeypatch):
    fake_indiamart(monkeypatch, {"Pune": [_im(f"p{i}", f"Seller {i}", "Pune", phone=f"98765000{i:02d}")
                                          for i in range(4)]}, [])
    out = asyncio.run(S.run_indiamart("t1", "ask", "cement", city="Pune", place="Pune", max_rows=2))
    assert out["run"]["found"] == 2 and out["run"]["kept"] == 2 and out["run"]["status"] == "DONE"
    assert out["bound"] == {"max_rows": 2, "stopped_by_bound": True}     # the card SAYS the bound stopped it


def test_indiamart_cap_refuses_at_plan_time(env, monkeypatch):
    monkeypatch.setattr(env["settings"], "leads_max_rows_per_run", 100)
    out = asyncio.run(S.run_indiamart("t1", "bada ask", "cement", city="Pune", place="Pune", max_rows=5000))
    assert out["ok"] is False and out["run"]["status"] == "REFUSED"
    assert "100" in out["plan"]["cap_refusal"]


def test_indiamart_error_aborts_the_run_with_the_reason(env, monkeypatch):
    from app import indiamart

    async def dead(search_term, query="", city="", brand="", specifications=None, min_price=None,
                   max_price=None, biztype=""):
        raise indiamart.IndiaMartError("IndiaMART ne mana kiya (HTTP 503).")
    monkeypatch.setattr(indiamart, "search", dead)
    out = asyncio.run(S.run_indiamart("t1", "ask", "cement", city="Pune", place="Pune"))
    assert out["ok"] is False and out["run"]["status"] == "ABORTED" and "mana kiya" in out["run"]["error"]


def test_indiamart_cities_cap_at_five(env, monkeypatch):
    calls: list[dict] = []
    fake_indiamart(monkeypatch, {}, calls)
    asyncio.run(S.run_indiamart("t1", "ask", "cement", city="Pune",
                                cities=["Nagpur", "Nashik", "Indore", "Surat", "Jaipur", "Kanpur"], place="Pune"))
    assert len(calls) == 5                                               # indiamart.MAX_CITIES, the module's own law


# ================================================================ the OFFICIAL_API lane (existing maps tools)
def test_place_cells_tile_the_circle_with_overlap():
    cells = S.place_cells({"lat": 18.5, "lng": 73.8}, sweep_km=3, cell_km=2)
    assert len(cells) == 5                                               # centre + 4 axis tiles, corners cut
    assert all(c["radius_m"] == 2000 for c in cells)
    with pytest.raises(S.LeadsError, match="cells"):
        S.place_cells({"lat": 18.5, "lng": 73.8}, sweep_km=60, cell_km=0.5)   # 400-cell ceiling, refused not run


def test_places_tiles_and_dedups_by_place_id(env, monkeypatch):
    pages = [[_pl("PID1", "Medplus Pharmacy"), _pl("PID2", "Apollo Pharmacy")],
             [_pl("PID2", "Apollo Pharmacy"), _pl("PID3", "Wellness Forever")]]
    fake_maps(monkeypatch, env, pages, [])
    out = asyncio.run(S.run_places("t1", "pharmacies Pune", ["pharmacy"], "Pune", sweep_km=3, cell_km=2))
    assert out["ok"] is True and out["cells"] == 5
    r = out["run"]
    assert r["status"] == "DONE" and r["found"] == 4 and r["kept"] == 3 and r["duped"] == 1
    store = S.rows("t1")
    assert store["total"] == 3
    p1 = next(x for x in store["rows"] if x["name"] == "Medplus Pharmacy")
    assert p1["key_type"] == "place_id" and p1["key_value"] == "PID1"
    assert p1["lat"] == 18.5204 and p1["phone"] == ""                    # PRO list: facts only, no expensive fields
    for x in store["rows"]:
        assert x["source_lane"] == "OFFICIAL_API" and "maps.google.com" in x["source_url"]
        assert x["parser_version"].startswith("v0.689")
    assert r["bill"]["sku_nearby"] == mapsbill.SKU_NEARBY_PRO and r["bill"]["nearby_calls"] == 5
    assert r["bill"]["attribution"] == "Google"
    assert r["bill"]["inr"] == 0.0                                       # inside the month's free allowance


def test_places_details_bought_per_place_under_the_budget(env, monkeypatch):
    fake_maps(monkeypatch, env, [[_pl("PID1", "Medplus Pharmacy"), _pl("PID2", "Apollo Pharmacy")]], [])
    monkeypatch.setattr(env["settings"], "leads_places_details_per_run", 1)
    out = asyncio.run(S.run_places("t1", "pharmacies", ["pharmacy"], "Pune", sweep_km=1, cell_km=2, details=True))
    assert out["details"] == {"requested": True, "bought": 1, "max": 1, "stopped_by_cap": False}
    store = {x["key_value"]: x for x in S.rows("t1")["rows"]}
    assert store["PID1"]["phone"] == "919876511111" and store["PID1"]["website"] == "https://medplus.in"
    assert store["PID1"]["rating"] == 4.5 and store["PID1"]["review_count"] == 120
    assert store["PID2"]["phone"] == ""                                  # the budget bought ONE place, not both


def test_places_mapscap_mid_list_aborts_with_the_cap_named(env, monkeypatch):
    # the REAL mapsbill charge path, with the month's free allowance gone and a Rs 0.5 day cap: the first
    # nearby call is REFUSED BEFORE it goes out - the run ABORTS, nothing is silently truncated
    fake_maps(monkeypatch, env, [[_pl("PID1", "Medplus Pharmacy")]], [])
    monkeypatch.setattr(mapsbill, "FREE_CAP", lambda: {})
    monkeypatch.setattr(env["settings"], "maps_daily_inr", 0.5)
    out = asyncio.run(S.run_places("t1", "pharmacies", ["pharmacy"], "Pune", sweep_km=1, cell_km=2))
    assert out["ok"] is False and out["run"]["status"] == "ABORTED"
    assert "cap" in out["run"]["error"].lower()
    assert S.rows("t1")["total"] == 0


def test_places_mapscap_mid_details_only_stops_the_buying(env, monkeypatch):
    # the list rides the free allowance; the DETAILS purchases hit the cap - the run still finishes DONE with
    # every list row kept, and the card says the buying stopped (never a pretend-complete details pass)
    fake_maps(monkeypatch, env, [[_pl("PID1", "Medplus Pharmacy"), _pl("PID2", "Apollo Pharmacy")]], [])
    monkeypatch.setattr(mapsbill, "FREE_CAP",
                        lambda: {mapsbill.SKU_NEARBY_PRO: mapsbill.UNLIMITED})
    monkeypatch.setattr(env["settings"], "maps_daily_inr", 0.5)
    monkeypatch.setattr(env["settings"], "leads_places_details_per_run", 5)
    out = asyncio.run(S.run_places("t1", "pharmacies", ["pharmacy"], "Pune", sweep_km=1, cell_km=2, details=True))
    assert out["ok"] is True and out["run"]["status"] == "DONE"
    assert out["details"]["bought"] == 0 and out["details"]["stopped_by_cap"] is True
    assert S.rows("t1")["total"] == 2                                    # the cheap list survived the cap


def test_places_unresolvable_area_leaves_no_run(env, monkeypatch):
    fake_maps(monkeypatch, env, [], [], resolve=None)
    with pytest.raises(S.LeadsError, match="nahi mila"):
        asyncio.run(S.run_places("t1", "ask", ["pharmacy"], "Nowhereville"))
    assert S.runs("t1") == []                                            # nothing ran, nothing is on the books


def test_places_needs_kinds_and_a_key(env):
    with pytest.raises(S.LeadsError, match="Kis tarah"):
        asyncio.run(S.run_places("t1", "ask", [], "Pune"))
    with pytest.raises(S.LeadsError, match="Kahan"):
        asyncio.run(S.run_places("t1", "ask", ["pharmacy"], ""))


def test_apply_details_updates_only_the_facts(env):
    row = S.add_row("t1", {"name": "Medplus", "place_id": "PID9", "city": "Pune"}, "OFFICIAL_API",
                    "https://maps.google.com/?cid=PID9")
    assert S.apply_details("t1", "PID9", {"phone": "+91 98765 22222", "website": "https://medplus.in",
                                          "rating": 4.1, "reviews": 55}) is True
    got = S.rows("t1")["rows"][0]
    assert got["phone"] == "919876522222" and got["website"] == "https://medplus.in"
    assert got["rating"] == 4.1 and got["review_count"] == 55
    assert got["source_lane"] == "OFFICIAL_API" and got["source_url"] == "https://maps.google.com/?cid=PID9"
    assert S.apply_details("t1", "NOPE", {"phone": "123"}) is False


def test_places_re_run_is_a_no_op(env, monkeypatch):
    fake_maps(monkeypatch, env, [[_pl("PID1", "Medplus Pharmacy")]], [])
    asyncio.run(S.run_places("t1", "ask", ["pharmacy"], "Pune", sweep_km=1, cell_km=2))
    fake_maps(monkeypatch, env, [[_pl("PID1", "Medplus Pharmacy")]], [])   # the world answers the same again
    again = asyncio.run(S.run_places("t1", "ask again", ["pharmacy"], "Pune", sweep_km=1, cell_km=2))
    assert again["run"]["kept"] == 0 and again["run"]["duped"] == 1
    assert S.rows("t1")["total"] == 1


# ================================================================ the enrich tool + the API surface
def test_leads_enrich_is_real_in_p2():
    # v0.543.0: the P2 skeleton became the real pass - the tool no longer refuses, it enriches (its tests live
    # in test_v0542_leads_enrich.py); here we only prove the handler is wired to the service, not to a stub.
    from app.agent.leads_tools import LEADS_HANDLERS
    from app.leads import service as Svc

    assert LEADS_HANDLERS["leads_enrich"].__module__ == "app.agent.leads_tools"
    assert hasattr(Svc, "enrich") and hasattr(Svc, "apply_enrich")
    from app.leads import enrich as _en
    assert hasattr(_en, "site_pass") and hasattr(_en, "grade_email") and hasattr(_en, "best_email")


def test_official_lanes_through_the_api(env, monkeypatch):
    fake_indiamart(monkeypatch, {"Pune": [_im("p1", "Balaji Traders", "Pune", phone="98765000001")]}, [])
    fake_maps(monkeypatch, env, [[_pl("PID1", "Medplus Pharmacy")]], [])
    with client(monkeypatch, env, api_key="secret") as c:
        h = {"Authorization": "Bearer secret"}
        ov = c.get("/api/leads", headers=h).json()
        assert ov["lanes_built"]["REGISTRY"] == "P1" and ov["lanes_built"]["OFFICIAL_API"] == "P1"
        r1 = c.post("/api/leads/runs/indiamart", headers=h,
                    json={"ask": "cement sellers", "search_term": "cement", "city": "Pune", "place": "Pune"})
        assert r1.status_code == 200 and r1.json()["run"]["kept"] == 1
        r2 = c.post("/api/leads/runs/places", headers=h,
                    json={"ask": "pharmacies", "kinds": ["pharmacy"], "near": "Pune", "sweep_km": 1})
        assert r2.status_code == 200 and r2.json()["run"]["kept"] == 1
        assert c.get("/api/leads/rows", headers=h, params={"lane": "OFFICIAL_API"}).json()["total"] == 1
        bad = c.post("/api/leads/runs/places", headers=h, json={"ask": "x", "kinds": [], "near": "Pune"})
        assert bad.status_code == 400                                     # a refusal is a 400 with the reason, not a 500
        scrap = c.post("/api/leads/runs/her-data", headers=h, json={"ask": "x", "rows": [], "lane": "SCRAPE"})
        assert scrap.status_code == 400                                   # the P3 lane is still refused, not stubbed
