"""PAST YIELD: the linear stress check only says "it has yielded somewhere". This says what happens next - how much
PERMANENT BEND is left after the load comes off, and at what load the part COLLAPSES.

Real elastic-plastic stepping (von Mises radial return at every integration point, modified Newton with Aitken
acceleration because the elastic stiffness under-corrects once part of the body has gone soft). Checked against the
two limit loads anyone can work out by hand: a bar in tension gives way when the section reaches yield, and a
rectangular beam in bending carries 1.5x its first-yield load - the plastic shape factor.
"""
import pytest

skfem = pytest.importorskip("skfem")
cq = pytest.importorskip("cadquery")

SY = 250.0          # steel yield in the material table


def _bar(a=10.0, L=80.0):
    return cq.Workplane("XY").box(a, a, L, centered=(True, True, False)).val()


def _spec(F, **kw):
    return {"kind": "plastic", "material": "steel", "fixed": "<Z", "nodes": 900, "converge": False,
            "loads": [{"faces": ">Z", "force": [0, 0, F]}], **kw}


def test_a_bar_in_tension_gives_way_when_the_section_reaches_yield():
    from app.engineering import fea
    A = 100.0
    r = fea.run(_bar(), _spec(0.5 * SY * A, max_factor=2.3))        # half of yield: the section yields at x2.0
    assert r["kind"] == "plastic" and r["hardening_MPa"] > 0        # a realistic hardening slope by default
    assert r["collapse_factor"] == pytest.approx(2.0, rel=0.25)     # the textbook limit load, within a load step or two
    assert r["carries_up_to"] >= 1.3
    ys = [h["yielded_pct"] for h in r["steps"]]
    assert ys[0] == 0.0 and ys[-1] > 5.0 and ys == sorted(ys)       # the yielded region only ever grows
    d = [h["max_disp_mm"] for h in r["steps"]]
    first = (d[1] - d[0]) / (r["steps"][1]["factor"] - r["steps"][0]["factor"])
    last = (d[-1] - d[-2]) / (r["steps"][-1]["factor"] - r["steps"][-2]["factor"])
    assert last > 4 * first                                        # it runs away at the end: that IS the collapse
    assert "collapse" in r["collapse_note"] and r["surface"]["t"]


def test_a_beam_in_bending_carries_more_than_its_first_yield_load():
    """The plastic reserve: a rectangular section does not fail when its outer fibre yields."""
    from app.engineering import fea
    b, h, L = 12.0, 12.0, 90.0
    beam = cq.Workplane("XY").box(L, b, h, centered=(False, True, True)).val()
    Fy = SY * (b * h * h / 6) / L                                   # the tip load that first yields the root
    r = fea.run(beam, {"kind": "plastic", "material": "steel", "fixed": "<X", "nodes": 1100,
                       "loads": [{"faces": ">X", "force": [0, 0, -Fy]}], "max_factor": 1.9, "max_set_mm": 0.05})
    assert r["first_yield_factor"] == pytest.approx(1.0, rel=0.25)   # we loaded it to first yield on purpose
    assert r["collapse_factor"] == pytest.approx(1.5, rel=0.3)       # 1.5 = the rectangular shape factor
    assert r["collapse_factor"] > 1.15                              # it clearly outlives first yield
    assert r["steps"][-1]["yielded_pct"] > 10.0
    hl = r["at_her_load"]
    assert hl and 0 <= hl["permanent_set_mm"] < 0.05 and hl["yielded_pct"] > 0   # at FIRST yield the set is ~nothing
    assert hl["max_disp_mm"] >= hl["elastic_would_be_mm"]            # plastic never comes out stiffer
    assert r["passes"] is True


def test_no_permanent_set_below_yield_and_some_above_it():
    from app.engineering import fea
    A = 100.0
    low = fea.run(_bar(), _spec(0.3 * SY * A, max_factor=1.0))      # nowhere near yield
    assert low["at_her_load"]["permanent_set_mm"] == 0.0
    assert low["at_her_load"]["yielded_pct"] == 0.0 and low["collapse_factor"] is None
    assert low["at_her_load"]["max_disp_mm"] == pytest.approx(low["at_her_load"]["elastic_would_be_mm"], rel=1e-6)
    high = fea.run(_bar(), _spec(0.9 * SY * A, max_factor=1.0, max_set_mm=0.0005))
    hl = high["at_her_load"]
    assert hl["permanent_set_mm"] > 0 and hl["yielded_pct"] > 0      # it keeps a set, and she is told it is too much
    assert high["passes"] is False


def test_it_says_plainly_when_the_part_cannot_even_hold_her_load():
    from app.engineering import fea
    r = fea.run(_bar(a=4.0), _spec(3.0 * SY * 16.0, max_factor=1.3))
    assert r["at_her_load"] is None and r["passes"] is False
    assert r["collapse_factor"] <= 1.0 and r["tears_at_pct"] == 15.0
    assert "tears" in r["collapse_note"] or "below her own load" in r["collapse_note"]
    from app.engineering.report import summary_rows
    rows = " | ".join(summary_rows({**r, "ok": True}))
    assert "does not even hold her own load" in rows


def test_the_rows_the_desk_and_the_guide():
    from app.engineering import ai, parts
    from app.engineering.report import summary_rows
    from app.engineering.service import _weak
    st = {"ok": True, "kind": "plastic", "material": "steel", "yield_MPa": 250.0, "hardening_MPa": 1000.0,
          "first_yield_factor": 0.8, "collapse_factor": 1.4, "collapse_at_least": 1.3, "carries_up_to": 1.15,
          "max_set_mm": 0.1, "passes": False, "mesh": {"nodes": 900, "elements": 3000, "h_mm": 2.0},
          "steps": [{"factor": 1.0, "max_disp_mm": 0.4, "max_plastic_strain_pct": 0.3, "yielded_pct": 4.0}],
          "at_her_load": {"max_disp_mm": 0.42, "elastic_would_be_mm": 0.40, "permanent_set_mm": 0.35,
                          "max_plastic_strain_pct": 0.3, "yielded_pct": 4.0, "holds": False},
          "note": "elastic-plastic", "collapse_note": "collapses at about x1.4"}
    rows = " | ".join(summary_rows(st))
    assert "PERMANENT SET" in rows and "0.35" in rows and "FAIL" in rows and "COLLAPSES" in rows
    probs = _weak({"studies": [st]})
    assert any("PERMANENT BEND" in p and "0.35" in p for p in probs)
    st2 = {**st, "at_her_load": None}
    assert any("COLLAPSES under her own load" in p for p in _weak({"studies": [st2]}))
    assert "plastic" in ai.GUIDE and "max_set_mm" in ai.GUIDE and "permanent" in ai.GUIDE.lower()
    parts.STUDIES.clear()
    parts.analyze("plastic", fixed="<Z", max_set_mm=0.2)
    assert parts.STUDIES[0]["kind"] == "plastic" and parts.STUDIES[0]["max_set_mm"] == 0.2
    parts.STUDIES.clear()
    with pytest.raises(ValueError, match="plastic"):
        parts.analyze("squish")


HOOK = """TITLE: Lug
MATERIAL: steel
ASSUMED: none
PLAN: a lug that must not take a permanent set
NOTES: test
```python
import cadquery as cq
result = cq.Workplane('XY').box(60, 20, {t}, centered=(False, True, False))
H.analyze('plastic', fixed='<X', loads=[{{'faces': '>X', 'force': (0, 0, -2600)}}], max_set_mm=0.05,
          nodes=500, max_factor=1.15)
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


def test_a_lug_that_bends_for_good_is_sent_back(desk):
    desk["replies"] += [HOOK.format(t=6), HOOK.format(t=20)]
    p = desk["svc"].start("default", "", "steel lug, 260 kg on the end, must not bend permanently")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    back = desk["seen"][1]
    assert "PERMANENT BEND" in back or "COLLAPSES under her own load" in back
    v = d["latest"]
    st = v["analysis"][0]
    assert st["kind"] == "plastic" and st["passes"] is True and v["bbox"]["z"] == 20
    assert st["at_her_load"]["permanent_set_mm"] <= 0.05 and st["lines"]
