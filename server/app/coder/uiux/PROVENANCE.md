# PROVENANCE - vendored UI/UX Pro Max engine

- Source: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill (upstream v2.15.0)
- License: MIT (NextLevelBuilder) - `LICENSE` beside this file; the license text is
  preserved verbatim and this vendor notice records the import.
- Imported: 2026-11-04, upstream commit as of clone date.
- v0.753: `data/` was never committed with the scripts (the tool answered "File not found" from v0.498 on);
  restored from upstream commit 6ae86f6 (2026-11-10), whose `src/ui-ux-pro-max/scripts/` is byte-identical to
  the vendored scripts here, so the data matches the engine.
- HOOLA release that vendored it: v0.486.0 (HOOLA UIUX PRO MAX).

## What came in

- `scripts/` - the search engine verbatim: `search.py` (CLI), `core.py` (BM25 over the
  CSV databases), `design_system.py` (the --design-system aggregator + --persist
  Master/Overrides writer), `reasoning_contract.py` (its dependency).
- `data/` - the databases verbatim: 12 domain CSVs + `ui-reasoning.csv` +
  22 stack CSVs under `stacks/` + the small provenance/license JSONs.

## What was left out (dev-only upstream, never needed at runtime)

- `scripts/tests/` (upstream's own suite), `scripts/validate_data.py` (dev validator),
  `templates/`, `references/`, gallery/screenshots/READMEs (repo furniture).
- `data/phosphor-icons-upstream.json` (upstream icon provenance, not read by the engine).

## What HOOLA adds (none of it inside the engine)

- `server/app/coder/uiux_tool.py` - the ONE tool wrapper (`uiux_design`): gate
  (coder_enabled + coder_uiux), asyncio.to_thread, subprocess timeout 30 s, query cap
  400 chars, output cap 24k, per-tenant `--output-dir` under the vault, `--force`
  never passed. The engine files themselves are UNMODIFIED upstream code.
- `server/app/coder/skillpack/uiux-pro-max.md` - the seed skill that teaches when/how.
