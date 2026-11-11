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
    return {"per_run": int(st.leads_max_rows_per_run), "per_day": int(st.leads_max_rows_per_day),
            "enrich_rows_per_run": int(st.leads_enrich_rows_per_run),   # v0.542.0: the P2 pass's own bound
            "scrape_max_cells": int(st.leads_scrape_max_cells),         # v0.543.0: the P3 grid's plan-time ceiling
            "scrape_pages_per_cell": int(st.leads_scrape_pages_per_cell)}


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
        raise LeadsCapped(f"This run asks for {w['per_run']['planned']:,} rows - the cap for one run is "
                          f"{w['per_run']['cap']:,} rows. Make the plan smaller (grid / filters), or have the cap changed, only with "
                          f"your approval. (Per-run cap, refused at plan time - the run did not start.)")
    if not w["per_day"]["ok"]:
        raise LeadsCapped(f"After today's {w['per_day']['already_kept']} kept rows, {w['per_day']['planned']:,} more rows "
                          f"would cross the day's cap of {w['per_day']['cap']:,}. Try again tomorrow, or make the plan smaller. "
                          f"(Per-day cap {w['per_day']['cap']:,} rows/tenant, refused at plan time.)")
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
