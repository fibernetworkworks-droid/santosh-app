---
name: byox-web-browser
description: Build a browser: HTML parser, CSS, box layout, paint
when_to_use: web browser from scratch, own browser, html renderer
---
GOAL: a browser that correctly renders a simple webpage with styled text and boxes.

PHASES
1. HTTP client + HTML tokeniser → element tree (handle malformed HTML gracefully).
2. CSS parser: rule matching by tag/class/id; specificity; cascade (last wins).
3. Block layout: width/height from CSS; margin, padding, border; vertical stacking.
4. Paint: background, borders, inline text; write to SDL/Cairo pixel buffer.
5. Inline layout: text wrapping at word boundaries; render a Wikipedia paragraph.

CORE CONCEPTS
- DOM tree: element nodes + text nodes; attributes as a dict.
- Box model: content + padding + border + margin; border-box vs content-box.
- Inline formatting context: words placed left-to-right; line breaks create new line boxes.

VERIFY: render `<p style="color:red;font-size:20px">Hello</p>` correctly; text is red.
