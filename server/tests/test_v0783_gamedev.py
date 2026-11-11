"""v0.783 HOOLA GAME DEV (/console/games): game making as its own full-screen console app.

Two halves:
1. static / server - the page route and its headers, the HTML's load order, the console sidebar row, the employees.js
   gameEmbed entry point (run in node, not just grepped), and the app script's own rules (syntax, esc() on server
   values, every DOM hook the contract names, no key, no eval).
2. a REAL BROWSER WALK (Playwright Chromium) against a live uvicorn on a fresh database: the hire gate for a tenant
   without the Game Developer, then two seeded games (one waiting on its design, one done with a playable build and a
   long Studio project) walked through every route and every tab, at desktop width and at 390px. Any page error or
   console error on any step fails the walk. No model and no Godot is ever called: rows are inserted directly.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]
ROOT = SERVER.parent
CONSOLE = SERVER / "app" / "static" / "console"
HTML = CONSOLE / "gamedev.html"
JS = CONSOLE / "gamedev.js"
CSS = CONSOLE / "gamedev.css"
EMP = CONSOLE / "employees.js"
V2 = CONSOLE / "v2.js"

PROJECT_PAGES = ["board", "bible", "scenes", "assets", "qa", "release"]
ROLE_PAGES = ["liveops", "prov", "runtime", "world", "physics", "audio", "haptics", "net", "xr", "sim", "twin", "vfx",
              "arena", "big"]
TABS = ["design", "play", "board", "bible", "scenes", "assets", "qa", "release", "liveops", "prov", "crew"]
NAVS = ["home", "games", "crew", "arena", "big"]


def _js() -> str:
    assert JS.is_file(), "server/app/static/console/gamedev.js has not landed yet (the app's script)"
    return JS.read_text(encoding="utf-8")


# ================================================================ 1. static / server
def test_page_route_serves_the_html_with_the_console_headers(env):
    """/console/games and /console/games/ are the app, with exactly the strict headers /console/apps carries."""
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    ref = c.get("/console/apps")
    assert ref.status_code == 200
    for path in ("/console/games", "/console/games/"):
        r = c.get(path)
        assert r.status_code == 200, path
        assert r.headers["content-type"].startswith("text/html"), path
        assert 'id="gdv"' in r.text and "gamedev.js" in r.text
        for h in ("content-security-policy", "x-frame-options", "x-content-type-options", "permissions-policy",
                  "referrer-policy"):
            assert r.headers.get(h) == ref.headers.get(h), (path, h)
        assert r.headers["x-frame-options"] == "DENY"
        csp = r.headers["content-security-policy"]
        assert "script-src 'self';" in csp and "frame-ancestors 'none'" in csp and "unsafe-eval" not in csp


def test_html_load_order():
    """v2.css before gamedev.css (the embedded pages wear the console's classes, the shell overrides after);
    md.js + qrcode + employees.js before gamedev.js (gameEmbed must exist when the app boots); no inline script."""
    h = HTML.read_text(encoding="utf-8")
    links = re.findall(r'<link[^>]+href="([^"]+)"', h)
    css = [x for x in links if x.endswith(".css") or ".css?" in x]
    assert [i for i, x in enumerate(css) if "/v2.css" in x] < [i for i, x in enumerate(css) if "/gamedev.css" in x]
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', h)
    names = [re.sub(r"\?.*$", "", x).rsplit("/static/console/", 1)[-1] for x in scripts]
    order = [names.index(x) for x in ("md.js", "vendor/qrcode.js", "employees.js", "gamedev.js")]
    assert order == sorted(order), names
    assert "<title>Hoola Game Dev</title>" in h
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", h), "inline script would break script-src 'self'"
    assert not re.search(r"\son[a-z]+\s*=", h), "inline handlers would break the CSP"
    # every local asset the page names really exists
    for rel in re.findall(r'(?:src|href)="/static/([^"?]+)', h):
        assert (SERVER / "app" / "static" / rel).is_file(), rel


def test_console_sidebar_row_and_go():
    v2 = V2.read_text(encoding="utf-8")
    nav = re.search(r"const NAV = \[(.*?)\];", v2).group(1)
    keys = re.findall(r"\['(\w+)',\s*'([^']*)'\]", nav)
    names = [k for k, _ in keys]
    assert names.index("gamedev") == names.index("appdev") + 1
    assert dict(keys)["gamedev"] == "Game Dev"
    assert re.search(r"IC\.gamedev\s*=\s*'<", v2)
    m = re.search(r"if \(v === 'gamedev'\) \{([^}]*)\}", v2)
    assert m and "location.assign('/console/games'" in m.group(1) and "#/game/" in m.group(1)


def test_employees_js_exports_game_embed_in_node():
    """Run employees.js in node: the factory returns gameEmbed beside the other desks, its page lists are the
    contract's, a project page with no studio id throws (the app relies on that) and an unknown page throws."""
    code = r"""
global.window = {}; global.document = {};
const fs = require('fs');
eval(fs.readFileSync(process.argv[1], 'utf8'));
const E = window.HoolaEmployees({api: async () => ({}), esc: s => String(s), toast() {}, changed() {}, say() {}, open() {}});
const out = {keys: Object.keys(E), pages: E.gameEmbed.pages, project: E.gameEmbed.projectPages,
             stop: typeof E.gameEmbed.stop, errs: []};
for (const [p, sid] of [['board', ''], ['release', ''], ['nope', 'gs_1']]) {
  try { E.gameEmbed({}, p, sid); out.errs.push(null); } catch (e) { out.errs.push(e.message); }
}
console.log(JSON.stringify(out));
"""
    r = subprocess.run(["node", "-e", code, str(EMP)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["keys"][-1] == "gameEmbed" and {"hub", "desk", "game"} <= set(out["keys"])
    assert out["project"] == PROJECT_PAGES
    assert out["pages"] == PROJECT_PAGES + ROLE_PAGES
    assert out["stop"] == "function"
    assert out["errs"][0] and "long project" in out["errs"][0]
    assert out["errs"][1] and "long project" in out["errs"][1]
    assert out["errs"][2] and "Unknown game page" in out["errs"][2]


def test_app_script_parses():
    _js()
    r = subprocess.run(["node", "--check", str(JS)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert CSS.is_file(), "gamedev.css missing"


def test_app_script_carries_every_dom_hook():
    s = _js()
    for hook in ('id="gdv"', "#gdv", "gdv-side", "data-gdv-nav", 'data-gdv-form="ask"', "gdvAsk", "gdvOr",
                 "gdv-card", "data-gdv-act", "gdv-top", "gdv-chat", "gdvMsgs", 'data-gdv-form="thread"', "gdvTh",
                 "gdv-tabs", "data-gdv-tab", "gdvPane", "gdv-embed", "gdv-role", "aria-current"):
        if hook == 'id="gdv"':
            continue                                       # the root lives in gamedev.html; the script finds it
        assert hook in s, hook
    for act in ("hire", "approve", "change", "make-project"):
        assert re.search(r"['\"`=]" + re.escape(act) + r"['\"`]", s), "data-gdv-act " + act
    for k in NAVS + TABS:
        assert re.search(r"['\"`]" + k + r"['\"`]", s), "route / tab key " + k
    for route in ("#/games", "#/crew", "#/arena", "#/big", "#/game/"):
        assert route in s, route
    assert "Hoola Game Dev" in s
    assert "gameEmbed" in s and "gameEmbed.stop" in s      # it leaves panes through the one door


SERVER_FIELDS = r"(?:title|brief|design|notes|error|say|number|stage|goal|name|text|words|url|play_url|message|detail|why|label)"


def _interps(src: str):
    """Every ${...} inside a template literal, with balanced braces, and the line it sits on."""
    i = 0
    while True:
        i = src.find("${", i)
        if i < 0:
            return
        j, depth = i + 2, 1
        while j < len(src) and depth:
            depth += {"{": 1, "}": -1}.get(src[j], 0)
            j += 1
        line_start = src.rfind("\n", 0, i) + 1
        line_end = src.find("\n", j)
        yield src[i + 2:j - 1], src[line_start:line_end if line_end >= 0 else len(src)]
        i = j


def test_app_script_escapes_server_values():
    """A server value (a title she typed, a design the model wrote, an error) never goes into HTML raw. Flags any
    ${...} that reads a server-ish field without esc() / encodeURIComponent / a number cast inside it. A line that only
    sets document.title or textContent is plain text, not HTML, and is allowed."""
    s = _js()
    assert re.search(r"\besc\s*\(", s)
    bad = []
    field = re.compile(r"(?:\.|\[['\"])" + SERVER_FIELDS + r"\b")
    for expr, line in _interps(s):
        if not field.search(expr):
            continue
        # the field only DECIDES between two constants: `${g.stage ? '' : ' hidden'}`
        if re.fullmatch(r"""[^?`'"]+\?\s*(?:'[^']*'|"[^"]*")\s*:\s*(?:'[^']*'|"[^"]*")\s*""", expr):
            continue
        if re.search(r"\besc\s*\(|encodeURIComponent\s*\(|\bNumber\s*\(|\bnum\s*\(|\bmd\s*\(|HoolaMD|\.length\b", expr):
            continue
        # plain text, not HTML: the tab title, textContent, a toast, an Error, and the hint lines sent to the model
        if re.search(r"document\.title\s*=|\.textContent\s*=|\btoast\s*\(|\bconsole\.|new Error\s*\(|\bthrow\b|\bhints\s*=", line):
            continue
        bad.append(line.strip()[:160])
    assert not bad, "unescaped server values:\n" + "\n".join(bad)
    # innerHTML is never fed a raw server field directly either
    assert not re.search(r"innerHTML\s*=\s*[A-Za-z_$][\w$]*\." + SERVER_FIELDS + r"\b", s)


def test_app_script_has_no_key_and_no_eval():
    s = _js()
    assert not re.search(r"\beval\s*\(", s)
    assert not re.search(r"\bnew\s+Function\s*\(", s)
    assert not re.search(r"setTimeout\s*\(\s*['\"`]", s)            # string timers are eval too
    for pat in (r"sk-[A-Za-z0-9_-]{16,}", r"AIza[0-9A-Za-z_-]{20,}", r"ghp_[A-Za-z0-9]{20,}", r"xox[bap]-[A-Za-z0-9-]{10,}",
                r"Bearer\s+[A-Za-z0-9._-]{20,}", r"owner-key", r"api[_-]?key\s*[:=]\s*['\"][^'\"]{8,}"):
        assert not re.search(pat, s, re.I), pat
    # the token comes from the console's own storage key, never typed into the script
    assert "hoola.console.token" in s
    assert not re.search(r"\son[a-z]+\s*=\s*['\"]", s), "inline on*= handlers break script-src 'self'"


# ================================================================ 2. the real-browser walk
TOKEN = "tok_gamedev_walk_0123456789"
DESIGN_A = "# Chai Hop\n\n**Pitch:** tap to fly a chai cup over Mumbai rooftops.\n\n## Controls\n\nTap = hop."


def _seed_games(tenant: str = "default") -> dict:
    """(a) design_ready with a design doc, (b) done with one good version + a play token + a real build on disk,
    (c) a long Studio project around (b). Inserted directly - no model, no Godot."""
    from app.db import session
    from app.gamedesk import service as G
    from app.gamedesk import studio as S
    G.ensure_table()
    S.ensure_tables()
    with session() as s:
        a = G.GameProject(tenant_id=tenant, number="G-0001", title="Chai Hop", brief="ek chai cup jo chhaton par uchhalta hai",
                          status="design_ready", stage="Design taiyaar", pct=100, design=DESIGN_A)
        s.add(a)
        s.flush()
        aid = a.id
    time.sleep(0.02)
    with session() as s:
        b = G.GameProject(tenant_id=tenant, number="G-0002", title="Rickshaw Racer", brief="Mumbai ki sadkon par rickshaw race",
                          status="done", stage="Taiyaar", pct=100, design="# Rickshaw Racer\n\nDodge the potholes.",
                          token=TOKEN, versions=[{"n": 1, "ok": True, "notes": "Tilt to steer.", "shots": [],
                                                  "files": ["main.gd"], "src": "src1", "at": "2026-11-10T10:00:00"}])
        s.add(b)
        s.flush()
        bid = b.id
        brow = b
        s.expunge(brow)
    build = G._vdir(brow, 1) / "build"
    build.mkdir(parents=True, exist_ok=True)
    (build / "index.html").write_text("<!doctype html><meta charset=utf-8><title>Rickshaw Racer</title><p id=game>game</p>")
    st = S.create(tenant, "", "Rickshaw Racer", "Ship it on Play in 6 months", game=bid)
    try:
        S.add_task(tenant, st["id"], "Add a nitro boost", "Tap twice for 2 s of speed", kind="feature")
    except Exception:
        pass                                               # the board renders empty too; the task is a nicety
    return {"a": aid, "b": bid, "sid": st["id"], "url_b": G.view(G._get(tenant, bid))["url"]}


@pytest.fixture
def gd_server(env, monkeypatch, tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setenv("GAME_DIR", str(tmp_path / "games"))
    monkeypatch.setenv("GAME_WORKER", "false")                    # nothing ever builds in the background
    monkeypatch.setenv("PUBLIC_BASE_URL", "")                     # play links stay on this server (relative /play/...)
    from app.config import get_settings
    get_settings.cache_clear()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


class Walk:
    """One browser context; every page error and console error is kept with the step it happened in."""

    def __init__(self, browser, base, key, width=1440, height=900, init=""):
        self.base, self.step, self.errors, self.bad_http = base, "boot", [], []
        self.ctx = browser.new_context(viewport={"width": width, "height": height})
        # init scripts run in EVERY frame, the sandboxed play frame too (opaque origin: localStorage throws there)
        self.ctx.add_init_script(f"if (window === window.top) localStorage.setItem('hoola.console.token', '{key}')")
        if init:
            self.ctx.add_init_script("if (window === window.top) {" + init + "}")
        # the page links Google Fonts; the sandbox may have no route out, and a font is not what is under test
        self.ctx.route("https://fonts.googleapis.com/**", lambda r: r.fulfill(body="", content_type="text/css"))
        self.ctx.route("https://fonts.gstatic.com/**", lambda r: r.fulfill(body=b"", content_type="font/woff2"))
        self.pg = self.ctx.new_page()
        self.pg.on("pageerror", lambda e: self.errors.append(f"[{self.step}] pageerror: {e}"))
        self.pg.on("console", lambda m: m.type == "error" and self.errors.append(f"[{self.step}] console: {m.text}"))
        self.pg.on("response", lambda r: r.status >= 400 and self.bad_http.append(f"[{self.step}] {r.status} {r.request.method} {r.url}"))

    def open(self, hash_=""):
        self.step = "open " + (hash_ or "/")
        self.pg.goto(self.base + "/console/games" + hash_)
        self.pg.wait_for_selector("#gdv")

    def route(self, hash_, sel, timeout=15000):
        self.step = hash_
        self.pg.evaluate("h => { location.hash = h; }", hash_)
        self.pg.wait_for_selector(sel, timeout=timeout)
        self.pg.wait_for_timeout(400)                     # late async renders get the chance to throw inside the step

    def check(self, allow: str = ""):
        """allow = a regex for console lines a test PROVOKES on purpose (the browser logs every failed fetch it was
        told to fail, e.g. 'Failed to load resource: ... status of 500'). Page errors are never allowed."""
        errs = [e for e in self.errors if not (allow and "pageerror" not in e and re.search(allow, e))]
        assert not errs, "\n".join(errs + ["-- http >= 400 seen:"] + self.bad_http)

    def close(self):
        self.ctx.close()


def test_hire_gate_when_the_game_developer_is_not_hired(gd_server):
    base, browser, key = gd_server
    w = Walk(browser, base, key)
    try:
        w.open()
        w.pg.wait_for_selector('[data-gdv-act="hire"]', timeout=15000)
        w.pg.wait_for_timeout(400)
        assert w.pg.locator("aside.gdv-side").count() == 1
        w.check()
    finally:
        w.close()


def test_game_dev_walk_in_a_real_browser(gd_server):
    base, browser, key = gd_server
    from app.employee import hire
    hire.hire("default", "game_dev")
    ids = _seed_games()
    assert ids["url_b"].endswith(f"/play/{TOKEN}/")
    a, b = ids["a"], ids["b"]
    w = Walk(browser, base, key)
    pg = w.pg
    try:
        # ---------------- home
        w.open()
        pg.wait_for_selector("a.gdv-card", timeout=20000)
        pg.wait_for_timeout(400)
        assert pg.title() == "Hoola Game Dev"
        assert pg.locator("aside.gdv-side").count() == 1
        assert pg.locator('[data-gdv-act="hire"]').count() == 0                    # hired: no gate
        for k in NAVS:
            assert pg.locator(f'aside.gdv-side [data-gdv-nav="{k}"]').count() >= 1, k
        assert pg.get_attribute('[data-gdv-nav="home"]', "aria-current") == "page"
        assert pg.locator('form[data-gdv-form="ask"] textarea#gdvAsk').count() == 1
        assert pg.locator('form[data-gdv-form="ask"] select#gdvOr').count() == 1
        hrefs = pg.eval_on_selector_all("a.gdv-card", "els => els.map(e => e.getAttribute('href'))")
        assert any(re.fullmatch(rf"#/game/{a}/\w+", h or "") for h in hrefs), hrefs
        assert any(re.fullmatch(rf"#/game/{b}/\w+", h or "") for h in hrefs), hrefs
        # the design_ready game sits under a "waiting" heading on home
        waiting = pg.evaluate("""id => { const c = document.querySelector(`a.gdv-card[href^="#/game/${id}/"]`);
            let n = c; while (n && n !== document.body) { let p = n.previousElementSibling;
              while (p) { if (/wait/i.test(p.textContent || '')) return p.textContent.trim().slice(0, 80); p = p.previousElementSibling; }
              n = n.parentElement; } return ''; }""", a)
        assert waiting, "design_ready game is not under a 'waiting' heading on home"
        w.check()

        # ---------------- each nav route
        for k, h in (("games", "#/games"), ("crew", "#/crew"), ("arena", "#/arena"), ("big", "#/big"), ("home", "#/")):
            w.route(h, f'[data-gdv-nav="{k}"][aria-current="page"]')
            assert pg.locator("#gdv").inner_text().strip(), h
            w.check()
        w.route("#/games", "a.gdv-card")
        assert pg.locator(f'a.gdv-card[href^="#/game/{a}/"]').count() >= 1
        assert pg.locator(f'a.gdv-card[href^="#/game/{b}/"]').count() >= 1
        w.check()

        # ---------------- crew grid + one role page
        w.route("#/crew", 'a.gdv-role[href^="#/crew/"]')
        n_roles = pg.locator('a.gdv-role[href^="#/crew/"]').count()
        assert n_roles >= 5, n_roles
        role_href = pg.get_attribute('a.gdv-role[href^="#/crew/"]', "href")
        w.step = "click " + role_href
        pg.click(f'a.gdv-role[href="{role_href}"]')
        pg.wait_for_function("h => location.hash === h", arg=role_href)
        pg.wait_for_timeout(800)
        assert pg.locator('[data-gdv-nav="crew"][aria-current="page"]').count() == 1
        assert pg.locator("#gdv").inner_text().strip()
        w.check()

        # ---------------- the design_ready game: Design tab
        w.route(f"#/game/{a}/design", 'nav.gdv-tabs a[data-gdv-tab="design"][aria-current="page"]')
        assert pg.title() == "Chai Hop · Hoola Game Dev"
        assert pg.locator("header.gdv-top").count() == 1
        assert pg.locator("section.gdv-chat #gdvMsgs").count() == 1
        assert pg.locator('section.gdv-chat form[data-gdv-form="thread"] textarea#gdvTh').count() == 1
        for t in TABS:
            assert pg.locator(f'nav.gdv-tabs a[data-gdv-tab="{t}"]').count() == 1, t
        pane = pg.inner_text("#gdvPane")
        assert "Chai Hop" in pane and "tap to fly" in pane, pane[:300]
        assert pg.locator('#gdvPane [data-gdv-act="approve"]').count() == 1
        assert pg.locator('#gdvPane [data-gdv-act="change"]').count() == 1
        assert pg.locator("#gdvPane h1, #gdvPane h2, #gdvPane h3").count() >= 1   # the markdown was rendered, not dumped
        w.check()
        # a project-only tab on a game with no long project offers to make one (never throws gameEmbed's error)
        w.route(f"#/game/{a}/board", '[data-gdv-act="make-project"]')
        assert pg.get_attribute('nav.gdv-tabs a[data-gdv-tab="board"]', "aria-current") == "page"
        w.check()

        # ---------------- the done game: Play tab
        w.route(f"#/game/{b}/play", "#gdvPane iframe")
        assert pg.title() == "Rickshaw Racer · Hoola Game Dev"
        src = pg.get_attribute("#gdvPane iframe", "src") or ""
        assert src.endswith(f"/play/{TOKEN}/"), src
        assert pg.evaluate("() => document.querySelector('#gdvPane iframe').src") == base + f"/play/{TOKEN}/"
        w.check()

        # ---------------- every embedded tab of the game that has a long project
        for t in ("board", "bible", "scenes", "assets", "qa", "release", "liveops", "prov"):
            w.route(f"#/game/{b}/{t}", f'nav.gdv-tabs a[data-gdv-tab="{t}"][aria-current="page"]')
            pg.wait_for_selector("#gdvPane .gdv-embed", timeout=15000)
            pg.wait_for_function("() => (document.querySelector('#gdvPane .gdv-embed').innerText || '').trim().length > 20",
                                 timeout=15000)
            pg.wait_for_timeout(600)
            assert pg.locator('#gdvPane [data-gdv-act="make-project"]').count() == 0, t
            w.check()
        w.route(f"#/game/{b}/crew", 'nav.gdv-tabs a[data-gdv-tab="crew"][aria-current="page"]')
        assert pg.inner_text("#gdvPane").strip()
        w.check()
        w.route(f"#/game/{b}/design", 'nav.gdv-tabs a[data-gdv-tab="design"][aria-current="page"]')
        assert "Rickshaw Racer" in pg.inner_text("#gdvPane")
        w.check()

        # ---------------- back home: the title comes back
        w.route("#/", '[data-gdv-nav="home"][aria-current="page"]')
        assert pg.title() == "Hoola Game Dev"
        w.check()
    finally:
        w.close()

    # ---------------- phone width: home and a game, no sideways scroll
    w = Walk(browser, base, key, width=390)
    try:
        for h, sel in (("", "a.gdv-card"), (f"#/game/{a}/design", "#gdvPane"), (f"#/game/{b}/board", "#gdvPane .gdv-embed")):
            w.open(h)
            w.pg.wait_for_selector(sel, timeout=20000)
            w.pg.wait_for_timeout(600)
            m = w.pg.evaluate("() => ({sw: document.scrollingElement.scrollWidth, iw: innerWidth})")
            assert m["sw"] <= m["iw"] + 1, (h or "#/", m)
        w.check()
    finally:
        w.close()


# ================================================================ 3. regressions from the independent review
# Each of these failed on the first build of the app (or on the shared files before the lead's fix) and must keep
# passing. Rows are inserted directly; nothing calls a model or Godot.
LOAD_FAIL = r"Failed to load resource: the server responded with a status of "


def _game(tenant="default", *, build=False, **kw):
    """One GameProject row. build=True gives it a good v1, a play token and a real index.html on disk."""
    import secrets
    from app.db import session
    from app.gamedesk import service as G
    G.ensure_table()
    fields = {"tenant_id": tenant, "number": kw.pop("number", "G-%04d" % secrets.randbelow(9999)), "title": "Chai Hop",
              "brief": "ek chai cup jo chhaton par uchhalta hai", "status": "design_ready", "pct": 100, "design": DESIGN_A}
    if build:
        fields.update(status="done", token="tk" + secrets.token_hex(12),
                      versions=[{"n": 1, "ok": True, "notes": "Tilt to steer.", "shots": [], "files": ["main.gd"],
                                 "src": "src1", "at": "2026-11-10T10:00:00"}])
    fields.update(kw)
    with session() as s:
        r = G.GameProject(**fields)
        s.add(r)
        s.flush()
        s.expunge(r)
    if build:
        d = G._vdir(r, 1) / "build"
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text("<!doctype html><meta charset=utf-8><title>game</title><p id=game>game</p>")
    time.sleep(0.02)
    return r.id


def _set_game(gid, **kw):
    from app.db import session
    from app.gamedesk import service as G
    with session() as s:
        r = s.get(G.GameProject, gid)
        for k, v in kw.items():
            setattr(r, k, v)
        r.updated_at = G.now()


def _project(gid, tenant="default"):
    from app.gamedesk import studio as S
    S.ensure_tables()
    return S.create(tenant, "", "Long project", "Ship it", game=gid)["id"]


def _conv(tenant="default", user_text=""):
    from app.db import Conversation, Message, session
    with session() as s:
        c = Conversation(tenant_id=tenant, title="Game thread")
        s.add(c)
        s.flush()
        cid = c.id
        if user_text:
            s.add(Message(conversation_id=cid, role="user", content=user_text, display=user_text, in_history=False))
    return cid


def _hired(tenant="default"):
    from app.employee import hire
    hire.hire(tenant, "game_dev")


def _requests(pg):
    seen = []
    pg.on("request", lambda r: seen.append((r.method, r.url, r.post_data or "")))
    return seen


GAME_DESK_HOME = """() => { const p = document.querySelector('#gdvPane') || document.querySelector('#gdvMain') || document;
  return {fail: !!p.querySelector('.gdv-embedfail'), retry: !!p.querySelector('.gdv-embedfail [data-embed-retry]'),
          gdNew: !!document.querySelector('#gdNew'), role: !!document.querySelector('[data-gs-role]'),
          h2: [...document.querySelectorAll('h2')].some(h => /Game Desk/.test(h.textContent))}; }"""


def test_embed_fallback_never_draws_the_whole_game_desk(gd_server):
    """1. An embedded page whose API fails draws the small 'could not load' panel with Try again - never the console's
    whole Game Desk home (#gdNew, the role cards, an h2 'Game Desk') inside a Game Dev tab."""
    base, browser, key = gd_server
    _hired()
    gid = _game(build=True)
    sid = _project(gid)
    w = Walk(browser, base, key)
    try:
        w.pg.route(re.compile(rf"/api/gamestudio/{sid}(\?.*)?$"), lambda r: r.fulfill(status=500, json={"detail": "boom"}))
        w.open(f"#/game/{gid}/board")
        w.pg.wait_for_selector("#gdvPane .gdv-embedfail", timeout=15000)
        w.pg.wait_for_timeout(600)
        got = w.pg.evaluate(GAME_DESK_HOME)
        assert got == {"fail": True, "retry": True, "gdNew": False, "role": False, "h2": False}, got
        w.check(allow=LOAD_FAIL + "500")
    finally:
        w.close()
    # the Game Arena is the owner's only: another signed-in person gets 403 from the server itself
    from app import accounts
    tok = accounts.issue_session("usr_gamedev_b")
    _hired("usr_gamedev_b")
    w = Walk(browser, base, tok)
    try:
        w.open("#/arena")
        w.pg.wait_for_selector(".gdv-embedfail", timeout=15000)
        w.pg.wait_for_timeout(600)
        got = w.pg.evaluate(GAME_DESK_HOME)
        assert got["fail"] and not got["gdNew"] and not got["role"] and not got["h2"], got
        assert any(" 403 " in x and "/api/gamedesk/arena" in x for x in w.bad_http), w.bad_http   # the real refusal
        w.check(allow=LOAD_FAIL + "403")
    finally:
        w.close()


def test_play_frame_survives_a_progress_tick(gd_server):
    """2. A game that plays while its next version builds: the poll's progress tick must not rebuild the iframe (the
    game she is playing would restart every 3 s)."""
    base, browser, key = gd_server
    _hired()
    gid = _game(build=True, status="building", stage="Godot mein bana raha hoon", pct=30)
    w = Walk(browser, base, key)
    try:
        w.open(f"#/game/{gid}/play")
        w.pg.wait_for_selector("#gdvPane iframe", timeout=15000)
        w.pg.evaluate("() => { document.querySelector('#gdvPane iframe').__gdvMark = 'still-me'; }")
        _set_game(gid, pct=55, stage="Khud khel kar jaanch raha hoon")
        w.pg.wait_for_timeout(4000)
        _set_game(gid, pct=70, stage="Godot mein bana raha hoon, phir se")
        w.pg.wait_for_timeout(4500)                       # > 2 poll intervals (3 s) after the first change
        mark = w.pg.evaluate("() => { const f = document.querySelectorAll('#gdvPane iframe');"
                             " return {n: f.length, mark: f[0] && f[0].__gdvMark}; }")
        assert mark == {"n": 1, "mark": "still-me"}, mark
        # the NEXT version moving from building to testing changes nothing about the version she plays (same v1,
        # same play link), so her game must not restart either
        _set_game(gid, pct=85, status="testing", stage="Khud khel kar jaanch raha hoon")
        w.pg.wait_for_timeout(7000)
        mark = w.pg.evaluate("() => { const f = document.querySelectorAll('#gdvPane iframe');"
                             " return {n: f.length, mark: f[0] && f[0].__gdvMark}; }")
        assert mark == {"n": 1, "mark": "still-me"}, ("building -> testing restarted the game she is playing", mark)
        w.check()
    finally:
        w.close()


def test_home_typing_survives_the_home_poll(gd_server):
    """3. With a game busy the home re-reads every few seconds; what she is typing, her focus and her scroll stay."""
    base, browser, key = gd_server
    _hired()
    busy = _game(status="building", stage="Godot mein bana raha hoon", pct=20, title="Busy one")
    for i in range(8):                                     # enough cards for the home to scroll at 500px
        _game(title=f"Old game {i}")
    w = Walk(browser, base, key, height=500)
    try:
        w.open()
        w.pg.wait_for_selector("#gdvAsk", timeout=15000)
        w.pg.wait_for_timeout(500)
        w.pg.click("#gdvAsk")
        w.pg.keyboard.type("ek cricket game jisme ball")
        before = w.pg.evaluate("""() => { const els = [document.scrollingElement, document.querySelector('#gdvMain')].filter(Boolean);
            const sc = els.find(e => e.scrollHeight > e.clientHeight + 40) || els[0];
            sc.scrollTop = 60; window.__gdvSc = sc; document.querySelector('#gdvAsk').focus();
            return {top: sc.scrollTop, scrollable: sc.scrollHeight > sc.clientHeight}; }""")
        _set_game(busy, pct=45)
        w.pg.wait_for_timeout(11500)                       # > 2 home polls (5 s)
        after = w.pg.evaluate("""() => ({v: document.querySelector('#gdvAsk').value,
            focus: document.activeElement === document.querySelector('#gdvAsk'),
            top: window.__gdvSc.scrollTop, attached: window.__gdvSc.isConnected})""")
        assert after["v"] == "ek cricket game jisme ball", after
        assert after["focus"], after
        assert after["attached"] and after["top"] == before["top"], (before, after)
        w.check()
    finally:
        w.close()


def test_conversation_kept_on_a_transient_error_and_taken_from_the_server(gd_server):
    """4. (a) A 503 while checking the stored thread must not throw the game's thread away for a new one.
    (b) A browser that never saw the game (empty storage) opens the game's OWN thread from the server row."""
    base, browser, key = gd_server
    _hired()
    conv = _conv()
    gid = _game(conversation_id=conv)
    once = {"n": 0}

    def flaky(route):
        if once["n"] == 0:
            once["n"] += 1
            return route.fulfill(status=503, json={"detail": "busy"})
        return route.continue_()

    w = Walk(browser, base, key, init=f"localStorage.setItem('hoola.gamedev.conv.{gid}', '{conv}');"
                                      "window.__toasts = []; new MutationObserver(() => { const t = document.getElementById('toast');"
                                      " if (t && !t.hidden && t.textContent) window.__toasts.push(t.textContent); })"
                                      ".observe(document, {subtree: true, childList: true, characterData: true, attributes: true});")
    sent = _requests(w.pg)
    try:
        w.pg.route(re.compile(rf"/api/conversations/{conv}/messages\?limit=1$"), flaky)
        # her message must not start a real turn (that would call a model): the POST is answered here
        w.pg.route(re.compile(rf"/api/conversations/[^/]+/messages$"),
                   lambda r: r.fulfill(status=202, json={"ok": True}) if r.request.method == "POST" else r.continue_())
        w.open(f"#/game/{gid}/design")
        w.pg.wait_for_selector("textarea#gdvTh", timeout=15000)
        w.pg.fill("textarea#gdvTh", "thoda tez karo")
        w.pg.evaluate("() => document.querySelector('form[data-gdv-form=\"thread\"]').requestSubmit()")
        w.pg.wait_for_timeout(2500)
        stored = w.pg.evaluate(f"() => localStorage.getItem('hoola.gamedev.conv.{gid}')")
        assert stored == conv, (stored, conv)
        assert not any(m == "POST" and u.endswith("/api/conversations") for m, u, _ in sent), "a new thread was made"
        if once["n"]:                                      # the 503 really happened: she was told
            assert w.pg.evaluate("() => window.__toasts.length") > 0
        w.check(allow=LOAD_FAIL + "503")
    finally:
        w.close()
    w = Walk(browser, base, key)
    sent = _requests(w.pg)
    try:
        w.open(f"#/game/{gid}/design")
        w.pg.wait_for_selector("textarea#gdvTh", timeout=15000)
        w.pg.wait_for_timeout(1500)
        stored = w.pg.evaluate(f"() => localStorage.getItem('hoola.gamedev.conv.{gid}')")
        reads = [u for m, u, _ in sent if f"/api/conversations/{conv}/" in u]
        assert stored == conv or (not stored and reads), (stored, conv, reads)
        assert reads, "the game's own thread was never read"
        assert not any(m == "POST" and u.endswith("/api/conversations") for m, u, _ in sent), "a new thread was made"
        w.check()
    finally:
        w.close()


def test_unknown_tab_falls_back_to_the_default_tab(gd_server):
    """5. #/game/<id>/nonsense shows the game's default tab, with exactly one tab marked current."""
    base, browser, key = gd_server
    _hired()
    plain = _game()
    playable = _game(build=True, title="Rickshaw Racer")
    w = Walk(browser, base, key)
    try:
        for gid, want in ((plain, "design"), (playable, "play")):
            w.open(f"#/game/{gid}/nonsense")
            w.pg.wait_for_selector("nav.gdv-tabs", timeout=15000)
            w.pg.wait_for_timeout(600)
            cur = w.pg.eval_on_selector_all('nav.gdv-tabs [aria-current="page"]', "els => els.map(e => e.dataset.gdvTab)")
            assert cur == [want], (gid, cur)
            assert w.pg.inner_text("#gdvPane").strip()
        w.check()
    finally:
        w.close()


HOSTILE_IMG = "<img src=x onerror=window.__pwned=1>"
HOSTILE_SCRIPT = '"><script>window.__pwned=1</script>'


def test_hostile_content_stays_text(gd_server):
    """6. Titles, briefs, designs, notes and errors are data. Nothing in them runs, no javascript: link survives,
    and the hint lines the app adds to her message never show in her bubble - even when the title has ']'."""
    base, browser, key = gd_server
    _hired()
    title = "Boss ]Fight[ " + HOSTILE_IMG
    hint = ('\n\n[Web console Game Dev: this chat is only about game G-0666 "' + title + '" (game id x, studio project none).'
            ' Work on THIS game; never start a new game unless I ask.]'
            '\n\n[Web console language preference: Reply in English unless I explicitly request another language.]')
    conv = _conv(user_text="Make it faster" + hint)
    design = ("# Evil " + HOSTILE_IMG + "\n\n" + HOSTILE_SCRIPT + "\n\n[click me](javascript:alert(1)) and "
              "[also](JavaScript:window.__pwned=1)\n\n<a href=\"javascript:window.__pwned=1\">raw</a>")
    vers = [{"n": 1, "ok": True, "notes": HOSTILE_IMG + HOSTILE_SCRIPT, "shots": [], "files": ["main.gd"], "src": "s",
             "words": HOSTILE_SCRIPT, "at": "2026-11-10T10:00:00"}]
    evil = _game(build=True, number="G-0666", title=title, brief="brief " + HOSTILE_SCRIPT + HOSTILE_IMG, design=design,
                 error="err " + HOSTILE_IMG, stage=HOSTILE_SCRIPT, versions=vers, conversation_id=conv)
    evil2 = _game(title=title, brief=HOSTILE_SCRIPT, design=design, error=HOSTILE_IMG, status="failed")
    w = Walk(browser, base, key, init=f"localStorage.setItem('hoola.gamedev.conv.{evil}', '{conv}');")
    try:
        probe = """() => ({pwned: typeof window.__pwned,
            img: document.querySelectorAll('img[src="x"], img[onerror], [onerror]').length,
            script: [...document.scripts].filter(s => /__pwned/.test(s.textContent)).length,
            js: [...document.querySelectorAll('[href],[src],[action],[formaction]')].map(e => e.getAttribute('href') || e.getAttribute('src')
                 || e.getAttribute('action') || e.getAttribute('formaction') || '').filter(h => /^\\s*javascript:/i.test(h)).length})"""
        clean = {"pwned": "undefined", "img": 0, "script": 0, "js": 0}
        for h, sel in (("", "a.gdv-card"), (f"#/game/{evil}/design", "#gdvPane"), (f"#/game/{evil}/play", "#gdvPane iframe"),
                       (f"#/game/{evil2}/design", "#gdvPane"), ("#/games", "a.gdv-card")):
            w.open(h)
            w.pg.wait_for_selector(sel, timeout=15000)
            w.pg.wait_for_timeout(900)
            got = w.pg.evaluate(probe)
            assert got == clean, (h or "#/", got)
            if h.startswith("#/game/"):
                assert "Boss ]Fight[" in w.pg.inner_text("header.gdv-top")       # shown, as text
        w.open(f"#/game/{evil}/design")
        w.pg.wait_for_function("() => /Make it faster/.test(document.querySelector('#gdvMsgs')?.innerText || '')", timeout=15000)
        msgs = w.pg.inner_text("#gdvMsgs")
        assert "[Web console" not in msgs, msgs[:400]
        assert w.pg.evaluate(probe) == clean
        w.check()
    finally:
        w.close()


TYPE_RULES = """() => { const bad = [];
  document.querySelectorAll('#gdvPane .gdv-embed *').forEach(e => {
    if (!e.getClientRects().length) return;                                // not drawn
    const has = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!has && !/^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(e.tagName)) return;  // only what carries words
    const cs = getComputedStyle(e), w = parseInt(cs.fontWeight, 10) || 400, z = parseFloat(cs.fontSize);
    if (w > 600 || z < 12 || cs.textTransform === 'uppercase')
      bad.push(`${e.tagName}.${e.className} w=${w} size=${z} tt=${cs.textTransform} "${(e.textContent || e.value || '').trim().slice(0, 30)}"`); });
  return bad.slice(0, 15); }"""


def test_embedded_pages_follow_the_type_rules(gd_server):
    """7. Inside the embedded pages: nothing heavier than 600, nothing under 12px, no all-caps (the console's rules)."""
    base, browser, key = gd_server
    _hired()
    gid = _game(build=True)
    _project(gid)
    w = Walk(browser, base, key)
    try:
        for t in ("board", "release"):
            w.open(f"#/game/{gid}/{t}")
            w.pg.wait_for_function("() => (document.querySelector('#gdvPane .gdv-embed')?.innerText || '').trim().length > 20",
                                   timeout=15000)
            w.pg.wait_for_timeout(800)
            bad = w.pg.evaluate(TYPE_RULES)
            assert not bad, (t, bad)
        w.check()
    finally:
        w.close()


def test_write_actions_send_the_right_requests(gd_server):
    """8. Approve -> POST /api/game/<id>/approve; make-project -> POST /api/gamestudio {game}; delete asks first and a
    dismissed confirm sends nothing. GAME_WORKER is off, so an approved design only queues (no model, no Godot)."""
    base, browser, key = gd_server
    _hired()
    design = _game()
    playable = _game(build=True, title="Rickshaw Racer")
    w = Walk(browser, base, key)
    sent = _requests(w.pg)
    asked = []
    try:
        # delete: dismissed -> no DELETE
        w.open(f"#/game/{design}/design")
        w.pg.wait_for_selector('#gdvPane [data-gdv-act="delete"]', timeout=15000)
        w.pg.once("dialog", lambda d: (asked.append(d.type), d.dismiss()))
        w.pg.click('#gdvPane [data-gdv-act="delete"]')
        w.pg.wait_for_timeout(1200)
        assert asked == ["confirm"], asked
        assert not [u for m, u, _ in sent if m == "DELETE"], sent
        # make-project on the playable game that has none
        w.open(f"#/game/{playable}/board")
        w.pg.wait_for_selector('#gdvPane [data-gdv-act="make-project"]:not([disabled])', timeout=15000)
        w.pg.click('#gdvPane [data-gdv-act="make-project"]')
        w.pg.wait_for_function("() => !document.querySelector('#gdvPane [data-gdv-act=\"make-project\"]')", timeout=15000)
        posts = [json.loads(b or "{}") for m, u, b in sent if m == "POST" and re.search(r"/api/gamestudio$", u)]
        assert posts and posts[0].get("game") == playable, posts
        # approve the design
        w.open(f"#/game/{design}/design")
        w.pg.wait_for_selector('#gdvPane [data-gdv-act="approve"]', timeout=15000)
        w.pg.click('#gdvPane [data-gdv-act="approve"]')
        w.pg.wait_for_timeout(1500)
        assert [u for m, u, _ in sent if m == "POST" and u.endswith(f"/api/game/{design}/approve")], sent
        from app.gamedesk import service as G
        assert G._get("default", design).status == "queued"
        w.check()
    finally:
        w.close()


def test_timers_stop_when_she_leaves_the_game(gd_server):
    """9. Leaving a busy game (with an embedded page open) for home: no more reads of that game or its project."""
    base, browser, key = gd_server
    _hired()
    gid = _game(build=True, status="building", pct=40)
    sid = _project(gid)
    w = Walk(browser, base, key)
    sent = _requests(w.pg)
    try:
        w.open(f"#/game/{gid}/board")
        w.pg.wait_for_selector("#gdvPane .gdv-embed", timeout=15000)
        w.pg.wait_for_timeout(1500)
        w.route("#/", '[data-gdv-nav="home"][aria-current="page"]')
        w.pg.wait_for_timeout(500)
        mark = len(sent)
        w.pg.wait_for_timeout(8000)
        late = [u for m, u, _ in sent[mark:] if re.search(rf"/api/(game/{gid}|gamestudio/{sid})(/|\?|$)", u)]
        assert not late, late
        w.check()
    finally:
        w.close()


def _lum(rgb: str) -> float:
    nums = [float(x) for x in re.findall(r"[\d.]+", rgb)[:3]]
    assert len(nums) == 3, rgb
    lin = [(c / 255) / 12.92 if c / 255 <= 0.03928 else (((c / 255) + 0.055) / 1.055) ** 2.4 for c in nums]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def test_dark_theme(gd_server):
    """10. theme.js reads localStorage 'hoola.theme' and sets data-theme on <html>: dark home + dark game tab."""
    base, browser, key = gd_server
    _hired()
    gid = _game(build=True)
    w = Walk(browser, base, key, init="localStorage.setItem('hoola.theme', 'dark');")
    try:
        for h, sel in (("", "a.gdv-card"), (f"#/game/{gid}/design", "#gdvPane"), (f"#/game/{gid}/play", "#gdvPane iframe")):
            w.open(h)
            w.pg.wait_for_selector(sel, timeout=15000)
            w.pg.wait_for_timeout(500)
            assert w.pg.evaluate("() => document.documentElement.dataset.theme") == "dark"
            bg = w.pg.evaluate("() => getComputedStyle(document.body).backgroundColor")
            assert _lum(bg) < 0.1, (h or "#/", bg)
            shell = w.pg.evaluate("() => { const e = document.querySelector('.gdv-main') || document.querySelector('#gdv');"
                                  " let n = e; while (n) { const c = getComputedStyle(n).backgroundColor;"
                                  " if (!/rgba\\(0, 0, 0, 0\\)|transparent/.test(c)) return c; n = n.parentElement; } return ''; }")
            assert shell and _lum(shell) < 0.1, (h or "#/", shell)
            ink = w.pg.evaluate("() => getComputedStyle(document.querySelector('#gdvPane') || document.querySelector('#gdvMain')).color")
            assert _lum(ink) > 0.4, (h or "#/", ink)                                 # the words are light on dark
        w.check()
    finally:
        w.close()
