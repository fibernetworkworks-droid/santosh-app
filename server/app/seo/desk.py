"""v0.314 THE SEO EMPLOYEE (Phase 0 + 1 of docs/SEO_EMPLOYEE_PLAN.md): what a hired SEO Specialist does on its own.

    hire (employee/hire.py) -> onboard (her site, goals, cities, competitors, trust)
        -> first run: full crawl (up to 500 pages), speed, Search Console, Google Analytics -> BASELINE (frozen)
        -> 90-DAY ROADMAP (Opus from the real audit + opportunities; rules when Opus is off) -> she approves it
    24/7 (run_due, from the worker every few minutes, only for tenants whose SEO employee is HIRED and not paused):
        hourly  watch: site up, robots.txt not blocking Google, home page not noindex, sitemap reachable -> alert on change
        daily   Search Console + Analytics numbers (28 days, same window as the baseline) -> drop alert
        weekly  full crawl + speed + Search Console snapshot (her weekday)
        monthly the report PDF (Hoola Print: Key takeaways, charts, baseline vs now, work done, next month)
    the desk (desk_view) = KPIs against the baseline, the roadmap board, alerts and runs.

Read-only toward her website and Google in this phase: nothing is published or changed anywhere (Phase 2 adds hands
with the trust gate). Official APIs only: Search Console, Analytics Data / Admin, PageSpeed. Her site is crawled with
robots.txt honoured, same host, public addresses only (service._fetch)."""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import rules as R
from . import service as S

log = logging.getLogger("santosh.seo.desk")
KEY = "seo"
GA4_ADMIN = "https://analyticsadmin.googleapis.com/v1beta"
GA4_DATA = "https://analyticsdata.googleapis.com/v1beta"
WORKSTREAMS = ("technical", "content", "local", "authority", "ai_search", "reporting")
BOARD = ("planned", "doing", "waiting_her", "done", "skipped")
_RUNNING: set[str] = set()
_RUN_LOCK = threading.Lock()
_LAST_SWEEP = {"at": 0.0}


class SeoDesk(Base):
    """The employee's own record of one site: what she wants, the frozen baseline, the latest numbers, its clock."""
    __tablename__ = "seo_desk"
    site_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    goals: Mapped[str] = mapped_column(Text, default="{}")            # goal, customers, cities, notes
    competitors: Mapped[str] = mapped_column(Text, default="[]")
    ga4_property: Mapped[str] = mapped_column(String(60), default="")
    baseline: Mapped[str] = mapped_column(Text, default="{}")
    baseline_at: Mapped[str] = mapped_column(String(20), default="")
    latest: Mapped[str] = mapped_column(Text, default="{}")
    watch: Mapped[str] = mapped_column(Text, default="{}")
    stamps: Mapped[str] = mapped_column(Text, default="{}")           # hourly / daily / weekly / monthly last run
    roadmap_status: Mapped[str] = mapped_column(String(12), default="none")   # none | draft | approved
    state: Mapped[str] = mapped_column(String(16), default="new")     # new | first_run | ready | error
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SeoRoadmapItem(Base):
    __tablename__ = "seo_roadmap"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    week: Mapped[int] = mapped_column(Integer, default=1)
    workstream: Mapped[str] = mapped_column(String(16), default="technical")
    title: Mapped[str] = mapped_column(String(160), default="")
    why: Mapped[str] = mapped_column(Text, default="")
    impact: Mapped[int] = mapped_column(Integer, default=2)
    effort: Mapped[int] = mapped_column(Integer, default=2)
    owner: Mapped[str] = mapped_column(String(10), default="hoola")     # hoola | her (needs her / her developer)
    status: Mapped[str] = mapped_column(String(12), default="planned")
    source: Mapped[str] = mapped_column(String(8), default="rules")    # opus | rules
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SeoEvent(Base):
    """What the employee did and saw: alerts, recoveries, runs, reports. The desk's activity feed."""
    __tablename__ = "seo_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("se"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="run")       # alert | recovered | run | report | note
    level: Mapped[str] = mapped_column(String(6), default="info")      # bad | warn | info | ok
    text: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[str] = mapped_column(Text, default="{}")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for t in (SeoDesk, SeoRoadmapItem, SeoEvent):
            t.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except ValueError:
        return default


def _hired(tenant: str) -> None:
    from ..employee import hire
    if not hire.is_hired(tenant, KEY):
        raise S.SeoError("SEO Specialist abhi hired nahi hai. Employees mein jaakar hire kijiye.")


def _event(tenant: str, sid: str, kind: str, level: str, text: str, data: dict | None = None) -> None:
    with session() as s:
        s.add(SeoEvent(tenant_id=tenant, site_id=sid, kind=kind, level=level, text=text[:600],
                       data=json.dumps(data or {}, ensure_ascii=False)[:20000]))


def _desk(s, tenant: str, site: str = "") -> SeoDesk:
    r = S._site(s, tenant, site)
    d = s.get(SeoDesk, r.id)
    if d is None:
        d = SeoDesk(site_id=r.id, tenant_id=tenant)
        s.add(d)
        s.flush()
    return d


# ---------------------------------------------------------------- onboarding
def onboard(tenant: str, url: str, name: str = "", city: str = "", services: list | None = None, goal: str = "",
            customers: str = "", cities: list | None = None, competitors: list | None = None, trust: str = "seekh",
            weekday: int | None = None, morning_time: str = "", background: bool = True, ask: Any = None) -> dict[str, Any]:
    """The hiring interview, saved: her site + business, what she wants, who she competes with, how much it may do on
    its own, when she wants the note. Then the first full run (in the background in the app)."""
    from ..employee import hire
    _hired(tenant)
    ensure_tables()
    url = (url or "").strip()
    if not url:
        raise S.SeoError("Website ka address chahiye.")
    existing = [x for x in S.sites(tenant) if x["url"].rstrip("/") == url.rstrip("/") or
                urlparse(x["url"]).hostname == urlparse(url if "://" in url else "https://" + url).hostname]
    sid = S.save_site(tenant, url, name, existing[0]["id"] if existing else "", services or None, city=city or None)["site"]["id"]
    comps = [str(c).strip()[:200] for c in (competitors or []) if str(c).strip()][:8]
    with session() as s:
        d = _desk(s, tenant, sid)
        d.goals = json.dumps({"goal": goal[:400], "customers": customers[:400],
                              "cities": [str(c)[:60] for c in (cities or ([city] if city else []))][:10]}, ensure_ascii=False)
        d.competitors = json.dumps(comps, ensure_ascii=False)
        d.state = "first_run"
    hire.save_settings(tenant, KEY, trust=trust, site=sid, onboarded=now().isoformat(timespec="seconds"))
    if weekday is not None or morning_time:
        S.save_settings(tenant, weekday=weekday, morning_time=morning_time or None)
    _event(tenant, sid, "note", "info", "Hired and onboarded. First full check started.")
    if background:
        threading.Thread(target=first_run, args=(tenant, sid), kwargs={"ask": ask}, daemon=True).start()
        return {"site": sid, "state": "first_run", "say": "Shuru kar diya: poori website, speed aur Google ke numbers dekh raha hoon. "
                "Baseline aur 90 din ka plan 10-15 minute mein desk par."}
    return first_run(tenant, sid, ask=ask)


def first_run(tenant: str, sid: str, ask: Any = None) -> dict[str, Any]:
    """The onboarding week in one go: full audit, speed, Search Console, Analytics -> frozen baseline -> roadmap draft."""
    if not _claim(f"{tenant}:{sid}:first"):
        return {"site": sid, "state": "busy"}
    try:
        out: dict[str, Any] = {"site": sid}
        try:
            out["audit"] = S.crawl(tenant, sid, max_pages=200, cap=500)
        except S.SeoError as e:
            out["audit_error"] = str(e)
        latest = _refresh_numbers(tenant, sid, with_speed=True, store=True)
        base = {**latest, "date": S.today(tenant).isoformat()}
        with session() as s:
            d = s.get(SeoDesk, sid)
            d.baseline, d.baseline_at = json.dumps(base, ensure_ascii=False), now().isoformat(timespec="seconds")
            d.latest = json.dumps(latest, ensure_ascii=False)
        rm = build_roadmap(tenant, sid, ask=ask)
        with session() as s:
            s.get(SeoDesk, sid).state = "ready"
        _event(tenant, sid, "run", "ok", f"Baseline saved and a {len(rm['items'])}-step 90-day plan is ready for your OK.",
               {"baseline": base})
        S._publish(tenant, "seo_update", {"site": sid, "score": base.get("score"), "text": "SEO baseline + 90-day plan ready"})
        out.update(baseline=base, roadmap=rm)
        return out
    except Exception as e:      # noqa: BLE001 - the desk says what happened instead of hanging in "first_run"
        log.exception("seo first run failed")
        with session() as s:
            d = s.get(SeoDesk, sid)
            if d:
                d.state = "error"
        _event(tenant, sid, "run", "bad", f"First check stopped: {type(e).__name__}. It will try again in the daily run.")
        return {"site": sid, "state": "error", "error": str(e)[:300]}
    finally:
        _release(f"{tenant}:{sid}:first")


def _claim(key: str) -> bool:
    with _RUN_LOCK:
        if key in _RUNNING:
            return False
        _RUNNING.add(key)
        return True


def _release(key: str) -> None:
    with _RUN_LOCK:
        _RUNNING.discard(key)


# ---------------------------------------------------------------- numbers
def _refresh_numbers(tenant: str, sid: str, with_speed: bool = False, store: bool = False) -> dict[str, Any]:
    """Score + issues from the last crawl, Search Console (28 days, final data), Analytics organic, speed. Missing
    sources stay out (never zeros pretending to be data)."""
    out: dict[str, Any] = {}
    with session() as s:
        site = s.get(S.SeoSite, sid)
        out["score"] = site.score if site else None
        out["pages"] = len(s.scalars(select(S.SeoPage.id).where(S.SeoPage.site_id == sid)).all())
        tasks = s.scalars(select(S.SeoTask).where(S.SeoTask.site_id == sid, S.SeoTask.status == "open")).all()
        out["bad"] = sum(1 for t in tasks if t.level == "bad")
        out["warn"] = sum(1 for t in tasks if t.level == "warn")
    if with_speed:
        try:
            sp = S.pagespeed(tenant, sid)
            out["cwv"] = {"lcp_ms": sp.get("lcp_ms"), "inp_ms": sp.get("inp_ms"), "cls": sp.get("cls"), "lab": sp.get("lab_score"),
                          "field": bool(sp.get("field_data"))}
        except S.SeoError:
            pass
    if S.gsc_status(tenant)["connected"]:
        try:
            p = S.performance(tenant, sid, 28, store=store)   # store: the first / weekly run keeps the snapshot the plan reads
            out["gsc"] = {**p["current"], "start": p["start"], "end": p["end"]}
        except S.SeoError as e:
            out["gsc_error"] = str(e)[:200]
    if S.gsc_status(tenant).get("analytics"):
        try:
            out["ga4"] = ga4_organic(tenant, sid, 28)
        except S.SeoError as e:
            out["ga4_error"] = str(e)[:200]
    return out


def _ga4(tenant: str, method: str, url: str, body: dict | None = None) -> dict:
    c, own = S._client()
    try:
        for force in (False, True):
            h = {"Authorization": f"Bearer {S._token(tenant, force)}"}
            try:
                r = c.request(method, url, headers=h, json=body, timeout=60)
            except httpx.HTTPError as e:
                raise S.SeoError(f"Google Analytics se baat nahi hui ({type(e).__name__}).")
            if r.status_code == 401 and not force:
                continue
            if r.status_code == 403:
                raise S.SeoError("Is Google account ko Analytics dekhne ki permission nahi.")
            if r.status_code >= 400:
                raise S.SeoError(f"Google Analytics: {r.text[:200]}")
            return r.json()
    finally:
        if own:
            c.close()
    raise S.SeoError("Google Analytics login nahi chala.")


def ga4_properties(tenant: str) -> list[dict[str, str]]:
    out = []
    for acc in _ga4(tenant, "GET", f"{GA4_ADMIN}/accountSummaries").get("accountSummaries", []):
        for p in acc.get("propertySummaries", []):
            out.append({"property": p.get("property", ""), "name": p.get("displayName", ""), "account": acc.get("displayName", "")})
    return out


def _ga4_property(tenant: str, sid: str) -> str:
    """The Analytics property whose web stream is her site (picked once, kept on the desk)."""
    with session() as s:
        d = s.get(SeoDesk, sid)
        if d and d.ga4_property:
            return d.ga4_property
        site = s.get(S.SeoSite, sid)
        host = (urlparse(site.url).hostname or "").removeprefix("www.") if site else ""
    pick = ""
    for p in ga4_properties(tenant)[:20]:
        try:
            streams = _ga4(tenant, "GET", f"{GA4_ADMIN}/{p['property']}/dataStreams").get("dataStreams", [])
        except S.SeoError:
            continue
        for st in streams:
            uri = (st.get("webStreamData") or {}).get("defaultUri", "")
            if host and (urlparse(uri if "://" in uri else "https://" + uri).hostname or "").removeprefix("www.") == host:
                pick = p["property"]
                break
        if pick:
            break
    if not pick:
        raise S.SeoError("Google Analytics mein is website ka property nahi mila.")
    with session() as s:
        d = s.get(SeoDesk, sid)
        if d:
            d.ga4_property = pick
    return pick


def ga4_organic(tenant: str, sid: str, days: int = 28) -> dict[str, Any]:
    """Organic Search sessions + key events (leads / orders she marked in Analytics), same final window as Search Console."""
    prop = _ga4_property(tenant, sid)
    end = S.today(tenant) - timedelta(days=3)
    start = end - timedelta(days=max(7, min(int(days), 90)) - 1)
    body = {"dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
            "dimensions": [{"name": "sessionDefaultChannelGroup"}], "metrics": [{"name": "sessions"}, {"name": "keyEvents"}]}
    rows = _ga4(tenant, "POST", f"{GA4_DATA}/{prop}:runReport", body).get("rows", [])
    sessions = leads = 0
    total = 0
    for r in rows:
        ch = ((r.get("dimensionValues") or [{}])[0].get("value") or "")
        mv = [float(x.get("value") or 0) for x in (r.get("metricValues") or [])] + [0, 0]
        total += int(mv[0])
        if ch.lower() == "organic search":
            sessions, leads = int(mv[0]), int(mv[1])
    return {"property": prop, "organic_sessions": sessions, "leads": leads, "all_sessions": total,
            "start": start.isoformat(), "end": end.isoformat()}


# ---------------------------------------------------------------- roadmap
PLAN_SYSTEM = """You are a senior SEO strategist at a world-class agency, writing the 90-day plan for one Indian small
business from its REAL audit and Search Console data. Work in the order agencies use: fix what blocks Google first
(technical), then the pages that already almost rank (striking distance, low CTR), then content gaps for the services
and cities she named, then local (Google Business Profile, reviews), then authority (real local links / PR, never bought
links), then AI-search visibility (answer-first pages, FAQs, consistent business facts). Never plan: buying links, fake
reviews, doorway or mass AI pages, keyword stuffing, promising rankings. Each item is one concrete piece of work a
person can check as done. 10-18 items over 13 weeks, most impact first."""

PLAN_FIELDS = ('Reply JSON: {"items": [{"week": 1-13, "workstream": one of ' + json.dumps(list(WORKSTREAMS)) +
               ', "title": "short task", "why": "one line, with the real number or page from the data", '
               '"impact": 1-3, "effort": 1-3, "owner": "hoola" or "her"}]}')


def _plan_inputs(tenant: str, sid: str) -> dict[str, Any]:
    with session() as s:
        site = s.get(S.SeoSite, sid)
        d = s.get(SeoDesk, sid)
        tasks = s.scalars(select(S.SeoTask).where(S.SeoTask.site_id == sid, S.SeoTask.status == "open")).all()
        last = s.scalars(select(S.SeoStat).where(S.SeoStat.site_id == sid).order_by(S.SeoStat.end.desc())).first()
        codes: dict[str, dict] = {}
        for t in tasks:
            c = codes.setdefault(t.code, {"code": t.code, "level": t.level, "count": 0, "example": t.url, "text": t.text})
            c["count"] += 1
        rows = _j(last.rows, []) if last else []
        biz = _j(site.business, {}) if site else {}
        return {"site": site.url if site else "", "name": site.name if site else "", "city": biz.get("city", ""),
                "services": _j(site.services, []) if site else [], "goals": _j(d.goals, {}) if d else {},
                "competitors": _j(d.competitors, []) if d else [], "score": site.score if site else None,
                "issues": sorted(codes.values(), key=lambda c: ({"bad": 0, "warn": 1, "info": 2}.get(c["level"], 3), -c["count"]))[:20],
                "opportunities": [o for o in ({**(R.opportunity(q) or {}), "query": q.get("query"), "page": q.get("page"),
                                               "position": q.get("position")} for q in rows[:200]) if o.get("do")][:12],
                "baseline": _j(d.baseline, {}) if d else {}}


def _rules_roadmap(inp: dict[str, Any]) -> list[dict[str, Any]]:
    """The plan without a model: issues by severity first, then opportunities, then the standing local / content /
    reporting work every agency does."""
    items: list[dict[str, Any]] = []
    week = 1
    for c in inp["issues"][:8]:
        items.append({"week": week, "workstream": "technical" if c["code"] not in ("thin", "title_short", "title_long", "title_missing",
                                                                                   "desc_missing", "desc_len", "h1_missing", "city", "dup_title",
                                                                                   "dup_desc") else "content",
                      "title": f"Fix: {c['text'][:110]}" + (f" ({c['count']} pages)" if c["count"] > 1 else ""),
                      "why": f"Found in the audit on {c['example']}.", "impact": 3 if c["level"] == "bad" else 2,
                      "effort": 1 if c["count"] <= 3 else 2, "owner": "her"})
        week = min(13, week + (1 if len(items) % 2 == 0 else 0))
    for o in inp["opportunities"][:4]:
        items.append({"week": min(13, week + 1), "workstream": "content", "title": f"Lift '{o['query']}' (position {o.get('position')})"[:150],
                      "why": o.get("do", "")[:240], "impact": 3, "effort": 2, "owner": "hoola"})
    city = inp.get("city") or "your city"
    items += [
        {"week": 3, "workstream": "local", "title": "Complete the Google Business Profile (categories, services, hours, photos)",
         "why": f"Local searches in {city} decide most calls.", "impact": 3, "effort": 1, "owner": "her"},
        {"week": 5, "workstream": "content", "title": "One strong page for each main service + city",
         "why": f"Services: {', '.join(inp.get('services') or [])[:150] or 'from your list'}.", "impact": 3, "effort": 3, "owner": "hoola"},
        {"week": 7, "workstream": "ai_search", "title": "FAQ answers on the main pages (answer first, with real facts)",
         "why": "Google AI answers and ChatGPT quote pages that answer clearly.", "impact": 2, "effort": 2, "owner": "hoola"},
        {"week": 9, "workstream": "authority", "title": "Get listed by 5 real local partners / associations / directories",
         "why": "Real local links and citations, never bought links.", "impact": 2, "effort": 2, "owner": "her"},
        {"week": 13, "workstream": "reporting", "title": "90-day review against the baseline and the next plan",
         "why": "Measure what worked before planning more.", "impact": 2, "effort": 1, "owner": "hoola"},
    ]
    return items


def _clean_items(raw: Any) -> list[dict[str, Any]]:
    out = []
    for it in (raw or [])[:24]:
        if not isinstance(it, dict) or not str(it.get("title") or "").strip():
            continue
        ws = str(it.get("workstream") or "").lower().replace(" ", "_")
        try:
            week = max(1, min(13, int(it.get("week") or 1)))
            impact = max(1, min(3, int(it.get("impact") or 2)))
            effort = max(1, min(3, int(it.get("effort") or 2)))
        except (TypeError, ValueError):
            week, impact, effort = 1, 2, 2
        out.append({"week": week, "workstream": ws if ws in WORKSTREAMS else "technical",
                    "title": str(it["title"]).strip()[:150], "why": str(it.get("why") or "").strip()[:300],
                    "impact": impact, "effort": effort, "owner": "her" if str(it.get("owner")).lower() == "her" else "hoola"})
    return out


def build_roadmap(tenant: str, sid: str, ask: Any = None) -> dict[str, Any]:
    """Opus writes the 90-day plan from the real audit; the rules plan when Opus is off / slow / says nothing usable.
    A new plan replaces the old DRAFT only - approved work and its statuses are never thrown away."""
    from ..config import get_settings
    inp = _plan_inputs(tenant, sid)
    items, source = [], "rules"
    st = get_settings()
    if ask is not None or (getattr(st, "seo_ai", True) and st.anthropic_api_key):
        try:
            from ..docstudio.htmlpdf import _ask_opus
            got = (ask or _ask_opus)(PLAN_SYSTEM, json.dumps(inp, ensure_ascii=False)[:9000] + "\n\n" + PLAN_FIELDS,
                                     "seo_plan", None, 90.0, max_tokens=4000) or {}
            items = _clean_items(got.get("items"))
            if len(items) >= 4:
                source = "opus"
            else:
                items = []
        except Exception as e:   # noqa: BLE001
            log.info("seo roadmap model skipped: %s", e)
            items = []
    if not items:
        items = _clean_items(_rules_roadmap(inp))
    with session() as s:
        for old in s.scalars(select(SeoRoadmapItem).where(SeoRoadmapItem.site_id == sid, SeoRoadmapItem.status == "planned")).all():
            s.delete(old)
        for it in sorted(items, key=lambda x: (x["week"], -x["impact"])):
            s.add(SeoRoadmapItem(tenant_id=tenant, site_id=sid, source=source, **it))
        d = s.get(SeoDesk, sid)
        if d and d.roadmap_status != "approved":
            d.roadmap_status = "draft"
    return {"items": items, "source": source}


def approve_roadmap(tenant: str, site: str = "") -> dict[str, Any]:
    _hired(tenant)
    with session() as s:
        d = _desk(s, tenant, site)
        d.roadmap_status = "approved"
        sid = d.site_id
    _event(tenant, sid, "note", "ok", "You approved the 90-day plan.")
    return {"roadmap_status": "approved"}


def set_item(tenant: str, item_id: str, status: str) -> dict[str, Any]:
    if status not in BOARD:
        raise S.SeoError("status: " + " | ".join(BOARD))
    with session() as s:
        it = s.get(SeoRoadmapItem, item_id)
        if it is None or it.tenant_id != tenant:
            raise S.SeoError("Yeh kaam nahi mila.")
        it.status = status
        return {"id": it.id, "status": it.status}


def roadmap(tenant: str, site: str = "") -> list[dict[str, Any]]:
    with session() as s:
        sid = S._site(s, tenant, site).id
        return [{"id": r.id, "week": r.week, "workstream": r.workstream, "title": r.title, "why": r.why, "impact": r.impact,
                 "effort": r.effort, "owner": r.owner, "status": r.status, "source": r.source}
                for r in s.scalars(select(SeoRoadmapItem).where(SeoRoadmapItem.site_id == sid)
                                   .order_by(SeoRoadmapItem.week, SeoRoadmapItem.impact.desc())).all()]


# ---------------------------------------------------------------- the desk
def _kpi(name: str, now_v: Any, base_v: Any, better: str = "up") -> dict[str, Any]:
    ch = None
    if isinstance(now_v, (int, float)) and isinstance(base_v, (int, float)) and base_v:
        ch = round((now_v - base_v) * 100 / abs(base_v))
    good = None if ch is None else (ch >= 0 if better == "up" else ch <= 0)
    return {"name": name, "now": now_v, "baseline": base_v, "change_pct": ch, "good": good}


def kpis(base: dict[str, Any], latest: dict[str, Any]) -> list[dict[str, Any]]:
    g, gb = latest.get("gsc") or {}, base.get("gsc") or {}
    a, ab = latest.get("ga4") or {}, base.get("ga4") or {}
    c, cb = latest.get("cwv") or {}, base.get("cwv") or {}
    out = [_kpi("SEO score", latest.get("score"), base.get("score")),
           _kpi("Urgent issues", latest.get("bad"), base.get("bad"), "down")]
    if g or gb:
        out += [_kpi("Clicks from Google (28 days)", g.get("clicks"), gb.get("clicks")),
                _kpi("Times shown on Google", g.get("impressions"), gb.get("impressions")),
                _kpi("Average position", g.get("position"), gb.get("position"), "down")]
    if a or ab:
        out += [_kpi("Visits from Google (Analytics)", a.get("organic_sessions"), ab.get("organic_sessions")),
                _kpi("Leads / orders from Google", a.get("leads"), ab.get("leads"))]
    if c or cb:
        out.append(_kpi("Load time on mobile (LCP ms)", c.get("lcp_ms"), cb.get("lcp_ms"), "down"))
    return out


def desk_view(tenant: str, site: str = "") -> dict[str, Any]:
    from ..employee import hire
    ensure_tables()
    st = hire.status(tenant, KEY)
    if st not in ("hired", "paused"):
        return {"hired": False, "status": st}
    sites = S.sites(tenant)
    trust = next((c.get("trust") for c in hire.catalog(tenant) if c["key"] == KEY), "seekh")
    if not sites:
        return {"hired": True, "status": st, "onboarded": False, "trust": trust, "google": S.gsc_status(tenant)}
    with session() as s:
        d = _desk(s, tenant, site)
        sid = d.site_id
        base, latest = _j(d.baseline, {}), _j(d.latest, {})
        info = {"state": d.state, "roadmap_status": d.roadmap_status, "baseline_at": d.baseline_at,
                "goals": _j(d.goals, {}), "competitors": _j(d.competitors, []), "ga4_property": d.ga4_property,
                "stamps": _j(d.stamps, {}), "watch": _j(d.watch, {})}
        events = [{"kind": e.kind, "level": e.level, "text": e.text, "at": e.at.isoformat() if e.at else ""}
                  for e in s.scalars(select(SeoEvent).where(SeoEvent.site_id == sid).order_by(SeoEvent.at.desc())).all()[:25]]
    rm = roadmap(tenant, sid)
    board = {k: [x for x in rm if x["status"] == k] for k in BOARD}
    view = next((x for x in sites if x["id"] == sid), sites[0])
    return {"hired": True, "status": st, "onboarded": True, "trust": trust, "site": view, "sites": sites, **info,
            "baseline": base, "latest": latest, "kpis": kpis(base, latest), "board": board, "roadmap_count": len(rm),
            "events": events, "google": S.gsc_status(tenant), "open_tasks": S.tasks(tenant, sid, "open")[:30],
            "schedule": schedule_view(tenant, info["stamps"])}


def schedule_view(tenant: str, stamps: dict[str, str]) -> list[dict[str, str]]:
    st = S.settings(tenant)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return [{"job": "Watch: site up, Google not blocked", "every": "Every hour", "last": stamps.get("hourly", "")},
            {"job": "Google numbers (Search Console, Analytics)", "every": "Every day, 6 am", "last": stamps.get("daily", "")},
            {"job": "Full website check + speed", "every": f"Every {days[st['weekday']]}", "last": stamps.get("weekly", "")},
            {"job": "Weekly note in chat", "every": f"{days[st['weekday']]} {st['morning_time']}", "last": ""},
            {"job": "Monthly report (PDF)", "every": "1st of every month", "last": stamps.get("monthly", "")}]


# ---------------------------------------------------------------- 24/7 jobs
def watch(tenant: str, sid: str) -> dict[str, Any]:
    """Hourly: is the site up, is Google allowed in, is the home page indexable, is the sitemap there. Alerts only on a
    CHANGE to bad (and says when it recovers), so a long outage is one alert, not 24."""
    with session() as s:
        site = s.get(S.SeoSite, sid)
        home = site.url if site else ""
        prev = _j(s.get(SeoDesk, sid).watch, {}) if s.get(SeoDesk, sid) else {}
    state: dict[str, Any] = {"at": now().isoformat(timespec="seconds")}
    try:
        status, _final, html, _size = S._fetch(home, 2_000_000)
        state["up"] = status < 400
        state["status"] = status
        d, _links = S._parse(home, status, html, len(html), home)
        state["noindex"] = bool(d.get("noindex"))
    except S.SeoError as e:
        state.update(up=False, status=599, error=str(e)[:200], noindex=False)
    robots = ""
    try:
        rs, _f, robots, _s = S._fetch(urljoin(home, "/robots.txt"), 200_000)
        robots = robots if rs < 400 else ""
    except S.SeoError:
        robots = ""
    state["robots_block"] = any(i["code"] == "robots_block" for i in R.site_issues([], robots, True))
    try:
        ss, _f, xml, _s = S._fetch(urljoin(home, "/sitemap.xml"), 3_000_000)
        state["sitemap"] = ss < 400 and "<loc>" in xml
    except S.SeoError:
        state["sitemap"] = False
    checks = [("up", False, "Website khul nahi rahi (HTTP {status}).", "Website phir khul gayi."),
              ("robots_block", True, "robots.txt ab poori site ko Google se rok raha hai (Disallow: /).", "robots.txt ab Google ko rok nahi raha."),
              ("noindex", True, "Home page par noindex lag gaya: Google ise hata dega.", "Home page se noindex hat gaya.")]
    alerts = []
    for key, bad_value, bad_text, ok_text in checks:
        now_bad = state.get(key) == bad_value
        was_bad = prev.get(key) == bad_value if key in prev else False
        if now_bad and not was_bad:
            text = bad_text.format(status=state.get("status"))
            alerts.append(text)
            _event(tenant, sid, "alert", "bad", text, {"check": key})
            S._publish(tenant, "seo_alert", {"site": sid, "text": text})
        elif was_bad and not now_bad:
            _event(tenant, sid, "recovered", "ok", ok_text, {"check": key})
    if prev.get("sitemap") and not state["sitemap"]:
        alerts.append("sitemap.xml ab nahi mil raha.")
        _event(tenant, sid, "alert", "warn", "sitemap.xml ab nahi mil raha.", {"check": "sitemap"})
    with session() as s:
        d = s.get(SeoDesk, sid)
        if d:
            d.watch = json.dumps(state, ensure_ascii=False)
    return {"state": state, "alerts": alerts}


def daily(tenant: str, sid: str) -> dict[str, Any]:
    latest = _refresh_numbers(tenant, sid, with_speed=False)
    with session() as s:
        d = s.get(SeoDesk, sid)
        old = _j(d.latest, {}) if d else {}
        keep = {k: v for k, v in old.items() if k == "cwv"}     # speed is refreshed weekly
        if d:
            d.latest = json.dumps({**keep, **latest}, ensure_ascii=False)
            base_missing = not _j(d.baseline, {}).get("gsc") and latest.get("gsc")
            if base_missing:      # Search Console connected after hiring: its numbers join the baseline once
                b = _j(d.baseline, {})
                b["gsc"] = latest["gsc"]
                if latest.get("ga4") and not b.get("ga4"):
                    b["ga4"] = latest["ga4"]
                d.baseline = json.dumps(b, ensure_ascii=False)
    return latest


def weekly(tenant: str, sid: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        out["audit"] = S.crawl(tenant, sid, max_pages=int(_hire_setting(tenant, "max_pages") or 200), cap=500)
    except S.SeoError as e:
        out["audit_error"] = str(e)
    latest = _refresh_numbers(tenant, sid, with_speed=True, store=True)   # the weekly snapshot = the report's trend line
    with session() as s:
        d = s.get(SeoDesk, sid)
        if d:
            d.latest = json.dumps(latest, ensure_ascii=False)
    a = out.get("audit") or {}
    _event(tenant, sid, "run", "info", f"Weekly check: {a.get('pages', 0)} pages, score {a.get('score')}, "
           f"{a.get('new', 0)} new issues, {a.get('fixed', 0)} fixed.")
    return out


def _hire_setting(tenant: str, k: str) -> Any:
    from ..employee import hire
    return hire.settings(tenant, KEY).get(k)


# ---------------------------------------------------------------- the monthly report
def report_markdown(tenant: str, sid: str) -> tuple[str, str]:
    """The monthly report as Hoola Print content: Key takeaways, numbers against the baseline, the trend chart, the
    work done and open, the plan for next month."""
    with session() as s:
        site = s.get(S.SeoSite, sid)
        d = s.get(SeoDesk, sid)
        stats = s.scalars(select(S.SeoStat).where(S.SeoStat.site_id == sid).order_by(S.SeoStat.end)).all()[-12:]
        last = stats[-1] if stats else None
        rows = _j(last.rows, []) if last else []
        base, latest = _j(d.baseline, {}), _j(d.latest, {})
        name = site.name or site.url
        stat_rows = [(x.end, x.clicks, x.impressions) for x in stats]
    rm = roadmap(tenant, sid)
    done = [x for x in rm if x["status"] == "done"]
    open_ = [x for x in rm if x["status"] in ("planned", "doing", "waiting_her")]
    k = kpis(base, latest)
    month = S.today(tenant).strftime("%B %Y")
    title = f"{name} — SEO report, {month}"

    def fmt(v):
        if v is None:
            return "–"
        if isinstance(v, float):
            return f"{v:,.1f}"
        return f"{v:,}" if isinstance(v, int) else str(v)
    lines = ["# Summary"]
    take = []
    for x in k:
        if x["change_pct"] is not None:
            take.append(f"{x['name']}: {fmt(x['now'])} ({'+' if x['change_pct'] >= 0 else ''}{x['change_pct']}% since you hired the SEO "
                        "Specialist)")
    take.append(f"{len(done)} planned tasks done, {len(open_)} in the plan.")
    lines.append("> [!KEY] " + take[0])
    for t in take[1:5]:
        lines.append("> " + t)
    lines.append("")
    stat_items = [x for x in k if x["now"] is not None][:4]
    for x in stat_items:
        lines.append(f"[stat: {fmt(x['now'])} | {x['name']}]")
    lines.append("# Where things stand against the baseline")
    lines.append(f"Baseline taken on {base.get('date', '–')}. Search Console data ends three days before today; that is Google's own delay.")
    lines.append("| Measure | Baseline | Now | Change |")
    lines.append("|---|---|---|---|")
    for x in k:
        ch = "–" if x["change_pct"] is None else f"{'+' if x['change_pct'] >= 0 else ''}{x['change_pct']}%"
        lines.append(f"| {x['name']} | {fmt(x['baseline'])} | {fmt(x['now'])} | {ch} |")
    if len(stat_rows) >= 2:
        lines.append("# Clicks from Google, week by week")
        lines.append("[chart: line | Clicks from Google (28-day totals)]")
        lines.append("| Period ending | Clicks |")
        lines.append("|---|---|")
        for end, clicks, _imp in stat_rows:
            lines.append(f"| {end[5:]} | {clicks} |")
        lines.append("Source: Google Search Console")
    if rows:
        lines.append("# The searches that bring people")
        lines.append("Table: Top searches, last 28 days")
        lines.append("| Search | Clicks | Shown | Position |")
        lines.append("|---|---|---|---|")
        for q in rows[:10]:
            lines.append(f"| {str(q.get('query', ''))[:60]} | {q.get('clicks', 0)} | {q.get('impressions', 0)} | {q.get('position', 0)} |")
        lines.append("Source: Google Search Console")
    lines.append("# Work done this period")
    if done:
        for x in done[:15]:
            lines.append(f"- {x['title']}")
    else:
        lines.append("No plan items marked done yet.")
    lines.append("# Next month")
    for x in open_[:8]:
        lines.append(f"1. {x['title']} — {x['why'][:120]}")
    tasks = S.tasks(tenant, sid, "open")
    if tasks:
        lines.append("# Open fixes on the website")
        lines.append("| Level | Page | Problem |")
        lines.append("|---|---|---|")
        for t in tasks[:15]:
            lines.append(f"| {t['level']} | {t['url'][-60:]} | {t['text'][:90]} |")
    return title, "\n".join(lines)


def monthly_report(tenant: str, sid: str, conv: str = "") -> dict[str, Any]:
    from .. import chatfiles
    from ..agent.docstudio_tools import make_pdf
    title, text = report_markdown(tenant, sid)
    with session() as s:
        site = s.get(S.SeoSite, sid)
        who = site.name or (urlparse(site.url).hostname or "")
    res = make_pdf(title, text, {"style": "auto", "subject": "Monthly SEO report", "cover": "auto", "toc": "auto"},
                   "Hoola SEO Specialist", who)
    f = chatfiles.store(tenant, f"SEO_report_{S.today(tenant).strftime('%Y_%m')}.pdf", res["data"], "application/pdf")
    S._publish(tenant, "pc_file", {**f, "source": "seo", "title": title}, conv)
    _event(tenant, sid, "report", "ok", f"Monthly report ready: {title}", {"file": f.get("id") or f.get("file_id") or ""})
    return {"file": f, "title": title, "pages": res.get("pages")}


# ---------------------------------------------------------------- the scheduler
def due_jobs(tenant: str, sid: str, at: datetime | None = None) -> list[str]:
    """Which jobs are due now for this site (her local time): hourly / daily (after 6 am) / weekly (her weekday) /
    monthly (the 1st)."""
    from ..life import tz_of
    local = (at or datetime.now(tz_of(tenant))).astimezone(tz_of(tenant))
    with session() as s:
        d = s.get(SeoDesk, sid)
        stamps = _j(d.stamps, {}) if d else {}
        state = d.state if d else "new"
    out = []
    last_h = stamps.get("hourly", "")
    if not last_h or local - datetime.fromisoformat(last_h) >= timedelta(minutes=55):
        out.append("hourly")
    if local.hour >= 6 and stamps.get("daily", "")[:10] != local.date().isoformat():
        out.append("daily")
    wk = f"{local.isocalendar()[0]}-W{local.isocalendar()[1]}"
    if local.weekday() == S.settings(tenant)["weekday"] and local.hour >= 5 and stamps.get("weekly_key") != wk:
        out.append("weekly")
    mk = local.strftime("%Y-%m")
    if local.day == 1 and local.hour >= 7 and stamps.get("monthly_key") != mk and state == "ready":
        out.append("monthly")
    if state in ("new", "error"):
        out.append("first")
    return out


def run_job(tenant: str, sid: str, job: str, at: datetime | None = None) -> dict[str, Any]:
    from ..life import tz_of
    local = (at or datetime.now(tz_of(tenant))).astimezone(tz_of(tenant))
    if job == "first":
        res = first_run(tenant, sid)
    elif job == "hourly":
        res = watch(tenant, sid)
    elif job == "daily":
        res = daily(tenant, sid)
    elif job == "weekly":
        res = weekly(tenant, sid)
    elif job == "monthly":
        res = monthly_report(tenant, sid)
    else:
        raise S.SeoError("job: first | hourly | daily | weekly | monthly")
    with session() as s:
        d = s.get(SeoDesk, sid)
        if d:
            st = _j(d.stamps, {})
            st[job] = local.isoformat(timespec="seconds")
            if job == "weekly":
                st["weekly_key"] = f"{local.isocalendar()[0]}-W{local.isocalendar()[1]}"
            if job == "monthly":
                st["monthly_key"] = local.strftime("%Y-%m")
            d.stamps = json.dumps(st)
    return res


def run_due(at: datetime | None = None, force: bool = False) -> list[tuple[str, str, str]]:
    """The 24/7 loop, called by the worker. Walks every tenant whose SEO employee is hired (not paused, not let go), every
    onboarded site, every due job. One job failing never stops the rest; it is written on the desk."""
    import time as _t
    if not force and _t.time() - _LAST_SWEEP["at"] < 240:
        return []
    _LAST_SWEEP["at"] = _t.time()
    from ..employee import hire
    ensure_tables()
    done: list[tuple[str, str, str]] = []
    for tenant in hire.working_tenants(KEY):
        with session() as s:
            sids = [d.site_id for d in s.scalars(select(SeoDesk).where(SeoDesk.tenant_id == tenant)).all()]
        for sid in sids:
            for job in due_jobs(tenant, sid, at):
                key = f"{tenant}:{sid}:{job}"
                if not _claim(key):
                    continue
                try:
                    run_job(tenant, sid, job, at)
                    done.append((tenant, sid, job))
                except Exception as e:   # noqa: BLE001
                    log.exception("seo job %s failed", job)
                    _event(tenant, sid, "run", "bad", f"{job} run stopped: {str(e)[:200]}")
                finally:
                    _release(key)
    return done
