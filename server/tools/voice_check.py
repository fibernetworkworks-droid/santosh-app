"""Find exactly which part of the live voice call Gemini rejects.

Run on the server:  cd ~/apps/santosh-core && .venv/bin/python tools/voice_check.py
Each test opens a fresh Gemini Live session, sends one kind of input and reports what came back.
"""
import asyncio
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import init_db  # noqa: E402

st = get_settings()
init_db()
from app import voice  # noqa: E402

client = genai.Client(api_key=st.gemini_api_key, http_options={"api_version": "v1beta"})
MODEL = st.gemini_live_model


def tone(seconds=1.5, rate=16000):
    """A quiet 220 Hz hum: real-looking audio without words."""
    n = int(seconds * rate)
    return b"".join(struct.pack("<h", int(1200 * math.sin(2 * math.pi * 220 * i / rate))) for i in range(n))


def minimal():
    return types.LiveConnectConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck"))))


def full():
    return voice.live_config("Puck", "hi-IN", "User's name: test", None)


def without(field):
    def make():
        c = full()
        setattr(c, field, None)
        return c
    make.__name__ = f"full minus {field}"
    return make


async def run(name, make_cfg, send):
    try:
        async with client.aio.live.connect(model=MODEL, config=make_cfg()) as s:
            await send(s)
            got_audio = 0
            text = ""

            async def collect():
                nonlocal got_audio, text
                while True:
                    async for m in s.receive():
                        sc = m.server_content
                        if sc and sc.model_turn:
                            for p in sc.model_turn.parts or []:
                                if p.inline_data and p.inline_data.data:
                                    got_audio += len(p.inline_data.data)
                        if sc and sc.output_transcription and sc.output_transcription.text:
                            text += sc.output_transcription.text
                        if sc and sc.turn_complete:
                            return
            try:
                await asyncio.wait_for(collect(), timeout=12)
            except asyncio.TimeoutError:
                pass
            ok = got_audio > 0
            print(f"{'OK  ' if ok else 'NONE'} {name}: {got_audio} bytes of voice{(' · ' + text[:80]) if text else ''}")
    except Exception as e:
        print(f"FAIL {name}: {e}")


async def say_text(s):
    await s.send_realtime_input(text="Namaste! Ek line mein apna naam batao.")


async def say_client_content(s):
    await s.send_client_content(turns=types.Content(role="user", parts=[types.Part(text="Namaste! Ek line mein apna naam batao.")]), turn_complete=True)


async def send_audio(s):
    data = tone()
    for i in range(0, len(data), 1280):
        await s.send_realtime_input(audio=types.Blob(data=data[i:i + 1280], mime_type="audio/pcm;rate=16000"))
        await asyncio.sleep(0.04)
    await s.send_realtime_input(audio_stream_end=True)


def plus(*fields):
    """Minimal config + the listed settings taken from Santosh's real config."""
    def make():
        f = full()
        c = minimal()
        for x in fields:
            setattr(c, x, getattr(f, x))
        return c
    make.__name__ = "minimal + " + ", ".join(fields)
    return make


async def main():
    print(f"Model: {MODEL}\n")
    await run("minimal + live text", minimal, say_text)
    for f in ("system_instruction", "tools", "input_audio_transcription", "output_audio_transcription",
              "realtime_input_config", "enable_affective_dialog", "context_window_compression", "session_resumption"):
        await run(f"minimal + {f}", plus(f), say_text)
    every = ("system_instruction", "tools", "input_audio_transcription", "output_audio_transcription",
             "realtime_input_config", "enable_affective_dialog", "context_window_compression", "session_resumption")
    await run("minimal + everything except proactivity", plus(*every), say_text)
    from app import web
    try:
        r = await web.google_search("aaj ka cricket score India")
        print(f"OK   google_search: {r['answer'][:90]} ({len(r['sources'])} sources)")
    except Exception as e:
        print(f"FAIL google_search: {e}")
    try:
        r = await web.open_website("https://www.wikipedia.org")
        print(f"OK   open_website: {r['title']} ({len(r['text'])} chars)")
    except Exception as e:
        print(f"FAIL open_website: {e}")


asyncio.run(main())
