"""The Hoola website on the Hoola server: home / Employee / Network pages, a Console button on every page,
downloads always the newest APK, strict CSP (no inline script, everything from this server), old web chat at /chat."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SITE = Path(__file__).resolve().parents[1] / "app" / "static" / "site"


@pytest.fixture
def web(env):
    from app import main
    with TestClient(main.app) as c:
        yield c


@pytest.mark.parametrize("path,slug", [("/", "home"), ("/employee", "employee"), ("/network", "network")])
def test_pages_have_console_and_strict_csp(web, path, slug):
    r = web.get(path)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    html = r.text
    assert "Hoola" in html
    # the Console option in the header, the menu and the closing call to action
    assert html.count('href="/console/"') >= 3
    assert 'class="cbtn" href="/console/"' in html
    csp = r.headers["content-security-policy"]
    assert "script-src 'self';" in csp and "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    assert r.headers["x-frame-options"] == "DENY"
    # no inline script; every script is served by this server
    tags = re.findall(r"<script[^>]*>", html)
    assert tags and all(re.search(r'src="/static/site/', t) for t in tags)
    for src in re.findall(r'<script[^>]*src="([^"]+)"', html):
        assert web.get(src).status_code == 200, src
    assert web.get("/static/site/site.css").status_code == 200
    # nothing from cdnjs, no fixed old APK link
    assert "cdnjs" not in html and "app-release.apk" not in html and "v0.119" not in html
    assert 'href="/download"' in html
    # links between pages go to server routes that work
    for href in set(re.findall(r'href="(/[a-z]*/?)"', html)):
        if href in ("/download",):
            continue
        assert web.get(href).status_code == 200, href
    assert 'href="index.html"' not in html and 'href="network.html"' not in html and 'href="employee.html"' not in html


def test_home_has_the_console_section(web):
    html = web.get("/").text
    assert 'id="console"' in html and "Open Hoola Console" in html
    assert html.index('id="console"') < html.index('id="get"')        # just before the last download call


def test_download_is_always_the_newest_apk(web, monkeypatch):
    from app import appupdate
    monkeypatch.setattr(appupdate, "latest", lambda force=False: {
        "apk_url": "https://github.com/fibernetworkworks-droid/santosh-app/releases/download/v0.146.0-b250/app-release.apk"})
    r = web.get("/download", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].endswith("/v0.146.0-b250/app-release.apk")
    # GitHub unreachable -> the releases page; a strange url is never followed
    monkeypatch.setattr(appupdate, "latest", lambda force=False: None)
    assert web.get("/download", follow_redirects=False).headers["location"].endswith("/santosh-app/releases")
    monkeypatch.setattr(appupdate, "latest", lambda force=False: {"apk_url": "https://evil.example/app.apk"})
    assert "evil" not in web.get("/download", follow_redirects=False).headers["location"]


def test_old_web_chat_moved_and_console_links_back(web):
    assert web.get("/chat").status_code == 200 and "<title>Santosh</title>" in web.get("/chat").text
    assert 'href="/"' in web.get("/console/").text


def test_site_scripts_are_plain_files():
    for slug in ("home", "employee", "network"):
        js = (SITE / f"{slug}.js").read_text()
        assert "eval(" not in js and "new Function" not in js
    assert (SITE / "vendor" / "gsap.min.js").read_text().startswith("/*!\n * GSAP 3.12.5")
