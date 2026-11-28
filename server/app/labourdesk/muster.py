"""The daily muster: per person (present / half / absent, hours, overtime, pieces) or a gang head count, from the foreman's
phone, a voice note, a photo of the paper sheet, the attendance device's CSV or typed. Rows are never edited: a correction
is a counter-row with a reason and who made it. Names Hoola cannot match go to "Who is this?" - never guessed.

The checks (flags, a person decides): the same person on two sites the same day; one device checking in many people inside a
minute; the register above the gate count; a person whose required papers lapsed or are missing; hours over her daily limit;
a mark after the cut-off; a change after the site engineer approved the day."""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from ..db import session
from .core import (LOCK, LabourError, S, day_of, employer_id, match, need_who, num, own_employer, paper_state, settings, site_id, site_names,
                   span, stamp, tables, today)
from .models import LdDayClose, LdEmployer, LdGate, LdMark, LdUnknown, LdWorker

VAL = {"p": 1.0, "present": 1.0, "1": 1.0, "h": 0.5, "half": 0.5, "½": 0.5, "0.5": 0.5, "a": 0.0, "absent": 0.0, "0": 0.0}
SOURCES = ("typed", "voice", "photo", "device", "phone", "legacy")


def _seq(s, tenant: str) -> int:
    return int(s.scalar(select(func.max(LdMark.seq)).where(LdMark.tenant_id == tenant)) or 0) + 1


def _value(v: Any) -> float:
    if isinstance(v, (int, float)):
        if v not in (0, 0.5, 1):
            raise LabourError("Attendance: 1 (present), 0.5 (half day) or 0 (absent).")
        return float(v)
    x = VAL.get(S(v, 10).lower())
    if x is None:
        raise LabourError(f"Attendance '{v}': P, half or A.")
    return x


def effective(s, tenant: str, start: str, end: str, site: str = "") -> tuple[dict[tuple, LdMark], dict[tuple, LdMark]]:
    """The mark in force for each (day, site, worker) and each (day, site, employer, gang) head count: the newest row wins."""
    q = select(LdMark).where(LdMark.tenant_id == tenant, LdMark.day >= start, LdMark.day <= end)
    if site:
        q = q.where(LdMark.site_id == site)
    per, heads = {}, {}
    for m in s.scalars(q.order_by(LdMark.seq)).all():
        if m.worker_id:
            per[(m.day, m.site_id, m.worker_id)] = m
        else:
            heads[(m.day, m.site_id, m.employer_id, m.gang)] = m
    return per, heads


def mark(tenant: str, marks: list[dict[str, Any]], site: str = "", day: str = "", source: str = "typed", who: str = "", device: str = "",
         gang: str = "") -> dict[str, Any]:
    """Each mark: {name or worker_id, status P|half|A (or value), hours, ot_hours, pieces, note} - or a head count {employer, gang, count}."""
    tables()
    if source not in SOURCES:
        raise LabourError("Source: typed, voice, photo, device or phone.")
    if not isinstance(marks, list) or not marks:
        raise LabourError("Give at least one mark: a name with P, half or A - or a gang's head count.")
    who = need_who(who, "the muster")
    d = day_of(day, tenant)
    if d > today(tenant).isoformat():
        raise LabourError("A muster cannot be for a day that has not come yet.")
    at = stamp(tenant)
    st = settings(tenant)
    late = d == today(tenant).isoformat() and at[11:16] > st["cutoff"]
    saved, unknown, heads = 0, [], 0
    with LOCK, session() as s:
        sid = site_id(s, tenant, site)
        seq = _seq(s, tenant)
        for x in marks[:2000]:
            if not isinstance(x, dict):
                continue
            if x.get("count") not in (None, "") and not (x.get("name") or x.get("worker_id")):
                c = int(num(x["count"], "Head count"))
                s.add(LdMark(tenant_id=tenant, seq=seq, day=d, site_id=sid, worker_id="", employer_id=employer_id(s, tenant, S(x.get("employer"), 120)),
                             gang=S(x.get("gang") or gang, 60) or "gang", count=c, value=1.0, ot_hours=num(x.get("ot_hours") or 0, "Overtime hours"),
                             source=source, device=S(device, 60), who=who, at=at, note=S(x.get("note"), 200)))
                seq += 1
                heads += 1
                continue
            w = s.get(LdWorker, S(x.get("worker_id"), 40)) if x.get("worker_id") else None
            if w is None or w.tenant_id != tenant:
                w, guesses = match(s, tenant, S(x.get("name"), 120))
                if w is None:
                    v = _value(x.get("status", x.get("value", "P")))
                    s.add(LdUnknown(tenant_id=tenant, site_id=sid, day=d, name=S(x.get("name"), 120), value=v, source=source, guesses=guesses))
                    unknown.append({"name": S(x.get("name"), 120), "guesses": guesses})
                    continue
            v = _value(x.get("status", x.get("value", "P")))
            hours = num(x.get("hours") or 0, "Hours")
            if hours > 24:
                raise LabourError(f"{w.name}: more than 24 hours in a day.")
            s.add(LdMark(tenant_id=tenant, seq=seq, day=d, site_id=sid, worker_id=w.id, employer_id=w.employer_id, gang=S(x.get("gang") or w.gang or gang, 60),
                         value=v, hours=hours, ot_hours=num(x.get("ot_hours") or 0, "Overtime hours"), pieces=num(x.get("pieces") or 0, "Pieces"),
                         source=source, device=S(device, 60), who=who, at=(S(x.get("at"), 19) if source == "device" and x.get("at") else at),
                         note=S(x.get("note"), 200)))
            seq += 1
            saved += 1
    say = f"{saved} mark(s) saved" + (f", {heads} head count(s)" if heads else "")
    if unknown:
        say += f"; {len(unknown)} name(s) I could not match are waiting under 'Who is this?'"
    if late:
        say += f" (after your {st['cutoff']} cut-off)"
    return {"saved": saved, "heads": heads, "unknown": unknown, "late": late, "day": d, "say": say + "."}


def correct(tenant: str, id: str, who: str, reason: str, status: Any = None, hours: Any = None, ot_hours: Any = None, count: Any = None) -> dict[str, Any]:
    """A counter-row: the original stays as it was; the new row says what changed, why and who."""
    tables()
    who = need_who(who, "the correction")
    reason = S(reason, 200)
    if not reason:
        raise LabourError("Why is the mark being corrected?")
    with LOCK, session() as s:
        m = s.get(LdMark, id)
        if m is None or m.tenant_id != tenant:
            raise LabourError("No such mark.")
        n = LdMark(tenant_id=tenant, seq=_seq(s, tenant), day=m.day, site_id=m.site_id, worker_id=m.worker_id, employer_id=m.employer_id, gang=m.gang,
                   value=_value(status) if status not in (None, "") else m.value, count=int(num(count, "Head count")) if count not in (None, "") else m.count,
                   hours=num(hours, "Hours") if hours not in (None, "") else m.hours, ot_hours=num(ot_hours, "Overtime hours") if ot_hours not in (None, "") else m.ot_hours,
                   pieces=m.pieces, source=m.source, device="", who=who, at=stamp(tenant), corrects=m.id, reason=reason)
        s.add(n)
        s.flush()
        closed = s.scalars(select(LdDayClose).where(LdDayClose.tenant_id == tenant, LdDayClose.site_id == m.site_id, LdDayClose.day == m.day)).first()
        return {"id": n.id, "say": "Corrected; the first mark is kept." + (" The site engineer had approved this day: it needs approving again." if closed else "")}


def resolve_unknown(tenant: str, id: str, worker: str = "", who: str = "", drop: bool = False) -> dict[str, Any]:
    tables()
    who = need_who(who, "matching the name")
    with LOCK, session() as s:
        u = s.get(LdUnknown, id)
        if u is None or u.tenant_id != tenant or u.resolved:
            raise LabourError("That name was already settled.")
        if drop:
            u.resolved, u.who = "dropped", who
            return {"say": f"'{u.name}' left out of the muster."}
        from .core import resolve as _r
        w = _r(s, tenant, worker)
        s.add(LdMark(tenant_id=tenant, seq=_seq(s, tenant), day=u.day, site_id=u.site_id, worker_id=w.id, employer_id=w.employer_id, gang=w.gang,
                     value=u.value, source=u.source, who=who, at=stamp(tenant), note=f"matched from '{u.name}'"))
        u.resolved, u.who = w.id, who
        return {"say": f"'{u.name}' is {w.name}; marked."}


def gate(tenant: str, count: Any, site: str = "", day: str = "", source: str = "", who: str = "") -> dict[str, Any]:
    tables()
    with LOCK, session() as s:
        sid = site_id(s, tenant, site)
        d = day_of(day, tenant)
        s.add(LdGate(tenant_id=tenant, site_id=sid, day=d, count=int(num(count, "Gate count")), source=S(source, 120) or "gate register", who=S(who, 80)))
    return {"say": f"Gate count {int(num(count, 'Gate count'))} saved for {d}."}


def close_day(tenant: str, site: str, day: str, who: str) -> dict[str, Any]:
    """The site engineer approves the day's muster (a person's tap)."""
    tables()
    who = need_who(who, "approving the muster")
    with LOCK, session() as s:
        sid = site_id(s, tenant, site)
        d = day_of(day, tenant)
        last = int(s.scalar(select(func.max(LdMark.seq)).where(LdMark.tenant_id == tenant, LdMark.site_id == sid, LdMark.day == d)) or 0)
        if not last:
            raise LabourError("Nothing is marked for that day yet.")
        s.add(LdDayClose(tenant_id=tenant, site_id=sid, day=d, who=who, seq=last))
    return {"say": f"Muster for {d} approved by {who}."}


def import_device(tenant: str, text: str, site: str = "", who: str = "", device: str = "") -> dict[str, Any]:
    """An attendance device's export as CSV: name or code, day (YYYY-MM-DD), in (HH:MM), out (HH:MM) - one row per check-in."""
    rows = list(csv.DictReader(io.StringIO(str(text or "")[:2_000_000])))
    if not rows:
        raise LabourError("Paste the device export as CSV: name, day, in, out.")
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows[:20000]:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        name = r.get("name") or r.get("code") or r.get("employee")
        d = (r.get("day") or r.get("date") or "")[:10]
        if not name or not d:
            continue
        hours = 0.0
        t1, t2 = r.get("in") or r.get("time in"), r.get("out") or r.get("time out")
        if t1 and t2:
            try:
                a, b = datetime.strptime(t1[:5], "%H:%M"), datetime.strptime(t2[:5], "%H:%M")
                hours = round(((b - a).seconds) / 3600, 2)
            except ValueError:
                hours = 0.0
        by_day[d].append({"name": name, "status": "P", "hours": hours, "at": f"{d}T{t1[:5]}:00" if t1 and len(t1) >= 5 else ""})
    out, unknown = 0, []
    for d, ms in by_day.items():
        r = mark(tenant, ms, site=site, day=d, source="device", who=who or "attendance device", device=S(device, 60) or "device")
        out += r["saved"]
        unknown += r["unknown"]
    return {"saved": out, "unknown": unknown, "days": sorted(by_day), "say": f"{out} check-in(s) read from the device file" + (f"; {len(unknown)} name(s) to match" if unknown else "") + "."}


def day_view(tenant: str, day: str = "", site: str = "") -> dict[str, Any]:
    tables()
    st = settings(tenant)
    d = day_of(day, tenant)
    with session() as s:
        sn = site_names(s, tenant)
        sid = site_id(s, tenant, site) if site else ""
        emp = {r.id: r for r in s.scalars(select(LdEmployer).where(LdEmployer.tenant_id == tenant)).all()}
        wk = {r.id: r for r in s.scalars(select(LdWorker).where(LdWorker.tenant_id == tenant)).all()}
        per, heads = effective(s, tenant, d, d)
        allmarks = s.scalars(select(LdMark).where(LdMark.tenant_id == tenant, LdMark.day == d).order_by(LdMark.seq)).all()
        gates = {g.site_id: g for g in s.scalars(select(LdGate).where(LdGate.tenant_id == tenant, LdGate.day == d).order_by(LdGate.id)).all()}
        closes = {c.site_id: c for c in s.scalars(select(LdDayClose).where(LdDayClose.tenant_id == tenant, LdDayClose.day == d)).all()}
        unk = [u for u in s.scalars(select(LdUnknown).where(LdUnknown.tenant_id == tenant, LdUnknown.day == d)).all() if not u.resolved]
        present_ids = sorted({k[2] for k, m in per.items() if m.value > 0})
        papers_bad = paper_state(s, tenant, present_ids, d, st["required"])
        own = own_employer(s, tenant).id
    flags: list[dict[str, Any]] = []
    # 1. the same person on two sites
    sites_of: dict[str, set] = defaultdict(set)
    for (dd, si, w), m in per.items():
        if m.value > 0:
            sites_of[w].add(si)
    for w, ss in sites_of.items():
        if len(ss) > 1:
            flags.append({"sev": "bad", "kind": "two_sites", "worker_id": w, "text": f"{wk[w].name} is marked present on {len(ss)} sites: " +
                          ", ".join(sorted(sn.get(x, '') for x in ss)) + ". Which one is right?"})
    # 2. one device checking in many people inside a minute
    burst = int(st["burst"])
    dev: dict[str, list[str]] = defaultdict(list)
    for m in allmarks:
        if m.source == "device" and m.device and m.worker_id:
            dev[m.device].append(m.at)
    for dv, ats in dev.items():
        ats.sort()
        for i in range(len(ats)):
            j = i
            while j < len(ats) and _secs(ats[i], ats[j]) <= 60:
                j += 1
            if j - i > burst:
                flags.append({"sev": "warn", "kind": "burst", "text": f"Device {dv} checked in {j - i} people inside one minute (your limit {burst}): someone may be marking for others."})
                break
    phones: dict[str, set] = defaultdict(set)
    for m in allmarks:
        if m.device and m.source in ("phone", "device"):
            phones[m.device].add(m.site_id)
    for dv, ss in phones.items():
        if len(ss) > 1:
            flags.append({"sev": "warn", "kind": "device_sites", "text": f"One phone / device ({dv}) marked people on {len(ss)} sites today."})
    # per site: totals, gate, papers, hours, late
    out_sites = []
    for si in sorted({k[1] for k in per} | {k[1] for k in heads} | set(gates) | ({sid} if sid else set())):
        if sid and si != sid:
            continue
        people = [(w, m) for (dd, s_, w), m in per.items() if s_ == si]
        present = sum(1 for w, m in people if m.value > 0)
        half = sum(1 for w, m in people if m.value == 0.5)
        absent = sum(1 for w, m in people if m.value == 0)
        hc = sum(m.count for (dd, s_, e, g), m in heads.items() if s_ == si)
        total = present + hc
        g = gates.get(si)
        if g is not None and abs(total - g.count) > int(st["gate_tol"]):
            sev = "bad" if total > g.count else "warn"
            flags.append({"sev": sev, "kind": "gate", "site_id": si, "text": f"{sn.get(si, '')}: the muster says {total}, the gate says {g.count} - " +
                          ("more on the register than came through the gate." if total > g.count else "fewer on the register than at the gate (someone not marked?).")})
        for w, m in people:
            if m.value > 0 and w in papers_bad:
                flags.append({"sev": "warn", "kind": "papers", "worker_id": w, "site_id": si,
                              "text": f"{wk[w].name}: " + "; ".join(papers_bad[w]) + ". The site engineer decides whether they work."})
            hrs = m.hours or (st["day_hours"] * m.value + (m.ot_hours or 0))
            if hrs > float(st["max_day_hours"]) + 1e-9:
                flags.append({"sev": "warn", "kind": "hours", "worker_id": w, "text": f"{wk[w].name}: {hrs:g} hours, over your {st['max_day_hours']:g}-hour limit."})
        c = closes.get(si)
        after = [m for m in allmarks if m.site_id == si and c is not None and m.seq > c.seq]
        if after:
            flags.append({"sev": "warn", "kind": "after_close", "site_id": si, "text": f"{sn.get(si, '')}: {len(after)} change(s) after {c.who} approved the day - approve it again."})
        gangs: dict[tuple, dict[str, Any]] = {}
        for w, m in people:
            k = (m.employer_id, m.gang or wk[w].gang or "")
            gg = gangs.setdefault(k, {"employer": emp[m.employer_id].name if m.employer_id in emp else "", "own": m.employer_id == own,
                                      "gang": k[1] or "no gang", "present": 0, "half": 0, "absent": 0, "ot": 0.0, "count": 0, "people": []})
            gg["present"] += 1 if m.value == 1 else 0
            gg["half"] += 1 if m.value == 0.5 else 0
            gg["absent"] += 1 if m.value == 0 else 0
            gg["ot"] += m.ot_hours or 0
            gg["people"].append({"mark_id": m.id, "worker_id": w, "name": wk[w].name, "value": m.value, "hours": m.hours, "ot_hours": m.ot_hours,
                                 "source": m.source, "who": m.who, "corrected": bool(m.corrects), "flags": papers_bad.get(w, [])})
        for (dd, s_, e, gname), m in heads.items():
            if s_ != si:
                continue
            gg = gangs.setdefault((e, gname), {"employer": emp[e].name if e in emp else "", "own": e == own, "gang": gname, "present": 0, "half": 0,
                                                "absent": 0, "ot": 0.0, "count": 0, "people": [], "head_id": m.id})
            gg["count"] += m.count
            gg["ot"] += m.ot_hours or 0
            gg["head_id"] = m.id
        out_sites.append({"site_id": si, "site": sn.get(si, ""), "present": present, "half": half, "absent": absent, "heads": hc, "total": total,
                          "gate": g.count if g else None, "closed": ({"who": c.who, "at": c.at.isoformat() if c.at else ""} if c else None),
                          "late": sum(1 for m in allmarks if m.site_id == si and m.at[:10] == d and m.at[11:16] > st["cutoff"]),
                          "gangs": sorted(gangs.values(), key=lambda x: (not x["own"], x["employer"], x["gang"]))})
    corrections = [{"id": m.id, "corrects": m.corrects, "who": m.who, "reason": m.reason, "at": m.at, "name": wk[m.worker_id].name if m.worker_id in wk else m.gang}
                   for m in allmarks if m.corrects]
    return {"day": d, "sites": out_sites, "flags": flags, "unknown": [{"id": u.id, "name": u.name, "site": sn.get(u.site_id, ""), "guesses": u.guesses,
                                                                         "value": u.value, "source": u.source} for u in unk],
            "corrections": corrections, "cutoff": st["cutoff"], "serious": sum(1 for f in flags if f["sev"] == "bad")}


def _secs(a: str, b: str) -> float:
    try:
        return abs((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds())
    except ValueError:
        return 10 ** 9


def headcount(tenant: str, days: int = 30) -> dict[str, Any]:
    """Present a day for the last `days`: own people, subcontractors' people, and the planned headcount."""
    tables()
    t0 = today(tenant)
    start = (t0 - timedelta(days=days - 1)).isoformat()
    with session() as s:
        own = own_employer(s, tenant).id
        per, heads = effective(s, tenant, start, t0.isoformat())
        from .models import LdSite
        planned = sum(r.planned for r in s.scalars(select(LdSite).where(LdSite.tenant_id == tenant, LdSite.active.is_(True))).all())
    rows = []
    for i in range(days):
        d = (t0 - timedelta(days=days - 1 - i)).isoformat()
        o = sum(m.value for (dd, si, w), m in per.items() if dd == d and m.employer_id == own and m.value > 0)
        c = sum(m.value for (dd, si, w), m in per.items() if dd == d and m.employer_id != own and m.value > 0)
        o += sum(m.count for (dd, si, e, g), m in heads.items() if dd == d and e == own)
        c += sum(m.count for (dd, si, e, g), m in heads.items() if dd == d and e != own)
        rows.append({"day": d, "own": round(o, 1), "subs": round(c, 1)})
    return {"rows": rows, "planned": planned}


def timesheet(tenant: str, start: str, end: str, employer: str = "", site: str = "") -> dict[str, Any]:
    """The muster rolled up per person for a period (days, hours, overtime) - what a wage run is made from."""
    tables()
    days = span(start, end)
    with session() as s:
        eid = employer_id(s, tenant, employer) if employer else ""
        sid = site_id(s, tenant, site) if site else ""
        per, heads = effective(s, tenant, days[0], days[-1], sid)
        wk = {r.id: r for r in s.scalars(select(LdWorker).where(LdWorker.tenant_id == tenant)).all()}
    rows: dict[str, dict[str, Any]] = {}
    for (d, si, w), m in sorted(per.items()):
        if eid and m.employer_id != eid:
            continue
        r = rows.setdefault(w, {"worker_id": w, "name": wk[w].name if w in wk else w, "days": 0.0, "hours": 0.0, "ot": 0.0, "marks": []})
        r["days"] += m.value
        r["marks"].append({"day": d, "site_id": si, "value": m.value, "hours": m.hours, "ot_hours": m.ot_hours, "pieces": m.pieces})
    return {"start": days[0], "end": days[-1], "rows": sorted(rows.values(), key=lambda r: r["name"])}
