"""v0.468 Phase 9 APNA NAKSHA - her own pins / areas kept on Hoola's server.

Pinned: KML lon,lat order (the classic mistake), KMZ unzip, refusal of DOCTYPE and zip bombs, the Takeout sniffer says what
it found and never invents a location, nothing is geocoded behind her back, tenant isolation, GeoJSON for the Data layer,
straight-line near(), delete needs a yes, owner only, and the HTTP routes are actually called."""
from __future__ import annotations

import asyncio
import io
import json
import zipfile

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import ownmap as O

KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Customers</name>
 <Folder><name>Akola</name>
  <Placemark><name>Sai Medical</name><description><![CDATA[<b>Open</b> 9-9]]></description>
   <ExtendedData><Data name="owner"><value>Ramesh</value></Data></ExtendedData>
   <Point><coordinates>77.0082,20.7002,0</coordinates></Point></Placemark>
  <Placemark><name>Route A</name><LineString><coordinates>77.0,20.7,0 77.1,20.8,0</coordinates></LineString></Placemark>
 </Folder>
 <Folder><name>Zones</name>
  <Placemark><name>Zone 1</name><Polygon><outerBoundaryIs><LinearRing><coordinates>
    77.0,20.0,0 77.1,20.0,0 77.1,20.1,0 77.0,20.1,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
 </Folder>
 <Placemark><name>No place</name></Placemark>
</Document></kml>"""


def test_kml_reads_longitude_first_and_keeps_layers_notes_and_data():
    p = O.parse_kml(KML)
    pt = [f for f in p["features"] if f["kind"] == "point"][0]
    assert (pt["lat"], pt["lng"]) == (20.7002, 77.0082), "KML is lon,lat - swapping them puts Akola in Antarctica"
    assert pt["layer"] == "Akola" and pt["note"] == "Open 9-9" and pt["props"] == {"owner": "Ramesh"}
    kinds = sorted(f["kind"] for f in p["features"])
    assert kinds == ["line", "point", "polygon"] and p["skipped"] == 1
    poly = [f for f in p["features"] if f["kind"] == "polygon"][0]
    ring = json.loads(poly["geometry"])["coordinates"][0]
    assert ring[0] == ring[-1] and ring[0] == [77.0, 20.0], "polygon ring is closed, GeoJSON lon,lat"


def test_kmz_is_unzipped():
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("doc.kml", KML)
        z.writestr("files/icon.png", b"x")
    assert len(O.parse_kml(b.getvalue(), "m.kmz")["features"]) == 3


def test_hostile_files_are_refused():
    with pytest.raises(O.OwnMapError):
        O.parse_kml(b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY a "aaaa">]><kml><Document/></kml>')
    with pytest.raises(O.OwnMapError):
        O.parse_kml(b"x" * (O.MAX_FILE + 1))
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", b"<kml>" + b" " * (O.MAX_UNZIPPED + 10) + b"</kml>")
    assert len(b.getvalue()) < O.MAX_FILE, "a zip bomb: small on disk, huge opened"
    with pytest.raises(O.OwnMapError):
        O.parse_kml(b.getvalue(), "bomb.kmz")
    with pytest.raises(O.OwnMapError):
        O.parse_kml(b"<kml><unclosed>")


def test_takeout_geojson_is_sniffed_and_a_row_without_coordinates_is_kept_unlocated():
    j = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [77.0, 20.7]},
         "properties": {"Title": "Akola Station", "Google Maps URL": "https://maps.google.com/?cid=1", "Comment": "meet here"}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]},
         "properties": {"Title": "Mystery", "Google Maps URL": "https://maps.google.com/?cid=2",
                        "Location": {"Address": "Tilak Rd"}}}]}
    p = O.parse_takeout(json.dumps(j).encode())
    a, b = p["features"]
    assert a["kind"] == "point" and (a["lat"], a["lng"]) == (20.7, 77.0) and a["note"] == "meet here"
    assert b["kind"] == "unlocated" and b["lat"] is None and b["url"].endswith("cid=2"), "never invented"
    assert "GeoJSON" in p["detected"] and "1 bina jagah" in p["detected"]


def test_takeout_csv_is_sniffed_and_reports_its_columns():
    p = O.parse_takeout(b"Title,Note,URL,Comment\nChai Point,good,https://maps.google.com/?cid=9,\nOffice,,,\n")
    assert [f["kind"] for f in p["features"]] == ["unlocated"] * 2 or len(p["features"]) == 1
    assert "CSV" in p["detected"] and "Title" in p["detected"]
    p2 = O.parse_takeout(b"name,latitude,longitude\nShop,20.7,77.0\n")
    assert p2["features"][0]["kind"] == "point"


def test_an_unknown_json_shape_is_refused_not_guessed():
    with pytest.raises(O.OwnMapError):
        O.parse_takeout(b'{"hello": "world"}')


def test_import_stores_it_and_reports_plainly(env):
    r = O.import_file("default", KML, "mine.kml", "Customers")
    assert r["count"] == 3 and r["kinds"] == {"point": 1, "line": 1, "polygon": 1} and r["layers"] == ["Akola", "Zones"]
    assert r["skipped"] == 1 and "KML" in r["detected"]
    assert O.maps("default")[0]["count"] == 3


def test_tenants_cannot_see_each_others_maps(env):
    r = O.import_file("default", KML, "mine.kml")
    assert O.maps("someone-else") == []
    with pytest.raises(O.OwnMapError):
        O.geojson("someone-else", r["map"])
    with pytest.raises(O.OwnMapError):
        O.delete_map("someone-else", r["map"])
    assert O.near("someone-else", 20.7, 77.0, 100) == []


def test_geojson_for_the_data_layer_leaves_out_unlocated_rows(env):
    j = {"features": [{"geometry": {"type": "Point", "coordinates": [77.0, 20.7]}, "properties": {"Title": "A"}},
                      {"geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {"Title": "B", "Google Maps URL": "u"}}]}
    r = O.import_file("default", json.dumps(j).encode(), "Saved Places.json", "Saved")
    g = O.geojson("default", r["map"])
    assert g["type"] == "FeatureCollection" and len(g["features"]) == 1
    assert g["features"][0]["geometry"] == {"type": "Point", "coordinates": [77.0, 20.7]}


def test_near_is_straight_line_sorted_and_bounded(env):
    r = O.import_file("default", KML, "mine.kml")
    O.add_pin("default", r["map"], "Far", 21.5, 78.0)
    rows = O.near("default", 20.7, 77.0, 5)
    assert [x["name"] for x in rows][0] == "Sai Medical" and all(x["distance_km"] <= 5 for x in rows)
    assert "Far" not in [x["name"] for x in rows]
    assert O.near("default", 20.7, 77.0, 500)[-1]["name"] == "Far"


def test_bad_pin_and_limits(env):
    r = O.import_file("default", KML, "mine.kml")
    with pytest.raises(O.OwnMapError):
        O.add_pin("default", r["map"], "x", 95, 77)
    with pytest.raises(O.OwnMapError):
        O.import_file("default", b"<kml xmlns='http://www.opengis.net/kml/2.2'><Document/></kml>", "e.kml")


def test_nothing_in_the_module_calls_google():
    import inspect
    src = inspect.getsource(O)
    assert "httpx" not in src and "googleapis" not in src, "her own data is never looked up behind her back"


def _ctx(actor="owner"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id="c", actor=actor)


def test_tools_import_near_pin_and_delete_need_a_yes(env, monkeypatch):
    from app.agent import maps_tools
    from app.agent.tools import ToolError
    from app.mailbox import service as ms
    monkeypatch.setattr(ms, "load_files", lambda t, f: [("mine.kml", "application/vnd.google-earth.kml+xml", KML)])
    r = asyncio.run(maps_tools.ownmap_import(_ctx(), "file_1", "Customers"))
    assert r["count"] == 3 and "re-import" in r["note"]
    near = asyncio.run(maps_tools.ownmap_near(_ctx(), lat=20.7, lng=77.0, radius_km=2))
    assert near["places"][0]["name"] == "Sai Medical"
    asyncio.run(maps_tools.ownmap_pin(_ctx(), r["map"], "New", lat=20.71, lng=77.01))
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.ownmap_delete(_ctx(), r["map"]))
    assert O.maps("default"), "not deleted without a yes"
    asyncio.run(maps_tools.ownmap_delete(_ctx(), r["map"], confirm=True))
    assert O.maps("default") == []
    for fn in (maps_tools.ownmap_list, maps_tools.ownmap_import):
        with pytest.raises(ToolError):
            asyncio.run(fn(_ctx("staff:1"), **({"file_id": "x"} if fn is maps_tools.ownmap_import else {})))


def test_the_http_routes_are_really_called(env):
    from app.ownmap_api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    r = c.post("/api/ownmap/import", files={"file": ("mine.kml", KML)}, data={"name": "Customers"})
    assert r.status_code == 200 and r.json()["count"] == 3
    mid = r.json()["map"]
    assert c.get("/api/ownmap").json()["maps"][0]["name"] == "Customers"
    assert len(c.get(f"/api/ownmap/{mid}/geojson").json()["features"]) == 3
    assert c.post("/api/ownmap/import", files={"file": ("x.json", b'{"hello":1}')}).status_code == 400
    assert c.delete(f"/api/ownmap/{mid}").status_code == 200
    assert c.get(f"/api/ownmap/{mid}/geojson").status_code == 400


def test_tools_and_router_are_registered(env):
    from app.agent.tools import TOOLS, HANDLERS
    for n in ("ownmap_import", "ownmap_list", "ownmap_near", "ownmap_pin", "ownmap_delete"):
        assert n in {t["name"] for t in TOOLS} and n in HANDLERS
    from app.main import app as real
    # mounted on the real app: 404 would mean make_router was never included (the test env has no API key, so 200 is right;
    # the router carries the same require_key dependency as every other module)
    code = TestClient(real).get("/api/ownmap").status_code
    assert code != 404, "/api/ownmap is not mounted on the app"
