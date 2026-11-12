"""Tool `audio_edit`: edit her audio (and the sound of her videos) end to end with ffmpeg on the server - trim, cut,
fade, volume, loudness, speed, pitch, noise reduction, voice clean-up, silence removal, EQ, join, voice + music with
ducking, split, convert, loudness report, waveform. All local: no key, no model, no cost."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..audedit import ops
from .tools import Ctx, ToolError

MAX_FILES = 10

GUIDE = (
    "AUDIO_EDIT GUIDE. Her audio files (voice notes, songs, podcasts, recordings) or a video's sound -> edited audio back "
    "in chat. Everything runs on the server with ffmpeg: free, no key, nothing leaves the server.\n"
    "action=run: file_ids (1-10), steps=[{op,...}] in order, format mp3|wav|m4a|ogg|opus|flac (default mp3), bitrate. Ops: "
    "trim{start,end} (keep only this part; times like 90, 1:30, 1m30s) | cut{start,end} (remove this part) | "
    "fade{in,out seconds} | volume{db or percent} | normalize{target podcast|social|music|audiobook|broadcast or a LUFS number} | "
    "speed{factor 0.25-4, pitch kept} | pitch{semitones -12..12} | denoise{strength light|medium|strong} | "
    "enhance_voice (clean + level a talking voice in one step) | remove_silence{min_silence, threshold_db, keep} | "
    "eq{bass, treble dB} | mono | stereo | sample_rate{hz} | reverse.\n"
    "action=info (length, format, loudness in LUFS, peak, a plain verdict) | convert (format change / pull the audio out of a "
    "video) | join (file_ids 2-20 in order, crossfade or gap seconds) | mix (file_ids [voice, music]: music looped to the voice, "
    "music_db quieter, ducked under speech, fade_out) | split (every seconds or at [times], up to 20 parts) | waveform (a PNG "
    "picture of the sound).\n"
    "Ringtone = trim 30 s + fade + normalize social. Podcast clean-up = enhance_voice + remove_silence. WhatsApp voice note = "
    "denoise + normalize voice_note, format m4a.\n"
    "NOT done here, say so plainly: separating vocals from music, making a voice sound like a real / famous person, writing "
    "a transcript (= kaan), making new music or speech (= Create studio). Use only music she has the right to use when mixing."
)

AUDIO_EDIT_TOOLS = [
    {"name": "audio_edit", "description": (
        "EDIT her audio or a video's sound with ffmpeg on the server (free, no key): trim / cut a part, fade, volume, "
        "loudness normalise (podcast / social / broadcast), speed without chipmunk voice, pitch, background-noise removal, "
        "voice clean-up, remove long pauses, bass / treble, mono / stereo, convert (mp3 / wav / m4a / ogg / opus / flac, "
        "or pull audio out of a video), join with crossfade, voice + background music with ducking, split into parts, "
        "loudness report, waveform picture. Actions: guide (read once) | info | run (file_ids, steps [{op,...}], format) | "
        "convert | join | mix (file_ids [voice, music]) | split | waveform. Results arrive as her files. Does NOT separate "
        "vocals, clone or impersonate voices, transcribe (kaan) or make new music (Create studio)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["guide", "info", "run", "convert", "join", "mix", "split", "waveform"]},
         "file_ids": {"type": "array", "items": {"type": "string"}},
         "steps": {"type": "array", "items": {"type": "object", "properties": {"op": {"type": "string"}}, "required": ["op"]}},
         "format": {"type": "string", "enum": list(ops.FORMATS)}, "bitrate": {"type": "integer"},
         "crossfade": {"type": "number"}, "gap": {"type": "number"},
         "music_db": {"type": "number"}, "duck": {"type": "boolean"}, "fade_out": {"type": "number"},
         "every": {"type": "string"}, "at": {"type": "array", "items": {"type": "string"}},
         "filename": {"type": "string"},
     }, "required": ["action"]}},
]
AUDIO_EDIT_LABELS = {"audio_edit": "Editing the audio"}


def _owner_path(ctx: Ctx, fid: str) -> tuple[str, str]:
    from ..mailbox import service as ms
    try:
        f = ms._file_row(ctx.tenant_id, str(fid))
    except Exception as e:
        raise ToolError(str(e))
    return f.name, f.stored_path


def _deliver(ctx: Ctx, name: str, data: bytes) -> dict[str, Any]:
    from .make_tools import _deliver as deliver
    return deliver(ctx, name, data, "hoola")


def _name(src: str, tag: str, ext: str, custom: str = "", i: int = 1, n: int = 1) -> str:
    from .make_tools import _safe
    base = (f"{custom} {i}" if n > 1 else custom) if custom else f"{Path(src).stem} {tag}".strip()
    return _safe(base, "." + ext)


def _ids(a: dict) -> list[str]:
    raw = a.get("file_ids") or ([a["file_id"]] if a.get("file_id") else [])
    out: list[str] = []
    for x in raw:
        x = str(x).strip()
        if x and x not in out:
            out.append(x)
    return out


def _need(ids: list[str], lo: int, hi: int, what: str) -> None:
    if not ids:
        raise ToolError("Which audio? Ask the user to attach the audio / video in the chat, then give its file_id.")
    if not lo <= len(ids) <= hi:
        raise ToolError(f"{what} needs {lo} to {hi} files.")


async def audio_edit(ctx: Ctx, action: str = "guide", **a: Any):
    action = (action or "guide").strip().lower()
    if action == "guide":
        return {"guide": GUIDE, "ffmpeg": ops.ffmpeg_ok(), "ops": sorted(ops.STEP_OPS), "formats": list(ops.FORMATS),
                "loudness_targets": ops.LOUDNESS}
    if not ops.ffmpeg_ok():
        raise ToolError("ffmpeg is not on the server, so audio editing is not possible right now (owner: apt install ffmpeg).")
    ids = _ids(a)
    fmt = str(a.get("format") or "mp3")
    try:
        if action == "info":
            _need(ids, 1, MAX_FILES, "info")
            out = []
            for fid in ids:
                name, path = await asyncio.to_thread(_owner_path, ctx, fid)
                try:
                    out.append({"file_id": fid, "name": name, **await asyncio.to_thread(ops.loudness, path)})
                except ops.AudioError as e:
                    out.append({"file_id": fid, "name": name, "error": str(e)})
            return {"files": out, "note": "LUFS = loudness. Podcast ~ -16, Instagram / YouTube ~ -14; peak above -1 dB can clip."}
        if action in ("run", "convert"):
            _need(ids, 1, MAX_FILES, action)
            steps = a.get("steps") or []
            if action == "run":
                ops.chain(steps, 3600.0, 48000)            # shape + names checked before any file is touched
            results = []
            for i, fid in enumerate(ids, 1):
                name, path = await asyncio.to_thread(_owner_path, ctx, fid)
                try:
                    r = await asyncio.to_thread(ops.edit if action == "run" else ops.convert, path,
                                                *([steps] if action == "run" else []), fmt, a.get("bitrate"))
                except ops.AudioError as e:
                    results.append({"file_id": fid, "name": name, "ok": False, "error": str(e)})
                    continue
                view = await asyncio.to_thread(_deliver, ctx, _name(name, "edited" if action == "run" else "", r["ext"],
                                                                  str(a.get("filename") or ""), i, len(ids)), r["bytes"])
                row = {"file_id": view["file_id"], "name": view["name"], "ok": True, "from_seconds": r["in"]["duration"],
                       "kb": round(len(r["bytes"]) / 1024, 1)}
                if action == "run":
                    row.update(steps=r["steps"], about_seconds=r["est_seconds"])
                if r["in"].get("from_video"):
                    row["note"] = "the video's sound was extracted"
                results.append(row)
            done = [r for r in results if r["ok"]]
            if not done:
                raise ToolError("No audio was made: " + "; ".join(r["error"] for r in results)[:400])
            return {"status": "done", "edited": len(done), "of": len(ids), "results": results,
                    "note": "The audio is in the chat as a file. Say in one line what changed."}
        if action == "join":
            _need(ids, 2, 20, "Joining")
            paths = [await asyncio.to_thread(_owner_path, ctx, f) for f in ids]
            r = await asyncio.to_thread(ops.join, [p for _, p in paths], a.get("crossfade") or 0, a.get("gap") or 0, fmt,
                                        a.get("bitrate"))
            view = await asyncio.to_thread(_deliver, ctx, _name("joined audio", "", r["ext"], str(a.get("filename") or "")),
                                           r["bytes"])
            return {"status": "done", "file_id": view["file_id"], "name": view["name"], "pieces": r["pieces"],
                    "about_seconds": r["est_seconds"]}
        if action == "mix":
            _need(ids, 2, 2, "Mix (first the voice, then the music)")
            (vn, vp), (_, mp) = [await asyncio.to_thread(_owner_path, ctx, f) for f in ids]
            r = await asyncio.to_thread(ops.mix, vp, mp, a.get("music_db", -18), a.get("duck", True) is not False,
                                        a.get("fade_out", 3), fmt, a.get("bitrate"))
            view = await asyncio.to_thread(_deliver, ctx, _name(vn, "with music", r["ext"], str(a.get("filename") or "")),
                                           r["bytes"])
            return {"status": "done", "file_id": view["file_id"], "name": view["name"], "about_seconds": r["est_seconds"],
                    "music_looped": r["music_looped"],
                    "note": "Use only music they have the right to use (their own / licensed)."}
        if action == "split":
            _need(ids, 1, 1, "Split")
            name, path = await asyncio.to_thread(_owner_path, ctx, ids[0])
            parts = await asyncio.to_thread(ops.split, path, a.get("every"), a.get("at"), fmt, a.get("bitrate"))
            out = []
            for i, p in enumerate(parts, 1):
                v = await asyncio.to_thread(_deliver, ctx, _name(name, f"part {i}", p["ext"]), p["bytes"])
                out.append({"file_id": v["file_id"], "name": v["name"], "from": p["from"], "to": p["to"]})
            return {"status": "done", "parts": out}
        if action == "waveform":
            _need(ids, 1, 1, "Waveform")
            name, path = await asyncio.to_thread(_owner_path, ctx, ids[0])
            png = await asyncio.to_thread(ops.waveform, path)
            v = await asyncio.to_thread(_deliver, ctx, _name(name, "waveform", "png"), png)
            return {"status": "done", "file_id": v["file_id"], "name": v["name"]}
    except ops.AudioError as e:
        raise ToolError(str(e))
    raise ToolError(f"audio_edit action '{action}' is not an action: guide | info | run | convert | join | mix | split | waveform.")


AUDIO_EDIT_HANDLERS = {"audio_edit": audio_edit}
