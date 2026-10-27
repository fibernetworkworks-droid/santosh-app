"""Gyaan records (v0.135): what she has ALREADY told Hoola in other screens, made searchable with the rest of her Gyaan.

  - Business profile (Employee): name, kind, what she sells / does, hours, her own rules
  - Seva: her live FAQ answers and policy lines (drafts never)
  - Kalam: her fact sheet + what she said about the business, and pieces she has PUBLISHED
  - Price list: her Hoola stock / rate card (name, unit, price, GST, bulk prices; never quantities, which change hourly)

Only her own business text; no customer records, no money ledgers, no staff salaries. Each collector is independent: a
module that is missing or changed simply contributes nothing. Rebuilt every 6 hours (unchanged text = no-op)."""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("santosh.gyaan")


def _j(v: Any, d: Any) -> Any:
    if isinstance(v, (list, dict)):
        return v
    try:
        return json.loads(v or "")
    except (TypeError, ValueError):
        return d


def _profile(tenant: str) -> list[dict[str, Any]]:
    from ..db import session
    from ..employee.models import EmployeeProfile
    with session() as s:
        p = s.get(EmployeeProfile, tenant)
        if not p:
            return []
        lines = []
        if p.business_name:
            lines.append(f"Business ka naam: {p.business_name}")
        if p.business_kind:
            lines.append(f"Kaam: {p.business_kind}")
        if p.about:
            lines.append(f"Business ke baare mein: {p.about}")
        h = _j(p.hours, {})
        if h.get("open") and h.get("close"):
            days = "Mon Tue Wed Thu Fri Sat Sun".split()
            dd = ", ".join(days[d] for d in h.get("days") or [] if 0 <= int(d) < 7)
            lines.append(f"Samay: {h['open']} se {h['close']}" + (f" ({dd})" if dd else ""))
        if p.rules:
            lines.append(f"Niyam: {p.rules}")
    if not lines:
        return []
    return [{"ref": "record:profile", "what": "profile", "title": "Business ki jaankari", "text": "\n".join(lines)}]


def _seva(tenant: str) -> list[dict[str, Any]]:
    from ..db import session
    from ..seva.service import SevaEntry
    with session() as s:
        rows = s.query(SevaEntry).filter(SevaEntry.tenant_id == tenant, SevaEntry.status == "live").all()
        faq = [(r.question, r.answer, r.kind) for r in rows if (r.question or r.answer)]
    out = []
    for kind, title in (("faq", "Graahakon ke sawaal-jawab (Seva)"), ("policy", "Business ki policy (Seva)")):
        lines = [f"Q: {q}\nA: {a}" if q else f"- {a}" for q, a, k in faq if k == kind]
        if lines:
            out.append({"ref": f"record:seva:{kind}", "what": "seva", "title": title, "text": "\n\n".join(lines)})
    return out


def _kalam(tenant: str) -> list[dict[str, Any]]:
    from ..db import session
    from ..kalam.service import KalamPiece, KalamSettings
    out = []
    with session() as s:
        st = s.get(KalamSettings, tenant)
        if st:
            facts = [f.get("fact", "") for f in _j(st.facts, []) if isinstance(f, dict) and f.get("fact")]
            lines = []
            if st.business:
                lines.append(f"Business: {st.business}")
            if st.about:
                lines.append(st.about)
            lines += [f"- {f}" for f in facts]
            if lines:
                out.append({"ref": "record:kalam:facts", "what": "kalam", "title": "Business ke pakke facts (Kalam)",
                            "text": "\n".join(lines)})
        pieces = (s.query(KalamPiece).filter(KalamPiece.tenant_id == tenant, KalamPiece.status == "published")
                  .order_by(KalamPiece.updated_at.desc()).limit(30).all())
        for p in pieces:
            title = (p.title or _j(p.meta, {}).get("meta_title") or p.keyword or (p.brief or "")[:60] or "Lekh")
            if (p.body or "").strip():
                out.append({"ref": f"record:kalam:{p.id}", "what": "kalam", "title": f"Chhapa hua: {title}"[:160],
                            "text": p.body, "at": str(getattr(p, "updated_at", "") or "")[:10]})
    return out


def _prices(tenant: str) -> list[dict[str, Any]]:
    from ..db import session
    from ..net.deal import StockItem
    with session() as s:
        rows = s.query(StockItem).filter(StockItem.tenant_id == tenant).order_by(StockItem.name).limit(800).all()
        items = [(r.name, r.unit, r.price, r.gst_pct, _j(r.tiers, []), r.kind or "goods", r.public) for r in rows]
    if not items:
        return []
    lines = ["Item | Unit | Daam (GST se pehle) | GST % | Bulk daam"]
    for name, unit, price, gst, tiers, kind, _pub in items:
        bulk = "; ".join(f"{t.get('min')}+ par Rs {t.get('price')}" for t in tiers if isinstance(t, dict))
        lines.append(f"{name}{' (seva)' if kind == 'service' else ''} | {unit or '-'} | Rs {price:g} | {gst:g} | {bulk or '-'}")
    return [{"ref": "record:prices", "what": "prices", "title": "Mera daam / rate list", "text": "\n".join(lines),
             "kind": "sheet"}]


COLLECTORS = (_profile, _seva, _kalam, _prices)


def collect(tenant: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in COLLECTORS:
        try:
            out += f(tenant)
        except Exception as e:                      # one Sahayak missing / changed never stops the rest
            log.info("gyaan records: %s skipped: %s", f.__name__, e)
    return out
