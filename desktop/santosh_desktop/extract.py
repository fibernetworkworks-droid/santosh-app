"""Pull plain text out of common office files so Santosh can search and read them."""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

TEXT_EXT = {".txt", ".csv", ".md", ".json", ".xml", ".log", ".tsv", ".html", ".htm"}
KIND = {".pdf": "pdf", ".xlsx": "excel", ".xlsm": "excel", ".xls": "excel", ".csv": "excel", ".docx": "word", ".doc": "word",
        ".jpg": "image", ".jpeg": "image", ".png": "image", ".heic": "image", ".webp": "image",
        ".txt": "text", ".md": "text", ".json": "text", ".xml": "text", ".tsv": "excel",
        ".900": "tally", ".tsf": "tally", ".1800": "tally", ".zip": "archive", ".pptx": "slides", ".ppt": "slides"}

CATEGORIES = [
    ("GST", r"\bgst(r|in)?\b|gstr-?\d|e-?invoice|\birn\b"),
    ("E-way bill", r"e-?way ?bill|\bewb\b"),
    ("Invoice", r"\b(tax )?invoice\b|\bbill no\b|\binv[-_ ]?\d"),
    ("Quotation", r"\bquotation\b|\bquote\b|\bestimate\b|\bproforma\b"),
    ("Purchase order", r"\bpurchase order\b|\bp\.?o\.? ?no\b"),
    ("Bank statement", r"\bbank statement\b|\baccount statement\b|\bstatement of account\b|\bpassbook\b"),
    ("Receipt", r"\breceipt\b|\bpayment received\b"),
    ("Salary", r"\bsalary\b|\bpayslip\b|\bpay slip\b|\bpayroll\b"),
    ("Challan", r"\bchallan\b|\bdelivery note\b"),
    ("Agreement", r"\bagreement\b|\bcontract\b|\bmou\b"),
    ("Tally", r"\btally\b"),
]


def kind_of(path: Path) -> str:
    return KIND.get(path.suffix.lower(), "other")


def category(name: str, text: str) -> str:
    hay = (name + " " + text[:4000]).lower()
    for label, pat in CATEGORIES:
        if re.search(pat, hay):
            return label
    return ""


def _docx(path: Path, limit: int) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)[:limit]


def _xlsx(path: Path, limit: int) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out, n = [], 0
    try:
        for ws in wb.worksheets:
            out.append(f"## {ws.title}")
            for row in ws.iter_rows(values_only=True):
                cells = ["" if v is None else str(v) for v in row]
                if any(cells):
                    line = " | ".join(cells).strip(" |")
                    out.append(line)
                    n += len(line)
                    if n > limit:
                        return "\n".join(out)[:limit]
    finally:
        wb.close()
    return "\n".join(out)[:limit]


def _pdf(path: Path, limit: int, max_pages: int = 40) -> str:
    from pypdf import PdfReader
    r = PdfReader(str(path))
    out, n = [], 0
    for i, page in enumerate(r.pages):
        if i >= max_pages:
            break
        t = page.extract_text() or ""
        out.append(t)
        n += len(t)
        if n > limit:
            break
    return "\n".join(out)[:limit]


def text_of(path: Path, limit: int = 20000) -> str:
    ext = path.suffix.lower()
    try:
        if ext in TEXT_EXT:
            raw = path.read_bytes()[: limit * 4]
            txt = raw.decode("utf-8", "ignore")
            if ext in (".html", ".htm", ".xml"):
                txt = re.sub(r"<[^>]+>", " ", txt)
            if ext in (".csv", ".tsv"):
                rows = csv.reader(io.StringIO(txt), delimiter="\t" if ext == ".tsv" else ",")
                txt = "\n".join(" | ".join(r) for r in rows)
            return txt[:limit]
        if ext == ".docx":
            return _docx(path, limit)
        if ext in (".xlsx", ".xlsm"):
            return _xlsx(path, limit)
        if ext == ".pdf":
            return _pdf(path, limit)
    except Exception:
        return ""
    return ""
