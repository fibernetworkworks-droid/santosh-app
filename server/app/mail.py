"""Email for Santosh: read the inbox over IMAP, send approved mail over SMTP.

Works with any provider via an app password. Hosts auto-detect for the common Indian/consumer ones;
a custom domain sets EMAIL_IMAP_HOST / EMAIL_SMTP_HOST. Blocking imaplib/smtplib calls run in a thread.
"""
from __future__ import annotations

import asyncio
import email
import email.utils
import imaplib
import logging
import re
import smtplib
import ssl
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.mime.text import MIMEText

from .config import get_settings

log = logging.getLogger("santosh.mail")

# host suffix -> (imap_host, smtp_host, smtp_port)
PROVIDERS = {
    "gmail.com": ("imap.gmail.com", "smtp.gmail.com", 587),
    "googlemail.com": ("imap.gmail.com", "smtp.gmail.com", 587),
    "outlook.com": ("outlook.office365.com", "smtp.office365.com", 587),
    "hotmail.com": ("outlook.office365.com", "smtp.office365.com", 587),
    "live.com": ("outlook.office365.com", "smtp.office365.com", 587),
    "office365.com": ("outlook.office365.com", "smtp.office365.com", 587),
    "yahoo.com": ("imap.mail.yahoo.com", "smtp.mail.yahoo.com", 587),
    "yahoo.in": ("imap.mail.yahoo.com", "smtp.mail.yahoo.com", 587),
    "zoho.com": ("imap.zoho.com", "smtp.zoho.com", 587),
    "zoho.in": ("imap.zoho.in", "smtp.zoho.in", 587),
    "rediffmail.com": ("imap.rediffmail.com", "smtp.rediffmail.com", 587),
    "icloud.com": ("imap.mail.me.com", "smtp.mail.me.com", 587),
}


class MailError(Exception):
    pass


def configured() -> bool:
    st = get_settings()
    return bool(st.email_address and st.email_password)


def _hosts():
    st = get_settings()
    if not configured():
        raise MailError("Email set nahi hai. Server ke .env mein EMAIL_ADDRESS aur EMAIL_PASSWORD daaliye.")
    domain = st.email_address.split("@")[-1].lower()
    imap_d, smtp_d, smtp_port_d = PROVIDERS.get(domain, ("", "", 587))
    imap = st.email_imap_host or imap_d
    smtp = st.email_smtp_host or smtp_d
    smtp_port = st.email_smtp_port or smtp_port_d
    if not imap or not smtp:
        raise MailError(f"'{domain}' ke liye server address nahi mila. .env mein EMAIL_IMAP_HOST aur EMAIL_SMTP_HOST set kijiye.")
    return imap, st.email_imap_port, smtp, smtp_port


def _dec(raw) -> str:
    if raw is None:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return str(raw)


def _addr_name(raw: str) -> tuple[str, str]:
    name, addr = email.utils.parseaddr(_dec(raw))
    return (name or addr, addr)


def _body_text(msg: email.message.Message) -> str:
    """Prefer text/plain; fall back to stripping a text/html part."""
    html_part = None
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" in disp:
                continue
            if ctype == "text/plain":
                return _payload(part)
            if ctype == "text/html" and html_part is None:
                html_part = part
        if html_part is not None:
            return _html_to_text(_payload(html_part))
        return ""
    if msg.get_content_type() == "text/html":
        return _html_to_text(_payload(msg))
    return _payload(msg)


def _payload(part) -> str:
    try:
        data = part.get_payload(decode=True)
        if data is None:
            return ""
        return data.decode(part.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return ""


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|tr|li|h[1-6])>", "\n", html)
    text = re.sub(r"<[^>]+>", " ", html)
    import html as _h
    text = _h.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


# ---------------- IMAP (reading) ----------------
def _imap_login() -> imaplib.IMAP4_SSL:
    imap_host, imap_port, _, _ = _hosts()
    st = get_settings()
    try:
        M = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=25)
        M.login(st.email_address, st.email_password)
        return M
    except imaplib.IMAP4.error as e:
        raise MailError(f"Email login fail hua: {e}. App password sahi hai? (Gmail: myaccount.google.com/apppasswords)")
    except OSError as e:
        raise MailError(f"Email server se connect nahi hua: {e}")


def _fetch(limit: int, unread_only: bool, search: str | None, mailbox: str):
    M = _imap_login()
    try:
        M.select(mailbox, readonly=True)
        crit = ["UNSEEN"] if unread_only else ["ALL"]
        if search:
            s = search.replace('"', " ")
            crit = ["OR", "OR", "FROM", f'"{s}"', "SUBJECT", f'"{s}"', "TEXT", f'"{s}"']
        typ, data = M.uid("search", None, *crit)
        uids = (data[0].split() if data and data[0] else [])[-limit:][::-1]
        out = []
        for uid in uids:
            typ, md = M.uid("fetch", uid, "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])")
            if typ != "OK" or not md or not md[0]:
                continue
            flags = md[0][0].decode(errors="replace") if isinstance(md[0], tuple) else ""
            hdr = email.message_from_bytes(md[0][1]) if isinstance(md[0], tuple) else email.message_from_string("")
            name, addr = _addr_name(hdr.get("From"))
            out.append({
                "id": uid.decode(), "from": name, "from_email": addr,
                "subject": _dec(hdr.get("Subject")) or "(no subject)",
                "date": _dec(hdr.get("Date")), "unread": "\\Seen" not in flags,
            })
        return out
    finally:
        try:
            M.logout()
        except Exception:
            pass


def _read_one(uid: str, mailbox: str, mark_seen: bool):
    M = _imap_login()
    try:
        M.select(mailbox, readonly=not mark_seen)
        typ, md = M.uid("fetch", uid.encode(), "(RFC822)")
        if typ != "OK" or not md or not md[0]:
            raise MailError("Yeh email nahi mila (shayad hata di gayi).")
        msg = email.message_from_bytes(md[0][1])
        if mark_seen:
            try:
                M.uid("store", uid.encode(), "+FLAGS", "(\\Seen)")
            except Exception:
                pass
        name, addr = _addr_name(msg.get("From"))
        body = _body_text(msg).strip()
        return {
            "id": uid, "from": name, "from_email": addr,
            "to": _dec(msg.get("To")), "cc": _dec(msg.get("Cc")),
            "subject": _dec(msg.get("Subject")) or "(no subject)",
            "date": _dec(msg.get("Date")),
            "message_id": (msg.get("Message-ID") or "").strip(),
            "references": (msg.get("References") or "").strip(),
            "body": body[:8000], "truncated": len(body) > 8000,
        }
    finally:
        try:
            M.logout()
        except Exception:
            pass


# ---------------- SMTP (sending) ----------------
def _send(to_addr: str, subject: str, body: str, cc: str, in_reply_to: str | None, references: str | None):
    st = get_settings()
    _, _, smtp_host, smtp_port = _hosts()
    msg = EmailMessage()
    from_name = st.email_sender_name or st.email_address.split("@")[0]
    msg["From"] = email.utils.formataddr((str(make_header([(from_name, "utf-8")])), st.email_address))
    msg["To"] = to_addr
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain=st.email_address.split("@")[-1])
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = (references + " " + in_reply_to).strip() if references else in_reply_to
    msg.set_content(body)
    recipients = [a for a in email.utils.getaddresses([to_addr, cc]) if a[1]]
    rcpt = [a[1] for a in recipients]
    try:
        ctx = ssl.create_default_context()
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=25, context=ctx)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=25)
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
        with server:
            server.login(st.email_address, st.email_password)
            server.send_message(msg, from_addr=st.email_address, to_addrs=rcpt)
    except smtplib.SMTPAuthenticationError as e:
        raise MailError(f"Email login fail hua (app password check kijiye): {e}")
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(f"Email bhejne mein dikkat: {e}")
    return msg["Message-ID"]


# ---------------- async wrappers ----------------
async def fetch_recent(limit=10, unread_only=False, search=None, mailbox="INBOX"):
    return await asyncio.to_thread(_fetch, max(1, min(limit, 25)), unread_only, search, mailbox)


async def read_email(uid: str, mailbox="INBOX", mark_seen=True):
    return await asyncio.to_thread(_read_one, uid, mailbox, mark_seen)


async def send_email(to_addr, subject, body, cc="", in_reply_to=None, references=None):
    return await asyncio.to_thread(_send, to_addr, subject, body, cc, in_reply_to, references)
