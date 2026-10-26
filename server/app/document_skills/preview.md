# Rich Document Preview Skill
When the user asks for a "preview", generate a self-contained HTML file that renders the document exactly as it would appear.

## Rules
- Use the same CSS as the PDF skill.
- Wrap content in a `max-width: 800px` container with a white background and subtle shadow.
- Include a "Download PDF" / "Download DOCX" button that links to the generated file.
- Save the HTML to `static/generated/preview_<id>.html` and return the URL.
