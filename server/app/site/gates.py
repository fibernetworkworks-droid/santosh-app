"""v0.551 SURAKSHA GATES for websites (web Step 7 part 1 = W11 of docs/WEB_PLATFORM_PLAN.md: "every build: dependency
and secret scan, CSP + security headers check, OWASP checks on forms and APIs, rate limits, bot protection on forms,
accessibility WCAG 2.2 AA gate, legal pages per profession, cookie banner only when a tracker is really present. A failing
gate blocks going live.").

`scan(out, site)` reads the BUILT site (every page on disk, not a sample) and returns rows in the same shape as the native
apps' gates (`appmaker/gates.py`): {gate, check, state pass | warn | fail | not_checked, say, read}. A FAIL joins the
version's blocking list, so `hosting.blockers()` refuses the launch card until it is fixed; a WARN is shown, never blocks;
NOT CHECKED (OSV.dev unreachable) is said as not checked, never counted as a pass.

  1 secrets       - the same key patterns the app gate uses, over every text file the visitor can download.
  2 libraries     - outside JavaScript libraries shipped in the site (three.js, MapLibre, Lottie, Chart.js, PDF.js...)
                    found by their own version banners, asked of OSV.dev; HIGH / CRITICAL fails. None = said so.
  3 headers       - the security headers the site is served with (the `_headers` file = what Hoola's server and nginx
                    send): a CSP with no unsafe-inline / unsafe-eval scripts, object-src none, frame-ancestors, base-uri,
                    form-action, nosniff, referrer and permissions policies.
  4 pages         - OWASP on every page: no inline script (JSON-LD aside), no on*= handlers, no javascript: links, no
                    outside <script src> except Cloudflare Turnstile when it is on, no http:// resource (mixed content),
                    no iframe to an unknown host; a new-tab link without rel=noopener is a warning.
  5 forms         - every enquiry form posts only to HER Hoola form address (POST), carries the hidden honeypot field,
                    no password box on a public page (logins live in the app pages), and a privacy page exists.
  6 bots          - Cloudflare Turnstile on the forms when the server has its keys, else a warning that names what does
                    protect them today (honeypot + 5 an address per 10 minutes + 200 a day).
  7 accessibility - WCAG 2.2 AA checks a file can prove on EVERY page (html lang, page title, image alt, labelled
                    controls, named links and buttons, zoom not disabled) + the browser's axe result for the pages it opened.
  8 legal         - per profession (taxonomy `legal`): FSSAI number on a food site, registration number for doctors,
                    seller details + refund / terms pages for a shop; Drugs and Magic Remedies Act cure claims and Bar
                    Council solicitation words FAIL; 'guaranteed result / 100% placement' on a coaching site warns.
  9 trackers      - a tracker (Google Analytics / Tag Manager, Meta Pixel, Hotjar, Clarity, DoubleClick...) found in a
                    page needs a consent banner; none found = no banner needed (Hoola counts visits on the server).
 10 rate limits   - the server-side limits the site's forms, shop and logins run behind, stated (they are code, not
                    a per-site setting).
 11 AI look       - v0.606 SAAF NAZAR (site/look.py, ideas from pbakaus/impeccable): the reflex tells that make a site
                    read as AI-made (overused fonts, violet gradients, a label above every heading, icon tiles, gradient
                    text, glow halos, bounce easing, buzzwords...). WARN only - it never blocks; her own choices win."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STATS = {"scans": 0, "fails": 0}
TEXT_EXT = {".html", ".js", ".css", ".json", ".xml", ".txt", ".webmanifest"}
MAX_FILES = 30_000
FRAME_OK = ("www.google.com", "maps.google.com", "www.youtube-nocookie.com", "challenges.cloudflare.com")
SCRIPT_OK = ("challenges.cloudflare.com",)
TURNSTILE_JS = "https://challenges.cloudflare.com/turnstile/v0/api.js"

LIBS = [                                                   # (npm name, banner regex giving the version)
    ("three", re.compile(r"three\.js r(\d+)|REVISION\s*=\s*['\"](\d+)['\"]")),
    ("maplibre-gl", re.compile(r"maplibre-gl[^\n]{0,40}?v?(\d+\.\d+\.\d+)")),
    ("lottie-web", re.compile(r"lottie[^\n]{0,30}?v?(\d+\.\d+\.\d+)")),
    ("chart.js", re.compile(r"Chart\.js v(\d+\.\d+\.\d+)")),
    ("pdfjs-dist", re.compile(r"pdfjsVersion\s*=\s*['\"](\d+\.\d+\.\d+)['\"]")),
    ("gsap", re.compile(r"GSAP (\d+\.\d+\.\d+)")),
    ("swiper", re.compile(r"Swiper (\d+\.\d+\.\d+)")),
    ("jquery", re.compile(r"jQuery v(\d+\.\d+\.\d+)")),
]
TRACKERS = [
    ("Google Analytics / Tag Manager", re.compile(r"googletagmanager\.com|google-analytics\.com|\bgtag\(", re.I)),
    ("Meta Pixel", re.compile(r"connect\.facebook\.net|\bfbq\(", re.I)),
    ("Hotjar", re.compile(r"static\.hotjar\.com|\bhj\(", re.I)),
    ("Microsoft Clarity", re.compile(r"clarity\.ms", re.I)),
    ("DoubleClick / Google Ads", re.compile(r"doubleclick\.net|googleadservices\.com", re.I)),
    ("LinkedIn Insight", re.compile(r"snap\.licdn\.com", re.I)),
]
# Drugs and Magic Remedies (Objectionable Advertisements) Act, 1954 - advertising a cure for the Schedule's diseases
DMR = (re.compile(r"\b(?:100\s*%|guaranteed|permanent|complete|sure[- ]?shot)\s+(?:cure|treatment|relief)\b", re.I),
       re.compile(r"\b(?:cures?|ilaaj|ilaj)\s+(?:for\s+|of\s+|from\s+)?(?:diabetes|cancer|obesity|asthma|arthritis|paralysis|"
                  r"epilepsy|infertility|impotence|blood pressure|hypertension|kidney stones?|piles|baldness|leprosy|"
                  r"tuberculosis)\b", re.I))
# Bar Council of India Rules, Part VI Ch. II r.36 - an advocate may not solicit or advertise
BCI = re.compile(r"\b(?:best|top|no\.?\s*1|number one|leading)\s+(?:lawyers?|advocates?|law firm)\b|"
                 r"\bguaranteed?\s+(?:win|success|bail|result)\b|\b100\s*%\s+(?:success|win)\b", re.I)
EDU = re.compile(r"\b(?:100\s*%|guaranteed)\s+(?:placement|selection|result|admission)s?\b", re.I)
FSSAI = re.compile(r"\bfssai\b[^\d]{0,30}\d{14}\b", re.I)
REGNO = re.compile(r"\b(?:reg(?:istration)?\.?\s*(?:no|number)|mci|nmc|smc)\b[^\n]{0,20}\d{3,}", re.I)

SCRIPT_TAG = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.I | re.S)
ON_ATTR = re.compile(r"<[a-z][^>]*\s(on[a-z]+)\s*=", re.I)
JS_URL = re.compile(r"""(?:href|src|action)\s*=\s*["']\s*javascript:""", re.I)
HTTP_RES = re.compile(r"""<(?:img|script|link|iframe|source|video|audio)\b[^>]*\s(?:src|href)\s*=\s*["']http://""", re.I)
IFRAME = re.compile(r"""<iframe\b[^>]*\ssrc\s*=\s*["']([^"']+)""", re.I)
BLANK_A = re.compile(r"""<a\b[^>]*target\s*=\s*["']_blank["'][^>]*>""", re.I)
FORM = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.I | re.S)


def _row(gate: str, check: str, state: str, say: str, read: str = "", sections: list[str] | None = None) -> dict[str, Any]:
    row = {"gate": gate, "check": check, "state": state, "say": say, "read": read[:300]}
    if sections:
        row["sections"] = sorted(set(sections))[:12]          # the build's fix round rewrites exactly these
    return row


SEC_START = re.compile(r"""<section\b[^>]*\bid\s*=\s*["'](s-[\w-]+)["']""", re.I)


def _sec_at(html: str, pos: int) -> str:
    """The section (her designed block, id s-<page>-<type>) a problem sits in, so a fix round can rewrite it."""
    sid = ""
    for m in SEC_START.finditer(html, 0, pos):
        sid = m.group(1)
    return sid


def _files(out: Path) -> list[Path]:
    got = []
    for p in out.rglob("*"):
        if p.is_file() and p.suffix in TEXT_EXT and not p.name.endswith(".gz"):
            got.append(p)
            if len(got) >= MAX_FILES:
                break
    return got


def _pages(out: Path) -> list[Path]:
    return [p for p in _files(out) if p.suffix == ".html"]


def _rel(out: Path, p: Path) -> str:
    return p.relative_to(out).as_posix()


# ---------------------------------------------------------------- 1. secrets
def gate_secrets(out: Path) -> list[dict[str, Any]]:
    from ..appmaker import gates as AG
    bad = []
    for p in _files(out):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for why, bit in AG._hits(txt):
            bad.append(f"{_rel(out, p)}: {why} ({bit})")
    if bad:
        return [_row("secrets", "No key or password in the site's files", "fail",
                     f"Website ki {len(bad)} jagah par ek chaabi / key dikh rahi hai - koi bhi visitor use download kar sakta "
                     "hai. Wahan se hataiye aur woh key badal dijiye (rotate).", "; ".join(bad[:5]))]
    return [_row("secrets", "No key or password in the site's files", "pass", "Kisi file mein koi key / password nahi mila.")]


# ---------------------------------------------------------------- 2. outside libraries
def found_libraries(out: Path) -> list[dict[str, str]]:
    deps: dict[str, str] = {}
    for p in _files(out):
        if p.suffix != ".js" or p.name.startswith("hoola-") or p.name in ("site.js",):
            continue
        try:
            head = p.read_text(encoding="utf-8", errors="ignore")[:4000]
        except OSError:
            continue
        for name, rx in LIBS:
            m = rx.search(head)
            if m:
                ver = next(g for g in m.groups() if g)
                if name == "three":
                    ver = f"0.{ver}.0"                     # three r149 = npm 0.149.0
                deps[name] = ver
    return [{"ecosystem": "npm", "name": k, "version": v} for k, v in sorted(deps.items())]


def gate_libraries(out: Path) -> list[dict[str, Any]]:
    from ..appmaker import gates as AG
    deps = found_libraries(out)
    if not deps:
        return [_row("libraries", "No outside library with a known hole", "pass",
                     "Website mein sirf Hoola ki apni scripts hain - koi bahar ki library nahi, jiska purana hole ho.")]
    res = AG._osv(deps)
    if res is None:
        return [_row("libraries", "No outside library with a known hole", "not_checked",
                     "OSV.dev (Google ka vulnerability database) abhi khula nahi - yeh jaanch HUI NAHI, pass nahi maana.",
                     ", ".join(f"{d['name']} {d['version']}" for d in deps))]
    bad, mild = [], []
    for d, vulns in zip(deps, res + [[]] * len(deps)):
        for v in vulns:
            sev = AG._worst(v)
            (bad if sev in ("HIGH", "CRITICAL") else mild).append(f"{d['name']} {d['version']}: {v.get('id', '?')} ({sev})")
    if bad:
        return [_row("libraries", "No outside library with a known hole", "fail",
                     f"{len(bad)} bahar ki library mein gambhir (HIGH / CRITICAL) hole hai - nayi version chahiye.",
                     "; ".join(bad[:6]))]
    if mild:
        return [_row("libraries", "No outside library with a known hole", "warn",
                     "Chhote holes mile (HIGH / CRITICAL nahi) - agli version mein library badal dena accha.", "; ".join(mild[:6]))]
    return [_row("libraries", "No outside library with a known hole", "pass",
                 f"{len(deps)} bahar ki libraries, kisi mein jaana-pehchana hole nahi.",
                 ", ".join(f"{d['name']} {d['version']}" for d in deps))]


# ---------------------------------------------------------------- 3. headers
def _headers(out: Path) -> dict[str, str]:
    f = out / "_headers"
    got: dict[str, str] = {}
    if not f.exists():
        return got
    for line in f.read_text(encoding="utf-8").splitlines():
        if ":" in line and line.startswith(" "):
            k, v = line.strip().split(":", 1)
            got[k.strip().lower()] = v.strip()
    return got


def gate_headers(out: Path) -> list[dict[str, Any]]:
    h = _headers(out)
    if not h:
        return [_row("headers", "Security headers", "fail", "Website ke saath security headers ki file (_headers) nahi bani.")]
    csp = h.get("content-security-policy", "")
    parts = {d.strip().split(" ")[0]: d.strip() for d in csp.split(";") if d.strip()}
    miss = []
    script = parts.get("script-src") or parts.get("default-src", "")
    if not script:
        miss.append("script-src")
    if "'unsafe-inline'" in script or "'unsafe-eval'" in script:
        miss.append("script-src without unsafe-inline / unsafe-eval")
    for need, want in (("object-src", "'none'"), ("frame-ancestors", ""), ("base-uri", ""), ("form-action", "")):
        if need not in parts or (want and want not in parts[need]):
            miss.append(f"{need} {want}".strip())
    for k in ("x-content-type-options", "referrer-policy", "permissions-policy"):
        if k not in h:
            miss.append(k)
    if miss:
        return [_row("headers", "Security headers", "fail", "Security headers adhoore: " + ", ".join(miss), csp[:200])]
    return [_row("headers", "Security headers", "pass",
                 "CSP (sirf apni scripts, koi plugin nahi, frame mein nahi khulti) + nosniff + referrer + permissions sab hain.")]


# ---------------------------------------------------------------- 4. pages (OWASP on every page)
def gate_pages(out: Path, pages: list[Path]) -> list[dict[str, Any]]:
    inline, handlers, jsurl, ext, mixed, frames, noopener = [], [], [], [], [], [], []
    secs: dict[str, list[str]] = {}

    def at(key: str, h: str, pos: int) -> None:
        sid = _sec_at(h, pos)
        if sid:
            secs.setdefault(key, []).append(sid)
    for p in pages:
        h = p.read_text(encoding="utf-8", errors="ignore")
        name = _rel(out, p)
        for sm in SCRIPT_TAG.finditer(h):
            attrs, body = sm.group(1), sm.group(2)
            src = re.search(r"""\ssrc\s*=\s*["']([^"']+)""", attrs)
            if src:
                u = urlparse(src.group(1))
                if u.scheme in ("http", "https") and (u.hostname or "") not in SCRIPT_OK:
                    ext.append(f"{name}: {src.group(1)[:60]}")
                    at("ext", h, sm.start())
            elif body.strip() and "application/ld+json" not in attrs:
                inline.append(name)
                at("inline", h, sm.start())
        m = ON_ATTR.search(h)
        if m:
            handlers.append(f"{name}: {m.group(1)}")
            at("handlers", h, m.start())
        m = JS_URL.search(h)
        if m:
            jsurl.append(name)
            at("jsurl", h, m.start())
        m = HTTP_RES.search(h)
        if m:
            mixed.append(name)
            at("mixed", h, m.start())
        for fm in IFRAME.finditer(h):
            src = fm.group(1)
            host = urlparse(src).hostname or ""
            if src.startswith(("http://", "https://")) and host not in FRAME_OK:
                frames.append(f"{name}: {host}")
                at("frames", h, fm.start())
        for a in BLANK_A.findall(h):
            if "noopener" not in a and "noreferrer" not in a:
                noopener.append(name)
                break
    rows = []

    def one(check: str, items: list[str], say: str, state: str = "fail", key: str = "") -> None:
        if items:
            rows.append(_row("pages", check, state, f"{len(items)} page(s): {say}", "; ".join(items[:5]), secs.get(key)))
        else:
            rows.append(_row("pages", check, "pass", "Har page saaf."))
    one("No inline script", inline, "page ke andar likha script (browser use rok dega, aur yeh XSS ka rasta hai)", key="inline")
    one("No on*= event handlers", handlers, "onclick= jaise handler (XSS ka rasta)", key="handlers")
    one("No javascript: links", jsurl, "javascript: link", key="jsurl")
    one("No outside scripts", ext, "bahar se script load ho rahi hai", key="ext")
    one("No http:// resources", mixed, "http:// se cheez aa rahi hai (https page par mixed content)", key="mixed")
    one("Frames only from known hosts", frames, "anjaane host ka iframe", key="frames")
    one("New-tab links have rel=noopener", noopener, "naye tab ka link bina rel=noopener", "warn")
    return rows


# ---------------------------------------------------------------- 5. forms + 6. bots
def gate_forms(out: Path, pages: list[Path], form_endpoint: str, turnstile: bool) -> list[dict[str, Any]]:
    bad_post, no_hp, pw, n_forms = [], [], [], 0
    want = urlparse(form_endpoint).hostname or ""
    for p in pages:
        name = _rel(out, p)
        if name.split("/")[0] in ("account", "admin"):          # the app pages: logins belong there
            continue
        h = p.read_text(encoding="utf-8", errors="ignore")
        for fm in FORM.finditer(h):
            attrs, body = fm.group(1), fm.group(2)
            n_forms += 1
            act = re.search(r"""\saction\s*=\s*["']([^"']+)""", attrs)
            if act and act.group(1).startswith(("http://", "https://")) and (urlparse(act.group(1)).hostname or "") != want:
                bad_post.append(f"{name}: {act.group(1)[:60]}")
            if "data-hoola-form" in attrs:
                ep = re.search(r"""data-endpoint\s*=\s*["']([^"']+)""", attrs)
                if ep and (urlparse(ep.group(1)).hostname or "") != want:
                    bad_post.append(f"{name}: {ep.group(1)[:60]}")
                if not re.search(r"""name\s*=\s*["']website["']""", body):
                    no_hp.append(name)
            if re.search(r"""type\s*=\s*["']password["']""", body):
                pw.append(name)
    rows = []
    rows.append(_row("forms", "Forms post only to her Hoola form address", "fail" if bad_post else "pass",
                     f"{len(bad_post)} form kisi aur jagah data bhej raha hai." if bad_post else f"{n_forms} form, sab sirf Hoola ke form address par.",
                     "; ".join(bad_post[:5])))
    rows.append(_row("forms", "Every enquiry form has the hidden honeypot", "fail" if no_hp else "pass",
                     f"{len(no_hp)} page ke form mein chhupa honeypot nahi." if no_hp else "Har form mein chhupa honeypot (bot ise bharta hai, insaan nahi).",
                     "; ".join(no_hp[:5])))
    rows.append(_row("forms", "No password box on a public page", "fail" if pw else "pass",
                     "Public page par password ka box - login sirf account / admin page par." if pw else "Kisi public page par password box nahi.",
                     "; ".join(pw[:5])))
    if n_forms and not (out / "privacy" / "index.html").exists():
        rows.append(_row("forms", "A privacy page beside the forms", "fail",
                         "Form logon ki jaankari leta hai par privacy page nahi (DPDP Act 2023)."))
    if not n_forms:
        rows.append(_row("bots", "Bot protection on forms", "pass", "Website par koi form nahi."))
    elif turnstile:
        rows.append(_row("bots", "Bot protection on forms", "pass",
                         "Cloudflare Turnstile har form par (server har bheja form Cloudflare se jaanchta hai) + honeypot + seemayein."))
    else:
        rows.append(_row("bots", "Bot protection on forms", "warn",
                         "Turnstile chalu nahi (server par SITE_TURNSTILE_SITE / SECRET nahi). Abhi bachav: chhupa honeypot + ek "
                         "address se 10 minute mein 5 + din mein 200 enquiry."))
    return rows


# ---------------------------------------------------------------- 7. accessibility (WCAG 2.2 AA, what a file can prove)
IMG = re.compile(r"<img\b([^>]*)>", re.I)
CONTROL = re.compile(r"<(input|select|textarea)\b([^>]*)>", re.I)
A_TAG = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
BUTTON = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.I | re.S)


def _named(attrs: str, inner: str) -> bool:
    if re.search(r"""aria-label(?:ledby)?\s*=\s*["'][^"']+["']|title\s*=\s*["'][^"']+["']""", attrs):
        return True
    txt = re.sub(r"<[^>]+>", " ", inner)
    if txt.strip():
        return True
    return bool(re.search(r"""<img\b[^>]*alt\s*=\s*["'][^"']+["']""", inner) or re.search(r"aria-label", inner))


def gate_accessibility(out: Path, pages: list[Path], report: dict[str, Any]) -> list[dict[str, Any]]:
    probs: dict[str, list[str]] = {"lang": [], "title": [], "alt": [], "label": [], "name": [], "zoom": []}
    secs: dict[str, list[str]] = {}
    for p in pages:
        name = _rel(out, p)
        h = p.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"<html\b[^>]*\slang\s*=\s*[\"'][^\"']+", h, re.I):
            probs["lang"].append(name)
        if not re.search(r"<title>[^<]+</title>", h, re.I):
            probs["title"].append(name)
        for im in IMG.finditer(h):
            if not re.search(r"\salt\s*=", im.group(1)):
                probs["alt"].append(name)
                secs.setdefault("alt", []).append(_sec_at(h, im.start()))
                break
        labels = set(re.findall(r"""<label\b[^>]*\sfor\s*=\s*["']([^"']+)""", h, re.I))
        wrapped = re.findall(r"<label\b[^>]*>(.*?)</label>", h, re.I | re.S)
        for cm in CONTROL.finditer(h):
            tag, attrs = cm.group(1), cm.group(2)
            if re.search(r"""type\s*=\s*["'](?:hidden|submit|button|reset|image)["']""", attrs) or re.search(r'class\s*=\s*"hp"', attrs):
                continue
            if re.search(r"""aria-label(?:ledby)?\s*=\s*["'][^"']+|title\s*=\s*["'][^"']+""", attrs):
                continue
            idm = re.search(r"""\sid\s*=\s*["']([^"']+)""", attrs)
            if idm and idm.group(1) in labels:
                continue
            if any(attrs[:60] in w for w in wrapped):
                continue
            probs["label"].append(name)
            secs.setdefault("label", []).append(_sec_at(h, cm.start()))
            break
        for am in list(A_TAG.finditer(h)) + list(BUTTON.finditer(h)):
            if not _named(am.group(1), am.group(2)):
                probs["name"].append(name)
                secs.setdefault("name", []).append(_sec_at(h, am.start()))
                break
        vp = re.search(r"""<meta\b[^>]*name\s*=\s*["']viewport["'][^>]*>""", h, re.I)
        if vp and re.search(r"user-scalable\s*=\s*(?:no|0)|maximum-scale\s*=\s*1(?:\.0)?\b", vp.group(0), re.I):
            probs["zoom"].append(name)
    say = {"lang": "page ki bhasha (html lang) nahi - screen reader galat bolega (WCAG 3.1.1)",
           "title": "page ka title nahi (2.4.2)", "alt": "tasveer bina alt ke (1.1.1)",
           "label": "form ka box bina label ke (1.3.1 / 4.1.2)", "name": "link / button bina naam ke (2.4.4 / 4.1.2)",
           "zoom": "zoom band kiya gaya (1.4.4)"}
    check = {"lang": "page language (3.1.1)", "title": "page title (2.4.2)", "alt": "image alt text (1.1.1)",
             "label": "labelled form boxes (1.3.1, 4.1.2)", "name": "named links and buttons (2.4.4, 4.1.2)",
             "zoom": "zoom allowed (1.4.4)"}
    rows = []
    for k, items in probs.items():
        rows.append(_row("accessibility", f"WCAG 2.2 AA {check[k]} on every page",
                         "fail" if items else "pass", f"{len(items)} page(s): {say[k]}" if items else "Har page par theek.",
                         "; ".join(items[:5]), [x for x in secs.get(k, []) if x]))
    a11y = [b for b in (report.get("blocking") or []) if b.get("kind") == "a11y"]
    src = str(report.get("source") or "")
    if "axe" in src:
        rows.append(_row("accessibility", "axe-core in the browser (opened pages)", "fail" if a11y else "pass",
                         f"{len(a11y)} gambhir accessibility galti browser mein mili (version ki jaanch mein bhi likhi)." if a11y
                         else "Browser mein khule pages par axe ko koi gambhir galti nahi mili.",
                         "; ".join(b["text"] for b in a11y[:4])))
    else:
        rows.append(_row("accessibility", "axe-core in the browser (opened pages)", "not_checked",
                         "Is jaanch mein axe nahi chala (browser jaanch nahi hui) - sirf files wali WCAG jaanch hui."))
    return rows


# ---------------------------------------------------------------- 8. legal per profession
def _site_text(pages: list[Path], cap: int = 400) -> str:
    """The visible words of the designed pages (catalogue item pages are sampled: the claims live in her own pages)."""
    keep = [p for p in pages if "/page/" not in p.as_posix()]
    keep = sorted(keep, key=lambda p: len(p.parts))[:cap]
    txt = []
    for p in keep:
        h = p.read_text(encoding="utf-8", errors="ignore")
        h = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S | re.I)
        txt.append(re.sub(r"<[^>]+>", " ", h))
    return re.sub(r"\s+", " ", " ".join(txt))


def gate_legal(out: Path, pages: list[Path], site: dict[str, Any]) -> list[dict[str, Any]]:
    legal = set(site.get("legal") or [])
    shop = bool((site.get("shop") or {}).get("api"))
    text = _site_text(pages)
    rows = []
    if "dmr" in legal or "nmc" in legal:
        hits = sorted({m.group(0).strip() for rx in DMR for m in rx.finditer(text)})[:6]
        rows.append(_row("legal", "No cure claims (Drugs and Magic Remedies Act, 1954)", "fail" if hits else "pass",
                         "Website kisi bimari ka 'pakka ilaaj / cure' claim kar rahi hai - yeh kanoon se mana hai (saza ho sakti hai). "
                         "Yeh shabd hataiye." if hits else "Koi 'pakka ilaaj' claim nahi.", "; ".join(hits)))
    if "nmc" in legal:
        ok = bool(REGNO.search(text))
        rows.append(_row("legal", "Doctor's registration number shown (NMC)", "pass" if ok else "warn",
                         "Registration number dikh raha hai." if ok else
                         "Doctor ka registration number (State Medical Council / NMC) website par nahi - NMC ke niyam ise dikhane ko "
                         "kehte hain. Facts mein daaliye, agli version mein aa jayega."))
    if "bci" in legal:
        hits = sorted({m.group(0).strip() for m in BCI.finditer(text)})[:6]
        rows.append(_row("legal", "No solicitation (Bar Council of India rule 36)", "fail" if hits else "pass",
                         "Vakeel apna prachaar nahi kar sakte ('best lawyer', 'guaranteed win' jaise shabd mana hain) - hataiye."
                         if hits else "Koi prachaar wale shabd nahi; disclaimer laga hai.", "; ".join(hits)))
    if "fssai" in legal:
        ok = bool(FSSAI.search(text))
        rows.append(_row("legal", "FSSAI licence number shown", "pass" if ok else ("fail" if shop else "warn"),
                         "FSSAI number dikh raha hai." if ok else
                         ("Online khana / food bechne wali website par FSSAI licence number dikhana zaroori hai (FSS e-commerce "
                          "guidelines) - facts mein FSSAI number daaliye." if shop else
                          "FSSAI number website par nahi - food business ke liye dikhana accha hai (facts mein daaliye).")))
    if "edu" in legal:
        hits = sorted({m.group(0).strip() for m in EDU.finditer(text)})[:6]
        rows.append(_row("legal", "No guaranteed-result claims (coaching)", "warn" if hits else "pass",
                         "'100% placement / guaranteed result' jaisa claim - CCPA ke coaching guidelines (2024) ise bhramak maante "
                         "hain; saboot na ho to hataiye." if hits else "Koi pakka-nateeja claim nahi.", "; ".join(hits)))
    if shop or "legal_metrology" in legal:
        need = [k for k in ("refund", "terms", "privacy") if not (out / k / "index.html").exists()]
        rows.append(_row("legal", "Seller pages for an online shop (Consumer Protection (E-Commerce) Rules 2020)",
                         "fail" if need and shop else ("warn" if need else "pass"),
                         f"Yeh page nahi: {', '.join(need)} - online bechne ke liye refund / terms / privacy page zaroori." if need
                         else "Refund, terms aur privacy page hain; seller ka naam / pata / sampark footer mein."))
    if not rows:
        rows.append(_row("legal", "Profession rules", "pass", "Is kaam ke liye koi khaas kanooni page nahi chahiye; privacy page laga hai."))
    return rows


# ---------------------------------------------------------------- 9. trackers + 10. limits
def gate_trackers(out: Path, pages: list[Path]) -> list[dict[str, Any]]:
    found: dict[str, str] = {}
    banner = False
    for p in pages[:3000]:
        h = p.read_text(encoding="utf-8", errors="ignore")
        if "data-hoola-consent" in h:
            banner = True
        for name, rx in TRACKERS:
            if name not in found and rx.search(h):
                found[name] = _rel(out, p)
    if not found:
        return [_row("trackers", "Cookie banner only when a tracker is present", "pass",
                     "Koi tracker nahi (Hoola visits server par ginta hai, bina cookie ke) - isliye cookie banner ki zaroorat nahi.")]
    if banner:
        return [_row("trackers", "Cookie banner only when a tracker is present", "pass",
                     f"Tracker hai ({', '.join(found)}) aur consent banner laga hai.")]
    return [_row("trackers", "Cookie banner only when a tracker is present", "fail",
                 f"Tracker mila ({', '.join(found)}) par visitor se poocha nahi gaya - DPDP Act 2023 ke hisaab se pehle haan "
                 "chahiye. Tracker hataiye ya consent banner lagwaiye.", "; ".join(f"{k}: {v}" for k, v in found.items()))]


def gate_limits() -> list[dict[str, Any]]:
    from ..config import get_settings
    st = get_settings()
    return [_row("limits", "Rate limits behind the site", "pass",
                 f"Server par: enquiry form ek address se 10 minute mein 5, din mein 200; dukaan order ek address se 10 minute "
                 f"mein {getattr(st, 'site_shop_ip_cap', 12)}, din mein {getattr(st, 'site_shop_day_cap', 300)}; login / OTP "
                 "ki apni seemayein (security.py). Yeh code mein hain, har website par lagte hain.")]


# ---------------------------------------------------------------- the scan
def gate_look(out: Path, site: dict[str, Any]) -> list[dict[str, Any]]:
    """v0.606 the AI-look tells (site/look.py): warnings with the section to fix, never a fail."""
    from ..config import get_settings
    if not getattr(get_settings(), "site_look", True):
        return []
    from . import look as LK
    return LK.rows(LK.scan(out, site))


def turnstile_on() -> bool:
    from ..config import get_settings
    st = get_settings()
    return bool(getattr(st, "site_turnstile_site", "") and getattr(st, "site_turnstile_secret", ""))


def scan(out: Path, site: dict[str, Any], report: dict[str, Any] | None = None, form_endpoint: str = "") -> dict[str, Any]:
    STATS["scans"] += 1
    report = report or {}
    pages = _pages(out)
    rows: list[dict[str, Any]] = []
    for fn in (lambda: gate_secrets(out), lambda: gate_libraries(out), lambda: gate_headers(out),
               lambda: gate_pages(out, pages), lambda: gate_forms(out, pages, form_endpoint, turnstile_on()),
               lambda: gate_accessibility(out, pages, report), lambda: gate_legal(out, pages, site),
               lambda: gate_trackers(out, pages), gate_limits, lambda: gate_look(out, site)):
        try:
            rows += fn()
        except Exception as e:                              # noqa: BLE001 - a broken gate is NOT CHECKED, never a pass
            rows.append(_row("gate", "A gate could not run", "not_checked", f"Yeh jaanch chal nahi payi: {type(e).__name__}"))
    count = {k: sum(1 for r in rows if r["state"] == k) for k in ("pass", "warn", "fail", "not_checked")}
    if count["fail"]:
        STATS["fails"] += 1
    return {"rows": rows, **count, "pages": len(pages), "ok": not count["fail"],
            "blocks": [f"{r['check']}: {r['say']}" for r in rows if r["state"] == "fail"]}


def merge(report: dict[str, Any], res: dict[str, Any]) -> dict[str, Any]:
    """The gate result joins a version's report: every FAIL is a blocking item (so the launch card refuses it)."""
    seen = {b.get("text") for b in report.get("blocking") or []}
    blocking = list(report.get("blocking") or []) + [
        {"kind": "gate", "text": f"{r['check']}: {r['say']}", "sections": r.get("sections") or []}
        for r in res["rows"] if r["state"] == "fail" and f"{r['check']}: {r['say']}" not in seen]
    warnings = list(report.get("warnings") or []) + [
        {"kind": "gate", "text": f"{r['check']}: {r['say']}", "sections": []} for r in res["rows"] if r["state"] == "warn"]
    out = {**report, "gates": {k: res[k] for k in ("rows", "pass", "warn", "fail", "not_checked", "pages")},
           "blocking": blocking, "warnings": warnings}
    out["passed"] = not blocking
    return out


def view(report: dict[str, Any]) -> dict[str, Any]:
    g = report.get("gates") or {}
    return {"rows": g.get("rows") or [], "pass": g.get("pass", 0), "warn": g.get("warn", 0), "fail": g.get("fail", 0),
            "not_checked": g.get("not_checked", 0)}


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d
