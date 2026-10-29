"""v0.259 CREATE STUDIO engines that the studio's own pages need and Video Studio does not already cover.

  * song   - a whole song (or an instrumental, a jingle, a score) from Google Lyria: genre, language, singers, mood,
             tempo, length and her lyrics (or lyrics Hoola writes) go into one prompt; the MP3 lands in her files.
  * voice  - a voice-over in any Gemini voice (the 22 named voices, or her Hoola's own call voice), with a style and a
             pace, in Hindi / Hinglish / Indian languages / English. WAV in her files.
  * dub    - dubbing of HER OWN video: Gemini listens once (who speaks when, man or woman, what they say) and writes
             the lines in each target language in the same call; Gemini TTS speaks every line in a voice matched to
             that speaker, fitted to the line's slot (sped up at most 1.3x); ffmpeg lays the new voices over the
             picture with the original sound kept quietly underneath (music and room) or removed. One MP4 per language.
             Honest limits (said in the result): voices are matched, not cloned from the speaker; lips are not
             re-synced here (lip sync is a paid Video Studio step); the original voice stays faintly under the music
             when the original sound is kept, because there is no stem separation.
Money: Gemini calls are counted by app/usage.py like every other call; a Lyria song is counted as MUSIC_USD.
Nothing is sent, shared or published from here: the files go to her chat as cards.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Any

from ..config import get_settings

log = logging.getLogger("santosh.create")

LANGS = ("Hindi", "Hinglish", "Marathi", "Tamil", "Telugu", "Bengali", "Gujarati", "Kannada", "Malayalam", "Punjabi",
         "Odia", "Urdu", "English", "Spanish", "Arabic", "French")
STYLES = {"friendly": "warm and friendly, smiling", "calm": "calm and reassuring", "excited": "excited and energetic",
          "news": "like a crisp news anchor", "story": "like a storyteller, with expression", "ad": "like a premium TV ad voice-over"}
MAX_TEXT = 5000
MAX_DUB_SECONDS = 180
MAX_DUB_MB = 200
FIT_MAX = 1.3                       # never speed a dubbed line up beyond this
TTS_FALLBACK = "gemini-2.5-flash-preview-tts"


class CreateError(Exception):
    pass


def _s():
    return get_settings()


def voices() -> dict[str, dict[str, str]]:
    from ..avatar import service as av
    return {"male": dict(av.MALE_VOICES), "female": dict(av.FEMALE_VOICES)}


def ready() -> dict[str, bool]:
    s = _s()
    return {"song": bool(s.gemini_api_key and s.studio_music_model), "voice": bool(s.gemini_api_key),
            "dub": bool(s.gemini_api_key and shutil.which("ffmpeg"))}


# ---------------------------------------------------------------- song (Google Lyria)
def song_prompt(brief: str = "", genre: str = "", language: str = "Hindi", vocals: str = "duet", mood: str = "",
                bpm: int = 0, seconds: int = 0, lyrics: str = "") -> str:
    v = (vocals or "").lower().strip()
    instrumental = v in ("none", "no vocals", "instrumental", "no")
    parts = [f"A complete, radio-ready {genre or 'Indian pop'} song" if not instrumental
             else f"A complete {genre or 'Indian'} instrumental, no vocals at all"]
    if brief.strip():
        parts.append(f"about: {brief.strip()[:600]}")
    if not instrumental:
        who = {"female": "a female lead singer", "male": "a male lead singer", "duet": "a male and female duet",
               "choir": "a lead singer with a choir"}.get(v, v or "a lead singer")
        parts.append(f"sung in {language or 'Hindi'} by {who}, clear diction")
    if mood:
        parts.append(f"mood: {mood}")
    if bpm:
        parts.append(f"tempo about {int(bpm)} BPM")
    if seconds:
        parts.append(f"about {int(seconds)} seconds long with a proper intro and ending")
    p = ", ".join(parts) + "."
    if lyrics.strip() and not instrumental:
        p += "\nUse exactly these lyrics, in this order:\n" + lyrics.strip()[:3000]
    return p


def _lyria(prompt: str) -> bytes:
    from ..studio import service as ss
    try:
        return ss._lyria(prompt)
    except ss.StudioJobError as e:
        raise CreateError(str(e)) from None


async def song(brief: str = "", genre: str = "", language: str = "Hindi", vocals: str = "duet", mood: str = "",
               bpm: int = 0, seconds: int = 0, lyrics: str = "") -> dict[str, Any]:
    if not ready()["song"]:
        raise CreateError("Gaane ke liye server par GEMINI_API_KEY aur STUDIO_MUSIC_MODEL (Google Lyria) chahiye.")
    if not (brief.strip() or lyrics.strip() or genre.strip()):
        raise CreateError("Gaana kis baare mein ho? Ek line, genre ya lyrics dijiye.")
    prompt = song_prompt(brief, genre, language, vocals, mood, bpm, seconds, lyrics)
    try:
        data = await asyncio.to_thread(_lyria, prompt)
    except CreateError:
        raise
    except Exception as e:
        log.exception("create song")
        raise CreateError(f"Gaana nahi ban paya: {str(e)[:150]}") from None
    from .. import usage
    usage.record(_s().studio_music_model, sec_out=60.0)       # PRICES["lyria"]: one song = one "minute" = MUSIC_USD
    return {"bytes": data, "ext": ".mp3", "prompt": prompt, "model": _s().studio_music_model}


# ---------------------------------------------------------------- words: screenplay + lyrics (Claude, the studio planner)
SCRIPT_SYSTEM = """You are an award-winning Indian screenwriter for ads, short films, web episodes and music videos.
Write a production-ready screenplay in standard format: numbered scene headings (1. INT./EXT. PLACE - TIME), short
present-tense action lines a camera can see, character names in capitals on their own line, an optional parenthetical,
then the dialogue. Dialogue in the language asked (Hinglish in Latin letters; other Indian languages in their own
script), natural and speakable; action lines in English. Fit the length asked (about 2.2 spoken Hindi words per second).
Hook in the first seconds, clear payoff at the end. No real famous people, no politicians, no real brands except hers,
no claims you cannot know (prices, awards, medical claims). Output ONLY the screenplay text, no notes, no markdown."""

LYRICS_SYSTEM = """You are a top Indian film and pop lyricist. Write original song lyrics, singable and rhythmic, with
section tags on their own lines ([Intro], [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Bridge], [Outro]). Use the
language asked (Hindi / Hinglish in Latin letters unless asked otherwise). A memorable chorus that repeats. No real
people, no brand names except hers, nothing copied from existing songs. Output ONLY the lyrics."""


async def write(kind: str, brief: str, fmt: str = "", length: str = "", language: str = "Hinglish", tone: str = "",
                genre: str = "", mood: str = "") -> str:
    from ..studio import service as ss
    brief = (brief or "").strip()
    if len(brief) < 4:
        raise CreateError("Pehle ek line likhiye ki yeh kis baare mein hai.")
    if kind == "script":
        system, prompt = SCRIPT_SYSTEM, (f"Brief: {brief[:2500]}\nFormat: {fmt or 'ad film'}\nLength: {length or '45 seconds'}\n"
                                         f"Dialogue language: {language or 'Hinglish'}\nTone: {tone or 'warm'}")
    elif kind == "lyrics":
        system, prompt = LYRICS_SYSTEM, (f"Song idea: {brief[:1500]}\nGenre: {genre or 'Bollywood'}\nLanguage: {language or 'Hindi'}\n"
                                         f"Mood: {mood or 'warm'}")
    else:
        raise CreateError("kind: script | lyrics")
    try:
        out = (await ss._write(system, prompt, 6000)).strip()
    except Exception as e:
        log.exception("create write")
        raise CreateError(f"Abhi likh nahi paya: {str(e)[:120]}") from None
    out = re.sub(r"^```\w*\n?|```$", "", out, flags=re.M).strip()
    if not out:
        raise CreateError("Abhi likh nahi paya; dobara try kijiye.")
    return out[:20000]


def cast_prompt(name: str, description: str, style: str = "") -> str:
    return (f"Character reference sheet of one ORIGINAL fictional character named {name or 'the character'}: "
            f"{description.strip()[:600]}. The same person shown four times side by side on a plain light studio "
            "background: front view, three-quarter view, side profile, back view; full body, identical face, hair, "
            "outfit and colours in all four; soft even light, sharp detail, no text, no logos."
            + (f" Style: {style}." if style else " Style: photoreal cinematic."))


# ---------------------------------------------------------------- voice (Gemini TTS)
def pick_voice(voice: str = "", gender: str = "") -> str:
    from ..avatar import service as av
    allv = {**av.MALE_VOICES, **av.FEMALE_VOICES}
    if voice in allv:
        return voice
    return av.DEFAULT_VOICE["f" if (gender or "").lower().startswith("f") else "m"]


def _pcm(text: str, voice: str, how: str) -> bytes:
    from google.genai import Client, types
    s = _s()
    cfg = types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))))
    client = Client(api_key=s.gemini_api_key)
    last: Exception | None = None
    for model in dict.fromkeys([s.voice_ack_tts_model, TTS_FALLBACK]):
        try:
            resp = client.models.generate_content(model=model, config=cfg, contents=f"{how}: {text}")
            pcm = next((p.inline_data.data for p in resp.candidates[0].content.parts if getattr(p, "inline_data", None)), b"")
            if pcm:
                return pcm
        except Exception as e:          # the newer TTS model can be missing on an account: fall back once
            last = e
    raise CreateError(f"Awaaz nahi ban payi{': ' + str(last)[:120] if last else ''}")


def wav_bytes(pcm: bytes, rate: int = 24000) -> bytes:
    import io
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return b.getvalue()


def how_to_say(language: str, style: str = "", speed: float = 1.0) -> str:
    st = STYLES.get((style or "").lower(), style or STYLES["friendly"])
    pace = "slightly slower than normal" if speed < 0.95 else "a little faster than normal" if speed > 1.1 else "a natural pace"
    return f"Say this in natural {language or 'Hindi'}, {st}, at {pace}"


async def voice(text: str, voice_name: str = "", language: str = "Hindi", style: str = "friendly", speed: float = 1.0,
                tenant: str = "") -> dict[str, Any]:
    if not ready()["voice"]:
        raise CreateError("Awaaz ke liye server par GEMINI_API_KEY chahiye.")
    text = (text or "").strip()
    if not text:
        raise CreateError("Kya bolna hai? Script likhiye.")
    if len(text) > MAX_TEXT:
        raise CreateError(f"Script {MAX_TEXT} akshar tak; isse chhota karke do hisson mein banaiye.")
    if voice_name in ("", "mine", "hoola") and tenant:
        from ..avatar import service as av
        a = av.get(tenant)
        voice_name = a.get("voice") or ""
        gender = a.get("gender") or "m"
    else:
        gender = ""
    v = pick_voice(voice_name, gender)
    pcm = await asyncio.to_thread(_pcm, text, v, how_to_say(language, style, speed))
    return {"bytes": wav_bytes(pcm), "ext": ".wav", "voice": v, "seconds": round(len(pcm) / 48000, 1)}


# ---------------------------------------------------------------- dubbing
LISTEN = """You are a professional dubbing script writer. Listen to this audio track of a video.
Return ONLY JSON: {"speakers": [{"id": "S1", "gender": "female|male", "note": "age / tone in 3 words"}],
"source_language": "...", "lines": [{"start": seconds, "end": seconds, "speaker": "S1", "text": "exact words spoken",
"tr": {%s}}]}
Rules: one entry per sentence or natural phrase (2-8 seconds), times in seconds with one decimal, in order, no overlaps.
"tr" holds the line translated for dubbing into each target language: natural spoken words a native would say, about
the same length as the original so it fits the same time, names / brands unchanged, Indian languages in their own
script (Hinglish in Latin letters). Skip music-only parts. Never add lines that are not spoken."""


def _ff(*args: str, timeout: int = 300) -> None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, timeout=timeout)
    if r.returncode:
        raise CreateError("Video process nahi hua: " + r.stderr.decode(errors="ignore")[-200:])


def duration(path: Path) -> float:
    probe = shutil.which("ffprobe")
    if not probe:
        return 0.0
    r = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, timeout=60)
    try:
        return float(r.stdout.decode().strip() or 0)
    except ValueError:
        return 0.0


def _json(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    return json.loads(t[t.find("{"):t.rfind("}") + 1])


def _listen(audio: bytes, langs: list[str]) -> dict[str, Any]:
    from google.genai import Client, types
    s = _s()
    model = s.video_gemini_model or s.reels_gemini_model or s.youtube_gemini_model
    tr = ", ".join(f'"{lang}": "..."' for lang in langs)
    resp = Client(api_key=s.gemini_api_key).models.generate_content(
        model=model, contents=[types.Part.from_bytes(data=audio, mime_type="audio/mp3"), LISTEN % tr],
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
    try:
        out = _json(resp.text or "")
    except (ValueError, json.JSONDecodeError):
        raise CreateError("Video ki baatein samajh nahi aayin; dobara try kijiye.") from None
    lines = [ln for ln in out.get("lines") or [] if str(ln.get("text") or "").strip()]
    if not lines:
        raise CreateError("Is video mein koi bolti hui line nahi mili.")
    out["lines"] = sorted(lines, key=lambda x: float(x.get("start") or 0))
    return out


def speaker_voices(speakers: list[dict[str, Any]]) -> dict[str, str]:
    """A different matched voice for each speaker (female / male lists in turn)."""
    from ..avatar import service as av
    pools = {"f": ["Kore", "Aoede", "Leda", "Sulafat", "Despina", "Zephyr"], "m": ["Puck", "Charon", "Orus", "Achird", "Iapetus", "Fenrir"]}
    used = {"f": 0, "m": 0}
    out = {}
    for sp in speakers:
        g = "f" if str(sp.get("gender") or "").lower().startswith("f") else "m"
        pool = [v for v in pools[g] if v in av.MALE_VOICES or v in av.FEMALE_VOICES]
        out[str(sp.get("id"))] = pool[used[g] % len(pool)]
        used[g] += 1
    return out


async def dub(video: bytes, name: str, langs: list[str], keep_sound: bool = True, voices_for: dict[str, str] | None = None,
              progress=None) -> dict[str, Any]:
    """Returns {"source_language", "speakers", "lines", "outputs": [{"language", "bytes", "seconds"}]}."""
    if not ready()["dub"]:
        raise CreateError("Dubbing ke liye server par GEMINI_API_KEY aur ffmpeg chahiye.")
    langs = [lang for lang in dict.fromkeys(str(x).strip().title() for x in langs or []) if lang]
    langs = [("Hinglish" if lang.lower() == "hinglish" else lang) for lang in langs][:4]
    if not langs:
        raise CreateError("Kis bhasha mein dub karna hai? (ek baar mein 4 tak)")
    if len(video) > MAX_DUB_MB * 1024 * 1024:
        raise CreateError(f"Video {MAX_DUB_MB} MB tak ka hona chahiye.")
    say = progress or (lambda *_: None)
    with tempfile.TemporaryDirectory(prefix="hoola_dub_") as tmp:
        d = Path(tmp)
        src = d / ("in" + (Path(name).suffix.lower() or ".mp4"))
        src.write_bytes(video)
        secs = await asyncio.to_thread(duration, src)
        if secs > MAX_DUB_SECONDS:
            raise CreateError(f"Abhi {MAX_DUB_SECONDS // 60} minute tak ka video dub hota hai (yeh {int(secs)} s ka hai). Chhota hissa bhejiye.")
        aud = d / "a.mp3"
        await asyncio.to_thread(_ff, "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(aud))
        say("listening")
        heard = await asyncio.to_thread(_listen, aud.read_bytes(), langs)
        vmap = {**speaker_voices(heard.get("speakers") or []), **{k: pick_voice(v) for k, v in (voices_for or {}).items()}}
        lines = heard["lines"]
        outputs = []
        sem = asyncio.Semaphore(4)
        for lang in langs:
            say(f"voicing {lang}")

            async def one(i: int, ln: dict[str, Any]) -> Path | None:
                text = str((ln.get("tr") or {}).get(lang) or "").strip()
                if not text:
                    return None
                v = vmap.get(str(ln.get("speaker")), pick_voice("", "m"))
                async with sem:
                    pcm = await asyncio.to_thread(_pcm, text, v, how_to_say(lang, "story"))
                f = d / f"{lang}_{i:03d}.wav"
                f.write_bytes(wav_bytes(pcm))
                return f
            clips = await asyncio.gather(*(one(i, ln) for i, ln in enumerate(lines)))
            out = d / f"dub_{lang}.mp4"
            await asyncio.to_thread(_mix, src, lines, clips, out, keep_sound, secs or 0)
            outputs.append({"language": lang, "bytes": out.read_bytes(), "seconds": round(secs, 1)})
    return {"source_language": heard.get("source_language") or "", "speakers": heard.get("speakers") or [],
            "voices": vmap, "lines": lines, "outputs": outputs}


def fit(start: float, nxt: float | None, length: float, total: float) -> float:
    """atempo for a line: it should end before the next line starts (or the video ends); never above FIT_MAX."""
    room = (nxt if nxt is not None else (total or start + length)) - start - 0.05
    if room <= 0 or length <= room:
        return 1.0
    return round(min(FIT_MAX, length / room), 3)


def _mix(src: Path, lines: list[dict[str, Any]], clips: list[Path | None], out: Path, keep_sound: bool, total: float) -> None:
    ins, chains, labels = ["-i", str(src)], [], []
    n = 0
    for i, (ln, clip) in enumerate(zip(lines, clips)):
        if not clip:
            continue
        n += 1
        ins += ["-i", str(clip)]
        start = max(0.0, float(ln.get("start") or 0))
        nxt = next((float(x.get("start") or 0) for x in lines[i + 1:]), None)
        with wave.open(str(clip)) as w:
            length = w.getnframes() / float(w.getframerate())
        tempo = fit(start, nxt, length, total)
        ms = int(start * 1000)
        chains.append(f"[{n}:a]{'atempo=' + str(tempo) + ',' if tempo != 1.0 else ''}aresample=48000,adelay={ms}|{ms}[v{n}]")
        labels.append(f"[v{n}]")
    if not labels:
        raise CreateError("Dub ke liye koi line nahi bani.")
    has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                     "-of", "csv=p=0", str(src)], capture_output=True, timeout=60).stdout.strip()) \
        if shutil.which("ffprobe") else True
    if keep_sound and has_audio:
        chains.append("[0:a]aresample=48000,volume=0.14[bed]")
        labels.insert(0, "[bed]")
    graph = ";".join(chains) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest,alimiter=limit=0.95,apad[mix]"
    _ff(*ins, "-filter_complex", graph, "-map", "0:v:0", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-shortest", str(out), timeout=900)


def stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")
