"""The data spine (plan 4.2): one place every finance employee reads and writes. F0 = workspaces' books + accounts + transactions, and
statement import in the formats banks give everywhere: CSV, OFX, QIF, MT940 and ISO 20022 CAMT.053.

A transaction is imported once: the dedup key (account, day, amount, narration, bank reference) makes a re-import add nothing."""
from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from . import calc as C

MAX_ROWS = 200_000


class SpineError(ValueError):
    pass


# ---- parsers: each returns [{day, amount (Decimal, + in / - out), narration, ref, currency?}] ----------------------------------

def _d(s: str, fmts: tuple[str, ...]) -> str:
    s = (s or "").strip()
    for f in fmts:
        try:
            return datetime.strptime(s, f).date().isoformat()
        except ValueError:
            continue
    return ""


def parse_csv(text: str) -> list[dict[str, Any]]:
    from ..finguard import statement as ST
    out = []
    for r in ST.parse_csv(text):
        amt = C._dec(r.get("credit") or 0) - C._dec(r.get("debit") or 0)
        out.append({"day": r["date"], "amount": amt, "narration": r.get("narration", ""), "ref": ""})
    return out


def _ofx_tag(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}>([^<\r\n]*)", block, re.I)
    return m.group(1).strip() if m else ""


def parse_ofx(text: str) -> list[dict[str, Any]]:
    out = []
    cur = _ofx_tag(text, "CURDEF")
    for b in re.findall(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|</BANKTRANLIST>)", text, re.S | re.I):
        day = _d(_ofx_tag(b, "DTPOSTED")[:8], ("%Y%m%d",))
        amt = _ofx_tag(b, "TRNAMT")
        if not day or not amt:
            continue
        nar = " ".join(x for x in (_ofx_tag(b, "NAME"), _ofx_tag(b, "MEMO")) if x)
        out.append({"day": day, "amount": C._dec(amt), "narration": nar, "ref": _ofx_tag(b, "FITID"), "currency": cur})
    return out


def parse_qif(text: str) -> list[dict[str, Any]]:
    out, cur = [], {}
    for line in (text or "").splitlines():
        if not line:
            continue
        k, v = line[0], line[1:].strip()
        if k == "^":
            if cur.get("day") and "amount" in cur:
                out.append({"day": cur["day"], "amount": cur["amount"], "narration": " ".join(x for x in (cur.get("p"), cur.get("m")) if x),
                            "ref": cur.get("n", "")})
            cur = {}
        elif k == "D":
            cur["day"] = _d(v.replace("'", "/"), ("%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%Y-%m-%d"))
        elif k in ("T", "U"):
            cur["amount"] = C._dec(v)
        elif k == "P":
            cur["p"] = v
        elif k == "M":
            cur["m"] = v
        elif k == "N":
            cur["n"] = v
    return out


def parse_mt940(text: str) -> list[dict[str, Any]]:
    out = []
    lines = (text or "").replace("\r", "").split("\n")
    cur_ccy = ""
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith(":60F:") or ln.startswith(":60M:"):
            m = re.match(r":60[FM]:[CD]\d{6}([A-Z]{3})", ln)
            cur_ccy = m.group(1) if m else cur_ccy
        if ln.startswith(":61:"):
            m = re.match(r":61:(\d{6})(\d{4})?(R?[CD])([A-Z])?([\d,]+)N?\w{3}([^/]*)(?://(.*))?", ln)
            nar = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith(":61:") and not lines[j].startswith(":62"):
                nar.append(re.sub(r"^:86:", "", lines[j]).strip())
                j += 1
            if m:
                day = _d(m.group(1), ("%y%m%d",))
                amt = C._dec(m.group(5).replace(",", "."))
                sign = -1 if m.group(3) in ("D", "RC") else 1
                out.append({"day": day, "amount": amt * sign, "narration": " ".join(x for x in nar if x)[:240],
                            "ref": (m.group(6) or "").strip(), "currency": cur_ccy})
            i = j
            continue
        i += 1
    return out


def _first(*els):
    """An XML element with no children is falsy - never chain them with `or`."""
    return next((e for e in els if e is not None), None)


def parse_camt053(text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    except ET.ParseError as e:
        raise SpineError(f"CAMT.053 is not valid XML: {e}")

    def local(t: str) -> str:
        return t.split("}", 1)[-1]

    def find(node, *path):
        for p in path:
            node = next((c for c in node if local(c.tag) == p), None)
            if node is None:
                return None
        return node

    out = []
    for ntry in root.iter():
        if local(ntry.tag) != "Ntry":
            continue
        amt_el = find(ntry, "Amt")
        if amt_el is None:
            continue
        ind = find(ntry, "CdtDbtInd")
        day_el = _first(find(ntry, "BookgDt", "Dt"), find(ntry, "BookgDt", "DtTm"), find(ntry, "ValDt", "Dt"))
        day = (day_el.text or "")[:10] if day_el is not None else ""
        info = [t.text.strip() for t in ntry.iter() if local(t.tag) in ("Ustrd", "AddtlNtryInf") and t.text]
        ref_el = _first(find(ntry, "AcctSvcrRef"), find(ntry, "NtryRef"))
        amt = C._dec(amt_el.text)
        out.append({"day": day, "amount": -amt if (ind is not None and ind.text == "DBIT") else amt,
                    "narration": " ".join(info)[:240], "ref": (ref_el.text or "").strip() if ref_el is not None else "",
                    "currency": amt_el.get("Ccy", "")})
    return out


PARSERS = {"csv": parse_csv, "ofx": parse_ofx, "qif": parse_qif, "mt940": parse_mt940, "camt053": parse_camt053}


def detect(text: str) -> str:
    t = (text or "").lstrip()[:4000]
    if "<Document" in t and "camt.053" in t or "<BkToCstmrStmt" in t:
        return "camt053"
    if "OFXHEADER" in t or "<OFX>" in t.upper():
        return "ofx"
    if t.startswith("!Type:") or t.startswith("!Account"):
        return "qif"
    if re.search(r"^:20:", t, re.M) and ":61:" in t:
        return "mt940"
    return "csv"


# ---- stored rows ---------------------------------------------------------------------------------------------------------------

def _dedup(account_id: str, day: str, minor: int, narration: str, ref: str) -> str:
    base = "|".join([account_id, day, str(minor), re.sub(r"\s+", " ", narration.lower()).strip()[:120], ref.strip().lower()])
    return hashlib.sha256(base.encode()).hexdigest()


def _ws(tenant: str, workspace_id: str) -> dict[str, Any]:
    from . import profile as PR
    return PR.get(tenant, workspace_id)


def account(tenant: str, workspace_id: str, name: str, currency: str = "", kind: str = "bank", institution: str = "",
            number: str = "") -> dict[str, Any]:
    """Get or make an account by name in a workspace. Only the last 4 of a number are ever kept."""
    from ..db import session
    from .models import FinAccount, FinBook, ensure
    ws = _ws(tenant, workspace_id)
    ensure()
    cur = (currency or ws["currency"]).upper()
    masked = ("..." + re.sub(r"\D", "", number)[-4:]) if re.sub(r"\D", "", number or "") else ""
    with session() as db:
        a = db.query(FinAccount).filter(FinAccount.tenant_id == tenant, FinAccount.workspace_id == workspace_id,
                                        FinAccount.name == name[:160]).first()
        if a is None:
            book = db.query(FinBook).filter(FinBook.tenant_id == tenant, FinBook.workspace_id == workspace_id).first()
            if book is None:
                kind_b = "household" if ws["size"] == "personal" else "business"
                book = FinBook(tenant_id=tenant, workspace_id=workspace_id, kind=kind_b, currency=ws["currency"],
                               year_end=(ws["settings"] or {}).get("year_end") or "12-31")
                db.add(book)
                db.flush()
            a = FinAccount(tenant_id=tenant, workspace_id=workspace_id, book_id=book.id, name=name[:160] or "Account", kind=kind,
                           institution=institution[:120], number_masked=masked, currency=cur)
            db.add(a)
            db.flush()
        return {"id": a.id, "name": a.name, "kind": a.kind, "currency": a.currency, "number_masked": a.number_masked}


def import_statement(tenant: str, workspace_id: str, text: str, account_name: str = "Main account", currency: str = "",
                     fmt: str = "", actor: str = "owner") -> dict[str, Any]:
    from ..db import session
    from . import evidence as EV
    from . import laws as L
    from .models import FinTxn, ensure
    if not (text or "").strip():
        raise SpineError("The statement is empty.")
    f = fmt or detect(text)
    if f not in PARSERS:
        raise SpineError("format: " + ", ".join(PARSERS))
    try:
        rows = PARSERS[f](text)
    except ValueError as e:
        raise SpineError(str(e))
    if len(rows) > MAX_ROWS:
        raise SpineError(f"At most {MAX_ROWS} rows in one import.")
    acc = account(tenant, workspace_id, account_name, currency or next((r.get("currency") for r in rows if r.get("currency")), ""))
    batch = "imp_" + hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:12]
    ensure()
    added = skipped = bad = 0
    with session() as db:
        seen = {d for (d,) in db.query(FinTxn.dedup).filter(FinTxn.tenant_id == tenant, FinTxn.account_id == acc["id"]).all()}
        for r in rows:
            if not r.get("day"):
                bad += 1
                continue
            cur = (r.get("currency") or acc["currency"]).upper()
            minor = C.to_minor(r["amount"], cur)
            nar = str(r.get("narration") or "")
            if L.secrets_in({"card_number": nar}):
                nar = re.sub(r"(?<!\d)((?:\d[ -]?){9,15})(\d{4})(?!\d)", lambda m: "****" + m.group(2), nar)
            key = _dedup(acc["id"], r["day"], minor, nar, str(r.get("ref") or ""))
            if key in seen:
                skipped += 1
                continue
            seen.add(key)
            db.add(FinTxn(tenant_id=tenant, workspace_id=workspace_id, account_id=acc["id"], day=r["day"], amount_minor=minor,
                          currency=cur, narration=nar[:240], ref=str(r.get("ref") or "")[:80], source=f, source_ref=batch, dedup=key))
            added += 1
    EV.record(tenant, workspace_id, actor, "import", f"statement {f}: {added} added, {skipped} already there", {"batch": batch})
    return {"account": acc, "format": f, "added": added, "already_there": skipped, "unreadable": bad, "batch": batch}


def txns(tenant: str, workspace_id: str, account_id: str = "", since: str = "", until: str = "", limit: int = 500) -> list[dict[str, Any]]:
    from ..db import session
    from .models import FinTxn, ensure
    _ws(tenant, workspace_id)
    ensure()
    with session() as db:
        q = db.query(FinTxn).filter(FinTxn.tenant_id == tenant, FinTxn.workspace_id == workspace_id)
        if account_id:
            q = q.filter(FinTxn.account_id == account_id)
        if since:
            q = q.filter(FinTxn.day >= since)
        if until:
            q = q.filter(FinTxn.day <= until)
        rows = q.order_by(FinTxn.day.desc(), FinTxn.id).limit(max(1, min(limit, 5000))).all()
        return [{"id": t.id, "day": t.day, "amount_minor": t.amount_minor, "currency": t.currency,
                 "amount": str(C.from_minor(t.amount_minor, t.currency)), "narration": t.narration, "ref": t.ref,
                 "account_id": t.account_id, "source": t.source} for t in rows]


def accounts(tenant: str, workspace_id: str) -> list[dict[str, Any]]:
    from sqlalchemy import func

    from ..db import session
    from .models import FinAccount, FinTxn, ensure
    _ws(tenant, workspace_id)
    ensure()
    with session() as db:
        out = []
        for a in db.query(FinAccount).filter(FinAccount.tenant_id == tenant, FinAccount.workspace_id == workspace_id).all():
            n, tot, last = db.query(func.count(FinTxn.id), func.coalesce(func.sum(FinTxn.amount_minor), 0), func.max(FinTxn.day)) \
                .filter(FinTxn.tenant_id == tenant, FinTxn.account_id == a.id).one()
            out.append({"id": a.id, "name": a.name, "kind": a.kind, "currency": a.currency, "number_masked": a.number_masked,
                        "txns": int(n), "net_minor": int(tot), "net": str(C.from_minor(int(tot), a.currency)),
                        "last_day": last or ""})
        return out
