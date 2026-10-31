"""v0.191 HARNESS-2, part 1: step-admitted tool subsets.

The study (deepseek-harness + Claude Code) was blunt about the biggest constant tax: the FULL tool registry rides
into EVERY model call. HOOLA measured that at 384 specs / ~568 KB (v0.187 diet brought it to ~383 KB) - re-sent on
each of the up-to-24 (goal: 80) calls of a turn. On the production brain (no prompt cache) that is pure
time-to-first-token; on the Anthropic path it eats the cache.

dsh's answer is step-admitted tool subsets with deferred families + a tool search; Claude Code keeps its tool set
small and stable per session. HOOLA's version, adapted to a chat agent:

- A turn admits the tool families her words actually need (Hinglish / Hindi / English keyword router over the
  families) ON TOP of a small always-on CORE (conversation, kaam status, plan, search, memory, reminders, the
  bazar gateway to everything). The admitted set is computed ONCE per turn and stays byte-stable across all its
  steps, so the Anthropic prompt cache holds within the turn.
- `tool_search` is the escape hatch (always offered, tiny spec): the model asks for a family by need, it is
  admitted for the REST of the turn (one deliberate cache re-write), and the model sees exactly what arrived.
- A family missed by the router is never fatal: dispatch() still runs any known handler, and pakka nudges push
  the model toward tool_search. The safety valve: if the router admits an absurd share of the registry, the FULL
  set goes instead (never worse than v0.190).

Admission only changes what the model SEES. dispatch(), employee.gate, the confirm-card rules, Rokiye - all
unchanged and applied after, exactly as before. Non-owner actors (routine / staff / customer) keep the full set:
their gates already restrict them and their jobs may need anything.
"""
from __future__ import annotations

import logging
import re

from .tools import FAMILY_OF, HANDLERS, TOOLS, TOOL_LABELS

log = logging.getLogger("santosh.admit")

STATS: dict[str, int] = {"turns": 0, "full_fallback": 0, "tool_search": 0, "families_added": 0}

# The always-on set: small families every conversation needs. The unmapped base specs (WhatsApp campaigns,
# kaam_plan goal tools) ride along because admission only FILTERS mapped names - unmapped = always kept.
CORE_FAMILIES = frozenset({
    "kaam",       # kaam_status: the truth about running jobs
    "goal",       # kaam_plan: long jobs
    "bazar",      # the gateway to MCP servers + everything not built in
    "web",        # google_search / web_sources / open_website / browse_web
    "gyaan",      # her knowledge base
    "procedure",  # seekhe hue kaam
    "google",     # google_status (the one-line Google fix)
    "make",       # memory_search + make_document + photo_clean / id_photo
    "life",       # reminders, alarms, lists, profile, weather
    "maps",       # places / directions
    "file",       # file_read (attachments in chat)
    "id",         # Pehchaan Locker
    "usage",      # ai_kharcha
    "device",     # phone_health
    "docstudio",  # v0.245 doc_studio / doc_preview: a document ask in any words finds the design studio
    "data",       # v0.238 data_fetch / data_read: big data stays in a server file (never escape to the cloud PC)
    "team",       # v0.193 deploy_agents / agent_status / session_log - the agent team is a first-class tool now
    "recall",     # v0.250 haal_ki_chats: her other chats by time (one tiny spec, like Claude's recent-chats tool)
})

# Hand-written keywords per family (lowercase substrings matched against her words). Tool names add their own
# auto-keys below - this map carries the natural language the names cannot cover.
EXTRA_KEYS: dict[str, tuple[str, ...]] = {
    # v0.311 WhatsApp campaigns are a family now (they were always on): her words, or a chat that already ran one
    "campaign": ("whatsapp", "whats app", "campaign", "template", "broadcast", "lead list", "leads", "contact list",
                 "customer list", "bulk message", "opt-in", "opt in", "consent", "व्हाट्सएप", "कैंपेन"),
    # v0.245 generic verbs (bhej / send / reply / draft / label) removed: they loaded 23 mail tools for every send
    "email": ("mail", "email", "gmail", "inbox", "khat", "newsletter", "unsubscribe", "attachment",
              "fwd", "snooze", "vacation", "spam", "ईमेल", "मेल", "इनबॉक्स"),
    "gcal": ("calendar", "kalandar", "meeting", "meeeting", "event", "agenda", "slot", "schedule", "invite",
             "invitation", "rsvp", "appointment", "madh", "free busy", "milne", "मीटिंग", "कैलेंडर", "अपॉइंटमेंट",
             "बैठक"),
    "sheets": ("sheet", "excel", "spreadsheet", "csv", "row", "column"),
    "gdrive": ("google doc", "gdoc", "drive", "google sheet"),      # v0.245 'document' / 'docx' = doc_studio now
    "drive": ("drive", "folder", "storage"),
    "slides": ("slide", "ppt", "presentation", "deck"),
    "forms": ("form", "survey", "respons"),
    "photos": ("google photos", "album", "gallery"),
    "photo": ("photo", "tasveer", "image", "picture", "wish", "greeting", "फोटो", "तस्वीर"),
    "graphic": ("graphic", "banner", "poster", "logo", "thumbnail", "design", "creativ"),
    "video": ("video", "clip", "trim", "subtitle", "edit", "reel"),
    "reel": ("reel", "short", "instagram", "status video"),
    "motion": ("motion", "animat", "animate"),
    "studio": ("studio", "ai video", "video shoot"),
    # v0.259 Create Studio: song / voice-over / dubbing (the Create page names the tool; these cover her own words)
    "create": ("song", "gaana", "gaane", "jingle", "lyrics", "music studio", "voice-over", "voiceover", "voice over",
               "dub", "dubbing", "create studio", "गाना", "डब"),
    "blender": ("blender", "3d", "three d"),
    "youtube": ("youtube", "channel", "vlog", "subscriber"),
    "tv": ("tv", "channel", "dth"),
    "bt": ("bluetooth", "speaker", "music", "song", "gaana", "gaane", "volume", "ac ", "air condition", "remote",
           "ganna", "गाना", "गाने"),
    # v0.245 "pc" is not keyword-admitted any more: _pc_wanted() decides (v0.271: only her PC / Hoola's PC named)
    "operator": ("computer operator", "operator"),
    "jaanch": ("jaanch", "test karo"),
    "shop": ("order", "amazon", "flipkart", "zomato", "swiggy", "kharid", "shopping", "pizza", "grocer"),
    "mshop": ("mobile shop", "sim card", "phone repair", "phone shop"),
    "courier": ("courier", "parcel", "deliver", "track", "shipment", "speed post", "speedpost", "bluedart",
                "delhivery"),
    "india": ("holiday", "chhutti", "ifsc", "pincode", "bank holiday", "panchang", "tithi", "muhurat", "ekadashi"),
    # v0.277 IndiaMART: B2B buying / sourcing words (the SOURCING intent below carries the sentence shapes)
    "indiamart": ("indiamart", "india mart", "supplier", "manufacturer", "wholesale", "wholesaler", "exporter",
                  "distributor", "dealer", "moq", "bulk", "thok", "sourcing", "सप्लायर", "थोक", "होलसेल", "भाव",
                  "रेट"),
    "notebook": ("notebook", "notebooklm", "padhai", "study guide", "mind map", "podcast banao"),
    # v0.245 bare 'hoola' removed: she says it in every message (it loaded 35 network tools + the PC tools)
    "hoola": ("avatar", "hoola network", "samaj", "dosti", "community", "connection", "business page", "network pe"),
    "employee": ("employee", "staff", "naukar"),
    "pgdb": ("postgres", "sql", "database"),
    "publicapi": ("api",),
    "handoff": ("digilocker", "ondc", "a2a", "consent"),
    "artifact": ("artifact", "tracker", "hisaab", "calculator", "planner", "checklist", "dashboard"),
    "army": ("army", "agent army"),
    "desk": ("yaad khojo", "doc desk", "milaan"),
    "website": ("website", "web site", "site banao", "landing page", "domain"),
    "site": ("website", "web site", "site banao", "landing page", "domain"),
    "sitesup": ("site supervisor", "sitesup", "dpr", "attendance", "challan"),
    "qa": ("qa", "retest"),
    "app": ("app banao", "app design", "android app", "apk"),
    "appcheck": ("app check", "appcheck"),
    "payroll": ("payroll", "salary", "vetan", "payslip"),
    "gst": ("gst", "gstr", "gstr"),
    "audit": ("audit",),
    "compliance": ("compliance", "complianc"),
    "cosec": ("cosec", "roc", "company law"),
    "contracts": ("contract", "agreement"),
    "legalres": ("legal research", "kanoon", "case law"),
    "vakil": ("vakil", "advocate", "lawyer"),
    "notary": ("notary", "notarise", "notarize"),
    "dpo": ("dpo", "data protection", "privacy policy", "dpdp"),
    "cyber": ("cyber", "hack"),
    "itadmin": ("it admin", "itadmin", "office wifi", "office network"),
    "devops": ("devops", "deploy", "server", "uptime"),
    "dev": ("dev", "developer", "code", "bug", "software"),
    "brand": ("brand", "branding"),
    "ads": ("ads", "advertis", "meta ad", "google ad", "campaign chalao"),
    "seo": ("seo", "google rank", "search rank"),
    "social": ("social media", "instagram post", "facebook post"),
    "content": ("content", "blog", "caption", "hashtag"),
    "influencer": ("influencer", "collab", "barter"),
    "patrakar": ("patrakar", "press", "news"),
    "editdesk": ("edit desk", "editing desk"),
    "filmdesk": ("film desk", "shoot"),
    "kalam": ("kalam", "writer", "lekha"),
    "lekhak": ("lekhak", "anuvaad", "translate", "translation", "grammar", "application likh", "kruti", "affidavit",
               "अनुवाद", "आवेदन"),
    "kitab": ("kitab", "book"),
    "podcast": ("podcast",),
    "telecall": ("telecall", "cold call", "call list"),
    "callcentre": ("call centre", "callcenter", "call center", "inbound", "outbound"),
    "helpdesk": ("helpdesk", "help desk", "complaint line"),
    "seva": ("seva", "service request"),
    "aftersales": ("aftersales", "after sales", "warranty", "service due"),
    "feedback": ("feedback", "review aaya"),
    "shikayat": ("shikayat", "complaint"),
    "wapsi": ("wapsi", "return", "refund"),
    "analyst": ("p&l", "profit loss", "balance sheet", "business analysis", "trial balance"),
    "product": ("product", "catalogue", "catalog"),
    "thok": ("thok", "wholesale", "bulk order"),
    "warehouse": ("warehouse", "godam", "stock", "inventory"),
    "logistics": ("logistics", "fleet", "truck"),
    "fleet": ("fleet", "vehicle", "gaadi"),
    "drivers": ("driver", "driver"),
    "rentdesk": ("rent", "kiraya", "tenant"),
    "propagent": ("property", "propagent", "real estate", "flat"),
    "interior": ("interior", "design ghar"),
    "archassist": ("architect", "archassist", "naksha"),
    "banquet": ("banquet", "party plot", "marriage hall"),
    "caterer": ("caterer", "catering", "rasoi"),
    "eventplan": ("event", "event plan", "shaadi plan"),
    "shaadi": ("shaadi", "wedding", "sagai"),
    "homestay": ("homestay", "homestay", "stay booking"),
    "tourguide": ("tour", "trip", "ghumne", "travel plan"),
    "travel": ("travel", "ticket", "flight", "train", "bus"),
    "society": ("society", "housing society", "maintenance"),
    "salamat": ("society", "salamat"),
    "insure": ("bima", "insurance", "policy renew"),
    "loan": ("loan", "emi", "credit"),
    "chai": ("chai", "tea stall", "cafe"),
    "darzi": ("darzi", "tailor", "stitch", "silai"),
    "artistmgr": ("artist", "mehndi", "decorator", "photographer booking"),
    "photoassist": ("photo assist", "photo edit", "retouch"),
    "franchise": ("franchise", "dealership"),
    "noc": ("noc", "no objection"),
    "customs": ("customs", "import", "export doc"),
    "niryat": ("niryat", "export"),
    "askform": ("ask form", "sawaal form"),
    "a2a": ("a2a",),
    "desk2": ("desk",),
    "team": ("agents", "agent lagao", "agent banao", "team banao", "team laga", "crew", "deploy",
             "parallel", "kai agents", "multiple agents", "agents lagao", "madadgar dal", "team se karo"),
}

# words that appear inside many tool names but mean nothing on their own - never become auto-keys
_STOP = frozenset({
    "tools", "tool", "status", "result", "results", "list", "lists", "get", "set", "add", "remove", "delete",
    "update", "create", "new", "run", "find", "read", "write", "show", "dekho", "banao", "karo", "my", "all",
    "the", "and", "for", "with", "from", "into", "one", "two", "action", "item", "data", "info", "detail",
    "details", "manage", "manager", "check", "open", "close", "send", "pick", "picked", "step", "ask", "sum",
    "milaan", "khojo", "dekha", "ley", "do", "me", "up", "out", "id", "ids", "ai", "api",
})

_WORD_RE = re.compile(r"[a-z]{3,}")


def _hit(key: str, text: str) -> bool:
    """Short keys match on word boundaries only ('id' must not live inside 'video', 'app' not inside 'apple');
    longer keys stay substrings so 'mail' finds gmail and 'sheet' finds spreadsheet."""
    if len(key) <= 3:
        return re.search(r"\b" + re.escape(key) + r"\b", text) is not None
    return key in text


# v0.245 tags / name-words that are everyday words: never auto-keys ('make' loaded notebook + network + artifact,
# 'search' / 'phone' / 'report' / 'print' loaded the PC tools, 'file' loaded Drive)
_GENERIC = frozenset({
    "make", "file", "files", "life", "desk", "note", "notes", "report", "print", "phone", "search", "task", "entry",
    "photo", "video", "edit", "share", "export", "copy", "upload", "comments", "threads", "thread", "answer", "reply",
    "call", "docs", "doc", "sheet", "form", "event", "cancel", "settings", "sources", "studio", "plan", "office",
    "product", "seva", "biz", "kaam", "jaanch", "agent", "google", "website", "drive", "hoola", "app", "channel",
    "shop", "data", "team", "web", "site", "maps", "usage", "device", "goal", "procedure", "handoff", "rea", "qa",
    "dev", "chain", "deal", "market", "group", "groups", "handle", "decide", "pick", "look", "learn", "learned",
    "act", "skills", "business", "connect", "find", "me", "inbox", "send", "post", "digest", "booking", "remove",
    "detail", "action", "status", "list", "my", "chat", "config", "output", "discover", "open", "ask", "add",
    "pdf",       # making a pdf = docstudio; working ON a pdf = the "pdf work" intent
})


def _auto_keys() -> dict[str, set[str]]:
    """family -> keywords derived from its own tag + tool names (built once). v0.245: a name-word is a key only when
    it belongs to ONE family and is not an everyday word; the joined tool name ('computer operator') always is."""
    words_of: dict[str, set[str]] = {}
    for name, fam in FAMILY_OF.items():
        words_of.setdefault(fam, set()).update(_WORD_RE.findall(fam) + _WORD_RE.findall(name))
    owners: dict[str, set[str]] = {}
    for fam, ws in words_of.items():
        for w in ws:
            owners.setdefault(w, set()).add(fam)
    out: dict[str, set[str]] = {}
    for name, fam in FAMILY_OF.items():
        keys = {w for w in words_of[fam] if w not in _STOP and w not in _GENERIC and len(w) >= 3
                and len(owners.get(w, ())) == 1}
        joined = name.replace("_", " ")
        if len(joined) >= 5 and joined not in joined.split():
            keys.add(joined)
        if fam not in _GENERIC and len(fam) >= 3:
            keys.add(fam)
        out.setdefault(fam, set()).update(keys)
    return out


_AUTO = _auto_keys()


class AdmitSet:
    """The admitted set of ONE turn. Stable across the whole turn (cache discipline); `admit_family` is the
    only way it grows (tool_search mid-turn), and the next loop iteration rebuilds the spec list from it."""

    def __init__(self, settings):
        self.settings = settings
        self.families: set[str] = set(CORE_FAMILIES)
        self.extra: set[str] = set()          # tool names admitted directly (beyond their family)
        self.why: dict[str, str] = {}         # v0.245 family -> how it got in (word / intent / meaning / place)

    def admit_families(self, tags) -> list[str]:
        """Add families, return the tool names that became visible (for the tool_search answer)."""
        fresh: list[str] = []
        for tag in tags:
            tag = str(tag).strip().lower()
            if not tag or tag in self.families:
                continue
            self.families.add(tag)
            for name, f in FAMILY_OF.items():
                if f == tag and name not in self.extra:
                    fresh.append(name)
        STATS["families_added"] += len(fresh)
        return sorted(fresh)

    def _seen(self, name: str) -> bool:
        fam = FAMILY_OF.get(name)
        return fam is None or fam in self.families or name in self.extra   # v0.245 unmapped = always (as documented)

    def size(self) -> int:
        return 1 + sum(1 for t in TOOLS if self._seen(t["name"]))

    def specs(self) -> list[dict]:
        """The tool list for the model: tool_search first, then the admitted specs in the registry's own order."""
        out = [dict(TOOL_SEARCH)]
        for t in TOOLS:
            if self._seen(t["name"]):
                out.append(t)
        return out


TOOL_SEARCH = {
    "name": "tool_search",
    "description": ("Open the full toolbox: another tool family (mail, calendar, sheets, video, pc, gst, ...) "
                    "exists but is not loaded in this turn. Call this with what you need, then use the tools it "
                    "lists. It never runs anything by itself."),
    "input_schema": {"type": "object", "properties": {
        "need": {"type": "string", "description": "What the job needs, e.g. 'send an email', 'sheet update', 'gst'"}},
        "required": ["need"]},
}

_LABEL = "Tools dhoondh raha hoon"


def _match(text: str) -> set[str]:
    """Families whose keys (auto or hand-written) appear in the text. Lowercase in, family tags out."""
    hits: set[str] = set()
    for fam, keys in _AUTO.items():
        for k in keys:
            if _hit(k, text):
                hits.add(fam)
                break
    for fam, keys in EXTRA_KEYS.items():
        for k in keys:
            if _hit(k, text):
                hits.add(fam)
                break
    return hits & set(FAMILY_OF.values())   # only families that really exist in the registry


# ---------------------------------------------------------------- v0.245 SAHI AUZAAR: the right tool, every ask
# The keyword list alone routed on single words ("pdf" -> India holidays, "make" -> notebook, "hoola" -> the PC):
# the right tool was often NOT in view and the wrong one was. Two more signals now decide what Hoola sees:
#  1. INTENTS - the job TYPE in her words (a document, a data list, a web form, writing / translation...),
#  2. the PC gate - her PC / Hoola's cloud PC tools only when she names a PC or the job needs desktop software.
# Measured on app/quality/tool_asks.py (the test pins it). A meaning (embedding) router was tried and measured: the
# multilingual MiniLM found the right family in its top 3 for only 79 of 155 asks and added wrong ones, so it is not used.
_D = r"(?:pdf|पीडीएफ|report|रिपोर्ट|proposal|profile|brochure|quotation|invoice|resume|\bcv\b|presentation|\bppt|deck|" \
     r"document|dastavez|दस्तावेज़|docx|word file|excel|xlsx|spreadsheet|certificate|catalogue|letter ?head|" \
     r"\bslides?\b|स्लाइड|प्रस्ताव|बायोडाटा|printable|menu card|flyer|pamphlet|leaflet|visiting card)"
# v0.257 REVERSE-ENGINEER ANYTHING: every program / app / package / library / model / firmware file kind REA reads,
# plus the words for the job itself. Shared with agent/pick.py (a PC call for this job is refused there).
_EXT = (r"exe|dll|sys|ocx|scr|msi|msix|appx|apk|apks|xapk|apkm|aab|dex|odex|oat|ipa|dmg|pkg|app|deb|rpm|appimage|snap|"
        r"jar|war|aar|class|so|elf|ko|dylib|bin|img|hex|elf|firmware|rom|wasm|pyc|pyd|pyo|whl|egg|gguf|onnx|tflite|"
        r"pt|pth|safetensors|h5|keras|mlmodel|asar|node|nupkg|beam|db|sqlite|sqlite3|realm|ips|dtb|unitypackage|pak")
APPFILE = re.compile(r"\.(?:" + _EXT + r")\b|\b(?:exe|dll|apk|apks|xapk|ipa|jar|msi|dmg|elf|binar(?:y|ies)|firmware|"
                     r"bytecode|executable|installer|setup file|library file|gguf|onnx|tflite|asar|wasm)\b|decompil|"
                     r"disassembl|reverse[ -]?engineer|revers(?:e|ing) kar|reverce|smali|\bendpoints?\b|"
                     r"\bhardcoded\b|\bsdk\b.{0,30}(?:kaun|which|list)|\btrackers?\b.{0,30}(?:app|apk|exe)|"
                     r"(?:app|apk|program|software|game|tool|file|exe|model)\b.{0,40}(?:kaise kaam|kaise bana|andar kya|"
                     r"kya karta|kya hota|ke andar|internals?|how (?:does it|it) works?|under the hood)", re.I)
INTENTS: list[tuple[re.Pattern, tuple[str, ...], str]] = [
    # a file to MAKE (pdf / word / excel / ppt): the design studio
    (re.compile(_D, re.I), ("docstudio",), "document"),
    # work ON a pdf she has: merge / split / shrink / rotate / pages / lock
    (re.compile(r"(?:pdf|पीडीएफ)\w*.{0,70}(?:jod|merge|mila|chhot|compress|split|alag|page|rotate|ghuma|small|"
                r"lock|password|unlock|watermark|size|badi)|(?:jod|merge|chhot|compress|split|rotate).{0,30}(?:pdf|पीडीएफ)",
                re.I),
     ("india",), "pdf work"),
    # many records: a list / ranking / API / dataset -> the data desk (+ the studio to print it)
    (re.compile(r"\btop\s*\d+|\b\d{2,}\s+(?:\w+\s+){0,2}(?:ki|ka|ke|of)?\s*(?:list|price|names?|companies|repos?)|"
                r"list of|price list|github|\brepos?\b|repositor|\bapi\b|dataset|\bcsv\b|statistic|\bstats\b|"
                r"market cap|ranking|table mein|data (?:la|nikal|collect|fetch)", re.I),
     ("data", "docstudio", "publicapi"), "data"),
    # a job ON a website: forms, applications, status, downloads, bookings -> the computer operator
    (re.compile(r"form\s+(?:\w+\s+){0,2}bhar|online\s+bhar|renew\w*.{0,30}online|online\s+renew|"  # v0.331 'form online bhar do'
                r"fill (?:the |this |my )?(?:\w+ )?form|(?:website|portal|site|seva)\b.{0,40}(?:form|apply|"
                r"appointment|status|download|registration|application)|(?:apply|application|registration|appointment)"
                r".{0,40}(?:online|website|portal|site)|status check|online apply", re.I),
     ("operator",), "web job"),
    # writing / typing / translating in Indian languages
    (re.compile(r"(?:application|arzi|letter|patra|complaint|shikayat|affidavit)\s+(?:\w+\s+){0,3}likh|likh\w*\s+(?:\w+\s+)"
                r"{0,2}(?:application|letter|patra|arzi)|anuvaad|translat|grammar|marathi|tamil|telugu|bangla|bengali|"
                r"gujarati|kannada|malayalam|punjabi|odia|kruti dev|type kar|अनुवाद|आवेदन|पत्र लिख", re.I),
     ("lekhak",), "writing"),
    # money maths / trackers she opens and uses
    (re.compile(r"\bemi\b|calculator|hisaab|tracker|planner|checklist|dashboard|kitna banega|kitni banegi", re.I),
     ("artifact",), "calculator / tracker"),
    # her business numbers
    (re.compile(r"p&l|profit\s*(?:and|&)?\s*loss|balance sheet|trial balance|business analysis|ratios?", re.I),
     ("analyst",), "business numbers"),
    # REVERSE-ENGINEER ANYTHING (v0.257, owner): a program / app / package / model / firmware file to read -> REA,
    # statically, on the server; the data desk rides along for the endpoint list. Never the cloud PC.
    (APPFILE, ("rea", "data"), "reverse engineer"),
    # v0.277 a product to buy / source / price -> live IndiaMART listings (city wise)
    (re.compile(r"\b(?:rate|bhav|bhaav|daam|dam)\b|kitne ka|kitne ki|kitne mein|price of|cost of|ka price|ki price|"
                r"ke price|kaha(?:n)? (?:se )?(?:milega|milegi|milte|kharid)|where (?:can i |to )?buy|"
                r"\b(?:suppliers?|manufacturers?|wholesal\w*|exporters?|distributors?|dealers?|vendors?)\b|"
                r"\bmoq\b|\bbulk\b|\bthok\b|भाव|रेट|कितने का|थोक|सप्लायर", re.I),
     ("indiamart",), "sourcing"),
    # other avatars on the Hoola Network
    (re.compile(r"(?:ke|ki|ka|ko)\s+avatar|avatar\s+(?:ko|se)|hoola network|network pe", re.I), ("hoola",), "network"),
    # research / comparison that splits into parts -> the team (core) + the web (core); nothing extra to load
]
# desktop-software words (v0.271: they no longer bring a PC into view by themselves - only her words do)
_DESKTOP = re.compile(r"\btally\b|busy software|\bmarg\b|ffmpeg|libreoffice|pandoc|imagemagick|\bapt\b|pip install|"
                      r"printer|printout|\bprint\s+(?:kar\s+do|kar\s+dena|nikal|karwa|out)|पीसी|santosh desktop", re.I)


def _pc_wanted(text: str) -> str:
    """'place' when the PC tools belong in view, '' when they don't. v0.271 SAB SERVER PAR (owner: "WE WANT HOOLA FOR
    EVERY TASK ON SERVER ... IF SHE TELLS TO DO THE TASK ON PC THEN ONLY HE WILL DO"): only HER words naming her PC /
    Hoola's PC bring a PC into view. Desktop-software words (Tally, ffmpeg, printer ...) no longer do - for those
    Hoola works on the server or ASKS her "Yeh aapke PC pe karun?" first."""
    from . import where
    p = where.place(text)
    if p in ("pc", "hoolapc"):
        return "place"
    return ""


def route(text: str, settings=None) -> dict[str, str]:
    """family -> why, for one ask (no admission state). The single source for plan_for and the tool-choice card."""
    low = str(text or "").lower()
    why: dict[str, str] = {}
    for fam in _match(low):
        why.setdefault(fam, "word")
    for pat, fams, label in INTENTS:
        if pat.search(text or ""):
            for f in fams:
                why.setdefault(f, "intent:" + label)
    pc = _pc_wanted(text or "")
    why.pop("pc", None)
    why.pop("operator", None) if pc == "place" and not any(v.startswith("intent:web") for v in why.values()) else None
    if pc:
        why["pc"] = "place" if pc == "place" else "software"
    why = {f: w for f, w in why.items() if f in set(FAMILY_OF.values())}
    return why


def plan_for(text: str, settings, extra_text: str = "") -> AdmitSet | None:
    """The admitted set for one turn, routed on her words (+ goal steps / worker notes).
    None = admission is off or the valve tripped: caller uses the FULL registry (v0.190 behaviour)."""
    if not getattr(settings, "agent_tool_admission", True):
        return None
    adm = AdmitSet(settings)
    why = route(text, settings)
    if extra_text:
        for f, w in route(extra_text, settings).items():
            why.setdefault(f, w)
    if why:
        adm.admit_families(why)
        adm.why = why
    STATS["turns"] += 1
    if adm.size() > max(40, int(getattr(settings, "tool_admit_cap", 220))):
        STATS["full_fallback"] += 1     # router over-matched: never worse than the full registry
        return None
    return adm


_NAME_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
UNLOADED_NOTE = ("\n\nTOOLS NOT LOADED IN THIS TURN: the guide above also names {names}. They are NOT in your tool "
                 "list right now - never call them directly and never steer the job toward them. If her ask truly "
                 "needs one, call tool_search first; otherwise pick from the tools you have.")


def unloaded_note(system_text: str, adm: "AdmitSet") -> str:
    """v0.311 SAHI AUZAAR 2: the shared guide names tools of families that are not loaded (a plain 'hello' turn named
    pc_do 3x, computer_operator 4x, hoola_pc_do 2x - 24 such tools), which pulled the model toward tools it could not
    see. One honest line names them as NOT loaded. Deterministic for a given family set (the prompt cache holds)."""
    seen: list[str] = []
    for m in _NAME_RE.findall(system_text or ""):
        if m in HANDLERS and m != "tool_search" and not adm._seen(m) and m not in seen:
            seen.append(m)
    if not seen:
        return ""
    return UNLOADED_NOTE.format(names=", ".join(seen[:30]))


def sticky_families(conversation_id: str) -> set[str]:
    """v0.311 families a chat keeps once it used them, whatever her next words are: a chat with a WhatsApp campaign
    (or a lead list uploaded into it) keeps the campaign tools for "Kaisa raha?" / "Haan, sabne consent diya hai"."""
    out: set[str] = set()
    if not conversation_id:
        return out
    try:
        from sqlalchemy import select
        from ..db import Campaign, Message, session
        with session() as s:
            if s.scalars(select(Campaign.id).where(Campaign.conversation_id == conversation_id).limit(1)).first():
                out.add("campaign")
            else:
                rows = s.scalars(select(Message.display).where(Message.conversation_id == conversation_id,
                                                                Message.role == "user")
                                 .order_by(Message.id.desc()).limit(6)).all()
                low = " ".join(str(r or "") for r in rows).lower()
                if any(_hit(k, low) for k in EXTRA_KEYS["campaign"]):
                    out.add("campaign")
    except Exception:
        log.debug("sticky families failed", exc_info=True)
    return out


async def tool_search(ctx, need: str = "", **_):
    """The tool_search handler: admit the matching families for the REST of this turn, name what arrived."""
    from .tools import Ctx
    adm = getattr(ctx, "admit", None) if isinstance(ctx, Ctx) else None
    need = (need or "").strip()
    if not need:
        return {"admitted": [], "note": "Batao kya kaam karna hai - 'send an email', 'sheet update' jaisa."}
    hits = _match(need.lower())
    if not hits:   # try the words as family tags / tool names directly
        low = need.lower()
        words = set(_WORD_RE.findall(low)) | {low}
        for name, fam in FAMILY_OF.items():
            if _hit(name, low) or _hit(low, name):
                hits.add(fam)
            elif any(_hit(w, fam) or w == fam for w in words):
                hits.add(fam)
    if not hits:
        return {"admitted": [], "note": ("Is naam se koi parivar nahi mila. Kaam ka verb batao (mail, calendar, "
                                         "sheet, video, photo, pc, gst...) ya seedha tool ka naam.")}
    if adm is None:   # no turn state (admission off / direct call): names only, nothing changes
        names = sorted(n for n, f in FAMILY_OF.items() if f in hits)
        return {"admitted": names[:40], "note": "Yeh tools is turn mein loaded NAHI hain (admission off)."}
    fresh = adm.admit_families(hits)
    STATS["tool_search"] += 1
    log.info("tool_search admitted %s (%s)", ",".join(hits), ",".join(fresh[:8]))
    return {"admitted": fresh, "note": "Yeh tools ab is poori turn ke liye khul gaye - agle call se upyog karo."}


HANDLERS["tool_search"] = tool_search
TOOL_LABELS["tool_search"] = _LABEL


def stats() -> dict:
    """Diagnostics: admission + family coverage at a glance."""
    from collections import Counter
    c = Counter(FAMILY_OF.values())
    return {"registry": len(TOOLS), "core": len(CORE_FAMILIES), "families": len(c),
            "biggest": dict(c.most_common(8)), **STATS}
