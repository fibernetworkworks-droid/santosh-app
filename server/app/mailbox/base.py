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

    def view(self) -> dict[str, Any]:
        return {"key": self.key, "kind": self.kind, "address": self.address, "name": self.name,
                "signature": self.signature}
