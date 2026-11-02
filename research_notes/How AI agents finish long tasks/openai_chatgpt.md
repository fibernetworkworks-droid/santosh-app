# How OpenAI's ChatGPT products and APIs finish long, multi-step tasks (as of Nov 2026)

Source-quality note for the writer: openai.com and help.openai.com returned HTTP 403 to the fetch tool, so launch posts and system cards could not be re-read in this session. Claims tagged **[V]** were read in this session from a primary page (developers.openai.com docs or cookbook, the Agents SDK docs, learn.chatgpt.com). Claims tagged **[T]** come from the researcher's training knowledge (cutoff mid-2026). They cite the canonical OpenAI URL, but that URL was not re-fetched and the claim should be spot-checked. Claims tagged **[S]** come from secondary news coverage only.

**Product landscape in 2026, with superseded items marked**
- Operator (Jan 2025) and Deep Research (Feb 2025) were merged into **ChatGPT agent** ("agent mode") in July 2025 [T] — [OpenAI: Introducing ChatGPT agent](https://openai.com/index/introducing-chatgpt-agent/).
- **SUPERSEDED: ChatGPT agent.** A help-center search snippet says ChatGPT agent "is no longer available" and points users to **ChatGPT Work** for longer multi-step tasks [S, via search snippet] — [help.openai.com 11752874](https://help.openai.com/en/articles/11752874-chatgpt-agent). A Wikipedia snippet says it was removed in early August 2026 with no advance notice. I could not corroborate that. — [Wikipedia: OpenAI Operator](https://en.wikipedia.org/wiki/OpenAI_Operator)
- **ChatGPT Work** launched around 9-10 July 2026 on GPT-5.6. It shipped alongside Sites (public beta) and Scheduled Tasks, and brought "Chat, Work, and Codex" into one ChatGPT experience: Work handles multi-step projects, and Codex stays focused on repositories [S] — [EdTech Innovation Hub](https://www.edtechinnovationhub.com/news/openai-launches-chatgpt-work-for-multi-step-projects-across-apps-and-files); [Windows Report](https://windowsreport.com/openai-launches-chatgpt-work-for-apps-files-and-business-tasks/); [Newsbytes PH, 10 Jul 2026](https://newsbytes.ph/2026/07/10/openai-unveils-chatgpt-work-for-multi-step-tasks-across-apps-files/)
- The current docs hub at learn.chatgpt.com (developers.openai.com/codex now redirects there with a 308) lists the following surfaces:
  - Codex in the ChatGPT desktop app, mobile, web, CLI, IDE extension and Codex Cloud.
  - Other surfaces: ChatGPT Work, "dots" (a messaging assistant), ChatGPT Space and Sites.
  - A model called "GPT-6.1 Terra" for visual reasoning and computer use.
  - Doc sections titled "long-running work", "automations", "notifications", "subagents", "auto-review", "permission modes" and "cloud environments".

  [V] — [learn.chatgpt.com/docs](https://learn.chatgpt.com/docs). The guessed subpage URLs returned 404, so the contents of those sections were not read.

## 1. What is the agent loop, how is planning surfaced, and when does it stop?

### Takeaway
Every OpenAI agent surface runs the same loop: the model calls tools until it produces a final answer. OpenAI drives persistence mostly through prompting ("keep going until the query is completely resolved"). Planning is made visible through tool preambles and an explicit plan tool (`update_plan` in Codex). Stopping is governed by stated stop conditions, plus lower uncertainty thresholds for risky tools.

### Cited Findings
- **Agents SDK loop.** Agents are "LLMs equipped with instructions and tools" running in a built-in loop "that continues until the task is complete". The other primitives are handoffs and agents-as-tools for delegation, guardrails (input and output validation that runs in parallel with the agent and fails fast), sessions (persistent memory), tracing, and human-in-the-loop with interruptions and resumable state [V] — [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/)
- **Persistence prompt, GPT-5 prompting guide.** The guide's persistence prompt reads: "please keep going until the user's query is completely resolved, before ending your turn and yielding back to the user"; "Never stop or hand back to the user when you encounter uncertainty"; "Do not ask the human to confirm or clarify assumptions, as you can always adjust later" [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- **Eagerness is tunable.** For less eagerness, lower `reasoning_effort` and use fixed budgets, e.g. "an absolute maximum of 2 tool calls", or stop early when "top hits converge (~70%)". For more eagerness, raise `reasoning_effort` and add the persistence prompt [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- **Tool preambles.** "GPT-5 is trained to provide clear upfront plans and consistent progress updates via 'tool preamble' messages"; "the longer the rollout, the bigger the difference these updates make" [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- **Stop conditions.** The guide says to "clearly state the stop conditions of the agentic tasks" and to "define when, if ever, it's acceptable for the model to hand back to the user". Checkout and payment tools "should explicitly have a lower uncertainty threshold for requiring user clarification" [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- **Splitting work across turns.** "we observe peak performance when distinct, separable tasks are broken up across multiple agent turns" [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- **Reasoning effort.** The default is `medium`; "For complex, multi-step tasks, we recommend higher reasoning". Verbosity controls the length of the final answer only, not of the thinking [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- **Cursor's production tuning, as reported in the guide.**
  - Verbosity set to low globally, but "high verbosity for writing code".
  - "you should almost never ask the user whether to proceed with a plan".
  - "Bias towards not asking the user for help if you can find the answer yourself".
  - The old "maximize_" thoroughness prompts turned out to be "counterproductive with GPT-5".

  [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- **Codex CLI system prompt** [T] — [openai/codex repo](https://github.com/openai/codex):
  - It tells the agent to keep going until the query is completely resolved.
  - It defines an `update_plan` tool: a list of steps, each `pending`, `in_progress` or `completed`, with only one `in_progress` at a time. The plan is for non-trivial, multi-step work, not single-step tasks.
  - It asks for short preambles before tool calls.
  - The raw path I tried (`codex-rs/core/prompt.md`) returned 404, so the file has moved.
- **ChatGPT Work flow.** The user states the outcome, audience, constraints and sources. Work then proposes a plan, flags missing context, executes "a sequence of approved steps", and returns outputs with open questions or decisions for a person. Users can follow progress, answer questions and redirect the work mid-run [S] — [EdTech Innovation Hub](https://www.edtechinnovationhub.com/news/openai-launches-chatgpt-work-for-multi-step-projects-across-apps-and-files)
- **ChatGPT agent (2025).** It ran on its own virtual computer with a visual browser, a text browser, a terminal and connectors. It narrated its steps on screen, and the user could interrupt and redirect it at any point [T] — [Introducing ChatGPT agent](https://openai.com/index/introducing-chatgpt-agent/)
- **"A practical guide to building agents" (2025).** It frames an agent as model + tools + instructions in a run loop that exits on a final-output tool, a response with no tool calls, an error, or a max-turns limit. It recommends a single agent before multiple agents (manager pattern, or decentralised handoffs), and layered guardrails plus human intervention on failure thresholds and high-risk actions [T] — [A practical guide to building agents (PDF)](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)

### Inferences
- OpenAI's stance is "autonomy by default, ask only at risky edges". The prompting guidance actively discourages clarifying questions for ordinary uncertainty. ChatGPT Work appears to move the confirmation point to plan approval at the start, rather than asking mid-run.

### Gaps
- The exact current Codex prompt and the current planning-tool name and schema (2026) could not be re-read because the repo path had moved.
- The internal loop of ChatGPT Work (tool set, max steps) was not found in any primary source.

## 2. How does it keep context under control on very long runs?

### Takeaway
OpenAI has three layers: (1) reasoning items carried across turns, via `previous_response_id` or encrypted reasoning content; (2) **compaction**, which is both a trained model behaviour (Codex-Max onward) and an API feature that emits an opaque encrypted compaction item; (3) server-side conversation state.

### Cited Findings
- **Standalone compaction endpoint `/responses/compact`.** It is "fully stateless and ZDR-friendly": you send a full context window and get back a compacted window to use as-is in the next call. Do not prune its output. The input must still fit in the model's context window [V] — [Compaction guide](https://developers.openai.com/api/docs/guides/compaction)
- **Server-side compaction.**
  - Configured with `context_management=[{type: "compaction", compact_threshold: N}]` on `/responses`.
  - Once the rendered token count crosses the threshold, the server compacts, emits the compaction item in the same stream, and prunes context before continuing inference.
  - ZDR-friendly with `store=false`.

  [V] — [Compaction guide](https://developers.openai.com/api/docs/guides/compaction)
- **The compaction item.** It "carries forward prior state and reasoning in fewer tokens" and is "opaque and not intended to be human-interpretable". With stateless chaining you may drop the items before the latest compaction item. With `previous_response_id` you should not prune manually [V] — [Compaction guide](https://developers.openai.com/api/docs/guides/compaction)
- **Reasoning carry-over.** Passing `previous_response_id` sends earlier reasoning items into later requests, which "allows the model to refer to its previous reasoning traces, conserving CoT tokens". Switching to the Responses API raised Tau-Bench Retail "from 73.9% to 78.2%" [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- **Encrypted reasoning for stateless and ZDR use.** Request `include=["reasoning.encrypted_content"]` with `store=false` and pass the items back in the next request [T] — [Reasoning guide](https://platform.openai.com/docs/guides/reasoning)
- **GPT-5.1-Codex-Max (19 Nov 2025)** was "trained to work across multiple context windows through a technique called compaction". It prunes while preserving critical state, so a session "can span millions of tokens". In internal testing OpenAI observed it working on tasks for more than 24 hours [S, quoting OpenAI] — [Neowin](https://www.neowin.net/news/openai-announces-gpt51-codex-max-a-new-coding-model-built-for-long-running-tasks/); [gend.co](https://www.gend.co/blog/gpt-5-1-codex-max-compaction). OpenAI's original post is at [openai.com/index/gpt-5-1-codex-max](https://openai.com/index/gpt-5-1-codex-max/) [T]. **Superseded as a model**: one guide lists it as "Superseded" [S] — [Verdent](https://www.verdent.ai/guides/model/gpt-5-1-codex)
- **Codex CLI.** It auto-compacts when the context nears its limit and has a manual `/compact` command [T] — [openai/codex](https://github.com/openai/codex)
- **Long-conversation drift.** The GPT-5 guide suggests re-appending formatting instructions "every 3-5 user messages" [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)

### Inferences
- The API now has the same primitive that Codex uses internally: a trained model compacts into an encrypted item, and the server trims history once a threshold is crossed. Developers no longer need to write their own summarisers for long runs on supported models.

### Gaps
- No primary statement was found on which 2026 models (GPT-5.6, 6.x) support native compaction, or what default threshold the server uses.
- No published compaction-quality evals were found.

## 3. How does it verify its own work and ask the user for confirmation?

### Takeaway
Codex verifies by running tests, linters and builds in its sandbox and citing terminal logs. A code-review model and "auto-review" exist as a further check. ChatGPT agent and Work rely on user controls: plan approval, confirmations before consequential actions, takeover of the browser for logins and sensitive input, and "watch mode" on sensitive sites.

### Cited Findings
- **ChatGPT agent safeguards.** These were confirmations for high-impact actions, refusal of disallowed tasks, prompt-injection monitoring, and a "watch mode" that requires the user to supervise on certain sites. On a login it pauses and asks the user to take over the virtual browser. Users are told to type sensitive input in takeover mode, never in the chat. OpenAI says these measures "don't eliminate all risks" [S, help-center snippets via search] — [help.openai.com 11752874](https://help.openai.com/en/articles/11752874-chatgpt-agent)
- **Prompt-injection example.** OpenAI's example was a malicious page comment that tries to make the agent fetch a Gmail password-reset code and send it elsewhere [S, help-center snippet] — [help.openai.com](https://help.openai.com/en/articles/11752874-agent)
- **ChatGPT Work controls.** Users review results "before they're used or shared". Enterprise and Edu admins control access, usable context, connectable tools and allowed actions. For Edu, admins can also control browser use, cloud network access, "sensitive actions" and approved local files and apps [S] — [EdTech Innovation Hub](https://www.edtechinnovationhub.com/news/openai-launches-chatgpt-work-for-multi-step-projects-across-apps-and-files)
- **Codex cloud.** Each task runs in an isolated container preloaded with the repo. The agent runs tests, linters and type checks, and gives verifiable evidence (citations to terminal logs and test output) before proposing a diff or PR. Internet access is off by default during the agent phase [T] — [Introducing Codex (May 2025)](https://openai.com/index/introducing-codex/)
- **GPT-5-Codex (Sep 2025).** It added a code-review mode that navigates the codebase and runs code and tests to validate findings [T] — [Introducing upgrades to Codex](https://openai.com/index/introducing-upgrades-to-codex/) (403 in this session)
- **Codex CLI sandbox and approvals.** Approval modes went from read-only / suggest, through auto-edit, to full-auto / "workspace-write" with network off. The OS sandbox is Seatbelt on macOS and Landlock/seccomp on Linux, and escalation needs approval [T] — [openai/codex](https://github.com/openai/codex). The 2026 docs list "permission modes", "sandboxing", "auto-review" and "agent approvals & security" [V, titles only] — [learn.chatgpt.com/docs](https://learn.chatgpt.com/docs)
- **Agents SDK guardrails.** They run in parallel with the agent and fail fast. Human-in-the-loop interruptions produce resumable state [V] — [Agents SDK](https://openai.github.io/openai-agents-python/)

### Inferences
- Coding agents can verify against ground truth (tests). The general-purpose agent mostly cannot, so OpenAI leans on human checkpoints (plan approval, confirmations, watch mode) instead.

### Gaps
- The ChatGPT agent system card's quantitative results (prompt-injection resistance rates, confirmation recall) could not be fetched (403).
- How Codex "auto-review" works was not retrieved.

## 4. How does it resume after interruption or failure, and how do background execution and notifications work?

### Takeaway
At the API level, **background mode** decouples long runs from the HTTP connection: you poll, cancel, or resume a stream from a cursor. At the product level, ChatGPT agent, Work and Codex cloud run tasks asynchronously, notify on completion, and support scheduled and recurring tasks (Tasks in 2025, Scheduled Tasks and Codex automations in 2026). Pulse is a separate proactive daily brief.

### Cited Findings
- **Background mode.** Set `background: true`. The call returns at once with a `status`. Keep polling "while the request is in the queued or in_progress state"; the examples treat `completed`, `failed` and `incomplete` as terminal [V] — [Background mode guide](https://developers.openai.com/api/docs/guides/background)
- **Cancel.** `POST /v1/responses/{id}/cancel`, which is idempotent [V] — [Background mode guide](https://developers.openai.com/api/docs/guides/background)
- **Resuming a dropped stream.** Start with `background` and `stream` both true and track `sequence_number`. If the connection drops, the response keeps running; resume with GET `stream=true&starting_after=<cursor>`. Keepalive events must not be used as cursors. Time to first token is currently higher than for synchronous calls [V] — [Background mode guide](https://developers.openai.com/api/docs/guides/background)
- **Retention.** Data is stored on disk "for roughly 10 minutes" to support polling. ZDR projects run with `store=false` but still get this temporary storage. The SDK's default 10-minute timeout may need raising [V] — [Background mode guide](https://developers.openai.com/api/docs/guides/background)
- **Webhooks.** The background guide does not mention them [V]. OpenAI does offer webhooks such as `response.completed` [T] — [Webhooks guide](https://platform.openai.com/docs/guides/webhooks)
- **Agents SDK.** Results carry interruptions and resume state, and the docs mention resumable sandbox sessions [V] — [Agents SDK](https://openai.github.io/openai-agents-python/)
- **Scheduled Tasks (2026).** They launched with ChatGPT Work for recurring work, e.g. weekly agenda updates [S] — [EdTech Innovation Hub](https://www.edtechinnovationhub.com/news/openai-launches-chatgpt-work-for-multi-step-projects-across-apps-and-files). The Codex docs have "automations", "scheduled tasks" and "notifications" sections [V, titles only] — [learn.chatgpt.com/docs](https://learn.chatgpt.com/docs)
- **Work while the user is away.** One report says Work can keep going for hours while the user is away, with external-app actions still gated by approvals [S] — [SimpMusic blog](https://www.simpmusic.org/blogs/openai-launches-chatgpt-work-agent) (low-quality source)
- **2025 products.** ChatGPT Tasks (Jan 2025) scheduled prompts with push and email notifications [T] — [help.openai.com Tasks](https://help.openai.com/en/articles/10291617-tasks-in-chatgpt). ChatGPT agent could be scheduled to repeat a completed task [T] — [Introducing ChatGPT agent](https://openai.com/index/introducing-chatgpt-agent/). Pulse (Sep 2025, Pro, mobile) does asynchronous overnight research and delivers morning cards [T] — [Introducing ChatGPT Pulse](https://openai.com/index/introducing-chatgpt-pulse/)

### Inferences
- Resume support is strongest at the transport and session layer: background responses, stream cursors, SDK resume state, compaction items. I found no primary evidence of mid-task checkpoint and restore for ChatGPT Work after a server-side failure.

### Gaps
- Pages describing how Codex long-running work handles notifications and resume returned 404 at guessed URLs.
- The current status of Pulse and of the original Tasks feature in Nov 2026 was not verified.

## 5. Reported numbers: run lengths, benchmarks, failure modes, safety

### Takeaway
OpenAI's run-length claims went from roughly 7 hours (GPT-5-Codex, Sep 2025) to more than 24 hours (GPT-5.1-Codex-Max, Nov 2025). Both come from internal observation, not a public benchmark. Benchmarks reported include HLE, BrowseComp, SWE-bench Verified, Terminal-Bench 2.0 and GDPval. The 2026 numbers for GPT-5.6, Work and GPT-6.x were not found in primary sources.

### Cited Findings
- **GPT-5.1-Codex-Max.**
  - Ran for more than 24 hours in internal testing.
  - SWE-Bench Verified 77.9%, up from 73.7% for GPT-5.1-Codex; SWE-Lancer IC SWE 79.9%; Terminal-Bench 2.0 58.1%.
  - Launched 19 Nov 2025 in the CLI, IDE, cloud and code review.

  [S, reporting OpenAI's numbers] — [Neowin](https://www.neowin.net/news/openai-announces-gpt51-codex-max-a-new-coding-model-built-for-long-running-tasks/)
- **GPT-5-Codex (15 Sep 2025).**
  - Observed working independently for more than 7 hours on large, complex tasks, iterating on its implementation and fixing test failures.
  - Thinking time is dynamic: it uses fewer tokens on easy turns and more on hard ones.
  - SWE-bench Verified about 74.5%, against about 72.8% for GPT-5 high; code-refactoring eval 51.3%, against 33.9%.

  [T] — [Introducing upgrades to Codex](https://openai.com/index/introducing-upgrades-to-codex/) (403 in this session; spot-check the figures)
- **Deep research (Feb 2025).** HLE 26.6%, on an early o3 optimised for browsing [S] — [Fortune](https://www.fortune.com/2025/02/12/openai-deepresearch-humanity-last-exam); [Maginative](https://www.maginative.com/article/openai-unveils-deep-research-an-ai-agent-that-conducts-multi-step-research-tasks/). BrowseComp is 1,266 hard browsing questions; deep research scored about 51.5% [T, NOT confirmed by search] — [BrowseComp](https://openai.com/index/browsecomp/)
- **ChatGPT agent (Jul 2025).** HLE about 41.6% (44.4% with parallel rollouts), FrontierMath about 27.4%, BrowseComp about 68.9%, WebArena about 65.4%, SpreadsheetBench about 45.5%. It was treated as High biological/chemical capability under the Preparedness Framework, with safeguards enabled [T] — [Introducing ChatGPT agent](https://openai.com/index/introducing-chatgpt-agent/); [ChatGPT agent system card](https://openai.com/index/chatgpt-agent-system-card/) (both 403; treat the figures as approximate)
- **GDPval (Sep 2025).** An OpenAI eval of 44 occupations and 1,320 tasks graded by experts against professionals' work [T] — [GDPval](https://openai.com/index/gdpval/)
- **Failure modes and mitigations named in OpenAI material:**
  - Prompt injection from web content [S] — [help.openai.com](https://help.openai.com/en/articles/11752874-agent)
  - Over-eager action, addressed by confirmations and watch mode [S] — [help.openai.com](https://help.openai.com/en/articles/11752874-chatgpt-agent)
  - The unsolved residual risk OpenAI states itself ("don't eliminate all risks") [S] — [help.openai.com](https://help.openai.com/en/articles/11752874-chatgpt-agent)
  - Over-thoroughness prompts backfiring on GPT-5 [V] — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)
- **Product retirement as a failure of its own.** ChatGPT agent was reportedly retired without notice in Aug 2026 [S, single unverified source] — [Wikipedia](https://en.wikipedia.org/wiki/OpenAI_Operator)

### Inferences
- The "hours-long" claims rest on compaction plus test-driven iteration in a sandbox. They are anecdotes from internal use, not benchmarked task horizons. The writer should present them as OpenAI claims.

### Gaps
- No primary 2026 numbers were found: GPT-5.6, ChatGPT Work and GPT-6.1 Terra benchmarks and run lengths, and the system cards. openai.com was blocked (403).
- AgentKit (Agent Builder, ChatKit, Connector Registry, evals; announced Oct 2025 at DevDay [T] — [Introducing AgentKit](https://openai.com/index/introducing-agentkit/)) could not be re-verified, and its 2026 status is unknown.
