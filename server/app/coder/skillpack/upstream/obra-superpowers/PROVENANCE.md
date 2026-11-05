# PROVENANCE - obra/superpowers (fed to HOOLA v0.495.0)

Source: https://github.com/obra/superpowers.git (shallow clone of main,
2026-11-04). Upstream version at feed time: 7.0.2 (.claude-plugin/plugin.json).
Author: Jesse Vincent / Prime Radiant.

License: MIT - the LICENSE file ships in this archive (Copyright (c) 2025
Jesse Vincent). The README's License section states "MIT License - see LICENSE
file for details" and plugin.json carries "license": "MIT". Unlike the
andrej-karpathy-skills feed (which ships no LICENSE file), the license file
itself is present.

What came in, VERBATIM and byte-identical to the clone:
- LICENSE, README.md, AGENTS.md (the contributor/agent guidelines)
- .claude-plugin/plugin.json + marketplace.json (the manifests that name and
  license the upstream project)
- skills/ COMPLETE: all 15 skills, every SKILL.md plus every references/,
  prompts/, templates/ and scripts/ file (80 files). The skills are pure
  advice - process documentation; their bundled scripts (worktree/ledger
  helpers, the visual-companion server, find-polluter.sh, render-graphs.js)
  ride as inert archive text: HOOLA never executes them, and the seeds
  distilled from the SKILL.mds carry the process, not the scripts.

What stayed out (with the reason):
- tests/ (688K) and docs/ (480K): plugin-infrastructure tests and per-harness
  install guides - dev-only, the same class the ui-ux-pro-max feed excluded.
- The 16 per-harness plugin dirs (.agents, .antigravity-plugin, .codex-plugin,
  .cursor-plugin, .devin-plugin, .hermes-plugin, .kimi-plugin, .muse-plugin,
  .opencode, .pi, .github, hooks/, scripts/, assets/, index.js, package.json,
  gemini-extension.json, .version-bump.json, .pre-commit-config.yaml,
  .gitattributes, .gitignore, CODE_OF_CONDUCT.md, GEMINI.md,
  RELEASE-NOTES.md): harness glue and repo plumbing - none of it is the
  methodology, and HOOLA's own skill desk is the harness here.
- RELEASE-NOTES.md (120K): release history, not skill content.

How HOOLA consumes it:
- The 15 seeds (skillpack/sp-<skill-name>.md, one per upstream skill, frontmatter
  name sp-<upstream name>) distill each SKILL.md to the desk's 4,000-char body
  cap, keeping upstream's iron laws and red-flag tables in upstream's words.
  Descriptions start "Use when..." per upstream's own convention. The sp- prefix
  is the lane, not a rename: the v0.492 two-lane model gives a NEW library its
  own once-ever stamp (skills:sp:<tenant>, seed_sp beside seed/seed_byox) so
  already-seeded tenants receive it too; upstream's canonical names live in
  this archive and in the sp-<name> mapping printed at feed time.
- This archive never seeds: the lane globs are top-level only (seed_files =
  non-byox non-sp *.md, byox_files = byox-*.md, sp_files = sp-*.md; the
  upstream/ subtree is test-pinned out).
- No network, no dependencies: nothing here executes or calls out.
