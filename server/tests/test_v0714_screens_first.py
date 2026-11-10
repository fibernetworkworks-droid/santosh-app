"""v0.714 SCREENS FIRST (owner: "STILL SAME :: CHECK HOW LOVABLE AND EMERGENT HANDLE THIS SMOOTHLY" -> research -> "GO" on
points 1 + 2).

ROOT CAUSE, held here: even after v0.709-v0.712 made the plan the site's structure, the site was still BUILT from a
marketing-only section library (hero / services / pricing / reviews) and the three looks showed only the home top (a
"strong distinct hero" + two sections). So a school portal's preview was a landing page whatever the plan said. Lovable /
Emergent start from the app's real screens, filled with mock data, and show THOSE.

1. App-screen building blocks: nine screen types (dashboard, data table, form, record detail, board, calendar, approvals,
   sign-in, settings) the architect plans with and the section writer draws as real working screens with marked samples.
2. Screens first: a system's plan names its MAIN SCREEN, the home is a compact front door + that screen, and the three
   looks show it (screens before any marketing section); sample rows never go live (the launch check counts them)."""
import json

from tests.test_v0709_plan_shape import PORTAL, deep_env  # noqa: F401
from tests.test_v0407_ek_dimaag import SCHOOL_LOGIC, SCHOOL_SPEC, T, arch_env  # noqa: F401
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401


def test_the_app_screen_types_exist_beside_the_marketing_library():
    from app.site import library as L
    from app.site import sitemap as SM
    from app.site import taxonomy as TX
    assert set(TX.SCREENS) == {"screen_dashboard", "screen_table", "screen_form", "screen_detail", "screen_board",
                               "screen_calendar", "screen_approvals", "screen_signin", "screen_settings"}
    assert all(TX.is_section(k) and TX.is_screen(k) and TX.SECTIONS[k]["variants"] for k in TX.SCREENS)
    assert not TX.is_screen("hero") and TX.label_of("screen_approvals") == "Approvals queue"
    assert TX.check() == [] and L.counts()["section_designs"] == 300          # the marketing library is unchanged
    lines = SM.section_lines()
    assert "APP SCREENS" in lines and "screen_dashboard (Dashboard)" in lines
    assert lines.index("APP SCREENS") > lines.index("hero (Hero)")           # listed apart, never mixed with marketing


def test_the_architect_plans_screens_and_names_a_main_screen():
    from app.site import architect as AR
    sysp = AR._system()
    assert "SCREENS FIRST" in sysp and "main_screen" in sysp and "screen_table" in sysp
    raw = json.loads(json.dumps(PORTAL))
    sp = AR.clean(raw, "school portal")
    assert sp["main_screen"] == "mark-attendance"                            # her architect's pick, a page with screens
    raw["main_screen"] = "not-a-page"
    assert AR.clean(raw, "school portal")["main_screen"] == "mark-attendance"   # a wrong pick falls back to a real one
    raw["kind"] = "brochure"
    assert AR.clean(raw, "bakery site")["main_screen"] == ""                 # only systems have one
    thin = json.loads(json.dumps(PORTAL))
    for p in thin["pages"]:
        p["sections"] = [x for x in p["sections"] if not str(x.get("type", "")).startswith("screen_")]
    tsp = AR.clean(thin, "school portal")
    assert tsp["main_screen"] == "" and ("a main screen built from app screens", False) in AR.checks(tsp)


def test_a_systems_home_is_a_front_door_plus_its_main_screen():
    from app.site import architect as AR
    sp = AR.clean(json.loads(json.dumps(PORTAL)), "school portal")
    plan = AR.site_plan(sp, {}, {"pages": [], "cta": "call"})
    home = plan["pages"][0]
    types = [x["type"] for x in home["sections"]]
    assert types[:2] == ["hero", "screen_table"] and home.get("main_screen")
    assert AR.APP_FRONT_DOOR in home["sections"][0]["design"] and "NOT a marketing hero" in home["sections"][0]["design"]
    assert plan["spec"]["main_screen"] == "mark-attendance" and plan["spec"]["main_title"] == "Mark attendance"
    none = json.loads(json.dumps(PORTAL))                                     # a system with no screen at all: a dashboard
    for p in none["pages"]:
        p["sections"] = [x for x in p["sections"] if not str(x.get("type", "")).startswith("screen_")]
    hp = AR.site_plan(AR.clean(none, "school portal"), {}, {"pages": [], "cta": "call"})["pages"][0]
    assert [x["type"] for x in hp["sections"]][:2] == ["hero", "screen_dashboard"]
    br = json.loads(json.dumps(PORTAL))                                       # a brochure keeps its own home as planned
    br["kind"] = "brochure"
    bp = AR.site_plan(AR.clean(br, "school site"), {}, {"pages": [], "cta": "call"})["pages"][0]
    assert [x["type"] for x in bp["sections"]][1] == "custom_quick_actions" and not bp.get("main_screen")


def test_the_looks_show_the_main_screen_and_the_writer_draws_a_real_screen(deep_env, monkeypatch):
    from fastapi.testclient import TestClient
    from app.site import ai as AI
    from app.site import service as S
    seen = []
    real = AI.ask_json

    def spy(system, prompt, max_tokens=6000, kind="build"):
        seen.append(prompt)
        return real(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", spy)
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    card = c.post("/api/site-architect", json={"words": "hamare school ka portal - admission, fees, attendance, notices"}).json()
    got = c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": card["hash"]}).json()
    r = S._load(got["site"])
    assert S.is_app_plan(json.loads(r.plan))
    assert [s["type"] for s in S._look_sections(r)] == ["screen_table"]       # SITE_LOOK_SECTIONS=1 still shows the screen
    assert any(AI.APP_LOOK_NOTE[:60] in p for p in seen)                      # the look's top is an app front door
    assert not any(AI.HERO_LOOK_NOTE[:60] in p for p in seen)
    scr = [p for p in seen if 'data-hoola-screen="screen_table"' in p]
    assert scr and "Sample data" in scr[0] and "no <form> element" in scr[0]  # the screen is drawn as a real app screen
    from app.site import build as B
    assert (B.site_dir(r.tenant_id, r.id) / "looks" / "0" / "home__screen_table.json").exists()
    home = json.loads(r.plan)["pages"][0]
    mk = S._section_prompt(r, "admissions", {"type": "process_steps", "design": "steps"}, [])
    assert "APP SCREEN (v0.714)" not in mk and "APP SCREEN (v0.714)" in S._section_prompt(r, "home", home["sections"][1], [])


def test_sample_data_never_goes_live_and_the_studio_marks_the_main_screen(env):
    from types import SimpleNamespace
    from app.site import checks as C
    from app.site import hosting as H
    import inspect
    assert "[data-sample]" in inspect.getsource(C)
    r = SimpleNamespace(checks=json.dumps({"blocking": [], "scores": {"samples": 2}}), status="ready", version=3)
    assert any("sample data" in x for x in H.blockers(r))
    r.checks = json.dumps({"blocking": [], "scores": {}})
    assert H.blockers(r) == []
    js = open(__import__("pathlib").Path(__file__).parents[1] / "app/static/console/webstudio.js", encoding="utf-8").read()
    assert "pill('Main screen', 'ok')" in js


def test_a_crashing_plan_never_kills_the_build_tap(site_env, monkeypatch):
    from app.site import architect as AR
    from app.site import service as S

    def boom(*a, **k):
        raise RuntimeError("model door exploded")
    monkeypatch.setattr(AR, "draft", boom)
    v = AR.build_now(T, "Sharma Sweets mithai dukaan ki website")
    assert v["say"].startswith("Gehra plan abhi nahi bana") and S._load(v["id"]) is not None
