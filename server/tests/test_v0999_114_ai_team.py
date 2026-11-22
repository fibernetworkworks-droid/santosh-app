"""v0.999.114 THE WHOLE AI TEAM IN THE CONSOLE (owner, 22 Nov: "FIRST CHECK THE APP SIDE HOW MANY AI EMPLOYEE IT HAS AND
ALSO SHOW ALL CATEGORY WISE IN CONSOLE --- SOME OF THEM ARE ALREADY IN WEB CONSOLE").

The phone's Your AI team list held 81 desks; 9 were already Hub employees under another name, the other 72 had no place in
the console. They now sit in the Hub by department and open on the desk room (forms read from their own tool) or their
own studio page; the phone opens the same employee on the screen it always had."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
EMP = (CON / "employees.js").read_text(encoding="utf-8")
DDK = (CON / "deptdesk.js").read_text(encoding="utf-8")
DART = (ROOT / "lib" / "ui" / "shell" / "hoola_employees.dart").read_text(encoding="utf-8")
TEAM_DART = (ROOT / "lib" / "ui" / "shell" / "hoola_team_list.dart").read_text(encoding="utf-8")
ALREADY = {"SeoScreen", "CallCentreScreen", "SevaScreen", "FilmdeskScreen", "ShikshaScreen", "GuruScreen",
           "DaftarScreen", "ShodhScreen", "PrayogScreen"}   # already Hub employees under another name


def _phone_desks():
    ents = re.findall(r'HoolaTeamEntry\("([^"]+)",\s*Icons\.\w+,\s*([\'"])(.*?)\2,\s*[\'"].*?[\'"],\s*\(a\) => (\w+)',
                      TEAM_DART, re.S)
    return [(g, t.replace("\\'", "'"), c) for g, _, t, c in ents if g not in ("Hire and manage", "Tools and apps")]


def test_the_phone_count_and_every_desk_has_a_place():
    from app.employee import hire as H, teamdesks as TD
    desks = _phone_desks()
    assert len(desks) == 81                                             # the phone's AI team, tools left out
    assert len([d for d in desks if d[2] not in ALREADY]) == len(TD.TEAM) == 72
    assert len(H.CATALOG) == 163                                        # + tax_worldwide (F4); 84 Hub employees + 72 + household_money (v0.999.129 F2) + books_accounts (v0.999.134 F3)
    for k, (name, group, pitch, does, _tail) in TD.TEAM.items():
        c = H.CATALOG[k]
        assert c["live"] and c["group"] == group and c["name"] == name and c["never"] and does, k
    from app.agent import tools as T
    assert all(k in T.HANDLERS for k in TD.TEAM)                        # each works through the tool it always had


def test_every_team_desk_opens_somewhere_real():
    from app.employee import deskroom as D, teamdesks as TD
    keys = set(D.keys())
    for k in TD.TEAM:
        if k in TD.DESK:
            assert TD.DESK[k] in ("webdev", "appdev", "code"), k        # the studios that are their own pages
            continue
        assert k in keys and D.tools_of(k)[0] == k, k
        for t in D.tools_of(k):
            assert D.spec(t)["actions"], t
    assert len(keys) == 106 and len(D.DEPTS) == 11                     # + tax_worldwide (F4); + household_money desk (v0.999.129 F2)


def test_categories_on_the_console():
    from app.employee import hire as H, teamdesks as TD
    groups = {c.get("group", "Business") for c in H.CATALOG.values()}
    for g in (TD.CARE_GROUP, TD.MOVE_GROUP, TD.LEGAL_GROUP, TD.HOSP_GROUP, "Construction & Real Estate",
              "Voice, Meetings & Transcription"):
        assert g in groups and f"{{g: '{g}'" in EMP, g                  # a named department card, not a plain one
    for i in ("biz", "care", "soft", "move", "legal", "hosp", "media"):
        assert f"    {i}: '<path" in DDK, i                             # the desk room's department icon
    assert ").desk || key + 'desk'" in EMP                             # Open desk uses the desk the server names


def test_hiring_gates_no_tool_and_the_desk_runs(env):
    from app.agent import tools as T
    from app.agent.tools import Ctx
    from app.main import app
    import asyncio
    # the tool still works with nobody hired (the EDU_OPEN law)
    out = asyncio.run(T.dispatch("chai_dekho", {"what": "today"}, Ctx(tenant_id="default", conversation_id="", actor="owner")))
    assert out is not None
    c = TestClient(app)
    emps = c.get("/api/employees").json()["employees"]
    row = next(e for e in emps if e["key"] == "shikayat")
    assert row["group"] == "Customer Service" and row["desk"] == "deptdesk" and row["status"] == "none"
    ov = c.get("/api/deskroom").json()
    assert ov["where"]["shikayat"] == "care" and ov["where"]["chai"] == "retail"
    d = c.get("/api/deskroom/care").json()
    assert [ln["id"] for ln in d["lanes"]] == ["care", "it"]
    r = c.post("/api/deskroom/chai/run", json={"tool": "chai_dekho", "action": "today"})
    assert r.status_code == 400 and "Hire" in r.json()["detail"]
    assert c.post("/api/employees/chai/hire", json={"trust": "seekh"}).status_code == 200
    r = c.post("/api/deskroom/chai/run", json={"tool": "chai_dekho", "action": "today"})
    assert r.status_code == 200, r.text


def test_the_phone_opens_the_screen_it_always_had():
    from app.employee import teamdesks as TD
    m = dict(re.findall(r"  '(\w+)': '((?:[^'\\]|\\.)*)',", DART.split("const Map<String, String> _teamTitle = {")[1].split("};")[0]))
    assert set(m) == set(TD.TEAM)
    titles = {t for _, t, _ in _phone_desks()}
    assert all(v.replace("\\'", "'") in titles for v in m.values())
    assert "native = t.open(staff.app);" in DART and "show hoolaTeamEntries" in DART
    for g in ("Customer Service", "Logistics, Travel & Trade", "Legal & Compliance", "Hospitality & Events"):
        assert f"(group: '{g}'" in DART, g


def _walk(browser, base, key, width, scheme):
    ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/")
    pg.wait_for_selector("#composer")
    pg.evaluate("document.querySelector('.sn[data-v=\"hire\"]')?.click()")
    pg.wait_for_selector("[data-ae=dept]")
    for i in ("care", "move", "legal", "hosp", "const"):
        assert pg.locator(f"[data-ae=dept][data-id={i}]").count() >= 1, i
    pg.locator("[data-ae=dept][data-id=care]").first.click()
    pg.locator("[data-ae=role][data-key=shikayat]").first.click()
    pg.locator("[data-ae=open][data-key=shikayat]").first.click()
    pg.wait_for_selector(".ddk-hero")
    assert pg.locator(".ddk-h1").text_content() == "Customer Service"
    assert pg.locator(".ddk-emp").count() == 6 and pg.locator(".ddk-dept").count() == 11
    assert pg.locator(".ddk-emp[aria-current=true] .ddk-empname").text_content().startswith("Complaints assistant")
    shots = __import__("os").environ.get("CONSOLE_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/team-care-{width}-{scheme}.png", full_page=True)
    pg.locator(".ddk-dept[data-id=hosp]").click()
    pg.wait_for_selector(".ddk-lane")
    assert pg.locator(".ddk-lane").count() == 3 and pg.locator(".ddk-emp").count() == 6
    assert pg.evaluate("document.querySelector('.ddk').scrollWidth <= document.querySelector('.ddk').clientWidth + 1")
    assert not errs, errs
    ctx.close()


def test_the_team_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    from app.employee import hire
    hire.hire("default", "shikayat", "seekh")
    _walk(browser, base, key, 1280, "light")
    _walk(browser, base, key, 390, "dark")
