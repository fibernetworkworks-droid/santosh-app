"""Maps packs to executors and gives every pack tool a unique, Claude-safe name."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..connectors.base import Ctx, Executor, ToolError, ToolSpec
from ..connectors.bbps import BBPSExecutor
from ..connectors.mcp_remote import McpExecutor
from ..connectors.pc import PcExecutor
from ..connectors.browser import BrowserExecutor
from ..connectors.calendar import CalendarExecutor
from ..connectors.mail import MailExecutor
from ..connectors.pcop import PcOpExecutor
from ..connectors.commerce import CommerceExecutor
from ..connectors.device import DeviceExecutor
from ..connectors.handoff import HandoffExecutor
from ..connectors.native2 import Native2Executor
from ..connectors.reader import ReaderExecutor
from ..connectors.rides import RideExecutor
from ..connectors.shops import ShopExecutor
from ..connectors.upi import UpiExecutor
from ..packs.registry import Pack


def default_executors() -> dict[str, Executor]:
    return {"mcp": McpExecutor(), "bbps": BBPSExecutor(), "upi": UpiExecutor(), "ride": RideExecutor(),
            "shop": ShopExecutor(), "native": Native2Executor(), "pc": PcExecutor(),
            "handoff": HandoffExecutor(), "reader": ReaderExecutor(), "device": DeviceExecutor(), "commerce": CommerceExecutor(), "browser": BrowserExecutor(), "pcop": PcOpExecutor(), "mail": MailExecutor(), "cal": CalendarExecutor()}


@dataclass
class BoundTool:
    api_name: str
    pack: Pack
    spec: ToolSpec


def api_name(pack: Pack, tool: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-zA-Z0-9_-]", "_", f"{pack.id[:34]}__{tool[:26]}")[:62]
    name, i = base, 2
    while name in taken:
        name = f"{base[:59]}_{i}"
        i += 1
    taken.add(name)
    return name


def bind_tools(packs: list[Pack], executors: dict[str, Executor], ctx: Ctx) -> tuple[dict[str, BoundTool], list[str]]:
    """Returns tools by API name plus a list of human notes for packs that could not load (e.g. account not linked)."""
    out: dict[str, BoundTool] = {}
    notes: list[str] = []
    taken: set[str] = set()
    for p in packs:
        try:
            specs = executors[p.executor].tool_specs(p, ctx)
        except ToolError as e:
            notes.append(f"{p.name}: {e}")
            continue
        except Exception as e:  # provider down
            notes.append(f"{p.name}: unavailable right now ({type(e).__name__})")
            continue
        for s in specs:
            n = api_name(p, s.name, taken)
            out[n] = BoundTool(n, p, s)
    return out, notes


def claude_tool_defs(tools: dict[str, BoundTool]) -> list[dict[str, Any]]:
    defs = []
    for t in tools.values():
        schema = t.spec.input_schema or {"type": "object", "properties": {}}
        if schema.get("type") != "object":
            schema = {"type": "object", "properties": {}}
        tier_note = {0: "", 1: "", 2: " Needs the user's tap to approve.", 3: " Needs approval and the user's UPI PIN."}[t.spec.tier]
        defs.append({"name": t.api_name, "description": (t.spec.description + tier_note)[:1024], "input_schema": schema})
    return defs
