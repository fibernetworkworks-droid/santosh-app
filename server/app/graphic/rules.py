"""Graphic Sahayak: pure rules (job kinds, print formats + vendor specs, preflight of her artwork files, font / asset licence
verdicts, trademark-search help for logos, revision rounds, GST / TDS notes, copyright assignment words).

Sources (checked 23 Oct 2026):
- GST: graphic design = specialty design services SAC 998391 (998392 for "design originals"), 18% (9% CGST + 9% SGST inside
  the state, 18% IGST outside); exports zero-rated (LUT); registration Rs 20 lakh for services (Rs 10 lakh special category
  states) - taxaj.com/learn/?p=505 (19 Jul 2026, upd. 14 Oct 2026). Her CA confirms the code per job.
- TDS (client side): Income-tax Act 2025 s.393(1) from 1 Apr 2026 - professional / technical fees 10% (2% technical) above
  Rs 50,000 a year, contract work 1% / 2% above Rs 30,000 a payment or Rs 1 lakh a year (studycafe.in TDS chart FY 2026-27);
  advertising work is commonly treated as contract (CBDT Circular 714 of 3 Aug 1995; vjmglobal.com). The CLIENT decides what it
  deducts: Hoola only records the rate the client says.
- Copyright Act 1957: s.17 the author (the freelance designer) is the first owner unless she works under a contract of service
  (s.17(c)); s.17(b) gives commissioned photographs / paintings / portraits / engravings / films to the person who paid, NOT
  logos / layouts. s.18-19: an assignment is valid only in WRITING signed by the assignor and names the rights, the
  royalty / consideration, the duration and the territory; no duration = 5 years (s.19(5)); no territory = India (s.19(6));
  not exercised within 1 year = deemed lapsed unless the deed says otherwise (s.19(4)). s.57 moral rights stay with her.
  (indiacode.nic.in a195714.pdf; courtbook.in/copyright-act-1957/section-19)
- Trade marks: logos are searched on IP India's public search (tmrsearch.ipindia.gov.in, linked from ipindiaonline.gov.in):
  Wordmark (start with / contains / match), Phonetic, and Vienna Code for figurative / logo elements, per class 1-45
  (calcguru.in/?p=5072, 12 Aug 2026). A search is a signal, not a clearance: a trade-mark attorney gives the opinion.
- Fonts: Google Fonts are under the SIL Open Font License / Apache: free for commercial print, logos and sharing the files
  (developers.google.com/fonts/faq). Adobe Fonts: files may NOT be sent to clients or printers; finished PDFs / PNGs with
  embedded or outlined text are fine; a client who edits needs its own licence; logos can be trademarked but the typeface
  can't (helpx.adobe.com font-licensing FAQ, upd. 27 Mar 2026). "Free for personal use" fonts are not for client work.
- Print: 3 mm bleed each side, 300 dpi for paper (150 dpi is the floor for photos), ~100 dpi for flex; CMYK for offset /
  digital presses, PDF (PDF/X-1a preferred) with fonts embedded (brand.rules sources; vistaprint.com business-card file prep).
  Indian visiting card common size 3.5 x 2 in (89 x 51 mm); 85 x 55 mm also used - the vendor's spec decides.
- Emblems and Names (Prevention of Improper Use) Act 1950: brand.rules.protected (reused, never copied).
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from typing import Any

# ---------------------------------------------------------------- job kinds
KINDS: dict[str, dict[str, Any]] = {
    "logo": {"label": "Logo / brand identity", "days": 10, "rounds": 3, "print": False,
             "files": ["SVG (vector)", "PDF (vector)", "PNG transparent (1000 px+)", "JPG", "One-colour (mono) version",
                       "Reversed (white) version", "Favicon / profile 512 px"]},
    "social": {"label": "Social media posts", "days": 3, "rounds": 2, "print": False, "sizes": ["insta_post", "story", "insta_square"]},
    "poster": {"label": "Poster / ad", "days": 3, "rounds": 2, "print": False, "sizes": ["insta_post", "a4"]},
    "flyer": {"label": "Flyer / pamphlet", "days": 3, "rounds": 2, "print": True, "format": "a5"},
    "brochure": {"label": "Brochure", "days": 7, "rounds": 2, "print": True, "format": "a4"},
    "visiting_card": {"label": "Visiting card", "days": 2, "rounds": 2, "print": True, "format": "visiting_card"},
    "letterhead": {"label": "Letterhead / stationery", "days": 3, "rounds": 2, "print": True, "format": "a4"},
    "packaging": {"label": "Packaging / box", "days": 10, "rounds": 3, "print": True, "format": "custom"},
    "label": {"label": "Label / sticker", "days": 5, "rounds": 2, "print": True, "format": "custom"},
    "banner": {"label": "Flex / banner / hoarding", "days": 2, "rounds": 2, "print": True, "format": "flex_6x3"},
    "standee": {"label": "Standee", "days": 2, "rounds": 2, "print": True, "format": "standee"},
    "menu": {"label": "Menu card", "days": 4, "rounds": 2, "print": True, "format": "a4"},
    "invitation": {"label": "Invitation / card", "days": 4, "rounds": 2, "print": True, "format": "a5"},
    "presentation": {"label": "Presentation / deck", "days": 5, "rounds": 2, "print": False},
    "other": {"label": "Other work", "days": 5, "rounds": 2, "print": False},
}
KIND_WORDS = [
    ("logo", r"\b(logo|identity|branding|brand kit|लोगो)\b"), ("visiting_card", r"\b(visiting|business) ?card\b"),
    ("letterhead", r"\bletter ?head|stationery\b"), ("packaging", r"\b(packag|box|dabba|pouch)"),
    ("label", r"\b(label|sticker)\b"), ("banner", r"\b(flex|banner|hoarding)\b"), ("standee", r"\bstandee\b"),
    ("menu", r"\bmenu\b"), ("invitation", r"\b(invitation|invite|card shaadi|nimantran|patrika|kankotri)\b"),
    ("brochure", r"\bbrochure|catalogue|catalog\b"), ("flyer", r"\b(flyer|pamphlet|handbill|parcha)\b"),
    ("presentation", r"\b(ppt|presentation|deck|slides)\b"), ("social", r"\b(insta|instagram|social|post|story|reel cover|status)\b"),
    ("poster", r"\bposter|ad\b"),
]

# ---------------------------------------------------------------- print formats (trim size in mm) + vendor spec defaults
FORMATS: dict[str, dict[str, Any]] = {
    "visiting_card": {"label": "Visiting card 3.5 x 2 in", "mm": (89, 51), "bleed": 3, "safe": 4, "dpi": 300},
    "visiting_card_55": {"label": "Visiting card 85 x 55 mm", "mm": (85, 55), "bleed": 3, "safe": 4, "dpi": 300},
    "a3": {"label": "A3", "mm": (297, 420), "bleed": 3, "safe": 5, "dpi": 300},
    "a4": {"label": "A4", "mm": (210, 297), "bleed": 3, "safe": 5, "dpi": 300},
    "a5": {"label": "A5", "mm": (148, 210), "bleed": 3, "safe": 5, "dpi": 300},
    "dl": {"label": "DL (99 x 210)", "mm": (99, 210), "bleed": 3, "safe": 5, "dpi": 300},
    "flex_6x3": {"label": "Flex 6 x 3 ft", "mm": (1829, 914), "bleed": 0, "safe": 25, "dpi": 100},
    "flex_10x4": {"label": "Flex 10 x 4 ft", "mm": (3048, 1219), "bleed": 0, "safe": 30, "dpi": 72},
    "standee": {"label": "Standee 2.5 x 6 ft", "mm": (762, 1829), "bleed": 3, "safe": 25, "dpi": 120},
}
VENDOR_DEFAULTS = {"color": "cmyk", "dpi": 300, "bleed": 3, "safe": 4, "format": "pdf", "min_font_pt": 6, "pdfx": False,
                   "ink_limit": 300}
WIDE_FORMAT_MM = 600          # anything wider than this is large-format (flex / vinyl): low dpi is normal


def format_spec(fmt: str, custom: dict[str, Any] | None = None, vendor: dict[str, Any] | None = None) -> dict[str, Any]:
    """Trim / bleed / safe / dpi / colour for a job: the job's custom size > the format table; the vendor's spec overrides."""
    base = dict(FORMATS.get(fmt) or {})
    c = custom or {}
    if c.get("w_mm") and c.get("h_mm"):
        base["mm"] = (float(c["w_mm"]), float(c["h_mm"]))
        base.setdefault("label", f"{c['w_mm']:g} x {c['h_mm']:g} mm")
    if not base.get("mm"):
        return {}
    v = {**VENDOR_DEFAULTS, **{k: x for k, x in (vendor or {}).items() if x not in (None, "")}}
    wide = max(base["mm"]) > WIDE_FORMAT_MM
    out = {"label": base.get("label") or fmt, "mm": tuple(float(x) for x in base["mm"]),
           "bleed": float(c.get("bleed_mm") if c.get("bleed_mm") is not None else (vendor or {}).get("bleed", base.get("bleed", 3))),
           "safe": float(c.get("safe_mm") if c.get("safe_mm") is not None else (vendor or {}).get("safe", base.get("safe", 4))),
           "dpi": int((vendor or {}).get("dpi") or base.get("dpi") or v["dpi"]),
           "color": str(v.get("color") or "cmyk").lower(), "file": str(v.get("format") or "pdf").lower(),
           "min_font_pt": float(v.get("min_font_pt") or 6), "pdfx": bool(v.get("pdfx")), "wide": wide}
    if wide and not (vendor or {}).get("dpi"):
        out["dpi"] = min(out["dpi"], int(base.get("dpi") or 100))
    return out


# ---------------------------------------------------------------- preflight of HER artwork file
def _mm(pt: float) -> float:
    return pt * 25.4 / 72.0


def _close(a: float, b: float, tol: float = 1.2) -> bool:
    return abs(a - b) <= tol


def _size_fit(wmm: float, hmm: float, spec: dict[str, Any]) -> str:
    """'bleed' = trim + bleed, 'trim' = only trim size (no bleed), 'rotated', '' = wrong size."""
    tw, th = spec["mm"]
    b = spec["bleed"]
    for (W, H, tag) in ((tw + 2 * b, th + 2 * b, "bleed"), (tw, th, "trim")):
        if _close(wmm, W) and _close(hmm, H):
            return tag
        if _close(wmm, H) and _close(hmm, W):
            return tag + "_rotated"
    return ""


def preflight_image(data: bytes, spec: dict[str, Any]) -> dict[str, Any]:
    """A JPG / PNG / TIFF she made: pixels vs print size -> effective dpi, colour mode, bleed, transparency."""
    from PIL import Image
    issues: list[dict[str, str]] = []
    try:
        im = Image.open(io.BytesIO(data))
    except Exception:
        return {"ok": False, "issues": [{"level": "block", "text": "The file does not open (damaged photo?)."}]}
    w, h = im.size
    mode = im.mode
    tw, th = spec["mm"]
    b = spec["bleed"]
    full_w, full_h = tw + 2 * b, th + 2 * b
    rot = (w > h) != (full_w > full_h) and abs(full_w - full_h) > 1
    if rot:
        full_w, full_h = full_h, full_w
    dpi_w = w / (full_w / 25.4)
    dpi_h = h / (full_h / 25.4)
    eff = round(min(dpi_w, dpi_h))
    ratio_file, ratio_print = w / h, full_w / full_h
    trim_ratio = (th / tw) if rot else (tw / th)
    if abs(ratio_file - ratio_print) / ratio_print > 0.02:
        if b and abs(ratio_file - trim_ratio) / trim_ratio <= 0.02:
            issues.append({"level": "block", "text": f"No bleed: the file is only the trim size; add {b:g} mm bleed on every side "
                                                     "(background to the edge)."})
        else:
            issues.append({"level": "block", "text": f"File size ({w}x{h} px) {spec['label']} proportions do not match."})
    need = spec["dpi"]
    if eff < need * 0.5:
        issues.append({"level": "block", "text": f"Resolution low: ~{eff} dpi (need {need}). The print will be blurry."})
    elif eff < need * 0.9:
        issues.append({"level": "warn", "text": f"Resolution ~{eff} dpi (need {need}): small text / photos may be slightly blurry."})
    if spec.get("color") == "cmyk" and mode != "CMYK":
        issues.append({"level": "warn", "text": f"File {mode}, the printer wants CMYK: colours may shift (especially neon / "
                                                "bright blue-green). Export in CMYK or get a proof from the printer."})
    if mode in ("RGBA", "LA", "P") and ("A" in mode or "transparency" in im.info):
        issues.append({"level": "warn", "text": "The file has transparency: flatten it on a white / coloured background for print."})
    if spec.get("file") == "pdf":
        issues.append({"level": "info", "text": "The printer wants a PDF: if possible send a PDF export (text stays vector)."})
    return {"ok": not any(i["level"] == "block" for i in issues), "issues": issues, "px": [w, h], "dpi": eff, "mode": mode,
            "kind": "image"}


def preflight_pdf(data: bytes, spec: dict[str, Any]) -> dict[str, Any]:
    """Her PDF: page size vs trim + bleed, TrimBox / BleedBox, fonts embedded, RGB images, PDF/X output intent."""
    try:
        import pikepdf
    except ImportError:
        return {"ok": True, "issues": [{"level": "info", "text": "The PDF check tool is not on the server; get a proof from the printer."}],
                "kind": "pdf"}
    issues: list[dict[str, str]] = []
    try:
        pdf = pikepdf.open(io.BytesIO(data))
    except pikepdf.PasswordError:
        return {"ok": False, "issues": [{"level": "block", "text": "The PDF has a password: the printer needs a file without one."}],
                "kind": "pdf"}
    except Exception:
        return {"ok": False, "issues": [{"level": "block", "text": "The PDF does not open (damaged file?)."}], "kind": "pdf"}
    pages = len(pdf.pages)
    unembedded: set[str] = set()
    rgb_images = 0
    sizes = []
    with pdf:
        for pg in pdf.pages:
            mb = [float(x) for x in pg.mediabox]
            wmm, hmm = _mm(mb[2] - mb[0]), _mm(mb[3] - mb[1])
            fit = _size_fit(wmm, hmm, spec)
            if not fit and "/TrimBox" in pg.obj:
                tb = [float(x) for x in pg.obj.TrimBox]
                tfit = _size_fit(_mm(tb[2] - tb[0]), _mm(tb[3] - tb[1]), spec)
                if tfit.startswith("trim"):
                    fit = "bleed"      # media bigger than trim, trim box right = bleed / marks present
            sizes.append((round(wmm, 1), round(hmm, 1), fit))
            res = pg.obj.get("/Resources") or {}
            fonts = res.get("/Font") or {}
            for _n, f in (fonts.items() if hasattr(fonts, "items") else []):
                try:
                    desc = f.get("/FontDescriptor")
                    if desc is None and f.get("/DescendantFonts") is not None:
                        desc = f.DescendantFonts[0].get("/FontDescriptor")
                    sub = str(f.get("/Subtype") or "")
                    if sub == "/Type3":
                        continue
                    if desc is None or not any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                        unembedded.add(str(f.get("/BaseFont") or "?").lstrip("/"))
                except Exception:
                    continue
            xo = res.get("/XObject") or {}
            for _n, x in (xo.items() if hasattr(xo, "items") else []):
                try:
                    if x.get("/Subtype") == "/Image" and str(x.get("/ColorSpace") or "") in ("/DeviceRGB", "/CalRGB"):
                        rgb_images += 1
                except Exception:
                    continue
        has_x = "/OutputIntents" in pdf.Root
    if any(not f for _w, _h, f in sizes):
        w, h, _ = sizes[0]
        tw, th = spec["mm"]
        issues.append({"level": "block", "text": f"Page size is {w:g} x {h:g} mm; need {tw:g} x {th:g} mm + "
                                                 f"{spec['bleed']:g} mm bleed on every side."})
    elif spec["bleed"] and all(f.startswith("trim") for _w, _h, f in sizes):
        issues.append({"level": "block", "text": f"No bleed: the page is only the trim size; add {spec['bleed']:g} mm bleed on every side."})
    if unembedded:
        issues.append({"level": "block", "text": f"Fonts not embedded: {', '.join(sorted(unembedded))[:160]}. In the export choose 'embed all "
                                                 "fonts' or outline the text."})
    if spec.get("color") == "cmyk" and rgb_images:
        issues.append({"level": "warn", "text": f"{rgb_images} photos are RGB; the printer wants CMYK (colours may shift a little)."})
    if spec.get("pdfx") and not has_x:
        issues.append({"level": "warn", "text": "The printer wants PDF/X: choose PDF/X-1a in the export."})
    return {"ok": not any(i["level"] == "block" for i in issues), "issues": issues, "pages": pages, "sizes": sizes,
            "fonts_unembedded": sorted(unembedded), "rgb_images": rgb_images, "pdfx": has_x, "kind": "pdf"}


def preflight(data: bytes, name: str, spec: dict[str, Any]) -> dict[str, Any]:
    if not spec:
        return {"ok": True, "issues": [], "kind": "none"}
    if data[:5] == b"%PDF-":
        return preflight_pdf(data, spec)
    return preflight_image(data, spec)


# ---------------------------------------------------------------- licences: fonts and assets
FONT_LICENCES = {
    "ofl": ("Open Font License (Google Fonts)", "share"),
    "apache": ("Apache (Google Fonts)", "share"),
    "adobe_fonts": ("Adobe Fonts (subscription)", "no_files"),
    "commercial": ("Purchased font (your licence)", "no_files"),
    "system": ("Font that came with Windows / Mac", "no_files"),
    "free_personal": ("Free for personal use only", "blocked"),
    "unknown": ("Licence unknown", "unknown"),
}
ASSET_LICENCES = {
    "own": "Made / photographed by you",
    "client": "Given by the client (their responsibility)",
    "stock_paid": "Purchased stock (licence number)",
    "stock_free": "Free stock (check terms / attribution)",
    "ai": "Made with AI (label needed)",
    "unknown": "Source unknown",
}


def font_kind(name: str, source: str = "") -> str:
    t = f"{name} {source}".lower()
    if re.search(r"personal use|for personal|demo|dafont|non.?commercial", t):
        return "free_personal"
    if re.search(r"adobe ?fonts|typekit", t):
        return "adobe_fonts"
    if re.search(r"google ?fonts|fonts\.google|\bofl\b|open font", t):
        return "ofl"
    if re.search(r"apache", t):
        return "apache"
    if re.search(r"bought|kharid|licen[cs]e|myfonts|fontshare pro|commercial", t):
        return "commercial"
    if re.search(r"\b(arial|calibri|times new roman|verdana|segoe|helvetica|mangal|nirmala|georgia|cambria)\b", t):
        return "system"
    return "unknown"


def asset_verdict(a: dict[str, Any]) -> dict[str, str]:
    """What this font / picture means for client work and handover."""
    kind = a.get("kind") or "font"
    lic = a.get("licence") or ""
    if kind == "font":
        lic = lic if lic in FONT_LICENCES else font_kind(a.get("name", ""), a.get("source", ""))
        label, rule = FONT_LICENCES[lic]
        say = {"share": "You can give the font file to the client (include the licence file).",
               "no_files": "You can NOT give the font file to the client: embed / outline it in the PDF / PNG; if the client edits, "
                           "they need their own licence.",
               "blocked": "Not allowed in client work: it is a 'personal use only' font. Choose another font or buy a commercial licence.",
               "unknown": "Find out the licence first (source / EULA): do not give the final to the client without it."}[rule]
        level = "block" if rule in ("blocked", "unknown") else "ok"
        return {"licence": lic, "label": label, "rule": rule, "say": say, "level": level}
    lic = lic if lic in ASSET_LICENCES else "unknown"
    say = {"own": "Fine.", "client": "Given by the client: get it in writing that they own the rights.",
           "stock_paid": "Keep the licence number / invoice; some licences limit print copies / resale.",
           "stock_free": "Read the terms: attribution may be needed / logo-trademark use may be banned.",
           "ai": "Made with AI: a 'Made with AI' label / telling the client is needed (IT Rules 2026); AI art in a logo can cause trade-mark trouble.",
           "unknown": "Source unknown: confirm the rights before the final to the client, or remove it."}[lic]
    level = "block" if lic == "unknown" else ("warn" if lic in ("stock_free", "ai", "client") else "ok")
    if lic == "stock_paid" and not (a.get("licence_ref") or "").strip():
        level, say = "warn", "Write the licence number / invoice (proof is needed later)."
    return {"licence": lic, "label": ASSET_LICENCES[lic], "rule": lic, "say": say, "level": level}


# ---------------------------------------------------------------- trademark help (logo jobs)
NICE: list[tuple[int, str, str]] = [
    (3, "Cosmetics, soap, incense sticks", r"cosmetic|beauty|soap|sabun|perfume|agarbatti|herbal"),
    (5, "Medicines, ayurvedic, health products", r"pharma|medicine|dawai|ayurved|medical store|chemist|supplement"),
    (9, "Software, app, electronics", r"software|app\b|mobile|electronic|computer|it services|saas"),
    (14, "Jewellery, watches", r"jewel|gehne|sona|gold|silver|watch"),
    (16, "Books, stationery, printing", r"book|stationery|print|kitaab|publication"),
    (18, "Bag, leather", r"\bbag|leather|purse"),
    (25, "Clothes, shoes", r"cloth|garment|kapde|saree|kurti|fashion|boutique|shoe|joote|apparel"),
    (29, "Milk, ghee, pickles, snacks", r"dairy|doodh|ghee|paneer|achaar|pickle|namkeen|oil"),
    (30, "Tea, spices, sweets, bakery", r"tea|chai|coffee|masala|spice|bakery|cake|mithai|sweet|atta|rice"),
    (32, "Water, juice, cold drinks", r"water|juice|beverage|soda|drink"),
    (35, "Shop / retail / advertising", r"shop|store|retail|dukaan|mart|trading|advertis|marketing|agency"),
    (36, "Finance, insurance, real estate", r"finance|insurance|bima|loan|real estate|property|broker"),
    (37, "Construction, repair", r"construct|builder|repair|contractor|plumb|electrician"),
    (38, "Telecom, internet, broadband", r"telecom|internet|broadband|isp|fiber|fibre|cable"),
    (39, "Transport, travel, courier", r"transport|travel|courier|logistic|cab|taxi|tour"),
    (41, "Education, coaching, events, gym", r"education|school|coaching|academy|class|tuition|event|gym|fitness|training"),
    (42, "Design, IT development", r"design studio|web develop|architect|it develop|tech"),
    (43, "Restaurant, cafe, hotel", r"restaurant|cafe|hotel|dhaba|food|catering|bakery cafe|resort"),
    (44, "Clinic, salon, hospital", r"clinic|hospital|doctor|dental|salon|parlour|spa|beauty parlour"),
    (45, "Legal, security, personal services", r"legal|lawyer|advocate|security|matrimon"),
]
TM_SEARCH = "https://tmrsearch.ipindia.gov.in/"
TM_PORTAL = "https://ipindiaonline.gov.in/"


def nice_classes(text: str) -> list[dict[str, Any]]:
    t = (text or "").lower()
    out = [{"class": n, "label": lab} for n, lab, pat in NICE if re.search(pat, t)]
    return out[:4]


def tm_help(name: str, business: str, classes: list[int] | None = None) -> dict[str, Any]:
    cls = [{"class": c, "label": next((lab for n, lab, _p in NICE if n == c), "")} for c in (classes or [])] or nice_classes(business)
    steps = [f"{TM_SEARCH} open it (IP India's official public search; you fill the CAPTCHA).",
             f"Wordmark search: '{name}' - both 'Start with' and 'Contains', class {', '.join(str(c['class']) for c in cls) or '[class?]'}.",
             "Phonetic search: the same name by similar pronunciation.",
             "Vienna Code search: find similar logos by the code of the logo's symbol (like star, lion, leaf).",
             "Write what you found (registered / objected / abandoned) here: Hoola keeps it on the job."]
    return {"name": name, "classes": cls, "steps": steps, "links": [TM_SEARCH, TM_PORTAL],
            "note": "This is only a check, not clearance: a trade-mark lawyer / agent gives the firm opinion. Hoola does not open the site itself."}


# ---------------------------------------------------------------- brief checks
CLONE = re.compile(r"(copy|clone|same as|hubahu|bilkul (waisa|same)|jaisa hi|duplicate|exact)\W+(\w+\W+){0,4}?(logo|design|packaging|label)"
                   r"|(logo|design|packaging|label)\W+(\w+\W+){0,4}?(copy|clone|same|hubahu|duplicate)", re.I)


def clone_problem(text: str) -> str:
    if CLONE.search(text or ""):
        return ("Copying another brand's logo / design exactly breaks copyright and trade-mark law: Hoola only makes "
                "original designs (inspiration yes, copies no).")
    return ""


def kind_of(text: str) -> str:
    t = (text or "").lower()
    for k, pat in KIND_WORDS:
        if re.search(pat, t):
            return k
    return "other"


# ---------------------------------------------------------------- money: GST + TDS notes
STATE_CODES = {"MH": "27", "GA": "30", "GJ": "24", "KA": "29", "DL": "07", "TN": "33", "TS": "36", "AP": "37", "MP": "23",
               "RJ": "08", "UP": "09", "WB": "19", "KL": "32", "PB": "03", "HR": "06", "BR": "10", "OD": "21", "CG": "22"}


def state_of(gstin: str = "", state: str = "") -> str:
    g = (gstin or "").strip().upper()
    if re.fullmatch(r"\d{2}[A-Z0-9]{13}", g):
        return g[:2]
    s = (state or "").strip().upper()
    if re.fullmatch(r"\d{2}", s):
        return s
    return STATE_CODES.get(s[:2], "") if s else ""


def gstin_ok(g: str) -> bool:
    g = (g or "").strip().upper()
    if not g:
        return True
    try:
        from ..india.money import gstin_ok as ok
        return bool(ok(g))
    except Exception:
        return bool(re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]", g))


def gst_lines(subtotal: float, rate: float, her_state: str, client_state: str, export: bool = False,
              lut: bool = False) -> dict[str, Any]:
    if rate <= 0:
        return {"kind": "none", "tax": 0.0, "rows": []}
    if export:
        if lut:
            return {"kind": "export_lut", "tax": 0.0, "rows": [],
                    "note": "Export of services under LUT, no IGST (zero-rated)."}
        t = round(subtotal * rate / 100, 2)
        return {"kind": "igst", "tax": t, "rows": [{"name": f"IGST {rate:g}%", "amount": t}]}
    if her_state and client_state and her_state != client_state:
        t = round(subtotal * rate / 100, 2)
        return {"kind": "igst", "tax": t, "rows": [{"name": f"IGST {rate:g}%", "amount": t}]}
    half = round(subtotal * rate / 200, 2)
    return {"kind": "cgst_sgst", "tax": round(half * 2, 2),
            "rows": [{"name": f"CGST {rate / 2:g}%", "amount": half}, {"name": f"SGST {rate / 2:g}%", "amount": half}]}


def tds_note(client_kind: str, tds_pct: float | None, fee: float) -> str:
    if client_kind != "business":
        return "The client is an individual: usually no TDS is deducted."
    if tds_pct is None:
        return ("A business client may deduct TDS (Income-tax Act 2025 s.393(1): professional / technical 10% / 2% above Rs 50,000 "
                "a year, or contract 1% / 2%): ask the client how much they will deduct and write it; Hoola does not guess.")
    return f"The client gave {tds_pct:g}% TDS: ~₹{fee * tds_pct / 100:,.0f} will be deducted; match it in Form 26AS / AIS."


# ---------------------------------------------------------------- copyright assignment
def assignment_text(designer: str, client: str, work: str, rights: str = "", years: int | None = None, territory: str = "",
                    consideration: str = "") -> dict[str, Any]:
    """Plain draft of a written assignment (Copyright Act s.18-19). Blanks stay blanks; a lawyer should read it."""
    yrs = f"{years} years" if years else "[write the period - if left out the law assumes 5 years, s.19(5)]"
    terr = territory or "[write the territory - if left out only India, s.19(6)]"
    rights = rights or "the right to print, use digitally, adapt and register as a trade-mark"
    cons = consideration or "[amount / invoice number]"
    body = (f"I, {designer or '[designer name]'} (\"Assignor\"), assign the copyright of the work below to {client or '[client name]'} "
            f"(\"Assignee\").\n\nWork: {work or '[work]'}\nRights given: {rights}\nPeriod: {yrs}\nTerritory: {terr}\n"
            f"In return: {cons}\n\nThis assignment takes effect on full payment. Even if the Assignee does not use the rights within a year, "
            "it will not lapse (despite s.19(4), by agreement of both). Moral rights (s.57) stay with the Assignor; "
            "the Assignor may show the work in their portfolio unless the client refuses.\n\n"
            "Assignor's signature: ______________   Date: ________\nAssignee's signature: ______________   Date: ________")
    blanks = re.findall(r"\[[^\]]{1,120}\]", body)
    return {"text": body, "blanks": blanks,
            "note": "Copyright Act 1957 s.19: an assignment is valid only in writing and signed. This is a draft: have a lawyer check it."}


# ---------------------------------------------------------------- small helpers
def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 2000) -> str:
    """Client / her words: secrets never kept (OTP / PIN / password values, card- and Aadhaar-like numbers)."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin|passcode)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [removed]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[removed]", t)
    return t.strip()[:n]


def phone(text: Any) -> str:
    d = re.sub(r"\D", "", str(text or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def hex_to_cmyk(h: str) -> tuple[int, int, int, int]:
    """Plain maths RGB -> CMYK (no ICC profile): a starting point only; the printer's proof decides."""
    h = (h or "#000000").lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    k = 1 - max(r, g, b)
    if k >= 1:
        return 0, 0, 0, 100
    c, m, y = ((1 - x - k) / (1 - k) for x in (r, g, b))
    return round(c * 100), round(m * 100), round(y * 100), round(k * 100)
