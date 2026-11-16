"""v0.942 CONNECT GITHUB LIKE CLAUDE CODE - a GitHub App install, no pasted token.

Claude Code connects GitHub by having you INSTALL its GitHub App on the repos you pick; it never asks for a personal
access token. Tokens are minted on demand, server-side, and are short-lived (about an hour) and scoped to exactly the
repos you installed on. Hoola does the same with its OWN GitHub App.

The owner creates the App once (GitHub > Settings > Developer settings > GitHub Apps), with these repository
permissions - Contents: read & write, Pull requests: read & write, Checks: read, Actions: read & write (for her
deploys), Webhooks: read & write - and puts the App id, slug and private key in the VPS .env. Nothing here is a
secret the user types; she just taps Connect and picks her repos on GitHub.

This module mints the tokens; `service._token` uses one when the tenant has an installation. No token is ever stored:
only the installation id is kept, and a fresh installation token is minted (and briefly cached) when needed."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from ..config import get_settings

log = logging.getLogger("hoola.devsahayak.ghapp")

_API = "https://api.github.com"
_tok_cache: dict[int, tuple[str, float]] = {}   # installation_id -> (token, expires_at epoch)


def configured() -> bool:
    st = get_settings()
    return bool((getattr(st, "github_app_id", "") or "").strip() and _private_key())


def _private_key() -> str:
    raw = (getattr(get_settings(), "github_app_private_key", "") or "").strip()
    if not raw:
        return ""
    # the .env often carries the PEM with literal \n; make it real newlines
    if "\\n" in raw and "-----BEGIN" in raw:
        raw = raw.replace("\\n", "\n")
    if "-----BEGIN" not in raw:
        # v0.943 the vps-ops github_app job writes the PEM base64-encoded on one line (no awk, no newlines in .env)
        try:
            import base64
            dec = base64.b64decode(raw, validate=False).decode("utf-8", errors="strict")
            if "-----BEGIN" in dec:
                raw = dec.strip()
        except Exception:
            pass
    return raw


def check() -> dict[str, Any]:
    """Ask GitHub whether the App id + private key work (GET /app with the App JWT). Names only, never the key."""
    if not configured():
        return {"ok": False, "why": "GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY is missing or unreadable"}
    try:
        app = _req("GET", "/app", _app_jwt(), app_jwt=True)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"ok": False, "why": "GitHub said 404: no GitHub App has this App ID - check the number next to 'App ID' on the App's page"}
        if e.code == 401:
            return {"ok": False, "why": "GitHub said 401: this private key does not belong to this App - generate a new key on the App's page"}
        return {"ok": False, "why": f"GitHub said {e.code}: the App ID and the key do not match"}
    except Exception as e:
        return {"ok": False, "why": f"could not reach GitHub: {str(e)[:120]}"}
    got_slug = str(app.get("slug") or "")
    return {"ok": True, "app": got_slug, "slug_matches": (not slug()) or got_slug == slug(),
            "installs": app.get("installations_count")}


def slug() -> str:
    return (getattr(get_settings(), "github_app_slug", "") or "").strip()


def _app_jwt() -> str:
    import jwt  # PyJWT
    app_id = (getattr(get_settings(), "github_app_id", "") or "").strip()
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 9 * 60, "iss": app_id}
    return jwt.encode(payload, _private_key(), algorithm="RS256")


def _req(method: str, path: str, token: str, *, app_jwt: bool = False, body: Any = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(_API + path, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Hoola-Code"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode() or "{}"
    return json.loads(raw) if raw.strip() else {}


def installation_token(installation_id: int) -> str:
    """A fresh installation access token (cached ~55 min). Scoped to the repos she installed on."""
    now = time.time()
    cached = _tok_cache.get(installation_id)
    if cached and cached[1] - 120 > now:
        return cached[0]
    out = _req("POST", f"/app/installations/{installation_id}/access_tokens", _app_jwt(), app_jwt=True, body={})
    token = str(out.get("token") or "")
    if not token:
        raise RuntimeError("GitHub did not return an installation token")
    # expires_at like 2026-11-16T03:30:00Z; cache conservatively for 50 min
    _tok_cache[installation_id] = (token, now + 50 * 60)
    return token


def account_of(installation_id: int) -> str:
    try:
        out = _req("GET", f"/app/installations/{installation_id}", _app_jwt(), app_jwt=True)
        acc = out.get("account") or {}
        return str(acc.get("login") or "")
    except Exception:
        log.debug("ghapp account lookup failed", exc_info=True)
        return ""


def installed_repos(installation_id: int) -> list[dict[str, Any]]:
    """The repos she installed the App on (GET /installation/repositories, with the installation token)."""
    token = installation_token(installation_id)
    out: list[dict[str, Any]] = []
    page = 1
    while page <= 10:
        r = _req("GET", f"/installation/repositories?per_page=100&page={page}", token)
        rows = r.get("repositories") if isinstance(r, dict) else None
        if not rows:
            break
        out.extend(rows)
        if len(rows) < 100:
            break
        page += 1
    return out


def install_url(state: str) -> str:
    s = slug()
    base = f"https://github.com/apps/{s}/installations/new" if s else "https://github.com/settings/installations"
    return f"{base}?state={state}" if state else base


# ------------------------------------------------------------------ v0.956 sign in with GitHub (one tap, like Claude Code)
# The install page alone cannot say WHOSE install it is: an App already installed never sends the signed state back,
# and an installation id in a URL proves nothing. So Connect signs her in on GitHub (the App's own user authorization;
# when she has said yes once it passes straight through) and Hoola asks GitHub which installs of THIS App she can
# reach. Only an install on that list is bound to her. Nothing is kept from the sign-in: the user token is used once.
_WEB = "https://github.com"


def oauth_ready() -> bool:
    st = get_settings()
    return bool(configured() and (getattr(st, "github_app_client_id", "") or "").strip()
                and (getattr(st, "github_app_client_secret", "") or "").strip())


def callback_url() -> str:
    base = (getattr(get_settings(), "public_base_url", "") or "").strip().rstrip("/")
    return f"{base}/api/devsahayak/github/installed" if base else ""


def authorize_url(state: str) -> str:
    from urllib.parse import urlencode
    q = {"client_id": (get_settings().github_app_client_id or "").strip(), "state": state}
    cb = callback_url()
    if cb:
        q["redirect_uri"] = cb
    return f"{_WEB}/login/oauth/authorize?{urlencode(q)}"


def user_token(code: str) -> str:
    """Trade the one-time code for a user token (used at once, never stored)."""
    st = get_settings()
    body = {"client_id": (st.github_app_client_id or "").strip(),
            "client_secret": (st.github_app_client_secret or "").strip(), "code": code}
    cb = callback_url()
    if cb:
        body["redirect_uri"] = cb
    req = urllib.request.Request(_WEB + "/login/oauth/access_token", data=json.dumps(body).encode(), method="POST",
                                 headers={"Accept": "application/json", "Content-Type": "application/json",
                                          "User-Agent": "Hoola-Code"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read().decode() or "{}")
    tok = str(out.get("access_token") or "")
    if not tok:
        raise RuntimeError(str(out.get("error_description") or out.get("error") or "GitHub did not sign you in"))
    return tok


def user_installations(token: str) -> list[dict[str, Any]]:
    """The installs of THIS App the signed-in user can reach (GET /user/installations), newest first."""
    app_id = str((get_settings().github_app_id or "").strip())
    out = _req("GET", "/user/installations?per_page=100", token)
    rows = out.get("installations") if isinstance(out, dict) else None
    keep = [i for i in (rows or []) if not app_id or str(i.get("app_id") or "") == app_id]
    return sorted(keep, key=lambda i: str(i.get("updated_at") or i.get("created_at") or ""), reverse=True)


def user_login(token: str) -> str:
    try:
        return str((_req("GET", "/user", token) or {}).get("login") or "")
    except Exception:
        return ""


def pick_install(rows: list[dict[str, Any]], login: str, wanted: int = 0) -> dict[str, Any] | None:
    """The install to bind: the one GitHub just sent (if it is on her list), else her own account's, else the newest."""
    if wanted:
        for i in rows:
            if int(i.get("id") or 0) == int(wanted):
                return i
    for i in rows:
        if login and str((i.get("account") or {}).get("login") or "").lower() == login.lower():
            return i
    return rows[0] if rows else None


# ------------------------------------------------------------------ the signed state (maps the callback back to her)
def _secret() -> bytes:
    st = get_settings()
    return (getattr(st, "secret_key", "") or getattr(st, "api_key", "") or "hoola-ghapp").encode()


def make_state(tenant: str) -> str:
    ts = str(int(time.time()))
    sig = hmac.new(_secret(), f"{tenant}|{ts}".encode(), hashlib.sha256).hexdigest()[:24]
    import base64
    raw = f"{tenant}|{ts}|{sig}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def read_state(state: str) -> str:
    """Return the tenant the state was made for, or '' if it is bad or older than an hour."""
    import base64
    try:
        pad = "=" * (-len(state) % 4)
        raw = base64.urlsafe_b64decode(state + pad).decode()
        tenant, ts, sig = raw.split("|", 2)
    except Exception:
        return ""
    good = hmac.new(_secret(), f"{tenant}|{ts}".encode(), hashlib.sha256).hexdigest()[:24]
    if not hmac.compare_digest(sig, good):
        return ""
    if abs(time.time() - int(ts)) > 3600:
        return ""
    return tenant
