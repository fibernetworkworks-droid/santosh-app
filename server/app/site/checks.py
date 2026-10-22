"""v0.121 Quality gates for a built site, run in real Chromium (Playwright) with the network blocked: every page at 360 /
390 / 768 / 1440 px. Blocking: horizontal scroll, broken internal links, missing alt / labels, one h1, title +
description, text contrast (WCAG AA), page weight (first load <= 1 MB, JS <= 120 KB gzipped, image <= 300 KB),
console errors, reduced-motion version shows everything, security headers. Lighthouse and axe-core are used when the
VPS has them (deploy/setup_sites.sh); otherwise Hoola's own lab numbers (LCP with 4x CPU slowdown, CLS, frame rate
while scrolling) are reported and labelled as such. Also makes the screenshots (390 + 1440), the og image and a 6 s
scroll video of the home page."""
from __future__ import annotations

import gzip
import http.server
import json
import logging
import mimetypes
import os
import shutil
import socketserver
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.site")
ORIGIN = "https://site.hoola.check"
VIEWPORTS = (360, 390, 768, 1440)


class CheckError(Exception):
    pass


def available() -> str:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return "playwright"
    return ""


def _vendor(name: str) -> Path | None:
    for base in (Path(os.environ.get("SITE_TOOLS_DIR", "data/site_tools")), Path(__file__).resolve().parent / "assets" / "vendor"):
        p = base / name
        if p.exists():
            return p
    return None


def _launch(p):
    kw: dict[str, Any] = {"args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--font-render-hinting=none",
                                   "--force-color-profile=srgb"]}
    if os.environ.get("HOOLA_CHROMIUM"):
        kw["executable_path"] = os.environ["HOOLA_CHROMIUM"]
    return p.chromium.launch(**kw)


def _serve(out: Path, counter: dict[str, int]):
    def handler(route):
        url = route.request.url
        if not url.startswith(ORIGIN):
            route.abort()
            return
        path = url[len(ORIGIN):].split("?")[0].split("#")[0] or "/"
        rel = path.lstrip("/")
        f = (out / rel)
        if path.endswith("/"):
            f = f / "index.html"
        try:
            f = f.resolve()
            f.relative_to(out.resolve())
        except (ValueError, OSError):
            route.fulfill(status=404, body="")
            return
        if not f.is_file():
            counter["missing"] = counter.get("missing", 0) + 1
            route.fulfill(status=404, body="not found")
            return
        data = f.read_bytes()
        counter["bytes"] = counter.get("bytes", 0) + len(data)
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if f.suffix == ".woff2":
            ctype = "font/woff2"
        if f.suffix == ".avif":
            ctype = "image/avif"
        route.fulfill(status=200, body=data, headers={"Content-Type": ctype})
    return handler


PAGE_JS = r"""() => {
  const out = {issues: [], warn: [], h1: document.querySelectorAll('h1').length,
    title: document.title || '', desc: (document.querySelector('meta[name=description]')||{}).content || '',
    blanks: document.querySelectorAll('.blank').length, links: []};
  const sid = el => { const s = el.closest('section'); return s ? s.id : ''; };
  const vw = window.innerWidth;
  if (document.scrollingElement.scrollWidth > vw + 1) {
    const wide = [...document.querySelectorAll('main *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > vw + 2; }).slice(0, 4);
    out.issues.push({kind: 'overflow', text: 'Page scrolls sideways at ' + vw + ' px', sections: [...new Set(wide.map(sid))]});
  }
  document.querySelectorAll('img').forEach(i => { if (!i.hasAttribute('alt')) out.issues.push({kind: 'alt', text: 'Image without alt text', sections: [sid(i)]}); });
  document.querySelectorAll('input,textarea,select').forEach(i => {
    if (i.type === 'hidden' || i.classList.contains('hp')) return;
    const lab = i.id && document.querySelector('label[for="' + i.id + '"]');
    if (!lab && !i.closest('label') && !i.getAttribute('aria-label')) out.issues.push({kind: 'label', text: 'Form field without a label', sections: [sid(i)]});
  });
  const rgba = c => { if (!c) return null; let m, k = 1;
    if (c.startsWith('color(srgb')) { m = c.match(/[\d.]+/g); k = 255; } else m = c.match(/[\d.]+/g);
    if (!m || m.length < 3) return null; return {r: +m[0] * k, g: +m[1] * k, b: +m[2] * k, a: m.length > 3 ? +m[3] : 1}; };
  const L = o => { const v = [o.r, o.g, o.b].map(x => { x = x / 255; return x <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); });
    return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;
      const c = rgba(cs.backgroundColor); if (c && c.a > .9) return c; }
    return rgba(getComputedStyle(document.body).backgroundColor); };
  let bad = 0;
  [...document.querySelectorAll('main h1,main h2,main h3,main p,main li,main a,main span,main button,main label,footer p,footer a')].slice(0, 600).forEach(el => {
    if (!el.childNodes.length || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || +cs.opacity < .5) return;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) return;
    const f0 = rgba(cs.color), bg = bgOf(el); if (!f0 || !bg) return;
    const fg = {r: f0.r * f0.a + bg.r * (1 - f0.a), g: f0.g * f0.a + bg.g * (1 - f0.a), b: f0.b * f0.a + bg.b * (1 - f0.a)};
    const a = L(fg), b = L(bg); const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    const large = parseFloat(cs.fontSize) >= 24 || (parseFloat(cs.fontSize) >= 18.6 && +cs.fontWeight >= 700);
    if (ratio < (large ? 3 : 4.5) && bad < 6) { bad++; out.issues.push({kind: 'contrast', text: 'Low contrast text (' + ratio.toFixed(1) + ':1): ' + el.textContent.trim().slice(0, 40), sections: [sid(el)]}); }
  });
  if (vw <= 400) {
    const small = [...document.querySelectorAll('main a, main button')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.height && (r.height < 40 && r.width < 40); });
    if (small.length) out.warn.push({kind: 'tap', text: small.length + ' small tap targets', sections: [...new Set(small.slice(0, 4).map(sid))]});
  }
  document.querySelectorAll('a[href]').forEach(a => out.links.push(a.getAttribute('href')));
  const pre = document.querySelectorAll('.hm-pre').length;
  out.hidden_motion = pre;
  return out;
}"""

LCP_JS = r"""() => new Promise(res => {
  let lcp = 0, cls = 0;
  try { new PerformanceObserver(l => { const e = l.getEntries(); lcp = e[e.length - 1].startTime; }).observe({type: 'largest-contentful-paint', buffered: true}); } catch (e) {}
  try { new PerformanceObserver(l => { l.getEntries().forEach(e => { if (!e.hadRecentInput) cls += e.value; }); }).observe({type: 'layout-shift', buffered: true}); } catch (e) {}
  setTimeout(() => res({lcp, cls}), 1500);
})"""

FPS_JS = r"""async () => {
  const H = document.scrollingElement.scrollHeight - innerHeight; const times = []; let last = performance.now();
  const t0 = last; await new Promise(res => { const step = t => { times.push(t - last); last = t;
      const k = Math.min(1, (t - t0) / 2500); scrollTo(0, H * k); if (k < 1) requestAnimationFrame(step); else res(); };
    requestAnimationFrame(step); });
  times.shift(); times.sort((a, b) => a - b); const med = times[Math.floor(times.length / 2)] || 16.7;
  return Math.round(1000 / med);
}"""


def run(out: Path, plan: dict[str, Any], shots_dir: Path | None = None, video: bool = True) -> dict[str, Any]:
    if available():
        raise CheckError("Website jaanch ke liye server par Playwright + Chromium chahiye (deploy/setup_sites.sh).")
    from playwright.sync_api import sync_playwright
    pages = [p["slug"] for p in plan.get("pages", [])]
    report: dict[str, Any] = {"pages": {}, "blocking": [], "warnings": [], "scores": {}, "source": "hoola"}
    # weight / JS budget (files, not browser): JS gzipped, biggest image
    js = b"".join((out / "assets" / n).read_bytes() for n in ("hoola-site.js", "site.js") if (out / "assets" / n).exists())
    js_kb = round(len(gzip.compress(js)) / 1024, 1)
    big_img = max([(p.stat().st_size, p.name) for p in (out / "assets" / "img").glob("*") if p.suffix in (".jpg", ".webp", ".avif")]
                  or [(0, "")])
    report["scores"]["js_kb"] = js_kb
    if js_kb > 120:
        report["blocking"].append({"kind": "weight", "text": f"JavaScript {js_kb} KB gzipped (limit 120 KB)", "sections": []})
    if big_img[0] > 300 * 1024 and not big_img[1].endswith("-1600.jpg"):
        report["warnings"].append({"kind": "weight", "text": f"Image {big_img[1]} is {big_img[0] // 1024} KB", "sections": []})
    axe = _vendor("axe.min.js")
    with sync_playwright() as p:
        b = _launch(p)
        try:
            for slug in pages:
                pr: dict[str, Any] = {"issues": [], "warnings": [], "shots": {}}
                url = f"{ORIGIN}/" + ("" if slug == "home" else f"{slug}/")
                for vw in VIEWPORTS:
                    counter: dict[str, int] = {}
                    ctx = b.new_context(viewport={"width": vw, "height": 844 if vw < 800 else 900}, device_scale_factor=1)
                    page = ctx.new_page()
                    errors: list[str] = []
                    page.on("pageerror", lambda e, errors=errors: errors.append(str(e)[:160]))
                    page.on("console", lambda m, errors=errors: errors.append(m.text[:160]) if m.type == "error" and
                            "Content Security Policy" not in m.text else None)
                    page.route("**/*", _serve(out, counter))
                    if vw == 390:
                        cdp = ctx.new_cdp_session(page)
                        try:
                            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
                        except Exception:
                            pass
                    page.goto(url, wait_until="load", timeout=45000)
                    try:
                        page.evaluate("document.fonts.ready.then(() => true)")
                    except Exception:
                        pass
                    if vw == 390:
                        perf = page.evaluate(LCP_JS)
                        pr["lcp_ms"], pr["cls"] = round(perf.get("lcp") or 0), round(perf.get("cls") or 0, 3)
                        pr["first_load_kb"] = round(counter.get("bytes", 0) / 1024)
                    res = page.evaluate(PAGE_JS)
                    for it in res["issues"]:
                        it["text"] += f" ({slug}, {vw}px)" if it["kind"] == "overflow" else f" ({slug})"
                        if not any(x["text"] == it["text"] for x in pr["issues"]):
                            pr["issues"].append(it)
                    pr["warnings"] += [w for w in res["warn"] if not any(x["text"] == w["text"] for x in pr["warnings"])]
                    if vw == 390:
                        pr.update({"h1": res["h1"], "title": res["title"], "desc": res["desc"], "blanks": res["blanks"],
                                   "links": res["links"]})
                        if axe:
                            try:
                                page.add_script_tag(content=axe.read_text())
                                ax = page.evaluate("axe.run(document,{resultTypes:['violations']}).then(r=>r.violations."
                                                   "filter(v=>['serious','critical'].includes(v.impact)).map(v=>({id:v.id,"
                                                   "n:v.nodes.length,help:v.help})))")
                                for v in ax:
                                    pr["issues"].append({"kind": "a11y", "text": f"{v['help']} ({v['n']}x, {slug})", "sections": []})
                                report["source"] = "hoola+axe"
                            except Exception:
                                log.info("axe failed", exc_info=True)
                        if slug == "home":
                            try:
                                pr["fps"] = page.evaluate(FPS_JS)
                            except Exception:
                                pr["fps"] = 0
                    if errors:
                        pr["issues"].append({"kind": "console", "text": f"Script error on {slug}: {errors[0]}", "sections": []})
                    if shots_dir is not None and vw in (390, 1440):
                        page.evaluate("window.scrollTo(0,0)")
                        page.wait_for_timeout(250)
                        shots_dir.mkdir(parents=True, exist_ok=True)
                        fn = shots_dir / f"{slug}-{vw}.jpg"
                        page.screenshot(path=str(fn), type="jpeg", quality=78, full_page=False)
                        pr["shots"][str(vw)] = fn.name
                        if slug == "home" and vw == 390:
                            full = shots_dir / f"{slug}-{vw}-full.jpg"
                            page.screenshot(path=str(full), type="jpeg", quality=70, full_page=True)
                            pr["shots"]["full"] = full.name
                    ctx.close()
                # reduced motion: everything must be visible
                ctx = b.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
                page = ctx.new_page()
                page.route("**/*", _serve(out, {}))
                page.goto(url, wait_until="load", timeout=45000)
                page.evaluate("window.scrollTo(0, document.scrollingElement.scrollHeight)")
                page.wait_for_timeout(300)
                hidden = page.evaluate("[...document.querySelectorAll('main *')].filter(e=>{const r=e.getBoundingClientRect();"
                                       "return getComputedStyle(e).opacity==='0'&&r.height>8&&r.right>0&&!e.closest('.hp,[aria-hidden=true]')}).length")
                if hidden:
                    pr["issues"].append({"kind": "motion", "text": f"{hidden} elements stay invisible with reduced motion ({slug})",
                                         "sections": []})
                ctx.close()
                # internal links
                for href in set(pr.pop("links", [])):
                    if not href or href.startswith(("http", "tel:", "mailto:", "sms:", "#", "https:")):
                        continue
                    base = Path("/" + ("" if slug == "home" else slug + "/"))
                    target = (base / href.split("#")[0]).as_posix()
                    target = os.path.normpath(target)
                    tf = out / target.lstrip("/")
                    if tf.is_dir() or target.endswith("/") or not tf.suffix:
                        tf = tf / "index.html"
                    if not tf.exists():
                        pr["issues"].append({"kind": "link", "text": f"Broken link '{href}' on {slug}", "sections": []})
                if pr.get("h1") != 1:
                    pr["issues"].append({"kind": "h1", "text": f"{slug}: {pr.get('h1')} h1 headings (needs exactly 1)", "sections": []})
                if not pr.get("desc"):
                    pr["warnings"].append({"kind": "seo", "text": f"{slug}: no description", "sections": []})
                if pr.get("first_load_kb", 0) > 1024:
                    pr["issues"].append({"kind": "weight", "text": f"{slug}: first load {pr['first_load_kb']} KB (limit 1,024)",
                                         "sections": []})
                if pr.get("lcp_ms", 0) > 2500:
                    pr["warnings"].append({"kind": "speed", "text": f"{slug}: LCP {pr['lcp_ms']} ms in Hoola's lab (target 2,500)",
                                           "sections": []})
                report["pages"][slug] = pr
            if shots_dir is not None:
                _og_and_video(b, out, shots_dir, video)
        finally:
            b.close()
    for slug, pr in report["pages"].items():
        report["blocking"] += pr["issues"]
        report["warnings"] += pr["warnings"]
    home = report["pages"].get("home", {})
    report["scores"].update({"lcp_ms": home.get("lcp_ms", 0), "cls": home.get("cls", 0), "fps": home.get("fps", 0),
                             "first_load_kb": home.get("first_load_kb", 0),
                             "blanks": sum(pr.get("blanks", 0) for pr in report["pages"].values())})
    lh = lighthouse(out)
    if lh:
        report["scores"].update(lh)
        report["source"] = "lighthouse" + ("+axe" if axe else "")
        for k in ("performance", "accessibility", "seo"):
            if lh.get(k, 100) < 90:
                (report["blocking"] if k != "performance" else report["warnings"]).append(
                    {"kind": "lighthouse", "text": f"Lighthouse {k} {lh[k]} (target 90+)", "sections": []})
    else:
        report["scores"].update(_own_scores(report))
    report["passed"] = not report["blocking"]
    return report


def _own_scores(r: dict[str, Any]) -> dict[str, int]:
    """Hoola's own 0-100 estimates (labelled 'Hoola lab') when Lighthouse is not on the server."""
    sc = r["scores"]
    perf = 100
    lcp = sc.get("lcp_ms", 0)
    perf -= max(0, min(40, (lcp - 1200) // 50)) if lcp else 0
    perf -= max(0, min(20, int((sc.get("first_load_kb", 0) - 500) / 40)))
    perf -= int(min(15, sc.get("cls", 0) * 100))
    kinds = [x["kind"] for x in r["blocking"]]
    acc = max(0, 100 - 8 * sum(k in ("contrast", "alt", "label", "a11y") for k in kinds))
    seo = max(0, 100 - 10 * sum(k in ("h1", "seo") for k in kinds + [w["kind"] for w in r["warnings"]]))
    best = max(0, 100 - 10 * sum(k in ("console", "link", "overflow") for k in kinds))
    return {"performance": int(max(0, perf)), "accessibility": acc, "best_practices": best, "seo": seo}


def media(out: Path, shots_dir: Path) -> None:
    """og image + the 6 s scroll video of the home page (once per version)."""
    if available():
        return
    from playwright.sync_api import sync_playwright
    shots_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = _launch(p)
        try:
            _og_and_video(b, out, shots_dir, True)
        finally:
            b.close()


def _og_and_video(b, out: Path, shots_dir: Path, video: bool) -> None:
    ctx = b.new_context(viewport={"width": 1200, "height": 630})
    page = ctx.new_page()
    page.route("**/*", _serve(out, {}))
    page.goto(ORIGIN + "/", wait_until="load")
    page.wait_for_timeout(1200)
    page.screenshot(path=str(out / "assets" / "og.jpg"), type="jpeg", quality=80)
    shutil.copy(out / "assets" / "og.jpg", shots_dir / "og.jpg")
    ctx.close()
    if not video or not shutil.which("ffmpeg"):
        return
    with tempfile.TemporaryDirectory() as td:
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        page = ctx.new_page()
        page.route("**/*", _serve(out, {}))
        page.goto(ORIGIN + "/", wait_until="load")
        page.wait_for_timeout(500)
        h = page.evaluate("document.scrollingElement.scrollHeight - innerHeight")
        n = 60
        for i in range(n):
            page.evaluate(f"window.scrollTo(0, {h} * {i / (n - 1):.4f})")
            page.wait_for_timeout(90)
            page.screenshot(path=f"{td}/f{i:03d}.jpg", type="jpeg", quality=75)
        ctx.close()
        try:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i", f"{td}/f%03d.jpg",
                            "-vf", "scale=390:-2,format=yuv420p", "-c:v", "libx264", "-crf", "28", "-movflags", "+faststart",
                            str(shots_dir / "scroll.mp4")], check=True, timeout=120)
        except Exception:
            log.info("scroll video failed", exc_info=True)


# ---------------------------------------------------------------- Lighthouse (optional, when installed)
class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def lighthouse(out: Path) -> dict[str, Any]:
    lh = shutil.which("lighthouse")
    if not lh or os.environ.get("SITE_LIGHTHOUSE", "true").lower() in ("0", "false", "off"):
        return {}
    chrome = os.environ.get("HOOLA_CHROMIUM") or _playwright_chrome()
    if not chrome:
        return {}
    handler = lambda *a, **k: _Quiet(*a, directory=str(out), **k)  # noqa: E731
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            r = subprocess.run([lh, f"http://127.0.0.1:{port}/", "--quiet", "--output=json", "--output-path=stdout",
                                "--only-categories=performance,accessibility,best-practices,seo", "--form-factor=mobile",
                                "--chrome-flags=--headless=new --no-sandbox --disable-gpu"],
                               capture_output=True, text=True, timeout=180, env={**os.environ, "CHROME_PATH": chrome})
            j = json.loads(r.stdout or "{}")
        except Exception:
            log.info("lighthouse failed", exc_info=True)
            return {}
        finally:
            srv.shutdown()
    cats = j.get("categories") or {}
    au = j.get("audits") or {}

    def sc(k: str) -> int:
        v = (cats.get(k) or {}).get("score")
        return int(round((v or 0) * 100))
    return {"performance": sc("performance"), "accessibility": sc("accessibility"), "best_practices": sc("best-practices"),
            "seo": sc("seo"), "lcp_ms": round((au.get("largest-contentful-paint") or {}).get("numericValue") or 0),
            "cls": round((au.get("cumulative-layout-shift") or {}).get("numericValue") or 0, 3),
            "tbt_ms": round((au.get("total-blocking-time") or {}).get("numericValue") or 0)}


def _playwright_chrome() -> str:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return p.chromium.executable_path
    except Exception:
        return ""
