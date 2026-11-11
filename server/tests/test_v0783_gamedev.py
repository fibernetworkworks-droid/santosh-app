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
        if re.search(r"\besc\s*\(|encodeURIComponent\s*\(|\bNumber\s*\(|\bnum\s*\(|\bmd\s*\(|HoolaMD|\.length\b", expr):
            continue
        if re.search(r"document\.title\s*=|\.textContent\s*=|\btoast\s*\(|\bconsole\.|new Error\s*\(|\bthrow\b", line):
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

    def __init__(self, browser, base, key, width=1440):
        self.base, self.step, self.errors, self.bad_http = base, "boot", [], []
        self.ctx = browser.new_context(viewport={"width": width, "height": 900})
        self.ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
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

    def check(self):
        assert not self.errors, "\n".join(self.errors + ["-- http >= 400 seen:"] + self.bad_http)

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
