"""v0.999.90 HOOLA VOCAL GLOBAL - "Hoola Auto": which engine does each job in each language, and what it costs.

The mix (docs/research/elevenlabs/01_BUILD_OR_BUY.md):
- Gemini voice for every language it speaks: speech, dialogue, readings, clone, design, remix.
- ElevenLabs for the languages Gemini lacks, the premium voice, the voice changer, voice out of music, sound effects
  from words and dubbing in the speakers' own voices.
- Hoola's own server for clean-up, joining, game sounds and conversions (free).

Prices are estimates from each engine's own list price. 1 credit = $0.001 of engine cost, the Hoola Credits rule.
"""
from __future__ import annotations

from typing import Any

from . import eleven, langs as L

CHARS_PER_MIN = 900          # about 15 characters a second of natural speech
GEMINI_USD_MIN = 9.0 / 1e6 * 25 * 60   # $9 per 1M audio tokens x 25 tokens a second = ~$0.0135 a minute


def gemini_ready() -> bool:
    from ..create import service as CS
    return bool(CS.ready().get("voice"))


def table() -> list[dict[str, Any]]:
    from ..audedit import ops
    from ..interactive import lab
    g, e = gemini_ready(), eleven.ready()
    return [
        {"id": "gemini", "name": "Gemini voice", "does": "Speech, dialogue, audiobooks, clone, design and remix a voice",
         "langs": f"{sum(1 for x in L.LANGS if x['gemini'])} languages · Standard", "state": "ready" if g else "needs_key",
         "why": "" if g else "Needs GEMINI_API_KEY on the server."},
        {"id": "eleven", "name": "ElevenLabs (premium)",
         "does": "Premium voices, more languages (Zulu, Urdu, Yoruba...), voice changer, voice out of music, sound effects from words, dubbing in their own voices",
         "langs": f"{sum(1 for x in L.LANGS if x['eleven4'] or x['eleven3'])} languages · Premium", "state": "ready" if e else "needs_key",
         "why": "" if e else "Needs ELEVENLABS_API_KEY in the server's .env."},
        {"id": "lab", "name": "Hoola GPU lab", "does": "Your own voices when Google's cloning is not available",
         "langs": "Hindi, English, Marathi", "state": "ready" if lab.configured() else "off",
         "why": "" if lab.configured() else "The GPU lab is not connected."},
        {"id": "server", "name": "Hoola server", "does": "Noise clean-up, loudness, joining, game sounds, file formats",
         "langs": "Any language · Free", "state": "ready" if ops.ffmpeg_ok() else "off",
         "why": "" if ops.ffmpeg_ok() else "ffmpeg is not installed."},
    ]


def pick_speech(lang: str, voice: dict | None = None, engine: str = "auto") -> str:
    """The engine that reads this language in this voice, or raises a plain refusal. Never another language."""
    v = voice or {}
    if v.get("engine") == "eleven" or engine == "eleven":
        if not eleven.ready():
            raise ValueError("Premium voices need an ElevenLabs key on the server.")
        if lang not in ("", "auto") and not L.eleven_speaks(lang):
            raise ValueError(f"The premium engine does not speak {L.name_of(lang)}. Choose a Standard voice.")
        return "eleven"
    if v.get("engine") == "lab":
        return "lab"
    auto = lang in ("", "auto")
    if auto or L.gemini_speaks(lang):
        if gemini_ready():
            return "gemini"
        if engine == "gemini" or not eleven.ready():
            raise ValueError("The speech engine is not set up on this server (it needs GEMINI_API_KEY).")
    if (auto or L.eleven_speaks(lang)) and eleven.ready() and engine != "gemini":
        return "eleven"
    if L.eleven_speaks(lang):
        raise ValueError(f"{L.name_of(lang)} is spoken only by the premium engine, which needs an ElevenLabs key on the server.")
    if lang in L.BY_CODE or lang:
        raise ValueError(f"No voice engine Hoola has speaks {L.name_of(lang) or lang} yet. Nothing was read in another language.")
    raise ValueError("No voice engine is set up on this server.")


def credits(usd: float) -> int:
    return max(1, round(usd * 1000))


def quote(job: str, chars: int = 0, seconds: float = 0.0, takes: int = 1, engine: str = "gemini") -> dict[str, Any]:
    """What a job will cost, before she taps. Minutes come from the characters (speech) or the seconds (sound)."""
    takes = max(1, min(int(takes or 1), 4))
    mins = (chars / CHARS_PER_MIN) if chars else (seconds / 60.0)
    mins = max(mins, 0.05)
    if job in ("tts", "dialogue", "chapter", "dub_matched"):
        per = eleven.USD_MIN["tts"] if engine == "eleven" else GEMINI_USD_MIN
        usd = per * mins * (takes if job == "tts" else 1) * (4 if job == "dub_matched" else 1)
    elif job == "change":
        usd = eleven.USD_MIN["change"] * mins
    elif job == "isolate":
        usd = eleven.USD_MIN["isolate"] * mins
    elif job == "sfx":
        usd = eleven.USD_MIN["sfx"] * max(seconds or 5.0, 1.0) / 60.0 * takes
    elif job == "dub_own":
        usd = eleven.USD_MIN["dub"] * mins
    elif job in ("clone", "design", "remix"):
        usd = GEMINI_USD_MIN * 0.5 * (3 if job == "design" else 1)
    else:
        usd = 0.0
    c = credits(usd) if usd else 0
    name = {"gemini": "Gemini voice", "eleven": "ElevenLabs", "lab": "Hoola GPU lab", "server": "Hoola server"}.get(engine, engine)
    line = (f"{name} · about {c} credit{'' if c == 1 else 's'} (≈ ${usd:.3f})" if c else f"{name} · free") + " · nothing is spent until you tap"
    return {"credits": c, "usd": round(usd, 4), "engine": engine, "engine_name": name, "line": line}


def prices() -> list[dict[str, Any]]:
    rows = [("Speech, 1 minute", "gemini", quote("tts", chars=CHARS_PER_MIN)),
            ("Premium speech, 1 minute", "eleven", quote("tts", chars=CHARS_PER_MIN, engine="eleven")),
            ("Clone or design a voice", "gemini", quote("design")),
            ("Dialogue / podcast, 1 minute", "gemini", quote("dialogue", chars=CHARS_PER_MIN)),
            ("Audiobook chapter, 15 minutes", "gemini", quote("chapter", chars=CHARS_PER_MIN * 15)),
            ("Voice changer, 1 minute", "eleven", quote("change", seconds=60, engine="eleven")),
            ("Voice out of music, 1 minute", "eleven", quote("isolate", seconds=60, engine="eleven")),
            ("Sound effect, 4 takes of 5 s", "eleven", quote("sfx", seconds=5, takes=4, engine="eleven")),
            ("Dub in their own voices, 1 minute", "eleven", quote("dub_own", seconds=60, engine="eleven")),
            ("Dub in matched voices, 1 minute", "gemini", quote("dub_matched", seconds=60)),
            ("Noise clean-up", "server", {"credits": 0, "usd": 0.0})]
    return [{"job": j, "engine": e, "credits": q["credits"], "usd": q["usd"]} for j, e, q in rows]
