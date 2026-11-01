"""v0.364 IPAD (App Sahayak Phase 28): the iPhone app also runs natively on iPad (device family 1,2, all iPad orientations,
the readable 720pt column from v0.363); CI opens every screen on a 13-inch iPad Pro simulator and checks the 13-inch App Store
screenshot size; the App Store push uploads the iPad set too (required once an app supports iPad)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "app/appmaker/android/fixture/spec.json"


class FakeAsc:
    def __init__(self):
        self.calls = []

    def call(self, method, path, body=None, ok404=False):
        self.calls.append((method, path, body))
        if path.endswith("/appScreenshotSets") and method == "GET":
            return {"data": []}
        if path == "/v1/appScreenshotSets":
            return {"data": {"id": "set-" + body["data"]["attributes"]["screenshotDisplayType"]}}
        if path == "/v1/appScreenshots":
            return {"data": {"id": "sh1", "attributes": {"uploadOperations": []}}}
        return {"data": {}}


def _png(w, h):
    import struct
    import zlib
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * w for _ in range(1))
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0) + b"\x00\x00\x00\x00"
            + struct.pack(">I", len(zlib.compress(raw))) + b"IDAT" + zlib.compress(raw) + b"\x00\x00\x00\x00")


def test_project_runs_on_ipad(tmp_path):
    from app.appmaker.ios import gen as IG
    IG.write_project(json.loads(FIX.read_text()), tmp_path / "i")
    assert 'TARGETED_DEVICE_FAMILY: "1,2"' in (tmp_path / "i/project.yml").read_text()
    plist = next((tmp_path / "i").rglob("Info.plist")).read_text()
    assert "UISupportedInterfaceOrientations~ipad" in plist and "UIInterfaceOrientationLandscapeLeft" in plist
    sim = (tmp_path / "i/hoola_qa/sim_check.sh").read_text()
    assert 'SIM_KIND") == "ipad"' in sim and "iPad Pro" in sim


def test_asc_uploads_the_ipad_set(tmp_path):
    from app.appmaker.ios import asc
    assert asc.IPAD_DISPLAY == "APP_IPAD_PRO_3GEN_129" and (2064, 2752) in asc.IPAD_SIZES
    p = tmp_path / "home.png"
    p.write_bytes(_png(2064, 2752))
    c = FakeAsc()
    assert asc.screenshots(c, "loc1", [p], asc.IPAD_DISPLAY, asc.IPAD_SIZES) == 1
    made = [b for m, path, b in c.calls if path == "/v1/appScreenshotSets"]
    assert made[0]["data"]["attributes"]["screenshotDisplayType"] == "APP_IPAD_PRO_3GEN_129"
    bad = tmp_path / "x.png"
    bad.write_bytes(_png(1320, 2868))
    try:
        asc.screenshots(FakeAsc(), "loc1", [bad], asc.IPAD_DISPLAY, asc.IPAD_SIZES)
        raise AssertionError("an iPhone-size picture went into the iPad slot")
    except asc.AscError as e:
        assert "2064x2752" in str(e)
    from app.appmaker.ios import appstore as ST
    assert "13-inch iPad" in ST.why_line("x.png is 1x1; the 13-inch iPad slot needs 2064x2752")


def test_ci_and_builds_repo():
    wf = (ROOT.parent / ".github/workflows/ios-check.yml").read_text()
    assert "SIM_KIND=ipad bash hoola_qa/sim_check.sh" in wf and "asc.IPAD_SIZES" in wf
    b = (ROOT / "app_builder/hoola-ios.yml").read_text()
    assert "SIM_KIND=ipad" in b and "asc.py push ios qa/store/screens qa/store-ipad/screens" in b
