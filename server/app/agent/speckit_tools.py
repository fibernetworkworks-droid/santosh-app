"""v0.560.0 SPEC SUTRA - the spec-driven ladder (the github/spec-kit idea, house-sized, end to end).

Owner: "FEED THIS TO HOOLA AI . GIT SPEC KIT TO HOOLA END TO END" after the full READ of
github.com/github/spec-kit (MIT, READ archived at download/SPEC_KIT_READ.md). ZERO spec-kit code
exists here (the house port law keeps even MIT code out) - what is kept is the IDEA: code serves
the specification, not the other way round. The ladder the spec-kit commands teach, ported as ONE
tool `speckit` the model runs before any real software build:

  constitution -> specify -> clarify -> plan -> tasks -> (build, the model's own way) ->
  analyze -> converge (repeat until verdict=converged)

The five spec-kit disciplines that survive the port (all code-enforced, none trusted to the model):
1. SPEC = WHAT/WHY, never HOW: the spec carries intent + features + stories + success metrics;
   a light how-leak scanner flags stack words that already choose an implementation (a warning,
   never a block - code cannot judge semantics, so it never pretends to).
2. NEVER GUESS: unanswered points must ride the spec as [NEEDS CLARIFICATION: ...] markers
   (max 5); action=clarify orders them scope > security > UX > technical (spec-kit's priority)
   and records her answers - an open marker BLOCKS analyze (never build on a guess).
3. THE CONSTITUTION: project laws as a checked artifact, not prose. A project gets the house
   starter (Simplicity, Anti-Abstraction, Test-First, Integration-First, Traceability) unless it
   ratifies its own; the plan must check every law, and a violation carries its justification
   (spec-kit's complexity-tracking table). Amendments need a documented rationale and are logged.
4. TRACEABILITY: every task is numbered T### and MUST name its requirement (FR-### / US#-AC# /
   SC-###) - analyze refuses "clean" while a P1 requirement has no task, and a task naming a
   requirement that does not exist is rejected at write time (no ghost refs).
5. THE CONVERGE LOOP: after a build round the model reports done tasks + gaps found (missing /
   partial / contradicts / unrequested); the tool APPENDS convergence tasks - existing spec, plan
   and tasks are never rewritten (append-only, spec-kit's law; the tasks action refuses to rewrite
   after the first round) - and repeats until the computed verdict says "converged" (all tasks
   done, no open gaps). Code computes the verdict; the model only reports what it saw.

Storage: per-tenant SQLite beside the other lanes - data/speckit/<tenant>/speckit.db (projects).
Every artifact is written ONCE (specify creates the project; nothing rewrites it). The only
post-write mutations are clarify's recorded answers, constitution amendments (rationale logged)
and converge's status flips + task appends. All offline: no network, no model calls, no keys.

Envelope (the discipline-tool shape v0.559 established): {schema_version, ok, tool, action,
project_id, stage, ..., meta{elapsed_ms, ...}, error{code, message, hint}} - OUT_OF_ORDER.hint
names the ladder step to run first; the model branches on ok / error.code, never on prose.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..config import get_settings
from .tools import Ctx

SCHEMA_VERSION = 1
TOOL_NAME = "speckit"

_IST = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------------- error codes (the ladder's discipline)
NEED_SETUP = "NEED_SETUP"        # speckit is turned off on this server
BAD_INPUT = "BAD_INPUT"          # the arguments were rejected (the message names what and why)
NOT_FOUND = "NOT_FOUND"          # project_id unknown for this tenant
OUT_OF_ORDER = "OUT_OF_ORDER"    # a ladder step was skipped - the hint names the step to run first
CONFLICT = "CONFLICT"            # the write would break an append-only / once-only law

VALID_ACTIONS = ("constitution", "specify", "clarify", "plan", "tasks", "analyze", "converge", "list")
PRIORITIES = ("P1", "P2", "P3")
PHASES = ("setup", "foundational", "story", "polish", "convergence")
GAP_TYPES = ("missing", "partial", "contradicts", "unrequested")
SEVERITIES = ("critical", "major", "minor")
GATE_STATUS = ("pass", "violation", "na")
_PHASE_RANK = {p: i for i, p in enumerate(PHASES)}

#: The house STARTER constitution - what a project gets when it ratifies none of its own
#: (spec-kit's default template, house-adapted to five laws the suites can actually assert).
STARTER_CONSTITUTION = [
    {"id": "I", "title": "Simplicity", "text": "At most 3 moving parts per build unless a written "
     "justification names the simpler alternative that was rejected."},
    {"id": "II", "title": "Anti-Abstraction", "text": "Use the framework / platform directly; a new "
     "abstraction layer needs its own justification against using what already exists."},
    {"id": "III", "title": "Test-First", "text": "A fix or feature is not done until a test that "
     "fails without it exists and passes with it. NON-NEGOTIABLE."},
    {"id": "IV", "title": "Integration-First", "text": "Prove it against the real door (real "
     "database, real API) before trusting a mock; mocks are scaffolding, not evidence."},
    {"id": "V", "title": "Traceability", "text": "Every task names the requirement it serves "
     "(FR/US/AC/SC); work no requirement asked for is flagged, not silently kept."},
]

# ---------------------------------------------------------------- caps (generous, but the envelope stays small)
_MAX_FEATURES = 40
_MAX_STORIES = 30
_MAX_SCENARIOS = 10
_MAX_METRICS = 20
_MAX_TASKS = 120
_MAX_MARKERS = 5
_MAX_ANSWERS = 10
_MAX_DECISIONS = 20
_MAX_GAPS = 30
_MAX_ARTICLES = 12
_NAME_CHARS = 80
_INTENT_CHARS = 2000
_DETAIL_CHARS = 1200
_TITLE_CHARS = 200
_TEXT_CHARS = 900
_JUST_CHARS = 600
_ANSWER_CHARS = 600
_DESC_CHARS = 400

_MARKER_RE = re.compile(r"\[NEEDS CLARIFICATION:\s*([^\]]{3,300})\]")

# spec = WHAT/WHY never HOW: a light scanner (a warning, never a block).
_HOW_WORDS = ("react", "flutter", "postgres", "postgresql", "mysql", "mongodb", "redis", "kubernetes",
              "docker", "node.js", "nodejs", "next.js", "nextjs", "django", "fastapi", "sqlite",
              "microservice", "websockets", "graphql", "kafka", "terraform", "aws", "gcp", "azure")

# clarify priority (spec-kit's order): scope > security/privacy > UX > technical.
_CLASS_ORDER = ("scope", "security", "ux", "technical")
_CLASS_WORDS = {
    "scope": ("scope", "include", "exclude", "coverage", "feature", "kya", "priority", "which", "kaun"),
    "security": ("security", "privacy", "auth", "permission", "consent", "encryption", "password",
                 "otp", "pii", "aadhaar", "suraksha", "data kaun", "personal data"),
    "ux": ("ux", "ui", "design", "layout", "look", "feel", "screen", "theme", "hindi", "english",
           "language", "mobile", "font", "colour", "color", "accessib"),
    "technical": ("api", "database", "latency", "scale", "performance", "infra", "deploy", "library",
                  "framework", "integration", "rate limit", "cache", "offline", "sync"),
}

_REF_RE = re.compile(r"^(FR-\d{1,3}|US\d{1,2}(-AC\d{1,2})?|SC-\d{1,3})$")


# ---------------------------------------------------------------- store (per-tenant sqlite)
def _db_path(tenant_id: str) -> Path:
    return Path("data") / "speckit" / tenant_id / "speckit.db"


def _con(tenant_id: str) -> sqlite3.Connection:
    _db_path(tenant_id).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_db_path(tenant_id)), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT UNIQUE, "
                "stage TEXT DEFAULT 'specified', constitution TEXT, spec TEXT, plan TEXT, "
                "tasks TEXT DEFAULT '[]', converge_log TEXT DEFAULT '[]', "
                "created_at REAL, updated_at REAL)")
    return con


def _load_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _get(con: sqlite3.Connection, project_id: str) -> dict | None:
    r = con.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["constitution"] = _load_json(d.get("constitution"), None)
    d["spec"] = _load_json(d.get("spec"), None)
    d["plan"] = _load_json(d.get("plan"), None)
    d["tasks"] = _load_json(d.get("tasks"), [])
    d["converge_log"] = _load_json(d.get("converge_log"), [])
    return d


def _save(con: sqlite3.Connection, pid: str, **cols) -> None:
    cols["updated_at"] = time.time()
    sets = ", ".join(f"{k} = ?" for k in cols)
    con.execute(f"UPDATE projects SET {sets} WHERE id = ?", (*cols.values(), pid))
    con.commit()


def _now_iso() -> str:
    """Sortable local time (IST) - amendment-vs-plan comparison reads it as plain text."""
    return datetime.now(_IST).strftime("%Y-%m-%d %H:%M")


def _ts_of(epoch: float | None) -> str:
    return _now_iso() if not epoch else datetime.fromtimestamp(epoch, _IST).strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- envelope (the v0.559 discipline shape)
def envelope(action: str, project_id: str | None = None, stage: str | None = None,
             error: tuple[str, str, str] | None = None, elapsed_ms: int = 0, **fields) -> dict:
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "ok": error is None, "tool": TOOL_NAME,
                           "action": action, "project_id": project_id, "stage": stage,
                           "error": (None if error is None else
                                     {"code": error[0], "message": error[1], "hint": error[2]})}
    out.update(fields)
    meta = dict(out.pop("meta", {}) or {})
    out["meta"] = {"elapsed_ms": max(0, int(elapsed_ms)), **meta}
    return out


def _bad(action: str, msg: str, hint: str = "") -> dict:
    return envelope(action, error=(BAD_INPUT, msg, hint or "Fix the arguments and call again."))


# ---------------------------------------------------------------- the spec-kit scanners
def scan_markers(text: str) -> list[str]:
    """The [NEEDS CLARIFICATION: question] markers the spec honestly carries (never a guess)."""
    return [m.strip() for m in _MARKER_RE.findall(text or "")]


def classify_question(q: str) -> str:
    """spec-kit's clarify priority: scope > security/privacy > UX > technical."""
    low = (q or "").lower()
    for klass in _CLASS_ORDER:
        if any(w in low for w in _CLASS_WORDS[klass]):
            return klass
    return "scope"


def how_leaks(text: str) -> list[str]:
    """Stack words that already choose the HOW (a warning - code never judges semantics)."""
    low = (text or "").lower()
    return [w for w in _HOW_WORDS if w in low]


def _roman(n: int) -> str:
    vals = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def _clean(text: object, cap: int) -> str:
    return " ".join(str(text or "").split())[:cap]


def _ref_exists(spec: dict, ref: str) -> bool:
    ids = {f["id"] for f in spec.get("features") or []}
    ids |= {s["id"] for s in spec.get("stories") or []}
    for s in spec.get("stories") or []:
        ids |= {a["id"] for a in s.get("scenarios") or []}
    ids |= {m["id"] for m in spec.get("metrics") or []}
    return ref in ids


def _open_markers(spec: dict) -> list[dict]:
    resolved = {c["question"] for c in spec.get("clarifications") or []}
    return [m for m in spec.get("markers") or [] if m["question"] not in resolved]


def _ordered_open(spec: dict) -> list[dict]:
    return sorted(_open_markers(spec), key=lambda m: _CLASS_ORDER.index(m.get("klass", "scope")))


# ---------------------------------------------------------------- action: constitution
def _do_constitution(con: sqlite3.Connection, articles: list | None, rationale: str | None,
                     project_id: str | None) -> dict:
    if not project_id and not articles:
        return envelope("constitution", items=[dict(a) for a in STARTER_CONSTITUTION],
                        say="This is the starter constitution every project gets until it ratifies its own.",
                        meta={"starter": True})
    if not project_id:
        return _bad("constitution", "setting a constitution needs the project to set it on (action=list shows ids)",
                    "Run action=specify first, then action=constitution with project_id.")
    p = _get(con, project_id)
    if p is None:
        return envelope("constitution", error=(NOT_FOUND, f"no project {project_id}",
                                               "action=list shows this tenant's projects."))
    if not articles:
        arts = p.get("constitution") or {"articles": STARTER_CONSTITUTION, "amendments": []}
        return envelope("constitution", project_id, p["stage"], items=arts["articles"],
                        amendments=arts.get("amendments") or [],
                        meta={"starter": p.get("constitution") is None})
    if not isinstance(articles, list) or not (1 <= len(articles) <= _MAX_ARTICLES):
        return _bad("constitution", f"articles must be a list of 1..{_MAX_ARTICLES} {{title, text}}")
    clean: list[dict] = []
    for i, a in enumerate(articles, 1):
        if not isinstance(a, dict) or not str(a.get("title") or "").strip() or not str(a.get("text") or "").strip():
            return _bad("constitution", f"article {i} needs a title and text")
        clean.append({"id": _roman(i), "title": _clean(a.get("title"), 120),
                      "text": _clean(a.get("text"), _TEXT_CHARS)})
    if not str(rationale or "").strip():
        return _bad("constitution", "an amendment without a documented rationale is not a law (the spec-kit rule)",
                    "Say in one line WHY these laws, and what they replace.")
    after_plan = bool(p.get("plan"))
    arts = {"articles": clean,
            "amendments": (p.get("constitution") or {}).get("amendments", [])
            + [{"at": _now_iso(), "rationale": _clean(rationale, _JUST_CHARS), "articles": len(clean),
                "after_plan": after_plan}]}
    _save(con, project_id, constitution=json.dumps(arts))
    return envelope("constitution", project_id, p["stage"], items=clean,
                    meta={"amended": True, "rationale_logged": True,
                          **({"note": "constitution changed after the plan - action=analyze will note the re-check"}
                             if after_plan else {}),
                          "say": f"{len(clean)} law(s) ratified and logged"})


# ---------------------------------------------------------------- action: specify
def _do_specify(con: sqlite3.Connection, ctx: Ctx, name: str | None, intent: str | None,
                features: list | None, stories: list | None, metrics: list | None) -> dict:
    name_c = _clean(name, _NAME_CHARS)
    if len(name_c) < 2:
        return _bad("specify", "name the project (2..80 chars) - it is how list and clarify find it again")
    if con.execute("SELECT 1 FROM projects WHERE name = ?", (name_c,)).fetchone():
        return envelope("specify", error=(CONFLICT, f"a project named '{name_c}' already exists",
                                          "Names are once-only; pick a new name or action=list to see it."))
    intent_c = _clean(intent, _INTENT_CHARS)
    if len(intent_c) < 10:
        return _bad("specify", "intent is the spec's heart: what should exist and why, in one honest line (10+ chars)",
                    "WHAT and WHY only - the HOW belongs to action=plan.")
    if not isinstance(features, list) or not (1 <= len(features) <= _MAX_FEATURES):
        return _bad("specify", f"features must be a list of 1..{_MAX_FEATURES} {{title, priority, detail}}")
    if stories is not None and not isinstance(stories, list):
        return _bad("specify", "stories must be a list of {title, priority, scenarios}")
    if metrics is not None and not isinstance(metrics, list):
        return _bad("specify", "metrics must be a list of {name, target}")
    feats, texts = [], [intent_c]
    for i, f in enumerate(features, 1):
        if not isinstance(f, dict) or not str(f.get("title") or "").strip():
            return _bad("specify", f"feature {i} needs a title")
        pr = str(f.get("priority") or "P3").upper()
        if pr not in PRIORITIES:
            return _bad("specify", f"feature {i} priority must be one of {', '.join(PRIORITIES)} (P1 is the MVP slice)",
                        "spec-kit's law: at least one P1 - without it there is no first working slice.")
        detail = _clean(f.get("detail"), _DETAIL_CHARS)
        texts.append(detail)
        feats.append({"id": f"FR-{i:03d}", "title": _clean(f.get("title"), 120), "priority": pr, "detail": detail})
    if not any(f["priority"] == "P1" for f in feats):
        return _bad("specify", "no P1 feature: the spec has no MVP slice to build first",
                    "Mark the one feature that alone is worth shipping as P1.")
    sts = []
    for i, s in enumerate(stories or [], 1):
        if not isinstance(s, dict) or not str(s.get("title") or "").strip():
            return _bad("specify", f"story {i} needs a title")
        pr = str(s.get("priority") or "P2").upper()
        if pr not in PRIORITIES:
            return _bad("specify", f"story {i} priority must be P1, P2 or P3")
        scen = []
        for j, sc in enumerate((s.get("scenarios") or [])[:_MAX_SCENARIOS], 1):
            if not isinstance(sc, dict):
                return _bad("specify", f"story {i} scenario {j} must be {{given, when, then}}")
            scen.append({"id": f"US{i}-AC{j}", "given": _clean(sc.get("given"), 300),
                         "when": _clean(sc.get("when"), 300), "then": _clean(sc.get("then"), 300)})
        sts.append({"id": f"US{i}", "title": _clean(s.get("title"), 120), "priority": pr, "scenarios": scen})
    mts = []
    for i, m in enumerate(metrics or [], 1):
        if not isinstance(m, dict) or not str(m.get("name") or "").strip():
            return _bad("specify", f"metric {i} needs a name")
        mts.append({"id": f"SC-{i:03d}", "name": _clean(m.get("name"), 120), "target": _clean(m.get("target"), 200)})
    markers: list[dict] = []
    marker_texts = [("intent", intent_c)] + [(f["id"], f.get("detail") or "") for f in feats] \
        + [(s["id"], s.get("title") or "") for s in sts]
    for where, txt in marker_texts:
        for q in scan_markers(txt):
            if len(markers) >= _MAX_MARKERS:
                return _bad("specify", f"more than {_MAX_MARKERS} [NEEDS CLARIFICATION] markers: the spec is "
                                       f"too vague to build from",
                            f"Keep the {_MAX_MARKERS} unknowns that truly block the build and write your best "
                            "documented guess for the rest (spec-kit's cap).")
            markers.append({"question": q.strip()[:300], "where": where, "klass": classify_question(q)})
    leaks = [{"where": "intent", "words": w} for w in [how_leaks(intent_c)] if w]
    leaks += [{"where": f["id"], "words": w} for f in feats if (w := how_leaks(f.get("detail")))]
    pid = "sp_" + uuid.uuid4().hex[:10]
    spec = {"name": name_c, "intent": intent_c, "features": feats, "stories": sts, "metrics": mts,
            "markers": markers, "clarifications": [], "how_leaks": leaks, "created_at": _now_iso()}
    now = time.time()
    con.execute("INSERT INTO projects (id, name, stage, constitution, spec, tasks, converge_log, created_at, updated_at) "
                "VALUES (?, ?, 'specified', NULL, ?, '[]', '[]', ?, ?)",
                (pid, name_c, json.dumps(spec), now, now))
    con.commit()
    return envelope("specify", pid, "specified",
                    spec={"features": feats, "stories": sts, "metrics": mts, "markers": markers},
                    meta={"requirements": len(feats), "stories": len(sts), "success_metrics": len(mts),
                          "open_unknowns": len(markers), "next": "clarify" if markers else "plan",
                          **({"how_leaks": leaks} if leaks else {})},
                    say=(f"{len(markers)} open unknown(s) - run action=clarify" if markers
                         else "spec written; run action=plan"))


# ---------------------------------------------------------------- action: clarify
def _do_clarify(con: sqlite3.Connection, ctx: Ctx, project_id: str | None, answers: list | None) -> dict:
    if not project_id:
        return _bad("clarify", "which project? pass project_id (action=list shows ids)")
    p = _get(con, project_id)
    if p is None:
        return envelope("clarify", error=(NOT_FOUND, f"no project {project_id}",
                                          "action=list shows this tenant's projects."))
    spec = p.get("spec")
    if not spec:
        return envelope("clarify", error=(OUT_OF_ORDER, "clarify needs a spec to clarify",
                                          "Run action=specify first - never guess what the spec should say."))
    ordered = _ordered_open(spec)
    if not answers:
        items = [{"id": f"Q{i}", "klass": m["klass"], "question": m["question"], "where": m["where"],
                  "how": "give her 2-4 options with what each costs; she picks - the answer is recorded, never guessed"}
                 for i, m in enumerate(ordered[:_MAX_MARKERS], 1)]
        return envelope("clarify", project_id, p["stage"], items=items,
                        meta={"open_unknowns": len(ordered), "resolved": len(spec.get("clarifications") or []),
                              "order": "scope > security > UX > technical"},
                        say=("no open unknowns - run action=plan" if not ordered
                             else "ask her these; record each answer with answers:[{id, answer}]"))
    if not isinstance(answers, list) or not answers or len(answers) > _MAX_ANSWERS:
        return _bad("clarify", f"answers must be a list of 1..{_MAX_ANSWERS} {{id: 'Q1', answer}}")
    by_id = {f"Q{i}": m for i, m in enumerate(ordered[:_MAX_MARKERS], 1)}
    before = len(spec.get("clarifications") or [])
    clar = list(spec.get("clarifications") or [])
    for a in answers:
        if not isinstance(a, dict) or str(a.get("id") or "") not in by_id:
            return _bad("clarify", f"answer id must be one of {', '.join(by_id) or '(none open)'} - the open list just shown")
        if not str(a.get("answer") or "").strip():
            return _bad("clarify", f"answer {a.get('id')} is empty - 'she has not answered yet' is honest, blank is not")
        m = by_id[str(a["id"])]
        clar.append({"id": str(a["id"]), "klass": m["klass"], "question": m["question"],
                     "answer": _clean(a.get("answer"), _ANSWER_CHARS), "at": _now_iso()})
    spec = {**spec, "clarifications": clar}
    _save(con, project_id, spec=json.dumps(spec))
    left = len(_open_markers(spec))
    return envelope("clarify", project_id, p["stage"],
                    meta={"resolved_now": len(clar) - before, "open_unknowns": left, "resolved_total": len(clar)},
                    say=("all unknowns answered - run action=plan" if left == 0
                         else f"{left} still open; ask again"))


# ---------------------------------------------------------------- action: plan
def _do_plan(con: sqlite3.Connection, ctx: Ctx, project_id: str | None, decisions: list | None,
             gates: list | None) -> dict:
    if not project_id:
        return _bad("plan", "which project? pass project_id (action=list shows ids)")
    p = _get(con, project_id)
    if p is None:
        return envelope("plan", error=(NOT_FOUND, f"no project {project_id}",
                                       "action=list shows this tenant's projects."))
    if not p.get("spec"):
        return envelope("plan", error=(OUT_OF_ORDER, "plan needs a spec to plan from",
                                       "Run action=specify first - a plan without a spec is a guess."))
    arts = (p.get("constitution") or {}).get("articles") or STARTER_CONSTITUTION
    starter = p.get("constitution") is None
    gates = gates if isinstance(gates, list) else []
    by_article: dict[str, dict] = {}
    for g in gates:
        if not isinstance(g, dict):
            return _bad("plan", "each gate must be {article, status, justification}")
        aid = str(g.get("article") or "").strip().upper()
        st = str(g.get("status") or "").lower()
        if st not in GATE_STATUS:
            return _bad("plan", f"gate {aid or '?'}: status must be pass | violation | na")
        if st == "violation" and not str(g.get("justification") or "").strip():
            return _bad("plan", f"gate {aid}: a violation without its justification is not allowed (the "
                                f"complexity-tracking rule)",
                        "Name what the violation buys and the simpler alternative it beat.")
        by_article[aid] = {"article": aid, "status": st,
                           "justification": _clean(g.get("justification"), _JUST_CHARS)}
    missing = [a["id"] for a in arts if a["id"] not in by_article]
    if missing:
        return _bad("plan", f"every law must be checked: missing gates for {', '.join(missing)}",
                    "pass = how the plan honours it; violation = with justification; na = why it cannot apply.")
    if decisions is not None and (not isinstance(decisions, list) or len(decisions) > _MAX_DECISIONS):
        return _bad("plan", f"decisions must be a list of 0..{_MAX_DECISIONS} {{topic, decision, why}}")
    dec = []
    for d in (decisions or []):
        if not isinstance(d, dict) or not str(d.get("topic") or "").strip() or not str(d.get("decision") or "").strip():
            return _bad("plan", "each decision needs a topic and the decision")
        dec.append({"topic": _clean(d.get("topic"), 120), "decision": _clean(d.get("decision"), _JUST_CHARS),
                    "why": _clean(d.get("why"), _JUST_CHARS)})
    plan = {"decisions": dec, "gates": [by_article[a["id"]] for a in arts],
            "constitution_ids": [a["id"] for a in arts], "starter_constitution": starter,
            "checked_at": _now_iso()}
    _save(con, project_id, plan=json.dumps(plan), stage="planned")
    return envelope("plan", project_id, "planned", plan={"decisions": dec, "gates": plan["gates"]},
                    meta={"laws_checked": len(arts),
                          "violations": sum(1 for g in plan["gates"] if g["status"] == "violation"),
                          "starter_constitution": starter},
                    say="plan checked against every law; run action=tasks next")


# ---------------------------------------------------------------- action: tasks
def _do_tasks(con: sqlite3.Connection, ctx: Ctx, project_id: str | None, tasks: list | None) -> dict:
    if not project_id:
        return _bad("tasks", "which project? pass project_id (action=list shows ids)")
    p = _get(con, project_id)
    if p is None:
        return envelope("tasks", error=(NOT_FOUND, f"no project {project_id}",
                                        "action=list shows this tenant's projects."))
    if not p.get("spec"):
        return envelope("tasks", error=(OUT_OF_ORDER, "tasks before a spec trace to nothing",
                                        "Run action=specify first - every task must name its requirement."))
    if not p.get("plan"):
        return envelope("tasks", error=(OUT_OF_ORDER, "tasks before a plan skip the laws and the research",
                                        "Run action=plan first (the ladder: specify -> plan -> tasks)."))
    if p.get("converge_log"):
        return envelope("tasks", error=(CONFLICT, "tasks are append-only after the first converge round "
                                                  "(the spec-kit law)",
                                        "Add the gaps as action=converge gaps; never rewrite the list."))
    if not isinstance(tasks, list) or not (1 <= len(tasks) <= _MAX_TASKS):
        return _bad("tasks", f"tasks must be a list of 1..{_MAX_TASKS} {{title, phase, source_refs, ...}}")
    spec = p["spec"]
    known_stories = {s["id"]: s for s in spec.get("stories") or []}
    out: list[dict] = []
    for i, t in enumerate(tasks, 1):
        if not isinstance(t, dict) or not str(t.get("title") or "").strip():
            return _bad("tasks", f"task {i} needs a title")
        phase = str(t.get("phase") or "").lower()
        if phase not in PHASES:
            return _bad("tasks", f"task {i} phase must be one of {', '.join(PHASES)}")
        refs = [str(r).strip().upper() for r in (t.get("source_refs") or []) if str(r).strip()][:8]
        for r in refs:
            if not _REF_RE.match(r):
                return _bad("tasks", f"task {i}: source_ref '{r}' does not look like FR-### / US# / US#-AC# / SC-###")
            if not _ref_exists(spec, r):
                return _bad("tasks", f"task {i} names requirement '{r}' which the spec does not have (a ghost ref)",
                            "Every task traces to a REAL requirement - fix the ref or write a new spec.")
        story_id = str(t.get("story") or "").strip().upper() or None
        if phase == "story":
            if story_id not in known_stories:
                return _bad("tasks", f"task {i}: story '{story_id}' is not a story of this spec",
                            "A story task implements ONE user story - name it US1, US2... as the spec numbered them.")
            if not refs:
                return _bad("tasks", f"task {i}: a story task without source_refs is unrequested work (the "
                                     f"traceability law)",
                            "Name the FR/AC the task serves, or drop it.")
        priority = str(t.get("priority") or "").upper()
        if priority not in PRIORITIES:
            priority = (known_stories.get(story_id) or {}).get("priority") or "P2"
        out.append({"id": f"T{i:03d}", "title": _clean(t.get("title"), _TITLE_CHARS), "phase": phase,
                    "story": story_id, "priority": priority, "source_refs": refs,
                    "parallel": bool(t.get("parallel")), "checkpoint": bool(t.get("checkpoint")),
                    "detail": _clean(t.get("detail"), _DESC_CHARS), "status": "todo", "done_at": None})
    _save(con, project_id, tasks=json.dumps(out), stage="tasks_ready")
    return envelope("tasks", project_id, "tasks_ready", tasks=out,
                    meta={"total": len(out),
                          "untraced": sum(1 for t in out if t["phase"] in ("foundational",) and not t["source_refs"])},
                    say="tasks numbered and traced; build in your own way, then action=analyze")


# ---------------------------------------------------------------- action: analyze
def _coverage(spec: dict, tasks: list[dict]) -> tuple[list[dict], int]:
    """Requirements with no task naming them (P1 first): the spec-kit coverage check."""
    refd = {r for t in tasks for r in t.get("source_refs") or []}
    refd |= {t.get("story") for t in tasks if t.get("story")}
    items: list[dict] = []
    for f in spec.get("features") or []:
        if f["id"] not in refd:
            items.append({"id": f["id"], "kind": "feature", "priority": f["priority"], "title": f["title"]})
    for s in spec.get("stories") or []:
        if s["id"] not in refd:
            items.append({"id": s["id"], "kind": "story", "priority": s["priority"], "title": s["title"]})
    order = {"P1": 0, "P2": 1, "P3": 2}
    items.sort(key=lambda x: order.get(x["priority"], 3))
    total = len(spec.get("features") or []) + len(spec.get("stories") or [])
    return items, total


def _do_analyze(con: sqlite3.Connection, ctx: Ctx, project_id: str | None) -> dict:
    if not project_id:
        return _bad("analyze", "which project? pass project_id (action=list shows ids)")
    p = _get(con, project_id)
    if p is None:
        return envelope("analyze", error=(NOT_FOUND, f"no project {project_id}",
                                          "action=list shows this tenant's projects."))
    if not p.get("spec") or not p.get("tasks"):
        return envelope("analyze", error=(OUT_OF_ORDER, "analyze crosses the spec against the tasks - one is missing",
                                          "Run action=specify and action=tasks first."))
    spec, tasks = p["spec"], p["tasks"]
    findings: list[dict] = []
    open_m = _open_markers(spec)
    if open_m:
        findings.append({"kind": "open_unknowns", "severity": "blocking",
                         "message": f"{len(open_m)} [NEEDS CLARIFICATION] still unanswered",
                         "where": ", ".join(m["where"] for m in open_m[:_MAX_MARKERS])})
    gaps, total = _coverage(spec, tasks)
    p1_gaps = [g for g in gaps if g["priority"] == "P1"]
    if p1_gaps:
        findings.append({"kind": "coverage_p1", "severity": "blocking",
                         "message": f"{len(p1_gaps)} P1 requirement(s) no task serves",
                         "where": ", ".join(g["id"] for g in p1_gaps)})
    p23_gaps = [g for g in gaps if g["priority"] != "P1"]
    if p23_gaps:
        findings.append({"kind": "coverage_p2_p3", "severity": "note",
                         "message": f"{len(p23_gaps)} P2/P3 requirement(s) no task serves (fine to defer - say so)",
                         "where": ", ".join(g["id"] for g in p23_gaps)})
    untraced = [t["id"] for t in tasks if t["phase"] == "story" and not t["source_refs"]]
    if untraced:
        findings.append({"kind": "untraced_story_tasks", "severity": "blocking",
                         "message": "story tasks that name no requirement (unrequested work)",
                         "where": ", ".join(untraced)})
    ghosts = sorted({r for t in tasks for r in t.get("source_refs") or [] if not _ref_exists(spec, r)})
    if ghosts:
        findings.append({"kind": "ghost_refs", "severity": "blocking",
                         "message": "tasks name requirements the spec does not have",
                         "where": ", ".join(ghosts)[:300]})
    if not p.get("plan"):
        findings.append({"kind": "no_plan", "severity": "note",
                         "message": "no plan on record - the laws were never checked", "where": "action=plan"})
    else:
        for g in (p["plan"].get("gates") or []):
            if g.get("status") == "violation" and not g.get("justification"):
                findings.append({"kind": "unjustified_violation", "severity": "blocking",
                                 "message": f"law {g['article']} violated with no justification",
                                 "where": "plan.gates"})
        amends = (p.get("constitution") or {}).get("amendments") or []
        if any(a.get("after_plan") for a in amends):
            # recorded at amendment time: the plan existed when the laws changed, so the gates
            # checked the OLD laws (no clock comparison - deterministic)
            findings.append({"kind": "constitution_amended_after_plan", "severity": "note",
                             "message": "the constitution changed after the plan - re-check the gates",
                             "where": "action=plan (again)"})
    ranks = [_PHASE_RANK.get(t["phase"], 9) for t in tasks]
    if ranks != sorted(ranks):
        findings.append({"kind": "phase_order", "severity": "note",
                         "message": "phases out of order (setup -> foundational -> story -> polish)",
                         "where": "tasks list"})
    blocking = [f for f in findings if f["severity"] == "blocking"]
    covered = total - len(gaps)
    return envelope("analyze", project_id, p["stage"], findings=findings,
                    meta={"verdict": "clean" if not blocking else "findings",
                          "blocking": len(blocking), "notes": len(findings) - len(blocking),
                          "traceability": {"covered": covered, "total": total,
                                           "pct": round(100 * covered / total) if total else 100}},
                    say=("clean - build, then action=converge with what you did and what you found"
                         if not blocking else
                         "fix the blocking findings, then analyze again - never build on a guess"))


# ---------------------------------------------------------------- action: converge
def _do_converge(con: sqlite3.Connection, ctx: Ctx, project_id: str | None, done: list | None,
                 gaps: list | None) -> dict:
    if not project_id:
        return _bad("converge", "which project? pass project_id (action=list shows ids)")
    p = _get(con, project_id)
    if p is None:
        return envelope("converge", error=(NOT_FOUND, f"no project {project_id}",
                                           "action=list shows this tenant's projects."))
    if not p.get("spec") or not p.get("tasks") or not p.get("plan"):
        return envelope("converge", error=(OUT_OF_ORDER, "converge assesses a BUILD against spec + plan + tasks",
                                           "Run the ladder: specify -> plan -> tasks -> build -> analyze -> converge."))
    tasks = [dict(t) for t in p["tasks"]]
    done = [str(d).strip().upper() for d in (done or [])]
    unknown = [d for d in done if d not in {t["id"] for t in tasks}]
    if unknown:
        return _bad("converge", f"done names task(s) this project does not have: {', '.join(unknown[:8])}",
                    "action=list with project_id shows the real T### ids - never invent them.")
    gaps = gaps if isinstance(gaps, list) else []
    if len(gaps) > _MAX_GAPS:
        return _bad("converge", f"gaps must be a list of 0..{_MAX_GAPS}")
    clean_gaps: list[dict] = []
    for g in gaps:
        if not isinstance(g, dict) or str(g.get("type") or "") not in GAP_TYPES:
            return _bad("converge", f"each gap needs type from {', '.join(GAP_TYPES)}")
        if not str(g.get("description") or "").strip():
            return _bad("converge", "a gap without its description assesses nothing")
        sev = str(g.get("severity") or "major").lower()
        if sev not in SEVERITIES:
            return _bad("converge", f"gap severity must be {', '.join(SEVERITIES)} (critical first)")
        ref = str(g.get("source_ref") or "").strip().upper() or None
        if ref and (not _REF_RE.match(ref) or not _ref_exists(p["spec"], ref)):
            return _bad("converge", f"gap source_ref '{ref}' is not a requirement of this spec")
        clean_gaps.append({"type": g["type"], "severity": sev,
                           "description": _clean(g.get("description"), _DESC_CHARS), "source_ref": ref})
    for t in tasks:
        if t["id"] in done:
            t["status"], t["done_at"] = "done", _now_iso()
    nxt = len(tasks) + 1
    added: list[str] = []
    for g in sorted(clean_gaps, key=lambda x: SEVERITIES.index(x["severity"])):
        if len(tasks) >= _MAX_TASKS + _MAX_GAPS:
            break
        t = {"id": f"T{nxt:03d}", "title": g["description"], "phase": "convergence", "story": None,
             "priority": "P1" if g["severity"] == "critical" else "P2",
             "source_refs": [g["source_ref"]] if g["source_ref"] else [], "parallel": False,
             "checkpoint": False, "detail": f"converge round: {g['type']} ({g['severity']})",
             "status": "todo", "done_at": None, "gap_type": g["type"], "gap_severity": g["severity"]}
        tasks.append(t)
        added.append(t["id"])
        nxt += 1
    open_tasks = [t["id"] for t in tasks if t["status"] != "done"]
    verdict = "converged" if not clean_gaps and not open_tasks else "more_rounds"
    log = list(p["converge_log"]) + [{"round": len(p["converge_log"]) + 1, "at": _now_iso(),
                                      "done_marked": len(done), "gaps_reported": len(clean_gaps),
                                      "tasks_added": added, "verdict": verdict}]
    stage = "converged" if verdict == "converged" else "converging"
    _save(con, project_id, tasks=json.dumps(tasks), converge_log=json.dumps(log), stage=stage)
    unreq = any(g["type"] == "unrequested" for g in clean_gaps)
    return envelope("converge", project_id, stage,
                    tasks_added=[t for t in tasks if t["id"] in added],
                    meta={"round": log[-1]["round"], "verdict": verdict, "append_only": True,
                          "done_marked": len(done), "gaps_reported": len(clean_gaps),
                          "open_tasks": len(open_tasks),
                          **({"note": "unrequested work needs her word: extend the spec (new project) or remove it"}
                             if unreq else {})},
                    say=("Converged - every task done, no gap open" if verdict == "converged"
                         else f"{len(open_tasks)} task(s) still open - converge again after the next build round"))


# ---------------------------------------------------------------- action: list
def _do_list(con: sqlite3.Connection, ctx: Ctx, project_id: str | None) -> dict:
    if not project_id:
        rows = con.execute("SELECT id, name, stage, spec, tasks, updated_at FROM projects "
                           "ORDER BY updated_at DESC").fetchall()
        items = []
        for r in rows:
            spec = _load_json(r["spec"], {}) or {}
            tasks = _load_json(r["tasks"], []) or []
            items.append({"id": r["id"], "name": r["name"], "stage": r["stage"],
                          "requirements": len(spec.get("features") or []),
                          "stories": len(spec.get("stories") or []),
                          "tasks_total": len(tasks),
                          "tasks_done": sum(1 for t in tasks if t.get("status") == "done"),
                          "open_unknowns": len(_open_markers(spec)) if spec else 0,
                          "updated_at": _ts_of(r["updated_at"])})
        return envelope("list", items=items, meta={"count": len(items)},
                        say="her spec projects; pass project_id for the full ladder")
    p = _get(con, project_id)
    if p is None:
        return envelope("list", error=(NOT_FOUND, f"no project {project_id}",
                                       "action=list (no id) shows this tenant's projects."))
    arts = p.get("constitution") or {"articles": STARTER_CONSTITUTION, "amendments": []}
    tasks = p.get("tasks") or []
    return envelope("list", project_id, p["stage"], constitution=arts["articles"], spec=p.get("spec"),
                    plan=p.get("plan"), tasks=tasks, converge_log=p.get("converge_log") or [],
                    meta={"tasks_done": sum(1 for t in tasks if t.get("status") == "done"),
                          "tasks_total": len(tasks),
                          "starter_constitution": p.get("constitution") is None})


# ---------------------------------------------------------------- the one tool the model sees
async def speckit(ctx: Ctx, action: str = "list", project_id: str | None = None, *,
                  name: str | None = None, intent: str | None = None, features: list | None = None,
                  stories: list | None = None, metrics: list | None = None, answers: list | None = None,
                  decisions: list | None = None, gates: list | None = None, tasks: list | None = None,
                  done: list | None = None, gaps: list | None = None, articles: list | None = None,
                  rationale: str | None = None, **_) -> dict:
    """The spec-driven ladder. Never raises; every answer is one envelope."""
    started = time.monotonic()
    action = str(action or "").strip().lower()
    if action not in VALID_ACTIONS:
        return _bad(action or "", f"unknown action '{action}'; valid: {', '.join(VALID_ACTIONS)}")
    if not getattr(get_settings(), "speckit_enabled", True) and not (
            action == "list" or (action == "constitution" and not articles)):
        # the kill switch stops the WRITES; the two read-only introspections stay answerable
        # (the reach honest-off pattern)
        return envelope(action, error=(NEED_SETUP, "speckit is turned off on this server",
                                       "Tell her plainly; nothing to fix from the chat."))
    con = _con(ctx.tenant_id)
    try:
        if action == "constitution":
            out = _do_constitution(con, articles, rationale, project_id)
        elif action == "specify":
            out = _do_specify(con, ctx, name, intent, features, stories, metrics)
        elif action == "clarify":
            out = _do_clarify(con, ctx, project_id, answers)
        elif action == "plan":
            out = _do_plan(con, ctx, project_id, decisions, gates)
        elif action == "tasks":
            out = _do_tasks(con, ctx, project_id, tasks)
        elif action == "analyze":
            out = _do_analyze(con, ctx, project_id)
        elif action == "converge":
            out = _do_converge(con, ctx, project_id, done, gaps)
        else:
            out = _do_list(con, ctx, project_id)
    finally:
        con.close()
    out["meta"]["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return out


SPECKIT_TOOLS = [
    {"name": "speckit", "description": (
        "SPEC SUTRA (v0.560): the spec-driven ladder for REAL software asks (a feature, tool, app or big "
        "website change - not a quick edit): constitution (the project's laws; call with no args to see the "
        "starter) -> specify (the spec: WHAT and WHY, never HOW; unanswered points ride as [NEEDS "
        "CLARIFICATION], never a guess) -> clarify (max 5 questions, scope > security > UX > technical; she "
        "answers, nothing guessed) -> plan (research decisions + every law checked; a violation carries its "
        "justification) -> tasks (T001... every task names its requirement FR-/US-AC/SC; no trace, no task) "
        "-> build in your usual way -> analyze (coverage + traceability; fix blocking findings, run again "
        "until clean) -> converge (report done task ids + gaps found: missing/partial/contradicts/unrequested; "
        "it APPENDS convergence tasks - never rewrites - and repeats until verdict=converged). list shows any "
        "project's full ladder. One envelope {ok, action, project_id, stage, error:{code, message, hint}}; "
        "OUT_OF_ORDER.hint names the step to run first."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": list(VALID_ACTIONS),
                    "description": "constitution | specify | clarify | plan | tasks | analyze | converge | list"},
         "project_id": {"type": "string", "description": "the sp_... id (list shows them)"},
         "name": {"type": "string", "description": "specify: project name (unique)"},
         "intent": {"type": "string", "description": "specify: what should exist and why (WHAT/WHY, never HOW)"},
         "features": {"type": "array", "description": "specify: [{title, priority: P1|P2|P3, detail}] - at least one P1"},
         "stories": {"type": "array", "description": "specify: [{title, priority, scenarios: [{given, when, then}]}]"},
         "metrics": {"type": "array", "description": "specify: [{name, target}] success criteria"},
         "answers": {"type": "array", "description": "clarify: [{id: 'Q1', answer}]"},
         "decisions": {"type": "array", "description": "plan: [{topic, decision, why}]"},
         "gates": {"type": "array", "description": "plan: [{article: 'I', status: pass|violation|na, justification}]"},
         "tasks": {"type": "array", "description": "tasks: [{title, phase: setup|foundational|story|polish, story, source_refs: [], parallel, checkpoint}]"},
         "done": {"type": "array", "description": "converge: task ids finished this round ['T001']"},
         "gaps": {"type": "array", "description": "converge: [{type: missing|partial|contradicts|unrequested, severity: critical|major|minor, description, source_ref}]"},
         "articles": {"type": "array", "description": "constitution: [{title, text}] the project's laws"},
         "rationale": {"type": "string", "description": "constitution: why these laws (amendments are logged)"}}}},
]

SPECKIT_LABELS = {"speckit": "Spec Sutra: from blueprint to work"}

SPECKIT_HANDLERS = {"speckit": speckit}
