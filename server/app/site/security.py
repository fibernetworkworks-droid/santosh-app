"""v0.433 LOGIN AUR SURAKSHA (web Step 3 = W3 of docs/WEB_PLATFORM_PLAN.md): how the PEOPLE of her website log in and stay
safe. Every function works on the app backend id (`app:<project>`), so a website and its phone app share it all.

- Phone OTP: 6 digits, only the HASH is kept, 5 minutes, 5 tries, 3 codes per number per 10 minutes, typed only into the
  site's own login box. Sent through a DLT-registered SMS provider (MSG91 OTP API, her account: SITE_SMS_PROVIDER=msg91 +
  MSG91_AUTHKEY + MSG91_OTP_TEMPLATE). No provider = the box says so; a code is never shown, logged or put in a reply.
- Staff 2FA (TOTP, RFC 6238 - any authenticator app): staff / admin turn it on; their password login then needs the
  6-digit code (a short signed ticket carries the step). The secret is stored encrypted.
- Sessions: every login is a row (device, masked IP, last seen); one can be ended, or all ("sign out everywhere"
  bumps the member's generation so even unseen old logins stop).
- DPDP: the website's sign-up needs the consent tick (version + time + how kept); a member downloads all her own data
  (JSON) or deletes her account and everything she owns.
- Audit log: every change to every row with WHO made it (the journal, `appmaker/backup.py`), admin / owner only.
- Permissions matrix: who may create / read / change / delete each list, and which fields are staff-only (`private`)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import struct
import time
from datetime import timedelta
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import webapp as W

log = logging.getLogger("santosh.site")

OTP_TTL = 300
OTP_TRIES = 5
CONSENT_V = 1
TICKET_S = 300
CAPTURED: dict[str, str] = {}          # tests only (SITE_SMS_PROVIDER=capture): phone -> last code
STATS = {"otp_sent": 0, "otp_ok": 0, "otp_bad": 0, "two_fa_ok": 0, "two_fa_bad": 0, "sessions": 0, "exports": 0}


class SiteAppSession(Base):
    __tablename__ = "site_app_sessions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ses"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    member_id: Mapped[str] = mapped_column(String(40), index=True)
    th: Mapped[str] = mapped_column(String(40), index=True)                 # sha256 of the token (never the token)
    ua: Mapped[str] = mapped_column(String(160), default="")
    ip: Mapped[str] = mapped_column(String(40), default="")                  # masked
    how: Mapped[str] = mapped_column(String(12), default="password")         # password | otp | 2fa | signup
    created_at = mapped_column(DateTime(timezone=True), default=now)
    seen_at = mapped_column(DateTime(timezone=True), default=now)
    ended: Mapped[bool] = mapped_column(Boolean, default=False)


class SiteAppOtp(Base):
    __tablename__ = "site_app_otps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_h: Mapped[str] = mapped_column(String(64))
    tries: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at = mapped_column(DateTime(timezone=True), default=now)
    extra: Mapped[str] = mapped_column(Text, default="")


def ensure_tables(eng) -> None:
    SiteAppSession.__table__.create(eng, checkfirst=True)
    SiteAppOtp.__table__.create(eng, checkfirst=True)


def _settings():
    from ..config import get_settings
    return get_settings()


def _h(x: str) -> str:
    return hmac.new(W._secret(), x.encode(), hashlib.sha256).hexdigest()


def _aware(dt):
    from datetime import timezone
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- sessions
def _th(token: str) -> str:
    return hashlib.sha256((token or "").encode()).hexdigest()[:40]


def _mask_ip(ip: str) -> str:
    ip = str(ip or "")
    if ip.count(".") == 3:
        return ".".join(ip.split(".")[:3]) + ".x"
    return ip.split(":")[0][:8] + ":…" if ip else ""


def record(site: str, m: W.SiteAppMember, token: str, ua: str = "", ip: str = "", how: str = "password") -> None:
    W.ensure_tables()
    with session() as s:
        s.add(SiteAppSession(site_id=site, member_id=m.id, th=_th(token), ua=str(ua or "")[:160], ip=_mask_ip(ip), how=how))
    STATS["sessions"] += 1


def token_ok(site: str, token: str) -> bool:
    """False only for a login she / the member ENDED; tokens from before sessions were kept still work (gen guards those)."""
    if not token:
        return True
    W.ensure_tables()
    with session() as s:
        row = s.scalars(select(SiteAppSession).where(SiteAppSession.site_id == site, SiteAppSession.th == _th(token))).first()
        if row is None:
            return True
        if row.ended:
            return False
        if row.seen_at is None or now() - _aware(row.seen_at) > timedelta(minutes=5):
            row.seen_at = now()
        return True


def sessions(site: str, m: W.SiteAppMember, token: str = "") -> list[dict[str, Any]]:
    W.ensure_tables()
    me = _th(token)
    with session() as s:
        rows = s.scalars(select(SiteAppSession).where(SiteAppSession.site_id == site, SiteAppSession.member_id == m.id,
                                                      SiteAppSession.ended.is_(False))
                         .order_by(SiteAppSession.seen_at.desc()).limit(30)).all()
        return [{"id": x.id, "device": _device(x.ua), "ip": x.ip, "how": x.how, "this": x.th == me,
                 "since": x.created_at.isoformat() if x.created_at else "", "seen": x.seen_at.isoformat() if x.seen_at else ""}
                for x in rows]


def _device(ua: str) -> str:
    u = ua or ""
    os_ = "Android" if "Android" in u else "iPhone" if "iPhone" in u else "iPad" if "iPad" in u else \
        "Windows" if "Windows" in u else "Mac" if "Mac OS" in u else "Linux" if "Linux" in u else "Device"
    br = "Edge" if "Edg/" in u else "Chrome" if "Chrome/" in u else "Firefox" if "Firefox/" in u else "Safari" if "Safari/" in u else ""
    return f"{br} on {os_}".strip() if br else os_


def end(site: str, m: W.SiteAppMember, sid: str) -> dict[str, Any]:
    with session() as s:
        row = s.get(SiteAppSession, sid)
        if row is None or row.site_id != site or row.member_id != m.id:
            raise W.AppError("Yeh login nahi mila.", 404)
        row.ended = True
    return {"ok": True}


def end_all(site: str, m: W.SiteAppMember) -> dict[str, Any]:
    """Sign out everywhere: every token of this member stops (gen bump) and every session row ends."""
    W.logout_all(site, m)
    with session() as s:
        for row in s.scalars(select(SiteAppSession).where(SiteAppSession.site_id == site, SiteAppSession.member_id == m.id)).all():
            row.ended = True
    return {"ok": True}


# ---------------------------------------------------------------- phone OTP
def phone10(raw: Any) -> str:
    d = re.sub(r"\D", "", str(raw or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    if not re.fullmatch(r"[6-9]\d{9}", d):
        raise W.AppError("Sahi 10 ankon ka mobile number likhiye.", 400)
    return d


def provider() -> str:
    return str(getattr(_settings(), "site_sms_provider", "") or "").strip().lower()


def _send(phone: str, code: str) -> None:
    p = provider()
    if p == "capture":                       # the test suite only
        CAPTURED[phone] = code
        return
    if p == "msg91":
        import httpx
        st = _settings()
        key, tpl = getattr(st, "msg91_authkey", ""), getattr(st, "msg91_otp_template", "")
        if not key or not tpl:
            raise W.AppError("SMS ka account adhoora hai (MSG91 key / DLT template); maalkin se kahiye.", 503)
        try:
            r = httpx.post("https://control.msg91.com/api/v5/otp", params={"template_id": tpl, "mobile": "91" + phone, "otp": code},
                           headers={"authkey": key, "Content-Type": "application/json"}, json={}, timeout=15)
            ok = r.status_code == 200 and (r.json() or {}).get("type") == "success"
        except Exception as e:               # noqa: BLE001
            log.warning("msg91 otp send failed: %s", type(e).__name__)
            ok = False
        if not ok:
            raise W.AppError("SMS abhi nahi gaya; thodi der baad dobara koshish kijiye.", 502)
        return
    raise W.AppError("Is website par mobile OTP login abhi chalu nahi hai; email se login kijiye.", 503)


def otp_start(site: str, raw_phone: str, ip: str = "") -> dict[str, Any]:
    phone = phone10(raw_phone)
    if not provider():
        raise W.AppError("Is website par mobile OTP login abhi chalu nahi hai; email se login kijiye.", 503)
    W.rate(f"otp|{site}|{phone}", 3, 600)
    W.rate(f"otpip|{site}|{ip}", 10, 3600)
    W.ensure_tables()
    code = f"{secrets.randbelow(10**6):06d}"
    _send(phone, code)
    with session() as s:
        for old in s.scalars(select(SiteAppOtp).where(SiteAppOtp.site_id == site, SiteAppOtp.phone == phone, SiteAppOtp.used.is_(False))).all():
            old.used = True                  # only the newest code counts
        s.add(SiteAppOtp(site_id=site, phone=phone, code_h=_h(f"{site}|{phone}|{code}")))
    STATS["otp_sent"] += 1
    return {"ok": True, "sent_to": phone[:2] + "******" + phone[-2:], "expires_in": OTP_TTL}


def otp_verify(site: str, schema: dict[str, Any], raw_phone: str, code: str, name: str = "", consent: bool = False,
               ua: str = "", ip: str = "") -> dict[str, Any]:
    phone = phone10(raw_phone)
    code = re.sub(r"\D", "", str(code or ""))[:6]
    W.ensure_tables()
    fail: tuple[str, int] | None = None
    with session() as s:                      # the try counter is SAVED before any refusal (a raise here would undo it)
        row = s.scalars(select(SiteAppOtp).where(SiteAppOtp.site_id == site, SiteAppOtp.phone == phone, SiteAppOtp.used.is_(False))
                        .order_by(SiteAppOtp.id.desc())).first()
        if row is None or now() - _aware(row.created_at) > timedelta(seconds=OTP_TTL):
            fail = ("Code purana ho gaya; naya code mangaiye.", 400)
        else:
            row.tries += 1
            if row.tries > OTP_TRIES:
                row.used = True
                fail = ("Bahut galat koshish; naya code mangaiye.", 429)
            elif not hmac.compare_digest(row.code_h, _h(f"{site}|{phone}|{code}")):
                STATS["otp_bad"] += 1
                fail = ("Code galat hai.", 400)
            else:
                known = s.scalars(select(W.SiteAppMember.id).where(W.SiteAppMember.site_id == site, W.SiteAppMember.phone == phone)).first()
                if known is None and not schema.get("signup", True):
                    fail = ("Is website par naye account band hain; dukaan se baat kijiye.", 403)
                elif known is None and not consent:   # refused BEFORE the code is spent: the tick + the same code works
                    fail = ("Account banane ke liye privacy notice par haan (tick) zaroori hai.", 400)
                else:
                    row.used = True
    if fail:
        raise W.AppError(*fail)
    with session() as s:
        m = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == site, W.SiteAppMember.phone == phone)).first()
        how = "otp"
        if m is None:
            m = W.SiteAppMember(site_id=site, email=f"{phone}@phone.local", name=str(name or "")[:120], pw="", role="member",
                                phone=phone, consent=json.dumps(consent_record("otp")))
            s.add(m)
            s.flush()
            how = "signup"
        s.expunge(m)
    if _two_fa_on(m):                         # staff with 2FA: the code is the second step even after an OTP
        return {"need_2fa": True, "ticket": _ticket(site, m)}
    STATS["otp_ok"] += 1
    tok = W.make_token(site, m)
    record(site, m, tok, ua, ip, how)
    return {"token": tok, "me": W.view_member(m)}


# ---------------------------------------------------------------- consent (DPDP)
def consent_record(via: str) -> dict[str, Any]:
    return {"v": CONSENT_V, "at": now().isoformat(), "via": via}


def save_consent(site: str, member_id: str, via: str) -> None:
    with session() as s:
        m = s.get(W.SiteAppMember, member_id)
        if m is not None and m.site_id == site:
            m.consent = json.dumps(consent_record(via))


# ---------------------------------------------------------------- staff 2FA (TOTP)
def _totp_at(secret_b32: str, t: int) -> str:
    key = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    h = hmac.new(key, struct.pack(">Q", t // 30), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


def totp_ok(secret_b32: str, code: str, at: float | None = None) -> bool:
    code = re.sub(r"\D", "", str(code or ""))
    t = int(at if at is not None else time.time())
    return len(code) == 6 and any(hmac.compare_digest(_totp_at(secret_b32, t + d * 30), code) for d in (-1, 0, 1))


def _totp_of(m: W.SiteAppMember) -> dict[str, Any]:
    from ..accounts import decrypt
    try:
        d = json.loads(m.totp or "{}")
    except (TypeError, ValueError):
        return {}
    if d.get("s"):
        d["s"] = decrypt(d["s"]) or ""
    return d


def _two_fa_on(m: W.SiteAppMember) -> bool:
    return bool(_totp_of(m).get("on") and _totp_of(m).get("s"))


def two_fa_start(site: str, m: W.SiteAppMember, label: str = "Hoola") -> dict[str, Any]:
    from ..accounts import encrypt
    if m.role not in ("staff", "admin"):
        raise W.AppError("2-step login staff / admin ke liye hai.", 403)
    secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
    with session() as s:
        x = s.get(W.SiteAppMember, m.id)
        x.totp = json.dumps({"on": False, "s": encrypt(secret)})
    acct = re.sub(r"[^A-Za-z0-9@._-]", "", m.email)[:60]
    issuer = re.sub(r"[^A-Za-z0-9 ._-]", "", label)[:40] or "Hoola"
    return {"secret": secret, "uri": f"otpauth://totp/{issuer}:{acct}?secret={secret}&issuer={issuer.replace(' ', '%20')}&digits=6&period=30",
            "say": "Authenticator app mein yeh key daaliye, phir uska 6 ank ka code yahan likhiye."}


def two_fa_confirm(site: str, m: W.SiteAppMember, code: str) -> dict[str, Any]:
    from ..accounts import encrypt
    d = _totp_of(m)
    if not d.get("s"):
        raise W.AppError("Pehle 2-step login shuru kijiye.", 409)
    if not totp_ok(d["s"], code):
        raise W.AppError("Code galat hai; app mein jo abhi dikh raha hai woh likhiye.", 400)
    with session() as s:
        x = s.get(W.SiteAppMember, m.id)
        x.totp = json.dumps({"on": True, "s": encrypt(d["s"])})
    return {"ok": True, "two_fa": True}


def two_fa_off(site: str, m: W.SiteAppMember, code: str) -> dict[str, Any]:
    d = _totp_of(m)
    if d.get("on") and not totp_ok(d.get("s", ""), code):
        raise W.AppError("2-step band karne ke liye abhi ka code chahiye.", 400)
    with session() as s:
        x = s.get(W.SiteAppMember, m.id)
        x.totp = None
    return {"ok": True, "two_fa": False}


def _ticket(site: str, m: W.SiteAppMember) -> str:
    exp = int(time.time()) + TICKET_S
    body = f"2fa.{m.id}.{m.gen}.{exp}"
    return body + "." + _h(site + "|" + body)[:32]


def two_fa_login(site: str, ticket: str, code: str, ua: str = "", ip: str = "") -> dict[str, Any]:
    try:
        tag, mid, gen, exp, sig = str(ticket or "").split(".")
    except ValueError:
        raise W.AppError("Login dobara kijiye.", 401)
    body = f"{tag}.{mid}.{gen}.{exp}"
    if tag != "2fa" or int(exp) < time.time() or not hmac.compare_digest(sig, _h(site + "|" + body)[:32]):
        raise W.AppError("Login dobara kijiye.", 401)
    W.rate(f"2fa|{site}|{mid}", 6, 600)
    with session() as s:
        m = s.get(W.SiteAppMember, mid)
        if m is None or m.site_id != site or str(m.gen) != gen:
            raise W.AppError("Login dobara kijiye.", 401)
        s.expunge(m)
    if not totp_ok(_totp_of(m).get("s", ""), code):
        STATS["two_fa_bad"] += 1
        raise W.AppError("Code galat hai.", 400)
    STATS["two_fa_ok"] += 1
    tok = W.make_token(site, m)
    record(site, m, tok, ua, ip, "2fa")
    return {"token": tok, "me": W.view_member(m)}


def needs_2fa(site: str, email: str) -> W.SiteAppMember | None:
    with session() as s:
        m = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == site,
                                                    W.SiteAppMember.email == (email or "").strip().lower())).first()
        if m is not None:
            s.expunge(m)
    return m if m is not None and _two_fa_on(m) else None


# ---------------------------------------------------------------- her data: export (DPDP)
def export(site: str, schema: dict[str, Any], m: W.SiteAppMember) -> dict[str, Any]:
    W.rate(f"exp|{site}|{m.id}", 5, 3600)
    out: dict[str, Any] = {"account": {"name": m.name, "email": "" if m.email.endswith("@phone.local") else m.email,
                                       "phone": m.phone or "", "role": m.role,
                                       "since": m.created_at.isoformat() if m.created_at else "",
                                       "consent": json.loads(m.consent) if m.consent else None},
                           "lists": {}, "made": now().isoformat()}
    cols = {c["key"]: c for c in schema.get("collections") or []}
    with session() as s:
        for row in s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site, W.SiteAppRow.owner == m.id)).all():
            c = cols.get(row.coll)
            if c is None:
                continue
            v = W.row_view(c, row, W.Who(m))
            v.pop("mine", None)
            out["lists"].setdefault(c.get("label") or row.coll, []).append(v)
    STATS["exports"] += 1
    return out


# ---------------------------------------------------------------- audit log + permissions matrix (admin / owner)
def audit(site: str, limit: int = 200, coll: str = "") -> list[dict[str, Any]]:
    from ..appmaker import backup as BK
    BK.ensure_table()
    with session() as s:
        q = select(BK.AppJournal).where(BK.AppJournal.site_id == site)
        if coll:
            q = q.where(BK.AppJournal.coll == coll)
        rows = s.scalars(q.order_by(BK.AppJournal.id.desc()).limit(max(1, min(limit, 500)))).all()
        names = {m.id: (m.name or m.email.split("@")[0]) for m in s.scalars(
            select(W.SiteAppMember).where(W.SiteAppMember.site_id == site)).all()}
    out = []
    for j in rows:
        try:
            b, a = json.loads(j.before or "{}"), json.loads(j.after or "{}")
        except ValueError:
            b, a = {}, {}
        changed = sorted(k for k in set(a) | set(b) if not str(k).startswith("_") and a.get(k) != b.get(k))
        by = j.by or ""
        role, _, mid = by.partition(":")
        who = "Aap (owner)" if by == "owner" else (names.get(mid, "member") + f" ({role})") if mid else \
            ("Hoola (niyam)" if by in ("", "system") else by)
        out.append({"at": j.at.isoformat() if j.at else "", "op": j.op, "list": j.coll, "row": j.row_id, "by": who,
                    "fields": changed[:12]})
    return out


def matrix(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Plain words for each list: who creates / reads / changes / deletes, which fields only staff see or set."""
    say = {"public": "sab", "member": "login wale", "members": "login wale", "own": "sirf apni", "admin": "staff"}
    out = []
    for c in schema.get("collections") or []:
        r = c.get("rules") or {}
        out.append({"list": c["key"], "label": c.get("label") or c["key"],
                    "create": say.get(r.get("create"), r.get("create")), "read": say.get(r.get("read"), r.get("read")),
                    "update": say.get(r.get("update"), r.get("update")), "delete": say.get(r.get("delete"), r.get("delete")),
                    "staff_set": [f["label"] for f in c.get("fields") or [] if f.get("admin_only")],
                    "staff_see": [f["label"] for f in c.get("fields") or [] if f.get("private")]})
    return out
