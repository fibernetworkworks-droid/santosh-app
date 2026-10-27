"""Turn a Hoola Motion page (HTML whose look is a pure function of time) into an MP4.

Headless Chromium (Playwright) opens the page from disk with ALL network blocked, sets the time frame by frame
(`HOOLA.seek(t)`), takes a screenshot of each frame and pipes them into ffmpeg (H.264, yuv420p, +faststart) with an
optional music bed. Every video carries a visible "AI · Hoola" badge (drawn by the page) and AI metadata in the file
(IT Rules 2026 labelling).
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

log = logging.getLogger("santosh.motion")

ASSETS = Path(__file__).parent / "assets"
SIZES = {"9:16": (720, 1280), "1:1": (900, 900), "16:9": (1280, 720)}
FPS = 30
MAX_SECONDS = 60


class RenderError(Exception):
    pass


# set the time; CSS / Web animations (if a custom page uses them) are paused at the same moment
_SEEK = ("HOOLA.seek(%.4f);(document.getAnimations?document.getAnimations():[]).forEach(function(a){try{a.pause();"
         "a.currentTime=%.1f}catch(e){}})")


def available() -> str:
    """'' when rendering works on this server, else what is missing."""
    if not shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return "playwright"
    return ""


def _page_file(tmp: Path, kind: str, html: str | None) -> Path:
    return ASSETS / f"{kind}.html"


_INLINE: dict[str, str] = {}


def _inline_runtime() -> str:
    """hm.css with the fonts as data: URLs + hm.js, for custom pages that load with no file or network access."""
    if "x" not in _INLINE:
        import base64
        css = (ASSETS / "hm.css").read_text(encoding="utf-8")
        for f in (ASSETS / "fonts").glob("*.woff2"):
            css = css.replace(f"url(fonts/{f.name})", "url(data:font/woff2;base64," + base64.b64encode(f.read_bytes()).decode() + ")")
        js = (ASSETS / "hm.js").read_text(encoding="utf-8")
        # a video is a pure function of time: clocks, timers and randomness are frozen / seeded
        freeze = ("(function(){var r=HM.rnd(20261021);Math.random=r;var T0=1767225600000;Date.now=function(){return T0};"
                  "if(window.performance){performance.now=function(){return 0}}"
                  "window.requestAnimationFrame=function(){return 0};window.setInterval=function(){return 0};"
                  "window.setTimeout=function(){return 0};})();")
        _INLINE["x"] = f"<style>{css}</style><script>{js}\n{freeze}</script>"
    return _INLINE["x"]


def custom_document(html: str) -> str:
    import re
    head = _inline_runtime()
    if re.search(r"<head[^>]*>", html, re.I):
        html = re.sub(r"(<head[^>]*>)", lambda m: m.group(1) + head, html, count=1, flags=re.I)
    else:
        html = head + html
    if 'id="stage"' not in html and "id='stage'" not in html:
        if re.search(r"<body[^>]*>", html, re.I):
            html = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + '<div id="stage"></div>', html, count=1, flags=re.I)
        else:
            html = html.replace(head, head + '<div id="stage"></div>', 1)
    return html


def frames(kind: str, data: dict, aspect: str = "9:16", html: str | None = None, times: list[float] | None = None,
           out_dir: Path | None = None) -> dict:
    """Open the page and either save some still frames (checks / thumbnails) or return its duration and errors."""
    from playwright.sync_api import sync_playwright
    w, h = SIZES.get(aspect, SIZES["9:16"])
    tmp = Path(tempfile.mkdtemp(prefix="hm_"))
    page_file = _page_file(tmp, kind, html)
    errors: list[str] = []
    out: dict = {"errors": errors, "shots": []}
    try:
        with sync_playwright() as p:
            browser = _launch(p)
            page = _open(browser, page_file, data, w, h, errors, html)
            out["duration"] = float(page.evaluate("window.HOOLA && HOOLA.duration") or 0)
            for i, t in enumerate(times or []):
                page.evaluate(_SEEK % (t, t * 1000))
                if out_dir is not None:
                    f = out_dir / f"frame_{i:02d}.jpg"
                    page.screenshot(path=str(f), type="jpeg", quality=85)
                    out["shots"].append(str(f))
            browser.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def _launch(p):
    import os
    kw = {"args": ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--font-render-hinting=none",
                   "--force-color-profile=srgb"]}
    exe = os.environ.get("HOOLA_CHROMIUM", "")
    if exe:
        kw["executable_path"] = exe
    return p.chromium.launch(**kw)


def _open(browser, page_file: Path, data: dict, w: int, h: int, errors: list[str], html: str | None = None):
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, java_script_enabled=True,
                              offline=True)
    page = ctx.new_page()
    # nothing leaves the machine: only the page's own folder (fonts, runtime) and data: / blob: URLs load
    root = ASSETS.resolve().as_uri()

    def route(r):
        u = r.request.url
        if u.startswith(root) or u.startswith("data:") or u.startswith("blob:"):
            return r.continue_()
        return r.abort()
    page.route("**/*", route)
    page.on("pageerror", lambda e: errors.append(str(e)[:300]))
    page.on("console", lambda m: errors.append(m.text[:300]) if m.type == "error" else None)
    page.add_init_script(f"window.DATA = {json.dumps(data, ensure_ascii=False)};")
    if html is None:
        page.goto(page_file.resolve().as_uri(), wait_until="load", timeout=20000)
    else:   # Hoola's own code: no file access at all (about:blank origin), runtime and fonts inlined
        page.set_content(custom_document(html), wait_until="load", timeout=20000)
    page.evaluate("window.HOOLA_READY || true")
    page.wait_for_function("window.HOOLA && typeof HOOLA.seek === 'function' && HOOLA.duration > 0", timeout=8000)
    return page


def video(kind: str, data: dict, out_path: Path, aspect: str = "9:16", html: str | None = None, music: Path | None = None,
          progress: Callable[[float], None] | None = None, title: str = "") -> dict:
    """Render the whole page to an MP4. Returns {duration, frames, size, errors}."""
    from playwright.sync_api import sync_playwright
    if available():
        raise RenderError(f"Server par video banane ke liye {available()} chahiye (deploy/setup_motion.sh chalaiye).")
    w, h = SIZES.get(aspect, SIZES["9:16"])
    tmp = Path(tempfile.mkdtemp(prefix="hm_"))
    page_file = _page_file(tmp, kind, html)
    errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = _launch(p)
            page = _open(browser, page_file, data, w, h, errors, html)
            dur = min(float(page.evaluate("HOOLA.duration") or 0), MAX_SECONDS)
            if dur <= 0:
                raise RenderError("Animation ki lambai nahi mili.")
            n = int(round(dur * FPS))
            cmd = ["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-"]
            if music is not None and music.exists():
                cmd += ["-i", str(music), "-filter_complex",
                        f"[1:a]atrim=0:{dur:.2f},volume=0.7,afade=t=in:d=0.4,afade=t=out:st={max(0.0, dur - 1.5):.2f}:d=1.5[a]",
                        "-map", "0:v", "-map", "[a]", "-c:a", "aac", "-b:a", "128k"]
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-metadata", f"title={title[:80] or 'Hoola Motion'}",
                    "-metadata", "comment=AI-generated video made with Hoola (Hoola AI). Synthetic content.",
                    "-metadata", "description=AI-generated (Hoola Motion)", "-t", f"{dur:.3f}", str(out_path)]
            ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                for i in range(n):
                    page.evaluate(_SEEK % (i / FPS, i / FPS * 1000))
                    ff.stdin.write(page.screenshot(type="jpeg", quality=90))
                    if progress and i % 15 == 0:
                        progress(i / n)
                ff.stdin.close()
                err = ff.stderr.read().decode("utf-8", "replace")
                if ff.wait(timeout=180) != 0:
                    raise RenderError(f"ffmpeg: {err[-300:]}")
            except BrokenPipeError:
                raise RenderError(f"ffmpeg ruk gaya: {ff.stderr.read().decode('utf-8', 'replace')[-300:]}")
            finally:
                if ff.poll() is None:
                    ff.kill()
            browser.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if progress:
        progress(1.0)
    return {"duration": round(dur, 2), "frames": n, "size": out_path.stat().st_size, "errors": errors[:10]}
