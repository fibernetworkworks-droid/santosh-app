"""Real logos for plugins and MCP servers: picked from the brand's own site, converted to a 128 px PNG, cached."""
import io
import socket

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image


def _img(size, fmt="PNG", color=(255, 80, 0, 255)):
    im = Image.new("RGBA", (size, size), color)
    buf = io.BytesIO()
    if fmt == "ICO":
        im.save(buf, "ICO", sizes=[(16, 16), (48, 48)])
    else:
        im.save(buf, fmt)
    return buf.getvalue()


@pytest.fixture()
def lg(env, monkeypatch, tmp_path):
    from app.bazar import custom_mcp, logos

    def fake_dns(host, *a, **k):
        ip = "10.0.0.9" if host.startswith("private") else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo", fake_dns)
    monkeypatch.setattr(logos, "CACHE_DIR", tmp_path / "logos")
    return logos


def _client(routes):
    def handle(req: httpx.Request):
        body = routes.get(str(req.url))
        if body is None:
            return httpx.Response(404)
        ctype, data = body
        return httpx.Response(200, headers={"content-type": ctype}, content=data)
    from app.bazar.custom_mcp import check_url
    return httpx.Client(transport=httpx.MockTransport(handle), follow_redirects=True,
                        event_hooks={"request": [lambda r: check_url(str(r.url))]})


def _size(png):
    return Image.open(io.BytesIO(png)).size


def test_takes_the_big_apple_touch_icon(lg):
    c = _client({"https://phonepe.com/apple-touch-icon.png": ("image/png", _img(180)),
                 "https://phonepe.com/favicon.ico": ("image/x-icon", _img(16, "ICO"))})
    png = lg.fetch("domain", "phonepe.com", client=c)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and _size(png) == (128, 128)


def test_falls_back_to_the_homepage_icon_then_favicon(lg):
    html = ('<html><head><link rel="icon" sizes="96x96" href="/static/logo96.png">'
            '<link rel="shortcut icon" href="/favicon.ico"></head></html>').encode()
    c = _client({"https://www.mahadiscom.in/": ("text/html", html),
                 "https://www.mahadiscom.in/static/logo96.png": ("image/png", _img(96)),
                 "https://mahadiscom.in/": ("text/html", b"<html></html>")})
    assert _size(lg.fetch("domain", "mahadiscom.in", client=c)) == (128, 128)
    c2 = _client({"https://sbi.co.in/favicon.ico": ("image/x-icon", _img(48, "ICO"))})
    assert _size(lg.fetch("domain", "sbi.co.in", client=c2)) == (128, 128)     # .ico made into a PNG


def test_html_tiny_and_private_are_refused(lg):
    c = _client({"https://x.example.com/apple-touch-icon.png": ("text/html", b"<html>not found</html>"),
                 "https://x.example.com/favicon.ico": ("image/png", _img(8))})
    assert lg.fetch("domain", "x.example.com", client=c) is None
    c2 = _client({"https://private.example.com/apple-touch-icon.png": ("image/png", _img(180))})
    assert lg.fetch("domain", "private.example.com", client=c2) is None       # never reaches a private address


def test_only_listed_things_have_logos_and_they_are_cached(lg, monkeypatch):
    calls = []

    def fake_fetch(kind, target, client=None):
        calls.append((kind, target))
        return _img(128) if target != "nologo.in" else None
    monkeypatch.setattr(lg, "fetch", fake_fetch)
    monkeypatch.setattr(lg, "_domains", {"phonepe": "phonepe.com", "feat:razorpay": "razorpay.com", "x": "nologo.in"})
    assert lg.resolve("pack", "bakery") is None and lg.resolve("pack", "../etc") is None
    assert lg.logo("pack", "phonepe") and lg.logo("pack", "phonepe")
    assert calls == [("domain", "phonepe.com")]                                # second time from disk
    assert lg.logo("pack", "x") is None and lg.logo("pack", "x") is None
    assert calls.count(("domain", "nologo.in")) == 1                            # a miss is remembered too
    assert lg.resolve("gh", "modelcontextprotocol") == ("url", "https://github.com/modelcontextprotocol.png?size=128")
    assert lg.resolve("gh", "bad/owner") is None
    assert lg.pack_logo("phonepe") == "/api/logo/pack/phonepe" and lg.pack_logo("bakery") is None
    assert lg.featured_logo("razorpay") == "/api/logo/feat/razorpay"
    assert lg.directory_logo("https://github.com/github/github-mcp-server") == "/api/logo/gh/github"
    assert lg.directory_logo("https://www.npmjs.com/package/x") is None
    from app import main
    with TestClient(main.app) as c:
        r = c.get("/api/logo/pack/phonepe")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png" and "max-age" in r.headers["cache-control"]
        assert c.get("/api/logo/pack/bakery").status_code == 404
        assert c.get("/api/logo/evil/phonepe").status_code == 404


def test_lists_carry_logos(env):
    from app.bazar import featured, logos, service
    cat = service.catalog("default")["packs"]
    by = {p["pack_id"]: p for p in cat}
    assert by["phonepe"]["logo"] == "/api/logo/pack/phonepe"
    assert by["msedcl-mahavitaran"]["logo"] and by["msedcl-mahavitaran"]["does"]
    assert by["bakery"]["logo"] is None                                         # a generic shop template: category icon
    with_logo = sum(1 for p in cat if p["logo"])
    assert with_logo >= 470                                                     # every branded plugin (shops / skills get icons)
    f = featured.public(featured.get("razorpay"))
    assert f["logo"] == "/api/logo/feat/razorpay"
    from app.bazar import directory
    hit = directory.search("github", limit=5)[0]
    assert hit["logo"] is None or hit["logo"].startswith("/api/logo/gh/")
    assert all(":" not in d and " " not in d for d in logos.domains().values())
