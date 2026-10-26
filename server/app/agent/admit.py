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
})

# Hand-written keywords per family (lowercase substrings matched against her words). Tool names add their own
# auto-keys below - this map carries the natural language the names cannot cover.
EXTRA_KEYS: dict[str, tuple[str, ...]] = {
    "email": ("mail", "email", "gmail", "inbox", "khat", "patra", "newsletter", "unsubscribe", "attachment",
              "attach", "forward", "fwd", "snooze", "vacation", "label", "spam", "draft", "bhej", "send", "reply"),
    "gcal": ("calendar", "kalandar", "meeting", "meeeting", "event", "agenda", "slot", "schedule", "invite",
             "invitation", "rsvp", "appointment", "madh", "free busy", "milne"),
    "sheets": ("sheet", "excel", "spreadsheet", "csv", "row", "column"),
    "gdrive": ("doc", "document", "docx", "word file", "padh"),
    "drive": ("drive", "folder", "upload", "storage", "bhej", "send"),
    "slides": ("slide", "ppt", "presentation", "deck"),
    "forms": ("form", "survey", "respons"),
    "photos": ("photo", "photo", "tasveer", "image", "picture", "album", "pic"),
    "photo": ("photo", "photo", "tasveer", "image", "picture", "banao", "generate"),
    "graphic": ("graphic", "banner", "poster", "logo", "thumbnail", "design", "creativ"),
    "video": ("video", "clip", "trim", "subtitle", "edit", "reel"),
    "reel": ("reel", "short", "instagram", "status video"),
    "motion": ("motion", "animat", "animate"),
    "studio": ("studio", "ai video", "video shoot"),
    "blender": ("blender", "3d", "three d"),
    "youtube": ("youtube", "channel", "vlog", "subscriber"),
    "tv": ("tv", "channel", "dth"),
    "bt": ("bluetooth", "speaker", "music", "song", "gaana", "ac ", "air condition", "remote", "ganna"),
    "pc": ("pc", "laptop", "computer", "browser", "screenshot", "tally", "print", "krom", "mera pc"),
    "operator": ("computer operator", "operator"),
    "jaanch": ("jaanch", "test karo"),
    "shop": ("order", "amazon", "flipkart", "zomato", "swiggy", "kharid", "shopping", "pizza", "grocer"),
    "mshop": ("mobile", "sim", "repair", "phone shop"),
    "courier": ("courier", "parcel", "deliver", "track", "shipment", "speed post", "speedpost", "bluedart",
                "delhivery"),
    "india": ("pdf", "india", "holiday", "chhutti", "ifsc", "pincode", "bank holiday", "govt"),
    "notebook": ("notebook", "note"),
    "hoola": ("hoola", "samaj", "dosti", "community", "deal", "market", "booking", "group", "connection",
              "connection", "post karo", "business page"),
    "employee": ("employee", "staff", "naukar"),
    "pgdb": ("postgres", "sql", "database"),
    "publicapi": ("api",),
    "handoff": ("digilocker", "ondc", "a2a", "consent"),
    "artifact": ("artifact",),
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
    "lekhak": ("lekhak", "script", "story"),
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
    "analyst": ("paisa", "analysis", "report banao"),
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


def _auto_keys() -> dict[str, set[str]]:
    """family -> keywords derived from its own tag + tool names (built once)."""
    out: dict[str, set[str]] = {}
    for name, fam in FAMILY_OF.items():
        words = set(_WORD_RE.findall(fam)) | set(_WORD_RE.findall(name))
        keys = {w for w in words if w not in _STOP and len(w) >= 3}
        # multi-word tool names also admit their joined form ("computer_operator" -> "computer operator")
        joined = name.replace("_", " ")
        if len(joined) >= 5 and joined not in joined.split():
            keys.add(joined)
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

    def size(self) -> int:
        return 1 + sum(1 for t in TOOLS if FAMILY_OF.get(t["name"]) in self.families or t["name"] in self.extra)

    def specs(self) -> list[dict]:
        """The tool list for the model: tool_search first, then the admitted specs in the registry's own order."""
        out = [dict(TOOL_SEARCH)]
        for t in TOOLS:
            if FAMILY_OF.get(t["name"]) in self.families or t["name"] in self.extra:
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


def plan_for(text: str, settings, extra_text: str = "") -> AdmitSet | None:
    """The admitted set for one turn, routed on her words (+ goal steps / worker notes).
    None = admission is off or the valve tripped: caller uses the FULL registry (v0.190 behaviour)."""
    if not getattr(settings, "agent_tool_admission", True):
        return None
    blob = f"{text or ''}\n{extra_text or ''}".lower()
    adm = AdmitSet(settings)
    hits = _match(blob)
    if hits:
        adm.admit_families(hits)
    STATS["turns"] += 1
    if adm.size() > max(40, int(getattr(settings, "tool_admit_cap", 220))):
        STATS["full_fallback"] += 1     # router over-matched: never worse than the full registry
        return None
    return adm


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
