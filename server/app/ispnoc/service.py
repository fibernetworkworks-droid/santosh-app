"""NOC Sahayak (ISP network): Hoola as an FTTH ISP / BSNL Bharat Fiber franchise's network engineer, end to end.

  1. Gets the alarms: pasted OLT logs / syslog lines / SNMP trap text / NMS CSV / email alerts (chat, call, app), files she
     forwards, or HER collector (a small script she runs on her own network: syslog in + read-only `show` commands, HMAC-signed
     pushes). The Hoola server never logs in to her equipment.
  2. Finds the REAL fault (rules.correlate): whole OLT down, uplink down / flapping, BNG / RADIUS, loop storm, rogue ONT, area
     power cut (dying gasp), feeder fibre cut / first splitter, one splitter branch, one customer's drop fibre / power / flap,
     optical (Rx) degradation of a whole PON or one ONT; with a timeline, reasons and a confidence.
  3. Explains it in plain English for her, and drafts the message for the affected customers (ETA blank until someone gives one).
  4. Opens a ticket with the right team (field fibre / NOC / BSNL / upstream / customer / electricity) with location (site,
     splitter, route, Maps), affected count + list, SLA from her own hours (her BSNL agreement's hours for BSNL), ETA, MTTR.
  5. Waits for her Haan on ANY CHANGE ON LIVE EQUIPMENT: ONT reboot, PON reset, ONT disable / enable, uplink reset, her own
     commands -> `ispnoc_change` card with the exact commands for her OLT make + rollback + who loses service + hash.
     Only POST /api/ispnoc/changes/{id}/decide (her tap) approves; then her collector runs exactly those lines (job signed with
     the collector's secret) or she gets the steps to do it herself. Device passwords never come to Hoola.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from sqlalchemy import delete, select

from ..db import now, session
from . import rules as R
from .models import (
    IspnocChange,
    IspnocCollector,
    IspnocEvent,
    IspnocFault,
    IspnocOlt,
    IspnocOnt,
    IspnocSettings,
    IspnocSite,
    IspnocSplitter,
    IspnocTicket,
)

log = logging.getLogger("santosh.ispnoc")
_LOCK = threading.RLock()
MAKES = ("syrotech", "vsol", "cdata", "bdcom", "huawei", "zte", "other")
TICKET_STATUS = ("open", "assigned", "on_site", "fixed", "closed", "cancelled")
TICKET_OPEN = ("open", "assigned", "on_site")
STATE_HOURS = 72                    # events this old still decide the current state of an ONT / OLT
RX_DAYS = 30
KEEP_DAYS = 30
COLLECTOR_OFFLINE_MIN = 15
JOB_TTL_MIN = 30
CLOCK_SKEW_S = 300
_SEEN_SIGS: dict[str, float] = {}
_LAST_ANALYSE: dict[str, float] = {}


class NocError(Exception):
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


def clock() -> datetime:
    return now()


def tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def _local(tenant: str, d: datetime | None) -> str:
    d = _aware(d)
    return d.astimezone(tz(tenant)).strftime("%d %b %I:%M %p") if d else ""


def _dur(a: datetime | None, b: datetime | None) -> str:
    a, b = _aware(a), _aware(b)
    if not a or not b:
        return ""
    m = max(0, int((b - a).total_seconds() // 60))
    return f"{m} min" if m < 60 else (f"{m // 60} h {m % 60} min" if m < 48 * 60 else f"{m // 1440} days {(m % 1440) // 60} h")


def _phone(v: str) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def _mask_phone(p: str) -> str:
    return f"{p[:2]}XXXX{p[-4:]}" if len(p) == 10 else ""


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("ispnoc publish failed")


def _st(s, tenant: str) -> IspnocSettings:
    r = s.get(IspnocSettings, tenant)
    if r is None:
        r = IspnocSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def is_owner(actor: str) -> bool:
    a = actor or "owner"
    return a == "owner" or a.startswith("approved:")


def actor_name(tenant: str, actor: str) -> str:
    try:
        from ..employee.service import actor_label
        return actor_label(tenant, actor or "owner")
    except Exception:
        return "Owner" if actor in ("", "owner") else actor[:40]


def _num(v) -> float | None:
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None


def _no_secret_keys(kw: dict) -> None:
    for k, v in kw.items():
        if re.search(r"(?i)pass|secret|community|token|key", str(k)) or (isinstance(v, str) and R.has_secret(v)):
            raise NocError("Do not give Hoola a device password / SNMP community / key. That stays only in your collector's config "
                           "(on your own network).")


# ---------------------------------------------------------------- settings
_SET_KEYS = ("isp_name", "model", "upstream", "optics", "bsnl_penalty_note", "morning_time", "rules", "window_min")


def settings(tenant: str) -> dict:
    with session() as s:
        r = _st(s, tenant)
        out = {k: getattr(r, k) for k in _SET_KEYS}
        out["teams"] = _j(r.teams, {})
        out["sla"] = {k: R.sla_for(k, _j(r.sla, {})) for k in R.SLA_DEFAULT}
        out["bsnl_sla_hours"] = r.bsnl_sla_hours
        out["optics_label"] = R.optics_of(r.optics)["label"]
        return out


def save_settings(tenant: str, **kw: Any) -> dict:
    _no_secret_keys({k: v for k, v in kw.items() if k != "teams"})
    with session() as s:
        r = _st(s, tenant)
        for k in ("isp_name", "upstream", "bsnl_penalty_note", "rules"):
            if kw.get(k) is not None:
                setattr(r, k, R.scrub(str(kw[k])).strip()[:600 if k == "rules" else 300])
        if kw.get("model") is not None:
            m = str(kw["model"]).lower().strip()
            if m not in ("isp", "franchise", "lco"):
                raise NocError("model = isp (own licence) | franchise (BSNL / TIP) | lco")
            r.model = m
        if kw.get("optics") is not None:
            o = str(kw["optics"]).lower().strip()
            if o not in R.OPTICS:
                raise NocError("optics = " + " | ".join(R.OPTICS))
            r.optics = o
        if kw.get("window_min") is not None:
            w = int(_num(kw["window_min"]) or 15)
            r.window_min = max(2, min(120, w))
        if kw.get("morning_time"):
            m = re.fullmatch(r"(\d{1,2}):(\d{2})", str(kw["morning_time"]).strip())
            if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
                raise NocError("Give the time as HH:MM (for example 09:00).")
            r.morning_time = f"{int(m.group(1)):02d}:{m.group(2)}"
        if "bsnl_sla_hours" in kw:
            v = _num(kw["bsnl_sla_hours"])
            r.bsnl_sla_hours = v if v and v > 0 else None
        if isinstance(kw.get("sla"), dict):
            cur = _j(r.sla, {})
            for k, v in kw["sla"].items():
                if k in R.SLA_DEFAULT and _num(v) is not None and _num(v) >= 0:
                    cur[k] = _num(v)
            r.sla = _dump(cur)
        if isinstance(kw.get("teams"), dict):
            teams = _j(r.teams, {})
            for team, people in kw["teams"].items():
                if team not in R.TEAMS:
                    raise NocError("team = " + " | ".join(R.TEAMS))
                rows = []
                for p in (people or [])[:20]:
                    if not isinstance(p, dict) or not str(p.get("name") or "").strip():
                        continue
                    ph = str(p.get("phone") or "")
                    if ph and not _phone(ph):
                        raise NocError(f"{p.get('name')}: the mobile number must have 10 digits.")
                    rows.append({"name": str(p["name"]).strip()[:80], "phone": _phone(ph), "email": str(p.get("email") or "").strip()[:120],
                                 "area": str(p.get("area") or "").strip()[:120]})
                teams[team] = rows
            r.teams = _dump(teams)
    return settings(tenant)


# ---------------------------------------------------------------- inventory
def _site_view(x: IspnocSite) -> dict:
    return {"id": x.id, "name": x.name, "kind": x.kind, "address": x.address, "lat": x.lat, "lng": x.lng, "power": x.power,
            "contact": x.contact, "notes": x.notes, "maps": _maps(x.lat, x.lng, x.address)}


def _maps(lat, lng, addr: str = "") -> str:
    if lat is not None and lng is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    return f"https://www.google.com/maps/search/?api=1&query={quote(addr)}" if addr else ""


def save_site(tenant: str, name: str, site: str = "", **kw: Any) -> dict:
    _no_secret_keys(kw)
    with session() as s:
        row = _find_site(s, tenant, site) if site else None
        if row is None:
            if not str(name or "").strip():
                raise NocError("Give the site / POP name.")
            row = _find_site(s, tenant, name) or IspnocSite(tenant_id=tenant)
            s.add(row)
        if name:
            row.name = str(name).strip()[:120]
        for k in ("kind", "address", "power", "contact", "notes"):
            if kw.get(k) is not None:
                setattr(row, k, str(kw[k]).strip()[:300])
        for k in ("lat", "lng"):
            if k in kw:
                setattr(row, k, _num(kw[k]))
        s.flush()
        return {"site": _site_view(row), "say": f"Site {row.name} saved."}


def _find_site(s, tenant: str, ref: str) -> IspnocSite | None:
    ref = str(ref or "").strip()
    if not ref:
        return None
    r = s.get(IspnocSite, ref)
    if r is not None and r.tenant_id == tenant:
        return r
    return s.scalars(select(IspnocSite).where(IspnocSite.tenant_id == tenant, IspnocSite.name.ilike(ref))).first()


def _find_olt(s, tenant: str, ref: str) -> IspnocOlt | None:
    ref = str(ref or "").strip()
    if not ref:
        return None
    r = s.get(IspnocOlt, ref)
    if r is not None and r.tenant_id == tenant:
        return r
    rows = s.scalars(select(IspnocOlt).where(IspnocOlt.tenant_id == tenant)).all()
    low = ref.lower()
    for o in rows:
        if o.name.lower() == low or (o.ip and o.ip == ref):
            return o
    for o in rows:
        if o.name and (low in o.name.lower() or o.name.lower() in low):
            return o
    return None


def _olt_view(o: IspnocOlt, sites: dict | None = None, counts: dict | None = None) -> dict:
    site = (sites or {}).get(o.site_id)
    return {"id": o.id, "name": o.name, "make": o.make, "model": o.model, "tech": o.tech, "optics": o.optics or "",
            "ip": o.ip, "site_id": o.site_id, "site": site["name"] if site else "", "pon_ports": o.pon_ports,
            "uplinks": _j(o.uplinks, []), "upstream": o.upstream, "serial": o.serial, "firmware": o.firmware,
            "collector_id": o.collector_id, "notes": o.notes, "onts": (counts or {}).get(o.id, 0)}


def save_olt(tenant: str, name: str, olt: str = "", **kw: Any) -> dict:
    _no_secret_keys(kw)
    with session() as s:
        row = _find_olt(s, tenant, olt) if olt else None
        if row is None:
            if not str(name or "").strip():
                raise NocError("Give the OLT name (for example OLT-AKOT-1).")
            row = _find_olt(s, tenant, name)
            if row is None:
                row = IspnocOlt(tenant_id=tenant)
                s.add(row)
        if name:
            row.name = str(name).strip()[:120]
        if kw.get("make") is not None:
            m = str(kw["make"]).lower().strip().replace("-", "").replace(" ", "")
            m = {"cdata": "cdata", "c-data": "cdata", "optilink": "cdata"}.get(m, m)
            if m and m not in MAKES:
                raise NocError("make = " + " | ".join(MAKES))
            row.make = m
        if kw.get("tech") is not None:
            t = str(kw["tech"]).lower().strip()
            if t not in ("gpon", "epon"):
                raise NocError("tech = gpon | epon")
            row.tech = t
        if kw.get("optics") is not None:
            o = str(kw["optics"]).lower().strip()
            if o and o not in R.OPTICS:
                raise NocError("optics = " + " | ".join(R.OPTICS))
            row.optics = o
        if kw.get("ip") is not None:
            ip = str(kw["ip"]).strip()
            if ip and not re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", ip):
                raise NocError("Write a valid IP (for example 10.10.1.2).")
            row.ip = ip
        if kw.get("site") is not None:
            st = _find_site(s, tenant, str(kw["site"]))
            if st is None and str(kw["site"]).strip():
                st = IspnocSite(tenant_id=tenant, name=str(kw["site"]).strip()[:120])
                s.add(st)
                s.flush()
            row.site_id = st.id if st else ""
        if kw.get("pon_ports") is not None:
            row.pon_ports = max(0, int(_num(kw["pon_ports"]) or 0))
        if kw.get("uplinks") is not None:
            u = kw["uplinks"]
            u = [x.strip().lower() for x in (u.split(",") if isinstance(u, str) else u) if str(x).strip()]
            row.uplinks = _dump(u[:16])
        for k in ("model", "upstream", "serial", "firmware", "notes"):
            if kw.get(k) is not None:
                setattr(row, k, str(kw[k]).strip()[:300])
        if kw.get("collector") is not None:
            c = s.get(IspnocCollector, str(kw["collector"]))
            row.collector_id = c.id if c and c.tenant_id == tenant else ""
        s.flush()
        return {"olt": _olt_view(row), "say": f"OLT {row.name} saved."}


def _ont_view(o: IspnocOnt, olts: dict | None = None, cls: str = "gpon_b+", full_phone: bool = False) -> dict:
    olt = (olts or {}).get(o.olt_id)
    oc = (olt.get("optics") if olt else "") or cls
    return {"id": o.id, "olt_id": o.olt_id, "olt": olt["name"] if olt else "", "pon": o.pon, "onu": o.onu, "sn": o.sn,
            "customer": o.customer, "account": o.account, "phone": o.phone if full_phone else _mask_phone(o.phone),
            "address": o.address, "splitter": o.splitter, "route": o.route, "plan": o.plan, "rx_base": o.rx_base,
            "rx_last": o.rx_last, "rx_band": R.rx_band(o.rx_last, oc), "state": o.state, "state_kind": o.state_kind,
            "active": o.active, "label": _ont_label(o)}


def _ont_label(o: IspnocOnt) -> str:
    who = o.customer or o.account or o.sn or ""
    return f"{who} (PON {o.pon} ONU {o.onu})".strip() if o.pon else who


def save_ont(tenant: str, ont: str = "", **kw: Any) -> dict:
    _no_secret_keys(kw)
    with session() as s:
        row = None
        if ont:
            row = s.get(IspnocOnt, ont)
            if row is not None and row.tenant_id != tenant:
                row = None
        sn = R.norm_sn(kw.get("sn") or "")
        if row is None and sn:
            row = s.scalars(select(IspnocOnt).where(IspnocOnt.tenant_id == tenant, IspnocOnt.sn == sn)).first()
        olt = _find_olt(s, tenant, str(kw.get("olt") or "")) if kw.get("olt") else None
        pon, onu = R.norm_pon(kw.get("pon") or ""), re.sub(r"\D", "", str(kw.get("onu") or ""))
        if row is None and olt and pon and onu:
            row = s.scalars(select(IspnocOnt).where(IspnocOnt.tenant_id == tenant, IspnocOnt.olt_id == olt.id,
                                                    IspnocOnt.pon == pon, IspnocOnt.onu == onu)).first()
        if row is None:
            if not (sn or (olt and pon and onu)):
                raise NocError("For an ONT give the SN / MAC, or the OLT + PON + ONU number.")
            row = IspnocOnt(tenant_id=tenant)
            s.add(row)
        if olt:
            row.olt_id = olt.id
        if pon:
            row.pon = pon
        if onu:
            row.onu = onu
        if sn:
            row.sn = sn
        for k in ("customer", "account", "address", "splitter", "route", "plan"):
            if kw.get(k) is not None:
                setattr(row, k, str(kw[k]).strip()[:300])
        if kw.get("phone") is not None:
            row.phone = _phone(kw["phone"])
        if kw.get("rx_base") is not None:
            row.rx_base = _num(kw["rx_base"])
        if kw.get("active") is not None:
            row.active = bool(kw["active"])
        s.flush()
        return {"ont": _ont_view(row), "say": f"ONT {_ont_label(row)} saved."}


def save_splitter(tenant: str, name: str, **kw: Any) -> dict:
    with session() as s:
        if not str(name or "").strip():
            raise NocError("Give the splitter name.")
        row = s.scalars(select(IspnocSplitter).where(IspnocSplitter.tenant_id == tenant, IspnocSplitter.name.ilike(str(name).strip()))).first()
        if row is None:
            row = IspnocSplitter(tenant_id=tenant, name=str(name).strip()[:120])
            s.add(row)
        if kw.get("olt"):
            o = _find_olt(s, tenant, str(kw["olt"]))
            if o:
                row.olt_id = o.id
        if kw.get("pon"):
            row.pon = R.norm_pon(kw["pon"])
        if kw.get("ratio"):
            rt = int(re.sub(r"\D", "", str(kw["ratio"]).split(":")[-1]) or 8)
            if rt not in R.SPLIT_LOSS:
                raise NocError("ratio = 2 / 4 / 8 / 16 / 32 / 64")
            row.ratio = rt
        for k in ("level",):
            if kw.get(k) is not None:
                row.level = max(1, int(_num(kw[k]) or 1))
        for k in ("parent", "location", "route"):
            if kw.get(k) is not None:
                setattr(row, k, str(kw[k]).strip()[:300])
        for k in ("lat", "lng", "km"):
            if k in kw:
                setattr(row, k, _num(kw[k]))
        s.flush()
        return {"splitter": _spl_view(row), "say": f"Splitter {row.name} saved."}


def _spl_view(x: IspnocSplitter) -> dict:
    return {"id": x.id, "name": x.name, "olt_id": x.olt_id, "pon": x.pon, "ratio": x.ratio, "level": x.level, "parent": x.parent,
            "location": x.location, "lat": x.lat, "lng": x.lng, "route": x.route, "km": x.km, "maps": _maps(x.lat, x.lng, x.location)}


def remove(tenant: str, what: str, ref: str) -> dict:
    model = {"site": IspnocSite, "olt": IspnocOlt, "ont": IspnocOnt, "splitter": IspnocSplitter}.get(what)
    if model is None:
        raise NocError("what = site | olt | ont | splitter")
    with session() as s:
        row = s.get(model, ref)
        if row is None and what == "olt":
            row = _find_olt(s, tenant, ref)
        if row is None or row.tenant_id != tenant:
            raise NocError("Not found.")
        if what == "olt" and s.scalars(select(IspnocOnt).where(IspnocOnt.tenant_id == tenant, IspnocOnt.olt_id == row.id)).first():
            raise NocError("This OLT has ONTs; remove them first or move them to another OLT.")
        s.delete(row)
    return {"ok": True, "say": "Removed."}


# ---- import (CSV / Excel) ------------------------------------------------
_IMP = {
    "customer": ("customer", "customer name", "name", "subscriber", "grahak", "naam"),
    "account": ("account", "account no", "user id", "username", "userid", "ftth id", "circuit id", "service id"),
    "phone": ("mobile", "phone", "contact", "mobile no", "phone no"),
    "address": ("address", "pata", "location"),
    "sn": ("sn", "serial", "onu sn", "ont sn", "mac", "onu mac", "serial no", "gpon sn"),
    "olt": ("olt", "olt name", "olt ip", "device"),
    "pon": ("pon", "pon port", "port"),
    "onu": ("onu", "ont", "onu id", "ont id", "llid"),
    "splitter": ("splitter", "spl", "splitter name", "db", "fdb", "fat"),
    "route": ("route", "fibre route", "fiber route"),
    "plan": ("plan", "package"),
    "rx_base": ("rx", "rx power", "rx base", "install rx"),
    "make": ("make", "vendor", "brand"),
    "model": ("model",),
    "ip": ("ip", "mgmt ip", "management ip"),
    "tech": ("tech", "type"),
    "site": ("site", "pop", "exchange"),
    "pon_ports": ("pon ports", "ports", "pon count"),
    "ratio": ("ratio", "split ratio"),
    "name": ("name", "olt name", "splitter name", "site name"),
    "lat": ("lat", "latitude"),
    "lng": ("lng", "lon", "long", "longitude"),
    "kind": ("kind",),
}


def _rows_of(data: bytes, name: str) -> list[list[str]]:
    n = (name or "").lower()
    if n.endswith((".xlsx", ".xlsm")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.worksheets[0]
        return [["" if c is None else str(c).strip() for c in row] for row in ws.iter_rows(values_only=True)][:20001]
    text = data.decode("utf-8-sig", errors="replace")
    return [[c.strip() for c in r] for r in csv.reader(io.StringIO(text))][:20001]


def _hdr(header: list[str]) -> dict[str, int]:
    hs = [h.lower().strip() for h in header]
    idx: dict[str, int] = {}
    for key, words in _IMP.items():
        for w in words:
            if w in hs:
                idx[key] = hs.index(w)
                break
    return idx


def import_inventory(tenant: str, data: bytes | None = None, name: str = "network.csv", kind: str = "auto", file_id: str = "") -> dict:
    """Her network sheet: customers' ONTs (customer, phone, SN / MAC, OLT, PON, ONU, splitter, route), OLTs, splitters or sites."""
    if file_id:
        from ..analyst.service import _load_file
        name, data = _load_file(tenant, file_id)
    if not data:
        raise NocError("The file is empty.")
    rows = [r for r in _rows_of(data, name) if any(c for c in r)]
    if len(rows) < 2:
        raise NocError("The sheet has no line below the header.")
    head = None
    for i, r in enumerate(rows[:10]):
        if len(_hdr(r)) >= 2:
            head = i
            break
    if head is None:
        raise NocError("Could not understand the header. Columns like: customer, mobile, sn/mac, olt, pon, onu, splitter.")
    header = rows[head]
    secret_cols = [h for h in header if re.search(r"(?i)pass|pwd|secret|community|key", h)]
    idx = _hdr(header)
    if kind == "auto":
        if "sn" in idx or ("onu" in idx and "pon" in idx):
            kind = "onts"
        elif "ratio" in idx:
            kind = "splitters"
        elif "ip" in idx or "make" in idx:
            kind = "olts"
        elif "customer" in idx or "phone" in idx:
            kind = "onts"
        else:
            kind = "sites"
    done, bad = 0, []
    for n, r in enumerate(rows[head + 1:], start=head + 2):
        g = {k: (r[i] if i < len(r) else "") for k, i in idx.items()}
        try:
            if kind == "onts":
                save_ont(tenant, **{k: g[k] for k in ("customer", "account", "phone", "address", "sn", "olt", "pon", "onu", "splitter", "route", "plan", "rx_base") if g.get(k)})
            elif kind == "olts":
                save_olt(tenant, g.get("name") or g.get("olt") or "", **{k: g[k] for k in ("make", "model", "ip", "tech", "site", "pon_ports") if g.get(k)})
            elif kind == "splitters":
                save_splitter(tenant, g.get("name") or g.get("splitter") or "", **{k: g[k] for k in ("olt", "pon", "ratio", "route", "lat", "lng") if g.get(k)},
                              **({"location": g["address"]} if g.get("address") else {}))
            elif kind == "sites":
                save_site(tenant, g.get("name") or g.get("site") or "", **{k: g[k] for k in ("address", "lat", "lng", "kind") if g.get(k)})
            else:
                raise NocError("kind = onts | olts | splitters | sites")
            done += 1
        except NocError as e:
            bad.append({"row": n, "why": str(e)[:120]})
    say = f"{done} {kind} lines saved."
    if bad:
        say += f" {len(bad)} lines skipped (reasons in the list)."
    if secret_cols:
        say += f" Column {', '.join(secret_cols)} not read at all (Hoola does not keep passwords / keys)."
    return {"kind": kind, "saved": done, "bad": bad[:50], "ignored_columns": secret_cols, "say": say}


def network(tenant: str) -> dict:
    with session() as s:
        sites = {x.id: _site_view(x) for x in s.scalars(select(IspnocSite).where(IspnocSite.tenant_id == tenant)).all()}
        onts = s.scalars(select(IspnocOnt).where(IspnocOnt.tenant_id == tenant)).all()
        counts: dict[str, int] = {}
        down: dict[str, int] = {}
        for o in onts:
            counts[o.olt_id] = counts.get(o.olt_id, 0) + 1
            if o.state == "down":
                down[o.olt_id] = down.get(o.olt_id, 0) + 1
        olts = []
        for o in s.scalars(select(IspnocOlt).where(IspnocOlt.tenant_id == tenant).order_by(IspnocOlt.name)).all():
            v = _olt_view(o, sites, counts)
            v["down"] = down.get(o.id, 0)
            olts.append(v)
        spl = [_spl_view(x) for x in s.scalars(select(IspnocSplitter).where(IspnocSplitter.tenant_id == tenant)).all()]
        weak = sum(1 for o in onts if o.rx_last is not None and R.rx_band(o.rx_last, settings_optics(tenant)) in ("weak", "bad"))
        return {"sites": list(sites.values()), "olts": olts, "splitters": spl, "onts": len(onts),
                "onts_active": sum(1 for o in onts if o.active), "onts_down": sum(1 for o in onts if o.state == "down"), "weak_rx": weak}


def settings_optics(tenant: str) -> str:
    with session() as s:
        return _st(s, tenant).optics


def find_onts(tenant: str, q: str = "", olt: str = "", pon: str = "", limit: int = 50) -> list[dict]:
    with session() as s:
        olts = {o.id: {"name": o.name, "optics": o.optics} for o in s.scalars(select(IspnocOlt).where(IspnocOlt.tenant_id == tenant)).all()}
        stmt = select(IspnocOnt).where(IspnocOnt.tenant_id == tenant)
        if olt:
            o = _find_olt(s, tenant, olt)
            stmt = stmt.where(IspnocOnt.olt_id == (o.id if o else "-"))
        if pon:
            stmt = stmt.where(IspnocOnt.pon == R.norm_pon(pon))
        rows = s.scalars(stmt).all()
        ql = str(q or "").strip().lower()
        if ql:
            qd = re.sub(r"\D", "", ql)
            qs = R.norm_sn(ql)
            rows = [o for o in rows if ql in (o.customer or "").lower() or ql in (o.account or "").lower() or
                    (len(qd) >= 4 and qd in o.phone) or (len(qs) >= 4 and qs in o.sn) or ql in (o.address or "").lower()]
        cls = _st(s, tenant).optics
        return [_ont_view(o, olts, cls) for o in rows[:limit]]


# ---------------------------------------------------------------- alarm intake
def _inv(s, tenant: str) -> tuple[dict, dict, dict, dict]:
    olts = {o.id: o for o in s.scalars(select(IspnocOlt).where(IspnocOlt.tenant_id == tenant)).all()}
    onts = {o.id: o for o in s.scalars(select(IspnocOnt).where(IspnocOnt.tenant_id == tenant)).all()}
    by_sn = {o.sn: o for o in onts.values() if o.sn}
    by_pos = {(o.olt_id, o.pon, o.onu): o for o in onts.values() if o.pon and o.onu}
    return olts, onts, by_sn, by_pos


def _olt_for(ev: dict, olts: dict, hint: IspnocOlt | None) -> str:
    if hint is not None:
        return hint.id
    for o in olts.values():
        if ev.get("ip") and o.ip and ev["ip"] == o.ip:
            return o.id
    h = (ev.get("host") or "").lower()
    if h:
        for o in olts.values():
            if o.name and o.name.lower() == h:
                return o.id
        for o in olts.values():
            if o.name and (h in o.name.lower() or o.name.lower() in h):
                return o.id
    if len(olts) == 1:
        return next(iter(olts))
    return ""


def ingest(tenant: str, text: str, olt: str = "", source: str = "paste", conv: str = "", actor: str = "owner",
           analyse_now: bool = True) -> dict:
    """Alarm text -> events (deduped) -> ONT states -> faults. Returns what was read and what Hoola concluded."""
    text = str(text or "")
    if not text.strip():
        raise NocError("The alarm text is empty. Paste the OLT log / syslog / the NMS CSV.")
    if len(text) > 2_000_000:
        raise NocError("The text is too large (up to 2 MB).")
    with _LOCK:
        with session() as s:
            st = _st(s, tenant)
            extra = {}
            for ln in (st.rules or "").splitlines():                 # "word = kind" lines in her rules teach the parser
                m = re.match(r"\s*([^=]{3,40})=\s*([a-z_]+)\s*$", ln)
                if m and m.group(2) in R.KINDS:
                    extra[m.group(1).strip()] = m.group(2)
            t_now = clock()
            parsed = R.parse_text(text, tz(tenant), t_now, extra)
            olts, onts, by_sn, by_pos = _inv(s, tenant)
            hint = _find_olt(s, tenant, olt) if olt else None
            if olt and hint is None:
                raise NocError(f"OLT '{olt}' is not in Hoola's list. Add it in Network first.")
            added = dup = unmapped = 0
            keys_seen: set[str] = set()
            for ev in parsed["events"]:
                at = (_aware(ev["at"]) or t_now).astimezone(timezone.utc)      # SQLite keeps the wall clock: always UTC
                if at > t_now + timedelta(minutes=10):
                    at = t_now
                oid = _olt_for(ev, olts, hint)
                ont = None
                if ev.get("sn"):
                    ont = by_sn.get(ev["sn"])
                if ont is None and oid and ev.get("pon") and ev.get("onu"):
                    ont = by_pos.get((oid, ev["pon"], ev["onu"]))
                if ont is not None:
                    oid = oid or ont.olt_id
                if not oid:
                    unmapped += 1
                key = hashlib.sha1(f"{oid}|{ev['pon']}|{ev['onu']}|{ev['sn']}|{ev['port']}|{ev['kind']}|{at.isoformat()}|{ev['raw'][:80]}"
                                   .encode()).hexdigest()[:40]
                if key in keys_seen or s.scalars(select(IspnocEvent.id).where(IspnocEvent.tenant_id == tenant, IspnocEvent.key == key)).first():
                    dup += 1
                    continue
                keys_seen.add(key)
                s.add(IspnocEvent(tenant_id=tenant, at=at, got_at=t_now, olt_id=oid, pon=ev["pon"] or (ont.pon if ont else ""),
                                  onu=ev["onu"] or (ont.onu if ont else ""), sn=ev["sn"] or (ont.sn if ont else ""), port=ev["port"],
                                  kind=ev["kind"], clear=ev["clear"], rx=ev["rx"], source=source[:16], raw=ev["raw"], key=key))
                added += 1
                if ont is not None:
                    if ev["kind"] in R.DOWN and (ont.state_at is None or _aware(ont.state_at) <= at):
                        ont.state, ont.state_kind, ont.state_at = "down", ev["kind"], at
                    elif ev["kind"] == "online" and (ont.state_at is None or _aware(ont.state_at) <= at):
                        ont.state, ont.state_kind, ont.state_at = "up", "", at
                    if ev["rx"] is not None:
                        ont.rx_last, ont.rx_at = ev["rx"], at
                        cls = (olts.get(ont.olt_id).optics if olts.get(ont.olt_id) else "") or st.optics
                        if ont.rx_base is None and R.rx_band(ev["rx"], cls) == "good":
                            ont.rx_base = ev["rx"]
    res = analyse(tenant, conv=conv) if analyse_now and added else {"new": [], "updated": [], "resolved": []}
    say = f"{added} alarms read" + (f", {dup} already there" if dup else "") + (f", {parsed['skipped']} lines not understood" if parsed["skipped"] else "") + "."
    if unmapped:
        say += f" {unmapped} alarms: could not tell which OLT they belong to. Send again with the OLT name (olt=...)."
    if res["new"]:
        say += " New faults: " + "; ".join(f"{f['number']} {f['title']} ({f['n_affected']} customers, {f['confidence_label']})" for f in res["new"][:5]) + "."
    if res["resolved"]:
        say += " Fixed: " + ", ".join(f["number"] for f in res["resolved"][:8]) + "."
    if not res["new"] and not res["updated"] and not res["resolved"] and added:
        say += " These create no open fault."
    return {"read": added, "duplicates": dup, "skipped": parsed["skipped"], "unmapped": unmapped, "format": parsed["format"],
            "new": res["new"], "updated": res["updated"], "resolved": res["resolved"], "say": say}


# ---------------------------------------------------------------- analysis
def _inv_dict(olts: dict, onts: dict, s, tenant: str) -> dict:
    spl = {x.name: {"olt": x.olt_id, "pon": x.pon, "level": x.level} for x in s.scalars(select(IspnocSplitter).where(IspnocSplitter.tenant_id == tenant)).all()}
    return {"olts": {k: {"name": o.name, "optics": o.optics, "pons": o.pon_ports, "uplinks": _j(o.uplinks, [])} for k, o in olts.items()},
            "onts": {k: {"olt": o.olt_id, "pon": o.pon, "splitter": o.splitter, "rx_base": o.rx_base, "customer": o.customer,
                         "active": o.active} for k, o in onts.items()},
            "splitters": spl}


def _event_dicts(s, tenant: str, onts: dict, t_now: datetime) -> list[dict]:
    by_sn = {o.sn: k for k, o in onts.items() if o.sn}
    by_pos = {(o.olt_id, o.pon, o.onu): k for k, o in onts.items() if o.pon and o.onu}
    rows = s.scalars(select(IspnocEvent).where(IspnocEvent.tenant_id == tenant, IspnocEvent.at >= t_now - timedelta(days=RX_DAYS))
                     .order_by(IspnocEvent.at)).all()
    out = []
    cut = t_now - timedelta(hours=STATE_HOURS)
    for e in rows:
        at = _aware(e.at)
        if at < cut and e.rx is None:
            continue
        ont = by_sn.get(e.sn) or by_pos.get((e.olt_id, e.pon, e.onu))
        if ont is None and (e.pon and e.onu):
            ont = f"{e.olt_id}|{e.pon}|{e.onu}"
        elif ont is None and e.sn:
            ont = f"sn:{e.sn}"
        kind = e.kind
        if at < cut:                                   # old rows only give Rx history, never state
            kind = "rx"
        out.append({"at": at, "olt": e.olt_id, "pon": e.pon, "onu": e.onu, "ont": ont, "kind": kind if kind not in ("rx_low", "rx_high") or e.rx is None else "rx",
                    "rx": e.rx, "port": e.port, "raw": e.raw})
    return out


def _next(s, tenant: str, field: str, prefix: str) -> str:
    st = _st(s, tenant)
    setattr(st, field, getattr(st, field) + 1)
    return f"{prefix}-{getattr(st, field):04d}"


def analyse(tenant: str, conv: str = "") -> dict:
    """Run correlation on the last 72 h of alarms (+30 days of Rx) and update the open faults."""
    t_now = clock()
    new, updated, resolved = [], [], []
    with _LOCK:
        with session() as s:
            st = _st(s, tenant)
            olts, onts, _a, _b = _inv(s, tenant)
            evs = _event_dicts(s, tenant, onts, t_now)
            found = R.correlate(evs, _inv_dict(olts, onts, s, tenant), t_now, st.window_min, st.optics)
            found_keys = {f["key"]: f for f in found}
            open_rows = {f.key: f for f in s.scalars(select(IspnocFault).where(IspnocFault.tenant_id == tenant,
                                                                               IspnocFault.status.in_(("open", "ticketed")))).all()}
            olt_down = {f["olt"] for f in found if f["kind"] == "olt_down"}
            for key, f in found_keys.items():
                row = open_rows.get(key)
                data = {"reasons": f["reasons"], "evidence": f["evidence"]}
                if row is None:
                    row = IspnocFault(tenant_id=tenant, number=_next(s, tenant, "seq", "F"), key=key, kind=f["kind"], scope=f["scope"],
                                      olt_id=f["olt"], pon=f["pon"], target=str(f["target"])[:160], started_at=f["started"],
                                      last_at=f["last"], status="open", confidence=f["confidence"], affected=_dump(f["affected"][:2000]),
                                      n_affected=f["n_affected"], n_total=f["n_total"], data=_dump(data))
                    s.add(row)
                    s.flush()
                    new.append(row.id)
                else:
                    changed = (row.n_affected != f["n_affected"] or abs(row.confidence - f["confidence"]) >= 0.05)
                    row.last_at, row.confidence = f["last"], f["confidence"]
                    row.affected, row.n_affected, row.n_total = _dump(f["affected"][:2000]), f["n_affected"], f["n_total"]
                    row.data = _dump({**_j(row.data, {}), **data})
                    if changed:
                        updated.append(row.id)
            for key, row in open_rows.items():
                if key in found_keys:
                    continue
                if row.olt_id in olt_down and row.kind != "olt_down":
                    row.status = "dismissed"
                    _note(row, "Merged into the whole-OLT fault.")
                    resolved.append(row.id)
                    continue
                if _cleared(row, evs):
                    row.status, row.resolved_at = "resolved", t_now
                    _note(row, f"Alarm cleared: fixed in {_dur(row.started_at, t_now)}.")
                    for tk in s.scalars(select(IspnocTicket).where(IspnocTicket.fault_id == row.id, IspnocTicket.status.in_(TICKET_OPEN))).all():
                        tk.status, tk.fixed_at = "fixed", t_now
                        _tlog(tk, "Alarm cleared, ticket fixed.")
                    resolved.append(row.id)
    _LAST_ANALYSE[tenant] = time.time()
    views_new = [fault_view(tenant, i) for i in new]
    views_upd = [fault_view(tenant, i) for i in updated]
    views_res = [fault_view(tenant, i) for i in resolved]
    for v in views_new:
        _publish(tenant, "ispnoc_fault", {"fault": v, "new": True, "say": f"{v['number']}: {v['title']}. {v['explain']}"}, conv)
    for v in views_upd + views_res:
        _publish(tenant, "ispnoc_fault", {"fault": v, "say": f"{v['number']}: {v['status_label']}"}, conv)
    return {"new": views_new, "updated": views_upd, "resolved": views_res}


def _cleared(row: IspnocFault, evs: list[dict]) -> bool:
    """A fault only closes on proof: its own clear alarm / affected ONTs online after it started (time-based kinds expire)."""
    if row.kind in ("flap", "rx_bad", "rx_high", "pon_degrade", "storm", "bng", "uplink_flap"):
        return True
    start = _aware(row.started_at)
    after = [e for e in evs if e["at"] >= start]
    if row.kind == "uplink":
        return any(e["kind"] == "uplink_up" and e["olt"] == row.olt_id and (e.get("port") or "uplink") == row.target for e in after)
    if row.kind == "olt_down" and any(e["kind"] == "olt_up" and e["olt"] == row.olt_id for e in after):
        return True
    if row.scope == "pon" and any(e["kind"] == "pon_up" and e["olt"] == row.olt_id and e["pon"] == row.pon for e in after):
        return True
    aff = set(_j(row.affected, []))
    if not aff:
        return False
    up = {e["ont"] for e in after if e["kind"] == "online"}
    still_down = {e["ont"] for e in after if e["kind"] in R.DOWN} - up
    return len(aff & up) >= max(1, int(0.8 * len(aff))) and not (aff & still_down)


def _note(row, text: str, by: str = "Hoola") -> None:
    n = _j(row.notes, [])
    n.append({"at": now().isoformat(timespec="seconds"), "by": by[:60], "text": text[:400]})
    row.notes = _dump(n[-60:])


def _tlog(tk: IspnocTicket, what: str, by: str = "Hoola") -> None:
    lg = _j(tk.log, [])
    lg.append({"at": now().isoformat(timespec="seconds"), "by": by[:60], "what": what[:300]})
    tk.log = _dump(lg[-80:])


# ---------------------------------------------------------------- views
STATUS_LABEL = {"open": "Open", "ticketed": "Ticket made", "resolved": "Fixed", "dismissed": "Merged / removed"}


def _get_fault(s, tenant: str, ref: str) -> IspnocFault:
    ref = str(ref or "").strip()
    r = s.get(IspnocFault, ref)
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(IspnocFault).where(IspnocFault.tenant_id == tenant, IspnocFault.number == ref.upper())).first()
    if r is None:
        raise NocError(f"Fault {ref} not found.")
    return r


def fault_view(tenant: str, ref: str, full_phone: bool = False) -> dict:
    with session() as s:
        f = _get_fault(s, tenant, ref)
        st = _st(s, tenant)
        olts, onts, _a, _b = _inv(s, tenant)
        olt = olts.get(f.olt_id)
        site = s.get(IspnocSite, olt.site_id) if olt and olt.site_id else None
        meta = R.FAULTS.get(f.kind, {"title": f.kind, "team": "noc", "scope": f.scope})
        aff_ids = _j(f.affected, [])

        def _ord(k):
            o = onts.get(k)
            return (0, o.pon, int(o.onu) if o.onu.isdigit() else 0, o.customer) if o is not None else (1, str(k), 0, "")
        aff_ids = sorted(aff_ids, key=_ord)
        aff = []
        for k in aff_ids[:60]:
            o = onts.get(k)
            if o is not None:
                aff.append({"id": o.id, "customer": o.customer, "phone": o.phone if full_phone else _mask_phone(o.phone),
                            "address": o.address[:80], "pon": o.pon, "onu": o.onu, "splitter": o.splitter, "state": o.state})
            else:
                aff.append({"id": k, "customer": "", "phone": "", "address": "", "label": str(k).split("|", 1)[-1].replace("|", " ONU "), "state": ""})
        one = onts.get(aff_ids[0]) if len(aff_ids) == 1 else None
        spl = None
        if f.scope == "splitter":
            spl = s.scalars(select(IspnocSplitter).where(IspnocSplitter.tenant_id == tenant, IspnocSplitter.name == f.target)).first()
        route = (spl.route if spl else "") or (one.route if one else "")
        if not route and f.scope == "pon":
            routes = {onts[k].route for k in aff_ids if k in onts and onts[k].route}
            route = ", ".join(sorted(routes)[:3])
        target = f.target
        if f.scope == "ont" and one is not None:
            target = _ont_label(one)
        elif f.scope == "ont":
            target = str(f.target).split("|", 1)[-1].replace("|", " ONU ")
        names = {"olt": olt.name if olt else "", "target": target, "upstream": (olt.upstream if olt else "") or st.upstream,
                 "route": route, "customer": one.customer if one else "", "rx": one.rx_last if one else None}
        fv = {"kind": f.kind, "olt": f.olt_id, "pon": f.pon, "target": f.target, "n_affected": f.n_affected}
        tks = s.scalars(select(IspnocTicket).where(IspnocTicket.fault_id == f.id).order_by(IspnocTicket.created_at)).all()
        eta = next((_aware(t.eta) for t in reversed(tks) if t.eta and t.status in TICKET_OPEN), None)
        team = meta["team"]
        if f.kind in ("uplink", "uplink_flap", "bng") and st.model == "franchise" and "bsnl" in ((names["upstream"] or "") + st.upstream).lower():
            team = "bsnl"
        sla_h = (st.bsnl_sla_hours if team == "bsnl" and st.bsnl_sla_hours else R.sla_for(f.kind, _j(st.sla, {})))
        end = _aware(f.resolved_at) or clock()
        mins = int((end - _aware(f.started_at)).total_seconds() // 60)
        total_subs = sum(1 for o in onts.values() if o.active)
        notes = []
        if f.status in ("open", "ticketed"):
            share = (f.n_affected / total_subs) if total_subs else 0
            if mins >= 240 and share >= 0.10:
                notes.append(f"{f.n_affected} / {total_subs} customers ({share:.0%}) down for more than 4 hours: under TRAI's draft (Aug 2026) this would be a "
                             "'Significant Network Outage' (report to TRAI within 24 hours). It is a draft for now"
                             + ("; under a BSNL franchise, tell BSNL at once." if st.model == "franchise" else "."))
            if mins >= 24 * 60:
                notes.append("Down for more than 24 hours: the TRAI draft talks of a rent rebate / extended validity for such customers; "
                             "tell the customers as per your own policy.")
        if f.kind in ("bng", "rogue_onu") and st.model == "franchise":
            notes.append("Network security / login problem: BSNL (the licensee) may have to be told (Telecom Cyber Security Rules 2024: "
                         "a security incident within 6 hours).")
        loc = {}
        if site is not None:
            loc = {"site": site.name, "address": site.address, "maps": _maps(site.lat, site.lng, site.address), "power": site.power}
        if spl is not None:
            loc.update({"splitter": spl.name, "splitter_location": spl.location, "splitter_maps": _maps(spl.lat, spl.lng, spl.location),
                        "km": spl.km})
        if one is not None:
            loc.update({"customer_address": one.address, "customer_maps": _maps(None, None, one.address) if one.address else ""})
        data = _j(f.data, {})
        suggest = []
        if f.kind in ("flap", "ont_offline") and one is not None and one.onu:
            suggest.append({"action": "reboot_ont", "olt": f.olt_id, "pon": one.pon, "onu": one.onu, "why": "restarting the ONT sometimes fixes it"})
        if f.kind == "storm":
            suggest.append({"action": "pon_reset", "olt": f.olt_id, "pon": f.pon, "why": "PON reset until the looping customer's port is found (everyone's internet will drop)"})
        return {
            "id": f.id, "number": f.number, "kind": f.kind, "title": meta["title"], "scope": f.scope, "olt_id": f.olt_id,
            "olt": olt.name if olt else "", "pon": f.pon, "target": target, "status": f.status, "status_label": STATUS_LABEL.get(f.status, f.status),
            "started": _local(tenant, f.started_at), "started_at": _aware(f.started_at).isoformat(), "last": _local(tenant, f.last_at),
            "resolved": _local(tenant, f.resolved_at), "minutes": mins, "duration": _dur(f.started_at, end),
            "n_affected": f.n_affected, "n_total": f.n_total, "affected": aff, "confidence": round(f.confidence, 2),
            "confidence_label": R.conf_label(f.confidence), "reasons": data.get("reasons", []), "evidence": data.get("evidence", []),
            "explain": R.explain(fv, names), "customer_msg": R.customer_message(fv, st.isp_name, _local(tenant, eta) if eta else "", one.customer if one else ""),
            "team": team, "team_label": R.TEAMS.get(team, team), "sla_hours": sla_h, "due": _local(tenant, _aware(f.started_at) + timedelta(hours=sla_h)) if sla_h else "",
            "location": loc, "route": route, "notes": notes, "log": _j(f.notes, [])[-10:], "suggest": suggest,
            "tickets": [_ticket_view(tenant, t, f) for t in tks],
        }


def faults(tenant: str, status: str = "open", limit: int = 40) -> list[dict]:
    with session() as s:
        stmt = select(IspnocFault.id).where(IspnocFault.tenant_id == tenant)
        if status == "open":
            stmt = stmt.where(IspnocFault.status.in_(("open", "ticketed")))
        elif status:
            stmt = stmt.where(IspnocFault.status == status)
        ids = s.scalars(stmt.order_by(IspnocFault.started_at.desc()).limit(limit)).all()
    return [fault_view(tenant, i) for i in ids]


def fault_note(tenant: str, ref: str, text: str, actor: str = "owner") -> dict:
    with session() as s:
        f = _get_fault(s, tenant, ref)
        _note(f, R.scrub(text), actor_name(tenant, actor))
        fid = f.id
    return {"fault": fault_view(tenant, fid), "say": "Note added."}


def dismiss(tenant: str, ref: str, reason: str = "", actor: str = "owner") -> dict:
    with session() as s:
        f = _get_fault(s, tenant, ref)
        f.status, f.resolved_at = "dismissed", clock()
        _note(f, "Removed: " + (R.scrub(reason) or "false alarm"), actor_name(tenant, actor))
        fid = f.id
    v = fault_view(tenant, fid)
    _publish(tenant, "ispnoc_fault", {"fault": v, "say": f"{v['number']} removed."})
    return {"fault": v, "say": f"{v['number']} removed."}


def resolve(tenant: str, ref: str, note: str = "", actor: str = "owner") -> dict:
    with session() as s:
        f = _get_fault(s, tenant, ref)
        f.status, f.resolved_at = "resolved", clock()
        _note(f, "Fixed: " + (R.scrub(note) or "(no note)"), actor_name(tenant, actor))
        for tk in s.scalars(select(IspnocTicket).where(IspnocTicket.fault_id == f.id, IspnocTicket.status.in_(TICKET_OPEN))).all():
            tk.status, tk.fixed_at = "fixed", clock()
            _tlog(tk, "Fault marked fixed.", actor_name(tenant, actor))
        fid = f.id
    v = fault_view(tenant, fid)
    _publish(tenant, "ispnoc_fault", {"fault": v, "say": f"{v['number']} fixed: {v['duration']}"})
    return {"fault": v, "say": f"{v['number']} marked fixed (down for{v['duration']}). If new alarms come, Hoola will open it again."}


def customer_message(tenant: str, ref: str, restored: bool = False) -> dict:
    """The text for affected customers + their numbers (for her to send from her own WhatsApp / SMS / broadcast)."""
    v = fault_view(tenant, ref, full_phone=True)
    st = settings(tenant)
    text = v["customer_msg"]
    if restored or v["status"] == "resolved":
        text = f"Hello, from {st['isp_name'] or '[ISP name]'}: internet service in your area is working again. If you still have a problem, switch the router off and on, or tell us."
    phones = [a["phone"] for a in v["affected"] if a.get("phone")]
    blanks = re.findall(r"\[[^\]]+\]", text)
    return {"text": text, "phones": phones, "count": len(phones), "blanks": blanks,
            "wa_link": f"https://wa.me/?text={quote(text)}" if text else "",
            "say": ("Message ready" + (f"; {', '.join(blanks)} still to be filled in" if blanks else "") +
                    f". {len(phones)} customer numbers; you send it from your own WhatsApp / SMS (Hoola does not send it).") if text
            else "No customer message is needed for this fault."}


# ---------------------------------------------------------------- tickets
def _get_ticket(s, tenant: str, ref: str) -> IspnocTicket:
    ref = str(ref or "").strip()
    t = s.get(IspnocTicket, ref)
    if t is None or t.tenant_id != tenant:
        t = s.scalars(select(IspnocTicket).where(IspnocTicket.tenant_id == tenant, IspnocTicket.number == ref.upper())).first()
    if t is None:
        raise NocError(f"Ticket {ref} not found.")
    return t


def _ticket_view(tenant: str, t: IspnocTicket, f: IspnocFault | None = None) -> dict:
    due = _aware(t.due_at)
    fixed = _aware(t.fixed_at)
    late = bool(due and (fixed or clock()) > due and t.status not in ("cancelled",))
    mttr = None
    if fixed and f is not None:
        mttr = round((fixed - _aware(f.started_at)).total_seconds() / 3600, 2)
    return {"id": t.id, "number": t.number, "fault_id": t.fault_id, "fault": f.number if f else "", "team": t.team,
            "team_label": R.TEAMS.get(t.team, t.team), "assignee": t.assignee, "phone": _mask_phone(t.phone), "status": t.status,
            "eta": _local(tenant, t.eta), "due": _local(tenant, due), "late": late, "sla_hours": t.sla_hours, "created": _local(tenant, t.created_at),
            "fixed": _local(tenant, fixed), "mttr_hours": mttr, "ext_ref": t.ext_ref, "text": t.text, "log": _j(t.log, [])[-12:],
            "wa_link": f"https://wa.me/91{t.phone}?text={quote(t.text)}" if t.phone else f"https://wa.me/?text={quote(t.text)}",
            "tel": f"tel:+91{t.phone}" if t.phone else ""}


def _ticket_text(tenant: str, v: dict, team: str, eta: str, note: str, isp: str) -> str:
    lines = [f"{isp or 'Network'} ticket: {v['title']} ({v['number']})", f"Since: {v['started']} ({v['duration']})",
             f"OLT: {v['olt'] or '-'}" + (f", PON {v['pon']}" if v["pon"] else "") + (f", {v['target']}" if v["scope"] in ("splitter", "ont", "uplink") else ""),
             f"Affected: {v['n_affected']} customers" + (f" / {v['n_total']}" if v["n_total"] and v["n_total"] != v["n_affected"] else ""),
             "Why it looks so: " + "; ".join(v["reasons"][:3])]
    loc = v["location"]
    if loc.get("site"):
        lines.append(f"Site: {loc['site']}, {loc.get('address') or ''} {loc.get('maps') or ''}".strip())
    if loc.get("splitter"):
        lines.append(f"Splitter: {loc['splitter']} {loc.get('splitter_location') or ''} {loc.get('splitter_maps') or ''}".strip())
    if v["route"]:
        lines.append(f"Route: {v['route']}")
    if team in ("field_fibre", "customer") and v["scope"] == "ont" and v["affected"]:
        a = v["affected"][0]
        lines.append(f"Customer: {a.get('customer') or '-'}, {a.get('address') or '-'}")
    elif v["affected"]:
        names = [a.get("customer") or a.get("label") or a["id"] for a in v["affected"][:15]]
        lines.append("Customers: " + ", ".join(n for n in names if n) + (f" ... (+{v['n_affected'] - 15})" if v["n_affected"] > 15 else ""))
    if eta:
        lines.append(f"ETA: {eta}")
    if note:
        lines.append(f"Note: {note}")
    lines.append("When the work is done, send 'fixed' on this number. Never write a device password in a message.")
    return "\n".join(lines)


def open_ticket(tenant: str, ref: str, team: str = "", assignee: str = "", phone: str = "", eta: str = "", note: str = "",
                ext_ref: str = "", actor: str = "owner", conv: str = "") -> dict:
    v = fault_view(tenant, ref, full_phone=True)
    team = (team or v["team"]).strip()
    if team not in R.TEAMS:
        raise NocError("team = " + " | ".join(R.TEAMS))
    st = settings(tenant)
    people = st["teams"].get(team, [])
    if assignee and not phone:
        hit = next((p for p in people if p["name"].lower() == assignee.lower()), None)
        phone = hit["phone"] if hit else ""
    if not assignee and people:
        assignee, phone = people[0]["name"], people[0]["phone"]
    if phone and not _phone(phone):
        raise NocError("The mobile number must have 10 digits.")
    eta_dt = R.parse_when(eta, clock(), tz(tenant)) if eta else None
    eta_dt = eta_dt.astimezone(timezone.utc) if eta_dt else None
    if eta and eta_dt is None:
        raise NocError("Could not understand the ETA: write it like '2 hours', '6 pm', '18:30'.")
    with session() as s:
        f = _get_fault(s, tenant, v["id"])
        dupe = s.scalars(select(IspnocTicket).where(IspnocTicket.fault_id == f.id, IspnocTicket.team == team,
                                                    IspnocTicket.status.in_(TICKET_OPEN))).first()
        if dupe is not None:
            return {"ticket": _ticket_view(tenant, dupe, f), "fault": v, "say": f"{dupe.number} is already open ({R.TEAMS[team]})."}
        sla_h = float(st["bsnl_sla_hours"]) if team == "bsnl" and st["bsnl_sla_hours"] else R.sla_for(f.kind, st["sla"])
        tk = IspnocTicket(tenant_id=tenant, number=_next(s, tenant, "ticket_seq", "N"), fault_id=f.id, team=team, assignee=assignee[:120],
                          phone=_phone(phone), status="assigned" if assignee else "open", eta=eta_dt, sla_hours=sla_h or None,
                          due_at=(_aware(f.started_at) + timedelta(hours=sla_h)) if sla_h else None, ext_ref=R.scrub(ext_ref)[:80],
                          raised_by=actor_name(tenant, actor))
        tk.text = _ticket_text(tenant, v, team, _local(tenant, eta_dt) if eta_dt else "", R.scrub(note), st["isp_name"])
        _tlog(tk, f"Ticket made ({R.TEAMS[team]}{', ' + assignee if assignee else ''})", actor_name(tenant, actor))
        s.add(tk)
        if f.status == "open":
            f.status = "ticketed"
        s.flush()
        out = _ticket_view(tenant, tk, f)
    say = f"{out['number']} is ready for {out['team_label']}" + (f" ({assignee})" if assignee else "") + \
          (f", SLA {out['sla_hours']:g} h (due {out['due']})" if out["sla_hours"] else "") + \
          ". You send it with the WhatsApp / call button; Hoola does not send it."
    if team == "bsnl" and not st["bsnl_sla_hours"]:
        say += " Add the SLA hours of the BSNL agreement in Rules; then Hoola can count the delay."
    _publish(tenant, "ispnoc_ticket", {"ticket": out, "say": say}, conv)
    return {"ticket": out, "fault": fault_view(tenant, v["id"]), "say": say}


def update_ticket(tenant: str, ref: str, status: str = "", eta: str = "", note: str = "", assignee: str = "", phone: str = "",
                  ext_ref: str = "", actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        tk = _get_ticket(s, tenant, ref)
        f = s.get(IspnocFault, tk.fault_id)
        who = actor_name(tenant, actor)
        if status:
            if status not in TICKET_STATUS:
                raise NocError("status = " + " | ".join(TICKET_STATUS))
            tk.status = status
            if status == "fixed" and tk.fixed_at is None:
                tk.fixed_at = clock()
            _tlog(tk, f"Status: {status}", who)
        if eta:
            e = R.parse_when(eta, clock(), tz(tenant))
            if e is None:
                raise NocError("Could not understand the ETA: '2 hours', '6 pm', '18:30'.")
            tk.eta = e.astimezone(timezone.utc)
            told = _j(tk.told, {})
            told.pop("eta", None)
            tk.told = _dump(told)
            _tlog(tk, f"ETA: {_local(tenant, e)}", who)
        if assignee:
            tk.assignee = assignee[:120]
            if tk.status == "open":
                tk.status = "assigned"
        if phone:
            if not _phone(phone):
                raise NocError("The mobile number must have 10 digits.")
            tk.phone = _phone(phone)
        if ext_ref:
            tk.ext_ref = R.scrub(ext_ref)[:80]
            _tlog(tk, f"Docket / ref: {tk.ext_ref}", who)
        if note:
            _tlog(tk, R.scrub(note), who)
        out = _ticket_view(tenant, tk, f)
        still_open = f is not None and f.status in ("open", "ticketed")
    say = f"{out['number']}: {out['status']}" + (f", ETA {out['eta']}" if out["eta"] else "") + "."
    if status == "fixed" and still_open:
        say += " The alarm has not cleared yet: paste new alarms (or the collector will send them) and Hoola will close the fault; or mark it 'fixed'."
    if status == "fixed" and out["mttr_hours"] is not None:
        say += f" MTTR {out['mttr_hours']:g} h" + (" (past SLA)" if out["late"] else "") + "."
    _publish(tenant, "ispnoc_ticket", {"ticket": out, "say": say}, conv)
    return {"ticket": out, "say": say}


def tickets(tenant: str, status: str = "open", limit: int = 40) -> list[dict]:
    with session() as s:
        stmt = select(IspnocTicket).where(IspnocTicket.tenant_id == tenant)
        if status == "open":
            stmt = stmt.where(IspnocTicket.status.in_(TICKET_OPEN))
        elif status:
            stmt = stmt.where(IspnocTicket.status == status)
        rows = s.scalars(stmt.order_by(IspnocTicket.created_at.desc()).limit(limit)).all()
        return [_ticket_view(tenant, t, s.get(IspnocFault, t.fault_id)) for t in rows]


# ---------------------------------------------------------------- changes on live equipment (her Haan)
CH_LABEL = {"waiting": "Waiting for your approval", "rejected": "Declined", "approved": "Approved: you will do it yourself", "queued": "Approved: the collector will do it",
            "running": "The collector is running it", "done": "Done", "failed": "Failed", "expired": "Timed out", "cancelled": "Cancelled"}


def _change_hash(c: IspnocChange, olt: IspnocOlt | None) -> str:
    blob = _dump({"a": c.action, "olt": c.olt_id, "ip": olt.ip if olt else "", "pon": c.pon, "onu": c.onu,
                  "cmd": _j(c.commands, []), "rb": _j(c.rollback, []), "n": c.n_affected})
    return hashlib.sha256(blob.encode()).hexdigest()


def _get_change(s, tenant: str, ref: str) -> IspnocChange:
    ref = str(ref or "").strip()
    c = s.get(IspnocChange, ref)
    if c is None or c.tenant_id != tenant:
        c = s.scalars(select(IspnocChange).where(IspnocChange.tenant_id == tenant, IspnocChange.number == ref.upper())).first()
    if c is None:
        raise NocError(f"Change {ref} not found.")
    return c


def _change_view(tenant: str, c: IspnocChange, olt: IspnocOlt | None, col: IspnocCollector | None = None) -> dict:
    cmds = _j(c.commands, [])
    return {"id": c.id, "number": c.number, "action": c.action, "action_label": R.CHANGE_ACTIONS.get(c.action, c.action),
            "olt_id": c.olt_id, "olt": olt.name if olt else "", "olt_ip": olt.ip if olt else "", "make": olt.make if olt else "",
            "pon": c.pon, "onu": c.onu, "fault_id": c.fault_id, "reason": c.reason, "commands": cmds, "rollback": _j(c.rollback, []),
            "verified": c.verified, "risk": c.risk, "n_affected": c.n_affected, "hash": c.hash, "status": c.status,
            "status_label": CH_LABEL.get(c.status, c.status), "via": c.via, "created": _local(tenant, c.created_at),
            "decided": _local(tenant, c.decided_at), "done": _local(tenant, c.done_at), "output": c.output[-2000:],
            "asked_by": c.asked_by, "collector": col.name if col else "",
            "warn": "" if c.verified else "Check these commands against your OLT's manual / Telnet help (the CLI of this make is not public). If wrong, correct them with 'Edit' and then approve again.",
            "steps": _manual_steps(olt, cmds, _j(c.rollback, [])) if c.status in ("approved", "waiting") else ""}


def _manual_steps(olt: IspnocOlt | None, cmds: list[str], back: list[str]) -> str:
    if olt is None:
        return ""
    s = f"1. From your own network, log in to OLT {olt.name} ({olt.ip or 'IP'}) over Telnet / SSH / web CLI (only you know the password).\n"
    s += "2. Run these lines one by one:\n" + "\n".join(f"   {c}" for c in cmds)
    if back:
        s += "\n3. If something goes wrong, roll back:\n" + "\n".join(f"   {c}" for c in back)
    s += "\n4. Then press 'Done' here; Hoola will check from the next alarm / Rx."
    return s


def request_change(tenant: str, action: str, olt: str, pon: str = "", onu: str = "", port: str = "", commands: list[str] | None = None,
                   rollback: list[str] | None = None, reason: str = "", fault: str = "", actor: str = "owner", conv: str = "") -> dict:
    """Make the card. Nothing on the equipment changes here."""
    if action not in R.CHANGE_ACTIONS:
        raise NocError("action = " + " | ".join(R.CHANGE_ACTIONS))
    if actor.startswith("customer:"):
        raise NocError("This is not available to customers.")
    with session() as s:
        o = _find_olt(s, tenant, olt)
        if o is None:
            raise NocError("Name an OLT (name or IP) that is in the Network list.")
        pon_n, onu_n = R.norm_pon(pon), re.sub(r"\D", "", str(onu or ""))
        if action in ("reboot_ont", "ont_disable", "ont_enable") and not (pon_n and onu_n):
            raise NocError("An ONT needs the PON and ONU number.")
        if action == "pon_reset" and not pon_n:
            raise NocError("Give the PON port.")
        if action == "uplink_reset" and not port:
            raise NocError("Give the uplink port (for example ge0/9).")
        if action == "custom" or commands:
            cmds = [str(c).strip() for c in (commands or []) if str(c).strip()][:40]
            back = [str(c).strip() for c in (rollback or []) if str(c).strip()][:40]
            if not cmds:
                raise NocError("Give your command lines.")
            verified = False
        else:
            t = R.commands_for(o.make, action, o.tech, pon_n, onu_n, port)
            cmds, back, verified = t["commands"], t["rollback"], t["verified"]
        probs = R.command_problems(cmds + back)
        if probs:
            raise NocError("These lines will not run through Hoola (password / erase / reload / firmware / copy): " + "; ".join(probs[:3]))
        if any(R.has_secret(c) for c in cmds + back):
            raise NocError("A command must not contain a password / key.")
        if action in ("reboot_ont", "ont_disable", "ont_enable"):
            n = 1
        elif action == "pon_reset":
            n = len(s.scalars(select(IspnocOnt.id).where(IspnocOnt.tenant_id == tenant, IspnocOnt.olt_id == o.id, IspnocOnt.pon == pon_n,
                                                         IspnocOnt.active.is_(True))).all())
        elif action == "uplink_reset":
            n = len(s.scalars(select(IspnocOnt.id).where(IspnocOnt.tenant_id == tenant, IspnocOnt.olt_id == o.id, IspnocOnt.active.is_(True))).all())
        else:
            n = 0
        fid = ""
        if fault:
            try:
                fid = _get_fault(s, tenant, fault).id
            except NocError:
                fid = ""
        same = s.scalars(select(IspnocChange).where(IspnocChange.tenant_id == tenant, IspnocChange.status == "waiting",
                                                    IspnocChange.olt_id == o.id, IspnocChange.action == action,
                                                    IspnocChange.pon == pon_n, IspnocChange.onu == onu_n)).first()
        if same is not None and _j(same.commands, []) == cmds:
            col = s.get(IspnocCollector, o.collector_id) if o.collector_id else None
            return {"change": _change_view(tenant, same, o, col), "needs_tap": True, "say": f"{same.number} is already waiting for your approval."}
        c = IspnocChange(tenant_id=tenant, number=_next(s, tenant, "change_seq", "C"), action=action, olt_id=o.id, pon=pon_n, onu=onu_n,
                         fault_id=fid, reason=R.scrub(reason)[:400], commands=_dump(cmds), rollback=_dump(back), verified=verified,
                         risk=R.risk_of(action, n), n_affected=n, status="waiting", asked_by=actor_name(tenant, actor))
        c.hash = _change_hash(c, o)
        s.add(c)
        s.flush()
        col = s.get(IspnocCollector, o.collector_id) if o.collector_id else None
        out = _change_view(tenant, c, o, col)
    say = (f"{out['number']}: {out['action_label']} ({out['olt']}" + (f" PON {out['pon']}" if out["pon"] else "") + (f" ONU {out['onu']}" if out["onu"] else "")
           + f"). Affected: {out['n_affected']} customers. A card has been sent for your approval; nothing changes on the equipment without your approval.")
    _publish(tenant, "ispnoc_change", {"change": out, "say": say}, conv)
    return {"change": out, "needs_tap": True, "say": say}


def edit_change(tenant: str, ref: str, commands: list[str], rollback: list[str] | None = None, actor: str = "owner") -> dict:
    with session() as s:
        c = _get_change(s, tenant, ref)
        if c.status != "waiting":
            raise NocError("Only a change that is still waiting can be edited.")
        cmds = [str(x).strip() for x in commands if str(x).strip()][:40]
        back = [str(x).strip() for x in (rollback if rollback is not None else _j(c.rollback, [])) if str(x).strip()][:40]
        if not cmds:
            raise NocError("The command lines are empty.")
        probs = R.command_problems(cmds + back)
        if probs or any(R.has_secret(x) for x in cmds + back):
            raise NocError("Lines with password / erase / reload / firmware / copy will not run.")
        c.commands, c.rollback, c.verified = _dump(cmds), _dump(back), False
        o = s.get(IspnocOlt, c.olt_id)
        c.hash = _change_hash(c, o)
        out = _change_view(tenant, c, o)
    say = f"{out['number']}: lines changed; new card. Your approval is needed again."
    _publish(tenant, "ispnoc_change", {"change": out, "say": say})
    return {"change": out, "needs_tap": True, "say": say}


def _collector_online(c: IspnocCollector | None) -> bool:
    return bool(c and c.active and c.last_seen and clock() - _aware(c.last_seen) <= timedelta(minutes=COLLECTOR_OFFLINE_MIN))


def decide_change(tenant: str, ref: str, yes: bool, hash_: str, reason: str = "", by_tap: bool = False) -> dict:
    """ONLY from her tap (POST /api/ispnoc/changes/{id}/decide). The hash must be the card she saw."""
    if not by_tap:
        raise NocError("A change on equipment happens only when you press Yes in your app.")
    with session() as s:
        c = _get_change(s, tenant, ref)
        o = s.get(IspnocOlt, c.olt_id)
        if c.status != "waiting":
            return {"change": _change_view(tenant, c, o), "say": f"{c.number} is already decided: {CH_LABEL.get(c.status, c.status)}."}
        if not hash_ or not hmac.compare_digest(str(hash_), c.hash) or c.hash != _change_hash(c, o):
            raise NocError("The card is old (the change was edited). See the new card and approve it.")
        c.decided_at = clock()
        if not yes:
            c.status = "rejected"
            c.output = R.scrub(reason)[:400]
            out = _change_view(tenant, c, o)
            say = f"{c.number}: declined. Nothing changed."
        else:
            col = s.get(IspnocCollector, o.collector_id) if o and o.collector_id else None
            if col is not None and col.changes_ok and _collector_online(col):
                c.status, c.via = "queued", "collector"
                say = f"{c.number}: approved. Collector '{col.name}' will run exactly these lines within {JOB_TTL_MIN} minutes; the result will come here."
            else:
                c.status, c.via = "approved", "manual"
                why = ("The collector is offline" if col is not None and not _collector_online(col) else
                       "The collector is not allowed to make changes" if col is not None else "This OLT has no collector")
                say = f"{c.number}: approved. {why}, so the steps are given: run them yourself, then press 'Done'."
            out = _change_view(tenant, c, o, col)
    _publish(tenant, "ispnoc_change", {"change": out, "say": say})
    return {"change": out, "say": say}


def change_done(tenant: str, ref: str, ok: bool, output: str = "", actor: str = "owner") -> dict:
    """She ran an approved change herself."""
    if not is_owner(actor):
        raise NocError("Only the owner can mark this.")
    with session() as s:
        c = _get_change(s, tenant, ref)
        if c.status not in ("approved", "expired"):
            raise NocError("Approval on the card is needed first (or it is running through the collector).")
        c.status, c.done_at, c.output = ("done" if ok else "failed"), clock(), R.scrub(output)[:4000]
        out = _change_view(tenant, c, s.get(IspnocOlt, c.olt_id))
    say = f"{out['number']}: {out['status_label']}."
    _publish(tenant, "ispnoc_change", {"change": out, "say": say})
    return {"change": out, "say": say}


def cancel_change(tenant: str, ref: str) -> dict:
    with session() as s:
        c = _get_change(s, tenant, ref)
        if c.status not in ("waiting", "approved", "queued"):
            raise NocError("This change can no longer be cancelled.")
        c.status = "cancelled"
        out = _change_view(tenant, c, s.get(IspnocOlt, c.olt_id))
    _publish(tenant, "ispnoc_change", {"change": out, "say": f"{out['number']} cancelled."})
    return {"change": out, "say": f"{out['number']} cancelled."}


def changes(tenant: str, status: str = "", limit: int = 40) -> list[dict]:
    with session() as s:
        stmt = select(IspnocChange).where(IspnocChange.tenant_id == tenant)
        if status:
            stmt = stmt.where(IspnocChange.status == status)
        rows = s.scalars(stmt.order_by(IspnocChange.created_at.desc()).limit(limit)).all()
        return [_change_view(tenant, c, s.get(IspnocOlt, c.olt_id)) for c in rows]


def optics_check(cls: str = "", km: float = 0, splits: list[int] | None = None, connectors: int = 4, splices: int = 4, rx: float | None = None) -> dict:
    out = R.budget(cls or "gpon_b+", km, splits, connectors, splices)
    if rx is not None:
        band = R.rx_band(rx, cls or "gpon_b+")
        out["measured"] = rx
        out["measured_band"] = band
        gap = round(out["rx_expected"] - rx, 2)
        out["gap_db"] = gap
        out["say"] += f" Measured {rx} dBm ({band})" + (f": {gap} dB below expected; check connector cleaning / splice / bend." if gap >= 3 else ".")
    return out


# ---------------------------------------------------------------- collector (her network) + HMAC
def collector_sign(secret: str, method: str, path: str, ts: str, body: bytes, nonce: str = "") -> str:
    msg = f"{method.upper()}\n{path}\n{ts}\n{nonce}\n".encode() + hashlib.sha256(body or b"").hexdigest().encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def job_sig(secret: str, job_id: str, hash_: str, commands: list[str]) -> str:
    return hmac.new(secret.encode(), f"{job_id}|{hash_}|{_dump(commands)}".encode(), hashlib.sha256).hexdigest()


def _secret_of(c: IspnocCollector) -> str:
    from ..bazar.security import vault
    return vault().open(c.sealed)


def create_collector(tenant: str, name: str, site: str = "", changes_ok: bool = False) -> dict:
    """API only (her app): the secret is shown ONCE so she can put it in the collector's config on her own machine."""
    import secrets as _s
    from ..bazar.security import vault
    if not str(name or "").strip():
        raise NocError("Give the collector a name (for example 'Akot POP box').")
    secret = _s.token_urlsafe(32)
    with session() as s:
        st = _find_site(s, tenant, site) if site else None
        c = IspnocCollector(tenant_id=tenant, name=str(name).strip()[:120], sealed=vault().seal(secret), site_id=st.id if st else "",
                            changes_ok=bool(changes_ok))
        s.add(c)
        s.flush()
        view = _collector_view(tenant, c)
    return {"collector": view, "secret": secret,
            "say": "Collector created. The secret is shown only now: put it in the collector's config on your POP / office computer. "
                   "Device passwords stay on that computer, not with Hoola."}


def _collector_view(tenant: str, c: IspnocCollector) -> dict:
    return {"id": c.id, "name": c.name, "site_id": c.site_id, "changes_ok": c.changes_ok, "online": _collector_online(c),
            "last_seen": _local(tenant, c.last_seen), "info": _j(c.last_info, {}), "active": c.active, "created": _local(tenant, c.created_at)}


def collectors(tenant: str) -> list[dict]:
    with session() as s:
        return [_collector_view(tenant, c) for c in s.scalars(select(IspnocCollector).where(IspnocCollector.tenant_id == tenant,
                                                                                          IspnocCollector.active.is_(True))).all()]


def update_collector(tenant: str, cid: str, changes_ok: bool | None = None, olts: list[str] | None = None, active: bool | None = None) -> dict:
    with session() as s:
        c = s.get(IspnocCollector, cid)
        if c is None or c.tenant_id != tenant:
            raise NocError("Collector not found.")
        if changes_ok is not None:
            c.changes_ok = bool(changes_ok)
        if active is not None:
            c.active = bool(active)
        if olts is not None:
            for o in s.scalars(select(IspnocOlt).where(IspnocOlt.tenant_id == tenant)).all():
                if o.collector_id == c.id:
                    o.collector_id = ""
            for ref in olts:
                o = _find_olt(s, tenant, ref)
                if o is not None:
                    o.collector_id = c.id
        view = _collector_view(tenant, c)
    return {"collector": view, "say": "Collector updated."}


def verify_collector(cid: str, method: str, path: str, ts: str, sig: str, body: bytes, nonce: str = "") -> IspnocCollector:
    try:
        t = int(ts)
    except (TypeError, ValueError):
        raise NocError("bad time")
    if abs(time.time() - t) > CLOCK_SKEW_S:
        raise NocError("clock skew")
    with session() as s:
        c = s.get(IspnocCollector, str(cid or ""))
        if c is None or not c.active:
            raise NocError("unknown collector")
        if not re.fullmatch(r"[0-9a-f]{16,64}", str(nonce or "")):
            raise NocError("nonce missing")
        want = collector_sign(_secret_of(c), method, path, ts, body, nonce)
        if not hmac.compare_digest(want, str(sig or "")):
            raise NocError("bad signature")
        with _LOCK:
            for k, v in list(_SEEN_SIGS.items()):
                if v < time.time() - 2 * CLOCK_SKEW_S:
                    _SEEN_SIGS.pop(k, None)
            if sig in _SEEN_SIGS:
                raise NocError("replay")
            _SEEN_SIGS[sig] = time.time()
        s.expunge(c)
        return c


def collector_push(c: IspnocCollector, body: dict) -> dict:
    """Heartbeat + alarm lines + read-only command outputs from her collector."""
    tenant = c.tenant_id
    info = body.get("info") if isinstance(body.get("info"), dict) else {}
    back = False
    with session() as s:
        row = s.get(IspnocCollector, c.id)
        back = row.offline_told
        row.last_seen, row.offline_told = clock(), False
        if info:
            row.last_info = _dump({k: str(v)[:200] for k, v in list(info.items())[:20]})
        olt_ids = [o.id for o in s.scalars(select(IspnocOlt).where(IspnocOlt.tenant_id == tenant, IspnocOlt.collector_id == c.id)).all()]
    if back:
        _publish(tenant, "ispnoc_alert", {"say": f"Collector '{c.name}' is connected again.", "kind": "collector_back"})
    total = {"read": 0, "new": [], "resolved": []}
    batches = []
    for b in (body.get("batches") or [])[:50]:
        if isinstance(b, dict) and isinstance(b.get("lines"), list):
            batches.append((str(b.get("olt") or ""), "\n".join(str(x) for x in b["lines"][:5000]), str(b.get("source") or "syslog")))
    for o in (body.get("outputs") or [])[:50]:
        if isinstance(o, dict) and isinstance(o.get("text"), str):
            cmd = str(o.get("command") or "")
            if not R.READ_ONLY.match(cmd):
                continue                                      # only read-only outputs are accepted
            batches.append((str(o.get("olt") or ""), o["text"][:500_000], "cli"))
    for olt, text, src in batches:
        if not text.strip():
            continue
        with session() as s:
            o = _find_olt(s, tenant, olt) if olt else None
            if olt and o is None:
                continue
            if o is not None and olt_ids and o.id not in olt_ids:
                continue                                      # a collector only speaks for the OLTs she gave it
            oname = o.id if o else ""
        try:
            r = ingest(tenant, text, olt=oname, source="collector" if src != "cli" else "cli", analyse_now=False)
            total["read"] += r["read"]
        except NocError:
            continue
    if total["read"]:
        res = analyse(tenant)
        total["new"] = [f["number"] for f in res["new"]]
        total["resolved"] = [f["number"] for f in res["resolved"]]
    return {"ok": True, **total}


def collector_jobs(c: IspnocCollector) -> dict:
    """Approved changes for the OLTs this collector serves (signed per job). Fetching = taking."""
    secret = _secret_of(c)
    out = []
    with session() as s:
        row = s.get(IspnocCollector, c.id)
        row.last_seen = clock()
        if not row.changes_ok:
            return {"jobs": []}
        olts = {o.id: o for o in s.scalars(select(IspnocOlt).where(IspnocOlt.tenant_id == c.tenant_id, IspnocOlt.collector_id == c.id)).all()}
        for ch in s.scalars(select(IspnocChange).where(IspnocChange.tenant_id == c.tenant_id, IspnocChange.status == "queued")).all():
            o = olts.get(ch.olt_id)
            if o is None:
                continue
            if clock() - _aware(ch.decided_at) > timedelta(minutes=JOB_TTL_MIN):
                ch.status = "expired"
                continue
            if ch.hash != _change_hash(ch, o):
                ch.status = "failed"
                ch.output = "The change was edited after the card; not run."
                continue
            cmds = _j(ch.commands, [])
            ch.status = "running"
            out.append({"id": ch.id, "number": ch.number, "olt": o.name, "ip": o.ip, "make": o.make, "commands": cmds,
                        "rollback": _j(ch.rollback, []), "hash": ch.hash, "sig": job_sig(secret, ch.id, ch.hash, cmds)})
    return {"jobs": out}


def collector_result(c: IspnocCollector, job_id: str, ok: bool, output: str = "") -> dict:
    with session() as s:
        ch = s.get(IspnocChange, job_id)
        if ch is None or ch.tenant_id != c.tenant_id or ch.status != "running":
            raise NocError("job not running")
        o = s.get(IspnocOlt, ch.olt_id)
        if o is None or o.collector_id != c.id:
            raise NocError("not your job")
        ch.status, ch.done_at, ch.output = ("done" if ok else "failed"), clock(), R.scrub(str(output))[:4000]
        out = _change_view(c.tenant_id, ch, o)
    say = f"{out['number']} ({out['action_label']}): {out['status_label']}."
    _publish(c.tenant_id, "ispnoc_change", {"change": out, "say": say})
    return {"ok": True, "change": out}


def collector_script() -> str:
    return (Path(__file__).parent / "collector.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------- day, report, tick
def day(tenant: str) -> dict:
    fs = faults(tenant, "open")
    tks = tickets(tenant, "open")
    ch = changes(tenant, "waiting")
    cols = collectors(tenant)
    late = [t for t in tks if t["late"]]
    off = [c for c in cols if not c["online"] and c["last_seen"]]
    down = sum(f["n_affected"] for f in fs if f["kind"] not in ("rx_bad", "rx_high", "pon_degrade", "flap"))
    parts = []
    if fs:
        parts.append(f"{len(fs)} open faults ({down} customers down)")
    if late:
        parts.append(f"{len(late)} tickets past SLA")
    if ch:
        parts.append(f"{len(ch)} changes waiting for your approval")
    if off:
        parts.append(f"{len(off)} collectors offline")
    return {"faults": fs, "tickets": tks, "late": late, "waiting_haan": ch, "collectors": cols, "customers_down": down,
            "say": ("Network: " + ", ".join(parts) + ".") if parts else "Network: no open faults."}


def report(tenant: str, days: int = 30) -> dict:
    since = clock() - timedelta(days=max(1, min(365, days)))
    with session() as s:
        fs = s.scalars(select(IspnocFault).where(IspnocFault.tenant_id == tenant, IspnocFault.started_at >= since)).all()
        tks = s.scalars(select(IspnocTicket).where(IspnocTicket.tenant_id == tenant, IspnocTicket.created_at >= since)).all()
        fmap = {f.id: f for f in fs}
        by_kind: dict[str, dict] = {}
        cust_min = 0
        for f in fs:
            if f.status == "dismissed":
                continue
            d = by_kind.setdefault(f.kind, {"kind": f.kind, "title": R.FAULTS.get(f.kind, {}).get("title", f.kind), "count": 0, "hours": []})
            d["count"] += 1
            if f.resolved_at:
                h = (_aware(f.resolved_at) - _aware(f.started_at)).total_seconds() / 3600
                d["hours"].append(h)
                if f.kind not in ("rx_bad", "rx_high", "pon_degrade", "flap"):
                    cust_min += int(h * 60) * max(1, f.n_affected)
        kinds = []
        for d in by_kind.values():
            hs = d.pop("hours")
            d["mttr_hours"] = round(sum(hs) / len(hs), 2) if hs else None
            kinds.append(d)
        kinds.sort(key=lambda x: -x["count"])
        team: dict[str, dict] = {}
        for t in tks:
            d = team.setdefault(t.team, {"team": t.team, "label": R.TEAMS.get(t.team, t.team), "tickets": 0, "fixed": 0, "in_sla": 0, "mttr": []})
            d["tickets"] += 1
            if t.fixed_at:
                d["fixed"] += 1
                f = fmap.get(t.fault_id) or s.get(IspnocFault, t.fault_id)
                if f is not None:
                    d["mttr"].append((_aware(t.fixed_at) - _aware(f.started_at)).total_seconds() / 3600)
                if not t.due_at or _aware(t.fixed_at) <= _aware(t.due_at):
                    d["in_sla"] += 1
        teams = []
        for d in team.values():
            m = d.pop("mttr")
            d["mttr_hours"] = round(sum(m) / len(m), 2) if m else None
            d["sla_pct"] = round(100 * d["in_sla"] / d["fixed"]) if d["fixed"] else None
            teams.append(d)
        pons: dict[str, int] = {}
        olts = {o.id: o.name for o in s.scalars(select(IspnocOlt).where(IspnocOlt.tenant_id == tenant)).all()}
        for f in fs:
            if f.pon and f.status != "dismissed":
                k = f"{olts.get(f.olt_id, f.olt_id or '?')} PON {f.pon}"
                pons[k] = pons.get(k, 0) + 1
        top = sorted(pons.items(), key=lambda x: -x[1])[:8]
        subs = len(s.scalars(select(IspnocOnt.id).where(IspnocOnt.tenant_id == tenant, IspnocOnt.active.is_(True))).all())
    all_fixed = [t for t in teams if t["mttr_hours"] is not None]
    mttr = round(sum(t["mttr_hours"] * t["fixed"] for t in all_fixed) / max(1, sum(t["fixed"] for t in all_fixed)), 2) if all_fixed else None
    tips = []
    if top and top[0][1] >= 3:
        tips.append(f"{top[0][0]}: {top[0][1]} faults: get that route / splitter checked fully once.")
    if mttr is not None and mttr > 10:
        tips.append(f"Average time to fix is {mttr:g} h: the TRAI draft says 10 hours; keep spare patch cords / a splicer with the team.")
    availability = None
    if subs:
        availability = round(100 - 100 * cust_min / (subs * days * 24 * 60), 3)
    return {"days": days, "faults": sum(k["count"] for k in kinds), "by_kind": kinds, "teams": teams, "top_pons": [{"pon": p, "count": c} for p, c in top],
            "mttr_hours": mttr, "customer_minutes_down": cust_min, "subscribers": subs, "availability_pct": availability, "tips": tips,
            "say": f"{days} days: {sum(k['count'] for k in kinds)} faults" + (f", fixed in {mttr:g} h on average" if mttr is not None else "")
                   + (f", service {availability}% chali" if availability is not None else "") + "."}


def overview(tenant: str) -> dict:
    d = day(tenant)
    return {**d, "settings": settings(tenant), "network": network(tenant), "changes": changes(tenant), "facts": R.RULES_FACTS,
            "sources": [{"title": t, "url": u} for t, u in R.SOURCES], "optics": R.OPTICS, "teams_all": R.TEAMS,
            "actions": R.CHANGE_ACTIONS}


def _told(row, tag: str) -> bool:
    t = _j(row.told, {})
    if tag in t:
        return True
    t[tag] = now().isoformat(timespec="minutes")
    row.told = _dump(t)
    return False


def send_morning(tenant: str) -> dict:
    d = day(tenant)
    lines = [d["say"]]
    for f in d["faults"][:6]:
        lines.append(f"- {f['number']} {f['title']}: {f['n_affected']} customers, {f['duration']}" + (" (ticket)" if f["tickets"] else " (no ticket)"))
    for t in d["late"][:5]:
        lines.append(f"- {t['number']} {t['team_label']} late (due {t['due']})")
    text = "NOC: " + "\n".join(lines)
    _publish(tenant, "ispnoc_day", {"say": d["say"], "text": text, "faults": len(d["faults"]), "late": len(d["late"]),
                                   "waiting": len(d["waiting_haan"])})
    return {"text": text}


def tick(when: datetime | None = None) -> dict:
    t_now = _aware(when) or clock()
    out = {"sla": 0, "eta": 0, "sno": 0, "collectors": 0, "expired": 0, "morning": 0, "analysed": 0}
    with session() as s:
        tenants = [r.tenant_id for r in s.scalars(select(IspnocSettings)).all()]
    for tenant in tenants:
        try:
            alerts: list[str] = []
            with session() as s:
                st = _st(s, tenant)
                for c in s.scalars(select(IspnocCollector).where(IspnocCollector.tenant_id == tenant, IspnocCollector.active.is_(True))).all():
                    if c.last_seen and t_now - _aware(c.last_seen) > timedelta(minutes=COLLECTOR_OFFLINE_MIN) and not c.offline_told:
                        c.offline_told = True
                        alerts.append(f"Collector '{c.name}' has been silent for {COLLECTOR_OFFLINE_MIN} minutes: check power / internet / the computer at that POP "
                                      "(news of a fault there may not be reaching Hoola).")
                        out["collectors"] += 1
                for tk in s.scalars(select(IspnocTicket).where(IspnocTicket.tenant_id == tenant, IspnocTicket.status.in_(TICKET_OPEN))).all():
                    if tk.due_at and t_now > _aware(tk.due_at) and not _told(tk, "sla"):
                        alerts.append(f"{tk.number} ({R.TEAMS.get(tk.team, tk.team)}) is past its SLA of {tk.sla_hours:g} h.")
                        out["sla"] += 1
                    if tk.eta and t_now > _aware(tk.eta) + timedelta(minutes=15) and not _told(tk, "eta"):
                        alerts.append(f"{tk.number}: ETA {_local(tenant, tk.eta)} has passed; ask {tk.assignee or 'the team'} for a new time.")
                        out["eta"] += 1
                subs = len(s.scalars(select(IspnocOnt.id).where(IspnocOnt.tenant_id == tenant, IspnocOnt.active.is_(True))).all())
                for f in s.scalars(select(IspnocFault).where(IspnocFault.tenant_id == tenant, IspnocFault.status.in_(("open", "ticketed")))).all():
                    mins = (t_now - _aware(f.started_at)).total_seconds() / 60
                    if f.kind in ("rx_bad", "rx_high", "pon_degrade", "flap"):
                        continue
                    if subs and mins >= 240 and f.n_affected / subs >= 0.10 and not _told(f, "sno"):
                        alerts.append(f"{f.number}: {f.n_affected} / {subs} customers down for 4 hours. Major outage: "
                                      + ("tell BSNL at once; " if st.model == "franchise" else "")
                                      + "the TRAI draft (Aug 2026) talks of reporting such an outage within 24 hours.")
                        out["sno"] += 1
                    if mins >= 24 * 60 and f.n_affected and not _told(f, "day"):
                        alerts.append(f"{f.number}: down for more than 24 hours ({f.n_affected} customers). Tell the customers and check your own rebate policy.")
                        out["sno"] += 1
                for ch in s.scalars(select(IspnocChange).where(IspnocChange.tenant_id == tenant, IspnocChange.status.in_(("queued", "running")))).all():
                    if ch.decided_at and t_now - _aware(ch.decided_at) > timedelta(minutes=JOB_TTL_MIN if ch.status == "queued" else 2 * JOB_TTL_MIN):
                        ch.status = "expired"
                        alerts.append(f"{ch.number}: the collector did not run it within {JOB_TTL_MIN} minutes; cancelled. Create a new card if needed.")
                        out["expired"] += 1
                s.execute(delete(IspnocEvent).where(IspnocEvent.tenant_id == tenant, IspnocEvent.at < t_now - timedelta(days=KEEP_DAYS)))
                morning, last = st.morning_time, st.last_morning
                loc = t_now.astimezone(tz(tenant))
                due_m = loc.strftime("%H:%M") >= morning and last != loc.date().isoformat()
                if due_m:
                    st.last_morning = loc.date().isoformat()
            for a in alerts:
                _publish(tenant, "ispnoc_alert", {"say": a})
            if time.time() - _LAST_ANALYSE.get(tenant, 0) > 300:
                with session() as s:
                    has_open = s.scalars(select(IspnocFault.id).where(IspnocFault.tenant_id == tenant, IspnocFault.status.in_(("open", "ticketed")))).first()
                if has_open:
                    analyse(tenant)
                    out["analysed"] += 1
            if due_m:
                d = day(tenant)
                if d["faults"] or d["late"] or d["waiting_haan"]:
                    send_morning(tenant)
                    out["morning"] += 1
        except Exception:
            log.exception("ispnoc tick failed for %s", tenant)
    return out
