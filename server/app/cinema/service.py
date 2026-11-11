"""HOOLA CINEMA - the work behind the page (owner: "GO BUILD THE WHOLE SET AS HOOLA CINEMA END TO END").

Eight video tools on one paid video engine (kie.ai, the server's own key) plus the Cinema still on Hoola's own picture
engine. What this module holds:

  characters   a person / made-up character / product saved once (1-5 photos) and picked in any tool. A REAL PERSON is
               saved only with her recorded yes ("this is me, or they agreed"); the time of that yes is kept.
  start()      one job: her files are checked by their BYTES (never by name), photos are re-saved as clean JPEGs
               (no hidden data), handed to the engine, and the task is kept on her list. Nothing starts without
               confirm=true (it spends credits), without her rights tick for a source video, or - when a face or body
               is driven and no saved character vouches for it - without her consent tick.
  factory      one brief -> up to six DIFFERENT scenes (written by the model, by rule when no model answers), each
               editable, then one batch she confirms once.
  refresh()    running tasks are read back; a finished video is fetched ONCE through the link wall and kept on her
               Create shelf (My creations), because the engine's link expires.

Limits that refuse before anything is spent: a per-person daily job cap (IST day), 25 MB per file, the model's own
sizes / lengths / seconds (specs.py), and a short list of asks Hoola does not make (nudity, a named real person without
their yes). The rupee cost is NOT known in advance - the engine publishes no price list; the page shows credits left
and what each finished job really used.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import shutil
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import kie, specs

log = logging.getLogger("santosh.cinema")

_LOCK = threading.Lock()
_KEEP = 200
MAX_UPLOAD = 25 * specs.MB
MAX_RESULT = 300 * specs.MB
MAX_CHARACTERS = 40
MAX_PHOTOS = 5
CHAR_KINDS = {"person": "A real person", "made": "A made-up or drawn character", "product": "A product or object"}
_IST = timezone(timedelta(hours=5, minutes=30))
_BAL: dict[str, Any] = {"at": 0.0, "value": None}

_NO = re.compile(r"\b(nude|naked|nsfw|undress\w*|topless|porn\w*|sexual\w*|explicit sex|deep\s?fake\w*|"
                 r"without (?:her|his|their|the person'?s?) (?:consent|permission|knowledge))\b", re.I)


class CinemaError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _s():
    from ..config import get_settings
    return get_settings()


def enabled() -> bool:
    return bool(getattr(_s(), "cinema_page", False))


def _home(tenant: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", tenant or "default")[:80] or "default"
    p = Path(getattr(_s(), "data_dir", "./data") or "./data") / "cinema" / safe
    (p / "photos").mkdir(parents=True, exist_ok=True)
    return p


def _read(tenant: str, name: str) -> list[dict[str, Any]]:
    try:
        d = json.loads((_home(tenant) / name).read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _write(tenant: str, name: str, rows: list[dict[str, Any]]) -> None:
    f = _home(tenant) / name
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


def _id(prefix: str) -> str:
    import secrets
    return f"{prefix}_{secrets.token_hex(6)}"


# ------------------------------------------------------------------ her files, judged by their bytes
def sniff(data: bytes) -> tuple[str, str, str]:
    """(kind, mime, ext) from the first bytes; ('', '', '') when it is none of the kinds Cinema takes."""
    h = data[:16]
    if h.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "image/png", ".png"
    if h.startswith(b"\xff\xd8\xff"):
        return "image", "image/jpeg", ".jpg"
    if h[:4] == b"RIFF" and h[8:12] == b"WEBP":
        return "image", "image/webp", ".webp"
    if h[:4] == b"RIFF" and h[8:12] == b"WAVE":
        return "audio", "audio/wav", ".wav"
    if h[4:8] == b"ftyp":
        brand = h[8:12]
        if brand in (b"M4A ", b"M4B "):
            return "audio", "audio/mp4", ".m4a"
        if brand == b"qt  ":
            return "video", "video/quicktime", ".mov"
        return "video", "video/mp4", ".mp4"
    if h.startswith(b"\x1a\x45\xdf\xa3"):
        return "video", "video/x-matroska", ".mkv"
    if h.startswith(b"ID3") or (len(h) > 1 and h[0] == 0xFF and h[1] in (0xFB, 0xF3, 0xF2)):
        return "audio", "audio/mpeg", ".mp3"
    if h.startswith(b"OggS"):
        return "audio", "audio/ogg", ".ogg"
    if len(h) > 1 and h[0] == 0xFF and h[1] in (0xF1, 0xF9):
        return "audio", "audio/aac", ".aac"
    return "", "", ""


def clean_photo(data: bytes, max_side: int = 3072) -> bytes:
    """A photo re-saved as a plain JPEG: right way up, no transparency, no hidden data, a size every model takes."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
    except Exception:                                   # noqa: BLE001 - not a picture Pillow can read
        raise CinemaError("That photo could not be read. Use a JPG, PNG or WebP picture.") from None
    if min(im.size) < 300:
        raise CinemaError("That photo is too small. The shorter side needs at least 300 pixels.")
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=92)
    return out.getvalue()


def _seconds(data: bytes, ext: str) -> float:
    """Length of a video / audio file, 0 when this server has no ffprobe (then the engine's own check decides)."""
    if not shutil.which("ffprobe"):
        return 0.0
    from ..create import service as cs
    with tempfile.NamedTemporaryFile(suffix=ext) as f:
        f.write(data)
        f.flush()
        try:
            return float(cs.duration(Path(f.name)))
        except Exception:                               # noqa: BLE001 - a length we cannot read is not a refusal
            return 0.0


def _ref_bytes(tenant: str, ref: str) -> tuple[str, bytes]:
    """One of HER files by reference: a character photo (ch:<id>:<n>), a Vocal sound (vo_), a creation (cr_), an upload."""
    ref = str(ref or "").strip()
    if not ref or len(ref) > 120:
        raise CinemaError("A file is missing.")
    try:
        if ref.startswith("ch:"):
            _, cid, n = (ref.split(":") + ["0"])[:3]
            path = character_photo(tenant, cid, int(n))
            return path.name, path.read_bytes()
        if ref.startswith("vo_"):
            from ..vocal import service as vs
            path, _ = vs.audio_file(tenant, ref)
            return path.name, path.read_bytes()
        from ..create import jobs as CJ
        if ref.startswith("cr_"):
            path, it = CJ.item_file(tenant, ref)
            return it.get("file") or path.name, path.read_bytes()
        return CJ._owner_named(tenant, ref)
    except CinemaError:
        raise
    except Exception:                                   # noqa: BLE001 - not hers, or gone
        raise CinemaError("One of the files was not found. Add it again.", 404) from None


def _take(tenant: str, ref: str, want: str, limit: dict[str, Any], label: str) -> tuple[str, bytes, str]:
    """A file ready for the engine: (name, bytes, mime), checked against what the model takes."""
    name, data = _ref_bytes(tenant, ref)
    if len(data) > MAX_UPLOAD:
        raise CinemaError(f"{label}: files up to 25 MB.")
    kind, mime, ext = sniff(data)
    if kind != want:
        raise CinemaError(f"{label}: this is not {'an' if want in ('image', 'audio') else 'a'} {want} file Hoola Cinema can use.")
    if want == "image":
        data, mime, ext = clean_photo(data), "image/jpeg", ".jpg"
    if len(data) > limit["mb"] * specs.MB:
        raise CinemaError(f"{label}: this model takes up to {limit['mb']} MB; the file is {len(data) / specs.MB:.1f} MB.")
    if limit.get("seconds"):
        lo, hi = limit["seconds"]
        sec = _seconds(data, ext)
        if sec and not lo <= sec <= hi + 0.5:
            raise CinemaError(f"{label}: this model takes {lo}-{hi} seconds; the file is {sec:.0f} seconds.")
    return f"{_id('f')}{ext}", data, mime


def screen(text: str) -> None:
    m = _NO.search(text or "")
    if m:
        raise CinemaError(f"Hoola Cinema does not make this (\"{m.group(0)}\"). Change the words and try again.")


# ------------------------------------------------------------------ characters
def characters(tenant: str) -> list[dict[str, Any]]:
    return [c for c in _read(tenant, "characters.json") if c.get("photos")]


def character(tenant: str, cid: str) -> dict[str, Any]:
    c = next((x for x in characters(tenant) if x["id"] == cid), None)
    if not c:
        raise CinemaError("That character was not found.", 404)
    return c


def character_photo(tenant: str, cid: str, n: int = 0) -> Path:
    c = character(tenant, cid)
    if not 0 <= n < len(c["photos"]):
        raise CinemaError("That photo was not found.", 404)
    f = _home(tenant) / "photos" / c["photos"][n]
    if not re.fullmatch(r"ch_[0-9a-f]{12}_\d\.jpg", c["photos"][n]) or not f.is_file():
        raise CinemaError("That photo was not found.", 404)
    return f


def character_add(tenant: str, name: str, kind: str, photos: list[str], consent: bool = False, note: str = "") -> dict[str, Any]:
    name = " ".join((name or "").split())[:40]
    if not name:
        raise CinemaError("Give the character a name.")
    if kind not in CHAR_KINDS:
        raise CinemaError("Say what this is: a real person, a made-up character, or a product.")
    if kind == "person" and consent is not True:
        raise CinemaError("A real person is saved only with their yes. Tick the box: this is you, or the person agreed "
                          "to being used in AI videos.")
    photos = [p for p in (photos or []) if p][:MAX_PHOTOS + 1]
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise CinemaError(f"Add 1 to {MAX_PHOTOS} photos.")
    if len(characters(tenant)) >= MAX_CHARACTERS:
        raise CinemaError(f"You can keep {MAX_CHARACTERS} characters. Remove one first.")
    cid = _id("ch")
    files = []
    for i, ref in enumerate(photos):
        _, data = _ref_bytes(tenant, ref)
        if sniff(data)[0] != "image":
            raise CinemaError("Characters are saved from photos (JPG, PNG or WebP).")
        fn = f"{cid}_{i}.jpg"
        (_home(tenant) / "photos" / fn).write_bytes(clean_photo(data, 2048))
        files.append(fn)
    row = {"id": cid, "name": name, "kind": kind, "photos": files, "note": " ".join((note or "").split())[:200],
           "consent_at": int(time.time()) if kind == "person" else 0, "created": int(time.time())}
    with _LOCK:
        _write(tenant, "characters.json", [row] + _read(tenant, "characters.json"))
    return row


def character_remove(tenant: str, cid: str) -> dict[str, Any]:
    with _LOCK:
        rows = _read(tenant, "characters.json")
        c = next((x for x in rows if x.get("id") == cid), None)
        if not c:
            raise CinemaError("That character was not found.", 404)
        for fn in c.get("photos") or []:
            if re.fullmatch(r"ch_[0-9a-f]{12}_\d\.jpg", fn):
                (_home(tenant) / "photos" / fn).unlink(missing_ok=True)
        _write(tenant, "characters.json", [x for x in rows if x.get("id") != cid])
    return {"removed": cid}


# ------------------------------------------------------------------ jobs
def jobs(tenant: str) -> list[dict[str, Any]]:
    return _read(tenant, "jobs.json")


def _update(tenant: str, jid: str, **fields: Any) -> dict[str, Any] | None:
    with _LOCK:
        rows = jobs(tenant)
        for j in rows:
            if j.get("id") == jid:
                j.update(fields)
                j["updated"] = int(time.time())
                _write(tenant, "jobs.json", rows[:_KEEP])
                return dict(j)
    return None


def today(tenant: str) -> dict[str, int]:
    start = datetime.now(_IST).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    used = sum(1 for j in jobs(tenant) if j.get("created", 0) >= start)
    cap = max(0, int(getattr(_s(), "cinema_daily_jobs", 20) or 0))
    return {"used": used, "cap": cap, "left": max(0, cap - used)}


def _room(tenant: str, n: int = 1) -> None:
    t = today(tenant)
    if t["left"] < n:
        raise CinemaError(f"Today's limit of {t['cap']} Cinema jobs is used ({t['used']} so far). It starts again at "
                          f"midnight; the owner can raise it (CINEMA_DAILY_JOBS).", 429)


def _kie(e: kie.KieError) -> CinemaError:
    return CinemaError(str(e), {"NEED_SETUP": 409, "AUTH": 502, "PAYMENT": 402, "RATE": 429, "BAD_INPUT": 400}.get(e.code, 502))


def _title(text: str, tool: str) -> str:
    t = " ".join((text or "").split())
    label = next((x["label"] for x in specs.TOOLS if x["id"] == tool), "Hoola Cinema")
    return (t[:60] + ("…" if len(t) > 60 else "")) or label


def _row(tool: str, model: str, task: str, title: str, prompt: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    now = int(time.time())
    return {"id": _id("cj"), "task": task, "tool": tool, "model": model, "model_label": specs.MODELS[model]["label"],
            "title": title, "prompt": prompt[:2000], "status": "waiting", "done": False, "ok": False, "error": "",
            "credits": None, "item_id": "", "save_error": "", "created": now, "updated": now, **(extra or {})}


def _keep_rows(tenant: str, rows: list[dict[str, Any]]) -> None:
    with _LOCK:
        _write(tenant, "jobs.json", (rows + jobs(tenant))[:_KEEP])


async def start(tenant: str, body: dict[str, Any]) -> dict[str, Any]:
    """One video job. Every refusal happens BEFORE her files leave the server or a credit is spent."""
    tool = str(body.get("tool") or "")
    if tool not in specs.TOOL_IDS or tool in ("still", "factory"):
        raise CinemaError("Pick a tool.")
    model = str(body.get("model") or "") or specs.models_for(tool)[0]
    m = specs.MODELS.get(model)
    if not m or tool not in m["tools"]:
        raise CinemaError("That model does not do this job. Pick one from the list.")
    if not kie.configured():
        raise CinemaError(kie.SETUP, 409)
    prompt = " ".join(str(body.get("prompt") or "").split())
    if tool == "restyle":
        try:
            prompt = specs.restyle_prompt(str(body.get("look") or ""), prompt)
        except ValueError as e:
            raise CinemaError(str(e)) from None
    elif tool == "animate":
        cam = specs.camera_text(str(body.get("camera") or ""))
        prompt = " ".join(x for x in (prompt, cam) if x)
    screen(prompt + " " + str(body.get("text") or ""))
    images = [str(x) for x in (body.get("images") or []) if x]
    cid = str(body.get("character") or "")
    vouched = False
    if cid:
        c = character(tenant, cid)
        vouched = c["kind"] != "person" or bool(c.get("consent_at"))
        if m.get("image") and not images:
            images = [f"ch:{cid}:0"]
    if tool in specs.VIDEO_TOOLS and body.get("rights") is not True:
        raise CinemaError("Tick the box: this is your video, or you have the right to use it.")
    if tool in specs.FACE_TOOLS and not (vouched and tool != "lipsync") and body.get("consent") is not True:
        raise CinemaError("Tick the box: the person shown is you, or they agreed to being used in AI videos.")
    if body.get("confirm") is not True:
        raise CinemaError("Starting this spends video-engine credits. Confirm it first.")
    _room(tenant)
    if tool == "animate" and not images:
        raise CinemaError("Add the picture first.")
    text = " ".join(str(body.get("text") or "").split())
    audio_ref = str(body.get("audio") or "")
    if m.get("audio") and not audio_ref and not text:
        raise CinemaError("Add an audio file, or type the words to speak.")
    try:
        specs.build(model, prompt=prompt, images=["x"] * len(images), video="x" if body.get("video") else "",
                    audio="x" if m.get("audio") else "", resolution=str(body.get("resolution") or ""),
                    aspect=str(body.get("aspect") or ""), seconds=body.get("seconds"), extras=body.get("extras") or {})
    except ValueError as e:                             # the shape is wrong: refuse before any upload
        raise CinemaError(str(e)) from None
    files: dict[str, Any] = {"images": [], "video": None, "audio": None}
    for i, ref in enumerate(images):
        files["images"].append(_take(tenant, ref, "image", m["image"], f"Photo {i + 1}"))
    if m.get("video"):
        files["video"] = _take(tenant, str(body.get("video") or ""), "video", m["video"], "Source video")
    spoken = ""
    if m.get("audio"):
        if audio_ref:
            files["audio"] = _take(tenant, audio_ref, "audio", m["audio"], "Audio")
        else:
            from ..create import service as cs
            lim = (m["audio"].get("seconds") or (1, 300))[1]
            if len(text) > min(cs.MAX_TEXT, lim * 18):   # about 18 characters a second of speech
                raise CinemaError(f"That is too long for this model (about {lim} seconds of speech). Shorten it or pick another model.")
            try:
                v = await cs.voice(text, str(body.get("voice") or ""), str(body.get("language") or "Hindi"),
                                   str(body.get("style") or "friendly"), 1.0, tenant)
            except cs.CreateError as e:
                raise CinemaError(f"The voice could not be made: {e}") from None
            if len(v["bytes"]) > m["audio"]["mb"] * specs.MB:
                raise CinemaError("The spoken audio is too long for this model. Shorten the words or pick another model.")
            files["audio"] = (f"{_id('f')}.wav", v["bytes"], "audio/wav")
            spoken = text
    try:
        urls = {"images": [await kie.upload(d, n, mt) for n, d, mt in files["images"]],
                "video": await kie.upload(files["video"][1], files["video"][0], files["video"][2]) if files["video"] else "",
                "audio": await kie.upload(files["audio"][1], files["audio"][0], files["audio"][2]) if files["audio"] else ""}
        input_ = specs.build(model, prompt=prompt, images=urls["images"], video=urls["video"], audio=urls["audio"],
                             resolution=str(body.get("resolution") or ""), aspect=str(body.get("aspect") or ""),
                             seconds=body.get("seconds"), avoid=str(body.get("avoid") or ""), sound=body.get("sound"),
                             extras=body.get("extras") or {})
        task = await kie.create(model, input_)
    except kie.KieError as e:
        raise _kie(e) from None
    except ValueError as e:
        raise CinemaError(str(e)) from None
    row = _row(tool, model, task, _title(spoken or body.get("prompt") or "", tool), spoken or prompt,
               {"character": cid, "look": str(body.get("look") or ""), "consent": bool(body.get("consent")) or vouched,
                "rights": bool(body.get("rights"))})
    _keep_rows(tenant, [row])
    return {"started": [row], "today": today(tenant)}


# ------------------------------------------------------------------ content factory
SCENES_SYSTEM = """You write prompts for an AI video model. Given a topic, write {n} DIFFERENT short video scenes about it,
one per line of a JSON array of strings. Each scene: 1-3 sentences, concrete and visual (subject, place, light, action),
one clear idea, no on-screen text. Each scene must take a different angle from the others. Never invent prices, offers,
phone numbers, claims, brand names or real people that are not in the topic. Answer with the JSON array only."""


async def factory_scenes(topic: str, count: int = 3, look: str = "", camera: str = "", platform: str = "") -> dict[str, Any]:
    topic = " ".join((topic or "").split())[:600]
    if len(topic) < 4:
        raise CinemaError("Say what the clips are about.")
    screen(topic)
    n = max(1, min(specs.MAX_BATCH, int(count or 3)))
    tail = " ".join(x for x in (specs._pick(specs.LOOKS, look), specs.camera_text(camera)) if x)
    scenes: list[str] = []
    by = "rule"
    try:
        from ..studio import service as ss
        raw = await asyncio.wait_for(ss._write(SCENES_SYSTEM.format(n=n), f"Topic: {topic}\nFor: {platform or 'short video'}", 1500), 40)
        m = re.search(r"\[.*\]", raw or "", re.S)
        got = json.loads(m.group(0)) if m else []
        scenes = [" ".join(str(x).split())[:700] for x in got if isinstance(x, str) and str(x).strip()][:n]
        if len(scenes) == n:
            by = "model"
            scenes = [f"{s.rstrip('. ')}. {tail}".strip() if tail else s for s in scenes]
    except Exception:                                   # noqa: BLE001 - no model answered: the rule writes them
        log.info("cinema factory: the model did not write the scenes; written by rule")
    if by == "rule":
        scenes = [specs.scene_prompt(topic, i, look, camera) for i in range(n)]
    return {"scenes": scenes, "written_by": by,
            "note": "" if by == "model" else "No writing model answered, so these follow a fixed pattern. Edit them before you make the clips."}


async def factory_start(tenant: str, body: dict[str, Any]) -> dict[str, Any]:
    model = str(body.get("model") or "") or specs.models_for("factory")[0]
    m = specs.MODELS.get(model)
    if not m or "factory" not in m["tools"]:
        raise CinemaError("That model does not do this job. Pick one from the list.")
    if not kie.configured():
        raise CinemaError(kie.SETUP, 409)
    scenes = [" ".join(str(s).split()) for s in (body.get("scenes") or []) if str(s).strip()]
    if not 1 <= len(scenes) <= specs.MAX_BATCH:
        raise CinemaError(f"A batch is 1 to {specs.MAX_BATCH} scenes.")
    for s in scenes:
        screen(s)
    try:
        inputs = [specs.build(model, prompt=s, resolution=str(body.get("resolution") or ""), aspect=str(body.get("aspect") or ""),
                              seconds=body.get("seconds"), sound=body.get("sound")) for s in scenes]
    except ValueError as e:
        raise CinemaError(str(e)) from None
    if body.get("confirm") is not True:
        raise CinemaError(f"Starting {len(scenes)} clips spends video-engine credits. Confirm it first.")
    _room(tenant, len(scenes))
    batch = _id("fb")
    rows, stopped = [], ""
    for s, inp in zip(scenes, inputs):
        try:
            task = await kie.create(model, inp)
        except kie.KieError as e:
            stopped = str(e)                            # stop the batch at the first refusal; what started stays
            if not rows:
                raise _kie(e) from None
            break
        rows.append(_row("factory", model, task, _title(s, "factory"), s, {"batch": batch}))
    _keep_rows(tenant, rows)
    return {"started": rows, "asked": len(scenes), "stopped": stopped, "today": today(tenant)}


# ------------------------------------------------------------------ results
async def _fetch(url: str) -> tuple[str, bytes]:
    """The ONE download seam (tests replace exactly this): the finished file at the engine's link, size-capped."""
    import httpx
    data = b""
    async with httpx.AsyncClient(timeout=180, follow_redirects=True, max_redirects=5) as c:
        async with c.stream("GET", url) as r:
            if r.status_code != 200:
                raise ValueError(f"the file link answered {r.status_code}")
            ctype = (r.headers.get("content-type") or "").split(";")[0].strip()
            async for chunk in r.aiter_bytes():
                data += chunk
                if len(data) > MAX_RESULT:
                    raise ValueError("the file is bigger than 300 MB")
    return ctype, data


async def _save(tenant: str, j: dict[str, Any]) -> dict[str, Any]:
    """Copy the finished video onto her Create shelf, once. Only the link the engine returned for THIS task is fetched,
    through the link wall (public https, no private or local hosts), and it must really be a video."""
    try:
        from ..agent import shilp_tools as SH
        url = SH._ref_url(j.get("url") or "", "result")
        if not url.startswith("https://"):
            raise ValueError("the finished file's link is not https")
        _, data = await _fetch(url)
        kind, _mime, ext = sniff(data)
        if kind != "video":
            raise ValueError("the finished file is not a video")
        from ..create import jobs as CJ
        item = CJ.keep(tenant, "video", j.get("title") or "Hoola Cinema", ext, data,
                       {"source": "Hoola Cinema", "tool": j.get("tool", ""), "model": j.get("model_label", ""),
                        "job": j.get("id", ""), "ai_made": True})
        return _update(tenant, j["id"], item_id=item["id"], save_error="") or j
    except Exception as e:                              # noqa: BLE001 - the link stays on the job
        return _update(tenant, j["id"], save_error=str(e)[:200]) or j


async def check(tenant: str, jid: str) -> dict[str, Any]:
    j = next((x for x in jobs(tenant) if x.get("id") == jid), None)
    if not j:
        raise CinemaError("That job is not on your list.", 404)
    if not j.get("done"):
        try:
            t = await kie.task(j["task"])
        except kie.KieError as e:
            raise _kie(e) from None
        fields: dict[str, Any] = {"status": t["state"]}
        if t["credits"] is not None:
            fields["credits"] = t["credits"]
        if t["state"] == "success":
            fields.update(done=True, ok=bool(t["urls"]), url=(t["urls"] or [""])[0],
                          error="" if t["urls"] else "The engine finished but returned no file.")
        elif t["state"] == "fail":
            fields.update(done=True, ok=False, error=t["error"] or "The engine could not make it.")
        j = _update(tenant, jid, **fields) or j
    if j.get("ok") and not j.get("item_id") and not j.get("save_error") and j.get("url"):
        j = await _save(tenant, j)
    return j


async def refresh(tenant: str, limit: int = 12) -> str:
    """Read back the running jobs (newest first, a few at a time). Returns the first problem, '' when all answered."""
    err = ""
    live = [j["id"] for j in jobs(tenant) if not j.get("done") or (j.get("ok") and not j.get("item_id") and not j.get("save_error"))]
    for jid in live[:limit]:
        try:
            await check(tenant, jid)
        except CinemaError as e:
            err = err or str(e)
            if e.status in (402, 409, 502):
                break
    return err


def remove(tenant: str, jid: str) -> dict[str, Any]:
    with _LOCK:
        rows = jobs(tenant)
        left = [j for j in rows if j.get("id") != jid]
        if len(left) == len(rows):
            raise CinemaError("That job is not on your list.", 404)
        _write(tenant, "jobs.json", left)
    return {"removed": jid}


async def balance(fresh: bool = False) -> float | None:
    if not kie.configured():
        return None
    if not fresh and time.time() - _BAL["at"] < 60:
        return _BAL["value"]
    try:
        _BAL.update(at=time.time(), value=await kie.credits())
    except kie.KieError:
        _BAL.update(at=time.time(), value=None)
    return _BAL["value"]


def _public(j: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in j.items() if k not in ("task", "url")} | {"has_link": bool(j.get("url"))}


def connected() -> dict[str, bool]:
    """What is NOT there yet is said on the page, never hidden."""
    return {"engine": kie.configured(), "rupee_price_before": False, "rupee_meter": False, "ai_mark": False,
            "trained_character": False, "agent_tool": False, "phone": False}


async def overview(tenant: str) -> dict[str, Any]:
    err = await refresh(tenant) if kie.configured() else ""
    from ..create import service as cs
    return {"enabled": True, "key_set": kie.configured(), "setup": "" if kie.configured() else kie.SETUP,
            "credits_left": await balance(), "refresh_error": err, "today": today(tenant),
            "connected": connected(), "voice_ready": bool(cs.ready().get("voice")),
            "voices": cs.voices(), "languages": list(cs.LANGS),
            "character_kinds": [{"id": k, "label": v} for k, v in CHAR_KINDS.items()],
            "characters": [{k: c.get(k) for k in ("id", "name", "kind", "note", "created")} | {"photos": len(c["photos"])}
                           for c in characters(tenant)],
            "jobs": [_public(j) for j in jobs(tenant)], **specs.public()}
