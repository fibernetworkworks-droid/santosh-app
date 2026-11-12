"""v0.245 SAHI AUZAAR - the last check on Hoola's pick, in code, before a tool runs.

The router (agent/admit.py) decides what Hoola SEES; this decides what may RUN when the pick is plainly wrong.
Three cases, all from real failures, and each refusal names the right tool so the next step is the right one:

1. A PC tool (her PC / Hoola's cloud PC) that was not in view this turn: she named no PC and the job needs no desktop
   software. The GLM brain could call any known handler from the guide text; that is how jobs drifted to the cloud PC.
   If she really meant a PC, tool_search opens the family and the call goes through.
2. A data job (lists, top N, API / repos, collecting) sent to a PC she did not name: data stays on the server
   (data_fetch -> data_read / data_note -> doc_studio data=) and its file reaches the chat; a VM file does not.
4. (v0.270, v0.271 SAB SERVER PAR) Any PC job she did not place on a PC (no PC named this turn or a moment ago, no
   running PC job of hers in the chat): every job runs on the server; desktop software in the task only makes
   Hoola ASK her first ("Yeh aapke PC pe karun?") - it never picks a PC by itself.
3. (v0.257) Reading / analysing a program or app file (.exe / .apk / .dll, endpoints, decompiling) sent to a PC
   without her saying so in THIS ask: that is rea_khoj (action=endpoints / overview), on the server, never run.
"""
from __future__ import annotations

import re
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


# v0.858 an ORDER / booking on a site where she has her own account (logged in on HER PC, her saved address and
# payment) is pointless in Hoola's own server browser - it has no login. With her PC online and no place named, Hoola
# ASKS which one (v0.271 kept: a PC only on her word) instead of silently ordering from its own browser.
_ACCOUNT_SITE = re.compile(r"\b(?:swiggy|zomato|zepto|blinkit|instamart|bigbasket|amazon|flipkart|myntra|meesho|nykaa|"
                           r"ajio|domino'?s|pizza\s*hut|kfc|mcdonald'?s|uber|ola|rapido|bookmyshow|makemytrip|"
                           r"goibibo|irctc|jiomart|dunzo|tata\s*1mg|pharmeasy)\b", re.I)
_ORDERISH = re.compile(r"\b(?:order|mangao|mangwa|mangva|kharid|buy|book|cart|checkout|deliver|bhejo|pay)", re.I)


def _her_account_site(name: str, args: dict[str, Any], ctx) -> None:
    if name == "computer_operator" and str(args.get("action") or "start") != "start":
        return
    task = " ".join(str(args.get(k) or "") for k in ("task", "start_url", "url"))
    if not (_ACCOUNT_SITE.search(task) and _ORDERISH.search(task)):
        return
    from . import where
    conv = getattr(ctx, "conversation_id", "") or ""
    place = getattr(ctx, "place", "") or ""
    if place in ("hoola", "server", "pc", "hoolapc") or where._asked(conv, "hoola") or \
            where.working(conv) in ("pc", "hoolapc"):
        return                                   # she named a place, or a PC task runs: the steer moves it there
    if _her_pc_lately(ctx):
        STATS["kept_her_pc"] = STATS.get("kept_her_pc", 0) + 1   # v0.863 PC SAATH: her orders run on her PC
        raise ToolError("Her own PC (her Chrome, her Swiggy / Amazon login and cart) was working for her minutes ago. "
                        "This order goes THERE: call pc_do with the full task (it continues in the tab that is "
                        "already open). Never your own browser and never Hoola's own PC for her orders.")
    try:
        from ..pc import hub
        online = hub.hub.is_online(getattr(ctx, "tenant_id", "") or "")
    except Exception:
        online = False
    if not online:
        return
    STATS["asked_place"] = STATS.get("asked_place", 0) + 1
    where.offer(conv, "pc")          # her plain 'haan' to this question now names her PC (where.remember)
    raise ToolError("This is an ORDER on a site where SHE has her own account (her login, saved address, payment) - "
                    "your own server browser has none of that. Her PC is online. Do NOT run it here: ask her in ONE "
                    "line 'Yeh aapke PC par karun? Wahan aap Swiggy / Amazon mein logged in hain.' On her yes use pc_do "
                    "with the full task (and the browser she named). Only if she says Hoola's browser, use this tool.")


def _her_pc_lately(ctx) -> bool:
    """v0.863 a task on HER own PC started or ended in the last 45 min (any chat or call of hers)."""
    try:
        from ..pc import operator as pcop
        return pcop.her_pc_recent(getattr(ctx, "tenant_id", "") or "")
    except Exception:
        return False


def check(name: str, args: dict[str, Any], ctx) -> None:
    """Raise ToolError with the right tool when the pick is plainly wrong; return quietly otherwise."""
    if name in ("computer_operator", "browse_web"):
        _her_account_site(name, args or {}, ctx)
    if name not in _PC_TOOLS:
        return
    STATS["checked"] += 1
    from . import admit, where
    adm = getattr(ctx, "admit", None)
    place = getattr(ctx, "place", "") or ""
    conv = getattr(ctx, "conversation_id", "") or ""
    named = place in ("pc", "hoolapc") or where._asked(conv, "pc") or where._asked(conv, "hoolapc") or \
        where.working(conv) in ("pc", "hoolapc")
    if not named and name == "pc_do" and _her_pc_lately(ctx):
        t0 = str((args or {}).get("task") or "")
        named = bool((where._WEBBY.search(t0) or _ORDERISH.search(t0)) and not where._DATA.search(t0))   # v0.863
    if adm is not None and "pc" not in adm.families and not named:
        STATS["pc_not_in_view"] += 1
        raise ToolError(f"{name} was not offered for this ask: she named no PC and the job needs no desktop software. "
                        "Use the server tools in view (documents: doc_studio; lists / API data: " + _DATA_WAY +
                        "; web pages: google_search / open_website / browse_web; website forms: computer_operator). "
                        "If she really wants a PC, call tool_search with 'pc' first.")
    if name in ("hoola_pc_do", "pc_do"):
        task = str((args or {}).get("task") or "")
        # v0.854 PC CONFUSION: the right PC tool for the place she named - 'mere PC' = pc_do, 'Hoola ka PC' = hoola_pc_do
        her_pc = place == "pc" or where._asked(conv, "pc")
        hoola_pc = place == "hoolapc" or where._asked(conv, "hoolapc")
        if not her_pc and not hoola_pc:
            her_pc, hoola_pc = where.working(conv) == "pc", where.working(conv) == "hoolapc"
        if name == "hoola_pc_do" and place != "hoolapc" and not where._asked(conv, "hoolapc") and _her_pc_lately(ctx) \
                and (where._WEBBY.search(task) or _ORDERISH.search(task)):
            STATS["wrong_pc"] = STATS.get("wrong_pc", 0) + 1     # v0.863 PC SAATH: not after her task ENDED either
            raise ToolError("Her own PC did her work minutes ago (this order / site job lives there: her login, her "
                            "cart, her open tab). Use pc_do with her words. Hoola's own PC only when she names it in "
                            "this message ('Hoola ke PC par').")
        if name == "hoola_pc_do" and place != "hoolapc" and where._her_pc_busy(conv):
            STATS["wrong_pc"] = STATS.get("wrong_pc", 0) + 1     # v0.858 never wander to Hoola's PC mid-task
            raise ToolError("Her task is RUNNING on HER OWN PC in this chat right now. Her follow-up belongs to that "
                            "task: call pc_do with her words (it goes into the running task). Hoola's own PC only "
                            "when she names it in this message ('Hoola ke PC par').")
        if name == "pc_do" and hoola_pc and not her_pc:
            STATS["wrong_pc"] = STATS.get("wrong_pc", 0) + 1
            raise ToolError("She asked for HOOLA'S OWN PC (your cloud computer), not hers: use hoola_pc_do, not pc_do.")
        if name == "hoola_pc_do" and her_pc and not hoola_pc:
            STATS["wrong_pc"] = STATS.get("wrong_pc", 0) + 1
            raise ToolError("She asked for HER OWN PC ('mere PC'), not Hoola's cloud PC: use pc_do, not hoola_pc_do.")
        if _appfile().search(task) and place not in ("pc", "hoolapc"):
            # stricter than data: only HER word in THIS ask (not an old PC lock in the chat) sends a program file to a PC
            STATS["file_to_pc"] += 1
            raise ToolError("Reading / analysing a program or app file is REA's job, not a PC's: use " + _REA_WAY +
                            ". Never install tools on the cloud PC for it.")
        if where._DATA.search(task) and not named:
            STATS["data_to_pc"] += 1
            raise ToolError("This is a DATA job and she did not ask for a PC: do it on the server - " + _DATA_WAY +
                            ". A file made on a PC does not come back to the chat.")
        # v0.270 / v0.271 SAB SERVER PAR: a PC is HER choice only - she named it this turn (or a moment ago), or a PC
        # job SHE started is still running in this chat. Desktop software in the task no longer counts on its own:
        # Hoola does the job on the server, or ASKS her first.
        place_now = place or where.working(conv)
        if place == "server":
            place_now = ""
        if name == "pc_do" and not place_now and _her_pc_lately(ctx) and (where._WEBBY.search(task) or
                                                                          _ORDERISH.search(task)):
            place_now = "pc"     # v0.863 PC SAATH: her follow-up order after her PC task ended stays on her PC
        if place_now not in ("pc", "hoolapc") and not where._asked(conv, "pc") and not where._asked(conv, "hoolapc"):
            STATS["pc_not_hers"] += 1
            if place_now == "hoola":
                raise ToolError("She asked for YOUR OWN browser (Hoola's browser on the server), not a PC: use "
                                "browse_web / computer_operator there, and doc_studio for a PDF.")
            needs = admit._DESKTOP.search(task) or _DESKTOP_APPS.search(task)
            raise ToolError(f"{name}: she did not ask for a PC - every job runs on the SERVER unless she says 'PC pe "
                            "karo'. " + ("This task names desktop software: ASK her first in one line ('Yeh aapke PC "
                                         "pe karun?') and wait for her yes; until then do what the server can. "
                                         if needs else "") +
                            "Server route: research = web_sources / google_search / open_website (browse_web for a "
                            "site that needs clicks; deploy_agents when it splits into parts); a PDF / Word / Excel "
                            "= doc_studio; lists / API data = " + _DATA_WAY + "; video = video_edit; a program file "
                            "= rea_khoj. A file made on a PC never reaches the chat.")
