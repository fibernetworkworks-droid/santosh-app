"""HOOLA CINEMA - what each tool accepts and how its request is shaped (data, no network).

Every field name, enum and limit below was read from the engine's own published specs (docs.kie.ai, the OpenAPI block
on each model page) on 2026-11-11 - never from memory, never from another project's code. A wrong field name is
accepted silently by the engine and the reference is ignored, so `build()` is the ONLY place a request is shaped and
the test suite pins every shape. NOT VERIFIED: no live call has been made with these shapes.

  tool      what she gets                                     models
  motion    her character performs the moves of a video       kling-3.0 / kling-2.6 motion-control, wan animate-move
  swap      the person in a video becomes her character       wan animate-replace
  edit      change an item / outfit / place in a video        happyhorse video-edit, wan 2.7 videoedit
  restyle   the whole video redrawn in one look               (the edit models, with a look preset as the instruction)
  talk      a photo speaks her audio or her typed words       kling ai-avatar std / pro, infinitalk, omnihuman, wan s2v
  lipsync   a video's lips follow new audio                   volcengine video-to-video-lip-sync
  animate   one picture becomes a moving shot                 wan 2.5 image-to-video, seedance 2 fast (first frame)
  factory   one brief -> a batch of different clips           seedance 2 fast, kling v3 turbo, wan 2.5 text-to-video
"""
from __future__ import annotations

from typing import Any

SPEC_DATE = "2026-11-11"
MB = 1024 * 1024

TOOLS: list[dict[str, Any]] = [
    {"id": "still", "label": "Cinema still", "group": "image", "engine": "hoola",
     "blurb": "A film-style picture: choose the camera, lens, focal length and aperture."},
    {"id": "motion", "label": "Motion transfer", "group": "video", "engine": "kie",
     "blurb": "Your character performs the moves from a source video.",
     "needs": "One photo of the character (head, shoulders and torso clear) and one source video."},
    {"id": "swap", "label": "Character swap", "group": "video", "engine": "kie",
     "blurb": "The person in a video becomes your character; the scene stays.",
     "needs": "One clear photo of the character and one source video."},
    {"id": "edit", "label": "Item swap / edit", "group": "video", "engine": "kie",
     "blurb": "Change a product, outfit or place in a video and keep the rest of the shot.",
     "needs": "A source video and one line saying what to change. Photos of the new item help."},
    {"id": "restyle", "label": "Restyle", "group": "video", "engine": "kie",
     "blurb": "Redraw a whole video in one look: anime, clay, pixel art, film noir…",
     "needs": "A source video and a look."},
    {"id": "talk", "label": "Talking photo", "group": "video", "engine": "kie",
     "blurb": "A photo speaks your audio, or the words you type in a Hoola voice.",
     "needs": "One portrait photo, and either an audio file or the words to speak."},
    {"id": "lipsync", "label": "Lip sync a video", "group": "video", "engine": "kie",
     "blurb": "The lips in a video follow new audio.",
     "needs": "A video of one person facing the camera and the new audio."},
    {"id": "animate", "label": "Picture to video", "group": "video", "engine": "kie",
     "blurb": "One picture becomes a moving shot, with a camera move you choose.",
     "needs": "One picture and one line about the motion."},
    {"id": "factory", "label": "Content factory", "group": "video", "engine": "kie",
     "blurb": "One brief in, up to six different short clips out.",
     "needs": "A topic. Hoola writes one scene per clip; you can edit each before it is made."},
]
TOOL_IDS = tuple(t["id"] for t in TOOLS)
FACE_TOOLS = ("motion", "swap", "talk", "lipsync")     # a person's face / body is driven: consent is asked
VIDEO_TOOLS = ("motion", "swap", "edit", "restyle", "lipsync")   # a source video goes in: her rights are asked

_AUDIO = {"key": "audio_setting", "label": "Sound", "options": [["auto", "Remake to match"], ["origin", "Keep the original"]],
          "default": "auto"}
_ORIENT = {"key": "character_orientation", "label": "Body direction follows",
           "options": [["video", "The source video (up to 30 s)"], ["image", "The photo (up to 10 s)"]], "default": "video"}

# image / video / audio: {param, single (a plain string, not a list), min, max, mb}; video also seconds (min, max)
MODELS: dict[str, dict[str, Any]] = {
    "kling-3.0/motion-control": {
        "label": "Kling 3.0 Motion Control", "tools": ["motion"], "note": "Best motion match. 720p or 1080p.",
        "image": {"param": "input_urls", "min": 1, "max": 1, "mb": 10},
        "video": {"param": "video_urls", "mb": 100, "seconds": (3, 30)},
        "prompt": {"max": 2500, "default": "Match the movement of the reference video."},
        "res": {"param": "mode", "options": ["720p", "1080p"], "default": "720p"}, "extras": [_ORIENT]},
    "kling-2.6/motion-control": {
        "label": "Kling 2.6 Motion Control", "tools": ["motion"], "note": "The cheaper Kling motion model.",
        "image": {"param": "input_urls", "min": 1, "max": 1, "mb": 10},
        "video": {"param": "video_urls", "mb": 100, "seconds": (3, 30)},
        "prompt": {"max": 2500, "default": "Match the movement of the reference video."},
        "res": {"param": "mode", "options": ["720p", "1080p"], "default": "720p"}, "extras": [_ORIENT]},
    "wan/2-2-animate-move": {
        "label": "Wan Animate Move", "tools": ["motion"], "note": "Open model. 720p, no prompt.",
        "image": {"param": "image_url", "single": True, "min": 1, "max": 1, "mb": 5},
        "video": {"param": "video_url", "single": True, "mb": 100, "seconds": (1, 30)},
        "res": {"param": "resolution", "options": ["720p"], "default": "720p"}, "safe": True},
    "wan/2-2-animate-replace": {
        "label": "Wan Animate Replace", "tools": ["swap"], "note": "Source video up to 10 MB. No prompt.",
        "image": {"param": "image_url", "single": True, "min": 1, "max": 1, "mb": 10},
        "video": {"param": "video_url", "single": True, "mb": 10, "seconds": (1, 30)},
        "res": {"param": "resolution", "options": ["480p", "580p", "720p"], "default": "480p"}, "safe": True},
    "happyhorse/video-edit": {
        "label": "HappyHorse Video Edit", "tools": ["edit", "restyle"], "note": "3-60 s video, up to 5 reference photos.",
        "image": {"param": "reference_image", "min": 0, "max": 5, "mb": 10},
        "video": {"param": "video_url", "single": True, "mb": 100, "seconds": (3, 60)},
        "prompt": {"max": 5000, "required": True},
        "res": {"param": "resolution", "options": ["720p", "1080p"], "default": "1080p"}, "extras": [_AUDIO]},
    "wan/2-7-videoedit": {
        "label": "Wan 2.7 Video Edit", "tools": ["edit", "restyle"], "note": "2-10 s video, one reference photo.",
        "image": {"param": "reference_image", "single": True, "min": 0, "max": 1, "mb": 10},
        "video": {"param": "video_url", "single": True, "mb": 100, "seconds": (2, 10)},
        "prompt": {"max": 5000}, "avoid": {"param": "negative_prompt", "max": 500},
        "res": {"param": "resolution", "options": ["720p", "1080p"], "default": "1080p"}, "extras": [_AUDIO], "safe": True},
    "kling/ai-avatar-standard": {
        "label": "Kling AI Avatar", "tools": ["talk"], "note": "Steady lip sync. Audio up to 5 minutes.",
        "image": {"param": "image_url", "single": True, "min": 1, "max": 1, "mb": 10},
        "audio": {"param": "audio_url", "mb": 100, "seconds": (1, 300)},
        "prompt": {"max": 5000, "required": True, "default": "The person speaks naturally to the camera with calm, friendly expressions."}},
    "kling/ai-avatar-pro": {
        "label": "Kling AI Avatar Pro", "tools": ["talk"], "note": "More facial detail. Audio up to 5 minutes.",
        "image": {"param": "image_url", "single": True, "min": 1, "max": 1, "mb": 10},
        "audio": {"param": "audio_url", "mb": 100, "seconds": (1, 300)},
        "prompt": {"max": 5000, "required": True, "default": "The person speaks naturally to the camera with calm, friendly expressions."}},
    "infinitalk/from-audio": {
        "label": "InfiniteTalk", "tools": ["talk"], "note": "Open model for longer talking videos. Audio up to 10 MB.",
        "image": {"param": "image_url", "single": True, "min": 1, "max": 1, "mb": 10},
        "audio": {"param": "audio_url", "mb": 10},
        "prompt": {"max": 5000, "required": True, "default": "The person speaks naturally to the camera."},
        "res": {"param": "resolution", "options": ["480p", "720p"], "default": "480p"}},
    "omnihuman-1-5": {
        "label": "OmniHuman 1.5", "tools": ["talk"], "note": "Natural upper-body movement. Audio under 60 s.",
        "image": {"param": "image_url", "single": True, "min": 1, "max": 1, "mb": 10},
        "audio": {"param": "audio_url", "mb": 10, "seconds": (1, 59)},
        "prompt": {"max": 300},
        "res": {"param": "output_resolution", "options": ["720", "1080"], "default": "1080"}},
    "wan/2-2-a14b-speech-to-video-turbo": {
        "label": "Wan Speech to Video", "tools": ["talk"], "note": "Short clips (about 5 s). Audio up to 10 MB.",
        "image": {"param": "image_url", "single": True, "min": 1, "max": 1, "mb": 10},
        "audio": {"param": "audio_url", "mb": 10},
        "prompt": {"max": 5000, "required": True, "default": "The person speaks naturally to the camera."},
        "avoid": {"param": "negative_prompt", "max": 500},
        "res": {"param": "resolution", "options": ["480p", "580p", "720p"], "default": "480p"}, "safe": True},
    "volcengine/video-to-video-lip-sync": {
        "label": "Volcengine Lip Sync", "tools": ["lipsync"], "note": "One person facing the camera. Audio up to about 3.5 minutes.",
        "video": {"param": "video_url", "single": True, "mb": 100},
        "audio": {"param": "audio_url", "mb": 10, "seconds": (2, 210)},
        "extras": [{"key": "mode", "label": "Scene", "options": [["lite", "One person, facing the camera (faster)"],
                                                                 ["basic", "One person, harder scene"]], "default": "lite"}]},
    "wan/2-5-image-to-video": {
        "label": "Wan 2.5", "tools": ["animate"], "note": "5 or 10 seconds.",
        "image": {"param": "image_url", "single": True, "min": 1, "max": 1, "mb": 10},
        "prompt": {"max": 800, "required": True}, "avoid": {"param": "negative_prompt", "max": 500},
        "res": {"param": "resolution", "options": ["720p", "1080p"], "default": "720p"},
        "duration": {"param": "duration", "options": [5, 10], "as": "str", "default": 5}, "safe": True},
    "bytedance/seedance-2-fast": {
        "label": "Seedance 2.0 Fast", "tools": ["factory", "animate"], "note": "4-15 seconds, with sound.",
        "image": {"param": "first_frame_url", "single": True, "min": 0, "max": 1, "mb": 30},
        "prompt": {"max": 20000, "required": True},
        "res": {"param": "resolution", "options": ["480p", "720p"], "default": "720p"},
        "aspects": ["9:16", "16:9", "1:1", "4:3", "3:4", "21:9"],
        "duration": {"param": "duration", "min": 4, "max": 15, "as": "int", "default": 5},
        "sound": "generate_audio", "safe": True},
    "kling/v3-turbo-text-to-video": {
        "label": "Kling 3 Turbo", "tools": ["factory"], "note": "3-15 seconds.",
        "prompt": {"max": 2500, "required": True},
        "res": {"param": "resolution", "options": ["720p", "1080p"], "default": "720p"},
        "aspects": ["9:16", "16:9", "1:1"],
        "duration": {"param": "duration", "min": 3, "max": 15, "as": "str", "default": 5}},
    "wan/2-5-text-to-video": {
        "label": "Wan 2.5", "tools": ["factory"], "note": "5 or 10 seconds.",
        "prompt": {"max": 800, "required": True}, "avoid": {"param": "negative_prompt", "max": 500},
        "res": {"param": "resolution", "options": ["720p", "1080p"], "default": "720p"},
        "aspects": ["9:16", "16:9", "1:1"],
        "duration": {"param": "duration", "options": [5, 10], "as": "str", "default": 5}, "safe": True},
}


def models_for(tool: str) -> list[str]:
    return [k for k, m in MODELS.items() if tool in m["tools"]]


# ------------------------------------------------------------------ presets (prompt text, Hoola's own wording)
CAMERA_MOVES: list[tuple[str, str, str]] = [
    ("auto", "Auto", ""),
    ("static", "Static", "The camera is locked on a tripod and does not move."),
    ("dolly-in", "Dolly in", "A slow, smooth dolly in towards the subject."),
    ("dolly-out", "Dolly out", "A slow dolly out that pulls back and reveals the scene."),
    ("crash-zoom", "Crash zoom", "A sudden fast zoom into the subject."),
    ("orbit", "Orbit", "The camera circles smoothly all the way around the subject."),
    ("arc", "Arc", "The camera moves in a slow arc around the subject."),
    ("crane-up", "Crane up", "A crane shot that rises up and over the scene."),
    ("crane-down", "Crane down", "A crane shot that comes down towards the subject."),
    ("tracking", "Tracking", "A tracking shot that moves alongside the subject."),
    ("follow", "Follow", "The camera follows close behind the subject."),
    ("fpv", "FPV drone", "A fast, swooping first-person drone flight through the scene."),
    ("aerial", "Aerial", "A high aerial shot gliding slowly over the scene."),
    ("handheld", "Handheld", "A handheld camera with small, natural movement."),
    ("whip-pan", "Whip pan", "A very quick pan to the subject with motion blur."),
    ("pan-left", "Pan left", "A smooth pan to the left."),
    ("pan-right", "Pan right", "A smooth pan to the right."),
    ("tilt-up", "Tilt up", "The camera tilts up from the ground to the subject."),
    ("tilt-down", "Tilt down", "The camera tilts down from the sky to the subject."),
    ("bullet-time", "Bullet time", "The action freezes while the camera sweeps around the subject."),
    ("rack-focus", "Rack focus", "The focus shifts from the foreground to the subject."),
    ("dutch", "Dutch angle", "A tilted frame with slow movement."),
    ("pov", "POV", "A first-person point of view."),
    ("low-angle", "Low angle", "A low hero angle looking up at the subject, with a slow push in."),
    ("top-down", "Top down", "An overhead shot looking straight down, turning slowly."),
    ("zoom-out", "Zoom out", "A slow zoom out that shows the wider place."),
    ("slow-motion", "Slow motion", "Smooth slow motion."),
]
RESTYLES: list[tuple[str, str, str]] = [
    ("anime", "Anime", "modern anime with clean line art and vivid colour"),
    ("cel", "Cel animation", "hand-painted 2D cel animation"),
    ("clay", "Claymation", "claymation with handmade texture"),
    ("felt", "Felt stop-motion", "felt puppet stop-motion animation"),
    ("comic", "Comic book", "a bold comic-book drawing with ink outlines and halftone shading"),
    ("watercolour", "Watercolour", "a soft watercolour painting"),
    ("oil", "Oil painting", "an oil painting with visible brush strokes"),
    ("pixel", "Pixel art", "16-bit pixel art"),
    ("retro3d", "Retro game 3D", "1990s low-poly video-game 3D graphics"),
    ("bricks", "Toy bricks", "a world built from plastic toy bricks"),
    ("neon", "Neon night", "a neon-lit night city look"),
    ("noir", "Film noir", "black-and-white film noir with hard shadows"),
    ("vintage", "Vintage film", "1970s film stock with grain and warm faded colour"),
    ("sketch", "Pencil sketch", "a moving pencil sketch on paper"),
    ("madhubani", "Madhubani", "Madhubani folk painting with fine line patterns and flat natural colour"),
    ("warli", "Warli", "white Warli stick-figure art on a terracotta wall"),
]
LOOKS: list[tuple[str, str, str]] = [
    ("any", "Any look", ""),
    ("real", "Realistic", "Photorealistic, natural light, true-to-life detail."),
    ("cinematic", "Cinematic", "A cinematic film look: dramatic light, shallow depth of field, rich colour grade."),
    ("ugc", "Phone / UGC", "Looks shot on a phone by a real person: handheld, natural room light, casual framing."),
    ("product", "Product ad", "A polished product advertisement: clean studio light, crisp detail, smooth motion."),
    ("cartoon", "Cartoon", "Stylised cartoon animation with bold shapes, clean lines and bright colour."),
    ("moody", "Moody", "Low-key light, deep shadows, atmospheric."),
    ("bright", "Bright and playful", "Bright saturated colour and playful energy."),
]
# Cinema still: generic camera language only (no maker or product names)
STILL: dict[str, list[tuple[str, str, str]]] = {
    "camera": [
        ("digital-ff", "Full-frame digital cinema", "shot on a full-frame digital cinema camera, clean detail and wide dynamic range"),
        ("digital-s35", "Super 35 digital", "shot on a Super 35 digital cinema camera"),
        ("large-format", "Large-format digital", "shot on a large-format digital cinema camera, very shallow depth and smooth tonal roll-off"),
        ("film-35", "35 mm film", "shot on 35 mm motion picture film, fine grain and gentle halation"),
        ("film-16", "16 mm film", "shot on 16 mm film, visible grain and a documentary feel"),
        ("film-70", "70 mm film", "shot on 70 mm film, huge detail and an epic scale"),
    ],
    "lens": [
        ("modern-prime", "Modern prime", "a sharp modern prime lens"),
        ("vintage-prime", "Vintage prime", "a vintage prime lens with soft contrast and gentle flare"),
        ("anamorphic", "Anamorphic", "an anamorphic lens with oval bokeh and horizontal flares"),
        ("macro", "Macro", "a macro lens, extreme close detail"),
        ("tilt-shift", "Tilt-shift", "a tilt-shift lens with a thin slice of focus"),
        ("swirl", "Swirl-bokeh portrait", "a portrait lens with swirling background blur"),
        ("diffusion", "Soft diffusion", "a diffusion filter that blooms the highlights"),
    ],
    "focal": [
        ("14", "14 mm ultra-wide", "14mm ultra-wide angle"), ("24", "24 mm wide", "24mm wide angle"),
        ("35", "35 mm natural", "35mm, a natural field of view"), ("50", "50 mm portrait", "50mm"),
        ("85", "85 mm tight portrait", "85mm, a tight flattering portrait"), ("135", "135 mm telephoto", "135mm telephoto, compressed background"),
    ],
    "aperture": [
        ("f1.4", "f/1.4 soft background", "f/1.4, very shallow depth of field"),
        ("f2.8", "f/2.8", "f/2.8, shallow depth of field"),
        ("f4", "f/4 balanced", "f/4, balanced depth of field"),
        ("f11", "f/11 everything sharp", "f/11, deep focus, everything sharp"),
    ],
    "light": [
        ("any", "Any light", ""), ("golden", "Golden hour", "warm golden-hour light"), ("window", "Window light", "soft window light from one side"),
        ("hard", "Hard sun", "hard midday sun with crisp shadows"), ("night", "Night practicals", "night, lit by practical lamps and signs"),
        ("studio", "Studio softbox", "soft studio light"), ("rim", "Rim light", "a strong rim light separating the subject from a dark background"),
    ],
}
PLATFORMS: list[tuple[str, str, str]] = [
    ("reels", "Reels / Shorts", "9:16"), ("wide", "YouTube / web", "16:9"), ("square", "Square post", "1:1")]
ANGLES: list[str] = [
    "Open on a striking visual hook in the first second, then show the subject.",
    "A close detail shot with slow, deliberate camera movement.",
    "A wide establishing shot with a smooth push in towards the subject.",
    "A person using or enjoying the subject, with a natural reaction.",
    "A clear before-and-after change.",
    "A fast rhythmic montage feel with a satisfying finish.",
]
MAX_BATCH = 6


def _pick(rows: list[tuple[str, str, str]], key: str) -> str:
    return next((r[2] for r in rows if r[0] == key), "")


def camera_text(key: str) -> str:
    return _pick(CAMERA_MOVES, key)


def restyle_prompt(key: str, extra: str = "") -> str:
    look = _pick(RESTYLES, key)
    if not look:
        raise ValueError("Pick a look for the restyle.")
    out = f"Restyle the entire video as {look}. Keep the original motion, timing, camera movement and composition."
    extra = " ".join((extra or "").split())
    return f"{out} {extra}" if extra else out


def still_prompt(prompt: str, camera: str = "", lens: str = "", focal: str = "", aperture: str = "", light: str = "") -> str:
    """The Cinema still: her words first, then the camera language she picked, as plain prompt text."""
    prompt = " ".join((prompt or "").split())
    if not prompt:
        raise ValueError("Describe the picture first.")
    bits = [_pick(STILL["camera"], camera), _pick(STILL["lens"], lens), _pick(STILL["focal"], focal),
            _pick(STILL["aperture"], aperture), _pick(STILL["light"], light)]
    bits = [b for b in bits if b]
    tail = ("Cinematic film still, " + ", ".join(bits) + ".") if bits else "Cinematic film still."
    return f"{prompt.rstrip('. ')}. {tail}"[:4000]


def scene_prompt(topic: str, i: int, look: str = "", camera: str = "") -> str:
    """One factory scene written by rule (used when no model is there to write it): topic + a different angle each."""
    topic = " ".join((topic or "").split()).rstrip(". ")
    parts = [f"{topic}.", ANGLES[i % len(ANGLES)], _pick(LOOKS, look), camera_text(camera)]
    return " ".join(p for p in parts if p)


# ------------------------------------------------------------------ the one request builder
def build(model: str, *, prompt: str = "", images: list[str] | None = None, video: str = "", audio: str = "",
          resolution: str = "", aspect: str = "", seconds: int | None = None, avoid: str = "", sound: bool | None = None,
          extras: dict[str, Any] | None = None) -> dict[str, Any]:
    """The engine's `input` object for one job. Refuses (ValueError) rather than send a shape the spec does not have."""
    m = MODELS.get(model)
    if not m:
        raise ValueError(f"Unknown model: {model}")
    images = [u for u in (images or []) if u]
    out: dict[str, Any] = {}
    p = m.get("prompt")
    text = " ".join((prompt or "").split())
    if p:
        text = text or p.get("default", "")
        if p.get("required") and not text:
            raise ValueError(f"{m['label']} needs a line describing what you want.")
        if len(text) > p["max"]:
            raise ValueError(f"{m['label']} takes up to {p['max']} characters; this is {len(text)}.")
        if text:
            out["prompt"] = text
    im = m.get("image")
    if im:
        if len(images) < im["min"]:
            raise ValueError(f"{m['label']} needs {'a photo' if im['min'] == 1 else str(im['min']) + ' photos'}.")
        if len(images) > im["max"]:
            raise ValueError(f"{m['label']} takes at most {im['max']} photo{'s' if im['max'] != 1 else ''}.")
        if images:
            out[im["param"]] = images[0] if im.get("single") else images
    elif images:
        raise ValueError(f"{m['label']} does not take photos.")
    v = m.get("video")
    if v:
        if not video:
            raise ValueError(f"{m['label']} needs a source video.")
        out[v["param"]] = video if v.get("single") else [video]
    elif video:
        raise ValueError(f"{m['label']} does not take a source video.")
    a = m.get("audio")
    if a:
        if not audio:
            raise ValueError(f"{m['label']} needs audio.")
        out[a["param"]] = audio
    elif audio:
        raise ValueError(f"{m['label']} does not take audio.")
    r = m.get("res")
    if r:
        val = resolution or r["default"]
        if val not in r["options"]:
            raise ValueError(f"{m['label']} makes {', '.join(r['options'])}; not {val}.")
        out[r["param"]] = val
    if m.get("aspects"):
        val = aspect or m["aspects"][0]
        if val not in m["aspects"]:
            raise ValueError(f"{m['label']} makes {', '.join(m['aspects'])}; not {val}.")
        out["aspect_ratio"] = val
    d = m.get("duration")
    if d:
        val = int(seconds or d["default"])
        if "options" in d:
            if val not in d["options"]:
                raise ValueError(f"{m['label']} makes {' or '.join(str(x) for x in d['options'])} seconds; not {val}.")
        elif not d["min"] <= val <= d["max"]:
            raise ValueError(f"{m['label']} makes {d['min']}-{d['max']} seconds; not {val}.")
        out[d["param"]] = str(val) if d["as"] == "str" else val
    av = m.get("avoid")
    if av and (avoid or "").strip():
        out[av["param"]] = " ".join(avoid.split())[:av["max"]]
    if m.get("sound") and sound is not None:
        out[m["sound"]] = bool(sound)
    for f in m.get("extras") or []:
        val = (extras or {}).get(f["key"], f["default"])
        if val not in [o[0] for o in f["options"]]:
            raise ValueError(f"{f['label']}: pick one of {', '.join(o[0] for o in f['options'])}.")
        out[f["key"]] = val
    if m.get("safe"):
        out["nsfw_checker"] = True          # the engine's default is NO filter; Hoola always asks for it
    return out


def public() -> dict[str, Any]:
    """What the page needs: tools, the models of each tool with their limits, and the preset lists."""
    def one(k: str) -> dict[str, Any]:
        m = MODELS[k]
        out = {"id": k, "label": m["label"], "note": m.get("note", ""), "tools": m["tools"],
               "res": (m.get("res") or {}).get("options") or [], "res_default": (m.get("res") or {}).get("default", ""),
               "aspects": m.get("aspects") or [], "prompt_max": (m.get("prompt") or {}).get("max", 0),
               "prompt_required": bool((m.get("prompt") or {}).get("required")) and not (m.get("prompt") or {}).get("default"),
               "avoid": bool(m.get("avoid")), "sound": bool(m.get("sound")), "extras": m.get("extras") or []}
        for part in ("image", "video", "audio"):
            if m.get(part):
                out[part] = {"min": m[part].get("min", 1), "max": m[part].get("max", 1), "mb": m[part]["mb"],
                             "seconds": list(m[part]["seconds"]) if m[part].get("seconds") else None}
        if m.get("duration"):
            d = m["duration"]
            out["duration"] = {"options": d.get("options"), "min": d.get("min"), "max": d.get("max"), "default": d["default"]}
        return out
    rows = lambda L: [{"id": a, "label": b, "text": c} for a, b, c in L]   # noqa: E731
    return {"spec_date": SPEC_DATE, "tools": TOOLS, "models": [one(k) for k in MODELS],
            "camera_moves": rows(CAMERA_MOVES), "restyles": rows(RESTYLES), "looks": rows(LOOKS),
            "still": {k: rows(v) for k, v in STILL.items()},
            "platforms": [{"id": a, "label": b, "aspect": c} for a, b, c in PLATFORMS], "max_batch": MAX_BATCH}
