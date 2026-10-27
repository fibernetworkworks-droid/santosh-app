"""Bill payments over BBPS (electricity, gas, LPG, mobile, broadband, DTH).

Flow (Tier 2):
  fetch_bill  -> bill saved server-side with its exact amount
  pay_bill    -> confirm card built from that saved bill (never from model text)
  approve     -> UPI intent to Newtika's collection VPA, tagged with txn_ref
  webhook     -> payment confirmed -> partner pays the biller -> receipt + next month's reminder

Adapters:
  SandboxBBPS : deterministic, offline; for dev, tests and demos.
  HttpBBPS    : talks to Newtika's BBPS gateway (a thin service in front of the chosen BBPS partner).
"""
from __future__ import annotations

import datetime as dt
import hashlib
from typing import Any, Protocol

import httpx
from sqlalchemy import select

from ..config import Settings
from ..db import InstalledPack, Reminder, Transaction
from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec, rupees
from .upi import build_upi_intent


class BBPSAdapter(Protocol):
    def fetch(self, pack: Pack, params: dict[str, str]) -> dict[str, Any]: ...
    def pay(self, bill: dict[str, Any], amount_paise: int, payment_ref: str) -> dict[str, Any]: ...


class SandboxBBPS:
    def fetch(self, pack: Pack, params: dict[str, str]) -> dict[str, Any]:
        key = "|".join([pack.id] + [str(params[k]) for k in sorted(params)])
        h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
        amount = 30_000 + (h % 270_000)  # ₹300 – ₹3,000
        amount -= amount % 10
        today = dt.date.today()
        first = (params.get("consumer_number") or params.get("mobile_number") or next(iter(params.values()), ""))
        return {"bill_ref": f"SBX{h % 10**10:010d}", "biller": pack.name, "amount_paise": amount,
                "due_date": (today + dt.timedelta(days=7 + h % 10)).isoformat(),
                "period": (today.replace(day=1) - dt.timedelta(days=1)).strftime("%B %Y"),
                "customer_name": "Consumer ••••" + str(first)[-4:], "sandbox": True}

    def pay(self, bill: dict[str, Any], amount_paise: int, payment_ref: str) -> dict[str, Any]:
        return {"status": "SUCCESS", "receipt_no": "BBPS" + payment_ref[-10:], "sandbox": True}


class HttpBBPS:
    """Contract of Newtika's BBPS gateway:

    POST {base}/v1/bills/fetch  {"biller_id","biller_name","category","params"} -> {"bill_ref","amount_paise","due_date","period","customer_name"}
    POST {base}/v1/bills/pay    {"bill_ref","amount_paise","payment_ref"}      -> {"status","receipt_no"}
    """

    def __init__(self, s: Settings, client: httpx.Client | None = None):
        if not s.bbps_base_url:
            raise ToolError("Bill payments are not configured yet (SANTOSH_BBPS_BASE_URL)")
        self.client = client or httpx.Client(base_url=s.bbps_base_url, timeout=20,
                                             headers={"Authorization": f"Bearer {s.bbps_api_key}"})

    def fetch(self, pack: Pack, params: dict[str, str]) -> dict[str, Any]:
        if not pack.config.get("biller_id"):
            raise ToolError(f"{pack.name} is not mapped with our bill-pay partner yet (biller_id missing).")
        r = self.client.post("/v1/bills/fetch", json={"biller_id": pack.config.get("biller_id"), "biller_name": pack.config["biller_name"],
                                                      "category": pack.config["biller_category"], "params": params})
        if r.status_code == 404:
            raise ToolError("No bill found for these details. Please check the number.")
        r.raise_for_status()
        out = r.json()
        out.setdefault("biller", pack.name)
        return out

    def pay(self, bill: dict[str, Any], amount_paise: int, payment_ref: str) -> dict[str, Any]:
        r = self.client.post("/v1/bills/pay", json={"bill_ref": bill["bill_ref"], "amount_paise": amount_paise, "payment_ref": payment_ref})
        r.raise_for_status()
        return r.json()


def adapter_for(s: Settings) -> BBPSAdapter:
    return SandboxBBPS() if s.bbps_mode == "sandbox" else HttpBBPS(s)


class BBPSExecutor:
    name = "bbps"

    def __init__(self, adapter: BBPSAdapter | None = None):
        self._adapter = adapter

    def adapter(self, ctx: Ctx) -> BBPSAdapter:
        return self._adapter or adapter_for(ctx.settings)

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        fields = pack.config["input_fields"]
        props = {f: {"type": "string"} for f in fields}
        return [
            ToolSpec("fetch_bill", f"Fetch the latest {pack.name} bill. Fields: {', '.join(fields)}. Leave them out to use the saved ones.",
                     {"type": "object", "properties": props}, 0),
            ToolSpec("pay_bill", f"Ask the user to approve paying a {pack.name} bill fetched earlier in this task.",
                     {"type": "object", "properties": {"bill_ref": {"type": "string"}}, "required": ["bill_ref"]}, 2),
        ]

    def _saved(self, ctx: Ctx, pack: Pack) -> InstalledPack | None:
        return ctx.session.scalars(select(InstalledPack).where(InstalledPack.user_id == ctx.user.id,
                                                               InstalledPack.pack_id == pack.id)).first()

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        if tool == "fetch_bill":
            inst = self._saved(ctx, pack)
            saved = (inst.settings if inst else {}) or {}
            params = {f: str(args.get(f) or saved.get(f) or "").strip() for f in pack.config["input_fields"]}
            missing = [f for f, v in params.items() if not v]
            if missing:
                raise ToolError(f"I need your {', '.join(m.replace('_', ' ') for m in missing)} for {pack.name}. I'll save it for next time.")
            bill = self.adapter(ctx).fetch(pack, params)
            if inst is None:
                inst = InstalledPack(user_id=ctx.user.id, pack_id=pack.id, settings={})
                ctx.session.add(inst)
            inst.settings = {**saved, **params}
            txn = Transaction(user_id=ctx.user.id, task_id=ctx.task.id if ctx.task else "", kind="bill", provider=pack.id,
                              amount_paise=int(bill["amount_paise"]), status="fetched", provider_ref=bill["bill_ref"],
                              meta={"bill": bill, "params": params})
            ctx.session.add(txn)
            ctx.session.flush()
            out_demo = {"demo": True, "note": "DEMO bill from the sandbox, not your real bill. Real bill pay starts once the BBPS partner is live."} \
                if bill.get("sandbox") else {}
            return {**out_demo, "bill_ref": bill["bill_ref"], "biller": bill["biller"], "amount": rupees(bill["amount_paise"]),
                    "amount_paise": bill["amount_paise"], "due_date": bill["due_date"], "period": bill.get("period", ""),
                    "customer_name": bill.get("customer_name", "")}
        if tool == "pay_bill":
            ref = str(args.get("bill_ref", ""))
            txn = ctx.session.scalars(select(Transaction).where(Transaction.user_id == ctx.user.id, Transaction.provider_ref == ref,
                                                                Transaction.kind == "bill")).first()
            if txn is None:
                raise ToolError("Fetch the bill first; I only pay bills I have fetched myself.")
            if txn.status in ("paid", "completed"):
                raise ToolError("This bill is already paid.")
            bill = txn.meta["bill"]
            demo = bool(bill.get("sandbox"))
            if not demo and not ctx.settings.bills_live:
                raise ToolError("Bill payment is not live yet (BBPS partner / collection UPI ID not configured).")
            return NeedsApproval(
                tier=2, title=("[DEMO] " if demo else "") + f"Pay {pack.name} bill", payee=pack.name, amount_paise=txn.amount_paise,
                items=[{"name": f"{bill.get('period', 'Bill')} · {bill.get('customer_name', '')}", "price_paise": txn.amount_paise},
                       {"name": f"Due {bill['due_date']}", "price_paise": None}],
                pay_method="Demo: no money moves" if demo else "UPI PIN in your UPI app",
                action={"executor": "bbps", "pack_id": pack.id, "name": "collect_payment", "args": {"txn_id": txn.id}})
        raise ToolError(f"Unknown tool {tool}")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        if action != "collect_payment":
            raise ToolError(f"Unknown action {action}")
        txn = ctx.session.get(Transaction, args["txn_id"])
        if txn is None or txn.user_id != ctx.user.id:
            raise ToolError("Bill not found")
        if (txn.meta or {}).get("bill", {}).get("sandbox"):
            # Sandbox: never send real money to a placeholder UPI ID. Settle with a demo receipt instead.
            txn.status = "paid"
            r = self.settle(pack, txn, ctx)
            return {"status": "demo_paid", "demo": True, **r,
                    "message": f"DEMO: {pack.name} bill marked paid with a test receipt {r['receipt_no']}. No money moved."}
        if not ctx.settings.bills_live:
            raise ToolError("Bill payment is not live yet (BBPS partner / collection UPI ID not configured).")
        txn.status = "awaiting_payment"
        link = build_upi_intent(ctx.settings.collection_vpa, ctx.settings.collection_name, txn.amount_paise,
                                f"{pack.name} bill", tr=txn.txn_ref, max_paise=ctx.settings.upi_max_amount_paise)
        return {"status": "open_app", "intent_url": link, "txn_ref": txn.txn_ref,
                "message": f"Opening your UPI app. Enter your PIN to pay {rupees(txn.amount_paise)}; I'll pay {pack.name} as soon as it lands."}

    # Called by the payment webhook once the user's UPI payment is confirmed.
    def settle(self, pack: Pack, txn: Transaction, ctx: Ctx) -> dict[str, Any]:
        bill = txn.meta["bill"]
        res = self.adapter(ctx).pay(bill, txn.amount_paise, txn.txn_ref)
        if str(res.get("status", "")).upper() != "SUCCESS":
            txn.status = "failed"
            txn.meta = {**txn.meta, "pay_result": res}
            raise ToolError("The biller did not accept the payment. Your money will be refunded.")
        txn.status = "completed"
        txn.meta = {**txn.meta, "pay_result": res}
        nxt = dt.datetime.combine(dt.date.fromisoformat(bill["due_date"]) + dt.timedelta(days=27), dt.time(9, 0))
        ctx.session.add(Reminder(user_id=txn.user_id, kind="bill", text=f"{pack.name} bill due soon", due_at=nxt,
                                 meta={"pack_id": pack.id}))
        return {"receipt_no": res.get("receipt_no"), "amount": rupees(txn.amount_paise), "biller": pack.name,
                "next_reminder": nxt.date().isoformat()}
