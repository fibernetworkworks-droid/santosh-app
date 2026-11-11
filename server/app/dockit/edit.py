"""D2 edit: crop (her margins, or trim the white edges itself), add things onto pages (text / picture / box / line /
circle / highlight / white box / note), highlight a word everywhere it appears, metadata (set or clean), bookmarks,
flatten (forms + comments become part of the page), N-up and booklet printing, fit every page to A4 / Letter,
grayscale, sanitize (scripts, attachments, hidden data out), attachments out.

Places she names are in what she SEES: mm (or '%') from the TOP-LEFT of the page, whatever the page's rotation.
A white box is NOT redaction (the text is still underneath; true redaction is D3) - every answer that uses one says so."""
from __future__ import annotations

import io
import re
from typing import Any

from . import core, stamp
from .core import DocError

MM = 72 / 25.4
SHEETS = {"a4": (595.28, 841.89), "letter": (612.0, 792.0), "legal": (612.0, 1008.0), "a3": (841.89, 1190.55),
          "a5": (419.53, 595.28)}
GRIDS = {2: (2, 1), 4: (2, 2), 6: (2, 3), 8: (2, 4), 9: (3, 3), 16: (4, 4)}


def from_visual(f: dict[str, float], X: float, Y: float) -> tuple[float, float]:
    """Inverse of stamp.to_visual: where she sees it -> the page's own space."""
    r, cw, ch = f["rot"], f["cw"], f["ch"]
    if r == 90:
        xl, yl = cw - Y, X
    elif r == 180:
        xl, yl = cw - X, ch - Y
    elif r == 270:
        xl, yl = Y, ch - X
    else:
        xl, yl = X, Y
    return xl + f["mx"] + f["cx"], yl + f["my"] + f["cy"]


def _len(v: Any, total: float, default: float = 0.0) -> float:
    """'12' / 12 = mm, '30%' = share of the side, '40pt' = points."""
    if v is None or v == "":
        return default
    s = str(v).strip().lower()
    try:
        if s.endswith("%"):
            return total * float(s[:-1]) / 100
        if s.endswith("pt"):
            return float(s[:-2])
        if s.endswith("mm"):
            s = s[:-2]
        return float(s) * MM
    except ValueError:
        raise DocError(f"'{v}' is not a length (give mm like 20, a share like 30%, or points like 40pt).")


# ---------------------------------------------------------------------------------------------- crop
def crop(data: bytes, *, top: Any = 0, right: Any = 0, bottom: Any = 0, left: Any = 0, pages: Any = "all",
         auto: bool = False, pad_mm: float = 4) -> tuple[bytes, list[dict]]:
    """Cut margins off (what she sees, in mm or %), or auto = trim the white edges of each page (kept + pad_mm)."""
    import pikepdf
    done = []
    with core.open_pdf(data) as pdf:
        idx = core.pages(pages or "all", len(pdf.pages))
        if auto:
            boxes = _ink_boxes(data, idx)
        for i in idx:
            page = pdf.pages[i]
            f = stamp.frame(page)
            w, h = f["vw"], f["vh"]
            if auto:
                b = boxes.get(i)
                if not b:
                    continue
                p = pad_mm * MM
                X0, Y0, X1, Y1 = max(0, b[0] - p), max(0, b[1] - p), min(w, b[2] + p), min(h, b[3] + p)
            else:
                X0, X1 = _len(left, w), w - _len(right, w)
                Y0, Y1 = _len(bottom, h), h - _len(top, h)
            if X1 - X0 < 36 or Y1 - Y0 < 36:
                raise DocError(f"Page {i + 1} would be smaller than half an inch; cut less.")
            a, b2 = from_visual(f, X0, Y0), from_visual(f, X1, Y1)
            box = [min(a[0], b2[0]), min(a[1], b2[1]), max(a[0], b2[0]), max(a[1], b2[1])]
            page.obj.CropBox = pikepdf.Array(box)
            page.obj.TrimBox = pikepdf.Array(box)
            done.append({"page": i + 1, "mm": f"{round((X1 - X0) / MM)} x {round((Y1 - Y0) / MM)}"})
        if not done:
            raise DocError("Nothing was cropped (the pages are blank or already tight).")
        return core.save(pdf), done


def _ink_boxes(data: bytes, idx: list[int]) -> dict[int, tuple[float, float, float, float]]:
    """Where the ink is on each page, in what she sees (points from the bottom-left)."""
    import pypdfium2 as pdfium
    from PIL import ImageOps
    out = {}
    doc = pdfium.PdfDocument(data)
    try:
        for i in idx[:core.RENDER_MAX_PAGES]:
            page = doc[i]
            try:
                w, h = page.get_size()
                sc = 50 / 72
                im = page.render(scale=sc).to_pil().convert("L")
            finally:
                page.close()
            bb = ImageOps.invert(im).point(lambda v: 255 if v > 24 else 0).getbbox()
            if not bb:
                continue
            x0, y0, x1, y1 = bb
            out[i] = (x0 / sc, h - y1 / sc, x1 / sc, h - y0 / sc)
    finally:
        doc.close()
    return out


# ---------------------------------------------------------------------------------------------- add things
KINDS = ("text", "image", "rect", "line", "ellipse", "highlight", "whiteout", "note")


def add(data: bytes, items: list[dict], images: dict[str, bytes] | None = None) -> tuple[bytes, list[str]]:
    """items: [{type, page (1-based or 'all'), x, y (from the top-left), w, h, text, size, color, bold, opacity,
    file_id (image), fill, stroke, width}]. Returns (pdf, notes)."""
    import pikepdf
    if not items:
        raise DocError("Give what to add: items=[{type: text, page: 1, x: 20, y: 30, text: '...'}].")
    if len(items) > 200:
        raise DocError("At most 200 things in one call.")
    notes: list[str] = []
    with core.open_pdf(data) as pdf:
        n = len(pdf.pages)
        per: dict[int, list[dict]] = {}
        for it in items:
            kind = str(it.get("type") or "text").lower()
            if kind not in KINDS:
                raise DocError(f"type = {' | '.join(KINDS)}.")
            for i in core.pages(it.get("page") or 1, n):
                per.setdefault(i, []).append(it | {"type": kind})
        keep: list = []
        for i, its in per.items():
            page = pdf.pages[i]
            notes_here = [x for x in its if x["type"] == "note"]
            draws = [x for x in its if x["type"] != "note"]
            if draws:
                stamp.layer(pdf, page, lambda c, w, h, its=draws: _draw_items(c, w, h, its, images or {}), keep=keep)
            for nt in notes_here:
                f = stamp.frame(page)
                X = _len(nt.get("x"), f["vw"], 20 * MM)
                Y = f["vh"] - _len(nt.get("y"), f["vh"], 20 * MM)
                x, y = from_visual(f, X, Y)
                annot = pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Text,
                                           Rect=pikepdf.Array([x, y - 20, x + 20, y]),
                                           Contents=pikepdf.String(str(nt.get("text") or "")[:2000]),
                                           T=pikepdf.String("Hoola"), Name=pikepdf.Name.Comment,
                                           C=pikepdf.Array(list(stamp.color(nt.get("color") or "yellow"))))
                if "/Annots" not in page.obj:
                    page.obj.Annots = pikepdf.Array()
                page.obj.Annots.append(pdf.make_indirect(annot))
        if any(it["type"] == "whiteout" for v in per.values() for it in v):
            notes.append("A white box only HIDES what is under it: the text is still inside the file and can be "
                         "copied. To remove it for good use true redaction (coming in D3).")
        out = core.save(pdf)
        for s in keep:
            s.close()
        return out, notes


def _draw_items(c, w: float, h: float, items: list[dict], images: dict[str, bytes]) -> None:
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    for it in items:
        k = it["type"]
        x = _len(it.get("x"), w, 20 * MM)
        top = _len(it.get("y"), h, 20 * MM)
        bw = _len(it.get("w"), w, 60 * MM)
        bh = _len(it.get("h"), h, 12 * MM)
        op = max(0.05, min(1.0, float(it.get("opacity") or (0.35 if k == "highlight" else 1.0))))
        c.saveState()
        c.setFillAlpha(op)
        c.setStrokeAlpha(op)
        if k == "text":
            size = float(it.get("size") or 12)
            c.setFillColorRGB(*stamp.color(it.get("color") or "#000000"))
            for j, line in enumerate(str(it.get("text") or "").splitlines()[:60] or [""]):
                stamp.draw_text(c, x, h - top - size * (j + 0.85) * 1.25, line, size, bool(it.get("bold")),
                                str(it.get("align") or "left"))
        elif k == "image":
            raw = images.get(str(it.get("file_id") or ""))
            if raw is None:
                raise DocError("An image item needs the file_id of her picture (her signature, stamp or logo).")
            im = Image.open(io.BytesIO(raw))
            im.load()
            iw, ih = im.size
            if it.get("h") in (None, "") and it.get("w") not in (None, ""):
                bh = bw * ih / iw
            elif it.get("w") in (None, "") and it.get("h") not in (None, ""):
                bw = bh * iw / ih
            elif it.get("w") in (None, "") and it.get("h") in (None, ""):
                bw, bh = 40 * MM, 40 * MM * ih / iw
            c.drawImage(ImageReader(im), x, h - top - bh, bw, bh, mask="auto")
        elif k in ("rect", "highlight", "whiteout", "ellipse"):
            fill = {"highlight": "yellow", "whiteout": "white"}.get(k, it.get("fill"))
            stroke = None if k in ("highlight", "whiteout") else (it.get("stroke") or it.get("color") or "#d32f2f")
            if fill:
                c.setFillColorRGB(*stamp.color(fill))
            if stroke:
                c.setStrokeColorRGB(*stamp.color(stroke))
                c.setLineWidth(float(it.get("width") or 1.5))
            if k == "whiteout":
                c.setFillAlpha(1)
            st, fl = (1 if stroke else 0), (1 if fill else 0)
            if k == "ellipse":
                c.ellipse(x, h - top - bh, x + bw, h - top, stroke=st, fill=fl)
            else:
                c.rect(x, h - top - bh, bw, bh, stroke=st, fill=fl)
        elif k == "line":
            c.setStrokeColorRGB(*stamp.color(it.get("color") or "#000000"))
            c.setLineWidth(float(it.get("width") or 1.5))
            x2 = _len(it.get("x2"), w, x + bw)
            y2 = _len(it.get("y2"), h, top)
            c.line(x, h - top, x2, h - y2)
        c.restoreState()


def find_boxes(data: bytes, term: str, pages: Any = "all", match_case: bool = False,
               hits: list | None = None) -> dict[int, list[tuple]]:
    """Every place a word / phrase appears -> boxes in the page's own space, one per line it covers."""
    import pypdfium2 as pdfium
    term = str(term or "").strip()
    if len(term) < 2:
        raise DocError("Give the word or phrase to find (2 letters or more).")
    out: dict[int, list[tuple]] = {}
    doc = pdfium.PdfDocument(data)
    try:
        for i in core.pages(pages or "all", len(doc)):
            page = doc[i]
            tp = page.get_textpage()
            try:
                s = tp.search(term, match_case=match_case)
                while True:
                    hit = s.get_next()
                    if not hit:
                        break
                    start, count = hit
                    if hits is not None:
                        hits.append(i)
                    lines: dict[int, list[float]] = {}
                    for ci in range(start, start + count):
                        l, b, r, t = tp.get_charbox(ci)
                        if r <= l:
                            continue
                        key = round(b / 4)
                        box = lines.setdefault(key, [l, b, r, t])
                        box[0], box[1], box[2], box[3] = min(box[0], l), min(box[1], b), max(box[2], r), max(box[3], t)
                    out.setdefault(i, []).extend(tuple(v) for v in lines.values())
                s.close()
            finally:
                tp.close()
                page.close()
    finally:
        doc.close()
    return out


def highlight_text(data: bytes, term: str, pages: Any = "all", color_: Any = "yellow",
                   match_case: bool = False) -> tuple[bytes, int]:
    hits: list = []
    found = find_boxes(data, term, pages, match_case, hits)
    count = len(hits)
    if not count:
        raise DocError(f"'{term}' was not found as text in this PDF (a scanned page has no text to search; OCR "
                       "comes in D4).")
    rgb = stamp.color(color_, "yellow")
    with core.open_pdf(data) as pdf:
        keep: list = []
        for i, boxes in found.items():
            f = stamp.frame(pdf.pages[i])

            def draw(c, w, h, boxes=boxes, f=f):
                c.setFillColorRGB(*rgb)
                c.setFillAlpha(0.38)
                for (l, b, r, t) in boxes:
                    p1, p2 = stamp.to_visual(f, l, b), stamp.to_visual(f, r, t)
                    x0, y0, x1, y1 = min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])
                    c.rect(x0 - 1, y0 - 1.5, x1 - x0 + 2, y1 - y0 + 3, stroke=0, fill=1)
            stamp.layer(pdf, pdf.pages[i], draw, keep=keep)
        out = core.save(pdf)
        for s in keep:
            s.close()
        return out, count


# ---------------------------------------------------------------------------------------------- document level
def metadata(data: bytes, *, title: str | None = None, author: str | None = None, subject: str | None = None,
             keywords: str | None = None, clean: bool = False) -> tuple[bytes, dict]:
    import pikepdf
    with core.open_pdf(data) as pdf:
        before = {k[1:].lower(): str(v)[:120] for k, v in (pdf.docinfo.items() if pdf.docinfo else [])}
        if clean:
            for k in list(pdf.docinfo.keys()) if pdf.docinfo else []:
                del pdf.docinfo[k]
            if "/Metadata" in pdf.Root:
                del pdf.Root.Metadata
            for page in pdf.pages:
                if "/Metadata" in page.obj:
                    del page.obj.Metadata
        for key, val in (("/Title", title), ("/Author", author), ("/Subject", subject), ("/Keywords", keywords)):
            if val is not None:
                pdf.docinfo[key] = pikepdf.String(str(val)[:500])
        if not clean and any(v is not None for v in (title, author, subject, keywords)):
            try:
                with pdf.open_metadata(set_pikepdf_as_editor=False) as m:
                    if title is not None:
                        m["dc:title"] = str(title)
                    if author is not None:
                        m["dc:creator"] = [str(author)]
            except Exception:
                pass
        after = {k[1:].lower(): str(v)[:120] for k, v in (pdf.docinfo.items() if pdf.docinfo else [])}
        return core.save(pdf), {"before": before, "after": after}


def bookmarks(data: bytes, items: list[dict] | None = None, clear: bool = False) -> tuple[bytes, int]:
    import pikepdf
    with core.open_pdf(data) as pdf:
        n = len(pdf.pages)
        with pdf.open_outline() as ol:
            if clear:
                ol.root.clear()
            for it in items or []:
                p = int(it.get("page") or 1)
                if not 1 <= p <= n:
                    raise DocError(f"Bookmark '{it.get('title')}' points at page {p}; the file has {n} pages.")
                ol.root.append(pikepdf.OutlineItem(str(it.get("title") or f"Page {p}")[:200], p - 1))
            count = len(list(ol.root))
        return core.save(pdf), count


def flatten(data: bytes) -> tuple[bytes, dict]:
    """Form fields and comments become part of the page (nobody can change the filled values afterwards)."""
    import pikepdf
    with core.open_pdf(data) as pdf:
        annots = sum(len(p.obj.get("/Annots", [])) for p in pdf.pages)
        fields = len(pdf.Root.get("/AcroForm", {}).get("/Fields", [])) if "/AcroForm" in pdf.Root else 0
        try:
            pdf.generate_appearance_streams()
        except Exception:
            pass
        pdf.flatten_annotations("all")
        if "/AcroForm" in pdf.Root:
            del pdf.Root.AcroForm
        for p in pdf.pages:                   # widgets left without a form (e.g. empty signature boxes) go too
            if "/Annots" in p.obj:
                p.obj.Annots = pikepdf.Array([a for a in p.obj.Annots if a.get("/Subtype") != "/Widget"])
        left = sum(len(p.obj.get("/Annots", [])) for p in pdf.pages)
        return core.save(pdf), {"annotations_before": annots, "form_fields": fields, "annotations_left": left}


def nup(data: bytes, per_sheet: int = 2, sheet: str = "a4", margin_mm: float = 6) -> bytes:
    """Several pages on one sheet (2 / 4 / 6 / 8 / 9 / 16), in reading order."""
    import pikepdf
    if per_sheet not in GRIDS:
        raise DocError(f"per_sheet = {' | '.join(str(k) for k in GRIDS)}.")
    sw, sh = SHEETS.get(str(sheet or "a4").lower(), (0, 0))
    if not sw:
        raise DocError(f"sheet = {' | '.join(SHEETS)}.")
    cols, rows = GRIDS[per_sheet]
    if per_sheet == 2:
        sw, sh = sh, sw                              # 2-up = landscape, side by side
    with core.open_pdf(data) as src:
        out = pikepdf.new()
        m = margin_mm * MM
        cw, chh = (sw - m * (cols + 1)) / cols, (sh - m * (rows + 1)) / rows
        n = len(src.pages)
        for s0 in range(0, n, per_sheet):
            out.add_blank_page(page_size=(sw, sh))
            sheet_p = out.pages[-1]
            for k in range(per_sheet):
                if s0 + k >= n:
                    break
                col, row = k % cols, k // cols
                x0 = m + col * (cw + m)
                y0 = sh - m - (row + 1) * chh - row * m
                sheet_p.add_overlay(src.pages[s0 + k], pikepdf.Rectangle(x0, y0, x0 + cw, y0 + chh))
        return core.save(out)


def booklet(data: bytes, sheet: str = "a4") -> tuple[bytes, int]:
    """Saddle-stitch booklet: pages reordered so the printed, folded stack reads 1, 2, 3...; blanks added to a
    multiple of 4. Print double-sided, flip on the SHORT edge."""
    import pikepdf
    sw, sh = SHEETS.get(str(sheet or "a4").lower(), (0, 0))
    if not sw:
        raise DocError(f"sheet = {' | '.join(SHEETS)}.")
    sw, sh = sh, sw
    with core.open_pdf(data) as src:
        n = len(src.pages)
        total = (n + 3) // 4 * 4
        seq = list(range(total))
        order = []
        for i in range(total // 2):
            a, b = (seq[total - 1 - i], seq[i]) if i % 2 == 0 else (seq[i], seq[total - 1 - i])
            order.append((a, b))
        out = pikepdf.new()
        half = sw / 2
        for a, b in order:
            out.add_blank_page(page_size=(sw, sh))
            sp = out.pages[-1]
            for slot, p in enumerate((a, b)):
                if p < n:
                    sp.add_overlay(src.pages[p], pikepdf.Rectangle(slot * half, 0, (slot + 1) * half, sh))
        return core.save(out), total - n


def fit(data: bytes, sheet: str = "a4", margin_mm: float = 0, orientation: str = "auto") -> bytes:
    """Every page onto one paper size (scaled, never stretched, centred): mixed scans become one tidy A4 file."""
    import pikepdf
    sw, sh = SHEETS.get(str(sheet or "a4").lower(), (0, 0))
    if not sw:
        raise DocError(f"sheet = {' | '.join(SHEETS)}.")
    with core.open_pdf(data) as src:
        out = pikepdf.new()
        m = margin_mm * MM
        for page in src.pages:
            f = stamp.frame(page)
            w, h = (sw, sh)
            o = (orientation or "auto").lower()
            if o == "landscape" or (o == "auto" and f["vw"] > f["vh"]):
                w, h = sh, sw
            out.add_blank_page(page_size=(w, h))
            out.pages[-1].add_overlay(page, pikepdf.Rectangle(m, m, w - m, h - m))
        return core.save(out)


_GRAY_OPS = {"rg": "g", "RG": "G", "k": "g", "K": "G"}


def _gray_stream(pdf, obj) -> int:
    import pikepdf
    try:
        ops = pikepdf.parse_content_stream(obj)
    except Exception:
        return 0
    out, changed = [], 0
    for operands, op in ops:
        name = str(op)
        if name in ("rg", "RG") and len(operands) == 3:
            r, g, b = (float(v) for v in operands)
            out.append(([round(0.299 * r + 0.587 * g + 0.114 * b, 4)], pikepdf.Operator(_GRAY_OPS[name])))
            changed += 1
        elif name in ("k", "K") and len(operands) == 4:
            c_, m_, y_, k_ = (float(v) for v in operands)
            r, g, b = (1 - c_) * (1 - k_), (1 - m_) * (1 - k_), (1 - y_) * (1 - k_)
            out.append(([round(0.299 * r + 0.587 * g + 0.114 * b, 4)], pikepdf.Operator(_GRAY_OPS[name])))
            changed += 1
        else:
            out.append((operands, op))
    if changed:
        data = pikepdf.unparse_content_stream(out)
        if isinstance(obj, pikepdf.Page):
            obj.obj.Contents = pdf.make_stream(data)
        else:
            obj.write(data)
    return changed


def grayscale(data: bytes) -> tuple[bytes, dict]:
    """Colour pictures -> grey, colour text / lines -> grey (black-and-white printing, smaller file).
    Colours set through named colour spaces or patterns are left as they are (said in the result)."""
    import pikepdf
    pics = ops = 0
    with core.open_pdf(data) as pdf:
        done = set()
        for page in pdf.pages:
            ops += _gray_stream(pdf, page)
            res = page.obj.get("/Resources", {})
            for _, xo in (res.get("/XObject", {}) or {}).items():
                if xo.objgen in done:
                    continue
                done.add(xo.objgen)
                try:
                    if xo.get("/Subtype") == "/Form":
                        ops += _gray_stream(pdf, xo)
                    elif xo.get("/Subtype") == "/Image" and xo.get("/SMask") is None and not xo.get("/ImageMask"):
                        pim = pikepdf.PdfImage(xo)
                        pil = pim.as_pil_image()
                        if pil.mode == "L":
                            continue
                        g = pil.convert("L")
                        buf = io.BytesIO()
                        g.save(buf, "JPEG", quality=85)
                        xo.write(buf.getvalue(), filter=pikepdf.Name.DCTDecode)
                        xo.ColorSpace = pikepdf.Name.DeviceGray
                        xo.BitsPerComponent = 8
                        xo.Width, xo.Height = g.size
                        for k in ("/DecodeParms", "/Decode"):
                            if k in xo:
                                del xo[k]
                        pics += 1
                except Exception:
                    continue
        return core.save(pdf, compress=True), {"pictures": pics, "colours": ops}


def sanitize(data: bytes, keep_links: bool = True) -> tuple[bytes, list[str]]:
    """Take out what can run or hide: JavaScript, auto-run actions, launch actions, embedded files, XFA forms,
    metadata, page thumbnails. Web links stay unless keep_links=false."""
    import pikepdf
    removed: list[str] = []
    with core.open_pdf(data) as pdf:
        root = pdf.Root
        names = root.get("/Names")
        if names is not None:
            for k in ("/JavaScript", "/EmbeddedFiles"):
                if k in names:
                    del names[k]
                    removed.append("JavaScript" if k == "/JavaScript" else "attached files")
        for k, label in (("/OpenAction", "an action that runs on opening"), ("/AA", "automatic actions"),
                         ("/Metadata", "XMP metadata")):
            if k in root:
                del root[k]
                removed.append(label)
        if "/AcroForm" in root and "/XFA" in root.AcroForm:
            del root.AcroForm.XFA
            removed.append("XFA form scripts")
        n_launch = n_links = 0
        for page in pdf.pages:
            for k in ("/AA", "/Thumb"):
                if k in page.obj:
                    del page.obj[k]
            annots = page.obj.get("/Annots")
            if annots is None:
                continue
            keep = pikepdf.Array()
            for a in annots:
                act = a.get("/A")
                s = str(act.get("/S")) if act is not None else ""
                if s in ("/JavaScript", "/Launch", "/ImportData", "/SubmitForm", "/ResetForm"):
                    n_launch += 1
                    continue
                if a.get("/Subtype") == "/FileAttachment":
                    n_launch += 1
                    continue
                if s == "/URI" and not keep_links:
                    n_links += 1
                    continue
                if "/AA" in a:
                    del a["/AA"]
                keep.append(a)
            page.obj.Annots = keep
        if n_launch:
            removed.append(f"{n_launch} script / launch / attachment items on pages")
        if n_links:
            removed.append(f"{n_links} web links")
        if pdf.docinfo:
            for k in list(pdf.docinfo.keys()):
                del pdf.docinfo[k]
            removed.append("document info (author, software)")
        return core.save(pdf), removed


def attachments(data: bytes) -> list[dict[str, Any]]:
    out = []
    with core.open_pdf(data) as pdf:
        for name, spec in pdf.attachments.items():
            try:
                blob = spec.get_file().read_bytes()
            except Exception:
                continue
            out.append({"name": re.sub(r"[\\/]+", "_", str(name))[:120] or "attachment", "bytes": blob})
            if len(out) >= 50:
                break
    return out
