"""v0.881 PC JUDA HAI - "connect to my PC" answered at once, with no AI turn and no PC job.

Root cause (her 13 Nov calls): "mere PC se connect karo" went to the full Hoola brain (Gemini -> santosh_kaam -> the PC
manager turn on Qwen with memory + PC rules), 10-20 s, and once the brain even started a whole PC screen task ("Connect to
this PC and take a look at the current screen") that held the call. Her PC is connected the moment Hoola Desktop is open
- 'connect' needs no action, only the hub's own state, which is a dictionary read.

`only_connect(text)` is strict on purpose: True only when EVERY word is a connect word, a PC word or filler. Any other
word (a site, 'kholo', 'search', 'Amazon') = a real job, and the normal brain path runs. Reads only; never starts,
steers or stops anything."""
from __future__ import annotations

import re

_CONNECT = re.compile(r"(?:connect|connected|conect|konnect|kanekt|connection|jodo|jod|joda|jodiye|juda|judo|jud|"
                      r"judiye|link|कनेक्ट|कनेक्शन|जोड़ो|जोड़|जोड़िए|जुड़ा|जुड़ो|जुड़|जुड़िए|लिंक)", re.I)
_PCWORD = re.compile(r"\b(?:pc|computer|laptop|desktop|system)\b|पीसी|कंप्यूटर|कम्प्यूटर|लैपटॉप|डेस्कटॉप|सिस्टम", re.I)
_FILLER = {
    # english
    "my", "the", "to", "with", "is", "it", "please", "pls", "plz", "can", "you", "check", "now", "ok", "okay", "yes",
    "hey", "hi", "hello", "and", "are", "we", "please.", "just", "once", "again", "of", "a", "me", "your", "be",
    # hinglish
    "mera", "meri", "mere", "apna", "apne", "se", "ko", "ka", "ki", "ke", "karo", "kar", "kardo", "kar do", "kijiye",
    "kariye", "karein", "karen", "do", "dijiye", "abhi", "ab", "ek", "baar", "bar", "hai", "hain", "kya", "hua", "huwa",
    "ho", "gaya", "gya", "haan", "han", "ji", "aap", "zara", "jara", "isse", "usse", "wapas", "phir", "fir", "dobara",
    "santosh", "hoola", "bhai", "na", "toh", "to", "theek", "thik", "accha", "acha", "achha", "chalo", "main", "mai",
    "mujhe", "kahiye", "dekho", "dekhiye", "batao", "bataiye", "par", "pe", "wala", "wali",
    # devanagari
    "मेरा", "मेरी", "मेरे", "अपना", "अपने", "से", "को", "का", "की", "के", "करो", "कर", "करिए", "कीजिए", "करें", "दो",
    "दीजिए", "अभी", "अब", "एक", "बार", "है", "हैं", "क्या", "हुआ", "हो", "गया", "हाँ", "हां", "जी", "आप", "ज़रा", "जरा",
    "ओके", "ओके।", "संतोष", "हूला", "चेक", "फिर", "दोबारा", "वापस", "ठीक", "अच्छा", "चलो", "मैं", "मुझे", "बताओ",
    "बताइए", "देखो", "पर", "पे", "वाला", "वो", "नहीं", "बोल", "रहा", "रही", "हूँ", "हूं",
}
_TOKEN = re.compile("[\\w\u0900-\u0963\u0966-\u097F]+", re.U)   # the danda (U+0964) is punctuation


def only_connect(text: str) -> bool:
    """Her words ask only to connect / whether her PC is connected - nothing else to do."""
    t = str(text or "").strip()
    if not t or len(t) > 160 or not _CONNECT.search(t) or not _PCWORD.search(t):
        return False
    for w in _TOKEN.findall(t.lower()):
        if w in _FILLER or _CONNECT.fullmatch(w) or _PCWORD.fullmatch(w) or w.isdigit():
            continue
        if w.startswith(("connect", "जोड़", "जुड़", "कनेक्ट")) and len(w) <= 12:   # connecting, जोड़ना
            continue
        return False
    return True


def _short_task(task: str) -> str:
    """v0.883 the spoken task: the '[Team job: ...]' goal only, never the long instruction read out word for word."""
    t = str(task or "").strip()
    m = re.match(r"\[(?:Team job|Job)\s*:\s*([^\]]+)\]", t, re.I)
    t = (m.group(1) if m else t).strip()
    t = re.split(r"(?<=[.!?।])\s", t, maxsplit=1)[0]
    return t[:90].rstrip(" ,;:")


def status_line(tenant_id: str, hinglish: bool = True) -> str:
    """One spoken line from the hub's own state: her PC online / control off / paused / offline (+ the task running)."""
    try:
        from .pc.hub import hub
        devs = [d for d in hub.devices(tenant_id) if d.get("kind") == "her_pc"]
    except Exception:
        devs = []
    if not devs:
        return ("Aapka PC abhi juda nahi hai. Us PC par Hoola Desktop kholiye; khulte hi woh apne aap jud jayega."
                if hinglish else "Your PC is not connected right now. Open Hoola Desktop on it and it connects by itself.")
    d = devs[0]
    name = d.get("name") or "PC"
    doing = ""
    try:
        from .pc import operator
        o = operator.busy(tenant_id, d.get("device_id"))
        doing = _short_task(o.task or "") if o else ""
    except Exception:
        doing = ""
    if d.get("paused"):
        return (f"Aapka PC {name} juda hai, par Hoola Desktop abhi pause par hai. Use resume kar dijiye, phir kaam shuru ho jayega."
                if hinglish else f"Your PC {name} is connected, but Hoola Desktop is paused. Resume it and I can start.")
    if not d.get("control"):
        return (f"Aapka PC {name} juda hai, par Hoola Desktop mein control band hai. Control on kar dijiye, phir us par kaam ho payega."
                if hinglish else f"Your PC {name} is connected, but control is off in Hoola Desktop. Turn it on and I can work on it.")
    if doing:
        return (f"Haan, aapka PC {name} juda hua hai. Abhi us par yeh kaam chal raha hai: {doing}."
                if hinglish else f"Yes, your PC {name} is connected. It is working on: {doing}.")
    return (f"Haan, aapka PC {name} juda hua hai. Boliye, us par kya karna hai?"
            if hinglish else f"Yes, your PC {name} is connected. What should I do on it?")
