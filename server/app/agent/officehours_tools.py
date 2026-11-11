"""v0.495.0 OFFICE HOURS — the THINK/PLAN lane (owner: "BUILD", after "NOW READ THIS REPO FIRST"
on github.com/garrytan/gstack).

gstack (Garry Tan's open-source software factory) turns a coding agent into a virtual engineering
team: /office-hours reframes the ask and writes a design doc, plan reviews (CEO / design / devex /
eng) amend it, and only then is anything built. The house already HAS the hands — qa, devops,
appreview, kaam_plan, the whole bazar — what it never had is the HEAD: the structured think/plan
step that decides what is WORTH building before anything is built. This lane is that head,
house-sized, with ZERO gstack code (all Markdown prompts over there; nothing of it enters this tree).

Storage: per-tenant SQLite — data/officehours/<safe-tenant>/officehours.db (office_docs +
office_reviews). A doc walks one honest status line: draft (start, the six questions) -> doc (the
design doc) -> reviewed (the eng lens landed; gstack's rule that eng reviews the FINAL amended plan,
so eng is the lens that closes the review state) -> decided (hers) | stopped.

House rules kept:
- The thinking is the AGENT's (it is the brain); the tool only stores the STRUCTURE and enforces the
  caps — exactly how kaam_plan stores the plan and qa stores the test cases.
- Nothing auto-runs off a doc. The wedge / next_step is advisory text: turning it into real work
  (kaam, a card, a site, whatever) happens on later turns, with her Haan, through the existing doors.
- decide is HER voice recorded; the agent never decides for her.
- The six forcing questions ask for REAL pain (a specific example, not a hypothetical), today's
  jugaad, the smallest self-useful wedge (gstack's "ship the narrowest wedge") and kill criteria.
- Review lenses mirror gstack's four plan reviews (ceo / design / devex / eng): findings + changes
  rows, append-only; an eng review before a doc exists is refused (never review a plan that is not
  written down).

Tools (2): officehours (start | doc | review | decide | stop) / officehours_dekho (list | doc |
reviews). Registry 529 -> 531.
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .tools import Ctx, ToolError

_TOPIC_CAP = 200
_TEXT_CAP = 2_000        # her_words / pain / reframe / recommendation
_SHORT_CAP = 1_000       # wedge / next_step / decision
_CAPS_MAX, _CAP_LEN = 7, 300          # capabilities
_PREM_MAX, _PREM_LEN = 7, 400         # premises: {challenge, answer}
_OPT_MAX = 4                          # gstack generates 3 approaches; room for one more
_OPT_NAME_LEN, _OPT_LEN = 120, 600
_FIND_MAX, _FIND_LEN = 12, 400        # review findings / changes
_VERDICT_LEN = 60
_LIST_CAP = 10
_KEEP_DOCS = 30         # finished-or-not docs kept per tenant; older ones (and their reviews) are forgotten
_LENS = ("ceo", "design", "devex", "eng")
_EFFORT = ("hours", "day", "days", "week", "weeks")

SIX_QUESTIONS = [
    "When is this pain at its WORST - give one REAL example (from yesterday or this week, not hypothetical)?",
    "Who does this work today, and how much time / money does it take?",
    "If it were all fixed, what is the FIRST visible change (what would be different tomorrow morning)?",
    "What workaround do people use instead today?",
    "What is the smallest piece that is useful ALONE (the wedge)?",
    "What would make you say 'this was useless' (kill criteria)?",
]


# --------------------------------------------------------------------------- store (per-tenant sqlite)

def _db_path(tenant_id: str) -> Path:
    safe = "".join(c for c in str(tenant_id or "x") if c.isalnum() or c in "_-")[:48] or "x"
    p = Path("data") / "officehours" / safe
    p.mkdir(parents=True, exist_ok=True)
    return p / "officehours.db"


def _con(tenant_id: str) -> sqlite3.Connection:
    con = sqlite3.connect(str(_db_path(tenant_id)), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS office_docs (id TEXT PRIMARY KEY, topic TEXT, status TEXT, "
                "her_words TEXT, pain TEXT, questions TEXT, reframe TEXT, capabilities TEXT, premises TEXT, "
                "options TEXT, recommendation TEXT, wedge TEXT, next_step TEXT, decision TEXT, "
                "created_at REAL, updated_at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS office_reviews (id TEXT PRIMARY KEY, doc_id TEXT, lens TEXT, "
                "verdict TEXT, findings TEXT, changes TEXT, created_at REAL)")
    return con


def _doc_row(r: sqlite3.Row, with_questions: bool = True) -> dict[str, Any]:
    d = dict(r)
    for k in ("capabilities", "premises", "options", "questions"):
        try:
            d[k] = json.loads(d.get(k) or "[]")
        except Exception:
            d[k] = []
    if not with_questions:
        d.pop("questions", None)
    return d


def _rev_row(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    for k in ("findings", "changes"):
        try:
            d[k] = json.loads(d.get(k) or "[]")
        except Exception:
            d[k] = []
    return d


def _forget_old(con: sqlite3.Connection, keep: int) -> None:
    """Keep the newest `keep` docs per tenant; older docs and their reviews are forgotten."""
    rows = con.execute("SELECT id FROM office_docs ORDER BY created_at DESC, id LIMIT -1 OFFSET ?",
                       (int(keep),)).fetchall()
    for r in rows:
        con.execute("DELETE FROM office_reviews WHERE doc_id = ?", (r["id"],))
        con.execute("DELETE FROM office_docs WHERE id = ?", (r["id"],))


def _touch(con: sqlite3.Connection, doc_id: str, **fields: Any) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    con.execute(f"UPDATE office_docs SET {sets}, updated_at = ? WHERE id = ?",
                (*fields.values(), time.time(), doc_id))


def get_doc(tenant_id: str, doc_id: str) -> dict[str, Any] | None:
    con = _con(tenant_id)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT * FROM office_docs WHERE id = ?", (doc_id,)).fetchone()
        return _doc_row(row) if row is not None else None
    finally:
        con.close()


def list_docs(tenant_id: str, limit: int = _LIST_CAP) -> tuple[list[dict[str, Any]], int]:
    con = _con(tenant_id)
    con.row_factory = sqlite3.Row
    try:
        total = con.execute("SELECT COUNT(*) c FROM office_docs").fetchone()["c"]
        rows = con.execute("SELECT * FROM office_docs ORDER BY created_at DESC, id LIMIT ?",
                           (int(limit),)).fetchall()
        return [_doc_row(r, with_questions=False) for r in rows], int(total)
    finally:
        con.close()


def list_reviews(tenant_id: str, doc_id: str) -> list[dict[str, Any]]:
    con = _con(tenant_id)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT * FROM office_reviews WHERE doc_id = ? ORDER BY created_at DESC, id",
                           (doc_id,)).fetchall()
        return [_rev_row(r) for r in rows]
    finally:
        con.close()


# --------------------------------------------------------------------------- actions (the five)

def start_doc(tenant_id: str, topic: str, her_words: str, pain: str,
              keep: int = _KEEP_DOCS) -> dict[str, Any]:
    """Open a baithak. An already open (draft/doc/reviewed) doc for the SAME topic is returned as-is."""
    now_ = time.time()
    con = _con(tenant_id)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT * FROM office_docs WHERE lower(topic) = lower(?) AND "
                          "status IN ('draft','doc','reviewed') ORDER BY created_at DESC LIMIT 1",
                          (topic,)).fetchone()
        if row is not None:
            out = _doc_row(row)
            out["_created"] = False
            return out
        did = "oh_" + uuid.uuid4().hex[:12]
        con.execute("INSERT INTO office_docs (id, topic, status, her_words, pain, questions, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (did, topic, "draft", her_words, pain, json.dumps(SIX_QUESTIONS), now_, now_))
        _forget_old(con, keep)
        con.commit()
        out = _doc_row(con.execute("SELECT * FROM office_docs WHERE id = ?", (did,)).fetchone())
        out["_created"] = True
        return out
    finally:
        con.close()


def save_doc(tenant_id: str, doc_id: str, reframe: str, capabilities: list, premises: list,
             options: list, recommendation: str, wedge: str) -> dict[str, Any] | None:
    """The design doc itself. Caps enforced honestly; effort clamped to the known words."""
    con = _con(tenant_id)
    try:
        row = con.execute("SELECT status FROM office_docs WHERE id = ?", (doc_id,)).fetchone()
        if row is None or row["status"] in ("decided", "stopped"):
            return None
        caps = [{"point": str(c.get("point") or c if isinstance(c, dict) else c)[:_CAP_LEN]}
                for c in (capabilities or [])][:_CAPS_MAX]
        caps = [{"point": str(c["point"])} for c in caps if str(c.get("point") or "").strip()]
        prems = []
        for p in (premises or [])[:_PREM_MAX]:
            if isinstance(p, dict):
                ch, an = str(p.get("challenge") or "")[:_PREM_LEN], str(p.get("answer") or "")[:_PREM_LEN]
            else:
                ch, an = str(p)[:_PREM_LEN], ""
            if ch.strip():
                prems.append({"challenge": ch, "answer": an})
        opts = []
        for o in (options or [])[:_OPT_MAX]:
            if not isinstance(o, dict):
                continue
            eff = str(o.get("effort") or "").strip().lower()
            if eff not in _EFFORT:
                eff = "days"
            name = str(o.get("name") or "")[:_OPT_NAME_LEN]
            if name.strip():
                opts.append({"name": name, "effort": eff, "what": str(o.get("what") or "")[:_OPT_LEN],
                             "why": str(o.get("why") or "")[:_OPT_LEN]})
        _touch(con, doc_id, reframe=str(reframe or "")[:_TEXT_CAP], capabilities=json.dumps(caps),
               premises=json.dumps(prems), options=json.dumps(opts),
               recommendation=str(recommendation or "")[:_TEXT_CAP], wedge=str(wedge or "")[:_SHORT_CAP],
               status="doc")
        con.commit()
        return get_doc(tenant_id, doc_id)
    finally:
        con.close()


def add_review(tenant_id: str, doc_id: str, lens: str, verdict: str, findings: list,
               changes: list) -> dict[str, Any] | None:
    """One plan-review lens. Append-only; the eng lens closes the review state (eng always last)."""
    lens = str(lens or "").strip().lower()
    if lens not in _LENS:
        return None
    con = _con(tenant_id)
    try:
        row = con.execute("SELECT status FROM office_docs WHERE id = ?", (doc_id,)).fetchone()
        if row is None or row["status"] in ("draft", "decided", "stopped"):
            return None
        finds = [str(f)[:_FIND_LEN] for f in (findings or [])][:_FIND_MAX]
        finds = [f for f in finds if f.strip()]
        chgs = [str(c)[:_FIND_LEN] for c in (changes or [])][:_FIND_MAX]
        chgs = [c for c in chgs if c.strip()]
        con.execute("INSERT INTO office_reviews (id, doc_id, lens, verdict, findings, changes, created_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    ("or_" + uuid.uuid4().hex[:12], doc_id, lens, str(verdict or "")[:_VERDICT_LEN],
                     json.dumps(finds), json.dumps(chgs), time.time()))
        if lens == "eng":
            _touch(con, doc_id, status="reviewed")
        else:
            _touch(con, doc_id)
        con.commit()
        return {"doc_id": doc_id, "lens": lens, "status": get_doc(tenant_id, doc_id)["status"],
                "reviews": list_reviews(tenant_id, doc_id)}
    finally:
        con.close()


def decide_doc(tenant_id: str, doc_id: str, decision: str, next_step: str) -> dict[str, Any] | None:
    """Record HER decision. The agent never decides; an already decided/stopped doc stays closed."""
    con = _con(tenant_id)
    try:
        row = con.execute("SELECT status FROM office_docs WHERE id = ?", (doc_id,)).fetchone()
        if row is None or row["status"] in ("decided", "stopped"):
            return None
        _touch(con, doc_id, status="decided", decision=str(decision or "")[:_SHORT_CAP],
               next_step=str(next_step or "")[:_SHORT_CAP])
        con.commit()
        return get_doc(tenant_id, doc_id)
    finally:
        con.close()


def stop_doc(tenant_id: str, doc_id: str) -> dict[str, Any] | None:
    con = _con(tenant_id)
    try:
        row = con.execute("SELECT status FROM office_docs WHERE id = ?", (doc_id,)).fetchone()
        if row is None or row["status"] in ("decided", "stopped"):
            return None
        _touch(con, doc_id, status="stopped")
        con.commit()
        return get_doc(tenant_id, doc_id)
    finally:
        con.close()


# --------------------------------------------------------------------------- tools

def _brief(row: dict[str, Any]) -> dict[str, Any]:
    return {"officehours_id": row["id"], "topic": row["topic"], "status": row["status"],
            "wedge": row.get("wedge") or "", "age_s": int(time.time() - float(row.get("updated_at") or 0))}


async def officehours(ctx: Ctx, action="start", topic="", her_words="", pain="", officehours_id="",
                      reframe="", capabilities=None, premises=None, options=None, recommendation="",
                      wedge="", lens="", verdict="", findings=None, changes=None, decision="",
                      next_step="", **_):
    """Office hours: the design-doc lane BEFORE any building. start -> the six questions; doc -> the
    design doc; review -> one lens (ceo/design/devex/eng, eng last); decide -> HER call; stop."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "officehours_enabled", True):
        raise ToolError("Office hours is switched off (officehours_enabled=false)")
    act = str(action or "start").strip().lower()
    if act == "start":
        topic = str(topic or "").strip()[:_TOPIC_CAP]
        if not topic:
            raise ToolError("A topic is needed for the session - what does she want to build, in one line")
        row = start_doc(ctx.tenant_id, topic, str(her_words or "")[:_TEXT_CAP], str(pain or "")[:_TEXT_CAP],
                        keep=max(1, int(getattr(s, "officehours_keep_docs", 30) or 30)))
        fresh = bool(row.pop("_created", False))
        return {"officehours_id": row["id"], "topic": row["topic"], "status": row["status"],
                "already_open": not fresh, "questions": row["questions"],
                "note": ("Session opened - six questions, ask them ONE BY ONE (not all together), with her real "
                         "example; then write the design doc with action=doc"
                         if fresh else
                         "A session on this topic is already open - the same doc continues (no new one was made)")}
    did = str(officehours_id or "").strip()
    if act in ("doc", "review", "decide", "stop") and not did:
        docs, _t = list_docs(ctx.tenant_id, 1)
        if not docs or docs[0]["status"] in ("decided", "stopped"):
            raise ToolError("No open session found - do action=start first")
        did = docs[0]["id"]
    if act == "doc":
        if not get_doc(ctx.tenant_id, did):
            raise ToolError(f"This officehours_id was not found: {did}")
        row = save_doc(ctx.tenant_id, did, reframe, list(capabilities or []), list(premises or []),
                       list(options or []), recommendation, wedge)
        if row is None:
            raise ToolError("This session is decided/stopped - for a new doc open a new session with action=start")
        return {"officehours_id": row["id"], "status": row["status"],
                "capabilities": len(row["capabilities"]), "premises": len(row["premises"]),
                "options": [f"{o['name']} ({o['effort']})" for o in row["options"]],
                "recommendation": row["recommendation"][:300],
                "note": ("Design doc written - now run the lenses: action=review (ceo / design / devex / "
                         "eng; eng LAST of all, it sees the final amended plan)")}
    if act == "review":
        if str(lens or "").strip().lower() not in _LENS:
            raise ToolError("lens is needed: ceo | design | devex | eng (eng always last)")
        cur = get_doc(ctx.tenant_id, did)
        if cur is None:
            raise ToolError(f"This officehours_id was not found: {did}")
        if cur["status"] == "draft":
            raise ToolError("Write the design doc with action=doc first - something not written cannot be reviewed")
        out = add_review(ctx.tenant_id, did, lens, verdict, list(findings or []), list(changes or []))
        if out is None:
            raise ToolError("This session is decided/stopped - review is closed")
        return {"officehours_id": did, "lens": out["lens"], "status": out["status"],
                "reviews_so_far": [f"{r['lens']}:{(r['verdict'] or '')[:40]}" for r in out["reviews"]],
                "note": ("Eng review done - the plan is now reviewed. The decision is hers: action=decide in "
                         "her words" if out["status"] == "reviewed" else
                         "Review notes added - the remaining lenses next (eng last)")}
    if act == "decide":
        decision = str(decision or "").strip()
        if not decision:
            raise ToolError("a decision is needed - in HER words (Hoola does not decide)")
        out = decide_doc(ctx.tenant_id, did, decision, next_step)
        if out is None:
            raise ToolError("This session is already decided/stopped")
        return {"officehours_id": out["id"], "status": out["status"], "decision": out["decision"],
                "next_step": out["next_step"],
                "note": "Decision noted - the doc can always be fetched again with officehours_dekho; further work happens on her yes"}
    if act == "stop":
        out = stop_doc(ctx.tenant_id, did)
        if out is None:
            raise ToolError("This session is already decided/stopped")
        return {"officehours_id": out["id"], "status": out["status"], "note": "Session closed"}
    raise ToolError("action is needed: start | doc | review | decide | stop")


async def officehours_dekho(ctx: Ctx, what="list", officehours_id="", **_):
    """Read office hours (nothing changes). what=list (latest baithaks) | doc (one poora doc) |
    reviews (one doc ki saari review notees)."""
    w = str(what or "list").strip().lower()
    if w == "list":
        docs, total = list_docs(ctx.tenant_id)
        return {"total": total, "count": len(docs), "docs": [_brief(d) for d in docs],
                "note": ("For the full doc use what=doc with officehours_id" if docs
                         else "No session yet - open one with officehours action=start")}
    did = str(officehours_id or "").strip()
    if not did:
        docs, _t = list_docs(ctx.tenant_id, 1)
        if not docs:
            raise ToolError("No session yet - do officehours action=start first")
        did = docs[0]["id"]
    if w == "doc":
        row = get_doc(ctx.tenant_id, did)
        if row is None:
            raise ToolError(f"This officehours_id was not found: {did}")
        revs = list_reviews(ctx.tenant_id, did)
        return {**row, "officehours_id": row["id"], "reviews_count": len(revs),
                "reviews_brief": [f"{r['lens']}:{(r['verdict'] or '')[:40]}" for r in revs]}
    if w == "reviews":
        if get_doc(ctx.tenant_id, did) is None:
            raise ToolError(f"This officehours_id was not found: {did}")
        revs = list_reviews(ctx.tenant_id, did)
        return {"officehours_id": did, "count": len(revs), "reviews": revs}
    raise ToolError("what is needed: list | doc | reviews")


OFFICEHOURS_TOOLS = [
    {"name": "officehours", "description": (
        "Office hours (v0.495, the gstack idea, house-sized): BEFORE building anything new, open a design "
        "doc and think it through with her. action=start (topic, her_words, pain) opens a session and "
        "returns SIX forcing questions (real pain examples, today's jugaad, the smallest self-useful "
        "wedge, kill criteria) — ask them ONE at a time, push back on her framing when her words and her "
        "pain differ. action=doc writes the doc: reframe, capabilities, premises (challenge -> her "
        "answer), 3-4 options with effort (hours|day|days|week|weeks), recommendation (the narrowest "
        "wedge), wedge. action=review adds one lens ceo|design|devex|eng with verdict + findings + "
        "changes — eng ALWAYS last (it reviews the final amended plan). action=decide records HER "
        "decision in her words (Hoola never decides for her); action=stop closes it. Nothing auto-runs "
        "off a doc — turning the wedge into real work happens later, with her Haan."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["start", "doc", "review", "decide", "stop"]},
         "topic": {"type": "string", "description": "(start) the idea in one line"},
         "her_words": {"type": "string", "description": "(start) her own words, so the doc stays honest to them"},
         "pain": {"type": "string", "description": "(start) the real pain she described, with her example"},
         "officehours_id": {"type": "string",
                            "description": "(doc/review/decide/stop) from the start result; empty = the latest open session"},
         "reframe": {"type": "string", "description": "(doc) what she asked vs what she actually needs"},
         "capabilities": {"type": "array", "items": {"type": "string"},
                          "description": "(doc) what the thing must DO (max 7 short points)"},
         "premises": {"type": "array", "items": {"type": "object", "properties": {
             "challenge": {"type": "string"}, "answer": {"type": "string"}},
             "description": "(doc) a premise you challenged and her answer (max 7)"}},
         "options": {"type": "array", "items": {"type": "object", "properties": {
             "name": {"type": "string"}, "effort": {"type": "string", "enum": ["hours", "day", "days", "week", "weeks"]},
             "what": {"type": "string"}, "why": {"type": "string"}},
             "description": "(doc) 3-4 ways to build it, each with an honest effort"}},
         "recommendation": {"type": "string", "description": "(doc) which option and WHY (the narrowest wedge)"},
         "wedge": {"type": "string", "description": "(doc) the smallest piece that is ALONE useful"},
         "lens": {"type": "string", "enum": ["ceo", "design", "devex", "eng"],
                  "description": "(review) which review lens; eng always LAST"},
         "verdict": {"type": "string", "description": "(review) one short line, e.g. GO / SHRINK / HOLD / REWORK"},
         "findings": {"type": "array", "items": {"type": "string"}, "description": "(review) what the lens found (max 12)"},
         "changes": {"type": "array", "items": {"type": "string"},
                     "description": "(review) what the plan should change (max 12)"},
         "decision": {"type": "string", "description": "(decide) HER decision, in her words (required)"},
         "next_step": {"type": "string", "description": "(decide) the first concrete next step, if she named one"}},
         "required": ["action"]}},
    {"name": "officehours_dekho", "description": (
        "Read office hours (nothing changes): what=list shows the latest sessions (topic, status, wedge), "
        "what=doc returns ONE full design doc (reframe, capabilities, premises, options, recommendation, "
        "wedge, decision, next_step, review count), what=reviews returns every review lens row of a doc. "
        "No officehours_id = the latest one. Use it to recall a past session before she repeats herself."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["list", "doc", "reviews"]},
         "officehours_id": {"type": "string", "description": "from officehours; empty = the latest"}},
         }},
]

OFFICEHOURS_LABELS = {"officehours": "Office hours baithak chal rahi hai",
                      "officehours_dekho": "Baithak ke notes dekh raha hoon"}

OFFICEHOURS_HANDLERS = {"officehours": officehours, "officehours_dekho": officehours_dekho}
