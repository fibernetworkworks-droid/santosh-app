"""v0.160 Hoola Console Build studio: the console page loads the studio (build.js + QR + the studio panel), the files are
served, and the website / app previews can be shown in the console's sandboxed frame (opaque origin -> CORS on their files)."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

STATIC = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def test_console_page_loads_the_build_studio(env):
    from app.main import app
    c = TestClient(app)
    html = c.get("/console/").text
    assert 'id="studio"' in html and 'id="studioBtn"' in html
    order = [m.group(1) for m in re.finditer(r'<script src="/static/console/([\w/.-]+)\?', html)]
    # v0.170: /console/ serves the v2 shell (v2.js); the same build studio rides along in the same order
    assert order.index("vendor/qrcode.js") < order.index("build.js") < order.index("v2.js")
    for f in ("build.js", "vendor/qrcode.js", "app.js", "app.css", "v2.js", "v2.css"):
        r = c.get(f"/static/console/{f}")
        assert r.status_code == 200 and len(r.content) > 1000, f
    csp = c.get("/console/").headers["content-security-policy"]
    # same-server preview frames are allowed (frame-src 'self' blob:), but nobody else may frame the console
    assert "default-src 'self'" in csp and "frame-src 'self' blob:" in csp and "frame-ancestors 'none'" in csp
    js = (STATIC / "build.js").read_text()
    # previews run without same-origin (they can't read the console's login); only our own preview paths are framed
    assert 'allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox' in js and "allow-same-origin" not in js
    assert r"^\/api\/(site|app)-preview\/[\w-]+\/$" in js
    for kind in ("site_board", "app_board", "app_android"):
        assert f"'{kind}'" in js
    app_js = (STATIC / "v2.js").read_text()
    assert "B.kinds.has(kind)" in app_js and "renderCard(ev.kind, p, ev.at, true)" in app_js
    # the previous console stays reachable and unchanged behind ?legacy=1
    old = c.get("/console/?legacy=1").text
    assert 'id="studio"' in old and "app.js" in old


def test_previews_allow_the_console_frame(env, monkeypatch):
    from app.main import app
    from app.site import service as S
    from app.appmaker import service as A
    hdr = {"Content-Security-Policy": "default-src 'self'; frame-ancestors *", "X-Robots-Tag": "noindex, nofollow"}
    monkeypatch.setattr(S, "preview_file", lambda token, path: (b"wOF2", "font/woff2", dict(hdr)))
    monkeypatch.setattr(A, "preview_file", lambda token, path: (b"<!doctype html>", "text/html", dict(hdr)))
    c = TestClient(app)
    for u in ("/api/site-preview/tok123/fonts/a.woff2", "/api/app-preview/tok123/?r=2"):
        r = c.get(u)
        assert r.status_code == 200, u
        assert r.headers["access-control-allow-origin"] == "*" and "frame-ancestors *" in r.headers["content-security-policy"]
        assert r.headers["x-robots-tag"] == "noindex, nofollow" and "x-frame-options" not in r.headers
