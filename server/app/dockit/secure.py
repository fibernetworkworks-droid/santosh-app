"""D3 security: protect (AES-256 + permissions), unlock, TRUE redaction.

Passwords (plan law 4.4): a password never passes through the chat or the model. Hoola either makes a strong one
and shows it ONLY on a one-time page (vault.py / api.py), or she types her own on that page. Unlocking an
open-password PDF happens on the same kind of page; 5 wrong tries and the page closes - nothing is ever guessed.

Redaction (plan law 4.3): every page that holds something to remove is REDRAWN as a picture with the black boxes
burned in, so the words, their hidden copies and anything under them leave the file; pages with nothing to remove
keep their text. Then the whole file is read again and every found thing must be gone, or nothing is delivered.
Found by pattern AND checksum where one exists (Aadhaar Verhoeff, card Luhn, GSTIN check character) - never guessed."""
from __future__ import annotations

import io
import re
import secrets
from typing import Any

from . import core, stamp
from .core import DocError

# ------------------------------------------------------------------------------------------------- protect
PERMS = ("print", "copy", "edit", "comment", "fill_forms", "assemble", "accessibility")
_ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"


def make_password() -> str:
    """14 characters in 3 groups, upper + lower + digit + '-': easy to read aloud, never generated twice."""
    while True:
        raw = "".join(secrets.choice(_ALPHA) for _ in range(12))
        pw = f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"
        if any(c.isupper() for c in raw) and any(c.islower() for c in raw) and any(c.isdigit() for c in raw):
            return pw


def password_problem(pw: str) -> str:
    if len(pw or "") < 8:
        return "At least 8 characters."
    if len(pw) > 64:
        return "At most 64 characters."
    kinds = sum([any(c.islower() for c in pw), any(c.isupper() for c in pw), any(c.isdigit() for c in pw),
                 any(not c.isalnum() for c in pw)])
    if kinds < 3:
        return "Use at least three of: small letters, capital letters, numbers, symbols."
    return ""


def protect(data: bytes, password: str, allow: list[str] | None = None, open_lock: bool = True) -> bytes:
    """AES-256 (PDF 2.0 revision 6). open_lock=False = no password to open, only the restrictions (said: viewers
    honour restrictions, but they are not a real lock). allow = what stays permitted (default: print + copy)."""
    import pikepdf
    allow = [a for a in (allow if allow is not None else ["print", "copy", "accessibility"]) if a]
    bad = [a for a in allow if a not in PERMS]
    if bad:
        raise DocError(f"allow = some of {', '.join(PERMS)} (not {', '.join(bad)}).")
    if open_lock and password_problem(password):
        raise DocError(password_problem(password))
    perms = pikepdf.Permissions(
        print_lowres="print" in allow, print_highres="print" in allow, extract="copy" in allow,
        modify_other="edit" in allow, modify_annotation="comment" in allow, modify_form="fill_forms" in allow,
        modify_assembly="assemble" in allow, accessibility=True)
    owner = make_password() + make_password()               # nobody needs it: Hoola never shows it
    with core.open_pdf(data) as pdf:
        buf = io.BytesIO()
        pdf.save(buf, encryption=pikepdf.Encryption(owner=owner, user=password if open_lock else "", R=6,
                                                     allow=perms, aes=True, metadata=True))
        return buf.getvalue()


def check_protected(data: bytes, password: str, open_lock: bool, allow: list[str]) -> list[str]:
    import pikepdf
    said = []
    if open_lock:
        try:
            pikepdf.open(io.BytesIO(data)).close()
            raise DocError("Check failed: the file opened WITHOUT the password; nothing was delivered.")
        except pikepdf.PasswordError:
            said.append("will not open without the password")
    with pikepdf.open(io.BytesIO(data), password=password if open_lock else "") as p:
        al = p.allow
        if ("print" in allow) != bool(al.print_highres) or ("copy" in allow) != bool(al.extract):
            raise DocError("Check failed: the permissions did not read back as set; nothing was delivered.")
        said.append(f"opens with the password, {len(p.pages)} pages" if open_lock else "restrictions read back as set")
    return said


def unlock(data: bytes, password: str = "") -> tuple[bytes, str]:
    """Restrictions only (opens without a password) -> removed. An open password -> only with HER password, typed
    on the one-time page; a wrong one is said, never retried by guessing."""
    import pikepdf
    core.check_size(data)
    try:
        pdf = pikepdf.open(io.BytesIO(data), password=password or "")
    except pikepdf.PasswordError:
        if not password:
            raise NeedsPassword()
        raise DocError("That password is not right for this PDF.")
    with pdf:
        if not pdf.is_encrypted:
            return core.save(pdf), "none"
        kind = "open password" if password else "restrictions"
        buf = io.BytesIO()
        pdf.save(buf)                      # no encryption= -> saved without any
        return buf.getvalue(), kind


class NeedsPassword(DocError):
    def __init__(self):
        super().__init__("This PDF needs its open password. She types it on a one-time page (never in chat).")


# ------------------------------------------------------------------------------------------------- detectors
_VERHOEFF_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
               [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
               [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
               [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_VERHOEFF_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
               [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
               [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]


def verhoeff_ok(num: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def luhn_ok(num: str) -> bool:
    total, alt = 0, False
    for ch in reversed(num):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


_GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_ok(g: str) -> bool:
    g = g.upper()
    if len(g) != 15:
        return False
    total = 0
    for i, ch in enumerate(g[:14]):
        v = _GST_CHARS.index(ch) * (2 if i % 2 else 1)
        total += v // 36 + v % 36
    return _GST_CHARS[(36 - total % 36) % 36] == g[14]


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


PRESETS: dict[str, dict[str, Any]] = {
    "aadhaar": {"re": r"(?<!\d)[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)", "ok": lambda s: verhoeff_ok(_digits(s)),
                "label": "Aadhaar number"},
    "vid": {"re": r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)", "ok": lambda s: verhoeff_ok(_digits(s)),
            "label": "Aadhaar VID"},
    "pan": {"re": r"(?<![A-Z0-9])[A-Z]{3}[PCHFATBLJG][A-Z]\d{4}[A-Z](?![A-Z0-9])", "ok": None, "label": "PAN"},
    "phone": {"re": r"(?<![\d+])(?:\+?91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}(?!\d)", "ok": None, "label": "phone number"},
    "email": {"re": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "ok": None, "label": "email"},
    "card": {"re": r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)", "ok": lambda s: 13 <= len(_digits(s)) <= 19 and luhn_ok(_digits(s)),
             "label": "card number"},
    "ifsc": {"re": r"(?<![A-Z0-9])[A-Z]{4}0[A-Z0-9]{6}(?![A-Z0-9])", "ok": None, "label": "IFSC"},
    "account": {"re": r"(?i)(?:a/?c|acct|account|खाता)[^\d\n]{0,20}(\d[\d -]{7,20}\d)", "ok": None, "group": 1,
                "label": "bank account number"},
    "gstin": {"re": r"(?<![A-Z0-9])\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z](?![A-Z0-9])", "ok": gstin_ok,
              "label": "GSTIN"},
    "vehicle": {"re": r"(?<![A-Z0-9])[A-Z]{2}[ -]?\d{1,2}[ -]?[A-Z]{1,3}[ -]?\d{4}(?!\d)", "ok": None,
                "label": "vehicle number"},
    "pincode": {"re": r"(?i)(?:pin(?:\s*code)?|पिन)[\s:.-]{0,4}([1-9]\d{2}\s?\d{3})(?!\d)", "ok": None, "group": 1,
                "label": "PIN code"},
}
DEFAULT_PRESETS = ("aadhaar", "vid", "pan", "card", "account", "phone", "email")


def mask(s: str) -> str:
    """What she sees in the list: enough to recognise it, never the whole thing."""
    t = s.strip()
    if "@" in t:
        a, _, d = t.partition("@")
        return (a[:1] + "***@" + d) if a else "***@" + d
    keep = 4 if len(re.sub(r"\W", "", t)) > 6 else 2
    shown, out = 0, []
    for ch in reversed(t):
        if ch.isalnum() and shown < keep:
            out.append(ch)
            shown += 1
        elif ch.isalnum():
            out.append("X")
        else:
            out.append(ch)
    return "".join(reversed(out))


# ------------------------------------------------------------------------------------------------- finding
def _page_chars(tp) -> tuple[str, int]:
    import pypdfium2.raw as R
    n = tp.count_chars()
    return "".join(chr(R.FPDFText_GetUnicode(tp.raw, i) or 32) for i in range(n)), n


def _boxes_for(tp, start: int, end: int) -> list[tuple[float, float, float, float]]:
    lines: dict[int, list[float]] = {}
    for ci in range(start, end):
        try:
            l, b, r, t = tp.get_charbox(ci)
        except Exception:
            continue
        if r <= l or t <= b:
            continue
        key = round(b / 3)
        box = lines.setdefault(key, [l, b, r, t])
        box[0], box[1], box[2], box[3] = min(box[0], l), min(box[1], b), max(box[2], r), max(box[3], t)
    return [tuple(v) for v in lines.values()]  # type: ignore[misc]


def find(data: bytes, presets: list[str] | None = None, terms: list[str] | None = None, pages: Any = "all",
         match_case: bool = False) -> dict[str, Any]:
    """-> {hits: [{page, kind, label, text, masked, boxes}], scanned_pages: [...], pages}."""
    import pypdfium2 as pdfium
    presets = list(presets if presets is not None else DEFAULT_PRESETS)
    bad = [p for p in presets if p not in PRESETS]
    if bad:
        raise DocError(f"presets = some of {', '.join(PRESETS)} (not {', '.join(bad)}).")
    terms = [str(t).strip() for t in (terms or []) if str(t).strip()]
    if any(len(t) < 2 for t in terms):
        raise DocError("Each word to remove needs 2 letters or more.")
    if not presets and not terms:
        raise DocError("Say what to remove: presets (aadhaar, pan, phone...) and / or words to find.")
    core.check_size(data)
    hits: list[dict[str, Any]] = []
    scanned: list[int] = []
    doc = pdfium.PdfDocument(data)
    try:
        idx = core.pages(pages or "all", len(doc))
        for i in idx:
            page = doc[i]
            tp = page.get_textpage()
            try:
                text, n = _page_chars(tp)
                if not text.strip():
                    scanned.append(i + 1)
                    continue
                spans: list[tuple[int, int, str, str]] = []
                for kind in presets:
                    p = PRESETS[kind]
                    for m in re.finditer(p["re"], text):
                        g = p.get("group", 0)
                        s0, s1 = m.span(g)
                        val = m.group(g)
                        if p["ok"] and not p["ok"](val):
                            continue
                        spans.append((s0, s1, kind, val))
                for t in terms:
                    flags = 0 if match_case else re.I
                    for m in re.finditer(re.escape(t).replace(r"\ ", r"\s+"), text, flags):
                        spans.append((m.start(), m.end(), "words", m.group(0)))
                spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
                last_end = -1
                for s0, s1, kind, val in spans:
                    if s0 < last_end:                     # inside a hit already found (a card inside a VID etc.)
                        continue
                    last_end = s1
                    boxes = _boxes_for(tp, s0, s1)
                    if not boxes:
                        continue
                    hits.append({"page": i + 1, "kind": kind, "label": PRESETS[kind]["label"] if kind in PRESETS
                                 else "words", "text": val, "masked": mask(val), "boxes": boxes})
            finally:
                tp.close()
                page.close()
    finally:
        doc.close()
    return {"hits": hits, "scanned_pages": scanned, "pages": len(idx)}


def area_boxes(data: bytes, areas: list[dict]) -> list[dict[str, Any]]:
    """Boxes she drew (mm / % from the top-left of what she sees) -> hits in the page's own space."""
    from .edit import _len, from_visual
    out = []
    with core.open_pdf(data) as pdf:
        n = len(pdf.pages)
        for a in areas or []:
            for i in core.pages(a.get("page") or 1, n):
                f = stamp.frame(pdf.pages[i])
                X, top = _len(a.get("x"), f["vw"]), _len(a.get("y"), f["vh"])
                w, h = _len(a.get("w"), f["vw"], 50 * stamp.MM), _len(a.get("h"), f["vh"], 10 * stamp.MM)
                p1, p2 = from_visual(f, X, f["vh"] - top - h), from_visual(f, X + w, f["vh"] - top)
                out.append({"page": i + 1, "kind": "area", "label": "area she marked", "text": "", "masked": "area",
                            "boxes": [(min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))]})
    return out


def summary(hits: list[dict]) -> list[dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    for h in hits:
        row = by.setdefault(h["label"], {"what": h["label"], "count": 0, "pages": set(), "examples": []})
        row["count"] += 1
        row["pages"].add(h["page"])
        if len(row["examples"]) < 3 and h["masked"] not in row["examples"]:
            row["examples"].append(h["masked"])
    return [{**v, "pages": sorted(v["pages"])} for v in by.values()]


def preview(data: bytes, hits: list[dict]) -> bytes:
    """A copy with every box outlined in red + 'PREVIEW - NOT REDACTED' on each page (nothing removed)."""
    by: dict[int, list] = {}
    for h in hits:
        by.setdefault(h["page"] - 1, []).extend(h["boxes"])
    with core.open_pdf(data) as pdf:
        keep: list = []
        for i, page in enumerate(pdf.pages):
            f = stamp.frame(page)
            boxes = by.get(i, [])

            def draw(c, w, h, boxes=boxes, f=f):
                c.setStrokeColorRGB(0.85, 0.1, 0.1)
                c.setFillColorRGB(0.85, 0.1, 0.1)
                c.setFillAlpha(0.18)
                c.setLineWidth(1.4)
                for (l, b, r, t) in boxes:
                    p1, p2 = stamp.to_visual(f, l, b), stamp.to_visual(f, r, t)
                    x0, y0 = min(p1[0], p2[0]), min(p1[1], p2[1])
                    c.rect(x0 - 1.5, y0 - 1.5, abs(p2[0] - p1[0]) + 3, abs(p2[1] - p1[1]) + 3, stroke=1, fill=1)
                c.setFillAlpha(0.9)
                stamp.draw_text(c, w / 2, 10, "PREVIEW - NOTHING REMOVED YET" + (f" - {len(boxes)} to remove" if boxes
                                                                                 else ""), 9, True, "center")
            stamp.layer(pdf, page, draw, keep=keep)
        out = core.save(pdf)
        for s in keep:
            s.close()
        return out


# ------------------------------------------------------------------------------------------------- redact
def redact(data: bytes, hits: list[dict], dpi: int = 200, terms: list[str] | None = None,
           presets: list[str] | None = None) -> dict[str, Any]:
    """Burn the boxes in: every page with a box is redrawn as a picture (text, hidden copies and anything under the
    box gone); other pages keep their text. Comments / bookmarks / form values carrying a found thing are removed,
    metadata + attachments + scripts are stripped. Then everything is read again: any found thing still present =
    nothing delivered."""
    import pikepdf
    import pypdfium2 as pdfium
    from PIL import ImageDraw
    from . import edit
    if not hits:
        raise DocError("Nothing to redact was found or marked.")
    dpi = max(150, min(300, int(dpi or 200)))
    by: dict[int, list] = {}
    for h in hits:
        by.setdefault(h["page"] - 1, []).extend(h["boxes"])
    secrets_found = sorted({h["text"] for h in hits if h["text"]}, key=len, reverse=True)
    # 1) the redrawn pages, as one-page PDFs (pictures with the boxes burned in)
    pdfdoc = pdfium.PdfDocument(data)
    redrawn: dict[int, bytes] = {}
    try:
        for i, boxes in by.items():
            page = pdfdoc[i]
            try:
                vw, vh = page.get_size()                   # pypdfium2 = the size she sees (rotation applied)
                sc = dpi / 72
                im = page.render(scale=sc, may_draw_forms=True, draw_annots=False).to_pil().convert("RGB")
            finally:
                page.close()
            with pikepdf.open(io.BytesIO(data)) as pk:
                f = stamp.frame(pk.pages[i])
            dr = ImageDraw.Draw(im)
            for (l, b, r, t) in boxes:
                p1, p2 = stamp.to_visual(f, l, b), stamp.to_visual(f, r, t)
                x0, x1 = sorted((p1[0], p2[0]))
                y0, y1 = sorted((p1[1], p2[1]))
                pad = 1.5
                dr.rectangle([(x0 - pad) * sc, (vh - y1 - pad) * sc, (x1 + pad) * sc, (vh - y0 + pad) * sc], fill=(0, 0, 0))
            b = io.BytesIO()
            im.save(b, "JPEG", quality=88)
            redrawn[i] = _picture_page(b.getvalue(), vw, vh)
    finally:
        pdfdoc.close()
    # 2) swap them in, strip what can carry a copy elsewhere
    keep: list = []
    with core.open_pdf(data) as pdf:
        for i, blob in redrawn.items():
            src = pikepdf.open(io.BytesIO(blob))
            keep.append(src)
            pdf.pages[i] = src.pages[0]
        removed_notes = 0
        for page in pdf.pages:
            annots = page.obj.get("/Annots")
            if annots is None:
                continue
            kept = pikepdf.Array()
            for a in annots:
                blob = " ".join(str(a.get(k, "")) for k in ("/Contents", "/T", "/V", "/TU"))
                if any(_present(s, blob) for s in secrets_found):
                    removed_notes += 1
                    continue
                kept.append(a)
            page.obj.Annots = kept
        _scrub_outline(pdf, secrets_found)
        for k in ("/AcroForm",):
            if k in pdf.Root:
                af = pdf.Root[k]
                vals = " ".join(str(fld.get("/V", "")) for fld in af.get("/Fields", []))
                if any(_present(s, vals) for s in secrets_found):
                    del pdf.Root[k]
        out = core.save(pdf)
    for s in keep:
        s.close()
    clean, stripped = edit.sanitize(out)
    ocr_pages: list[int] = []
    try:                                                # the kept words on redrawn pages become searchable again
        from . import ocrlayer
        if ocrlayer.ready():
            r = ocrlayer.searchable(clean, "", ",".join(str(p + 1) for p in sorted(redrawn)), auto_rotate=False)
            clean, ocr_pages = r["bytes"], r["done"]
    except Exception:
        ocr_pages = []
    # 3) the proof: read it all again (the text layer too)
    left = verify(clean, secrets_found, presets or [])
    if left:
        raise DocError(f"Check failed: {len(left)} found item(s) could still be read after redaction ({', '.join(mask(x) for x in left[:3])}); "
                       "nothing was delivered.")
    return {"bytes": clean, "pages_redrawn": sorted(p + 1 for p in redrawn), "boxes": sum(len(v) for v in by.values()),
            "comments_removed": removed_notes, "stripped": stripped, "text_layer_pages": ocr_pages}


def _present(secret: str, blob: str) -> bool:
    a, b = re.sub(r"[\s-]", "", secret).lower(), re.sub(r"[\s-]", "", blob).lower()
    return bool(a) and a in b


def _scrub_outline(pdf, found: list[str]) -> None:
    try:
        with pdf.open_outline() as ol:
            def walk(items):
                for it in list(items):
                    if any(_present(s, str(it.title or "")) for s in found):
                        items.remove(it)
                    else:
                        walk(it.children)
            walk(ol.root)
    except Exception:
        pass


def _picture_page(jpeg: bytes, w: float, h: float) -> bytes:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.drawImage(ImageReader(io.BytesIO(jpeg)), 0, 0, w, h)
    c.showPage()
    c.save()
    return buf.getvalue()


def verify(data: bytes, found: list[str], presets: list[str]) -> list[str]:
    """Everything still readable that should be gone: page text, comments, bookmarks, form values, metadata."""
    import pikepdf
    from . import convert
    blob = "\n".join(convert.page_texts(data))
    with pikepdf.open(io.BytesIO(data)) as p:
        for page in p.pages:
            for a in page.obj.get("/Annots", []) or []:
                blob += " " + " ".join(str(a.get(k, "")) for k in ("/Contents", "/T", "/V"))
        if p.docinfo:
            blob += " " + " ".join(str(v) for v in p.docinfo.values())
        try:
            with p.open_outline() as ol:
                blob += " " + " ".join(str(x.title) for x in ol.root)
        except Exception:
            pass
    left = [s for s in found if _present(s, blob)]
    for kind in presets:
        pr = PRESETS.get(kind)
        if not pr:
            continue
        for m in re.finditer(pr["re"], blob):
            val = m.group(pr.get("group", 0))
            if (not pr["ok"] or pr["ok"](val)) and val not in left:
                left.append(val)
    return left
