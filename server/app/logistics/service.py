"""Logistics Sahayak: Hoola as a logistics coordinator for a trader / manufacturer / transporter, end to end.

  1. Gets the job: "Sharma Traders ko 120 bag cement bhejna hai, gaadi MH30AB1234, invoice 45", a Thok bill, "driver ne bola
     Nagpur cross kar liya", a location the driver shared, a courier AWB, the POD photo.
  2. Does the work: shipment S-0001 (consignor, consignee with GSTIN check, goods + HSN, value, weight, packages, vehicle,
     own / hired / courier, LR, dispatch / ETA); papers by code: LR / consignment note (Carriage by Road Act 2007 s.9, Rules 2011),
     delivery challan (CGST Rule 55), packing list, Thok tax invoice link; e-way bill readiness (Rule 138 limits from thok.rules,
     Part A / Part B, validity 200 km a day / ODC 20 km, 180-day document age, extension window, consolidated EWB) and the NIC JSON.
  3. Tracks: a status timeline ONLY from her / the transporter / the driver / the courier module; delays vs ETA, e-way bill
     expiry while moving, "no news for 12 hours" -> ask the driver.
  4. Ready as a card, a file or a draft: Hinglish customer updates (dispatch, in transit, delay, out for delivery, delivered) as
     wa.me drafts; the e-way bill filing card; LR / challan / packing list PDFs; dispatch board; register Excel; morning note.
  5. Waits for her tap: a customer message goes only from her phone or by her tap on 'Business WhatsApp se bhejo'; an e-way bill
     generate / Part B / extension / consolidated is a filing and goes only by her tap (GSP API) or she does it on the portal.
  6. Delivers and learns: POD photo (EXIF / GPS stripped) closes it; shortage / damage -> claim notice date (180 days from
     booking) and the carrier's limit; on-time % per transporter / route from real dispatch -> delivery times.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import threading
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from sqlalchemy import select

from ..db import new_id, now, session
from . import rules as R
from .models import LogiEwbAsk, LogiMessage, LogiParty, LogiPhoto, LogiSettings, LogiShipment

log = logging.getLogger("santosh.logistics")
_LOCK = threading.Lock()
UTC = timezone.utc


class LogiError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _d(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def _num(v) -> float:
    return R.money(v)


def _rs(v) -> str:
    v = round(float(v or 0))
    s = str(abs(v))
    if len(s) > 3:
        s = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", s[:-3]) + "," + s[-3:]
    return ("-" if v < 0 else "") + "₹" + s


_TZ: dict[str, tuple[float, Any]] = {}


def _tz(tenant: str):
    """Her time zone, READ only (life.tz_of may insert a profile row, which would wait on our own open write session)."""
    import time as _t
    from zoneinfo import ZoneInfo
    hit = _TZ.get(tenant)
    if hit and _t.monotonic() - hit[0] < 300:
        return hit[1]
    tz = ZoneInfo("Asia/Kolkata")
    try:
        from ..db import Profile
        with session() as s:
            p = s.get(Profile, tenant)
            if p is not None and p.timezone:
                tz = ZoneInfo(p.timezone)
    except Exception:
        pass
    _TZ[tenant] = (_t.monotonic(), tz)
    return tz


def _now() -> datetime:
    return now()


def today(tenant: str) -> date:
    return _now().astimezone(_tz(tenant)).date()


def _aw(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _local(tenant: str, dt: datetime | None) -> str:
    dt = _aw(dt)
    return dt.astimezone(_tz(tenant)).strftime("%d %b %H:%M") if dt else ""


def _date(v) -> date | None:
    if isinstance(v, date):
        return v
    if v in (None, ""):
        return None
    from ..analyst.service import _date as d
    return d(str(v).strip()[:10]) or d(str(v).strip())


def _phone(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if len(d) == 10 and d[0] in "6789" else ""


def _hash(*parts) -> str:
    return hashlib.sha256(_d(list(parts)).encode()).hexdigest()


def _wa(phone: str, text: str) -> str:
    return f"https://wa.me/91{phone}?text={quote(text)}" if len(phone) == 10 else ""


def _sms(phone: str, text: str) -> str:
    return f"sms:+91{phone}?body={quote(text)}" if len(phone) == 10 else ""


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("logistics publish failed")


_HOUR = re.compile(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|baje)?", re.I)


def when(text, tenant: str, base: datetime | None = None) -> datetime | None:
    """Her words -> an aware time. '24-10-2026 18:00', '2026-10-24T18:00', 'kal shaam', 'parso 11 baje', '2 din', '5 ghante',
    'aaj raat'. Nothing understood -> None (never a guess)."""
    if isinstance(text, datetime):
        return _aw(text)
    t = _s(text).lower()
    if not t:
        return None
    tz = _tz(tenant)
    base = (_aw(base) or _now()).astimezone(tz)
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})[ t](\d{1,2}):(\d{2})(?::\d{2})?(?:\.\d+)?([+-]\d{2}:?\d{2}|z)?", t)
    if m:
        dt = datetime.fromisoformat(t.upper().replace("Z", "+00:00").replace(" ", "T"))
        return dt if dt.tzinfo else dt.replace(tzinfo=tz)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(din|day|days|ghante|ghanta|hour|hours|hrs|hr)\b", t)
    if m and not re.search(r"\d{1,2}[-/.]\d{1,2}", t):
        n = float(m.group(1))
        return (base + (timedelta(days=n) if m.group(2).startswith(("din", "day")) else timedelta(hours=n))).astimezone(UTC)
    day: date | None = None
    dm = re.search(r"(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?", t)
    if dm:
        y = int(dm.group(3)) if dm.group(3) else base.year
        y = y + 2000 if y < 100 else y
        try:
            day = date(y, int(dm.group(2)), int(dm.group(1)))
        except ValueError:
            return None
        rest = t[dm.end():]
    else:
        rest = t
        if "parso" in t or "day after" in t:
            day = base.date() + timedelta(days=2)
        elif "kal" in t or "tomorrow" in t:
            day = base.date() + timedelta(days=1)
        elif "aaj" in t or "today" in t or "abhi" in t or "shaam" in t or "raat" in t or "baje" in t:
            day = base.date()
        else:
            d0 = _date(t)
            if d0:
                day, rest = d0, ""
    if day is None:
        return None
    hh, mm = None, 0
    hm = _HOUR.search(rest)
    if hm and (hm.group(2) or hm.group(3)):
        hh, mm = int(hm.group(1)), int(hm.group(2) or 0)
        ap = (hm.group(3) or "").lower()
        if ap == "pm" and hh < 12:
            hh += 12
        elif ap == "am" and hh == 12:
            hh = 0
        elif ap == "baje" and hh < 8 and ("subah" not in t):
            hh += 12
        if ("shaam" in t or "raat" in t) and hh < 12:
            hh += 12
    if hh is None:
        hh = 9 if "subah" in t else 18 if "shaam" in t else 21 if "raat" in t else 12 if "dopahar" in t else 18
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return datetime.combine(day, time(hh, mm), tzinfo=tz).astimezone(UTC)


# ---------------------------------------------------------------- settings / keys
SETTING_KEYS = ("firm", "role", "gstin", "address", "place", "pincode", "phone", "carrier_reg", "gta_rate", "lr_prefix", "dc_prefix",
                "grace_h", "silent_h", "morning_time", "terms")


def _st(s, tenant: str) -> LogiSettings:
    r = s.get(LogiSettings, tenant)
    if r is None:
        r = LogiSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _sv(r: LogiSettings) -> dict:
    out = {k: getattr(r, k) for k in SETTING_KEYS}
    out["state"] = r.gstin[:2] if r.gstin else ""
    out["ewb"] = {"provider": r.ewb_provider, "joined": bool(r.ewb_sealed), "label": r.ewb_label}
    return out


def settings(tenant: str) -> dict:
    with session() as s:
        return _sv(_st(s, tenant))


def save_settings(tenant: str, **kw: Any) -> dict:
    from ..india.money import gstin_ok
    with session() as s:
        r = _st(s, tenant)
        if kw.get("gstin"):
            g = _s(kw["gstin"]).upper()
            if not gstin_ok(g):
                raise LogiError(f"GSTIN galat lagta hai: {g}")
            r.gstin = g
        for k in ("firm", "address", "place", "carrier_reg", "terms"):
            if kw.get(k) is not None:
                setattr(r, k, _s(kw[k])[:600])
        if kw.get("role"):
            if kw["role"] not in ("trader", "manufacturer", "transporter"):
                raise LogiError("role: trader | manufacturer | transporter")
            r.role = kw["role"]
        if kw.get("pincode"):
            p = re.sub(r"\D", "", _s(kw["pincode"]))
            if len(p) != 6:
                raise LogiError("PIN code 6 ank ka.")
            r.pincode = p
        if kw.get("phone"):
            p = _phone(kw["phone"])
            if not p:
                raise LogiError("Phone 10 ank ka chahiye.")
            r.phone = p
        if kw.get("gta_rate") not in (None, ""):
            g = float(kw["gta_rate"])
            if g not in (0.0,) + R.GTA_RATES:
                raise LogiError("GTA GST: 5 (bina ITC) ya 18 (ITC ke saath), ya 0 agar aap GTA nahi.")
            r.gta_rate = g
        for k in ("lr_prefix", "dc_prefix"):
            if kw.get(k):
                v = re.sub(r"[^A-Z0-9]", "", _s(kw[k]).upper())[:6]
                if v:
                    setattr(r, k, v)
        for k in ("grace_h", "silent_h"):
            if kw.get(k) not in (None, ""):
                setattr(r, k, max(0.5, min(72.0, float(kw[k]))))
        if kw.get("morning_time"):
            if not re.fullmatch(r"\d{1,2}:\d{2}", _s(kw["morning_time"])):
                raise LogiError("Subah ka samay HH:MM.")
            r.morning_time = _s(kw["morning_time"]).zfill(5)
        return _sv(r)


def set_ewb_keys(tenant: str, provider: str, creds: dict | None = None) -> dict:
    """Typed ONLY in the app. Sealed with the bazar vault; never returned, logged or shown to the model."""
    from ..bazar.security import vault
    from . import ewb as E
    if provider not in E.PROVIDERS:
        raise LogiError("provider: manual | gsp")
    with session() as s:
        r = _st(s, tenant)
        if provider == "manual":
            r.ewb_provider, r.ewb_sealed, r.ewb_label = "manual", "", ""
            return _sv(r)["ewb"]
        c = {k: _s(v) for k, v in (creds or {}).items() if k in E.Gsp.needs + ("auth_path", "api_path")}
        missing = [k for k in E.Gsp.needs if not c.get(k)]
        if missing:
            raise LogiError("GSP ke liye chahiye: " + ", ".join(missing))
        if not c["base_url"].startswith("https://"):
            raise LogiError("GSP ka address https:// wala.")
        r.ewb_provider, r.ewb_sealed = "gsp", vault().seal(_d(c))
        host = re.sub(r"^https://", "", c["base_url"]).split("/")[0]
        r.ewb_label = f"{host} · {c['gstin'][:2]}XXXX{c['gstin'][-4:]}"
        return _sv(r)["ewb"]


def _ewb_client(tenant: str):
    from ..bazar.security import vault
    from . import ewb as E
    with session() as s:
        r = _st(s, tenant)
        prov, sealed = r.ewb_provider, r.ewb_sealed
    creds = _j(vault().open(sealed), {}) if sealed else {}
    return E.get(prov if sealed else "manual", creds)


# ---------------------------------------------------------------- parties
def _pv(p: LogiParty) -> dict:
    return {"id": p.id, "name": p.name, "gstin": p.gstin, "address": p.address, "place": p.place, "pincode": p.pincode,
            "state": p.state, "phone": p.phone, "no_messages": p.no_messages, "kind": p.kind, "trans_id": p.trans_id}


def _party(s, tenant: str, ref: str) -> LogiParty | None:
    ref = _s(ref)
    if not ref:
        return None
    p = s.get(LogiParty, ref)
    if p and p.tenant_id == tenant:
        return p
    rows = s.scalars(select(LogiParty).where(LogiParty.tenant_id == tenant)).all()
    low = ref.lower()
    for p in rows:
        if p.name.lower() == low or (p.gstin and p.gstin == ref.upper()) or (p.phone and p.phone == _phone(ref)):
            return p
    hits = [p for p in rows if low in p.name.lower()]
    return hits[0] if len(hits) == 1 else None


def save_party(tenant: str, name: str = "", party: str = "", **kw: Any) -> dict:
    from ..india.money import gstin_ok
    with session() as s:
        p = _party(s, tenant, party) if party else None
        if party and not p:
            raise LogiError("Party nahi mili.")
        if p is None:
            if not _s(name):
                raise LogiError("Party ka naam chahiye.")
            p = _party(s, tenant, name)
            if p is None or p.name.lower() != _s(name).lower():
                p = LogiParty(tenant_id=tenant, name=_s(name)[:160])
                s.add(p)
        warn = []
        if kw.get("gstin"):
            g = _s(kw["gstin"]).upper()
            if not gstin_ok(g):
                raise LogiError(f"GSTIN galat lagta hai ({g}): check digit / state code mel nahi kha raha.")
            p.gstin, p.state = g, g[:2]
        if kw.get("state"):
            st = re.sub(r"\D", "", _s(kw["state"]))[:2]
            if st:
                p.state = st.zfill(2)
        for k in ("address", "place"):
            if kw.get(k) is not None:
                setattr(p, k, _s(kw[k])[:400])
        if kw.get("pincode"):
            pc = re.sub(r"\D", "", _s(kw["pincode"]))
            if len(pc) != 6:
                raise LogiError("PIN code 6 ank ka.")
            p.pincode = pc
        if kw.get("phone"):
            ph = _phone(kw["phone"])
            if not ph:
                warn.append("Phone number samajh nahi aaya (10 ank).")
            else:
                p.phone = ph
        if kw.get("kind") in ("customer", "supplier", "transporter"):
            p.kind = kw["kind"]
        if kw.get("trans_id"):
            p.trans_id = _s(kw["trans_id"]).upper()[:15]
        if kw.get("no_messages") is not None:
            p.no_messages = bool(kw["no_messages"])
        s.flush()
        return {"party": _pv(p), "warnings": warn}


def parties(tenant: str, kind: str = "", q: str = "") -> list[dict]:
    with session() as s:
        rows = s.scalars(select(LogiParty).where(LogiParty.tenant_id == tenant).order_by(LogiParty.name)).all()
        return [_pv(p) for p in rows if (not kind or p.kind == kind) and (not q or q.lower() in p.name.lower())]


# ---------------------------------------------------------------- shipments
def _goods(lines, text: str = "") -> list[dict]:
    out = []
    src = list(lines or [])
    if not src and text:
        from ..thok.rules import parse_order
        src = [{"name": x["item"], "qty": x["qty"], "unit": x["unit"], "rate": x["rate"]} for x in parse_order(text)]
    for g in src:
        if not isinstance(g, dict):
            continue
        name = _s(g.get("name") or g.get("item") or g.get("description"))
        if not name:
            continue
        qty = _num(g.get("qty"))
        rate = _num(g.get("rate"))
        val = _num(g.get("value")) or (qty * rate if qty and rate else 0.0)
        hsn = re.sub(r"\D", "", _s(g.get("hsn")))[:8]
        out.append({"name": name[:120], "hsn": hsn, "qty": qty, "unit": R.uqc(_s(g.get("unit"))), "value": R.r2(val),
                    "gst": float(_num(g.get("gst") or g.get("gst_pct"))) if g.get("gst") not in (None, "") or g.get("gst_pct") not in (None, "") else None})
    return out


def _next_number(st: LogiSettings) -> str:
    st.seq = (st.seq or 0) + 1
    return f"S-{st.seq:04d}"


def _fy(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def _sh(s, tenant: str, ref: str) -> LogiShipment:
    ref = _s(ref)
    sh = s.get(LogiShipment, ref) if ref else None
    if sh and sh.tenant_id == tenant:
        return sh
    if ref:
        q = select(LogiShipment).where(LogiShipment.tenant_id == tenant)
        num = ref.upper()
        if re.fullmatch(r"S-?\d+", num):
            num = "S-" + num.lstrip("S-").zfill(4)
        sh = (s.scalars(q.where(LogiShipment.number == num)).first() or s.scalars(q.where(LogiShipment.lr_no == ref)).first()
              or s.scalars(q.where(LogiShipment.doc_no == ref)).first() or s.scalars(q.where(LogiShipment.vehicle_no == R.clean_vehicle(ref))
                                                                                   .order_by(LogiShipment.created_at.desc())).first()
              or s.scalars(q.where(LogiShipment.awb == ref)).first())
        if sh is None and re.sub(r"\D", "", ref) and len(re.sub(r"\D", "", ref)) == 12:
            for x in s.scalars(q).all():
                if _j(x.ewb, {}).get("no") == re.sub(r"\D", "", ref):
                    return x
        if sh:
            return sh
    raise LogiError("Shipment nahi mila (S-0001 / LR / invoice / gaadi no. bataiye).")


SHIP_KEYS = ("direction", "doc_type", "doc_no", "doc_date", "reason", "weight_kg", "packages", "package_kind", "mode", "fleet",
             "vehicle_no", "odc", "courier", "awb", "freight", "freight_by", "from_place", "to_place", "distance_km", "note",
             "value", "lr_no")


def _apply(s, tenant: str, sh: LogiShipment, kw: dict) -> list[str]:
    """Write fields onto a shipment. Returns warnings."""
    warn: list[str] = []
    if kw.get("direction") in ("out", "in", "carry"):
        sh.direction = kw["direction"]
    if kw.get("doc_type"):
        if kw["doc_type"] not in R.DOC_TYPE:
            raise LogiError("doc_type: invoice | bill_of_supply | challan | bill_of_entry | other")
        sh.doc_type = kw["doc_type"]
    if kw.get("doc_no"):
        dn = _s(kw["doc_no"])
        if len(dn) > 16:
            raise LogiError("Invoice / challan number 16 akshar se lamba nahi ho sakta (GST niyam).")
        sh.doc_no = dn
    if kw.get("doc_date"):
        d = _date(kw["doc_date"])
        if not d:
            raise LogiError("Invoice ki tareekh samajh nahi aayi.")
        sh.doc_date = d.isoformat()
    if kw.get("reason"):
        if kw["reason"] not in R.SUB_SUPPLY:
            raise LogiError("reason: " + " | ".join(R.SUB_SUPPLY))
        sh.reason = kw["reason"]
    for k in ("weight_kg", "freight", "distance_km", "value"):
        if kw.get(k) not in (None, ""):
            setattr(sh, k, max(0.0, _num(kw[k])))
    if kw.get("packages") not in (None, ""):
        sh.packages = max(0, int(_num(kw["packages"])))
    for k in ("package_kind", "courier", "from_place", "to_place"):
        if kw.get(k) is not None:
            setattr(sh, k, _s(kw[k])[:80])
    if kw.get("awb") is not None:
        sh.awb = re.sub(r"\s", "", _s(kw["awb"]))[:40]
        if sh.awb and sh.fleet != "courier":
            sh.fleet, sh.mode = "courier", "courier"
    if kw.get("note") is not None:
        sh.note = _s(kw["note"])[:1000]
    if kw.get("mode"):
        if kw["mode"] not in ("road", "rail", "air", "ship", "courier"):
            raise LogiError("mode: road | rail | air | ship | courier")
        sh.mode = kw["mode"]
    if kw.get("fleet"):
        if kw["fleet"] not in ("own", "hired", "courier"):
            raise LogiError("fleet: own | hired | courier")
        sh.fleet = kw["fleet"]
    if kw.get("freight_by"):
        if kw["freight_by"] not in ("paid", "to_pay", "tbb"):
            raise LogiError("freight_by: paid | to_pay | tbb")
        sh.freight_by = kw["freight_by"]
    if kw.get("odc") is not None:
        sh.odc = bool(kw["odc"])
    if kw.get("lr_no"):
        sh.lr_no = _s(kw["lr_no"])[:20]
    if kw.get("vehicle_no") is not None:
        v = R.clean_vehicle(kw["vehicle_no"])
        if v and not R.vehicle_ok(v):
            warn.append(f"Gaadi no. {v} ka format ajeeb hai (jaise MH30AB1234); e-way bill mein galat no. = maal ruk sakta hai.")
        if v and sh.vehicle_no and v != sh.vehicle_no and _j(sh.ewb, {}).get("no"):
            warn.append("Gaadi badli: e-way bill ka Part B update karna padega (card bhejiye: action=ewb kind=part_b).")
        sh.vehicle_no = v
    tr = _j(sh.transporter, {})
    for k_in, k in (("transporter_name", "name"), ("transporter_gstin", "gstin"), ("transporter_phone", "phone")):
        if kw.get(k_in):
            val = _s(kw[k_in])
            if k == "phone":
                val = _phone(val) or ""
            if k == "gstin":
                val = val.upper()
                from ..india.money import gstin_ok
                if not gstin_ok(val) and not re.fullmatch(r"\d{2}[A-Z0-9]{13}", val):
                    warn.append("Transporter ka GSTIN / Transporter ID galat lagta hai.")
            tr[k] = val
    sh.transporter = _d(tr)
    dr = _j(sh.driver, {})
    if kw.get("driver_name"):
        dr["name"] = _s(kw["driver_name"])[:60]
    if kw.get("driver_phone"):
        p = _phone(kw["driver_phone"])
        if p:
            dr["phone"] = p
        else:
            warn.append("Driver ka phone 10 ank ka chahiye.")
    sh.driver = _d(dr)
    for k in ("dispatch", "eta"):
        if kw.get(k):
            t = when(kw[k], tenant)
            if not t:
                warn.append(f"{'Nikalne' if k == 'dispatch' else 'Pahunchne'} ka samay samajh nahi aaya: '{kw[k]}'.")
            elif k == "eta":
                sh.eta = t
            else:
                sh.dispatch_at = t
    return warn


def new_shipment(tenant: str, consignee: str = "", goods: list | None = None, goods_text: str = "", thok_order: str = "", conv: str = "",
                 **kw: Any) -> dict:
    """One consignment. Consignee by name from her party book (made if new) with GSTIN checked. A Thok bill fills it."""
    from ..india.money import gstin_ok
    g = _s(kw.get("consignee_gstin")).upper()
    if g and not gstin_ok(g):
        raise LogiError(f"Consignee ka GSTIN galat lagta hai ({g}): check digit / state code mel nahi kha raha.")
    if kw.get("consignee_pincode") and len(re.sub(r"\D", "", _s(kw["consignee_pincode"]))) != 6:
        raise LogiError("Consignee ka PIN code 6 ank ka.")
    th: dict = {}
    if thok_order:
        from ..thok import service as TS
        try:
            th = TS.get_order(tenant, thok_order)
        except TS.ThokError as e:
            raise LogiError(str(e))
        if th.get("status") != "billed":
            raise LogiError("Yeh Thok order abhi bill nahi hua: pehle bill banaiye (aapki haan se).")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        cname = _s(consignee) or th.get("party", "")
        if not cname:
            raise LogiError("Maal kisko jaana hai (consignee) bataiye.")
        p = _party(s, tenant, cname)
        if p is None:
            p = LogiParty(tenant_id=tenant, name=cname[:160])
            s.add(p)
            s.flush()
        sh = LogiShipment(tenant_id=tenant, number=_next_number(st), consignee_id=p.id)
        s.add(sh)
        s.flush()
    if any(kw.get(k) for k in ("consignee_gstin", "consignee_address", "consignee_place", "consignee_pincode", "consignee_phone",
                               "consignee_state")) or th:
        save_party(tenant, party=p.id, gstin=kw.get("consignee_gstin") or "", address=kw.get("consignee_address"),
                   place=kw.get("consignee_place"), pincode=kw.get("consignee_pincode") or "", phone=kw.get("consignee_phone") or th.get("phone", ""),
                   state=kw.get("consignee_state") or "")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        sh = s.get(LogiShipment, sh.id)
        p = s.get(LogiParty, sh.consignee_id)
        gl = _goods(goods, goods_text)
        if th:
            gl = gl or [{"name": _s(x.get("name") or x.get("item")), "hsn": re.sub(r"\D", "", _s(x.get("hsn")))[:8], "qty": _num(x.get("qty")),
                         "unit": R.uqc(_s(x.get("unit"))), "value": R.r2(_num(x.get("taxable") or x.get("amount"))),
                         "gst": _num(x.get("gst_pct") or x.get("gst"))} for x in th.get("lines", [])]
            sh.thok_order, sh.doc_no, sh.doc_date, sh.tax = th["id"], th.get("number", "")[:16], th.get("bill_date", ""), float(th.get("tax") or 0)
            sh.value = float(th.get("taxable") or 0)
        sh.goods = _d(gl)
        if not sh.value:
            sh.value = R.r2(sum(g["value"] for g in gl))
        if kw.get("tax") not in (None, ""):
            sh.tax = _num(kw["tax"])
        sh.consignor = _d({"name": st.firm, "gstin": st.gstin, "address": st.address, "place": st.place, "pincode": st.pincode,
                           "state": st.gstin[:2], "phone": st.phone})
        sh.consignee = _d(_pv(p))
        sh.from_place = st.place
        sh.to_place = p.place
        if st.role == "transporter":
            sh.direction = "carry"
        warn = _apply(s, tenant, sh, kw)
        if sh.direction == "carry" and kw.get("consignor"):
            sh.consignor = _d({"name": _s(kw["consignor"]), "gstin": _s(kw.get("consignor_gstin")).upper(), "place": _s(kw.get("consignor_place")),
                               "state": _s(kw.get("consignor_gstin"))[:2]})
        sh.timeline = _d([{"at": _now().isoformat(), "status": "booked", "text": "Shipment banaya", "by": "owner", "source": "her"}])
        sh.last_update_at = _now()
        s.flush()
        v = _view(s, tenant, sh)
    v["warnings"] = warn + v["warnings"]
    _publish(tenant, "logistics_shipment", {"shipment": v, "say": v["say"]}, conv)
    return {"shipment": v, "say": v["say"]}


def update_shipment(tenant: str, ref: str, conv: str = "", **kw: Any) -> dict:
    with _LOCK, session() as s:
        sh = _sh(s, tenant, ref)
        if sh.status in ("delivered", "cancelled") and not kw.get("note"):
            raise LogiError("Yeh shipment band ho chuka hai.")
        if kw.get("goods") or kw.get("goods_text"):
            sh.goods = _d(_goods(kw.get("goods"), _s(kw.get("goods_text"))))
            if not kw.get("value"):
                sh.value = R.r2(sum(g["value"] for g in _j(sh.goods, [])))
        if kw.get("tax") not in (None, ""):
            sh.tax = _num(kw["tax"])
        warn = _apply(s, tenant, sh, kw)
        s.flush()
        v = _view(s, tenant, sh)
    v["warnings"] = warn + v["warnings"]
    _publish(tenant, "logistics_shipment", {"shipment": v, "say": v["say"]}, conv)
    return {"shipment": v, "say": (("; ".join(warn) + " ") if warn else "") + v["say"]}


def _ewb_view(tenant: str, sh: LogiShipment, at: datetime | None = None) -> dict:
    at = at or _now()
    cr, ce = _j(sh.consignor, {}), _j(sh.consignee, {})
    need = R.ewb_needed(sh.value + (sh.tax or 0), cr.get("state", ""), ce.get("state", ""))
    e = _j(sh.ewb, {})
    upto = when(e.get("valid_upto"), tenant) if e.get("valid_upto") else None
    gen = when(e.get("date"), tenant) if e.get("date") else None
    out = {**need, "no": e.get("no", ""), "valid_upto": _local(tenant, upto), "part_b": bool(e.get("part_b") or sh.vehicle_no),
           "days": R.validity_days(sh.distance_km, sh.odc), "cewb": e.get("cewb", "")}
    if e.get("no") and sh.status in R.OPEN:
        al = R.ewb_alert(upto, at, gen)
        if al:
            out["alert"] = al
    return out


def _checks(tenant: str, sh: LogiShipment) -> list[dict]:
    from ..india.money import gstin_ok
    out = []
    ce = _j(sh.consignee, {})
    goods = _j(sh.goods, [])
    if ce.get("gstin") and not gstin_ok(ce["gstin"]):
        out.append({"level": "bad", "text": "Consignee ka GSTIN galat."})
    if not goods:
        out.append({"level": "warn", "text": "Maal ki list nahi (naam, HSN, maatra)."})
    if not sh.value:
        out.append({"level": "warn", "text": "Maal ki keemat nahi: e-way bill zaroori hai ya nahi, pata nahi chalega."})
    e = _ewb_view(tenant, sh)
    if e["needed"] and not e["no"]:
        out.append({"level": "bad" if sh.status in R.MOVING else "warn",
                    "text": "E-way bill chahiye, abhi bana nahi." + (" Maal raste mein hai: Rs 10,000 ya tax ka jurmana ho sakta hai." if sh.status in R.MOVING else "")})
    if e["needed"]:
        if any(not g.get("hsn") for g in goods):
            out.append({"level": "warn", "text": "Kuch items ka HSN nahi (e-way bill mein zaroori)."})
        if not sh.distance_km:
            out.append({"level": "warn", "text": "Doori (km) nahi: e-way bill ki validity isi se banti hai."})
        if not ce.get("pincode"):
            out.append({"level": "warn", "text": "Consignee ka PIN code nahi."})
        if sh.mode == "road" and not sh.vehicle_no:
            out.append({"level": "warn", "text": "Gaadi no. nahi: Part B ke bina maal nahi chal sakta (50 km tak transporter ke paas chhodkar)."})
    if sh.doc_date and R.doc_too_old(_date(sh.doc_date), today(tenant)):
        out.append({"level": "bad", "text": "Invoice / challan 180 din se purana: is par e-way bill nahi banega."})
    if sh.vehicle_no and not R.vehicle_ok(sh.vehicle_no):
        out.append({"level": "warn", "text": f"Gaadi no. {sh.vehicle_no} sahi format mein nahi lagta."})
    if sh.status in R.MOVING and not sh.eta:
        out.append({"level": "info", "text": "Pahunchne ka andaaza (ETA) nahi diya: der pakadne ke liye bataiye."})
    return out


def _grace(s, tenant: str) -> float:
    r = s.get(LogiSettings, tenant)
    return r.grace_h if r else 2.0


def _delay_h(sh: LogiShipment, grace: float, at: datetime | None = None) -> float:
    if sh.status not in R.MOVING:
        return 0.0
    return R.delay_of(_aw(sh.eta), at or _now(), grace)


def _view(s, tenant: str, sh: LogiShipment) -> dict:
    ce, cr = _j(sh.consignee, {}), _j(sh.consignor, {})
    msgs = s.scalars(select(LogiMessage).where(LogiMessage.shipment_id == sh.id).order_by(LogiMessage.at.desc()).limit(8)).all()
    asks = s.scalars(select(LogiEwbAsk).where(LogiEwbAsk.shipment_id == sh.id).order_by(LogiEwbAsk.at.desc()).limit(5)).all()
    photos = s.scalars(select(LogiPhoto).where(LogiPhoto.shipment_id == sh.id)).all()
    ewb = _ewb_view(tenant, sh)
    checks = _checks(tenant, sh)
    late = _delay_h(sh, _grace(s, tenant))
    tl = _j(sh.timeline, [])
    for t in tl:
        t["when"] = _local(tenant, when(t.get("at"), tenant)) if t.get("at") else ""
    v = {"id": sh.id, "number": sh.number, "direction": sh.direction, "status": sh.status, "status_label": R.LABEL.get(sh.status, sh.status),
         "consignor": cr, "consignee": ce, "goods": _j(sh.goods, []), "value": sh.value, "tax": sh.tax, "doc_type": sh.doc_type,
         "doc_no": sh.doc_no, "doc_date": sh.doc_date, "reason": sh.reason, "thok_order": sh.thok_order, "weight_kg": sh.weight_kg,
         "packages": sh.packages, "package_kind": sh.package_kind, "mode": sh.mode, "fleet": sh.fleet,
         "transporter": _j(sh.transporter, {}), "vehicle_no": sh.vehicle_no, "odc": sh.odc, "driver": _j(sh.driver, {}),
         "courier": sh.courier, "awb": sh.awb, "lr_no": sh.lr_no, "lr_date": sh.lr_date, "freight": sh.freight, "freight_by": sh.freight_by,
         "from_place": sh.from_place, "to_place": sh.to_place, "distance_km": sh.distance_km,
         "dispatch_at": _local(tenant, sh.dispatch_at), "eta": _local(tenant, sh.eta), "delivered_at": _local(tenant, sh.delivered_at),
         "late_h": late, "ewb": ewb, "timeline": tl[-30:], "location": _j(sh.last_location, {}), "pod": _j(sh.pod, {}),
         "photos": [{"id": p.id, "stage": p.stage} for p in photos], "note": sh.note,
         "messages": [_mv(m) for m in msgs], "ewb_asks": [_av(a) for a in asks], "checks": checks,
         "warnings": [c["text"] for c in checks if c["level"] in ("bad", "warn")]}
    bits = [f"{sh.number} {ce.get('name', '')}: {v['status_label']}"]
    if sh.vehicle_no:
        bits.append(f"gaadi {sh.vehicle_no}")
    if v["eta"] and sh.status in R.OPEN:
        bits.append(f"ETA {v['eta']}")
    if late:
        bits.append(f"{late:g} ghante late")
    if ewb.get("alert"):
        bits.append(ewb["alert"]["text"])
    elif ewb["needed"] and not ewb["no"]:
        bits.append("e-way bill baaki")
    v["say"] = ", ".join(bits) + "."
    return v


def get(tenant: str, ref: str) -> dict:
    with session() as s:
        return _view(s, tenant, _sh(s, tenant, ref))


def shipments(tenant: str, status: str = "", q: str = "", limit: int = 100) -> list[dict]:
    with session() as s:
        qq = select(LogiShipment).where(LogiShipment.tenant_id == tenant)
        if status == "open":
            qq = qq.where(LogiShipment.status.in_(R.OPEN))
        elif status:
            qq = qq.where(LogiShipment.status == status)
        rows = s.scalars(qq.order_by(LogiShipment.created_at.desc()).limit(max(1, min(500, limit)))).all()
        out = []
        g = _grace(s, tenant)
        for sh in rows:
            if q and q.lower() not in (sh.number + " " + sh.consignee + " " + sh.vehicle_no + " " + sh.lr_no + " " + sh.doc_no).lower():
                continue
            ce = _j(sh.consignee, {})
            out.append({"id": sh.id, "number": sh.number, "status": sh.status, "status_label": R.LABEL.get(sh.status, sh.status),
                        "consignee": ce.get("name", ""), "to_place": sh.to_place, "vehicle_no": sh.vehicle_no, "lr_no": sh.lr_no,
                        "eta": _local(tenant, sh.eta), "late_h": _delay_h(sh, g), "ewb_no": _j(sh.ewb, {}).get("no", ""),
                        "value": sh.value, "awb": sh.awb})
        return out


# ---------------------------------------------------------------- tracking
def _add_event(sh: LogiShipment, status: str, text: str, by: str, source: str, at: datetime | None = None, where: str = "") -> dict:
    tl = _j(sh.timeline, [])
    ev = {"at": (at or _now()).isoformat(), "status": status, "text": _s(text)[:300], "by": by, "source": source}
    if where:
        ev["where"] = _s(where)[:80]
    tl.append(ev)
    sh.timeline = _d(tl[-120:])
    sh.last_update_at = _now()
    return ev


def update(tenant: str, ref: str, status: str = "", text: str = "", where: str = "", eta: str = "", at: str = "", by: str = "owner",
           source: str = "her", conv: str = "", reason: str = "") -> dict:
    """A real update from her / the transporter / the driver (source her | transporter | driver | courier). Status from the words
    when not given. Nothing here is made up: no words, no status = refused."""
    st_new = _s(status) or R.status_from_words(text)
    if st_new and st_new not in R.STATUSES:
        raise LogiError("status: " + " | ".join(R.STATUSES))
    if not st_new and not _s(text) and not _s(where) and not _s(eta):
        raise LogiError("Kya update hai? (jaise 'nikal gaya', 'Nagpur cross kiya', 'kal shaam tak pahunchega')")
    loc = R.parse_location(text) or R.parse_location(where)
    drafts = []
    with _LOCK, session() as s:
        sh = _sh(s, tenant, ref)
        if sh.status in ("delivered", "cancelled") and st_new not in ("", "returned"):
            raise LogiError(f"{sh.number} pehle hi {R.LABEL[sh.status]}.")
        t_at = when(at, tenant) if at else None
        if eta:
            e = when(eta, tenant)
            if not e:
                raise LogiError(f"ETA samajh nahi aaya: '{eta}'.")
            sh.eta = e
        if st_new == "delayed" and not (reason or text):
            raise LogiError("Der ki wajah bataiye (jaam / gaadi kharab / naka...), andaaza nahi lagata.")
        _add_event(sh, st_new or sh.status, text or (f"ETA {_local(tenant, sh.eta)}" if eta else where), by, source, t_at,
                   where if not loc else "")
        if loc:
            sh.last_location = _d({**loc, "at": _now().isoformat(), "by": source})
        if st_new:
            sh.status = st_new
            if st_new == "dispatched" and not sh.dispatch_at:
                sh.dispatch_at = t_at or _now()
            if st_new == "delivered":
                sh.delivered_at = t_at or _now()
        s.flush()
        sid = sh.id
    kind = {"dispatched": "dispatch", "in_transit": "in_transit", "delayed": "delay", "breakdown": "delay", "held": "delay",
            "out_for_delivery": "out_for_delivery", "delivered": "delivered"}.get(st_new, "")
    if kind:
        why = reason or (text if st_new in ("delayed", "breakdown", "held") else "")
        m = draft(tenant, sid, kind, conv=conv, reason=why, where=where or (text if st_new == "in_transit" else ""))
        if m.get("message"):
            drafts.append(m["message"])
    v = get(tenant, sid)
    _publish(tenant, "logistics_shipment", {"shipment": v, "say": v["say"]}, conv)
    say = v["say"] + (" Graahak ke liye message taiyaar (aap bhejiye)." if drafts else "")
    return {"shipment": v, "drafts": drafts, "say": say}


def location(tenant: str, ref: str, text: str, by: str = "driver", conv: str = "") -> dict:
    """A location share she forwarded (driver's live / current location link or 'lat, lng')."""
    loc = R.parse_location(text)
    if not loc:
        raise LogiError("Isme location nahi mili: driver se WhatsApp 'Location' share karwa kar link bhejiye.")
    with _LOCK, session() as s:
        sh = _sh(s, tenant, ref)
        sh.last_location = _d({**loc, "at": _now().isoformat(), "by": by})
        _add_event(sh, sh.status, "Location mili", "owner", by)
        s.flush()
        sid = sh.id
    v = get(tenant, sid)
    return {"location": loc, "shipment": v, "say": f"{v['number']} ki location save ki: {loc['maps']}"}


def _courier_track(tenant: str, courier: str, awb: str) -> dict | None:
    """Neighbour courier module (Courier desk) when present: {status, events[{at, what, where}]}. None = not available."""
    try:
        from ..courier import service as CS  # type: ignore
    except Exception:
        return None
    fn = getattr(CS, "track_awb", None)
    if not fn:
        return None
    try:
        return fn(tenant, courier=courier, awb=awb)
    except Exception as e:
        log.info("courier track failed: %s", e)
        return {"error": str(e)[:200]}


_COURIER_MAP = {"delivered": "delivered", "in_transit": "in_transit", "out_for_delivery": "out_for_delivery", "picked": "dispatched",
                "booked": "booked", "cancelled": "cancelled", "failed": "held", "rto": "returned", "returned": "returned"}


def track(tenant: str, ref: str, conv: str = "") -> dict:
    with session() as s:
        sh = _sh(s, tenant, ref)
        awb, cou, sid, num = sh.awb, sh.courier, sh.id, sh.number
    if not awb:
        return {"say": f"{num} courier se nahi gaya (AWB nahi). Gaadi ki khabar driver / transporter se lijiye.", "shipment": get(tenant, sid)}
    r = _courier_track(tenant, cou, awb)
    if r is None:
        return {"say": f"Courier tracking Courier desk se judti hai (abhi juda nahi). AWB {awb} apne courier app mein dekhiye, phir status bataiye.",
                "shipment": get(tenant, sid)}
    if r.get("error"):
        return {"say": f"Courier ne jawab nahi diya: {r['error']}", "shipment": get(tenant, sid)}
    new = 0
    with _LOCK, session() as s:
        sh = s.get(LogiShipment, sid)
        seen = {(e.get("at"), e.get("text")) for e in _j(sh.timeline, []) if e.get("source") == "courier"}
        for e in r.get("events") or []:
            key = (_s(e.get("at")), _s(e.get("what"))[:300])
            if key in seen or not key[1]:
                continue
            tl = _j(sh.timeline, [])
            tl.append({"at": key[0] or _now().isoformat(), "status": sh.status, "text": key[1], "where": _s(e.get("where"))[:80],
                       "by": cou or "courier", "source": "courier"})
            sh.timeline = _d(tl[-120:])
            new += 1
        st = _COURIER_MAP.get(_s(r.get("status")), "")
        old = sh.status
        if st and st != sh.status and sh.status not in ("delivered", "cancelled"):
            sh.status = st
            if st == "delivered":
                sh.delivered_at = _now()
        if new or st:
            sh.last_update_at = _now()
        s.flush()
    if st and st != old and st in ("delivered", "out_for_delivery"):
        draft(tenant, sid, st if st == "out_for_delivery" else "delivered", conv=conv)
    v = get(tenant, sid)
    return {"shipment": v, "new_events": new, "say": f"Courier: {R.LABEL.get(v['status'], v['status'])}; {new} nayi entry."}


# ---------------------------------------------------------------- customer messages (drafts she sends)
def _mv(m: LogiMessage) -> dict:
    return {"id": m.id, "shipment_id": m.shipment_id, "kind": m.kind, "text": m.text, "phone": m.phone, "status": m.status, "via": m.via,
            "hash": m.hash, "wa_link": _wa(m.phone, m.text) if m.status == "draft" else "", "sms_link": _sms(m.phone, m.text) if m.status == "draft" else ""}


def draft(tenant: str, ref: str, kind: str, conv: str = "", reason: str = "", where: str = "", text: str = "") -> dict:
    """A customer update draft in Hinglish. Never sent by Hoola; one waiting draft per shipment + kind."""
    if kind not in ("dispatch", "in_transit", "delay", "out_for_delivery", "delivered", "custom"):
        raise LogiError("kind: dispatch | in_transit | delay | out_for_delivery | delivered | custom")
    with _LOCK, session() as s:
        sh = _sh(s, tenant, ref)
        st = _st(s, tenant)
        ce = _j(sh.consignee, {})
        p = s.get(LogiParty, sh.consignee_id) if sh.consignee_id else None
        if p is not None and p.no_messages:
            return {"say": f"{ce.get('name', '')} ne message mana kiya hai: draft nahi banaya.", "message": None}
        dr, e = _j(sh.driver, {}), _j(sh.ewb, {})
        f = {"name": ce.get("name", ""), "business": st.firm, "ref": f"({sh.doc_no})" if sh.doc_no else f"({sh.number})", "lr": sh.lr_no,
             "goods": _goods_line(_j(sh.goods, []), sh.packages, sh.package_kind), "vehicle": sh.vehicle_no,
             "eta": _local(tenant, sh.eta), "ewb": e.get("no", ""), "awb": sh.awb, "courier": sh.courier,
             "driver": " ".join(x for x in (dr.get("name", ""), dr.get("phone", "")) if x), "reason": reason, "where": where,
             "receiver": _j(sh.pod, {}).get("receiver", "")}
        body = _s(text) if kind == "custom" else R.customer_text(kind, f)
        if not body:
            raise LogiError("Message ka text chahiye.")
        from ..net import policy
        if policy.secret_found(body):
            raise LogiError("Isme OTP / PIN / card jaisi baat hai: aisa message nahi banta.")
        for old in s.scalars(select(LogiMessage).where(LogiMessage.shipment_id == sh.id, LogiMessage.kind == kind,
                                                       LogiMessage.status == "draft")).all():
            old.status = "dropped"
        phone = ce.get("phone") or (p.phone if p else "")
        m = LogiMessage(id=new_id("lm"), tenant_id=tenant, shipment_id=sh.id, kind=kind, phone=phone, text=body[:1500])
        m.hash = _hash(m.id, phone, m.text)
        s.add(m)
        s.flush()
        mv = _mv(m)
        num = sh.number
    blanks = re.findall(r"\[[^\]]+\]", body)
    say = f"{num}: graahak ke liye message taiyaar." + (f" Bhejne se pehle bhariye: {', '.join(blanks)}." if blanks else "") + \
        ("" if phone else " Graahak ka phone nahi: copy karke bhejiye.")
    _publish(tenant, "logistics_update", {"message": mv, "number": num, "blanks": blanks, "say": say}, conv)
    return {"message": mv, "blanks": blanks, "say": say}


def _goods_line(goods: list, packages: int, kind: str) -> str:
    if packages:
        return f"{packages} {kind or 'packet'}"
    if goods:
        g = goods[0]
        more = f" aur {len(goods) - 1} aur" if len(goods) > 1 else ""
        return f"{g['name']}{(' ' + format(g['qty'], 'g') + ' ' + g['unit']) if g.get('qty') else ''}{more}"
    return "aapka maal"


def edit_message(tenant: str, msg_id: str, text: str) -> dict:
    from ..net import policy
    with session() as s:
        m = s.get(LogiMessage, msg_id)
        if not m or m.tenant_id != tenant or m.status != "draft":
            raise LogiError("Draft nahi mila.")
        if policy.secret_found(text):
            raise LogiError("Isme OTP / PIN / card jaisi baat hai.")
        m.text = _s(text)[:1500]
        m.hash = _hash(m.id, m.phone, m.text)
        return {"message": _mv(m), "say": "Draft badla."}


def message_sent(tenant: str, msg_id: str) -> dict:
    """She sent it from her own WhatsApp / SMS (wa.me) and says so."""
    with session() as s:
        m = s.get(LogiMessage, msg_id)
        if not m or m.tenant_id != tenant:
            raise LogiError("Message nahi mila.")
        if m.status == "draft":
            m.status, m.via = "sent", "self"
        return {"message": _mv(m), "say": "Theek, bhej diya mark kiya."}


async def send_business(tenant: str, msg_id: str, hash_: str, by_tap: bool = False) -> dict:
    """Business WhatsApp (official Cloud API, inside Meta's 24 h window) — ONLY from her tap in the app."""
    if not by_tap:
        raise LogiError("Graahak ko message sirf aapke tap se jaata hai.")
    from ..employee import inbox
    from ..employee.models import BizContact
    with session() as s:
        m = s.get(LogiMessage, msg_id)
        if not m or m.tenant_id != tenant or m.status != "draft":
            raise LogiError("Draft nahi mila / pehle hi gaya.")
        if not hash_ or hash_ != m.hash:
            raise LogiError("Draft badal gaya: naya dekh kar tap kijiye.")
        if not m.phone:
            raise LogiError("Graahak ka phone nahi.")
        c = s.scalars(select(BizContact).where(BizContact.tenant_id == tenant, BizContact.wa_id.in_((m.phone, "91" + m.phone)))).first()
        cid, text = (c.id if c else ""), m.text
    if not cid:
        raise LogiError("Is graahak ne business WhatsApp par kabhi message nahi kiya: apne WhatsApp se (wa.me) bhejiye.")
    if re.search(r"\[[^\]]+\]", text):
        raise LogiError("Message mein khaali jagah [..] baaki hai: pehle bhariye.")
    try:
        await inbox.send(tenant, cid, text, by="owner")
    except inbox.InboxError as e:
        raise LogiError(str(e))
    with session() as s:
        m = s.get(LogiMessage, msg_id)
        m.status, m.via = "sent", "business"
        return {"message": _mv(m), "say": "Business WhatsApp se bhej diya."}


# ---------------------------------------------------------------- e-way bill
def _ewb_payload(tenant: str, sh: LogiShipment) -> dict:
    """NIC e-way bill fields (bulk JSON / API). Values from the shipment only; empty where she hasn't said."""
    cr, ce, tr = _j(sh.consignor, {}), _j(sh.consignee, {}), _j(sh.transporter, {})
    goods = _j(sh.goods, [])
    intra = (cr.get("state") or "") == (ce.get("state") or "") or not ce.get("state")
    cg = sg = ig = 0.0
    items = []
    for g in goods:
        rate = float(g.get("gst") or 0)
        val = float(g.get("value") or 0)
        it = {"productName": g["name"][:100], "productDesc": g["name"][:100], "hsnCode": int(g["hsn"]) if g.get("hsn") else "",
              "quantity": g.get("qty") or 0, "qtyUnit": g.get("unit") or "NOS", "taxableAmount": R.r2(val),
              "cgstRate": rate / 2 if intra else 0, "sgstRate": rate / 2 if intra else 0, "igstRate": 0 if intra else rate, "cessRate": 0,
              "cessNonAdvol": 0}
        if intra:
            cg += val * rate / 200
            sg += val * rate / 200
        else:
            ig += val * rate / 100
        items.append(it)
    if not any(g.get("gst") is not None for g in goods) and sh.tax:
        if intra:
            cg = sg = sh.tax / 2
        else:
            ig = sh.tax
    d = _date(sh.doc_date)
    supply_out = sh.direction != "in"
    p = {"supplyType": "O" if supply_out else "I", "subSupplyType": R.SUB_SUPPLY.get(sh.reason, 1), "subSupplyDesc": "",
         "docType": R.DOC_TYPE.get(sh.doc_type, "INV"), "docNo": sh.doc_no, "docDate": d.strftime("%d/%m/%Y") if d else "",
         "transactionType": 1,
         "fromGstin": cr.get("gstin") or "URP", "fromTrdName": cr.get("name", ""), "fromAddr1": (cr.get("address") or "")[:100], "fromAddr2": "",
         "fromPlace": cr.get("place", "") or sh.from_place, "fromPincode": int(cr["pincode"]) if cr.get("pincode") else "",
         "fromStateCode": int(cr["state"]) if cr.get("state") else "", "actFromStateCode": int(cr["state"]) if cr.get("state") else "",
         "toGstin": ce.get("gstin") or "URP", "toTrdName": ce.get("name", ""), "toAddr1": (ce.get("address") or "")[:100], "toAddr2": "",
         "toPlace": ce.get("place", "") or sh.to_place, "toPincode": int(ce["pincode"]) if ce.get("pincode") else "",
         "toStateCode": int(ce["state"]) if ce.get("state") else "", "actToStateCode": int(ce["state"]) if ce.get("state") else "",
         "totalValue": R.r2(sh.value), "cgstValue": R.r2(cg), "sgstValue": R.r2(sg), "igstValue": R.r2(ig), "cessValue": 0,
         "cessNonAdvolValue": 0, "otherValue": 0, "totInvValue": R.r2(sh.value + cg + sg + ig),
         "transporterId": tr.get("gstin", ""), "transporterName": tr.get("name", ""), "transDocNo": sh.lr_no if sh.mode != "road" else "",
         "transDocDate": "", "transMode": R.TRANS_MODE.get(sh.mode if sh.mode != "courier" else "road", 1), "transDistance": int(round(sh.distance_km or 0)),
         "vehicleNo": sh.vehicle_no if sh.mode in ("road", "courier") else "", "vehicleType": "O" if sh.odc else "R",
         "itemList": items}
    return p


def ewb_ready(tenant: str, ref: str) -> dict:
    """Readiness for e-way bill generation: blockers (can't be made) and warnings, plus the Part A / Part B data."""
    with session() as s:
        sh = _sh(s, tenant, ref)
        p = _ewb_payload(tenant, sh)
        e = _ewb_view(tenant, sh)
        num, status, odc, ddate = sh.number, sh.status, sh.odc, _date(sh.doc_date)
    block, warn = [], []
    if not p["docNo"]:
        block.append("Invoice / challan number nahi.")
    if not p["docDate"]:
        block.append("Invoice / challan ki tareekh nahi.")
    elif R.doc_too_old(ddate, today(tenant)):
        block.append("Document 180 din se purana: e-way bill nahi banega (1 Jan 2025 se).")
    if p["fromGstin"] == "URP" and p["supplyType"] == "O":
        block.append("Aapka GSTIN Niyam mein daaliye.")
    if not p["toPincode"]:
        block.append("Consignee ka PIN code nahi.")
    if not p["fromPincode"]:
        block.append("Aapka PIN code (Niyam) nahi.")
    if not p["itemList"]:
        block.append("Maal ki list nahi.")
    if any(not it["hsnCode"] for it in p["itemList"]):
        block.append("Har item ka HSN chahiye.")
    if not p["totalValue"]:
        block.append("Maal ki keemat nahi.")
    if not p["transDistance"]:
        block.append("Doori (km) nahi: portal PIN se andaaza dikhata hai, sahi doori aap bataiye.")
    if not p["vehicleNo"] and not p["transporterId"] and p["transMode"] == 1:
        warn.append("Gaadi no. / transporter ID nahi: sirf Part A banega, maal chalane se pehle Part B zaroori.")
    if not e["needed"]:
        warn.append(e["why"])
    if e["no"]:
        warn.append(f"Is shipment ka EWB {e['no']} pehle se hai.")
    days = R.validity_days(p["transDistance"], odc)
    return {"number": num, "status": status, "needed": e["needed"], "why": e["why"], "blockers": block, "warnings": warn,
            "validity_days": days, "payload": p,
            "say": (f"{num}: e-way bill ke liye {len(block)} cheez baaki: " + "; ".join(block)) if block else
                   f"{num}: e-way bill ka data taiyaar ({days} din ki validity, {p['transDistance']} km)."}


def _av(a: LogiEwbAsk) -> dict:
    return {"id": a.id, "shipment_id": a.shipment_id, "kind": a.kind, "status": a.status, "hash": a.hash, "checks": _j(a.checks, {}),
            "result": _j(a.result, {}), "payload": _j(a.payload, {})}


EWB_KIND_LABEL = {"generate": "E-way bill banana", "part_b": "Part B (gaadi) badalna", "extend": "E-way bill ki validity badhana",
                  "consolidated": "Consolidated e-way bill"}


def ewb_request(tenant: str, ref: str, kind: str = "generate", vehicle_no: str = "", reason: str = "", from_place: str = "",
                from_state: str = "", from_pincode: str = "", remaining_km=None, refs: list | None = None, conv: str = "") -> dict:
    """Prepare an e-way bill filing as a card. It goes to the portal ONLY on her tap (POST /api/logistics/ewb/{id}/decide)."""
    if kind not in EWB_KIND_LABEL:
        raise LogiError("kind: generate | part_b | extend | consolidated")
    st_ = settings(tenant)
    checks: dict = {}
    with session() as s:
        sh = _sh(s, tenant, ref)
        e = _j(sh.ewb, {})
        sid, num = sh.id, sh.number
        if kind == "generate":
            pass
        elif kind == "part_b":
            v = R.clean_vehicle(vehicle_no or sh.vehicle_no)
            if not e.get("no"):
                raise LogiError("Pehle e-way bill ka number chahiye.")
            if not R.vehicle_ok(v):
                raise LogiError("Nayi gaadi ka sahi number bataiye (jaise MH30AB1234).")
            if not reason:
                raise LogiError("Gaadi badalne ki wajah bataiye (breakdown / transhipment / other).")
            payload = {"ewbNo": int(e["no"]), "vehicleNo": v, "fromPlace": from_place or sh.from_place, "fromState": int(from_state or (st_["state"] or 0) or 0),
                       "reasonCode": {"breakdown": "1", "transhipment": "2", "others": "3", "first_time": "4"}.get(reason, "3"),
                       "reasonRem": reason[:50], "transDocNo": "", "transDocDate": "", "transMode": "1"}
        elif kind == "extend":
            if not e.get("no"):
                raise LogiError("Pehle e-way bill ka number chahiye.")
            upto = when(e.get("valid_upto"), tenant) if e.get("valid_upto") else None
            if upto:
                a, b = R.extend_window(upto)
                if not (a <= _now() <= b):
                    raise LogiError(f"Extension sirf {a.astimezone(_tz(tenant)).strftime('%d %b %H:%M')} se "
                                    f"{b.astimezone(_tz(tenant)).strftime('%d %b %H:%M')} tak maang sakte hain.")
            km = _num(remaining_km)
            if not km:
                raise LogiError("Baaki doori (km) bataiye.")
            if not (from_place and from_pincode):
                raise LogiError("Maal abhi kahan hai (shehar + PIN) bataiye.")
            if not reason:
                raise LogiError("Extension ki wajah (natural calamity / law and order / transhipment / accident / others).")
            payload = {"ewbNo": int(e["no"]), "vehicleNo": sh.vehicle_no, "fromPlace": from_place, "fromState": int(from_state or (st_["state"] or 0) or 0),
                       "remainingDistance": int(km), "transDocNo": "", "transDocDate": "", "transMode": "1",
                       "extnRsnCode": {"natural_calamity": 1, "law_order": 2, "transhipment": 4, "accident": 5, "others": 99}.get(reason, 99),
                       "extnRemarks": reason[:50], "fromPincode": int(re.sub(r"\D", "", from_pincode) or 0), "consignmentStatus": "M",
                       "transitType": ""}
            checks["remaining_days"] = R.validity_days(km, sh.odc)
        else:
            nos = []
            others = [sh] + [_sh(s, tenant, r) for r in (refs or []) if _s(r)]
            for x in others:
                n = _j(x.ewb, {}).get("no")
                if not n:
                    raise LogiError(f"{x.number} ka e-way bill nahi: consolidated ke liye har maal ka EWB chahiye.")
                nos.append({"ewbNo": int(n)})
            v = R.clean_vehicle(vehicle_no or sh.vehicle_no)
            if not R.vehicle_ok(v):
                raise LogiError("Ek gaadi ka sahi number chahiye.")
            if len(nos) < 2:
                raise LogiError("Consolidated mein kam se kam do e-way bill.")
            payload = {"fromPlace": from_place or sh.from_place, "fromState": int(from_state or (st_["state"] or 0) or 0), "vehicleNo": v,
                       "transMode": "1", "transDocNo": "", "transDocDate": "", "tripSheetEwbBills": nos}
            checks["shipments"] = [x.number for x in others]
    if kind == "generate":
        rd = ewb_ready(tenant, sid)
        if rd["blockers"]:
            raise LogiError(rd["say"])
        payload = rd["payload"]
        checks = {"warnings": rd["warnings"], "validity_days": rd["validity_days"], "needed": rd["needed"], "why": rd["why"]}
    with _LOCK, session() as s:
        for old in s.scalars(select(LogiEwbAsk).where(LogiEwbAsk.shipment_id == sid, LogiEwbAsk.kind == kind,
                                                      LogiEwbAsk.status == "waiting")).all():
            old.status = "stale"
        a = LogiEwbAsk(id=new_id("le"), tenant_id=tenant, shipment_id=sid, kind=kind, payload=_d(payload), checks=_d(checks))
        a.hash = _hash(a.id, kind, payload)
        s.add(a)
        s.flush()
        av = _av(a)
    prov = st_["ewb"]["provider"] if st_["ewb"]["joined"] else "manual"
    how = ("Haan karte hi aapke GSP se portal par jaayega." if prov == "gsp" else
           "Haan karne par JSON file + portal ke steps milenge; aap portal par upload / bharti hain (OTP aapka), ya Computer Operator se bharwaiye.")
    say = f"{num}: {EWB_KIND_LABEL[kind]} ka card bheja: aapke tap ke bina portal par kuch nahi jaata. {how}"
    _publish(tenant, "logistics_ewb", {"ask": av, "number": num, "label": EWB_KIND_LABEL[kind], "how": how, "provider": prov, "say": say}, conv)
    return {"ask": av, "status": "needs_tap", "say": say}


def decide_ewb(tenant: str, ask_id: str, yes: bool, hash_: str, by_tap: bool = False, conv: str = "") -> dict:
    """ONLY her tap in the app. Rebuilt payload must still match the card (a changed shipment = stale card)."""
    if not by_tap:
        raise LogiError("E-way bill portal par sirf aapke tap se jaata hai.")
    with _LOCK, session() as s:
        a = s.get(LogiEwbAsk, ask_id)
        if not a or a.tenant_id != tenant:
            raise LogiError("Card nahi mila.")
        if a.status != "waiting":
            raise LogiError(f"Yeh card pehle hi {a.status}.")
        if not hash_ or hash_ != a.hash:
            raise LogiError("Card badal gaya: naya card dekhiye.")
        if not yes:
            a.status, a.decided_at = "rejected", _now()
            return {"ask": _av(a), "say": "Theek, portal par kuch nahi bheja."}
        kind, payload, sid = a.kind, _j(a.payload, {}), a.shipment_id
        if kind == "generate":
            sh = s.get(LogiShipment, sid)
            if _hash(a.id, kind, _ewb_payload(tenant, sh)) != a.hash:
                a.status = "stale"
                raise LogiError("Card ke baad shipment badla: naya card banaiye.")
    from . import ewb as E
    client = _ewb_client(tenant)
    try:
        res = client.run(kind, payload)
    except E.EwbError as e:
        with session() as s:
            a = s.get(LogiEwbAsk, ask_id)
            a.status, a.result, a.decided_at = "failed", _d({"error": str(e)}), _now()
        raise LogiError(str(e))
    files = []
    with _LOCK, session() as s:
        a = s.get(LogiEwbAsk, ask_id)
        a.decided_at = _now()
        sh = s.get(LogiShipment, sid)
        num = sh.number
        if res["mode"] == "gsp":
            a.status = "done"
            ev = _j(sh.ewb, {})
            if kind == "generate" and res.get("ewb_no"):
                ev.update({"no": re.sub(r"\D", "", res["ewb_no"]), "date": _ndt(tenant, res.get("ewb_date")), "valid_upto": _ndt(tenant, res.get("valid_upto")),
                           "part_b": bool(payload.get("vehicleNo")), "by": "gsp"})
            elif kind == "part_b":
                sh.vehicle_no = payload["vehicleNo"]
                ev.update({"part_b": True, "valid_upto": _ndt(tenant, res.get("valid_upto")) or ev.get("valid_upto", "")})
            elif kind == "extend":
                ev.update({"valid_upto": _ndt(tenant, res.get("valid_upto")) or ev.get("valid_upto", ""), "extended": (ev.get("extended") or 0) + 1})
            elif kind == "consolidated":
                ev["cewb"] = res.get("ewb_no", "")
            sh.ewb = _d(ev)
            _add_event(sh, sh.status, f"{EWB_KIND_LABEL[kind]}: ho gaya" + (f" (EWB {ev.get('no')})" if ev.get("no") else ""), "owner", "her")
        else:
            a.status = "manual"
        a.result = _d({k: v for k, v in res.items() if k != "json"} | ({"json_chars": len(res.get("json", ""))} if res.get("json") else {}))
        s.flush()
        av = _av(a)
    if res["mode"] == "manual" and res.get("json"):
        from .. import chatfiles
        f = chatfiles.store(tenant, f"EWB-{num}-{kind}.json", res["json"].encode(), "application/json")
        files.append(f)
        _publish(tenant, "pc_file", {**f, "source": "logistics", "title": f"{num} e-way bill JSON"}, conv)
    say = (f"{num}: {EWB_KIND_LABEL[kind]} ho gaya." if res["mode"] == "gsp" else
           f"{num}: JSON taiyaar. Portal par: " + " → ".join(res.get("steps", [])[:2]) + ". Phir EWB number bataiye.")
    v = get(tenant, sid)
    _publish(tenant, "logistics_shipment", {"shipment": v, "say": v["say"]}, conv)
    return {"ask": av, "result": {k: v for k, v in res.items() if k != "json"}, "files": files, "shipment": v, "say": say}


def _ndt(tenant: str, v) -> str:
    """NIC dates '24/10/2026 11:59:00 PM' -> ISO with offset."""
    t = _s(v)
    if not t:
        return ""
    for fmt in ("%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %I:%M %p", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(t, fmt).replace(tzinfo=_tz(tenant)).isoformat()
        except ValueError:
            continue
    w = when(t, tenant)
    return w.isoformat() if w else ""


def ewb_set(tenant: str, ref: str, ewb_no: str, valid_upto: str = "", generated: str = "", conv: str = "") -> dict:
    """She made it on the portal herself and tells the number + 'Valid Upto' (or Hoola works it out from the distance)."""
    n = re.sub(r"\D", "", _s(ewb_no))
    if len(n) != 12:
        raise LogiError("E-way bill number 12 ank ka hota hai.")
    with _LOCK, session() as s:
        sh = _sh(s, tenant, ref)
        gen = when(generated, tenant) if generated else _now()
        upto = when(valid_upto, tenant) if valid_upto else None
        computed = False
        if valid_upto and not upto:
            raise LogiError("'Valid Upto' samajh nahi aaya.")
        if not upto and sh.distance_km and sh.vehicle_no:
            upto = R.valid_upto(gen.astimezone(_tz(tenant)), sh.distance_km, sh.odc).astimezone(UTC)
            computed = True
        sh.ewb = _d({"no": n, "date": (gen or _now()).isoformat(), "valid_upto": upto.isoformat() if upto else "", "part_b": bool(sh.vehicle_no),
                     "by": "her", "computed": computed})
        _add_event(sh, sh.status, f"E-way bill {n}", "owner", "her")
        s.flush()
        sid = sh.id
        for a in s.scalars(select(LogiEwbAsk).where(LogiEwbAsk.shipment_id == sid, LogiEwbAsk.kind == "generate",
                                                    LogiEwbAsk.status.in_(("manual", "waiting")))).all():
            a.status = "done"
    v = get(tenant, sid)
    extra = " (Valid Upto doori se nikala; portal wala alag ho to bataiye.)" if computed else "" if upto else " Valid Upto bataiye taaki expiry yaad dila sakoon."
    return {"shipment": v, "say": f"{v['number']}: EWB {n} save. Valid {v['ewb']['valid_upto'] or 'pata nahi'}.{extra}"}


# ---------------------------------------------------------------- documents (PDF by code)
def _pdf_base():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    return buf, pdf, A4


def _pdf_text(pdf, x, y, txt, size=9.0, bold=False):
    pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    pdf.drawString(x, y, _ascii(txt)[:120])


def _ascii(t) -> str:
    return re.sub(r"[^\x20-\x7E]", "", str(t or "").replace("₹", "Rs ").replace("·", "-"))


def _assign_lr(s, tenant: str, sh: LogiShipment) -> None:
    if sh.lr_no:
        return
    st = _st(s, tenant)
    st.lr_seq = (st.lr_seq or 0) + 1
    sh.lr_no = f"{st.lr_prefix}/{_fy(today(tenant))}/{st.lr_seq:04d}"[:20]
    sh.lr_date = today(tenant).isoformat()


def lr_pdf(tenant: str, ref: str) -> tuple[bytes, str]:
    """Goods receipt / consignment note (Carriage by Road Act s.9): three copies (consignor, consignee, driver / office)."""
    with _LOCK, session() as s:
        sh = _sh(s, tenant, ref)
        st = _st(s, tenant)
        _assign_lr(s, tenant, sh)
        s.flush()
        v = _view(s, tenant, sh)
        firm, reg, terms, gta, gstin, addr = st.firm, st.carrier_reg, st.terms, st.gta_rate, st.gstin, st.address
        role = st.role
    tr = v["transporter"]
    carrier = firm if role == "transporter" or v["fleet"] == "own" else (tr.get("name") or "[transporter]")
    buf, pdf, (w, h) = _pdf_base()
    cap = R.liability_cap(v["freight"], v["value"] + v["tax"])
    for copy in ("CONSIGNOR COPY (original)", "CONSIGNEE COPY", "DRIVER / OFFICE COPY"):
        y = h - 40
        _pdf_text(pdf, 40, y, "GOODS RECEIPT / CONSIGNMENT NOTE (LR)", 13, True)
        _pdf_text(pdf, w - 210, y, copy, 8.5, True)
        y -= 18
        _pdf_text(pdf, 40, y, f"Carrier: {carrier}", 10, True)
        y -= 13
        if role == "transporter" or v["fleet"] == "own":
            _pdf_text(pdf, 40, y, f"{addr}  GSTIN: {gstin or '-'}  Regn (Carriage by Road Act): {reg or '[registration no.]'}", 8)
            y -= 12
        elif tr.get("gstin"):
            _pdf_text(pdf, 40, y, f"Transporter GSTIN / ID: {tr['gstin']}", 8)
            y -= 12
        _pdf_text(pdf, 40, y, f"LR No: {v['lr_no']}    Date: {v['lr_date']}    Shipment: {v['number']}", 10, True)
        y -= 16
        for title, p in (("Consignor", v["consignor"]), ("Consignee", v["consignee"])):
            _pdf_text(pdf, 40, y, f"{title}: {p.get('name', '')}  GSTIN: {p.get('gstin') or '-'}", 9, True)
            y -= 11
            _pdf_text(pdf, 52, y, f"{p.get('address', '')} {p.get('place', '')} {p.get('pincode', '')}  Ph: {p.get('phone', '')}", 8)
            y -= 14
        _pdf_text(pdf, 40, y, f"From: {v['from_place'] or '-'}   To: {v['to_place'] or '-'}   Vehicle: {v['vehicle_no'] or '-'}   "
                              f"Driver: {v['driver'].get('name', '-')}", 9)
        y -= 14
        _pdf_text(pdf, 40, y, "Packages / description (said to contain)                HSN        Qty         Value", 8.5, True)
        y -= 12
        for g in v["goods"][:12]:
            _pdf_text(pdf, 40, y, f"{g['name'][:48]:<50} {g.get('hsn') or '-':<10} {format(g.get('qty') or 0, 'g')} {g.get('unit', '')}", 8)
            _pdf_text(pdf, w - 120, y, _rs(g.get("value")), 8)
            y -= 11
        _pdf_text(pdf, 40, y, f"No. of packages: {v['packages'] or '-'} {v['package_kind']}   Actual weight: {v['weight_kg'] or '-'} kg   "
                              f"Declared value: {_rs(v['value'] + v['tax'])}", 9)
        y -= 13
        fb = {"paid": "PAID", "to_pay": "TO PAY", "tbb": "TO BE BILLED"}.get(v["freight_by"], "-")
        _pdf_text(pdf, 40, y, f"Freight: {_rs(v['freight']) if v['freight'] else '-'} ({fb})" +
                  (f"   GST on GTA: {gta:g}%" + (" (RCM: payable by recipient)" if gta == 5 else "") if gta else ""), 9)
        y -= 13
        _pdf_text(pdf, 40, y, f"Invoice / challan: {v['doc_no'] or '-'} {v['doc_date']}   E-way bill: {v['ewb']['no'] or '-'}"
                              f"{'   Valid upto: ' + v['ewb']['valid_upto'] if v['ewb']['valid_upto'] else ''}", 9)
        y -= 18
        _pdf_text(pdf, 40, y, "Liability (Carriage by Road Act 2007 s.10, Rules 2011 r.12): for loss / damage limited to 10 times the", 7.5)
        y -= 10
        _pdf_text(pdf, 40, y, "freight, not more than the declared value, unless a higher risk rate was agreed. Claims: written notice", 7.5)
        y -= 10
        _pdf_text(pdf, 40, y, "within 180 days of booking (s.16). Dangerous / hazardous goods must be declared in the forwarding note (s.8).", 7.5)
        y -= 12
        for line in _ascii(terms).splitlines()[:4]:
            _pdf_text(pdf, 40, y, line, 7.5)
            y -= 10
        y -= 26
        _pdf_text(pdf, 40, y, "Consignor's signature", 8.5)
        _pdf_text(pdf, 230, y, "For the carrier", 8.5)
        _pdf_text(pdf, 400, y, "Received in good condition (consignee)", 8.5)
        _pdf_text(pdf, 40, 30, f"Cap shown on card: {_ascii(cap['text'])}", 6.5)
        pdf.showPage()
    pdf.save()
    return buf.getvalue(), v["lr_no"]


def challan_pdf(tenant: str, ref: str) -> tuple[bytes, str]:
    """Delivery challan (CGST Rule 55) when goods move without an invoice. Triplicate."""
    with _LOCK, session() as s:
        sh = _sh(s, tenant, ref)
        st = _st(s, tenant)
        if sh.doc_type != "challan" or not sh.doc_no:
            st.dc_seq = (st.dc_seq or 0) + 1
            sh.doc_type, sh.doc_no = "challan", f"{st.dc_prefix}/{_fy(today(tenant))}/{st.dc_seq:04d}"[:16]
            sh.doc_date = sh.doc_date or today(tenant).isoformat()
            if sh.reason == "supply":
                sh.reason = "others"
        s.flush()
        v = _view(s, tenant, sh)
    buf, pdf, (w, h) = _pdf_base()
    pos = v["consignee"].get("state") or ""
    from ..india.money import STATE_CODES
    for copy in ("ORIGINAL FOR CONSIGNEE", "DUPLICATE FOR TRANSPORTER", "TRIPLICATE FOR CONSIGNOR"):
        y = h - 40
        _pdf_text(pdf, 40, y, "DELIVERY CHALLAN", 13, True)
        _pdf_text(pdf, w - 200, y, copy, 8.5, True)
        y -= 18
        cr, ce = v["consignor"], v["consignee"]
        _pdf_text(pdf, 40, y, f"{cr.get('name', '')}  GSTIN: {cr.get('gstin') or '-'}", 10, True)
        y -= 12
        _pdf_text(pdf, 40, y, f"{cr.get('address', '')} {cr.get('place', '')} {cr.get('pincode', '')}", 8)
        y -= 16
        _pdf_text(pdf, 40, y, f"Challan No: {v['doc_no']}   Date: {v['doc_date']}   Purpose: {v['reason'].replace('_', ' ')}", 10, True)
        y -= 14
        _pdf_text(pdf, 40, y, f"Consignee: {ce.get('name', '')}  GSTIN: {ce.get('gstin') or 'Unregistered'}", 9, True)
        y -= 11
        _pdf_text(pdf, 52, y, f"{ce.get('address', '')} {ce.get('place', '')} {ce.get('pincode', '')}", 8)
        y -= 12
        _pdf_text(pdf, 40, y, f"Place of supply: {STATE_CODES.get(pos, '-')} ({pos or '-'})   Vehicle: {v['vehicle_no'] or '-'}   "
                              f"E-way bill: {v['ewb']['no'] or '-'}", 9)
        y -= 16
        _pdf_text(pdf, 40, y, "Sr  Description                                  HSN        Qty          Taxable value   GST%   Tax", 8.5, True)
        y -= 12
        tot = tax = 0.0
        for i, g in enumerate(v["goods"][:16], 1):
            rate = float(g.get("gst") or 0)
            t = g["value"] * rate / 100
            tot += g["value"]
            tax += t
            _pdf_text(pdf, 40, y, f"{i:<3} {g['name'][:42]:<44} {g.get('hsn') or '-':<10} {format(g.get('qty') or 0, 'g')} {g.get('unit', '')}", 8)
            _pdf_text(pdf, w - 210, y, f"{g['value']:,.2f}", 8)
            _pdf_text(pdf, w - 120, y, f"{rate:g}", 8)
            _pdf_text(pdf, w - 85, y, f"{t:,.2f}", 8)
            y -= 11
        y -= 4
        _pdf_text(pdf, 40, y, f"Total taxable: Rs {tot:,.2f}   Tax (where the movement is a supply): Rs {tax:,.2f}", 9, True)
        y -= 34
        _pdf_text(pdf, 40, y, "Receiver's signature", 8.5)
        _pdf_text(pdf, 380, y, f"For {cr.get('name', '')} (authorised signatory)", 8.5)
        _pdf_text(pdf, 40, 30, "Delivery challan under CGST Rule 55. Not a tax invoice.", 6.5)
        pdf.showPage()
    pdf.save()
    return buf.getvalue(), v["doc_no"]


def packing_pdf(tenant: str, ref: str) -> tuple[bytes, str]:
    v = get(tenant, ref)
    buf, pdf, (w, h) = _pdf_base()
    y = h - 40
    _pdf_text(pdf, 40, y, "PACKING LIST", 13, True)
    y -= 18
    _pdf_text(pdf, 40, y, f"{v['consignor'].get('name', '')} -> {v['consignee'].get('name', '')} ({v['to_place']})", 10, True)
    y -= 13
    _pdf_text(pdf, 40, y, f"Shipment {v['number']}   Invoice / challan: {v['doc_no'] or '-'} {v['doc_date']}   LR: {v['lr_no'] or '-'}   "
                          f"Vehicle: {v['vehicle_no'] or '-'}", 9)
    y -= 16
    _pdf_text(pdf, 40, y, "Sr  Item                                              HSN        Qty", 8.5, True)
    y -= 12
    for i, g in enumerate(v["goods"][:30], 1):
        _pdf_text(pdf, 40, y, f"{i:<3} {g['name'][:50]:<52} {g.get('hsn') or '-':<10} {format(g.get('qty') or 0, 'g')} {g.get('unit', '')}", 8)
        y -= 11
    y -= 6
    _pdf_text(pdf, 40, y, f"Packages: {v['packages'] or '-'} {v['package_kind']}   Gross weight: {v['weight_kg'] or '-'} kg", 9, True)
    y -= 30
    _pdf_text(pdf, 40, y, "Packed by", 8.5)
    _pdf_text(pdf, 300, y, "Checked by", 8.5)
    pdf.showPage()
    pdf.save()
    return buf.getvalue(), v["number"]


DOC_KINDS = ("lr", "challan", "packing", "invoice", "ewb_json")


def documents(tenant: str, ref: str, which: list | str | None = None, conv: str = "") -> dict:
    """Dispatch papers as her files (pc_file cards). invoice = the Thok tax invoice when this shipment came from a Thok bill."""
    from .. import chatfiles
    kinds = [which] if isinstance(which, str) and which else list(which or ["lr", "packing"])
    out, notes = [], []
    with session() as s:
        sh = _sh(s, tenant, ref)
        sid, num, thok, dtype = sh.id, sh.number, sh.thok_order, sh.doc_type
    for k in kinds:
        if k not in DOC_KINDS:
            raise LogiError("documents: " + " | ".join(DOC_KINDS))
        if k == "lr":
            data, no = lr_pdf(tenant, sid)
            f = chatfiles.store(tenant, f"LR-{no.replace('/', '-')}.pdf", data, "application/pdf")
            title = f"LR {no}"
        elif k == "challan":
            if thok and dtype == "invoice":
                notes.append("Is maal ka tax invoice (Thok) hai: challan ki zaroorat nahi.")
                continue
            data, no = challan_pdf(tenant, sid)
            f = chatfiles.store(tenant, f"Challan-{no.replace('/', '-')}.pdf", data, "application/pdf")
            title = f"Delivery challan {no}"
        elif k == "packing":
            data, no = packing_pdf(tenant, sid)
            f = chatfiles.store(tenant, f"Packing-{num}.pdf", data, "application/pdf")
            title = f"Packing list {num}"
        elif k == "invoice":
            if not thok:
                notes.append("Tax invoice Thok Sahayak se banta hai (bill aapki haan se); yeh shipment kisi Thok bill se nahi juda.")
                continue
            from ..thok import service as TS
            r = TS.invoice_file(tenant, thok, conv)
            out.append(r.get("file") or r)
            continue
        else:
            rd = ewb_ready(tenant, sid)
            if rd["blockers"]:
                notes.append(rd["say"])
                continue
            from .ewb import bulk_json
            f = chatfiles.store(tenant, f"EWB-{num}.json", bulk_json([rd["payload"]]).encode(), "application/json")
            title = f"{num} e-way bill JSON"
        _publish(tenant, "pc_file", {**f, "source": "logistics", "title": title}, conv)
        out.append(f)
    return {"files": out, "notes": notes, "say": f"{num}: {len(out)} kaagaz taiyaar." + (" " + " ".join(notes) if notes else "")}


# ---------------------------------------------------------------- POD
def _dir(tenant: str, sid: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", tenant)[:64]
    p = Path(os.environ.get("LOGISTICS_DIR") or "data/logistics") / safe / sid
    p.mkdir(parents=True, exist_ok=True)
    return p


def _clean_image(data: bytes) -> bytes:
    """Re-encode from pixels (JPEG <= 1600 px): EXIF / GPS / camera details gone."""
    from PIL import Image, ImageOps
    if not data or len(data) > 20 * 1024 * 1024:
        raise LogiError("Photo khaali ya 20 MB se badi.")
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise LogiError("Yeh photo khul nahi rahi (JPG / PNG / WEBP).")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1600, 1600))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85, optimize=True)
    return out.getvalue()


def add_photo(tenant: str, ref: str, data: bytes, stage: str = "pod", receiver: str = "", remarks: str = "", short=None,
              damaged: bool = False, conv: str = "") -> dict:
    """POD photo (signed LR / delivery receipt), loading or damage photo. A POD closes the shipment as delivered."""
    if stage not in ("pod", "loading", "damage"):
        raise LogiError("stage: pod | loading | damage")
    clean = _clean_image(data)
    with _LOCK, session() as s:
        sh = _sh(s, tenant, ref)
        n = s.scalars(select(LogiPhoto.id).where(LogiPhoto.shipment_id == sh.id)).all()
        if len(n) >= 20:
            raise LogiError("Ek shipment par 20 photo tak.")
        path = _dir(tenant, sh.id) / f"{stage}_{len(n) + 1:02d}.jpg"
        path.write_bytes(clean)
        ph = LogiPhoto(tenant_id=tenant, shipment_id=sh.id, stage=stage, path=str(path))
        s.add(ph)
        s.flush()
        sid, num, created = sh.id, sh.number, _aw(sh.created_at)
        newly = False
        if stage == "pod" or damaged or short:
            pod = _j(sh.pod, {})
            pod.setdefault("photos", []).append(ph.id)
            if receiver:
                pod["receiver"] = _s(receiver)[:80]
            if remarks:
                pod["remarks"] = _s(remarks)[:300]
            if short not in (None, "", 0):
                pod["short"] = _num(short)
            if damaged:
                pod["damaged"] = True
            sh.pod = _d(pod)
        if stage == "pod" and sh.status != "delivered":
            sh.status, sh.delivered_at, newly = "delivered", _now(), True
            _add_event(sh, "delivered", "POD mila" + (f" ({receiver})" if receiver else ""), "owner", "her")
        s.flush()
        pod = _j(sh.pod, {})
        freight, val = sh.freight, sh.value + sh.tax
    notes = []
    if pod.get("damaged") or pod.get("short"):
        cb = R.claim_by(created.astimezone(_tz(tenant)).date() if created else today(tenant))
        cap = R.liability_cap(freight, val)
        notes.append(f"Kami / nuksaan likha gaya: transporter ko likhit claim notice {cb.strftime('%d %b %Y')} se pehle (booking ke 180 din, "
                     f"Carriage by Road Act s.16). {cap['text']}")
    if newly:
        draft(tenant, sid, "delivered", conv=conv)
    v = get(tenant, sid)
    _publish(tenant, "logistics_shipment", {"shipment": v, "say": v["say"]}, conv)
    return {"photo": {"id": ph.id, "stage": stage}, "shipment": v, "notes": notes,
            "say": f"{num}: photo save (location / camera details hata diye)." + (" Deliver mark kiya." if newly else "") + (" " + " ".join(notes) if notes else "")}


def add_photo_file(tenant: str, ref: str, file_id: str, **kw) -> dict:
    """A photo she sent in chat (file_id)."""
    from ..mailbox import service as ms
    try:
        f = ms._file_row(tenant, str(file_id))
        data = Path(f.stored_path).read_bytes()
    except Exception:
        raise LogiError("Woh photo nahi mili (file_id).")
    return add_photo(tenant, ref, data, **kw)


def photo_file(tenant: str, photo_id: str) -> Path:
    with session() as s:
        p = s.get(LogiPhoto, photo_id)
        if not p or p.tenant_id != tenant or not Path(p.path).exists():
            raise LogiError("Photo nahi mili.")
        return Path(p.path)


def cancel(tenant: str, ref: str, reason: str = "", conv: str = "") -> dict:
    with _LOCK, session() as s:
        sh = _sh(s, tenant, ref)
        if sh.status == "delivered":
            raise LogiError("Deliver ho chuka maal cancel nahi hota.")
        sh.status = "cancelled"
        _add_event(sh, "cancelled", reason or "Cancel", "owner", "her")
        e = _j(sh.ewb, {})
        sid = sh.id
    v = get(tenant, sid)
    note = " E-way bill bana tha: portal par 24 ghante ke andar cancel kijiye (aapka login)." if e.get("no") else ""
    return {"shipment": v, "say": f"{v['number']} cancel.{note}"}


# ---------------------------------------------------------------- board / report / learning
def _ontime(tenant: str) -> dict:
    """Real dispatch -> delivery vs ETA per transporter (learned, no guesses)."""
    stats: dict[str, dict] = {}
    with session() as s:
        rows = s.scalars(select(LogiShipment).where(LogiShipment.tenant_id == tenant, LogiShipment.status == "delivered")).all()
        for sh in rows:
            key = _j(sh.transporter, {}).get("name") or sh.courier or ("Apni gaadi" if sh.fleet == "own" else "")
            if not key or not sh.eta or not sh.delivered_at:
                continue
            d = stats.setdefault(key, {"trips": 0, "on_time": 0, "late_h": []})
            d["trips"] += 1
            lh = (_aw(sh.delivered_at) - _aw(sh.eta)).total_seconds() / 3600
            if lh <= 2:
                d["on_time"] += 1
            else:
                d["late_h"].append(round(lh, 1))
    return {k: {"trips": v["trips"], "on_time_pct": round(100 * v["on_time"] / v["trips"]), "avg_late_h": round(sum(v["late_h"]) / len(v["late_h"]), 1) if v["late_h"] else 0}
            for k, v in stats.items()}


def board(tenant: str) -> dict:
    """Daily dispatch board: going today, moving, late, e-way bill alerts, delivered without POD, cards waiting for her."""
    td = today(tenant)
    tz = _tz(tenant)
    with session() as s:
        rows = s.scalars(select(LogiShipment).where(LogiShipment.tenant_id == tenant)).all()
        asks = s.scalars(select(LogiEwbAsk).where(LogiEwbAsk.tenant_id == tenant, LogiEwbAsk.status == "waiting")).all()
        drafts = s.scalars(select(LogiMessage).where(LogiMessage.tenant_id == tenant, LogiMessage.status == "draft")).all()
        out = {"today": [], "moving": [], "late": [], "ewb": [], "no_pod": [], "ewb_missing": []}
        g = _grace(s, tenant)
        for sh in rows:
            item = None
            if sh.status in ("booked", "loaded") and (not sh.dispatch_at or _aw(sh.dispatch_at).astimezone(tz).date() <= td):
                out["today"].append(item := _brief(tenant, sh, g))
            if sh.status in R.MOVING:
                out["moving"].append(item or (item := _brief(tenant, sh, g)))
                if _delay_h(sh, g):
                    out["late"].append(item)
            if sh.status in R.OPEN:
                e = _ewb_view(tenant, sh)
                if e.get("alert"):
                    out["ewb"].append({**(item or _brief(tenant, sh, g)), "alert": e["alert"]})
                elif e["needed"] and not e["no"]:
                    out["ewb_missing"].append(item or _brief(tenant, sh, g))
            if sh.status == "delivered" and not _j(sh.pod, {}).get("photos") and sh.delivered_at and \
                    (_now() - _aw(sh.delivered_at)).days <= 30:
                out["no_pod"].append(_brief(tenant, sh, g))
        out["waiting"] = {"ewb_cards": len(asks), "drafts": len(drafts)}
    bits = []
    if out["today"]:
        bits.append(f"aaj {len(out['today'])} maal nikalna hai")
    if out["moving"]:
        bits.append(f"{len(out['moving'])} raste mein")
    if out["late"]:
        bits.append(f"{len(out['late'])} late ({', '.join(x['number'] for x in out['late'][:3])})")
    if out["ewb"]:
        bits.append(f"{len(out['ewb'])} e-way bill par dhyaan")
    if out["ewb_missing"]:
        bits.append(f"{len(out['ewb_missing'])} ka e-way bill baaki")
    if out["no_pod"]:
        bits.append(f"{len(out['no_pod'])} deliver par POD nahi")
    if asks:
        bits.append(f"{len(asks)} e-way bill card aapke tap ka intezaar")
    if drafts:
        bits.append(f"{len(drafts)} graahak message bhejne baaki")
    out["ontime"] = _ontime(tenant)
    out["say"] = ("Logistics: " + ", ".join(bits) + ".") if bits else "Logistics: aaj kuch baaki nahi."
    return out


def _brief(tenant: str, sh: LogiShipment, grace: float = 2.0) -> dict:
    ce = _j(sh.consignee, {})
    return {"id": sh.id, "number": sh.number, "consignee": ce.get("name", ""), "to_place": sh.to_place, "vehicle_no": sh.vehicle_no,
            "status": sh.status, "status_label": R.LABEL.get(sh.status, sh.status), "eta": _local(tenant, sh.eta), "late_h": _delay_h(sh, grace),
            "phone": _j(sh.driver, {}).get("phone", ""), "ewb_no": _j(sh.ewb, {}).get("no", "")}


def overview(tenant: str) -> dict:
    return {"board": board(tenant), "shipments": shipments(tenant, limit=60), "settings": settings(tenant), "parties": parties(tenant),
            "never": list(R.NEVER)}


def register_file(tenant: str, days: int = 90, conv: str = "") -> dict:
    from openpyxl import Workbook
    from .. import chatfiles
    wb = Workbook()
    ws = wb.active
    ws.title = "Shipments"
    ws.append(["No", "Status", "Consignee", "GSTIN", "To", "Invoice / challan", "Date", "Value", "Vehicle", "Transporter", "LR", "EWB",
               "EWB valid upto", "Dispatched", "ETA", "Delivered", "POD", "Freight", "Freight by"])
    since = _now() - timedelta(days=max(1, days))
    with session() as s:
        for sh in s.scalars(select(LogiShipment).where(LogiShipment.tenant_id == tenant).order_by(LogiShipment.created_at)).all():
            if _aw(sh.created_at) < since:
                continue
            ce, e = _j(sh.consignee, {}), _j(sh.ewb, {})
            ws.append([sh.number, sh.status, ce.get("name", ""), ce.get("gstin", ""), sh.to_place, sh.doc_no, sh.doc_date, sh.value, sh.vehicle_no,
                       _j(sh.transporter, {}).get("name", "") or sh.courier, sh.lr_no, e.get("no", ""),
                       _local(tenant, when(e.get("valid_upto"), tenant)) if e.get("valid_upto") else "", _local(tenant, sh.dispatch_at),
                       _local(tenant, sh.eta), _local(tenant, sh.delivered_at), "yes" if _j(sh.pod, {}).get("photos") else "", sh.freight, sh.freight_by])
    w2 = wb.create_sheet("On-time")
    w2.append(["Transporter", "Trips", "On time %", "Avg late hours"])
    for k, v in _ontime(tenant).items():
        w2.append([k, v["trips"], v["on_time_pct"], v["avg_late_h"]])
    buf = io.BytesIO()
    wb.save(buf)
    f = chatfiles.store(tenant, "Logistics-register.xlsx", buf.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "logistics", "title": "Logistics register"}, conv)
    return {"file": f, "say": "Register Excel taiyaar."}


# ---------------------------------------------------------------- worker
def _once(sh: LogiShipment, key: str) -> bool:
    al = _j(sh.alerts, [])
    if key in al:
        return False
    al.append(key)
    sh.alerts = _d(al[-60:])
    return True


def check_alerts(tenant: str, at: datetime | None = None) -> list[dict]:
    """Late vs ETA, e-way bill expiring / expired while moving, no news while moving. Each told once."""
    at = at or _now()
    out = []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        grace, silent = st.grace_h, st.silent_h
        rows = s.scalars(select(LogiShipment).where(LogiShipment.tenant_id == tenant, LogiShipment.status.in_(R.OPEN))).all()
        for sh in rows:
            ce = _j(sh.consignee, {})
            late = R.delay_of(_aw(sh.eta), at, grace) if sh.status in R.MOVING else 0
            if late and _once(sh, f"late:{_aw(sh.eta).isoformat() if sh.eta else ''}"):
                out.append({"kind": "late", "id": sh.id, "number": sh.number,
                            "text": f"{sh.number} ({ce.get('name', '')}) ETA {_local(tenant, sh.eta)} se {late:g} ghante upar: driver / transporter se poochhiye; "
                                    f"graahak ke liye der ka draft bana sakte hain."})
            e = _j(sh.ewb, {})
            if e.get("no") and e.get("valid_upto"):
                al = R.ewb_alert(when(e["valid_upto"], tenant), at, when(e.get("date"), tenant) if e.get("date") else None)
                if al and al["level"] in ("warn", "bad") and _once(sh, f"{al['kind']}:{e['valid_upto']}"):
                    out.append({"kind": al["kind"], "id": sh.id, "number": sh.number, "text": f"{sh.number}: {al['text']}"})
            last = _aw(sh.last_update_at)
            if sh.status in R.MOVING and last and (at - last).total_seconds() > silent * 3600 and \
                    _once(sh, f"silent:{last.isoformat()[:13]}"):
                dr = _j(sh.driver, {})
                out.append({"kind": "silent", "id": sh.id, "number": sh.number, "phone": dr.get("phone", ""),
                            "text": f"{sh.number}: {int((at - last).total_seconds() // 3600)} ghante se koi khabar nahi. Driver"
                                    f"{(' ' + dr['name']) if dr.get('name') else ''} se location share karwaiye."})
    return out


def due_mornings(at: datetime | None = None) -> list[str]:
    out = []
    at = at or _now()
    with session() as s:
        for r in s.scalars(select(LogiSettings)).all():
            if not s.scalars(select(LogiShipment.id).where(LogiShipment.tenant_id == r.tenant_id).limit(1)).first():
                continue
            local = at.astimezone(_tz(r.tenant_id))
            try:
                hh, mm = [int(x) for x in (r.morning_time or "08:30").split(":")]
            except ValueError:
                hh, mm = 8, 30
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            d = local.date().isoformat()
            if r.last_morning != d and 0 <= late <= 180:
                r.last_morning = d
                out.append(r.tenant_id)
    return out


def send_morning(tenant: str) -> dict:
    from ..events import notify
    from ..net.service import home_conv
    b = board(tenant)
    conv = home_conv(tenant)
    try:
        notify(conv, b["say"])
    except Exception:
        pass
    _publish(tenant, "logistics_day", {"text": b["say"], "board": {k: b[k] for k in ("today", "moving", "late", "ewb", "no_pod", "waiting")}}, conv)
    return {"text": b["say"]}


_LAST_TICK: dict[str, float] = {}


def tick(now_: datetime | None = None) -> dict:
    """Worker (every minute is fine; alerts every 10 minutes). Each alert once; morning note once a day at her time."""
    at = now_ or _now()
    done = {"alerts": 0, "mornings": 0}
    stamp = at.timestamp()
    if now_ is not None or stamp - _LAST_TICK.get("alerts", 0) >= 600:
        _LAST_TICK["alerts"] = stamp
        with session() as s:
            tenants = sorted(set(s.scalars(select(LogiShipment.tenant_id).where(LogiShipment.status.in_(R.OPEN))).all()))
        for t in tenants:
            try:
                for a in check_alerts(t, at):
                    done["alerts"] += 1
                    from ..net.service import home_conv
                    conv = home_conv(t)
                    _publish(t, "logistics_alert", {**a, "say": a["text"]}, conv)
                    try:
                        from ..events import notify
                        notify(conv, "Logistics: " + a["text"])
                    except Exception:
                        pass
            except Exception:
                log.exception("logistics alerts failed for %s", t)
    for t in due_mornings(at):
        try:
            send_morning(t)
            done["mornings"] += 1
        except Exception:
            log.exception("logistics morning failed for %s", t)
    return done
