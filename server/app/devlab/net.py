"""Hoola Code Phase 6 - network levels for the box (docs/HOOLA_CODE_WEB_PLAN.md; owner: "GO PHASE 6").

Until now a command in the box had NO network at all. This module gives a repo three levels, chosen by its owner on the
settings page and by nobody else:
  none     - as before: no route out (the default, and what every repo has while `dev_net` is off)
  limited  - the package registries + the hosts she listed, and nothing else
  full     - any public https / http host
At every level above none the box still has NO route of its own: it sits on a Docker network without one
(`docker network create --internal`), and the one way out is the allow-list proxy (netproxy.py) running in its own
small container on that network. So even "full" cannot reach her own server, the Docker host or a private address, and
only http(s) leaves.

SECRETS ("network secrets"): a key for an outside API is saved for ONE host, sealed, and added to the request by the
proxy. It is never in the box - not in its environment, not in a file, not in a command.

Nothing here is tried in the tests against real Docker (there is none there): `python -m app.devlab net` proves it on
her server, and `dev_net` stays off until that passes."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import ssl
import subprocess
import time
from pathlib import Path
from typing import Any

from . import box
from .netproxy import HOST_RE, is_ip

log = logging.getLogger("santosh.devlab.net")
NET = "hoola-lab-net"
PROXY = "hoola-lab-proxy"
PORT = 3128
LEVELS = ("none", "limited", "full")
MAX_HOSTS = 20
MAX_SECRETS = 5
# What "limited" always allows: where a package manager fetches from. Not GitHub - that is a way out to any repo.
REGISTRIES = ("pypi.org", "files.pythonhosted.org", "registry.npmjs.org", "registry.yarnpkg.com", "repo.maven.apache.org",
              "repo1.maven.org", "plugins.gradle.org", "services.gradle.org", "pub.dev", "crates.io", "static.crates.io",
              "index.crates.io", "proxy.golang.org", "sum.golang.org", "rubygems.org", "api.nuget.org", "packagist.org")
HEADER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]{1,39}$")
HEADER_NO = {"host", "content-length", "transfer-encoding", "connection", "proxy-authorization", "cookie", "te", "upgrade"}
INNER = ("localhost", "local", "internal", "lan", "home", "corp", "test", "invalid", "example")


def root() -> Path:
    p = Path("data") / "devlab" / "net"
    (p / "runs").mkdir(parents=True, exist_ok=True)
    return p.resolve()


def on() -> bool:
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "dev_net", False))
    except Exception:
        return False


# ---------------------------------------------------------------- what she may type
def clean_hosts(hosts: Any) -> list[str]:
    """Her allowed hosts: plain names (`api.example.com`) or one level of wildcard (`*.example.com`). Refuses anything
    that is not a public DNS name - an address, a bare word, an inside-only name - and says which one."""
    out: list[str] = []
    for h in (hosts or []):
        h = str(h or "").strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0].rstrip(".")
        if not h:
            continue
        bare = h[2:] if h.startswith("*.") else h
        if "*" in bare or is_ip(bare) or not HOST_RE.match(bare) or bare.rsplit(".", 1)[-1] in INNER:
            raise ValueError(f"'{h[:60]}' is not a public host name. Write it like api.example.com or *.example.com.")
        if h.startswith("*.") and bare.count(".") < 1:
            raise ValueError(f"'{h[:60]}' is too wide. Name the site, like *.example.com.")
        if h not in out:
            out.append(h)
    if len(out) > MAX_HOSTS:
        raise ValueError(f"At most {MAX_HOSTS} hosts.")
    return out


def clean_secret(host: str, header: str, prefix: str = "") -> tuple[str, str, str]:
    host = clean_hosts([host])[0] if str(host or "").strip() else ""
    if not host or host.startswith("*."):
        raise ValueError("A secret is for ONE exact host, like api.example.com.")
    header = str(header or "Authorization").strip()
    if not HEADER_RE.match(header) or header.lower() in HEADER_NO:
        raise ValueError("The header name is not one a key travels in. Most APIs use Authorization or X-Api-Key.")
    prefix = str(prefix or "").strip()
    if prefix and not re.fullmatch(r"[A-Za-z][A-Za-z-]{1,15}", prefix):
        raise ValueError("The word before the key is one word, like Bearer or Token.")
    return host, header, prefix


def allow_for(level: str, hosts: list[str]) -> list[str]:
    if level == "full":
        return ["*"]
    if level == "limited":
        return list(REGISTRIES) + [h for h in hosts if h not in REGISTRIES]
    return []


# ---------------------------------------------------------------- the server's own lab CA (for hosts with a secret)
def ca() -> tuple[Path, Path]:
    d = root()
    pem, key = d / "ca.pem", d / "ca.key"
    if not (pem.exists() and key.exists()):
        subprocess.run(["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes",
                        "-keyout", str(key), "-out", str(pem), "-days", "3650", "-subj", "/CN=Hoola Lab Proxy CA",
                        "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign"],
                       check=True, capture_output=True, timeout=60)
        os.chmod(key, 0o600)
    return pem, key


def bundle() -> Path:
    """What a box is told to trust: the usual public CAs + this server's lab CA. The CA's KEY is never in it."""
    pem, _ = ca()
    out = root() / "bundle.pem"
    if not out.exists() or out.stat().st_mtime < pem.stat().st_mtime:
        base = ""
        for cand in (ssl.get_default_verify_paths().cafile, "/etc/ssl/certs/ca-certificates.crt"):
            if cand and os.path.exists(cand):
                base = Path(cand).read_text(encoding="utf-8", errors="ignore")
                break
        if not base:
            try:
                import certifi
                base = Path(certifi.where()).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                base = ""
        out.write_text(base.rstrip() + "\n" + pem.read_text(encoding="utf-8"), encoding="utf-8")
        os.chmod(out, 0o644)
    return out


# ---------------------------------------------------------------- the proxy container
def _uid() -> int:
    return os.getuid() or 1000


def _own(p: Path) -> None:
    if os.getuid() == 0:                          # the server runs as root: hand the file to the proxy's own user
        try:
            os.chown(p, 1000, 1000)
        except OSError:
            pass


def _code_rev() -> str:
    return hashlib.sha256((Path(__file__).parent / "netproxy.py").read_bytes()).hexdigest()[:16]


def proxy_args(d: str) -> list[str]:
    """How the proxy container is started. It gets: the rules folder (read-only), its own code (read-only), a small tmp
    for the per-host certificates, and nothing else - no capabilities, no writable root, not root."""
    r = root()
    code = Path(__file__).parent / "netproxy.py"
    return [d, "run", "-d", "--name", PROXY, "--restart", "unless-stopped", "--network", NET, "--read-only",
            "--user", f"{_uid()}:{_uid()}", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--memory", "256m", "--memory-swap", "256m", "--cpus", "1", "--pids-limit", "256",
            "--tmpfs", "/tmp:rw,size=32m", "--label", f"hoola.proxy.rev={_code_rev()}",
            "-v", f"{r}:/rules:ro", "-v", f"{code}:/proxy/netproxy.py:ro",
            box.BASE_IMAGE, "python3", "/proxy/netproxy.py", "--dir", "/rules", "--port", str(PORT)]


def ensure() -> dict[str, Any]:
    """The inside-only network and the proxy on it, made once and left running. Safe to call before every command."""
    d = box.docker()
    if not d:
        return {"ok": False, "why": "Docker is not on this server."}
    try:
        ca()
        for p in (root(), root() / "runs"):
            os.chmod(p, 0o755)
        for p in (root() / "ca.pem", root() / "ca.key"):
            _own(p)
        rc, _, _ = box._run([d, "network", "inspect", NET], 20)
        if rc != 0:
            rc, out, _ = box._run([d, "network", "create", "--internal", NET], 60)
            if rc != 0:
                return {"ok": False, "why": f"The inside-only network could not be made: {out.strip()[:200]}"}
        rc, out, _ = box._run([d, "inspect", "-f", '{{.State.Running}} {{index .Config.Labels "hoola.proxy.rev"}}', PROXY], 20)
        state = out.strip().split()
        if rc == 0 and state[:1] == ["true"] and state[1:2] == [_code_rev()]:
            return {"ok": True, "started": False}
        if rc == 0:
            box._run([d, "rm", "-f", PROXY], 60)
        rc, out, _ = box._run(proxy_args(d), 120)
        if rc != 0:
            return {"ok": False, "why": f"The proxy could not start: {out.strip()[:200]}"}
        rc, out, _ = box._run([d, "network", "connect", "bridge", PROXY], 60)     # the ONE container here with a route out
        if rc != 0 and "already exists" not in out:
            box._run([d, "rm", "-f", PROXY], 60)
            return {"ok": False, "why": f"The proxy could not be given a route out: {out.strip()[:200]}"}
        time.sleep(1.0)
        return {"ok": True, "started": True}
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "why": f"{e.__class__.__name__}: {str(e)[:160]}"}


# ---------------------------------------------------------------- one command's pass
def grant(level: str, hosts: list[str], inject: dict[str, dict[str, str]] | None = None, ttl: int = 900) -> dict[str, Any]:
    """Write the rule for ONE command and return what `box.run_in(net=...)` needs. The secret values go into the rule
    file (read by the proxy only) and nowhere else."""
    rid, key = secrets.token_hex(10), secrets.token_urlsafe(18)
    rule = {"key": hashlib.sha256(key.encode()).hexdigest(), "until": time.time() + ttl + 120, "level": level,
            "allow": allow_for(level, hosts), "inject": inject or {}}
    p = root() / "runs" / f"{rid}.json"
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(rule, f)
    _own(p)
    url = f"http://{rid}:{key}@{PROXY}:{PORT}"
    env = {"HTTPS_PROXY": url, "HTTP_PROXY": url, "https_proxy": url, "http_proxy": url,
           "NO_PROXY": "localhost,127.0.0.1", "no_proxy": "localhost,127.0.0.1"}
    mounts: list[str] = []
    if inject:                                    # only then does the box need to trust the lab CA
        ca_in = "/etc/hoola/ca-bundle.pem"
        mounts.append(f"{bundle()}:{ca_in}:ro")
        env.update({k: ca_in for k in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS",
                                       "PIP_CERT", "GIT_SSL_CAINFO")})
    return {"id": rid, "network": NET, "env": env, "mounts": mounts, "hide": [v["value"] for v in (inject or {}).values()]}


def revoke(rid: str) -> None:
    try:
        (root() / "runs" / f"{rid}.json").unlink(missing_ok=True)
    except OSError:
        pass


def sweep() -> int:
    """Rules whose time is over (a command that died without revoking). Called from the worker's tick."""
    n = 0
    for p in (root() / "runs").glob("*.json"):
        try:
            if float(json.loads(p.read_text(encoding="utf-8")).get("until") or 0) < time.time():
                p.unlink()
                n += 1
        except (OSError, ValueError):
            pass
    return n


def status() -> dict[str, Any]:
    d = box.docker()
    up = False
    if d:
        rc, out, _ = box._run([d, "inspect", "-f", "{{.State.Running}}", PROXY], 20)
        up = rc == 0 and out.strip() == "true"
    return {"on": on(), "docker": bool(d), "proxy": up, "levels": list(LEVELS), "registries": list(REGISTRIES)}


# ---------------------------------------------------------------- the proof, on her server
def check(echo_url: str = "") -> dict[str, Any]:
    """Every wall of the network levels, tried for real in the box. Printed stage by stage; ok only if all hold."""
    import tempfile
    stages: list[dict[str, Any]] = []

    def add(name: str, ok: bool, note: str = "") -> bool:
        stages.append({"stage": name, "ok": bool(ok), "note": note[:300]})
        return bool(ok)
    av = box.available()
    if not add("docker + base image", bool(av.get("ok")) and box.has_image(box.BASE_IMAGE), str(av.get("why") or "")):
        return {"ok": False, "stages": stages}
    e = ensure()
    if not add("inside-only network + proxy container", bool(e.get("ok")), str(e.get("why") or "")):
        return {"ok": False, "stages": stages}
    work = tempfile.mkdtemp(prefix="hoola-netcheck-")
    os.chmod(work, 0o777)

    def run(g: dict[str, Any] | None, cmd: str) -> tuple[int, str]:
        r = box.run_in(box.BASE_IMAGE, work, cmd, timeout=90, net=g)
        return int(r.get("rc") or 0), str(r.get("out") or "")
    code = "curl -sS -o /dev/null -m 40 -w '%{http_code}' "
    g = grant("limited", [])
    try:
        rc, out = run(g, code + "https://pypi.org/simple/pip/")
        add("limited: a package registry answers", out.strip().endswith("200"), out)
        rc, out = run(g, code + "https://example.com/ ; echo")
        add("limited: a host not on the list is refused", "200" not in out.strip()[-3:], out)
        rc, out = run(g, "curl -sS -m 15 --noproxy '*' -o /dev/null -w '%{http_code}' https://pypi.org/ ; echo rc=$?")
        add("no way around the proxy", "rc=0" not in out, out)
        rc, out = run(g, code + "http://169.254.169.254/ ; echo; " + code + "https://172.17.0.1/ ; echo")
        add("an address instead of a name is refused", "200" not in out, out)
    finally:
        revoke(g["id"])
    rc, out = run(None, "curl -sS -m 10 -o /dev/null -w '%{http_code}' https://pypi.org/ ; echo rc=$?")
    add("none: still no network at all", "rc=0" not in out, out)
    g = grant("full", [])
    try:
        rc, out = run(g, code + "https://example.com/")
        add("full: any public host answers", out.strip().endswith("200"), out)
    finally:
        revoke(g["id"])
    if echo_url:                                   # her own server says what it received - as a fingerprint, never the value
        from urllib.parse import urlparse
        host = (urlparse(echo_url).hostname or "").lower()
        val = "hoola-check-" + secrets.token_hex(12)
        g = grant("none", [], {host: {"header": "X-Hoola-Lab-Check", "value": val}})
        try:
            rc, out = run(g, f"curl -sS -m 40 {echo_url} ; echo; env | grep -c '{val}' ; grep -rc '{val}' /etc/hoola 2>/dev/null | tail -1")
            want = hashlib.sha256(val.encode()).hexdigest()[:16]
            add("secret: the host received it", want in out, out.replace(val, "[the secret]"))
            add("secret: it is nowhere in the box", val not in out and "\n0" in out, out.replace(val, "[the secret]"))
        finally:
            revoke(g["id"])
    return {"ok": all(s["ok"] for s in stages), "stages": stages}
