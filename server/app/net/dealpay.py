"""v0.106 Hoola Deals, phase 3: money, cancel requests, the buyer's check after handover, and disputes - all as signed
steps of the same deal (same step chain + state machine as deal.py).

Money rules (from the research report: UPI P2P collect ended 1 Oct 2025; payment status only from the payee, never a
screenshot; the payer starts the payment in their own app):
  * A payment request (`deal_pay`) is LOCKED to the deal: the amount is what is still due (total - paid) unless the
    seller marks it a part payment, and the buyer's Hoola refuses any other amount. The buyer's Hoola builds the
    `upi://pay` link itself from the checked fields (pa, pn, am, tn = order number, tr = request ref); a link string
    from the other side is never used. The buyer pays in their own UPI app; Hoola never pays.
  * Verified payee: the seller's UPI ID comes only from the seller's own settings (and is shown with the operator's
    verified-business badge when the business is verified). The buyer's Hoola pins the first payee per seller
    (`PayeePin`); a NEW payee is shown as new, a CHANGED payee is blocked until the buyer taps "naya UPI sahi hai".
  * "Maine pay kiya" (`deal_paid`, with the UTR) is only a claim. Money counts as received only when the seller says so
    (`deal_receipt`, her tap / her words as owner); her Galla UPI alerts are shown as a hint ("₹X 10:42 par aaya").
  * At handover the money must be settled first (Mere Niyam selling.pay_before = handover, default): paid, on khata, or
    collected at the counter right then (cash / UPI amount == what is due -> receipt).
Cancel: free for the buyer until the seller accepts and for `cancel_minutes` (her terms, default 30) after; later the
buyer's cancel becomes a request the seller answers. Money already paid becomes refund_due on both sides until the seller
records the refund (`deal_refund` with the UTR).
After handover the buyer's Hoola asks "sab sahi mila?": Haan -> closed; or a dispute inside `dispute_hours` (default
48): reason + which lines + note -> the seller answers (refund / credit to khata / replace / reject) -> the buyer
accepts (closed) or escalates (official routes named: National Consumer Helpline 1915 / e-Daakhil). Timers (tick)
remind once each: unaccepted orders auto-cancel on the buyer's side after 6 h, open payment requests, unanswered
cancel requests / disputes, and an unclosed handover closes by itself when the dispute window ends.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import identity as idn
from . import policy

STEP_KINDS = {"deal_pay", "deal_paid", "deal_receipt", "deal_refund", "deal_cancel_req", "deal_cancel_no", "deal_ok",
              "deal_dispute", "deal_resolve", "deal_dispute_close", "deal_escalate"}
PAY_OPTIONS = ("upi", "counter", "khata")
UTR_RE = re.compile(r"^[A-Za-z0-9]{10,22}$")
REASONS = {"short": "kam aaya", "damaged": "toota / kharab", "wrong": "galat cheez", "expired": "expiry nikal gayi",
           "price": "daam galat laga", "other": "kuch aur"}
RESOLVES = {"refund": "paise wapas", "credit": "khata mein jama", "replace": "badal kar denge", "reject": "shikayat nahi maani"}
CONFIRM_WAIT_H = 6            # the buyer's Hoola cancels an order nobody accepted in 6 hours (warns at 3)
PAY_REMIND_H = 24
CLAIM_REMIND_H = 6
CANCEL_REQ_REMIND_H = 2
DISPUTE_REMIND_H = 24
DISPUTE_ESCALATE_H = 72
OFFICIAL = ("National Consumer Helpline 1915 (ya WhatsApp 8800001915) / consumerhelpline.gov.in, aur zaroorat ho to "
            "e-Daakhil (edaakhil.nic.in) par consumer complaint")
STATS = {"requests": 0, "claims": 0, "receipts": 0, "refunds": 0, "disputes": 0, "auto_cancels": 0, "payee_changed": 0}


class PayeePin(Base):
    """The buyer's side: which UPI ID this seller's payments went to before (a changed one waits for her tap)."""
    __tablename__ = "hoola_payee_pins"
    __table_args__ = (UniqueConstraint("tenant_id", "peer", name="uq_hoola_payee_pin"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    peer: Mapped[str] = mapped_column(String(200))
    upi_id: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(80), default="")
    pinned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _dl():
    from . import deal as dl
    return dl


def _r2(x: Any) -> float:
    return round(float(x or 0) + 0.0, 2)


def _vpa_ok(v: str) -> bool:
    from .share import VPA_RE
    return bool(VPA_RE.match(v or ""))


def _left(d) -> float:
    p = d.pay or {}
    return max(0.0, _r2(float(p.get("due") or 0) - float(p.get("paid") or 0)))


# ---------------------------------------------------------------- the seller's terms in every quote
def payee(tenant: str) -> dict[str, Any]:
    dl = _dl()
    r = dl.rules(tenant)
    if not r.upi_id:
        return {}
    verified = False
    try:
        from .business import _biz
        b = _biz(tenant)
        verified = bool(b and b.verification == "verified")
    except Exception:
        pass
    return {"upi_id": r.upi_id, "name": r.payee_name or idn.my_card(tenant).get("owner_name", ""), "business_verified": verified}


def set_payee(tenant: str, upi_id: str, name: str = "") -> dict[str, Any]:
    """Only from her own settings (owner): the UPI ID her buyers' Hoolas will pay to."""
    dl = _dl()
    v = (upi_id or "").strip()
    if v and not _vpa_ok(v):
        raise dl.DealError("UPI ID aisa hota hai: naam@bank (jaise sharma.traders@okhdfcbank)")
    with session() as s:
        r = s.get(dl.DealRules, tenant) or dl.DealRules(tenant_id=tenant)
        s.add(r)
        r.upi_id, r.payee_name = v, policy.clean_name(name, 80)
    return payee(tenant)


def terms_for(tenant: str, peer: str, total: float) -> dict[str, Any]:
    dl = _dl()
    so = dl.selling(tenant)
    opts = []
    pe = payee(tenant)
    if pe:
        opts.append("upi")
    if so.get("counter_ok", True):
        opts.append("counter")
    if so.get("khata"):
        from . import khata
        off = khata.offer(tenant, peer)
        if off and off["limit_left"] >= total:
            opts.append("khata")
    if not opts:
        opts = ["counter"]
    t = {"pay_options": opts, "pay_before": so.get("pay_before", "handover"),
         "cancel_minutes": int(so.get("cancel_minutes", 30)), "dispute_hours": int(so.get("dispute_hours", 48)), "payee": pe}
    if "khata" in opts:
        from . import khata
        t["khata"] = khata.offer(tenant, peer)
    return t


def check_terms(raw: Any, total: float) -> dict[str, Any]:
    dl = _dl()
    raw = raw if isinstance(raw, dict) else {}
    opts = [o for o in (raw.get("pay_options") or []) if o in PAY_OPTIONS]
    opts = list(dict.fromkeys(opts)) or ["counter"]
    pe = raw.get("payee") if isinstance(raw.get("payee"), dict) else {}
    payee_ = {}
    if pe.get("upi_id"):
        if not _vpa_ok(str(pe["upi_id"])):
            raise dl.DealError("payee UPI ID galat")
        payee_ = {"upi_id": str(pe["upi_id"]), "name": policy.clean_name(pe.get("name"), 80),
                  "business_verified": bool(pe.get("business_verified"))}
    if "upi" in opts and not payee_:
        opts.remove("upi")
        opts = opts or ["counter"]
    t = {"pay_options": opts, "pay_before": raw.get("pay_before") if raw.get("pay_before") in ("handover", "none") else "handover",
         "cancel_minutes": int(dl._num(raw.get("cancel_minutes"), 0, 1440) or 0),
         "dispute_hours": int(dl._num(raw.get("dispute_hours"), 1, 720) or 48), "payee": payee_}
    if "khata" in opts:
        k = raw.get("khata") if isinstance(raw.get("khata"), dict) else {}
        left, days = dl._num(k.get("limit_left"), 0, dl.MAX_TOTAL), dl._num(k.get("days"), 1, 365)
        if left is None or days is None or left + 0.01 < total:
            opts.remove("khata")
        else:
            t["khata"] = {"limit_left": _r2(left), "days": int(days)}
    return t


# ---------------------------------------------------------------- accept / cancel hooks (called from deal.py)
def at_accept(tenant: str, d) -> dict[str, Any]:
    dl = _dl()
    q = d.quote or {}
    total = float(q.get("total") or 0)
    choice = (d.pay or {}).get("choice") or "counter"
    due_on = ""
    if choice == "khata":
        from . import khata
        if not khata.can_charge(tenant, d.peer, total):
            raise dl.DealError("Is graahak ki khata seema paar ho jaayegi. Seema badhaiye, ya UPI / counter par lene ko kahiye.")
        days = int(((q.get("terms") or {}).get("khata") or {}).get("days") or khata.offer(tenant, d.peer)["days"])
        due_on = (now() + timedelta(days=days)).date().isoformat()
    pay = {"choice": choice, "status": "khata" if choice == "khata" else "due", "due": _r2(total), "paid": 0.0,
           "payee": (q.get("terms") or {}).get("payee") or {}, "requests": [], "claims": [], "receipts": [], "refunds": [],
           "refund_due": 0.0, "due_on": due_on}
    return {"pay": pay, "body": {"pay": choice, **({"due_on": due_on} if due_on else {})}}


def after_accept(tenant: str, d) -> None:
    """Khata: the order goes into her khata book. UPI: the locked payment request goes by itself (a card, not money)."""
    p = d.pay or {}
    if p.get("choice") == "khata":
        from . import khata
        khata.add(tenant, d.peer, "debit", float(p.get("due") or 0), d.number, p.get("due_on", ""), side="seller")
    elif p.get("choice") == "upi" and (p.get("payee") or {}).get("upi_id"):
        try:
            request_payment(tenant, d.id, by="rules")
        except Exception:
            pass


def buyer_at_accept(tenant: str, d, raw: dict[str, Any]) -> dict[str, Any]:
    q = d.quote or {}
    choice = (d.pay or {}).get("choice") or raw.get("pay") or "counter"
    due_on = str(raw.get("due_on") or "")[:10] if choice == "khata" else ""
    pay = {"choice": choice, "status": "khata" if choice == "khata" else "due", "due": _r2(q.get("total")), "paid": 0.0,
           "payee": (q.get("terms") or {}).get("payee") or {}, "requests": [], "claims": [], "receipts": [], "refunds": [],
           "refund_due": 0.0, "due_on": due_on}
    if choice == "khata":
        from . import khata
        khata.add(tenant, d.peer, "debit", pay["due"], raw.get("number") or "", due_on, side="buyer")
    return pay


def cancel_needs_ok(d) -> bool:
    if d.role != "buyer" or d.state not in ("accepted", "packing") or d.accepted_at is None:
        return False
    mins = int(((d.quote or {}).get("terms") or {}).get("cancel_minutes") or 0)
    from .deal import _utc
    return now() > _utc(d.accepted_at) + timedelta(minutes=mins)


def after_cancel(tenant: str, deal_id: str) -> None:
    """Money already paid becomes refund_due; a khata order is taken back out of the khata (both sides)."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    p = dict(d.pay or {})
    if not p:
        return
    if p.get("status") == "khata" and not p.get("khata_reversed"):
        from . import khata
        khata.add(tenant, d.peer, "credit", float(p.get("due") or 0), d.number + " cancel", "", side=d.role)
        p["khata_reversed"] = True
    if float(p.get("paid") or 0) > 0:
        p["refund_due"] = _r2(float(p.get("paid") or 0) - sum(float(r.get("amount") or 0) for r in p.get("refunds") or []))
        p["status"] = "refund_due" if p["refund_due"] > 0 else p.get("status")
        p["refund_say"] = (f"{dl.inr(p['refund_due'])} wapas dena baaki hai (aap apne UPI se bhejiye, phir 'refund diya')."
                           if d.role == "seller" else f"{dl.inr(p['refund_due'])} wapas aana baaki hai.")
    d.pay = p
    dl._save(d)


# ---------------------------------------------------------------- the seller
def request_payment(tenant: str, deal_id: str, amount: Any = None, by: str = "owner") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if d.role != "seller":
        raise dl.DealError("Paise sirf bechne wala maangta hai.")
    p = dict(d.pay or {})
    if not p or p.get("status") in ("khata",):
        raise dl.DealError("Is order mein paise abhi nahi maange ja sakte (khata par hai ya order pakka nahi).")
    left = _left(d)
    if left <= 0:
        raise dl.DealError("Is order ka poora paisa mil chuka hai.")
    pe = payee(tenant)
    if not pe:
        raise dl.DealError("Pehle apna UPI ID daaliye (Khareed aur bikri > Niyam > UPI ID).")
    amt = left if amount in (None, "", 0) else dl._num(amount, 1, left + 0.001)
    if amt is None:
        raise dl.DealError(f"Rakam 1 se {dl.inr(left)} ke beech honi chahiye (jitna baaki hai).")
    amt = _r2(amt)
    ref = new_id("pr")[:20]
    body = {"ref": ref, "amount": amt, "upi_id": pe["upi_id"], "name": pe["name"], "number": d.number,
            "part": amt + 0.001 < left, "business_verified": pe["business_verified"]}
    p["requests"] = (p.get("requests") or []) + [{"ref": ref, "amount": amt, "at": now().isoformat(), "part": body["part"]}]
    p["status"], p["payee"] = "requested", {k: pe[k] for k in ("upi_id", "name", "business_verified")}
    d.pay = p
    dl._send(tenant, d, "deal_pay", body, f"Paise maange: {dl.inr(amt)}" + (" (aapke niyam se)" if by == "rules" else ""))
    STATS["requests"] += 1
    d = dl._get(tenant, deal_id)
    if by != "rules":
        dl._publish(tenant, d, "info", f"{dl._say_who(d.peer)} ko {dl.inr(amt)} ka payment card bheja (UPI {pe['upi_id']}).")
    return {"status": "requested", "amount": amt, "deal": dl.view(d)}


def received(tenant: str, deal_id: str, amount: Any = None, mode: str = "upi", utr: str = "", by: str = "owner") -> dict[str, Any]:
    """She says the money came (seen in her bank / UPI app / cash in hand) -> receipt to the buyer."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if d.role != "seller":
        raise dl.DealError("Paisa milne ki baat bechne wala kehta hai.")
    p = dict(d.pay or {})
    if not p:
        raise dl.DealError("Is order mein abhi paisa nahi bana.")
    left = _left(d)
    if left <= 0:
        raise dl.DealError("Is order ka poora paisa pehle hi mil chuka hai.")
    amt = left if amount in (None, "", 0) else dl._num(amount, 0.01, left + 0.001)
    if amt is None:
        raise dl.DealError(f"Rakam {dl.inr(left)} se zyada nahi ho sakti (itna hi baaki hai).")
    if mode not in ("upi", "cash", "bank"):
        raise dl.DealError("mode: upi, cash, bank")
    utr = re.sub(r"\s", "", str(utr or ""))
    if utr and not UTR_RE.match(utr):
        raise dl.DealError("UTR / reference 10-22 akshar / ank ka hota hai.")
    with session() as s:
        r = s.get(dl.DealRules, tenant) or dl.DealRules(tenant_id=tenant)
        s.add(r)
        s.flush()
        no = f"R-{r.next_receipt:04d}"
        r.next_receipt += 1
    amt = _r2(amt)
    paid = _r2(float(p.get("paid") or 0) + amt)
    body = {"receipt": no, "amount": amt, "mode": mode, "utr_tail": utr[-6:] if utr else "", "paid_total": paid,
            "due_left": _r2(max(0.0, float(p.get("due") or 0) - paid)), "number": d.number, "at": now().isoformat()}
    p["paid"], p["receipts"] = paid, (p.get("receipts") or []) + [body]
    p["status"] = "paid" if body["due_left"] <= 0 else "part_paid"
    d.pay = p
    dl._send(tenant, d, "deal_receipt", body, f"Paisa mila {dl.inr(amt)} ({mode}), rasid {no}")
    STATS["receipts"] += 1
    d = dl._get(tenant, deal_id)
    dl._publish(tenant, d, "info", f"Order {d.number}: {dl.inr(amt)} mila, rasid {no} graahak ko gayi." +
                (f" Baaki {dl.inr(body['due_left'])}." if body["due_left"] > 0 else ""))
    return {"status": p["status"], "receipt": no, "deal": dl.view(d)}


def refund(tenant: str, deal_id: str, amount: Any = None, utr: str = "") -> dict[str, Any]:
    """She sent money back from her own UPI / bank: the record goes to the buyer (Hoola never sends money)."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if d.role != "seller":
        raise dl.DealError("Refund bechne wala deta hai.")
    p = dict(d.pay or {})
    due = float(p.get("refund_due") or 0)
    if due <= 0:
        raise dl.DealError("Is order mein koi refund baaki nahi.")
    amt = due if amount in (None, "", 0) else dl._num(amount, 0.01, due + 0.001)
    if amt is None:
        raise dl.DealError(f"Refund {dl.inr(due)} tak hi.")
    utr = re.sub(r"\s", "", str(utr or ""))
    if utr and not UTR_RE.match(utr):
        raise dl.DealError("UTR / reference 10-22 akshar / ank ka hota hai.")
    amt = _r2(amt)
    body = {"amount": amt, "utr_tail": utr[-6:] if utr else "", "at": now().isoformat()}
    p["refunds"] = (p.get("refunds") or []) + [body]
    p["refund_due"] = _r2(due - amt)
    p["status"] = "refunded" if p["refund_due"] <= 0 else "refund_due"
    p["refund_say"] = "" if p["refund_due"] <= 0 else p.get("refund_say", "")
    d.pay = p
    dl._send(tenant, d, "deal_refund", body, f"Refund diya {dl.inr(amt)}")
    STATS["refunds"] += 1
    return {"status": p["status"], "deal": dl.view(dl._get(tenant, deal_id))}


def resolve(tenant: str, deal_id: str, action: str, amount: Any = None, note: str = "") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if d.role != "seller" or d.state != "disputed":
        raise dl.DealError("Khuli shikayat par hi jawab diya jaata hai.")
    if action not in RESOLVES:
        raise dl.DealError("action: refund, credit, replace, reject")
    p = dict(d.pay or {})
    amt = 0.0
    if action in ("refund", "credit"):
        cap = float(p.get("paid") or 0) if action == "refund" else float(p.get("due") or 0)
        if action == "refund" and cap <= 0:
            raise dl.DealError("Paisa abhi mila hi nahi; 'credit' (khata / agla bill) ya 'replace' chuniye.")
        a = dl._num(amount, 0.01, cap + 0.001)
        if a is None:
            raise dl.DealError(f"Rakam {dl.inr(cap)} tak.")
        amt = _r2(a)
    note = policy.quote(note, 400)
    if action == "reject" and not note:
        raise dl.DealError("Mana karne ki wajah likhiye (graahak ko dikhegi).")
    body = {"action": action, "amount": amt, "note": note}
    d.dispute = dict(d.dispute or {}, answer=body, answered_at=now().isoformat())
    if action == "refund":
        p["refund_due"] = _r2(float(p.get("refund_due") or 0) + amt)
        p["status"] = "refund_due"
        d.pay = p
    dl._send(tenant, d, "deal_resolve", body, f"Shikayat ka jawab: {RESOLVES[action]}" + (f" {dl.inr(amt)}" if amt else ""))
    if action == "credit":
        from . import khata
        khata.add(tenant, d.peer, "credit", amt, d.number + " shikayat", "", side="seller")
    return {"status": "answered", "deal": dl.view(dl._get(tenant, deal_id))}


def cancel_answer(tenant: str, deal_id: str, yes: bool, note: str = "") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if d.role != "seller" or (d.cancel_req or {}).get("status") != "waiting":
        raise dl.DealError("Koi cancel request baaki nahi.")
    if yes:
        d.cancel_req = dict(d.cancel_req, status="yes")
        dl._save(d)
        return dl.cancel(tenant, deal_id, "Graahak ki request par cancel")
    d.cancel_req = dict(d.cancel_req, status="no", note=policy.quote(note, 300))
    dl._send(tenant, d, "deal_cancel_no", {"note": policy.quote(note, 300)}, "Cancel request mana")
    return {"status": "declined", "deal": dl.view(dl._get(tenant, deal_id))}


def check_handover(tenant: str, d, collect: dict | None) -> None:
    """Money first (her Mere Niyam selling.pay_before = handover): paid, on khata, or collected now at the counter."""
    dl = _dl()
    p = d.pay or {}
    if not p or p.get("status") in ("khata",) or dl.selling(tenant).get("pay_before", "handover") == "none":
        return
    left = _left(d)
    if left <= 0:
        return
    if collect and isinstance(collect, dict):
        amt = dl._num(collect.get("amount"), 0.01, dl.MAX_TOTAL)
        if amt is None or abs(amt - left) > 0.01:
            raise dl.DealError(f"Counter par poora {dl.inr(left)} lena hai (likha {collect.get('amount')}).")
        received(tenant, d.id, left, str(collect.get("mode") or "cash"), str(collect.get("utr") or ""), by="counter")
        return
    raise dl.DealError(f"Pehle paisa: {dl.inr(left)} baaki hai. Counter par cash / UPI lijiye (collect), ya graahak ka "
                       "payment aane dijiye.")


# ---------------------------------------------------------------- the buyer
def _pin(tenant: str, peer: str) -> PayeePin | None:
    with session() as s:
        p = s.scalars(select(PayeePin).where(PayeePin.tenant_id == tenant, PayeePin.peer == peer)).first()
        if p is not None:
            s.expunge(p)
        return p


def _open_request(d) -> dict[str, Any] | None:
    p = d.pay or {}
    reqs = p.get("requests") or []
    if not reqs or p.get("status") not in ("requested", "part_paid", "claimed"):
        return None
    return reqs[-1]


def pay_link(tenant: str, deal_id: str) -> dict[str, Any]:
    """The buyer's UPI link, built HERE from checked fields; a new / changed payee needs her tap first."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if d.role != "buyer":
        raise dl.DealError("Payment khareedne wala karta hai.")
    rq = _open_request(d)
    if rq is None:
        raise dl.DealError("Is order mein abhi koi payment card nahi hai.")
    pe = (d.pay or {}).get("payee") or {}
    pin = _pin(tenant, d.peer)
    status = "ok"
    if pin is None:
        status = "new_payee"
    elif pin.upi_id.lower() != str(pe.get("upi_id", "")).lower():
        status = "payee_changed"
    from urllib.parse import quote as q
    url = (f"upi://pay?pa={q(pe.get('upi_id', ''))}&pn={q(pe.get('name', ''))}&am={rq['amount']:.2f}&cu=INR"
           f"&tn={q('Order ' + d.number)}&tr={q(rq['ref'])}")
    from . import trust
    vbc = (d.quote or {}).get("vbc") or {}
    out = {"status": status, "amount": rq["amount"], "upi_id": pe.get("upi_id"), "name": pe.get("name"),
           "business_verified": trust.payee_ok(vbc, str(pe.get("upi_id") or "")), "number": d.number,
           "verified_name": vbc.get("name", "") if vbc.get("ok") else ""}
    if status == "ok":
        out["url"] = url
    elif status == "payee_changed":
        out["was"] = pin.upi_id
        out["say"] = (f"Dhyan dein: {dl._say_who(d.peer)} ka UPI badla hai ({pin.upi_id} -> {pe.get('upi_id')}). Unse phone par "
                      "pakka kijiye, tabhi 'naya UPI sahi hai' dabaiye.")
    else:
        out["say"] = (f"Pehli baar {pe.get('upi_id')} ({pe.get('name')}) ko payment. UPI app mein naam milakar hi PIN daaliye.")
    return out


def trust_payee(tenant: str, deal_id: str) -> dict[str, Any]:
    """Her tap: this payee is right (first time, or after a change she checked)."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    pe = (d.pay or {}).get("payee") or {}
    if d.role != "buyer" or not pe.get("upi_id"):
        raise dl.DealError("Is order mein payee nahi hai.")
    with session() as s:
        p = s.scalars(select(PayeePin).where(PayeePin.tenant_id == tenant, PayeePin.peer == d.peer)).first()
        if p is None:
            p = PayeePin(tenant_id=tenant, peer=d.peer, upi_id=pe["upi_id"])
            s.add(p)
        p.upi_id, p.name, p.pinned_at = pe["upi_id"], pe.get("name", ""), now()
    return pay_link(tenant, deal_id)


def claim_paid(tenant: str, deal_id: str, utr: str = "") -> dict[str, Any]:
    """She paid in her UPI app: Hoola tells the seller (a claim; it counts only when the seller confirms)."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    rq = _open_request(d)
    if d.role != "buyer" or rq is None:
        raise dl.DealError("Is order mein koi payment card nahi hai.")
    utr = re.sub(r"\s", "", str(utr or ""))
    if utr and not UTR_RE.match(utr):
        raise dl.DealError("UTR / UPI reference 12 ank ka hota hai (UPI app mein payment ke details mein).")
    p = dict(d.pay or {})
    body = {"ref": rq["ref"], "amount": rq["amount"], "utr": utr}
    p["claims"] = (p.get("claims") or []) + [body | {"at": now().isoformat()}]
    p["status"] = "claimed"
    d.pay = p
    dl._send(tenant, d, "deal_paid", body, f"Maine {dl.inr(rq['amount'])} bheja" + (f" (UTR ..{utr[-4:]})" if utr else ""))
    STATS["claims"] += 1
    return {"status": "claimed", "say": "Dukaan ko bata diya; unke 'paisa mila' kehne par rasid aayegi.",
            "deal": dl.view(dl._get(tenant, deal_id))}


def all_ok(tenant: str, deal_id: str) -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if d.role != "buyer" or d.state != "handed_over":
        raise dl.DealError("Saamaan milne ke baad hi.")
    d.waiting = ""
    dl._send(tenant, d, "deal_ok", {"note": "sab sahi mila"}, "Sab sahi mila")
    return {"status": "closed", "deal": dl.view(dl._get(tenant, deal_id))}


def dispute(tenant: str, deal_id: str, reason: str, lines: Any = None, note: str = "") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if d.role != "buyer" or d.state != "handed_over":
        raise dl.DealError("Shikayat saamaan milne ke baad, aur sirf ek baar.")
    hrs = int(((d.quote or {}).get("terms") or {}).get("dispute_hours") or 48)
    from .deal import _utc
    if d.handed_at is not None and now() > _utc(d.handed_at) + timedelta(hours=hrs):
        raise dl.DealError(f"Shikayat ka samay ({hrs} ghante) nikal gaya. Dukaan se seedha baat kijiye.")
    if reason not in REASONS:
        raise dl.DealError("reason: " + ", ".join(REASONS))
    items = _clean_lines(d, lines)
    note = policy.quote(note, 600)
    if not items and not note:
        raise dl.DealError("Kya galat hai? Kaunsi cheez (kitni) ya do line mein bataiye.")
    body = {"reason": reason, "lines": items, "note": note}
    d.dispute, d.waiting = body | {"at": now().isoformat()}, ""
    dl._send(tenant, d, "deal_dispute", body, f"Shikayat: {REASONS[reason]}")
    STATS["disputes"] += 1
    return {"status": "disputed", "say": "Shikayat dukaan ke Hoola ko gayi; jawab aate hi bataunga.",
            "deal": dl.view(dl._get(tenant, deal_id))}


def _clean_lines(d, lines: Any) -> list[dict[str, Any]]:
    dl = _dl()
    got = {dl.norm(l["item"]): l for l in (d.quote or {}).get("lines") or [] if l.get("qty")}
    out = []
    for x in (lines or [])[:dl.MAX_LINES] if isinstance(lines, list) else []:
        if not isinstance(x, dict):
            continue
        ln = got.get(dl.norm(x.get("item")))
        q = dl._num(x.get("qty"), 0, 1e6)
        if ln is None or q is None or q > float(ln["qty"]) + 1e-9:
            raise dl.DealError(f"'{x.get('item')}': order mein yeh cheez / itni maatra nahi thi.")
        out.append({"item": ln["item"], "qty": q})
    return out


def dispute_close(tenant: str, deal_id: str, accept: bool, note: str = "") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if d.role != "buyer" or d.state != "disputed" or not (d.dispute or {}).get("answer"):
        raise dl.DealError("Dukaan ka jawab aane ke baad hi.")
    note = policy.quote(note, 400)
    if accept:
        dl._send(tenant, d, "deal_dispute_close", {"note": note}, "Jawab maan liya")
        return {"status": "closed", "deal": dl.view(dl._get(tenant, deal_id))}
    d.dispute = dict(d.dispute, escalated=now().isoformat())
    dl._send(tenant, d, "deal_escalate", {"note": note}, "Jawab nahi maana")
    d = dl._get(tenant, deal_id)
    dl._publish(tenant, d, "info", f"Theek hai, record rakha hai (poori history card mein). Aage: {OFFICIAL}.")
    return {"status": "escalated", "official": OFFICIAL, "deal": dl.view(d)}


def cancel_request(tenant: str, deal_id: str, reason: str = "") -> dict[str, Any]:
    dl = _dl()
    d = dl._get(tenant, deal_id)
    if (d.cancel_req or {}).get("status") == "waiting":
        raise dl.DealError("Cancel request pehle se bheji hui hai; dukaan ke jawab ka intezaar.")
    reason = policy.quote(reason, 300) or "Nahi chahiye"
    d.cancel_req = {"by": "buyer", "reason": reason, "at": now().isoformat(), "status": "waiting"}
    dl._send(tenant, d, "deal_cancel_req", {"reason": reason}, "Cancel request: " + reason)
    return {"status": "cancel_requested", "say": "Free cancel ka samay nikal gaya tha; dukaan se cancel ki request bheji.",
            "deal": dl.view(dl._get(tenant, deal_id))}


# ---------------------------------------------------------------- receiving the steps
def receive_step(tenant: str, d, kind: str, raw: dict[str, Any], who: str, key) -> dict[str, Any]:
    dl = _dl()
    E = dl.DealError
    p = dict(d.pay or {})
    if kind == "deal_pay":                                       # buyer: a payment card, locked to what is due
        if not p:
            raise E("order pakka nahi")
        left = _left(d)
        amt = dl._num(raw.get("amount"), 0.01, dl.MAX_TOTAL)
        part = bool(raw.get("part"))
        if amt is None or amt > left + 0.01 or (not part and abs(amt - left) > 0.01):
            raise E(f"rakam deal se mel nahi khaati (baaki {left}, maanga {raw.get('amount')})")
        vpa, name = str(raw.get("upi_id") or ""), policy.clean_name(raw.get("name"), 80)
        if not _vpa_ok(vpa):
            raise E("UPI ID galat")
        ref = policy.clean_name(raw.get("ref"), 30)
        if not ref:
            raise E("ref chahiye")
        dl._record(d, kind, raw, "seller", f"Payment card: {dl.inr(amt)}")
        pin = _pin(tenant, d.peer)
        from . import trust                      # v0.107 only the checked credential can call this payee verified
        vbc = (d.quote or {}).get("vbc") or {}
        p["payee"] = {"upi_id": vpa, "name": name, "business_verified": trust.payee_ok(vbc, vpa)}
        p["requests"] = (p.get("requests") or []) + [{"ref": ref, "amount": _r2(amt), "at": now().isoformat(), "part": part}]
        p["status"] = "requested"
        d.pay, d.waiting = p, "pay"
        dl._save(d)
        warn = ""
        if vbc.get("ok") and vbc.get("upi") and str(vbc["upi"]).lower() != vpa.lower():
            warn = f" Dhyan dein: verified UPI {vbc['upi']} hai, yeh card {vpa} ka hai; pakka kiye bina pay mat kijiye."
        elif p["payee"]["business_verified"]:
            warn = " ✓ Verified business ka UPI (bank mein naam mila hua)."
        if pin is not None and pin.upi_id.lower() != vpa.lower():
            STATS["payee_changed"] += 1
            warn += f" Dhyan dein: UPI badla hai ({pin.upi_id} -> {vpa}); pakka kiye bina pay mat kijiye."
        elif pin is None:
            warn += " Pehli baar is UPI ko payment: naam milakar hi PIN daaliye."
        dl._publish(tenant, d, "pay", f"{who}: order {d.number} ka {dl.inr(amt)}" + (" (aadha / hissa)" if part else "") +
                    f" UPI {vpa} ({name}) par. 'Pay' dabane se aapka UPI app khulega; PIN aap hi daalenge.{warn}",
                    f"{who} ne order {d.number} ka payment card bheja: {dl.inr(amt)}. Paisa sirf owner apne UPI app se bhejegi; "
                    f"tum pay nahi kar sakte. deal_id={d.id}.")
        return {"ok": True, "status": "requested"}
    if kind == "deal_paid":                                      # seller: the buyer says she paid
        ref, utr = str(raw.get("ref") or ""), re.sub(r"\s", "", str(raw.get("utr") or ""))
        rq = next((r for r in p.get("requests") or [] if r.get("ref") == ref), None)
        amt = dl._num(raw.get("amount"), 0.01, dl.MAX_TOTAL)
        if rq is None or amt is None or abs(amt - float(rq["amount"])) > 0.01:
            raise E("yeh payment card hamara nahi / rakam alag")
        if utr and not UTR_RE.match(utr):
            raise E("UTR galat")
        dl._record(d, kind, raw, "buyer", f"Graahak: {dl.inr(amt)} bheja" + (f" (UTR ..{utr[-4:]})" if utr else ""))
        p["claims"] = (p.get("claims") or []) + [{"ref": ref, "amount": _r2(amt), "utr": utr, "at": now().isoformat()}]
        p["status"], d.pay, d.waiting = "claimed", p, "received"
        dl._save(d)
        hint = galla_hint(tenant, amt)
        dl._publish(tenant, d, "money", f"{who} keh rahe hain {dl.inr(amt)} bhej diya" + (f" (UTR {utr})" if utr else "") +
                    f". Apne bank / UPI app mein dekh kar 'Paisa mila' dabaiye.{hint}",
                    f"{who} ka kehna: order {d.number} ka {dl.inr(amt)} bheja. Yeh sirf unka kehna hai; owner apne UPI / bank mein "
                    f"dekh kar 'paisa mila' kahe tabhi rasid jaati hai. deal_id={d.id}.")
        return {"ok": True, "status": "claimed"}
    if kind == "deal_receipt":                                   # buyer: the seller's receipt
        amt = dl._num(raw.get("amount"), 0.01, dl.MAX_TOTAL)
        left = _left(d)
        no = policy.clean_name(raw.get("receipt"), 20)
        if amt is None or amt > left + 0.01 or not no or raw.get("mode") not in ("upi", "cash", "bank"):
            raise E("rasid galat")
        dl._record(d, kind, raw, "seller", f"Rasid {no}: {dl.inr(amt)}")
        paid = _r2(float(p.get("paid") or 0) + amt)
        rec = {"receipt": no, "amount": _r2(amt), "mode": raw["mode"], "utr_tail": policy.clean_name(raw.get("utr_tail"), 8),
               "at": now().isoformat()}
        p["paid"], p["receipts"] = paid, (p.get("receipts") or []) + [rec]
        p["status"] = "paid" if paid + 0.01 >= float(p.get("due") or 0) else "part_paid"
        d.pay = p
        if d.waiting == "pay":
            d.waiting = ""
        dl._save(d)
        dl._publish(tenant, d, "receipt", f"{who} ne {dl.inr(amt)} ki rasid di ({no})." +
                    (f" Baaki {dl.inr(_left(d))}." if p["status"] != "paid" else " Poora paisa jama."))
        return {"ok": True, "status": p["status"]}
    if kind == "deal_refund":                                    # buyer: money back recorded by the seller
        amt = dl._num(raw.get("amount"), 0.01, dl.MAX_TOTAL)
        if amt is None or amt > float(p.get("paid") or 0) + 0.01:
            raise E("refund rakam galat")
        dl._record(d, kind, raw, "seller", f"Refund {dl.inr(amt)}")
        p["refunds"] = (p.get("refunds") or []) + [{"amount": _r2(amt), "utr_tail": policy.clean_name(raw.get("utr_tail"), 8),
                                                     "at": now().isoformat()}]
        p["refund_due"] = _r2(max(0.0, float(p.get("refund_due") or 0) - amt))
        p["status"] = "refunded" if p["refund_due"] <= 0 else "refund_due"
        d.pay = p
        dl._save(d)
        dl._publish(tenant, d, "info", f"{who} ne {dl.inr(amt)} wapas bheja (unke hisaab se). Apne bank mein dekh lijiye.")
        return {"ok": True, "status": "refund"}
    if kind == "deal_cancel_req":                                # seller: cancel after the free window
        reason = policy.quote(raw.get("reason"), 300)
        dl._record(d, kind, raw, "buyer", "Cancel request: " + reason)
        d.cancel_req = {"by": "buyer", "reason": reason, "at": now().isoformat(), "status": "waiting"}
        d.waiting = "cancel_req"
        dl._save(d)
        dl._publish(tenant, d, "cancel_req", f"{who} order {d.number} cancel karna chahte hain: {reason}. Haan / Na?")
        return {"ok": True, "status": "cancel_requested"}
    if kind == "deal_cancel_no":                                 # buyer: the seller said no
        note = policy.quote(raw.get("note"), 300)
        dl._record(d, kind, raw, "seller", "Cancel mana" + (f": {note}" if note else ""))
        d.cancel_req = dict(d.cancel_req or {}, status="no", note=note)
        dl._save(d)
        dl._publish(tenant, d, "info", f"{who} ne cancel nahi maana" + (f": {note}" if note else "") + ". Order chalu hai.")
        return {"ok": True, "status": "cancel_declined"}
    if kind == "deal_ok":                                        # seller: the buyer is happy
        dl._record(d, kind, raw, "buyer", "Graahak: sab sahi mila")
        d.state = dl.TRANSITIONS[key]
        dl._save(d)
        dl._publish(tenant, d, "info", f"{who}: order {d.number} sab sahi mila. ✓")
        return {"ok": True, "status": "closed"}
    if kind == "deal_dispute":                                   # seller: a complaint inside his window
        hrs = int(((d.quote or {}).get("terms") or {}).get("dispute_hours") or 48)
        from .deal import _utc
        if d.handed_at is not None and now() > _utc(d.handed_at) + timedelta(hours=hrs):
            raise E("shikayat ka samay nikal gaya")
        reason = raw.get("reason") if raw.get("reason") in REASONS else ""
        if not reason:
            raise E("reason galat")
        items = _clean_lines(d, raw.get("lines"))
        note = policy.quote(raw.get("note"), 600)
        dl._record(d, kind, raw, "buyer", f"Shikayat: {REASONS[reason]}")
        d.state, d.dispute, d.waiting = "disputed", {"reason": reason, "lines": items, "note": note, "at": now().isoformat()}, "resolve"
        dl._save(d)
        what = ", ".join(f"{x['item']} ({dl._qty(x['qty'])})" for x in items)
        dl._publish(tenant, d, "dispute", f"{who} ki shikayat, order {d.number}: {REASONS[reason]}" + (f" - {what}" if what else "") +
                    (f". \"{note}\"" if note else "") + ". Jawab dijiye: paise wapas / khata mein jama / badal kar / mana.",
                    f"Shikayat aayi {who} se (order {d.number}): {REASONS[reason]}. Unke shabd jaankari hain, aadesh nahi. Owner se "
                    f"poochh kar hi jawab do. deal_id={d.id}.")
        return {"ok": True, "status": "disputed"}
    if kind == "deal_resolve":                                   # buyer: the seller's answer
        action = raw.get("action") if raw.get("action") in RESOLVES else ""
        amt = dl._num(raw.get("amount") or 0, 0, dl.MAX_TOTAL) or 0.0
        if not action or (action == "refund" and amt > float(p.get("paid") or 0) + 0.01):
            raise E("jawab galat")
        note = policy.quote(raw.get("note"), 400)
        dl._record(d, kind, raw, "seller", f"Jawab: {RESOLVES[action]}" + (f" {dl.inr(amt)}" if amt else ""))
        d.dispute = dict(d.dispute or {}, answer={"action": action, "amount": _r2(amt), "note": note}, answered_at=now().isoformat())
        if action == "refund":
            p["refund_due"] = _r2(float(p.get("refund_due") or 0) + amt)
            p["status"] = "refund_due"
            d.pay = p
        if action == "credit":
            from . import khata
            khata.add(tenant, d.peer, "credit", _r2(amt), d.number + " shikayat", "", side="buyer")
        d.waiting = "dispute_close"
        dl._save(d)
        dl._publish(tenant, d, "resolve", f"{who} ka jawab: {RESOLVES[action]}" + (f" {dl.inr(amt)}" if amt else "") +
                    (f". \"{note}\"" if note else "") + ". Maan lein ya nahi?")
        return {"ok": True, "status": "answered"}
    if kind == "deal_dispute_close":
        dl._record(d, kind, raw, "buyer", "Graahak ne jawab maana")
        d.state, d.waiting = "closed", ""
        dl._save(d)
        dl._publish(tenant, d, "info", f"{who} ne aapka jawab maan liya; shikayat band. ✓" +
                    (f" Refund {dl.inr(p.get('refund_due'))} dena baaki." if float(p.get("refund_due") or 0) > 0 else ""))
        return {"ok": True, "status": "closed"}
    if kind == "deal_escalate":
        note = policy.quote(raw.get("note"), 400)
        dl._record(d, kind, raw, "buyer", "Graahak ne jawab nahi maana")
        d.dispute = dict(d.dispute or {}, escalated=now().isoformat(), escalate_note=note)
        dl._save(d)
        dl._publish(tenant, d, "dispute", f"{who} ne aapka jawab nahi maana" + (f": \"{note}\"" if note else "") +
                    ". Doosra jawab de sakte hain; poori history dono taraf hai.")
        return {"ok": True, "status": "escalated"}
    raise E("unknown")


# ---------------------------------------------------------------- views
def actions(d) -> list[str]:
    p = d.pay or {}
    out = []
    if d.role == "buyer":
        if p.get("status") in ("requested", "part_paid") and p.get("requests") and _left(d) > 0:
            out += ["pay", "paid"]
        if d.state == "disputed" and (d.dispute or {}).get("answer") and not (d.dispute or {}).get("escalated"):
            out += ["dispute_close", "escalate"]
        return out
    if d.state in ("accepted", "packing", "ready", "handed_over", "disputed", "closed") and p and p.get("status") != "khata" \
            and _left(d) > 0:
        out += ["pay_request", "received"]
    if float(p.get("refund_due") or 0) > 0:
        out.append("refund")
    if d.state == "disputed" and not (d.dispute or {}).get("answer"):
        out.append("resolve")
    if d.state == "disputed" and (d.dispute or {}).get("escalated"):
        out.append("resolve")
    if (d.cancel_req or {}).get("status") == "waiting" and d.state in ("accepted", "packing"):
        out += ["cancel_yes", "cancel_no"]
    return list(dict.fromkeys(out))


def pay_view(d) -> dict[str, Any]:
    p = dict(d.pay or {})
    if not p:
        return {}
    p["due_left"] = _left(d)
    p["requests"] = (p.get("requests") or [])[-3:]
    p["claims"] = [dict(c, utr=("…" + str(c.get("utr") or "")[-4:]) if c.get("utr") else "") for c in (p.get("claims") or [])[-3:]] \
        if d.role == "buyer" else (p.get("claims") or [])[-3:]
    return p


def galla_hint(tenant: str, amount: float, within_h: int = 6) -> str:
    """Her own Galla (UPI alerts read on her phone, v0.84): a credit of this amount lately = a hint, never proof."""
    try:
        from ..galla.service import GallaEntry, _tz, _utc
        paise = int(round(float(amount) * 100))
        with session() as s:
            e = s.scalars(select(GallaEntry).where(GallaEntry.tenant_id == tenant, GallaEntry.void.is_(False),
                                                   GallaEntry.amount_paise == paise,
                                                   GallaEntry.at >= now() - timedelta(hours=within_h))
                          .order_by(GallaEntry.at.desc())).first()
            if e is None:
                return ""
            t = _utc(e.at).astimezone(_tz(tenant)).strftime("%H:%M")
            return f" (Aapke Galla mein {t} par itna hi UPI credit dikha" + (f", {e.payer}" if e.payer else "") + ".)"
    except Exception:
        return ""


def receipt_pdf(tenant: str, deal_id: str) -> bytes:
    """A plain receipt / bill from this side's own record (never a file the other side made)."""
    dl = _dl()
    d = dl._get(tenant, deal_id)
    q, p = d.quote or {}, d.pay or {}
    from io import BytesIO
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    w, h = A5
    seller = idn.my_card(tenant).get("owner_name", "") if d.role == "seller" else dl._say_who(d.peer)
    buyer = dl._say_who(d.peer) if d.role == "seller" else idn.my_card(tenant).get("owner_name", "")
    y = h - 40
    c.setFont("Helvetica-Bold", 13)
    c.drawString(30, y, f"Order {d.number or d.id}")
    c.setFont("Helvetica", 9)
    y -= 16
    c.drawString(30, y, f"Seller: {seller}"[:90])
    y -= 12
    c.drawString(30, y, f"Buyer: {buyer}"[:90])
    y -= 18
    for ln in q.get("lines") or []:
        if not ln.get("qty"):
            continue
        c.drawString(30, y, f"{ln['item']}"[:40])
        c.drawRightString(w - 120, y, f"{dl._qty(ln['qty'])} x {ln.get('price') or 0:.2f}")
        c.drawRightString(w - 30, y, f"{ln['amount'] + ln['gst']:.2f}")
        y -= 12
        if y < 120:
            c.showPage()
            y = h - 40
            c.setFont("Helvetica", 9)
    y -= 6
    c.drawRightString(w - 30, y, f"Subtotal {q.get('subtotal', 0):.2f}   GST {q.get('gst', 0):.2f}   Total Rs {q.get('total', 0):.2f}")
    y -= 18
    for r in p.get("receipts") or []:
        c.drawString(30, y, f"Receipt {r.get('receipt')}: Rs {float(r.get('amount') or 0):.2f} {r.get('mode', '')} "
                            f"{('ref ..' + r['utr_tail']) if r.get('utr_tail') else ''}  {str(r.get('at', ''))[:10]}")
        y -= 12
    c.drawString(30, y, f"Paid Rs {float(p.get('paid') or 0):.2f}   Due Rs {_left(d):.2f}" +
                 ("   (on khata)" if p.get("status") == "khata" else ""))
    y -= 22
    c.setFont("Helvetica-Oblique", 7)
    c.drawString(30, y, "Made by Hoola from the deal record. Not a GST tax invoice unless the seller issues one.")
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------- timers (once each)
def tick() -> int:
    dl = _dl()
    from .deal import Deal, _utc
    n = 0
    with session() as s:
        rows = s.scalars(select(Deal).where(Deal.state.in_(("confirmed", "accepted", "packing", "ready", "handed_over",
                                                                 "disputed", "cancelled", "closed")))).all()
        for r in rows:
            s.expunge(r)
    for d in rows:
        t = dict(d.timers or {})
        upd = (d.updated_at and _utc(d.updated_at)) or now()
        try:
            if d.role == "buyer" and d.state == "confirmed":
                age = now() - upd
                if age > timedelta(hours=CONFIRM_WAIT_H):
                    dl.cancel(d.tenant_id, d.id, f"{CONFIRM_WAIT_H} ghante mein order pakka nahi hua")
                    STATS["auto_cancels"] += 1
                    n += 1
                    continue
                if age > timedelta(hours=CONFIRM_WAIT_H / 2) and not t.get("confirm_warn"):
                    t["confirm_warn"] = 1
                    _timer_note(d, t, f"{dl._say_who(d.peer)} ne abhi order pakka nahi kiya. {CONFIRM_WAIT_H} ghante tak jawab na aaya "
                                      "to main khud cancel kar dunga.")
                    n += 1
                    continue
            p = d.pay or {}
            last_req = (p.get("requests") or [{}])[-1].get("at")
            if d.role == "buyer" and p.get("status") == "requested" and last_req and not t.get("pay_" + str(len(p.get("requests") or []))):
                if now() - dl._when(last_req) > timedelta(hours=PAY_REMIND_H):
                    t["pay_" + str(len(p.get("requests") or []))] = 1
                    _timer_note(d, t, f"Order {d.number} ka {dl.inr(_left(d))} abhi baaki hai (payment card upar hai).", card="pay")
                    n += 1
                    continue
            last_claim = (p.get("claims") or [{}])[-1].get("at")
            if d.role == "seller" and p.get("status") == "claimed" and last_claim and not t.get("claim_" + str(len(p.get("claims") or []))):
                if now() - dl._when(last_claim) > timedelta(hours=CLAIM_REMIND_H):
                    t["claim_" + str(len(p.get("claims") or []))] = 1
                    _timer_note(d, t, f"{dl._say_who(d.peer)} ne order {d.number} ka paisa bhejne ki baat ki thi; mila ho to 'Paisa mila' "
                                      "dabaiye, na mila ho to unse baat kijiye.", card="money")
                    n += 1
                    continue
            cr = d.cancel_req or {}
            if d.role == "seller" and cr.get("status") == "waiting" and not t.get("cancel_req") \
                    and now() - dl._when(cr.get("at")) > timedelta(hours=CANCEL_REQ_REMIND_H):
                t["cancel_req"] = 1
                _timer_note(d, t, f"{dl._say_who(d.peer)} ki cancel request ka jawab baaki hai (order {d.number}).", card="cancel_req")
                n += 1
                continue
            dp = d.dispute or {}
            if d.state == "disputed" and not dp.get("answer") and dp.get("at"):
                age = now() - dl._when(dp["at"])
                if d.role == "seller" and age > timedelta(hours=DISPUTE_REMIND_H) and not t.get("dispute_remind"):
                    t["dispute_remind"] = 1
                    _timer_note(d, t, f"Order {d.number} ki shikayat ka jawab {DISPUTE_REMIND_H} ghante se baaki hai.", card="dispute")
                    n += 1
                    continue
                if d.role == "buyer" and age > timedelta(hours=DISPUTE_ESCALATE_H) and not t.get("dispute_official"):
                    t["dispute_official"] = 1
                    _timer_note(d, t, f"Dukaan ne {DISPUTE_ESCALATE_H} ghante mein shikayat ka jawab nahi diya. Record aapke paas hai; "
                                      f"aage: {OFFICIAL}.")
                    n += 1
                    continue
            if d.state == "handed_over" and d.handed_at is not None:
                hrs = int(((d.quote or {}).get("terms") or {}).get("dispute_hours") or 48)
                if now() > _utc(d.handed_at) + timedelta(hours=hrs):
                    with session() as s2:                    # the window ended with no complaint: closed (no message needed)
                        row = s2.get(Deal, d.id)
                        if row is not None and row.state == "handed_over":
                            row.state, row.waiting, row.updated_at = "closed", "", now()
                    n += 1
        except Exception:
            continue
    return n


def _timer_note(d, t: dict[str, Any], say: str, card: str = "info") -> None:
    dl = _dl()
    with session() as s:
        row = s.get(dl.Deal, d.id)
        if row is not None:
            row.timers = t
    dl._publish(d.tenant_id, dl._get(d.tenant_id, d.id), card, say)
