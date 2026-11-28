"""v0.999.64 D3 THE SPEED LAB (docs/WEB_DESIGN_ENGINE_PLAN.md P6): a built App Engine app's pages measured the way
Google's Lighthouse measures a phone - Chromium at a phone size, the CPU slowed 4x and the network slowed to
Lighthouse's mobile setting applied in the browser (562.5 ms round trip, 1.47 Mbit/s down: rtt 150 ms x 3.75,
1.6 Mbit/s x 0.9). The pages are served the way a live site app serves them (service._serve: site pages with their
sealed CSP, gzip like a front door).

Per page: LCP (largest paint), CLS (layout shift, over the whole visit incl. islands waking as it scrolls), TBT (main
thread blocked after the first paint - the lab's stand-in for INP, which needs a real visitor), FCP, the JavaScript /
CSS / font / image weight (gzip, as sent), and the SEO basics (title, description, one H1, canonical, lang, valid
JSON-LD, pictures with alt text). Budgets below = Google's "good" thresholds for Core Web Vitals + Hoola's own weights.

This is a LAB number on this machine: a real visitor's phone and network differ (field data is a later step)."""
from __future__ import annotations

import gzip
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

BUDGET = {"lcp_ms": 2500, "cls": 0.1, "tbt_ms": 200,       # Core Web Vitals "good" (TBT stands in for INP in a lab)
          "site_js_first_kb": 100,                            # a SITE page, first screen: only the islands near it (gzip)
          "site_js_kb": 200,                                  # a SITE page, a whole visit to the bottom (every island woke)
          "image_kb": 1000, "font_kb": 250, "css_kb": 60}
THROTTLE = {"latency": 562.5, "downloadThroughput": 1474.56 * 1024 / 8, "uploadThroughput": 675 * 1024 / 8,
            "cpu": 4, "name": "Lighthouse mobile (devtools throttling): 150 ms x 3.75 RTT, 1.6 Mbit/s x 0.9, CPU x4"}
PHONE = {"viewport": {"width": 412, "height": 823}, "device_scale_factor": 1.75, "is_mobile": True, "has_touch": True,
         "user_agent": ("Mozilla/5.0 (Linux; Android 11; moto g power (2022)) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Mobile Safari/537.36")}
PREFIX = "/apps/lab/"

_OBSERVE = """(() => {
  window.__hl = { lcp: 0, cls: 0, fcp: 0, long: [] };
  try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__hl.lcp = e.startTime; })
          .observe({ type: 'largest-contentful-paint', buffered: true }); } catch (e) {}
  try { new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__hl.cls += e.value; })
          .observe({ type: 'layout-shift', buffered: true }); } catch (e) {}
  try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__hl.long.push([e.startTime, e.duration]); })
          .observe({ type: 'longtask', buffered: true }); } catch (e) {}
  try { new PerformanceObserver((l) => { for (const e of l.getEntries()) if (e.name === 'first-contentful-paint') window.__hl.fcp = e.startTime; })
          .observe({ type: 'paint', buffered: true }); } catch (e) {}
})();"""

_SEO = """() => {
  const ld = [...document.querySelectorAll('script[type="application/ld+json"]')];
  let ldOk = true;
  for (const s of ld) { try { JSON.parse(s.textContent || ''); } catch (e) { ldOk = false; } }
  const desc = document.querySelector('meta[name="description"]');
  return {
    title: document.title || '',
    description: desc ? desc.getAttribute('content') || '' : '',
    h1: document.querySelectorAll('h1').length,
    canonical: (document.querySelector('link[rel="canonical"]') || {}).href || '',
    lang: document.documentElement.lang || '',
    viewport: !!document.querySelector('meta[name="viewport"]'),
    jsonld: ld.length, jsonld_ok: ldOk,
    img_no_alt: [...document.querySelectorAll('img')].filter((i) => !i.hasAttribute('alt')).length,
    noindex: !!document.querySelector('meta[name="robots"][content*="noindex"]'),
    scripts: [...document.querySelectorAll('script[type="module"][src]')].length,
    islands: document.querySelectorAll('[data-island]').length,
  };
}"""

_AWAKE = """() => [...document.querySelectorAll('[data-island]')].filter((el) =>
  Object.keys(el).some((k) => k.startsWith('__reactContainer'))).length"""


# ------------------------------------------------------------------ serving a dist folder like a live site app

def _respond(root: Path, rel: str) -> tuple[int, bytes, str, dict[str, str]]:
    from . import service as AE
    try:
        last = rel.rsplit("/", 1)[-1]
        if rel and "." in last:
            data, ctype, hdr = AE._serve(root, rel, PREFIX, False, site=True)
        elif AE._is_site_page(root, rel):
            data, ctype, hdr = AE._serve(root, rel, PREFIX, False, site=True, cloud="/api/cloud/lab")
        else:
            data, ctype, hdr = AE._serve(root, rel, PREFIX, False)
        return 200, data, ctype, hdr
    except AE.AppEngineError:
        return 404, b"not found", "text/plain", {}


def serve(root: Path):
    """a local server for a built dist folder at /apps/lab/ (gzip for text, as a front door sends it)"""
    import http.server
    import socketserver

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):  # noqa: N802
            path = self.path.split("?", 1)[0]
            if not path.startswith(PREFIX):
                self.send_response(404)
                self.end_headers()
                return
            code, data, ctype, hdr = _respond(root, path[len(PREFIX):])
            zipped = "gzip" in (self.headers.get("Accept-Encoding") or "") and (
                ctype.startswith("text/") or "javascript" in ctype or "json" in ctype or "xml" in ctype or "svg" in ctype)
            if zipped:
                data = gzip.compress(data, 6)
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            if zipped:
                self.send_header("Content-Encoding", "gzip")
            for k, v in hdr.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}{PREFIX}"


def _browser(pw):
    exe = os.environ.get("HOOLA_CHROMIUM") or None
    return pw.chromium.launch(**({"executable_path": exe} if exe else {}))


def site_paths(dist: Path) -> list[str]:
    from . import service as AE
    pg = AE.pages_of(dist)
    return [p["path"] for p in pg.get("pages") or [] if p.get("kind") == "site"]


# ------------------------------------------------------------------ one page, measured

def _measure(b, url: str, kind: str) -> dict[str, Any]:
    ctx = b.new_context(**PHONE)
    pg = ctx.new_page()
    errs: list[str] = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:300]))
    pg.on("console", lambda m: errs.append(m.text[:300]) if m.type == "error" else None)
    sizes = {"script": 0, "stylesheet": 0, "font": 0, "image": 0, "document": 0, "other": 0}
    reqs = {"n": 0}

    def got(resp):
        try:
            rt = resp.request.resource_type
            sz = int((resp.headers or {}).get("content-length") or 0)
            if not sz:
                sz = len(resp.body())
            key = rt if rt in sizes else "other"
            sizes[key] += sz
            reqs["n"] += 1
        except Exception:  # noqa: BLE001 - a size we cannot read is left out, never guessed
            pass

    pg.on("response", got)
    cdp = ctx.new_cdp_session(pg)
    cdp.send("Network.enable")
    cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": THROTTLE["latency"],
                                                   "downloadThroughput": THROTTLE["downloadThroughput"],
                                                   "uploadThroughput": THROTTLE["uploadThroughput"]})
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": THROTTLE["cpu"]})
    pg.add_init_script(_OBSERVE)
    t0 = time.time()
    pg.goto(url, wait_until="load", timeout=90000)
    try:
        pg.wait_for_load_state("networkidle", timeout=20000)
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(1500)
    first = pg.evaluate("() => window.__hl")
    js_first = sizes["script"]
    seo = pg.evaluate(_SEO)
    # the visit: scroll to the bottom slowly so every island wakes; shifts it causes count in CLS
    h = pg.evaluate("() => document.documentElement.scrollHeight")
    y = 0
    while y < h:
        y += 600
        pg.evaluate(f"() => window.scrollTo(0, {y})")
        pg.wait_for_timeout(250)
    try:
        pg.wait_for_load_state("networkidle", timeout=20000)
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(800)
    after = pg.evaluate("() => window.__hl")
    awake = pg.evaluate(_AWAKE)
    fcp = float(first.get("fcp") or 0)
    tbt = sum(max(0.0, d - 50) for s, d in first.get("long") or [] if s >= fcp)
    out = {"kind": kind, "lcp_ms": round(float(first.get("lcp") or 0)), "fcp_ms": round(fcp), "tbt_ms": round(tbt),
           "cls": round(float(after.get("cls") or 0), 4), "load_s": round(time.time() - t0, 2),
           "js_first_kb": round(js_first / 1024, 1), "js_kb": round(sizes["script"] / 1024, 1), "css_kb": round(sizes["stylesheet"] / 1024, 1),
           "font_kb": round(sizes["font"] / 1024, 1), "image_kb": round(sizes["image"] / 1024, 1),
           "html_kb": round(sizes["document"] / 1024, 1), "requests": reqs["n"], "islands_awake": awake,
           "errors": errs[:10], "seo": seo}
    ctx.close()
    return out


def judge(p: dict[str, Any]) -> list[str]:
    """what a page got wrong against the budgets (empty = it passes)"""
    bad = []
    if not p.get("lcp_ms"):
        bad.append("no largest paint was recorded")
    elif p["lcp_ms"] > BUDGET["lcp_ms"]:
        bad.append(f"LCP {p['lcp_ms']} ms > {BUDGET['lcp_ms']}")
    if p["cls"] > BUDGET["cls"]:
        bad.append(f"CLS {p['cls']} > {BUDGET['cls']}")
    if p["tbt_ms"] > BUDGET["tbt_ms"]:
        bad.append(f"TBT {p['tbt_ms']} ms > {BUDGET['tbt_ms']}")
    if p["kind"] == "site" and p["js_first_kb"] > BUDGET["site_js_first_kb"]:
        bad.append(f"JavaScript for the first screen {p['js_first_kb']} KB > {BUDGET['site_js_first_kb']} on a site page")
    if p["kind"] == "site" and p["js_kb"] > BUDGET["site_js_kb"]:
        bad.append(f"JavaScript for the whole visit {p['js_kb']} KB > {BUDGET['site_js_kb']} on a site page")
    for k in ("image_kb", "font_kb", "css_kb"):
        if p[k] > BUDGET[k]:
            bad.append(f"{k.split('_')[0]} {p[k]} KB > {BUDGET[k]}")
    s = p.get("seo") or {}
    if not s.get("title"):
        bad.append("no page title")
    if s.get("h1") != 1:
        bad.append(f"{s.get('h1')} H1 headings (one is right)")
    if not s.get("noindex"):
        if not s.get("description") or s.get("description") == "Made with Hoola":
            bad.append("no description of its own")
        if not s.get("canonical"):
            bad.append("no canonical link")
    if not s.get("lang"):
        bad.append("no page language")
    if not s.get("jsonld_ok"):
        bad.append("JSON-LD that does not parse")
    if s.get("img_no_alt"):
        bad.append(f"{s['img_no_alt']} picture(s) without alt text")
    if s.get("islands") and p.get("islands_awake", 0) < 1:
        bad.append("its islands never woke up")
    if p.get("errors"):
        bad.append("page errors: " + "; ".join(p["errors"][:2]))
    return bad


def lab(dist: Path, paths: list[str] | None = None) -> dict[str, Any]:
    """measure the pages of a built dist folder; verdict PASS when every page meets every budget"""
    from playwright.sync_api import sync_playwright
    from . import service as AE
    pg = AE.pages_of(dist)
    kinds = {p["path"]: p.get("kind") for p in pg.get("pages") or []}
    paths = paths or [p for p in kinds] or ["/"]
    srv, base = serve(dist)
    pages = []
    try:
        with sync_playwright() as pw:
            b = _browser(pw)
            try:
                for path in paths:
                    m = _measure(b, base + path.lstrip("/"), kinds.get(path) or "app")
                    m["path"] = path
                    m["problems"] = judge(m)
                    pages.append(m)
            finally:
                b.close()
    finally:
        srv.shutdown()
    return {"verdict": "PASS" if pages and all(not p["problems"] for p in pages) else "FAIL", "pages": pages,
            "budget": BUDGET, "throttle": THROTTLE["name"], "mode": pg.get("mode") or "", "prerendered": bool(pg.get("ok")),
            "note": "lab numbers on this machine; real visitors' phones and networks differ"}


def walk_dist(dist: Path, paths: list[str]) -> dict[str, Any]:
    """the islands proof, unthrottled: each page loads clean, islands wake, an accordion opens, and with JavaScript off
    the page still has its words"""
    from playwright.sync_api import sync_playwright
    srv, base = serve(dist)
    out: dict[str, Any] = {}
    try:
        with sync_playwright() as pw:
            b = _browser(pw)
            try:
                for path in paths:
                    ctx = b.new_context(viewport={"width": 1280, "height": 900})
                    pg = ctx.new_page()
                    errs: list[str] = []
                    pg.on("pageerror", lambda e: errs.append(str(e)[:300]))
                    pg.on("console", lambda m: errs.append(m.text[:300]) if m.type == "error" else None)
                    pg.goto(base + path.lstrip("/"), wait_until="networkidle")
                    h = pg.evaluate("() => document.documentElement.scrollHeight")
                    for y in range(0, h + 900, 700):
                        pg.evaluate(f"() => window.scrollTo(0, {y})")
                        pg.wait_for_timeout(120)
                    pg.wait_for_load_state("networkidle")
                    pg.wait_for_timeout(500)
                    seo = pg.evaluate(_SEO)
                    opened = False
                    trig = pg.locator('[data-block="faq"] button[aria-expanded]')
                    if trig.count():
                        trig.first.click()
                        pg.wait_for_timeout(300)
                        opened = trig.first.get_attribute("aria-expanded") == "true"
                    out[path] = {"errors": errs, "h1": seo["h1"], "scripts": seo["scripts"], "islands": seo["islands"],
                                 "islands_awake": pg.evaluate(_AWAKE), "faq_opened": opened}
                    ctx.close()
                    nj = b.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
                    p2 = nj.new_page()
                    p2.goto(base + path.lstrip("/"), wait_until="load")
                    text = p2.inner_text("body")
                    # words a visitor with no script can see: nothing hidden waiting for code
                    hidden = p2.locator(".opacity-0:not([aria-hidden])").count()
                    out[path].update({"nojs_words": len(re.findall(r"\w+", text)), "nojs_hidden": hidden})
                    nj.close()
            finally:
                b.close()
    finally:
        srv.shutdown()
    return out


DIRECTIONS = ("warm_local", "luxury_dark", "tech_gradient")


def lab_check(directions: tuple[str, ...] | list[str] = DIRECTIONS) -> dict[str, Any]:
    """the D3 done-line on this server: build the proof site (a dental clinic: hero, services, reviews, FAQ, contact +
    an about page + an account page) as a SITE app in each design direction (a real D2 genome: its own colours and
    bundled fonts), pre-render it and measure its content pages in the lab"""
    import shutil
    import tempfile
    from . import genome as GN
    from . import kit as KIT
    from . import runner as RN
    av = RN.available()
    if not av["ok"]:
        return {"verdict": "NOT RUN", "why": av["why"]}
    runs = []
    for d in directions:
        tmp = Path(tempfile.mkdtemp(prefix="hoola-speed-"))
        try:
            src = KIT.gallery_dir("calm", tmp / "app")
            g = GN.generate(seed=f"speed-{d}", direction=d)
            (src / "src" / "styles" / "tokens.css").write_text(GN.css(g), "utf-8")
            GN.write_fonts(g, src / "src" / "styles" / "fonts")
            (src / "hoola.render.json").write_text(json.dumps({"mode": "site"}))
            (src / "src" / "App.tsx").write_text(PROOF_APP, "utf-8")
            t0 = time.time()
            b = RN.build(src, wait=120.0, source=False)
            if not b.get("ok"):
                runs.append({"direction": d, "verdict": "FAIL", "why": "the proof site did not build: " + (b.get("why") or ""),
                             "pages": []})
                continue
            dist = Path(b["dist"])
            rep = lab(dist, site_paths(dist))
            rep.update({"direction": d, "build_s": round(time.time() - t0, 1), "prerender": b.get("prerender"),
                        "fonts": [f for _, _, _, f in GN.fonts_used(g)][:6]})
            shutil.rmtree(b.get("out_dir") or "/nonexistent", ignore_errors=True)
            runs.append(rep)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return {"verdict": "PASS" if runs and all(r["verdict"] == "PASS" for r in runs) else "FAIL", "runs": runs,
            "budget": BUDGET, "throttle": THROTTLE["name"],
            "note": "lab numbers on this machine; real visitors' phones and networks differ"}


def say(rep: dict[str, Any]) -> str:
    """the lab report in plain lines"""
    if rep.get("verdict") == "NOT RUN":
        return "Speed lab not run: " + rep.get("why", "")
    out = [f"Speed lab {rep['verdict']} ({rep['throttle']})"]
    for r in rep.get("runs") or []:
        out.append(f"  {r.get('direction')}: {r['verdict']}" + (f" - {r['why']}" if r.get("why") else ""))
        for p in r.get("pages") or []:
            out.append(f"    {p['path']:<10} LCP {p['lcp_ms']} ms  CLS {p['cls']}  TBT {p['tbt_ms']} ms  JS first {p['js_first_kb']} KB / "
                       f"visit {p['js_kb']} KB  fonts {p['font_kb']} KB" + (("  PROBLEMS: " + "; ".join(p["problems"])) if p["problems"] else ""))
    out.append("  " + rep.get("note", ""))
    return "\n".join(out)


PROOF_APP = '''import { Routes, Route, Link } from "react-router-dom";
import { Seo, AppPage } from "@/lib/seo";
import Hero from "@/components/blocks/hero";
import ServicesGrid from "@/components/blocks/services-grid";
import Reviews from "@/components/blocks/reviews";
import Faq from "@/components/blocks/faq";
import ContactBlock from "@/components/blocks/contact-block";
import IntroStory from "@/components/blocks/intro-story";
import Team from "@/components/blocks/team";
import ScreenTable from "@/components/blocks/screen-table";

function Nav() {
  return (
    <header className="border-b border-line">
      <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-4 text-sm font-medium">
        <Link to="/" className="font-head text-lg text-ink">Asha Dental</Link>
        <Link to="/about">About</Link>
        <Link to="/account">Your visits</Link>
      </nav>
    </header>
  );
}
function Home() {
  return (
    <>
      <Seo title="Asha Dental - gentle dental care in Ramdaspeth, Nagpur" description="Check-ups, cleaning, braces and root canals in Ramdaspeth, Nagpur. Open six days a week; book on WhatsApp."
           jsonLd={{ "@type": "Dentist", name: "Asha Dental", address: { "@type": "PostalAddress", addressLocality: "Nagpur" } }} />
      <Nav />
      <main>
        <Hero />
        <ServicesGrid />
        <Reviews />
        <Faq />
        <ContactBlock />
      </main>
    </>
  );
}
function About() {
  return (
    <>
      <Seo title="About Asha Dental, Nagpur" description="Dr Asha Kulkarni has cared for families in Ramdaspeth since 2009." />
      <Nav />
      <main>
        <h1 className="sr-only">About Asha Dental</h1>
        <IntroStory />
        <Team />
      </main>
    </>
  );
}
function Account() {
  return (
    <AppPage>
      <Seo title="Your visits" noindex />
      <Nav />
      <ScreenTable />
    </AppPage>
  );
}
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/about" element={<About />} />
      <Route path="/account" element={<Account />} />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
'''
