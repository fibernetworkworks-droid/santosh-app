---
name: byox-text-editor
description: Build a terminal text editor: gap buffer, raw mode, syntax highlight
---
GOAL: a Kilo-like editor that opens a file, edits it, saves, and highlights syntax.

PHASES
1. Raw terminal mode (termios): disable echo + canonical; read individual keypresses.
2. Render file lines to terminal with ANSI escape codes; arrow keys move cursor.
3. Insert and delete characters (gap buffer or rope); horizontal scrolling.
4. Open / save file; dirty flag; Ctrl-S / Ctrl-Q with unsaved-changes warning.
5. Syntax highlighting for C/Python via keyword lookup + comment/string colouring.

CORE CONCEPTS
- termios: TCSAFLUSH disables ECHO + ICANON; restore on exit.
- Gap buffer: array with a gap at the cursor; insert = shrink gap; move = copy chars.
- ANSI: `\x1b[2J` clear; `\x1b[H` home; `\x1b[1;32m` bold green; `\x1b[m` reset.

VERIFY: open source.c; edit a function name; save; file on disk reflects the change.
