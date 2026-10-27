"""Graphic Sahayak: Hoola as a freelance graphic designer's / small studio's client desk, end to end.

  1. Clients with THEIR brand kits (logo -> colours read from the picture, font, tagline, what goes on their designs).
  2. Jobs (G-0001): brief in the client's words (data), what may go on the design, deliverables (screen sizes and / or a print
     format), due date, HER price lines, revision rounds included + HER price for an extra round, advance %.
  3. Proofs: made by the brand engine (`app.brand.render` with the CLIENT's kit - the brand Sahayak stays the poster engine;
     nothing of it is copied or changed) or her own artwork file from her design tool; print files are preflighted against the
     print vendor's spec (trim + bleed, dpi, CMYK, fonts embedded, PDF/X). Every proof carries a PROOF mark.
  4. Revision rounds counted in code: client feedback (their words = data) opens a round; once the rounds in the quote are used,
     the next version is refused until HER tap on an extra-round card (her price) or her own "is baar free".
  5. Font / picture licence register per job (Google Fonts OFL ok to share, Adobe Fonts / bought fonts never handed over as files,
     "personal use" fonts blocked), trademark search help for logos (IP India public search; Hoola never opens it itself).
  6. Handover pack: finals, colour codes (HEX + plain CMYK as a starting point), font / asset notes, a written copyright
     assignment draft (Copyright Act s.19), all as one ZIP in her files.

Waits for HER tap (only the app API passes by_tap=True; tools only make the card):
  * the quotation, every proof, any message, the handover pack and the print order going OUT (client / vendor),
  * an extra paid revision round, every invoice / payment request (UPI link to HER UPI ID),
  * any discount (her phone's fingerprint once a phone key is active: approvekey kind "graphic").
Hoola never sends, never takes or pays money and never invents a price, date or fact (blanks instead)."""
from __future__ import annotations

import io
import json
import logging
import os
import re
import secrets
import threading
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote as urlq

from sqlalchemy import select

from ..db import now, session
from . import rules as R
from .models import GraphicAlert, GraphicCard, GraphicClient, GraphicJob, GraphicSettings, GraphicVendor, GraphicVersion

log = logging.getLogger("santosh.graphic")
_LOCK = threading.RLock()
MONEY_CARDS = ("discount",)
CARD_KINDS = ("quote", "proof", "extra", "handover", "vendor", "invoice", "discount", "message")
CARD_TITLE = {"quote": "Quotation client ko", "proof": "Proof client ko", "extra": "Extra revision round",
              "handover": "Final files client ko", "vendor": "Print order printer ko", "invoice": "Invoice / paise maangna",
              "discount": "Discount", "message": "Client ko message"}
STATUS = {"brief": "Brief", "quoted": "Quote gaya", "accepted": "Kaam shuru", "proof": "Proof", "approved": "Client ki haan",
          "delivered": "Files de di", "done": "Poora", "cancelled": "Radd"}


class GraphicError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str | None, default):
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


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return clock().astimezone(_tz(tenant)).date()


def _date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
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
    return None


def _num(v) -> float | None:
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).lower().replace(",", "").strip()
    mult = 1.0
    if re.search(r"\d\s*(k|hazaar|hazar)\b", t):
        mult = 1000.0
    elif re.search(r"\d\s*(lakh|lac)\b", t):
        mult = 100000.0
    s = re.sub(r"[^\d.\-]", "", t)
    try:
        return float(s) * mult if s not in ("", "-", ".") else None
    except ValueError:
        return None


def _int(v) -> int | None:
    n = _num(v)
    return int(n) if n is not None and n >= 0 else None


def _rs(v: float | None) -> str:
    if v is None:
        return "[daam?]"
    try:
        from ..india.money import inr
        return inr(v)
    except Exception:
        return f"₹{v:,.0f}"


def _pdf_rs(v: float | None) -> str:
    return "[ ? ]" if v is None else "Rs. " + f"{v:,.2f}"


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("graphic publish failed")


def is_owner(actor: str) -> bool:
    a = actor or "owner"
    return a == "owner" or a.startswith("approved:")


def actor_name(tenant: str, actor: str) -> str:
    if is_owner(actor):
        return "Owner"
    try:
        from ..employee.service import actor_label
        return actor_label(tenant, actor)
    except Exception:
        return str(actor)[:40]


def _owner_only(actor: str) -> None:
    if not is_owner(actor):
        raise GraphicError("Yeh sirf owner kar sakti hain.")


def _root() -> Path:
    return Path(os.environ.get("GRAPHIC_DIR", "data/graphic"))


def _safe(x: str) -> str:
    return re.sub(r"[^\w-]", "_", x or "")[:64] or "x"


def _dir(tenant: str, sub: str = "") -> Path:
    p = _root() / _safe(tenant)
    if sub:
        p = p / _safe(sub)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _st(s, tenant: str) -> GraphicSettings:
    r = s.get(GraphicSettings, tenant)
    if r is None:
        r = GraphicSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _wa(phone: str, text: str) -> str:
    d = R.phone(phone)
    return f"https://wa.me/91{d}?text={urlq(text)}" if d else ""


def _sms(phone: str, text: str) -> str:
    d = R.phone(phone)
    return f"sms:+91{d}?body={urlq(text)}" if d else ""


def _mail(email: str, subject: str, text: str) -> str:
    e = (email or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e):
        return ""
    return f"mailto:{e}?subject={urlq(subject)}&body={urlq(text)}"


def _draft(phone: str, text: str, email: str = "", subject: str = "", **extra) -> dict:
    return {"text": text, "wa": _wa(phone, text), "sms": _sms(phone, text), "mail": _mail(email, subject, text), **extra}


def _upi_of(tenant: str) -> tuple[str, str]:
    with session() as s:
        st = _st(s, tenant)
        upi, nm = st.upi_id, st.studio or st.designer
    if not upi:
        try:
            from ..employee import service as emp
            p = emp.profile(tenant) or {}
            upi = p.get("upi_id") or ""
            nm = nm or p.get("upi_name") or p.get("business_name") or ""
        except Exception:
            upi = ""
    return upi, nm


def _upi(tenant: str, amount: float, note: str) -> str:
    upi, nm = _upi_of(tenant)
    if not upi or amount <= 0:
        return ""
    return f"upi://pay?pa={urlq(upi)}&pn={urlq(nm)}&am={amount:.2f}&cu=INR&tn={urlq(note[:40])}"


def _store(tenant: str, name: str, data: bytes, mime: str, conv: str = "", title: str = "") -> dict:
    from .. import chatfiles
    f = chatfiles.store(tenant, name, data, mime)
    _publish(tenant, "pc_file", {**f, "source": "graphic", "title": title or name}, conv)
    return f


def _load_file(tenant: str, file_id: str) -> tuple[str, bytes]:
    from ..mailbox import service as ms
    try:
        name, _m, data = ms.load_files(tenant, [{"type": "file", "file_id": file_id}])[0]
        return name, data
    except Exception as e:
        raise GraphicError(f"File {file_id} nahi mili: {e}")


def _fy(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def _log(j: GraphicJob, text: str, by: str = "") -> None:
    lg = _j(j.log, [])
    lg.append({"at": now().isoformat(), "what": R.clean(text, 300), "by": by})
    j.log = _dump(lg[-100:])
    j.updated_at = now()


def _ai_words(system: str, prompt: str) -> dict[str, Any]:
    """Claude via the content writer's JSON helper; {} when no model (tests monkeypatch this)."""
    try:
        from ..kalam.service import _ai_json
        return _ai_json(system, prompt, 900) or {}
    except Exception as e:
        log.info("graphic words model failed: %s", e)
        return {}


def _secret_text(text: str) -> bool:
    if re.search(r"\b(otp|pin|cvv|password|upi pin)\b", text or "", re.I):
        return True
    try:
        from ..net.policy import secret_found
        return bool(secret_found(text or ""))
    except Exception:
        return False


# ---------------------------------------------------------------- settings
_SET_KEYS = ("studio", "designer", "gstin", "state", "address", "phone", "email", "upi_id", "gst_rate", "sac", "lut", "udyam",
             "rounds", "extra_round", "advance_pct", "pay_days", "validity_days", "handover_after_pay", "assign_copyright",
             "terms", "rules", "morning_time")


def _settings_view(st: GraphicSettings) -> dict:
    return {"studio": st.studio, "designer": st.designer, "gstin": st.gstin, "state": st.state, "address": st.address,
            "phone": st.phone, "email": st.email, "upi_id": st.upi_id, "gst_rate": st.gst_rate, "sac": st.sac, "lut": st.lut,
            "udyam": st.udyam, "rounds": st.rounds, "extra_round": st.extra_round, "advance_pct": st.advance_pct,
            "pay_days": st.pay_days, "validity_days": st.validity_days, "handover_after_pay": st.handover_after_pay,
            "assign_copyright": st.assign_copyright, "terms": st.terms, "rules": _j(st.rules, []),
            "morning_time": st.morning_time, "gst_on": bool(st.gstin),
            "formats": {k: v["label"] for k, v in R.FORMATS.items()}, "kinds": {k: v["label"] for k, v in R.KINDS.items()},
            "font_licences": {k: v[0] for k, v in R.FONT_LICENCES.items()}, "asset_licences": dict(R.ASSET_LICENCES)}


def settings(tenant: str) -> dict:
    with session() as s:
        return _settings_view(_st(s, tenant))


def save_settings(tenant: str, actor: str = "owner", **kw: Any) -> dict:
    _owner_only(actor)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        for k in ("studio", "designer", "address", "terms", "sac", "lut", "udyam"):
            if kw.get(k) is not None:
                setattr(st, k, R.clean(kw[k], 600 if k in ("address", "terms") else 160))
        if kw.get("gstin") is not None:
            g = str(kw["gstin"]).strip().upper()
            if g and not R.gstin_ok(g):
                raise GraphicError(f"GSTIN {g} sahi nahi lagta (check digit galat).")
            st.gstin = g
        if kw.get("state") is not None:
            st.state = R.clean(kw["state"], 20)
        if kw.get("phone") is not None:
            p = str(kw["phone"]).strip()
            if p and not R.phone(p):
                raise GraphicError("Phone 10 ankon ka mobile number likhiye.")
            st.phone = R.phone(p)
        if kw.get("email") is not None:
            st.email = R.clean(kw["email"], 120)
        if kw.get("upi_id") is not None:
            u = str(kw["upi_id"]).strip()
            if u and not re.fullmatch(r"[\w.\-]{2,}@[a-zA-Z]{2,}", u):
                raise GraphicError("UPI ID naam@bank jaisa likhiye.")
            st.upi_id = u
        for k, lo, hi in (("gst_rate", 0, 28), ("advance_pct", 0, 100)):
            if kw.get(k) is not None:
                v = _num(kw[k])
                if v is None or not lo <= v <= hi:
                    raise GraphicError(f"{k} {lo}-{hi} ke beech.")
                setattr(st, k, v)
        if "extra_round" in kw:
            st.extra_round = None if kw["extra_round"] in (None, "") else _num(kw["extra_round"])
        for k, lo, hi in (("rounds", 0, 10), ("pay_days", 0, 120), ("validity_days", 1, 90)):
            if kw.get(k) is not None:
                v = _int(kw[k])
                if v is None or not lo <= v <= hi:
                    raise GraphicError(f"{k} {lo}-{hi} ke beech.")
                setattr(st, k, v)
        for k in ("handover_after_pay", "assign_copyright"):
            if kw.get(k) is not None:
                setattr(st, k, bool(kw[k]))
        if kw.get("morning_time"):
            if not re.fullmatch(r"\d{2}:\d{2}", str(kw["morning_time"])):
                raise GraphicError("morning_time HH:MM.")
            st.morning_time = str(kw["morning_time"])
        if kw.get("rules") is not None:
            rl = kw["rules"] if isinstance(kw["rules"], list) else [x for x in str(kw["rules"]).split("\n")]
            st.rules = _dump([R.clean(x, 200) for x in rl if R.clean(x, 200)][:30])
        v = _settings_view(st)
    return {"settings": v, "say": "Studio ke niyam save."}


# ---------------------------------------------------------------- clients + their brand kits
def _client_view(c: GraphicClient, full: bool = True) -> dict:
    cols = _j(c.colors, {})
    if not cols:
        from ..brand import rules as BR
        cols = BR.kit_colors(_j(c.palette, []) or ["#1565C0"])
    v = {"id": c.id, "number": c.number, "name": c.name, "business": c.business, "kind": c.kind, "phone": c.phone,
         "email": c.email, "gstin": c.gstin, "state": c.state, "country": c.country, "tds_pct": c.tds_pct,
         "logo": bool(c.logo_path and Path(c.logo_path).exists()), "forgotten": c.forgotten}
    if full:
        v.update({"tagline": c.tagline, "colors": cols, "colors_set": c.colors_set, "palette": _j(c.palette, []), "font": c.font,
                  "contact": _j(c.contact, {}), "language": c.language, "notes": c.notes, "no_messages": c.no_messages,
                  "cmyk": {k: R.hex_to_cmyk(h) for k, h in cols.items()}})
    return v


def _client(s, tenant: str, ref: str) -> GraphicClient:
    ref = (ref or "").strip()
    if not ref:
        raise GraphicError("Kaunsa client? Naam ya C-001 bataiye.")
    q = select(GraphicClient).where(GraphicClient.tenant_id == tenant)
    c = s.scalars(q.where(GraphicClient.id == ref)).first() or s.scalars(q.where(GraphicClient.number == ref.upper())).first()
    if c is None:
        low = ref.lower()
        rows = [x for x in s.scalars(q).all() if not x.forgotten and (low == x.name.lower() or low == x.business.lower())]
        if not rows:
            rows = [x for x in s.scalars(q).all() if not x.forgotten and (low in x.name.lower() or low in x.business.lower())]
        if len(rows) > 1:
            raise GraphicError(f"'{ref}' naam ke {len(rows)} client: number (C-001) bataiye.")
        c = rows[0] if rows else None
    if c is None:
        raise GraphicError(f"Client '{ref}' nahi mila.")
    return c


def client_save(tenant: str, ref: str = "", actor: str = "owner", **kw: Any) -> dict:
    from ..brand import rules as BR
    with _LOCK, session() as s:
        if ref:
            c = _client(s, tenant, ref)
        else:
            name = R.clean(kw.get("name") or kw.get("business"), 120)
            if not name:
                raise GraphicError("Client ka naam bataiye.")
            n = len(s.scalars(select(GraphicClient.id).where(GraphicClient.tenant_id == tenant)).all()) + 1
            c = GraphicClient(tenant_id=tenant, number=f"C-{n:03d}", name=name)
            s.add(c)
        for k, n in (("name", 120), ("business", 160), ("tagline", 160), ("notes", 600), ("country", 40), ("state", 20)):
            if kw.get(k) is not None:
                setattr(c, k, R.clean(kw[k], n))
        if kw.get("kind"):
            k = str(kw["kind"]).lower()
            if k not in ("business", "individual"):
                raise GraphicError("kind = business | individual")
            c.kind = k
        if kw.get("phone") is not None:
            p = str(kw["phone"]).strip()
            if p and not R.phone(p):
                raise GraphicError("Client ka phone 10 ankon ka mobile likhiye.")
            c.phone = R.phone(p)
        if kw.get("email") is not None:
            c.email = R.clean(kw["email"], 120)
        if kw.get("gstin") is not None:
            g = str(kw["gstin"]).strip().upper()
            if g and not R.gstin_ok(g):
                raise GraphicError(f"GSTIN {g} sahi nahi lagta.")
            c.gstin = g
        if "tds_pct" in kw:
            v = kw["tds_pct"]
            if v in (None, ""):
                c.tds_pct = None
            else:
                p = _num(v)
                if p is None or not 0 <= p <= 20:
                    raise GraphicError("TDS % 0-20.")
                c.tds_pct = p
        if kw.get("font"):
            f = str(kw["font"]).lower()
            if f not in BR.FONTS:
                raise GraphicError("font = " + " | ".join(BR.FONTS))
            c.font = f
        if kw.get("language"):
            c.language = R.clean(kw["language"], 10).lower()
        if isinstance(kw.get("colors"), dict) and kw["colors"]:
            cols = _j(c.colors, {}) or BR.kit_colors(_j(c.palette, []) or ["#1565C0"])
            for role, val in kw["colors"].items():
                if role not in ("primary", "secondary", "accent", "dark", "light"):
                    continue
                h = BR.parse_color(str(val))
                if not h:
                    raise GraphicError(f"'{val}' rang samajh nahi aaya (#1565C0 ya laal / neela).")
                cols[role] = h
            c.colors, c.colors_set = _dump(cols), True
        if isinstance(kw.get("contact"), dict):
            ct = _j(c.contact, {})
            for k in ("phone", "whatsapp", "website", "instagram", "address", "email"):
                if k in kw["contact"]:
                    v = R.clean(kw["contact"][k], 140)
                    if v:
                        ct[k] = v
                    else:
                        ct.pop(k, None)
            c.contact = _dump(ct)
        if kw.get("no_messages") is not None:
            c.no_messages = bool(kw["no_messages"])
        s.flush()
        v = _client_view(c)
    return {"client": v, "say": f"Client {v['number']} {v['name']} save."}


def client_logo(tenant: str, ref: str, data: bytes | None = None, file_id: str = "", name: str = "logo.png",
                actor: str = "owner") -> dict:
    """The client's logo: re-encoded by Pillow (EXIF / GPS dropped) and its colours read for their kit (brand engine maths)."""
    from .. import filecheck
    from ..brand import render as RN
    from ..brand import rules as BR
    if file_id:
        name, data = _load_file(tenant, file_id)
    if not data:
        raise GraphicError("Logo ki file bhejiye.")
    if filecheck.real_type(name, data).get("danger"):
        raise GraphicError("Yeh file photo nahi lagti; Hoola ne nahi li.")
    try:
        img, mime, px = RN.safe_image(data, 1200, keep_alpha=True)
    except Exception:
        raise GraphicError("Logo khul nahi raha (PNG / JPG bhejiye; SVG / AI ko PNG export karke).")
    pal = BR.palette_from_image(img)
    with _LOCK, session() as s:
        c = _client(s, tenant, ref)
        folder = _dir(tenant, "client_" + c.id)
        for old in folder.glob("logo.*"):
            old.unlink(missing_ok=True)
        p = folder / ("logo.png" if mime == "image/png" else "logo.jpg")
        p.write_bytes(img)
        import hashlib
        c.logo_path, c.logo_hash, c.palette = str(p), hashlib.sha256(img).hexdigest()[:16], _dump(pal)
        if not c.colors_set:
            c.colors = _dump(BR.kit_colors(pal))
        v = _client_view(c)
    say = f"{v['name']} ka logo save; rang mile: {', '.join(pal)}."
    if px[0] < 500 and px[1] < 500:
        say += f" Logo chhota hai ({px[0]}x{px[1]}): print ke liye bada PNG / vector chahiye."
    return {"client": v, "palette": pal, "say": say}


def clients(tenant: str) -> list[dict]:
    with session() as s:
        rows = s.scalars(select(GraphicClient).where(GraphicClient.tenant_id == tenant).order_by(GraphicClient.number)).all()
        return [_client_view(c, full=False) for c in rows]


def client_view(tenant: str, ref: str) -> dict:
    with session() as s:
        c = _client(s, tenant, ref)
        v = _client_view(c)
        v["jobs"] = [_job_view(s, j, False) for j in s.scalars(select(GraphicJob).where(
            GraphicJob.tenant_id == tenant, GraphicJob.client_id == c.id).order_by(GraphicJob.created_at.desc())).all()]
    return v


def _kit_of(c: GraphicClient | None) -> tuple[dict, str, str]:
    """The kit dict the brand engine's page() takes, built from the CLIENT (never her own brand kit)."""
    from ..brand import render as RN
    from ..brand import rules as BR
    if c is None:
        return {"name": "", "tagline": "", "colors": BR.kit_colors(["#1565C0"]), "font": "poppins", "contact": {}, "rules": [],
                "logo": False}, "", ""
    cols = _j(c.colors, {}) or BR.kit_colors(_j(c.palette, []) or ["#1565C0"])
    kit = {"name": c.business or c.name, "tagline": c.tagline, "colors": cols, "font": c.font, "contact": _j(c.contact, {}),
           "rules": [], "logo": bool(c.logo_path and Path(c.logo_path).exists())}
    uri = ""
    if kit["logo"]:
        data = Path(c.logo_path).read_bytes()
        uri = RN.data_uri(data, "image/png" if c.logo_path.endswith(".png") else "image/jpeg")
    return kit, uri, c.logo_hash


# ---------------------------------------------------------------- vendors (printers)
def _vendor_view(v: GraphicVendor) -> dict:
    return {"id": v.id, "name": v.name, "phone": v.phone, "email": v.email, "does": v.does, "spec": _j(v.spec, {}),
            "notes": v.notes, "active": v.active}


def _vendor(s, tenant: str, ref: str) -> GraphicVendor:
    ref = (ref or "").strip()
    q = select(GraphicVendor).where(GraphicVendor.tenant_id == tenant)
    v = s.scalars(q.where(GraphicVendor.id == ref)).first() if ref else None
    if v is None and ref:
        v = next((x for x in s.scalars(q).all() if ref.lower() in x.name.lower()), None)
    if v is None:
        raise GraphicError(f"Printer '{ref}' nahi mila.")
    return v


def vendor_save(tenant: str, name: str, phone: str = "", email: str = "", does: str = "", spec: dict | None = None,
                notes: str = "", vendor_id: str = "", actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        if vendor_id:
            v = _vendor(s, tenant, vendor_id)
        else:
            if not R.clean(name, 120):
                raise GraphicError("Printer ka naam bataiye.")
            v = GraphicVendor(tenant_id=tenant, name=R.clean(name, 120))
            s.add(v)
        if name:
            v.name = R.clean(name, 120)
        if phone:
            if not R.phone(phone):
                raise GraphicError("Printer ka phone 10 ankon ka mobile likhiye.")
            v.phone = R.phone(phone)
        if email:
            v.email = R.clean(email, 120)
        if does:
            v.does = R.clean(does, 300)
        if notes:
            v.notes = R.clean(notes, 600)
        if isinstance(spec, dict):
            sp = _j(v.spec, {})
            for k in ("color", "format"):
                if spec.get(k):
                    sp[k] = str(spec[k]).lower()[:10]
            for k in ("dpi", "bleed", "safe", "min_font_pt", "ink_limit"):
                if spec.get(k) not in (None, ""):
                    n = _num(spec[k])
                    if n is None or n < 0:
                        raise GraphicError(f"{k} sahi number likhiye.")
                    sp[k] = n
            if spec.get("pdfx") is not None:
                sp["pdfx"] = bool(spec["pdfx"])
            v.spec = _dump(sp)
        s.flush()
        out = _vendor_view(v)
    return {"vendor": out, "say": f"Printer {out['name']} save."}


def vendors(tenant: str) -> list[dict]:
    with session() as s:
        return [_vendor_view(v) for v in s.scalars(select(GraphicVendor).where(GraphicVendor.tenant_id == tenant)).all()]


# ---------------------------------------------------------------- jobs
def _job(s, tenant: str, ref: str) -> GraphicJob:
    ref = (ref or "").strip()
    if not ref:
        raise GraphicError("Kaunsa kaam? G-0001 jaisa number bataiye.")
    q = select(GraphicJob).where(GraphicJob.tenant_id == tenant)
    j = s.scalars(q.where(GraphicJob.id == ref)).first() or s.scalars(q.where(GraphicJob.number == ref.upper())).first()
    if j is None and re.fullmatch(r"\d{1,4}", ref):
        j = s.scalars(q.where(GraphicJob.number == f"G-{int(ref):04d}")).first()
    if j is None:
        raise GraphicError(f"Kaam '{ref}' nahi mila.")
    return j


def _versions(s, j: GraphicJob) -> list[GraphicVersion]:
    return list(s.scalars(select(GraphicVersion).where(GraphicVersion.job_id == j.id).order_by(GraphicVersion.n)).all())


def _spec_of(s, j: GraphicJob) -> dict:
    if not j.print_fmt:
        return {}
    vspec = {}
    if j.vendor_id:
        v = s.get(GraphicVendor, j.vendor_id)
        vspec = _j(v.spec, {}) if v else {}
    return R.format_spec(j.print_fmt, _j(j.print_custom, {}), vspec)


def _clean_lines(lines: Any) -> list[dict]:
    out = []
    for x in lines or []:
        if isinstance(x, str):
            m = re.match(r"\s*(.+?)\s*[-:@]\s*(?:rs\.?|₹)?\s*([\d,.]+\s*(?:k|hazaar)?)\s*$", x, re.I)
            x = {"name": m.group(1), "rate": m.group(2)} if m else {"name": x}
        if not isinstance(x, dict):
            continue
        name = R.clean(x.get("name"), 120)
        if not name:
            continue
        rate = _num(x.get("rate") if x.get("rate") is not None else x.get("price"))
        qty = _num(x.get("qty")) or 1.0
        out.append({"name": name, "qty": qty, "rate": rate})
    return out[:30]


def _rounds_left(j: GraphicJob) -> int:
    return j.rounds_included + j.extra_rounds + j.waived_rounds - j.rounds_used


def _job_view(s, j: GraphicJob, full: bool = True) -> dict:
    c = s.get(GraphicClient, j.client_id) if j.client_id else None
    vs = _versions(s, j)
    last = vs[-1] if vs else None
    v = {"id": j.id, "number": j.number, "kind": j.kind, "kind_label": R.KINDS.get(j.kind, {}).get("label", j.kind),
         "title": j.title, "client": c.name if c else "", "client_id": j.client_id, "client_number": c.number if c else "",
         "status": j.status, "status_label": STATUS.get(j.status, j.status), "due": j.due,
         "rounds": {"included": j.rounds_included, "used": j.rounds_used, "extra": j.extra_rounds, "waived": j.waived_rounds,
                    "left": _rounds_left(j), "pending_feedback": j.pending_feedback},
         "versions": len(vs), "last_version": last.n if last else 0,
         "thumb": _proof_url(j, last) if last else "", "updated_at": _aware(j.updated_at).isoformat() if j.updated_at else ""}
    if full:
        st = _st(s, j.tenant_id)
        v.update({"brief": j.brief, "facts": j.facts, "sizes": _j(j.sizes, []), "print_fmt": j.print_fmt,
                  "print_custom": _j(j.print_custom, {}), "print_job": _j(j.print_job, {}), "spec": _spec_of(s, j),
                  "vendor_id": j.vendor_id, "lines": _j(j.lines, []), "extra_round_price": j.extra_round_price,
                  "advance_pct": j.advance_pct, "quote": _quote(s, j.tenant_id, j), "feedback": _j(j.feedback, []),
                  "client_ok": _j(j.client_ok, {}), "accepted": _j(j.accepted, {}),
                  "assets": [{**a, "verdict": R.asset_verdict(a)} for a in _j(j.assets, [])], "tm": _j(j.tm, {}),
                  "assignment": _j(j.assignment, {}), "payments": _j(j.payments, []), "invoices": _j(j.invoices, []),
                  "paid": _paid(j), "balance": round(_quote(s, j.tenant_id, j)["total"] - _paid(j), 2)
                  if _quote(s, j.tenant_id, j)["total"] is not None else None,
                  "handover": _j(j.handover, {}), "log": _j(j.log, [])[-30:],
                  "version_list": [_version_view(j, x) for x in vs],
                  "client_view": _client_view(c) if c else {}, "studio": st.studio})
    return v


def _proof_url(j: GraphicJob, x: GraphicVersion) -> str:
    pr = _j(x.proofs, {})
    first = next(iter(pr.values()), "")
    return f"/api/graphic/files/{j.id}/{first}" if first else ""


def _version_view(j: GraphicJob, x: GraphicVersion) -> dict:
    pr = _j(x.proofs, {})
    return {"id": x.id, "n": x.n, "source": x.source, "status": x.status, "round": x.round, "layout": x.layout,
            "sizes": _j(x.sizes, []), "content": _j(x.content, {}),
            "proofs": {k: f"/api/graphic/files/{j.id}/{n}" for k, n in pr.items()},
            "file": f"/api/graphic/files/{j.id}/{x.file_name}" if x.file_name else "", "file_name": x.file_name,
            "preflight": _j(x.preflight, {}), "checks": _j(x.checks, []),
            "blocks": [c["text"] for c in _j(x.checks, []) if c.get("level") == "block"], "note": x.note,
            "created_at": _aware(x.created_at).isoformat() if x.created_at else ""}


_JOB_KEYS = ("title", "kind", "brief", "facts", "sizes", "print_fmt", "print_custom", "print_job", "vendor", "due", "lines",
             "rounds", "extra_round_price", "advance_pct")
_MONEY_KEYS = ("lines", "rounds", "extra_round_price", "advance_pct")


def job_save(tenant: str, job: str = "", client: str = "", actor: str = "owner", conv: str = "", **kw: Any) -> dict:
    """New job or changes. Prices / rounds / advance are HER numbers (owner only once a quote went out). Brief = data."""
    from ..brand import rules as BR
    text = " ".join(str(kw.get(k) or "") for k in ("title", "brief", "facts"))
    bad = BR.protected(text)
    if bad:
        raise GraphicError(f"Vyapar ke design mein {', '.join(bad)} nahi laga sakte (Emblems Act 1950).")
    cl = R.clone_problem(text)
    if cl:
        raise GraphicError(cl)
    try:
        from ..ads.rules import banned
        for msg in banned(text):
            raise GraphicError(msg + " Aisa design Hoola nahi banayega.")
    except ImportError:
        pass
    warn: list[str] = []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        if job:
            j = _job(s, tenant, job)
            if j.status in ("done", "cancelled"):
                raise GraphicError(f"{j.number} {STATUS[j.status]}: badla nahi ja sakta.")
            if any(k in kw for k in _MONEY_KEYS) and not is_owner(actor):
                raise GraphicError("Daam / rounds / advance sirf owner badal sakti hain.")
            if any(k in kw for k in ("lines", "rounds", "extra_round_price", "advance_pct")) and j.quote_ok and not is_owner(actor):
                raise GraphicError("Quote ja chuka: badlav owner hi karein.")
        else:
            c = _client(s, tenant, client)
            st.job_seq += 1
            kind = kw.get("kind") or R.kind_of(text)
            kind = kind if kind in R.KINDS else "other"
            j = GraphicJob(tenant_id=tenant, number=f"G-{st.job_seq:04d}", client_id=c.id, kind=kind,
                           rounds_included=R.KINDS[kind]["rounds"] if st.rounds == 2 else st.rounds,
                           extra_round_price=st.extra_round, advance_pct=st.advance_pct, conv=conv)
            s.add(j)
            spec = R.KINDS[kind]
            if not kw.get("sizes") and spec.get("sizes"):
                j.sizes = _dump(spec["sizes"])
            if not kw.get("print_fmt") and spec.get("print") and spec.get("format") in R.FORMATS:
                j.print_fmt = spec["format"]
            if not kw.get("title"):
                j.title = R.clean((kw.get("brief") or spec["label"]).split("\n")[0], 80)
        if kw.get("kind") and kw["kind"] in R.KINDS:
            j.kind = kw["kind"]
        if kw.get("title"):
            j.title = R.clean(kw["title"], 160)
        if kw.get("brief") is not None:
            j.brief = R.clean(kw["brief"], 4000)
        if kw.get("facts") is not None:
            j.facts = R.clean(kw["facts"], 2000)
        if kw.get("sizes") is not None:
            j.sizes = _dump(BR.sizes_of(kw["sizes"]) if kw["sizes"] else [])
        if kw.get("print_fmt") is not None:
            f = str(kw["print_fmt"]).lower().strip()
            if f and f not in R.FORMATS and f != "custom":
                raise GraphicError("print_fmt = " + " | ".join(list(R.FORMATS) + ["custom"]))
            j.print_fmt = f
        if isinstance(kw.get("print_custom"), dict):
            pc = {k: _num(v) for k, v in kw["print_custom"].items() if k in ("w_mm", "h_mm", "bleed_mm", "safe_mm")}
            j.print_custom = _dump({k: v for k, v in pc.items() if v is not None})
            j.print_fmt = j.print_fmt or "custom"
        if isinstance(kw.get("print_job"), dict):
            pj = _j(j.print_job, {})
            for k in ("qty", "stock", "finish", "sides", "notes"):
                if kw["print_job"].get(k) not in (None, ""):
                    pj[k] = R.clean(kw["print_job"][k], 200)
            j.print_job = _dump(pj)
        if kw.get("vendor"):
            j.vendor_id = _vendor(s, tenant, str(kw["vendor"])).id
        if kw.get("due") is not None:
            if kw["due"]:
                d = _date(kw["due"])
                if d is None:
                    raise GraphicError("Due date YYYY-MM-DD / DD-MM-YYYY likhiye.")
                if d < today(tenant):
                    raise GraphicError("Due date beet chuki hai.")
                usual = R.KINDS.get(j.kind, {}).get("days", 5)
                if (d - today(tenant)).days < usual:
                    warn.append(f"{R.KINDS[j.kind]['label']} mein aam taur par ~{usual} din lagte hain; {d:%d %b} tak tight hai.")
                j.due = d.isoformat()
            else:
                j.due = ""
        if kw.get("lines") is not None:
            j.lines = _dump(_clean_lines(kw["lines"]))
        if kw.get("rounds") is not None:
            r = _int(kw["rounds"])
            if r is None or r > 10:
                raise GraphicError("rounds 0-10.")
            j.rounds_included = r
        if "extra_round_price" in kw:
            j.extra_round_price = None if kw["extra_round_price"] in (None, "") else _num(kw["extra_round_price"])
        if kw.get("advance_pct") is not None:
            a = _num(kw["advance_pct"])
            if a is None or not 0 <= a <= 100:
                raise GraphicError("advance % 0-100.")
            j.advance_pct = a
        if j.print_fmt == "custom" and not (_j(j.print_custom, {}).get("w_mm") and _j(j.print_custom, {}).get("h_mm")):
            warn.append("Custom print size: chaudai / oonchai mm mein bataiye (print_custom w_mm, h_mm).")
        if j.kind == "logo" and not _j(j.tm, {}):
            warn.append("Logo ke liye IP India trade-mark search (tm) zaroor karwaiye, client ko batana hoga.")
        _log(j, "Kaam save", actor_name(tenant, actor))
        s.flush()
        v = _job_view(s, j)
    say = f"{v['number']} ({v['kind_label']}) {v['client']} ke liye save."
    if v["quote"]["missing"]:
        say += " Daam abhi nahi: quote se pehle aap daam bataiye."
    if warn:
        say += " " + " ".join(warn)
    _publish(tenant, "graphic_job", {"job": {k: v[k] for k in ("id", "number", "title", "status", "client")}, "say": say}, conv)
    return {"job": v, "warnings": warn, "say": say}


def jobs(tenant: str, status: str = "", client: str = "") -> list[dict]:
    with session() as s:
        q = select(GraphicJob).where(GraphicJob.tenant_id == tenant)
        if status == "open":
            q = q.where(GraphicJob.status.not_in(("done", "cancelled")))
        elif status:
            q = q.where(GraphicJob.status == status)
        if client:
            q = q.where(GraphicJob.client_id == _client(s, tenant, client).id)
        return [_job_view(s, j, False) for j in s.scalars(q.order_by(GraphicJob.updated_at.desc())).all()][:200]


def job_view(tenant: str, ref: str) -> dict:
    with session() as s:
        return _job_view(s, _job(s, tenant, ref))


# ---------------------------------------------------------------- money: quote
def _paid(j: GraphicJob) -> float:
    return round(sum(float(p.get("amount") or 0) for p in _j(j.payments, [])), 2)


def _quote(s, tenant: str, j: GraphicJob) -> dict:
    st = _st(s, tenant)
    c = s.get(GraphicClient, j.client_id) if j.client_id else None
    lines, missing = [], []
    sub = 0.0
    for ln in _j(j.lines, []):
        amt = None if ln.get("rate") is None else round(float(ln["rate"]) * float(ln.get("qty") or 1), 2)
        if amt is None:
            missing.append(ln["name"])
        else:
            sub += amt
        lines.append({**ln, "amount": amt})
    if j.extra_rounds and j.extra_round_price:
        amt = round(j.extra_rounds * j.extra_round_price, 2)
        lines.append({"name": "Extra revision round", "qty": j.extra_rounds, "rate": j.extra_round_price, "amount": amt})
        sub += amt
    if not lines:
        missing.append("daam")
    disc = min(j.discount or 0.0, sub)
    taxable = round(sub - disc, 2)
    export = bool(c and c.country and c.country.lower() not in ("india", "bharat", "in"))
    her = R.state_of(st.gstin, st.state)
    theirs = R.state_of(c.gstin if c else "", c.state if c else "") or her
    g = R.gst_lines(taxable, st.gst_rate if st.gstin else 0.0, her, theirs, export, bool(st.lut)) if st.gstin else \
        {"kind": "none", "tax": 0.0, "rows": []}
    total = None if missing else round(taxable + g["tax"], 2)
    adv = None if total is None else round(total * (j.advance_pct or 0) / 100, 2)
    words = ""
    if total is not None:
        try:
            from ..india.money import rupees_words
            words = rupees_words(total, "en")
        except Exception:
            words = ""
    return {"lines": lines, "subtotal": round(sub, 2), "discount": disc, "taxable": taxable, "gst": g, "total": total,
            "total_text": _rs(total), "total_words": words, "advance": adv, "advance_text": _rs(adv), "missing": missing,
            "rounds": j.rounds_included, "extra_round_price": j.extra_round_price, "sac": st.sac if st.gstin else "",
            "export": export, "gst_note": "" if st.gstin else "GSTIN nahi: GST nahi lagaya (Rs 20 lakh se upar registration zaroori).",
            "tds_note": R.tds_note(c.kind if c else "individual", c.tds_pct if c else None, taxable)}


# ---------------------------------------------------------------- versions (proofs)
def _round_gate(s, j: GraphicJob) -> int:
    """Revision rounds in code. Returns the round number the new version belongs to (0 = first concepts)."""
    vs = _versions(s, j)
    if not vs or not any(x.status in ("sent", "client_ok") for x in vs):
        return j.rounds_used                       # still working before the client saw anything: no round used
    if not j.pending_feedback:
        if any(x.status == "client_ok" for x in vs):
            raise GraphicError(f"{j.number}: client ne pehle hi haan kar di; naya badlav = naya round (pehle client ka feedback likhiye).")
        return j.rounds_used
    if _rounds_left(j) <= 0:
        price = _rs(j.extra_round_price) if j.extra_round_price else "[daam?]"
        raise GraphicError(f"{j.number}: quote ke {j.rounds_included} revision round poore ho gaye. Agla round extra hai ({price}): "
                           "extra round ka card banaiye (aapki haan) ya owner 'is baar free' (waive) kahein.")
    j.rounds_used += 1
    j.pending_feedback = False
    return j.rounds_used


def _new_version(s, tenant: str, j: GraphicJob, rnd: int, **kw) -> GraphicVersion:
    vs = _versions(s, j)
    for x in vs:
        if x.status == "draft":
            x.status = "old"
    x = GraphicVersion(tenant_id=tenant, job_id=j.id, n=(vs[-1].n + 1) if vs else 1, round=rnd, **kw)
    s.add(x)
    s.flush()
    if j.status in ("brief", "quoted", "accepted"):
        j.status = "proof"
    return x


def _brand_check(tenant: str, j: GraphicJob, content: dict, layout: str, sizes: list[str], fits: dict, kit: dict) -> list[dict]:
    """The brand engine's own checks (Emblems Act, blanks, claims, fit, contrast, logo / contact) with the client's kit."""
    from ..brand import service as BS
    ns = SimpleNamespace(content=_dump(content), brief=f"{j.brief}\n{j.facts}", layout=layout, kind="poster", photo_px="",
                         sizes=_dump(sizes), festival="{}", bg_path="", number=j.number)
    try:
        return BS.check(tenant, ns, fits, {**kit, "rules": [j.facts] if j.facts else []})
    except Exception as e:
        log.info("brand check failed: %s", e)
        return []


def _render(jobs_: list[dict]) -> list[dict]:
    from ..brand import render as RN
    try:
        return RN.render(jobs_)
    except RN.RenderError as e:
        raise GraphicError(str(e))


def proof_render(tenant: str, job: str, words: dict | None = None, layout: str = "", sizes: Any = None, instruction: str = "",
                 actor: str = "owner", conv: str = "") -> dict:
    """A proof drawn by the brand engine in the CLIENT's kit. Words only from the brief / facts (Claude arranges, never invents)."""
    from ..brand import render as RN
    from ..brand import rules as BR
    from ..brand import service as BS
    if instruction and (BR.protected(instruction) or R.clone_problem(instruction)):
        raise GraphicError(R.clone_problem(instruction) or "Emblems Act 1950: yeh chinh / naam design mein nahi lag sakta.")
    with session() as s:
        j = _job(s, tenant, job)
        c = s.get(GraphicClient, j.client_id)
        kit, logo_uri, _lh = _kit_of(c)
        size_list = BR.sizes_of(sizes) if sizes else [x for x in _j(j.sizes, []) if x in BR.SIZES]
        if j.print_fmt in BR.SIZES and j.print_fmt not in size_list:
            size_list.append(j.print_fmt)
        if not size_list:
            raise GraphicError(f"{R.KINDS.get(j.kind, {}).get('label', j.kind)} ka size engine mein nahi (jaise visiting card): "
                               "apni design file upload kijiye (proof_upload), Hoola print jaanch karega.")
        vs = _versions(s, j)
        base = next((_j(x.content, {}) for x in reversed(vs) if x.source == "render"), {})
        base_layout = next((x.layout for x in reversed(vs) if x.source == "render"), "")
        brief, facts, lang = j.brief, j.facts, c.language if c else "hinglish"
        number = j.number
    if words:
        content = BS._clean_content(words)
    elif instruction and base:
        r = _ai_words(BS.REVISE_SYSTEM, f"CURRENT: {json.dumps(base, ensure_ascii=False)}\nLAYOUT: {base_layout}\n"
                                        f"FACTS (only these may appear): {facts}\nINSTRUCTION (data): {R.clean(instruction, 800)}")
        content = BS._clean_content(r, base) if r else dict(base)
        layout = layout or str(r.get("layout") or "")
    else:
        prompt = (f"KIND: poster for a client\nLANGUAGE: {lang}\nBUSINESS: {kit['name']} | tagline: {kit['tagline']}\n"
                  f"FACTS THAT MAY APPEAR (her words): {facts or '-'}\nCLIENT BRIEF (data):\n{brief[:2000]}")
        r = _ai_words(BS.DESIGN_SYSTEM, prompt)
        content = BS._clean_content(r) if (r.get("headline") or r.get("greeting")) else \
            BS._fallback_words(facts or brief, "poster", {}, lang)
        layout = layout or str(r.get("layout") or "")
    content.pop("layout", None)
    content.pop("title", None)
    lay = layout if layout in BR.LAYOUTS and layout != "festival" else (base_layout or "hero")
    if lay in ("photo", "split"):
        lay = "hero"
    page_d = {**content, "layout": lay, "kind": "poster", "festival": {}, "show_contact": True}
    seed = int(re.sub(r"\D", "", number) or 7)
    kit2 = dict(kit)
    if content.get("colors"):
        kit2["colors"] = {**kit["colors"], **content["colors"]}
    res = _render([{"html": RN.page(page_d, kit2, sz, proof=True, logo=logo_uri, seed=seed), "size": sz, "out": "jpg",
                    "quality": 84, "scale_to": min(BR.SIZES[sz]["w"], 1080)} for sz in size_list])
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        rnd = _round_gate(s, j)
        x = _new_version(s, tenant, j, rnd, source="render", content=_dump(content), layout=lay, sizes=_dump(size_list),
                         note=R.clean(instruction, 300))
        folder = _dir(tenant, j.id)
        proofs, fits = {}, {}
        for sz, rr in zip(size_list, res):
            name = f"proof_v{x.n}_{sz}.jpg"
            (folder / name).write_bytes(rr["data"])
            proofs[sz], fits[sz] = name, rr["fit"]
        x.proofs = _dump(proofs)
        import hashlib
        x.file_hash = hashlib.sha256(_dump([content, lay, size_list, kit2["colors"]]).encode()).hexdigest()[:32]
        jv = j
        content_c, sizes_c = content, size_list
    checks = _brand_check(tenant, jv, content_c, lay, sizes_c, fits, kit2)
    checks += _job_checks(tenant, job)
    with _LOCK, session() as s:
        x = s.get(GraphicVersion, x.id)
        x.checks = _dump(checks)
        j = _job(s, tenant, job)
        _log(j, f"Proof v{x.n} bana (engine, round {x.round})", actor_name(tenant, actor))
        v = _version_view(j, x)
        jn = j.number
    say = f"{jn} proof v{v['n']} ({len(sizes_c)} size) taiyaar" + (f"; pehle theek karna: {v['blocks'][0]}" if v["blocks"] else "") + \
        ". Dekh kar 'client ko bhejo' boliye: card aayega."
    _publish(tenant, "graphic_job", {"job": {"id": v["id"], "number": jn}, "version": v, "say": say}, conv)
    return {"version": v, "say": say}


def _job_checks(tenant: str, job: str) -> list[dict]:
    """Job-wide checks every proof carries: licences of fonts / pictures used, logo trademark search."""
    out = []
    with session() as s:
        j = _job(s, tenant, job)
        for a in _j(j.assets, []):
            vd = R.asset_verdict(a)
            if vd["level"] in ("block", "warn"):
                out.append({"level": vd["level"], "text": f"{a.get('name')}: {vd['say']}"})
        if j.kind == "logo" and not _j(j.tm, {}).get("result"):
            out.append({"level": "warn", "text": "Trade-mark search abhi nahi hua: IP India public search karke likhiye (tm)."})
    return out


def _proof_image(data: bytes) -> bytes:
    """Client-facing proof of her artwork: re-encoded by Pillow (EXIF / GPS / camera gone), max 1600 px, PROOF watermark."""
    from PIL import Image, ImageDraw, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    im = im.convert("RGB")
    im.thumbnail((1600, 1600))
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    step = max(120, im.size[0] // 4)
    for y in range(0, im.size[1], step):
        for x in range(-step, im.size[0], step * 2):
            d.text((x + (y // step % 2) * step, y), "PROOF · HOOLA", fill=(220, 40, 40, 70))
    out = Image.alpha_composite(im.convert("RGBA"), over).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def _pdf_preview(data: bytes) -> bytes | None:
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(data)
        img = doc[0].render(scale=1.5).to_pil()
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "PNG")
        return _proof_image(buf.getvalue())
    except Exception:
        return None


def proof_upload(tenant: str, job: str, data: bytes | None = None, name: str = "", file_id: str = "", note: str = "",
                 actor: str = "owner", conv: str = "") -> dict:
    """Her own artwork (PDF / PNG / JPG / TIFF from her design tool). Kept byte-exact for print; preflighted for the print format;
    a re-encoded, watermarked JPG proof is what the client sees."""
    from .. import filecheck
    import hashlib
    if file_id:
        name, data = _load_file(tenant, file_id)
    if not data:
        raise GraphicError("Design ki file bhejiye (PDF / PNG / JPG).")
    if len(data) > 80 * 1024 * 1024:
        raise GraphicError("File 80 MB se badi: printer ke liye compress / link bhejiye.")
    rt = filecheck.real_type(name or "art", data)
    if rt.get("danger"):
        raise GraphicError("Yeh file design / photo nahi lagti; Hoola ne nahi li.")
    is_pdf = data[:5] == b"%PDF-"
    ext = "pdf" if is_pdf else (Path(name or "").suffix.lower().lstrip(".") or "png")
    if not is_pdf:
        try:
            from PIL import Image
            Image.open(io.BytesIO(data)).verify()
        except Exception:
            raise GraphicError("File khul nahi rahi: PDF / PNG / JPG / TIFF bhejiye (AI / CDR / PSD ko PDF export kijiye).")
    with session() as s:
        j = _job(s, tenant, job)
        spec = _spec_of(s, j)
    pf = R.preflight(data, name, spec)
    proof = _pdf_preview(data) if is_pdf else _proof_image(data)
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        rnd = _round_gate(s, j)
        x = _new_version(s, tenant, j, rnd, source="upload", note=R.clean(note, 300), file_mime="application/pdf" if is_pdf
                         else f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}", preflight=_dump(pf),
                         file_hash=hashlib.sha256(data).hexdigest()[:32])
        folder = _dir(tenant, j.id)
        fname = f"art_v{x.n}.{ext}"
        (folder / fname).write_bytes(data)
        x.file_name = fname
        if proof:
            (folder / f"proof_v{x.n}.jpg").write_bytes(proof)
            x.proofs = _dump({"art": f"proof_v{x.n}.jpg"})
        checks = [dict(i, pre=True) for i in pf.get("issues", [])]     # print problems stop the print order, not the look
        if not spec and _j(j.sizes, []):
            checks.append({"level": "info", "text": "Screen design: rang RGB theek hai."})
        x.checks = _dump(checks)
        jn = j.number
        jid = j.id
    extra = _job_checks(tenant, jid)
    with _LOCK, session() as s:
        x = s.get(GraphicVersion, x.id)
        x.checks = _dump(_j(x.checks, []) + extra)
        j = _job(s, tenant, jid)
        _log(j, f"Design file v{x.n} aayi (round {x.round}); print jaanch: {'theek' if pf.get('ok') else 'dikkat'}",
             actor_name(tenant, actor))
        v = _version_view(j, x)
    say = f"{jn} v{v['n']} file mili."
    if spec:
        say += " Print jaanch theek." if pf.get("ok") else f" Print jaanch: {v['blocks'][0] if v['blocks'] else 'dekhiye'}."
    _publish(tenant, "graphic_job", {"job": {"id": jid, "number": jn}, "version": v, "say": say}, conv)
    return {"version": v, "preflight": pf, "say": say}


def feedback(tenant: str, job: str, text: str, version: int | None = None, actor: str = "owner", conv: str = "") -> dict:
    """The client's notes on a proof (their words = data). Opens the next revision round; tells her when rounds are used up."""
    t = R.clean(text, 3000)
    if not t:
        raise GraphicError("Client ne kya badlav bola? Likhiye.")
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        vs = _versions(s, j)
        sent = [x for x in vs if x.status in ("sent", "client_ok")]
        if not sent:
            raise GraphicError(f"{j.number}: abhi koi proof client ko gaya hi nahi (pehle proof card par haan).")
        n = version or sent[-1].n
        fb = _j(j.feedback, [])
        fb.append({"at": now().isoformat(), "version": n, "text": t, "by": actor_name(tenant, actor), "round": j.rounds_used + 1})
        j.feedback = _dump(fb[-60:])
        j.pending_feedback = True
        for x in vs:
            if x.status == "client_ok":
                x.status = "sent"
        if j.status == "approved":
            j.status = "proof"
            j.client_ok = "{}"
        _log(j, f"Client feedback v{n}", actor_name(tenant, actor))
        left = _rounds_left(j)
        jn, inc = j.number, j.rounds_included
        price = j.extra_round_price
    if left > 0:
        say = f"{jn}: feedback likha. Agla version ek revision round lega ({left} baaki)."
    else:
        say = (f"{jn}: feedback likha, lekin quote ke {inc} round poore. Extra round {_rs(price) if price else '[daam?]'}: "
               "extra round card banau? (aapki haan)")
    return {"rounds_left": left, "say": say}


def waive_round(tenant: str, job: str, reason: str = "", actor: str = "owner") -> dict:
    _owner_only(actor)
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        j.waived_rounds += 1
        _log(j, f"Ek round free diya: {R.clean(reason, 200)}", "Owner")
        jn = j.number
    return {"say": f"{jn}: ek extra round aapki marzi se free."}


def client_approved(tenant: str, job: str, version: int | None = None, evidence: str = "", actor: str = "owner") -> dict:
    """She records that the CLIENT said yes to a proof she sent (their words / screenshot note = evidence)."""
    ev = R.clean(evidence, 600)
    if not ev:
        raise GraphicError("Client ki haan ka saboot likhiye (unka message / screenshot ki baat).")
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        vs = _versions(s, j)
        x = next((v for v in vs if v.n == version), None) if version else next((v for v in reversed(vs) if v.status == "sent"), None)
        if x is None or x.status not in ("sent", "client_ok"):
            raise GraphicError("Yeh version client ko gaya hi nahi: pehle proof card par haan.")
        for v in vs:
            if v.status == "client_ok":
                v.status = "sent"
        x.status = "client_ok"
        j.client_ok = _dump({"version": x.n, "at": now().isoformat(), "evidence": ev})
        j.pending_feedback = False
        j.status = "approved"
        _log(j, f"Client ne v{x.n} par haan ki", actor_name(tenant, actor))
        jn, n = j.number, x.n
    return {"say": f"{jn}: client ki haan v{n} par likhi. Ab files handover / print order ke card bana sakte hain."}


# ---------------------------------------------------------------- assets + trademark
def asset_add(tenant: str, job: str, name: str, kind: str = "font", source: str = "", licence: str = "", licence_ref: str = "",
              actor: str = "owner") -> dict:
    nm = R.clean(name, 120)
    if not nm:
        raise GraphicError("Font / photo ka naam bataiye.")
    kind = kind if kind in ("font", "image", "icon", "illustration", "mockup", "other") else "other"
    a = {"name": nm, "kind": kind, "source": R.clean(source, 200), "licence": (licence or "").lower(),
         "licence_ref": R.clean(licence_ref, 80)}
    if kind == "font" and a["licence"] not in R.FONT_LICENCES:
        a["licence"] = R.font_kind(nm, source)
    if kind != "font" and a["licence"] not in R.ASSET_LICENCES:
        a["licence"] = "unknown"
    vd = R.asset_verdict(a)
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        al = [x for x in _j(j.assets, []) if not (x.get("name", "").lower() == nm.lower() and x.get("kind") == kind)]
        al.append(a)
        j.assets = _dump(al[-60:])
        _log(j, f"Asset {nm} ({vd['label']})", actor_name(tenant, actor))
        jn = j.number
    return {"asset": {**a, "verdict": vd}, "say": f"{jn}: {nm} - {vd['say']}"}


def asset_remove(tenant: str, job: str, name: str, actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        al = _j(j.assets, [])
        keep = [x for x in al if x.get("name", "").lower() != (name or "").lower()]
        if len(keep) == len(al):
            raise GraphicError(f"'{name}' list mein nahi.")
        j.assets = _dump(keep)
        jn = j.number
    return {"say": f"{jn}: {name} hata diya."}


def tm_help(tenant: str, job: str, classes: list[int] | None = None) -> dict:
    with session() as s:
        j = _job(s, tenant, job)
        c = s.get(GraphicClient, j.client_id)
        nm = (c.business or c.name) if c else j.title
        biz = f"{c.business if c else ''} {c.notes if c else ''} {j.brief}"
    return R.tm_help(nm, biz, classes)


def tm_record(tenant: str, job: str, result: str, classes: list[int] | None = None, notes: str = "", actor: str = "owner") -> dict:
    res = (result or "").lower()
    if res not in ("nothing_similar", "similar_found", "registered_same", "not_done"):
        raise GraphicError("result = nothing_similar | similar_found | registered_same | not_done")
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        j.tm = _dump({"result": res, "classes": [int(x) for x in (classes or []) if str(x).isdigit() and 1 <= int(x) <= 45],
                      "notes": R.clean(notes, 600), "at": now().isoformat(), "by": actor_name(tenant, actor)})
        _log(j, f"Trade-mark search: {res}", actor_name(tenant, actor))
        jn = j.number
    say = {"nothing_similar": "kuch milta-julta nahi mila (yeh clearance nahi; vakil ki raay behtar).",
           "similar_found": "milte-julte mark mile: client ko batana zaroori, naam / logo badalne ki salah.",
           "registered_same": "wahi mark pehle se registered: is logo / naam par aage badhna jokhim hai, client ko bataiye.",
           "not_done": "search nahi hua (likh liya)."}[res]
    return {"say": f"{jn}: {say}"}


# ---------------------------------------------------------------- cards (HER tap only)
def _card_view(c: GraphicCard) -> dict:
    sh = _j(c.show, {})
    return {"id": c.id, "kind": c.kind, "title": CARD_TITLE.get(c.kind, c.kind), "status": c.status, "hash": c.hash,
            "show": {k: v for k, v in sh.items() if not k.startswith("_")}, "job_id": c.job_id, "money": c.kind in MONEY_CARDS,
            "asked_by": c.asked_by, "reason": c.reason, "result": _j(c.result, {}),
            "created_at": _aware(c.created_at).isoformat() if c.created_at else ""}


def _finals_plan(s, j: GraphicJob, x: GraphicVersion) -> list[dict]:
    from ..brand import rules as BR
    if x.source == "upload":
        return [{"name": f"{j.number}-final-v{x.n}.{x.file_name.rsplit('.', 1)[-1]}", "what": "Aapki final design file"}]
    out = []
    for sz in _j(x.sizes, []):
        if BR.SIZES.get(sz, {}).get("print"):
            out.append({"name": f"{j.number}-{sz}.pdf", "what": f"{BR.SIZES[sz]['label']} print PDF (bleed ke saath)"})
        else:
            out.append({"name": f"{j.number}-{sz}.png", "what": BR.SIZES.get(sz, {}).get("label", sz)})
    return out


def _show(s, tenant: str, kind: str, j: GraphicJob | None, inp: dict) -> dict:
    """What the card shows, rebuilt from the state NOW (the hash covers it: any change after the card = stale)."""
    if j is None:
        return {"kind": kind, **inp}
    st = _st(s, tenant)
    c = s.get(GraphicClient, j.client_id) if j.client_id else None
    base = {"job": j.number, "title": j.title, "client": c.name if c else "", "phone": c.phone if c else "",
            "email": c.email if c else "", "kind_label": R.KINDS.get(j.kind, {}).get("label", j.kind)}
    vs = _versions(s, j)
    if kind == "quote":
        q = _quote(s, tenant, j)
        valid = (today(tenant) + timedelta(days=st.validity_days)).isoformat() if not inp.get("valid_until") else inp["valid_until"]
        inp["valid_until"] = valid
        return {**base, "lines": q["lines"], "subtotal": q["subtotal"], "discount": q["discount"], "gst": q["gst"],
                "total": q["total"], "total_text": q["total_text"], "advance_text": q["advance_text"], "due": j.due,
                "rounds": j.rounds_included, "extra_round_text": _rs(j.extra_round_price) if j.extra_round_price else "",
                "valid_until": valid, "deliverables": _j(j.sizes, []) + ([j.print_fmt] if j.print_fmt else []),
                "rights": "Copyright poore bhugtaan ke baad likhit assignment se (Copyright Act s.19)." if st.assign_copyright
                else "Copyright designer ke paas; client ko use ka licence.", "_in": inp}
    if kind == "proof":
        x = next((v for v in vs if v.n == inp.get("version")), None)
        if x is None:
            raise GraphicError("Version nahi mila.")
        return {**base, "version": x.n, "round": x.round, "rounds_left": _rounds_left(j), "rounds": j.rounds_included,
                "file_hash": x.file_hash, "proofs": _version_view(j, x)["proofs"], "checks": _j(x.checks, []),
                "blocks": [c["text"] for c in _j(x.checks, []) if c.get("level") == "block" and not c.get("pre")],
                "print_problems": [c["text"] for c in _j(x.checks, []) if c.get("pre") and c.get("level") == "block"], "_in": inp}
    if kind == "extra":
        return {**base, "amount": j.extra_round_price, "amount_text": _rs(j.extra_round_price), "used": j.rounds_used,
                "included": j.rounds_included, "extra_so_far": j.extra_rounds, "_in": inp}
    if kind == "handover":
        x = next((v for v in vs if v.status == "client_ok"), None)
        q = _quote(s, tenant, j)
        bal = None if q["total"] is None else round(q["total"] - _paid(j), 2)
        assets = [{"name": a.get("name"), **R.asset_verdict(a)} for a in _j(j.assets, [])]
        blocks = []
        if x is None:
            blocks.append("Client ki haan kisi version par nahi likhi.")
        blocks += [f"{a['name']}: {a['say']}" for a in assets if a["level"] == "block"]
        if st.handover_after_pay and bal is not None and bal > 0.5 and not inp.get("force"):
            blocks.append(f"Abhi {_rs(bal)} baaki: niyam ke hisaab se files poore paise ke baad (owner force kar sakti hain).")
        if bal is None and st.handover_after_pay and not inp.get("force"):
            blocks.append("Kaam ka daam hi nahi likha: pehle quote / bill.")
        asg = _j(j.assignment, {})
        a_txt = R.assignment_text(st.designer or st.studio, (c.business or c.name) if c else "", f"{j.title} ({j.number})",
                                  asg.get("rights", ""), asg.get("years"), asg.get("territory", ""),
                                  f"{_rs(q['total'])} (invoice ke anusaar)" if q["total"] is not None else "") if st.assign_copyright else {}
        cols = _kit_of(c)[0]["colors"] if c else {}
        return {**base, "version": x.n if x else None, "file_hash": x.file_hash if x else "",
                "files": _finals_plan(s, j, x) if x else [], "fonts": [a for a in assets if a.get("licence") in R.FONT_LICENCES],
                "assets": assets, "colors": {k: {"hex": h, "cmyk": R.hex_to_cmyk(h)} for k, h in cols.items()},
                "assignment": a_txt.get("text", ""), "assignment_blanks": a_txt.get("blanks", []), "balance": bal,
                "balance_text": _rs(bal), "tm": _j(j.tm, {}), "blocks": blocks, "_in": inp}
    if kind == "vendor":
        x = next((v for v in vs if v.status == "client_ok"), None)
        v = s.get(GraphicVendor, j.vendor_id) if j.vendor_id else None
        spec = _spec_of(s, j)
        blocks = []
        if not j.print_fmt:
            blocks.append("Yeh print ka kaam nahi (print format nahi chuna).")
        if v is None:
            blocks.append("Printer nahi chuna.")
        elif not v.phone and not v.email:
            blocks.append("Printer ka phone / email nahi.")
        if x is None:
            blocks.append("Client ki final haan nahi.")
        elif x.source == "upload":
            blocks += [i["text"] for i in _j(x.preflight, {}).get("issues", []) if i.get("level") == "block"]
        pj = _j(j.print_job, {})
        if not pj.get("qty"):
            blocks.append("Kitni copies? (print_job qty)")
        return {**base, "vendor": v.name if v else "", "vendor_phone": v.phone if v else "", "vendor_email": v.email if v else "",
                "version": x.n if x else None, "file_hash": x.file_hash if x else "", "spec": spec, "print_job": pj,
                "blocks": blocks, "_in": inp}
    if kind == "invoice":
        q = _quote(s, tenant, j)
        what = inp.get("what", "final")
        billed = sum(float(i.get("total") or 0) for i in _j(j.invoices, []))
        if q["total"] is None:
            amount = None
        elif what == "advance":
            amount = q["advance"]
        else:
            amount = round(q["total"] - billed, 2)
        upi, _ = _upi_of(tenant)
        return {**base, "what": what, "lines": q["lines"], "gst": q["gst"], "quote_total": q["total"], "billed": billed,
                "amount": amount, "amount_text": _rs(amount), "upi": upi, "sac": q["sac"], "tds_note": q["tds_note"],
                "msme": bool(st.udyam), "pay_days": st.pay_days, "gstin": st.gstin, "client_gstin": c.gstin if c else "",
                "_in": inp}
    if kind == "discount":
        q = _quote(s, tenant, j)
        return {**base, "amount": inp.get("amount"), "amount_text": _rs(inp.get("amount")), "reason": inp.get("reason", ""),
                "subtotal": q["subtotal"], "current_discount": j.discount, "_in": inp}
    if kind == "message":
        return {**base, "text": inp.get("text", ""), "_in": inp}
    raise GraphicError(f"card '{kind}' nahi pehchana.")


def _make_card(tenant: str, kind: str, job_ref: str, inp: dict, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        j = _job(s, tenant, job_ref) if job_ref else None
        show = _show(s, tenant, kind, j, inp)
        if show.get("blocks"):
            raise GraphicError(f"{CARD_TITLE[kind]} abhi nahi: " + "; ".join(show["blocks"][:3]))
        h = R.digest(show)
        old = s.scalars(select(GraphicCard).where(GraphicCard.tenant_id == tenant, GraphicCard.kind == kind,
                                                  GraphicCard.job_id == (j.id if j else ""), GraphicCard.status == "waiting")).all()
        for o in old:
            if o.hash == h:
                return {"card": _card_view(o), "status": "needs_tap", "existing": True,
                        "say": "Yahi card pehle se aapki haan ka intezaar kar raha hai."}
            o.status = "stale"
        c = GraphicCard(tenant_id=tenant, job_id=j.id if j else "", kind=kind, show=_dump(show), hash=h,
                        asked_by=actor_name(tenant, actor), conv=conv or (j.conv if j else ""))
        s.add(c)
        s.flush()
        v = _card_view(c)
        cv = c.conv
    say = f"{CARD_TITLE[kind]}: {v['show'].get('job', '')} aapki haan ka card bheja hai."
    _publish(tenant, "graphic_card", {"card": v, "say": say}, cv)
    return {"card": v, "status": "needs_tap", "say": say}


def card_view(tenant: str, card_id: str) -> dict:
    with session() as s:
        c = s.get(GraphicCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise GraphicError("Card nahi mila.")
        return _card_view(c)


def cards(tenant: str, status: str = "waiting") -> list[dict]:
    with session() as s:
        q = select(GraphicCard).where(GraphicCard.tenant_id == tenant)
        if status:
            q = q.where(GraphicCard.status == status)
        return [_card_view(c) for c in s.scalars(q.order_by(GraphicCard.created_at.desc())).all()][:100]


def card_challenge(tenant: str, card_id: str) -> dict:
    """approvekey's message format (kind 'graphic'): her phone signs this money card (discount) as it is NOW."""
    from .. import approvekey as ak
    c = card_view(tenant, card_id)
    if c["status"] != "waiting" or c["kind"] not in MONEY_CARDS:
        raise GraphicError("Yeh card ab baaki nahi hai.")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|graphic|{card_id}|{c['hash']}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="graphic", target=card_id, digest=c["hash"], message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    sh = c["show"]
    return {"challenge_id": chid, "message": msg, "show": {"title": f"{c['title']} {sh.get('job', '')}",
                                                           "amount": sh.get("amount_text", ""), "payee": sh.get("client", "")},
            "expires_at": exp.isoformat()}


def _verify_fingerprint(tenant: str, card_id: str, digest: str, proof: dict | None) -> None:
    from .. import approvekey as ak
    if not proof:
        raise GraphicError("fingerprint_needed")
    with session() as s:
        ak._settle(s, tenant)
        ok = ak._check(s, tenant, "graphic", card_id, proof, digest)
    if not ok:
        raise GraphicError("fingerprint_invalid")


def decide(tenant: str, card_id: str, yes: bool, card_hash: str = "", reason: str = "", proof: dict | None = None,
           by_tap: bool = False, conv: str = "") -> dict:
    """ONLY from the app's API (her tap). The card's hash must still match the state NOW; money cards need her fingerprint."""
    if not by_tap:
        raise GraphicError("Yeh sirf aapke tap se (app ka card).")
    with session() as s:
        c = s.get(GraphicCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise GraphicError("Card nahi mila.")
        if c.status != "waiting":
            return {"card": _card_view(c), "say": f"Yeh card pehle hi '{c.status}' hai."}
        j = s.get(GraphicJob, c.job_id) if c.job_id else None
        inp = _j(c.show, {}).get("_in", {})
        try:
            sh_now = _show(s, tenant, c.kind, j, dict(inp))
            now_hash = R.digest(sh_now) if not sh_now.get("blocks") else ""
        except GraphicError:
            now_hash = ""
        ch, kind = c.hash, c.kind
    bad = not card_hash or card_hash != ch or now_hash != ch
    if bad:
        if now_hash != ch:
            with _LOCK, session() as s:
                s.get(GraphicCard, card_id).status = "stale"
        raise GraphicError("Card ke baad kuch badal gaya; naya card dekhiye.")
    if yes and kind in MONEY_CARDS:
        from .. import approvekey as ak
        if ak.active_on(tenant):
            _verify_fingerprint(tenant, card_id, card_hash, proof)
    if not yes:
        with _LOCK, session() as s:
            c = s.get(GraphicCard, card_id)
            c.status, c.reason, c.decided_at = "rejected", R.clean(reason, 300), now()
            v = _card_view(c)
        return {"card": v, "say": f"{CARD_TITLE[kind]}: nahi."}
    fn = {"quote": _do_quote, "proof": _do_proof, "extra": _do_extra, "handover": _do_handover, "vendor": _do_vendor,
          "invoice": _do_invoice, "discount": _do_discount, "message": _do_message}[kind]
    out = fn(tenant, card_id, conv)
    with _LOCK, session() as s:
        c = s.get(GraphicCard, card_id)
        if c.status == "waiting":
            c.status, c.decided_at = "approved", now()
        c.result = _dump({k: v for k, v in out.items() if k in ("draft", "file_id", "say", "files")})
        out["card"] = _card_view(c)
    return out


def _card_ctx(card_id: str) -> tuple[dict, str]:
    with session() as s:
        c = s.get(GraphicCard, card_id)
        return _j(c.show, {}), c.job_id


def _do_quote(tenant: str, card_id: str, conv: str) -> dict:
    sh, jid = _card_ctx(card_id)
    pdf = quote_pdf(tenant, jid, final=True, valid_until=sh.get("valid_until", ""))
    with _LOCK, session() as s:
        j = s.get(GraphicJob, jid)
        st = _st(s, tenant)
        j.quote_ok = R.digest({k: v for k, v in sh.items() if k != "_in"})
        if j.status == "brief":
            j.status = "quoted"
        _log(j, "Quotation aapki haan se final", "Owner")
        num, studio = j.number, st.studio or st.designer
    f = _store(tenant, f"{num}_quotation.pdf", pdf, "application/pdf", conv, f"{num} quotation")
    text = (f"Namaste {sh.get('client')} ji, {studio or 'hamari'} taraf se '{sh.get('title')}' ka quotation {num}: kul "
            f"{sh.get('total_text')}, advance {sh.get('advance_text')}, {sh.get('rounds')} revision round shaamil"
            + (f", {sh['valid_until']} tak valid" if sh.get("valid_until") else "") + ". PDF saath hai; haan ho to bataiye.")
    return {"draft": _draft(sh.get("phone", ""), text, sh.get("email", ""), f"Quotation {num}", file_id=f.get("file_id", "")),
            "file_id": f.get("file_id", ""), "say": f"{num} quotation final; draft taiyaar, aap khud bhejiye (PDF saath)."}


def _do_proof(tenant: str, card_id: str, conv: str) -> dict:
    sh, jid = _card_ctx(card_id)
    files = []
    with _LOCK, session() as s:
        j = s.get(GraphicJob, jid)
        x = next(v for v in _versions(s, j) if v.n == sh["version"])
        x.status = "sent"
        _log(j, f"Proof v{x.n} client ko bhejne ki haan", "Owner")
        folder = _dir(tenant, j.id)
        names = list(_j(x.proofs, {}).values())
        num = j.number
    for n in names:
        p = folder / n
        if p.exists():
            f = _store(tenant, f"{num}-proof-v{sh['version']}-{n}", p.read_bytes(), "image/jpeg", conv, f"{num} proof v{sh['version']}")
            files.append(f.get("file_id", ""))
    left = sh.get("rounds_left", 0)
    text = (f"Namaste {sh.get('client')} ji, '{sh.get('title')}' ({num}) ka proof v{sh['version']} bhej rahi hoon. Badlav ho to "
            f"ek saath likh dijiye ({left} revision round baaki), ya 'final' likhiye. PROOF mark final file mein nahi hoga.")
    return {"draft": _draft(sh.get("phone", ""), text, sh.get("email", ""), f"Proof {num} v{sh['version']}", file_ids=files),
            "files": files, "say": f"{num} proof v{sh['version']} taiyaar; draft + photo aapki files mein, aap bhejiye."}


def _do_extra(tenant: str, card_id: str, conv: str) -> dict:
    sh, jid = _card_ctx(card_id)
    with _LOCK, session() as s:
        j = s.get(GraphicJob, jid)
        j.extra_rounds += 1
        _log(j, f"Extra round {_rs(j.extra_round_price)} aapki haan se", "Owner")
        num = j.number
    text = (f"Namaste {sh.get('client')} ji, quote ke {sh.get('included')} revision round poore ho gaye hain. Agla round extra "
            f"{sh.get('amount_text')} ka hoga (bill mein judega). Theek ho to badlav bhejiye.")
    return {"draft": _draft(sh.get("phone", ""), text, sh.get("email", ""), f"{num} extra revision"),
            "say": f"{num}: ek extra round khula ({sh.get('amount_text')} bill mein); client ko batane ka draft taiyaar."}


def _readme(sh: dict) -> str:
    lines = [f"{sh.get('job')} - {sh.get('title')}", f"Client: {sh.get('client')}", "", "FILES"]
    lines += [f"- {f['name']}: {f['what']}" for f in sh.get("files", [])]
    lines += ["", "COLOURS (HEX / CMYK - CMYK sirf shuruaati andaaza; printer ka proof dekhiye)"]
    for k, v in (sh.get("colors") or {}).items():
        c, m, y, kk = v["cmyk"]
        lines.append(f"- {k}: {v['hex']}  C{c} M{m} Y{y} K{kk}")
    lines += ["", "FONTS / PICTURES"]
    for a in sh.get("assets", []):
        lines.append(f"- {a.get('name')}: {a.get('label')} - {a.get('say')}")
    if not sh.get("assets"):
        lines.append("- (koi list nahi)")
    lines += ["", "Hoola se banaya handover. Font files sirf wahi jinka licence share karne deta hai (OFL / Apache)."]
    return "\n".join(lines)


def _do_handover(tenant: str, card_id: str, conv: str) -> dict:
    from ..brand import render as RN
    from ..brand import rules as BR
    sh, jid = _card_ctx(card_id)
    with session() as s:
        j = s.get(GraphicJob, jid)
        x = next(v for v in _versions(s, j) if v.n == sh["version"])
        c = s.get(GraphicClient, j.client_id)
        kit, logo_uri, _ = _kit_of(c)
        folder = _dir(tenant, j.id)
        num, source, sizes = j.number, x.source, _j(x.sizes, [])
        content, layout, fname = _j(x.content, {}), x.layout, x.file_name
    pack: list[tuple[str, bytes]] = []
    if source == "upload":
        pack.append((sh["files"][0]["name"], (folder / fname).read_bytes()))
    else:
        page_d = {**content, "layout": layout, "kind": "poster", "festival": {}, "show_contact": True}
        kit2 = {**kit, "colors": {**kit["colors"], **(content.get("colors") or {})}}
        seed = int(re.sub(r"\D", "", num) or 7)
        jobs_ = []
        for sz in sizes:
            html = RN.page(page_d, kit2, sz, proof=False, logo=logo_uri, seed=seed)
            jobs_.append({"html": html, "size": sz, "out": "pdf" if BR.SIZES.get(sz, {}).get("print") else "png"})
        for sz, r in zip(sizes, _render(jobs_)):
            ext = "pdf" if BR.SIZES.get(sz, {}).get("print") else "png"
            pack.append((f"{num}-{sz}.{ext}", r["data"]))
    pack.append(("README.txt", _readme(sh).encode()))
    if sh.get("assignment"):
        pack.append(("copyright-assignment-DRAFT.pdf", _pdf("Copyright assignment (DRAFT)", [("p", ln) for ln in
                                                                                             sh["assignment"].split("\n") if ln],
                                                             "DRAFT")))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in pack:
            z.writestr(n, d)
    data = buf.getvalue()
    (folder / f"{num}-handover.zip").write_bytes(data)
    f = _store(tenant, f"{num}-handover.zip", data, "application/zip", conv, f"{num} final files")
    with _LOCK, session() as s:
        j = s.get(GraphicJob, jid)
        x = next(v for v in _versions(s, j) if v.n == sh["version"])
        x.status = "final"
        j.status = "delivered"
        j.handover = _dump({"at": now().isoformat(), "file_id": f.get("file_id", ""), "files": [n for n, _ in pack],
                            "forced": bool(sh.get("_in", {}).get("force"))})
        _log(j, "Final files ka pack aapki haan se taiyaar", "Owner")
    text = (f"Namaste {sh.get('client')} ji, '{sh.get('title')}' ({num}) ki final files ka pack bhej rahi hoon: design files, "
            "rang ke code aur font ki jaankari" + (", aur copyright saunpne ka likhit draft (dono ke hastakshar ke liye)" if sh.get("assignment") else "")
            + ". Shukriya!")
    return {"draft": _draft(sh.get("phone", ""), text, sh.get("email", ""), f"{num} final files", file_id=f.get("file_id", "")),
            "file_id": f.get("file_id", ""), "files": [n for n, _ in pack],
            "say": f"{num}: final pack ({len(pack)} files) aapki files mein; draft taiyaar, aap bhejiye."}


def _do_vendor(tenant: str, card_id: str, conv: str) -> dict:
    sh, jid = _card_ctx(card_id)
    from ..brand import render as RN
    with session() as s:
        j = s.get(GraphicJob, jid)
        x = next(v for v in _versions(s, j) if v.n == sh["version"])
        c = s.get(GraphicClient, j.client_id)
        kit, logo_uri, _ = _kit_of(c)
        folder = _dir(tenant, j.id)
        num, source, fname, fmt = j.number, x.source, x.file_name, j.print_fmt
        content, layout = _j(x.content, {}), x.layout
    if source == "upload":
        data, name, mime = (folder / fname).read_bytes(), f"{num}-print.{fname.rsplit('.', 1)[-1]}", x.file_mime
    else:
        page_d = {**content, "layout": layout, "kind": "poster", "festival": {}, "show_contact": True}
        r = _render([{"html": RN.page(page_d, kit, fmt, proof=False, logo=logo_uri), "size": fmt, "out": "pdf"}])[0]
        data, name, mime = r["data"], f"{num}-print.pdf", "application/pdf"
    f = _store(tenant, name, data, mime or "application/octet-stream", conv, f"{num} print file")
    sp, pj = sh.get("spec") or {}, sh.get("print_job") or {}
    mm = sp.get("mm") or ["?", "?"]
    text = (f"Namaste {sh.get('vendor')} ji, print order {num}: {pj.get('qty')} copies, size {mm[0]} x {mm[1]} mm "
            f"(bleed {sp.get('bleed', '?')} mm)" + (f", kaagaz {pj['stock']}" if pj.get("stock") else "")
            + (f", finish {pj['finish']}" if pj.get("finish") else "") + (f", {pj['sides']}" if pj.get("sides") else "")
            + ". File saath hai. Chhapne se pehle ek proof / rate bata dijiye.")
    with _LOCK, session() as s:
        j = s.get(GraphicJob, jid)
        _log(j, f"Print order {sh.get('vendor')} ko aapki haan se", "Owner")
    return {"draft": _draft(sh.get("vendor_phone", ""), text, sh.get("vendor_email", ""), f"Print order {num}",
                            file_id=f.get("file_id", "")),
            "file_id": f.get("file_id", ""), "say": f"{num}: print file + printer ka draft taiyaar; aap bhejiye. Paise aap khud dengi."}


def _do_invoice(tenant: str, card_id: str, conv: str) -> dict:
    sh, jid = _card_ctx(card_id)
    d = today(tenant)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        st.inv_seq += 1
        no = f"INV/{_fy(d)}/{st.inv_seq:04d}"
        j = s.get(GraphicJob, jid)
        inv = _j(j.invoices, [])
        inv.append({"number": no, "what": sh["what"], "total": sh["amount"], "day": d.isoformat()})
        j.invoices = _dump(inv)
        _log(j, f"Invoice {no} {_rs(sh['amount'])} aapki haan se", "Owner")
        num = j.number
    pdf = invoice_pdf(tenant, jid, no, sh)
    f = _store(tenant, f"{no.replace('/', '-')}.pdf", pdf, "application/pdf", conv, f"Invoice {no}")
    upi = _upi(tenant, float(sh["amount"] or 0), f"{no} {num}")
    text = (f"Namaste {sh.get('client')} ji, '{sh.get('title')}' ({num}) ka {'advance ' if sh['what'] == 'advance' else ''}invoice "
            f"{no}: {sh.get('amount_text')}. PDF saath hai." + (f" UPI se: {upi}" if upi else "") +
            (f" {sh.get('pay_days')} din mein bhugtaan kripya." if sh.get("pay_days") else ""))
    with _LOCK, session() as s:
        j = s.get(GraphicJob, jid)
        inv = _j(j.invoices, [])
        inv[-1]["file_id"] = f.get("file_id", "")
        j.invoices = _dump(inv)
    return {"draft": _draft(sh.get("phone", ""), text, sh.get("email", ""), f"Invoice {no}", upi=upi, file_id=f.get("file_id", "")),
            "file_id": f.get("file_id", ""), "invoice": no,
            "say": f"Invoice {no} bana; draft + UPI link (aapke UPI ID ka) taiyaar: aap bhejiye. Hoola paise nahi leta."}


def _do_discount(tenant: str, card_id: str, conv: str) -> dict:
    sh, jid = _card_ctx(card_id)
    with _LOCK, session() as s:
        j = s.get(GraphicJob, jid)
        j.discount = float(sh["amount"] or 0)
        _log(j, f"Discount {_rs(j.discount)}: {sh.get('reason')}", "Owner")
        num = j.number
    return {"say": f"{num}: {sh.get('amount_text')} ka discount laga (fingerprint se aapki haan)."}


def _do_message(tenant: str, card_id: str, conv: str) -> dict:
    sh, jid = _card_ctx(card_id)
    return {"draft": _draft(sh.get("phone", ""), sh.get("text", ""), sh.get("email", ""), sh.get("title", "")),
            "say": "Message draft taiyaar: aap khud bhejiye."}


# ---------------------------------------------------------------- card requests (never decide)
def quote_request(tenant: str, job: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        j = _job(s, tenant, job)
        q = _quote(s, tenant, j)
        c = s.get(GraphicClient, j.client_id)
        if q["missing"]:
            raise GraphicError(f"{j.number}: daam nahi likha ({', '.join(q['missing'])}): aap batayiye, Hoola daam nahi lagata.")
        if c and c.no_messages:
            raise GraphicError("Is client ne message mana kiya hai.")
    return _make_card(tenant, "quote", job, {}, actor, conv)


def proof_send(tenant: str, job: str, version: int | None = None, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        j = _job(s, tenant, job)
        vs = _versions(s, j)
        if not vs:
            raise GraphicError(f"{j.number}: abhi koi proof nahi.")
        x = next((v for v in vs if v.n == version), None) if version else vs[-1]
        if x is None:
            raise GraphicError("Woh version nahi mila.")
        if x.status in ("old",):
            raise GraphicError(f"v{x.n} purana hai; naya version bhejiye.")
        n = x.n
    return _make_card(tenant, "proof", job, {"version": n}, actor, conv)


def extra_request(tenant: str, job: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        j = _job(s, tenant, job)
        if not j.extra_round_price:
            raise GraphicError(f"{j.number}: extra round ka daam nahi likha (aap batayiye: extra_round_price).")
    return _make_card(tenant, "extra", job, {"n": "next"}, actor, conv)


def handover_request(tenant: str, job: str, force: bool = False, actor: str = "owner", conv: str = "") -> dict:
    if force:
        _owner_only(actor)
    return _make_card(tenant, "handover", job, {"force": bool(force)}, actor, conv)


def vendor_request(tenant: str, job: str, vendor: str = "", actor: str = "owner", conv: str = "") -> dict:
    if vendor:
        with _LOCK, session() as s:
            j = _job(s, tenant, job)
            j.vendor_id = _vendor(s, tenant, vendor).id
    return _make_card(tenant, "vendor", job, {}, actor, conv)


def invoice_request(tenant: str, job: str, what: str = "final", actor: str = "owner", conv: str = "") -> dict:
    what = what if what in ("advance", "final") else "final"
    with session() as s:
        j = _job(s, tenant, job)
        sh = _show(s, tenant, "invoice", j, {"what": what})
        if sh["amount"] is None:
            raise GraphicError(f"{j.number}: daam nahi likha; pehle quote lines.")
        if sh["amount"] <= 0:
            raise GraphicError(f"{j.number}: poora bill ho chuka.")
        if what == "advance" and any(i.get("what") == "advance" for i in _j(j.invoices, [])):
            raise GraphicError("Advance invoice pehle hi ban chuka.")
    return _make_card(tenant, "invoice", job, {"what": what}, actor, conv)


def discount_request(tenant: str, job: str, amount=None, pct=None, reason: str = "", actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        j = _job(s, tenant, job)
        q = _quote(s, tenant, j)
    a = _num(amount)
    if a is None and pct is not None:
        p = _num(pct)
        if p is None or not 0 < p <= 100:
            raise GraphicError("discount % 1-100.")
        a = round(q["subtotal"] * p / 100, 2)
    if not a or a <= 0:
        raise GraphicError("Kitna discount? amount ya pct.")
    if a > q["subtotal"]:
        raise GraphicError("Discount kul daam se zyada nahi ho sakta.")
    return _make_card(tenant, "discount", job, {"amount": round(a, 2), "reason": R.clean(reason, 200)}, actor, conv)


def message_request(tenant: str, job: str, text: str, actor: str = "owner", conv: str = "") -> dict:
    t = R.clean(text, 1500)
    if not t:
        raise GraphicError("Message kya likhna hai?")
    if _secret_text(text):
        raise GraphicError("OTP / PIN / password jaisi baat message mein nahi.")
    if re.search(r"\[[^\]]{1,40}\]", t):
        raise GraphicError("Message mein [khaali jagah] bachi hai: pehle bhariye.")
    with session() as s:
        j = _job(s, tenant, job)
        c = s.get(GraphicClient, j.client_id)
        if c and c.no_messages:
            raise GraphicError("Is client ne message mana kiya hai.")
    return _make_card(tenant, "message", job, {"text": t}, actor, conv)


# ---------------------------------------------------------------- her records (owner)
def accepted(tenant: str, job: str, evidence: str = "", actor: str = "owner") -> dict:
    ev = R.clean(evidence, 600)
    if not ev:
        raise GraphicError("Client ne quote maana: unka message / baat likhiye.")
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        if not j.quote_ok:
            raise GraphicError(f"{j.number}: quote abhi gaya hi nahi (quote card par haan).")
        j.accepted = _dump({"at": now().isoformat(), "evidence": ev})
        if j.status in ("brief", "quoted"):
            j.status = "accepted"
        _log(j, "Client ne quote maana", actor_name(tenant, actor))
        jn = j.number
    return {"say": f"{jn}: client ne quote maana, kaam shuru."}


def paid(tenant: str, job: str, amount, mode: str = "upi", ref: str = "", day: str = "", actor: str = "owner") -> dict:
    _owner_only(actor)
    a = _num(amount)
    if not a or a <= 0:
        raise GraphicError("Kitne paise mile?")
    d = _date(day) or today(tenant)
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        pm = _j(j.payments, [])
        pm.append({"amount": round(a, 2), "mode": (mode or "upi")[:10], "ref": R.clean(ref, 40)[-6:], "day": d.isoformat()})
        j.payments = _dump(pm)
        _log(j, f"{_rs(a)} mile ({mode})", "Owner")
        q = _quote(s, tenant, j)
        bal = None if q["total"] is None else round(q["total"] - _paid(j), 2)
        jn = j.number
    return {"paid": round(a, 2), "balance": bal, "say": f"{jn}: {_rs(a)} likh liya. Baaki {_rs(bal)}."}


def cancel(tenant: str, job: str, reason: str = "", actor: str = "owner") -> dict:
    _owner_only(actor)
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        j.status = "cancelled"
        for c in s.scalars(select(GraphicCard).where(GraphicCard.job_id == j.id, GraphicCard.status == "waiting")).all():
            c.status = "stale"
        _log(j, f"Radd: {R.clean(reason, 200)}", "Owner")
        jn = j.number
    return {"say": f"{jn} radd. Advance lautana ho to aap khud bhejiye (Hoola paise nahi bhejta)."}


def done(tenant: str, job: str, actor: str = "owner") -> dict:
    _owner_only(actor)
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        j.status = "done"
        _log(j, "Kaam poora", "Owner")
        jn = j.number
    return {"say": f"{jn} poora."}


def set_assignment(tenant: str, job: str, rights: str = "", years=None, territory: str = "", actor: str = "owner") -> dict:
    _owner_only(actor)
    y = _int(years) if years not in (None, "") else None
    with _LOCK, session() as s:
        j = _job(s, tenant, job)
        j.assignment = _dump({"rights": R.clean(rights, 300), "years": y, "territory": R.clean(territory, 80)})
        jn = j.number
    return {"say": f"{jn}: copyright assignment ki shartein save."}


def forget_client(tenant: str, client: str, actor: str = "owner") -> dict:
    """DPDP: a client's personal details erased once their jobs are finished; amounts / invoice numbers stay for her accounts."""
    _owner_only(actor)
    with _LOCK, session() as s:
        c = _client(s, tenant, client)
        open_ = s.scalars(select(GraphicJob).where(GraphicJob.client_id == c.id,
                                                   GraphicJob.status.not_in(("done", "cancelled", "delivered")))).all()
        if open_:
            raise GraphicError(f"{len(open_)} kaam abhi khule hain ({', '.join(j.number for j in open_[:3])}): pehle poore / radd kijiye.")
        c.name, c.phone, c.email, c.notes, c.contact = f"Purana client {c.number}", "", "", "", "{}"
        c.forgotten = True
        for j in s.scalars(select(GraphicJob).where(GraphicJob.client_id == c.id)).all():
            j.brief, j.feedback = "[hataya - DPDP]", "[]"
            j.client_ok = _dump({k: v for k, v in _j(j.client_ok, {}).items() if k != "evidence"})
            j.accepted = "{}"
        num = c.number
    return {"say": f"{num}: client ki personal details hata di; kaam ke number aur hisaab rahe."}


# ---------------------------------------------------------------- PDFs
def _pdf(title: str, blocks: list[tuple], watermark: str = "") -> bytes:
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from .. import indicpdf
    pdf = indicpdf.blocks_pdf(title, blocks, watermark)
    if pdf:
        return pdf
    ss = getSampleStyleSheet()
    small = ss["BodyText"].clone("small", fontSize=8.5, leading=10.5)

    def txt(t: str) -> str:
        return indicpdf.rl_markup(escape(str(t or "").replace("₹", "Rs. ")))
    story: list = []
    for b in blocks:
        if b[0] == "h":
            story.append(Paragraph(txt(b[1]), ss["Heading2"]))
        elif b[0] == "h1":
            story.append(Paragraph(txt(b[1]), ss["Title"]))
        elif b[0] == "p":
            story.append(Paragraph(txt(b[1]), ss["BodyText"]))
        elif b[0] == "table":
            rows = [[Paragraph(txt(c), small) for c in r] for r in b[1]]
            t = Table(rows, colWidths=b[2] if len(b) > 2 else None, repeatRows=1)
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(t)
        story.append(Spacer(1, 6))
    bio = io.BytesIO()

    def mark(c, _d):
        if watermark:
            c.saveState()
            c.setFont("Helvetica-Bold", 46)
            c.setFillColor(colors.Color(0.85, 0.2, 0.2, alpha=0.18))
            c.translate(300, 420)
            c.rotate(35)
            c.drawCentredString(0, 0, watermark)
            c.restoreState()
    doc = SimpleDocTemplate(bio, pagesize=A4, title=title, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    doc.build(story, onFirstPage=mark, onLaterPages=mark)
    return bio.getvalue()


def _head(st: GraphicSettings, title: str) -> list[tuple]:
    who = " · ".join(x for x in (st.studio or st.designer, f"GSTIN {st.gstin}" if st.gstin else "",
                                 f"Udyam {st.udyam}" if st.udyam else "") if x)
    contact = " · ".join(x for x in (st.address, st.phone, st.email) if x)
    out = [("h1", title)]
    if who:
        out.append(("p", who))
    if contact:
        out.append(("p", contact))
    return out


def _money_rows(q: dict) -> list[tuple]:
    rows = [["Item", "Qty", "Rate", "Amount"]]
    for ln in q["lines"]:
        rows.append([ln["name"], f"{float(ln.get('qty') or 1):g}", _pdf_rs(ln.get("rate")), _pdf_rs(ln.get("amount"))])
    t = [["", "Amount"], ["Subtotal", _pdf_rs(q["subtotal"])]]
    if q["discount"]:
        t.append(["Discount", "- " + _pdf_rs(q["discount"])])
    for r in q["gst"].get("rows", []):
        t.append([r["name"], _pdf_rs(r["amount"])])
    if q["gst"].get("note"):
        t.append([q["gst"]["note"], ""])
    t.append(["TOTAL", _pdf_rs(q["total"])])
    return [("table", rows, [260, 50, 90, 100]), ("table", t, [350, 150])]


def quote_pdf(tenant: str, job: str, final: bool = False, valid_until: str = "") -> bytes:
    with session() as s:
        j = _job(s, tenant, job)
        st = _st(s, tenant)
        c = s.get(GraphicClient, j.client_id)
        q = _quote(s, tenant, j)
        blocks = _head(st, f"Quotation {j.number}") + [
            ("p", f"Client: {c.business or c.name if c else ''}" + (f" · GSTIN {c.gstin}" if c and c.gstin else "")),
            ("p", f"Kaam: {j.title} ({R.KINDS.get(j.kind, {}).get('label', j.kind)})" + (f" · Due {j.due}" if j.due else "")),
        ] + _money_rows(q) + [
            ("p", f"SAC {q['sac']}" if q["sac"] else q["gst_note"]),
            ("p", f"Advance {j.advance_pct:g}%: {_pdf_rs(q['advance'])}. Revision rounds shaamil: {j.rounds_included}"
                  + (f"; har extra round {_pdf_rs(j.extra_round_price)}." if j.extra_round_price else ".")),
            ("p", "Copyright: poore bhugtaan ke baad likhit assignment (Copyright Act 1957 s.19) se client ko." if st.assign_copyright
             else "Copyright designer ke paas rahega; client ko upyog ka licence."),
            ("p", "Fonts / stock photos ke licence alag; final files ke saath jaankari di jayegi."),
        ]
        if valid_until:
            blocks.append(("p", f"Valid till {valid_until}."))
        if st.terms:
            blocks.append(("p", st.terms))
    return _pdf(f"Quotation {job}", blocks, "" if final else "DRAFT")


def invoice_pdf(tenant: str, job: str, number: str, sh: dict) -> bytes:
    with session() as s:
        j = _job(s, tenant, job)
        st = _st(s, tenant)
        c = s.get(GraphicClient, j.client_id)
        q = _quote(s, tenant, j)
        title = "Tax Invoice" if st.gstin else "Bill of Supply / Invoice"
        blocks = _head(st, f"{title} {number}") + [
            ("p", f"Date: {today(tenant).isoformat()} · Job {j.number}: {j.title}"),
            ("p", f"Bill to: {c.business or c.name if c else ''}" + (f" · GSTIN {c.gstin}" if c and c.gstin else "")
             + (f" · {c.state}" if c and c.state else "")),
        ] + _money_rows(q)
        if sh.get("what") == "advance":
            blocks.append(("p", f"Is invoice ki rakam (advance {j.advance_pct:g}%): {_pdf_rs(sh.get('amount'))}"))
        else:
            blocks.append(("p", f"Pehle bill ho chuka: {_pdf_rs(sh.get('billed'))} · Is invoice ki rakam: {_pdf_rs(sh.get('amount'))}"))
        if q["total_words"]:
            blocks.append(("p", q["total_words"]))
        if q["sac"]:
            blocks.append(("p", f"SAC {q['sac']} (design services)"))
        if st.udyam:
            blocks.append(("p", f"MSME (Udyam {st.udyam}): MSMED Act s.15 ke anusaar 45 din ke andar bhugtaan."))
        if sh.get("upi"):
            blocks.append(("p", f"UPI: {sh['upi']}"))
        blocks.append(("p", q["tds_note"]))
    return _pdf(f"Invoice {number}", blocks)


# ---------------------------------------------------------------- files
def file_path(tenant: str, job: str, name: str) -> tuple[Path, str]:
    if not re.fullmatch(r"[\w.\-]{1,120}", name or "") or ".." in name:
        raise GraphicError("File nahi mili.")
    with session() as s:
        j = _job(s, tenant, job)
        p = _dir(tenant, j.id) / name
    if not p.exists():
        raise GraphicError("File nahi mili.")
    ext = p.suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".pdf": "application/pdf",
            ".zip": "application/zip", ".tif": "image/tiff", ".tiff": "image/tiff"}.get(ext, "application/octet-stream")
    return p, mime


# ---------------------------------------------------------------- day / overview / worker
def day(tenant: str) -> dict:
    t = today(tenant)
    with session() as s:
        rows = s.scalars(select(GraphicJob).where(GraphicJob.tenant_id == tenant,
                                                  GraphicJob.status.not_in(("done", "cancelled")))).all()
        due_today, late, soon, feedback_wait, unpaid, waiting_client = [], [], [], [], [], []
        for j in rows:
            v = _job_view(s, j, False)
            d = _date(j.due)
            if d and j.status not in ("delivered",):
                if d < t:
                    late.append(v)
                elif d == t:
                    due_today.append(v)
                elif d <= t + timedelta(days=2):
                    soon.append(v)
            if j.pending_feedback:
                feedback_wait.append(v)
            vs = _versions(s, j)
            if vs and vs[-1].status == "sent" and not j.pending_feedback:
                waiting_client.append(v)
            q = _quote(s, tenant, j)
            if j.status == "delivered" and q["total"] is not None and q["total"] - _paid(j) > 0.5:
                unpaid.append({**v, "balance": round(q["total"] - _paid(j), 2)})
        waiting = len(cards(tenant))
    bits = []
    if late:
        bits.append(f"{len(late)} kaam due date se late ({', '.join(x['number'] for x in late[:3])})")
    if due_today:
        bits.append(f"aaj due: {', '.join(x['number'] for x in due_today[:3])}")
    if feedback_wait:
        bits.append(f"{len(feedback_wait)} par client ka feedback aaya, naya version baaki")
    if waiting_client:
        bits.append(f"{len(waiting_client)} proof client ke jawab ka intezaar")
    if unpaid:
        bits.append(f"{len(unpaid)} kaam ki files de di, paise baaki")
    if waiting:
        bits.append(f"{waiting} card aapki haan ka intezaar")
    say = ("Design desk: " + "; ".join(bits) + ".") if bits else "Design desk ka aaj sab theek."
    return {"say": say, "late": late, "today": due_today, "soon": soon, "feedback": feedback_wait,
            "waiting_client": waiting_client, "unpaid": unpaid, "waiting": waiting}


def overview(tenant: str) -> dict:
    return {"day": day(tenant), "settings": settings(tenant), "clients": clients(tenant), "jobs": jobs(tenant, "open"),
            "vendors": vendors(tenant), "cards": cards(tenant)}


def _once(s, tenant: str, key: str) -> bool:
    k = f"{tenant}:{key}"[:200]
    if s.get(GraphicAlert, k) is not None:
        return False
    s.add(GraphicAlert(key=k, tenant_id=tenant))
    return True


def _tenants() -> list[str]:
    with session() as s:
        return sorted(set(s.scalars(select(GraphicJob.tenant_id)).all()) | set(s.scalars(select(GraphicSettings.tenant_id)).all()))


def tick(when: datetime | None = None) -> dict:
    """Worker, every minute: due tomorrow / overdue (once each), a proof sent 3 days ago with no reply (follow-up draft offer),
    invoice unpaid after her pay days (and 45 days for MSME), morning note at her time (only when there is something)."""
    n = _aware(when) or now()
    out = {"alerts": 0, "morning": 0}
    for tenant in _tenants():
        try:
            loc = n.astimezone(_tz(tenant))
            on = loc.date()
            alerts = []
            with _LOCK, session() as s:
                st = _st(s, tenant)
                for j in s.scalars(select(GraphicJob).where(GraphicJob.tenant_id == tenant,
                                                            GraphicJob.status.not_in(("done", "cancelled")))).all():
                    d = _date(j.due)
                    if d and j.status != "delivered":
                        if d == on + timedelta(days=1) and _once(s, tenant, f"due1:{j.id}:{d}"):
                            alerts.append({"kind": "due", "job": j.number, "say": f"Kal {j.number} '{j.title}' ki due date hai."})
                        elif d < on and _once(s, tenant, f"late:{j.id}:{d}"):
                            alerts.append({"kind": "late", "job": j.number,
                                           "say": f"{j.number} due date ({d:%d %b}) nikal gayi: client ko nayi tareekh ka message card banau?"})
                    vs = _versions(s, j)
                    if vs and vs[-1].status == "sent" and not j.pending_feedback:
                        sent_at = _aware(vs[-1].created_at)
                        if sent_at and n - sent_at > timedelta(days=3) and _once(s, tenant, f"nudge:{vs[-1].id}"):
                            alerts.append({"kind": "nudge", "job": j.number,
                                           "say": f"{j.number} proof v{vs[-1].n} ko 3 din se jawab nahi: yaad dilane ka message card banau?"})
                    for inv in _j(j.invoices, []):
                        d0 = _date(inv.get("day"))
                        if not d0:
                            continue
                        lim = 45 if st.udyam else (st.pay_days or 15)
                        if (on - d0).days >= lim and _paid(j) + 0.5 < sum(float(i.get("total") or 0) for i in _j(j.invoices, [])) \
                                and _once(s, tenant, f"unpaid:{j.id}:{inv.get('number')}"):
                            alerts.append({"kind": "unpaid", "job": j.number,
                                           "say": f"Invoice {inv.get('number')} ({j.number}) ko {lim} din ho gaye, paise poore nahi aaye."
                                                  + (" MSME: 45 din ki seema." if st.udyam else "")})
            for a in alerts:
                _publish(tenant, "graphic_alert", a)
                out["alerts"] += 1
            with session() as s:
                r = s.get(GraphicSettings, tenant)
                due_m = False
                if r is not None and r.last_morning != on.isoformat():
                    try:
                        hh, mm = (int(z) for z in (r.morning_time or "09:30").split(":"))
                    except ValueError:
                        hh, mm = 9, 30
                    due_m = (loc.hour, loc.minute) >= (hh, mm)
                    if due_m:
                        r.last_morning = on.isoformat()
            if due_m:
                d = day(tenant)
                if d["say"] != "Design desk ka aaj sab theek.":
                    _publish(tenant, "graphic_day", {"say": d["say"], "late": len(d["late"]), "today": len(d["today"]),
                                                     "waiting": d["waiting"]})
                    out["morning"] += 1
        except Exception:
            log.exception("graphic tick failed for %s", tenant)
    return out
