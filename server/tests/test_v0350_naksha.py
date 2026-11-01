"""v0.350 NAKSHA (App Sahayak Phase 14): staff see every open row that carries a location, nearest first, each opening in
Maps, and the whole route in one tap - Android through Google's official Maps URLs, iPhone on an Apple MapKit map - with no
map key and no map tiles in the app; the location question only on a tap."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app/appmaker"
BE = {"collections": [{"key": "orders", "label": "Orders", "rules": {"create": "member"},
                       "fields": [{"key": "name", "label": "Name", "type": "text"}, {"key": "pin", "label": "Location", "type": "location"}]}],
      "order": "orders"}


def test_android_kit_stops():
    pro = (ROOT / "android/template/app/src/main/java/hoola/kit/Pro.kt").read_text()
    assert "fun StopsBlock()" in pro and "if (!Auth.isStaff) return" in pro
    assert "https://www.google.com/maps/dir/?api=1" in pro and "&waypoints=" in pro and "take(10)" in pro
    assert "Places.allowed(c)" in pro                         # never asks for location by itself
    assert "maps.googleapis.com" not in pro and "API_KEY" not in pro.upper().replace("API=1", "")
    assert "StopsBlock()" in (ROOT / "android/template/app/src/main/java/hoola/kit/Accounts.kt").read_text()


def test_iphone_kit_stops():
    pro = (ROOT / "ios/template/Sources/Kit/Pro.swift").read_text()
    assert "struct StopsBlock: View" in pro and "Map(coordinateRegion:" in pro and "MKMapItem.openMaps" in pro
    assert "authorizationStatus" in pro and "Nearest first (use my location)" in pro   # the location question only on her tap
    assert "StopsBlock()" in (ROOT / "ios/template/Sources/Kit/Accounts.swift").read_text()


def test_code_screens_and_guides():
    from app.appmaker.android import gen as AG
    from app.appmaker.android import prompts as AP
    from app.appmaker.ios import gen as IG
    from app.appmaker.ios import prompts as IP
    assert "StopsBlock()" in AG.fallback_screen({"id": "deliveries", "label": "Deliveries"}, ["deliveries"], [], BE)
    assert "StopsBlock()" not in AG.fallback_screen({"id": "home", "label": "Home"}, ["home"], [], BE)
    no_loc = {"collections": [{"key": "orders", "label": "Orders", "fields": [{"key": "name", "label": "Name", "type": "text"}]}]}
    assert "StopsBlock()" not in AG.fallback_screen({"id": "deliveries", "label": "Deliveries"}, ["deliveries"], [], no_loc)
    assert "StopsBlock()" in IG.code_screen({"id": "route", "label": "Route"}, ["route"], [], BE)
    assert "@Composable StopsBlock()" in AP.kit_sheet() and "StopsBlock" in IP.KIT_SHEET
