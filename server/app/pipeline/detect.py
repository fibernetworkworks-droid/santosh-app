"""P1 DETECT (plan sections 2 + 5.1): the kind of work + the language of a ONE-part ask, read by code in
milliseconds. An ask with several parts is reported as such (`parts` > 1) - the LOW planner splits it in P3.

Pure: the same words + the same attachments always give the same answer. Order matters: the first rule that fits wins
(what she attached outranks what she wrote; making a file outranks reading one).
"""
from __future__ import annotations

import re
from typing import Any

# --------------------------------------------------------------------------- language
SCRIPTS = [  # (language, first char, last char) - Devanagari is read as Hindi unless Marathi words say otherwise
    ("bn", "ঀ", "৿"), ("pa", "਀", "੿"), ("gu", "઀", "૿"), ("or", "଀", "୿"),
    ("ta", "஀", "௿"), ("te", "ఀ", "౿"), ("kn", "ಀ", "೿"), ("ml", "ഀ", "ൿ"),
    ("hi", "ऀ", "ॿ"), ("ur", "؀", "ۿ"), ("zh", "一", "鿿"), ("ja", "぀", "ヿ"),
    ("ko", "가", "힯"), ("ru", "Ѐ", "ӿ"), ("ar", "ݐ", "ݿ"),
]
NAMED = {
    "hindi": "hi", "marathi": "mr", "bengali": "bn", "bangla": "bn", "tamil": "ta", "telugu": "te", "kannada": "kn",
    "malayalam": "ml", "gujarati": "gu", "punjabi": "pa", "odia": "or", "oriya": "or", "urdu": "ur",
    "assamese": "as", "spanish": "es", "french": "fr", "german": "de", "chinese": "zh", "japanese": "ja",
    "korean": "ko", "russian": "ru", "polish": "pl", "arabic": "ar", "portuguese": "pt", "italian": "it",
    "english": "en", "hinglish": "hinglish",
}
# the pooled board for a language (feed's `by_language` keys)
BOARD_LANG = {"es": "spanish", "zh": "chinese", "fr": "french", "de": "german", "ja": "japanese", "ko": "korean",
              "ru": "russian", "pl": "polish"}
MARATHI = re.compile(r"(आहे|आहेत|नाही|करा|मला|तुम्ही|काय)")
HINGLISH = re.compile(r"(?i)\b(hai|hain|kya|karo|kar|kijiye|mujhe|mera|meri|mere|aap|nahi|kaise|kaisa|kaisi|kitna|"
                      r"kitne|bata\w*|chahiye|banao|bana|likho|bhejo|abhi|kal|wala|wali|ka|ke|ki|ko|mein|rahega|"
                      r"raha|rahi|hoga|dijiye|aur|bhi|yeh|woh|kyun|kab|kahan)\b")
NAME_IN = re.compile(r"(?i)\b(?:in|into|mein|me)\s+([a-z]+)\b|\b([a-z]+)\s+(?:mein|me|main)\b")


def language(text: str) -> str:
    """The language she wants the answer in: a language she names ('Hindi mein likho', 'in Tamil') wins, then her
    script, then Hinglish words; else English."""
    t = str(text or "")
    for m in NAME_IN.finditer(t):
        for g in m.groups():
            if g and g.lower() in NAMED:
                return NAMED[g.lower()]
    counts: dict[str, int] = {}
    for ch in t:
        for lang, a, b in SCRIPTS:
            if a <= ch <= b:
                counts[lang] = counts.get(lang, 0) + 1
                break
    if counts:
        lang = max(sorted(counts), key=lambda k: counts[k])
        if lang == "hi" and MARATHI.search(t):
            return "mr"
        return lang
    return "hinglish" if len(HINGLISH.findall(t)) >= 2 else "en"


# --------------------------------------------------------------------------- kind of work
R = lambda p: re.compile(p, re.I)  # noqa: E731
EDIT_IMG = R(r"\b(edit|badlo|change|hata\w*|remove|background|bg|crop|colou?r|retouch|fix (?:this|the) (?:photo|image|picture))\b")
MAKE_IMG = R(r"\b(image|picture|photo|poster|logo|thumbnail|banner|illustration|drawing|tasveer|chitra)\b.*\b(bana\w*|"
             r"make|create|generate|draw|design)\b|\b(bana\w*|make|create|generate|draw|design)\b.*\b(image|picture|photo|"
             r"poster|logo|thumbnail|banner|illustration|drawing|tasveer)\b")
MAKE_VIDEO = R(r"\b(video|reel|clip|short film|animation)\b.*\b(bana\w*|make|create|generate)\b|\b(bana\w*|make|"
               r"create|generate)\b.*\b(video|reel|clip|animation)\b|\b(?:a|an|ek)\s+(?:\d+\s*(?:s|sec|second)\w*\s+)?"
               r"(?:short\s+)?(?:video|reel|clip|animation)\b")
MAKE_MUSIC = R(r"\b(song|gaana|gana|music|jingle|tune|beat|background score)\b.*\b(bana\w*|make|create|compose|"
               r"generate)\b|\b(bana\w*|make|create|compose|generate)\b.*\b(song|gaana|music|jingle|tune)\b")
SPEAK = R(r"\b(voice ?over|read (?:it )?aloud|padh ?kar sunao|bol ?kar sunao|audio bana\w*|text to speech|tts|"
          r"awaaz mein|narrat\w*)\b")
TRANSCRIBE = R(r"\b(transcri\w*|likh ?kar do|text mein|subtitle\w*|caption\w*)\b")
TRANSLATE = R(r"\b(translat\w*|anuvad|anuvaad|tarjuma)\b|\b(?:in|into|mein|me)\s+(?:hindi|marathi|english|tamil|"
              r"telugu|kannada|bengali|gujarati|punjabi|spanish|french|german|arabic|urdu)\s+(?:kar\w*|convert|badlo)\b")
SUMMARISE = R(r"\b(summar\w*|saar|saransh|tl;?dr|short mein bata\w*|chhota kar\w*|key points|main points|nichod)\b")
EXTRACT = R(r"\b(extract|nikaal\w*|nikal\w*|pull out|list (?:all|the|every)|table (?:bana\w*|mein)|in a table|"
            r"fields?|columns?|rows?|json|csv)\b")
CODE = R(r"\b(code|function|script|bug|repo|pull request|\bpr\b|python|javascript|typescript|dart|kotlin|sql|regex|"
         r"api endpoint|stack ?trace|traceback|compile|refactor|unit test)\b")
CODE_SMALL = R(r"\b(script|snippet|regex|function|formula|one.liner|chhota code|small code|sql query)\b")
RESEARCH = R(r"\b(research|find out|pata (?:karo|lagao)|dhoondh\w*|search (?:for|the web)|latest|news|sources?|"
             r"compare\w*|competitors?|top \d+)\b")
WRITE_DOC = R(r"\b(report|letter|article|essay|blog|story|kahani|speech|proposal|email|notice|application|patra|"
              r"chitthi)\b.*\b(likh\w*|write|draft|prepare)\b|\b(likh\w*|write|draft|prepare)\b.*\b(report|letter|"
              r"article|essay|blog|story|kahani|speech|proposal|email|notice|application|patra|chitthi)\b")
WRITE = R(r"\b(report|letter|article|essay|blog|story|kahani|script|speech|proposal|email|mail|post|caption|"
          r"description|bio|resume|cv|notice|application|patra|chitthi)\b.*\b(likh\w*|write|draft|bana\w*|prepare|"
          r"create)\b|\b(likh\w*|write|draft|prepare)\b")
FACTS = R(r"\b(what is the|kab (?:hua|tha|hai)|when (?:was|did|is)|who (?:is|was)|kaun (?:hai|tha)|capital of|"
          r"population|founded|exact (?:date|number|figure)|fact)\b")
TOOLS = R(r"^\s*(?:hoola[,\s]+)?(?:send|bhej\w*|remind|yaad dila\w*|alarm|book|order|mangwa\w*|kholo|open|call|share|"
          r"delete|hata\w*|schedule|set (?:a|an|the)|mail kar\w*|whatsapp)\b|\b(bhej do|bhej dijiye|send it|"
          r"book kar\w*|remind me|remind kar\w*|yaad dila\w*|reminder (?:laga|set)\w*|alarm laga\w*)\b")
PARTS = re.compile(r"(?i)(?:,\s*(?:aur|and|then|phir)\b|\b(?:and then|phir|uske baad|then|also|aur saath)\b|;|\n\s*"
                   r"(?:[-*•]|\d+[.)])\s)")


def _att_kind(att: dict) -> str:
    t = str(att.get("type") or att.get("mime") or att.get("name") or "").lower()
    if t.startswith("image") or t.endswith((".png", ".jpg", ".jpeg", ".webp", ".heic", ".gif")):
        return "image"
    if "pdf" in t or t.endswith((".pdf", ".docx", ".doc", ".xlsx", ".pptx")):
        return "pdf"
    if t.startswith("audio") or t.endswith((".mp3", ".wav", ".m4a", ".ogg", ".opus", ".aac")):
        return "audio"
    if t.startswith("video") or t.endswith((".mp4", ".mov", ".webm", ".mkv")):
        return "video"
    return "file"


def parts_count(text: str) -> int:
    return min(1 + len(PARTS.findall(str(text or ""))), 9)


def kind(text: str, attachments: list[dict] | None = None, surface: str = "chat",
         input_words: int = 0) -> dict[str, Any]:
    """{kind, language, parts, why} for one ask. `surface` 'code' = Hoola Code (a code part there is `code`)."""
    t = str(text or "").strip()
    lang = language(t)
    atts = [_att_kind(a) for a in (attachments or [])]
    n = parts_count(t)

    def out(k: str, why: str) -> dict[str, Any]:
        if k == "write" and lang not in ("en", "hinglish"):
            k, why = "write.lang", why + f" in {lang}"
        if k == "speech.in" and lang in INDIAN_SPEECH:
            k = "speech.in.indian"
        if k == "speech.out" and lang in INDIAN_SPEECH:
            k = "speech.out.indian"
        return {"kind": k, "language": lang, "parts": n, "why": why, "attachments": atts}

    if surface == "code":
        return out("code", "Hoola Code session")
    if "image" in atts:
        if EDIT_IMG.search(t) or MAKE_IMG.search(t):
            return out("image.edit", "a picture attached with an edit ask")
        return out("read.image", "a picture attached")
    if "audio" in atts:
        return out("speech.in", "a recording attached")
    if "pdf" in atts or "file" in atts:
        if SUMMARISE.search(t):
            return out("summarise", "a document attached to sum up")
        if EXTRACT.search(t):
            return out("extract", "a document attached to pull fields from")
        return out("read.pdf", "a document attached")
    if MAKE_VIDEO.search(t):
        return out("video.make", "asks for a video")
    if MAKE_MUSIC.search(t):
        return out("music.make", "asks for music")
    if MAKE_IMG.search(t):
        return out("image.make", "asks for a picture")
    if SPEAK.search(t):
        return out("speech.out", "asks for speech")
    if TOOLS.search(t):
        return out("tools", "an action (send / remind / book / open ...)")
    if TRANSLATE.search(t):
        return out("translate", "asks for a translation")
    if SUMMARISE.search(t):
        return out("summarise", "asks for a summary")
    if CODE.search(t):
        return out("code.small" if CODE_SMALL.search(t) or len(t.split()) < 40 else "code", "about code")
    if WRITE_DOC.search(t):
        return out("write", "asks for a piece of writing")
    if RESEARCH.search(t):
        return out("research", "needs finding things out")
    if max(input_words, len(t.split())) >= 3000:
        return out("read.long", "a very long text")
    if EXTRACT.search(t):
        return out("extract", "pull fields / rows into a shape")
    if WRITE.search(t):
        return out("write", "asks for writing")
    if FACTS.search(t):
        return out("facts", "a factual question")
    try:
        from ..agent import hard as H
        if H.assess(t).get("hard"):
            return out("reason", "a hard reasoning ask")
    except Exception:   # noqa: BLE001
        pass
    return out("chat", "a plain message")


INDIAN_SPEECH = {"hi", "mr", "bn", "ta", "te", "kn", "ml", "gu", "pa", "or", "ur", "as", "hinglish"}
