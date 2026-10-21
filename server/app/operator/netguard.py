"""Copy of server/browser_worker/netguard.py, used by the Computer Operator's Chromium too.

A tiny HTTP proxy in front of Santosh's Chromium: every request (pages, images, scripts, websockets) goes
through it, and only public internet addresses are reached. Local services on the VPS (Santosh itself, OmniRoute,
databases, cloud metadata) can't be touched by a web page, even through redirects or DNS tricks: the proxy
resolves the name itself and connects to the checked IP."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket

log = logging.getLogger("santosh.browser.net")

ALLOWED_PORTS = {80, 443, 8080, 8443}


def port_ok(port: int) -> bool:
    return port in ALLOWED_PORTS
_BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "web.whatsapp.com"}


class NetGuard:
    def __init__(self, allow_private: bool = False):
        self.allow_private = allow_private   # tests only
        self.server: asyncio.base_events.Server | None = None
        self.port = 0
        self.blocked: list[str] = []
        self.failed: list[str] = []      # sites that could not be reached from this server (DNS / timeout / refused)

    async def start(self) -> int:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
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

    async def resolve_all(self, host: str, port: int) -> list[str]:
        """Every checked IP for this host, IPv4 first (many servers have no working IPv6), or PermissionError."""
        h = host.strip("[]").lower().rstrip(".")
        if not port_ok(port) and not self.allow_private:
            raise PermissionError(f"port {port}")
        if h in _BLOCKED_HOSTS and not (self.allow_private and h == "localhost"):
            raise PermissionError(h)
        try:
            ips = [ipaddress.ip_address(h)]
        except ValueError:
            try:
                infos = await asyncio.wait_for(
                    asyncio.get_running_loop().getaddrinfo(h, port, type=socket.SOCK_STREAM), 15)
            except Exception as e:
                raise LookupError(f"{h}: name not found (DNS: {type(e).__name__})") from None
            ips = list(dict.fromkeys(ipaddress.ip_address(i[4][0].split("%")[0]) for i in infos))
        if not ips:
            raise LookupError(f"{h}: no address")
        if not self.allow_private and not all(ip.is_global for ip in ips):
            raise PermissionError(f"{h} is a local address")
        ips.sort(key=lambda ip: ip.version)   # IPv4 first
        return [str(ip) for ip in ips]

    async def open(self, host: str, port: int):
        """Connect to the first reachable checked address (short timeout per address)."""
        last: Exception | None = None
        for ip in (await self.resolve_all(host, port))[:6]:
            try:
                return await asyncio.wait_for(asyncio.open_connection(ip, port), 12)
            except Exception as e:   # timeout / unreachable (e.g. IPv6 on a v4-only VPS): try the next one
                last = e
        why = "timed out" if isinstance(last, asyncio.TimeoutError) else (type(last).__name__ if last else "unreachable")
        raise ConnectionError(f"{host}:{port} did not answer this server ({why})")

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
                from urllib.parse import urlsplit
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
            w.close()
        except Exception:
            pass
