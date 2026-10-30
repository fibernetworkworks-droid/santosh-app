"""v0.299 Website live features (web design Phase 3): things a static page could not do before.

Opus writes a placeholder, Hoola builds the real thing (so the model never invents an embed, a slot or a payment link):
- `<div data-hoola-booking></div>` -> a booking form that reads her REAL free slots from Hoola's booking book
  (net/booking.free_slots: her days, hours, slot length, jobs already held) through `/api/site-forms/<id>/slots`,
  minus slots another visitor already asked for; the visitor's request lands as a lead (kind booking) + a card to
  her; SHE confirms or declines it (nothing is promised to the visitor by itself).
- `<div data-hoola-map></div>` -> her address with a "Map dekhiye" button: the Google Map loads only on that tap
  (no third-party request, cookie or weight before the visitor asks), plus an open-in-Google-Maps link.
- `<div data-hoola-video="https://youtu.be/ID"></div>` -> a play button; the YouTube (no-cookie) player loads on tap.
- `<a data-hoola-pay="499" data-for="Kaju katli 1 kg">...</a>` -> pay by UPI to HER UPI ID (facts.upi, which she gives
  herself; the site is public only after her launch tap): a upi:// link on phones + a QR code for computers. Hoola
  never touches the money; without a UPI ID the button becomes "Order on WhatsApp".
"""
from __future__ import annotations

import base64
import html as _html
import re
from typing import Any
from urllib.parse import quote

VPA = re.compile(r"^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z][a-zA-Z0-9]{1,63}$")
YT = re.compile(r"(?:youtu\.be/|youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/))([\w-]{11})")
FRAME_SRC = "https://www.google.com https://www.youtube-nocookie.com"
WORDS = {
    "en": {"map": "Show map", "maps": "Open in Google Maps", "play": "Play video", "slots": "Pick a time",
           "loading": "Checking free times…", "none": "No free time online right now. Please call or WhatsApp us.",
           "name": "Your name", "phone": "Mobile number", "note": "Anything we should know? (optional)",
           "book": "Request this time", "ok": "Request sent! We will confirm on your phone.",
           "fail": "Could not send. Please call or WhatsApp us.", "consent": "We use your number only to confirm this booking.",
           "pay": "Pay with UPI", "scan": "Scan with any UPI app", "order": "Order on WhatsApp"},
    "hi": {"map": "नक्शा देखिए", "maps": "Google Maps में खोलिए", "play": "वीडियो चलाइए", "slots": "समय चुनिए",
           "loading": "खाली समय देख रहे हैं…", "none": "अभी ऑनलाइन खाली समय नहीं है। कृपया कॉल या WhatsApp कीजिए।",
           "name": "आपका नाम", "phone": "मोबाइल नंबर", "note": "कुछ बताना हो तो (ज़रूरी नहीं)", "book": "यह समय माँगिए",
           "ok": "अनुरोध भेज दिया! हम फ़ोन पर पक्का करेंगे।", "fail": "भेज नहीं पाए। कृपया कॉल या WhatsApp कीजिए।",
           "consent": "आपका नंबर सिर्फ़ इस बुकिंग को पक्का करने के लिए है।", "pay": "UPI से भुगतान", "scan": "किसी भी UPI ऐप से स्कैन कीजिए",
           "order": "WhatsApp पर ऑर्डर"},
}
WORDS["mr"] = {**WORDS["hi"], "map": "नकाशा पहा", "play": "व्हिडिओ चालवा", "slots": "वेळ निवडा", "book": "ही वेळ मागा"}
WORDS["hinglish"] = {**WORDS["en"], "map": "Map dekhiye", "maps": "Google Maps mein kholiye", "play": "Video chalaiye",
                     "slots": "Samay chuniye", "loading": "Khaali samay dekh rahe hain…", "book": "Yeh samay maangiye",
                     "ok": "Request bhej di! Hum phone par pakka karenge.", "name": "Aapka naam", "phone": "Mobile number",
                     "pay": "UPI se pay kijiye", "scan": "Kisi bhi UPI app se scan kijiye", "order": "WhatsApp par order"}


def esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s), quote=True)


def words(lang: str) -> dict[str, str]:
    return WORDS.get(lang or "en", WORDS["en"])


def youtube_id(v: str) -> str:
    v = (v or "").strip()
    if re.fullmatch(r"[\w-]{11}", v):
        return v
    m = YT.search(v)
    return m.group(1) if m else ""


def vpa_ok(v: str) -> bool:
    return bool(VPA.match((v or "").strip()))


def upi_link(vpa: str, name: str, amount: str = "", note: str = "") -> str:
    q = f"pa={quote(vpa)}&pn={quote(name[:50] or 'Shop')}&cu=INR"
    if amount:
        q += f"&am={amount}"
    if note:
        q += f"&tn={quote(note[:60])}"
    return "upi://pay?" + q


def qr_data_uri(text: str) -> str:
    """A small SVG QR code as a data: URL (allowed by the site's img-src; no request to anyone)."""
    import io

    import segno
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="svg", scale=4, border=2, dark="#111111", light="#ffffff", xmldecl=False)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()


def _amount(v: str) -> str:
    m = re.fullmatch(r"\s*(\d{1,7})(?:\.(\d{1,2}))?\s*", v or "")
    if not m:
        return ""
    return m.group(1) + (f".{m.group(2)}" if m.group(2) else "")


def _attr(tag: str, name: str) -> str:
    m = re.search(rf'{name}=["\']([^"\']*)["\']', tag)
    return _html.unescape(m.group(1)) if m else ""


def expand(html: str, site: dict[str, Any], endpoint: str, icon) -> tuple[str, list[str]]:
    """The placeholders of one section -> the real things. Returns (html, problems)."""
    f = site.get("facts") or {}
    w = words(site.get("language") or "en")
    problems: list[str] = []

    def mapit(m: re.Match) -> str:
        addr = " ".join(x for x in (f.get("name"), f.get("address"), f.get("city")) if x).strip()
        if not f.get("address"):
            problems.append("map: no address in her facts")
            return '<p class="muted"><em class="blank">[address]</em></p>'
        q = quote(addr[:200])
        return (f'<figure class="hs-map" data-hs-map="https://www.google.com/maps?q={q}&amp;output=embed">'
                f'<div class="hs-map-face">{icon("map-pin")}<p>{esc(f.get("address"))}</p><div class="btns">'
                f'<button type="button" class="btn btn-primary hs-load">{esc(w["map"])}</button>'
                f'<a class="btn btn-ghost" href="https://maps.google.com/?q={q}" target="_blank" rel="noopener">{esc(w["maps"])}</a>'
                f'</div></div></figure>')

    def video(m: re.Match) -> str:
        tag = m.group(1)
        vid = youtube_id(_attr(tag, "data-hoola-video"))
        if not vid:
            problems.append("video: not a YouTube link")
            return '<p class="muted"><em class="blank">[YouTube video link]</em></p>'
        title = _attr(tag, "data-title") or w["play"]
        return (f'<figure class="hs-video" data-hs-yt="{vid}" data-title="{esc(title)}">'
                f'<button type="button" class="hs-load hs-play" aria-label="{esc(w["play"])}: {esc(title)}">'
                f'{icon("play")}<span>{esc(title)}</span></button></figure>')

    def booking(m: re.Match) -> str:
        return (f'<form class="hs-form hs-book" data-hoola-book data-endpoint="{esc(endpoint)}" data-none="{esc(w["none"])}" '
                f'data-ok="{esc(w["ok"])}" data-fail="{esc(w["fail"])}">'
                f'<fieldset class="hs-slots-wrap"><legend>{esc(w["slots"])}</legend>'
                f'<div class="hs-slots" role="radiogroup"><p class="muted">{esc(w["loading"])}</p></div></fieldset>'
                f'<label>{esc(w["name"])} <input name="name" autocomplete="name" required></label>'
                f'<label>{esc(w["phone"])} <input name="phone" type="tel" inputmode="numeric" autocomplete="tel" required></label>'
                f'<label>{esc(w["note"])} <textarea name="message" rows="2"></textarea></label>'
                f'<input class="hp" name="website" tabindex="-1" autocomplete="off">'
                f'<p class="hs-consent">{esc(w["consent"])}</p>'
                f'<button type="submit" class="btn btn-primary">{esc(w["book"])}</button>'
                f'<p class="hs-form-msg" role="status"></p></form>')

    def pay(m: re.Match) -> str:
        tag, inner = m.group(1), m.group(2)
        amt = _amount(_attr(tag, "data-hoola-pay"))
        what = _attr(tag, "data-for")
        cls = _attr(tag, "class") or "btn btn-primary"
        vpa = f.get("upi") or ""
        if not vpa_ok(vpa):
            from .build import wa_link
            link = wa_link(f, f"{what} order karna hai" if what else "")
            if not link:
                return f'<span class="{esc(cls)}" aria-disabled="true">{inner}</span>'
            return f'<a class="{esc(cls)}" href="{esc(link)}" target="_blank" rel="noopener">{esc(w["order"])}</a>'
        link = upi_link(vpa, f.get("name") or "", amt, what)
        label = f"₹{amt}" if amt else ""
        return (f'<span class="hs-pay"><a class="{esc(cls)}" href="{esc(link)}">{inner}</a>'
                f'<img class="hs-qr" src="{qr_data_uri(link)}" alt="{esc(w["scan"])} {esc(label)}" width="132" height="132">'
                f'<small>{esc(w["scan"])}</small></span>')

    html = re.sub(r"<div\b[^>]*data-hoola-map\b[^>]*>\s*</div>", mapit, html)
    html = re.sub(r"(<div\b[^>]*data-hoola-video=[^>]*>)\s*</div>", video, html)
    html = re.sub(r"<div\b[^>]*data-hoola-booking\b[^>]*>\s*</div>", booking, html)
    html = re.sub(r"(<a\b[^>]*data-hoola-pay=[^>]*>)(.*?)</a>", pay, html, flags=re.S)
    return html, problems


# ---------------------------------------------------------------- the public booking endpoints (her real slots)
def slots(site_id: str, n: int = 12) -> list[dict[str, str]]:
    from sqlalchemy import select

    from ..db import session
    from ..net import booking as BK
    from .models import Site, SiteLead
    with session() as s:
        r = s.get(Site, site_id)
        if r is None:
            return []
        tenant = r.tenant_id
        held = {x.slot for x in s.scalars(select(SiteLead).where(SiteLead.site_id == site_id, SiteLead.kind == "booking",
                                                                  SiteLead.status.in_(("new", "confirmed")))).all() if x.slot}
    out = []
    for iso in BK.free_slots(tenant, n + len(held)):
        if iso in held:
            continue
        out.append({"slot": iso, "label": BK.say_slot(tenant, iso)})
        if len(out) >= n:
            break
    return out


def slot_ok(site_id: str, slot: str) -> bool:
    return any(x["slot"] == slot for x in slots(site_id, 40))
