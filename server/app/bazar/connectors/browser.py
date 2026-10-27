"""Santosh Browser approvals: when the browser worker stops before a click that submits, sends, books or deletes,
this pack turns it into a confirm card. The label, website and the worker's one-time pending id come from the
worker itself (never from model text), and the click happens only after the user taps Approve."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec


class BrowserExecutor:
    name = "browser"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_step", "Ask the user to approve the step Santosh's web browser paused on "
                         "(submit / send / book / apply / delete on a website). Used by browse_web.",
                         {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ... import browser
        if tool != "confirm_step":
            raise ToolError(f"Unknown tool {tool}")
        sid = str(args.get("session_id", ""))
        try:
            res = browser.get(ctx.user.id, sid, 0)
        except browser.BrowserError as e:
            raise ToolError(str(e))
        p = res.get("pending") or {}
        if res.get("status") != "needs_confirm" or not p.get("id"):
            raise ToolError("The browser isn't waiting for an approval any more.")
        site = browser.host_of(p.get("url") or res.get("url", "")) or "website"
        label = str(p.get("label") or "next step")[:80]
        return NeedsApproval(
            tier=2, title=f"{site}: '{label}'", payee=site, amount_paise=0,
            items=[{"name": f"Hoola ka apna browser (server par, aapka PC nahi) '{label}' dabayega: {site}"},
                   {"name": "No payment. Passwords, OTPs and payments are never done by Santosh."}],
            pay_method="Hoola ka browser", preview={"message": f"Approve to let Santosh click '{label}' on {site}."},
            action={"executor": "browser", "pack_id": pack.id, "name": "approve_step",
                    "args": {"session_id": sid, "pending_id": p["id"], "label": label, "site": site}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ... import browser
        if action != "approve_step":
            raise ToolError(f"Unknown action {action}")
        try:
            browser.approve(ctx.user.id, args["session_id"], args["pending_id"])
        except browser.BrowserError as e:
            raise ToolError(str(e))
        conv = (ctx.task.conversation_id if ctx.task is not None else "") or ""
        browser.follow(ctx.user.id, conv, args["session_id"])
        return {"message": f"Theek hai, {args.get('site', 'website')} par '{args.get('label', '')}' kar raha hoon. "
                           "Ho jaate hi yahin bataunga."}
