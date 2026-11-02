# How Anthropic's Claude products and APIs carry long, multi-step tasks to completion

Scope note: these are research notes as of 2 Nov 2026. Primary Anthropic sources were preferred. Where only third-party coverage exists, that is said in place. Dates are given so the reader can tell older guidance from current guidance. Not covered directly: Claude Code hooks / TodoWrite docs pages, the Cowork product page, the computer-use docs, prompt caching docs and the extended-thinking docs (see Gaps).

## 1. What is the core agent loop and how does it decide it is done (stopping criteria)?

### Takeaway
Anthropic's loop is simple: the model calls tools, reads what the environment returns ("ground truth"), and repeats until it judges the task complete or a harness limit stops it. Claude Code describes three phases that blend together: gather context, take action, verify results. In practice, "done" is decided by the model reading external signals (tests, verifier output, a feature list), with hard caps such as maximum iterations as a backstop. Anthropic reports that the model's own sense of "done" is unreliable (it declares victory early), so long-running harnesses put the definition of done outside the model.

### Cited Findings
- Agents are "typically just LLMs using tools based on environmental feedback in a loop"; they should gain "ground truth" from the environment at each step (tool results, code execution) to judge progress — [Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- Workflows vs agents: "Workflows are systems where LLMs and tools are orchestrated through predefined code paths"; agents are systems where the LLM directs its own process and tool use — [Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- Stopping: "it's also common to include stopping conditions (such as a maximum number of iterations) to maintain control"; "Agents can then pause for human feedback at checkpoints or when encountering blockers" — [Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- Five workflow patterns named: prompt chaining, routing, parallelization (sectioning / voting), orchestrator-workers, evaluator-optimizer ("one LLM call generates a response while another provides evaluation and feedback in a loop") — [Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- Claude Code loop: "gather context, take action, and verify results. These phases blend together." Claude "decides what each step requires based on what it learned from the previous step, chaining dozens of actions together and course-correcting along the way." The user can interrupt at any point; a queued message is read "as soon as those calls finish, within the same turn" — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- Example "fix the failing tests" loop: run tests → read errors → search → read files → edit → run tests again to verify — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- "Claude Code is the layer around the model that provides the tools and manages the context the model sees. This surrounding layer is what the term agentic harness refers to." — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- At the API level the loop runs until `stop_reason` is no longer `tool_use`; SDK tool runners expose `until_done()` and a `max_iterations` cap (e.g. 10 in the examples) — [Memory tool docs (code examples)](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- Research system: the lead agent decides whether more research is needed, can spawn more subagents or change strategy, and "exits the loop once it has enough information" — [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Effort scaling rules are written into the lead's prompt so it knows how much work is "enough": simple fact-finding = 1 agent, 3-10 tool calls; direct comparisons = 2-4 subagents, 10-15 calls each; complex research = more than 10 subagents. Early versions spawned 50 subagents for simple queries — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Premature "done" failure: in later sessions an agent "saw existing progress and declared the project done"; Claude "often marked features complete without verifying them end-to-end" — [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Fix: a JSON feature list (200+ features for a claude.ai clone, all starting as failing) with a `"passes"` field defines done outside the model; agents may only flip that field, and removing or editing tests is "unacceptable" — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- C compiler project (16 parallel agents): tests were the main control mechanism, because "agents solve whatever problem the verifier defines". A bash loop restarted `claude` in a fresh container as soon as a session ended, so the system as a whole never stopped by itself; it ran until humans stopped it (one agent accidentally ran `pkill -9 bash` and ended the loop) — [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) (5 Feb 2026)
- Claude Code auto-compaction has its own stop: if one huge output refills context right after each summary, "Claude Code stops auto-compacting after a few attempts and shows an error instead of looping" — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)

### Inferences
- "Done" works best as an external, checkable artifact (feature list `passes`, a test suite, a verifier score). The model's own judgement is a weak stopping signal over long horizons.
- Harness-level stops (max iterations, thrash detection, budget) are safety nets, not success criteria.

### Gaps
- I did not find a single Anthropic page that lists Claude Code's internal stop rules (turn caps, budget caps) beyond the compaction-thrash rule.

## 2. How is planning represented (todo lists, progress files, feature lists, git commits) and kept up to date?

### Takeaway
Anthropic stores plans outside the context window in plain files the model rereads: Claude Code's to-do list, NOTES.md / progress files, a JSON feature list, git history with descriptive commits, task-lock files for parallel agents, and memory-tool files. The research lead saves its plan to memory before its context fills. Plans stay current through a fixed session routine: read the state, do one item, verify it, commit, update the progress log.

### Cited Findings
- Structured note-taking: the agent writes notes to persistent memory outside the context window and reloads them later. Examples are "Claude Code's to-do list" and a custom agent "maintaining a NOTES.md file" — [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (29 Sep 2025)
- Pokémon example of a progress note: "for the last 1,234 steps I've been training my Pokémon in Route 1, Pikachu has gained 8 levels toward the target of 10" — [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Two-agent harness: an initializer agent (first session) sets up `init.sh`, `claude-progress.txt` and an initial git commit. A coding agent runs every later session. Both use the same system prompt, tools and harness and differ only in the first user prompt — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (26 Nov 2025, Opus 4.5 on the Claude Agent SDK)
- The feature list is JSON on purpose: the model "is less likely to inappropriately change or overwrite JSON than Markdown" — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Session startup routine: (1) `pwd`; (2) read git logs and progress files; (3) read the feature list and pick the highest-priority unfinished feature; (4) start the dev server via `init.sh` and run a basic end-to-end test before new work — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- One feature at a time was "critical" to stop the model doing too much at once. Agents commit with descriptive messages and write progress summaries so a bad change can be reverted — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Memory tool "multisession software development pattern" (official docs): initializer session writes a progress log, a feature checklist and a pointer to the startup script; each later session opens by reading them; an end-of-session update records what was done and what remains. "Mark a feature complete only after end-to-end verification confirms it works, not when the code is written." — [Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- The research lead "saves its plan to memory because context beyond 200,000 tokens gets truncated" — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Parallel planning without an orchestrator: task locks are text files in `current_tasks/`; if two agents claim one task, git sync forces the second to choose another. Agents pick the "next most obvious" problem themselves — [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler)
- Claude Code Plan mode: "Claude explores and proposes a plan without editing your source files"; the built-in Plan subagent is read-only and does research during plan mode — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works); [Subagents](https://code.claude.com/docs/en/sub-agents)
- Persistent instructions belong in CLAUDE.md because compaction can lose early instructions. Auto memory loads "the first 200 lines or 25KB of MEMORY.md, whichever comes first" at session start — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- In agent teams, teammates "additionally keep the task tools and cron tools" — [Subagents](https://code.claude.com/docs/en/sub-agents)
- Extended thinking is used "as a planning scratchpad" by the research lead — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)

### Inferences
- Across Anthropic's posts the pattern is a plan file plus one-item-at-a-time execution plus a git commit per verified item. Git doubles as plan history and rollback.
- Machine-readable plans (JSON) resist drift better than prose plans.

### Gaps
- I did not fetch the TodoWrite / task-tools reference pages, so I have no exact schema or status values for Claude Code's task list.

## 3. How do orchestrator/sub-agent designs work, when do they help vs hurt, and what do they cost in tokens?

### Takeaway
claude.ai Research uses orchestrator-worker: an Opus lead plans and spawns 3-5 Sonnet subagents in parallel, each with its own clean context, then synthesizes; a CitationAgent adds citations. It beat single-agent Opus by 90.2% on Anthropic's internal research eval, but uses about 15x chat tokens (single agents use about 4x). It suits breadth-first work and suits tightly coupled work such as most coding poorly. Claude Code subagents follow the same idea: their own context, a summary returned to the parent. Later work (the C compiler) used 16 peer agents coordinated only through git, with no orchestrator.

### Cited Findings
- Architecture: the LeadResearcher plans and spawns subagents that search in parallel; subagents run their own search loops and return findings; a separate CitationAgent attaches citations — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Gain: an Opus 4 lead with Sonnet 4 subagents "outperformed single-agent Opus 4 by 90.2%" on the internal research eval — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Cost: agents use about 4x the tokens of chat; multi-agent systems use about 15x. "Economically viable only when task value justifies the cost" — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Why it works: on BrowseComp, token usage alone explained 80% of performance variance (95% with tool calls and model choice). "Multi-agent systems work mainly because they help spend enough tokens to solve the problem." — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- When it hurts: tasks needing shared context or many dependencies between agents, "such as most coding tasks"; current agents coordinate poorly in real time — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Speed: the lead spins up 3-5 subagents at once and subagents use 3+ tools in parallel, which "cut research time by up to 90% for complex queries" — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Delegation quality: each subagent needs an objective, an output format, tool / source guidance and task boundaries; vague instructions caused duplicated work — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Limitation: synchronous execution. The lead waits for each batch, cannot steer subagents mid-task, and subagents cannot coordinate. Asynchronous execution was a planned improvement — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Subagents write outputs to external storage and pass lightweight references back, avoiding the "game of telephone" — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Subagents may use "tens of thousands of tokens or more" exploring but return "a condensed, distilled summary", often 1,000-2,000 tokens — [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Claude Code subagents: each "runs in its own context window with a custom system prompt, specific tool access, and independent permissions"; a non-fork subagent "doesn't see your conversation history". Built-ins: Explore (read-only), Plan (read-only), general-purpose (all tools). Model order: per-call → frontmatter → `CLAUDE_CODE_SUBAGENT_MODEL` → main model — [Subagents](https://code.claude.com/docs/en/sub-agents)
- Current Claude Code behaviour (Nov 2026): "a subagent that Claude spawns from your main conversation starts in the background" by default. Forks inherit the parent conversation. Nesting is allowed "up to three layers below the main conversation" (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`). Subagents can be resumed with `SendMessage` and keep full history; Explore and Plan are one-shot. Agent teams are a separate feature for coordinated sessions — [Subagents](https://code.claude.com/docs/en/sub-agents). Superseded: older guidance said subagents could not spawn subagents; the current page says the opposite.
- Peer-agent design, C compiler: 16 parallel Opus 4.6 agents, nearly 2,000 Claude Code sessions over two weeks, 2 billion input and 140 million output tokens, about $20,000. Output: a roughly 100,000-line Rust C compiler that builds Linux 6.9 on x86, ARM and RISC-V and passes about 99% of most compiler test suites. Coordination was a bare git repo plus lock files, "no orchestration agent". Specialized agents handled dedup, performance, code quality and docs — [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler)
- Parallelism failure: distinct failing tests parallelized well, but the Linux kernel was one big task, so "all agents got stuck on the same bug". The fix was GCC as a known-good oracle plus delta debugging to split the work — [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler)
- Open question as of Nov 2025: whether one general coding agent beats a multi-agent setup with testing / QA / cleanup agents — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

### Inferences
- Multi-agent mainly buys parallel token spend and clean contexts. Use it when subtasks are independent and the answer is worth roughly 15x the tokens.
- For coupled work, Anthropic's choices were a single agent with sequential sessions (harness post) or peers coordinated by git and tests (compiler), not a chatty orchestrator.

### Gaps
- No Anthropic token-cost numbers were found for Claude Code agent teams specifically.

## 4. How is context kept healthy over hours (compaction, context editing, memory files, just-in-time retrieval, note-taking)?

### Takeaway
Anthropic treats context as a finite "attention budget" that suffers "context rot". Its toolkit has five parts: (1) just-in-time retrieval (file paths, grep/glob instead of preloading); (2) compaction (summarize history and continue); (3) context editing (clear old tool results / thinking by rule); (4) persistent memory (memory tool, CLAUDE.md, progress files); (5) subagents with clean windows. The API now offers server-side compaction (on demand and at a threshold), context-editing strategies, a memory tool that warns the model before clearing, and tool search so tool definitions do not fill the window.

### Cited Findings
- Context rot: as the window grows, recall accuracy falls; this "appears across all models". "Context, therefore, must be treated as a finite resource with diminishing marginal returns." n tokens give n² pairwise attention relationships — [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Goal: "the smallest set of high-signal tokens that maximizes the desired outcome" — [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Just-in-time: keep "lightweight identifiers (file paths, stored queries, web links, etc.)" and load at runtime; Claude Code uses "glob and grep". Hybrid approach: CLAUDE.md up front, the rest on demand — [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Claude Code compaction (2025 description): the history is summarized, preserving "architectural decisions, unresolved bugs, and implementation details" and discarding redundant tool output; work continues with the summary plus "the five most recently accessed files". Tune for recall first, then precision — [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Claude Code compaction (current docs): auto-compacts near the limit; "detailed instructions from early in the conversation may be lost"; control it with a "Compact Instructions" section in CLAUDE.md or `/compact focus on ...`; `/context` shows usage; MCP tool definitions are "deferred by default and loaded on demand via tool search" — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- Tool-result clearing is "one of the safest lightest touch forms of compaction" — [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Context editing API (beta `context-management-2025-06-27`): `clear_tool_uses_20250919` (defaults: trigger 100,000 input tokens, keep 3 tool uses; options `clear_at_least`, `exclude_tools`, `clear_tool_inputs`) and `clear_thinking_20251015`. Edits apply server-side; the client keeps full history. Clearing tool results invalidates the prompt cache, so `clear_at_least` exists to make that worth it. The docs now recommend server-side compaction as the primary strategy — [Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing)
- Thinking-clearing defaults: Opus 4.5+, Sonnet 4.6+, Haiku 5.5+, Fable and Mythos keep all thinking turns; earlier models keep the last turn only. "On Claude 5.1 and later, server-side context management never invalidates thinking blocks." — [Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing)
- With the memory tool, "When context approaches the clearing threshold, Claude receives an automatic warning to save important information to memory files before it is cleared." — [Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing)
- SDK client-side compaction (`compaction_control`, default threshold 100,000 tokens, asks for a `<summary>`) is deprecated in favour of server-side compaction (`compact_20260112` edit). SUPERSEDED — [Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing)
- Current compaction API (Nov 2026): "Compaction on demand" (beta `compact-2026-09-04`, top-level `compaction` parameter; you decide when; can keep recent turns word for word; can run in the background) and "Compaction at a token threshold" (the API compacts inside the request that reaches your trigger). The docs say to use on-demand compaction wherever available, because "response quality degrades as a conversation grows" — [Compaction overview](https://platform.claude.com/docs/en/build-with-claude/compaction)
- Memory tool (`memory_20250818`, now stable on all models): client-side `/memories` directory with commands view / create / str_replace / insert / delete / rename. The API auto-injects: "ALWAYS VIEW YOUR MEMORY DIRECTORY BEFORE DOING ANYTHING ELSE ... ASSUME INTERRUPTION: Your context window might be reset at any moment". For long agents the docs advise using both compaction (keeps active context small) and memory (keeps what must survive summarization) — [Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- Tool Search Tool: 191,300 tokens of context preserved vs 122,800 with the traditional approach; tool overhead about 77K → about 8.7K tokens (85% less); MCP eval accuracy Opus 4 49% → 74%, Opus 4.5 79.5% → 88.1% (`defer_loading: true`) — [Advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use) (24 Nov 2025)
- Programmatic tool calling: Claude writes code that calls tools in a sandbox, so intermediate results stay out of context; average tokens 43,588 → 27,297 (37% less), GIA 46.5% → 51.2%, internal knowledge retrieval 25.6% → 28.5%; 20+ tool calls without a model pass for each (`allowed_callers: ["code_execution_20250825"]`). Tool use examples: complex-parameter accuracy 72% → 90% — [Advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use)
- Tool output budget: "For Claude Code, we restrict tool responses to 25,000 tokens by default"; a `response_format` concise/detailed enum cut a Slack response from 206 to 72 tokens — [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- Harness-side context hygiene (compiler): keep test output to a few lines, log details to files, tag errors `ERROR` on one line for grep, precompute summaries; a `--fast` mode runs a 1% / 10% deterministic sample to counter "time blindness" — [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler)
- Research system long-horizon: summarize completed phases, store key information in external memory, and spawn fresh subagents with clean context when limits approach — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Compaction alone did not fix the long-run coding failures, "since it doesn't always pass clear instructions to the next agent"; hence progress files and feature lists — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Opus 5 (24 Jul 2026) adds a beta for mid-conversation tool changes "without invalidating the prompt cache" — [Introducing Claude Opus 5](https://www.anthropic.com/news/claude-opus-5)

### Inferences
- The durable state of a long job should live in files (memory / progress / git). Compaction keeps the working window small, and the files make a reset survivable.
- Tool outputs are the main cause of context bloat. Capping, paginating, clearing and running tools in code all attack that cause.

### Gaps
- I did not fetch the threshold-compaction subpage, so default trigger values for `compact_20260112` are not confirmed here.
- No primary source gave the exact context-window sizes of the 5.x models.

## 5. How is work verified, and how are failures recovered from?

### Takeaway
Verification has three layers: environment ground truth (tests, builds, a browser driven like a human), external graders (code checks, LLM-judge rubrics, humans), and a structural rule that an item counts as done only after end-to-end checks pass. Recovery uses git commits and Claude Code checkpoints to roll back, resume-from-failure instead of restart, retries with errors fed back to the model, and fresh sessions that rebuild state from progress files.

### Cited Findings
- Browser testing: prompting Claude to test with browser automation (Puppeteer MCP) "as a human user" significantly improved results. Limitation: it cannot see browser-native alert modals — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Each session first runs a basic end-to-end test "to catch broken state before starting new work" — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Regressions: new features kept breaking old code until a CI pipeline and stricter enforcement were added. A known-good oracle (GCC) plus delta debugging isolated failures — [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler)
- Author's warning: passing tests can be mistaken for a finished job, and he worries about shipping code no one has personally verified — [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler)
- LLM judge for research output: rubric of factual accuracy, citation accuracy, completeness, source quality and tool efficiency; "A single LLM call outputting a 0.0-1.0 score and pass/fail grade was the most consistent and closest to human judgment." Start with about 20 queries. Grade outcomes, not paths. Human testers caught a preference for SEO content farms — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Evals vocabulary: task, trial, grader, transcript, outcome ("final state in the environment"). Grader types: code-based, model-based, human. pass@k vs pass^k (75% per trial over 3 trials → about 42% pass^3). Capability evals start low; regression evals stay near 100%. Start with "20-50 simple tasks drawn from real failures". Isolate trials (one eval let Claude see git history from earlier trials). Give LLM graders an "Unknown" option. "Read the transcripts!" 0% pass@100 "is most often a signal of a broken task" — [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (9 Jan 2026)
- Grader bugs matter: Opus 4.5 on CORE-Bench went 42% → 95% after fixing rigid grading and ambiguous or stochastic tasks; SWE-bench Verified went "from 40% to >80%" in one year — [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- Opus 5 is "much stronger at verifying its work and iterating carefully until it succeeds" (Anthropic claim) — [Introducing Claude Opus 5](https://www.anthropic.com/news/claude-opus-5)
- Production reliability: agents are stateful and errors compound, so the system "resumes from the point of failure instead of restarting", combining retry logic with checkpoints. Agents are told when a tool fails so they can adapt. Rainbow deployments avoid disrupting running agents. Full production tracing is used without reading conversation contents — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Claude Code checkpoints: Claude snapshots a file before editing it; `Esc` twice rewinds. Checkpoints are separate from git, survive resume, and cover only file changes ("databases, APIs, deployments" cannot be checkpointed). Sessions are saved as JSONL under `~/.claude/projects/`, enabling resume (`--continue` / `--resume`) and fork (`--fork-session`, `/branch`) — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- Checkpoints launched with Sonnet 4.5: they "save your progress and allow you to roll back instantly to a previous state" — [Introducing Claude Sonnet 4.5](https://www.anthropic.com/news/claude-sonnet-4-5) (29 Sep 2025)
- Git as recovery: descriptive commits plus progress summaries let a bad change be reverted — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Tool errors should be actionable messages, not opaque codes or tracebacks — [Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents)
- Self-improving tools: a tool-testing agent rewrote flawed MCP tool descriptions and cut future task time by 40% — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system). Claude-optimized tools beat "expert" ones on held-out sets — [Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents)

### Inferences
- The strongest Anthropic pattern pairs a verifier the model cannot edit (frozen tests, a JSON `passes` field, CI) with frequent commits, so recovery means reverting to the last green state.
- Remote side effects cannot be undone, so they are handled by permission gates (next section), not by rollback.

### Gaps
- I did not fetch the hooks docs, so there is no detail here on using hooks (e.g. Stop hooks) to force verification before finishing.

## 6. Where is the human kept in the loop (permissions, approvals, plan review)?

### Takeaway
Claude Code exposes permission modes (Auto with a background safety classifier, Manual, Accept edits, Plan), allow rules in settings, interrupt / steer at any moment, and plan review before edits. Anthropic's design advice is to pause at checkpoints or blockers. Irreversible remote actions are explicitly left to permissions, because checkpoints cannot undo them.

### Cited Findings
- Permission modes (Shift+Tab): **Auto** — "a classifier reviews most actions in the background and blocks the risky ones instead of asking you" (the default starting mode from Claude Code v2.1.283); **Manual** — asks before edits and shell commands; **Accept edits**; **Plan** — explores and proposes without editing source files. Trusted commands can be allowlisted in `.claude/settings.json`, scoped from org policy down to personal — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- Interrupt and steer: `Esc` stops at once; a typed correction is queued and read after the current tool calls, within the same turn — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- Foreground subagents pass permission prompts through to the user; background ones run concurrently — [Subagents](https://code.claude.com/docs/en/sub-agents)
- "Agents can then pause for human feedback at checkpoints or when encountering blockers" — [Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- Checkpoints do not cover remote systems; "You control those with your permission mode and permission rules" — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
- Human evaluation remains necessary: testers caught failures automated evals missed — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system); "Read the transcripts!" — [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- Opus 5 / Fable 5 safety routing: a beta "automatic API fallbacks" feature routes safety-flagged requests to another model instead of blocking them; flagged cyber requests fall back to Opus 4.8 by default — [Introducing Claude Opus 5](https://www.anthropic.com/news/claude-opus-5)

### Inferences
- The trend is from asking per action toward classifier-gated autonomy plus plan review up front, keeping hard approvals for irreversible or external actions.

### Gaps
- Not researched: Claude for Chrome / Cowork / computer-use approval flows (site permissions, action confirmations). No primary page for them was fetched.

## 7. Concrete numbers: token usage, run lengths, eval gains, reported failure modes

### Takeaway
Anthropic's published autonomy claims: about 7 hours (Opus 4, per press coverage of Anthropic's statement), then "more than 30 hours" of focus observed with Sonnet 4.5 (Sep 2025), then a two-week, 16-agent, roughly 2,000-session run with Opus 4.6 (Feb 2026). The 2026 flagship pages (Opus 5, Jul 2026) talk about long-horizon gains but give no hour figure. Token and cost figures: 4x / 15x chat tokens for agents / multi-agent; 2B in + 140M out tokens, about $20K for the compiler.

### Cited Findings
- Sonnet 4.5: "we've observed it maintaining focus for more than 30 hours on complex, multi-step tasks" (an observation, not a benchmark); SWE-bench Verified 77.2% (10-trial average; 82.0% with high compute); OSWorld 61.4% vs Sonnet 4's 42.2% four months earlier (OSWorld-Verified, 100 max steps, 4 runs). The Agent SDK is "the same infrastructure that powers Claude Code". Context editing and the memory tool launched to let "agents run even longer" — [Introducing Claude Sonnet 4.5](https://www.anthropic.com/news/claude-sonnet-4-5)
- Press: 30+ hours vs about 7 hours for Opus 4; one internal run reportedly built a chat app of about 11,000 lines over about 30 hours — [Axios](https://www.axios.com/2025/09/29/anthropic-claude-sonnet-coding-agent); [Bloomberg](https://www.bloomberg.com/news/articles/2025-09-29/anthropic-says-new-ai-model-can-code-on-its-own-for-30-hours-straight) (secondary; the 11,000-line detail was not seen in a primary source)
- Customer quotes in the Sonnet 4.5 post: Devin planning +18% and end-to-end eval +12% — [Introducing Claude Sonnet 4.5](https://www.anthropic.com/news/claude-sonnet-4-5)
- Compiler: 16 agents, about 2,000 sessions, 2 weeks, 2B input / 140M output tokens, about $20,000, about 100K lines of Rust — [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler)
- Research system: +90.2% vs single agent; 15x tokens; up to 90% less time from parallelism; 80% of BrowseComp variance explained by tokens — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- Opus 5 (24 Jul 2026, $5 / $25 per M tokens): "comes close to the frontier intelligence of Claude Fable 5 at half the price"; effort levels from lowest to high / xhigh / max; partner-reported 26% fewer tokens than Opus 4.8 at max, "a third fewer turns and tool calls, and 60% less time"; the biggest gains are on longer-horizon work; Anthropic notes "important limitations on long-running, autonomous research tasks" (biology); fast mode about 2.5x speed at 2x price — [Introducing Claude Opus 5](https://www.anthropic.com/news/claude-opus-5)
- Fable 5 (Jun 2026) and Fable 5.1 (Sep 2026): third-party coverage describes it as built for work running hours (claims of "days" appear only in weaker sources), 1M context, file-based memory. NOT VERIFIED against a primary Anthropic page (anthropic.com/news/claude-fable-5 returned 404) — [TripleDart](https://www.tripledart.com/marketing-digest/claude-fable-5); [MindStudio](https://www.mindstudio.ai/blog/how-to-use-claude-fable-5-long-running-agentic-tasks); [RuntimeWire on Mollick](https://www.runtimewire.com/article/anthropic-fable-5-ethan-mollick-agent-test)
- An "8 hours from a four-sentence prompt, about 70,000 lines" Opus 5 anecdote exists only in a Chinese blog — [woshipm](https://www.woshipm.com/share/6437572.html) (anecdote, unverified)
- METR measured Opus 4.5 at roughly a five-hour 50% time horizon (secondary coverage) — [Digit](https://www.digit.in/features/general/five-hours-of-expert-level-autonomy-metrs-claude-opus-45s-crazy-results.html/amp/)
- Reported failure modes, collected: one-shotting / running out of context mid-feature; declaring victory early; marking features done without end-to-end testing — [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents). Spawning 50 subagents for simple queries; duplicated work from vague delegation; favouring SEO farms; errors compounding — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system). All agents stuck on one bug; regressions; context pollution from verbose output; time blindness; an agent killing the loop with `pkill -9 bash` — [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler). Claude appending "2025" to search queries — [Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents). Exploiting loopholes or shared state in evals — [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents). Auto-compaction thrash on huge outputs — [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)

### Inferences
- Long run lengths come from the harness (restart loops, progress files, tests, git), not from one unbroken context. The 30-hour and two-week figures span many context windows or sessions.
- Anthropic's 2026 messaging moved from "hours of autonomy" to efficiency per task (tokens, turns, effort levels) and verification quality.

### Gaps
- No primary Anthropic source found for Fable 5 / 5.1 or Opus 4.6-4.8 autonomy-hour claims, or for the system-card numbers on long-horizon evals.
- Not covered: Cowork, Claude for Chrome and computer-use architecture beyond the OSWorld numbers and the Sonnet 4.5 Chrome mention; prompt-caching mechanics; interleaved-thinking docs (it is mentioned as used by research subagents after tool results — [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)).
