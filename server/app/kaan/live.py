"""KAAN W2 live captions: rolling-window transcription over a PCM spine.

THE SHAPE: a caption session (start) takes audio CHUNKS (chunk) as they arrive from her side
(phone mic, call stream, extension tab) and answers with the NEW captions after every chunk;
stop closes the session and hands one `kaan_transcripts` row (source='live') to diarize/minutes.

THE SPINE: every chunk is decoded by ffmpeg to 16 kHz mono s16le PCM and APPENDED to one file
per session (data/kaan_live/<id>.pcm). Mixed containers are fine (webm/opus from MediaRecorder,
wav, mp3) because each chunk is decoded on its own - the spine is pure PCM.

THE WINDOW: a transcription pass runs on [watermark - OVERLAP, end] only, cut by BYTE OFFSET
from the spine and wrapped into a wav with the stdlib `wave` module (no subprocess, exact by
construction: 16k x 2 bytes). Whisper repeats words across overlapping windows, so accepted
words must start at/after the watermark (EPS 0.02 s for float jitter) - the honest line says
borderline repeats can still slip through. The watermark advances to the window end on every
pass that ran, so silence is never re-scanned.

THE GATES: start/chunk are AUDIO INGEST - the kaan_audio gate owns them (same gate as W0, no
new switch). stop is bookkeeping on audio already on her server (the W1 law: stored bytes are
hers) plus an OPTIONAL bounded clean pass (finalize_model, <= 10 min audio). No websocket, no
daemon thread: the tool lane is request/response, one pass per chunk call - the caller sets
the cadence. LAWS: port law (hand-built, whisper stays a lazy dependency), inertness law
(importing this module touches nothing), local-first (spine + captions never leave the box).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import new_id, now, session
from . import engine as EN
from . import limits as LM
from . import vocab as VB
from .models import KaanLiveSession

LIVE_DEFAULT_MODEL = "base"      # fast on CPU for rolling passes; per-session override via ladder
MAX_CHUNK_BYTES = 5 * 1024 * 1024
MAX_SESSION_S = 2 * 3600.0       # 2 h cap on one session
MAX_CHUNKS = 2000
MIN_WINDOW_S = 1.5               # a pass needs at least this much NEW audio past the watermark
MIN_TAIL_S = 0.3                 # stop still runs a pass for a small tail (sub-MIN_WINDOW)
OVERLAP_S = 0.5                  # the window re-includes this much before the watermark
PHRASE_GAP_S = 0.6               # a word gap longer than this starts a new caption phrase
MAX_FINALIZE_S = 600.0           # the optional clean batch pass is bounded to 10 minutes
EPS = 0.02
SAMPLE_RATE, SAMPLE_WIDTH = 16000, 2
BYTES_PER_S = SAMPLE_RATE * SAMPLE_WIDTH
ENDERS = (".", "!", "?", "।")
GATE_OFF = ("Kaan abhi band hai - audio/transcript kaam ke liye owner ne 'kaan_audio' switch on nahi kiya. "
            "VPS .env mein KAAN_AUDIO=1 karein, phir yeh kaam chal jayega.")
LIVE_NOTE = ("live captions: har chunk ffmpeg se 16k mono PCM ban kar isi server par jama hota hai; "
             "har chunk par sirf NAYA hissa transcribe hota hai (window + 0.5s overlap, watermark se "
             "dupes katte hain - border par ek-shabd dobara aa sakta hai); stop par ek kn_ transcript "
             "banti hai jis par diarize/minutes chalte hain. Audio + text bahar nahi jate.")


class LiveError(EN.KaanError):
    """One honest line for her; same family as KaanError (the tool layer maps both)."""


# ---------------------------------------------------------------- pcm helpers
def _live_dir() -> Path:
    p = Path(get_settings().kaan_live_dir or "./data/kaan_live")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _decode_chunk(data: bytes) -> bytes:
    """Any container in -> 16k mono s16le PCM out (ffmpeg, stdin pipe, no temp file)."""
    try:
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
             "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "pipe:1"],
            input=data, capture_output=True, timeout=120)
    except FileNotFoundError:
        raise LiveError(EN._ffmpeg_ok()[1] or "ffmpeg server par nahi mila.")
    except subprocess.TimeoutExpired:
        raise LiveError("chunk decode mein time limit cross hui (120s) - chhota chunk bhejein.")
    if p.returncode != 0 or not p.stdout:
        tail = (p.stderr or b"")[-160:].decode(errors="replace").strip()
        raise LiveError(f"chunk decode nahi hua (ffmpeg){': ' + tail if tail else '.'}")
    return p.stdout


def _append_pcm(pcm_path: Path, data: bytes) -> None:
    with open(pcm_path, "ab") as f:
        f.write(data)


def _window_wav(pcm_path: Path, start_s: float, end_s: float, out_wav: Path) -> None:
    """Cut [start, end] from the spine by byte offset and wrap it as a wav (stdlib wave)."""
    b0 = max(0, int(round(start_s * BYTES_PER_S)))
    b1 = int(round(end_s * BYTES_PER_S))
    with open(pcm_path, "rb") as f:
        f.seek(b0)
        blob = f.read(max(0, b1 - b0))
    import wave
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(blob)


def _phrases(words: list[tuple[float, float, str]], gap_s: float = PHRASE_GAP_S) -> list[dict[str, Any]]:
    """Accepted words -> caption phrases: split on a long gap or a sentence ender."""
    out: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for ws, we, txt in words:
        if cur is None or (ws - cur["end"]) > gap_s or cur["last"].endswith(ENDERS):
            if cur is not None:
                out.append(cur)
            cur = {"start": round(ws, 3), "end": round(we, 3), "last": txt,
                   "text": txt.strip()}
        else:
            cur["end"] = round(we, 3)
            cur["last"] = txt
            cur["text"] = (cur["text"] + " " + txt.strip()).strip()
    if cur is not None:
        out.append(cur)
    for p in out:
        p.pop("last", None)
    return out


# ---------------------------------------------------------------- session helpers
def _get(tenant: str, sid: str) -> KaanLiveSession:
    with session() as s:
        r = s.scalars(select(KaanLiveSession).where(KaanLiveSession.tenant_id == tenant,
                                                    KaanLiveSession.id == sid)).first()
        if not r:
            raise LiveError(f"live session {sid} nahi mili (is tenant ka nahi, ya kabhi bani hi nahi).")
        s.expunge(r)
    return r


def _row(r: KaanLiveSession, tail: int = 10) -> dict[str, Any]:
    caps = (r.captions or {}).get("items", []) if isinstance(r.captions, dict) else []
    return {"id": r.id, "status": r.status, "model": r.model, "language": r.language,
            "duration_s": r.pcm_seconds, "watermark_s": r.watermark_s, "n_chunks": r.n_chunks,
            "n_phrases": len(caps), "captions_tail": caps[-tail:],
            "text_tail": " ".join(p.get("text", "") for p in caps[-6:])[:240],
            "transcript_id": r.transcript_id, "note": r.note,
            "created_at": r.created_at.isoformat() if r.created_at else ""}


# ---------------------------------------------------------------- the three doors
def start(tenant: str, *, model: str = "", language: str = "", conversation_id: str = "",
          vocab: bool = True, fn: Any = None) -> dict[str, Any]:
    """Open a caption session. AUDIO GATE owns it (ingest), engine must be ready.
    W3: vocab=True freezes the tenant's terms into the session prompt (initial_prompt for
    every rolling pass + the clean pass); the frozen copy keeps a session consistent."""
    if not _gate():
        raise LiveError(GATE_OFF)
    LM.check_quota_live_start(tenant)       # W6: no new session once the monthly cap is hit
    ok, why = EN.available()
    if not ok:
        raise LiveError(why)
    m = (model or LIVE_DEFAULT_MODEL).lower()
    if m not in {x["name"] for x in EN.MODEL_LADDER}:
        raise LiveError(f"model '{m}' nahi jaana. Ladder: {', '.join(x['name'] for x in EN.MODEL_LADDER)}.")
    prompt, n_terms, _trunc = VB.prompt_for(tenant) if vocab else ("", 0, 0)
    sid = new_id("kl")
    pcm_path = _live_dir() / f"{sid}.pcm"
    with session() as s:
        s.add(KaanLiveSession(id=sid, tenant_id=tenant, conversation_id=conversation_id or "",
                              model=m, language=language or "", prompt=prompt, pcm_path=str(pcm_path),
                              pcm_seconds=0.0, watermark_s=0.0, n_chunks=0,
                              captions={"items": []}, status="live", note=""))
        s.commit()
    return {"id": sid, "status": "live", "model": m, "language": language or "",
            "vocab_terms": n_terms, "vocab": "on" if vocab else "off",
            "note": LIVE_NOTE, "privacy": "spine + captions isi server par; koi bahar API nahi."}


def chunk(tenant: str, sid: str, data: bytes, *, fn: Any = None) -> dict[str, Any]:
    """One chunk in -> the NEW captions out. One rolling pass per call; caller sets the cadence."""
    if not _gate():
        raise LiveError(GATE_OFF)
    data = bytes(data or b"")
    if not data:
        raise LiveError("chunk khaali hai - audio bytes bhejein.")
    if len(data) > MAX_CHUNK_BYTES:
        raise LiveError(f"chunk {len(data) / (1024 * 1024):.1f} MB hai - {MAX_CHUNK_BYTES // (1024 * 1024)} MB tak letha hoon.")
    r = _get(tenant, sid)
    if r.status != "live":
        return _row(r)
    if r.n_chunks + 1 > MAX_CHUNKS:
        raise LiveError(f"chunk cap {MAX_CHUNKS} cross hua - session stop karke nayi shuru karein.")
    pcm_path = Path(r.pcm_path)
    _append_pcm(pcm_path, _decode_chunk(data))
    end_s = pcm_path.stat().st_size / BYTES_PER_S
    if end_s > MAX_SESSION_S:
        raise LiveError(f"session {MAX_SESSION_S / 3600:.0f} ghante ka cap cross kar gaya - ab stop karein.")

    watermark = float(r.watermark_s or 0.0)
    new_phrases: list[dict[str, Any]] = []
    ran = False
    if end_s - watermark >= MIN_WINDOW_S:
        ran = True
        w_start = max(0.0, watermark - OVERLAP_S)
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        try:
            _window_wav(pcm_path, w_start, end_s, Path(tmp.name))
            transcribe = fn or EN.transcribe
            out = transcribe(tmp.name, model=r.model, language=r.language or "",
                             task="transcribe", word_timestamps=True, initial_prompt=(r.prompt or ""))
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
        accepted: list[tuple[float, float, str]] = []
        for seg in out.get("segments") or []:
            for w in seg.get("words") or []:
                txt = (w.get("word") or "").strip()
                ws = w_start + float(w.get("start") or 0.0)
                we = w_start + float(w.get("end") or 0.0)
                if txt and ws >= watermark - EPS:
                    accepted.append((ws, we, txt))
        new_phrases = _phrases(accepted)
        watermark = max(watermark, end_s)

    with session() as s:
        row = s.scalars(select(KaanLiveSession).where(KaanLiveSession.id == sid)).first()
        if row is None:
            raise LiveError(f"live session {sid} beech mein uDD gayi.")
        caps = (row.captions or {}).get("items", []) if isinstance(row.captions, dict) else []
        if new_phrases:
            caps = caps + new_phrases
        row.captions = {"items": caps}
        row.pcm_seconds = round(end_s, 3)
        row.watermark_s = round(watermark, 3)
        row.n_chunks = r.n_chunks + 1
        row.updated_at = now()
        s.commit()
        n_total = len(caps)
    return {"id": sid, "status": "live", "duration_s": round(end_s, 3), "n_chunks": r.n_chunks + 1,
            "new": new_phrases, "n_new": len(new_phrases), "n_phrases": n_total,
            "ran": ran, "watermark_s": round(watermark, 3),
            "text_tail": " ".join(p.get("text", "") for p in caps[-6:])[:240]}


def stop(tenant: str, sid: str, *, finalize_model: str = "", fn: Any = None) -> dict[str, Any]:
    """Close the session: a tail pass for the last words, then ONE `kn_` transcript row
    (source='live') that diarize/minutes already know how to read. Idempotent."""
    r = _get(tenant, sid)
    if r.status != "live":
        out = _row(r)
        out["already_stopped"] = True
        return out
    pcm_path = Path(r.pcm_path)
    end_s = pcm_path.stat().st_size / BYTES_PER_S if pcm_path.exists() else 0.0
    watermark = float(r.watermark_s or 0.0)
    caps = (r.captions or {}).get("items", []) if isinstance(r.captions, dict) else []
    finalize = "captions"

    if end_s - watermark >= MIN_TAIL_S:                       # the last words before close
        w_start = max(0.0, watermark - OVERLAP_S)
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        try:
            _window_wav(pcm_path, w_start, end_s, Path(tmp.name))
            transcribe = fn or EN.transcribe
            out = transcribe(tmp.name, model=r.model, language=r.language or "",
                             task="transcribe", word_timestamps=True, initial_prompt=(r.prompt or ""))
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
        accepted = []
        for seg in out.get("segments") or []:
            for w in seg.get("words") or []:
                txt = (w.get("word") or "").strip()
                ws = w_start + float(w.get("start") or 0.0)
                we = w_start + float(w.get("end") or 0.0)
                if txt and ws >= watermark - EPS:
                    accepted.append((ws, we, txt))
        caps = caps + _phrases(accepted)

    # the optional clean pass: one bounded batch transcription of the whole spine
    segs_final: list[dict[str, Any]] | None = None
    fm = (finalize_model or "").lower()
    if fm:
        if fm not in {x["name"] for x in EN.MODEL_LADDER}:
            raise LiveError(f"finalize_model '{fm}' nahi jaana. Ladder: {', '.join(x['name'] for x in EN.MODEL_LADDER)}.")
        if end_s > MAX_FINALIZE_S:
            raise LiveError(f"finalize ke liye audio {end_s:.0f}s hai - {MAX_FINALIZE_S / 60:.0f} min tak ka clean pass hai; "
                            "bade session ke liye captions hi theek hain.")
        ok, why = EN.available()
        if not ok:
            raise LiveError(why)
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        try:
            _window_wav(pcm_path, 0.0, end_s, Path(tmp.name))
            transcribe = fn or EN.transcribe
            out = transcribe(tmp.name, model=fm, language=r.language or "",
                             task="transcribe", word_timestamps=True, initial_prompt=(r.prompt or ""))
            segs_final = out.get("segments") or []
            finalize = "batch"
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    text = " ".join(p.get("text", "") for p in caps).strip()
    if segs_final is not None:
        text = " ".join(s.get("text", "") for s in segs_final).strip()
    n_words = sum(len((s.get("words") or [])) for s in (segs_final or [])) or len(text.split())
    row_segs = segs_final if segs_final is not None else [
        {"start": p.get("start", 0.0), "end": p.get("end", 0.0), "text": p.get("text", "")} for p in caps]
    status = "ready" if text else "empty"
    note = "" if text else "live session mein koi baat nahi sunai di (sirf khamoshi)."
    if segs_final is not None:
        note = (note or f"clean batch pass ({fm}) se bana; live captions the rolling-window wale the.")
    kn_id = new_id("kn")
    from .models import KaanTranscript
    with session() as s:
        sess = s.scalars(select(KaanLiveSession).where(KaanLiveSession.id == sid)).first()
        if sess is None:
            raise LiveError(f"live session {sid} beech mein uDD gayi.")
        s.add(KaanTranscript(
            id=kn_id, tenant_id=tenant, conversation_id=sess.conversation_id or "", source="live",
            file_id="", file_name=f"live:{sid}", language=sess.language or "",
            task="transcribe", model=fm or sess.model, duration_s=round(end_s, 3),
            n_segments=len(row_segs), text=text, segments={"items": row_segs},
            words={"count": n_words} if n_words else None, status=status, note=note))
        sess.captions = {"items": caps}
        sess.pcm_seconds = round(end_s, 3)
        sess.watermark_s = round(max(watermark, end_s), 3)
        sess.status = "done"
        sess.transcript_id = kn_id
        sess.note = note
        sess.updated_at = now()
        s.commit()
    return {"id": sid, "status": "done", "transcript_id": kn_id, "duration_s": round(end_s, 3),
            "n_phrases": len(caps), "n_words": n_words, "finalize": finalize,
            "text_tail": text[:240], "note": note}


def get_session(tenant: str, sid: str) -> dict[str, Any]:
    return _row(_get(tenant, sid))


def list_sessions(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(KaanLiveSession).where(KaanLiveSession.tenant_id == tenant)
                         .order_by(KaanLiveSession.created_at.desc())
                         .limit(max(1, min(int(limit or 20), 100)))).all()
        return [_row(r, tail=3) for r in rows]


def active_count(tenant: str) -> int:
    with session() as s:
        return len(s.scalars(select(KaanLiveSession.id)
                             .where(KaanLiveSession.tenant_id == tenant, KaanLiveSession.status == "live")).all())


# ---------------------------------------------------------------- gate
def _gate() -> bool:
    return bool(get_settings().kaan_audio)
