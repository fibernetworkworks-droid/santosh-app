"""v0.124 Website care: what happens after launch. Visits counted by the server that hosts the site (page views per day and
per page; no cookies, no IP kept, no third-party tracker), uptime samples from the 5-minute checks, enquiries this month vs
last, SSL days left, domain expiry, built-but-not-live changes, facts that changed since the site was built (phone / address
in her brand kit), the last check report -> a monthly care note (`site_care` card on the 1st) and `report` on demand.

Agency: sites grouped by client (`clients`), a staff member works only on the sites given to them (`staff_ok`), a client
summary (`client_report`)."""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from .models import Site, SiteLead, SiteVersion

log = logging.getLogger("santosh.site")
IST = timezone(timedelta(hours=5, minutes=30))


class SiteCareDay(Base):
    __tablename__ = "site_care_days"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("scd"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)               # IST yyyy-mm-dd
    views: Mapped[int] = mapped_column(Integer, default=0)
    pages: Mapped[str] = mapped_column(Text, default="{}")                 # path -> views
    missing: Mapped[int] = mapped_column(Integer, default=0)               # 404s (broken links somewhere)
    up: Mapped[int] = mapped_column(Integer, default=0)                    # uptime checks ok
    down: Mapped[int] = mapped_column(Integer, default=0)


class SiteCareNote(Base):
    __tablename__ = "site_care_notes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("scn"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    month: Mapped[str] = mapped_column(String(7))                          # yyyy-mm the note covered
    body: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_BUF: dict[tuple[str, str, str], dict[str, Any]] = {}
_LOCK = threading.Lock()
_LAST = {"at": time.time()}


def _day(t: datetime | None = None) -> str:
    return (t or datetime.now(timezone.utc)).astimezone(IST).strftime("%Y-%m-%d")


def _slot(site: str, tenant: str) -> dict[str, Any]:
    k = (site, tenant, _day())
    if k not in _BUF:
        _BUF[k] = {"views": 0, "pages": {}, "missing": 0, "up": 0, "down": 0}
    return _BUF[k]


def count_view(site: str, tenant: str, path: str, status: int) -> None:
    """Called by hosting.serve for HTML answers only. Nothing about the visitor is kept."""
    if not site:
        return
    p = (path or "/").split("?")[0][:120] or "/"
    with _LOCK:
        b = _slot(site, tenant)
        if status == 404:
            b["missing"] += 1
        else:
            b["views"] += 1
            if len(b["pages"]) < 200 or p in b["pages"]:
                b["pages"][p] = b["pages"].get(p, 0) + 1
    if time.time() - _LAST["at"] > 60 or len(_BUF) > 200:
        flush()


def count_check(site: str, tenant: str, ok: bool) -> None:
    with _LOCK:
        _slot(site, tenant)["up" if ok else "down"] += 1


def flush() -> None:
    with _LOCK:
        items = list(_BUF.items())
        _BUF.clear()
        _LAST["at"] = time.time()
    if not items:
        return
    try:
        with session() as s:
            for (site, tenant, day), b in items:
                row = s.scalars(select(SiteCareDay).where(SiteCareDay.site_id == site, SiteCareDay.day == day)).first()
                if row is None:
                    row = SiteCareDay(site_id=site, tenant_id=tenant, day=day)
                    s.add(row)
                    s.flush()
                row.views = (row.views or 0) + b["views"]
                row.missing = (row.missing or 0) + b["missing"]
                row.up = (row.up or 0) + b["up"]
                row.down = (row.down or 0) + b["down"]
                pages = json.loads(row.pages or "{}")
                for p, n in b["pages"].items():
                    pages[p] = pages.get(p, 0) + n
                row.pages = json.dumps(dict(sorted(pages.items(), key=lambda x: -x[1])[:60]))
    except Exception:
        log.exception("care flush failed")


# ---------------------------------------------------------------- the report
def _period(days: int, end: datetime | None = None) -> tuple[str, str]:
    e = (end or datetime.now(timezone.utc)).astimezone(IST)
    return (e - timedelta(days=days - 1)).strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")


def _days(s, site: str, a: str, b: str) -> list[SiteCareDay]:
    return s.scalars(select(SiteCareDay).where(SiteCareDay.site_id == site, SiteCareDay.day >= a, SiteCareDay.day <= b)
                     .order_by(SiteCareDay.day)).all()


def _leads(s, site: str, a: str, b: str) -> int:
    lo = datetime.strptime(a, "%Y-%m-%d").replace(tzinfo=IST).astimezone(timezone.utc)
    hi = (datetime.strptime(b, "%Y-%m-%d").replace(tzinfo=IST) + timedelta(days=1)).astimezone(timezone.utc)
    return int(s.scalar(select(func.count()).select_from(SiteLead).where(
        SiteLead.site_id == site, SiteLead.status != "spam", SiteLead.created_at >= lo, SiteLead.created_at < hi)) or 0)


def _drift(r: Site) -> list[str]:
    """Facts that changed in her own profile since the site was built (she decides; nothing is changed by itself)."""
    from . import service as S
    out = []
    try:
        now_f = S.gather_facts(r.tenant_id, "")
    except Exception:
        return out
    was = json.loads(r.facts or "{}")
    for k, label in (("phone", "phone"), ("whatsapp", "WhatsApp"), ("address", "pata"), ("email", "email")):
        a, b = str(was.get(k) or "").strip(), str(now_f.get(k) or "").strip()
        if a and b and a != b:
            out.append(f"Website par {label} '{a}' hai, aapke profile mein ab '{b}'. Badalna ho to 'website mein naya {label}' kahiye.")
    return out


def report(tenant: str, ref: str = "", days: int = 30) -> dict[str, Any]:
    from . import hosting as H
    from . import service as S
    flush()
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
        a, b = _period(days)
        pa, pb = _period(days, datetime.now(timezone.utc) - timedelta(days=days))
        cur, prev = _days(s, r.id, a, b), _days(s, r.id, pa, pb)
        leads, leads_prev = _leads(s, r.id, a, b), _leads(s, r.id, pa, pb)
    views = sum(x.views for x in cur)
    views_prev = sum(x.views for x in prev)
    up, down = sum(x.up for x in cur), sum(x.down for x in cur)
    pages: dict[str, int] = {}
    for x in cur:
        for p, n in json.loads(x.pages or "{}").items():
            pages[p] = pages.get(p, 0) + n
    hosts = [h for h in H._hosts_of(r) if h.status in ("active", "pending")]
    live_v = max((h.live_version for h in hosts), default=0)
    ssl = {}
    for h in hosts:
        if h.status == "active" and h.role == "main":
            d = H.ssl_days(h.hostname)
            if d is not None:
                ssl[h.hostname] = d
    doms = []
    try:
        from .domains import domains as _doms
        doms = [d for d in _doms(tenant) if d["status"] in ("registered", "kyc") and d.get("expires_at")]
    except Exception:
        pass
    chk = json.loads(r.checks or "{}")
    tips: list[str] = []
    if not hosts:
        tips.append("Website abhi live nahi; 'website live karo' kahiye.")
    if live_v and r.version > live_v:
        tips.append(f"v{r.version} bana hua hai par live v{live_v} hai; naya live karne ke liye card bhejun?")
    if up + down and down / (up + down) > 0.02:
        tips.append(f"Is mahine {down} baar site nahi khuli; hosting / DNS dekhna chahiye.")
    if sum(x.missing for x in cur) > 20:
        tips.append("Kai log aisi pages khol rahe hain jo nahi hain (purane link?); 'purane link ki page bana do' kaha ja sakta hai.")
    for host, d in ssl.items():
        if d < 15:
            tips.append(f"{host} ka SSL {d} din mein khatam; Cloudflare apne aap naya karta hai, na hua to Hoola batayega.")
    for d in doms:
        try:
            left = (datetime.fromisoformat(d["expires_at"]) - datetime.now(timezone.utc)).days
        except ValueError:
            continue
        if left < 45:
            tips.append(f"{d['domain']} {left} din mein khatam; renew ₹{d['renew_inr']:,.0f}.")
    if views and leads == 0 and views > 200:
        tips.append("Log aa rahe hain par enquiry nahi; contact / WhatsApp button upar laane ka badlav bolun?")
    if views_prev and views < 0.6 * views_prev:
        tips.append("Pichhle mahine se visit kaafi kam; SEO sahayak se jaanch karwa sakte hain.")
    tips += _drift(r)
    if chk.get("blocking"):
        tips.append(f"Pichhli jaanch mein {len(chk['blocking'])} zaroori kami thi; 'website theek karo' kahiye.")
    conv = round(100 * leads / views, 1) if views else 0.0
    say = (f"{r.name}: {days} din mein {views} visit"
           + (f" ({'+' if views >= views_prev else ''}{views - views_prev} pichhle se)" if views_prev else "")
           + f", {leads} enquiry" + (f" ({conv}%)" if views else "")
           + (f", uptime {round(100 * up / (up + down), 1)}%" if up + down else "") + ".")
    return {"site": S.view(r, False), "days": days, "views": views, "views_prev": views_prev, "leads": leads,
            "leads_prev": leads_prev, "conversion_pct": conv,
            "uptime_pct": round(100 * up / (up + down), 2) if up + down else None, "down_checks": down,
            "missing_hits": sum(x.missing for x in cur), "daily": [{"day": x.day, "views": x.views} for x in cur],
            "top_pages": sorted(pages.items(), key=lambda x: -x[1])[:8], "live_version": live_v, "version": r.version,
            "ssl_days": ssl, "domains": doms, "scores": json.loads(r.scores or "{}"), "tips": tips[:8], "say": say}


def monthly(at: datetime | None = None) -> int:
    """Worker: on the 1st (IST, after 9 am) one care note per live site for the month that just ended."""
    t = (at or datetime.now(timezone.utc)).astimezone(IST)
    if t.day != 1 or t.hour < 9:
        return 0
    from . import hosting as H
    from . import service as S
    month = (t.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    n = 0
    with session() as s:
        live = {h.site_id for h in s.scalars(select(H.SiteHost).where(H.SiteHost.status == "active")).all()}
        done = {x.site_id for x in s.scalars(select(SiteCareNote).where(SiteCareNote.month == month)).all()}
        rows = [r for r in s.scalars(select(Site).where(Site.id.in_(live - done))).all()]
        for r in rows:
            s.expunge(r)
    for r in rows:
        try:
            rep = report(r.tenant_id, r.id, 30)
            with session() as s:
                s.add(SiteCareNote(site_id=r.id, tenant_id=r.tenant_id, month=month,
                                   body=json.dumps({k: rep[k] for k in ("views", "leads", "uptime_pct", "tips", "say")})))
            S._publish(r.tenant_id, "site_care", {**{k: rep[k] for k in ("site", "views", "views_prev", "leads", "leads_prev",
                                                                          "conversion_pct", "uptime_pct", "top_pages", "tips")},
                                                  "month": month, "say": rep["say"], "push": True}, r.conv)
            n += 1
        except Exception:
            log.exception("care note failed for %s", r.id)
    return n


# ---------------------------------------------------------------- agency
def staff_ok(tenant: str, ref: str, actor: str) -> bool:
    """Owner / approved / routine: every site. A staff member: only sites given to them (Site.staff == their id)."""
    if not str(actor).startswith("staff:"):
        return True
    from . import service as S
    with session() as s:
        try:
            r = S._find(s, tenant, ref)
        except Exception:
            return False
        return bool(r.staff) and r.staff in (str(actor), str(actor).split(":", 1)[1])


def assign(tenant: str, ref: str, client: str | None = None, staff: str | None = None) -> dict[str, Any]:
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        if client is not None:
            r.client = client.strip()[:120]
        if staff is not None:
            r.staff = staff.strip()[:60]
        out = {"site": r.number, "client": r.client, "staff": r.staff}
    out["say"] = f"{out['site']}: client '{out['client'] or '-'}', staff '{out['staff'] or 'sirf aap'}'."
    return out


def clients(tenant: str) -> list[dict[str, Any]]:
    from . import hosting as H
    flush()
    a, b = _period(30)
    with session() as s:
        sites = s.scalars(select(Site).where(Site.tenant_id == tenant).order_by(Site.client, Site.created_at)).all()
        live = {h.site_id: h.hostname for h in s.scalars(select(H.SiteHost).where(
            H.SiteHost.tenant_id == tenant, H.SiteHost.status == "active", H.SiteHost.role == "main")).all()}
        groups: dict[str, dict[str, Any]] = {}
        for r in sites:
            g = groups.setdefault(r.client or "", {"client": r.client or "", "sites": [], "views": 0, "leads": 0})
            v = sum(x.views for x in _days(s, r.id, a, b))
            ld = _leads(s, r.id, a, b)
            g["sites"].append({"id": r.id, "number": r.number, "name": r.name, "status": r.status, "version": r.version,
                               "live": live.get(r.id, ""), "staff": r.staff, "views_30d": v, "leads_30d": ld})
            g["views"] += v
            g["leads"] += ld
    return list(groups.values())


def client_report(tenant: str, client: str) -> dict[str, Any]:
    g = next((x for x in clients(tenant) if x["client"].lower() == (client or "").strip().lower()), None)
    if g is None:
        from .service import SiteError
        raise SiteError("Is naam ka client nahi mila.")
    lines = [f"{x['number']} {x['name']}: {'live ' + x['live'] if x['live'] else x['status']}, 30 din: {x['views_30d']} visit, "
             f"{x['leads_30d']} enquiry" for x in g["sites"]]
    return {**g, "text": f"{g['client'] or 'Bina client'}\n" + "\n".join(lines),
            "say": f"{g['client']}: {len(g['sites'])} website, 30 din mein {g['views']} visit, {g['leads']} enquiry."}
