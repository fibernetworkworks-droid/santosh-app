"""v0.747 HOOLA INTERACTIVE - the console's own video studio (owner: "a perfect Hoola Interactive page in console,
same as HeyGen, with HyperFrames in it end to end" -> the approved canvas -> "go").

One line in, a finished MP4 out, every real step shown on the way:

    draft(tenant, ask, ...)   the brain writes the film as SCENES (one spoken line + one look each); every number a
                              look shows must be in her own words, else the look is kept EMPTY and marked
                              "needs your numbers" (code decides, not the model) - the film cannot be made until she fills it
    save(tenant, pid, ...)    her edits: scenes, looks, shape, language, avatar, closing line
    make(tenant, pid, ...)    one pollable job over frames.do_avatar_film: voice -> words timed -> drawn with HyperFrames
                              (check first, then render) -> kept. Stop stops at the next step boundary.

Laws (test_v0747_hoola_interactive.py):
  REAL      the stages are real boundaries of the film pipeline, never a timer; an error is the error;
  HERS      prices / numbers / names only from her words or her edits; a missing one blocks the make, never guessed;
  OWNERS    every project, photo and video is tenant-scoped (one JSON per tenant, files under her own folder);
  KEPT      finished videos and avatar photos live in data/interactive/<tenant>/ - the chat file lane sweeps after 24 h;
  ONE       one make at a time per tenant (the renderer itself is one-at-a-time for the whole server);
  CONSENT   a photo avatar needs her yes that it is her or that the person agreed; nothing else is accepted.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("santosh.interactive")

SHAPES = ("talking_head", "product", "reel")
LANGS = {"hi": "Hindi", "en": "English", "mr": "Marathi", "gu": "Gujarati", "ta": "Tamil", "te": "Telugu",
         "bn": "Bengali", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi"}
MAX_SCENES = 12
MAX_SAY = 300
MAX_PROJECTS = 60
MAX_VIDEOS = 40
MAX_AVATARS = 12
PHOTO_EXT = (".png", ".jpg", ".jpeg", ".webp")
NUMBER_LOOKS = ("big_number", "price", "bar_chart")

_LOCK = threading.RLock()
_JOBS: dict[str, dict[str, Any]] = {}

# the make job's steps, in order - each one a real boundary of frames.do_avatar_film (+ our own save)
STEPS = [("voice", "Speaking the script"), ("align", "Lining words up to the voice"),
         ("draw", "Checking and drawing the scenes"), ("save", "Keeping the video"), ("done", "Ready")]


class StudioError(Exception):
    pass


# ------------------------------------------------------------------ storage ---
def _root() -> Path:
    p = Path("data") / "interactive"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe(tenant: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(tenant or "default"))[:64] or "default"


def _home(tenant: str) -> Path:
    p = _root() / _safe(tenant)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _db(tenant: str) -> Path:
    return _home(tenant) / "studio.json"


def _load(tenant: str) -> dict[str, Any]:
    p = _db(tenant)
    if not p.is_file():
        return {"projects": [], "avatars": []}
    try:
        d = json.loads(p.read_text("utf-8"))
        if not isinstance(d, dict):
            raise ValueError
        d.setdefault("projects", [])
        d.setdefault("avatars", [])
        return d
    except Exception:
        log.warning("interactive studio file unreadable for %s - starting empty", _safe(tenant))
        return {"projects": [], "avatars": []}


def _store(tenant: str, d: dict[str, Any]) -> None:
    p = _db(tenant)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(p)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _find(d: dict[str, Any], pid: str) -> dict[str, Any]:
    for p in d["projects"]:
        if p["id"] == pid:
            return p
    raise StudioError("This video was not found.")


def video_path(tenant: str, pid: str) -> Path:
    return _home(tenant) / "videos" / f"{re.sub(r'[^A-Za-z0-9_-]', '', pid)}.mp4"


def photo_path(tenant: str, aid: str) -> Path | None:
    d = _load(tenant)
    for a in d["avatars"]:
        if a["id"] == aid:
            p = _home(tenant) / "avatars" / a["photo"]
            return p if p.is_file() else None
    return None


# ------------------------------------------------------------------ avatars ---
def add_avatar(tenant: str, name: str, file_path: str, lang: str = "hi", consent: bool = False,
               filename: str = "") -> dict[str, Any]:
    """A photo avatar: her picture (or a person who agreed), shown beside the words. Consent is a hard gate."""
    name = re.sub(r"\s+", " ", str(name or "").strip())[:40]
    if not name:
        raise StudioError("Give the avatar a name.")
    if not consent:
        raise StudioError("Hoola only uses a face with consent: tick that this is you, or that the person agreed.")
    src = Path(file_path)
    ext = (Path(filename).suffix or src.suffix).lower()   # chat-lane files are stored without an extension
    if ext == ".jpeg":
        ext = ".jpg"
    if ext not in PHOTO_EXT:
        raise StudioError("The avatar must be a photo (png, jpg or webp).")
    head = src.read_bytes()[:12]
    if not (head.startswith(b"\x89PNG") or head.startswith(b"\xff\xd8") or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")):
        raise StudioError("That file is not a real photo.")
    with _LOCK:
        d = _load(tenant)
        if len(d["avatars"]) >= MAX_AVATARS:
            raise StudioError(f"You already have {MAX_AVATARS} avatars - remove one first.")
        aid = "av_" + uuid.uuid4().hex[:10]
        folder = _home(tenant) / "avatars"
        folder.mkdir(exist_ok=True)
        shutil.copyfile(src, folder / f"{aid}{ext}")
        row = {"id": aid, "name": name, "kind": "photo", "photo": f"{aid}{ext}",
               "lang": lang if lang in LANGS else "hi", "consent_at": _now_iso(), "created": _now_iso()}
        d["avatars"].insert(0, row)
        _store(tenant, d)
    return row


def remove_avatar(tenant: str, aid: str) -> bool:
    with _LOCK:
        d = _load(tenant)
        keep = [a for a in d["avatars"] if a["id"] != aid]
        if len(keep) == len(d["avatars"]):
            raise StudioError("This avatar was not found.")
        gone = next(a for a in d["avatars"] if a["id"] == aid)
        (_home(tenant) / "avatars" / gone["photo"]).unlink(missing_ok=True)
        d["avatars"] = keep
        for p in d["projects"]:
            if p.get("avatar_id") == aid:
                p["avatar_id"] = ""
        _store(tenant, d)
    return True


# ------------------------------------------------------------------ scenes ---
def _digits(s: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", str(s or "").replace(",", "")))


def _look_numbers(look: dict[str, Any]) -> set[str]:
    k = look.get("kind")
    if k == "big_number":
        return _digits(look.get("value", ""))
    if k == "price":
        return _digits(look.get("new", "")) | _digits(look.get("old", ""))
    if k == "bar_chart":
        out: set[str] = set()
        for b in look.get("bars") or []:
            out |= _digits(b.get("value", ""))
        return out
    return set()


def clean_scene(sc: Any, her_words: str, trust_numbers: bool) -> dict[str, Any]:
    """One scene, shaped for the page. trust_numbers=False (a model draft): a number she never wrote is removed and
    the look waits for her ("needs your numbers"). trust_numbers=True: her own edit."""
    sc = sc if isinstance(sc, dict) else {}
    say = re.sub(r"\s+", " ", str(sc.get("say") or "").strip())[:MAX_SAY]
    look = sc.get("look") if isinstance(sc.get("look"), dict) else {}
    kind = str(look.get("kind") or "none")
    allowed = ("none", "title", "big_number", "price", "bar_chart", "lower_third")
    if kind not in allowed:
        kind = "none"
    lk: dict[str, Any] = {"kind": kind}
    for k in ("text", "value", "label", "new", "old", "title", "sub", "unit"):
        if look.get(k):
            lk[k] = re.sub(r"\s+", " ", str(look[k]).strip())[:60]
    if kind == "bar_chart":
        lk["bars"] = [{"label": re.sub(r"\s+", " ", str(b.get("label") or ""))[:16], "value": str(b.get("value") or "")[:16]}
                      for b in (look.get("bars") or [])[:6] if isinstance(b, dict)]
    needs = ""
    if kind in NUMBER_LOOKS:
        nums = _look_numbers(lk)
        given = _digits(her_words)
        if not nums or (not trust_numbers and not nums <= given):
            for k in ("value", "new", "old"):
                lk.pop(k, None)
            if kind == "bar_chart":
                lk["bars"] = [{"label": b["label"], "value": ""} for b in lk.get("bars") or []] or \
                             [{"label": "", "value": ""}, {"label": "", "value": ""}]
            needs = "Needs your numbers"
    return {"say": say, "look": lk, "needs": needs}


def _her_words(p: dict[str, Any]) -> str:
    return " ".join([p.get("ask", "")] + [str(x) for x in p.get("facts", [])])


_SYSTEM = """You write short business videos for an Indian small-business owner. Hoola speaks every line in her avatar's
voice and draws each scene with a look. Write the film as scenes: ONE short spoken line per scene (8-22 words, natural,
in the language asked, Hindi in Roman script unless she wrote Devanagari), 3-7 scenes, about 2.6 words a second.
Looks: none | title {text} | big_number {value, label} | price {new, old, label} | bar_chart {bars:[{label, value}], unit}
| lower_third {title, sub}. Use a number ONLY if it is in her words - never invent a price, discount, count, rating or
date. If a scene needs a number she did not give, still pick the look and leave the number empty. Product films may list
items {name, price, note} - prices only from her words. Return ONLY JSON:
{"title": "...", "scenes": [{"say": "...", "look": {...}}], "items": [], "closing": "short call to action or empty"}"""


def _brain(system: str, prompt: str) -> dict[str, Any]:
    from ..videoedit import brain
    return brain.think(system, prompt, max_tokens=2500)


def draft(tenant: str, ask: str, shape: str = "talking_head", lang: str = "hi", aspect: str = "",
          seconds: int = 30, avatar_id: str = "", brand: str = "",
          think: Callable[[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    ask = re.sub(r"\s+", " ", str(ask or "").strip())
    if len(ask) < 6:
        raise StudioError("Say in one line what the video should be about.")
    ask = ask[:1200]
    shape = shape if shape in SHAPES else "talking_head"
    lang = lang if lang in LANGS else "hi"
    seconds = max(10, min(90, int(seconds or 30)))
    prompt = (f"Her words: {ask}\nVideo kind: {shape}\nLanguage: {LANGS[lang]}\nLength: about {seconds} seconds"
              + (f"\nBusiness name: {brand}" if brand else ""))
    out = (think or _brain)(_SYSTEM, prompt)
    scenes_in = out.get("scenes") if isinstance(out, dict) else None
    if not scenes_in or not isinstance(scenes_in, list):
        raise StudioError("Hoola could not write the script just now. Try again in a minute.")
    scenes = [clean_scene(sc, ask, trust_numbers=False) for sc in scenes_in[:MAX_SCENES]]
    scenes = [s for s in scenes if s["say"]]
    if not scenes:
        raise StudioError("Hoola could not write the script just now. Try again in a minute.")
    items = []
    for it in (out.get("items") or [])[:8]:
        if isinstance(it, dict) and str(it.get("name") or "").strip():
            price = str(it.get("price") or "").strip()[:24]
            if price and not _digits(price) <= _digits(ask):
                price = ""                                          # a price she never wrote is never shown
            items.append({"name": str(it["name"]).strip()[:48], "price": price, "note": str(it.get("note") or "").strip()[:60]})
    pid = "iv_" + uuid.uuid4().hex[:10]
    p = {"id": pid, "title": re.sub(r"\s+", " ", str(out.get("title") or ask[:60])).strip()[:80],
         "ask": ask, "facts": [], "shape": shape, "lang": lang,
         "aspect": "9:16" if shape == "reel" else (aspect if aspect in ("16:9", "1:1") else "16:9"),
         "avatar_id": avatar_id, "brand": str(brand or "").strip()[:40],
         "scenes": scenes, "items": items, "closing": str(out.get("closing") or "").strip()[:80],
         "status": "draft", "error": "", "video": None, "created": _now_iso(), "updated": _now_iso()}
    with _LOCK:
        d = _load(tenant)
        d["projects"].insert(0, p)
        d["projects"] = d["projects"][:MAX_PROJECTS]
        _store(tenant, d)
    return p


def save(tenant: str, pid: str, body: dict[str, Any]) -> dict[str, Any]:
    """Her edits. Her own numbers are trusted (it is her film); everything else is checked again."""
    with _LOCK:
        d = _load(tenant)
        p = _find(d, pid)
        if p["status"] == "making":
            raise StudioError("This video is being made - wait for it, or stop it first.")
        if "title" in body:
            p["title"] = re.sub(r"\s+", " ", str(body["title"] or "")).strip()[:80] or p["title"]
        if body.get("shape") in SHAPES:
            p["shape"] = body["shape"]
            p["aspect"] = "9:16" if p["shape"] == "reel" else (p["aspect"] if p["aspect"] != "9:16" else "16:9")
        if body.get("lang") in LANGS:
            p["lang"] = body["lang"]
        if body.get("aspect") in ("16:9", "1:1") and p["shape"] != "reel":
            p["aspect"] = body["aspect"]
        if "avatar_id" in body:
            aid = str(body["avatar_id"] or "")
            if aid and not any(a["id"] == aid for a in d["avatars"]):
                raise StudioError("That avatar was not found.")
            p["avatar_id"] = aid
        for k, cap in (("brand", 40), ("closing", 80)):
            if k in body:
                p[k] = str(body[k] or "").strip()[:cap]
        if isinstance(body.get("scenes"), list):
            sc = [clean_scene(s, _her_words(p), trust_numbers=True) for s in body["scenes"][:MAX_SCENES]]
            p["scenes"] = sc
        if isinstance(body.get("items"), list):
            p["items"] = [{"name": str(i.get("name") or "").strip()[:48], "price": str(i.get("price") or "").strip()[:24],
                           "note": str(i.get("note") or "").strip()[:60]}
                          for i in body["items"][:8] if isinstance(i, dict) and str(i.get("name") or "").strip()]
        if p["status"] in ("failed", "ready"):
            p["status"] = "draft" if p["status"] == "failed" else p["status"]
        p["updated"] = _now_iso()
        _store(tenant, d)
        return p


def remove(tenant: str, pid: str) -> bool:
    with _LOCK:
        if running_for(tenant) == pid:
            raise StudioError("This video is being made - stop it first.")
        d = _load(tenant)
        _find(d, pid)
        d["projects"] = [p for p in d["projects"] if p["id"] != pid]
        video_path(tenant, pid).unlink(missing_ok=True)
        _store(tenant, d)
    return True


def listing(tenant: str) -> dict[str, Any]:
    d = _load(tenant)
    return {"projects": d["projects"], "avatars": d["avatars"], "running": running_for(tenant)}


def project(tenant: str, pid: str) -> dict[str, Any]:
    return _find(_load(tenant), pid)


def problems(p: dict[str, Any]) -> list[str]:
    """What blocks the make, in her words - checked by code before any voice or render."""
    out = []
    if not p["scenes"]:
        out.append("Add at least one scene.")
    for i, s in enumerate(p["scenes"]):
        if not s["say"]:
            out.append(f"Scene {i + 1} has no line to say.")
        if s.get("needs"):
            out.append(f"Scene {i + 1} needs your numbers.")
    if p["shape"] == "product" and not p["items"]:
        out.append("A product film needs at least one product (name and price).")
    return out


def _brand_color(tenant: str) -> dict[str, str]:
    """v0.772: her Brand page colour is drawn into the film (the composition already takes brand.color)."""
    c = str((_load(tenant).get("brand") or {}).get("color") or "")
    return {"color": c} if re.fullmatch(r"#[0-9A-Fa-f]{6}", c) else {}


def spec_for(tenant: str, p: dict[str, Any], silent: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    spec: dict[str, Any] = {"shape": p["shape"], "title": p["title"], "lang": p["lang"], "aspect": p["aspect"],
                            "silent": bool(silent), "brand": {"name": p.get("brand", ""), **_brand_color(tenant)},
                            "scenes": [{"say": s["say"], "look": s["look"]} for s in p["scenes"]]}
    if p["items"]:
        spec["items"] = p["items"]
    if p.get("closing"):
        spec["cta"] = {"text": p["closing"]}
    files: list[dict[str, Any]] = []
    if p.get("avatar_id"):
        ph = photo_path(tenant, p["avatar_id"])
        if ph is not None:
            name = "assets/avatar" + ph.suffix.lower()
            spec["avatar"] = name
            files.append({"name": name, "path": str(ph)})
    return spec, files


# ------------------------------------------------------------------ the make job ---
def running_for(tenant: str) -> str:
    with _LOCK:
        for jid, j in _JOBS.items():
            if j["tenant"] == tenant and not j["done"]:
                return j["pid"]
    return ""


def job_view(tenant: str, pid: str) -> dict[str, Any]:
    with _LOCK:
        j = _JOBS.get(pid)
        if not j or j["tenant"] != tenant:
            p = project(tenant, pid)
            return {"pid": pid, "status": p["status"], "error": p.get("error", ""), "steps": [], "done": True,
                    "lost": p["status"] == "making"}
        now = time.time()
        return {"pid": pid, "status": "making" if not j["done"] else j["status"], "done": j["done"],
                "error": j.get("error", ""), "stopping": j["cancel"].is_set() and not j["done"],
                "elapsed": round((j.get("ended") or now) - j["started"], 1),
                "steps": [{"k": k, "label": lbl, "at": round(j["marks"][k] - j["started"], 1) if k in j["marks"] else None,
                           "detail": j["detail"].get(k, "")} for k, lbl in STEPS],
                "current": j["current"], "silent": j["silent"]}


def _set_status(tenant: str, pid: str, **kw: Any) -> None:
    with _LOCK:
        d = _load(tenant)
        try:
            p = _find(d, pid)
        except StudioError:
            return
        p.update(kw)
        p["updated"] = _now_iso()
        _store(tenant, d)


def _keep_videos(tenant: str) -> None:
    folder = _home(tenant) / "videos"
    vids = sorted(folder.glob("*.mp4"), key=lambda q: q.stat().st_mtime, reverse=True) if folder.is_dir() else []
    for old in vids[MAX_VIDEOS:]:
        old.unlink(missing_ok=True)


def make(tenant: str, pid: str, silent: bool = False,
         film: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    """Start the make job. Refuses (with the reasons) before anything is spent."""
    with _LOCK:
        p = project(tenant, pid)
        busy = running_for(tenant)
        if busy:
            raise StudioError("Another video is being made right now - one at a time." if busy != pid
                              else "This video is already being made.")
        why = problems(p)
        if why:
            raise StudioError(" ".join(why))
        spec, files = spec_for(tenant, p, silent)
        try:
            from ..studio import avatar as av
            av.validate_spec(spec)                        # the composition's own gate, before any voice is spoken
        except Exception as e:
            raise StudioError(str(e))
        job = {"tenant": tenant, "pid": pid, "started": time.time(), "marks": {}, "detail": {}, "current": "voice",
               "done": False, "status": "making", "cancel": threading.Event(), "silent": bool(silent), "ended": None}
        _JOBS[pid] = job
        for k in [k for k, j in _JOBS.items() if j["done"] and time.time() - (j["ended"] or 0) > 3600]:
            _JOBS.pop(k, None)
    _set_status(tenant, pid, status="making", error="")

    def on_stage(stage: str, detail: str = "") -> None:
        with _LOCK:
            if stage not in job["marks"] or stage == job["current"]:
                job["marks"].setdefault(stage, time.time())
            job["current"] = stage
            if detail:
                job["detail"][stage] = detail

    def run() -> None:
        from ..studio import frames
        t0 = time.time()
        try:
            runner = film or frames.do_avatar_film
            res = runner(tenant, spec, files=files, out_name=pid, on_stage=on_stage, cancel=job["cancel"])
            if job["cancel"].is_set():
                raise frames.FramesError("Stopped. Nothing was kept.")
            if not res.get("ok"):
                errs = "; ".join(str(e) for e in (res.get("errors") or [])[:3]) or "the scene check failed"
                raise frames.FramesError(f"The scene check found a problem: {errs}")
            on_stage("save")
            dest = video_path(tenant, pid)
            dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(res["mp4_path"], dest)
            _keep_videos(tenant)
            video = {"size": dest.stat().st_size, "duration": res.get("duration_s") or res.get("total_s"),
                     "scenes": res.get("scenes"), "made_s": round(time.time() - t0, 1),
                     "words_estimated": bool(res.get("words_estimated")), "silent": bool(res.get("silent")),
                     "aspect": spec["aspect"] if spec.get("shape") != "reel" else "9:16", "made": _now_iso()}
            _set_status(tenant, pid, status="ready", error="", video=video)
            on_stage("done")
            with _LOCK:
                job.update(done=True, status="ready", ended=time.time())
        except Exception as e:
            msg = str(e) or e.__class__.__name__
            stopped = job["cancel"].is_set()
            _set_status(tenant, pid, status="draft" if stopped else "failed", error="" if stopped else msg)
            with _LOCK:
                job.update(done=True, status="stopped" if stopped else "failed", error=msg, ended=time.time())
            log.warning("interactive make %s ended: %s", pid, msg)

    threading.Thread(target=run, name=f"interactive-{pid}", daemon=True).start()
    return job_view(tenant, pid)


def stop(tenant: str, pid: str) -> bool:
    with _LOCK:
        j = _JOBS.get(pid)
        if not j or j["tenant"] != tenant or j["done"]:
            raise StudioError("This video is not being made.")
        j["cancel"].set()
    return True


def readiness() -> dict[str, Any]:
    """What the page's status line says: can a film be drawn, can it be spoken."""
    from ..studio import frames
    from . import lab
    import importlib.util
    drawn = bool(frames.configured())
    voice = bool(lab.configured())
    return {"draw": drawn, "voice": voice, "whisper": importlib.util.find_spec("faster_whisper") is not None,
            "busy": bool(frames._render_lock.locked()), "langs": LANGS, "shapes": list(SHAPES)}
