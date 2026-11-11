"""D0 PDF PROOF CARD (docs/DOCUMENT_KIT_PLAN.md): every document-kit action run on fixture files made HERE in code
(no real person's data), each result scored by code - pages, size, text, pictures - never by a model.

python -m app.quality pdf [--only id,id] [--json]     (free: no model, no network; vps-ops > pdf_card)
A case whose engine is not installed on this server is SKIPPED with the reason, never counted as a pass."""
from __future__ import annotations

import io
import time
from typing import Any, Callable

import pikepdf

from ..dockit import convert, core, optimize, organize
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
