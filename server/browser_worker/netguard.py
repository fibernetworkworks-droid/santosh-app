"""A tiny HTTP proxy in front of Santosh's Chromium: every request (pages, images, scripts, websockets) goes
through it, and only public internet addresses are reached. Local services on the VPS (Santosh itself, OmniRoute,
databases, cloud metadata) can't be touched by a web page, even through redirects or DNS tricks: the proxy
resolves the name itself and connects to the checked IP.

v0.89 reliability (the safety rule is unchanged: never a local / private address):
  * a name whose DNS answer mixes public and non-public addresses uses its public ones (it used to be refused whole)
  * any web port of a public address (gov portals on :8081, :9443, :444 ...); only mail / remote-login ports refused
  * DNS: the server's resolver, one retry, then DNS-over-HTTPS (Cloudflare / Google, by IP) when it fails; answers
    cached 5 minutes per browser
  * connect: every address (IPv4 first), 10 s each, and the whole try once more after a short pause
  * optional upstream: BROWSER_UPSTREAM_PROXY=http://user:pass@host:port sends the traffic out through the owner's own
    network (e.g. a small proxy on her office broadband) for sites that refuse data-centre addresses; the checks above
    still run first. BROWSER_UPSTREAM_HOSTS=uidai.gov.in,irctc.co.in limits it to those sites (and their subdomains).
"""
from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import logging
import os
import socket
import ssl
import time
import urllib.request
from urllib.parse import unquote, urlsplit

log = logging.getLogger("santosh.browser.net")

# mail / remote-login / file-share ports are never opened from the browser; every other port of a public address is fine
DENIED_PORTS = {0, 21, 22, 23, 25, 110, 135, 137, 138, 139, 143, 445, 465, 587, 993, 995, 1433, 3306, 3389, 5432, 5900, 6379}
CONNECT_TIMEOUT = 10
DNS_TTL = 300
DOH = (("1.1.1.1", "cloudflare-dns.com"), ("8.8.8.8", "dns.google"))


def port_ok(port: int) -> bool:
    return 0 < port < 65536 and port not in DENIED_PORTS and (port >= 80)


_BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "web.whatsapp.com"}


def _upstream() -> tuple[str, int, str] | None:
    raw = (os.environ.get("BROWSER_UPSTREAM_PROXY") or "").strip()
    if not raw:
        return None
    u = urlsplit(raw if "://" in raw else "http://" + raw)
    if not u.hostname:
        return None
    auth = ""
    if u.username:
        auth = base64.b64encode(f"{unquote(u.username)}:{unquote(u.password or '')}".encode()).decode()
    return u.hostname, u.port or 3128, auth


def _upstream_for(host: str) -> tuple[str, int, str] | None:
    up = _upstream()
    if not up:
        return None
    only = [h.strip().lower().lstrip(".") for h in (os.environ.get("BROWSER_UPSTREAM_HOSTS") or "").split(",") if h.strip()]
    h = host.lower().rstrip(".")
    if only and not any(h == d or h.endswith("." + d) for d in only):
        return None
    return up


def _doh(host: str) -> list[str]:
    """DNS over HTTPS by IP (no system resolver needed). A and AAAA answers, IPv4 first."""
    out: list[str] = []
    ctx = ssl.create_default_context()
    for ip, name in DOH:
        for qtype in ("A", "AAAA"):
            url = f"https://{ip}/dns-query?name={host}&type={qtype}" if name == "cloudflare-dns.com" else \
                f"https://{ip}/resolve?name={host}&type={qtype}"
            try:
                req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
                with urllib.request.urlopen(req, timeout=6, context=ctx) as r:   # noqa: S310 (fixed public resolvers)
                    data = json.loads(r.read(200_000))
                for a in data.get("Answer") or []:
                    if a.get("type") in (1, 28):
                        out.append(str(a.get("data", "")).strip())
            except Exception:
                continue
        if out:
            break
    return [x for x in dict.fromkeys(out) if x]


class NetGuard:
    def __init__(self, allow_private: bool = False):
        self.allow_private = allow_private   # tests only
        self.server: asyncio.base_events.Server | None = None
        self.port = 0
        self.blocked: list[str] = []
        self.failed: list[str] = []      # sites that could not be reached from this server (DNS / timeout / refused)
        self._dns: dict[str, tuple[float, list[str]]] = {}
        self.stats = {"connects": 0, "retries": 0, "doh": 0, "upstream": 0, "failed": 0}

    async def start(self) -> int:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0, limit=1 << 20)
        self.port = self.server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            try:
                await asyncio.wait_for(self.server.wait_closed(), 2)
            except Exception:
                pass

    def chrome_args(self) -> list[str]:
        return [f"--proxy-server=http://127.0.0.1:{self.port}", "--proxy-bypass-list=<-loopback>",
                "--force-webrtc-ip-handling-policy=disable_non_proxied_udp", "--webrtc-ip-handling-policy=disable_non_proxied_udp"]

    def last_failure(self, host: str = "") -> str:
        """The newest 'could not reach' line (for this host when given)."""
        for f in reversed(self.failed):
            if not host or host.lower() in f.lower():
                return f
        return ""

    async def _lookup(self, h: str, port: int) -> list[str]:
        hit = self._dns.get(h)
        if hit and time.time() - hit[0] < DNS_TTL:
            return hit[1]
        loop = asyncio.get_running_loop()
        found: list[str] = []
        for attempt in range(2):
            try:
                infos = await asyncio.wait_for(loop.getaddrinfo(h, port, type=socket.SOCK_STREAM), 8)
                found = [i[4][0].split("%")[0] for i in infos]
                if found:
                    break
            except Exception:
                await asyncio.sleep(0.3 * (attempt + 1))
        if not found:   # the server's DNS failed or hiccuped: ask a public DNS-over-HTTPS resolver directly
            found = await asyncio.to_thread(_doh, h)
            if found:
                self.stats["doh"] += 1
        if not found:
            raise LookupError(f"{h}: name not found (DNS)")
        found = list(dict.fromkeys(found))
        self._dns[h] = (time.time(), found)
        return found

    async def resolve_all(self, host: str, port: int) -> list[str]:
        """Every checked public IP for this host, IPv4 first, or PermissionError / LookupError."""
        h = host.strip("[]").lower().rstrip(".")
        if not port_ok(port) and not self.allow_private:
            raise PermissionError(f"port {port}")
        if h in _BLOCKED_HOSTS and not (self.allow_private and h == "localhost"):
            raise PermissionError(h)
        try:
            ips = [ipaddress.ip_address(h)]
        except ValueError:
            ips = [ipaddress.ip_address(x) for x in await self._lookup(h, port)]
        if not ips:
            raise LookupError(f"{h}: no address")
        if not self.allow_private:
            public = [ip for ip in ips if ip.is_global]
            if not public:
                raise PermissionError(f"{h} is a local address")
            ips = public          # only ever connect to the public ones
        ips.sort(key=lambda ip: ip.version)   # IPv4 first
        return [str(ip) for ip in ips]

    async def _direct(self, host: str, port: int):
        last: Exception | None = None
        for attempt in range(2):
            for ip in (await self.resolve_all(host, port))[:6]:
                try:
                    self.stats["connects"] += 1
                    return await asyncio.wait_for(asyncio.open_connection(ip, port, limit=1 << 20), CONNECT_TIMEOUT)
                except Exception as e:   # timeout / unreachable (e.g. IPv6 on a v4-only VPS): try the next one
                    last = e
            if attempt == 0:
                self.stats["retries"] += 1
                self._dns.pop(host.lower(), None)
                await asyncio.sleep(0.6)
        why = "timed out" if isinstance(last, asyncio.TimeoutError) else (type(last).__name__ if last else "unreachable")
        raise ConnectionError(f"{host}:{port} did not answer this server ({why})")

    async def _via_upstream(self, up: tuple[str, int, str], host: str, port: int):
        """A tunnel to host:port through the owner's own proxy (after our own public-address check)."""
        await self.resolve_all(host, port)                 # same rules first: never a local / private target
        uh, upt, auth = up
        r, w = await asyncio.wait_for(asyncio.open_connection(uh, upt, limit=1 << 20), CONNECT_TIMEOUT)
        req = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n"
        if auth:
            req += f"Proxy-Authorization: Basic {auth}\r\n"
        w.write((req + "\r\n").encode("latin-1"))
        await w.drain()
        head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 20)
        status = head.split(b"\r\n", 1)[0]
        if b" 200" not in status:
            w.close()
            raise ConnectionError(f"{host}:{port}: upstream proxy said {status.decode('latin-1', 'replace')[:60]}")
        self.stats["upstream"] += 1
        return r, w

    async def open(self, host: str, port: int):
        """Connect to the first reachable checked address (or through the owner's upstream proxy)."""
        up = _upstream_for(host)
        if up:
            try:
                return await self._via_upstream(up, host, port)
            except PermissionError:
                raise
            except Exception as e:
                log.info("upstream proxy failed for %s (%s); trying direct", host, e)
        return await self._direct(host, port)

    async def resolve(self, host: str, port: int) -> str:
        """The one IP to connect to, or raise PermissionError."""
        return (await self.resolve_all(host, port))[0]

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 30)
        except Exception:
            writer.close()
            return
        lines = head.decode("latin-1").split("\r\n")
        try:
            method, target, version = lines[0].split(" ", 2)
        except ValueError:
            writer.close()
            return
        try:
            if method.upper() == "CONNECT":
                host, _, port_s = target.rpartition(":")
                port = int(port_s or 443)
                r2, w2 = await self.open(host, port)
                writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
                await writer.drain()
            else:
                u = urlsplit(target)
                if u.scheme != "http" or not u.hostname:
                    raise PermissionError("bad request")
                port = u.port or 80
                r2, w2 = await self.open(u.hostname, port)
                path = (u.path or "/") + (f"?{u.query}" if u.query else "")
                keep = [ln for ln in lines[1:] if ln and not ln.lower().startswith(("proxy-", "connection:", "keep-alive:"))]
                req = f"{method} {path} {version}\r\n" + "\r\n".join(keep) + "\r\nConnection: close\r\n\r\n"
                w2.write(req.encode("latin-1"))
                await w2.drain()
        except PermissionError as e:
            self.blocked.append(str(e))
            del self.blocked[:-50]
            log.info("blocked %s %s (%s)", method, target, e)
            try:
                writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                await writer.drain()
            finally:
                writer.close()
            return
        except Exception as e:
            self.failed.append(str(e)[:200])
            del self.failed[:-50]
            self.stats["failed"] += 1
            log.info("proxy could not reach %s: %s", target, e)
            try:
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                await writer.drain()
            finally:
                writer.close()
            return
        await asyncio.gather(_pipe(reader, w2), _pipe(r2, writer), return_exceptions=True)


async def _pipe(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await r.read(65536)
            if not data:
                break
            w.write(data)
            await w.drain()
    except Exception:
        pass
    finally:
        try:
            if w.can_write_eof():
                w.write_eof()           # half-close: let the other side finish sending its answer
            else:
                w.close()
        except Exception:
            try:
                w.close()
            except Exception:
                pass
