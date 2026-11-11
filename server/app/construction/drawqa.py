"""#9 Building-bye-law Checker + #16 Drawing QA Reviewer glue (v0.531.0, Wave 2 C10).

Document-level, PDF/DWG-first, and HONEST about it: the drawing register keeps what came in (dwg
no, revision, scale-as-noted, source); the bye-law rules are DATA - the state pack's determined
rows plus her typed project rules, each with clause + source (a rule without its clause refuses to
save); a check is ARITHMETIC (declared vs limit; over = breach) and the outcome belongs to the
Drawing QA Reviewer - the project architect (tier B on every card).

Hoola never claims model-level checking: a PDF was never a model, and the scale-bar geometry stays
with the person who measured. What Hoola owns is the register, the rule rows, the arithmetic and
the review pack with the architect's sign line EMPTY."""
from __future__ import annotations

import io

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, today)
from .models import CDraw, CDrawCheck, CDrawRule


def dwg_add(tenant: str, project: str, dwg_no: str, rev: str = "", kind: str = "", scale_as_noted: str = "",
            source: str = "", conv: str = "") -> dict:
    """One drawing into the register - document-level: jo sheet aayi, wahi record."""
    if not str(project or "").strip() or not str(dwg_no or "").strip():
        raise CstError("Give the project and the drawing number.")
    with _LOCK, session() as s:
        x = CDraw(tenant_id=tenant, project=project.strip()[:160], dwg_no=dwg_no.strip()[:80], rev=rev.strip()[:20],
                  kind=kind.strip()[:60], scale_as_noted=scale_as_noted.strip()[:60], source=source.strip()[:120])
        s.add(x)
        s.flush()
        did = x.id
    from .common import publish
    publish(tenant, "const_drawqa", {"kind": "dwg_add", "project": project, "dwg_no": dwg_no}, conv)
    return {"drawing_id": did,
            "say": f"Drawing register: {dwg_no}{' rev ' + rev if rev else ''} ({project}"
                   + (f", scale {scale_as_noted})" if scale_as_noted else ")")
                   + ". The check is at document level - not model level (a PDF is never a model). "
                     "Measured values are attached through checks."}


def rule_add(tenant: str, rule_id: str, text: str, limit_value, unit: str, clause: str, source: str,
             checked_on: str = "", direction: str = "max") -> dict:
    """A bye-law rule as DATA: clause + source REQUIRED (kaunsa bye-law, kahan likha). Direction: 'max'
    (declared must not exceed - FAR, height) or 'min' (declared must not fall below - setbacks)."""
    if not str(rule_id or "").strip() or not str(text or "").strip():
        raise CstError("Give the rule id and the text (for example 'front_setback', 'Front setback min').")
    if _num(limit_value) <= 0:
        raise CstError("Give the limit value (> 0).")
    if direction not in ("min", "max"):
        raise CstError("direction: min | max (a setback is a min, FAR is a max).")
    cl, src = str(clause or "").strip(), str(source or "").strip()
    if not cl or not src:
        raise CstError("Both the clause and the source are needed (for example 'UDCPR 6.1', 'DCPR 2034 / ULB letter') - "
                       "a rule without a clause is not a bye-law, it is a guess. It is not accepted.")
    with _LOCK, session() as s:
        x = CDrawRule(tenant_id=tenant, rule_id=rule_id.strip()[:60], text=text.strip()[:300],
                      limit_value=_num(limit_value), direction=direction, unit=unit.strip()[:20], clause=cl[:160],
                      source=src[:200], checked_on=(_date(checked_on) or today(tenant)).isoformat())
        s.add(x)
        s.flush()
        rid = x.id
    return {"rule_id": rid,
            "say": f"Rule added: {rule_id} - {text[:70]} limit {_num(limit_value):g} {unit} ({direction}) "
                   f"({cl}, {src[:60]}). The drawings' declared values are now checked against it - the verdict is the architect's."}


def check(tenant: str, drawing_id: str, rule_id: str, declared, note: str = "") -> dict:
    """The arithmetic: declared vs limit (min ya max, rule ka direction). 'breach' ka matlab hai limit
    ke us paar - yeh HISaab hai, approval nahi. Rule miss ho to saaf mana karta hoon, andaza nahi lagata."""
    with session() as s:
        d = s.get(CDraw, drawing_id)
        if not d or d.tenant_id != tenant:
            raise CstError("Drawing not found.")
        r = s.scalars(select(CDrawRule).where(CDrawRule.tenant_id == tenant, CDrawRule.rule_id == rule_id)).first()
    if r is None:
        raise CstError(f"Rule '{rule_id}' is not in this project - add it first with rule_add, with clause and "
                       "source. Without a rule there is no check (a guess is not a bye-law).")
    val = _num(declared)
    if r.direction == "min":
        verdict = "ok" if val >= r.limit_value else "breach"
        margin = round(val - r.limit_value, 3)
    else:
        verdict = "ok" if val <= r.limit_value else "breach"
        margin = round(r.limit_value - val, 3)
    with _LOCK, session() as s:
        x = CDrawCheck(tenant_id=tenant, drawing_id=drawing_id[:40], rule_id=rule_id[:60], declared=val,
                       limit_value=r.limit_value, unit=r.unit[:20], verdict=verdict,
                       checked_on=today(tenant).isoformat(), note=note[:200])
        s.add(x)
        s.flush()
        cid = x.id
    return {"check_id": cid, "rule": rule_id, "declared": val, "limit": r.limit_value, "verdict": verdict,
            "margin": margin,
            "say": (f"{d.dwg_no} vs {rule_id}: declared {val:g} {r.unit} {'>=' if r.direction == 'min' else '<='} "
                    f"limit {r.limit_value:g} {r.unit} (margin {margin:g}) -> WITHIN (arithmetic). "
                    if verdict == "ok" else
                    f"{d.dwg_no} vs {rule_id}: declared {val:g} {r.unit} "
                    f"{'<' if r.direction == 'min' else '>'} limit {r.limit_value:g} {r.unit} "
                    f"-> BREACH (arithmetic). ")
                   + f"Rule: {r.clause} ({r.source[:60]}). The next decision is the Drawing QA Reviewer's "
                     "(project architect) - this is a number, not an approval."}


def dwg_mark(tenant: str, drawing_id: str, status: str, note: str = "") -> dict:
    """The register's walk: received -> under_check -> returned / ok_drafted ('ok' ka matlab yahan
    register ki sthiti hai, architect ka verdict nahi)."""
    if status not in ("received", "under_check", "returned", "ok_drafted"):
        raise CstError("status: received | under_check | returned | ok_drafted")
    with _LOCK, session() as s:
        x = s.get(CDraw, drawing_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Drawing not found.")
        x.status = status
        if note:
            x.note = note[:200]
        dwg_no = x.dwg_no
    return {"say": f"{dwg_no}: register status -> {status}. The architect's verdict is a separate thing - it comes from the review pack."}


def review_pack(tenant: str, drawing_id: str) -> dict:
    """The reviewer's pack: the drawing's checks with rule citations and the architect's sign line
    EMPTY - the PDF that goes to the project architect, never a verdict."""
    with session() as s:
        d = s.get(CDraw, drawing_id)
        if not d or d.tenant_id != tenant:
            raise CstError("Drawing not found.")
        checks = s.scalars(select(CDrawCheck).where(CDrawCheck.tenant_id == tenant,
                                                    CDrawCheck.drawing_id == drawing_id)).all()
    pdf = _review_pdf(d, checks)
    from .. import chatfiles
    f = chatfiles.store(tenant, f"DQA-{d.dwg_no[:20].replace('/', '-')}-{d.id[:6]}.pdf", pdf, "application/pdf")
    breach = sum(1 for c in checks if c.verdict == "breach")
    return {"drawing_id": drawing_id, "checks": len(checks), "breaches": breach, "file": f,
            "say": f"Review pack ready: {d.dwg_no} - {len(checks)} checks ({breach} breach). "
                   "The project architect reviews and signs it - the sign line is empty, they fill it in."}


def _review_pdf(d: CDraw, checks: list) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 50

    def t(a, text, size=10, bold=False):
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(a, y, str(text)[:110])
        y -= size + 5

    t(50, "DRAWING QA - REVIEW PACK", 13, True)
    t(50, f"Project: {d.project}    Drawing: {d.dwg_no} rev {d.rev or '-'}")
    t(50, f"Kind: {d.kind or '-'}    Scale (as noted): {d.scale_as_noted or '-'}")
    t(50, "Document-level check - the PDF was never a model; scale-bar geometry stays with the reader.")
    y -= 8
    if not checks:
        t(50, "No checks recorded yet.", 10)
    for c in checks:
        t(56, f"{c.verdict.upper():6s} rule {c.rule_id}: declared {c.declared:g} vs limit {c.limit_value:g} "
              f"{c.unit}  ({c.checked_on})", 9.5)
    y -= 16
    t(50, "Reviewed by: ____________________________   Date: ____________", 10)
    t(50, "(project architect - Drawing QA Reviewer; Hoola can never fill in this line)", 8.5)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def day(tenant: str) -> dict:
    """The DQA morning: drawings in play, checks recorded, breaches waiting for the architect."""
    with session() as s:
        dws = s.scalars(select(CDraw).where(CDraw.tenant_id == tenant)).all()
        cks = s.scalars(select(CDrawCheck).where(CDrawCheck.tenant_id == tenant)).all()
    breaches = [c for c in cks if c.verdict == "breach"]
    say = (f"Drawing QA: {len(dws)} drawings registered, {len(cks)} checks, {len(breaches)} breach - "
           "without the architect's review pack no drawing is 'fine'.")
    return {"drawings": len(dws), "checks": len(cks), "breaches": len(breaches), "say": say}
