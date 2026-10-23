"""Motion designer desk: pure rules (no DB). Deliverable specs per platform, licence handover rules, revision rounds, timecoded
client notes, storyboard cleaning, GST / TDS notes. Everything here is a STARTER the owner can change; sources are in WIRING.md."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

# ---------------------------------------------------------------- small helpers


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 500) -> str:
    """Client / her words: secrets never kept (OTP / PIN / password values, card-like and Aadhaar-like numbers)."""
    t = str(text or "")
    t = re.sub(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f]", " ", t)
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    return t.strip()[:n]


def phone(text: Any) -> str:
    d = re.sub(r"\D", "", str(text or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").strip()
    m = re.fullmatch(r"([\d.]+)\s*(k|hazar|hazaar|thousand|lakh|lac|l)?", s)
    if not m:
        return None
    try:
        x = float(m.group(1))
    except ValueError:
        return None
    mult = {"k": 1e3, "hazar": 1e3, "hazaar": 1e3, "thousand": 1e3, "lakh": 1e5, "lac": 1e5, "l": 1e5}.get(m.group(2) or "", 1)
    return round(x * mult, 2)


def hexcol(v: Any) -> str:
    v = str(v or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", v):
        return ("#" + v.lstrip("#")).upper()
    return ""


NAMED = {"laal": "#D32F2F", "red": "#D32F2F", "neela": "#1565C0", "blue": "#1565C0", "hara": "#2E7D32", "green": "#2E7D32",
         "peela": "#F9A825", "yellow": "#F9A825", "kaala": "#111111", "black": "#111111", "safed": "#FFFFFF", "white": "#FFFFFF",
         "narangi": "#EF6C00", "orange": "#EF6C00", "gulabi": "#D81B60", "pink": "#D81B60", "baingani": "#6A1B9A", "purple": "#6A1B9A",
         "sunehra": "#C9A227", "golden": "#C9A227", "gold": "#C9A227", "aasmani": "#29B6F6", "maroon": "#7B1F2A"}


def color(v: Any) -> str:
    return hexcol(v) or NAMED.get(str(v or "").strip().lower(), "")


# ---------------------------------------------------------------- deliverable specs (platform -> what to export)
# px / aspect / fps / longest allowed (starter; platforms change these: re-check). `engine` = the aspect Hoola Motion can render.
PLATFORMS: dict[str, dict[str, Any]] = {
    "insta_reel": {"label": "Instagram Reel", "aspect": "9:16", "px": "1080x1920", "fps": 30, "max_s": 180, "engine": "9:16",
                   "note": "Reel 9:16, 1080x1920, 3 min tak. Neeche ~20% aur upar ~14% mein text mat rakhiye (buttons / caption)."},
    "insta_post": {"label": "Instagram feed video 4:5", "aspect": "4:5", "px": "1080x1350", "fps": 30, "max_s": 180, "engine": "",
                   "note": "Feed 4:5: Hoola Motion 4:5 nahi banata; 1:1 version de sakte hain ya editor mein crop."},
    "insta_story": {"label": "Instagram Story", "aspect": "9:16", "px": "1080x1920", "fps": 30, "max_s": 60, "engine": "9:16",
                    "note": "Story ek card 60 sec tak."},
    "yt_short": {"label": "YouTube Short", "aspect": "9:16", "px": "1080x1920", "fps": 30, "max_s": 180, "engine": "9:16",
                 "note": "Shorts 3 min tak (15 Oct 2024 se). Music ka Content ID dhyaan rakhiye."},
    "youtube": {"label": "YouTube video 16:9", "aspect": "16:9", "px": "1920x1080", "fps": 30, "max_s": None, "engine": "16:9",
                "note": "16:9 Full HD. YouTube awaaz ko lagbhag -14 LUFS par barabar karta hai."},
    "fb_reel": {"label": "Facebook Reel", "aspect": "9:16", "px": "1080x1920", "fps": 30, "max_s": 90, "engine": "9:16",
                "note": "Facebook reel (starter 90 sec; Meta ka spec dobara dekhiye)."},
    "whatsapp_status": {"label": "WhatsApp Status", "aspect": "9:16", "px": "1080x1920", "fps": 30, "max_s": 60, "engine": "9:16",
                        "note": "Status chhota rakhiye (starter 60 sec); file chhoti (16 MB ke aas paas) behtar."},
    "square": {"label": "Square 1:1 (feed / WhatsApp)", "aspect": "1:1", "px": "1080x1080", "fps": 30, "max_s": 180, "engine": "1:1",
               "note": "1:1 sab jagah chalta hai."},
    "linkedin": {"label": "LinkedIn video", "aspect": "1:1", "px": "1080x1080", "fps": 30, "max_s": 600, "engine": "1:1",
                 "note": "LinkedIn feed mein 1:1 ya 4:5 achha dikhta hai; captions zaroor (bina awaaz dekhte hain)."},
    "presentation": {"label": "Presentation / website 16:9", "aspect": "16:9", "px": "1920x1080", "fps": 30, "max_s": None,
                     "engine": "16:9", "note": "Website / pitch ke liye MP4 H.264; website par muted autoplay."},
    "tv_ooh": {"label": "TV / LED screen 16:9", "aspect": "16:9", "px": "1920x1080", "fps": 25, "max_s": None, "engine": "16:9",
               "note": "TV / mall LED ka spec channel / vendor ki sheet se lijiye (fps, loudness, safe area). Hoola starter 25 fps likhta hai."},
    "gif": {"label": "GIF / sticker", "aspect": "1:1", "px": "600x600", "fps": 15, "max_s": 10, "engine": "1:1",
            "note": "GIF ke liye MP4 se convert: chhota aur bina awaaz."},
}
ENGINE_PX = {"9:16": "720x1280", "1:1": "900x900", "16:9": "1280x720"}    # what Hoola Motion renders today


def platform_of(text: Any) -> str:
    t = str(text or "").lower()
    if t in PLATFORMS:
        return t
    pairs = [("story", "insta_story"), ("status", "whatsapp_status"), ("short", "yt_short"), ("reel", "insta_reel"),
             ("youtube", "youtube"), ("yt", "youtube"), ("facebook", "fb_reel"), ("linkedin", "linkedin"), ("square", "square"),
             ("1:1", "square"), ("4:5", "insta_post"), ("feed", "insta_post"), ("post", "insta_post"), ("gif", "gif"),
             ("tv", "tv_ooh"), ("led", "tv_ooh"), ("website", "presentation"), ("presentation", "presentation"), ("16:9", "youtube"),
             ("9:16", "insta_reel"), ("insta", "insta_reel")]
    for w, p in pairs:
        if w in t:
            return p
    return ""


def deliverable(item: Any) -> dict[str, Any] | None:
    """{platform, seconds?, note?} or a word -> a clean deliverable line with the spec and honest notes."""
    if isinstance(item, str):
        item = {"platform": item}
    if not isinstance(item, dict):
        return None
    p = platform_of(item.get("platform") or item.get("name") or "")
    if not p:
        return None
    sp = PLATFORMS[p]
    sec = num(item.get("seconds"))
    warn = []
    if sec is not None and sp["max_s"] and sec > sp["max_s"]:
        warn.append(f"{sp['label']} {sp['max_s']} sec tak leta hai; {int(sec)} sec zyada hai.")
    if not sp["engine"]:
        warn.append(sp["note"])
    elif ENGINE_PX[sp["engine"]] != sp["px"]:
        warn.append(f"Hoola Motion abhi {ENGINE_PX[sp['engine']]} banata hai; {sp['label']} ke liye {sp['px']} sujhaya jaata hai "
                    "(upscale / editor mein export, ya aisa hi chalega - aapka faisla).")
    return {"platform": p, "label": sp["label"], "aspect": sp["aspect"], "px": sp["px"], "fps": sp["fps"], "max_s": sp["max_s"],
            "seconds": sec, "engine_aspect": sp["engine"], "note": clean(item.get("note"), 200), "spec_note": sp["note"],
            "warnings": warn}


# ---------------------------------------------------------------- licences (fonts, music, stock, templates)
LICENCES: dict[str, dict[str, Any]] = {
    "ofl": {"label": "SIL Open Font License", "files_ok": True, "edit_ok": True,
            "say": "OFL: video / commercial kaam mein free; font file client ko de sakte hain (licence file ke saath), font akela bechna mana."},
    "apache": {"label": "Apache 2.0", "files_ok": True, "edit_ok": True, "say": "Apache 2.0: licence copy ke saath file de sakte hain."},
    "adobe_fonts": {"label": "Adobe Fonts (Creative Cloud)", "files_ok": False, "edit_ok": False,
                    "say": "Adobe Fonts: video / commercial output theek, par font FILE client ko nahi de sakte. Client ko edit karna ho to "
                           "apna Adobe / desktop licence lena hoga."},
    "desktop_font": {"label": "Kharida hua desktop font", "files_ok": False, "edit_ok": False,
                     "say": "Kharida font: aam taur par file sirf aapke licence ke liye; client ko apna licence lena hota hai (EULA dekhiye)."},
    "subscription_single": {"label": "Subscription, ek project par register (Envato Elements jaisa)", "files_ok": False,
                            "edit_ok": False, "single_project": True,
                            "say": "Har naye project ke liye naya register / licence; end product client ko de sakte hain, item alag se nahi."},
    "subscription": {"label": "Subscription (Artlist / Epidemic jaisa)", "files_ok": False, "edit_ok": False,
                     "say": "Subscription ke time pe publish hua kaam covered; client ke channel ke liye unka 'client' / single-track "
                            "licence sharton se dekhiye; Content ID clearance zaroori ho sakta hai."},
    "single_track": {"label": "Ek track / ek item ka licence", "files_ok": False, "edit_ok": False,
                     "say": "Jis kaam ke liye liya, usi mein; licence copy client ko do."},
    "royalty_free": {"label": "Royalty-free (shart ke saath)", "files_ok": False, "edit_ok": False,
                     "say": "Royalty-free ka matlab free nahi: shartein (attribution, platform) dekhiye."},
    "cc0": {"label": "CC0 / public domain", "files_ok": True, "edit_ok": True, "say": "CC0: koi shart nahi; source note rakhiye."},
    "cc_by": {"label": "CC BY (naam dena zaroori)", "files_ok": True, "edit_ok": True,
              "say": "CC BY: credit line dena zaroori (description / end card)."},
    "client_supplied": {"label": "Client ne diya", "files_ok": True, "edit_ok": True,
                        "say": "Client ki di hui cheez: haq client ka zimma; likhit mein le lijiye ki unke paas haq hai."},
    "own_work": {"label": "Aapka apna banaya", "files_ok": True, "edit_ok": True, "say": "Aapka banaya: copyright aapka, jab tak likhit assignment na ho."},
    "hoola_music": {"label": "Hoola Motion ka apna music bed", "files_ok": True, "edit_ok": True,
                    "say": "Hoola ka numpy se bana music bed: kisi aur ka gaana nahi, client use kar sakta hai."},
    "ai_generated": {"label": "AI se bana (Hoola / photogen / studio)", "files_ok": True, "edit_ok": True,
                     "say": "AI se bana: 'AI-generated' label zaroori (IT Rules 2026); asli logon ka chehra / awaaz sirf consent se."},
    "unknown": {"label": "Pata nahi", "files_ok": False, "edit_ok": False,
                "say": "Licence pata nahi: final se pehle licence ka saboot (invoice / licence ID) chahiye."},
}
ASSET_KINDS = ("font", "music", "sfx", "stock_video", "stock_image", "template", "3d_model", "plugin", "logo", "photo", "other")
SOURCE_LICENCE = {"google_fonts": "ofl", "fontsource": "ofl", "adobe_fonts": "adobe_fonts", "envato": "subscription_single",
                  "artlist": "subscription", "epidemic": "subscription", "pixabay": "royalty_free", "pexels": "royalty_free",
                  "unsplash": "royalty_free", "youtube_audio_library": "royalty_free", "hoola_music": "hoola_music",
                  "hoola": "ai_generated", "own": "own_work", "client": "client_supplied"}


def licence_of(source: str, licence: str) -> str:
    licence = (licence or "").strip().lower()
    if licence in LICENCES:
        return licence
    return SOURCE_LICENCE.get((source or "").strip().lower(), "unknown")


def asset_problems(a: dict[str, Any], job_id: str, today_iso: str) -> tuple[list[str], list[str]]:
    """(blocks, warnings) for using asset `a` in job `job_id`."""
    lic = LICENCES.get(a.get("licence") or "unknown", LICENCES["unknown"])
    blocks, warns = [], []
    name = a.get("name") or a.get("kind") or "asset"
    if (a.get("licence") or "unknown") == "unknown":
        blocks.append(f"{name}: licence pata nahi (licence ID / invoice daaliye).")
    if lic.get("single_project"):
        used = [j for j in (a.get("jobs") or []) if j]
        if len(set(used) | {job_id}) > 1 and (a.get("project_job") or "") not in ("", job_id):
            blocks.append(f"{name}: ek project wala licence pehle {a.get('project_job')} ke liye register hai; is kaam ke liye naya "
                          "register / licence chahiye.")
    vu = a.get("valid_until") or ""
    if vu and vu < today_iso:
        warns.append(f"{name}: licence {vu} ko khatam; naye kaam / naye download ke liye renew chahiye (pehle bana kaam aam taur par "
                     "covered rehta hai: shartein dekhiye).")
    if (a.get("licence") or "") == "cc_by" and not a.get("credit"):
        blocks.append(f"{name}: CC BY mein credit line zaroori; credit likhiye.")
    return blocks, warns


def handover_lines(assets: list[dict[str, Any]]) -> list[dict[str, str]]:
    """What the client gets / must buy for each asset (the handover note)."""
    out = []
    for a in assets:
        lic = LICENCES.get(a.get("licence") or "unknown", LICENCES["unknown"])
        out.append({"name": a.get("name", ""), "kind": a.get("kind", ""), "licence": lic["label"],
                    "ref": a.get("licence_ref") or "", "files": "file de sakte hain" if lic["files_ok"] else "file nahi, sirf output",
                    "client_needs": "" if lic["edit_ok"] else "Edit / dobara use ke liye client ko apna licence chahiye",
                    "credit": a.get("credit") or "", "say": lic["say"]})
    return out


# ---------------------------------------------------------------- revision rounds
def round_state(used: int, included: int) -> dict[str, Any]:
    left = max(0, included - used)
    return {"used": used, "included": included, "left": left, "extra": max(0, used - included),
            "say": (f"{used} / {included} badlav round use hue" + (f"; {left} baaki." if left else "; ab extra round paise wala hai."))}


_TC = re.compile(r"(?<![\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.:](\d{1,2}))?(?![\d:])|(?<![\w.])(\d{1,3}(?:\.\d)?)\s*(?:s|sec|second)\b",
                 re.I)


def timecodes(text: Any) -> list[dict[str, Any]]:
    """Client notes -> [{tc seconds | None, text}]. One line per note; '0:12 logo bada karo', '00:01:05 colour', '12s fast'."""
    out = []
    for line in re.split(r"[\n;]+", str(text or "")):
        line = clean(line, 400)
        if not line:
            continue
        m = _TC.search(line)
        tc = None
        if m:
            if m.group(5):
                tc = float(m.group(5))
            else:
                h = int(m.group(1) or 0)
                mm, ss = int(m.group(2)), int(m.group(3))
                if ss < 60:
                    tc = h * 3600 + mm * 60 + ss + (int(m.group(4)) / 30 if m.group(4) else 0)
            body = (line[:m.start()] + line[m.end():]).strip(" -:–,")
        else:
            body = line
        out.append({"tc": round(tc, 2) if tc is not None else None, "text": body or line})
    return out


def tc_text(tc: float | None) -> str:
    if tc is None:
        return "--:--"
    m, s = divmod(int(tc), 60)
    return f"{m:02d}:{s:02d}"


# ---------------------------------------------------------------- storyboard
def clean_frames(frames: Any, brief: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Model / her frames -> clean list. Numbers (prices, phones, %, dates) that are not in the brief become '[?]'."""
    seen_nums = set(re.findall(r"\d+(?:[.,]\d+)?", brief or ""))
    out, notes = [], []
    if not isinstance(frames, list):
        return [], []
    for i, f in enumerate(frames[:24]):
        if not isinstance(f, dict):
            continue
        d = {"n": len(out) + 1, "seconds": max(0.5, min(float(num(f.get("seconds")) or 3.0), 60.0)),
             "visual": clean(f.get("visual"), 300), "text": clean(f.get("text"), 160), "motion": clean(f.get("motion"), 160),
             "audio": clean(f.get("audio"), 120)}
        for k in ("visual", "text", "audio"):
            def _fix(m: re.Match) -> str:
                return m.group(0) if m.group(0) in seen_nums else "[?]"
            new = re.sub(r"\d+(?:[.,]\d+)?", _fix, d[k])
            if new != d[k]:
                notes.append(f"Frame {d['n']}: brief mein na hone wala number hataya ([?]).")
                d[k] = new
        if d["visual"] or d["text"]:
            out.append(d)
    return out, notes


def fallback_frames(brief: str, seconds: float | None = None) -> list[dict[str, Any]]:
    """No model: her own sentences become frames (nothing added)."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?।])\s+|\n+", clean(brief, 3000)) if p.strip()][:8]
    if not parts:
        return []
    total = seconds or max(6.0, 3.0 * len(parts))
    each = round(total / len(parts), 1)
    return [{"n": i + 1, "seconds": each, "visual": p, "text": p[:120], "motion": "", "audio": ""} for i, p in enumerate(parts)]


def storyboard_seconds(frames: list[dict[str, Any]]) -> float:
    return round(sum(float(f.get("seconds") or 0) for f in frames), 1)


# ---------------------------------------------------------------- money
def gst_split(gstin: str, client_gstin: str, client_state: str = "") -> str:
    """'intra' (CGST + SGST) or 'inter' (IGST) from the two GSTIN state codes; unknown client state = intra (her state)."""
    mine = (gstin or "")[:2]
    theirs = (client_gstin or "")[:2] or (client_state or "")[:2]
    if mine and theirs and theirs.isdigit() and theirs != mine:
        return "inter"
    return "intra"


TDS_NOTE = ("TDS client kaatega, aapke bill par nahi: creative / design fees aam taur par Income-tax Act 2025 s.393(1) mein "
            "'professional fees' 10% (saal mein Rs 50,000 se upar), ya 'contract work' 1% / 2% (ek baar Rs 30,000 / saal Rs 1 lakh "
            "se upar) maana jaata hai. Kaunsa lagega, client ka CA tay karta hai; Form 26AS / AIS mein milaan kariye.")
GST_NOTE = ("GST aapke CA se pakka kariye: design / animation seva aam taur par 18% (SAC 998391 'specialty design' starter; "
            "video production / post-production SAC 9996 ke andar bhi ho sakta hai). Registration ke bina GST mat lagaiye.")
COPYRIGHT_NOTE = ("Copyright (Copyright Act 1957): freelancer ka banaya kaam ka pehla maalik banane wala hota hai (s.17), sirf paise "
                  "dene se client ka nahi hota. Client ko dena ho to likhit assignment (s.19): kaunse haq, kitne saal, kis desh mein. "
                  "Saal / desh na likha ho to kanoon 5 saal aur Bharat maanta hai (s.19(5), (6)).")
AI_NOTE = ("AI se bana / badla video (Hoola Motion, 3D, photo, studio) par 'AI-generated' label rakhiye; platform par upload karte "
           "waqt bhi batana hota hai (IT Rules 2026, 20 Feb 2026 se).")
