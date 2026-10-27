"""v0.110 Niryat Sahayak: Hoola as an exporter's coworker, end to end.

  1. Gets the job: "Dubai ke Al Noor ko 2000 kg haldi ka PI banao, FOB Mundra, USD 2.10", the buyer's PO, "container
     nikal gaya, shipping bill 1234567", "Al Noor se 12,000 dollar aaye", "kiska paisa baaki hai".
  2. Does the work, step by step: buyer book (country, currency, payment terms), proforma invoice from her lines (8-digit
     ITC-HS, quantity, rate in foreign currency, weights, packages), Incoterm cost split and FOB value, rupee value at
     her exchange rate, LUT / IGST mode, document list for the Incoterm + payment term, RoDTEP estimate, realisation
     deadline from the shipment date, payments against each shipment.
  3. Checked against the rules and earlier work: sanctioned countries, FTA available (certificate of origin), EU CBAM
     goods, US duty to re-check, HS code digits, DDP / credit risk, LUT valid for this FY, RCMC expiry, RBI 9-month
     (12 for INR) realisation, RoDTEP period (31 Dec 2026).
  4. Ready as a card, a file or a draft: PI PDF, commercial invoice + packing list PDFs (LUT line), the document
     checklist, payment reminder drafts to the buyer, an export register Excel.
  5. Waits for her Haan: the PI goes to the buyer and the commercial invoice is made only on her Haan. The shipping bill,
     certificate of origin, e-BRC and any forward contract are done by her / her CHA / her AD bank - Hoola never logs in
     there and never touches money.
  6. Delivers and learns: shipped -> realisation clock; payments realise shipments; buyers' payment days and each
     product's last rate are remembered for the next PI.
"""
from __future__ import annotations

import io
import json
import logging
import re
import threading
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, Float, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import rules as R

log = logging.getLogger("santosh.niryat")
_LOCK = threading.Lock()


class NiryatError(Exception):
    pass


class NiryatSettings(Base):
    __tablename__ = "niryat_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    iec: Mapped[str] = mapped_column(String(10), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    ad_bank: Mapped[str] = mapped_column(Text, default="")                   # AD bank name + AD code as she gives it (printed)
    lut_no: Mapped[str] = mapped_column(String(40), default="")
    lut_fy: Mapped[str] = mapped_column(String(7), default="")              # "2026-27"
    rcmc: Mapped[str] = mapped_column(String(120), default="")
    rcmc_valid_to: Mapped[str] = mapped_column(String(10), default="")
    prefix: Mapped[str] = mapped_column(String(6), default="EXP")
    counters: Mapped[str] = mapped_column(Text, default="{}")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")


class NiryatBuyer(Base):
    __tablename__ = "niryat_buyers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    country: Mapped[str] = mapped_column(String(2), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(24), default="")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    pay_terms: Mapped[str] = mapped_column(String(8), default="advance")
    credit_days: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NiryatShipment(Base):
    __tablename__ = "niryat_shipments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ns"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    buyer_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(20), default="", index=True)
    status: Mapped[str] = mapped_column(String(10), default="pi")          # pi | confirmed | shipped | realised | cancelled
    incoterm: Mapped[str] = mapped_column(String(3), default="FOB")
    place: Mapped[str] = mapped_column(String(80), default="")              # named port / place for the Incoterm
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    fx: Mapped[float] = mapped_column(Float, default=0.0)                   # rupees per unit of currency (her rate)
    lines: Mapped[str] = mapped_column(Text, default="[]")
    freight: Mapped[float] = mapped_column(Float, default=0.0)
    insurance: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)                # invoice value in currency
    fob: Mapped[float] = mapped_column(Float, default=0.0)
    gst_mode: Mapped[str] = mapped_column(String(4), default="lut")         # lut | igst
    pay_terms: Mapped[str] = mapped_column(String(8), default="advance")
    port_loading: Mapped[str] = mapped_column(String(60), default="")
    port_discharge: Mapped[str] = mapped_column(String(60), default="")
    dest: Mapped[str] = mapped_column(String(2), default="")
    mode: Mapped[str] = mapped_column(String(4), default="sea")
    pi_date: Mapped[str] = mapped_column(String(10), default="")
    inv_date: Mapped[str] = mapped_column(String(10), default="")
    sb_no: Mapped[str] = mapped_column(String(20), default="")
    sb_date: Mapped[str] = mapped_column(String(10), default="")
    bl_no: Mapped[str] = mapped_column(String(40), default="")
    ship_date: Mapped[str] = mapped_column(String(10), default="")
    realise_by: Mapped[str] = mapped_column(String(10), default="", index=True)
    received: Mapped[float] = mapped_column(Float, default=0.0)            # in currency
    received_inr: Mapped[float] = mapped_column(Float, default=0.0)
    rodtep: Mapped[str] = mapped_column(Text, default="{}")
    checks: Mapped[str] = mapped_column(Text, default="[]")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NiryatPayment(Base):
    __tablename__ = "niryat_payments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("np"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    shipment_id: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)              # in the shipment's currency
    inr: Mapped[float] = mapped_column(Float, default=0.0)                 # credited by the bank
    on: Mapped[str] = mapped_column(String(10), default="")
    ref: Mapped[str] = mapped_column(String(60), default="")               # IRM / FIRC / e-BRC number
    kind: Mapped[str] = mapped_column(String(8), default="after")          # advance | after


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _num(v) -> float:
    if v in (None, ""):
        return 0.0
    m = re.search(r"-?\d+(\.\d+)?", str(v).replace(",", ""))
    return float(m.group(0)) if m else 0.0


def _fc(v: float, cur: str) -> str:
    return f"{cur} {v:,.2f}"


def _rs(v) -> str:
    v = round(float(v or 0))
    s = str(abs(v))
    if len(s) > 3:
        s = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", s[:-3]) + "," + s[-3:]
    return ("-" if v < 0 else "") + "₹" + s


def today(tenant: str) -> date:
    from ..life import tz_of
    return datetime.now(tz_of(tenant)).date()


def _date(v, default: date | None = None) -> date | None:
    if isinstance(v, date):
        return v
    if v in (None, ""):
        return default
    from ..analyst.service import _date as d
    return d(v) or default


def fy_of(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("niryat publish failed")


def _st(s, tenant: str) -> NiryatSettings:
    r = s.get(NiryatSettings, tenant)
    if r is None:
        r = NiryatSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def settings(tenant: str) -> dict:
    on = today(tenant)
    with session() as s:
        r = _st(s, tenant)
        v = {k: getattr(r, k) for k in ("firm", "address", "iec", "gstin", "phone", "email", "ad_bank", "lut_no", "lut_fy", "rcmc",
                                        "rcmc_valid_to", "prefix", "morning_time")}
    v["lut_ok"] = bool(v["lut_no"]) and v["lut_fy"] == fy_of(on)
    rv = _date(v["rcmc_valid_to"])
    v["rcmc_ok"] = bool(rv and rv >= on)
    return v


def save_settings(tenant: str, **kw: Any) -> dict:
    from ..gstp.rules import valid_gstin
    with session() as s:
        r = _st(s, tenant)
        if kw.get("iec"):
            i = str(kw["iec"]).strip().upper()
            if not R.iec_ok(i):
                raise NiryatError("IEC 10 akshar / ank ka hota hai (aksar PAN jaisa).")
            r.iec = i
        if kw.get("gstin"):
            g = str(kw["gstin"]).strip().upper()
            if not valid_gstin(g):
                raise NiryatError(f"GSTIN galat lagta hai: {g}")
            r.gstin = g
        for k in ("firm", "address", "phone", "email", "ad_bank", "lut_no", "rcmc"):
            if kw.get(k) is not None:
                setattr(r, k, str(kw[k]).strip()[:500])
        if kw.get("lut_no"):
            r.lut_fy = str(kw.get("lut_fy") or fy_of(today(tenant)))[:7]
        if kw.get("rcmc_valid_to"):
            d = _date(kw["rcmc_valid_to"])
            if not d:
                raise NiryatError("RCMC ki tareekh samajh nahi aayi.")
            r.rcmc_valid_to = d.isoformat()
        if kw.get("prefix"):
            r.prefix = re.sub(r"[^A-Z0-9]", "", str(kw["prefix"]).upper())[:6] or r.prefix
        if kw.get("morning_time"):
            r.morning_time = str(kw["morning_time"]).zfill(5)[:5]
    return settings(tenant)


# ---------------------------------------------------------------- buyers
def _buyer(s, tenant: str, ref: str) -> NiryatBuyer:
    ref = str(ref or "").strip()
    if not ref:
        raise NiryatError("Kaun sa buyer?")
    b = s.get(NiryatBuyer, ref)
    if b and b.tenant_id == tenant:
        return b
    rows = s.scalars(select(NiryatBuyer).where(NiryatBuyer.tenant_id == tenant)).all()
    exact = [r for r in rows if r.name.lower() == ref.lower()]
    if len(exact) == 1:
        return exact[0]
    hits = [r for r in rows if ref.lower() in r.name.lower()]
    if len(hits) == 1:
        return hits[0]
    if hits:
        raise NiryatError("Kai buyer: " + ", ".join(h.name for h in hits[:6]))
    raise NiryatError(f"Buyer '{ref}' nahi mila. Pehle jodiye (naam, desh, currency).")


def _buyer_view(b: NiryatBuyer) -> dict:
    return {"id": b.id, "name": b.name, "country": b.country, "address": b.address, "email": b.email, "phone": b.phone,
            "currency": b.currency, "pay_terms": b.pay_terms, "pay_label": R.PAY_TERMS.get(b.pay_terms, b.pay_terms),
            "credit_days": b.credit_days, "fta": R.FTA.get(b.country, ""), "notes": b.notes}


def save_buyer(tenant: str, name: str = "", buyer: str = "", country: str = "", address: str = "", email: str = "", phone: str = "",
               currency: str = "", pay_terms: str = "", credit_days=None, notes: str = "") -> dict:
    with _LOCK, session() as s:
        b = _buyer(s, tenant, buyer) if buyer else None
        new = b is None
        if new:
            if not str(name).strip():
                raise NiryatError("Buyer ka naam chahiye.")
            b = NiryatBuyer(tenant_id=tenant)
            s.add(b)
        if name:
            b.name = re.sub(r"\s+", " ", str(name)).strip()[:160]
        if country:
            c = R.country(country)
            if not c:
                raise NiryatError(f"Desh samajh nahi aaya: {country} (2 akshar ka code bhi chalega, jaise AE, US, GB).")
            b.country = c
        elif new:
            raise NiryatError("Buyer kis desh ka hai?")
        if address:
            b.address = str(address)[:500]
        if email:
            b.email = str(email)[:120]
        if phone:
            b.phone = re.sub(r"[^\d+]", "", str(phone))[:24]
        if currency:
            c = str(currency).upper()[:3]
            if c not in R.CURRENCIES:
                raise NiryatError("Currency: " + ", ".join(R.CURRENCIES))
            b.currency = c
        if pay_terms:
            p = str(pay_terms).lower()
            p = "lc" if "lc" in p or "credit" in p and "letter" in p else "dp" if p in ("dp", "d/p", "cad") else \
                "da" if p in ("da", "d/a") else "open" if "open" in p else "part" if "part" in p else "advance" if "adv" in p or "tt" in p else p
            if p not in R.PAY_TERMS:
                raise NiryatError("Payment: advance | lc | dp | da | open | part")
            b.pay_terms = p
        if credit_days not in (None, ""):
            b.credit_days = max(0, min(int(credit_days), 360))
        if notes:
            b.notes = str(notes)[:1000]
        s.flush()
        v = _buyer_view(b)
    warn = R.SANCTION_CHECK.get(v["country"])
    say = f"{'Naya buyer' if new else 'Update'}: {v['name']} ({v['country']}, {v['currency']}, {v['pay_label']})."
    if v["fta"]:
        say += f" {v['fta']} laagu: certificate of origin se buyer ki duty kam."
    if warn:
        say += f" Dhyaan: {warn} par pabandiyan hain - bank se pehle baat kariye."
    return {"buyer": v, "say": say}


def buyers(tenant: str) -> list[dict]:
    with session() as s:
        return [_buyer_view(b) for b in s.scalars(select(NiryatBuyer).where(NiryatBuyer.tenant_id == tenant).order_by(NiryatBuyer.name)).all()]


# ---------------------------------------------------------------- shipments
def _next_number(st: NiryatSettings, d: date, kind: str) -> str:
    c = _j(st.counters, {})
    key = f"{kind}{fy_of(d)}"
    n = int(c.get(key, 0)) + 1
    c[key] = n
    st.counters = json.dumps(c)
    return f"{st.prefix}/{'PI' if kind == 'pi' else ''}{fy_of(d)[2:4]}{fy_of(d)[5:]}/{n:03d}".replace("//", "/")[:20]


def _view(sh: NiryatShipment, b: NiryatBuyer | None, on: date) -> dict:
    rb = _date(sh.realise_by)
    outstanding = round(sh.total - sh.received, 2)
    return {"id": sh.id, "number": sh.number, "status": sh.status, "buyer_id": sh.buyer_id, "buyer": b.name if b else "",
            "country": sh.dest, "incoterm": sh.incoterm, "incoterm_says": R.INCOTERMS.get(sh.incoterm, ""), "place": sh.place,
            "currency": sh.currency, "fx": sh.fx, "lines": _j(sh.lines, []), "freight": sh.freight, "insurance": sh.insurance,
            "total": sh.total, "fob": sh.fob, "fob_inr": round(sh.fob * sh.fx, 2), "gst_mode": sh.gst_mode, "pay_terms": sh.pay_terms,
            "port_loading": sh.port_loading, "port_discharge": sh.port_discharge, "mode": sh.mode, "pi_date": sh.pi_date,
            "inv_date": sh.inv_date, "sb_no": sh.sb_no, "sb_date": sh.sb_date, "bl_no": sh.bl_no, "ship_date": sh.ship_date,
            "realise_by": sh.realise_by, "days_left": (rb - on).days if rb else None, "received": sh.received,
            "received_inr": sh.received_inr, "outstanding": outstanding, "rodtep": _j(sh.rodtep, {}), "checks": _j(sh.checks, []),
            "docs": R.doc_list(sh.incoterm, sh.pay_terms, bool(R.FTA.get(sh.dest)), sh.mode), "log": _j(sh.log, [])[-10:]}


def _log(sh: NiryatShipment, what: str) -> None:
    lg = _j(sh.log, [])
    lg.append({"at": now().isoformat(timespec="seconds"), "what": what[:300]})
    sh.log = json.dumps(lg[-60:], ensure_ascii=False)


def _lines(raw: list | None, text: str = "") -> list[dict]:
    if not raw and text:
        raw = []
        for part in re.split(r"[\n;]+", text):
            m = re.match(r"\s*(.+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z]*)\s*@\s*([\d.,]+)(?:.*?hs\s*:?\s*(\d{4,8}))?", part, re.I)
            if m:
                raw.append({"item": m.group(1), "qty": m.group(2), "unit": m.group(3) or "", "rate": m.group(4), "hs": m.group(5) or ""})
    out = []
    for x in raw or []:
        if not isinstance(x, dict):
            continue
        item = str(x.get("item") or x.get("name") or "").strip()
        qty, rate = _num(x.get("qty")), _num(x.get("rate"))
        if not item or qty <= 0 or rate <= 0:
            raise NiryatError(f"'{item or x}': maatra aur rate (videshi currency mein) dono chahiye.")
        hs = re.sub(r"\D", "", str(x.get("hs") or x.get("hsn") or ""))
        out.append({"item": item[:120], "hs": hs, "qty": qty, "unit": str(x.get("unit") or "KGS").upper()[:6], "rate": round(rate, 4),
                    "amount": round(qty * rate, 2), "net_kg": _num(x.get("net_kg")), "gross_kg": _num(x.get("gross_kg")),
                    "packages": int(_num(x.get("packages"))), "rodtep_pct": _num(x.get("rodtep_pct")), "rodtep_cap": _num(x.get("rodtep_cap"))})
    if not out:
        raise NiryatError("Maal ki line chahiye: 'Haldi powder 2000 kg @ 2.10 HS 09103030'.")
    return out


def _last_rates(s, tenant: str, buyer_id: str) -> dict[str, float]:
    last: dict[str, float] = {}
    for sh in s.scalars(select(NiryatShipment).where(NiryatShipment.tenant_id == tenant, NiryatShipment.buyer_id == buyer_id,
                                                     NiryatShipment.status != "cancelled").order_by(NiryatShipment.created_at)).all():
        for x in _j(sh.lines, []):
            last[x["item"].lower()] = x["rate"]
    return last


def proforma(tenant: str, buyer: str, lines: list | None = None, text: str = "", incoterm: str = "FOB", place: str = "", fx=None,
             freight=None, insurance=None, gst_mode: str = "lut", port_loading: str = "", port_discharge: str = "", mode: str = "sea",
             currency: str = "", conv: str = "") -> dict:
    on = today(tenant)
    term = (incoterm or "FOB").upper()
    if term not in R.INCOTERMS:
        raise NiryatError("Incoterm: " + ", ".join(R.INCOTERMS))
    ls = _lines(lines, text)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        b = _buyer(s, tenant, buyer)
        cur = (currency or b.currency or "USD").upper()
        fr, ins = _num(freight), _num(insurance)
        if term in ("CFR", "CPT", "CIF", "CIP", "DAP", "DPU", "DDP") and not fr:
            raise NiryatError(f"{term} mein freight aap dengi: freight ({cur}) bataiye.")
        if term in ("CIF", "CIP") and not ins:
            ins = round(sum(x["amount"] for x in ls) * 0.0011, 2)               # 110% cover at ~0.1%: she can change it
        goods = round(sum(x["amount"] for x in ls), 2)
        total = round(goods + (fr if term not in ("EXW", "FCA", "FAS", "FOB") else 0) + (ins if term in ("CIF", "CIP", "DAP", "DPU", "DDP") else 0), 2)
        fob = R.fob_value(total, term, fr, ins if term in ("CIF", "CIP", "DAP", "DPU", "DDP") else 0)
        rate_fx = _num(fx)
        hs = [x["hs"] for x in ls]
        ck = R.checks(b.country, hs, term, b.pay_terms, cur)
        if gst_mode == "lut" and not (st.lut_no and st.lut_fy == fy_of(on)):
            ck.append({"level": "warn", "text": f"Is saal ({fy_of(on)}) ka LUT nahi likha: GST portal par RFD-11 bhariye, warna IGST bharkar refund lena padega."})
        last = _last_rates(s, tenant, b.id)
        for x in ls:
            lr = last.get(x["item"].lower())
            if lr and abs(lr - x["rate"]) / lr > 0.1:
                ck.append({"level": "info", "text": f"{x['item']}: pichhli baar rate {cur} {lr} tha, ab {x['rate']}."})
        sh = NiryatShipment(tenant_id=tenant, buyer_id=b.id, number=_next_number(st, on, "pi"), incoterm=term, place=str(place)[:80],
                            currency=cur, fx=rate_fx, lines=json.dumps(ls, ensure_ascii=False), freight=fr, insurance=ins, total=total,
                            fob=fob, gst_mode="igst" if gst_mode == "igst" else "lut", pay_terms=b.pay_terms, dest=b.country,
                            port_loading=str(port_loading)[:60], port_discharge=str(port_discharge)[:60], mode="air" if mode == "air" else "sea",
                            pi_date=on.isoformat(), checks=json.dumps(ck, ensure_ascii=False))
        _log(sh, f"PI {total} {cur}")
        s.add(sh)
        s.flush()
        v = _view(sh, b, on)
    f = pi_file(tenant, v["id"], conv)
    stop = [c for c in ck if c["level"] == "stop"]
    say = (f"PI {v['number']} {v['buyer']}: {len(ls)} item, {term} {place or ''} {_fc(total, cur)} (FOB {_fc(fob, cur)}"
           + (f" = {_rs(fob * rate_fx)}" if rate_fx else "") + ").")
    if ck:
        say += " " + " ".join(c["text"] for c in ck[:4])
    say += " Buyer ko bhejne se pehle aapki haan."
    _publish(tenant, "niryat_pi", {"shipment_id": v["id"], "number": v["number"], "buyer": v["buyer"], "total": total, "currency": cur,
                                   "stop": bool(stop)}, conv)
    return {"shipment": v, "file": f["file"], "say": say}


def _doc_pdf(tenant: str, sid: str, kind: str) -> bytes:
    """PI / commercial invoice / packing list."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    st = settings(tenant)
    with session() as s:
        sh = s.get(NiryatShipment, sid)
        b = s.get(NiryatBuyer, sh.buyer_id)
        v = _view(sh, b, today(tenant))
        bv = _buyer_view(b)
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 40

    def t(x, text, size=9, bold=False, right=False):
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        s_ = str(text).replace("₹", "Rs ").encode("latin-1", "replace").decode("latin-1")
        (pdf.drawRightString if right else pdf.drawString)(x, y, s_[:115])

    title = {"pi": "PROFORMA INVOICE", "ci": "COMMERCIAL INVOICE", "pl": "PACKING LIST"}[kind]
    t(w / 2 - 60, title, 13, True)
    y -= 20
    t(30, st["firm"] or "-", 11, True)
    no = v["number"]
    t(w - 30, f"No: {no}   Date: {v['inv_date'] if kind != 'pi' else v['pi_date']}", 9, True, True)
    y -= 12
    t(30, (st["address"] or "")[:100])
    y -= 12
    t(30, f"IEC: {st['iec'] or '-'}   GSTIN: {st['gstin'] or '-'}" + (f"   RCMC: {st['rcmc']}" if st["rcmc"] else ""))
    y -= 16
    t(30, "Buyer / Consignee:", 9, True)
    y -= 12
    t(30, bv["name"], 10, True)
    y -= 12
    if bv["address"]:
        t(30, bv["address"][:100])
        y -= 12
    t(30, f"Country of origin: INDIA   Final destination: {bv['country']}   Terms: {v['incoterm']} {v['place']}   Payment: {R.PAY_TERMS.get(v['pay_terms'], '')}")
    y -= 12
    t(30, f"Port of loading: {v['port_loading'] or '-'}   Port of discharge: {v['port_discharge'] or '-'}   By: {v['mode'].upper()}")
    y -= 18
    if kind == "pl":
        cols = [(30, "#"), (48, "Description"), (260, "HS code"), (330, "Qty"), (400, "Pkgs"), (450, "Net kg"), (565, "Gross kg")]
    else:
        cols = [(30, "#"), (48, "Description"), (260, "HS code"), (330, "Qty"), (420, f"Rate {v['currency']}"), (565, f"Amount {v['currency']}")]
    for x, name in cols:
        t(x, name, 8.5, True, x == 565)
    y -= 4
    pdf.line(30, y, w - 30, y)
    y -= 12
    for i, ln in enumerate(v["lines"], 1):
        if y < 130:
            pdf.showPage()
            y = h - 40
        t(30, i, 8.5)
        t(48, ln["item"][:40], 8.5)
        t(260, ln["hs"] or "-", 8.5)
        t(330, f"{ln['qty']:g} {ln['unit']}", 8.5)
        if kind == "pl":
            t(400, ln.get("packages") or "-", 8.5)
            t(450, f"{ln.get('net_kg') or 0:g}", 8.5)
            t(565, f"{ln.get('gross_kg') or 0:g}", 8.5, False, True)
        else:
            t(420, f"{ln['rate']:,.4g}", 8.5)
            t(565, f"{ln['amount']:,.2f}", 8.5, False, True)
        y -= 12
    pdf.line(30, y + 4, w - 30, y + 4)
    y -= 10
    if kind == "pl":
        t(30, f"Total packages: {sum(int(x.get('packages') or 0) for x in v['lines'])}   Net: {sum(x.get('net_kg') or 0 for x in v['lines']):g} kg   "
              f"Gross: {sum(x.get('gross_kg') or 0 for x in v['lines']):g} kg", 9, True)
        y -= 14
    else:
        rows = [("Goods", round(sum(x["amount"] for x in v["lines"]), 2))]
        if v["incoterm"] not in ("EXW", "FCA", "FAS", "FOB"):
            rows.append(("Freight", v["freight"]))
        if v["incoterm"] in ("CIF", "CIP", "DAP", "DPU", "DDP") and v["insurance"]:
            rows.append(("Insurance", v["insurance"]))
        rows.append((f"TOTAL {v['incoterm']} {v['currency']}", v["total"]))
        for k, a in rows:
            t(420, k, 9, k.startswith("TOTAL"))
            t(565, f"{a:,.2f}", 9, k.startswith("TOTAL"), True)
            y -= 13
        if v["incoterm"] != "FOB":
            t(30, f"FOB value: {v['currency']} {v['fob']:,.2f}", 8.5)
            y -= 12
        if kind == "ci":
            lut = ("SUPPLY MEANT FOR EXPORT UNDER LUT NO. " + (st["lut_no"] or "_____") + " WITHOUT PAYMENT OF IGST") if v["gst_mode"] == "lut" \
                else "SUPPLY MEANT FOR EXPORT ON PAYMENT OF IGST"
            t(30, lut, 8.5, True)
            y -= 12
        if st["ad_bank"]:
            t(30, "Bank: " + st["ad_bank"][:105], 8.5)
            y -= 12
        if kind == "pi":
            t(30, "This proforma is valid for 15 days. Prices subject to confirmation of order.", 8)
            y -= 12
    y -= 6
    t(30, "We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.", 7.5)
    y -= 34
    t(w - 30, f"For {st['firm'] or ''}", 9, True, True)
    y -= 28
    t(w - 30, "Authorised signatory", 8.5, False, True)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def _store(tenant: str, sid: str, kind: str, conv: str) -> dict:
    from .. import chatfiles
    v = get_shipment(tenant, sid)
    name = {"pi": "PI", "ci": "Invoice", "pl": "PackingList"}[kind]
    f = chatfiles.store(tenant, f"{name}-{v['number'].replace('/', '-')}.pdf", _doc_pdf(tenant, sid, kind), "application/pdf")
    _publish(tenant, "pc_file", {**f, "source": "niryat", "title": f"{name} {v['number']}"}, conv)
    return {"file": f}


def pi_file(tenant: str, sid: str, conv: str = "") -> dict:
    return _store(tenant, sid, "pi", conv)


def get_shipment(tenant: str, ref: str) -> dict:
    with session() as s:
        sh = s.get(NiryatShipment, ref)
        if not sh or sh.tenant_id != tenant:
            sh = s.scalars(select(NiryatShipment).where(NiryatShipment.tenant_id == tenant, NiryatShipment.number == ref)).first()
        if not sh:
            raise NiryatError("Shipment / PI nahi mila.")
        return _view(sh, s.get(NiryatBuyer, sh.buyer_id), today(tenant))


def pi_draft(tenant: str, sid: str) -> dict:
    """Her Haan: the message to the buyer with the PI (she sends it from her own email / WhatsApp)."""
    v = get_shipment(tenant, sid)
    firm = settings(tenant)["firm"]
    with session() as s:
        b = s.get(NiryatBuyer, v["buyer_id"])
        to = b.email or b.phone
    text = (f"Dear {v['buyer']},\nPlease find attached our Proforma Invoice {v['number']} for {v['currency']} {v['total']:,.2f} "
            f"({v['incoterm']} {v['place']}). Payment: {R.PAY_TERMS.get(v['pay_terms'], v['pay_terms'])}. Kindly confirm the order.\n"
            f"Regards,\n{firm}")
    return {"to": to, "text": text, "say": "Buyer ke liye message taiyaar; PI saath lagaakar aap bhejiye."}


def confirm(tenant: str, sid: str, inv_date: str = "", fx=None, conv: str = "") -> dict:
    """Her Haan: the buyer confirmed -> commercial invoice number + invoice and packing list PDFs."""
    on = today(tenant)
    with _LOCK, session() as s:
        sh = s.get(NiryatShipment, sid)
        if not sh or sh.tenant_id != tenant:
            raise NiryatError("PI nahi mila.")
        if sh.status != "pi":
            raise NiryatError(f"Yeh pehle se {sh.status} hai.")
        if any(c["level"] == "stop" for c in _j(sh.checks, [])):
            raise NiryatError("Is shipment par rok wali jaanch hai (sanctions). Bank / CA se clear karke hi aage.")
        st = _st(s, tenant)
        d = _date(inv_date, on)
        sh.number = _next_number(st, d, "ci")
        sh.inv_date = d.isoformat()
        if fx not in (None, ""):
            sh.fx = _num(fx)
        sh.status = "confirmed"
        _log(sh, f"Order pakka, invoice {sh.number}")
    a = _store(tenant, sid, "ci", conv)
    b = _store(tenant, sid, "pl", conv)
    v = get_shipment(tenant, sid)
    return {"shipment": v, "files": [a["file"], b["file"]], "docs": v["docs"],
            "say": f"Invoice {v['number']} aur packing list taiyaar. CHA ko dijiye shipping bill ke liye. Kaagaz: " + ", ".join(v["docs"]) + "."}


def shipped(tenant: str, sid: str, sb_no: str, sb_date: str = "", bl_no: str = "", ship_date: str = "", fx=None) -> dict:
    """Shipping bill + B/L: the RBI realisation clock starts; RoDTEP estimate; IGST refund note."""
    on = today(tenant)
    if not str(sb_no).strip():
        raise NiryatError("Shipping bill number bataiye.")
    with _LOCK, session() as s:
        sh = s.get(NiryatShipment, sid)
        if not sh or sh.tenant_id != tenant:
            raise NiryatError("Shipment nahi mila.")
        if sh.status not in ("confirmed", "pi"):
            raise NiryatError(f"Yeh {sh.status} hai.")
        sh.sb_no = re.sub(r"\D", "", str(sb_no))[:20]
        sh.sb_date = (_date(sb_date, on)).isoformat()
        sh.bl_no = str(bl_no)[:40]
        sd = _date(ship_date, _date(sh.sb_date, on))
        sh.ship_date = sd.isoformat()
        if fx not in (None, ""):
            sh.fx = _num(fx)                                   # customs (CBIC) rate on the shipping bill
        sh.realise_by = R.realise_by(sd, sh.currency).isoformat()
        ls = _j(sh.lines, [])
        goods = sum(x["amount"] for x in ls) or 1
        rd_total, notes = 0.0, ""
        for x in ls:
            if x.get("rodtep_pct"):
                share = sh.fob * x["amount"] / goods
                r = R.rodtep(share * sh.fx, x["rodtep_pct"], x.get("rodtep_cap") or 0.0, x["qty"], sd)
                rd_total += r["amount"]
                notes = r["note"]
        sh.rodtep = json.dumps({"estimate": round(rd_total, 2), "note": notes})
        sh.status = "shipped"
        _log(sh, f"Shipped: SB {sh.sb_no}, realise by {sh.realise_by}")
        mode = sh.gst_mode
    v = get_shipment(tenant, sid)
    say = f"{v['number']} nikal gaya (SB {v['sb_no']}). Paisa {v['realise_by']} tak aana zaroori (RBI {12 if v['currency'] == 'INR' else 9} mahine)."
    if rd_total:
        say += f" RoDTEP ka andaza {_rs(rd_total)} (shipping bill mein declare hua ho to e-scrip ICEGATE par)."
    say += (" IGST bhara hai: GSTR-1 (table 6A) aur 3B time par bhariye, refund shipping bill se apne aap." if mode == "igst"
            else " LUT par gaya: GSTR-1 mein zero-rated (without payment) dikhaiye.")
    return {"shipment": v, "say": say}


def receive(tenant: str, sid: str, amount, inr=None, on: str = "", ref: str = "", kind: str = "") -> dict:
    """Foreign money reached HER AD bank (Hoola only notes it). Advance before shipment, or realisation after."""
    amt = _num(amount)
    if amt <= 0:
        raise NiryatError("Rakam (videshi currency mein) bataiye.")
    d = _date(on, today(tenant))
    with _LOCK, session() as s:
        sh = s.get(NiryatShipment, sid)
        if not sh or sh.tenant_id != tenant:
            sh = s.scalars(select(NiryatShipment).where(NiryatShipment.tenant_id == tenant, NiryatShipment.number == sid)).first()
        if not sh:
            raise NiryatError("Shipment nahi mila.")
        k = kind or ("advance" if sh.status in ("pi", "confirmed") else "after")
        s.add(NiryatPayment(tenant_id=tenant, shipment_id=sh.id, amount=round(amt, 2), inr=round(_num(inr), 2), on=d.isoformat(),
                            ref=str(ref)[:60], kind=k))
        sh.received = round(sh.received + amt, 2)
        sh.received_inr = round(sh.received_inr + _num(inr), 2)
        if sh.status == "shipped" and sh.received >= sh.total - 0.01:
            sh.status = "realised"
        _log(sh, f"Mila {sh.currency} {amt} ({k})")
        sid2 = sh.id
    v = get_shipment(tenant, sid2)
    say = f"{v['buyer']} se {_fc(amt, v['currency'])} mila" + (f" ({_rs(_num(inr))})" if inr else "") + f". Baaki {_fc(v['outstanding'], v['currency'])}."
    if v["status"] == "realised":
        say += " Poora realise: bank se e-BRC / IRM number le kar note kariye."
        if v["received_inr"] and v["fx"]:
            gain = v["received_inr"] - v["total"] * v["fx"]
            say += f" Invoice rate se {'faayda' if gain >= 0 else 'nuksaan'} {_rs(abs(gain))}."
    if k == "advance":
        say += " Advance: shipment 1 saal mein bhejna zaroori (RBI)."
    return {"shipment": v, "say": say}


def cancel(tenant: str, sid: str, reason: str = "") -> dict:
    with session() as s:
        sh = s.get(NiryatShipment, sid)
        if not sh or sh.tenant_id != tenant:
            raise NiryatError("Shipment nahi mila.")
        if sh.status in ("shipped", "realised"):
            raise NiryatError("Maal nikal chuka hai: cancel nahi, bank / CHA se baat kariye.")
        sh.status = "cancelled"
        _log(sh, f"Cancel: {reason}")
    return {"say": "Cancel."}


def shipments(tenant: str, status: str = "", buyer: str = "") -> list[dict]:
    on = today(tenant)
    with session() as s:
        q = select(NiryatShipment).where(NiryatShipment.tenant_id == tenant)
        if status:
            q = q.where(NiryatShipment.status == status)
        if buyer:
            q = q.where(NiryatShipment.buyer_id == _buyer(s, tenant, buyer).id)
        bs = {b.id: b for b in s.scalars(select(NiryatBuyer).where(NiryatBuyer.tenant_id == tenant)).all()}
        return [_view(x, bs.get(x.buyer_id), on) for x in s.scalars(q.order_by(NiryatShipment.created_at.desc())).all()][:200]


def realisation(tenant: str) -> dict:
    """Shipped, not fully paid: days left to the RBI date; reminder drafts she sends."""
    rows = [x for x in shipments(tenant, "shipped") if x["outstanding"] > 0.01]
    rows.sort(key=lambda x: x["days_left"] if x["days_left"] is not None else 9999)
    overdue = [x for x in rows if (x["days_left"] or 0) < 0]
    soon = [x for x in rows if 0 <= (x["days_left"] or 0) <= 30]
    firm = settings(tenant)["firm"]
    drafts = []
    with session() as s:
        contacts = {b.id: (b.email or b.phone) for b in s.scalars(select(NiryatBuyer).where(NiryatBuyer.tenant_id == tenant)).all()}
    for x in rows:
        sd = _date(x["ship_date"])
        with session() as s:
            b = s.get(NiryatBuyer, x["buyer_id"])
            credit = b.credit_days if b else 0
        if sd and (today(tenant) - sd).days >= credit:
            drafts.append({"buyer": x["buyer"], "to": contacts.get(x["buyer_id"], ""),
                           "text": f"Dear {x['buyer']},\nThis is a gentle reminder that {x['currency']} {x['outstanding']:,.2f} against our invoice "
                                   f"{x['number']} (B/L {x['bl_no'] or '-'}) is due. Kindly arrange the remittance to our bank.\nRegards,\n{firm}"})
    say = f"{len(rows)} shipment ka paisa baaki." + (f" {len(overdue)} RBI ki tareekh paar: AD bank se extension / write-off ki baat turant." if overdue else "") \
        + (f" {len(soon)} ki tareekh 30 din mein." if soon else "")
    return {"shipments": rows, "overdue": overdue, "soon": soon, "drafts": drafts, "say": say}


def register_file(tenant: str, conv: str = "") -> dict:
    import openpyxl
    from .. import chatfiles
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exports"
    ws.append(["Invoice", "Buyer", "Country", "Incoterm", "Currency", "Total", "FOB", "FX", "FOB INR", "SB no", "SB date", "B/L", "Ship date",
               "Realise by", "Received", "Outstanding", "RoDTEP est", "Status"])
    for x in shipments(tenant):
        if x["status"] == "cancelled":
            continue
        ws.append([x["number"], x["buyer"], x["country"], x["incoterm"], x["currency"], x["total"], x["fob"], x["fx"], x["fob_inr"], x["sb_no"],
                   x["sb_date"], x["bl_no"], x["ship_date"], x["realise_by"], x["received"], x["outstanding"], x["rodtep"].get("estimate", ""),
                   x["status"]])
    bio = io.BytesIO()
    wb.save(bio)
    f = chatfiles.store(tenant, "Export_register.xlsx", bio.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "niryat", "title": "Export register"}, conv)
    return {"file": f, "say": "Export register Excel mein (invoice, shipping bill, realisation, RoDTEP)."}


def day(tenant: str) -> dict:
    on = today(tenant)
    st = settings(tenant)
    r = realisation(tenant)
    pis = shipments(tenant, "pi")
    conf = shipments(tenant, "confirmed")
    parts = []
    if not st["lut_ok"]:
        parts.append(f"Is saal ({fy_of(on)}) ka LUT nahi likha")
    elif on.month == 3:
        parts.append("31 March ke baad naya LUT (RFD-11) bhariye")
    rv = _date(st["rcmc_valid_to"])
    if rv and (rv - on).days <= 30:
        parts.append(f"RCMC {rv.isoformat()} ko khatam")
    if r["overdue"]:
        parts.append(f"{len(r['overdue'])} shipment ka paisa RBI tareekh paar")
    if r["soon"]:
        parts.append(f"{len(r['soon'])} ka paisa 30 din mein")
    if pis:
        parts.append(f"{len(pis)} PI ka jawab baaki")
    if conf:
        parts.append(f"{len(conf)} invoice taiyaar, shipping bill baaki")
    if on > R.RODTEP_UNTIL - timedelta(days=30) and on <= R.RODTEP_UNTIL:
        parts.append("RoDTEP abhi 31 Dec 2026 tak hi notified")
    return {"parts": parts, "realisation": r, "say": ("; ".join(parts) + ".") if parts else "Niryat: sab theek."}


def due_mornings() -> list[str]:
    from ..life import tz_of
    out = []
    with session() as s:
        for r in s.scalars(select(NiryatSettings)).all():
            if not s.scalars(select(NiryatShipment.id).where(NiryatShipment.tenant_id == r.tenant_id).limit(1)).first():
                continue
            local = datetime.now(tz_of(r.tenant_id))
            try:
                hh, mm = [int(x) for x in (r.morning_time or "09:00").split(":")]
            except ValueError:
                hh, mm = 9, 0
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            d = local.date().isoformat()
            if r.last_morning != d and 0 <= late <= 180:
                r.last_morning = d
                out.append(r.tenant_id)
    return out


def send_morning(tenant: str) -> dict:
    from ..events import notify
    from ..net.service import home_conv
    d = day(tenant)
    if not d["parts"]:
        return {"text": ""}
    text = "Niryat: " + d["say"]
    conv = home_conv(tenant)
    try:
        notify(conv, text)
    except Exception:
        pass
    _publish(tenant, "niryat_day", {"text": text}, conv)
    return {"text": text}
