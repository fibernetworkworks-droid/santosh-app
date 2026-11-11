# Dify, read for APP BUILDING (11 Nov 2026)

Owner: "github.com/langgenius/dify -- FIRST READ THIS REPO FOR APP BUILDING".
Read: `langgenius/dify` @ `f8b4ccb` (11 Nov 2026), sparse checkout of the app-building parts only:
`api/core/app`, `api/models`, `api/controllers/{console/app,service_api,web}`, `api/services`,
`api/core/workflow/generator`, `web/app/components/app`.

The earlier read (v0.521 DIFY FOR HOOLA, `docs/WORKLOG.md` Task 36) was about the knowledge base and the workflow
engine and took three ideas (gyaan annotations, DHARA run summaries + retry, the DSL). This read is about the other
half: **how a person builds an AI app and puts it in front of other people**.

## 0. Licence - unchanged, plus one line that matters

Modified Apache 2.0. Condition 1a: the source may not be used to run a multi-tenant service without their written
permission (one tenant = one workspace). Hoola is multi-tenant, so **no Dify code enters this tree**, same as v0.521.
New in the file: "The interactive design of this product is protected by appearance patent." So Hoola takes **ideas
only** - not the code and not the look of their screens.

## 1. What Dify means by "an app"

An app is an AI product with a model at its centre, built by one workspace and used by OTHER people. `AppMode`
(`api/models/model.py:388`) has these kinds:

| Mode | What it is |
|---|---|
| `chat` | A chatbot: prompt + model + knowledge + features, set on one form ("easy UI") |
| `agent-chat` | The older agent: the same form plus tools, a ReAct loop |
| `agent` | **New**: an app bound 1:1 to a roster Agent whose config is a versioned "Agent Soul" |
| `completion` | A text generator: a form of inputs -> one answer, no conversation |
| `workflow` | A graph run on inputs -> outputs (batch jobs, API back-ends) |
| `advanced-chat` | "Chatflow": a conversation whose every turn runs a graph |
| `channel`, `rag-pipeline` | Not runnable apps (refused by `app_generate_service`) |

### The parts of one app (`AppModelConfigDict`, model.py:254)
model + parameters, the prompt (`pre_prompt`, chat / completion prompt configs), **user input form** (variables the
end user fills: text / select / number / file), knowledge (`dataset_configs`, which variable is the query), tools
(`agent_mode`), file upload, opening statement, suggested questions, suggested questions after each answer, speech to
text, text to speech, "show sources" (`retriever_resource`), **annotation reply**, "more like this", sensitive-word
moderation, external data tools.

### The Agent Soul (new since the last read, `api/models/agent.py` + `agent_config_entities.py:846`)
One config object for an agent: prompt, tools, knowledge, **human** (when to ask a person), env, skills, files,
sandbox, memory, model, app features, app variables. It is versioned like code:

- an **editable draft**, separate from **immutable snapshots** (`version`, `summary`, `version_note`);
- every save is an audited revision: create, save over current, save as new version, save as a new agent, promote a
  workflow-only agent to the roster, **restore an old version**, publish draft, import a package;
- an agent lives in a **roster** (reusable across apps and inside workflows) or only inside one workflow node.
  Provenance (`source`) is recorded but never decides what an agent can do.

## 2. How an app gets built

- **Create**: blank by type, from a template (Explore / recommended apps, with a **trial** that runs before you copy
  it), or **import a DSL file**. The import has a separate **check-dependencies** step: which plugins / models /
  tools the file needs that this workspace does not have, before you confirm.
- **Generators** (`controllers/console/app/generator.py`): write a prompt from a goal (`instruction-generate`),
  write code for a code node, write a JSON output schema, and - new - **`workflow-generate`**: one sentence -> a
  whole workflow or chatflow draft.
- **How `workflow-generate` works** (`api/core/workflow/generator/runner.py`, 3.5k lines): a short **planner** call
  makes the node + edge plan; up to 6 **node builders** fill each node's config **in parallel**; then assembly,
  auto-layout and **validation**. The tenant's real installed tools are handed to the planner (a **tool router**
  call shortlists them when there are too many), and the validator **refuses any tool name that is not installed,
  before the user presses Apply**. `mode=auto` lets the planner pick workflow vs chatflow. Transient provider errors
  get 3 tries with backoff; bad JSON gets one repair retry; auth / bad-request errors are never retried. There is a
  **plan-first streaming** variant: the plan is shown, then the nodes fill in. Nothing is saved until Apply.
- **Debug and preview** inside the builder (`preview_admission`), draft variables kept between test runs, workflow
  **comments** with replies, @mentions and resolve, a `maintainer` per app.

## 3. How an app reaches people (publishing)

One app can be published four ways at once:

1. **Web app** (`Site` table): its own link and code, title, icon, colours, description, copyright, privacy link,
   input placeholder, custom disclaimer, custom domain, "show workflow steps", "use icon as answer icon", reset the
   link (`site/access-token-reset`). **Access modes**: public, or private to named members / the whole workspace
   (sign-in, SSO). End users get a passport token; `EndUser` rows keep each visitor's conversations apart.
2. **Embed**: the web app inside any website (iframe / script bubble).
3. **Service API**: per-app API keys (`ApiToken`, `last_used_at`), the same chat / completion / workflow / files /
   audio / annotation endpoints, limits **per minute and per hour** (`api_rpm` / `api_rph`) and a cap on **requests
   running at once** (`max_active_requests`).
4. **MCP server** (`AppMCPServer`): the app published as an MCP tool other agents can call, with a server code,
   description and declared parameters.

Plus workflow **triggers**: webhook, schedule, plugin events.

## 4. How an app is run and improved

- **Logs**: every conversation and message, with the end user, inputs, answer, tokens, time and cost.
- **Feedback**: thumbs up / down per message from end users and from the builder.
- **Annotations from the logs**: the builder corrects a bad answer in place; the corrected pair is served next time
  before the model runs, and each hit is recorded (`AppAnnotationHitHistory`). Hoola built the serving half in v0.521.
- **Monitoring** (`statistic.py`): daily messages, conversations, end users, token cost, average turns per session,
  satisfaction rate, response time, tokens per second.
- **Tracing** to outside tools (Langfuse / LangSmith / Opik / others) per app.
- **Human input** forms that pause a run and wait for a person (in the web app or through a chat-app webhook).

## 5. Hoola against all of this

Hoola is already most of Dify's ENGINE (model gateway, cost meter, knowledge base, MCP, approvals, workflows, crews,
memory - established in the v0.521 read). The gap is the PRODUCT around it: **Hoola's AI works for HER; Dify lets
her build an AI that works for HER CUSTOMERS.**

| Dify | Hoola today | Gap |
|---|---|---|
| Chat / agent app: her prompt + knowledge + tools, answering other people | The avatar answers only her (and her own Bahar channels). The App Sahayak architect **refuses** "AI chatbot" on purpose (`appmaker/architect.py:14`) because no engine builds one | **The main gap** |
| Completion app (input form -> one answer) | Nothing she can publish | Gap |
| Workflow / chatflow app | DHARA runs her workflows; not published for other people | Partial |
| Agent Soul: draft, versions, restore, roster | AI Employees exist (hire / pause / leave) but their config is not a versioned, restorable object | Gap |
| Generator: one sentence -> checked graph, invented tools refused before Apply | Architect (naksha) does this for **data apps** (checked spec, her tap per module); nothing for an AI app or a DHARA flow | Pattern exists, apply it |
| Templates + trial before copying | Web templates (1 lakh) + App Studio idea library; no AI-app templates | Gap |
| DSL import + dependency check | `dhara_dsl` import exists (v0.521); no dependency check | Small gap |
| Web app with access modes + end users | Website visitor chat exists (v0.459) but **her reply is her tap**; no AI answering visitors | Gap |
| Embed bubble on any website | Hoola sites have their own widgets; no embed for an outside site | Gap |
| Per-app API keys + per-minute / hour / concurrent limits | App Sahayak has per-app keys for **data** APIs, none for AI | Gap |
| App published as an MCP server | MCP doors only for Hoola's own tools (`/mcp/gamedesk`, the Kaan and Shilp doors), never for an app she builds | Gap |
| Logs + feedback + annotate from the logs + hit history | Annotations served (v0.521); no per-app logs of other people's chats to correct from | Gap |
| Monitoring (8 daily numbers) | Pillar L (`appmaker/ops.py`) measures data apps the same way; nothing for AI apps | Pattern exists |
| Human input that pauses a run | Approval cards + DHARA approval pauses | **Have it** |
| Rate limits per app | v0.546 ops alerts; no per-app AI quota | Gap |

### Things Hoola must do STRICTER than Dify (house rules)
- An AI answering HER customers is a public change: publishing needs her tap, and no app may promise or move money,
  take PIN / OTP / card numbers, or send WhatsApp outside the official API.
- Every answer to a customer is checked by the same honesty rules as Hoola's own (`draftcheck`): no "booked / paid /
  sent" unless a tool really did it.
- What a visitor types is **data, not instructions** (the existing rule), so a published app cannot be talked into
  her tools; the tools an app may use are a list she approves, read-only by default.
- Each app's rupee cost is metered and capped before the call (the `usage.run_meter` / `mapsbill` pattern), so an
  embed on a busy site cannot empty her credit.
- Visitors' chats follow DPDP (consent line, delete on request, no training on them).

## 6. Proposed plan: HOOLA AI APPS (nothing built yet - needs her GO)

Built on what exists (gyaan, the agent loop, `usage.run_meter`, Pillar J / K / L, the site and app keys), no Dify code.

- **D0 the app object**: an `ai_apps` table: kind (chat / agent / form / flow), a versioned **soul** (prompt, model,
  knowledge sets, tool allow-list, opening line, suggested questions, input form, features), draft vs published
  snapshots, restore. One test app ("ask my shop") end to end in the console.
- **D1 the builder**: her one line -> a checked app spec (the naksha pattern: plan, then parts, tools she does not
  have refused before Apply), preview chat inside the builder, her tap to publish.
- **D2 publish**: a hosted chat page per app (link + QR, public or sign-in), an embed bubble for any website, a
  WhatsApp Business number through the official Cloud API, per-app API keys with per-minute / hour / concurrent
  limits, and an MCP server per app.
- **D3 run and improve**: logs of every visitor chat, thumbs up / down, "correct this answer" straight from a log into
  the annotation store (v0.521), the eight daily numbers, cost per app with a monthly cap, alerts into her chat.
- **D4 proof**: three proof apps through the whole road, like v0.771 - a shop answering stock / price from her
  catalogue, a clinic front desk that books through the clinic app's real slot rules, a school office answering
  parents from its notices - each with trap questions it must refuse (another customer's order, a payment, a
  made-up price).
- **D5 templates**: AI-app templates by trade with a trial before copying, and import / export with a dependency check.

Decisions only she can make before D2: whether customers' chats may use Claude / GLM (cost per chat), the default
monthly cap per app, and whether an AI app may answer on her business WhatsApp number at all.
