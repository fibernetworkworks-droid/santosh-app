# How non-Anthropic, non-OpenAI agent products finish long, multi-step tasks (state as of 2 Nov 2026)

Scope: Google (Gemini Deep Research, Gemini Agent / Project Mariner, Jules, Antigravity, ADK), Manus, Cognition Devin, Cursor, Replit Agent 3, Perplexity, open frameworks (LangGraph, OpenHands, smolagents, Temporal). Source status: "[fetched]" means the primary page was read in this session. "[search snippet]" means the claim came from a search-result summary of the cited page. "[not re-fetched]" means the URL comes from prior knowledge and was not re-read this session, so verify it before quoting.

## 1. How each product represents and updates the plan, and decides it is done

### Takeaway
The products converge on three patterns. (a) An explicit plan artifact the human can see or edit: Gemini Deep Research's multi-point plan, Antigravity's Implementation Plan, Cursor's plan-then-approve, Devin's Interactive Planning. (b) A plan that the agent keeps rewriting into its own context: Manus todo.md "recitation". (c) In multi-agent swarms, a separate role decides "continue or stop": Cursor's judge agent. Few vendors publish an explicit "done" criterion beyond plan items checked off, tests or self-tests passing, or a judge/reviewer saying stop.

### Cited Findings
**Google Gemini Deep Research**
- A planner turns the question into a "personalised multi-point research plan", which Gemini shows the user, who can refine it before research runs. [search snippet] — [Gemini Deep Research overview](https://gemini.google/gb/overview/deep-research/)
- The model "oversees the execution of this plan, and intelligently determines which sub-tasks can be tackled simultaneously and which need to be done sequentially." [search snippet] — [Gemini Deep Research overview](https://gemini.google/ao/overview/deep-research/?hl=en-GB)
- Google built "a novel asynchronous task manager that maintains a shared state between the planner and task models", so errors can be recovered "without restarting the whole task". It runs in the background: the user can leave and is notified when research finishes. [search snippet] — [Gemini Deep Research overview](https://gemini.google/gb/overview/deep-research/)
- The original Dec 2024 launch post describes the planner breaking the problem into smaller sub-tasks. Later versions run on Gemini 3. [search snippet; launch post not re-fetched] — [Google blog, Deep Research launch](https://blog.google/products/gemini/google-gemini-deep-research/)

**Google Antigravity (agent-first IDE, launched Nov 2025)**
- Agents produce "Artifacts": task lists, implementation plans, screenshots and browser recordings. These let the user verify the work without reading raw tool calls. [search snippet] — [Google Developers Blog: Build with Google Antigravity](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)
- In Planning mode the agent first writes an Implementation Plan artifact. The user comments on it before coding starts. The Agent Manager window shows each agent's status, its artifacts and pending approval requests. [search snippet] — [Getting Started with Google Antigravity codelab](https://codelabs.developers.google.com/getting-started-google-antigravity)
- A third-party tutorial says the user clicks "Approve Plan" before work proceeds. [secondary] — [agentpedia tutorial](https://agentpedia.codes/tutorial)

**Google Jules (async coding agent): SUPERSEDED / being shut down**
- Jules worked in a cloud VM, produced a plan, showed it for approval and then opened a PR. [secondary] — [InfoQ on Jules](https://www.infoq.com/news/2025/08/google-jules)
- Google announced the wind-down on 29 Oct 2026. Reported dates: no new tasks from 11 Nov 2026 (some reports say read-only from 12 Nov), fully wound down by 31 Dec 2026. Learnings go to Antigravity, and Jules-style background tasks are "coming to Antigravity" with no date. Jules settings, env vars, scheduled tasks and repo memory do not migrate automatically. [secondary only; I could not find Google's own post] — [Tecnoblog](https://tecnoblog.net/noticias/google-vai-encerrar-agente-de-ia-que-programa-sozinho/); [SmartScope](https://smartscope.blog/blog/google-jules-shutting-down-december-31-read-only-2026/); [PCGH](https://www.pcgameshardware.de/Kuenstliche-Intelligenz-Hardware-279517/News/google-jules-einstellung-november-2026-daten-export-antigravity-1558327/)
- Secondary reporting also says Google is sunsetting Gemini CLI in favour of a closed-source Antigravity CLI. [secondary, unverified] — [lavx news](https://news.lavx.hu/article/google-sunsets-gemini-cli-pushes-developers-into-the-closed-source-antigravity-cli)

**Manus**
- A complex task averages about 50 tool calls. Manus creates a todo.md, rewrites it and checks items off as it goes. This "recites its objectives" at the end of the context, which keeps the plan in the model's recent attention and counters "lost-in-the-middle" drift. [fetched] — [Manus: Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- Tool availability depends on task state through a state machine, enforced by logit masking rather than by changing the tool list. [fetched] — same source

**Cursor**
- Long-running agents (research preview, 12 Feb 2026) "propose a plan and wait for approval instead of immediately jumping into execution." They "use a plan and multiple different agents checking each other's work". [fetched] — [Cursor: Long-running agents](https://cursor.com/blog/long-running-agents)
- In the swarm research (14 Jan 2026, Wilson Lin), planners continuously explore the codebase, create tasks and can spawn sub-planners. Workers complete tasks without coordinating with each other. "At the end of each cycle, a judge agent decides whether to continue", and the next iteration starts fresh. [fetched] — [Cursor: Scaling long-running autonomous coding](https://cursor.com/blog/scaling-agents)

**Cognition Devin**
- Planning mode: Devin detects complex tasks and proposes a plan before executing. The user can auto-approve. [search snippet of localized official release notes] — [Devin release notes (zh)](https://docs.devin.ai/zh/release-notes/2024)
- "Interactive Planning": at session start Devin researches the codebase and returns relevant files, findings and a preliminary plan the user can edit before it acts autonomously. [secondary] — [fast.io Devin 2.0 guide](https://www.fast.io/resources/devin-2-0-guide.md)

**Perplexity Deep Research**
- It "iteratively searches, reads documents, and reasons about what to do next", refining its plan as it learns. Reported to finish in under 3 minutes (other coverage says 2-4 minutes). It runs dozens of searches over hundreds of sources and produces a cited report exportable to PDF or a Page. [secondary coverage of Feb 2025 launch] — [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2025/02/perplexity-deep-research/); [Maginative](https://www.maginative.com/article/perplexity-ai-unveils-free-deep-research-tool/)

**Open frameworks**
- smolagents has a `planning_interval` option: every N steps the agent writes or updates a plan of facts and next steps. [not re-fetched] — [smolagents docs](https://huggingface.co/docs/smolagents/index)

### Inferences
- "Done" is usually decided by one of four things: the plan being exhausted (Manus todo.md, Deep Research plan), an external check (Replit's test subagent, CI for Cursor and Devin), a judge or reviewer agent (Cursor), or the human approving a PR or diff (Jules, Devin, Antigravity). Nobody publishes a formal termination rule.
- Showing the plan before execution is now standard in Google's, Cursor's and Devin's products. It moves the human review to the cheapest point, before money and time are spent.

### Gaps
- I found no primary Google page for the Gemini Agent / Project Mariner plan format. Mariner (announced Dec 2024, ran up to 10 tasks in parallel in cloud VMs in its 2025 update; "teach and repeat") was not verified this session. Treat it as [not re-fetched]: [Project Mariner](https://deepmind.google/models/project-mariner/).
- I could not reach Google's own Jules shutdown post; the dates come from secondary sources only.
- Perplexity Comet's agent-confirmation behaviour: no source found.

## 2. Single-agent vs multi-agent: choices and published arguments

### Takeaway
The published positions split cleanly. Cognition argues for one agent with one continuous context: multi-agent systems are fragile because "actions carry implicit decisions". Manus (Wide Research) and Cursor (swarms) use many agents, but only where sub-tasks are independent: one item per sub-agent with a fresh context, or planners and workers with strict role separation. Replit uses a narrow sub-agent only for testing, to keep the main context clean.

### Cited Findings
- Cognition, "Don't Build Multi-Agents" (Walden Yan, 12 Jun 2025). Principle 1: "Share context, and share full agent traces, not just individual messages". Principle 2: "Actions carry implicit decisions, and conflicting decisions carry bad results." The conclusion: multi-agent collaboration "only results in fragile systems". [fetched] — [Cognition blog](https://cognition.com/blog/dont-build-multi-agents)
- The Flappy Bird example: one sub-agent built a Super Mario-style background, while the other's bird did not look or move like Flappy Bird. Copying the original task to sub-agents is not enough. Even with shared context, parallel sub-agents choose conflicting styles because they cannot see each other's work. [fetched] — same
- Same post: Claude Code (as of Jun 2025) "never does work in parallel with the subtask agent". Its sub-agents answer well-defined questions and do not write code, which keeps their exploration out of the main history. Also, 2024's "edit-apply" split (a big model plans, a small model rewrites the file) misfired; today one model does both. [fetched] — same
- Manus Wide Research (late Jul 2025): the main agent splits the job and runs 100+ sub-agents in parallel. Each is a full general-purpose Manus instance (not a role agent) with its own VM, tools and internet access and a fresh context per item. Results are gathered and synthesised. Examples: 100 sneakers analysed, 50 posters designed. No benchmarks published, and Manus calls it experimental. [search snippets of primary + coverage] — [Manus: Introducing Wide Research](https://manus.im/blog/introducing-wide-research); [Manus Wide Research feature page](https://manus.im/features/wide-research); [VentureBeat](https://venturebeat.com/ai/youve-heard-of-ai-deep-research-tools-now-manus-is-launching-wide-research-that-spins-up-100-agents-to-scour-the-web-for-you)
- Cursor swarm history. A flat structure with a shared coordination file and locks failed: agents held locks too long, and "Twenty agents would slow down to the effective throughput of two or three." Optimistic concurrency was more robust but made agents risk-averse: they avoided hard tasks and churned. What worked was separate roles (planners, workers, judge). "The harness and models matter, but the prompts matter more." [fetched] — [Cursor: Scaling agents](https://cursor.com/blog/scaling-agents)
- Cursor found GPT-5.2 better at extended autonomous work (focus, no drift), while Opus 4.5 "tended to stop earlier and take shortcuts". GPT-5.2 was a better planner than GPT-5.1-Codex, so Cursor now assigns models by role. [fetched] — same
- Secondary coverage: in Cursor's swarm, planners don't code and workers don't plan. Workers used ≥69% of tokens in every run and usually >90%. [secondary] — [The Decoder](https://the-decoder.com/cursors-agent-swarm-suggests-cheaper-models-can-handle-most-coding-when-frontier-models-plan-the-work/)
- Replit: the main agent's context often reaches 80k-100k tokens, so testing inline would pollute it. The main agent instead hands a high-level test plan to a testing sub-agent, which returns a summary of what works and what is broken. [fetched] — [Replit: Enabling Agent 3 to Self-Test at Scale](https://frontier.replit.com/automated-self-testing/)
- Gemini Deep Research runs parallelisable sub-tasks in parallel under one planner with shared state. [search snippet] — [Gemini Deep Research overview](https://gemini.google/ao/overview/deep-research/?hl=en-GB)

### Inferences
- The reconciled rule across vendors: parallelise reads and independent items (research, per-item analysis, testing), keep writes and decisions in one thread of context. Even Cursor's swarm avoids worker-to-worker coordination entirely.
- Every multi-agent design that works has the sub-agent return a summary, not its full trace, which is the trade-off Cognition warns about.

### Gaps
- No vendor published a head-to-head success-rate comparison of single-agent vs multi-agent on the same tasks.

## 3. Context and memory on long runs (files, summaries, restorable compression)

### Takeaway
Three tactics recur: (1) the file system or sandbox as external memory, with compression that can be undone (drop the content, keep the URL or path); (2) summarise or condense older history, using a dedicated summariser model (Cognition) or an LLM condenser (OpenHands, about 2x per-turn cost saving); (3) keep state in code or sandbox variables instead of in the prompt (Replit's REPL). Manus adds KV-cache discipline as the main cost and latency lever.

### Cited Findings
- Manus. "The KV-cache hit rate is the single most important metric for a production-stage AI agent." Cached Claude Sonnet input costs $0.30/MTok vs $3/MTok uncached (10x). The input:output token ratio averages about 100:1. Rules: a stable prompt prefix (no timestamp at the top), append-only context, deterministic JSON key order, explicit cache breakpoints, and vLLM prefix caching with session-ID routing for self-hosted models. [fetched] — [Manus blog](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- Manus. Don't add or remove tools mid-task: it invalidates the cache, and old turns would reference missing tools. Instead mask token logits through a state machine, using shared name prefixes (`browser_`, `shell_`) to select groups. Response prefill gives three modes: auto, required and specified. [fetched] — same
- Manus. The file system is the "ultimate context": "unlimited in size, persistent by nature, and directly operable by the agent itself". Compression must be restorable: drop a web page's content but keep its URL, drop a document but keep its sandbox path. [fetched] — same
- Manus. Vary few-shot patterns, because repeated action-observation pairs cause drift. In a 20-resume review the agent fell into a rhythm and hallucinated. The fix is controlled variation in templates and phrasing ("don't few-shot yourself into a rut"). [fetched] — same
- Cognition recommends a dedicated model that compresses history into "key details, events, and decisions". It is hard to get right; Cognition fine-tuned a smaller model for it. Even so, a limit is eventually hit. [fetched] — [Cognition blog](https://cognition.com/blog/dont-build-multi-agents)
- OpenHands. The default `LLMSummarizingCondenser` summarises history once it exceeds a size limit. This gives up to 2x lower per-turn API cost with comparable SWE-bench Verified (subset) results, and the cost curve flattens once condensation starts. [search snippet] — [OpenHands blog: context condensation](https://openhands.dev/blog/openhands-context-condensensation-for-more-efficient-ai-agents); [OpenHands SDK docs: context condenser](https://docs.openhands.dev/sdk/guides/context-condenser)
- Counterpoint, "The Complexity Trap" (arXiv 2508.21433). Simple observation masking halves cost vs the raw agent while matching, and sometimes slightly beating, LLM summarisation's solve rate (tested mainly in SWE-agent, only briefly in OpenHands). [search snippet] — [arXiv 2508.21433](https://arxiv.org/abs/2508.21433v3)
- Replit. Notebook-style persistence keeps variables and browser sessions alive across executions, so "state lives in code rather than in the model's context". A 36-month date pick is one generated loop, not 36 model actions. [fetched] — [Replit self-testing](https://frontier.replit.com/automated-self-testing/)
- Cursor. Periodic fresh starts are needed to counter drift and tunnel vision: each judge cycle restarts fresh. [fetched] — [Cursor: Scaling agents](https://cursor.com/blog/scaling-agents)
- LangGraph separates checkpointers (thread-scoped short-term state snapshots) from stores (cross-thread key-value long-term memory). It recommends pruning or a retention policy because checkpoints accumulate. [fetched] — [LangGraph docs: durable execution / persistence](https://docs.langchain.com/oss/python/langgraph/durable-execution)
- Jules kept per-repo "repo memory" (it did not migrate on shutdown). [secondary] — [SmartScope](https://smartscope.blog/blog/google-jules-shutting-down-december-31-read-only-2026/)

### Inferences
- The cheapest wins come first: observation masking or restorable dropping of bulky tool output, then a todo-style recitation file. LLM summarisation helps cost, but the evidence that it beats masking on success rate is weak.
- Prompt-cache stability matters most when tool lists or system prompts change between turns. Masking or prefill keeps the tool list stable.

### Gaps
- Google has published no details of Deep Research's context management (how many sources are kept in context vs summarised).

## 4. Verification, self-testing, error recovery and durable execution / checkpoint-resume

### Takeaway
Verification is moving from "the model says it's done" to executed checks: Replit's browser-testing sub-agent (median $0.20 per session) and Antigravity's screenshot and browser-recording artifacts. Error recovery means keeping failures visible (Manus) and resuming from shared state instead of restarting (Gemini Deep Research). Crash safety comes from durable execution: LangGraph checkpointers with `sync`/`async`/`exit` durability, and Temporal wrapping each LLM or tool call as a replayable activity.

### Cited Findings
- Replit's "Potemkin interfaces": buttons that render with no event handlers, mocked data, dead links. They "pass as working on first glance", and errors compound as the agent builds on them. [fetched] — [Replit self-testing (15 Dec 2025)](https://frontier.replit.com/automated-self-testing/)
- Replit's rejected options. Playwright, Puppeteer or Cypress tests written blind are inaccurate. Browser-use tool wrappers eat context and limit the action space. Computer-use agents cost roughly $0.50 and take 30-90 s to fill a 5-field form (back-of-napkin estimate with Claude Sonnet 4). [fetched] — same
- Replit's chosen approach: the agent writes Playwright code that runs in a persistent REPL sandbox. It sees a stripped DOM (ARIA and test attributes), read-only DB queries, and client and server logs since the last run. Autonomy rose from about 20 min to 200+ min ("10x"). Multi-hundred-step testing runs at a median $0.20 per session. No accuracy or false-positive numbers are published. [fetched] — same
- Replit Agent 3 (10 Sep 2025) works autonomously for up to 200 minutes with live monitoring and self-tests in a real browser in a reflection loop. [search snippet of official changelog] — [Replit changelog 2025-09-12](https://docs.replit.com/updates/2025/09/12/changelog)
- Manus keeps failed actions and stack traces in context instead of cleaning them up or silently retrying. Seeing the failure shifts the model away from repeating it; "error recovery is one of the clearest indicators of true agentic behavior". [fetched] — [Manus blog](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- Gemini Deep Research's async task manager shares state between planner and task models, so a single failure does not restart the task. [search snippet] — [Gemini Deep Research overview](https://gemini.google/gb/overview/deep-research/)
- Antigravity's verification artifacts (screenshots, browser recordings, test results) let the human check outcomes instead of reading tool calls. [search snippet] — [Google Developers Blog](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)
- Cursor names the long-horizon failure modes: models "forget the overall goal, lose track of their work, or stop at partial completion", and "a small early wrong assumption" can wreck the final result. Its countermeasures are plan approval upfront plus agents cross-checking each other against the plan. [fetched] — [Cursor: Long-running agents](https://cursor.com/blog/long-running-agents)
- LangGraph durability modes [fetched] — [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers.md):
  - `exit`: persists only when the graph exits. Fastest, but a mid-run process crash cannot be recovered.
  - `async`: persists while the next step runs. Small risk of a lost checkpoint on crash.
  - `sync`: persists before the next step starts. The most durable. In `sync` mode the input checkpoint is committed before the first node runs.
  - Pending writes from nodes that completed in a failed super-step are stored, so successful siblings do not re-run. The graph restarts "from the last successful step", but only at super-step boundaries.
  - Replay or fork from any checkpoint: earlier nodes are skipped, and later nodes (LLM calls, API requests) re-execute. So side-effecting nodes must be safe to repeat. That is my inference; the docs page does not state an idempotency rule.
- Temporal + agent SDKs. The agent run is wrapped in a durable Workflow, and each LLM call or tool execution becomes an Activity. After a crash, a network timeout or a multi-day wait for human approval, the workflow resumes where it left off instead of restarting and re-paying tokens. [search snippets] — [Temporal docs: Durable AI](https://docs.temporal.io/ai.md); [temporalio-openai-agents on PyPI](https://pypi.org/project/temporalio-openai-agents/); [InfoQ](https://www.infoq.com/news/2025/09/temporal-aiagent)
- Maturity of the Temporal integration: launched as public preview (Sep 2025). One secondary guide claims GA on 23 Mar 2026; unverified. — [DEV guide](https://dev.to/jangwook_kim_e31e7291ad98/temporal-for-ai-agents-durable-execution-guide-2026-9hf)
- Devin's sessions can sleep and resume. In Slack, saying "sleep" puts Devin to sleep until someone @mentions it in the thread; "archive" sleeps and archives the session. Release notes also mention fixes for sessions stuck or failing to sleep or wake. [search snippets of localized official docs] — [Devin docs (de)](https://docs.devin.ai/de/release-notes/2024); [Devin release notes (zh)](https://docs.devin.ai/zh/release-notes/2024)

### Inferences
- The two-layer pattern: an executed check inside the loop (tests or browser) plus a durable step log outside it (checkpoints or activities). Most products publish the first. Only frameworks (LangGraph, Temporal) document the second in detail.
- Replay safety requires idempotent side effects (send, pay, post). Neither the LangGraph nor the Temporal snippets I read spell out the key pattern, so it must be designed in.

### Gaps
- No vendor published the false-pass rate of its self-verification.
- I could not open Google ADK docs this session. From prior knowledge ([not re-fetched]): ADK has Session/State/Memory services, long-running function tools and tool-confirmation (human-in-the-loop) hooks. — [ADK docs](https://google.github.io/adk-docs/)

## 5. Human-in-the-loop patterns

### Takeaway
The common spine: approve or edit the plan first; the agent then runs asynchronously with a live view; a human gate covers risky or credential steps; review happens at the PR or artifact. Antigravity makes the gate a policy setting. LangGraph and Temporal make "pause for a human for days" a first-class, crash-safe state.

### Cited Findings
- Gemini Deep Research: the user refines the plan before research runs, then leaves and is notified on completion. [search snippet] — [Gemini Deep Research overview](https://gemini.google/gb/overview/deep-research/)
- Antigravity's review policy has three settings: "Always Proceed", "Agent Decides" and "Request Review". Users comment on artifacts, including the plan, while the agent keeps working. The Agent Manager lists pending approval requests. [search snippet] — [Antigravity codelab](https://codelabs.developers.google.com/getting-started-google-antigravity); [Google Developers Blog](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/)
- Cursor: plan approval first. In Cursor's testing this produced larger, more complete PRs with fewer follow-ups. Remaining follow-ups on the proxy task were mostly changes the team hadn't specified. [fetched] — [Cursor: Long-running agents](https://cursor.com/blog/long-running-agents)
- Cursor: a local chat can be pushed to a cloud agent by prefixing the message with `&`. [search snippet of changelog] — [Cursor changelog](https://prod.cursor.com/changelog/page/6)
- Devin: plan proposal with an optional auto-approve [search snippet, official]; an Interactive Browser for human-gated steps such as CAPTCHA and MFA [secondary]. — [Devin release notes (zh)](https://docs.devin.ai/zh/release-notes/2024); [fast.io session guide](https://fast.io/resources/devin-session-tools-guide/)
- Jules showed a diff for approval before opening a PR [secondary]. An unreliable claim of a 5-minute auto-approve timeout is excluded. — [InfoQ](https://www.infoq.com/news/2025/08/google-jules)
- LangGraph: checkpointers let humans "inspect, interrupt, and approve graph steps". The graph resumes after the human edits state, keyed by `thread_id`. Interrupts always re-trigger on replay. [fetched] — [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers.md)
- Temporal: workflows survive a "multi-day wait for a human to approve a step". [search snippet] — [Temporal docs: Durable AI](https://docs.temporal.io/ai.md)
- Replit's Live Monitoring lets the user watch a 200-minute autonomous run. [search snippet] — [Replit changelog](https://docs.replit.com/updates/2025/09/12/changelog)

### Inferences
- The "Agent Decides" style of policy (the agent judges when review is needed) sits between full autonomy and gating every step. Products pair it with hard gates for credentials and irreversible actions.

### Gaps
- Gemini Agent / Mariner and Comet confirmation rules for purchases and sends were not verified this session.

## 6. Reported run lengths, success rates, costs and failure modes

### Takeaway
Published numbers are mostly run lengths and costs, almost never success rates. Run lengths: Perplexity Deep Research about 2-4 min; Replit 200+ min; Cursor long-running agents 25-52 h; Cursor swarms about a week to 3+ weeks.

### Cited Findings
| Product | Length / scale | Cost / quality numbers | Source |
|---|---|---|---|
| Manus | ~50 tool calls per complex task; 100:1 input:output | cached $0.30 vs $3/MTok | [Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) |
| Manus Wide Research | 100+ parallel sub-agents | no benchmarks | [VentureBeat](https://venturebeat.com/ai/youve-heard-of-ai-deep-research-tools-now-manus-is-launching-wide-research-that-spins-up-100-agents-to-scour-the-web-for-you) |
| Replit Agent 3 | ~20 min -> 200+ min autonomy | testing median $0.20/session; computer use ~$0.50 + 30-90 s per 5-field form | [Replit](https://frontier.replit.com/automated-self-testing/) |
| Cursor long-running (Feb 2026) | 25 h, 30 h, 36 h examples; "commonly more than a day"; a 52-hour Rspack task | "substantially larger PRs with merge rates comparable"; 10k-line PR; 151k-LoC Rspack PR | [Cursor](https://cursor.com/blog/long-running-agents) |
| Cursor swarms (Jan 2026) | browser ~1 week, 1M+ LoC / 1,000 files; Solid->React 3+ weeks (+266K/-193K); hundreds of concurrent agents; "trillions of tokens" | 25x video-render speedup merged; Java LSP 550K, Win7 emulator 1.2M, Excel 1.6M LoC (ongoing) | [Cursor](https://cursor.com/blog/scaling-agents) |
| OpenHands condenser | — | up to 2x lower per-turn cost, comparable SWE-bench Verified subset | [OpenHands](https://openhands.dev/blog/openhands-context-condensensation-for-more-efficient-ai-agents) |
| Perplexity Deep Research | <3 min (2-4 min) | dozens of searches, hundreds of sources | [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2025/02/perplexity-deep-research/) |

Failure modes named by the vendors:
- Goal forgetting, losing track of work, stopping at partial completion, and an early wrong assumption compounding. — [Cursor](https://cursor.com/blog/long-running-agents)
- Drift and tunnel vision, needing fresh starts; risk-averse agents under optimistic concurrency; lock contention; Opus 4.5 stopping early or taking shortcuts (Cursor's finding). — [Cursor](https://cursor.com/blog/scaling-agents)
- Potemkin features that look done but are not. — [Replit](https://frontier.replit.com/automated-self-testing/)
- Few-shot rut / hallucination on repetitive batches; lost-in-the-middle on ~50-call tasks; cache invalidation from changing tools. — [Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- Sub-agent miscommunication and conflicting implicit decisions. — [Cognition](https://cognition.com/blog/dont-build-multi-agents)
- Devin sessions stuck or failing to sleep or wake (fixed in release notes). — [Devin release notes (zh)](https://docs.devin.ai/zh/release-notes/2024)
- AutoGPT-era lessons (open-ended loops, no grounding, cost blow-ups) are widely discussed, but I did not fetch a primary source this session. Gap.

### Inferences
- The longest reported runs (Cursor, days to weeks) all share three things: (1) the plan is fixed or approved upfront, (2) there is an external check (CI, tests, a judge), (3) contexts restart periodically instead of growing forever.

### Gaps
- No vendor in scope publishes task success rates for long autonomous runs. The Cursor merge-rate chart's numbers appear only in an image.
- Gemini Deep Research run times and costs, and Gemini Agent / Mariner success rates, were not found in primary sources this session.
