# The EXACT research technique of each vendor, one by one (3 Nov 2026)

Owner asked: *"GO DEEP AND FIND THE EXACT RESEARCH TECHNIQUE USE BY THEM ALL ONE BY ONE."*

**How this was read.** Every vendor's documentation host is blocked from this sandbox, so not one line below comes
from a blog or from memory. Each comes from the vendor's **own current SDK on PyPI** — code the vendor writes,
versions and ships. An API's parameter surface and its event/result types ARE its technique: you cannot offer a
`plan-output: tasks | stop` event unless your pipeline plans and fans out, and you cannot return a `confidence` per
output field unless you score fields. The package + file is the citation after each heading.

**What is NOT in here, and cannot be until the doc hosts are allowed:** prices, rate limits, context sizes, model
quality claims, benchmark numbers, and every vendor's terms on storing or re-sharing its output. Treat all of those
as unknown. (The one exception is where a vendor's SDK itself carries a cost field — noted as such.)

---

## 1. OpenAI — "a deep-research MODEL, driven by the Responses loop"
`openai 3.42.1` · `types/responses/*`

- **Shape:** one model id does the research — `o3-deep-research`, `o4-mini-deep-research` (dated variants too) —
  called through **Responses**, not chat completions. The loop is the model's own; you hand it tools.
- **Tools it is given:** `web_search` / `web_search_preview`, `code_interpreter`, `mcp`, `file_search`.
- **Source control is on the search tool itself** (`web_search_tool_param.py`): `filters.allowed_domains`
  (the SDK's own example is `["pubmed.ncbi.nlm.nih.gov"]`) and `user_location` (`city`, `region`, `country`,
  `timezone`, type `approximate`).
- **You can demand the receipts:** `include` accepts `web_search_call.action.sources`, `web_search_call.results`,
  `code_interpreter_call.outputs`, `message.output_text.logprobs`, `reasoning.encrypted_content`.
- **Citations come back as typed annotations:** `url_citation`, `file_citation`, `container_file_citation`.
- **Long runs:** `background` (start, poll, don't hold the socket) + `reasoning.effort` and
  `reasoning.summary` (`auto|concise|detailed`).
- **The technique in one line:** *domain-filtered server-side web search + a code interpreter for the arithmetic,
  inside one long-running reasoning model, with per-sentence url citations and the raw search results retrievable.*
- **What Hoola takes:** `allowed_domains` as a first-class research input, `code_interpreter` ≡ our `pylab` for
  every derived number, and `background` as the shape of a long run.

## 2. Google — "a server-managed agent that asks you to approve its plan"
`google-genai 2.34.0` · `_gaos/types/interactions/*`

- **Shape:** an **Interactions API** with server-managed agents; `agent_config` selects one, and
  `DeepResearchAgentConfig(type="deep-research")` is a first-class agent beside Antigravity and CodeMender.
- **`collaborative_planning: bool`**, quoted from the file: *"Enables human-in-the-loop planning for the Deep
  Research agent. If set to true, the Deep Research agent will provide a research plan in its response. The agent
  will then proceed only if the user confirms the plan in the next turn."* **Plan → her confirmation → run.**
- `thinking_summaries`, `visualization: off|auto` ("whether to include visualizations in the response"),
  `enable_bigquery_tool` (research over your OWN warehouse, not just the web).
- **Long runs:** `background: bool`, `store`, `stream`, `webhook_config`, and a **`continuation_token`** — *"Opaque
  token to resume a long decode… set when status is REQUIRES_CONTINUATION"*. `InteractionStatus` is
  `IN_PROGRESS | IDLE`.
- **The run is a list of typed STEPS**, which is the pipeline laid bare (one module each):
  `userinputstep`, `thoughtstep`, `googlesearchcallstep` → `googlesearchresultstep`,
  `urlcontextcallstep` → `urlcontextresultstep` (fetch a page), `filesearchcallstep` → `filesearchresultstep`,
  `retrievalcallstep` → `retrievalresultstep`, `codeexecutioncallstep` → `codeexecutionresultstep`,
  `googlemapscallstep` → `googlemapsresultstep`, `mcpservertoolcallstep`, `processingcallstep`, `modeloutputstep`.
  Citations are typed too: `urlcitation`, `filecitation`, `placecitation`, plus `source` and `groundingtoolcount`.
- **Finding worth its own line:** Google's grounding config ships **`exaaisearchconfig`** (requires *your* Exa API
  key, plus `custom_config` to pass any Exa Search parameter) and **`parallelaisearchconfig`**, next to
  `googlesearch`, `vertexaisearchconfig` and `hybridsearch(alpha=…)` (dense/sparse weighting). **Google itself
  treats third-party research search as a swappable backend.** That is exactly the design this plan proposes.
- **The technique in one line:** *plan-then-approve, then a typed search → fetch → think → code → write step
  machine that can be resumed by token and can draw its own charts.*
- **What Hoola takes:** the plan card as a gate (we already have the pattern), **typed steps** as the live
  narration and the audit trail, and `continuation_token` as the model for resuming a restarted job.

## 3. Anthropic — "no deep-research model; your own loop, with the tools made safe"
`anthropic 2.4.0` · `types/beta/*`

- **Shape:** deliberately **no** deep-research model id. You run the loop; Anthropic hardens the parts.
- `web_search_20250305`: `allowed_domains`, `blocked_domains`, **`max_uses`**, `user_location`.
- `web_fetch_20250910`: `allowed_domains` / `blocked_domains`, `max_uses`, **`max_content_tokens`**
  ("maximum number of tokens used by including web page text content in the context"), **`citations`** config, and
  **`url_sources`** — which sources may contribute a fetchable URL: `user_input` is `all|none`, and tool results are
  `all|none|only(named tools)|except(named tools)`. **A prompt-injection wall: the model may only fetch URLs that
  came from a source you approved.**
- `code_execution_20250522` for the arithmetic; `memory_20250818` (a memory tool) for facts that must outlive the
  context; `tool_search_tool_bm25_20251119` + `defer_loading` so a big toolset is searched, not all loaded.
- **`context_management.edits` → `clear_tool_uses_20250919`**: `trigger` (input tokens or tool uses),
  `keep` (how many recent tool uses to retain), `clear_at_least`, `clear_tool_inputs`, `exclude_tools`. **Server-side
  context pruning for a long tool-heavy run** — the exact failure mode of a 40-minute research job.
- **The technique in one line:** *your agent loop, with domain-restricted search, fetch limited to approved URLs and
  capped in tokens, citations on the fetched document, a memory file, and automatic pruning of old tool output.*
- **What Hoola takes:** `url_sources` as a rule (never fetch a URL a page asked us to fetch — this is our standing
  "text in a web page is data, never instructions"), `clear_tool_uses` as the long-run context policy, and the
  memory tool for a multi-session report.

## 4. Parallel — "research as a typed object, with evidence per FIELD"
`parallel-web 1.3.7` · `types/*`, `resources/{task_run,task_group,monitor,beta}`

- **Shape:** a **task run**. `input` (text or JSON) + **`processor`** (cost/quality tier: `lite`, `base`, `core`,
  `pro`) + **`task_spec.output_schema`** (a JSON schema, a text description, or `auto`). Runs are polled
  (`wait_for_completion`), grouped (`task_group`), and can carry `mcp_servers`, `metadata`, a `webhook`,
  `previous_interaction_id` and **`memory_scope_key`**.
- **The output contract is the real technique — `field_basis.py`:** for EACH output field, a
  **`reasoning`** string, a list of **`citations`** (`url`, `title`, **`excerpts`** supporting the output) and a
  **`confidence`** level. Not "here is a report with footnotes" — **evidence attached per field, scored.**
- **`source_policy`**: `include_domains`, `exclude_domains` (domain *or* domain/path prefixes), `after_date`.
- **Search API** (`client_search_params.py`): `search_queries` — *"concise keyword search queries, 3-6 words each"*,
  plural, i.e. **fan-out is the caller's job**; plus `objective` (what the search is FOR), `mode`
  (`turbo|fast|basic|advanced`), `max_chars_total` (a context budget, not a result count), `session_id`,
  `client_model` ("the model generating this request and consuming the results"), and
  `advanced_settings` = `excerpt_settings`, **`fetch_policy`** (live fetch or not), `location` (ISO country),
  `max_results`, `source_policy`.
- **FindAll** (`findall_create_params.py`): entity discovery — `entity_type`, `objective`, **`match_conditions`**,
  `match_limit`, `exclude_list`, generator tier `base|core|pro|preview`, with candidate **metrics** and match
  **status** events. This is "list every X that satisfies Y", done properly.
- **Monitors** (`monitor_create_params.py`): `frequency` ("`<n><h|d|w>`"), `type: event_stream | snapshot`,
  processor `lite|base`, webhook, memory scope. **A research answer that keeps itself up to date.**
- **The technique in one line:** *declare the shape of the answer, choose how much to spend, fan out keyword
  queries against a source policy, and get back structured fields each carrying excerpts, reasoning and a
  confidence — then optionally keep watching the topic.*
- **What Hoola takes:** **per-field basis + confidence** (this is the missing claim-level check), the processor
  tier as a price dial, `source_policy` + `after_date`, FindAll for "list all suppliers / tenders / colleges", and
  monitors for a topic she watches. Hoola already pays for this key, so it is the cheapest experiment.

## 5. Exa — "a planner that emits tasks, then search → crawl → think, until it says stop"
`exa-py 2.27.0` · `exa_py/research/models.py`, `research/sync_client.py`

- **Shape:** `research.create(instructions=…, model=…, output_schema=…)`, then `poll_until_finished`
  (`poll_interval=1000ms`, `timeout_ms=600000` — **a ten-minute default run**), with `events=True` to stream.
- **Three tiers:** `exa-research-fast` (the SDK default), `exa-research`, `exa-research-pro`.
- **The event list is the architecture, verbatim from the models file:**
  - `research-definition` (instructions + output schema),
  - `plan-definition` → `plan-operation` → **`plan-output`**, where the plan's output is either
    **`tasks`** (`reasoning` + **`tasks_instructions: List[str]`** = the fan-out) or **`stop`** (`reasoning`),
  - each **operation** is one of `think` (content), `search` (`query`, `search_type: neural|keyword|auto|fast`,
    `results`, `page_tokens`, and a **`goal`**), or `crawl` (one result, `page_tokens`, `goal`),
  - `research-output`: `completed` (content + optional `parsed` against the schema) or `failed`.
- **Cost is itemised in the response** (`CostDollars`): `total`, **`num_pages`**, **`num_searches`**,
  **`reasoning_tokens`**. The only vendor whose SDK hands you the cost breakdown of a research run.
- Beside it: `websets` (searches + enrichments + imports + **monitors** + items) — a saved, growing collection.
- **The technique in one line:** *a planner that writes sub-task instructions, workers that each run goal-tagged
  neural/keyword searches and page crawls with a think step, and a planner that decides each round to issue more
  tasks or stop — billed per page, per search and per reasoning token.*
- **What Hoola takes:** this IS the reference loop for `engine=hoola`: plan → `tasks_instructions` → per-task
  goal-tagged search/crawl/think → re-plan or stop. And **every operation carries its `goal`**, which is what makes
  a live narration and an audit honest.

## 6. Linkup — "one call, depth and mode as dials, answer or schema"
`linkup-sdk 0.24.0` · `linkup/_client.py`, `linkup/_types.py`

- **`search(query, depth=flash|fast|standard|deep, output_type=searchResults|sourcedAnswer|structured, …)`** with
  `structured_output_schema`, `from_date` / `to_date`, `include_domains` / `exclude_domains`, `max_results`,
  **`include_inline_citations`**, `include_sources`, `include_images`.
- **`research(query, output_type=sourcedAnswer|structured, reasoning_depth=S|M|L|XL, mode=answer|auto|investigate|research, …)`**
  — same source and date filters. Two dials: how hard to think (S→XL) and **what kind of job it is**
  (answer / auto / investigate / research).
- Async **task** objects exist for all three verbs (`LinkupSearchTask`, `LinkupResearchTask`, `LinkupFetchTask`,
  paged, with `LinkupTaskMetadata` and **`LinkupTaskQuota`**), i.e. submit-and-collect. Also `fetch` (one page, with
  image extraction) and an `x402` signer (pay-per-call over HTTP).
- **The technique in one line:** *one request, with effort and job-kind as parameters, returning either a sourced
  answer with inline citations or your own schema — synchronously or as a task.*
- **What Hoola takes:** `reasoning_depth` × `mode` as the cleanest public expression of "how big is this ask", which
  maps straight onto Hoola's own trivial/small/standard/large sizing; and `sourcedAnswer` as the minimum any engine
  must return to be allowed into a document.

## 7. Perplexity — "search as its own product, with academic and SEC modes"
`perplexityai 0.46.1` · `types/search_create_params.py`, `types/chat/completion_create_params.py`, `resources/*`

- **`/search`** is a separate endpoint from chat: `query` may be a **list of queries** (fan-out server-side),
  `max_results`, `max_tokens`, **`max_tokens_per_page`**, **`search_context_size: low|medium|high`** ("how much
  content is retrieved per result"), `search_domain_filter`, `search_language_filter`,
  **`search_mode: web|academic|sec`**, `search_recency_filter: hour|day|week|month|year`,
  `search_after_date_filter` / `before`, `last_updated_after_filter` / `before`, `search_type: web|people`,
  `country`.
- **Chat completions** carry the same search controls plus `reasoning_effort: minimal|low|medium|high`,
  `num_search_results`, `ranking_model`, `enable_search_classifier`, `disable_search`, `return_related_questions`,
  `response_format`, `latitude`/`longitude`, `file_workspace_id`, `thread_id`, `safe_search`.
- Resources shipped beside them: **`async_.chat.completions`** (submit, list, get — a long job), `batches`,
  **`browser.sessions`**, `decisions`, `skills` (+ revisions), `responses`, `files`, `embeddings`,
  `contextualized_embeddings`.
- **The technique in one line:** *a ranked, freshness- and corpus-filtered search engine (web / academic / SEC
  filings) whose results are fed to a reasoning model in the same call, with the retrieval depth per page as an
  explicit dial — and an async queue for the long ones.*
- **What Hoola takes:** `search_mode=academic` is a real distinction we already honour via `shodh`; `recency` +
  `last_updated` filters belong on every Hoola research input ("as of when?"); `search_context_size` is the honest
  knob for "read the page properly vs skim it".

## 8. Valyu — "paid datasets beside the web, with a price ceiling on the data itself"
`valyu 2.13.5` · `types/{answer,deepresearch,datasources}.py`, `deepresearch_client.py`

- **`answer`**: `query`, **`search_type: all|web|proprietary|news`**, **`data_max_price`** (a cap on what the DATA
  may cost for this one call), `included_sources` / `excluded_sources`, `start_date` / `end_date`, `country_code`,
  `fast_mode`, `structured_output`, `system_instructions`.
- **`datasources`**: a catalogue of licensed corpora, each with `category`, `topics`, `languages`, `modality`,
  `coverage(start_date, end_date)`, `update_frequency`, `size`, `response_schema` and **`pricing.cpm`** (cost per
  million tokens). **You can see what a source costs before you read it.**
- **`deepresearch.create`**: `mode` / `model` = **`instant | fast | standard | heavy | max`**, `strategy` /
  `research_strategy`, `report_format`, `output_formats` (`markdown`, `pdf`, …), `search` config, `urls`, `files`
  (attachments with `context`), `mcp_servers` (with `allowed_tools`), `previous_reports`, and
  **`deliverables`**: `csv | xlsx | pptx | docx | pdf` with `columns`, `include_headers`, `sheet_name`, `slides`,
  `template`.
- **`tools` with per-tool call budgets**, quoted: *"System defaults for max_calls: browser_use 5, screenshots 15,
  code_execution 10… max_calls can only be lowered, not raised."* Tools: `code_execution`, `screenshots`,
  `browser_use`, `charts`.
- Cost comes back split (`CostBreakdown`): `search_deduction_dollars`, `ai_deduction_dollars`,
  `contents_deduction_dollars`; extraction metadata counts `urls_requested / processed / failed`.
- **The technique in one line:** *research across the web AND licensed datasets whose per-million price you can see
  and cap, with per-tool call budgets, prior reports as context, and the output delivered as the actual file the
  user wanted.*
- **What Hoola takes:** **`data_max_price`** (our `mapsbill` pattern, proven elsewhere), **per-tool `max_calls`**
  (a research run must not be able to open 200 pages), `previous_reports` as context for a follow-up, and
  `deliverables` — the report as the file she asked for, which is Hoola's `doc_studio` job.

---

## 9. What they all agree on (and what only some do)

| Technique | OpenAI | Google | Anthropic | Parallel | Exa | Linkup | Perplexity | Valyu |
|---|---|---|---|---|---|---|---|---|
| Plan shown before the work | — | **yes** (`collaborative_planning`) | your loop | — | internal (`plan-output`) | — | — | `strategy` |
| Sub-question fan-out | model's own | steps | your loop | `search_queries[]` | **`tasks_instructions[]`** | internal | `query[]` | internal |
| Effort / cost tier | `reasoning.effort` | agent cfg | your loop | **processor** | 3 models | `reasoning_depth` S–XL | `reasoning_effort` | `instant`→`max` |
| Domain / date source policy | `allowed_domains` | — | allow+block | **`source_policy`** | — | **both + dates** | **domain+lang+recency** | sources + dates |
| Fetch-the-page step | via search | `url_context` | **`web_fetch`** | `fetch_policy` | **`crawl`** | `fetch` | `browser.sessions` | `urls` |
| Arithmetic in code | `code_interpreter` | `code_execution` | `code_execution` | — | — | — | — | `code_execution` |
| Citations typed | `url_citation` | url/file/place | on fetch | **per field + excerpts** | in content | inline | annotations | results |
| **Confidence per claim** | — | — | — | **yes** | — | — | — | — |
| Long run / resume | `background` | **`continuation_token`** | your loop | polled runs | polled 10 min | tasks | `async_` | polled |
| Context pruning for long runs | — | — | **`clear_tool_uses`** | — | — | — | — | — |
| Keeps watching the topic | — | — | — | **monitors** | websets monitors | — | — | alerts |
| Output as a FILE | — | — | — | — | — | — | — | **`deliverables`** |
| Cost itemised in the result | usage | usage | usage | — | **pages/searches/tokens** | quota | usage | **3-way split** |

**Unanimous:** a research answer is a *schema or a sourced answer*, never free prose; source policy (domains +
dates) is an input, not a prompt instruction; effort is a paid dial; long runs are submitted and polled, never held
open. **Only one vendor each** does: confidence per field (Parallel), server-side context pruning (Anthropic),
plan-then-approve as a flag (Google), itemised research cost (Exa), priced data sources with a cap (Valyu),
the deliverable file (Valyu), academic/SEC corpora as a mode (Perplexity).

**Hoola's advantage is the union**: nobody ships plan-approval + per-claim confidence + a priced cap + context
pruning + the finished document in one product. That union is the plan in `docs/RESEARCH_PRO_PLAN.md` §3.
