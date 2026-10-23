"""v0.128 Real-browser pass over the prototype (Playwright Chromium, network blocked, files served from disk): every screen
on Android and iPhone at 390 x 844 (x2) -> screenshots + thumbnails + an 'all screens' sheet, and the checks per screen at
360 and 390 px wide:

blocking - wider than the phone, image without alt / input without a label, a button that goes to a screen that does not
exist, a tap target smaller than 30 px, low-contrast text (WCAG AA), a card / CVV / UPI PIN / password field, console errors;
warnings - tap targets under 44 px, text smaller than 11 px, clipped text, screens nobody can reach, [blanks] left."""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Any

from ..site import checks as SC

log = logging.getLogger("santosh.app")
ORIGIN = SC.ORIGIN
W, H, SCALE = 390, 844, 2

CHECK_JS = r"""(narrow) => {
  const scr = document.querySelector('.scr.on'); const out = {issues: [], warn: [], gos: [], blanks: 0};
  if (!scr) return out;
  const vw = window.innerWidth;
  const visible = e => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && !e.closest('.sheet:not(.open)'); };
  const inScroller = e => { for (let p = e.parentElement; p && p !== scr; p = p.parentElement) { const o = getComputedStyle(p).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden') return true; } return false; };
  const wide = [...scr.querySelectorAll('*')].filter(e => { if (!visible(e) || inScroller(e)) return false;
    const r = e.getBoundingClientRect(); return r.right > vw + 1.5 || r.left < -1.5; });
  if (wide.length) out.issues.push({kind: 'overflow', text: 'Screen is wider than the phone at ' + vw + ' px (' +
    (wide[0].className || wide[0].tagName).toString().slice(0, 40) + ')'});
  scr.querySelectorAll('img').forEach(i => { if (!i.hasAttribute('alt')) out.issues.push({kind: 'alt', text: 'Image without alt text'}); });
  scr.querySelectorAll('input,textarea,select').forEach(i => {
    if (i.type === 'hidden') return;
    const lab = i.id && scr.querySelector('label[for="' + i.id + '"]');
    if (!lab && !i.closest('label') && !i.getAttribute('aria-label') && !i.getAttribute('placeholder'))
      out.issues.push({kind: 'label', text: 'Input without a label'});
    const n = ((i.name || '') + ' ' + (i.placeholder || '') + ' ' + (i.getAttribute('aria-label') || '') + ' ' +
      ((i.closest('label') || {}).textContent || '')).toLowerCase();
    if (/(card number|card no|cvv|cvc|expiry|upi pin|\bmpin\b|password|pass code|passcode|atm pin)/.test(n))
      out.issues.push({kind: 'secret', text: 'Card / CVV / PIN / password field is not allowed in the app: ' + n.trim().slice(0, 40)});
  });
  const rgba = c => { if (!c) return null; let m = c.match(/[\d.]+/g), k = c.startsWith('color(srgb') ? 255 : 1;
    if (!m || m.length < 3) return null; return {r: +m[0] * k, g: +m[1] * k, b: +m[2] * k, a: m.length > 3 ? +m[3] : 1}; };
  const L = o => { const v = [o.r, o.g, o.b].map(x => { x = x / 255; return x <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); });
    return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;
      if (cs.backdropFilter && cs.backdropFilter !== 'none') return null;
      const c = rgba(cs.backgroundColor); if (c && c.a > .9) return c; }
    return rgba(getComputedStyle(document.body).backgroundColor); };
  let bad = 0, tiny = 0;
  [...scr.querySelectorAll('h1,h2,h3,p,li,a,span,button,label,dt,dd,b,strong,output')].slice(0, 500).forEach(el => {
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
    if (!visible(el)) return;
    const cs = getComputedStyle(el); if (+cs.opacity < .5) return;
    if (parseFloat(cs.fontSize) < 11 && tiny < 3) { tiny++; out.warn.push({kind: 'small_text', text: 'Text smaller than 11 px: ' + el.textContent.trim().slice(0, 30)}); }
    const f0 = rgba(cs.color), bg = bgOf(el); if (!f0 || !bg) return;
    const fg = {r: f0.r * f0.a + bg.r * (1 - f0.a), g: f0.g * f0.a + bg.g * (1 - f0.a), b: f0.b * f0.a + bg.b * (1 - f0.a)};
    const a = L(fg), b = L(bg); const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    const large = parseFloat(cs.fontSize) >= 24 || (parseFloat(cs.fontSize) >= 18.6 && +cs.fontWeight >= 700);
    if (ratio < (large ? 3 : 4.5) && bad < 4) { bad++; out.issues.push({kind: 'contrast', text: 'Low contrast text (' + ratio.toFixed(1) + ':1): ' + el.textContent.trim().slice(0, 36)}); }
  });
  let small = 0, tooSmall = 0;
  scr.querySelectorAll('button,a,[data-go],[data-sheet],.chip,input[type=checkbox]').forEach(e => {
    if (!visible(e) || e.closest('.stepper') && e.tagName !== 'BUTTON') return;
    const r = (e.tagName === 'INPUT' && e.closest('label') ? e.closest('label') : e).getBoundingClientRect();
    if (Math.max(r.width, r.height) < 30) tooSmall++; else if (Math.min(r.width, r.height) < 34 && Math.max(r.width, r.height) < 44) small++;
  });
  if (tooSmall) out.issues.push({kind: 'tap', text: tooSmall + ' tap target(s) smaller than 30 px'});
  if (small) out.warn.push({kind: 'tap', text: small + ' small tap target(s) (under 44 px)'});
  const clipped = [...scr.querySelectorAll('.btn,.chip,.ab-title,.t-title,.price')].filter(e => visible(e) && e.scrollWidth > e.clientWidth + 2 &&
    getComputedStyle(e).textOverflow !== 'ellipsis');
  if (clipped.length) out.warn.push({kind: 'clip', text: 'Text cut off: ' + clipped[0].textContent.trim().slice(0, 30)});
  out.blanks = scr.querySelectorAll('em.blank').length;
  scr.querySelectorAll('[data-go]').forEach(e => out.gos.push(e.getAttribute('data-go')));
  return out;
}"""


class RenderError(Exception):
    pass


def available() -> str:
    return SC.available()


def _thumb(src: bytes, width: int = 240) -> bytes:
    from PIL import Image
    im = Image.open(io.BytesIO(src)).convert("RGB")
    h = round(im.height * width / im.width)
    im = im.resize((width, h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True)
    return buf.getvalue()


def sheet(paths: list[tuple[str, Path]], dest: Path, cols: int = 4, width: int = 220) -> None:
    """All screens on one image (labels under each)."""
    from PIL import Image, ImageDraw, ImageFont
    if not paths:
        return
    th = []
    for label, p in paths:
        try:
            im = Image.open(p).convert("RGB")
        except OSError:
            continue
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        th.append((label, im))
    if not th:
        return
    pad, lab_h = 18, 26
    ch = max(im.height for _, im in th)
    rows = (len(th) + cols - 1) // cols
    sheet_im = Image.new("RGB", (pad + cols * (width + pad), pad + rows * (ch + lab_h + pad)), (238, 240, 244))
    d = ImageDraw.Draw(sheet_im)
    try:
        font = ImageFont.load_default(size=15)
    except TypeError:
        font = ImageFont.load_default()
    for i, (label, im) in enumerate(th):
        x = pad + (i % cols) * (width + pad)
        y = pad + (i // cols) * (ch + lab_h + pad)
        sheet_im.paste(im, (x, y))
        d.text((x + 2, y + im.height + 6), label[:28], fill=(30, 30, 36), font=font)
    sheet_im.save(dest, "JPEG", quality=82, optimize=True)


def run(out: Path, order: list[str], shots: Path, labels: dict[str, str], platforms: tuple[str, ...] = ("android", "ios"),
        only: list[str] | None = None, check: bool = True, alt: bool = True, extras: bool = True) -> dict[str, Any]:
    """Screenshots (+ checks) for the screens in `order` (or just `only`): Android + iPhone in the app's own colour mode,
    plus Android in the other mode (light <-> dark) with its own contrast check; the open side bar and the open speed dial
    as extra pictures. Returns {screens: {sid: {issues, warn, gos, blanks, shots}}, console, extras}."""
    if available():
        raise RenderError("Playwright / Chromium nahi hai (VPS: bash ~/santosh_app/server/deploy/setup_sites.sh)")
    from playwright.sync_api import sync_playwright
    shots.mkdir(parents=True, exist_ok=True)
    (shots / "thumb").mkdir(exist_ok=True)
    want = [s for s in order if not only or s in only]
    res: dict[str, Any] = {"screens": {s: {"issues": [], "warn": [], "gos": [], "blanks": 0, "shots": {}} for s in want},
                           "console": [], "extras": {}}
    passes = [(p, False) for p in platforms] + ([("android", True)] if alt and "android" in platforms else [])
    counter: dict[str, int] = {}
    with sync_playwright() as p:
        b = SC._launch(p)
        try:
            for plat, is_alt in passes:
                ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=SCALE, is_mobile=True, has_touch=True,
                                    reduced_motion="reduce")
                ctx.route("**/*", SC._serve(out, counter))
                page = ctx.new_page()
                errs: list[str] = []
                page.on("console", lambda m, errs=errs: errs.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
                page.goto(f"{ORIGIN}/index.html?p={plat}&shot=1&m={'alt' if is_alt else 'base'}&s={want[0] if want else ''}",
                          wait_until="load")
                page.evaluate("document.fonts.ready")
                suffix = f"{plat}-alt" if is_alt else plat
                for sid in want:
                    if not page.evaluate("(id) => window.HoolaProto && window.HoolaProto.show(id)", sid):
                        res["screens"][sid]["issues"].append({"kind": "missing", "text": "Screen did not open"})
                        continue
                    page.wait_for_timeout(60)
                    img = page.screenshot(type="jpeg", quality=84)
                    name = f"{sid}-{suffix}.jpg"
                    (shots / name).write_bytes(img)
                    (shots / "thumb" / name).write_bytes(_thumb(img))
                    res["screens"][sid]["shots"][suffix] = name
                    if check and plat == "android":
                        r = page.evaluate(CHECK_JS, False)
                        if is_alt:          # the other colour mode: only colour problems matter here
                            for it in r.get("issues") or []:
                                if it["kind"] == "contrast":
                                    res["screens"][sid]["issues"].append({**it, "text": it["text"] + " (doosre mode mein)"})
                        else:
                            for k in ("issues", "warn"):
                                res["screens"][sid][k] += r.get(k) or []
                            res["screens"][sid]["gos"] = sorted(set(r.get("gos") or []))
                            res["screens"][sid]["blanks"] = r.get("blanks") or 0
                if extras and not is_alt and want:
                    tab = page.evaluate("() => (document.querySelector('[data-tabbtn]') || {}).getAttribute ? "
                                        "document.querySelector('[data-tabbtn]').getAttribute('data-tabbtn') : ''")
                    if tab and tab in want:
                        page.evaluate("(id) => window.HoolaProto.show(id)", tab)
                        if page.evaluate("() => window.HoolaProto.drawer(true)"):
                            page.wait_for_timeout(60)
                            n = f"_drawer-{plat}.jpg"
                            (shots / n).write_bytes(page.screenshot(type="jpeg", quality=84))
                            res["extras"][f"drawer-{plat}"] = n
                            page.evaluate("() => window.HoolaProto.drawer(false)")
                        tabs_all = page.evaluate("() => [...document.querySelectorAll('[data-tabbtn]')]"
                                                 ".map(b => b.getAttribute('data-tabbtn'))") or [tab]
                        for t2 in [tab] + [x for x in tabs_all if x != tab and x in want]:
                            # the FAB menu on the first tab that has no bottom action bar of its own
                            page.evaluate("(id) => window.HoolaProto.show(id)", t2)
                            if page.evaluate("() => !!document.querySelector('.fabx .fab-actions') && "
                                             "!document.querySelector('.frame.has-bar') && window.HoolaProto.fab(true)"):
                                page.wait_for_timeout(60)
                                n = f"_fab-{plat}.jpg"
                                (shots / n).write_bytes(page.screenshot(type="jpeg", quality=84))
                                res["extras"][f"fab-{plat}"] = n
                                page.evaluate("() => window.HoolaProto.fab(false)")
                                break
                if errs:
                    res["console"] += [e[:200] for e in errs[:5]]
                ctx.close()
            if check:            # narrow phones (360 px): only the overflow / clipping problems
                ctx = b.new_context(viewport={"width": 360, "height": 760}, device_scale_factor=1, is_mobile=True, reduced_motion="reduce")
                ctx.route("**/*", SC._serve(out, counter))
                page = ctx.new_page()
                page.goto(f"{ORIGIN}/index.html?p=android&shot=1&s={want[0] if want else ''}", wait_until="load")
                for sid in want:
                    if not page.evaluate("(id) => window.HoolaProto && window.HoolaProto.show(id)", sid):
                        continue
                    r = page.evaluate(CHECK_JS, True)
                    for it in r.get("issues") or []:
                        if it["kind"] == "overflow" and not any(x["kind"] == "overflow" for x in res["screens"][sid]["issues"]):
                            res["screens"][sid]["issues"].append(it)
                ctx.close()
        finally:
            b.close()
    return res


def page_shot(html_file: Path, dest: Path, width: int = 1280, max_height: int = 2400) -> None:
    """A picture of one local page (the ER diagram): network blocked, only that file's folder served."""
    if available():
        raise RenderError("Playwright / Chromium nahi hai")
    from playwright.sync_api import sync_playwright
    html_file = Path(html_file)
    counter: dict[str, int] = {}
    with sync_playwright() as p:
        b = SC._launch(p)
        try:
            ctx = b.new_context(viewport={"width": width, "height": 900}, device_scale_factor=1)
            ctx.route("**/*", SC._serve(html_file.parent, counter))
            page = ctx.new_page()
            page.goto(f"{ORIGIN}/{html_file.name}", wait_until="load")
            h = min(max_height, page.evaluate("document.documentElement.scrollHeight"))
            page.set_viewport_size({"width": width, "height": max(400, h)})
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(page.screenshot(type="jpeg", quality=82))
            ctx.close()
        finally:
            b.close()


def scene_png(scene: dict[str, Any], colours: dict[str, str], dest: Path, size: int = 720) -> None:
    """v0.140 one still picture of an app's 3D scene (transparent PNG) for the native Android app, drawn by the same
    scene runtime as the prototype. Network blocked; only the scene runtime + data are served."""
    if available():
        raise RenderError("Playwright / Chromium nahi hai")
    import json as _json
    import shutil as _sh
    import tempfile
    from playwright.sync_api import sync_playwright
    from . import artdirect as AD
    assets = Path(__file__).with_name("assets")
    var = {"primary": "--c-primary", "accent": "--c-accent", "ink": "--c-ink", "surface": "--c-surface", "bg": "--c-bg",
           "muted": "--c-muted", "tint": "--c-tint"}
    style = ";".join(f"{var[k]}:{v}" for k, v in colours.items() if k in var and re.fullmatch(r"#[0-9a-fA-F]{6}", str(v or "")))
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _sh.copy(assets / "three.min.js", d / "three.min.js")
        _sh.copy(assets / "scene3d.js", d / "scene3d.js")
        (d / "scene.js").write_text("window.__s = " + _json.dumps(AD.clean_scene(scene) or {}) + ";\n"
                                    "window.__ok = !!HoolaScene.build(document.getElementById('s'), window.__s, {still: true, t: 1.2});\n")
        (d / "index.html").write_text(f'<!doctype html><html><body style="margin:0;background:transparent;{style}">'
                                      f'<div id="s" style="width:{size // 2}px;height:{size // 2}px"></div><script src="three.min.js">'
                                      f'</script><script src="scene3d.js"></script><script src="scene.js"></script></body></html>')
        counter: dict[str, int] = {}
        with sync_playwright() as p:
            b = SC._launch(p)
            try:
                ctx = b.new_context(viewport={"width": size // 2, "height": size // 2}, device_scale_factor=2)
                ctx.route("**/*", SC._serve(d, counter))
                page = ctx.new_page()
                page.goto(f"{ORIGIN}/index.html", wait_until="load")
                page.wait_for_timeout(400)
                if not page.evaluate("window.__ok === true"):
                    raise RenderError("3D scene nahi bani (WebGL)")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(page.locator("#s").screenshot(type="png", omit_background=True))
                ctx.close()
            finally:
                b.close()


def graph_problems(order: list[str], tabs: list[str], start: str, results: dict[str, Any], known: set[str]) -> dict[str, list[dict]]:
    """Links to screens that don't exist (blocking) and screens nobody can reach (warning)."""
    out: dict[str, list[dict]] = {}
    edges: dict[str, set[str]] = {}
    for sid, r in results.items():
        for g in r.get("gos") or []:
            if g not in known:
                out.setdefault(sid, []).append({"kind": "dead_link", "text": f"A button goes to '{g}', which is not a screen", "blocking": True})
            else:
                edges.setdefault(sid, set()).add(g)
    seen, todo = set(), [start] + list(tabs)
    while todo:
        s = todo.pop()
        if s in seen:
            continue
        seen.add(s)
        todo += list(edges.get(s, ()))
    for sid in order:
        if sid in results and sid not in seen:
            out.setdefault(sid, []).append({"kind": "unreachable", "text": "No button leads to this screen yet", "blocking": False})
    return out


SECRET_RE = re.compile(r"(card\s*number|cvv|cvc|upi\s*pin|\bmpin\b|atm\s*pin|net\s*banking\s*password)", re.I)
