"""KAAN PACK tool: `kaan` (transcribe / status / list / get / search) — WhisperAI Wave W0.

Guards: the `kaan_audio` AUDIO gate (default OFF) sits in front of transcribe; status / list / get /
search are read-only and always allowed for the owner's side. Customers are refused (the paisa_sahayak
pattern). The heavy transcribe rides santosh_kaam on voice calls (VOICE_VIA_KAAM).
"""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["transcribe", "diarize", "minutes", "status", "list", "get", "search",
            "live_start", "live_chunk", "live_stop", "live_get", "live_list",
            "style", "vocab_add", "vocab_list", "vocab_remove",
            "export", "to_gyaan"]  # W4 grew actions (the newest-enum precedent)

KAAN_TOOLS = [
    {"name": "kaan", "description": (
        "Audio/video sun-kar likhawat (Whisper W0) + W1 diarize/minutes + W2 live captions + W3 styles/vocab "
        "+ W4 exports/gyaan. "
        "transcribe: file_id + model (default small; turbo translate NAHI) + language + task transcribe|translate "
        "(whisper X->English only) -> text, segments (per-word timing); vocab=true (default) tenant ke shabd "
        "initial_prompt hint + fix_to deterministic replacement lagata hai (note mein count). "
        "vocab_add (term, fix_to khaali ya replacement) / vocab_list / vocab_remove. "
        "diarize: id YA file_id -> pauses se TURN kate hain (speaker pehchaan NAHI); names={\"1\": \"Gupta ji\"}. "
        "minutes: id -> turn stats, keywords, action CANDIDATES. "
        "style: id + verbatim|clean|subtitles|minutes|social -> deterministic render. "
        "export: id + fmt srt|vtt|txt|json -> deterministic caption/text export (read-only). "
        "to_gyaan: id -> transcript ke apne shabd uski gyaan corpus mein (gyaan_khojo dhoondhega). "
        "live_start (model base) -> kl_ session; live_chunk (id + audio bytes) -> naye captions; "
        "live_stop (id, finalize_model) -> kn_ transcript; live_get/live_list. "
        "status: gate, engine, ladder, styles, vocab, exports, stored, privacy. Audio + text isi server par. "
        "Badi file santosh_kaam par chalti hai."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "file_id": {"type": "string"},
         "model": {"type": "string", "enum": ["", "tiny", "base", "small", "medium", "turbo", "large-v3"]},
         "language": {"type": "string"}, "task": {"type": "string", "enum": ["transcribe", "translate"]},
         "word_timestamps": {"type": "boolean"}, "id": {"type": "string"}, "q": {"type": "string"},
         "names": {"type": "object", "description": "diarize: turn number -> naam, jaise {\"1\": \"Gupta ji\"}"},
         "pause_s": {"type": "number", "description": "diarize: turn cut ka pause threshold (default 0.8s)"},
         "style": {"type": "string", "enum": ["", "verbatim", "clean", "subtitles", "minutes", "social"],
                   "description": "style action: kaunsa deterministic render"},
         "term": {"type": "string", "description": "vocab_add/remove: kaunsa shabd"},
         "fix_to": {"type": "string", "description": "vocab_add: khaali = sirf hint; warna deterministic replacement"},
         "fmt": {"type": "string", "enum": ["", "srt", "vtt", "txt", "json"],
                 "description": "export: which format"},
         "vocab": {"type": "boolean", "description": "transcribe/live_start: tenant vocab lagana hai (default true)"},
         "finalize_model": {"type": "string", "enum": ["", "tiny", "base", "small", "medium", "large-v3"],
                            "description": "live_stop: khaali = captions se transcript; model naam = 10-min tak ka clean batch pass"},
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
                                  vocab=a.get("vocab") is not False,
                                  data=data if isinstance(data, (bytes, bytearray)) else None)
    if action == "status":
        return KS.status(ctx.tenant_id)
    if action == "diarize":
        fid = str(a.get("file_id") or "")
        data = a.get("data") if isinstance(a.get("data"), (bytes, bytearray)) else None
        if fid or data is not None:
            out = KS.transcribe_file(ctx.tenant_id, file_id=fid, name=str(a.get("name") or ""),
                                     model=str(a.get("model") or ""), language=str(a.get("language") or ""),
                                     word_timestamps=a.get("word_timestamps") is not False,
                                     conversation_id=ctx.conversation_id or "", data=data)
            tid = out["id"]
        else:
            tid = str(a.get("id") or "")
            if not tid:
                raise ValueError("diarize ke liye transcript ki id (id=) ya audio file (file_id=) dijiye.")
        names = a.get("names") if isinstance(a.get("names"), dict) else None
        pause_s = float(a.get("pause_s")) if a.get("pause_s") else None
        return KS.diarize_transcript(ctx.tenant_id, tid, names=names, pause_s=pause_s)
    if action == "minutes":
        return KS.minutes(ctx.tenant_id, str(a.get("id") or ""))
    if action == "list":
        return {"items": KS.list_transcripts(ctx.tenant_id, a.get("limit") or 20)}
    if action == "get":
        return KS.get_transcript(ctx.tenant_id, str(a.get("id") or ""))
    if action == "search":
        q = str(a.get("q") or "").strip()
        return {"q": q, "items": KS.search_transcripts(ctx.tenant_id, q, a.get("limit") or 10)}
    if action == "live_start":
        return KS.live_start(ctx.tenant_id, model=str(a.get("model") or ""),
                             language=str(a.get("language") or ""),
                             conversation_id=ctx.conversation_id or "",
                             vocab=a.get("vocab") is not False)
    if action == "live_chunk":
        data = a.get("data") if isinstance(a.get("data"), (bytes, bytearray)) else None
        return KS.live_chunk(ctx.tenant_id, str(a.get("id") or ""), data or b"")
    if action == "live_stop":
        return KS.live_stop(ctx.tenant_id, str(a.get("id") or ""),
                            finalize_model=str(a.get("finalize_model") or ""))
    if action == "live_get":
        return KS.live_get(ctx.tenant_id, str(a.get("id") or ""))
    if action == "live_list":
        return {"items": KS.live_list(ctx.tenant_id, a.get("limit") or 20)}
    if action == "style":
        return KS.style_render(ctx.tenant_id, str(a.get("id") or ""), str(a.get("style") or ""))
    if action == "vocab_add":
        return KS.vocab_add(ctx.tenant_id, str(a.get("term") or ""), fix_to=str(a.get("fix_to") or ""))
    if action == "vocab_list":
        return KS.vocab_list(ctx.tenant_id)
    if action == "vocab_remove":
        return KS.vocab_remove(ctx.tenant_id, str(a.get("term") or ""))
    if action == "export":
        return KS.export_transcript(ctx.tenant_id, str(a.get("id") or ""), str(a.get("fmt") or ""))
    if action == "to_gyaan":
        return KS.to_gyaan(ctx.tenant_id, str(a.get("id") or ""))
    raise ValueError(f"action '{action}' nahi pehchana: {', '.join(_ACTIONS)}")


async def _kaan(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if action in ("transcribe", "live_start", "live_chunk", "live_stop") and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Audio sun-kar likhna (live captions bhi) sirf owner ke liye (ya approved kaam).")
    if action == "diarize" and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Diarize sirf owner ke liye (ya approved kaam) - yeh transcript par likhta bhi hai.")
    if action in ("live_get", "live_list") and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Live session ki jankari sirf owner ke liye (ya approved kaam).")
    if action in ("vocab_add", "vocab_remove", "to_gyaan") and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Vocab badalna sirf owner ke liye (ya approved kaam) - yeh tenant ka data likhta hai.")
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
