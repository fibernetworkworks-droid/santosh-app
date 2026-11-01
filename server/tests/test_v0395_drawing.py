"""REAL DRAWINGS: an A3 shop drawing measured from the model - vector hidden-line views at a standard scale, overall /
step / hole-position dimensions, hole callouts recognised from the B-rep (THRU, DEEP, CBORE, CSK), radius callouts,
ISO 286 fit limits, ISO 2768 note, title block with the projection symbol. Read back from the PDF's own text."""
import io

import pytest

cq = pytest.importorskip("cadquery")


def _plate():
    return (cq.Workplane("XY").box(80, 50, 12).faces(">Z").workplane().rect(60, 30, forConstruction=True).vertices()
            .hole(5.5).faces(">Z").workplane().center(0, 0).cboreHole(6.6, 11, 6.5).faces(">Z").workplane()
            .center(20, 0).hole(5, 8).faces(">Z").workplane().center(-40, 0).cskHole(6.6, 12, 90)
            .edges("|Z").fillet(5)).val()


def _views2d():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "engineering"))
    import views2d
    return views2d


def _text(pdf: bytes) -> str:
    from pypdf import PdfReader
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)


def test_holes_are_recognised_from_the_geometry():
    dd = _views2d().drawing_data(_plate())
    hs = dd["holes"]
    assert sum(1 for h in hs if h["dia"] == 5.5 and h["through"]) == 4
    cb = next(h for h in hs if h["cbore"])
    assert cb["dia"] == 6.6 and cb["cbore"] == [11.0, 6.5] and cb["through"]
    ck = next(h for h in hs if h["csk"])
    assert ck["csk"][0] == 12.0 and abs(abs(ck["csk"][1]) - 90) < 0.5
    blind = next(h for h in hs if not h["through"])
    assert blind["dia"] == 5.0 and blind["depth"] == 8.0
    assert all(h["view"] == "top" for h in hs)
    assert sum(1 for a in dd["arcs"] if a["r"] == 5 and not a["full"]) == 4
    assert dd["views"]["top"]["box"] == [-40.0, -25.0, 40.0, 25.0]


def test_the_sheet_carries_measured_callouts_fits_and_title_block():
    from app.engineering import drawing
    dd = _views2d().drawing_data(_plate())
    pdf = drawing.make(dd, {"title": "Mounting plate", "material": "aluminium", "mass_g": 112, "version": 2,
                            "fits": [{"d": 5.0, "fit": "H7"}], "notes": ["anodise black"]})
    t = _text(pdf)
    for want in ("4× Ø5.5 THRU", "CBORE Ø11 DEEP 6.5", "CSK Ø12 × 90°", "Ø5 H7 (+0.012/0) DEEP 8", "4× R5",
                 "ISO 2768-m", "FIRST ANGLE", "2:1", "Mounting plate", "aluminium", "112 g", "v2", "ANODISE BLACK"):
        assert want in t, want
    for size in ("80", "50", "12", "10", "70"):                       # overall + hole positions from the corner
        assert f" {size} " in f" {t} " or f"{size}\n" in t


def test_iso_286_limits():
    from app.engineering import drawing
    assert drawing.tol_text(25, "H7") == " H7 (+0.021/0)"
    assert drawing.tol_text(25, "g6") == " g6 (-0.007/-0.020)"
    assert drawing.tol_text(10, "k6") == " k6 (+0.010/+0.001)"


def test_third_angle_puts_the_top_view_above():
    from app.engineering import drawing
    dd = _views2d().drawing_data(_plate(), "third")
    s, scale, place = drawing.pick_scale(dd, "right", False)
    assert place["top"][1] > place["front"][1] and "right" in dd["views"]
    assert "THIRD ANGLE" in _text(drawing.make(dd, {"title": "P"}))


GOOD = """TITLE: Bearing plate
SIZE: 80 x 50 x 12
MATERIAL: steel
ASSUMED: none
PLAN: plate, 4 bolt holes, H7 bore
NOTES: test
```python
import cadquery as cq
result = (cq.Workplane('XY').box(80, 50, 12).faces('>Z').workplane().rect(60, 30, forConstruction=True).vertices()
          .hole(H.hole(5, 'clearance')).faces('>Z').workplane().center(0, 0).hole(20))
H.fit(20, 'H7')
H.drawing(projection='first', tolerance='f', notes=['harden to 45 HRC'], part_no='BP-7')
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
    replies = []
    monkeypatch.setattr(ai, "ask", lambda *a, **k: replies.pop(0))
    from app.employee import hire
    hire.hire("default", "cad")
    yield {"svc": service, "replies": replies}
    get_settings.cache_clear()


def test_desk_drawing_is_the_real_sheet(desk):
    desk["replies"].append(GOOD)
    p = desk["svc"].start("default", "", "steel plate 80 x 50 x 12, 4 M5 holes, 20 H7 bore, harden 45 HRC")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done"
    path = desk["svc"]._pdir("default", p["id"]) / "v1" / "drawing.pdf"
    from pypdf import PdfReader
    pdf = path.read_bytes()
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 2                   # the sheet + the shaded views
    t = _text(pdf)
    for want in ("4× Ø5.5 THRU", "Ø20 H7 (+0.021/0) THRU", "ISO 2768-f", "HARDEN TO 45 HRC", "BP-7", "FIRST ANGLE"):
        assert want in t, want
