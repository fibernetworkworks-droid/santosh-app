"""Screenshots and steps from HER live product (real Chromium, Playwright).

Safety, in code:
- runs only the safe step language (rules.validate_steps): goto / click / fill / select / press / wait / scroll / hover /
  screenshot. Hoola never evaluates JavaScript she or anyone else wrote; the only scripts are the fixed ones in this file.
- top-level pages stay on her verified host; every request must go to a public address (no localhost / VPS / private
  network; `ALLOW_PRIVATE` only for tests); no downloads, no permissions, service workers blocked.
- a box for a password / OTP / PIN / card number is never filled (checked on the real element before typing).
- personal data on screen (e-mails, phone numbers, Aadhaar / PAN / card-like numbers, password boxes, the boxes she asked to
  hide) is covered with a SOLID box before the file is saved (Google style guide: blur / mosaic can be reversed).
- the element a step talks about gets a highlight frame and a numbered badge (Pillow), like a technical writer's callout."""
from __future__ import annotations

import io
import ipaddress
import logging
import os
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from . import rules as R

log = logging.getLogger("santosh.docwriter")
ALLOW_PRIVATE = False            # tests only
STEP_TIMEOUT_MS = 9000
ACCENT = (255, 106, 0)
MASK = (31, 41, 51)

MASK_JS = r"""(rx) => {
  const re = new RegExp(rx, 'g'); const out = [];
  const add = r => { if (r.width > 1 && r.height > 1 && r.bottom > 0 && r.right > 0) out.push([r.left, r.top, r.width, r.height]); };
  document.querySelectorAll('input[type=password],input[autocomplete^="cc-"],input[autocomplete="one-time-code"]').forEach(e => add(e.getBoundingClientRect()));
  const w = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
  let n, count = 0;
  while ((n = w.nextNode()) && count < 400) {
    const t = n.textContent; if (!t || t.length < 6) continue; re.lastIndex = 0; let m;
    while ((m = re.exec(t)) && count < 400) { count++;
      const rg = document.createRange(); rg.setStart(n, m.index); rg.setEnd(n, m.index + m[0].length);
      for (const r of rg.getClientRects()) add(r); }
  }
  document.querySelectorAll('input,textarea').forEach(e => { const v = e.value || ''; re.lastIndex = 0; if (v && re.test(v)) add(e.getBoundingClientRect()); });
  return out;
}"""
BOX_JS = r"""(e) => { const lab = e.labels && e.labels[0] ? e.labels[0].textContent : '';
  return [e.type || '', e.name || '', e.id || '', e.getAttribute('autocomplete') || '', e.getAttribute('aria-label') || '',
          e.getAttribute('placeholder') || '', lab || ''].join(' '); }"""


class CaptureError(Exception):
    pass


def available() -> str:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return "playwright"
    return ""


_PUBLIC: dict[str, bool] = {}


def public_host(host: str) -> bool:
    if ALLOW_PRIVATE:
        return True
    host = (host or "").lower()
    if host in _PUBLIC:
        return _PUBLIC[host]
    ok = False
    try:
        infos = socket.getaddrinfo(host, None)
        ok = bool(infos) and all(ipaddress.ip_address(i[4][0]).is_global for i in infos)
    except (socket.gaierror, ValueError, UnicodeError):
        ok = False
    _PUBLIC[host] = ok
    return ok


def _launch(p):
    kw: dict[str, Any] = {"args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--force-color-profile=srgb"]}
    if os.environ.get("HOOLA_CHROMIUM"):
        kw["executable_path"] = os.environ["HOOLA_CHROMIUM"]
    return p.chromium.launch(**kw)


def _loc(page, t: dict[str, str]):
    if "role" in t:
        return page.get_by_role(t["role"], name=t.get("name") or None).first
    if "label" in t:
        return page.get_by_label(t["label"]).first
    if "placeholder" in t:
        return page.get_by_placeholder(t["placeholder"]).first
    if "testid" in t:
        return page.get_by_test_id(t["testid"]).first
    if "alt" in t:
        return page.get_by_alt_text(t["alt"]).first
    if "title" in t:
        return page.get_by_title(t["title"]).first
    if "css" in t:
        return page.locator(t["css"]).first
    return page.get_by_text(t["text"]).first


def ahash(png: bytes) -> str:
    """Tiny average hash (8x8 grey) for 'did this screen change since the last shoot?'."""
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("L").resize((16, 16))
    px = list(im.tobytes())
    avg = sum(px) / len(px)
    bits = "".join("1" if p > avg else "0" for p in px)
    return f"{int(bits, 2):064x}"


def hash_distance(a: str, b: str) -> int:
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 256


def annotate(png: bytes, scale: float, masks: list[list[float]], box: list[float] | None, number: int | None) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(io.BytesIO(png)).convert("RGB")
    d = ImageDraw.Draw(im)
    for x, y, w, h in masks:
        d.rectangle([x * scale - 2, y * scale - 2, (x + w) * scale + 2, (y + h) * scale + 2], fill=MASK)
    if box:
        x, y, w, h = (v * scale for v in box)
        pad = 4 * scale
        d.rounded_rectangle([x - pad, y - pad, x + w + pad, y + h + pad], radius=int(6 * scale), outline=ACCENT, width=max(3, int(3 * scale)))
        if number:
            r = 13 * scale
            cx, cy = max(r + 2, x - pad), max(r + 2, y - pad)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT, outline=(255, 255, 255), width=max(2, int(2 * scale)))
            try:
                font = ImageFont.load_default(size=int(15 * scale))
            except TypeError:
                font = ImageFont.load_default()
            label = str(number)
            tw = d.textlength(label, font=font)
            d.text((cx - tw / 2, cy - 9 * scale), label, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def run(base_url: str, steps: list[dict[str, Any]], out_dir: Path, device: str = "phone", product: str = "",
        lang: str = "en", hide: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Walk the steps; returns {shots: [{step, file, alt, hash, box}], log: [...], error}."""
    if available():
        raise CaptureError("Playwright / Chromium nahi hai (VPS: bash ~/santosh_app/server/deploy/setup_sites.sh)")
    from playwright.sync_api import Error as PwError
    from playwright.sync_api import sync_playwright
    host = (urlparse(base_url).hostname or "").lower()
    if not host or urlparse(base_url).scheme not in ("http", "https"):
        raise CaptureError("Product ka link http(s) hona chahiye")
    if not public_host(host):
        raise CaptureError("Yeh address public internet par nahi; Hoola ise nahi kholega")
    w, h, dsf, mobile = R.VIEWPORTS.get(device, R.VIEWPORTS["phone"])
    out_dir.mkdir(parents=True, exist_ok=True)
    shots: list[dict[str, Any]] = []
    logs: list[str] = []
    blocked: list[str] = []
    error = ""

    def guard(route):
        req = route.request
        u = urlparse(req.url)
        if u.scheme in ("data", "blob", "about"):
            return route.continue_()
        if u.scheme not in ("http", "https") or not u.hostname or not public_host(u.hostname):
            blocked.append(req.url[:120])
            return route.abort()
        if req.is_navigation_request() and req.frame == req.frame.page.main_frame and not R.same_site(u.hostname, host):
            blocked.append(req.url[:120])
            return route.abort()
        return route.continue_()

    with sync_playwright() as p:
        b = _launch(p)
        try:
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dsf, is_mobile=mobile, has_touch=mobile,
                                accept_downloads=False, service_workers="block", permissions=[], reduced_motion="reduce",
                                locale="en-IN", timezone_id="Asia/Kolkata")
            ctx.route("**/*", guard)
            page = ctx.new_page()
            page.set_default_timeout(STEP_TIMEOUT_MS)
            page.goto(base_url, wait_until="load")
            n = 0
            for i, st in enumerate(steps, 1):
                do = st["do"]
                try:
                    target = None
                    if st.get("target"):
                        target = _loc(page, st["target"])
                        target.wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
                        target.scroll_into_view_if_needed(timeout=STEP_TIMEOUT_MS)
                    if do in ("fill", "select") and target is not None:
                        what = target.evaluate(BOX_JS)
                        if R.SECRET_BOX.search(what):
                            raise R.StepError(f"step {i}: yeh password / OTP / PIN / card ka box hai; Hoola isme nahi bharta")
                    if st.get("shot"):          # taken BEFORE the action: shows where to tap / what to fill
                        n += 1
                        shots.append(_shoot(page, target, out_dir, i, n, dsf, st, product, lang, hide or []))
                    if do == "goto":
                        url = urljoin(base_url, st["url"])
                        if not R.same_site(urlparse(url).hostname or "", host):
                            raise R.StepError(f"step {i}: sirf {host} ke pages")
                        page.goto(url, wait_until="load")
                    elif do == "click":
                        target.click()
                    elif do == "fill":
                        target.fill(st.get("value", ""))
                    elif do == "select":
                        try:
                            target.select_option(label=st.get("value", ""))
                        except PwError:
                            target.select_option(st.get("value", ""))
                    elif do == "press":
                        page.keyboard.press(st["key"])
                    elif do == "hover":
                        target.hover()
                    elif do == "scroll":
                        page.mouse.wheel(0, st.get("y", 600))
                    elif do == "wait":
                        page.wait_for_timeout(st.get("ms", 800))
                    if do in ("goto", "click", "press", "select"):
                        try:
                            page.wait_for_load_state("load", timeout=4000)
                        except PwError:
                            pass
                        page.wait_for_timeout(250)
                    logs.append(f"{i}. {do} ok")
                except R.StepError as e:
                    error = str(e)
                    break
                except PwError as e:
                    error = f"step {i} ({do}) nahi hua: " + str(e).splitlines()[0][:160]
                    break
            ctx.close()
        finally:
            b.close()
    return {"shots": shots, "log": logs, "error": error, "blocked": blocked[:10]}


def _shoot(page, target, out_dir: Path, step: int, n: int, dsf: float, st: dict[str, Any], product: str, lang: str,
           hide: list[dict[str, str]]) -> dict[str, Any]:
    box = None
    if target is not None:
        bb = target.bounding_box()
        if bb:
            box = [bb["x"], bb["y"], bb["width"], bb["height"]]
    masks = page.evaluate(MASK_JS, R.PII_JS_RX) or []
    for t in list(hide) + list(st.get("mask") or []):
        try:
            bb = _loc(page, t).bounding_box(timeout=1500)
            if bb:
                masks.append([bb["x"], bb["y"], bb["width"], bb["height"]])
        except Exception:
            continue
    raw = page.screenshot(type="png")
    png = annotate(raw, dsf, masks, box, n if box else None)
    name = f"step{step:02d}.png"
    (out_dir / name).write_bytes(png)
    sentence = R.step_sentence(st, lang).replace("**", "") if st["do"] != "screenshot" else ""
    alt = st.get("alt") or (f"{product}: " if product else "") + (sentence or (page.title() or "screen"))
    alt = alt.strip()[:154]
    if alt and alt[-1] not in ".!?।":
        alt += "."
    return {"step": step, "n": n, "file": name, "alt": alt, "hash": ahash(raw), "box": bool(box), "masked": len(masks),
            "title": (page.title() or "")[:120], "path": urlparse(page.url).path[:200]}
