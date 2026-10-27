"""v0.189.0 Document Studio: Claude-grade documents for the owner - PDF / Word / Excel / PowerPoint
built on a real design system (cascade palettes, typography scale, table iron rules) with a deep
preview + QA pass before the file ever reaches the chat.

The design rules are ported from the Claude Code document skills:
  - cascade palette: area is inversely proportional to saturation (XL bg S<=0.08, L surfaces S<=0.15,
    M structural S<=0.30, S edges S<=0.50, XS accents S<=0.75); colours are derived from the title,
    never hand-picked hex
  - fonts: a registered pool with fallback (FreeSerif family for Latin, Devanagari shaped via the
    v0.144 uharfbuzz path), never Helvetica/Arial defaults
  - tables: every cell a real paragraph, proportional widths <= available width, centred, repeat header,
    M-tier header fill + L-tier zebra
  - TOC gate: auto TOC only through the template that can fill it (multiBuild), never hardcoded numbers
  - QA before delivery: every generated file is re-opened, measured and reported (preview + issues)

Modules:
  tokens.py   - cascade palette engine + typography scale (single source of truth, no hardcoded hex)
  pdfgen.py   - ReportLab report line: cover, TOC, tables, callouts, header/footer, page images
  xlsxgen.py  - Excel: setup_sheet, zebra, totals, number formats, chart factories, formula guard
  docxgen.py  - Word: recipe cover, heading styles, 1.3x spacing, zebra tables, TOC field
  pptxgen.py  - PowerPoint: palette deck with title slide + footers
  preview.py  - deep preview: page images (pypdfium2), outline, per-sheet structure, QA report
Files come back as bytes; make_tools-style callers store them as the owner's files.
"""
from __future__ import annotations

STUDIO_VERSION = "v0.192.0"
