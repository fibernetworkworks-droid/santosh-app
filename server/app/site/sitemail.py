"""v0.994 B6 SIGN-IN AND RECEIPT EMAILS FOR WEBSITES (owner: "GO B6" on docs/research/lovable/03_backend_vs_hoola.md, gap 7).

Her website sent no email at all: a visitor who forgot the password had no way back in, and nobody got a word after
sending an order or an enquiry. This module adds the two kinds of email a website needs, sent through HER own
transactional mail service over SMTP (ZeptoMail, Amazon SES and Brevo all give an SMTP login; the keys live in the VPS
.env only, SITE_MAIL_* - never in chat or in the repo).

1. Sign-in codes (on by default once a mail service is set): "Email me a code" logs a visitor in, and "Forgot password"
   sets a new one. A code is 6 digits, only its HASH is kept, 10 minutes, 5 tries, 3 codes per address per 10 minutes.
   The answer never says whether an account exists for an address. Setting a new password signs that person out
   everywhere. A code is never logged, shown in the Studio or put in a reply.
2. Receipts (off until she turns them on, list by list): after a signed-in visitor adds an entry, one short email says
   it arrived. The email repeats nothing the visitor typed, so the website can never be used to send someone else's
   words to a stranger, and it goes only to the signed-in person's own address.

Every email is counted against a daily cap per website (SITE_MAIL_DAILY) and logged without its body (when, what kind,
the address masked, whether it went).
"""
from __future__ import annotations

import email.utils
import hashlib
import hmac
import json
import logging
import re
import secrets
import smtplib
import ssl
import threading
from datetime import timedelta
from email.message import EmailMessage
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import security as SEC
from . import webapp as W

log = logging.getLogger("santosh.site.mail")

CODE_TTL = 600
CODE_TRIES = 5
PURPOSES = ("login", "reset")
CAPTURED: list[dict[str, str]] = []        # tests only (SITE_MAIL_PROVIDER=capture)
STATS = {"sent": 0, "failed": 0, "capped": 0, "codes": 0, "code_ok": 0, "code_bad": 0, "receipts": 0}
_LOCK = threading.Lock()


def _st():
    from ..config import get_settings
    return get_settings()


def provider() -> str:
    return str(getattr(_st(), "site_mail_provider", "") or "").strip().lower()


def ready() -> bool:
    p, st = provider(), _st()
    if p == "capture":
        return True
    return p == "smtp" and bool(st.site_mail_smtp_host and st.site_mail_smtp_user and st.site_mail_smtp_password
                                and W.EMAIL.match(st.site_mail_from or ""))


# ---------------------------------------------------------------- her settings (per website, on its app backend)
def _home(p):
    from ..appmaker import sign as SG
    return SG._home(p)


def settings(p) -> dict[str, Any]:
    from ..appmaker import backend as BE
    saved = BE._j(_home(p).backend, {}).get("mail") or {}
    return {"codes": bool(saved.get("codes", True)), "receipts": [str(x) for x in saved.get("receipts") or []],
            "reply_to": str(saved.get("reply_to") or ""), "ready": ready(), "provider": provider() or "",
            "from": str(_st().site_mail_from or "") if ready() else ""}


def save_settings(p, body: dict[str, Any]) -> dict[str, Any]:
    from ..appmaker import backend as BE
    body = body if isinstance(body, dict) else {}
    cur = settings(p)
    keys = {c["key"] for c in BE.schema(p).get("collections") or [] if not str(c.get("key", "")).startswith("_")}
    rec = body.get("receipts", cur["receipts"])
    if not isinstance(rec, list):
        raise W.AppError("receipts: a list of list names.", 400)
    bad = [str(x) for x in rec if str(x) not in keys]
    if bad:
        raise W.AppError(f"No such list: {', '.join(bad[:3])}.", 400)
    reply = str(body.get("reply_to", cur["reply_to"]) or "").strip().lower()
    if reply and not W.EMAIL.match(reply):
        raise W.AppError("The reply-to address does not look right.", 400)
    keep = {"codes": bool(body.get("codes", cur["codes"])), "receipts": sorted(set(map(str, rec))), "reply_to": reply}
    BE.patch_backend(_home(p), set_={"mail": keep})
    return settings(p)


def _twin(p) -> bool:
    from . import twin as TW
    return TW.is_twin(p)


def public(p) -> dict[str, Any]:
    """What the login box may offer. A preview / draft copy never sends email (its data is not real)."""
    st = settings(p)
    return {"codes": bool(st["ready"] and st["codes"] and not _twin(p))}


# ---------------------------------------------------------------- the log (no bodies, addresses masked)
def mask(addr: str) -> str:
    a = str(addr or "")
    if "@" not in a:
        return ""
    u, d = a.split("@", 1)
    return (u[:1] + "***" + (u[-1:] if len(u) > 2 else "")) + "@" + d


def _log_file(p):
    from ..appmaker import backend as BE
    return BE._files(_home(p)).parent / "mail_log.json"


def _log_read(p) -> list[dict[str, Any]]:
    f = _log_file(p)
    try:
        return json.loads(f.read_text()) if f.exists() else []
    except (ValueError, OSError):
        return []


def _log_add(p, row: dict[str, Any]) -> None:
    with _LOCK:
        rows = _log_read(p)
        rows.insert(0, row)
        _log_file(p).write_text(json.dumps(rows[:300]))


def log_view(p, limit: int = 100) -> dict[str, Any]:
    rows = _log_read(p)[:max(1, min(int(limit or 100), 300))]
    today = now().date().isoformat()
    sent_today = sum(1 for x in _log_read(p) if str(x.get("at", "")).startswith(today) and x.get("ok"))
    return {"log": rows, "sent_today": sent_today, "daily_cap": int(_st().site_mail_daily or 0)}


# ---------------------------------------------------------------- sending
def _clean(s: str, n: int = 120) -> str:
    return re.sub(r"[\r\n\t]+", " ", str(s or "")).strip()[:n]


def _deliver(to: str, subject: str, body: str, from_name: str, reply_to: str) -> None:
    p, st = provider(), _st()
    if p == "capture":
        CAPTURED.append({"to": to, "subject": subject, "body": body, "from_name": from_name, "reply_to": reply_to})
        return
    msg = EmailMessage()
    msg["From"] = email.utils.formataddr((from_name, st.site_mail_from))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=False)
    msg["Message-ID"] = email.utils.make_msgid(domain=st.site_mail_from.split("@")[-1])
    msg["Auto-Submitted"] = "auto-generated"          # RFC 3834: no auto-replies back to this
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    ctx = ssl.create_default_context()
    port = int(st.site_mail_smtp_port or 587)
    server = (smtplib.SMTP_SSL(st.site_mail_smtp_host, port, timeout=20, context=ctx) if port == 465
              else smtplib.SMTP(st.site_mail_smtp_host, port, timeout=20))
    with server:
        if port != 465:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
        server.login(st.site_mail_smtp_user, st.site_mail_smtp_password)
        server.send_message(msg, from_addr=st.site_mail_from, to_addrs=[to])


def send(p, site_name: str, to: str, kind: str, subject: str, body: str) -> bool:
    """One email from her website. False (and logged) when it did not go; never raises."""
    row = {"at": now().isoformat(), "kind": kind, "to": mask(to), "ok": False}
    if _twin(p):
        return False
    if not ready():
        row["why"] = "no mail service set"
        _log_add(p, row)
        return False
    cap = int(_st().site_mail_daily or 0)
    today = now().date().isoformat()
    if cap and sum(1 for x in _log_read(p) if str(x.get("at", "")).startswith(today) and x.get("ok")) >= cap:
        STATS["capped"] += 1
        row["why"] = "daily limit reached"
        _log_add(p, row)
        return False
    try:
        _deliver(to, _clean(subject, 160), body, _clean(site_name, 80) or "Hoola", settings(p)["reply_to"])
        row["ok"] = True
        STATS["sent"] += 1
    except Exception as e:                    # noqa: BLE001 - the reason is the error's type, never its text (it may echo the login)
        STATS["failed"] += 1
        row["why"] = type(e).__name__
        log.warning("site mail %s to %s failed: %s", kind, mask(to), type(e).__name__)
    _log_add(p, row)
    return bool(row["ok"])


# ---------------------------------------------------------------- sign-in codes
def _key(email_addr: str) -> str:
    return "m" + hashlib.sha256(email_addr.encode()).hexdigest()[:19]          # fits the OTP table's 20-char slot


def _addr(raw: Any) -> str:
    a = str(raw or "").strip().lower()
    if not W.EMAIL.match(a) or a.endswith(".local"):
        raise W.AppError("Write a correct email.", 400)
    return a


def code_start(p, site_name: str, raw_email: str, purpose: str, ip: str = "") -> dict[str, Any]:
    from ..appmaker import backend as BE
    if purpose not in PURPOSES:
        raise W.AppError("not found", 404)
    if not public(p)["codes"]:
        raise W.AppError("Email codes are not switched on for this website.", 503)
    addr = _addr(raw_email)
    site = BE.bid(p)
    W.rate(f"mc|{site}|{addr}", 3, 600)
    W.rate(f"mcip|{site}|{ip}", 10, 3600)
    W.ensure_tables()
    say = {"ok": True, "sent_to": mask(addr), "expires_in": CODE_TTL,
           "say": "If this email can be used here, a 6-digit code is on its way. It works for 10 minutes."}
    with session() as s:
        known = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == site, W.SiteAppMember.email == addr)).first()
    if known is None and (purpose == "reset" or not BE.schema(p).get("signup", True)):
        return say                            # same answer either way: the website never tells who has an account
    code = f"{secrets.randbelow(10**6):06d}"
    with session() as s:
        for old in s.scalars(select(SEC.SiteAppOtp).where(SEC.SiteAppOtp.site_id == site, SEC.SiteAppOtp.phone == _key(addr),
                                                         SEC.SiteAppOtp.used.is_(False))).all():
            old.used = True
        s.add(SEC.SiteAppOtp(site_id=site, phone=_key(addr), code_h=SEC._h(f"{site}|{addr}|{purpose}|{code}"), extra=purpose))
    STATS["codes"] += 1
    name = _clean(site_name, 80) or "this website"
    if purpose == "reset":
        subject, body = (f"Reset your password for {name}",
                         f"Your code to set a new password for {name} is:\n\n    {code}\n\nIt works for 10 minutes. "
                         "Setting a new password signs you out on every device.\n\nIf you did not ask for this, ignore this "
                         "email; your password stays as it is.\n")
    else:
        subject, body = (f"Your sign-in code for {name}",
                         f"Your code to sign in to {name} is:\n\n    {code}\n\nIt works for 10 minutes.\n\n"
                         "If you did not ask for this, ignore this email.\n")
    send(p, site_name, addr, "reset_code" if purpose == "reset" else "login_code", subject, body)
    return say


def code_verify(p, raw_email: str, code: str, purpose: str, password: str = "", name: str = "", consent: bool = False,
                ua: str = "", ip: str = "") -> dict[str, Any]:
    from ..appmaker import backend as BE
    if purpose not in PURPOSES:
        raise W.AppError("not found", 404)
    addr = _addr(raw_email)
    code = re.sub(r"\D", "", str(code or ""))[:6]
    site = BE.bid(p)
    W.ensure_tables()
    if purpose == "reset" and len(password or "") < 8:       # checked BEFORE the code is spent
        raise W.AppError("The new password needs at least 8 characters.", 400)
    fail: tuple[str, int] | None = None
    with session() as s:                      # the try counter is SAVED before any refusal
        row = s.scalars(select(SEC.SiteAppOtp).where(SEC.SiteAppOtp.site_id == site, SEC.SiteAppOtp.phone == _key(addr),
                                                    SEC.SiteAppOtp.used.is_(False)).order_by(SEC.SiteAppOtp.id.desc())).first()
        if row is None or (row.extra or "") != purpose or now() - SEC._aware(row.created_at) > timedelta(seconds=CODE_TTL):
            fail = ("The code has expired; ask for a new one.", 400)
        else:
            row.tries += 1
            if row.tries > CODE_TRIES:
                row.used = True
                fail = ("Too many wrong tries; ask for a new code.", 429)
            elif not hmac.compare_digest(row.code_h, SEC._h(f"{site}|{addr}|{purpose}|{code}")):
                STATS["code_bad"] += 1
                fail = ("That code is not right.", 400)
            else:
                known = s.scalars(select(W.SiteAppMember.id).where(W.SiteAppMember.site_id == site, W.SiteAppMember.email == addr)).first()
                if known is None and purpose == "reset":
                    fail = ("The code has expired; ask for a new one.", 400)
                elif known is None and not BE.schema(p).get("signup", True):
                    fail = ("New accounts are closed on this website.", 403)
                elif known is None and not consent:  # refused BEFORE the code is spent: tick + the same code works
                    fail = ("Please tick the privacy notice to make an account.", 400)
                else:
                    row.used = True
    if fail:
        raise W.AppError(*fail)
    how = "email"
    with session() as s:
        m = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == site, W.SiteAppMember.email == addr)).first()
        if m is None:
            m = W.SiteAppMember(site_id=site, email=addr, name=_clean(name), pw="", role="member",
                                consent=json.dumps(SEC.consent_record("email")))
            s.add(m)
            s.flush()
            how = "signup"
        elif purpose == "reset":
            m.pw = W.hash_pw(password)
            s.flush()                         # saved before the object leaves the session (an expunged change is lost)
        s.expunge(m)
    if purpose == "reset":
        SEC.end_all(site, m)                  # every earlier login stops (generation bump + sessions ended)
        with session() as s:
            m = s.get(W.SiteAppMember, m.id)
            s.expunge(m)
    STATS["code_ok"] += 1
    if SEC._two_fa_on(m):
        return {"need_2fa": True, "ticket": SEC._ticket(site, m)}
    tok = W.make_token(site, m)
    SEC.record(site, m, tok, ua, ip, how)
    return {"token": tok, "me": W.view_member(m), **({"say": "Your new password is set."} if purpose == "reset" else {})}


# ---------------------------------------------------------------- receipts
def receipt_text(site_name: str, label: str, row_id: str) -> tuple[str, str]:
    name = _clean(site_name, 80) or "the website"
    what = _clean(label, 60) or "entry"
    ref = re.sub(r"[^A-Za-z0-9_-]", "", str(row_id or ""))[-8:]
    return (f"{name}: we got your {what.lower()}",
            f"Thank you. {name} has received your {what.lower()} (reference {ref}).\n\n"
            "You can see it any time by signing in on the website.\n\n"
            "If you did not send this, reply to this email and the team will look into it.\n")


def after_create(p, site_name: str, key: str, row: dict[str, Any], w: W.Who) -> None:
    """Her switched-on receipt for this list, to the signed-in visitor's own address, in the background."""
    try:
        st = settings(p)
        addr = str(getattr(w.m, "email", "") or "") if w.m is not None else ""
        if (not st["ready"] or key not in st["receipts"] or not addr or addr.endswith(".local")
                or not W.EMAIL.match(addr) or not isinstance(row, dict) or row.get("dedup")):
            return
        try:
            W.rate(f"rc|{p.id}|{w.m.id}", 5, 3600)
        except W.AppError:
            return
        from ..appmaker import backend as BE
        label = next((c.get("label") or c["key"] for c in BE.schema(p).get("collections") or [] if c.get("key") == key), key)
        subject, body = receipt_text(site_name, label, str(row.get("id") or ""))
    except Exception:                         # noqa: BLE001 - a receipt never breaks the write it follows
        log.debug("receipt skipped", exc_info=True)
        return

    def go():
        if send(p, site_name, addr, "receipt", subject, body):
            STATS["receipts"] += 1
    threading.Thread(target=go, name="site-mail", daemon=True).start()
