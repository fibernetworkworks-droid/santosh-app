"""Copy of server/browser_worker/guard.py (the worker has its own venv), used by the Computer Operator too.

What Santosh's browser may do on its own, and what needs the user.

Pure functions (no browser-use import) so they are easy to test. The worker asks `classify_click`,
`classify_input` and `classify_keys` before every action; anything that is not plainly safe stops the run:

  payment   pay / checkout / place order / UPI / card ...  -> never done by Santosh; the user finishes on their phone
  secret    password, OTP, PIN, CVV, card number, Aadhaar   -> never typed by Santosh; the user does it themselves
  commit    submit / send / book / apply / delete / confirm -> needs the user's tap on a confirm card first
  ok        everything else (reading, searching, scrolling, filling ordinary fields, choosing options)
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

PAYMENT = re.compile(
    r"\b(pay|payment|pay now|paynow|proceed to pay|make payment|checkout|check out|place (?:your )?order|buy now|"
    r"purchase|upi|net ?banking|credit card|debit card|card details|wallet|recharge now|donate|add money|"
    r"complete (?:payment|purchase|order)|confirm (?:and|&) pay|pay securely)\b|भुगतान|पेमेंट|पैसे भेजें",
    re.I)
COMMIT = re.compile(
    r"\b(submit|send|apply|register|sign ?up|create (?:an )?account|book|reserve|confirm|delete|remove|"
    r"cancel (?:order|booking|subscription|ticket)|unsubscribe|subscribe|post|publish|share|transfer|"
    r"save changes|update (?:profile|details)|i agree|agree (?:and|&) continue|accept (?:and|&) continue|"
    r"final submit|lodge|file (?:complaint|return|grievance)|request (?:otp|callback)|get otp|send otp|"
    r"verify|claim|redeem|enrol|enroll|order now|add to (?:cart|bag) (?:and|&) checkout)\b|"
    r"जमा करें|सबमिट|भेजें|बुक करें|पुष्टि",
    re.I)
DANGER_LINK = re.compile(r"\b(delete|remove|cancel|unsubscribe|confirm|verify|approve|accept|deactivate|close account)\b", re.I)
SAFE_BUTTON = re.compile(
    r"^\s*(search|go|next|previous|prev|back|more|show more|load more|view|view details|details|show|filter|"
    r"apply filters?|sort|close|ok|got it|accept cookies|accept all|reject all|allow|continue reading|read more|"
    r"expand|collapse|menu|open|home|english|hindi|हिंदी|खोजें|आगे)\s*$",
    re.I)
SECRET_WORDS = re.compile(   # letters-only boundaries, so otp_code / user_pin / aadhaar_no all match
    r"pass(?:word|wd|code)?(?![a-z])|(?<![a-z])otp(?![a-z])|one.?time|(?<![a-z])(?:m|t)?pin(?![a-z])(?![\s_-]*code)|"
    r"(?<![a-z])cv[vc](?![a-z])|card.?(?:number|no)|cc-?num|(?<![a-z])aadh?aa?r|security.?code|secret|captcha", re.I)
SECRET_AUTOCOMPLETE = {"current-password", "new-password", "one-time-code", "cc-number", "cc-csc", "cc-exp",
                       "cc-exp-month", "cc-exp-year", "cc-name", "cc-type"}
SEARCH_FIELD = re.compile(r"search|query|\bq\b|find|khoj|keyword|lookup", re.I)

BLOCKED_HOSTS = {"web.whatsapp.com", "localhost", "metadata.google.internal", "metadata"}
BLOCKED_SUFFIXES = (".local", ".internal", ".localhost", ".lan", ".home.arpa")


def _label(node: dict) -> str:
    a = node.get("attributes") or {}
    parts = [node.get("text") or "", a.get("aria-label", ""), a.get("title", ""), a.get("value", ""),
             a.get("alt", ""), a.get("name", ""), a.get("id", "")]
    return " ".join(p for p in parts if p).strip()[:200]


def describe(node: dict) -> str:
    a = node.get("attributes") or {}
    text = (node.get("text") or a.get("aria-label") or a.get("value") or a.get("title") or a.get("placeholder")
            or a.get("name") or node.get("tag") or "element")
    return re.sub(r"\s+", " ", str(text)).strip()[:80]


def classify_click(node: dict | None) -> str:
    """payment | commit | ok for a click on this element."""
    if not node:
        return "ok"
    label = _label(node)
    a = node.get("attributes") or {}
    tag = (node.get("tag") or "").lower()
    if PAYMENT.search(label):
        return "payment"
    href = a.get("href", "").strip().lower()
    if tag == "a" and href and not href.startswith(("#", "javascript")):
        # plain links just open a page ("Book tickets" menu): only links that change something need a tap
        return "commit" if DANGER_LINK.search(label) else "ok"
    if COMMIT.search(label):
        return "commit"
    is_submit = (a.get("type", "").lower() == "submit") or (tag == "button" and a.get("type", "").lower() in ("", "submit")
                                                             and node.get("in_form"))
    if is_submit and not SAFE_BUTTON.match(describe(node)) and not SEARCH_FIELD.search(label):
        return "commit"   # a form's submit button with an unclear label: ask first
    return "ok"


def classify_input(node: dict | None, text: str = "") -> str:
    """secret | ok for typing into this element."""
    if not node:
        return "ok"
    a = node.get("attributes") or {}
    if a.get("type", "").lower() == "password":
        return "secret"
    if a.get("autocomplete", "").lower() in SECRET_AUTOCOMPLETE:
        return "secret"
    hay = " ".join(a.get(k, "") for k in ("name", "id", "placeholder", "aria-label", "title", "autocomplete", "class"))
    hay += " " + (node.get("text") or "") + " " + (node.get("label") or "")
    if SECRET_WORDS.search(hay):
        return "secret"
    digits = re.sub(r"[\s-]", "", text or "")
    if re.fullmatch(r"\d{12}|\d{13,19}", digits):   # looks like an Aadhaar or card number
        return "secret"
    return "ok"


def is_search_field(node: dict | None) -> bool:
    if not node:
        return False
    a = node.get("attributes") or {}
    if a.get("type", "").lower() == "search" or a.get("role", "").lower() in ("searchbox", "combobox"):
        return True
    hay = " ".join(a.get(k, "") for k in ("name", "id", "placeholder", "aria-label", "title", "class"))
    return bool(SEARCH_FIELD.search(hay))


def classify_keys(keys: str, last_input: dict | None) -> str:
    """Pressing Enter submits forms: fine in a search box, otherwise it needs a tap."""
    if re.search(r"enter|return", keys or "", re.I):
        return "ok" if is_search_field(last_input) else "commit"
    return "ok"


def url_problem(url: str, allow_private: bool = False) -> str:
    """Why Santosh's browser must not open this address ('' = fine). The network proxy re-checks every request."""
    u = (url or "").strip()
    if not u or u in ("about:blank",):
        return ""
    p = urlparse(u if "://" in u else "https://" + u)
    if p.scheme not in ("http", "https"):
        return f"{p.scheme or 'this'} links can't be opened"
    host = (p.hostname or "").lower().rstrip(".")
    if not host:
        return "no website in that link"
    if host in BLOCKED_HOSTS or host.endswith(BLOCKED_SUFFIXES):
        if host == "web.whatsapp.com":
            return "Santosh doesn't run WhatsApp Web (only the official WhatsApp Business API)"
        return "" if allow_private and host != "web.whatsapp.com" else "local or internal addresses are blocked"
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return ""
    return "" if ip.is_global or allow_private else "local or internal addresses are blocked"


INTERNAL_PAGES = ("about:", "chrome-error:", "data:", "blob:", "chrome://newtab", "chrome://new-tab-page",
                  "chrome-search://", "edge://newtab")


def page_problem(url: str, allow_private: bool = False) -> str:
    """For the page the browser is ON (not a link it is about to open): Chrome's own error page (a site that did not
    load), a new tab, data:/blob: pages are not a way out of the internet, so they are fine here. ('' = fine)"""
    u = (url or "").strip().lower()
    if not u or u.startswith(INTERNAL_PAGES):
        return ""
    return url_problem(url, allow_private)


def load_error(url: str) -> bool:
    """True when the browser shows Chrome's own 'site can't be reached' page."""
    return (url or "").lower().startswith("chrome-error:")
