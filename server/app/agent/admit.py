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
unchanged and applied after, exactly as before. Non-owner actors (staff / customer) keep the full set (v0.558: her own routines are admitted like chat):
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
    "reach",      # v0.559 REACH MANCH: the fallback door when a web tool fails + status/channels introspection
    "gyaan",      # her knowledge base
    "procedure",  # seekhe hue kaam
    "google",     # google_status (the one-line Google fix)
    "make",       # memory_search + make_document + photo_clean / id_photo
    "life",       # reminders, alarms, lists, profile, weather
    # v0.559 "maps" left the core: the family grew to 20 tools over the Maps phases and rode on every "namaste";
    # her map words open the whole family, and CORE_TOOLS below keeps the two everyday ones always in view
    "file",       # file_read (attachments in chat)
    "id",         # Pehchaan Locker
    "usage",      # ai_kharcha
    "device",     # phone_health
    "docstudio",  # v0.245 doc_studio / doc_preview: a document ask in any words finds the design studio
    "data",       # v0.238 data_fetch / data_read: big data stays in a server file (never escape to the cloud PC)
    # v0.559 "team" left the core too: a BIG ask (several things to make) or her team words open it (plan_for)
    "recall",     # v0.250 haal_ki_chats: her other chats by time (one tiny spec, like Claude's recent-chats tool)
})
# v0.559 SAHI GINTI: single tools that stay in view on every turn even though their family is not core - the
# everyday ones of a family that is otherwise only opened by her words. Anthropic's guidance: tool choice gets worse
# past 30-50 tools in view; a plain "namaste" carried 75 before this, ~52 after.
CORE_TOOLS = frozenset({"maps_search", "maps_directions",
                        "yaad_khojo"})   # v0.605 EK YAAD: the one memory door is always in view (old chats are fetched, not pasted)
_LATLNG = re.compile(r"(?<![\d.])-?\d{1,2}\.\d{2,}\s*,\s*-?\d{1,3}\.\d{2,}")

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
    # v0.589 KAAN PACK: her words for a transcript job (sunwai stays OUT - it is the vakil desk's court-hearing word;
    # bare "kaan" stays OUT too - "makaan" contains it, the rentdesk lane does not need our family)
    "kaan": ("transcript", "transcribe", "transcription", "kaan se", "kaan tool", "kaan pack", "audio sun",
             "sun kar", "sun ke", "audio likh", "likhawat", "srt", "subtitle", "voice note likh", "speech to text",
             "meeting ki file", "record sun", "record likh", "ट्रांसक्रिप्ट", "लिखावट"),
    # v0.357 Engineering Desk (CAD Engineer): her words for a part / drawing / CAD files
    "eng": ("cad", "step file", ".step", "stl", "3d print", "cnc", "machin", "bracket", "flange", "enclosure", "mounting",
            "part bana", "drawing", "dimension", "fillet", "chamfer", "solidworks", "fusion 360", "autocad", "freecad",
            # v0.365 analysis / calculations / sheet / CNC
            "fea", "stress analysis", "safety factor", "tolerance stack", "h7", "bolt torque", "weld size", "g-code",
            "gcode", "sheet metal", "flat pattern", "natural frequency", "deflection", "pressure drop",
            "fatigue", "bolted joint", "vdi 2230", "cfd", "flow simulation", "preload",
            "dfm", "manufacturab", "printab", "injection mould", "injection mold", "draft angle", "undercut",
            "urdf", "robot arm", "gripper", "mechanism", "linkage", "joint", "exploded view", "ros "),
    "youtube": ("youtube", "channel", "vlog", "subscriber"),
    "tv": ("tv", "channel", "dth"),
    "bt": ("bluetooth", "speaker", "music", "song", "gaana", "gaane", "volume", "ac ", "air condition", "remote",
           "ganna", "गाना", "गाने"),
    # v0.245 "pc" is not keyword-admitted any more: _pc_wanted() decides (v0.271: only her PC / Hoola's PC named)
    "operator": ("computer operator", "operator"),
    "jaanch": ("jaanch", "test karo"),
    # v0.559 REACH MANCH: core family anyway; these words keep it admitted if core ever shrinks ('kya kharab hai'
    # stays with jaanch - Hoola's own health - reach answers only about the internet doors)
    "reach": ("reach", "reach manch", "website nahi khul", "site nahi khul", "nahi khul raha", "internet check",
              "backends", "kaun sa door", "web status"),
    # v0.560 SPEC SUTRA: a work lane, not core (reach is the fallback door every chat may need; the spec
    # ladder is admitted when software work is spoken). Bare "spec" stays with product (its action=spec) -
    # these keys are the software-build shapes.
    "speckit": ("speckit", "spec sutra", "spec driven", "spec-driven", "sdd", "user story", "acceptance criteria",
                "user stories", "traceability", "constitution", "naksha banao", "spec banao", "spec likho",
                "spec likh", "requirements doc", "requirement list", "converge loop", "convergence"),
    # v0.586 SANDARBH MANCH: two work lanes (backend-only, the hoola AI's own desks - the T1 reference
    # family). Bare "file" stays with product's file tools; these are the agent-owns-it shapes.
    "workspace": ("workspace", "meri files", "file banao", "file likho", "file padho", "file kholo",
                  "file save karo", "folder banao", "folder dikhao", "file dikhao", "directory tree",
                  "apni file", "workspac"),
    "kgmemory": ("kgmemory", "knowledge graph", "graph memory", "kg memory", "long term memory",
                 "long-term memory", "entity banao", "relation banao", "yaad graph", "memory graph"),
    "shop": ("order", "amazon", "flipkart", "zomato", "swiggy", "kharid", "shopping", "pizza", "grocer"),
    "mshop": ("mobile shop", "sim card", "phone repair", "phone shop"),
    "courier": ("courier", "parcel", "deliver", "track", "shipment", "speed post", "speedpost", "bluedart",
                "delhivery"),
    "india": ("holiday", "chhutti", "ifsc", "pincode", "bank holiday", "panchang", "tithi", "muhurat", "ekadashi"),
    # v0.277 IndiaMART: B2B buying / sourcing words (the SOURCING intent below carries the sentence shapes)
    # v0.381 Game Desk: a game to make (the GAME intent below carries the sentence shapes)
    "gamedesk": ("godot", "game banao", "game bana", "game develop", "game design", "video game", "mobile game", "web game",
                 "browser game", "khel banao", "गेम बनाओ", "गेम",
                 # v0.386 Studio Project: the long game project's words
                 "game project", "game studio", "studio project", "game ka kaam", "game ka task",
                 "game bible", "game ki bible", "balance pass", "difficulty curve", "enemy stats", "level design",
                 "game art", "sprite", "game sound", "sound effect", "game music", "game assets", "3d model for my game",
                 "game qa", "game test", "game bug", "game ke bug", "playtest", "golden screen",
                 "itch.io", "steam page", "game release", "game ki release", "windows build", "mac build", "linux build", "age rating",
                 # v0.420 role packs: worlds + physics
                 "procedural world", "world generation", "dungeon", "game map", "game world", "level generator",
                 "game physics", "physics engine", "game ki physics",
                 # v0.421 batch 2: spatial audio + haptics
                 "spatial audio", "3d sound", "3d audio", "binaural", "reverb zone", "game ki awaaz", "haptic", "haptics",
                 "vibration pattern", "game vibration", "rumble",
                 # v0.422 batch 3: multiplayer + AR / VR
                 "multiplayer", "netcode", "game server", "lag compensation", "webxr", "virtual reality", "vr game",
                 "ar game", "headset", "oculus", "quest 3", "hand tracking",
                 # v0.423 batch 4: simulators, digital twin, VFX pipeline
                 "flight simulator", "training simulator", "orbit simulation", "driving simulator", "digital twin",
                 "factory simulation", "line simulation", "vfx pipeline", "render farm", "aces colour", "aces color", "exr",
                 # v0.425 Phase 8: runtime + editor
                 "replay test", "game replay", "game telemetry", "retention", "godot editor", "godot plugin", "ask hoola panel",
                 # v0.428 Phase 9: live ops
                 "live ops", "liveops", "a/b test", "ab test", "live event", "game event", "game crash", "hotfix",
                 "patch check", "arpdau", "game revenue", "game ka event", "game ka a/b",
                 # v0.433 Phase 10: big-studio mode
                 "unity", "unreal", "unreal engine", "ue5", "big studio", "hoola crew plugin", "editor plugin",
                 # v0.447 Game Arena
                 "game arena", "games arena", "game ka score", "game duel", "game originality",
                 # v0.455 provenance
                 "steam survey", "ai disclosure", "game provenance", "kahan se aaya", "created with ai",
                 # v0.456 scenes
                 "game scene", "game ka scene", "tscn", "level scene", "platformer level"),
    # v0.348 official Indian statistics -> MoSPI (built in); the STATS intent below carries sentence shapes
    "mospi": ("mospi", "esankhyiki", "inflation", "mehngai", "mahangai", "महंगाई", "cpi", "wpi", "iip", "gdp", "gva",
              "plfs", "unemployment", "berozgari", "बेरोजगारी", "jobless", "labour force", "nfhs", "census", "sarkari aankde",
              "statistics", "aankde", "आंकड़े", "per capita", "industrial production", "national accounts", "aishe", "udise"),
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
    # v0.381 Shiksha suite: school / coaching work (papers, question banks, plans) + the Python sandbox
    # Shiksha Phase 2: the personal tutor (doubts, practice, language practice, progress)
    # Shiksha Phase 3: the school office (attendance, grading, timetable, report cards)
    # Shiksha Phase 4: the research assistant (literature, gaps, references, analysis, drafts)
    "prayog": ("practical", "prayog", "prayogshala", "experiment", "lab mein", "3d mein", "kaise kaam karta", "kaise kaam karti",
               "how it works", "how does", "simulation", "pendulum", "lens", "prism", "ohm", "meter bridge", "potentiometer",
               "resonance", "sonometer", "vernier", "screw gauge", "प्रयोग", "प्रयोगशाला"),
    "shodh": ("research paper", "literature review", "literature survey", "thesis", "dissertation", "phd", "synopsis",
              "doi", "citation", "references banao", "bibliography", "bibtex", "zotero", "openalex", "pubmed", "arxiv",
              "research gap", "research question", "methodology", "regression", "anova", "t-test", "chi square",
              "hypothesis", "shodh", "शोध", "शोध पत्र"),
    "daftar": ("hazri", "attendance", "absent", "gair hazir", "present", "timetable", "time table", "report card",
               "marksheet", "result banao", "grading", "copy check", "answer sheet", "omr", "check karo paper",
               "marks chadhao", "marks enter", "sign off", "transcript", "हाज़िरी", "रिपोर्ट कार्ड", "समय सारणी"),
    "guru": ("tutor", "padhao", "padha do", "samjhao", "samjha do", "doubt", "homework", "practice karao", "revision",
             "sawaal samajh", "kaise hal", "solve karna sikhao", "hint do", "english bolna", "spoken english", "grammar",
             "pragati", "progress report", "weak topic", "पढ़ाओ", "समझाओ", "होमवर्क"),
    "shiksha": ("question paper", "sample paper", "test paper", "paper banao", "question bank", "sawaal banao", "mcq",
                "syllabus", "lesson plan", "year plan", "rubric", "blueprint", "marking scheme", "answer key", "worksheet",
                "unit test", "periodic test", "cbse", "icse", "ncert", "board exam", "class 10", "class 12", "students",
                "bachche", "school", "coaching", "teacher", "padhana", "pathyakram", "पेपर", "प्रश्न पत्र", "पाठ्यक्रम",
                "python", "regression", "t-test", "anova", "chart banao", "data analysis", "statistics nikalo"),
    "vakil": ("vakil", "advocate", "lawyer"),
    "notary": ("notary", "notarise", "notarize"),
    "dpo": ("dpo", "data protection", "privacy policy", "dpdp"),
    "cyber": ("cyber", "hack"),
    "itadmin": ("it admin", "itadmin", "office wifi", "office network"),
    "devops": ("devops", "deploy", "server", "uptime"),
    "dev": ("dev", "developer", "code", "bug", "software"),
    # v0.585 Paisa Sahayak (consumer money safety): loan / fee / scam / complaint words. Tight keys.
    "finguard": ("emi", "loan", "karz", "qarz", "processing fee", "apr", "prepay", "foreclos", "snowball", "avalanche", "scam", "fraud", "dhokha",
                 "thagi", "fake call", "fake kyc", "kyc expire", "upi collect", "collect request", "ombudsman", "bank complaint", "bank charges",
                 "hidden charges", "sms charges", "min balance", "credit card charges", "paisa_sahayak", "otp maang", "otp mang", "digital arrest"),
    # v0.602 Vitt Sahayak (finance desk assists, Wave 2). Tight keys.
    "finops": ("sip", "advance tax", "26as", "ais reconcile", "tds reconcil", "ageing", "aging report", "receivable", "payable", "three way match",
               "3 way match", "aml", "structuring", "sanction", "pep screening", "credit memo", "dscr", "financial ratio", "vitt_sahayak"),
    # v0.603 Risk Desk (markets and credit papers, Wave 3). Tight keys.
    "riskdesk": ("order ticket", "rebalance", "portfolio drift", "concentration limit", "margin utilisation", "underwrit", "key fact statement", " kfs",
                 "dpd", "npa", "sma-", "ecl", "expected credit loss", "dcf", "discounted cash", "velocity check", "wash trade", "round trip trade", "risk_desk"),
    # v0.495 office hours (the gstack THINK/PLAN lane): her big-idea words open a design doc first.
    # Tight keys only - "idea" / "plan" alone would load it on every second turn (kaam_plan is core already).
    "officehours": ("office hours", "officehours", "baithak", "design doc", "plan review", "naya idea",
                    "product idea", "business idea", "idea pe soch", "shuru karne se pehle",
                    "officehours_dekho"),
    # v0.502 DHARA (her workflows, the n8n lane): recurring-automation words. Tight keys - "kaam"
    # alone is the kaam lane, "reminder" is life; only workflow-shaped asks open dhara.
    "dhara": ("workflow", "workflows", "dhara", "automation", "automate", "auto chalu", "apne aap chal",
              "roz ka automatic", "har din automatic", "jab bhi", "webhook", "dhara_list", "dhara_save",
              "dhara_run", "dhara_runs", "dhara_control", "dhara_dsl", "workflow file", "export workflow", "import workflow", "backup workflow"),
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
    # v0.559 maps left the core, so her place words must open it (before, it rode on every turn and needed none)
    "maps": ("paas mein", "paas me", "aas paas", "aaspaas", "nazdeek", "najdeek", "kahan hai", "kaha hai", "kahaan hai",
             "rasta", "raasta", "route", "direction", "map", "location", "kitni door", "kitna door", "kitne km",
             "km door", "distance", "near me", "nearby", "petrol pump", "pahunchna", "pahuchna", "kaise jaun",
             "kaise jaaun", "kaise pahunch", "google maps", "kaun si jagah", "jagah batao", "dukaan kahan",
             "shop near", "my maps", "business profile", "listing", "ghar ke paas", "yahan ke paas",
             "office ke paas", "dukaan ke paas", "ke aas paas", "sabse paas", "doori", "km ke andar", "km tak",
             "jagah", "jagahen", "kram mein", "gps", "pins", "pin kiya", "dukaan tak", "google se kitne",
             "maps ka", "maps par", "maps pe", "delivery kis kram"),
    "team": ("agents", "agent lagao", "agent banao", "team banao", "team bana", "agent team", "team laga", "crew", "deploy",
             "parallel", "kai agents", "multiple agents", "agents lagao", "madadgar dal", "team se karo"),
    # v0.479 HOOLA SMART HOME: ghar ke devices (Home Assistant). Fridge / geyser words bhi yahin
    # admit hote hain TAAKI Hoola politely refuse kar sake (read-only guard app/home.py mein).
    "home": ("home assistant", "smart home", "smart bulb", "smart light", "smart plug", "smart speaker",
             "ghar ki light", "ghar ki lights", "ghar ka", "ghar ke device", "ghar ke devices",
             "light on", "light off", "light band", "light jalao", "light bujha", "lights band", "lights on",
             "bulb", "led strip", "dim ", "mood light",
             "pankha", "fan chala", "fan band", "fan on", "fan off", "fan band karo",
             "ac chala", "ac band", "ac on", "ac off", "ac lagao", "ac temperature", "ac 24", "ac 22", "ac 26",
             "thermostat", "hvac", "temperature set",
             "curtain", "curtains", "parda", "parde", "blind", "blinds", "shutter", "shutters",
             "taala", "lock khol", "lock kar", "door lock", "main door",
             "home_devices", "home_state", "home_on", "home_off", "home_link",
             "fridge", "refrigerator", "washing machine", "geyser", "washer",
             "home assistant link", "smart plug on", "device band karo", "device chalao", "saari lights"),
    "byox": ("build your own", "byox", "from scratch", "scratch se banao", "scratch se banana",
             "implement a", "write a compiler", "write a database", "write a shell", "write a web server",
             "build a database", "build a git", "build a compiler", "build a shell", "build a browser",
             "build a container", "build an os", "build an operating system", "build a renderer",
             "build a torrent", "build a blockchain", "build a neural", "build a physics",
             "systems programming", "how does git work", "how does a database work",
             "how does tcp work", "how does docker work", "low-level programming",
             "byox_list", "byox_guide", "byox_plan",
             "3d renderer", "bittorrent client", "blockchain", "docker container",
             "emulator", "frontend framework", "language interpreter", "memory allocator",
             "regex engine", "search engine", "voxel engine", "web browser",
             # v0.488 Hinglish / Hindi: how people actually ask
             "khud se banao", "khud se banana", "khud banana sikhao", "banana sikhao", "banate hain",
             "kaise banta hai", "kaise banate", "ground up", "bilkul scratch", "shuru se banao",
             "systems seekhna", "sikhna chahta", "sikhna chahti", "kaise kaam karta hai git",
             "kaise kaam karta hai database", "kaise kaam karta hai docker",
             "खुद से बनाओ", "स्क्रैच से", "बनाना सिखाओ", "कैसे बनाते हैं"),

    # v0.496 CODE GRAPH (Graphify): structure questions about a repo. No bare 'graph' (charts / dashboards own that word).
    "graph": ("graphify", "knowledge graph", "code graph", "call graph", "dependency graph", "codebase map",
              "map the codebase", "map this repo", "map this codebase", "who calls", "what calls", "what depends on",
              "what breaks if", "impact of changing", "architecture of this repo", "codebase samjh", "code ka naksha",
              "repo ka naksha", "kaun call karta", "kis par depend", "isko badalne se kya tootega", "graph_build",
              "graph_ask", "graph_list"),
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
    "build",     # v0.496 "build a website / app" is not a code-graph ask
    "graph",     # v0.496 charts / dashboards own the bare word; the code-graph family has its own phrases
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
        out = [search_spec()]
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

_SPEC: dict = {}


def search_spec() -> dict:
    """v0.563 tool_search with the families named (Anthropic's tool-search advice: say which categories exist so the
    model knows what it can search for). Built once from the registry, so it is byte-stable across turns (cache)."""
    if not _SPEC:
        fams = sorted({f for f in FAMILY_OF.values() if f})
        _SPEC.update(TOOL_SEARCH)
        _SPEC["description"] = (TOOL_SEARCH["description"] + f" Every Hoola tool can be found here ({len(TOOLS)} in "
                                f"{len(fams)} families: " + ", ".join(fams) + "). Search by what the job needs or by "
                                "a tool's exact name; the tools found load for you to call next.")
    return dict(_SPEC)


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
    # v0.381 a game to make / change -> the Game Developer (Game Desk)
    (re.compile(r"\b(?:game|games|gaming|khel)\b.{0,40}\b(?:bana\w*|build|make|create|develop|design|chahiye)\b|"
                r"\b(?:bana\w*|build|make|create|develop)\b.{0,30}\b(?:game|khel)\b|\bgodot\b|गेम", re.I),
     ("gamedesk",), "game"),
    # v0.410 a system to architect / design (or a PR to check against its design) -> the Principal Software Architect
    (re.compile(r"\b(?:architect\w*|architecture|system design|design (?:a|the|my|our) (?:system|backend|platform|app)|"
                r"high[- ]level design|hld|lld|low[- ]level design|scal(?:e|able|ability)|microservices?|monolith|"
                r"adr|c4 (?:model|diagram)|capacity plan\w*|distributed system)\b", re.I),
     ("arch",), "software architecture"),
    # v0.348 an official Indian number (inflation, GDP, jobs, industry, surveys) -> MoSPI first, never a search summary
    (re.compile(r"\b(?:cpi|wpi|iip|gdp|gva|plfs|nfhs|nss|mospi)\b|inflation|mehngai|mahangai|unemployment|berozgari|"
                r"growth rate|per capita|industrial (?:output|production)|labour force|sarkari aank|महंगाई|बेरोजगारी", re.I),
     ("mospi",), "official stats"),
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


# v0.430 SOCH KE JAWAB step 3: pylab (the locked Python sandbox - pandas / numpy / scipy / statsmodels / matplotlib,
# no network, no secrets) lived in the Shiksha family and was in view for 1 of 50 hard asks, so Hoola did EMIs, CAGRs,
# break-evens and forecasts in its head. It now rides with every ask that needs a worked-out number or real analysis.
_CALC = re.compile(r"\bcalculat\w*|\bcompute\b|\bstatistic\w*|\baverage\b|\bmean\b|\bmedian\b|\bcorrelat\w*|"
                   r"\bregression|\btrend\b|\bgrowth\s+rate|\bchart\b|\bgraph\b|\bplot\b|\bhisaab\s+laga|\bjod\s+ke|"
                   r"\btotal\s+(?:kitna|nikal)|\bpercent\w*|\b\d+(?:\.\d+)?\s*%|\bganana|गणना|\bforecast|\bproject(?:ion|ed)\b",
                   re.I)


def calc_needed(text: str, why: dict | None = None) -> bool:
    """Does this ask need numbers worked out / data analysed for real? A hard reasoning ask (agent/hard.py), a data job,
    a reverse-engineering list, or plain calculation words."""
    t = str(text or "")
    if not t.strip() or t.lstrip().startswith(("[", "(")):
        return False
    why = why or {}
    if any(str(v).startswith(("intent:data", "intent:business numbers")) for v in why.values()):
        return True
    if _CALC.search(t):
        return True
    try:
        from . import hard
        return hard.assess(t)["hard"]
    except Exception:
        return False


def plan_for(text: str, settings, extra_text: str = "") -> AdmitSet | None:
    """The admitted set for one turn, routed on her words (+ goal steps / worker notes).
    None = admission is off or the valve tripped: caller uses the FULL registry (v0.190 behaviour)."""
    if not getattr(settings, "agent_tool_admission", True):
        return None
    adm = AdmitSet(settings)
    adm.extra.update(n for n in CORE_TOOLS if n in HANDLERS)     # v0.559 the everyday tools of non-core families
    why = route(text, settings)
    if extra_text:
        for f, w in route(extra_text, settings).items():
            why.setdefault(f, w)
    if why:
        adm.admit_families(why)
        adm.why = why
    if "maps" in set(FAMILY_OF.values()) and "maps" not in adm.families and _LATLNG.search(text or ""):
        adm.admit_families(["maps"])            # v0.559 a latitude, longitude pair in her words is a maps ask
        adm.why = {**adm.why, "maps": "coordinates"}
    try:                            # v0.559 a big ask (several things to make) brings the agent team into view
        from . import goal as _goal
        if "team" in set(FAMILY_OF.values()) and "team" not in adm.families and \
                (_goal.looks_big(text) or _goal.looks_big(extra_text or "")):
            adm.admit_families(["team"])
            adm.why = {**adm.why, "team": "big ask"}
    except Exception:               # noqa: BLE001 - routing never fails a turn
        pass
    if calc_needed(text, why):
        adm.extra.add("pylab")          # v0.430 SOCH KE JAWAB 3: every worked-out number comes from real code
        adm.why = {**adm.why, "pylab": "calculation"}
    try:                            # v0.473 R2: a research ask brings Hoola's own research engine into view
        from . import hard as _hard
        if "research" in set(FAMILY_OF.values()) and (_hard.research_wanted(text) or "research_status" in str(text) or "research_watch" in str(text)):
            adm.admit_families(["research"])
            adm.why = {**adm.why, "research": "research ask"}
            if "team" in set(FAMILY_OF.values()):     # v0.559 team left the core: deep research still gets its crew
                adm.admit_families(["team"])
                adm.why.setdefault("team", "research ask")
    except Exception:               # noqa: BLE001 - routing never fails a turn
        pass
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
    # v0.550 EK JAISA: a tool asked for by its EXACT name always opens its own family. The keyword match used to win
    # and the name lookup ran only when it found nothing, so tool_search("sheet_read") opened sheets but not
    # gdrive, "crm_arch" opened arch but not enterprise, "edit_desk" opened video - 15 tools could not be reached.
    for nm in set(_NAME_RE.findall(need.lower())) | {need.lower()}:
        fam = FAMILY_OF.get(nm)
        if fam:
            hits.add(fam)
    if not hits:   # try the words as family tags / tool names directly
        low = need.lower()
        words = set(_WORD_RE.findall(low)) | {low}
        for name, fam in FAMILY_OF.items():
            if _hit(name, low) or _hit(low, name):
                hits.add(fam)
            elif any(_hit(w, fam) or w == fam for w in words):
                hits.add(fam)
    if adm is not None and getattr(ctx, "native_search", False):
        # v0.563 CLAUDE KA AUZAAR: on a Claude turn every tool is already declared (deferred). The answer is
        # tool_reference blocks - the API loads those definitions - and the request's tool list never changes.
        # The families still count as opened (the PC gate in pick.py reads them; the next turn keeps them sticky).
        from . import toolsearch as _ts
        had = set(adm.families)
        if hits:
            adm.admit_families(hits)
        try:
            from .prompts import guide_for
            g = guide_for(hits - had, had)
            if g:   # the family's working guide, delivered beside the result (the system prompt stays as it was)
                getattr(ctx, "native_guides", None) is None and setattr(ctx, "native_guides", [])
                ctx.native_guides.append(g)
        except Exception:
            log.debug("native guide lookup failed", exc_info=True)
        names = _ts.find(need, hits)
        STATS["tool_search"] += 1
        refs = _ts.answer(names, set(getattr(ctx, "native_loaded", ()) or ()))
        log.info("tool_search (native) %s -> %s", ",".join(sorted(hits)), ",".join(names[:8]))
        if refs:
            return {"tool_references": refs, "found": names}
        if names:
            return {"admitted": [], "note": "Yeh tools pehle se dikh rahe hain: " + ", ".join(names[:20])}
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
