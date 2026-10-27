"""Shared types for every executor (connector)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from ..config import Settings
from ..db import Task, User
from ..packs.registry import Pack


class ToolError(Exception):
    """A tool could not complete; message is safe to show the user."""


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    tier: int


@dataclass
class NeedsApproval:
    """Returned by a tool that would move money or act for the user.

    The action stored here is what runs after approval. Its amount, payee and items were computed by
    server code, so model text can never change them.
    """
    tier: int
    title: str
    payee: str
    amount_paise: int
    items: list[dict[str, Any]]
    pay_method: str
    action: dict[str, Any]           # {"executor", "pack_id", "name", "args"}
    preview: dict[str, Any] = field(default_factory=dict)


@dataclass
class Ctx:
    session: Session
    user: User
    task: Task | None
    settings: Settings


class Executor(Protocol):
    name: str

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]: ...

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval: ...

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]: ...


def rupees(paise: int) -> str:
    r, p = divmod(int(paise), 100)
    s = f"{r:,}"
    # Indian grouping: 1,23,456
    if r >= 1000:
        head, tail = str(r)[:-3], str(r)[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return f"₹{s}" + (f".{p:02d}" if p else "")


def to_paise(amount: Any) -> int:
    """Accept 120, "120", "₹1,240.50" and return paise."""
    if isinstance(amount, (int, float)):
        return int(round(float(amount) * 100))
    s = str(amount).replace("₹", "").replace(",", "").replace("rs", "").replace("Rs", "").strip()
    if not s:
        raise ToolError("Amount missing")
    try:
        return int(round(float(s) * 100))
    except ValueError as e:
        raise ToolError(f"Not a valid amount: {amount}") from e
