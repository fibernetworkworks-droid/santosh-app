---
name: sp-finishing-a-development-branch
description: Use when work is done - green suite first, then merge menu
when_to_use: finish the branch, merge the work, wrap up feature, ready to merge
---
Verify tests -> detect environment -> present options -> execute the choice
-> clean up.

STEP 1 - VERIFY TESTS: run the project's FULL suite now (npm test / cargo
test / pytest / go test ./...). "Tests passed earlier this session" is not
evidence - a green run only proves the tree it ran on. Failing -> report the
failures and stop; the menu comes only after a green suite.

STEP 2 - DETECT ENVIRONMENT: GIT_DIR vs GIT_COMMON; capture WORKTREE_PATH
(git rev-parse --show-toplevel) NOW, while still inside the workspace -
cleanup runs from outside later. Normal repo -> standard 3 options, no
worktree cleanup. Linked worktree on a named branch -> standard 3 options,
provenance-based cleanup. Detached HEAD (externally managed) -> reduced 2
options (no merge), workspace left in place.

STEP 3 - BASE BRANCH: whatever the branch forked from - usually named in the
plan, the conversation, or the branch's upstream. Unknown? Ask: "This branch
split from <best guess> - is that correct?" Merging into the wrong base is
expensive to undo.

STEP 4 - PRESENT EXACTLY THESE OPTIONS (normal repo / named-branch worktree):
1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
Detached HEAD: 1) push as new branch and create a PR; 2) keep as-is.
The integration decision is the human partner's - present the menu and wait.
DISCARD happens only when they ask for it in so many words; then confirm
with the full permanent-deletion list and: Type 'discard' to confirm. Only
the typed word 'discard' authorizes deletion - "yeah, get rid of it" does
not count.

STEP 5 - EXECUTE: MERGE - from the main repo root: checkout base, pull,
merge, run the tests on the MERGED result. Failing merged result -> stop,
leave the worktree and branch in place (nothing was pushed; recoverable).
Green -> clean up the worktree, then git branch -d <feature-branch>.
PUSH+PR - git push -u origin <branch> (from detached HEAD:
HEAD:refs/heads/<new-branch>), open the PR against <base> with the forge's
CLI or the creation URL, following the repo's PR template; report the URL;
KEEP the worktree - PR feedback gets fixed there. KEEP AS-IS - report and
stop.

CLEANUP (runs for merge and confirmed discards only; from the main root, so
removal runs outside the worktree): normal repo - nothing to clean. Worktree
under .worktrees/ or worktrees/ (superpowers created it - we own cleanup):
git worktree remove + git worktree prune (self-healing). Removal REFUSED
("contains modified or untracked files" - files that exist nowhere else:
uncommitted plans, notes, scratch)? NEVER --force on your own initiative -
show git -C <path> status --porcelain -uall and ask: commit them to the
branch / move them into the main repo root / delete them (unrecoverable).
Anything else belongs to the HOST environment - leave it in place. Only
clean worktrees you created; a stale-looking sibling is not yours to clean.

FORCE-PUSH LAW: a rejected push means the remote moved - investigate;
force-push only on the partner's explicit request.