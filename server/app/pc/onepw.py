"""v0.999.51 1PASSWORD SIGN-INS (owner, 20 Nov 2026: "1Password login (Grok Bot) ... LETS WORK ON IT FIRST").

Grok Bot signs in from her 1Password with her approval and never sees the password. Here, through 1Password's own
official route - a SERVICE ACCOUNT and the official SDK (onepassword-sdk):

- She makes a vault for Hoola in 1Password (e.g. "Hoola"), puts the portal logins Hoola may use in it, and creates a
  service account with READ access to that vault only. She pastes its token ONCE into the form on the Hoola Computer
  page (never the chat). It is sealed with the ID-locker key; no route ever returns it.
- Hoola reads only the vault she picked. A sign-in box on a site that one of its logins lists (by website) shows
  "Use 1Password sign-in" on the private form; the user name / password are typed into the PC only on her tap and
  never reach the model, a log or the chat.
- A login that holds a one-time code (TOTP): a 2-step box on the same site, right after that sign-in, is filled with
  the code 1Password computes - said in her chat.
- Never bank / card / payment / UPI / broker logins (pc/vault.money_site), and credit-card items are never read.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session

log = logging.getLogger("santosh.pc")
APP_NAME, APP_VER = "Hoola", "0.999.51"
CLIENT_TTL = 25 * 60


class OnePwLink(Base):
    __tablename__ = "onepw_links"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    token_sealed: Mapped[str] = mapped_column(Text, default="")
    vault_id: Mapped[str] = mapped_column(String(80), default="")
    vault_name: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_TABLE_OK: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _TABLE_OK:
        return
    OnePwLink.__table__.create(bind=eng, checkfirst=True)
    _TABLE_OK.add(id(eng))


class OnePwError(Exception):
    pass


def available() -> bool:
    try:
        import onepassword  # noqa: F401
        return True
    except Exception:
        return False


_CLIENTS: dict[str, tuple[Any, float]] = {}


async def _client_for_token(token: str):
    if not available():
        raise OnePwError("1Password is not installed on the server yet (onepassword-sdk) - run the deploy again.")
    from onepassword.client import Client
    try:
        return await Client.authenticate(auth=token, integration_name=APP_NAME, integration_version=APP_VER)
    except Exception as e:     # the SDK's own error text never carries the token
        raise OnePwError(f"1Password did not accept that token ({type(e).__name__}). Check it is a service account "
                         "token (starts with ops_) and not expired.")


def _row(tenant: str) -> OnePwLink | None:
    ensure_table()
    with session() as s:
        r = s.get(OnePwLink, tenant)
        if r is not None:
            s.expunge(r)
        return r


async def _client(tenant: str):
    hit = _CLIENTS.get(tenant)
    if hit and time.time() - hit[1] < CLIENT_TTL:
        return hit[0]
    r = _row(tenant)
    if r is None or not r.token_sealed:
        raise OnePwError("1Password is not connected.")
    from ..idvault import _open
    c = await _client_for_token(_open(r.token_sealed))
    _CLIENTS[tenant] = (c, time.time())
    return c


def status(tenant: str) -> dict[str, Any]:
    r = _row(tenant)
    return {"installed": available(), "connected": bool(r and r.token_sealed and r.vault_id),
            "vault": (r.vault_name if r else ""), "needs_vault": bool(r and r.token_sealed and not r.vault_id)}


async def connect(tenant: str, token: str, vault_id: str = "") -> dict[str, Any]:
    """Her service-account token (from the form). Checks it with 1Password, keeps it sealed, and picks the vault: the
    only one it can see, or the one she chose. Returns the vaults (names only) when she has to choose."""
    token = str(token or "").strip()
    r0 = _row(tenant)
    if not token and r0 is not None and r0.token_sealed:      # choosing the vault after a token with several
        from ..idvault import _open
        token = _open(r0.token_sealed)
    if not token.startswith("ops_") or len(token) > 4000:
        raise OnePwError("That is not a 1Password service account token (it starts with ops_).")
    c = await _client_for_token(token)
    try:
        vaults = [v for v in await c.vaults.list()]
    except Exception as e:
        raise OnePwError(f"1Password: could not list the vaults ({type(e).__name__}).")
    if not vaults:
        raise OnePwError("This service account cannot see any vault. Give it read access to your Hoola vault.")
    pick = next((v for v in vaults if v.id == vault_id), None) if vault_id else (vaults[0] if len(vaults) == 1 else None)
    from ..idvault import _seal
    ensure_table()
    with session() as s:
        r = s.get(OnePwLink, tenant) or OnePwLink(tenant_id=tenant)
        s.add(r)
        r.token_sealed = _seal(token)
        r.vault_id, r.vault_name = (pick.id, pick.title) if pick else ("", "")
        r.created_at = now()
    _CLIENTS[tenant] = (c, time.time())
    log.info("1password connected for %s (%d vault(s) visible, using %s)", tenant, len(vaults),
             pick.title if pick else "none yet")
    out = status(tenant)
    if pick is None:
        out["vaults"] = [{"id": v.id, "name": v.title} for v in vaults]
    elif len(vaults) > 1:
        out["note"] = (f"This token can see {len(vaults)} vaults; Hoola reads only '{pick.title}'. Safer: give the "
                       "service account access to that one vault only.")
    return out


def disconnect(tenant: str) -> bool:
    _CLIENTS.pop(tenant, None)
    ensure_table()
    with session() as s:
        r = s.get(OnePwLink, tenant)
        if r is None:
            return False
        s.delete(r)
        return True


def _host_key(url: str) -> str:
    from .vault import key_of
    u = str(url or "")
    return key_of("", u if "://" in u else "https://" + u)


async def find(tenant: str, key: str, site: str = "") -> dict[str, Any] | None:
    """The login in her Hoola vault for this site (by its websites), as {id, title, user} - user masked."""
    from .vault import money_site, _mask
    if not key or money_site(site, key):
        return None
    r = _row(tenant)
    if r is None or not r.vault_id:
        return None
    try:
        c = await _client(tenant)
        items = await c.items.list(r.vault_id)
    except Exception as e:
        log.warning("1password lookup failed for %s: %s", tenant, type(e).__name__)
        return None
    for it in items:
        cat = str(getattr(getattr(it, "category", ""), "value", getattr(it, "category", "")))
        if cat != "Login":
            continue
        if any(_host_key(w.url) == key for w in (it.websites or [])):
            user = ""
            try:
                full = await c.items.get(r.vault_id, it.id)
                user = _fields(full)[0]
            except Exception:
                pass
            return {"id": it.id, "title": it.title, "user": _mask(user)}
    return None


def _fields(item) -> tuple[str, str, str]:
    """(user name, password, current one-time code) of a 1Password login item."""
    user = pw = code = ""
    first_text = first_secret = ""
    for f in item.fields or []:
        ft = str(getattr(f.field_type, "value", f.field_type))
        fid = str(f.id or "").lower()
        val = str(f.value or "")
        if ft == "Totp":
            det = getattr(f, "details", None)
            code = str(getattr(getattr(det, "content", None), "code", "") or "")
        elif fid == "password":
            pw = val
        elif fid == "username":
            user = val
        elif ft == "Concealed" and not first_secret:
            first_secret = val
        elif ft in ("Text", "Email") and not first_text:
            first_text = val
    return (user or first_text), (pw or first_secret), code


async def open_(tenant: str, item_id: str) -> tuple[str, str, str]:
    """The real values for the PC's fields only - never returned to the model or a client."""
    r = _row(tenant)
    if r is None or not r.vault_id:
        raise OnePwError("1Password is not connected.")
    c = await _client(tenant)
    item = await c.items.get(r.vault_id, item_id)
    cat = str(getattr(getattr(item, "category", ""), "value", getattr(item, "category", "")))
    if cat != "Login":
        raise OnePwError("Only 1Password logins are used.")
    with session() as s:
        row = s.get(OnePwLink, tenant)
        if row is not None:
            row.used_at = now()
    return _fields(item)
