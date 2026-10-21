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
    r"expand|collapse|menu|open|home|english|hindi|हिंदी|खोजें|आगे|"
    # v0.80 Order karo: putting things in the cart moves no money and can be undone (pay / place order stay hers)
    r"add|add to cart|add to bag|add to basket|add item|add to trolley|\+|update cart|"
    r"increase quantity|decrease quantity|deliver here|deliver to this address|use this address|select address)\s*$",
    re.I)
SECRET_WORDS = re.compile(   # letters-only boundaries, so otp_code / user_pin / aadhaar_no all match
    r"pass(?:word|wd|code)?(?![a-z])|(?<![a-z])otp(?![a-z])|one.?time|(?<![a-z])(?:m|t)?pin(?![a-z])(?![\s_-]*code)|"
    r"(?<![a-z])cv[vc](?![a-z])|card.?(?:number|no)|cc-?num|security.?code|secret|captcha", re.I)
# v0.75 identity numbers (filled from the owner's Pehchaan Locker, never typed from the model's own words)
ID_WORDS = re.compile(
    r"(?<![a-z])aadh?aa?r|(?<![a-z])pan(?![a-z])|pan.?(?:no|number|card)|permanent.?account|"
    r"voter|(?<![a-z])epic(?![a-z])|passport.?(?:no|number)|driving.?licen|(?<![a-z])dl.?(?:no|number)|ration.?card|"
    r"(?<![a-z])abha|(?<![a-z])uan(?![a-z])|gstin|आधार|पैन", re.I)
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


ID_PHRASE = re.compile(r"(?:" + ID_WORDS.pattern + r")[\s_.-]*(?:card)?[\s_.-]*(?:number|num|no\.?)?", re.I)


def _no_id(text: str) -> str:
    """'PAN card number' / 'aadhaar_card_no' -> IDNUM, so 'card number' inside an ID name is not a bank card."""
    return ID_PHRASE.sub(" IDNUM ", text or "")


def _id_first(label: str) -> bool:
    """The label names an ID number first ("Aadhaar Number (OTP will be sent)"), not an OTP ("Enter Aadhaar OTP")."""
    label = _no_id(label)
    i, k = re.search(r"IDNUM", label), SECRET_WORDS.search(label)
    if not i:
        return False
    if not k:
        return True
    return i.start() < k.start() and bool(re.search(r"\w{2,}|[(\[:,-]", label[i.end():k.start()]))


def classify_input(node: dict | None, text: str = "") -> str:
    """secret | id | ok for typing into this element. secret = password / OTP / PIN / CVV / card: only the owner types
    it. id = an identity number box (Aadhaar, PAN...): filled from her locker, never from the model's own words."""
    if not node:
        return "ok"
    a = node.get("attributes") or {}
    if a.get("autocomplete", "").lower() in SECRET_AUTOCOMPLETE:
        return "secret"
    own = " ".join(a.get(k, "") for k in ("name", "id", "placeholder"))
    said = " ".join(x for x in (a.get("aria-label", ""), a.get("title", ""), node.get("text") or "", node.get("label") or "") if x)
    hay = own + " " + a.get("autocomplete", "") + " " + a.get("class", "") + " " + said
    # v0.76 an identity box wins over words around it ("Aadhaar Number (OTP will be sent to your mobile)") and over
    # type=password (many portals hide the Aadhaar they ask for). A box whose own name says OTP / password, or whose
    # label is "Aadhaar OTP" / "Enter OTP ... Aadhaar", stays secret.
    if ID_WORDS.search(hay) and not SECRET_WORDS.search(_no_id(own)) and _id_first(said or own):
        return "id"
    if a.get("type", "").lower() == "password":
        return "secret"
    if SECRET_WORDS.search(hay):
        return "secret"
    digits = re.sub(r"[\s-]", "", text or "")
    if re.fullmatch(r"\d{13,19}", digits):          # looks like a card number
        return "secret"
    if ID_WORDS.search(hay) or re.fullmatch(r"\d{12}", digits) or re.fullmatch(r"[A-Za-z]{5}\d{4}[A-Za-z]", (text or "").strip()):
        return "id"
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
