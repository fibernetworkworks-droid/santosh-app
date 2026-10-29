"""REA Khoj: the avatar can reverse-engineer an app / program / file it has, statically, on user call.

Same locked-down REA client as App Jaanch, but investigation-shaped: the model drives the loop itself
(overview -> classes -> class -> method -> refs), exactly REA's own agent flow. The file is never run,
never uploaded anywhere, never re-distributed. Findings are data about how a thing works, with evidence.

Safety framing (carried from App Jaanch and App Review): REA Khoj is for LEARNING how a feature works so
the owner can build their own. It refuses to crack, unlock paid features, bypass licence / anti-cheat /
DRM, dump credentials, or copy someone's app verbatim. The description below tells the model the same.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..appcheck import khoj
from ..appcheck.runner import ReaError
from .tools import Ctx, ToolError

REA_TOOLS = [
    {"name": "rea_khoj", "description": (
        "Read a program / app file (.exe .apk .dll .so .jar) on the server WITHOUT running it: what it does, its "
        "endpoints / URLs. Reverse-engineering = REA static analysis, never the cloud PC. action=endpoints lists every "
        "URL, host, API path and IP written inside it (works even without the REA engine; full list saved as a "
        "dataset for data_read / doc_studio data=). Use it when the user asks 'yeh app ka X feature kaise kaam karta hai', 'is app mein yeh kya hota hai', "
        "'yeh .exe / .dll / .so / .db / model file kya karta hai?', or 'saboot ke saath samjhao'. The avatar drives the "
        "investigation itself: call action=overview first, then for an APK run action=classes (query a name), "
        "action=class (class_name -> methods/fields), action=method (class_name + method_name + overload_index -> "
        "decompiled body + smali fallback), action=refs (who uses a class/method), action=signature (APK signers + "
        "certificates). For an EXE/DLL overview returns PE imports/cert/load-config + .NET metadata; for an ELF/.ko "
        "exports + build notes + go/rust; for a JS/Electron app the module graph; for a SQLite/BEAM/.pyc/.ips/.dtb/"
        "model/.gguf/EVM artifact the matching static inspector. Sources are the same as app_check: file_id (a file "
        "from the phone or PC), email_id + attachment_id, or drive (a Drive file name / id / link). The file is copied "
        "into a per-user REA cache so follow-up calls (class / method / refs) keep working across turns; it is never "
        "executed and never re-uploaded. Report findings in plain words with the evidence (quote a few decompiled "
        "lines), and say what is NOT known. Refuse to crack a licence, unlock paid features, bypass anti-cheat / DRM, "
        "dump credentials, or copy code byte-for-byte - REA Khoj is to LEARN and reimplement, never to steal. If REA is "
        "not installed on this server, action=status says so and you tell the user plainly."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["overview", "classes", "class", "method", "refs", "signature", "status",
                                                      "endpoints"]},
         "file_id": {"type": "string"}, "email_id": {"type": "string"}, "attachment_id": {"type": "string"},
         "drive": {"type": "string", "description": "Drive file name, id or link"},
         "query": {"type": "string", "description": "for action=classes: class-name substring to search (empty = all)"},
         "class_name": {"type": "string", "description": "fully-qualified class, e.g. com.example.MainActivity"},
         "method_name": {"type": "string"}, "overload_index": {"type": "integer", "default": 0},
     }, "required": ["action"]}},
]
REA_LABELS = {"rea_khoj": "REA se khangal raha hoon"}


def _src(args: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in {"file_id": args.get("file_id"), "email_id": args.get("email_id"),
                             "attachment_id": args.get("attachment_id"), "drive": args.get("drive")}.items()
            if v not in (None, "")}


async def rea_khoj(ctx: Ctx, action: str = "status", file_id: str = "", email_id: str = "",
                   attachment_id: str = "", drive: str = "", query: str = "", class_name: str = "",
                   method_name: str = "", overload_index: int = 0, **_) -> dict[str, Any]:
    if action == "status":
        return khoj.status()
    src = _src({"file_id": file_id, "email_id": email_id, "attachment_id": attachment_id, "drive": drive})
    if not src:
        raise ToolError("Kaunsi file? file_id (phone / PC se aayi file), email attachment, ya Drive file dijiye.")
    try:
        return await asyncio.to_thread(khoj.run, ctx.tenant_id, src, action,
                                       query=query, class_name=class_name, method_name=method_name,
                                       overload_index=overload_index)
    except (khoj.KhojError, ReaError) as e:
        raise ToolError(str(e))


REA_HANDLERS = {"rea_khoj": rea_khoj}
