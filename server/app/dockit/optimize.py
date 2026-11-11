"""Optimize: compress (three levels or a target size she names), repair, info. pikepdf + Pillow only (no
Ghostscript: AGPL, owner decision D2 = not at first).

What makes a PDF big is almost always the pictures inside; text and vector drawings stay sharp at every level."""
from __future__ import annotations

import io
from typing import Any

from . import core
from .core import DocError

# level -> (longest side px, JPEG quality, smallest picture touched in px^2)
LEVELS = {"less": (2400, 80, 900 * 900), "recommended": (1600, 62, 600 * 600), "extreme": (1100, 42, 300 * 300)}
# rungs tried after 'extreme' when she named a target size
DEEPER = [(900, 35, 200 * 200), (720, 30, 150 * 150), (560, 25, 100 * 100), (420, 22, 80 * 80)]
JUNK = ("/PieceInfo", "/Thumb")


def _shrink_images(pdf, max_side: int, quality: int, min_area: int) -> int:
    import pikepdf
    from PIL import Image
    done, changed = set(), 0
    for page in pdf.pages:
        for k in JUNK:
            if k in page.obj:
                del page.obj[k]
        for _, raw in list(core.images_of(page).items()):
            if raw.objgen in done:
                continue
            done.add(raw.objgen)
            try:
                if raw.get("/SMask") is not None or raw.get("/Mask") is not None or raw.get("/ImageMask"):
                    continue                     # pictures with transparency stay as they are (they would go black)
                pim = pikepdf.PdfImage(raw)
                if pim.width * pim.height < min_area:
                    continue
                pil = pim.as_pil_image()
                if pil.mode == "CMYK":
                    pil = pil.convert("RGB")
                elif pil.mode not in ("RGB", "L"):
                    pil = pil.convert("RGB")
                if max(pil.size) > max_side:
                    pil.thumbnail((max_side, max_side), Image.LANCZOS)
                buf = io.BytesIO()
                pil.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
                if buf.tell() >= len(raw.read_raw_bytes()) * 0.95:
                    continue
                raw.write(buf.getvalue(), filter=pikepdf.Name.DCTDecode)
                raw.Width, raw.Height = pil.size
                raw.ColorSpace = pikepdf.Name.DeviceGray if pil.mode == "L" else pikepdf.Name.DeviceRGB
                raw.BitsPerComponent = 8
                for k in ("/DecodeParms", "/Decode", "/Intent"):
                    if k in raw:
                        del raw[k]
                changed += 1
            except Exception:
                continue
    return changed


def _pass(data: bytes, max_side: int, quality: int, min_area: int) -> tuple[bytes, int]:
    with core.open_pdf(data) as pdf:
        try:
            pdf.remove_unreferenced_resources()
        except Exception:
            pass
        n = _shrink_images(pdf, max_side, quality, min_area)
        return core.save(pdf, compress=True), n


def compress(data: bytes, level: str = "recommended", target_kb: int = 0) -> dict[str, Any]:
    """-> {bytes, level, before, after, images, met (target), note}. The smallest result that still meets her ask;
    the original back (unchanged) when nothing could be saved - said, never faked."""
    level = (level or "recommended").strip().lower()
    if level not in LEVELS:
        raise DocError("level = less | recommended | extreme (or give target_kb).")
    before = len(data)
    target = int(target_kb or 0) * 1024
    if target and target < 10 * 1024:
        raise DocError("A target under 10 KB is not possible for a PDF; give 10 KB or more.")
    if target and before <= target:
        return {"bytes": data, "level": "none", "before": before, "after": before, "images": 0, "met": True,
                "note": f"It is already {core.kb(before)} KB, under the {target_kb} KB asked. Nothing changed."}
    rungs = [(level, LEVELS[level])]
    if target:
        order = ["less", "recommended", "extreme"]
        rungs = [(k, LEVELS[k]) for k in order[order.index(level):]] + [(f"deeper {i + 1}", r) for i, r in enumerate(DEEPER)]
    best, best_lvl, best_n = data, "none", 0
    for name, (side, q, area) in rungs:
        out, n = _pass(data, side, q, area)
        if len(out) < len(best):
            best, best_lvl, best_n = out, name, n
        if not target or len(best) <= target:
            break
    after = len(best)
    met = (after <= target) if target else after < before
    if after >= before:
        note = "It could not be made smaller: the pictures inside are already small (or it has no pictures)."
        best, after = data, before
    elif target and not met:
        note = (f"The smallest reached is {core.kb(after)} KB (was {core.kb(before)} KB); {target_kb} KB is not "
                "reachable without losing what can be read. Splitting it into parts (mode=size) can meet a portal limit.")
    else:
        note = f"{core.kb(before)} KB -> {core.kb(after)} KB ({100 - round(after * 100 / before)}% smaller)."
    return {"bytes": best, "level": best_lvl, "before": before, "after": after, "images": best_n, "met": bool(met),
            "note": note}


def repair(data: bytes) -> dict[str, Any]:
    """qpdf (inside pikepdf) rebuilds a damaged cross-reference table and recovers what it can; when it cannot,
    pypdfium2 draws each readable page and those pictures become a new PDF (said plainly: text becomes a picture)."""
    import pikepdf
    core.check_size(data)
    try:
        with pikepdf.open(io.BytesIO(data), attempt_recovery=True) as pdf:
            n = len(pdf.pages)
            if n == 0:
                raise ValueError("no pages")
            out = core.save(pdf)
        return {"bytes": out, "pages": n, "method": "structure rebuilt (text and pictures kept)"}
    except pikepdf.PasswordError:
        raise DocError("This PDF has an open password; it is locked, not broken. Share a copy without the password.")
    except Exception:
        pass
    try:
        import pypdfium2 as pdfium
        from . import convert
        doc = pdfium.PdfDocument(data)
        pics = []
        try:
            for i in range(min(len(doc), core.RENDER_MAX_PAGES)):
                page = doc[i]
                try:
                    im = page.render(scale=150 / 72).to_pil().convert("RGB")
                    b = io.BytesIO()
                    im.save(b, "JPEG", quality=85)
                    pics.append((f"page {i + 1}", b.getvalue()))
                except Exception:
                    continue
                finally:
                    page.close()
        finally:
            doc.close()
        if pics:
            return {"bytes": convert.images_to_pdf(pics, page_size="fit"), "pages": len(pics),
                    "method": "pages redrawn as pictures (the text is no longer selectable; OCR can bring it back)"}
    except Exception:
        pass
    raise DocError("This file is too damaged: no page could be recovered. If it came by email or download, fetch it again.")


def info(data: bytes, name: str = "") -> dict[str, Any]:
    """Pages, size, page sizes, text or scanned, bookmarks, form fields, signatures, attachments, JavaScript, metadata."""
    from . import convert
    with core.open_pdf(data, name) as pdf:
        n = len(pdf.pages)
        sizes = {}
        for p in pdf.pages[:50]:
            try:
                b = [float(x) for x in p.mediabox]
                w, h = round((b[2] - b[0]) / 72 * 25.4), round((b[3] - b[1]) / 72 * 25.4)
                sizes[f"{w}x{h} mm"] = sizes.get(f"{w}x{h} mm", 0) + 1
            except Exception:
                continue
        fields = sigs = 0
        try:
            for f in pdf.Root.get("/AcroForm", {}).get("/Fields", []):
                fields += 1
                if f.get("/FT") == "/Sig":
                    sigs += 1
        except Exception:
            pass
        try:
            with pdf.open_outline() as ol:
                marks = len(list(ol.root))
        except Exception:
            marks = 0
        js = "/JavaScript" in pdf.Root.get("/Names", {}) or "/OpenAction" in pdf.Root
        meta = {}
        try:
            for k in ("/Title", "/Author", "/Creator", "/Producer"):
                if pdf.docinfo and k in pdf.docinfo:
                    meta[k[1:].lower()] = str(pdf.docinfo[k])[:120]
        except Exception:
            pass
        attach = len(pdf.attachments) if hasattr(pdf, "attachments") else 0
        restricted = bool(pdf.is_encrypted)          # opened without a password = owner restrictions only
        images = 0
        for p in pdf.pages[:50]:
            try:
                images += len(core.images_of(p))
            except Exception:
                pass
    texts = convert.page_texts(data, f"1-{min(n, 30)}")
    no_text = sum(1 for t in texts if not t.strip())
    kind = "scanned (pictures of pages)" if no_text == len(texts) else ("mixed" if no_text else "text")
    return {"name": name, "pages": n, "size_kb": core.kb(len(data)), "page_sizes": sizes, "kind": kind,
            "pages_without_text": no_text, "bookmarks": marks, "form_fields": fields - sigs, "signatures": sigs,
            "attachments": attach, "javascript": bool(js), "images_first_50_pages": images, "metadata": meta,
            "restrictions": restricted}
