"""v0.708 PLAN KA DHAANCHA (owner: "any simple / complex / hard web development work - Hoola just creates a random plan...
the plan must go deep with all aspects... BIG issue: the plan is a different structure and Hoola shows a preview of a
landing marketing page for any plan - go deep, find the root cause and fix this perfectly").

ROOT CAUSE, held here:
1. approve() flattened the spec into one line of page titles and S.new() built the LIBRARY's page set for the business
   type (home / about / services / contact with a marketing home + the library's marketing hero). The spec's pages and
   their purpose were thrown away, so every plan - a school portal, a clinic system - looked like the same landing page.
   Now the approved plan IS the site's structure (pages + sections in order, the logged-in screens in the app area) and
   every writer + the three looks read THE PLAN instead of the library's generic page list.
2. The architect was a 6,000-token single shot with no idea of size and no section design: a thin list of titles. Now
   code sizes the ask (simple / standard / complex), the architect designs every page section by section plus journeys,
   quality, launch phases and risks, code checks the depth against the size, and a thin plan goes back ONCE with its
   gaps named.
3. Build mode with a system ask ("school portal with fees + attendance") also took the library's marketing set; it now
   gets the same deep plan, built at once on her Build tap."""
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v0407_ek_dimaag import SCHOOL_LOGIC, SCHOOL_SPEC, T, arch_env  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

PORTAL = {
    "name": "Gyan Vidya Mandir", "summary": "School ka portal: admission, fees, attendance, notices.", "field_hint": "school",
    "kind": "portal", "complexity": "standard", "goal": "enquiry",
    "roles": [{"key": "parent", "label": "Parent", "can": "admission form bhare, apne bachche ki fees aur attendance dekhe"},
              {"key": "teacher", "label": "Teacher", "can": "attendance bhare, notice daale"}],
    "pages": [
        {"slug": "home", "title": "Home", "purpose": "portal ka darwaza", "for": "public",
         "sections": [{"type": "hero", "design": "PORTAL FRONT DOOR: school name, sign in for parents and teachers"},
                      {"type": "custom", "name": "Quick actions", "design": "Apply for admission, Pay fees, See attendance"},
                      {"type": "custom", "name": "Notice board", "design": "latest notices from the notices list"},
                      {"type": "contact_block", "design": "office phone + timings"}]},
        {"slug": "admissions", "title": "Admissions", "purpose": "online admission form", "for": "public",
         "sections": [{"type": "hero"}, {"type": "process_steps", "design": "4 steps from form to seat"},
                      {"type": "custom", "name": "Admission form", "design": "the admissions list form"}]},
        {"slug": "fee-structure", "title": "Fee structure", "purpose": "class-wise fees", "for": "public",
         "sections": [{"type": "hero"}, {"type": "pricing_table", "design": "class-wise fee table, values from her"}]},
        {"slug": "contact", "title": "Contact", "purpose": "pata, phone", "for": "public",
         "sections": [{"type": "hero"}, {"type": "contact_block", "design": "office phone"}, {"type": "map_hours"}]},
        {"slug": "my-child", "title": "My child", "purpose": "fees + attendance of her child", "for": "member",
         "sections": [{"type": "custom", "name": "Fee status", "design": "paid / due rows"}]},
        {"slug": "mark-attendance", "title": "Mark attendance", "purpose": "teacher marks the class", "for": "staff",
         "sections": [{"type": "custom", "name": "Class register", "design": "today's class list with present / absent"}]}],
    "flows": [{"name": "Online admission", "who": "Parent", "steps": ["opens Admissions", "fills the form", "office reviews", "parent sees the decision"]},
              {"name": "Daily attendance", "who": "Teacher", "steps": ["signs in", "opens Mark attendance", "marks the class", "parents see it"]}],
    "features": {"shop": False, "blog": False, "booking": False, "languages": ["hi"]},
    "stories": [{"who": "Parent", "want": "apply online", "so": "no visit"}, {"who": "Parent", "want": "see fees due", "so": "pay on time"},
                {"who": "Parent", "want": "see attendance", "so": "know"}, {"who": "Teacher", "want": "mark attendance", "so": "fast"},
                {"who": "Teacher", "want": "post a notice", "so": "parents know"}, {"who": "Admin", "want": "approve admissions", "so": "control"}],
    "payments": {"mode": "record", "what": "fees paid at the office"},
    "notifications": [{"when": "admission approved", "who": "row_owner", "how": "in_app"}],
    "integrations": [],
    "app_words": "students: name, class\nadmissions: child name, class, status Asked/Approved\nattendance: student, date, present\n"
                 "fees: student, month, amount, paid\nnotices: title, text\nparents read only their own child's rows",
    "quality": {"security": ["parents see only their own child"], "privacy": ["phone numbers visible to staff only"],
                "performance": ["pages under 100 KB"], "seo": ["school admission <city>"], "accessibility": ["WCAG AA"]},
    "phases": [{"name": "Launch", "includes": ["admissions", "notices"]}, {"name": "Next", "includes": ["fees online"]}],
    "risks": [{"risk": "parents forget the password", "plan": "phone OTP sign-in"}],
    "assumptions": ["one branch"], "content_needed": ["fee table", "school photos"], "page_count": 4, "questions": []}


@pytest.fixture
def deep_env(site_env, monkeypatch):
    from app.appmaker import ai as AAI
    from app.site import ai as AI
    from app.site import architect as AR
    calls = []

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(AR.ARCH_SYSTEM[:40]):
            calls.append({"system": system, "prompt": prompt, "max_tokens": max_tokens, "kind": kind})
            return json.loads(json.dumps(PORTAL))
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    monkeypatch.setattr(AAI, "ask_json", lambda system, prompt, max_tokens=7000: json.loads(json.dumps(SCHOOL_LOGIC)))
    return calls


def test_size_is_decided_by_code():
    from app.site import architect as AR
    assert AR.size("mithai dukaan ki website") == "simple"
    assert AR.size("clinic ki website with appointment booking") == "standard"
    assert AR.size("school portal - admission, fees, attendance, marks, teacher login, parent dashboard") == "complex"
    assert AR.wants_plan("school ka portal - admission, fees, attendance") and AR.wants_plan("ek web app chahiye jisme staff login kare")
    assert not AR.wants_plan("mithai dukaan ki website") and not AR.wants_plan("ek sundar bakery website banao Pune mein")


def test_the_architect_designs_every_page_and_the_whole_system(deep_env):
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    card = c.post("/api/site-architect", json={"words": "hamare school ka portal - admission, fees, attendance, notices"}).json()
    call = deep_env[0]
    assert call["max_tokens"] >= 16000 and call["kind"] == "site_art"                       # was 6,000 on the light path
    assert "process_steps" in call["system"] and "NOT a marketing landing page" in call["system"]   # section types + the rule
    assert json.loads(call["prompt"])["size_by_code"] == "standard"
    mods = {m["key"]: m for m in card["modules"]}
    assert list(mods) == ["stories", "pages", "users", "flows", "data", "logic", "payments", "notifications", "integrations",
                          "features", "quality", "phases", "risks"]
    home = next(x for x in mods["pages"]["items"] if x["title"] == "Home")
    assert home["tags"][:3] == ["Hero", "Quick actions", "Notice board"] or home["tags"][1:3] == ["Quick actions", "Notice board"]
    assert any("Fee status" in x for x in next(x for x in mods["pages"]["items"] if x["title"] == "My child")["tags"])
    assert mods["flows"]["items"][0]["steps"][0] == "opens Admissions"
    assert any(x.startswith("Security:") for x in mods["quality"]["lines"]) and "Launch" in mods["phases"]["lines"][0]
    assert any(x.startswith("You give:") for x in mods["risks"]["lines"])
    assert all(m.get("required") for k, m in mods.items() if k in ("flows", "quality", "phases", "risks"))   # no switch to tap
    assert card["kind"] == "portal" and card["depth"]["total"] >= 10 and card["depth"]["passed"] == card["depth"]["total"]
    assert len(deep_env) == 1                                                                  # deep enough: no second round


def test_a_thin_plan_goes_back_once_with_its_gaps(site_env, monkeypatch):
    from app.appmaker import ai as AAI
    from app.site import ai as AI
    from app.site import architect as AR
    asks = []

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(AR.ARCH_SYSTEM[:40]):
            asks.append((system, json.loads(prompt)))
            return json.loads(json.dumps(SCHOOL_SPEC if len(asks) == 1 else PORTAL))
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    monkeypatch.setattr(AAI, "ask_json", lambda system, prompt, max_tokens=7000: json.loads(json.dumps(SCHOOL_LOGIC)))
    card = AR.draft(T, "hamare school ka portal - admission, fees, attendance, notices")
    assert len(asks) == 2 and AR.DEEPEN[:30] in asks[1][0]
    gaps = asks[1][1]["GAPS"]
    assert any("sections of page" in g for g in gaps) and any("journey" in g for g in gaps)
    assert asks[1][1]["plan"]["pages"]                                                       # the thin plan rides along
    assert card["depth"]["gaps"] == [] and any(m["key"] == "flows" and m["items"] for m in card["modules"])


def test_build_this_plan_builds_the_plans_own_structure(deep_env):
    from app.site import service as S
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    card = c.post("/api/site-architect", json={"words": "hamare school ka portal - admission, fees, attendance, notices"}).json()
    got = c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": card["hash"]}).json()
    r = S._load(got["site"])
    plan = json.loads(r.plan)
    slugs = [p["slug"] for p in plan["pages"]]
    assert slugs[:4] == ["home", "admissions", "fee-structure", "contact"]                   # the PLAN's pages, in order
    assert not {"about", "services", "gallery", "reviews"} & set(slugs)                      # not the library's marketing set
    home = plan["pages"][0]
    assert [x["type"] for x in home["sections"]][:2] == ["hero", "custom_quick_actions"] or \
        home["sections"][1]["label"] == "Quick actions"
    assert "PORTAL FRONT DOOR" in home["sections"][0]["design"]
    from app.site import architect as AR                                                     # a page with no sections: library fallback
    base = {"pages": [{"slug": "home", "sections": []}], "cta": "call"}
    fb = AR.site_plan({"pages": [{"slug": "home", "title": "Home", "for": "public", "sections": []},
                                 {"slug": "contact", "title": "Contact", "for": "public", "sections": []}]}, {}, base)
    assert [x["type"] for x in fb["pages"][1]["sections"]] == ["hero", "contact_block", "map_hours"]
    assert plan["spec"]["kind"] == "portal" and {x["title"] for x in plan["spec"]["app_pages"]} == {"My child", "Mark attendance"}
    assert r.status == "looks"
    # every writer reads THE PLAN, not the library's page list / home sections / marketing hero
    from app.site import library as L
    br = L.brief(r.field, r.goal, r.style)
    txt = S.brief_text(br, plan)
    assert "THE APPROVED PLAN" in txt and "NOT a marketing landing page" in txt and "Mark attendance" in txt
    assert not any(x.startswith(("Pages: home", "Home sections: ", "Hero: ")) for x in txt.split("\n"))
    p = S._section_prompt(r, "home", home["sections"][1], [])
    assert "THE APPROVED PLAN" in p and "INTERNAL LINKS" in p and "admissions/" in p
    assert S._home_hero(plan).startswith("PORTAL FRONT DOOR")
    from app.config import get_settings
    st = get_settings()
    old, st.site_look_sections = st.site_look_sections, 3
    try:
        assert [s["label"] for s in S._look_sections(r)][:1] == ["Quick actions"]           # the looks show the plan's top
    finally:
        st.site_look_sections = old


def test_build_mode_gives_a_system_ask_the_deep_plan(deep_env):
    from app.site import service as S
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    v = c.post("/api/sites", json={"brief": "hamare school ka portal - admission, fees, attendance, notices", "deep": True}).json()
    plan = json.loads(S._load(v["id"]).plan)
    assert plan["spec"]["kind"] == "portal" and [p["slug"] for p in plan["pages"]][:2] == ["home", "admissions"]
    assert v["status"] == "looks" and v["spec"]
    n = len(deep_env)
    b = c.post("/api/sites", json={"brief": "mithai dukaan ki website", "deep": True}).json()   # a brochure stays fast
    assert len(deep_env) == n and "spec" not in json.loads(S._load(b["id"]).plan)


def test_studio_draws_the_plan_as_a_document():
    from pathlib import Path
    D = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    ws = (D / "webstudio.js").read_text()
    assert "deep: true" in ws and "function modBody(m)" in ws and "function depthLine(c)" in ws
    assert "data-page" in ws and "data-flow" in ws and "architecture checks passed" in ws
    assert ".doc .pgs" in (D / "webstudio.css").read_text()


def test_the_plan_document_in_a_browser(deep_env, arena_server):
    base, browser, key = arena_server
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    res = c.post("/api/site-architect", json={"words": "hamare school ka portal - admission, fees, attendance, notices"},
                 headers={"Authorization": "Bearer " + key})
    assert res.status_code == 200, res.text
    card = res.json()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + f"/console/web#/plan/{card['id']}")
    pg.wait_for_selector(".doc [data-page]", timeout=20000)
    assert pg.locator(".doc [data-page]").count() == 6 and pg.locator(".doc [data-flow]").count() == 2
    doc = pg.inner_text(".doc")
    assert "Quick actions" in doc and "Mark attendance" in doc and "architecture checks passed" in doc
    assert "After sign-in" in doc and "Staff" in doc
    w = pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert w
    import os
    if os.environ.get("APP_SHOTS"):
        pg.screenshot(path=f"{os.environ['APP_SHOTS']}/plan-doc.png", full_page=False)
    ctx.close()
    assert not errs, errs
