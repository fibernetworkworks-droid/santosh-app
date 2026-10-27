"""The three model calls behind the video editor (each one is a plain function so tests can replace it):

watch()  - Gemini watches a source video: transcript with times, the best moments, mood, what is in it.
think()  - Claude writes / changes the edit (a vedit timeline) from the brief + what was watched.
look()   - Claude looks at a contact sheet of the finished video and says what is wrong, like a picky editor.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import re
import time
from typing import Any

log = logging.getLogger("santosh.videoedit")
INLINE_MAX = 18 * 1024 * 1024

WATCH_PROMPT = """You are a video editor's assistant. Watch this clip carefully (picture AND sound) and return ONLY JSON:
{
  "summary": "2 short lines: what happens, who is in it, where",
  "language": "main spoken language code (hi, en, mr, ta, ... or none)",
  "transcript": [{"start": 0.0, "end": 2.4, "text": "exact words spoken"}],
  "highlights": [{"start": 3.0, "end": 7.5, "why": "the strongest / most useful moment, in a few words", "score": 1-10}],
  "bad_parts": [{"start": 0.0, "end": 1.2, "why": "shaky / blurry / dead air / mistake / looking away"}],
  "products": ["things shown that a shop would sell"],
  "mood": "calm | energetic | emotional | funny | informative",
  "thumbnail_time": 4.0,
  "on_screen_text": "text already burned into the video, if any"
}
Times are seconds from the start of THIS clip, to 0.1 s, and must not pass its length (%(dur).1f s).
transcript: every spoken sentence in order, split at natural pauses, max ~10 words per item; write the words in %(script)s.
If nobody speaks, transcript is []. Up to 6 highlights, best first. Say only what is really there."""


def _gemini_client():
    from ..config import get_settings
    st = get_settings()
    if not st.gemini_api_key:
        return None, ""
    from google import genai
    model = getattr(st, "video_gemini_model", "") or getattr(st, "reels_gemini_model", "") or st.youtube_gemini_model or "gemini-2.5-flash"
    return genai.Client(api_key=st.gemini_api_key), model


def _json(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        v = json.loads(t)
        return v if isinstance(v, dict) else {}
    except ValueError:
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            return {}
        try:
            v = json.loads(m.group(0))
            return v if isinstance(v, dict) else {}
        except ValueError:
            return {}


def watch(data: bytes, mime: str, duration: float, script: str = "the language spoken, in its own script") -> dict[str, Any]:
    """Gemini watches one source clip. {} when there is no Gemini key or it fails (the edit still works, just less smart)."""
    client, model = _gemini_client()
    if client is None:
        return {}
    from google.genai import types
    try:
        if len(data) <= INLINE_MAX:
            part = types.Part.from_bytes(data=data, mime_type=mime)
        else:
            f = client.files.upload(file=io.BytesIO(data), config={"mime_type": mime})
            for _ in range(90):
                if str(getattr(f.state, "name", f.state)) != "PROCESSING":
                    break
                time.sleep(2)
                f = client.files.get(name=f.name)
            part = types.Part(file_data=types.FileData(file_uri=f.uri, mime_type=mime))
        r = client.models.generate_content(
            model=model, contents=types.Content(role="user", parts=[part, types.Part(text=WATCH_PROMPT % {"dur": duration, "script": script})]),
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1, max_output_tokens=8000))
        return _json(r.text or "")
    except Exception as e:
        log.info("video watch failed: %s", e)
        return {}


def think(system: str, prompt: str, max_tokens: int = 6000) -> dict[str, Any]:
    """Claude (the avatar's main brain) writes the edit. Returns the JSON object it answered with ({} on failure)."""
    from ..net.ai import llm
    try:
        raw = llm(system + "\nReply with ONLY one JSON object, no prose before or after.", prompt, max_tokens, timeout=180)
    except Exception as e:
        log.info("video plan failed: %s", e)
        return {}
    return _json(raw)


def look(png: bytes, system: str, prompt: str) -> dict[str, Any]:
    """Claude looks at the contact sheet of the result. {} when no vision model is available."""
    from ..net import media
    b64 = base64.b64encode(png).decode()
    try:
        raw = media._claude_see(system + "\nReply with ONLY one JSON object.", prompt, "image/png", b64, max_tokens=700)
    except Exception as e:
        log.info("video look failed: %s", e)
        raw = ""
    if not raw:
        try:
            raw = media._gemini_see(system + "\nReply with ONLY one JSON object.", prompt, "image/png", png)
        except Exception:
            raw = ""
    return _json(raw)
