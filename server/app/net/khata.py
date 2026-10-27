"""v0.106 Khata (udhaar book) between Hoolas, kept on BOTH sides from the deals themselves.

Seller side (`side="seller"`, what others owe me): the owner opens a khata for one customer with a limit and days
(`open_account`). Only then can that customer choose "khata" in a quote (deal.terms shows the limit left) and the order
is checked against the limit again at accept. An accepted khata order is a debit; a cancel / dispute credit is a credit;
money she says she got (`received`) is a payment with a receipt R-number sent to the customer's Hoola.
Buyer side (`side="buyer"`, what I owe): a mirror written only from the seller's signed steps (deal accept on khata,
khata_receipt, khata_pay) - never from what the model says.

Kinds (EXTRA_KINDS, active link needed):
  khata_pay      seller -> buyer   {ref, amount, upi_id, name, balance}   a reminder / payment card for the khata balance
  khata_paid     buyer  -> seller  {ref, amount, utr}                     "maine bhej diya" (a claim)
  khata_receipt  seller -> buyer   {receipt, amount, mode, utr_tail, balance}
Money still only moves in the payer's own UPI app; the buyer's Hoola builds the upi:// link itself from the pinned payee.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import identity as idn
from . import policy
from .service import EXTRA_KINDS, NetError, _link, _post, resolve, tell

KHATA_KINDS = ("khata_pay", "khata_paid", "khata_receipt")
MAX_LIMIT = 50_00_000.0
REMIND_DAYS = 3              # one reminder this many days before / on / after the due date
STATS = {"opened": 0, "debits": 0, "payments": 0, "reminders": 0, "refused": 0}


class KhataError(NetError):
    pass


class KhataAccount(Base):
    """Seller side: a customer she gives udhaar to (limit + days)."""
    __tablename__ = "hoola_khata_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "peer", name="uq_hoola_khata_acct"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ka"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    peer: Mapped[str] = mapped_column(String(200))
    limit: Mapped[float] = mapped_column(Float, default=0.0)
    days: Mapped[int] = mapped_column(Integer, default=15)
    status: Mapped[str] = mapped_column(String(10), default="active")     # active | paused
    reminded: Mapped[str] = mapped_column(String(10), default="")          # the due date last reminded about
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KhataEntry(Base):
    """One line in the khata; `side` seller = they owe me, buyer = I owe them."""
    __tablename__ = "hoola_khata_entries"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ke"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    peer: Mapped[str] = mapped_column(String(200), index=True)
    side: Mapped[str] = mapped_column(String(8), default="seller")
    kind: Mapped[str] = mapped_column(String(8), default="debit")          # debit (more owed) | credit | payment
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    ref: Mapped[str] = mapped_column(String(60), default="")               # order number / receipt number
    due_on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KhataCard(Base):
    """Buyer side: the last khata payment card a seller's Hoola sent (cleared by their receipt)."""
    __tablename__ = "hoola_khata_cards"
    __table_args__ = (UniqueConstraint("tenant_id", "peer", name="uq_hoola_khata_card"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    peer: Mapped[str] = mapped_column(String(200))
    ref: Mapped[str] = mapped_column(String(30), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    upi_id: Mapped[str] = mapped_column(String(80), default="")
    name: Mapped[str] = mapped_column(String(80), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _card(tenant: str, peer: str) -> dict[str, Any] | None:
    with session() as s:
        c = s.scalars(select(KhataCard).where(KhataCard.tenant_id == tenant, KhataCard.peer == peer)).first()
        return {"ref": c.ref, "amount": c.amount, "upi_id": c.upi_id, "name": c.name} if c is not None and c.amount > 0 else None


def _set_card(tenant: str, peer: str, card: dict[str, Any] | None) -> None:
    with session() as s:
        c = s.scalars(select(KhataCard).where(KhataCard.tenant_id == tenant, KhataCard.peer == peer)).first()
        if card is None:
            if c is not None:
                s.delete(c)
            return
        if c is None:
            c = KhataCard(id=new_id("kc"), tenant_id=tenant, peer=peer)
            s.add(c)
        c.ref, c.amount, c.upi_id, c.name, c.at = card["ref"], card["amount"], card["upi_id"], card["name"], now()


def _r2(x: Any) -> float:
    return round(float(x or 0) + 0.0, 2)


def _who(peer: str) -> str:
    return idn.label(idn.peer_card(peer)) if peer else "Hoola"


def _peer(tenant: str, who: str) -> str:
    l0 = _link(tenant, (who or "").strip()) if (who or "").startswith("hl_") else None
    if l0 is not None and l0.status == "active":        # the app sends the peer's address back as it got it
        return who.strip()
    try:
        p = resolve(tenant, who)
    except NetError as e:
        raise KhataError(str(e)) from e
    l = _link(tenant, p)
    if l is None or l.status != "active":
        raise KhataError(f"{who} se Hoola connection nahi hai.")
    return p


# ---------------------------------------------------------------- book
def add(tenant: str, peer: str, kind: str, amount: float, ref: str, due_on: str = "", side: str = "seller",
        note: str = "") -> None:
    if amount <= 0:
        return
    kind = {"debit": "debit", "credit": "credit", "payment": "payment"}.get(kind, "debit")
    with session() as s:
        s.add(KhataEntry(id=new_id("ke"), tenant_id=tenant, peer=peer, side=side, kind=kind, amount=_r2(amount),
                         ref=str(ref or "")[:60], due_on=str(due_on or "")[:10], note=policy.quote(note, 200), at=now()))
    if kind == "debit":
        STATS["debits"] += 1


def balance(tenant: str, peer: str, side: str = "seller") -> float:
    with session() as s:
        rows = s.scalars(select(KhataEntry).where(KhataEntry.tenant_id == tenant, KhataEntry.peer == peer,
                                                  KhataEntry.side == side)).all()
        return _r2(sum(r.amount if r.kind == "debit" else -r.amount for r in rows))


def _due_on(tenant: str, peer: str, side: str) -> str:
    """The oldest due date of an order not yet covered by credits / payments (FIFO)."""
    with session() as s:
        rows = s.scalars(select(KhataEntry).where(KhataEntry.tenant_id == tenant, KhataEntry.peer == peer,
                                                  KhataEntry.side == side).order_by(KhataEntry.at)).all()
        paid = sum(r.amount for r in rows if r.kind != "debit")
        for r in rows:
            if r.kind != "debit":
                continue
            if paid + 0.01 >= r.amount:
                paid -= r.amount
                continue
            return r.due_on
    return ""


def _acct(tenant: str, peer: str) -> KhataAccount | None:
    with session() as s:
        a = s.scalars(select(KhataAccount).where(KhataAccount.tenant_id == tenant, KhataAccount.peer == peer)).first()
        if a is not None:
            s.expunge(a)
        return a


def offer(tenant: str, peer: str) -> dict[str, Any] | None:
    a = _acct(tenant, peer)
    if a is None or a.status != "active" or a.limit <= 0:
        return None
    return {"limit_left": _r2(max(0.0, a.limit - balance(tenant, peer, "seller"))), "days": int(a.days)}


def can_charge(tenant: str, peer: str, amount: float) -> bool:
    o = offer(tenant, peer)
    return bool(o) and o["limit_left"] + 0.01 >= float(amount or 0)


def open_account(tenant: str, who: str, limit: Any, days: Any = 15, status: str = "active") -> dict[str, Any]:
    """Owner only: give this customer udhaar up to `limit` for `days` (0 limit / paused stops new khata orders)."""
    peer = _peer(tenant, who)
    try:
        lim, dys = float(limit), int(days or 15)
    except (TypeError, ValueError) as e:
        raise KhataError("Seema (rupaye) aur din number mein likhiye.") from e
    if not (0 <= lim <= MAX_LIMIT) or not (1 <= dys <= 365):
        raise KhataError("Seema 0 se 50 lakh tak, din 1 se 365 tak.")
    with session() as s:
        a = s.scalars(select(KhataAccount).where(KhataAccount.tenant_id == tenant, KhataAccount.peer == peer)).first()
        if a is None:
            a = KhataAccount(id=new_id("ka"), tenant_id=tenant, peer=peer, created_at=now())
            s.add(a)
            STATS["opened"] += 1
        a.limit, a.days, a.status = _r2(lim), dys, "paused" if status == "paused" else "active"
    return account_view(tenant, peer, "seller")


def entries(tenant: str, peer: str, side: str, limit: int = 30) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(KhataEntry).where(KhataEntry.tenant_id == tenant, KhataEntry.peer == peer,
                                                  KhataEntry.side == side).order_by(KhataEntry.at.desc()).limit(limit)).all()
        return [{"kind": r.kind, "amount": r.amount, "ref": r.ref, "due_on": r.due_on, "note": r.note,
                 "at": r.at.isoformat() if r.at else ""} for r in rows]


def account_view(tenant: str, peer: str, side: str) -> dict[str, Any]:
    a = _acct(tenant, peer) if side == "seller" else None
    bal = balance(tenant, peer, side)
    due = _due_on(tenant, peer, side) if bal > 0 else ""
    return {"peer": peer, "with": _who(peer), "side": side, "balance": bal, "due_on": due,
            "overdue": bool(due and due < date.today().isoformat()),
            "limit": a.limit if a else 0, "days": a.days if a else 0, "status": a.status if a else "",
            "limit_left": _r2(max(0.0, a.limit - bal)) if a else 0, "entries": entries(tenant, peer, side, 10)}


def book(tenant: str) -> dict[str, Any]:
    """Both lists: who owes me (seller side) and whom I owe (buyer side)."""
    with session() as s:
        pairs = set(s.execute(select(KhataEntry.peer, KhataEntry.side).where(KhataEntry.tenant_id == tenant)).all())
        accts = s.scalars(select(KhataAccount.peer).where(KhataAccount.tenant_id == tenant)).all()
    pairs |= {(p, "seller") for p in accts}
    rows = [account_view(tenant, p, side) for p, side in sorted(pairs)]
    owed = [r for r in rows if r["side"] == "seller"]
    owe = [r for r in rows if r["side"] == "buyer"]
    return {"owed_to_me": owed, "i_owe": owe, "owed_total": _r2(sum(r["balance"] for r in owed if r["balance"] > 0)),
            "owe_total": _r2(sum(r["balance"] for r in owe if r["balance"] > 0))}


# ---------------------------------------------------------------- seller: ask for / record khata money
def request(tenant: str, who: str, amount: Any = None) -> dict[str, Any]:
    from . import dealpay
    peer = _peer(tenant, who)
    bal = balance(tenant, peer, "seller")
    if bal <= 0:
        raise KhataError(f"{_who(peer)} ka khata saaf hai.")
    pe = dealpay.payee(tenant)
    if not pe:
        raise KhataError("Pehle apna UPI ID daaliye (Khareed aur bikri > Niyam).")
    try:
        amt = bal if amount in (None, "", 0) else _r2(float(amount))
    except (TypeError, ValueError) as e:
        raise KhataError("Rakam number mein.") from e
    if not (0 < amt <= bal + 0.01):
        raise KhataError(f"Rakam {bal:,.2f} tak (itna baaki hai).")
    ref = new_id("kr")[:20]
    r = _post(tenant, peer, "khata_pay", {"ref": ref, "amount": amt, "upi_id": pe["upi_id"], "name": pe["name"],
                                          "balance": bal, "business_verified": pe["business_verified"]}, new_id("tk"))
    if not r.get("ok"):
        raise KhataError(f"{_who(peer)} tak nahi pahuncha: {r.get('reason') or r.get('status')}")
    STATS["reminders"] += 1
    return {"status": "requested", "amount": amt, "say": f"{_who(peer)} ko khata ke Rs {amt:,.2f} ka payment card bheja."}


def received(tenant: str, who: str, amount: Any, mode: str = "upi", utr: str = "") -> dict[str, Any]:
    """Owner: money for the khata came (she checked her bank / cash in hand) -> receipt to the customer."""
    from . import deal as dl
    from .dealpay import UTR_RE
    peer = _peer(tenant, who)
    bal = balance(tenant, peer, "seller")
    try:
        amt = _r2(float(amount))
    except (TypeError, ValueError) as e:
        raise KhataError("Rakam number mein.") from e
    if not (0 < amt <= max(bal, 0) + 0.01):
        raise KhataError(f"Khata mein Rs {bal:,.2f} baaki hai; isse zyada jama nahi.")
    if mode not in ("upi", "cash", "bank"):
        raise KhataError("mode: upi, cash, bank")
    utr = re.sub(r"\s", "", str(utr or ""))
    if utr and not UTR_RE.match(utr):
        raise KhataError("UTR / reference 10-22 akshar / ank ka hota hai.")
    with session() as s:
        r = s.get(dl.DealRules, tenant) or dl.DealRules(tenant_id=tenant)
        s.add(r)
        s.flush()
        no = f"R-{r.next_receipt:04d}"
        r.next_receipt += 1
    add(tenant, peer, "payment", amt, no, side="seller", note=mode)
    left = balance(tenant, peer, "seller")
    STATS["payments"] += 1
    sent = _post(tenant, peer, "khata_receipt", {"receipt": no, "amount": amt, "mode": mode, "utr_tail": utr[-6:],
                                                  "balance": left}, new_id("tk"))
    return {"status": "received", "receipt": no, "balance": left, "sent": bool(sent.get("ok")),
            "say": f"Khata mein Rs {amt:,.2f} jama ({no}). Baaki Rs {left:,.2f}."}


# ---------------------------------------------------------------- buyer: the payment card for a khata balance
def pay_link(tenant: str, who: str) -> dict[str, Any]:
    from urllib.parse import quote as q
    from .dealpay import PayeePin
    peer = _peer(tenant, who)
    rq = _card(tenant, peer)
    if not rq:
        raise KhataError("Is dukaan ka koi khata payment card nahi hai.")
    with session() as s:
        pin = s.scalars(select(PayeePin).where(PayeePin.tenant_id == tenant, PayeePin.peer == peer)).first()
        pinned = pin.upi_id if pin else ""
    out = {"amount": rq["amount"], "upi_id": rq["upi_id"], "name": rq["name"], "with": _who(peer)}
    if not pinned:
        out["status"] = "new_payee"
        return out
    if pinned.lower() != rq["upi_id"].lower():
        out |= {"status": "payee_changed", "was": pinned}
        return out
    out |= {"status": "ok", "url": f"upi://pay?pa={q(rq['upi_id'])}&pn={q(rq['name'])}&am={rq['amount']:.2f}&cu=INR"
                                   f"&tn={q('Khata')}&tr={q(rq['ref'])}"}
    return out


def trust_payee(tenant: str, who: str) -> dict[str, Any]:
    """Her tap: the UPI ID on this khata card is right (first time, or after a change she checked)."""
    from .dealpay import PayeePin
    peer = _peer(tenant, who)
    rq = _card(tenant, peer)
    if not rq:
        raise KhataError("Is dukaan ka koi khata payment card nahi hai.")
    with session() as s:
        p = s.scalars(select(PayeePin).where(PayeePin.tenant_id == tenant, PayeePin.peer == peer)).first()
        if p is None:
            p = PayeePin(id=new_id("pp"), tenant_id=tenant, peer=peer, upi_id=rq["upi_id"])
            s.add(p)
        p.upi_id, p.name, p.pinned_at = rq["upi_id"], rq["name"], now()
    return pay_link(tenant, who)


def claim_paid(tenant: str, who: str, utr: str = "") -> dict[str, Any]:
    from .dealpay import UTR_RE
    peer = _peer(tenant, who)
    rq = _card(tenant, peer)
    if not rq:
        raise KhataError("Is dukaan ka koi khata payment card nahi hai.")
    utr = re.sub(r"\s", "", str(utr or ""))
    if utr and not UTR_RE.match(utr):
        raise KhataError("UTR / UPI reference 12 ank ka hota hai.")
    r = _post(tenant, peer, "khata_paid", {"ref": rq["ref"], "amount": rq["amount"], "utr": utr}, new_id("tk"))
    if not r.get("ok"):
        raise KhataError(r.get("reason") or "nahi pahuncha")
    return {"status": "claimed", "say": "Dukaan ko bata diya; unke 'paisa mila' kehne par rasid aayegi."}


# ---------------------------------------------------------------- receiving

def receive(tenant: str, env: dict[str, Any], card: dict[str, Any], link, rules_: dict[str, Any]) -> dict[str, Any]:
    kind, raw, peer = env["kind"], env.get("body") or {}, env["from"]
    if policy.secret_found(policy.all_text(raw)):
        STATS["refused"] += 1
        return {"ok": False, "status": "refused", "reason": "mana ki gayi jaankari"}
    who = idn.label(card)
    try:
        amt = _r2(float(raw.get("amount")))
    except (TypeError, ValueError):
        return {"ok": False, "status": "refused", "reason": "rakam galat"}
    if not (0 < amt <= MAX_LIMIT):
        return {"ok": False, "status": "refused", "reason": "rakam galat"}
    if kind == "khata_pay":                     # buyer side: only up to what MY mirror says I owe them
        from .share import VPA_RE
        mine = balance(tenant, peer, "buyer")
        vpa = str(raw.get("upi_id") or "")
        if amt > mine + 0.01 or not VPA_RE.match(vpa):
            STATS["refused"] += 1
            return {"ok": False, "status": "refused", "reason": f"hamare hisaab se khata Rs {mine:,.2f} hai"}
        _set_card(tenant, peer, {"ref": policy.clean_name(raw.get("ref"), 30), "amount": amt, "upi_id": vpa,
                                 "name": policy.clean_name(raw.get("name"), 80)})
        tell(tenant, "hoola_khata", account_view(tenant, peer, "buyer") | {"card": "pay", "amount": amt, "upi_id": vpa,
                                                                            "say": f"{who}: khata ke Rs {amt:,.2f} (aapke hisaab se Rs {mine:,.2f} baaki). 'Pay' se aapka UPI app khulega."},
             f"{who} ne khata ka payment card bheja: Rs {amt:,.2f}. Paisa sirf owner apne UPI app se bhejegi.")
        return {"ok": True, "status": "shown"}
    if kind == "khata_paid":                    # seller side: a claim; she confirms with 'received'
        from .dealpay import galla_hint
        tell(tenant, "hoola_khata", account_view(tenant, peer, "seller") | {"card": "money", "amount": amt,
                                                                             "say": f"{who} keh rahe hain khata ke Rs {amt:,.2f} bhej diye" + (f" (UTR {raw.get('utr')})" if raw.get("utr") else "") + ". Bank / UPI mein dekh kar 'Paisa mila' dabaiye." + galla_hint(tenant, amt)},
             f"{who} ka kehna: khata ke Rs {amt:,.2f} bheje. Yeh sirf unka kehna hai; owner dekh kar hi 'paisa mila' kahe.")
        return {"ok": True, "status": "claimed"}
    if kind == "khata_receipt":                 # buyer side: the mirror gets the payment
        mine = balance(tenant, peer, "buyer")
        if amt > mine + 0.01:
            return {"ok": False, "status": "refused", "reason": "rasid khata se zyada"}
        no = policy.clean_name(raw.get("receipt"), 20)
        add(tenant, peer, "payment", amt, no, side="buyer", note=str(raw.get("mode") or "")[:8])
        _set_card(tenant, peer, None)
        tell(tenant, "hoola_khata", account_view(tenant, peer, "buyer") | {"card": "receipt", "amount": amt,
                                                                            "say": f"{who} ne khata ke Rs {amt:,.2f} ki rasid di ({no}). Baaki Rs {balance(tenant, peer, 'buyer'):,.2f}."})
        return {"ok": True, "status": "received"}
    return {"ok": False, "status": "refused", "reason": "unknown"}


def tick() -> int:
    """One reminder per due date to the seller (and the buyer's own Hoola) a few days before / when it is due."""
    n = 0
    soon = (date.today() + timedelta(days=REMIND_DAYS)).isoformat()
    with session() as s:
        accts = s.scalars(select(KhataAccount)).all()
        for a in accts:
            s.expunge(a)
    for a in accts:
        try:
            bal = balance(a.tenant_id, a.peer, "seller")
            due = _due_on(a.tenant_id, a.peer, "seller") if bal > 0 else ""
            if not due or due > soon or a.reminded == due:
                continue
            with session() as s:
                row = s.get(KhataAccount, a.id)
                row.reminded = due
            late = due < date.today().isoformat()
            tell(a.tenant_id, "hoola_khata", account_view(a.tenant_id, a.peer, "seller") | {"card": "due",
                 "say": f"{_who(a.peer)} ka khata Rs {bal:,.2f} {'ki taareekh ' + due + ' nikal gayi' if late else due + ' tak dena hai'}. "
                        "Payment card bhejun?"})
            n += 1
        except Exception:
            continue
    return n


for _k in KHATA_KINDS:
    EXTRA_KINDS[_k] = receive
