"""HOOLA AEP history - chat session memory, the langchain-core `chat_history.py`
idea hand-built (upstream reference: chat_history.py:31 BaseChatMessageHistory,
:223 InMemoryChatMessageHistory).

v0.510.0 HOOLA CORE: the minimal history contract the graph engine (P3) and the
RunnableWithMessageHistory slot (P6/P7) build on. A vault-backed session history
(sqlalchemy, tenant-scoped like the coder store) is the P6 bridge and is named in
the plan - this file ships only the contract + the in-memory default. Inert.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from pydantic import Field

from .messages import BaseMessage
from .serializable import Serializable


class BaseChatMessageHistory(ABC):
    """Store + append messages for one conversation."""

    messages: list[BaseMessage]

    @abstractmethod
    def add_message(self, message: BaseMessage) -> None:
        """Append one message (implies persistence for durable backends)."""

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        for m in messages:
            self.add_message(m)

    @abstractmethod
    def clear(self) -> None: ...


class InMemoryChatMessageHistory(BaseChatMessageHistory):
    """The default process-local history (upstream chat_history.py:223)."""

    def __init__(self, messages: Sequence[BaseMessage] | None = None) -> None:
        self.messages: list[BaseMessage] = list(messages or [])

    def add_message(self, message: BaseMessage) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)


def get_buffer_string(messages: Sequence[BaseMessage]) -> str:
    """The flat Human:/AI: buffer view (upstream utils.get_buffer_string)."""
    lines = []
    for m in messages:
        role = {"human": "Human", "ai": "AI", "system": "System",
                "tool": "Tool", "function": "Function"}.get(m.type, m.type.capitalize())
        lines.append(f"{role}: {m.text}")
    return "\n".join(lines)
