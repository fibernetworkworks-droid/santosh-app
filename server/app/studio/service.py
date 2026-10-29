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
_painting: dict[str, set[str]] = {}         # v0.159 "tenant:project" -> shots whose opening picture is being painted
_reviewing: set[str] = set()                # "tenant:project" while the AI looks at fresh takes
VOICES = ("male", "female")
LOGO_SPOTS = ("top-right", "top", "top-left", "right", "left", "bottom-right", "bottom", "bottom-left", "center")
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
politicians; no explicit, violent or hateful content. Nothing is posted anywhere: she shares the video herself.
In the app she can do all of this herself on the Video Studio screens; you see the same project."""


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
    exp = (int(time.time()) // 86400 + days + 1) * 86400      # whole days: same link all day (phone image cache)
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


def _key(tenant: str, project: str) -> str:
    return f"{tenant}:{slug(project)}"


def _ts(iso: str | None) -> float:
    try:
        return dt.datetime.fromisoformat(str(iso)).timestamp()
    except Exception:
        return 0.0


def _typical_s(seconds: float) -> float:
    """How long a clip usually takes at the providers (1-5 minutes): for the progress bar only."""
    return 70.0 + 14.0 * float(seconds or 5)


DEFAULT_PREFS = {"voice": "", "captions": True, "caption_style": "bold", "music": "", "quality": "final",
                 "model": "", "resolution": ""}       # v0.262 her model / resolution pick ("" = Hoola Auto / by quality)


def prefs_of(p: dict) -> dict:
    return {**DEFAULT_PREFS, **(p.get("prefs") or {})}


def quote(st: Studio, p: dict, quality: str, shot_ids: list[str] | None = None, variants: int = 1,
          model: str | None = None) -> dict:
    """v0.159 The price of one generate run, line by line (video / opening pictures / lip sync / music): the same numbers
    on the app's price sheet and on the card she taps."""
    e = st.estimate(p["name"], quality, shot_ids, variants, model)
    sync_ps = st.models["sync-3"]["usd_per_s"] if "sync-3" in st.models else 0.0
    video = lips = 0.0
    lip_shots, lip_secs = 0, 0
    for r in e["shots"]:
        if st.models[r["model"]]["provider"] == "sync":
            lips += r["usd"]
        elif r.get("lipsync"):
            part = r["seconds"] * sync_ps * variants
            lips += part
            video += r["usd"] - part
        else:
            video += r["usd"]
        if r.get("lipsync"):
            lip_shots += 1
            lip_secs += r["seconds"]
    rows = {r["shot"] for r in e["shots"]}
    paint = []
    if st.painter and quality != "preview":
        paint = [x["id"] for x in p["shots"] if x["id"] in rows and not x.get("keyframe") and not x.get("start_image")
                 and (quality in ("final", "premium") or (x.get("kind") or "scene") == "talk")]
    pr = prefs_of(p)
    mood = pr["music"] if quality != "preview" and not shot_ids and pr["music"] and not p.get("music") and lyria_ready() else ""
    pic = KEYFRAME_USD * len(paint)
    mus = MUSIC_USD if mood else 0.0
    total = round(e["usd"] + pic + mus, 4)
    k = float(_st().studio_usd_inr or 85)
    rows_out = [{"shot": r["shot"], "model": r["model"], "name": _label(st, r["model"]), "seconds": r["seconds"],
                 "resolution": r["resolution"], "audio": r.get("audio", True), "takes": r.get("variants", variants),
                 "lipsync": bool(r.get("lipsync")), "inr_per_s": round(catalog.rate(st.models[r["model"]], r["resolution"],
                                                                                  r.get("audio", True)) * k, 2),
                 "inr": round(r["usd"] * k, 1)} for r in e["shots"]]
    return {"quality": quality, "usd": total, "inr": _inr(total), "cap_usd": round(e["usd"], 4), "rows": rows_out,
            "video_usd": round(video, 4), "video_inr": _inr(video), "lipsync_usd": round(lips, 4), "lipsync_inr": _inr(lips),
            "lipsync_shots": lip_shots, "lipsync_seconds": lip_secs, "keyframes": len(paint), "paint_ids": paint,
            "keyframes_inr": _inr(pic), "music": mood, "music_inr": _inr(mus), "shots": len(e["shots"]),
            "seconds": sum(r["seconds"] for r in e["shots"]), "models": sorted({r["model"] for r in e["shots"]}),
            "lipsync": sum(1 for r in e["shots"] if r.get("lipsync"))}


def _label(st: Studio, m: str | None) -> str:
    if not m:
        return ""
    return LABELS.get(m) or str((st.models.get(m) or {}).get("label") or m).replace(" via OpenRouter", "")


LABELS = {"or-wan-3": "Wan 3.0", "or-seedance-2.5": "Seedance 2.5", "or-minimax-h3": "MiniMax H3", "or-minimax-h3-max":
          "MiniMax H3 Max", "gemini-omni-flash": "Gemini Omni Flash", "sync-3": "Sync 3 lip sync", "or-seedance-2-fast":
          "Seedance 2 Fast", "or-seedance-2": "Seedance 2.0", "or-flux-3-video": "FLUX 3 Video", "offline-preview": "Free preview",
          "nano-banana-pro": "Nano Banana Pro", "lyria-3.5": "Google Lyria", **{k: v["name"] for k, v in catalog.CARDS.items()}}


def view(tenant: str, p: dict) -> dict[str, Any]:
    st = studio_sync(tenant)
    key = _key(tenant, p["name"])
    painting = _painting.get(key, set())
    jobs = p.get("jobs", {})
    pr = prefs_of(p)
    want = pr["quality"] if pr["quality"] in ("draft", "final", "premium") else "final"
    t_now = time.time()
    shots = []
    for s in p.get("shots", []):
        vs = p.get("variants", {}).get(s["id"], [])
        mine = [j for j in jobs.values() if j["shot"] == s["id"]]
        live = [j for j in mine if j["state"] in ("queued", "submitted", "running", "retrying")]
        last = mine[-1] if mine else None
        kf = s.get("keyframe")
        picked = p.get("picked", {}).get(s["id"])
        takes = []
        for v in vs[-6:]:
            f = Path(v["file"])
            if f.is_file():
                takes.append({"n": v["n"], "quality": v["quality"], "model": v.get("model"), "model_label": _label(st, v.get("model")),
                              "url": link(tenant, f, 3), "seconds": v.get("duration"), "score": (v.get("look") or {}).get("score"),
                              "problems": (v.get("look") or {}).get("problems") or [], "good": (v.get("look") or {}).get("good") or [],
                              "fix": (v.get("look") or {}).get("fix") or "", "lipsync": v.get("lipsync"),
                              "lipsync_error": v.get("lipsync_error"), "cost_inr": _inr(v.get("cost_usd") or 0),
                              "picked": v["n"] == picked})
        phase, pct = "new", None
        lj = live[-1] if live else None
        if s["id"] in painting:
            phase = "paint"
        elif lj:
            if lj.get("stage") == "lip sync":
                phase = "lipsync"
            elif lj["state"] == "retrying":
                phase = "retrying"
            elif lj["state"] == "queued":
                phase = "queued"
            else:
                phase = "video"
                started = _ts(lj.get("submitted") or lj.get("created"))
                if started:
                    pct = max(3, min(95, int((t_now - started) / _typical_s(lj.get("duration")) * 100)))
        elif last and last["state"] in ("failed", "cancelled") and not picked:
            phase = last["state"]
        elif picked:
            phase = "done"
        elif kf:
            phase = "pictured"
        try:
            m = st.model_for(s, want, None, st.pref_model(p))
        except Exception:
            m = None
        text, _v, _l, line = st.speech_plan(p, s)
        vo = (p.get("voiceovers") or {}).get(s["id"])
        pv = next((v for v in vs if v["n"] == picked), None)
        shots.append({"id": s["id"], "prompt": s["prompt"][:1500], "duration": s["duration"], "caption": s.get("caption") or "",
                      "kind": s.get("kind") or "scene", "dialogue": s.get("dialogue") or "", "voiceover": s.get("voiceover") or "",
                      "camera": s.get("camera") or "", "characters": s.get("characters") or [], "speaker": s.get("speaker") or "",
                      "transition": s.get("transition") or "",
                      "keyframe": link(tenant, kf, 3) if kf and Path(kf).is_file() else "",
                      "takes": len(vs), "take_list": takes, "picked": picked,
                      "quality": pv["quality"] if pv else None, "score": ((pv or {}).get("look") or {}).get("score"),
                      "state": "working" if live else (last["state"] if last else "new"),
                      "stage": (live[-1].get("stage") if live else None), "phase": phase, "pct": pct,
                      "model": m, "model_label": _label(st, m), "lipsync": st.needs_lipsync(p, s, want),
                      "line_url": link(tenant, line, 3) if text and line.is_file() else "",
                      "vo_url": link(tenant, vo["file"], 3) if vo and Path(vo["file"]).is_file() else "",
                      "vo_text": (vo or {}).get("text") or "",
                      "error": (last or {}).get("error") if last and last["state"] == "failed" else None})
    outs = []
    for o in p.get("outputs", [])[-3:]:
        f = Path(o["file"])
        if f.is_file():
            thumb = f.with_suffix(".jpg")
            outs.append({"url": link(tenant, f), "seconds": o.get("seconds"), "takes": o.get("takes"), "at": o.get("at"),
                         "file_id": o.get("file_id"), "thumb": link(tenant, thumb) if thumb.is_file() else "",
                         "preview": "preview" in str(o.get("takes", "")), "mb": round(f.stat().st_size / 1e6, 1),
                         "name": f.name})
    pend = [a for a in p.get("approvals", {}).values() if a.get("status") == "pending"]
    est = {}
    if p.get("shots"):
        for q in ("draft", "final", "premium"):
            try:
                est[q] = {k: v for k, v in quote(st, p, q).items() if k != "paint_ids"}
            except Exception:
                pass
    # the batch running now (or last): progress for the live screen
    batch = p.get("batch") or {}
    bj = [jobs[j] for j in batch.get("jobs", []) if j in jobs]
    prog = None
    if bj:
        cnt = {k: sum(1 for j in bj if j["state"] == k) for k in ("done", "failed", "cancelled")}
        live_j = [j for j in bj if j["state"] in ("queued", "submitted", "running", "retrying")]
        part = 0.0
        eta = 0.0
        for j in live_j:
            started = _ts(j.get("submitted") or j.get("created"))
            typ = _typical_s(j.get("duration"))
            el = max(0.0, t_now - started) if started and j["state"] != "queued" else 0.0
            part += min(0.95, el / typ) if j.get("stage") != "lip sync" else 0.85
            eta += max(20.0, typ - el)
        conc = max(1, int(_st().studio_concurrency or 3))
        done_all = cnt["done"] + cnt["failed"] + cnt["cancelled"]
        spent = sum(float(v.get("cost_usd") or 0) for vs in p.get("variants", {}).values() for v in vs
                    if v.get("job") in batch.get("jobs", []))
        prog = {"quality": batch.get("quality"), "total": len(bj), **cnt, "live": len(live_j),
                "pct": int(round((done_all + part) / len(bj) * 100)), "eta_s": int(eta / conc) if live_j else 0,
                "inr": batch.get("inr") or _inr(batch.get("usd") or 0), "spent_inr": _inr(spent), "at": batch.get("at")}
    working = any(x["state"] == "working" for x in shots)
    assembling = p["name"] in _assembling
    planning = p["name"] in _planning
    step = (0 if painting else 1 if any(x["phase"] in ("video", "queued", "retrying") for x in shots)
            else 2 if any(x["phase"] == "lipsync" for x in shots) else 3 if key in _reviewing else 4 if assembling else 5)
    phase = ("planning" if planning and not shots else "painting" if painting else "working" if working
             else "reviewing" if key in _reviewing else "assembling" if assembling
             else "ready" if outs and not outs[-1]["preview"] else "empty" if not shots else "storyboard")
    nxt: dict[str, Any] = {"kind": "plan", "label": "Storyboard banao", "inr": 0}
    if planning:
        nxt = {"kind": "wait", "label": "Storyboard likh raha hoon", "inr": 0}
    elif shots:
        nokf = [x for x in p["shots"] if not x.get("keyframe") and not x.get("start_image")]
        unpicked = [x for x in shots if not x["picked"]]
        last_out = _ts(outs[-1]["at"]) if outs else 0
        newer = any(_ts(v.get("created")) > last_out for vs in p.get("variants", {}).values() for v in vs) if outs else True
        if working or painting:
            nxt = {"kind": "wait", "label": "Ban raha hai", "inr": 0}
        elif nokf and st.painter:
            nxt = {"kind": "keyframes", "label": "Pehli tasveerein", "inr": _inr(KEYFRAME_USD * len(nokf))}
        elif unpicked or all(x["quality"] == "preview" for x in shots):
            nxt = {"kind": "generate", "label": "Video banao", "inr": (est.get(want) or {}).get("inr", 0)}
        elif newer or not outs:
            nxt = {"kind": "assemble", "label": "Final video jodo", "inr": 0}
        else:
            nxt = {"kind": "done", "label": "Taiyaar", "inr": 0}
    chars = []
    for k, v in p.get("characters", {}).items():
        imgs = [link(tenant, x, 3) for x in (v.get("images") or [])[:3] if Path(x).is_file()]
        chars.append({"name": k, "description": v.get("description", ""), "voice": v.get("voice", ""),
                      "kind": v.get("kind", "person"), "images": imgs, "image": imgs[0] if imgs else "",
                      "generated": bool(v.get("generated")), "consent": bool(v.get("consent")),
                      "shots": sum(1 for x in p.get("shots", []) if k in (x.get("characters") or []))})
    mu = p.get("music") or None
    lg = p.get("logo") or None
    return {"project": p["name"], "aspect": p["aspect"], "style": p["style"], "language": p["language"], "brief": p.get("brief", ""),
            "budget_usd": p["budget_usd"], "spent_usd": round(p["spent_usd"], 3), "spent_inr": _inr(p["spent_usd"]),
            "characters": list(p.get("characters", {})), "shots": shots, "outputs": outs,
            "working": working or assembling, "assembling": assembling, "approvals": pend, "updated": p.get("updated"),
            "created": p.get("created"), "estimates": est, "planning": planning,
            "seconds": sum(int(x["duration"]) for x in p.get("shots", [])),
            "keyframes": sum(1 for x in p.get("shots", []) if x.get("keyframe")),
            "music": bool(mu), "logo": bool(lg), "character_list": chars, "prefs": pr, "quality_pref": want,
            "music_info": ({"mood": mu.get("mood") or "", "url": link(tenant, mu["file"], 3) if Path(mu["file"]).is_file() else "",
                            "volume": mu.get("volume")} if mu else None),
            "logo_info": ({"url": link(tenant, lg["src"], 3) if Path(lg["src"]).is_file() else "", "position": lg.get("position")}
                          if lg else None),
            "progress": prog, "step": step, "phase": phase, "next": nxt, "painting": sorted(painting),
            "reviewing": key in _reviewing, "can_paint": bool(st.painter), "lyria": lyria_ready(),
            "cameras": list(catalog.CAMERA), "kinds": list(catalog.KINDS),
            "month": {"spent_inr": _inr(month_spent(tenant)), "limit_inr": _inr(float(_st().studio_month_usd or 0))}}


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
            if not p.get("hidden") and (p.get("updated") or "") > best[1]:
                best = (p["name"], p.get("updated") or "")
    return best[0]


def listing(tenant: str, hidden: bool = False) -> list[dict[str, Any]]:
    return sorted([x for x in studio_sync(tenant).list_projects() if hidden or not x.get("hidden")],
                  key=lambda x: x.get("updated") or "", reverse=True)


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
                 brief: str = "", conversation_id: str = "", prefs: dict | None = None) -> dict[str, Any]:
    name = re.sub(r"\s+", " ", name or "").strip()[:60]
    if len(name) < 2:
        raise StudioJobError("Project ka naam chahiye")
    st = await studio(tenant)
    try:
        st.create(name, aspect or "9:16", style or "reel", language or "Hindi", float(_st().studio_project_usd or 5), None, brief[:2000])
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    pr = _clean_prefs(prefs or {})
    p = await st.update(name, lambda q: q.update(conversation=conversation_id, approvals={}, prefs=pr))
    _publish(tenant, p)
    return view(tenant, p)


def _clean_prefs(d: dict, base: dict | None = None) -> dict:
    """v0.159 The choices she made on the 'Naya video' screens (voice, captions + their look, music mood, quality)."""
    out = dict(base or DEFAULT_PREFS)
    if "voice" in d and d["voice"] is not None:
        v = str(d["voice"]).strip()
        out["voice"] = _voice_name(v) if v else ""
        out["voice_kind"] = v if v in VOICES else ""
    if "captions" in d and d["captions"] is not None:
        out["captions"] = bool(d["captions"])
    if d.get("caption_style") in ("bold", "words", "plain"):
        out["caption_style"] = d["caption_style"]
    if "music" in d and d["music"] is not None:
        m = str(d["music"]).strip()[:200]
        out["music"] = m
    if d.get("quality") in ("draft", "final", "premium"):
        out["quality"] = d["quality"]
    if "model" in d and d["model"] is not None:          # v0.262 checked against the studio's models when used
        out["model"] = re.sub(r"[^\w.\-/]", "", str(d["model"]))[:80]
    if "resolution" in d and d["resolution"] is not None:
        r = catalog.norm_res(d["resolution"])
        out["resolution"] = r if r in catalog.RES_ORDER else ""
    return out


async def character(tenant: str, project: str, name: str, description: str, file_ids: list[str], consent: bool,
                    voice: str = "", kind: str = "person") -> dict:
    kind = kind if kind in ("person", "place", "product") else "person"
    if not file_ids:
        raise StudioJobError("Photo ka file_id chahiye (chat mein photo bhejiye), ya character_generate.")
    if kind == "person" and not consent:
        raise StudioJobError("Asli insaan ki photo se video tabhi banega jab unki ijazat ho. Owner se poochiye; "
                             "haan ho to consent=true. (Product / logo / mascot ki photo ho to bhi consent=true.)")
    st = await studio(tenant)
    paths = [str(_her_file(tenant, st, f, "characters", ("image",))) for f in file_ids[:4]]
    try:
        r = st.character_add(project, name[:40], description[:400], paths)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    await st.update(project, lambda q: q["characters"][name[:40]].update(
        consent=True, consent_at=dt.datetime.now().isoformat(), voice=_voice_name(voice, description), kind=kind))
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
    p = st.load(project)
    try:
        q = quote(st, p, quality, shot_ids, max(1, min(int(variants or 1), 4)), model)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    if q["usd"] <= 0:
        return await _run_generate(tenant, st, project, quality, shot_ids, variants, model, None)
    return await _ask(tenant, st, project, {**{k: v for k, v in q.items() if k != "quality"}, "kind": "generate",
                                            "quality": quality, "shot_ids": shot_ids or [],
                                            "variants": max(1, min(int(variants or 1), 4)), "model": model})


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


async def character_generate(tenant: str, project: str, name: str, description: str, kind: str = "person",
                             voice: str = "") -> dict:
    st = await studio(tenant)
    kind = kind if kind in ("person", "place", "product") else "person"
    if st.painter:                     # v0.159 Nano Banana Pro paints the reference picture (same key as the opening pictures)
        return await _ask(tenant, st, project, {"kind": "character", "name": name[:40], "description": description[:400],
                                                "usd": KEYFRAME_USD, "shots": 0, "seconds": 0, "models": ["nano-banana-pro"],
                                                "char_kind": kind, "voice": voice})
    if not st.providers["fal"].ready():
        r = await st.character_generate(project, name[:40], description[:400], "offline-image")
        await st.update(project, lambda q: q["characters"][name[:40]].update(kind=kind, voice=_voice_name(voice, description)))
        _changed(tenant, project)
        return {**r, "note": "FAL_KEY nahi hai: abhi ek saada placeholder bana. Asli tasveer ke liye server par FAL_KEY lagaiye."}
    usd = catalog.IMAGE_MODELS["flux-dev"]["usd_per_image"]
    return await _ask(tenant, st, project, {"kind": "character", "name": name[:40], "description": description[:400], "usd": usd,
                                            "shots": 0, "seconds": 0, "models": ["flux-dev"], "char_kind": kind,
                                            "voice": voice})


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
        if a["kind"] == "character" and a.get("models") == ["nano-banana-pro"]:
            _bg(tenant, project, _paint_character(tenant, st, project, a))
            return st.load(project)["approvals"][approval_id]
        if a["kind"] == "character":
            r = await st.character_generate(project, a["name"], a["description"], "flux-dev")
            await st.update(project, lambda q: q["characters"][a["name"]].update(
                kind=a.get("char_kind") or "person", voice=_voice_name(a.get("voice") or "", a["description"])))
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
        if a.get("music"):              # v0.159 the music she picked comes in the same tap
            _bg(tenant, project, _do_music(tenant, st, project, a["music"],
                                           float(sum(x["duration"] for x in p["shots"]) + 3), 0.25))
        if a.get("paint_ids"):
            _bg(tenant, project, _paint_then_generate(tenant, st, project, a))
            return st.load(project)["approvals"][approval_id]
        await _run_generate(tenant, st, project, a["quality"], a["shot_ids"] or None, a["variants"], a.get("model"),
                            _cap(a) + 1e-6, a)
    except (StudioError, StudioJobError) as e:
        p = await st.update(project, lambda q: q["approvals"][approval_id].update(status="failed", error=str(e)[:300]))
        _publish(tenant, p)
        raise StudioJobError(str(e)) from None
    return st.load(project)["approvals"][approval_id]


async def expire_asks(ttl_h: int = 24) -> int:
    """v0.179 a price card that waited longer than the TTL closes itself (worker tick): nothing was spent,
    and her chat stops asking for a Haan that will never come."""
    root = Path("data") / "studio"
    if not root.is_dir():
        return 0
    cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=max(1, int(ttl_h)))
    n = 0
    for d in root.iterdir():
        if not (d.is_dir() and (d / "projects").is_dir()):
            continue
        tenant = d.name
        try:
            st = await studio(tenant)
            for p in listing(tenant):
                proj = p["project"]
                aps = st.load(proj).get("approvals") or {}
                stale = []
                for aid, a in aps.items():
                    if a.get("status") != "pending":
                        continue
                    try:
                        made = dt.datetime.fromisoformat(str(a.get("created") or ""))
                        if made.tzinfo is None:
                            made = made.replace(tzinfo=dt.timezone.utc)
                    except ValueError:
                        continue
                    if made < cut:
                        stale.append(aid)
                for aid in stale:
                    p2 = await st.update(proj, lambda q, _aid=aid: q["approvals"][_aid].update(status="expired"))
                    _publish(tenant, p2, "studio_approval", p2["approvals"][aid])
                    n += 1
        except Exception:  # noqa: BLE001
            log.exception("studio expire %s", tenant)
    return n


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
    key = _key(tenant, project)
    _painting[key] = set(ids) | _painting.get(key, set())
    _changed(tenant, project)
    try:
        r = await st.keyframes(project, ids, KEYFRAME_USD)
    except Exception as e:
        _painting.pop(key, None)
        log.exception("studio keyframes")
        _note(tenant, st.load(project), f"Video studio '{project}': tasveerein nahi ban payin: {str(e)[:160]}")
        return {}
    left = _painting.get(key, set()) - set(ids)
    if left:
        _painting[key] = left
    else:
        _painting.pop(key, None)
    p = st.load(project)
    _publish(tenant, p)
    _note(tenant, p, f"Video studio '{project}': {len(r['painted'])} shots ki pehli tasveer taiyaar"
          + (f" ({len(r['failed'])} nahi bani)" if r["failed"] else "") + ". Free preview ('generate preview') ab inhi se banega.")
    return r


async def _paint_then_generate(tenant: str, st: Studio, project: str, a: dict) -> None:
    await _do_keyframes(tenant, st, project, a["paint_ids"])
    p = st.load(project)
    try:
        await _run_generate(tenant, st, project, a["quality"], a["shot_ids"] or None, a["variants"], a.get("model"),
                            _cap(a) + 1e-6, a)
    except Exception as e:
        _note(tenant, p, f"Video studio '{project}': shots shuru nahi hue: {str(e)[:200]}")


CHARACTER_LOOK = {
    "person": ("3:4", "A photorealistic reference photo of {d}: facing the camera, upper body, natural soft light, plain light "
                      "background, sharp face, natural skin. No text, no watermark."),
    "product": ("3:4", "A clean studio product photo of {d} on a plain light background, soft studio light, sharp edges, true "
                       "colours. No text other than what is printed on the product, no watermark."),
    "place": ("16:9", "A wide, realistic photo of {d}, natural light, no people, no text, no watermark."),
}


async def _paint_character(tenant: str, st: Studio, project: str, a: dict) -> None:
    """v0.159 A made-up person / product / place painted once, then used as the reference in every shot."""
    p = st.load(project)
    kind = a.get("char_kind") or "person"
    aspect, prompt = CHARACTER_LOOK.get(kind, CHARACTER_LOOK["person"])
    try:
        img = await asyncio.to_thread(st.painter, prompt.format(d=a["description"] or a["name"]), aspect, [])
        d = st.home / "uploads" / "characters"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"gen_{slug(a['name'])}_{int(time.time())}.jpg"
        f.write_bytes(img)
        st.character_add(project, a["name"], a["description"], [str(f)])

        def fn(q):
            q["characters"][a["name"]].update(generated="nano-banana-pro", kind=kind,
                                              voice=_voice_name(a.get("voice") or "", a["description"]))
            st._charge(q, KEYFRAME_USD, f"character {a['name']}", "nano-banana-pro")
        p = await st.update(project, fn)
        _publish(tenant, p)
        _note(tenant, p, f"Video studio '{project}': '{a['name']}' ki tasveer ban gayi; har shot mein yahi dikhega.")
    except Exception as e:
        log.exception("studio character paint")
        _note(tenant, p, f"Video studio '{project}': '{a['name']}' ki tasveer nahi ban payi: {str(e)[:150]}")


def _cap(a: dict) -> float:
    """The most the video shots of an approved card may cost (pictures and music are paid separately)."""
    if a.get("cap_usd") is not None:
        return float(a["cap_usd"])
    return max(0.0, float(a["usd"]) - KEYFRAME_USD * len(a.get("paint_ids") or []) - (MUSIC_USD if a.get("music") else 0))


async def _run_generate(tenant: str, st: Studio, project: str, quality: str, shot_ids, variants, model, max_cost,
                        card: dict | None = None) -> dict:
    try:
        r = await st.generate(project, quality, shot_ids or None, variants, model, max_cost, 0)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    usd = float((card or {}).get("usd") or r["estimate_usd"])
    await st.update(project, lambda q: q.update(batch={"jobs": r["jobs"], "quality": quality, "usd": usd, "inr": _inr(usd),
                                                       "at": dt.datetime.now().isoformat(timespec="seconds")}))
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
        if js and all(j["state"] in ("done", "failed", "cancelled") for j in js):
            done = sum(1 for j in js if j["state"] == "done")
            if quality != "preview" and done:
                _reviewing.add(_key(tenant, project))
                _changed(tenant, project)
                try:
                    await _auto_review(tenant, st, project, [j for j in js if j["state"] == "done"])
                finally:
                    _reviewing.discard(_key(tenant, project))
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
                    x for x in q["variants"][sid] if x["n"] == n).update(look={k: lk.get(k) for k in ("score", "problems", "fix", "matches", "good")}))
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
            "\"good\": [2-3 short things that are right], \"problems\": [short, with the second they happen like '0:04 ...'], "
            "\"fix\": \"a better prompt sentence if needed\"}. Write good / problems in simple Hinglish. Look for wrong "
            "faces, extra fingers, melting objects, text gibberish, wrong place.")
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
        voice = prefs_of(st.load(project))["voice"] or ("female" if (a.get("gender") or "m") == "f" else "male")
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
    await st.update(project, lambda q: q["music"].update(mood="apna gaana" if file_id else mood))
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

        def charged(q):
            st._charge(q, MUSIC_USD, f"music ({mood})", _st().studio_music_model)
            q["music"]["mood"] = mood
        await st.update(project, charged)
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
        r = st.logo_set(project, str(src), position if position in LOGO_SPOTS else "top-right")
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    _changed(tenant, project)
    return r


async def assemble(tenant: str, project: str, captions: bool | None = None, transition: str | None = None) -> dict:
    st = await studio(tenant)
    p = _load(tenant, project)
    if captions is None:
        captions = bool(prefs_of(p)["captions"])
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


# ---------------------------------------------------------------- v0.159 the app's full studio
async def settings(tenant: str, project: str, changes: dict) -> dict:
    """Project choices from the app: voice, captions + their look, music mood, quality, logo position, name of the look."""
    st = await studio(tenant)
    p = _load(tenant, project)
    pos = changes.get("logo_position")
    if pos and pos not in LOGO_SPOTS:
        raise StudioJobError("logo ki jagah: " + " / ".join(LOGO_SPOTS))
    style = changes.get("style")
    if style and style not in catalog.STYLES:
        raise StudioJobError(f"look: {', '.join(catalog.STYLES)}")

    def fn(q):
        q["prefs"] = _clean_prefs(changes, prefs_of(q))
        if pos and q.get("logo"):
            q["logo"]["position"] = pos
        if style:
            q["style"] = style
        if changes.get("music_volume") is not None and q.get("music"):
            q["music"]["volume"] = max(0.05, min(float(changes["music_volume"]), 1.0))
    p = await st.update(project, fn)
    _publish(tenant, p)
    return view(tenant, p)


async def add_shot(tenant: str, project: str, shot: dict, after: str = "") -> dict:
    p = _load(tenant, project)
    shots = [dict(x) for x in p["shots"]]
    used = {x["id"] for x in shots}
    n = len(shots) + 1
    while f"s{n}" in used:
        n += 1
    new = {k: v for k, v in (shot or {}).items() if k in ("prompt", "duration", "kind", "camera", "characters", "dialogue",
                                                          "caption", "speaker", "transition") and v not in (None, "")}
    new.setdefault("duration", 5)
    new["id"] = f"s{n}"
    at = next((i + 1 for i, x in enumerate(shots) if x["id"] == after), len(shots))
    shots.insert(at, new)
    return await _reboard(tenant, project, shots)


async def _reboard(tenant: str, project: str, shots: list[dict]) -> dict:
    """Storyboard change from the app: existing shots keep their own pictures / frames (they are already inside her folder)."""
    st = await studio(tenant)
    try:
        st.storyboard_set(project, shots)
    except StudioError as e:
        raise StudioJobError(str(e)) from None
    _changed(tenant, project)
    return view(tenant, _load(tenant, project))


async def delete_shot(tenant: str, project: str, shot_id: str) -> dict:
    p = _load(tenant, project)
    shots = [dict(x) for x in p["shots"] if x["id"] != shot_id]
    if len(shots) == len(p["shots"]):
        raise StudioJobError(f"Shot {shot_id} nahi mila")
    if not shots:
        raise StudioJobError("Aakhri shot nahi hata sakte; badal dijiye.")
    return await _reboard(tenant, project, shots)


async def redo_shot(tenant: str, project: str, shot_id: str, change: str = "", quality: str = "") -> dict:
    """Takes screen 'Kuch badalna hai?': her words go into the shot, then that one shot is made again (a price card)."""
    st = await studio(tenant)
    p = _load(tenant, project)
    s = next((x for x in p["shots"] if x["id"] == shot_id), None)
    if not s:
        raise StudioJobError(f"Shot {shot_id} nahi mila")
    change = re.sub(r"\s+", " ", change or "").strip()[:300]
    if change:
        base = re.sub(r"\s*Change: .*$", "", s["prompt"]).rstrip(". ")
        try:
            st.shot_update(project, shot_id, {"prompt": f"{base}. Change: {change}."})
        except StudioError as e:
            raise StudioJobError(str(e)) from None
        _changed(tenant, project)
    picked = p.get("picked", {}).get(shot_id)
    last_q = next((v["quality"] for v in p.get("variants", {}).get(shot_id, []) if v["n"] == picked), None)
    q = quality if quality in catalog.QUALITY else (last_q if last_q and last_q != "preview" else prefs_of(p)["quality"])
    return await generate(tenant, project, q, [shot_id])


async def cancel(tenant: str, project: str) -> dict:
    st = await studio(tenant)
    _load(tenant, project)
    r = await st.cancel_jobs(project)
    p = st.load(project)
    _publish(tenant, p)
    if r["cancelled"]:
        _note(tenant, p, f"Video studio '{project}': {r['cancelled']} shot rok diye. Jo ban chuke the woh rahenge.")
    return {**r, "say": (f"{r['cancelled']} shot rok diye. Jo pehle se provider par shuru ho chuka tha, uska paisa "
                         "provider le sakta hai." if r["cancelled"] else "Kuch chal nahi raha tha.")}


async def hide(tenant: str, project: str) -> dict:
    """Remove a project from her list (the files and the spend record stay, so the month's total stays right)."""
    st = await studio(tenant)
    p = _load(tenant, project)
    if any(j["state"] in ("queued", "submitted", "running", "retrying") for j in p.get("jobs", {}).values()):
        raise StudioJobError("Pehle chal rahe shots rokiye.")
    await st.update(project, lambda q: q.update(hidden=True))
    return {"hidden": project}


IMPROVE_SYSTEM = """You help an Indian small-business owner describe a short AI video. Rewrite her idea as a richer brief
for a film director: who / what we see, the place, the mood, the light, 3-6 moments in order, the one line to be said
(in her language) and the ending. Keep every fact she gave (names, prices, offers, dates, phone numbers) exactly; never
invent prices, phone numbers, dates, real people or brand names. Write in simple Hinglish (Roman script) except the
spoken line, which stays in her language and script. Max 90 words. Output only the brief."""


async def improve_brief(brief: str, language: str = "Hindi", seconds: int = 30) -> dict:
    brief = (brief or "").strip()
    if len(brief) < 4:
        raise StudioJobError("Pehle thoda sa likhiye ki video kis baare mein hai.")
    out = await _write(IMPROVE_SYSTEM, f"Her idea: {brief[:1500]}\nLanguage of the spoken line: {language}\n"
                                       f"Length: about {int(seconds)} seconds.", 900)
    out = re.sub(r"^\s*(brief|Brief)\s*:\s*", "", out).strip().strip('"')
    if not out:
        raise StudioJobError("Abhi behtar nahi ho paya; dobara try kijiye.")
    return {"brief": out[:2000]}


SAMPLE_LINES = {"Hindi": "Namaste! Main aapke video mein yahi awaaz hoon.", "Marathi": "नमस्कार! तुमच्या व्हिडिओमध्ये हाच आवाज असेल.",
                "English": "Hello! This is the voice in your video.", "Hinglish": "Hello! Aapke video mein yahi awaaz hogi."}


async def voice_sample(tenant: str, voice: str = "male", language: str = "Hindi") -> dict:
    """A short line in the voice she is choosing (made once per voice + language, kept)."""
    if not _st().gemini_api_key:
        raise StudioJobError("Awaaz sunane ke liye server par GEMINI_API_KEY chahiye.")
    st = await studio(tenant)
    voice = voice if voice in VOICES else "male"
    d = st.home / "uploads" / "samples"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{voice}_{slug(language)}.wav"
    if not out.is_file():
        line = SAMPLE_LINES.get(language, SAMPLE_LINES["Hindi"])
        try:
            got = await asyncio.to_thread(st.speak, line, language, voice)
        except Exception as e:
            raise StudioJobError(f"Awaaz nahi ban payi: {str(e)[:150]}") from None
        shutil.copyfile(got, out)
    return {"url": link(tenant, out, 3), "voice": voice}


async def speak_line(tenant: str, project: str, shot_id: str) -> dict:
    """The shot's spoken line in the chosen voice, free (also used later for lip sync), so she can hear it first."""
    st = await studio(tenant)
    p = _load(tenant, project)
    s = next((x for x in p["shots"] if x["id"] == shot_id), None)
    if not s or not s.get("dialogue"):
        raise StudioJobError("Is shot mein bolne wali line nahi hai.")
    try:
        f = await st._speech(project, s)
    except Exception as e:
        raise StudioJobError(f"Awaaz nahi ban payi: {str(e)[:150]}") from None
    _changed(tenant, project)
    return {"url": link(tenant, f, 3)}


# ---------------------------------------------------------------- v0.262 EVERY MODEL, PRICE FIRST
KEY_OF = {"fal": "FAL_KEY", "byteplus": "ARK_API_KEY", "google": "GEMINI_API_KEY", "sync": "SYNC_API_KEY",
          "openrouter": "OPENROUTER_API_KEY", "offline": ""}


SKIP_RE = re.compile(r"(edit|upscale|aleph)", re.I)
AVATAR_RE = re.compile(r"(avatar|heygen)", re.I)


def _watch_card(m: dict) -> dict:
    """A model the live OpenRouter list brought in: the market card it matches, else its own name split as 'Maker: Name'."""
    rid = str(m.get("model") or "").lower()
    for w in catalog.WATCH:
        if re.search(w["match"], rid):
            return {k: w[k] for k in ("name", "maker", "tier", "best")}
    label = str(m.get("label") or rid).replace(" via OpenRouter", "")
    maker, _, name = label.partition(": ")
    return {"name": name or label, "maker": maker if name else rid.split("/")[0], "tier": "strong", "best": ""} if name \
        else {"name": label, "maker": rid.split("/")[0], "tier": "strong", "best": ""}


def catalogue(tenant: str) -> dict:
    """Every video model for her picker: the ones Hoola can call (ready, or the server key that switches them on) and
    the rest of the market (and what it would take), each with its price per second at every resolution in rupees."""
    st = studio_sync(tenant)
    k = float(_st().studio_usd_inr or 85)
    live_ids = [str(m.get("model") or "").lower() for m in st.models.values() if m.get("provider") == "openrouter"]
    cards = []
    for key, m in st.models.items():
        if key in ("offline-preview", "sync-3") or SKIP_RE.search(str(m.get("model") or "")):
            continue                                       # edit / upscale models need a video in, not a new clip
        c = catalog.CARDS.get(key) or _watch_card(m)
        ready = st.providers[m["provider"]].ready()
        avatar = AVATAR_RE.search(str(m.get("model") or ""))
        if avatar:                                         # photo + script avatars: the Voice / Editor pages, a later phase
            c = {**c, "tier": "talk"}
            ready = False
        cards.append({
            "key": key, "name": c.get("name") or _label(st, key), "maker": c.get("maker") or (m.get("model", "").split("/")[0] or m["provider"]),
            "tier": c.get("tier") or "strong", "best": c.get("best") or m.get("label", ""), "rank": c.get("rank", ""),
            "via": m["provider"], "ready": ready, "status": "ready" if ready else ("coming" if avatar else "needs_key"),
            "why": "" if ready else ("Talking avatars from a photo come to the Voice studio in the next phase" if avatar
                                     else f"Switch on with {KEY_OF.get(m['provider'], 'its key')} on the server"),
            "resolutions": [catalog.norm_res(r) for r in m["resolutions"]], "durations": m["durations"],
            "allowed_durations": m.get("allowed_durations"), "aspects": m["aspects"], "audio": bool(m.get("audio", True)),
            "references": m.get("references", 0),
            "inr_per_s": {catalog.norm_res(r): round(catalog.rate(m, r) * k, 2) for r in m["resolutions"]},
            "inr_per_s_silent": ({catalog.norm_res(r): round(catalog.rate(m, r, False) * k, 2) for r in m["resolutions"]}
                                 if m.get("usd_by_res_noaudio") else None),
            "price_live": bool(m.get("price_live")), "listed": bool(c)})
    for w in catalog.WATCH:
        if any(re.search(w["match"], i) for i in live_ids):
            continue                                       # carried live by OpenRouter: it is already in the list above
        cards.append({"key": "", "name": w["name"], "maker": w["maker"], "tier": w["tier"], "best": w["best"], "rank": "",
                      "via": "", "ready": False, "status": "coming", "why": "Needs " + w["needs"], "resolutions": [],
                      "durations": [], "allowed_durations": None, "aspects": [], "audio": True, "references": 0,
                      "inr_per_s": {"1080p": round(w["usd_s"] * k, 2)}, "inr_per_s_silent": None, "price_live": False,
                      "listed": True, "estimate_only": True})
    for c in cards:
        c["q"] = catalog.quality_rank(c["name"])
    order = {"top": 0, "strong": 1, "budget": 2, "talk": 3}
    cards.sort(key=lambda c: (not c["ready"], c["status"] == "coming", order.get(c["tier"], 4), c["q"], c["name"]))
    return {"models": cards, "usd_inr": k, "prices_checked": catalog.PRICES_CHECKED, "synced_at": st.synced_at,
            "not_offered": [{"name": n, "why": y} for n, y in catalog.NOT_OFFERED],
            "lipsync": {"name": "Sync 3", "inr_per_s": round(catalog.rate(st.models["sync-3"], "1080p") * k, 2)} if "sync-3" in st.models else None,
            "note": "Prices are per second of finished video. The card before every paid run shows the exact total; "
                    "you are never charged more than the card."}


QUALITY_OF_RES = {"360p": "draft", "480p": "draft", "540p": "draft", "720p": "draft", "768p": "draft",
                  "1080p": "final", "2k": "premium", "4k": "premium"}


def clip_price(tenant: str, model: str = "", seconds: int = 8, resolution: str = "1080p", audio: bool = True,
               takes: int = 1, kind: str = "scene") -> dict:
    """The live price on the Create button: one clip of `seconds` at `resolution` with this model (or what Hoola Auto
    would pick), `takes` times. The same rate table the price card and the run use."""
    st = studio_sync(tenant)
    res = catalog.norm_res(resolution) or "1080p"
    quality = QUALITY_OF_RES.get(res, "final")
    if model and model not in st.models:
        raise StudioJobError("Yeh model is server par nahi hai")
    m = model or st.model_for({"kind": kind}, quality, None)
    cfg = st.models[m]
    lo, hi = cfg["durations"]
    secs = max(lo, min(hi, int(seconds or 8)))
    if cfg.get("allowed_durations"):
        secs = min(cfg["allowed_durations"], key=lambda x: (abs(x - int(seconds or 8)), -x))
    ress = [catalog.norm_res(r) for r in cfg["resolutions"]]
    got = res if res in ress else min(ress, key=lambda r: abs(catalog.RES_ORDER.index(r) - catalog.RES_ORDER.index(res))
                                      if r in catalog.RES_ORDER and res in catalog.RES_ORDER else 99)
    takes = max(1, min(int(takes or 1), 4))
    usd = catalog.rate(cfg, got, audio) * secs * takes
    k = float(_st().studio_usd_inr or 85)
    return {"model": m, "name": _label(st, m), "auto": not model, "seconds": secs, "resolution": got, "audio": audio,
            "takes": takes, "inr_per_s": round(catalog.rate(cfg, got, audio) * k, 2), "usd": round(usd, 4),
            "inr": round(usd * k, 1), "ready": st.providers[cfg["provider"]].ready(),
            "changed": [x for x, a, b in (("seconds", secs, int(seconds or 8)), ("resolution", got, res)) if a != b]}


async def models_refresh(tenant: str) -> dict:
    """Read OpenRouter's live model list and prices now (also done when the studio starts)."""
    st = await studio(tenant)
    try:
        r = await asyncio.wait_for(st.models_sync(), 30)
    except Exception as e:
        raise StudioJobError(f"Abhi model list nahi mili: {str(e)[:120]}") from None
    return {**r, "synced_at": st.synced_at}
