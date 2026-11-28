"""v0.999.330 UX RULES WHERE WEBSITES AND APPS ARE BUILT - the design database's UX rules, read by code.

The UI/UX Pro Max database (coder/uiux/data/ux-guidelines.csv, upstream 11ca2b3, MIT) holds 141 UX rules. Until now only
the chat's `uiux_design` tool could read them; nothing that BUILDS a website or an app did. This module gives the
builders the rules that fit what they are building, with no model call and no subprocess:

- `topics_of(text)` - what a section / file holds (forms, maps, dialogs), read from its words and its code;
- `block(topics)` - the short rule list for those topics, for a writer's or a critic's prompt;
- `prompt_for(text)` - the two together, empty when nothing fits (most sections hold no form or map);
- `code_problems(code)` - a few rules a computer can check in code (paste blocked, the submit button disabled until
  the form is valid, fields with no label, an email box that is not type=email, a map with its attribution or keyboard
  switched off, a map popup drawn from raw HTML, a map with no text for people who cannot see it). A problem found by
  code is a fact, not a guess: the critic loop sends it back to the writer as a rewrite note.

v0.999.334 beside them: Ant Design's business-screen, number and wording rules (coder/bizrules.py) - results, errors
and empty states; search-and-filter lists; record pages; dashboards; settings; long forms; numbers, money and dates in
the business's own country; buttons and words - with their own code checks (a typed currency sign, toFixed on money, a
fixed 'en-US' / 'en-IN', a date built from getMonth() + 1, 'Submit' / 'Click here' buttons, '!' on a button).

The rules are recommendations; the house checks (tokens, AutoFix, the build, the critic's scores) still decide.
"""
from __future__ import annotations

import csv
import functools
import os
import re
from typing import Any

from . import bizrules as BR

DATA = os.path.join(os.path.dirname(__file__), "uiux", "data", "ux-guidelines.csv")
CHARS = 1600                        # a prompt block never grows past this (a little more when it holds many topics)
CHARS_MAX = 2600

# what a section holds, read from its words or its code (lower case)
SIGNALS = {
    "forms": re.compile(r"<form\b|<input\b|<textarea\b|<select\b|onsubmit|screen[-_]form|screen[-_]signin|"
                        r"contact[-_]block|booking[-_]slots|\brsvp\b|\b(form|enquir\w*|inquir\w*|booking|book a|"
                        r"appointment|sign ?up|log ?in|login|register|newsletter|subscribe|checkout|get a quote|"
                        r"feedback form|apply now)\b"),
    "maps": re.compile(r"maplibre|leaflet|mapbox|google\.com/maps|maps\.google|map[-_]hours|coverage[-_]areas|"
                       r"(?<![.\w])maps?\b(?!\s*[(<])|\b(store locator|find us|directions to)\b"),
    "dialogs": re.compile(r"<dialog\b|alertdialog|<Dialog\b|(?<![.\w])dialog\b(?!\s*[(<])|\bmodal\b"),
    # v0.999.334 Ant Design's business screens
    "states": re.compile(r"screen[-_][a-z]+|\bresult page\b|\b(404|403|500) page|page not found|empty state|<Result\b|"
                         r"<Empty\b|usequery|hoola\.db|\bcheckout\b|\bpayment\b|order placed|thank you|\bportal\b"),
    "tables": re.compile(r"screen[-_](table|approvals)|datatable|data-table|<table\b|<thead\b|query table|"
                         r"\blist of (orders|students|customers|patients|bookings|invoices|leads|members|staff|products)\b"),
    "detail": re.compile(r"screen[-_]detail|record detail|\bdetail page\b|\bprofile page\b"),
    "dashboard": re.compile(r"screen[-_]dashboard|\bdashboard\b|\bkpis?\b|stats[-_]counters"),
    "settings": re.compile(r"screen[-_]settings|\bsettings\b|\bpreferences\b"),
    "long_forms": re.compile(r"screen[-_]form|multi-?step|step form|\bwizard\b|<steps\b|application form|\badmission\b"),
    "numbers": re.compile(r"[₹€£¥]|\$\d|\bprice|\bamount|\btotal\b|\binvoice|\bfees?\b|\bsalary|\brevenue|\bbalance\b|"
                          r"\bpercent|tofixed|tolocale|intl\.|\bdates?\b|\bschedule\b|\bcalendar\b|\bbooking|"
                          r"\bappointment|\bkpis?\b|stats[-_]counters|pricing[-_]table|\bmoney\(|\bnum\("),
    "words": re.compile(r"screen[-_][a-z]+|<form\b|onsubmit|contact[-_]block|booking[-_]slots|\brsvp\b|<dialog\b|"
                        r"\bcheckout\b"),
}
DATA_MAP = re.compile(r"choropleth|heat ?map|geojson|by region|per district|per state|density map")

# the rules each topic carries (Issue names in the database; a name the data no longer has is simply left out)
TOPICS: dict[str, dict[str, Any]] = {
    "forms": {"issues": ("Input Labels", "Error Placement", "Actionable Error Messages",
                         "Preserve Input After Failed Submit", "Clear Errors After Correction", "Submit Feedback",
                         "Submit Button Not Pre-Disabled", "Never Block Paste", "Input Types",
                         "Forgiving Input Formats", "Error Messages", "Unsaved Changes Warning",
                         "Premature Validation", "Autofill Support", "Mobile Keyboards")},
    "maps": {"issues": ("Map Attribution Visible", "Map Text Alternative", "Map Keyboard and Non-Drag Navigation",
                        "Map Symbology Not Color Alone", "Safe Map Popup Content", "Cluster Dense Map Points",
                        "Map Camera Reduced Motion")},
    "data_maps": {"issues": ("Normalized Choropleth Map", "Perceptual Map Color Ramps",
                             "Large Geodata as Vector Tiles")},
    "dialogs": {"issues": ("Modal Dialog Focus", "Confirmation Dialogs")},
    # v0.999.334 Hoola's own rows read from Ant Design's specs (coder/bizrules.py), in their order of weight
    **{k: {"own": True} for k in BR.RULES},
}


@functools.lru_cache(maxsize=1)
def rows() -> tuple[dict[str, str], ...]:
    try:
        with open(DATA, encoding="utf-8", newline="") as f:
            return tuple(csv.DictReader(f))
    except OSError:
        return ()


def topics_of(text: str) -> list[str]:
    t = (text or "").lower()
    t2 = t.replace("_", " ")                         # "custom_enquiry" reads as "custom enquiry" too
    out = [k for k, rx in SIGNALS.items() if rx.search(t) or rx.search(t2)]
    if "maps" in out and DATA_MAP.search(t):
        out.append("data_maps")
    return out


def rules(topic: str, platform: str = "web") -> list[dict[str, str]]:
    """The topic's rules in the order that matters most for it (a name the data no longer has is left out)."""
    if (TOPICS.get(topic) or {}).get("own"):
        return BR.rules(topic)
    order = list((TOPICS.get(topic) or {}).get("issues") or ())
    plats = {"All", "Web"} if platform == "web" else {"All", "Mobile"}
    by = {r.get("Issue"): r for r in rows() if (r.get("Platform") or "All") in plats}
    return [by[i] for i in order if i in by]


def _line(r: dict[str, str]) -> str:
    do, dont = (r.get("Do") or "").strip().rstrip("."), (r.get("Don't") or "").strip().rstrip(".")
    s = f"- {r.get('Issue')}: {do}" + (f" (not: {dont})" if dont else "") + "."
    if len(s) > 170:                                 # the don't goes first, then the do is cut at a word
        s = f"- {r.get('Issue')}: {do}."
    return s if len(s) <= 170 else s[:166].rsplit(" ", 1)[0] + "..."


def block(topics: list[str], platform: str = "web", limit: int = CHARS, head: str = "") -> str:
    """Each topic gets an even share of `limit`, so a form never pushes the map rules out."""
    topics = [t for t in topics if t in TOPICS]
    head = head or "UX RULES for what this holds (Hoola's design rules - follow them):"
    if not topics:
        return ""
    if limit == CHARS and len(topics) > 4:
        limit = min(CHARS_MAX, CHARS + 220 * (len(topics) - 4))
    share = max(200, (limit - len(head)) // len(topics))
    body, seen = [], set()
    for t in topics:
        used = 0
        for r in rules(t, platform):
            ln = _line(r)
            if r.get("Issue") in seen or used + len(ln) + 1 > share:
                continue
            seen.add(r.get("Issue"))
            body.append(ln)
            used += len(ln) + 1
    return (head + "\n" + "\n".join(body)) if body else ""


def prompt_for(text: str, platform: str = "web", limit: int = CHARS) -> str:
    b = block(topics_of(text), platform, limit)
    return ("\n\n" + b) if b else ""


# ---------------------------------------------------------------- the rules a computer can check in code
_TAG = re.compile(r"<(button|Button|input|Input|textarea|Textarea|select|Select)\b((?:=>|[^>])*)>", re.S)
_FIELD = re.compile(r"<(input|Input|textarea|Textarea|select|Select)\b(?![^>]*type=[\"'](?:hidden|submit|button|checkbox|radio)[\"'])")
_LABEL = re.compile(r"<label\b|<Label\b|aria-label=|aria-labelledby=|htmlFor=|\bfor=")
_BUSY = re.compile(r"submitting|sending|loading|pending|busy|saving|inflight|in_flight|isSubmitting", re.I)
_MAP = re.compile(r"maplibregl|maplibre-gl|leaflet|mapboxgl|<Map\b|google\.com/maps|maps\.google|L\.map\(")


def code_problems(code: str) -> list[str]:
    """Rules broken in this file, each named after its rule. Only what code can see for sure; nothing else."""
    c = code or ""
    out: list[str] = []
    if re.search(r"onPaste=\{[^}]*preventDefault|onpaste=[\"'][^\"']*(preventDefault|return false)", c):
        out.append("Never Block Paste: a field stops paste - let people paste into every field")
    for m in _TAG.finditer(c):
        tag, attrs = m.group(1).lower(), m.group(2)
        if tag == "button" and re.search(r"type=[\"']submit[\"']", attrs):
            d = re.search(r"disabled=\{\s*!([^}]*)\}", attrs)
            if d and not _BUSY.search(d.group(1)):
                out.append("Submit Button Not Pre-Disabled: the send button stays disabled until the form is valid - "
                           "keep it enabled and show what to fix when it is pressed (disable it only while sending)")
                break
    fields = [m for m in _FIELD.finditer(c)]
    if fields and not _LABEL.search(c):
        out.append("Input Labels: the fields have no label (a placeholder is not a label) - give each a visible label")
    for m in _TAG.finditer(c):
        tag, attrs = m.group(1).lower(), m.group(2)
        if tag != "input":
            continue
        named = " ".join(re.findall(r"(?:name|id|placeholder)=[\"']([^\"']*)[\"']", attrs)).lower()
        if re.search(r"e-?mail", named) and not re.search(r"type=[\"']email[\"']", attrs):
            out.append("Input Types: the email field is not type=\"email\" - phones then show the email keyboard")
            break
        if re.search(r"\b(phone|mobile|tel|whatsapp)\b", named) and not re.search(r"type=[\"']tel[\"']", attrs):
            out.append("Input Types: the phone field is not type=\"tel\" - phones then show the number keypad")
            break
    out += _biz_problems(c)
    if _MAP.search(c):
        if re.search(r"attributionControl\s*[:=]\s*\{?\s*false", c):
            out.append("Map Attribution Visible: the map's attribution is switched off - keep it visible (the map's "
                       "data licence asks for it)")
        if re.search(r"\bkeyboard\s*[:=]\s*\{?\s*false", c):
            out.append("Map Keyboard and Non-Drag Navigation: the map's keyboard control is off - keep arrow keys "
                       "and +/- working")
        if re.search(r"\.setHTML\(", c):
            out.append("Safe Map Popup Content: a map popup is drawn from HTML - use setText or setDOMContent")
        if not re.search(r"aria-label=|aria-labelledby=|role=[\"']region[\"']|title=", c):
            out.append("Map Text Alternative: the map has no label or text for people who cannot see it - label it "
                       "and give a short list of the places beside it")
    return out


# ---------------------------------------------------------------- v0.999.334 Ant Design's number and wording rules in code
_SIGN = "[₹€£¥]"
_MONEY_SIGN = re.compile(rf"(?<![\w\\]){_SIGN}\s*\{{(?!\s*[\"'`])|[\"'`]{_SIGN}[\"'`]\s*\+|`{_SIGN}\$\{{|"
                         rf"\+\s*[\"'`]\s?{_SIGN}[\"'`]|\bRs\.?\s*\{{(?!\s*[\"'`])")
_MONEY_FIXED = re.compile(r"\b\w*(price|amount|total|cost|fee|balance|mrp|tax|due|paid|salary)\w*\)?\.toFixed\(", re.I)
_FIXED_LOCALE = re.compile(r"toLocale(?:String|DateString|TimeString)\(\s*[\"'][a-z]{2}-[A-Z]{2}[\"']|"
                           r"Intl\.NumberFormat\(\s*[\"'][a-z]{2}-[A-Z]{2}[\"']")
_HAND_DATE = re.compile(r"getMonth\(\)\s*\+\s*1")
_BTN = re.compile(r"<(button|Button)\b(?:=>|[^>])*>\s*([^<{]*?)\s*</(?:button|Button)>")
_VAGUE = re.compile(r"^(submit|ok|okay|click|click here|go|yes)$", re.I)
_CLICK_HERE = re.compile(r">\s*click here\s*<", re.I)


def _biz_problems(c: str) -> list[str]:
    out: list[str] = []
    if _MONEY_SIGN.search(c):
        out.append("Currency the Country's Way: an amount is written with a typed currency sign - use money(n) from "
                   "@/lib/format (or the site's own price format) so it shows the business's currency its country's way")
    if _MONEY_FIXED.search(c):
        out.append("Currency the Country's Way: money is rounded with toFixed - use money(n) from @/lib/format, which "
                   "groups the digits and places the currency the country's way")
    if _FIXED_LOCALE.search(c):
        out.append("Digits in Groups: a number is fixed to one country's format ('en-US' / 'en-IN') - use num() / "
                   "money() from @/lib/format so it follows the app's own country")
    if _HAND_DATE.search(c):
        out.append("Dates in Their Order: a date is built by hand from getMonth() + 1 - use date() / range() from "
                   "@/lib/format (Intl) so it reads in the country's own order")
    vague = bang = False
    for m in _BTN.finditer(c):
        text = m.group(2).strip()
        if text and _VAGUE.match(text):
            vague = True
        if text.endswith("!"):
            bang = True
    if vague or _CLICK_HERE.search(c):
        out.append("Button Says the Action: a button or link says 'Submit' / 'OK' / 'Click here' - name the action "
                   "('Send enquiry', 'Book the visit', 'See the menu')")
    if bang:
        out.append("Calm Tone: a button ends with '!' - say the action calmly")
    return out
