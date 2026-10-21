"""From the owner's hoola-studio package (v0.68 in Hoola). Downloads only from public internet addresses.

Video providers. Each turns one shot request into a video file.

fal         - Seedance 2.0 (and any other fal video model) via fal's queue API   [FAL_KEY]
byteplus    - Seedance 2.0 direct from BytePlus ModelArk                        [ARK_API_KEY]
google      - Gemini Omni Flash via the Gemini Interactions API                  [GEMINI_API_KEY]
offline     - free placeholder clips (animatic) made locally with ffmpeg; also used for tests

Images are sent inline (data URIs / base64), so no file hosting is needed.
Base URLs can be overridden (FAL_QUEUE_URL, ARK_BASE_URL, GEMINI_BASE_URL) for proxies and for tests.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


class ProviderError(Exception):
    def __init__(self, msg: str, transient: bool = False):
        super().__init__(msg)
        self.transient = transient


@dataclass
class GenRequest:
    model: str
    cfg: dict
    prompt: str
    duration: int
    resolution: str
    aspect: str
    audio: bool = True
    mode: str = "t2v"                     # t2v | i2v | ref
    images: list[str] = field(default_factory=list)   # reference images (local paths)
    start_image: str | None = None
    end_image: str | None = None
    seed: int | None = None
    label: str = ""                       # shot id, for offline clips
    summary: str = ""                     # the shot as the user wrote it, for offline clips


def image_b64(path: str, max_side: int = 1280) -> tuple[str, str]:
    """Shrink + re-encode to JPEG so requests stay small. Returns (base64, mime)."""
    src = Path(path)
    if not src.is_file():
        raise ProviderError(f"image not found: {path}")
    tmp = Path(tempfile.mkdtemp()) / "img.jpg"
    try:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-vf",
                        f"scale='min({max_side},iw)':'min({max_side},ih)':force_original_aspect_ratio=decrease",
                        "-q:v", "3", "-frames:v", "1", str(tmp)], check=True, capture_output=True)
        return base64.b64encode(tmp.read_bytes()).decode(), "image/jpeg"
    except subprocess.CalledProcessError as e:
        raise ProviderError(f"could not read image {path}: {e.stderr.decode()[-200:]}") from None
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def data_uri(path: str) -> str:
    b, mime = image_b64(path)
    return f"data:{mime};base64,{b}"


def _http_error(r: httpx.Response, who: str) -> ProviderError:
    body = r.text[:500]
    transient = r.status_code >= 500 or r.status_code in (408, 409, 425, 429)
    hint = ""
    if r.status_code in (401, 403):
        hint = " (check the API key)"
    elif r.status_code in (400, 422):
        hint = " (request rejected: check the prompt for blocked content, sizes or durations)"
    elif r.status_code == 402:
        hint = " (account out of credit)"
    return ProviderError(f"{who} HTTP {r.status_code}{hint}: {body}", transient=transient)


def _public(url: str) -> None:
    """Provider results point at their CDN; never let a reply send the server to a local / internal address."""
    if os.environ.get("STUDIO_ALLOW_PRIVATE", "").lower() in ("1", "true"):
        return
    import ipaddress
    import socket
    from urllib.parse import urlparse
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ProviderError(f"bad download link: {url[:80]}")
    try:
        ips = {i[4][0] for i in socket.getaddrinfo(u.hostname, None)}
    except OSError as e:
        raise ProviderError(f"download host not found: {e}", transient=True) from None
    if not ips or not all(ipaddress.ip_address(ip).is_global for ip in ips):
        raise ProviderError("download link points at a local address; refused")


async def download(url: str, dest: Path, headers: dict | None = None) -> Path:
    _public(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    try:
        async def _hop(request):          # every redirect is checked too
            _public(str(request.url))
        async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=30), follow_redirects=True,
                                     event_hooks={"request": [_hop]}) as c:
            async with c.stream("GET", url, headers=headers or {}) as r:
                if r.status_code >= 400:
                    raise _http_error(r, "download")
                with open(tmp, "wb") as f:
                    async for chunk in r.aiter_bytes(1 << 16):
                        f.write(chunk)
    except httpx.HTTPError as e:
        raise ProviderError(f"download failed: {e}", transient=True) from None
    os.replace(tmp, dest)
    return dest


# ------------------------------------------------------------------------------------------ fal
class Fal:
    name = "fal"

    def __init__(self):
        self.key = os.environ.get("FAL_KEY", "")
        self.base = os.environ.get("FAL_QUEUE_URL", "https://queue.fal.run").rstrip("/")

    def ready(self) -> bool:
        return bool(self.key)

    def _h(self) -> dict:
        return {"Authorization": f"Key {self.key}", "Content-Type": "application/json"}

    def body(self, q: GenRequest) -> dict:
        b: dict[str, Any] = {"prompt": q.prompt, "resolution": q.resolution, "aspect_ratio": q.aspect,
                             "duration": str(int(q.duration)), "generate_audio": bool(q.audio)}
        if q.mode == "i2v":
            b["image_url"] = data_uri(q.start_image)
            if q.end_image:
                b["end_image_url"] = data_uri(q.end_image)
        elif q.mode == "ref":
            b["image_urls"] = [data_uri(p) for p in q.images]
        return b  # fal's Seedance schema has no seed input, so none is sent

    async def submit(self, q: GenRequest) -> dict:
        if not self.ready():
            raise ProviderError("FAL_KEY is not set")
        ep = q.cfg["endpoints"][q.mode]
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(f"{self.base}/{ep}", headers=self._h(), json=self.body(q))
        except httpx.HTTPError as e:
            raise ProviderError(f"fal submit failed: {e}", transient=True) from None
        if r.status_code >= 400:
            raise _http_error(r, "fal")
        j = r.json()
        return {"provider": "fal", "request_id": j["request_id"], "status_url": j["status_url"],
                "response_url": j["response_url"], "cancel_url": j.get("cancel_url")}

    async def poll(self, h: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.get(h["status_url"], headers=self._h())
                if r.status_code >= 400:
                    raise _http_error(r, "fal status")
                st = r.json()
                s = st.get("status")
                if s in ("IN_QUEUE", "IN_PROGRESS"):
                    return {"state": "queued" if s == "IN_QUEUE" else "running", "position": st.get("queue_position")}
                if s != "COMPLETED":
                    return {"state": "running"}
                if st.get("error"):
                    return {"state": "failed", "error": f"{st.get('error_type', '')}: {st['error']}"}
                r = await c.get(h["response_url"], headers=self._h())
                if r.status_code >= 400:
                    e = _http_error(r, "fal result")
                    return {"state": "failed", "error": str(e)} if not e.transient else {"state": "running"}
                out = r.json()
        except httpx.HTTPError as e:
            raise ProviderError(f"fal poll failed: {e}", transient=True) from None
        url = (out.get("video") or {}).get("url")
        if not url:
            return {"state": "failed", "error": f"fal returned no video: {str(out)[:300]}"}
        return {"state": "done", "url": url, "seed": out.get("seed")}

    async def fetch(self, res: dict, dest: Path) -> Path:
        return await download(res["url"], dest)

    async def cancel(self, h: dict) -> None:
        if h.get("cancel_url"):
            async with httpx.AsyncClient(timeout=30) as c:
                await c.put(h["cancel_url"], headers=self._h())


# ------------------------------------------------------------------------------------------ BytePlus
class BytePlus:
    name = "byteplus"

    def __init__(self):
        self.key = os.environ.get("ARK_API_KEY", "")
        self.base = os.environ.get("ARK_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3").rstrip("/")

    def ready(self) -> bool:
        return bool(self.key)

    def _h(self) -> dict:
        return {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def body(self, q: GenRequest) -> dict:
        content: list[dict] = [{"type": "text", "text": q.prompt}]
        if q.mode == "i2v":
            content.append({"type": "image_url", "image_url": {"url": data_uri(q.start_image)}, "role": "first_frame"})
            if q.end_image:
                content.append({"type": "image_url", "image_url": {"url": data_uri(q.end_image)}, "role": "last_frame"})
        elif q.mode == "ref":
            content += [{"type": "image_url", "image_url": {"url": data_uri(p)}, "role": "reference_image"} for p in q.images]
        b = {"model": q.cfg["model"], "content": content, "ratio": q.aspect, "duration": int(q.duration),
             "resolution": q.resolution, "generate_audio": bool(q.audio), "watermark": False}
        if q.seed is not None:
            b["seed"] = q.seed
        return b

    async def submit(self, q: GenRequest) -> dict:
        if not self.ready():
            raise ProviderError("ARK_API_KEY is not set")
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(f"{self.base}/contents/generations/tasks", headers=self._h(), json=self.body(q))
        except httpx.HTTPError as e:
            raise ProviderError(f"BytePlus submit failed: {e}", transient=True) from None
        if r.status_code >= 400:
            raise _http_error(r, "BytePlus")
        return {"provider": "byteplus", "task_id": r.json()["id"]}

    async def poll(self, h: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.get(f"{self.base}/contents/generations/tasks/{h['task_id']}", headers=self._h())
        except httpx.HTTPError as e:
            raise ProviderError(f"BytePlus poll failed: {e}", transient=True) from None
        if r.status_code >= 400:
            raise _http_error(r, "BytePlus status")
        j = r.json()
        s = j.get("status")
        if s in ("queued", "running"):
            return {"state": s}
        if s == "succeeded":
            url = (j.get("content") or {}).get("video_url")
            return {"state": "done", "url": url, "seed": j.get("seed")} if url else {"state": "failed", "error": "no video_url"}
        err = j.get("error") or {}
        return {"state": "failed", "error": f"{s}: {err.get('code', '')} {err.get('message', '')}".strip()}

    async def fetch(self, res: dict, dest: Path) -> Path:
        return await download(res["url"], dest)

    async def cancel(self, h: dict) -> None:
        async with httpx.AsyncClient(timeout=30) as c:
            await c.delete(f"{self.base}/contents/generations/tasks/{h['task_id']}", headers=self._h())


# ------------------------------------------------------------------------------------------ OpenRouter
class OpenRouter:
    """One key for Seedance, Veo, Kling, Wan... POST /videos -> poll polling_url -> download. The poll result carries
    usage.cost (USD), which the studio records as the real spend."""
    name = "openrouter"

    def __init__(self):
        self.key = os.environ.get("OPENROUTER_API_KEY", "")
        self.base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.site = re.match(r"^(https?://[^/]+)", self.base).group(1)
        # how reference images reach OpenRouter: "data" (inline) or "public" (signed links served by this studio)
        self.image_mode = os.environ.get("HOOLA_STUDIO_IMAGE_MODE", "data")
        self.public_image = None  # set by the studio: callable(path) -> https URL

    def ready(self) -> bool:
        return bool(self.key)

    def _h(self) -> dict:
        h = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        if os.environ.get("OPENROUTER_APP_URL"):
            h["HTTP-Referer"] = os.environ["OPENROUTER_APP_URL"]
        h["X-Title"] = os.environ.get("OPENROUTER_APP_NAME", "Hoola Video Studio")
        return h

    def _img(self, path: str) -> str:
        if self.image_mode == "public":
            if not self.public_image:
                raise ProviderError("HOOLA_STUDIO_IMAGE_MODE=public needs HOOLA_STUDIO_PUBLIC_URL")
            return self.public_image(path)
        return data_uri(path)

    def body(self, q: GenRequest) -> dict:
        b: dict[str, Any] = {"model": q.cfg["model"], "prompt": q.prompt, "duration": int(q.duration),
                             "resolution": q.resolution, "aspect_ratio": q.aspect, "generate_audio": bool(q.audio)}
        if q.mode == "i2v":
            b["frame_images"] = [{"type": "image_url", "image_url": {"url": self._img(q.start_image)}, "frame_type": "first_frame"}]
            if q.end_image:
                b["frame_images"].append({"type": "image_url", "image_url": {"url": self._img(q.end_image)}, "frame_type": "last_frame"})
        elif q.mode == "ref":
            b["input_references"] = [{"type": "image_url", "image_url": {"url": self._img(p)}} for p in q.images]
        if q.seed is not None:
            b["seed"] = q.seed
        if os.environ.get("OPENROUTER_CALLBACK_URL"):
            b["callback_url"] = os.environ["OPENROUTER_CALLBACK_URL"]
        return b

    async def submit(self, q: GenRequest) -> dict:
        if not self.ready():
            raise ProviderError("OPENROUTER_API_KEY is not set")
        try:
            async with httpx.AsyncClient(timeout=90) as c:
                r = await c.post(f"{self.base}/videos", headers=self._h(), json=self.body(q))
        except httpx.HTTPError as e:
            raise ProviderError(f"OpenRouter submit failed: {e}", transient=True) from None
        if r.status_code >= 400:
            raise _http_error(r, "OpenRouter")
        j = r.json()
        pu = j.get("polling_url") or f"{self.base}/videos/{j['id']}"
        if pu.startswith("/"):
            pu = self.site + pu
        return {"provider": "openrouter", "id": j["id"], "polling_url": pu}

    async def poll(self, h: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.get(h["polling_url"], headers=self._h())
        except httpx.HTTPError as e:
            raise ProviderError(f"OpenRouter poll failed: {e}", transient=True) from None
        if r.status_code >= 400:
            raise _http_error(r, "OpenRouter status")
        j = r.json()
        s = j.get("status")
        if s in ("pending", "in_progress"):
            return {"state": "queued" if s == "pending" else "running"}
        if s == "completed":
            cost = (j.get("usage") or {}).get("cost")
            urls = j.get("unsigned_urls") or []
            signed = [u.get("url") if isinstance(u, dict) else u for u in (j.get("urls") or [])]
            return {"state": "done", "id": h["id"], "url": urls[0] if urls else None, "signed": signed[0] if signed else None,
                    "cost": float(cost) if cost is not None else None, "generation_id": j.get("generation_id")}
        err = j.get("error")
        if isinstance(err, dict):
            err = err.get("message") or str(err)
        return {"state": "failed", "error": f"{s}: {err or 'no details'}"}

    async def fetch(self, res: dict, dest: Path) -> Path:
        url = res.get("url") or f"{self.base}/videos/{res['id']}/content?index=0"
        if url.startswith("/"):
            url = self.site + url
        if url.startswith(self.site):
            return await download(url, dest, {"Authorization": f"Bearer {self.key}"})
        if res.get("signed") and not res.get("url"):
            return await download(res["signed"], dest)
        return await download(url, dest)

    async def cancel(self, h: dict) -> None:
        return None  # the API has no cancel endpoint for video jobs

    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get(f"{self.base}/videos/models", headers=self._h() if self.key else {})
        if r.status_code >= 400:
            raise _http_error(r, "OpenRouter models")
        return r.json().get("data", [])


# ------------------------------------------------------------------------------------------ Google
class Google:
    """Gemini Omni Flash through the Interactions API. The create call returns when the video is ready, so it runs
    as a background task inside this process (a restart loses in-flight Google jobs; they are retried)."""
    name = "google"

    def __init__(self):
        self.key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        self.base = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self.running: dict[str, asyncio.Task] = {}

    def ready(self) -> bool:
        return bool(self.key)

    def body(self, q: GenRequest) -> dict:
        res = q.resolution if q.resolution in ("360p", "720p", "1080p", "4k") else "720p"
        b: dict[str, Any] = {"model": q.cfg["model"],
                             "response_format": {"type": "video", "aspect_ratio": q.aspect if q.aspect in ("16:9", "9:16") else "16:9",
                                                 "resolution": res, "delivery": "uri"}}
        imgs = [q.start_image] if q.mode == "i2v" else q.images if q.mode == "ref" else []
        if imgs:
            items = []
            for p in imgs:
                d, mime = image_b64(p)
                items.append({"type": "image", "data": d, "mime_type": mime})
            items.append({"type": "text", "text": q.prompt})
            b["input"] = items
            b["generation_config"] = {"video_config": {"task": "image_to_video" if q.mode == "i2v" else "reference_to_video"}}
        else:
            b["input"] = q.prompt
        return b

    async def _run(self, q: GenRequest) -> dict:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(900, connect=30)) as c:
                r = await c.post(f"{self.base}/interactions", params={"key": self.key}, json=self.body(q))
        except httpx.HTTPError as e:
            raise ProviderError(f"Gemini request failed: {e}", transient=True) from None
        if r.status_code >= 400:
            raise _http_error(r, "Gemini")
        return r.json()

    @staticmethod
    def find_video(obj: Any) -> dict | None:
        if isinstance(obj, dict):
            if obj.get("type") == "video" and (obj.get("uri") or obj.get("data")):
                return obj
            for v in obj.values():
                f = Google.find_video(v)
                if f:
                    return f
        elif isinstance(obj, list):
            for v in obj:
                f = Google.find_video(v)
                if f:
                    return f
        return None

    async def submit(self, q: GenRequest) -> dict:
        if not self.ready():
            raise ProviderError("GEMINI_API_KEY is not set")
        jid = "g" + hashlib.sha1(f"{q.prompt}{os.urandom(8)}".encode()).hexdigest()[:12]
        self.running[jid] = asyncio.ensure_future(self._run(q))
        return {"provider": "google", "job": jid}

    async def poll(self, h: dict) -> dict:
        t = self.running.get(h["job"])
        if t is None:
            return {"state": "failed", "error": "lost after restart", "transient": True}
        if not t.done():
            return {"state": "running"}
        self.running.pop(h["job"], None)
        try:
            j = t.result()
        except ProviderError as e:
            if e.transient:
                raise
            return {"state": "failed", "error": str(e)}
        v = self.find_video(j)
        if not v:
            return {"state": "failed", "error": f"no video in response: {str(j)[:300]}"}
        return {"state": "done", "video": v}

    async def fetch(self, res: dict, dest: Path) -> Path:
        v = res["video"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if v.get("data"):
            dest.write_bytes(base64.b64decode(v["data"]))
            return dest
        fid = v["uri"].split("/files/")[-1].split(":")[0].split("?")[0]
        async with httpx.AsyncClient(timeout=60) as c:
            for _ in range(120):
                r = await c.get(f"{self.base}/files/{fid}", params={"key": self.key})
                if r.status_code >= 400:
                    raise _http_error(r, "Gemini file")
                st = r.json().get("state")
                if st == "ACTIVE":
                    break
                if st == "FAILED":
                    raise ProviderError("Gemini file processing failed")
                await asyncio.sleep(2)
        return await download(f"{self.base}/files/{fid}:download?alt=media&key={self.key}", dest)

    async def cancel(self, h: dict) -> None:
        t = self.running.pop(h.get("job", ""), None)
        if t:
            t.cancel()


# ------------------------------------------------------------------------------------------ offline
SIZES = {"360p": 360, "480p": 480, "720p": 720, "1080p": 1080, "4k": 2160}


def frame_size(resolution: str, aspect: str) -> tuple[int, int]:
    short = SIZES.get(resolution, 720)
    aw, ah = (int(x) for x in aspect.split(":"))
    if aw >= ah:
        w, h = round(short * aw / ah), short
    else:
        w, h = short, round(short * ah / aw)
    return w - w % 2, h - h % 2


class Offline:
    """Free animatic clips: the shot text over a colour plate (or a slow push-in on the start/reference image),
    with a quiet tone. Lets the user check story and timing before paying for real generation."""
    name = "offline"

    def __init__(self):
        self.jobs: dict[str, asyncio.Task] = {}
        self.fail_once = set(filter(None, os.environ.get("HOOLA_OFFLINE_FAIL_ONCE", "").split(",")))

    def ready(self) -> bool:
        return True

    async def _make(self, q: GenRequest, out: Path) -> Path:
        delay = float(os.environ.get("HOOLA_OFFLINE_DELAY", "0"))
        if delay:
            await asyncio.sleep(delay)
        if q.label in self.fail_once:
            self.fail_once.discard(q.label)
            raise ProviderError("simulated temporary provider error", transient=True)
        w, h = frame_size(q.resolution, q.aspect)
        d = int(q.duration)
        tmp = Path(tempfile.mkdtemp(prefix="hoola_off_"))
        fs = max(14, min(w, h) // 22)
        per_line = max(12, int(w * 0.86 / (fs * 0.62)))
        wrap = "\n".join(textwrap.wrap(q.summary or q.prompt, per_line)[:8])
        (tmp / "t.txt").write_text(f"{q.label} · {d}s · preview\n\n{wrap}", encoding="utf-8")
        hue = int(hashlib.md5(q.prompt.encode()).hexdigest()[:2], 16) * 360 // 256
        img = q.start_image or (q.images[0] if q.images else None)
        font = next((f for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",) if Path(f).exists()), None)
        draw = (f",drawtext=textfile=t.txt:fontcolor=white:fontsize={fs}:line_spacing={fs // 3}:box=1:boxcolor=black@0.55:"
                f"boxborderw={fs // 2}:x=(w-text_w)/2:y=(h-text_h)/2" + (f":fontfile={font}" if font else ""))
        n = d * 25
        if img:
            shutil.copyfile(img, tmp / ("in" + Path(img).suffix))
            src = ["-loop", "1", "-framerate", "25", "-t", str(d), "-i", "in" + Path(img).suffix]
            vf = (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
                  f"zoompan=z='min(zoom+0.0008,1.15)':d={n}:s={w}x{h}:fps=25,format=yuv420p{draw}")
        else:
            src = ["-f", "lavfi", "-i", f"gradients=s={w}x{h}:d={d}:r=25:c0=0x203060:c1=0x{hue:02x}4080:speed=0.02"]
            vf = f"hue=h={hue},format=yuv420p{draw}"
        aud = ["-f", "lavfi", "-t", str(d), "-i",
               "sine=f=220:sample_rate=48000" if q.audio else "anullsrc=r=48000:cl=stereo"]
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *src, *aud, "-vf", vf, "-af", "volume=0.08",
               "-t", str(d), "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-shortest", "out.mp4"]
        p = await asyncio.create_subprocess_exec(*cmd, cwd=str(tmp), stdout=asyncio.subprocess.DEVNULL,
                                                 stderr=asyncio.subprocess.PIPE)
        _, err = await p.communicate()
        if p.returncode != 0:
            shutil.rmtree(tmp, ignore_errors=True)
            raise ProviderError(f"offline render failed: {err.decode()[-300:]}")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp / "out.mp4"), out)
        shutil.rmtree(tmp, ignore_errors=True)
        return out

    async def submit(self, q: GenRequest) -> dict:
        jid = "o" + hashlib.sha1(os.urandom(8)).hexdigest()[:12]
        out = Path(tempfile.gettempdir()) / f"hoola_offline_{jid}.mp4"
        self.jobs[jid] = asyncio.ensure_future(self._make(q, out))
        return {"provider": "offline", "job": jid, "path": str(out)}

    async def poll(self, h: dict) -> dict:
        t = self.jobs.get(h["job"])
        if t is None:
            return {"state": "failed", "error": "lost after restart", "transient": True}
        if not t.done():
            return {"state": "running"}
        self.jobs.pop(h["job"], None)
        t.result()  # raises ProviderError
        return {"state": "done", "path": h["path"]}

    async def fetch(self, res: dict, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(res["path"], dest)
        return dest

    async def cancel(self, h: dict) -> None:
        t = self.jobs.pop(h.get("job", ""), None)
        if t:
            t.cancel()


async def fal_image(endpoint: str, prompt: str, dest: Path, aspect: str = "1:1") -> Path:
    """Text-to-image on fal (for character sheets / keyframes). Output schema: images[0].url."""
    f = Fal()
    if not f.ready():
        raise ProviderError("FAL_KEY is not set")
    size = {"1:1": "square_hd", "16:9": "landscape_16_9", "9:16": "portrait_16_9", "4:3": "landscape_4_3", "3:4": "portrait_4_3"}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{f.base}/{endpoint}", headers=f._h(), json={"prompt": prompt, "image_size": size.get(aspect, "square_hd")})
        if r.status_code >= 400:
            raise _http_error(r, "fal image")
        h = r.json()
        for _ in range(180):
            s = (await c.get(h["status_url"], headers=f._h())).json()
            if s.get("status") == "COMPLETED":
                break
            await asyncio.sleep(1)
        out = (await c.get(h["response_url"], headers=f._h())).json()
    url = (out.get("images") or [{}])[0].get("url")
    if not url:
        raise ProviderError(f"no image returned: {str(out)[:200]}")
    if url.startswith("data:"):
        dest.write_bytes(base64.b64decode(url.split(",", 1)[1]))
        return dest
    return await download(url, dest)


def all_providers() -> dict[str, Any]:
    return {"openrouter": OpenRouter(), "fal": Fal(), "byteplus": BytePlus(), "google": Google(), "offline": Offline()}
