"""Hoola Awaaz worker: speaks in the owner's own (consented) voice or a designed voice, for live calls.

It runs on a GPU machine, apart from Hoola core, with its own Python environment (the speech models pin their own
torch / transformers versions). Hoola core talks to it over HTTPS / a private network with a shared key.

    phone <-> Hoola core (Gemini Live: listens, thinks, writes the words) --WebSocket--> this worker --> audio

Protocol (every request needs the header  x-worker-key: <WORKER_KEY>, or ?key= on the WebSocket):
  GET    /healthz                         engine, ready, voices, can_design, watermark
  POST   /v1/voices        (multipart)    voice_id, lang, ref_text, file=<wav>   -> make a voice from a recording
  DELETE /v1/voices/{voice_id}            forget a voice completely (reference audio + cached data)
  POST   /v1/tts           (json)         {voice_id, text, lang} -> 24 kHz mono PCM16 (short lines, previews)
  POST   /v1/design        (json)         {description, text, lang} -> 24 kHz mono WAV of a brand-new voice
  WS     /v1/stream?voice_id=&lang=       live speech for one call:
         in   {"type": "say", "gen": n, "text": "..."}   queue a piece of a reply (gen = reply number)
              {"type": "cancel", "gen": n}               drop everything of replies <= n (the user interrupted)
         out  binary: 4-byte big-endian gen + 24 kHz mono PCM16
              {"type": "done", "gen": n} after each piece | {"type": "error", "message": "..."}

Voices are stored only on this machine's disk (VOICES_DIR) and are deleted on request. This worker never decides
who may use a voice: Hoola core checks consent and ownership before it sends anything here.

Run:  WORKER_KEY=... ENGINE=chatterbox .venv/bin/python -m uvicorn worker:app --host 0.0.0.0 --port 8090
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import io
import json
import logging
import os
import re
import shutil
import struct
import threading
import time
import wave
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, Form, Header, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from engines import Engine, EngineError, load_engine

log = logging.getLogger("hoola.awaaz")

WORKER_KEY = os.environ.get("WORKER_KEY", "")
ENGINE_NAME = os.environ.get("ENGINE", "fake")
VOICES_DIR = Path(os.environ.get("VOICES_DIR", "./voices"))
MAX_PARALLEL = int(os.environ.get("MAX_PARALLEL", "2"))     # model runs at once (one GPU)
OUT_RATE = 24000                                            # what Hoola's phone app plays
MAX_REF_MB = 12

@contextlib.asynccontextmanager
async def _lifespan(_app):
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    if ENGINE_NAME != "fake":
        asyncio.get_running_loop().run_in_executor(None, _try_load)   # load the model without blocking start-up
    yield


app = FastAPI(title="Hoola Awaaz worker", lifespan=_lifespan)
_engine: Engine | None = None
_engine_error = ""
_load_lock = threading.Lock()
_gpu: asyncio.Semaphore | None = None
_VOICE_ID = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


def engine() -> Engine:
    global _engine, _engine_error
    with _load_lock:
        if _engine is None and not _engine_error:
            try:
                e = load_engine(ENGINE_NAME)
                e.load()
                _engine = e
                log.info("engine %s ready", e.name)
            except Exception as ex:   # the worker still answers /healthz so the problem can be seen
                _engine_error = f"{type(ex).__name__}: {ex}"
                log.exception("engine %s failed to load", ENGINE_NAME)
    if _engine is None:
        raise HTTPException(503, f"engine not ready: {_engine_error or 'loading'}")
    return _engine


def gpu() -> asyncio.Semaphore:
    global _gpu
    if _gpu is None:
        _gpu = asyncio.Semaphore(max(1, MAX_PARALLEL))
    return _gpu


def _try_load() -> None:
    with contextlib.suppress(HTTPException):
        engine()


def _check(key: str | None) -> None:
    if not WORKER_KEY:
        raise HTTPException(503, "WORKER_KEY is not set on the worker")
    if not key or not hmac.compare_digest(key, WORKER_KEY):
        raise HTTPException(401, "bad worker key")


def _voice_dir(voice_id: str) -> Path:
    if not _VOICE_ID.match(voice_id or ""):
        raise HTTPException(400, "bad voice_id")
    return VOICES_DIR / voice_id


# ----------------------------------------------------------------------------- audio helpers
def to_pcm16(x: np.ndarray, rate: int) -> bytes:
    """float32 [-1, 1] at `rate` -> 24 kHz mono PCM16 little endian."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if rate != OUT_RATE and len(x):
        n = int(round(len(x) * OUT_RATE / rate))
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()


def to_wav(pcm: bytes, rate: int = OUT_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def check_wav(data: bytes) -> float:
    """A readable mono/stereo 16-bit WAV of 5-60 s. Returns its length in seconds."""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            if w.getsampwidth() != 2:
                raise HTTPException(400, "WAV must be 16-bit PCM")
            seconds = w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError) as e:
        raise HTTPException(400, f"not a WAV file: {e}")
    if not 5 <= seconds <= 60:
        raise HTTPException(400, f"recording must be 5-60 s (got {seconds:.1f} s)")
    return seconds


async def _run_sync_stream(gen_fn, cancelled) -> "asyncio.Queue":
    """Run a blocking generator in a thread; its chunks come out of the returned queue (None = finished)."""
    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def work():
        try:
            for chunk in gen_fn():
                if cancelled():
                    break
                loop.call_soon_threadsafe(q.put_nowait, chunk)
        except Exception as e:   # handed to the reader
            loop.call_soon_threadsafe(q.put_nowait, e)
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    threading.Thread(target=work, daemon=True, name="awaaz-tts").start()
    return q


# ----------------------------------------------------------------------------- HTTP
@app.get("/healthz")
def healthz():
    e = _engine
    voices = sum(1 for p in VOICES_DIR.glob("*/ref.wav")) if VOICES_DIR.exists() else 0
    return {"ok": e is not None or ENGINE_NAME == "fake", "engine": ENGINE_NAME, "ready": e is not None,
            "error": _engine_error, "voices": voices, "can_design": bool(e and e.can_design),
            "watermark": bool(e and e.watermark), "sample_rate": OUT_RATE}


@app.post("/v1/voices")
async def add_voice(voice_id: str = Form(...), lang: str = Form("hi"), ref_text: str = Form(""),
                    file: UploadFile = File(...), x_worker_key: str | None = Header(None)):
    _check(x_worker_key)
    d = _voice_dir(voice_id)
    data = await file.read(MAX_REF_MB * 1024 * 1024 + 1)
    if len(data) > MAX_REF_MB * 1024 * 1024:
        raise HTTPException(413, "recording too big")
    seconds = check_wav(data)
    eng = engine()
    tmp = VOICES_DIR / f".{voice_id}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "ref.wav").write_bytes(data)
    (tmp / "meta.json").write_text(json.dumps({"lang": lang, "ref_text": ref_text[:2000], "engine": eng.name,
                                               "seconds": round(seconds, 1), "made": time.time()}))
    try:
        async with gpu():
            facts = await asyncio.to_thread(eng.prepare, tmp, tmp / "ref.wav", ref_text, lang)
    except EngineError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(422, str(e))
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        log.exception("prepare failed")
        raise HTTPException(500, f"could not make the voice: {type(e).__name__}")
    shutil.rmtree(d, ignore_errors=True)
    tmp.rename(d)
    return {"ok": True, "voice_id": voice_id, "seconds": round(seconds, 1), "engine": eng.name, **(facts or {})}


@app.delete("/v1/voices/{voice_id}")
def delete_voice(voice_id: str, x_worker_key: str | None = Header(None)):
    _check(x_worker_key)
    d = _voice_dir(voice_id)
    existed = d.exists()
    shutil.rmtree(d, ignore_errors=True)
    return {"ok": True, "deleted": existed}


class TtsIn(BaseModel):
    voice_id: str
    text: str = Field(..., min_length=1, max_length=600)
    lang: str = "hi"


@app.post("/v1/tts")
async def tts(body: TtsIn, x_worker_key: str | None = Header(None)):
    _check(x_worker_key)
    d = _voice_dir(body.voice_id)
    if not (d / "ref.wav").exists():
        raise HTTPException(404, "no such voice")
    eng = engine()

    def run() -> bytes:
        return b"".join(to_pcm16(c, eng.sample_rate) for c in eng.stream(d, body.text, body.lang))
    try:
        async with gpu():
            pcm = await asyncio.to_thread(run)
    except EngineError as e:
        raise HTTPException(422, str(e))
    return Response(pcm, media_type="audio/L16;rate=24000")


class DesignIn(BaseModel):
    description: str = Field(..., min_length=3, max_length=400)
    text: str = Field(..., min_length=3, max_length=600)
    lang: str = "hi"


@app.post("/v1/design")
async def design(body: DesignIn, x_worker_key: str | None = Header(None)):
    _check(x_worker_key)
    eng = engine()
    if not eng.can_design:
        raise HTTPException(501, "this engine cannot design voices")
    try:
        async with gpu():
            x = await asyncio.to_thread(eng.design, body.description, body.text, body.lang)
    except EngineError as e:
        raise HTTPException(422, str(e))
    return Response(to_wav(to_pcm16(x, eng.sample_rate)), media_type="audio/wav")


# ----------------------------------------------------------------------------- live calls
@app.websocket("/v1/stream")
async def stream(ws: WebSocket, voice_id: str = "", lang: str = "hi", key: str = ""):
    got = ws.headers.get("x-worker-key") or key
    if not WORKER_KEY or not got or not hmac.compare_digest(got, WORKER_KEY):
        await ws.close(code=4401)
        return
    try:
        d = _voice_dir(voice_id)
    except HTTPException:
        await ws.close(code=4400)
        return
    if not (d / "ref.wav").exists():
        await ws.close(code=4404)
        return
    try:
        eng = engine()
    except HTTPException:
        await ws.close(code=4503)
        return
    await ws.accept()
    todo: asyncio.Queue = asyncio.Queue()
    state = {"cancel": -1}
    send_lock = asyncio.Lock()

    async def send_json(obj: dict) -> None:
        async with send_lock:
            await ws.send_text(json.dumps(obj))

    async def speaker() -> None:
        while True:
            gen, text = await todo.get()
            if gen <= state["cancel"]:
                continue
            head = struct.pack(">I", gen & 0xFFFFFFFF)
            try:
                async with gpu():
                    if gen <= state["cancel"]:
                        continue
                    q = await _run_sync_stream(lambda: eng.stream(d, text, lang), lambda: gen <= state["cancel"])
                    while True:
                        chunk = await q.get()
                        if chunk is None:
                            break
                        if isinstance(chunk, Exception):
                            raise chunk
                        if gen <= state["cancel"]:
                            continue   # drain the thread's last chunk, send nothing
                        async with send_lock:
                            await ws.send_bytes(head + to_pcm16(chunk, eng.sample_rate))
            except EngineError as e:
                await send_json({"type": "error", "gen": gen, "message": str(e)})
                continue
            except Exception as e:
                log.exception("stream failed")
                await send_json({"type": "error", "gen": gen, "message": type(e).__name__})
                continue
            if gen > state["cancel"]:
                await send_json({"type": "done", "gen": gen})

    task = asyncio.create_task(speaker())
    try:
        while True:
            m = json.loads(await ws.receive_text())
            if not isinstance(m, dict):
                continue
            if m.get("type") == "say" and str(m.get("text", "")).strip():
                todo.put_nowait((int(m.get("gen", 0)), str(m["text"])[:600]))
            elif m.get("type") == "cancel":
                state["cancel"] = max(state["cancel"], int(m.get("gen", 0)))
            elif m.get("type") == "ping":
                await send_json({"type": "pong"})
    except (WebSocketDisconnect, RuntimeError, ValueError):
        pass
    finally:
        task.cancel()
        with contextlib.suppress(BaseException):
            await task
