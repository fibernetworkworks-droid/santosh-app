"""From the owner's hoola-studio package (v0.68 in Hoola).

Models, camera presets and styles.

Prices are ESTIMATES in USD per second of output (October 2026 public figures). Set your real contract prices in
HOOLA_STUDIO_MODELS (a JSON file with the same shape) before charging users.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ASPECTS_SEEDANCE = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]

MODELS: dict[str, dict] = {
    "offline-preview": {
        "provider": "offline", "label": "Free animatic (offline placeholder clips to check timing and story)",
        "durations": [1, 30], "resolutions": ["480p", "720p", "1080p"], "aspects": ASPECTS_SEEDANCE,
        "audio": True, "references": 9, "usd_per_s": 0.0, "price_note": "free",
    },
    "seedance-2-fast": {
        "provider": "fal", "label": "Seedance 2.0 Fast via fal (drafts, social clips)",
        "endpoints": {"t2v": "bytedance/seedance-2.0/fast/text-to-video", "i2v": "bytedance/seedance-2.0/fast/image-to-video",
                      "ref": "bytedance/seedance-2.0/fast/reference-to-video"},
        "durations": [4, 15], "resolutions": ["480p", "720p", "1080p"], "aspects": ASPECTS_SEEDANCE,
        "audio": True, "references": 9, "usd_per_s": 0.09, "price_note": "estimate",
    },
    "seedance-2": {
        "provider": "fal", "label": "Seedance 2.0 via fal (final quality)",
        "endpoints": {"t2v": "bytedance/seedance-2.0/text-to-video", "i2v": "bytedance/seedance-2.0/image-to-video",
                      "ref": "bytedance/seedance-2.0/reference-to-video"},
        "durations": [4, 15], "resolutions": ["480p", "720p", "1080p", "4k"], "aspects": ASPECTS_SEEDANCE,
        "audio": True, "references": 9, "usd_per_s": 0.15, "price_note": "estimate (resellers list ~$0.11-0.18/s at 720p)",
    },
    "seedance-2-byteplus": {
        "provider": "byteplus", "label": "Seedance 2.0 direct from BytePlus ModelArk",
        "model": "dreamina-seedance-2-0-260128",
        "durations": [4, 15], "resolutions": ["480p", "720p", "1080p", "4k"], "aspects": ASPECTS_SEEDANCE,
        "audio": True, "references": 9, "usd_per_s": 0.112, "price_note": "estimate",
    },
    "gemini-omni-flash": {
        "provider": "google", "label": "Google Gemini Omni Flash (successor of Veo 3.1 in the Gemini API)",
        "model": "gemini-omni-1.1-flash",
        "durations": [4, 10], "resolutions": ["360p", "720p", "1080p", "4k"], "aspects": ["16:9", "9:16"],
        "audio": True, "references": 3, "usd_per_s": 0.40, "price_note": "estimate (Google had not published Omni prices)",
        "fixed_duration": True,
    },
}

_OR_NOTE = "conservative estimate for budget checks; the real cost reported by OpenRouter is what gets recorded"
_OR = {"provider": "openrouter", "resolutions": ["480p", "720p", "1080p"], "audio": True, "references": 4,
       "price_note": _OR_NOTE}
MODELS.update({
    "or-seedance-2-fast": {**_OR, "label": "Seedance 2.0 Fast via OpenRouter (drafts, social clips)",
                           "model": "bytedance/seedance-2.0-fast", "durations": [4, 15], "aspects": ASPECTS_SEEDANCE, "usd_per_s": 0.10},
    "or-seedance-2": {**_OR, "label": "Seedance 2.0 via OpenRouter (final quality)",
                      "model": "bytedance/seedance-2.0", "durations": [4, 15], "aspects": ASPECTS_SEEDANCE, "usd_per_s": 0.15},
    "or-seedance-2.5": {**_OR, "label": "Seedance 2.5 via OpenRouter (newest Seedance)",
                        "model": "bytedance/seedance-2.5", "durations": [4, 15], "aspects": ASPECTS_SEEDANCE, "usd_per_s": 0.20},
    "or-veo-3.1-fast": {**_OR, "label": "Google Veo 3.1 Fast via OpenRouter",
                        "model": "google/veo-3.1-fast", "durations": [4, 8], "aspects": ["16:9", "9:16"], "usd_per_s": 0.12,
                        "allowed_durations": [4, 6, 8]},
    "or-veo-3.1-lite": {**_OR, "label": "Google Veo 3.1 Lite via OpenRouter (cheapest Google)",
                        "model": "google/veo-3.1-lite", "durations": [4, 8], "aspects": ["16:9", "9:16"], "usd_per_s": 0.08,
                        "allowed_durations": [4, 6, 8]},
    "or-kling-3-std": {**_OR, "label": "Kling 3.0 Standard via OpenRouter",
                       "model": "kwaivgi/kling-v3.0-std", "durations": [5, 10], "aspects": ["16:9", "9:16", "1:1"], "usd_per_s": 0.15,
                       "allowed_durations": [5, 10]},
    "or-wan-3": {**_OR, "label": "Wan 3.0 via OpenRouter (low cost)",
                 "model": "alibaba/wan-3.0", "durations": [5, 10], "aspects": ["16:9", "9:16", "1:1"], "usd_per_s": 0.08},
})

# draft/final use OpenRouter when OPENROUTER_API_KEY is set, otherwise fal
QUALITY_BY_PROVIDER = {"openrouter": {"draft": "or-seedance-2-fast", "final": "or-seedance-2"},
                       "fal": {"draft": "seedance-2-fast", "final": "seedance-2"},
                       "byteplus": {"draft": "seedance-2-byteplus", "final": "seedance-2-byteplus"}}

IMAGE_MODELS: dict[str, dict] = {
    "offline-image": {"provider": "offline", "usd_per_image": 0.0},
    "flux-dev": {"provider": "fal", "endpoint": "fal-ai/flux/dev", "usd_per_image": 0.025, "price_note": "estimate"},
}

QUALITY = {
    "preview": {"model": "offline-preview", "resolution": "480p"},
    "draft": {"model": "seedance-2-fast", "resolution": "480p"},
    "final": {"model": "seedance-2", "resolution": "1080p"},
}

CAMERA = {
    "static": "locked-off static camera",
    "dolly_in": "slow dolly-in towards the subject",
    "dolly_out": "slow dolly-out revealing the surroundings",
    "pan_left": "smooth pan to the left",
    "pan_right": "smooth pan to the right",
    "tilt_up": "camera tilts up",
    "tilt_down": "camera tilts down",
    "orbit": "camera orbits around the subject",
    "crane_up": "crane shot rising up",
    "tracking": "tracking shot following the subject",
    "handheld": "handheld camera with natural shake",
    "drone": "aerial drone shot",
    "zoom_in": "slow zoom in",
    "whip_pan": "fast whip pan",
    "close_up": "close-up shot",
    "wide": "wide establishing shot",
    "low_angle": "low-angle hero shot",
    "pov": "first-person point of view",
    "slow_motion": "slow motion",
}

STYLES = {
    "cinematic": "cinematic, film look, natural lighting, shallow depth of field, rich colour grade",
    "ad": "premium product commercial, clean studio lighting, crisp detail, glossy",
    "reel": "vibrant social media reel, energetic, bright, high contrast",
    "documentary": "documentary style, natural light, realistic, observational",
    "animation_3d": "stylized 3D animation, soft lighting, Pixar-like characters",
    "anime": "anime style, cel shading, expressive",
    "indian_wedding": "Indian wedding film, warm golden tones, marigold decor, festive",
    "news": "TV news style, steady framing, neutral lighting",
}


def load_models() -> dict[str, dict]:
    m = json.loads(json.dumps(MODELS))
    f = os.environ.get("HOOLA_STUDIO_MODELS")
    if f and Path(f).is_file():
        for k, v in json.loads(Path(f).read_text()).items():
            m[k] = {**m.get(k, {}), **v}
    return m
