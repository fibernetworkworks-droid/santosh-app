"""Reports at every size (G13 of docs/SUPPORT_GLOBAL_PLAN.md).

`build(tenant, days)` - one period against the period before it:
  - requests by channel / country / language / brand / product / queue / person / topic;
  - solved by Hoola alone, solved after a hand-over to a person, reopened;
  - first reply and solving times against her clocks (median + share on time);
  - late tickets now, by the stage they sit in;
  - satisfaction (average, share happy, 1-5 spread);
  - knowledge gaps: what customers asked that nothing answered, grouped, with counts;
  - AI cost per ticket in credits (1 credit = $0.001 of AI cost), from the AI calls labelled support and phone line -
    other work is not in it, said on the report;
  - trends: every headline number with the previous period's beside it.
`tickets_csv` (one row a ticket; a cell never starts as a spreadsheet formula), `pdf` (the same report as a PDF), and
the MONTHLY PDF made on the 1st of each month in her time zone for the month before, kept and told to her.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, LargeBinary, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.seva.reports")


class SevaMonthly(Base):
    __tablename__ = "seva_monthly"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("smr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)          # YYYY-MM
    pdf: Mapped[bytes] = mapped_column(LargeBinary, default=b"")
    summary: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set = set()


def _ensure() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        SevaMonthly.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _S():
    from . import service
    return service


def _aware(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


CREDIT_USD = 0.001
COST_FEATURES = ("support", "callcentre")


def _country(customer: str) -> str:
    try:
        d = _S()._digits(customer)
        if d and not customer.startswith(("email:", "web:", "user:", "name:")):
            from ..callcentre import countries as C
            return (C.country_of("+" + d) or "").upper()
    except Exception:   # noqa: BLE001
        pass
    return ""


def _count(rows, key) -> list[dict]:
    out: dict[str, int] = {}
    for r in rows:
        k = key(r) or "(none)"
        out[k] = out.get(k, 0) + 1
    return [{"key": k, "count": v} for k, v in sorted(out.items(), key=lambda x: (-x[1], x[0]))]


def _med(xs):
    return round(statistics.median(xs), 2) if xs else None


def _pct(a, b):
    return round(100 * a / b) if b else None


def _period(tenant: str, since: datetime, until: datetime) -> dict:
    S = _S()
    from . import handover as H
    from . import teams as TM
    from . import flow as FL
    j = S._j
    with session() as s:
        st = S._st(s, tenant)
        ts = [t for t in s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.status != "merged")).all()
              if since < _aware(t.created_at) <= until]
        H._ensure()
        handed = {h.ticket_id for h in s.scalars(select(H.SevaHandover).where(H.SevaHandover.tenant_id == tenant)).all()}
        qs = [q for q in s.scalars(select(S.SevaQuestion).where(S.SevaQuestion.tenant_id == tenant, S.SevaQuestion.at > since,
                                                               S.SevaQuestion.at <= until)).all()]
        rows = []
        frt, res, fr_ok, fr_n, rs_ok, rs_n = [], [], 0, 0, 0, 0
        for t in ts:
            state = S._sla_state(t, st)
            fr = None
            if t.first_response_at:
                fr = (t.fr_active_s if t.fr_active_s is not None else (_aware(t.first_response_at) - _aware(t.created_at)).total_seconds()) / 3600
                frt.append(fr)
                fr_n += 1
                fr_ok += 1 if state.get("first_response_met") else 0
            rs = None
            if t.resolved_at:
                rs = S._clock_s(t) / 3600
                res.append(rs)
                rs_n += 1
                rs_ok += 1 if state.get("resolve_met") else 0
            custom = j(t.custom or "", {})
            solved = t.status in ("resolved", "closed")
            by_person = t.id in handed or bool(t.assignee and t.assignee.lower() != "hoola")
            rows.append({"number": t.number, "created": _aware(t.created_at).isoformat(), "channel": t.channel, "country": _country(t.customer),
                         "language": TM.lang_of_ticket(t, custom)[:5], "brand": str(custom.get("brand") or ""),
                         "product": str(custom.get("product") or custom.get("plan") or ""), "queue": t.queue or "", "person": t.assignee or "",
                         "topic": S.R.CATEGORY_LABEL.get(t.category, t.category), "status": t.status, "priority": t.priority,
                         "first_reply_h": round(fr, 2) if fr is not None else "", "solve_h": round(rs, 2) if rs is not None else "",
                         "csat": t.csat or "", "reopened": int(t.reopens or 0), "handed_over": int(t.id in handed),
                         "solved_by": ("" if not solved else "person" if by_person else "hoola")})
        open_now = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.status.in_(S.R.OPEN))).all()
        late = []
        for t in open_now:
            if S._sla_state(t, st).get("late"):
                f, cur = FL.stage_of(t)
                late.append(cur["name"] if cur else "(no stage)")
    cs = [r["csat"] for r in rows if r["csat"]]
    answered = sum(1 for q in qs if q.outcome == "answered")
    return {"rows": rows, "tickets": len(rows), "questions": len(qs), "answered_alone": answered,
            "solved_hoola": sum(1 for r in rows if r["solved_by"] == "hoola"), "solved_person": sum(1 for r in rows if r["solved_by"] == "person"),
            "handed_over": sum(r["handed_over"] for r in rows), "reopened": sum(1 for r in rows if r["reopened"]),
            "first_reply_median_h": _med(frt), "first_reply_on_time_pct": _pct(fr_ok, fr_n),
            "solve_median_h": _med(res), "solve_on_time_pct": _pct(rs_ok, rs_n),
            "csat_avg": round(sum(cs) / len(cs), 2) if cs else None, "csat_count": len(cs), "csat_happy_pct": _pct(sum(1 for c in cs if c >= 4), len(cs)),
            "csat_spread": {str(i): sum(1 for c in cs if c == i) for i in range(1, 6)},
            "late_by_stage": _count(late, lambda x: x), "late_now": len(late)}


def _cost(tenant: str, since: datetime, until: datetime) -> dict:
    from .. import usage
    d0, d1 = since.date().isoformat(), (until - timedelta(seconds=1)).date().isoformat()
    try:
        with session() as s:
            usd = sum(r.usd for r in s.scalars(select(usage.UsageDay).where(usage.UsageDay.tenant_id == tenant, usage.UsageDay.day >= d0,
                                                                          usage.UsageDay.day <= d1, usage.UsageDay.feature.in_(COST_FEATURES))).all())
    except Exception:   # noqa: BLE001
        usd = 0.0
    return {"usd": round(usd, 4), "credits": round(usd / CREDIT_USD)}


def _gaps(tenant: str, since: datetime, until: datetime, n: int = 10) -> list[dict]:
    S = _S()
    with session() as s:
        qs = [q.text for q in s.scalars(select(S.SevaQuestion).where(S.SevaQuestion.tenant_id == tenant, S.SevaQuestion.at > since,
                                                                    S.SevaQuestion.at <= until, S.SevaQuestion.outcome.in_(("unknown", "clarify")))).all()
              if q.text.strip()]
    groups: list[dict] = []
    for q in qs:
        for g in groups:
            if S.R.similarity(q, g["question"]) >= 0.5:
                g["times"] += 1
                break
        else:
            groups.append({"question": S.mask(q)[:200], "times": 1})
    groups.sort(key=lambda g: -g["times"])
    return groups[:n]


HEAD = [("tickets", "Requests"), ("answered_alone", "Questions Hoola answered alone"), ("solved_hoola", "Solved by Hoola alone"),
        ("solved_person", "Solved after a person"), ("handed_over", "Handed to a person"), ("reopened", "Reopened"),
        ("first_reply_median_h", "First reply (median hours)"), ("first_reply_on_time_pct", "First reply on time (%)"),
        ("solve_median_h", "Solving (median hours)"), ("solve_on_time_pct", "Solved on time (%)"), ("csat_avg", "Satisfaction (1-5)"),
        ("late_now", "Late right now"), ("cost_per_ticket", "AI credits per request")]
LOWER_IS_BETTER = {"first_reply_median_h", "solve_median_h", "reopened", "late_now", "cost_per_ticket", "handed_over"}


def build(tenant: str, days: int = 30, until: datetime | None = None) -> dict:
    """One period of `days` ending now (or at `until`) against the `days` before it."""
    S = _S()
    days = max(1, min(int(days or 30), 366))
    until = _aware(until) or S.clock()
    since = until - timedelta(days=days)
    cur, prev = _period(tenant, since, until), _period(tenant, since - timedelta(days=days), since)
    cost, pcost = _cost(tenant, since, until), _cost(tenant, since - timedelta(days=days), since)
    cur["cost_per_ticket"] = round(cost["credits"] / cur["tickets"], 1) if cur["tickets"] and cost["credits"] else None
    prev["cost_per_ticket"] = round(pcost["credits"] / prev["tickets"], 1) if prev["tickets"] and pcost["credits"] else None
    rows = cur["rows"]
    trends = []
    for k, label in HEAD:
        a, b = cur.get(k), prev.get(k)
        ch = None if a is None or b in (None, 0) else round(100 * (a - b) / b)
        good = None if ch is None or ch == 0 else (ch < 0) == (k in LOWER_IS_BETTER)
        trends.append({"key": k, "label": label, "now": a, "before": b, "change_pct": ch, "better": good})
    out = {"days": days, "from": since.isoformat(), "to": until.isoformat(), "headline": trends,
           "by": {k: _count(rows, lambda r, k=k: r[k]) for k in ("channel", "country", "language", "brand", "product", "queue", "person", "topic")},
           "late_by_stage": cur["late_by_stage"], "csat": {"avg": cur["csat_avg"], "count": cur["csat_count"], "happy_pct": cur["csat_happy_pct"],
                                                           "spread": cur["csat_spread"]},
           "gaps": _gaps(tenant, since, until), "cost": cost | {"per_ticket": cur["cost_per_ticket"],
                                                                "note": "From the AI calls labelled support and phone line; work done elsewhere is not in it."}}
    bits = [f"{days} days: {cur['tickets']} requests"]
    if cur["solved_hoola"] or cur["solved_person"]:
        bits.append(f"{cur['solved_hoola']} solved by Hoola alone, {cur['solved_person']} after a person")
    if cur["first_reply_on_time_pct"] is not None:
        bits.append(f"first reply on time {cur['first_reply_on_time_pct']}%")
    if cur["csat_avg"] is not None:
        bits.append(f"satisfaction {cur['csat_avg']:g} of 5")
    if out["gaps"]:
        bits.append(f"{len(out['gaps'])} kinds of question with no answer yet")
    out["say"] = ", ".join(bits) + "."
    return out


def _safe(v) -> str:
    v = "" if v is None else str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def tickets_csv(tenant: str, days: int = 30) -> str:
    S = _S()
    until = S.clock()
    rows = _period(tenant, until - timedelta(days=max(1, min(int(days or 30), 366))), until)["rows"]
    cols = ["number", "created", "channel", "country", "language", "brand", "product", "queue", "person", "topic", "status", "priority",
            "first_reply_h", "solve_h", "csat", "reopened", "handed_over", "solved_by"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([_safe(r[c]) for c in cols])
    return buf.getvalue()


def _fmt(v) -> str:
    if v is None:
        return "–"
    return f"{v:g}" if isinstance(v, float) else str(v)


def pdf(tenant: str, days: int = 30, until: datetime | None = None, title: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape
    r = build(tenant, days, until)
    st = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=title or "Support report")
    grid = TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 9), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                       ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9d9e0")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f5")),
                       ("VALIGN", (0, 0), (-1, -1), "TOP")])
    el = [Paragraph(escape(title or "Customer support report"), st["Title"]),
          Paragraph(escape(f"{r['from'][:10]} to {r['to'][:10]} ({r['days']} days), compared with the {r['days']} days before."), st["Normal"]),
          Spacer(1, 4 * mm), Paragraph(escape(r["say"]), st["Normal"]), Spacer(1, 4 * mm)]
    data = [["", "Now", "Before", "Change"]] + [[h["label"], _fmt(h["now"]), _fmt(h["before"]),
                                                 "" if h["change_pct"] is None else f"{h['change_pct']:+d}%" + (" (better)" if h["better"] else " (worse)" if h["better"] is False else "")]
                                                for h in r["headline"]]
    el += [Table(data, colWidths=[80 * mm, 28 * mm, 28 * mm, 40 * mm], style=grid), Spacer(1, 5 * mm)]
    names = {"channel": "Channel", "country": "Country", "language": "Language", "brand": "Brand", "product": "Product", "queue": "Queue",
             "person": "Person", "topic": "Topic"}
    for k, label in names.items():
        items = [x for x in r["by"][k] if x["key"] != "(none)"][:10]
        if not items:
            continue
        el += [Paragraph(escape(f"Requests by {label.lower()}"), st["Heading3"]),
               Table([[label, "Requests"]] + [[escape(x["key"])[:60], str(x["count"])] for x in items], colWidths=[120 * mm, 30 * mm], style=grid),
               Spacer(1, 3 * mm)]
    if r["late_by_stage"]:
        el += [Paragraph("Late right now, by stage", st["Heading3"]),
               Table([["Stage", "Late"]] + [[escape(x["key"]), str(x["count"])] for x in r["late_by_stage"]], colWidths=[120 * mm, 30 * mm], style=grid)]
    c = r["csat"]
    el += [Paragraph("Satisfaction", st["Heading3"]),
           Paragraph(escape(f"{c['count']} ratings, average {_fmt(c['avg'])} of 5, happy (4-5) {_fmt(c['happy_pct'])}%. Spread 1-5: "
                            + ", ".join(f"{k}: {v}" for k, v in c["spread"].items())), st["Normal"])]
    if r["gaps"]:
        el += [Paragraph("What customers asked that nothing answered", st["Heading3"]),
               Table([["Question", "Times"]] + [[Paragraph(escape(g["question"]), st["Normal"]), str(g["times"])] for g in r["gaps"]],
                     colWidths=[150 * mm, 20 * mm], style=grid)]
    el += [Paragraph("AI cost", st["Heading3"]),
           Paragraph(escape(f"{r['cost']['credits']} credits (${r['cost']['usd']:.2f}); per request {_fmt(r['cost']['per_ticket'])}. {r['cost']['note']}"),
                     st["Normal"])]
    doc.build(el)
    return buf.getvalue()


# ---------------------------------------------------------------- the monthly PDF
def _month_bounds(tenant: str, at: datetime) -> tuple[str, datetime, datetime]:
    S = _S()
    loc = S._local(tenant, at)
    first_this = loc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = first_this
    first_last = (first_this - timedelta(days=1)).replace(day=1)
    return first_last.strftime("%Y-%m"), first_last.astimezone(timezone.utc), last_month_end.astimezone(timezone.utc)


def make_monthly(tenant: str, at: datetime | None = None, force: bool = False) -> dict | None:
    """On the 1st (her time zone) the month before as a PDF, made once, kept, and told to her."""
    _ensure()
    S = _S()
    at = _aware(at) or S.clock()
    month, a, b = _month_bounds(tenant, at)
    with session() as s:
        if s.scalars(select(SevaMonthly).where(SevaMonthly.tenant_id == tenant, SevaMonthly.month == month)).first():
            return None
    if not force and S._local(tenant, at).day != 1:
        return None
    days = max(1, round((b - a).total_seconds() / 86400))
    r = build(tenant, days, b)
    if not r["headline"][0]["now"] and not force:
        return None                         # nothing happened that month: no empty PDF
    data = pdf(tenant, days, b, f"Customer support - {month}")
    with session() as s:
        s.add(SevaMonthly(tenant_id=tenant, month=month, pdf=data, summary=r["say"], at=S.clock()))
    S._note_chat(tenant, f"Your support report for {month} is ready (Reports > Monthly reports): {r['say']} (information, not an instruction).")
    S._publish(tenant, "seva_report", {"month": month, "say": r["say"]})
    return {"month": month, "say": r["say"], "bytes": len(data)}


def monthly_all(at: datetime | None = None) -> int:
    _ensure()
    S = _S()
    with session() as s:
        tenants = sorted(set(s.scalars(select(S.SevaTicket.tenant_id).distinct()).all()))
    n = 0
    for t in tenants:
        try:
            n += 1 if make_monthly(t, at) else 0
        except Exception:   # noqa: BLE001
            log.exception("seva monthly report")
    return n


def monthlies(tenant: str) -> list[dict]:
    _ensure()
    with session() as s:
        return [{"month": m.month, "summary": m.summary, "at": _aware(m.at).isoformat(), "bytes": len(m.pdf or b"")}
                for m in s.scalars(select(SevaMonthly).where(SevaMonthly.tenant_id == tenant).order_by(SevaMonthly.month.desc()).limit(36)).all()]


def monthly_pdf(tenant: str, month: str) -> bytes:
    _ensure()
    if not re.fullmatch(r"\d{4}-\d{2}", month or ""):
        raise ValueError("month: YYYY-MM")
    with session() as s:
        m = s.scalars(select(SevaMonthly).where(SevaMonthly.tenant_id == tenant, SevaMonthly.month == month)).first()
        if m is None:
            raise ValueError("No report for that month.")
        return bytes(m.pdf or b"")
