"""v0.345 HAR RAASTA JAANCHO (App Sahayak Phase 11): every button / link on every screen is tapped on the device check
(Android: uiautomator + adb taps in device_check.sh; iPhone: a generated XCUITest) - a crash on a tap blocks the build like
a screen crash and goes to Opus with the real crash and the button's name; a tap that changes nothing is reported."""
import json
from pathlib import Path

FIX = Path(__file__).resolve().parents[1] / "app/appmaker/android/fixture/spec.json"

XML = """<hierarchy><node class="android.widget.FrameLayout" bounds="[0,0][1080,2400]" clickable="false">
<node class="android.view.View" text="" content-desc="Open cart" clickable="true" bounds="[40,1800][1040,1950]"/>
<node class="android.view.View" text="Atta 5 kg" clickable="true" bounds="[40,400][1040,600]"><node text="ADD" bounds="[900,450][1000,520]"/></node>
<node class="android.widget.EditText" text="Name" clickable="true" bounds="[40,700][1040,800]"/>
<node class="android.view.View" text="Atta 5 kg" clickable="true" bounds="[40,900][1040,1000]"/>
<node class="android.view.View" text="" clickable="true" bounds="[0,0][4,4]"/></node></hierarchy>"""


def test_android_tap_targets_and_signature():
    from app.appmaker.android import qa
    t = qa.targets(XML)
    assert [x[2] for x in t] == ["Atta 5 kg ADD", "Atta 5 kg", "Open cart"]          # top to bottom, no typing box, no 4px dot
    assert t[0][:2] == (540, 500)
    assert qa.sig(XML) == qa.sig(XML) and qa.sig(XML) != qa.sig(XML.replace("Open cart", "Cart (1)"))
    assert len(qa.targets(XML, limit=1)) == 1


def test_android_report_flows(tmp_path):
    from app.appmaker.android import qa
    out = tmp_path
    (out / "screens").mkdir()
    (out / "opened.txt").write_text("home 1\ncart 1\n")
    (out / "taps.txt").write_text("home\tOpen cart\t1\t1\t1\nhome\tHelp\t1\t0\t2\ncart\tPlace order\t0\t0\t1\n")
    (out / "screens/cart.tap1.crash.txt").write_text(
        "--------- beginning of crash\nE AndroidRuntime: FATAL EXCEPTION: main\nE AndroidRuntime: java.lang.IllegalStateException: boom\n"
        "E AndroidRuntime: \tat hoola.app.screens.ScreenCartKt.ScreenCart(ScreenCart.kt:42)\n")
    rep = qa.report(out)
    assert rep["flows"]["tapped"] == 3 and rep["flows"]["moved"] == 1
    assert rep["flows"]["dead"] == [{"screen": "home", "label": "Help"}]
    assert rep["flows"]["crashed"] == [{"screen": "cart", "label": "Place order"}]
    assert rep["passed"] is False and rep["screens"]["cart"]["opened"] is True               # opened fine, crashed on a tap
    assert "IllegalStateException" in rep["screens"]["cart"]["tap_crash"]["exception"]
    assert "buttons tapped (1 crashed, 1 did nothing)" in qa.summary(rep)


def test_tap_crash_goes_to_opus_with_the_button():
    from app.appmaker.android import service as AN
    from app.appmaker.ios import service as IO
    rep = {"screens": {"cart": {"opened": True, "tap_crash": {"label": "Place order", "exception": "IllegalStateException: boom",
                                                             "excerpt": "at hoola.app.screens.ScreenCartKt"}},
                       "home": {"opened": True, "taps": [{"label": "Open cart", "ok": True, "changed": True}]}}}
    a = AN._crashed_screens(rep, ["cart", "home"])
    assert list(a) == ["cart"] and "CRASHED WHEN THE USER TAPPED 'Place order'" in a["cart"]["excerpt"]
    i = IO._crashed({"screens": {"cart": {"crashed": False, "tap_crash": {"label": "Pay", "excerpt": "EXC_BREAKPOINT"}}}}, ["cart"])
    assert "TAPPED 'Pay'" in i["cart"] and "EXC_BREAKPOINT" in i["cart"]


def test_iphone_flow_merge(tmp_path):
    from app.appmaker.ios import flows
    (tmp_path / "report.json").write_text(json.dumps({"screens": {"home": {"crashed": False}, "cart": {"crashed": False}}, "passed": True}))
    (tmp_path / "flows-crash.txt").write_text("Exception Type: EXC_BREAKPOINT (SIGTRAP)")
    log = ("Test Case '-[AppUITests.FlowTests testEveryButtonOnEveryScreen]' started.\n"
           "HOOLA_TAP\thome\tOpen cart\t1\t1\t1\nHOOLA_TAP\thome\tHelp\t1\t0\t2\nHOOLA_TAP\tcart\tPlace order\t0\t1\t1\n"
           "HOOLA_TAP\tcart\t(open)\t0\t0\t0\n")
    rep = flows.merge(tmp_path, log)
    assert rep["flows"]["tapped"] == 3 and rep["flows"]["dead"] == [{"screen": "home", "label": "Help"}]
    assert rep["flows"]["crashed"] == [{"screen": "cart", "label": "Place order"}] and rep["passed"] is False
    assert "EXC_BREAKPOINT" in rep["screens"]["cart"]["tap_crash"]["excerpt"]
    assert json.loads((tmp_path / "report.json").read_text())["flows"]["ran"] is True


def test_projects_carry_the_flow_walk(tmp_path):
    from app.appmaker.android import gen as AG
    from app.appmaker.ios import gen as IG
    sp = json.loads(FIX.read_text())
    AG.write_project(sp, tmp_path / "a")
    dc = (tmp_path / "a/hoola_qa/device_check.sh").read_text()
    assert "qa.py\" taps" in dc and "input tap" in dc and "< /dev/null" in dc and "taps.txt" in dc
    IG.write_project(sp, tmp_path / "i")
    ft = (tmp_path / "i/UITests/FlowTests.swift").read_text()
    assert 'final class FlowTests: XCTestCase' in ft and '"hoola_inbox"' in ft and 'print("HOOLA_TAP' in ft
    assert '"-hoola_screen", sid' in ft and "app.terminate()" in ft
    yml = (tmp_path / "i/project.yml").read_text()
    assert "type: bundle.ui-testing" in yml and "TEST_TARGET_NAME: App" in yml
    assert (tmp_path / "i/hoola_qa/flow_check.sh").exists() and (tmp_path / "i/hoola_qa/flows.py").exists()
    root = Path(__file__).resolve().parents[2]
    assert "flow_check.sh" in (root / ".github/workflows/ios-check.yml").read_text()
    assert "flow walk" in (root / ".github/workflows/appgen-check.yml").read_text()
    assert "flow_check.sh" in (root / "server/app_builder/hoola-ios.yml").read_text()
