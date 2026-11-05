# Pilot skills - licence verdicts (P0, 4 Nov 2026)

Source: github.com/anthropics/skills (main). Each LICENSE.txt was read; "Apache 2.0" means the full Apache License,
Version 2.0 text, Copyright Anthropic, PBC. Nothing was copied into this repo in P0/P1.

| Skill | LICENSE.txt in folder | Verdict | Action at import (P2-P4) |
|---|---|---|---|
| internal-comms | yes, Apache 2.0 | copy + modify allowed | keep LICENSE.txt, mark changed files, add Hinglish note |
| theme-factory | yes, Apache 2.0 | copy + modify allowed | same; theme-showcase.pdf kept as a shipped, non-readable file |
| frontend-design | yes, Apache 2.0 | copy + modify allowed | same |
| webapp-testing | yes, Apache 2.0 | copy + modify allowed | same; scripts stored, never run until S3 |
| canvas-design | yes, Apache 2.0 | copy + modify allowed | same; fonts folder needs its own per-font licence check |
| mcp-builder | yes, Apache 2.0 | copy + modify allowed | same |
| skill-creator | yes, Apache 2.0 (LICENSE.txt present; text read) | copy + modify allowed | big machinery needs Claude CLI/subagents: Hoola-adapted smaller version |
| doc-coauthoring | NO license file, no `license:` field | DO NOT COPY | write a Hoola-original skill from the idea only |

Apache 2.0 conditions we must meet: (a) give recipients the licence text (kept as LICENSE.txt beside each skill),
(b) mark modified files prominently ("Modified by Newtika for Hoola"), (c) keep copyright / attribution notices,
(d) include a NOTICE file's text if the skill folder has one, (e) no use of Anthropic names/trademarks except to
state where the skill came from. The patent clause ends if we sue over a patent in the work.

Still open: per-font licences inside canvas-design/canvas-fonts (read each before vendoring); any NOTICE file in the
folders (not seen in the listings read so far); the README's statement that the document skills are source-available
applies to docx/pdf/pptx/xlsx, which are NOT in this pilot.
