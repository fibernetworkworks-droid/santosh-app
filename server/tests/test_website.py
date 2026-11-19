"""The Hoola website (v0.999.30 HOOLA WEBSITE): nine pages in the console's design, a Console way in on every page,
downloads always the newest APK, strict CSP (no inline script, everything from this server), one shared script that
plays only on screen and stands still for reduced motion, the old web chat at /chat."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SITE = Path(__file__).resolve().parents[1] / "app" / "static" / "site"
PAGES = [("/", "home"), ("/employee", "employee"), ("/tools", "tools"), ("/studio", "studio"), ("/websites", "websites"),
         ("/code", "code"), ("/computer", "computer"), ("/network", "network"), ("/pricing", "pricing")]


@pytest.fixture
def web(env):
    from app import main
    with TestClient(main.app) as c:
        yield c


@pytest.mark.parametrize("path,slug", PAGES)
def test_pages_have_console_and_strict_csp(web, path, slug):
    r = web.get(path)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    html = r.text
    assert "<title>" in html and "Hoola" in html and '<html lang="en">' in html
    assert re.search(r'<meta name="description" content="[^"]{40,}">', html)
    # the Console way in: the header button, the menu and the closing call to action
    assert html.count('href="/console/"') >= 3
    assert 'class="btn ghost sm signin cbtn" href="/console/"' in html
    csp = r.headers["content-security-policy"]
    assert "script-src 'self';" in csp and "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    assert r.headers["x-frame-options"] == "DENY"
    # one script, from this server, no inline script, no inline handlers
    tags = re.findall(r"<script[^>]*>", html)
    assert tags == ['<script src="/static/site/site.js?v=site29" defer>']
    assert not re.search(r"\son[a-z]+=", html)
    assert web.get("/static/site/site.js").status_code == 200 and web.get("/static/site/site.css").status_code == 200
    assert "cdnjs" not in html and "app-release.apk" not in html and "gsap" not in html.lower()
    assert 'href="/download"' in html
    # every link between pages goes to a server route that answers (redirects followed)
    for href in set(re.findall(r'href="(/[a-z]*/?)(?:#[a-z-]+)?"', html)):
        if href == "/download":
            continue
        assert web.get(href).status_code == 200, href
    # the page marks itself in the menu (Create Studio sits under Tools)
    here = {"home": "/", "studio": "/tools"}.get(slug, path)
    assert f'<a href="{here}" aria-current="page">' in html
    # only English on the page a visitor reads, except the one Hinglish line she speaks on a call
    assert "Kya " not in html and "Haan," not in html


def test_home_has_the_console_section_and_the_moving_parts(web):
    html = web.get("/").text
    assert 'id="console"' in html and "Open Hoola Console" in html
    assert html.index('id="console"') < html.index('id="get"')        # just before the last download call
    for part in ("data-hero", "data-switch", 'role="tablist"', "data-site", "data-phone", "data-code", "data-board", "data-pc",
                 "data-voice", 'id="tiersel"', '<template id="payCard">'):
        assert part in html, part
    # the first frame is complete without any script: the reply and the payment card are in the HTML
    assert "₹1,840" in html and "Slide to pay" in html and "Worked for 41s" in html


def test_apps_moved_into_websites(web):
    r = web.get("/apps", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/websites#app-studio"
    w = web.get("/websites").text
    assert 'id="app-studio"' in w and 'href="/console/web"' in w and 'href="/console/apps"' in w


def test_pricing_matches_the_credit_plans(web):
    """Every price and credit amount on the page is the one the server sells (credits/plans.py), India and the world."""
    from app.credits import plans as P
    html = web.get("/pricing").text
    panels = {r: html[html.index(f'data-of="region" data-panel="{r}"'):] for r in ("in", "world")}
    cur = {"in": "₹", "world": "$"}
    num = lambda v: f"{v:,.2f}" if v != int(v) else f"{int(v):,}"
    for r in ("in", "world"):
        for plan in P.PLANS.values():
            assert f"{cur[r]}{num(plan['price'][r])}" in panels[r], (r, plan["name"])
            assert f"{num(plan['credits'][r])} credits" in panels[r], (r, plan["name"])
        for t in P.TOPUPS.values():
            assert f"{num(t['credits'])} for {cur[r]}{num(t['price'][r])}" in panels[r], (r, t)
    packs = html[html.index("AI-employee packages"):]
    for r in ("in", "world"):
        for pk in P.PACKS.values():
            assert f"{cur[r]}{num(pk['price'][r])}" in packs and f"{pk['jobs']} jobs" in packs, (r, pk["name"])


def test_tools_link_into_the_console_studios(web):
    html = web.get("/tools").text
    assert html.count('class="tool"') == 12
    for href in ("/console/web", "/console/apps", "/console/code", "/studio", "/console/design", "/console/games",
                 "/console/flow", "/console/prompting", "/console/?v=creative", "/console/?v=vocal", "/console/?v=interactive",
                 "/console/?v=connectors"):
        assert f'href="{href}"' in html, href


def test_download_is_always_the_newest_apk(web, monkeypatch):
    from app import appupdate
    monkeypatch.setattr(appupdate, "latest", lambda force=False: {
        "apk_url": "https://github.com/fibernetworkworks-droid/santosh-app/releases/download/v0.146.0-b250/app-release.apk"})
    r = web.get("/download", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].endswith("/v0.146.0-b250/app-release.apk")
    monkeypatch.setattr(appupdate, "latest", lambda force=False: None)
    assert web.get("/download", follow_redirects=False).headers["location"].endswith("/santosh-app/releases")
    monkeypatch.setattr(appupdate, "latest", lambda force=False: {"apk_url": "https://evil.example/app.apk"})
    assert "evil" not in web.get("/download", follow_redirects=False).headers["location"]


def test_old_web_chat_moved_and_console_links_back(web):
    assert web.get("/chat").status_code == 200 and "<title>Santosh</title>" in web.get("/chat").text
    assert 'href="/"' in web.get("/console/").text


def test_one_plain_script_that_respects_reduced_motion():
    js = (SITE / "site.js").read_text()
    assert "eval(" not in js and "new Function" not in js and "innerHTML = location" not in js
    assert "prefers-reduced-motion" in js and "IntersectionObserver" in js and "visibilityState" in js
    # the old per-page scripts and the animation library are gone
    for old in ("home.js", "employee.js", "network.js", "studio.js", "websites.js", "apps.js", "vendor/gsap.min.js"):
        assert not (SITE / old).exists(), old


def test_styles_follow_the_console_design():
    css = (SITE / "site.css").read_text()
    for token in ("--acc:#5B45E0", "--ink:#1B1A17", "Literata", "Schibsted Grotesk", "JetBrains Mono",
                  "prefers-reduced-motion:reduce", '[data-theme="dark"]', "safe-area-inset"):
        assert token in css, token
