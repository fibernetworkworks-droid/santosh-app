# CODING HARNESS — research + plan: what makes Claude Code's long coding work, and what Hoola is missing

**Owner's ask (2 Nov 2026):** *"FIRST DO EXTREME DEEP RESEARCH ON HOW CLAUDE CODE DO PERFECT CONTINUOUS, LONG CODING,
DEBUGGING ETC — FIND PERFECT REPORT FIRST."* No code was written for this document. Read §1 and §5; the rest is
reference.

**Sources.** Anthropic's own docs and engineering writing (code.claude.com/docs, anthropic.com/engineering →
now redirecting to /research), platform.claude.com tool-use docs, the SWE-agent paper (arXiv 2405.15793), and the
vendor docs of Cursor, OpenAI Codex cloud, Google Jules, Devin, Aider and OpenHands. All fetched 2 Nov 2026 by four
parallel research agents; every claim below carries its source. **Two URL moves worth knowing:**
`anthropic.com/engineering/claude-code-best-practices` now 308-redirects to `code.claude.com/docs/en/best-practices`
and serves a REWRITTEN doc — the April 2025 "explore, plan, code, commit" essay is no longer at that URL, so any
advice quoted from memory of it is unverifiable. `docs.cursor.com/*` → `cursor.com/docs/*`,
`developers.openai.com/codex/*` → `learn.chatgpt.com/docs/*`.

**Honesty markers used throughout:** *verified* = read on the vendor's page; *not verified* = could not be confirmed
from a primary source. Hoola-side facts are cited as `file:line` from this repo and were measured, not remembered.

---

## 1. THE FIVE FINDINGS THAT DECIDE EVERYTHING

### 1.1 The harness matters as much as the model — and it is measured
SWE-agent's ablation (arXiv 2405.15793, Table 3) is the only published controlled experiment on this question: **the
model is held fixed (GPT-4 Turbo)** and only the agent's INTERFACE changes. SWE-bench Lite, % resolved:

| interface change | % resolved | delta |
|---|---|---|
| edit tool **with a linter guardrail** (default) | **18.0** | — |
| edit tool without linting | 15.0 | **-3.0** |
| no edit command at all | 10.3 | -7.7 |
| **100-line file window** (default) | **18.0** | — |
| whole file shown instead | 12.7 | **-5.3** |
| **last 5 observations** (default) | **18.0** | — |
| full history kept | 15.0 | **-3.0** |
| **summarized search** (default) | **18.0** | — |
| iterative search (strictly more capable) | 12.0 | **-5.7** |

Their four design principles, verbatim: *"Actions should be simple and easy to understand for agents" · "Actions
should be compact and efficient" · "Environment feedback should be informative but concise" · "Guardrails mitigate
error propagation and hasten recovery."*

Two conclusions Hoola must act on. First, **a noisier interface loses even when it shows more** (iterative search is
-5.7 while being more powerful). Second, these are all harness knobs — nothing here is bought by swapping in a better
model. Anthropic says the same from the other side: *"While building our agent for SWE-bench, we actually spent more
time optimizing our tools than the overall prompt"* (anthropic.com/engineering/building-effective-agents), and Sonnet
3.5's SWE-bench Verified SOTA came *"after we made precise refinements to tool descriptions"*
(anthropic.com/engineering/writing-tools-for-agents).

### 1.2 Without a pass/fail command, the agent only knows "looks done" — and the user IS the test suite
The central doctrine of the current Claude Code best-practices doc, verbatim:

> *"Claude stops when the work looks done. If it has nothing to run that tells it whether the work actually is done,
> 'looks done' is all it has to go on. In practice that makes you the test suite, and every mistake sits there until
> you happen to notice it. If you give it something that comes back pass or fail, Claude can close that loop itself.
> It makes the change, runs the check, and if something broke it reads the output and fixes it before running the
> check again."*
> — code.claude.com/docs/en/best-practices

And: *"ask Claude for **evidence**: the command it ran and its output... 'All tests pass' on its own tells you very
little."* **This is exactly Hoola's position today: Meghana is the test suite.** The repo's code never runs on
Hoola's server (`devsahayak/rules.py:24`), so the only oracle is her CI after a push — minutes per iteration, in
public branch history, and nothing observable in between.

Their four escalating strictness levels for "when is it done" map 1:1 onto a harness design, verbatim:
in the prompt (*"keep going until they pass"*) → as a goal (*"a separate model checks against the conversation after
every turn"*) → **as a Stop hook** (*"enforced by Claude Code (the harness), so the turn doesn't end until the
typecheck passes"*, exit code 2 blocks, 8 consecutive blocks then it gives up) → **by a fresh reviewer that never saw
the conversation**.

### 1.3 Compaction is NOT how long work is done — a structured handoff is
> *"The core challenge of long-running agents is that they must work in discrete sessions, and each new session begins
> with no memory of what came before. Imagine a software project staffed by engineers working in shifts, where each new
> engineer arrives with no memory of what happened on the previous shift."*
> *"**Compaction isn't sufficient.** Out of the box, even a frontier coding model... running on the Claude Agent SDK in
> a loop across multiple context windows will fall short of building a production-quality web app."*
> — anthropic.com/engineering/effective-harnesses-for-long-running-agents

What they use instead, and every piece of it is a FILE, not a conversation:
- an **initializer** session with a different prompt from every later session;
- a **JSON feature list** (200+ features for a claude.ai clone), all starting as failing, which coding agents may edit
  **only by flipping a `passes` field** — *"It is unacceptable to remove or edit tests"* — and **JSON on purpose**
  because *"the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files"*;
- **one feature at a time**: *"This incremental approach turned out to be critical to addressing the agent's tendency
  to do too much at once"*;
- a **`claude-progress.txt`** log and **a git commit per session**, so the model can use git to revert its own bad work;
- a **session-start ritual**: `pwd`, read git log + progress file, read the feature list, pick the highest-priority
  unfinished item — and run a smoke test on the dev server **before** starting anything new, because *"if the agent had
  instead started implementing a new feature, it would likely make the problem worse"*;
- a definition of **"clean state"** as the hand-off contract: *"the kind of code that would be appropriate for merging
  to a main branch... a developer could easily begin work on a new feature without first having to clean up an
  unrelated mess."*

A later post (anthropic.com/engineering/harness-design-long-running-apps, Mar 2026) adds planner → generator →
evaluator, agents communicating **through files**, a **"sprint contract"** agreed before any code is written, and
distinguishes a **context reset** (fresh agent + structured handoff) from compaction (same agent, summarized). Its
published cost: solo run 20 min / $9 vs the full harness 6 hr / $200 — *"over 20x more expensive"*. Long work is not
free.

### 1.4 Every serious competitor runs code in an isolation boundary, and most turn the network OFF
| | execution environment | network |
|---|---|---|
| Claude Code | your machine; optional sandbox (macOS Seatbelt / Linux bubblewrap) | sandbox: *"No direct route out"*, proxy + `allowedDomains` starting empty |
| Codex cloud | cached container, image `universal` (12 h cache) | **off by default during the agent phase**; setup scripts online; secrets removed before the agent starts |
| Jules | short-lived Ubuntu VM (Node/Python/Go/Java/Rust/Docker) | not documented |
| Devin | Linux VM + VSCode + shell + browser, per-session snapshot | not documented |
| Cursor | local terminal in OS sandbox, or cloud VMs | 3 modes, ~100 default-allowed domains |
| OpenHands | **Docker**, stated reason: *"Executing untrusted code can pose significant risks to the host system"* | — |
| Aider | your own machine, no sandbox | yours |

Anthropic's own warnings, which apply directly to anything Hoola builds:
*"The sandbox covers only shell commands. Claude's file tools, MCP servers, and hooks run outside it"* and is
therefore *"not sufficient for fully unattended runs"*; **Bash allowlists on command text are *"fragile"*** (worked
bypasses: options before the URL, a different protocol, redirects, `URL=... && curl $URL`); *"Avoid mounting host
secrets"*; and for the API bash tool: *"Treat every command as untrusted input... Run the session in an isolated
environment, such as a container or a virtual machine, as the least-privileged user that can do the work."*

### 1.5 Truncation and output shape are first-class features, not plumbing
Claude Code's measured contract (code.claude.com/docs/en/tools-reference): output streams to a file as the command
runs; **a command whose output passes 5 GB is killed**; a successful result comes back inline up to ~**30,000
characters** and past that as **a file path plus a 2,000-char preview that Claude can grep**; a **failing** result
comes back as *"a head-and-tail excerpt"* of ~**10,000 characters, with no file path**. Exit code 1 counts as success
only for a named list (`grep`, `rg`, `find`, `diff`, `test`, `git diff`, `git grep`); **everything else exiting 1 is a
failure**, so a failing test run gets the SMALLER window.

**Our research flagged this as backwards for debugging, and I agree: the failing run is the one whose full output you
want.** Hoola should give failures the LARGER window and always hand back the log path. This is the cheapest single
improvement on the whole list.

Also from the same contract, worth copying: when a foreground command times out, **it is moved to the background with
a task ID and an output file, not killed** (defaults: 2 min command timeout, 10 min ceiling, 30 min background).

---

## 2. HOW CLAUDE CODE SUSTAINS A LONG SESSION (mechanisms, with citations)

| mechanism | what it does | detail that matters |
|---|---|---|
| auto-compaction | summarizes the conversation at the context limit | *"The summary keeps your requests and key code snippets, but detailed instructions from early in the conversation may be lost."* Window settable 100K–1M. Stops after a few failed attempts rather than looping |
| **re-injection from disk** | what survives compaction is RE-READ, not remembered | project CLAUDE.md, rules, auto memory, **the plan from plan mode**, skill descriptions, system prompt; up to 5 recently modified files re-read; `SessionStart` hooks with matcher `compact` re-run |
| CLAUDE.md hierarchy | managed → user → project → local, all **concatenated**, closer dirs last | *"Claude treats them as context, not enforced configuration. To block an action regardless of what Claude decides, use a PreToolUse hook instead."* Target < 200 lines; `@imports` max 4 hops |
| auto memory | first 200 lines / 25 KB of MEMORY.md at session start, topic files on demand | machine-local, shared across worktrees |
| task list | TodoWrite / Task* tools | *"Tasks persist across context compactions."* Default only on older models; newer ones track multi-step work without a written list |
| subagents | isolated context, own model, own tools | gets the delegation message + CLAUDE.md, **not** the conversation; *"returns only the summary"* (~1–2k tokens); each spends its own tokens; agent teams ≈ **7x** tokens |
| hooks | the deterministic layer | PreToolUse can block/rewrite (**exit code 2** = stop); Stop can send the model back (8-block cap); PreCompact can block; `@`-mentions bypass PreToolUse because no tool call is made |
| permission modes | default / acceptEdits / plan / auto / dontAsk / bypassPermissions | auto-mode classifier **pauses after 3 consecutive or 20 total blocks**; *"not an isolation boundary"*; deny rules bind in every mode |
| plan mode | research + propose, edits blocked until approval | the plan is re-injected after compaction |
| `/goal` | a condition a separate model checks after every turn | the judge *"doesn't run commands or read files independently"*, so the condition must be provable from the transcript; at most 3 idle check-ins |
| checkpoints | file snapshot before each edit, Esc-Esc rewinds | *"Actions that affect remote systems... can't be checkpointed"* |
| resume | JSONL transcript per session; `--continue` / `--resume` / `/branch` | *"a tool that was still running when the previous process ended... doesn't get rerun when you resume"* |

**The tool-design rules** (anthropic.com/engineering/writing-tools-for-agents), which are the cheapest thing on this
whole page to copy: a tool is *"a contract between deterministic systems and non-deterministic agents"*, so **do not
wrap your API endpoint-for-endpoint**; build *"a few thoughtful tools targeting specific high-impact workflows"*
(`search_logs` not `read_logs`; `get_customer_context` not three getters); *"If a human engineer can't definitively say
which tool should be used in a given situation, an AI agent can't be expected to do better"*; **return only
high-signal fields**, resolve UUIDs to names; cap responses (**Claude Code's own number is 25,000 tokens**);
**poka-yoke the signature** (absolute paths only; `old_str` must match exactly once); and *"prompt-engineer your error
responses to clearly communicate specific and actionable improvements, rather than opaque error codes or tracebacks"*.

---

## 3. WHERE HOOLA STANDS TODAY (measured in this repo, 2 Nov 2026, v0.451)

**What is already right, and matches the research:**
- an 8-tool step loop with read-before-edit, exact-match, unique-match editing (`devsahayak/loop.py`) — the same
  contract Claude Code's Edit tool enforces, including the "read it first" rule;
- **project rules read first**, longest and before anything else (`loop._project_rules`, `RULES_KB = 60`) — this is
  CLAUDE.md-for-her-repo, and it predates our reading of the research;
- a **plan pass + approval gate** for big work (v0.451), which is Jules's gate and ECC's Gate 1;
- a **fresh-eyes reviewer** on its own PR (v0.445) — level 4 of the "when is it done" ladder;
- **red-then-green proof of a bug** through her CI (v0.447) — the right idea, the slowest possible oracle;
- CI fix rounds (3) with the failure log fed back (v0.352);
- cards that measure real jobs: easy 12/12, hard 12/12, mobile 10/10.

**The caps, as they actually are:** 40 steps / 20 min a job, `READ_LINES = 400`, tool results truncated at
**60,000 characters** with no overflow file (`loop.py` `content: out[:60000]`), 20 files / 1500 lines a change,
`BRAIN` = Opus at effort high, `max_tokens = 16000`.

**The four real gaps, each confirmed in code:**
1. **No execution of her code, so no pass/fail oracle** (`rules.py:24`: *"tests aapke CI mein chalte hain"*). Her CI is
   the only check, at minutes per round, capped at 3 rounds.
2. **No context management in the coding loop.** `messages` grows unbounded across up to 40 steps of 400-line reads;
   the only guard is for a cut *reply* (`stop == "max_tokens"`), not an overflowing input. The chat side has had
   compaction since v0.242 and a context gauge since v0.239 — the dev loop has neither. Per §1.1 this is also a
   *quality* bug, not just a crash risk: full history scored **-3.0** against keeping the last five observations.
3. **No failure-first truncation and no searchable log.** A long CI failure arrives as a flat 60k-char slab; there is
   no log file the model can grep, and no head-and-tail shaping.
4. **No session handoff for long work.** A task row carries `log`, `changes` and now `plan`, but there is no
   progress-notes artifact, no feature list, and no session-start ritual; `tick()` resumes only `ci_running` tasks.

**And the finding that changes the cost of fixing #1: Hoola already runs tests — just never on her repo.**
`quality/codecard.py` runs pytest, `node --test`, the Dart VM and kotlinc in a throwaway temp dir with CPU/memory/file
rlimits and a scrubbed environment (`_py`, `_seq`, `_pytest`); `pylab/runner.py` is stronger still — rlimits plus
process-group kill plus **its own empty network namespace where the kernel allows it**. The machinery exists and is
wired only to the practice cards.

**The two obstacles that are real, and must be decided before any of it is built:**
- **Isolation.** Running her repo's test code on the VPS is arbitrary code execution on the box that holds every
  user's sealed keys. Per §1.4 the only honest boundary is a container or VM, and per CLAUDE.md v0.361 **this VPS has
  no `unshare -rn`**, so pylab's network namespace is unavailable here. Options: a Docker container on the VPS (needs
  ops confirmation that Docker is available), or the per-user cloud VM that already exists in the product (v0.193
  HOOLA KA APNA PC / `desktop-linux/`) — **which is inside the owner's PC freeze and cannot be touched without her
  explicit ask in chat**.
- **Dependencies.** The card repos have none; a real repo needs its own installed. Every competitor solves this the
  same way — a declared setup step plus a cached image or snapshot (Codex `universal` + 12 h cache, Jules "Run and
  Snapshot", Devin's blueprint, Cursor's environment snapshot). There is no shortcut.

---

## 4. THE GAP, RANKED (research agents' ranking, which I accept)

**For long multi-file work** — the failure mode is drift, so state and environment dominate:
reproducible environment > persistent workspace > repo-wide search and static checks > in-loop tests > instrumented
debugging. On a 30-file change the first question is "does this even build", the second "is my half-done refactor
consistent", the third "who else calls this symbol" — and the third is answered far more cheaply by a repo map and a
type-checker than by a test run. (Aider's tree-sitter repo map, graph-ranked over dependency edges with a 1k-token
budget, exists precisely for that question.)

**For debugging** — the failure mode is a wrong hypothesis, so cycle time and observability dominate:
in-loop tests > instrumented debugging > shell > persistent workspace > environment.

---

## 5. THE PLAN (nothing built yet; each phase stands alone and is measurable)

Ordered by value per rupee and by risk. **H1 and H2 need no execution at all** — they are harness quality, they are
measurable on the existing cards, and per §1.1 they are worth real points.

**H1 — SAAF FEEDBACK (the interface fixes).** Failure-first truncation: stream a long tool result to a file, return
the **tail** on failure (the traceback is at the end) and the head on success, always with the byte count and the log
path, plus a `grep_log(task, pattern)` tool so the model can ask the log a second question. Audit every tool error
message against *"the error must contain the fix"*. Keep file reads windowed (we are at 400 lines; SWE-agent's best
was 100) and measure. *Cost: small. Risk: low. Measured by: code cards, before/after.*

**H2 — LAMBA DIMAAG (the coding loop survives its own length).** Prune old observations instead of carrying full
history (SWE-agent: **+3.0**), keep the last N tool results in full and collapse older ones to one line each; add an
input-size gauge and, at the limit, a **structured handoff** rather than a summary: write the progress notes + the
plan's `done_when` state, then re-enter with a fresh context (Anthropic: *"compaction isn't sufficient"*).
*Cost: small-medium. Risk: low — it only shortens prompts. Measured by: a long-job card that today dies.*

**H3 — PRAYOGSHALA (the lab: run her checks locally).** One tool, `run_check`, that runs a **declared** command (from
her repo's CI / AGENTS.md / her settings — never invented, exactly as Aider's `--test-cmd`, Devin's `knowledge`
`lint`/`test`/`build`, Jules's setup script) against a throwaway copy of the branch, with rlimits, no secrets in the
environment, a hard timeout, auto-background on timeout, and H1's output shaping. Then: the v0.447 bug proof becomes
local and takes seconds instead of a CI round, and the v0.451 plan's `done_when` lines become **executed**, not
asserted. **Blocked on the isolation decision in §3 — do not start without it.** *Cost: large. Risk: high (this is
the one that can hurt the server). Measured by: a new debugging card set, plus pass@3.*

**H4 — NAKSHA (repo map).** Aider-style: tree-sitter symbols + a dependency graph ranking, a 1–2k token budget, given
to the plan pass and the edit loop. Answers "who calls this" without execution; ranked top-two for long multi-file
work. *Cost: medium. Risk: low.*

**H5 — SHIFT HANDOFF (long jobs over many sessions).** The Anthropic harness, adapted: progress notes per task, a
**JSON** checklist the model may only flip `passes` on, one feature at a time, a commit per step (we already commit
per round), and a session-start ritual that reads the notes and runs the smoke check **before** new work.
*Cost: medium. Risk: low. Needs H3 for the smoke check to mean anything.*

**H6 — SABOOT SE REVIEW (evidence, not claims).** The v0.445 self-review and the v0.447 proof must carry **the
command and its output**, per *"ask Claude for evidence"*. Needs H3. *Cost: small on top of H3.*

**H7 — PASS@3 + a debugging card set.** Run each card job three times (ECC's `eval-harness`, Anthropic's held-out
sets) so one lucky pass stops counting; add jobs that can only be solved by running something. *Cost: small. Risk:
low — it only measures.*

**What I will NOT propose, and why:** a full per-user VM for coding (the product already has one, and it is frozen);
Claude-Code-style hooks (Hoola has no equivalent surface — our deterministic layer is Python in the harness, which is
better); giving the coding loop network access inside the sandbox (§1.4 — Codex turns it off during the agent phase
and so should we); and copying Claude Code's failure truncation exactly (§1.5 — it is backwards for debugging).

**Open questions only she / ops can answer:**
1. Is **Docker** usable on the VPS for a test container? If not, H3 needs the frozen cloud-PC VM — which needs her
   explicit word.
2. Which repos may ever run their code? (My recommendation: **only repos she owns**, never a third party's, and never
   a public one.)
3. Is a per-repo **setup command + cached snapshot** acceptable to maintain (every competitor requires one)?

**Honest summary.** H1, H2, H4 and H7 close the part of the gap that is about the harness, cost little, and are
measurable this week. H3 is the part that separates "writes good PRs" from "works like Claude Code", and it is a real
engineering project with a real security decision attached. The research does not support building H3 first.

---

## ANSWERED + BUILT (5 Nov 2026)

**Her answers to the three open questions above:** *"Docker on the VPS -- YES, OWN AS WELL AS THIRD PARTY CLONEING
FOR CHECKING, setup command + cached snapshot acceptable to maintain -- SAME AS CLAUDE CODE."* So H3 is unblocked and
third-party repos are in scope — which is sound only because nothing of hers is inside the box (no token, no `.git`,
no secrets, no network on a check).

**v0.456 — H3 step 1, the box.** `app/devlab`: `box.py` (the walls), `spec.py` (the command is declared, never
invented), `service.py` (clone outside, snapshot once per lock-file hash, sealed check), `out.py` (failure-first
output + a greppable log). Proof on her VPS: `python -m app.devlab check` / vps-ops `lab_check`.

**v0.531 — H3 step 2, the caller.** `devsahayak/lab.py` + `run_check` / `grep_log` in the coding loop; the bug proof
measured locally (red-then-green in seconds) instead of pushing a deliberate red commit; the plan's `done_when` lines
RUN; the lab's evidence handed to the own review and written into the PR. One clone per task, reused — the persistent
workspace this document ranked first for long multi-file work.

**Still not built from this plan:** H1 (the loop's own tool-output shaping — the lab has it, `ws.run` results do not),
H2 (no context management in the coding loop: `messages` still grows unbounded, and SWE-agent's last-5-observations
finding says that costs quality as well as crashes), H4 (the tree-sitter repo map), H5 (progress notes + a JSON
feature list + the session-start ritual), H7 (pass@3 and a debugging card set). **H2 is the next one worth doing**:
it is cheap, it needs no execution, and the ablation table says it is worth real points.
