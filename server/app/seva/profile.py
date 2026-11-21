"""G0 of docs/SUPPORT_GLOBAL_PLAN.md: the Customer Support PROFILE - 8 setup answers -> what the business sees + its
industry pack (`seva/packs/<industry>.json`: categories, urgent words, reply times, workflow templates, policy starting
values, knowledge questions, saved-reply starters, law notes per country with their source).

Laws kept here:
- Setup never changes anything by itself: `preview` lists every change and gives a hash; `apply` runs only with that
  hash (her tap). A changed answer shows a new preview.
- A pack only fills what she left empty (reply times she set, policy values she typed, saved replies she has are kept).
- Saved-reply starters arrive as DRAFTS (she approves them like any other saved reply).
- Law notes are shown with their source and "check this"; nothing in a law note is applied by code.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

PACK_DIR = Path(__file__).resolve().parent / "packs"

SIZES = {"me": ("Just me", "small"), "small_team": ("A small team (2-10)", "team"),
         "teams": ("Several teams", "multi"), "enterprise": ("An enterprise with departments and regions", "enterprise")}
CHANNELS = {"phone": "Phone calls", "whatsapp": "WhatsApp", "sms": "SMS / RCS", "email": "Email", "web": "Chat on my website",
            "app": "Chat inside my app or software", "messenger": "Facebook Messenger", "instagram": "Instagram",
            "telegram": "Telegram", "line": "LINE", "wechat": "WeChat", "viber": "Viber", "kakao": "KakaoTalk", "zalo": "Zalo",
            "apple": "Apple Messages for Business", "x": "X (Twitter)", "slack_teams": "Slack / Teams / Discord", "walkin": "In person"}
HELPDESKS = {"none": "None", "zendesk": "Zendesk", "freshdesk": "Freshdesk", "salesforce": "Salesforce Service Cloud",
             "zoho": "Zoho Desk", "intercom": "Intercom", "hubspot": "HubSpot Service", "servicenow": "ServiceNow",
             "chatwoot": "Chatwoot", "jira": "Jira Service Management", "other": "Other"}
SPLITS = {"shifts": "Shifts", "language": "By language", "product": "By product", "region": "By region", "tier": "By customer tier"}
DATA = {"none": "Nowhere yet", "sheet": "A spreadsheet", "systems": "A system joined on the Systems page", "api": "Our own API",
        "shopify": "Shopify", "salesforce": "Salesforce", "sap": "SAP", "stripe": "Stripe", "other": "Another system"}
LANGS = ("English", "Hindi", "Marathi", "Bengali", "Tamil", "Telugu", "Kannada", "Malayalam", "Gujarati", "Punjabi", "Urdu",
         "Spanish", "Portuguese", "French", "German", "Italian", "Dutch", "Polish", "Turkish", "Russian", "Ukrainian", "Arabic",
         "Hebrew", "Persian", "Swahili", "Amharic", "Hausa", "Yoruba", "Zulu", "Chinese", "Japanese", "Korean", "Vietnamese",
         "Thai", "Indonesian", "Malay", "Filipino", "Bahasa", "Greek", "Romanian", "Czech", "Hungarian", "Swedish")
# Who a workflow stage may be owned by (G8 maps these to real people / teams).
OWNERS = {"hoola": "Hoola", "team": "The support team", "supervisor": "A supervisor", "approver": "Whoever may approve",
          "finance": "Finance", "field": "Field staff", "engineering": "Engineering"}


class ProfileError(Exception):
    pass


# ---------------------------------------------------------------- packs
@lru_cache(maxsize=1)
def _packs() -> dict[str, dict]:
    out = {}
    for f in sorted(PACK_DIR.glob("*.json")):
        p = json.loads(f.read_text())
        out[p["key"]] = p
    return out


def packs() -> list[dict]:
    """Every pack, short (for the setup screen)."""
    return [{"key": k, "name": p["name"], "flows": [f["name"] for f in p["flows"]], "categories": len(p["categories"])}
            for k, p in sorted(_packs().items(), key=lambda kv: (kv[0] == "other", kv[1]["name"]))]


def pack(key: str) -> dict:
    p = _packs().get(key or "other")
    if p is None:
        raise ProfileError("industry: " + " / ".join(_packs()))
    return p


def check_pack(p: dict) -> list[str]:
    """Problems in one pack (tests + a bad file never loads quietly)."""
    bad = []
    for k in ("key", "name", "kind", "sla", "categories", "flows", "law", "knowledge_questions", "saved_replies"):
        if k not in p:
            bad.append(f"{p.get('key')}: missing {k}")
    from . import rules as R
    if p.get("kind") not in R.SLA_PRESETS:
        bad.append(f"{p['key']}: kind {p.get('kind')}")
    for pr, v in (p.get("sla") or {}).items():
        if pr not in R.PRIORITIES or not (0 < float(v[0]) <= float(v[1])):
            bad.append(f"{p['key']}: sla {pr}")
    for ck in p.get("categories", {}):
        if len(ck) > 20:
            bad.append(f"{p['key']}: category key too long {ck}")
    for f in p.get("flows", []):
        keys = [s["key"] for s in f["stages"]]
        if len(set(keys)) != len(keys):
            bad.append(f"{p['key']}/{f['key']}: repeated stage")
        for s in f["stages"]:
            if s["owner"] not in OWNERS:
                bad.append(f"{p['key']}/{f['key']}: owner {s['owner']}")
        for a, tos in f["arrows"].items():
            if a not in keys or any(t not in keys for t in tos):
                bad.append(f"{p['key']}/{f['key']}: arrow {a}")
        last = keys[-1]
        if f["arrows"].get(last):
            bad.append(f"{p['key']}/{f['key']}: the last stage must end")
        seen, todo = set(), [keys[0]]          # every stage reachable from the first
        while todo:
            k = todo.pop()
            if k not in seen:
                seen.add(k)
                todo += f["arrows"].get(k, [])
        if seen != set(keys):
            bad.append(f"{p['key']}/{f['key']}: stage cannot be reached {sorted(set(keys) - seen)}")
    for law in p.get("law", []):
        if not law.get("source") or law.get("status") not in ("check", "checked"):
            bad.append(f"{p['key']}: law note without source / status")
    return bad


# ---------------------------------------------------------------- questions
def _countries() -> list[dict]:
    from ..callcentre.world import WORLD
    return sorted(({"code": c, "name": v["name"]} for c, v in WORLD.items()), key=lambda x: x["name"])


def questions() -> list[dict]:
    """The 8 setup questions. Each can be skipped; the default is said."""
    return [
        {"key": "size", "q": "How big is your support?", "kind": "one", "options": {k: v[0] for k, v in SIZES.items()}, "default": "me"},
        {"key": "industry", "q": "What kind of business is it?", "kind": "one", "options": {p["key"]: p["name"] for p in packs()},
         "default": "other"},
        {"key": "countries", "q": "Which countries do your customers live in?", "kind": "many", "options": "countries",
         "default": "your own country"},
        {"key": "languages", "q": "Which languages should Hoola answer in?", "kind": "many", "options": list(LANGS),
         "default": "English"},
        {"key": "channels", "q": "Where do customers reach you today?", "kind": "many", "options": CHANNELS, "default": ["whatsapp", "phone"]},
        {"key": "helpdesk", "q": "Do you already use a helpdesk?", "kind": "one", "options": HELPDESKS, "default": "none"},
        {"key": "team", "q": "How many people answer customers, and how do you split the work?", "kind": "team",
         "options": SPLITS, "default": {"people": 1, "split": []}},
        {"key": "money", "q": "Up to what amount may a staff member or a supervisor agree to a refund or credit alone?",
         "kind": "money", "default": "everything comes to you"},
        {"key": "data", "q": "Where do your orders, accounts or bookings live?", "kind": "one", "options": DATA, "default": "none"},
    ]


def _own_country(tenant: str) -> str:
    """Her country from her time zone (the first country that uses it); India if unknown."""
    try:
        from ..callcentre.world import WORLD
        from ..life import tz_of
        z = str(tz_of(tenant))
        for c, v in WORLD.items():
            if z in v.get("tz", []):
                return c
    except Exception:
        pass
    return "IN"


def clean(tenant: str, answers: dict | None) -> dict:
    """Answers checked against the options; blanks get their defaults."""
    a = answers if isinstance(answers, dict) else {}
    from ..callcentre.world import WORLD
    size = a.get("size") if a.get("size") in SIZES else "me"
    ind = a.get("industry") if a.get("industry") in _packs() else "other"
    cs = [str(c).upper() for c in (a.get("countries") or []) if str(c).upper() in WORLD][:60] or [_own_country(tenant)]
    ls = [l for l in (a.get("languages") or []) if l in LANGS][:20] or ["English"]
    ch = [c for c in (a.get("channels") or []) if c in CHANNELS] or ["whatsapp", "phone"]
    hd = a.get("helpdesk") if a.get("helpdesk") in HELPDESKS else "none"
    t = a.get("team") if isinstance(a.get("team"), dict) else {}
    try:
        people = max(1, min(100000, int(t.get("people") or 1)))
    except (TypeError, ValueError):
        people = 1
    split = [s for s in (t.get("split") or []) if s in SPLITS]
    m = a.get("money") if isinstance(a.get("money"), dict) else {}

    def amt(v):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return None
        return n if n >= 0 else None
    money = {"agent": amt(m.get("agent")), "supervisor": amt(m.get("supervisor")),
             "currency": str(m.get("currency") or WORLD.get(cs[0], {}).get("currency") or "INR").upper()[:3]}
    if money["agent"] is not None and money["supervisor"] is not None and money["supervisor"] < money["agent"]:
        raise ProfileError("A supervisor's limit cannot be below a staff member's.")
    data = a.get("data") if a.get("data") in DATA else "none"
    return {"size": size, "industry": ind, "countries": cs, "languages": ls, "channels": ch, "helpdesk": hd,
            "team": {"people": people, "split": split}, "money": money, "data": data}


def derive(answers: dict) -> dict:
    """The profile the desk reads: tier, mode and which parts are switched on."""
    tier = SIZES[answers["size"]][1]
    people = answers["team"]["people"]
    if tier == "small" and people > 1:
        tier = "team"
    big = tier in ("multi", "enterprise")
    money = answers["money"]
    return {
        "tier": tier, "industry": answers["industry"], "regions": answers["countries"], "languages": answers["languages"],
        "mode": "layer" if answers["helpdesk"] != "none" else "own", "helpdesk": answers["helpdesk"],
        "channels": answers["channels"], "data": answers["data"], "currency": money["currency"],
        "parts": {
            "queues": big or bool(answers["team"]["split"]),
            "shifts": "shifts" in answers["team"]["split"] or tier == "enterprise",
            "workflow_designer": tier != "small",
            "approval_chain": money["agent"] is not None or money["supervisor"] is not None or big,
            "trust_controls": tier == "enterprise",
            "several_languages": len(answers["languages"]) > 1,
            "several_countries": len(answers["countries"]) > 1,
            "live_lookups": answers["data"] != "none",
        },
    }


# ---------------------------------------------------------------- stored profile
def _row(s, tenant: str):
    from . import service as S
    return S._st(s, tenant)


def get(tenant: str) -> dict:
    from ..db import session
    with session() as s:
        r = _row(s, tenant)
        return json.loads(r.profile or "{}") if getattr(r, "profile", "") else {}


def _hash(tenant: str, answers: dict) -> str:
    return hashlib.sha256((tenant + "|" + json.dumps(answers, sort_keys=True)).encode()).hexdigest()[:16]


def _changes(tenant: str, answers: dict, prof: dict) -> list[dict]:
    from . import service as S
    from . import rules as R
    p = pack(answers["industry"])
    cur = S.settings(tenant)
    old = get(tenant)
    out = []

    def add(what, before, after, note=""):
        if before != after:
            out.append({"what": what, "from": before, "to": after, "note": note})
    oa = old.get("answers") or {}
    add("Business kind", _packs().get(oa.get("industry"), {}).get("name", "Not set"), p["name"])
    add("Size", SIZES.get(oa.get("size"), ("Not set",))[0], SIZES[answers["size"]][0])
    add("Countries", ", ".join(oa.get("countries") or []) or "Not set", ", ".join(answers["countries"]))
    add("Languages", ", ".join(oa.get("languages") or []) or "Not set", ", ".join(answers["languages"]))
    own_sla = bool(S._j(_sla_raw(tenant), {}))
    if not own_sla:
        add("Reply times", _sla_text(cur["sla"]), _sla_text(p["sla"]), "from the pack; you can change them later")
    pol = cur.get("policy") or {}
    for k, v in (p.get("policy") or {}).items():
        if k not in pol:
            add(f"Rule: {k.replace('_', ' ')}", "not set", v, "a starting value; change it in Channels & settings")
    have = {m["name"].lower() for m in S.macros(tenant)}
    new_rep = [r["name"] for r in p["saved_replies"] if r["name"].lower() not in have]
    if new_rep:
        add("Saved replies (drafts to check)", "", ", ".join(new_rep))
    add("Ticket stages", ", ".join(f["name"] for f in pack(oa["industry"])["flows"]) if oa.get("industry") in _packs() else "Not set",
        ", ".join(f["name"] for f in p["flows"]), "used by the workflow (G8)")
    on = [k for k, v in prof["parts"].items() if v]
    oon = [k for k, v in (old.get("profile") or {}).get("parts", {}).items() if v]
    add("Parts shown", ", ".join(PART_NAMES[k] for k in oon) or "The simple desk",
        ", ".join(PART_NAMES[k] for k in on) or "The simple desk")
    if prof["mode"] == "layer":
        add("How Hoola works", "Its own inbox", f"On top of {HELPDESKS[prof['helpdesk']]}", "joining it comes in phase G12")
    return out


PART_NAMES = {"queues": "Queues and routing", "shifts": "Shifts", "workflow_designer": "Your ticket workflow",
              "approval_chain": "Approval chain for money", "trust_controls": "Enterprise controls",
              "several_languages": "Several languages", "several_countries": "Several countries",
              "live_lookups": "Live lookups in your systems"}


def _sla_raw(tenant: str) -> str:
    from ..db import session
    with session() as s:
        return _row(s, tenant).sla or ""


def _sla_text(sla: dict) -> str:
    return " · ".join(f"{p} {float(v[0]):g}h/{float(v[1]):g}h" for p, v in sla.items())


def preview(tenant: str, answers: dict | None) -> dict:
    a = clean(tenant, answers)
    prof = derive(a)
    return {"answers": a, "profile": prof, "pack": pack(a["industry"])["name"], "changes": _changes(tenant, a, prof),
            "hash": _hash(tenant, a),
            "say": "Here is what setup will change. Nothing changes until you tap Apply."}


def apply(tenant: str, answers: dict | None, hash: str) -> dict:
    """Her tap: the preview's hash must match these answers."""
    from ..db import session
    from . import service as S
    a = clean(tenant, answers)
    if not hash or hash != _hash(tenant, a):
        raise ProfileError("The answers changed after the preview. Look at the new preview and tap Apply again.")
    prof = derive(a)
    p = pack(a["industry"])
    with session() as s:
        r = _row(s, tenant)
        r.kind = p["kind"]
        if not S._j(r.sla, {}):
            r.sla = S._dump({k: list(v) for k, v in p["sla"].items()})
        pol = S._j(r.policy, {})
        for k, v in (p.get("policy") or {}).items():
            pol.setdefault(k, v)
        r.policy = S._dump(pol)
        if "online_store" == p["key"] and any(c == "IN" for c in a["countries"]):
            r.ecommerce = True
        r.profile = json.dumps({"answers": a, "profile": prof, "pack": p["key"], "pack_version": p.get("version", 1)},
                               sort_keys=True)
    have = {m["name"].lower() for m in S.macros(tenant)}
    added = 0
    for rep in p["saved_replies"]:
        if rep["name"].lower() in have:
            continue
        try:
            S.macro_add(tenant, rep["name"], rep["text"])
            added += 1
        except S.SevaError:
            pass
    out = view(tenant)
    out["say"] = (f"Setup saved: {p['name']}, {SIZES[a['size']][0].lower()}."
                  + (f" {added} saved repl{'ies' if added != 1 else 'y'} wait for your check in Knowledge." if added else ""))
    return out


# ---------------------------------------------------------------- what the desk reads
def view(tenant: str) -> dict:
    stored = get(tenant)
    if not stored:
        return {"done": False, "questions": questions(), "packs": packs(), "countries": _countries(),
                "answers": clean(tenant, {}), "profile": derive(clean(tenant, {}))}
    a = stored["answers"]
    p = pack(stored["pack"])
    regions = set(a["countries"])
    law = [l for l in p["law"] if _applies(l["region"], regions)]
    return {"done": True, "answers": a, "profile": stored["profile"], "questions": questions(), "packs": packs(),
            "countries": _countries(), "pack": {"key": p["key"], "name": p["name"], "flows": p["flows"],
            "categories": {k: v["label"] for k, v in p["categories"].items()}, "knowledge_questions": p["knowledge_questions"],
            "law": law}, "parts_on": [PART_NAMES[k] for k, v in stored["profile"]["parts"].items() if v]}


def _applies(region: str, countries: set[str]) -> bool:
    eu = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT",
          "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
    for part in region.split("/"):
        part = part.strip()
        if part == "EU" and countries & eu:
            return True
        if part == "UK" and "GB" in countries:
            return True
        if part.startswith("US") and "US" in countries:
            return True
        if part in countries:
            return True
    return False


def categories(tenant: str) -> dict[str, dict]:
    """The pack's ticket categories for this business ({} before setup)."""
    st = get(tenant)
    if not st:
        return {}
    try:
        return pack(st["pack"])["categories"]
    except ProfileError:
        return {}


def urgent_words(tenant: str) -> list[str]:
    st = get(tenant)
    if not st:
        return []
    try:
        return pack(st["pack"]).get("urgent_words", [])
    except ProfileError:
        return []


def line(tenant: str) -> str:
    """One line for the Support chat's desk block."""
    st = get(tenant)
    if not st:
        return "Setup not done yet (8 questions on the desk's Setup page)."
    a, pr = st["answers"], st["profile"]
    return (f"Setup: {pack(st['pack'])['name']}, {SIZES[a['size']][0].lower()}, countries {', '.join(a['countries'][:8])}, "
            f"languages {', '.join(a['languages'][:6])}, {'on top of ' + HELPDESKS[pr['helpdesk']] if pr['mode'] == 'layer' else 'its own inbox'}.")
