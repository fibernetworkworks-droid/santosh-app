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
    "sap":        {"label": "SAP",                "how": "own", "note": "SAP Integration Suite MCP Gateway or OData API, from your own BTP tenant"},
    "oracle":     {"label": "Oracle / NetSuite",  "how": "own", "note": "NetSuite REST, from your own account (also through Composio)"},
    "salesforce": {"label": "Salesforce",         "how": "own", "note": "Salesforce's own hosted MCP server, with your login (OAuth)"},
    "windchill":  {"label": "PTC Windchill",      "how": "own", "note": "Windchill OData REST, from your own server"},
    "teamcenter": {"label": "Siemens Teamcenter", "how": "read_only",
                   "note": "read only for now: Siemens' real route is SOA (not REST), and the REST that exists is built by the admin in each installation"},
    "shopify":    {"label": "Shopify",            "how": "own", "note": "your own shop"},
    "composio":   {"label": "Composio apps",      "how": "own", "note": "~1,600 apps, your own key (v0.294)"},
    "tally":      {"label": "TallyPrime",         "how": "own", "note": "on your office PC"},
    "sheet":      {"label": "Sheet / CSV",        "how": "own", "note": "from a sheet when there is no system"},
}

ARTIFACTS = ("spec", "mapping", "plan", "checklist", "register", "report", "test_plan", "runbook",
             "config", "matrix", "sop", "training")

ROLES: dict[str, dict[str, Any]] = {
    "erp": {
        "label": "ERP Architect (SAP / Oracle)",
        "say": "reads SAP or NetSuite modules and fields to make integration specs, field mappings and migration sheets",
        "systems": ["sap", "oracle", "sheet", "composio"],
        "artifacts": ["spec", "mapping", "plan", "test_plan", "runbook", "config", "matrix", "sop",
                      "report", "register", "checklist", "training"],
        "writes": True,
        "cap": "",
        "rules": ["No entry goes into the ERP without your approval.",
                  "Production and test systems are separate: which one it is gets written down before every job."],
    },
    "crm_arch": {
        "label": "CRM Architect (Salesforce)",
        "say": "reads Salesforce objects, flows and permissions to make a customisation plan and a test list",
        "systems": ["salesforce", "composio", "sheet"],
        "artifacts": ["spec", "plan", "test_plan", "register", "config", "matrix", "sop", "training",
                      "report", "checklist", "runbook", "mapping"],
        "writes": True,
        "cap": "",
        "rules": ["Any change in a live org only with your approval.",
                  "Only Salesforce's own hosted MCP is used; the DX server is being shut down."],
    },
    "tpm": {
        "label": "Technical Product Manager",
        "say": ("the engineering side of the work: team-to-team dependencies, architecture decisions, NFRs, technical "
                "debt, capacity, release train, RAID and incident follow-up - with updates from each owner"),
        "systems": ["composio", "sheet"],
        "artifacts": ["plan", "report", "register", "spec", "matrix", "checklist", "runbook", "mapping", "sop"],
        "writes": True,
        "cap": "",
        "rules": [
            "No date is promised to anyone on your behalf: Hoola asks and reports.",
            # The product side already has a far richer home. Saying so here is what stops two tools doing one job.
            "Discovery, RICE / ICE scoring, PRDs and release notes are the `product` tool's job - here only "
            "the engineering side: dependencies, architecture, NFRs, debt, capacity, release train, risk.",
            "Every change in the tracker (Jira / Linear / Asana) only with your approval - reading is open.",
            "Hoola does not write a status the team did not give: it writes 'no update received'.",
        ],
    },
    "bpa": {
        "label": "Process Automation Architect",
        "say": "connects work between two systems - builds and runs step-by-step flows with Composio apps",
        "systems": ["composio", "sheet", "sap", "oracle", "salesforce"],
        "artifacts": ["spec", "plan", "runbook", "test_plan", "mapping", "report", "checklist", "matrix", "sop"],
        "writes": True,
        "cap": "",
        "rules": ["Every step that writes to another system passes the trust gate.",
                  "A flow runs on one test record first, then on all - only with your approval."],
    },
    "ecom_arch": {
        "label": "E-Commerce Systems Architect",
        "say": "checks catalogue, stock, prices and checkout - what will break under load - and fixes listings",
        "systems": ["shopify", "composio", "sheet"],
        "artifacts": ["report", "plan", "checklist", "test_plan", "spec", "mapping", "config", "register", "runbook"],
        "writes": True,
        "cap": "",
        "rules": ["Price and catalogue changes only with your approval.", "Stock numbers are read from the shop, not guessed."],
    },
    "health_int": {
        "label": "Healthcare Integration (HL7 / FHIR)",
        "say": "the full ABDM pack - FHIR R4 record structure, the ABHA flow, M1/M2/M3 checklist and audit papers",
        "systems": ["sheet"],
        "artifacts": ["spec", "mapping", "checklist", "plan", "matrix", "report", "register", "sop"],
        "writes": False,
        "cap": ("Hoola neither reads nor sends real patient data. Hoola has NOT checked the ABDM production route "
                "itself: we could not read NHA's actual documents (milestones, the condition for leaving the sandbox, "
                "the audit), and outside sources contradict each other - some say CERT-In, some say STQC. What is not "
                "confirmed is not worked on. You get all the papers up to here; the road beyond is in your organisation's name."),
        "rules": ["No patient's name, number or report ever reaches Hoola - only the structure and sample data.",
                  "Only FHIR R4 is written, because that is what ABDM asks for."],
    },
    "bank_int": {
        "label": "Core Banking Integrator",
        "say": "statement reconciliation, ledger matching, reporting formats and an Account Aggregator readiness checklist",
        "systems": ["tally", "sheet", "composio"],
        "artifacts": ["report", "mapping", "checklist", "register", "spec", "plan", "matrix", "sop"],
        "writes": False,
        "cap": ("Hoola does not touch any banking rail. Under RBI rules (Master Direction NBFC-AA, 2016) only an "
                "entity that is itself registered with a financial regulator - RBI, SEBI, IRDAI or PFRDA - can be "
                "an 'FIU' that receives bank data. Hoola is not, and this cannot be bought with an audit. "
                "All the calculation, reconciliation and preparation work happens here; money or a bank connection never."),
        "rules": ["No money moves, and there is no direct connection to a bank.",
                  "A full account number is never written - only the last 4 digits."],
    },
    "supply_opt": {
        "label": "Supply Chain Optimisation",
        "say": "the cheapest plan from routes, warehouses and orders, reorder points and stock levels - savings in rupees",
        "systems": ["sheet", "composio", "oracle"],
        "artifacts": ["report", "plan", "mapping", "register", "checklist", "matrix", "spec"],
        "writes": False,
        "cap": "",
        "rules": ["Hoola makes the plan; you place the order.",
                  "Every savings number is shown with its calculation, otherwise no number is written."],
    },
    "plm": {
        "label": "PLM Specialist",
        "say": "reads Windchill parts, BOMs and change orders to draft a change and its impact",
        "systems": ["windchill", "teamcenter", "sheet"],
        "artifacts": ["spec", "mapping", "report", "checklist", "config", "matrix", "plan", "register", "runbook"],
        "writes": True,
        "cap": "",
        "rules": ["Every write to a BOM only with your approval.",
                  "Teamcenter is read-only for now - not because Siemens forbids it (SOA gives both "
                  "read and write), but because Hoola does not speak SOA and its REST is built by the "
                  "admin in each installation."],
    },
    "regtech": {
        "label": "RegTech / Compliance Automation",
        "say": "compliance calendar, a watch on every date, filing papers ready and a warning when a rule is broken",
        "systems": ["sheet", "tally", "composio"],
        "artifacts": ["register", "checklist", "report", "plan", "matrix", "sop", "mapping", "spec"],
        "writes": False,
        "cap": ("You do the filing yourself, on your own portal. Hoola prepares the papers, reminds you of dates "
                "and catches mistakes - but never submits anything on any government portal on your behalf."),
        "rules": ["No legal advice: the rule is cited, not an opinion.",
                  "The source of every date is written, otherwise it says 'not confirmed'."],
    },
}

# every role reads; these are the ones that may change something outside when she taps Haan
WRITERS = tuple(k for k, v in ROLES.items() if v["writes"])
CAPPED = tuple(k for k, v in ROLES.items() if v["cap"])

NEVER = (
    "No password, token or key for any enterprise system is taken in chat - it is connected through the app.",
    "Nothing is written in a production system without your approval.",
    "A number that did not come from the system is never written - it says 'not known'.",
    "Patient data, full account numbers and ID numbers never go into an artifact.",
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
        "blueprint":   {"label": "Blueprint / design", "say": "understands the business process to make the ERP design and gap list",
                        "papers": ["spec", "report", "plan"]},
        "functional":  {"label": "Functional consultant", "say": "module config - FI/CO, MM, SD, PP, HR - and its documentation",
                        "papers": ["config", "spec", "sop"]},
        "technical":   {"label": "Technical / ABAP", "say": "technical spec for custom reports, forms, enhancements, interfaces",
                        "papers": ["spec", "test_plan"]},
        "data":        {"label": "Data migration", "say": "data from the old system - field mapping, cleansing rules, load plan, reconciliation",
                        "papers": ["mapping", "plan", "checklist", "report"]},
        "integration": {"label": "Integration", "say": "connecting other systems - interfaces, middleware, error handling, resending",
                        "papers": ["spec", "mapping", "runbook", "test_plan"]},
        "basis":       {"label": "Basis / system admin", "say": "system upkeep, transports, patches, backups, performance",
                        "papers": ["runbook", "checklist", "report"]},
        "security":    {"label": "Security and authorisation", "say": "which role sees what, SoD conflicts, user access review",
                        "papers": ["matrix", "report", "checklist"]},
        "testing":     {"label": "Testing / UAT", "say": "test cases, UAT rounds, regression, defect list",
                        "papers": ["test_plan", "register", "report"]},
        "cutover":     {"label": "Cutover and go-live", "say": "hour-by-hour go-live plan, freeze, rollback, hypercare",
                        "papers": ["runbook", "checklist", "plan"]},
        "training":    {"label": "Training and change", "say": "teaching users - guides, step-by-step SOPs, who learns when",
                        "papers": ["training", "sop", "plan"]},
        "support":     {"label": "Support / AMS", "say": "tickets, incidents, root cause, SLA and a monthly report",
                        "papers": ["register", "report", "sop"]},
        "masterdata":  {"label": "Master data", "say": "vendor, customer, material, GL - one source of truth, catching duplicates and errors",
                        "papers": ["register", "checklist", "report"]},
        "reporting":   {"label": "Reporting and analytics", "say": "reports and dashboards from the ERP - where each number comes from",
                        "papers": ["spec", "mapping", "report"]},
        "finance_ops": {"label": "Finance close", "say": "month-end close schedule, reconciliation, controlling calculations",
                        "papers": ["checklist", "report", "sop"]},
        "licence":     {"label": "Licences and cost", "say": "how many users, which licence, what can be saved",
                        "papers": ["report", "register"]},
        "upgrade":     {"label": "Upgrade / patch", "say": "changing version - impact, test scope, rollback",
                        "papers": ["plan", "checklist", "test_plan", "report"]},
    },
    # A Salesforce practice is a desk too. The split that matters here is DATA (records: leads, accounts) versus
    # CONFIGURATION (objects, fields, flows, permission sets) - the second lives behind the Tooling API and can
    # break the org for everyone, which is why `api` is on the run and production config changes are never routine.
    # ---------------------------------------------------------------- the remaining seven desks
    "bpa": {
        "discover":  {"label": "Understanding the work", "say": "how the work is done today - every step, every hand",
                      "papers": ["spec", "mapping", "report"]},
        "design":    {"label": "Designing the new flow", "say": "which system does what, in which order",
                      "papers": ["spec", "plan", "mapping"]},
        "build":     {"label": "Building the flow", "say": "setting up the flow by connecting Composio apps",
                      "papers": ["runbook", "spec", "config"]},
        "exceptions": {"label": "When something breaks", "say": "what happens on failure - retry, stop, or hand to a person",
                       "papers": ["runbook", "checklist", "spec"]},
        "test":      {"label": "Testing", "say": "from one test record to the full load",
                      "papers": ["test_plan", "checklist", "report"]},
        "handover":  {"label": "Handing to the team", "say": "who runs it, what they watch, where to complain",
                      "papers": ["sop", "runbook", "matrix"]},
        "monitor":   {"label": "Monitoring", "say": "how many ran, how many got stuck, how much time was saved",
                      "papers": ["report", "register"]},
    },
    "ecom_arch": {
        "catalogue": {"label": "Catalogue", "say": "products, variants, photos, descriptions - what is incomplete",
                      "papers": ["report", "checklist", "mapping"]},
        "pricing":   {"label": "Prices", "say": "prices, discounts, tax - where they look wrong",
                      "papers": ["report", "register", "checklist"]},
        "stock":     {"label": "Stock", "say": "how much there is, how much is shown, oversell risk",
                      "papers": ["report", "checklist", "mapping"]},
        "checkout":  {"label": "Checkout", "say": "from cart to payment - where people drop off",
                      "papers": ["report", "test_plan", "plan"]},
        "payments":  {"label": "Payment", "say": "UPI / card / COD, what happens on failure, refunds",
                      "papers": ["spec", "runbook", "checklist"]},
        "shipping":  {"label": "Delivery", "say": "pin code, charge, courier, tracking",
                      "papers": ["mapping", "spec", "report"]},
        "peak":      {"label": "Getting ready for peak load", "say": "what will break on sale day - caught in advance",
                      "papers": ["checklist", "test_plan", "runbook"]},
        "integration": {"label": "Integration", "say": "connecting to ERP / accounting / courier",
                        "papers": ["spec", "mapping", "runbook"]},
    },
    "plm": {
        "parts":     {"label": "Part master", "say": "part number, name, revision - one source of truth",
                      "papers": ["register", "mapping", "checklist"]},
        "bom":       {"label": "BOM", "say": "which part goes where, how many, at which level",
                      "papers": ["report", "mapping", "spec"]},
        "change":    {"label": "Change order", "say": "impact of a change - which assemblies, which stock, which suppliers",
                      "papers": ["spec", "report", "checklist"]},
        "revision":  {"label": "Revision", "say": "which version is current, which is old",
                      "papers": ["register", "report"]},
        "supplier":  {"label": "Supplier parts", "say": "bought-in parts, their numbers, their place",
                      "papers": ["mapping", "register", "report"]},
        "cost":      {"label": "Cost", "say": "cost of the whole assembly, rolled up from the bottom",
                      "papers": ["report", "mapping"]},
        "docs":      {"label": "Drawings and documents", "say": "which drawing belongs to which part, which is latest",
                      "papers": ["register", "checklist", "mapping"]},
        "release":   {"label": "Release", "say": "from design to production - everything that is needed",
                      "papers": ["checklist", "runbook", "plan"]},
    },
    "supply_opt": {
        "demand":    {"label": "Demand", "say": "how much sells, which months sell more",
                      "papers": ["report", "mapping"]},
        "reorder":   {"label": "When to order", "say": "reorder point, safety stock, how much to order",
                      "papers": ["report", "register", "plan"]},
        "stock":     {"label": "Stock position", "say": "what is overstocked, what is about to run out",
                      "papers": ["report", "checklist", "register"]},
        "supplier":  {"label": "Supplier", "say": "who delivers on time, who is expensive",
                      "papers": ["matrix", "report", "register"]},
        "routes":    {"label": "Routes and freight", "say": "which route is cheapest, how much it costs",
                      "papers": ["report", "mapping", "plan"]},
        "warehouse": {"label": "Warehouse", "say": "what to keep where, how much space is needed",
                      "papers": ["plan", "report", "mapping"]},
        "service":   {"label": "Service level", "say": "how often stock ran out, how many orders were filled",
                      "papers": ["report", "register"]},
    },
    "health_int": {
        "abha":      {"label": "ABHA", "say": "the flow for creating and linking ABHA (M1)",
                      "papers": ["spec", "checklist", "plan"]},
        "fhir":      {"label": "FHIR R4", "say": "record structure - which resource, which field",
                      "papers": ["mapping", "spec", "checklist"]},
        "hip":       {"label": "Sharing records (M2)", "say": "link, discovery, care context - the HIP's work",
                      "papers": ["spec", "checklist", "plan"]},
        "hiu":       {"label": "Receiving records (M3)", "say": "requesting records with consent - the HIU's work",
                      "papers": ["spec", "checklist", "plan"]},
        "consent":   {"label": "Consent", "say": "permission for what, for how long, how it is withdrawn",
                      "papers": ["spec", "matrix", "checklist"]},
        "security":  {"label": "Security audit", "say": "papers and checklist for the CERT-In audit",
                      "papers": ["checklist", "register", "report"]},
        "mapping":   {"label": "From the old system", "say": "where your HMS fields go in FHIR",
                      "papers": ["mapping", "report", "spec"]},
    },
    "bank_int": {
        "recon":     {"label": "Reconciliation", "say": "statement and ledger reconciliation - what did not match",
                      "papers": ["report", "register", "mapping"]},
        "formats":   {"label": "File formats", "say": "structure of bank files, NACH and payment files",
                      "papers": ["mapping", "spec", "checklist"]},
        "aa_ready":  {"label": "Account Aggregator readiness", "say": "everything needed for AA - checklist",
                      "papers": ["checklist", "register", "report"]},
        "reporting": {"label": "Reports", "say": "daily / monthly reports, in which format",
                      "papers": ["report", "spec", "sop"]},
        "controls":  {"label": "Controls", "say": "who can do what, maker-checker",
                      "papers": ["matrix", "checklist", "register"]},
        "exceptions": {"label": "Unmatched items", "say": "failed, duplicate, circulating money - what to do",
                       "papers": ["register", "sop", "report"]},
    },
    "regtech": {
        "calendar":  {"label": "Compliance calendar", "say": "which date, whose task, what to submit",
                      "papers": ["register", "checklist", "plan"]},
        "filings":   {"label": "Filing papers", "say": "the full set before submitting",
                      "papers": ["checklist", "register", "report"]},
        "rules":     {"label": "Rules", "say": "which rule applies, where it is written",
                      "papers": ["register", "report", "mapping"]},
        "evidence":  {"label": "Evidence", "say": "which evidence is kept for which rule",
                      "papers": ["register", "matrix", "checklist"]},
        "breaches":  {"label": "Breaches", "say": "what was missed, how large the penalty can be",
                      "papers": ["report", "register", "plan"]},
        "audit":     {"label": "Audit", "say": "the set of auditor questions and their answers",
                      "papers": ["checklist", "register", "report"]},
        "policy":    {"label": "Policy and SOP", "say": "writing internal rules and getting them to the team",
                      "papers": ["sop", "spec", "checklist"]},
    },
    "crm_arch": {
        "admin":       {"label": "Admin", "say": "users, licences, login problems, daily upkeep",
                        "papers": ["sop", "register", "checklist"]},
        "config":      {"label": "Object and field config", "say": "objects, fields, page layouts, record types - and why",
                        "papers": ["config", "spec", "matrix"]},
        "automation":  {"label": "Flows and automation", "say": "flows, validation rules, approval processes - what runs when",
                        "papers": ["spec", "test_plan", "runbook"]},
        "apex":        {"label": "Apex / code", "say": "Apex classes, triggers, test coverage",
                        "papers": ["spec", "test_plan"]},
        "integration": {"label": "Integration", "say": "connecting other systems, named credentials, platform events",
                        "papers": ["spec", "mapping", "runbook", "test_plan"]},
        "data":        {"label": "Data work", "say": "imports, duplicate cleanup, mass updates, data health",
                        "papers": ["mapping", "plan", "checklist", "report"]},
        "security":    {"label": "Profiles and sharing", "say": "profiles, permission sets, sharing rules, field-level security",
                        "papers": ["matrix", "report", "checklist"]},
        "reporting":   {"label": "Reports and dashboards", "say": "reports, dashboards, list views - where each number comes from",
                        "papers": ["spec", "mapping", "report"]},
        "testing":     {"label": "Testing / UAT", "say": "test cases, UAT, regression, defect list",
                        "papers": ["test_plan", "register", "report"]},
        "release":     {"label": "Release and deployment", "say": "sandbox to production, change sets, rollback",
                        "papers": ["runbook", "checklist", "plan"]},
        "adoption":    {"label": "Adoption and training", "say": "teaching users, SOPs, who is using what",
                        "papers": ["training", "sop", "report"]},
        "support":     {"label": "User support", "say": "user questions, bugs, 'how does this work', SLA",
                        "papers": ["register", "report", "sop"]},
    },
    # The TPM desk. It deliberately does NOT repeat the product side (discovery, scoring, PRDs, releases) - that
    # lives in the far richer `product` tool. What is here is the engineering layer a technical PM actually holds:
    # what blocks what, what was decided and why, what must be true to ship, and what is owed.
    "tpm": {
        "roadmap":      {"label": "Technical roadmap", "say": "now / next / later - across teams, from the engineering view",
                         "papers": ["plan", "report"]},
        "dependencies": {"label": "Dependencies and critical path", "say": "who is blocked on whom, and the longest path",
                         "papers": ["matrix", "report", "register"]},
        "architecture": {"label": "Architecture decisions", "say": "what was decided, why, and what was left out (ADR)",
                         "papers": ["spec", "register", "report"]},
        "nfr":          {"label": "NFR", "say": "speed, scale, uptime, security - what must be true before shipping",
                         "papers": ["spec", "checklist", "report"]},
        "debt":         {"label": "Technical debt", "say": "what debt is outstanding, its interest, and the plan to pay it off",
                         "papers": ["register", "plan", "report"]},
        "capacity":     {"label": "Capacity", "say": "how much time the team has and how much is already promised",
                         "papers": ["report", "plan", "matrix"]},
        "release":      {"label": "Release train", "say": "what is in which release, go / no-go, who signs off",
                         "papers": ["checklist", "runbook", "plan"]},
        "risk":         {"label": "RAID", "say": "risks, assumptions, issues, dependencies - in one place, each with an owner",
                         "papers": ["register", "report"]},
        "vendor":       {"label": "Build or buy", "say": "build vs buy, vendor comparison, what is missing",
                         "papers": ["report", "matrix", "spec"]},
        "incident":     {"label": "Incident follow-up", "say": "work left after the post-mortem - until it is closed",
                         "papers": ["register", "report", "sop"]},
        "metrics":      {"label": "Delivery numbers", "say": "lead time, escaped defects, promised vs delivered",
                         "papers": ["report", "mapping"]},
        "status":       {"label": "Status and escalation", "say": "weekly note, what is blocked, who to tell",
                         "papers": ["report", "sop"]},
    },
}


def jobs_of(role_key: str) -> dict[str, dict[str, Any]]:
    return JOBS.get(role_key, {})


def job_papers(role_key: str, job: str) -> list[str]:
    """The paper kinds that sub-job really produces; the role's full list when it has no sub-jobs."""
    j = JOBS.get(role_key, {}).get(job)
    return list(j["papers"]) if j else list(role(role_key)["artifacts"])
