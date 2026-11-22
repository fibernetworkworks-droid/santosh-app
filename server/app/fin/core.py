"""How a finance tool runs on the core (F0): the laws first, then the work, then one audit row. The work itself is unchanged - the old
tools hand their own function in, so their results are byte for byte what they were."""
from __future__ import annotations

from typing import Any, Callable

from . import evidence as EV
from . import laws as L


def run_tool(tenant: str, actor: str, tool: str, action: str, args: dict[str, Any], work: Callable[[], Any]) -> Any:
    try:
        L.screen(tool, action, args)
    except L.Refused as e:
        EV.record(tenant, "", actor, "refused", f"{tool}.{action}: {e.key}", {"action": action})
        raise
    out = work()
    EV.record(tenant, "", actor, "tool", f"{tool}.{action}", {"args": args})
    return out
