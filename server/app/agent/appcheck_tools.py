"""App Jaanch tool: check an APK / EXE / app file before installing (REA static analysis; the file is never run)."""
from __future__ import annotations

import asyncio
from typing import Any

from ..appcheck import service as acs
from ..appcheck.runner import ReaError
from .tools import Ctx, ToolError

APPCHECK_TOOLS = [
    {"name": "app_check", "description": (
        "Check whether an Android app file (APK / XAPK), Windows program (EXE / MSI), zip or script the user got is safe "
        "to install or open, BEFORE they do. Reads the file without running it: package, permissions (SMS / OTP reading, "
        "accessibility, device admin, overlay), hidden icon, who signed it, company name, double-extension tricks, bank / "
        "KYC / challan / wedding-card scam names. Give file_id (a file from the phone or PC), or email_id + attachment_id, "
        "or drive. Shows a verdict card. Only for safety checks of a file the user has; never for cracking, bypassing "
        "licences, cheats, or copying someone's app."),
     "input_schema": {"type": "object", "properties": {
         "file_id": {"type": "string"}, "email_id": {"type": "string"}, "attachment_id": {"type": "string"},
         "drive": {"type": "string", "description": "Drive file name, id or link"}}}},
]
APPCHECK_LABELS = {"app_check": "App ki jaanch kar raha hoon"}


async def app_check(ctx: Ctx, file_id="", email_id="", attachment_id="", drive="", **_) -> dict[str, Any]:
    src = {k: v for k, v in {"file_id": file_id, "email_id": email_id, "attachment_id": attachment_id, "drive": drive}.items()
           if v not in (None, "")}
    try:
        out = await asyncio.to_thread(acs.check, ctx.tenant_id, ctx.conversation_id, src)
    except (acs.CheckError, ReaError) as e:
        raise ToolError(str(e))
    f = out.get("facts") or {}
    return {"verdict": out["verdict"], "verdict_text": out["verdict_text"], "name": out["name"], "kind": out["kind"],
            "findings": [x["text"] for x in out.get("flags") or []][:10],
            "facts": {k: v for k, v in f.items() if k not in ("permissions", "signer_sha256") and v not in (None, "", [])},
            "permission_count": len(f.get("permissions") or []), "limits": out.get("limits") or [],
            "advice": out.get("advice", ""), "card_shown": True,
            "note": "File was never run. Never call a file 100% safe; say what was checked."}


APPCHECK_HANDLERS = {"app_check": app_check}
