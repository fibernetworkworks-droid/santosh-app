"""v0.194: Claude-style document generator.
Generates PDF, DOCX, XLSX, and HTML previews using production-grade formatting.
"""
import os
import uuid
import logging
from pathlib import Path

log = logging.getLogger("santosh.docs")
OUT_DIR = Path("static/generated")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_pdf(html_content: str) -> dict:
    """Generate a PDF from HTML using WeasyPrint."""
    try:
        from weasyprint import HTML
        doc_id = str(uuid.uuid4())[:8]
        path = OUT_DIR / f"doc_{doc_id}.pdf"
        HTML(string=html_content).write_pdf(str(path))
        return {"ok": True, "url": f"/static/generated/doc_{doc_id}.pdf", "path": str(path)}
    except Exception as e:
        log.error(f"PDF generation failed: {e}")
        return {"ok": False, "error": str(e)}

def generate_docx(title: str, paragraphs: list[str], table_data: list[list] = None) -> dict:
    """Generate a Word document with proper styles."""
    try:
        from docx import Document
        from docx.shared import Inches
        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)
        doc.add_heading(title, level=0)
        for p in paragraphs:
            doc.add_paragraph(p)
        if table_data:
            table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
            table.style = "Table Grid"
            for i, row in enumerate(table_data):
                for j, val in enumerate(row):
                    table.cell(i, j).text = str(val)
        doc_id = str(uuid.uuid4())[:8]
        path = OUT_DIR / f"doc_{doc_id}.docx"
        doc.save(str(path))
        return {"ok": True, "url": f"/static/generated/doc_{doc_id}.docx", "path": str(path)}
    except Exception as e:
        log.error(f"DOCX generation failed: {e}")
        return {"ok": False, "error": str(e)}

def generate_xlsx(title: str, headers: list[str], rows: list[list]) -> dict:
    """Generate a styled Excel spreadsheet with xlsxwriter."""
    try:
        import xlsxwriter
        doc_id = str(uuid.uuid4())[:8]
        path = OUT_DIR / f"doc_{doc_id}.xlsx"
        wb = xlsxwriter.Workbook(str(path))
        ws = wb.add_worksheet(title[:31])
        header_fmt = wb.add_format({"bold": True, "font_color": "white", "bg_color": "#1E3A5F", "border": 1})
        for col, h in enumerate(headers):
            ws.write(0, col, h, header_fmt)
        for row_idx, row in enumerate(rows, start=1):
            for col, val in enumerate(row):
                ws.write(row_idx, col, val)
        ws.freeze_panes(1, 0)
        wb.close()
        return {"ok": True, "url": f"/static/generated/doc_{doc_id}.xlsx", "path": str(path)}
    except Exception as e:
        log.error(f"XLSX generation failed: {e}")
        return {"ok": False, "error": str(e)}

def generate_preview(html_content: str) -> dict:
    """Save an HTML preview file."""
    doc_id = str(uuid.uuid4())[:8]
    path = OUT_DIR / f"preview_{doc_id}.html"
    path.write_text(html_content, encoding="utf-8")
    return {"ok": True, "url": f"/static/generated/preview_{doc_id}.html"}

def generate_pdf_from_url(url: str, title: str = "") -> dict:
    """Fetch a webpage, extract the main content, and render it as a long, beautifully formatted PDF."""
    try:
        import trafilatura
        from weasyprint import HTML
        
        # 1. Fetch and extract clean text/HTML
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {"ok": False, "error": "Could not download the webpage."}
        
        # Extract as HTML (preserves headings, lists, tables)
        clean_html = trafilatura.extract(downloaded, output_format="html", include_images=True, include_links=True)
        if not clean_html:
            return {"ok": False, "error": "Could not extract text from the page."}
            
        page_title = title or "Document"
        
        # 2. Wrap in a production-grade print template
        css = """
        @page {
            size: A4;
            margin: 20mm 15mm;
            @bottom-center {
                content: counter(page);
                font-family: 'Noto Sans', sans-serif;
                font-size: 9pt;
                color: #718096;
            }
        }
        body {
            font-family: 'Noto Sans', 'Segoe UI', sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #2D3748;
            text-align: justify;
        }
        h1, h2, h3 { color: #1E3A5F; page-break-after: avoid; margin-top: 1.5em; }
        h1 { font-size: 22pt; border-bottom: 2px solid #E8A317; padding-bottom: 8px; }
        h2 { font-size: 16pt; }
        h3 { font-size: 13pt; }
        img { max-width: 100%; height: auto; page-break-inside: avoid; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin: 1em 0; page-break-inside: avoid; }
        th, td { border: 1px solid #CBD5E1; padding: 8px; text-align: left; }
        th { background-color: #F1F5F9; font-weight: bold; }
        a { color: #3182CE; text-decoration: none; }
        blockquote { border-left: 4px solid #E8A317; margin: 1em 0; padding-left: 1em; color: #4A5568; font-style: italic; }
        """
        
        full_html = f"""<!DOCTYPE html>
        <html><head><meta charset="utf-8"><title>{page_title}</title><style>{css}</style></head>
        <body><h1>{page_title}</h1>{clean_html}</body></html>"""
        
        # 3. Generate the PDF
        doc_id = str(uuid.uuid4())[:8]
        path = OUT_DIR / f"doc_{doc_id}.pdf"
        HTML(string=full_html).write_pdf(str(path))
        
        return {"ok": True, "url": f"/static/generated/doc_{doc_id}.pdf", "path": str(path), "title": page_title}
    except Exception as e:
        log.error(f"Long PDF generation failed: {e}")
        return {"ok": False, "error": str(e)}

def generate_advanced_excel(spec: dict) -> dict:
    """Generate a multi-sheet, formatted Excel file with formulas and charts from a JSON spec."""
    try:
        import xlsxwriter
        
        filename = spec.get("filename", "Report.xlsx")
        doc_id = str(uuid.uuid4())[:8]
        path = OUT_DIR / f"{doc_id}_{filename}"
        
        wb = xlsxwriter.Workbook(str(path))
        
        # Formats
        fmt_header = wb.add_format({"bold": True, "font_color": "white", "bg_color": "#1E3A5F", "border": 1, "align": "center"})
        fmt_currency = wb.add_format({"num_format": "₹#,##0.00", "border": 1})
        fmt_percent = wb.add_format({"num_format": "0.00%", "border": 1})
        fmt_date = wb.add_format({"num_format": "DD-MMM-YYYY", "border": 1})
        fmt_zebra = wb.add_format({"bg_color": "#F8FAFC", "border": 1})
        
        for sheet_spec in spec.get("sheets", []):
            sheet_name = sheet_spec.get("name", "Sheet1")
            ws = wb.add_worksheet(sheet_name)
            
            headers = sheet_spec.get("headers", [])
            rows = sheet_spec.get("rows", [])
            formats = sheet_spec.get("formats", {})
            
            # Write headers
            for col_idx, header in enumerate(headers):
                ws.write(0, col_idx, header, fmt_header)
                
            # Write data
            for row_idx, row in enumerate(rows, start=1):
                for col_idx, val in enumerate(row):
                    col_letter = xlsxwriter.utility.xl_col_to_name(col_idx)
                    fmt = fmt_zebra if row_idx % 2 == 0 else None
                    
                    # Apply specific column formats
                    if col_letter in formats:
                        f_type = formats[col_letter]
                        if f_type == "currency": fmt = fmt_currency
                        elif f_type == "percent": fmt = fmt_percent
                        elif f_type == "date": fmt = fmt_date
                        
                    if isinstance(val, str) and val.startswith("="):
                        ws.write_formula(row_idx, col_idx, val, fmt)
                    else:
                        ws.write(row_idx, col_idx, val, fmt)
                        
            # Freeze top row and auto-fit columns
            ws.freeze_panes(1, 0)
            for i in range(len(headers)):
                ws.set_column(i, i, 15)
                
            # Add Chart if requested
            chart_spec = sheet_spec.get("chart")
            if chart_spec and rows:
                chart = wb.add_chart({"type": chart_spec.get("type", "column")})
                title = chart_spec.get("title", "Chart")
                cat_col = chart_spec.get("categories_col", "A")
                val_cols = chart_spec.get("values_cols", [])
                
                for val_col in val_cols:
                    col_idx = xlsxwriter.utility.xl_cell_to_rowcol(f"{val_col}1")[1]
                    header_name = headers[col_idx] if col_idx < len(headers) else val_col
                    chart.add_series({
                        "name": header_name,
                        "categories": f"='{sheet_name}'!${cat_col}$2:${cat_col}${len(rows)+1}",
                        "values": f"='{sheet_name}'!${val_col}$2:${val_col}${len(rows)+1}",
                    })
                chart.set_title({"name": title})
                ws.insert_chart(f"{chr(65 + len(headers))}2", chart)
                
        wb.close()
        return {"ok": True, "url": f"/static/generated/{doc_id}_{filename}", "path": str(path), "filename": filename}
    except Exception as e:
        log.error(f"Advanced Excel generation failed: {e}")
        return {"ok": False, "error": str(e)}
