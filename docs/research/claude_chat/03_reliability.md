# How Claude finishes work reliably (research, 18 Nov 2026)

Everything below comes from primary Anthropic sources (anthropic.com/engineering, claude.com/blog, platform.claude.com docs, code.claude.com docs), which I read on 18 Nov 2026. I mark anything not from a primary source as UNCONFIRMED, and every number is quoted as Anthropic published it. Some features are Claude API features (server-side compaction, context editing, tool search, task budgets). A product running on other models, such as Hoola on GLM or Qwen, can only copy those as patterns in its own harness. Where a technique needs to be rebuilt client-side, its "Portable" line says how.

---

## A. The loop and how it decides it is done

**1. The loop is gather context → take action → verify → repeat, and the model controls the transitions.**
- What it is:
  - The Agent SDK post defines the loop as "gather context -> take action -> verify work -> repeat."
  - Claude Code's docs say the phases "blend together". Claude "decides what each step requires based on what it learned from the previous step, chaining dozens of actions together and course-correcting along the way."
  - Anthropic's SWE-bench scaffold was deliberately minimal: a prompt, a bash tool and an edit tool. Sampling continues "until the model decides that it is finished, or exceeds its 200k context length", so the model is "free to choose how it moves from step to step, rather than having strict and discrete transitions."
- Prevents: brittle hard-coded state machines that cannot recover when step N reveals something unexpected.
- Numbers: that minimal scaffold scored 49% on SWE-bench Verified, against a previous best of 45%.
- Sources:
  - https://claude.com/blog/building-agents-with-the-claude-agent-sdk
  - https://code.claude.com/docs/en/how-claude-code-works
  - https://www.anthropic.com/engineering/swe-bench-sonnet

**2. The API signal for "done" is `stop_reason: end_turn`, and every other stop reason means "not done yet".**
- What it is: the loop is literally "while stop_reason == tool_use: run tools, append results, call again."
- Ground truth matters: agents "check the environment for 'ground truth', such as tool results or code execution output, to assess progress." Anthropic adds that it is "common to add stopping conditions such as a maximum number of iterations." It publishes no specific value.
- Prevents: runaway loops and compounding errors.
- Sources:
  - https://www.anthropic.com/engineering/building-effective-agents
  - https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons

**3. A separate evaluator decides "done", not the model doing the work (`/goal` and Stop hooks).**
- Why it is needed: Claude Code's docs say plainly that "Claude stops when the work looks done. If it has nothing to run that tells it whether the work actually is done, 'looks done' is all it has to go on. In practice that makes you the test suite."
- What it is:
  - For long runs, "Claude sometimes ends a turn with a progress summary while items are still open, and the goal sends it back."
  - `/goal` is a prompt-based Stop hook. After every turn, a small fast model reads the condition and the conversation and returns one of three verdicts: Not yet met (Claude continues, taking the reason as guidance), Met, or Impossible.
  - The evaluator "doesn't run commands or read files independently", so the condition must be "something Claude's own output can demonstrate". A good condition has one measurable end state, a stated check (for example "`npm test` exits 0"), and constraints that must not be broken.
  - The loop is bounded: if Claude keeps answering "without making progress (no tool use for several turns in a row)", the loop stops.
  - Errors that cannot be retried away (auth, credit, a context overflow compaction could not clear) clear the goal. Transient errors retry up to 3 times, then pause.
- Prevents: premature "victory" summaries, and infinite busy-looping.
- Sources:
  - https://code.claude.com/docs/en/best-practices
  - https://code.claude.com/docs/en/goal
- Portable: after each final reply, run one cheap-model check ("given the transcript, is condition X demonstrated? met / not_met / impossible + reason"). Feed not_met back as the next user turn, and stop after N turns with no tool use.

---

## B. Verification before claiming done

**4. Give the agent a pass/fail check, and demand evidence rather than claims.**
- What it is:
  - "Give Claude something it can run that comes back pass or fail. Once it has that, it can keep going on its own and you don't have to watch."
  - Ask for evidence: "the command it ran and its output, or the screenshot. 'All tests pass' on its own tells you very little."
  - Use a reviewer that "never saw your conversation", so it "isn't swayed by the reasoning that produced the code." Scope that reviewer ("skip style"), because "a reviewer that's asked to find problems will always find *something*."
- Prevents: claimed-but-false completion, and over-fixing based on nitpicks.
- Source: https://code.claude.com/docs/en/best-practices

**5. Verify end to end, as a user would.**
- What it is: the long-running harness post lists "marking features done without testing" as a core failure, where the agent relied on unit tests or `curl` and missed end-to-end breaks. The fix was prompting the agent to "use browser automation tools and do all testing as a human user would". Anthropic says this "dramatically improved performance", but gives no number.
- Verification methods, from the Agent SDK post:
  - rules-based (linting, the strongest)
  - visual (screenshots)
  - LLM-as-judge, which it calls "generally not a very robust method"
- Sources:
  - https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
  - https://claude.com/blog/building-agents-with-the-claude-agent-sdk

**6. Protect the definition of done from the agent.**
- What it is:
  - Keep the full scope as a JSON feature list where every item starts failing and has a `passes` field. The agent may change only that field.
  - Anthropic chose JSON "because the model is less likely to overwrite it than Markdown."
  - The instruction used: "It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality."
  - Against reward-hacking: "Do not hard-code values or create solutions that only work for specific test inputs… If… any of the tests are incorrect, please inform me rather than working around them."
- Prevents: "declaring victory too early" (a later session sees progress and calls the project done) and gaming the tests.
- Sources:
  - https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

**7. Investigate before answering, and say a check was done only if a tool showed it.**
- What it is: two prompt blocks Anthropic publishes.
  - `<investigate_before_answering>`: "Never speculate about code you have not opened… you MUST read the file before answering."
  - The payments and records block, which applies to any agent: "Say a check was done only if a tool result in this session showed it before you acted. Otherwise name who told you about it. Say plainly if a required check was skipped."
- Prevents: hallucinated state, and false "verified" claims.
- Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

---

## C. Planning, to-do lists and state

**8. Plan first, then keep the plan outside the context window.**
- Claude Code has a Plan permission mode ("explores and proposes a plan without editing your source files"). Its best practices describe writing a SPEC.md and starting "a fresh session to build from it, so the build begins with a clean context and a written definition of done."
- In the multi-agent research system, the lead agent "saves its plan to memory, since context over 200,000 tokens gets truncated."
- Context engineering names structured note-taking as a core technique: "a to-do list or a NOTES.md file", reloaded later.
- Sources:
  - https://code.claude.com/docs/en/how-claude-code-works
  - https://code.claude.com/docs/en/best-practices
  - https://www.anthropic.com/engineering/multi-agent-research-system
  - https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

**9. Work one item at a time, with a session-start ritual and a clean exit.**
- What it is:
  - Use a different prompt for the first window (the "initializer"), which writes the feature list, `init.sh`, `claude-progress.txt` and an initial git commit.
  - Every later session runs the same ritual: check the working directory, read the git log and progress file, read the feature list, start the server via `init.sh`, and run a basic end-to-end test to catch breakage left by the previous session.
  - Every session ends with a commit and a progress update.
  - Anthropic's guidance: use JSON for structured state, free text for progress notes, and git as "a log … and checkpoints that can be restored."
- Prevents:
  - "trying to one-shot the app" (running out of context mid-feature)
  - leaving the environment broken
  - wasting time re-learning how to run the app
- Sources:
  - https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool (the "Multisession software development pattern")

**10. Tell the model about context resets so it does not stop early.**
- Suggested prompt text: "Your context window will be automatically compacted… do not stop tasks early due to token budget concerns. As you approach your token budget limit, save your current progress and state to memory…"
- The memory tool's auto-injected system prompt says: "ALWAYS VIEW YOUR MEMORY DIRECTORY BEFORE DOING ANYTHING ELSE… ASSUME INTERRUPTION: Your context window might be reset at any moment."
- Prevents: models "naturally attempt[ing] to bring its work to a close as it approaches the context limit."
- Sources:
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool

---

## D. Tool design and avoiding wrong-tool choice

**11. Fewer, consolidated, non-overlapping tools with distinct purposes.**
- "Overlapping tools distract agents." Aim for a "minimal viable set of tools."
- Consolidate multi-step operations, for example `search_contacts` instead of `list_contacts`, or `get_customer_context` instead of several lookups.
- The docs recommend grouping actions under one tool with an `action` parameter rather than separate `create_pr` / `review_pr` / `merge_pr` tools.
- Sources:
  - https://www.anthropic.com/engineering/writing-tools-for-agents
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools

**12. Write descriptions like docs for a new hire, and namespace names.**
- Descriptions are "by far the most important factor in tool performance". Say what the tool does, when to use it and when not, what each parameter means, and its caveats.
- "Aim for at least 3–4 sentences for each tool description."
- Use unambiguous parameter names (`user_id`, not `user`) and namespace prefixes (`github_list_prs`).
- Small description changes matter: Claude Sonnet 3.5 reached state of the art on SWE-bench Verified after "precise refinements to tool descriptions" (no delta published).
- A tool-testing agent that rewrote flawed MCP tool descriptions "cut task completion time by 40%."
- Sources:
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
  - https://www.anthropic.com/engineering/writing-tools-for-agents
  - https://www.anthropic.com/engineering/multi-agent-research-system

**13. Poka-yoke the interface (make wrong use structurally hard).**
- Anthropic "always require[s] absolute filepaths" after the model erred with relative paths. After that change, the model "used this method flawlessly."
- The edit tool replaces only when there is "exactly one match of `old_str`".
- Anthropic spent more time on tools than on the prompt.
- Sources:
  - https://www.anthropic.com/engineering/building-effective-agents
  - https://www.anthropic.com/engineering/swe-bench-sonnet

**14. Tool search with deferred loading, once the tool count grows.**
- "Claude's ability to pick the right tool degrades once you exceed 30–50 available tools."
- How it works: mark tools `defer_loading: true`. Claude searches (regex or BM25) and gets 3–5 tools by default, and the full definitions are expanded in.
- Keep your "3–5 most frequently used tools non-deferred". Use it when there are 10 or more tools or more than 10k tokens of definitions.
- Numbers: on internal MCP evals, Opus 4 went from 49% to 74% and Opus 4.5 from 79.5% to 88.1%. Definitions fell from about 77K to about 8.7K tokens, an 85% reduction.
- Sources:
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
  - https://www.anthropic.com/engineering/advanced-tool-use
- Portable: a client-side search tool that returns tool names, after which you add those definitions to the next request (the docs describe a custom `tool_reference` implementation).

**15. Strict schemas and input examples.**
- `strict: true` uses grammar-constrained sampling, so inputs "always match your schema". There is "no need to validate and retry tool calls", and `"2"` versus `2` mismatches cannot happen.
- `input_examples` raised complex-parameter accuracy from 72% to 90% in internal testing, at roughly 20–50 tokens per simple example and 100–200 per complex one.
- Sources:
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use
  - https://www.anthropic.com/engineering/advanced-tool-use

**16. Be explicit about acting versus suggesting.**
- "If you say 'can you suggest some changes,' Claude will sometimes provide suggestions rather than implementing them."
- Use a `<default_to_action>` block (or the conservative `<do_not_act_before_instructions>` block) to set the default.
- Newer models overtrigger on aggressive wording such as "CRITICAL: You MUST use this tool". Use "Use this tool when…" instead.
- Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

---

## E. Tool errors and retries

**17. Return errors as `tool_result` with `is_error: true` and an instructive message.**
- "Write instructive error messages. Instead of generic errors such as 'failed', include what went wrong and what Claude should try next (for example, 'Rate limit exceeded. Retry after 60 seconds.')." Do not return opaque codes or tracebacks.
- "If a tool request is invalid or missing parameters, Claude will retry 2–3 times with corrections before apologizing to the user."
- For truncated results, tell the agent how to narrow its next call.
- Sources:
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
  - https://www.anthropic.com/engineering/writing-tools-for-agents

**18. Get the message structure right, or the loop silently degrades.**
- Every `tool_use` needs its `tool_result` immediately after it. Results must come first in the user message, all results must go in one user message, and no text should follow them.
- Separate result messages "teach" Claude to stop making parallel calls.
- Text added after tool results causes empty `end_turn` replies ("exactly 2–3 tokens with no content"), because Claude learns to expect user input after every tool. Do not retry an empty response unchanged. Fix the structure; "Please continue" is a last resort.
- If a parallel call fails because its prerequisite has not run, return `is_error` and "Claude will reissue the call on the next turn". You can also add the system-prompt rule "Only batch tool calls that are independent of each other."
- Sources:
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use
  - https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons

**19. Make production failures resumable.**
- "Resume from the point of failure instead of restarting", combining retry logic with regular checkpoints.
- "Let the agent know when a tool is failing so it can adapt."
- Use rainbow deployments, because agents are long-lived and stateful.
- Source: https://www.anthropic.com/engineering/multi-agent-research-system

---

## F. Keeping context clean in long tasks

**20. Treat context as a finite attention budget.**
- "Context rot": recall falls as the window fills, because transformers form "n² pairwise relationships for n tokens."
- Prefer just-in-time retrieval: keep paths, queries and links, and load on demand (use `head`/`tail`, not whole files). A hybrid is fine, for example loading CLAUDE.md up front and fetching the rest with grep.
- Cap tool output: Claude Code limits tool responses to 25,000 tokens by default.
- Offer a `response_format` concise/detailed enum. Anthropic's example was 206 versus 72 tokens, about one-third with concise.
- Sources:
  - https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
  - https://www.anthropic.com/engineering/writing-tools-for-agents

**21. Clear old tool results (context editing).**
- Context engineering calls it "one of the safest lightest touch forms of compaction."
- API strategy `clear_tool_uses_20250919`:
  - defaults: trigger 100,000 input tokens, keep the last 3 tool uses
  - `clear_at_least` (so the cache break is worth it), `exclude_tools`, `clear_tool_inputs`
  - near the threshold, Claude gets a warning so it can save results to memory first
- Numbers: on an internal agentic-search eval, context editing alone gave +29%, and with the memory tool +39%. In a 100-turn web search eval it let agents finish workflows that otherwise failed, "reducing token consumption by 84%."
- Sources:
  - https://platform.claude.com/docs/en/build-with-claude/context-editing
  - https://claude.com/blog/context-management
- Portable: in your own history builder, replace tool results older than the last K with "[result cleared - re-run tool if needed]", while keeping the tool_use blocks.

**22. Compaction, or a fresh start from files.**
- Compaction "replaces the older turns of a conversation with a summary"; "response quality degrades as a conversation grows."
- Tune the summarizer for recall first, then precision. Claude Code also keeps "the five most recently accessed files."
- Its auto-compaction "keeps your requests and key code snippets, but detailed instructions from early in the conversation may be lost", so persistent rules belong in CLAUDE.md. It also stops after a few thrashing attempts rather than looping.
- Alternative: "consider starting with a brand new context window rather than using compaction. Claude's latest models are extremely effective at discovering state from the local filesystem."
- Sources:
  - https://platform.claude.com/docs/en/build-with-claude/compaction
  - https://code.claude.com/docs/en/how-claude-code-works
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

**23. Do the heavy lifting in code, not in context.**
- "Code execution with MCP": tools are presented as code APIs, and data is filtered in the sandbox ("The agent sees five rows instead of 10,000"). One workflow fell from 150,000 to 2,000 tokens, a 98.7% reduction.
- Programmatic tool calling: average tokens fell from 43,588 to 27,297 (−37%). Internal knowledge retrieval rose from 25.6% to 28.5%, and GIA from 46.5% to 51.2%. Use it for 3 or more dependent calls, or when only aggregates are needed.
- Sources:
  - https://www.anthropic.com/engineering/code-execution-with-mcp
  - https://www.anthropic.com/engineering/advanced-tool-use

**24. Progressive disclosure for skills.**
- Only each skill's name and description sit in the system prompt. The full SKILL.md is read when relevant, and linked files only as needed, so bundled context is "effectively unbounded."
- Deterministic scripts inside a skill run without loading the script or the data into context.
- Source: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

**25. Prompt caching keeps long loops affordable, but only if the prefix is stable.**
- Pricing and timing:
  - cache writes cost 1.25× (5-minute TTL) or 2× (1-hour TTL); reads cost 0.1× of base input
  - reads are 0.05× on Opus 5.5 and Sonnet 5.5
  - the TTL refreshes free on each use
  - up to 4 breakpoints; automatic caching moves the breakpoint forward as the conversation grows
- The prefix order is tools → system → messages. Changing tool definitions invalidates everything. Changing thinking, effort or tool_choice invalidates the message blocks.
- Reliability implication: keep the tool list and system prompt fixed within a turn, and add per-turn context at the end.
- Source: https://platform.claude.com/docs/en/build-with-claude/prompt-caching

---

## G. Sub-agents

**26. Use sub-agents to keep the main context clean, and have them return condensed results.**
- Each sub-agent may burn "tens of thousands of tokens or more" but returns "often 1,000-2,000 tokens."
- Claude Code: "the subagent's tool calls stay out of your context, and Claude gets back a summary."
- Sub-agents should write their outputs to external storage and pass back lightweight references.
- Sources:
  - https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
  - https://code.claude.com/docs/en/how-claude-code-works
  - https://www.anthropic.com/engineering/multi-agent-research-system

**27. Delegate with a full brief, and scale effort to the task.**
- Each sub-agent needs "an objective, an output format, tool and source guidance, and clear task boundaries. Vague instructions caused duplicated work."
- Effort rules:
  - simple: 1 agent, 3–10 calls
  - comparisons: 2–4 sub-agents, 10–15 calls each
  - complex research: more than 10 sub-agents
- Parallelism: the lead spawns 3–5 sub-agents, each using 3 or more tools in parallel, which cut research time by up to 90%.
- Numbers:
  - multi-agent beat single-agent Opus 4 by 90.2% on the internal research eval
  - token usage alone explained 80% of the variance (95% together with tool-call count and model)
  - cost: agents use about 4× chat tokens; multi-agent about 15×
- Do not overuse sub-agents. Use them "when tasks can run in parallel, require isolated context… For simple tasks, sequential operations, single-file edits… work directly."
- Sources:
  - https://www.anthropic.com/engineering/multi-agent-research-system
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

**28. Parallel tool calls by prompt.**
- System prompt text: "For maximum efficiency, whenever you need to perform multiple independent operations, invoke all relevant tools simultaneously rather than sequentially."
- A stronger `<use_parallel_tool_calls>` block exists. Read-only operations are safe to run in parallel; run side-effect tools sequentially.
- Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use

---

## H. Streaming progress to the user

**29. Short narration before tool calls, plus explicit progress updates.**
- Claude "often comments on what it's doing… before calling tools" (for example "I'll check the current weather…"). That text should be treated as plain prose, with nothing parsed from it.
- Newer models "might skip verbal summaries after tool calls". If you want visibility, add the prompt "After completing a task that involves tool use, provide a quick summary of the work you've done."
- On recent models, the API returns progress updates as separate thinking blocks immediately before a tool call ("what the model just found and what it's about to do next, written for the person watching"). `display: "updates"` exposes only those, to render as a status line.
- Fine-grained tool streaming (`eager_input_streaming: true`) streams large tool inputs without buffering. You may receive invalid JSON. Return `{"INVALID_JSON": "<raw>"}` with `is_error: true`.
- Users can steer mid-run: in Claude Code, a typed message is read "as soon as those calls finish, within the same turn."
- Sources:
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
  - https://platform.claude.com/docs/en/build-with-claude/thinking
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming
  - https://code.claude.com/docs/en/how-claude-code-works

---

## I. Recovering from max_tokens and pause_turn

**30. Handle every stop reason explicitly.**

| stop_reason | What to do |
|---|---|
| `max_tokens` | "Raise `max_tokens` or continue the response." If the last block is an incomplete `tool_use`, "retry the request with a higher `max_tokens`" (never run a half tool call). If you cannot continue, append a notice that the output is incomplete. |
| `pause_turn` | The server-tool loop hit its limit (default 10 iterations). "Send the response back as-is" with no new user message, and pass the `container` id back or files are lost. |
| `refusal` | Read `stop_details` and retry on a fallback model. |
| `model_context_window_exceeded` | Treat as truncated. |

- Thinking counts toward `max_tokens`. At high effort, set it large; the docs say 64k is a reasonable start at xhigh/max.
- Source: https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons

**31. Thinking, effort and budgets.**
- Thinking blocks must be passed back "complete and unmodified" within a tool-use turn, because the signature carries the reasoning. With adaptive thinking, interleaved thinking (reasoning between tool calls) is automatic.
- Suggested prompt: "After receiving tool results, carefully reflect on their quality and determine optimal next steps."
- Effort governs all output tokens. Lower effort means "fewer and terser tool calls". Haiku 5.5 at `low` "is more likely to skip a search, stop early, or skip a check", which hurts reliability.
- Task budgets (beta) give the model a server-side countdown for the whole loop, so it "finish[es] gracefully" instead of cutting off. The minimum is 20,000. A budget that is too small causes refusal-like early stops.
- Forcing `tool_choice` skips thinking.
- Think tool (older): +54% relative on τ-bench airline (0.570 vs 0.370 pass^1; the post's own table shows 0.584/0.332), and +1.6% on SWE-bench. Anthropic's December 2025 note now prefers extended/adaptive thinking in most cases.
- Sources:
  - https://platform.claude.com/docs/en/build-with-claude/thinking
  - https://platform.claude.com/docs/en/build-with-claude/effort
  - https://platform.claude.com/docs/en/build-with-claude/task-budgets
  - https://www.anthropic.com/engineering/claude-think-tool

---

## J. Summarising results back to the user

**32. Synthesize with grounded attribution.**
- The research system's lead synthesizes the sub-agent results, then a separate CitationAgent attributes claims to sources.
- The API's citations feature guarantees "valid pointers to the provided documents". Anthropic says it is "significantly more likely to cite the most relevant quotes" than prompt-based citing, and `cited_text` costs no output tokens.
- Report facts, not celebration: newer models give "fact-based progress reports rather than self-celebratory updates."
- Sources:
  - https://www.anthropic.com/engineering/multi-agent-research-system
  - https://platform.claude.com/docs/en/build-with-claude/citations
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

**33. Gate irreversible actions.**
- Prompt block: "Consider the reversibility and potential impact of your actions… for actions that are hard to reverse, affect shared systems, or could be destructive, ask the user before proceeding… do not use destructive actions as a shortcut."
- Claude Code snapshots files before edits. Remote side effects cannot be checkpointed, so they need permission gates.
- Anthropic's payments block: "Never initiate, send or release a payment… Prepare the payment request and leave the release to a person". It adds that a prompt "guides… and doesn't enforce anything, so have a person approve each call to any tool that can move money."
- Sources:
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
  - https://code.claude.com/docs/en/how-claude-code-works

---

## K. Measuring reliability with evals

**34. pass^k, not just pass@k.**
- pass@k is the chance of at least one success in k tries. pass^k is the chance that all k succeed. Example: a 75% per-trial rate gives 0.75³ ≈ 42% at pass^3. By k=10, pass@k nears 100% while pass^k falls toward 0%.
- Use pass^k for customer-facing consistency. The think-tool post reported gains holding "up to k=5".
- Source: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

**35. Build the eval harness right.**
- Start with "20-50 simple tasks drawn from real failures." The research post started with about 20 queries, because large effect sizes show up in small samples.
- Write tasks two experts would grade the same way, and give each a reference solution.
- Grade the outcome, the final environment state ("whether a reservation actually exists in the database, not whether the agent said it did"), not the path, which is "overly brittle". Give partial credit.
- Isolate trials (clean environment, no leftover git or files).
- Balance the sets: test when a behaviour should and should not happen.
- Treat near-0% results as a broken task or grader. Opus 4.5 went from 42% to 95% on CORE-Bench after grader and spec fixes.
- Graders:
  - code (fast, objective, brittle)
  - model (rubric, calibrated against humans, allowed to answer "Unknown", one isolated judge per dimension)
  - human (gold standard)
- The research system's single-call judge produced 0.0–1.0 scores plus pass/fail across accuracy, citations, completeness, source quality and tool efficiency.
- Keep capability evals (low pass rate) separate from regression evals (about 100%). Read transcripts.
- Track tool metrics too: accuracy, runtime, total calls, tokens and errors. Redundant calls point to pagination problems; invalid-parameter errors point to bad descriptions. Use held-out sets.
- Sources:
  - https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
  - https://www.anthropic.com/engineering/multi-agent-research-system
  - https://www.anthropic.com/engineering/writing-tools-for-agents

---

## Unconfirmed or caveated items
- The 39% / 29% / 84% context-editing figures are internal Anthropic results (primary source claude.com/blog/context-management). The 84% baseline is not defined there.
- The think-tool airline numbers disagree between the post's text and its table, as noted above.
- Anthropic publishes no numeric value for: the "maximum number of iterations" stop condition, the browser-testing gain, or the SWE-bench gain from tool-description refinement.
- Model names and defaults (Opus 5.5 at medium effort, and so on) are as the docs state today, and they change per model.

---

## Top 12 techniques ranked by impact on reliability
1. **A pass/fail check the agent runs itself**, with evidence (command plus output) required before "done" (#4, #5).
2. **A separate evaluator after every turn decides "done"**, not the working model, bounded by no-progress and error rules (#3).
3. **Durable state outside context**: a JSON task list with only `passes` editable, progress notes, git commits, and a session-start ritual (#6, #9).
4. **Correct loop mechanics**: every tool_use paired, results first and together, no trailing text, and every stop_reason handled, including truncated tool calls and `pause_turn` (#18, #30).
5. **Instructive `is_error` results** (what failed, what to try next), plus strict schemas so malformed calls cannot happen (#15, #17).
6. **Few, distinct, well-described, namespaced tools**, with deferred loading or tool search past about 10–30 tools (#11–#14).
7. **Context hygiene**: clear old tool results, cap and paginate outputs, retrieve just in time (#20, #21).
8. **Compaction or fresh-window restarts from files**, plus telling the model it will not lose its work so it does not stop early (#10, #22).
9. **Sub-agents with full briefs that return 1–2k-token summaries or file references**, used only where work is parallel or isolated (#26, #27).
10. **Interleaved and adaptive thinking with blocks passed back unmodified**, with effort set high enough that checks are not skipped (#31).
11. **Human gates on irreversible and money actions**, enforced in code, not only in the prompt (#33).
12. **Outcome-graded evals measured as pass^k** on 20–50 real-failure tasks, with calibrated graders and transcript reading (#34, #35).
