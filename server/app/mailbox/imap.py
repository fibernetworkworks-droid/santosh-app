"""Any mailbox with an app password: IMAP to read and organise, SMTP to send (Gmail, Outlook, Yahoo, Zoho, Rediff,
iCloud, custom domains)."""
from __future__ import annotations

import base64
import email
import email.utils
import imaplib
import re
import smtplib
import ssl
import time
from datetime import datetime
from email.message import EmailMessage
from typing import Any

from . import mime
from .base import Box, MailError

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
    "zohomail.in": ("imap.zoho.in", "smtp.zoho.in", 587),
    "rediffmail.com": ("imap.rediffmail.com", "smtp.rediffmail.com", 587),
    "icloud.com": ("imap.mail.me.com", "smtp.mail.me.com", 587),
    "me.com": ("imap.mail.me.com", "smtp.mail.me.com", 587),
}
# these servers file sent mail in "Sent" themselves; for the rest we append a copy
AUTO_SAVES_SENT = ("gmail.com", "googlemail.com", "office365.com", "outlook.office365.com", "smtp.office365.com",
                   "yahoo.com", "zoho.com", "zoho.in", "mail.me.com")

SPECIAL = {"\\sent": "sent", "\\trash": "trash", "\\junk": "spam", "\\archive": "archive", "\\all": "all",
           "\\flagged": "starred", "\\drafts": "drafts"}
GUESS = {"sent": ["Sent", "Sent Items", "Sent Messages", "Sent Mail", "INBOX.Sent", "[Gmail]/Sent Mail"],
         "trash": ["Trash", "Deleted Items", "Deleted Messages", "Deleted", "INBOX.Trash", "[Gmail]/Trash", "Bin"],
         "spam": ["Spam", "Junk", "Junk E-mail", "Junk Email", "Bulk Mail", "INBOX.Spam", "[Gmail]/Spam"],
         "archive": ["Archive", "Archives", "INBOX.Archive", "[Gmail]/All Mail"],
         "drafts": ["Drafts", "INBOX.Drafts", "[Gmail]/Drafts"],
         "starred": ["[Gmail]/Starred", "Starred", "Flagged"]}
LIST_RE = re.compile(rb'\((?P<flags>[^)]*)\)\s+(?P<delim>"[^"]*"|NIL)\s+(?P<name>.+)$')
HDRS = "FROM TO CC SUBJECT DATE MESSAGE-ID LIST-UNSUBSCRIBE PRECEDENCE AUTO-SUBMITTED CONTENT-TYPE"


def hosts_for(address: str, imap_host: str = "", smtp_host: str = "", smtp_port: int = 0) -> tuple[str, str, int]:
    domain = address.split("@")[-1].lower()
    imap_d, smtp_d, port_d = PROVIDERS.get(domain, ("", "", 587))
    imap_h, smtp_h = imap_host or imap_d, smtp_host or smtp_d
    if not imap_h or not smtp_h:
        if domain and "." in domain:   # custom domains usually follow mail.<domain>
            imap_h, smtp_h = imap_h or f"imap.{domain}", smtp_h or f"smtp.{domain}"
        else:
            raise MailError(f"'{domain}' ke liye mail server nahi mila. IMAP aur SMTP host bhi bataiye.")
    return imap_h, smtp_h, int(smtp_port or port_d or 587)


def _q(name: str) -> str:
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _enc_folder(folder: str) -> str:
    return base64.urlsafe_b64encode(folder.encode()).decode().rstrip("=")


def _dec_folder(s: str) -> str:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()


def split_id(mid: str) -> tuple[str, str]:
    """IMAP uids are per folder: "123" is INBOX/123, "123@<b64 folder>" another folder."""
    if "@" in mid:
        uid, f = mid.split("@", 1)
        return _dec_folder(f), uid
    return "INBOX", mid


def make_id(folder: str, uid: str) -> str:
    return uid if folder.upper() == "INBOX" else f"{uid}@{_enc_folder(folder)}"


class ImapBox(Box):
    kind = "imap"

    def __init__(self, key: str, address: str, password: str, name: str = "", signature: str = "",
                 imap_host: str = "", imap_port: int = 993, smtp_host: str = "", smtp_port: int = 0) -> None:
        super().__init__(key, address, name, signature)
        self.password = password
        self.imap_host, self.smtp_host, self.smtp_port = hosts_for(address, imap_host, smtp_host, smtp_port)
        self.imap_port = int(imap_port or 993)
        self._special: dict[str, str] | None = None

    # ---------------- connection ----------------
    def _login(self) -> imaplib.IMAP4_SSL:
        try:
            M = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, timeout=25)
            M.login(self.address, self.password)
            return M
        except imaplib.IMAP4.error as e:
            raise MailError(f"Email login fail hua: {e}. App password sahi hai? (Gmail: myaccount.google.com/apppasswords)")
        except OSError as e:
            raise MailError(f"Email server ({self.imap_host}) se connect nahi hua: {e}")

    def _run(self, fn):
        M = self._login()
        try:
            return fn(M)
        finally:
            try:
                M.logout()
            except Exception:
                pass

    def check(self) -> None:
        """Log in to IMAP and SMTP once (used when the user connects the mailbox)."""
        self._run(lambda M: M.select("INBOX", readonly=True))
        with self._smtp():
            pass

    def _specials(self, M) -> dict[str, str]:
        if self._special is not None:
            return self._special
        found: dict[str, str] = {}
        names: list[str] = []
        typ, data = M.list()
        for line in data or []:
            if not isinstance(line, bytes):
                continue
            m = LIST_RE.match(line)
            if not m:
                continue
            name = m.group("name").strip()
            if name.startswith(b'"') and name.endswith(b'"'):
                name = name[1:-1].replace(b'\\"', b'"').replace(b"\\\\", b"\\")
            n = name.decode("utf-8", "replace")
            names.append(n)
            for flag in m.group("flags").decode().lower().split():
                if flag in SPECIAL and SPECIAL[flag] not in found:
                    found[SPECIAL[flag]] = n
        lower = {n.lower(): n for n in names}
        for kind, guesses in GUESS.items():
            if kind not in found:
                for g in guesses:
                    if g.lower() in lower:
                        found[kind] = lower[g.lower()]
                        break
        found["_all_names"] = "\n".join(names)
        self._special = found
        return found

    def _folder(self, M, folder: str, create: bool = False) -> str:
        f = (folder or "inbox").strip()
        if f.lower() == "inbox":
            return "INBOX"
        sp = self._specials(M)
        if f.lower() in sp and not f.startswith("_"):
            return sp[f.lower()]
        names = sp.get("_all_names", "").split("\n")
        for n in names:
            if n.lower() == f.lower() or n.lower().endswith("/" + f.lower()) or n.lower().endswith("." + f.lower()):
                return n
        if f.lower() == "archive" or create:
            name = "Archive" if f.lower() == "archive" else f
            M.create(_q(name))
            self._special = None
            return name
        raise MailError(f"'{folder}' naam ka folder nahi mila. Folders: {', '.join(n for n in names if n)[:400]}")

    # ---------------- reading ----------------
    def list(self, folder="inbox", unread_only=False, search=None, limit=10, since=None, snippets=False):
        limit = max(1, min(int(limit or 10), 50))

        def go(M):
            fname = self._folder(M, folder)
            starred_fallback = folder == "starred" and fname == "INBOX"
            typ, _ = M.select(_q(fname), readonly=True)
            if typ != "OK":
                raise MailError(f"Folder '{fname}' nahi khula")
            crit: list[str] = []
            if unread_only:
                crit.append("UNSEEN")
            if starred_fallback:
                crit.append("FLAGGED")
            if since:
                crit += ["SINCE", since.strftime("%d-%b-%Y")]
            if search:
                s = re.sub(r'["\\]', " ", search).strip()
                if s.isascii():
                    crit += ["OR", "OR", "FROM", _q(s), "SUBJECT", _q(s), "TEXT", _q(s)]
            typ, data = M.uid("search", None, *(crit or ["ALL"]))
            uids = (data[0].split() if data and data[0] else [])[-limit:][::-1]
            out = []
            for uid in uids:
                item = self._summary(M, uid, fname, snippets)
                if item:
                    if since and item.get("_ts") and item["_ts"] < since.timestamp():
                        continue
                    item.pop("_ts", None)
                    out.append(item)
            return out
        return self._run(go)

    def _summary(self, M, uid: bytes, fname: str, snippets: bool) -> dict[str, Any] | None:
        parts = f"(FLAGS BODY.PEEK[HEADER.FIELDS ({HDRS})]" + (" BODY.PEEK[TEXT]<0.4000>" if snippets else "") + ")"
        typ, md = M.uid("fetch", uid, parts)
        if typ != "OK" or not md:
            return None
        hdr_bytes, text_bytes, meta = b"", b"", b""
        for it in md:
            if isinstance(it, tuple):
                meta += it[0]
                if b"HEADER.FIELDS" in it[0].upper():
                    hdr_bytes = it[1]
                elif b"TEXT" in it[0].upper():
                    text_bytes = it[1]
            elif isinstance(it, bytes):
                meta += it
        flags = re.search(rb"FLAGS \(([^)]*)\)", meta)
        flags_s = flags.group(1).decode(errors="replace") if flags else ""
        msg = email.message_from_bytes(hdr_bytes)
        h = mime.headers_of(msg)
        ctype = str(msg.get("Content-Type") or "").lower()
        snippet = ""
        if snippets and text_bytes:
            snippet = mime.snippet_of(hdr_bytes + b"\r\n" + text_bytes) or \
                re.sub(r"\s+", " ", mime.html_to_text(text_bytes.decode("utf-8", "replace")))[:220]
        ts = None
        try:
            ts = email.utils.parsedate_to_datetime(h["date"]).timestamp()
        except Exception:
            pass
        return {"id": make_id(fname, uid.decode()), "thread_id": "", "from": h["from"], "from_email": h["from_email"],
                "to": h["to"], "subject": h["subject"], "date": h["date"], "unread": "\\Seen" not in flags_s,
                "starred": "\\Flagged" in flags_s, "snippet": snippet, "bulk": h["bulk"],
                "has_attachments": ctype.startswith("multipart/mixed"), "message_id": h["message_id"], "_ts": ts}

    def raw(self, mid):
        fname, uid = split_id(mid)

        def go(M):
            M.select(_q(fname), readonly=True)
            typ, md = M.uid("fetch", uid.encode(), "(BODY.PEEK[])")
            for it in md or []:
                if isinstance(it, tuple):
                    return it[1]
            raise MailError("Yeh email nahi mila (shayad hata di gayi).")
        return self._run(go)

    # ---------------- organising ----------------
    def _group(self, ids):
        g: dict[str, list[str]] = {}
        for i in ids:
            f, uid = split_id(i)
            g.setdefault(f, []).append(uid)
        return g

    def _flags(self, ids, flag: str, on: bool):
        def go(M):
            for f, uids in self._group(ids).items():
                M.select(_q(f))
                M.uid("store", ",".join(uids), "+FLAGS" if on else "-FLAGS", f"({flag})")
        self._run(go)

    def mark(self, ids, read):
        self._flags(ids, "\\Seen", read)

    def star(self, ids, on):
        self._flags(ids, "\\Flagged", on)

    def _move(self, ids, target_kind: str, create: bool = False):
        def go(M):
            dest = self._folder(M, target_kind, create=create)
            caps = [c.upper() for c in (M.capabilities or ())]
            for f, uids in self._group(ids).items():
                if f == dest:
                    continue
                M.select(_q(f))
                seq = ",".join(uids)
                if "MOVE" in caps:
                    typ, _ = M.uid("MOVE", seq, _q(dest))
                    if typ == "OK":
                        continue
                M.uid("COPY", seq, _q(dest))
                M.uid("STORE", seq, "+FLAGS", "(\\Deleted)")
                if "UIDPLUS" in caps:
                    M.uid("EXPUNGE", seq)
                else:
                    M.expunge()
        self._run(go)

    def archive(self, ids):
        self._move(ids, "archive")

    def trash(self, ids):
        self._move(ids, "trash")

    def move(self, ids, folder):
        self._move(ids, folder, create=True)

    def folders(self):
        sp = self._run(self._specials)
        return [n for n in sp.get("_all_names", "").split("\n") if n]

    # ---------------- sending ----------------
    def _smtp(self):
        ctx = ssl.create_default_context()
        try:
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30, context=ctx)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.ehlo()
                server.starttls(context=ctx)
                server.ehlo()
            server.login(self.address, self.password)
            return server
        except smtplib.SMTPAuthenticationError as e:
            raise MailError(f"Email login fail hua (app password check kijiye): {e}")
        except (smtplib.SMTPException, OSError) as e:
            raise MailError(f"Email server ({self.smtp_host}) se connect nahi hua: {e}")

    def send(self, msg: EmailMessage, thread_id=None):
        rcpt = mime.recipients(msg)
        bcc = msg.get("Bcc")
        if bcc:
            del msg["Bcc"]           # never show Bcc to the other recipients
        try:
            with self._smtp() as server:
                server.send_message(msg, from_addr=self.address, to_addrs=rcpt)
        except MailError:
            raise
        except (smtplib.SMTPException, OSError) as e:
            raise MailError(f"Email bhejne mein dikkat: {e}")
        if not any(self.smtp_host.endswith(d) or self.address.endswith("@" + d) for d in AUTO_SAVES_SENT):
            try:
                def put(M):
                    dest = self._folder(M, "sent", create=True)
                    M.append(_q(dest), "(\\Seen)", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                self._run(put)
            except Exception:
                pass
        return {"message_id": msg["Message-ID"], "thread_id": ""}

    def replies(self, message_id, thread_id, since):
        mid = (message_id or "").strip()
        if not mid:
            return {"from_them": False, "from_me": False}

        def go(M):
            res = {"from_them": False, "from_me": False}
            for kind in ("inbox", "sent"):
                try:
                    f = self._folder(M, kind)
                except MailError:
                    continue
                M.select(_q(f), readonly=True)
                typ, data = M.uid("search", None, "OR", "HEADER", "In-Reply-To", _q(mid), "HEADER", "References", _q(mid))
                for uid in (data[0].split() if data and data[0] else []):
                    item = self._summary(M, uid, f, False)
                    if not item:
                        continue
                    if item.get("_ts") and item["_ts"] < since.timestamp() - 60:
                        continue
                    if item["from_email"] == self.address:
                        res["from_me"] = True
                    else:
                        res["from_them"] = True
            return res
        return self._run(go)
