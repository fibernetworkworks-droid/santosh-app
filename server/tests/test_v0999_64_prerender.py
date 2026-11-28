"""v0.999.64 D3 PRE-RENDER + ISLANDS (docs/WEB_DESIGN_ENGINE_PLAN.md phase D3, P6): every page of an App Engine app is
rendered to finished HTML in the build box; on a SITE app a page is plain HTML + CSS that loads JavaScript only for its
islands ("use client" components) and goes out at the app's own address (sealed by `sandbox` in its CSP, read by
Google); a page with <AppPage> / an app screen stays the full app in its sealed frame. Done-line: content pages pass
Core Web Vitals in the lab (`speed.lab_check`)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.appengine import kit as KIT
from app.appengine import rules as RL
from tests.test_v0814_app_engine import _box, _refused, _tool, ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]
TPL = KIT.TEMPLATE

SITE_APP = '''import { Routes, Route, Link } from "react-router-dom";
import { Seo, AppPage } from "@/lib/seo";
import Hero from "@/components/blocks/hero";
import Faq from "@/components/blocks/faq";
import ServicesGrid from "@/components/blocks/services-grid";
import ScreenTable from "@/components/blocks/screen-table";

function Nav() {
  return (
    <nav className="flex gap-4 p-4">
      <Link to="/">Home</Link>
      <Link to="/about">About</Link>
      <Link to="/account">Account</Link>
    </nav>
  );
}
function Home() {
  return (
    <main>
      <Seo title="Asha Dental, Nagpur" description="Gentle dental care in Ramdaspeth." jsonLd={{ "@type": "Dentist", name: "Asha Dental" }} />
      <Nav />
      <Hero />
      <ServicesGrid />
      <Faq />
    </main>
  );
}
function About() {
  return (
    <main>
      <Seo title="About Asha Dental" description="Our story." />
      <Nav />
      <h1 className="p-4 text-3xl">About us</h1>
    </main>
  );
}
function Account() {
  return (
    <AppPage>
      <Seo title="Your visits" noindex />
      <Nav />
      <ScreenTable />
    </AppPage>
  );
}
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/about" element={<About />} />
      <Route path="/account" element={<Account />} />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
'''


# ---------------------------------------------------------------- 1. the template carries the pieces, locked
def test_template_has_the_prerender_pieces_and_they_are_locked():
    for rel in ("hoola.prerender.mjs", "src/entry-server.tsx", "src/islands-entry.tsx", "src/lib/island.tsx", "src/lib/seo.tsx"):
        assert (TPL / rel).exists(), rel
        assert rel in RL.LOCKED, rel
        with pytest.raises(RL.RuleError, match="locked"):
            RL.writable(rel)
    assert "hoola.render.json" in RL.LOCKED
    from app.appengine import service as AE
    for rel in ("hoola.prerender.mjs", "src/entry-server.tsx", "src/islands-entry.tsx", "src/lib/island.tsx", "src/lib/seo.tsx"):
        assert rel in AE.TOOLING, rel                      # an older app gets them before its next build
    vc = (TPL / "vite.config.ts").read_text()
    assert "isSsrBuild" in vc and "noExternal: true" in vc and "islands-entry.tsx" in vc and "manifest: true" in vc
    assert "hoolaIslands()" in vc
    from app.appengine import runner as RN
    assert "--ssr src/entry-server.tsx" in RN.SCRIPT and "hoola.prerender.mjs" in RN.SCRIPT and "|| true" in RN.SSR


def test_the_kit_shows_its_words_without_javascript():
    rv = (TPL / "src/components/effects/reveal.tsx").read_text()
    assert "useInView" not in rv and "opacity-0" not in rv and "hoola-reveal" in rv
    css = (TPL / "src/index.css").read_text()
    assert "animation-timeline: view()" in css and "@supports (animation-timeline: view())" in css
    nt = (TPL / "src/components/effects/number-ticker.tsx").read_text()
    assert "React.useState(value)" in nt                 # the page has the real number
    for p in KIT.kit_files():
        code = p.read_text()
        if p.suffix == ".tsx":
            # nothing reads window / document while it renders at the top level of a kit file
            top = [ln for ln in code.splitlines() if re.match(r"^(const|let|var)\s+\w+\s*=\s*(window|document)\b", ln)]
            assert not top, (p.name, top)


def test_interactive_blocks_are_islands_static_ones_are_not():
    isl, plain = [], []
    for b in KIT.block_ids():
        code = (KIT.BLOCKS_DIR / KIT.file_of(b)).read_text()
        (isl if code.lstrip().startswith('"use client"') else plain).append(b)
        assert "export default function" in code, b      # the island wrap is the build's, never hand-written
    assert {"faq", "contact_block", "booking_slots", "pricing_table", "gallery_masonry"} <= set(isl)
    assert {"hero", "process_steps", "team", "stats_counters", "logos_marquee"} <= set(plain)
    assert not any(b.startswith("screen_") for b in isl)  # app screens run as the full app instead
    assert 'data-hoola-app={block.startsWith("screen-")' in (KIT.BLOCKS_DIR / "_kit.tsx").read_text()
    plug = (TPL / "hoola.plugin.mjs").read_text()
    assert "export function hoolaIslands" in plug and "__hoolaIsland" in plug


def test_render_mode_is_app_unless_asked_and_kept(ae_env):
    from app.appengine import service as AE
    # an app made before D3 (or without a word) stays the whole app: its buttons keep working
    a = _tool(action="create", name="Shop staff tasks", brief="A task list for my shop staff")
    assert a["render"] == "app" and AE.render_mode(AE._load(T, a["id"])) == "app"
    s = _tool(action="create", name="Asha Dental", brief="a dental clinic website", render="site")
    assert AE.render_mode(AE._load(T, s["id"])) == "site"
    b = _tool(action="create", name="Ops", brief="something", render="app")
    assert AE.render_mode(AE._load(T, b["id"])) == "app"
    r = _tool(action="render_mode", app=b["id"], render="site")
    assert "next build" in r["say"] and AE.render_mode(AE._load(T, b["id"])) == "site"
    assert "render_mode" in _refused(action="render_mode", app=b["id"])
    assert "render_mode" in _refused(action="write", app=b["id"], path="hoola.render.json", code="{}")
    snap = ae_env / "snapcheck"
    snap.mkdir()
    AE._prep_snap(AE._load(T, b["id"]), snap)
    assert json.loads((snap / "hoola.render.json").read_text()) == {"mode": "site"}


def test_a_site_page_with_its_own_state_is_named(ae_env):
    from app.appengine import service as AE
    d = ae_env / "deadcheck"
    (d / "src" / "pages").mkdir(parents=True)
    (d / "src" / "components").mkdir(parents=True)
    (d / "src" / "pages" / "Home.tsx").write_text("export default function Home(){ const [n,setN]=React.useState(0); return <button onClick={()=>setN(n+1)}>{n}</button>; }")
    (d / "src" / "pages" / "About.tsx").write_text("export default function About(){ return <h1>About</h1>; }")
    (d / "src" / "pages" / "Account.tsx").write_text("export default function A(){ const [x]=useState(1); return <AppPage>{x}</AppPage>; }")
    (d / "src" / "components" / "Counter.tsx").write_text('"use client";\nexport default function Counter(){ const [n,setN]=React.useState(0); return <b onClick={()=>setN(1)}>{n}</b>; }')
    assert AE.site_dead_code(d) == ["src/pages/Home.tsx"]


def _site_app():
    _box()
    from app.appengine import service as AE
    aid = _tool(action="create", name="Asha Dental", brief="a dental clinic website in Nagpur", render="site")["id"]
    _tool(action="write", app=aid, path="src/App.tsx", code=SITE_APP)
    res = _tool(action="build", app=aid)
    assert res.get("built"), res.get("say")
    r = AE._load(T, aid)
    return aid, r, AE.ver_dir(r, r.version) / "dist", res


def test_a_site_app_prerenders_every_page_with_islands_only_where_needed(ae_env):
    aid, r, dist, res = _site_app()
    pg = json.loads((dist / "__pages.json").read_text())
    assert pg["ok"] and pg["mode"] == "site" and not pg["failed"], pg
    kinds = {p["path"]: p for p in pg["pages"]}
    assert set(kinds) == {"/", "/about", "/account"}, kinds   # found by following the app's own links
    assert kinds["/"]["kind"] == "site" and "components/blocks/faq" in kinds["/"]["islands"]
    assert kinds["/about"]["kind"] == "site" and kinds["/about"]["islands"] == []
    assert kinds["/account"]["kind"] == "app" and kinds["/account"]["noindex"]
    assert "Pre-rendered 3 page(s)" in res["say"]
    assert "do NOTHING" not in res["say"]                     # every interactive part here is an island
    home = (dist / "index.html").read_text()
    assert "Gentle dental care" in home and "<title>Asha Dental, Nagpur</title>" in home
    assert 'application/ld+json' in home and '"@type":"Dentist"' in home and 'rel="canonical"' in home
    assert 'data-island="components/blocks/faq"' in home
    scripts = re.findall(r'<script type="module"[^>]*src="([^"]+)"', home)
    assert len(scripts) == 1 and "islands-" in scripts[0], scripts   # the islands loader only, never the whole app
    about = (dist / "about" / "index.html").read_text()
    assert "About us" in about and not re.findall(r'<script type="module"', about)   # no islands = no script at all
    acct = (dist / "account" / "index.html").read_text()
    assert "data-hoola-app" in acct and re.findall(r'<script type="module"[^>]*src="[^"]*index-', acct)
    assert (dist / "__spa.html").exists() and '<div id="root"></div>' in (dist / "__spa.html").read_text()
    sm = (dist / "sitemap.xml").read_text()
    assert "__hoola_base__/about" in sm and "account" not in sm


def test_live_site_pages_go_out_at_the_address_sealed_and_filled(ae_env, monkeypatch):
    aid, r, dist, _ = _site_app()
    from app.appengine import service as AE
    monkeypatch.setenv("APP_ENGINE_PUBLISH_CHECKS", "false")   # the scans have their own suite; this is about serving
    from app.config import get_settings
    get_settings.cache_clear()
    AE.publish(T, aid, r.version, confirm=True)
    r = AE._load(T, aid)
    from app.main import app
    c = TestClient(app)
    home = c.get(f"/apps/{r.slug}/")
    assert home.status_code == 200
    csp = home.headers["content-security-policy"]
    assert csp.startswith("sandbox allow-scripts") and "allow-same-origin" not in csp   # its own blank origin
    assert "Gentle dental care" in home.text
    assert "/__hoola_base__" not in home.text and "__hoola_origin__" not in home.text
    assert f'<base href="/apps/{r.slug}/">' in home.text and 'name="hoola-cloud"' in home.text
    assert "shell.js" not in home.text                                        # no frame around a site page
    assert f'href="/apps/{r.slug}/about"' in home.text
    about = c.get(f"/apps/{r.slug}/about")
    assert about.status_code == 200 and "About us" in about.text and about.headers["content-security-policy"].startswith("sandbox")
    acct = c.get(f"/apps/{r.slug}/account")
    assert "shell.js" in acct.text                                            # an app page keeps its sealed frame
    framed = c.get(f"/apps/{r.slug}/__app/account")
    assert "data-hoola-app" in framed.text and not framed.headers["content-security-policy"].startswith("sandbox")
    css = re.search(r'href="\./(assets/[^"]+\.css)"', home.text).group(1)
    a = c.get(f"/apps/{r.slug}/{css}")
    assert a.status_code == 200 and a.headers["access-control-allow-origin"] == "*"
    sm = c.get(f"/apps/{r.slug}/sitemap.xml")
    assert sm.status_code == 200 and f"/apps/{r.slug}/about" in sm.text and "xml" in sm.headers["content-type"]
    assert c.get(f"/apps/{r.slug}/__pages.json").status_code == 404
    assert c.get(f"/apps/{r.slug}/__app/__spa.html").status_code == 404
    unknown = c.get(f"/apps/{r.slug}/__app/some/new/route")
    assert unknown.status_code == 200 and '<div id="root"></div>' in unknown.text   # the plain app page


def test_islands_hydrate_in_a_real_browser_and_the_page_needs_no_script(ae_env):
    aid, r, dist, _ = _site_app()
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        pytest.skip("no Playwright here")
    from app.appengine import speed as SP
    out = SP.walk_dist(dist, ["/", "/about"])
    home, about = out["/"], out["/about"]
    assert home["errors"] == [] and about["errors"] == []
    assert home["h1"] >= 1 and about["h1"] == 1
    assert home["islands_awake"] >= 1                     # the FAQ accordion opens after it woke up
    assert home["faq_opened"]
    assert about["scripts"] == 0
    assert home["nojs_words"] > 200                       # with JavaScript off the page still has all its words


def test_content_pages_pass_core_web_vitals_in_the_lab(ae_env):
    aid, r, dist, _ = _site_app()
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        pytest.skip("no Playwright here")
    from app.appengine import speed as SP
    rep = SP.lab(dist, ["/", "/about"])
    assert rep["verdict"] == "PASS", json.dumps(rep, indent=1)[:3000]
    for p in rep["pages"]:
        assert p["lcp_ms"] <= SP.BUDGET["lcp_ms"] and p["cls"] <= SP.BUDGET["cls"] and p["tbt_ms"] <= SP.BUDGET["tbt_ms"]
        assert p["js_first_kb"] <= SP.BUDGET["site_js_first_kb"] and p["js_kb"] <= SP.BUDGET["site_js_kb"]


def test_speed_lab_wiring():
    from app.appengine import speed as SP
    assert SP.BUDGET["lcp_ms"] == 2500 and SP.BUDGET["cls"] == 0.1 and SP.BUDGET["tbt_ms"] == 200
    ops = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "appengine_speed)" in ops and "python -m app.appengine speed" in ops
    main = (ROOT / "server" / "app" / "appengine" / "__main__.py").read_text()
    assert '"speed"' in main or "'speed'" in main
    agents = (TPL / "AGENTS.md").read_text()
    assert "use client" in agents and "<Seo" in agents and "<AppPage>" in agents
