"""v0.540.0 LEADS NEEV - the caps that REFUSE BEFORE the run (the mapsbill lesson, ported to leads).

The plan (docs/LEADS_PLAN.md, sections 2 and 5.6) is explicit: `mapsbill.py`'s daily rupee cap REFUSES BEFORE the
call -> `leadscap.py` refuses the run at PLAN time. A 50,000-row ask is REFUSED WITH THE CAP NAMED, not silently
truncated at row 5,000 and not stopped at row 4,999 either. The counters live in lead_cap_days (a small ledger, so
leads_forget deleting rows cannot also erase the memory that they were counted), keyed per tenant per UTC day.

P0 counts ROWS only - the per-host request caps and politeness sleeps belong to the scrape lane (P3) and will join
the same check_run() so a plan can never pass one cap by naming another lane."""
from __future__ import annotations

from datetime import datetime, timezone

from .config import get_settings


class LeadsCapped(Exception):
    """Raised at PLAN time; the message names the cap and the number, because a refusal that does not say why
    teaches her nothing."""


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def ensure_table() -> None:
    from .leads.models import ensure_tables
    ensure_tables()


def _ledgers(tenant: str) -> tuple[int, int]:
    ensure_table()
    from .db import session
    from .leads.models import LeadCapDay
    with session() as s:
        row = s.query(LeadCapDay).filter(LeadCapDay.tenant_id == tenant, LeadCapDay.day == today()).first()
        return (int(row.rows_kept or 0), int(row.runs_started or 0)) if row else (0, 0)


def caps() -> dict[str, int]:
    st = get_settings()
    return {"per_run": int(st.leads_max_rows_per_run), "per_day": int(st.leads_max_rows_per_day)}


def usage(tenant: str) -> dict:
    kept, runs = _ledgers(tenant)
    c = caps()
    return {"day": today(), "rows_kept": kept, "runs_started": runs,
            "per_run": c["per_run"], "per_day": c["per_day"], "per_run_left": c["per_run"], "per_day_left": c["per_day"] - kept}


def would_exceed(tenant: str, planned_rows: int, runs: int = 1) -> dict:
    """The check WITHOUT the raise - what a plan card shows before she says go."""
    c = caps()
    kept, _ = _ledgers(tenant)
    per_run_ok = 0 <= planned_rows <= c["per_run"]
    per_day_ok = kept + max(0, planned_rows) <= c["per_day"]
    return {"ok": per_run_ok and per_day_ok, "per_run": {"planned": planned_rows, "cap": c["per_run"], "ok": per_run_ok},
            "per_day": {"already_kept": kept, "planned": planned_rows, "cap": c["per_day"], "ok": per_day_ok},
            "day": today()}


def check_run(tenant: str, planned_rows: int, runs: int = 1) -> dict:
    """Refuse BEFORE the run. The card the caller gets back on success carries the same numbers, so the plan and
    the run cannot drift apart."""
    w = would_exceed(tenant, planned_rows, runs)
    if not w["per_run"]["ok"]:
        raise LeadsCapped(f"Yeh run {w['per_run']['planned']:,} rows maang raha hai - ek run ka cap "
                          f"{w['per_run']['cap']:,} rows hai. Plan chhota kijiye (grid / filters), warna aapki haan se "
                          f"cap badalwaiye. (Per-run cap, plan time par refuse kiya - run shuru nahi hua.)")
    if not w["per_day"]["ok"]:
        raise LeadsCapped(f"Aaj ke {w['per_day']['already_kept']} kept rows ke baad {w['per_day']['planned']:,} aur rows "
                          f"day ka cap {w['per_day']['cap']:,} paar karta hai. Kal phir, ya plan chhota kijiye. "
                          f"(Per-day cap {w['per_day']['cap']:,} rows/tenant, plan time par refuse kiya.)")
    return {"planned_rows": planned_rows, "runs": runs, "caps": caps(), "day": today(), "checked_at_plan": True}


def record(tenant: str, kept: int, runs: int = 1) -> None:
    """Ledger AFTER the run: rows actually kept (not planned). forget() deletes contacts, never this ledger."""
    if kept <= 0 and runs <= 0:
        return
    ensure_table()
    from .db import session
    from .leads.models import LeadCapDay
    with session() as s:
        row = s.query(LeadCapDay).filter(LeadCapDay.tenant_id == tenant, LeadCapDay.day == today()).first()
        if row is None:
            row = LeadCapDay(tenant_id=tenant, day=today())
            s.add(row)
            s.flush()
        row.rows_kept = int(row.rows_kept or 0) + max(0, kept)
        row.runs_started = int(row.runs_started or 0) + max(0, runs)
