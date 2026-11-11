"""Shared ground for the document kit: errors, limits, opening / saving a PDF, the one page grammar."""
from __future__ import annotations

import io
import re
from typing import Any

MAX_MB = 200                 # one input file (chat uploads are capped at 25 MB; Drive / email files can be bigger)
MAX_PAGES = 2000             # pages in one input
MAX_FILES = 50               # files in one merge / batch
MAX_OUT_FILES = 300          # files one split may make
RENDER_MAX_PAGES = 300       # pages rendered to pictures in one call
RENDER_MAX_PIXELS = 40_000_000   # one rendered page (e.g. A4 at 600 dpi ~ 35 MP)


class DocError(ValueError):
    """A plain-words reason the action cannot be done (said to her as it is)."""


def mb(n: int) -> float:
    return round(n / 1048576, 2)


def kb(n: int) -> int:
    return int(round(n / 1024))


def check_size(data: bytes, name: str = "") -> None:
    if not data:
        raise DocError(f"{name or 'The file'} is empty.")
    if len(data) > MAX_MB * 1048576:
        raise DocError(f"{name or 'The file'} is {mb(len(data))} MB; the limit is {MAX_MB} MB per file.")


def is_pdf(data: bytes) -> bool:
    return data[:1024].lstrip()[:5] == b"%PDF-" or b"%PDF-" in data[:1024]


def open_pdf(data: bytes, name: str = ""):
    """Open with pikepdf (qpdf repairs small damage by itself). A password PDF is refused - never guessed."""
    import pikepdf
    check_size(data, name)
    try:
        pdf = pikepdf.open(io.BytesIO(data))
    except pikepdf.PasswordError:
        raise DocError(f"{name or 'This PDF'} has an open password. Hoola never asks for a password in chat: open it "
                       "on the phone and use Print > Save as PDF for a copy without the password, then share that.")
    except Exception as e:
        raise DocError(f"{name or 'This PDF'} could not be opened ({type(e).__name__}). Try action=repair.")
    if len(pdf.pages) > MAX_PAGES:
        n = len(pdf.pages)
        pdf.close()
        raise DocError(f"{name or 'This PDF'} has {n} pages; the limit is {MAX_PAGES}.")
    return pdf


def save(pdf, compress: bool = False, linearize: bool = False) -> bytes:
    import pikepdf
    buf = io.BytesIO()
    pdf.save(buf, compress_streams=True, recompress_flate=compress, linearize=linearize,
             object_stream_mode=pikepdf.ObjectStreamMode.generate if compress else pikepdf.ObjectStreamMode.preserve)
    return buf.getvalue()


def page_count(data: bytes) -> int:
    pdf = open_pdf(data)
    with pdf:
        return len(pdf.pages)


_WORDS = {"all": "1-", "first": "1", "last": "-1"}


def pages(spec: Any, n: int, *, allow_repeat: bool = False) -> list[int]:
    """Her page words -> zero-based indexes, in her order.

    '1-3, 5, 8-' | '-3' (= 1-3, the old grammar) | '5-1' (backwards) | 'odd' | 'even' | 'first' | 'last' |
    'last-2' (the last 2 pages) | 'all-but-last' | 'all-but-first' | 'all'. A list of 1-based ints works too.
    Repeats are dropped unless allow_repeat (organize may duplicate a page)."""
    if n <= 0:
        raise DocError("This PDF has no pages.")
    if isinstance(spec, (list, tuple)):
        toks = [str(x) for x in spec]
    else:
        s = str(spec or "").strip().lower()
        s = s.replace("–", "-").replace("—", "-").replace(" to ", "-").replace(" se ", "-").replace(" tak", "")
        if not s or s in _WORDS and _WORDS[s] == "1-":
            return list(range(n))
        toks = [t for t in re.split(r"[,;\s]+(?![^()]*\))", s) if t]
    out: list[int] = []

    def add(i: int) -> None:
        if 0 <= i < n and (allow_repeat or i not in out):
            out.append(i)

    for t in toks:
        t = t.strip()
        if t in ("all",):
            for i in range(n):
                add(i)
        elif t in ("odd",):
            for i in range(0, n, 2):
                add(i)
        elif t in ("even",):
            for i in range(1, n, 2):
                add(i)
        elif t in ("first",):
            add(0)
        elif t == "last":
            add(n - 1)
        elif m := re.fullmatch(r"last-(\d+)", t):
            for i in range(max(0, n - int(m.group(1))), n):
                add(i)
        elif t in ("all-but-last", "all_but_last"):
            for i in range(n - 1):
                add(i)
        elif t in ("all-but-first", "all_but_first"):
            for i in range(1, n):
                add(i)
        elif m := re.fullmatch(r"(\d+)?-(\d+)?", t):
            a = int(m.group(1) or 1)
            b = int(m.group(2) or n)
            step = 1 if a <= b else -1           # '5-1' = backwards (organize)
            for p in range(a, b + step, step):
                add(p - 1)
        elif t.isdigit():
            add(int(t) - 1)
        else:
            raise DocError(f"Page '{t}' was not understood (examples: 1-3,5 | 8- | odd | even | last | last-2).")
    if not out:
        raise DocError(f"None of those pages exist (this PDF has {n} pages).")
    return out


def stem(name: str) -> str:
    base = (name or "document").rsplit("/", 1)[-1]
    return base.rsplit(".", 1)[0] if "." in base else base


def images_of(page):
    """The pictures a page uses, including those inside form XObjects (pikepdf >= 9: get_images)."""
    return page.get_images() if hasattr(page, "get_images") else page.images
