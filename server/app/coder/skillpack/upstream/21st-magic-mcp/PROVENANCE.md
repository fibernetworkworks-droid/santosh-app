# PROVENANCE — upstream/21st-magic-mcp

- **Upstream**: https://github.com/21st-dev/magic-mcp
- **Commit shipped verbatim**: `6b5299e8a83ceffa73d4fc4e148905bb3eeeeb55` (HEAD of `main` at
  clone time, 2026-11-05; "ci: publish release archives with npm trusted publishing")
- **Package**: `@21st-dev/magic` v0.2.3 — "Magic MCP is now the 21st MCP": a thin
  stdio↔HTTP compatibility proxy to the unified 21st MCP endpoint
  (`https://21st.dev/api/mcp`); the repo also carries the agent-plugin packaging
  (`.claude-plugin/`, `.agents/plugins/`, `server.json`) and the `21st-ui` skill.
- **License**: ISC — Copyright (c) 2026 21st.dev. `LICENSE` ships verbatim in this
  directory. ISC is permissive; verbatim redistribution with the notice is permitted.
- **Exclusions**: `.git/` (version-control internals only). EVERYTHING else ships as-is:
  `src/index.ts` (the whole proxy — the protocol documentation this port was written
  against), `skills/21st-ui/SKILL.md`, `README.md`, `llms-install.md`, `LICENSE`,
  `package.json`, `package-lock.json`, `server.json`, `mcp.json`, `.mcp.json`,
  `smithery.yaml`, `tsconfig.json`, `Dockerfile`, `.claude-plugin/`, `.codex-plugin/`,
  `.cursor-plugin/`, `.agents/`, `.github/`, `assets/logo.png`.
- **No upstream code runs in Hoola.** The Hoola surface is `server/app/coder/magic21.py`
  (the `magic21` tool) — an independent Python implementation of the same wire behavior
  (one POST per JSON-RPC message, session-id echo, 401 latch, NOT_AUTHED wording verbatim
  from `src/index.ts:107-109`) and of the skill's workflow laws. Zero lines copied from
  the TypeScript.
- **Cloned by**: the Hoola feed chain (v0.512.0 HOOLA 21ST), 2026-11-05.
