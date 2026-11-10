"""Item 7: tell a BLOCK from a page, by vendor. Hand-built (the port law).

Hoola already has block-detection WITH escalation to the stealth fetcher (`scrape_tools._blocked`, the
Firecrawl-waterfall idea) - status codes, challenge titles, and a small-body fingerprint gate. So this is an
ENRICHMENT of a real feature, not a new one: it adds the vendor fingerprint catalogue and the empty-shell
check that `_blocked` has no notion of, and it keeps `_blocked`'s size gate, which is what stops a normal
article that merely mentions captcha from escalating.

Three tiers, the published shape:
  tier 1  structural markers - a token that appears on a challenge page and essentially nowhere else, so it
          fires at ANY page size.
  tier 2  generic wording - fires only on a SMALL page or an error status (an article about Cloudflare must
          not read as a Cloudflare block).
  tier 3  structural integrity - a 200 that is really an empty shell: no text, no links, a bare script.

Detection philosophy, kept from the source because it is the right trade here: a false positive costs one
wasted re-read, a false negative feeds her garbage as if it were a page.
"""
from __future__ import annotations

import re

SMALL_PAGE = 10_000        # tier 3 (empty shell) gate: bytes of HTML
# Tier 2 gates on VISIBLE TEXT, not HTML bytes, and that distinction is a bug fixed by measurement: a
# 5 KB article explaining how Cloudflare bot detection works sat under a 10 KB HTML gate and was flagged
# as a challenge on the words "bot detection". A challenge page carries a few hundred visible characters;
# a short article carries thousands. Visible text is the real discriminator.
SMALL_TEXT = 1_200         # tier 2 only below this many visible characters

# --- tier 1: vendor fingerprints. Each is a token that does not occur on a real page.
_TIER1: tuple[tuple[str, re.Pattern], ...] = (
    ("Cloudflare", re.compile(r"__cf_chl_f_tk=|cf-error-code|/cdn-cgi/challenge-platform/|cf_chl_opt|"
                              r"cdn-cgi/l/chk_jschl", re.I)),
    ("Akamai", re.compile(r"Reference\s*#\d{2}\.[0-9a-f]{8}|ak_bmsc|_abck=|akamai-bot-manager", re.I)),
    ("PerimeterX/HUMAN", re.compile(r"window\._pxAppId|captcha\.px-cdn\.net|_px(?:Captcha|Vid)\b|px-captcha", re.I)),
    ("DataDome", re.compile(r"captcha-delivery\.com|datadome|dd_cookie_test", re.I)),
    ("Imperva/Incapsula", re.compile(r"_Incapsula_Resource|incap_ses_|visid_incap_|iae\.incapsula", re.I)),
    ("Sucuri", re.compile(r"sucuri_cloudproxy|cloudproxy__js|Access Denied - Sucuri", re.I)),
    ("Kasada", re.compile(r"KPSDK\.scriptStart|kpsdk-ct|/149e9513-01fa-4fb0-aad4-566afd725d1b/", re.I)),
    ("AWS WAF", re.compile(r"awswaf|aws-waf-token|challenge\.js\?.*awswaf", re.I)),
    ("reCAPTCHA wall", re.compile(r"g-recaptcha.{0,400}(?:verify|not a robot)|recaptcha/api2/bframe", re.I | re.S)),
    ("hCaptcha wall", re.compile(r"hcaptcha\.com/1/api\.js|h-captcha-response", re.I)),
)
# --- tier 2: generic wording. Small pages / error statuses only.
_TIER2 = re.compile(
    r"checking your browser|just a moment|please wait while we|verify you are (?:a )?human|"
    r"are you a robot|enable javascript and cookies to continue|pardon our interruption|"
    r"unusual traffic from your|access denied|request blocked|bot detection|"
    r"your browser sent a request we could not|ddos protection by", re.I)
_TITLES = re.compile(r"just a moment|attention required|access denied|security check|are you human|"
                     r"bot verification|captcha|blocked|403 forbidden|too many requests", re.I)
_BLOCK_STATUS = {401, 403, 406, 409, 429, 503}
_TEXT = re.compile(r"<[^>]+>")
_TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def _visible_len(html: str) -> int:
    body = re.sub(r"(?is)<(script|style|noscript|template)[^>]*>.*?</\1>", " ", html or "")
    return len(re.sub(r"\s+", " ", _TEXT.sub(" ", body)).strip())


def why_blocked(html: str, status: int = 200, url: str = "") -> str | None:
    """A short reason, or None when the page looks real. Reason text is for HER card, so it names the vendor."""
    h = html or ""
    size = len(h)
    small = size < SMALL_PAGE
    err = int(status or 0) in _BLOCK_STATUS
    vis = _visible_len(h)

    # tier 1 - any size
    for vendor, pat in _TIER1:
        if pat.search(h):
            return f"{vendor} challenge"
    # a block status with an HTML body is a block, whatever it says
    if err and "<html" in h[:2000].lower():
        return f"HTTP {status}"
    if err:
        return f"HTTP {status}"
    # tier 2 - wording, gated on size/status so a real article about bots never escalates
    m = _TITLE_TAG.search(h)
    title = re.sub(r"\s+", " ", _TEXT.sub(" ", m.group(1))).strip() if m else ""
    if title and _TITLES.search(title):
        return f"challenge title ({title[:60]!r})"
    if vis < SMALL_TEXT or err:
        hit = _TIER2.search(h)
        if hit:
            return f"challenge wording ({hit.group(0)[:40]!r})"
    # tier 3 - structural integrity: a 200 that carries nothing
    if small:
        if vis < 200 and re.search(r"(?i)<script", h):
            links = len(re.findall(r"(?i)<a\s", h))
            if links <= 2:
                return f"empty shell ({vis} visible chars, {links} links, script-only)"
    return None


def is_blocked(html: str, status: int = 200, url: str = "") -> bool:
    return why_blocked(html, status, url) is not None
