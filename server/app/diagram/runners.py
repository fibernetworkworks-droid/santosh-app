"""Hoola's runners for the three vendored engines: each engine's OWN checks and renderer, called as they ship.

  archify          `node bin/archify.mjs finalize <type> candidate.json out.html --quality showcase --json`
                   = its four gates (validate, deliver, strict check, real-browser check) in one call
  diagram-design   `scripts/self_check.py` + `scripts/verify_geometry.py` (the checks), `scripts/export_png.py` (PNG)
  draw.io          the pinned editor (drawio.py) in headless Chromium, loaded through its embed protocol, PNG out

Hoola's rules around them (the vendored files are never edited):
- archify's daily update check is switched OFF with its own documented variable ARCHIFY_UPDATE_CHECK_DISABLED=1 - a
  diagram never makes a call to archify.si;
- every run has a hard time limit and a fresh scratch folder; the output is read back, never trusted blind;
- the browser is the server's (HOOLA_CHROMIUM / `diagram_chrome` / Google Chrome / Playwright's Chromium)."""
from __future__ import annotations

import base64
import functools
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from . import vendor as V

ARCHIFY_TIMEOUT = 240
CHECK_TIMEOUT = 90
RENDER_TIMEOUT = 120


def _set(name: str, default: Any = "") -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


# ------------------------------------------------------------------ programs
@functools.lru_cache(maxsize=1)
def node_bin() -> str:
    """A node >= 18, or '' (archify needs it)."""
    for cand in (str(_set("diagram_node", "") or ""), shutil.which("node") or ""):
        if not cand:
            continue
        try:
            out = subprocess.run([cand, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        m = re.match(r"v(\d+)", out)
        if m and int(m.group(1)) >= 18:
            return cand
    return ""


def chrome_path() -> str:
    """The Chrome / Chromium both archify's browser gate and Hoola's renders use, or ''."""
    for cand in (str(_set("diagram_chrome", "") or ""), os.environ.get("HOOLA_CHROMIUM", ""),
                 shutil.which("google-chrome") or "", shutil.which("google-chrome-stable") or "",
                 shutil.which("chromium") or "", shutil.which("chromium-browser") or ""):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            exe = p.chromium.executable_path
        if exe and os.path.isfile(exe):
            return exe
    except Exception:  # noqa: BLE001
        pass
    return ""


def _env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TMPDIR",
                                                        "PLAYWRIGHT_BROWSERS_PATH", "HOOLA_CHROMIUM")}
    env["ARCHIFY_UPDATE_CHECK_DISABLED"] = "1"          # archify's own switch: no call to archify.si
    chrome = chrome_path()
    if chrome:
        env["ARCHIFY_CHROME"] = chrome
    if _set("diagram_chrome_no_sandbox", False):
        env["ARCHIFY_CHROME_NO_SANDBOX"] = "1"
    return env


def _last_json(text: str) -> dict[str, Any] | None:
    """The JSON receipt archify prints (the last top-level {...} on stdout)."""
    s = (text or "").strip()
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else None
    except ValueError:
        pass
    i = s.rfind("\n{")
    while i >= 0:
        try:
            v = json.loads(s[i + 1:])
            return v if isinstance(v, dict) else None
        except ValueError:
            i = s.rfind("\n{", 0, i)
    return None


# ------------------------------------------------------------------ engine A: archify
def archify_finalize(kind: str, candidate: dict[str, Any] | str | Path, out_dir: str | Path,
                     slug: str = "diagram", quality: str = "showcase") -> dict[str, Any]:
    """Run archify's finalize. {ok, gates, html, receipt, problems, said}. Never raises for a failing diagram."""
    kinds = {t["type"] for t in V.archify_types()} | {"explainer"}
    if kind not in kinds:
        return {"ok": False, "gates": {}, "html": "", "problems": [f"archify has no type '{kind}'"],
                "said": f"archify draws {', '.join(sorted(kinds))}."}
    node = node_bin()
    if not node:
        return {"ok": False, "gates": {}, "html": "", "problems": ["node >= 18 is not installed on the server"],
                "said": "archify needs Node 18 or newer on the server."}
    out = Path(out_dir).resolve()           # archify runs inside this folder: every path it gets is absolute
    out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9-]", "", slug.lower())[:48] or "diagram"
    cand = out / "candidate.json"
    if isinstance(candidate, dict):
        cand.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), "utf-8")
    else:
        shutil.copyfile(str(candidate), cand)
    html = out / f"{slug}.html"
    cmd = [node, str(V.ARCHIFY / "bin" / "archify.mjs"), "finalize", kind, str(cand), str(html),
           "--quality", quality, "--json"]
    try:
        r = subprocess.run(cmd, cwd=str(out), env=_env(), capture_output=True, text=True, timeout=ARCHIFY_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "gates": {}, "html": "", "problems": [f"archify took longer than {ARCHIFY_TIMEOUT} s"],
                "said": "archify did not finish in time."}
    receipt = _last_json(r.stdout) or _last_json(r.stderr) or {}
    gates = receipt.get("gates") or {}
    ok = r.returncode == 0 and bool(receipt.get("ok")) and html.is_file()
    problems: list[str] = []
    if not ok:
        for d in (receipt.get("diagnostics") or [])[:20]:
            if isinstance(d, dict):
                problems.append(str(d.get("message") or d.get("code") or d)[:400])
            else:
                problems.append(str(d)[:400])
        if not problems:
            tail = (r.stdout or r.stderr or "").strip().splitlines()[-6:]
            problems = [t[:400] for t in tail] or [f"archify exited with {r.returncode}"]
    review = receipt.get("visualReviewRecommendation") or {}
    codes = [str(d.get("code")) for d in (receipt.get("diagnostics") or []) if isinstance(d, dict) and d.get("code")]
    return {"ok": ok, "gates": gates, "codes": codes, "html": str(html) if html.is_file() else "", "receipt": receipt,
            "problems": problems, "review": review.get("hints") or [],
            "said": ("archify: all gates passed" if ok else
                     "archify: " + ", ".join(f"{k} {v}" for k, v in gates.items() if v != "pass") or "archify failed")}


# ------------------------------------------------------------------ engine B: diagram-design
def _py(script: str, args: list[str], timeout: int = CHECK_TIMEOUT) -> subprocess.CompletedProcess:
    # -I: the vendored script runs isolated (no current-folder imports, no user site, no PYTHON* variables)
    return subprocess.run([sys.executable, "-I", str(V.DD / "scripts" / script), *args], cwd=str(V.DD),
                          capture_output=True, text=True, timeout=timeout)


def dd_check(files: list[str | Path]) -> dict[str, Any]:
    """diagram-design's two checkers on one or more files. {ok, failed: {file: [problems]}, checked}."""
    paths = [str(Path(f).resolve()) for f in files]
    failed: dict[str, list[str]] = {}
    try:
        r1 = _py("self_check.py", paths, timeout=CHECK_TIMEOUT + 2 * len(paths))
        cur = ""
        for line in r1.stdout.splitlines():
            if line.startswith("FAIL "):
                cur = line[5:].strip()
                failed.setdefault(cur, [])
            elif line.startswith("  - ") and cur:
                failed[cur].append("self_check: " + line[4:].strip())
        r2 = _py("verify_geometry.py", paths, timeout=CHECK_TIMEOUT + 2 * len(paths))
        for line in r2.stdout.splitlines():
            if line.startswith("Summary:") or not line.strip():
                continue
            m = re.match(r"(.+?\.html):\s*(.*)", line)
            key = m.group(1) if m else (paths[0] if len(paths) == 1 else "?")
            failed.setdefault(key, []).append("verify_geometry: " + (m.group(2) if m else line).strip())
        rc_ok = r1.returncode == 0 and r2.returncode == 0
    except subprocess.TimeoutExpired:
        return {"ok": False, "failed": {"*": ["the checkers took too long"]}, "checked": len(paths)}
    return {"ok": rc_ok and not failed, "failed": failed, "checked": len(paths)}


def dd_png(html: str | Path, png: str | Path, scale: int = 1) -> dict[str, Any]:
    """diagram-design's own PNG export (its export_png.py, unchanged, run through _dd_export.py with the server's browser)."""
    Path(png).parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HOOLA_DIAGRAM_CHROME"] = chrome_path()
    try:
        r = subprocess.run([sys.executable, "-I", str(Path(__file__).with_name("_dd_export.py")), str(V.DD / "scripts"),
                            str(Path(html).resolve()), str(Path(png).resolve()), str(scale)],
                           cwd=str(V.DD), env=env, capture_output=True, text=True, timeout=RENDER_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "said": "the PNG export took too long"}
    ok = r.returncode == 0 and Path(png).is_file() and Path(png).stat().st_size > 0
    return {"ok": ok, "png": str(png) if ok else "", "said": "" if ok else (r.stderr or r.stdout).strip()[-400:]}


# ------------------------------------------------------------------ any HTML diagram -> PNG (archify pages)
def _launch(p):
    kw: dict[str, Any] = {"args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                                   "--font-render-hinting=none", "--force-color-profile=srgb"]}
    exe = chrome_path()
    if exe:
        kw["executable_path"] = exe
    return p.chromium.launch(**kw)


def page_png(html: str | Path, png: str | Path, width: int = 1440, height: int = 900, scale: int = 1) -> dict[str, Any]:
    """A full-page picture of a diagram page (offline: the page may not load anything from the network)."""
    from playwright.sync_api import sync_playwright
    Path(png).parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = _launch(p)
        try:
            ctx = b.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale)
            ctx.route(re.compile(r"^https?://"), lambda route: route.abort())
            page = ctx.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)[:300]))
            page.goto(Path(html).resolve().as_uri(), wait_until="load", timeout=RENDER_TIMEOUT * 1000)
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(400)
            page.screenshot(path=str(png), full_page=True)
        finally:
            b.close()
    ok = Path(png).is_file() and Path(png).stat().st_size > 0
    return {"ok": ok and not errors, "png": str(png) if ok else "", "errors": errors}


# ------------------------------------------------------------------ engine C: draw.io editor
_HOST_PAGE = """<!doctype html><meta charset="utf-8"><title>hoola draw.io</title>
<style>html,body,iframe{margin:0;border:0;width:100%;height:100%}</style>
<iframe id="ed" src="index.html?embed=1&proto=json&spin=0&ui=simple&offline=1&noSaveBtn=1&noExitBtn=1&lang=en"></iframe>
<script>
window.__hoola = {state: 'wait', png: '', error: ''};
const ed = document.getElementById('ed');
window.addEventListener('message', (e) => {
  if (e.source !== ed.contentWindow) return;
  let m; try { m = JSON.parse(e.data); } catch (_) { return; }
  if (m.event === 'init') { window.__hoola.state = 'init';
    ed.contentWindow.postMessage(JSON.stringify({action: 'load', xml: window.__xml, autosave: 0}), '*'); }
  else if (m.event === 'load') { window.__hoola.state = 'loaded';
    ed.contentWindow.postMessage(JSON.stringify({action: 'export', format: window.__fmt || 'png'}), '*'); }
  else if (m.event === 'export') { window.__hoola.png = m.data || ''; window.__hoola.state = 'done'; }
});
</script>"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a: Any) -> None:     # noqa: D401
        pass


def _serve(root: Path):
    handler = functools.partial(_Quiet, directory=str(root))
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def drawio_png(xml: str, png: str | Path) -> dict[str, Any]:
    """Load draw.io XML into the pinned editor (served from 127.0.0.1, every outside request refused) and export a PNG."""
    return drawio_export(xml, png, "png")


def drawio_export(xml: str, out: str | Path, fmt: str = "png") -> dict[str, Any]:
    """The pinned editor's own export: fmt png (a picture) or xmlsvg (an SVG that also carries the diagram)."""
    from . import drawio as DR
    if not DR.ready():
        return {"ok": False, "said": "the draw.io editor is not set up (python -m app.diagram setup)"}
    from playwright.sync_api import sync_playwright
    # the editor folder is served as is; Hoola's small host page sits beside it (same origin = the embed protocol)
    root = DR.editor_dir()
    host = root / "__hoola_host.html"
    host.write_text(_HOST_PAGE, "utf-8")
    srv = _serve(root)
    port = srv.server_address[1]
    try:
        with sync_playwright() as p:
            b = _launch(p)
            try:
                ctx = b.new_context(viewport={"width": 1400, "height": 900})
                ctx.route(re.compile(r"^https?://(?!127\.0\.0\.1:%d/)" % port), lambda route: route.abort())
                page = ctx.new_page()
                page.add_init_script("window.__xml = " + json.dumps(xml) + "; window.__fmt = " + json.dumps(fmt) + ";")
                page.goto(f"http://127.0.0.1:{port}/__hoola_host.html", wait_until="load",
                          timeout=RENDER_TIMEOUT * 1000)
                page.wait_for_function("window.__hoola && window.__hoola.state === 'done'",
                                       timeout=RENDER_TIMEOUT * 1000)
                data = page.evaluate("window.__hoola.png")
            finally:
                b.close()
    finally:
        srv.shutdown()
        srv.server_close()
    m = re.match(r"data:image/(?:png|svg\+xml);base64,(.+)$", data or "", re.S)
    if not m:
        return {"ok": False, "said": "draw.io returned no picture"}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(base64.b64decode(m.group(1)))
    return {"ok": True, "png": str(out), "file": str(out)}
