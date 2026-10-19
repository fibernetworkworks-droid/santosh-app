"""Santosh Agent Army: search the catalogue of 36,336 open-source AI agents (see app/bazar/agents.py)."""
from __future__ import annotations

import asyncio

from ..bazar import agents
from .tools import Ctx, ToolError

ARMY_TOOLS = [
    {"name": "agent_army", "description": (
        "Santosh Agent Army: a catalogue of 36,336 open-source AI agents worldwide in 37 fields (coding, voice and "
        "call centre, accounting/tax, legal, healthcare, sales/CRM, marketing/SEO, e-commerce, finance, HR, education, "
        "research, browser/computer-use, DevOps, cybersecurity, data/BI, RAG, agriculture, manufacturing, telecom...). "
        "Use it when the user asks which agent/tool/framework to use for a job, wants options compared, or wants to "
        "build or deploy an agent. action=search (query and/or field, kind 'Agent / app'|'Framework / SDK'|'Plugin / "
        "tool / connector', tier 'A' or 'A,B'); action=details (ref); action=fields (counts and best per field). "
        "Tier A = proven, B = established (real usage signals), C/D = early/unproven: recommend A/B first. The score "
        "is a popularity/recency signal, not a benchmark. These agents are NOT run on Santosh's server; say how each "
        "can be used (how_to_use), and always mention licence_note and caution when present."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["search", "details", "fields"]},
         "query": {"type": "string"}, "field": {"type": "string"}, "kind": {"type": "string"},
         "tier": {"type": "string"}, "ref": {"type": "string"}, "limit": {"type": "integer"}},
         "required": ["action"]}},
]

ARMY_LABELS = {"agent_army": "Agent Army mein dhoondh raha hoon"}


async def agent_army(ctx: Ctx, action, query="", field="", kind="", tier="", ref="", limit=8, **_):
    if action == "search":
        if not (query or field or kind or tier):
            raise ToolError("Give a query or a field")
        res = await asyncio.to_thread(agents.search, str(query), str(field), str(kind), str(tier), int(limit or 8))
        return {"agents": res, "total_in_catalogue": len(agents.agents()),
                "note": "Score = popularity/recency signal, not a benchmark. Recommend Tier A/B; test before production."}
    if action == "details":
        a = await asyncio.to_thread(agents.get, str(ref))
        if a is None:
            raise ToolError("Not found in Agent Army (use action=search first)")
        return a
    if action == "fields":
        st = await asyncio.to_thread(agents.stats)
        return {"total": st["total"], "tiers": st["tiers"], "kinds": st["kinds"], "fields": st["fields"],
                "how_to_read": st["how_to_read"]}
    raise ToolError("action must be search, details or fields")


ARMY_HANDLERS = {"agent_army": agent_army}
