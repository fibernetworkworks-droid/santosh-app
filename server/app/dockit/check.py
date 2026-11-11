"""Done = checked (plan law 4.1). Every output is opened again - by pikepdf (the structure) AND pypdfium2 (the engine
Chrome uses to draw PDFs) - before Hoola calls it done. A file that fails is never delivered; the reason is said."""
from __future__ import annotations

import io
from typing import Any

from .core import DocError


def pdf_out(data: bytes, expect_pages: int | None = None, what: str = "the result") -> list[str]:
    import pikepdf
    import pypdfium2 as pdfium
    said: list[str] = []
    try:
        with pikepdf.open(io.BytesIO(data)) as pdf:
            n = len(pdf.pages)
    except Exception as e:
        raise DocError(f"Check failed: {what} does not open ({type(e).__name__}); nothing was delivered.")
    if expect_pages is not None and n != expect_pages:
        raise DocError(f"Check failed: {what} has {n} pages, {expect_pages} were expected; nothing was delivered.")
    said.append(f"opens, {n} page{'s' if n != 1 else ''}")
    try:
        doc = pdfium.PdfDocument(data)
        try:
            page = doc[0]
            try:
                page.render(scale=0.15)
            finally:
                page.close()
        finally:
            doc.close()
        said.append("draws in a viewer")
    except Exception as e:
        raise DocError(f"Check failed: {what} does not draw ({type(e).__name__}); nothing was delivered.")
    return said


def image_out(data: bytes, what: str = "the picture") -> list[str]:
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
    except Exception as e:
        raise DocError(f"Check failed: {what} is not a readable picture ({type(e).__name__}).")
    return ["picture opens"]


def summary(checks: list[str]) -> str:
    return "checked: " + ", ".join(dict.fromkeys(checks)) if checks else ""


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise DocError("Check failed: " + msg + "; nothing was delivered.")


def page_total(parts: list[dict[str, Any]], n: int) -> None:
    got = sum(len(p.get("pages") or []) for p in parts)
    expect(got == n, f"the parts hold {got} pages but the file has {n}")
