"""v0.93 Teen jagah: Hoola's own browser vs HER PC vs her phone - her words decide, in code.

Owner (22 Oct 2026): "Hoola is confusing between MERA PC browser and Hoola on browser". Three places can open a
website: Hoola's own browser on the server (browse_web / computer_operator), HER PC through Santosh Desktop (pc_do =
Chrome on her computer) and her phone (open_on_phone). The model mixed them up: the PC tools were tagged "[Mera PC]"
(which, from Hoola's mouth, means Hoola's PC), PC results arrived as "(Mera PC result ...)", Hoola's own browser card
had a computer icon, and v0.92 moves a website job to her PC by itself. Now:

  * `place(text)` reads where she wants it: "mere PC / laptop / computer pe", "PC ke Chrome mein", "mere browser mein"
    -> "pc"; "apne / tumhare / aapke / Hoola ke browser mein", "server pe" -> "hoola"; "phone pe kholo" -> "phone";
    a place she says NO to ("PC pe nahi") doesn't count; two different places / none -> "".
  * `remember(conv, text)` keeps the place she named for her short follow-ups ("kal ki", "haan karo"; 15 min) until she
    names another place or starts a new, longer request without one.
  * `steer(name, args, place)` in `tools.dispatch` (chat, calls, delegated call jobs): pc -> browse_web becomes pc_do,
    computer_operator runs on her PC, open_on_phone opens in her PC's Chrome; hoola -> a pc_do website task is refused
    with the right tool, and computer_operator never moves to her PC without asking her first.

v0.104 "Browser work in PC is smooth, but suddenly Hoola launches its own browser in between": the place she named was
kept only 15 min and only for follow-ups of <= 8 words, so a longer next message, the "(Result from HER PC ...)" note
turn, or a retry after a PC hiccup came with NO place and the model picked its own browser. Now the place also sticks
by the WORK itself (`worked`): once a website job runs on her PC (or in Hoola's own browser) in this chat, every later
website step stays there for `WORK_KEEP_S` (refreshed by every step and every result note) until she names another
place. If that place stops answering, the model is told to tell her and ask - never to switch by itself.
"""
from __future__ import annotations

import re
import time
from typing import Any

from .tools import ToolError

KEEP_S = 15 * 60
FOLLOW_UP_WORDS = 8              # a message this short with no place = a follow-up of the last request
WORK_KEEP_S = 45 * 60            # a running website job keeps its place this long after its last step / result
HOOLAPC_KEEP_S = 20 * 60         # v0.238 the cloud PC holds the chat this long from when it STARTED, never renewed
                                 # (one cloud-PC job's results used to pull every later job there)
STATS = {"named": 0, "kept": 0, "steered": 0, "refused": 0, "stuck": 0, "not_stuck": 0}
_PLACE: dict[str, tuple[str, float]] = {}
_WORK: dict[str, tuple[str, float]] = {}      # conv -> (place where website work is really running, last touch)
_WHY: dict[str, str] = {}                    # conv -> named | follow | work (for the line the model gets)

PC_WORDS = "Aapka PC (Santosh Desktop: Chrome / apps on HER own computer)"
HOOLA_WORDS = "Hoola ka apna browser (on Hoola's server - not her PC, not her phone)"
# v0.194 the third computer: Hoola's OWN cloud PC (the coworker VM, Linux + Chromium + install software)
HOOLAPC_WORDS = "Hoola ka apna cloud PC (the Linux computer owned by Hoola: Chromium, apt/pip installs, shell)"

_NOUN = r"(?:pc|p\.c\.|computer|kompyuter|compyuter|laptop|desktop|पीसी|कंप्यूटर|कम्प्यूटर|लैपटॉप|डेस्कटॉप)"
_PC = [
    re.compile(r"(?<![\w.])" + _NOUN + r"(?![\w])", re.I),
    re.compile(r"\b(?:santosh|hoola)\s+desktop\b", re.I),
    re.compile(r"\b(?:mer[aei]|my|hamar[aei])\s+(?:wal[aei]\s+)?(?:chrome|browser|edge|firefox)\b", re.I),
    re.compile(r"(?:मेरे|मेरा|मेरी)\s+(?:ब्राउज़र|ब्राउजर|क्रोम)"),
]
_HOOLA = [
    re.compile(r"\b(?:apn[aei]|tumhar[aei]|tumhare|ter[aei]|aapk[aei]|aap\s+k[aei]|your|your\s+own|khud\s+k[aei]|"
               r"hoola\s+k[aei]|santosh\s+k[aei]|hoola)\s+(?:own\s+|wal[aei]\s+|hi\s+)?(?:browser|chrome)\b", re.I),
    re.compile(r"\bhoola\s+(?:on|in|par|pe|mein)\s+(?:the\s+)?browser\b", re.I),
    re.compile(r"\b(?:server|cloud)\s*(?:pe|par|pr|mein|me|se|on|wal[aei])\b|\bon\s+(?:the\s+|your\s+)?server\b", re.I),
    re.compile(r"(?:अपने|तुम्हारे|आपके|होला\s+के)\s+(?:ब्राउज़र|ब्राउजर|क्रोम)"),
]
_PHONE = [
    re.compile(r"\b(?:phone|mobile|fon)\s*(?:pe|par|pr|mein|me|on)\s+(?:hi\s+)?(?:khol|dikha|open|chala|show)", re.I),
    re.compile(r"\b(?:on|in)\s+my\s+(?:phone|mobile)\b", re.I),
    re.compile(r"(?:फ़ोन|फोन|मोबाइल)\s*(?:पे|पर|में)\s*(?:खोल|दिखा)"),
]
_NOT_AFTER = re.compile(r"^[\s,.)]*(?:\w+\s+)?(?:(?:nahi|nahin|nai|mat|na|not|no)\b|नहीं|नही|मत)", re.I)
_NOT_BEFORE = re.compile(r"(?:\bnot|\bno|\bmat|\bna|नहीं|मत)\s+(?:\w+\s+)?$", re.I)
# v0.194 HOOLA KA APNA PC: the possessive points at Hoola (aapke / tumhare / apne / hoola ke) + a COMPUTER noun
# (not browser). From her mouth 'apna computer' attaches to the doer - Hoola - same convention as 'apne browser'.
_HOOLAPC = [
    re.compile(r"\b(?:apn[aei]|tumhar[aei]|tumhare|ter[aei]|aapk[aei]|aap\s+k[aei]|your|your\s+own|khud\s+k[aei]|"
               r"hoola\s+k[aei]|santosh\s+k[aei]|hoola)\s+(?:own\s+|wal[aei]\s+|hi\s+)?"
               r"(?:pc|p\.c\.|computer|kompyuter|compyuter|laptop|desktop|machine)\b", re.I),
    re.compile(r"\bhoola\s+ka\s+(?:apna\s+)?(?:pc|computer|laptop|desktop)\b|\bhoola\s+(?:pc|laptop)\b", re.I),
    re.compile(r"(?:अपने|तुम्हारे|आपके|होला\s+के)\s*(?:पीसी|कंप्यूटर|कम्प्यूटर|लैपटॉप|डेस्कटॉप)"),
]
# v0.238 data / API jobs are not website work: they never lock the chat onto a place (they belong to data_fetch)
_DATA = re.compile(r"\bapi\b|\bapi\.|/api/|\bjson\b|\brepos?\b|repositor|\bcsv\b|dataset|\btop\s*\d+|scrap|"
                   r"\bcollect|\bfetch|\bstats?\b|\bdata\b", re.I)


def _form_job(task: str) -> bool:
    """A real website job (a page to open / fill / click), not data collection."""
    t = str(task or "")
    return bool(_WEBBY.search(t)) and not _DATA.search(t)


def _asked(conv: str, where: str) -> bool:
    """She herself named this place for the work (now, or a moment ago)."""
    old = _PLACE.get(conv)
    return bool(old and old[0] == where and time.time() - old[1] <= KEEP_S)


# names of features, not places: "computer operator" is Hoola's own browser, "PC operator" is her PC (kept)
_FEATURE = re.compile(r"\bcomputer\s+operator\b", re.I)
_WEBBY = re.compile(r"https?://|www\.|\.(?:com|in|org|net|gov|co)\b|\b(?:chrome|browser|website|site|portal|web\s*page|"
                    r"online|login|irctc|uidai|aadhaar|digilocker|amazon|flipkart|google)\b", re.I)


def _hit(text: str, pats: list[re.Pattern]) -> bool:
    for p in pats:
        for m in p.finditer(text):
            if _NOT_AFTER.match(text[m.end():m.end() + 24]) or _NOT_BEFORE.search(text[max(0, m.start() - 16):m.start()]):
                continue
            return True
    return False


def place(text: str) -> str:
    """Where she wants it: 'pc' | 'hoolapc' | 'hoola' | 'phone' | '' (none named, or two different places)."""
    t = _FEATURE.sub(" ", str(text or ""))[:2000]
    if not t.strip():
        return ""
    if _hit(t, _HOOLAPC):   # v0.194 the possessive named Hoola's own computer: wins over the bare-noun PC match
        return "hoolapc"
    got = {p for p, pats in (("pc", _PC), ("hoola", _HOOLA), ("phone", _PHONE)) if _hit(t, pats)}
    return next(iter(got)) if len(got) == 1 else ""


def remember(conv: str, text: str) -> str:
    """The place for this message: named now, kept from her last request for a short follow-up, else the place where
    website work is already running in this chat (so a job never jumps to another browser half way)."""
    p = place(text)
    now = time.time()
    if p:
        STATS["named"] += 1
        _PLACE[conv] = (p, now)
        w = _WORK.get(conv)
        if w and w[0] != p:
            _WORK.pop(conv, None)           # her word moves the work: the old place no longer holds
        _WHY[conv] = "named"
        return p
    old = _PLACE.get(conv)
    if old and now - old[1] <= KEEP_S and len(str(text or "").split()) <= FOLLOW_UP_WORDS:
        STATS["kept"] += 1
        _WHY[conv] = "follow"
        return old[0]
    if not old or now - old[1] > KEEP_S or len(str(text or "").split()) > FOLLOW_UP_WORDS:
        _PLACE.pop(conv, None)
    w = working(conv)
    if w:
        STATS["stuck"] += 1
        _WHY[conv] = "work"
        return w
    _WHY.pop(conv, None)
    return ""


def current(conv: str) -> str:
    old = _PLACE.get(conv)
    if old and time.time() - old[1] <= KEEP_S:
        return old[0]
    return working(conv)


def working(conv: str) -> str:
    """Where website work is running in this chat right now (pc | hoola), '' when none lately."""
    w = _WORK.get(conv)
    if not w:
        return ""
    if time.time() - w[1] > (HOOLAPC_KEEP_S if w[0] == "hoolapc" else WORK_KEEP_S):
        _WORK.pop(conv, None)
        return ""
    return w[0]


def touch(conv: str, where: str) -> None:
    """A step or a result of website work just happened in this place (keeps the job where it is).
    v0.238: the cloud PC (hoolapc) locks the chat only when she herself asked for it - Hoola's own choice of the
    cloud PC never sticks - and its lock is never EXTENDED by the running job (her PC / Hoola's browser still are)."""
    if not conv or where not in ("pc", "hoola", "hoolapc"):
        return
    if where == "hoolapc" and not (_asked(conv, "hoolapc") or (_WORK.get(conv) or ("",))[0] == "hoolapc"):
        STATS["not_stuck"] += 1
        return
    if where == "hoolapc" and working(conv) == "hoolapc":
        return                        # already held: the window counts from the start, never renewed
    _WORK[conv] = (where, time.time())


def worked(conv: str, name: str, args: dict[str, Any], out: Any = None) -> None:
    """Called by dispatch with the tool that REALLY ran: remembers where the website work is going on."""
    args = args or {}
    w = ""
    if name == "pc_do" and _form_job(str(args.get("task") or "")):
        w = "pc"
    elif name == "hoola_pc_do" and _form_job(str(args.get("task") or "")) and _asked(conv, "hoolapc"):
        w = "hoolapc"                 # v0.238 only when SHE asked for the cloud PC
    elif name in ("pc_do", "hoola_pc_do"):
        STATS["not_stuck"] += 1
    elif name == "browse_web":
        w = "hoola"
    elif name == "computer_operator" and str(args.get("action") or "") == "start":
        moved = isinstance(out, dict) and (out.get("moved_to") == "pc" or out.get("where") == "pc")
        w = "pc" if (args.get("where") == "pc" or moved) else "hoola"
    if w:
        touch(conv, w)


def forget(conv: str = "") -> None:
    if conv:
        _PLACE.pop(conv, None)
        _WORK.pop(conv, None)
        _WHY.pop(conv, None)
    else:
        _PLACE.clear()
        _WORK.clear()
        _WHY.clear()


def _url(u: Any) -> str:
    u = str(u or "").strip()
    if u and not u.lower().startswith(("http://", "https://")):
        u = "https://" + u
    return u


def steer(name: str, args: dict[str, Any], where: str) -> tuple[str, dict[str, Any], str]:
    """(tool, args, note). Moves a website tool to the place she named; refuses a call that goes to the other place."""
    args = dict(args or {})
    if where == "hoolapc":   # v0.193 she named Hoola's OWN computer: website jobs run in Chromium on the Hoola PC
        if name in ("browse_web", "open_on_phone"):
            url = _url(args.get("start_url") or args.get("url"))
            task = (str(args.get("task") or "").strip() + (f" Website: {url}." if url else "") +
                    " Do it in Chromium on Hoola's own PC (your own cloud computer).")
            STATS["steered"] += 1
            return "hoola_pc_do", {"task": task}, ("She asked for HOOLA KA APNA PC, so this runs in Chromium on the "
                                                    "Hoola PC (your own cloud computer), not the server browser.")
        if name == "pc_do":
            STATS["refused"] += 1
            raise ToolError("She asked for HOOLA KA APNA PC (your own cloud computer), not her PC. Use hoola_pc_do "
                            "for this task; pc_do drives HER Windows PC and needs her to say 'mere PC pe'.")
        if name == "computer_operator" and str(args.get("action") or "") == "start":
            url = _url(args.get("start_url"))
            task = (str(args.get("task") or "").strip() + (f" Website: {url}." if url else "") +
                    " Do it in Chromium on Hoola's own PC (your own cloud computer).")
            STATS["steered"] += 1
            return "hoola_pc_do", {"task": task}, "She asked for HOOLA KA APNA PC: this website job runs in Chromium on the Hoola PC."
    if where == "pc":
        if name == "hoola_pc_do":   # v0.270 she named HER PC: never Hoola's cloud PC behind her back
            STATS["refused"] += 1
            raise ToolError("She asked for HER PC (Santosh Desktop on her own computer), not your cloud PC. Use "
                            "pc_do for this task.")
        if name == "browse_web":
            url = _url(args.get("start_url"))
            task = (str(args.get("task") or "").strip() + (f" Website: {url}." if url else "") +
                    " Do it in Google Chrome on this PC (her own browser).")
            STATS["steered"] += 1
            return "pc_do", {"task": task}, "She asked for HER PC, so this runs in Chrome on her PC (not your server browser)."
        if name == "open_on_phone":
            url = _url(args.get("url"))
            STATS["steered"] += 1
            return "pc_do", {"task": f"Open {url} in Google Chrome on this PC and leave it open for her."}, \
                "She asked for HER PC, so the link opens in Chrome on her PC (not on her phone)."
        if name == "computer_operator" and str(args.get("action") or "") == "start" and args.get("where") != "pc":
            args["where"] = "pc"
            STATS["steered"] += 1
            return name, args, "She asked for HER PC, so this website job runs in Chrome on her PC."
    elif where == "hoola":
        if name == "pc_do" and _WEBBY.search(str(args.get("task") or "")):
            STATS["refused"] += 1
            raise ToolError("She asked for YOUR OWN browser (Hoola's browser on the server), not her PC. Use browse_web "
                            "for look-ups / checking, or computer_operator action=start for forms, downloads and logins. "
                            "Don't use pc_do unless she says 'PC par'.")
        if name == "computer_operator" and str(args.get("action") or "") == "start" and args.get("where") in (None, "", "auto", "pc"):
            args["where"] = "hoola"
            return name, args, ""
    return name, args, ""


def note(where: str, conv: str = "") -> str:
    """The line the model gets with her message when a place holds for it."""
    if conv and _WHY.get(conv) == "work" and where in ("pc", "hoola", "hoolapc"):
        if where == "pc":
            return ("[Jagah: the website work in this chat is running in Chrome on HER PC. Keep every website step of it there "
                    "(pc_do / pc_task_result) - do NOT open your own browser (browse_web / computer_operator) for it. If her PC "
                    "doesn't answer, tell her plainly and ask; never switch by yourself. Call it 'aapka PC'.]")
        if where == "hoolapc":
            return ("[Jagah: the website work in this chat is running in Chromium on HOOLA KA APNA PC (your own cloud "
                    "computer). Keep every website step of it there (hoola_pc_do / pc_task_result) - do NOT open the server "
                    "browser (browse_web / computer_operator) or her PC (pc_do) for it. If the Hoola PC doesn't answer, tell "
                    "her plainly and ask; never switch by yourself.]")
        return ("[Jagah: the website work in this chat is running in YOUR OWN browser (Hoola's browser on the server). Keep it "
                "there (browse_web / computer_operator); don't move it to her PC unless she says 'PC par'.]")
    return {
        "pc": "[Jagah: she said HER PC. Website work runs in Chrome on her PC (pc_do, or computer_operator where=pc), "
              "not in your own browser. Call it 'aapka PC', never 'mera PC'.]",
        "hoolapc": "[Jagah: she said HOOLA KA APNA PC (your own cloud computer). The job runs there (hoola_pc_do): "
                   "Chromium, and you may install software / run commands freely inside your own VM. Not her PC (pc_do), "
                   "not the server browser (browse_web).]",
        "hoola": "[Jagah: she said YOUR OWN browser (Hoola's browser on the server): browse_web / computer_operator. "
                 "Not her PC. If the site refuses your server, tell her and ask before moving it to her PC.]",
        "phone": "[Jagah: she said her PHONE: open_on_phone opens it there for her.]",
    }.get(where, "")


def shown(name: str, args: dict[str, Any], where: str) -> str:
    """The tool that will really run (for labels and the Work Theatre), without raising."""
    if not where:
        return name
    try:
        return steer(name, args, where)[0]
    except ToolError:
        return name
