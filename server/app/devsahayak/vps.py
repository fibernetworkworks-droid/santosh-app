"""v0.941 HOOLA CODE ON YOUR SERVER — pair a VPS the simple, safe way.

HER SERVER CALLS HOOLA. The helper on her server opens an outbound long-poll to this server and asks for work; this
server never dials in. So no inbound port is opened, no firewall rule changes, and Hoola keeps NO password and NO SSH
key that could open her server. The helper runs as its own unprivileged `hoola` user and can act as root only for the
exact admin commands she ticked.

The access rules live BOTH here and in the helper on her server, so they hold even if THIS server were ever broken
into. Three places refuse a dangerous command: the session's tool, this module (`classify`), and the helper itself.

The only ways something runs on her server:
  - a look-only command (logs, status, disk, a file in a folder she allowed) runs by itself;
  - with "Trust my folders" on, a known-safe step (git pull, tests, restart her app) in one of her folders runs by
    itself; anything else waits for her tap;
  - every other command waits for POST /api/devsahayak/servers/{id}/cmds/{cid}/decide (her tap).
The never-list (delete everything, wipe a disk, change a password / user / SSH, open a firewall port, download-and-run
from outside, read a secret file) is refused everywhere and can never be approved.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from datetime import timedelta
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import now, session
from .models import DevServer, DevServerCmd

log = logging.getLogger("hoola.devsahayak.vps")


class VpsError(ValueError):
    pass


def on() -> bool:
    return bool(getattr(get_settings(), "dev_vps", False))


# ------------------------------------------------------------------ the never-list (refused everywhere, never approvable)
# Each entry: a reason she can read, and the pattern that matches the command text.
_REFUSE: list[tuple[str, re.Pattern[str]]] = [
    ("deletes a whole folder tree", re.compile(r"\brm\b[^\n|;&]*\s-[a-z]*r[a-z]*f|\brm\b[^\n|;&]*\s-[a-z]*f[a-z]*r|\brm\s+-rf?\s+(/|~|\$HOME|\*)", re.I)),
    ("wipes or reformats a disk", re.compile(r"\b(mkfs|fdisk|parted|dd)\b|\bwipefs\b|>\s*/dev/sd", re.I)),
    ("changes a password", re.compile(r"\b(passwd|chpasswd)\b", re.I)),
    ("adds, removes or changes a user", re.compile(r"\b(useradd|userdel|usermod|adduser|deluser|groupadd)\b", re.I)),
    ("changes SSH or its keys", re.compile(r"\bsshd?_config\b|~/\.ssh|\bauthorized_keys\b|\bssh-keygen\b", re.I)),
    ("opens a firewall port", re.compile(r"\b(ufw|iptables|nft|firewall-cmd)\b", re.I)),
    ("downloads and runs a script from outside", re.compile(r"\b(curl|wget|fetch)\b[^\n]*\|[^\n]*\b(ba)?sh\b", re.I)),
    ("reads a secret or key file", re.compile(r"(^|[\s/])(\.env(\.[\w-]+)?|id_rsa|id_ed25519|.*\.pem|.*\.key|credentials|secrets?\.(json|ya?ml|txt))(\s|$|['\"])", re.I)),
    ("gives itself root for everything", re.compile(r"\bsudo\s+(su|-i|bash|sh)\b|\bsudo\s+-s\b", re.I)),
    ("shuts down or reboots the server", re.compile(r"\b(shutdown|reboot|halt|poweroff|init\s+0)\b", re.I)),
]

# Look-only: reads the server, changes nothing. Allowed by itself at "look", "ask" and "trust".
_READS = re.compile(
    r"^\s*(ls|cat|head|tail|less|wc|grep|rg|find|stat|file|df|du|free|uptime|uname|hostname|whoami|id|date|env|printenv|"
    r"ps|top|htop|pm2\s+(list|status|logs|show|describe|info|jlist|prettylist)|systemctl\s+(status|show|is-active|list-units)|"
    r"journalctl|docker\s+(ps|logs|inspect|images|stats)|git\s+(status|log|diff|show|branch|remote|rev-parse|config\s+--get)|"
    r"node\s+--version|npm\s+(ls|list|--version|run\s+(lint|typecheck|test))|python3?\s+(-m\s+pytest|--version)|"
    r"pip\s+(list|show|freeze)|cu?rl\s+-s[^|]*localhost|which|type|tree|echo)\b", re.I)

# Known-safe writes that a "Trust my folders" grant may run by itself IN one of her folders.
_SAFE_WRITE = re.compile(
    r"^\s*(git\s+(pull|fetch|checkout|merge\s+--ff-only|reset\s+--hard\s+origin/|stash)|"
    r"pm2\s+(restart|reload|start|stop)|"
    r"systemctl\s+(reload|restart)\b|"
    r"npm\s+(ci|install|run\s+(build|test|lint|typecheck|migrate))|yarn\s+(install|test|build)|pnpm\s+(install|test|build)|"
    r"python3?\s+-m\s+(pytest|pip\s+install\s+-r)|pytest|"
    r"make\s+(test|build|lint)|docker\s+(restart|compose\s+(up|restart|build)))\b", re.I)


def _program(cmd: str) -> str:
    """A normalized 'program' key for an 'always in this folder' grant: the first two words, lower case."""
    parts = re.findall(r"[\w./-]+", (cmd or "").strip().lower())
    return " ".join(parts[:2]) if parts else (cmd or "").strip().lower()[:40]


def classify(cmd: str, folder: str, srv: DevServer) -> tuple[str, str]:
    """Return (lane, reason). lane is one of: refuse | reads | trusted | admin | write.
    - refuse: on the never-list, never runs.
    - reads: look-only, runs by itself at every level.
    - trusted: a safe write in a folder she allowed AND trust is on (or she tapped 'always' for it before).
    - admin: one of the root commands she ticked (still asks).
    - write: anything else (asks)."""
    text = cmd or ""
    for reason, pat in _REFUSE:
        if pat.search(text):
            return "refuse", reason
    if _READS.search(text) and "|" not in text and ">" not in text and ";" not in text:
        return "reads", "reads the server; changes nothing"
    folders = _folders(srv)
    in_folder = _in_allowed(folder, folders)
    already = f"{folder}|{_program(text)}" in set(_j(srv.trusted or "[]"))
    if (already or (srv.access == "trust" and in_folder and _SAFE_WRITE.search(text))):
        return "trusted", "a safe step in a folder you trust"
    for a in _j(srv.admin_cmds or "[]"):
        if _program(str(a)) == _program(text):
            return "admin", "an admin command you allowed (still asks)"
    return "write", "changes something on your server"


# ------------------------------------------------------------------ small helpers
def _j(s: str, default: Any = None):
    import json
    try:
        v = json.loads(s or "")
        return v if v is not None else (default if default is not None else [])
    except (ValueError, TypeError):
        return default if default is not None else []


def _dump(v: Any) -> str:
    import json
    return json.dumps(v, ensure_ascii=False)


def _folders(srv: DevServer) -> list[str]:
    return [str(x) for x in _j(srv.folders or "[]") if str(x).strip()]


def _in_allowed(folder: str, folders: list[str]) -> bool:
    f = (folder or "").strip().rstrip("/")
    if not f:
        return False
    for a in folders:
        a = a.strip().rstrip("/")
        if a and (f == a or f.startswith(a + "/")):
            return True
    return False


def _base_url() -> str:
    st = get_settings()
    base = (getattr(st, "public_base_url", "") or "").strip().rstrip("/")
    if not base:
        dom = (getattr(st, "hoola_domain", "") or "").strip()
        base = f"https://{dom}" if dom else ""
    return base


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(dt):
    from datetime import timezone
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _online(srv: DevServer) -> bool:
    if srv.status not in ("online",):
        return False
    seen = _aware(srv.last_seen)
    if seen is None:
        return False
    return (now() - seen).total_seconds() < getattr(get_settings(), "dev_vps_offline_s", 90)


def _scrub(text: str) -> str:
    """Hide any line that looks like a key or password before output reaches the model or her page."""
    try:
        from . import engine as E
        return E.scrub(text or "")
    except Exception:
        return text or ""


# ------------------------------------------------------------------ pairing (she starts it in the app)
def pair_start(tenant: str, name: str) -> dict[str, Any]:
    """Make a fresh 6-digit code (10 minutes) and the one line she pastes on her server."""
    if not on():
        raise VpsError("Hoola Code on your server is off on this server.")
    base = _base_url()
    if not base:
        raise VpsError("This server has no public address set, so a helper cannot reach it.")
    code = f"{secrets.randbelow(1000000):06d}"
    with session() as s:
        srv = DevServer(tenant_id=tenant, name=(name or "My server").strip()[:80], status="pairing",
                        pair_code=code, pair_until=now() + timedelta(minutes=10),
                        access="ask", folders="[]", admin_cmds="[]", trusted="[]")
        s.add(srv)
        s.flush()
        sid = srv.id
    return {"id": sid, "code": code, "ends_in_s": 600, "install": _install_line(base, code),
            "say": "Paste the line on your server. This page moves on by itself once it answers."}


def _install_line(base: str, code: str) -> str:
    return f"curl -fsSL {base}/vps/install | sudo bash -s {code}"


def enroll(code: str, facts: dict[str, Any]) -> dict[str, Any]:
    """The helper on her server calls this ONCE with the code she pasted. We bind it and hand back the helper's
    long-lived token (its sha256 is all we keep) and the current access rules. PUBLIC route, no sign-in."""
    code = re.sub(r"\D", "", code or "")
    if len(code) != 6:
        raise VpsError("bad code")
    with session() as s:
        srv = s.scalars(select(DevServer).where(DevServer.pair_code == code, DevServer.status == "pairing")).first()
        if srv is None or _aware(srv.pair_until) is None or _aware(srv.pair_until) < now():
            raise VpsError("this code is not active")
        token = "hvps_" + secrets.token_urlsafe(32)
        srv.agent_hash = _hash(token)
        srv.pair_code = ""
        srv.pair_until = None
        srv.status = "online"
        srv.last_seen = now()
        srv.facts = _dump(_clean_facts(facts))
        sid, poll = srv.id, _poll_s()
    return {"ok": True, "token": token, "server_id": sid, "config": _agent_config_by_id(sid), "poll_s": poll}


def _clean_facts(facts: dict[str, Any]) -> dict[str, Any]:
    f = facts if isinstance(facts, dict) else {}
    out: dict[str, Any] = {}
    for k, cast in (("os", str), ("cpus", int), ("mem_mb", int), ("disk_free_gb", int), ("agent_ver", str)):
        try:
            if k in f:
                out[k] = cast(f[k]) if cast is not str else str(f[k])[:60]
        except (ValueError, TypeError):
            pass
    return out


def _poll_s() -> int:
    return 20


def _idle_too_long(s, row: DevServer) -> bool:
    """v0.999.245 her "remove the helper after N idle days" (auto_off_days, 0 = never) was stored and shown but nothing
    acted on it: idle = no command proposed for this server (or since pairing) for that many days."""
    days = int(row.auto_off_days or 0)
    if days <= 0:
        return False
    last = s.scalars(select(DevServerCmd.created_at).where(DevServerCmd.server_id == row.id)
                     .order_by(DevServerCmd.created_at.desc()).limit(1)).first()
    since = _aware(last) or _aware(row.created_at)
    return bool(since) and now() - since > timedelta(days=days)


def _agent_config_by_id(sid: str) -> dict[str, Any]:
    with session() as s:
        srv = s.get(DevServer, sid)
        if srv is None:
            return {}
        return _agent_config(srv)


def _agent_config(srv: DevServer) -> dict[str, Any]:
    """What the helper enforces on its side: the never-list words, the access level, the allowed folders, the ticked
    admin commands, and when to remove itself. The helper refuses anything that breaks these even if this server asks."""
    return {
        "access": srv.access, "folders": _folders(srv), "admin_cmds": [str(x) for x in _j(srv.admin_cmds or "[]")],
        "auto_off_days": int(srv.auto_off_days or 0), "removing": srv.status in ("removing", "removed"),
        "cmd_timeout_s": int(getattr(get_settings(), "dev_vps_cmd_timeout_s", 900)),
        "poll_s": _poll_s(),        # v0.999.245 the helper reads poll_s from here (it was only at the top of the enroll reply)
    }


def _by_token(token: str) -> DevServer | None:
    h = _hash(token or "")
    with session() as s:
        srv = s.scalars(select(DevServer).where(DevServer.agent_hash == h)).first()
        if srv is None or not hmac.compare_digest(srv.agent_hash, h):
            return None
        s.expunge(srv)
        return srv


def check_in(token: str, facts: dict[str, Any] | None = None) -> dict[str, Any]:
    """The helper's outbound long-poll: 'I'm here, anything to run?' We mark it online, return the live config and any
    commands she has approved. PUBLIC route; the token (its hash) is the only credential."""
    srv = _by_token(token)
    if srv is None:
        raise VpsError("not paired")
    with session() as s:
        row = s.get(DevServer, srv.id)
        row.last_seen = now()
        if facts:
            row.facts = _dump(_clean_facts(facts))
        if row.status == "offline":
            row.status = "online"
        if row.status not in ("removing", "removed") and _idle_too_long(s, row):
            row.status = "removing"            # v0.999.245 auto-off: enforced HERE, so every helper (even 1.0.0) removes itself
        removing = row.status in ("removing", "removed")
        cfg = _agent_config(row)
        if removing:
            row.status = "removed"
            return {"config": cfg, "jobs": [], "remove": True}
        jobs = []
        q = s.scalars(select(DevServerCmd).where(DevServerCmd.server_id == row.id, DevServerCmd.status == "allowed")
                      .order_by(DevServerCmd.created_at)).all()
        for c in q[:5]:
            c.status = "running"
            jobs.append({"id": c.id, "cmd": c.cmd, "folder": c.folder,
                         "admin": classify(c.cmd, c.folder, row)[0] == "admin"})
    return {"config": cfg, "jobs": jobs, "remove": False}


def report(token: str, cmd_id: str, exit_code: int, output: str) -> dict[str, Any]:
    """The helper reports a command's result. PUBLIC route."""
    srv = _by_token(token)
    if srv is None:
        raise VpsError("not paired")
    out = _scrub(_clip(output or ""))
    with session() as s:
        c = s.get(DevServerCmd, cmd_id)
        if c is None or c.server_id != srv.id:
            raise VpsError("unknown command")
        c.exit_code = int(exit_code)
        c.output = out
        c.status = "done" if int(exit_code) == 0 else "failed"
        c.done_at = now()
    return {"ok": True}


def _clip(text: str, keep: int = 6000) -> str:
    t = text or ""
    if len(t) <= keep:
        return t
    head = t[: keep * 2 // 3]
    tail = t[-keep // 3:]
    return f"{head}\n… ({len(t) - keep} characters hidden) …\n{tail}"


# ------------------------------------------------------------------ a session proposes a command (the engine tool)
def propose(tenant: str, sid: str, cmd: str, folder: str = "", reason: str = "", task_id: str = "") -> dict[str, Any]:
    """A session wants to run a command on her server. Returns the state:
      refused  — on the never-list, nothing queued;
      queued   — waiting for her tap (write / admin);
      allowed  — a look-only or trusted command; the helper picks it up on its next check-in.
    The command never runs here; it runs in the helper on her server."""
    if not on():
        raise VpsError("Hoola Code on your server is off.")
    cmd = (cmd or "").strip()
    if not cmd:
        raise VpsError("no command")
    with session() as s:
        srv = _own(s, tenant, sid)
        folder = (folder or (_folders(srv)[0] if _folders(srv) else "~")).strip()
        lane, why = classify(cmd, folder, srv)
        if srv.access == "look" and lane not in ("reads", "refuse"):
            # v0.999.245 "Look only" promises nothing changes: a change is refused, never queued for a tap
            lane, why = "refuse", "changes something, and this server is set to Look only"
        online = _online(srv)
        auto = lane in ("reads", "trusted")
        c = DevServerCmd(tenant_id=tenant, server_id=sid, task_id=task_id, cmd=cmd[:4000], folder=folder[:300],
                         reason=(reason or why)[:400], reads_only=(lane == "reads"),
                         status=("refused" if lane == "refuse" else "allowed" if auto else "waiting"),
                         decided=("once" if auto else ""), decided_at=(now() if auto else None))
        s.add(c)
        s.flush()
        cid = c.id
        if lane == "refuse":
            return {"state": "refused", "id": cid, "reason": why,
                    "say": f"I won't run that on your server — it {why}."}
        if not online:
            return {"state": "offline", "id": cid, "lane": lane,
                    "say": f"{srv.name} is not connected right now, so I can't run that yet."}
        if auto:
            return {"state": "allowed", "id": cid, "lane": lane, "reason": why}
        return {"state": "queued", "id": cid, "lane": lane, "reason": why,
                "cmd": cmd, "folder": folder, "admin": lane == "admin"}


def decide(tenant: str, cmd_id: str, choice: str) -> dict[str, Any]:
    """Her tap on a waiting command: 'once' | 'always' | 'no'. 'always' also lets that command run by itself in that
    folder from now on. The never-list can never be approved (it is already 'refused' and not 'waiting')."""
    choice = (choice or "").strip().lower()
    if choice not in ("once", "always", "no"):
        raise VpsError("choice must be once / always / no")
    with session() as s:
        c = s.get(DevServerCmd, cmd_id)
        if c is None or c.tenant_id != tenant:
            raise VpsError("unknown command")
        if c.status != "waiting":
            return {"ok": True, "state": c.status}
        srv = s.get(DevServer, c.server_id)
        # never approve something the rules would refuse now (the folder / rules may have changed)
        if srv is not None and classify(c.cmd, c.folder, srv)[0] == "refuse":
            c.status = "refused"
            return {"ok": True, "state": "refused"}
        c.decided = choice
        c.decided_at = now()
        if choice == "no":
            c.status = "no"
            return {"ok": True, "state": "no"}
        c.status = "allowed"
        if choice == "always" and srv is not None:
            key = f"{c.folder}|{_program(c.cmd)}"
            keep = [x for x in _j(srv.trusted or "[]")]
            if key not in keep:
                keep.append(key)
                srv.trusted = _dump(keep[-200:])
    return {"ok": True, "state": "allowed"}


def wait_result(tenant: str, cmd_id: str) -> dict[str, Any]:
    """What a session reads back after proposing: the command's current state and, once done, its output."""
    with session() as s:
        c = s.get(DevServerCmd, cmd_id)
        if c is None or c.tenant_id != tenant:
            raise VpsError("unknown command")
        return {"id": c.id, "status": c.status, "exit_code": c.exit_code,
                "output": c.output if c.status in ("done", "failed") else "", "reason": c.reason}


# ------------------------------------------------------------------ her screens
def _own(s, tenant: str, sid: str) -> DevServer:
    srv = s.get(DevServer, sid)
    if srv is None or srv.tenant_id != tenant or srv.status == "removed":
        raise VpsError("That server is not connected.")
    return srv


def overview(tenant: str) -> dict[str, Any]:
    with session() as s:
        rows = s.scalars(select(DevServer).where(DevServer.tenant_id == tenant, DevServer.status != "removed")
                         .order_by(DevServer.created_at.desc())).all()
        return {"servers": [_server_view(r) for r in rows], "on": on()}


def _server_view(srv: DevServer) -> dict[str, Any]:
    f = _j(srv.facts or "{}", {})
    return {"id": srv.id, "name": srv.name, "status": ("online" if _online(srv) else srv.status),
            "online": _online(srv), "access": srv.access,
            "folders": _folders(srv), "admin_cmds": [str(x) for x in _j(srv.admin_cmds or "[]")],
            "auto_off_days": int(srv.auto_off_days or 0),
            "facts": f, "line": _facts_line(f),
            "last_seen": _aware(srv.last_seen).isoformat() if srv.last_seen else ""}


def _facts_line(f: dict[str, Any]) -> str:
    bits = []
    if f.get("os"):
        bits.append(str(f["os"]))
    if f.get("mem_mb"):
        bits.append(f"{round(int(f['mem_mb']) / 1024)} GB")
    if f.get("cpus"):
        bits.append(f"{int(f['cpus'])} CPU" + ("s" if int(f["cpus"]) != 1 else ""))
    if f.get("disk_free_gb"):
        bits.append(f"{int(f['disk_free_gb'])} GB free")
    return " · ".join(bits)


def detail(tenant: str, sid: str) -> dict[str, Any]:
    with session() as s:
        srv = _own(s, tenant, sid)
        v = _server_view(srv)
    v["activity"] = recent(tenant, sid)
    return v


def set_access(tenant: str, sid: str, *, access: str | None = None, folders: list[str] | None = None,
               admin_cmds: list[str] | None = None, auto_off_days: int | None = None, name: str | None = None) -> dict[str, Any]:
    with session() as s:
        srv = _own(s, tenant, sid)
        if access is not None:
            if access not in ("look", "ask", "trust"):
                raise VpsError("access must be look / ask / trust")
            srv.access = access
        if folders is not None:
            srv.folders = _dump([str(x).strip() for x in folders if str(x).strip()][:40])
        if admin_cmds is not None:
            clean = []
            for a in admin_cmds:
                a = str(a).strip()
                if a and not any(p.search(a) for _, p in _REFUSE):     # a refused command can never become an admin grant
                    clean.append(a[:200])
            srv.admin_cmds = _dump(clean[:40])
        if auto_off_days is not None:
            srv.auto_off_days = max(0, min(365, int(auto_off_days)))
        if name is not None and name.strip():
            srv.name = name.strip()[:80]
        v = _server_view(srv)
    return {"ok": True, "server": v, "say": "Saved."}


def disconnect(tenant: str, sid: str) -> dict[str, Any]:
    """Mark it for removal. The helper removes itself (and the hoola user) on its next check-in; if the server is
    offline she runs `sudo hoola-agent remove` there. Either way this server stops using it at once."""
    with session() as s:
        srv = _own(s, tenant, sid)
        srv.status = "removing"
        srv.agent_hash = srv.agent_hash  # kept so the helper can still check in once to tear itself down
        # cancel anything not yet run
        for c in s.scalars(select(DevServerCmd).where(DevServerCmd.server_id == sid,
                                                      DevServerCmd.status.in_(["waiting", "allowed"]))).all():
            c.status = "stale"
    return {"ok": True, "say": "Disconnected. The helper removes itself within a minute."}


def recent(tenant: str, sid: str, limit: int = 30) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(DevServerCmd).where(DevServerCmd.tenant_id == tenant, DevServerCmd.server_id == sid)
                         .order_by(DevServerCmd.created_at.desc()).limit(limit)).all()
        out = []
        for c in rows:
            out.append({"id": c.id, "cmd": c.cmd, "folder": c.folder, "status": c.status,
                        "reads_only": bool(c.reads_only), "decided": c.decided, "reason": c.reason,
                        "who": _who(c), "at": _aware(c.created_at).isoformat() if c.created_at else ""})
        return out


def _who(c: DevServerCmd) -> str:
    if c.status == "refused":
        return "Refused by your server"
    if c.status == "no":
        return "You said no"
    if c.status == "stale":
        return "Cancelled"
    if c.reads_only:
        return "Look only · ran by itself"
    if c.decided == "always":
        return "Allowed · always in this folder"
    if c.decided == "once":
        return "You allowed it" if not c.reads_only else "Ran by itself"
    return {"waiting": "Waiting for you", "allowed": "Ran by itself", "running": "Running"}.get(c.status, "")


# ------------------------------------------------------------------ the installer + helper served to her server
import pathlib

_DEPLOY = pathlib.Path(__file__).resolve().parents[3] / "deploy" / "hoola-vps"


def install_script() -> str:
    """The bash she pastes (the 6-digit code is her own argument, so the SAME script serves everyone)."""
    base = _base_url()
    try:
        text = (_DEPLOY / "install.sh").read_text()
    except OSError:
        raise VpsError("installer not found on this server")
    return text.replace("__BASE__", base)


def agent_source() -> str:
    try:
        return (_DEPLOY / "agent.py").read_text()
    except OSError:
        raise VpsError("helper not found on this server")


# ------------------------------------------------------------------ the session's tool (run a command on her server)
import time as _time

SERVER_TOOL: dict[str, Any] = {
    "name": "server",
    "description": (
        "Run a command on HER OWN server (a VPS she paired), to deploy, read logs, restart her app or find out why "
        "something broke. Her server runs it, not you. "
        "action=list shows the servers she connected (name + whether online). "
        "action=run with cmd (and an optional folder and a one-line reason): proposes the command. A look-only command "
        "(logs, status, disk, a file in a folder she allowed) and, when she turned on Trust, a known-safe step (git "
        "pull, tests, restart her app) in one of her folders run by themselves - you get the output back. Anything else "
        "WAITS for her tap; you are told it is waiting and should move on or stop, not loop. "
        "action=result with id reads a command's output once it has run. "
        "Never try to read a secret file (.env, keys), delete trees, change users / passwords / SSH, or open ports - "
        "her server refuses those and they can never be approved. Give the plainest, smallest command that does the job."),
    "input_schema": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["list", "run", "result"]},
        "server": {"type": "string", "description": "which server, by name (needed only when more than one is online)"},
        "cmd": {"type": "string", "description": "the exact shell command to run"},
        "folder": {"type": "string", "description": "the folder to run it in (one of her allowed folders)"},
        "reason": {"type": "string", "description": "one short line: what it does / why"},
        "id": {"type": "string", "description": "for result: the command id from a run"}},
        "required": ["action"]}}

HOWTO = ("HER SERVER (the server tool): she can connect her own VPS. Use the server tool to look at logs / status / disk, "
         "and - with her OK - to deploy, pull, run tests or restart her app. Her server runs the command; you only ask. "
         "A look-only command runs by itself; a change waits for her tap unless she turned on Trust for that folder. "
         "If a command is waiting for her tap, say so and move on - do not loop asking. Never read .env or key files.")


def _one_online(tenant: str, name: str = "") -> DevServer | None:
    with session() as s:
        rows = s.scalars(select(DevServer).where(DevServer.tenant_id == tenant, DevServer.status != "removed")).all()
        online = [r for r in rows if _online(r)]
        if name.strip():
            for r in online:
                if r.name.strip().lower() == name.strip().lower():
                    s.expunge(r)
                    return r
            return None
        if len(online) == 1:
            s.expunge(online[0])
            return online[0]
        return None


def server_tool(tenant: str, inp: dict[str, Any], emit=None) -> tuple[str, dict[str, Any] | None]:
    """Called from a Hoola Code round. Returns (text for the model, an event for her page or None)."""
    if not on():
        return "Running on her own server is off on this server.", None
    action = str(inp.get("action") or "").strip()
    if action == "list":
        ov = overview(tenant)
        servers = ov["servers"]
        if not servers:
            return "She has not connected a server yet (she does it in Hoola Code > Servers).", None
        lines = [f"- {x['name']}: {'online' if x['online'] else x['status']}"
                 + (f" ({x['line']})" if x.get('line') else "")
                 + (f", folders: {', '.join(x['folders'])}" if x['folders'] else "") for x in servers]
        return "Her servers:\n" + "\n".join(lines), None
    if action == "result":
        r = wait_result(tenant, str(inp.get("id") or ""))
        if r["status"] in ("done", "failed"):
            tag = "ran" if r["status"] == "done" else f"failed (exit {r['exit_code']})"
            return f"The command {tag}:\n{r['output'] or '(no output)'}", None
        if r["status"] == "waiting":
            return "Still waiting for her tap.", None
        if r["status"] in ("refused", "no", "stale"):
            return f"It did not run ({r['status']}).", None
        return "It is still running; read the result again in a moment.", None
    if action != "run":
        return "Use action list / run / result.", None
    srv = _one_online(tenant, str(inp.get("server") or ""))
    if srv is None:
        ov = overview(tenant)
        if not ov["servers"]:
            return "No server is connected. She connects one in Hoola Code > Servers.", None
        if not any(x["online"] for x in ov["servers"]):
            return "Her server is not connected right now.", None
        names = ", ".join(x["name"] for x in ov["servers"] if x["online"])
        return f"More than one server is online - say which with 'server': {names}.", None
    res = propose(tenant, srv.id, str(inp.get("cmd") or ""), str(inp.get("folder") or ""), str(inp.get("reason") or ""),
                  task_id=str(inp.get("_task") or ""))
    state, cid = res.get("state"), res.get("id")
    if state == "refused":
        return res["say"], {"k": "server", "state": "refused", "cmd": str(inp.get("cmd") or ""), "reason": res.get("reason", "")}
    if state == "offline":
        return res["say"], {"k": "server", "state": "offline", "server": srv.name}
    if state == "queued":
        ev = {"k": "server", "state": "waiting", "id": cid, "server_id": srv.id, "server": srv.name,
              "cmd": str(inp.get("cmd") or ""), "folder": res.get("folder", ""), "reason": res.get("reason", ""),
              "admin": bool(res.get("admin"))}
        return (f"Waiting for her tap to run `{inp.get('cmd')}` on {srv.name}. I'll see the result when she allows it - "
                "moving on for now."), ev
    # allowed (reads / trusted): wait briefly for the helper to run it
    ev = {"k": "server", "state": "running", "id": cid, "server": srv.name, "cmd": str(inp.get("cmd") or ""),
          "folder": res.get("folder", ""), "reason": res.get("reason", "")}
    deadline = _time.time() + 28
    while _time.time() < deadline:
        _time.sleep(2)
        r = wait_result(tenant, cid)
        if r["status"] in ("done", "failed"):
            tag = "ran" if r["status"] == "done" else f"failed (exit {r['exit_code']})"
            return f"`{inp.get('cmd')}` {tag} on {srv.name}:\n{r['output'] or '(no output)'}", {**ev, "state": r["status"]}
    return (f"`{inp.get('cmd')}` is running on {srv.name}; read it back with action result, id {cid}."), ev
