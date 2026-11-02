"""BUCKLING: a slender part FOLDS long before the stress breaks it, and the stress check cannot see that.
The eigenvalue solver is checked against Euler's column (mode 1 AND mode 2 = 9x mode 1), against Hoola's own
Euler / Johnson hand calculation, and the whole desk loop: a thin post that folds comes back and is redesigned."""
import math

import pytest

skfem = pytest.importorskip("skfem")
cq = pytest.importorskip("cadquery")

E_STEEL = 200000.0


def _col(L=300.0, b=10.0):
    return cq.Workplane("XY").box(b, b, L, centered=(True, True, False)).val()


def _spec(L=300.0, F=1000.0, **kw):
    return {"kind": "buckling", "material": "steel", "fixed": "<Z", "nodes": 2000, "converge": False,
            "loads": [{"faces": ">Z", "force": [0, 0, -F]}], **kw}


def test_euler_cantilever_column_and_its_second_mode():
    from app.engineering import fea
    L, b = 300.0, 10.0
    r = fea.run(_col(L, b), _spec(L, modes=3))
    euler = math.pi ** 2 * E_STEEL * (b ** 4 / 12) / (4 * L * L)          # fixed-free: (KL)² = (2L)²
    assert r["load_factor"] * 1000 == pytest.approx(euler, rel=0.03)      # mode 1 within 3 % of theory
    assert r["critical_load_N"] == pytest.approx(euler, rel=0.03)
    assert r["factors"][2] / r["factors"][0] == pytest.approx(9.0, rel=0.05)   # mode 2 of a cantilever = 9 x mode 1
    assert r["governs"] == "buckling" and not r["buckles"] and r["passes"]
    assert r["surface"]["t"] and "40-70" in r["note"]


def test_the_factor_scales_with_the_load_and_the_length():
    from app.engineering import fea
    base = fea.run(_col(), _spec(F=1000.0))["load_factor"]
    twice = fea.run(_col(), _spec(F=2000.0))["load_factor"]
    assert twice == pytest.approx(base / 2, rel=0.02)                     # twice the load, half the factor
    longer = fea.run(_col(L=600.0), _spec(L=600.0, F=1000.0))["load_factor"]
    assert longer == pytest.approx(base / 4, rel=0.06)                    # twice as long, a quarter the factor


def test_it_folds_under_her_own_load():
    from app.engineering import fea
    r = fea.run(_col(), _spec(F=9000.0, min_lf=2))
    assert r["buckles"] and not r["passes"] and r["load_factor"] < 1 and r["need_given"]
    from app.engineering.report import summary_rows
    rows = " | ".join(summary_rows({**r, "ok": True}))
    assert "IT FOLDS under her own load" in rows and "FAIL" in rows


def test_a_stubby_block_and_a_part_in_tension_are_not_buckling_cases():
    from app.engineering import fea
    blk = cq.Workplane("XY").box(60, 60, 60).val()
    r = fea.run(blk, _spec(nodes=1000))
    assert r["governs"] == "strength" and r["not_a_buckling_case"] and "yield / break long before" in r["note"]
    t = fea.run(_col(), _spec(F=-1000.0, nodes=1200))                      # pulled, not pushed
    assert t["governs"] == "strength" and t["not_a_buckling_case"]


def test_a_deep_section_beats_a_thick_one():
    """The fix the desk is told to make must really work: depth cubed beats thickness."""
    from app.engineering import fea
    flat = cq.Workplane("XY").box(30, 4, 300, centered=(True, True, False)).val()     # 120 mm², weak way = 4 mm
    deep = cq.Workplane("XY").box(11, 11, 300, centered=(True, True, False)).val()    # 121 mm², same metal
    lf_flat = fea.run(flat, _spec(nodes=1800))["load_factor"]
    lf_deep = fea.run(deep, _spec(nodes=1800))["load_factor"]
    assert lf_deep > 5 * lf_flat                                           # same area, far harder to fold


def test_hand_calc_agrees_with_the_fea_and_knows_short_columns():
    from app.engineering import calc, fea
    L, b = 300.0, 10.0
    hand = calc.run("column", {"length_mm": L, "section": {"type": "rect", "b": b, "h": b}, "ends": "cantilever",
                               "load_N": 1000.0, "min_sf": 2.0})
    euler = math.pi ** 2 * E_STEEL * (b ** 4 / 12) / (4 * L * L)
    assert hand["critical_load_N"] == pytest.approx(euler, rel=1e-3) and hand["K"] == 2.0
    assert hand["radius_of_gyration_mm"] == pytest.approx(b / math.sqrt(12), abs=1e-3)
    assert hand["mode"].startswith("Euler") and hand["passes"] is True
    fea_lf = fea.run(_col(L, b), _spec(L))["load_factor"]
    assert hand["critical_load_N"] == pytest.approx(fea_lf * 1000, rel=0.03)     # two different methods agree
    short = calc.run("column", {"length_mm": 40, "section": {"type": "round", "d": 20}, "ends": "pinned",
                                "load_N": 50000.0})
    assert short["mode"].startswith("Johnson") and short["slenderness_KL_r"] < short["changeover_slenderness"]
    assert short["critical_load_N"] < short["euler_load_N"]                       # Johnson never promises Euler's load
    folds = calc.run("column", {"length_mm": L, "section": {"type": "rect", "b": b, "h": b}, "ends": "cantilever",
                                "load_N": 9000.0})
    assert "IT FOLDS" in folds["verdict"]
    with pytest.raises(Exception):
        calc.run("column", {"length_mm": 100, "section": {"type": "rect", "b": 5, "h": 5}, "ends": "glued"})


POST = """TITLE: Post
MATERIAL: steel
ASSUMED: none
PLAN: a post that carries the load
NOTES: test
```python
import cadquery as cq
result = cq.Workplane('XY').box({b}, {b}, 400, centered=(True, True, False))
H.analyze('buckling', fixed='<Z', loads=[{{'faces': '>Z', 'force': (0, 0, -4000)}}], min_lf=2, nodes=900, converge=False)
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


def test_a_folding_post_is_sent_back_and_made_deeper(desk):
    desk["replies"] += [POST.format(b=12), POST.format(b=30)]
    p = desk["svc"].start("default", "", "steel post 400 mm tall carrying 400 kg, must not buckle")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    back = desk["seen"][1]
    assert "it FOLDS (buckles) too easily" in back and "depth^3" in back
    v = d["latest"]
    st = v["analysis"][0]
    assert st["kind"] == "buckling" and st["passes"] is True and st["load_factor"] >= 2
    assert any(c["name"] and "uckling" in c["name"] for c in v["checks"]) or st["lines"]
    assert "fea_0.png" in v["files"]


def test_the_guide_and_the_tools_know_buckling():
    from app.agent.eng_tools import ENG_TOOLS
    from app.engineering import ai, parts
    assert "buckling" in ai.GUIDE and "min_lf" in ai.GUIDE and "I goes as h^3" in ai.GUIDE
    tool = next(t for t in ENG_TOOLS if t["name"] == "eng_calc")
    assert "column" in tool["input_schema"]["properties"]["kind"]["enum"] and "FOLD" in tool["description"]
    parts.STUDIES.clear()
    parts.analyze("buckling", fixed="<Z")
    assert parts.STUDIES[0]["kind"] == "buckling"
    parts.STUDIES.clear()
    with pytest.raises(ValueError, match="buckling"):
        parts.analyze("wobble")
