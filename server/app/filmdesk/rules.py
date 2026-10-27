"""Pure rules of the Film Desk (no DB): script parsing -> scene breakdown, shot list from scenes, consent scope checks,
rights checks, release checklist per target, AI disclosure lines, CBFC / OTT ratings, hashing and cleaning.

Research (checked 23 Oct 2026; plain-words guidance, not legal advice):
  * IT (Intermediary Guidelines and Digital Media Ethics Code) Amendment Rules 2026, G.S.R. 120(E), notified 10 Feb 2026, in force
    20 Feb 2026: "synthetically generated information" (audio / visual / audio-visual made or altered by a computer resource;
    routine editing, colour, compression, translation and accessibility excluded) must carry a clear, prominent label (visible on
    video, spoken on audio) plus embedded metadata / unique identifier that is not stripped; significant social media platforms ask
    the uploader to DECLARE synthetic content and verify it; takedown 3 h on orders, 2 h for non-consensual intimate / deepfake
    imagery, user grievances 7 days (blog.ipleaders.in/it-rules-2026, dsci.in).
  * Personality rights: Delhi HC Anil Kapoor (2023), Amitabh Bachchan v Rajat Nagi CS(COMM) 819/2022, Abhishek Bachchan
    CS(COMM) 960/2025 and Aishwarya Rai CS(COMM) 956/2025 (2025: name, image, likeness, AI deepfakes, merchandise restrained),
    Nagarjuna (Sep 2025), Global Health / Dr Naresh Trehan deepfake ads (8 Jan 2025); Bombay HC Asha Bhosle v Mayk Inc
    (29 Sep 2025: AI voice clones of her voice restrained) (ssrana.in "Personality Rights and the Bachchan Cases").
    -> a real person's face / voice only with recorded consent; famous / public figures never (photogen.problem refuses too).
  * CBFC: Cinematograph (Amendment) Act 2023 + Cinematograph (Certification) Rules 2024 (Mar 2024): U, UA 7+, UA 13+, UA 16+, A,
    S; certificates perpetual (old 10-year limit removed); online process (e-Cinepramaan); only U can go on TV; MIB accessibility
    guidelines 15 Mar 2024: closed captions + audio description (+ ISL) files with the CBFC application, multi-language films in
    6 months, all theatrical feature films (>= 72 min) incl. trailers within 2 years (iprmentlaw.com/?p=7213). Theatrical = CBFC;
    OTT = IT Rules 2021 Part III code of ethics, self-classification U / U/A 7+ / 13+ / 16+ / A with content descriptors, parental
    lock for 13+ and above, three-tier grievance (Lok Sabha reply 17 Dec 2025, latestly.com).
  * YouTube "altered or synthetic content" (Studio > Attributes > AI use): realistic footage, real people saying / doing things
    they didn't, AI music / cloned real voices must be declared; clearly unreal / animated content, scripts, captions, own-voice
    dubbing exempt; since 27 May 2026 undeclared photorealistic AI is auto-labelled, label below the player (Shorts overlay);
    repeated non-disclosure -> label forced / removal / YPP suspension (air.io, 2026).
  * Music: IPRS (registered society: musical + literary works) is separate from sound-recording rights; PPL re-registered under
    s.33(3) on 11 Jun 2026; Novex not registered (Bombay vs Madras HC split); sync right flows from the reproduction right
    (s.14) and is licensed by the owner / label (ssrana.in music licensing 2025-26). Copyright Act 1957: producer = author of a
    cinematograph film (s.2(d)(v)); work for hire s.17; assignment in writing s.19; performers' rights s.38-38B.
  * Filming money: the AI shots' price comes ONLY from the studio engine's estimate and is approved on the studio's own card
    (her tap); this desk never spends.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

FORMATS = {
    "short": {"label": "Short film", "aspect": "16:9", "max_s": 1800},
    "reel": {"label": "Reel / Short", "aspect": "9:16", "max_s": 90},
    "ad": {"label": "Ad film", "aspect": "16:9", "max_s": 120},
    "music_video": {"label": "Music video", "aspect": "16:9", "max_s": 420},
    "web_episode": {"label": "Web series episode", "aspect": "16:9", "max_s": 3600},
    "feature": {"label": "Feature film", "aspect": "16:9", "max_s": 12000},
    "documentary": {"label": "Documentary", "aspect": "16:9", "max_s": 7200},
    "explainer": {"label": "Explainer", "aspect": "16:9", "max_s": 600},
}
TARGETS = {"youtube": "YouTube", "instagram": "Instagram / Facebook", "ott": "OTT platform", "festival": "Film festival",
           "theatrical": "Cinema hall (theatrical)", "whatsapp": "WhatsApp / own use", "tv": "TV broadcast"}
RATINGS = ("U", "UA7", "UA13", "UA16", "A", "S")
RATING_LABEL = {"U": "U", "UA7": "UA 7+", "UA13": "UA 13+", "UA16": "UA 16+", "A": "A (adults)", "S": "S (special audience)"}
STATUS = ("idea", "script", "breakdown", "shots", "storyboard", "production", "post", "release_ready", "released")
USES = ("ai_likeness", "ai_voice", "real_footage", "real_voice", "name", "promo")
USE_LABEL = {"ai_likeness": "AI se chehra / roop", "ai_voice": "AI se awaaz", "real_footage": "Asli shooting", "real_voice":
             "Asli recording", "name": "Naam / credit", "promo": "Promo / trailer"}
CONSENT_HOW = ("signed_form", "video", "audio", "email", "written")
RIGHT_KINDS = ("music", "song", "voice", "stock", "font", "script", "lyrics", "footage", "artwork", "ai_model")
LICENCES = ("own", "commissioned", "licensed", "royalty_free", "ai_generated", "public_domain")
ROLES = ("actor", "voice", "subject", "crew", "writer", "composer", "singer", "other")
SAC_FILM = "999612"     # motion picture / video production services (GST 18%, her CA confirms)

_HEAD = re.compile(r"^\s*(?:\d+[.)]?\s*)?(INT\.?/EXT\.?|EXT\.?/INT\.?|I/E\.?|INT\.?|EXT\.?)\s+(.+)$", re.I)
_SCENE_WORD = re.compile(r"^\s*(?:scene|sc\.?|drishya|दृश्य|सीन|प्रसंग)\s*[-#:]?\s*(\d+)\b[\s.:\-–]*(.*)$", re.I)
_TIME = {"day": ("day", "din", "दिन", "morning", "subah", "सुबह", "afternoon", "dopahar"),
         "night": ("night", "raat", "रात", "evening", "shaam", "शाम", "dusk", "sham")}
_SPEAKER_COLON = re.compile(r"^\s*([A-Za-zऀ-ॿ][\wऀ-ॿ .']{0,28}?)\s*(?:\(([^)]{0,40})\))?\s*[:：]\s*(.+)$")
_CAPS_NAME = re.compile(r"^\s*([A-Z][A-Z .']{1,28})(?:\s*\(([^)]{0,30})\))?\s*$")
_NOT_NAMES = {"INT", "EXT", "CUT TO", "FADE IN", "FADE OUT", "DISSOLVE TO", "THE END", "CONTINUED", "SCENE", "TITLE", "SUPER",
              "MONTAGE", "BACK TO", "LATER", "INTERCUT", "SMASH CUT"}


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 500) -> str:
    """Her / outside words: secrets never kept (OTP / PIN / password values, card-like and Aadhaar-like numbers)."""
    t = str(text or "")
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


def mask_phone(p: str) -> str:
    return f"XXXXXX{p[-4:]}" if p else ""


def fmt(f: str) -> str:
    f = (f or "").strip().lower().replace(" ", "_").replace("-", "_")
    alias = {"film": "short", "short_film": "short", "shorts": "reel", "ad_film": "ad", "advert": "ad", "commercial": "ad",
             "song": "music_video", "episode": "web_episode", "series": "web_episode", "movie": "feature", "docu": "documentary"}
    f = alias.get(f, f)
    return f if f in FORMATS else "short"


def targets_of(v: Any) -> list[str]:
    items = v if isinstance(v, list) else re.split(r"[,/ ]+", str(v or ""))
    alias = {"yt": "youtube", "insta": "instagram", "facebook": "instagram", "reels": "instagram", "netflix": "ott",
             "prime": "ott", "jiohotstar": "ott", "cinema": "theatrical", "theatre": "theatrical", "theater": "theatrical",
             "film_festival": "festival", "fest": "festival", "broadcast": "tv"}
    out: list[str] = []
    for x in items:
        k = alias.get(str(x).strip().lower(), str(x).strip().lower())
        if k in TARGETS and k not in out:
            out.append(k)
    return out


def rating(v: Any) -> str:
    s = re.sub(r"[\s/+\-]", "", str(v or "")).upper()
    s = {"UA": "UA13", "U/A": "UA13", "UA7PLUS": "UA7", "ADULT": "A", "ADULTS": "A"}.get(s, s)
    return s if s in RATINGS else ""


# ---------------------------------------------------------------- script -> scenes
def _time_of(text: str) -> str:
    t = text.lower()
    for k, words in _TIME.items():
        if any(re.search(rf"(?<![\wऀ-ॿ]){re.escape(w)}(?![\wऀ-ॿ])", t) for w in words):
            return k
    return ""


def _place(text: str) -> tuple[str, str]:
    """'INT. KITCHEN - NIGHT' -> ('int', 'KITCHEN')."""
    m = _HEAD.match(text)
    if m:
        ie = m.group(1).upper().rstrip(".")
        ie = "int_ext" if "/" in ie else ie.lower()
        place = re.split(r"\s+[-–—]\s+", m.group(2).strip())[0]
        return ie, place.strip(" .")[:80]
    return "", re.split(r"\s+[-–—]\s+", text.strip())[0].strip(" .")[:80]


def parse_script(text: str) -> list[dict[str, Any]]:
    """Scenes from a screenplay or a plain Hinglish script: headings (INT./EXT., Scene 3, Drishya 2, दृश्य 4), speakers
    ('NAME' on its own line or 'Name: line'), action lines. Seconds = dialogue words / 2.5 + action words / 3 (min 4)."""
    lines = [ln.rstrip() for ln in str(text or "").replace("\r", "").split("\n")]
    scenes: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None

    def start(heading: str) -> dict[str, Any]:
        ie, place = _place(heading)
        return {"heading": heading.strip()[:120], "int_ext": ie, "place": place, "time": _time_of(heading),
                "action": [], "dialogue": [], "characters": []}

    pending_speaker = ""
    for ln in lines:
        s = ln.strip()
        if not s:
            pending_speaker = ""
            continue
        if _HEAD.match(s) or _SCENE_WORD.match(s):
            if cur:
                scenes.append(cur)
            m = _SCENE_WORD.match(s)
            cur = start(m.group(2) or s if m else s)
            if m and not cur["heading"]:
                cur["heading"] = s[:120]
            pending_speaker = ""
            continue
        if cur is None:
            cur = start("Scene 1")
        m = _CAPS_NAME.match(s)
        if m and m.group(1).strip() not in _NOT_NAMES and len(s.split()) <= 4 and not s.endswith("."):
            pending_speaker = m.group(1).strip().title()
            if pending_speaker not in cur["characters"]:
                cur["characters"].append(pending_speaker)
            continue
        m = _SPEAKER_COLON.match(s)
        if m and len(m.group(1).split()) <= 3 and m.group(1).strip().upper() not in _NOT_NAMES:
            who = m.group(1).strip().title()
            cur["dialogue"].append({"who": who, "line": m.group(3).strip()[:400]})
            if who not in cur["characters"]:
                cur["characters"].append(who)
            pending_speaker = ""
            continue
        if pending_speaker:
            cur["dialogue"].append({"who": pending_speaker, "line": s[:400]})
            continue
        cur["action"].append(s[:400])
    if cur and (cur["action"] or cur["dialogue"] or scenes == []):
        scenes.append(cur)
    out = []
    for i, sc in enumerate(scenes, 1):
        dw = sum(len(d["line"].split()) for d in sc["dialogue"])
        aw = sum(len(a.split()) for a in sc["action"])
        sec = max(4, int(round(dw / 2.5 + aw / 3.0)))
        if not sc["time"]:
            sc["time"] = _time_of(" ".join(sc["action"][:2]))
        out.append({**sc, "n": i, "id": f"sc{i}", "seconds": sec, "words": dw + aw})
    return out


def breakdown_summary(scenes: list[dict]) -> dict[str, Any]:
    chars: dict[str, int] = {}
    places: dict[str, int] = {}
    for sc in scenes:
        for c in sc.get("characters") or []:
            chars[c] = chars.get(c, 0) + 1
        p = sc.get("place") or ""
        if p:
            places[p] = places.get(p, 0) + 1
    return {"scenes": len(scenes), "seconds": sum(int(s.get("seconds") or 0) for s in scenes),
            "characters": [{"name": k, "scenes": v} for k, v in sorted(chars.items(), key=lambda x: -x[1])],
            "places": [{"place": k, "scenes": v} for k, v in sorted(places.items(), key=lambda x: -x[1])],
            "night": sum(1 for s in scenes if s.get("time") == "night")}


# ---------------------------------------------------------------- scenes -> shots (code fallback)
def shots_from_scene(sc: dict[str, Any], style_hint: str = "") -> list[dict[str, Any]]:
    """An establishing shot + one shot per dialogue beat (max 6), 4-10 s each, cameras from the studio's list."""
    place = sc.get("place") or "the place"
    tod = {"day": "daylight", "night": "night, practical lights"}.get(sc.get("time") or "", "soft light")
    act = (sc.get("action") or [""])[0]
    base = f"{place}, {tod}" + (f". {style_hint}" if style_hint else "")
    shots = [{"prompt": f"Wide establishing view of {base}. {act}".strip()[:400], "camera": "wide", "duration": 5,
              "characters": [], "dialogue": None, "speaker": None, "caption": ""}]
    beats = (sc.get("dialogue") or [])[:5]
    cams = ["close_up", "dolly_in", "static", "close_up", "tracking"]
    for i, d in enumerate(beats):
        words = len(d["line"].split())
        shots.append({"prompt": f"{d['who']} speaks in {place}, {tod}; natural expression, cinematic framing."[:400],
                      "camera": cams[i % len(cams)], "duration": max(4, min(10, int(round(words / 2.5)) + 2)),
                      "characters": [d["who"]], "dialogue": d["line"][:300], "speaker": d["who"], "caption": ""})
    if len(shots) == 1 and len(sc.get("action") or []) > 1:
        shots.append({"prompt": f"{sc['action'][1]} ({place}, {tod})"[:400], "camera": "tracking", "duration": 6,
                      "characters": list(sc.get("characters") or [])[:2], "dialogue": None, "speaker": None, "caption": ""})
    return shots


# ---------------------------------------------------------------- consent
def consent_problem(person: dict[str, Any], use: str, today: str) -> str:
    """'' when this person's recorded consent covers `use` today, else the plain reason."""
    if not person.get("real"):
        return ""
    if person.get("public_figure"):
        return (f"{person.get('name')}: jaane-maane log (neta / actor / khiladi) ka chehra ya awaaz AI se nahi banta "
                "(personality rights; Delhi / Bombay HC 2023-25). Unki likhit licence + vakil ki salah ke bina nahi.")
    c = person.get("consent") or {}
    st = c.get("status") or "none"
    if st == "withdrawn":
        return f"{person.get('name')} ne ijazat wapas le li hai ({c.get('withdrawn_at', '')[:10]}): unka chehra / awaaz ab nahi."
    if st != "recorded":
        return f"{person.get('name')} ki ijazat (consent) darj nahi hai: pehle unka sign kiya form / video / audio record kijiye."
    if person.get("minor") and not c.get("guardian"):
        return f"{person.get('name')} nabalig hain: mata-pita / guardian ki ijazat chahiye."
    if use not in (c.get("uses") or []):
        return f"{person.get('name')} ki ijazat mein '{USE_LABEL.get(use, use)}' shaamil nahi hai."
    until = c.get("until") or ""
    if until and until < today:
        return f"{person.get('name')} ki ijazat {until} ko khatam ho gayi."
    return ""


# ---------------------------------------------------------------- rights
def rights_problem(r: dict[str, Any], targets: list[str], today: str) -> str:
    lic = r.get("licence") or ""
    if lic not in LICENCES:
        return f"{r.get('title')}: licence ka prakaar nahi likha."
    if lic in ("licensed", "commissioned") and not r.get("proof"):
        return f"{r.get('title')}: licence / agreement ka saboot (file) nahi juda."
    if lic == "licensed":
        plats = r.get("platforms") or []
        miss = [TARGETS[t] for t in targets if t != "whatsapp" and plats and "all" not in plats and t not in plats]
        if miss:
            return f"{r.get('title')}: licence in jagah ke liye nahi: {', '.join(miss)}."
        if r.get("kind") in ("music", "song") and not r.get("sync"):
            return f"{r.get('title')}: gaane ko video ke saath jodne (sync) ki ijazat licence mein nahi likhi."
    until = r.get("until") or ""
    if until and until < today:
        return f"{r.get('title')}: licence {until} ko khatam."
    return ""


# ---------------------------------------------------------------- disclosure + release checklist
DISCLOSURE = {
    "hi": "इस वीडियो के कुछ दृश्य / आवाज़ें AI से बनाई गई हैं (AI-generated).",
    "mr": "या व्हिडिओमधील काही दृश्ये / आवाज AI ने तयार केले आहेत (AI-generated).",
    "en": "This video contains scenes / voices made with AI (AI-generated).",
    "hinglish": "Is video ke kuch drishya / awaaz AI se bane hain (AI-generated).",
}


def lang_key(language: str) -> str:
    l = (language or "").lower()
    if l.startswith("mar") or l == "mr":
        return "mr"
    if l.startswith("eng") or l == "en":
        return "en"
    if "hinglish" in l:
        return "hinglish"
    return "hi"


def disclosure(language: str, targets: list[str]) -> dict[str, Any]:
    k = lang_key(language)
    out = {"on_screen": "AI-generated · Hoola (studio label, hamesha on)", "description_line": DISCLOSURE[k],
           "english": DISCLOSURE["en"], "steps": []}
    if "youtube" in targets:
        out["steps"].append("YouTube Studio > upload > Details > 'Altered or synthetic content' (AI use) = Haan. Label player ke "
                            "neeche / Shorts par dikhega; na batane par YouTube khud label laga sakta hai.")
    if "instagram" in targets:
        out["steps"].append("Instagram / Facebook par post karte waqt 'AI info' / AI label on kijiye.")
    if any(t in targets for t in ("ott", "festival", "theatrical", "tv")):
        out["steps"].append("Credits / opening card mein AI ka zikr aur metadata mein AI-generated likhiye (IT Rules 2026).")
    return out


def checklist(targets: list[str], fmt_key: str, ai_used: bool) -> list[dict[str, Any]]:
    """Release checklist items per target. key, label, why, auto (checked by code) or manual (she ticks)."""
    it: list[dict[str, Any]] = [
        {"key": "consents", "label": "Har asli insaan ki ijazat darj (chehra / awaaz)", "auto": True,
         "why": "Personality rights + DPDP: bina ijazat chehra / awaaz istemaal nahi."},
        {"key": "rights", "label": "Gaana / awaaz / stock / font sab ke licence", "auto": True,
         "why": "Copyright Act 1957: sync / reproduction ki ijazat owner se."},
        {"key": "final_video", "label": "Final video studio se jud gaya", "auto": True, "why": "Release sirf final file se."},
        {"key": "credits", "label": "Credits (cast, crew, music, AI tools) likhe", "auto": False,
         "why": "Kalakaaron ka naam, licence ki shart."},
    ]
    if ai_used:
        it.append({"key": "disclosure", "label": "AI label + description line taiyaar", "auto": True,
                   "why": "IT Rules 2026: AI se bani video par saaf label + metadata."})
    if "youtube" in targets:
        it += [{"key": "yt_altered", "label": "YouTube: 'altered or synthetic content' Haan", "auto": False,
                "why": "YouTube disclosure niyam."},
               {"key": "yt_kids", "label": "YouTube: 'Made for kids' sahi chuna", "auto": False, "why": "COPPA / YouTube niyam."}]
    if "instagram" in targets:
        it.append({"key": "ig_ai", "label": "Instagram / Facebook: AI label on", "auto": False, "why": "Meta AI info label."})
    if "ott" in targets:
        it += [{"key": "ott_rating", "label": "OTT rating (U / UA 7+ / 13+ / 16+ / A) + content descriptors", "auto": True,
                "why": "IT Rules 2021 Part III code of ethics."},
               {"key": "subtitles", "label": "Subtitles / captions file", "auto": False, "why": "OTT delivery spec."}]
    if "festival" in targets:
        it += [{"key": "fest_rules", "label": "Festival ke niyam padhe (premiere status, length, AI policy)", "auto": False,
                "why": "Har festival ki apni shart."},
               {"key": "eng_subs", "label": "English subtitles", "auto": False, "why": "Zyadatar festival maangte hain."}]
    if "theatrical" in targets:
        it += [{"key": "cbfc", "label": "CBFC certificate (category + number) darj", "auto": True,
                "why": "Cinema hall mein bina certificate film nahi chal sakti (Cinematograph Act 1952)."},
               {"key": "access", "label": "Closed captions + audio description files (MIB 15 Mar 2024)", "auto": False,
                "why": "Theatrical feature film ke liye accessibility files CBFC application ke saath."}]
    if "tv" in targets:
        it.append({"key": "tv_u", "label": "TV ke liye U certificate", "auto": True, "why": "TV par sirf U certificate wali film."})
    return it


CBFC_NOTE = ("Cinema hall release ke liye CBFC certificate zaroori hai (Cinematograph Act 1952; Amendment Act 2023 + Certification "
             "Rules 2024): category U / UA 7+ / UA 13+ / UA 16+ / A / S, certificate ab hamesha ke liye valid, application online "
             "(e-Cinepramaan portal). Feature film (72 min+) ke saath closed captions + audio description files (MIB accessibility "
             "guidelines, 15 Mar 2024). TV par sirf U. OTT par CBFC nahi, IT Rules 2021 ka code of ethics (self-classification). "
             "Application aap / aapke producer khud bharte hain; Hoola portal par kuch nahi bharta.")


def ai_used(shots: list[dict]) -> bool:
    return bool(shots)


_GENERIC = re.compile(r"\b(actor|actress|celebrity|cricketer|politician|prime minister|chief minister|famous person)s?\b", re.I)


def story_problem(text: str) -> str:
    """A fictional story may have 'an actor' or 'a politician' as a character; what is refused is a NAMED real / famous
    person, face swaps / deepfakes, sexual content, fake documents and protected emblems (photogen.problem)."""
    from ..photogen import problem
    t = _GENERIC.sub("character", str(text or ""))
    why = problem(t) if t.strip() else ""
    return "" if why.startswith("Kya banana hai") else why
