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
            "drafts": "in:drafts", "snoozed": "in:snoozed",
            "archive": "-in:inbox -in:sent -in:drafts -in:trash -in:spam -in:chats"}
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
        q = []
        if f == "search":                      # v0.184.0 a saved search's raw query: no folder operator on top
            pass
        else:
            op = FOLDER_Q.get(f)
            q.append(op if op else f'label:"{folder}"')
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
        return ["inbox", "sent", "archive", "starred", "snoozed", "spam", "trash"] + \
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

    # ---------------- v0.181.0 threads: the whole conversation ----------------
    def thread(self, mid: str, max_messages: int = 30, body_chars: int = 3000) -> dict[str, Any]:
        t = self._req("GET", f"/threads/{mid}",
                      params=[("format", "metadata")] + [("metadataHeaders", h) for h in META])
        msgs: list[dict[str, Any]] = []
        for m in (t.get("messages") or [])[:max_messages]:
            try:
                p = mime.parse(self.raw(m["id"]))
            except MailError:
                continue                       # a message that vanished (deleted/spam purge) never breaks the thread
            p["id"] = m["id"]
            p["thread_id"] = m.get("threadId") or t.get("id", "")
            if len(p.get("body", "")) > body_chars:
                p["body"] = p["body"][:body_chars]
                p["truncated"] = True
            msgs.append(p)
        return {"thread_id": t.get("id", ""), "count": len(msgs), "messages": msgs}

    # ---------------- v0.181.0 drafts inside Gmail itself ----------------
    def save_draft(self, msg: EmailMessage, thread_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"message": {"raw": b64url(msg.as_bytes())}}
        if thread_id:
            body["message"]["threadId"] = thread_id
        out = self._req("POST", "/drafts", json=body)
        m = out.get("message") or {}
        return {"draft_id": out.get("id", ""), "message_id": m.get("id", ""),
                "thread_id": m.get("threadId") or thread_id or ""}

    def drafts_list(self, limit: int = 10) -> list[dict[str, Any]]:
        ids = [d["id"] for d in self._req("GET", "/drafts", params={"maxResults": max(1, min(int(limit or 10), 25))}).get("drafts", [])]
        out = []
        for did in ids:
            d = self._req("GET", f"/drafts/{did}", params=[("format", "metadata")] + [("metadataHeaders", h) for h in META])
            s = self._summary(d.get("message") or {})
            s["draft_id"] = did
            out.append(s)
        return out

    def draft_delete(self, draft_id: str) -> None:
        self._req("DELETE", f"/drafts/{draft_id}")

    # ---------------- v0.181.0 labels: full management ----------------
    def label_create(self, name: str) -> dict[str, Any]:
        return self._req("POST", "/labels", json={"name": (name or "").strip()[:60], "labelListVisibility": "labelShow",
                                                  "messageListVisibility": "show"})

    def label_rename(self, name: str, new_name: str) -> None:
        lid = self._label_id(name)
        self._req("PATCH", f"/labels/{lid}", json={"name": (new_name or "").strip()[:60]})

    def label_delete(self, name: str) -> None:
        lid = self._label_id(name)
        self._req("DELETE", f"/labels/{lid}")

    # ---------------- v0.184.0 labels with colours + nesting ----------------
    def labels_full(self) -> list[dict[str, Any]]:
        """Raw label rows (id, name, type, color) — the tree display and the colour picker read this."""
        return self._labels()

    def label_color(self, name: str, background: str, text: str) -> dict[str, Any]:
        lid = self._label_id(name)
        return self._req("PATCH", f"/labels/{lid}",
                         json={"color": {"backgroundColor": background, "textColor": text}})

    # ---------------- v0.181.0 importance + category tabs ----------------
    CATEGORIES = {"personal": "CATEGORY_PERSONAL", "social": "CATEGORY_SOCIAL", "updates": "CATEGORY_UPDATES",
                  "forums": "CATEGORY_FORUMS", "promotions": "CATEGORY_PROMOTIONS"}

    def mark_important(self, ids: list[str], on: bool) -> None:
        self._modify(ids, add=["IMPORTANT"]) if on else self._modify(ids, remove=["IMPORTANT"])

    def set_category(self, ids: list[str], category: str) -> None:
        cat = self.CATEGORIES.get((category or "").strip().lower())
        if not cat:
            raise MailError("category personal / social / updates / forums / promotions mein se hai")
        self._modify(ids, add=[cat], remove=[c for c in self.CATEGORIES.values() if c != cat])

    def apply_label(self, ids: list[str], name: str) -> None:
        """v0.182.0 a label on top of the mail, inbox nahi chhodti (a rule's 'label' action)."""
        self._modify(ids, add=[self._label_id(name, create=True)])

    # ---------------- v0.182.0 the new-mail watcher: history.list with a stored watermark ----------------
    def profile(self) -> dict[str, Any]:
        """The mailbox's own view: historyId (the watcher's watermark), address, messages count."""
        return self._req("GET", "/profile")

    def history(self, start_history_id: str, types: str = "messageAdded", max_results: int = 100) -> dict[str, Any]:
        """Everything that changed since the watermark (new mail). A 404 here means the watermark expired
        (history purged) — the sync engine falls back to a plain `after:` listing, nothing is ever lost."""
        return self._req("GET", "/history", params={"startHistoryId": start_history_id, "historyTypes": types,
                                                    "maxResults": max(1, min(int(max_results), 500))})

    # ---------------- v0.183.0 settings: vacation reply, sendAs (signature / aliases), auto-forward ----------------
    # These need the gmail.settings.basic scope (one-time reconnect for mailboxes linked before v0.183.0).
    def vacation_get(self) -> dict[str, Any]:
        return self._req("GET", "/settings/vacation")

    def vacation_set(self, enable: bool, message: str = "", subject: str = "", start_ms: int = 0, end_ms: int = 0,
                     restrict_to_contacts: bool = False) -> dict[str, Any]:
        body = {"enableAutoReply": bool(enable), "responseBody": (message or "")[:10000],
                "responseSubject": (subject or "")[:500], "restrictToContacts": bool(restrict_to_contacts),
                "restrictToDomain": False, "startTime": str(max(0, int(start_ms or 0))),
                "endTime": str(max(0, int(end_ms or 0)))}
        return self._req("PUT", "/settings/vacation", json=body)

    def send_as_list(self) -> list[dict[str, Any]]:
        return self._req("GET", "/settings/sendAs").get("sendAs", [])

    def send_as_signature(self, send_as_email: str, signature_html: str) -> dict[str, Any]:
        """Gmail's signature field is HTML; we push escaped text with <br> line breaks."""
        return self._req("PATCH", f"/settings/sendAs/{send_as_email}", json={"signature": (signature_html or "")[:2000]})

    def auto_forwarding_get(self) -> dict[str, Any]:
        return self._req("GET", "/settings/autoForwarding")

    def auto_forwarding_set(self, enabled: bool, email_address: str, disposition: str = "keep") -> dict[str, Any]:
        return self._req("PUT", "/settings/autoForwarding",
                         json={"enabled": bool(enabled), "emailAddress": (email_address or "").strip().lower(),
                               "disposition": disposition})

    # ---------------- v0.186.0 the remaining surface: filters, forwarding addresses, alias add/remove,
    # IMAP / POP / language, drafts read-edit-send, threads as a unit, delete forever ----------------
    def filters_list(self) -> list[dict[str, Any]]:
        return self._req("GET", "/settings/filters").get("filter", [])

    def filter_create(self, criteria: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
        return self._req("POST", "/settings/filters", json={"criteria": criteria, "action": action})

    def filter_delete(self, filter_id: str) -> None:
        self._req("DELETE", f"/settings/filters/{filter_id}")

    def forwarding_list(self) -> list[dict[str, Any]]:
        return self._req("GET", "/settings/forwardingAddresses").get("forwardingAddresses", [])

    def forwarding_create(self, email: str) -> dict[str, Any]:
        return self._req("POST", "/settings/forwardingAddresses",
                         json={"forwardingEmail": (email or "").strip().lower()})

    def forwarding_delete(self, email: str) -> None:
        self._req("DELETE", f"/settings/forwardingAddresses/{(email or '').strip().lower()}")

    def send_as_create(self, email: str, name: str = "", reply_to: str = "") -> dict[str, Any]:
        body: dict[str, Any] = {"sendAsEmail": (email or "").strip().lower()}
        if name.strip():
            body["displayName"] = name.strip()[:100]
        if reply_to.strip():
            body["replyToAddress"] = reply_to.strip()
        return self._req("POST", "/settings/sendAs", json=body)

    def send_as_delete(self, email: str) -> None:
        self._req("DELETE", f"/settings/sendAs/{(email or '').strip().lower()}")

    def imap_get(self) -> dict[str, Any]:
        return self._req("GET", "/settings/imap")

    def imap_set(self, enabled: bool, auto_expunge: bool = True, expunge_behavior: str = "archive",
                 max_folder_size: int = 0) -> dict[str, Any]:
        return self._req("PUT", "/settings/imap",
                         json={"enabled": bool(enabled), "autoExpunge": bool(auto_expunge),
                               "expungeBehavior": expunge_behavior, "maxFolderSize": int(max_folder_size)})

    def pop_get(self) -> dict[str, Any]:
        return self._req("GET", "/settings/pop")

    def pop_set(self, access_window: str, disposition: str = "leaveInInbox") -> dict[str, Any]:
        return self._req("PUT", "/settings/pop", json={"accessWindow": access_window, "disposition": disposition})

    def language_get(self) -> dict[str, Any]:
        return self._req("GET", "/settings/language")

    def language_set(self, display_language: str) -> dict[str, Any]:
        return self._req("PUT", "/settings/language", json={"displayLanguage": (display_language or "").strip()})

    def draft_get(self, draft_id: str) -> dict[str, Any]:
        return self._req("GET", f"/drafts/{draft_id}")

    def draft_raw(self, draft_id: str) -> tuple[bytes, str]:
        """The draft's raw MIME + its thread id — the edit path rebuilds from this, attachments included."""
        m = (self._req("GET", f"/drafts/{draft_id}").get("message") or {})
        return unb64url(m.get("raw", "")), m.get("threadId", "")

    def draft_update(self, draft_id: str, msg: EmailMessage, thread_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"message": {"raw": b64url(msg.as_bytes())}}
        if thread_id:
            body["message"]["threadId"] = thread_id
        out = self._req("PUT", f"/drafts/{draft_id}", json=body)
        m = out.get("message") or {}
        return {"draft_id": out.get("id", draft_id), "message_id": m.get("id", ""),
                "thread_id": m.get("threadId") or thread_id or ""}

    def draft_send(self, draft_id: str) -> dict[str, Any]:
        out = self._req("POST", "/drafts/send", json={"id": draft_id})
        return {"id": out.get("id", ""), "thread_id": out.get("threadId", ""), "message_id": out.get("id", "")}

    def threads_list(self, query: str = "in:inbox", limit: int = 10) -> list[dict[str, Any]]:
        ids = self._req("GET", "/threads", params={"q": query or "in:inbox",
                                                   "maxResults": max(1, min(int(limit or 10), 25))}).get("threads", [])
        out = []
        for t in ids:
            tid = t.get("id", "")
            if not tid:
                continue
            one = self._req("GET", f"/threads/{tid}",
                            params=[("format", "metadata")] + [("metadataHeaders", h) for h in ("From", "Subject", "Date")])
            msgs = one.get("messages") or []
            if not msgs:
                continue
            first = msgs[0]
            last = msgs[-1]
            hdrs = lambda m: {h["name"].lower(): h["value"] for h in (m.get("payload") or {}).get("headers", [])}
            lf, ll = hdrs(first), hdrs(last)
            label_ids = last.get("labelIds") or []
            out.append({"thread_id": tid, "count": len(msgs),
                        "subject": mime.dec(ll.get("subject")) or mime.dec(lf.get("subject")) or "(no subject)",
                        "from": mime.addr(lf.get("from"))[0] or mime.addr(lf.get("from"))[1],
                        "from_email": mime.addr(lf.get("from"))[1],
                        "last_from": mime.addr(ll.get("from"))[1],
                        "date": ll.get("date", lf.get("date", "")),
                        "snippet": html.unescape(last.get("snippet", "")),
                        "unread": "UNREAD" in label_ids, "starred": "STARRED" in label_ids,
                        "labels": [l for l in label_ids if l in ("INBOX", "SENT", "TRASH", "SPAM")]})
        return out

    def thread_modify(self, thread_id: str, add=(), remove=()) -> None:
        self._req("POST", f"/threads/{thread_id}/modify",
                  json={"addLabelIds": list(add), "removeLabelIds": list(remove)})

    def thread_trash(self, thread_id: str) -> None:
        self._req("POST", f"/threads/{thread_id}/trash")

    def message_delete(self, mid: str) -> None:
        """DELETE /messages/{id} — permanently, Trash bhi nahi (the card says this in plain words)."""
        self._req("DELETE", f"/messages/{mid}")
