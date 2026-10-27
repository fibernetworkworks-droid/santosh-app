"""Runs test cases in real Chromium (Playwright). Every request goes through one route handler:

- disk targets (a Hoola-built site version or app prototype): files are served from her build folder at a made-up origin;
  nothing else is reachable; form POSTs get a fake 200 (nothing is sent anywhere).
- her own website (ownership verified): only public addresses; pages of OTHER sites are never opened (a click that leaves her
  site is stopped); third-party scripts / styles / pictures load as GET only; payment gateways never get a request beyond
  their scripts; POST / PUT / DELETE to her site only when she switched on "forms may submit" for a staging site.

Clicks on pay / checkout / place order are refused (blocked, not a bug), a card / CVV / OTP / UPI PIN box is never filled, a
password box only takes {account.password} (her TEST account, typed in the app, opened here only). The model never writes
JavaScript: the JS below is Hoola's own, fixed code for audits."""
from __future__ import annotations

import ipaddress
import logging
import mimetypes
import random
import re
import socket
import string
import threading
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

from . import rules as R
from .steps import describe

log = logging.getLogger("santosh.qa")
DISK_ORIGIN = {"site": "https://site.hoola.qa", "app": "https://app.hoola.qa"}
STEP_TIMEOUT_MS = 8000
NAV_TIMEOUT_MS = 30000
CASE_LIMIT_S = 90
NET_FULFILL: Callable[[Any], bool] | None = None      # tests: serve a fake host (returns True when it answered)
_PUB: dict[str, bool] = {}
_PUB_LOCK = threading.Lock()


class StepFail(Exception):
    def __init__(self, message: str, expected: str = "", actual: str = ""):
        super().__init__(message)
        self.expected, self.actual = expected, actual


class Blocked(Exception):
    pass


def available() -> str:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return "Testing ke liye server par Playwright + Chromium chahiye (deploy/setup_sites.sh)."
    return ""


def is_public(host: str) -> bool:
    host = (host or "").lower()
    with _PUB_LOCK:
        if host in _PUB:
            return _PUB[host]
    ok = False
    try:
        infos = socket.getaddrinfo(host, None)
        ok = bool(infos) and all(ipaddress.ip_address(i[4][0]).is_global for i in infos)
    except (socket.gaierror, ValueError, OSError):
        ok = False
    with _PUB_LOCK:
        _PUB[host] = ok
    return ok


class Source:
    """Where the pages come from + the network rules for this run."""

    def __init__(self, kind: str, root: Path | None = None, url: str = "", host: str = "", allow_writes: bool = False,
                 start: str = "/"):
        self.kind = kind                        # disk kinds: site | app ; net: url
        self.root = root
        self.disk = kind in DISK_ORIGIN
        self.origin = DISK_ORIGIN[kind] if self.disk else f"https://{host}"
        self.host = urlparse(self.origin).hostname or host
        self.allow_writes = allow_writes
        self.start = start or "/"
        self.notes: list[str] = []
        self.mixed: list[str] = []
        self.doc_headers: dict[str, str] = {}

    def own(self, host: str) -> bool:
        host = (host or "").lower()
        return host == self.host or host.endswith("." + self.host) or (self.host.startswith("www.") and host == self.host[4:])

    def url(self, path: str) -> str:
        if re.match(r"^https?://", path or "", re.I):
            if not self.own(urlparse(path).hostname or ""):
                raise Blocked("Doosri website nahi kholi jaati: sirf aapki apni site.")
            return path
        return urljoin(self.origin + "/", (path or "/").lstrip("/") if not (path or "").startswith("?") else path)

    def _serve_disk(self, route) -> None:
        req = route.request
        p = urlparse(req.url)
        if req.method not in ("GET", "HEAD"):
            self.notes.append(f"form {req.method} {p.path} (preview: kahin bheja nahi gaya)")
            route.fulfill(status=200, body='{"ok":true}', headers={"Content-Type": "application/json"})
            return
        rel = p.path.lstrip("/")
        assert self.root is not None
        f = self.root / rel
        if not rel or rel.endswith("/"):
            f = f / "index.html"
        try:
            f = f.resolve()
            f.relative_to(self.root.resolve())
        except (ValueError, OSError):
            route.fulfill(status=404, body="not found")
            return
        if f.is_dir():
            f = f / "index.html"
        if not f.is_file():
            route.fulfill(status=404, body="not found", headers={"Content-Type": "text/html"})
            return
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if f.suffix == ".woff2":
            ctype = "font/woff2"
        route.fulfill(status=200, body=f.read_bytes(), headers={"Content-Type": ctype})

    def handler(self, route) -> None:
        req = route.request
        url = req.url
        p = urlparse(url)
        if p.scheme in ("data", "blob"):
            route.continue_()
            return
        host = (p.hostname or "").lower()
        try:
            if self.disk:
                if p.scheme == "https" and host == self.host:
                    self._serve_disk(route)
                else:
                    route.abort()
                return
            if p.scheme not in ("http", "https") or not host:
                route.abort()
                return
            if p.scheme == "http" and self.origin.startswith("https"):
                self.mixed.append(url[:160])
            own = self.own(host)
            if not own and not is_public(host):
                self.notes.append(f"band: {host} (public internet par nahi)")
                route.abort()
                return
            if own and not is_public(host) and NET_FULFILL is None:
                route.abort()
                return
            nav = req.is_navigation_request()
            if nav and not own and req.frame.parent_frame is None:
                self.notes.append(f"site se bahar jaane ki koshish rok di: {host}")
                route.abort()
                return
            if R.pay_host(host) and (nav or req.resource_type not in ("script", "stylesheet", "image", "font")):
                self.notes.append(f"payment gateway ko request nahi: {host}")
                route.abort()
                return
            if req.method not in ("GET", "HEAD", "OPTIONS"):
                if not own or not self.allow_writes:
                    self.notes.append(f"{req.method} {p.path} roka (live site par form submit band hai)")
                    route.abort()
                    return
            if NET_FULFILL is not None and NET_FULFILL(route):
                return
            route.continue_()
        except Exception as e:                       # a route must always be answered
            log.debug("qa route %s: %s", url, e)
            try:
                route.abort()
            except Exception:
                pass


# ---------------------------------------------------------------- Hoola's own audit scripts
A11Y_JS = r"""() => {
  const out = [], warn = [];
  const name = el => (el.getAttribute('aria-label') || el.getAttribute('title') || el.innerText || el.value || el.getAttribute('alt') || '').trim();
  const vis = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  if (!document.title.trim()) out.push({rule: '2.4.2', text: 'Page ka title nahi hai'});
  if (!(document.documentElement.getAttribute('lang') || '').trim()) out.push({rule: '3.1.1', text: 'html lang nahi diya'});
  document.querySelectorAll('img').forEach(i => { if (vis(i) && !i.hasAttribute('alt')) out.push({rule: '1.1.1', text: 'Photo bina alt text: ' + (i.getAttribute('src') || '').slice(-40)}); });
  document.querySelectorAll('input,select,textarea').forEach(i => {
    if (['hidden', 'submit', 'button', 'reset', 'image'].includes(i.type) || !vis(i)) return;
    const lab = (i.id && document.querySelector('label[for="' + CSS.escape(i.id) + '"]')) || i.closest('label');
    if (!lab && !i.getAttribute('aria-label') && !i.getAttribute('aria-labelledby') && !i.getAttribute('title'))
      out.push({rule: '1.3.1', text: 'Form ka khana bina label: ' + (i.name || i.type)});
  });
  document.querySelectorAll('button,a[href],[role=button]').forEach(b => { if (vis(b) && !name(b) && !b.querySelector('img[alt]:not([alt=""]),svg title')) out.push({rule: '4.1.2', text: 'Button / link ka naam nahi (icon only?)'}); });
  const h1 = [...document.querySelectorAll('h1')].filter(vis).length;
  if (h1 === 0) warn.push({rule: '1.3.1', text: 'Page par h1 heading nahi'});
  if (h1 > 1) warn.push({rule: '1.3.1', text: h1 + ' h1 headings (ek rakhiye)'});
  const ids = {}; document.querySelectorAll('[id]').forEach(e => { ids[e.id] = (ids[e.id] || 0) + 1; });
  const dup = Object.keys(ids).filter(k => ids[k] > 1); if (dup.length) warn.push({rule: '4.1.1', text: 'Ek jaise id: ' + dup.slice(0, 3).join(', ')});
  let small = 0; document.querySelectorAll('a[href],button,input,select,[role=button]').forEach(e => {
    if (!vis(e) || e.disabled) return; const lb = ['checkbox', 'radio'].includes(e.type) && e.closest('label'); const r = (lb || e).getBoundingClientRect(); const inline = getComputedStyle(e).display === 'inline' && e.tagName === 'A' && e.closest('p,li');
    if (!inline && (r.width < 24 || r.height < 24)) small++; });
  if (small) out.push({rule: '2.5.8', text: small + ' tap targets 24x24 px se chhote'});
  const rgba = c => { const m = (c || '').match(/[\d.]+/g); if (!m || m.length < 3) return null; return {r: +m[0], g: +m[1], b: +m[2], a: m.length > 3 ? +m[3] : 1}; };
  const L = o => { const v = [o.r, o.g, o.b].map(x => { x /= 255; return x <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); }); return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.backgroundImage && cs.backgroundImage !== 'none') return null; const c = rgba(cs.backgroundColor); if (c && c.a > .9) return c; } return {r: 255, g: 255, b: 255, a: 1}; };
  let bad = 0;
  [...document.querySelectorAll('h1,h2,h3,p,li,a,span,button,label,td')].slice(0, 500).forEach(el => {
    if (bad >= 5 || !vis(el) || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
    if (el.disabled || el.closest('[disabled],[aria-disabled=true]')) return;
    const cs = getComputedStyle(el); if (+cs.opacity < .5) return;
    const f = rgba(cs.color), bg = bgOf(el); if (!f || !bg) return;
    const fg = {r: f.r * f.a + bg.r * (1 - f.a), g: f.g * f.a + bg.g * (1 - f.a), b: f.b * f.a + bg.b * (1 - f.a)};
    const a = L(fg), b = L(bg), ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    const large = parseFloat(cs.fontSize) >= 24 || (parseFloat(cs.fontSize) >= 18.6 && +cs.fontWeight >= 700);
    if (ratio < (large ? 3 : 4.5)) { bad++; out.push({rule: '1.4.3', text: 'Kam contrast (' + ratio.toFixed(1) + ':1): ' + el.textContent.trim().slice(0, 40)}); }
  });
  return {issues: out, warnings: warn};
}"""

OVERFLOW_JS = r"""() => { const vw = innerWidth, sw = document.scrollingElement.scrollWidth;
  if (sw <= vw + 1) return {issues: []};
  const wide = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > vw + 2; })
    .slice(0, 3).map(e => e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.split(' ')[0] : ''));
  return {issues: [{rule: '1.4.10', text: vw + ' px par page side mein khisakta hai (' + sw + ' px): ' + wide.join(', ')}]}; }"""

IMAGES_JS = r"""() => ({issues: [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src'))
  .slice(0, 5).map(i => ({rule: 'img', text: 'Photo nahi khuli: ' + i.getAttribute('src').slice(-60)}))})"""

LINKS_JS = r"""() => [...document.querySelectorAll('a[href]')].map(a => a.href).filter(h => /^https?:/.test(h))"""

MAP_JS = r"""() => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const lab = i => { const l = (i.id && document.querySelector('label[for="' + CSS.escape(i.id) + '"]')) || i.closest('label');
    return ((l && l.innerText) || i.getAttribute('aria-label') || i.placeholder || i.name || '').trim().slice(0, 60); };
  const forms = [...document.querySelectorAll('form')].slice(0, 4).map(f => ({
    fields: [...f.querySelectorAll('input,textarea,select')].filter(i => !['hidden', 'submit', 'button'].includes(i.type) && !i.classList.contains('hp'))
      .slice(0, 10).map(i => ({label: lab(i), name: i.name || '', id: i.id || '', type: (i.type || 'text').toLowerCase(), required: i.required,
        min: i.min || '', max: i.max || '', minlength: i.minLength > 0 ? i.minLength : '', maxlength: i.maxLength > 0 ? i.maxLength : '',
        pattern: i.getAttribute('pattern') || '', autocomplete: i.autocomplete || '', placeholder: i.placeholder || ''})),
    submit: ((f.querySelector('button[type=submit],input[type=submit],button:not([type])') || {}).innerText || (f.querySelector('input[type=submit]') || {}).value || '').trim().slice(0, 40)
  }));
  const screens = [...document.querySelectorAll('.scr[data-screen]')].map(s => ({id: s.getAttribute('data-screen'),
    label: ((s.querySelector('h1,h2,.title') || {}).innerText || '').trim().slice(0, 50), tabbed: s.hasAttribute('data-tabbed'),
    goes: [...new Set([...s.querySelectorAll('[data-go]:not([disabled])')].map(e => e.getAttribute('data-go')))].slice(0, 12),
    consent: !!(s.querySelector('input[type=checkbox]') && s.querySelector('button[disabled]'))}));
  return {title: document.title, h1: ((document.querySelector('h1') || {}).innerText || '').trim().slice(0, 80),
    links: [...document.querySelectorAll('a[href]')].map(a => a.href).filter(h => /^https?:/.test(h)).slice(0, 200),
    tel: [...document.querySelectorAll('a[href^="tel:"]')].length, wa: [...document.querySelectorAll('a[href*="wa.me"],a[href*="api.whatsapp.com"]')].length,
    password: !!document.querySelector('input[type=password]'), forms, screens,
    nav: [...document.querySelectorAll('nav a[href], header a[href]')].filter(vis).slice(0, 12).map(a => ({text: a.innerText.trim().slice(0, 40), href: a.getAttribute('href')}))};
}"""

FIELD_JS = r"""e => { const l = (e.id && document.querySelector('label[for="' + CSS.escape(e.id) + '"]')) || e.closest('label');
  return {type: (e.type || '').toLowerCase(), name: e.name || '', id: e.id || '', ac: e.autocomplete || '', ph: e.placeholder || '',
          aria: e.getAttribute('aria-label') || '', label: (l && l.innerText) || ''}; }"""

CLICK_JS = r"""e => ({text: (e.innerText || e.value || e.getAttribute('aria-label') || e.getAttribute('title') || '').trim().slice(0, 120),
  href: e.getAttribute('href') || (e.closest('a') ? e.closest('a').getAttribute('href') : '') || ''})"""


# ---------------------------------------------------------------- execution
def _launch(p):
    import os
    kw: dict[str, Any] = {"args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]}
    if os.environ.get("HOOLA_CHROMIUM"):
        kw["executable_path"] = os.environ["HOOLA_CHROMIUM"]
    return p.chromium.launch(**kw)


def _rand(kind: str) -> str:
    n = "".join(random.choices(string.digits, k=5))
    return {"email": f"qa.test{n}@example.com", "phone": "98" + "".join(random.choices(string.digits, k=8)),
            "name": f"QA Test {n}", "text": f"Hoola QA test {n}"}[kind]


class _Case:
    def __init__(self, src: Source, page, ctx, case: dict[str, Any], account: dict[str, str] | None, shots: Path | None):
        self.src, self.page, self.ctx, self.case, self.account, self.shots = src, page, ctx, case, account, shots
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.shot = ""
        self.shot_n = 0

    def value(self, v: str) -> str:
        def rep(m):
            k = m.group(1)
            if k.startswith("account."):
                if not self.account:
                    raise Blocked("Test account nahi juda: app mein QA > target > Test account bharo (asli password nahi).")
                return self.account.get(k.split(".", 1)[1], "")
            return _rand(k.split(".", 1)[1])
        return re.sub(r"\{(account\.(?:username|password)|rand\.(?:email|phone|name|text))\}", rep, v)

    def loc(self, t: dict[str, Any], visible: bool = True):
        page, ex = self.page, bool(t.get("exact"))
        if "css" in t:
            lo = page.locator(t["css"])
        elif "role" in t:
            lo = page.get_by_role(t["role"], name=t["name"], exact=ex) if t.get("name") else page.get_by_role(t["role"])
        elif "label" in t:
            lo = page.get_by_label(t["label"], exact=ex)
        elif "placeholder" in t:
            lo = page.get_by_placeholder(t["placeholder"], exact=ex)
        elif "testid" in t:
            lo = page.get_by_test_id(t["testid"])
        elif "alt" in t:
            lo = page.get_by_alt_text(t["alt"], exact=ex)
        else:
            lo = page.get_by_text(t["text"], exact=ex)
        return (lo.filter(visible=True) if visible else lo).first

    def found(self, t: dict[str, Any], visible: bool = True):
        lo = self.loc(t, visible)
        try:
            lo.wait_for(state="visible" if visible else "attached", timeout=STEP_TIMEOUT_MS)
        except Exception:
            raise StepFail(f"Nahi mila: {describe({'do': 'click', 'target': t})[7:]}", "element dikhna chahiye", "page par nahi mila")
        return lo

    def snap(self, name: str) -> str:
        if not self.shots:
            return ""
        self.shot_n += 1
        fn = f"{self.case['id']}-{self.shot_n}-{re.sub(r'[^\w-]', '_', name)[:30]}.jpg"
        try:
            self.page.screenshot(path=str(self.shots / fn), type="jpeg", quality=60)
            return fn
        except Exception:
            return ""

    def audit(self, kind: str) -> None:
        page = self.page
        issues: list[dict[str, str]] = []
        if kind == "a11y":
            r = page.evaluate(A11Y_JS)
            issues = r["issues"]
            self.warnings += [f"[{w['rule']}] {w['text']}" for w in r["warnings"]]
        elif kind == "overflow":
            issues = page.evaluate(OVERFLOW_JS)["issues"]
        elif kind == "images":
            issues = page.evaluate(IMAGES_JS)["issues"]
        elif kind == "console":
            errs = [e for e in self.errors if "favicon" not in e.lower()]
            issues = [{"rule": "console", "text": e} for e in errs[:5]]
        elif kind == "headers":
            if self.src.disk:
                self.warnings.append("Preview mein headers asli nahi hote: live address par jaanchiye.")
                return
            h = {k.lower(): v for k, v in self.src.doc_headers.items()}
            if "strict-transport-security" not in h:
                issues.append({"rule": "hsts", "text": "Strict-Transport-Security header nahi"})
            if "x-content-type-options" not in h:
                issues.append({"rule": "nosniff", "text": "X-Content-Type-Options: nosniff nahi"})
            csp = h.get("content-security-policy", "")
            if not csp:
                self.warnings.append("Content-Security-Policy header nahi")
            if "x-frame-options" not in h and "frame-ancestors" not in csp:
                issues.append({"rule": "frame", "text": "Clickjacking se bachav nahi (X-Frame-Options / frame-ancestors)"})
            for c in self.ctx.cookies():
                if not c.get("secure"):
                    issues.append({"rule": "cookie", "text": f"Cookie '{c['name']}' bina Secure"})
            if self.src.mixed:
                issues.append({"rule": "mixed", "text": f"HTTPS page par http:// cheezein: {self.src.mixed[0]}"})
        elif kind == "links":
            hrefs = list(dict.fromkeys(h.split("#")[0] for h in page.evaluate(LINKS_JS)))
            own = [h for h in hrefs if self.src.own(urlparse(h).hostname or "")][:20]
            p2 = self.ctx.new_page()
            try:
                for h in own:
                    try:
                        resp = p2.goto(h, wait_until="commit", timeout=15000)
                        st = resp.status if resp else 0
                    except Exception:
                        st = 0
                    if not st or st >= 400:
                        issues.append({"rule": "link", "text": f"Toota link ({st or 'nahi khula'}): {urlparse(h).path or '/'}"})
            finally:
                p2.close()
        if issues:
            msg = "; ".join(f"[{i['rule']}] {i['text']}" for i in issues[:4])
            more = f" (+{len(issues) - 4} aur)" if len(issues) > 4 else ""
            raise StepFail(f"Jaanch '{kind}' fail: {msg}{more}", f"{kind} mein koi dikkat nahi", msg)

    def step(self, s: dict[str, Any]) -> None:
        op, page = s["do"], self.page
        if op == "goto":
            resp = page.goto(self.src.url(s["path"]), wait_until="load", timeout=NAV_TIMEOUT_MS)
            if resp is not None:
                self.src.doc_headers = dict(resp.headers)
                if resp.status >= 400:
                    raise StepFail(f"Page {resp.status} de raha hai: {s['path']}", "page khule (200)", f"HTTP {resp.status}")
            elif not page.url.startswith(self.src.origin):
                raise StepFail(f"Page nahi khula: {s['path']}", "page khule", "kuch nahi aaya")
            return
        if op == "back":
            page.go_back(wait_until="load", timeout=NAV_TIMEOUT_MS)
            return
        if op == "viewport":
            page.set_viewport_size({"width": s["width"], "height": 800 if s["width"] >= 768 else 760})
            page.wait_for_timeout(150)
            return
        if op == "wait":
            page.wait_for_timeout(s["ms"])
            return
        if op == "screenshot":
            self.shot = self.snap(s["name"]) or self.shot
            return
        if op == "press":
            page.keyboard.press(s["key"])
            return
        if op == "audit":
            self.audit(s["kind"])
            return
        if op in ("expect_text", "expect_no_text"):
            lo = page.get_by_text(s["text"], exact=False).filter(visible=True).first
            try:
                lo.wait_for(state="visible", timeout=STEP_TIMEOUT_MS if op == "expect_text" else 1200)
                seen = True
            except Exception:
                seen = False
            body = ""
            try:
                body = re.sub(r"\s+", " ", page.inner_text("body"))[:220]
            except Exception:
                pass
            if op == "expect_text" and not seen:
                raise StepFail(f"\"{s['text']}\" nahi dikha", f"\"{s['text']}\" dikhe", body or "page khaali")
            if op == "expect_no_text" and seen:
                raise StepFail(f"\"{s['text']}\" dikh raha hai jo nahi dikhna chahiye", f"\"{s['text']}\" na dikhe", "dikh raha hai")
            return
        if op == "expect_url":
            deadline = time.time() + STEP_TIMEOUT_MS / 1000
            while s["contains"] not in page.url and time.time() < deadline:
                page.wait_for_timeout(200)
            if s["contains"] not in page.url:
                raise StepFail("Galat page", f"address mein '{s['contains']}'", urlparse(page.url).path or "/")
            return
        if op == "expect_title":
            t = page.title()
            if s["contains"].lower() not in t.lower() or (not s["contains"] and not t.strip()):
                raise StepFail("Page title galat", f"title mein '{s['contains']}'" if s["contains"] else "title ho", t or "(khaali)")
            return
        t = s["target"]
        if op == "expect_hidden":
            lo = self.loc(t, visible=False)
            try:
                lo.wait_for(state="hidden", timeout=STEP_TIMEOUT_MS)
            except Exception:
                raise StepFail("Cheez chhupi honi chahiye thi", "chhupa ho", "dikh raha hai")
            return
        lo = self.found(t)
        if op == "expect_visible":
            return
        if op in ("expect_enabled", "expect_disabled"):
            en = lo.is_enabled()
            if (op == "expect_enabled") != en:
                raise StepFail("Button / khana galat haal mein", "chalu ho" if op == "expect_enabled" else "band ho",
                               "chalu hai" if en else "band hai")
            return
        if op in ("expect_invalid", "expect_valid"):
            bad = lo.evaluate("e => (e.checkValidity ? !e.checkValidity() : false) || e.getAttribute('aria-invalid') === 'true'")
            if (op == "expect_invalid") != bad:
                raise StepFail("Galat input ko sahi maan liya" if op == "expect_invalid" else "Sahi input ko galat maana",
                               "galat maana jaaye" if op == "expect_invalid" else "sahi maana jaaye", "sahi maana" if not bad else "galat maana")
            return
        if op == "click":
            info = lo.evaluate(CLICK_JS)
            from ..operator.guard import DANGER_LINK, PAYMENT
            if PAYMENT.search(info["text"]) or R.pay_host(urlparse(urljoin(page.url, info["href"] or "")).hostname or ""):
                raise Blocked(f"Payment wala button nahi dabaya: '{info['text'][:40]}' (paise kabhi nahi)")
            if not self.src.disk and not self.src.allow_writes and DANGER_LINK.search(info["text"]):
                raise Blocked(f"Live site par '{info['text'][:40]}' nahi dabaya (delete / cancel / confirm)")
            lo.click(timeout=STEP_TIMEOUT_MS)
            page.wait_for_timeout(250)
            return
        if op in ("fill", "select"):
            meta = lo.evaluate(FIELD_JS)
            words = " ".join(str(meta.get(k) or "") for k in ("name", "id", "ac", "ph", "aria", "label"))
            if meta.get("ac", "").startswith("cc-") or R.SECRET_WORDS.search(words) or "one-time-code" in meta.get("ac", ""):
                raise Blocked("Card / CVV / OTP / UPI PIN ka khana Hoola kabhi nahi bharta.")
            raw = s["value"]
            if meta.get("type") == "password" and raw != "{account.password}":
                raise Blocked("Password khane mein sirf test account ka password jaata hai ({account.password}).")
            if "{account.password}" in raw and meta.get("type") != "password":
                raise Blocked("Test password sirf password wale khane mein.")
            val = self.value(raw)
            if op == "fill":
                lo.fill(val, timeout=STEP_TIMEOUT_MS)
            else:
                try:
                    lo.select_option(label=val, timeout=STEP_TIMEOUT_MS)
                except Exception:
                    lo.select_option(val, timeout=STEP_TIMEOUT_MS)
            return
        if op in ("check", "uncheck"):
            (lo.check if op == "check" else lo.uncheck)(timeout=STEP_TIMEOUT_MS)
            return
        if op == "hover":
            lo.hover(timeout=STEP_TIMEOUT_MS)
            return
        raise StepFail(f"Step '{op}' samajh nahi aaya")


def _context(browser, src: Source, width: int):
    ctx = browser.new_context(viewport={"width": width, "height": 800 if width >= 768 else 760}, service_workers="block",
                              accept_downloads=False, locale="en-IN", timezone_id="Asia/Kolkata")
    ctx.route("**/*", src.handler)
    return ctx


def run_cases(src: Source, cases: list[dict[str, Any]], accounts: dict[str, dict[str, str]] | None = None,
              shots: Path | None = None, stop: Callable[[], bool] | None = None,
              on_result: Callable[[dict[str, Any]], None] | None = None) -> list[dict[str, Any]]:
    """cases: [{id, number, title, steps, viewport, account, type, priority}] -> results in the same order."""
    why = available()
    if why:
        raise RuntimeError(why)
    from playwright.sync_api import sync_playwright
    out: list[dict[str, Any]] = []
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = _launch(p)
        try:
            for c in cases:
                if stop and stop():
                    break
                res = run_one(browser, src, c, (accounts or {}).get(c.get("account") or "test"), shots)
                out.append(res)
                if on_result:
                    on_result(res)
        finally:
            browser.close()
    return out


def run_one(browser, src: Source, c: dict[str, Any], account: dict[str, str] | None, shots: Path | None) -> dict[str, Any]:
    t0 = time.time()
    res: dict[str, Any] = {"case_id": c["id"], "number": c.get("number", ""), "status": "pass", "step": -1, "message": "",
                           "expected": "", "actual": "", "console": [], "shot": "", "url": "", "warnings": [], "notes": []}
    steps = list(c.get("steps") or [])
    if not steps:
        res.update(status="manual", message="Haath se jaanchna hai (steps chalane layak nahi)")
        return res
    inserted = 0
    if steps[0]["do"] != "goto":
        steps.insert(0, {"do": "goto", "path": src.start})
        inserted = 1
    src.notes, src.mixed = [], []
    ctx = _context(browser, src, int(c.get("viewport") or 1280))
    page = ctx.new_page()
    page.set_default_timeout(STEP_TIMEOUT_MS)
    run = _Case(src, page, ctx, c, account, shots)
    page.on("pageerror", lambda e: run.errors.append(str(e)[:200]))
    page.on("console", lambda m: run.errors.append(m.text[:200]) if m.type == "error" else None)
    try:
        for i, s in enumerate(steps):
            if time.time() - t0 > CASE_LIMIT_S:
                raise StepFail("Case bahut der tak chala (90 sec)", "jaldi poora ho", "time khatam")
            res["step"] = i
            run.step(s)
        res["step"] = -1
    except StepFail as e:
        res.update(status="fail", message=str(e), expected=e.expected, actual=e.actual)
    except Blocked as e:
        res.update(status="blocked", message=str(e))
    except Exception as e:                      # Playwright error, timeout...
        msg = str(e).split("\n")[0][:200]
        res.update(status="fail", message=f"Step nahi chala: {msg}", expected=describe(steps[res['step']]) if res["step"] >= 0 else "",
                   actual=msg)
    try:
        res["url"] = page.url if page.url.startswith(src.origin) else ""
        if res["status"] == "fail":
            res["shot"] = run.snap("fail")
        else:
            res["shot"] = run.shot
    except Exception:
        pass
    res["console"] = [e for e in run.errors if "favicon" not in e.lower()][:8]
    res["warnings"] = run.warnings[:10]
    res["notes"] = list(dict.fromkeys(src.notes))[:8]
    if res["step"] >= 0:
        res["step_text"] = describe(steps[res["step"]])
        res["step"] = res["step"] - inserted
    res["ms"] = int((time.time() - t0) * 1000)
    try:
        ctx.close()
    except Exception:
        pass
    return res


def discover(src: Source, max_pages: int = 12) -> dict[str, Any]:
    """Open her site / app and note what is there: pages (title, h1, forms with their fields, nav), screens of an app."""
    why = available()
    if why:
        raise RuntimeError(why)
    from playwright.sync_api import sync_playwright
    pages: list[dict[str, Any]] = []
    seen: set[str] = set()
    todo = [src.url(src.start)]
    out: dict[str, Any] = {"pages": pages, "screens": [], "notes": []}
    with sync_playwright() as p:
        browser = _launch(p)
        try:
            ctx = _context(browser, src, 1280)
            page = ctx.new_page()
            while todo and len(pages) < max_pages:
                u = todo.pop(0)
                key = u.split("#")[0].split("?")[0] if src.kind != "app" else u
                if key in seen:
                    continue
                seen.add(key)
                try:
                    resp = page.goto(u, wait_until="load", timeout=NAV_TIMEOUT_MS)
                except Exception as e:
                    out["notes"].append(f"{urlparse(u).path}: nahi khula ({str(e).splitlines()[0][:80]})")
                    continue
                if resp is not None and resp.status >= 400:
                    out["notes"].append(f"{urlparse(u).path}: HTTP {resp.status}")
                    continue
                m = page.evaluate(MAP_JS)
                path = urlparse(page.url).path or "/"
                pages.append({"path": path, "title": m["title"][:120], "h1": m["h1"], "forms": m["forms"], "tel": m["tel"],
                              "wa": m["wa"], "password": m["password"], "nav": m["nav"]})
                if m["screens"]:
                    out["screens"] = m["screens"]
                    break
                for h in m["links"]:
                    hp = urlparse(h)
                    if src.own(hp.hostname or "") and not re.search(r"\.(pdf|jpe?g|png|webp|zip|docx?|xlsx?)$", hp.path, re.I):
                        nk = h.split("#")[0].split("?")[0]
                        if nk not in seen and nk not in todo:
                            todo.append(nk)
            ctx.close()
        finally:
            browser.close()
    out["notes"] += list(dict.fromkeys(src.notes))[:6]
    return out
