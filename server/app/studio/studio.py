"""From the owner's hoola-studio package (Hoola Video Studio MCP), used inside Hoola as a library (v0.68).
Changes for Hoola: per-owner home, the vedit engine from app.vedit, the AI label can't be switched off, a Devanagari
font by default, signed media links served by Hoola itself, never a path outside the project / her own files.

Hoola Video Studio: idea -> storyboard -> shots (Seedance / Gemini Omni / free animatic) -> review -> final video.

Everything about a project lives in one folder (project.json + media), so work survives restarts and can be
reviewed by a person. Money is guarded: every generation is estimated first and refused if it would exceed the
project budget or the caller's max_cost_usd.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from . import catalog
from .providers import GenRequest, ProviderError, all_providers, fal_image, frame_size

from .. import vedit
from ..vedit import ops as vops

DEFAULT_FONT = str((Path(__file__).resolve().parent.parent / "videoedit" / "fonts" / "NotoSansDevanagari-Bold.ttf"))


CAPTION_STYLES = ("bold", "words", "plain")


def caption_texts(cap: str, dur: float, style: str = "bold", font: str | None = None, aspect: str = "9:16") -> list[dict]:
    """v0.159 Three caption looks: bold (big outlined words), words (2-3 words at a time, saffron, karaoke feel),
    plain (smaller text on a dark strip)."""
    f = {"font": font} if font else {}
    style = style if style in CAPTION_STYLES else "bold"
    if style == "plain":
        return [{"text": cap, "position": "bottom", "start": 0.2, "fade": 0.2, "size": 44, "box": True,
                 "box_color": "black@0.6", **f}]
    if style == "words":
        words = cap.split()
        n = 3 if len(words) > 8 else 2
        chunks = [" ".join(words[i:i + n]) for i in range(0, len(words), n)] or [cap]
        span = max(0.6, float(dur) - 0.4)
        step = span / len(chunks)
        return [{"text": c, "position": "bottom", "start": round(0.2 + i * step, 3), "end": round(0.2 + (i + 1) * step, 3),
                 "size": 72, "box": False, "color": "#FFD27A", **f} for i, c in enumerate(chunks)]
    return [{"text": cap, "position": "bottom", "start": 0.2, "fade": 0.2, "box": False, **f}]


class StudioError(Exception):
    """Message written for the AI (and the person) using the studio."""


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:50] or "project"


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


class Studio:
    def __init__(self, home: str | os.PathLike | None = None, public_url: str = "", label: str = "AI-generated · Hoola"):
        self.home = Path(home or os.environ.get("HOOLA_STUDIO_HOME") or Path.home() / ".hoola-studio").expanduser().resolve()
        (self.home / "projects").mkdir(parents=True, exist_ok=True)
        self.models = catalog.load_models()
        self.providers = all_providers()
        self.sem = asyncio.Semaphore(int(os.environ.get("HOOLA_STUDIO_CONCURRENCY", "3")))
        self.poll_s = float(os.environ.get("HOOLA_STUDIO_POLL_S", "5"))
        self.locks: dict[str, asyncio.Lock] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self.label_ai = label or "AI-generated"            # never empty in Hoola (IT Rules: AI content is labelled)
        self.public_url = (public_url or "").rstrip("/")
        self.on_change = None                              # Hoola: called with the project name after a job / output
        self.speak = None                                  # v0.157 Hoola: (text, language, voice) -> wav path (Gemini TTS)
        self.painter = None                                # v0.157 Hoola: (prompt, aspect, refs) -> image bytes (Nano Banana)
        sf = self.home / "media.secret"
        if not sf.exists():
            sf.write_bytes(os.urandom(32))
            os.chmod(sf, 0o600)
        self._secret = os.environ.get("HOOLA_STUDIO_SECRET", "").encode() or sf.read_bytes()
        if self.public_url:
            self.providers["openrouter"].public_image = self.sign_media

    # ------------------------------------------------------------------ signed media links
    def sign_media(self, path: str, ttl_s: int = 3600) -> str:
        """A short-lived public link to a reference image, for providers that only accept URLs."""
        import base64, hashlib, hmac
        rel = str(Path(path).resolve().relative_to(self.home))
        exp = int(time.time()) + ttl_s
        p64 = base64.urlsafe_b64encode(rel.encode()).decode().rstrip("=")
        sig = hmac.new(self._secret, f"{p64}.{exp}".encode(), hashlib.sha256).hexdigest()[:32]
        return f"{self.public_url}/media/{sig}/{exp}/{p64}{Path(rel).suffix}"

    def verify_media(self, sig: str, exp: str, p64_ext: str) -> Path | None:
        import base64, hashlib, hmac
        p64 = p64_ext.rsplit(".", 1)[0] if "." in p64_ext else p64_ext
        good = hmac.new(self._secret, f"{p64}.{exp}".encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(good, sig) or not exp.isdigit() or int(exp) < time.time():
            return None
        try:
            rel = base64.urlsafe_b64decode(p64 + "=" * (-len(p64) % 4)).decode()
        except Exception:
            return None
        f = (self.home / rel).resolve()
        if self.home not in f.parents or not f.is_file() or f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            return None
        return f

    def inside(self, path: str | None) -> Path | None:
        """Only files inside this owner's studio folder (Hoola copies her own files there first)."""
        if not path:
            return None
        f = Path(path).expanduser().resolve()
        return f if f.is_file() and self.home in f.parents else None

    # ------------------------------------------------------------------ storage
    def pdir(self, name: str) -> Path:
        return self.home / "projects" / slug(name)

    def load(self, name: str) -> dict:
        f = self.pdir(name) / "project.json"
        if not f.exists():
            known = [p.name for p in (self.home / "projects").iterdir() if (p / "project.json").exists()]
            raise StudioError(f"No project '{name}'. Projects: {known}")
        return json.loads(f.read_text(encoding="utf-8"))

    def save(self, p: dict) -> None:
        d = self.pdir(p["name"])
        d.mkdir(parents=True, exist_ok=True)
        p["updated"] = now()
        tmp = d / "project.json.tmp"
        tmp.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, d / "project.json")

    def lock(self, name: str) -> asyncio.Lock:
        return self.locks.setdefault(slug(name), asyncio.Lock())

    async def update(self, name: str, fn) -> dict:
        async with self.lock(name):
            p = self.load(name)
            fn(p)
            self.save(p)
            return p

    # ------------------------------------------------------------------ projects
    def create(self, name: str, aspect: str = "9:16", style: str = "cinematic", language: str = "Hindi",
               budget_usd: float = 10.0, font: str | None = None, brief: str = "") -> dict:
        if self.pdir(name).joinpath("project.json").exists():
            raise StudioError(f"Project '{name}' already exists")
        if aspect not in catalog.ASPECTS_SEEDANCE:
            raise StudioError(f"aspect must be one of {catalog.ASPECTS_SEEDANCE}")
        font = font if font and Path(font).is_file() else (DEFAULT_FONT if Path(DEFAULT_FONT).is_file() else None)
        p = {"name": name, "slug": slug(name), "created": now(), "aspect": aspect, "style": style, "language": language,
             "brief": brief, "budget_usd": float(budget_usd), "spent_usd": 0.0, "ledger": [], "characters": {}, "shots": [],
             "variants": {}, "picked": {}, "jobs": {}, "voiceovers": {}, "music": None, "logo": None, "font": font,
             "outputs": []}
        self.save(p)
        return self.summary(p)

    def summary(self, p: dict) -> dict:
        shots = []
        for s in p["shots"]:
            vs = p["variants"].get(s["id"], [])
            shots.append({"id": s["id"], "duration": s["duration"], "prompt": s["prompt"][:90],
                          "variants": len(vs), "picked": p["picked"].get(s["id"]),
                          "best_quality": max((v["quality"] for v in vs), key=catalog.RANK.index, default=None)})
        active = [j for j in p["jobs"].values() if j["state"] in ("queued", "submitted", "running")]
        return {"project": p["name"], "aspect": p["aspect"], "style": p["style"], "language": p["language"],
                "budget_usd": p["budget_usd"], "spent_usd": round(p["spent_usd"], 3), "characters": list(p["characters"]),
                "shots": shots, "active_jobs": len(active), "outputs": p["outputs"][-3:], "folder": str(self.pdir(p["name"]))}

    def list_projects(self) -> list[dict]:
        out = []
        for d in sorted((self.home / "projects").iterdir()):
            if (d / "project.json").exists():
                p = json.loads((d / "project.json").read_text())
                out.append({"project": p["name"], "shots": len(p["shots"]), "spent_usd": round(p["spent_usd"], 3), "updated": p.get("updated"),
                            "hidden": bool(p.get("hidden"))})
        return out

    # ------------------------------------------------------------------ characters
    def character_add(self, project: str, name: str, description: str, images: list[str]) -> dict:
        p = self.load(project)
        if not images:
            raise StudioError("Give at least one reference image (a clear face/full-body photo or design)")
        d = self.pdir(project) / "characters" / slug(name)
        d.mkdir(parents=True, exist_ok=True)
        saved = []
        for i, img in enumerate(images):
            src = Path(img).expanduser().resolve()
            if not src.is_file() or self.home not in src.parents:
                raise StudioError(f"image not found: {img}")
            dst = d / f"ref{i + 1}{src.suffix.lower()}"
            shutil.copyfile(src, dst)
            saved.append(str(dst))
        p["characters"][name] = {"description": description, "images": saved}
        self.save(p)
        return {"character": name, "images": len(saved)}

    async def character_generate(self, project: str, name: str, description: str, model: str = "flux-dev") -> dict:
        """Make a reference image for a character that has no photo (fictional people, mascots, products)."""
        p = self.load(project)
        d = self.pdir(project) / "characters" / slug(name)
        d.mkdir(parents=True, exist_ok=True)
        dst = d / "ref1.png" if model == "offline-image" else d / "ref1.jpg"
        prompt = (f"Character reference sheet, full body and clear face, plain light background, {description}, "
                  f"{catalog.STYLES.get(p['style'], p['style'])}")
        cost = 0.0
        if model == "offline-image":
            w, h = 768, 1024
            txt = d / "name.txt"
            txt.write_text(f"{name}\n\n{description[:120]}", encoding="utf-8")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                            f"color=c=0x2b3a67:s={w}x{h}:d=1", "-vf",
                            f"drawtext=textfile={txt}:fontcolor=white:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2",
                            "-frames:v", "1", str(dst)], check=True)
            txt.unlink()
        else:
            m = catalog.IMAGE_MODELS.get(model)
            if not m or m["provider"] != "fal":
                raise StudioError(f"image model must be one of {list(catalog.IMAGE_MODELS)}")
            await self._check_budget(p, m["usd_per_image"], None)
            try:
                await fal_image(m["endpoint"], prompt, dst, "3:4")
            except ProviderError as e:
                raise StudioError(str(e)) from None
            cost = m["usd_per_image"]
        def fn(q):
            q["characters"][name] = {"description": description, "images": [str(dst)], "generated": model}
            self._charge(q, cost, f"character image {name}", model)
        await self.update(project, fn)
        return {"character": name, "image": str(dst), "cost_usd": cost}

    # ------------------------------------------------------------------ storyboard
    def storyboard_set(self, project: str, shots: list[dict]) -> dict:
        p = self.load(project)
        problems, clean, ids = [], [], set()
        for i, s in enumerate(shots):
            sid = str(s.get("id") or f"s{i + 1}")
            if sid in ids:
                problems.append(f"shot {i + 1}: duplicate id {sid}")
            ids.add(sid)
            if not str(s.get("prompt", "")).strip() and not s.get("dialogue"):
                problems.append(f"shot {sid}: needs a prompt (what we see and what happens)")
            dur = int(s.get("duration", 5))
            if not 2 <= dur <= 30:
                problems.append(f"shot {sid}: duration {dur}s must be 2-30 (most models 4-10; Wan 3.0 / Seedance 2.5 up to 30)")
            kind = str(s.get("kind") or ("talk" if s.get("dialogue") and not s.get("prompt") else "scene"))
            if kind not in catalog.KINDS:
                problems.append(f"shot {sid}: kind '{kind}' unknown; use one of {catalog.KINDS}")
            if kind == "talk" and not s.get("dialogue"):
                problems.append(f"shot {sid}: a talk shot needs the dialogue line (what is said)")
            for c in s.get("characters", []) or []:
                if c not in p["characters"]:
                    problems.append(f"shot {sid}: unknown character '{c}' (add it first)")
            cam = s.get("camera")
            if cam and cam not in catalog.CAMERA:
                problems.append(f"shot {sid}: camera '{cam}' unknown; use one of {sorted(catalog.CAMERA)}")
            for k in ("start_image", "end_image", "keyframe"):
                if s.get(k) and not self.inside(s[k]):
                    problems.append(f"shot {sid}: {k} not found: {s[k]}")
            if s.get("model") and s["model"] not in self.models:
                problems.append(f"shot {sid}: model '{s['model']}' unknown; use one of {list(self.models)}")
            clean.append({"id": sid, "prompt": str(s.get("prompt", "")).strip(), "duration": dur, "kind": kind,
                          "keyframe": s.get("keyframe"), "voice": s.get("voice"),
                          "camera": cam, "characters": list(s.get("characters", []) or []),
                          "dialogue": s.get("dialogue"), "speaker": s.get("speaker"), "voiceover": s.get("voiceover"),
                          "caption": s.get("caption"), "transition": s.get("transition"), "audio": bool(s.get("audio", True)),
                          "start_image": s.get("start_image"), "end_image": s.get("end_image"), "model": s.get("model")})
        if problems:
            raise StudioError("Storyboard problems:\n- " + "\n- ".join(problems))
        p["shots"] = clean
        p["picked"] = {k: v for k, v in p["picked"].items() if k in ids}
        self.save(p)
        return {"shots": len(clean), "total_seconds": sum(s["duration"] for s in clean),
                "estimate": self.estimate(project, "final"), "next": "generate(quality='preview') to check story and timing for free"}

    def shot_update(self, project: str, shot_id: str, changes: dict) -> dict:
        p = self.load(project)
        s = next((x for x in p["shots"] if x["id"] == shot_id), None)
        if not s:
            raise StudioError(f"No shot {shot_id}")
        changes = dict(changes)
        if any(k in changes and changes[k] != s.get(k) for k in ("prompt", "kind", "characters", "camera")) and "keyframe" not in changes:
            changes["keyframe"] = None                    # the painted first frame no longer matches the shot
        merged = [dict(x, **changes) if x["id"] == shot_id else x for x in p["shots"]]
        self.storyboard_set(project, merged)
        return {"updated": shot_id}

    # ------------------------------------------------------------------ prompts
    def build(self, p: dict, s: dict, model: str, quality: str) -> GenRequest:
        cfg = self.models[model]
        chars = [c for c in s["characters"] if p["characters"].get(c, {}).get("images")]
        mode = "t2v"
        images: list[str] = []
        first = s.get("start_image") or s.get("keyframe")
        if cfg["provider"] == "sync":
            mode = "talk"
        elif first:
            mode = "i2v"
        elif chars:
            mode = "ref"
            for c in chars[: cfg.get("references", 3)]:
                images.append(p["characters"][c]["images"][0])
        parts = []
        if mode == "ref":
            for i, c in enumerate(chars[: len(images)]):
                if cfg["provider"] == "google":
                    parts.append(f"<IMAGE_REF_{i}> is {c}: {p['characters'][c]['description']}.")
                elif cfg["provider"] == "openrouter":
                    if p["characters"][c].get("kind") == "place":
                        parts.append(f"Reference image {i + 1} shows the place {c}: {p['characters'][c]['description']}. "
                                     f"Keep this place exactly as in reference image {i + 1}.")
                    else:
                        parts.append(f"Reference image {i + 1} shows {c}: {p['characters'][c]['description']}. "
                                     f"Keep {c}'s look exactly as in reference image {i + 1}.")
                else:
                    parts.append(f"@Image{i + 1} is {c}: {p['characters'][c]['description']}.")
        else:
            for c in s["characters"]:
                if c in p["characters"]:
                    parts.append(f"{c}: {p['characters'][c]['description']}.")
        if s["prompt"]:
            parts.append(s["prompt"].rstrip(".") + ".")
        if s.get("camera"):
            parts.append(catalog.CAMERA[s["camera"]].capitalize() + ".")
        parts.append(f"Style: {catalog.STYLES.get(p['style'], p['style'])}.")
        if s.get("dialogue"):
            who = s.get("speaker") or self.speaker_of(p, s) or "The person"
            if self.needs_lipsync(p, s, quality):
                parts.append(f"{who} talks naturally with clear mouth movement, face well lit and visible; "
                             "no audible words in the soundtrack, only ambient sound.")
            else:
                parts.append(f'{who} says in {p["language"]}, clearly with natural lip sync: "{s["dialogue"]}"')
        elif s.get("voiceover"):
            parts.append("No one speaks on camera; ambient sound only.")
        if quality in ("final", "premium"):
            parts.append("High detail, natural motion, coherent hands and faces, stable identity, no on-screen text, "
                         "no subtitles, no watermark, no logos.")
        q = catalog.QUALITY[quality]
        res = q["resolution"] if q["resolution"] in cfg["resolutions"] else cfg["resolutions"][0]
        lo, hi = cfg["durations"]
        dur = max(lo, min(hi, int(s["duration"])))
        if cfg.get("allowed_durations"):
            dur = min(cfg["allowed_durations"], key=lambda x: (abs(x - int(s["duration"])), -x))
        aspect = p["aspect"] if p["aspect"] in cfg["aspects"] else ("9:16" if p["aspect"] in ("9:16", "3:4") else "16:9")
        if mode == "talk":
            res = "1080p" if quality in ("final", "premium") else "720p"
        return GenRequest(model=model, cfg=cfg, prompt=" ".join(parts), duration=dur, resolution=res, aspect=aspect,
                          audio=s.get("audio", True), mode=mode, images=images, start_image=first,
                          end_image=s.get("end_image"), label=s["id"], summary=s["prompt"] or s.get("dialogue") or "")

    def needs_lipsync(self, p: dict, s: dict, quality: str) -> bool:
        """v0.157 Spoken lines in Hindi / Indian languages (or any talk shot) = our own voice line + Sync 3 lip sync;
        English / Chinese / Japanese... are spoken by the video model itself."""
        if quality == "preview" or not s.get("dialogue"):
            return False
        kind = s.get("kind") or "scene"
        if kind == "talk":
            return True
        if not self.providers["sync"].ready():
            return False
        return kind == "dialogue" or str(p.get("language", "")).lower() not in catalog.NATIVE_SPEECH

    def model_for(self, s: dict, quality: str, override: str | None) -> str:
        if quality == "preview":
            return "offline-preview"
        if override or s.get("model"):
            return override or s.get("model")
        route = catalog.ROUTES.get(s.get("kind") or "scene", catalog.ROUTES["scene"]).get(quality) or []
        for m in route:                                  # v0.157 best model for this kind of shot whose key is set
            if m in self.models and self.providers[self.models[m]["provider"]].ready():
                return m
        for prov in ("openrouter", "fal", "byteplus"):  # first provider with a key decides draft/final models
            if self.providers[prov].ready():
                return catalog.QUALITY_BY_PROVIDER[prov][quality]
        return route[0] if route else catalog.QUALITY[quality]["model"]

    def estimate(self, project: str, quality: str = "final", shot_ids: list[str] | None = None, variants: int = 1,
                 model: str | None = None) -> dict:
        p = self.load(project)
        if quality not in catalog.QUALITY:
            raise StudioError(f"quality must be one of {list(catalog.QUALITY)}")
        rows, total = [], 0.0
        for s in p["shots"]:
            if shot_ids and s["id"] not in shot_ids:
                continue
            m = self.model_for(s, quality, model)
            q = self.build(p, s, m, quality)
            c = q.duration * self.models[m]["usd_per_s"] * variants
            sync = self.models[m]["provider"] != "sync" and self.needs_lipsync(p, s, quality)
            if sync:
                c += q.duration * self.models["sync-3"]["usd_per_s"] * variants
            total += c
            rows.append({"shot": s["id"], "model": m, "seconds": q.duration, "resolution": q.resolution, "usd": round(c, 3),
                         "kind": s.get("kind") or "scene", "lipsync": sync or self.models[m]["provider"] == "sync"})
        left = p["budget_usd"] - p["spent_usd"] - self._reserved(p)
        return {"quality": quality, "usd": round(total, 3), "budget_left_usd": round(left, 3), "fits_budget": total <= left + 1e-9,
                "shots": rows, "note": "Prices are estimates; set real prices with HOOLA_STUDIO_MODELS."}

    def _reserved(self, p: dict) -> float:
        return sum(j.get("cost_est", 0) for j in p["jobs"].values() if j["state"] in ("queued", "submitted", "running"))

    async def _check_budget(self, p: dict, cost: float, max_cost: float | None) -> None:
        left = p["budget_usd"] - p["spent_usd"] - self._reserved(p)
        if max_cost is not None and cost > max_cost + 1e-9:
            raise StudioError(f"Estimated ${cost:.2f} is above max_cost_usd ${max_cost:.2f}. Ask the user to approve more.")
        if cost > left + 1e-9:
            raise StudioError(f"Estimated ${cost:.2f} but only ${left:.2f} of the ${p['budget_usd']:.2f} budget is left. "
                              "Ask the user to raise the budget (budget_set) or use quality='preview'/'draft'.")

    def _charge(self, p: dict, usd: float, what: str, model: str) -> None:
        if usd <= 0:
            return
        p["spent_usd"] = round(p["spent_usd"] + usd, 4)
        p["ledger"].append({"at": now(), "usd": round(usd, 4), "what": what, "model": model})

    # ------------------------------------------------------------------ generation
    async def generate(self, project: str, quality: str = "preview", shot_ids: list[str] | None = None, variants: int = 1,
                       model: str | None = None, max_cost_usd: float | None = None, wait_s: float = 0) -> dict:
        if quality not in catalog.QUALITY:
            raise StudioError(f"quality must be one of {list(catalog.QUALITY)}")
        variants = max(1, min(int(variants), 4))
        async with self.lock(project):
            p = self.load(project)
            if not p["shots"]:
                raise StudioError("No storyboard yet. Call storyboard_set first.")
            targets = [s for s in p["shots"] if not shot_ids or s["id"] in shot_ids]
            if shot_ids and len(targets) != len(set(shot_ids)):
                raise StudioError(f"Unknown shot ids: {sorted(set(shot_ids) - {s['id'] for s in targets})}")
            need = {self.models[self.model_for(s, quality, model)]["provider"] for s in targets}
            missing = [n for n in need if not self.providers[n].ready()]
            if missing:
                keys = {"fal": "FAL_KEY", "byteplus": "ARK_API_KEY", "google": "GEMINI_API_KEY", "sync": "SYNC_API_KEY",
                        "openrouter": "OPENROUTER_API_KEY"}
                raise StudioError(f"Missing API key for {missing}: set {[keys[m] for m in missing]} on the server, "
                                  "or use quality='preview' for a free animatic.")
            est = self.estimate(project, quality, [s["id"] for s in targets], variants, model)
            await self._check_budget(p, est["usd"], max_cost_usd)
            started = []
            for s in targets:
                m = self.model_for(s, quality, model)
                if self.models[m]["provider"] == "sync" and not (s.get("keyframe") or s.get("start_image")):
                    raise StudioError(f"shot {s['id']} (talk) needs its picture first: paint the keyframe (keyframes) "
                                      "or give a start image.")
                for _ in range(variants):
                    req = self.build(p, s, m, quality)
                    jid = f"j{int(time.time() * 1000) % 10**9}{len(p['jobs'])}"
                    sync = self.models[m]["provider"] != "sync" and self.needs_lipsync(p, s, quality)
                    cost = req.duration * (self.models[m]["usd_per_s"] + (self.models["sync-3"]["usd_per_s"] if sync else 0))
                    p["jobs"][jid] = {"shot": s["id"], "model": m, "quality": quality, "state": "queued", "attempts": 0,
                                      "cost_est": round(cost, 4), "lipsync": sync, "prompt": req.prompt,
                                      "mode": req.mode, "duration": req.duration, "resolution": req.resolution,
                                      "aspect": req.aspect, "created": now(), "handle": None, "error": None}
                    started.append(jid)
            self.save(p)
        for jid in started:
            self.tasks[jid] = asyncio.ensure_future(self._run_job(project, jid))
        out = {"started": len(started), "estimate_usd": est["usd"], "jobs": started}
        if wait_s:
            out["status"] = await self.wait(project, wait_s)
        return out

    async def _set_job(self, project: str, jid: str, **kw) -> dict:
        def fn(p):
            p["jobs"][jid].update(kw)
        p = await self.update(project, fn)
        return p["jobs"][jid]

    async def _run_job(self, project: str, jid: str) -> None:
        p = self.load(project)
        j = p["jobs"][jid]
        shot = next(s for s in p["shots"] if s["id"] == j["shot"])
        prov = self.providers[self.models[j["model"]]["provider"]]
        async with self.sem:
            for attempt in range(1, 4):
                try:
                    handle = j.get("handle") if j.get("state") in ("submitted", "running") and j.get("handle") else None
                    if not handle:
                        req = self.build(p, shot, j["model"], j["quality"])
                        if prov.name == "sync":
                            req.speech = await self._speech(project, shot)
                        handle = await prov.submit(req)
                        j = await self._set_job(project, jid, handle=handle, state="submitted", attempts=attempt, submitted=now())
                    t0 = time.time()
                    while True:
                        r = await prov.poll(handle)
                        if r["state"] in ("queued", "running"):
                            if j["state"] != "running" and r["state"] == "running":
                                j = await self._set_job(project, jid, state="running")
                            if time.time() - t0 > float(os.environ.get("HOOLA_STUDIO_JOB_TIMEOUT_S", "1800")):
                                await prov.cancel(handle)
                                raise ProviderError("timed out", transient=True)
                            await asyncio.sleep(0.3 if prov.name == "offline" else self.poll_s)
                            continue
                        if r["state"] == "failed":
                            if r.get("transient"):
                                raise ProviderError(r["error"], transient=True)
                            await self._set_job(project, jid, state="failed", error=r["error"], finished=now())
                            self._changed(project)
                            return
                        break
                    n = len(self.load(project)["variants"].get(j["shot"], [])) + 1
                    dest = self.pdir(project) / "shots" / f"{j['shot']}_v{n}_{j['quality']}.mp4"
                    while dest.exists():
                        n += 1
                        dest = self.pdir(project) / "shots" / f"{j['shot']}_v{n}_{j['quality']}.mp4"
                    await prov.fetch(r, dest)
                    info = vedit.probe(str(dest)) if vedit else None
                    if info is not None and (not info.has_video or info.duration < 1):
                        raise ProviderError("downloaded file is not a valid video", transient=True)
                    sync_err = None
                    if j.get("lipsync"):                 # v0.157 her line in her language, lips re-synced by Sync 3
                        await self._set_job(project, jid, state="running", stage="lip sync")
                        raw = dest.with_name(dest.stem + "_raw.mp4")
                        os.replace(dest, raw)
                        for k in range(2):               # never pay for the scene twice: only the lip sync is retried
                            try:
                                await self._lipsync(project, shot, raw, dest)
                                sync_err = None
                                break
                            except ProviderError as e:
                                sync_err = str(e)
                                if not e.transient:
                                    break
                        if sync_err:
                            shutil.copyfile(raw, dest)   # keep the paid scene; the line can still go on as narration
                        info = vedit.probe(str(dest)) if vedit else None
                    def fn(q):
                        q["jobs"][jid].update(state="done", finished=now(), file=str(dest), handle=None, error=None)
                        v = {"n": n, "file": str(dest), "model": j["model"], "quality": j["quality"], "job": jid,
                             "duration": round(info.duration, 2) if info else j["duration"], "seed": r.get("seed"),
                             "width": info.width if info else None, "height": info.height if info else None,
                             "has_audio": info.has_audio if info else None, "created": now(), "prompt": j["prompt"],
                             "lipsync": bool(j.get("lipsync")) and not sync_err, "lipsync_error": sync_err}
                        q["variants"].setdefault(j["shot"], []).append(v)
                        real = r.get("cost")
                        if real is not None and j.get("lipsync") and not sync_err:      # the lip sync is billed on top
                            real = round(real + float(j["duration"]) * self.models["sync-3"]["usd_per_s"], 4)
                        self._charge(q, real if real is not None else j["cost_est"],
                                     f"shot {j['shot']} v{n} ({j['quality']})" + (" [actual]" if real is not None else " [estimate]"),
                                     j["model"])
                        v["cost_usd"] = real if real is not None else j["cost_est"]
                        cur = q["picked"].get(j["shot"])
                        rank = catalog.RANK
                        cur_q = next((x["quality"] for x in q["variants"][j["shot"]] if x["n"] == cur), None)
                        if cur is None or rank.index(j["quality"]) > rank.index(cur_q or "preview"):
                            q["picked"][j["shot"]] = n  # newest better-quality take becomes the pick
                    await self.update(project, fn)
                    self._changed(project)
                    return
                except ProviderError as e:
                    if e.transient and attempt < 3:
                        j = await self._set_job(project, jid, state="retrying", error=str(e), handle=None)
                        await asyncio.sleep(2 ** attempt if prov.name != "offline" else 0.1)
                        continue
                    await self._set_job(project, jid, state="failed", error=str(e), finished=now(), handle=None)
                    self._changed(project)
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as e:  # never leave a job hanging
                    await self._set_job(project, jid, state="failed", error=f"{type(e).__name__}: {e}", finished=now())
                    self._changed(project)
                    return

    def speech_plan(self, p: dict, shot: dict) -> tuple[str, str, str, Path]:
        """(text, voice, language, file) of a shot's spoken line; the file exists once it has been made."""
        import hashlib
        text = str(shot.get("dialogue") or "").strip()
        voice = shot.get("voice") or ""
        who = shot.get("speaker") or self.speaker_of(p, shot)
        if not voice and who:
            voice = p["characters"].get(who, {}).get("voice") or ""
        voice = voice or (p.get("prefs") or {}).get("voice") or ""      # v0.159 the voice she chose for the video
        lang = p.get("language", "Hindi")
        key = hashlib.sha1(f"{text}|{voice}|{lang}".encode()).hexdigest()[:12]
        return text, voice, lang, self.pdir(p["name"]) / "audio" / f"line_{key}.wav"

    @staticmethod
    def speaker_of(p: dict, shot: dict) -> str:
        """The first person in the shot (places and products don't speak)."""
        for c in shot.get("characters") or []:
            if (p["characters"].get(c) or {}).get("kind", "person") == "person":
                return c
        return ""

    async def _speech(self, project: str, shot: dict) -> str:
        """The shot's spoken line as our own voice file (made once per text + voice, kept in the project)."""
        p = self.load(project)
        text, voice, lang, out = self.speech_plan(p, shot)
        if not text:
            raise ProviderError("this shot has no line to speak")
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.is_file():
            return str(out)
        if not self.speak:
            raise ProviderError("no voice engine for the spoken line")
        try:
            got = await asyncio.to_thread(self.speak, text, lang, voice)
        except Exception as e:
            raise ProviderError(f"voice line failed: {e}", transient=True) from None
        shutil.copyfile(got, out)
        return str(out)

    async def _lipsync(self, project: str, shot: dict, video: Path, dest: Path) -> None:
        sp = self.providers["sync"]
        req = GenRequest(model="sync-3", cfg=self.models["sync-3"], prompt="", duration=int(shot["duration"]), resolution="1080p",
                         aspect=self.load(project)["aspect"], mode="talk", video_in=str(video), label=shot["id"])
        req.speech = await self._speech(project, shot)
        h = await sp.submit(req)
        t0 = time.time()
        while True:
            r = await sp.poll(h)
            if r["state"] == "done":
                break
            if r["state"] == "failed":
                raise ProviderError(r["error"])
            if time.time() - t0 > float(os.environ.get("HOOLA_STUDIO_JOB_TIMEOUT_S", "1800")):
                raise ProviderError("lip sync timed out", transient=True)
            await asyncio.sleep(self.poll_s)
        await sp.fetch(r, dest)

    def keyframe_prompt(self, p: dict, s: dict) -> tuple[str, list[str]]:
        """v0.157 The first frame of a shot, painted (Nano Banana Pro) with the characters' photos as references:
        the same face / product in every shot, and the video model starts from a designed picture."""
        refs, who = [], []
        for c in s.get("characters") or []:
            ch = p["characters"].get(c)
            if ch and ch.get("images"):
                refs.append(ch["images"][0])
                kind = ch.get("kind", "person")
                if kind == "place":
                    who.append(f"The setting is {c} ({ch.get('description', '')}), exactly as in reference photo {len(refs)}: "
                               "same place, buildings / trees / water, colours and layout")
                elif kind == "product":
                    who.append(f"{c} ({ch.get('description', '')}) looks exactly like reference photo {len(refs)}: same product "
                               "shape, colours, packaging and label")
                else:
                    who.append(f"{c} ({ch.get('description', '')}) looks exactly like the reference photo {len(refs)}: same face, "
                               "hair, skin tone, clothes")
        style = catalog.STYLES.get(p["style"], p["style"])
        if (s.get("kind") or "scene") == "talk":
            body = (f"A medium close-up of {s.get('speaker') or self.speaker_of(p, s) or 'the speaker'} "
                    f"looking into the camera, about to speak, face evenly lit, mouth closed and relaxed, shoulders visible. "
                    f"Setting: {s.get('prompt') or 'a simple pleasant background that suits the topic'}.")
        else:
            cam = catalog.CAMERA.get(s.get("camera") or "", "")
            body = f"{s['prompt']}" + (f" Framing: {cam}." if cam else "")
        prompt = (f"The opening frame of one shot of a {p['aspect']} video ({p.get('brief') or 'short film'}), as a single still "
                  f"image. {body} " + (" ".join(who) + ". " if who else "") +
                  f"Look: {style}. Composition made for {p['aspect']}, subject clearly readable, natural anatomy. "
                  "No text, no captions, no subtitles, no watermark, no logos, no borders.")
        return prompt, refs[:3]

    async def keyframes(self, project: str, shot_ids: list[str] | None = None, cost_each: float = 0.0) -> dict:
        if not self.painter:
            raise StudioError("No picture model (needs GEMINI_API_KEY)")
        p = self.load(project)
        targets = [s for s in p["shots"] if not shot_ids or s["id"] in shot_ids]
        d = self.pdir(project) / "keyframes"
        d.mkdir(parents=True, exist_ok=True)
        sem = asyncio.Semaphore(3)
        done, failed = [], []

        async def one(s: dict) -> None:
            prompt, refs = self.keyframe_prompt(p, s)
            async with sem:
                try:
                    img = await asyncio.to_thread(self.painter, prompt, p["aspect"], refs)
                except Exception as e:
                    failed.append(f"{s['id']}: {str(e)[:120]}")
                    return
            out = d / f"{s['id']}_{int(time.time() * 1000) % 10**8}.jpg"
            out.write_bytes(img)
            done.append((s["id"], str(out)))
        await asyncio.gather(*(one(s) for s in targets))

        def fn(q):
            for sid, path in done:
                for x in q["shots"]:
                    if x["id"] == sid:
                        x["keyframe"] = path
            self._charge(q, cost_each * len(done), f"{len(done)} keyframes", "nano-banana-pro")
        await self.update(project, fn)
        self._changed(project)
        return {"painted": [sid for sid, _ in done], "failed": failed, "usd": round(cost_each * len(done), 3)}

    def _changed(self, project: str) -> None:
        if self.on_change:
            try:
                self.on_change(project)
            except Exception:
                pass

    async def resume(self) -> int:
        """After a restart: keep following fal/BytePlus jobs that were already submitted; resubmit the others."""
        n = 0
        for d in (self.home / "projects").iterdir():
            f = d / "project.json"
            if not f.exists():
                continue
            p = json.loads(f.read_text())
            for jid, j in p["jobs"].items():
                if j["state"] in ("queued", "submitted", "running", "retrying") and jid not in self.tasks:
                    if j.get("handle") and j["handle"].get("provider") in ("google", "offline"):
                        j["handle"], j["state"] = None, "queued"
                        self.save(p)
                    self.tasks[jid] = asyncio.ensure_future(self._run_job(p["name"], jid))
                    n += 1
        return n

    async def cancel_jobs(self, project: str) -> dict:
        """v0.159 'Rok do': stop every shot still waiting or being made (finished takes stay; nothing more is charged
        here, though a provider may still bill a clip it had already started)."""
        p = self.load(project)
        live = [jid for jid, j in p["jobs"].items() if j["state"] in ("queued", "submitted", "running", "retrying")]
        for jid in live:
            t = self.tasks.pop(jid, None)
            if t and not t.done():
                t.cancel()
            j = p["jobs"][jid]
            if j.get("handle"):
                try:
                    await self.providers[self.models[j["model"]]["provider"]].cancel(j["handle"])
                except Exception:
                    pass

        def fn(q):
            for jid in live:
                if q["jobs"][jid]["state"] in ("queued", "submitted", "running", "retrying"):
                    q["jobs"][jid].update(state="cancelled", finished=now(), handle=None, error="rok diya")
        await self.update(project, fn)
        self._changed(project)
        return {"cancelled": len(live)}

    def jobs(self, project: str) -> dict:
        p = self.load(project)
        js = [{"job": k, "shot": v["shot"], "model": v["model"], "quality": v["quality"], "state": v["state"],
               "error": v.get("error"), "file": v.get("file")} for k, v in p["jobs"].items()]
        counts: dict[str, int] = {}
        for j in js:
            counts[j["state"]] = counts.get(j["state"], 0) + 1
        return {"counts": counts, "jobs": js[-40:], "spent_usd": round(p["spent_usd"], 3)}

    async def wait(self, project: str, timeout_s: float = 300) -> dict:
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            st = self.jobs(project)
            if not any(s in st["counts"] for s in ("queued", "submitted", "running", "retrying")):
                return st
            await asyncio.sleep(0.5)
        return self.jobs(project)

    # ------------------------------------------------------------------ review
    def review(self, project: str, shot_id: str, variant: int | None = None) -> dict:
        p = self.load(project)
        vs = p["variants"].get(shot_id, [])
        if not vs:
            raise StudioError(f"Shot {shot_id} has no takes yet")
        n = variant or p["picked"].get(shot_id) or vs[-1]["n"]
        v = next((x for x in vs if x["n"] == n), None)
        if not v:
            raise StudioError(f"Shot {shot_id} has takes {[x['n'] for x in vs]}")
        sheet = self.pdir(project) / "review" / f"{shot_id}_v{n}.png"
        sheet.parent.mkdir(exist_ok=True)
        vops.contact_sheet(v["file"], str(sheet), count=6, columns=3, width=320)
        return {"shot": shot_id, "take": n, "takes": [x["n"] for x in vs], "picked": p["picked"].get(shot_id),
                "info": {k: v[k] for k in ("model", "quality", "duration", "width", "height", "has_audio")}, "sheet": str(sheet)}

    def pick(self, project: str, shot_id: str, take: int) -> dict:
        p = self.load(project)
        if take not in [x["n"] for x in p["variants"].get(shot_id, [])]:
            raise StudioError(f"Shot {shot_id} has no take {take}")
        p["picked"][shot_id] = take
        self.save(p)
        return {"shot": shot_id, "picked": take}

    # ------------------------------------------------------------------ audio, branding
    def voiceover_set(self, project: str, shot_id: str, audio_file: str, text: str | None = None) -> dict:
        p = self.load(project)
        if shot_id not in [s["id"] for s in p["shots"]]:
            raise StudioError(f"No shot {shot_id}")
        src = self.inside(audio_file) or Path("/nonexistent")
        if not src.is_file():
            raise StudioError(f"audio not found: {audio_file}")
        info = vedit.probe(str(src))
        if not info.has_audio:
            raise StudioError("file has no audio")
        dst = self.pdir(project) / "audio" / f"vo_{shot_id}{src.suffix.lower()}"
        dst.parent.mkdir(exist_ok=True)
        shutil.copyfile(src, dst)
        p["voiceovers"][shot_id] = {"file": str(dst), "text": text, "seconds": round(info.duration, 2)}
        self.save(p)
        shot = next(s for s in p["shots"] if s["id"] == shot_id)
        warn = f"voiceover is {info.duration:.1f}s but the shot is {shot['duration']}s" if info.duration > shot["duration"] + 0.5 else None
        return {"shot": shot_id, "seconds": round(info.duration, 2), "warning": warn}

    def music_set(self, project: str, audio_file: str, volume: float = 0.25) -> dict:
        p = self.load(project)
        src = self.inside(audio_file) or Path("/nonexistent")
        if not src.is_file():
            raise StudioError(f"music not found: {audio_file}")
        dst = self.pdir(project) / "audio" / f"music{src.suffix.lower()}"
        dst.parent.mkdir(exist_ok=True)
        shutil.copyfile(src, dst)
        p["music"] = {"file": str(dst), "volume": float(volume)}
        self.save(p)
        return {"music": dst.name, "volume": volume}

    def logo_set(self, project: str, image: str, position: str = "top-right", scale: float = 0.16) -> dict:
        p = self.load(project)
        src = self.inside(image) or Path("/nonexistent")
        if not src.is_file():
            raise StudioError(f"logo not found: {image}")
        dst = self.pdir(project) / f"logo{src.suffix.lower()}"
        shutil.copyfile(src, dst)
        p["logo"] = {"src": str(dst), "position": position, "scale": float(scale), "opacity": 0.9}
        self.save(p)
        return {"logo": dst.name}

    def budget_set(self, project: str, budget_usd: float) -> dict:
        p = self.load(project)
        p["budget_usd"] = float(budget_usd)
        self.save(p)
        return {"budget_usd": p["budget_usd"], "spent_usd": p["spent_usd"]}

    # ------------------------------------------------------------------ assembly
    def _audio_bed(self, p: dict, starts: dict[str, float], total: float, work: Path) -> str | None:
        """Mix voiceovers (placed at each shot's start) with music that dips under the voice."""
        vos = [(sid, v) for sid, v in p["voiceovers"].items() if sid in starts]
        music = p.get("music")
        if not vos and not music:
            return None
        inputs, filt, labels = [], [], []
        for i, (sid, v) in enumerate(vos):
            inputs += ["-i", v["file"]]
            ms = int(round((starts[sid] + 0.25) * 1000))
            filt.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{i}]")
            labels.append(f"[v{i}]")
        voice = None
        if vos:
            filt.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest,apad,atrim=0:{total:.3f}[voice]")
            voice = "voice"
        if music:
            k = len(vos)
            inputs += ["-stream_loop", "-1", "-i", music["file"]]
            filt.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={music['volume']},atrim=0:{total:.3f},"
                        f"afade=t=out:st={max(0, total - 2):.3f}:d=2[mus]")
            if voice:
                filt.append("[voice]asplit=2[vk][vm]")
                filt.append("[mus][vk]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[md]")
                filt.append("[vm][md]amix=inputs=2:normalize=0:duration=first[bed]")
            else:
                filt.append("[mus]anull[bed]")
        else:
            filt.append("[voice]anull[bed]")
        out = work / "bed.wav"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filt),
                        "-map", "[bed]", "-ar", "48000", "-ac", "2", str(out)], check=True)
        return str(out)

    def assemble(self, project: str, output_name: str | None = None, captions: bool = True, ai_label: bool = True,
                 loudness: float = -14.0, transition_default: str | None = None) -> dict:
        p = self.load(project)
        missing = [s["id"] for s in p["shots"] if not p["picked"].get(s["id"])]
        if missing:
            raise StudioError(f"These shots have no take yet: {missing}. Generate them first.")
        work = self.pdir(project) / "work"
        work.mkdir(exist_ok=True)
        rank = {}
        clips, starts, t = [], {}, 0.0
        for i, s in enumerate(p["shots"]):
            v = next(x for x in p["variants"][s["id"]] if x["n"] == p["picked"][s["id"]])
            rank[v["quality"]] = rank.get(v["quality"], 0) + 1
            dur = vedit.probe(v["file"]).duration
            starts[s["id"]] = t
            c: dict[str, Any] = {"src": v["file"]}
            if s["id"] in p["voiceovers"]:
                c["volume"] = 0.3
            cap = s.get("caption")
            if captions and cap:
                c["texts"] = caption_texts(cap, dur, (p.get("prefs") or {}).get("caption_style") or "bold", p.get("font"),
                                           p["aspect"])
            tr = s.get("transition") or transition_default
            td = 0.0
            if tr and i < len(p["shots"]) - 1:
                c["transition"] = {"type": tr, "duration": 0.4}
                td = 0.4
            clips.append(c)
            t += dur - td
        total = t
        tl: dict[str, Any] = {"output": {"aspect": p["aspect"], "fit": "crop", "fps": 30, "crf": 18, "loudnorm": {"I": loudness}},
                              "clips": clips}
        bed = self._audio_bed(p, starts, total, work)
        if bed:
            tl["music"] = {"src": bed, "volume": 1.0, "duck": False, "loop": False, "fade_out": 0}
        if p.get("logo"):
            tl["overlays"] = [p["logo"]]
        if self.label_ai:              # always on in Hoola
            tl["texts"] = [{"text": self.label_ai, "position": "top-left", "size": 26, "box": False, "color": "white@0.75"}]
        name = output_name or f"{p['slug']}_{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.mp4"
        out = self.pdir(project) / "final" / (name if name.endswith(".mp4") else name + ".mp4")
        try:
            rep = vedit.render(tl, str(out), cache_dir=str(work / "cache"))
        except vedit.VeditError as e:
            raise StudioError(f"Assembly failed: {e}") from None
        sheet = out.with_suffix(".png")
        vops.contact_sheet(str(out), str(sheet), count=12, columns=4, width=240)
        quality_mix = ", ".join(f"{k}: {v}" for k, v in rank.items())
        p = self.load(project)
        p["outputs"].append({"file": str(out), "at": now(), "seconds": rep.video_duration, "ok": rep.ok, "takes": quality_mix})
        self.save(p)
        return {"file": str(out), "ok": rep.ok, "seconds": rep.video_duration, "size": f"{rep.width}x{rep.height}",
                "checks": rep.checks, "takes_used": quality_mix, "sheet": str(sheet),
                "note": None if "preview" not in rank else "Contains free animatic placeholders. Generate draft/final takes for real video."}

    def spend(self, project: str) -> dict:
        p = self.load(project)
        by: dict[str, float] = {}
        for e in p["ledger"]:
            by[e["model"]] = round(by.get(e["model"], 0) + e["usd"], 4)
        return {"budget_usd": p["budget_usd"], "spent_usd": round(p["spent_usd"], 3), "reserved_usd": round(self._reserved(p), 3),
                "by_model": by, "ledger": p["ledger"][-30:], "note": "Estimates from the price table, not provider invoices."}

    async def models_sync(self) -> dict:
        """Read OpenRouter's live video model list: update durations/sizes of known models and add new ones."""
        orp = self.providers["openrouter"]
        data = await orp.list_models()
        by_slug = {m.get("model"): k for k, m in self.models.items() if m.get("provider") == "openrouter"}
        updated, added = [], []
        for d in data:
            mid = d.get("id")
            if not mid:
                continue
            key = by_slug.get(mid) or ("or-" + re.sub(r"[^a-z0-9.]+", "-", mid.split("/")[-1].lower()))
            m = self.models.get(key) or {"provider": "openrouter", "model": mid, "label": f"{d.get('name', mid)} via OpenRouter",
                                         "durations": [4, 10], "resolutions": ["720p"], "aspects": ["16:9", "9:16"], "audio": True,
                                         "references": 4, "usd_per_s": 0.25, "price_note": "unknown price (conservative 0.25/s); real cost is recorded"}
            durs = d.get("supported_durations")
            if durs:
                durs = sorted(int(x) for x in durs)
                m["durations"], m["allowed_durations"] = [durs[0], durs[-1]], durs
            if d.get("supported_resolutions"):
                m["resolutions"] = list(d["supported_resolutions"])
            if d.get("supported_aspect_ratios"):
                m["aspects"] = list(d["supported_aspect_ratios"])
            if d.get("supported_frame_images") is not None:
                m["frame_images"] = d["supported_frame_images"]
            if d.get("pricing_skus") is not None:
                m["pricing_skus"] = d["pricing_skus"]
            (updated if key in self.models else added).append(key)
            self.models[key] = m
        (self.home / "openrouter_models.json").write_text(json.dumps(data, indent=1))
        return {"updated": updated, "added": added, "total_openrouter_models": len(data)}

    def models_info(self) -> list[dict]:
        out = []
        for k, m in self.models.items():
            out.append({"model": k, "label": m["label"], "provider": m["provider"], "ready": self.providers[m["provider"]].ready(),
                        "usd_per_second": m["usd_per_s"], "price": m.get("price_note"), "durations_s": m["durations"],
                        "resolutions": m["resolutions"], "aspects": m["aspects"], "audio": m["audio"]})
        return out
