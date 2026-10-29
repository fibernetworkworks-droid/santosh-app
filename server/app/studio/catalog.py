"""From the owner's hoola-studio package (v0.68 in Hoola).

Models, camera presets and styles.

Prices are ESTIMATES in USD per second of output (October 2026 public figures). Set your real contract prices in
HOOLA_STUDIO_MODELS (a JSON file with the same shape) before charging users.
"""
from __future__ import annotations

import json
import re
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
_AS5 = ["16:9", "9:16", "1:1", "4:3", "3:4"]
MODELS.update({
    # ---- v0.157 research (24 Oct 2026, Artificial Analysis + Arena + OpenRouter): best model per job; prices = 1080p estimates
    "or-wan-3": {**_OR, "label": "Wan 3.0 (Alibaba): #1 text-to-video, up to 30 s, multi-shot, sound",
                 "model": "alibaba/wan-3.0", "durations": [2, 30], "aspects": _AS5, "usd_per_s": 0.10},
    "or-seedance-2.5": {**_OR, "label": "Seedance 2.5 (ByteDance): premium, many references, same face everywhere, 30 s",
                        "model": "bytedance/seedance-2.5", "durations": [4, 30], "aspects": ASPECTS_SEEDANCE, "usd_per_s": 0.57,
                        "references": 9},
    "or-minimax-h3": {**_OR, "label": "MiniMax H3 (Hailuo 3): #1 photo-to-video, 2K, product shots",
                      "model": "minimax/hailuo-3", "durations": [6, 10], "aspects": _AS5, "usd_per_s": 0.13,
                      "resolutions": ["720p", "1080p"]},
    "or-minimax-h3-max": {**_OR, "label": "MiniMax H3 Max: first / last frame keyframes, low cost",
                          "model": "minimax/hailuo-3-max", "durations": [6, 10], "aspects": _AS5, "usd_per_s": 0.08,
                          "resolutions": ["720p", "1080p"]},
    "or-flux-3-video": {**_OR, "label": "FLUX 3 Video (Black Forest Labs): premium look, 20 s, timed keyframes",
                        "model": "black-forest-labs/flux-3-video", "durations": [5, 20], "aspects": _AS5, "usd_per_s": 0.29,
                        "resolutions": ["720p", "1080p"]},
    "or-seedance-2-fast": {**_OR, "label": "Seedance 2.0 Fast via OpenRouter (drafts)",
                           "model": "bytedance/seedance-2.0-fast", "durations": [4, 15], "aspects": ASPECTS_SEEDANCE, "usd_per_s": 0.045},
    "or-seedance-2": {**_OR, "label": "Seedance 2.0 via OpenRouter",
                      "model": "bytedance/seedance-2.0", "durations": [4, 15], "aspects": ASPECTS_SEEDANCE, "usd_per_s": 0.15},
    "or-veo-3.1-fast": {**_OR, "label": "Google Veo 3.1 Fast via OpenRouter",
                        "model": "google/veo-3.1-fast", "durations": [4, 8], "aspects": ["16:9", "9:16"], "usd_per_s": 0.12,
                        "allowed_durations": [4, 6, 8]},
    "or-veo-3.1-lite": {**_OR, "label": "Google Veo 3.1 Lite via OpenRouter (cheapest Google)",
                        "model": "google/veo-3.1-lite", "durations": [4, 8], "aspects": ["16:9", "9:16"], "usd_per_s": 0.08,
                        "allowed_durations": [4, 6, 8]},
    "or-kling-3-std": {**_OR, "label": "Kling 3.0 Standard via OpenRouter",
                       "model": "kwaivgi/kling-v3.0-std", "durations": [5, 10], "aspects": ["16:9", "9:16", "1:1"], "usd_per_s": 0.15,
                       "allowed_durations": [5, 10]},
    # Hindi (any language) talking: our own voice line + Sync 3 lip sync (95+ languages): photo -> talking video, or
    # a generated scene -> its lips re-synced to the line. Charged per second of output.
    "sync-3": {"provider": "sync", "label": "Sync 3 lip sync (95+ languages incl. Hindi)", "model": "sync-3",
               "durations": [1, 60], "resolutions": ["720p", "1080p", "4k"], "aspects": ASPECTS_SEEDANCE, "audio": True,
               "references": 0, "usd_per_s": 0.13, "price_note": "list $0.107-0.133/s"},
})
MODELS["gemini-omni-flash"].update({"model": "gemini-omni-1.1-flash", "durations": [3, 10], "usd_per_s": 0.15,
                                    "label": "Google Gemini Omni 1.1 Flash: #1 in human votes, first / last frame, scene links",
                                    "price_note": "estimate (~$0.10/s at 720p, ~$0.15/s at 1080p)"})

# What each kind of shot needs, per quality, best first (the first model whose provider has a key is used).
# scene = people / places / story; product = her product photo comes alive; talk = a person speaks to camera
# (painted portrait + her line, lip-synced); dialogue = people talking inside a scene (scene model, then lip sync);
# link = moves from one picture to the next (first + last frame).
ROUTES: dict[str, dict[str, list[str]]] = {
    "scene": {"draft": ["or-seedance-2-fast", "or-wan-3", "seedance-2-fast", "seedance-2-byteplus", "gemini-omni-flash"],
              "final": ["or-wan-3", "gemini-omni-flash", "or-seedance-2", "seedance-2", "seedance-2-byteplus"],
              "premium": ["or-seedance-2.5", "or-flux-3-video", "gemini-omni-flash", "or-wan-3", "seedance-2"]},
    "product": {"draft": ["or-minimax-h3-max", "or-seedance-2-fast", "seedance-2-fast"],
                "final": ["or-minimax-h3", "or-wan-3", "gemini-omni-flash", "seedance-2"],
                "premium": ["or-seedance-2.5", "or-minimax-h3", "or-flux-3-video", "seedance-2"]},
    "link": {"draft": ["or-minimax-h3-max", "or-seedance-2-fast", "seedance-2-fast"],
             "final": ["gemini-omni-flash", "or-minimax-h3-max", "or-wan-3", "or-seedance-2", "seedance-2"],
             "premium": ["or-seedance-2.5", "gemini-omni-flash", "or-flux-3-video", "seedance-2"]},
    "talk": {"draft": ["sync-3"], "final": ["sync-3"], "premium": ["sync-3"]},
}
ROUTES["dialogue"] = ROUTES["scene"]
KINDS = list(ROUTES)
LIPSYNC_KINDS = ("talk", "dialogue")
# languages the video models themselves lip-sync well (others: our voice line + Sync 3)
NATIVE_SPEECH = ("english", "en", "mandarin", "chinese", "japanese", "korean", "spanish", "french", "german")

IMAGE_MODELS: dict[str, dict] = {
    "offline-image": {"provider": "offline", "usd_per_image": 0.0},
    "nano-banana-pro": {"provider": "gemini", "usd_per_image": 0.14, "price_note": "Nano Banana Pro 2K (+ thinking)"},
    "flux-dev": {"provider": "fal", "endpoint": "fal-ai/flux/dev", "usd_per_image": 0.025, "price_note": "estimate"},
}

QUALITY = {
    "preview": {"model": "offline-preview", "resolution": "480p"},
    "draft": {"model": "seedance-2-fast", "resolution": "720p"},
    "final": {"model": "seedance-2", "resolution": "1080p"},          # = HD
    "premium": {"model": "seedance-2", "resolution": "1080p"},
}
RANK = ["preview", "draft", "final", "premium"]
QUALITY_LABEL = {"preview": "Free preview", "draft": "Draft (720p)", "final": "HD (1080p)", "premium": "Premium (1080p)"}

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


# ================================================================ v0.262 EVERY MODEL, PRICE FIRST (owner: "IT MUST INCLUDE ALL
# MODEL IN IT LETS USER CHOOSE THE RIGHT ONE FOR THEM ... USER WILL SEE THE PRICING OF EVERY VIDEO BEFORE GENERATION")
PRICES_CHECKED = "2026-10-29"
RES_ORDER = ["360p", "480p", "540p", "720p", "768p", "1080p", "2k", "4k"]

# USD per second of output WITH sound, per resolution, from the public price pages (Oct 2026). The live OpenRouter
# list (Studio.models_sync -> parse_skus) replaces these for OpenRouter models whenever it is reachable.
_BY_RES = {
    "gemini-omni-flash": {"360p": 0.034, "720p": 0.10, "1080p": 0.152, "4k": 0.304},
    "or-veo-3.1-fast": {"720p": 0.10, "1080p": 0.12, "4k": 0.30},
    "or-veo-3.1-lite": {"720p": 0.05, "1080p": 0.08},
    "or-seedance-2.5": {"480p": 0.103, "720p": 0.231, "1080p": 0.569},
    "or-minimax-h3": {"720p": 0.08, "1080p": 0.13},
    "or-minimax-h3-max": {"720p": 0.08, "1080p": 0.08},
    "or-wan-3": {"480p": 0.06, "720p": 0.08, "1080p": 0.10},
    "or-seedance-2": {"480p": 0.07, "720p": 0.11, "1080p": 0.15},
    "or-seedance-2-fast": {"480p": 0.03, "720p": 0.045, "1080p": 0.07},
    "seedance-2-byteplus": {"480p": 0.05, "720p": 0.112, "1080p": 0.25},
    "or-kling-3-std": {"720p": 0.11, "1080p": 0.15},
}
for _k, _t in _BY_RES.items():
    if _k in MODELS:
        MODELS[_k]["usd_by_res"] = dict(_t)

# Kling 3.0 Pro is listed on OpenRouter's video API as kwaivgi/kling-v3.0-pro (estimate until the live list prices it)
MODELS["or-kling-3-pro"] = {**_OR, "label": "Kling 3.0 Pro via OpenRouter: cinematic motion, multi-shot, sound",
                            "model": "kwaivgi/kling-v3.0-pro", "durations": [5, 10], "aspects": ["16:9", "9:16", "1:1"],
                            "usd_per_s": 0.22, "allowed_durations": [5, 10], "usd_by_res": {"720p": 0.16, "1080p": 0.22}}

# What her picker card says about each model Hoola can call. tier: top | strong | budget | talk | free
CARDS: dict[str, dict] = {
    "gemini-omni-flash": {"name": "Gemini Omni 1.1 Flash", "maker": "Google", "tier": "top",
                          "best": "Top of the human-vote boards; first / last frame, scene links", "rank": "#1 Arena (human votes)"},
    "or-wan-3": {"name": "Wan 3.0", "maker": "Alibaba", "tier": "top", "best": "Long shots up to 30 s, multi-shot story, great value",
                 "rank": "#1 Artificial Analysis text-to-video"},
    "or-seedance-2.5": {"name": "Seedance 2.5", "maker": "ByteDance", "tier": "top",
                        "best": "Premium look, many references, the same face everywhere, 30 s", "rank": "Top 3 Artificial Analysis"},
    "or-minimax-h3": {"name": "MiniMax H3", "maker": "MiniMax", "tier": "top", "best": "Photo to video, product shots, stereo sound",
                      "rank": "Top 3 Artificial Analysis"},
    "or-minimax-h3-max": {"name": "MiniMax H3 Max", "maker": "MiniMax", "tier": "strong", "best": "First / last frame moves at a low price"},
    "or-veo-3.1-fast": {"name": "Veo 3.1 Fast", "maker": "Google", "tier": "top", "best": "Most film-like look, 4K, clip extension"},
    "or-veo-3.1-lite": {"name": "Veo 3.1 Lite", "maker": "Google", "tier": "budget", "best": "Cheapest Google video, quick social clips"},
    "or-kling-3-pro": {"name": "Kling 3.0 Pro", "maker": "Kuaishou", "tier": "top", "best": "Cinematic motion, people and action",
                       "rank": "#1 LLM Stats blind votes (Kling v3)"},
    "or-kling-3-std": {"name": "Kling 3.0 Standard", "maker": "Kuaishou", "tier": "strong", "best": "Kling motion at a lower price"},
    "or-flux-3-video": {"name": "FLUX 3 Video", "maker": "Black Forest Labs", "tier": "strong", "best": "Premium stills-quality look, timed keyframes"},
    "or-seedance-2": {"name": "Seedance 2.0", "maker": "ByteDance", "tier": "strong", "best": "Reliable all-rounder, 9 references"},
    "seedance-2": {"name": "Seedance 2.0 (fal)", "maker": "ByteDance", "tier": "strong", "best": "Seedance 2.0 through a fal account, up to 4K"},
    "seedance-2-byteplus": {"name": "Seedance 2.0 (BytePlus)", "maker": "ByteDance", "tier": "strong", "best": "Seedance 2.0 direct from ByteDance's cloud"},
    "or-seedance-2-fast": {"name": "Seedance 2.0 Fast", "maker": "ByteDance", "tier": "budget", "best": "Cheap fast drafts and social clips"},
    "seedance-2-fast": {"name": "Seedance 2.0 Fast (fal)", "maker": "ByteDance", "tier": "budget", "best": "Cheap drafts through a fal account"},
    "sync-3": {"name": "Sync 3 lip sync", "maker": "Sync", "tier": "talk",
               "best": "Lips matched to Hindi and 95+ languages; used by itself for spoken lines"},
    "offline-preview": {"name": "Free animatic", "maker": "Hoola", "tier": "free", "best": "Check story and timing before paying"},
}

# The rest of the market (October 2026). Shown in the picker so she sees everything; they switch on by themselves the
# day OpenRouter's live list carries a model whose id matches `match`. `needs` = what it takes otherwise.
WATCH: list[dict] = [
    {"name": "Kling 4.0", "maker": "Kuaishou", "tier": "top", "match": r"kling.*(v4|4\.0|-4)", "usd_s": 0.235,
     "best": "30 s clips, 15 references, 4K, stereo sound (launched 15 Oct 2026)", "needs": "Kling's own API (not open yet) or a provider that carries it"},
    {"name": "Vidu Q4", "maker": "Shengshu", "tier": "top", "match": r"vidu.*q4", "usd_s": 0.39,
     "best": "Acting performances, 15 image + 3 voice references, 4K", "needs": "a Vidu API account"},
    {"name": "Runway Gen-4.5", "maker": "Runway", "tier": "top", "match": r"(runway.*)?gen-?4\.5", "usd_s": 0.12,
     "best": "Strong generation plus Aleph 2 video editing", "needs": "a Runway API account"},
    {"name": "HappyHorse 1.0", "maker": "Alibaba", "tier": "top", "match": r"happy-?horse-1\.0", "usd_s": 0.17,
     "best": "Top video-to-video (restyle a clip)", "needs": "an Alibaba Cloud / fal account"},
    {"name": "Wan 3.0 Prime", "maker": "Alibaba", "tier": "top", "match": r"wan-3\.0-prime", "usd_s": 0.28,
     "best": "Wan 3.0's highest-quality tier, 30 s", "needs": "OpenRouter"},
    {"name": "HappyHorse 1.1", "maker": "Alibaba", "tier": "top", "match": r"happy-?horse-1\.1", "usd_s": 0.13,
     "best": "Realistic people and motion, strong in blind votes", "needs": "OpenRouter"},
    {"name": "Veo 3.1", "maker": "Google", "tier": "top", "match": r"veo-3\.1$", "usd_s": 0.40,
     "best": "Google's full Veo 3.1: most film-like, 4K", "needs": "OpenRouter"},
    {"name": "Kling Video O1", "maker": "Kuaishou", "tier": "strong", "match": r"kling-video-o1", "usd_s": 0.112,
     "best": "Kling with element references and multi-character scenes", "needs": "OpenRouter"},
    {"name": "Grok Imagine Video 1.5 Lite", "maker": "xAI", "tier": "budget", "match": r"grok-imagine-video-1\.5-lite", "usd_s": 0.03,
     "best": "Very cheap drafts with sound", "needs": "OpenRouter"},
    {"name": "Grok Imagine Video", "maker": "xAI", "tier": "budget", "match": r"grok-imagine-video$", "usd_s": 0.07,
     "best": "Older Grok video, cheap", "needs": "OpenRouter"},
    {"name": "Seedance 2.0 Mini", "maker": "ByteDance", "tier": "budget", "match": r"seedance-2\.0-mini", "usd_s": 0.076,
     "best": "Smallest Seedance 2: cheap clips with sound", "needs": "OpenRouter"},
    {"name": "Seedance 1.5 Pro", "maker": "ByteDance", "tier": "budget", "match": r"seedance-1-?5", "usd_s": 0.05,
     "best": "Cheapest good-quality clips", "needs": "OpenRouter"},
    {"name": "Wan 2.7", "maker": "Alibaba", "tier": "budget", "match": r"wan-2\.7", "usd_s": 0.10, "best": "Older Wan, steady value",
     "needs": "OpenRouter"},
    {"name": "Wan 2.6", "maker": "Alibaba", "tier": "budget", "match": r"wan-2\.6", "usd_s": 0.08, "best": "Older Wan, low price",
     "needs": "OpenRouter"},
    {"name": "Luma Ray3.2", "maker": "Luma", "tier": "strong", "match": r"ray-?3", "usd_s": 0.20,
     "best": "20 s at 1080p, 16 keyframes, HDR", "needs": "a Luma API account"},
    {"name": "Grok Imagine Video 1.5", "maker": "xAI", "tier": "strong", "match": r"grok-imagine-video-1\.5$", "usd_s": 0.25,
     "best": "15 s with sound, 1080p", "needs": "an xAI API account"},
    {"name": "PixVerse V6", "maker": "PixVerse", "tier": "strong", "match": r"pixverse.*v6", "usd_s": 0.08,
     "best": "1080p social clips with sound", "needs": "a PixVerse or fal account"},
    {"name": "Hailuo 2.3", "maker": "MiniMax", "tier": "budget", "match": r"hailuo-?2\.3", "usd_s": 0.082,
     "best": "Older, cheap", "needs": "a fal account"},
    {"name": "Pika 2.5", "maker": "Pika", "tier": "budget", "match": r"pika", "usd_s": 0.05,
     "best": "Playful social effects", "needs": "a Pika or fal account"},
    {"name": "LTX-2.5", "maker": "Lightricks", "tier": "budget", "match": r"ltx", "usd_s": 0.02,
     "best": "Open weights: runs on Hoola's own GPU later, sound, up to 4K", "needs": "a GPU server (open model)"},
    {"name": "Wan 2.2", "maker": "Alibaba", "tier": "budget", "match": r"wan-?2\.2", "usd_s": 0.02,
     "best": "Open weights (Apache 2.0): cheapest drafts on a GPU", "needs": "a GPU server (open model)"},
    {"name": "HunyuanVideo 1.5", "maker": "Tencent", "tier": "budget", "match": r"hunyuan", "usd_s": 0.03,
     "best": "Open weights, cinematic motion (licence excludes EU / UK / Korea)", "needs": "a GPU server (open model)"},
    {"name": "OmniHuman 1.5", "maker": "ByteDance", "tier": "talk", "match": r"omnihuman", "usd_s": 0.14,
     "best": "A photo speaks from a real voice track, up to 30 s", "needs": "a BytePlus / fal account"},
    {"name": "Moonvalley Marey", "maker": "Moonvalley", "tier": "strong", "match": r"marey", "usd_s": 0.30,
     "best": "Trained only on licensed footage (brand-safe)", "needs": "a Moonvalley account"},
]
# Not offered, and why (shown once at the bottom of the picker)
NOT_OFFERED = [("Sora 2 (OpenAI)", "shut down (app April 2026, API September 2026)"),
               ("Utopai X", "only inside Utopai's own studio, no API"),
               ("Meta Movie Gen", "research model, no developer access"),
               ("Midjourney video", "no current video model")]


def norm_res(r: str) -> str:
    r = str(r or "").lower().strip()
    return {"2160p": "4k", "1440p": "2k", "uhd": "4k", "fhd": "1080p", "hd": "720p"}.get(r, r)


def rate(m: dict, resolution: str = "", audio: bool = True) -> float:
    """USD per second for this model at this resolution (with or without sound). Unknown resolution -> the nearest one
    at or above it, else the best it makes; no table -> the model's flat estimate."""
    table = (m.get("usd_by_res_noaudio") if not audio else None) or m.get("usd_by_res") or {}
    if table:
        r = norm_res(resolution)
        if r in table:
            return float(table[r])
        idx = RES_ORDER.index(r) if r in RES_ORDER else RES_ORDER.index("1080p")
        known = sorted((RES_ORDER.index(k), v) for k, v in table.items() if k in RES_ORDER)
        if known:
            above = [v for i, v in known if i >= idx]
            return float(above[0] if above else known[-1][1])
    return float(m.get("usd_per_s") or 0.0)


# Seedance-style token billing: tokens per second of video = width x height x 24 fps / 1024
TOKENS_PER_S = {"480p": 9_607, "540p": 12_150, "720p": 21_600, "768p": 24_576, "1080p": 48_600, "2k": 86_400, "4k": 194_400}


def parse_skus(skus: dict | None, resolutions: list[str] | None = None) -> tuple[dict, dict, float]:
    """OpenRouter's pricing_skus -> ({res: usd/s with sound}, {res: usd/s silent}, minimum usd per generation).
    Real keys (29 Oct 2026 live list): duration_seconds[_with_audio|_without_audio][_<res>] (USD / s),
    cents_per_second_output[_<res>] and cents_per_video_output_second_<res> (cents / s), text_to_video_duration_seconds_<res>,
    video_tokens[_without_audio] (USD per token, Seedance), minimum_cents_per_generation. Image / video INPUT, continuation and
    image-to-video-only keys are not the price of a new clip and are skipped."""
    w: dict[str, float] = {}
    wo: dict[str, float] = {}
    bw = bwo = plain = None
    tok: dict[str, float] = {}
    unmarked: dict[str, float] = {}                  # per-resolution keys that do not say with / without sound
    minimum = 0.0
    for k, v in (skus or {}).items():
        try:
            val = float(v)
        except (TypeError, ValueError):
            continue
        key = str(k).lower()
        if key.startswith("minimum"):
            minimum = val / 100 if "cents" in key else val
            continue
        if any(x in key for x in ("continuation", "image_input", "reference_image", "image_to_video", "video_input", "input")):
            continue
        no_audio = bool(re.search(r"without[-_]?audio|no[-_]?audio|silent", key))
        if "token" in key:
            tok["wo" if no_audio else "w"] = val
            continue
        if "second" not in key:
            continue
        if "cents" in key:
            val /= 100
        mres = re.search(r"(360p|480p|540p|720p|768p|1080p|1440p|2160p|2k|4k)", key)
        if mres:
            r = norm_res(mres.group(1))
            if no_audio:
                wo[r] = val
            elif "with_audio" in key or "with-audio" in key:
                w[r] = val
            else:
                unmarked[r] = val
        elif no_audio:
            bwo = val
        elif "with_audio" in key or "with-audio" in key:
            bw = val
        else:
            plain = val
    explicit = bw is not None                        # a separate "_with_audio" price exists
    for r, val in unmarked.items():                  # next to an explicit sound price, an unmarked one is the silent rate
        (wo if explicit else w).setdefault(r, val)
    if bw is None:
        bw = plain
    elif plain is not None and bwo is None:
        bwo = plain                                  # "duration_seconds" next to an explicit "_with_audio" = silent rate
    ress = [norm_res(x) for x in (resolutions or [])] or list(w) or ["1080p"]
    if tok:
        for res in ress:
            n = TOKENS_PER_S.get(res)
            if n and "w" in tok:
                w.setdefault(res, round(tok["w"] * n, 5))
            if n and "wo" in tok:
                wo.setdefault(res, round(tok["wo"] * n, 5))
    for res in ress:
        if bw is not None:
            w.setdefault(res, bw)
        if bwo is not None:
            wo.setdefault(res, bwo)
    return w, wo, minimum

# "Best quality first" in her picker: the October 2026 leaderboards (Artificial Analysis, Arena, LLM Stats) merged
QUALITY_ORDER = ["Gemini Omni 1.1 Flash", "Wan 3.0 Prime", "Wan 3.0", "Kling 4.0", "Seedance 2.5", "MiniMax H3", "HappyHorse 1.1",
                 "HappyHorse 1.0", "Veo 3.1", "Kling 3.0 Pro", "Vidu Q4", "Veo 3.1 Fast", "Runway Gen-4.5", "FLUX 3 Video",
                 "Grok Imagine Video 1.5", "Luma Ray3.2", "Kling Video O1", "Seedance 2.0", "Kling 3.0 Standard", "MiniMax H3 Max",
                 "Moonvalley Marey", "PixVerse V6", "Veo 3.1 Lite", "Seedance 2.0 Fast", "Seedance 2.0 Mini", "Hailuo 2.3",
                 "Seedance 1.5 Pro", "Wan 2.7", "Wan 2.6", "Grok Imagine Video", "Grok Imagine Video 1.5 Lite", "Pika 2.5",
                 "HunyuanVideo 1.5", "LTX-2.5", "Wan 2.2"]


def quality_rank(name: str) -> int:
    base = re.sub(r"\s*\((fal|BytePlus)\)$", "", name or "")
    return QUALITY_ORDER.index(base) if base in QUALITY_ORDER else 99
