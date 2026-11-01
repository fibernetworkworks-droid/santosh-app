"""v0.340 HAR FEATURE 2 (App Sahayak Phase 8): the barcode / QR scan field (server check, complex lists map codes to it,
her data change can add one), the staff dashboard numbers (/stats: staff only, counts, status mix, 14 days, money), the
updates inbox and background updates on both platforms (generated Kotlin / Swift + Info.plist), and the model's guides.
The Kotlin compiles in CI appgen-check (emulator: 14 screens incl. hoola_inbox); the Swift in ios-check (macOS)."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0319_app_features import _member
from tests.test_v128_appdesign import T
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

FIX = Path(__file__).resolve().parents[1] / "app/appmaker/android/fixture/spec.json"


def test_scan_field_and_dashboard_numbers(droid_env):
    from app.appmaker import backend as BE
    from app.main import app
    c = TestClient(app)
    aid, conv, key, _be = _built(droid_env)
    api = f"/api/app-api/{key}"
    # her data change adds a scan field (additive, optional) - e.g. a gift-card code
    out = c.post(f"/api/apps/{aid}/data_change", json={"ops": {"add": [{"coll": "orders", "key": "coupon", "label": "Coupon code", "type": "scan"}]}})
    assert out.status_code == 200, out.text
    sch = BE.schema(BE.by_key_or_ref(T, aid))
    f = next(x for x in sch["collections"][0]["fields"] if x["key"] == "coupon")
    assert f["type"] == "scan" and f["required"] is False
    ha, hb = _member(c, api, "asha@example.com"), _member(c, api, "ravi@example.com")
    pid = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]["id"]
    base = {"name": "Asha", "phone": "9876543210", "cart": [{"id": pid, "qty": 2}]}
    row = c.post(f"{api}/c/orders", json={**base, "coupon": " HOOLA\x07-42\n "}, headers=ha).json()
    assert row["coupon"] == "HOOLA-42"                                   # control characters gone, trimmed
    assert c.post(f"{api}/c/orders", json={**base, "coupon": "\x01\x02"}, headers=ha).status_code == 400
    c.post(f"{api}/c/orders", json=base, headers=ha)
    # the dashboard: customers never see the business's numbers
    assert c.get(f"{api}/stats").status_code == 401
    assert c.get(f"{api}/stats", headers=ha).status_code == 403
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    hb = {"Authorization": "Bearer " + c.post(f"{api}/login", json={"email": "ravi@example.com", "password": "pass-word-1"}).json()["token"]}
    st = c.get(f"{api}/stats", headers=hb).json()
    assert len(st["days"]) == 14 and st["days"][-1] > st["days"][0]
    orders = next(x for x in st["lists"] if x["key"] == "orders")
    assert orders["count"] == 2 and orders["daily"][-1] == 2 and orders["status"] == {"New": 2}
    assert orders["total"] > 0 and orders["total"] == 2 * row["total"]   # server-priced totals, summed
    assert len(c.get(f"{api}/stats", params={"days": 400}, headers=hb).json()["days"]) == 60


def test_complex_lists_scan_their_codes():
    from app.appmaker import backend as BE
    plan = {"blueprint": {"complex": True, "modules": ["sales", "inventory"]}}
    lists = BE._complex_lists(plan, "inventory")
    types = {(c["key"], f["key"]): f["type"] for c in lists for f in c["fields"]}
    item_codes = {k: v for (c, k), v in types.items() if c == "item" and k in ("sku", "barcode", "name")}
    assert item_codes.get("barcode") == "scan" or item_codes.get("sku") == "scan"
    assert item_codes.get("name") == "text"
    per_list = {}
    for (c, k), v in types.items():
        per_list[c] = per_list.get(c, 0) + (v == "scan")
    assert max(per_list.values()) <= 2                                  # at most two scan boxes a list


def _spec_with_scan():
    sp = json.loads(FIX.read_text())
    sp["seed"]["backend"]["collections"][0]["fields"].append({"key": "coupon", "label": "Coupon", "type": "scan", "required": False})
    return sp


def test_android_project_has_scan_dashboard_inbox(tmp_path):
    from app.appmaker.android import gen as G
    from app.appmaker.android import prompts as PR
    sp = _spec_with_scan()
    out = tmp_path / "a"
    G.write_project(sp, out)
    scr = out / "app/src/main/java/hoola/app/screens"
    be = sp["seed"]["backend"]
    assert 'ScanField("Coupon", "coupon")' in G.fallback_screen({"id": "cart", "label": "Cart"}, ["cart"], [], be)
    assert "StatsBlock()" in G.fallback_screen({"id": "dashboard", "label": "Dashboard"}, ["dashboard"], [], be)
    assert scr.exists()
    reg = (out / "app/src/main/java/hoola/app/AppScreens.kt").read_text()
    assert '"hoola_inbox" -> InboxScreen()' in reg and '"hoola_inbox"' in reg.split("val ids")[1].split("\n")[0]
    main = (out / "app/src/main/java/hoola/app/MainActivity.kt").read_text()
    assert "Inbox.unread.value = Inbox.count(this)" in main
    assert (out / "hoola_qa/screens.txt").read_text().split()[-1] == "hoola_inbox"
    kit = out / "app/src/main/java/hoola/kit"
    assert "Inbox.add(" in (kit / "Updates.kt").read_text() and "StatsBlock()" in (kit / "Accounts.kt").read_text()
    pro = (kit / "Pro.kt").read_text()
    assert "GmsBarcodeScanning" in pro and "Manifest.permission.CAMERA" not in pro
    assert "CAMERA" not in (out / "app/src/main/AndroidManifest.xml").read_text()      # Google's scanner: no camera permission
    gradle = (out / "gradle/libs.versions.toml").read_text()
    assert "play-services-code-scanner" in gradle and "libs.gms.code.scanner" in (out / "app/build.gradle.kts").read_text()
    sheet = PR.kit_sheet()
    assert "@Composable ScanField(label: String, key: String)" in sheet and "@Composable StatsBlock()" in sheet
    assert "[scan]" in PR.backend_line({"collections": sp["seed"]["backend"]["collections"]})
    assert G.scan_screen('package hoola.app.screens\nimport hoola.kit.*\nimport androidx.compose.runtime.Composable\n'
                         '@Composable\nfun ScreenHome() { Page("x") { block { StatsBlock() } } }\n', "home", ["home"]) == []


def test_iphone_project_has_scan_dashboard_inbox_background(tmp_path):
    from app.appmaker.ios import gen as G
    from app.appmaker.ios import prompts as PR
    out = tmp_path / "i"
    G.write_project(_spec_with_scan(), out)
    assert "StatsBlock()" in (out / "Sources/Screens/ScreenDashboard.swift").read_text()
    assert 'case "hoola_inbox": return AnyView(InboxScreen())' in (out / "Sources/App/AppScreens.swift").read_text()
    assert '"hoola_inbox"' in (out / "Sources/App/AppTokens.swift").read_text()
    app = (out / "Sources/App/HoolaApp.swift").read_text()
    assert "Updates.register()" in app and "await Updates.check()" in app and "Updates.schedule()" in app
    plist = (out / "Info.plist").read_text()
    assert "<string>$(PRODUCT_BUNDLE_IDENTIFIER).updates</string>" in plist and "<string>fetch</string>" in plist
    assert "NSCameraUsageDescription" in plist                         # only because a list has a scan field
    plain = tmp_path / "p"
    G.write_project(json.loads(FIX.read_text()), plain)
    assert "NSCameraUsageDescription" not in (plain / "Info.plist").read_text()
    kit = (out / "Sources/Kit/Pro.swift").read_text()
    for s in ("DataScannerViewController", "BGAppRefreshTaskRequest", "UNUserNotificationCenter", "BarMark", "hoola_upd_since"):
        assert s in kit, s
    acc = (out / "Sources/Kit/Accounts.swift").read_text()
    assert 'case "scan":' in acc and "InboxButton()" in acc and "StatsBlock()" in acc
    assert (out / "hoola_qa/screens.txt").read_text().split()[-1] == "hoola_inbox"
    assert "ScanRow" in PR.KIT_SHEET and "StatsBlock" in PR.KIT_SHEET
