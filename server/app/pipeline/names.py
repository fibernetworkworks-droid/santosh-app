"""Board model names -> the id the Box calls (plan 8.2.2). Pure, tested."""
from __future__ import annotations

import re

# hand-checked: board name (normalised) -> OpenRouter id
ALIAS = {
    "dreamina seedance 2.0": "bytedance/seedance-2.0", "dreamina seedance 2.5": "bytedance/seedance-2.5",
    "minimax h3": "minimax/hailuo-3", "happyhorse 1.0": "alibaba/happyhorse-1.0", "veo 3.1": "google/veo-3.1",
    "veo 3.1 fast": "google/veo-3.1-fast", "grok imagine video": "x-ai/grok-imagine-video", "wan 2.7": "alibaba/wan-2.7",
    "wan 2.6": "alibaba/wan-2.6", "runway gen 4.5": "runway/gen-4.5", "kling 3.0 pro": "kwaivgi/kling-v3.0-pro",
    "hailuo 2.3": "minimax/hailuo-2.3", "kling o1 pro": "kwaivgi/kling-video-o1",
    "flux 3 video": "black-forest-labs/flux-3-video", "gemini 3.1 flash image": "google/gemini-3.1-flash-image",
    "qwen image 3.0 pro": "qwen/qwen-image-3-pro", "mai image 2.5": "microsoft/mai-image-2.5",
    "gemini 3.1 flash lite image": "google/gemini-3.1-flash-lite-image",
    "seedream 5.0 pro": "bytedance-seed/seedream-5-0-pro", "gemini 3 pro image": "google/gemini-3-pro-image",
    "qwen image 2.1": "qwen/qwen-image-2.1-pro", "minimax h3 image": "minimax/minimax-h3-image",
    "flux.2 [max]": "black-forest-labs/flux.2-max", "flux.2 [flex]": "black-forest-labs/flux.2-flex",
    "flux.2 [pro]": "black-forest-labs/flux.2-pro", "seedream 4.5": "bytedance-seed/seedream-4.5",
    "seedream 5.0 lite": "bytedance-seed/seedream-5-0-lite",
    "recraft v4.1 utility pro": "recraft/recraft-v4.1-utility-pro", "recraft v4.1 pro": "recraft/recraft-v4.1-pro",
    "gemini 2.5 flash image": "google/gemini-2.5-flash-image", "gpt image 2": "openai/gpt-image-2",
    "muse wonder full": "meta/muse-wonder",
}

# models no OpenRouter route carries (research 05 / D11 / D12): normalised board name -> route
# status: ready | check_terms (read the provider's terms first) | check_model (confirm the id serves this model) |
#         needs_permission (left out of every table)
ROUTES = {
    "reve 2.1": {"route": "fal", "id": "reve/2.1/text-to-image", "status": "check_model"},
    "ideogram 4.0": {"route": "fal", "id": "ideogram/v4", "status": "ready"},
    "sora 2 pro": {"route": "fal", "id": "fal-ai/sora-2/text-to-video/pro", "status": "ready"},
    "vidu q3 pro": {"route": "fal", "id": "fal-ai/vidu/q3/text-to-video", "status": "check_model"},
    "pixverse v5.6": {"route": "fal", "id": "fal-ai/pixverse/v5.6/text-to-video", "status": "ready"},
    "skyreels v4": {"route": "wavespeed", "id": "skywork-ai/skyreels-v4/text-to-video", "status": "needs_permission"},
    # Indian speech in (voiceofindia STT names)
    "indic transcribe core": {"route": "direct:bodhan", "id": "indic-transcribe-core", "status": "ready"},
    "indic transcribe flex": {"route": "direct:bodhan", "id": "indic-transcribe-flex", "status": "ready"},
    "saaras v3": {"route": "direct:sarvam", "id": "saaras:v3", "status": "ready"},
    "transcribe": {"route": "eden", "id": "amazon/speech_to_text_async", "status": "check_terms"},
    "fast transcription api": {"route": "eden", "id": "microsoft/speech_to_text_async", "status": "check_terms"},
    "realtime transcription api": {"route": "direct:azure", "id": "azure-speech-realtime", "status": "ready"},
    "maya transcribe one": {"route": "direct:maya", "id": "maya-transcribe-one", "status": "ready"},
    "prisma v2.5": {"route": "direct:gnani", "id": "prisma-v2.5", "status": "ready"},
    "gpt live transcribe": {"route": "direct:openai", "id": "gpt-live-transcribe", "status": "ready"},
    # Indian speech out (voiceofindia TTS names)
    "sonic 3.6": {"route": "direct:cartesia", "id": "sonic-3.6", "status": "ready"},
    "sonic 3.5": {"route": "direct:cartesia", "id": "sonic-3.5", "status": "ready"},
    "sonic 3": {"route": "direct:cartesia", "id": "sonic-3", "status": "ready"},
    "maya 2 native": {"route": "direct:maya", "id": "maya2-native", "status": "ready"},
    "gemini 2.5 pro tts": {"route": "direct:google", "id": "gemini-2.5-pro-tts", "status": "ready"},
    "chirp 3 hd": {"route": "direct:google", "id": "chirp-3-hd", "status": "ready"},
    "falcon": {"route": "direct:murf", "id": "falcon", "status": "ready"},
    "vachana tts v3": {"route": "direct:gnani", "id": "vachana-tts-v3", "status": "ready"},
    "lightning 3.1 pro": {"route": "direct:smallest", "id": "lightning-3.1-pro", "status": "ready"},
    "mira tts": {"route": "direct:miraiminds", "id": "mira-tts", "status": "ready"},
    "chariot tts v0": {"route": "direct:chariot", "id": "chariot-tts-v0", "status": "ready"},
    "bulbul v3": {"route": "direct:sarvam", "id": "bulbul:v3", "status": "ready"},
    "teen v1": {"route": "direct:teenageworks", "id": "teen-v1", "status": "ready"},
    "mai voice 1": {"route": "direct:microsoft", "id": "mai-voice-1", "status": "ready"},
}
# voiceofindia names that ARE on OpenRouter
VOI_OR = {
    "eleven v4": "elevenlabs/eleven-v4", "gemini 3.8 flash tts": "google/gemini-3.8-flash-tts",
    "gemini 3.1 flash tts": "google/gemini-3.1-flash-tts-preview",
    "gemini 3.8 flash lite tts": "google/gemini-3.8-flash-lite-tts", "eleven labs v3": "elevenlabs/eleven-v3",
    "speech 2.8 hd": "minimax/speech-2.8-hd", "mai transcribe 2": "microsoft/mai-transcribe-2",
    "mai transcribe 1.5": "microsoft/mai-transcribe-1.5", "gemini 3.5 transcribe": "google/gemini-3.5-transcribe",
    "scribe v2": "elevenlabs/scribe-v2", "gemini 3.8 flash": "google/gemini-3.8-flash",
    "nemotron 3.5 transcribe": "nvidia/nemotron-3.5-transcribe", "gemini 3 flash": "google/gemini-3-flash-preview",
    "gpt transcribe": "openai/gpt-transcribe", "grok voice transcribe 2.0": "x-ai/grok-stt-2.0",
    "nova 3": "deepgram/nova-3", "qwen3 asr": "qwen/qwen3-asr-1.7b",
}


def norm(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = s.split(":", 1)[1] if ":" in s else s
    s = re.sub(r"[-_/]", " ", s)
    s = re.sub(r"\b(preview|latest|thinking|instruct|it)\b", " ", s)
    s = re.sub(r"\b\d{4,8}\b", " ", s)
    return " ".join(s.split())


def index(catalogue: list[dict]) -> dict[str, dict]:
    """OpenRouter catalogue -> {normalised name or slug: model}. First seen wins (stable order)."""
    idx: dict[str, dict] = {}
    for m in catalogue:
        mid = str(m.get("id") or "")
        if not mid or mid.startswith("openrouter/"):
            continue
        for k in (norm(str(m.get("name") or "")), norm(mid.split("/", 1)[-1])):
            if k:
                idx.setdefault(k, m)
    return idx


def match(name: str, idx: dict[str, dict], by_id: dict[str, dict]) -> dict | None:
    """-> {'id', 'route': 'openrouter', 'model': <catalogue row>} or a ROUTES entry, or None."""
    k = norm(name)
    m = by_id.get(ALIAS[k]) if k in ALIAS else idx.get(k)
    if m:
        return {"id": m["id"], "route": "openrouter", "status": "ready", "model": m}
    r = ROUTES.get(k)
    if r:
        return {**r, "model": None}
    return None
