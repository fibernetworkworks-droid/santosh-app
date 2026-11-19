"""CAD contact: an assembly as SEPARATE parts that touch, open, slide or stick, held by preloaded bolts.
Checked against stacked-beam theory (bonded = one beam, frictionless = 4x the deflection) and bolted-joint behaviour
(preload exact, a small pull adds a fraction to the bolt, a big pull opens the joint and the bolt carries it all)."""
import pytest

skfem = pytest.importorskip("skfem")
cq = pytest.importorskip("cadquery")


def _beams():
    low = cq.Workplane("XY").box(100, 10, 5, centered=(False, True, False)).val()
    up = cq.Workplane("XY").box(100, 10, 5, centered=(False, True, False)).translate((0, 0, 5)).val()
    return [("low", low), ("up", up)]


SPEC = {"fixed": "<X", "loads": [{"faces": ">X", "force": [0, 0, -100]}], "material": "steel", "nodes": 1400}
SOLID = 100 * 100 ** 3 / (3 * 200000 * (10 * 10 ** 3 / 12))          # one 10 x 10 beam: 0.2 mm


def test_bonded_stack_bends_like_one_beam():
    from app.engineering import contact
    r = contact.solve(_beams(), {**SPEC, "contact": "bonded"})
    assert abs(r["max_disp_mm"] - SOLID) / SOLID < 0.05
    assert r["equilibrium_error_pct"] < 0.5 and r["contacts"][0]["open_pct"] == 0


def test_frictionless_stack_bends_four_times_more():
    from app.engineering import contact
    r = contact.solve(_beams(), {**SPEC, "contact": "frictionless"})
    assert abs(r["max_disp_mm"] - 4 * SOLID) / (4 * SOLID) < 0.08      # two beams of h/2 each: I / 4
    assert r["equilibrium_error_pct"] < 0.5


def _blocks():
    bot = cq.Workplane("XY").box(30, 30, 20, centered=(True, True, False)).faces(">Z").workplane().hole(11).val()
    top = (cq.Workplane("XY").box(30, 30, 20, centered=(True, True, False)).faces(">Z").workplane().hole(11)
           .translate((0, 0, 20)).val())
    return [("bottom", bot), ("top", top)]


def _bolted(p):
    from app.engineering import contact
    return contact.solve(_blocks(), {"fixed": "<Z", "loads": [{"faces": ">Z", "force": [0, 0, p]}], "material": "steel",
                                     "nodes": 1200, "contact": "frictionless",
                                     "bolts": [{"m": 10, "at": [0, 0], "grade": "8.8"}]})


def test_bolt_preload_and_load_sharing():
    r = _bolted(5000)
    b = r["bolts"][0]
    assert b["preload_N"] == pytest.approx(0.75 * 580 * 58.0, rel=0.01)          # calibrated pretension
    assert 0 < b["change_N"] < 0.3 * 5000                                         # the joint takes most of it
    assert not r["separated"] and r["equilibrium_error_pct"] < 0.5


def test_big_pull_opens_the_joint_and_the_bolt_carries_it():
    r = _bolted(60000)
    assert r["separated"] is True
    assert r["bolts"][0]["loaded_N"] == pytest.approx(60000, rel=0.1)
    assert r["bolts"][0]["yield_sf"] < 1                                          # over the M10 8.8 proof load
    assert r["passes"] is False


def test_a_part_nothing_holds_is_refused():
    from app.engineering import contact
    a = cq.Workplane("XY").box(10, 10, 10).val()
    b = cq.Workplane("XY").box(10, 10, 10).translate((30, 0, 0)).val()
    with pytest.raises(contact.ContactError, match="not held by"):
        contact.solve([("a", a), ("b", b)], {"fixed": "<X", "loads": [], "nodes": 600, "contact": "frictionless"})


ASSY = """TITLE: Bolted bracket
SIZE: 30 x 30 x 40
MATERIAL: steel
ASSUMED: none
PLAN: two blocks bolted with one M{m}, pulled apart
NOTES: test
```python
import cadquery as cq
bot = cq.Workplane('XY').box(30, 30, 20, centered=(True, True, False)).faces('>Z').workplane().hole({hole})
top = cq.Workplane('XY').box(30, 30, 20, centered=(True, True, False)).faces('>Z').workplane().hole({hole}).translate((0, 0, 20))
result = cq.Assembly(name='bracket').add(bot, name='base').add(top, name='cap')
H.analyze('static', fixed='<Z', loads=[{{'faces': '>Z', 'force': (0, 0, 30000)}}], contact='frictionless',
          bolts=[{{'m': {m}, 'at': (0, 0), 'grade': '8.8'}}], nodes=900)
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


def test_overloaded_bolted_joint_is_redesigned(desk):
    desk["replies"] += [ASSY.format(m=6, hole=6.6), ASSY.format(m=16, hole=17.5)]
    p = desk["svc"].start("default", "", "two blocks bolted together, 3 tonne pull, will the bolt hold")
    desk["svc"].run_job(p["id"])
    d = desk["svc"].get("default", p["id"])
    assert d["status"] == "done" and not desk["replies"]
    assert "joint separates" in desk["seen"][1] or "bolt overloaded" in desk["seen"][1]
    st = d["latest"]["analysis"][0]
    assert st["ok"] and st["bolts"][0]["bolt"].startswith("M16") and not st["separated"]
    assert any("Bolt M16" in line for line in st["lines"])


def test_friction_holds_then_slips():
    from app.engineering import contact
    base = {"fixed": "<Z", "material": "steel", "nodes": 1200, "contact": "friction", "friction": 0.2,
            "bolts": [{"m": 10, "at": [0, 0], "grade": "8.8"}]}
    held = contact.solve(_blocks(), {**base, "loads": [{"faces": ">Z", "force": [2000, 0, 0]}]})
    slid = contact.solve(_blocks(), {**base, "loads": [{"faces": ">Z", "force": [12000, 0, 0]}]})
    assert held["slipped"] is False and held["contacts"][0]["slipping_pct"] < 50       # 2 kN < 0.2 x 25 kN clamp
    assert slid["slipped"] is True                                                    # 12 kN > friction can carry
