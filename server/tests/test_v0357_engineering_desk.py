"""v0.357 ENGINEERING DESK Phase 1: hire the CAD Engineer -> words -> CadQuery in a locked box -> checks -> STEP / STL /
views / drawing PDF, fixes from the real error, changes as new versions, signed files, guard, limits."""
import json
import time

import pytest

GOOD = """TITLE: Wall bracket
SIZE: 80 x 40 x 30
ASSUMED: 2 holes 8 mm
NOTES: L bracket
```python
import cadquery as cq
w, d, t = 80, 40, 10
base = cq.Workplane('XY').box(w, d, t).faces('>Z').workplane().pushPoints([(-28, 0), (28, 0)]).hole(8)
wall = cq.Workplane('XY').box(w, 8, 30).translate((0, 16, 10))
result = base.union(wall)
```"""
BROKEN = GOOD.replace("result = base.union(wall)", "result = base.union(wall).edges().fillet(50)")
CHANGED = GOOD.replace("hole(8)", "hole(10)").replace("TITLE: Wall bracket", "TITLE: Wall bracket v2")


@pytest.fixture
def eng(env, monkeypatch, tmp_path):
    pytest.importorskip("cadquery")
    monkeypatch.setenv("ENG_WORKER", "false")
    monkeypatch.setenv("ENG_DIR", str(tmp_path / "eng"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.engineering import ai, service
    replies = []
    monkeypatch.setattr(ai, "ask", lambda system, prompt, images=None, max_tokens=8000: replies.pop(0))
    from app.employee import hire
    yield {"svc": service, "replies": replies, "hire": hire}
    get_settings.cache_clear()


def test_needs_the_hire_first(eng):
    with pytest.raises(eng["svc"].EngError, match="hired nahi"):
        eng["svc"].start("default", "", "L bracket 80 x 40 mm")


def test_words_to_step_stl_views_and_drawing(eng):
    eng["hire"].hire("default", "cad")
    eng["replies"].append(GOOD)
    p = eng["svc"].start("default", "", "L bracket 80 x 40 x 30 mm, two 8 mm holes")
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert d["status"] == "done" and d["title"] == "Wall bracket"
    v = d["latest"]
    assert v["bbox"]["x"] == 80 and v["bbox"]["y"] == 40 and v["bbox"]["z"] == 30
    assert all(c["ok"] for c in v["checks"]) and {c["name"] for c in v["checks"]} >= {"Valid solid", "One body", "Size as asked"}
    assert set(v["files"]) >= {"part.step", "part.stl", "drawing.pdf", "iso.png", "front.png", "top.png", "right.png", "part.py"}
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get(v["files"]["part.step"])
    assert r.status_code == 200 and b"ISO-10303-21" in r.content[:200]
    assert c.get(v["files"]["drawing.pdf"]).content[:4] == b"%PDF"
    assert c.get(v["files"]["iso.png"]).content[:4] == b"\x89PNG"
    assert c.get(v["files"]["part.step"].replace("sig=", "sig=x")).status_code == 404     # tampered link


def test_kernel_error_goes_back_to_the_model_and_gets_fixed(eng):
    eng["hire"].hire("default", "cad")
    eng["replies"] += [BROKEN, GOOD]
    p = eng["svc"].start("default", "", "L bracket")
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert d["status"] == "done" and len(d["versions"]) == 1 and not eng["replies"]


def test_unsafe_script_never_runs(eng):
    eng["hire"].hire("default", "cad")
    bad = "TITLE: x\nSIZE: 1 x 1 x 1\n```python\nimport os\nos.system('id')\nresult = 1\n```"
    eng["replies"] += [bad, bad, bad]
    p = eng["svc"].start("default", "", "anything")
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert d["status"] == "failed" and "import os" in d["error"]


def test_change_makes_a_new_version_keeping_the_old(eng):
    eng["hire"].hire("default", "cad")
    eng["replies"].append(GOOD)
    p = eng["svc"].start("default", "", "L bracket")
    eng["svc"].run_job(p["id"])
    eng["replies"].append(CHANGED)
    eng["svc"].change("default", p["id"], "holes 10 mm karo")
    eng["svc"].run_job(p["id"])
    d = eng["svc"].get("default", p["id"])
    assert [v["n"] for v in d["versions"]] == [1, 2] and d["latest"]["words"] == "holes 10 mm karo"
    assert d["versions"][0]["volume_mm3"] > d["versions"][1]["volume_mm3"]       # bigger holes, less material


def test_size_mismatch_is_flagged(eng):
    eng["hire"].hire("default", "cad")
    wrong = GOOD.replace("SIZE: 80 x 40 x 30", "SIZE: 100 x 40 x 30")
    eng["replies"] += [wrong, wrong, wrong]
    p = eng["svc"].start("default", "", "bracket 100 mm long")
    eng["svc"].run_job(p["id"])
    v = eng["svc"].get("default", p["id"])["latest"]
    size = [c for c in v["checks"] if c["name"] == "Size as asked"][0]
    assert size["ok"] is False and "expected" in size["note"]


def test_other_tenant_cannot_see_or_change_her_part(eng):
    eng["hire"].hire("default", "cad")
    eng["replies"].append(GOOD)
    p = eng["svc"].start("default", "", "L bracket")
    with pytest.raises(eng["svc"].EngError, match="nahi mila"):
        eng["svc"].get("other", p["id"])
    assert eng["svc"].projects("other") == []


def test_daily_cap(eng, monkeypatch):
    monkeypatch.setenv("ENG_DAILY_PARTS", "1")
    eng["hire"].hire("default", "cad")
    eng["replies"].append(GOOD)
    p = eng["svc"].start("default", "", "L bracket")
    eng["svc"].run_job(p["id"])
    with pytest.raises(eng["svc"].EngError, match="Aaj ke 1"):
        eng["svc"].start("default", "", "another part")


def test_guard_rules():
    from app.engineering import guard
    assert guard.problems("import cadquery as cq\nresult = cq.Workplane('XY').box(1, 2, 3)\n") == []
    p = guard.problems("import subprocess\nresult = cq.exporters.export(1, '/etc/x')\n")
    assert any("subprocess" in x for x in p) and any("export" in x for x in p)
    assert guard.problems("import cadquery as cq\nx = 1\n") == ["script ke end mein `result = ...` (cadquery Workplane / Shape) set karo"]
    assert any("__class__" in x for x in guard.problems("result = ().__class__\n"))


def test_catalog_has_the_engineering_group():
    from app.employee import hire
    eng_keys = [k for k, c in hire.CATALOG.items() if c.get("group") == "Research, CAD, Hardware & Industrial Tech"]
    assert len(eng_keys) == 10 and hire.CATALOG["cad"]["live"] is True
    assert sum(1 for k in eng_keys if hire.CATALOG[k].get("live")) == 1


def test_v0361_lockdown_holds_without_a_network_namespace(env, monkeypatch, tmp_path):
    """v0.361 her VPS (Ubuntu 24.04) refuses `unshare -rn`: the fourth wall must stop a program / socket by itself."""
    pytest.importorskip("cadquery")
    monkeypatch.setenv("ENG_NO_NET", "false")
    from app.engineering import sandbox
    sandbox._NET_OK = None
    marker = tmp_path / "pwned"
    code = (f"import cadquery as cq\nx = cq.exporters.os.system('touch {marker}')\n"     # bypasses guard on purpose
            "result = cq.Workplane('XY').box(1, 1, 1)\n")
    r = sandbox.run(tmp_path / "a", code)
    assert r["ok"] is False and "band" in r["errors"][0] and not marker.exists()
    code2 = "import cadquery as cq\nimport math\nresult = cq.Workplane('XY').box(10, 10, 10)\n"
    r2 = sandbox.run(tmp_path / "b", code2)
    assert r2["ok"] and (tmp_path / "b" / "part.step").exists()                         # the runner's own export still works
    sandbox._NET_OK = None
