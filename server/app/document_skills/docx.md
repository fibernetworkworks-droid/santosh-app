# Word Document Skill (Production-Grade)
Use `python-docx`.

## Default Standards
- Margins: 1 inch (2.54 cm) all sides.
- Body font: Calibri, 11pt.
- Headings: Use built-in `Heading 1`, `Heading 2` styles (do not manually bold).
- Tables: Use `Table Grid` style, header row bold with #D9E2F3 background.
- Page numbers in footer.

## Workflow
1. Create `Document()`.
2. Add headings with `add_heading()`, paragraphs with `add_paragraph()`.
3. Save and validate.
