"""v0.351 PAKKA SABOOT (App Sahayak Phase 15): a second CI app made only by the generator - a field-service staff app in
Hindi + English whose list carries every field kind from Phases 8-14 (scan, photo, PDF, location, choices) - generates on
both platforms with the right blocks; CI compiles it and walks every screen and button (appgen-check / ios-check fixture2)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "app/appmaker/android/fixture2/spec.json"


def test_spec_is_current():
    from app.appmaker.android import fixture_make2 as F
    sp = json.loads(SPEC.read_text())
    assert sp["app"]["app_key"] == F.FIXTURE2_KEY and sp["app"]["language"] == "hi"
    assert sp["screens_kt"] == {} and {s["id"] for s in sp["screens"]} >= {"home", "jobs", "new_job", "route", "dashboard", "profile"}
    kinds = {f["type"] for f in sp["seed"]["backend"]["collections"][0]["fields"]}
    assert {"scan", "photo", "file", "location", "choice"} <= kinds
    assert sp["i18n"]["langs"] == ["hi", "en"] and sp["i18n"]["t"]["hi"]["Route in Maps"]


def test_generates_on_both_platforms(tmp_path):
    from app.appmaker.android import gen as AG
    from app.appmaker.ios import gen as IG
    sp = json.loads(SPEC.read_text())
    AG.write_project(sp, tmp_path / "a")
    kt = "\n".join(p.read_text() for p in (tmp_path / "a/app/src/main/java/hoola/app").rglob("*.kt"))
    assert "StopsBlock()" in kt and "StatsBlock" in kt
    assert json.loads((tmp_path / "a/app/src/main/assets/i18n.json").read_text())["default"] == "hi"
    IG.write_project(sp, tmp_path / "i")
    sw = "\n".join(p.read_text() for p in (tmp_path / "i/Sources/Screens").rglob("*.swift"))
    assert "StopsBlock()" in sw and "StatsBlock" in sw
    assert json.loads((tmp_path / "i/Resources/i18n.json").read_text())["t"]["hi"]["Jobs"] == "काम"


def test_ci_walks_it():
    wf = (ROOT.parent / ".github/workflows")
    for f in ("appgen-check.yml", "ios-check.yml"):
        t = (wf / f).read_text()
        assert "fixture2:" in t and "fixture2/spec.json" in t
