"""v0.472 R1 PLAN PEHLE - a big research ask gets its PLAN first, and the money is spent only on her Haan.

Plan: `docs/RESEARCH_PRO_PLAN.md` parts 1 + 2 (SAMAJHO, PLAN). The shape is Google's `collaborative_planning` ("provide a
research plan in its response; proceed only if the user confirms the plan in the next turn") on Hoola's own house pattern
(`devsahayak/plan.py`: score the ask in CODE, a LARGE one waits for her Haan, her note rides along).

  small     one lookup                       -> straight to work, nothing shown
  standard  a real question, a few parts     -> straight to work (the research recipe already guides it)
  large     a report: deep / many parts /    -> a PLAN CARD first (the question restated, 4-6 sub-questions, where it
            a document she will hand over       will look, as of when, est. minutes + rupees) and NOTHING runs until
                                                her Haan. Her words after the Haan are the note ("Haan, par Pakistan bhi").

The tier is read from her words in code, before any model call, so a small ask costs nothing extra. The plan itself is one
cheap model call for the sub-questions, with a code fallback when the call fails (the card still comes, from templates).

What this is NOT: it is not the research engine (R2) and it does not make the run longer or background (R4). It only
decides whether the run may start, and hands the approved plan to the SAME turn as a block the model must follow.

Estimates (minutes, rupees) are ASSUMED from the sub-question count and the model's list price - the live research card
has not run, so they are labelled "andaza" on the card itself. R5 replaces them with the measured numbers.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.research_plan")

PLAN_V = 1
WAIT_HOURS = 24                 # a plan nobody answered for a day is stale: a new ask starts clean

# ---- ASSUMED sizing (no live card yet): per sub-question and for the writing pass, in tokens
ASSUMED_IN_PER_Q, ASSUMED_OUT_PER_Q = 60_000, 6_000
ASSUMED_IN_WRITE, ASSUMED_OUT_WRITE = 40_000, 8_000
ASSUMED_MIN_BASE, ASSUMED_MIN_PER_Q = 4, 3


class ResearchPlan(Base):
    __tablename__ = "research_plans"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    ask: Mapped[str] = mapped_column(Text, default="")
    plan: Mapped[str] = mapped_column(Text, default="{}")                      # JSON: the card's content
    status: Mapped[str] = mapped_column(String(12), default="waiting")         # waiting|approved|cancelled|superseded|expired
    note: Mapped[str] = mapped_column(Text, default="")                        # her words with the Haan
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_ready = False


def ensure_table() -> None:
    """Self-heal: a database born before this model existed has no table (a lazily imported model module)."""
    global _ready
    if _ready:
        return
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        ResearchPlan.__table__.create(eng, checkfirst=True)
    _ready = True


# ---------------------------------------------------------------- 1. SAMAJHO: how big is this ask (code, no model)
_DEEP = re.compile(r"(?i)\b(deep\s*research|full\s+(?:research\s+)?report|poora\s+(?:research\s+)?(?:report|document)|"
                   r"research\s+(?:document|report|paper)|literature\s+review|in.?depth|detailed|proper\s+(?:research\s+)?"
                   r"(?:document|report)|white\s*paper|landscape|competitor\s+report|market\s+(?:study|report)|"
                   r"sources?\s+(?:and|aur)\s+dates?|with\s+(?:exact\s+)?sources|sources?\s+ke\s+saath|"
                   r"research\s+document\s+chahiye)\b")
_CALC = re.compile(r"(?i)\b(compute|calculate|work\s+out|cagr|growth\s+rate|year.on.year|yoy|hisaab|nikalo|kitna\s+"
                   r"(?:padega|hoga|aayega)|per\s+month|monthly)\b")
_JOIN = re.compile(r"(?i)(,|;|\baur\b|\band\b|\+|\n\s*[-*•]|\n\s*\d+[.)])")
_OFFICIAL = re.compile(r"(?i)\b(cpi|gdp|iip|plfs|inflation|mospi|trai|rbi|sebi|census|official\s+(?:sources?|guidance|data|"
                       r"numbers)|government)\b")
_SCHOLAR = re.compile(r"(?i)\b(papers?|literature|evidence\s+on|study|studies|systematic|journal|arxiv|pubmed|peer.?review)\b")
_HINGLISH = re.compile(r"(?i)\b(karo|kar|hai|hain|ka|ke|ki|mein|me|chahiye|batao|aur|kya|kitna|kitni|ko|se|par|"
                       r"saath|abhi|latest\s+kitni|mujhe|mera|meri)\b")


def assess(text: str) -> dict[str, Any]:
    """{tier, parts, calc, corpus, deep, hinglish, why} for one research ask. No model call."""
    t = str(text or "").strip()
    deep = bool(_DEEP.search(t))
    calc = bool(_CALC.search(t))
    body = t.split(":", 1)[1] if ":" in t[:120] else t
    parts = min(len(_JOIN.findall(body)) + 1, 9)
    corpus = "official" if _OFFICIAL.search(t) else ("scholarly" if _SCHOLAR.search(t) else "web")
    why: list[str] = []
    if deep:
        why.append("deep / report / document words")
    if parts >= 4:
        why.append(f"{parts} things asked")
    if calc and parts >= 3:
        why.append("figures to work out")
    if len(t) > 260:
        why.append("long ask")
    if deep or parts >= 4 or (calc and parts >= 3) or len(t) > 260:
        tier = "large"
    elif len(t) <= 90 and parts <= 2 and not calc:
        tier = "small"
    else:
        tier = "standard"
    return {"tier": tier, "parts": parts, "calc": calc, "corpus": corpus, "deep": deep,
            "hinglish": len(_HINGLISH.findall(t)) >= 2 or bool(re.search(r"[ऀ-ॿ]", t)), "why": why}


# ---------------------------------------------------------------- 2. PLAN: the card
_TEMPLATE_Q = {
    "official": ["What do the official statistics / regulator publish on this, and as of which date?",
                 "How has it moved over the period that matters (trend, not one number)?",
                 "Where do the official source and other credible sources disagree?",
                 "What is not yet final, revised, or not published?"],
    "scholarly": ["What are the most relevant primary studies, and what did each find?",
                  "Where do the studies agree, and where do they disagree?",
                  "How strong is the evidence (sample, method, date)?",
                  "What is still unknown?"],
    "web": ["What are the key facts and figures, from the primary source where one exists?",
            "Who are the main players / parties, and how do they compare?",
            "What changed recently, and what is announced but not final?",
            "Where do credible sources disagree, and what could not be confirmed?"],
}
_PLAN_SYSTEM = ("You plan a research job for an AI coworker. Given the ask, reply ONLY JSON: "
                '{"sub_questions": ["...", ...4 to 6 items, each one question that can be answered from sources], '
                '"look_in": ["kinds of places to look, e.g. regulator site, company filings, TRAI data"], '
                '"as_of": "the date or period the answer must be current to"}. '
                "No facts, no numbers, no answers - only the questions and where to look. Keep each under 25 words. "
                "Write in the same language as the ask.")


def _fallback(a: dict[str, Any]) -> dict[str, Any]:
    qs = list(_TEMPLATE_Q.get(a["corpus"], _TEMPLATE_Q["web"]))
    if a["calc"]:
        qs.append("Which derived figures are needed (growth, share, total), and what are their inputs?")
    return {"sub_questions": qs[:6], "look_in": {"official": ["MoSPI / TRAI / the regulator's own releases"],
                                                  "scholarly": ["papers via OpenAlex / arXiv / PubMed"],
                                                  "web": ["primary sources first, then credible reporting"]}[a["corpus"]],
            "as_of": "today", "from_model": False}


async def _questions(ask: str, note: str, a: dict[str, Any], settings) -> dict[str, Any]:
    try:
        from .santosh import get_client
        model = getattr(settings, "hard_judge_model", "") or settings.anthropic_model
        user = f"ASK:\n{ask[:3000]}" + (f"\n\nHER NOTE ON THE PLAN (follow it):\n{note[:600]}" if note else "")
        resp = await asyncio.wait_for(get_client().messages.create(
            model=model, max_tokens=600, system=_PLAN_SYSTEM, messages=[{"role": "user", "content": user}]), timeout=40)
        raw = "".join(str(b.get("text") if isinstance(b, dict) else getattr(b, "text", "")) for b in resp.content)
        m = re.search(r"\{.*\}", raw, re.S)
        v = json.loads(m.group(0)) if m else {}
        qs = [str(x).strip() for x in (v.get("sub_questions") or []) if str(x).strip()][:6]
        if len(qs) < 3:
            return _fallback(a)
        return {"sub_questions": qs, "look_in": [str(x)[:120] for x in (v.get("look_in") or [])][:5] or _fallback(a)["look_in"],
                "as_of": str(v.get("as_of") or "today")[:80], "from_model": True}
    except Exception as e:      # noqa: BLE001 - no model, no key, a timeout: the plan still comes, from the templates
        log.info("research plan questions fell back to templates: %s", e)
        return _fallback(a)


def estimate(n_q: int, settings) -> dict[str, Any]:
    """Minutes and rupees for n sub-questions. ASSUMED sizes x the model's list price (usage.cost); said so on the card."""
    from .. import usage
    model = getattr(settings, "agent_hard_model", "") or settings.anthropic_model
    tin, tout = n_q * ASSUMED_IN_PER_Q + ASSUMED_IN_WRITE, n_q * ASSUMED_OUT_PER_Q + ASSUMED_OUT_WRITE
    try:
        inr = round(float(usage.cost(model, tok_in=tin, tok_out=tout)) * usage.usd_inr(), 0)
    except Exception:       # noqa: BLE001 - an unpriced model: say so rather than invent a figure
        inr = None
    return {"minutes": ASSUMED_MIN_BASE + ASSUMED_MIN_PER_Q * n_q, "inr": inr, "model": model, "assumed": True}


async def build(ask: str, settings, note: str = "") -> dict[str, Any]:
    a = assess(ask)
    q = await _questions(ask, note, a, settings)
    return {"v": PLAN_V, "ask": ask[:1500], "tier": a["tier"], "corpus": a["corpus"], "calc": a["calc"],
            "hinglish": a["hinglish"], "sub_questions": q["sub_questions"], "look_in": q["look_in"],
            "as_of": q["as_of"], "from_model": q["from_model"], "est": estimate(len(q["sub_questions"]), settings),
            "note": note[:600]}


def card_text(p: dict[str, Any]) -> str:
    """The plan as one chat message, in her language. Ends with the one thing she has to say."""
    hi = bool(p.get("hinglish"))
    est = p["est"]
    money = f"~Rs {int(est['inr']):,}" if est.get("inr") is not None else ("kharcha andaza nahi laga paaya" if hi else
                                                                          "cost could not be estimated")
    qs = "\n".join(f"{i}. {q}" for i, q in enumerate(p["sub_questions"], 1))
    where = ", ".join(p["look_in"])
    if hi:
        return (f"**Research plan** - chalne se pehle aapki haan chahiye.\n\n**Sawal:** {p['ask'][:400]}\n\n"
                f"**Main yeh dhoondhunga:**\n{qs}\n\n**Kahan dekhunga:** {where}\n**Kab tak ka data:** {p['as_of']}\n"
                f"**Andaza:** ~{est['minutes']} minute, {money} (andaza hai - asli kharcha research card se pakka hoga)\n"
                f"**Report mein:** har number ke saath uska source aur date, aur jo confirm nahi ho paya woh alag se.\n\n"
                f"Theek hai to **\"Haan, shuru karo\"** likhiye. Kuch badalna ho to saath mein likh dijiye "
                f"(jaise \"Haan, par Pakistan se bhi tulna\"). Nahi karna to **\"nahi\"**.")
    return (f"**Research plan** - I need your Haan before I start.\n\n**Question:** {p['ask'][:400]}\n\n"
            f"**What I will find out:**\n{qs}\n\n**Where I will look:** {where}\n**Current to:** {p['as_of']}\n"
            f"**Estimate:** ~{est['minutes']} min, {money} (an estimate - the research card will make it exact)\n"
            f"**In the report:** every number with its source and date, and what could not be confirmed kept separate.\n\n"
            f"Reply **\"Haan, shuru karo\"** to start. Add a change in the same message "
            f"(e.g. \"Haan, but also compare with Pakistan\"). Reply **\"no\"** to drop it.")


def approved_block(p: dict[str, Any], note: str = "") -> str:
    """What the SAME turn receives after her Haan: the plan she approved, which the research must follow."""
    qs = "\n".join(f"{i}. {q}" for i, q in enumerate(p["sub_questions"], 1))
    out = (f"<approved_research_plan>\nShe approved this plan - it is already approved, so do not ask her again and do not "
           f"write another plan card: start now by calling research_run with this question and EXACTLY these sub-questions (plus her change below, "
           f"if any). Answer exactly these sub-questions, look where it says, "
           f"keep the report current to: {p['as_of']}.\n{qs}\nLook in: {', '.join(p['look_in'])}\n")
    if note.strip():
        out += f"HER CHANGE TO THE PLAN (follow it): {note.strip()[:600]}\n"
    return out + "</approved_research_plan>"


# ---------------------------------------------------------------- 3. the gate (called from the chat turn)
def _waiting(tenant: str, conv: str) -> ResearchPlan | None:
    ensure_table()
    cutoff = now() - timedelta(hours=WAIT_HOURS)
    with session() as s:
        row = s.scalars(select(ResearchPlan).where(ResearchPlan.tenant_id == tenant, ResearchPlan.conversation_id == conv,
                                                   ResearchPlan.status == "waiting")
                        .order_by(ResearchPlan.created_at.desc())).first()
        if row is None:
            return None
        ca = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)
        if ca < cutoff:
            row.status, row.decided_at = "expired", now()
            return None
        s.expunge(row)
        return row


def _close(plan_id: str, status: str, note: str = "") -> None:
    with session() as s:
        row = s.get(ResearchPlan, plan_id)
        if row is not None:
            row.status, row.note, row.decided_at = status, note[:600], now()


def _save_plan(tenant: str, conv: str, ask: str, plan: dict[str, Any]) -> str:
    ensure_table()
    with session() as s:
        row = ResearchPlan(tenant_id=tenant, conversation_id=conv, ask=ask[:3000],
                           plan=json.dumps(plan, ensure_ascii=False))
        s.add(row)
        s.flush()
        return row.id


def _is_research_ask(text: str) -> bool:
    from . import hard
    return hard.research_wanted(text)


async def gate(tenant: str, conv: str, text: str, settings) -> dict[str, Any] | None:
    """Decide what her message means for a research plan. Returns None = nothing to do (the turn runs as before), or
        {"action": "say",   "text": ...}            show this (a new plan, a revised plan, 'ok dropped') and end the turn
        {"action": "start", "text": ..., "words": ...}  run now: `text` is the ask + the approved plan, `words` is what she typed
    Only her own typed chat words reach here (the caller checks owner / not voice / not a system note)."""
    from .. import approval_words as AW
    t = str(text or "").strip()
    if not t:
        return None
    wait = _waiting(tenant, conv)
    if wait is not None:
        plan = json.loads(wait.plan or "{}")
        if AW.is_pure_rejection(t):
            _close(wait.id, "cancelled")
            hi = plan.get("hinglish", True)
            return {"action": "say", "words": t,
                    "text": "Theek hai, research nahi kar raha. Jab chahein phir bol dijiye." if hi
                    else "Okay, I won't run that research. Tell me whenever you want it."}
        if AW.is_pure_approval(t):
            _close(wait.id, "approved")
            return {"action": "start", "words": t, "text": f"{plan['ask']}\n\n{approved_block(plan)}", "plan_id": wait.id}
        if AW.approve_lead(t):                    # "Haan, par Pakistan bhi": the Haan leads, the rest is her change
            note = re.sub(r"(?i)^\W*(haan|han|haa|yes|ok|okay|theek hai|thik hai|sure|go|shuru karo|start)\b[\s,.-]*", "", t).strip()
            _close(wait.id, "approved", note)
            return {"action": "start", "words": t, "plan_id": wait.id,
                    "text": f"{plan['ask']}\n\n{approved_block(plan, note)}"}
        if _is_research_ask(t) and assess(t)["tier"] == "large":     # a different big ask: the old plan is dropped
            _close(wait.id, "superseded")
        elif not t.startswith(("[", "(")) and len(t) <= 400:         # anything else short = her change to the plan
            note = (plan.get("note", "") + " | " if plan.get("note") else "") + t
            newp = await build(plan["ask"], settings, note)
            _close(wait.id, "superseded")
            _save_plan(tenant, conv, plan["ask"], newp)
            return {"action": "say", "words": t, "text": card_text(newp)}
        else:
            return None
    if not getattr(settings, "research_plan_gate", True):
        return None
    if t.startswith(("[", "(")) or not _is_research_ask(t):
        return None
    if assess(t)["tier"] != "large":
        return None
    plan = await build(t, settings)
    _save_plan(tenant, conv, t, plan)
    return {"action": "say", "words": t, "text": card_text(plan)}
