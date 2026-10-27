"""Outlook / Microsoft 365 / Hotmail through the official Microsoft Graph API (OAuth: Mail.ReadWrite, Mail.Send)."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Callable
from urllib.parse import quote

import httpx

from . import mime
from .base import Box, MailError

API = "https://graph.microsoft.com/v1.0/me"
WELL_KNOWN = {"inbox": "inbox", "sent": "sentitems", "archive": "archive", "trash": "deleteditems",
              "spam": "junkemail", "drafts": "drafts"}
SELECT = "id,conversationId,subject,from,toRecipients,receivedDateTime,isRead,hasAttachments,bodyPreview," \
         "internetMessageId,flag,inferenceClassification"


def _q(mid: str) -> str:
    return quote(mid, safe="")


class OutlookBox(Box):
    kind = "outlook"

    def __init__(self, key: str, address: str, token: Callable[[bool], str], name: str = "", signature: str = "",
                 client: httpx.Client | None = None) -> None:
        super().__init__(key, address, name, signature)
        self._token = token
        self._client = client

    def _req(self, method: str, path: str, raw: bool = False, **kw) -> Any:
        c = self._client or httpx.Client(timeout=40)
        extra = kw.pop("headers", {})
        url = path if path.startswith("http") else API + path
        try:
            for attempt in (0, 1):
                r = c.request(method, url, headers={"Authorization": f"Bearer {self._token(attempt == 1)}", **extra}, **kw)
                if r.status_code == 401 and attempt == 0:
                    continue
                break
        except httpx.HTTPError as e:
            raise MailError(f"Outlook se baat nahi ho payi ({type(e).__name__})")
        finally:
            if self._client is None:
                c.close()
        if r.status_code == 404:
            raise MailError("Yeh email ya folder nahi mila.")
        if r.status_code >= 400:
            raise MailError(f"Outlook error {r.status_code}: {r.text[:200]}")
        if raw:
            return r.content
        return r.json() if r.content else {}

    # ---------------- folders ----------------
    def _all_folders(self) -> list[dict]:
        out = self._req("GET", "/mailFolders", params={"$top": "100"}).get("value", [])
        try:
            out += self._req("GET", "/mailFolders/inbox/childFolders", params={"$top": "100"}).get("value", [])
        except MailError:
            pass
        return out

    def _folder_id(self, folder: str, create: bool = False) -> str:
        f = (folder or "inbox").lower()
        if f in WELL_KNOWN:
            return WELL_KNOWN[f]
        for x in self._all_folders():
            if x.get("displayName", "").lower() == f:
                return x["id"]
        if not create:
            raise MailError(f"'{folder}' naam ka folder nahi mila")
        return self._req("POST", "/mailFolders", json={"displayName": folder})["id"]

    # ---------------- reading ----------------
    def list(self, folder="inbox", unread_only=False, search=None, limit=10, since=None, snippets=False):
        limit = max(1, min(int(limit or 10), 50))
        f = (folder or "inbox").lower()
        fid = "inbox" if f == "starred" else self._folder_id(folder)
        params: dict[str, str] = {"$top": str(limit if not search else min(limit * 2, 50)), "$select": SELECT}
        filters = []
        if search:
            params["$search"] = '"' + search.replace('"', " ") + '"'
        else:
            params["$orderby"] = "receivedDateTime desc"
            if unread_only:
                filters.append("isRead eq false")
            if since:
                filters.append("receivedDateTime ge " + since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
            if f == "starred":
                filters.append("flag/flagStatus eq 'flagged'")
            if filters:
                params["$filter"] = " and ".join(filters)
        rows = self._req("GET", f"/mailFolders/{fid}/messages", params=params).get("value", [])
        out = [self._summary(m) for m in rows]
        if search:   # $search can't be combined with filters; apply them here
            if unread_only:
                out = [o for o in out if o["unread"]]
            if since:
                out = [o for o in out if o["_ts"] >= since.timestamp()]
        for o in out:
            o.pop("_ts", None)
        return out[:limit]

    def _summary(self, m: dict) -> dict[str, Any]:
        frm = ((m.get("from") or {}).get("emailAddress") or {})
        a = (frm.get("address") or "").lower()
        tos = ", ".join((r.get("emailAddress") or {}).get("address", "") for r in m.get("toRecipients") or [])
        ts = 0.0
        try:
            ts = datetime.fromisoformat(m.get("receivedDateTime", "").replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
        return {"id": m["id"], "thread_id": m.get("conversationId", ""), "from": frm.get("name") or a, "from_email": a,
                "to": tos, "subject": m.get("subject") or "(no subject)", "date": m.get("receivedDateTime", ""),
                "unread": not m.get("isRead", True), "starred": (m.get("flag") or {}).get("flagStatus") == "flagged",
                "snippet": (m.get("bodyPreview") or "")[:220],
                "bulk": m.get("inferenceClassification") == "other" or mime.is_automated(a),
                "has_attachments": bool(m.get("hasAttachments")), "message_id": m.get("internetMessageId", ""), "_ts": ts}

    def raw(self, mid):
        return self._req("GET", f"/messages/{_q(mid)}/$value", raw=True)

    def thread_of(self, mid):
        return self._req("GET", f"/messages/{_q(mid)}", params={"$select": "conversationId"}).get("conversationId", "")

    # ---------------- organising ----------------
    def mark(self, ids, read):
        for i in ids:
            self._req("PATCH", f"/messages/{_q(i)}", json={"isRead": bool(read)})

    def star(self, ids, on):
        for i in ids:
            self._req("PATCH", f"/messages/{_q(i)}", json={"flag": {"flagStatus": "flagged" if on else "notFlagged"}})

    def _move(self, ids, dest):
        for i in ids:
            self._req("POST", f"/messages/{_q(i)}/move", json={"destinationId": dest})

    def archive(self, ids):
        self._move(ids, "archive")

    def trash(self, ids):
        self._move(ids, "deleteditems")

    def move(self, ids, folder):
        self._move(ids, self._folder_id(folder, create=True))

    def folders(self):
        return [x.get("displayName", "") for x in self._all_folders()]

    # ---------------- sending ----------------
    def send(self, msg: EmailMessage, thread_id=None):
        self._req("POST", "/sendMail", content=base64.b64encode(msg.as_bytes()), headers={"Content-Type": "text/plain"})
        return {"message_id": msg["Message-ID"], "thread_id": ""}

    def replies(self, message_id, thread_id, since):
        res = {"from_them": False, "from_me": False}
        conv = thread_id
        if not conv and message_id:
            found = self._req("GET", "/messages", params={"$filter": f"internetMessageId eq '{message_id}'",
                                                          "$select": "conversationId"}).get("value", [])
            conv = found[0]["conversationId"] if found else ""
        if not conv:
            return res
        rows = self._req("GET", "/messages", params={"$filter": f"conversationId eq '{conv}'",
                                                     "$select": "from,receivedDateTime,isDraft", "$top": "50"}).get("value", [])
        for m in rows:
            if m.get("isDraft"):
                continue
            try:
                t = datetime.fromisoformat(m.get("receivedDateTime", "").replace("Z", "+00:00")).timestamp()
            except ValueError:
                continue
            if t <= since.timestamp() + 60:
                continue
            a = (((m.get("from") or {}).get("emailAddress") or {}).get("address") or "").lower()
            if a == self.address:
                res["from_me"] = True
            else:
                res["from_them"] = True
        return res
