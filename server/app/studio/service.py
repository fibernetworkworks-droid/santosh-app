"""v0.68 Hoola Video Studio inside Hoola: the owner's hoola-studio engine (brief -> characters -> storyboard -> free
preview -> paid AI shots -> review -> voice, music, logo, captions -> final video), directed by the avatar.

Hoola's rules on top of her engine:
  * Money moves only with the owner's tap: every paid generation (draft / final shots, generated character images)
    becomes a `studio_approval` card with the price in rupees and dollars; nothing paid runs before her Haan, and
    the run is capped at the amount she approved. A monthly ceiling per owner (`STUDIO_MONTH_USD`) on top.
  * Only her own files: photos, start frames, narration, music and logos come from her Hoola files (file_id) and are
    copied into her studio folder; a real person's photo needs her word that she has their permission.
  * The "AI-generated" label is always on the final video; no imitating real brands, news or officials (guide).
  * API keys only from the server's settings (.env); provider downloads only from the public internet.
Free extras from Hoola: narration in the avatar's own voice (Gemini TTS) and royalty-free music beds (Hoola Motion).
"""
from __future__ import annotations

import asyncio
import base64
import datetime as dt
import json
import logging
import re
import shutil
import time
import wave
from pathlib import Path
from typing import Any

from ..config import get_settings
from . import catalog
from .studio import Studio, StudioError, slug

log = logging.getLogger("santosh.studio")

_studios: dict[str, tuple[Any, Studio]] = {}
_watchers: dict[str, asyncio.Task] = {}
_assembling: dict[str, asyncio.Task] = {}
_planning: dict[str, asyncio.Task] = {}
KEYFRAME_USD = 0.14            # Nano Banana Pro 2K picture (+ thinking), conservative
MUSIC_USD = 0.08               # Lyria 3.5 song

GUIDE = """HOOLA VIDEO STUDIO (v0.157: best model per shot) - you are the director. Flow:
1. BRIEF: purpose (ad, reel, explainer, invite, story...), audience, length, language, shape (9:16 reel / short, 16:9
   YouTube, 1:1 feed), her assets (logo, product photos, people), quality (draft / HD / premium). Ask only what is missing.
2. create(name, aspect, style, language, brief). Styles: """ + ", ".join(catalog.STYLES) + """.
3. CHARACTERS (same person / product in every shot): character with her photo file_ids (a real person only with that
   person's permission: consent=true only when she said yes; voice female|male for their spoken lines) or
   character_generate for fictional people, mascots, products.
4. STORYBOARD: plan(brief, seconds) writes it for you (Claude, prompts tuned for the video models) - or storyboard(shots).
   Each shot has a KIND: scene (people / places / story), product (her product comes alive), talk (a person speaks to
   camera: painted portrait + her line, lip-synced in any language), dialogue (people talk inside a scene, lips re-synced),
   link (moves from one picture to the next). Spoken lines in Hindi / Indian languages are spoken by Hoola's own voice and
   lip-synced (Sync 3); English etc. by the video model.
5. keyframes() paints each shot's opening picture with Nano Banana Pro (~Rs 12 each, a card): the real look, and the
   video starts from it (same face everywhere). generate(quality='preview') is FREE: an animatic from those pictures.
6. Paid shots: generate(quality='draft' 720p | 'final' HD 1080p | 'premium'). The router picks the best model per shot:
   scene = Wan 3.0 (HD) / Seedance 2.5 (premium); product = MiniMax H3; talk = Sync 3; link = Gemini Omni Flash.
   Never spends by itself: she gets a card with the price and taps Haan. Missing keyframes for HD / premium are painted
   in the same card. Tell her the price in rupees. Regenerate only the shots that need it (shot_ids).
7. review(shot_id) (also runs by itself on paid takes: score + problems); shot_update + generate(shot_ids, variants=2);
   pick(shot_id, take).
8. FINISH: voiceover(shot_id, text) in your own voice or her audio file_id, music(mood: a real Lyria track, or her
   licensed file_id), logo(file_id), then assemble. The AI-generated label always stays on.
Never make videos of real people without their permission, or that imitate real brands, news, officials or
politicians; no explicit, violent or hateful content. Nothing is posted anywhere: she shares the video herself.""" + ", ".join(catalog.STYLES) + """.
3. CHARACTERS (same person / product in every shot): character with her photo file_ids (a real person only with that
   person's permission: ask her and pass consent=true only when she said yes) or character_generate for fictional
   people, mascots, products.
4. STORYBOARD: 3-8 shots of 4-10 s. Each: what we SEE and what HAPPENS (subject, action, place, light) in one concrete
   sentence, camera (""" + ", ".join(catalog.CAMERA) + """), characters, dialogue (spoken on camera in the project
   language, lip-synced) OR voiceover text, and a short caption. One idea per shot.
5. generate(quality='preview') is FREE: an animatic to agree story and timing. assemble it and show her.
6. Paid shots: generate(quality='draft' (cheap, 480p) or 'final' (1080p)). This never spends by itself: she gets a card
   with the price and taps Haan. Tell her the price in rupees. Regenerate only the shots that need it (shot_ids).
7. review(shot_id) looks at a take; shot_update + generate(shot_ids=[..], variants=2) to fix; pick(shot_id, take).
8. FINISH: voiceover(shot_id, text) in your own voice (free) or her audio file_id, music(mood upbeat|calm|festive, free)
   or her licensed music, logo(file_id), then assemble. The AI-generated label always stays on.
Never make videos of real people without their permission, or that imitate real brands, news, officials or
politicians; no explicit, violent or hateful content. Nothing is posted anywhere: she shares the video herself."""


class StudioJobError(Exception):
    pass


def _st():
    return get_settings()


def available() -> bool:
    return bool(getattr(_st(), "studio_on", True)) and shutil.which("ffmpeg") is not None


def _safe(tenant: str) -> str:
    return re.sub(r"[^\w-]", "_", tenant)[:64] or "default"


def home(tenant: str) -> Path:
    p = Path("data") / "studio" / _safe(tenant)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _configure(st: Studio, tenant: str) -> Studio:
    s = _st()
    pv = st.providers
    pv["openrouter"].key = s.openrouter_api_key or ""
    pv["fal"].key = s.fal_key or ""
    pv["byteplus"].key = s.ark_api_key or ""
    pv["google"].key = s.gemini_api_key or ""
    pv["sync"].key = s.sync_api_key or ""
    if s.studio_sync_url:
        pv["sync"].base = s.studio_sync_url.rstrip("/")
    st.speak = _speaker(tenant, st)
    st.painter = _painter if s.gemini_api_key else None
    if s.studio_openrouter_url:
        pv["openrouter"].base = s.studio_openrouter_url.rstrip("/")
        pv["openrouter"].site = re.match(r"^(https?://[^/]+)", pv["openrouter"].base).group(1)
    if s.studio_fal_url:
        pv["fal"].base = s.studio_fal_url.rstrip("/")
    if s.studio_ark_url:
        pv["byteplus"].base = s.studio_ark_url.rstrip("/")
    if s.studio_gemini_url:
        pv["google"].base = s.studio_gemini_url.rstrip("/")
    pv["openrouter"].image_mode = s.studio_image_mode or "data"
    if (s.studio_image_mode or "") == "public" and s.public_base_url:
        st.public_url = s.public_base_url.rstrip("/") + "/api/studio/media/" + _safe(tenant)
        pv["openrouter"].public_image = st.sign_media
    st.poll_s = float(s.studio_poll_s or 5)
    st.sem = asyncio.Semaphore(max(1, int(s.studio_concurrency or 3)))
    return st


async def studio(tenant: str) -> Studio:
    loop = asyncio.get_running_loop()
    have = _studios.get(tenant)
    if have and have[0] is loop:
        return have[1]
    st = _configure(Studio(home(tenant)), tenant)
    st.on_change = lambda name, t=tenant: _changed(t, name)
    _studios[tenant] = (loop, st)
    if st.providers["openrouter"].ready():
        try:
            await asyncio.wait_for(st.models_sync(), 20)
        except Exception as e:
            log.info("studio models_sync: %s", e)
    try:
        await st.resume()
    except Exception:
        log.exception("studio resume")
    return st


def studio_sync(tenant: str) -> Studio:
    """For plain reads and the signed links (no jobs started)."""
    have = _studios.get(tenant)
    return have[1] if have else _configure(Studio(home(tenant)), tenant)


# ---------------------------------------------------------------- v0.157 voice, pictures, writer
SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1440, 1440), "4:3": (1440, 1080), "3:4": (1080, 1440),
         "21:9": (2520, 1080)}
FEMALE = re.compile(r"\b(woman|women|girl|lady|female|she|her|aunty|mahila|ladki|didi|maa|mother|wife|bride|dulhan)\b", re.I)


def _voice_name(voice: str, description: str = "") -> str:
    from ..notebook import media
    v = (voice or "").strip()
    if v in media.NARRATORS:
        return media.NARRATORS[v]
    if v[:1].isupper() and v.isalpha():
        return v                                        # a Gemini voice name (Kore, Charon, Puck...)
    return media.NARRATORS["female" if FEMALE.search(description or "") else "male"]


def _speaker(tenant: str, st: Studio):
    """(text, language, voice) -> a WAV of the line in that voice: Gemini 3.8 Flash TTS (older TTS as fallback)."""
    def speak(text: str, language: str, voice: str = "") -> str:
        from ..notebook import media
        name = _voice_name(voice)
        pcm = b""
        if media._new_tts_ok():
            try:
                pcm = media.tts_turns([{"text": text}], voice=name,
                                      style=f"natural, expressive, clear speech in {language}, like a real person in a film")
            except Exception as e:
                media._new_tts_failed(e)
        if not pcm:
            pcm = media.tts_chunk(f"Say this naturally in {language}, like a real person in a film: {media.plain(text)}", voice=name)
        d = st.home / "uploads" / "audio"
        d.mkdir(parents=True, exist_ok=True)
        out = d / f"line_{int(time.time() * 1000)}.wav"
        out.write_bytes(media.wav_bytes(pcm))
        return str(out)
    return speak


def _painter(prompt: str, aspect: str, refs: list[str]) -> bytes:
    """A shot's first frame, painted by Nano Banana Pro (2.1 next) with the character photos as references."""
    from ..notebook import paint
    imgs = [Path(r).read_bytes() for r in refs if Path(r).is_file()]
    raw, _model = paint.paint(prompt, aspect if aspect in SIZES else "16:9", "page", imgs)
    w, h = SIZES.get(aspect, (1920, 1080))
    return paint.finish(raw, w, h, label=False, quality=92)


async def _write(system: str, prompt: str, max_tokens: int = 12000) -> str:
    s = _st()
    if s.anthropic_api_key and s.studio_plan_model:
        try:
            from ..agent.santosh import get_client
            msg = await get_client().messages.create(model=s.studio_plan_model, max_tokens=max_tokens, system=system,
                                                     messages=[{"role": "user", "content": prompt}])
            text = "".join(getattr(b, "text", "") for b in msg.content).strip()
            if text:
                return text
        except Exception as e:
            log.info("studio planner %s failed, chat model instead: %s", s.studio_plan_model, e)
    from ..artifacts import _llm
    return (await _llm(system, prompt, max_tokens)).strip()


# ---------------------------------------------------------------- links, views, events
def _sign(tenant: str, rel: str, exp: int) -> str:
    from ..pc.service import sign
    return sign(f"studio:{tenant}:{rel}", exp)


def link(tenant: str, path: str | Path, days: int = 10) -> str:
    """Signed link to a file in her studio folder (final videos, sheets), for the app's player / download."""
    h = home(tenant).resolve()
    rel = str(Path(path).resolve().relative_to(h))
    exp = int(time.time()) + days * 86400
    b = base64.urlsafe_b64encode(rel.encode()).decode().rstrip("=")
    return f"/api/studio/files/{_safe(tenant)}/{exp}/{_sign(_safe(tenant), rel, exp)}/{b}{Path(rel).suffix}"


def file_for(tenant: str, exp: str, sig: str, name: str) -> Path | None:
    import hmac
    b = name.rsplit(".", 1)[0] if "." in name else name
    try:
        rel = base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode()
    except Exception:
        return None
    if not exp.isdigit() or int(exp) < time.time() or not hmac.compare_digest(_sign(tenant, rel, int(exp)), sig):
        return None
    h = home(tenant).resolve()
    f = (h / rel).resolve()
    return f if h in f.parents and f.is_file() else None


def _inr(usd: float) -> int:
    return int(round(float(usd) * float(_st().studio_usd_inr or 85)))


def month_spent(tenant: str) -> float:
    st = studio_sync(tenant)
    ym = dt.datetime.now().strftime("%Y-%m")
    total = 0.0
    for d in (st.home / "projects").iterdir():
        f = d / "project.json"
        if f.exists():
            for e in json.loads(f.read_text()).get("ledger", []):
                if str(e.get("at", "")).startswith(ym):
                    total += float(e.get("usd", 0))
    return round(total, 4)


def view(tenant: str, p: dict) -> dict[str, Any]:
    st = studio_sync(tenant)
    jobs = p.get("jobs", {})
    shots = []
    for s in p.get("shots", []):
        vs = p.get("variants", {}).get(s["id"], [])
        mine = [j for j in jobs.values() if j["shot"] == s["id"]]
        live = [j for j in mine if j["state"] in ("queued", "submitted", "running", "retrying")]
        last = mine[-1] if mine else None
        kf = s.get("keyframe")
        takes = []
        for v in vs[-6:]:
            f = Path(v["file"])
            if f.is_file():
                takes.append({"n": v["n"], "quality": v["quality"], "model": v.get("model"), "url": link(tenant, f, 3),
                              "seconds": v.get("duration"), "score": (v.get("look") or {}).get("score"),
                              "problems": (v.get("look") or {}).get("problems") or [], "lipsync": v.get("lipsync"),
                              "lipsync_error": v.get("lipsync_error")})
        shots.append({"id": s["id"], "prompt": s["prompt"][:400], "duration": s["duration"], "caption": s.get("caption") or "",
                      "kind": s.get("kind") or "scene", "dialogue": s.get("dialogue") or "", "voiceover": s.get("voiceover") or "",
                      "camera": s.get("camera") or "", "characters": s.get("characters") or [],
                      "keyframe": link(tenant, kf, 3) if kf and Path(kf).is_file() else "",
                      "takes": len(vs), "take_list": takes, "picked": p.get("picked", {}).get(s["id"]),
                      "quality": next((v["quality"] for v in vs if v["n"] == p.get("picked", {}).get(s["id"])), None),
                      "state": "working" if live else (last["state"] if last else "new"),
                      "stage": (live[-1].get("stage") if live else None),
                      "error": (last or {}).get("error") if last and last["state"] == "failed" else None})
    outs = []
    for o in p.get("outputs", [])[-3:]:
        f = Path(o["file"])
        if f.is_file():
            thumb = f.with_suffix(".jpg")
            outs.append({"url": link(tenant, f), "seconds": o.get("seconds"), "takes": o.get("takes"), "at": o.get("at"),
                         "file_id": o.get("file_id"), "thumb": link(tenant, thumb) if thumb.is_file() else "",
                         "preview": "preview" in str(o.get("takes", ""))})
    pend = [a for a in p.get("approvals", {}).values() if a.get("status") == "pending"]
    est = {}
    if p.get("shots"):
        for q in ("draft", "final", "premium"):
            try:
                e = st.estimate(p["name"], q)
                est[q] = {"usd": e["usd"], "inr": _inr(e["usd"]), "models": sorted({r["model"] for r in e["shots"]})}
            except Exception:
                pass
    return {"project": p["name"], "aspect": p["aspect"], "style": p["style"], "language": p["language"], "brief": p.get("brief", ""),
            "budget_usd": p["budget_usd"], "spent_usd": round(p["spent_usd"], 3), "spent_inr": _inr(p["spent_usd"]),
            "characters": list(p.get("characters", {})), "shots": shots, "outputs": outs,
            "working": any(x["state"] == "working" for x in shots) or p["name"] in _assembling,
            "assembling": p["name"] in _assembling, "approvals": pend, "updated": p.get("updated"),
            "estimates": est, "planning": p["name"] in _planning, "seconds": sum(int(x["duration"]) for x in p.get("shots", [])),
            "keyframes": sum(1 for x in p.get("shots", []) if x.get("keyframe")),
            "music": bool(p.get("music")), "logo": bool(p.get("logo")),
            "character_list": [{"name": k, "description": v.get("description", ""), "voice": v.get("voice", "")}
                               for k, v in p.get("characters", {}).items()]}


def _conv(tenant: str, p: dict) -> str:
    if p.get("conversation"):
        return p["conversation"]
    try:
        from ..net.service import home_conv
        return home_conv(tenant)
    except Exception:
        return ""


def _publish(tenant: str, p: dict, kind: str = "studio", payload: dict | None = None) -> None:
    from ..events import bus
    try:
        bus.publish(_conv(tenant, p), kind, payload if payload is not None else view(tenant, p))
    except Exception:
        pass


def _note(tenant: str, p: dict, text: str) -> None:
    from ..events import notify
    try:
        notify(_conv(tenant, p), text)
    except Exception:
        pass


def _changed(tenant: str, name: str) -> None:
    try:
        _publish(tenant, studio_sync(tenant).load(name))
    except Exception:
        pass


def _load(tenant: str, project: str) -> dict:
    try:
        return studio_sync(tenant).load(project)
    except StudioError as e:
        raise StudioJobError(str(e)) from None


def latest(tenant: str) -> str:
    st = studio_sync(tenant)
    best = ("", "")
    for d in (st.home / "projects").iterdir():
        f = d / "project.json"
        if f.exists():
            p = json.loads(f.read_text())
            if (p.get("updated") or "") > best[1]:
                best = (p["name"], p.get("updated") or "")
    return best[0]


def listing(tenant: str) -> list[dict[str, Any]]:
    return sorted(studio_sync(tenant).list_projects(), key=lambda x: x.get("updated") or "", reverse=True)


# ---------------------------------------------------------------- her files -> her studio folder
def _her_file(tenant: str, st: Studio, file_id: str, sub: str, kinds: tuple[str, ...]) -> Path:
    from ..mailbox.service import MailError, _file_row
    try:
        f = _file_row(tenant, file_id)
    except MailError as e:
        raise StudioJobError(str(e)) from None
    src = Path(f.stored_path or "")
    if not src.is_file():
        raise StudioJobError("Yeh file ab server par nahi hai; dobara bhejiye.")
    ext = Path(f.name or "").suffix.lower()
    ok = {"image": (".jpg", ".jpeg", ".png", ".webp"), "audio": (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".mp4"),
          "video": (".mp4", ".mov", ".m4v", ".webm")}
    if not any(ext in ok[k] for k in kinds):
        raise StudioJobError(f"'{f.name}' yahan nahi chalegi ({'/'.join(kinds)} chahiye).")
    d = st.home / "uploads" / sub
    d.mkdir(parents=True, exist_ok=True)
    dst = d / f"{file_id}{ext}"
    shutil.copyfile(src, dst)
    return dst


# ---------------------------------------------------------------- actions
async def create(tenant: str, name: str, aspect: str = "9:16", style: str = "reel", language: str = "Hindi",
                 brief: str = "", conversation_id: str = "") -> dict[str, Any]:
    name = re.sub(r"\s+", " ", name or "").strip()[:60]
    if len(name) < 2:
        raise StudioJobError("Project ka naam chahiye")
    st = await studio(tenant)
    try:
        st.create(name, aspect or "9:16", style or "reel", language or "Hindi", float(_st().studio_project_usd or 5), None, brief[:2000])
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    p = await st.update(name, lambda q: q.update(conversation=conversation_id, approvals={}))
    _publish(tenant, p)
    return view(tenant, p)


async def character(tenant: str, project: str, name: str, description: str, file_ids: list[str], consent: bool,
                    voice: str = "") -> dict:
    if not file_ids:
        raise StudioJobError("Photo ka file_id chahiye (chat mein photo bhejiye), ya character_generate.")
    if not consent:
        raise StudioJobError("Asli insaan ki photo se video tabhi banega jab unki ijazat ho. Owner se poochiye; "
                             "haan ho to consent=true. (Product / logo / mascot ki photo ho to bhi consent=true.)")
    st = await studio(tenant)
    paths = [str(_her_file(tenant, st, f, "characters", ("image",))) for f in file_ids[:4]]
    try:
        r = st.character_add(project, name[:40], description[:400], paths)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    await st.update(project, lambda q: q["characters"][name[:40]].update(
        consent=True, consent_at=dt.datetime.now().isoformat(), voice=_voice_name(voice, description)))
    _changed(tenant, project)
    return r


async def storyboard(tenant: str, project: str, shots: list[dict]) -> dict:
    st = await studio(tenant)
    clean = []
    for s in shots or []:
        s = dict(s)
        for k in ("start_image", "end_image"):
            fid = s.pop(k + "_file_id", None)
            s.pop(k, None)                    # paths only from her own files
            if fid:
                s[k] = str(_her_file(tenant, st, fid, "frames", ("image",)))
        clean.append(s)
    try:
        r = st.storyboard_set(project, clean)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    _changed(tenant, project)
    r["estimate"]["inr"] = _inr(r["estimate"]["usd"])
    return r


async def generate(tenant: str, project: str, quality: str = "preview", shot_ids: list[str] | None = None,
                   variants: int = 1, model: str | None = None, conversation_id: str = "") -> dict:
    """Preview = free, runs now. Draft / final = a card for her tap; nothing paid runs before it."""
    st = await studio(tenant)
    if quality not in catalog.QUALITY:
        raise StudioJobError(f"quality = {list(catalog.QUALITY)}")
    try:
        est = st.estimate(project, quality, shot_ids, max(1, min(int(variants or 1), 4)), model)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    p = st.load(project)
    rows = {r["shot"]: r for r in est["shots"]}
    paint_ids = []
    if st.painter and quality != "preview":
        paint_ids = [x["id"] for x in p["shots"] if x["id"] in rows and not x.get("keyframe") and not x.get("start_image")
                     and (quality in ("final", "premium") or (x.get("kind") or "scene") == "talk")]
    usd = round(est["usd"] + KEYFRAME_USD * len(paint_ids), 4)
    if usd <= 0:
        return await _run_generate(tenant, st, project, quality, shot_ids, variants, model, None)
    return await _ask(tenant, st, project, {"kind": "generate", "quality": quality, "shot_ids": shot_ids or [],
                                            "variants": max(1, min(int(variants or 1), 4)), "model": model,
                                            "usd": usd, "shots": len(est["shots"]), "keyframes": len(paint_ids),
                                            "paint_ids": paint_ids,
                                            "lipsync": sum(1 for r in est["shots"] if r.get("lipsync")),
                                            "seconds": sum(r["seconds"] for r in est["shots"]),
                                            "models": sorted({r["model"] for r in est["shots"]})})


async def keyframes(tenant: str, project: str, shot_ids: list[str] | None = None) -> dict:
    """v0.157 Paint each shot's opening picture (Nano Banana Pro): a card first (about Rs 12 a picture)."""
    st = await studio(tenant)
    if not st.painter:
        raise StudioJobError("Tasveer ke liye server par GEMINI_API_KEY chahiye.")
    p = _load(tenant, project)
    ids = [x["id"] for x in p["shots"] if not shot_ids or x["id"] in shot_ids]
    if not ids:
        raise StudioJobError("Pehle storyboard banaiye (plan).")
    return await _ask(tenant, st, project, {"kind": "keyframes", "shot_ids": ids, "usd": round(KEYFRAME_USD * len(ids), 4),
                                            "shots": len(ids), "seconds": 0, "models": ["nano-banana-pro"]})


async def character_generate(tenant: str, project: str, name: str, description: str) -> dict:
    st = await studio(tenant)
    if not st.providers["fal"].ready():
        r = await st.character_generate(project, name[:40], description[:400], "offline-image")
        _changed(tenant, project)
        return {**r, "note": "FAL_KEY nahi hai: abhi ek saada placeholder bana. Asli tasveer ke liye server par FAL_KEY lagaiye."}
    usd = catalog.IMAGE_MODELS["flux-dev"]["usd_per_image"]
    return await _ask(tenant, st, project, {"kind": "character", "name": name[:40], "description": description[:400], "usd": usd,
                                            "shots": 0, "seconds": 0, "models": ["flux-dev"]})


async def _ask(tenant: str, st: Studio, project: str, req: dict) -> dict:
    s = _st()
    left = float(s.studio_month_usd or 0) - month_spent(tenant)
    if req["usd"] > left + 1e-9:
        raise StudioJobError(f"Is mahine AI video ki seema ${s.studio_month_usd:.2f} (~₹{_inr(s.studio_month_usd)}) hai; "
                             f"sirf ${max(0, left):.2f} bacha hai aur yeh ${req['usd']:.2f} ka hai. Preview free hai; ya "
                             "server par STUDIO_MONTH_USD badhaiye.")
    aid = "sa" + base64.b32encode(bytes.fromhex(f"{int(time.time() * 1000) % 16**10:010x}")).decode().lower().rstrip("=")[:10]
    req = {**req, "id": aid, "project": project, "status": "pending", "inr": _inr(req["usd"]),
           "month_left_usd": round(left, 2), "created": dt.datetime.now().isoformat(timespec="seconds")}
    p = await st.update(project, lambda q: q.setdefault("approvals", {}).__setitem__(aid, req))
    _publish(tenant, p, "studio_approval", req)
    _publish(tenant, p)
    what = _what(req)
    return {"waiting_owner": aid, "usd": req["usd"], "inr": req["inr"],
            "say": f"{what} banane mein lagbhag ₹{req['inr']} (${req['usd']:.2f}) lagenge. Card par Haan dabayengi tabhi banega.",
            "note_for_you": "Nothing is spent until she taps Haan on the card. Don't call generate again for this."}


async def decide(tenant: str, approval_id: str, yes: bool) -> dict:
    """Her tap on the price card."""
    st = await studio(tenant)
    project = next((p["project"] for p in listing(tenant) if aid_in(st, p["project"], approval_id)), "")
    if not project:
        raise StudioJobError("Yeh card purana ho gaya")
    p = st.load(project)
    a = p["approvals"][approval_id]
    if a["status"] != "pending":
        return a
    if not yes:
        p = await st.update(project, lambda q: q["approvals"][approval_id].update(status="rejected"))
        _publish(tenant, p, "studio_approval", p["approvals"][approval_id])
        _publish(tenant, p)
        return p["approvals"][approval_id]
    left = float(_st().studio_month_usd or 0) - month_spent(tenant)
    if a["usd"] > left + 1e-9:
        raise StudioJobError(f"Is mahine ki seema poori ho gayi (${max(0, left):.2f} bacha).")
    need = p["spent_usd"] + st._reserved(p) + a["usd"]

    def ok(q):
        q["approvals"][approval_id].update(status="approved", approved_at=dt.datetime.now().isoformat(timespec="seconds"))
        q["budget_usd"] = max(q["budget_usd"], round(need + 1e-6, 4))     # her tap is the budget for this run
    p = await st.update(project, ok)
    _publish(tenant, p, "studio_approval", p["approvals"][approval_id])
    try:
        if a["kind"] == "character":
            r = await st.character_generate(project, a["name"], a["description"], "flux-dev")
            _changed(tenant, project)
            _note(tenant, p, f"Character '{a['name']}' ki photo ban gayi.")
            return {**p["approvals"][approval_id], "result": r}
        if a["kind"] == "keyframes":
            _bg(tenant, project, _do_keyframes(tenant, st, project, a["shot_ids"]))
            return st.load(project)["approvals"][approval_id]
        if a["kind"] == "music":
            _bg(tenant, project, _do_music(tenant, st, project, a.get("mood") or "upbeat", float(a.get("seconds") or 60),
                                           float(a.get("volume") or 0.25)))
            return st.load(project)["approvals"][approval_id]
        if a.get("paint_ids"):
            _bg(tenant, project, _paint_then_generate(tenant, st, project, a))
            return st.load(project)["approvals"][approval_id]
        await _run_generate(tenant, st, project, a["quality"], a["shot_ids"] or None, a["variants"], a.get("model"),
                            a["usd"] + 1e-6)
    except (StudioError, StudioJobError) as e:
        p = await st.update(project, lambda q: q["approvals"][approval_id].update(status="failed", error=str(e)[:300]))
        _publish(tenant, p)
        raise StudioJobError(str(e)) from None
    return st.load(project)["approvals"][approval_id]


def _what(a: dict) -> str:
    k = a.get("kind")
    if k == "generate":
        extra = (f" + {a['keyframes']} tasveerein" if a.get("keyframes") else "") + (f", {a['lipsync']} lip sync" if a.get("lipsync") else "")
        return f"{a.get('shots', 0)} shot{'s' if a.get('shots') != 1 else ''} ({a.get('seconds', 0)} s, {a.get('quality', '')}{extra})"
    if k == "keyframes":
        return f"{a.get('shots', 0)} shots ki pehli tasveer (Nano Banana Pro)"
    if k == "music":
        return f"music ({a.get('mood', '')}, Lyria)"
    return f"character photo '{a.get('name')}'"


def aid_in(st: Studio, project: str, aid: str) -> bool:
    try:
        return aid in st.load(project).get("approvals", {})
    except StudioError:
        return False


_bg_tasks: set[asyncio.Task] = set()


def _bg(tenant: str, project: str, coro) -> None:
    t = asyncio.ensure_future(coro)
    _bg_tasks.add(t)
    t.add_done_callback(_bg_tasks.discard)


async def _do_keyframes(tenant: str, st: Studio, project: str, ids: list[str]) -> dict:
    try:
        r = await st.keyframes(project, ids, KEYFRAME_USD)
    except Exception as e:
        log.exception("studio keyframes")
        _note(tenant, st.load(project), f"Video studio '{project}': tasveerein nahi ban payin: {str(e)[:160]}")
        return {}
    p = st.load(project)
    _publish(tenant, p)
    _note(tenant, p, f"Video studio '{project}': {len(r['painted'])} shots ki pehli tasveer taiyaar"
          + (f" ({len(r['failed'])} nahi bani)" if r["failed"] else "") + ". Free preview ('generate preview') ab inhi se banega.")
    return r


async def _paint_then_generate(tenant: str, st: Studio, project: str, a: dict) -> None:
    await _do_keyframes(tenant, st, project, a["paint_ids"])
    p = st.load(project)
    spent_on_pictures = KEYFRAME_USD * len(a["paint_ids"])
    try:
        await _run_generate(tenant, st, project, a["quality"], a["shot_ids"] or None, a["variants"], a.get("model"),
                            max(0.0, a["usd"] - spent_on_pictures) + 1e-6)
    except Exception as e:
        _note(tenant, p, f"Video studio '{project}': shots shuru nahi hue: {str(e)[:200]}")


async def _run_generate(tenant: str, st: Studio, project: str, quality: str, shot_ids, variants, model, max_cost) -> dict:
    try:
        r = await st.generate(project, quality, shot_ids or None, variants, model, max_cost, 0)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    _changed(tenant, project)
    key = f"{tenant}:{slug(project)}"
    old = _watchers.get(key)
    if old and not old.done():
        old.cancel()
    _watchers[key] = asyncio.ensure_future(_watch(tenant, st, project, quality, r["jobs"]))
    return {"started": r["started"], "quality": quality, "usd": r["estimate_usd"], "inr": _inr(r["estimate_usd"]),
            "say": ("Free preview ban raha hai (kahani aur timing dekhne ke liye)." if quality == "preview"
                    else "Shots ban rahe hain; har shot 1-5 minute. Card par dikhega."),
            "note_for_you": "Do not poll: a note arrives when the shots are done."}


async def _watch(tenant: str, st: Studio, project: str, quality: str, jobs: list[str]) -> None:
    t0 = time.time()
    while time.time() - t0 < 3 * 3600:
        p = st.load(project)
        js = [p["jobs"][j] for j in jobs if j in p["jobs"]]
        if js and all(j["state"] in ("done", "failed") for j in js):
            done = sum(1 for j in js if j["state"] == "done")
            if quality != "preview":
                await _auto_review(tenant, st, project, [j for j in js if j["state"] == "done"])
                p = st.load(project)
            bad = [f"{j['shot']}: {str(j.get('error'))[:120]}" for j in js if j["state"] == "failed"]
            _publish(tenant, p)
            msg = (f"Video studio '{project}': {done} {quality} shot taiyaar"
                   + (f", {len(bad)} nahi bane ({'; '.join(bad[:3])})" if bad else "") + ". ")
            weak = [f"{sid} ({v.get('look', {}).get('score')}/10)" for sid, vs in p.get("variants", {}).items() for v in vs
                    if v.get("job") in jobs and (v.get("look") or {}).get("score") is not None and v["look"]["score"] < 6]
            if weak:
                msg += f"In shots ko dobara banana theek rahega: {', '.join(weak[:6])}. "
            msg += ("Preview jodkar dekhna ho to 'assemble' bolo." if quality == "preview"
                    else f"Ab tak kharch ${p['spent_usd']:.2f} (~₹{_inr(p['spent_usd'])}). Dekh ke batao, phir final video jod dunga.")
            _note(tenant, p, msg)
            try:
                from ..voice import inject
                inject(_conv(tenant, p), f"(Video studio: {msg} Tell her in one short line.)")
            except Exception:
                pass
            return
        await asyncio.sleep(1.0)


async def _auto_review(tenant: str, st: Studio, project: str, jobs: list[dict]) -> None:
    """v0.157 Every paid take is looked at (6 frames, a vision model): score + problems saved on the take; low scores
    are named in the note so she can redo just those shots (nothing is regenerated by itself)."""
    for j in jobs[:20]:
        try:
            p = st.load(project)
            v = next((x for x in p["variants"].get(j["shot"], []) if x.get("job") and x["file"] == j.get("file")), None)
            if not v or v.get("look"):
                continue
            r = await review(tenant, project, j["shot"], v["n"])
            look = r.get("look") or {}
            if look.get("score") is not None:
                await st.update(project, lambda q, sid=j["shot"], n=v["n"], lk=look: next(
                    x for x in q["variants"][sid] if x["n"] == n).update(look={k: lk.get(k) for k in ("score", "problems", "fix", "matches")}))
        except Exception as e:
            log.info("studio auto review %s: %s", j.get("shot"), e)


async def review(tenant: str, project: str, shot_id: str, take: int | None = None) -> dict:
    st = await studio(tenant)
    try:
        r = await asyncio.to_thread(st.review, project, shot_id, take)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    sheet = Path(r.pop("sheet"))
    p = st.load(project)
    shot = next(s for s in p["shots"] if s["id"] == shot_id)
    look = {}
    try:
        from ..videoedit import brain
        look = await asyncio.to_thread(
            brain.look, sheet.read_bytes(), "You are a picky film director checking one generated shot (6 frames in time order).",
            f"The shot should show: {shot['prompt']}. Return JSON {{\"matches\": true/false, \"score\": 1-10, "
            "\"problems\": [short], \"fix\": \"a better prompt sentence if needed\"}. Look for wrong faces, extra fingers, "
            "melting objects, text gibberish, wrong place.")
    except Exception as e:
        log.info("studio review look: %s", e)
    r["look"] = look or {"note": "no vision model; she can see the sheet"}
    r["sheet_url"] = link(tenant, sheet, 2)
    return r


async def voiceover(tenant: str, project: str, shot_id: str, text: str = "", file_id: str = "") -> dict:
    st = await studio(tenant)
    if file_id:
        src = _her_file(tenant, st, file_id, "audio", ("audio",))
    elif text.strip():
        if not _st().gemini_api_key:
            raise StudioJobError("Awaaz ke liye GEMINI_API_KEY chahiye; ya apni recording ka file_id dijiye.")
        from ..avatar import service as av
        a = av.get(tenant)
        voice = "female" if (a.get("gender") or "m") == "f" else "male"
        try:
            src = Path(await asyncio.to_thread(st.speak, text.strip()[:600], st.load(project)["language"], voice))
        except Exception as e:
            raise StudioJobError(f"Awaaz nahi ban payi: {str(e)[:150]}") from None
    else:
        raise StudioJobError("text (meri awaaz mein bolunga) ya audio file_id chahiye")
    try:
        r = st.voiceover_set(project, shot_id, str(src), text or None)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    _changed(tenant, project)
    return r


def _tts(tenant: str, st: Studio, text: str, language: str) -> Path:
    """Narration in the avatar's own call voice (Gemini TTS, 24 kHz mono)."""
    s = _st()
    if not s.gemini_api_key:
        raise StudioJobError("Awaaz ke liye GEMINI_API_KEY chahiye; ya apni recording ka file_id dijiye.")
    from google.genai import Client, types
    from ..avatar import service as av
    a = av.get(tenant)
    gender = a.get("gender") or "m"
    voice = a.get("voice") or (s.voice_default if gender == "m" else av.DEFAULT_VOICE["f"])
    cfg = types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))))
    resp = Client(api_key=s.gemini_api_key).models.generate_content(
        model=s.voice_ack_tts_model, config=cfg,
        contents=f"Read this as a warm, clear narrator for a short video, in natural {language}: {text}")
    pcm = next((p.inline_data.data for p in resp.candidates[0].content.parts if getattr(p, "inline_data", None)), b"")
    if not pcm:
        raise StudioJobError("Awaaz nahi ban payi")
    d = st.home / "uploads" / "audio"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"tts_{int(time.time() * 1000)}.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    return out


MOODS = {"upbeat": "bright, energetic modern Indian pop instrumental with tabla, dhol and synths, confident and happy",
         "calm": "calm warm instrumental with soft piano, sitar and strings, gentle and hopeful",
         "festive": "festive Indian celebration instrumental with shehnai, dhol and claps, joyful wedding / Diwali mood",
         "cinematic": "cinematic orchestral instrumental with a slow build, emotional strings and big drums",
         "corporate": "clean modern corporate instrumental, light percussion, optimistic and professional",
         "lofi": "lo-fi chill instrumental, mellow beats, soft keys"}


def lyria_ready() -> bool:
    s = _st()
    return bool(s.gemini_api_key and s.studio_music_model)


async def music(tenant: str, project: str, mood: str = "", file_id: str = "", volume: float = 0.25) -> dict:
    """Her own licensed music file, or (v0.157) a real track made by Google Lyria for this video (a card first),
    or Hoola's own free synthesised bed when Lyria isn't available."""
    st = await studio(tenant)
    p = st.load(project)
    secs = sum(s["duration"] for s in p["shots"]) + 3 or 30
    if not file_id and lyria_ready():
        mood = mood if mood in MOODS else (mood.strip()[:200] or "upbeat")
        return await _ask(tenant, st, project, {"kind": "music", "mood": mood, "usd": MUSIC_USD, "shots": 0,
                                                "seconds": int(secs), "volume": max(0.05, min(float(volume or 0.25), 1.0)),
                                                "models": [_st().studio_music_model]})
    if file_id:
        src = _her_file(tenant, st, file_id, "audio", ("audio",))
    else:
        from ..motion import music as mm
        mood = mood if mood in ("upbeat", "calm", "festive") else "upbeat"
        d = st.home / "uploads" / "audio"
        d.mkdir(parents=True, exist_ok=True)
        src = await asyncio.to_thread(mm.write, mood, float(secs), d / f"bed_{mood}.wav")
        if not src:
            raise StudioJobError("music nahi bana")
    try:
        r = st.music_set(project, str(src), max(0.05, min(float(volume or 0.25), 1.0)))
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    _changed(tenant, project)
    return r


def _lyria(prompt: str) -> bytes:
    import base64 as b64
    from google import genai
    s = _st()
    client = genai.Client(api_key=s.gemini_api_key)
    it = client.interactions.create(model=s.studio_music_model, input=prompt)
    audio = getattr(it, "output_audio", None)
    if not audio or not getattr(audio, "data", None):
        raise StudioJobError("Lyria ne music nahi diya")
    data = audio.data
    return b64.b64decode(data) if isinstance(data, str) else bytes(data)


async def _do_music(tenant: str, st: Studio, project: str, mood: str, seconds: float, volume: float = 0.25) -> None:
    p = st.load(project)
    desc = MOODS.get(mood, mood)
    prompt = (f"Instrumental only, no vocals. {desc}. Background music for a {p['aspect']} video: {p.get('brief') or project}. "
              f"About {int(seconds)} seconds long, with a clear ending; steady energy under narration.")
    try:
        data = await asyncio.to_thread(_lyria, prompt)
        d = st.home / "uploads" / "audio"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"lyria_{int(time.time())}.mp3"
        f.write_bytes(data)
        st.music_set(project, str(f), volume)
        await st.update(project, lambda q: st._charge(q, MUSIC_USD, f"music ({mood})", _st().studio_music_model))
        p = st.load(project)
        _publish(tenant, p)
        _note(tenant, p, f"Video studio '{project}': music taiyaar ({mood}, Google Lyria). Final video jodte waqt lagega.")
    except Exception as e:
        log.exception("studio lyria")
        _note(tenant, p, f"Video studio '{project}': music nahi bana ({str(e)[:150]}). 'music' bina mood ke free bed laga dega.")


# ---------------------------------------------------------------- v0.157 planner
PLAN_SYSTEM = """You are an award-winning Indian ad film director and storyboard artist writing for AI video models
(Wan 3.0, Seedance 2.5, MiniMax H3, Gemini Omni Flash). Output ONLY JSON.
Rules for every shot prompt (English, one paragraph, 35-70 words): SUBJECT (who / what, with concrete look) + ACTION
(one clear action, physically plausible) + SETTING (specific Indian place / home / shop / street when it fits) +
LIGHTING (time of day, light quality) + CAMERA (shot size, lens feel, movement) + MOOD. Describe what is VISIBLE; no
on-screen text, no logos, no brand names, no real famous people, no politicians. Keep characters' looks identical across
shots (repeat their key traits). One idea per shot; vary shot sizes (wide, medium, close-up) for rhythm; start with a
hook in the first 2 seconds; end on a clear payoff / call to action shot.
Shot kinds: scene (people / places / story), product (a product photo comes alive: turntable, hero light, in use),
talk (a person speaks to camera: the prompt describes the setting behind them), dialogue (people speak inside a scene),
link (smooth move from one picture to the next). Durations: scene / product / link 4-8 s (up to 10), talk = length of
the line (Hindi ~2.2 words per second, + 1 s). Spoken lines (dialogue field) are in the project language, natural,
short (max 2 sentences). Captions (caption field) are 2-6 words in the project language, optional.
camera must be one of: CAMERAS. characters only from: CHARACTERS (or none)."""


async def plan(tenant: str, project: str, brief: str = "", seconds: int = 30, conversation_id: str = "") -> dict:
    """v0.157 Claude (Opus) writes the storyboard: shots with kind, prompts tuned for the video models, camera, lines,
    captions; checked by the studio (problems fed back once)."""
    st = await studio(tenant)
    p = _load(tenant, project)
    brief = (brief or p.get("brief") or "").strip()
    if not brief:
        raise StudioJobError("Video kis baare mein hai? (brief)")
    seconds = max(6, min(int(seconds or 30), 600))
    if project in _planning and not _planning[project].done():
        return {"status": "already planning"}
    if brief != p.get("brief"):
        await st.update(project, lambda q: q.update(brief=brief[:2000]))
    _planning[project] = asyncio.ensure_future(_plan(tenant, st, project, brief, seconds))
    _changed(tenant, project)
    return {"status": "planning", "say": "Storyboard likh raha hoon (1-2 minute); card par aa jayega.",
            "note_for_you": "Do not poll; the storyboard arrives as a card + note."}


async def _plan(tenant: str, st: Studio, project: str, brief: str, seconds: int) -> dict | None:
    from ..notebook.service import parse_json
    p = st.load(project)
    chars = {k: v.get("description", "") for k, v in p["characters"].items()}
    system = PLAN_SYSTEM.replace("CAMERAS", ", ".join(catalog.CAMERA)).replace("CHARACTERS", json.dumps(chars, ensure_ascii=False) or "none")
    ask = (f"Project: {project}\nBrief: {brief}\nShape: {p['aspect']}\nLook: {catalog.STYLES.get(p['style'], p['style'])}\n"
           f"Language for spoken lines and captions: {p['language']}\nTarget length: about {seconds} seconds "
           f"(about {max(1, round(seconds / 6))} shots).\nJSON: {{\"title\": \"\", \"shots\": [{{\"id\": \"s1\", \"kind\": "
           f"\"scene\", \"prompt\": \"\", \"duration\": 6, \"camera\": \"dolly_in\", \"characters\": [], "
           f"\"dialogue\": \"\", \"speaker\": \"\", \"caption\": \"\", \"transition\": \"fade\"}}]}}")
    last = ""
    try:
        for attempt in range(2):
            raw = await _write(system, ask + (f"\n\nYour last storyboard had these problems, fix them:\n{last}" if last else ""), 16000)
            js = parse_json(raw)
            shots = []
            for i, x in enumerate(js.get("shots") or [], 1):
                if not isinstance(x, dict):
                    continue
                x = {k: v for k, v in x.items() if v not in (None, "", [])}
                x["id"] = str(x.get("id") or f"s{i}")
                x["characters"] = [c for c in (x.get("characters") or []) if c in p["characters"]]
                if x.get("camera") not in catalog.CAMERA:
                    x.pop("camera", None)
                if x.get("transition") not in ("fade", "dissolve", "wipeleft", "wiperight", "slideleft", "slideright", None):
                    x.pop("transition", None)
                x["duration"] = max(2, min(int(x.get("duration") or 6), 15))
                shots.append(x)
            try:
                r = await storyboard(tenant, project, shots[:80])
                break
            except StudioJobError as e:
                last = str(e)[:1500]
                if attempt:
                    raise
        p = st.load(project)
        _publish(tenant, p)
        _note(tenant, p, f"Video studio '{project}': storyboard taiyaar ({len(p['shots'])} shots, {r['total_seconds']} s). "
              f"HD ka andaaza ~Rs {r['estimate']['inr']}. Pehle tasveerein (keyframes) ya free preview dekh lijiye.")
        return r
    except Exception as e:
        log.exception("studio plan")
        _note(tenant, st.load(project), f"Video studio '{project}': storyboard nahi ban paya: {str(e)[:200]}")
        return None
    finally:
        _planning.pop(project, None)
        _changed(tenant, project)


async def logo(tenant: str, project: str, file_id: str, position: str = "top-right") -> dict:
    st = await studio(tenant)
    src = _her_file(tenant, st, file_id, "logo", ("image",))
    try:
        r = st.logo_set(project, str(src), position if position in ("top-right", "top-left", "bottom-right", "bottom-left") else "top-right")
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    _changed(tenant, project)
    return r


async def assemble(tenant: str, project: str, captions: bool = True, transition: str | None = None) -> dict:
    st = await studio(tenant)
    p = _load(tenant, project)
    missing = [s["id"] for s in p["shots"] if not p["picked"].get(s["id"])]
    if not p["shots"] or missing:
        raise StudioJobError(f"In shots ka koi take nahi hai: {missing or 'storyboard khaali'}. Pehle generate.")
    if project in _assembling and not _assembling[project].done():
        return {"status": "already assembling"}
    _assembling[project] = asyncio.ensure_future(_assemble(tenant, st, project, captions, transition))
    _changed(tenant, project)
    return {"status": "assembling", "say": "Final video jod raha hoon (1-3 minute); card par aa jayega.",
            "note_for_you": "Do not poll; the video arrives as a card + note."}


async def _assemble(tenant: str, st: Studio, project: str, captions: bool, transition: str | None) -> dict | None:
    try:
        r = await asyncio.to_thread(st.assemble, project, None, captions, True, -14.0, transition)
        out = Path(r["file"])
        from ..mailbox.service import store_bytes
        from ..vedit import ops as vops
        thumb = out.with_suffix(".jpg")
        try:
            await asyncio.to_thread(vops.thumbnail, str(out), str(thumb), min(1.0, (r.get("seconds") or 2) / 3), 360)
        except Exception:
            pass
        f = await asyncio.to_thread(store_bytes, tenant, out.name, out.read_bytes(), "to_phone")

        def fn(q):
            q["outputs"][-1]["file_id"] = f.id
        p = await st.update(project, fn)
    except Exception as e:
        log.exception("studio assemble")
        p = st.load(project)
        _note(tenant, p, f"Video studio '{project}': final video nahi jud paya: {str(e)[:200]}")
        return None
    finally:
        _assembling.pop(project, None)
    _publish(tenant, p)
    preview = "preview" in str(r.get("takes_used", ""))
    _note(tenant, p, f"Video studio '{project}': video taiyaar ({r['seconds']:.0f} s, {r['size']})."
          + (" Yeh free preview hai (asli shots nahi). Pasand aaye to draft / final shots banwa lijiye." if preview
             else f" Kul kharch ${p['spent_usd']:.2f} (~₹{_inr(p['spent_usd'])}). 'AI-generated' label laga hai. Post aap khud kijiye."))
    return r


async def spend(tenant: str, project: str) -> dict:
    st = await studio(tenant)
    try:
        r = st.spend(project)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    r["spent_inr"] = _inr(r["spent_usd"])
    r["month_spent_usd"] = month_spent(tenant)
    r["month_limit_usd"] = float(_st().studio_month_usd or 0)
    return r


def models(tenant: str) -> list[dict]:
    st = studio_sync(tenant)
    return [{**m, "inr_per_second": round(m["usd_per_second"] * float(_st().studio_usd_inr or 85), 1)} for m in st.models_info()]


def ready_providers(tenant: str) -> list[str]:
    st = studio_sync(tenant)
    return [n for n, pv in st.providers.items() if n != "offline" and pv.ready()]


async def resume_all() -> int:
    """After a restart: every owner's submitted jobs keep being followed."""
    n = 0
    root = Path("data") / "studio"
    if not root.is_dir():
        return 0
    for d in root.iterdir():
        if d.is_dir() and (d / "projects").is_dir():
            try:
                await studio(d.name)
                n += 1
            except Exception:
                log.exception("studio resume %s", d.name)
    return n


def approval_card(tenant: str, approval_id: str) -> dict | None:
    """v0.97 The pending price card as it is now (for the fingerprint-signed approval); None when gone or decided."""
    st = studio_sync(tenant)
    for p in listing(tenant):
        try:
            a = st.load(p["project"]).get("approvals", {}).get(approval_id)
        except StudioError:
            continue
        if a is not None:
            if a.get("status") != "pending":
                return None
            what = _what(a)
            return {"title": f"Video Studio: {p['project']} - {what}", "inr": f"₹{a.get('inr')}",
                    "usd": f"${float(a.get('usd') or 0):.2f}"}
    return None
