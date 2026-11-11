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
        "Audio/video transcription (Whisper W0) + W1 diarize/minutes + W2 live captions + W3 styles/vocab "
        "+ W4 exports/gyaan. "
        "transcribe: file_id + model (default small; turbo does NOT translate) + language + task transcribe|translate "
        "(whisper X->English only) -> text, segments (per-word timing); vocab=true (default) applies the tenant's terms as an "
        "initial_prompt hint + fix_to deterministic replacement (count in note). "
        "vocab_add (term, fix_to empty or a replacement) / vocab_list / vocab_remove. "
        "diarize: id OR file_id -> TURNS cut at pauses (NOT speaker recognition); names={\"1\": \"Gupta ji\"}. "
        "minutes: id -> turn stats, keywords, action CANDIDATES. "
        "style: id + verbatim|clean|subtitles|minutes|social -> deterministic render. "
        "export: id + fmt srt|vtt|txt|json -> deterministic caption/text export (read-only). "
        "to_gyaan: id -> the transcript's own words into her gyaan corpus (gyaan_khojo will find them). "
        "live_start (model base) -> kl_ session; live_chunk (id + audio bytes) -> new captions; "
        "live_stop (id, finalize_model) -> kn_ transcript; live_get/live_list. "
        "status: gate, engine, ladder, styles, vocab, exports, stored, privacy. Audio + text stay on this server. "
        "A big file runs via santosh_kaam."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "file_id": {"type": "string"},
         "model": {"type": "string", "enum": ["", "tiny", "base", "small", "medium", "turbo", "large-v3"]},
         "language": {"type": "string"}, "task": {"type": "string", "enum": ["transcribe", "translate"]},
         "word_timestamps": {"type": "boolean"}, "id": {"type": "string"}, "q": {"type": "string"},
         "names": {"type": "object", "description": "diarize: turn number -> name, e.g. {\"1\": \"Gupta ji\"}"},
         "pause_s": {"type": "number", "description": "diarize: pause threshold for a turn cut (default 0.8s)"},
         "style": {"type": "string", "enum": ["", "verbatim", "clean", "subtitles", "minutes", "social"],
                   "description": "style action: which deterministic render"},
         "term": {"type": "string", "description": "vocab_add/remove: which term"},
         "fix_to": {"type": "string", "description": "vocab_add: empty = hint only; otherwise a deterministic replacement"},
         "fmt": {"type": "string", "enum": ["", "srt", "vtt", "txt", "json"],
                 "description": "export: which format"},
         "vocab": {"type": "boolean", "description": "transcribe/live_start: apply the tenant vocab (default true)"},
         "diarize": {"type": "string", "enum": ["", "pause_turns", "voiceprint"],
                     "description": "transcribe: name the speakers - pause_turns cuts turns at pauses; "
                                    "voiceprint matches her enrolled Awaaz Pehchaan prints (W6; needs "
                                    "KAAN_VOICEPRINT=1 + KAAN_RETENTION_DAYS>0, checked BEFORE the engine)"},
         "finalize_model": {"type": "string", "enum": ["", "tiny", "base", "small", "medium", "large-v3"],
                            "description": "live_stop: empty = transcript from the captions; a model name = a clean batch pass of up to 10 min"},
         "limit": {"type": "integer"}}, "required": ["action"]}},
]
KAAN_LABELS = {"kaan": "Listening and transcribing"}


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
                                  diarize=str(a.get("diarize") or ""),
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
                raise ValueError("For diarize give the transcript id (id=) or an audio file (file_id=).")
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
    raise ValueError(f"action '{action}' not recognised: {', '.join(_ACTIONS)}")


async def _kaan(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    if action in ("transcribe", "live_start", "live_chunk", "live_stop") and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Transcribing audio (live captions too) is for the owner only (or an approved job).")
    if action == "diarize" and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Diarize is for the owner only (or an approved job) - it also writes onto the transcript.")
    if action in ("live_get", "live_list") and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Live session details are for the owner only (or an approved job).")
    if action in ("vocab_add", "vocab_remove", "to_gyaan") and actor not in ("owner",) and not actor.startswith("approved:"):
        raise ToolError("Changing vocab is for the owner only (or an approved job) - it writes tenant data.")
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
