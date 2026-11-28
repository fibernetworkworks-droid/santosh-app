"""v0.999.166 bank accounts of a business, connected the way that works in her country (plan D4).

Four routes, all landing bank lines in the same place (fin.spine.import_rows), so matching and reconciliation never care
where a line came from:
  1. bank connection  a licensed open-banking partner (India Account Aggregator, UK/EU GoCardless, US/Canada Plaid); she
                      signs in at her OWN bank's page and approves read-only access; Hoola fetches new lines every hour
  2. bank files       MT940 / CAMT.053 / OFX / QIF files her bank or her accounting program sends - to her business email or
                      to POST /api/books/bank-file with her books key - read automatically
  3. statement mail   her bank's monthly statement email (PDF or CSV) from a sender she named for an account; a PDF password
                      she typed once here, sealed, used only to open that bank's statements
  4. upload           a file she drops in (always works, every country)
Hoola never sees a bank password, PIN or OTP, never moves money and never writes to her bank."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..sources import openbanking as OB
from .safety import SafetyError

log = logging.getLogger("hoola.books.bank")

FILE_EXT = (".sta", ".940", ".mt940", ".ofx", ".qfx", ".qif", ".camt", ".053")
TEXT_FMT = ("camt053", "mt940", "ofx", "qif")
MAX_FILE = 15 * 1024 * 1024
SYNC_EVERY = 3600
DEFAULT = {"email": True, "senders": [], "seen": [], "warned": []}


class BankFeedError(SafetyError):
    pass


def _db():
    from ... import db
    from .. import models as M
    M.ensure()
    return db, M


def _ws(tenant: str, ws: str):
    db, M = _db()
    with db.session() as s:
        w = s.get(M.FinWorkspace, ws)
        if w is None or w.tenant_id != tenant:
            raise BankFeedError("No such business.")
        return {"id": w.id, "name": w.name, "countries": json.loads(w.countries or "[]"), "currency": w.currency,
                "settings": json.loads(w.settings or "{}")}


def settings(tenant: str, ws: str) -> dict[str, Any]:
    return {**DEFAULT, **(_ws(tenant, ws)["settings"].get("bank_feed") or {})}


def _save(tenant: str, ws: str, upd: dict[str, Any]) -> dict[str, Any]:
    db, M = _db()
    with db.session() as s:
        w = s.get(M.FinWorkspace, ws)
        st = json.loads(w.settings or "{}")
        cur = {**DEFAULT, **(st.get("bank_feed") or {}), **upd}
        st["bank_feed"] = cur
        w.settings = json.dumps(st)
        return cur


def _seal(x: str) -> str:
    from ...accounts import AuthError, encrypt
    try:
        return encrypt(x) or ""
    except AuthError:
        raise BankFeedError("This server cannot keep a password sealed yet (SECRET_KEY is not set), so it was not saved.")


def _unseal(x: str) -> str:
    from ...accounts import decrypt
    try:
        return decrypt(x) or ""
    except Exception:   # noqa: BLE001
        return ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- what she sees

def routes(tenant: str, ws: str) -> dict[str, Any]:
    """The ways a bank account of this business can come in, for her country."""
    w = _ws(tenant, ws)
    from . import books_feed as F
    feed = F.settings(tenant, ws)
    cc = [c.upper() for c in (w["countries"] or [])] or [""]
    bm = F.business_mail(tenant, ws)
    return {
        "countries": cc,
        "connection": [{"country": c, **OB.for_country(c)} for c in cc],
        "files": {"address": "/api/books/bank-file", "key_on": bool(feed.get("hook_hash")),
                  "emails": [a["address"] for a in bm.get("attached") or []]},
        "mail": {"on": bool(settings(tenant, ws).get("email")), "emails": [a["address"] for a in bm.get("attached") or []]},
        "upload": {"formats": ["CSV", "OFX", "QIF", "MT940", "CAMT.053", "PDF"]},
    }


def _link_view(l) -> dict[str, Any]:
    acc = json.loads(l.accounts or "[]")
    days_left = None
    if l.expires_at:
        try:
            days_left = (datetime.fromisoformat(l.expires_at) - datetime.now(timezone.utc)).days
        except ValueError:
            pass
    return {"id": l.id, "partner": l.partner, "partner_name": OB.NAMES.get(l.partner, l.partner), "country": l.country,
            "institution": l.institution, "status": l.status, "accounts": [{k: a.get(k) for k in ("name", "masked", "currency")} for a in acc],
            "expires_at": l.expires_at, "days_left": days_left, "last_sync": l.last_sync, "error": l.last_error,
            "renew": l.status == "expired" or (days_left is not None and days_left <= 7)}


def overview(tenant: str, ws: str) -> dict[str, Any]:
    """Bank accounts of the business with where their lines come from, the connections, and the routes for her country."""
    from sqlalchemy import func
    from .. import spine as SP
    db, M = _db()
    accts = SP.accounts(tenant, ws)
    with db.session() as s:
        src: dict[str, dict[str, int]] = {}
        for aid, so, n in s.query(M.FinTxn.account_id, M.FinTxn.source, func.count(M.FinTxn.id)).filter(
                M.FinTxn.tenant_id == tenant, M.FinTxn.workspace_id == ws).group_by(M.FinTxn.account_id, M.FinTxn.source).all():
            src.setdefault(aid, {})[so or ""] = int(n)
        links = [_link_view(l) for l in s.query(M.FinBankLink).filter(M.FinBankLink.tenant_id == tenant, M.FinBankLink.workspace_id == ws,
                                                                       M.FinBankLink.status != "revoked").order_by(M.FinBankLink.created_at).all()]
    label = {"bank": "Bank connection", "bank_file": "Bank file", "mail": "Statement mail"}
    for a in accts:
        a["sources"] = sorted({label.get(k, "Upload") for k in src.get(a["id"], {})})
    st = settings(tenant, ws)
    senders = [{"match": x["match"], "account": x["account"], "password": bool(x.get("pw"))} for x in st.get("senders") or []]
    return {"accounts": [a for a in accts if a.get("kind") == "bank"], "links": links, "senders": senders, "routes": routes(tenant, ws)}


# ---------------------------------------------------------------- 1. bank connection (open banking)

def banks(tenant: str, ws: str, country: str, q: str = "") -> dict[str, Any]:
    p = OB.for_country(country)
    if p["state"] != "ready" or p["needs"] != "bank":
        return {"banks": [], "why": p.get("why", "")}
    try:
        return {"banks": OB.partner(p["partner"]).banks(country, q)}
    except OB.BankLinkError as e:
        raise BankFeedError(str(e))


def connect(tenant: str, ws: str, country: str, account: str = "", bank: str = "", mobile: str = "", actor: str = "",
            bank_name: str = "") -> dict[str, Any]:
    """She starts a connection: Hoola asks the partner for a consent page at HER bank and gives her the link."""
    from ...config import get_settings
    w = _ws(tenant, ws)
    cc = (country or (w["countries"] or [""])[0]).upper()
    p = OB.for_country(cc)
    if p["state"] != "ready":
        raise BankFeedError(p["why"])
    base = str(get_settings().public_base_url or "").rstrip("/")
    if not base:
        raise BankFeedError("This server has no public address set (PUBLIC_BASE_URL), so the bank cannot send you back.")
    state = secrets.token_urlsafe(18)
    try:
        got = OB.partner(p["partner"]).start(cc, bank, f"{base}/api/books/bank/back?s={state}", state, mobile)
    except OB.BankLinkError as e:
        raise BankFeedError(str(e))
    if not got.get("url"):
        raise BankFeedError("The partner gave no page to open. Try again in a minute.")
    db, M = _db()
    with db.session() as s:
        l = M.FinBankLink(tenant_id=tenant, workspace_id=ws, partner=p["partner"], country=cc, institution=str(bank_name or got.get("institution") or bank)[:160],
                          ext_ref=str(got.get("ext_ref") or "")[:120], state=state, expires_at=str(got.get("expires_at") or ""),
                          accounts=json.dumps([{"hint": (account or "")[:80]}]) if account else "[]")
        s.add(l)
        s.flush()
        lid = l.id
    _evidence(tenant, ws, actor, "bank_connect", f"started a bank connection through {OB.NAMES[p['partner']]}")
    return {"link": lid, "url": got["url"], "partner": p["name"],
            "says": f"Open the page, sign in at your own bank and approve read-only access. Hoola never sees your bank password."}


def _rows_of(link, ws_currency: str) -> dict[str, Any]:
    return {"ext_ref": link.ext_ref, "token": _unseal(link.token_sealed) if link.token_sealed else "", "cursor": link.cursor,
            "accounts": json.loads(link.accounts or "[]")}


def refresh(tenant: str, link_id: str, full: bool = False) -> dict[str, Any]:
    """Ask the partner where the consent stands; when it is active, bring in new bank lines for every account it covers."""
    from .. import spine as SP
    db, M = _db()
    with db.session() as s:
        l = s.get(M.FinBankLink, link_id)
        if l is None or l.tenant_id != tenant:
            raise BankFeedError("No such bank connection.")
        if l.status == "revoked":
            return _link_view(l)
        ws = l.workspace_id
        try:
            ad = OB.PARTNERS[l.partner]
            st = ad.status(_rows_of(l, ""))
        except (OB.BankLinkError, KeyError, httpx_errors()) as e:
            l.last_error = str(e)[:300]
            return _link_view(l)
        hint = next((a.get("hint") for a in json.loads(l.accounts or "[]") if a.get("hint")), "")
        if st.get("token"):
            l.token_sealed = _seal(st["token"])
        if st.get("institution"):
            l.institution = str(st["institution"])[:160]
        prev = {a.get("ext_id"): a for a in json.loads(l.accounts or "[]") if a.get("ext_id")}
        if st.get("accounts"):
            accts = []
            for i, a in enumerate(st["accounts"]):
                keep = prev.get(a["ext_id"]) or {}
                name = keep.get("book_name") or (hint if hint and i == 0 else "") or \
                    f"{l.institution or a.get('name') or 'Bank'} {a.get('masked') or ''}".strip()
                accts.append({**a, "book_name": name[:160]})
            l.accounts = json.dumps(accts)
        l.status = st.get("status") or l.status
        link = {**_rows_of(l, ""), "token": _unseal(l.token_sealed) if l.token_sealed else ""}
        status, accts, last = l.status, json.loads(l.accounts or "[]"), l.last_sync
        partner, inst = l.partner, l.institution
    added = 0
    err = ""
    if status == "active":
        since = (date.today() - timedelta(days=90 if (full or not last) else 7)).isoformat()
        cursor = link.get("cursor", "")
        for a in accts:
            if not a.get("ext_id"):
                continue
            try:
                got = OB.PARTNERS[partner].fetch({**link, "cursor": cursor}, a["ext_id"], since)
            except (OB.BankLinkError, httpx_errors()) as e:
                err = str(e)[:300]
                continue
            cursor = got.get("cursor") or cursor
            rows = [r for r in got.get("rows") or [] if r.get("day")]
            if rows:
                out = SP.import_rows(tenant, ws, rows, a["book_name"], a.get("currency") or "", "bank",
                                     f"bank_{link_id}_{date.today().isoformat()}", "Hoola (bank connection)", inst, a.get("masked") or "")
                added += out["added"]
        with db.session() as s:
            l = s.get(M.FinBankLink, link_id)
            l.cursor = cursor
            l.last_sync = _now()
            l.last_error = err
    with db.session() as s:
        v = _link_view(s.get(M.FinBankLink, link_id))
    return {**v, "added": added}


def httpx_errors():
    import httpx
    return httpx.HTTPError


def back(state: str) -> dict[str, Any]:
    """The bank sent her back (public route): find the connection by its one-time key and read it."""
    db, M = _db()
    if not state or len(state) < 16:
        return {"ok": False, "says": "This link is not from Hoola."}
    with db.session() as s:
        l = s.query(M.FinBankLink).filter(M.FinBankLink.state == state).first()
        if l is None:
            return {"ok": False, "says": "This link is not from Hoola or was already used."}
        tenant, lid = l.tenant_id, l.id
        l.state = ""            # one-time
    v = refresh(tenant, lid, full=True)
    if v.get("status") == "active":
        return {"ok": True, "says": f"Your bank is connected. {v.get('added', 0)} bank lines came in. You can close this page.", "link": v}
    return {"ok": False, "says": "The bank did not confirm the connection yet. Go back to Hoola and press Check again.", "link": v}


def disconnect(tenant: str, ws: str, link_id: str, actor: str = "") -> dict[str, Any]:
    db, M = _db()
    with db.session() as s:
        l = s.get(M.FinBankLink, link_id)
        if l is None or l.tenant_id != tenant or l.workspace_id != ws:
            raise BankFeedError("No such bank connection.")
        link = _rows_of(l, "")
        partner = l.partner
        l.status = "revoked"
        l.token_sealed = ""
        l.state = ""
    note = ""
    try:
        OB.PARTNERS[partner].revoke(link)
    except Exception as e:   # noqa: BLE001
        note = f" The partner did not confirm ({str(e)[:120]}); also remove Hoola in your bank's or the partner's consent settings."
    _evidence(tenant, ws, actor, "bank_disconnect", f"ended a bank connection through {OB.NAMES.get(partner, partner)}")
    return {"says": "Disconnected. Bank lines already in the books stay." + note, "bank": overview(tenant, ws)}


def sync_now(tenant: str, ws: str) -> dict[str, Any]:
    db, M = _db()
    with db.session() as s:
        ids = [l.id for l in s.query(M.FinBankLink).filter(M.FinBankLink.tenant_id == tenant, M.FinBankLink.workspace_id == ws,
                                                            M.FinBankLink.status.in_(("active", "pending"))).all()]
    added = sum(int(refresh(tenant, i).get("added") or 0) for i in ids)
    return {"added": added, "says": f"{added} new bank line{'s' if added != 1 else ''} came in.", "bank": overview(tenant, ws)}


# ---------------------------------------------------------------- 2 + 3. bank files and statement mail

def _norm_rule(m: str) -> str:
    m = str(m or "").strip().lower()
    if not m or not re.fullmatch(r"(?:[^@\s]+@)?@?[a-z0-9.-]+\.[a-z]{2,}", m):
        raise BankFeedError("Type the address your bank's statements come from, like statements@yourbank.com or @yourbank.com.")
    return m if "@" in m else "@" + m


def sender_add(tenant: str, ws: str, match: str, account: str, password: str = "", actor: str = "") -> dict[str, Any]:
    """Statements from this sender go into this bank account. A PDF password is sealed and used only for that bank's statements."""
    rule = _norm_rule(match)
    acct = str(account or "").strip()[:160]
    if not acct:
        raise BankFeedError("Name the bank account these statements are for.")
    st = settings(tenant, ws)
    rows = [x for x in st.get("senders") or [] if x["match"] != rule]
    rows.append({"match": rule, "account": acct, "pw": _seal(password) if password else ""})
    _save(tenant, ws, {"senders": rows[:20], "email": True})
    _evidence(tenant, ws, actor, "bank_sender", f"statements from {rule} go to {acct}" + (" (PDF password saved, sealed)" if password else ""))
    return {"says": f"Statements from {rule} now go into {acct}.", "bank": overview(tenant, ws)}


def sender_remove(tenant: str, ws: str, match: str) -> dict[str, Any]:
    rule = str(match or "").strip().lower()
    st = settings(tenant, ws)
    _save(tenant, ws, {"senders": [x for x in st.get("senders") or [] if x["match"] != rule]})
    return {"says": f"{rule} is no longer read for bank statements.", "bank": overview(tenant, ws)}


def _rule_for(st: dict[str, Any], sender: str) -> dict[str, Any] | None:
    s = str(sender or "").lower().strip()
    for r in st.get("senders") or []:
        m = r["match"]
        if (m.startswith("@") and s.endswith(m)) or s == m:
            return r
    return None


def _file_rows(name: str, data: bytes, password: str = "") -> tuple[str, list[dict[str, Any]]]:
    """(format, rows) for a statement file, or ('', []) when it is not one."""
    from .. import spine as SP
    from decimal import Decimal
    low = (name or "").lower()
    if low.endswith(".pdf") or data[:4] == b"%PDF":
        from ...bahi import bank as BB
        try:
            got = BB.parse_pdf(data, password)
        except Exception as e:   # noqa: BLE001
            raise BankFeedError(str(e)[:200])
        return "pdf", [{"day": r["date"], "amount": Decimal(str(r.get("credit") or 0)) - Decimal(str(r.get("debit") or 0)),
                        "narration": r.get("narration", ""), "ref": ""} for r in got]
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1", "ignore")
    f = SP.detect(text)
    try:
        return f, SP.PARSERS[f](text)
    except Exception:   # noqa: BLE001
        return "", []


def is_bank_file(name: str, data: bytes) -> bool:
    """A file that is a bank statement by its own format (MT940, CAMT.053, OFX, QIF) - no sender rule needed."""
    from .. import spine as SP
    low = (name or "").lower()
    if low.endswith(FILE_EXT):
        return True
    if low.endswith((".xml", ".txt")) and len(data) < MAX_FILE:
        head = data[:4000].decode("utf-8", "ignore")
        return SP.detect(head) in TEXT_FMT
    return False


def _mt940_account(data: bytes) -> str:
    m = re.search(rb"^:25:([^\r\n]+)", data, re.M)
    if not m:
        return ""
    num = re.sub(r"\D", "", m.group(1).decode("latin-1", "ignore"))
    return f"Bank account ...{num[-4:]}" if num else ""


def take_file(tenant: str, ws: str, sender: str, name: str, data: bytes, ref: str, source: str = "mail",
              account: str = "", currency: str = "") -> dict[str, Any] | None:
    """A file that arrived (mail or API). Returns the import when it was a bank statement, None when it is not one (the
    invoice reader then looks at it)."""
    from .. import spine as SP
    st = settings(tenant, ws)
    rule = _rule_for(st, sender) if source == "mail" else None
    if ref and ref in (st.get("seen") or []):
        return {"skipped": "already read"}
    if not rule and not account and not is_bank_file(name, data):
        return None
    if source == "mail" and not st.get("email"):
        return None
    if len(data) > MAX_FILE:
        raise BankFeedError("That statement file is too big (15 MB at most).")
    f, rows = _file_rows(name, data, _unseal(rule.get("pw", "")) if rule and rule.get("pw") else "")
    if not rows:
        if rule:          # her bank's mail with no statement inside (a notice, an advert): not an invoice either
            return {"skipped": "no bank lines in this mail"}
        return None
    acct = account or (rule or {}).get("account") or _mt940_account(data) or "Bank file"
    out = SP.import_rows(tenant, ws, rows, acct, currency, "mail" if rule else "bank_file",
                         "bf_" + hashlib.sha256(data).hexdigest()[:12], f"Hoola ({'statement mail' if rule else 'bank file'})")
    if ref:
        _save(tenant, ws, {"seen": ([x for x in st.get("seen") or [] if x != ref] + [ref])[-300:]})
    return {**out, "format": f, "from": sender}


def from_api_file(tenant: str, ws: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/books/bank-file (her books key): {account, currency?, name, base64 | text} - a statement file her program sends."""
    if body.get("base64"):
        try:
            data = base64.b64decode(str(body["base64"]), validate=True)
        except Exception:   # noqa: BLE001
            raise BankFeedError("base64 could not be read.")
    else:
        data = str(body.get("text") or "").encode()
    if not data.strip():
        raise BankFeedError("Send the statement as base64 or text.")
    acct = str(body.get("account") or "").strip()[:160] or "Bank file"
    out = take_file(tenant, ws, "", str(body.get("name") or "statement.sta")[:200], data, "", "api", acct,
                    str(body.get("currency") or "").upper()[:3])
    if not out or "added" not in out:
        raise BankFeedError("No bank lines could be read from that file (CSV, OFX, QIF, MT940, CAMT.053 or PDF).")
    return out


# ---------------------------------------------------------------- the worker

_last: dict[str, float] = {}


def tick() -> int:
    """Every hour: new lines from every active connection; a consent that runs out within 7 days is said once in her updates chat."""
    import time
    t = time.time()
    if t - _last.get("run", 0) < 300:
        return 0
    _last["run"] = t
    db, M = _db()
    with db.session() as s:
        rows = [(l.id, l.tenant_id, l.workspace_id, l.status, l.last_sync, l.expires_at, l.partner)
                for l in s.query(M.FinBankLink).filter(M.FinBankLink.status.in_(("active", "pending"))).all()]
    made = 0
    for lid, tenant, ws, status, last, exp, partner in rows:
        try:
            if status == "pending":
                with db.session() as s:
                    l = s.get(M.FinBankLink, lid)
                    if l.created_at and (datetime.now(timezone.utc) - _aware(l.created_at)).days >= 1:
                        l.status, l.last_error = "failed", "She did not finish at the bank within a day."
                        continue
            if last and (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() < SYNC_EVERY:
                continue
            v = refresh(tenant, lid)
            made += int(v.get("added") or 0)
            if v.get("renew"):
                _warn(tenant, ws, lid, v)
        except Exception:   # noqa: BLE001
            log.exception("bank sync %s", lid)
    return made


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _warn(tenant: str, ws: str, lid: str, v: dict[str, Any]) -> None:
    st = settings(tenant, ws)
    key = f"{lid}:{v.get('status')}"
    if key in (st.get("warned") or []):
        return
    _save(tenant, ws, {"warned": ((st.get("warned") or []) + [key])[-50:]})
    line = (f"Books: your bank connection through {v['partner_name']} has ended. Renew it in Books & Accounts > Bank & matching "
            "so bank lines keep coming in." if v.get("status") == "expired" else
            f"Books: your bank connection through {v['partner_name']} runs out in {v.get('days_left')} days. Renew it in Books & Accounts > "
            "Bank & matching.")
    try:
        from ... import convs
        from ...agent.santosh import _save as save
        from ...events import bus
        conv = convs.notice_chat(tenant)
        if conv:
            save(conv, "assistant", [{"type": "text", "text": line}], display=line)
            bus.publish(conv, "message", {"role": "assistant", "text": line, "source": "books_bank"})
    except Exception:   # noqa: BLE001
        log.exception("bank warn")


def _evidence(tenant: str, ws: str, actor: str, kind: str, text: str) -> None:
    try:
        from .. import evidence as EV
        EV.record(tenant, ws, actor or "owner", kind, text, {})
    except Exception:   # noqa: BLE001
        log.info("bank evidence %s", kind)
