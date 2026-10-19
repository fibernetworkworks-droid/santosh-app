"""Mera PC tools: the user's office/home computer through Santosh Desktop (files, printing, TallyPrime)."""
from __future__ import annotations

import asyncio

from ..bazar import service
from ..bazar.connectors.base import ToolError as BazarError
from ..bazar.connectors.pc import SCHEMAS
from .tools import Ctx, ToolError

PACK = "pc-bridge"

_NAMES = {"pc_status": "status", "pc_search": "search", "pc_list": "list", "pc_read": "read",
          "pc_send_to_phone": "send_file", "pc_print": "print", "tally_report": "tally_report", "tally_entry": "tally_voucher"}

PC_TOOLS = [{"name": api, "description": "[Mera PC] " + SCHEMAS[tool][0], "input_schema": SCHEMAS[tool][1]}
            for api, tool in _NAMES.items()]

PC_LABELS = {"pc_status": "PC dekh raha hoon", "pc_search": "PC par file dhoondh raha hoon", "pc_list": "PC ka folder dekh raha hoon",
             "pc_read": "File padh raha hoon", "pc_send_to_phone": "File phone par bhej raha hoon",
             "pc_print": "Print taiyar kar raha hoon", "tally_report": "Tally dekh raha hoon", "tally_entry": "Tally entry taiyar kar raha hoon"}


def _handler(api: str):
    tool = _NAMES[api]

    async def h(ctx: Ctx, **args):
        try:
            return await asyncio.to_thread(service.run, ctx.tenant_id, ctx.conversation_id, PACK, tool, args)
        except BazarError as e:
            raise ToolError(str(e))
    return h


PC_HANDLERS = {api: _handler(api) for api in _NAMES}
