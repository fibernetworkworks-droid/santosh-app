"""The ten Enterprise Systems & ERP jobs: what each one reads, what it produces, and where it must stop.

One engine serves all ten (service.py) because the work has one shape in every role:

    she connects her own system  ->  Hoola reads it  ->  Hoola drafts the artifact  ->  HER TAP  ->  Hoola does it  ->  audit

What differs per role is only the table below, so a new role is data, not code.

CAPPED ROLES. Three jobs stop at the paperwork on purpose, and `cap` says so in her own words. The gate there is a
licence or a statutory audit, not our code, and writing past it would break the project's "official routes only"
rule - for banking, the law. A capped role still does the whole analyst half; it simply never touches the live
rail, and it SAYS it stops rather than quietly doing less than she expected.
"""
from __future__ import annotations

from typing import Any

# a system Hoola can be pointed at. "own" = she connects her company's tenant with her own key, exactly the way
# v0.290 Zoho MCP and v0.297 Composio key apps already work - Hoola never holds a shared enterprise credential.
SYSTEMS: dict[str, dict[str, str]] = {
    "sap":        {"label": "SAP",                "how": "own", "note": "SAP Integration Suite ka MCP Gateway ya OData API, aapke apne BTP tenant se"},
    "oracle":     {"label": "Oracle / NetSuite",  "how": "own", "note": "NetSuite REST, aapke apne account se (Composio ke zariye bhi)"},
    "salesforce": {"label": "Salesforce",         "how": "own", "note": "Salesforce ka apna hosted MCP server, aapke login se (OAuth)"},
    "windchill":  {"label": "PTC Windchill",      "how": "own", "note": "Windchill OData REST, aapke apne server se"},
    "teamcenter": {"label": "Siemens Teamcenter", "how": "read_only", "note": "abhi sirf padhna: bahar se agent ka rasta har installation mein alag hai, pehle jaanch"},
    "shopify":    {"label": "Shopify",            "how": "own", "note": "aapki apni dukaan"},
    "composio":   {"label": "Composio apps",      "how": "own", "note": "~1,600 apps, aapki apni key (v0.294)"},
    "tally":      {"label": "TallyPrime",         "how": "own", "note": "aapke office PC par"},
    "sheet":      {"label": "Sheet / CSV",        "how": "own", "note": "koi bhi system na ho to sheet se"},
}

ARTIFACTS = ("spec", "mapping", "plan", "checklist", "register", "report", "test_plan", "runbook")

ROLES: dict[str, dict[str, Any]] = {
    "erp": {
        "label": "ERP Architect (SAP / Oracle)",
        "say": "SAP ya NetSuite ka module aur field padhkar integration spec, field mapping aur migration sheet banana",
        "systems": ["sap", "oracle", "sheet", "composio"],
        "artifacts": ["spec", "mapping", "plan", "test_plan", "runbook"],
        "writes": True,
        "cap": "",
        "rules": ["ERP mein koi entry aapki haan ke bina nahi jaati.",
                  "Production aur test system alag: kaunsa hai, yeh har kaam se pehle likha jaata hai."],
    },
    "crm_arch": {
        "label": "CRM Architect (Salesforce)",
        "say": "Salesforce ke object, flow aur permission padhkar customisation ka plan aur test list banana",
        "systems": ["salesforce", "composio", "sheet"],
        "artifacts": ["spec", "plan", "test_plan", "register"],
        "writes": True,
        "cap": "",
        "rules": ["Live org mein koi badlav aapki haan se.",
                  "Salesforce ka apna hosted MCP hi istemaal hota hai; DX wala server band ho raha hai."],
    },
    "tpm": {
        "label": "Technical Product Manager",
        "say": "roadmap, milestone, risk aur hafte ka status note; har owner se update maangna",
        "systems": ["sheet", "composio"],
        "artifacts": ["plan", "report", "register"],
        "writes": False,
        "cap": "",
        "rules": ["Aapki taraf se kisi ko tareekh ka vaada nahi kiya jaata: Hoola sirf report karta hai."],
    },
    "bpa": {
        "label": "Process Automation Architect",
        "say": "do system ke beech ka kaam jodna - Composio ke apps se step-by-step flow banakar chalana",
        "systems": ["composio", "sheet", "sap", "oracle", "salesforce"],
        "artifacts": ["spec", "plan", "runbook", "test_plan"],
        "writes": True,
        "cap": "",
        "rules": ["Doosre system mein har likhne wala kadam trust gate se guzarta hai.",
                  "Flow pehle ek test record par chalta hai, phir sab par - aapki haan se."],
    },
    "ecom_arch": {
        "label": "E-Commerce Systems Architect",
        "say": "catalogue, stock, daam aur checkout ki jaanch - bheed mein kya tootega - aur listing theek karna",
        "systems": ["shopify", "composio", "sheet"],
        "artifacts": ["report", "plan", "checklist", "test_plan"],
        "writes": True,
        "cap": "",
        "rules": ["Daam aur catalogue ka badlav aapki haan se.", "Stock ka number dukaan se padha jaata hai, anuman se nahi."],
    },
    "health_int": {
        "label": "Healthcare Integration (HL7 / FHIR)",
        "say": "ABDM ka poora pack - FHIR R4 record ka dhaancha, ABHA ka flow, M1/M2/M3 checklist aur audit ke kaagaz",
        "systems": ["sheet"],
        "artifacts": ["spec", "mapping", "checklist", "plan"],
        "writes": False,
        "cap": ("Asli mareez ka data Hoola na padhta hai na bhejta hai. ABDM production ke liye CERT-In empanelled "
                "security audit pehle paas karna padta hai - woh aapke sanstha ko karna hota hai, Hoola use kar nahi sakta. "
                "Yahan tak sab kaagaz taiyaar milega; aage ka rasta audit ke baad khulta hai."),
        "rules": ["Kisi mareez ka naam, number ya report Hoola ke paas nahi aati - sirf dhaancha aur namoona data.",
                  "FHIR R4 hi likha jaata hai, kyunki ABDM wahi maangta hai."],
    },
    "bank_int": {
        "label": "Core Banking Integrator",
        "say": "statement milaan, ledger match, reporting format aur Account Aggregator ki taiyari ki checklist",
        "systems": ["tally", "sheet", "composio"],
        "artifacts": ["report", "mapping", "checklist", "register"],
        "writes": False,
        "cap": ("Hoola kisi banking rail ko haath nahi lagata. Account Aggregator ke liye RBI ka licence aur "
                "Sahamati ka empanelled audit chahiye - Hoola na FIU hai na AA. Hisaab, milaan aur taiyari ka saara "
                "kaam yahan hota hai; paisa ya bank ka connection kabhi nahi."),
        "rules": ["Koi paisa nahi hilta, koi bank se seedha connection nahi.",
                  "Account number poora kabhi nahi likha jaata - sirf aakhri 4 ank."],
    },
    "supply_opt": {
        "label": "Supply Chain Optimisation",
        "say": "route, godown aur order se sabse sasta plan, reorder point aur stock level - bachat rupay mein",
        "systems": ["sheet", "composio", "oracle"],
        "artifacts": ["report", "plan", "mapping"],
        "writes": False,
        "cap": "",
        "rules": ["Hoola plan banata hai; order aap deti hain.",
                  "Har bachat ka number uske hisaab ke saath dikhaya jaata hai, warna number nahi likha jaata."],
    },
    "plm": {
        "label": "PLM Specialist",
        "say": "Windchill ke part, BOM aur change order padhkar badlav ka draft aur uska asar",
        "systems": ["windchill", "teamcenter", "sheet"],
        "artifacts": ["spec", "mapping", "report", "checklist"],
        "writes": True,
        "cap": "",
        "rules": ["BOM mein har likhai aapki haan se.",
                  "Teamcenter abhi sirf padhne ke liye hai: bahar se agent ka rasta jaanche bina nahi chhua jaata."],
    },
    "regtech": {
        "label": "RegTech / Compliance Automation",
        "say": "compliance calendar, har tareekh par nazar, filing ke kaagaz taiyaar aur niyam toot-ne par chetavni",
        "systems": ["sheet", "tally", "composio"],
        "artifacts": ["register", "checklist", "report", "plan"],
        "writes": False,
        "cap": ("Filing aap hi karti hain, apne portal par. Hoola kaagaz taiyaar karta hai, tareekh yaad dilata hai "
                "aur galti pakadta hai - par kisi sarkari portal par aapki taraf se jama nahi karta."),
        "rules": ["Kaanoon ki salah nahi: niyam ka hawala diya jaata hai, raay nahi.",
                  "Har tareekh ka source likha jaata hai, warna 'pakka nahi' kaha jaata hai."],
    },
}

# every role reads; these are the ones that may change something outside when she taps Haan
WRITERS = tuple(k for k, v in ROLES.items() if v["writes"])
CAPPED = tuple(k for k, v in ROLES.items() if v["cap"])

NEVER = (
    "Koi bhi enterprise system ka password, token ya key chat mein nahi li jaati - app se joda jaata hai.",
    "Production system mein bina aapki haan ke kuch nahi likha jaata.",
    "Jo number system se nahi aaya, woh number likha hi nahi jaata - 'pata nahi' kaha jaata hai.",
    "Mareez ka data, poora account number aur ID number kabhi artifact mein nahi jaate.",
)


def role(key: str) -> dict[str, Any]:
    r = ROLES.get(key)
    if r is None:
        raise KeyError(key)
    return r


def systems_for(key: str) -> list[dict[str, str]]:
    return [{"key": s, **SYSTEMS[s]} for s in role(key)["systems"] if s in SYSTEMS]


def cap_of(key: str) -> str:
    return role(key)["cap"]


def may_write(key: str) -> bool:
    return bool(role(key)["writes"])
