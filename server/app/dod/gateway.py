"""One OpenClaw Gateway per user - the invisible hands of her Hoola DOD coworker.

OpenClaw's own rule: one Gateway is one trust boundary, never shared by people who do not trust each other
(docs/gateway/security). So each user who uses Hoola DOD gets her own container from the pinned official image,
with its own state folder, its own Gateway token (sealed here), its own OpenRouter key with a spending limit, caps on
memory / CPU / processes, its own Docker network, and its port bound to 127.0.0.1 only. Nobody else's work can reach
it; only Hoola's server talks to it, with her token.

Hoola drives it over OpenClaw's documented OpenResponses endpoint (docs/gateway/openresponses-http-api.md):
POST /v1/responses with stream=true, Authorization: Bearer <her token>. Each request runs as a normal Gateway agent
run. Hoola gives the run its own client tools (hoola_step / hoola_ask / hoola_deliver / hoola_done, see service.py),
so every step, every question and her yes stay Hoola's. Not used: OpenClaw's chat-app channels (its WhatsApp is
WhatsApp Web, against Hoola's rule), its Control UI, its update checks and telemetry.

Seams for tests: DOCKER (runs a docker command), TRANSPORT (an httpx transport), OPENROUTER (base URL).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import shutil
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx

from .. import db
from ..config import get_settings
from .models import DodGateway, DodTask, ensure_tables

log = logging.getLogger("hoola.dod")

GATEWAY_PORT = 18789                      # the Gateway's fixed in-container listener (docker-compose.yml)
OPENROUTER = "https://openrouter.ai/api/v1"
TRANSPORT: httpx.AsyncBaseTransport | None = None   # tests put a fake OpenClaw / OpenRouter here
_LOCKS: dict[str, asyncio.Lock] = {}


class NotReady(Exception):
    """The coworker cannot start work yet. `why` is for her, `admin` names the fix for the owner."""

    def __init__(self, why: str, admin: str = ""):
        super().__init__(why)
        self.why = why
        self.admin = admin


# ------------------------------------------------------------------------------------------------ names and paths
def slug(tenant: str) -> str:
    return hashlib.sha256(tenant.encode()).hexdigest()[:12]


def container_name(tenant: str) -> str:
    return f"hoola-dod-{slug(tenant)}"


def network_name(tenant: str) -> str:
    return f"hoola-dod-net-{slug(tenant)}"


def home_dir(tenant: str) -> Path:
    s = get_settings()
    base = Path(s.dod_data_dir) if s.dod_data_dir else Path("data") / "dod"
    return base / slug(tenant)


def state_dir(tenant: str) -> Path:
    return home_dir(tenant) / "state"


def workspace_dir(tenant: str) -> Path:
    return state_dir(tenant) / "workspace"


# ------------------------------------------------------------------------------------------------ docker
async def _docker(*args: str, timeout: float = 120) -> tuple[int, str]:
    """Run one docker command; returns (exit code, output). Never a shell."""
    exe = shutil.which("docker")
    if not exe:
        return 127, "docker is not installed"
    proc = await asyncio.create_subprocess_exec(exe, *args, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return 124, "docker did not answer in time"
    return proc.returncode or 0, (out or b"").decode(errors="replace")[-4000:]


DOCKER: Callable[..., Awaitable[tuple[int, str]]] = _docker


def config_for(token: str, key: str, model: str, mcp_token: str = "", mcp_url: str = "") -> dict[str, Any]:
    """Her Gateway's openclaw.json: token auth, only the responses endpoint, no URL fetches of files / images, no
    update checks, no telemetry, her own model key. Keys and paths from OpenClaw's own docs (gateway/config-gateway,
    gateway/openresponses-http-api, gateway/telemetry, providers/openrouter)."""
    cfg: dict[str, Any] = {
        "gateway": {
            "mode": "local",   # a real Gateway refuses to start without it ("missing gateway.mode")
            "auth": {"mode": "token", "token": token},
            "bind": "lan",   # inside her container only; the host port is 127.0.0.1-bound by Hoola
            "http": {"endpoints": {"responses": {"enabled": True,
                                                 "files": {"allowUrl": False}, "images": {"allowUrl": False}}}},
        },
        "update": {"checkOnStart": False},
        "telemetry": {"enabled": False},
        "env": {"vars": {"OPENROUTER_API_KEY": key}},
        "agents": {"defaults": {"model": {"primary": model}}},
        # Chrome cannot start its own sandbox inside Docker's default limits (seen on the real -browser image: "No usable
        # sandbox"); her container is the wall around the browser instead
        "browser": {"noSandbox": True},
        # her container is the wall: commands run inside it, with no way to other users or Hoola's server
        "tools": {"exec": {"mode": "full"},
                  # OpenClaw hides most tool schemas behind its Tool Search; Hoola's own tools (hoola_step / hoola_ask /
                  # hoola_deliver / hoola_done, sent with each run) and her Hoola accounts (MCP hoola__*) stay directly
                  # visible to the model, so every step and every yes really goes through Hoola (seen on a real Gateway)
                  "toolSearch": {"mode": "tools", "exclude": [{"source": "client"}, {"source": "mcp", "name": "hoola__*"}]}},
    }
    if mcp_token and mcp_url:
        # her Hoola accounts (Gmail, Drive, Calendar, Sheets, Docs, her memory) as an MCP server - read-only tools,
        # her token only, and Hoola answers it only from her own container's network (dod/mcp.py)
        cfg["mcp"] = {"servers": {"hoola": {"url": mcp_url, "transport": "streamable-http", "enabled": True,
                                            "headers": {"Authorization": f"Bearer {mcp_token}"},
                                            "connectionTimeoutMs": 8000, "requestTimeoutMs": 60000}}}
    return cfg


def run_args(tenant: str, port: int, token: str) -> list[str]:
    """`docker run` for her Gateway (the official image unchanged; only its config and limits are Hoola's)."""
    s = get_settings()
    st = state_dir(tenant).resolve()
    return [
        "run", "-d", "--name", container_name(tenant), "--restart", "no",
        "--network", network_name(tenant),
        "-p", f"127.0.0.1:{port}:{GATEWAY_PORT}",
        "--memory", s.dod_memory, "--memory-swap", s.dod_memory, "--cpus", str(s.dod_cpus),
        "--pids-limit", "1024", "--security-opt", "no-new-privileges",
        "--label", "hoola.dod=1",
        "-e", "HOME=/home/node", "-e", "OPENCLAW_HOME=/home/node",
        "-e", "OPENCLAW_STATE_DIR=/home/node/.openclaw",
        "-e", "OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json",
        "-e", "OPENCLAW_WORKSPACE_DIR=/home/node/.openclaw/workspace",
        "-e", f"OPENCLAW_GATEWAY_PORT={GATEWAY_PORT}",
        "-e", f"OPENCLAW_GATEWAY_TOKEN={token}",
        "-e", "OPENCLAW_DISABLE_BONJOUR=1", "-e", "OPENCLAW_NO_AUTO_UPDATE=1",
        "-e", "DO_NOT_TRACK=1", "-e", "CLAWHUB_DISABLE_TELEMETRY=1",
        "-v", f"{st}:/home/node/.openclaw",
        s.dod_image,
    ]


def recover_args(tenant: str, *extra: str) -> list[str]:
    """A one-off container on her state folder that runs OpenClaw's own `gateway recover-lock` (no network)."""
    s = get_settings()
    return ["run", "--rm", "--network", "none", "--user", f"{s.dod_uid}:{s.dod_uid}", "--entrypoint", "openclaw",
            "-e", "HOME=/home/node", "-e", "OPENCLAW_STATE_DIR=/home/node/.openclaw",
            "-e", "OPENCLAW_CONFIG_PATH=/home/node/.openclaw/openclaw.json",
            "-v", f"{state_dir(tenant).resolve()}:/home/node/.openclaw", s.dod_image,
            "gateway", "recover-lock", "--json", *extra]


async def recover_lock(tenant: str) -> bool:
    """Clear a lock left by a Gateway that was killed hard (a server reboot, the memory cap, a crash). Without this a
    new start of her coworker waits on the dead owner and never comes up (seen on the real image: "cannot verify
    Gateway ownership"). Uses OpenClaw's own two-step recovery (inspect, then confirm exactly that record), and only
    when her container is not running - Hoola is the only owner of her state folder. Returns True when it cleared one."""
    code, out = await DOCKER("inspect", "-f", "{{.State.Running}}", container_name(tenant), timeout=30)
    if code == 0 and out.strip() == "true":
        return False
    if not (state_dir(tenant) / "openclaw.json").exists():
        return False
    code, out = await DOCKER(*recover_args(tenant), timeout=120)
    try:
        info = json.loads(out[out.index("{"):out.rindex("}") + 1])
    except ValueError:
        log.warning("dod lock check for %s gave no answer: %s", tenant, out[-200:])
        return False
    if not info.get("present") or not info.get("confirmation"):
        return False
    code, out = await DOCKER(*recover_args(tenant, "--confirm", str(info["confirmation"])), timeout=120)
    try:
        done = code == 0 and bool(json.loads(out[out.index("{"):out.rindex("}") + 1]).get("recovered"))
    except ValueError:
        done = False
    log.info("dod lock for %s %s", tenant, "cleared" if done else f"not cleared: {out[-200:]}")
    return done


def _own(path: Path) -> None:
    """Her state folder belongs to the container's user (dod_uid, the image's `node`), private: 700 folders, 600 files.
    Links are left alone (OpenClaw keeps some pointing inside its own image)."""
    import os
    uid = get_settings().dod_uid
    root_user = hasattr(os, "geteuid") and os.geteuid() == 0

    def fix(p: str, mode: int | None) -> None:
        if os.path.islink(p):
            return
        try:
            if mode is not None:
                os.chmod(p, mode)
            if root_user:
                os.chown(p, uid, uid)
        except OSError as e:
            log.warning("dod state ownership not set on %s: %s", p, e)

    fix(str(path), 0o700)
    for root, dirs, files in os.walk(path):
        for d in dirs:
            fix(os.path.join(root, d), 0o700)
        for f in files:
            fix(os.path.join(root, f), None)


# ------------------------------------------------------------------------------------------------ readiness
def readiness() -> dict[str, Any]:
    """Can a coworker start work on this server? {ok, why (for her), admin (for the owner)}."""
    s = get_settings()
    if not s.dod_engine:
        return {"ok": False, "why": "Your coworker is not switched on on this server yet.",
                "admin": "Set DOD_ENGINE=true in the VPS .env."}
    if not s.openrouter_provisioning_key:
        return {"ok": False, "why": "Your coworker cannot start work yet: the server is still being set up for it.",
                "admin": "Add OPENROUTER_PROVISIONING_KEY to the VPS .env (OpenRouter > Settings > Provisioning keys); "
                         "each user then gets her own model key with a spending limit."}
    if DOCKER is _docker and not shutil.which("docker"):
        return {"ok": False, "why": "Your coworker cannot start work yet: the server is still being set up for it.",
                "admin": "Docker is not installed on the server."}
    return {"ok": True, "why": "", "admin": ""}


def _row(tenant: str) -> DodGateway:
    ensure_tables()
    with db.session() as ss:
        g = ss.get(DodGateway, tenant)
        if g is None:
            g = DodGateway(tenant_id=tenant)
            ss.add(g)
            ss.commit()
        ss.expunge(g)
        return g


def _save(tenant: str, **kw: Any) -> None:
    with db.session() as ss:
        g = ss.get(DodGateway, tenant)
        if g is None:
            g = DodGateway(tenant_id=tenant)
            ss.add(g)
        for k, v in kw.items():
            setattr(g, k, v)
        ss.commit()


def _free_port() -> int:
    s = get_settings()
    with db.session() as ss:
        used = {p for (p,) in ss.query(DodGateway.port).all() if p}
    for p in range(s.dod_port_base, s.dod_port_base + 5000):
        if p not in used:
            return p
    raise NotReady("The server has no room for another coworker right now.", "No free port in the DOD range.")


# ------------------------------------------------------------------------------------------------ her model key
async def mint_key(tenant: str) -> tuple[str, str]:
    """Her own OpenRouter key with a spending limit (OpenRouter's provisioning API: POST /keys). Her coworker never
    sees the server's key, and nobody spends another user's credit."""
    s = get_settings()
    async with httpx.AsyncClient(transport=TRANSPORT, timeout=30) as c:
        r = await c.post(f"{OPENROUTER}/keys", headers={"Authorization": f"Bearer {s.openrouter_provisioning_key}"},
                         json={"name": f"hoola-dod-{slug(tenant)}", "limit": float(s.dod_key_limit_usd)})
    if r.status_code >= 300:
        raise NotReady("Your coworker cannot start work yet: the server could not set up its model.",
                       f"OpenRouter refused the new key: HTTP {r.status_code} {r.text[:200]}")
    data = r.json()
    key = data.get("key") or ""
    if not key:
        raise NotReady("Your coworker cannot start work yet: the server could not set up its model.",
                       "OpenRouter answered without a key.")
    return key, str((data.get("data") or {}).get("hash") or "")


async def spent(tenant: str) -> dict[str, Any] | None:
    """What her coworker's model key has used and its limit, in US dollars (OpenRouter GET /key), or None."""
    g = _row(tenant)
    if not g.key_enc:
        return None
    from ..bazar.security import vault
    try:
        key = vault().open(g.key_enc)
        async with httpx.AsyncClient(transport=TRANSPORT, timeout=10) as c:
            r = await c.get(f"{OPENROUTER}/key", headers={"Authorization": f"Bearer {key}"})
        d = (r.json() or {}).get("data") or {}
        return {"usage": float(d.get("usage") or 0), "limit": d.get("limit")}
    except Exception:  # noqa: BLE001 - the meter is a nicety, never a failure
        return None


# ------------------------------------------------------------------------------------------------ wake / sleep
def _awake_count() -> int:
    with db.session() as ss:
        return ss.query(DodGateway).filter(DodGateway.state == "awake").count()


async def _ready_http(base: str, token: str, wait: float) -> bool:
    end = time.monotonic() + wait
    async with httpx.AsyncClient(transport=TRANSPORT, timeout=5) as c:
        while time.monotonic() < end:
            try:
                r = await c.get(f"{base}/readyz", headers={"Authorization": f"Bearer {token}"})
                if r.status_code == 200:
                    return True
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1.5)
    return False


async def ensure(tenant: str) -> tuple[str, str]:
    """Her Gateway awake and ready -> (base URL, token). Starts it the first time, wakes it after sleep."""
    ready = readiness()
    if not ready["ok"]:
        raise NotReady(ready["why"], ready["admin"])
    s = get_settings()
    lock = _LOCKS.setdefault(tenant, asyncio.Lock())
    async with lock:
        g = _row(tenant)
        from ..bazar.security import vault
        if g.state == "awake" and g.port and g.token_enc:
            token = vault().open(g.token_enc)
            base = f"http://127.0.0.1:{g.port}"
            if await _ready_http(base, token, 3):
                _save(tenant, last_used_at=db.now())
                return base, token
        if g.state != "awake" and _awake_count() >= s.dod_max_awake:
            raise NotReady("Many coworkers are working on the server right now. Yours starts as soon as there is room.",
                           f"dod_max_awake={s.dod_max_awake} gateways are awake.")
        _save(tenant, state="starting", error="")
        try:
            if not g.mcp_enc:
                mt = secrets.token_urlsafe(32)
                _save(tenant, mcp_enc=vault().seal(mt), mcp_hash=hashlib.sha256(mt.encode()).hexdigest())
            if not g.token_enc:
                token = secrets.token_urlsafe(32)
                key, khash = await mint_key(tenant)
                port = _free_port()
                _save(tenant, token_enc=vault().seal(token), key_enc=vault().seal(key), key_hash=khash, port=port,
                      container=container_name(tenant), image=s.dod_image)
            g = _row(tenant)
            token, key = vault().open(g.token_enc), vault().open(g.key_enc)
            st = state_dir(tenant)
            (st / "workspace").mkdir(parents=True, exist_ok=True)
            cfg = st / "openclaw.json"
            mcp_url = (s.dod_hoola_url.rstrip("/") + "/mcp/dod") if s.dod_hoola_url else ""
            cfg.write_text(json.dumps(config_for(token, key, s.dod_model, vault().open(g.mcp_enc), mcp_url), indent=2),
                           encoding="utf-8")
            cfg.chmod(0o600)
            _own(st)   # OpenClaw runs as `node` (uid 1000) and refuses a state folder others can write to
            await recover_lock(tenant)   # a coworker killed hard leaves a lock that blocks every new start
            code, out = await DOCKER("start", container_name(tenant), timeout=60)
            if code != 0:
                await DOCKER("network", "create", "--driver", "bridge", network_name(tenant), timeout=30)
                c2, sub = await DOCKER("network", "inspect", "-f", "{{(index .IPAM.Config 0).Subnet}}",
                                       network_name(tenant), timeout=30)
                if c2 == 0 and "/" in sub:
                    _save(tenant, subnet=sub.strip())
                code, out = await DOCKER(*run_args(tenant, g.port, token), timeout=600)
                if code != 0:
                    raise NotReady("Your coworker could not start. Hoola will try again with your next task.",
                                   f"docker run failed: {out[-400:]}")
            base = f"http://127.0.0.1:{g.port}"
            if not await _ready_http(base, token, s.dod_start_wait_s):
                raise NotReady("Your coworker is taking long to start. Try again in a minute.",
                               f"{container_name(tenant)} did not answer /readyz in {s.dod_start_wait_s} s.")
            _save(tenant, state="awake", last_used_at=db.now(), error="")
            return base, token
        except NotReady as e:
            _save(tenant, state="failed", error=e.admin or e.why)
            raise


async def sleep_idle() -> int:
    """Put to sleep the Gateways with no work for dod_idle_min minutes (state kept on disk). Returns how many."""
    s = get_settings()
    ensure_tables()
    cut = db.now() - timedelta(minutes=s.dod_idle_min)
    n = 0
    with db.session() as ss:
        rows = ss.query(DodGateway).filter(DodGateway.state == "awake").all()
        busy = {t for (t,) in ss.query(DodTask.tenant_id).filter(DodTask.status.in_(("working", "queued"))).all()}
    for g in rows:
        last = g.last_used_at
        if last is not None and last.tzinfo is None:
            from datetime import timezone
            last = last.replace(tzinfo=timezone.utc)
        if g.tenant_id in busy or (last is not None and last > cut):
            continue
        code, _ = await DOCKER("stop", "-t", "20", g.container or container_name(g.tenant_id), timeout=60)
        if code == 0:
            _save(g.tenant_id, state="asleep")
            n += 1
    return n


def touch(tenant: str) -> None:
    _save(tenant, last_used_at=db.now())


# ------------------------------------------------------------------------------------------------ one agent run
async def respond(tenant: str, body: dict[str, Any], session_key: str,
                  on_text: Callable[[str], None] | None = None) -> dict[str, Any]:
    """One streamed agent run on her Gateway. Returns OpenClaw's final response object (id, status, output[])."""
    base, token = await ensure(tenant)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
               "x-openclaw-agent-id": "main", "x-openclaw-session-key": session_key}
    final: dict[str, Any] | None = None
    event = ""
    timeout = httpx.Timeout(connect=10, read=get_settings().dod_read_timeout_s, write=30, pool=10)
    async with httpx.AsyncClient(transport=TRANSPORT, timeout=timeout) as c:
        async with c.stream("POST", f"{base}/v1/responses", headers=headers, json={**body, "stream": True}) as r:
            if r.status_code >= 300:
                text = (await r.aread()).decode(errors="replace")[:400]
                raise RuntimeError(f"Her Gateway answered HTTP {r.status_code}: {text}")
            async for line in r.aiter_lines():
                if line.startswith("event:"):
                    event = line[6:].strip()
                    continue
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except ValueError:
                    continue
                kind = obj.get("type") or event
                if kind == "response.output_text.delta" and on_text:
                    on_text(str(obj.get("delta") or ""))
                elif kind in ("response.completed", "response.incomplete", "response.failed"):
                    final = obj.get("response") or obj
                    final.setdefault("status", kind.split(".", 1)[1])
    touch(tenant)
    if final is None:
        raise RuntimeError("Her Gateway closed the stream without a result.")
    return final


# ------------------------------------------------------------------------------------------------ her coworker's screen
async def screenshot(tenant: str, session_key: str) -> bytes | None:
    """A picture of the page her coworker's browser has open (OpenClaw's tools-invoke endpoint, browser screenshot).
    Only while her Gateway is awake - it never wakes or starts a browser just to look. None when there is no page."""
    g = _row(tenant)
    if g.state != "awake" or not g.port or not g.token_enc:
        return None
    from ..bazar.security import vault
    import base64
    token = vault().open(g.token_enc)
    try:
        async with httpx.AsyncClient(transport=TRANSPORT, timeout=20) as c:
            r = await c.post(f"http://127.0.0.1:{g.port}/tools/invoke", headers={"Authorization": f"Bearer {token}"},
                             json={"tool": "browser", "action": "screenshot", "args": {"type": "jpeg"},
                                   "sessionKey": session_key})
        if r.status_code != 200:
            return None
        res = (r.json() or {}).get("result") or {}
        for part in (res.get("content") or []) if isinstance(res, dict) else []:
            if isinstance(part, dict) and part.get("type") == "image" and part.get("data"):
                return base64.b64decode(part["data"])
    except Exception:  # noqa: BLE001 - no picture is a fine answer
        return None
    return None


# ------------------------------------------------------------------------------------------------ credits
async def charge_usage(tenant: str) -> float:
    """What her coworker's model key used since the last look goes into her Hoola Credits (1 credit = $0.001 of AI
    cost, the same meter as every other model call). Returns the US dollars charged now."""
    sp = await spent(tenant)
    if sp is None:
        return 0.0
    g = _row(tenant)
    delta = round(float(sp["usage"]) - float(g.usage_seen or 0.0), 8)
    if delta <= 0:
        return 0.0
    _save(tenant, usage_seen=float(sp["usage"]))
    try:
        from ..credits import wallet
        wallet.note(tenant, delta, "dod")
        wallet.flush()
    except Exception as e:  # noqa: BLE001
        log.warning("dod credits for %s not written: %s", tenant, e)
    return delta
