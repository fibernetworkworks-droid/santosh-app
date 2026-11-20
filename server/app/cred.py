"""v0.999.54 HOOLA CRED - Hoola's own password manager (owner, 20 Nov 2026: "LETS BUILD OUR OWN 1PASSWORD -- WE NAME IT A
HOOLA CRED"; her choices: "Master password + Hoola use", first release = vault app on console + phone, 2-step codes,
autofill in her browser, safety check + import).

ZERO KNOWLEDGE, like 1Password: her master password never leaves her device. On her device (console page / the phone's
page / the Hoola browser extension) PBKDF2-SHA256 (600,000 rounds, her own random salt) turns it into a key that
unwraps her vault key; every item (title, user name, password, sites, 2-step secret, notes, folder) is encrypted there
with AES-256-GCM before it is sent. This server keeps only: the salt, the round count, the WRAPPED vault key and each
item's ciphertext + nonce. It cannot open any of them - and nothing here ever tries.

HOOLA MAY USE: a login she switches to "Hoola may use" is ALSO sent once (decrypted on her device) to be sealed with the
server's key into her Saved sign-ins (pc/vault.py, one row per site, its 2-step secret too), so the Hoola PC can sign
in for her - still only on her tap on the private sign-in form. Switching it off removes those copies. Bank / card /
payment logins are never accepted for Hoola use.

Breach check: the k-anonymity range API of Have I Been Pwned - her device sends only the first 5 characters of the
password's SHA-1; the server forwards just that prefix (CSP keeps her page on this server).
"""
from __future__ import annotations

import base64
import logging
import re
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

log = logging.getLogger("santosh.cred")

MAX_ITEMS = 2000
MAX_CT = 96 * 1024
MIN_ITERS = 100_000
_B64 = re.compile(r"^[A-Za-z0-9+/=_-]{8,}$")


class CredVault(Base):
    __tablename__ = "cred_vaults"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salt: Mapped[str] = mapped_column(String(80))
    iters: Mapped[int] = mapped_column(Integer, default=600_000)
    wrapped: Mapped[str] = mapped_column(Text)          # {"iv": b64, "ct": b64} of the vault key under her master key
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CredItem(Base):
    __tablename__ = "cred_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cri"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    iv: Mapped[str] = mapped_column(String(40))
    ct: Mapped[str] = mapped_column(Text)
    hoola: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_TABLE_OK: set[int] = set()


def ensure_table() -> None:
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _TABLE_OK:
        return
    CredVault.__table__.create(bind=eng, checkfirst=True)
    CredItem.__table__.create(bind=eng, checkfirst=True)
    _TABLE_OK.add(id(eng))


class CredError(Exception):
    pass


def _b64ok(v: str, cap: int) -> str:
    v = str(v or "")
    if not v or len(v) > cap or not _B64.match(v):
        raise CredError("That is not encrypted data.")
    return v


def _wrapped_ok(w: dict) -> str:
    import json
    if not isinstance(w, dict):
        raise CredError("Bad vault key.")
    return json.dumps({"iv": _b64ok(w.get("iv", ""), 40), "ct": _b64ok(w.get("ct", ""), 200)})


def view_vault(tenant: str) -> dict[str, Any]:
    import json
    ensure_table()
    with session() as s:
        v = s.get(CredVault, tenant)
        if v is None:
            return {"exists": False}
        items = s.execute(select(CredItem).where(CredItem.tenant_id == tenant).order_by(CredItem.updated_at.desc())
                          ).scalars().all()
        return {"exists": True, "salt": v.salt, "iters": v.iters, "wrapped": json.loads(v.wrapped),
                "items": [{"id": i.id, "iv": i.iv, "ct": i.ct, "hoola": bool(i.hoola), "version": i.version,
                           "updated": i.updated_at.isoformat() if i.updated_at else ""} for i in items]}


def create_vault(tenant: str, salt: str, iters: int, wrapped: dict) -> dict[str, Any]:
    ensure_table()
    if int(iters or 0) < MIN_ITERS:
        raise CredError("Too few rounds for the master key.")
    with session() as s:
        if s.get(CredVault, tenant) is not None:
            raise CredError("Your Hoola Cred vault already exists.")
        s.add(CredVault(tenant_id=tenant, salt=_b64ok(salt, 80), iters=int(iters), wrapped=_wrapped_ok(wrapped)))
    log.info("hoola cred vault created for %s", tenant)
    return {"ok": True}


def rewrap(tenant: str, salt: str, iters: int, wrapped: dict) -> dict[str, Any]:
    """A new master password: her device re-wrapped the same vault key (the items stay as they are)."""
    ensure_table()
    if int(iters or 0) < MIN_ITERS:
        raise CredError("Too few rounds for the master key.")
    with session() as s:
        v = s.get(CredVault, tenant)
        if v is None:
            raise CredError("No vault yet.")
        v.salt, v.iters, v.wrapped, v.updated_at = _b64ok(salt, 80), int(iters), _wrapped_ok(wrapped), now()
    log.info("hoola cred master password changed for %s", tenant)
    return {"ok": True}


def delete_vault(tenant: str) -> dict[str, Any]:
    ensure_table()
    from .pc import vault as pcv
    with session() as s:
        n = 0
        for i in s.execute(select(CredItem).where(CredItem.tenant_id == tenant)).scalars().all():
            s.delete(i)
            n += 1
        v = s.get(CredVault, tenant)
        if v is not None:
            s.delete(v)
    pcv.delete_from_cred(tenant, None)
    log.info("hoola cred vault deleted for %s (%d items)", tenant, n)
    return {"ok": True, "deleted": n}


def _need_vault(s, tenant: str) -> None:
    if s.get(CredVault, tenant) is None:
        raise CredError("Make your vault first.")


def add_item(tenant: str, iv: str, ct: str) -> dict[str, Any]:
    from sqlalchemy import func
    ensure_table()
    with session() as s:
        _need_vault(s, tenant)
        n = s.execute(select(func.count()).select_from(CredItem).where(CredItem.tenant_id == tenant)).scalar() or 0
        if n >= MAX_ITEMS:
            raise CredError(f"A vault holds up to {MAX_ITEMS} items.")
        i = CredItem(tenant_id=tenant, iv=_b64ok(iv, 40), ct=_b64ok(ct, MAX_CT))
        s.add(i)
        s.flush()
        return {"id": i.id, "version": i.version}


def put_item(tenant: str, iid: str, iv: str, ct: str, version: int) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        i = s.get(CredItem, iid)
        if i is None or i.tenant_id != tenant:
            raise CredError("Not found.")
        if int(version or 0) != i.version:
            raise CredError("This item changed on another device - reload it first.")
        i.iv, i.ct, i.version, i.updated_at = _b64ok(iv, 40), _b64ok(ct, MAX_CT), i.version + 1, now()
        return {"id": i.id, "version": i.version}


def delete_item(tenant: str, iid: str) -> bool:
    from .pc import vault as pcv
    ensure_table()
    with session() as s:
        i = s.get(CredItem, iid)
        if i is None or i.tenant_id != tenant:
            return False
        s.delete(i)
    pcv.delete_from_cred(tenant, iid)
    return True


def set_hoola(tenant: str, iid: str, on: bool, title: str = "", username: str = "", password: str = "",
              urls: list[str] | None = None, totp: str = "") -> dict[str, Any]:
    """Her switch 'Hoola may use': the login's values (sent from her device once) sealed into Saved sign-ins."""
    from .pc import vault as pcv
    ensure_table()
    with session() as s:
        i = s.get(CredItem, iid)
        if i is None or i.tenant_id != tenant:
            raise CredError("Not found.")
    pcv.delete_from_cred(tenant, iid)
    keys: list[str] = []
    if on:
        if not password:
            raise CredError("Hoola can use a login only when it has a password.")
        for u in (urls or [])[:10]:
            k = pcv.key_of(title, u if "://" in u else "https://" + u)
            if k and k not in keys:
                keys.append(k)
        if not keys:
            raise CredError("Add the site's address to this login first, so Hoola knows where to use it.")
        if any(pcv.money_site(title, k) for k in keys):
            raise CredError("Bank, card and payment sign-ins are never given to Hoola.")
        if totp and not pcv.totp_secret(totp):
            raise CredError("That 2-step key is not valid.")
        for k in keys:
            pcv.save(tenant, k, title or k, username, password, cred_item=iid, totp=totp)
    with session() as s:
        i = s.get(CredItem, iid)
        if i is not None:
            i.hoola = bool(on)
    log.info("hoola cred item %s hoola-use=%s (%d site(s)) for %s", iid, bool(on), len(keys), tenant)
    return {"hoola": bool(on), "sites": keys}


# ------------------------------------------------------------------------------------------------ breach check
_PWNED: dict[str, tuple[str, float]] = {}


def pwned_range(prefix: str) -> str:
    """Have I Been Pwned range: only the 5-hex prefix of the SHA-1 ever leaves (k-anonymity)."""
    p = str(prefix or "").upper()
    if not re.fullmatch(r"[0-9A-F]{5}", p):
        raise CredError("Bad prefix.")
    hit = _PWNED.get(p)
    if hit and time.time() - hit[1] < 3600:
        return hit[0]
    import httpx
    r = httpx.get(f"https://api.pwnedpasswords.com/range/{p}", timeout=15,
                  headers={"User-Agent": "Hoola-Cred", "Add-Padding": "true"})
    r.raise_for_status()
    _PWNED[p] = (r.text, time.time())
    if len(_PWNED) > 2000:
        _PWNED.pop(next(iter(_PWNED)))
    return r.text


# ------------------------------------------------------------------------------------------------ routes
class VaultIn(BaseModel):
    salt: str
    iters: int
    wrapped: dict


class ItemIn(BaseModel):
    iv: str
    ct: str = Field(max_length=MAX_CT)
    version: int = 0


class HoolaIn(BaseModel):
    on: bool
    title: str = Field(default="", max_length=200)
    username: str = Field(default="", max_length=400)
    password: str = Field(default="", max_length=400)
    urls: list[str] = Field(default_factory=list)
    totp: str = Field(default="", max_length=600)

    def __repr__(self) -> str:          # never printed with the password in it
        return f"HoolaIn(on={self.on})"

    __str__ = __repr__


def mount(app, current_tenant, require_key) -> None:
    router = APIRouter()

    def _err(e: CredError) -> HTTPException:
        msg = str(e)
        return HTTPException(404 if msg == "Not found." else 409, msg)

    @router.get("/api/cred/vault", dependencies=[Depends(require_key)])
    def cred_vault(tenant: str = Depends(current_tenant)):
        return view_vault(tenant)

    @router.post("/api/cred/vault", dependencies=[Depends(require_key)])
    def cred_vault_new(body: VaultIn, tenant: str = Depends(current_tenant)):
        try:
            return create_vault(tenant, body.salt, body.iters, body.wrapped)
        except CredError as e:
            raise _err(e)

    @router.put("/api/cred/vault", dependencies=[Depends(require_key)])
    def cred_vault_rewrap(body: VaultIn, tenant: str = Depends(current_tenant)):
        try:
            return rewrap(tenant, body.salt, body.iters, body.wrapped)
        except CredError as e:
            raise _err(e)

    @router.delete("/api/cred/vault", dependencies=[Depends(require_key)])
    def cred_vault_delete(confirm: str = "", tenant: str = Depends(current_tenant)):
        if confirm != "DELETE":
            raise HTTPException(400, "Send confirm=DELETE")
        return delete_vault(tenant)

    @router.post("/api/cred/items", dependencies=[Depends(require_key)])
    def cred_item_new(body: ItemIn, tenant: str = Depends(current_tenant)):
        try:
            return add_item(tenant, body.iv, body.ct)
        except CredError as e:
            raise _err(e)

    @router.put("/api/cred/items/{iid}", dependencies=[Depends(require_key)])
    def cred_item_put(iid: str, body: ItemIn, tenant: str = Depends(current_tenant)):
        try:
            return put_item(tenant, iid, body.iv, body.ct, body.version)
        except CredError as e:
            raise _err(e)

    @router.delete("/api/cred/items/{iid}", dependencies=[Depends(require_key)])
    def cred_item_delete(iid: str, tenant: str = Depends(current_tenant)):
        if not delete_item(tenant, iid):
            raise HTTPException(404, "Not found")
        return {"ok": True}

    @router.put("/api/cred/items/{iid}/hoola", dependencies=[Depends(require_key)])
    def cred_item_hoola(iid: str, body: HoolaIn, tenant: str = Depends(current_tenant)):
        try:
            return set_hoola(tenant, iid, body.on, body.title, body.username, body.password, body.urls, body.totp)
        except CredError as e:
            raise _err(e)
        finally:
            body.password = body.totp = ""

    @router.get("/api/cred/pwned/{prefix}", dependencies=[Depends(require_key)])
    def cred_pwned(prefix: str):
        from fastapi.responses import PlainTextResponse
        try:
            return PlainTextResponse(pwned_range(prefix), headers={"Cache-Control": "no-store"})
        except CredError as e:
            raise HTTPException(400, str(e))
        except Exception:
            raise HTTPException(502, "The breach check is not reachable right now.")

    @router.get("/api/cred/device/vault")
    def cred_device_vault(request: Request):
        """The Hoola browser extension (its paired-device token): the same ENCRYPTED vault, opened on her computer."""
        from .pc import service as pcs
        tok = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        dev = pcs.device_for_token(tok)
        if dev is None:
            raise HTTPException(401, "This device is not paired (or was removed). Pair it again.")
        return view_vault(dev.tenant_id)

    app.include_router(router)
