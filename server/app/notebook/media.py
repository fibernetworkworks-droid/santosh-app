"""Hoola Notebook media: Gemini text-to-speech (two hosts or one narrator, any language), MP3 encoding, and the video
assembler (each scene = a still frame with a slow zoom + its narration; scenes joined into one MP4 with subtitles).

Everything here is blocking (run it in a thread). Tests replace `tts_chunk` and need only ffmpeg."""
from __future__ import annotations

import io
import logging
import re
import shutil
import subprocess
import wave
from pathlib import Path

from ..config import get_settings

log = logging.getLogger("santosh.notebook.media")

RATE = 24000                         # Gemini TTS: 24 kHz mono 16-bit PCM
HOST_VOICES = {"Ravi": "Charon", "Priya": "Kore"}
NARRATORS = {"female": "Kore", "male": "Charon", "warm": "Sulafat", "bright": "Puck"}


class MediaError(Exception):
    pass


def tts_chunk(text: str, voices: dict[str, str] | None = None, voice: str = "") -> bytes:
    """One call to the OLDER Gemini TTS path (generate_content, legacy model). Fallback when the new TTS refuses."""
    from google.genai import Client, types
    st = get_settings()
    if not st.gemini_api_key:
        raise MediaError("Awaaz ke liye server par GEMINI_API_KEY chahiye (Google ki awaaz).")
    client = Client(api_key=st.gemini_api_key)
    if voices:
        speech = types.SpeechConfig(multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
            speaker_voice_configs=[types.SpeakerVoiceConfig(speaker=n, voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=v))) for n, v in voices.items()]))
    else:
        speech = types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice or NARRATORS["female"])))
    model = st.notebook_tts_legacy_model or "gemini-2.5-flash-preview-tts"
    resp = client.models.generate_content(model=model, contents=text,
                                          config=types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=speech))
    for part in resp.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            return part.inline_data.data
    raise MediaError("Google ki awaaz (TTS) ne audio nahi diya.")


def tts_turns(turns: list[dict], voices: dict[str, str] | None = None, voice: str = "", style: str = "") -> bytes:
    """v0.155: one call to Gemini 3.8 Flash TTS (Interactions API): turns = [{speaker, text, style}] for two hosts, or
    one turn for a narrator. Expressive: per-turn style, <laugh> / <short pause> tags, |haan| backchannels.
    Returns raw 24 kHz mono 16-bit PCM."""
    import base64
    from google import genai
    st = get_settings()
    if not st.gemini_api_key:
        raise MediaError("Awaaz ke liye server par GEMINI_API_KEY chahiye (Google ki awaaz).")
    client = genai.Client(api_key=st.gemini_api_key)
    content = []
    for t in turns:
        meta: dict = {"type": "speech_metadata"}
        if voices and t.get("speaker"):
            meta["speaker"] = t["speaker"]
        if t.get("style") or style:
            meta["style"] = (t.get("style") or style)[:120]
        content.append({"type": "text", "text": t["text"], "annotations": [meta]})
    if voices:
        speech: object = {"speakers": [{"speaker": n, "voice": v} for n, v in voices.items()]}
    else:
        speech = [{"voice": voice or NARRATORS["female"]}]
    it = client.interactions.create(model=st.notebook_tts_model, input=[{"type": "user_input", "content": content}],
                                    response_format={"type": "audio", "mime_type": "audio/l16"},
                                    generation_config={"speech_config": speech})
    data = base64.b64decode(it.output_audio.data)
    if data[:4] == b"RIFF":                      # a WAV came back anyway: keep only the samples
        with wave.open(io.BytesIO(data)) as w:
            data = w.readframes(w.getnframes())
    if not data:
        raise MediaError("Google ki awaaz (TTS) ne audio nahi diya.")
    return data


def silence(seconds: float) -> bytes:
    return b"\x00\x00" * int(RATE * seconds)


TAG = re.compile(r"<[^<>]{1,30}>")
BACK = re.compile(r"\|[^|]{1,40}\|")
LINE = re.compile(r"^(Ravi|Priya)\s*(?:\[([^\]]{1,60})\])?\s*:\s*(.+)$")


def plain(text: str) -> str:
    """Text for the older TTS (it would read tags aloud)."""
    return re.sub(r"\s{2,}", " ", BACK.sub("", TAG.sub("", text or ""))).strip()


def parse_turns(lines: list[str]) -> list[dict]:
    out = []
    for ln in lines:
        m = LINE.match(ln.strip())
        if m and m.group(3).strip():
            out.append({"speaker": m.group(1), "style": (m.group(2) or "").strip(), "text": m.group(3).strip()})
    return out


_NEW_TTS_OFF = {"until": 0.0}


def _new_tts_ok() -> bool:
    import time
    return time.time() >= _NEW_TTS_OFF["until"] and str(get_settings().notebook_tts_model or "").startswith("gemini-3")


def _new_tts_failed(e: Exception) -> None:
    import time
    log.warning("notebook: new TTS failed (%s); using the older TTS for 30 min", str(e)[:200])
    _NEW_TTS_OFF["until"] = time.time() + 1800


def speak_dialogue(lines: list[str], tone: str) -> bytes:
    """Two-host script ('Ravi [style]: ...' / 'Priya: ...') in parts (long scripts), joined into one PCM stream."""
    turns = parse_turns(lines) or [{"speaker": "Ravi", "style": "", "text": ln} for ln in lines]
    parts, cur = [], []
    for t in turns:
        cur.append(t)
        if sum(len(x["text"]) for x in cur) > 2400:
            parts.append(cur)
            cur = []
    if cur:
        parts.append(cur)
    pcm = b""
    for p in parts:
        got = b""
        if _new_tts_ok():
            try:
                got = tts_turns(p, voices=HOST_VOICES, style=f"warm, lively, natural podcast conversation in {tone}")
            except Exception as e:
                _new_tts_failed(e)
        if not got:
            got = tts_chunk(f"Read this as a warm, lively, natural podcast conversation in {tone}. Real people, not "
                            f"announcers: small reactions, natural pace:\n"
                            + "\n".join(f"{t['speaker']}: {plain(t['text'])}" for t in p), voices=HOST_VOICES)
        pcm += got + silence(0.25)
    return pcm


def speak_narration(text: str, tone: str, voice: str = "female") -> bytes:
    """One narrator (video scenes), split on sentences when long."""
    text = (text or "").strip()
    if not text:
        return silence(1.0)
    pieces, cur = [], ""
    for sent in re.split(r"(?<=[.!?।])\s+", text):
        if len(cur) + len(sent) > 1800 and cur:
            pieces.append(cur)
            cur = ""
        cur = (cur + " " + sent).strip()
    if cur:
        pieces.append(cur)
    name = NARRATORS.get(voice, voice or NARRATORS["female"])
    pcm = b""
    for p in pieces:
        got = b""
        if _new_tts_ok():
            try:
                got = tts_turns([{"text": p}], voice=name, style=f"clear, warm, engaging explainer-video narrator in {tone}")
            except Exception as e:
                _new_tts_failed(e)
        if not got:
            got = tts_chunk(f"Narrate this clearly and warmly, like a good explainer video, in {tone}:\n{plain(p)}", voice=name)
        pcm += got
    return pcm


def seconds_of(pcm: bytes) -> float:
    return len(pcm) / (RATE * 2)


def wav_bytes(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def encode_mp3(pcm: bytes) -> tuple[bytes, str]:
    """MP3 when ffmpeg is on the server (10x smaller), else WAV."""
    if shutil.which("ffmpeg"):
        try:
            r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1",
                                "-i", "pipe:0", "-codec:a", "libmp3lame", "-b:a", "64k", "-f", "mp3", "pipe:1"],
                               input=pcm, capture_output=True, timeout=600)
            if r.returncode == 0 and r.stdout:
                return r.stdout, ".mp3"
        except Exception:
            pass
    return wav_bytes(pcm), ".wav"


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt(captions: list[tuple[float, float, str]]) -> str:
    out = []
    for i, (a, b, t) in enumerate(captions, 1):
        out.append(f"{i}\n{_ts(a)} --> {_ts(b)}\n{t}\n")
    return "\n".join(out)


def _caption_lines(text: str, start: float, dur: float) -> list[tuple[float, float, str]]:
    """Narration of one scene shared out over its time by length (sentences, ~12 words a line)."""
    words = (text or "").split()
    if not words:
        return []
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 12 or re.search(r"[.!?।]$", w):
            lines.append(" ".join(cur))
            cur = []
    if cur:
        lines.append(" ".join(cur))
    total = sum(len(x) for x in lines) or 1
    out, t = [], start
    for ln in lines:
        d = dur * len(ln) / total
        out.append((t, t + d, ln))
        t += d
    return out


def assemble_video(scenes: list[dict], out_path: Path, work: Path, fps: int = 25, size: tuple[int, int] = (1280, 720)) -> dict:
    """scenes: [{png: Path, pcm: bytes, narration: str}] -> one MP4 (H.264 + AAC, faststart) + SRT captions.
    Each scene: the frame with a slow Ken Burns zoom for the narration's length + 0.6 s, short fades in / out."""
    if not shutil.which("ffmpeg"):
        raise MediaError("Video ke liye server par ffmpeg chahiye (deploy/setup_video.sh).")
    work, out_path = work.resolve(), out_path.resolve()
    work.mkdir(parents=True, exist_ok=True)
    clips, captions, t = [], [], 0.0
    w, h = size
    for i, sc in enumerate(scenes):
        wav = work / f"s{i:02d}.wav"
        pcm = sc["pcm"] + silence(0.6)
        wav.write_bytes(wav_bytes(pcm))
        dur = seconds_of(pcm)
        frames = max(int(dur * fps), fps)
        zoom_in = i % 2 == 0
        z = "min(zoom+0.00045,1.07)" if zoom_in else "if(eq(on,1),1.07,max(zoom-0.00045,1.0))"
        vf = (f"[0:v]scale={w * 2}:{h * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:"
              f"s={w}x{h}:fps={fps},fade=t=in:st=0:d=0.35,fade=t=out:st={max(dur - 0.35, 0):.2f}:d=0.35,format=yuv420p[v]")
        clip = work / f"s{i:02d}.mp4"
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(Path(sc["png"]).resolve()),
                            "-i", str(wav), "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-t", f"{dur:.3f}",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-r", str(fps),
                            "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "1", str(clip)],
                           capture_output=True, timeout=900)
        if r.returncode != 0:
            raise MediaError("ffmpeg scene: " + r.stderr.decode("utf-8", "replace")[-300:])
        clips.append(clip)
        captions += _caption_lines(sc.get("narration", ""), t, dur - 0.6)
        t += dur
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", "-movflags", "+faststart", str(out_path)], capture_output=True, timeout=900, cwd=str(work))
    if r.returncode != 0:
        raise MediaError("ffmpeg join: " + r.stderr.decode("utf-8", "replace")[-300:])
    for c in clips:
        c.unlink(missing_ok=True)
    for f in work.glob("s*.wav"):
        f.unlink(missing_ok=True)
    return {"seconds": int(round(t)), "srt": srt(captions)}


def poster_frame(video: Path, out: Path, at: float = 1.5) -> bool:
    if not shutil.which("ffmpeg"):
        return False
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(at), "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=640:-2", str(out)], capture_output=True, timeout=120)
    return r.returncode == 0 and out.exists()
