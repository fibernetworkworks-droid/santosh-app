"""v0.332 IPHONE (App Phase 6): the iPhone app from the SAME approved design and the SAME backend as Android - the SwiftUI
kit + Xcode project generator (pure stdlib, runs on the Mac), the house rules for model-written SwiftUI screens, Xcode
error parsing, the build service (Opus screens -> Mac compile rounds -> simulator crash fix -> TestFlight upload with HER key
kept in her builds repo) on a faked Mac, routes and the agent tool. The real compile + simulator run is CI (ios-check.yml)."""
import json
import re
import struct
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _shop_app
from tests.test_v128_appdesign import T
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

FIX = Path(__file__).resolve().parents[1] / "app/appmaker/android/fixture/spec.json"


def _spec():
    return json.loads(FIX.read_text())


# ---------------------------------------------------------------- generator
def test_project_from_the_android_spec(tmp_path):
    from app.appmaker.ios import gen as G
    out = tmp_path / "ios"
    res = G.write_project(_spec(), out)
    assert res["bundle_id"] == "in.hoola.preview.fixture"
    assert set(res["screens"].values()) == {"code"}
    for f in ("project.yml", "Info.plist", "Resources/seed.json", "Resources/PrivacyInfo.xcprivacy", "Sources/Kit/Backend.swift",
              "Sources/Kit/Accounts.swift", "Sources/App/AppTokens.swift", "Sources/App/AppScreens.swift",
              "Sources/App/HoolaApp.swift", "Sources/Screens/ScreenCart.swift", "hoola_qa/sim_check.sh"):
        assert (out / f).exists(), f
    tok = (out / "Sources/App/AppTokens.swift").read_text()
    for sid in ("home", "cart", "orders", "seller_info", "privacy", "delete_account", "hoola_login", "hoola_account"):
        assert f'"{sid}"' in tok
    assert 'TabSpec(id: "cart", label: "Cart", symbol: "cart")' in tok and 'static let appKey = "akf1c7a2e0000000000000001"' in tok
    reg = (out / "Sources/App/AppScreens.swift").read_text()
    assert 'case "hoola_account": return AnyView(AccountScreen())' in reg and 'case "cart": return AnyView(ScreenCart())' in reg
    # the fixture keeps orders on its server: the cart places a real order, the orders list shows the user's real rows
    assert 'FormBlock(coll: "orders")' in (out / "Sources/Screens/ScreenCart.swift").read_text()
    assert 'RowsSection(coll: "orders")' in (out / "Sources/Screens/ScreenOrders.swift").read_text()
    assert 'ListBlock(list: "products"' in (out / "Sources/Screens/ScreenProduct.swift").read_text()
    assert "AccountButton()" in (out / "Sources/Screens/ScreenProfile.swift").read_text()
    plist = (out / "Info.plist").read_text()
    assert "NSLocationWhenInUseUsageDescription" in plist          # the order form has a location field
    assert "<string>upi</string>" in plist and "ITSAppUsesNonExemptEncryption" in plist
    yml = (out / "project.yml").read_text()
    assert 'iOS: "16.0"' in yml and "PRODUCT_BUNDLE_IDENTIFIER: in.hoola.preview.fixture" in yml and "scheme: {}" in yml
    png = (out / "Resources/Assets.xcassets/AppIcon.appiconset/icon.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", png[16:24]) == (1024, 1024)
    assert png[25] == 2                                               # RGB, no alpha (App Store refuses transparent icons)
    assert (out / "hoola_qa/screens.txt").read_text().split()[-2:] == ["hoola_login", "hoola_account"]
    # debug-only test hooks; a release build has neither
    app = (out / "Sources/App/HoolaApp.swift").read_text()
    assert app.count("#if DEBUG") == 2 and "-hoola_screen" in app and "-hoola_base" in app


def test_bundle_id_rules():
    from app.appmaker.ios import gen as G
    sp = _spec()
    sp["ios"] = {"bundle_id": "com.sharma_kirana.app"}
    assert G.bundle_id(sp) == "com.sharma-kirana.app"
    sp["ios"] = {"bundle_id": "bad id"}
    try:
        G.bundle_id(sp)
        raise AssertionError("bad id accepted")
    except ValueError:
        pass


def test_swift_string_escaping():
    from app.appmaker.ios import gen as G
    assert G.sstr('a "b" \\ c\nd') == '"a \\"b\\" \\\\ c\\nd"'
    sp = _spec()
    sp["screens"][0]["label"] = 'Ghar "Home" \\'
    assert 'label: "Ghar \\"Home\\" \\\\"' in G.tokens_swift(sp)


GOOD = """import SwiftUI

struct ScreenHome: View {
    @Environment(\\.colorScheme) private var scheme
    @ObservedObject private var data = AppData.shared
    var body: some View {
        let c = H.c(scheme)
        Page("Home") {
            Text(data.appName).font(.largeTitle.weight(.bold)).foregroundStyle(c.ink)
            ListBlock(list: "products", next: "product")
            MainButton(text: "Open cart") { Router.shared.go("cart") }
        }
    }
}
"""


def test_house_rules_for_model_screens():
    from app.appmaker.ios import gen as G
    ids = ["home", "cart", "product"]
    assert G.scan_screen(GOOD, "home", ids) == []
    bad = {
        "SecureField": GOOD.replace('ListBlock(list: "products", next: "product")', 'SecureField("PIN", text: .constant(""))'),
        "network": GOOD.replace("Page(", "let _ = URLSession.shared\n        Page("),
        "UIApplication": GOOD.replace("Page(", "let _ = UIApplication.shared\n        Page("),
        "no such screen": GOOD.replace('go("cart")', 'go("checkout")'),
        "import": "import UIKit\n" + GOOD,
        "storage": GOOD.replace("@ObservedObject private var data", "@AppStorage(\"x\") var x = \"\"\n    @ObservedObject private var data"),
        "must define": GOOD.replace("ScreenHome", "HomeView"),
        "logging": GOOD.replace("Page(", "print(1)\n        Page("),
    }
    for want, src in bad.items():
        probs = G.scan_screen(src, "home", ids)
        assert any(want in p for p in probs), (want, probs)
    assert G.scan_screen(GOOD.replace('go("cart")', 'go("hoola_account")'), "home", ids) == []


def test_model_screen_used_only_when_clean(tmp_path):
    from app.appmaker.ios import gen as G
    sp = _spec()
    sp["screens_swift"] = {"home": GOOD, "cart": GOOD.replace("ScreenHome", "ScreenCart").replace('"cart"', '"nowhere"')}
    res = G.write_project(sp, tmp_path / "p")
    assert res["screens"]["home"] == "model" and res["screens"]["cart"] == "code"
    assert (tmp_path / "p/Sources/Screens/ScreenHome.swift").read_text() == GOOD


def test_xcode_errors_per_screen():
    from app.appmaker.ios import gen as G
    log = ("/Users/runner/work/ios/Sources/Screens/ScreenCart.swift:12:9: error: cannot find 'Foo' in scope\n"
           "/Users/runner/work/ios/Sources/Screens/ScreenCart.swift:20:1: error: extraneous '}' at top level\n"
           "/Users/runner/work/ios/Sources/Kit/Kit.swift:3:1: warning: something\n"
           "/Users/runner/work/ios/Sources/Screens/ScreenHome.swift:5:5: error: the compiler is unable to type-check this expression\n")
    e = G.screen_errors(log)
    assert set(e) == {"ScreenCart", "ScreenHome"} and e["ScreenCart"][0] == "line 12: cannot find 'Foo' in scope"


def test_ci_and_builds_repo_workflows():
    root = Path(__file__).resolve().parents[2]
    ci = (root / ".github/workflows/ios-check.yml").read_text()
    assert "macos-15" in ci and "server/app/appmaker/ios/**" in ci and "CODE_SIGNING_ALLOWED=NO" in ci and "sim_check.sh" in ci
    wf = (root / "server/app_builder/hoola-ios.yml").read_text()
    for s in ("ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_KEY_P8", "APPLE_TEAM_ID", "app-store-connect", "UPLOADED_TO_TESTFLIGHT",
              "hoola-${{ inputs.job }}", "qa/screens/*.png", 'rm -f "$KEY"'):
        assert s in wf, s
    assert "secrets." in wf and "ASC_KEY_P8: ${{ secrets.ASC_KEY_P8 }}" in wf


# ---------------------------------------------------------------- the build service on a faked Mac
class FakeSwift:
    """Opus stand-in: a clean SwiftUI screen; the cart's first draft does not compile (BROKEN_), its fix does."""
    def __init__(self):
        self.calls = 0
        self.fixes = []

    def __call__(self, system, prompt):
        self.calls += 1
        fn = re.search(r"struct (Screen\w+): View", system).group(1)
        if "COMPILE ERRORS" in prompt or "CRASHED" in prompt:
            self.fixes.append(fn)
        body = 'Muted("ok")'
        if fn == "ScreenCart" and "COMPILE ERRORS" not in prompt:
            body = "BROKEN_x"
        return f"import SwiftUI\n\nstruct {fn}: View {{\n    var body: some View {{\n        Page(\"x\") {{\n            {body}\n        }}\n    }}\n}}\n"


class FakeMac:
    def __init__(self, crash_once=""):
        self.calls, self.crash_once, self.uploads = [], crash_once, 0

    def __call__(self, src, key, kind):
        self.calls.append(kind)
        assert (src / "project.yml").exists() and (src / "Resources/seed.json").exists()
        errs = []
        for f in sorted((src / "Sources/Screens").glob("*.swift")):
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if "BROKEN_" in line:
                    errs.append(f"/Users/runner/w/ios/Sources/Screens/{f.name}:{i}:13: error: cannot find 'BROKEN_x' in scope")
        if errs:
            return {"ok": False, "log": "\n".join(errs) + "\n** BUILD FAILED **", "seconds": 60}
        if kind == "testflight":
            self.uploads += 1
            return {"ok": True, "log": "BUILD SUCCEEDED", "uploaded": True, "upload_log": "UPLOADED_TO_TESTFLIGHT", "seconds": 300}
        ids = (src / "hoola_qa/screens.txt").read_text().split()
        first = self.crash_once and not getattr(self, "_done", False)
        self._done = True
        screens = {}
        for sid in ids:
            c = bool(first and self.crash_once == sid)
            screens[sid] = {"crashed": c, "shot": True, "bytes": 90000, "excerpt": "EXC_BREAKPOINT Index out of range" if c else ""}
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 40
        cr = [k for k, v in screens.items() if v["crashed"]]
        return {"ok": True, "log": "** BUILD SUCCEEDED **", "seconds": 70, "shots": {k: png for k in ids},
                "report": {"opened": len(ids) - len(cr), "total": len(ids), "crashed": cr, "screens": screens,
                           "perf": {"launch_ms": 640, "app_mb": 3.2}, "passed": not cr}}


def _ios_env(droid_env, monkeypatch, mac):
    fake, _kt = droid_env
    from app.appmaker.ios import service as IO
    sw = FakeSwift()
    monkeypatch.setattr(IO, "_ask", sw)
    IO.set_runner(mac)
    aid, conv = _shop_app(fake)
    return aid, conv, sw, IO


def test_iphone_build_compile_rounds_and_qa(droid_env, monkeypatch):
    mac = FakeMac()
    aid, conv, sw, IO = _ios_env(droid_env, monkeypatch, mac)
    try:
        v = IO.build(T, aid, conv)
        assert v["status"] == "ready", v["error"]
        assert mac.calls == ["sim", "sim"]                    # round 0 failed on the cart, round 1 compiled
        assert sw.fixes == ["ScreenCart"]
        assert v["stats"]["code"] == 0 and v["stats"]["model"] >= 3
        assert v["qa"]["ran"] and v["qa"]["opened"] == v["qa"]["total"] and v["qa"]["perf"]["launch_ms"] == 640
        assert v["bundle_id"].startswith("in.hoola.app.") and v["zip"] and v["zip_url"]
        assert v["history"][0]["build_number"] >= 100 and not v["testflight"]
        c = TestClient(__import__("app.main", fromlist=["app"]).app)
        assert c.get(f"/api/apps/{aid}/ios").json()["status"] == "ready"
        assert c.get(f"/api/apps/{aid}/ios/qa/home").status_code == 200
        assert c.get(f"/api/apps/{aid}/ios/qa/..%2Fx").status_code == 404
        z = c.get("/api/" + v["zip_url"].split("/api/", 1)[1])
        assert z.status_code == 200 and z.content[:2] == b"PK"
        assert c.get("/api/app-ios-zip/" + "x" * 30 + "/ios-project-b1.zip").status_code == 404
        # an update rewrites only changed screens: the second build reuses every cached SwiftUI screen
        n = sw.calls
        v2 = IO.build(T, aid, conv)
        assert v2["status"] == "ready" and sw.calls == n and v2["history"][0]["build_number"] > v["history"][0]["build_number"]
    finally:
        IO.set_runner(None)


def test_iphone_crash_gets_one_fix(droid_env, monkeypatch):
    mac = FakeMac(crash_once="home")
    aid, conv, sw, IO = _ios_env(droid_env, monkeypatch, mac)
    try:
        v = IO.build(T, aid, conv)
        assert v["status"] == "ready", v["error"]
        assert "ScreenHome" in sw.fixes
    finally:
        IO.set_runner(None)


def test_testflight_upload_and_refusals(droid_env, monkeypatch):
    mac = FakeMac()
    aid, conv, _sw, IO = _ios_env(droid_env, monkeypatch, mac)
    try:
        c = TestClient(__import__("app.main", fromlist=["app"]).app)
        v = c.post(f"/api/apps/{aid}/ios", json={"kind": "testflight"}).json()
        assert v["status"] == "ready" and v["testflight"]["build"] >= 100 and mac.uploads == 1
        assert "TestFlight" in v["say"]
        assert c.post(f"/api/apps/{aid}/ios", json={"kind": "appstore"}).status_code == 400
    finally:
        IO.set_runner(None)
    # her missing secret / app record -> the exact step she takes, never a raw log
    assert "ASC_KEY_P8" in IO._upload_why("MISSING_SECRET ASC_KEY_P8")
    assert "New App" in IO._upload_why("error: No suitable application records were found")
    assert "agreement" in IO._upload_why("You must accept the latest Program License Agreement")


def test_no_mac_gives_the_xcode_zip(droid_env, monkeypatch):
    fake, _kt = droid_env
    from app.appmaker.ios import service as IO
    monkeypatch.setattr(IO, "_ask", FakeSwift())
    IO.set_runner(None)
    aid, conv = _shop_app(fake)
    v = IO.build(T, aid, conv)
    assert v["status"] == "zip" and v["zip"] and "Mac" in v["note"] and v["runner"]["ready"] is False


def test_not_before_design_approval(droid_env):
    fake, _kt = droid_env
    from app.appmaker import service as S
    from app.appmaker.ios import service as IO
    from tests.test_v128_appdesign import conv_ctx
    v = S.new(T, "Sharma Kirana ki app", conv_ctx().conversation_id, name="Sharma Kirana", goal="shop")
    try:
        IO.build(T, v["id"])
        raise AssertionError("built without approval")
    except IO.IosError as e:
        assert "pakka" in str(e)


def test_agent_tool_ios(droid_env, monkeypatch):
    mac = FakeMac()
    aid, conv, _sw, IO = _ios_env(droid_env, monkeypatch, mac)
    from app.agent.app_tools import APP_TOOLS, _act
    from app.agent.tools import Ctx
    try:
        tool = next(t for t in APP_TOOLS if t["name"] == "app_banao")
        assert "ios" in tool["input_schema"]["properties"]["action"]["enum"]
        assert "TestFlight" in tool["description"] and "never in chat" in tool["description"]
        out = _act(Ctx(tenant_id=T, conversation_id=conv), "ios", {"app": aid})
        assert out["status"] == "ready" and mac.calls[-1] == "sim"
    finally:
        IO.set_runner(None)
