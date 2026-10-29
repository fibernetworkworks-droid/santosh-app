"""v0.245 SAHI AUZAAR - the last check on Hoola's pick, in code, before a tool runs.

The router (agent/admit.py) decides what Hoola SEES; this decides what may RUN when the pick is plainly wrong.
Only two cases, both from real failures, and each refusal names the right tool so the next step is the right one:

1. A PC tool (her PC / Hoola's cloud PC) that was not in view this turn: she named no PC and the job needs no desktop
   software. The GLM brain could call any known handler from the guide text; that is how jobs drifted to the cloud PC.
   If she really meant a PC, tool_search opens the family and the call goes through.
2. A data job (lists, top N, API / repos, collecting) sent to a PC she did not name: data stays on the server
   (data_fetch -> data_read / data_note -> doc_studio data=) and its file reaches the chat; a VM file does not.
"""
from __future__ import annotations

from typing import Any

from .tools import FAMILY_OF, ToolError

STATS = {"checked": 0, "pc_not_in_view": 0, "data_to_pc": 0}

_PC_TOOLS = frozenset(n for n, f in FAMILY_OF.items() if f == "pc")
_DATA_WAY = ("data_fetch (keeps only the fields you need, saves a dataset on the server) -> data_read / data_note in "
             "batches -> doc_studio data=<id> for the PDF / Excel")


def check(name: str, args: dict[str, Any], ctx) -> None:
    """Raise ToolError with the right tool when the pick is plainly wrong; return quietly otherwise."""
    if name not in _PC_TOOLS:
        return
    STATS["checked"] += 1
    from . import admit, where
    adm = getattr(ctx, "admit", None)
    place = getattr(ctx, "place", "") or ""
    conv = getattr(ctx, "conversation_id", "") or ""
    named = place in ("pc", "hoolapc") or where._asked(conv, "pc") or where._asked(conv, "hoolapc") or \
        where.working(conv) in ("pc", "hoolapc")
    if adm is not None and "pc" not in adm.families and not named:
        STATS["pc_not_in_view"] += 1
        raise ToolError(f"{name} was not offered for this ask: she named no PC and the job needs no desktop software. "
                        "Use the server tools in view (documents: doc_studio; lists / API data: " + _DATA_WAY +
                        "; web pages: google_search / open_website / browse_web; website forms: computer_operator). "
                        "If she really wants a PC, call tool_search with 'pc' first.")
    if name in ("hoola_pc_do", "pc_do"):
        task = str((args or {}).get("task") or "")
        if where._DATA.search(task) and not admit._DESKTOP.search(task) and not named:
            STATS["data_to_pc"] += 1
            raise ToolError("This is a DATA job and she did not ask for a PC: do it on the server - " + _DATA_WAY +
                            ". A file made on a PC does not come back to the chat.")
