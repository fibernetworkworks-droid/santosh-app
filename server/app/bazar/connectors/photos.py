"""Confirm card for a big upload into Google Photos (more than 20 files at once). The card and what runs after the
tap come from the stored upload, never from model text."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec


class PhotosExecutor:
    name = "photos"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return [ToolSpec("confirm_change", "Ask the user to approve a prepared Google Photos upload.",
                         {"type": "object", "properties": {"pending_id": {"type": "string"}}, "required": ["pending_id"]}, 2)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        from ...photos import service as ps
        if tool != "confirm_change":
            raise ToolError(f"Unknown tool {tool}")
        p = ps.pending(ctx.user.id, str(args.get("pending_id", "")))
        if p is None or p["status"] != "pending":
            raise ToolError("Yeh upload taiyaar nahi hai; dobara boliye.")
        sm = p["summary"]
        items = [{"name": f"{sm.get('count', 0)} photos / videos Google Photos mein jayengi"}]
        if sm.get("album"):
            items.append({"name": f"Album: {sm['album']}"})
        items.append({"name": "Google Photos mein se hatana aapko khud karna hoga (Santosh delete nahi kar sakta)."})
        return NeedsApproval(tier=2, title="Itni photos upload karein?", payee="Google Photos", amount_paise=0,
                             items=items, pay_method="Santosh Photos",
                             preview={"message": f"Approve to upload {sm.get('count', 0)} files to Google Photos."},
                             action={"executor": "photos", "pack_id": pack.id, "name": "run", "args": {"pending_id": p["id"]}})

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        from ...photos import service as ps
        from ...photos.client import PhotosError
        if action != "run":
            raise ToolError(f"Unknown action {action}")
        try:
            return ps.run_pending(ctx.user.id, args["pending_id"])
        except PhotosError as e:
            raise ToolError(str(e))
