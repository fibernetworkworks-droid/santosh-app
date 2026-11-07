"""v0.542.0 P2 ENRICHMENT - the omkarcloud email flow, our own hands (docs/LEADS_PLAN.md section 6).

A kept lead's OWN website gets ONE bounded pass, through code that already existed (the port law in reverse:
the reuse law - nothing new is built that the house already has):

  FETCH    `app/agent/scrape_tools` - the SSRF guard (_guard_url), the robots.txt gate (scrape_respect_robots,
           default True, fail-open only on unreachable robots), the curl_cffi fetcher and the proxy POLICY.
           No second fetch client is written here and no browser is launched (the stealth lane stays OFF
           behind its setting, as it has been since v0.208.1).
  EYES     `app/crawl/blocked.why_blocked` names a block page / CAPTCHA wall for what it is - the enrich pass
           records it honestly and moves on; Hoola does not muscle through (rules.NEVER).
  TEXT     `app/crawl/prune.prune` - the same HTML->text pruner the crawl brain reads.
  MAIL     mailto: links + a regex over the pruned text; social links BY HOSTNAME of her own site's pages
           (linkedin/twitter/x/instagram/facebook/youtube). NOTHING is fetched from the social platforms
           themselves (rules.NEVER: "Social-platform scraping ... NOT BUILT").
  GRADE    DNS exists -> MX exists -> not a disposable domain -> `email_grade` = pakka / sadak_tak / galat
           (maps_address_check's vocabulary, rules.EMAIL_GRADES). We do NOT SMTP-probe - no RCPT TO, ever
           (spam infrastructure; rules.NEVER).
  PICK     the AI best-email: ONE cheap-brain call per row (usage.run_meter catches the spend - the
           research/bill.py pattern), the pick validated against the candidates, its reason kept. With no
           model configured the deterministic rank answers and the card says "rule" - never a pretended AI.

Politeness: site-level 1 request/second (per-host min interval), at most SITE_PAGES_MAX pages per site
(home + contact-ish links). Zero model calls for rows with no email candidates.
"""
from __future__ import annotations

import json
import re
import socket
import time
from typing import Any
from urllib.parse import urljoin, urlparse

PARSER_ENRICH = "v0.672.0-en1"          # every enriched field names the code that read its site

SITE_PAGES_MAX = 3                       # home + up to two contact-ish pages; a lead site is read, not crawled
HOST_MIN_INTERVAL = 1.0                  # site-level politeness: >= 1s between fetches to the same host
FETCH_TIMEOUT = 20
_EMAIL_CAP = 24                          # candidates kept per row (the model prompt and the log stay small)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
HREF_RE = re.compile(r"""<a\s[^>]*?href\s*=\s*["']([^"']+)["']""", re.IGNORECASE | re.S)

_SOCIAL_HOSTS = (("linkedin", "linkedin.com"), ("twitter", "twitter.com"), ("twitter", "x.com"),
                 ("instagram", "instagram.com"), ("facebook", "facebook.com"), ("youtube", "youtube.com"))
_CONTACT_WORDS = ("contact", "about", "reach", "sampark", "contact-us", "contactus")

_ROLE_INBOXES = ("info", "contact", "sales", "hello", "office", "admin", "support", "enquiry", "enquiries",
                 "marketing", "care", "customercare", "booking", "orders")
_PERSONAL_DOMAINS = ("gmail.com", "yahoo.com", "yahoo.co.in", "hotmail.com", "outlook.com", "rediffmail.com",
                     "live.com", "icloud.com")
_JUNK_TAILS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js", ".webp", ".ico", ".pdf")

DISPOSABLE_DOMAINS = frozenset({
    "mailinator.com", "tempmail.com", "temp-mail.org", "guerrillamail.com", "yopmail.com", "10minutemail.com",
    "trashmail.com", "throwawaymail.com", "sharklasers.com", "getnada.com", "dispostable.com", "fakeinbox.com",
    "maildrop.cc", "tempinbox.com", "spam4.me", "grr.la", "mytemp.email", "burnermail.io", "trbvm.com", "tmail.ws",
})


class EnrichError(ValueError):
    """The enrich pass refused / could not read - the caller sees the reason, never a silent skip."""


# ---------------------------------------------------------------- the boundaries (tests fake THESE, zero network)
def _robots_ok(url: str) -> bool:
    """robots.txt gate - the scrape lane's own check, one wrapper so a test can stand at this boundary."""
    from ..agent.scrape_tools import _robots_allowed
    return _robots_allowed(url)


def _get(url: str, tenant_id: str):
    """One public page through the EXISTING scrape stack (SSRF guard + curl_cffi + proxy policy)."""
    from ..agent.scrape_tools import _fetch, _guard_url
    return _fetch(_guard_url(url), tenant_id, timeout=FETCH_TIMEOUT)


def _resolve_dns(domain: str) -> bool:
    """DNS A/AAAA lookup - stdlib only."""
    try:
        return bool(socket.getaddrinfo(domain, None))
    except socket.gaierror:
        return False


def _resolve_mx(domain: str) -> bool:
    """MX record lookup - dnspython (already in the house deps)."""
    import dns.resolver                                  # noqa: PLC0415 - lazy, like every heavy import here
    try:
        return bool(dns.resolver.resolve(domain, "MX", lifetime=5))
    except Exception:                                    # noqa: BLE001 - NXDomain / no MX / timeouts all mean "no"
        return False


_LAST_HIT: dict[str, float] = {}


def _polite(host: str) -> None:
    """Site-level 1 request/second: the same host never sees two fetches inside HOST_MIN_INTERVAL."""
    wait = HOST_MIN_INTERVAL - (time.monotonic() - _LAST_HIT.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _LAST_HIT[host] = time.monotonic()


# ---------------------------------------------------------------- the read (pure string work - fixtures feed tests)
def extract_emails(html: str) -> list[str]:
    """mailto: links first, then a regex over the PRUNED text (crawl brain's reader, not raw soup)."""
    out: list[str] = []
    for m in re.finditer(r"mailto:([^\"'?>\s]+)", html or "", re.IGNORECASE):
        out.append(m.group(1))
    try:
        from ..crawl import prune as _prune
        stripped = re.sub(r"(?is)<(script|style|noscript|template)[^>]*>.*?</\1>", " ", html or "")
        text = _prune.as_text(_prune.prune(stripped))
    except Exception:                                    # noqa: BLE001 - a page prune cannot kill the pass
        text = re.sub(r"<[^>]+>", " ", html or "")
    for m in EMAIL_RE.finditer(text):
        out.append(m.group(0))
    if not out:                                          # the pruner optimises big pages; a one-line contact
        text = re.sub(r"<[^>]+>", " ", stripped)         # card page must still give up its address
        for m in EMAIL_RE.finditer(text):
            out.append(m.group(0))
    seen, clean = set(), []
    for raw in out:
        e = raw.strip().strip(".").lower()
        if not e or e in seen or len(e) > 100 or "@" not in e:
            continue
        if e.endswith(_JUNK_TAILS) or e.startswith(("noreply", "no-reply", "donotreply", "postmaster@",
                                                    "abuse@", "example.", "test@", "sentry", "u003e")):
            continue
        seen.add(e)
        clean.append(e)
        if len(clean) >= _EMAIL_CAP:
            break
    return clean


def extract_socials(html: str, base_url: str = "") -> dict[str, str]:
    """Social links BY HOSTNAME from her own site's pages. One handle per platform, the first wins."""
    got: dict[str, str] = {}
    base = base_url or ""
    for m in HREF_RE.finditer(html or ""):
        href = (m.group(1) or "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
            continue
        absu = urljoin(base, href) if base else href
        host = (urlparse(absu).hostname or "").lower()
        if not host:
            continue
        for name, dom in _SOCIAL_HOSTS:
            if host == dom or host.endswith("." + dom):
                path = urlparse(absu).path.strip("/")
                if not path or path in ("", "login", "share"):   # the platform home is not the business's handle
                    continue
                if name not in got:
                    got[name] = absu.split("?")[0][:300]
    return got


def contact_links(html: str, base_url: str, have: int = 0) -> list[str]:
    """Contact / about pages worth one more fetch each, home-page-first order, SITE_PAGES_MAX bounds the total."""
    out: list[str] = []
    for m in HREF_RE.finditer(html or ""):
        href = (m.group(1) or "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
            continue
        low = href.lower()
        hits = any(w in low for w in _CONTACT_WORDS)
        last = low.rsplit("/", 1)[-1]
        if hits and (last.endswith((".html", ".htm", ".php", "/")) or "." not in last):
            absu = urljoin(base_url, href).split("#")[0]
            if absu not in out:
                out.append(absu)
    return out[: max(0, SITE_PAGES_MAX - have)]


# ---------------------------------------------------------------- the grade (DNS -> MX -> disposable)
def grade_email(email: str) -> str:
    """pakka = DNS + MX + not disposable; sadak_tak = DNS alive but no MX (mail may not flow); galat = dead
    domain or disposable. Syntax-dead is galat before any network. NO SMTP probe, ever."""
    e = (email or "").strip().lower()
    if not EMAIL_RE.fullmatch(e):
        return "galat"
    domain = e.rsplit("@", 1)[1]
    if domain in DISPOSABLE_DOMAINS or domain.endswith(".test") or domain.endswith(".invalid"):
        return "galat"
    if not _resolve_dns(domain):
        return "galat"
    if not _resolve_mx(domain):
        return "sadak_tak"
    return "pakka"


# ---------------------------------------------------------------- the pick (AI with bill, rule as the honest fallback)
_ROLE_RANK = {r: 2 for r in _ROLE_INBOXES}


def rank_emails(emails: list[str], business: str = "") -> list[str]:
    """The deterministic ladder the model must beat: named-person > role inbox > other > personal-domain.
    A name match inside the local part lifts an address (omkarcloud's 'role > named > generic', refined)."""
    biz_tokens = [t for t in re.findall(r"[a-z]+", (business or "").lower()) if len(t) > 2]

    def score(e: str) -> int:
        local, _, domain = e.rpartition("@")
        s = 1
        if local.split("+")[0].split(".")[0] in _ROLE_RANK:
            s = 2
        if domain in _PERSONAL_DOMAINS:
            s = min(s, 0)
        if biz_tokens and any(t in local for t in biz_tokens):
            s = 3
        if "." in local and not any(t in local for t in biz_tokens):
            s = max(s, 2)                                    # first.last shape reads like a person
        return s

    return sorted(set(emails), key=lambda e: (-score(e), e))


async def best_email(emails: list[str], business: str) -> dict[str, Any]:
    """ONE cheap-brain call ranks the candidates; the pick must be one of them. Falls back to the
    deterministic rank (labelled 'rule') when no model answers - the card always names its picker."""
    cands = rank_emails(emails, business)
    if not cands:
        return {"email": "", "reason": "", "pick": "none"}
    if len(cands) == 1:
        return {"email": cands[0], "reason": "ek hi candidate mila", "pick": "single"}
    rule_top = cands[0]
    system = ("Tum ek B2B leads engine ke email picker ho. Diye gaye business ke liye sabse sambhavit "
              "contact email chuno - SIRF candidates mein se. Role inbox (info@/sales@/contact@) jab tak "
              "koi named-person email business se match nahi karta, upar rehta hai. Sirf JSON do: "
              '{"email": "...", "reason": "ek line, Hindi ya English, max 200 chars"}')
    text = (f"Business: {business}\nCandidates:\n" +
            "\n".join(f"- {e}" for e in cands[:12]))
    try:
        from ..agent import llm
        from ..agent.santosh import get_settings
        cheap = llm.cheap_brain()
        if cheap:
            msgs = [{"role": "user", "content": [{"type": "text", "text": text}]}]
            blocks, _, _ = await llm.openai_create(cheap, system, [], msgs, 200)
            raw = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            m = re.search(r"\{.*\}", raw or "", re.S)
            if m:
                js = json.loads(m.group(0))
                pick = str(js.get("email") or "").strip().lower()
                if pick in cands:
                    return {"email": pick, "reason": str(js.get("reason") or "")[:300], "pick": "ai"}
    except Exception:                                    # noqa: BLE001 - a model out never kills the enrich pass
        pass
    return {"email": rule_top, "reason": "model nahi tha - rule rank ne chuna (role inbox > named > generic)",
            "pick": "rule"}


# ---------------------------------------------------------------- the site pass (one bounded read per site)
def site_pass(url: str, tenant_id: str) -> dict[str, Any]:
    """The ONE crawl-brain pass per site: home page (+ contact-ish pages, SITE_PAGES_MAX bound), robots obeyed,
    1 req/s per host, blocked pages recorded honestly. Returns emails / socials / pages / blocked - no store
    writes here; the service applies what the caller accepts."""
    pages: list[dict[str, Any]] = []
    emails: list[str] = []
    socials: dict[str, str] = {}
    blocked: list[str] = []
    host = (urlparse(url).hostname or "").replace("www.", "")
    targets = [url]
    seen = {url.split("#")[0]}
    while targets and len(pages) < SITE_PAGES_MAX:
        u = targets.pop(0)
        try:
            if not _robots_ok(u):
                blocked.append(f"robots: {u}")
                continue
            _polite(host)
            page = _get(u, tenant_id)
            html = getattr(page, "html_content", "") or ""
            status = int(getattr(page, "status", 0) or 0)
            final = getattr(page, "url", "") or u
        except Exception as e:                           # noqa: BLE001 - a dead site is a RESULT, not a crash
            pages.append({"url": u, "status": 0, "dead": str(e)[:200]})
            continue
        from ..crawl import blocked as _blocked
        why = _blocked.why_blocked(html, status, u)
        if why:
            blocked.append(f"{why}: {u}")
            pages.append({"url": u, "status": status, "blocked": why})
            continue
        pages.append({"url": final, "status": status})
        for e in extract_emails(html):
            if e not in emails:
                emails.append(e)
        for k, v in extract_socials(html, final).items():
            socials.setdefault(k, v)
        if len(pages) < SITE_PAGES_MAX:
            for link in contact_links(html, final, have=len(pages)):
                if link not in seen:
                    seen.add(link)
                    targets.append(link)
    return {"site": url, "pages": pages, "emails": emails, "socials": socials, "blocked": blocked,
            "parser_version": PARSER_ENRICH}
