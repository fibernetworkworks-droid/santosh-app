"""Organize: merge, split (every mode), remove, extract, organize (reorder / duplicate / blank), reverse, interleave,
rotate. pikepdf (MPL-2.0) for the structure; pypdfium2 only to find blank pages."""
from __future__ import annotations

import re
from typing import Any

from . import core
from .core import DocError


def merge(files: list[tuple[str, bytes]], bookmarks: bool = True) -> bytes:
    """PDFs (and pictures, turned into a page each) joined in her order; one bookmark per file."""
    import pikepdf
    from . import convert
    if len(files) < 2:
        raise DocError("Merging needs at least 2 files.")
    if len(files) > core.MAX_FILES:
        raise DocError(f"At most {core.MAX_FILES} files in one merge.")
    out = pikepdf.new()
    keep, marks = [], []
    for name, data in files:
        if not core.is_pdf(data):
            if convert.is_image(data):
                data = convert.images_to_pdf([(name, data)])
            else:
                raise DocError(f"{name} is not a PDF or a picture. Office files become PDFs with action=convert.")
        src = core.open_pdf(data, name)
        keep.append(src)                     # sources stay open until the merged file is saved
        marks.append((core.stem(name), len(out.pages)))
        out.pages.extend(src.pages)
    if len(out.pages) > core.MAX_PAGES:
        raise DocError(f"The merged file would have {len(out.pages)} pages; the limit is {core.MAX_PAGES}.")
    if bookmarks:
        with out.open_outline() as ol:
            for title, at in marks:
                ol.root.append(pikepdf.OutlineItem(title, at))
    data = core.save(out)
    for s in keep:
        s.close()
    return data


def _subset(src, idx: list[int]) -> bytes:
    import pikepdf
    out = pikepdf.new()
    for i in idx:
        out.pages.append(src.pages[i])
    return core.save(out)


def extract(data: bytes, spec: Any) -> bytes:
    """Only these pages, in her order (one new PDF)."""
    with core.open_pdf(data) as src:
        return _subset(src, core.pages(spec, len(src.pages)))


def remove(data: bytes, spec: Any) -> bytes:
    with core.open_pdf(data) as src:
        n = len(src.pages)
        drop = set(core.pages(spec, n))
        keep = [i for i in range(n) if i not in drop]
        if not keep:
            raise DocError("That would remove every page; nothing would be left.")
        return _subset(src, keep)


def organize(data: bytes, order: Any) -> bytes:
    """A new page order. Tokens: page numbers / ranges (repeats allowed = duplicate), 'blank' = an empty page.
    Pages left out are dropped (that is how she deletes while reordering)."""
    import pikepdf
    with core.open_pdf(data) as src:
        n = len(src.pages)
        toks = order if isinstance(order, (list, tuple)) else [t for t in re.split(r"[,;\s]+", str(order or "")) if t]
        if not toks:
            raise DocError("Give the new page order, e.g. '3,1,2,blank,4-'.")
        out = pikepdf.new()
        for t in toks:
            t = str(t).strip().lower()
            if t in ("blank", "b", "khali"):
                out.add_blank_page(page_size=_size(src.pages[0]))
                continue
            for i in core.pages(t, n, allow_repeat=True):
                out.pages.append(src.pages[i])
        if len(out.pages) > core.MAX_PAGES:
            raise DocError(f"The new file would have {len(out.pages)} pages; the limit is {core.MAX_PAGES}.")
        return core.save(out)


def _size(page) -> tuple[float, float]:
    try:
        b = [float(x) for x in page.mediabox]
        return (b[2] - b[0], b[3] - b[1])
    except Exception:
        return (595.0, 842.0)


def reverse(data: bytes) -> bytes:
    with core.open_pdf(data) as src:
        return _subset(src, list(range(len(src.pages) - 1, -1, -1)))


def interleave(front: bytes, back: bytes | None = None, back_reversed: bool = True) -> bytes:
    """Double-sided scanning done on a one-sided scanner: fronts 1,3,5.. + backs (usually scanned in reverse).
    One file = its first half are the fronts, its second half the backs."""
    import pikepdf
    out = pikepdf.new()
    a = core.open_pdf(front, "the fronts")
    b = core.open_pdf(back, "the backs") if back else None
    with a:
        if b is None:
            n = len(a.pages)
            if n % 2:
                raise DocError(f"One file with fronts + backs needs an even page count (it has {n}).")
            fronts, backs = list(a.pages[: n // 2]), list(a.pages[n // 2:])
        else:
            fronts, backs = list(a.pages), list(b.pages)
        if back_reversed:
            backs = backs[::-1]
        if abs(len(fronts) - len(backs)) > 1:
            raise DocError(f"{len(fronts)} fronts and {len(backs)} backs do not pair up.")
        for i in range(max(len(fronts), len(backs))):
            if i < len(fronts):
                out.pages.append(fronts[i])
            if i < len(backs):
                out.pages.append(backs[i])
        data = core.save(out)
    if b is not None:
        b.close()
    return data


def rotate(data: bytes, degrees: int, spec: Any = "") -> bytes:
    if int(degrees) % 90:
        raise DocError("Pages turn only by 90, 180 or 270 degrees.")
    with core.open_pdf(data) as pdf:
        for i in core.pages(spec or "all", len(pdf.pages)):
            pdf.pages[i].rotate(int(degrees), relative=True)
        return core.save(pdf)


# ---------------------------------------------------------------------------------------------------- split
SPLIT_MODES = ("ranges", "every", "each", "pages", "size", "bookmarks", "blank")


def _ranges(spec: Any) -> list[str]:
    if isinstance(spec, (list, tuple)):
        return [str(x).strip() for x in spec if str(x).strip()]
    return [x.strip() for x in re.split(r"[|;]+|\band\b", str(spec or "")) if x.strip()]


def split(data: bytes, mode: str = "each", *, ranges: Any = None, every: int = 0, pages: Any = None,
          max_kb: int = 0, merge_ranges: bool = False) -> list[dict[str, Any]]:
    """-> [{label, pages: [1-based...], bytes}] in order. merge_ranges = the chosen parts joined into ONE file."""
    mode = (mode or "each").strip().lower()
    if mode not in SPLIT_MODES:
        raise DocError(f"Split mode must be one of {', '.join(SPLIT_MODES)}.")
    with core.open_pdf(data) as src:
        n = len(src.pages)
        groups: list[tuple[str, list[int]]] = []
        if mode == "ranges":
            parts = _ranges(ranges)
            if not parts:
                raise DocError("Give the parts, e.g. ranges=['1-3','4-10'] or '1-3 | 4-10'.")
            for p in parts:
                groups.append((f"pages {p}", core.pages(p, n)))
        elif mode == "every":
            k = int(every or 0)
            if k < 1:
                raise DocError("every = how many pages in each part (1 or more).")
            for a in range(0, n, k):
                idx = list(range(a, min(n, a + k)))
                groups.append((f"pages {idx[0] + 1}-{idx[-1] + 1}", idx))
        elif mode == "each":
            groups = [(f"page {i + 1}", [i]) for i in range(n)]
        elif mode == "pages":
            groups = [(f"page {i + 1}", [i]) for i in core.pages(pages or "all", n)]
        elif mode == "bookmarks":
            groups = _by_bookmarks(src, n)
        elif mode == "blank":
            groups = _by_blank(data, n)
        else:  # size
            return _by_size(src, n, int(max_kb or 0))
        if merge_ranges:
            idx = [i for _, g in groups for i in g]
            return [{"label": "chosen pages", "pages": [i + 1 for i in idx], "bytes": _subset(src, idx)}]
        if len(groups) > core.MAX_OUT_FILES:
            raise DocError(f"That makes {len(groups)} files; the limit is {core.MAX_OUT_FILES}. Use a bigger 'every'.")
        return [{"label": lab, "pages": [i + 1 for i in g], "bytes": _subset(src, g)} for lab, g in groups]


def _by_bookmarks(src, n: int) -> list[tuple[str, list[int]]]:
    starts: list[tuple[int, str]] = []
    try:
        with src.open_outline() as ol:
            for item in ol.root:
                try:
                    import pikepdf
                    dest = item.destination
                    if dest is None and item.action is not None:
                        dest = item.action.get("/D")
                    if isinstance(dest, int):
                        p = dest
                    else:
                        p = pikepdf.Page(dest[0]).index if dest is not None else None
                except Exception:
                    p = None
                if p is not None and 0 <= p < n:
                    starts.append((p, str(item.title or f"part {len(starts) + 1}")))
    except Exception:
        starts = []
    starts = sorted({p: t for p, t in starts}.items())
    if not starts:
        raise DocError("This PDF has no bookmarks to split by. Use mode=every or mode=ranges.")
    if starts[0][0] != 0:
        starts.insert(0, (0, "start"))
    out = []
    for k, (p, title) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else n
        out.append((title[:60], list(range(p, end))))
    return out


def blank_pages(data: bytes, n: int) -> list[int]:
    """Pages with no text and (almost) no ink - the separator sheets of a batch scan."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(data)
    blank = []
    try:
        for i in range(n):
            page = doc[i]
            try:
                txt = page.get_textpage().get_text_range().strip()
                if txt:
                    continue
                img = page.render(scale=20 / 72).to_pil().convert("L")
                hist = img.histogram()
                dark = sum(hist[:200])
                if dark <= max(2, img.width * img.height // 400):
                    blank.append(i)
            finally:
                page.close()
    finally:
        doc.close()
    return blank


def _by_blank(data: bytes, n: int) -> list[tuple[str, list[int]]]:
    seps = set(blank_pages(data, n))
    if not seps:
        raise DocError("No blank separator pages were found. Use mode=every or mode=ranges.")
    out, cur = [], []
    for i in range(n):
        if i in seps:
            if cur:
                out.append((f"part {len(out) + 1}", cur))
            cur = []
        else:
            cur.append(i)
    if cur:
        out.append((f"part {len(out) + 1}", cur))
    return out


def _by_size(src, n: int, max_kb: int) -> list[dict[str, Any]]:
    if max_kb < 20:
        raise DocError("max_kb = the most each part may weigh, in KB (at least 20).")
    if n > 600:
        raise DocError("Splitting by size works on up to 600 pages; split by pages first.")
    limit = max_kb * 1024
    out: list[dict[str, Any]] = []
    cur: list[int] = []
    cur_bytes = b""
    for i in range(n):
        trial = _subset(src, cur + [i])
        if len(trial) <= limit or not cur:
            cur, cur_bytes = cur + [i], trial
            continue
        out.append({"label": f"part {len(out) + 1}", "pages": [p + 1 for p in cur], "bytes": cur_bytes})
        cur, cur_bytes = [i], _subset(src, [i])
    if cur:
        out.append({"label": f"part {len(out) + 1}", "pages": [p + 1 for p in cur], "bytes": cur_bytes})
    for part in out:
        if len(part["bytes"]) > limit:
            part["over"] = True              # one page alone is bigger than the limit: said, never hidden
    if len(out) > core.MAX_OUT_FILES:
        raise DocError(f"That makes {len(out)} files; the limit is {core.MAX_OUT_FILES}. Allow a bigger size.")
    return out
