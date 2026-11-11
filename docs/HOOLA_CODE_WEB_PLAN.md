# Hoola Code like Claude Code on the web — research + plan (11 Nov 2026)

Owner: "MAKE IT SAME EXACTLY AS CLAUDE CODE LOOKS IN WEB" -> "FIRST DO DEEP RESEARCH ON CLAUDE CODE WEB DESIGN AND ITS
ALL 100 % FEATURES AND MAKE A PLAN SAME FOR HOOLA CODE". Nothing in this document is built yet. Read it before touching
`static/console/code.js` or `server/app/devsahayak/`.

**Status (v0.785.0, built as 0.783):** Phase 4 (the workspace engine) is BUILT, behind the switch `dev_workspace` (OFF) - `grep -n "v0.785.0 HOOLA CODE" docs/HISTORY.md`. Decision 2 is answered: **2 live sessions** (`dev_workspace_live`). It is NOT proved on a real Docker box yet: run vps-ops `ws_check`, then `ws_flip`, then the coding cards (easy / hard / mobile) with the engine on - Phase 4 must not lower one. Left out of Phase 4 on purpose, said in HISTORY: a deleted / renamed file is not sent in a change, no hard disk quota on a live checkout, a running command cannot be stopped early, pictures on follow-up messages, the phone app. Phases 5-6 not built. Earlier (v0.779.0, built as 0.777): Phase 3 (the composer) is BUILT too - `grep -n "v0.779.0 HOOLA CODE" docs/HISTORY.md`; the model picker shows the server's forced model instead of a choice while SAB GLM / claude_one_model is on. Earlier (v0.776.0, built as 0.774): Phase 2 (review and the pull request) is BUILT too - see `grep -n "v0.776.0 HOOLA CODE" docs/HISTORY.md`; a mid-work question with choices moved to Phase 4, and Decision 1 (merge when ready) is still open, so merge stays her tap. Phase 0 (design canvas) and Phase 1 (shell + session, v0.773.0, built as 0.768) are BUILT, and on her word Hoola Code is now its own page at `/console/code` with only its own sidebar. Phases 4-6 are not built. Details: `grep -n "v0.773.0 HOOLA CODE" docs/HISTORY.md`.

## 1. How the research was done, and its limits

Two read-only passes on 11 Nov 2026: one over Anthropic's own docs for every feature (about 25 pages under
code.claude.com/docs/en: claude-code-on-the-web, web-quickstart, cloud-environments, routines, desktop, mobile,
permission-modes, remote-control, tools-reference, interactive-mode, whats-new and others), one over the docs, Anthropic's
blog posts and hands-on reviews for layout.

- FEATURES are well sourced: labels, limits and behaviour come from the docs.
- LOOK is only partly sourced. No screenshot could be read; the docs are text. Positions, labels and behaviour are
  documented; fonts, colours, exact widths and the drawing of a tool row are NOT. So "exactly the same" can be met for
  layout and behaviour, and Hoola's own tokens (v0.254 white, v0.253 Literata replies, CRISP TEXT) stay for type and colour.
- The docs do not describe these parts of the web page: sidebar status icons / search, the stop button, the to-do list,
  the subagent display, CI status and merge on web, attachments in the web composer, browser notifications, split vs
  unified diff, the plan approval buttons. For those the plan follows the Desktop app docs (same product, documented) or
  says "our choice".

## 2. Claude Code on the web: the layout

Ten decisions that define it (all sourced):

1. Three zones: sessions sidebar (left), chat (centre), a right "session rail" of stacked status cards (Changes,
   environment, context). The rail hides when the chat gets narrow, and has a show / hide icon in the title bar.
2. Every launch setting lives in ONE row under the prompt box, not in a form. Left to right: environment, repository
   (several allowed), branch, permission mode, model (+ effort, fast mode), usage ring.
3. A "+" beside the prompt box opens a menu: add files or photos, slash commands, plugins, connectors.
4. Tool calls are folded into summaries by default. Three transcript views: Normal (summaries + full replies),
   Thinking (+ thinking), Verbose (every call).
5. Anything she can act on is a CARD in the chat: live to-do list, recap when Claude needs her, code review card
   (Walk through in diff / Fix this one / Apply fixes), suggested tasks, usage-limit card.
6. The diff stats (`+42 -18`) are the door to review. The diff is a pane beside the chat, not a page: file by file,
   "Compare against" another branch.
7. Line comments: hover a line, click "+", type, Enter. Comments QUEUE and travel with her next message.
8. The whole pull request life sits on the Changes card: Create PR (right-click: Create draft PR), CI check status,
   and a menu with Auto-fix and Merge when ready.
9. She can type while it works. The message queues (shown grey, "x" takes it back into the box). A stop button stops.
10. Secondary actions hide in menus: "..." on a session row (Archive, Delete, Open in), a caret by the session title
    (rename, archive, delete, Open in, edit environment, transcript view), an overflow in the title bar.

Title bar: session title (click to rename) + caret, then icon buttons Terminal, Changes, Browser, Files, an overflow menu.
Sidebar: "+ New", nav entries (Projects, Scheduled), sessions under headings with a Group and sort menu (group by
project, sort, status running / waiting / archived), "View all" -> a full page with an Archived tab.

## 3. Claude Code on the web: every feature (short form)

| Area | Features |
|---|---|
| Start | repo picker (multi-repo), branch, environment, mode (Accept edits / Plan / Auto), model, effort, fast mode, attachments, ghost-text suggestion, URL pre-fill (`prompt`, `repositories`, `environment`), start from terminal (`--cloud`) |
| Sidebar | grouped list, working / needs-you state, filters, rename, archive / unarchive, delete (confirm), share (Private / Team / Public), full sessions page |
| In a session | transcript, folded tool calls, 3 view modes, to-do list, thinking, subagents + background tasks pane, queue a message, take it back, stop, question dialog with "Other", plan approval, permission prompts, slash commands, rewind / edit / retry / fork, plugin cards |
| Review | Changes card with counts, diff pane, file list, compare against a branch, inline comments that ride the next message, code review card with fixes |
| Git / GitHub | pushes its branch at a stopping point, Create PR / draft PR with written title + body, session link in the PR, CI status, Auto-fix (CI failures + review comments), Merge when ready, auto-archive after merge |
| Environments | named environment: network None / Limited (allowed domains, package managers) / Full, env vars, network secrets, setup script (cached ~7 days), SessionStart hooks, fixed machine (4 vCPU, 16 GB, 30 GB), pre-installed toolchains |
| Other surfaces | teleport to terminal, Remote Control of a local machine, mobile Code tab, desktop app (Local / SSH / Cloud), Slack |
| Automation | scheduled tasks (hourly / daily / weekly / cron), API trigger URL + token, GitHub event triggers with filters, Run now, run history |
| Notifications | phone push when done or when it needs her, desktop notification, Slack DM |
| Account | plan limits shared with chat, usage ring, admin switches, sharing settings |
| Safety | fresh isolated VM per session, GitHub token never inside the VM (proxy), secrets added outside the VM, all traffic through a proxy, no Bypass mode in cloud |

## 4. Hoola Code today (read from the code)

- Page: `static/console/code.js` (323 lines) + `.hcd-` rules in `v2.css`. Server: `server/app/devsahayak/` (4,730 lines,
  34 routes under /api/devsahayak), test lab `server/app/devlab/` (Docker box, network off, per-repo snapshot).
- It already has: sessions, background start, structured steps, notes while it works, Stop, a read-only plan pass with
  her OK for large jobs, bug proof (test fails first), own review, CI fix rounds, draft PR -> ready, merge card bound to
  the commit, PR reviews with her choice of Comment / Request changes / Approve, her rules, limits.
- Two bugs in the page: every refresh redraws the whole page, so a half-typed note is lost; the spinner is a rotating
  ring (breaks CRISP TEXT).

**The one deep difference.** Claude Code gives each session a real machine with a shell: it clones the repo, runs any
command, keeps the files between messages, and the conversation continues for as long as she likes. Hoola Code today is
a TASK: it reads files through the GitHub API, keeps its edits in memory, has 8 fixed tools (list, search, read, usages,
edit, new file, diff, done) plus "run her declared check" in the lab, and ends. A follow-up is a new "revise" run. So
the look can be matched in the page alone, but about a third of the features (terminal, any command, files pane, a
conversation that continues, environments, setup scripts) need a workspace engine first. That is Phase 4.

## 5. Feature map: Claude Code web -> Hoola Code

Status: HAVE = server ready, page only. SMALL = a few routes / columns. BIG = new engine. NO = not for Hoola (reason).

| Claude Code feature | Hoola status | Phase |
|---|---|---|
| Three-zone shell, collapsible sidebar, rail show / hide | page only | 1 |
| Title bar: rename by click, caret menu, Changes / Files / Terminal buttons, overflow | SMALL (rename) | 1, 4 |
| Sidebar groups + Group and sort, working / needs-you marks | HAVE | 1 |
| Row menu: Archive, Delete (confirm), full page with Archived tab, search | SMALL (archived flag, delete) | 1 |
| Folded tool calls, Normal / Verbose view | HAVE (steps are structured) | 1 |
| Thinking view | SMALL (keep the model's thinking text per step, never sent back) | 5 |
| Live to-do list | HAVE for planned jobs (plan steps); SMALL for others (a `todo` tool) | 1, 4 |
| Queue a message, take it back, stop | HAVE (note queue, Stop); SMALL (delete a queued note) | 1 |
| Question dialog with choices + "Other" | SMALL (an `ask_her` tool; today it asks in plain text) | 2 |
| Plan approval | HAVE | 1 |
| Recap card when it needs her | HAVE (status + next action) | 1 |
| Changes card with counts, diff pane, file list | HAVE (diff + files in the task view) | 2 |
| Compare against another branch | SMALL (GitHub compare API) | 2 |
| Inline line comments that ride the next message | SMALL (comments array on revise) | 2 |
| Code review card: Walk through / Fix this one / Apply fixes | HAVE (own review v0.445); SMALL (fix one point) | 2 |
| Create PR / Create draft PR, written title + body | HAVE | 2 |
| CI status on the card | HAVE | 2 |
| Auto-fix (CI) | HAVE (`dev_ci_loop`, 3 rounds) -> per-PR switch | 2 |
| Auto-fix (reviewers' comments on the PR) | SMALL-BIG (read PR review comments, fix round) | 5 |
| Merge when ready | DECISION 1 below | 2 |
| Auto-archive after merge | SMALL | 2 |
| One settings row under the prompt box | page only | 3 |
| Branch picker (base branch) | SMALL (`base` exists on the task; list branches) | 3 |
| Permission mode: Accept edits / Plan / Auto | HAVE as two switches -> one picker (see section 7) | 3 |
| Model + effort picker | SMALL (v0.740 model list; `dev_loop_model` per task) | 3 |
| "+" menu: files / photos | SMALL (pictures to a model that reads them, text files into the ask) | 3 |
| "+" menu: slash commands | SMALL (/plan /review /tests /explain /compact as kinds) | 3 |
| Ghost-text next suggestion | SMALL (one cheap call after a session ends) | 5 |
| URL pre-fill | page only | 3 |
| Usage ring | SMALL (`usage.run_meter` per session, rupees) | 3 |
| Multi-repo session | BIG | 6, only if asked |
| A real machine: clone, shell, any command | BIG (devlab box kept per session) | 4 |
| Terminal pane, Files pane, background commands | BIG (rides the same engine) | 4 |
| A conversation that continues, rewind / fork | BIG (session = message history + workspace snapshot) | 4 |
| Subagents / background tasks pane | SMALL after 4 (specialist passes shown as children) | 5 |
| Environments: network level, allowed domains | BIG (an allow-list proxy for the box) | 6 |
| Environment variables, setup script, cache | SMALL after 4 (`.hoola/lab.json` setup + snapshot exist) | 4 |
| Secrets added outside the box | BIG (proxy injects) | 6 |
| Scheduled coding tasks, Run now, history | SMALL (Hoola routines engine) | 5 |
| API trigger URL + token | SMALL | 5 |
| GitHub event triggers | BIG (needs a GitHub App / webhooks; Hoola uses her token and polls) | 6 |
| Phone push when done / needs her | SMALL (`push.py` kinds) | 5 |
| Phone screen | exists (`lib/ui`), redraw later | 6 |
| Share a session (read-only link) | SMALL | 5 |
| Teleport to a terminal | NO Hoola CLI -> "Copy git checkout command" + "Open on GitHub" | 2 |
| Remote Control, Desktop / SSH, Slack | NO (Mera PC is frozen; no Slack coding lane) | - |
| Fast mode, plan tiers, admin roles | NO (Hoola has its own models and pricing) | - |
| Bypass permissions | NO, same as Claude Code cloud | - |

## 6. Phases (one version each, tests + a browser walk in every one)

**Phase 0 - design v2 (no code).** Redraw the 7-screen canvas to match section 2: right rail of cards, title-bar
buttons, the settings row in the documented order, the "+" menu, queued message with "x", comments riding the next
message, PR life on the Changes card. Her OK before Phase 1.

**Phase 1 - the shell and the session (page + small server).**
Three zones; sidebar that collapses; rail with show / hide; title bar with rename and caret menu; sessions grouped
with Group and sort, search, Archive / Delete, a full "All sessions" page with Archived. Session: folded step groups,
Normal / Verbose switch, to-do card from the plan, recap card, plan approval bar, queued notes with take-back, Stop.
Only the changed parts are redrawn (fixes the lost-typing bug); no rotating ring. Server: `title` rename,
`archived_at`, delete, delete a queued note.

**Phase 2 - review and the pull request.**
Changes card in the rail -> diff pane (file list, line numbers, long diffs folded, compare against a branch), line
comments that queue and ride the next message, question dialog, code review card with "Fix this one", Create PR /
draft PR, CI checks on the card, per-PR Auto-fix switch, merge per Decision 1, auto-archive after merge, "Copy checkout
command".

**Phase 3 - the composer.**
One settings row: repo, branch, mode, model + effort, usage ring. "+" menu with files / photos and slash commands.
URL pre-fill. Kind chips go away (the mode and her words decide; "explain" and "review" become slash commands).

**Phase 4 - the workspace engine (the big one; changes HOW it codes, so it ships behind a switch).**
Each session gets a real checkout kept in the devlab box for the life of the session: clone outside the box as today,
commands run inside with the network off, a `run_command` tool beside `run_check`, files kept between messages,
background commands with a time limit, a snapshot per message for rewind. The session becomes a conversation (message
history + checkpoint) instead of task + revise. Then the Terminal pane (output only - she does not get a shell, same
as Claude Code), the Files pane, env vars and setup script per repo. Needs: disk and RAM budget on the VPS (Decision 2),
a cap on live boxes, idle pause + rebuild on reopen, durable resume after a server restart (worker slot, not threads).
The old engine stays as the fallback, as the one-shot did under the v0.350 loop.

**Phase 5 - around the session.**
Thinking view, subagent / background pane, reviewers' comments auto-fix, ghost-text suggestion, scheduled coding tasks
with Run now + history, API trigger, phone push, read-only share link.

**Phase 6 - only on her word.** Network levels with an allow-list proxy, secrets injected outside the box, GitHub App
+ event triggers, multi-repo sessions, the phone screen redraw.

Measured after Phases 1, 2 and 4 with the coding cards that already exist (`python -m app.quality code`, hard, mobile):
the page work must not change a score; Phase 4 must not lower one.

## 7. Where Hoola stays different on purpose

- **Merging is her tap.** CLAUDE.md: public changes need a confirm card. See Decision 1.
- **Modes map onto Hoola's rules, not Claude's.** "Ask before the PR" (today's `ask_before_pr`), "Work and open the PR"
  (today's default on private repos), "Plan first" (today's plan gate, forced). Public repos always ask. No Bypass.
- **The GitHub token** stays sealed on the server and is typed only on the settings screen; nothing is cloned or pushed
  from inside the box.
- **Type and colour** are Hoola's console tokens; layout and behaviour follow Claude Code.
- **No rented VM per user.** Phase 4 uses the Docker box on Hoola's own VPS; the per-user cloud PC is inside the Mera PC
  freeze and is not used.

## 8. Decisions only she can make

1. **Merge when ready.** Claude Code merges by itself once checks pass. Options: (a) keep today's rule - Hoola says
   "ready" and she taps Merge (recommended); (b) her switch per PR counts as her tap, bound to the commit she saw, and
   any later push cancels it.
2. **Phase 4 budget.** Each live session box costs disk (the base image is 1.54 GB once, plus a checkout and a
   dependency snapshot per repo) and RAM while a command runs. How many live coding sessions should the VPS allow at
   once? (Suggested: 2 live, the rest paused.)
3. **Order.** Recommended: 0 -> 1 -> 2 -> 3 -> 4 -> 5. Phases 1-3 make it look and behave like Claude Code on today's
   engine; Phase 4 makes it work like Claude Code underneath.
