"""v0.89 The browser opens sites reliably: a page that fails to load is retried by itself and reported as "did not load"
(never as a safety block), NetGuard keeps every safety rule but stops refusing normal sites (mixed DNS answers, gov
portals on odd web ports, a hiccuping DNS), and an optional upstream proxy on the owner's own network carries traffic
for sites that refuse data-centre addresses."""
import asyncio
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

WORKER = Path(__file__).resolve().parents[1] / "browser_worker"


def test_internal_pages_are_not_safety_blocks():
    from app.operator import guard
    for u in ("chrome-error://chromewebdata/", "about:blank", "chrome://newtab/", "data:text/html,hi", "blob:https://x/1"):
        assert guard.page_problem(u) == "", u
    assert guard.load_error("chrome-error://chromewebdata/") and not guard.load_error("https://uidai.gov.in/")
    assert guard.page_problem("http://127.0.0.1:8077/api") and guard.page_problem("http://169.254.169.254/")
    assert guard.url_problem("chrome-error://chromewebdata/")        # still never a place to *open*
    assert guard.site_block("Access Denied", "You don't have permission to access") == "Access Denied"
    assert guard.site_block("Attention Required! | Cloudflare", "") and not guard.site_block("UIDAI", "Download Aadhaar")
    sys.path.insert(0, str(WORKER))
    try:
        import guard as wguard
        assert wguard.page_problem("chrome-error://chromewebdata/") == "" and wguard.site_block("Access Denied")
    finally:
        sys.path.remove(str(WORKER))


def test_netguard_keeps_the_rules_but_opens_normal_sites(monkeypatch):
    from app.operator import netguard
    from app.operator.netguard import NetGuard

    async def go():
        g = NetGuard()
        for host in ("127.0.0.1", "10.0.0.5", "169.254.169.254", "localhost", "[::1]"):
            with pytest.raises(PermissionError):
                await g.resolve(host, 443)
        for port in (22, 25, 3389):
            with pytest.raises(PermissionError):
                await g.resolve("8.8.8.8", port)
        assert await g.resolve("8.8.8.8", 8081) == "8.8.8.8" and await g.resolve("8.8.8.8", 444) == "8.8.8.8"

        async def mixed(h, port):
            return ["10.1.2.3", "fc00::5", "8.8.4.4"]
        g._lookup = mixed
        assert await g.resolve_all("portal.example", 443) == ["8.8.4.4"]      # only the public address is used

        async def only_local(h, port):
            return ["10.1.2.3", "192.168.1.5"]
        g._lookup = only_local
        with pytest.raises(PermissionError):
            await g.resolve_all("rebind.example", 443)
    asyncio.run(go())


def test_dns_hiccup_falls_back_to_dns_over_https(monkeypatch):
    from app.operator import netguard
    from app.operator.netguard import NetGuard
    monkeypatch.setattr(netguard, "_doh", lambda host: ["8.8.8.8"])

    async def go():
        g = NetGuard()
        loop = asyncio.get_running_loop()

        async def broken(*a, **k):
            raise OSError("resolver down")
        monkeypatch.setattr(loop, "getaddrinfo", broken)
        ips = await g.resolve_all("www.example.gov.in", 443)
        return ips, g.stats["doh"]
    ips, doh = asyncio.run(go())
    assert ips == ["8.8.8.8"] and doh == 1


def test_upstream_proxy_carries_the_tunnel(monkeypatch):
    """Her own office proxy: NetGuard checks the target, then asks the upstream for the tunnel (with her login)."""
    from app.operator.netguard import NetGuard
    seen = []

    async def go():
        async def upstream(reader, writer):
            head = await reader.readuntil(b"\r\n\r\n")
            seen.append(head.decode())
            writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
            await writer.drain()
            data = await reader.read(100)
            writer.write(b"echo:" + data)
            await writer.drain()
            writer.close()
        srv = await asyncio.start_server(upstream, "127.0.0.1", 0)
        port = srv.sockets[0].getsockname()[1]
        monkeypatch.setenv("BROWSER_UPSTREAM_PROXY", f"http://meghana:s3cret@127.0.0.1:{port}")
        g = NetGuard()

        async def public(h, p):
            return ["93.184.216.34"]
        g._lookup = public
        r, w = await g.open("site.example", 443)
        w.write(b"hello")
        await w.drain()
        got = await asyncio.wait_for(r.read(100), 5)
        w.close()
        srv.close()
        return got, g.stats["upstream"]
    got, n = asyncio.run(go())
    assert got == b"echo:hello" and n == 1
    assert "CONNECT site.example:443" in seen[0] and "Proxy-Authorization: Basic" in seen[0]
    monkeypatch.setenv("BROWSER_UPSTREAM_HOSTS", "uidai.gov.in")
    from app.operator.netguard import _upstream_for
    assert _upstream_for("myaadhaar.uidai.gov.in") and not _upstream_for("www.google.com")


class _Flaky(BaseHTTPRequestHandler):
    hits: dict = {}

    def do_GET(self):
        n = self.hits[self.path] = self.hits.get(self.path, 0) + 1
        if self.path.startswith("/flaky") and n == 1:
            self.connection.close()            # the first try dies mid-way, like a site that hiccups
            return
        body = {"/": b"<title>Home</title><a href='/flaky'>Status dekho</a>",
                "/blocked": b"<title>Access Denied</title><h1>Access Denied</h1>You don't have permission to access"}.get(
            self.path, b"<title>Status</title><h1>Aapka status: Approved</h1>")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


try:
    import playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False


@pytest.mark.skipif(not HAVE_PW, reason="needs playwright + chromium")
def test_a_site_that_hiccups_still_opens_and_a_firewall_page_is_named(env, tmp_path):
    from app.operator.browser import Operator, OperatorError, fmt_snapshot
    _Flaky.hits = {}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Flaky)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    async def go():
        op = Operator(tmp_path / "op", allow_private=True, screenshots=False)
        try:
            s = await op.session("main")
            r = await op.goto(s, base + "/flaky-direct")            # the first load fails: tried again by itself
            assert "Approved" in r["page"] and _Flaky.hits["/flaky-direct"] >= 2
            await op.goto(s, base + "/")
            page = fmt_snapshot(await op.snapshot(s))
            link = re.search(r"\[(\w+)\] link \"Status dekho", page).group(1)
            r = await op.act(s, "click", link)                      # a click into a load that fails once
            assert "Approved" in str(r.get("page", "")) or "Approved" in fmt_snapshot(await op.snapshot(s))
            r = await op.goto(s, base + "/blocked")
            assert "refused this server" in r.get("site_block", "")
            srv.shutdown()                                          # now the site is really gone
            with pytest.raises(OperatorError) as e:
                await op.goto(s, base + "/flaky-later")
            assert "safety" not in str(e.value).lower() or "not a safety block" in str(e.value)
        finally:
            await op.shutdown()
    asyncio.run(go())
