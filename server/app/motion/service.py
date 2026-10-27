"""Hoola Motion: plan a short animated video with AI, render it to MP4 on the server, keep it for the owner.

Kinds (templates tuned from the most remade prompts in yihui-dev/awesome-opus5-5-videos, MIT, with credit):
  explainer  "Mere business ki reel"  - problem, what we do, 3 steps, proof, call to action (after @alex-prompter)
  recipe     "Recipe reel"             - ingredients drop into the kadhai, steps, final dish (after @Ror_Fly, @sarut0bisasuke)
  logo       "Logo intro"              - wireframe, flying shards assemble, name types out (after @mounnna, @0xvalure)
  offer      "Offer / sale"            - kinetic headline, offer stamp, items, dates + contact (after @viktoroddy)
  custom     "Apna idea" (beta)        - Hoola (Claude) writes the whole animation as code; checked before rendering
Renders run one at a time in a background thread (CPU heavy); the app polls the job.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import now, session
from . import ai, music, render
from .models import MotionVideo

log = logging.getLogger("santosh.motion")

KINDS = [
    {"id": "explainer", "label": "Business ki reel", "emoji": "🏪",
     "about": "Aapke kaam ki 25 second ki reel: grahak ki pareshani, aap kya karte ho, 3 steps, bharosa, contact.",
     "example": "Meri chai ki dukaan 'Sharma Chai Point', Gandhi Chowk Akola. Adrak elaichi wali chai, WhatsApp pe order, "
                "ghar tak delivery. Phone 98765 43210. Pehli chai free."},
    {"id": "recipe", "label": "Recipe reel", "emoji": "🍲",
     "about": "Saamaan kadhai mein girta hai, phir steps, phir taiyaar dish. Kisi bhi recipe ki.",
     "example": "Masala chai 2 logon ke liye: paani, adrak, elaichi, chai patti, doodh, cheeni."},
    {"id": "logo", "label": "Logo intro", "emoji": "✨",
     "about": "10 second ka brand intro: logo tukdon se judta hai, naam type hota hai. Logo photo de sakte hain.",
     "example": "Newtika AI - software jo sochta hai. Neela rang."},
    {"id": "offer", "label": "Offer / sale", "emoji": "🎉",
     "about": "Sale ya tyohaar ka offer: bada headline, offer stamp, kya milega, tareekh aur contact.",
     "example": "Diwali sale, Sharma Saree Center: har saree par 30% off, Banarasi, Paithani, cotton. 25 Oct se 5 Nov. "
                "Main Road Akola, 98765 43210."},
    {"id": "custom", "label": "Apna idea (beta)", "emoji": "🧪",
     "about": "Kuch bhi likhiye: Hoola khud poori animation code mein likhta hai. Thoda zyada samay lagta hai.",
     "example": "Raat ke aasmaan mein taare jud kar 'Happy Birthday Meghana' likhte hain, phir phuljhadi."},
]
KIND_IDS = {k["id"] for k in KINDS}
ASPECTS = tuple(render.SIZES)
AI_NOTE = "AI se bani video · Hoola"

_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="motion")
_lock = threading.Lock()


class MotionError(Exception):
    pass


def _dir() -> Path:
    p = Path(get_settings().motion_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ----------------------------------------------------------------------------- cleaning the plan
def _s(v: Any, n: int) -> str:
    return re.sub(r"[\u0000-\u001f‪-‮⁦-⁩<>]", " ", str(v or "")).strip()[:n]


def _hex(v: Any) -> str:
    v = str(v or "").strip()
    return v if re.fullmatch(r"#[0-9a-fA-F]{6}", v) else ""


def _colors(c: Any) -> dict:
    c = c if isinstance(c, dict) else {}
    return {k: _hex(c.get(k)) for k in ("bg1", "bg2", "accent", "ink", "onaccent") if _hex(c.get(k))}


def _logo(v: Any) -> str:
    v = str(v or "")
    m = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", v)
    if not m or len(v) > 700_000:
        return ""
    try:
        base64.b64decode(m.group(2), validate=True)
    except ValueError:
        return ""
    return v


def clean(kind: str, d: Any) -> dict:
    """Only known fields, short and safe (the page uses textContent, but lengths keep the layout sane)."""
    d = d if isinstance(d, dict) else {}
    lst = lambda v, n: v[:n] if isinstance(v, list) else []          # noqa: E731
    if kind == "explainer":
        p, so, pr, c = (d.get(k) if isinstance(d.get(k), dict) else {} for k in ("problem", "solution", "proof", "cta"))
        return {"brand": _s(d.get("brand"), 40), "tagline": _s(d.get("tagline"), 70), "emoji": _s(d.get("emoji"), 8),
                "colors": _colors(d.get("colors")), "steps_title": _s(d.get("steps_title"), 20),
                "problem": {"emoji": _s(p.get("emoji"), 8), "tag": _s(p.get("tag"), 26), "title": _s(p.get("title"), 70),
                            "sub": _s(p.get("sub"), 90)},
                "solution": {"emoji": _s(so.get("emoji"), 8), "title": _s(so.get("title"), 80)},
                "steps": [{"emoji": _s(x.get("emoji"), 8), "title": _s(x.get("title"), 50)}
                          for x in lst(d.get("steps"), 3) if isinstance(x, dict) and _s(x.get("title"), 50)],
                "proof": {"big": _s(pr.get("big"), 14), "sub": _s(pr.get("sub"), 50)},
                "cta": {"title": _s(c.get("title"), 50), "offer": _s(c.get("offer"), 40), "phone": _s(c.get("phone"), 24),
                        "place": _s(c.get("place"), 50), "extra": _s(c.get("extra"), 40)}}
    if kind == "recipe":
        return {"dish": _s(d.get("dish"), 40), "emoji": _s(d.get("emoji"), 8), "time": _s(d.get("time"), 16),
                "serves": _s(d.get("serves"), 16), "level": _s(d.get("level"), 16), "colors": _colors(d.get("colors")),
                "ingredients_title": _s(d.get("ingredients_title"), 20),
                "ingredients": [{"emoji": _s(x.get("emoji"), 8), "qty": _s(x.get("qty"), 16), "name": _s(x.get("name"), 30)}
                                for x in lst(d.get("ingredients"), 8) if isinstance(x, dict) and _s(x.get("name"), 30)],
                "steps": [_s(x, 110) for x in lst(d.get("steps"), 5) if _s(x, 110)],
                "end": _s(d.get("end"), 40), "credit": _s(d.get("credit"), 40)}
    if kind == "logo":
        return {"brand": _s(d.get("brand"), 32), "tagline": _s(d.get("tagline"), 50), "monogram": _s(d.get("monogram"), 2),
                "colors": _colors(d.get("colors")), "logo": _logo(d.get("logo"))}
    if kind == "offer":
        return {"festival": _s(d.get("festival"), 20).lower(), "headline": _s(d.get("headline"), 26), "sub": _s(d.get("sub"), 60),
                "big": _s(d.get("big"), 16), "big_note": _s(d.get("big_note"), 30), "items_title": _s(d.get("items_title"), 26),
                "items": [_s(x, 40) for x in lst(d.get("items"), 5) if _s(x, 40)], "dates": _s(d.get("dates"), 30),
                "cta": _s(d.get("cta"), 40), "brand": _s(d.get("brand"), 40), "phone": _s(d.get("phone"), 24),
                "place": _s(d.get("place"), 50), "upi": _s(d.get("upi"), 50), "colors": _colors(d.get("colors"))}
    return {}


def title_of(kind: str, d: dict) -> str:
    return _s(d.get("brand") or d.get("dish") or d.get("headline") or d.get("title") or
              next(k["label"] for k in KINDS if k["id"] == kind), 80)


# ----------------------------------------------------------------------------- planning
def kinds() -> dict:
    return {"kinds": KINDS, "aspects": list(ASPECTS), "music": list(music.MOODS), "ready": not render.available(),
            "missing": render.available()}


def plan(kind: str, brief: str) -> dict:
    if kind not in KIND_IDS or kind == "custom":
        raise MotionError("Plan sirf template wali videos ke liye banta hai.")
    try:
        raw = ai.plan(kind, brief)
    except ai.AiError as e:
        raise MotionError(str(e))
    except Exception as e:
        log.warning("motion plan failed: %s", e)
        raise MotionError("Abhi plan nahi ban paya. Thodi der baad try kijiye.")
    data = clean(kind, raw)
    return {"kind": kind, "data": data, "title": title_of(kind, data)}


# ----------------------------------------------------------------------------- jobs
def _sig(vid: str, exp: int) -> str:
    st = get_settings()
    key = st.secret_key or st.api_key or "hoola-motion"
    return hmac.new(f"motion:{key}".encode(), f"{vid}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def file_url(vid: str, what: str = "mp4", hours: int = 72) -> str:
    exp = int(time.time()) + hours * 3600
    return f"/api/motion/files/{vid}.{what}?exp={exp}&sig={_sig(vid + what, exp)}"


def check_sig(vid: str, what: str, exp: int, sig: str) -> bool:
    return exp >= time.time() and hmac.compare_digest(_sig(vid + what, exp), sig or "")


def view(v: MotionVideo) -> dict:
    out = {"id": v.id, "kind": v.kind, "title": v.title, "aspect": v.aspect, "music": v.music, "status": v.status,
           "progress": round(v.progress, 3), "error": v.error, "duration": v.duration, "size": v.size,
           "created_at": v.created_at.isoformat() if v.created_at else "", "ai_label": AI_NOTE,
           "data": json.loads(v.data or "{}") if v.kind != "custom" else {"brief": json.loads(v.data or "{}").get("brief", "")}}
    if v.status == "done":
        out["url"] = file_url(v.id, "mp4")
        if v.thumb:
            out["thumb"] = file_url(v.id, "jpg")
    return out


def create(tenant: str, kind: str, data: Any = None, aspect: str = "9:16", mood: str = "upbeat", brief: str = "",
           conv: str = "") -> dict:
    if kind not in KIND_IDS:
        raise MotionError("Yeh video type nahi hai.")
    from .. import usage
    if not usage.allowed(tenant, "motion"):             # v0.98 the month's AI limit is used up
        raise MotionError(usage.blocked_text(tenant))
    if aspect not in ASPECTS:
        aspect = "9:16"
    mood = mood if mood in music.MOODS else "upbeat"
    if render.available():
        raise MotionError(f"Server par video banane ka saamaan nahi hai ({render.available()}). VPS par "
                          "server/deploy/setup_motion.sh chalaiye.")
    if kind == "custom":
        if len((brief or "").strip()) < 5:
            raise MotionError("Apne idea ko do-teen line mein likhiye.")
        d: dict = {"brief": _s(brief, 3000)}
        title = _s(brief, 60)
    else:
        d = clean(kind, data)
        if not any(v for k, v in d.items() if k != "colors"):
            raise MotionError("Video mein kya dikhana hai? Pehle plan banaiye ya details bhariye.")
        title = title_of(kind, d)
    with session() as s:
        busy = s.scalars(select(MotionVideo).where(MotionVideo.tenant_id == tenant,
                                                   MotionVideo.status.in_(("queued", "rendering")))).all()
        if len(busy) >= 3:
            raise MotionError("3 videos pehle se ban rahi hain. Unke poore hone ka intezaar kijiye.")
        v = MotionVideo(tenant_id=tenant, conversation_id=conv, kind=kind, title=title, aspect=aspect, music=mood,
                        data=json.dumps(d, ensure_ascii=False))
        s.add(v)
        s.flush()
        vid = v.id
        out = view(v)
    _pool.submit(_run, vid)
    return out


def _set(vid: str, **kw) -> None:
    with session() as s:
        v = s.get(MotionVideo, vid)
        if v is not None:
            for k, val in kw.items():
                setattr(v, k, val)


def _run(vid: str) -> None:
    """The render job (one at a time)."""
    with session() as s:
        v = s.get(MotionVideo, vid)
        if v is None or v.status != "queued":
            return
        kind, aspect, mood, data, conv, tenant = v.kind, v.aspect, v.music, json.loads(v.data or "{}"), v.conversation_id, v.tenant_id
        v.status = "rendering"
    from .. import usage
    usage.bind(tenant, "motion")
    out = _dir() / f"{vid}.mp4"
    try:
        html = None
        if kind == "custom":
            w, h = render.SIZES[aspect]
            html = ai.custom_html(data.get("brief", ""), aspect, w, h)
            check_custom(html, aspect)
            _set(vid, html=html, progress=.08)
        page_data = {} if kind == "custom" else data
        info = render.frames(kind, page_data, aspect, html=html)
        if info["errors"] and kind != "custom":
            log.warning("motion template %s errors: %s", kind, info["errors"][:3])
        wav = music.write(mood, min(info.get("duration") or 0, render.MAX_SECONDS) + 1, _dir() / f"{vid}.wav")
        base = .1 if kind == "custom" else 0.0
        res = render.video(kind, page_data, out, aspect, html=html, music=wav, title=title_of(kind, data),
                           progress=lambda f: _set(vid, progress=base + (1 - base) * f * .97))
        if wav:
            wav.unlink(missing_ok=True)
        thumb = _thumb(out)
        _set(vid, status="done", progress=1.0, path=str(out), size=res["size"], duration=res["duration"],
             thumb=str(thumb) if thumb else "", finished_at=now())
        _prune(tenant)
        _tell(tenant, conv, vid)
    except (ai.AiError, render.RenderError, MotionError) as e:
        _set(vid, status="failed", error=str(e)[:500], finished_at=now())
    except Exception as e:
        log.exception("motion render %s failed", vid)
        _set(vid, status="failed", error=f"Video nahi ban payi: {str(e)[:200]}", finished_at=now())


def check_custom(html: str, aspect: str) -> None:
    """Hoola's own animation code must run without errors, move, and draw the same frame for the same time."""
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="hmc_"))
    try:
        info = render.frames("custom", {}, aspect, html=html, times=[.5, 2.5, .5, 4.5], out_dir=tmp)
        errs = [e for e in info["errors"] if "favicon" not in e]
        if errs:
            raise MotionError(f"Banaye hue code mein galti: {errs[0][:160]}")
        dur = info.get("duration") or 0
        if not 3 <= dur <= render.MAX_SECONDS:
            raise MotionError("Animation ki lambai theek nahi (3 se 60 second honi chahiye).")
        shots = [Path(p).read_bytes() for p in info["shots"]]
        if len(shots) == 4:
            from io import BytesIO
            from PIL import Image, ImageChops, ImageStat
            ims = [Image.open(BytesIO(b)).convert("L") for b in shots]
            if max(ImageStat.Stat(i).stddev[0] for i in ims) < 4:
                raise MotionError("Animation khaali screen dikha rahi hai.")
            if ImageStat.Stat(ImageChops.difference(ims[0], ims[2])).mean[0] > .15:
                raise MotionError("Animation har baar alag frame bana rahi hai (time pe nirbhar nahi).")
            if ImageStat.Stat(ImageChops.difference(ims[1], ims[3])).mean[0] < .3 and \
                    ImageStat.Stat(ImageChops.difference(ims[0], ims[1])).mean[0] < .3:
                raise MotionError("Animation hil hi nahi rahi.")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def _thumb(mp4: Path) -> Path | None:
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        return None
    t = mp4.with_suffix(".jpg")
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "2.5", "-i", str(mp4), "-frames:v", "1", "-vf", "scale=360:-2", str(t)],
                       timeout=30, check=True)
        return t
    except Exception:
        return None


def _tell(tenant: str, conv: str, vid: str) -> None:
    """Started from chat / a call: show the finished video card there."""
    if not conv:
        return
    try:
        from ..events import bus
        with session() as s:
            v = s.get(MotionVideo, vid)
            card = view(v)
        bus.publish(conv, "motion", {k: card.get(k) for k in ("id", "title", "kind", "aspect", "duration", "url", "thumb", "ai_label")})
    except Exception:
        log.exception("motion: could not tell the chat")


def _prune(tenant: str) -> None:
    keep = get_settings().motion_keep
    with session() as s:
        rows = s.scalars(select(MotionVideo).where(MotionVideo.tenant_id == tenant)
                         .order_by(MotionVideo.created_at.desc())).all()
        for v in rows[keep:]:
            _delete_files(v)
            s.delete(v)


def _delete_files(v: MotionVideo) -> None:
    for p in (v.path, v.thumb):
        if p:
            Path(p).unlink(missing_ok=True)


def get(tenant: str, vid: str) -> dict:
    with session() as s:
        v = s.get(MotionVideo, vid)
        if v is None or v.tenant_id != tenant:
            raise MotionError("Yeh video nahi mili.")
        return view(v)


def list_(tenant: str, limit: int = 40) -> list[dict]:
    with session() as s:
        rows = s.scalars(select(MotionVideo).where(MotionVideo.tenant_id == tenant)
                         .order_by(MotionVideo.created_at.desc()).limit(limit)).all()
        return [view(v) for v in rows]


def delete(tenant: str, vid: str) -> dict:
    with session() as s:
        v = s.get(MotionVideo, vid)
        if v is None or v.tenant_id != tenant:
            raise MotionError("Yeh video nahi mili.")
        if v.status == "rendering":
            raise MotionError("Video abhi ban rahi hai; poori hone ke baad hataiye.")
        _delete_files(v)
        s.delete(v)
    return {"deleted": True}


def file_path(vid: str, what: str) -> Path | None:
    with session() as s:
        v = s.get(MotionVideo, vid)
        if v is None or v.status != "done":
            return None
        p = Path(v.thumb if what == "jpg" else v.path)
    return p if p.exists() else None


def to_youtube(tenant: str, conv: str, vid: str, title: str = "", privacy: str = "private") -> dict:
    """Owner's own channel only, as a Short, marked as AI-made; the owner approves the card before anything is posted."""
    from ..bazar import service as bazar
    from ..mailbox import service as ms
    from ..youtube import service as ys
    with session() as s:
        v = s.get(MotionVideo, vid)
        if v is None or v.tenant_id != tenant or v.status != "done":
            raise MotionError("Pehle video poori banne dijiye.")
        path, vtitle, aspect = v.path, v.title, v.aspect
    row = ms.store_bytes(tenant, f"{re.sub(r'[^A-Za-z0-9 _-]', '', vtitle)[:50] or 'hoola'}.mp4", Path(path).read_bytes(), "to_youtube")
    t = _s(title or vtitle, 90)
    if aspect == "9:16" and "#shorts" not in t.lower():
        t = (t[:80] + " #Shorts").strip()
    desc = "Hoola AI se bani video (AI-generated)."
    try:
        pid = ys.plan_upload(tenant, conv, row.id, t, desc, privacy if privacy in ("private", "unlisted", "public") else "private",
                             ["Hoola", "AI"], synthetic=True)
    except TypeError:          # older youtube service without the synthetic flag
        pid = ys.plan_upload(tenant, conv, row.id, t, desc, privacy, ["Hoola", "AI"])
    except Exception as e:
        raise MotionError(str(e))
    try:
        out = bazar.run(tenant, conv, "santosh-youtube", "confirm_change", {"pending_id": pid})
    except Exception as e:
        raise MotionError(str(e))
    return {k: v for k, v in out.items() if k in ("needs_approval", "approval_id", "card", "say")}
