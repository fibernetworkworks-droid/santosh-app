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
"""
from __future__ import annotations

import re
import time
from typing import Any

from .tools import ToolError

KEEP_S = 15 * 60
FOLLOW_UP_WORDS = 8              # a message this short with no place = a follow-up of the last request
STATS = {"named": 0, "kept": 0, "steered": 0, "refused": 0}
_PLACE: dict[str, tuple[str, float]] = {}

PC_WORDS = "Aapka PC (Santosh Desktop: Chrome / apps on HER own computer)"
HOOLA_WORDS = "Hoola ka apna browser (on Hoola's server - not her PC, not her phone)"

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
    """Where she wants it: 'pc' | 'hoola' | 'phone' | '' (none named, or two different places)."""
    t = _FEATURE.sub(" ", str(text or ""))[:2000]
    if not t.strip():
        return ""
    got = {p for p, pats in (("pc", _PC), ("hoola", _HOOLA), ("phone", _PHONE)) if _hit(t, pats)}
    return next(iter(got)) if len(got) == 1 else ""


def remember(conv: str, text: str) -> str:
    """The place for this message: named now, or kept from her last request when this is a short follow-up."""
    p = place(text)
    now = time.time()
    if p:
        STATS["named"] += 1
        _PLACE[conv] = (p, now)
        return p
    old = _PLACE.get(conv)
    if not old or now - old[1] > KEEP_S:
        _PLACE.pop(conv, None)
        return ""
    if len(str(text or "").split()) > FOLLOW_UP_WORDS:     # a new request of its own: let it choose freely
        _PLACE.pop(conv, None)
        return ""
    STATS["kept"] += 1
    return old[0]


def current(conv: str) -> str:
    old = _PLACE.get(conv)
    return old[0] if old and time.time() - old[1] <= KEEP_S else ""


def forget(conv: str = "") -> None:
    if conv:
        _PLACE.pop(conv, None)
    else:
        _PLACE.clear()


def _url(u: Any) -> str:
    u = str(u or "").strip()
    if u and not u.lower().startswith(("http://", "https://")):
        u = "https://" + u
    return u


def steer(name: str, args: dict[str, Any], where: str) -> tuple[str, dict[str, Any], str]:
    """(tool, args, note). Moves a website tool to the place she named; refuses a call that goes to the other place."""
    args = dict(args or {})
    if where == "pc":
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


def note(where: str) -> str:
    """The line the model gets with her message when she named a place."""
    return {
        "pc": "[Jagah: she said HER PC. Website work runs in Chrome on her PC (pc_do, or computer_operator where=pc), "
              "not in your own browser. Call it 'aapka PC', never 'mera PC'.]",
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
