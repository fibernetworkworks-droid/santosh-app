"""KAAN PACK tool: `kaan` (transcribe / status / list / get / search) — WhisperAI Wave W0.

Guards: the `kaan_audio` AUDIO gate (default OFF) sits in front of transcribe; status / list / get /
search are read-only and always allowed for the owner's side. Customers are refused (the paisa_sahayak
pattern). The heavy transcribe rides santosh_kaam on voice calls (VOICE_VIA_KAAM).
"""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["transcribe", "status", "list", "get", "search"]

KAAN_TOOLS = [
    {"name": "kaan", "description": (
        "Audio / video sun-kar likhawat (transcription; WhisperAI Wave W0). action=transcribe: file_id (chat mein "
        "bheji gayi audio/video file) + model (tiny/base/small/medium/turbo/large-v3; default small; turbo translate "
        "NAHI kar sakta) + language (hi/mr/en/... khali chhodo to khud pehchanega) + task transcribe|translate + "
        "word_timestamps (per-word timing) -> text, segments (start/end/words), language, duration. File aur transcript "
        "isi server par rehte hain - koi bahar API nahi. status: gate (kaan_audio), engine ready ya nahi + kyun nahi, "
        "model ladder, stored count, privacy line. list: pichhli transcripts (limit). get: id -> poora transcript + "
        "segments. search: q -> jis transcript mein woh baat boli gayi. NOTE: badi file ka waqt lagta hai - call par "
        "yeh santosh_kaam se chalta hai aur kaam poora hone par phone ghanti bajti hai."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "file_id": {"type": "string"},
         "model": {"type": "string", "enum": ["", "tiny", "base", "small", "medium", "turbo", "large-v3"]},
         "language": {"type": "string"}, "task": {"type": "string", "enum": ["transcribe", "translate"]},
         "word_timestamps": {"type": "boolean"}, "id": {"type": "string"}, "q": {"type": "string"},
         "limit": {"type": "integer"}}, "required": ["action"]}},
]
KAAN_LABELS = {"kaan": "Kaan se sun-kar likh raha hoon"}


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _sync(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..kaan import service as KS
    if action == "transcribe":
        data = a.get("data")
        return KS.transcribe_file(ctx.tenant_id, file_id=str(a.get("file_id") or ""), name=str(a.get("name") or ""),
                                  model=str(a.get("model") or ""),
                                  language=str(a.get("language") or ""), task=str(a.get("task") or "transcribe"),
                                  word_timestamps=a.get("word_timestamps") is not False,
                                  conversation_id=ctx.conversation_id or "",
                                  data=data if isinstance(data, (bytes, bytearray)) else None)
    if action == "status":
        return KS.status(ctx.tenant_id)
    if action == "list":
        return {"items": KS.list_transcripts(ctx.tenant_id, a.get("limit") or 20)}
    if action == "get":
        return KS.get_transcript(ctx.tenant_id, str(a.get("id") or ""))
    if action == "search":
        q = str(a.get("q") or "").strip()
        return {"q": q, "items": KS.search_transcripts(ctx.tenant_id, q, a.get("limit") or 10)}
    raise ValueError(f"action '{action}' nahi pehchana: {', '.join(_ACTIONS)}")


async def _kaan(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if action == "transcribe" and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Audio sun-kar likhna sirf owner ke liye (ya approved kaam).")
    try:
        return await asyncio.to_thread(_sync, ctx, action, a)
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        from ..kaan.engine import KaanError
        if isinstance(e, KaanError):
            raise ToolError(str(e))
        raise


KAAN_HANDLERS = {"kaan": _kaan}
