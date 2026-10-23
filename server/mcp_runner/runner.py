"""Hoola MCP Runner (v0.154): runs npm / PyPI / Docker-catalogue MCP servers for Hoola on a SEPARATE machine, never the
Hoola VPS, so a directory server works in Hoola with one tap.

Each server runs in its own locked Docker container (no host files, read-only root, all capabilities dropped, no new
privileges, pid / memory / CPU limits, its own small cache volume, install scripts off, a network that reaches only the
public internet). The runner speaks MCP over stdio to the container and offers it to Hoola as a Streamable HTTP MCP
endpoint `/mcp/<instance>` guarded by that instance's own bearer token. Hoola registers instances with HMAC-signed control
calls (`/v1/...`, secret HOOLA_RUNNER_SECRET); keys a server needs travel only on those calls and live only in memory here
(nothing secret is written to disk; after a restart Hoola registers the instance again). Idle containers stop after
HOOLA_RUNNER_IDLE_S and start again on the next request. `/v1/check` = safety check of a package before its first run
(registry facts, OSV.dev malware / vulnerability records, a scan of the package files for known bad patterns).
Standard library only.

    HOOLA_RUNNER_SECRET=... python3 runner.py --port 8091          (behind nginx with TLS; deploy/setup_mcp_runner.sh)
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import os
import re
import subprocess
import tarfile
import threading
import time
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

SECRET = os.environ.get("HOOLA_RUNNER_SECRET", "")
LAUNCHER = os.environ.get("HOOLA_RUNNER_LAUNCHER", "docker")       # docker | process (process = tests / dev only)
NETWORK = os.environ.get("HOOLA_RUNNER_NETWORK", "hoola-mcp")      # public-internet-only bridge (setup script)
IDLE_S = int(os.environ.get("HOOLA_RUNNER_IDLE_S", "600"))
MAX_INSTANCES = int(os.environ.get("HOOLA_RUNNER_MAX", "40"))
MEMORY = os.environ.get("HOOLA_RUNNER_MEMORY", "768m")
CPUS = os.environ.get("HOOLA_RUNNER_CPUS", "1")
START_TIMEOUT = float(os.environ.get("HOOLA_RUNNER_START_S", "180"))   # first start downloads the package
CALL_TIMEOUT = float(os.environ.get("HOOLA_RUNNER_CALL_S", "90"))
NODE_IMAGE = os.environ.get("HOOLA_RUNNER_NODE_IMAGE", "node:22-bookworm-slim")
UV_IMAGE = os.environ.get("HOOLA_RUNNER_UV_IMAGE", "ghcr.io/astral-sh/uv:python3.12-bookworm-slim")
MAX_BODY = 4 * 1024 * 1024
PROTOCOL = "2025-06-18"
_NPM = re.compile(r"^(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]{0,213}$")
_PYPI = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")
_DOCKER = re.compile(r"^mcp/[a-z0-9][a-z0-9._-]{0,80}$")             # Docker's own MCP catalogue images only
_VER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_-]{0,40}$")
_ENV = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_ARG = re.compile(r"^[A-Za-z0-9@:/._=,+-]{1,200}$")
_IID = re.compile(r"^[a-f0-9]{24}$")
BAD_ENV = {"PATH", "HOME", "LD_PRELOAD", "LD_LIBRARY_PATH", "NODE_OPTIONS", "PYTHONPATH", "PYTHONSTARTUP",
           "NPM_CONFIG_REGISTRY", "UV_INDEX_URL", "PIP_INDEX_URL", "http_proxy", "https_proxy"}

SPECS: dict[str, dict] = {}          # iid -> spec (memory only: it holds the server's keys)
LIVE: dict[str, "Instance"] = {}
LOCK = threading.RLock()


# ------------------------------------------------------------------------------------------------------------- auth
def sign(method: str, path: str, ts: str, body: bytes, secret: str | None = None) -> str:
    msg = f"{method}\n{path}\n{ts}\n".encode() + hashlib.sha256(body).hexdigest().encode()
    return hmac.new((secret if secret is not None else SECRET).encode(), msg, hashlib.sha256).hexdigest()


def clean_spec(d: dict) -> dict:
    """Only what we understand; anything odd is refused (the spec decides what runs)."""
    kind, pkg = str(d.get("kind") or ""), str(d.get("package") or "")
    if kind == "npm" and not _NPM.match(pkg) or kind == "pypi" and not _PYPI.match(pkg) or \
            kind == "docker" and not _DOCKER.match(pkg) or kind not in ("npm", "pypi", "docker", "cmd"):
        raise ValueError("bad package")
    if kind == "cmd" and os.environ.get("HOOLA_RUNNER_ALLOW_CMD") != "1":
        raise ValueError("cmd only in tests")
    ver = str(d.get("version") or "")
    if ver and not _VER.match(ver):
        raise ValueError("bad version")
    env = d.get("env") or {}
    if not isinstance(env, dict) or len(env) > 20:
        raise ValueError("bad env")
    env = {str(k): str(v)[:4000] for k, v in env.items()}
    if any(not _ENV.match(k) or k in BAD_ENV for k in env):
        raise ValueError("bad env name")
    args = [str(a) for a in (d.get("args") or [])][:12]
    if any(not _ARG.match(a) for a in args):
        raise ValueError("bad arg")
    th = str(d.get("token_sha256") or "")
    if not re.fullmatch(r"[a-f0-9]{64}", th):
        raise ValueError("bad token")
    out = {"kind": kind, "package": pkg, "version": ver, "env": env, "args": args, "token_sha256": th}
    if kind == "cmd":
        out["cmd"] = [str(x) for x in d.get("cmd") or []]
    return out


# --------------------------------------------------------------------------------------------------------- launching
def command(iid: str, spec: dict) -> list[str]:
    kind, pkg, ver = spec["kind"], spec["package"], spec["version"]
    if kind == "cmd":
        return spec["cmd"]
    fake = os.environ.get("HOOLA_RUNNER_FAKE_CMD", "")       # tests only: a local fake server instead of Docker
    if fake and os.environ.get("HOOLA_RUNNER_ALLOW_CMD") == "1":
        return json.loads(fake)
    cache = "hmcp-cache-" + hashlib.sha1(f"{kind}:{pkg}".encode()).hexdigest()[:16]
    base = ["docker", "run", "-i", "--rm", "--name", f"hmcp-{iid}", "--network", NETWORK, "--read-only",
            "--tmpfs", "/tmp:rw,exec,size=512m", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "256", "--memory", MEMORY, "--cpus", CPUS, "--user", "10001:10001",
            "--label", "hoola-mcp=1", "-e", "HOME=/tmp", "-e", "npm_config_ignore_scripts=true",
            "-e", "npm_config_update_notifier=false", "-e", "NO_UPDATE_NOTIFIER=1"]
    for k, v in spec["env"].items():
        base += ["-e", f"{k}={v}"]
    if kind == "npm":
        return base + ["-v", f"{cache}:/cache", "-e", "npm_config_cache=/cache/npm", NODE_IMAGE,
                       "npx", "-y", f"{pkg}@{ver}" if ver else pkg, *spec["args"]]
    if kind == "pypi":
        return base + ["-v", f"{cache}:/cache", "-e", "UV_CACHE_DIR=/cache/uv", "-e", "UV_TOOL_DIR=/tmp/uvtools",
                       UV_IMAGE, "uvx", f"{pkg}@{ver}" if ver else pkg, *spec["args"]]
    return base + [f"{pkg}:{ver}" if ver else pkg, *spec["args"]]          # docker catalogue image


class Instance:
    """One running server: stdio JSON-RPC with ids remapped so many HTTP callers can share it."""

    def __init__(self, iid: str, spec: dict):
        self.iid, self.spec = iid, spec
        self.proc: subprocess.Popen | None = None
        self.pending: dict[int, list] = {}
        self.next_id = 1
        self.lock = threading.Lock()
        self.wlock = threading.Lock()
        self.init_result: dict | None = None
        self.err = b""
        self.last = time.time()
        self.dead = False

    def start(self) -> None:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp")}
        if self.spec["kind"] == "cmd" or os.environ.get("HOOLA_RUNNER_FAKE_CMD"):
            env.update(self.spec["env"])       # docker runs get them as -e flags instead
        self.proc = subprocess.Popen(command(self.iid, self.spec), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, env=env, start_new_session=True)
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()
        res = self.request("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                          "clientInfo": {"name": "hoola-mcp-runner", "version": "1"}}, START_TIMEOUT)
        if "error" in res:
            raise RuntimeError(f"initialize failed: {json.dumps(res['error'])[:300]}")
        self.init_result = res.get("result") or {}
        self.notify("notifications/initialized", {})

    def _read_err(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            self.err = (self.err + line)[-6000:]

    def _read(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue
            if "method" in msg and "id" in msg:             # the server asks us something: we answer simply
                if msg["method"] == "roots/list":
                    self._write({"jsonrpc": "2.0", "id": msg["id"], "result": {"roots": []}})
                elif msg["method"] == "ping":
                    self._write({"jsonrpc": "2.0", "id": msg["id"], "result": {}})
                else:
                    self._write({"jsonrpc": "2.0", "id": msg["id"],
                                 "error": {"code": -32601, "message": "not supported by Hoola"}})
                continue
            if "id" in msg:
                with self.lock:
                    slot = self.pending.pop(msg["id"], None)
                if slot is not None:
                    slot[1] = msg
                    slot[0].set()
        self.dead = True
        with self.lock:
            for slot in self.pending.values():
                slot[1] = {"error": {"code": -32000, "message": "server stopped"}}
                slot[0].set()
            self.pending.clear()

    def _write(self, msg: dict) -> None:
        if not self.proc or not self.proc.stdin or self.dead:
            raise RuntimeError("server not running")
        with self.wlock:
            self.proc.stdin.write((json.dumps(msg) + "\n").encode())
            self.proc.stdin.flush()

    def notify(self, method: str, params: dict | None) -> None:
        self._write({"jsonrpc": "2.0", "method": method, **({"params": params} if params is not None else {})})

    def request(self, method: str, params: dict | None, timeout: float = CALL_TIMEOUT) -> dict:
        ev = threading.Event()
        slot: list = [ev, None]
        with self.lock:
            rid = self.next_id
            self.next_id += 1
            self.pending[rid] = slot
        self.last = time.time()
        self._write({"jsonrpc": "2.0", "id": rid, "method": method, **({"params": params} if params is not None else {})})
        if not ev.wait(timeout):
            with self.lock:
                self.pending.pop(rid, None)
            return {"error": {"code": -32001, "message": f"{method} timed out"}}
        self.last = time.time()
        return slot[1] or {}

    def stop(self) -> None:
        self.dead = True
        if self.proc and self.proc.poll() is None:
            try:
                if self.spec["kind"] != "cmd" and not os.environ.get("HOOLA_RUNNER_FAKE_CMD"):
                    subprocess.run(["docker", "rm", "-f", f"hmcp-{self.iid}"], capture_output=True, timeout=20)
                self.proc.terminate()
                self.proc.wait(5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass

    def stderr_tail(self) -> str:
        return mask(self.err.decode("utf-8", "replace")[-1500:], self.spec)


def mask(text: str, spec: dict) -> str:
    for v in spec.get("env", {}).values():
        if len(v) >= 6:
            text = text.replace(v, "[key hataya]")
    return re.sub(r"(?i)(token|key|secret|password)([\"'=: ]+)[A-Za-z0-9_\-./+]{12,}", r"\1\2[key hataya]", text)


def live(iid: str) -> Instance:
    with LOCK:
        inst = LIVE.get(iid)
        if inst and not inst.dead and inst.proc and inst.proc.poll() is None:
            return inst
        spec = SPECS.get(iid)
        if spec is None:
            raise KeyError(iid)
        if len([i for i in LIVE.values() if not i.dead]) >= MAX_INSTANCES:     # least recently used one makes room
            old = min((i for i in LIVE.values() if not i.dead), key=lambda i: i.last)
            old.stop()
        inst = Instance(iid, spec)
        LIVE[iid] = inst
    try:
        inst.start()
    except Exception:
        inst.stop()
        raise
    return inst


def reaper() -> None:
    while True:
        time.sleep(30)
        with LOCK:
            for iid, inst in list(LIVE.items()):
                if inst.dead or time.time() - inst.last > IDLE_S:
                    inst.stop()
                    LIVE.pop(iid, None)


# ---------------------------------------------------------------------------------------------------------- MCP plane
def handle_mcp(iid: str, body: dict | list) -> tuple[int, object | None]:
    inst = live(iid)
    msgs = body if isinstance(body, list) else [body]
    out = []
    for m in msgs:
        if not isinstance(m, dict) or m.get("jsonrpc") != "2.0":
            out.append({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}})
            continue
        method, mid = m.get("method"), m.get("id")
        if method is None:                       # a response to something we never asked: ignore
            continue
        if mid is None:                          # notification
            if method != "notifications/initialized":
                try:
                    inst.notify(method, m.get("params"))
                except Exception:
                    pass
            continue
        if method == "initialize":               # the server was initialised once by us; every caller gets that answer
            out.append({"jsonrpc": "2.0", "id": mid, "result": inst.init_result or {}})
            continue
        res = inst.request(method, m.get("params"))
        reply = {"jsonrpc": "2.0", "id": mid}
        reply.update({"error": res["error"]} if "error" in res else {"result": res.get("result", {})})
        out.append(reply)
    if not out:
        return 202, None
    return 200, out if isinstance(body, list) else out[0]


# ------------------------------------------------------------------------------------------------------- safety check
RED = [  # (pattern, why, severe)
    (r"curl[^\n|]{0,200}\|\s*(ba)?sh\b|wget[^\n|]{0,200}\|\s*(ba)?sh\b", "downloads and runs a shell script", True),
    (r"stratum\+tcp://|\bxmrig\b|coinhive|cryptonight", "crypto-mining code", True),
    (r"\.ssh/id_(rsa|ed25519)|\.aws/credentials|/etc/shadow", "reads private keys / credentials", True),
    (r"discord(app)?\.com/api/webhooks/\d+", "sends data to a Discord webhook", True),
    (r"api\.telegram\.org/bot[0-9]+:", "sends data to a Telegram bot", True),
    (r"JSON\.stringify\(\s*process\.env\s*\)|json\.dumps\(\s*dict\(\s*os\.environ", "collects all environment secrets", True),
    (r"eval\(\s*(atob|Buffer\.from)\(|exec\(\s*base64\.b64decode", "runs hidden (encoded) code", True),
    (r"child_process['\"]?\)?\.exec(Sync)?\(|subprocess\.(Popen|run|call)\([^)]*shell\s*=\s*True",
     "runs shell commands", False),
    (r"\bfs\.(rm|unlink)Sync\(\s*['\"]/|shutil\.rmtree\(\s*['\"]/", "deletes files outside its folder", False),
]


def _get(url: str, limit: int = 15 * 1024 * 1024, data: bytes | None = None) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "hoola-mcp-runner/1",
                                                          **({"Content-Type": "application/json"} if data else {})})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("too big")
    return raw


def _scan_archive(raw: bytes, name: str) -> list[dict]:
    hits: dict[str, dict] = {}

    def look(fname: str, data: bytes) -> None:
        if len(data) > 1_500_000 or not re.search(r"\.(m?js|cjs|ts|py|sh|json)$", fname):
            return
        text = data.decode("utf-8", "ignore")
        for pat, why, severe in RED:
            if why not in hits and re.search(pat, text):
                hits[why] = {"why": why, "file": fname[-80:], "severe": severe}
    try:
        if name.endswith((".whl", ".zip")):
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                for i in z.infolist()[:4000]:
                    if not i.is_dir():
                        look(i.filename, z.read(i)[:1_600_000])
        else:
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as t:
                for m in t.getmembers()[:4000]:
                    if m.isfile():
                        f = t.extractfile(m)
                        if f:
                            look(m.name, f.read(1_600_000))
    except Exception:
        hits["archive"] = {"why": "package files could not be read", "file": "", "severe": False}
    return list(hits.values())


def check(kind: str, pkg: str, version: str = "") -> dict:
    """Facts + verdict: ok | caution | block (with plain reasons). Never runs the package."""
    facts: dict = {"kind": kind, "package": pkg}
    reasons: list[str] = []
    verdict = "ok"
    try:
        if kind == "npm":
            meta = json.loads(_get(f"https://registry.npmjs.org/{quote(pkg, safe='@')}", 30 * 1024 * 1024))
            ver = version or (meta.get("dist-tags") or {}).get("latest", "")
            vm = (meta.get("versions") or {}).get(ver) or {}
            facts.update(version=ver, created=(meta.get("time") or {}).get("created", ""),
                         deprecated=bool(vm.get("deprecated")), repository=str((vm.get("repository") or {}) and
                         (vm.get("repository") or {}).get("url", "") if isinstance(vm.get("repository"), dict) else
                         vm.get("repository") or ""), licence=str(vm.get("license") or ""),
                         install_scripts=sorted(k for k in (vm.get("scripts") or {}) if k in
                                                ("preinstall", "install", "postinstall")))
            try:
                dl = json.loads(_get(f"https://api.npmjs.org/downloads/point/last-month/{quote(pkg, safe='@')}"))
                facts["downloads_month"] = int(dl.get("downloads") or 0)
            except Exception:
                pass
            tarball = (vm.get("dist") or {}).get("tarball", "")
            eco = "npm"
        elif kind == "pypi":
            meta = json.loads(_get(f"https://pypi.org/pypi/{quote(pkg)}/json", 30 * 1024 * 1024))
            info = meta.get("info") or {}
            ver = version or info.get("version", "")
            files = (meta.get("releases") or {}).get(ver) or meta.get("urls") or []
            facts.update(version=ver, yanked=any(f.get("yanked") for f in files), licence=str(info.get("license") or "")[:60],
                         repository=str((info.get("project_urls") or {}).get("Source") or info.get("home_page") or ""))
            pick = next((f for f in files if f.get("packagetype") == "bdist_wheel"), None) or (files[0] if files else {})
            tarball = pick.get("url", "")
            eco = "PyPI"
        else:
            return {"verdict": "ok", "reasons": ["Docker's own MCP catalogue image"], "facts": facts}
    except Exception as e:
        return {"verdict": "block", "reasons": [f"package not found on its registry ({type(e).__name__})"], "facts": facts}
    try:
        osv = json.loads(_get("https://api.osv.dev/v1/query", data=json.dumps(
            {"package": {"name": pkg, "ecosystem": eco}, **({"version": facts["version"]} if facts.get("version") else {})}
        ).encode()))
        vulns = [v.get("id", "") for v in osv.get("vulns") or []]
        facts["osv"] = vulns[:10]
        if any(v.startswith("MAL-") for v in vulns):
            verdict = "block"
            reasons.append("OSV.dev lists this package as MALICIOUS")
        elif vulns:
            verdict = "caution"
            reasons.append(f"{len(vulns)} known security problem(s) on OSV.dev")
    except Exception:
        reasons.append("OSV.dev could not be checked right now")
    if facts.get("deprecated") or facts.get("yanked"):
        verdict = "caution" if verdict == "ok" else verdict
        reasons.append("the publisher marked this version deprecated / yanked")
    if facts.get("install_scripts"):
        reasons.append("has install scripts (they are switched off when Hoola runs it)")
    if tarball.startswith("https://"):
        try:
            found = _scan_archive(_get(tarball), tarball)
        except Exception:
            found = [{"why": "package files could not be downloaded", "file": "", "severe": False}]
        facts["scan"] = found
        for f in found:
            if f["severe"]:
                verdict = "block"
            elif verdict == "ok":
                verdict = "caution"
            reasons.append(f["why"] + (f" ({f['file']})" if f["file"] else ""))
    return {"verdict": verdict, "reasons": reasons, "facts": facts}


# --------------------------------------------------------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    server_version = "HoolaMcpRunner/1"

    def log_message(self, fmt, *args):  # no request lines with tokens in them
        pass

    def _send(self, code: int, obj: object | None = None, ctype: str = "application/json") -> None:
        body = b"" if obj is None else json.dumps(obj).encode()
        self.send_response(code)
        if obj is not None:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("too big")
        return self.rfile.read(n) if n else b""

    def _control_ok(self, body: bytes) -> bool:
        ts = self.headers.get("X-Hoola-Time", "")
        if not SECRET or not ts.isdigit() or abs(time.time() - int(ts)) > 300:
            return False
        return hmac.compare_digest(self.headers.get("X-Hoola-Sign", ""), sign(self.command, self.path, ts, body))

    def _instance_ok(self, iid: str) -> bool:
        spec = SPECS.get(iid)
        auth = self.headers.get("Authorization", "")
        tok = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        return bool(spec and tok) and hmac.compare_digest(hashlib.sha256(tok.encode()).hexdigest(), spec["token_sha256"])

    def do_GET(self):
        if self.path == "/v1/health":
            with LOCK:
                running = len([i for i in LIVE.values() if not i.dead])
            return self._send(200, {"ok": True, "instances": len(SPECS), "running": running, "launcher": LAUNCHER})
        if self.path.startswith("/mcp/"):
            return self._send(405, {"error": "no server stream; POST only"})
        self._send(404, {"error": "not found"})

    def do_DELETE(self):
        if self.path.startswith("/mcp/"):
            return self._send(200, {})
        body = self._body()
        if not self._control_ok(body):
            return self._send(401, {"error": "bad signature"})
        m = re.fullmatch(r"/v1/instances/([a-f0-9]{24})", self.path)
        if not m:
            return self._send(404, {"error": "not found"})
        with LOCK:
            SPECS.pop(m.group(1), None)
            inst = LIVE.pop(m.group(1), None)
        if inst:
            inst.stop()
        self._send(200, {"ok": True})

    def do_POST(self):
        try:
            body = self._body()
        except ValueError:
            return self._send(413, {"error": "too big"})
        m = re.fullmatch(r"/mcp/([a-f0-9]{24})", self.path)
        if m:
            iid = m.group(1)
            if not self._instance_ok(iid):
                return self._send(401 if iid in SPECS else 404, {"error": "unknown instance or bad token"})
            try:
                payload = json.loads(body or b"null")
                code, out = handle_mcp(iid, payload)
            except KeyError:
                return self._send(404, {"error": "unknown instance"})
            except Exception as e:
                inst = LIVE.get(iid)
                return self._send(502, {"error": f"server did not start: {type(e).__name__}: {str(e)[:200]}",
                                        "stderr": inst.stderr_tail() if inst else ""})
            return self._send(code, out)
        if not self._control_ok(body):
            return self._send(401, {"error": "bad signature"})
        try:
            data = json.loads(body or b"{}")
        except ValueError:
            return self._send(400, {"error": "bad json"})
        if self.path == "/v1/instances":
            iid = str(data.get("iid") or "")
            if not _IID.match(iid):
                return self._send(400, {"error": "bad iid"})
            try:
                spec = clean_spec(data)
            except ValueError as e:
                return self._send(400, {"error": str(e)})
            with LOCK:
                old = SPECS.get(iid)
                SPECS[iid] = spec
                if old and old != spec and iid in LIVE:
                    LIVE.pop(iid).stop()
            if not data.get("start"):
                return self._send(200, {"ok": True, "registered": True})
            try:
                inst = live(iid)
                tools = inst.request("tools/list", {})
            except Exception as e:
                inst = LIVE.get(iid)
                return self._send(200, {"ok": False, "error": f"{type(e).__name__}: {mask(str(e), spec)[:300]}",
                                        "stderr": inst.stderr_tail() if inst else ""})
            if "error" in tools:
                return self._send(200, {"ok": False, "error": json.dumps(tools["error"])[:300],
                                        "stderr": inst.stderr_tail()})
            names = [t.get("name") for t in (tools.get("result") or {}).get("tools") or [] if isinstance(t, dict)]
            return self._send(200, {"ok": True, "tools": names[:200], "server": (inst.init_result or {}).get("serverInfo")})
        if self.path == "/v1/check":
            kind, pkg = str(data.get("kind") or ""), str(data.get("package") or "")
            ok_name = {"npm": _NPM, "pypi": _PYPI, "docker": _DOCKER}.get(kind)
            if not ok_name or not ok_name.match(pkg):
                return self._send(400, {"error": "bad package"})
            return self._send(200, check(kind, pkg, str(data.get("version") or "")))
        self._send(404, {"error": "not found"})


def serve(port: int, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=reaper, daemon=True).start()
    return srv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8091)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    if not SECRET:
        raise SystemExit("set HOOLA_RUNNER_SECRET")
    print(f"Hoola MCP runner on {a.host}:{a.port} ({LAUNCHER}); idle stop {IDLE_S}s, max {MAX_INSTANCES}", flush=True)
    serve(a.port, a.host).serve_forever()


if __name__ == "__main__":
    main()
