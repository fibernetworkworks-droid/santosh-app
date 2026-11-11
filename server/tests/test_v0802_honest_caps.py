"""v0.802 HONEST CAPS: the native-app plan says which phone features the generated app really has.

CAPS carries what the store ALLOWS; `built` says what the kit BUILDS per platform (read from the .kt / .swift kits).
A plan that wants a feature the kit does not build carries it in `caps_missing`, the chat line says "Not in this version
yet", and the App Studio Plan page shows a Built / Partly / Not yet pill per platform."""
from pathlib import Path

from app.appmaker import blueprint as BP
from app.appmaker import capabilities as CP
from app.appmaker import taxonomy as TX

D = Path(__file__).resolve().parents[1] / "app"


def test_every_cap_says_what_is_built():
    assert set(CP.BUILT) == set(CP.CAPS)
    for cid, c in CP.CAPS.items():
        b = c["built"]
        assert set(b) == {"android", "ios"}, cid
        assert b["android"] in CP.BUILT_VALUES and b["ios"] in CP.BUILT_VALUES, cid
        if "no" in b.values() or "partial" in b.values():
            assert c["built_note"].strip(), f"{cid}: a partial / no needs a plain note"


def test_this_wave_is_built_and_widgets_are_not():
    for cid in ("camera", "share_sheet", "biometrics", "in_app_review", "calendar", "contacts_pick"):
        assert CP.CAPS[cid]["built"] == {"android": "yes", "ios": "yes"}, cid
    g = {r["id"]: r for r in CP.gaps(["biometrics", "widgets", "three_d", "camera"])}
    assert "biometrics" not in g and "camera" not in g
    assert g["widgets"]["android"] == "no" and g["widgets"]["ios"] == "no"
    assert g["three_d"]["android"] == "partial" and g["three_d"]["ios"] == "no"


def test_three_d_libs_are_honest():
    c = CP.CAPS["three_d"]
    assert "SceneView" not in c["lib"] and "Filament" not in c["lib"] and "still picture" in c["lib"]
    assert "SceneKit" not in c["ios_lib"] and "RealityKit" not in c["ios_lib"]


def test_store_refused_platform_is_not_a_gap():
    # usb: iPhone has no such access (not_possible) -> n/a there, but Android is still not built
    g = CP.gaps(["usb"])[0]
    assert g["ios"] == "n/a" and g["android"] == "no"
    # a restricted feature on both stores is said by check()['problems'], not as a missing build
    assert CP.gaps(["sms_read"]) == []


def test_blueprint_carries_caps_missing_create_and_revise():
    bp = BP.make("shop", TX.GOALS["shop"]["screens"], "home screen pe widget chahiye aur fingerprint se khule")
    assert "widgets" in bp["caps_usable"] and "biometrics" in bp["caps_usable"]
    ids = [m["id"] for m in bp["caps_missing"]]
    assert "widgets" in ids and "biometrics" not in ids
    bp2, _ = BP.change(bp, {"caps": {"add": ["nfc"]}}, "")
    assert {"widgets", "nfc"} <= {m["id"] for m in bp2["caps_missing"]}
    v = BP.view(bp2)
    assert {"widgets", "nfc"} <= {m["id"] for m in v["caps_missing"]}
    w = next(c for c in v["caps"] if c["id"] == "widgets")
    assert w["built"] == {"android": "no", "ios": "no"} and w["built_note"]


def test_old_blueprint_without_caps_missing_is_still_told():
    bp = BP.make("shop", TX.GOALS["shop"]["screens"], "widget")
    bp.pop("caps_missing")
    assert "widgets" in {m["id"] for m in BP.view(bp)["caps_missing"]}


def test_plan_text_says_not_in_this_version():
    bp = BP.make("isp_ops", TX.GOALS["isp_ops"]["screens"], "home screen widget bhi chahiye")
    line = BP.say(bp)
    assert "Not in this version yet" in line and "Home-screen widget" in line
    from app.appmaker import service as S
    v = {"status": "planned", "name": "Dukaan", "questions": [],
         "plan": {"screens": [], "code_screens": [], "complex": False,
                  "blueprint": BP.view(BP.make("shop", TX.GOALS["shop"]["screens"], "widget chahiye"))}}
    assert "Not in this version yet" in S._say(v)
    assert CP.gaps_line([]) == ""


def test_agent_tool_tells_the_model_never_to_promise():
    t = (D / "agent" / "app_tools.py").read_text()
    assert "caps_missing" in t and "never promise them" in t


def test_app_studio_plan_page_shows_built_pills():
    js = (D / "static" / "console" / "appstudio.js").read_text()
    assert "bp.caps_missing" in js and "as-caplist" in js
    for w in ("'Built'", "'Partly'", "'Not yet'"):
        assert w in js
    assert "bp.features || bp.phone" not in js          # the old dead chip line is gone, not duplicated
    assert js.count("Phone features") == 1
    css = (D / "static" / "console" / "appstudio.css").read_text()
    assert ".ws-app .as-caplist" in css
