# Excel Spreadsheet Skill (Production-Grade)
Use `xlsxwriter` for new files (best formatting) or `openpyxl` if editing an existing template.

## Default Standards
- Header row: Bold, white text on #1E3A5F background, frozen.
- Column widths: auto-fit (min 12, max 40).
- Number formats: Currency `₹#,##0.00`, dates `DD-MMM-YYYY`.
- Zebra striping: alternating row colors (#F8FAFC / #FFFFFF).
- Add a "Summary" sheet with totals and a chart if the data has numeric columns.

## Workflow
1. Create `Workbook(path)`.
2. Write headers with `write_row()` and a format object.
3. Write data rows.
4. Add formulas where applicable (e.g., `=SUM(B2:B10)`).
5. Close and validate.
