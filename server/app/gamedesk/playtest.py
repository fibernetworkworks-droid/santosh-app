"""Hoola plays the Web build before she sees it: Chromium opens it, waits for Hoola's probe (window.__hoola), reads the
engine's own fps / memory / frame count, presses keys, taps and swipes, takes screenshots, collects script errors and
checks the screen is not blank. Software WebGL (SwiftShader) on the server is slower than a phone, so a low fps here is
reported, not failed; a frozen game, a script error or an empty screen fails."""
from __future__ import annotations

import functools
import http.server
import io
import os
import threading
import time
from pathlib import Path
from typing import Any

NOISE = ("GL Driver Message", "GPU stall", "WebGL-", "favicon", "AudioContext was not allowed", "autoplay")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a) -> None:
        pass


def _serve(folder: Path):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(folder)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _launch_kw() -> dict[str, Any]:
    kw: dict[str, Any] = {"args": ["--no-sandbox", "--disable-dev-shm-usage", "--use-gl=angle", "--use-angle=swiftshader",
                                   "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required"]}
    exe = os.environ.get("HOOLA_CHROMIUM", "")
    if exe:
        kw["executable_path"] = exe
    return kw


def blank(png: bytes) -> bool:
    """True when the picture is (almost) one colour: the game drew nothing."""
    try:
        from PIL import Image, ImageStat
        im = Image.open(io.BytesIO(png)).convert("L").resize((64, 64))
        return ImageStat.Stat(im).stddev[0] < 2.0
    except Exception:
        return False


def run(build: Path, out: Path, orientation: str = "portrait", seconds: int = 8) -> dict[str, Any]:
    """Play the build; screenshots go to out/shot1.png ... Returns the verdict and the numbers."""
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    vw, vh = {"portrait": (360, 640), "landscape": (640, 360), "square": (512, 512)}.get(orientation, (360, 640))
    srv = _serve(build)
    res: dict[str, Any] = {"ok": False, "errors": [], "warnings": [], "shots": [], "fps": None, "mem_mb": None,
                           "load_s": None, "frames_advanced": False}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(**_launch_kw())
            try:
                pg = b.new_page(viewport={"width": vw, "height": vh}, device_scale_factor=2, has_touch=False)
                msgs: list[str] = []
                pg.on("console", lambda m: msgs.append(m.text[:300]) if m.type in ("error", "warning") else None)
                pg.on("pageerror", lambda e: msgs.append("page error: " + str(e)[:300]))
                t0 = time.time()
                pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/index.html")
                try:
                    pg.wait_for_function("window.__hoola && window.__hoola.ready", timeout=60000)
                except Exception:
                    res["errors"].append("the game did not start within 60 seconds")
                    return res
                res["load_s"] = round(time.time() - t0, 1)
                pg.wait_for_timeout(2000)
                first = pg.evaluate("window.__hoola") or {}
                shot = pg.screenshot()
                (out / "shot1.png").write_bytes(shot)
                res["shots"].append("shot1.png")
                empty = [blank(shot)]
                cx, cy = vw // 2, vh // 2
                pg.mouse.click(cx, cy)
                for k in ("Space", "Enter", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"):
                    pg.keyboard.press(k)
                    pg.wait_for_timeout(120)
                pg.mouse.move(cx, int(vh * 0.75))
                pg.mouse.down()
                pg.mouse.move(cx, int(vh * 0.25), steps=8)
                pg.mouse.up()
                pg.mouse.move(int(vw * 0.8), cy)
                pg.mouse.down()
                pg.mouse.move(int(vw * 0.2), cy, steps=8)
                pg.mouse.up()
                for i in range(6):
                    pg.mouse.click(cx + (i - 3) * 20, cy + 40)
                    pg.wait_for_timeout(150)
                pg.wait_for_timeout(1500)
                shot = pg.screenshot()
                (out / "shot2.png").write_bytes(shot)
                res["shots"].append("shot2.png")
                empty.append(blank(shot))
                pg.wait_for_timeout(max(1000, (seconds - 5) * 1000))
                last = pg.evaluate("window.__hoola") or {}
                shot = pg.screenshot()
                (out / "shot3.png").write_bytes(shot)
                res["shots"].append("shot3.png")
                empty.append(blank(shot))
                res["fps"] = last.get("fps")
                res["mem_mb"] = round((last.get("mem") or 0) / 1048576, 1) or None
                res["frames_advanced"] = (last.get("frames") or 0) > (first.get("frames") or 0)
                script = [m for m in msgs if not any(n in m for n in NOISE) and
                          ("SCRIPT ERROR" in m or "ERROR:" in m or m.startswith("page error"))]
                res["errors"] += script[:8]
                if not res["frames_advanced"]:
                    res["errors"].append("the game froze (no new frames while playing)")
                if all(empty):
                    res["errors"].append("the screen stayed empty (one colour) the whole time")
                if res["fps"] is not None and res["fps"] < 20:
                    res["warnings"].append(f"{res['fps']} fps on the server's software graphics (phones are faster)")
                res["ok"] = not res["errors"]
                return res
            finally:
                b.close()
    except Exception as e:
        res["errors"].append(f"playtest could not run: {type(e).__name__}: {str(e)[:200]}")
        return res
    finally:
        srv.shutdown()
