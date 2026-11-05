# Pilot skills - Claude tool -> Hoola tool map (P0, 4 Nov 2026)

What each skill assumes (read from the real SKILL.md files) and what Hoola uses instead. "Status" = what P0/P1
established; nothing here is imported yet.

| Skill | Assumes | Hoola equivalent | Status |
|---|---|---|---|
| internal-comms | read examples/*.md | `skill_manage read_file` (P1 done) | importable once P1 ships; add Hinglish examples |
| theme-factory | read themes/*.md, show a PDF | `read_file` for themes; PDF is shipped but not readable (binary) | importable; the showcase PDF can be offered as a file card later |
| frontend-design | write HTML/CSS, optional screenshot | artifact tools, `site/kit.py` rules, Playwright screenshot in browser worker | importable; add a precedence line vs existing site kit rules |
| webapp-testing | Playwright (python), shell, `scripts/with_server.py` | `server/browser_worker` (Playwright) | guidance usable now; script execution waits for S3 (sandbox + approval) |
| canvas-design | render png/pdf by code, fonts, download fonts | Create Studio / HOOLA PRINT; Hoola's bundled fonts | needs a render path decision + font licence check |
| mcp-builder | network (WebFetch/search), npm, npx inspector, python | Developer Sahayak, `app/devlab` (network off by default), scrape tools | usable as guidance; build/run steps need the dev lab |
| skill-creator | subagents, `claude -p`, browser viewer, python scripts, TodoList | skill desk telemetry + a Hoola eval run (new skills card) | Hoola-adapted smaller version (P4) |
| doc-coauthoring | create_file, str_replace, artifacts, optional MCP + subagent | doc_studio, artifacts | Hoola-original (no licence to copy) |

## P1 changes that make these importable (done, server/app/coder)
- Folder skills: `skills/<tenant>/<name>/SKILL.md` + resources; old `<name>.md` files unchanged.
- Claude limits for IMPORTED skills only (description 1,024, body 30,000); model-written skills stay 60 / 4,000.
- `imported: true` is stamped in the frontmatter and survives every update/park; imported skills are never nominated.
- Extra frontmatter kept: when_to_use (searchable), disable-model-invocation (kept out of the shortlist), license,
  user-invocable, allowed-tools, paths, context, model, argument-hint, compatibility (stored, not yet acted on).
- `skill_manage read_file(name, path)`: one bundled text file, confined to the skill folder, 60k chars cap,
  binary files listed but not readable.
- Zip import/export (`POST /api/coder/skills/import-zip`, `GET /api/coder/skills/export-zip?name=`): no '..',
  no absolute paths, no symlinks, no executables, 200 files / 8 MB / 1 MB per file, one skill per zip.
- Import of raw markdown under Claude's limits: `POST /api/coder/skills/import` with `"format": "claude"`.
- Injected prompt lines cut an imported description to 110 chars.
- Scripts are STORED only. Nothing is executed (that is S3).
