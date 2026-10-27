"""IT Helpdesk Sahayak: Hoola as a small office's IT helpdesk, end to end.

  1. Gets the job: her or her staff's words ("accounts wale PC par printer nahi chal raha", "sab ka net band", "Tally
     licence error", "yeh mail ajeeb hai, Ramesh ne link khola") in chat, on a call, or from a team member (Employee staff actor).
  2. Logs it with details: ticket HD-0001 with who / which device (asset register) / error text / since when / what was tried,
     impact x urgency -> P1-P4, response + fix times (SLA), the same problem on the same device before, several people at
     once = one known issue (linked).
  3. Walks the person through the fix step by step (IT playbooks: printer, network, slow PC, email, password / lockout,
     Tally, Office, WhatsApp Web, UPS, CCTV, display, scanner, VPN, virus / phishing, backup, PC won't start), one step at a
     time, "theek hua?", what fixed it in THIS office before goes first next time.
  4. Waits for her Haan on CHANGING SYSTEM SETTINGS: a step that changes a setting, installs / uninstalls, resets or touches an
     account becomes a `helpdesk_change` card; only her tap in the app (`decide_change(by_tap=True)`) unlocks it. Hoola itself
     never changes, installs or resets anything; staff can't approve.
  5. Escalates what needs a technician: AMC vendor / ISP / printer service / Tally partner / electrician picked from the asset
     and the problem, with what to tell them (model, serial, warranty / AMC, error, what was tried) as a WhatsApp / email /
     call draft she sends.
  6. Security: a suspicious mail / SMS is read as DATA (links never opened): red flags, what to do, CERT-In 6-hour rule when it
     applies (business = body corporate) with a report draft and a reminder, DPDP note when personal data is involved.
  7. Learns: step stats per office, repeat devices -> AMC / replace suggestion, warranty / AMC / Windows 10 dates in the morning note.

Never: asking for or keeping a password / OTP / PIN (scrubbed from every text), changing a system setting by itself, opening a
suspicious link, paying a vendor.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from sqlalchemy import select

from ..db import now, session
from . import playbooks as P
from . import rules as R
from .models import (
    HelpdeskAsset,
    HelpdeskChange,
    HelpdeskIncident,
    HelpdeskSettings,
    HelpdeskStepStat,
    HelpdeskTicket,
    HelpdeskVendor,
)

log = logging.getLogger("santosh.helpdesk")
_LOCK = threading.RLock()
RESULTS = ("fixed", "not_fixed", "skipped", "cant")
OPEN = ("new", "working", "waiting_haan", "waiting_tech")
STATUS_LABEL = {"new": "Naya", "working": "Chal raha", "waiting_haan": "Aapki haan ka intezaar", "waiting_tech": "Technician ke paas",
                "resolved": "Theek ho gaya", "closed": "Band"}
KNOWN_WINDOW_H = 4
SHARED = {"network", "email", "printer", "cctv", "ups_power", "tally", "vpn"}   # one cause can hit many people


class HelpdeskError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _iso(d: datetime | None) -> str:
    d = _aware(d)
    return d.isoformat(timespec="minutes") if d else ""


def clock() -> datetime:
    return now()


def today(tenant: str) -> date:
    from ..life import tz_of
    return clock().astimezone(tz_of(tenant)).date()


def _local(tenant: str, d: datetime | None) -> str:
    from ..life import tz_of
    d = _aware(d)
    return d.astimezone(tz_of(tenant)).strftime("%d %b %I:%M %p") if d else ""


def _date(v) -> date | None:
    if isinstance(v, date):
        return v
    if not v:
        return None
    s = str(v).strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    m = re.fullmatch(r"(\d{4})", s)
    return date(int(m.group(1)), 1, 1) if m else None


def _hrs(h: float) -> str:
    return f"{int(h * 60)} minute" if h < 1 else (f"{h:g} ghante" if h < 48 else f"{h / 24:g} din")


_SECRET = re.compile(r"\b(password|passcode|pass ?word|pwd|pin|mpin|otp|cvv)\b\s*(?:is|hai|:|=|-)?\s*(\S{3,})", re.I)


def scrub(text: str) -> tuple[str, str]:
    """Remove passwords / OTPs / card numbers someone typed. -> (clean text, what was found or '')."""
    from ..net.policy import secret_found
    t = str(text or "")
    found = secret_found(t)
    out = _SECRET.sub(lambda m: f"{m.group(1)} [hataya]", t)
    out = re.sub(r"\b(?:\d[ -]?){13,19}\b", "[hataya]", out)
    if not found and out != t:
        found = "password"
    return out, found


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("helpdesk publish failed")


def _log(t: HelpdeskTicket, what: str, by: str = "Hoola") -> None:
    lg = _j(t.log, [])
    lg.append({"at": now().isoformat(timespec="seconds"), "by": by[:60], "what": what[:300]})
    t.log = _dump(lg[-80:])


def _st(s, tenant: str) -> HelpdeskSettings:
    r = s.get(HelpdeskSettings, tenant)
    if r is None:
        r = HelpdeskSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def actor_name(tenant: str, actor: str) -> str:
    try:
        from ..employee.service import actor_label
        return actor_label(tenant, actor or "owner")
    except Exception:
        return "Owner" if actor in ("", "owner") else actor[:40]


def is_owner(actor: str) -> bool:
    a = actor or "owner"
    return a == "owner" or a.startswith("approved:")


# ---------------------------------------------------------------- settings
_SET_KEYS = ("office_name", "entity", "contact_name", "contact_phone", "contact_email", "it_person", "morning_time", "rules")


def settings(tenant: str) -> dict:
    with session() as s:
        r = _st(s, tenant)
        out = {k: getattr(r, k) for k in _SET_KEYS}
        out["sla"] = {p: R.sla_for(p, _j(r.sla, {})) for p in ("P1", "P2", "P3", "P4")}
        out["entity_label"] = R.ENTITY_LABEL.get(r.entity, r.entity)
        return out


def save_settings(tenant: str, **kw: Any) -> dict:
    with session() as s:
        r = _st(s, tenant)
        if kw.get("entity") is not None:
            e = str(kw["entity"]).lower().strip()
            if e not in R.ENTITY_LABEL:
                raise HelpdeskError("entity = company | llp | partnership | proprietor | trust | society | govt | individual")
            r.entity = e
        for k in ("office_name", "contact_name", "contact_phone", "contact_email", "it_person", "rules"):
            if kw.get(k) is not None:
                setattr(r, k, scrub(str(kw[k]))[0].strip()[:600 if k == "rules" else 160])
        if kw.get("morning_time"):
            m = re.fullmatch(r"(\d{1,2}):(\d{2})", str(kw["morning_time"]).strip())
            if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
                raise HelpdeskError("Samay HH:MM mein (jaise 09:30).")
            r.morning_time = f"{int(m.group(1)):02d}:{m.group(2)}"
        if isinstance(kw.get("sla"), dict):
            cur = _j(r.sla, {})
            for p, v in kw["sla"].items():
                if p in R.SLA_DEFAULT and isinstance(v, dict):
                    cur[p] = {**cur.get(p, {}), **{k: v[k] for k in ("respond_h", "resolve_h") if k in v}}
            r.sla = _dump(cur)
    return settings(tenant)


# ---------------------------------------------------------------- vendors
def _vendor_view(v: HelpdeskVendor, on: date) -> dict:
    amc = _date(v.amc_until)
    return {"id": v.id, "name": v.name, "kind": v.kind, "kind_label": P.VENDOR_LABEL.get(v.kind, v.kind), "phone": v.phone,
            "email": v.email, "covers": _j(v.covers, []), "amc_until": v.amc_until, "amc_days_left": (amc - on).days if amc else None,
            "sla_hours": v.sla_hours, "notes": v.notes}


def _phone(v: str) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d


def save_vendor(tenant: str, name: str = "", vendor: str = "", **kw: Any) -> dict:
    on = today(tenant)
    with _LOCK, session() as s:
        v = _vendor(s, tenant, vendor) if vendor else None
        if v is None:
            if not str(name).strip():
                raise HelpdeskError("Vendor ka naam chahiye.")
            v = s.scalars(select(HelpdeskVendor).where(HelpdeskVendor.tenant_id == tenant, HelpdeskVendor.name == str(name).strip())).first()
        if v is None:
            v = HelpdeskVendor(tenant_id=tenant, name=str(name).strip()[:120])
            s.add(v)
        elif name:
            v.name = str(name).strip()[:120]
        if kw.get("kind"):
            k = str(kw["kind"]).lower()
            v.kind = k if k in P.VENDOR_KINDS else "other"
        if kw.get("phone"):
            p = _phone(kw["phone"])
            if len(p) != 10:
                raise HelpdeskError("Phone 10 ankon ka chahiye.")
            v.phone = p
        if kw.get("email"):
            e = str(kw["email"]).strip()
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", e):
                raise HelpdeskError("Email sahi nahi lagta.")
            v.email = e[:120]
        if kw.get("covers"):
            cv = kw["covers"] if isinstance(kw["covers"], list) else re.split(r"[,\s]+", str(kw["covers"]))
            v.covers = _dump([c for c in (str(x).lower().strip() for x in cv) if c in P.ASSET_KINDS])
        if kw.get("amc_until"):
            d = _date(kw["amc_until"])
            if not d:
                raise HelpdeskError("AMC ki tareekh samajh nahi aayi.")
            v.amc_until = d.isoformat()
        if kw.get("sla_hours") not in (None, ""):
            v.sla_hours = max(0.0, float(kw["sla_hours"]))
        if kw.get("notes") is not None:
            v.notes = scrub(str(kw["notes"]))[0][:400]
        s.flush()
        out = _vendor_view(v, on)
    return {"vendor": out, "say": f"Vendor: {out['name']} ({out['kind_label']})" + (f", AMC {out['amc_until']} tak" if out["amc_until"] else "") + "."}


def _vendor(s, tenant: str, ref: str) -> HelpdeskVendor | None:
    if not ref:
        return None
    v = s.get(HelpdeskVendor, ref)
    if v and v.tenant_id == tenant:
        return v
    rows = s.scalars(select(HelpdeskVendor).where(HelpdeskVendor.tenant_id == tenant)).all()
    low = ref.lower().strip()
    return next((r for r in rows if r.name.lower() == low), None) or next((r for r in rows if low in r.name.lower()), None)


def vendors(tenant: str) -> list[dict]:
    on = today(tenant)
    with session() as s:
        return [_vendor_view(v, on) for v in s.scalars(select(HelpdeskVendor).where(HelpdeskVendor.tenant_id == tenant)
                                                       .order_by(HelpdeskVendor.name)).all()]


def remove_vendor(tenant: str, vendor: str) -> dict:
    with session() as s:
        v = _vendor(s, tenant, vendor)
        if not v:
            raise HelpdeskError("Vendor nahi mila.")
        name = v.name
        for a in s.scalars(select(HelpdeskAsset).where(HelpdeskAsset.tenant_id == tenant, HelpdeskAsset.vendor_id == v.id)).all():
            a.vendor_id = ""
        s.delete(v)
    return {"removed": name, "say": f"{name} hata diya."}


# ---------------------------------------------------------------- assets
def _repeat(s, tenant: str, asset_id: str, exclude: str = "") -> dict | None:
    if not asset_id:
        return None
    since = now() - timedelta(days=90)
    rows = [t for t in s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == tenant, HelpdeskTicket.asset_id == asset_id)).all()
            if t.id != exclude and (_aware(t.created_at) or now()) >= since]
    if len(rows) < 2:
        return None
    cats: dict[str, int] = {}
    for t in rows:
        cats[t.category] = cats.get(t.category, 0) + 1
    top = max(cats.items(), key=lambda x: x[1])
    return {"count_90d": len(rows), "top": top[0], "top_label": P.playbook(top[0])["label"], "top_count": top[1],
            "numbers": [t.number for t in rows][-5:]}


def _advice(a: HelpdeskAsset, rep: dict | None, on: date) -> list[str]:
    out = []
    w, amc, bought = _date(a.warranty_until), _date(a.amc_until), _date(a.bought)
    if rep:
        out.append(f"{rep['count_90d']} baar 90 din mein dikkat ({rep['top_label']} {rep['top_count']} baar).")
        if w and w >= on:
            out.append("Warranty mein hai: brand service centre se claim kijiye (bill saath).")
        elif not (amc and amc >= on):
            out.append("Na warranty na AMC: AMC lena ya badalna sasta pad sakta hai (aapka faisla).")
    years = R.REPLACE_YEARS.get(a.kind)
    if bought and years and (on - bought).days >= years * 365:
        out.append(f"{(on - bought).days // 365} saal purana ({a.kind} aam taur par ~{years} saal): badalne ka budget sochiye.")
    note = R.os_note(a.os, on)
    if note:
        out.append(note)
    return out


def _asset_view(s, a: HelpdeskAsset, on: date, with_history: bool = False) -> dict:
    w, amc = _date(a.warranty_until), _date(a.amc_until)
    v = s.get(HelpdeskVendor, a.vendor_id) if a.vendor_id else None
    rep = _repeat(s, a.tenant_id, a.id)
    out = {"id": a.id, "tag": a.tag, "kind": a.kind, "name": a.name, "brand": a.brand, "model": a.model, "serial": a.serial,
           "user": a.user, "location": a.location, "os": a.os, "bought": a.bought, "warranty_until": a.warranty_until,
           "warranty_days_left": (w - on).days if w else None, "amc_until": a.amc_until, "amc_days_left": (amc - on).days if amc else None,
           "vendor": v.name if v else "", "vendor_id": a.vendor_id, "notes": a.notes, "pc_device": a.pc_device, "active": a.active,
           "repeat": rep, "advice": _advice(a, rep, on)}
    if with_history:
        rows = s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == a.tenant_id, HelpdeskTicket.asset_id == a.id)
                         .order_by(HelpdeskTicket.created_at.desc()).limit(30)).all()
        out["tickets"] = [{"id": t.id, "number": t.number, "title": t.title, "status": t.status, "at": _iso(t.created_at),
                           "fixed_by": t.fixed_by} for t in rows]
    return out


def _asset(s, tenant: str, ref: str) -> HelpdeskAsset | None:
    if not ref:
        return None
    a = s.get(HelpdeskAsset, ref)
    if a and a.tenant_id == tenant:
        return a
    rows = s.scalars(select(HelpdeskAsset).where(HelpdeskAsset.tenant_id == tenant, HelpdeskAsset.active.is_(True))).all()
    low = ref.lower().strip()
    for f in (lambda r: r.tag.lower() == low, lambda r: r.serial and r.serial.lower() == low, lambda r: r.name.lower() == low,
              lambda r: low in r.name.lower(), lambda r: r.user and low == r.user.lower()):
        hit = [r for r in rows if f(r)]
        if len(hit) == 1:
            return hit[0]
    return None


def _asset_for(s, tenant: str, person: str, kind: str) -> HelpdeskAsset | None:
    """The device of this person for this kind of problem (only when there is exactly one)."""
    if not person:
        return None
    rows = s.scalars(select(HelpdeskAsset).where(HelpdeskAsset.tenant_id == tenant, HelpdeskAsset.active.is_(True))).all()
    mine = [r for r in rows if r.user and r.user.lower() == person.lower().strip()]
    if kind:
        want = {kind, "laptop"} if kind == "pc" else {kind}
        mine = [r for r in mine if r.kind in want]
    return mine[0] if len(mine) == 1 else None


def save_asset(tenant: str, asset: str = "", **kw: Any) -> dict:
    on = today(tenant)
    with _LOCK, session() as s:
        a = _asset(s, tenant, asset) if asset else None
        if asset and a is None:
            raise HelpdeskError("Yeh device register mein nahi mila.")
        new = a is None
        if new:
            if not str(kw.get("name") or "").strip():
                raise HelpdeskError("Device ka naam chahiye (jaise 'Accounts PC', 'Reception printer').")
            st = _st(s, tenant)
            st.asset_seq = (st.asset_seq or 0) + 1
            a = HelpdeskAsset(tenant_id=tenant, tag=f"A-{st.asset_seq:03d}")
            s.add(a)
        if kw.get("kind"):
            k = str(kw["kind"]).lower().strip()
            a.kind = k if k in P.ASSET_KINDS else "other"
        for k in ("name", "brand", "model", "serial", "user", "location", "os"):
            if kw.get(k) is not None:
                setattr(a, k, scrub(str(kw[k]))[0].strip()[:120])
        if kw.get("notes") is not None:
            a.notes = scrub(str(kw["notes"]))[0][:500]
        for k in ("bought", "warranty_until", "amc_until"):
            if kw.get(k):
                d = _date(kw[k])
                if not d:
                    raise HelpdeskError(f"{k}: tareekh samajh nahi aayi.")
                setattr(a, k, d.isoformat())
        if kw.get("vendor"):
            v = _vendor(s, tenant, str(kw["vendor"]))
            if not v:
                raise HelpdeskError("Yeh vendor list mein nahi: pehle vendor jodiye.")
            a.vendor_id = v.id
            if not a.amc_until and v.amc_until and v.kind == "amc":
                a.amc_until = v.amc_until
        s.flush()
        out = _asset_view(s, a, on)
    say = f"{'Naya device' if new else 'Update'} {out['tag']}: {out['name']}" + (f" ({out['user']})" if out["user"] else "") + "."
    if out["advice"]:
        say += " " + " ".join(out["advice"][:2])
    return {"asset": out, "say": say}


def assets(tenant: str, kind: str = "") -> list[dict]:
    on = today(tenant)
    with session() as s:
        q = select(HelpdeskAsset).where(HelpdeskAsset.tenant_id == tenant, HelpdeskAsset.active.is_(True))
        if kind:
            q = q.where(HelpdeskAsset.kind == kind)
        return [_asset_view(s, a, on) for a in s.scalars(q.order_by(HelpdeskAsset.tag)).all()]


def asset_view(tenant: str, ref: str) -> dict:
    with session() as s:
        a = _asset(s, tenant, ref)
        if not a:
            raise HelpdeskError("Device nahi mila.")
        return _asset_view(s, a, today(tenant), with_history=True)


def remove_asset(tenant: str, ref: str) -> dict:
    with session() as s:
        a = _asset(s, tenant, ref)
        if not a:
            raise HelpdeskError("Device nahi mila.")
        a.active = False
        return {"removed": a.tag, "say": f"{a.tag} {a.name} register se hata diya (purane ticket rahenge)."}


def sync_pcs(tenant: str) -> dict:
    """Her paired PCs (Santosh Desktop) into the register: name + Windows version only (read-only, nothing changed on the PC)."""
    from ..pc import service as pcs
    added, updated = [], []
    with _LOCK, session() as s:
        for d in pcs.devices(tenant):
            a = s.scalars(select(HelpdeskAsset).where(HelpdeskAsset.tenant_id == tenant, HelpdeskAsset.pc_device == d["id"])).first()
            if a is None:
                st = _st(s, tenant)
                st.asset_seq = (st.asset_seq or 0) + 1
                a = HelpdeskAsset(tenant_id=tenant, tag=f"A-{st.asset_seq:03d}", kind="pc", name=str(d.get("name") or "PC")[:120],
                                  pc_device=d["id"])
                s.add(a)
                added.append(a.name)
            else:
                updated.append(a.name)
            if d.get("os"):
                a.os = str(d["os"])[:60]
    return {"added": added, "updated": updated,
            "say": (f"{len(added)} naye PC register mein jode" if added else "Koi naya PC nahi") + (f", {len(updated)} update." if updated else ".")}


# ---------------------------------------------------------------- tickets: the step runner
def _stats(s, tenant: str, cat: str) -> dict[str, tuple[int, int]]:
    pre = f"{tenant}:{cat}:"
    rows = s.scalars(select(HelpdeskStepStat).where(HelpdeskStepStat.key.like(pre + "%"))).all()
    return {r.key[len(pre):]: (r.tried, r.fixed) for r in rows}


def _learn(s, tenant: str, cat: str, step: str, fixed: bool) -> None:
    k = f"{tenant}:{cat}:{step}"[:140]
    r = s.get(HelpdeskStepStat, k)
    if not r:
        r = HelpdeskStepStat(key=k, tried=0, fixed=0)
        s.add(r)
    r.tried = (r.tried or 0) + 1
    r.fixed = (r.fixed or 0) + (1 if fixed else 0)


def _plan(s, tenant: str, cat: str) -> list[dict]:
    spec = P.playbook(cat)
    stats = _stats(s, tenant, cat)
    rows = []
    for i, st in enumerate(spec["steps"]):
        st = {**st, "result": None, "at": None, "note": "", "change": st.get("change", ""), "careful": bool(st.get("careful")),
              "admin": bool(st.get("admin")), "change_id": ""}
        tried, fixed = stats.get(st["id"], (0, 0))
        rate = (fixed + 1) / (tried + 2) if fixed else None      # only steps that really fixed it here move up
        if rate is not None:
            st["learned"] = f"Is office mein {fixed}/{tried} baar isi se theek hua."
        # safety / security playbooks keep their order; elsewhere what worked here comes first; careful steps always last
        if st["careful"]:
            key = (2, 0.0, i)
        elif spec.get("security") or cat == "ups_power":
            key = (1, 0.0, i)
        else:
            key = (1, -(rate or 0.0), i)
        rows.append((key, st))
    return [st for _, st in sorted(rows, key=lambda x: x[0])]


def _current(steps: list[dict]) -> dict | None:
    return next((st for st in steps if st.get("result") is None), None)


def _change_view(c: HelpdeskChange) -> dict:
    return {"id": c.id, "number": c.number, "ticket_id": c.ticket_id, "step_id": c.step_id, "kind": c.kind,
            "kind_label": P.CHANGE_LABEL.get(c.kind, c.kind), "what": c.what, "where": c.where, "how": c.how, "risk": c.risk,
            "undo": c.undo, "careful": c.careful, "admin": c.admin, "asked_by": c.asked_by, "hash": c.hash, "status": c.status,
            "reason": c.reason, "decided_at": _iso(c.decided_at), "done_note": c.done_note, "created_at": _iso(c.created_at)}


def _hash(*parts: str) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def _where(s, t: HelpdeskTicket) -> str:
    a = s.get(HelpdeskAsset, t.asset_id) if t.asset_id else None
    if a:
        return f"{a.tag} {a.name}" + (f" ({a.user})" if a.user else "")
    return t.person or "Office"


def _new_change(s, t: HelpdeskTicket, step_id: str, kind: str, what: str, how: str, risk: str = "", undo: str = "",
                careful: bool = False, admin: bool = False, asked_by: str = "Hoola") -> HelpdeskChange:
    st = _st(s, t.tenant_id)
    st.change_seq = (st.change_seq or 0) + 1
    c = HelpdeskChange(tenant_id=t.tenant_id, number=f"HC-{st.change_seq:04d}", ticket_id=t.id, step_id=step_id,
                       kind=kind if kind in P.CHANGE_LABEL else "other", what=what[:200], where=_where(s, t)[:160], how=how[:2000],
                       careful=careful, admin=admin, asked_by=asked_by[:80])
    c.risk = risk or ("Isme data / settings mit sakti hain: pehle backup." if careful else
                      "Yeh system ki setting badalta hai; theek na lage to wapas kiya ja sakta hai." if kind in ("setting", "network") else
                      "Program / driver badalta hai: sirf company ki apni site se.")
    c.undo = undo
    s.add(c)
    s.flush()
    c.hash = _hash(c.id, c.ticket_id, c.step_id, c.kind, c.what, c.where, c.how)
    return c


def _ticket(s, tenant: str, ref: str) -> HelpdeskTicket:
    t = None
    if ref:
        t = s.get(HelpdeskTicket, ref)
        if not t or t.tenant_id != tenant:
            t = s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == tenant, HelpdeskTicket.number == ref.upper().strip())).first()
    else:
        t = s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == tenant, HelpdeskTicket.status.in_(OPEN))
                      .order_by(HelpdeskTicket.updated_at.desc()).limit(1)).first()
    if not t:
        raise HelpdeskError("Yeh ticket nahi mila.")
    return t


def _view(s, t: HelpdeskTicket, full: bool = True) -> dict:
    steps = _j(t.steps, [])
    cur = _current(steps) if t.status in OPEN else None
    done = [x for x in steps if x.get("result")]
    ch = None
    if cur and cur.get("change_id"):
        c = s.get(HelpdeskChange, cur["change_id"])
        ch = _change_view(c) if c else None
    a = s.get(HelpdeskAsset, t.asset_id) if t.asset_id else None
    spec = P.playbook(t.category)
    n = clock()
    late = bool(t.status in OPEN and t.resolve_due and _aware(t.resolve_due) < n)
    out = {"id": t.id, "number": t.number, "category": t.category, "label": spec["label"], "title": t.title, "text": t.text,
           "details": _j(t.details, {}), "person": t.person, "raised_by": t.raised_by, "asset": ({"id": a.id, "tag": a.tag, "name": a.name,
           "user": a.user, "kind": a.kind} if a else None), "impact": t.impact, "urgency": t.urgency, "priority": t.priority,
           "priority_label": R.PRIORITY_LABEL.get(t.priority, t.priority), "security": t.security, "status": t.status,
           "status_label": STATUS_LABEL.get(t.status, t.status), "current": cur, "change": ch, "step_no": len(done) + 1 if cur else len(done),
           "total": len(steps), "parent_id": t.parent_id, "fixed_by": t.fixed_by, "resolution": t.resolution, "cost": t.cost,
           "respond_due": _iso(t.respond_due), "resolve_due": _iso(t.resolve_due), "late": late, "created_at": _iso(t.created_at),
           "resolved_at": _iso(t.resolved_at), "escalate_when": spec.get("escalate_when", []), "tell": spec.get("tell", [])}
    if full:
        out["steps"] = steps
        out["escalation"] = _j(t.escalation, {})
        out["log"] = _j(t.log, [])[-40:]
        if t.parent_id:
            p = s.get(HelpdeskTicket, t.parent_id)
            out["parent_number"] = p.number if p else ""
        out["children"] = [c.number for c in s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.parent_id == t.id)).all()]
    return out


def _step_say(st: dict | None, n: int, total: int, change: dict | None = None) -> str:
    if not st:
        return ""
    if change and change["status"] == "waiting":
        return (f"Step {n}/{total}: {st['title']}. Isme {P.CHANGE_LABEL.get(st['change'], 'badlaav').lower()} hai, isliye aapki haan ka "
                f"card ({change['number']}) bheja hai. Haan ke baad hi karenge.")
    s = f"Step {n}/{total}: {st['title']}. {st['how']}"
    if st.get("check"):
        s += f" Dekhiye: {st['check']}"
    if change and change["status"] == "approved":
        s = "Aapki haan mil gayi. " + s
    if st.get("admin"):
        s += " (Admin wale account se.)"
    if st.get("learned"):
        s += f" ({st['learned']})"
    return s + " Ho gaya to bataiye: theek hua ya nahi?"


def _gate(s, t: HelpdeskTicket, steps: list[dict], conv: str) -> HelpdeskChange | None:
    """If the current step changes the system, make sure a change card exists and waits; ticket -> waiting_haan."""
    cur = _current(steps)
    if not cur or not cur.get("change"):
        if t.status == "waiting_haan":
            t.status = "working"
        return None
    c = s.get(HelpdeskChange, cur["change_id"]) if cur.get("change_id") else None
    if c is None or c.status in ("stale",):
        c = _new_change(s, t, cur["id"], cur["change"], f"{cur['title']} ({P.playbook(t.category)['label']})", cur["how"],
                        careful=cur.get("careful", False), admin=cur.get("admin", False))
        cur["change_id"] = c.id
        t.steps = _dump(steps)
        _log(t, f"Haan ka card {c.number}: {cur['title']}")
        s.flush()
        _publish(t.tenant_id, "helpdesk_change", {"change": _change_view(c), "ticket": t.id, "number": t.number,
                                                  "say": f"{t.number}: '{cur['title']}' karne ke liye aapki haan chahiye."}, conv or t.conv)
    if c.status == "waiting":
        t.status = "waiting_haan"
    elif c.status == "approved" and t.status == "waiting_haan":
        t.status = "working"
    return c


def _card(s, t: HelpdeskTicket) -> dict:
    v = _view(s, t, full=False)
    return {"ticket": t.id, "number": t.number, "status": t.status, "status_label": v["status_label"], "title": t.title,
            "label": v["label"], "priority": t.priority, "current": v["current"], "change": v["change"], "step_no": v["step_no"],
            "total": v["total"], "person": t.person, "asset": v["asset"], "late": v["late"], "raised_by": t.raised_by}


def new_ticket(tenant: str, text: str, person: str = "", asset: str = "", category: str = "", impact: str = "", urgency: str = "",
               error: str = "", since: str = "", location: str = "", actor: str = "owner", conv: str = "") -> dict:
    clean, secret = scrub(text)
    clean = clean.strip()
    if not clean and not category:
        raise HelpdeskError("Kya dikkat hai? Apne shabdon mein bataiye (kaun sa device, kya error).")
    if str(actor or "").startswith("customer:"):
        raise HelpdeskError("Yeh office ka andar ka helpdesk hai.")
    guesses = P.detect(clean + " " + str(error or ""))
    cat = category if category in P.PLAYBOOKS or category == "other" else (guesses[0] if guesses else "other")
    spec = P.playbook(cat)
    danger = bool(R.DANGER_WORDS.search(clean))
    imp, urg = R.impact_of(clean, impact), R.urgency_of(clean, urgency)
    security = bool(spec.get("security"))
    pr = R.priority(imp, urg, security=False, danger=danger)
    by = actor_name(tenant, actor)
    n = now()
    with _LOCK, session() as s:
        st = _st(s, tenant)
        sla = _j(st.sla, {})
        a = _asset(s, tenant, asset) if asset else None
        if a is None:
            a = _asset_for(s, tenant, person, spec.get("asset", ""))
        # several people, same problem, last few hours = one known issue
        parent = None
        if cat != "other":
            recent = s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == tenant, HelpdeskTicket.category == cat,
                                                            HelpdeskTicket.status.in_(OPEN), HelpdeskTicket.parent_id == "")
                               .order_by(HelpdeskTicket.created_at)).all()
            recent = [r for r in recent if (_aware(r.created_at) or n) >= n - timedelta(hours=KNOWN_WINDOW_H)
                      and (not a or r.asset_id != a.id) and (r.person or "").lower() != (person or "").lower().strip()]
            if recent and cat in SHARED:
                parent = recent[0]
        if parent is not None and imp == "one":
            imp = "several"
            pr = R.priority(imp, urg, danger=danger)
        st.seq = (st.seq or 0) + 1
        details = {k: v for k, v in (("error", scrub(error)[0][:400]), ("since", str(since or "")[:80]), ("location", str(location or "")[:80])) if v}
        t = HelpdeskTicket(tenant_id=tenant, number=f"HD-{st.seq:04d}", category=cat, title=(clean or spec["label"])[:200], text=clean[:2000],
                           details=_dump(details), person=str(person or "").strip()[:80], raised_by=by, raised_actor=str(actor or "owner")[:60],
                           asset_id=a.id if a else "", impact=imp, urgency=urg, priority=pr, security=security, status="new",
                           parent_id=parent.id if parent else "", conv=conv or "")
        t.respond_due, t.resolve_due = R.due_times(n, pr, sla)
        steps = _plan(s, tenant, cat)
        t.steps = _dump(steps)
        s.add(t)
        s.flush()
        _log(t, f"Darj kiya ({R.PRIORITY_LABEL[pr]}): {t.title[:120]}", by)
        if parent is not None:
            _log(parent, f"Wahi dikkat {t.number} ({t.person or by}) ko bhi", "Hoola")
            parent.impact = "several" if parent.impact == "one" else parent.impact
        rep = _repeat(s, tenant, t.asset_id, exclude=t.id)
        ch = _gate(s, t, steps, conv)
        s.flush()
        v = _view(s, t)
        card = _card(s, t)
        sla_now = R.sla_for(pr, sla)
        parent_no = parent.number if parent else ""
    say = f"{v['number']} darj: {spec['label']} ({R.PRIORITY_LABEL[pr]}, jawab {_hrs(sla_now['respond_h'])} / theek {_hrs(sla_now['resolve_h'])} mein)."
    if secret:
        say += f" {secret.capitalize()} chat mein likha tha: hata diya, kahin save nahi kiya. Woh password ab badal dijiye."
    if danger:
        say = "Pehle suraksha: jalne ki gandh / chingari ho to main switch band, kuch mat chhuiye, electrician ko bulaiye. " + say
    if parent_no:
        say += f" Yahi dikkat abhi aur logon ko bhi hai ({parent_no} se joda): ek saath dekh rahe hain."
    if rep:
        say += f" Is device par 90 din mein {rep['count_90d']} baar pehle bhi dikkat hui ({', '.join(rep['numbers'][-3:])})."
    if cat == "account":
        say += " Password / OTP Hoola ko kabhi mat bataiye."
    say += " " + _step_say(v["current"], v["step_no"], v["total"], v["change"])
    others = [g for g in guesses[1:3] if g != cat]
    if others:
        say += " (Agar dikkat " + " / ".join(P.playbook(g)["label"] for g in others) + " hai to bataiye.)"
    _publish(tenant, "helpdesk_ticket", {**card, "say": say}, conv)
    return {"ticket": v, "say": say, "change": _change_view_dict(ch)}


def _change_view_dict(c) -> dict | None:
    return _change_view(c) if isinstance(c, HelpdeskChange) else None


def step(tenant: str, ticket: str = "", result: str = "not_fixed", note: str = "", step_id: str = "", actor: str = "owner",
         conv: str = "") -> dict:
    result = {"theek": "fixed", "theek hua": "fixed", "haan": "fixed", "yes": "fixed", "ho gaya": "fixed", "nahi": "not_fixed",
              "no": "not_fixed", "nahi hua": "not_fixed", "skip": "skipped", "chhodo": "skipped", "nahi ho paya": "cant"}.get(
        str(result or "").lower().strip(), str(result or "").lower().strip())
    if result not in RESULTS:
        raise HelpdeskError("result = fixed | not_fixed | skipped | cant")
    by = actor_name(tenant, actor)
    note = scrub(note)[0][:300]
    with _LOCK, session() as s:
        t = _ticket(s, tenant, ticket)
        if t.status not in OPEN:
            return {"ticket": _view(s, t), "say": f"{t.number} pehle se '{STATUS_LABEL.get(t.status)}' hai."}
        steps = _j(t.steps, [])
        st = next((x for x in steps if x["id"] == step_id and x.get("result") is None), None) if step_id else None
        st = st or _current(steps)
        if not st:
            raise HelpdeskError("Saare steps ho chuke; technician ko bhejiye (escalate).")
        if st.get("change") and result in ("fixed", "not_fixed"):
            c = s.get(HelpdeskChange, st.get("change_id") or "")
            approved = c is not None and c.status in ("approved", "done", "failed")
            if not approved and not is_owner(actor):
                raise HelpdeskError(f"'{st['title']}' system badalta hai: pehle owner ki haan (card {c.number if c else ''}). Tab tak mat kijiye.")
            if not approved:
                note = (note + " " if note else "") + "(Owner ne khud kiya)"
                if c and c.status == "waiting":
                    c.status, c.reason, c.decided_at = "approved", "Owner ne khud kiya", now()
            if c and c.status == "approved":
                c.status, c.done_note = ("done" if result == "fixed" else "failed"), note[:300]
        st["result"], st["at"], st["note"] = result, now().isoformat(timespec="seconds"), note
        if result in ("fixed", "not_fixed"):
            _learn(s, tenant, t.category, st["id"], result == "fixed")
        if not t.responded_at:
            t.responded_at = now()
        _log(t, f"{st['title']}: {dict(fixed='theek hua', not_fixed='nahi hua', skipped='chhoda', cant='nahi ho paya')[result]}"
                + (f" ({note[:80]})" if note else ""), by)
        if result == "fixed":
            t.status, t.fixed_by, t.resolved_at = "resolved", st["id"], now()
            t.resolution = f"{st['title']}" + (f": {note}" if note else "")
            t.steps = _dump(steps)
            kids = _resolve_children(s, t)
            v, card = _view(s, t), _card(s, t)
            say = f"Badhiya! {t.number} '{st['title']}' se theek ho gaya. Agli baar yahi pehle aayega." + (
                f" Saath jude {', '.join(kids)} bhi theek maan liye (galat ho to 'reopen')." if kids else "")
            _publish(tenant, "helpdesk_ticket", {**card, "say": say}, conv or t.conv)
            return {"ticket": v, "resolved": True, "say": say}
        if t.status == "new":
            t.status = "working"
        t.steps = _dump(steps)
        ch = _gate(s, t, steps, conv)
        v, card = _view(s, t), _card(s, t)
        tid = t.id
    if v["current"]:
        say = _step_say(v["current"], v["step_no"], v["total"], v["change"])
        _publish(tenant, "helpdesk_ticket", {**card, "say": say}, conv)
        return {"ticket": v, "say": say, "change": _change_view_dict(ch)}
    out = escalate(tenant, tid, actor=actor, conv=conv)
    out["say"] = "Office mein karne wale saare upay ho gaye. " + out["say"]
    return out


def _resolve_children(s, t: HelpdeskTicket) -> list[str]:
    out = []
    for c in s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.parent_id == t.id, HelpdeskTicket.status.in_(OPEN))).all():
        c.status, c.resolved_at, c.fixed_by = "resolved", now(), t.fixed_by
        c.resolution = f"{t.number} ke saath theek hua"
        _log(c, c.resolution)
        out.append(c.number)
    return out


def request_change(tenant: str, ticket: str, what: str, how: str = "", kind: str = "setting", risk: str = "", undo: str = "",
                   careful: bool = False, actor: str = "owner", conv: str = "") -> dict:
    """A change outside the playbook (e.g. router DNS, a new antivirus). Only makes the card: her tap decides."""
    what, _ = scrub(what)
    how, _ = scrub(how)
    if not what.strip():
        raise HelpdeskError("Kya badalna hai, ek line mein.")
    with _LOCK, session() as s:
        t = _ticket(s, tenant, ticket)
        dup = s.scalars(select(HelpdeskChange).where(HelpdeskChange.ticket_id == t.id, HelpdeskChange.status == "waiting",
                                                     HelpdeskChange.what == what.strip()[:200])).first()
        c = dup or _new_change(s, t, "", kind, what.strip(), how.strip() or what.strip(), risk=scrub(risk)[0], undo=scrub(undo)[0],
                               careful=bool(careful), asked_by=actor_name(tenant, actor))
        if not dup:
            _log(t, f"Haan ka card {c.number}: {c.what}", actor_name(tenant, actor))
        t.status = "waiting_haan"
        cv = _change_view(c)
        number = t.number
    if not dup:
        _publish(tenant, "helpdesk_change", {"change": cv, "ticket": cv["ticket_id"], "number": number,
                                             "say": f"{number}: '{cv['what']}' ke liye aapki haan chahiye."}, conv)
    return {"change": cv, "needs_tap": True,
            "say": f"Card {cv['number']} bheja: '{cv['what']}'. Hoola khud kuch nahi badalta; aapki haan ke baad hi."}


def decide_change(tenant: str, change: str, yes: bool, hash: str = "", reason: str = "", by_tap: bool = False, conv: str = "") -> dict:
    """ONLY from her tap in the app (the API passes by_tap=True). The tool can never call this."""
    if not by_tap:
        raise HelpdeskError("Yeh faisla sirf owner app mein card par tap karke karti hain.")
    with _LOCK, session() as s:
        c = s.get(HelpdeskChange, change)
        if not c or c.tenant_id != tenant:
            raise HelpdeskError("Card nahi mila.")
        if c.status != "waiting":
            return {"change": _change_view(c), "say": f"Is card par faisla ho chuka ({c.status})."}
        if hash and hash != c.hash:
            raise HelpdeskError("Card badal gaya hai: naya card dekhkar faisla kijiye.")
        c.status, c.decided_at, c.reason = ("approved" if yes else "rejected"), now(), scrub(reason)[0][:300]
        t = s.get(HelpdeskTicket, c.ticket_id)
        say = ""
        if t is not None:
            steps = _j(t.steps, [])
            st = next((x for x in steps if x.get("change_id") == c.id), None)
            _log(t, f"{c.number} par owner: {'Haan' if yes else 'Mana'}" + (f" ({c.reason})" if c.reason else ""), "Owner")
            if yes:
                t.status = "working"
                say = f"Haan mili ({c.number}). Ab: {c.how}" + (f" Dekhiye: {st['check']}" if st and st.get("check") else "") + \
                      " Ho jaye to batana: theek hua ya nahi."
            else:
                if st and st.get("result") is None:
                    st["result"], st["at"], st["note"] = "skipped", now().isoformat(timespec="seconds"), "Owner ne mana kiya"
                t.status = "working"
                t.steps = _dump(steps)
                _gate(s, t, steps, conv)
                v = _view(s, t, full=False)
                say = f"Theek hai, '{c.what}' nahi karenge. " + (_step_say(v["current"], v["step_no"], v["total"], v["change"]) if v["current"]
                                                                  else "")
                out_of_steps = st is not None and not v["current"]
            card = _card(s, t)
        cv = _change_view(c)
    if t is not None and not yes and locals().get("out_of_steps"):
        out = escalate(tenant, t.id, conv=conv)
        return {"change": cv, "ticket": out["ticket"], "escalation": out["escalation"],
                "say": f"Theek hai, '{cv['what']}' nahi karenge. Office ke upay khatam: " + out["say"]}
    if t is not None:
        _publish(tenant, "helpdesk_ticket", {**card, "say": say}, conv or (t.conv if t else ""))
    return {"change": cv, "say": say or "Faisla save."}


def change_done(tenant: str, change: str, ok: bool, note: str = "", actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        c = s.get(HelpdeskChange, change)
        if not c or c.tenant_id != tenant:
            raise HelpdeskError("Card nahi mila.")
        if c.status not in ("approved",):
            raise HelpdeskError("Pehle owner ki haan chahiye." if c.status == "waiting" else f"Card '{c.status}' hai.")
        ticket, step_id = c.ticket_id, c.step_id
        if not step_id:
            c.status, c.done_note = ("done" if ok else "failed"), scrub(note)[0][:300]
    if step_id:
        return step(tenant, ticket, "fixed" if ok else "not_fixed", note, step_id, actor=actor, conv=conv)
    if ok:
        return resolve(tenant, ticket, note or "Badlaav ke baad theek", actor=actor, conv=conv)
    return {"say": "Badlaav se bhi nahi hua: technician ko bhejiye (escalate)."}


def changes(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(HelpdeskChange).where(HelpdeskChange.tenant_id == tenant)
        if status:
            q = q.where(HelpdeskChange.status == status)
        return [_change_view(c) for c in s.scalars(q.order_by(HelpdeskChange.created_at.desc()).limit(50)).all()]


# ---------------------------------------------------------------- escalation to a technician
def _maps(tenant: str, q: str) -> str:
    try:
        from .. import maps
        return maps.search_link(q, maps.where_am_i(tenant))
    except Exception:
        return "https://www.google.com/maps/search/" + quote(q)


def _pick_vendor(s, tenant: str, t: HelpdeskTicket, a: HelpdeskAsset | None, ref: str, on: date) -> HelpdeskVendor | None:
    if ref:
        v = _vendor(s, tenant, ref)
        if not v:
            raise HelpdeskError("Yeh vendor list mein nahi.")
        return v
    rows = s.scalars(select(HelpdeskVendor).where(HelpdeskVendor.tenant_id == tenant)).all()
    want = P.playbook(t.category).get("escalate", "it")
    if a and a.vendor_id:
        v = s.get(HelpdeskVendor, a.vendor_id)
        if v and want not in ("isp", "electrician", "tally_partner"):
            return v
    kind = a.kind if a else P.playbook(t.category).get("asset", "")
    for f in (lambda v: v.kind == want, lambda v: kind and kind in _j(v.covers, []),
              lambda v: v.kind == "amc" and (_date(v.amc_until) or on) >= on and want in ("it", "printer")):
        hit = [v for v in rows if f(v)]
        if hit:
            return hit[0]
    return None


def escalate(tenant: str, ticket: str = "", vendor: str = "", actor: str = "owner", conv: str = "") -> dict:
    on = today(tenant)
    with _LOCK, session() as s:
        t = _ticket(s, tenant, ticket)
        a = s.get(HelpdeskAsset, t.asset_id) if t.asset_id else None
        v = _pick_vendor(s, tenant, t, a, vendor, on)
        st = _st(s, tenant)
        spec = P.playbook(t.category)
        tried = [x["title"] for x in _j(t.steps, []) if x.get("result") in ("not_fixed", "cant")]
        det = _j(t.details, {})
        dev = ""
        if a:
            dev = " ".join(x for x in (a.name, f"({a.brand} {a.model})".replace("( )", "").strip() if (a.brand or a.model) else "") if x)
            if a.serial:
                dev += f", serial {a.serial}"
            w, amc = _date(a.warranty_until), _date(a.amc_until)
            if w and w >= on:
                dev += f", warranty {w.strftime('%d-%m-%Y')} tak"
            if amc and amc >= on:
                dev += f", AMC {amc.strftime('%d-%m-%Y')} tak"
        lines = [f"Namaste{(' ' + v.name) if v else ''}, {st.office_name or '[office ka naam]'} se.",
                 f"Ticket {t.number}: {spec['label']}." + (f" Device: {dev}." if dev else ""),
                 f"Dikkat: {t.title}" + (f" (error: {det['error']})" if det.get("error") else "") + (f", {det['since']} se" if det.get("since") else "") + ".",
                 (f"Humne try kiya: {', '.join(tried)}." if tried else ""),
                 f"Kab aa sakte hain? Address: {det.get('location') or '[office ka pata]'}."]
        text = "\n".join(x for x in lines if x)
        w_ok = bool(a and _date(a.warranty_until) and _date(a.warranty_until) >= on)
        esc: dict[str, Any] = {"vendor": _vendor_view(v, on) if v else None, "text": text, "tell": spec.get("tell", []),
                               "why": spec.get("escalate_when", []), "links": [], "notes": [], "at": now().isoformat(timespec="seconds")}
        if v and v.phone:
            esc["wa_link"] = f"https://wa.me/91{v.phone}?text={quote(text)}"
            esc["tel"] = f"tel:+91{v.phone}"
        if v and v.email:
            esc["mailto"] = f"mailto:{v.email}?subject={quote(t.number + ' ' + spec['label'])}&body={quote(text)}"
        if not v:
            esc["notes"].append(f"{P.VENDOR_LABEL.get(spec.get('escalate', 'it'))} list mein nahi: 'vendor' se jodiye.")
            esc["links"].append({"label": "Paas ke computer / printer repair", "url": _maps(tenant, "computer repair service")})
        if w_ok and a and a.brand:
            esc["notes"].append(f"Warranty mein hai: {a.brand} service centre muft dekhega (bill / serial saath).")
            esc["links"].append({"label": f"{a.brand} service centre", "url": _maps(tenant, f"{a.brand} service centre")})
        if spec.get("escalate") == "isp":
            esc["notes"].append("ISP ki shikayat par complaint / docket number zaroor likh lijiye; 'ticket' mein daal dijiye.")
        esc["notes"].append("Technician ko PC ka password / Wi-Fi password khud saamne type kijiye; likhkar mat dijiye. Remote (AnyDesk) "
                            "sirf apne jaane-pehchane vendor ko, aur kaam ke baad app band.")
        if v and v.sla_hours:
            esc["notes"].append(f"Contract mein {_hrs(v.sla_hours)} mein aane ka vaada hai.")
        t.escalation = _dump(esc)
        t.status = "waiting_tech"
        if not t.responded_at:
            t.responded_at = now()
        _log(t, f"Technician ke liye taiyaar: {v.name if v else 'vendor chuna nahi'}", actor_name(tenant, actor))
        cv = _view(s, t)
        card = _card(s, t)
        conv0 = t.conv
    say = (f"{cv['number']} ab technician ka kaam hai. " + (f"{esc['vendor']['name']} ko bhejne ka message taiyaar (aap bhejengi)."
                                                           if esc["vendor"] else "Vendor list mein nahi: paas ki dukaan ka link card par.")
           + " Unhe yeh batana: " + text.replace("\n", " "))
    _publish(tenant, "helpdesk_escalate", {**card, "escalation": esc, "say": say}, conv or conv0)
    return {"ticket": cv, "escalation": esc, "say": say}


def tech_update(tenant: str, ticket: str, note: str = "", fixed: bool = True, cost: float | None = None, actor: str = "owner",
                conv: str = "") -> dict:
    with _LOCK, session() as s:
        t = _ticket(s, tenant, ticket)
        note = scrub(note)[0][:400]
        if cost not in (None, ""):
            t.cost = max(0.0, float(cost))
        _log(t, "Technician: " + (note or ("theek kiya" if fixed else "abhi nahi hua")) + (f" (kharcha ₹{t.cost:g})" if t.cost else ""),
             actor_name(tenant, actor))
        if fixed:
            t.status, t.resolved_at, t.fixed_by = "resolved", now(), "technician"
            t.resolution = "Technician: " + (note or "theek kiya")
            kids = _resolve_children(s, t)
        else:
            t.status, kids = "waiting_tech", []
        rep = _repeat(s, tenant, t.asset_id)
        a = s.get(HelpdeskAsset, t.asset_id) if t.asset_id else None
        adv = _advice(a, rep, today(tenant)) if a else []
        v, card = _view(s, t), _card(s, t)
    say = (f"{v['number']} technician ne theek kiya." if fixed else f"{v['number']} abhi technician ke paas.") + (
        f" Saath jude {', '.join(kids)} bhi theek." if kids else "") + (" " + " ".join(adv[:2]) if fixed and adv else "")
    _publish(tenant, "helpdesk_ticket", {**card, "say": say}, conv)
    return {"ticket": v, "say": say, "advice": adv}


def resolve(tenant: str, ticket: str, note: str = "", actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        t = _ticket(s, tenant, ticket)
        if t.status not in OPEN:
            return {"ticket": _view(s, t), "say": f"{t.number} pehle se {STATUS_LABEL.get(t.status)}."}
        t.status, t.resolved_at = "resolved", now()
        t.resolution = scrub(note)[0][:400] or "Theek ho gaya"
        t.fixed_by = t.fixed_by or "other"
        _log(t, "Theek: " + t.resolution, actor_name(tenant, actor))
        kids = _resolve_children(s, t)
        v, card = _view(s, t), _card(s, t)
    say = f"{v['number']} theek ho gaya." + (f" {', '.join(kids)} bhi." if kids else "")
    _publish(tenant, "helpdesk_ticket", {**card, "say": say}, conv)
    return {"ticket": v, "say": say}


def set_status(tenant: str, ticket: str, status: str, actor: str = "owner") -> dict:
    if status not in ("closed", "reopen"):
        raise HelpdeskError("status = closed | reopen")
    with _LOCK, session() as s:
        t = _ticket(s, tenant, ticket)
        if status == "closed":
            t.status = "closed"
            for c in s.scalars(select(HelpdeskChange).where(HelpdeskChange.ticket_id == t.id, HelpdeskChange.status == "waiting")).all():
                c.status = "stale"
            _log(t, "Band kiya", actor_name(tenant, actor))
        else:
            t.status, t.resolved_at = "working", None
            _log(t, "Dobara khola", actor_name(tenant, actor))
        return {"ticket": _view(s, t), "say": f"{t.number}: {STATUS_LABEL[t.status]}."}


def update_ticket(tenant: str, ticket: str, actor: str = "owner", **kw: Any) -> dict:
    with _LOCK, session() as s:
        t = _ticket(s, tenant, ticket)
        det = _j(t.details, {})
        for k in ("error", "since", "location", "tried", "note"):
            if kw.get(k):
                det[k] = scrub(str(kw[k]))[0][:400]
        t.details = _dump(det)
        if kw.get("person"):
            t.person = str(kw["person"]).strip()[:80]
        if kw.get("asset"):
            a = _asset(s, tenant, str(kw["asset"]))
            if not a:
                raise HelpdeskError("Device register mein nahi.")
            t.asset_id = a.id
        changed = False
        for k, allowed in (("impact", R.IMPACTS), ("urgency", R.URGENCIES)):
            if kw.get(k) in allowed and getattr(t, k) != kw[k]:
                setattr(t, k, kw[k])
                changed = True
        if changed:
            pr = R.priority(t.impact, t.urgency)
            if t.security and pr in ("P3", "P4"):
                pr = "P2"
            if pr != t.priority:
                t.priority = pr
                t.respond_due, t.resolve_due = R.due_times(_aware(t.created_at) or now(), pr, _j(_st(s, tenant).sla, {}))
        _log(t, "Detail joda", actor_name(tenant, actor))
        v = _view(s, t)
    return {"ticket": v, "say": f"{v['number']} update ({v['priority_label']})."}


def get_ticket(tenant: str, ticket: str = "") -> dict:
    with session() as s:
        return _view(s, _ticket(s, tenant, ticket))


def tickets(tenant: str, status: str = "", limit: int = 40) -> list[dict]:
    with session() as s:
        q = select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == tenant)
        if status == "open":
            q = q.where(HelpdeskTicket.status.in_(OPEN))
        elif status:
            q = q.where(HelpdeskTicket.status == status)
        rows = s.scalars(q.order_by(HelpdeskTicket.created_at.desc()).limit(max(1, min(int(limit or 40), 200)))).all()
        out = [_view(s, t, full=False) for t in rows]
    order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    return sorted(out, key=lambda v: (v["status"] not in OPEN, order.get(v["priority"], 9), v["created_at"]))


def known(tenant: str, category: str = "") -> list[dict]:
    """What fixed what in this office."""
    pre = f"{tenant}:"
    with session() as s:
        rows = s.scalars(select(HelpdeskStepStat).where(HelpdeskStepStat.key.like(pre + (category + ":" if category else "") + "%"))).all()
    out = []
    for r in rows:
        _, cat, stp = r.key.split(":", 2)
        title = next((x["title"] for x in P.playbook(cat)["steps"] if x["id"] == stp), stp)
        out.append({"category": cat, "label": P.playbook(cat)["label"], "step": stp, "title": title, "tried": r.tried, "fixed": r.fixed})
    return sorted(out, key=lambda x: (-x["fixed"], x["tried"]))


# ---------------------------------------------------------------- security: phishing / incidents
_DID = ("clicked", "entered_password", "opened_attachment", "money", "gave_otp", "remote_access")


def _inc_view(tenant: str, i: HelpdeskIncident) -> dict:
    n = now()
    due = _aware(i.report_due)
    return {"id": i.id, "ticket_id": i.ticket_id, "kind": i.kind, "kind_label": R.PHISH_KIND.get(i.kind, i.kind), "sender": i.sender,
            "summary": i.summary, "analysis": _j(i.analysis, {}), "did": _j(i.did, {}), "personal_data": i.personal_data,
            "cert_in": _j(i.cert_in, {}), "detected_at": _iso(i.detected_at), "detected_local": _local(tenant, i.detected_at),
            "report_due": _iso(due), "report_due_local": _local(tenant, due), "hours_left": round((due - n).total_seconds() / 3600, 1) if due and not i.reported_at else None,
            "reported_at": _iso(i.reported_at), "reported_ref": i.reported_ref, "status": i.status}


def report_phish(tenant: str, text: str, sender: str = "", links: list | None = None, attachments: list | None = None,
                 kind: str = "phishing", person: str = "", asset: str = "", personal_data: bool = False, actor: str = "owner",
                 conv: str = "", **did_kw: Any) -> dict:
    """A suspicious mail / SMS / WhatsApp or a security incident. The text is DATA: read for red flags, links never opened."""
    body, _ = scrub(text)
    sender = scrub(sender)[0][:200]
    if not body.strip() and not sender and kind == "phishing":
        raise HelpdeskError("Mail / message ka text (ya bhejne wale ka pata) daaliye; link mat kholiye.")
    kind = kind if kind in R.PHISH_KIND else "other"
    did = {k: bool(did_kw.get(k)) for k in _DID}
    an = R.phish_check(body, sender, [str(x) for x in (links or [])][:20], [str(x) for x in (attachments or [])][:10]) if kind == "phishing" else \
        {"verdict": "incident", "flags": [], "hosts": [], "say": ""}
    harmed = any(did.values()) or kind != "phishing"
    st = settings(tenant)
    ci = R.cert_in(st["entity"], kind, did)
    dp = R.dpdp(bool(personal_data), today(tenant))
    detected = now()
    words = f"{R.PHISH_KIND[kind]}: {sender or ''} " + ("(click / password / paisa)" if harmed else "(sirf mila)")
    out_t = new_ticket(tenant, words.strip(), person=person, asset=asset, category="security",
                       impact="one", urgency="high" if harmed else "normal", actor=actor, conv=conv)
    tid = out_t["ticket"]["id"]
    with _LOCK, session() as s:
        t = s.get(HelpdeskTicket, tid)
        pr = R.priority(t.impact, t.urgency, security=harmed, money_or_data=did["money"] or did["gave_otp"] or bool(personal_data))
        if pr != t.priority:
            t.priority = pr
            t.respond_due, t.resolve_due = R.due_times(_aware(t.created_at) or detected, pr, _j(_st(s, tenant).sla, {}))
        t.security = True
        t.details = _dump({**_j(t.details, {}), "did": did, "verdict": an["verdict"]})
        i = HelpdeskIncident(tenant_id=tenant, ticket_id=tid, kind=kind, sender=sender, summary=body[:3000], analysis=_dump(an),
                             did=_dump(did), personal_data=bool(personal_data), cert_in=_dump(ci), detected_at=detected)
        if harmed and ci.get("applies") is not False:
            i.report_due = detected + timedelta(hours=R.CERT_IN["hours"])
        s.add(i)
        s.flush()
        inc = _inc_view(tenant, i)
        _log(t, f"Security: {an['verdict']} ({len(an['flags'])} nishaan)" + (", CERT-In 6 ghante" if i.report_due else ""))
    actions = R.phish_actions(did)
    draft = R.cert_in_text(st, {"kind": kind, "kind_label": R.PHISH_KIND[kind], "detected": _local(tenant, detected),
                                "summary": (an.get("say") or "") + " " + ", ".join(f["text"] for f in an["flags"][:3]),
                                "indicators": ", ".join([sender] + an.get("hosts", [])[:5]).strip(", "),
                                "actions": "; ".join(actions[:3]), "personal_data": personal_data,
                                "systems": out_t["ticket"]["asset"]["name"] if out_t["ticket"].get("asset") else person})
    say = an.get("say", "") + (" " + " ".join(f["text"] for f in an["flags"][:3]) if an["flags"] else "")
    say += " Abhi: " + actions[0]
    if inc["report_due"]:
        say += (f" CERT-In: {ci['why']} Aakhri samay {inc['report_due_local']}. Report ka draft card par ({R.CERT_IN['email']}, "
                f"{R.CERT_IN['phone']}); aap apne email se bhejiye.") if ci.get("applies") else \
               f" CERT-In: {ci['why']} Draft card par hai."
    elif ci.get("applies") is None:
        say += " " + ci["why"]
    if dp:
        say += " " + dp["say"]
    payload = {"kind": "security", "incident": inc, "actions": actions, "cert_in_draft": draft if harmed or ci.get("applies") is None else "",
               "ticket": tid, "number": out_t["ticket"]["number"], "say": say.strip()}
    _publish(tenant, "helpdesk_alert", payload, conv)
    return {"incident": inc, "ticket": get_ticket(tenant, tid), "actions": actions, "cert_in": ci, "dpdp": dp,
            "cert_in_draft": payload["cert_in_draft"], "say": say.strip()}


def cert_in_reported(tenant: str, incident: str, ref: str = "") -> dict:
    with session() as s:
        i = s.get(HelpdeskIncident, incident)
        if not i or i.tenant_id != tenant:
            raise HelpdeskError("Incident nahi mila.")
        i.reported_at, i.reported_ref, i.status = clock(), scrub(ref)[0][:120], "reported"
        t = s.get(HelpdeskTicket, i.ticket_id) if i.ticket_id else None
        if t:
            _log(t, "CERT-In ko report kiya" + (f" ({i.reported_ref})" if i.reported_ref else ""), "Owner")
        due = _aware(i.report_due)
        late = bool(due and _aware(i.reported_at) > due)
        v = _inc_view(tenant, i)
    return {"incident": v, "say": "CERT-In report darj." + (" (6 ghante ke baad gaya: wajah mail mein likh dijiye.)" if late else "")}


def incidents(tenant: str, open_only: bool = False) -> list[dict]:
    with session() as s:
        q = select(HelpdeskIncident).where(HelpdeskIncident.tenant_id == tenant)
        if open_only:
            q = q.where(HelpdeskIncident.status == "open")
        return [_inc_view(tenant, i) for i in s.scalars(q.order_by(HelpdeskIncident.detected_at.desc()).limit(50)).all()]


# ---------------------------------------------------------------- the day + worker
def day(tenant: str) -> dict:
    on = today(tenant)
    n = clock()
    with session() as s:
        rows = s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == tenant, HelpdeskTicket.status.in_(OPEN))).all()
        open_v = [_view(s, t, full=False) for t in rows]
        assets_all = s.scalars(select(HelpdeskAsset).where(HelpdeskAsset.tenant_id == tenant, HelpdeskAsset.active.is_(True))).all()
        expiring, repeat, win10 = [], [], []
        for a in assets_all:
            for k, label in (("warranty_until", "warranty"), ("amc_until", "AMC")):
                d = _date(getattr(a, k))
                if d and 0 <= (d - on).days <= 30:
                    expiring.append({"tag": a.tag, "name": a.name, "what": label, "on": d.isoformat(), "days": (d - on).days})
            rep = _repeat(s, tenant, a.id)
            if rep and rep["count_90d"] >= 3:
                repeat.append({"tag": a.tag, "name": a.name, **rep})
            if re.search(r"windows\s*(7|8|10)\b", (a.os or "").lower()):
                win10.append({"tag": a.tag, "name": a.name, "os": a.os})
        for v in s.scalars(select(HelpdeskVendor).where(HelpdeskVendor.tenant_id == tenant)).all():
            d = _date(v.amc_until)
            if d and 0 <= (d - on).days <= 30:
                expiring.append({"tag": "", "name": v.name, "what": "AMC contract", "on": d.isoformat(), "days": (d - on).days})
        waiting = [_change_view(c) for c in s.scalars(select(HelpdeskChange).where(HelpdeskChange.tenant_id == tenant,
                                                                                   HelpdeskChange.status == "waiting")).all()]
        incs = [_inc_view(tenant, i) for i in s.scalars(select(HelpdeskIncident).where(HelpdeskIncident.tenant_id == tenant,
                                                                                      HelpdeskIncident.status == "open")).all()]
        week = s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == tenant)).all()
        done7 = [t for t in week if t.resolved_at and (_aware(t.resolved_at) or n) >= n - timedelta(days=7)]
    late = [v for v in open_v if v["late"]]
    cert = [i for i in incs if i["report_due"] and not i["reported_at"]]
    bits = []
    if open_v:
        bits.append(f"{len(open_v)} ticket khule" + (f" ({len(late)} der se)" if late else ""))
    if waiting:
        bits.append(f"{len(waiting)} badlaav aapki haan ke intezaar mein")
    if cert:
        bits.append("CERT-In report baaki: " + ", ".join(f"{i['kind_label']} ({i['report_due_local']} tak)" for i in cert[:2]))
    tech = [v for v in open_v if v["status"] == "waiting_tech"]
    if tech:
        bits.append(f"{len(tech)} technician ke paas")
    if expiring:
        bits.append("Khatam ho raha: " + ", ".join(f"{e['name']} {e['what']} {e['days']} din" for e in expiring[:3]))
    if repeat:
        bits.append("Baar baar kharab: " + ", ".join(f"{r['name']} ({r['count_90d']} baar)" for r in repeat[:3]))
    if win10:
        bits.append(f"{len(win10)} PC purane Windows par")
    say = ("IT: " + "; ".join(bits) + ".") if bits else "IT: sab theek, koi khula ticket nahi."
    order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    return {"say": say, "open": sorted(open_v, key=lambda v: (order.get(v["priority"], 9), v["created_at"])), "late": late,
            "waiting_haan": waiting, "incidents": incs, "expiring": expiring, "repeat": repeat, "old_windows": win10,
            "resolved_7d": len(done7), "settings": settings(tenant)}


def overview(tenant: str) -> dict:
    d = day(tenant)
    return {**d, "tickets": tickets(tenant, limit=60), "assets": assets(tenant), "vendors": vendors(tenant), "changes": changes(tenant),
            "playbooks": playbook_list(), "known": known(tenant)[:20]}


def playbook_list() -> list[dict]:
    return [{"id": k, "label": v["label"], "steps": len(v["steps"]), "security": bool(v.get("security")),
             "escalate": P.VENDOR_LABEL.get(v.get("escalate", "it"))} for k, v in P.PLAYBOOKS.items()]


def playbook_view(cat: str) -> dict:
    spec = P.playbook(cat)
    return {"id": cat, **{k: v for k, v in spec.items() if k != "words"}, "escalate_label": P.VENDOR_LABEL.get(spec.get("escalate", "it"))}


def _tenants() -> list[str]:
    with session() as s:
        ids = {r for r in s.scalars(select(HelpdeskTicket.tenant_id).where(HelpdeskTicket.status.in_(OPEN))).all()}
        ids |= {r for r in s.scalars(select(HelpdeskIncident.tenant_id).where(HelpdeskIncident.status == "open")).all()}
        ids |= {r for r in s.scalars(select(HelpdeskSettings.tenant_id)).all()}
    return sorted(ids)


def tick(when: datetime | None = None) -> dict:
    """Worker, every minute: SLA alerts (once each), CERT-In 6-hour reminders, the morning IT note (once a day, only when there is
    something to say)."""
    n = _aware(when) or now()
    out = {"sla": 0, "cert_in": 0, "morning": 0}
    for tenant in _tenants():
        try:
            alerts = []
            with _LOCK, session() as s:
                for t in s.scalars(select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == tenant, HelpdeskTicket.status.in_(OPEN))).all():
                    told = _j(t.told, {})
                    if t.status in ("new",) and not t.responded_at and t.respond_due and _aware(t.respond_due) < n and "respond" not in told:
                        told["respond"] = n.isoformat()
                        alerts.append({"kind": "sla", "ticket": t.id, "number": t.number,
                                       "say": f"{t.number} ({t.priority}) par abhi tak kisi ne jawab nahi diya: {t.title[:80]}."})
                    if t.resolve_due and _aware(t.resolve_due) < n and "resolve" not in told and t.status != "waiting_haan":
                        told["resolve"] = n.isoformat()
                        alerts.append({"kind": "sla", "ticket": t.id, "number": t.number,
                                       "say": f"{t.number} ({t.priority}) theek hone ka samay nikal gaya: {t.title[:80]}."
                                              + (" Technician ko yaad dilaiye." if t.status == "waiting_tech" else " Technician ko bhejein?")})
                    t.told = _dump(told)
                for i in s.scalars(select(HelpdeskIncident).where(HelpdeskIncident.tenant_id == tenant, HelpdeskIncident.status == "open",
                                                                  HelpdeskIncident.report_due.is_not(None))).all():
                    due = _aware(i.report_due)
                    left = (due - n).total_seconds() / 3600
                    if left <= 0 and i.reminded != "late":
                        i.reminded = "late"
                        alerts.append({"kind": "cert_in", "incident": i.id, "say": "CERT-In ke 6 ghante poore: report abhi bhi bhej dijiye "
                                                                                 f"({R.CERT_IN['email']}), der ki wajah likhkar."})
                    elif 0 < left <= 2 and i.reminded == "":
                        i.reminded = "4h"
                        alerts.append({"kind": "cert_in", "incident": i.id,
                                       "say": f"CERT-In report ke {left:.1f} ghante bache ({R.PHISH_KIND.get(i.kind, i.kind)})."})
            for a in alerts:
                out["sla" if a["kind"] == "sla" else "cert_in"] += 1
                _publish(tenant, "helpdesk_alert", a)
            if _morning_due(tenant, n):
                d = day(tenant)
                from ..life import tz_of
                with session() as s:
                    _st(s, tenant).last_morning = n.astimezone(tz_of(tenant)).date().isoformat()
                if d["open"] or d["waiting_haan"] or d["incidents"] or d["expiring"] or d["repeat"]:
                    _publish(tenant, "helpdesk_day", {"say": d["say"], "open": len(d["open"]), "late": len(d["late"]),
                                                      "waiting_haan": len(d["waiting_haan"]), "expiring": d["expiring"][:5],
                                                      "repeat": d["repeat"][:3]})
                    out["morning"] += 1
        except Exception:
            log.exception("helpdesk tick failed for %s", tenant)
    return out


def _morning_due(tenant: str, n: datetime) -> bool:
    from ..life import tz_of
    with session() as s:
        r = s.get(HelpdeskSettings, tenant)
        if r is None:
            return False
        loc = n.astimezone(tz_of(tenant))
        if r.last_morning == loc.date().isoformat():
            return False
        try:
            hh, mm = (int(x) for x in (r.morning_time or "09:30").split(":"))
        except ValueError:
            hh, mm = 9, 30
        return (loc.hour, loc.minute) >= (hh, mm)


def send_morning(tenant: str) -> dict:
    d = day(tenant)
    _publish(tenant, "helpdesk_day", {"say": d["say"], "open": len(d["open"]), "late": len(d["late"]), "waiting_haan": len(d["waiting_haan"]),
                                      "expiring": d["expiring"][:5], "repeat": d["repeat"][:3]})
    return {"text": d["say"]}


def register_file(tenant: str, conv: str = "") -> dict:
    """Asset register + ticket log as an Excel file (her file, pc_file card)."""
    sheets = [{"name": "Devices", "rows": [["Tag", "Kind", "Name", "Brand", "Model", "Serial", "User", "Location", "OS", "Bought",
                                             "Warranty till", "AMC till", "Vendor", "Advice"]] +
               [[a["tag"], a["kind"], a["name"], a["brand"], a["model"], a["serial"], a["user"], a["location"], a["os"], a["bought"],
                 a["warranty_until"], a["amc_until"], a["vendor"], " ".join(a["advice"])] for a in assets(tenant)]},
              {"name": "Tickets", "rows": [["No", "Priority", "Status", "Problem", "Person", "Device", "Raised by", "Created", "Resolved",
                                            "Fixed by"]] +
               [[t["number"], t["priority"], t["status_label"], t["title"], t["person"], (t["asset"] or {}).get("name", ""), t["raised_by"],
                 t["created_at"], t["resolved_at"], t["fixed_by"]] for t in tickets(tenant, limit=200)]},
              {"name": "Vendors", "rows": [["Name", "Kind", "Phone", "Email", "AMC till", "Visit SLA (h)"]] +
               [[v["name"], v["kind_label"], v["phone"], v["email"], v["amc_until"], v["sla_hours"] or ""] for v in vendors(tenant)]}]
    import io

    import openpyxl

    from .. import chatfiles
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sh in sheets:
        ws = wb.create_sheet(sh["name"][:30])
        for row in sh["rows"]:
            ws.append(row)
    bio = io.BytesIO()
    wb.save(bio)
    name = f"IT_register_{today(tenant).isoformat()}.xlsx"
    f = chatfiles.store(tenant, name, bio.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "helpdesk", "title": "IT register"}, conv)
    return {"file": f, "say": "Devices, tickets aur vendors ka IT register Excel mein."}
