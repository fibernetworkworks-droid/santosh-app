"""v0.109 What happened after "Paisa bhejo": the UPI app's own answer, or the owner's word.

Flow: approval card -> upi://pay intent (tr = our txn_ref) -> the phone opens it with startActivityForResult ->
the UPI app hands back a response string (NPCI intent spec: "txnId=..&responseCode=..&Status=SUCCESS&txnRef=..")
-> the phone POSTs it here -> the transaction moves to completed / failed / pending -> a chat line + a card.

The UPI app's answer is a statement from an app on HER phone, not a bank confirmation: it is recorded as
"app_said" and shown as such. When an app sends nothing back (she pressed back, the app gives no result, the
phone restarted) the card asks her "Ho gaya / Nahi hua"; her word is recorded as "owner_said".
Hoola never moves money and never sees the UPI PIN.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import unquote_plus

from sqlalchemy import select

from ..db import session
from ..events import bus, notify
from .connectors.base import ToolError, rupees
from .db import Task, Transaction

log = logging.getLogger("santosh.upi")

# Response codes UPI apps commonly hand back (NPCI). Plain words; `blocked` = the app or bank refused the intent
# itself, so typing the UPI ID in the app by hand is the way through.
CODES: dict[str, tuple[str, bool]] = {
    "U16": ("app ya bank ne risk limit ki wajah se roka", True),
    "U30": ("bank ne paise kaatne se mana kiya", False),
    "U66": ("device ya app se payment allowed nahi hui", True),
    "U90": ("bank ka jawab der se aaya", False),
    "ZM": ("UPI PIN galat tha", False),
    "Z6": ("UPI PIN ki koshishein khatam ho gayin", False),
    "Z9": ("account mein paise kam the", False),
    "Z8": ("din ki limit poori ho gayi", False),
    "ZD": ("app ne link ko sahi nahi maana", True),
    "ZA": ("aapne app mein mana kar diya", False),
    "ZH": ("UPI ID galat hai", False),
    "ZX": ("account band / inactive hai", False),
    "XB": ("bank ne transaction mana kiya", False),
    "YE": ("bank ne transaction mana kiya", False),
    "RB": ("bank ne transaction mana kiya", False),
}
# Words some apps put in their failure text when they refuse a payment link to a person's UPI ID.
BLOCK_WORDS = re.compile(r"security|risk|not allowed|not permitted|declined by|limit exceeded|unsafe|suspicious|"
                         r"payment link|merchant|not responding|exceed", re.I)   # v0.322 her GPay: "server not responding / limit exceeded"
DONE = ("completed", "paid")

# v0.120 Apps known to refuse a payment link to a PERSON's UPI ID started by another app ("security reasons").
# PhonePe: seen on the owner's OnePlus 22 Oct 2026. Others are learned per owner when they refuse.
P2P_LINK_BLOCKED = {"com.phonepe.app"}
P2P_LINK_DEFAULT_BLOCKED = True   # v0.322 every app, unless she saw the link work in it
BLOCK_KEEP_DAYS = 60   # apps change their rules; after this the link is tried again


def _blocked_map(user) -> dict[str, str]:
    return dict(((user.profile or {}).get("upi_link_blocked") or {}))


def link_blocked(user, package: str) -> bool:
    """True when this app refuses Hoola's payment link for a person (built-in list or learned for this owner).
    v0.322: EVERY UPI app is treated as refusing by default (her live test 31 Oct: Google Pay and others answered "server
    not responding / limit exceeded" - since 2023-24 the big apps only accept signed MERCHANT links), so a payment to a
    person always goes the copy-UPI-ID way; an app she has seen accept the link ("ok") gets the link again."""
    if not package:
        return False
    if P2P_LINK_DEFAULT_BLOCKED and _blocked_map(user).get(package) != "ok":
        return True
    seen = _blocked_map(user).get(package)
    if seen == "ok":
        return False   # she saw the link work in this app: trust that over the built-in list
    if seen:
        try:
            import datetime as _dt
            if (_dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) - _dt.datetime.fromisoformat(seen)).days > BLOCK_KEEP_DAYS:
                return package in P2P_LINK_BLOCKED
        except ValueError:
            pass
        return True
    return package in P2P_LINK_BLOCKED


def _mark(s, user_id: str, package: str, value: str) -> None:
    from .db import User
    import datetime as _dt
    u = s.get(User, user_id)
    if u is None or not package:
        return
    mp = _blocked_map(u)
    mp[package[:120]] = value if value == "ok" else _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    u.profile = {**(u.profile or {}), "upi_link_blocked": mp}


def parse(raw: str) -> dict[str, str]:
    """NPCI response string -> {status SUCCESS|FAILURE|SUBMITTED|UNKNOWN, txn_id, approval_ref, code, txn_ref, text}.
    Keys are matched without case; values are url-decoded. Junk or empty input -> UNKNOWN."""
    raw = (raw or "").strip()
    kv: dict[str, str] = {}
    for part in re.split(r"[&\n]", raw[:2000]):
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip().lower()] = unquote_plus(v.strip())[:120]
    st = (kv.get("status") or "").upper()
    if st in ("SUCCESS", "S"):
        status = "SUCCESS"
    elif st in ("FAILURE", "FAILED", "F", "FAIL"):
        status = "FAILURE"
    elif st in ("SUBMITTED", "PENDING"):
        status = "SUBMITTED"
    else:
        status = "UNKNOWN"
    code = (kv.get("responsecode") or kv.get("response_code") or "").upper()
    if status == "UNKNOWN" and code == "00" and kv.get("txnid"):
        status = "SUCCESS"
    return {"status": status, "txn_id": kv.get("txnid", ""), "code": code,
            "approval_ref": kv.get("approvalrefno") or kv.get("approvalref") or "",
            "txn_ref": kv.get("txnref") or kv.get("tr") or "", "text": raw[:300]}


def _tail(ref: str) -> str:
    ref = re.sub(r"\W", "", ref or "")
    return ref[-4:] if len(ref) >= 4 else ref


def card(txn: Transaction, ask: bool = False, reason: str = "", blocked: bool = False) -> dict[str, Any]:
    m = txn.meta or {}
    up = m.get("upi") or {}
    return {"txn_ref": txn.txn_ref, "status": txn.status, "amount": rupees(txn.amount_paise),
            "amount_paise": txn.amount_paise, "name": m.get("name", ""), "vpa": m.get("vpa", ""),
            "app": m.get("app", ""), "package": m.get("package", ""), "said_by": up.get("said_by", ""),
            "ref_tail": _tail(up.get("txn_id") or up.get("approval_ref") or ""),
            "ask": ask, "reason": reason, "blocked": blocked, "mode": m.get("mode", "")}


def _conv(s, txn: Transaction) -> str:
    from .service import _conv_of_txn
    return _conv_of_txn(s, txn)


def record(tenant_id: str, txn_ref: str, response: str = "", result: str = "", package: str = "",
           answer: str = "") -> dict[str, Any]:
    """The phone's report (response = the UPI app's string, result ok|cancelled|none) or her answer (done|not).
    Idempotent: a payment already completed by her word or the app is never undone by a late empty result."""
    answer = (answer or "").lower()
    if answer and answer not in ("done", "not", "blocked"):
        raise ToolError("answer must be done, not or blocked")
    with session() as s:
        txn = s.scalars(select(Transaction).where(Transaction.txn_ref == str(txn_ref)[:40])).first()
        if txn is None or txn.user_id != tenant_id:
            raise ToolError("Payment not found")
        if txn.kind != "upi":
            raise ToolError("Not a UPI transfer")
        m = dict(txn.meta or {})
        if package and not m.get("package"):
            m["package"] = package[:120]
        name, amt = m.get("name") or "unhe", rupees(txn.amount_paise)
        up = dict(m.get("upi") or {})
        reason, blocked, ask = "", False, False
        if answer == "blocked":
            # she saw the app refuse the link (or chose copy-and-pay): next time this app gets copy-and-pay at once
            _mark(s, txn.user_id, m.get("package", ""), "blocked")
            up["link_blocked"] = True
            m["upi"] = up
            txn.meta = m
            c = card(txn, ask=True, blocked=True)
            conv = _conv(s, txn)
            s.commit()
            if conv:
                bus.publish(conv, "upi_result", c)
            return {"txn_ref": c["txn_ref"], "status": c["status"], "say": "", "card": c}
        if answer:
            if txn.status in DONE and up.get("said_by") == "app" and answer == "not":
                # the app said success; her "nahi hua" is kept, but the record stays and she is told to check
                up["owner_doubt"] = True
                line = (f"UPI app ne {amt} {name} ko jaane ki baat kahi thi. Agar bank statement mein nahi dikh raha, "
                        f"UPI app ki history mein ref dekhiye.")
            elif answer == "done":
                txn.status = "completed"
                up.update(said_by="owner")
                line = f"Theek hai, {amt} {name} ko chale gaye ✅ (aapne bataya)."
            else:
                txn.status = "failed"
                up.update(said_by="owner")
                line = f"Theek hai, {amt} {name} ko nahi gaye. Dobara bhejna ho to bataiye."
        else:
            r = parse(response)
            if txn.status in DONE or (txn.status == "failed" and r["status"] != "SUCCESS"):
                return {"txn_ref": txn.txn_ref, "status": txn.status, "unchanged": True}
            if r["txn_ref"] and r["txn_ref"] != txn.txn_ref:
                log.warning("upi result ref mismatch: got %s for %s", r["txn_ref"][:40], txn.txn_ref)
                r["status"] = "UNKNOWN"
            up.update(said_by="app", status=r["status"], code=r["code"], txn_id=r["txn_id"],
                      approval_ref=r["approval_ref"], result=(result or "")[:20])
            if r["status"] == "SUCCESS":
                txn.status = "completed"
                txn.provider_ref = (r["approval_ref"] or r["txn_id"])[:80]
                if m.get("mode") != "copy":
                    _mark(s, txn.user_id, m.get("package", ""), "ok")   # the link worked in this app
                tail = _tail(r["approval_ref"] or r["txn_id"])
                line = f"{amt} {name} ko chale gaye ✅" + (f" (UPI ref ...{tail})" if tail else "") + "."
            elif r["status"] == "FAILURE":
                txn.status = "failed"
                reason, blocked = CODES.get(r["code"], ("", False))
                if not blocked and BLOCK_WORDS.search(response or ""):
                    blocked = True
                if not reason:
                    reason = "UPI app ne payment poori nahi ki"
                line = f"{amt} {name} ko nahi gaye: {reason}. Aapke account se kuch nahi kata."
                if blocked:
                    _mark(s, txn.user_id, m.get("package", ""), "blocked")
                    line += " Chahein to UPI ID copy karke app mein khud bhej sakti hain; agli baar ye app seedha aise hi khulega."
            elif r["status"] == "SUBMITTED":
                txn.status = "pending"
                ask = True
                line = (f"{amt} {name} ko bheja gaya, bank se pakka hona baaki hai ⏳. "
                        f"UPI app ki history mein dekhkar bataiye: ho gaya?")
            else:
                up["said_by"] = ""
                ask = True
                why = "aap app se wapas aa gayin" if result == "cancelled" else "UPI app ne kuch bataya nahi"
                line = f"{why.capitalize()}. {amt} {name} ko gaye ya nahi?"
                # some apps (personal transfers on GPay / PhonePe) return nothing when they refuse the link
                blocked = True
        m["upi"] = up
        txn.meta = m
        task = s.get(Task, txn.task_id) if txn.task_id else None
        if task and txn.status in DONE + ("failed",):
            task.status, task.reply = "done", line
        conv = _conv(s, txn)
        c = card(txn, ask=ask, reason=reason, blocked=blocked)
        s.commit()
    if conv:
        bus.publish(conv, "upi_result", c)
        notify(conv, line)
    return {"txn_ref": c["txn_ref"], "status": c["status"], "say": line, "card": c}


def copy_card(tenant_id: str, txn_ref: str) -> None:
    """Copy-and-pay mode: the app opens without a link; the card waits for her Ho gaya / Nahi hua."""
    with session() as s:
        txn = s.scalars(select(Transaction).where(Transaction.txn_ref == str(txn_ref)[:40])).first()
        if txn is None or txn.user_id != tenant_id:
            return
        c = card(txn, ask=True, blocked=False)
        conv = _conv(s, txn)
    if conv:
        bus.publish(conv, "upi_result", c)
