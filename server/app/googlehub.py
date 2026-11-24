"""v0.999.181 GOOGLE CONNECTIONS (owner: "NOW LETS WORK ON GMAIL, SHEET, FORM, DRIVE ETC CONNECTION TO HOOLA" -> the audit
-> design canvas claude.ai/artifact/HatjjJRPedGgA5zfgq1TBK -> "GO").

One place for every Google app Hoola works in: Gmail, Calendar, Drive, Docs, Sheets, Forms, Slides (the everyday apps,
connected with one tap) and Photos, YouTube, Business Profile, Search Console (each when she needs it).

The rules this module keeps:
- A connection is always added to the Hoola account she is signed in as. The state of every connect carries her tenant;
  the callback never issues a session and never switches accounts (the console's old "Connect Google apps" did).
- Her first Google account lives on the sign-in connection (OAuthConnection), which every app already reads when it
  holds that app's permission. A second Google account is saved into each app's own account table, the way the
  per-app links always did, so every app sees both.
- Status is read from what is really stored: the permissions Google granted and whether Google refused the last
  refresh. Nothing is called connected that cannot work.
- Disconnecting an account removes Hoola's access at Google too (Google's revoke endpoint); disconnecting one app
  stops Hoola using that app for that account.
- Which account an app uses first is her choice (google_prefs); an account Google refused is tried last, so one
  expired extra login never blocks one that works.
"""
from __future__ import annotations

import logging
import re
import secrets
from datetime import timedelta
from typing import Any, Callable
from urllib.parse import urlencode

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from . import accounts as acc
from .config import get_settings
from .db import Base, MailLinkState, OAuthConnection, as_utc, now, session

log = logging.getLogger("santosh.googlehub")

BASIC = ("openid", "email", "profile")
G = "https://www.googleapis.com/auth/"
REVOKE = "https://oauth2.googleapis.com/revoke"
USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"
STATE_PREFIX = "ggl_"


class HubError(Exception):
    """Said to her as it is."""


# ---------------------------------------------------------------- the apps
def _scopes(mod: str, name: str) -> list[str]:
    import importlib
    m = importlib.import_module(f"app.{mod}")
    return [x for x in getattr(m, name) if x not in BASIC]


def _model(mod: str, name: str):
    import importlib
    return getattr(importlib.import_module(f"app.{mod}"), name)


# key, letter (in the state), name, group, one line, primary scope (it decides "connected"), scopes to ask, table
APPS: list[dict[str, Any]] = [
    {"key": "gmail", "c": "g", "name": "Gmail", "group": "core",
     "does": "Reads and sorts your mail, drafts replies. Sends only after your yes.",
     "primary": G + "gmail.modify", "ask": lambda: _scopes("mailbox.accounts", "GMAIL_SCOPES"),
     "table": lambda: _model("db", "MailAccount")},
    {"key": "calendar", "c": "c", "name": "Calendar", "group": "core",
     "does": "Sees your day, adds meetings and reminders.",
     "primary": G + "calendar", "ask": lambda: _scopes("cal.accounts", "SCOPES"),
     "table": lambda: _model("db", "CalendarAccount")},
    {"key": "drive", "c": "d", "name": "Drive", "group": "core", "does": "Finds, reads and saves your files.",
     "primary": G + "drive", "ask": lambda: _scopes("drive.accounts", "SCOPES"),
     "table": lambda: _model("drive.models", "DriveAccount")},
    {"key": "docs", "c": "o", "name": "Docs", "group": "core", "does": "Writes and reads documents (they live in Drive).",
     "primary": G + "drive", "ask": lambda: [G + "documents", G + "drive"], "table": None},
    {"key": "sheets", "c": "s", "name": "Sheets", "group": "core", "does": "Reads sheets, adds rows, makes new sheets.",
     "primary": G + "spreadsheets", "ask": lambda: _scopes("sheets.accounts", "SCOPES"),
     "table": lambda: _model("db", "SheetsAccount")},
    {"key": "forms", "c": "f", "name": "Forms", "group": "core", "does": "Makes forms and reads the answers.",
     "primary": G + "forms.body", "ask": lambda: _scopes("forms.accounts", "SCOPES"),
     "table": lambda: _model("forms.models", "FormsAccount")},
    {"key": "slides", "c": "l", "name": "Slides", "group": "core", "does": "Makes presentations from your notes.",
     "primary": G + "presentations", "ask": lambda: _scopes("slides.accounts", "SCOPES"),
     "table": lambda: _model("slides.models", "SlidesAccount")},
    {"key": "photos", "c": "p", "name": "Photos", "group": "more", "does": "Uses only the photos you pick.",
     "primary": G + "photospicker.mediaitems.readonly", "ask": lambda: _scopes("photos.accounts", "SCOPES"),
     "table": lambda: _model("photos.models", "PhotosAccount")},
    {"key": "youtube", "c": "y", "name": "YouTube", "group": "more", "does": "Your channel and uploads, each with your yes.",
     "primary": G + "youtube.force-ssl", "ask": lambda: _scopes("youtube.accounts", "SCOPES"),
     "table": lambda: _model("youtube.models", "YouTubeAccount")},
    {"key": "business", "c": "b", "name": "Business Profile", "group": "more",
     "does": "Your listing, its numbers, and review replies with your yes.",
     "primary": G + "business.manage", "ask": lambda: [G + "business.manage"], "table": None},
    {"key": "searchconsole", "c": "w", "name": "Search Console", "group": "more",
     "does": "How people find your website on Google.",
     "primary": G + "webmasters.readonly", "ask": lambda: [G + "webmasters.readonly"], "table": None},
    # v0.999.185 SHEETS COMPLETE: programs inside her sheets, and BigQuery data in a sheet
    {"key": "appsscript", "c": "a", "name": "Apps Script", "group": "more",
     "does": "Writes small programs inside your sheets, each after your yes.",
     "primary": G + "script.projects", "ask": lambda: [G + "script.projects", G + "spreadsheets"], "table": None},
    {"key": "bigquery", "c": "q", "name": "BigQuery", "group": "more",
     "does": "Puts your BigQuery tables in a sheet (read only).",
     "primary": G + "bigquery.readonly", "ask": lambda: [G + "bigquery.readonly", G + "spreadsheets"], "table": None},
    # v0.999.186 DRIVE COMPLETE: who did what in her Drive
    {"key": "driveactivity", "c": "v", "name": "Drive Activity", "group": "more",
     "does": "Shows who changed, moved, shared or removed your files (read only).",
     "primary": G + "drive.activity.readonly", "ask": lambda: [G + "drive.activity.readonly", G + "drive"], "table": None},
]
BY_KEY = {a["key"]: a for a in APPS}
BY_C = {a["c"]: a for a in APPS}
CORE = [a["key"] for a in APPS if a["group"] == "core"]


def _granted(a: dict, scopes: set[str]) -> bool:
    return a["primary"] in scopes


# ---------------------------------------------------------------- "used first" (her choice per app)
class GooglePref(Base):
    __tablename__ = "google_prefs"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    app: Mapped[str] = mapped_column(String(20), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), default="")


_TABLE_OK: set[int] = set()


def ensure_table() -> None:
    """Self-heal: a database born before this table existed gets it on first use (keyed per engine)."""
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _TABLE_OK:
        return
    GooglePref.__table__.create(eng, checkfirst=True)
    _TABLE_OK.add(id(eng))


def _pref(tenant: str, app: str) -> str:
    ensure_table()
    with session() as s:
        p = s.get(GooglePref, (tenant, app))
        return (p.email if p else "") or ""


def set_first(tenant: str, app: str, email: str) -> dict:
    if app not in BY_KEY:
        raise HubError("That is not a Google app Hoola knows.")
    email = (email or "").strip().lower()
    if email not in {x["email"] for x in status(tenant)["accounts"]}:
        raise HubError("That Google account is not connected to Hoola.")
    ensure_table()
    with session() as s:
        p = s.get(GooglePref, (tenant, app)) or GooglePref(tenant_id=tenant, app=app)
        p.email = email
        s.add(p)
    return {"ok": True, "app": app, "email": email}


def _broken(tenant: str, app: str) -> set[str]:
    """Accounts Google refused for this app (they go last)."""
    out: set[str] = set()
    try:
        with session() as s:
            from .google_auth import _google_conn
            c = _google_conn(s, tenant)
            if c is not None and c.last_error:
                out.add((c.account_email or "").lower())
            a = BY_KEY.get(app)
            if a and a["table"]:
                T = a["table"]()
                for r in s.scalars(select(T).where(T.tenant_id == tenant)).all():
                    if (getattr(r, "status", "ok") or "ok") == "error":
                        out.add((r.address or "").lower())
    except Exception:          # noqa: BLE001 - ordering must never break an app
        log.debug("google order skipped", exc_info=True)
    return out


def arrange(tenant: str, app: str, items: list, address: Callable[[Any], str] | None = None) -> list:
    """Her first choice first, accounts Google refused last, the rest as they were."""
    if len(items) < 2:
        return items
    addr = address or (lambda x: str(getattr(x, "address", "") or "").lower())
    try:
        first = _pref(tenant, app)
    except Exception:          # noqa: BLE001
        first = ""
    bad = _broken(tenant, app)

    def rank(pair):
        i, x = pair
        e = addr(x).lower()
        return (0 if first and e == first else 1, 1 if e in bad else 0, i)
    return [x for _, x in sorted(enumerate(items), key=rank)]


# ---------------------------------------------------------------- connecting
def ready() -> bool:
    return acc.oauth_configured()


def _main(s, tenant: str):
    from .google_auth import _google_conn
    return _google_conn(s, tenant)


def _main_user(s, tenant: str) -> str:
    from .google_auth import _user_ids
    ids = _user_ids(s, tenant)
    return ids[1] if len(ids) > 1 else ids[0]


_HINT = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,24}$")


def is_link_state(state: str) -> bool:
    return (state or "").startswith(STATE_PREFIX)


def start(tenant: str, apps: list[str] | str, surface: str = "web", hint: str = "") -> str:
    """The Google page to open. apps: 'core', or app keys. The state remembers her tenant, the surface and the apps."""
    if not ready():
        raise HubError("Google is not set up on this server yet (GOOGLE_OAUTH_CLIENT_ID / SECRET, PUBLIC_BASE_URL, SECRET_KEY).")
    keys = CORE if apps in ("core", ["core"], None, "", []) else [k for k in ([apps] if isinstance(apps, str) else apps)]
    keys = [k for k in dict.fromkeys(keys) if k in BY_KEY]
    if not keys:
        raise HubError("Choose at least one Google app to connect.")
    scopes: list[str] = list(BASIC)
    for k in keys:
        for x in BY_KEY[k]["ask"]():
            if x not in scopes:
                scopes.append(x)
    surf = "p" if surface == "phone" else "w"
    state = f"{STATE_PREFIX}{surf}{''.join(BY_KEY[k]['c'] for k in keys)}_{secrets.token_urlsafe(18)}"
    with session() as s:
        s.add(MailLinkState(state=state, tenant_id=tenant, provider="ghub"))
        m = _main(s, tenant)
        main_email = (m.account_email if m else "") or ""
    h = (hint or "").strip().lower() or main_email.lower()
    st = get_settings()
    q = {"client_id": st.google_oauth_client_id, "redirect_uri": acc._redirect_uri(), "response_type": "code",
         "scope": " ".join(scopes), "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"}
    if _HINT.match(h):
        q["login_hint"] = h
    q["state"] = state
    from .mailbox import accounts as mail_acc
    return mail_acc.GOOGLE_AUTH + "?" + urlencode(q)


def surface_of(state: str) -> str:
    return "phone" if (state or "").startswith(STATE_PREFIX + "p") else "web"


def _asked(state: str) -> list[str]:
    body = (state or "")[len(STATE_PREFIX) + 1:].split("_", 1)[0]
    return [BY_C[c]["key"] for c in body if c in BY_C]


def finish(code: str, state: str) -> dict[str, Any]:
    """Google came back. Save the access on HER Hoola account; report what was granted and what was left out."""
    from .mailbox import accounts as mail_acc
    st = get_settings()
    with session() as s:
        row = s.get(MailLinkState, state)
        if row is None or row.provider != "ghub" or as_utc(row.created_at) < now() - timedelta(minutes=30):
            raise HubError("This link is too old. Press Connect again.")
        tenant = row.tenant_id
        s.delete(row)
    asked = _asked(state)
    try:
        tok = mail_acc._post(mail_acc.GOOGLE_TOKEN, {"code": code, "client_id": st.google_oauth_client_id,
                                                     "client_secret": st.google_oauth_client_secret,
                                                     "redirect_uri": acc._redirect_uri(), "grant_type": "authorization_code"})
        info = mail_acc._get(USERINFO, tok["access_token"])
    except mail_acc.MailError as e:
        raise HubError(str(e))
    email = (info.get("email") or "").strip().lower()
    if "@" not in email:
        raise HubError("Google did not say which account this is. Try again.")
    if info.get("email_verified") is False:
        raise HubError("Google has not checked the email on this account yet, so Hoola cannot use it.")
    granted = set((tok.get("scope") or "").split())
    refresh = tok.get("refresh_token") or ""
    expiry = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
    where = "main"
    with session() as s:
        m = _main(s, tenant)
        if m is None or (m.account_email or "").lower() == email or not m.refresh_token_enc:
            if m is None:
                m = OAuthConnection(user_id=_main_user(s, tenant), provider="google")
                s.add(m)
            same = (m.account_email or "").lower() == email
            if not refresh and not (same and m.refresh_token_enc):
                raise HubError("Google did not give Hoola lasting access. Press Connect again.")
            old = set((m.scopes or "").split()) if same else set()
            m.account_email = email
            m.access_token_enc = acc.encrypt(tok["access_token"])
            if refresh:
                m.refresh_token_enc = acc.encrypt(refresh)
            m.scopes = " ".join(sorted(old | granted))
            m.expiry = expiry
            m.last_error = None
        else:
            where = "extra"
    if where == "main":
        from . import google_auth
        google_auth._DEAD.pop(tenant, None)
    else:
        if not refresh:
            raise HubError("Google did not give Hoola lasting access. Press Connect again.")
        _save_extra(tenant, email, info.get("name") or "", tok, granted, expiry)
    if G + "webmasters.readonly" in granted and refresh:
        _save_gsc(tenant, email, tok, granted, expiry)
    got = [a["key"] for a in APPS if _granted(a, granted)]
    miss = [k for k in asked if k not in got]
    log.info("google connected for %s: %s (%s), left out %s", tenant, ",".join(got) or "-", where, ",".join(miss) or "-")
    return {"tenant": tenant, "email": email, "got": got, "miss": miss, "where": where, "surface": surface_of(state)}


def _save_extra(tenant: str, email: str, name: str, tok: dict, granted: set[str], expiry) -> None:
    """A second Google account: into each app's own table (every app already reads those)."""
    from .mailbox import accounts as mail_acc
    at, rt = acc.encrypt(tok["access_token"]), acc.encrypt(tok["refresh_token"])
    for a in APPS:
        if not a["table"] or not _granted(a, granted):
            continue
        if a["key"] == "gmail":
            mail_acc._save(tenant, "gmail", email, name, access_token_enc=at, refresh_token_enc=rt,
                           scopes=" ".join(sorted(granted)), expiry=expiry)
            continue
        T = a["table"]()
        with session() as s:
            n = len(s.scalars(select(T.id).where(T.tenant_id == tenant)).all())
            r = s.scalar(select(T).where(T.tenant_id == tenant, T.address == email))
            if r is None:
                r = T(tenant_id=tenant, address=email, is_default=(n == 0))
                s.add(r)
            if hasattr(r, "display_name") and name:
                r.display_name = name[:120]
            r.access_token_enc, r.refresh_token_enc, r.expiry = at, rt, expiry
            r.status, r.last_error = "ok", ""


def _save_gsc(tenant: str, email: str, tok: dict, granted: set[str], expiry) -> None:
    try:
        from .seo.service import SeoGoogle
        with session() as s:
            g = s.get(SeoGoogle, tenant) or SeoGoogle(tenant_id=tenant)
            s.add(g)
            g.address = email
            g.access_token_enc = acc.encrypt(tok["access_token"])
            g.refresh_token_enc = acc.encrypt(tok["refresh_token"])
            g.expiry, g.status, g.last_error = expiry, "ok", ""
            g.scopes = " ".join(sorted(granted))
    except Exception:          # noqa: BLE001 - Search Console is one app; the rest are saved
        log.exception("search console save failed")


# ---------------------------------------------------------------- status
def status(tenant: str) -> dict[str, Any]:
    """Every Google account and every Google app, as they really are."""
    accts: dict[str, dict] = {}

    def acct(email: str) -> dict:
        e = (email or "").lower()
        return accts.setdefault(e, {"email": e, "first": False, "state": "ok", "error": "", "apps": {}})
    with session() as s:
        m = _main(s, tenant)
        if m is not None and m.refresh_token_enc and m.account_email:
            a = acct(m.account_email)
            a["first"] = True
            sc = set((m.scopes or "").split())
            dead = bool(m.last_error)
            if dead:
                a["state"], a["error"] = "expired", str(m.last_error)[:300]
            for ap in APPS:
                if ap["key"] != "searchconsole" and _granted(ap, sc):
                    a["apps"][ap["key"]] = "expired" if dead else "ok"
        signin = (m.account_email or "").lower() if (m is not None and not m.refresh_token_enc) else ""
        for ap in APPS:
            if not ap["table"]:
                continue
            T = ap["table"]()
            q = select(T).where(T.tenant_id == tenant)
            if ap["key"] == "gmail":
                q = q.where(T.kind == "gmail")
            for r in s.scalars(q).all():
                bad = (getattr(r, "status", "ok") or "ok") == "error"
                a = acct(r.address)
                a["apps"][ap["key"]] = "expired" if bad else a["apps"].get(ap["key"], "ok")
                if bad and a["state"] == "ok":
                    a["state"], a["error"] = "expired", str(getattr(r, "last_error", "") or "")[:300]
                if ap["key"] == "drive" and not bad:
                    a["apps"].setdefault("docs", "ok")
    try:
        from .seo.service import SeoGoogle
        with session() as s:
            g = s.get(SeoGoogle, tenant)
            if g is not None and g.address:
                a = acct(g.address)
                a["apps"]["searchconsole"] = "expired" if (g.status or "ok") == "error" else "ok"
    except Exception:          # noqa: BLE001
        pass
    for a in accts.values():
        if a["state"] == "ok" and any(v == "expired" for v in a["apps"].values()):
            a["state"] = "expired"
    order = sorted(accts.values(), key=lambda a: (not a["first"], a["email"]))
    apps = []
    for ap in APPS:
        on = [a["email"] for a in order if a["apps"].get(ap["key"]) == "ok"]
        off = [a["email"] for a in order if a["apps"].get(ap["key"]) == "expired"]
        st = "ok" if on and not off else "expired" if off else "none"
        first = ""
        if on or off:
            pref = ""
            try:
                pref = _pref(tenant, ap["key"])
            except Exception:  # noqa: BLE001
                pass
            first = pref if pref in on + off else (on + off)[0]
        apps.append({"key": ap["key"], "name": ap["name"], "group": ap["group"], "does": ap["does"], "state": st,
                     "working": on, "expired": off, "first": first})
    return {"ready": ready(), "signin": signin, "accounts": [{**a, "apps": sorted(a["apps"])} for a in order],
            "apps": apps, "core": CORE}


def summary(tenant: str) -> dict[str, Any]:
    """One line for a Settings row / sidebar dot."""
    st = status(tenant)
    working = sum(1 for a in st["apps"] if a["state"] == "ok")
    expired = [a["email"] for a in st["accounts"] if a["state"] == "expired"]
    return {"working": working, "expired": len(expired), "accounts": len(st["accounts"]),
            "line": (f"{working} apps working" if working else "Not connected")
            + (f" · {len(expired)} account{'s' if len(expired) > 1 else ''} needs reconnecting" if expired else "")}


# ---------------------------------------------------------------- disconnecting
def _revoke(token_enc: str | None) -> bool:
    if not token_enc:
        return False
    try:
        import httpx
        tok = acc.decrypt(token_enc)
        r = httpx.post(REVOKE, data={"token": tok}, timeout=15)
        return r.status_code in (200, 400)       # 400 = Google already forgot it
    except Exception:          # noqa: BLE001 - the stored copy goes either way
        log.warning("google revoke did not answer", exc_info=True)
        return False


def disconnect(tenant: str, email: str, app: str = "") -> dict[str, Any]:
    """app '' = the whole account: Hoola's access removed at Google and every stored copy gone. app = one app: Hoola
    stops using that app for this account."""
    email = (email or "").strip().lower()
    if app and app not in BY_KEY:
        raise HubError("That is not a Google app Hoola knows.")
    keys = [app] if app else [a["key"] for a in APPS]
    found = False
    revoked = False
    with session() as s:
        m = _main(s, tenant)
        if m is not None and (m.account_email or "").lower() == email:
            found = True
            if app:
                drop = set(BY_KEY[app]["ask"]())
                if app == "drive":
                    drop |= set(BY_KEY["docs"]["ask"]())
                m.scopes = " ".join(x for x in (m.scopes or "").split() if x not in drop)
            else:
                revoked = _revoke(m.refresh_token_enc) or revoked
                m.refresh_token_enc = None
                m.access_token_enc = None
                m.scopes = " ".join(BASIC)
                m.last_error = None
    for k in keys:
        ap = BY_KEY[k]
        if not ap["table"]:
            continue
        T = ap["table"]()
        with session() as s:
            for r in s.scalars(select(T).where(T.tenant_id == tenant, T.address == email)).all():
                if k == "gmail" and getattr(r, "kind", "gmail") != "gmail":
                    continue
                found = True
                if not app:
                    revoked = _revoke(r.refresh_token_enc) or revoked
                s.delete(r)
    if "searchconsole" in keys:
        try:
            from .seo.service import SeoGoogle
            with session() as s:
                g = s.get(SeoGoogle, tenant)
                if g is not None and (g.address or "").lower() == email:
                    found = True
                    if not app:
                        revoked = _revoke(g.refresh_token_enc) or revoked
                    s.delete(g)
        except Exception:      # noqa: BLE001
            pass
    if not found:
        raise HubError("That Google account is not connected to Hoola.")
    return {"ok": True, "email": email, "app": app, "revoked": revoked}


# ---------------------------------------------------------------- words for her
def where_to_connect(app: str = "") -> str:
    name = BY_KEY[app]["name"] if app in BY_KEY else "Google"
    return (f"To connect {name}: on the web console open Connectors > Google, or in the phone app open Settings > Google, "
            "and press Connect.")
