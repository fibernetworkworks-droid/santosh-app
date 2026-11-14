"""v0.878 HOOLA CODE ENVIRONMENTS (owner: "CHECK THE CLAUDE CODE DESIGN IN APP ... FROM ENVIRONMENT ATTACHMENT TO LONG CODE
DEVELOPMENT").

Claude Code's cloud sessions run in a named ENVIRONMENT picked on the new-session screen (code.claude.com/docs/en/
cloud-environments): Name, Network access (None / Limited - the package managers box + Allowed domains - / Full),
environment variables and a setup script. Hoola Code had the same pieces, but only per repo (Settings > repo). This
module adds the environment as its own thing, the same shape:

  * every tenant has a "Default" environment, made the first time she looks: Limited network, package managers allowed,
    no variables, no script - the same default Claude Code's onboarding makes;
  * "Auto" (no environment on the session) = "follows your repositories": each repo's own Settings, exactly as before;
  * a session started in an environment uses ITS network, its variables over the repo's, and its setup script after the
    repo's own setup command. Keys never live in an environment: they stay sealed on the repo and the proxy adds them
    outside the box, so they apply in every environment;
  * an environment is ARCHIVED, never deleted: running sessions keep it, new sessions cannot pick it;
  * nothing about the network changes while `dev_net` is off (the proxy check has not passed on the server): an
    environment then still carries its variables and setup script, and every view says the network is not on yet.
"""
from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import rules as R
from .models import DevEnv, DevSettings, DevTask

MAX_ENVS = 12
MAX_SETUP_LINES = 30
NAME_RE = re.compile(r"^[\w .()&+-]{1,60}$", re.UNICODE)
_VAR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,60}$")
_SECRETY = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key|credential)")
AUTO = "auto"


class EnvError(Exception):
    pass


def _j(v: Any, d: Any) -> Any:
    try:
        return json.loads(v) if v else d
    except (TypeError, ValueError):
        return d


def net_on() -> bool:
    try:
        from ..devlab import net as NET
        return NET.on()
    except Exception:
        return False


# ---------------------------------------------------------------- what she may type
def clean_vars(raw: Any) -> dict[str, str]:
    """NAME=value pairs, from a dict or from `.env` text (one per line, # comments). Never a secret: the box's output is
    shown to the AI, so a name or value that looks like a key is refused by name."""
    pairs: list[tuple[str, str]] = []
    if isinstance(raw, dict):
        pairs = [(str(k), str(v)) for k, v in raw.items()]
    elif raw:
        for line in str(raw).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise EnvError(f"'{line[:40]}' is not NAME=value.")
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            pairs.append((k.strip().removeprefix("export ").strip(), v))
    out: dict[str, str] = {}
    for k, v in pairs[:30]:
        k, v = k.strip(), v.strip()[:400]
        if not k:
            continue
        if not _VAR.match(k):
            raise EnvError(f"'{k[:40]}' is not a valid variable name (letters, numbers and _ only).")
        if _SECRETY.search(k) or R.secrets_in(f"{k}={v}") or R.looks_token(v):
            raise EnvError(f"{k} looks like a key or a password. Environments are not a place for secrets - add a key "
                           "for one host in Settings > repo > Keys, where it stays outside the box.")
        out[k] = v
    return out


def clean_setup(raw: Any) -> str:
    """The setup script: plain lines (comments allowed), each one a command the box may run - no sudo / docker / service
    commands and no key in it. It runs once with the network, before the session's first command, and is cached."""
    from ..devlab import spec as SP
    lines: list[str] = []
    for line in str(raw or "").replace("\r", "").split("\n"):
        line = line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        c = SP._clean(line)
        if not c:
            continue
        why = SP.refuse_reason(c)
        if why or R.secrets_in(c):
            raise EnvError(f"This setup line cannot run in the box ({why or 'it has a key in it'}): {line.strip()[:80]}")
        lines.append(c)
    if len(lines) > MAX_SETUP_LINES:
        raise EnvError(f"At most {MAX_SETUP_LINES} setup lines.")
    return "\n".join(lines)


def _clean_hosts(raw: Any) -> list[str]:
    from ..devlab import net as NET
    items = raw if isinstance(raw, list) else str(raw or "").replace(",", "\n").split()
    try:
        hosts = NET.clean_hosts(items)
    except ValueError as e:
        raise EnvError(str(e))
    if len(hosts) > NET.MAX_HOSTS:
        raise EnvError(f"At most {NET.MAX_HOSTS} allowed hosts.")
    return hosts


# ---------------------------------------------------------------- views
def view(e: DevEnv) -> dict[str, Any]:
    on = net_on()
    level = e.net_level or "limited"
    return {"id": e.id, "name": e.name, "kind": "cloud",
            "net": {"level": level, "pkgs": bool(e.pkgs), "hosts": _j(e.hosts, []), "on": on,
                    "note": "" if on or level == "none" else
                    "The network turns on once the server's network check passes (dev_net). Until then commands run offline."},
            "env_vars": _j(e.env_vars, {}), "setup": e.setup or "",
            "archived": e.archived_at is not None,
            "created_at": e.created_at.isoformat() if e.created_at else "",
            "updated_at": e.updated_at.isoformat() if e.updated_at else ""}


AUTO_VIEW = {"id": AUTO, "name": "Auto", "kind": "auto", "sub": "Follows your repositories",
             "note": "Each repo's own box settings (Settings > repo): its network, variables and setup command."}


def _ensure_default(s: Any, tenant: str) -> None:
    has = s.scalars(select(DevEnv).where(DevEnv.tenant_id == tenant).limit(1)).first()
    if has is None:
        s.add(DevEnv(tenant_id=tenant, name="Default", net_level="limited", pkgs=True))
        s.flush()


def list_envs(tenant: str, archived: bool = False) -> dict[str, Any]:
    with session() as s:
        _ensure_default(s, tenant)
        q = select(DevEnv).where(DevEnv.tenant_id == tenant)
        if not archived:
            q = q.where(DevEnv.archived_at.is_(None))
        rows = s.scalars(q.order_by(DevEnv.created_at)).all()
        st = s.get(DevSettings, tenant)
        pick = (st.env_pick if st is not None else None) or AUTO
        envs = [view(e) for e in rows]
    if pick != AUTO and not any(e["id"] == pick and not e["archived"] for e in envs):
        pick = AUTO
    return {"envs": envs, "auto": AUTO_VIEW, "pick": pick, "net_on": net_on(), "max": MAX_ENVS}


def get_env(tenant: str, eid: str) -> DevEnv | None:
    if not eid or eid == AUTO:
        return None
    with session() as s:
        e = s.get(DevEnv, eid)
        if e is None or e.tenant_id != tenant:
            return None
        s.expunge(e)
        return e


def _apply(e: DevEnv, b: dict[str, Any]) -> None:
    from ..devlab import net as NET
    if "name" in b:
        name = " ".join(str(b.get("name") or "").split())
        if not NAME_RE.match(name):
            raise EnvError("Give the environment a short name (letters, numbers, spaces).")
        e.name = name
    net = b.get("net") if isinstance(b.get("net"), dict) else b
    if "level" in net or "net_level" in net:
        lv = str(net.get("level", net.get("net_level")) or "").strip().lower()
        if lv not in NET.LEVELS:
            raise EnvError("Network access = none | limited | full")
        e.net_level = lv
    if "pkgs" in net:
        e.pkgs = bool(net.get("pkgs"))
    if "hosts" in net:
        e.hosts = json.dumps(_clean_hosts(net.get("hosts")))
    if "env_vars" in b:
        e.env_vars = json.dumps(clean_vars(b.get("env_vars")))
    if "setup" in b:
        e.setup = clean_setup(b.get("setup"))


def create_env(tenant: str, b: dict[str, Any]) -> dict[str, Any]:
    with session() as s:
        _ensure_default(s, tenant)
        n = len(s.scalars(select(DevEnv).where(DevEnv.tenant_id == tenant, DevEnv.archived_at.is_(None))).all())
        if n >= MAX_ENVS:
            raise EnvError(f"At most {MAX_ENVS} environments. Archive one first.")
        e = DevEnv(tenant_id=tenant, name="Default", net_level="limited", pkgs=True)
        _apply(e, {"name": b.get("name") or "", **{k: v for k, v in b.items() if k != "name"}})
        taken = {x.name.lower() for x in s.scalars(select(DevEnv).where(DevEnv.tenant_id == tenant,
                                                                         DevEnv.archived_at.is_(None))).all()}
        if e.name.lower() in taken:
            raise EnvError(f"You already have an environment called {e.name}.")
        s.add(e)
        s.flush()
        return view(e)


def update_env(tenant: str, eid: str, b: dict[str, Any]) -> dict[str, Any]:
    with session() as s:
        e = s.get(DevEnv, eid)
        if e is None or e.tenant_id != tenant:
            raise EnvError("That environment is not yours.")
        if e.archived_at is not None and not b.get("unarchive"):
            raise EnvError("This environment is archived. Unarchive it first.")
        if b.get("unarchive"):
            e.archived_at = None
        _apply(e, b)
        if "name" in b:
            clash = s.scalars(select(DevEnv).where(DevEnv.tenant_id == tenant, DevEnv.id != e.id,
                                                   DevEnv.archived_at.is_(None))).all()
            if any(x.name.lower() == e.name.lower() for x in clash):
                raise EnvError(f"You already have an environment called {e.name}.")
        e.updated_at = now()
        s.flush()
        return view(e)


def archive_env(tenant: str, eid: str) -> dict[str, Any]:
    """Archived, never deleted: sessions already in it keep running with it; new sessions cannot pick it."""
    with session() as s:
        e = s.get(DevEnv, eid)
        if e is None or e.tenant_id != tenant:
            raise EnvError("That environment is not yours.")
        live = s.scalars(select(DevEnv).where(DevEnv.tenant_id == tenant, DevEnv.archived_at.is_(None))).all()
        if e.archived_at is None and len(live) <= 1:
            raise EnvError("Keep at least one environment. Make another one first.")
        e.archived_at = now()
        st = s.get(DevSettings, tenant)
        if st is not None and st.env_pick == e.id:
            st.env_pick = None
        s.flush()
        return view(e)


def pick_for_new(tenant: str, eid: str) -> str | None:
    """The environment a NEW session runs in: '' = her last pick, 'auto' = none. An archived or foreign one is refused.
    Her choice is remembered for the next new session, like the selector does."""
    eid = str(eid or "").strip()
    with session() as s:
        st = s.get(DevSettings, tenant)
        if st is None:
            st = DevSettings(tenant_id=tenant)
            s.add(st)
        if not eid:
            eid = (st.env_pick if st is not None else None) or AUTO
            quiet = True
        else:
            quiet = False
        if eid == AUTO:
            if st is not None and not quiet:
                st.env_pick = AUTO
            return None
        e = s.get(DevEnv, eid)
        if e is None or e.tenant_id != tenant or e.archived_at is not None:
            if quiet:
                return None
            raise EnvError("That environment cannot be used (archived or not yours).")
        if st is not None:
            st.env_pick = e.id
        return e.id


def set_session_env(tenant: str, tid: str, eid: str) -> dict[str, Any]:
    """Change the environment of an existing session (Claude Code: the caret after the title > Edit cloud environment).
    It applies from the next round; a round already running keeps what it started with."""
    eid = str(eid or "").strip() or AUTO
    with session() as s:
        t = s.get(DevTask, tid)
        if t is None or t.tenant_id != tenant:
            raise EnvError("Session not found.")
        if eid == AUTO:
            t.env_id = None
        else:
            e = s.get(DevEnv, eid)
            if e is None or e.tenant_id != tenant or e.archived_at is not None:
                raise EnvError("That environment cannot be used (archived or not yours).")
            t.env_id = e.id
        s.flush()
        return {"ok": True, "task": t.id, "env": eid}


# ---------------------------------------------------------------- what the engine runs with
def overlay(tenant: str, env_id: str | None, hers: dict[str, str], env: dict[str, str],
            net: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    """The repo's (setup / test commands, variables, network) with the session's environment laid over them.
    No environment (Auto) = the repo's own, untouched. Keys stay the repo's - they apply in every environment."""
    e = get_env(tenant, env_id or "")
    if e is None:
        return hers, env, net
    hers = dict(hers)
    lines = [x for x in (hers.get("setup", ""), *(e.setup or "").split("\n")) if str(x).strip()]
    if lines:
        hers["setup"] = " && ".join(f"( {x} )" if len(lines) > 1 else x for x in lines)
    env = {**env, **{str(k): str(v) for k, v in (_j(e.env_vars, {}) or {}).items()}}
    out_net: dict[str, Any] = {}
    if net_on():
        level = e.net_level or "none"
        inject = (net or {}).get("inject") or {}
        if level != "none" or inject:
            out_net = {"level": level, "hosts": _j(e.hosts, []), "pkgs": bool(e.pkgs), "inject": inject, "env": e.name}
    return hers, env, out_net


def label(tenant: str, env_id: str | None) -> dict[str, Any]:
    """What a session shows on its chip: Auto, or the environment's name (and that it was archived since)."""
    if not env_id:
        return {"id": AUTO, "name": "Auto"}
    e = get_env(tenant, env_id)
    if e is None:
        return {"id": env_id, "name": "Removed environment"}
    return {"id": e.id, "name": e.name, "archived": e.archived_at is not None, "level": e.net_level}
