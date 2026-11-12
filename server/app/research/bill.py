"""v0.476 R5 KHARCHA - what a research run costs, a ceiling that REFUSES BEFORE it spends, and the numbers measured instead of assumed.

Plan: `docs/RESEARCH_PRO_PLAN.md` part 9 (Valyu `data_max_price` + Exa's itemised `num_pages / num_searches / reasoning_tokens` + Parallel's tiers),
built like `mapsbill.py`: the cap exists BEFORE any paid engine (R6) is switched on.

  METER      a run's model calls are counted by `usage.run_meter` (a context-scoped meter fed by `usage.record`, so a chat of the same tenant
             that happens to run at the same time is NOT in it). Price = `usage.cost` x `usage.usd_inr()` - the same list price every other
             feature uses, never a number typed here. A run restarted after a crash starts its meter at what the run had ALREADY spent.
  WEB        search / fetch calls are COUNTED and shown, but their rupee price is UNKNOWN until her Parallel plan is read: `research_search_inr` /
             `research_fetch_inr` default to 0 and every cost line says "web price not known" until she sets them. A cost shown as complete
             while a part of it is unpriced would be a lie, so the line carries the flag.
  CEILINGS   a per-RUN cap (`research_run_cap_inr`) and a per-TENANT per-DAY cap (`research_daily_inr`, IST, the sum of that tenant's runs). A run
             asks `afford()` before EVERY model call, with `research_call_reserve_inr` of room; when it cannot, it stops at once, keeps what it
             found, and says "cost ceiling" on its dossier. A new run is refused outright when the day's room is gone (`preflight`).
             The defaults are defaults, not measured needs - say so wherever they are shown.
  MEASURED   `measured_per_goal(tenant)` = the median rupees per goal of her own finished runs (needs 3); the plan card (R1) uses it instead of
             the assumed sizes once it exists, and says which it used.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta
from typing import Any

from . import store

IST_OFFSET = timedelta(hours=5, minutes=30)
MIN_RUNS_FOR_MEASURE = 3


class ResearchCapped(Exception):
    """A research run was refused (or stopped) because the next call would cross a ceiling."""


def _st():
    from ..config import get_settings
    return get_settings()


def day_start_utc(at: datetime | None = None) -> datetime:
    """Midnight of the current IST day, as an aware UTC datetime."""
    from datetime import timezone
    n = (at or datetime.now(timezone.utc)).astimezone(timezone(IST_OFFSET))
    return n.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def caps() -> dict[str, float]:
    st = _st()
    return {"run_inr": float(st.research_run_cap_inr), "day_inr": float(st.research_daily_inr),
            "reserve_inr": float(st.research_call_reserve_inr)}


def web_prices() -> dict[str, Any]:
    st = _st()
    s, f = float(st.research_search_inr), float(st.research_fetch_inr)
    return {"search_inr": s, "fetch_inr": f, "known": s > 0 or f > 0}


class Meter:
    """One run's tally. `acc` is the dict `usage.run_meter` fills; `base` is what the run had spent before this process (a resume)."""

    def __init__(self, tenant: str, run_id: str = "", base: dict | None = None, acc: dict | None = None):
        self.tenant, self.run_id = tenant, run_id
        self.acc = acc if acc is not None else {"usd": 0.0, "calls": 0, "tok_in": 0, "tok_out": 0, "by_model": {}}
        self.base = base or {}
        self.counts: dict[str, int] = {"searches": 0, "fetches": 0}
        self._day_base: float | None = None
        # v0.477 R6: a vendor engine's charge (NOT a model call, so usage.record never sees it). Starts as the run's PRICE (the committed
        # estimate), becomes the vendor's own reported cost when it reports one. A restart carries it in `base`.
        self.vendor: dict[str, Any] = dict(self.base.get("vendor") or {})
        # wave 9: calls granted by afford() that have not been counted yet. Goals run IN PARALLEL, so up to six workers
        # used to pass afford() at Rs 147 of a Rs 150 cap and then each spend ~Rs 10: the spend only grows after a call
        # returns. Every granted call now holds its likely price until the meter has counted it.
        self._granted = 0
        self._calls0 = int(self.acc.get("calls", 0))

    # -- the money
    def model_inr(self) -> float:
        from .. import usage
        return round(float(self.base.get("model_inr", 0.0)) + float(self.acc.get("usd", 0.0)) * usage.usd_inr(), 4)

    def web_inr(self) -> float:
        p = web_prices()
        n_s = int(self.base.get("searches", 0)) + self.counts["searches"]
        n_f = int(self.base.get("fetches", 0)) + self.counts["fetches"]
        return round(n_s * p["search_inr"] + n_f * p["fetch_inr"], 4)

    def vendor_inr(self) -> float:
        return round(float(self.vendor.get("inr", 0.0)), 4)

    def set_vendor(self, engine: str, inr: float, known: bool, note: str = "") -> None:
        """Replace (never add to) the vendor line: first the price committed at the start, later the real cost if the vendor reported one."""
        self.vendor = {"engine": engine, "inr": round(float(inr), 4), "known": bool(known), "note": note[:200]}

    def total_inr(self) -> float:
        return round(self.model_inr() + self.web_inr() + self.vendor_inr(), 4)

    def update_counts(self, searches: int, fetches: int) -> None:
        self.counts["searches"], self.counts["fetches"] = max(0, searches), max(0, fetches)

    # -- the ceilings
    def day_spent_inr(self) -> float:
        """Today's rupees for this tenant: other runs as saved + this run's live total (so two runs share one day's room)."""
        others = store.spent_since(self.tenant, day_start_utc(), exclude=self.run_id)
        return round(others + self.total_inr(), 4)

    def held_inr(self) -> float:
        """The likely price of the calls already granted and still running (not yet in the meter)."""
        done = max(0, int(self.acc.get("calls", 0)) - self._calls0)
        return round(max(0, self._granted - done) * per_call_inr(), 4)

    def afford(self) -> tuple[bool, str]:
        c = caps()
        need = max(float(c["reserve_inr"]), per_call_inr())   # the call about to be made, at its likely price
        spent, held = self.total_inr(), self.held_inr()
        if spent + held + need > c["run_inr"]:
            return False, (f"this run has spent Rs {spent:.0f} of its Rs {c['run_inr']:.0f} ceiling"
                           + (f" (Rs {held:.0f} more is held by calls still running)" if held >= 0.5 else ""))
        day = self.day_spent_inr()
        if day + held + need > c["day_inr"]:
            return False, (f"today's research has spent Rs {day:.0f} of the Rs {c['day_inr']:.0f} daily ceiling"
                           + (f" (Rs {held:.0f} more is held by calls still running)" if held >= 0.5 else ""))
        self._granted += 1
        return True, ""

    # -- the itemised line
    def breakdown(self, stop: str = "") -> dict[str, Any]:
        from .. import usage
        p, c = web_prices(), caps()
        n_s = int(self.base.get("searches", 0)) + self.counts["searches"]
        n_f = int(self.base.get("fetches", 0)) + self.counts["fetches"]
        by = {k: {"calls": v["calls"], "inr": round(v["usd"] * usage.usd_inr(), 4)} for k, v in self.acc.get("by_model", {}).items()}
        for k, v in (self.base.get("by_model") or {}).items():
            cur = by.setdefault(k, {"calls": 0, "inr": 0.0})
            cur["calls"] += v.get("calls", 0)
            cur["inr"] = round(cur["inr"] + v.get("inr", 0.0), 4)
        return {"total_inr": self.total_inr(), "model_inr": self.model_inr(), "web_inr": self.web_inr(), "vendor": dict(self.vendor),
                "vendor_inr": self.vendor_inr(),
                "model_calls": int(self.base.get("model_calls", 0)) + int(self.acc.get("calls", 0)),
                "tok_in": int(self.base.get("tok_in", 0)) + int(self.acc.get("tok_in", 0)),
                "tok_out": int(self.base.get("tok_out", 0)) + int(self.acc.get("tok_out", 0)),
                "by_model": by, "searches": n_s, "fetches": n_f, "web_price_known": p["known"],
                "model_prices_known": all(usage.price_of(m)[1] for m in by) if by else True,
                "run_cap_inr": c["run_inr"], "day_cap_inr": c["day_inr"], "stopped_by_cost": bool(stop), "stop": stop}

    def carry(self) -> dict[str, Any]:
        """What a restarted run starts from (its saved breakdown becomes `base`)."""
        b = self.breakdown()
        return {"model_inr": b["model_inr"], "model_calls": b["model_calls"], "tok_in": b["tok_in"], "tok_out": b["tok_out"],
                "searches": b["searches"], "fetches": b["fetches"], "by_model": b["by_model"]}


def per_call_inr(tok_in: int = 12000, tok_out: int = 2500) -> float:
    """wave 9: the likely rupees of ONE research model call (a worker step: page context in, up to 2,500 tokens out) at the
    model the SDK door really sends - never the flat Rs 3 reserve, which one Sonnet call with page context exceeds."""
    try:
        from .. import usage
        from ..config import get_settings
        st = get_settings()
        model = usage.one_model({"model": str(getattr(st, "anthropic_model", "") or "claude")})["model"]
        p, _known = usage.price_of(model)
        usd = (tok_in * float(p.get("in", 0.0)) + tok_out * float(p.get("out", 0.0))) / 1_000_000
        return round(usd * usage.usd_inr(), 4)
    except Exception:   # noqa: BLE001
        return 3.0


def preflight(tenant: str) -> None:
    """Refuse a NEW run when the day's room is already gone. (The run's own ceiling is enforced as it works.)"""
    c = caps()
    spent = store.spent_since(tenant, day_start_utc())
    if spent + c["reserve_inr"] > c["day_inr"]:
        raise ResearchCapped(f"Today's research budget is used up: Rs {spent:.0f} has been spent, the ceiling is Rs {c['day_inr']:.0f} "
                             f"(it can be changed with RESEARCH_DAILY_INR). Try again tomorrow, or raise the ceiling.")


def format_line(b: dict, hi: bool = False) -> str:
    """The cost as one honest line. An unpriced part is said, not hidden."""
    web = ("web price abhi pata nahi" if hi else "web price not known") if not b.get("web_price_known") else \
          (f"web Rs {b['web_inr']:.1f}" if not hi else f"web Rs {b['web_inr']:.1f}")
    v = b.get("vendor") or {}
    ven_hi = (f", {v['engine']} Rs {v['inr']:.1f} ({'vendor ka apna hisaab' if v.get('known') else 'andaza - vendor ne kharcha nahi bataya'})") if v else ""
    ven_en = (f", {v['engine']} Rs {v['inr']:.1f} ({'reported by the vendor' if v.get('known') else 'an ESTIMATE - the vendor did not report its cost'})") if v else ""
    head = (f"Kharcha: Rs {b['total_inr']:.1f} (model Rs {b['model_inr']:.1f}, {b['model_calls']} calls{ven_hi}; {b['searches']} searches + "
            f"{b['fetches']} pages - {web}) / run seema Rs {b['run_cap_inr']:.0f}") if hi else \
           (f"Cost: Rs {b['total_inr']:.1f} (model Rs {b['model_inr']:.1f}, {b['model_calls']} calls{ven_en}; {b['searches']} searches + "
            f"{b['fetches']} pages - {web}) of a Rs {b['run_cap_inr']:.0f} ceiling")
    if b.get("stopped_by_cost"):
        head += (" - ROKA GAYA: " if hi else " - STOPPED: ") + str(b.get("stop"))
    return head


# ---------------------------------------------------------------- measured, not assumed
def measured_per_goal(tenant: str) -> dict[str, Any] | None:
    """Median rupees per goal over her own finished runs that really cost something (needs MIN_RUNS_FOR_MEASURE). None = not enough yet."""
    rows = [r for r in store.costs(tenant, 12) if r["cost_inr"] > 0 and r["goals"] > 0]
    if len(rows) < MIN_RUNS_FOR_MEASURE:
        return None
    per = [r["cost_inr"] / r["goals"] for r in rows]
    return {"per_goal_inr": round(statistics.median(per), 2), "runs": len(rows), "max_run_inr": round(max(r["cost_inr"] for r in rows), 2)}


def usage_report(tenant: str) -> dict[str, Any]:
    c = caps()
    today = store.spent_since(tenant, day_start_utc())
    month = store.spent_since(tenant, day_start_utc().replace(day=1))
    from . import vendors
    return {"engines": vendors.status_table(), "today_inr": today, "month_inr": month, "caps": c, "left_today_inr": round(max(0.0, c["day_inr"] - today), 2),
            "web": web_prices(), "measured": measured_per_goal(tenant),
            "assumed": ["the ceilings are defaults, not measured needs",
                        *([] if web_prices()["known"] else ["the rupee price of a web search / page fetch is UNKNOWN (set RESEARCH_SEARCH_INR / RESEARCH_FETCH_INR once her plan is read): "
                                                            "web calls are counted but not priced"]),
                        "model rupees = list price x the server's USD->INR rate (`usage.PRICES`), not an invoice",
                        "a vendor engine's cost is the price YOU set per run unless the vendor reports its own (Exa does); no vendor wire format has been answered live"],
            "runs": [{"id": r["id"], "goals": r["goals"], "cost_inr": r["cost_inr"], "status": r["status"]} for r in store.costs(tenant, 10, only_done=False)]}
