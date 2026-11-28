"""v0.999.46 CA DOCUMENT DESK - the GST & Accounts employee for a CA practice (owner: "MUST HAS ATTACHMENT OF DOC, IMAGE,
PDF, ZIP ... VIA WHATS APP, TELEGRAM, SLACK, EMAIL, LINKEDIN, LOCAL CA PC ... COLLECTING DOCUMENTS, ARRANGING IT IN CA
ASSIGNED PC OR IN CLOUD. ALSO FOLDER OF EVERY CUSTOMER OF CA").

Every client of the CA has a folder:  Client / FY 2026-27 / 10 October / Purchase bills / <date party number>.pdf
A file arrives (WhatsApp business number, the CA's Telegram bot, a Slack channel, a client's email, the CA's PC
'_Drop here' folder, or an upload on the console / phone) and `collect` does the work:

  1. the sender is matched to a client (phone / email / Telegram id / Slack channel / PC folder). An UNKNOWN sender is
     never filed by itself: the files wait in the Document inbox with Hoola's guess (a GSTIN on the bill names a client).
  2. an archive (ZIP / RAR / 7z) is opened and every file inside is collected on its own; a locked one waits.
  3. the file is read (PDF text, OCR for photos) and its kind (sales / purchase / bank / expense / GST return / permanent /
     other) and month are worked out BY CODE from what is on it. Unsure = it waits, with the reason and the choices.
  4. the original bytes are kept unchanged in Hoola's cloud (the master copy), then mirrored by the worker into the CA's
     Google Drive ("CA Clients/...") and onto the CA's PC (Hoola Desktop `save_into` under the folder she picked).

What it never does: send anything to a client on its own (a request is drafted; her tap sends it), keep a password or an
OTP a client types, open a program inside an archive, delete a file on the PC. LinkedIn is not a channel: LinkedIn gives
no app access to messages or their files.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.practice")

KINDS = {"sales": "Sales bills", "purchase": "Purchase bills", "bank": "Bank statements", "expense": "Expenses & receipts",
         "gst": "GST returns", "other": "Other", "permanent": "Permanent"}
CHECKLIST = ["sales", "purchase", "bank", "expense"]
CHANNELS = ("whatsapp", "email", "telegram", "slack", "pc", "upload", "phone")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
          "December"]
MAX_FILE = 30 * 1024 * 1024
MAX_CLIENTS = 2000


class PracticeError(Exception):
    pass


# ---------------------------------------------------------------- tables
class AccClient(Base):
    """One client of the CA, with the ways that client sends documents."""
    __tablename__ = "acc_clients"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    folder: Mapped[str] = mapped_column(String(120), default="")            # the folder name (safe on Windows / Drive)
    gstin: Mapped[str] = mapped_column(String(15), default="", index=True)
    pan: Mapped[str] = mapped_column(String(10), default="")
    phones: Mapped[str] = mapped_column(Text, default="[]")                   # last 10 digits of each WhatsApp number
    emails: Mapped[str] = mapped_column(Text, default="[]")
    telegram: Mapped[str] = mapped_column(Text, default="[]")                 # Telegram user ids
    slack: Mapped[str] = mapped_column(Text, default="[]")                    # Slack channel ids
    code: Mapped[str] = mapped_column(String(16), default="", index=True)    # the client's link code (Telegram start)
    note: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccFile(Base):
    """One document of one client (or one still waiting for her in the Document inbox)."""
    __tablename__ = "acc_files"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    client_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    status: Mapped[str] = mapped_column(String(10), default="waiting", index=True)   # filed | waiting | dropped
    month: Mapped[str] = mapped_column(String(7), default="", index=True)            # YYYY-MM
    kind: Mapped[str] = mapped_column(String(12), default="other")
    name: Mapped[str] = mapped_column(String(200), default="")                       # the name in the folder
    orig_name: Mapped[str] = mapped_column(String(200), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    stored: Mapped[str] = mapped_column(Text, default="")                            # path under the practice store
    channel: Mapped[str] = mapped_column(String(12), default="upload")
    sender: Mapped[str] = mapped_column(String(160), default="")
    message: Mapped[str] = mapped_column(Text, default="")                           # the words that came with it
    guess: Mapped[str] = mapped_column(Text, default="{}")                           # Hoola's guess for a waiting file
    why: Mapped[str] = mapped_column(Text, default="")                               # why it waits (shown to her)
    facts: Mapped[str] = mapped_column(Text, default="{}")                           # party, number, date, total read off it
    parent: Mapped[str] = mapped_column(String(40), default="")                      # the archive it came out of
    drive_state: Mapped[str] = mapped_column(String(12), default="")                 # "" | waiting | done | failed | off
    drive_id: Mapped[str] = mapped_column(String(80), default="")
    pc_state: Mapped[str] = mapped_column(String(12), default="")                    # "" | waiting | done | inbox | failed | off
    pc_path: Mapped[str] = mapped_column(Text, default="")
    tries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    filed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccPracticeSet(Base):
    """The CA's practice settings: which channels are on, where files are mirrored, the Telegram / Slack secrets (sealed)."""
    __tablename__ = "acc_practice_set"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    on: Mapped[bool] = mapped_column(Boolean, default=True)
    practice_name: Mapped[str] = mapped_column(String(160), default="")
    drive_on: Mapped[bool] = mapped_column(Boolean, default=False)
    pc_on: Mapped[bool] = mapped_column(Boolean, default=False)
    pc_root: Mapped[str] = mapped_column(Text, default="")
    whatsapp_on: Mapped[bool] = mapped_column(Boolean, default=True)
    email_on: Mapped[bool] = mapped_column(Boolean, default=False)
    email_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checklist: Mapped[str] = mapped_column(Text, default="")
    telegram: Mapped[str] = mapped_column(Text, default="")        # sealed {token, header}
    telegram_hook: Mapped[str] = mapped_column(String(40), default="", index=True)
    telegram_bot: Mapped[str] = mapped_column(String(80), default="")
    slack: Mapped[str] = mapped_column(Text, default="")           # sealed {bot_token, signing_secret}
    slack_hook: Mapped[str] = mapped_column(String(40), default="", index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccDriveFolder(Base):
    """A Google Drive folder Hoola made for a path, so the same folder is reused (never made twice)."""
    __tablename__ = "acc_drive_folders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dfo"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    path: Mapped[str] = mapped_column(Text, default="")
    ref: Mapped[str] = mapped_column(String(160), default="")


class AccMailSeen(Base):
    """An email already looked at for client documents (each mail once)."""
    __tablename__ = "acc_mail_seen"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)        # tenant + mail ref
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccDocRequest(Base):
    """A request to a client for the month's missing documents. Drafted by Hoola; SENT only by her tap."""
    __tablename__ = "acc_doc_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("drq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    client_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    month: Mapped[str] = mapped_column(String(7), default="")
    channel: Mapped[str] = mapped_column(String(12), default="email")
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="sent")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


TABLES = (AccClient, AccFile, AccPracticeSet, AccDriveFolder, AccMailSeen, AccDocRequest)
_READY: set[int] = set()


def ensure_tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    for t in TABLES:
        t.__table__.create(bind=eng, checkfirst=True)
    _READY.add(id(eng))


# ---------------------------------------------------------------- small helpers
def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _j(v: str, default: Any) -> Any:
    try:
        out = json.loads(v or "")
    except (TypeError, ValueError):
        return default
    return out if isinstance(out, type(default)) else default


def _digits(v: Any) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    return d[-10:] if len(d) >= 10 else d


def safe_part(v: Any, limit: int = 80) -> str:
    """A folder / file name that is safe on Windows, Mac, Linux and Drive: no path, no reserved characters."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", str(v or "")).strip(" .")
    s = re.sub(r"\s+", " ", s)[:limit].strip(" .")
    if s.upper() in ("CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))):
        s = "_" + s
    return s or "file"


def fy_of(month: str) -> str:
    """'2026-10' -> 'FY 2026-27'; '2027-02' -> 'FY 2026-27'."""
    try:
        y, m = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        return "FY unknown"
    start = y if m >= 4 else y - 1
    return f"FY {start}-{str(start + 1)[2:]}"


def month_dir(month: str) -> str:
    try:
        m = int(month[5:7])
        return f"{m:02d} {MONTHS[m - 1]}"
    except (ValueError, IndexError):
        return "Undated"


def parts_of(client: dict[str, Any] | AccClient, f: AccFile | dict[str, Any]) -> list[str]:
    folder = client["folder"] if isinstance(client, dict) else client.folder
    kind = f["kind"] if isinstance(f, dict) else f.kind
    month = f["month"] if isinstance(f, dict) else f.month
    if kind == "permanent":
        return [folder, KINDS["permanent"]]
    return [folder, fy_of(month), month_dir(month), KINDS.get(kind, "Other")]


def store_root() -> Path:
    from ..config import get_settings
    base = Path(getattr(get_settings(), "practice_files_dir", "") or "./data/practice")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _tdir(tenant: str) -> Path:
    return store_root() / hashlib.sha256(tenant.encode()).hexdigest()[:20]


def _month_now() -> str:
    d = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
    return f"{d.year:04d}-{d.month:02d}"


def _prev_month(m: str) -> str:
    y, mo = int(m[:4]), int(m[5:7])
    y, mo = (y, mo - 1) if mo > 1 else (y - 1, 12)
    return f"{y:04d}-{mo:02d}"


# ---------------------------------------------------------------- settings
def settings_row(s, tenant: str) -> AccPracticeSet:
    row = s.get(AccPracticeSet, tenant)
    if row is None:
        row = AccPracticeSet(tenant_id=tenant)
        s.add(row)
        s.flush()
    return row


def _seal(d: dict) -> str:
    from ..bazar.security import vault
    return vault().seal(json.dumps(d))


def _open(v: str) -> dict:
    if not v:
        return {}
    from ..bazar.security import vault
    try:
        return json.loads(vault().open(v))
    except Exception:   # noqa: BLE001
        return {}


def checklist_of(row: AccPracticeSet) -> list[str]:
    got = [k for k in _j(row.checklist, []) if k in KINDS]
    return got or list(CHECKLIST)


def settings(tenant: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        r = settings_row(s, tenant)
        s.commit()
        return {"on": bool(r.on), "practice_name": r.practice_name, "drive_on": bool(r.drive_on), "pc_on": bool(r.pc_on),
                "pc_root": r.pc_root, "whatsapp_on": bool(r.whatsapp_on), "email_on": bool(r.email_on),
                "checklist": checklist_of(r), "telegram": {"on": bool(r.telegram), "bot": r.telegram_bot},
                "slack": {"on": bool(r.slack)}, "linkedin": {"on": False, "why": (
                    "LinkedIn gives no app access to your messages or their files, so Hoola cannot collect documents "
                    "there. Ask the client to send them on email or WhatsApp.")}}


def save_settings(tenant: str, changes: dict[str, Any]) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        r = settings_row(s, tenant)
        for k in ("on", "drive_on", "pc_on", "whatsapp_on", "email_on"):
            if k in changes:
                setattr(r, k, bool(changes[k]))
                if k == "email_on" and changes[k] and not r.email_since:
                    r.email_since = now() - timedelta(days=2)
        if "practice_name" in changes:
            r.practice_name = str(changes["practice_name"] or "")[:160]
        if "pc_root" in changes:
            r.pc_root = str(changes["pc_root"] or "")[:400]
        if isinstance(changes.get("checklist"), list):
            r.checklist = json.dumps([k for k in changes["checklist"] if k in KINDS][:10])
        r.updated_at = now()
        s.commit()
    return settings(tenant)


# ---------------------------------------------------------------- clients
def _cview(c: AccClient) -> dict[str, Any]:
    return {"id": c.id, "name": c.name, "folder": c.folder, "gstin": c.gstin, "pan": c.pan,
            "phones": _j(c.phones, []), "emails": _j(c.emails, []), "telegram": _j(c.telegram, []),
            "slack": _j(c.slack, []), "code": c.code, "note": c.note, "active": bool(c.active)}


def _clean_list(kind: str, vals: Any) -> list[str]:
    out: list[str] = []
    for v in (vals if isinstance(vals, list) else [vals] if vals else []):
        if kind == "phones":
            v = _digits(v)
            ok = len(v) == 10
        elif kind == "emails":
            v = str(v or "").strip().lower()
            ok = bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v))
        else:
            v = str(v or "").strip()[:40]
            ok = bool(v)
        if ok and v not in out:
            out.append(v)
    return out[:20]


def save_client(tenant: str, data: dict[str, Any], client_id: str = "") -> dict[str, Any]:
    from ..appmaker.gst import valid_gstin
    ensure_tables()
    name = str(data.get("name") or "").strip()
    with session() as s:
        if client_id:
            c = s.get(AccClient, client_id)
            if c is None or c.tenant_id != tenant:
                raise PracticeError("That client was not found.")
        else:
            if not name:
                raise PracticeError("Give the client's name.")
            n = len(s.scalars(select(AccClient.id).where(AccClient.tenant_id == tenant)).all())
            if n >= MAX_CLIENTS:
                raise PracticeError(f"A practice can keep up to {MAX_CLIENTS} clients.")
            c = AccClient(tenant_id=tenant, code=secrets.token_hex(4))
            s.add(c)
        if name:
            c.name = name[:160]
            if not c.folder or data.get("rename_folder"):
                base = safe_part(name, 80)
                taken = set(s.scalars(select(AccClient.folder).where(AccClient.tenant_id == tenant, AccClient.id != c.id)).all())
                folder, i = base, 2
                while folder in taken:
                    folder, i = f"{base} ({i})", i + 1
                c.folder = folder
        if "gstin" in data:
            g = str(data.get("gstin") or "").strip().upper()
            if g and not valid_gstin(g):
                raise PracticeError("That GSTIN's shape or check digit is wrong.")
            c.gstin = g
        if "pan" in data:
            p = str(data.get("pan") or "").strip().upper()
            if p and not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", p):
                raise PracticeError("That PAN does not look right (5 letters, 4 digits, 1 letter).")
            c.pan = p
        for k in ("phones", "emails", "telegram", "slack"):
            if k in data:
                setattr(c, k, json.dumps(_clean_list(k, data.get(k))))
        if "note" in data:
            c.note = str(data.get("note") or "")[:1000]
        if "active" in data:
            c.active = bool(data["active"])
        s.commit()
        return _cview(c)


def add_sender(tenant: str, client_id: str, channel: str, sender: str) -> None:
    kind = {"whatsapp": "phones", "email": "emails", "telegram": "telegram", "slack": "slack"}.get(channel)
    if not kind or not sender:
        return
    with session() as s:
        c = s.get(AccClient, client_id)
        if c is None or c.tenant_id != tenant:
            return
        cur = _j(getattr(c, kind), [])
        setattr(c, kind, json.dumps(_clean_list(kind, cur + [sender])))
        s.commit()


def clients(tenant: str, month: str = "", q: str = "") -> list[dict[str, Any]]:
    """Every client with this month's state: what arrived, what is missing from her checklist, the last file."""
    ensure_tables()
    month = month or _month_now()
    with session() as s:
        need = checklist_of(settings_row(s, tenant))
        rows = s.scalars(select(AccClient).where(AccClient.tenant_id == tenant).order_by(AccClient.name)).all()
        files = s.scalars(select(AccFile).where(AccFile.tenant_id == tenant, AccFile.status == "filed")).all()
        s.commit()
        out = []
        ql = (q or "").strip().lower()
        for c in rows:
            v = _cview(c)
            if ql and ql not in (c.name.lower() + " " + c.gstin.lower() + " " + " ".join(v["phones"]) + " " + " ".join(v["emails"])):
                continue
            mine = [f for f in files if f.client_id == c.id]
            got = {f.kind for f in mine if f.month == month}
            last = max(mine, key=lambda f: _utc(f.created_at) or now(), default=None)
            v["month"] = month
            v["missing"] = [k for k in need if k not in got]
            v["complete"] = not v["missing"]
            v["files_month"] = sum(1 for f in mine if f.month == month)
            v["files"] = len(mine)
            v["sends_on"] = [ch for ch, k in (("WhatsApp", "phones"), ("Email", "emails"), ("Telegram", "telegram"),
                                              ("Slack", "slack")) if v[k]]
            v["last"] = ({"name": last.name, "at": _utc(last.created_at).isoformat(), "channel": last.channel} if last else None)
            out.append(v)
        return out


def client(tenant: str, client_id: str) -> AccClient:
    with session() as s:
        c = s.get(AccClient, client_id)
        if c is None or c.tenant_id != tenant:
            raise PracticeError("That client was not found.")
        s.expunge(c)
        return c


def find_client(tenant: str, channel: str, sender: str) -> dict[str, Any] | None:
    """The client a sender belongs to, or None. PC files name their client by its folder."""
    ensure_tables()
    sender = str(sender or "").strip()
    if not sender:
        return None
    with session() as s:
        rows = s.scalars(select(AccClient).where(AccClient.tenant_id == tenant, AccClient.active.is_(True))).all()
        for c in rows:
            if channel == "pc" and c.folder.lower() == sender.lower():
                return _cview(c)
            if channel == "whatsapp" and _digits(sender) in _j(c.phones, []):
                return _cview(c)
            if channel == "email" and sender.lower() in _j(c.emails, []):
                return _cview(c)
            if channel == "telegram" and sender in _j(c.telegram, []):
                return _cview(c)
            if channel == "slack" and sender in _j(c.slack, []):
                return _cview(c)
    return None


def client_by_gstin(tenant: str, gstins: list[str]) -> dict[str, Any] | None:
    if not gstins:
        return None
    with session() as s:
        for c in s.scalars(select(AccClient).where(AccClient.tenant_id == tenant, AccClient.gstin.in_(gstins))).all():
            return _cview(c)
    return None


# ---------------------------------------------------------------- reading a file
_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
_DATE = re.compile(r"\b(\d{1,2})[/\-. ](\d{1,2}|[A-Za-z]{3,9})[/\-. ](\d{2,4})\b")
_ISO = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")


def read_text(name: str, data: bytes) -> str:
    """The text on a file: the PDF / Word / Excel text, OCR for photos and scans. Never raises ('' = nothing read)."""
    low = (name or "").lower()
    try:
        if low.endswith((".png", ".jpg", ".jpeg", ".webp", ".heic", ".bmp", ".tif", ".tiff")):
            from .. import ocr
            r = ocr.read(data, language="en")
            return (r or {}).get("text") or ""
        from .. import docread
        text = (docread.read_text(name, "", data) or {}).get("text") or ""
        if len(text.strip()) < 40 and low.endswith(".pdf"):
            from .. import ocr
            o = ocr.read_pdf(data, language="en")
            text = (o or {}).get("text") or text
        return text
    except Exception:   # noqa: BLE001 - a file Hoola cannot read is still kept; it just waits for her
        log.info("practice: could not read %s", name, exc_info=True)
        return ""


def _dates(text: str) -> list[str]:
    out: list[str] = []
    for d, mo, y in _DATE.findall(text):
        y = ("20" + y) if len(y) == 2 else y
        for fmt, s in (("%d-%m-%Y", f"{d}-{mo}-{y}"), ("%d-%b-%Y", f"{d}-{mo[:3]}-{y}"), ("%d-%B-%Y", f"{d}-{mo}-{y}")):
            try:
                out.append(datetime.strptime(s, fmt).date().isoformat())
                break
            except ValueError:
                continue
    for y, m, d in _ISO.findall(text):
        try:
            out.append(date(int(y), int(m), int(d)).isoformat())
        except ValueError:
            pass
    today = date.today()
    return [d for d in out if "2000-01-01" <= d <= (today + timedelta(days=31)).isoformat()]


_BANK = re.compile(r"(?i)statement of account|account statement|bank statement|opening balance|closing balance|"
                   r"withdrawal|ifsc")
_GSTR = re.compile(r"(?i)\bgstr[\s-]?(1|3b|2a|2b|9|4)\b|form gst|return filed|acknowledg(e)?ment.*return")
_PERM = re.compile(r"(?i)income tax department|permanent account number|registration certificate|form gst reg-06|"
                   r"certificate of incorporation|partnership deed|memorandum of association|udyam registration")
_RECEIPT = re.compile(r"(?i)\breceipt\b|cash memo|fuel|petrol|diesel|restaurant|toll|ticket|boarding pass|parking")
_INVOICE = re.compile(r"(?i)tax invoice|\binvoice\b|\bbill\s*(no|number|#)|debit note|credit note")


def classify(name: str, text: str, client_gstin: str = "") -> dict[str, Any]:
    """{kind, sure, month, months, facts, gstins} - from what is ON the file. Nothing guessed beyond the reasons given."""
    low, t = (name or "").lower(), text or ""
    gstins: list[str] = []
    for g in _GSTIN.findall(t.upper()):
        if g not in gstins:
            gstins.append(g)
    kind, sure = "other", False
    if _GSTR.search(t) or re.search(r"gstr", low):
        kind, sure = "gst", True
    elif _PERM.search(t) or re.search(r"\bpan\b|certificate|deed|udyam", low):
        kind, sure = "permanent", True
    elif _BANK.search(t) or re.search(r"statement|passbook", low):
        kind, sure = "bank", True
    elif _INVOICE.search(t) and gstins:
        if client_gstin and gstins and gstins[0] == client_gstin:
            kind, sure = "sales", True
        elif client_gstin and client_gstin in gstins:
            kind, sure = "purchase", True
        else:
            kind, sure = "purchase", False             # a bill; who issued it is not clear without the client's GSTIN
    elif _RECEIPT.search(t) or re.search(r"receipt|bill|invoice", low):
        kind, sure = "expense", bool(t.strip())
    dates = _dates(t)
    months = []
    for d in dates:
        if d[:7] not in months:
            months.append(d[:7])
    facts: dict[str, Any] = {}
    if kind in ("sales", "purchase", "expense") and t.strip():
        from .intake import extract
        try:
            f = extract(t, client_gstin)
        except Exception:   # noqa: BLE001
            f = {}
        facts = {k: f.get(k) for k in ("party_name", "number", "date", "total", "supplier_gstin") if f.get(k)}
    month = ""
    if facts.get("date"):
        month = str(facts["date"])[:7]
    elif kind == "bank" and months:
        counts: dict[str, int] = {}
        for d in dates:
            counts[d[:7]] = counts.get(d[:7], 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])
        # a statement belongs to a month only when (nearly) all its dates are in it; one spanning months waits for her
        month = top[0][0] if len(top) == 1 or top[0][1] >= 0.8 * len(dates) else ""
    elif len(months) == 1:
        month = months[0]
    return {"kind": kind, "sure": sure, "month": month, "months": months[:4], "facts": facts, "gstins": gstins[:6],
            "read": bool(t.strip())}


def file_name(f: dict[str, Any], orig: str) -> str:
    """'2026-10-06 Patel Steel PS-2611.pdf' when the file says so, else its own name."""
    ext = Path(orig or "").suffix.lower()[:8]
    bits = [str(f.get("date") or ""), str(f.get("party_name") or "")[:50], str(f.get("number") or "").replace("/", "-")]
    bits = [b for b in bits if b]
    if len(bits) >= 2:
        return safe_part(" ".join(bits), 150) + ext
    return safe_part(Path(orig or "file").stem, 150) + ext


# ---------------------------------------------------------------- collecting
def _keep(tenant: str, data: bytes, orig: str) -> str:
    """The master copy, unchanged. Content-addressed per tenant: the same bytes twice are stored once."""
    h = hashlib.sha256(data).hexdigest()
    d = _tdir(tenant) / "blobs" / h[:2]
    d.mkdir(parents=True, exist_ok=True)
    p = d / (h + Path(orig or "").suffix.lower()[:8])
    if not p.exists():
        p.write_bytes(data)
    return str(p.relative_to(store_root()))


def blob(f: AccFile) -> bytes:
    p = (store_root() / f.stored).resolve()
    if store_root().resolve() not in p.parents or not p.is_file():
        raise PracticeError("The file is not on the server any more.")
    return p.read_bytes()


def fview(f: AccFile, cname: str = "") -> dict[str, Any]:
    return {"id": f.id, "client_id": f.client_id, "client": cname, "status": f.status, "month": f.month, "kind": f.kind,
            "kind_label": KINDS.get(f.kind, "Other"), "name": f.name, "orig_name": f.orig_name, "size": f.size,
            "channel": f.channel, "sender": f.sender, "message": f.message[:300], "guess": _j(f.guess, {}),
            "why": f.why, "facts": _j(f.facts, {}), "parent": f.parent, "drive": f.drive_state or ("off" if not f.drive_id else ""),
            "pc": f.pc_state, "pc_path": f.pc_path, "at": (_utc(f.created_at) or now()).isoformat()}


def collect(tenant: str, channel: str, sender: str, name: str, data: bytes, message: str = "", client_id: str = "",
            parent: str = "") -> list[dict[str, Any]]:
    """One file from outside -> filed in its client's folder, or waiting in the Document inbox. Returns the rows made
    (an archive gives one row per file inside, plus the archive kept under Other). Never raises for a bad file."""
    from .. import archive, filecheck
    ensure_tables()
    channel = channel if channel in CHANNELS else "upload"
    name = safe_part((name or "file").replace("\\", "/").rsplit("/", 1)[-1], 180)
    if not data:
        return []
    if len(data) > MAX_FILE:
        return [_row(tenant, channel, sender, name, b"", message, None, "dropped",
                     why=f"Over {MAX_FILE // 1024 // 1024} MB - not kept. Ask the client for a Drive link or a smaller file.")]
    rt = filecheck.real_type(name, data)
    if rt.get("danger"):
        return [_row(tenant, channel, sender, name, b"", message, None, "dropped",
                     why=f"Not kept: it looks unsafe ({rt.get('note', '')}). Do not open it.")]
    known = None
    if client_id:
        try:
            known = _cview(client(tenant, client_id))
        except PracticeError:
            known = None
    known = known or find_client(tenant, channel, sender)
    if archive.is_archive(name, data):
        res = archive.open_archive(name, data)
        out = []
        arc = _row(tenant, channel, sender, name, data, message, known, "filed" if known and res["ok"] else "waiting",
                   kind="other", month=_month_now(), parent=parent,
                   why="" if res["ok"] and known else ("Locked or not opened: " + (res.get("note") or "")[:200]) if not res["ok"]
                   else "Who sent this? The sender is not one of your clients.")
        out.append(arc)
        if res["ok"]:
            for member, b in res["files"]:
                out += collect(tenant, channel, sender, member, b, message, client_id=(known or {}).get("id", ""),
                               parent=arc["id"])
            for sk in res.get("skipped") or []:
                out.append(_row(tenant, channel, sender, safe_part(sk.get("name"), 180), b"", message, known, "dropped",
                                parent=arc["id"], why="Inside the archive, not kept: " + str(sk.get("why") or "")[:160]))
        return out
    text = read_text(name, data)
    cg = (known or {}).get("gstin", "")
    c = classify(name, text, cg)
    if not known:
        # an unknown sender is never filed by itself; a client's GSTIN on the file is only a guess for her
        g = client_by_gstin(tenant, c["gstins"])
        guess = {"client_id": g["id"], "client": g["name"], "kind": c["kind"], "month": c["month"] or _month_now()} if g else \
            {"kind": c["kind"], "month": c["month"] or _month_now()}
        why = (f"Who is this? The file is addressed to {g['name']} ({g['gstin']}). Is this sender theirs?" if g
               else "Who sent this? The sender is not one of your clients yet.")
        return [_row(tenant, channel, sender, name, data, message, None, "waiting", kind=c["kind"], month=c["month"],
                     guess=guess, why=why, facts=c["facts"], parent=parent)]
    if c["kind"] in ("sales", "purchase", "expense", "gst", "bank") and not c["month"]:
        rcv = _month_now()
        opts = [m for m in (c["months"] or [rcv, _prev_month(rcv)])][:3]
        return [_row(tenant, channel, sender, name, data, message, known, "waiting", kind=c["kind"],
                     guess={"client_id": known["id"], "client": known["name"], "kind": c["kind"], "months": opts},
                     why=("The dates on it cover more than one month." if len(c["months"]) > 1 else
                          "No date could be read on it." if c["read"] else "Hoola could not read it (too dark or blurred)."),
                     facts=c["facts"], parent=parent)]
    if not c["read"] and c["kind"] == "other":
        return [_row(tenant, channel, sender, name, data, message, known, "waiting", kind="other",
                     guess={"client_id": known["id"], "client": known["name"], "kind": "other", "month": _month_now()},
                     why="Hoola could not read this file, so its kind and month are not known.", parent=parent)]
    month = c["month"] or _month_now()
    return [_row(tenant, channel, sender, file_name(c["facts"], name), data, message, known, "filed", kind=c["kind"],
                 month=month, facts=c["facts"], parent=parent, orig=name)]


def _row(tenant: str, channel: str, sender: str, name: str, data: bytes, message: str, known: dict | None, status: str,
         kind: str = "other", month: str = "", guess: dict | None = None, why: str = "", facts: dict | None = None,
         parent: str = "", orig: str = "") -> dict[str, Any]:
    h = hashlib.sha256(data).hexdigest() if data else ""
    with session() as s:
        if h and known:
            dup = s.scalars(select(AccFile).where(AccFile.tenant_id == tenant, AccFile.client_id == known["id"],
                                                  AccFile.sha256 == h, AccFile.status != "dropped")).first()
            if dup is not None:
                v = fview(dup, known["name"])
                return v | {"duplicate": True}
        cfg = settings_row(s, tenant)
        f = AccFile(tenant_id=tenant, client_id=(known or {}).get("id", ""), status=status, month=month or "",
                    kind=kind if kind in KINDS else "other", name=safe_part(name, 190), orig_name=safe_part(orig or name, 190),
                    size=len(data), sha256=h, stored=_keep(tenant, data, orig or name) if data else "", channel=channel,
                    sender=str(sender or "")[:160], message=str(message or "")[:2000], guess=json.dumps(guess or {}),
                    why=why[:500], facts=json.dumps(facts or {}), parent=parent)
        if status == "filed":
            f.filed_at = now()
            f.drive_state = "waiting" if cfg.drive_on else ""
            f.pc_state = "waiting" if cfg.pc_on else ""
        s.add(f)
        s.commit()
        return fview(f, (known or {}).get("name", ""))


def file_it(tenant: str, file_id: str, client_id: str, month: str = "", kind: str = "", remember_sender: bool = False,
            new_client: dict | None = None) -> dict[str, Any]:
    """Her tap on a waiting file: which client, which month, which kind. `remember_sender` = this sender is that client's."""
    ensure_tables()
    if new_client:
        client_id = save_client(tenant, new_client)["id"]
    c = client(tenant, client_id)
    with session() as s:
        f = s.get(AccFile, file_id)
        if f is None or f.tenant_id != tenant:
            raise PracticeError("That file was not found.")
        if f.status == "dropped" or not f.stored:
            raise PracticeError("This file was not kept, so it cannot be filed.")
        g = _j(f.guess, {})
        f.client_id = c.id
        f.month = (month or f.month or g.get("month") or _month_now())[:7]
        if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", f.month):
            raise PracticeError("Month must be YYYY-MM.")
        f.kind = kind if kind in KINDS else (f.kind if f.kind in KINDS else "other")
        f.status, f.why, f.filed_at = "filed", "", now()
        cfg = settings_row(s, tenant)
        f.drive_state = "waiting" if cfg.drive_on else ""
        f.pc_state = "waiting" if cfg.pc_on else ""
        ch, snd = f.channel, f.sender
        s.commit()
        out = fview(f, c.name)
    if remember_sender:
        add_sender(tenant, c.id, ch, snd)
        # every other file waiting from the same sender goes to the same client
        for w in waiting(tenant):
            if w["channel"] == ch and w["sender"] == snd and w["id"] != file_id:
                try:
                    file_it(tenant, w["id"], c.id, month=w.get("month") or (w["guess"] or {}).get("month", ""),
                            kind=w.get("kind", ""))
                except PracticeError:
                    pass
    return out


def drop(tenant: str, file_id: str) -> dict[str, Any]:
    """'Not for me': the file leaves the inbox. Its bytes are not kept."""
    with session() as s:
        f = s.get(AccFile, file_id)
        if f is None or f.tenant_id != tenant:
            raise PracticeError("That file was not found.")
        f.status, f.why = "dropped", "You marked it 'not for me'."
        s.commit()
        return fview(f)


def waiting(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(AccFile).where(AccFile.tenant_id == tenant, AccFile.status == "waiting")
                         .order_by(AccFile.created_at.desc()).limit(200)).all()
        names = {c.id: c.name for c in s.scalars(select(AccClient).where(AccClient.tenant_id == tenant)).all()}
        return [fview(f, names.get(f.client_id, "")) for f in rows]


def today(tenant: str) -> dict[str, Any]:
    ensure_tables()
    since = now() - timedelta(hours=24)
    with session() as s:
        rows = s.scalars(select(AccFile).where(AccFile.tenant_id == tenant, AccFile.created_at >= since)).all()
        names = {c.id: c.name for c in s.scalars(select(AccClient).where(AccClient.tenant_id == tenant)).all()}
        filed = [fview(f, names.get(f.client_id, "")) for f in rows if f.status == "filed"]
    w = waiting(tenant)
    return {"came": len([1 for _ in rows]), "filed": filed[:100], "filed_count": len(filed), "waiting": w, "waiting_count": len(w)}


def folder(tenant: str, client_id: str) -> dict[str, Any]:
    """The client's folder tree (FY > month > kind with counts) and every filed file."""
    c = client(tenant, client_id)
    with session() as s:
        rows = s.scalars(select(AccFile).where(AccFile.tenant_id == tenant, AccFile.client_id == c.id,
                                               AccFile.status == "filed").order_by(AccFile.month.desc(), AccFile.name)).all()
        files = [fview(f, c.name) for f in rows]
    tree: dict[str, dict[str, dict[str, int]]] = {}
    for f in files:
        if f["kind"] == "permanent":
            tree.setdefault(KINDS["permanent"], {}).setdefault("", {}).setdefault(KINDS["permanent"], 0)
            tree[KINDS["permanent"]][""][KINDS["permanent"]] += 1
            continue
        fy, md = fy_of(f["month"]), month_dir(f["month"])
        tree.setdefault(fy, {}).setdefault(md, {}).setdefault(KINDS.get(f["kind"], "Other"), 0)
        tree[fy][md][KINDS.get(f["kind"], "Other")] += 1
        f["path"] = " / ".join(parts_of(_cview(c), f))
    return {"client": _cview(c), "tree": tree, "files": files}


def get_file(tenant: str, file_id: str) -> tuple[str, bytes]:
    with session() as s:
        f = s.get(AccFile, file_id)
        if f is None or f.tenant_id != tenant or not f.stored:
            raise PracticeError("That file was not found.")
        s.expunge(f)
    return f.name or f.orig_name, blob(f)


def month_zip(tenant: str, client_id: str, month: str) -> tuple[str, bytes]:
    import io
    import zipfile
    c = client(tenant, client_id)
    with session() as s:
        rows = s.scalars(select(AccFile).where(AccFile.tenant_id == tenant, AccFile.client_id == c.id,
                                               AccFile.status == "filed", AccFile.month == month)).all()
        for r in rows:
            s.expunge(r)
    if not rows:
        raise PracticeError("Nothing is filed for that month yet.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        used: set[str] = set()
        for r in rows:
            p = f"{KINDS.get(r.kind, 'Other')}/{r.name}"
            i = 2
            while p in used:
                p = f"{KINDS.get(r.kind, 'Other')}/({i}) {r.name}"
                i += 1
            used.add(p)
            try:
                z.writestr(p, blob(r))
            except PracticeError:
                continue
    return f"{c.folder} {month}.zip", buf.getvalue()


# ---------------------------------------------------------------- requests (drafted by Hoola, sent by her tap)
def request_draft(tenant: str, client_id: str, month: str = "") -> dict[str, Any]:
    month = month or _prev_month(_month_now())
    c = client(tenant, client_id)
    row = next((r for r in clients(tenant, month) if r["id"] == c.id), None)
    missing = (row or {}).get("missing") or []
    with session() as s:
        cfg = settings_row(s, tenant)
        firm = cfg.practice_name or "your CA"
        s.commit()
    mname = month_dir(month).split(" ", 1)[-1] + " " + month[:4]
    lines = "\n".join(f"- {KINDS[k].lower()}" for k in missing)
    text = (f"Namaste {c.name},\n\nFor your {mname} accounts we still need:\n{lines}\n\n"
            "Please send photos, PDFs or one ZIP on this chat or by email.\n\n— " + firm) if missing else ""
    channels = (["email"] if _j(c.emails, []) else []) + (["whatsapp"] if _j(c.phones, []) else [])
    return {"client": _cview(c), "month": month, "missing": missing, "text": text, "channels": channels,
            "subject": f"Documents needed for {mname}"}


async def send_request(tenant: str, client_id: str, channel: str, text: str, month: str = "", subject: str = "") -> dict[str, Any]:
    """Her tap. Email = sent through her own mailbox; WhatsApp = her business number inside the 24-hour window, else a
    wa.me link she opens herself (outside the window WhatsApp needs an approved template)."""
    import asyncio
    c = client(tenant, client_id)
    text = str(text or "").strip()
    if not text:
        raise PracticeError("The message is empty.")
    month = month or _prev_month(_month_now())
    if channel == "email":
        to = _j(c.emails, [])
        if not to:
            raise PracticeError("This client has no email address saved.")
        from ..db import EmailDraft
        from ..mailbox import service as ms

        def go() -> dict:
            with session() as s:
                d = EmailDraft(tenant_id=tenant, conversation_id="", to_addr=", ".join(to)[:1000],
                               subject=(subject or "Documents needed")[:500], body=text[:20000], kind="new")
                s.add(d)
                s.flush()
                did = d.id
            return ms.send_draft(tenant, did)
        try:
            r = await asyncio.to_thread(go)
        except Exception as e:   # noqa: BLE001
            raise PracticeError(f"The email could not be sent: {e}") from e
        out = {"sent": True, "channel": "email", "status": (r or {}).get("status", "sent")}
    elif channel == "whatsapp":
        phones = _j(c.phones, [])
        if not phones:
            raise PracticeError("This client has no WhatsApp number saved.")
        from urllib.parse import quote
        out = {"sent": False, "channel": "whatsapp", "link": f"https://wa.me/91{phones[0]}?text={quote(text)}",
               "say": "The 24-hour WhatsApp window with this client is closed, so open the link to send it from your WhatsApp."}
        try:
            from ..employee import inbox as biz
            with session() as s:
                bc = s.scalars(select(biz.BizContact).where(biz.BizContact.tenant_id == tenant,
                                                            biz.BizContact.wa_id.like(f"%{phones[0]}"))).first()
                cid = bc.id if bc is not None and biz._window_open(bc) else ""
            if cid:
                await biz.send(tenant, cid, text, by="owner")
                out = {"sent": True, "channel": "whatsapp", "status": "sent"}
        except Exception as e:   # noqa: BLE001 - the wa.me link stays the honest way
            log.info("practice whatsapp request %s: %s", tenant, e)
    else:
        raise PracticeError("channel: email | whatsapp")
    if out.get("sent"):
        with session() as s:
            s.add(AccDocRequest(tenant_id=tenant, client_id=c.id, month=month, channel=channel, text=text[:4000]))
            s.commit()
    return out


def requests_view(tenant: str, month: str = "") -> dict[str, Any]:
    month = month or _prev_month(_month_now())
    with session() as s:
        asked = {}
        for r in s.scalars(select(AccDocRequest).where(AccDocRequest.tenant_id == tenant, AccDocRequest.month == month)).all():
            prev = asked.get(r.client_id)
            if prev is None or (_utc(r.sent_at) or now()) > prev:
                asked[r.client_id] = _utc(r.sent_at) or now()
        need = checklist_of(settings_row(s, tenant))
        s.commit()
    rows = [r | {"asked": asked[r["id"]].isoformat() if r["id"] in asked else ""} for r in clients(tenant, month) if r["missing"]]
    return {"month": month, "checklist": need, "kinds": KINDS, "missing": rows}


# ---------------------------------------------------------------- mirrors (worker)
async def _drive(tenant: str, f: AccFile, c: AccClient) -> None:
    from ..drive import service as DS
    import asyncio

    def go() -> str:
        parent = None
        path = "CA Clients"
        for part in ["CA Clients"] + parts_of(c, f):
            path = path if part == "CA Clients" else f"{path}/{part}"
            with session() as s:
                hit = s.scalars(select(AccDriveFolder).where(AccDriveFolder.tenant_id == tenant, AccDriveFolder.path == path)).first()
                ref = hit.ref if hit else ""
            if not ref:
                made = DS.create_folder(tenant, part, parent)["folder"]
                ref = str(made.get("ref") or made.get("id") or "")
                with session() as s:
                    s.add(AccDriveFolder(tenant_id=tenant, path=path, ref=ref))
                    s.commit()
            parent = ref
        from ..mailbox import service as ms
        tmp = ms.store_bytes(tenant, f.name, blob(f), "mail")
        up = DS.upload(tenant, {"file_id": tmp.id}, folder=parent, name=f.name)["uploaded"]
        return str(up.get("ref") or up.get("id") or "")
    ref = await asyncio.to_thread(go)
    with session() as s:
        r = s.get(AccFile, f.id)
        r.drive_state, r.drive_id = "done", ref[:80]
        s.commit()


async def _pc(tenant: str, f: AccFile, c: AccClient, root: str) -> None:
    from ..mailbox import service as ms
    from ..pc.hub import PcError, hub
    import asyncio
    if not hub.is_online(tenant):
        return                                   # waits: lands when Hoola Desktop is open again
    tmp = await asyncio.to_thread(ms.store_bytes, tenant, f.name, blob(f), "to_pc")
    args = {"file_id": tmp.id, "name": f.name, "url": f"/api/pc/fetch/{tmp.id}", "parts": parts_of(c, f), "root": root}
    try:
        got = await hub.call(tenant, "save_into", args)
        state, path = "done", str((got or {}).get("saved_path") or "")
    except PcError as e:
        if "Unknown action" not in str(e):
            raise
        # an older Hoola Desktop: the file goes to its flat inbox, the client and month in its name
        flat = safe_part(" - ".join(parts_of(c, f)[:3] + [f.name]), 190)
        got = await hub.call(tenant, "save_file", {"file_id": tmp.id, "name": flat, "url": f"/api/pc/fetch/{tmp.id}"})
        state, path = "inbox", str((got or {}).get("saved_path") or "")
    with session() as s:
        r = s.get(AccFile, f.id)
        r.pc_state, r.pc_path = state, path[:1000]
        s.commit()


async def mirror_tick(limit: int = 12) -> int:
    """Drive + PC copies of filed files. A failure is retried a few times, then said on the file (never silent)."""
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(AccFile).where(AccFile.status == "filed", AccFile.tries < 5,
                                               (AccFile.drive_state == "waiting") | (AccFile.pc_state == "waiting"))
                         .limit(limit)).all()
        for r in rows:
            s.expunge(r)
    done = 0
    for f in rows:
        try:
            c = client(f.tenant_id, f.client_id)
        except PracticeError:
            continue
        with session() as s:
            cfg = settings_row(s, f.tenant_id)
            drive_on, pc_on, root = cfg.drive_on, cfg.pc_on, cfg.pc_root
            s.commit()
        for which, on, fn in (("drive", drive_on, lambda: _drive(f.tenant_id, f, c)),
                              ("pc", pc_on, lambda: _pc(f.tenant_id, f, c, root))):
            if getattr(f, f"{which}_state") != "waiting":
                continue
            if not on:
                with session() as s:
                    r = s.get(AccFile, f.id)
                    setattr(r, f"{which}_state", "off")
                    s.commit()
                continue
            try:
                await fn()
                done += 1
            except Exception as e:   # noqa: BLE001
                log.info("practice mirror %s %s: %s", which, f.id, e)
                with session() as s:
                    r = s.get(AccFile, f.id)
                    r.tries = (r.tries or 0) + 1
                    if r.tries >= 5:
                        setattr(r, f"{which}_state", "failed")
                        r.why = f"Could not copy to {'Google Drive' if which == 'drive' else 'your PC'}: {str(e)[:200]}"
                    s.commit()
    return done


async def pc_drop_tick() -> int:
    """Ask each online CA PC for files dropped in a client's '_Drop here' folder (the desktop uploads them here)."""
    from ..pc.hub import hub
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(AccPracticeSet).where(AccPracticeSet.pc_on.is_(True))).all()
        sets = [(r.tenant_id, r.pc_root) for r in rows]
    n = 0
    for tenant, root in sets:
        if not hub.is_online(tenant):
            continue
        folders = [c["folder"] for c in clients(tenant)]
        try:
            got = await hub.call(tenant, "ca_drop", {"root": root, "folders": folders})
            n += int((got or {}).get("sent") or 0)
        except Exception as e:   # noqa: BLE001 - an older desktop has no ca_drop: nothing to collect
            log.debug("practice pc drop %s: %s", tenant, e)
    return n


# ---------------------------------------------------------------- email (her mailbox)
def email_tick(limit: int = 20) -> int:
    from ..mailbox import service as ms
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(AccPracticeSet).where(AccPracticeSet.email_on.is_(True), AccPracticeSet.on.is_(True))).all()
        sets = [(r.tenant_id, _utc(r.email_since)) for r in rows]
    made = 0
    for tenant, since in sets:
        addrs = {e for c in clients(tenant) for e in c["emails"]}
        if not addrs:
            continue
        try:
            got = ms.check(tenant, "inbox", search="has:attachment newer_than:3d", limit=limit, since=since, snippets=False)
        except Exception as e:   # noqa: BLE001
            log.info("practice email %s: %s", tenant, e)
            continue
        for m in got.get("emails") or []:
            frm = str(m.get("from_email") or "").lower()
            key = f"{tenant}:{m.get('id')}"[:200]
            with session() as s:
                if s.get(AccMailSeen, key) is not None:
                    continue
                s.add(AccMailSeen(id=key, tenant_id=tenant))
                s.commit()
            if frm not in addrs:
                continue                       # only mail from a client's saved address is opened
            try:
                full = ms.read(tenant, m["id"], mark_seen=False, learn_contacts=False)
            except Exception:   # noqa: BLE001
                continue
            for a in full.get("attachments") or []:
                try:
                    name, _mt, data = ms.attachment(tenant, m["id"], str(a.get("id")))
                except Exception:   # noqa: BLE001
                    continue
                made += len(collect(tenant, "email", frm, name, data, message=str(full.get("subject") or "")[:300]))
    return made


# ---------------------------------------------------------------- WhatsApp (her business number)
def whatsapp_wanted(value: dict[str, Any]) -> list[tuple[str, str, str, str, str]]:
    """From one Meta `messages` change: the files clients sent to a CA's business number with practice on.
    -> [(tenant, wa_number, media_id, filename, caption)]."""
    from ..employee import inbox as biz
    pnid = str((value.get("metadata") or {}).get("phone_number_id") or "")
    tenant = biz.tenant_of_number(pnid)
    if not tenant:
        return []
    ensure_tables()
    with session() as s:
        r = s.get(AccPracticeSet, tenant)
        if r is not None and (not r.on or not r.whatsapp_on):
            return []
        # only a CA practice (she has clients) collects files from her business number; a shop's customers are not
        if s.scalars(select(AccClient.id).where(AccClient.tenant_id == tenant).limit(1)).first() is None:
            return []
    out = []
    for m in value.get("messages") or []:
        t = m.get("type")
        if t not in ("document", "image"):
            continue
        part = m.get(t) or {}
        mid = str(part.get("id") or "")
        if not mid:
            continue
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}.get(
            str(part.get("mime_type") or ""), "")
        fname = str(part.get("filename") or f"WhatsApp {t} {str(m.get('timestamp') or '')}{ext}")
        out.append((tenant, _digits(m.get("from")), mid, fname, str(part.get("caption") or "")[:500]))
    return out


async def whatsapp_fetch(tenant: str, pnid_hint: str, wa: str, media_id: str, fname: str, caption: str) -> int:
    """Meta's media download: GET /{media-id} -> a short-lived url -> the bytes, with her business number's token."""
    import httpx
    from ..config import get_settings
    from ..employee import inbox as biz
    _pn, token = biz._channel_auth(tenant, pnid_hint)
    token = token or get_settings().wa_token
    if not token:
        return 0
    ver = getattr(get_settings(), "wa_graph_version", "v21.0") or "v21.0"
    hdr = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=60) as h:
        meta = (await h.get(f"https://graph.facebook.com/{ver}/{media_id}", headers=hdr)).json()
        url = str(meta.get("url") or "")
        if not url.startswith("https://"):
            return 0
        r = await h.get(url, headers=hdr)
        if r.status_code >= 400 or len(r.content) > MAX_FILE:
            return 0
        data = r.content
    import asyncio
    rows = await asyncio.to_thread(collect, tenant, "whatsapp", wa, fname, data, caption)
    return len(rows)


# ---------------------------------------------------------------- Telegram (the CA's own bot for clients)
async def telegram_setup(tenant: str, token: str, base: str) -> dict[str, Any]:
    import httpx
    token = str(token or "").strip()
    if not re.fullmatch(r"\d{5,12}:[A-Za-z0-9_-]{30,60}", token):
        raise PracticeError("That does not look like a Telegram bot token (from @BotFather).")
    hook, header = secrets.token_urlsafe(16), secrets.token_urlsafe(24)
    async with httpx.AsyncClient(timeout=20) as h:
        me = (await h.get(f"https://api.telegram.org/bot{token}/getMe")).json()
        if not me.get("ok"):
            raise PracticeError("Telegram did not accept that bot token.")
        wr = (await h.post(f"https://api.telegram.org/bot{token}/setWebhook",
                           json={"url": f"{base.rstrip('/')}/webhooks/practice/telegram/{hook}", "secret_token": header,
                                 "allowed_updates": ["message"]})).json()
        if not wr.get("ok"):
            raise PracticeError("Telegram did not set the webhook: " + str(wr.get("description") or "")[:160])
    with session() as s:
        r = settings_row(s, tenant)
        r.telegram, r.telegram_hook = _seal({"token": token, "header": header}), hook
        r.telegram_bot = str((me.get("result") or {}).get("username") or "")[:80]
        s.commit()
    return settings(tenant)


def telegram_link(tenant: str, client_id: str) -> str:
    c = client(tenant, client_id)
    with session() as s:
        bot = settings_row(s, tenant).telegram_bot
        s.commit()
    return f"https://t.me/{bot}?start={c.code}" if bot else ""


def by_hook(kind: str, hook: str) -> tuple[str, dict] | None:
    if not hook:
        return None
    ensure_tables()
    with session() as s:
        col = AccPracticeSet.telegram_hook if kind == "telegram" else AccPracticeSet.slack_hook
        r = s.scalars(select(AccPracticeSet).where(col == hook)).first()
        if r is None:
            return None
        return r.tenant_id, _open(r.telegram if kind == "telegram" else r.slack)


async def telegram_update(tenant: str, sec: dict, update: dict[str, Any]) -> int:
    import asyncio
    import httpx
    m = update.get("message") or {}
    frm = str((m.get("from") or {}).get("id") or "")
    chat = (m.get("chat") or {}).get("id")
    if not frm or (m.get("from") or {}).get("is_bot") or (m.get("chat") or {}).get("type") != "private":
        return 0
    tok = sec.get("token", "")
    text = str(m.get("text") or "")
    if text.startswith("/start "):
        code = text.split(" ", 1)[1].strip()[:16]
        with session() as s:
            c = s.scalars(select(AccClient).where(AccClient.tenant_id == tenant, AccClient.code == code)).first()
            cid, cname = (c.id, c.name) if c else ("", "")
        if cid:
            add_sender(tenant, cid, "telegram", frm)
            async with httpx.AsyncClient(timeout=20) as h:
                await h.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                             json={"chat_id": chat, "text": f"Linked for {cname}. Send your bills, photos, PDFs or a ZIP here."})
        return 0
    doc = m.get("document")
    photo = (m.get("photo") or [])[-1:] if m.get("photo") else []
    item = doc or (photo[0] if photo else None)
    if not item:
        return 0
    async with httpx.AsyncClient(timeout=60) as h:
        info = (await h.get(f"https://api.telegram.org/bot{tok}/getFile", params={"file_id": item.get("file_id")})).json()
        path = str((info.get("result") or {}).get("file_path") or "")
        if not path or int((info.get("result") or {}).get("file_size") or 0) > MAX_FILE:
            return 0
        r = await h.get(f"https://api.telegram.org/file/bot{tok}/{path}")
        if r.status_code >= 400:
            return 0
    name = str((doc or {}).get("file_name") or Path(path).name or "telegram photo.jpg")
    rows = await asyncio.to_thread(collect, tenant, "telegram", frm, name, r.content, str(m.get("caption") or ""))
    return len(rows)


# ---------------------------------------------------------------- Slack (the CA's app in client channels)
def slack_setup(tenant: str, bot_token: str, signing_secret: str) -> dict[str, Any]:
    if not str(bot_token or "").startswith("xoxb-") or len(str(signing_secret or "")) < 16:
        raise PracticeError("Give the Slack app's bot token (xoxb-...) and its signing secret.")
    with session() as s:
        r = settings_row(s, tenant)
        r.slack = _seal({"bot_token": bot_token.strip(), "signing_secret": signing_secret.strip()})
        r.slack_hook = r.slack_hook or secrets.token_urlsafe(16)
        s.commit()
        hook = r.slack_hook
    return settings(tenant) | {"events_url_path": f"/webhooks/practice/slack/{hook}"}


async def slack_event(tenant: str, sec: dict, body: dict[str, Any]) -> int:
    import asyncio
    import httpx
    ev = body.get("event") or {}
    if body.get("type") != "event_callback" or ev.get("type") != "message" or ev.get("bot_id"):
        return 0
    files = ev.get("files") or []
    chan = str(ev.get("channel") or "")
    n = 0
    async with httpx.AsyncClient(timeout=60, follow_redirects=False) as h:
        for f in files[:20]:
            url = str(f.get("url_private_download") or "")
            if not url.startswith("https://files.slack.com/") or int(f.get("size") or 0) > MAX_FILE:
                continue
            r = await h.get(url, headers={"Authorization": f"Bearer {sec.get('bot_token', '')}"})
            if r.status_code >= 400 or "text/html" in r.headers.get("content-type", ""):
                continue
            rows = await asyncio.to_thread(collect, tenant, "slack", chan, str(f.get("name") or "slack file"), r.content,
                                           str(ev.get("text") or "")[:300])
            n += len(rows)
    return n


def slack_sig_ok(secret: str, ts: str, raw: bytes, sig: str) -> bool:
    from .. import bahar
    return bahar.slack_sig_ok(secret, ts, raw, sig)


def summary(tenant: str) -> dict[str, Any]:
    """For the chat: clients, this month's state, the inbox."""
    cs = clients(tenant)
    w = waiting(tenant)
    return {"clients": len(cs), "complete": sum(1 for c in cs if c["complete"]), "month": _month_now(),
            "missing": [{"client": c["name"], "missing": [KINDS[k] for k in c["missing"]]} for c in cs if c["missing"]][:30],
            "waiting": len(w), "waiting_first": [{"id": x["id"], "name": x["name"], "why": x["why"], "from": x["channel"]}
                                                 for x in w[:10]]}
