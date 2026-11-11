"""D0 PDF PROOF CARD (docs/DOCUMENT_KIT_PLAN.md): every document-kit action run on fixture files made HERE in code
(no real person's data), each result scored by code - pages, size, text, pictures - never by a model.

python -m app.quality pdf [--only id,id] [--json]     (free: no model, no network; vps-ops > pdf_card)
A case whose engine is not installed on this server is SKIPPED with the reason, never counted as a pass."""
from __future__ import annotations

import io
import time
from typing import Any, Callable

import pikepdf

from ..dockit import archive, convert, core, edit, forms, fromdoc, ocrlayer, optimize, organize, secure, sign, smart, stamp
from ..dockit.core import DocError


# ---------------------------------------------------------------------------------------------------- fixtures
def text_pdf(pages: int = 12, title: str = "Hoola fixture") -> bytes:
    from reportlab.pdfgen import canvas
    b = io.BytesIO()
    c = canvas.Canvas(b)
    for i in range(pages):
        c.setFont("Helvetica-Bold", 20)
        c.drawString(72, 770, f"{title} - page {i + 1}")
        c.setFont("Helvetica", 11)
        for k in range(30):
            c.drawString(72, 740 - k * 18, f"Line {k + 1}: invoice total Rs {1000 + i * 37 + k}, GSTIN check text.")
        c.showPage()
    c.save()
    return b.getvalue()


def noisy_photo(w: int = 2400, h: int = 1800, seed: int = 7) -> bytes:
    """A photo-like picture that JPEG cannot squeeze for free (random detail), saved at high quality."""
    import random
    from PIL import Image, ImageFilter
    rnd = random.Random(seed)
    small = Image.new("RGB", (w // 8, h // 8))
    small.putdata([(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)) for _ in range(small.width * small.height)])
    im = small.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=97)
    return b.getvalue()


def photo_pdf(pages: int = 4) -> bytes:
    return convert.images_to_pdf([(f"p{i}.jpg", noisy_photo(seed=i)) for i in range(pages)], page_size="a4")


def blank_separated() -> bytes:
    """3 documents (2 + 3 + 1 pages) with a blank sheet between them, like a batch scan."""
    import pikepdf as pk
    out = pk.new()
    keep = []
    for n in (2, 3, 1):
        src = pk.open(io.BytesIO(text_pdf(n, f"doc{n}")))
        keep.append(src)
        if len(out.pages):
            out.add_blank_page(page_size=(595, 842))
        out.pages.extend(src.pages)
    return core.save(out)


def locked_pdf() -> bytes:
    with pikepdf.open(io.BytesIO(text_pdf(2))) as p:
        b = io.BytesIO()
        p.save(b, encryption=pikepdf.Encryption(user="secret-user", owner="secret-owner"))
        return b.getvalue()


def broken_pdf() -> bytes:
    """A real PDF whose cross-reference table was cut off (a half-finished download)."""
    d = text_pdf(3)
    i = d.rfind(b"xref")
    return d[:i] + b"\n%%EOF\n"


def word_file() -> bytes:
    from docx import Document
    doc = Document()
    doc.add_heading("Hoola quotation", 1)
    doc.add_paragraph("Item one Rs 1,200. Item two Rs 3,400.")
    b = io.BytesIO()
    doc.save(b)
    return b.getvalue()


def form_pdf() -> bytes:
    """A fillable form (one text box, one tick box), filled in."""
    from reportlab.pdfgen import canvas
    b = io.BytesIO()
    c = canvas.Canvas(b)
    c.drawString(72, 760, "Name:")
    c.acroForm.textfield(name="name", x=120, y=745, width=200, height=20, value="Ramesh Kumar")
    c.acroForm.checkbox(name="agree", x=120, y=700, checked=True)
    c.showPage()
    c.save()
    return b.getvalue()


def risky_pdf() -> bytes:
    """JavaScript that runs on opening + a file attached inside."""
    with pikepdf.open(io.BytesIO(text_pdf(2))) as p:
        js = pikepdf.Dictionary(S=pikepdf.Name.JavaScript, JS=pikepdf.String("app.alert('hi')"))
        p.Root.OpenAction = p.make_indirect(js)
        p.attachments["notes.txt"] = pikepdf.AttachedFileSpec(p, b"secret attached notes", mime_type="text/plain")
        return core.save(p)


def logo_png() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGBA", (300, 120), (0, 160, 0, 255)).save(b, "PNG")
    return b.getvalue()


def ink(data: bytes, page: int, test, scale: float = 0.5) -> tuple[int, int, int, int, int] | None:
    """Pixels matching test(r, g, b) on a drawn page -> (count, x0, y0, x1, y1) in the picture (top-left origin)."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(data)
    try:
        im = doc[page - 1].render(scale=scale).to_pil().convert("RGB")
    finally:
        doc.close()
    px, W, H = im.load(), im.width, im.height
    pts = [(x, y) for y in range(0, H, 1) for x in range(0, W, 1) if test(*px[x, y])]
    if not pts:
        return None
    xs, ys = [a for a, _ in pts], [b for _, b in pts]
    return len(pts), min(xs) / W, min(ys) / H, max(xs) / W, max(ys) / H


def aadhaar_number() -> str:
    """A 12-digit number that passes the Aadhaar (Verhoeff) check, made here - not anyone's."""
    base = "23456789012"
    return next(base + str(d) for d in range(10) if secure.verhoeff_ok(base + str(d)))


def id_pdf() -> bytes:
    """Page 1: made-up Indian IDs; page 2: plain text; page 3: a scanned (picture) page."""
    from reportlab.pdfgen import canvas
    a = aadhaar_number()
    b = io.BytesIO()
    c = canvas.Canvas(b)
    c.drawString(72, 760, f"Name: Ramesh Kumar   Aadhaar: {a[:4]} {a[4:8]} {a[8:]}")
    c.drawString(72, 740, "PAN: ABCPE1234F   Mobile: +91 98765 43210   GSTIN: 27AAPFU0939F1ZV")
    c.drawString(72, 720, "Card 4111 1111 1111 1111   A/c No: 123456789012   ramesh@example.com")
    c.drawString(72, 700, "Order 2345 6789 0125 is not an Aadhaar number.")
    c.showPage()
    c.drawString(72, 760, "Page two: nothing private here.")
    c.showPage()
    c.save()
    scan = convert.images_to_pdf([("s.jpg", noisy_photo(600, 800, 9))], page_size="a4")
    return organize.merge([("ids.pdf", b.getvalue()), ("scan.pdf", scan)], bookmarks=False)


def scanned_text_pdf() -> bytes:
    """A 'scan': a picture of a printed page (English + Hindi), no text inside."""
    from PIL import Image, ImageDraw, ImageFont
    from pathlib import Path
    fonts = Path(__file__).resolve().parent.parent / "fonts"
    lat = ImageFont.truetype(str(fonts / "print" / "Inter.ttf"), 44)
    dev = ImageFont.truetype(str(fonts / "NotoSansDevanagari-Regular.ttf"), 44)
    im = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(im)
    d.text((110, 160), "Invoice from Sharma Traders", fill="black", font=lat)
    d.text((110, 260), "Total amount 4650 rupees", fill="black", font=lat)
    d.text((110, 360), "नमस्ते दुकान", fill="black", font=dev)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=90)
    return convert.images_to_pdf([("scan.jpg", b.getvalue())], page_size="a4")


def table_pdf(total: str = "4,650.50") -> bytes:
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
    b = io.BytesIO()
    ss = getSampleStyleSheet()
    rows = [["Item", "Qty", "Amount"], ["Atta", "2", "1,200.00"], ["Rice", "1", "3,450.50"], ["Total", "", total]]
    t = Table(rows)
    t.setStyle([("GRID", (0, 0), (-1, -1), 0.5, (0, 0, 0))])
    SimpleDocTemplate(b).build([Paragraph("Quotation 12", ss["Title"]),
                                Paragraph("This is the body text of the quotation for the shop.", ss["Normal"]),
                                Spacer(1, 12), t])
    return b.getvalue()


def embedded_font_pdf() -> bytes:
    from pathlib import Path
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    f = Path(__file__).resolve().parent.parent / "fonts" / "Poppins-Bold.ttf"
    pdfmetrics.registerFont(TTFont("CardPoppins", str(f)))
    b = io.BytesIO()
    c = canvas.Canvas(b)
    c.setFont("CardPoppins", 16)
    c.drawString(72, 760, "Archive copy with the font inside")
    c.showPage()
    c.save()
    return b.getvalue()


def signature_photo() -> bytes:
    """A made-up squiggle in dark ink on white paper, as a phone photo would be."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (600, 200), (250, 250, 246))
    d = ImageDraw.Draw(im)
    d.line([(30, 150), (120, 50), (200, 150), (300, 60), (420, 150), (560, 70)], fill=(15, 15, 40), width=7)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=90)
    return b.getvalue()


def blank_form() -> bytes:
    out, _ = forms.create(text_pdf(1), [
        {"name": "Full name", "type": "text", "page": 1, "x": 20, "y": 30, "w": 80, "h": 8},
        {"name": "agree", "type": "checkbox", "page": 1, "x": 20, "y": 45},
        {"name": "city", "type": "choice", "page": 1, "x": 20, "y": 55, "options": ["Akola", "Pune", "Mumbai"]},
        {"name": "Sign here", "type": "signature", "page": 1, "x": 110, "y": 230}])
    return out


def quote_pdf(total: str = "4,650", due: str = "12/11/2026", extra: str = "") -> bytes:
    from reportlab.pdfgen import canvas
    b = io.BytesIO()
    c = canvas.Canvas(b)
    c.drawString(72, 760, "Quotation for Sharma Traders")
    c.drawString(72, 740, f"Total amount Rs {total} due on {due}")
    c.drawString(72, 720, "Terms: payment in 30 days")
    if extra:
        c.drawString(72, 700, extra)
    c.showPage()
    c.drawString(72, 760, "Page two text unchanged")
    c.showPage()
    c.save()
    return b.getvalue()


class _FakeModel:
    """The card never calls a real model: a scripted one proves the pipes (and the checks) for free."""
    def __init__(self, fn):
        self.fn, self.old = fn, None

    def __enter__(self):
        self.old = smart.ask_model
        smart.ask_model = self.fn
        return self

    def __exit__(self, *a):
        smart.ask_model = self.old


# ---------------------------------------------------------------------------------------------------- scoring
def n_pages(data: bytes) -> int:
    with pikepdf.open(io.BytesIO(data)) as p:
        return len(p.pages)


def first_line(data: bytes, page: int = 1) -> str:
    t = convert.page_texts(data, str(page))[0]
    return t.strip().splitlines()[0] if t.strip() else ""


def _tool(files: dict[str, tuple[str, bytes]], action: str, **a: Any) -> tuple[dict[str, Any], list[tuple[str, bytes]]]:
    """Run the real pdf_kit tool with her files in memory (nothing is stored, nothing reaches a chat)."""
    import asyncio
    from types import SimpleNamespace
    from ..agent import pdfkit_tools as T
    made: list[tuple[str, bytes]] = []

    def get(ctx, fid):
        if fid not in files:
            raise T.ToolError("not found")
        return files[fid]

    def put(ctx, name, data):
        made.append((name, data))
        return {"file_id": f"o{len(made)}", "name": name}
    old = T._get, T._put
    T._get, T._put = get, put
    try:
        r = asyncio.run(T.pdf_kit(SimpleNamespace(tenant_id="__pdfcard__", conversation_id="", actor="owner"), action, **a))
    finally:
        T._get, T._put = old
    return r, made


def _case(cid: str, what: str, fn: Callable[[], tuple[bool, str]], needs: Callable[[], bool] | None = None,
          why: str = "") -> dict[str, Any]:
    return {"id": cid, "what": what, "fn": fn, "needs": needs, "why": why}


def cases() -> list[dict[str, Any]]:
    T12 = text_pdf(12)
    PH = photo_pdf(4)

    def merge():
        m = organize.merge([("a.pdf", text_pdf(3, "A")), ("b.pdf", text_pdf(2, "B")), ("c.jpg", noisy_photo(600, 400))])
        with pikepdf.open(io.BytesIO(m)) as p, p.open_outline() as ol:
            marks = [o.title for o in ol.root]
        ok = n_pages(m) == 6 and first_line(m, 4).startswith("B - page 1") and marks == ["a", "b", "c"]
        return ok, f"6 pages, file B starts at page 4, bookmarks {marks}"

    def split_every():
        parts = organize.split(T12, "every", every=5)
        sizes = [len(p["pages"]) for p in parts]
        return sizes == [5, 5, 2] and first_line(parts[2]["bytes"]).endswith("page 11"), f"parts {sizes}"

    def split_ranges():
        parts = organize.split(T12, "ranges", ranges=["1-2", "10-12"])
        ok = [len(p["pages"]) for p in parts] == [2, 3] and first_line(parts[1]["bytes"]).endswith("page 10")
        joined = organize.split(T12, "ranges", ranges="1-2 | 10-12", merge_ranges=True)
        return ok and len(joined) == 1 and n_pages(joined[0]["bytes"]) == 5, "2 + 3 pages; merged = one 5-page file"

    def split_each():
        parts = organize.split(T12, "each")
        return len(parts) == 12 and all(n_pages(p["bytes"]) == 1 for p in parts), "12 one-page files"

    def split_size():
        parts = organize.split(PH, "size", max_kb=max(60, core.kb(len(PH)) // 3))
        total = sum(len(p["pages"]) for p in parts)
        limit = max(60, core.kb(len(PH)) // 3) * 1024
        return total == 4 and len(parts) >= 2 and all(len(p["bytes"]) <= limit or p.get("over") for p in parts), \
            f"{len(parts)} parts under {limit // 1024} KB"

    def split_blank():
        parts = organize.split(blank_separated(), "blank")
        return [len(p["pages"]) for p in parts] == [2, 3, 1], f"parts {[len(p['pages']) for p in parts]}"

    def split_bookmarks():
        m = organize.merge([("x.pdf", text_pdf(2, "X")), ("y.pdf", text_pdf(3, "Y"))])
        parts = organize.split(m, "bookmarks")
        return [len(p["pages"]) for p in parts] == [2, 3] and parts[1]["label"] == "y", "by bookmark: 2 + 3"

    def remove():
        r = organize.remove(T12, "3, last")
        return n_pages(r) == 10 and first_line(r, 3).endswith("page 4"), "12 - 2 = 10, page 3 gone"

    def extract():
        r = organize.extract(T12, "last, first")
        return n_pages(r) == 2 and first_line(r, 1).endswith("page 12"), "2 pages in her order (12 then 1)"

    def organize_():
        r = organize.organize(T12, "3,1,1,blank,12")
        ok = n_pages(r) == 5 and first_line(r, 1).endswith("page 3") and first_line(r, 3).endswith("page 1")
        return ok and not convert.page_texts(r, "4")[0].strip(), "reorder + duplicate + blank"

    def rotate():
        r = organize.rotate(T12, 90, "odd")
        with pikepdf.open(io.BytesIO(r)) as p:
            rots = [int(p.pages[i].obj.get("/Rotate", 0)) for i in range(3)]
        return rots == [90, 0, 90], f"rotations {rots}"

    def reverse():
        r = organize.reverse(T12)
        return first_line(r, 1).endswith("page 12"), "page 12 first"

    def interleave():
        fr, bk = text_pdf(3, "F"), text_pdf(3, "B")
        r = organize.interleave(fr, bk, back_reversed=True)
        lines = [first_line(r, i) for i in (1, 2, 3)]
        return n_pages(r) == 6 and lines[0].startswith("F - page 1") and lines[1].startswith("B - page 3"), str(lines)

    def compress_levels():
        r = optimize.compress(PH, "recommended")
        e = optimize.compress(PH, "extreme")
        ok = r["after"] < r["before"] and e["after"] <= r["after"] and n_pages(e["bytes"]) == 4
        return ok, f"{core.kb(r['before'])} KB -> recommended {core.kb(r['after'])} KB, extreme {core.kb(e['after'])} KB"

    def compress_target():
        goal = max(40, core.kb(len(PH)) // 8)
        r = optimize.compress(PH, target_kb=goal)
        return r["met"] and len(r["bytes"]) <= goal * 1024 and n_pages(r["bytes"]) == 4, \
            f"target {goal} KB -> {core.kb(r['after'])} KB"

    def compress_text_honest():
        r = optimize.compress(T12, "extreme")
        return r["bytes"] is T12 or r["after"] < r["before"], r["note"][:80]

    def repair():
        r = optimize.repair(broken_pdf())
        return r["pages"] == 3 and first_line(r["bytes"], 3).endswith("page 3"), r["method"]

    def locked_refused():
        try:
            organize.extract(locked_pdf(), "1")
        except DocError as e:
            return "password" in str(e) and "chat" in str(e), "refused, no password asked"
        return False, "a locked PDF was opened"

    def images_to_pdf():
        r = convert.images_to_pdf([("a.jpg", noisy_photo(800, 600)), ("b.jpg", noisy_photo(600, 900, 3))],
                                  page_size="a4", margin="small")
        with pikepdf.open(io.BytesIO(r)) as p:
            boxes = [tuple(round(float(x)) for x in pg.mediabox) for pg in p.pages]
        return boxes == [(0, 0, 842, 595), (0, 0, 595, 842)], f"landscape then portrait A4: {boxes}"

    def to_images():
        imgs = convert.pdf_to_images(T12, "1,12", dpi=100, fmt="png")
        ok = len(imgs) == 2 and abs(imgs[0]["width"] - round(595 * 100 / 72)) <= 2
        return ok, f"{len(imgs)} pictures {imgs[0]['width']}x{imgs[0]['height']}"

    def extract_images():
        imgs = convert.extract_images(PH)
        return len(imgs) == 4 and imgs[0]["ext"] in ("jpg", "png"), f"{len(imgs)} stored pictures"

    def to_text():
        t = convert.pdf_to_text(T12, "txt")
        s = convert.pdf_to_text(PH, "txt")
        return "page 7" in t["text"] and s["no_text_pages"] == [1, 2, 3, 4], "text out; scanned pages named"

    def info():
        i = optimize.info(T12)
        s = optimize.info(PH)
        return i["pages"] == 12 and i["kind"] == "text" and s["kind"].startswith("scanned"), f"{i['kind']} / {s['kind']}"

    def office():
        r = convert.office_to_pdf("quote.docx", word_file())
        return n_pages(r) >= 1 and "quotation" in convert.page_texts(r)[0].lower(), "Word -> PDF, text inside"


    RED = (lambda r, g, b: r > 170 and g < 90 and b < 90)

    def numbers_rotated():
        r = organize.rotate(organize.rotate(text_pdf(4), 90, "2"), 270, "3")
        r = organize.rotate(r, 180, "4")
        out = stamp.page_numbers(r, text="Page {n} of {p}", position="bottom-right", size=20, color_="red")
        spots = [ink(out, i, RED) for i in (1, 2, 3, 4)]
        ok = all(s and s[1] > 0.6 and s[2] > 0.85 for s in spots)        # right side, bottom, on every rotation
        return ok and "Page 4 of 4" in convert.page_texts(out, "4")[0], "bottom-right on screen at 0 / 90 / 270 / 180"

    def numbers_hindi_bates_skip():
        h = stamp.page_numbers(text_pdf(5), text="hindi_of", digits="devanagari", skip_first=1)
        b = stamp.page_numbers(text_pdf(3), bates_prefix="ABC-", start=101)
        t1, t2 = convert.page_texts(h, "1")[0], convert.page_texts(h, "2")[0]
        ok = "पृष्ठ" not in t1 and "पृष्ठ १ / ५" in t2 and "ABC-000103" in convert.page_texts(b, "3")[0]
        return ok, "cover skipped, Hindi digits, Bates ABC-000101.."

    def watermark_text_logo():
        w = stamp.watermark(text_pdf(2), text="गोपनीय CONFIDENTIAL", opacity=0.3)
        g = stamp.watermark(text_pdf(2), image=logo_png(), position="bottom-right", rotation=0, opacity=1)
        spot = ink(g, 1, lambda r, gg, b: gg > 120 and r < 60 and b < 60)
        ok = "CONFIDENTIAL" in convert.page_texts(w, "1")[0] and spot and spot[1] > 0.5 and spot[2] > 0.5
        return bool(ok), f"text in Hindi + English; logo at bottom-right {spot[1:3] if spot else None}"

    def watermark_under():
        w = stamp.watermark(text_pdf(1), text="DRAFT", layer_="under", color_="red", opacity=1)
        with pikepdf.open(io.BytesIO(w)) as p:
            c = p.pages[0].obj.Contents
            body = b"".join(x.read_bytes() for x in c) if isinstance(c, pikepdf.Array) else c.read_bytes()
        under = 0 <= body.find(b" Do") < body.find(b"BT")          # the watermark is drawn before the page's own text
        return under and "DRAFT" in convert.page_texts(w)[0], "drawn before the page's own text (under it)"

    def header_footer():
        h = stamp.header_footer(text_pdf(3), header={"left": "Hoola Traders"}, footer={"center": "Page {n} of {p}"})
        t = convert.page_texts(h, "2")[0]
        return "Hoola Traders" in t and "Page 2 of 3" in t, "header + footer with {n} of {p}"

    def crop_margins_auto():
        c, _ = edit.crop(text_pdf(2), top=20, bottom=20, left=10, right=10)
        a, _ = edit.crop(text_pdf(2), auto=True)
        with pikepdf.open(io.BytesIO(c)) as p, pikepdf.open(io.BytesIO(a)) as q:
            cb = [float(x) for x in p.pages[0].obj.CropBox]
            ab = [float(x) for x in q.pages[0].obj.CropBox]
        w_mm = round((cb[2] - cb[0]) / edit.MM)
        return w_mm == 190 and (ab[2] - ab[0]) < 400, f"margins -> {w_mm} mm wide; auto-trim -> {round((ab[2]-ab[0])/edit.MM)} mm"

    def add_things():
        out, notes = edit.add(text_pdf(2), [
            {"type": "text", "page": 1, "x": 20, "y": 20, "text": "Approved ₹1,200 स्वीकृत", "size": 14},
            {"type": "image", "page": 2, "x": 100, "y": 200, "w": 50, "file_id": "logo"},
            {"type": "whiteout", "page": 1, "x": 10, "y": 60, "w": 60, "h": 8},
            {"type": "note", "page": 1, "text": "check the total"}], {"logo": logo_png()})
        with pikepdf.open(io.BytesIO(out)) as p:
            notes_in = len(p.pages[0].obj.get("/Annots", []))
        spot = ink(out, 2, lambda r, g, b: g > 120 and r < 60 and b < 60)
        ok = "Approved" in convert.page_texts(out, "1")[0] and spot and notes_in == 1 and notes and "HIDES" in notes[0]
        return bool(ok), "text + her picture + note added; white box said to be NOT redaction"

    def highlight():
        out, n = edit.highlight_text(text_pdf(3), "invoice total")
        spot = ink(out, 1, lambda r, g, b: r > 200 and g > 200 and b < 150)
        return n == 90 and bool(spot), f"{n} places highlighted"

    def metadata_set_clean():
        a, m = edit.metadata(text_pdf(1), title="Quote 12", author="Hoola Traders")
        b, m2 = edit.metadata(a, clean=True)
        return m["after"].get("title") == "Quote 12" and not m2["after"], "set, then cleaned to nothing"

    def bookmarks():
        b, n = edit.bookmarks(text_pdf(5), [{"title": "Start", "page": 1}, {"title": "Totals", "page": 5}])
        parts = organize.split(b, "bookmarks")
        return n == 2 and [len(p["pages"]) for p in parts] == [4, 1], "2 bookmarks; split by them = 4 + 1"

    def flatten():
        f, inf = edit.flatten(form_pdf())
        with pikepdf.open(io.BytesIO(f)) as p:
            still = "/AcroForm" in p.Root
        return inf["form_fields"] == 2 and not still and "Ramesh" in convert.page_texts(f)[0], "2 fields -> page"

    def nup_booklet_fit():
        n4 = n_pages(edit.nup(text_pdf(9), 4))
        bk, pad = edit.booklet(text_pdf(6))
        ft = edit.fit(text_pdf(2), "letter")
        with pikepdf.open(io.BytesIO(ft)) as p:
            box = [round(float(x)) for x in p.pages[0].mediabox]
        t = convert.page_texts(bk, "1")[0]
        ok = n4 == 3 and n_pages(bk) == 4 and pad == 2 and "page 1" in t and box == [0, 0, 612, 792]
        return ok, f"9 pages 4-up = {n4} sheets; booklet 6+{pad} blanks = 4 sides; Letter"

    def grayscale():
        col = convert.images_to_pdf([("c.png", logo_png())])
        g, _ = edit.grayscale(col)
        spot = ink(g, 1, lambda r, gg, b: abs(r - gg) > 25 or abs(gg - b) > 25)
        return spot is None, "no colour left on the page"

    def sanitize_and_attachments():
        risky = risky_pdf()
        files = edit.attachments(risky)
        clean, removed = edit.sanitize(risky)
        with pikepdf.open(io.BytesIO(clean)) as p:
            gone = "/OpenAction" not in p.Root and len(p.attachments) == 0
        ok = files and files[0]["bytes"] == b"secret attached notes" and gone and any("JavaScript" in r or "opening" in r for r in removed)
        return bool(ok), f"attachment taken out; removed: {', '.join(removed)[:90]}"

    def protect_hoola():
        pw = secure.make_password()
        lk = secure.protect(text_pdf(2), pw, ["print"])
        said = secure.check_protected(lk, pw, True, ["print"])
        try:
            organize.extract(lk, "1")
            opened = True
        except DocError:
            opened = False
        return not opened and len(said) == 2 and secure.password_problem(pw) == "", "locked, refuses without it"

    def unlock_both():
        r = secure.protect(text_pdf(2), "", ["print"], open_lock=False)
        u1, k1 = secure.unlock(r)
        lk = secure.protect(text_pdf(2), "Hoola-Test-2026", ["print", "copy"])
        try:
            secure.unlock(lk)
            asked = False
        except secure.NeedsPassword:
            asked = True
        try:
            secure.unlock(lk, "wrong-Password-9")
            wrong = False
        except DocError:
            wrong = True
        u2, k2 = secure.unlock(lk, "Hoola-Test-2026")
        return k1 == "restrictions" and asked and wrong and k2 == "open password" and n_pages(u2) == 2, \
            "restrictions removed; open password only with hers; a wrong one refused"

    def checksums():
        ok = (secure.verhoeff_ok(aadhaar_number()) and not secure.verhoeff_ok("123456789012") and
              secure.luhn_ok("4111111111111111") and not secure.luhn_ok("4111111111111112") and
              secure.gstin_ok("27AAPFU0939F1ZV") and not secure.gstin_ok("27AAPFU0939F1ZX"))
        return ok, "Aadhaar Verhoeff, card Luhn, GSTIN check character"

    def redact_presets():
        pdf = id_pdf()
        f = secure.find(pdf, list(secure.DEFAULT_PRESETS) + ["gstin"], ["Ramesh Kumar"])
        kinds = sorted({h["kind"] for h in f["hits"]})
        r = secure.redact(pdf, f["hits"], presets=list(secure.DEFAULT_PRESETS) + ["gstin"])
        t = convert.page_texts(r["bytes"])
        gone = not any(x in " ".join(t) for x in ("ABCPE1234F", "98765", "4111", "ramesh@", "Ramesh", "27AAPFU"))
        ok = (kinds == ["aadhaar", "account", "card", "email", "gstin", "pan", "phone", "words"] and gone and
              "nothing private" in t[1] and r["pages_redrawn"] == [1] and f["scanned_pages"] == [3])
        return ok, f"{len(f['hits'])} found ({', '.join(kinds)}); none readable after; page 2 keeps its text; scan named"

    def redact_not_fooled():
        f = secure.find(id_pdf(), ["aadhaar"])
        return len(f["hits"]) == 1, "an order number that fails the Aadhaar check is left alone"

    def redact_preview_keeps():
        pdf = id_pdf()
        f = secure.find(pdf, ["pan"])
        pv = secure.preview(pdf, f["hits"])
        return "ABCPE1234F" in convert.page_texts(pv)[0] and "PREVIEW" in convert.page_texts(pv)[0], "preview removes nothing"

    def ocr_scan():
        r = ocrlayer.searchable(scanned_text_pdf(), "hindi")
        t = convert.page_texts(r["bytes"])[0]
        same = ink(r["bytes"], 1, lambda a, b, c: a < 80) == ink(scanned_text_pdf(), 1, lambda a, b, c: a < 80)
        return r["done"] == [1] and "Sharma" in t and "Invoice" in t and same, f"read: {t.strip()[:50]!r}; page unchanged"

    def ocr_skips_text():
        r = ocrlayer.searchable(text_pdf(2))
        return r["done"] == [] and r["skipped_text"] == [1, 2], "pages that have text are left alone"

    def to_excel():
        from openpyxl import load_workbook
        good = fromdoc.to_xlsx(table_pdf())
        ws = load_workbook(io.BytesIO(good["bytes"])).worksheets[0]
        vals = [[c.value for c in r] for r in ws.iter_rows()]
        bad = fromdoc.to_xlsx(table_pdf("4,999.00"))
        ok = vals[1][2] == 1200 and vals[2][2] == 3450.5 and not good["notes"] and any("4650.5" in n for n in bad["notes"])
        return ok, "numbers as numbers; a wrong Total is named"

    def to_word():
        from docx import Document
        r = fromdoc.to_docx(table_pdf())
        d = Document(io.BytesIO(r["bytes"]))
        ok = r["headings"] >= 1 and len(d.tables) == 1 and d.tables[0].cell(1, 0).text == "Atta" and \
            any("body text" in p.text for p in d.paragraphs)
        return ok, f"{r['headings']} heading, {r['paragraphs']} paragraph, {r['tables']} table"

    def to_word_scan():
        r = fromdoc.to_docx(scanned_text_pdf())
        from docx import Document
        d = Document(io.BytesIO(r["bytes"]))
        return r["ocr_pages"] == [1] and any("Sharma" in p.text for p in d.paragraphs), "a scan read with OCR first"

    def to_powerpoint():
        from pptx import Presentation
        r = fromdoc.to_pptx(text_pdf(3))
        prs = Presentation(io.BytesIO(r["bytes"]))
        notes = prs.slides[1].notes_slide.notes_text_frame.text
        return len(prs.slides) == 3 and "page 2" in notes, "3 slides, each page's words in its notes"

    def pdfa_keep():
        import pikepdf
        r = archive.to_pdfa(embedded_font_pdf(), "2b")
        with pikepdf.open(io.BytesIO(r["bytes"])) as p:
            meta = str(p.open_metadata())
            intent = "/OutputIntents" in p.Root
        honest = r["validated"] or r["compliant"] is None
        return ("pdfaid" in meta and intent and not r["notes"] and honest and "Archive copy" in
                convert.page_texts(r["bytes"])[0]), "font inside -> kept as is + PDF/A identity; validation said plainly"

    def pdfa_pages():
        r = archive.to_pdfa(text_pdf(2), "2b")
        t = convert.page_texts(r["bytes"])[1]
        return (r["fonts_not_embedded"] and r["notes"] and "page 2" in t), "fonts not inside -> pages redrawn + text layer"

    def redact_keeps_words():
        pdf = id_pdf()
        f = secure.find(pdf, ["pan"])
        r = secure.redact(pdf, f["hits"], presets=["pan"])
        t = convert.page_texts(r["bytes"])[0]
        return "ABCPE1234F" not in t and "Name" in t and r["text_layer_pages"] == [1], "other words searchable again"

    def form_detect_fill():
        f = blank_form()
        names = {x["name"]: x["kind"] for x in forms.detect(f)}
        r = forms.fill(f, {"Full name": "Ramesh Kumar", "agree": "yes", "city": "pune"})
        got = {x["name"]: x["value"] for x in forms.detect(r["bytes"])}
        ok = names == {"Full name": "text", "agree": "checkbox", "city": "choice", "Sign here": "signature"} and \
            got["Full name"] == "Ramesh Kumar" and got["city"] == "Pune" and got["agree"] not in ("", "Off")
        return ok, "4 fields found; text, tick and choice read back as filled"

    def form_refusals():
        f = blank_form()
        msgs = []
        for vals in ({"Name": "x"}, {"city": "Delhi"}, {"Sign here": "x"}):
            try:
                forms.fill(f, vals)
                msgs.append("")
            except DocError as e:
                msgs.append(str(e))
        ok = "Did you mean: Full name" in msgs[0] and "Akola, Pune, Mumbai" in msgs[1] and "action=sign" in msgs[2]
        return ok, "wrong name / choice / signature box each refused with the right words"

    def form_flatten_batch():
        f = blank_form()
        flat = forms.fill(f, {"Full name": "Ramesh Kumar", "city": "Akola"}, flatten=True)["bytes"]
        rows = forms.fill_rows(f, [{"Full name": "A One", "city": "Pune"}, {"Full name": "B Two", "city": "Goa"}],
                               name_from="Full name")
        ok = "Ramesh Kumar" in convert.page_texts(flat)[0] and not forms.detect(flat) and \
            [r["ok"] for r in rows] == [True, False]
        return ok, "flattened text on the page, no fields left; batch: good row made, bad row named"

    def sign_place_digital():
        sign._MEM.clear()
        sign.save_signature("__card__", signature_photo())
        placed = sign.place(text_pdf(2), "__card__", name="Card Owner")
        spot = ink(placed, 2, lambda r, g, b: b - r > 25 and r < 200, scale=1.5)    # the blue-black ink, not black text
        d = sign.digital(placed, "__card__", name="Card Owner")
        v = sign.verify(d["bytes"], "__card__")["signatures"][0]
        return bool(spot) and v["intact"] and v["valid"] and v["her_hoola_certificate"], \
            "signature picture placed (ink seen) + digital signature valid with her certificate"

    def sign_tamper():
        sign._MEM.clear()
        d = sign.digital(text_pdf(2), "__card__", name="Card Owner")["bytes"]
        cut = len(d) // 2
        bad = d[:cut] + bytes([d[cut] ^ 0x01]) + d[cut + 1:]
        try:
            v = sign.verify(bad, "__card__")
            caught = "changed" in v["say"] or any(not s.get("intact", True) or "error" in s for s in v["signatures"])
        except DocError:
            caught = True
        return caught, "one changed byte after signing is caught"

    def sign_field_and_second():
        sign._MEM.clear()
        d1 = sign.digital(blank_form(), "__card__", field="Sign here")["bytes"]
        d2 = sign.digital(d1, "__card__")["bytes"]
        vs = sign.verify(d2, "__card__")["signatures"]
        return len(vs) == 2 and all(x["intact"] for x in vs), "the form's own box signed, then a second signature; both valid"

    def sign_request_flow():
        sign._MEM.clear()
        q = sign.request("__card__", "card-conv", text_pdf(2), "Lease.pdf", [{"name": "First"}, {"name": "Second"}])
        k1, k2 = (x["link"].split("/sign/")[1] for x in q["links"])
        req, s2, i2 = sign.load_request(k2)
        try:
            sign.complete_one(req, s2, i2, signature_photo(), "Second", "1.1.1.1", "card")
            order_kept = False
        except DocError:
            order_kept = True
        req, s1, i1 = sign.load_request(k1)
        sign.complete_one(req, s1, i1, signature_photo(), "First Person", "1.1.1.1", "card")
        req, s2, i2 = sign.load_request(k2)
        fin = sign.complete_one(req, s2, i2, signature_photo(), "Second Person", "2.2.2.2", "card")
        last = convert.page_texts(fin["bytes"])[-1]
        v = sign.verify(fin["bytes"], "__card__")["signatures"]
        ok = order_kept and fin["done"] and "Signing record" in last and "Second Person" in last and v and v[-1]["intact"]
        for ext in (".pdf", ".json"):                       # the card leaves nothing behind on her server
            (sign._req_dir() / f"{q['request_id']}{ext}").unlink(missing_ok=True)
        return ok, "order kept; record page added; sealed"

    def compare_money_dates():
        r = smart.compare(quote_pdf(), quote_pdf("4,950", "15/11/2026", "New clause: late fee Rs 200"))
        ok = (r["changed_pages"] == [1] and any("4,650" in x and "4,950" in x for x in r["money_changed"]) and
              any("15/11/2026" in x for x in r["dates_changed"]) and r.get("bytes") and
              "What changed" in convert.page_texts(r["bytes"])[0] and n_pages(r["bytes"]) == 2)
        return bool(ok), f"money {r['money_changed'][:1]}, dates {r['dates_changed'][:1]}, report + boxed page 1"

    def compare_same():
        r = smart.compare(quote_pdf(), quote_pdf())
        return r["same"] and "bytes" not in r, "identical words = 'same', no report made"

    def answer_check():
        with _FakeModel(lambda s, u, m=0: "The total is Rs 4,650 [p.1], plus a fee of Rs 999 [p.9]."):
            r = smart.ask(quote_pdf(), "What is the total?")
        c = r["check"]
        return c["numbers_not_in_document"] == ["999"] and c["bad_page_refs"] == [9] and c["pages_cited"] == [1], \
            "an invented number and a wrong page are both caught"

    def translate_layout():
        import json as _j

        def fake(s, u, m=0):
            return _j.dumps([ln.split(". ", 1)[1].replace("Quotation for", "कोटेशन -").replace("Terms", "शर्तें")
                             for ln in u.splitlines()])
        with _FakeModel(fake):
            r = smart.translate(quote_pdf(), "hindi")
        t = convert.page_texts(r["bytes"])[0]
        ok = "कोटेशन" in t and "4,650" in t and "Quotation" not in t and n_pages(r["bytes"]) == 2 and not r["flagged"]
        return ok, "Hindi in place of the English, numbers kept, the original words gone"

    def translate_flags_numbers():
        import json as _j
        with _FakeModel(lambda s, u, m=0: _j.dumps([ln.split(". ", 1)[1].replace("4,650", "4,560")
                                                    for ln in u.splitlines()])):
            r = smart.translate(quote_pdf(), "marathi")
        return any("4,650" in x for x in r["flagged"]), "a line whose number changed in translation is flagged"

    def smart_split_plan():
        with _FakeModel(lambda s, u, m=0: '[{"start": 1, "title": "Invoice A"}, {"start": 3, "title": "Invoice B"}, '
                                           '{"start": 99, "title": "ghost"}]'):
            r = smart.smart_split(text_pdf(5))
        return r["ranges"] == ["1-2", "3-5"], f"plan {r['ranges']} (a page that does not exist dropped)"

    def flow_chain():
        r, made = _tool({"a": ("Bill A.pdf", text_pdf(3, "A")), "b": ("Bill B.pdf", text_pdf(2, "B"))}, "flow",
                        file_ids=["a", "b"], workflow="ca")
        name, blob = made[0]
        try:
            pikepdf.open(io.BytesIO(blob)).close()
            locked = False
        except pikepdf.PasswordError:
            locked = True
        ok = len(made) == 1 and locked and bool(r.get("password_links")) and "(For the CA)" in name
        return ok, f"{len(made)} file delivered (in-between files kept in memory), locked, password on a one-time link"

    def flow_batch():
        files = {"a": ("A.pdf", text_pdf(3, "A")), "b": ("B.pdf", text_pdf(2, "B")), "bad": ("x.pdf", b"%PDF-1.4 broken")}
        r, made = _tool(files, "flow", file_ids=["a", "bad", "b"], steps=[{"action": "rotate", "degrees": 90},
                                                                           {"action": "page_numbers"}], batch=True)
        pages = sorted(n_pages(b) for _, b in made)
        ok = pages == [2, 3] and len(r["failed"]) == 1 and r["ran_on"] == 2
        return ok, f"2 of 3 made, 1 failed and named, the others not stopped (pages {pages})"

    def flow_rules():
        from ..dockit import flows
        bad = [[{"action": "redact"}], [{"action": "compress"}, {"action": "merge"}],
               [{"action": "protect"}, {"action": "compress"}], [{"action": "protect", "password": "mine"}],
               [{"action": "summarize"}], [{"action": "sign", "mode": "digital"}], [{"action": "nope"}],
               [{"action": "compress"}] * (flows.MAX_STEPS + 1)]
        refused = 0
        for st in bad:
            try:
                flows.check(st)
            except DocError:
                refused += 1
        good = flows.check([{"action": "merge"}, {"action": "compress", "target_kb": 900, "file_id": "x"}, "protect"])
        ok = refused == len(bad) and "file_id" not in good[1] and good[2] == {"action": "protect"}
        return ok, f"{refused}/{len(bad)} broken chains refused before anything ran"

    return [
        _case("merge", "merge 2 PDFs + a photo, bookmarks", merge),
        _case("split_every", "split every 5 pages", split_every),
        _case("split_ranges", "split by ranges (+ merged)", split_ranges),
        _case("split_each", "split each page", split_each),
        _case("split_size", "split by size limit", split_size),
        _case("split_blank", "split at blank separator pages", split_blank),
        _case("split_bookmarks", "split by bookmarks", split_bookmarks),
        _case("remove", "remove pages", remove),
        _case("extract", "extract pages in her order", extract),
        _case("organize", "reorder + duplicate + blank", organize_),
        _case("rotate", "rotate odd pages", rotate),
        _case("reverse", "reverse order", reverse),
        _case("interleave", "two-sided scan interleave", interleave),
        _case("compress_levels", "compress recommended / extreme", compress_levels),
        _case("compress_target", "compress to a target KB", compress_target),
        _case("compress_honest", "text-only PDF: honest result", compress_text_honest),
        _case("repair", "repair a cut-off PDF", repair),
        _case("locked_refused", "locked PDF refused, no password asked", locked_refused),
        _case("images_to_pdf", "photos -> A4 PDF, orientation", images_to_pdf),
        _case("to_images", "pages -> PNG", to_images),
        _case("extract_images", "pictures inside", extract_images),
        _case("to_text", "PDF -> text, scans named", to_text),
        _case("info", "info: text vs scanned", info),
        _case("office_to_pdf", "Word -> PDF (LibreOffice)", office, convert.office_ready, "LibreOffice not installed"),
        # D2
        _case("numbers_rotated", "page numbers on rotated pages", numbers_rotated),
        _case("numbers_hindi", "Hindi digits, cover skipped, Bates", numbers_hindi_bates_skip),
        _case("watermark", "watermark text (Hindi) + her logo", watermark_text_logo),
        _case("watermark_under", "watermark under the page", watermark_under),
        _case("header_footer", "header + footer", header_footer),
        _case("crop", "crop margins + auto-trim", crop_margins_auto),
        _case("add", "add text / picture / note / white box", add_things),
        _case("highlight", "highlight a phrase everywhere", highlight),
        _case("metadata", "metadata set + clean", metadata_set_clean),
        _case("bookmarks", "bookmarks added", bookmarks),
        _case("flatten", "flatten a filled form", flatten),
        _case("nup_booklet_fit", "4-up, booklet, fit to Letter", nup_booklet_fit),
        _case("grayscale", "grayscale", grayscale),
        _case("sanitize", "sanitize + attachments out", sanitize_and_attachments),
        # D3
        _case("protect", "lock with a strong password", protect_hoola),
        _case("unlock", "unlock restrictions / with her password", unlock_both),
        _case("checksums", "Aadhaar / card / GSTIN checksums", checksums),
        _case("redact", "true redaction, Indian presets", redact_presets),
        _case("redact_checksum", "redaction is not fooled by look-alikes", redact_not_fooled),
        _case("redact_preview", "preview removes nothing", redact_preview_keeps),
        # D4
        _case("ocr", "scan -> searchable (Hindi + English)", ocr_scan, ocrlayer.ready, "Tesseract not installed"),
        _case("ocr_skips", "pages with text left alone", ocr_skips_text, ocrlayer.ready, "Tesseract not installed"),
        _case("to_excel", "tables -> Excel, totals checked", to_excel),
        _case("to_word", "PDF -> editable Word", to_word),
        _case("to_word_scan", "scan -> Word via OCR", to_word_scan, ocrlayer.ready, "Tesseract not installed"),
        _case("to_powerpoint", "PDF -> PowerPoint", to_powerpoint),
        _case("pdfa_keep", "PDF/A-2b, fonts inside", pdfa_keep),
        _case("pdfa_pages", "PDF/A-2b, fonts missing", pdfa_pages, ocrlayer.ready, "Tesseract not installed"),
        _case("redact_text_layer", "redacted page stays searchable", redact_keeps_words, ocrlayer.ready,
              "Tesseract not installed"),
        # D5
        _case("form_fill", "form fields found + filled", form_detect_fill),
        _case("form_refusals", "form refusals name the right fix", form_refusals),
        _case("form_flatten_batch", "flatten + batch from rows", form_flatten_batch),
        _case("sign_place_digital", "signature placed + digital signature", sign_place_digital),
        _case("sign_tamper", "a change after signing is caught", sign_tamper),
        _case("sign_field_second", "sign a form's box, then sign again", sign_field_and_second),
        _case("sign_request", "two people sign in order, sealed", sign_request_flow),
        # D6
        _case("compare", "compare: money + dates pulled out, report", compare_money_dates),
        _case("compare_same", "compare: identical = same", compare_same),
        _case("answer_check", "answers: invented numbers / pages caught (scripted model)", answer_check),
        _case("translate", "translate keeping the layout (scripted model)", translate_layout),
        _case("translate_flags", "translation number check (scripted model)", translate_flags_numbers),
        _case("smart_split", "smart split = a checked plan (scripted model)", smart_split_plan),
        # D7
        _case("flow_chain", "workflow: CA chain -> one locked file", flow_chain),
        _case("flow_batch", "workflow batch: one bad file never stops the rest", flow_batch),
        _case("flow_rules", "workflow rules refuse broken chains first", flow_rules),
    ]


def card(only: list[str] | None = None) -> dict[str, Any]:
    rows = []
    for c in cases():
        if only and c["id"] not in only:
            continue
        if c["needs"] and not c["needs"]():
            rows.append({"id": c["id"], "what": c["what"], "state": "SKIP", "detail": c["why"], "seconds": 0})
            continue
        t = time.monotonic()
        try:
            ok, detail = c["fn"]()
            state = "PASS" if ok else "FAIL"
        except Exception as e:
            state, detail = "FAIL", f"{type(e).__name__}: {str(e)[:140]}"
        rows.append({"id": c["id"], "what": c["what"], "state": state, "detail": detail,
                     "seconds": round(time.monotonic() - t, 2)})
    run = [r for r in rows if r["state"] != "SKIP"]
    passed = sum(r["state"] == "PASS" for r in run)
    return {"rows": rows, "passed": passed, "ran": len(run), "skipped": len(rows) - len(run),
            "say": f"{passed}/{len(run)} actions proved on this server" +
                   (f"; {len(rows) - len(run)} skipped (engine not installed)" if len(rows) > len(run) else "")}


def lines(rep: dict[str, Any]) -> list[str]:
    out = ["HOOLA DOCUMENT KIT - PDF proof card (fixtures made in code, scored by code)"]
    for r in rep["rows"]:
        out.append(f"  {r['state']:<4} {r['id']:<17} {r['seconds']:>5}s  {r['what']}: {r['detail']}")
    out += ["", rep["say"]]
    return out
