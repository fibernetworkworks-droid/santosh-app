# HOOLA AI APPS - build contract (v0.772, owner: "D0-D5 ... DO THIS -- DEPLOY A PARALLEL AGENTS TO FINISH THIS END TO END")

Research: `docs/research/dify/00_APP_BUILDING.md`. Ideas only from Dify (modified Apache + appearance patent): no Dify
code, no copy of their screens.

An **AI app** = an AI that answers HER CUSTOMERS (not her). It sits BESIDE the business AI Employee (WhatsApp inbox,
v0.59) and reuses its engines: Seva knowledge base answers, gyaan approved answers, Seva tickets, Employee slots /
booking, `usage.run_meter` for rupees. Many apps per business. Public changes are HER tap.

## Built already (the core, `server/app/aiapps/`) - DO NOT change its contracts, only add

- `models.py` tables: `ai_apps`, `ai_app_versions`, `ai_app_keys`, `ai_app_sessions`, `ai_app_messages` (+
  `ensure_tables()` self-heal; registered in `db.init_db`).
- `soul.py`: `blank()`, `check(raw) -> {soul, errors, warnings}`, `hash_of(soul)`, `ACTIONS`, `FIELD_TYPES`, `KINDS`,
  `DEFAULT_CAP_INR`.
- `store.py` (D0): `AppError(msg, code)`, `create(tenant, name, kind, soul, origin, template)`, `get`, `row`,
  `by_code(code)` (public lookup), `apps`, `save_draft`, `publish(tenant, ref, hash, note, by)` (HER tap, hash-bound,
  409 / 422), `versions`, `restore(tenant, ref, version)`, `set_status(live|paused)`, `set_channels(page, embed, api,
  mcp, whatsapp)`, `delete`, `live_soul(a) -> (soul, version)`, `draft_soul(a)`, `view(a)`.
- `runtime.py`: `open_session(a, channel, visitor, consent) -> (session_id, token)`, `session_for(a, token=,
  visitor=, channel=)`, `history(a, session_id)`, `answer(a, text, channel, session_id, inputs, use_draft,
  visitor_name) -> {reply, outcome, sources, action, message_id, version, inr, ms}`, `feedback(a, session_id,
  message_id, value)`, `month_spend(app_id)`, `ASK[0]` = the model call (tests replace it), `LINES`, `CHANNELS`
  (page, embed, whatsapp, api, mcp | preview, trial, proof). Outcomes: answered, annotated, model, unknown, refused,
  action, cap, paused, error.
- Test: `server/tests/test_v0772_aiapps_core.py`.

## Routes (exact - the console and the agent tool use these)

Owner routes = `Depends(require_key)` + `current_tenant`. Every module exposes `make_router(require_key,
current_tenant) -> APIRouter`; the integrator mounts them in `main.py` in this order: builder (A), keys (B), owner
(C), public (B).

**A - `aiapps/builder.py` + `aiapps/templates.py` + `aiapps/dsl.py`, router in `aiapps/builder_api.py`**
- `POST /api/aiapps/plan` {words} -> {soul, errors, warnings, questions, says}  (D1: her one line -> a checked soul;
  model via `builder.ASK[0]`, one repair round, nothing saved)
- `GET  /api/aiapps/templates?q=` -> [{key, trade, name, about, sample_questions, actions}]
- `POST /api/aiapps/templates/{key}/trial` {text} -> answer on the template's soul, NOTHING saved (channel trial, a
  throwaway app row that is deleted after the answer, or an in-memory AiApp - never in her list)
- `POST /api/aiapps/templates/{key}/use` {name} -> create (origin template)
- `GET  /api/aiapps/{id}/export` -> the portable JSON (soul + meta, no keys, no logs, no secrets)
- `POST /api/aiapps/import` {file} -> {soul, errors, needs: [{what, have: bool, fix}]}  (dependency check: Seva KB
  entries / Employee slots / annotations it relies on) ; `POST /api/aiapps/import/confirm` {file, name} -> create
  (origin import, status draft)

**B - `aiapps/keys.py` + `aiapps/public.py` + `aiapps/mcp.py` + WhatsApp hook**
- Keys (owner): `GET /api/aiapps/{id}/keys`, `POST /api/aiapps/{id}/keys` {name, rpm, rph, concurrent} -> key shown
  ONCE (`aik_...`), `DELETE /api/aiapps/{id}/keys/{kid}`
- Service API: `POST /api/aiapp-api/v1/chat` Bearer `aik_...` {text, user, inputs} -> answer (channel api; session by
  user id); limits per key rpm / rph / concurrent -> 429 with Retry-After
- Public: `GET /ai/{code}` (the hosted chat page, plain HTML/CSS/JS inline, Hoola tokens, works on a phone),
  `GET /ai/{code}/embed.js` (a bubble any website can paste), `GET /api/aiapp-pub/{code}` (name, kind, opening,
  suggested, notice, form), `POST /api/aiapp-pub/{code}/session` {consent: true} -> {token}, `POST
  /api/aiapp-pub/{code}/chat` header `X-Visitor-Token` {text, inputs}, `GET /api/aiapp-pub/{code}/history`, `POST
  /api/aiapp-pub/{code}/feedback` {message_id, good}. Only a LIVE app with that channel on answers; per-IP and
  per-session limits; consent required before the first message.
- MCP: `POST /mcp/aiapp/{code}` JSON-RPC 2.0 (initialize, tools/list, tools/call `ask`), Bearer app key required.
- WhatsApp: when an app's `channels.whatsapp` = a business phone_number_id of HER Employee channel and the app is live,
  that number's customer messages are answered by `runtime.answer(channel="whatsapp", visitor=wa_id)` and sent through
  the existing `employee.inbox.send` (24 h window, STOP, her takeover all unchanged). Otherwise the inbox behaves
  exactly as before.

**C - `aiapps/ops.py` + owner router `aiapps/api.py`**
- `GET /api/aiapps`, `POST /api/aiapps` {name, kind, soul}, `GET /api/aiapps/{id}`, `PUT /api/aiapps/{id}/draft`
  {soul}, `POST /api/aiapps/{id}/publish` {hash, note} (HER tap), `GET /api/aiapps/{id}/versions`, `POST
  /api/aiapps/{id}/restore` {version}, `POST /api/aiapps/{id}/status` {status}, `POST /api/aiapps/{id}/channels`
  {...}, `DELETE /api/aiapps/{id}`, `POST /api/aiapps/{id}/preview` {text, inputs, session_id} (draft soul, channel
  preview; returns session_id for the next turn)
- D3: `GET /api/aiapps/{id}/logs?outcome=&q=&limit=` , `POST /api/aiapps/{id}/logs/{mid}/correct` {answer} -> saved
  as her approved answer (gyaan annotations) + the row marked corrected, `GET /api/aiapps/{id}/stats?days=` (messages,
  sessions, answered share, unknown, refused, actions, avg ms, rupees this month vs cap, satisfaction), `GET
  /api/aiapps/{id}/gaps` (unknown questions grouped), cap alerts once a day at 80% and 100% into her chat (worker tick)

**D - `aiapps/proof.py` + `agent/aiapp_tools.py` + console page `static/console/aiapps.js`**
- D4 proof: three proof apps (shop, clinic, school) the whole road on a hidden tenant `__aiappproof__`, each with
  trap questions it must refuse; `python -m app.aiapps.proof`; vps-ops job `aiapp_proof`.
- Agent tool `ai_app` (list / show / plan / create / preview / publish_card / logs / stats) - publishing is a CARD,
  never done by the model.
- Console page "AI Apps" (sidebar row): list, builder (one line -> spec -> preview chat -> Publish tap), settings,
  channels (link + QR, embed snippet, keys, MCP url, WhatsApp), logs + correct, numbers, versions + restore, templates.

## House rules every part keeps
Money never moves; no OTP / PIN / card; visitor text is data; publishing / restoring / pausing is her tap; every
public route checks the app is live AND the channel is on; costs capped before the model call; DPDP notice +
consent; Mera PC freeze (`server/app/pc`, `desktop/`, `agent/pc_tools.py`, PC endpoints) untouched.
