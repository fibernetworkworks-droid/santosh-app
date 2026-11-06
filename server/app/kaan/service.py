"""KAAN PACK orchestration: gate -> ingest guards -> engine -> store -> honest answers.

Everything here is hand-built on house primitives (db.session, mailbox files, the config gate).
Long files are expected to ride santosh_kaam (the kaam lane) - the handler is sync-friendly and the
tool layer runs it in a thread, exactly like the finguard / analyst packs do.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..db import new_id, now, session
from . import engine as EN
from .models import KaanTranscript

MAX_BYTES = 5 * 1024 * 1024 * 1024        # the whisperai.com ceiling, kept as OUR ceiling too (5 GB)
AUDIO_EXT = (".mp3", ".m4a", ".wav", ".ogg", ".opus", ".aac", ".flac", ".amr", ".3gp", ".webm", ".wma", ".mp4", ".mkv")
GATE_OFF = ("Kaan abhi band hai - audio/transcript kaam ke liye owner ne 'kaan_audio' switch on nahi kiya. "
            "VPS .env mein KAAN_AUDIO=1 karein, phir yeh kaam chal jayega.")


def gate_open() -> bool:
    from ..config import get_settings
    return bool(get_settings().kaan_audio)


# ---------------------------------------------------------------- ingest
def _ext_ok(name: str) -> bool:
    return name.lower().endswith(AUDIO_EXT)


def _load_bytes(tenant: str, file_id: str) -> tuple[str, bytes]:
    from ..mailbox import service as ms
    name, _mtype, data = ms.load_files(tenant, [{"type": "file", "file_id": file_id}])[0]
    return name, data


def _duration_of(path: str) -> float:
    """Best-effort duration; 0.0 when ffprobe is absent (never a failure)."""
    import shutil
    import subprocess
    ff = shutil.which("ffprobe")
    if not ff:
        return 0.0
    try:
        out = subprocess.run([ff, "-v", "error", "-show_entries", "format=duration", "-of",
                              "default=noprint_wrappers=1:nokey=1", path],
                             capture_output=True, text=True, timeout=30)
        return round(float(out.stdout.strip() or 0.0), 2)
    except Exception:
        return 0.0


def transcribe_file(tenant: str, *, file_id: str = "", name: str = "", data: bytes | None = None,
                    model: str = "", language: str = "", task: str = "transcribe",
                    word_timestamps: bool = True, conversation_id: str = "",
                    fn: Any = None, store: bool = True) -> dict[str, Any]:
    """The W0 pipeline: guards -> engine -> store -> answer. `fn` swaps the engine (tests).
    Every refusal is one honest line (KaanError / ValueError -> ToolError in the tool layer)."""
    if not gate_open():
        raise EN.KaanError(GATE_OFF)
    if data is None:
        if not file_id:
            raise ValueError("Audio file ka file_id dijiye (chat mein file bhejkar), ya naam + data.")
        name, data = _load_bytes(tenant, file_id)
    name = name or "audio"
    if not _ext_ok(name):
        raise ValueError(f"'{Path(name).suffix or name}' audio nahi lagti. Chalti hain: {', '.join(AUDIO_EXT)}")
    if len(data) > MAX_BYTES:
        raise ValueError(f"File {len(data) / (1024 ** 3):.1f} GB hai - 5 GB se upar Kaan nahi leta.")
    if not data:
        raise ValueError("File khaali hai.")
    ok, why = EN.available()
    if not ok:
        raise EN.KaanError(why)

    tmp = tempfile.NamedTemporaryFile(suffix=Path(name).suffix, delete=False)
    try:
        tmp.write(data)
        tmp.close()
        duration = _duration_of(tmp.name)
        fn = fn or EN.transcribe
        out = fn(tmp.name, model=model, language=language, task=task, word_timestamps=word_timestamps)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    segs = out.get("segments") or []
    text = (out.get("text") or "").strip()
    n_words = sum(len(s.get("words") or []) for s in segs)
    status, note = "ready", ""
    if not text and not segs:
        status, note = "empty", "Engine ko khamoshi hi mili - koi baat nahi sunai di (na koi shabd, na segment)."
    row_id = new_id("kn")
    if store:
        with session() as s:
            s.add(KaanTranscript(
                id=row_id, tenant_id=tenant, conversation_id=conversation_id or "", source="file",
                file_id=file_id or "", file_name=name, language=out.get("language", ""), task=out.get("task", task),
                model=out.get("model", ""), duration_s=duration, n_segments=len(segs), text=text,
                segments={"items": segs}, words={"count": n_words} if n_words else None,
                status=status, note=note,
            ))
            s.commit()
    return {"id": row_id, "file_name": name, "language": out.get("language", ""), "task": out.get("task", task),
            "model": out.get("model", ""), "duration_s": duration, "n_segments": len(segs), "n_words": n_words,
            "text": text, "segments": segs, "status": status, "note": note, "stored": store}


# ---------------------------------------------------------------- store reads
def get_transcript(tenant: str, tid: str) -> dict[str, Any]:
    with session() as s:
        r = s.scalars(select(KaanTranscript).where(KaanTranscript.tenant_id == tenant, KaanTranscript.id == tid)).first()
        if not r:
            raise ValueError(f"Transcript {tid} nahi mili (is tenant ka nahi, ya kabhi bani hi nahi).")
        return _row(r)


def list_transcripts(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(KaanTranscript).where(KaanTranscript.tenant_id == tenant)
                         .order_by(KaanTranscript.created_at.desc()).limit(max(1, min(int(limit or 20), 100)))).all()
        return [_row(r) for r in rows]


def search_transcripts(tenant: str, q: str, limit: int = 10) -> list[dict[str, Any]]:
    q = (q or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    with session() as s:
        rows = s.scalars(select(KaanTranscript)
                         .where(KaanTranscript.tenant_id == tenant, KaanTranscript.text.ilike(like))
                         .order_by(KaanTranscript.created_at.desc()).limit(max(1, min(int(limit or 10), 50)))).all()
        return [_row(r) for r in rows]


def _row(r: KaanTranscript) -> dict[str, Any]:
    segs = (r.segments or {}).get("items", []) if isinstance(r.segments, dict) else (r.segments or [])
    n_words = (r.words or {}).get("count", 0) if isinstance(r.words, dict) else 0
    return {"id": r.id, "file_name": r.file_name, "language": r.language, "task": r.task, "model": r.model,
            "duration_s": r.duration_s, "n_segments": r.n_segments, "n_words": n_words, "text": r.text,
            "status": r.status, "note": r.note, "created_at": r.created_at.isoformat() if r.created_at else ""}


# ---------------------------------------------------------------- status
def status(tenant: str) -> dict[str, Any]:
    ok, why = EN.available()
    with session() as s:
        n = len(s.scalars(select(KaanTranscript.id).where(KaanTranscript.tenant_id == tenant)).all())
    return {
        "gate": "ON" if gate_open() else "OFF",
        "gate_note": "" if gate_open() else "VPS .env mein KAAN_AUDIO=1 karne par chalega (default OFF - recording ka faisla owner ka hai).",
        "engine": "ready" if ok else "nahi",
        "engine_note": "" if ok else why,
        "default_model": EN.default_model(),
        "ladder": [{"name": m["name"], "params": m["params"], "note": m["note"]} for m in EN.MODEL_LADDER],
        "stored": n,
        "privacy": "audio + transcript isi server par rehte hain; koi bahar API is path par nahi.",
    }
