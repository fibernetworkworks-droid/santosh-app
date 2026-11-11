"""Starter recipes: a brief with blanks. These are Hoola's STARTERS - the page says so; nothing here claims a kept
rate (that needs the outcome ledger, plan P4). Web starters are the Web Studio's own 1,00,000 website templates."""
from __future__ import annotations

import re
from typing import Any

from . import anatomy as A
from . import brief as B

B_NAME = {"key": "business", "label": "Business name", "eg": "Shree Balaji Sweets"}
B_CITY = {"key": "city", "label": "City", "eg": "Akola"}
B_OFFER = {"key": "offer", "label": "The offer, exactly", "eg": "Flat 30% Off"}
B_PRODUCT = {"key": "product", "label": "Product or service", "eg": "kaju katli"}
B_PRICE = {"key": "price", "label": "Price, exactly", "eg": "Rs 499"}
B_FEST = {"key": "festival", "label": "Festival", "eg": "Diwali"}
B_AUD = {"key": "audience", "label": "Who it is for", "eg": "families in Akola"}

_IMAGE = [
    ("img-festival-offer", "Festival offer poster", "a festive poster with your offer in large words",
     "{festival} offer poster for {business}", [B_FEST, B_NAME, B_OFFER],
     {"subject": "one clear {festival} symbol with a few flowers beside it", "scene": "on a dark, uncluttered surface",
      "style": "Festive poster", "words": "{festival} Sale - {offer}", "size": "4:5",
      "composition": "the symbol in the lower third, clear empty space in the upper half for the words",
      "light": "warm glow, dark background"}),
    ("img-product-photo", "Product photo", "a clean close-up photo of one product",
     "product photo of {product} for {business}", [B_PRODUCT, B_NAME],
     {"subject": "{product}, shown at its best", "scene": "on a clean counter or table", "style": "Product photo", "size": "1:1",
      "composition": "close-up from a 45 degree angle, the product fills most of the frame, soft blurred background",
      "light": "soft daylight from a window on one side"}),
    ("img-festival-wish", "Festival greeting", "a greeting picture with your shop's wishes",
     "{festival} greeting from {business}", [B_FEST, B_NAME],
     {"subject": "a simple, respectful {festival} scene", "style": "Flat illustration", "words": "Happy {festival} - {business}",
      "size": "1:1", "composition": "the scene in the centre, room at the top for the words", "light": "even bright light"}),
    ("img-price-offer", "Price offer post", "a square post with one product and its price",
     "offer post: {product} at {price}", [B_PRODUCT, B_PRICE, B_NAME],
     {"subject": "{product}", "scene": "on a plain coloured background", "style": "Product photo",
      "words": "{product} - {price}", "size": "1:1", "composition": "the product on the left two thirds, the words on the right"}),
    ("img-admission", "Admissions open poster", "a poster for school, coaching or class admissions",
     "admissions open poster for {business}", [B_NAME, {"key": "year", "label": "Session", "eg": "2027-28"}],
     {"subject": "three smiling students with bags", "scene": "in front of the institute's gate", "style": "Real photograph",
      "words": "Admissions Open {year}", "size": "4:5",
      "composition": "students on the left half, a plain coloured panel on the right for the words", "light": "morning sunlight"}),
    ("img-hiring", "We are hiring post", "a simple hiring post",
     "hiring post for {business}", [B_NAME, {"key": "role", "label": "Role", "eg": "Sales Executive"}],
     {"subject": "a tidy desk with a laptop, a mug and a small plant", "style": "Flat illustration",
      "words": "We Are Hiring - {role}", "size": "1:1", "composition": "desk in the lower half, plain wall above for the words"}),
    ("img-banner", "Website / shop banner", "a wide banner for a website header or shop board",
     "wide banner for {business}", [B_NAME, B_PRODUCT],
     {"subject": "{product}", "scene": "inside the shop, softly blurred behind", "style": "Real photograph", "size": "16:9",
      "words": "{business}", "composition": "the product on the right third, soft empty space on the left for the words"}),
    ("img-logo", "Simple logo idea", "a simple two-colour logo to start from",
     "logo for {business}", [B_NAME, {"key": "symbol", "label": "One symbol", "eg": "a clay cup of chai"}],
     {"subject": "{symbol}", "scene": "on a plain background", "style": "Simple logo", "words": "{business}", "size": "1:1",
      "composition": "the symbol in the centre, nothing else around it", "colours": "two colours only"}),
    ("img-thumbnail", "Video thumbnail", "a punchy wide thumbnail with big words",
     "thumbnail for my video about {product}", [B_PRODUCT, {"key": "title", "label": "3-4 words on it", "eg": "10 Minute Paneer"}],
     {"subject": "{product}, in a tight close-up", "style": "Real photograph", "words": "{title}", "size": "16:9",
      "composition": "the subject fills the left two thirds, big bold words on the right", "light": "strong warm light"}),
    ("img-story", "Story announcement", "a vertical story for WhatsApp or Instagram",
     "story announcing {offer} at {business}", [B_OFFER, B_NAME],
     {"subject": "the shop front or the main product", "style": "Festive poster", "words": "{offer}", "size": "9:16",
      "composition": "the subject in the middle third, words in the top third, the bottom third left clear"}),
]
_SCRIPT = [
    ("scr-festival-reel", "Festival offer reel", "a 30-second reel for a festival offer",
     "{festival} reel script for {business}", [B_FEST, B_NAME, B_OFFER, B_AUD],
     {"platform": "Instagram reel", "length": "30 seconds", "audience": "{audience}",
      "message": "{business} is where the family's {festival} shopping starts", "hook": "a small, real family moment just before {festival}",
      "cta": "Message on WhatsApp", "tone": "Warm"}, "Offer: {offer}"),
    ("scr-shop-intro", "Shop introduction", "a short video that introduces your shop",
     "introduction video script for {business} in {city}", [B_NAME, B_CITY, B_PRODUCT],
     {"platform": "Instagram reel", "length": "30 seconds", "audience": "people in {city} who have not visited yet",
      "message": "what makes {business} worth one visit for {product}", "hook": "the shutter going up in the morning",
      "cta": "Visit the shop", "tone": "Warm"}, ""),
    ("scr-product-launch", "New product launch", "a reel announcing something new",
     "launch reel for {product} at {business}", [B_PRODUCT, B_NAME, B_PRICE],
     {"platform": "Instagram reel", "length": "20 seconds", "audience": "our regular customers",
      "message": "{product} is here and it is worth trying this week", "hook": "hands unboxing {product} for the first time",
      "cta": "Message on WhatsApp", "tone": "Energetic"}, "Price: {price}"),
    ("scr-customer-story", "Customer story", "a short, honest customer moment",
     "customer story video for {business}", [B_NAME, B_AUD],
     {"platform": "Instagram reel", "length": "45 seconds", "audience": "{audience}",
      "message": "the small problem {business} quietly solves", "hook": "the customer's problem, shown without words",
      "cta": "Message on WhatsApp", "tone": "Emotional"}, ""),
    ("scr-whatsapp-status", "WhatsApp status video", "a 15-second status for today's offer",
     "whatsapp status video for today's offer at {business}", [B_NAME, B_OFFER],
     {"platform": "WhatsApp status video", "length": "15 seconds", "audience": "people who already have our number",
      "message": "today's offer, said once and clearly", "cta": "Message on WhatsApp", "tone": "Funny"}, "Offer: {offer}"),
    ("scr-explainer", "How it works explainer", "a one-minute explainer of your service",
     "explainer video script: how {product} from {business} works", [B_PRODUCT, B_NAME, B_AUD],
     {"platform": "YouTube video", "length": "60 seconds", "audience": "{audience}",
      "message": "{product} in three plain steps", "hook": "the everyday trouble before {product}",
      "cta": "Call now", "tone": "Straight and honest"}, ""),
    ("scr-hiring", "Hiring video", "a short video to attract the right applicants",
     "hiring video script for {business}", [B_NAME, {"key": "role", "label": "Role", "eg": "delivery partners"}],
     {"platform": "Instagram reel", "length": "30 seconds", "audience": "people looking for work as {role}",
      "message": "what a normal day and a fair deal look like at {business}", "cta": "Call now", "tone": "Straight and honest"}, ""),
    ("scr-testimonial-ask", "Admission / season opening", "a video for admissions or a new season",
     "admissions video script for {business}", [B_NAME, B_AUD, {"key": "date", "label": "Last date / start date", "eg": "15 June"}],
     {"platform": "Instagram reel", "length": "30 seconds", "audience": "{audience}",
      "message": "why this is the year to join {business}", "hook": "a question a child or a customer really asks",
      "cta": "Call now", "tone": "Warm"}, "Date: {date}"),
]
_BLANK = re.compile(r"\{([a-z_]+)\}")


def _mk(t, section: str) -> dict[str, Any]:
    rid, title, makes, intent, blanks, slots = t[:6]
    return {"id": rid, "section": section, "title": title, "makes": makes, "intent": intent, "blanks": blanks,
            "slots": slots, "facts": t[6] if len(t) > 6 else "", "starter": True}


RECIPES: list[dict[str, Any]] = [*[_mk(t, "image") for t in _IMAGE], *[_mk(t, "script") for t in _SCRIPT]]


def listing(section: str = "", q: str = "", limit: int = 30) -> dict[str, Any]:
    """Recipes for the shelf. `web` comes from the Web Studio's template library (search by trade, city, style)."""
    out: list[dict[str, Any]] = []
    words = [w for w in (q or "").lower().split() if w]
    if section in ("", "image", "script"):
        for r in RECIPES:
            if section and r["section"] != section:
                continue
            hay = (r["title"] + " " + r["makes"] + " " + r["intent"]).lower()
            if all(w in hay for w in words):
                out.append({k: r[k] for k in ("id", "section", "title", "makes", "blanks", "starter")})
    try:                                         # BAHI: recipes whose results were kept come first, with the count
        from . import ledger as L
        rates = L.recipe_rates()
        for r in out:
            if r["id"] in rates:
                r["kept"] = rates[r["id"]]
        out.sort(key=lambda r: -(r["kept"]["kept"] / r["kept"]["of"]) if r.get("kept") else 1)
    except Exception:       # noqa: BLE001
        pass
    total = len(out)
    if section in ("", "web"):
        try:
            from ..site import templates as T
            got = T.search(q=q or "", limit=min(limit, 24))
            for c in got.get("items") or got.get("rows") or []:
                out.append({"id": f"web:{c.get('id')}", "section": "web", "title": c.get("title") or c.get("name") or "Website",
                            "makes": str(c.get("line") or "") + (f" - {c['style_label']}" if c.get("style_label") else ""),
                            "blanks": [], "starter": True})
            total += int(got.get("total") or 0)
        except Exception:       # noqa: BLE001 - the template library is optional here
            pass
    return {"items": out[:limit + 24], "total": total}


def _sub(text: str, values: dict[str, str]) -> tuple[str, bool]:
    """`text` with its blanks filled; the bool is False when a blank is still empty."""
    full = True

    def rep(m):
        nonlocal full
        v = str(values.get(m.group(1)) or "").strip()
        if not v:
            full = False
            return "[" + m.group(1).replace("_", " ") + "]"
        return v[:120]
    return _BLANK.sub(rep, text), full


def use(recipe_id: str, values: dict[str, str] | None = None) -> dict[str, Any]:
    """A recipe with her values -> {"brief": ...} (image / script) or {"ready": finished prompt} (a web template).
    A slot whose blank she left empty is LEFT OUT (it becomes a question), never filled with a made-up value."""
    values = {str(k): str(v) for k, v in (values or {}).items()}
    if recipe_id.startswith("web:"):
        from ..site import templates as T
        p = T.prompt(recipe_id[4:])
        return {"ready": {"section": "web", "title": p.get("title") or "Website", "prompt": p["prompt"],
                          "run": {"to": "web", "text": p["prompt"], "label": "Open in Web Studio"}}}
    r = next((x for x in RECIPES if x["id"] == recipe_id), None)
    if r is None:
        raise ValueError("No such recipe.")
    intent, _ = _sub(r["intent"], values)
    facts, full = _sub(r.get("facts") or "", values)
    if facts and full:
        intent += ". " + facts
    slots: dict[str, Any] = {}
    for k, v in r["slots"].items():
        text, ok = _sub(v, values)
        if ok:
            slots[k] = {"value": text, "source": "recipe"}
    raw = {"section": r["section"], "intent": intent, "slots": slots, "recipe_id": r["id"]}
    return {"brief": B.validate(raw)}


def check() -> list[str]:
    """Every starter is well-formed (run by a test): known slots only, blanks declared, no magic phrase."""
    bad: list[str] = []
    for r in RECIPES:
        declared = {b["key"] for b in r["blanks"]}
        used = set(_BLANK.findall(r["intent"] + " " + " ".join(r["slots"].values()) + " " + (r.get("facts") or "")))
        if used - declared:
            bad.append(f"{r['id']}: undeclared blanks {sorted(used - declared)}")
        if set(r["slots"]) - set(A.keys(r["section"])):
            bad.append(f"{r['id']}: unknown slots")
        if any(m in (r["intent"] + " ".join(r["slots"].values())).lower() for m in B.MAGIC):
            bad.append(f"{r['id']}: magic phrase")
    if len({r["id"] for r in RECIPES}) != len(RECIPES):
        bad.append("duplicate ids")
    return bad
