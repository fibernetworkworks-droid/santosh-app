"""D0 PDF PROOF CARD (docs/DOCUMENT_KIT_PLAN.md): every document-kit action run on fixture files made HERE in code
(no real person's data), each result scored by code - pages, size, text, pictures - never by a model.

python -m app.quality pdf [--only id,id] [--json]     (free: no model, no network; vps-ops > pdf_card)
A case whose engine is not installed on this server is SKIPPED with the reason, never counted as a pass."""
from __future__ import annotations

import io
import time
from typing import Any, Callable

import pikepdf

from ..dockit import convert, core, edit, optimize, organize, stamp
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


# ---------------------------------------------------------------------------------------------------- scoring
def n_pages(data: bytes) -> int:
    with pikepdf.open(io.BytesIO(data)) as p:
        return len(p.pages)


def first_line(data: bytes, page: int = 1) -> str:
    t = convert.page_texts(data, str(page))[0]
    return t.strip().splitlines()[0] if t.strip() else ""


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
