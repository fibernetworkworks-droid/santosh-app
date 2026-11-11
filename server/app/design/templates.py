"""HOOLA DESIGN AI: built-in layouts for a server with NO model configured.

`make(prompt, preset, brand, variant)` gives a spec in exactly the words the model would use (ai.py cleans and
builds it the same way), filled from the request's own words: the headline is what she asked for, her brand kit
gives the name and the colours, and every fact nobody gave - a price, a phone number, an address - is a marked
[blank]. Nothing is invented and no model is called. The answer of the route says "template", so nobody takes
this for a made-to-order design.
"""
from __future__ import annotations

import re
from typing import Any

# name: accent, accent dark (gradient end / pressed), tint, background, surface, border, ink, secondary ink
PALETTES: dict[str, dict[str, str]] = {
    "indigo": {"accent": "#4F46E5", "deep": "#312E81", "tint": "#EEF2FF", "bg": "#FFFFFF", "soft": "#F5F7FB",
               "line": "#E2E8F0", "ink": "#0F172A", "sub": "#475569", "on": "#FFFFFF"},
    "saffron": {"accent": "#C2410C", "deep": "#7C2D12", "tint": "#FFEDD5", "bg": "#FFFBF5", "soft": "#FFF4E6",
                "line": "#F1DFC9", "ink": "#1C1917", "sub": "#57534E", "on": "#FFFFFF"},
    "emerald": {"accent": "#047857", "deep": "#064E3B", "tint": "#D1FAE5", "bg": "#FFFFFF", "soft": "#F1F8F5",
                "line": "#D7E7E0", "ink": "#0B1F17", "sub": "#3F5B50", "on": "#FFFFFF"},
    "rose": {"accent": "#BE123C", "deep": "#881337", "tint": "#FFE4E6", "bg": "#FFFDFD", "soft": "#FFF5F6",
             "line": "#F3D9DD", "ink": "#1F1216", "sub": "#6B4A52", "on": "#FFFFFF"},
    "festive": {"accent": "#B45309", "deep": "#4A0D2B", "tint": "#FEF3C7", "bg": "#FFFBF2", "soft": "#FFF4DC",
                "line": "#F0DDB4", "ink": "#2B0A1A", "sub": "#6B3F4E", "on": "#FFFFFF"},
    "midnight": {"accent": "#A5B4FC", "deep": "#6366F1", "tint": "#1E2545", "bg": "#0B1020", "soft": "#141A30",
                 "line": "#273056", "ink": "#F8FAFC", "sub": "#B4C0DA", "on": "#0B1020"},
}
_PALETTE_WORDS = [
    (r"dark|night|premium|luxury|luxe|gaming|crypto|black|music|club", "midnight"),
    (r"diwali|deepavali|eid|holi|navratri|dussehra|rakhi|ganesh|pongal|onam|christmas|new year|festival|festive|wedding|"
     r"shaadi|shadi|mehndi|sangeet|anniversary|दिवाली|दीपावली|होली|ईद|शादी|त्योहार", "festive"),
    (r"food|restaurant|cafe|café|sweet|mithai|bakery|biryani|pizza|chai|tea|kitchen|tiffin|dhaba|catering|snack|"
     r"मिठाई|खाना|रेस्टोरेंट|चाय", "saffron"),
    (r"health|clinic|doctor|hospital|yoga|ayurved|organic|farm|plant|nursery|garden|eco|green|pharmacy|medical|"
     r"डॉक्टर|क्लिनिक|योग", "emerald"),
    (r"beauty|salon|parlour|parlor|spa|makeup|boutique|fashion|saree|jewel|bridal|florist|flower|ब्यूटी|सैलून|साड़ी", "rose"),
]
_HI = {
    "Welcome": "स्वागत है", "Search": "खोजें", "Get started": "शुरू करें", "See all": "सभी देखें", "Popular": "लोकप्रिय",
    "Home": "होम", "Cart": "कार्ट", "Profile": "प्रोफ़ाइल", "Continue": "आगे बढ़ें", "Sign in": "साइन इन",
    "Mobile number": "मोबाइल नंबर", "About": "हमारे बारे में", "Services": "सेवाएँ", "Contact": "संपर्क",
    "Get in touch": "संपर्क करें", "Learn more": "और जानें", "What you get": "आपको क्या मिलता है", "Ready to start?": "शुरू करें?",
    "Know more": "और जानें", "Message us": "हमें संदेश भेजें", "Thank you": "धन्यवाद", "Skip": "छोड़ें",
    "[One line about this]": "[इसके बारे में एक पंक्ति]", "[Your business name]": "[आपके व्यवसाय का नाम]",
    "[phone number]": "[फ़ोन नंबर]", "[your address]": "[आपका पता]", "[email]": "[ईमेल]", "[price]": "[कीमत]",
    "[Date and time]": "[तारीख़ और समय]", "[Your name]": "[आपका नाम]", "[Your role]": "[आपका पद]",
    "[Item name]": "[वस्तु का नाम]", "[Short detail]": "[छोटा विवरण]", "[Your tagline]": "[आपकी टैगलाइन]",
    "[Feature]": "[ख़ूबी]", "[Point]": "[बात]", "[What makes this special]": "[इसमें ख़ास क्या है]",
    "[Offer or date]": "[ऑफ़र या तारीख़]", "We will send a one-time code to this number.": "हम इस नंबर पर एक कोड भेजेंगे।",
}
_FORMAT = (r"(?:instagram|insta|facebook|whatsapp|social(?: media)?|a4|business|visiting|landing|home|web|mobile|phone|android|"
           r"app|presentation|pitch|onboarding|sign ?in|login)?\s*(?:poster|post|story|status|screen|screens|page|website|site|card|"
           r"slide|deck|logo|flyer|banner|pamphlet|mockup|wireframe|design|ui|app|template|creative|flow)")
_LEAD = re.compile(r"^(?:please\s+|pls\s+|kindly\s+)?(?:can you\s+|could you\s+)?(?:i\s+(?:need|want)\s+|we\s+(?:need|want)\s+)?"
                   r"(?:make|create|design|build|generate|draw|give|show|prepare)?\s*(?:me\s+|us\s+)?(?:an?\s+|the\s+|one\s+|ek\s+)?", re.I)
_TAIL = re.compile(r"\s*(?:banao|bana do|banaiye|bana dijiye|chahiye|please|pls|बनाओ|बनाइए|बना दो|चाहिए)\s*$", re.I)


def _is_hindi(text: str) -> bool:
    return sum(1 for ch in text if "ऀ" <= ch <= "ॿ") >= 3


def subject(prompt: str) -> tuple[str, str]:
    """(headline, about) from her own words: "a Diwali sale poster for my sweet shop" -> ("Diwali sale", "Sweet shop").
    Never more than she said; ("", "") when the request names only the format."""
    s = re.sub(r"\s+", " ", str(prompt or "")).strip().strip(".!?।")
    s = _TAIL.sub("", _LEAD.sub("", s, count=1))
    s = re.sub(r"^\d+\s+(?:\w+\s+)?(?:screens?|pages?|slides?)\s*(?:of|for)?\s*", "", s, flags=re.I)
    m = re.search(r"\b" + _FORMAT + r"\b\s*(?:for|of|about|on|to promote|ke liye|के लिए)\s+", s, re.I)
    if m:
        left, right = s[:m.start()].strip(), s[m.end():].strip()
    else:
        left, right = re.sub(r"\s*\b" + _FORMAT + r"\b\s*$", "", s, flags=re.I).strip(), ""
        left = re.sub(r"^\b" + _FORMAT + r"\b\s*[:\-]?\s*", "", left, flags=re.I).strip()
    for _ in range(3):                                   # "pitch deck", "grocery app": the format's own words are not a headline
        left = re.sub(r"^\s*\b" + _FORMAT + r"\b\s*[:\-]?\s*|\s*\b" + _FORMAT + r"\b\s*$", "", left, flags=re.I).strip()
        right = re.sub(r"\s+\b(?:app|website|site|page)\b\s*$", "", right, flags=re.I).strip()
    left = re.sub(r"\s*(?:का|की|के)?\s*(?:पोस्टर|पोस्ट|स्टोरी|स्टेटस|लोगो|कार्ड|स्क्रीन|वेबसाइट|ऐप|डिज़ाइन|डिजाइन)\s*$", "", left).strip()
    right = re.sub(r"^(?:my|our|a|an|the|mera|meri|hamara|hamari)\s+", "", right, flags=re.I).strip()
    left = re.sub(r"^(?:my|our|a|an|the)\s+", "", left, flags=re.I).strip()
    head, about = (left, right) if left else (right, "")

    def tidy(t: str, cap: int) -> str:
        t = t.strip(" ,;:-")
        if len(t) > cap:
            t = t[:cap].rsplit(" ", 1)[0]
        return t[:1].upper() + t[1:]

    return tidy(head, 64), tidy(about, 40)


def palette(prompt: str, brand: dict, variant: int = 0) -> dict[str, str]:
    low = str(prompt or "").lower()
    name = next((n for pattern, n in _PALETTE_WORDS if re.search(pattern, low)), "indigo")
    if variant:
        order = [name] + [k for k in ("indigo", "midnight", "saffron", "emerald", "rose", "festive") if k != name]
        name = order[variant % len(order)]
    pal = dict(PALETTES[name])
    cols = (brand or {}).get("colors") or {}
    if cols.get("primary"):
        pal.update(accent=cols["primary"], deep=cols.get("dark") or cols.get("secondary") or pal["deep"])
        if name == "midnight":
            pal = {**PALETTES["indigo"], "accent": cols["primary"], "deep": cols.get("dark") or PALETTES["indigo"]["deep"]}
        if cols.get("light"):
            pal["tint"] = cols["light"]
    return pal


# ------------------------------------------------------------------------------------------- spec words
def T(chars: str, size: float, weight: int = 400, color: str = "", **kw: Any) -> dict:
    return {"type": "text", "chars": chars, "size": size, "weight": weight, "color": color, **kw}


def F(name: str, layout: str, children: list, **kw: Any) -> dict:
    return {"type": "frame", "name": name, "layout": layout, "children": [c for c in children if c], **kw}


def I(icon: str, size: float, color: str, **kw: Any) -> dict:
    return {"type": "icon", "icon": icon, "size": size, "color": color, **kw}


def IMG(label: str, **kw: Any) -> dict:
    return {"type": "image", "label": label, **kw}


def _button(label: str, fill: Any, ink: str, size: float = 16, pad: list | None = None, icon: str = "", **kw: Any) -> dict:
    return F("Button", "row", [T(label, size, 600, ink), I(icon, size + 2, ink) if icon else None], gap=8, align="center",
             justify="center", pad=pad or [14, 24, 14, 24], radius=999, fill=fill, **kw)


class _Ctx:
    def __init__(self, prompt: str, brand: dict, variant: int, assets: dict):
        self.hindi = _is_hindi(prompt)
        self.head, self.about = subject(prompt)
        self.p = palette(prompt, brand, variant)
        self.brand = (brand or {}).get("name") or ""
        self.tagline = (brand or {}).get("tagline") or ""
        self.contact = (brand or {}).get("contact") or {}
        self.logo = "logo" in (assets or {})
        self.font = "Noto Sans Devanagari" if self.hindi else "Inter"
        self.display = "Noto Sans Devanagari" if self.hindi else "Sora"

    def t(self, s: str) -> str:
        return _HI.get(s, s) if self.hindi else s

    @property
    def name(self) -> str:
        return self.brand or self.t("[Your business name]")

    @property
    def title(self) -> str:
        return self.head or self.about or self.brand or self.t("[Your headline]")

    @property
    def kicker(self) -> str:
        return self.about or self.tagline or ""

    def phone(self) -> str:
        return self.contact.get("phone") or self.contact.get("whatsapp") or self.t("[phone number]")

    def grad(self, angle: int = 135) -> dict:
        return {"from": self.p["accent"], "to": self.p["deep"], "angle": angle}


# ------------------------------------------------------------------------------------------- phone
def _nav(c: _Ctx) -> dict:
    p = c.p
    items = [("home", "Home", True), ("search", "Search", False), ("cart", "Cart", False), ("user", "Profile", False)]
    return F("Bottom bar", "row", [
        F(label, "column", [I(icon, 24, p["accent"] if on else p["sub"]),
                            T(c.t(label), 12, 600 if on else 500, p["accent"] if on else p["sub"], font=c.font)],
          gap=4, align="center", w="hug") for icon, label, on in items
    ], justify="between", align="center", pad=[12, 32, 24, 32], fill=p["bg"], stroke={"color": p["line"], "width": 1})


def phone_home(c: _Ctx, preset: str = "phone") -> dict:
    p = c.p
    row = lambda n: F(f"Item {n}", "row", [                                         # noqa: E731
        IMG("Photo", w=64, h=64, radius=14, fill=p["tint"]),
        F("Words", "column", [T(c.t("[Item name]"), 16, 600, p["ink"], font=c.font),
                              T(c.t("[Short detail]"), 14, 400, p["sub"], font=c.font)], gap=4, w="fill"),
        T("₹" + c.t("[price]"), 16, 600, p["accent"], font=c.font),
    ], gap=14, align="center", pad=12, radius=18, fill=p["bg"], stroke={"color": p["line"], "width": 1})
    content = F("Content", "column", [
        F("Header", "row", [
            F("Greeting", "column", [T(c.kicker or c.t("Welcome"), 14, 500, p["sub"], font=c.font),
                                     T(c.name, 24, 700, p["ink"], font=c.display, lineHeight=1.2)], gap=4, w="fill"),
            F("Avatar", "row", [I("user", 22, p["accent"])], w=44, h=44, radius=999, fill=p["tint"], align="center", justify="center"),
        ], gap=12, align="center"),
        F("Search", "row", [I("search", 20, p["sub"]), T(c.t("Search"), 16, 400, p["sub"], font=c.font)],
          gap=12, align="center", pad=[0, 16, 0, 16], h=52, radius=16, fill=p["soft"], stroke={"color": p["line"], "width": 1}),
        F("Hero card", "column", [
            T(c.title, 24, 700, "#FFFFFF", font=c.display, lineHeight=1.2, w="fill"),
            T(c.t("[One line about this]"), 14, 400, "#FFFFFF", font=c.font, opacity=0.9, w="fill"),
            _button(c.t("Get started"), "#FFFFFF", p["deep"], 14, [12, 18, 12, 18], "arrow-right", w="hug"),
        ], gap=12, pad=20, radius=24, fill=c.grad(), shadow="md"),
        F("Section title", "row", [T(c.t("Popular"), 18, 600, p["ink"], font=c.display, w="fill"),
                                   T(c.t("See all"), 14, 600, p["accent"], font=c.font)], align="center"),
        F("List", "column", [row(1), row(2), row(3)], gap=12),
    ], gap=20, pad=[56, 20, 16, 20], h="fill")
    return F("Home", "column", [content, _nav(c)], preset=preset, fill=p["soft"] if p["bg"] == "#FFFFFF" else p["bg"])


def phone_signin(c: _Ctx, preset: str = "phone") -> dict:
    p = c.p
    return F("Sign in", "column", [
        F("Top", "column", [
            F("Mark", "row", [T((c.name.strip("[] ") or "H")[:1].upper(), 32, 700, "#FFFFFF", font=c.display)],
              w=72, h=72, radius=22, fill=c.grad(), align="center", justify="center", shadow="md"),
            T(c.name, 32, 700, p["ink"], font=c.display, lineHeight=1.15, w="fill"),
            T(c.title if c.head else c.t("[One line about this]"), 16, 400, p["sub"], font=c.font, w="fill"),
        ], gap=16, h="fill", justify="center"),
        F("Form", "column", [
            T(c.t("Mobile number"), 14, 600, p["ink"], font=c.font),
            F("Field", "row", [I("phone", 20, p["sub"]), T("+91  " + c.t("[phone number]"), 16, 400, p["sub"], font=c.font)],
              gap=12, align="center", pad=[0, 16, 0, 16], h=56, radius=16, fill=p["bg"], stroke={"color": p["line"], "width": 1}),
            T(c.t("We will send a one-time code to this number."), 14, 400, p["sub"], font=c.font, w="fill"),
            _button(c.t("Continue"), p["accent"], p["on"], 16, [16, 24, 16, 24], "arrow-right"),
        ], gap=12),
    ], preset=preset, pad=[72, 24, 40, 24], gap=24, fill=p["soft"] if p["bg"] == "#FFFFFF" else p["bg"])


def phone_welcome(c: _Ctx, preset: str = "phone") -> dict:
    p = c.p
    return F("Welcome", "column", [
        F("Top bar", "row", [T(c.name, 16, 600, "#FFFFFF", font=c.display, w="fill"), T(c.t("Skip"), 14, 500, "#FFFFFF", font=c.font, opacity=0.85)],
          align="center"),
        IMG("A photo that shows what you offer", h="fill", radius=28, fill=p["tint"]),
        F("Words", "column", [
            T(c.title, 32, 700, "#FFFFFF", font=c.display, lineHeight=1.15, w="fill"),
            T(c.t("[One line about this]"), 16, 400, "#FFFFFF", font=c.font, opacity=0.9, w="fill"),
        ], gap=12),
        _button(c.t("Get started"), "#FFFFFF", p["deep"], 16, [16, 24, 16, 24], "arrow-right"),
    ], preset=preset, pad=[64, 24, 40, 24], gap=28, fill=c.grad(160))


# ------------------------------------------------------------------------------------------- web
def web_landing(c: _Ctx) -> dict:
    p = c.p
    link = lambda s: T(c.t(s), 16, 500, p["sub"], font=c.font)       # noqa: E731
    feature = lambda n, icon: F(f"Feature {n}", "column", [          # noqa: E731
        F("Icon tile", "row", [I(icon, 26, p["accent"])], w=56, h=56, radius=16, fill=p["tint"], align="center", justify="center"),
        T(f"{c.t('[Feature]')} {n}", 24, 600, p["ink"], font=c.display, lineHeight=1.25),
        T(c.t("[What makes this special]"), 16, 400, p["sub"], font=c.font, lineHeight=1.5, w="fill"),
    ], gap=16, pad=32, radius=24, fill=p["bg"], stroke={"color": p["line"], "width": 1}, w="fill")
    return F("Landing page", "column", [
        F("Navigation", "row", [
            T(c.name, 24, 700, p["ink"], font=c.display, w="fill"),
            F("Links", "row", [link("Home"), link("About"), link("Services"), link("Contact")], gap=36, align="center"),
            _button(c.t("Get in touch"), p["accent"], p["on"], 16, [12, 22, 12, 22]),
        ], gap=48, align="center", pad=[24, 120, 24, 120], fill=p["bg"], stroke={"color": p["line"], "width": 1}),
        F("Hero", "row", [
            F("Words", "column", [
                F("Pill", "row", [I("sparkle", 16, p["accent"], filled=True), T(c.kicker or c.t("Welcome"), 14, 600, p["accent"], font=c.font)],
                  gap=8, align="center", pad=[8, 14, 8, 14], radius=999, fill=p["tint"], w="hug"),
                T(c.title, 64, 700, p["ink"], font=c.display, lineHeight=1.08, w="fill"),
                T(c.t("[One line about this]"), 18, 400, p["sub"], font=c.font, lineHeight=1.55, w="fill"),
                F("Actions", "row", [_button(c.t("Get started"), p["accent"], p["on"], 16, [16, 28, 16, 28], "arrow-right"),
                                     _button(c.t("Learn more"), p["bg"], p["ink"], 16, [16, 28, 16, 28], stroke={"color": p["line"], "width": 1})],
                  gap=16, align="center"),
            ], gap=24, w="fill"),
            IMG("A photo that shows what you offer", w=560, h=440, radius=32, fill=p["tint"]),
        ], gap=72, align="center", pad=[96, 120, 96, 120], fill=p["bg"]),
        F("Features", "column", [
            T(c.t("What you get"), 40, 700, p["ink"], font=c.display, lineHeight=1.15, align="center", w="fill"),
            F("Cards", "row", [feature(1, "bolt"), feature(2, "shield"), feature(3, "heart")], gap=24),
        ], gap=48, pad=[96, 120, 96, 120], fill=p["soft"]),
        F("Call to action", "column", [
            T(c.t("Ready to start?"), 48, 700, "#FFFFFF", font=c.display, lineHeight=1.1, align="center", w="fill"),
            T(c.phone(), 18, 500, "#FFFFFF", font=c.font, align="center", opacity=0.92, w="fill"),
            _button(c.t("Get in touch"), "#FFFFFF", p["deep"], 16, [16, 32, 16, 32], "arrow-right", w="hug"),
        ], gap=24, align="center", pad=[88, 120, 88, 120], fill=c.grad(120)),
        F("Footer", "row", [T(c.name, 16, 600, p["ink"], font=c.display, w="fill"),
                            T(c.contact.get("address") or c.t("[your address]"), 14, 400, p["sub"], font=c.font)],
          align="center", pad=[32, 120, 32, 120], fill=p["bg"]),
    ], preset="web", fill=p["bg"])


# ------------------------------------------------------------------------------------------- post / story / poster
def _dots(c: _Ctx, w: int, h: int) -> list[dict]:
    r1, r2 = int(w * 0.62), int(w * 0.42)
    return [{"type": "ellipse", "name": "Glow", "x": w - int(r1 * 0.62), "y": -int(r1 * 0.38), "w": r1, "h": r1, "fill": "#FFFFFF", "opacity": 0.08},
            {"type": "ellipse", "name": "Glow", "x": -int(r2 * 0.4), "y": h - int(r2 * 0.6), "w": r2, "h": r2, "fill": "#FFFFFF", "opacity": 0.07}]


def social_post(c: _Ctx, preset: str = "instagram") -> dict:
    p = c.p
    w, h = 1080, 1080
    content = F("Content", "column", [
        F("Top", "row", [
            T(c.name, 32, 600, "#FFFFFF", font=c.display, w="fill"),
            F("Tag", "row", [T(c.t("[Offer or date]"), 26, 600, "#FFFFFF", font=c.font)], pad=[12, 24, 12, 24], radius=999,
              stroke={"color": "#FFFFFF", "width": 2}, w="hug"),
        ], gap=24, align="center"),
        F("Message", "column", [
            T(c.kicker, 30, 600, p["tint"], font=c.font, letterSpacing=4, upper=True) if c.kicker else None,
            T(c.title, 112 if len(c.title) <= 22 else 84, 700, "#FFFFFF", font=c.display, lineHeight=1.04, w="fill"),
            T(c.t("[One line about this]"), 38, 400, "#FFFFFF", font=c.font, lineHeight=1.35, opacity=0.9, w="fill"),
        ], gap=28, h="fill", justify="center"),
        F("Bottom", "row", [
            F("Contact", "row", [I("phone", 34, "#FFFFFF"), T(c.phone(), 32, 500, "#FFFFFF", font=c.font)], gap=14, align="center", w="fill"),
            _button(c.t("Know more"), "#FFFFFF", p["deep"], 32, [24, 44, 24, 44]),
        ], gap=24, align="center"),
    ], x=0, y=0, w=w, h=h, pad=88, gap=40)
    return F("Post", "none", _dots(c, w, h) + [content], preset=preset, fill=c.grad(140))


def story(c: _Ctx, preset: str = "story") -> dict:
    p = c.p
    w, h = 1080, 1920
    content = F("Content", "column", [
        T(c.name, 36, 600, "#FFFFFF", font=c.display, align="center", w="fill"),
        IMG("A photo that shows what you offer", h="fill", radius=56, fill=p["tint"]),
        F("Message", "column", [
            T(c.kicker, 32, 600, p["tint"], font=c.font, letterSpacing=5, upper=True, align="center", w="fill") if c.kicker else None,
            T(c.title, 104 if len(c.title) <= 20 else 80, 700, "#FFFFFF", font=c.display, lineHeight=1.06, align="center", w="fill"),
            T(c.t("[One line about this]"), 40, 400, "#FFFFFF", font=c.font, lineHeight=1.35, align="center", opacity=0.9, w="fill"),
        ], gap=28),
        F("Action", "column", [_button(c.t("Message us"), "#FFFFFF", p["deep"], 36, [28, 56, 28, 56], "chat", w="hug")], align="center"),
    ], x=0, y=0, w=w, h=h, pad=[180, 88, 200, 88], gap=64)
    return F("Story", "none", _dots(c, w, h) + [content], preset=preset, fill=c.grad(170))


def poster(c: _Ctx) -> dict:
    p = c.p
    info = lambda icon, text: F("Detail", "row", [                                   # noqa: E731
        F("Icon tile", "row", [I(icon, 36, p["accent"])], w=80, h=80, radius=20, fill=p["tint"], align="center", justify="center"),
        T(text, 36, 500, p["ink"], font=c.font, lineHeight=1.3, w="fill")], gap=28, align="center")
    return F("Poster", "column", [
        F("Band", "column", [
            T(c.name, 36, 600, "#FFFFFF", font=c.display, w="fill"),
            T(c.kicker, 30, 600, p["tint"], font=c.font, letterSpacing=5, upper=True, w="fill") if c.kicker else None,
            T(c.title, 148 if len(c.title) <= 18 else 112, 700, "#FFFFFF", font=c.display, lineHeight=1.03, w="fill"),
            T(c.t("[One line about this]"), 44, 400, "#FFFFFF", font=c.font, lineHeight=1.3, opacity=0.92, w="fill"),
        ], gap=32, pad=[96, 96, 104, 96], fill=c.grad(150)),
        F("Body", "column", [
            IMG("A photo that shows what you offer", h="fill", radius=36, fill=p["tint"]),
            F("Details", "column", [info("calendar", c.t("[Date and time]")),
                                    info("map-pin", c.contact.get("address") or c.t("[your address]")),
                                    info("phone", c.phone())], gap=24),
        ], gap=56, pad=[80, 96, 96, 96], h="fill"),
    ], preset="poster", fill=p["bg"])


# ------------------------------------------------------------------------------------------- card / slide / logo
def business_card(c: _Ctx) -> dict:
    p = c.p
    name = c.brand or c.head or c.about or c.name
    line = lambda icon, text: F("Line", "row", [I(icon, 26, p["accent"]), T(text, 26, 400, p["ink"], font=c.font, w="fill")],   # noqa: E731
                                gap=16, align="center")
    return F("Business card", "row", [
        F("Side", "column", [
            F("Mark", "row", [T((name.strip("[] ") or "H")[:1].upper(), 72, 700, p["deep"], font=c.display)],
              w=140, h=140, radius=999, fill="#FFFFFF", align="center", justify="center"),
            T(name, 34, 700, "#FFFFFF", font=c.display, lineHeight=1.2, align="center", w="fill"),
        ], gap=28, align="center", justify="center", pad=40, w=380, h="fill", fill=c.grad(160)),
        F("Details", "column", [
            F("Who", "column", [T(c.t("[Your name]"), 46, 700, p["ink"], font=c.display, lineHeight=1.15),
                                T(c.t("[Your role]"), 26, 500, p["accent"], font=c.font)], gap=8),
            {"type": "line", "color": p["line"], "width": 2},
            F("Contact", "column", [line("phone", c.phone()), line("mail", c.contact.get("email") or c.t("[email]")),
                                    line("map-pin", c.contact.get("address") or c.t("[your address]"))], gap=18),
        ], gap=32, justify="center", pad=[56, 64, 56, 64], w="fill", h="fill"),
    ], preset="card", fill=p["bg"])


def slide(c: _Ctx) -> dict:
    p = c.p
    point = lambda n: F(f"Point {n}", "row", [                                       # noqa: E731
        F("Tick", "row", [I("check", 26, p["on"])], w=48, h=48, radius=999, fill=p["accent"], align="center", justify="center"),
        T(f"{c.t('[Point]')} {n}", 36, 500, p["ink"], font=c.font, w="fill")], gap=24, align="center")
    return F("Slide", "row", [
        F("Words", "column", [
            T(c.kicker or c.name, 28, 600, p["accent"], font=c.font, letterSpacing=4, upper=True),
            T(c.title, 96 if len(c.title) <= 26 else 72, 700, p["ink"], font=c.display, lineHeight=1.06, w="fill"),
            T(c.t("[One line about this]"), 36, 400, p["sub"], font=c.font, lineHeight=1.4, w="fill"),
            F("Points", "column", [point(1), point(2), point(3)], gap=24),
        ], gap=40, justify="center", pad=[96, 80, 96, 120], w="fill", h="fill"),
        F("Picture side", "column", [IMG("A photo or chart for this slide", h="fill", radius=40, fill=p["tint"])],
          pad=[72, 72, 72, 0], w=760, h="fill"),
    ], preset="slide", fill=p["bg"])


def logo(c: _Ctx) -> dict:
    p = c.p
    name = c.name if c.brand else (c.title if (c.head or c.about) else c.name)
    chip = lambda col: {"type": "ellipse", "w": 36, "h": 36, "fill": col, "stroke": {"color": p["line"], "width": 1}}   # noqa: E731
    return F("Logo", "column", [
        F("Lockup", "row", [
            F("Mark", "row", [T((name.strip("[] ") or "H")[:1].upper(), 80, 700, "#FFFFFF", font=c.display)],
              w=144, h=144, radius=40, fill=c.grad(140), align="center", justify="center", shadow="md"),
            F("Words", "column", [T(name, 60 if len(name) <= 16 else 44, 700, p["ink"], font=c.display, lineHeight=1.1),
                                  T(c.tagline or c.t("[Your tagline]"), 20, 500, p["sub"], font=c.font, letterSpacing=4, upper=True)], gap=10),
        ], gap=32, align="center", w="hug"),
        F("Colours", "row", [chip(p["accent"]), chip(p["deep"]), chip(p["tint"]), chip(p["ink"])], gap=14, w="hug"),
    ], preset="logo", gap=56, align="center", justify="center", fill=p["bg"])


# ------------------------------------------------------------------------------------------- choose
def make(prompt: str, preset: str = "", brand: dict | None = None, variant: int = 0, assets: dict | None = None) -> dict:
    """A raw spec ({notes, frames}) for the request, from the built-in layouts."""
    c = _Ctx(prompt, brand or {}, variant, assets or {})
    low = str(prompt or "").lower()
    key = preset or "phone"
    if key in ("phone", "android"):
        many = re.search(r"screens|flow|onboarding|\b[2-6]\s+(?:app\s+)?(?:screen|page)", low)
        if many:
            frames = [phone_welcome(c, key), phone_signin(c, key), phone_home(c, key)]
        elif re.search(r"login|log in|sign ?in|sign ?up|signup|otp|register|लॉगिन", low):
            frames = [phone_signin(c, key)]
        elif re.search(r"welcome|splash|intro", low):
            frames = [phone_welcome(c, key)]
        else:
            frames = [phone_home(c, key)]
    else:
        frames = [{"web": web_landing, "poster": poster, "card": business_card, "slide": slide, "logo": logo}.get(key, lambda x: None)(c)
                  or (story(c, key) if key in ("story", "whatsapp") else social_post(c, "instagram"))]
    return {"notes": "A built-in Hoola layout filled from your words; every [blank] is a fact only you know.", "frames": frames}
