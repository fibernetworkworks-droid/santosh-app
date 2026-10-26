# PDF Generation Skill (Production-Grade)
Use `weasyprint` for HTML-to-PDF (best for typography, columns, margins) or `reportlab` for precise coordinate control (charts, barcodes).

## Default Standards (Apply unless user specifies otherwise)
- Page size: A4 (210mm x 297mm)
- Margins: 20mm top/bottom, 15mm left/right
- Body font: Noto Sans (or Inter), 11pt, line-height 1.5
- Headings: Bold, H1 18pt, H2 14pt, H3 12pt
- Colors: Primary #1E3A5F, Accent #E8A317, Text #2D3748
- Tables: Header row background #F1F5F9, 1px solid #CBD5E1 borders, 8pt padding
- Footer: Page number centered, 9pt gray (#718096)

## Workflow
1. Write the content as clean HTML with inline CSS.
2. Use `weasyprint.HTML(string=html).write_pdf(output_path)`.
3. Validate the output (file exists, > 1KB).
