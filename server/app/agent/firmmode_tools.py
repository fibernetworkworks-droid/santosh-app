"""Firm mode (F7 of docs/FINANCE_GLOBAL_PLAN.md) tool: `firm_practice`. An accounting, tax or advisory firm runs its clients in one
account: client books, the client switcher, engagement letters, paper requests, the client portal, drafts that a reviewer approves
and the named signer signs, the review queue, the firm dashboard, each client's audit trail, and the adviser / practice parts
(fact-find, meeting notes, suitability draft, rebalancing drift, a fractional-CFO pack). Every action is done as a named person of the
firm and each person sees only the clients they may see; a client sees only their own book. It never files, sends or pays."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["person_add", "client_add", "clients", "engagement", "request", "provide", "portal", "draft", "edit", "review", "sign",
            "share", "queue", "dashboard", "audit", "factfind", "meeting", "suitability", "drift", "cfo_pack"]

FIRMMODE_TOOLS = [
    {"name": "firm_practice", "description": (
        "Firm mode for accounting / tax / advisory firms (firm = the firm's workspace, size firm). Every action needs person = the "
        "firm person doing it; access is checked per client. person_add: name, role partner|manager|preparer|reviewer|client, clients "
        "(staff: list or all; client: [their one book]) - the first person is a partner, then only a partner adds people. client_add: "
        "name, size personal|solo|business, countries, currency. clients: the switcher for this person. engagement: client, services, "
        "fee, period, terms, signer. request: client, items, due. provide (a client sends a paper): request, item. portal: the client's "
        "own page. draft: client, kind tax_return|accounts|letter|engagement|suitability|plan|memo|cfo_pack|other, title, body, signer "
        "(a partner / manager). edit: draft, body (an approved draft goes back to review). review: draft, verdict approve|send_back, "
        "notes, hash (never by its preparer). sign: draft (only the named signer, only the approved text). share: draft (signed, to "
        "the portal). queue, dashboard, audit: client. factfind: client, answers. meeting: client, text. suitability: client, "
        "recommendation (the adviser's own), parts, signer. drift: holdings, targets, tolerance_pct. cfo_pack: client, since, upto."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "firm": {"type": "string"}, "person": {"type": "string"},
         "name": {"type": "string"}, "role": {"type": "string"}, "clients": {}, "client": {"type": "string"}, "size": {"type": "string"},
         "countries": {"type": "array", "items": {"type": "string"}}, "currency": {"type": "string"},
         "services": {"type": "array", "items": {"type": "string"}}, "fee": {"type": "string"}, "period": {"type": "string"},
         "terms": {"type": "string"}, "client_name": {"type": "string"}, "client_duties": {"type": "string"},
         "items": {"type": "array", "items": {"type": "string"}}, "due": {"type": "string"}, "request": {"type": "string"},
         "item": {"type": "string"}, "kind": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"},
         "signer": {"type": "string"}, "draft": {"type": "string"}, "verdict": {"type": "string"}, "notes": {"type": "string"},
         "hash": {"type": "string"}, "answers": {"type": "object"}, "text": {"type": "string"}, "recommendation": {"type": "string"},
         "parts": {"type": "object"}, "holdings": {"type": "array", "items": {"type": "object"}}, "targets": {"type": "object"},
         "tolerance_pct": {"type": "number"}, "since": {"type": "string"}, "upto": {"type": "string"}, "today": {"type": "string"}},
         "required": ["action"]}},
]
FIRMMODE_LABELS = {"firm_practice": "Working on the firm's clients"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import firm as FM
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "firm_practice", action, a, lambda: FM.run(tenant, action, a, actor))


async def _firm_practice(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This work is for the firm's people; a client uses the portal.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    try:
        return await asyncio.to_thread(_work, ctx, action, a)
    except PermissionError as e:
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


FIRMMODE_HANDLERS = {"firm_practice": _firm_practice}
