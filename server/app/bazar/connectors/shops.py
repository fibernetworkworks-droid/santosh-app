"""Bazar shops: local merchants on Newtika's own rails. Santosh can do the whole job here.

Modes (from the shop template):
  catalog       kirana, vegetables, bakery, sweets, chicken, medical store, paper plates, xerox
  subscription  dairy, tiffin, water cans (same tools as catalog; items are per-day/per-month)
  booking       clinic, salon, laundry, electrician, plumber
  due_payment   local ISP, cable LCO, tuition, gym (shop uploads what each customer owes)
"""
from __future__ import annotations

import difflib
import re
from typing import Any

from sqlalchemy import select

from ..db import InstalledPack, Shop, ShopDue, ShopItem, ShopOrder, Transaction
from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec, rupees
from .upi import build_upi_intent

UNIT_ALIASES = {
    "kg": "kg", "kilo": "kg", "kilos": "kg", "kgs": "kg", "kilogram": "kg", "किलो": "kg",
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g", "ग्राम": "g",
    "l": "l", "ltr": "l", "litre": "l", "liter": "l", "litres": "l", "liters": "l", "लीटर": "l",
    "ml": "ml",
    "pc": "pc", "pcs": "pc", "piece": "pc", "pieces": "pc", "nag": "pc",
    "pack": "pack", "packet": "pack", "packets": "pack", "pkt": "pack", "puda": "pack",
    "dozen": "dozen", "darjan": "dozen", "डझन": "dozen",
    "can": "pc", "cans": "pc", "jar": "pc", "plate": "pc", "plates": "pc",
}
NUM_WORDS = {"ek": 1, "one": 1, "do": 2, "don": 2, "two": 2, "teen": 3, "tin": 3, "three": 3, "char": 4, "four": 4,
             "paanch": 5, "panch": 5, "five": 5, "che": 6, "six": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10, "dahaa": 10,
             "ten": 10, "aadha": 0.5, "adha": 0.5, "half": 0.5, "pav": 0.25, "paav": 0.25, "dedh": 1.5, "dhai": 2.5}
SEP = re.compile(r"\s*(?:,|\n|;|\baur\b|\band\b|\bani\b|\bva\b|\bतथा\b|\bआणि\b|\bऔर\b)\s*", re.I)
FILLER = re.compile(r"\b(se|ke|ki|ka|dukaan|dukan|shop|bhejo|mangwa|mangwao|do|de|dena|order|karo|chahiye|pahije|please|plz|ghar|ke liye|liye)\b", re.I)


def parse_lines(text: str) -> list[dict[str, Any]]:
    """'5 kilo atta aur 1 litre tel, 2 packet bread' -> [{'qty':5,'unit':'kg','name':'atta'}, ...]"""
    out = []
    words = "|".join(sorted(NUM_WORDS, key=len, reverse=True))
    numpat = re.compile(r"(?<![\w])(?P<num>\d+(?:\.\d+)?|" + words + r")(?![\w])\s*(?P<rest>.+)$", re.I)
    for part in SEP.split(text):
        part = part.strip()
        if not part:
            continue
        part = re.sub(r"(\d)([^\d\s.,])", r"\1 \2", part)  # "5kg" -> "5 kg"
        qty, unit, name = 1.0, "", part
        m = numpat.search(part)
        if m and m.group("rest").strip():
            num = m.group("num").lower()
            qty = float(num) if num[0].isdigit() else float(NUM_WORDS[num])
            rest = m.group("rest").strip()
            first, _, tail = rest.partition(" ")
            if first.lower() in UNIT_ALIASES and tail:
                unit, name = UNIT_ALIASES[first.lower()], tail
            else:
                name = rest
        name = FILLER.sub(" ", name)
        name = re.sub(r"\s+", " ", name).strip(" .")
        if name:
            out.append({"qty": qty, "unit": unit, "name": name})
    return out


def _convert(qty: float, unit: str, item_unit: str) -> float:
    if not unit or unit == item_unit:
        return qty
    pairs = {("g", "kg"): 0.001, ("kg", "g"): 1000, ("ml", "l"): 0.001, ("l", "ml"): 1000, ("dozen", "pc"): 12}
    f = pairs.get((unit, item_unit))
    if f is None:
        if unit in ("pc", "pack") or item_unit in ("pc", "pack"):
            return qty
        raise ToolError(f"Can't sell {unit} of an item priced per {item_unit}")
    return qty * f


def match_item(items: list[ShopItem], name: str) -> ShopItem | None:
    name = name.lower().strip()
    best, best_score = None, 0.0
    for it in items:
        for cand in [it.name] + list(it.aliases or []):
            c = cand.lower()
            if c == name:
                return it
            words_c, words_n = set(c.split()), set(name.split())
            overlap = len(words_c & words_n) / max(1, len(words_c))
            ratio = difflib.SequenceMatcher(None, c, name).ratio()
            score = max(ratio, overlap if overlap >= 0.5 else 0, 0.85 if (c in name or name in c) and len(c) >= 3 else 0)
            if score > best_score:
                best, best_score = it, score
    return best if best_score >= 0.72 else None


class ShopExecutor:
    name = "shop"

    # ---------- discovery ----------
    def find_shop(self, ctx: Ctx, pack: Pack, hint: str = "") -> Shop:
        shops = ctx.session.scalars(select(Shop).where(Shop.template_id == pack.config["template"], Shop.active.is_(True))).all()
        if not shops:
            raise ToolError(f"No {pack.name.lower()} near you is on MVP Bazar yet.")
        pin = ctx.user.pincode
        nearby = [s for s in shops if not s.pincodes or not pin or pin in s.pincodes] or shops
        h = (hint or "").lower()
        if h:
            named = [s for s in nearby if s.name.lower() in h or any(a.lower() in h for a in (s.aliases or []))
                     or any(w for w in s.name.lower().split() if len(w) > 3 and w in h)]
            if len(named) == 1:
                return named[0]
            if named:
                nearby = named
        if len(nearby) == 1:
            return nearby[0]
        prev = ctx.session.scalars(select(ShopOrder).where(ShopOrder.user_id == ctx.user.id,
                                                           ShopOrder.shop_id.in_([s.id for s in nearby]))
                                   .order_by(ShopOrder.created_at.desc())).first()
        if prev:
            return next(s for s in nearby if s.id == prev.shop_id)
        raise ToolError("Which shop? " + ", ".join(s.name for s in nearby[:5]))

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        shop_arg = {"shop": {"type": "string", "description": "Shop name or the way the user refers to it, e.g. 'Ramesh bhau'"}}
        specs = {
            "search_items": ToolSpec("search_items", f"Search items or services at a {pack.name.lower()} on MVP Bazar.",
                                     {"type": "object", "properties": {**shop_arg, "query": {"type": "string"}}}, 0),
            "build_cart": ToolSpec("build_cart", "Build a cart. 'lines' is free text like '5 kg atta, 1 litre oil' or a list of {name, qty, unit}.",
                                   {"type": "object", "properties": {**shop_arg, "lines": {}}, "required": ["lines"]}, 1),
            "place_order": ToolSpec("place_order", "Ask the user to approve the cart and place the order.",
                                    {"type": "object", "properties": {"cart_id": {"type": "string"}, "slot": {"type": "string"},
                                                                      "address": {"type": "string"}}, "required": ["cart_id"]}, 2),
            "order_status": ToolSpec("order_status", "Status of the user's latest (or a given) order at this kind of shop.",
                                     {"type": "object", "properties": {"order_id": {"type": "string"}}}, 0),
            "book_slot": ToolSpec("book_slot", "Book a service slot (clinic, salon, laundry pickup, electrician, plumber).",
                                  {"type": "object", "properties": {**shop_arg, "service": {"type": "string"}, "slot": {"type": "string"},
                                                                    "note": {"type": "string"}}, "required": ["service"]}, 2),
            "get_due": ToolSpec("get_due", "Look up what the user owes this shop (internet bill, cable, tuition, gym).",
                                {"type": "object", "properties": {**shop_arg, "customer_ref": {"type": "string"}}}, 0),
            "pay_due": ToolSpec("pay_due", "Ask the user to approve paying a due found by get_due.",
                                {"type": "object", "properties": {"due_id": {"type": "string"}}, "required": ["due_id"]}, 2),
        }
        return [specs[t.name] for t in pack.tools]

    # ---------- tools ----------
    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        hint = str(args.get("shop") or (ctx.task.text if ctx.task else ""))
        if tool == "search_items":
            shop = self.find_shop(ctx, pack, hint)
            q = str(args.get("query", "")).lower()
            items = [i for i in shop.items if i.in_stock and (not q or q in i.name.lower() or any(q in a.lower() for a in i.aliases or []))]
            return {"shop": shop.name, "shop_id": shop.id, "items": [self._item(i) for i in items[:30]]}

        if tool == "build_cart":
            shop = self.find_shop(ctx, pack, hint)
            raw = args.get("lines")
            wanted = parse_lines(raw) if isinstance(raw, str) else [
                {"qty": float(x.get("qty", 1)), "unit": UNIT_ALIASES.get(str(x.get("unit", "")).lower(), ""), "name": str(x.get("name", ""))}
                for x in (raw or [])]
            if not wanted:
                raise ToolError("What should I add to the cart?")
            lines, missing = [], []
            for w in wanted:
                it = match_item([i for i in shop.items if i.in_stock], w["name"])
                if not it:
                    missing.append(w["name"])
                    continue
                units = _convert(w["qty"], w["unit"], it.unit) / (it.unit_qty or 1)
                price = int(round(units * it.price_paise))
                lines.append({"item_id": it.id, "name": it.name, "qty": w["qty"], "unit": w["unit"] or it.unit,
                              "price_paise": price, "label": f"{it.name} {self._fmt_qty(w['qty'], w['unit'] or it.unit)}"})
            if not lines:
                raise ToolError(f"{shop.name} doesn't have " + ", ".join(missing) + ".")
            total = sum(l["price_paise"] for l in lines) + shop.delivery_fee_paise
            order = ShopOrder(shop_id=shop.id, user_id=ctx.user.id, kind="subscription" if pack.config["mode"] == "subscription" else "order",
                              lines=lines, total_paise=total, status="cart")
            ctx.session.add(order)
            ctx.session.flush()
            res = {"cart_id": order.id, "shop": shop.name, "lines": [{"item": l["label"], "price": rupees(l["price_paise"])} for l in lines],
                   "delivery_fee": rupees(shop.delivery_fee_paise), "total": rupees(total), "total_paise": total,
                   "slots": shop.slots}
            if missing:
                res["not_available"] = missing
            if total < shop.min_order_paise:
                res["warning"] = f"Minimum order is {rupees(shop.min_order_paise)}"
            return res

        if tool == "place_order":
            order = self._own_order(ctx, str(args.get("cart_id", "")))
            if order.status != "cart":
                raise ToolError("This cart was already ordered.")
            shop = ctx.session.get(Shop, order.shop_id)
            assert shop is not None
            if order.total_paise < shop.min_order_paise:
                raise ToolError(f"{shop.name} needs a minimum order of {rupees(shop.min_order_paise)}.")
            slot = str(args.get("slot") or (shop.slots[0] if shop.slots else "Today"))
            address = str(args.get("address") or ctx.user.profile.get("address", ""))
            items = [{"name": l["label"], "price_paise": l["price_paise"]} for l in order.lines]
            if shop.delivery_fee_paise:
                items.append({"name": "Delivery", "price_paise": shop.delivery_fee_paise})
            return NeedsApproval(tier=2, title="Confirm order", payee=shop.name, amount_paise=order.total_paise, items=items,
                                 pay_method="UPI to shop · one tap",
                                 action={"executor": "shop", "pack_id": pack.id, "name": "confirm_order",
                                         "args": {"order_id": order.id, "slot": slot, "address": address}},
                                 preview={"slot": slot})

        if tool == "order_status":
            oid = args.get("order_id")
            q = select(ShopOrder).where(ShopOrder.user_id == ctx.user.id, ShopOrder.status != "cart")
            if oid:
                q = q.where(ShopOrder.id == oid)
            order = ctx.session.scalars(q.order_by(ShopOrder.created_at.desc())).first()
            if not order:
                return {"status": "no_orders"}
            shop = ctx.session.get(Shop, order.shop_id)
            return {"order_id": order.id, "shop": shop.name if shop else "", "status": order.status, "slot": order.slot,
                    "payment": order.payment_status, "total": rupees(order.total_paise)}

        if tool == "book_slot":
            shop = self.find_shop(ctx, pack, hint)
            svc = match_item([i for i in shop.items if i.in_stock], str(args.get("service", "")))
            if not svc:
                raise ToolError(f"{shop.name} offers: " + ", ".join(i.name for i in shop.items if i.in_stock))
            slot = str(args.get("slot") or (shop.slots[0] if shop.slots else ""))
            if shop.slots and slot not in shop.slots:
                raise ToolError(f"Available slots at {shop.name}: " + ", ".join(shop.slots))
            order = ShopOrder(shop_id=shop.id, user_id=ctx.user.id, kind="booking", slot=slot, status="cart",
                              lines=[{"item_id": svc.id, "name": svc.name, "qty": 1, "unit": svc.unit, "price_paise": svc.price_paise,
                                      "label": svc.name, "note": str(args.get("note", ""))}],
                              total_paise=svc.price_paise)
            ctx.session.add(order)
            ctx.session.flush()
            return NeedsApproval(tier=2, title="Confirm booking", payee=shop.name, amount_paise=svc.price_paise,
                                 items=[{"name": f"{svc.name} · {slot}", "price_paise": svc.price_paise}],
                                 pay_method="Pay at shop" if svc.price_paise == 0 else "UPI to shop · one tap",
                                 action={"executor": "shop", "pack_id": pack.id, "name": "confirm_order",
                                         "args": {"order_id": order.id, "slot": slot, "address": ""}})

        if tool == "get_due":
            shop = self.find_shop(ctx, pack, hint)
            inst = ctx.session.scalars(select(InstalledPack).where(InstalledPack.user_id == ctx.user.id,
                                                                   InstalledPack.pack_id == pack.id)).first()
            ref = str(args.get("customer_ref") or (inst.settings.get(f"ref:{shop.id}") if inst else "") or "")
            q = select(ShopDue).where(ShopDue.shop_id == shop.id, ShopDue.paid.is_(False))
            if not ref and not ctx.user.phone:
                raise ToolError(f"What is your customer / account number at {shop.name}?")
            q = q.where(ShopDue.customer_ref == ref) if ref else q.where(ShopDue.customer_phone == ctx.user.phone)
            dues = ctx.session.scalars(q).all()
            if not dues:
                return {"shop": shop.name, "dues": [], "message": f"Nothing due at {shop.name}."}
            if ref:
                if inst is None:
                    inst = InstalledPack(user_id=ctx.user.id, pack_id=pack.id, settings={})
                    ctx.session.add(inst)
                inst.settings = {**(inst.settings or {}), f"ref:{shop.id}": ref}
            return {"shop": shop.name, "dues": [{"due_id": d.id, "for": d.description, "amount": rupees(d.amount_paise),
                                                  "due_on": d.due_on.isoformat() if d.due_on else ""} for d in dues]}

        if tool == "pay_due":
            due = ctx.session.get(ShopDue, str(args.get("due_id", "")))
            if not due or due.paid:
                raise ToolError("I couldn't find that due. Let me look it up again.")
            shop = ctx.session.get(Shop, due.shop_id)
            assert shop is not None
            if due.customer_phone and due.customer_phone != ctx.user.phone:
                inst = ctx.session.scalars(select(InstalledPack).where(InstalledPack.user_id == ctx.user.id,
                                                                       InstalledPack.pack_id == pack.id)).first()
                if not inst or inst.settings.get(f"ref:{shop.id}") != due.customer_ref:
                    raise ToolError("This due belongs to another customer account.")
            return NeedsApproval(tier=2, title=f"Pay {shop.name}", payee=shop.name, amount_paise=due.amount_paise,
                                 items=[{"name": due.description or "Due", "price_paise": due.amount_paise}],
                                 pay_method="UPI to shop · one tap",
                                 action={"executor": "shop", "pack_id": pack.id, "name": "pay_due", "args": {"due_id": due.id}})
        raise ToolError(f"Unknown tool {tool}")

    # ---------- approved actions ----------
    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        if action == "confirm_order":
            order = self._own_order(ctx, args["order_id"])
            shop = ctx.session.get(Shop, order.shop_id)
            assert shop is not None
            order.status, order.slot, order.address = "placed", args.get("slot", ""), args.get("address", "")
            out: dict[str, Any] = {"order_id": order.id, "shop": shop.name, "slot": order.slot, "status": "placed"}
            if order.total_paise > 0:
                txn = Transaction(user_id=ctx.user.id, task_id=ctx.task.id if ctx.task else "", kind="shop_order", provider=shop.id,
                                  amount_paise=order.total_paise, status="awaiting_payment", meta={"order_id": order.id})
                ctx.session.add(txn)
                ctx.session.flush()
                order.txn_ref = txn.txn_ref
                out["intent_url"] = build_upi_intent(shop.upi_id, shop.name, order.total_paise, f"Order {order.id[:6]}",
                                                     tr=txn.txn_ref, max_paise=ctx.settings.upi_max_amount_paise)
                out["txn_ref"] = txn.txn_ref
            out["message"] = (f"{shop.name} has your order" + (f" for {order.slot}" if order.slot else "") + "."
                              + (f" Pay {rupees(order.total_paise)} on the UPI screen." if order.total_paise else ""))
            self._notify_shop(ctx, shop, order)
            return out
        if action == "pay_due":
            due = ctx.session.get(ShopDue, args["due_id"])
            if not due:
                raise ToolError("Due not found")
            shop = ctx.session.get(Shop, due.shop_id)
            assert shop is not None
            txn = Transaction(user_id=ctx.user.id, task_id=ctx.task.id if ctx.task else "", kind="shop_due", provider=shop.id,
                              amount_paise=due.amount_paise, status="awaiting_payment", meta={"due_id": due.id})
            ctx.session.add(txn)
            ctx.session.flush()
            return {"status": "open_app", "txn_ref": txn.txn_ref,
                    "intent_url": build_upi_intent(shop.upi_id, shop.name, due.amount_paise, due.description[:40], tr=txn.txn_ref,
                                                   max_paise=ctx.settings.upi_max_amount_paise),
                    "message": f"Opening your UPI app to pay {rupees(due.amount_paise)} to {shop.name}."}
        raise ToolError(f"Unknown action {action}")

    # ---------- helpers ----------
    def _own_order(self, ctx: Ctx, oid: str) -> ShopOrder:
        o = ctx.session.get(ShopOrder, oid)
        if not o or o.user_id != ctx.user.id:
            raise ToolError("Cart not found. Let me build it again.")
        return o

    @staticmethod
    def _fmt_qty(q: float, unit: str) -> str:
        qs = str(int(q)) if float(q).is_integer() else f"{q:g}"
        return f"{qs} {unit}" if unit not in ("pc", "") else f"× {qs}"

    @staticmethod
    def _item(i: ShopItem) -> dict[str, Any]:
        per = f"{i.unit_qty:g} {i.unit}" if i.unit_qty != 1 else i.unit
        return {"item_id": i.id, "name": i.name, "price": f"{rupees(i.price_paise)} / {per}", "kind": i.kind}

    def _notify_shop(self, ctx: Ctx, shop: Shop, order: ShopOrder) -> None:
        """WhatsApp the shop about a new order. Free text only reaches a number that messaged us in the last 24 h,
        so an approved UTILITY template is used when configured. The outcome is recorded, never swallowed."""
        from .whatsapp import WhatsApp
        wa = WhatsApp(ctx.settings)
        if not wa.configured:
            order.notify_status = "not sent: WhatsApp Business number not connected (shop sees it in its order list)"
            return
        items = ", ".join(l["label"] for l in order.lines)[:900]
        where = " · ".join(x for x in (order.slot, order.address) if x)[:300] or "-"
        try:
            if ctx.settings.shop_order_template:
                r = wa.send_template(shop.owner_phone, ctx.settings.shop_order_template, ctx.settings.shop_order_template_lang,
                                     [order.id[:6], items, rupees(order.total_paise), where])
            else:
                r = wa.send_text(shop.owner_phone, f"New Santosh order {order.id[:6]}\n{items}\nTotal {rupees(order.total_paise)}\n{where}")
            ok = bool(r.get("ok"))
            order.notify_status = "sent" if ok else ("failed: " + str(r.get("response", ""))[:150] if ctx.settings.shop_order_template
                                                     else "failed: no 24h window; set BAZAR_SHOP_ORDER_TEMPLATE")
        except Exception as e:  # never fail the order over a notification
            order.notify_status = f"failed: {type(e).__name__}: {str(e)[:120]}"
