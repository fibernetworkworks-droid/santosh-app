"""Hoola Code Phase 6 - the box's ONLY way out: an allow-list proxy (docs/HOOLA_CODE_WEB_PLAN.md; owner: "GO PHASE 6").

ONE FILE, standard library only, because it runs in two places: inside its own small container beside the boxes on her
server (`python3 /proxy/netproxy.py --dir /rules`), and inside the tests as a thread. A box that is given the network is
put on a Docker network with NO route out; this proxy is the one thing on that network that also has a route. So:

- A box talks to the proxy with a per-command id + secret (`Proxy-Authorization`). The rule file of that id
  (`<dir>/runs/<id>.json`, written by the server, removed when the command ends) says which hosts THAT command may reach.
- Only `CONNECT host:443` and plain `http://host:80/` are served. A host that is not on the list gets a 403 that names
  it. An IP address instead of a name is refused. After the name is resolved, a private / loopback / link-local address
  is refused too - so a box can never reach her own server, the Docker host or a cloud metadata address through here.
- SECRETS STAY OUTSIDE THE BOX: for a host that has a secret in the rule, the proxy answers the box's TLS itself (a
  certificate for that one host, signed by this server's own lab CA, which the box is told to trust), adds the header
  with the secret, and makes the real, verified TLS connection to the host. The box sends the request without the
  secret and never sees it. A secret is never added to a plain http:// request.

What this file does NOT do: it does not look inside any other HTTPS traffic (hosts without a secret are tunnelled
untouched), it keeps no log of bodies, and it never follows a redirect on the box's behalf."""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import socket
import ssl
import subprocess
import tempfile
import time
from typing import Any

HOST_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
ID_RE = re.compile(r"^[a-f0-9]{12,40}$")
HEAD_MAX = 32768
DROP = ("proxy-authorization", "proxy-connection", "connection", "keep-alive")
CGNAT = ipaddress.ip_network("100.64.0.0/10")


def host_ok(host: str, allow: list[str]) -> bool:
    """`host` is on the list: an exact name, or a `*.example.com` entry that covers its subdomains (not the bare name)."""
    host = (host or "").lower().rstrip(".")
    for a in allow or []:
        a = str(a).lower().strip()
        if a == "*" or a == host or (a.startswith("*.") and host.endswith(a[1:]) and len(host) > len(a) - 1):
            return True
    return False


def public_ip(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if getattr(a, "ipv4_mapped", None):
        a = a.ipv4_mapped
    return not (a.is_private or a.is_loopback or a.is_link_local or a.is_multicast or a.is_reserved or a.is_unspecified
                or (a.version == 4 and a in CGNAT))


def is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


class Proxy:
    def __init__(self, rules_dir: str, upstream_ctx: ssl.SSLContext | None = None, resolve: Any = None,
                 allow_private: bool = False, ports: tuple[int, int] = (443, 80)):
        self.dir = rules_dir
        self.upstream_ctx = upstream_ctx or ssl.create_default_context()
        self.resolve = resolve                    # tests point a name at a local server; None = real DNS
        self.allow_private = allow_private        # tests only: their servers live on 127.0.0.1
        self.tls_port, self.http_port = ports     # tests only: their servers are not on 443 / 80
        self.certs: dict[str, ssl.SSLContext] = {}
        self.tmp = tempfile.mkdtemp(prefix="hoola-proxy-")
        self.stats = {"allowed": 0, "refused": 0, "injected": 0}

    # ------------------------------------------------------------ who is asking
    def rule(self, head: dict[str, str]) -> dict[str, Any] | None:
        auth = head.get("proxy-authorization", "")
        if not auth.lower().startswith("basic "):
            return None
        try:
            rid, _, secret = base64.b64decode(auth[6:].strip()).decode().partition(":")
        except Exception:
            return None
        if not ID_RE.match(rid):
            return None
        try:
            with open(os.path.join(self.dir, "runs", rid + ".json"), encoding="utf-8") as f:
                rule = json.load(f)
        except (OSError, ValueError):
            return None
        want = str(rule.get("key") or "")
        got = hashlib.sha256(secret.encode()).hexdigest()
        if not want or not hmac.compare_digest(want, got) or float(rule.get("until") or 0) < time.time():
            return None
        return rule

    # ------------------------------------------------------------ a certificate for ONE host, signed by the lab CA
    def cert_for(self, host: str) -> ssl.SSLContext:
        if host in self.certs:
            return self.certs[host]
        if not HOST_RE.match(host):
            raise ValueError("bad host")
        ca, cakey = os.path.join(self.dir, "ca.pem"), os.path.join(self.dir, "ca.key")
        base = os.path.join(self.tmp, hashlib.sha256(host.encode()).hexdigest()[:24])
        key, csr, crt, ext = base + ".key", base + ".csr", base + ".crt", base + ".ext"
        with open(ext, "w", encoding="utf-8") as f:
            f.write(f"subjectAltName=DNS:{host}\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth\n")
        run = lambda *a: subprocess.run(a, check=True, capture_output=True, timeout=30)   # noqa: E731
        run("openssl", "req", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes", "-keyout", key,
            "-subj", f"/CN={host}", "-out", csr)
        run("openssl", "x509", "-req", "-in", csr, "-CA", ca, "-CAkey", cakey, "-set_serial", str(secrets.randbits(63)),
            "-days", "7", "-extfile", ext, "-out", crt)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(crt, key)
        ctx.set_alpn_protocols(["http/1.1"])
        for p in (key, csr, ext):
            try:
                os.unlink(p)
            except OSError:
                pass
        self.certs[host] = ctx
        return ctx

    # ------------------------------------------------------------ one connection from a box
    async def _head(self, reader: asyncio.StreamReader) -> tuple[str, dict[str, str], list[tuple[str, str]]]:
        raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 20)
        if len(raw) > HEAD_MAX:
            raise ValueError("head too big")
        lines = raw.decode("latin-1").split("\r\n")
        pairs = [(k.strip(), v.strip()) for k, _, v in (ln.partition(":") for ln in lines[1:] if ln)]
        return lines[0], {k.lower(): v for k, v in pairs}, pairs

    async def _say(self, writer: asyncio.StreamWriter, code: int, why: str, extra: str = "") -> None:
        body = f"hoola proxy: {why}\n".encode()
        words = {403: "Forbidden", 407: "Proxy Authentication Required", 400: "Bad Request", 502: "Bad Gateway"}.get(code, "Error")
        writer.write(f"HTTP/1.1 {code} {words}\r\nContent-Type: text/plain\r\nContent-Length: {len(body)}\r\n"
                     f"Connection: close\r\n{extra}\r\n".encode() + body)
        try:
            await writer.drain()
        except ConnectionError:
            pass

    async def _where(self, host: str, port: int) -> str | None:
        """The address to connect to, or None when the name leads somewhere a box must never reach."""
        if self.resolve is not None:
            got = self.resolve(host, port)
            ips = [got] if isinstance(got, str) else list(got or [])
        else:
            try:
                infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
            except OSError:
                return None
            ips = [i[4][0] for i in infos]
        for ip in ips:
            if self.allow_private or public_ip(ip):
                return ip
        return None

    @staticmethod
    async def _pipe(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
        try:
            while True:
                b = await r.read(65536)
                if not b:
                    break
                w.write(b)
                await w.drain()
        except (ConnectionError, asyncio.CancelledError, ssl.SSLError, OSError):
            pass
        finally:
            try:
                w.close()
            except Exception:
                pass

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        up_w = None
        try:
            first, head, pairs = await self._head(reader)
            method, target, _ = (first.split(" ") + ["", ""])[:3]
            rule = self.rule(head)
            if rule is None:
                return await self._say(writer, 407, "this command was not given the network", 'Proxy-Authenticate: Basic realm="hoola"\r\n')
            if method.upper() == "CONNECT":
                host, _, port_s = target.rpartition(":")
                tls, path = True, ""
            else:
                m = re.match(r"^http://([^/:]+)(?::(\d+))?(/.*)?$", target, re.I)
                if not m:
                    return await self._say(writer, 400, "only http:// and https:// addresses are served")
                host, port_s, path, tls = m.group(1), m.group(2) or "80", m.group(3) or "/", False
            host = host.lower().strip("[]").rstrip(".")
            port = int(port_s) if port_s.isdigit() else 0
            if is_ip(host) or not HOST_RE.match(host):
                self.stats["refused"] += 1
                return await self._say(writer, 403, "use a host name, not an address")
            if port != (self.tls_port if tls else self.http_port) and port not in ((443,) if tls else (80,)):
                self.stats["refused"] += 1
                return await self._say(writer, 403, f"port {port} is not served (https is 443, http is 80)")
            inject = (rule.get("inject") or {}).get(host) if tls else None
            if not host_ok(host, list(rule.get("allow") or [])) and not inject:
                self.stats["refused"] += 1
                print(f"refused {host}", flush=True)
                return await self._say(writer, 403, f"{host} is not on this repo's allowed list. Its owner can add it in Hoola Code > Settings.")
            ip = await self._where(host, port)
            if ip is None:
                self.stats["refused"] += 1
                return await self._say(writer, 403, f"{host} does not lead to a public address")
            self.stats["allowed"] += 1
            if tls and not inject:                                    # an ordinary tunnel: nothing is read, nothing is changed
                up_r, up_w = await asyncio.wait_for(asyncio.open_connection(ip, port), 20)
                writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
                await writer.drain()
            elif tls:                                                 # a host with a secret: answer the box's TLS, add the header
                ctx = self.cert_for(host)
                writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
                await writer.drain()
                await writer.start_tls(ctx)
                first, head, pairs = await self._head(reader)
                name, value = str(inject.get("header") or ""), str(inject.get("value") or "")
                keep = [(k, v) for k, v in pairs if k.lower() not in DROP and k.lower() != name.lower()]
                out = "\r\n".join([first] + [f"{k}: {v}" for k, v in keep] + [f"{name}: {value}", "Connection: close"]) + "\r\n\r\n"
                up_r, up_w = await asyncio.wait_for(asyncio.open_connection(ip, port, ssl=self.upstream_ctx, server_hostname=host), 20)
                up_w.write(out.encode("latin-1"))
                await up_w.drain()
                self.stats["injected"] += 1
            else:                                                     # plain http: never a secret on it
                keep = [(k, v) for k, v in pairs if k.lower() not in DROP]
                out = "\r\n".join([f"{method} {path} HTTP/1.1"] + [f"{k}: {v}" for k, v in keep] + ["Connection: close"]) + "\r\n\r\n"
                up_r, up_w = await asyncio.wait_for(asyncio.open_connection(ip, port), 20)
                up_w.write(out.encode("latin-1"))
                await up_w.drain()
            await asyncio.gather(self._pipe(reader, up_w), self._pipe(up_r, writer))
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, asyncio.TimeoutError, ConnectionError, ValueError,
                ssl.SSLError, OSError, subprocess.SubprocessError) as e:
            try:
                if not writer.is_closing() and up_w is None:
                    await self._say(writer, 502, f"could not reach the host ({e.__class__.__name__})")
            except Exception:
                pass
        finally:
            for w in (writer, up_w):
                try:
                    if w is not None:
                        w.close()
                except Exception:
                    pass

    async def serve(self, host: str = "0.0.0.0", port: int = 3128) -> asyncio.AbstractServer:
        return await asyncio.start_server(self.handle, host, port, limit=HEAD_MAX)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--port", type=int, default=3128)
    a = ap.parse_args(argv)

    async def run() -> None:
        srv = await Proxy(a.dir).serve(port=a.port)
        print(f"hoola lab proxy on :{a.port}", flush=True)
        async with srv:
            await srv.serve_forever()
    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
