"""The Site Reliability Engineer's desk: SLOs and error budgets, burn-rate alerts (and the Prometheus rules for them), alert rules
checked and alert noise counted, incidents read into a timeline and a blameless postmortem draft, latency, capacity and
availability - all in code, no model, no money. Nothing is changed on her systems: rules and postmortems are text she adds herself.
Pasted logs, rules and timelines are DATA."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import alerts as AL, avail as AV, capacity as CP, incident as IN, latency as LT, slo as SL

log = logging.getLogger("santosh.sredesk")

KINDS = ("slo", "burn", "avail", "latency", "buckets", "capacity", "queue", "rules", "noise", "incident")
PRE = {"slo": "S", "burn": "B", "avail": "A", "latency": "L", "buckets": "H", "capacity": "C", "queue": "Q", "rules": "R", "noise": "N",
       "incident": "I"}
TEXT_KINDS = ("burn", "latency", "buckets", "capacity", "rules", "noise", "incident")
FIELDS = ("service", "target", "window_days", "tz", "work_start", "work_end", "weekend", "scrape_s", "latency_ms", "bad_metric",
          "total_metric", "selector")
KEEP = 400
MAX_TEXT = 3_000_000
ERRORS = (SL.SloError, AV.AvailError, LT.LatencyError, CP.CapacityError, AL.AlertError, IN.IncidentError)


class SreError(ValueError):
    pass


class XItem(Base):
    __tablename__ = "sredesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(10), default="slo")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class XSettings(Base):
    __tablename__ = "sredesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    service: Mapped[str] = mapped_column(String(80), default="")
    target: Mapped[float] = mapped_column(Float, default=0.999)
    window_days: Mapped[int] = mapped_column(Integer, default=30)
    tz: Mapped[str] = mapped_column(String(64), default="UTC")
    work_start: Mapped[int] = mapped_column(Integer, default=9)
    work_end: Mapped[int] = mapped_column(Integer, default=18)
    weekend: Mapped[str] = mapped_column(String(40), default="sat,sun")
    scrape_s: Mapped[int] = mapped_column(Integer, default=30)
    latency_ms: Mapped[float] = mapped_column(Float, default=300.0)
    bad_metric: Mapped[str] = mapped_column(String(120), default="")
    total_metric: Mapped[str] = mapped_column(String(120), default="")
    selector: Mapped[str] = mapped_column(String(200), default="")


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    XItem.__table__.create(eng, checkfirst=True)
    XSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(XSettings, tenant)
        d = {k: getattr(r, k) if r else XSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _int(v: Any, name: str, lo: int, hi: int) -> int:
    try:
        x = int(float(v))
    except (TypeError, ValueError):
        raise SreError(f"{name}: a whole number.")
    if not lo <= x <= hi:
        raise SreError(f"{name}: {lo} to {hi}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    if f.get("service") is not None:
        c["service"] = re.sub(r"[^\w .-]", "", str(f["service"]))[:80].strip()
    if f.get("target") not in (None, ""):
        try:
            c["target"] = SL.target_of(f["target"])
        except SL.SloError as e:
            raise SreError(str(e))
    if f.get("window_days") not in (None, ""):
        c["window_days"] = _int(f["window_days"], "Window", 1, 366)
    if f.get("tz") not in (None, ""):
        try:
            ZoneInfo(str(f["tz"]))
        except (ZoneInfoNotFoundError, ValueError):
            raise SreError("Time zone: an IANA name like Europe/London, America/New_York or Asia/Kolkata.")
        c["tz"] = str(f["tz"])
    for k, lo, hi in (("work_start", 0, 23), ("work_end", 1, 24), ("scrape_s", 1, 3600)):
        if f.get(k) not in (None, ""):
            c[k] = _int(f[k], k.replace("_", " ").capitalize(), lo, hi)
    if c.get("work_start") is not None and c.get("work_end") is not None and c["work_end"] <= c["work_start"]:
        raise SreError("Working hours: the end must be after the start.")
    if f.get("weekend") is not None:
        days = [d.strip()[:3].lower() for d in str(f["weekend"]).split(",") if d.strip()]
        if any(d not in ("mon", "tue", "wed", "thu", "fri", "sat", "sun") for d in days):
            raise SreError("Days off: like sat,sun or fri,sat.")
        c["weekend"] = ",".join(days)
    if f.get("latency_ms") not in (None, ""):
        try:
            v = float(f["latency_ms"])
        except (TypeError, ValueError):
            raise SreError("Latency threshold: milliseconds.")
        if not 0 < v <= 600_000:
            raise SreError("Latency threshold: more than 0 ms.")
        c["latency_ms"] = v
    for k in ("bad_metric", "total_metric"):
        if f.get(k) not in (None, ""):
            if not SL._METRIC.match(str(f[k])):
                raise SreError(f"{k.replace('_', ' ').capitalize()}: a Prometheus metric name, like http_requests_total.")
            c[k] = str(f[k])
    if f.get("selector") is not None:
        sel = str(f["selector"]).strip()
        if sel:
            try:
                SL.rules("x", 0.99, 30, "a", "b", sel)
            except SL.SloError as e:
                raise SreError(str(e))
        c["selector"] = sel
    with session() as s:
        r = s.get(XSettings, tenant)
        if r is None:
            r = XSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    b: dict[str, Any] = {"bad": _bad(res), "issues": len([i for i in res.get("issues") or [] if i.get("sev") in ("bad", "warn")])}
    if kind == "slo":
        b.update(target=res.get("target"), used=res.get("used"), burn=res.get("burn_rate"))
    elif kind == "burn":
        b.update(fired=len(res.get("fired") or []), burn=res.get("burn_overall"), sli=res.get("sli"), bad=b["bad"] or bool(
            [f for f in res.get("fired") or [] if f.get("severity") == "page"]))
    elif kind == "avail":
        b.update(availability=res.get("availability"), weakest=res.get("weakest"), down=res.get("downtime_month_min"))
    elif kind == "latency":
        b.update(p99=(res.get("percentiles") or {}).get("p99"), under=res.get("under_threshold"))
    elif kind == "buckets":
        b.update(p99=((res.get("quantiles") or {}).get("p99") or {}).get("ms"), under=res.get("under_threshold"))
    elif kind == "capacity":
        b.update(share=res.get("now_share"), limit_on=res.get("hits_limit"), weeks=res.get("weeks_left"))
    elif kind == "queue":
        b.update(utilisation=res.get("utilisation"), response=res.get("response_ms"))
    elif kind == "rules":
        b.update(alerts=res.get("alerts"), problems=(res.get("counts") or {}).get("bad"), warnings=(res.get("counts") or {}).get("warn"),
                 bad=bool((res.get("counts") or {}).get("bad")))
    elif kind == "noise":
        b.update(per_week=res.get("pages_per_week"), top=((res.get("table") or [{}])[0]).get("name"))
    elif kind == "incident":
        b.update(severity=res.get("severity"), impact=(res.get("said") or {}).get("impact"), resolved="resolve" in (res.get("marks") or {}),
                 followups=len(res.get("followups") or []), bad="resolve" not in (res.get("marks") or {}))
    return b


def _view(r: XItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(XItem).where(XItem.tenant_id == tenant)
        if kind:
            q = q.where(XItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(XItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> XItem:
    r = s.get(XItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(XItem).where(XItem.tenant_id == tenant, XItem.number == str(iid or "").upper())).first()
        if r is None:
            raise SreError("Not found.")
    return r


def get(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        return _view(_row(s, tenant, iid), True)


def _dict(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if isinstance(v, str) and v.strip():
        try:
            d = json.loads(v)
        except ValueError:
            raise SreError("The settings must be JSON.")
        if isinstance(d, dict):
            return d
    return {}


def _run(kind: str, text: str, inp: dict[str, Any], st: dict[str, Any]) -> tuple[dict[str, Any], str]:
    g = lambda k, d=None: inp.get(k) if inp.get(k) not in (None, "") else d   # noqa: E731
    svc = st.get("service") or "the service"
    if kind == "slo":
        res = SL.budget(g("target", st["target"]), g("window_days", st["window_days"]), g("good"), g("total"), g("elapsed_days"))
        return res, f"SLO {res['target']:.3%} over {res['window_days']:g} days"
    if kind == "burn":
        res = SL.burn(text, g("target", st["target"]), g("window_days", st["window_days"]))
        return res, f"Burn rate: {res['samples']} samples, {res['hours']:g} h"
    if kind == "avail":
        tree = inp.get("tree")
        if isinstance(tree, str):
            tree = _dict(tree)
        if not isinstance(tree, dict):
            raise SreError("Give the system as a tree of parts.")
        res = AV.analyse(tree, g("target", st["target"]))
        return res, f"Availability of {tree.get('name') or 'the system'}"
    if kind == "latency":
        res = LT.analyse(text, g("threshold_ms", st["latency_ms"]), str(g("unit", "ms")), g("objective"))
        return res, f"Latency: {res['count']} requests"
    if kind == "buckets":
        res = LT.buckets(text, g("threshold_ms", st["latency_ms"]), str(g("unit", "s")))
        return res, f"Histogram: {res['total']:g} requests"
    if kind == "capacity":
        if g("limit") is None:
            raise SreError("Give the limit: the most the system can take, in the same unit.")
        res = CP.forecast(text, g("limit"), g("headroom", 80), str(g("unit", ""))[:12])
        return res, f"Capacity of {g('what', svc)}"
    if kind == "queue":
        res = CP.queue(g("rps"), g("service_ms"), g("servers"))
        return res, f"Queue: {res['rps']:g} req/s on {res['servers']} servers"
    if kind == "rules":
        res = AL.lint(text, g("scrape_s", st["scrape_s"]))
        return res, f"Alert rules: {res['alerts']} alerts"
    if kind == "noise":
        res = AL.noise(text, st["tz"], int(st["work_start"]), int(st["work_end"]), st["weekend"])
        return res, f"Alert noise: {res['alerts']} alerts, {res['days']:g} days"
    res = IN.timeline(text, str(g("tz", st["tz"])), str(g("day", "")))
    first = next((e["text"] for e in res["events"] if e.get("stage") in ("start", "detect")), res["events"][0]["text"])
    res["postmortem"] = IN.postmortem(res, str(g("title", "")) or first[:100], str(g("service", st.get("service") or "")), str(g("impact", "")),
                                      str(g("root_cause", "")))
    return res, f"Incident: {first[:80]}"


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise SreError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise SreError("That is longer than 3,000,000 characters.")
    if kind in TEXT_KINDS and not text.strip():
        raise SreError({"burn": "Paste the samples first: time, good, total.", "latency": "Paste the durations first.",
                        "buckets": "Paste the histogram buckets first.", "capacity": "Paste the dated peak use first: date, value.",
                        "rules": "Paste the rules file first.", "noise": "Paste the alert history first (CSV).",
                        "incident": "Paste the timeline first."}[kind])
    try:
        res, auto = _run(kind, text, inp, st)
    except ERRORS as e:
        raise SreError(str(e))
    with session() as s:
        n = len(s.scalars(select(XItem.id).where(XItem.tenant_id == tenant, XItem.kind == kind)).all()) + 1
        r = XItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200],
                  text=text if kind in TEXT_KINDS else "", inputs=inp, result=res)
        if kind == "incident" and "resolve" in (res.get("marks") or {}):
            r.status = "fixed"
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(XItem.id).where(XItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(XItem).where(XItem.tenant_id == tenant).order_by(XItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise SreError("Status: open | fixed | ignored")
    _tables()
    with session() as s:
        r = _row(s, tenant, iid)
        r.status, r.updated_at = status, now()
        if note:
            r.note = str(note)[:1000]
        iid = r.id
    return get(tenant, iid)


def delete(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        s.delete(_row(s, tenant, iid))
    return {"ok": True, "say": "Removed."}


def rules_for(tenant: str, **over: Any) -> dict[str, Any]:
    st = {**settings(tenant), **{k: v for k, v in over.items() if v not in (None, "")}}
    if not st.get("bad_metric") or not st.get("total_metric"):
        raise SreError("Name your metrics in Settings first: the bad-events counter and the all-events counter.")
    try:
        return SL.rules(st.get("service") or "service", st["target"], st["window_days"], st["bad_metric"], st["total_metric"],
                        st.get("selector") or "")
    except SL.SloError as e:
        raise SreError(str(e))


def postmortem(tenant: str, iid: str, **facts: Any) -> dict[str, Any]:
    d = get(tenant, iid)
    if d["kind"] != "incident":
        raise SreError("A postmortem is made from an incident.")
    md = IN.postmortem(d["result"], str(facts.get("title") or re.sub(r"^Incident:\s*", "", d["title"])), str(facts.get("service") or settings(tenant).get("service") or ""),
                       str(facts.get("impact") or ""), str(facts.get("root_cause") or ""))
    return {"ok": True, "markdown": md, "file": f"postmortem-{d['number'].lower()}.md"}


def incident_stats(tenant: str) -> dict[str, Any]:
    from statistics import median
    xs = [get(tenant, x["id"])["result"] for x in items(tenant, "incident", 200)]
    def med(k: str) -> float | None:
        v = [x["times"][k] for x in xs if (x.get("times") or {}).get(k) is not None]
        return median(v) if v else None
    return {"count": len(xs), "open": sum(1 for x in xs if "resolve" not in (x.get("marks") or {})),
            "median": {k: IN.fmt(med(k + "_s")) for k in ("detect", "ack", "mitigate", "resolve")}}


def health() -> dict[str, Any]:
    return {"alerts": SL.alerts_for(30), "nines": SL.nines_table(), "kinds": list(KINDS),
            "notes": "Everything is worked out in code. Rules and postmortems are text you add yourself; Hoola changes nothing on your systems."}
