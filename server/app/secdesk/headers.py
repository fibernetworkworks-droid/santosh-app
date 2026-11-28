"""A web response's security headers and cookies checked the way a security engineer reviews them: paste `curl -sI https://...` (or
the browser's response headers; redirects in one paste are read hop by hop). Strict-Transport-Security (present, long enough,
subdomains, preload), Content-Security-Policy (script sources that allow inline code or eval, wildcards, missing object-src,
base-uri, frame-ancestors - and report-only that blocks nothing), clickjacking cover, X-Content-Type-Options, Referrer-Policy,
Permissions-Policy, version banners, cross-origin rules (any origin with credentials, the null origin), and each cookie's
Secure / HttpOnly / SameSite and its __Host- / __Secure- prefix rules. Read from what you paste - nothing is fetched."""
from __future__ import annotations

import re
from typing import Any

from .common import SecInputError, finder, finish


class HeadersError(SecInputError):
    pass


SESSIONISH = re.compile(r"sess|sid|token|auth|jwt|login|remember|csrf|xsrf|connect\.sid|phpsessid|jsessionid|asp\.net", re.I)


def _blocks(text: str) -> list[dict[str, Any]]:
    out, cur = [], None
    for raw in str(text or "").replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(HTTP/[\d.]+)\s+(\d{3})", line)
        if m:
            cur = {"status": int(m.group(2)), "h": []}
            out.append(cur)
            continue
        if line.startswith(("< ", "> ")):
            line = line[2:]
        if ":" in line and not line.lower().startswith(("http://", "https://")):
            if cur is None:
                cur = {"status": None, "h": []}
                out.append(cur)
            k, v = line.split(":", 1)
            cur["h"].append((k.strip().lower(), v.strip()))
    return [b for b in out if b["h"] or b["status"]]


def _get(b: dict[str, Any], k: str) -> list[str]:
    return [v for kk, v in b["h"] if kk == k]


def _csp(v: str) -> dict[str, list[str]]:
    d: dict[str, list[str]] = {}
    for part in v.split(";"):
        w = part.strip().split()
        if w:
            d.setdefault(w[0].lower(), [x for x in w[1:]])
    return d


def analyse(text: str, url: str = "", hsts_min_days: float = 180) -> dict[str, Any]:
    bl = _blocks(text)
    if not bl:
        raise HeadersError("Paste the response headers - `curl -sI https://your.site` prints them.")
    issues, add = finder()
    https = not url or url.lower().startswith("https")
    hops = [{"status": b["status"], "location": (_get(b, "location") or [""])[0]} for b in bl]
    b = bl[-1]
    h = {k: v for k, v in b["h"]}
    checks: list[dict[str, Any]] = []

    def ck(name: str, ok: bool, say: str, sev: str = "warn", fix: str = "") -> None:
        checks.append({"name": name, "ok": ok, "say": say})
        if not ok:
            add(sev, name, say, fix)
    # HSTS
    hs = h.get("strict-transport-security", "")
    if https:
        if not hs:
            ck("HSTS", False, "No Strict-Transport-Security - a first visit over plain HTTP can be intercepted.", "warn",
               f"Strict-Transport-Security: max-age=31536000; includeSubDomains")
        else:
            m = re.search(r"max-age\s*=\s*\"?(\d+)", hs, re.I)
            age = int(m.group(1)) if m else 0
            ok = age >= hsts_min_days * 86400
            ck("HSTS", ok, f"HSTS max-age is {age // 86400} day(s)" + ("." if ok else f" - under your {hsts_min_days:g}."), "warn", "Raise max-age to 31536000 (a year).")
            if ok and "includesubdomains" not in hs.lower():
                add("info", "HSTS subdomains", "HSTS does not cover subdomains.", "Add includeSubDomains once every subdomain serves HTTPS.")
    # CSP
    csp = h.get("content-security-policy", "")
    ro = h.get("content-security-policy-report-only", "")
    if not csp:
        ck("CSP", False, "No Content-Security-Policy" + (" (only report-only - it blocks nothing)." if ro else " - injected scripts would run."), "warn",
           "Start with: default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'")
    else:
        d = _csp(csp)
        src = d.get("script-src", d.get("default-src"))
        if src is None:
            ck("CSP scripts", False, "The CSP has no script-src or default-src, so scripts are not limited.", "warn", "Add default-src 'self' or a script-src.")
        else:
            lo = [x.lower() for x in src]
            strict = any(x.startswith(("'nonce-", "'sha256-", "'sha384-", "'sha512-")) for x in lo) and "'strict-dynamic'" in lo
            if "'unsafe-inline'" in lo and not any(x.startswith(("'nonce-", "'sha")) for x in lo):
                ck("CSP scripts", False, "script-src allows 'unsafe-inline' - an injected <script> runs.", "warn", "Use nonces or hashes instead of 'unsafe-inline'.")
            elif "'unsafe-eval'" in lo:
                ck("CSP scripts", False, "script-src allows 'unsafe-eval'.", "warn", "Remove 'unsafe-eval' (rewrite code that builds code from strings).")
            elif not strict and any(x in ("*", "https:", "http:", "data:", "blob:") or x.startswith("*.") for x in lo):
                ck("CSP scripts", False, f"script-src allows {', '.join(x for x in src if x in ('*', 'https:', 'http:', 'data:', 'blob:') or x.startswith('*.'))} - scripts from almost anywhere.", "warn",
                   "Name the hosts, or use nonces with 'strict-dynamic'.")
            else:
                ck("CSP scripts", True, "Scripts are limited by the CSP.")
        if "object-src" not in d and [x.lower() for x in d.get("default-src", [])] != ["'none'"]:
            add("info", "CSP object-src", "No object-src - plugins fall back to default-src.", "Add object-src 'none'.")
        if "base-uri" not in d:
            add("info", "CSP base-uri", "No base-uri - an injected <base> can redirect relative scripts.", "Add base-uri 'self' (or 'none').")
    # clickjacking
    fa = _csp(csp).get("frame-ancestors") if csp else None
    xfo = h.get("x-frame-options", "")
    ck("Framing", bool(fa) or xfo.upper() in ("DENY", "SAMEORIGIN"), "Pages can be framed by any site (clickjacking)." if not (fa or xfo) else "Framing is limited.", "warn",
       "Add frame-ancestors 'self' to the CSP (or X-Frame-Options: DENY).")
    ck("No sniffing", h.get("x-content-type-options", "").lower() == "nosniff", "X-Content-Type-Options is not nosniff." if h.get("x-content-type-options", "").lower() != "nosniff" else "nosniff is set.", "info",
       "X-Content-Type-Options: nosniff")
    rp = h.get("referrer-policy", "")
    if rp.lower() in ("unsafe-url", "no-referrer-when-downgrade"):
        ck("Referrer", False, f"Referrer-Policy {rp} sends full addresses (with their query strings) to other sites.", "warn", "Referrer-Policy: strict-origin-when-cross-origin")
    elif not rp:
        add("info", "Referrer", "No Referrer-Policy (browsers default to strict-origin-when-cross-origin).", "Set it explicitly.")
    if "permissions-policy" not in h:
        add("info", "Permissions", "No Permissions-Policy - camera, microphone and location are not switched off for embedded content.", "Permissions-Policy: camera=(), microphone=(), geolocation=()")
    for k in ("server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version", "x-generator"):
        v = h.get(k, "")
        if v and re.search(r"\d", v):
            add("info", "Version shown", f"{k}: {v} tells anyone the exact software version.", "Remove the version from this header.")
    # CORS
    acao = h.get("access-control-allow-origin", "")
    acac = h.get("access-control-allow-credentials", "").lower() == "true"
    if acao == "*" and acac:
        add("bad", "CORS", "Any origin with credentials - browsers refuse it, and it shows the server was set to trust every site.", "Allow named origins only.")
    elif acao.lower() == "null":
        add("warn", "CORS", "Access-Control-Allow-Origin: null - sandboxed pages and local files are trusted.", "Allow named origins only.")
    elif acao == "*":
        add("info", "CORS", "Any origin may read this response (fine for public data, not for anything private).", "")
    # cookies
    cookies = []
    for c in _get(b, "set-cookie"):
        parts = [p.strip() for p in c.split(";")]
        name = parts[0].split("=", 1)[0].strip()
        attrs = {p.split("=", 1)[0].strip().lower(): (p.split("=", 1)[1].strip() if "=" in p else True) for p in parts[1:] if p}
        ss = str(attrs.get("samesite", "")).lower() if attrs.get("samesite") else ""
        fl = []
        sess = bool(SESSIONISH.search(name))
        if https and "secure" not in attrs:
            fl.append("no Secure")
            add("warn" if sess else "info", "Cookie", f"{name} has no Secure flag - it can be sent over plain HTTP.", "Add Secure.", name)
        if sess and "httponly" not in attrs:
            fl.append("no HttpOnly")
            add("warn", "Cookie", f"{name} looks like a session cookie and has no HttpOnly - page scripts can read it.", "Add HttpOnly.", name)
        if not ss:
            fl.append("no SameSite")
            add("info", "Cookie", f"{name} has no SameSite (browsers treat it as Lax).", "Set SameSite=Lax (or Strict).", name)
        elif ss == "none" and "secure" not in attrs:
            fl.append("SameSite=None without Secure")
            add("bad", "Cookie", f"{name} is SameSite=None without Secure - browsers reject it.", "Add Secure.", name)
        if name.startswith("__Host-") and ("secure" not in attrs or "domain" in attrs or str(attrs.get("path", "")) != "/"):
            fl.append("__Host- rules broken")
            add("bad", "Cookie", f"{name} breaks the __Host- rules (Secure, Path=/, no Domain) - browsers drop it.", "Fix the attributes or the name.", name)
        if name.startswith("__Secure-") and "secure" not in attrs:
            fl.append("__Secure- without Secure")
            add("bad", "Cookie", f"{name} is __Secure- without Secure - browsers drop it.", "Add Secure.", name)
        cookies.append({"name": name, "secure": "secure" in attrs, "httponly": "httponly" in attrs, "samesite": ss or "", "domain": attrs.get("domain") if isinstance(attrs.get("domain"), str) else "",
                        "session": sess, "flags": fl})
    if len(bl) > 1 and hops[0]["status"] in (301, 302, 307, 308) and hops[0]["location"].lower().startswith("http://"):
        add("warn", "Redirect", "A redirect sends visitors to plain HTTP.", "Redirect to the https:// address.")
    grade_pts = sum(1 for c in checks if c["ok"])
    res = {"url": url, "status": b["status"], "hops": hops, "headers": [{"name": k, "value": v[:400]} for k, v in b["h"] if k != "set-cookie"][:80], "cookies": cookies,
           "checks": checks, "passed": grade_pts, "total": len(checks), "csp": {k: v for k, v in _csp(csp).items()} if csp else {},
           "verdict": f"{grade_pts} of {len(checks)} header checks pass" + (f", {len(cookies)} cookie(s)" if cookies else "")}
    res["note"] = "Read only from the headers you pasted (the last response if there were redirects). Nothing was fetched; a page behind a login may send other headers."
    return finish(res, issues)
