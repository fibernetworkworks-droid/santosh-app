"""HOOLA DFM: manufacturability MEASURED on the part (3D print, CNC, sheet metal, injection moulding), every row with
the measured value, the limit, its source and a fix; a FAIL goes back to the designer like a weak part does."""
import sys
from pathlib import Path

import pytest

cq = pytest.importorskip("cadquery")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "engineering"))


def _run(shape, spec, sheet=None):
    import dfm
    import views2d
    hl = [{"dia": h["dia"], "depth": h["depth"], "through": h["through"], "p3": h["entry"]}
          for h in views2d.hole_stacks(shape)]
    r = dfm.check(shape, spec, hl, sheet)
    return r, {row["check"]: row for row in r["rows"]}


def test_fdm_thin_walls_and_overhangs():
    shell = (cq.Workplane("XY").box(40, 40, 30).faces(">Z").shell(-0.8)
             .union(cq.Workplane("XY").box(30, 10, 3).translate((0, 25, 10))).val())
    r, rows = _run(shell, {"process": "fdm"})
    assert rows["Wall thickness"]["status"] == "fail" and "1.2" in rows["Wall thickness"]["limit"]
    assert rows["Overhangs (need support)"]["status"] == "review"
    ok, rows2 = _run(cq.Workplane("XY").box(40, 40, 30).val(), {"process": "fdm"})
    assert rows2["Wall thickness"]["status"] == "pass" and ok["fails"] == 0


def test_powder_processes_need_no_support_rows():
    _r, rows = _run(cq.Workplane("XY").box(20, 20, 20).val(), {"process": "sls"})
    assert rows["Overhangs"]["status"] == "pass"


def test_cnc_sharp_inside_corners_fail_and_rounded_pass():
    sharp = cq.Workplane("XY").box(60, 40, 20).faces(">Z").workplane().rect(30, 20).cutBlind(-10).val()
    r, rows = _run(sharp, {"process": "cnc", "material": "aluminium", "tool_d": 6})
    assert rows["Internal vertical corners"]["status"] == "fail" and "4 sharp" in rows["Internal vertical corners"]["measured"]
    round_ = (cq.Workplane("XY").box(60, 40, 20).faces(">Z").workplane().rect(30, 20).cutBlind(-10)
              .edges("|Z").fillet(4)).val()
    r2, rows2 = _run(round_, {"process": "cnc", "material": "aluminium", "tool_d": 6})
    assert rows2["Internal vertical corners"]["status"] == "pass" and r2["fails"] == 0
    small = (cq.Workplane("XY").box(60, 40, 20).faces(">Z").workplane().rect(30, 20).cutBlind(-10)
             .edges("|Z").fillet(2)).val()
    _r3, rows3 = _run(small, {"process": "cnc", "tool_d": 6})
    assert rows3["Inside corner radii"]["status"] == "fail"                 # R2 < the 3 mm tool radius


def test_cnc_deep_hole_and_setups():
    b = cq.Workplane("XY").box(60, 40, 40).faces(">Z").workplane().center(20, 10).hole(3, 36).val()
    _r, rows = _run(b, {"process": "cnc"})
    assert rows["Hole depth / diameter"]["status"] == "fail"                # 12 x d > 10 x d
    assert rows["Setups (3-axis)"]["measured"].startswith(("1", "2"))


def test_sheet_flange_and_bend_rules():
    import parts
    parts.FLAT.clear()
    s = parts.sheet([(40, 90), (30, -90), (9, 0)], 50, 2).val()
    _r, rows = _run(s, {"process": "sheet"}, parts.FLAT["sheet"])
    assert rows["Flange length"]["status"] == "fail" and rows["Inside bend radius"]["status"] == "pass"
    assert rows["Constant thickness"]["status"] == "pass"
    parts.FLAT.clear()
    tight = parts.sheet([(40, 90), (30, 0)], 20, 2, r=1).val()
    _r, rows = _run(tight, {"process": "sheet"}, parts.FLAT["sheet"])
    assert rows["Inside bend radius"]["status"] == "fail"


def test_molding_draft_walls_and_clamp():
    box = cq.Workplane("XY").box(60, 40, 25).faces(">Z").shell(-2).val()
    r, rows = _run(box, {"process": "molding", "material": "abs"})
    assert rows["Draft on side walls"]["status"] == "fail"
    assert rows["Wall thickness"]["status"] == "pass" and rows["Undercuts"]["status"] == "pass"
    assert "t at 35 MPa" in rows["Clamp force (estimate)"]["measured"]
    drafted = (cq.Workplane("XY").rect(60, 40).extrude(25, taper=2).faces(">Z").shell(-2)).val()
    _r, rows2 = _run(drafted, {"process": "molding", "material": "abs"})
    assert rows2["Draft on side walls"]["status"] in ("pass", "review")
    assert r["rows"][0]["source"].startswith("Protolabs")


CNC = """TITLE: Pocket block
SIZE: 60 x 40 x 20
MATERIAL: aluminium
ASSUMED: none
PLAN: block with a pocket, milled
NOTES: test
```python
import cadquery as cq
result = cq.Workplane('XY').box(60, 40, 20).faces('>Z').workplane().rect(30, 20).cutBlind(-10){fillet}
H.make('cnc', material='aluminium', tool_d=6)
```"""


@pytest.fixture
def desk(env, monkeypatch, tmp_path):
    monkeypatch.setenv("ENG_WORKER", "false")
    monkeypatch.setenv("ENG_DIR", str(tmp_path / "eng"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    monkeypatch.setenv("ENG_LOOK_ROUNDS", "0")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.engineering import ai, service
    replies, seen = [], []

    def fake_ask(system, prompt, images=None, max_tokens=8000, think=False):
        seen.append(prompt)
        return replies.pop(0)
    monkeypatch.setattr(ai, "ask", fake_ask)
    from app.employee import hire
    hire.hire("default", "cad")
    yield {"svc": service, "replies": replies, "seen": seen}
    get_settings.cache_clear()


def test_unmachinable_corners_are_sent_back_and_fixed(desk):
    desk["replies"] += [CNC.format(fillet=""), CNC.format(fillet=".edges('|Z').fillet(4)")]
    p = desk["svc"].start("default", "", "aluminium block 60 x 40 x 20 with a 30 x 20 pocket 10 deep, CNC milled")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    assert "manufacturing (cnc): Internal vertical corners" in desk["seen"][1]
    v = d["latest"]
    assert v["dfm"]["process"] == "cnc" and v["dfm"]["fails"] == 0
    assert "analysis.pdf" in v["files"]
