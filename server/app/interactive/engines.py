"""v0.999.170 HOOLA INTERACTIVE REBUILD - the engines she chooses (contract docs/HOOLA_INTERACTIVE_REBUILD.md part 3).

The brain and the voice stay Hoola's; only the FACE is chosen. Three jobs:

    video   a finished talking MP4 (Hoola standard, Kling AI Avatar, OmniHuman, InfiniteTalk, Wan, Runway, HeyGen, Hedra)
    live    a face that listens and talks in a browser (Simli, Anam, HeyGen LiveAvatar, Tavus, bitHuman, the GPU lab)
    broll   a short shot without a person (Gemini Omni / Veo on the Gemini API, HyperFrames looks)

Every engine is one row of ENGINES: what it does, a quality mark, languages, the vendor's PUBLISHED price per minute, the
key it needs (a name in the VPS .env, never a value), whether its adapter is built here, and `connected()` read from this
server - never assumed. Her default per job is kept in her studio.json ("engines").

Rules:
  PRICE    `quote()` = engine price x minutes -> credits (1 credit = $0.001, the Vocal rule) BEFORE every paid make; the
           make refuses unless her tap carries that exact quote (`check_quote`).
  SAID     an engine that is not connected / not built says so with the key it needs; a vendor refusal is said in the
           vendor's own words (scrubbed of keys).
  KEYS     keys are read from settings / the environment only; no route returns one; a browser gets short-lived tokens.
  CONSENT  a face engine only ever drives an avatar that has her consent on record (studio.add_avatar refuses otherwise).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Any, Callable

log = logging.getLogger("santosh.interactive.engines")

CREDIT_USD = 0.001

# id, job, label, what, quality 1-5, languages, usd per minute (published, low-high), key env names, adapter kind
ENGINES: list[dict[str, Any]] = [
    {"id": "hoola", "job": "video", "label": "Hoola standard", "what": "Your photo beside the words, scenes and numbers drawn by HyperFrames",
     "quality": 2, "langs": "140 (Hoola voices)", "usd_min": (0.0, 0.0), "keys": [], "adapter": "frames", "face": False},
    {"id": "kling", "job": "video", "label": "Kling AI Avatar", "what": "Your photo talks with steady lips, up to 5 minutes",
     "quality": 4, "langs": "any (follows the voice)", "usd_min": (3.03, 3.03), "keys": ["KIE_API_KEY"], "adapter": "kie",
     "model": "kling/ai-avatar-standard", "max_s": 300, "face": True},
    {"id": "kling_pro", "job": "video", "label": "Kling AI Avatar Pro", "what": "More facial detail, up to 5 minutes",
     "quality": 5, "langs": "any (follows the voice)", "usd_min": (6.06, 6.06), "keys": ["KIE_API_KEY"], "adapter": "kie",
     "model": "kling/ai-avatar-pro", "max_s": 300, "face": True},
    {"id": "omnihuman", "job": "video", "label": "OmniHuman 1.5", "what": "A photo becomes a talking, gesturing upper body (under a minute)",
     "quality": 5, "langs": "any (follows the voice)", "usd_min": (4.2, 9.6), "keys": ["KIE_API_KEY"], "adapter": "kie",
     "model": "omnihuman-1-5", "max_s": 59, "face": True},
    {"id": "infinitetalk", "job": "video", "label": "InfiniteTalk", "what": "Long talking videos, open model",
     "quality": 3, "langs": "any (follows the voice)", "usd_min": (0.9, 3.9), "keys": ["KIE_API_KEY"], "adapter": "kie",
     "model": "infinitalk/from-audio", "max_s": 600, "face": True},
    {"id": "wan_s2v", "job": "video", "label": "Wan Speech to Video", "what": "Short talking clips (about 5 seconds), the cheapest",
     "quality": 2, "langs": "any (follows the voice)", "usd_min": (0.9, 7.8), "keys": ["KIE_API_KEY"], "adapter": "kie",
     "model": "wan/2-2-a14b-speech-to-video-turbo", "max_s": 15, "face": True},
    {"id": "runway", "job": "video", "label": "Runway avatar", "what": "One reference photo, the cheapest talking face",
     "quality": 3, "langs": "any (follows the voice)", "usd_min": (0.2, 0.2), "keys": ["RUNWAY_API_KEY"], "adapter": "runway", "face": True},
    {"id": "heygen", "job": "video", "label": "HeyGen Avatar", "what": "Studio quality talking photo, consent built in",
     "quality": 5, "langs": "175+ for translation", "usd_min": (1.0, 7.0), "keys": ["HEYGEN_API_KEY"], "adapter": "heygen", "face": True},
    {"id": "hedra", "job": "video", "label": "Hedra Character-3", "what": "Expressive characters up to 10 minutes",
     "quality": 4, "langs": "many", "usd_min": (1.5, 3.75), "keys": ["HEDRA_API_KEY"], "adapter": "hedra", "face": True},

    {"id": "simli", "job": "live", "label": "Simli", "what": "Face only; Hoola's brain and voice drive it",
     "quality": 3, "langs": "any (follows the voice)", "usd_min": (0.005, 0.01), "keys": ["SIMLI_API_KEY"], "adapter": "simli"},
    {"id": "anam", "job": "live", "label": "Anam", "what": "Faces from a photo or words, quick replies",
     "quality": 4, "langs": "70+", "usd_min": (0.04, 0.16), "keys": ["ANAM_API_KEY"], "adapter": "anam"},
    {"id": "liveavatar", "job": "live", "label": "HeyGen LiveAvatar", "what": "HeyGen faces, Hoola's voice and brain (LITE)",
     "quality": 5, "langs": "any (follows the voice)", "usd_min": (0.1, 0.13), "keys": ["HEYGEN_API_KEY"], "adapter": "liveavatar"},
    {"id": "tavus", "job": "live", "label": "Tavus", "what": "Sees the person, best turn-taking; Hoola's brain",
     "quality": 5, "langs": "42+", "usd_min": (0.26, 0.35), "keys": ["TAVUS_API_KEY"], "adapter": "tavus"},
    {"id": "gpulab", "job": "live", "label": "Hoola GPU lab", "what": "MuseTalk on your own GPU, no company in between",
     "quality": 3, "langs": "any (follows the voice)", "usd_min": (0.0, 0.0), "keys": ["AVATAR_ENGINE_URL", "AVATAR_ENGINE_KEY"],
     "adapter": "gpulab"},
    {"id": "voice_only", "job": "live", "label": "Voice only", "what": "No face: Hoola listens and answers in a Vocal voice",
     "quality": 2, "langs": "140 (Hoola voices)", "usd_min": (0.0, 0.0), "keys": [], "adapter": "voice"},

    {"id": "gemini_broll", "job": "broll", "label": "Gemini Omni", "what": "A 4-8 s shot with its own sound: the shop, the product - never a person",
     "quality": 4, "langs": "any", "usd_min": (4.2, 4.2), "keys": ["GEMINI_API_KEY"], "adapter": "gemini_video"},
    {"id": "frames_looks", "job": "broll", "label": "HyperFrames looks", "what": "Titles, prices, charts, name strips drawn by Hoola",
     "quality": 3, "langs": "any", "usd_min": (0.0, 0.0), "keys": [], "adapter": "frames"},
]
BY_ID = {e["id"]: e for e in ENGINES}
JOBS = ("video", "live", "broll")
DEFAULTS = {"video": "hoola", "live": "voice_only", "broll": "frames_looks"}
BUILT = {"frames", "kie", "runway", "heygen", "hedra", "simli", "anam", "liveavatar", "tavus", "gpulab", "voice", "gemini_video"}


class EngineError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


# ------------------------------------------------------------------ keys + connected (read, never assumed) ---
def _key(name: str) -> str:
    from ..config import get_settings
    st = get_settings()
    v = getattr(st, name.lower(), None)
    if v is None and name == "GEMINI_API_KEY":
        v = getattr(st, "gemini_api_key", None)
    return str(v or os.environ.get(name) or "").strip()


def key_of(eid: str) -> str:
    e = BY_ID[eid]
    return _key(e["keys"][0]) if e["keys"] else ""


def connected(eid: str) -> bool:
    e = BY_ID.get(eid)
    if not e:
        return False
    if e["adapter"] == "frames":
        from ..studio import frames
        return bool(frames.configured())
    if e["adapter"] == "voice":
        return True
    if e["adapter"] == "gpulab":
        from . import lab
        return bool(lab.configured())
    return all(_key(k) for k in e["keys"])


def status_of(eid: str) -> str:
    e = BY_ID[eid]
    if e["adapter"] not in BUILT:
        return "Not built yet"
    if connected(eid):
        return "Ready"
    if e["adapter"] == "frames":
        return "The video drawer is not installed on this server"
    return "Add " + " and ".join(e["keys"]) if e["keys"] else "Not connected"


def view(tenant: str = "") -> dict[str, Any]:
    defaults = defaults_of(tenant) if tenant else dict(DEFAULTS)
    rows = []
    for e in ENGINES:
        st = status_of(e["id"])
        lo, hi = e["usd_min"]
        price = "free" if hi == 0 else (f"≈ ${lo:g}/min" if lo == hi else f"${lo:g}-{hi:g}/min")
        rows.append({"id": e["id"], "job": e["job"], "label": e["label"], "what": e["what"], "quality": e["quality"],
                     "langs": e["langs"], "price": price, "usd_min": hi, "status": st, "ready": st == "Ready",
                     "keys": e["keys"], "default": defaults.get(e["job"]) == e["id"], "face": bool(e.get("face")),
                     "max_s": e.get("max_s"), "usd_lo": lo, "need": need_of(e["id"])})
    return {"engines": rows, "defaults": defaults,
            "notes": {"video": "Every language works on every face engine: the face follows your Vocal voice.",
                      "live": "The listening and the voice stay Hoola's; only the face is rented.",
                      "broll": "A shot without a person; never your face."}}


def need_of(eid: str) -> str:
    """v0.999.208 what an engine that is not ready needs, in plain words (never a key name)."""
    e = BY_ID[eid]
    if e["adapter"] not in BUILT:
        return "Hoola does not drive this engine yet."
    if connected(eid):
        return ""
    if e["adapter"] == "frames":
        return "The video drawer is not installed on this server yet. Whoever runs your Hoola server installs it."
    if e["adapter"] == "gpulab":
        return "Your own GPU lab is not linked yet. Whoever runs your Hoola server adds its address in the server's settings."
    return ("Its key is added by whoever runs your Hoola server, in the server's settings. Once it is there, this engine "
            "turns Ready by itself. Nothing is typed into this page.")


LENGTHS = {"video": (15, 30, 60, 180, 300), "live": (60, 300, 900, 1800), "broll": (4, 6, 8)}


def prices(job: str, seconds: float, voice_credits: int = 0) -> dict[str, Any]:
    """v0.999.208 every engine of one job priced for one length, the same way the Make price card prices it."""
    if job not in JOBS:
        raise EngineError("Pick videos, live agents or B-roll shots.")
    secs = max(1.0, min(float(seconds or 0), 3600.0))
    out = []
    for e in ENGINES:
        if e["job"] != job:
            continue
        q = quote(e["id"], secs, voice_credits)
        out.append({"id": e["id"], "credits": q["credits"], "face_credits": q["face_credits"],
                    "voice_credits": q["voice_credits"], "too_long": bool(e.get("max_s") and secs > e["max_s"])})
    return {"job": job, "seconds": secs, "voice_credits": int(voice_credits or 0), "engines": out}


def ladder(eid: str, voice_for: Callable[[float], int] | None = None) -> list[dict[str, Any]]:
    """v0.999.208 one engine's price at each usual length (the detail panel's table)."""
    e = BY_ID.get(eid)
    if not e:
        raise EngineError("That engine is not on the list.")
    rows = []
    for secs in LENGTHS[e["job"]]:
        vc = int(voice_for(float(secs)) if (voice_for and e["job"] == "video") else 0)
        q = quote(eid, float(secs), vc)
        rows.append({"seconds": secs, "face": q["face_credits"], "voice": q["voice_credits"], "credits": q["credits"],
                     "too_long": bool(e.get("max_s") and secs > e["max_s"])})
    return rows


# ------------------------------------------------------------------ her defaults ---
def defaults_of(tenant: str) -> dict[str, str]:
    from . import studio as S
    got = S._load(tenant).get("engines") or {}
    out = dict(DEFAULTS)
    for job in JOBS:
        eid = str(got.get(job) or "")
        if eid in BY_ID and BY_ID[eid]["job"] == job:
            out[job] = eid
    return out


def set_default(tenant: str, eid: str) -> dict[str, str]:
    from . import studio as S
    e = BY_ID.get(eid)
    if not e:
        raise EngineError("That engine is not on the list.")
    if not connected(eid):
        raise EngineError(f"{e['label']} is not connected on this server yet: {status_of(eid)}.", 409)
    with S._LOCK:
        d = S._load(tenant)
        eng = d.get("engines") if isinstance(d.get("engines"), dict) else {}
        eng[e["job"]] = eid
        d["engines"] = eng
        S._store(tenant, d)
    return defaults_of(tenant)


# ------------------------------------------------------------------ price ---
def _margin() -> float:
    from ..config import get_settings
    try:
        return max(1.0, float(getattr(get_settings(), "interactive_credit_margin", 1.0) or 1.0))
    except (TypeError, ValueError):
        return 1.0


def quote(eid: str, seconds: float, voice_credits: int = 0) -> dict[str, Any]:
    """What one make costs, before she taps: the face engine's published price x minutes, plus the voice."""
    e = BY_ID.get(eid)
    if not e:
        raise EngineError("That engine is not on the list.")
    mins = max(float(seconds or 0), 1.0) / 60.0
    usd = e["usd_min"][1] * mins * _margin()
    face = max(1, round(usd / CREDIT_USD)) if usd else 0
    total = face + int(voice_credits or 0)
    key = hashlib.sha256(f"{eid}|{round(seconds, 1)}|{total}".encode()).hexdigest()[:16]
    line = (f"{e['label']} · about {round(seconds)} s · about {total} credit{'' if total == 1 else 's'}"
            + (f" (face {face}, voice {voice_credits})" if face and voice_credits else "")
            + " · nothing is spent until you tap")
    return {"engine": eid, "label": e["label"], "seconds": round(seconds, 1), "face_credits": face,
            "voice_credits": int(voice_credits or 0), "credits": total, "usd": round(usd, 3), "key": key, "line": line,
            "published": e["usd_min"]}


def check_quote(q: dict[str, Any], given: str) -> None:
    """A paid FACE engine (or a B-roll shot) needs her tap on this exact price; the voice alone follows Vocal's rule
    (the price is shown, the Make button is her tap)."""
    if q["face_credits"] and str(given or "") != q["key"]:
        raise EngineError(f"Confirm the price first: {q['line']}.", 409)


def charge(tenant: str, q: dict[str, Any]) -> None:
    """The face engine's cost into her credits (the voice is charged by Vocal itself)."""
    if not q.get("usd"):
        return
    try:
        from ..credits import wallet as W
        W.note(tenant, float(q["usd"]), "interactive")
    except Exception:   # noqa: BLE001
        log.exception("interactive credit note failed")


# ------------------------------------------------------------------ video adapters ---
def _sniff_video(data: bytes) -> bool:
    return len(data) > 1000 and data[4:8] in (b"ftyp", b"moov", b"mdat", b"free")


def _wait(poll: Callable[[], dict[str, Any]], cancel: Any, on_wait: Callable[[str], None] | None, label: str,
          limit_s: int = 1800, every: float = 6.0) -> dict[str, Any]:
    """Poll a vendor job until it is done, failed, stopped or too slow. `poll` returns {state, url, error}."""
    t0 = time.time()
    while True:
        if cancel is not None and cancel.is_set():
            raise EngineError("Stopped. Nothing was kept.")
        r = poll()
        if r["state"] == "success":
            return r
        if r["state"] == "fail":
            raise EngineError(f"{label} could not make it: {r.get('error') or 'no reason given'}", 502)
        if time.time() - t0 > limit_s:
            raise EngineError(f"{label} took longer than {limit_s // 60} minutes. Try again later.", 504)
        if on_wait:
            on_wait(f"{label}: {r['state']} · {int(time.time() - t0)} s")
        time.sleep(every)


def _fetch(url: str) -> bytes:
    """The finished file at the vendor's own link, through Cinema's link wall (public https only), size-capped."""
    from ..agent import shilp_tools as SH
    from ..cinema import service as C
    safe = SH._ref_url(url or "", "result")
    if not safe.startswith("https://"):
        raise EngineError("The engine's file link is not https.", 502)
    _ctype, data = asyncio.run(C._fetch(safe))
    if not _sniff_video(data):
        raise EngineError("The engine's file is not a video.", 502)
    return data


def _kie_face(e: dict[str, Any], photo: bytes, photo_name: str, wav: bytes, cancel: Any,
              on_wait: Callable[[str], None] | None) -> bytes:
    from ..cinema import kie
    from ..cinema import specs as CS

    async def up() -> str:
        ext = photo_name.rsplit(".", 1)[-1].lower() if "." in photo_name else "jpg"
        img = await kie.upload(photo, f"face.{ext}", "image/png" if ext == "png" else "image/webp" if ext == "webp" else "image/jpeg")
        aud = await kie.upload(wav, "voice.wav", "audio/wav")
        m = CS.MODELS[e["model"]]
        res = (m.get("res") or {}).get("default", "")
        return await kie.create(e["model"], CS.build(e["model"], images=[img], audio=aud, resolution=res))

    try:
        task = asyncio.run(up())
    except kie.KieError as err:
        raise EngineError(str(err), 402 if err.code == "PAYMENT" else 502) from None
    except ValueError as err:
        raise EngineError(str(err)) from None

    def poll() -> dict[str, Any]:
        try:
            t = asyncio.run(kie.task(task))
        except kie.KieError as err:
            raise EngineError(str(err), 502) from None
        return {"state": "success" if t["state"] == "success" else "fail" if t["state"] == "fail" else t["state"],
                "url": (t["urls"] or [""])[0], "error": t["error"]}

    r = _wait(poll, cancel, on_wait, e["label"])
    if not r["url"]:
        raise EngineError(f"{e['label']} finished but returned no file.", 502)
    return _fetch(r["url"])


def face_video(eid: str, photo: bytes, photo_name: str, wav: bytes, seconds: float, cancel: Any = None,
               on_wait: Callable[[str], None] | None = None) -> bytes:
    """Her photo + the spoken track -> a talking MP4 from the chosen engine."""
    e = BY_ID.get(eid)
    if not e or e["job"] != "video" or not e.get("face"):
        raise EngineError("That engine does not make a talking face.")
    if not connected(eid):
        raise EngineError(f"{e['label']} is not connected on this server: {status_of(eid)}.", 409)
    if e.get("max_s") and seconds > e["max_s"] + 0.5:
        raise EngineError(f"{e['label']} takes up to {e['max_s']} seconds of speech; this video is {round(seconds)} s. "
                          "Shorten it or pick another engine.")
    if e["adapter"] == "kie":
        return _kie_face(e, photo, photo_name, wav, cancel, on_wait)
    from . import vendors as VD
    fn = {"runway": VD.runway_face, "heygen": VD.heygen_face, "hedra": VD.hedra_face}.get(e["adapter"])
    if fn is None:
        raise EngineError(f"{e['label']} is not built yet.", 501)
    url = fn(_key(e["keys"][0]), photo, photo_name, wav, seconds, cancel, on_wait, _wait)
    return _fetch(url)


def broll(tenant: str, eid: str, prompt: str, seconds: int, aspect: str, cancel: Any = None,
          on_wait: Callable[[str], None] | None = None) -> bytes:
    e = BY_ID.get(eid)
    if not e or e["job"] != "broll" or e["adapter"] == "frames":
        raise EngineError("Pick a B-roll engine that makes a video shot.")
    if not connected(eid):
        raise EngineError(f"{e['label']} is not connected on this server: {status_of(eid)}.", 409)
    from . import vendors as VD
    url_or_bytes = VD.gemini_video(_key("GEMINI_API_KEY"), prompt, seconds, aspect, cancel, on_wait, _wait)
    return url_or_bytes if isinstance(url_or_bytes, bytes) else _fetch(url_or_bytes)


def live_session(tenant: str, eid: str, agent: dict[str, Any]) -> dict[str, Any]:
    """A short-lived pass for the browser to show the chosen live face. The vendor key never leaves the server."""
    e = BY_ID.get(eid)
    if not e or e["job"] != "live":
        raise EngineError("Pick a live face engine.")
    if not connected(eid):
        raise EngineError(f"{e['label']} is not connected on this server: {status_of(eid)}.", 409)
    if e["adapter"] == "voice":
        return {"engine": eid, "kind": "voice"}
    if e["adapter"] == "gpulab":
        from . import lab
        try:
            return {"engine": eid, "kind": "gpulab", "address": lab.live_address(),
                    "ticket": lab.make_ticket(str(agent.get("avatar_id") or "lab-live"))}
        except lab.LabError as err:
            raise EngineError(str(err), 503) from None
    from . import vendors as VD
    fn = {"simli": VD.simli_session, "anam": VD.anam_session, "liveavatar": VD.liveavatar_session,
          "tavus": VD.tavus_session}.get(e["adapter"])
    if fn is None:
        raise EngineError(f"{e['label']} is not built yet.", 501)
    out = fn(_key(e["keys"][0]), agent)
    out.update(engine=eid)
    return out


def ai_mark(path: str) -> None:
    """The AI mark written into the MP4's own metadata (said on the page as well)."""
    import shutil
    import subprocess
    import tempfile
    if not shutil.which("ffmpeg"):
        return
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "m.mp4")
        try:
            subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", path, "-map", "0", "-c", "copy",
                            "-metadata", "comment=Made with AI by Hoola Interactive", "-metadata", "ai_generated=true",
                            "-movflags", "+faststart", out], capture_output=True, timeout=120, check=True)
            shutil.copyfile(out, path)
        except Exception:   # noqa: BLE001
            log.warning("interactive AI mark not written to %s", path)


def dumps(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False)
