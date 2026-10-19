"""Small PDF writer for invoices, quotations, salary slips, rent receipts and resumes (ReportLab)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_FONT = "Helvetica"
_BOLD = "Helvetica-Bold"
_RS = "Rs. "
for base in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu"):
    if os.path.exists(f"{base}/DejaVuSans.ttf") and os.path.exists(f"{base}/DejaVuSans-Bold.ttf"):
        pdfmetrics.registerFont(TTFont("DejaVu", f"{base}/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", f"{base}/DejaVuSans-Bold.ttf"))
        _FONT, _BOLD, _RS = "DejaVu", "DejaVu-Bold", "₹"
        break


def money(paise: int) -> str:
    r, p = divmod(int(round(paise)), 100)
    s = str(r)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"{_RS}{s}.{p:02d}"


ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
        "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n: int) -> str:
    return ONES[n] if n < 20 else (TENS[n // 10] + (" " + ONES[n % 10] if n % 10 else ""))


def _three(n: int) -> str:
    h, r = divmod(n, 100)
    return ((ONES[h] + " Hundred" + (" " if r else "")) if h else "") + (_two(r) if r else "")


def words_inr(paise: int) -> str:
    """Indian numbering: 1,23,45,678.50 -> One Crore Twenty Three Lakh ... Rupees and Fifty Paise Only"""
    rupees, p = divmod(int(round(paise)), 100)
    if rupees == 0 and p == 0:
        return "Zero Rupees Only"
    parts = []
    crore, rupees = divmod(rupees, 10_000_000)
    lakh, rupees = divmod(rupees, 100_000)
    thousand, rupees = divmod(rupees, 1000)
    if crore:
        parts.append((_three(crore) if crore < 1000 else words_inr(crore * 100).replace(" Rupees Only", "")) + " Crore")
    if lakh:
        parts.append(_two(lakh) + " Lakh")
    if thousand:
        parts.append(_two(thousand) + " Thousand")
    if rupees:
        parts.append(_three(rupees))
    out = " ".join(parts) + " Rupees"
    if p:
        out += f" and {_two(p)} Paise"
    return out + " Only"


def _styles():
    ss = getSampleStyleSheet()
    return {
        "h": ParagraphStyle("h", parent=ss["Title"], fontName=_BOLD, fontSize=18, spaceAfter=4, alignment=0),
        "b": ParagraphStyle("b", parent=ss["Normal"], fontName=_FONT, fontSize=9.5, leading=13),
        "bb": ParagraphStyle("bb", parent=ss["Normal"], fontName=_BOLD, fontSize=10, leading=14),
        "small": ParagraphStyle("s", parent=ss["Normal"], fontName=_FONT, fontSize=8, leading=11, textColor=colors.HexColor("#555555")),
    }


def write_pdf(path: Path, title: str, top_left: list[str], top_right: list[str], header: list[str], rows: list[list[Any]],
              totals: list[tuple[str, str]], footer: list[str], col_widths: list[float] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    st = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=title)
    story: list[Any] = [Paragraph(title, st["h"]), Spacer(1, 4)]
    head = Table([[Paragraph("<br/>".join(top_left), st["b"]), Paragraph("<br/>".join(top_right), st["b"])]],
                 colWidths=[95 * mm, 83 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [head, Spacer(1, 8)]
    if header:
        data = [[Paragraph(f"<b>{h}</b>", st["b"]) for h in header]] + [[Paragraph(str(c), st["b"]) for c in r] for r in rows]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1EEE6")),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
        ]))
        story += [t, Spacer(1, 6)]
    if totals:
        tt = Table([[Paragraph(k, st["bb"] if i == len(totals) - 1 else st["b"]), Paragraph(v, st["bb"] if i == len(totals) - 1 else st["b"])]
                    for i, (k, v) in enumerate(totals)], colWidths=[140 * mm, 38 * mm])
        tt.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black)]))
        story += [tt, Spacer(1, 8)]
    for f in footer:
        story.append(Paragraph(f, st["small"]))
    doc.build(story)
    return path
