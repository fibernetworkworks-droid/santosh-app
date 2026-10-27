"""App Jaanch pack: the app_check tool does the work (REA static analysis, nothing to approve, nothing is run)."""
from __future__ import annotations

from typing import Any

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec


class AppCheckExecutor:
    name = "appcheck"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        return []

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        raise ToolError("App Jaanch ke liye app_check tool use kijiye.")

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        raise ToolError(f"Unknown action {action}")
