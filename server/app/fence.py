"""v0.246 FULL CLAUDE MODE Phase 3C: FENCED SESSIONS - Claude's project memory.

A console "Session" is a project (`Conversation.project_id`). Like Claude's projects, what Hoola picks up inside one
Session stays inside it: a chat in Session "Client X" never recalls Client Y's work, and a general chat (no Session)
never recalls either. Scope of a chat = its project_id, "" for a general chat.

FENCED (per scope):
- facts Hoola picked up BY ITSELF (`MemoryFact.conversation_id` set, source auto) -> only chats of the same scope;
- the work diary (`TaskRun.conversation_id`, website jobs, call receipts) and the running-jobs block (KaamJob);
- puri yaad search (`yaad.search` items + raw words) and the facts recalled by meaning.
GLOBAL (about HER, every scope): facts she asked to remember ("yaad rakhna", `remember` tool - no conversation), pinned
facts, rows from before v0.246 (no conversation recorded), her profile. The owner's decision: "RECOMMENDED".

Everything is decided at READ time from the chat a row came from, so a chat moved into / out of a Session takes its
memory with it. MEMORY_FENCE=false turns the fence off (the v0.245 behaviour, every chat sees everything).
"""
from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy import or_, select

from .db import Conversation, session

log = logging.getLogger("santosh.fence")

STATS: dict[str, int] = {"scoped": 0, "hidden": 0}


def enabled() -> bool:
    from .config import get_settings
    return bool(getattr(get_settings(), "memory_fence", True))


def scope_of(conversation_id: str) -> str | None:
    """The chat's Session id ('' = general chat); None = unknown chat (no fence can be drawn)."""
    if not conversation_id:
        return None
    try:
        with session() as s:
            c = s.get(Conversation, conversation_id)
            return None if c is None else (c.project_id or "")
    except Exception:
        log.exception("fence scope read failed")
        return None


def is_incognito(conversation_id: str) -> bool:
    """v0.250 an incognito chat: Hoola reads her memory there but writes nothing from it."""
    if not conversation_id:
        return False
    try:
        with session() as s:
            c = s.get(Conversation, conversation_id)
            return bool(c is not None and c.incognito)
    except Exception:
        log.exception("incognito read failed")
        return False


def incognito_ids(tenant: str) -> set[str]:
    """Her incognito chats: never a source of memory for any other chat (v0.250)."""
    with session() as s:
        return set(s.scalars(select(Conversation.id).where(Conversation.tenant_id == tenant,
                                                           Conversation.incognito.is_(True))).all())


def prefs(tenant: str) -> dict[str, bool]:
    """v0.250 her memory switches: auto = Hoola picks up facts / writes her page by itself; recall = Hoola uses her
    past chats (search, recent chats, her page). Both on unless she turned them off (Profile > Hoola ki yaad)."""
    try:
        from .db import Profile
        with session() as s:
            p = s.get(Profile, tenant)
            return {"auto": not (p is not None and p.memory_auto is False),
                    "recall": not (p is not None and p.memory_recall is False)}
    except Exception:
        return {"auto": True, "recall": True}


def chats_in(tenant: str, conversation_id: str) -> set[str] | None:
    """Every chat of hers in the SAME scope as this one (itself included). None = no fence (off / unknown chat):
    callers then see everything, exactly as before v0.246."""
    if not enabled():
        return None
    scope = scope_of(conversation_id)
    if scope is None:
        return None
    with session() as s:
        q = select(Conversation.id).where(Conversation.tenant_id == tenant,
                                          or_(Conversation.incognito.is_(None), Conversation.incognito.is_(False)))
        q = q.where(Conversation.project_id == scope) if scope else \
            q.where(or_(Conversation.project_id.is_(None), Conversation.project_id == ""))
        out = set(s.scalars(q).all())   # v0.250 incognito chats are never a source
    out.add(conversation_id)
    STATS["scoped"] += 1
    return out


def visible(row_conversation: str | None, allowed: set[str] | None) -> bool:
    """A memory row may be shown in this chat: no fence, or a row with no chat (global: hers, or older than
    v0.246), or a row from a chat of the same scope."""
    if allowed is None or not row_conversation:
        return True
    ok = row_conversation in allowed
    if not ok:
        STATS["hidden"] += 1
    return ok


def keep(rows: Iterable, allowed: set[str] | None, attr: str = "conversation_id") -> list:
    """The rows this chat may see (attribute or dict key `attr` = the chat each row came from)."""
    out = []
    for r in rows:
        conv = r.get(attr) if isinstance(r, dict) else getattr(r, attr, None)
        if visible(conv, allowed):
            out.append(r)
    return out
