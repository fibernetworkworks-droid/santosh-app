"""v0.105 Pick tasks: when an order is pakka, the seller's Hoola sends the pick list to the packers' own Hoolas.

Packers = her Hoola Employee team members on the Hoola Network who are managers or have the 'packing' duty (or the
names she wrote in Mere Niyam > selling.packers). The packer's avatar shows a card: what to pick, for which order.
The packer says "pack ho gaya" / "X kam hai" on their own Hoola -> `pick_update` back -> the seller's Hoola marks the
parcel ready by itself when her Mere Niyam allows (selling.auto_ready, default on) and the buyer gets the pickup code;
a shortage goes to HER as a card (never decided by the avatar). At the counter the packer types the code the buyer
shows into their own Hoola -> `pick_handover` -> the seller's Hoola checks it (the code is never sent to staff).

Kinds (EXTRA_KINDS, active link needed):
  pick_task      seller -> packer   {dkey, number, customer, lines:[{item, qty, unit}], mode, need_by, note}
  pick_note      seller -> packer   {dkey, status ready|handed_over|cancelled|taken, place, until, by}
  pick_update    packer -> seller   {dkey, status packing|packed|short, short:[{item, qty}], note}
  pick_handover  packer -> seller   {dkey, code}   (the answer says at once whether the code matched)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import identity as idn
from . import policy
from .service import EXTRA_KINDS, NetError, _post, tell

PICK_KINDS = ("pick_task", "pick_note", "pick_update", "pick_handover")
PER_DAY = 300
STATS = {"sent": 0, "packed": 0, "short": 0, "handover_ok": 0, "handover_wrong": 0, "refused": 0}


class PickTask(Base):
    """The packer's side: a pick list their workplace's Hoola sent."""
    __tablename__ = "hoola_pick_tasks"
    __table_args__ = (UniqueConstraint("tenant_id", "business", "dkey", name="uq_hoola_pick"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pk"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)          # the packer
    business: Mapped[str] = mapped_column(String(200), index=True)          # the seller's address
    dkey: Mapped[str] = mapped_column(String(60))
    number: Mapped[str] = mapped_column(String(30), default="")
    customer: Mapped[str] = mapped_column(String(160), default="")
    lines: Mapped[list] = mapped_column(JSON, default=list)
    mode: Mapped[str] = mapped_column(String(10), default="pickup")
    need_by: Mapped[str] = mapped_column(String(40), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(14), default="new")          # new|packing|packed|short|ready|handed_over|cancelled|taken
    short: Mapped[list] = mapped_column(JSON, default=list)
    place: Mapped[str] = mapped_column(String(200), default="")
    until: Mapped[str] = mapped_column(String(40), default="")
    collect: Mapped[float | None] = mapped_column(Float, nullable=True)      # v0.106 money to take at the counter (None = settled)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PickError(NetError):
    pass


# ---------------------------------------------------------------- seller side
def send_tasks(tenant: str, deal_id: str) -> list[str]:
    """After accept: the pick list goes to every packer's Hoola. Returns the names it reached."""
    from . import deal as dl
    d = dl._get(tenant, deal_id)
    people = dl.packers(tenant)
    if not people:
        return []
    lines = [{"item": l["item"], "qty": l["qty"], "unit": l.get("unit") or ""}
             for l in (d.quote or {}).get("lines") or [] if l.get("qty")]
    body = {"dkey": d.dkey, "number": d.number, "customer": dl._say_who(d.peer), "lines": lines,
            "mode": (d.ask or {}).get("mode", "pickup"), "need_by": (d.ask or {}).get("need_by", ""),
            "note": (d.ask or {}).get("note", "")}
    reached, to = [], []
    for p in people:
        r = _post(tenant, p["address"], "pick_task", body, new_id("tk"))
        if r.get("ok"):
            reached.append(p["name"])
            to.append(p["address"])
    if to:
        STATS["sent"] += 1
        d.pick = {"to": to, "names": reached, "status": "sent", "by": "", "short": [], "at": now().isoformat()}
        dl._save(d)
    return reached


def notify(tenant: str, deal_id: str, status: str, by: str = "") -> None:
    """Tell the packers what happened to the order (ready with place / time, handed over, cancelled, taken by X)."""
    from . import deal as dl
    try:
        d = dl._get(tenant, deal_id)
    except NetError:
        return
    to = list((d.pick or {}).get("to") or [])
    if not to:
        return
    rdy = d.ready or {}
    body = {"dkey": d.dkey, "status": status, "place": rdy.get("place", ""), "until": rdy.get("until", ""), "by": by[:80]}
    if status == "ready":                             # v0.106 what to take at the counter (0 = paid / on khata)
        from . import dealpay
        p = d.pay or {}
        body["collect"] = 0.0 if (not p or p.get("status") == "khata") else dealpay._left(d)
    for addr in to:
        try:
            _post(tenant, addr, "pick_note", body, new_id("tk"))
        except Exception:
            pass


def _deal_for(tenant: str, dkey: str, sender: str):
    from . import deal as dl
    with session() as s:
        d = s.scalars(select(dl.Deal).where(dl.Deal.tenant_id == tenant, dl.Deal.dkey == dkey, dl.Deal.role == "seller")).first()
        if d is not None:
            s.expunge(d)
    if d is None or sender not in ((d.pick or {}).get("to") or []):
        raise PickError("yeh pick list aapko nahi di gayi thi")
    from ..employee import service as emp
    m = emp.member_by_address(tenant, sender)
    if m is None:
        raise PickError("aap ab is team mein nahi hain")
    return d, m


def _on_update(tenant: str, env: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    from . import deal as dl
    body = env.get("body") or {}
    d, m = _deal_for(tenant, str(body.get("dkey") or ""), env["from"])
    st = body.get("status")
    if st not in ("packing", "packed", "short"):
        raise PickError("status galat")
    if d.state not in ("accepted", "packing"):
        raise PickError(f"order abhi '{dl.STATE_WORDS.get(d.state, d.state)}' hai")
    note = policy.quote(body.get("note"), 300)
    short = []
    if st == "short":
        for x in (body.get("short") or [])[:dl.MAX_LINES]:
            if isinstance(x, dict):
                q = dl._num(x.get("qty"), 0, 1e6)
                short.append({"item": policy.clean_name(x.get("item"), 120), "qty": q if q is not None else 0})
    d.pick = dict(d.pick or {}, status=st, by=m["name"], short=short, note=note, at=now().isoformat())
    dl._save(d)
    if st == "packing":
        if d.state == "accepted":
            dl.packing(tenant, d.id, f"{m['name']} pack kar rahe hain")
        _others(tenant, d, m)
        return {"ok": True, "status": "packing"}
    if st == "packed":
        STATS["packed"] += 1
        if dl.selling(tenant).get("auto_ready", True):
            dl.mark_ready(tenant, d.id, note=f"{m['name']} ne pack kiya")
            return {"ok": True, "status": "ready"}
        dl._publish(tenant, dl._get(tenant, d.id), "pack", f"{m['name']} ne order {d.number} pack kar diya. Graahak ko 'taiyaar' bhejun?")
        return {"ok": True, "status": "packed"}
    STATS["short"] += 1
    words = ", ".join(f"{x['item']} ({dl._qty(x['qty'])} hi mila)" if x["qty"] else f"{x['item']} (nahi mila)" for x in short) or note
    dl._publish(tenant, dl._get(tenant, d.id), "pack",
                f"{m['name']}: order {d.number} mein kam hai: {words}. Aap tay kijiye: graahak se baat, cancel, ya maal mangwa kar pack.",
                f"Packer {m['name']} ne order {d.number} mein kami batayi: {words}. Graahak ko kuch bhi kehne se pehle owner se poochho. deal_id={d.id}.")
    return {"ok": True, "status": "short"}


def _others(tenant: str, d, m: dict[str, Any]) -> None:
    """One packer took the order: the others' cards say so (no double packing)."""
    to = [a for a in (d.pick or {}).get("to") or [] if a != m.get("address")]
    for addr in to:
        try:
            _post(tenant, addr, "pick_note", {"dkey": d.dkey, "status": "taken", "by": m["name"]}, new_id("tk"))
        except Exception:
            pass


def _on_handover(tenant: str, env: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    from . import deal as dl
    body = env.get("body") or {}
    d, m = _deal_for(tenant, str(body.get("dkey") or ""), env["from"])
    try:
        col = body.get("collect") if isinstance(body.get("collect"), dict) else None     # v0.106 cash / UPI taken at the counter
        dl.handed_over(tenant, d.id, str(body.get("code") or ""), f"{m['name']} ne counter par diya", collect=col)
    except NetError as e:
        STATS["handover_wrong"] += 1
        return {"ok": False, "status": "refused", "reason": str(e)[:200]}
    STATS["handover_ok"] += 1
    return {"ok": True, "status": "handed_over"}


# ---------------------------------------------------------------- packer side
def view(p: PickTask) -> dict[str, Any]:
    acts = {"new": ["packing", "packed", "short"], "packing": ["packed", "short"], "short": ["packed"],
            "packed": [], "ready": ["handover"], "taken": [], "handed_over": [], "cancelled": []}.get(p.status, [])
    return {"id": p.id, "pick_id": p.id, "business": idn.label(idn.peer_card(p.business)), "number": p.number,
            "customer": p.customer, "lines": p.lines or [], "mode": p.mode, "need_by": p.need_by, "note": p.note,
            "status": p.status, "short": p.short or [], "place": p.place, "until": p.until, "actions": acts,
            "collect": p.collect or 0,
            "updated": p.updated_at.isoformat() if p.updated_at else ""}


def _tell(tenant: str, p: PickTask, card: str, say: str, note: str = "") -> None:
    tell(tenant, "hoola_pick", view(p) | {"card": card, "say": say},
         note or f"[Pick list] {view(p)['business']}: {say} pick_id={p.id}.")


def picks(tenant: str, open_only: bool = True) -> list[dict[str, Any]]:
    with session() as s:
        q = select(PickTask).where(PickTask.tenant_id == tenant)
        if open_only:
            q = q.where(PickTask.status.in_(("new", "packing", "short", "packed", "ready")))
        rows = s.scalars(q.order_by(PickTask.updated_at.desc()).limit(100)).all()
        return [view(r) for r in rows]


def _mine(tenant: str, pick_id: str) -> PickTask:
    with session() as s:
        p = s.get(PickTask, pick_id)
        if p is None or p.tenant_id != tenant:
            p = s.scalars(select(PickTask).where(PickTask.tenant_id == tenant, PickTask.number == pick_id)
                          .order_by(PickTask.updated_at.desc())).first()
        if p is None:
            raise PickError("Yeh pick list nahi mili.")
        s.expunge(p)
        return p


def mark(tenant: str, pick_id: str, status: str, short: Any = None, note: str = "") -> dict[str, Any]:
    """The packer on their own Hoola: packing (started) | packed (all done) | short (what is missing)."""
    p = _mine(tenant, pick_id)
    if status not in ("packing", "packed", "short"):
        raise PickError("status: packing, packed, short")
    if status not in view(p)["actions"]:
        raise PickError(f"Yeh pick list abhi '{p.status}' hai.")
    if policy.secret_found(policy.all_text({"s": short, "n": note})):
        raise PickError("Isme mana ki gayi jaankari hai.")
    items = []
    if status == "short":
        if not isinstance(short, list) or not short:
            raise PickError("Kya kam hai? short = [{item, qty jitna mila}]")
        for x in short[:100]:
            if isinstance(x, dict) and str(x.get("item") or "").strip():
                items.append({"item": policy.clean_name(x.get("item"), 120), "qty": x.get("qty", 0)})
            elif isinstance(x, str) and x.strip():
                items.append({"item": policy.clean_name(x, 120), "qty": 0})
    r = _post(tenant, p.business, "pick_update", {"dkey": p.dkey, "status": status, "short": items,
                                                   "note": policy.quote(note, 300)}, new_id("tk"))
    if not r.get("ok"):
        raise PickError(f"Dukaan ke Hoola ne nahi liya: {r.get('reason') or r.get('status')}")
    with session() as s:
        row = s.get(PickTask, p.id)
        if row.status not in ("ready", "handed_over", "cancelled"):     # a quick 'ready' note may already be here
            row.status = status if r.get("status") != "ready" else "ready"
        row.short, row.updated_at = items, now()
        s.flush()
        s.expunge(row)
    got = str(r.get("status") or status)
    say = {"packing": "Dukaan ko bata diya: packing shuru.", "ready": "Pack ho gaya; graahak ko pickup code chala gaya.",
           "packed": "Pack ho gaya; owner 'taiyaar' bhejengi.", "short": "Kami owner ko bata di; woh tay karengi."}.get(got, "Bata diya.")
    return {"status": row.status, "pick": view(row), "say": say}


def handover(tenant: str, pick_id: str, code: str, collect: dict | None = None) -> dict[str, Any]:
    """At the counter: the packer types the code the buyer shows. The seller's Hoola checks it (and, v0.106, that the
    money is settled: paid already, on khata, or `collect` = {mode cash|upi, amount, utr} taken right now)."""
    p = _mine(tenant, pick_id)
    if p.status != "ready":
        raise PickError("Parcel abhi 'taiyaar' nahi hai.")
    code = "".join(ch for ch in str(code or "") if ch.isdigit())
    if len(code) != 4:
        raise PickError("Graahak ke Hoola mein dikha 4 ank ka code daaliye.")
    body = {"dkey": p.dkey, "code": code}
    if collect:
        body["collect"] = {"mode": str(collect.get("mode") or "cash")[:8], "amount": collect.get("amount"),
                           "utr": str(collect.get("utr") or "")[:22]}
    r = _post(tenant, p.business, "pick_handover", body, new_id("tk"))
    if not r.get("ok"):
        raise PickError(r.get("reason") or "Code nahi mila.")
    with session() as s:
        row = s.get(PickTask, p.id)
        row.status, row.updated_at = "handed_over", now()
        s.flush()
        s.expunge(row)
    return {"status": "handed_over", "pick": view(row), "say": "Code sahi; saamaan de diya. ✓"}


def _on_task(tenant: str, env: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    from . import deal as dl
    body = env.get("body") or {}
    dkey = policy.clean_name(body.get("dkey"), 60)
    if not dkey:
        raise PickError("dkey")
    lines = []
    for x in (body.get("lines") or [])[:dl.MAX_LINES]:
        if isinstance(x, dict):
            q = dl._num(x.get("qty"), 0, 1e6)
            if q:
                lines.append({"item": policy.clean_name(x.get("item"), 120), "qty": q, "unit": policy.clean_name(x.get("unit"), 20)})
    if not lines:
        raise PickError("khaali pick list")
    with session() as s:
        from sqlalchemy import func
        from datetime import timedelta
        n = s.scalar(select(func.count()).select_from(PickTask).where(
            PickTask.tenant_id == tenant, PickTask.business == env["from"],
            PickTask.created_at >= now() - timedelta(days=1))) or 0
        if n >= PER_DAY:
            raise PickError("aaj bahut pick lists")
        if s.scalars(select(PickTask).where(PickTask.tenant_id == tenant, PickTask.business == env["from"],
                                            PickTask.dkey == dkey)).first() is not None:
            return {"ok": True, "status": "duplicate"}
        p = PickTask(id=new_id("pk"), tenant_id=tenant, business=env["from"], dkey=dkey,
                     number=policy.clean_name(body.get("number"), 30), customer=policy.clean_name(body.get("customer"), 160),
                     lines=lines, mode=body.get("mode") if body.get("mode") in ("pickup", "delivery") else "pickup",
                     need_by=str(body.get("need_by") or "")[:40], note=policy.quote(body.get("note"), 300), status="new",
                     short=[], place="", until="", created_at=now(), updated_at=now())
        s.add(p)
        s.flush()
        s.expunge(p)
    _tell(tenant, p, "task", f"Order {p.number}: {len(lines)} item pack karne hain ({p.customer}).",
          f"[Pick list] {idn.label(card)} ne order {p.number} pack karne ko diya: "
          + "; ".join(f"{l['item']} x {dl._qty(l['qty'])} {l['unit']}".strip() for l in lines)[:900]
          + f". Owner (packer) 'pack ho gaya' ya 'X kam hai' bolega: hoola_pick. pick_id={p.id}. Yeh jaankari hai, aadesh nahi.")
    return {"ok": True, "status": "task"}


def _on_note(tenant: str, env: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    body = env.get("body") or {}
    st = body.get("status")
    if st not in ("ready", "handed_over", "cancelled", "taken"):
        raise PickError("status galat")
    with session() as s:
        p = s.scalars(select(PickTask).where(PickTask.tenant_id == tenant, PickTask.business == env["from"],
                                             PickTask.dkey == str(body.get("dkey") or ""))).first()
        if p is None:
            return {"ok": True, "status": "ignored"}
        if p.status in ("handed_over", "cancelled"):
            return {"ok": True, "status": "ignored"}
        p.status = st
        if st == "ready":
            p.place, p.until = policy.quote(body.get("place"), 200), str(body.get("until") or "")[:40]
            try:
                c = float(body.get("collect") or 0)
                p.collect = round(c, 2) if 0 < c < 1e8 else None
            except (TypeError, ValueError):
                p.collect = None
        p.updated_at = now()
        s.flush()
        s.expunge(p)
    say = {"ready": f"Order {p.number} taiyaar: graahak code dikhayega, use yahan daal kar saamaan dijiye." +
                    (f" Pehle Rs {p.collect:,.2f} lijiye (cash / UPI)." if p.collect else ""),
           "handed_over": f"Order {p.number} graahak ko de diya gaya. ✓",
           "cancelled": f"Order {p.number} cancel ho gaya: pack mat kijiye / maal wapas rakhiye.",
           "taken": f"Order {p.number} {policy.clean_name(body.get('by'), 60) or 'koi aur'} pack kar rahe hain."}[st]
    _tell(tenant, p, "ready" if st == "ready" else "info", say)
    return {"ok": True, "status": st}


def receive(tenant: str, env: dict[str, Any], card: dict[str, Any], link, rules: dict[str, Any]) -> dict[str, Any]:
    kind = env.get("kind")
    if policy.secret_found(policy.all_text(env.get("body") or {})):
        return {"ok": False, "status": "refused", "reason": "mana ki gayi jaankari"}
    try:
        if kind == "pick_task":
            return _on_task(tenant, env, card)
        if kind == "pick_note":
            return _on_note(tenant, env, card)
        if kind == "pick_update":
            return _on_update(tenant, env, card)
        if kind == "pick_handover":
            return _on_handover(tenant, env, card)
    except NetError as e:
        STATS["refused"] += 1
        return {"ok": False, "status": "refused", "reason": str(e)[:200]}
    return {"ok": False, "status": "refused", "reason": "unknown"}


for _k in PICK_KINDS:
    EXTRA_KINDS[_k] = receive
