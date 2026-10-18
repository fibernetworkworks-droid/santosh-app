"""Task orchestration: run a user instruction, pause for approval, resume, settle payments."""
from __future__ import annotations

import datetime as dt
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..connectors.base import Ctx, Executor, NeedsApproval, ToolError, rupees
from ..db import Approval, InstalledPack, Shop, ShopOrder, Task, TaskStep, Transaction, User
from ..packs.registry import Pack, Registry, registry
from .guard import can_auto_approve
from .toolbox import default_executors


class PausedForApproval(Exception):
    def __init__(self, approval: Approval):
        self.approval = approval


class Runner:
    def __init__(self, session: Session, settings: Settings | None = None, reg: Registry | None = None,
                 executors: dict[str, Executor] | None = None, claude_client: Any = None):
        self.s = session
        self.settings = settings or get_settings()
        self.reg = reg or registry()
        self.executors = executors or default_executors()
        self.claude_client = claude_client

    # ------------------------------------------------------------------ approvals
    def decide(self, approval_id: str, user: User, decision: str) -> dict[str, Any]:
        """The user tapped Approve / Reject on the card. Runs the frozen server-side action (never model text)."""
        ap = self.s.get(Approval, approval_id)
        if ap is None or ap.user_id != user.id:
            raise ToolError("Approval not found")
        if ap.decision != "pending":
            raise ToolError(f"Already {ap.decision}")
        task = self.s.get(Task, ap.task_id)
        assert task is not None
        ctx = Ctx(self.s, user, task, self.settings)
        ap.decided_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        if decision == "approve":
            ap.decision = "approved"
            try:
                outcome = self._execute(ctx, ap)
            except ToolError as e:
                outcome = {"error": str(e)}
            if task.status == "awaiting_approval":
                task.status = "done"
        else:
            ap.decision = "rejected"
            outcome = {"rejected": True, "message": "Cancelled. Nothing was ordered or paid."}
            task.status = "cancelled"
        ap.result = _jsonable(outcome)
        self.s.commit()
        return outcome

    # ------------------------------------------------------------------ tool calls
    def call_tool(self, ctx: Ctx, pack: Pack, tool: str, args: dict[str, Any], tool_use_id: str = "") -> dict[str, Any]:
        task = ctx.task
        assert task is not None
        seq = len(task.steps) + 1
        step = TaskStep(task_id=task.id, seq=seq, tool=f"{pack.id}.{tool}", input=_jsonable(args))
        task.steps.append(step)
        task.pack_id = task.pack_id or pack.id
        try:
            res = self.executors[pack.executor].call(pack, tool, args, ctx)
        except ToolError as e:
            step.error = str(e)
            raise
        if isinstance(res, NeedsApproval):
            ap = Approval(task_id=task.id, user_id=ctx.user.id, tier=res.tier, title=res.title, payee=res.payee,
                          amount_paise=res.amount_paise, items=res.items, pay_method=res.pay_method, action=res.action,
                          tool_use_id=tool_use_id)
            self.s.add(ap)
            self.s.flush()
            if can_auto_approve(self.s, ctx.user, res):
                ap.decision = "auto"
                ap.decided_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
                step.note = f"auto-approved under your limit ({rupees(res.amount_paise)})"
                out = self._execute(ctx, ap)
                step.output = _jsonable(out)
                return {"auto_approved": True, **out}
            step.note = "waiting for approval"
            step.output = {"approval_id": ap.id, "amount": rupees(ap.amount_paise)}
            task.status = "awaiting_approval"
            raise PausedForApproval(ap)
        step.output = _jsonable(res)
        return res

    def _execute(self, ctx: Ctx, ap: Approval) -> dict[str, Any]:
        act = ap.action
        pack = self.reg.get(act["pack_id"])
        out = self.executors[act["executor"]].execute(pack, act["name"], act["args"], ctx)
        task = ctx.task
        assert task is not None
        task.steps.append(TaskStep(task_id=task.id, seq=len(task.steps) + 1, tool=f"{pack.id}.{act['name']}",
                                   input={"approval_id": ap.id}, output=_jsonable(out), note=f"approved: {ap.decision}"))
        if out.get("intent_url"):
            task.status = "awaiting_payment"
        task.result = {**(task.result or {}), "last_action": _jsonable(out)}
        return out

    # ------------------------------------------------------------------ payments
    def payment_confirmed(self, txn_ref: str, ok: bool, provider_ref: str = "") -> Transaction:
        """Called by the payment webhook (PA / bank) or by the merchant marking an order paid."""
        txn = self.s.scalars(select(Transaction).where(Transaction.txn_ref == txn_ref)).first()
        if txn is None:
            raise ToolError("Unknown payment reference")
        if txn.status in ("completed", "paid"):
            return txn
        user = self.s.get(User, txn.user_id)
        task = self.s.get(Task, txn.task_id) if txn.task_id else None
        ctx = Ctx(self.s, user, task, self.settings)  # type: ignore[arg-type]
        if not ok:
            txn.status = "failed"
            if task:
                task.status, task.reply = "done", "The payment didn't go through. Nothing was charged; want to try again?"
            self.s.commit()
            return txn
        txn.status, txn.provider_ref = "paid", provider_ref
        reply = ""
        if txn.kind == "bill":
            from ..connectors.bbps import BBPSExecutor
            ex = self.executors.get("bbps") or BBPSExecutor()
            assert isinstance(ex, BBPSExecutor)
            try:
                r = ex.settle(self.reg.get(txn.provider), txn, ctx)
                reply = f"Paid {r['amount']} to {r['biller']}. Receipt {r['receipt_no']}. I'll remind you around {r['next_reminder']}."
            except ToolError as e:
                reply = str(e)
        elif txn.kind == "shop_order":
            order = self.s.get(ShopOrder, txn.meta.get("order_id"))
            if order:
                order.payment_status = "paid"
            txn.status = "completed"
            shop = self.s.get(Shop, txn.provider)
            reply = f"Payment of {rupees(txn.amount_paise)} received by {shop.name if shop else 'the shop'}. Your order is confirmed."
        elif txn.kind == "shop_due":
            from ..db import ShopDue
            due = self.s.get(ShopDue, (txn.meta or {}).get("due_id"))
            if due:
                due.paid = True
            txn.status = "completed"
            shop = self.s.get(Shop, txn.provider)
            reply = f"{shop.name if shop else 'The shop'} confirmed your payment of {rupees(txn.amount_paise)}."
        else:
            txn.status = "completed"
            reply = f"Payment of {rupees(txn.amount_paise)} done."
        if task:
            task.status, task.reply = "done", reply
        txn.meta = {**(txn.meta or {}), "reply": reply}
        self.s.commit()
        return txn

    # ------------------------------------------------------------------ helpers
    def installed_ids(self, user: User) -> set[str]:
        return set(self.s.scalars(select(InstalledPack.pack_id).where(InstalledPack.user_id == user.id)).all())


def _jsonable(x: Any) -> Any:
    return json.loads(json.dumps(x, default=str))
