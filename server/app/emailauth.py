"""SIGN IN WITH EMAIL (owner: "THERE WILL BE 2 WAY TO SIGN UP TO HOOLA 1ST SELF REGISTRACTION VIA EMAIL AND OTHER IS
GOOGLE" -> "MAKE IT SAME AS OTHER DOES LIKE CLAUDE AND CHAT GPT").

The way Claude and ChatGPT do it: ONE screen "Log in or sign up". Continue with Google, or type your email and press
Continue; a 6-digit code arrives by email; type it and you are in. There is no password to make or forget. The same
screen logs in an old account and makes a new one; a new person is then asked what to call them.

- One account per email address. Google sign-in and email sign-in with the same address land in the SAME Hoola (Google
  has confirmed the address, and the code proves she holds it), so nothing is split.
- A code is 6 digits, works 10 minutes and once, 5 wrong tries kill it, only its keyed hash is kept. At most 3 codes per
  address per 10 minutes and 12 per network address per hour.
- The answer to "send me a code" is the same whether the address has an account or not.
- A code is never logged, never put in a reply and never in a URL.
- New accounts follow HOOLA_SIGNUP (open / invite), exactly like Google sign-in.
- The email goes out through the same transactional mail service as the website emails (SITE_MAIL_* in the VPS .env:
  ZeptoMail / Amazon SES / Brevo SMTP). Until it is set, email sign-in says so and Google keeps working.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import threading
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, User, as_utc, now, session

log = logging.getLogger("santosh.emailauth")

CODE_TTL = 600
CODE_TRIES = 5
PER_EMAIL = (3, 600)        # codes per address per 10 minutes
PER_IP = (12, 3600)         # codes per network address per hour
VERIFY_PER_IP = (40, 3600)  # code checks per network address per hour
EMAIL = re.compile(r"^[^@\s<>\"',;]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$")
STATS = {"sent": 0, "send_failed": 0, "verified": 0, "new_accounts": 0, "bad_codes": 0}
_RATE: dict[str, list[float]] = {}
_LOCK = threading.Lock()


class EmailAuthError(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


class AuthEmailCode(Base):
    """One sign-in code waiting to be typed (only its keyed hash)."""
    __tablename__ = "auth_email_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    tries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_ready: set[int] = set()


def ensure_table() -> None:
    """Self-heal: a database born before this table existed gets it on first use (keyed per engine)."""
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _ready:
        return
    AuthEmailCode.__table__.create(eng, checkfirst=True)
    _ready.add(id(eng))


def _st():
    from .config import get_settings
    return get_settings()


def ready() -> bool:
    """Can Hoola send sign-in codes on this server? (the same mail service as the website emails)"""
    from .site import sitemail
    return sitemail.ready()


def _hash(email: str, code: str) -> str:
    key = (_st().secret_key or "hoola").encode()
    return hmac.new(key, f"{email}|{code}".encode(), hashlib.sha256).hexdigest()


def mask(addr: str) -> str:
    from .site.sitemail import mask as _m
    return _m(addr)


def clean_email(raw: Any) -> str:
    a = str(raw or "").strip().lower()
    if len(a) > 254 or not EMAIL.match(a) or ".." in a or a.endswith(".local"):
        raise EmailAuthError("Enter a correct email address.")
    return a


def _rate(key: str, n: int, per: int) -> None:
    t = time.time()
    with _LOCK:
        if len(_RATE) > 20000:
            for k in [k for k, v in _RATE.items() if not v or t - v[-1] > 3600]:
                _RATE.pop(k, None)
        hits = [x for x in _RATE.get(key, []) if t - x < per]
        if len(hits) >= n:
            raise EmailAuthError("Too many tries. Wait a few minutes and try again.", 429)
        _RATE[key] = hits + [t]


def _body(code: str) -> str:
    return (f"Your Hoola code is: {code}\n\n"
            "Type it on the Hoola screen to log in or finish signing up. It works for 10 minutes, once.\n\n"
            "If you did not ask for this, ignore this email: nobody can get in without the code.\n"
            "Hoola will never ask you for this code on a call, in a chat or in another email.\n\n"
            "— Hoola by Newtika")


def start(raw_email: str, ip: str = "") -> dict[str, Any]:
    """Send a 6-digit code to this address. The same answer whether the address has an account or not."""
    if not ready():
        raise EmailAuthError("Email sign-in is not switched on for this server yet. Use Continue with Google.", 503)
    addr = clean_email(raw_email)
    _rate(f"e|{addr}", *PER_EMAIL)
    _rate(f"i|{ip or '?'}", *PER_IP)
    ensure_table()
    code = f"{secrets.randbelow(10**6):06d}"
    with session() as s:
        for old in s.scalars(select(AuthEmailCode).where(AuthEmailCode.email == addr, AuthEmailCode.used_at.is_(None))).all():
            old.used_at = now()                    # a new code replaces the one before
        for gone in s.scalars(select(AuthEmailCode).where(AuthEmailCode.created_at < now() - timedelta(days=1))).all():
            s.delete(gone)
        s.add(AuthEmailCode(email=addr, code_hash=_hash(addr, code)))
    from .site import sitemail
    try:
        sitemail._deliver(addr, f"Your Hoola code: {code}", _body(code), "Hoola", "")
        STATS["sent"] += 1
    except Exception as e:                         # noqa: BLE001 - the type only: the error may echo the mail login
        STATS["send_failed"] += 1
        log.warning("sign-in code to %s did not go: %s", mask(addr), type(e).__name__)
        raise EmailAuthError("The code email could not be sent right now. Try again in a minute, or use Continue "
                             "with Google.", 502)
    log.info("sign-in code sent to %s", mask(addr))
    return {"ok": True, "sent_to": mask(addr), "expires_in": CODE_TTL,
            "say": f"We sent a 6-digit code to {mask(addr)}. It works for 10 minutes."}


def _check(addr: str, code: str) -> None:
    code = re.sub(r"\D", "", str(code or ""))
    if len(code) != 6:
        raise EmailAuthError("Type the 6-digit code from the email.")
    ensure_table()
    fail = ""
    with session() as s:          # the outcome is decided inside and raised AFTER the commit: a wrong try must count
        row = s.scalars(select(AuthEmailCode).where(AuthEmailCode.email == addr, AuthEmailCode.used_at.is_(None))
                        .order_by(AuthEmailCode.id.desc())).first()
        if row is None or (as_utc(row.created_at) or now()) < now() - timedelta(seconds=CODE_TTL):
            fail = "This code has expired. Ask for a new code."
        elif not hmac.compare_digest(row.code_hash, _hash(addr, code)):
            row.tries += 1
            STATS["bad_codes"] += 1
            if row.tries >= CODE_TRIES:
                row.used_at = now()
                fail = "Too many wrong codes. Ask for a new code."
            else:
                fail = f"That code is not right. {CODE_TRIES - row.tries} tries left."
        else:
            row.used_at = now()
    if fail:
        raise EmailAuthError(fail, 401)


def verify(raw_email: str, code: str, ip: str = "") -> dict[str, Any]:
    """The code is right -> the account for this email (made now if new) and a session for this device."""
    from . import accounts
    addr = clean_email(raw_email)
    _rate(f"v|{ip or '?'}", *VERIFY_PER_IP)
    _check(addr, code)
    with session() as s:
        user = s.scalar(select(User).where(User.email == addr))
        new = user is None
        if new:
            if not accounts.signup_allowed(addr):
                raise accounts.SignupClosed("Hoola is opening by invite for now. There is no place for this email yet; "
                                            "ask the Hoola team for an invite.")
            user = User(email=addr, name="")
            s.add(user)
            s.flush()
        user.last_login = now()
        uid, name = user.id, user.name or ""
    if not name:
        try:
            from .db import Profile
            with session() as s:
                p = s.get(Profile, accounts.tenant_of_user(uid))
                name = (p.name or "") if p else ""
        except Exception:                          # noqa: BLE001 - no profile yet: she is asked her name
            name = ""
    STATS["verified"] += 1
    if new:
        STATS["new_accounts"] += 1
        log.info("new Hoola account by email: %s", mask(addr))
    return {"session_token": accounts.issue_session(uid), "user_id": uid, "email": addr, "name": name,
            "new": new, "needs_name": not name}


def save_name(tenant: str, user_id: str | None, name: str) -> str:
    """After a new sign-up: 'What should we call you?' -> the account and the profile."""
    nm = re.sub(r"\s+", " ", str(name or "")).strip()[:80]
    if not nm:
        raise EmailAuthError("Type your name.")
    if user_id:
        with session() as s:
            u = s.get(User, user_id)
            if u is not None:
                u.name = nm
    from . import life
    from .db import Profile
    life.get_profile(tenant)
    with session() as s:
        p = s.get(Profile, tenant)
        if p is not None:
            p.name = nm
    return nm


def status() -> dict[str, Any]:
    return {"email": ready(), "google": _google_ready(), "stats": dict(STATS)}


def _google_ready() -> bool:
    from . import accounts
    return accounts.oauth_configured()
