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

## 5. Hoola against all of this (CORRECTED 11 Nov: the first draft missed what is already built)

The owner's correction was right: Dify's "AI app for her customers" is **already in Hoola**, under a different name -
the **business AI Employee** (since v0.59) and the desks built on it. Checked in the code:

| Dify | Hoola (already built) | Where |
|---|---|---|
| Chat / agent app answering other people | Hoola answers customers **as the business's employee** on her own WhatsApp Business number (official Cloud API): only customer tools, always about that one customer, trust per duty, daily caps, her takeover, 24 h window, STOP respected, bookings, UPI link without moving money | `employee/inbox.py`, `employee/service.py` |
| The app's config (prompt, role, rules) | Employee profile: role (290 roles), preset (clinic / shop / ISP...), about, hours, after-hours, job sheet, her rules, duties, trust | `employee/models.py`, `employee/roles.py` |
| Knowledge-grounded answers + sources | Seva: answers ONLY from her Gyaan with source + confidence, clarify band, "unknown" never guessed -> handover; macros in 4 languages | `seva/service.py` (`answer`, `macros`) |
| Logs -> "correct this answer" | Every customer question logged masked; unanswered ones grouped as **gaps** with "Jawab do" | `seva/service.py` `gaps` |
| Annotation reply | Her approved answers served before retrieval (v0.521) | `gyaan/annotations.py` |
| Monitoring | Seva numbers: first response / resolution, % within SLA, deflection, CSAT, top questions, morning note | `seva/service.py` `report` |
| Human input that pauses | Refund / exception cards decided only by her tap (fingerprint for money) | `seva` exceptions, approval cards |
| Voice app | Call Centre: her phone line answered from her APPROVED, VERSIONED script (her tap makes a version live), AI disclosure first, hand-over, call notes | `callcentre/` |
| Agent-to-agent | Hoola Network: avatars talk to other businesses' avatars | `net/` |
| Workflow app | DHARA workflows + DSL (v0.502 / v0.521) | `dhara` |
| Data apps with AI around them | App Sahayak native apps + web apps, Pillars A-L, proof apps (v0.771) | `appmaker/` |

So Hoola is not missing the product. What Dify has that Hoola does NOT (checked, small list):

1. **Website visitors answered by AI.** The website live chat is owner-reply-only ON PURPOSE (`site/livesite.py`: "the
   agent never answers a customer on its own"); the WhatsApp employee does answer. A visitor-chat channel for the same
   employee + Seva would be a decision for her, not a missing engine.
2. **An embed bubble for a website Hoola did not build.**
3. **API keys / an MCP server for her employee**, so her own software can ask it (with per-minute / per-hour /
   concurrent limits).
4. **More than one AI app per business.** `EmployeeProfile` is keyed on the tenant - one employee per business
   (her internal AI Employees desks are separate). Dify lets one workspace run many apps.
5. **Versions + restore for the employee's config.** The call-centre script is versioned; the employee profile is not.
6. **One sentence -> a checked DHARA flow** (Dify's `workflow-generate`: plan -> parallel node builders -> tools she
   lacks refused before Apply). The naksha does this for data apps only.

## 6. Plan

No new product. If she wants any of the six above, each is a small addition to the existing employee / Seva / DHARA
code, and items 1 and 2 need her decision first (an AI answering her website visitors is a public change).
