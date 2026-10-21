"""v0.75 Pehchaan Locker: the owner's (and her family's) identity numbers - Aadhaar, PAN, voter ID, driving licence,
passport, ration card, ABHA, UAN, GSTIN... - kept encrypted, so Hoola can fill government / KYC forms like a Seva
Kendra operator does.

How it stays safe:
  * stored encrypted (Fernet: SECRET_KEY, else a 0600 key file); the app shows them masked (XXXX XXXX 1234), the full
    number only when the owner taps "dikhao";
  * the AI model never sees a full number: whatever she says or types is captured here first and replaced by a short
    reference like {id:ab12cd34} with the masked number next to it; the Computer Operator turns the reference back into
    the real number only inside the form box (official government sites directly, any other site after her tap);
  * OTP, PIN, CVV, card numbers and passwords are NOT identity numbers: Hoola still never takes those (she types them).
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

KINDS = {
    "aadhaar": "Aadhaar", "pan": "PAN", "voter": "Voter ID (EPIC)", "dl": "Driving licence", "passport": "Passport",
    "ration": "Ration card", "abha": "ABHA (health ID)", "uan": "UAN (PF)", "gstin": "GSTIN", "vehicle": "Vehicle number",
    "other": "Other ID",
}
PEOPLE = {   # words -> who it belongs to
    "self": ("mera", "meri", "mere", "my", "mine", "apna", "apni", "khud"),
    "maa": ("maa", "mummy", "mumma", "mother", "mom", "aai", "amma"),
    "papa": ("papa", "pappa", "father", "dad", "pitaji", "baba", "abba", "daddy"),
    "pati": ("pati", "husband", "hubby"),
    "patni": ("patni", "wife", "biwi"),
    "beta": ("beta", "son", "bete"),
    "beti": ("beti", "daughter"),
    "bhai": ("bhai", "bhaiya", "brother", "dada"),
    "behen": ("behen", "bahan", "didi", "sister", "tai"),
    "dada": ("dadaji", "grandfather", "nanaji", "ajoba"),
    "dadi": ("dadiji", "grandmother", "naniji", "aaji"),
}
PERSON_LABEL = {"self": "Aap", "maa": "Maa", "papa": "Papa", "pati": "Pati", "patni": "Patni", "beta": "Beta",
                "beti": "Beti", "bhai": "Bhai", "behen": "Behen", "dada": "Dada / Nana", "dadi": "Dadi / Nani"}

REF = re.compile(r"\{id:([a-z0-9]{6,16})\}")
AADHAAR = re.compile(r"(?<!\d)([2-9]\d{3})[ -]?(\d{4})[ -]?(\d{4})(?!\d)")
VID = re.compile(r"(?<!\d)(\d{4})[ -]?(\d{4})[ -]?(\d{4})[ -]?(\d{4})(?!\d)")         # Aadhaar Virtual ID (16 digits)
PAN = re.compile(r"\b([A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z])\b")
PAN_LOOSE = re.compile(r"\b([A-Za-z]{3}[ABCFGHLJPTabcfghljpt][A-Za-z]\d{4}[A-Za-z])\b")
EPIC = re.compile(r"\b([A-Z]{3}\d{7})\b")
GSTIN = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b")


class IdRecord(Base):
    __tablename__ = "id_vault"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("idv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ref: Mapped[str] = mapped_column(String(16), index=True)            # {id:<ref>}
    person: Mapped[str] = mapped_column(String(40), default="self")
    kind: Mapped[str] = mapped_column(String(16), default="other")
    sealed: Mapped[str] = mapped_column(Text)
    masked: Mapped[str] = mapped_column(String(40), default="")
    digest: Mapped[str] = mapped_column(String(64), index=True)          # sha256(tenant + value): same number = same row
    note: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VaultError(Exception):
    pass


# ----------------------------------------------------------------------------- crypto
_F: dict[str, Any] = {}


def _fernet():
    from cryptography.fernet import Fernet
    from .config import get_settings
    st = get_settings()
    key_src = st.secret_key
    if key_src:
        k = base64.urlsafe_b64encode(hashlib.sha256(("idvault:" + key_src).encode()).digest())
    else:
        p = Path("data") / "id_vault.key"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(Fernet.generate_key())
            try:
                os.chmod(p, 0o600)
            except OSError:
                pass
        k = p.read_bytes().strip()
    if _F.get("k") != k:
        _F.update(k=k, f=Fernet(k))
    return _F["f"]


def _seal(v: str) -> str:
    return _fernet().encrypt(v.encode()).decode()


def _open(s: str) -> str:
    return _fernet().decrypt(s.encode()).decode()


# ----------------------------------------------------------------------------- numbers
def verhoeff_ok(num: str) -> bool:
    from .pii import verhoeff_ok as v
    return v(num)


def normalize(kind: str, value: str) -> str:
    v = (value or "").strip()
    if kind in ("aadhaar", "abha", "uan"):
        return re.sub(r"\D", "", v)
    return re.sub(r"\s+", "", v).upper()


def validate(kind: str, v: str) -> str:
    """'' when fine, else why not."""
    if kind == "aadhaar":
        if not re.fullmatch(r"[2-9]\d{11}", v) or not verhoeff_ok(v):
            return "Yeh sahi Aadhaar number nahi lagta (12 ank, aakhri ank check se mel nahi khata)."
    elif kind == "pan" and not re.fullmatch(r"[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]", v):
        return "PAN 10 akshar ka hota hai, jaise ABCPE1234F."
    elif kind == "gstin" and not GSTIN.fullmatch(v):
        return "GSTIN 15 akshar ka hota hai."
    elif kind == "uan" and not re.fullmatch(r"\d{12}", v):
        return "UAN 12 ank ka hota hai."
    elif kind == "abha" and not re.fullmatch(r"\d{14}", v):
        return "ABHA number 14 ank ka hota hai."
    elif not v or len(v) > 40:
        return "Number khaali ya bahut lamba hai."
    return ""


def mask(kind: str, v: str) -> str:
    if kind == "aadhaar":
        return f"XXXX XXXX {v[-4:]}"
    if kind == "pan":
        return f"{v[:3]}XX{v[5:6]}XXX{v[-1]}" if len(v) == 10 else "XXXXXXXXXX"
    if len(v) <= 4:
        return "X" * len(v)
    return "X" * (len(v) - 4) + v[-4:]


def display(kind: str, v: str) -> str:
    return f"{v[:4]} {v[4:8]} {v[8:]}" if kind == "aadhaar" and len(v) == 12 else v


def _person_of(text: str, start: int) -> str:
    """Whose number: the nearest family word before it (else the owner)."""
    window = (text or "")[max(0, start - 60):start].lower()
    best, pos = "self", -1
    for who, words in PEOPLE.items():
        for w in words:
            for m in re.finditer(rf"\b{re.escape(w)}\b", window):
                if m.start() > pos:
                    best, pos = who, m.start()
    return best


def _person_clean(p: str) -> str:
    p = re.sub(r"[^\w\s.-]", "", (p or "self").strip().lower())[:40] or "self"
    for who, words in PEOPLE.items():
        if p == who or p in words:
            return who
    return p


# ----------------------------------------------------------------------------- store
def save(tenant: str, kind: str, value: str, person: str = "self", note: str = "") -> dict:
    kind = kind if kind in KINDS else "other"
    v = normalize(kind, value)
    why = validate(kind, v)
    if why:
        raise VaultError(why)
    person = _person_clean(person)
    dig = hashlib.sha256(f"{tenant}:{kind}:{v}".encode()).hexdigest()
    with session() as s:
        row = s.scalars(select(IdRecord).where(IdRecord.tenant_id == tenant, IdRecord.digest == dig)).first()
        if row is None:
            row = IdRecord(tenant_id=tenant, ref=new_id("x").split("_", 1)[1][:10].lower(), kind=kind, sealed=_seal(v),
                           masked=mask(kind, v), digest=dig)
            s.add(row)
        row.person = person or row.person
        if note:
            row.note = note[:120]
        s.flush()
        return view(row)


def view(r: IdRecord) -> dict:
    return {"id": r.id, "ref": f"{{id:{r.ref}}}", "person": r.person, "person_label": PERSON_LABEL.get(r.person, r.person.title()),
            "kind": r.kind, "kind_label": KINDS.get(r.kind, r.kind), "masked": r.masked, "note": r.note,
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "used_at": r.used_at.isoformat() if r.used_at else ""}


def list_(tenant: str) -> list[dict]:
    with session() as s:
        rows = s.scalars(select(IdRecord).where(IdRecord.tenant_id == tenant).order_by(IdRecord.person, IdRecord.kind)).all()
        return [view(r) for r in rows]


def delete(tenant: str, rid: str) -> dict:
    with session() as s:
        r = s.get(IdRecord, rid)
        if r is None or r.tenant_id != tenant:
            raise VaultError("Yeh number locker mein nahi mila.")
        s.delete(r)
    return {"deleted": True}


def reveal(tenant: str, rid: str) -> dict:
    """For the owner's own screen only (never offered to the model)."""
    with session() as s:
        r = s.get(IdRecord, rid)
        if r is None or r.tenant_id != tenant:
            raise VaultError("Yeh number locker mein nahi mila.")
        return view(r) | {"value": display(r.kind, _open(r.sealed))}


def resolve(tenant: str, ref: str) -> tuple[str, str] | None:
    """{id:abc} or abc -> (real value, kind) for typing into a form box. Marks it used."""
    m = REF.fullmatch((ref or "").strip()) or re.fullmatch(r"([a-z0-9]{6,16})", (ref or "").strip())
    if not m:
        return None
    with session() as s:
        r = s.scalars(select(IdRecord).where(IdRecord.tenant_id == tenant, IdRecord.ref == m.group(1))).first()
        if r is None:
            return None
        r.used_at = now()
        return _open(r.sealed), r.kind


def find_for(tenant: str, person: str = "self", kind: str = "aadhaar") -> dict | None:
    person = _person_clean(person)
    for r in list_(tenant):
        if r["person"] == person and r["kind"] == kind:
            return r
    return None


def summary_for_model(tenant: str) -> str:
    """What the model may know: who has which ID saved, masked, with the reference to use."""
    rows = list_(tenant)
    if not rows:
        return ""
    return "; ".join(f"{r['person_label']} {r['kind_label']} {r['masked']} = {r['ref']}" for r in rows[:30])


# ----------------------------------------------------------------------------- capture from what she says / types
def capture(tenant: str, text: str) -> tuple[str, list[dict]]:
    """Find identity numbers in her words, keep them in the locker, and give back the text with each number replaced
    by its masked form + reference. OTP / PIN / card / password are not touched here (those stay hers)."""
    if not text:
        return text, []
    saved: list[dict] = []
    out = text
    spans: list[tuple[int, int, str, str]] = []
    for m in AADHAAR.finditer(text):
        digits = "".join(m.groups())
        if verhoeff_ok(digits):
            spans.append((m.start(), m.end(), "aadhaar", digits))
    for m in PAN_LOOSE.finditer(text):
        v = m.group(1).upper()
        if PAN.fullmatch(v) and re.search(r"[A-Za-z]", m.group(1)) and (m.group(1).isupper() or re.search(r"\bpan\b", text[max(0, m.start() - 40):m.start()], re.I)):
            spans.append((m.start(), m.end(), "pan", v))
    for m in GSTIN.finditer(text):
        spans.append((m.start(), m.end(), "gstin", m.group(1)))
    for m in EPIC.finditer(text):
        if re.search(r"voter|epic|matdata|election", text[max(0, m.start() - 50):m.start()], re.I):
            spans.append((m.start(), m.end(), "voter", m.group(1)))
    spans.sort()
    keep, last = [], -1
    for sp in spans:                      # drop overlaps (a PAN inside a GSTIN...)
        if sp[0] >= last:
            keep.append(sp)
            last = sp[1]
    for start, end, kind, value in reversed(keep):
        try:
            rec = save(tenant, kind, value, _person_of(text, start))
        except VaultError:
            continue
        saved.insert(0, rec)
        out = out[:start] + f"[{rec['person_label']} ka {rec['kind_label']} {rec['masked']} · {rec['ref']}]" + out[end:]
    return out, saved


def fill_value(text: str, tenant: str) -> tuple[str, list[str]]:
    """Replace every {id:...} in a value with the real number (for the form box only). Returns (value, kinds)."""
    kinds: list[str] = []

    def sub(m):
        got = resolve(tenant, m.group(0))
        if got is None:
            raise VaultError(f"{m.group(0)} locker mein nahi mila.")
        kinds.append(got[1])
        return got[0]
    return REF.sub(sub, text or ""), kinds


OFFICIAL = re.compile(r"(\.gov\.in|\.nic\.in|\.gov|\.gov\.in\.)$")
OFFICIAL_HOSTS = {"onlineservices.nsdl.com", "tin.tin.nsdl.com", "www.protean-tinpan.com", "protean-tinpan.com",
                  "www.pan.utiitsl.com", "pan.utiitsl.com", "www.utiitsl.com", "utiitsl.com", "www.irctc.co.in",
                  "irctc.co.in", "www.npci.org.in", "npci.org.in", "enps.nsdl.com", "npscra.nsdl.co.in"}


def official_site(url: str) -> bool:
    from urllib.parse import urlparse
    host = (urlparse(url if "://" in (url or "") else "https://" + (url or "")).hostname or "").lower().rstrip(".")
    return bool(host) and (bool(OFFICIAL.search(host)) or host in OFFICIAL_HOSTS)
