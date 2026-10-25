"""What every mailbox (Gmail API, Outlook/Microsoft Graph, IMAP/SMTP) can do for Santosh.

Methods are blocking; callers run them in a thread. Message ids are the provider's own; the service layer prefixes
them with the account key so one Santosh can hold several mailboxes.
"""
from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from typing import Any

FOLDERS = ("inbox", "sent", "archive", "trash", "spam", "starred", "drafts")


class MailError(Exception):
    pass


class NotConnected(MailError):
    pass


class Box:
    kind = "base"

    def __init__(self, key: str, address: str, name: str = "", signature: str = "") -> None:
        self.key = key
        self.address = (address or "").lower()
        self.name = name or ""
        self.signature = signature or ""

    # summaries: {id, thread_id, from, from_email, to, subject, date, unread, snippet, bulk, has_attachments, folder}
    def list(self, folder: str = "inbox", unread_only: bool = False, search: str | None = None, limit: int = 10,
             since: datetime | None = None, snippets: bool = False) -> list[dict[str, Any]]:
        raise NotImplementedError

    def raw(self, mid: str) -> bytes:
        raise NotImplementedError

    def thread_of(self, mid: str) -> str:
        return ""

    def mark(self, ids: list[str], read: bool) -> None:
        raise NotImplementedError

    def star(self, ids: list[str], on: bool) -> None:
        raise NotImplementedError

    def archive(self, ids: list[str]) -> None:
        raise NotImplementedError

    def trash(self, ids: list[str]) -> None:
        raise NotImplementedError

    def move(self, ids: list[str], folder: str) -> None:
        raise NotImplementedError

    def folders(self) -> list[str]:
        return list(FOLDERS)

    def send(self, msg: EmailMessage, thread_id: str | None = None) -> dict[str, Any]:
        """Returns {"message_id": <RFC Message-ID>, "thread_id": <provider thread id or "">}."""
        raise NotImplementedError

    def replies(self, message_id: str, thread_id: str, since: datetime) -> dict[str, bool]:
        """Has anyone answered this mail since `since`? {"from_them": bool, "from_me": bool}."""
        raise NotImplementedError

    # ---------------- v0.181.0: richer abilities, Gmail-first, clean "nahi hota" elsewhere ----------------
    def thread(self, mid: str) -> dict[str, Any]:
        raise MailError("Poora conversation (thread view) abhi Gmail mailbox par khulta hai; "
                        "is mailbox par mail ek ek karke kholta hoon.")

    def save_draft(self, msg: EmailMessage, thread_id: str | None = None) -> dict[str, Any]:
        raise MailError("Draft is mailbox ke apne Drafts folder mein save nahi hota (abhi Gmail par). "
                        "Hoola ka draft bana rahega; wahi se Bhejo hoga.")

    def drafts_list(self, limit: int = 10) -> list[dict[str, Any]]:
        raise MailError("Mailbox ke apne drafts abhi Gmail par dikhte hain.")

    def draft_delete(self, draft_id: str) -> None:
        raise MailError("Mailbox ke apne drafts abhi Gmail par delete hote hain.")

    def label_create(self, name: str) -> dict[str, Any]:
        raise MailError("Labels ka poora management abhi Gmail mailbox par hai (move se label banti hai).")

    def label_rename(self, name: str, new_name: str) -> None:
        raise MailError("Labels ka poora management abhi Gmail mailbox par hai.")

    def label_delete(self, name: str) -> None:
        raise MailError("Labels ka poora management abhi Gmail mailbox par hai.")

    def mark_important(self, ids: list[str], on: bool) -> None:
        raise MailError("Important mark abhi Gmail mailbox par hota hai.")

    def set_category(self, ids: list[str], category: str) -> None:
        raise MailError("Category tabs (Social / Promotions...) abhi Gmail mailbox par hain.")

    def apply_label(self, ids: list[str], name: str) -> None:
        raise MailError("Label lagana bina inbox se hataye abhi Gmail mailbox par hota hai.")

    def profile(self) -> dict[str, Any]:
        raise MailError("Yeh mailbox watcher ke liye history nahi deta; purani mail dekhne ke liye email_check hai.")

    def history(self, start_history_id: str, types: str = "messageAdded", max_results: int = 100) -> dict[str, Any]:
        raise MailError("Yeh mailbox watcher ke liye history nahi deta.")

    # ---------------- v0.183.0 Gmail settings: vacation / sendAs / auto-forward ----------------
    def vacation_get(self) -> dict[str, Any]:
        raise MailError("Vacation reply (out of office) abhi Gmail mailbox par hota hai.")

    def vacation_set(self, enable: bool, message: str = "", subject: str = "", start_ms: int = 0, end_ms: int = 0,
                     restrict_to_contacts: bool = False) -> dict[str, Any]:
        raise MailError("Vacation reply (out of office) abhi Gmail mailbox par hota hai.")

    def send_as_list(self) -> list[dict[str, Any]]:
        raise MailError("Send-as aliases abhi Gmail mailbox par dikhte hain.")

    def send_as_signature(self, send_as_email: str, signature_html: str) -> dict[str, Any]:
        raise MailError("Signature ko Gmail ke andar badalna abhi Gmail mailbox par hota hai.")

    def auto_forwarding_get(self) -> dict[str, Any]:
        raise MailError("Auto-forward abhi Gmail ki apni setting hai.")

    def auto_forwarding_set(self, enabled: bool, email_address: str, disposition: str = "keep") -> dict[str, Any]:
        raise MailError("Auto-forward abhi Gmail ki apni setting hai.")

    def view(self) -> dict[str, Any]:
        return {"key": self.key, "kind": self.kind, "address": self.address, "name": self.name,
                "signature": self.signature}
