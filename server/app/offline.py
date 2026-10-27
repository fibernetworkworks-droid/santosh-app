"""Phone offline? Santosh keeps you posted by email.

The phone counts as online while its live stream is open (the app or its background service) or it made
any API call recently. When it has been silent for OFFLINE_AFTER_MIN minutes, new Santosh updates
(reminders, briefings, job results, approvals waiting) are sent as one short email digest, at most every
30 minutes. Nothing that needs your tap is done by email: approvals only say "waiting for you".
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .config import get_settings
from .db import Conversation, Message, PhoneSeen, User, session

log = logging.getLogger("santosh.offline")
_touched: dict[str, float] = {}


def touch(tenant_id: str) -> None:
    """Mark the phone as seen (throttled to once a minute per tenant)."""
    if not tenant_id:
        return
    t = time.time()
    if t - _touched.get(tenant_id, 0) < 60:
        return
    _touched[tenant_id] = t
    try:
        with session() as s:
            row = s.get(PhoneSeen, tenant_id)
            if row is None:
                last = s.scalar(select(Message.id).order_by(Message.id.desc()).limit(1)) or 0
                s.add(PhoneSeen(tenant_id=tenant_id, at=datetime.now(timezone.utc), digest_upto_id=last))
            else:
                row.at = datetime.now(timezone.utc)
    except Exception:
        log.exception("touch failed")


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def recipient(tenant_id: str) -> str:
    st = get_settings()
    if tenant_id == st.tenant_id:
        if st.owner_emails.strip():
            return st.owner_emails.split(",")[0].strip()
        return st.email_address
    with session() as s:
        u = s.get(User, tenant_id)
        return u.email if u else ""


def due_digests(now: datetime | None = None) -> list[dict]:
    """Which tenants need an email now, and what goes in it."""
    st = get_settings()
    now = now or datetime.now(timezone.utc)
    out = []
    with session() as s:
        for row in s.scalars(select(PhoneSeen)).all():
            seen = _utc(row.at)
            if seen is None or now - seen < timedelta(minutes=st.offline_after_min):
                continue
            sent = _utc(row.digest_sent_at)
            if sent and now - sent < timedelta(minutes=30):
                continue
            convs = [c.id for c in s.scalars(select(Conversation).where(Conversation.tenant_id == row.tenant_id)).all()]
            if not convs:
                continue
            msgs = s.scalars(select(Message).where(Message.conversation_id.in_(convs), Message.role == "assistant",
                                                   Message.in_history.is_(False), Message.id > row.digest_upto_id)
                             .order_by(Message.id).limit(30)).all()
            items = [(m.id, _utc(m.created_at), m.display or "") for m in msgs if (m.display or "").strip()]
            if items:
                out.append({"tenant_id": row.tenant_id, "since": seen, "items": items})
    return out


def compose(d: dict) -> tuple[str, str]:
    ist = timezone(timedelta(hours=5, minutes=30))
    n = len(d["items"])
    subject = f"Santosh: aapke phone ke bina {n} update" + ("" if n == 1 else "s")
    lines = ["Namaste! Aapka phone kuch der se offline hai, isliye yeh updates email par bhej raha hoon:", ""]
    for _, at, text in d["items"]:
        lines.append(f"• {at.astimezone(ist).strftime('%I:%M %p').lstrip('0')} — {text}")
    lines += ["", "Kuch bhi approve karna ho to phone on hote hi Santosh app mein dikhega. "
              "Payment kabhi email se nahi hota.", "", "— Santosh"]
    return subject, "\n".join(lines)


# v0.92 a digest that cannot go out is not retried every 2 minutes forever (the VPS log showed exactly that):
# after a failure the next try waits 30 min, then 1 h, 2 h ... up to 12 h; one log line per wait, with the fix.
_FAIL: dict[str, tuple[int, float]] = {}
STATS = {"sent": 0, "via_api": 0, "via_smtp": 0, "failed": 0}


class _NoRoute(Exception):
    pass


def _may_try(tenant: str) -> bool:
    n, next_at = _FAIL.get(tenant, (0, 0.0))
    return time.time() >= next_at


def _failed(tenant: str, to: str, e: Exception) -> None:
    n = _FAIL.get(tenant, (0, 0.0))[0] + 1
    wait_min = min(30 * 2 ** (n - 1), 720)
    _FAIL[tenant] = (n, time.time() + wait_min * 60)
    STATS["failed"] += 1
    text = str(e)
    hint = ""
    if any(w in text for w in ("Errno 101", "unreachable", "timed out", "Errno 110", "Connection refused")):
        hint = (" (this server cannot reach the mail server by SMTP - most cloud servers block SMTP ports; sign in with "
                "Google / Outlook in the app so the digest goes through their API over HTTPS)")
    log.warning("offline digest to %s failed (%s)%s; next try in %s min", to, text[:160], hint, wait_min)


async def _deliver(tenant: str, to: str, subject: str, body: str) -> str:
    """Her own Gmail / Outlook sign-in first (HTTPS API: works where SMTP ports are blocked), then the server's SMTP."""
    import asyncio
    from email.message import EmailMessage

    from . import mail
    api_err: Exception | None = None
    try:
        from .mailbox.accounts import boxes
        api = [b for b in await asyncio.to_thread(boxes, tenant) if getattr(b, "kind", "") in ("gmail", "outlook")]
    except Exception:
        api = []
    for b in api:
        msg = EmailMessage()
        msg["From"] = b.address
        msg["To"] = to
        msg["Subject"] = subject
        import email.utils as eu
        msg["Date"] = eu.formatdate(localtime=True)
        msg["Message-ID"] = eu.make_msgid(domain=(b.address.split("@")[-1] or "hoola"))
        msg.set_content(body)
        try:
            await asyncio.to_thread(b.send, msg)
            STATS["via_api"] += 1
            return b.kind
        except Exception as e:      # an expired sign-in etc.: try the next route
            api_err = e
    if tenant == get_settings().tenant_id and mail.configured():
        await mail.send_email(to, subject, body)
        STATS["via_smtp"] += 1
        return "smtp"
    if api_err is not None:
        raise api_err
    raise _NoRoute()


async def send_due() -> int:
    st = get_settings()
    if not st.offline_email:
        return 0
    sent = 0
    for d in due_digests():
        tenant = d["tenant_id"]
        if not _may_try(tenant):
            continue
        to = recipient(tenant)
        if "@" not in (to or ""):
            continue
        subject, body = compose(d)
        try:
            await _deliver(tenant, to, subject, body)
        except _NoRoute:
            continue
        except Exception as e:
            _failed(tenant, to, e)
            continue
        _FAIL.pop(tenant, None)
        with session() as s:
            row = s.get(PhoneSeen, tenant)
            if row:
                row.digest_upto_id = d["items"][-1][0]
                row.digest_sent_at = datetime.now(timezone.utc)
        sent += 1
        STATS["sent"] += 1
    return sent
