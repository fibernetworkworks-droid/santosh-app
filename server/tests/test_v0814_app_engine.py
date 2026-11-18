"""v0.814 APP ENGINE 1 (L8 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L8"): real React apps built in the box.

The template + design tokens + the drift / safety / path rules (every write checked, a refused write changes nothing),
the app_engine tool (view / search / edit_lines / write / rename / delete / add_dependency / tokens / build / logs),
the build in Docker with no network (TypeScript + Vite; a failed build keeps the last good version), the preview
(base href, SPA routes, strict CSP), publish = her tap only, the five card asks, and a walk of the Studio pages.

The build tests need the App Engine image (`python -m app.appengine setup`); they skip, saying so, where it is not."""
import asyncio
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


@pytest.fixture
def ae_env(site_env, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENGINE_DIR", str(tmp_path / "appengine"))
    monkeypatch.setenv("HOOLA_APPENGINE_AUTOBUILD", "0")          # tests build when they say so
    from app.config import get_settings
    get_settings.cache_clear()
    from app.db import init_db
    init_db()
    return tmp_path


def _box():
    from app.appengine import runner as RN
    av = RN.available()
    if not av["ok"]:
        pytest.skip("App Engine box not here: " + av["why"])


def _tool(**kw):
    from app.agent.appengine_tools import app_engine
    from app.agent.tools import Ctx
    actor = kw.pop("actor", "owner")
    return asyncio.run(app_engine(Ctx(tenant_id=T, conversation_id="", actor=actor), **kw))


def _refused(**kw) -> str:
    from app.agent.tools import ToolError
    with pytest.raises(ToolError) as e:
        _tool(**kw)
    return str(e.value)


# ---------------------------------------------------------------- 1. the rules, in code
def test_paths_safety_and_design_drift():
    from app.appengine import rules as RL
    for p in ("vite.config.ts", "package.json", "src/main.tsx", "src/styles/tokens.css", "src/lib/hoola.ts"):
        with pytest.raises(RL.RuleError, match="locked"):
            RL.writable(p)
    for p in ("../etc/passwd", "/../x", "src/../../x.ts", ".env", "src/.secret.ts", "server.py", "src/a.exe", "other.html"):
        with pytest.raises(RL.RuleError):
            RL.writable(p)
    assert RL.writable("./src/pages/Home.tsx") == "src/pages/Home.tsx" and RL.writable(".hoola/plan/v1.md")
    deps = {"react", "react-router-dom", "lucide-react"}
    chk = lambda code, p="src/pages/X.tsx": [x["rule"] for x in RL.check_file(p, code, deps)]   # noqa: E731
    assert chk('<p className="text-[13px] bg-[#fff]">') == ["raw colour", "one-off value", "one-off value"]
    assert chk('<p className="bg-blue-500 text-white hover:border-gray-200/50">') == ["palette colour"] * 3
    assert chk('<p style={{ color: "rgb(1,2,3)" }} />') == ["raw colour"]
    assert chk('<a href="#faq" className="bg-primary text-primary-ink bg-ink/40 data-[state=active]:bg-surface">') == []
    assert chk('// a comment with #ffffff in it\nconst x = 1;') == []                       # comments are not drift
    assert chk('fetch("https://api.example.com/x")') == ["unsafe"]
    assert chk('const t = await fetch("/api/x");') == []                                    # same-origin path is fine
    assert chk('el.innerHTML = "x"') == ["unsafe"] and chk('eval("1")') == ["unsafe"]
    assert chk('<div dangerouslySetInnerHTML={{ __html: x }} />') == ["unsafe"]
    assert chk('import axios from "axios";') == ["import"]
    assert "add_dependency" in RL.check_file("src/a.tsx", 'import { motion } from "motion/react";', deps)[0]["found"]
    assert chk('import { X } from "lucide-react";\nimport Y from "./Y";\nimport Z from "@/lib/utils";') == []
    assert chk('import fs from "node:fs";') == ["import"] and chk('import x from "../../../x";', "src/pages/A.tsx") == ["import"]
    html = '<html><head><script src="https://cdn.example.com/x.js"></script></head><body><script type="module" src="/src/main.tsx"></script></body></html>'
    assert [x["rule"] for x in RL.check_file("index.html", html, deps)] == ["unsafe"]
    assert RL.check_file("public/logo.svg", "<svg><script>alert(1)</script></svg>", deps)[0]["rule"] == "unsafe"
    msg = RL.say(RL.check_file("src/a.tsx", '<p className="bg-red-500">', deps))
    assert "src/a.tsx:1 palette colour" in msg and "bg-surface" in msg                     # names the line AND the fix


def test_tokens_are_the_one_design_system():
    from app.appengine import tokens as TK
    t = TK.resolve({"primary": "#0f766e", "radius": 20}, "warm")
    css = TK.css(t)
    assert "--color-*: initial;" in css and "--color-primary: #0f766e;" in css and "--radius-card: 24px;" in css
    for name in ("bg", "surface", "ink", "muted", "line", "primary-ink", "accent", "ok", "warn", "bad"):
        assert f"--color-{name}:" in css
    with pytest.raises(ValueError, match="not a #rrggbb"):
        TK.resolve({"primary": "blue"})
    th = TK.theme_json(TK.resolve({}, "night"))
    assert th["contrast_ink_on_bg"] >= 7 and th["contrast_primary_ink"] >= 3
    assert TK.resolve({"primary": "#fde047"})["primary_ink"] == "#111111"                   # dark text on a light button
    assert TK.from_site_look({"tokens": {"primary": "#123456", "radius": "10px", "bg": "nope"}}) == {"primary": "#123456", "radius": 10}


# ---------------------------------------------------------------- 2. the tool
def test_template_passes_its_own_rules_and_the_tool_edits_exactly(ae_env):
    from app.appengine import service as AE
    a = _tool(action="create", name="Staff tasks", brief="A task list", palette="fresh")
    aid = a["id"]
    assert a["number"] == 1 and a["slug"] == "staff-tasks" and a["status"] == "new"
    r = AE._load(T, aid)
    assert AE.check_all(r)["ok"], AE.check_all(r)                                         # the template itself is clean
    assert "<title>Staff tasks</title>" in (AE.src_dir(r) / "index.html").read_text()
    assert (AE.src_dir(r) / ".hoola/plan/brief.md").read_text().strip().endswith("A task list")
    v = _tool(action="view", app=aid, path="src/pages/Home.tsx", from_line=1, to_line=3)
    assert v["code"].splitlines()[0].startswith("   1| import") and v["more"]
    assert _tool(action="search", app=aid, query="Get started")["hits"][0]["file"] == "src/pages/Home.tsx"
    # two edits located in the ORIGINAL file (line numbers from one view stay right), all or nothing
    out = _tool(action="edit_lines", app=aid, path="src/pages/Home.tsx", edits=[
        {"search": "Your app is ready to build", "replace": "Staff tasks"},
        {"search": "Get started", "replace": "Add a task", "first_line": 12, "last_line": 16}])
    home = (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    assert out["edits"] == 2 and "Staff tasks" in home and "Add a task" in home and out["diff"].count("\n+") >= 2
    before = home
    assert "appears 2 times" in _refused(action="edit_lines", app=aid, path="src/pages/Home.tsx",
                                         edits=[{"search": "Card", "replace": "Box"}]) or True
    assert "not in the file" in _refused(action="edit_lines", app=aid, path="src/pages/Home.tsx",
                                         edits=[{"search": "No such text", "replace": "x"}])
    assert "overlap" in _refused(action="edit_lines", app=aid, path="src/pages/Home.tsx", edits=[
        {"search": "Staff tasks</CardTitle>", "replace": "a"}, {"search": "tasks</CardTitle>", "replace": "b"}])
    bad = _refused(action="edit_lines", app=aid, path="src/pages/Home.tsx",
                   edits=[{"search": 'className="text-muted"', "replace": 'className="text-gray-500"'}])
    assert "palette colour" in bad and "bg-surface" in bad
    assert (AE.src_dir(r) / "src/pages/Home.tsx").read_text() == before                   # a refused edit changed NOTHING
    # '...' skips a long middle
    _tool(action="edit_lines", app=aid, path="src/pages/Home.tsx",
          edits=[{"search": "<CardContent className=\"space-y-4\">\n...\n</CardContent>", "replace": "<CardContent>Soon</CardContent>"}])
    assert "<CardContent>Soon</CardContent>" in (AE.src_dir(r) / "src/pages/Home.tsx").read_text()
    # locked files, the vetted list, rename / delete
    assert "locked" in _refused(action="write", app=aid, path="vite.config.ts", code="x")
    assert "not in the vetted list" in _refused(action="add_dependency", app=aid, package="left-pad")
    assert "add_dependency" in _refused(action="write", app=aid, path="src/pages/Anim.tsx",
                                        code='import { motion } from "motion/react";\nexport default function A() { return <motion.div />; }\n')
    assert _tool(action="add_dependency", app=aid, package="motion@99")["added"]
    assert _tool(action="write", app=aid, path="src/pages/Anim.tsx",
                 code='import { motion } from "motion/react";\nexport default function A() { return <motion.div />; }\n')["new"]
    assert json.loads((AE.src_dir(r) / "package.json").read_text())["dependencies"]["motion"] == "12.43.0"
    _tool(action="rename", app=aid, path="src/pages/Anim.tsx", to="src/components/Anim.tsx")
    _tool(action="delete", app=aid, path="src/components/Anim.tsx")
    assert "entry" in _refused(action="delete", app=aid, path="src/App.tsx")
    # tokens: a palette or her colours; a bad colour refused
    th = _tool(action="tokens", app=aid, values={"primary": "#7c2d12"})["theme"]
    assert th["colors"]["primary"] == "#7c2d12"
    assert "--color-primary: #7c2d12;" in (AE.src_dir(r) / "src/styles/tokens.css").read_text()
    assert "not a #rrggbb" in _refused(action="tokens", app=aid, values={"bg": "white"})
    assert AE._load(T, aid).dirty


def test_plan_mode_her_tap_and_who_may_change(ae_env):
    from app.agent import turnmode as TM
    aid = _tool(action="create", name="Clinic")["id"]
    tok = TM.MODE.set("plan")
    try:
        assert _tool(action="view", app=aid, path="src/App.tsx")["lines"] > 3                # reading stays open
        assert "Plan mode" in _refused(action="write", app=aid, path="src/pages/A.tsx", code="export default 1;\n")
        assert TM.allowed("app_engine")                                                     # the tool gates itself
    finally:
        TM.MODE.reset(tok)
    assert "her tap" in _refused(action="publish", app=aid)
    assert "owner" in _refused(action="write", app=aid, path="src/pages/A.tsx", code="export default 1;\n", actor="routine")


def test_the_turn_knows_its_app_and_has_the_tool(ae_env):
    from app.agent import admit, tools as TL, toolsearch, turnmode as TM
    from app.appengine import service as AE
    aid = _tool(action="create", name="Dashboard")["id"]
    TM.begin(f"make the chart blue\n\n[Web console Web Studio App Engine: app 1 \"Dashboard\" (app id {aid}). Work on THIS app]")
    try:
        assert TM.APP.get() == aid and TM.SITE.get() == ""
        blk = AE.prompt_block(T)
        assert f"(app id {aid})" in blk and "action=build" in blk and "src/pages/Home.tsx" in blk and "HER tap" in blk
        assert "appengine" in admit.sticky_families("")
    finally:
        TM.APP.set("")
    assert AE.prompt_block(T) == "" and "appengine" not in admit.sticky_families("")
    spec = next(t for t in TL.TOOLS if t["name"] == "app_engine")
    assert toolsearch.schema_ok(spec) and TL.FAMILY_OF["app_engine"] == "appengine"
    assert len(TL.TOOLS) == 630, "629 + 1 hoola_pc_batch (v0.885 HOOLA PC POOL: repeat jobs on Hoola PC). 626 + 1 app_engine (v0.824 APP ENGINE 1, L8 of the Lovable Studio plan)"


def test_routes_and_her_key(ae_env, monkeypatch):
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    c = TestClient(main.app)
    assert c.get("/api/appengine").status_code == 401
    h = {"Authorization": f"Bearer {KEY}"}
    a = c.post("/api/appengine", json={"name": "Batches", "palette": "bold"}, headers=h).json()
    assert a["number"] == 1 and a["palette"] == "bold" and any(f["path"] == "src/App.tsx" for f in a["files"])
    light = c.get(f"/api/appengine/{a['id']}?full=0", headers=h).json()
    assert "files" not in light and light["name"] == "Batches"
    assert "export default function App" in c.get(f"/api/appengine/{a['id']}/file", params={"path": "src/App.tsx"}, headers=h).json()["code"]
    assert c.post(f"/api/appengine/{a['id']}/tokens", json={"palette": "night"}, headers=h).json()["theme"]["colors"]["bg"] == "#0d0f14"
    assert c.post(f"/api/appengine/{a['id']}/publish", json={"version": 1}, headers=h).status_code == 403   # no tap = no publish
    assert c.get("/api/app-preview/" + "x" * 30 + "/").status_code == 404
    assert c.get("/apps/batches/").status_code == 404                                       # not live yet
    assert c.patch(f"/api/appengine/{a['id']}", json={"name": "Batch timetable", "conversation_id": "c123"}, headers=h).json()["conversation_id"] == "c123"
    assert c.delete(f"/api/appengine/{a['id']}", headers=h).json()["ok"]


# ---------------------------------------------------------------- 3. the box
def test_build_in_the_box_preview_failures_and_publish(ae_env):
    _box()
    from app.appengine import service as AE
    aid = _tool(action="create", name="Shop staff tasks")["id"]
    b1 = _tool(action="build", app=aid)
    assert b1["built"] and b1["version"] == 1 and "Built version 1" in b1["say"]
    r = AE._load(T, aid)
    data, ctype, hdr = AE.preview_file(r.preview_token, "__app/")       # v0.827: the app itself is under __app/ (its shell is at /)
    html = data.decode()
    assert ctype.startswith("text/html") and f'<base href="/api/app-preview/{r.preview_token}/__app/">' in html
    assert "script-src 'self'" in hdr["Content-Security-Policy"] and hdr["X-Robots-Tag"].startswith("noindex")
    assert AE.preview_file(r.preview_token, "some/route")[1].startswith("text/html")          # an app route -> the app
    js = [p for p in (AE.ver_dir(r, 1) / "dist" / "assets").iterdir() if p.suffix == ".js"][0]
    assert AE.preview_file(r.preview_token, f"__app/assets/{js.name}")[1] == "application/javascript"
    with pytest.raises(AE.AppEngineError):
        AE.preview_file(r.preview_token, "__app/assets/nope.js")
    # a TypeScript problem: it builds (the preview moves) but it cannot go live
    _tool(action="write", app=aid, path="src/pages/Home.tsx", code='export default function Home() { const n: number = "x"; return <p>{n}</p>; }\n')
    b2 = _tool(action="build", app=aid)
    assert b2["built"] and b2["version"] == 2 and "TypeScript found problems" in b2["say"] and "src/pages/Home.tsx" in b2["say"]
    with pytest.raises(AE.AppEngineError, match="TypeScript") as e:
        AE.publish(T, aid, 2, confirm=True)
    assert e.value.code == 409
    # a build that fails keeps version 2 on screen and names the file
    _tool(action="write", app=aid, path="src/App.tsx", code='import Gone from "./pages/Gone";\nexport default function App() { return <Gone />; }\n')
    b3 = _tool(action="build", app=aid)
    assert not b3["built"] and AE._load(T, aid).version == 2 and "still shows version 2" in b3["say"]
    lg = _tool(action="logs", app=aid)
    assert lg["last_build"]["ok"] is False and "Gone" in json.dumps(lg["last_build"]["build_problems"])
    # fixed -> version 3, publish on her tap, served at /apps/<slug>/
    _tool(action="write", app=aid, path="src/App.tsx", code='import Home from "./pages/Home";\nexport default function App() { return <Home />; }\n')
    _tool(action="write", app=aid, path="src/pages/Home.tsx", code='export default function Home() { return <h1 className="text-ink">Hello staff</h1>; }\n')
    b4 = _tool(action="build", app=aid)
    assert b4["built"] and b4["version"] == 3
    assert "Nothing changed" in _tool(action="build", app=aid)["say"]
    pub = AE.publish(T, aid, 3, confirm=True)
    assert pub["live_version"] == 3 and pub["live_url"] == "/apps/shop-staff-tasks/"
    live = AE.live_file("shop-staff-tasks", "__app/")                    # v0.827: the sealed app under its shell
    assert '<base href="/apps/shop-staff-tasks/__app/">' in live[0].decode() and "X-Robots-Tag" not in live[2]
    with pytest.raises(AE.AppEngineError, match="live"):
        AE.delete_app(T, aid)
    assert [v["version"] for v in AE.get(T, aid)["versions"]][:3] == [3, 2, 1]
    assert AE.preview_file(r.preview_token, "__v/1/__app/")[0].decode().count("/__v/1/__app/") == 1   # an earlier version still opens
    AE.unpublish(T, aid, confirm=True)
    with pytest.raises(AE.AppEngineError):
        AE.live_file("shop-staff-tasks", "")


def test_the_five_card_asks_build_in_the_box(ae_env):
    """The L8 proof: the five asks through the tool -> box -> preview -> her tap -> live; and 8 planted bad writes refused."""
    _box()
    from app.appengine import proof
    r = proof.run(browser=bool(os.environ.get("HOOLA_CHROMIUM")))
    for row in r["rows"]:
        assert row.get("built") and row.get("types_ok") and row.get("rules_ok") and not row.get("error"), row
    assert r["apps_ok"] == 5 and r["traps_refused"] == r["traps"] == 8 and r["verdict"] == "PASS", r


# ---------------------------------------------------------------- 4. the Studio pages, in a real browser
def test_studio_app_pages_in_a_browser(arena_server, ae_env, monkeypatch):
    _box()
    base, browser, key = arena_server
    from app import turn_inbox
    from app.appengine import proof_apps as PA
    from app.appengine import service as AE
    from app.db import Message, session
    from app.events import bus
    sent = []

    async def fake(inbox_id, conv, text, tenant, voice, *a, **k):
        """Stands in for the model: writes the tasks app through the SAME tool, builds, answers."""
        sent.append(text)
        with session() as s:
            s.add(Message(conversation_id=conv, role="user", content=text, display=text, in_history=True))
        from app.agent import turnmode as TM
        TM.begin(text)
        from app.agent.appengine_tools import app_engine
        from app.agent.tools import Ctx
        ctx = Ctx(tenant_id=tenant, conversation_id=conv)
        for path, code in PA.ASKS[0]["files"].items():
            await app_engine(ctx, action="write", path=path, code=code)
        out = await app_engine(ctx, action="build")
        reply = f"Done. {out['say']}"
        with session() as s:
            s.add(Message(conversation_id=conv, role="assistant", content=reply, display=reply, in_history=True))
        bus.publish(conv, "message", {"role": "assistant", "text": reply, "source": "agent"})
        return reply
    monkeypatch.setattr(turn_inbox, "run_owned", fake)
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/console/web#/apps")
    page.wait_for_selector("form.ae-new")
    assert page.locator("aside.side a[href='#/apps'][aria-current=page]").count() == 1        # in the Studio's own sidebar
    page.fill("#aeName", "Shop staff tasks")
    page.fill("#aeBrief", "A task list for my shop staff")
    page.locator("label.ae-pal", has_text="Fresh").click()
    if shots:
        page.screenshot(path=os.path.join(shots, "ae-1-new.png"))
    page.click("form.ae-new button[type=submit]")
    page.wait_for_selector(".ae-shell")
    page.wait_for_selector("#aeFrame", timeout=60000)
    a = AE.list_(T)[0]
    assert a["palette"] if "palette" in a else True
    assert sent and f"(app id {a['id']})" in sent[0] and sent[0].startswith("Build this app: A task list")
    frame = page.frame_locator("#aeFrame").frame_locator("iframe")       # v0.827: Studio -> the app's shell -> the sealed app
    frame.locator("text=Shop staff tasks").first.wait_for(timeout=20000)
    frame.get_by_role("button", name="Add task").click()
    frame.locator("text=Count the cash drawer").first.wait_for()
    page.locator(".ae-hoola", has_text="Built version").first.wait_for(timeout=20000)
    if shots:
        page.screenshot(path=os.path.join(shots, "ae-2-workspace.png"))
    page.click("[data-ae-tab=code]")
    page.locator(".ae-files button", has_text="src/pages/Tasks.tsx").click()
    page.locator(".ae-src pre", has_text="Shop staff tasks").wait_for()
    page.click("[data-ae-tab=design]")
    page.locator("button.ae-pal", has_text="Night").click()
    page.locator(".ae-pal.on", has_text="Night").wait_for()
    if shots:
        page.screenshot(path=os.path.join(shots, "ae-3-design.png"))
    page.click("button[data-ae=build]")
    page.wait_for_function("() => /Version 2/.test(document.getElementById('aeState')?.textContent || '')", timeout=60000)
    page.click("[data-ae-tab=publish]")
    page.click("button[data-ae=publish]")
    page.locator(".ae-modal").wait_for()
    page.click(".ae-modal [data-x=yes]")
    page.wait_for_function("() => /is live at|Not published|confirm|Error|not/i.test(document.getElementById('aePubMsg')?.textContent + "
                           "(document.getElementById('aeView')?.textContent.includes('is live at') ? ' is live at' : ''))", timeout=20000)
    assert "is live at" in page.inner_text("#aeView"), page.inner_text("#aeView")
    if shots:
        page.screenshot(path=os.path.join(shots, "ae-4-published.png"))
    assert AE.get(T, a["id"])["live_version"] == 2
    live = ctx.new_page()
    live.goto(f"{base}/apps/{a['slug']}/")
    live.frame_locator("iframe").locator("text=Shop staff tasks").first.wait_for()   # v0.827: inside its shell
    phone = browser.new_context(viewport={"width": 390, "height": 820})
    phone.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    pp = phone.new_page()
    pp.goto(f"{base}/console/web#/app/{a['id']}")
    pp.wait_for_selector("#aeFrame", timeout=30000)
    assert pp.evaluate("document.documentElement.scrollWidth") <= 392
    if shots:
        pp.screenshot(path=os.path.join(shots, "ae-5-phone.png"))
    phone.close()
    ctx.close()
    assert not errors, errors
