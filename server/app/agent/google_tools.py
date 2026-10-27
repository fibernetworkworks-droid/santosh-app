"""v0.70 Tool `google_status`: why Google Drive / Gmail / Calendar are (not) working for her, with the fix."""
from __future__ import annotations

import asyncio

from .tools import Ctx

GOOGLE_TOOLS = [
    {"name": "google_status", "description": (
        "Check her Google connection when Drive / Gmail / Calendar / Sheets don't work or she asks 'Drive kyun nahi chal "
        "raha': which permissions she gave, whether Google refused the login (expired / revoked), which Drive accounts "
        "are linked, and a live test. Tell her the 'say' line and the fix in simple words."),
     "input_schema": {"type": "object", "properties": {}}},
]
GOOGLE_LABELS = {"google_status": "Google connection jaanch raha hoon"}


async def google_status(ctx: Ctx, **_):
    from .. import google_check
    return await asyncio.to_thread(google_check.diagnose, ctx.tenant_id, True)


GOOGLE_HANDLERS = {"google_status": google_status}
