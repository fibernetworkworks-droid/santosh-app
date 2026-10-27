"""v0.142 Hoola Console: logins for the web console and the few read views the phone app builds on its own.

Two ways in, both ending in the same opaque session token the phone uses (`AppSession`, Bearer on every call):
  * Google: /auth/google/start?web=1 -> Google -> /auth/google/callback. A web sign-in state starts with `cw_`; instead
    of the app's deep link the callback hands the browser a ONE-TIME code (`ConsoleCode`, 2 minutes, used once, token
    sealed with the accounts vault) and redirects to /console/?code=...; the page swaps it for the token with
    POST /api/console/exchange. The token itself never sits in a URL, a referrer or the browser history.
  * Hoola account: her Hoola ID (@handle) + a console password she set while signed in (PUT /api/console/password).
    scrypt (n=2^14, r=8, p=1, 16-byte salt), 10-128 characters, the current password needed to change it, 5 wrong
    tries on one ID = locked 15 minutes, 20 wrong tries from one address in 15 minutes = refused (429). The answer for a
    wrong ID and a wrong password is the same. Every login is noted in her own chat (a stranger's login gets noticed).

The session made by a password login is for the tenant itself (`AppSession.user_id = tenant`): accounts.tenant_of_user
maps it back to the same tenant (owner tenant or a Google user's tenant). Money cards still need her phone's
fingerprint (v0.97, HTTP 428): the console shows them and points to the phone.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, Conversation, Message, now, session

log = logging.getLogger("santosh.console")

PW_MIN, PW_MAX = 10, 128
LOCK_AFTER, LOCK_FOR = 5, timedelta(minutes=15)
IP_LIMIT, IP_WINDOW = 20, 15 * 60
CODE_TTL = timedelta(minutes=2)
WEB_STATE = "cw_"
STATS = {"logins": 0, "refused": 0, "locked": 0, "codes": 0, "exchanged": 0}
_IP_FAILS: dict[str, deque] = defaultdict(deque)


class ConsoleError(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


class ConsoleLogin(Base):
    """Her console password (only a scrypt hash) and the lock counters."""
    __tablename__ = "console_logins"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    salt: Mapped[str] = mapped_column(String(64))
    pw_hash: Mapped[str] = mapped_column(String(128))
    failed: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ConsoleCode(Base):
    """One-time code that carries a fresh Google session from the callback to the console page."""
    __tablename__ = "console_codes"
    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    token_enc: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _sha(x: str) -> str:
    return hashlib.sha256(x.encode()).hexdigest()


def _scrypt(password: str, salt_hex: str) -> str:
    return hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1, dklen=32).hex()


# ---------------------------------------------------------------- Hoola ID <-> tenant
def handle_of(tenant: str) -> str:
    try:
        from ..net import identity
        return identity.ensure(tenant).handle
    except Exception:
        log.exception("hoola id failed")
        return ""


def tenant_of_handle(raw: str) -> str | None:
    from ..net.models import HoolaId
    h = (raw or "").strip().lstrip("@").lower()
    if "@" in h:                      # handle@this.server typed in full
        h = h.split("@", 1)[0]
    if not h or len(h) > 40:
        return None
    with session() as s:
        row = s.scalars(select(HoolaId).where(HoolaId.handle == h)).first()
        if row is None:
            row = s.scalars(select(HoolaId).where(HoolaId.old_handle == h)).first()   # an old ID keeps working 90 days
        return row.tenant_id if row else None


# ---------------------------------------------------------------- password
def has_password(tenant: str) -> bool:
    with session() as s:
        return s.get(ConsoleLogin, tenant) is not None


def set_password(tenant: str, new: str, current: str = "") -> dict[str, Any]:
    new = new or ""
    if len(new) < PW_MIN or len(new) > PW_MAX:
        raise ConsoleError(f"Password {PW_MIN} se {PW_MAX} akshar ka rakhiye.")
    if new.strip() != new or len(set(new)) < 4:
        raise ConsoleError("Thoda mushkil password rakhiye (aage-peeche space nahi, kam se kam 4 alag akshar).")
    salt = secrets.token_hex(16)
    with session() as s:
        row = s.get(ConsoleLogin, tenant)
        if row is not None:
            if not current or not hmac.compare_digest(_scrypt(current, row.salt), row.pw_hash):
                raise ConsoleError("Abhi wala password galat hai.", 403)
            row.salt, row.pw_hash, row.failed, row.locked_until, row.updated_at = salt, _scrypt(new, salt), 0, None, now()
        else:
            s.add(ConsoleLogin(tenant_id=tenant, salt=salt, pw_hash=_scrypt(new, salt)))
    return {"ok": True, "handle": "@" + handle_of(tenant)}


def remove_password(tenant: str, current: str) -> bool:
    with session() as s:
        row = s.get(ConsoleLogin, tenant)
        if row is None:
            return False
        if not current or not hmac.compare_digest(_scrypt(current, row.salt), row.pw_hash):
            raise ConsoleError("Abhi wala password galat hai.", 403)
        s.delete(row)
        return True


def _counted(ip: str) -> bool:
    """Only real public addresses are limited: behind a proxy that doesn't send X-Real-IP every visitor looks like
    127.0.0.1, and one person must not be able to block everyone's login (the per-ID lock still holds)."""
    import ipaddress
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def _ip_blocked(ip: str) -> bool:
    if not _counted(ip):
        return False
    q = _IP_FAILS[ip]
    cut = time.monotonic() - IP_WINDOW
    while q and q[0] < cut:
        q.popleft()
    return len(q) >= IP_LIMIT


def login(handle: str, password: str, ip: str = "") -> dict[str, Any]:
    """-> {session_token, tenant, handle}. Same answer for an unknown ID and a wrong password."""
    from .. import accounts
    ip = (ip or "?")[:64]
    if _ip_blocked(ip):
        STATS["refused"] += 1
        raise ConsoleError("Bahut galat koshishein hui. 15 minute baad phir try kijiye.", 429)
    wrong = ConsoleError("Hoola ID ya password galat hai.", 401)
    tenant = tenant_of_handle(handle)
    outcome = "ok"
    with session() as s:        # decide inside, raise after the commit (a raise inside would roll the counter back)
        row = s.get(ConsoleLogin, tenant) if tenant else None
        if row is None:
            _scrypt(password or "x", "00" * 16)          # same time as a real check
            outcome = "wrong"
        elif (_utc(row.locked_until) or now() - timedelta(seconds=1)) > now():
            outcome = "locked"
        elif not password or len(password) > PW_MAX or not hmac.compare_digest(_scrypt(password, row.salt), row.pw_hash):
            row.failed = (row.failed or 0) + 1
            if row.failed >= LOCK_AFTER:
                row.locked_until, row.failed = now() + LOCK_FOR, 0
            outcome = "wrong"
        else:
            row.failed, row.locked_until, row.last_login, row.last_ip = 0, None, now(), ip
    if outcome == "locked":
        STATS["locked"] += 1
        raise ConsoleError("Is Hoola ID par bahut galat koshishein hui. 15 minute baad phir try kijiye.", 429)
    if outcome == "wrong":
        if _counted(ip):
            _IP_FAILS[ip].append(time.monotonic())
        STATS["refused"] += 1
        raise wrong
    token = accounts.issue_session(tenant)
    STATS["logins"] += 1
    _tell(tenant, f"Hoola Console mein aapke Hoola ID se login hua ({ip}). Aapne nahi kiya? Main > Console mein password "
                  "badliye.")
    return {"session_token": token, "tenant": tenant, "handle": "@" + handle_of(tenant)}


def _tell(tenant: str, text: str) -> None:
    try:
        from ..events import notify
        from ..net.service import home_conv
        notify(home_conv(tenant), text)
    except Exception:
        log.exception("console login notice failed")


# ---------------------------------------------------------------- Google -> console handoff
def is_web_state(state: str) -> bool:
    return (state or "").startswith(WEB_STATE)


def issue_code(session_token: str) -> str:
    from .. import accounts
    code = secrets.token_urlsafe(24)
    with session() as s:
        s.add(ConsoleCode(code_hash=_sha(code), token_enc=accounts.encrypt(session_token)))
        for old in s.scalars(select(ConsoleCode).where(ConsoleCode.created_at < now() - timedelta(hours=1))).all():
            s.delete(old)
    STATS["codes"] += 1
    return code


def exchange(code: str) -> str:
    from .. import accounts
    if not code or len(code) > 100:
        raise ConsoleError("Login code galat hai.", 401)
    with session() as s:
        row = s.get(ConsoleCode, _sha(code))
        if row is None or row.used_at is not None or (_utc(row.created_at) or now()) < now() - CODE_TTL:
            raise ConsoleError("Login code purana ho gaya. Dobara 'Continue with Google' dabaiye.", 401)
        row.used_at = now()
        tok = accounts.decrypt(row.token_enc)
    STATS["exchanged"] += 1
    return tok


# ---------------------------------------------------------------- what the console shows
def me(tenant: str) -> dict[str, Any]:
    from ..avatar import service as av
    from .. import accounts
    a = av.get(tenant)
    user = None
    try:
        user = accounts.user_info(tenant)
    except Exception:
        pass
    try:
        from ..net.identity import owner_name
        owner = owner_name(tenant)
    except Exception:
        owner = ""
    return {"tenant": tenant, "handle": "@" + handle_of(tenant), "avatar": {"name": a["name"], "gender": a["gender"],
            "voice": a["voice"], "look": a.get("look")}, "owner": (user or {}).get("name") or owner,
            "email": (user or {}).get("email", ""), "has_password": has_password(tenant),
            "google_apps": _google_apps(user)}


def _google_apps(user: dict | None) -> dict[str, bool]:
    """Which Google apps her sign-in covers (the console asks for name + email first, apps separately)."""
    scopes = " ".join(" ".join(c.get("scopes") or []) for c in (user or {}).get("connections", []) if c.get("provider") == "google")
    return {"gmail": "gmail" in scopes, "calendar": "calendar" in scopes, "drive": "auth/drive" in scopes,
            "docs": "documents" in scopes, "sheets": "spreadsheets" in scopes}


def conversations(tenant: str, limit: int = 40) -> list[dict[str, Any]]:
    """Her chats, newest activity first, titled by her first message (like any chat app)."""
    out = []
    with session() as s:
        convs = s.scalars(select(Conversation).where(Conversation.tenant_id == tenant)
                          .order_by(Conversation.created_at.desc()).limit(200)).all()
        for c in convs:
            first = s.scalars(select(Message).where(Message.conversation_id == c.id, Message.role == "user",
                                                    Message.display.is_not(None)).order_by(Message.id).limit(1)).first()
            last = s.scalars(select(Message).where(Message.conversation_id == c.id).order_by(Message.id.desc()).limit(1)).first()
            title = (first.display if first else "").strip().replace("\n", " ")
            at = _utc(last.created_at if last else c.created_at)
            out.append({"id": c.id, "title": title[:80] or "Naya chat", "empty": first is None,
                        "updated_at": at.isoformat() if at else ""})
    out.sort(key=lambda x: x["updated_at"], reverse=True)
    return out[:max(1, min(limit, 100))]


def pending(tenant: str) -> list[dict[str, Any]]:
    """Everything waiting for her Haan, from every place that asks (each source fails alone)."""
    items: list[dict[str, Any]] = []
    try:
        from ..bazar import service as bz
        for c in bz.pending_approvals(tenant):
            items.append({"kind": "bazar_approval", "id": c["id"], "title": c.get("title") or "Aapki Haan chahiye",
                          "sub": " · ".join(x for x in (c.get("amount"), c.get("payee"), c.get("pack")) if x),
                          "money": bool(c.get("money")), "card": c})
    except Exception:
        log.exception("pending bazar")
    try:
        from ..employee import service as emp
        for a in emp.asks(tenant, "pending", 20):
            items.append({"kind": "employee_ask", "id": a["id"], "title": a.get("what") or "Employee ka sawaal",
                          "sub": " · ".join(x for x in (a.get("who"), a.get("why")) if x), "money": False, "card": a})
    except Exception:
        log.exception("pending employee")
    try:
        from ..operator import service as ops
        t = ops.active(tenant)
        p = (t or {}).get("pending")
        if t and p:
            items.append({"kind": "operator_ask", "id": p.get("id", ""), "title": p.get("reason") or "Website ka sawaal",
                          "sub": (t.get("site") or "") + (" · OTP" if p.get("kind") == "otp" else ""),
                          "money": p.get("kind") == "payment", "card": {**p, "task_id": t.get("id")}})
    except Exception:
        log.exception("pending operator")
    return items


def today(tenant: str) -> dict[str, Any]:
    out: dict[str, Any] = {"reminders": [], "lists": {}, "pending": pending(tenant)}
    try:
        from ..db import ListItem, Reminder
        with session() as s:
            rs = s.scalars(select(Reminder).where(Reminder.tenant_id == tenant, Reminder.status == "active")
                           .order_by(Reminder.due_at).limit(12)).all()
            out["reminders"] = [{"id": r.id, "text": r.text, "due_at": (_utc(r.due_at) or now()).isoformat()} for r in rs]
            for li in s.scalars(select(ListItem).where(ListItem.tenant_id == tenant, ListItem.done.is_(False))
                                .order_by(ListItem.list_name, ListItem.id).limit(60)).all():
                out["lists"].setdefault(li.list_name, []).append({"id": li.id, "text": li.text})
    except Exception:
        log.exception("today")
    return out
