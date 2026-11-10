---
name: sp-using-git-worktrees
description: Use when starting feature work - isolated workspace first
when_to_use: git worktree, separate workspace, feature branch setup
---
Ensure work happens in an isolated workspace. CORE PRINCIPLE: detect
existing isolation first, then native tools, then the git fallback - never
fight the harness.

STEP 0 - DETECT EXISTING ISOLATION (before creating anything): compare
git rev-parse --git-dir with --git-common-dir (both resolved to real paths).
Different (and NOT a submodule - check git rev-parse
--show-superproject-working-tree; submodules fool this test)? You ARE
already in a linked worktree: do NOT create another - go straight to project
setup, reporting the path and branch (or detached HEAD, externally managed).
Same dir (or in a submodule): normal checkout. No worktree preference
declared in your instructions? Ask consent: "Would you like me to set up an
isolated worktree? It protects your current branch from changes." Honor a
declared preference without asking; declined -> work in place.

STEP 1A - NATIVE TOOLS FIRST: is there a worktree tool (EnterWorktree,
WorktreeCreate, a /worktree command, a --worktree flag)? Use it and skip to
setup. Native tools own directory placement, branch creation, and cleanup;
running git worktree add beside them creates PHANTOM STATE your harness
cannot see or manage - the #1 mistake.

STEP 1B - GIT FALLBACK (only with no native tool): directory priority -
explicit user preference beats everything; then an existing project-local
.worktrees/ (preferred) or worktrees/; then default to .worktrees/ at the
project root. SAFETY (project-local only): the directory MUST be ignored -
git check-ignore -q; if NOT ignored, add it to .gitignore and commit first
(an unignored worktree directory commits the whole tree into the repo).
Then: git worktree add <path> -b <branch>. Sandbox denied the create? Say
so, and run setup and baseline tests in place instead.

STEP 2 - PROJECT SETUP: auto-detect and run - package.json -> npm install;
Cargo.toml -> cargo build; requirements.txt -> pip install;
pyproject.toml -> poetry install; go.mod -> go mod download.

STEP 3 - VERIFY CLEAN BASELINE: run the project's tests NOW. A dirty
baseline makes every later failure ambiguous. Failing -> report the failures
and ask whether to proceed or investigate (proceeding is the partner's
call). Passing -> report ready: worktree path, N tests 0 failures, ready to
implement <feature>.

RATIONALIZATIONS: "I'm obviously not in a worktree - no need to check" -
run Step 0; harness-created isolation and submodules both fool eyeballing.
"git worktree add is quicker than hunting for a native tool" - bypassing
the native tool creates unmanageable phantom state. "The worktree directory
is surely ignored already" - run check-ignore. "The workspace is fresh -
baseline tests can wait" - they can't; proceed past failures only with the
partner's say-so.