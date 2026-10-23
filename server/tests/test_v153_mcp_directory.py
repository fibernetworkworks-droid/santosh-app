"""v0.153 MCP directory merged with mcp.so, mcpservers.org and the Apify Store: every server has a clean name, a short
description, a category and an HD logo; addresses the directory knows connect with just the ref; scrapers never connect."""
import io
import re
import socket

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from tests.test_bazar import bz  # noqa: F401  (fixture)


def test_every_server_has_name_short_description_category_logo():
    from app.bazar import directory as d
    cats = set(d.categories())
    seen = set()
    for s in d.servers():
        title, short = s[d.TITLE], s[d.SHORT]
        assert title and len(title) <= 60 and title == title.strip(), s[d.NAME]
        assert 10 <= len(short) <= 141 and short[0] == short[0].upper() and short[-1] in ".!?…。", (s[d.NAME], short)
        assert s[d.FIELD] in cats
        assert re.fullmatch(r"[0-9a-f]{10}", s[d.ID]) and s[d.ID] not in seen
        seen.add(s[d.ID])
    assert len(seen) > 60000
    hit = d.public(d.servers()[123])
    assert hit["logo"] == f"/api/logo/dir/{hit['id']}?v={d.LOGO_VERSION}" and hit["name"] and hit["does"]


def test_names_and_descriptions_are_clean():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import merge_mcp_lists as m
    assert m.clean_title("mcp-server-github", slug=True) == "GitHub"
    assert m.clean_title("@acme/mcp", slug=True) == "Acme"
    assert m.clean_title("iflow-mcp_orly-mcp", "An MCP server for the ORLY tool.", slug=True) == "ORLY"
    assert m.clean_title("CourtListener Legal Data Scraper — No Login, $4/1k") == "CourtListener Legal Data Scraper"
    assert "4.6" in m.clean_title("glm-4.6v-flash-mcp", slug=True)
    assert m.short_desc("A Model Context Protocol (MCP) server that helps AI editors find symbols", "X") == \
        "Helps AI editors find symbols."
    assert m.short_desc("MCP Server for executing PowerShell scripts", "PS") == "Tools for executing PowerShell scripts."
    assert m.short_desc("Mirror of", "X") == "" and m.short_desc("Developer Tools", "X") == ""
    assert m.short_desc("A Universal MCP Application: universal mcp apollo", "Universal Apollo") == ""
    assert m.apify_image("https://images.apifyusercontent.com/sig/rs:fill:76:76/cb:1/"
                         "aHR0cHM6Ly9leGFtcGxlLmNvbS9sb2dvLnBuZw.webp") == "https://example.com/logo.png"
    assert m.mcp_url_ok("https://api.ahrefs.com/mcp/mcp") and not m.mcp_url_ok("https://github.com/x/y")
    assert not m.mcp_url_ok("https://your-server.example.com/mcp") and not m.mcp_url_ok("https://{host}/mcp")


def test_search_finds_the_real_brand_first():
    from app.bazar import directory as d
    for q, want in (("stripe", "Stripe"), ("github", "GitHub"), ("razorpay", "Razorpay")):
        top = d.search(q, limit=3)[0]
        assert top["name"] == want and top["official"], (q, top)
    st = d.stats()
    assert "Crypto & Web3" in st["fields"] and st["hosted"] > 2000


def test_apify_scrapers_and_whatsapp_never_connect(bz, monkeypatch):  # noqa: F811
    from app.bazar import custom_mcp, directory as d, service
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo",
                        lambda h, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    from app.bazar.connectors.base import ToolError
    apify = [s for s in d.servers() if s[d.SRC] == "apify"]
    scraper = next(s for s in apify if d.blocked(s) == "scraper")
    pub = d.public(scraper)
    assert pub["connect"] == "not_allowed" and "official routes" in pub["how_to_connect"]
    with pytest.raises(ToolError, match="scrapes"):
        service.mcp_add("default", "https://x.apify.actor/mcp", ref=scraper[d.NAME])
    usable = next(s for s in apify if not d.blocked(s) and s[d.MCP_URL])
    p = d.public(usable)
    assert p["connect"] == "remote" and p["key_header"] == "Authorization" and "credits" in p["how_to_connect"]


def test_known_address_connects_with_just_the_ref(bz, monkeypatch):  # noqa: F811
    from app.bazar import custom_mcp, directory as d, service
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo",
                        lambda h, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    s = next(x for x in d.servers() if x[d.MCP_URL] and not d.blocked(x) and x[d.SRC] != "apify")
    probe = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    out = service.mcp_add("default", "", ref=s[d.NAME], probe_client=probe)
    assert out["url"].rstrip("/") == s[d.MCP_URL].rstrip("/") and out["name"] == s[d.TITLE]
    lst = service.mcp_list("default")
    assert lst[0]["logo"] == f"/api/logo/dir/{s[d.ID]}?v={d.LOGO_VERSION}"


def _png(size, colors=200):
    im = Image.new("RGB", (size, size))
    px = im.load()
    for y in range(size):
        for x in range(size):
            px[x, y] = ((x * 7) % colors, (y * 5) % 255, (x + y) % 255)
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def test_dir_logo_always_hd(env, monkeypatch, tmp_path):
    from app.bazar import custom_mcp, directory as d, logos
    monkeypatch.setattr(logos, "CACHE_DIR", tmp_path / "logos")
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo",
                        lambda h, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    gh_only = next(s for s in d.servers() if not s[d.LOGO][0] and not s[d.LOGO][1] and s[d.LOGO][2])
    owner = gh_only[d.LOGO][2]
    ident = Image.new("RGB", (420, 420), (240, 240, 240))
    for i in range(0, 420, 84):
        ident.paste((80, 160, 90), (i, i, i + 70, i + 70))
    ib = io.BytesIO()
    ident.save(ib, "PNG")
    routes = {f"https://github.com/{owner}.png?size=256": ib.getvalue()}

    def client():
        def handle(req):
            body = routes.get(str(req.url))
            return httpx.Response(200, headers={"content-type": "image/png"}, content=body) if body else httpx.Response(404)
        return httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(logos, "_client", client)
    # a GitHub default avatar (identicon) is not a logo -> the drawn HD tile
    png = logos.logo("dir", gh_only[d.ID])
    im = Image.open(io.BytesIO(png))
    assert im.size == (256, 256) and png == logos.monogram(gh_only[d.TITLE], gh_only[d.FIELD])
    # a real picture wins (cache of a drawn tile is retried later, not kept forever)
    routes[f"https://github.com/{owner}.png?size=256"] = _png(300)
    drawn = next((logos.CACHE_DIR).glob("*.drawn"))
    import os
    os.utime(drawn, (1, 1))
    png2 = logos.logo("dir", gh_only[d.ID])
    assert png2 != png and Image.open(io.BytesIO(png2)).size == (256, 256)
    from app import main
    with TestClient(main.app) as c:
        r = c.get(f"/api/logo/dir/{gh_only[d.ID]}?v=3")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
        assert c.get("/api/logo/dir/zzzzzzzzzz").status_code == 404
