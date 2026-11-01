"""v0.415 ASSET PIPELINE (Hoola Game Engine plan, Phase 4): the game's art, sound, music, voice and 3D models as
versioned files of a Studio Project, every one checked in code, none in the game before her OK.

Kinds and where each comes from:
- sprite / icon / ui / background : Hoola's picture engine (photogen, Gemini), STYLE-LOCKED to the Game Bible - the
  prompt carries the palette + tone, sprites are drawn on flat magenta and keyed to transparency in code, cropped,
  resized to the exact size, then measured: how much of it is the Bible palette (palette lock "check" or "strict" =
  every pixel snapped to the palette). Costs money -> a PRICE CARD first; only her tap spends.
- sfx   : made in code (gamedesk/sfx.py) from a preset + seed - free, instant, the same seed = the same bytes.
- music : Lyria (create.song), instrumental, made loop-friendly, OGG for the web - price card first.
- voice : text-to-speech lines (create.voice) - price card first.
- model : a 3D model built by Hoola's 3D Studio (Blender, GLB) - no money (model calls only).
- her own files: PNG / JPEG / WAV / OGG / GLB, checked by their bytes, never trusted by their name.

Checks in code (`check_file`): it decodes, exact size, transparent edges for sprites / icons / ui, not blank, bytes
under the kind's budget, palette share, audio length and level. An asset version that fails is never approved.
In the game: approved assets are copied into the project at every build (`res://assets/<key>.<ext>`) with
`hoola_assets.gd` = the HoolaAssets autoload (HoolaAssets.tex / sound / play / scene / has), written by Hoola. Keys
follow the Bible: an enemy `red_bat` has the sprite `red_bat`, a level `l1` the background `bg_l1`. AI-made assets are
marked in the PNG / file metadata and listed in HoolaAssets.CREDITS, which the game shows on its title screen."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session
from . import service as G
from . import sfx as SFX

log = logging.getLogger("santosh.gamedesk")
USD_INR = 88
KINDS: dict[str, dict[str, Any]] = {
    "sprite": {"label": "Sprite", "media": "image", "alpha": True, "size": (128, 128), "max_side": 512, "budget_kb": 200,
               "cost_inr": 3, "source": "photogen"},
    "icon": {"label": "Icon", "media": "image", "alpha": True, "size": (96, 96), "max_side": 256, "budget_kb": 80,
             "cost_inr": 3, "source": "photogen"},
    "ui": {"label": "UI piece", "media": "image", "alpha": True, "size": (256, 96), "max_side": 1024, "budget_kb": 150,
           "cost_inr": 3, "source": "photogen"},
    "background": {"label": "Background", "media": "image", "alpha": False, "size": (720, 1280), "max_side": 2048,
                   "budget_kb": 900, "cost_inr": 3, "source": "photogen"},
    "sfx": {"label": "Sound effect", "media": "audio", "len": (0.02, 3.0), "budget_kb": 200, "cost_inr": 0, "source": "synth"},
    "music": {"label": "Music", "media": "audio", "len": (10.0, 240.0), "budget_kb": 4000,
              "cost_inr": round(0.08 * USD_INR), "source": "lyria"},
    "voice": {"label": "Voice line", "media": "audio", "len": (0.2, 30.0), "budget_kb": 1500, "cost_inr": 1, "source": "tts"},
    "model": {"label": "3D model", "media": "model", "budget_kb": 8000, "cost_inr": 0, "source": "blender"},
}
PAID = {k for k, v in KINDS.items() if v["cost_inr"]}
MAX_ASSETS = 300
KEY = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MAGENTA = (255, 0, 255)
CREDIT = "Some art, sound, music or voice in this game was made with AI (Hoola)."
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="gameassets")


class AssetError(G.GameError):
    pass


class GameAsset(Base):
    __tablename__ = "game_assets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ga"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(16), default="sprite")
    words: Mapped[str] = mapped_column(Text, default="")
    spec: Mapped[dict] = mapped_column(JSON, default=dict)         # size, quality, palette_lock, preset, seed, voice, text...
    status: Mapped[str] = mapped_column(String(12), default="priced")   # priced|making|draft|approved|rejected|failed
    version: Mapped[int] = mapped_column(Integer, default=0)        # newest made version
    approved: Mapped[int] = mapped_column(Integer, default=0)       # the version inside the game (0 = none)
    history: Mapped[list] = mapped_column(JSON, default=list)       # [{v, file, at, source, meta, checks, cost_inr}]
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)     # the price card for the NEXT making
    spent_inr: Mapped[float] = mapped_column(Float, default=0.0)
    job: Mapped[str] = mapped_column(String(40), default="")        # a 3D Studio project id for kind=model
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameAsset.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _dir(tenant: str, studio_id: str, key: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "assets" / studio_id / key


def _ext(kind: str, v: dict) -> str:
    return v.get("file", "").rsplit(".", 1)[-1] if v.get("file") else {"sfx": "wav", "music": "ogg", "voice": "wav", "model": "glb"}.get(kind, "png")


# ---------------------------------------------------------------- signed preview links
def _sig(aid: str, v: int, exp: int) -> str:
    st = get_settings()
    key = st.secret_key or st.api_key or "hoola-assets"
    return hmac.new(f"gas:{key}".encode(), f"{aid}/{v}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def file_url(aid: str, v: int, days: int = 7) -> str:
    exp = int(time.time()) + days * 86400
    return f"/api/gamestudio/asset/{aid}/{v}?exp={exp}&sig={_sig(aid, v, exp)}"


def file_for(aid: str, v: int, exp: int, sig: str) -> tuple[Path | None, str]:
    if exp < time.time() or not hmac.compare_digest(_sig(aid, v, exp), sig or ""):
        return None, ""
    ensure_table()
    with session() as s:
        a = s.get(GameAsset, aid)
        if a is None:
            return None, ""
        h = next((x for x in a.history or [] if x.get("v") == v), None)
        if not h:
            return None, ""
        p = _dir(a.tenant_id, a.studio_id, a.key) / h["file"]
    media = {"png": "image/png", "wav": "audio/wav", "ogg": "audio/ogg", "glb": "model/gltf-binary"}.get(p.suffix[1:], "application/octet-stream")
    return (p, media) if p.is_file() else (None, "")


# ---------------------------------------------------------------- views
def view(a: GameAsset) -> dict[str, Any]:
    cur = next((x for x in a.history or [] if x.get("v") == a.version), {}) if a.version else {}
    return {"id": a.id, "key": a.key, "kind": a.kind, "label": KINDS.get(a.kind, {}).get("label", a.kind), "words": a.words,
            "spec": a.spec or {}, "status": a.status, "version": a.version, "approved": a.approved,
            "cost_inr": a.cost_inr, "spent_inr": round(a.spent_inr or 0, 2), "error": a.error, "job": a.job,
            "url": file_url(a.id, a.version) if cur else "", "meta": cur.get("meta", {}), "checks": cur.get("checks", {}),
            "source": cur.get("source", ""),
            "history": [{"v": x["v"], "at": x.get("at"), "source": x.get("source"), "ok": not (x.get("checks") or {}).get("errors"),
                         "url": file_url(a.id, x["v"])} for x in reversed(a.history or [])][:10]}


def assets(tenant: str, ref: str) -> dict[str, Any]:
    ensure_table()
    r = _studio(tenant, ref)
    with session() as s:
        rows = s.scalars(select(GameAsset).where(GameAsset.studio_id == r.id).order_by(GameAsset.kind, GameAsset.key)).all()
        for a in rows:
            s.expunge(a)
    items = [view(a) for a in rows]
    waiting = [i for i in items if i["status"] == "priced"]
    return {"studio": r.id, "assets": items, "kinds": {k: {kk: v[kk] for kk in ("label", "media", "cost_inr", "source")}
                                                       for k, v in KINDS.items()},
            "presets": list(SFX.PRESETS), "card": {"items": [{"id": i["id"], "key": i["key"], "kind": i["kind"],
                                                              "cost_inr": i["cost_inr"]} for i in waiting],
                                                   "total_inr": round(sum(i["cost_inr"] for i in waiting), 2)},
            "in_game": sum(1 for i in items if i["approved"]), "spent_inr": round(sum(i["spent_inr"] for i in items), 2),
            "credit": CREDIT}


# ---------------------------------------------------------------- planning (code, from the Bible)
def suggest(tenant: str, ref: str) -> list[dict[str, Any]]:
    """What the game still needs, from the Game Bible: a sprite per character / enemy / item, a background per level,
    the usual sounds, one music track. Keys follow the Bible ids. Nothing is made or priced here."""
    r = _studio(tenant, ref)
    have = {a["key"] for a in assets(tenant, ref)["assets"]}
    out: list[dict[str, Any]] = []
    try:
        from . import bible as B
        data = B.view(tenant, r.id)["data"]
    except Exception:                                   # noqa: BLE001
        data = {}
    ents = (data or {}).get("entities") or {}
    for kind in ("character", "enemy", "item"):
        for e in ents.get(kind) or []:
            if e.get("id") and e["id"] not in have:
                out.append({"key": e["id"], "kind": "sprite" if kind != "item" else "icon",
                            "words": f"{e.get('name', '')}: {e.get('notes') or e.get('bio') or e.get('behaviour') or ''}".strip(" :")})
    for lv in ents.get("level") or []:
        if lv.get("id") and f"bg_{lv['id']}" not in have:
            out.append({"key": f"bg_{lv['id']}", "kind": "background", "words": f"{lv.get('name', '')} {lv.get('notes', '')}".strip()})
    for p in ("jump", "coin", "hit", "powerup", "select"):
        if f"sfx_{p}" not in have:
            out.append({"key": f"sfx_{p}", "kind": "sfx", "words": p, "preset": p})
    if "music_main" not in have:
        out.append({"key": "music_main", "kind": "music", "words": (data.get("meta") or {}).get("genre") or "upbeat game loop"})
    for o in out:
        o["cost_inr"] = KINDS[o["kind"]]["cost_inr"]
    return out[:60]


# ---------------------------------------------------------------- asking for an asset
def _clean_key(key: str, words: str) -> str:
    k = re.sub(r"[^a-z0-9_]+", "_", (key or words or "").lower()).strip("_")[:40]
    if k and not k[0].isalpha():
        k = f"a_{k}"[:40]
    if not KEY.match(k or ""):
        raise AssetError("Asset ka naam (key) chhote angrezi akshar / number / _ mein: jaise red_bat, sfx_jump.")
    return k


def request(tenant: str, ref: str, kind: str, key: str = "", words: str = "", **spec) -> dict[str, Any]:
    """A new asset (or a new version of one): free kinds start at once; paid ones get a PRICE CARD and wait for her tap."""
    ensure_table()
    if kind not in KINDS:
        raise AssetError("kind = " + ", ".join(KINDS))
    words = re.sub(r"\s+", " ", str(words or "")).strip()[:600]
    why = G.problem(words)
    if not why and KINDS[kind]["source"] == "photogen":
        from .. import photogen
        why = photogen.problem(words or key)
    if why:
        raise AssetError(why)
    r = _studio(tenant, ref)
    key = _clean_key(key, words)
    sp = _spec(kind, spec, r)
    with session() as s:
        a = s.scalars(select(GameAsset).where(GameAsset.studio_id == r.id, GameAsset.key == key)).first()
        if a is None:
            n = len(s.scalars(select(GameAsset.id).where(GameAsset.studio_id == r.id)).all())
            if n >= MAX_ASSETS:
                raise AssetError(f"Is game mein {MAX_ASSETS} assets ho gaye.")
            a = GameAsset(tenant_id=tenant, studio_id=r.id, key=key, kind=kind, history=[])
            s.add(a)
        elif a.kind != kind:
            raise AssetError(f"'{key}' pehle se ek {a.kind} hai; doosra naam dijiye.")
        elif a.status in ("making",):
            raise AssetError(f"'{key}' abhi ban raha hai.")
        a.words, a.spec, a.error = words or a.words, sp, ""
        a.cost_inr = float(_price(kind, sp))
        a.status = "priced" if a.cost_inr else "making"
        a.updated_at = now()
        s.flush()
        aid = a.id
        s.expunge(a)
    if a.status == "making":
        _submit(tenant, aid)
    return view(a)


def _spec(kind: str, spec: dict, r) -> dict[str, Any]:
    k = KINDS[kind]
    out: dict[str, Any] = {}
    if k["media"] == "image":
        w, h = k["size"]
        if kind == "background":
            g = G._get(r.tenant_id, r.game_id) if r.game_id else None
            from .template import SIZES
            w, h = SIZES.get(getattr(g, "orientation", "portrait") or "portrait", SIZES["portrait"])
        try:
            w = int(spec.get("w") or spec.get("size") or w)
            h = int(spec.get("h") or spec.get("size") or h) if kind in ("sprite", "icon") or spec.get("h") else h
        except (TypeError, ValueError):
            pass
        side = k["max_side"]
        out["w"], out["h"] = max(16, min(side, w)), max(16, min(side, h))
        out["quality"] = "best" if spec.get("quality") == "best" else "fast"
        out["palette_lock"] = spec.get("palette_lock") if spec.get("palette_lock") in ("off", "check", "strict") else "check"
        out["view"] = re.sub(r"\s+", " ", str(spec.get("view") or ("side view" if kind == "sprite" else "")))[:60]
    elif kind == "sfx":
        pre = spec.get("preset") or (spec.get("words") or "")
        out["preset"] = pre if pre in SFX.PRESETS else "blip"
        try:
            out["seed"] = max(1, min(10 ** 6, int(spec.get("seed") or 1)))
        except (TypeError, ValueError):
            out["seed"] = 1
    elif kind == "music":
        out["mood"] = re.sub(r"\s+", " ", str(spec.get("mood") or ""))[:80]
        out["bpm"] = int(spec.get("bpm") or 0) if str(spec.get("bpm") or "0").isdigit() else 0
    elif kind == "voice":
        out["text"] = re.sub(r"\s+", " ", str(spec.get("text") or ""))[:400]
        out["voice"] = str(spec.get("voice") or "")[:40]
        out["language"] = str(spec.get("language") or "Hindi")[:20]
        if not out["text"]:
            raise AssetError("Voice line ka text dijiye (kya bolna hai).")
    return out


def _price(kind: str, sp: dict) -> float:
    c = KINDS[kind]["cost_inr"]
    if KINDS[kind]["source"] == "photogen" and sp.get("quality") == "best":
        from .. import photogen
        return photogen.COST_INR["best"]
    return c


def spend(tenant: str, ref: str, ids: list[str]) -> dict[str, Any]:
    """ONLY HER TAP (the API's price-card button; the agent tool never calls this): the priced assets start."""
    r = _studio(tenant, ref)
    started = []
    with session() as s:
        for aid in ids or []:
            a = s.get(GameAsset, aid)
            if a is None or a.studio_id != r.id or a.status != "priced":
                continue
            a.status, a.updated_at = "making", now()
            started.append(aid)
    if not started:
        raise AssetError("Koi priced asset nahi chuna.")
    for aid in started:
        _submit(tenant, aid)
    return assets(tenant, ref)


def _submit(tenant: str, aid: str) -> None:
    if os.environ.get("GAME_WORKER", "true").lower() in ("0", "false", "off"):
        return                                         # tests call make() themselves
    _POOL.submit(_make_safe, tenant, aid)


def _make_safe(tenant: str, aid: str) -> None:
    try:
        make(tenant, aid)
    except Exception as e:                             # noqa: BLE001
        log.exception("asset %s", aid)
        _fail(aid, f"andar ki gadbad: {type(e).__name__}")


def _fail(aid: str, err: str) -> None:
    with session() as s:
        a = s.get(GameAsset, aid)
        if a is not None:
            a.status, a.error, a.updated_at = "failed", err[:400], now()


# ---------------------------------------------------------------- making
def _bible(tenant: str, sid: str) -> dict:
    try:
        from . import bible as B
        return B.view(tenant, sid)["data"]
    except Exception:                                   # noqa: BLE001
        return {}


ART = {
    "sprite": "a single game sprite of {what}, {view}, the whole subject in frame and centred, flat cel-shaded 2D game art, "
              "clean bold outline, on a perfectly flat pure magenta (#FF00FF) background with nothing else on it, "
              "no shadow on the ground, no text, no border, no frame",
    "icon": "a single game icon of {what}, centred, bold simple shape that reads at small size, flat 2D game art, on a "
            "perfectly flat pure magenta (#FF00FF) background, no text, no border",
    "ui": "a game user-interface piece: {what}, flat 2D, crisp edges, centred, on a perfectly flat pure magenta (#FF00FF) "
          "background, no text unless asked, no border around the image",
    "background": "a game background scene: {what}, 2D game art, no characters, no text, calm enough that game "
                  "objects on top stay easy to see, the whole frame filled",
}


def art_prompt(kind: str, words: str, sp: dict, bible: dict) -> str:
    style = (bible or {}).get("style") or {}
    meta = (bible or {}).get("meta") or {}
    pal = [c for c in style.get("palette") or [] if isinstance(c, str)]
    p = ART[kind].format(what=words or "the item", view=sp.get("view") or "front view")
    if pal:
        p += f". Use ONLY these colours (and their light / dark shades): {', '.join(pal)}"
        if kind != "background":
            p += " - never magenta in the subject itself"
    if style.get("tone"):
        p += f". Style: {style['tone']}"
    if meta.get("genre"):
        p += f". For a {meta['genre']} game"
    return p + ". Original design, not from any existing game."


def _png(img) -> bytes:
    from PIL import PngImagePlugin
    info = PngImagePlugin.PngInfo()
    info.add_text("Software", "Hoola Studio")
    info.add_text("Comment", "AI-generated game art (Hoola)")
    buf = io.BytesIO()
    img.save(buf, "PNG", pnginfo=info, optimize=True)
    return buf.getvalue()


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def key_out(img, tol: int = 90):
    """Flat magenta -> transparent (soft edge), magenta spill removed from the edge pixels."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            d = abs(r - 255) + g + abs(b - 255)
            if d < tol:
                px[x, y] = (r, g, b, 0)
            elif d < tol * 2:
                k = (d - tol) / tol
                px[x, y] = (r, min(g + int((1 - k) * 40), 255), b, int(a * k))
    return img


def fit(img, w: int, h: int, alpha: bool):
    from PIL import Image
    if alpha:
        bb = img.getbbox()
        if bb:
            img = img.crop(bb)
        iw, ih = img.size
        s = min((w * 0.94) / max(1, iw), (h * 0.94) / max(1, ih))
        img = img.resize((max(1, int(iw * s)), max(1, int(ih * s))), Image.LANCZOS)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(img, ((w - img.size[0]) // 2, (h - img.size[1]) // 2), img)
        return canvas
    iw, ih = img.size                                   # cover-crop to the exact size
    s = max(w / iw, h / ih)
    img = img.convert("RGB").resize((max(w, int(iw * s + 0.5)), max(h, int(ih * s + 0.5))), Image.LANCZOS)
    x, y = (img.size[0] - w) // 2, (img.size[1] - h) // 2
    return img.crop((x, y, x + w, y + h))


def _shades(pal: list[str]) -> list[tuple[int, int, int]]:
    out = []
    for c in pal:
        r, g, b = _hex(c)
        for f in (0.55, 0.78, 1.0):
            out.append((int(r * f), int(g * f), int(b * f)))
        for f in (0.25, 0.5):
            out.append((int(r + (255 - r) * f), int(g + (255 - g) * f), int(b + (255 - b) * f)))
    return out


def palette_share(img, pal: list[str], dist: int = 60) -> float | None:
    """Share of visible pixels within `dist` of the palette or its shades (sampled). None when there is no palette."""
    if not pal:
        return None
    sh = _shades(pal)
    im = img.convert("RGBA")
    im.thumbnail((96, 96))
    px = list(im.getdata())
    vis = [p for p in px if p[3] > 128]
    if not vis:
        return 0.0
    near = sum(1 for p in vis if min(abs(p[0] - c[0]) + abs(p[1] - c[1]) + abs(p[2] - c[2]) for c in sh) <= dist)
    return round(near / len(vis), 3)


def snap(img, pal: list[str]):
    """palette_lock=strict: every visible pixel becomes its nearest palette shade (a hard style lock)."""
    sh = _shades(pal)
    im = img.convert("RGBA")
    px = im.load()
    cache: dict[tuple, tuple] = {}
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            k = (r >> 3, g >> 3, b >> 3)
            if k not in cache:
                cache[k] = min(sh, key=lambda c: (r - c[0]) ** 2 + (g - c[1]) ** 2 + (b - c[2]) ** 2)
            c = cache[k]
            px[x, y] = (c[0], c[1], c[2], a)
    return im


def make_image(kind: str, words: str, sp: dict, bible: dict, raw: bytes | None = None) -> tuple[bytes, dict]:
    """Picture engine (or her upload) -> the exact game file. Returns (png, meta)."""
    from PIL import Image
    k = KINDS[kind]
    model = "upload"
    if raw is None:
        from .. import photogen
        aspect = "1:1" if kind in ("sprite", "icon") else ("9:16" if sp["h"] > sp["w"] else "16:9") if kind == "background" else "16:9"
        raw, model = photogen.generate(art_prompt(kind, words, sp, bible), None, aspect, sp.get("quality", "fast"))
    img = Image.open(io.BytesIO(raw))
    img.load()
    keyed = None
    if k["alpha"]:
        img = key_out(img) if model != "upload" or img.mode != "RGBA" else img.convert("RGBA")
        h = img.getchannel("A").histogram()
        keyed = round(sum(h[:16]) / max(1, sum(h)), 3)   # how much background the keying actually removed
    out = fit(img, sp["w"], sp["h"], k["alpha"])
    pal = [c for c in ((bible or {}).get("style") or {}).get("palette") or [] if isinstance(c, str)]
    if sp.get("palette_lock") == "strict" and pal:
        out = snap(out, pal)
    return _png(out), {"model": model, "w": sp["w"], "h": sp["h"], **({"keyed": keyed} if keyed is not None else {})}


def _ogg(data: bytes, src_ext: str, loop_fade: bool = False) -> tuple[bytes, str]:
    """Any audio -> OGG Vorbis for the web (ffmpeg); without ffmpeg the original bytes stay (a warning in the checks)."""
    if not shutil.which("ffmpeg"):
        return data, src_ext
    with tempfile.TemporaryDirectory(prefix="hoola-aud-") as d:
        src, dst = Path(d) / f"in.{src_ext}", Path(d) / "out.ogg"
        src.write_bytes(data)
        af = ["-af", "afade=t=in:d=0.3,areverse,afade=t=in:d=1.5,areverse"] if loop_fade else []
        try:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), *af, "-ac", "2", "-ar", "44100",
                            "-c:a", "libvorbis", "-q:a", "4", str(dst)], timeout=180, check=True)
            return dst.read_bytes(), "ogg"
        except Exception as e:                          # noqa: BLE001
            log.info("asset ogg: %s", e)
            return data, src_ext


def make(tenant: str, aid: str) -> dict[str, Any]:
    """Make the next version of one asset (status making). Runs in the asset pool (tests call it directly)."""
    from .. import usage
    with session() as s:
        a = s.get(GameAsset, aid)
        if a is None or a.tenant_id != tenant or a.status != "making":
            raise AssetError("Yeh asset banne ki line mein nahi.")
        s.expunge(a)
    k = KINDS[a.kind]
    bible = _bible(tenant, a.studio_id)
    sp = a.spec or {}
    meta: dict[str, Any] = {}
    try:
        with usage.scope(tenant, "game"):
            if k["media"] == "image":
                data, meta = make_image(a.kind, a.words or a.key.replace("_", " "), sp, bible)
                ext = "png"
            elif a.kind == "sfx":
                data, meta = SFX.make(sp.get("preset", "blip"), int(sp.get("seed") or 1))
                ext = "wav"
            elif a.kind == "music":
                from ..create import service as CR
                res = asyncio.run(CR.song(brief=f"{a.words}. Instrumental only, no vocals, a seamless loop for a video game",
                                          genre=(bible.get("meta") or {}).get("genre", "") or "game music",
                                          vocals="instrumental", mood=sp.get("mood", ""), bpm=sp.get("bpm", 0), seconds=60))
                data, ext = _ogg(res["bytes"], res.get("ext", ".mp3").lstrip("."), loop_fade=True)
                meta = {"model": res.get("model")}
            elif a.kind == "voice":
                from ..create import service as CR
                res = asyncio.run(CR.voice(sp.get("text", ""), sp.get("voice", ""), sp.get("language", "Hindi"), tenant=tenant))
                data, ext = res["bytes"], "wav"
                meta = {"voice": res.get("voice")}
            else:                                       # model: Hoola's 3D Studio builds it, we collect the GLB
                return _start_model(tenant, a)
    except AssetError:
        raise
    except Exception as e:                              # noqa: BLE001
        msg = str(e)[:300]
        _fail(aid, f"nahi ban paya: {msg}")
        raise AssetError(f"'{a.key}' nahi ban paya: {msg}") from None
    return _store(tenant, aid, data, ext, meta, source=k["source"], cost=a.cost_inr)


def _store(tenant: str, aid: str, data: bytes, ext: str, meta: dict, source: str, cost: float = 0.0) -> dict[str, Any]:
    with session() as s:
        a = s.get(GameAsset, aid)
        bible = _bible(tenant, a.studio_id)
        n = (a.version or 0) + 1
        d = _dir(tenant, a.studio_id, a.key)
        d.mkdir(parents=True, exist_ok=True)
        name = f"v{n}.{ext}"
        (d / name).write_bytes(data)
        checks, more = check_file(a.kind, data, ext, a.spec or {}, bible)
        if KINDS[a.kind].get("alpha") and meta.get("keyed") is not None and meta["keyed"] < 0.03:
            checks["errors"].insert(0, "no transparent background (the flat backdrop was not found, so nothing was removed)")
        meta = {**meta, **more}
        a.history = ((a.history or []) + [{"v": n, "file": name, "at": now().isoformat(), "source": source, "meta": meta,
                                           "checks": checks, "cost_inr": cost}])[-20:]
        a.version, a.status, a.error = n, "draft" if not checks["errors"] else "failed", "; ".join(checks["errors"][:3])
        a.spent_inr = (a.spent_inr or 0) + (cost or 0)
        a.cost_inr = 0.0 if a.kind not in PAID else float(_price(a.kind, a.spec or {}))
        a.updated_at = now()
        s.flush()
        s.expunge(a)
    return view(a)


def _start_model(tenant: str, a: GameAsset) -> dict[str, Any]:
    from ..blender3d import service as B3
    st = _studio(tenant, a.studio_id)
    v = B3.start(tenant, st.conversation_id or "", f"A game-ready 3D model: {a.words}. Low poly (under 5,000 triangles), "
                 "origin at the base, real-world size, simple materials, one object.", {"exports": ["glb"]},
                 title=f"{st.title}: {a.key}")
    with session() as s:
        row = s.get(GameAsset, a.id)
        row.job, row.updated_at = v["id"], now()
        s.flush()
        s.expunge(row)
    return view(row)


def collect_models(tenant: str, ref: str = "") -> int:
    """3D Studio jobs that finished -> their GLB becomes the asset's next version (called by views and the worker)."""
    from ..blender3d import service as B3
    ensure_table()
    q = select(GameAsset).where(GameAsset.tenant_id == tenant, GameAsset.kind == "model", GameAsset.status == "making")
    with session() as s:
        rows = s.scalars(q).all()
        for a in rows:
            s.expunge(a)
    done = 0
    for a in rows:
        if not a.job:
            continue
        try:
            v = B3.get(tenant, a.job)
        except Exception:                               # noqa: BLE001
            continue
        if v["status"] in ("failed", "cancelled"):
            _fail(a.id, "3D Studio: " + (v.get("error") or "nahi bana"))
            continue
        glb = (v.get("exports") or {}).get("glb") or {}
        if v["status"] == "done" and glb.get("name") and not glb.get("too_big"):
            p = B3._pdir(tenant, a.job) / f"v{v['version']}" / glb["name"]
            if p.is_file():
                _store(tenant, a.id, p.read_bytes(), "glb", {"tris": (v.get("stats") or {}).get("tris"),
                                                             "b3d": v.get("number")}, source="blender")
                done += 1
    return done


def upload(tenant: str, ref: str, kind: str, key: str, data_b64: str, words: str = "") -> dict[str, Any]:
    """Her own file, checked by its bytes; images are fitted to the kind's size like a made one."""
    ensure_table()
    if kind not in KINDS:
        raise AssetError("kind = " + ", ".join(KINDS))
    try:
        data = base64.b64decode(data_b64 or "", validate=False)
    except Exception:                                   # noqa: BLE001
        raise AssetError("File padhi nahi gayi.") from None
    if not data or len(data) > 12 * 1024 * 1024:
        raise AssetError("File 12 MB tak.")
    r = _studio(tenant, ref)
    key = _clean_key(key, words)
    media = KINDS[kind]["media"]
    sig = data[:12]
    if media == "image" and not (sig.startswith(b"\x89PNG") or sig.startswith(b"\xff\xd8")):
        raise AssetError("Picture PNG ya JPEG honi chahiye.")
    if media == "audio" and not (sig.startswith(b"RIFF") or sig.startswith(b"OggS") or sig.startswith(b"ID3") or sig[:2] == b"\xff\xfb"):
        raise AssetError("Awaaz WAV, OGG ya MP3 honi chahiye.")
    if media == "model" and not sig.startswith(b"glTF"):
        raise AssetError("3D model GLB (glTF binary) hona chahiye.")
    sp = _spec(kind, {"text": "her voice"} if kind == "voice" else {}, r)
    with session() as s:
        a = s.scalars(select(GameAsset).where(GameAsset.studio_id == r.id, GameAsset.key == key)).first()
        if a is None:
            a = GameAsset(tenant_id=tenant, studio_id=r.id, key=key, kind=kind, history=[], words=words[:600])
            s.add(a)
        elif a.kind != kind:
            raise AssetError(f"'{key}' pehle se ek {a.kind} hai.")
        a.spec, a.status, a.cost_inr = sp, "making", 0.0
        s.flush()
        aid = a.id
    if media == "image":
        png, meta = make_image(kind, words, sp, _bible(tenant, r.id), raw=data)
        return _store(tenant, aid, png, "png", meta, source="her upload")
    if media == "audio":
        ext = "wav" if sig.startswith(b"RIFF") else "ogg" if sig.startswith(b"OggS") else "mp3"
        if ext == "mp3":
            data, ext = _ogg(data, "mp3")
            if ext == "mp3":
                _fail(aid, "MP3 ko OGG banane ke liye server par ffmpeg chahiye")
                raise AssetError("MP3 ko OGG banane ke liye server par ffmpeg chahiye; WAV ya OGG bhejiye.")
        return _store(tenant, aid, data, ext, {}, source="her upload")
    return _store(tenant, aid, data, "glb", {}, source="her upload")


# ---------------------------------------------------------------- checks (code)
def _wav_info(data: bytes) -> tuple[float, float]:
    import array
    with wave.open(io.BytesIO(data)) as w:
        n, rate, width, ch = w.getnframes(), w.getframerate(), w.getsampwidth(), w.getnchannels()
        frames = w.readframes(min(n, rate * 30))
    dur = n / float(rate or 1)
    if width != 2:
        return dur, 0.0
    a = array.array("h", frames)
    peak = max((abs(x) for x in a), default=0) / 32768.0
    return dur, peak


def _ogg_seconds(data: bytes) -> float | None:
    if not shutil.which("ffprobe"):
        return None
    with tempfile.NamedTemporaryFile(suffix=".ogg") as f:
        f.write(data)
        f.flush()
        try:
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f.name],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
            return float(out)
        except Exception:                               # noqa: BLE001
            return None


def check_file(kind: str, data: bytes, ext: str, sp: dict, bible: dict) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Every rule of a game file, in code. errors = never approved; warnings = shown."""
    k = KINDS[kind]
    errors: list[str] = []
    warns: list[str] = []
    meta: dict[str, Any] = {"bytes": len(data)}
    if len(data) > k["budget_kb"] * 1024:
        (errors if len(data) > k["budget_kb"] * 1024 * 2 else warns).append(
            f"{len(data) // 1024} KB is over the {k['budget_kb']} KB budget for a {k['label'].lower()}")
    if k["media"] == "image":
        from PIL import Image
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception:                               # noqa: BLE001
            return {"errors": ["the picture does not open"], "warnings": []}, meta
        meta["w"], meta["h"] = img.size
        if img.size != (sp.get("w"), sp.get("h")):
            errors.append(f"size {img.size[0]}x{img.size[1]} is not the asked {sp.get('w')}x{sp.get('h')}")
        rgba = img.convert("RGBA")
        alpha = rgba.getchannel("A")
        hist = alpha.histogram()
        total = sum(hist) or 1
        cover = 1 - hist[0] / total
        meta["cover"] = round(cover, 3)
        if k["alpha"]:
            w, h = rgba.size
            edge = [alpha.getpixel((x, 0)) for x in range(w)] + [alpha.getpixel((x, h - 1)) for x in range(w)] + \
                   [alpha.getpixel((0, y)) for y in range(h)] + [alpha.getpixel((w - 1, y)) for y in range(h)]
            clear = sum(1 for v in edge if v < 16) / max(1, len(edge))
            meta["clear_edges"] = round(clear, 3)
            if cover < 0.04:
                errors.append("almost nothing is visible (the picture is empty after removing the background)")
            elif cover > 0.97:
                errors.append("no transparent background (the background was not removed)")
            if clear < 0.85:
                warns.append(f"only {round(clear * 100)}% of the edge is transparent: the subject may be cut off")
        else:
            ext_ = rgba.convert("L").getextrema()
            if ext_[1] - ext_[0] < 12:
                errors.append("the picture is one flat colour")
        pal = [c for c in ((bible or {}).get("style") or {}).get("palette") or [] if isinstance(c, str)]
        share = palette_share(rgba, pal)
        meta["palette_share"] = share
        if share is None:
            warns.append("the Game Bible has no palette, so the style could not be checked")
        elif sp.get("palette_lock") != "off" and share < 0.5:
            warns.append(f"only {round(share * 100)}% of it uses the Bible palette (style may not match)")
    elif k["media"] == "audio":
        dur: float | None = None
        if ext == "wav":
            try:
                dur, peak = _wav_info(data)
                meta["peak"] = round(peak, 3)
                if peak < 0.05:
                    errors.append("the sound is (almost) silent")
                if peak > 0.999:
                    warns.append("the sound clips (too loud)")
            except Exception:                           # noqa: BLE001
                return {"errors": ["the sound does not open"], "warnings": []}, meta
        elif ext == "ogg":
            if not data.startswith(b"OggS"):
                errors.append("not an OGG file")
            dur = _ogg_seconds(data)
        else:
            warns.append(f"{ext.upper()} is not the web format (OGG / WAV); ffmpeg was not there to convert it")
        if dur is None:
            warns.append("the length could not be measured")
        else:
            meta["seconds"] = round(dur, 2)
            lo, hi = k["len"]
            if not lo <= dur <= hi:
                errors.append(f"{round(dur, 2)} s is outside {lo}-{hi} s for a {k['label'].lower()}")
    else:
        if not data.startswith(b"glTF"):
            errors.append("not a GLB (glTF binary) file")
    return {"errors": errors, "warnings": warns}, meta


# ---------------------------------------------------------------- her OK
def approve(tenant: str, ref: str, key: str, version: int = 0) -> dict[str, Any]:
    r = _studio(tenant, ref)
    with session() as s:
        a = s.scalars(select(GameAsset).where(GameAsset.studio_id == r.id, GameAsset.key == key)).first()
        if a is None:
            raise AssetError(f"'{key}' nahi mila.")
        v = int(version or a.version)
        h = next((x for x in a.history or [] if x.get("v") == v), None)
        if not h:
            raise AssetError("Woh version nahi mila.")
        if (h.get("checks") or {}).get("errors"):
            raise AssetError("Is version ki jaanch fail hai: " + "; ".join(h["checks"]["errors"][:2]))
        a.approved, a.status, a.updated_at = v, "approved", now()
        s.flush()
        s.expunge(a)
    from . import studio as S
    S._decide(r, f"Asset {a.key} v{v} OK ({a.kind})", a.words[:200], by="her")
    return view(a)


def reject(tenant: str, ref: str, key: str) -> dict[str, Any]:
    r = _studio(tenant, ref)
    with session() as s:
        a = s.scalars(select(GameAsset).where(GameAsset.studio_id == r.id, GameAsset.key == key)).first()
        if a is None:
            raise AssetError(f"'{key}' nahi mila.")
        a.status = "approved" if a.approved else "rejected"
        a.updated_at = now()
        s.flush()
        s.expunge(a)
    return view(a)


def remove(tenant: str, ref: str, key: str) -> None:
    r = _studio(tenant, ref)
    with session() as s:
        a = s.scalars(select(GameAsset).where(GameAsset.studio_id == r.id, GameAsset.key == key)).first()
        if a is None:
            raise AssetError(f"'{key}' nahi mila.")
        if a.status == "making":
            raise AssetError("Abhi ban raha hai.")
        shutil.rmtree(_dir(tenant, r.id, key), ignore_errors=True)
        s.delete(a)


# ---------------------------------------------------------------- into the game
def gd(entries: dict[str, dict], ai_made: bool) -> str:
    """HoolaAssets autoload: written by Hoola from the approved assets, never by the model."""
    from .bible import _gd
    return ('extends Node\n# HoolaAssets (an autoload): the game\'s approved art, sound, music, voice and 3D models.\n'
            '# Written by Hoola Studio; do not edit (approve assets in the Studio and rebuild).\n'
            f'const CREDITS := {json.dumps(CREDIT if ai_made else "")}\n'
            f'const ASSETS := {_gd(entries)}\n\n'
            'func has(key: String) -> bool:\n\treturn ASSETS.has(key)\n\n'
            'func tex(key: String) -> Texture2D:\n\tif not ASSETS.has(key):\n\t\treturn null\n'
            '\treturn load(String(ASSETS[key]["path"])) as Texture2D\n\n'
            'func sound(key: String) -> AudioStream:\n\tif not ASSETS.has(key):\n\t\treturn null\n'
            '\treturn load(String(ASSETS[key]["path"])) as AudioStream\n\n'
            'func scene(key: String) -> PackedScene:\n\tif not ASSETS.has(key):\n\t\treturn null\n'
            '\treturn load(String(ASSETS[key]["path"])) as PackedScene\n\n'
            'func play(key: String, volume_db: float = 0.0) -> void:\n\tvar s := sound(key)\n\tif s == null:\n\t\treturn\n'
            '\tvar p := AudioStreamPlayer.new()\n\tp.stream = s\n\tp.volume_db = volume_db\n\tadd_child(p)\n'
            '\tp.finished.connect(p.queue_free)\n\tp.play()\n')


def for_game(tenant: str, game_id: str) -> tuple[str, dict[str, Path]] | None:
    """(hoola_assets.gd, {res path inside the project: file on disk}) for the approved assets of this game's project."""
    from . import studio as S
    ensure_table()
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is None:
            return None
        rows = s.scalars(select(GameAsset).where(GameAsset.studio_id == st.id, GameAsset.approved > 0)).all()
        for a in rows:
            s.expunge(a)
    entries: dict[str, dict] = {}
    files: dict[str, Path] = {}
    ai_made = False
    for a in rows:
        h = next((x for x in a.history or [] if x.get("v") == a.approved), None)
        if not h:
            continue
        src = _dir(tenant, st.id, a.key) / h["file"]
        if not src.is_file():
            continue
        rel = f"assets/{a.key}.{h['file'].rsplit('.', 1)[-1]}"
        files[rel] = src
        m = h.get("meta") or {}
        entries[a.key] = {"kind": a.kind, "path": f"res://{rel}", "v": a.approved,
                          **{k: m[k] for k in ("w", "h", "seconds") if k in m}}
        ai_made = ai_made or h.get("source") not in ("her upload", "synth")
    if not entries:
        return None
    return gd(entries, ai_made), files


def apply(tenant: str, ref: str) -> dict[str, Any]:
    """The approved assets into the live game: same code, the files + HoolaAssets, the usual checks (no model call)."""
    r = _studio(tenant, ref)
    if for_game(tenant, r.game_id) is None:
        raise AssetError("Koi approved asset nahi; pehle asset OK kijiye.")
    try:
        from . import bible as B
        bv = B.view(tenant, r.id)["version"]
    except Exception:                                   # noqa: BLE001
        bv = 0
    G.data_build(tenant, r.game_id, bv, words="Assets game mein")
    return assets(tenant, ref)
