"""v0.943 HOOLA CODE LOOKS AT WHAT IT CHANGED (owner, on the Cursor comparison: "It doesn't open a browser to check the
app it changed").

The `look` tool opens a page of the WORKING COPY in the server's own headless Chromium, on a phone and a computer
screen, and hands back what a person checking it would notice:
  * a screenshot of each (to the model when its brain reads pictures, and onto her session as a step),
  * the errors the page printed in its console and the requests that failed,
  * the things that are plainly wrong on a phone: the page wider than the screen, pictures that did not load, tap
    targets under 40 px, text under 12 px.

The walls, in code:
  * the page is served from the working copy by a tiny server on 127.0.0.1 that answers ONLY files inside the copy -
    never a link (a planted link could point at the server's own files), never a file that holds secrets;
  * the browser may reach nothing but that server: every other request is refused (no internet, no her other
    services), so a page cannot phone home or pull a script from outside;
  * a page that needs its own running server (an API, a database, a Next.js server) cannot be checked this way and
    the tool says so plainly rather than show a half-broken picture as if it were the app.
Built apps: have the box build first (npm run build ...), then look at the built file (dist/index.html, build/...).
"""
from __future__ import annotations

import base64
import functools
import http.server
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

log = logging.getLogger("hoola.devsahayak.look")

SIZES = {"phone": (390, 844), "computer": (1280, 800)}
SHOTS_KEPT = 24

LOOK_TOOL = {
    "name": "look",
    "description": ("Open a page of the working copy in a real browser (phone 390 px + computer 1280 px) and see it: "
                    "screenshots, the console errors, failed requests, and what is plainly broken on a phone (wider than "
                    "the screen, pictures not loading, tiny tap targets / text). Use it after you change a web page, "
                    "before you call done. path = an .html file from the repo root (for a built app: build it in the "
                    "box first, then look at dist/index.html or build/index.html). The browser reaches nothing outside "
                    "the working copy, so a page that needs its own running server cannot be checked this way."),
    "input_schema": {"type": "object", "properties": {
        "path": {"type": "string", "description": "The page, from the repo root, e.g. index.html or dist/index.html"},
        "screens": {"type": "array", "items": {"type": "string", "enum": ["phone", "computer"]},
                    "description": "Which screens (default both)"},
        "wait_ms": {"type": "integer", "description": "Extra wait after the page loads, for animations (max 4000)"}},
        "required": ["path"]},
}


def on() -> bool:
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "dev_look", True))
    except Exception:
        return True


def _pictures_ok() -> bool:
    """Send the screenshots to the model unless its profile says it reads no pictures (or she turned it off)."""
    try:
        from ..config import get_settings
        if not bool(getattr(get_settings(), "dev_look_pictures", True)):
            return False
        from ..agent import modelprofile as MP
        from . import brain as B
        if B.brain_name() == "qwen":
            prof = MP.get("openrouter:" + B.qwen_model())
            if prof.get("known") and "image" not in (prof.get("inputs") or []):
                return False
    except Exception:
        pass
    return True


class _Handler(http.server.SimpleHTTPRequestHandler):
    """Serves only regular files inside the copy: no links, no secrets, no listing."""
    root: Path = Path("/nonexistent")

    def log_message(self, *a: Any) -> None:  # quiet
        pass

    def list_directory(self, path: str) -> None:  # type: ignore[override]
        self.send_error(404)
        return None

    def send_head(self):  # type: ignore[override]
        rel = unquote(urlsplit(self.path).path).lstrip("/")
        if rel.endswith("/") or rel == "":
            rel = rel + "index.html"
        if not _allowed(self.root, rel):
            self.send_error(404)
            return None
        return super().send_head()


def _allowed(root: Path, rel: str) -> bool:
    if not rel or ".." in rel.split("/") or rel.startswith("."):
        return False
    try:
        from . import engine as EN
        if EN.R.SECRET_FILES.search(rel):
            return False
    except Exception:
        pass
    p = root
    for part in rel.split("/"):
        p = p / part
        if p.is_symlink():
            return False                          # never a link: it could lead out of the copy
    try:
        return p.is_file() and p.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def _serve(root: Path) -> http.server.ThreadingHTTPServer:
    h = type("H", (_Handler,), {"root": root})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(h, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


_CHECK_JS = """() => {
  const vw = document.documentElement.clientWidth;
  const sw = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0);
  const bad = [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.getAttribute('src') || '').slice(0, 8);
  const small = [];
  for (const el of document.querySelectorAll('a,button,input,select,textarea,[role=button]')) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && (r.width < 40 || r.height < 40) && small.length < 8)
      small.push((el.innerText || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 30) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
  }
  let tiny = 0;
  for (const el of document.querySelectorAll('p,span,a,li,td,label,button')) {
    if (!el.innerText || !el.innerText.trim()) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs && fs < 12) tiny++;
  }
  const words = (document.body ? document.body.innerText : '').trim().split(/\\s+/).filter(Boolean).length;
  const vp = !!document.querySelector('meta[name=viewport]');
  return {vw, sw, bad, small, tiny, words, vp, title: document.title || ''};
}"""


def check(repo: Path, rel: str, screens: list[str] | None = None, wait_ms: int = 600) -> dict[str, Any]:
    """Open the page; {ok, path, screens: [{screen, png (bytes), facts}], errors, failed, refused, note}."""
    from ..devlab import service as LS
    rel = LS.safe_rel(rel or "")
    if not rel or not rel.lower().endswith((".html", ".htm")):
        return {"ok": False, "note": "Give an .html file from the repo root (for a built app, build it first and look at dist/index.html)."}
    if not _allowed(repo, rel):
        return {"ok": False, "note": f"{rel} is not a file of the working copy (or it is a link / holds secrets)."}
    want = [s for s in (screens or ["phone", "computer"]) if s in SIZES] or ["phone", "computer"]
    wait_ms = max(0, min(int(wait_ms or 0), 4000))
    srv = _serve(repo)
    origin = f"http://127.0.0.1:{srv.server_address[1]}"
    errors: list[str] = []
    failed: list[str] = []
    refused: list[str] = []
    shots: list[dict[str, Any]] = []
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        srv.shutdown()
        return {"ok": False, "note": "This server has no browser installed (Playwright), so the page cannot be looked at."}
    try:
        with sync_playwright() as p:
            kw: dict[str, Any] = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if os.environ.get("HOOLA_CHROMIUM"):
                kw["executable_path"] = os.environ["HOOLA_CHROMIUM"]
            b = p.chromium.launch(**kw)
            try:
                for sc in want:
                    w, h = SIZES[sc]
                    ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                                        is_mobile=(sc == "phone"), has_touch=(sc == "phone"), service_workers="block")

                    def route(r: Any) -> None:
                        if r.request.url.startswith(origin + "/") or r.request.url.startswith("data:"):
                            r.continue_()
                        else:
                            if len(refused) < 12:
                                refused.append(r.request.url[:160])
                            r.abort()
                    ctx.route("**/*", route)
                    pg = ctx.new_page()
                    pg.on("console", lambda m: errors.append(m.text[:240]) if m.type == "error" and len(errors) < 20 else None)
                    pg.on("pageerror", lambda e: errors.append(str(e)[:240]) if len(errors) < 20 else None)
                    pg.on("requestfailed", lambda r: failed.append(r.url.replace(origin, "")[:160])
                          if r.url.startswith(origin) and len(failed) < 12 else None)
                    pg.on("response", lambda r: failed.append(r.url.replace(origin, "")[:160])
                          if r.url.startswith(origin) and r.status >= 400 and len(failed) < 12 else None)
                    try:
                        pg.goto(f"{origin}/{rel}", wait_until="load", timeout=20000)
                    except Exception as e:
                        errors.append(f"The page did not finish loading: {str(e)[:160]}")
                    if wait_ms:
                        pg.wait_for_timeout(wait_ms)
                    try:
                        facts = pg.evaluate(_CHECK_JS)
                    except Exception:
                        facts = {}
                    png = pg.screenshot(full_page=False, type="png")
                    shots.append({"screen": sc, "png": png, "facts": facts, "size": [w, h]})
                    ctx.close()
            finally:
                b.close()
    except Exception as e:
        log.warning("look failed: %s", e)
        return {"ok": False, "note": f"The browser could not open the page: {str(e)[:200]}"}
    finally:
        srv.shutdown()
    return {"ok": True, "path": rel, "screens": shots, "errors": _dedupe(errors), "failed": _dedupe(failed),
            "refused": _dedupe(refused)}


def _dedupe(xs: list[str]) -> list[str]:
    seen: list[str] = []
    for x in xs:
        if x not in seen:
            seen.append(x)
    return seen


def words(res: dict[str, Any]) -> str:
    """What the model is told, in plain lines. Pure."""
    if not res.get("ok"):
        return str(res.get("note") or "The page could not be looked at.")
    out = [f"Looked at {res['path']}."]
    for s in res.get("screens") or []:
        f = s.get("facts") or {}
        w = s["size"][0]
        bits = [f"{s['screen']} ({w} px): {f.get('words', 0)} words on screen"]
        if s["screen"] == "phone" and f and not f.get("vp"):
            bits.append("NO <meta name=viewport> TAG - a phone shows the page zoomed out, tiny")
        if f.get("sw") and f.get("vw") and int(f["sw"]) > int(f["vw"]) + 2:
            bits.append(f"PAGE IS WIDER THAN THE SCREEN ({f['sw']} px vs {f['vw']} px) - it scrolls sideways")
        if f.get("bad"):
            bits.append("pictures that did not load: " + ", ".join(f["bad"]))
        if s["screen"] == "phone" and f.get("small"):
            bits.append("tap targets under 40 px: " + "; ".join(f["small"]))
        if f.get("tiny"):
            bits.append(f"{f['tiny']} text blocks under 12 px")
        if f and not f.get("words"):
            bits.append("NOTHING READABLE ON SCREEN (blank page?)")
        out.append(" - " + "; ".join(bits))
    if res.get("errors"):
        out.append("Console errors:\n" + "\n".join(f"  {e}" for e in res["errors"][:12]))
    if res.get("failed"):
        out.append("Files the page asked for that are not there: " + ", ".join(res["failed"][:12]))
    if res.get("refused"):
        out.append("Outside addresses the page tried (blocked here, so this check cannot show them): "
                   + ", ".join(res["refused"][:6]) + ". If the page needs its own server or an API, say so to her "
                   "instead of calling it checked.")
    if not res.get("errors") and not res.get("failed"):
        out.append("No console errors, no missing files.")
    return "\n".join(out)


def keep(sdir: Path, res: dict[str, Any]) -> list[str]:
    """Save the screenshots in the session folder (oldest dropped past SHOTS_KEPT); their file names."""
    d = sdir / "shots"
    d.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    stamp = int(time.time() * 1000)
    for s in res.get("screens") or []:
        n = f"{stamp}-{s['screen']}.png"
        (d / n).write_bytes(s["png"])
        names.append(n)
    olds = sorted(d.glob("*.png"))
    for o in olds[:-SHOTS_KEPT]:
        try:
            o.unlink()
        except OSError:
            pass
    return names


def shot_path(sdir: Path, name: str) -> Path | None:
    import re
    if not re.fullmatch(r"\d{10,16}-(phone|computer)\.png", name or ""):
        return None
    p = sdir / "shots" / name
    return p if p.is_file() else None


def run_tool(repo: Path, sdir: Path, inp: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str]:
    """(tool-result blocks, step event for her page, trail line)."""
    res = check(repo, str(inp.get("path") or ""), inp.get("screens") if isinstance(inp.get("screens"), list) else None,
                int(inp.get("wait_ms") or 600))
    text = words(res)
    if not res.get("ok"):
        return [{"type": "text", "text": text}], None, "tried to look at a page"
    names = keep(sdir, res)
    blocks: list[dict[str, Any]] = [{"type": "text", "text": text}]
    pics = []
    if _pictures_ok():
        for s in res["screens"]:
            pics.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                     "data": base64.b64encode(s["png"]).decode()}})
    ev = {"k": "look", "path": res["path"], "shots": names,
          "errors": len(res.get("errors") or []), "text": text.split("\n", 1)[0],
          "facts": json.dumps([{"screen": s["screen"], **{k: v for k, v in (s.get("facts") or {}).items() if k in ("sw", "vw", "words")}}
                               for s in res["screens"]])}
    return blocks + pics, ev, f"looked at {res['path']}"
