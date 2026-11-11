"""v0.787 HOOLA VOCAL - the voice studio (owner: "HOOLA VOCAL ... make same 11labs for hoola end to end").

What it stands on is Hoola's OWN engines; nothing here is copied from another project:
  speech        create.service.voice     Google's prebuilt voices, when GEMINI_API_KEY is set
  clone/design  interactive.lab.voice    Chatterbox (her recorded sample) / Indic Parler (a described voice), when the GPU lab is set
  sound effects gamedesk.sfx             code-made presets (preset + seed) - not "text to sound"
  clean-up      audedit.ops              ffmpeg noise removal + voice EQ - not a model that separates voice from music
  music         create.service.song      Google Lyria, when configured

Rules kept in CODE:
  - a cloned voice needs a recorded yes; without it nothing is stored.
  - her pronunciation rules are applied by code before the words reach an engine, and the count is recorded.
  - every result is a file in her own folder with a history row; the oldest go when the limit is reached.
  - what this server cannot do is reported by connected() and SAID on the page; no control pretends.
Still one JSON file per tenant (like Hoola Interactive); jobs run inside the request and do not survive a restart."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import secrets
import threading
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.vocal")
_LOCK = threading.RLock()

LANGS = {"hi": "Hindi", "en": "English", "hinglish": "Hinglish", "mr": "Marathi", "gu": "Gujarati", "bn": "Bengali",
         "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi"}
STYLES = {"friendly": "Friendly", "calm": "Calm", "excited": "Excited", "news": "News reader", "story": "Storyteller",
          "ad": "Advert voice-over"}
MAX_TOTAL = 40000        # characters in one generation (cut into engine-sized pieces by code)
MAX_HISTORY = 200
MAX_LINES = 40
MAX_RULES = 200
MAX_VOICES = 30
MAX_PROJECTS = 40
MAX_CHAPTERS = 60
MAX_SAMPLE = 2 * 1024 * 1024
GAP_S = 0.14             # quiet between two pieces of one reading
LINE_GAP_S = 0.32        # quiet between two speakers
PREVIEW = {"en": "Hello, this is how I sound.", "mr": "Namaskar, mi asa bolto.", "hi": "Namaste, meri awaaz aisi sunai deti hai."}
EMPTY = {"voices": [], "rules": [], "history": [], "projects": []}


class VocalError(Exception):
    pass


# ------------------------------------------------------------------ storage ---
def _safe(tenant: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(tenant or "default"))[:64] or "default"


def _home(tenant: str) -> Path:
    p = Path("data") / "vocal" / _safe(tenant)
    (p / "audio").mkdir(parents=True, exist_ok=True)
    (p / "samples").mkdir(parents=True, exist_ok=True)
    return p


def _load(tenant: str) -> dict[str, Any]:
    p = _home(tenant) / "vocal.json"
    try:
        d = json.loads(p.read_text("utf-8")) if p.is_file() else {}
        if not isinstance(d, dict):
            raise ValueError
    except Exception:
        log.warning("vocal file unreadable for %s - starting empty", _safe(tenant))
        d = {}
    for k, v in EMPTY.items():
        if not isinstance(d.get(k), list):
            d[k] = list(v)
    return d


def _store(tenant: str, d: dict[str, Any]) -> None:
    p = _home(tenant) / "vocal.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    tmp.replace(p)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def _clean(s: Any, n: int) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(s or "")).strip()[:n]


# ------------------------------------------------------------------ engines ---
def engines() -> dict[str, bool]:
    from ..audedit import ops
    from ..config import get_settings
    from ..create import service as CS
    from ..interactive import lab
    r = CS.ready()
    return {"speech": bool(r.get("voice")), "lab": bool(lab.configured()), "ffmpeg": bool(ops.ffmpeg_ok()),
            "music": bool(r.get("song")), "dub": bool(r.get("dub")), "stt": bool(getattr(get_settings(), "kaan_audio", False))}


def connected() -> dict[str, bool]:
    """The honest switchboard the page reads. False = the page says "not connected" and disables the control."""
    e = engines()
    tts = e["speech"] or e["lab"]
    return {"tts": tts, "library": e["speech"], "dialogue": tts, "studio": tts, "clone": e["lab"], "design": e["lab"],
            "sfx_presets": True, "sfx_text": False, "cleanup": e["ffmpeg"], "isolate": False, "changer": False,
            "stt": e["stt"], "music": e["music"], "dub": e["dub"], "pro_clone": False, "audio_native": False,
            "agents_here": False, "api": False, "watermark": False, "rupee_meter": False}


def builtin() -> list[dict[str, Any]]:
    """Hoola's ready voices. Their names are the engine's own; the tone is the English half of Hoola's note."""
    from ..create import service as CS
    out = []
    for g, group in CS.voices().items():
        for name, note in group.items():
            out.append({"id": f"hv_{name}", "name": name, "gender": g, "tone": str(note).split(",")[-1].strip().capitalize(),
                        "kind": "hoola", "ready": True})
    return out


def _voice(d: dict[str, Any], vid: str) -> dict[str, Any]:
    for v in builtin():
        if v["id"] == vid:
            return v
    for v in d["voices"]:
        if v["id"] == vid:
            return v
    raise VocalError("That voice was not found.")


# ------------------------------------------------------------------ sound ---
def _wav_info(data: bytes) -> tuple[tuple[int, int, int], bytes]:
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            return (w.getnchannels(), w.getsampwidth(), w.getframerate()), w.readframes(w.getnframes())
    except Exception:
        raise VocalError("The engine returned sound Hoola could not read.") from None


def join_wavs(parts: list[bytes], gap: float = GAP_S) -> bytes:
    """Several readings -> one WAV, with a short quiet between them. All parts must share one format (one engine)."""
    if not parts:
        raise VocalError("Nothing was spoken.")
    fmt, frames = _wav_info(parts[0])
    quiet = b"\x00" * (int(fmt[2] * gap) * fmt[0] * fmt[1])
    out = [frames]
    for p in parts[1:]:
        f2, fr = _wav_info(p)
        if f2 != fmt:
            raise VocalError("Two voices came back in different sound formats, so they cannot be joined. Use voices of one kind.")
        out += [quiet, fr]
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(fmt[0])
        w.setsampwidth(fmt[1])
        w.setframerate(fmt[2])
        w.writeframes(b"".join(out))
    return b.getvalue()


def wav_seconds(data: bytes) -> float:
    fmt, frames = _wav_info(data)
    return round(len(frames) / (fmt[0] * fmt[1] * fmt[2]), 1)


def pieces(text: str, limit: int) -> list[str]:
    """Cut long words into engine-sized pieces at sentence ends. Her words are never rewritten."""
    out, cur = [], ""
    for s in re.split(r"(?<=[.!?।\n])\s+", text.strip()):
        s = s.strip()
        while len(s) > limit:                           # one very long sentence: cut at a space
            cut = s.rfind(" ", 0, limit)
            cut = cut if cut > limit // 2 else limit
            out.append((cur + " " + s[:cut]).strip() if cur and len(cur) + cut < limit else s[:cut].strip())
            cur, s = "", s[cut:].strip()
        if not s:
            continue
        if cur and len(cur) + 1 + len(s) > limit:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return [p for p in out if p]


def apply_rules(text: str, rules: list[dict[str, Any]], lang: str) -> tuple[str, int]:
    """Her pronunciation rules, by code: whole words only, any letter case. Returns the words to speak + how many changed."""
    n = 0
    for r in rules:
        if r.get("lang") and r["lang"] != lang:
            continue
        word, say = str(r.get("word") or ""), str(r.get("say") or "")
        if not word or not say:
            continue
        text, k = re.subn(rf"(?<!\w){re.escape(word)}(?!\w)", lambda _m, s=say: s, text, flags=re.I)
        n += k
    return text, n


async def _say(tenant: str, v: dict[str, Any], text: str, lang: str, style: str, speed: float) -> bytes:
    """One voice reads `text` (any length up to MAX_TOTAL) and one WAV comes back."""
    from ..create import service as CS
    from ..interactive import lab
    con = connected()
    if v["kind"] == "hoola":
        if not con["library"]:
            raise VocalError("The speech engine is not set up on this server (it needs GEMINI_API_KEY).")
        parts = []
        for p in pieces(text, CS.MAX_TEXT - 200):
            try:
                r = await CS.voice(p, voice_name=v["name"], language=LANGS.get(lang, "Hindi"), style=style, speed=speed)
            except CS.CreateError as e:
                raise VocalError(f"The speech engine did not answer{': ' + str(e).split(': ', 1)[1] if ': ' in str(e) else ''}.") from None
            parts.append(r["bytes"])
        return join_wavs(parts)
    if not con["clone"]:
        raise VocalError("Your own voices need the GPU voice engine, which is not connected on this server yet.")
    sample = None
    if v["kind"] == "clone":
        f = _home(tenant) / "samples" / str(v.get("sample") or "")
        if not f.is_file():
            raise VocalError("This voice's recording is missing. Add the voice again.")
        sample = f.read_bytes()
    ll = lang if lang in ("hi", "en", "mr") else "hi"
    parts = []
    for p in pieces(text, lab.MAX_TEXT - 80):
        try:
            if sample:
                parts.append(await asyncio.to_thread(lab.voice, p, lang=ll, model="chatterbox", ref_audio=sample))
            else:
                parts.append(await asyncio.to_thread(lab.voice, p, lang=ll, model="indic_parler",
                                                     description=str(v.get("description") or "")))
        except lab.LabError as e:
            raise VocalError(f"The voice engine did not answer: {str(e)[:160]}") from None
    return join_wavs(parts)


def _keep(tenant: str, data: bytes, ext: str, row: dict[str, Any]) -> dict[str, Any]:
    """Save a result as a file + a history row; drop the oldest rows (and their files) past the limit."""
    row = {"id": _id("vo"), "made": _now(), "ext": ext.lstrip("."), "size": len(data), **row}
    home = _home(tenant)
    (home / "audio" / f"{row['id']}.{row['ext']}").write_bytes(data)
    with _LOCK:
        d = _load(tenant)
        d["history"].insert(0, row)
        keep_ids = {c.get("audio") for p in d["projects"] for c in p.get("chapters", [])}
        while len(d["history"]) > MAX_HISTORY:
            i = next((k for k in range(len(d["history"]) - 1, -1, -1) if d["history"][k]["id"] not in keep_ids), -1)
            if i < 0:
                break
            old = d["history"].pop(i)
            (home / "audio" / f"{old['id']}.{old.get('ext', 'wav')}").unlink(missing_ok=True)
        _store(tenant, d)
    return row


def _check_text(text: Any) -> str:
    t = _clean(text, MAX_TOTAL + 1)
    if len(t) < 2:
        raise VocalError("Write the words to speak.")
    if len(t) > MAX_TOTAL:
        raise VocalError(f"That is over {MAX_TOTAL:,} characters. Use Studio and split it into chapters.")
    return t


# ------------------------------------------------------------------ speech ---
async def tts(tenant: str, text: Any, voice: str = "", lang: str = "hi", style: str = "friendly", speed: Any = 1.0,
              rules: bool = True) -> dict[str, Any]:
    t = _check_text(text)
    lang = lang if lang in LANGS else "hi"
    style = style if style in STYLES else "friendly"
    try:
        speed = min(1.3, max(0.8, float(speed or 1.0)))
    except (TypeError, ValueError):
        speed = 1.0
    d = _load(tenant)
    v = _voice(d, voice or builtin()[0]["id"]) if (voice or builtin()) else None
    if not v:
        raise VocalError("No voice is available on this server.")
    spoken, n = apply_rules(t, d["rules"], lang) if rules else (t, 0)
    data = await _say(tenant, v, spoken, lang, style, speed)
    return _keep(tenant, data, "wav", {"kind": "tts", "title": t[:60], "text": t[:2000], "voice": v["id"], "voice_name": v["name"],
                                       "lang": lang, "style": style, "speed": speed, "chars": len(t), "applied": n,
                                       "seconds": wav_seconds(data)})


async def dialogue(tenant: str, lines: Any, cast: Any, lang: str = "hi", style: str = "friendly") -> dict[str, Any]:
    """Several speakers, each with a voice she chose, read in order into ONE file."""
    rows = [(_clean(x.get("speaker"), 30) or "Speaker", _clean(x.get("text"), 1500)) for x in (lines or []) if isinstance(x, dict)]
    rows = [(s, t) for s, t in rows if t]
    if not rows:
        raise VocalError("Write at least one line.")
    if len(rows) > MAX_LINES:
        raise VocalError(f"Up to {MAX_LINES} lines in one dialogue.")
    cast = cast if isinstance(cast, dict) else {}
    lang = lang if lang in LANGS else "hi"
    d = _load(tenant)
    voices: dict[str, dict[str, Any]] = {}
    for s in {s for s, _ in rows}:
        if not cast.get(s):
            raise VocalError(f"Choose a voice for {s}.")
        voices[s] = _voice(d, str(cast[s]))
    if len({v["kind"] == "hoola" for v in voices.values()}) > 1:
        raise VocalError("Use either Hoola voices or your own voices in one dialogue - the two kinds cannot be joined.")
    parts, applied = [], 0
    for s, t in rows:
        spoken, n = apply_rules(t, d["rules"], lang)
        applied += n
        parts.append(await _say(tenant, voices[s], spoken, lang, style if style in STYLES else "friendly", 1.0))
    data = join_wavs(parts, LINE_GAP_S)
    script = "\n".join(f"{s}: {t}" for s, t in rows)
    return _keep(tenant, data, "wav", {"kind": "dialogue", "title": rows[0][1][:60], "text": script[:2000], "voice": "",
                                       "voice_name": ", ".join(sorted(v["name"] for v in voices.values())), "lang": lang,
                                       "chars": sum(len(t) for _, t in rows), "applied": applied, "lines": len(rows),
                                       "seconds": wav_seconds(data)})


async def preview(tenant: str, voice: str, lang: str = "hi") -> bytes:
    """A short line in one voice. Not kept in history."""
    v = _voice(_load(tenant), voice)
    return await _say(tenant, v, PREVIEW.get(lang, PREVIEW["hi"]), lang if lang in LANGS else "hi", "friendly", 1.0)


# ------------------------------------------------------------------ her voices ---
def _sound_kind(data: bytes) -> str:
    """wav / mp3 / m4a / ogg / webm by the bytes, never by the file name."""
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "mp3"
    if data[4:8] == b"ftyp":
        return "m4a"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return ""


def voice_clone(tenant: str, name: Any, path: str, consent: Any, lang: str = "hi") -> dict[str, Any]:
    """A voice from HER recording. The yes is required and its time is kept; nothing is stored without it."""
    name = _clean(name, 40)
    if not name:
        raise VocalError("Give the voice a name.")
    if consent is not True:
        raise VocalError("A voice can be added only when it is yours, or the person who spoke agreed. Tick the box to say so.")
    data = Path(path).read_bytes()
    if len(data) > MAX_SAMPLE:
        raise VocalError("The recording is over 2 MB. Use about 30 to 60 seconds.")
    kind = _sound_kind(data)
    if not kind:
        raise VocalError("That file is not a sound recording Hoola can read (wav, mp3, m4a, ogg or webm).")
    with _LOCK:
        d = _load(tenant)
        if sum(1 for v in d["voices"]) >= MAX_VOICES:
            raise VocalError(f"Up to {MAX_VOICES} voices. Remove one first.")
        v = {"id": _id("mv"), "name": name, "kind": "clone", "lang": lang if lang in LANGS else "hi", "sample": "",
             "consent_at": _now(), "made": _now(), "gender": "", "tone": "Your recording"}
        v["sample"] = f"{v['id']}.{kind}"
        (_home(tenant) / "samples" / v["sample"]).write_bytes(data)
        d["voices"].insert(0, v)
        _store(tenant, d)
    return v


def voice_design(tenant: str, name: Any, description: Any, gender: str = "") -> dict[str, Any]:
    """A voice described in words (no recording). It is spoken by the lab's described-voice model."""
    name, desc = _clean(name, 40), _clean(description, 300)
    if not name:
        raise VocalError("Give the voice a name.")
    if len(desc) < 12:
        raise VocalError("Describe the voice in a sentence: who is speaking, the tone, the pace.")
    if re.search(r"\b(sound|speak|talk)s?\s+(exactly\s+)?like\b|\bvoice of\b|\bimitat|\bimpersonat", desc, re.I):
        raise VocalError("Describe the voice itself, not a real person to copy. Hoola does not imitate named people.")
    with _LOCK:
        d = _load(tenant)
        if len(d["voices"]) >= MAX_VOICES:
            raise VocalError(f"Up to {MAX_VOICES} voices. Remove one first.")
        v = {"id": _id("mv"), "name": name, "kind": "design", "description": desc, "made": _now(),
             "gender": gender if gender in ("male", "female") else "", "tone": "Described voice"}
        d["voices"].insert(0, v)
        _store(tenant, d)
    return v


def voice_remove(tenant: str, vid: str) -> dict[str, Any]:
    with _LOCK:
        d = _load(tenant)
        v = next((x for x in d["voices"] if x["id"] == vid), None)
        if not v:
            raise VocalError("That voice was not found.")
        d["voices"].remove(v)
        if v.get("sample"):
            (_home(tenant) / "samples" / v["sample"]).unlink(missing_ok=True)    # the recording goes with the voice
        _store(tenant, d)
    return {"removed": vid}


# ------------------------------------------------------------------ dictionary ---
def rule_add(tenant: str, word: Any, say: Any, lang: str = "") -> dict[str, Any]:
    word, say = _clean(word, 60), _clean(say, 120)
    if not word or not say:
        raise VocalError("Give the word as written and how it should be said.")
    with _LOCK:
        d = _load(tenant)
        d["rules"] = [r for r in d["rules"] if not (r["word"].lower() == word.lower() and r.get("lang", "") == (lang if lang in LANGS else ""))]
        if len(d["rules"]) >= MAX_RULES:
            raise VocalError(f"Up to {MAX_RULES} words.")
        r = {"id": _id("pr"), "word": word, "say": say, "lang": lang if lang in LANGS else ""}
        d["rules"].insert(0, r)
        _store(tenant, d)
    return r


def rule_remove(tenant: str, rid: str) -> dict[str, Any]:
    with _LOCK:
        d = _load(tenant)
        d["rules"] = [r for r in d["rules"] if r["id"] != rid]
        _store(tenant, d)
    return {"removed": rid}


# ------------------------------------------------------------------ effects, clean-up, music ---
def sfx_presets() -> list[str]:
    from ..gamedesk import sfx
    return sorted(sfx.PRESETS)


def sfx(tenant: str, preset: str, seed: Any = 1) -> dict[str, Any]:
    from ..gamedesk import sfx as G
    if preset not in G.PRESETS:
        raise VocalError("Choose one of the listed sounds.")
    try:
        seed = max(1, min(9999, int(seed or 1)))
    except (TypeError, ValueError):
        seed = 1
    data, _ = G.make(preset, seed)
    return _keep(tenant, data, "wav", {"kind": "sfx", "title": f"{preset.replace('_', ' ').capitalize()} #{seed}", "text": "",
                                       "voice": "", "voice_name": "Made by code", "lang": "", "chars": 0,
                                       "seconds": wav_seconds(data), "preset": preset, "seed": seed})


def cleanup(tenant: str, path: str, name: str = "", denoise: bool = True, voice: bool = True, silence: bool = False,
            level: bool = True) -> dict[str, Any]:
    """Clean a recording with ffmpeg filters. This is NOT a model that lifts a voice out of music."""
    from ..audedit import ops
    if not ops.ffmpeg_ok():
        raise VocalError("ffmpeg is not installed on this server, so recordings cannot be cleaned here.")
    steps = [s for s, on in (({"op": "denoise"}, denoise), ({"op": "enhance_voice"}, voice),
                             ({"op": "remove_silence"}, silence), ({"op": "normalize"}, level)) if on]
    if not steps:
        raise VocalError("Choose at least one thing to do.")
    try:
        r = ops.edit(path, steps, fmt="mp3")
    except Exception as e:
        raise VocalError(f"That recording could not be cleaned: {str(e)[:140]}") from None
    return _keep(tenant, r["bytes"], "mp3", {"kind": "cleanup", "title": _clean(name, 60) or "Cleaned recording", "text": "",
                                             "voice": "", "voice_name": ", ".join(s["op"].replace("_", " ") for s in steps),
                                             "lang": "", "chars": 0, "seconds": round(float(r.get("est_seconds") or 0), 1)})


async def music(tenant: str, brief: Any, genre: str = "", lang: str = "hi", vocals: str = "instrumental", mood: str = "") -> dict[str, Any]:
    from ..create import service as CS
    if not connected()["music"]:
        raise VocalError("The music engine is not set up on this server.")
    brief = _clean(brief, 600)
    if len(brief) < 4 and not genre:
        raise VocalError("Say in a line what the music is for.")
    try:
        r = await CS.song(brief=brief, genre=_clean(genre, 40), language=LANGS.get(lang, "Hindi"),
                          vocals=_clean(vocals, 20) or "instrumental", mood=_clean(mood, 40))
    except CS.CreateError as e:
        raise VocalError(f"The music engine did not answer: {str(e)[:140]}") from None
    return _keep(tenant, r["bytes"], r.get("ext", ".mp3"), {"kind": "music", "title": brief[:60] or genre, "text": brief,
                                                            "voice": "", "voice_name": _clean(genre, 40) or "Music",
                                                            "lang": lang, "chars": 0, "seconds": 0})


# ------------------------------------------------------------------ studio: long readings ---
def project_save(tenant: str, pid: str = "", title: Any = "", voice: str = "", lang: str = "hi", chapters: Any = None) -> dict[str, Any]:
    title = _clean(title, 80) or "Untitled reading"
    chs = []
    for c in (chapters or [])[:MAX_CHAPTERS]:
        if isinstance(c, dict):
            chs.append({"title": _clean(c.get("title"), 80) or f"Chapter {len(chs) + 1}", "text": _clean(c.get("text"), MAX_TOTAL)})
    with _LOCK:
        d = _load(tenant)
        if voice:
            _voice(d, voice)
        p = next((x for x in d["projects"] if x["id"] == pid), None)
        if not p:
            if len(d["projects"]) >= MAX_PROJECTS:
                raise VocalError(f"Up to {MAX_PROJECTS} readings. Remove one first.")
            p = {"id": _id("vp"), "made": _now(), "chapters": []}
            d["projects"].insert(0, p)
        old = p.get("chapters", [])
        for i, c in enumerate(chs):                    # a chapter keeps its audio only while its words are unchanged
            if i < len(old) and old[i].get("text") == c["text"] and old[i].get("audio"):
                c.update(audio=old[i]["audio"], seconds=old[i].get("seconds", 0))
        p.update(title=title, voice=voice or p.get("voice", ""), lang=lang if lang in LANGS else "hi", chapters=chs, updated=_now())
        _store(tenant, d)
    return p


def project_remove(tenant: str, pid: str) -> dict[str, Any]:
    with _LOCK:
        d = _load(tenant)
        d["projects"] = [p for p in d["projects"] if p["id"] != pid]
        _store(tenant, d)
    return {"removed": pid}


def _project(d: dict[str, Any], pid: str) -> dict[str, Any]:
    p = next((x for x in d["projects"] if x["id"] == pid), None)
    if not p:
        raise VocalError("That reading was not found.")
    return p


async def chapter_make(tenant: str, pid: str, n: Any) -> dict[str, Any]:
    d = _load(tenant)
    p = _project(d, pid)
    try:
        c = p["chapters"][int(n)]
    except (IndexError, TypeError, ValueError):
        raise VocalError("That chapter was not found.") from None
    if not p.get("voice"):
        raise VocalError("Choose a voice for this reading first.")
    t = _check_text(c["text"])
    v = _voice(d, p["voice"])
    spoken, applied = apply_rules(t, d["rules"], p["lang"])
    data = await _say(tenant, v, spoken, p["lang"], "story", 1.0)
    row = _keep(tenant, data, "wav", {"kind": "chapter", "title": f"{p['title']} - {c['title']}"[:80], "text": t[:2000],
                                      "voice": v["id"], "voice_name": v["name"], "lang": p["lang"], "chars": len(t),
                                      "applied": applied, "seconds": wav_seconds(data), "project": pid})
    with _LOCK:
        d = _load(tenant)
        p = _project(d, pid)
        if int(n) < len(p["chapters"]) and p["chapters"][int(n)]["text"] == c["text"]:
            p["chapters"][int(n)].update(audio=row["id"], seconds=row["seconds"])
            _store(tenant, d)
    return row


def project_export(tenant: str, pid: str) -> dict[str, Any]:
    """Every chapter's reading, in order, as one file. Refuses while any chapter has not been read."""
    d = _load(tenant)
    p = _project(d, pid)
    missing = [c["title"] for c in p["chapters"] if not c.get("audio")]
    if not p["chapters"] or missing:
        raise VocalError("Read every chapter first" + (f": {', '.join(missing[:3])} still to do." if missing else "."))
    home = _home(tenant)
    parts = []
    for c in p["chapters"]:
        f = home / "audio" / f"{c['audio']}.wav"
        if not f.is_file():
            raise VocalError(f"The reading of {c['title']} is no longer kept. Read it again.")
        parts.append(f.read_bytes())
    data = join_wavs(parts, 0.9)
    return _keep(tenant, data, "wav", {"kind": "book", "title": p["title"], "text": "", "voice": p.get("voice", ""),
                                       "voice_name": f"{len(parts)} chapters", "lang": p["lang"],
                                       "chars": 0, "seconds": wav_seconds(data), "project": pid})


# ------------------------------------------------------------------ history, usage, overview ---
def history_remove(tenant: str, hid: str) -> dict[str, Any]:
    with _LOCK:
        d = _load(tenant)
        h = next((x for x in d["history"] if x["id"] == hid), None)
        if not h:
            raise VocalError("That item was not found.")
        d["history"].remove(h)
        for p in d["projects"]:
            for c in p.get("chapters", []):
                if c.get("audio") == hid:
                    c.pop("audio", None)
                    c.pop("seconds", None)
        (_home(tenant) / "audio" / f"{hid}.{h.get('ext', 'wav')}").unlink(missing_ok=True)
        _store(tenant, d)
    return {"removed": hid}


def audio_file(tenant: str, hid: str) -> tuple[Path, dict[str, Any]]:
    h = next((x for x in _load(tenant)["history"] if x["id"] == hid), None)
    f = _home(tenant) / "audio" / f"{hid}.{(h or {}).get('ext', 'wav')}"
    if not h or not re.fullmatch(r"vo_[0-9a-f]{12}", hid) or not f.is_file():
        raise VocalError("That sound was not found.")
    return f, h


def usage(d: dict[str, Any]) -> dict[str, Any]:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    rows = [h for h in d["history"] if str(h.get("made", "")).startswith(month)]
    by: dict[str, int] = {}
    for h in rows:
        by[h["kind"]] = by.get(h["kind"], 0) + 1
    return {"month": month, "made": len(rows), "characters": sum(int(h.get("chars") or 0) for h in rows),
            "minutes": round(sum(float(h.get("seconds") or 0) for h in rows) / 60, 1), "by_kind": by,
            "kept": len(d["history"]), "kept_max": MAX_HISTORY}


def overview(tenant: str) -> dict[str, Any]:
    d = _load(tenant)
    con = connected()
    mine = [{**v, "ready": con["clone"]} for v in d["voices"]]
    return {"voices": (builtin() if con["library"] else []) + mine, "hoola_voices": len(builtin()), "my_voices": len(mine),
            "rules": d["rules"], "history": d["history"], "projects": d["projects"], "usage": usage(d),
            "langs": LANGS, "styles": STYLES, "sfx": sfx_presets(),
            "limits": {"characters": MAX_TOTAL, "lines": MAX_LINES, "voices": MAX_VOICES, "sample_mb": 2, "history": MAX_HISTORY},
            "status": {"engines": engines(), "connected": con}}
