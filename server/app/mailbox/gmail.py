"""Gmail through the official Gmail API (OAuth, scope gmail.modify). Messages are fetched as raw MIME so parsing and
attachments are the same as every other mailbox."""
from __future__ import annotations

import base64
import html
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Callable

import httpx

from . import mime
from .base import Box, MailError

API = "https://gmail.googleapis.com/gmail/v1/users/me"
FOLDER_Q = {"inbox": "in:inbox", "sent": "in:sent", "trash": "in:trash", "spam": "in:spam", "starred": "is:starred",
            "drafts": "in:drafts", "archive": "-in:inbox -in:sent -in:drafts -in:trash -in:spam -in:chats"}
META = ["From", "To", "Cc", "Subject", "Date", "Message-ID", "List-Unsubscribe", "Precedence", "Auto-Submitted"]


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def unb64url(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class GmailBox(Box):
    kind = "gmail"

    def __init__(self, key: str, address: str, token: Callable[[bool], str], name: str = "", signature: str = "",
                 client: httpx.Client | None = None) -> None:
        super().__init__(key, address, name, signature)
        self._token = token
        self._client = client

    def _req(self, method: str, path: str, **kw) -> Any:
        c = self._client or httpx.Client(timeout=40)
        try:
            for attempt in (0, 1):
                r = c.request(method, API + path, headers={"Authorization": f"Bearer {self._token(attempt == 1)}"}, **kw)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise MailError(f"Gmail se baat nahi ho payi ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 403 and "insufficient" in r.text.lower():
            raise MailError("Gmail ki permission nahi mili. App mein Profile > Email se Gmail dobara jodiye.")
        if r.status_code == 404:
            raise MailError("Yeh email nahi mila (shayad hata di gayi).")
        if r.status_code >= 400:
            raise MailError(f"Gmail error {r.status_code}: {r.text[:200]}")
        return r.json() if r.content else {}

    # ---------------- reading ----------------
    def _labels(self) -> list[dict]:
        return self._req("GET", "/labels").get("labels", [])

    def _label_id(self, name: str, create: bool = False) -> str:
        for lb in self._labels():
            if lb["name"].lower() == name.lower() or lb["id"].lower() == name.lower():
                return lb["id"]
        if not create:
            raise MailError(f"'{name}' naam ka label nahi mila")
        return self._req("POST", "/labels", json={"name": name, "labelListVisibility": "labelShow",
                                                   "messageListVisibility": "show"})["id"]

    def list(self, folder="inbox", unread_only=False, search=None, limit=10, since=None, snippets=False):
        f = (folder or "inbox").lower()
        q = [FOLDER_Q.get(f) or f'label:"{folder}"']
        if unread_only:
            q.append("is:unread")
        if since:
            q.append(f"after:{int(since.timestamp())}")
        if search:
            q.append(search)
        params = {"q": " ".join(q), "maxResults": max(1, min(int(limit or 10), 50))}
        if f in ("trash", "spam"):
            params["includeSpamTrash"] = "true"
        ids = [m["id"] for m in self._req("GET", "/messages", params=params).get("messages", [])]
        out = []
        for mid in ids:
            m = self._req("GET", f"/messages/{mid}", params=[("format", "metadata")] + [("metadataHeaders", h) for h in META])
            out.append(self._summary(m))
        return out

    def _summary(self, m: dict) -> dict[str, Any]:
        hdrs = {h["name"].lower(): h["value"] for h in (m.get("payload") or {}).get("headers", [])}
        name, a = mime.addr(hdrs.get("from"))
        labels = m.get("labelIds") or []
        bulk = bool(hdrs.get("list-unsubscribe") or hdrs.get("precedence", "").lower() in ("bulk", "list", "junk")
                    or hdrs.get("auto-submitted", "no").lower() != "no" or "CATEGORY_PROMOTIONS" in labels
                    or "CATEGORY_SOCIAL" in labels)
        return {"id": m["id"], "thread_id": m.get("threadId", ""), "from": name, "from_email": a,
                "to": mime.dec(hdrs.get("to")), "subject": mime.dec(hdrs.get("subject")) or "(no subject)",
                "date": hdrs.get("date", ""), "unread": "UNREAD" in labels, "starred": "STARRED" in labels,
                "snippet": html.unescape(m.get("snippet", "")), "bulk": bulk,
                "has_attachments": (m.get("payload") or {}).get("mimeType", "").startswith("multipart/mixed"),
                "message_id": hdrs.get("message-id", ""), "important": "IMPORTANT" in labels}

    def raw(self, mid):
        return unb64url(self._req("GET", f"/messages/{mid}", params={"format": "raw"})["raw"])

    def thread_of(self, mid):
        return self._req("GET", f"/messages/{mid}", params={"format": "minimal"}).get("threadId", "")

    # ---------------- organising ----------------
    def _modify(self, ids, add=(), remove=()):
        self._req("POST", "/messages/batchModify", json={"ids": list(ids), "addLabelIds": list(add), "removeLabelIds": list(remove)})

    def mark(self, ids, read):
        self._modify(ids, remove=["UNREAD"]) if read else self._modify(ids, add=["UNREAD"])

    def star(self, ids, on):
        self._modify(ids, add=["STARRED"]) if on else self._modify(ids, remove=["STARRED"])

    def archive(self, ids):
        self._modify(ids, remove=["INBOX"])

    def trash(self, ids):
        for i in ids:
            self._req("POST", f"/messages/{i}/trash")

    def move(self, ids, folder):
        f = folder.lower()
        if f == "inbox":
            return self._modify(ids, add=["INBOX"], remove=["TRASH", "SPAM"])
        if f == "archive":
            return self.archive(ids)
        if f == "trash":
            return self.trash(ids)
        if f == "spam":
            return self._modify(ids, add=["SPAM"], remove=["INBOX"])
        self._modify(ids, add=[self._label_id(folder, create=True)], remove=["INBOX"])

    def folders(self):
        return ["inbox", "sent", "archive", "starred", "spam", "trash"] + \
            sorted(lb["name"] for lb in self._labels() if lb.get("type") == "user")

    # ---------------- sending ----------------
    def send(self, msg: EmailMessage, thread_id=None):
        body: dict[str, Any] = {"raw": b64url(msg.as_bytes())}
        if thread_id:
            body["threadId"] = thread_id
        out = self._req("POST", "/messages/send", json=body)
        return {"message_id": msg["Message-ID"], "thread_id": out.get("threadId", ""), "id": out.get("id", "")}

    def replies(self, message_id, thread_id, since):
        tid = thread_id
        if not tid and message_id:
            found = self._req("GET", "/messages", params={"q": f"rfc822msgid:{message_id.strip('<>')}", "maxResults": 1,
                                                          "includeSpamTrash": "true"}).get("messages", [])
            tid = found[0]["threadId"] if found else ""
        res = {"from_them": False, "from_me": False}
        if not tid:
            return res
        t = self._req("GET", f"/threads/{tid}", params={"format": "metadata", "metadataHeaders": "From"})
        cutoff = since.timestamp() * 1000 + 60_000
        for m in t.get("messages", []):
            if int(m.get("internalDate", 0)) <= cutoff:
                continue
            hdrs = {h["name"].lower(): h["value"] for h in (m.get("payload") or {}).get("headers", [])}
            _, frm = mime.addr(hdrs.get("from"))
            if "SENT" in (m.get("labelIds") or []) or frm == self.address:
                res["from_me"] = True
            else:
                res["from_them"] = True
        return res
