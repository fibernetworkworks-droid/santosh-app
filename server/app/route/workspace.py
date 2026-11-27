"""v0.999.246 ACCOUNTS, VARIABLES, SETTINGS, VERSIONS, SHARING (R7 of the Hoola Route plan; owner: "GO R7").

- variables   values every route can read as {{env.NAME}} (not for secrets: those are sign-ins)
- sign-ins    a web request step signs in with a saved sign-in by its name: a bearer token, a header, user + password, a key
              in the address or OAuth2 client credentials. Sealed on arrival (the house vault), never shown again (only the
              last 4), never seen by the AI, and only ever sent to the one site she named for it.
- accounts    which of her connected accounts a step uses (mailboxes + Google accounts), offered where a tool takes one
- versions    every save keeps a version (the steps, the trigger, the settings); any version can be brought back, which is
              itself a new version; 50 kept per route
- sharing     a read-only link to look at a route (its steps in words, no data, no keys; 30 days, can be stopped) and team
              members who may run it from their own Hoola (they can run it, never change it)
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
from typing import Any
from urllib.parse import urlparse

VAR_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,49}$")
VARS_MAX = 100
VAR_BYTES = 20_000
CRED_KINDS = ("bearer", "header", "basic", "query", "oauth2")
CREDS_MAX = 50
VERSIONS_KEEP = 50
SHARE_DAYS = 30
TAGS_MAX = 10
_TOKENS: dict[str, tuple[str, float]] = {}      # an OAuth2 token per sign-in, kept in memory until it runs out


class WorkspaceError(ValueError):
    pass


def _con(tenant: str):
    from ..agent import dhara_tools as D
    con = D._con(tenant)
    con.execute("CREATE TABLE IF NOT EXISTS route_vars (name TEXT PRIMARY KEY, value TEXT, note TEXT, updated_at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS route_creds (name TEXT PRIMARY KEY, kind TEXT, host TEXT, sealed TEXT, hint TEXT, "
                "note TEXT, created_at REAL, used_at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS route_versions (id TEXT PRIMARY KEY, workflow_id TEXT, at REAL, hash TEXT, "
                "description TEXT, trigger_kind TEXT, trigger_spec TEXT, steps TEXT, settings TEXT, note TEXT)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_route_versions ON route_versions (workflow_id, at)")
    con.execute("CREATE TABLE IF NOT EXISTS route_shares (workflow_id TEXT PRIMARY KEY, token_hash TEXT, path TEXT, "
                "created_at REAL, expires_at REAL)")
    return con


# ---------------------------------------------------------------- variables ({{env.NAME}})
def variables(tenant: str) -> list[dict]:
    con = _con(tenant)
    try:
        rows = con.execute("SELECT * FROM route_vars ORDER BY name").fetchall()
    finally:
        con.close()
    out = []
    for r in rows:
        try:
            v = json.loads(r["value"])
        except (TypeError, ValueError):
            v = r["value"]
        out.append({"name": r["name"], "value": v, "note": r["note"] or "", "updated_at": r["updated_at"]})
    return out


def env(tenant: str) -> dict[str, Any]:
    return {v["name"]: v["value"] for v in variables(tenant)}


_SECRETISH = re.compile(r"(sk|pk|rk)_(live|test)_[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abp]-[A-Za-z0-9-]{10,}|"
                        r"-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.")


def set_variable(tenant: str, name: str, value: Any, note: str = "") -> dict:
    name = str(name or "").strip()
    if not VAR_NAME.match(name):
        raise WorkspaceError("A variable needs a short name: letters, digits and _ (like SHOP_NAME)")
    txt = json.dumps(value, ensure_ascii=False, default=str)
    if len(txt) > VAR_BYTES:
        raise WorkspaceError(f"A variable can hold up to {VAR_BYTES // 1000} KB")
    if _SECRETISH.search(txt):
        raise WorkspaceError("That looks like a key or a password. Keep it as a saved sign-in instead - variables are not secret.")
    con = _con(tenant)
    try:
        n = con.execute("SELECT COUNT(*) FROM route_vars WHERE name != ?", (name,)).fetchone()[0]
        if n >= VARS_MAX:
            raise WorkspaceError(f"Up to {VARS_MAX} variables")
        con.execute("INSERT OR REPLACE INTO route_vars (name, value, note, updated_at) VALUES (?, ?, ?, ?)",
                    (name, txt, str(note or "")[:200], time.time()))
        con.commit()
    finally:
        con.close()
    return {"name": name, "value": value}


def drop_variable(tenant: str, name: str) -> None:
    con = _con(tenant)
    try:
        con.execute("DELETE FROM route_vars WHERE name = ?", (str(name),))
        con.commit()
    finally:
        con.close()


# ---------------------------------------------------------------- sign-ins (credentials)
def _vault():
    from ..bazar.security import vault
    return vault()


def _host(v: str) -> str:
    v = str(v or "").strip().lower()
    if "://" in v:
        v = urlparse(v).hostname or ""
    v = v.split("/")[0].split(":")[0].strip(".")
    if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", v):
        raise WorkspaceError("Give the site this sign-in is for, like api.example.com")
    return v


def _hint(secret: str) -> str:
    s = str(secret or "")
    return ("••••" + s[-4:]) if len(s) >= 8 else "••••"


def credentials(tenant: str) -> list[dict]:
    con = _con(tenant)
    try:
        rows = con.execute("SELECT name, kind, host, hint, note, created_at, used_at FROM route_creds ORDER BY name").fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def save_credential(tenant: str, body: dict) -> dict:
    name = str(body.get("name") or "").strip()
    if not VAR_NAME.match(name):
        raise WorkspaceError("A sign-in needs a short name: letters, digits and _ (like SHOP_API)")
    kind = str(body.get("kind") or "")
    if kind not in CRED_KINDS:
        raise WorkspaceError(f"The kind of sign-in must be one of: {', '.join(CRED_KINDS)}")
    host = _host(body.get("host"))
    need = {"bearer": ("token",), "header": ("header", "value"), "basic": ("user", "password"), "query": ("param", "value"),
            "oauth2": ("token_url", "client_id", "client_secret")}[kind]
    data = {k: str(body.get(k) or "").strip() for k in ("token", "header", "value", "user", "password", "param", "token_url",
                                                         "client_id", "client_secret", "scope")}
    miss = [k for k in need if not data[k]]
    if miss:
        raise WorkspaceError("Fill in: " + ", ".join(m.replace("_", " ") for m in miss))
    if kind == "header" and not re.match(r"^[A-Za-z0-9-]{1,60}$", data["header"]):
        raise WorkspaceError("A header name has letters, digits and -")
    if kind == "query" and not re.match(r"^[A-Za-z0-9_.-]{1,60}$", data["param"]):
        raise WorkspaceError("The name in the address has letters, digits, _ . -")
    if kind == "oauth2":
        th = _host(data["token_url"])
        if not data["token_url"].lower().startswith("https://"):
            raise WorkspaceError("The token address must start with https://")
        if th != host and not th.endswith("." + host) and not host.endswith("." + th.split(".", 1)[-1]):
            pass                                    # an identity provider may live on its own site; it is SSRF-guarded at use
    secret = {"bearer": data["token"], "header": data["value"], "basic": data["password"], "query": data["value"],
              "oauth2": data["client_secret"]}[kind]
    keep = {k: v for k, v in data.items() if v}
    con = _con(tenant)
    try:
        n = con.execute("SELECT COUNT(*) FROM route_creds WHERE name != ?", (name,)).fetchone()[0]
        if n >= CREDS_MAX:
            raise WorkspaceError(f"Up to {CREDS_MAX} sign-ins")
        con.execute("INSERT OR REPLACE INTO route_creds (name, kind, host, sealed, hint, note, created_at, used_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                    (name, kind, host, _vault().seal(json.dumps(keep)), _hint(secret), str(body.get("note") or "")[:200], time.time()))
        con.commit()
    finally:
        con.close()
    _TOKENS.pop(f"{tenant}:{name}", None)
    return {"name": name, "kind": kind, "host": host, "hint": _hint(secret)}


def drop_credential(tenant: str, name: str) -> None:
    con = _con(tenant)
    try:
        con.execute("DELETE FROM route_creds WHERE name = ?", (str(name),))
        con.commit()
    finally:
        con.close()
    _TOKENS.pop(f"{tenant}:{name}", None)


def _host_ok(url_host: str, cred_host: str) -> bool:
    url_host = (url_host or "").lower()
    return url_host == cred_host or url_host.endswith("." + cred_host)


def apply_auth(tenant: str, name: str, url: str, headers: dict) -> tuple[str, dict]:
    """Add the saved sign-in to a web request - only when the request goes to the site it is for."""
    import httpx
    con = _con(tenant)
    try:
        r = con.execute("SELECT * FROM route_creds WHERE name = ?", (str(name),)).fetchone()
        if r is not None:
            con.execute("UPDATE route_creds SET used_at = ? WHERE name = ?", (time.time(), str(name)))
            con.commit()
    finally:
        con.close()
    if r is None:
        raise WorkspaceError(f"There is no saved sign-in named {name}")
    host = urlparse(url).hostname or ""
    if not _host_ok(host, r["host"]):
        raise WorkspaceError(f"The sign-in {name} is only for {r['host']} - this request goes to {host or 'an unknown site'}")
    d = json.loads(_vault().open(r["sealed"]))
    h = dict(headers or {})
    kind = r["kind"]
    if kind == "bearer":
        h["Authorization"] = "Bearer " + d["token"]
    elif kind == "header":
        h[d["header"]] = d["value"]
    elif kind == "basic":
        import base64
        h["Authorization"] = "Basic " + base64.b64encode(f"{d['user']}:{d['password']}".encode()).decode()
    elif kind == "query":
        from urllib.parse import urlencode
        url = url + ("&" if "?" in url else "?") + urlencode({d["param"]: d["value"]})
    elif kind == "oauth2":
        key = f"{tenant}:{name}"
        tok, until = _TOKENS.get(key, ("", 0.0))
        if not tok or time.time() > until - 30:
            from ..agent import scrape_tools as st
            turl = st._guard_url(d["token_url"])
            resp = httpx.post(turl, data={"grant_type": "client_credentials", "client_id": d["client_id"],
                                          "client_secret": d["client_secret"], **({"scope": d["scope"]} if d.get("scope") else {})},
                              timeout=httpx.Timeout(15.0))
            if resp.status_code >= 400:
                raise WorkspaceError(f"The sign-in {name} was refused by its site ({resp.status_code})")
            j = resp.json()
            tok = str(j.get("access_token") or "")
            if not tok:
                raise WorkspaceError(f"The sign-in {name} got no token back")
            _TOKENS[key] = (tok, time.time() + float(j.get("expires_in") or 3000))
        h["Authorization"] = "Bearer " + tok
    return url, h


# ---------------------------------------------------------------- accounts (which account a step uses)
def accounts(tenant: str) -> list[dict]:
    out: list[dict] = []
    try:
        from sqlalchemy import select
        from ..db import MailAccount, session
        with session() as s:
            for m in s.scalars(select(MailAccount).where(MailAccount.tenant_id == tenant)).all():
                out.append({"value": m.address, "label": m.address, "kind": m.kind, "default": bool(m.is_default),
                            "ok": (m.status or "ok") == "ok"})
    except Exception:   # noqa: BLE001
        pass
    try:
        from .. import googlehub
        for a in (googlehub.status(tenant) or {}).get("accounts") or []:
            e = str(a.get("email") or "")
            if e and not any(x["value"] == e for x in out):
                out.append({"value": e, "label": e, "kind": "google", "default": bool(a.get("first")), "ok": a.get("state") == "ok"})
    except Exception:   # noqa: BLE001
        pass
    return out


# ---------------------------------------------------------------- versions
def _vhash(wf: dict) -> str:
    return hashlib.sha256(json.dumps([wf.get("steps"), wf.get("trigger_kind"), wf.get("trigger_spec"), wf.get("settings"),
                                      wf.get("description")], sort_keys=True, default=str).encode()).hexdigest()


def keep_version(tenant: str, wf: dict, note: str = "") -> str | None:
    """A version of the route as it is now (skipped when nothing changed since the last one)."""
    h = _vhash(wf)
    con = _con(tenant)
    try:
        last = con.execute("SELECT hash FROM route_versions WHERE workflow_id = ? ORDER BY at DESC LIMIT 1", (wf["id"],)).fetchone()
        if last is not None and last["hash"] == h:
            return None
        vid = "rv_" + secrets.token_hex(6)
        con.execute("INSERT INTO route_versions (id, workflow_id, at, hash, description, trigger_kind, trigger_spec, steps, "
                    "settings, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (vid, wf["id"], time.time(), h, wf.get("description") or "", wf.get("trigger_kind") or "manual",
                     json.dumps(wf.get("trigger_spec") or {}), json.dumps(wf.get("steps") or []),
                     json.dumps(wf.get("settings") or {}), str(note or "")[:200]))
        con.execute("DELETE FROM route_versions WHERE workflow_id = ? AND id NOT IN (SELECT id FROM route_versions WHERE "
                    "workflow_id = ? ORDER BY at DESC LIMIT ?)", (wf["id"], wf["id"], VERSIONS_KEEP))
        con.commit()
        return vid
    finally:
        con.close()


def _flat(steps: list) -> dict[str, dict]:
    from .stepdata import _all
    return {str(s.get("id")): s for s in _all(steps or [])}


def versions(tenant: str, wf_id: str) -> list[dict]:
    con = _con(tenant)
    try:
        rows = con.execute("SELECT * FROM route_versions WHERE workflow_id = ? ORDER BY at DESC", (wf_id,)).fetchall()
    finally:
        con.close()
    out, newer = [], None
    for r in reversed(rows):                           # oldest first, to say what each one changed
        steps = json.loads(r["steps"] or "[]")
        cur = _flat(steps)
        if newer is None:
            change = "The first saved version"
        else:
            added = [k for k in cur if k not in newer]
            gone = [k for k in newer if k not in cur]
            edited = [k for k in cur if k in newer and json.dumps(cur[k], sort_keys=True) != json.dumps(newer[k], sort_keys=True)]
            bits = []
            if added:
                bits.append("added " + ", ".join(a.replace("_", " ") for a in added[:4]))
            if gone:
                bits.append("removed " + ", ".join(g.replace("_", " ") for g in gone[:4]))
            if edited:
                bits.append("changed " + ", ".join(e.replace("_", " ") for e in edited[:4]))
            change = "; ".join(bits) or "Its trigger or settings changed"
        out.append({"id": r["id"], "at": r["at"], "trigger": r["trigger_kind"], "steps": len(cur), "change": change,
                    "note": r["note"] or ""})
        newer = cur
    out.reverse()
    if out:
        out[0]["current"] = True
    return out


def version(tenant: str, wf_id: str, vid: str) -> dict | None:
    con = _con(tenant)
    try:
        r = con.execute("SELECT * FROM route_versions WHERE workflow_id = ? AND id = ?", (wf_id, vid)).fetchone()
    finally:
        con.close()
    if r is None:
        return None
    return {"id": r["id"], "at": r["at"], "trigger": r["trigger_kind"], "trigger_spec": json.loads(r["trigger_spec"] or "{}"),
            "steps": json.loads(r["steps"] or "[]"), "settings": json.loads(r["settings"] or "{}"), "description": r["description"] or ""}


def restore(tenant: str, wf: dict, vid: str) -> dict:
    """Bring a version back: saved through the engine's own checks, as a new version."""
    from ..agent import dhara_tools as D
    from . import triggers as TR
    v = version(tenant, wf["id"], vid)
    if v is None:
        raise WorkspaceError("That version is not kept any more")
    settings = D.validate_settings(v["settings"] or {}, tenant)
    spec = TR.validate(v["trigger"], v["trigger_spec"], settings)
    norm = D.validate_steps(v["steps"])
    stamp = time.strftime("%d %b %Y %H:%M", time.localtime(v["at"]))
    new, _ = D.save_workflow(tenant, wf["name"], v["description"][:500], v["trigger"], spec, norm, settings=settings,
                             note=f"Brought back the version of {stamp}")
    con = D._con(tenant)
    try:
        con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?",
                    (D.next_due(new) if v["trigger"] in ("schedule", "event") else None, new["id"]))
        con.commit()
    finally:
        con.close()
    return D.get_workflow(tenant, wf_id=new["id"])


# ---------------------------------------------------------------- sharing
def share_state(tenant: str, wf_id: str) -> dict:
    from ..config import get_settings
    con = _con(tenant)
    try:
        r = con.execute("SELECT * FROM route_shares WHERE workflow_id = ?", (wf_id,)).fetchone()
    finally:
        con.close()
    if r is None or float(r["expires_at"] or 0) < time.time():
        return {"on": False}
    base = (get_settings().public_base_url or "").rstrip("/")
    return {"on": True, "url": (base + r["path"]) if base else r["path"], "expires_at": r["expires_at"]}


def share_make(tenant: str, wf_id: str) -> dict:
    tok = secrets.token_urlsafe(18)
    path = f"/route-view/{tok}"
    con = _con(tenant)
    try:
        con.execute("INSERT OR REPLACE INTO route_shares (workflow_id, token_hash, path, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                    (wf_id, hashlib.sha256(tok.encode()).hexdigest(), path, time.time(), time.time() + SHARE_DAYS * 86400))
        con.commit()
    finally:
        con.close()
    return share_state(tenant, wf_id)


def share_stop(tenant: str, wf_id: str) -> None:
    con = _con(tenant)
    try:
        con.execute("DELETE FROM route_shares WHERE workflow_id = ?", (wf_id,))
        con.commit()
    finally:
        con.close()


def _share_find(token: str) -> tuple[str, dict | None]:
    from pathlib import Path
    from ..agent import dhara_tools as D
    th = hashlib.sha256(str(token or "").encode()).hexdigest()
    root = Path("data") / "dhara"
    for p in sorted(root.glob("*/dhara.db")) if root.is_dir() else []:
        t = p.parent.name
        con = _con(t)
        try:
            r = con.execute("SELECT workflow_id, expires_at FROM route_shares WHERE token_hash = ?", (th,)).fetchone()
        finally:
            con.close()
        if r is not None and float(r["expires_at"] or 0) >= time.time():
            return t, D.get_workflow(t, wf_id=r["workflow_id"])
    return "", None


def _words(s: dict) -> str:
    t = s.get("type")
    label = str(s.get("label") or "").strip()
    kind = {"tool": "Uses " + str(s.get("name") or "a tool").replace("_", " "), "data": "Data: " + str(s.get("op") or ""),
            "ai": "AI: " + str(s.get("op") or ""), "condition": "If / else", "router": "Switch", "loop": "Repeat for each",
            "wait": "Wait", "approval": "Ask first", "notify": "Tell her", "set": "Set a value", "http": "Web request",
            "code": "Code", "filter": "Filter", "subroute": "Run another route", "stop": "Stop the run",
            "respond": "Answer the caller"}.get(t, str(t))
    return f"{label} ({kind})" if label else kind


def view_html(token: str) -> tuple[int, str]:
    import html as H
    from . import triggers as TR
    from .api import _when
    t, wf = _share_find(token)
    if wf is None:
        return 404, TR._shell("Not found", "<h1>This link has stopped</h1><p class='lead'>Ask for a new link.</p>")
    e = H.escape

    def lst(steps, depth=0) -> str:
        items = []
        for s in steps or []:
            if not isinstance(s, dict):
                continue
            sub = ""
            for k, lab in (("then", "If yes"), ("else", "If no"), ("body", "For each item"), ("fallback", "Anything else")):
                if isinstance(s.get(k), list) and (k != "body" or s.get("type") == "loop") and s[k]:
                    sub += f"<li class='br'><b>{lab}</b>{lst(s[k], depth + 1)}</li>"
            for i, rt in enumerate(s.get("routes") or []):
                if isinstance(rt, dict):
                    sub += f"<li class='br'><b>{e(str(rt.get('label') or f'Way {i + 1}'))}</b>{lst(rt.get('steps'), depth + 1)}</li>"
            oe = s.get("on_error")
            if isinstance(oe, dict) and oe.get("steps"):
                sub += f"<li class='br'><b>If it fails</b>{lst(oe['steps'], depth + 1)}</li>"
            items.append(f"<li>{e(_words(s))}{('<ul>' + sub + '</ul>') if sub else ''}</li>")
        return "<ol>" + "".join(items) + "</ol>"
    style = "<style>ol,ul{padding-left:22px;margin:6px 0}li{margin:6px 0}li.br{list-style:none}li.br b{font-weight:500;color:var(--mut)}</style>"
    body = (f"{style}<h1>{e(str(wf['name']).replace('_', ' ').capitalize())}</h1>"
            f"<p class='lead'>{e(wf.get('description') or '')}\nRuns: {e(_when(wf))}</p>{lst(wf.get('steps'))}"
            "<p class='lead'>A read-only view of a Hoola route: its steps, without any of its data or sign-ins.</p>")
    return 200, TR._shell("A Hoola route", body)


def shared_with(wf: dict) -> list[str]:
    return [str(x) for x in ((wf.get("settings") or {}).get("shared_with") or [])]


def team_may_run(tenant: str, actor: str, wf: dict) -> bool:
    if not str(actor).startswith("staff:"):
        return False
    return str(actor)[6:] in shared_with(wf)
