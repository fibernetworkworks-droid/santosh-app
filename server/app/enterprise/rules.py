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

ARTIFACTS = ("spec", "mapping", "plan", "checklist", "register", "report", "test_plan", "runbook",
             "config", "matrix", "sop", "training")

ROLES: dict[str, dict[str, Any]] = {
    "erp": {
        "label": "ERP Architect (SAP / Oracle)",
        "say": "SAP ya NetSuite ka module aur field padhkar integration spec, field mapping aur migration sheet banana",
        "systems": ["sap", "oracle", "sheet", "composio"],
        "artifacts": ["spec", "mapping", "plan", "test_plan", "runbook", "config", "matrix", "sop",
                      "report", "register", "checklist", "training"],
        "writes": True,
        "cap": "",
        "rules": ["ERP mein koi entry aapki haan ke bina nahi jaati.",
                  "Production aur test system alag: kaunsa hai, yeh har kaam se pehle likha jaata hai."],
    },
    "crm_arch": {
        "label": "CRM Architect (Salesforce)",
        "say": "Salesforce ke object, flow aur permission padhkar customisation ka plan aur test list banana",
        "systems": ["salesforce", "composio", "sheet"],
        "artifacts": ["spec", "plan", "test_plan", "register", "config", "matrix", "sop", "training",
                      "report", "checklist", "runbook", "mapping"],
        "writes": True,
        "cap": "",
        "rules": ["Live org mein koi badlav aapki haan se.",
                  "Salesforce ka apna hosted MCP hi istemaal hota hai; DX wala server band ho raha hai."],
    },
    "tpm": {
        "label": "Technical Product Manager",
        "say": ("engineering ki taraf ka kaam: team-to-team dependency, architecture ka faisla, NFR, technical "
                "debt, capacity, release train, RAID aur incident ka peechha - har owner se update lekar"),
        "systems": ["composio", "sheet"],
        "artifacts": ["plan", "report", "register", "spec", "matrix", "checklist", "runbook", "mapping", "sop"],
        "writes": True,
        "cap": "",
        "rules": [
            "Aapki taraf se kisi ko tareekh ka vaada nahi kiya jaata: Hoola poochta hai aur report karta hai.",
            # The product side already has a far richer home. Saying so here is what stops two tools doing one job.
            "Discovery, RICE / ICE scoring, PRD aur release notes `product` tool ka kaam hai - yahan sirf "
            "engineering ki taraf: dependency, architecture, NFR, debt, capacity, release train, risk.",
            "Tracker (Jira / Linear / Asana) mein har badlav aapki haan se - padhna khula hai.",
            "Jo team ne khud nahi kaha, woh status Hoola nahi likhta: 'update nahi aaya' likha jaata hai.",
        ],
    },
    "bpa": {
        "label": "Process Automation Architect",
        "say": "do system ke beech ka kaam jodna - Composio ke apps se step-by-step flow banakar chalana",
        "systems": ["composio", "sheet", "sap", "oracle", "salesforce"],
        "artifacts": ["spec", "plan", "runbook", "test_plan", "mapping", "report", "checklist", "matrix", "sop"],
        "writes": True,
        "cap": "",
        "rules": ["Doosre system mein har likhne wala kadam trust gate se guzarta hai.",
                  "Flow pehle ek test record par chalta hai, phir sab par - aapki haan se."],
    },
    "ecom_arch": {
        "label": "E-Commerce Systems Architect",
        "say": "catalogue, stock, daam aur checkout ki jaanch - bheed mein kya tootega - aur listing theek karna",
        "systems": ["shopify", "composio", "sheet"],
        "artifacts": ["report", "plan", "checklist", "test_plan", "spec", "mapping", "config", "register", "runbook"],
        "writes": True,
        "cap": "",
        "rules": ["Daam aur catalogue ka badlav aapki haan se.", "Stock ka number dukaan se padha jaata hai, anuman se nahi."],
    },
    "health_int": {
        "label": "Healthcare Integration (HL7 / FHIR)",
        "say": "ABDM ka poora pack - FHIR R4 record ka dhaancha, ABHA ka flow, M1/M2/M3 checklist aur audit ke kaagaz",
        "systems": ["sheet"],
        "artifacts": ["spec", "mapping", "checklist", "plan", "matrix", "report", "register", "sop"],
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
        "artifacts": ["report", "mapping", "checklist", "register", "spec", "plan", "matrix", "sop"],
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
        "artifacts": ["report", "plan", "mapping", "register", "checklist", "matrix", "spec"],
        "writes": False,
        "cap": "",
        "rules": ["Hoola plan banata hai; order aap deti hain.",
                  "Har bachat ka number uske hisaab ke saath dikhaya jaata hai, warna number nahi likha jaata."],
    },
    "plm": {
        "label": "PLM Specialist",
        "say": "Windchill ke part, BOM aur change order padhkar badlav ka draft aur uska asar",
        "systems": ["windchill", "teamcenter", "sheet"],
        "artifacts": ["spec", "mapping", "report", "checklist", "config", "matrix", "plan", "register", "runbook"],
        "writes": True,
        "cap": "",
        "rules": ["BOM mein har likhai aapki haan se.",
                  "Teamcenter abhi sirf padhne ke liye hai: bahar se agent ka rasta jaanche bina nahi chhua jaata."],
    },
    "regtech": {
        "label": "RegTech / Compliance Automation",
        "say": "compliance calendar, har tareekh par nazar, filing ke kaagaz taiyaar aur niyam toot-ne par chetavni",
        "systems": ["sheet", "tally", "composio"],
        "artifacts": ["register", "checklist", "report", "plan", "matrix", "sop", "mapping", "spec"],
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

# ---------------------------------------------------------------- sub-jobs inside one role
# An ERP "job" is not one person's work - it is a desk. The owner asked for ALL of it, so the whole lifecycle is
# here, from the first blueprint to the support ticket years later. Every sub-job sits inside the SAME duty
# (ent_erp) because the risk is the same - it is still her live ERP - so trust is set once for the whole desk.
# The structure is generic: any role in ROLES may grow a JOBS entry the same way.
JOBS: dict[str, dict[str, dict[str, Any]]] = {
    "erp": {
        "blueprint":   {"label": "Blueprint / design", "say": "business process samajhkar ERP ka design aur gap list",
                        "papers": ["spec", "report", "plan"]},
        "functional":  {"label": "Functional consultant", "say": "module ka config - FI/CO, MM, SD, PP, HR - aur uska dastavez",
                        "papers": ["config", "spec", "sop"]},
        "technical":   {"label": "Technical / ABAP", "say": "custom report, form, enhancement, interface ka technical spec",
                        "papers": ["spec", "test_plan"]},
        "data":        {"label": "Data migration", "say": "purane system se data - field mapping, safai ke niyam, load ka plan, milaan",
                        "papers": ["mapping", "plan", "checklist", "report"]},
        "integration": {"label": "Integration", "say": "doosre system se jodna - interface, middleware, error handling, dobara bhejna",
                        "papers": ["spec", "mapping", "runbook", "test_plan"]},
        "basis":       {"label": "Basis / system admin", "say": "system ka rakhrakhav, transport, patch, backup, performance",
                        "papers": ["runbook", "checklist", "report"]},
        "security":    {"label": "Security aur authorisation", "say": "kis role ko kya dikhe, SoD ka takraav, user access review",
                        "papers": ["matrix", "report", "checklist"]},
        "testing":     {"label": "Testing / UAT", "say": "test case, UAT ka round, regression, defect ki list",
                        "papers": ["test_plan", "register", "report"]},
        "cutover":     {"label": "Cutover aur go-live", "say": "go-live ka ghanta-dar-ghanta plan, freeze, rollback, hypercare",
                        "papers": ["runbook", "checklist", "plan"]},
        "training":    {"label": "Training aur change", "say": "user ko sikhana - guide, step-by-step SOP, kaun kab seekhega",
                        "papers": ["training", "sop", "plan"]},
        "support":     {"label": "Support / AMS", "say": "ticket, incident, root cause, SLA aur mahine ki report",
                        "papers": ["register", "report", "sop"]},
        "masterdata":  {"label": "Master data", "say": "vendor, customer, material, GL - ek hi sach, duplicate aur galti pakadna",
                        "papers": ["register", "checklist", "report"]},
        "reporting":   {"label": "Reporting aur analytics", "say": "ERP se report aur dashboard - kaunsa number kahan se aata hai",
                        "papers": ["spec", "mapping", "report"]},
        "finance_ops": {"label": "Finance close", "say": "month-end close ka schedule, reconciliation, controlling ka hisaab",
                        "papers": ["checklist", "report", "sop"]},
        "licence":     {"label": "Licence aur kharcha", "say": "kitne user, kaunsa licence, kya bach sakta hai",
                        "papers": ["report", "register"]},
        "upgrade":     {"label": "Upgrade / patch", "say": "version badalna - asar, test ka daayra, rollback",
                        "papers": ["plan", "checklist", "test_plan", "report"]},
    },
    # A Salesforce practice is a desk too. The split that matters here is DATA (records: leads, accounts) versus
    # CONFIGURATION (objects, fields, flows, permission sets) - the second lives behind the Tooling API and can
    # break the org for everyone, which is why `api` is on the run and production config changes are never routine.
    # ---------------------------------------------------------------- the remaining seven desks
    "bpa": {
        "discover":  {"label": "Kaam samajhna", "say": "abhi kaam kaise hota hai - har kadam, har haath",
                      "papers": ["spec", "mapping", "report"]},
        "design":    {"label": "Naya flow banana", "say": "kaunsa system kya karega, kis kram mein",
                      "papers": ["spec", "plan", "mapping"]},
        "build":     {"label": "Flow jodna", "say": "Composio ke apps jodkar flow khada karna",
                      "papers": ["runbook", "spec", "config"]},
        "exceptions": {"label": "Jab kuch toote", "say": "fail hone par kya - dobara, rokna, ya insaan ko dena",
                       "papers": ["runbook", "checklist", "spec"]},
        "test":      {"label": "Jaanch", "say": "ek test record se poore load tak",
                      "papers": ["test_plan", "checklist", "report"]},
        "handover":  {"label": "Team ko dena", "say": "kaun chalayega, kya dekhega, kahan shikayat",
                      "papers": ["sop", "runbook", "matrix"]},
        "monitor":   {"label": "Nazar rakhna", "say": "kitne chale, kitne atke, kitna waqt bacha",
                      "papers": ["report", "register"]},
    },
    "ecom_arch": {
        "catalogue": {"label": "Catalogue", "say": "product, variant, photo, description - kya adhoora hai",
                      "papers": ["report", "checklist", "mapping"]},
        "pricing":   {"label": "Daam", "say": "daam, chhoot, tax - kahan galat lag raha hai",
                      "papers": ["report", "register", "checklist"]},
        "stock":     {"label": "Stock", "say": "kitna hai, kitna dikhaya ja raha hai, oversell ka khatra",
                      "papers": ["report", "checklist", "mapping"]},
        "checkout":  {"label": "Checkout", "say": "cart se paise tak - kahan log chhod jaate hain",
                      "papers": ["report", "test_plan", "plan"]},
        "payments":  {"label": "Payment", "say": "UPI / card / COD, fail hone par kya, refund",
                      "papers": ["spec", "runbook", "checklist"]},
        "shipping":  {"label": "Delivery", "say": "pin code, charge, courier, tracking",
                      "papers": ["mapping", "spec", "report"]},
        "peak":      {"label": "Bheed ke liye taiyari", "say": "sale ke din kya tootega - pehle hi pakad lena",
                      "papers": ["checklist", "test_plan", "runbook"]},
        "integration": {"label": "Jodna", "say": "ERP / accounting / courier se jodna",
                        "papers": ["spec", "mapping", "runbook"]},
    },
    "plm": {
        "parts":     {"label": "Part master", "say": "part number, naam, revision - ek hi sach",
                      "papers": ["register", "mapping", "checklist"]},
        "bom":       {"label": "BOM", "say": "kaunsa part kahan lagta hai, kitna, kis level par",
                      "papers": ["report", "mapping", "spec"]},
        "change":    {"label": "Change order", "say": "badlav ka asar - kaunse assembly, kaunsa stock, kaunsa supplier",
                      "papers": ["spec", "report", "checklist"]},
        "revision":  {"label": "Revision", "say": "kaunsa version chal raha hai, kaunsa purana",
                      "papers": ["register", "report"]},
        "supplier":  {"label": "Supplier ka part", "say": "bahar se aane wale part, unke number, unki jagah",
                      "papers": ["mapping", "register", "report"]},
        "cost":      {"label": "Laagat", "say": "poore assembly ki laagat, neeche se jodkar",
                      "papers": ["report", "mapping"]},
        "docs":      {"label": "Drawing aur document", "say": "kaunsa drawing kis part ka, kaunsa latest",
                      "papers": ["register", "checklist", "mapping"]},
        "release":   {"label": "Release", "say": "design se production tak - kya kya chahiye",
                      "papers": ["checklist", "runbook", "plan"]},
    },
    "supply_opt": {
        "demand":    {"label": "Maang", "say": "kitna bikta hai, kis mahine zyada",
                      "papers": ["report", "mapping"]},
        "reorder":   {"label": "Kab mangwana hai", "say": "reorder point, safety stock, kitna mangwana hai",
                      "papers": ["report", "register", "plan"]},
        "stock":     {"label": "Stock ka haal", "say": "kya zyada pada hai, kya khatm hone wala hai",
                      "papers": ["report", "checklist", "register"]},
        "supplier":  {"label": "Supplier", "say": "kaun samay par deta hai, kaun mehnga hai",
                      "papers": ["matrix", "report", "register"]},
        "routes":    {"label": "Raasta aur dhulai", "say": "kaunsa raasta sasta, kitna kharcha",
                      "papers": ["report", "mapping", "plan"]},
        "warehouse": {"label": "Godown", "say": "kahan kya rakha jaye, kitni jagah chahiye",
                      "papers": ["plan", "report", "mapping"]},
        "service":   {"label": "Service level", "say": "kitni baar stock khatm hua, kitna order poora hua",
                      "papers": ["report", "register"]},
    },
    "health_int": {
        "abha":      {"label": "ABHA", "say": "ABHA banane aur jodne ka flow (M1)",
                      "papers": ["spec", "checklist", "plan"]},
        "fhir":      {"label": "FHIR R4", "say": "record ka dhaancha - kaunsa resource, kaunsa field",
                      "papers": ["mapping", "spec", "checklist"]},
        "hip":       {"label": "Record dena (M2)", "say": "link, discovery, care context - HIP ka kaam",
                      "papers": ["spec", "checklist", "plan"]},
        "hiu":       {"label": "Record lena (M3)", "say": "consent se record maangna - HIU ka kaam",
                      "papers": ["spec", "checklist", "plan"]},
        "consent":   {"label": "Consent", "say": "kis cheez ki ijazat, kitne samay ke liye, kaise wapas",
                      "papers": ["spec", "matrix", "checklist"]},
        "security":  {"label": "Security audit", "say": "CERT-In audit ke liye kaagaz aur checklist",
                      "papers": ["checklist", "register", "report"]},
        "mapping":   {"label": "Purane system se", "say": "aapke HMS ke field FHIR mein kahan jaate hain",
                      "papers": ["mapping", "report", "spec"]},
    },
    "bank_int": {
        "recon":     {"label": "Milaan", "say": "statement aur ledger ka milaan - kya nahi mila",
                      "papers": ["report", "register", "mapping"]},
        "formats":   {"label": "File ke dhaanche", "say": "bank ki file, NACH, payment file ka dhaancha",
                      "papers": ["mapping", "spec", "checklist"]},
        "aa_ready":  {"label": "Account Aggregator ki taiyari", "say": "AA ke liye kya kya chahiye - checklist",
                      "papers": ["checklist", "register", "report"]},
        "reporting": {"label": "Report", "say": "roz / mahine ki report, kis format mein",
                      "papers": ["report", "spec", "sop"]},
        "controls":  {"label": "Control", "say": "kaun kya kar sakta hai, maker-checker",
                      "papers": ["matrix", "checklist", "register"]},
        "exceptions": {"label": "Jo nahi mila", "say": "fail, duplicate, ghoomta hua paisa - kya karna hai",
                       "papers": ["register", "sop", "report"]},
    },
    "regtech": {
        "calendar":  {"label": "Compliance calendar", "say": "kaunsi tareekh, kiska kaam, kya jama karna hai",
                      "papers": ["register", "checklist", "plan"]},
        "filings":   {"label": "Filing ke kaagaz", "say": "jama karne se pehle ka pura set",
                      "papers": ["checklist", "register", "report"]},
        "rules":     {"label": "Niyam", "say": "kaunsa niyam lagta hai, kahan likha hai",
                      "papers": ["register", "report", "mapping"]},
        "evidence":  {"label": "Saboot", "say": "kis niyam ka kaunsa saboot rakha hai",
                      "papers": ["register", "matrix", "checklist"]},
        "breaches":  {"label": "Jo toota", "say": "kya chhoot gaya, kitna jurmana ho sakta hai",
                      "papers": ["report", "register", "plan"]},
        "audit":     {"label": "Audit", "say": "auditor ke sawaal aur unke jawab ka set",
                      "papers": ["checklist", "register", "report"]},
        "policy":    {"label": "Policy aur SOP", "say": "andar ke niyam likhna aur team tak pahunchana",
                      "papers": ["sop", "spec", "checklist"]},
    },
    "crm_arch": {
        "admin":       {"label": "Admin", "say": "user, licence, login ki dikkat, roz ka rakhrakhav",
                        "papers": ["sop", "register", "checklist"]},
        "config":      {"label": "Object aur field config", "say": "object, field, page layout, record type - aur kyun",
                        "papers": ["config", "spec", "matrix"]},
        "automation":  {"label": "Flow aur automation", "say": "flow, validation rule, approval process - kab kya chalta hai",
                        "papers": ["spec", "test_plan", "runbook"]},
        "apex":        {"label": "Apex / code", "say": "Apex class, trigger, test coverage",
                        "papers": ["spec", "test_plan"]},
        "integration": {"label": "Integration", "say": "doosre system se jodna, named credential, platform event",
                        "papers": ["spec", "mapping", "runbook", "test_plan"]},
        "data":        {"label": "Data ka kaam", "say": "import, duplicate safai, mass update, data ki sehat",
                        "papers": ["mapping", "plan", "checklist", "report"]},
        "security":    {"label": "Profile aur sharing", "say": "profile, permission set, sharing rule, field-level security",
                        "papers": ["matrix", "report", "checklist"]},
        "reporting":   {"label": "Report aur dashboard", "say": "report, dashboard, list view - kaunsa number kahan se",
                        "papers": ["spec", "mapping", "report"]},
        "testing":     {"label": "Testing / UAT", "say": "test case, UAT, regression, defect ki list",
                        "papers": ["test_plan", "register", "report"]},
        "release":     {"label": "Release aur deployment", "say": "sandbox se production, change set, rollback",
                        "papers": ["runbook", "checklist", "plan"]},
        "adoption":    {"label": "Adoption aur training", "say": "user ko sikhana, SOP, kaun kya istemaal kar raha hai",
                        "papers": ["training", "sop", "report"]},
        "support":     {"label": "User support", "say": "user ke sawaal, bug, 'yeh kaise hota hai', SLA",
                        "papers": ["register", "report", "sop"]},
    },
    # The TPM desk. It deliberately does NOT repeat the product side (discovery, scoring, PRDs, releases) - that
    # lives in the far richer `product` tool. What is here is the engineering layer a technical PM actually holds:
    # what blocks what, what was decided and why, what must be true to ship, and what is owed.
    "tpm": {
        "roadmap":      {"label": "Technical roadmap", "say": "ab / aage / baad mein - team ke paar, engineering ki nazar se",
                         "papers": ["plan", "report"]},
        "dependencies": {"label": "Dependency aur critical path", "say": "kaun kis par ruka hai, aur sabse lamba raasta",
                         "papers": ["matrix", "report", "register"]},
        "architecture": {"label": "Architecture ke faisle", "say": "kya tay hua, kyun, aur kya chhoda gaya (ADR)",
                         "papers": ["spec", "register", "report"]},
        "nfr":          {"label": "NFR", "say": "speed, scale, uptime, security - shipping se pehle kya sach hona chahiye",
                         "papers": ["spec", "checklist", "report"]},
        "debt":         {"label": "Technical debt", "say": "kya udhaar pada hai, uska byaaj, aur chukane ka plan",
                         "papers": ["register", "plan", "report"]},
        "capacity":     {"label": "Capacity", "say": "team ke paas kitna waqt hai aur kitna vaada ho chuka hai",
                         "papers": ["report", "plan", "matrix"]},
        "release":      {"label": "Release train", "say": "kis release mein kya, go / no-go, kaun sign karega",
                         "papers": ["checklist", "runbook", "plan"]},
        "risk":         {"label": "RAID", "say": "risk, assumption, issue, dependency - ek jagah, har ek ka maalik",
                         "papers": ["register", "report"]},
        "vendor":       {"label": "Banayein ya khareedein", "say": "build vs buy, vendor ki tulna, kya chhoot raha hai",
                         "papers": ["report", "matrix", "spec"]},
        "incident":     {"label": "Incident ka peechha", "say": "post-mortem ke baad jo kaam bacha - band hone tak",
                         "papers": ["register", "report", "sop"]},
        "metrics":      {"label": "Delivery ke number", "say": "lead time, escaped defect, kitna vaada vs kitna hua",
                         "papers": ["report", "mapping"]},
        "status":       {"label": "Status aur escalation", "say": "hafte ka note, kya ruka hai, kise batana hai",
                         "papers": ["report", "sop"]},
    },
}


def jobs_of(role_key: str) -> dict[str, dict[str, Any]]:
    return JOBS.get(role_key, {})


def job_papers(role_key: str, job: str) -> list[str]:
    """The paper kinds that sub-job really produces; the role's full list when it has no sub-jobs."""
    j = JOBS.get(role_key, {}).get(job)
    return list(j["papers"]) if j else list(role(role_key)["artifacts"])
