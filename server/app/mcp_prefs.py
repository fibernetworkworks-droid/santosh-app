"""v0.91 Per-tool switches for the MCP servers the owner added (idea from OpenDots' Connections).

For every tool of a server she added:
  * on / off: an "off" tool is never offered to the avatar (chat or call) and a call to it is refused;
  * "pehle poochho" (ask first): the call is frozen and shown on a confirm card, and only her tap runs it.

Defaults (nothing changes until she touches a switch): a tool whose name plainly reads (get / list / search ...) or
that the server marks read-only (MCP `readOnlyHint`) runs by itself, unless its name says it sends, deletes, pays,
shares or publishes; everything else asks first. She can turn "ask first" ON for any tool. She can turn it OFF only for a
tool that is not "locked": a tool whose name sends / deletes / pays / shares / publishes / books / creates or changes
something, or any non-read tool of a server
marked as handling money or code, always keeps its confirm card (the house rule: sending, deleting, sharing, public
changes and money always need her tap). The server's read-only mark is only a hint: it never unlocks such a tool.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

from sqlalchemy import Boolean, DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

LOCK_WORDS = {"send", "delete", "del", "remove", "destroy", "drop", "wipe", "purge", "erase", "trash", "pay", "payment",
              "payout", "transfer", "refund", "charge", "purchase", "buy", "order", "checkout", "book", "booking", "reserve",
              "cancel", "publish", "post", "tweet", "share", "invite", "email", "mail", "message", "sms", "whatsapp", "reply",
              "broadcast", "bulk", "deploy", "merge", "push", "revoke", "grant", "permission", "permissions", "approve",
              "sign", "submit", "withdraw", "transaction", "upi",
              # writes that change her data or something other people see (the "public changes" rule)
              "create", "add", "insert", "update", "edit", "write", "set", "upsert", "modify", "change", "move", "rename",
              "archive", "close", "assign", "comment", "upload", "import", "schedule", "execute", "exec", "run_sql"}


class McpToolPref(Base):
    __tablename__ = "mcp_tool_prefs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    pack_id: Mapped[str] = mapped_column(String(40), index=True)
    tool: Mapped[str] = mapped_column(String(160))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ask: Mapped[bool | None] = mapped_column(Boolean, nullable=True)        # None = Hoola's default
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


# (pack_id, tool) -> the server's readOnlyHint, learned whenever its tool list is fetched (hint only)
HINTS: dict[tuple[str, str], bool] = {}


class PrefError(ValueError):
    pass


def words_of(tool: str) -> set[str]:
    t = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", tool or "").lower()
    return {w for w in re.split(r"[^a-z0-9]+", t) if w}


def locked(tool: str, caution: bool = False) -> bool:
    """Always needs her tap, whatever the switches say. On a money / code server every tool that is not plainly a read."""
    from .bazar.packs.registry import is_read_only
    return bool(words_of(tool) & LOCK_WORDS) or (bool(caution) and not is_read_only(tool))


def default_ask(pack_id: str, tool: str, caution: bool = False) -> bool:
    from .bazar.packs.registry import is_read_only
    if locked(tool, caution):
        return True
    if is_read_only(tool):
        return False
    # the server's read-only mark is trusted only on ordinary servers (money / code servers: names decide)
    return not (HINTS.get((pack_id, tool)) is True and not caution)


def note_hints(pack_id: str, tools: list[dict[str, Any]]) -> None:
    for t in tools:
        if "read_only" in t and t["read_only"] is not None:
            HINTS[(pack_id, t["name"])] = bool(t["read_only"])


def _load(tenant: str, pack_id: str) -> dict[str, tuple[bool, bool | None]]:
    with session() as s:
        rows = s.scalars(select(McpToolPref).where(McpToolPref.tenant_id == tenant, McpToolPref.pack_id == pack_id)).all()
        return {r.tool: (bool(r.enabled), r.ask) for r in rows}


def prefs(tenant: str, pack_id: str) -> dict[str, tuple[bool, bool | None]]:
    return _load(tenant, pack_id)


def enabled(tenant: str, pack_id: str, tool: str) -> bool:
    p = _load(tenant, pack_id).get(tool)
    return True if p is None else p[0]


def needs_tap(tenant: str, pack_id: str, tool: str, caution: bool = False) -> bool:
    if locked(tool, caution):
        return True
    p = _load(tenant, pack_id).get(tool)
    if p is not None and p[1] is not None:
        return bool(p[1])
    return default_ask(pack_id, tool, caution)


def view(tenant: str, pack_id: str, tools: list[dict[str, Any]], caution: bool = False) -> list[dict[str, Any]]:
    mine = _load(tenant, pack_id)
    out = []
    for t in tools:
        name = t["name"]
        en, ask = mine.get(name, (True, None))
        lk = locked(name, caution)
        d_ask = default_ask(pack_id, name, caution)
        out.append({"name": name, "description": (t.get("description") or "")[:300], "enabled": en,
                    "ask": True if lk else (d_ask if ask is None else bool(ask)), "default_ask": d_ask, "locked": lk,
                    "read_hint": HINTS.get((pack_id, name)), "changed": (name in mine)})
    return out


def set_pref(tenant: str, pack_id: str, tool: str, known: list[str], enabled: bool | None = None,
             ask: bool | None = None, caution: bool = False) -> dict[str, Any]:
    if tool not in known:
        raise PrefError("Is server mein yeh tool nahi mila. List dobara kholiye.")
    if ask is False and locked(tool, caution):
        raise PrefError("Yeh tool bhejta / mitata / paise ya share karta hai: iske liye aapka tap hamesha lagega.")
    with session() as s:
        r = s.scalars(select(McpToolPref).where(McpToolPref.tenant_id == tenant, McpToolPref.pack_id == pack_id,
                                                McpToolPref.tool == tool)).first()
        if r is None:
            r = McpToolPref(tenant_id=tenant, pack_id=pack_id, tool=tool, enabled=True, ask=None)
            s.add(r)
        if enabled is not None:
            r.enabled = bool(enabled)
        if ask is not None:
            r.ask = bool(ask)
        r.updated_at = now()
        out = {"tool": tool, "enabled": bool(r.enabled),
               "ask": True if locked(tool, caution) else (default_ask(pack_id, tool, caution) if r.ask is None else bool(r.ask))}
    from .agent import mcp_live
    mcp_live.forget(tenant)              # the avatar's tool list changes on the next turn / call (re)connect
    return out


def reset(tenant: str, pack_id: str) -> int:
    with session() as s:
        rows = s.scalars(select(McpToolPref).where(McpToolPref.tenant_id == tenant, McpToolPref.pack_id == pack_id)).all()
        for r in rows:
            s.delete(r)
        n = len(rows)
    from .agent import mcp_live
    mcp_live.forget(tenant)
    return n
