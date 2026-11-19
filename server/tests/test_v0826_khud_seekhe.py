"""v0.999.37 KHUD SEEKHE (P10 of docs/HOOLA_PROMPTING_PLAN.md): the outcome ledger changes Hoola Prompting's questions,
defaults and recipe values - only by rule, only with a measured gain, only on the owner's tap. THE PLAN'S GATE: a proposed
change that does not gain is refused. Her own usual choices are offered to her and used only after her yes."""
import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
CON = REPO / "server" / "app" / "static" / "console"
KEY = "test-key-khud"
H = {"Authorization": f"Bearer {KEY}"}


@pytest.fixture
def kh(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.prompting import brief as B
    from app.prompting import context as C
    from app.prompting import khud as K
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    monkeypatch.setattr(B, "ASK", [lambda s, p: {}])
    K._CACHE.clear()
    yield K
    K._CACHE.clear()
    get_settings.cache_clear()


_N = [0]


def runs(n, kept, section="image", slots=None, choices=None, tenant="t1", recipe="", dialect="", days=2):
    """n graded runs, the first `kept` kept, the rest redone."""
    from app.db import now, session
    from app.prompting import ledger as L
    L.ensure_table()
    with session() as s:
        for i in range(n):
            _N[0] += 1
            s.add(L.PromptRun(id=f"prn_k{_N[0]}", tenant_id=tenant, section=section, slots=json.dumps(slots or {}),
                              choices=json.dumps(choices or {}), recipe=recipe, dialect=dialect,
                              grade="kept" if i < kept else "redone", status="settled",
                              handed_at=now() - timedelta(days=days, minutes=_N[0])))


def test_measure_needs_enough_on_both_sides(kh):
    runs(8, 6, choices={"style": "Festive poster"})
    runs(7, 2, choices={"style": "Real photograph"})
    m = kh.measure("default", "image", "style", value="Festive poster")
    assert m["gain"] is False and "Not enough results yet" in m["say"]           # 7 on one side is not enough
    runs(1, 0, choices={"style": "Real photograph"})
    m = kh.measure("default", "image", "style", value="Festive poster")
    assert m["gain"] is True and m["with"] == {"kept": 6, "of": 8, "rate": 75} and m["without"]["rate"] == 25


def test_a_change_that_does_not_gain_is_refused(kh):
    """THE GATE: owner-written with no data = refused at once; no clear gain = refused; accepted only with the gain."""
    c = kh.propose("default", "image", "style", value="Festive poster")
    assert c["status"] == "refused" and c["reason"].startswith("No gain shown")
    runs(8, 4, choices={"style": "Festive poster"})
    runs(8, 4, choices={"style": "Real photograph"})                           # same rate = no gain
    c = kh.propose("default", "image", "style", value="Festive poster")
    assert c["status"] == "refused" and "at least 10 points" in c["reason"]
    with pytest.raises(kh.KhudError, match="own options"):
        kh.propose("default", "image", "style", value="a moody neon look")
    with pytest.raises(kh.KhudError):
        kh.propose("alert", "image", "dialect")
    assert kh.default_for("image") == {}


def test_accept_measures_again(kh):
    runs(8, 7, choices={"style": "Festive poster"})
    runs(8, 2, choices={"style": "Real photograph"})
    new = kh.scan()
    d = [c for c in new if c["kind"] == "default" and c["slot"] == "style"]
    assert d and d[0]["value"] == "Festive poster" and d[0]["status"] == "proposed"
    assert kh.scan() == []                                                     # idempotent
    runs(20, 0, choices={"style": "Festive poster"})                           # the gain is gone by the time she taps
    got = kh.decide(d[0]["id"], "accept")
    assert got["status"] == "refused" and "checked again" in got["reason"]
    assert kh.default_for("image") == {}


def test_accepted_default_preselects_as_hoolas_suggestion_and_undo(kh):
    from app.prompting import brief as B
    runs(8, 7, choices={"style": "Festive poster"})
    runs(8, 2, choices={"style": "Real photograph"})
    cid = [c for c in kh.scan() if c["kind"] == "default"][0]["id"]
    assert kh.decide(cid, "accept")["status"] == "accepted"
    b = B.understand("t9", "a poster for my bakery opening", "image")
    assert b["slots"]["style"] == {"value": "Festive poster", "source": "hoola_guess"}    # still marked a suggestion
    assert kh.decide(cid, "undo")["status"] == "undone"
    assert "style" not in B.understand("t9", "a poster for my bakery opening", "image")["slots"]
    with pytest.raises(kh.KhudError):
        kh.decide(cid, "undo")


def test_ask_off_removes_the_question(kh):
    from app.prompting import brief as B
    runs(8, 5, slots={"style": "her_answer"})
    runs(8, 5, slots={"style": "hoola_guess"})                                 # answered or not: same
    off = [c for c in kh.scan() if c["kind"] == "ask_off" and c["slot"] == "style"]
    assert off and "Stop asking" in off[0]["what"]
    b = B.understand("t9", "a poster of a cup of chai", "image")
    assert any(q["key"] == "style" for q in b["questions"]) or "style" in b["missing"]
    kh.decide(off[0]["id"], "accept")
    b = B.understand("t9", "a poster of a cup of chai", "image")
    assert "style" not in b["missing"] and not any(q["key"] == "style" for q in b["questions"])


def test_recipe_value_change_applies_in_use(kh):
    from app.prompting import recipes as R
    runs(8, 7, recipe="img-festival-offer", choices={"size": "9:16"})
    runs(8, 2, recipe="img-festival-offer", choices={"size": "4:5"})
    rc = [c for c in kh.scan() if c["kind"] == "recipe"]
    assert rc and rc[0]["recipe"] == "img-festival-offer" and rc[0]["value"] == "9:16"
    kh.decide(rc[0]["id"], "accept")
    b = R.use("img-festival-offer", {"festival": "Diwali", "business": "Balaji", "offer": "Flat 30% Off"})["brief"]
    assert b["slots"]["size"]["value"] == "9:16"


def test_alert_on_a_drop_changes_nothing(kh):
    runs(8, 7, dialect="image-1", days=20)
    runs(8, 2, dialect="image-2", days=2)
    al = [c for c in kh.scan() if c["kind"] == "alert"]
    assert al and al[0]["value"] == "image-2" and "got worse" in al[0]["what"]
    with pytest.raises(kh.KhudError, match="seen"):
        kh.decide(al[0]["id"], "accept")
    assert kh.decide(al[0]["id"], "dismiss")["status"] == "dismissed"


def test_her_usual_only_after_her_yes(kh):
    from app.prompting import brief as B
    from app.prompting import ledger as L
    for _ in range(4):
        L.hand("t1", "a poster", B.apply(B.understand("t1", "a picture of chai", "image"), {"size": "4:5"}))
    got = kh.usual_scan("t1")
    u = [x for x in got if x["slot"] == "size"]
    assert u and u[0]["value"] == "4:5" and u[0]["status"] == "offered"
    assert "size" not in B.understand("t1", "a picture of samosa", "image")["slots"]       # offered is not on
    kh.usual_decide("t1", u[0]["id"], True)
    assert B.understand("t1", "a picture of samosa", "image")["slots"]["size"] == {"value": "4:5", "source": "her_default"}
    assert "size" not in B.understand("t2", "a picture of samosa", "image")["slots"]       # only hers
    with pytest.raises(KeyError):
        kh.usual_decide("t2", u[0]["id"], True)


def test_routes_owner_only(kh, monkeypatch):
    import app.main as M
    c = TestClient(M.app)
    runs(8, 7, choices={"style": "Festive poster"})
    runs(8, 2, choices={"style": "Real photograph"})
    r = c.get("/api/prompting/khud", headers=H).json()
    assert r["rules"] == {"min_each_side": 8, "gain_points": 10, "same_points": 5} and r["changes"]
    cid = r["changes"][0]["id"]
    assert c.post(f"/api/prompting/khud/{cid}/maybe", headers=H).status_code == 400
    assert c.post("/api/prompting/khud/nope/accept", headers=H).status_code == 404
    bad = c.post("/api/prompting/khud", headers=H, json={"kind": "default", "section": "image", "slot": "size", "value": "1:1"}).json()
    assert bad["status"] == "refused"
    assert c.get("/api/prompting/usual", headers=H).json() == {"usual": []}
    monkeypatch.setattr(M, "_resolve_tenant", lambda req: "someone_else")
    assert c.get("/api/prompting/khud", headers=H).status_code == 403
    assert c.post(f"/api/prompting/khud/{cid}/accept", headers=H).status_code == 403
    assert c.get("/api/prompting/usual", headers=H).status_code == 200


def test_page_wiring():
    js = (CON / "prompting.js").read_text()
    for needle in ("Hoola improving itself", "Your usual choices", "data-khud", "data-usual", "/api/prompting/khud",
                   "/api/prompting/usual"):
        assert needle in js, needle


def test_khud_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    base, browser, key = arena_server
    runs(8, 7, choices={"style": "Festive poster"}, tenant="default")
    runs(8, 2, choices={"style": "Real photograph"}, tenant="default")
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/prompting#/results")
    pg.wait_for_selector("#hpKhud [data-act=accept]")
    assert "Pre-select 'Festive poster'" in pg.inner_text("#hpKhud")
    pg.click("#hpKhud [data-act=accept]")
    pg.wait_for_selector("#hpKhud [data-act=undo]")
    assert "In use" in pg.inner_text("#hpKhud")
    box = pg.evaluate("(() => { const m = document.querySelector('#hpMain'); return m.scrollWidth <= m.clientWidth + 1; })()")
    assert box and not [e for e in errs if "prompting" in e], errs
