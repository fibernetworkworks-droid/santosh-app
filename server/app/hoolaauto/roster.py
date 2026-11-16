"""HOOLA AUTO fixed lists: the agents, the intake questions, the gates. Plain data - every screen reads these."""
from __future__ import annotations

# key, label, group (plan | build | check | ship), Hoola Code session kind (None = works with one model call, no session),
# what it does (shown on the review screen and given to the agent as its role)
ROLES: list[tuple[str, str, str, str | None, str]] = [
    ("intake", "Intake", "plan", None, "Collects every input from the client and marks where each answer came from."),
    ("analyst", "Analyst", "plan", None, "Turns the intake into user stories with acceptance criteria."),
    ("architect", "Architect", "plan", None, "Designs the system: parts, data, APIs and the risks."),
    ("ux", "UX", "plan", None, "Designs the screens and the flow between them."),
    ("planner", "Planner + Cost", "plan", None, "Splits the work into tasks and sprints and prices it."),
    ("builder_web", "Builder · web", "build", "write", "Builds the web app screens."),
    ("builder_api", "Builder · API", "build", "write", "Builds the server, the API and the business rules."),
    ("builder_mobile", "Builder · mobile", "build", "write", "Builds the phone app."),
    ("builder_data", "Builder · data", "build", "write", "Builds the database, migrations and data imports."),
    ("test", "Test", "check", "tests", "Writes tests for every story before and after it is built."),
    ("security", "Security", "check", "explain", "Reads the code for security and privacy problems and reports them."),
    ("reviewer", "Reviewer", "check", None, "Reviews every change before it joins the project branch."),
    ("qa", "QA", "check", "tests", "Tests whole journeys end to end before your UAT."),
    ("devops", "DevOps", "ship", "write", "Sets up CI, the build and staging deploys."),
    ("release", "Release", "ship", None, "Opens the go-live pull request to your main branch at G7."),
    ("docs", "Docs", "ship", "docs", "Writes the README, the runbook and the handover pack."),
]
ROLE = {r[0]: r for r in ROLES}
SESSION_ROLES = {r[0] for r in ROLES if r[3]}


def label(role: str) -> str:
    return ROLE.get(role, (role, role.replace("_", " ").title()))[1]


# The intake: 10 sections, 30 questions. key, question, choices (tap answers; empty = typed)
INTAKE: list[tuple[str, list[tuple[str, str, list[str]]]]] = [
    ("Business goals", [
        ("goal", "What should this project achieve for the business?", []),
        ("success", "How will you know it worked? (a number, if you have one)", []),
        ("deadline", "Is there a date it must be ready by?", ["No fixed date", "Within a month", "Within 3 months"]),
    ]),
    ("Users and roles", [
        ("roles", "Who will use it? (for example: customer, front desk, manager)", []),
        ("user_count", "About how many people will use it?", ["Under 100", "100 to 10,000", "Over 10,000"]),
        ("languages", "Which languages must it support?", ["English", "English and Hindi", "English, Hindi and a regional language"]),
    ]),
    ("Features", [
        ("must_have", "What must it do on day one?", []),
        ("nice_to_have", "What would be nice, but can wait?", []),
        ("out_of_scope", "Anything it must NOT do in this project?", []),
        ("platforms", "Where will people use it?", ["Website", "Android app", "Website and Android app", "Website, Android and iPhone"]),
    ]),
    ("Data", [
        ("existing_data", "Is there existing data to bring in? Where is it now?", ["Nothing to bring in", "Spreadsheet / CSV", "Another software"]),
        ("data_rules", "Any rules about the data (who can see what, how long to keep it)?", []),
    ]),
    ("Integrations", [
        ("payments", "Which payment gateway should take payments?", ["Razorpay", "Cashfree", "PhonePe", "No online payment"]),
        ("messaging", "Should it send messages?", ["WhatsApp", "SMS", "Email", "WhatsApp and email", "No messages"]),
        ("other_systems", "Which other systems must it talk to?", []),
        ("api_docs", "Are there API documents for those systems? (upload them as a source)", ["Yes, I will upload them", "No documents", "No other systems"]),
    ]),
    ("Speed, security, laws", [
        ("performance", "How fast must it be, and for how many people at once?", []),
        ("security", "Anything special about security (login, roles, approvals)?", []),
        ("compliance", "Which rules apply? (GST invoices, DPDP privacy, health or finance rules)", ["GST invoices", "DPDP privacy only", "Health data rules", "Finance rules", "Nothing special"]),
    ]),
    ("Brand", [
        ("brand", "Brand colours and fonts? (or a link to the current website)", []),
        ("logo", "Is there a logo? (upload it as a source)", ["Yes, I will upload it", "No logo yet"]),
    ]),
    ("Access and accounts", [
        ("repos", "Which code repositories does Hoola work in?", []),
        ("test_accounts", "Which test accounts can the agents use? (never real passwords here)", ["I will add test keys in Environments", "No test accounts needed"]),
        ("store_accounts", "Who owns the Play Store / App Store accounts?", ["Our company", "The client", "Not needed"]),
        ("hosting", "Where will it run?", ["Our own server", "AWS", "Google Cloud", "Not decided"]),
    ]),
    ("People who decide", [
        ("decider", "Who signs off at each gate?", []),
        ("reviewers", "Who else should see the sprint demos?", []),
    ]),
    ("Contract terms", [
        ("budget", "What is the budget range?", []),
        ("timeline", "What timeline was agreed?", ["4 weeks", "6 weeks", "8 weeks", "3 months"]),
        ("support", "How long is support after go-live?", ["1 month", "3 months", "6 months", "None"]),
    ]),
]
FIELDS: dict[str, tuple[str, str, list[str]]] = {k: (sec, q, ch) for sec, rows in INTAKE for k, q, ch in rows}
ORDER: list[str] = [k for _sec, rows in INTAKE for k, _q, _ch in rows]

SOURCE_LABEL = {"form": "Client form", "doc": "Document", "call": "Recording", "repo": "Repo scan", "chat": "Pasted chat",
                "you": "You", "client": "Client", "": "Not given yet"}

# The 8 gates. code, name, when, what her tap means
GATES: list[tuple[str, str, str, str]] = [
    ("G1", "Scope sign-off", "now", "Fixes what will be built. The design starts."),
    ("G2", "Design approval", "after design", "Fixes how it will look and work. Planning starts."),
    ("G3", "Plan + price", "after planning", "Fixes the tasks, sprints and the cost cap. The agents start building."),
    ("G4", "Sprint demo", "after each sprint", "Accepts the sprint. The next sprint starts."),
    ("G5", "Change approval", "when asked", "Adds the change with its own price."),
    ("G6", "UAT sign-off", "after the last sprint", "You tested it. Go-live is prepared."),
    ("G7", "Go-live", "after UAT", "Opens the pull request to your main branch. Merging it is one more tap."),
    ("G8", "Handover", "after go-live", "Accepts the handover pack. The project is closed."),
]
GATE = {g[0]: g for g in GATES}
PHASES = [("intake", "Intake"), ("review", "Requirements"), ("design", "Design"), ("plan", "Plan"), ("build", "Build"),
          ("uat", "QA + UAT"), ("golive", "Release"), ("handover", "Handover")]
