> Companion file: **`01_techniques.md`** — the exact research technique of each vendor, one by one, with the
> SDK file that proves each line.

> **CORRECTION 3 Nov 2026:** Exa's `/research/v1` listed below is RETIRED (its own SDK says so); its replacement is the Agent API (`POST /agent/runs`). See `01_techniques.md` s5.

# Deep-research APIs — what exists, read from the vendors' OWN shipped SDKs (3 Nov 2026)

**How this was read, and why it matters.** Every vendor's documentation host is BLOCKED from this sandbox
(`platform.openai.com`, `docs.anthropic.com`, `ai.google.dev`, `docs.perplexity.ai`, `docs.x.ai`, `docs.parallel.ai`,
`docs.exa.ai`, `docs.tavily.com`, `openrouter.ai` — all refused at the proxy). So nothing here comes from a blog or
from memory: each line was extracted from the vendor's **own current package on PyPI**, which is a primary artefact
the vendor publishes and versions. The package name + version is the citation. A web search was run too; its results
were third-party comparison blogs and are recorded at the bottom as **claims, not facts**.

## 1. The two vendors that ship a deep-research MODEL / AGENT

### OpenAI — `openai 3.42.1`
- Model ids in the Responses API: **`o3-deep-research`**, `o3-deep-research-2025-06-26`,
  **`o4-mini-deep-research`**, `o4-mini-deep-research-2025-06-26` (found in `types/responses/responses.py`).
- Tools the Responses API carries: `web_search` (+ `web_search_call` events), `code_interpreter`, `mcp`.
- `background` mode exists on Responses (a long run is started and polled, not held open).

### Google — `google-genai 2.34.0`
- A separate **Interactions API** with server-managed **agents** (`_is_agent_body`: "Whether the create body targets
  an agent (server-managed loop)"), `background`, streaming and continuation/timeout handling.
- **`DeepResearchAgentConfig`** exists (`_gaos/types/.../deepresearchagentconfig.py`), with:
  - **`collaborative_planning`** — *"Enables human-in-the-loop planning for the Deep Research agent. If set to true,
    the Deep Research agent will provide a research plan in its response. The agent will then proceed only if the…"*
    (quote truncated in the file; the shape is plan → approval → run). **This is Hoola's own plan-card pattern.**
  - `visualization`: `off` | `auto` ("Whether to include visualizations in the response").
  - thinking summaries.
- Deep-research model ids: **`deep-research-preview-04-2026`**, **`deep-research-max-preview-04-2026`**,
  `deep-research-pro-preview-12-2025`, and a bare `deep-research`.

### Anthropic — `anthropic 2.4.0` (what Hoola already runs on)
- **No deep-research model exists.** Anthropic's answer is tools + your own loop, and it ships:
  **`web_search`** with real citations (`citation_web_search_result_location`), **`web_fetch`**,
  **`code_execution`** (`code_execution_20250825`, `20260120`, `20260521`) and a **memory tool**
  (`memory_20250818`, plus memory stores / sessions) — the memory tool is the one piece Hoola does NOT use today
  and is the obvious fit for a long research run.
- Model ids include `claude-opus-5-5`, `claude-opus-5`, `claude-sonnet-5-5`, `claude-sonnet-5`, `claude-haiku-5-5`.

## 2. The research-first vendors (search + report as one call)

| Vendor | Package | What its own SDK exposes |
|---|---|---|
| **Parallel** (Hoola ALREADY pays them for `web_sources`) | `parallel-web 1.3.7` | `/v1/tasks/runs` + `/v1/tasks/groups` (long tasks), `/v1/search`, `/v1/extract`, `/v1/monitors`; processor names `lite` / `base` / `core` / `pro` / `ultra…` |
| **Exa** | `exa-py 2.27.0` | **`/research/v1`** with models **`exa-research-fast`**, **`exa-research`**, **`exa-research-pro`**; plus `answer`, `search_and_contents` |
| **Linkup** | `linkup-sdk 0.24.0` | **`/research`** (sync `research`, `async_research`, `list_research`, `get_research`), `/search`, `/fetch`, `/tasks` |
| **Perplexity** | `perplexityai 0.46.1` | `/chat/completions`, `/async/chat/completions`, `/search`; model strings in the SDK: `sonar-pro`, `sonar-reasoning` (**`sonar-deep-research` was NOT found in this package** — unverified whether the API still offers it) |
| **Valyu** | `valyu 2.13.5` | `answer` + a `deepresearch` module with research modes |

## 3. NOT VERIFIED — do not quote these from here
- **Every price.** No vendor's pricing page is reachable. A third-party blog quoted $10 / $40 per million tokens for
  `o3-deep-research` and $2 / $12 for a Gemini deep-research preview; both are **unconfirmed** and the wrong basis for
  a rupee cap.
- **Rate limits, region availability, and whether India is served.**
- **The terms** — in particular whether a provider's returned report may be stored and re-shared in her PDF, which is
  exactly the question that reshaped Google Maps Phase 7. Must be read before any provider is switched on.
- **Every benchmark claim.** The blogs cite DRACO 53.1 (Valyu) and SealQA-0 61% (Linkup) — each published by the
  vendor that wins it. Hoola's own scored card is the only number worth acting on.
- Whether `sonar-deep-research`, xAI's DeepSearch and Kimi / GLM research modes still exist as APIs.

## 4. What this means for Hoola (the judgement, not a fact)
Hoola already owns a research loop: the `research` signal (`agent/hard.py`), the DEEP RESEARCH recipe, a sub-agent
crew with its own research budget and a graceful wrap-up (`agent/team.py`), `web_sources` (Parallel) / `google_search`
/ `open_website`, the scholarly APIs in `app/shodh`, `pylab` for derived numbers, `research_check` (refuses a report
with no sources or an invented link) and `doc_studio` for the PDF. What it does NOT have is a **measured** answer to
"is the report any good", a **plan she approves before the money is spent**, and a long **background** run that
survives a restart. Buying one vendor's report does not give those three things — they are Hoola's side of the work.
