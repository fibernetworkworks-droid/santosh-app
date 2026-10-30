"""v0.245 SAHI AUZAAR - the last check on Hoola's pick, in code, before a tool runs.

The router (agent/admit.py) decides what Hoola SEES; this decides what may RUN when the pick is plainly wrong.
Three cases, all from real failures, and each refusal names the right tool so the next step is the right one:

1. A PC tool (her PC / Hoola's cloud PC) that was not in view this turn: she named no PC and the job needs no desktop
   software. The GLM brain could call any known handler from the guide text; that is how jobs drifted to the cloud PC.
   If she really meant a PC, tool_search opens the family and the call goes through.
2. A data job (lists, top N, API / repos, collecting) sent to a PC she did not name: data stays on the server
   (data_fetch -> data_read / data_note -> doc_studio data=) and its file reaches the chat; a VM file does not.
4. (v0.270) Any other PC job she did not place on a PC (no PC named this turn, no running PC job in the chat, no
   desktop software): deep research + PDF went to her PC / the cloud PC; it belongs to the server tools.
3. (v0.257) Reading / analysing a program or app file (.exe / .apk / .dll, endpoints, decompiling) sent to a PC
   without her saying so in THIS ask: that is rea_khoj (action=endpoints / overview), on the server, never run.
"""
from __future__ import annotations

from typing import Any

from .tools import FAMILY_OF, ToolError

STATS = {"checked": 0, "pc_not_in_view": 0, "data_to_pc": 0, "file_to_pc": 0, "pc_not_hers": 0}
# v0.270 desktop apps that only exist on a computer (a job in one of them may go to a PC without the word "PC")
_DESKTOP_APPS = __import__("re").compile(r"\b(?:excel|ms word|word mein|word file|powerpoint|outlook|notepad|tally|"
                                         r"busy|marg|photoshop|corel|autocad|vlc|file explorer|desktop app|"
                                         r"control panel)\b", __import__("re").I)

_PC_TOOLS = frozenset(n for n, f in FAMILY_OF.items() if f == "pc")
# v0.257 reading a program / app file (owner: "READ THIS EXE FILE END TO END AND EXTRACT ENDPOINTS ... HOOLA OPENS ITS OWN
# PC INSTEAD OF USING REA"): the server reads it statically - rea_khoj - and the file is never run anywhere
def _appfile():
    from .admit import APPFILE
    return APPFILE


_REA_WAY = ("rea_khoj on the server, statically, the file never runs: action=endpoints lists every URL / host / API path "
            "/ IP inside it (saved as a dataset -> data_read, doc_studio data=<id>), action=overview shows what it is, "
            "imports and uses; for an APK classes / class / method / refs go deeper. The file_id is the one she sent")
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
        if _appfile().search(task) and place not in ("pc", "hoolapc"):
            # stricter than data: only HER word in THIS ask (not an old PC lock in the chat) sends a program file to a PC
            STATS["file_to_pc"] += 1
            raise ToolError("Reading / analysing a program or app file is REA's job, not a PC's: use " + _REA_WAY +
                            ". Never install tools on the cloud PC for it.")
        if where._DATA.search(task) and not admit._DESKTOP.search(task) and not named:
            STATS["data_to_pc"] += 1
            raise ToolError("This is a DATA job and she did not ask for a PC: do it on the server - " + _DATA_WAY +
                            ". A file made on a PC does not come back to the chat.")
        # v0.270 a PC is HER choice or the job's software, never Hoola's: a research / website / writing job on a PC
        # she did not name this turn (and no running PC job of this chat) is refused with the server route
        place_now = place or where.working(conv)
        if place == "server":
            place_now = ""
        if place_now not in ("pc", "hoolapc") and not where._asked(conv, "pc") and not where._asked(conv, "hoolapc") \
                and not admit._DESKTOP.search(task) and not _DESKTOP_APPS.search(task):
            STATS["pc_not_hers"] += 1
            if place_now == "hoola":
                raise ToolError("She asked for YOUR OWN browser (Hoola's browser on the server), not a PC: use "
                                "browse_web / computer_operator there, and doc_studio for a PDF.")
            raise ToolError(f"{name}: she did not put this job on a PC and it needs no desktop software. Do it on "
                            "the server: research = web_sources / google_search / open_website (browse_web for a "
                            "site that needs clicks; deploy_agents when it splits into parts); a PDF / Word / Excel "
                            "= doc_studio; lists / API data = " + _DATA_WAY + ". A file made on a PC never reaches "
                            "the chat.")
