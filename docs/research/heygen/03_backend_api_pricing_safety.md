# HeyGen backend surface — as read on 11 Nov 2026

**Method.** Most of this comes from HeyGen's own machine-readable sources, downloaded and parsed directly: the v3 OpenAPI spec (`https://developers.heygen.com/openapi/external-api.json`, 1.9 MB), the docs index (`https://developers.heygen.com/llms.txt`), ~45 guide pages as `.md`, and the LiveAvatar OpenAPI (`https://docs.liveavatar.com/openapi.json`) plus its docs. Tags: **[C]** = confirmed from an official HeyGen source, **[R]** = third-party report.

**Three things that change the plan before anything else:**
- **v1/v2 are dead.** `docs.heygen.com` now redirects to `developers.heygen.com`. v1/v2 "reached end of support" on **31 Oct 2026** and are being removed; v3 is the only supported API. `/v2/video/generate`, `video_inputs[]`, `/v2/photo_avatar/*`, `/v1/webhook/endpoint.*` and `/v2/template/{id}/generate` are all legacy. [C] https://developers.heygen.com/endpoint-version-comparison.md
- **Interactive Avatar / Streaming API is gone.** It was replaced by a separate product, **LiveAvatar** (own domain, API, key and credits). The old `streaming.*` pages now 404.
- **API pricing is no longer public.** The per-operation rate card sits behind login at `platform.heygen.com/pricing`. Every per-unit API rate below is therefore [R] or inferred.

---

## 1. API reference (v3)

**Basics [C]**
- Base URL `https://api.heygen.com`. Auth header `X-Api-Key` (spec also declares OAuth2 Bearer, used by MCP and CLI `--oauth`).
- An API key bills to the API wallet; OAuth bills to the user's web-plan credits.
- `Idempotency-Key` header is supported on writes.
- Lists use cursor pagination (`limit`, `next_token`/`token`, `has_more`).
- Every file input is a discriminated union: `{type:"url",url}` | `{type:"asset_id",asset_id}` | `{type:"base64",media_type,data}`.
- API keys carry scopes; `scope_mode` is `full` | `read_only` | `custom`. Scopes are `<area>:read|write` for: account, ai_clipping, assets, avatars, brand, filler_removal, hyperframes, images, lipsync, resource, templates, translations, video_agent, videos, voices, webhooks. https://developers.heygen.com/docs/api-key-permissions.md
- HeyGen now splits the surface into a **Model API** (`/v3/models/*`: raw prompt/photo/audio in, nothing pre-created) and an **Application API** (works on avatars, voices, templates, brand kits by ID).

**All endpoints, from the OpenAPI spec [C]**

*Videos*
- `POST /v3/videos` create · `GET /v3/videos` list · `GET /v3/videos/{video_id}` get/status · `POST /v3/videos/{video_id}` edit · `DELETE /v3/videos/{video_id}`
- `GET /v3/videos/{video_id}/scenes` · `POST /v3/videos/{video_id}/deliveries` (redeliver files)
- Batches: `POST /v3/videos/batches` (≤100 items) · `GET /v3/videos/batches/{batch_id}` · `GET /v3/videos/statuses` (bulk)
- Legacy, still in spec: `POST/GET /v2/videos`, `GET/DELETE /v2/videos/{video_id}`

*`POST /v3/videos` body*
- `type*`: `avatar` | `image` | `cinematic_avatar` | `studio` (multi-scene).
- Avatar variant: `avatar_id*`, `script` + `voice_id` **or** `audio_url` / `audio_asset_id`.
- `voice_settings{speed,pitch,volume,locale,engine_settings}`.
- `engine` = Avatar III / IV / V config (`type`; V adds `reference_look_id`, `more_blinking`); `motion_prompt`; `expressiveness` high|medium|low.
- Output: `resolution` 720p|1080p|4k; `aspect_ratio` 16:9|9:16|4:5|5:4|1:1|auto; `fit` contain|cover; `output_format` mp4|webm.
- `background{type,value|url|asset_id}`, `remove_background`.
- `caption{file_format,style}`, `watermark{image,scale,opacity,placement}`.
- `output_upload{video,captions,thumbnail}` (push to your own storage).
- `title`, `folder_id`, `brand_glossary_id`, `callback_url`, `callback_id`.
- Response: `{video_id, status, output_format}`.

*Model API*
- `POST /v3/models/videos` (HeyGen Video, `heygen-video-1`; text/image/reference to 5–30 s clips with audio) · `GET /v3/models/videos/{video_id}`
- `POST /v3/models/avatars` (Avatar 6: photo/video + audio → talking video, 1080p/2K)
- `POST /v3/models/images` · `GET /v3/models/images/{generation_id}`
- Voice: `POST /v3/models/audio/tts` · `POST /v3/models/audio/tts/stream` · `POST /v3/models/audio/tts/stream-input/tokens` (WebSocket input streaming) · `POST /v3/models/audio/sts` (speech-to-speech)
- Voices: `POST /v3/models/audio/voices` (create/retrain; `mode` instant or professional) · `GET /v3/models/audio/voices` · `GET/DELETE /v3/models/audio/voices/{voice_id}`
- `POST /v3/models/audio/transcriptions`
- Also `POST /v3/images` · `GET /v3/images/{id}` · `POST /v3/video-generations` · `GET /v3/video-generations/{id}`

*Avatars*
- `POST /v3/avatars` (one endpoint; `type` = `digital_twin` | `photo` | `prompt`) · `GET /v3/avatars` (groups) · `GET/PATCH/DELETE /v3/avatars/{group_id}`
- `POST /v3/avatars/{group_id}/consent`
- `GET/POST /v3/avatars/looks` · `GET/PATCH/DELETE /v3/avatars/looks/{look_id}` · `GET /v3/avatars/look-templates`

*Voices (deprecated v3 paths, replaced by `/v3/models/audio/*`)*
- `POST /v3/voices/speech` · `POST /v3/voices` (design) · `GET /v3/voices` · `POST /v3/voices/clone` · `GET/DELETE /v3/voices/{voice_id}`
- Legacy: `POST /v1/audio/text_to_speech`, `GET /v1/audio/voices`

*Audio utilities*
- `GET /v3/audio/sounds` (music/SFX search) · `POST /v3/audio/music` · `GET /v3/audio/music/{id}`
- `POST /v3/audio/transcriptions` · `GET /v3/audio/transcriptions/{id}`
- `POST /v3/audio/analysis` · `POST /v3/audio/stems` · `GET /v3/audio/stems/{id}`

*Templates*
- `GET /v3/templates` · `POST /v3/templates` (create from a video) · `GET/PATCH/DELETE /v3/templates/{template_id}`
- `POST /v3/templates/{template_id}` (generate) · `PUT /v3/templates/{template_id}/variables`
- Generate body: `variables*`, `title`, `caption`, `subtitles`, `dimension`, `fps`, `scene_ids`, `brand_voice_id`, `brand_glossary_id`, `folder_id`, `include_gif`, `enable_sharing`, `callback_url`, `callback_id`.

*Video translation*
- `POST /v3/video-translations` · `GET` list · `GET/PATCH/DELETE /v3/video-translations/{id}` · `GET /v3/video-translations/languages` (175+)
- Proofread: `POST/GET /v3/video-translations/proofreads` · `GET/DELETE …/{proofread_id}` · `GET/PUT …/{id}/srt` · `POST …/{id}/generate`
- Batches: `POST /v3/video-translations/batches` · `GET …/batches/{id}` · `GET /v3/video-translations/statuses`
- Body: `video*`, `output_languages*[]`, `mode` (`speed` default | `precision`), `input_language`, `translate_audio_only`, `speaker_num`, `enable_caption`, `enable_dynamic_duration`, `disable_music_track`, `enable_speech_enhancement`, `enable_watermark`, `start_time`/`end_time`, `brand_voice_id`, `brand_glossary_id`, `stock_voice_config`, `srt`, `output_uploads`, `folder_id`, callbacks.
- Legacy: `POST /v2/video_translate`, `GET /v2/video_translate/target_languages`, `GET /v2/video_translate/caption`.

*Lipsync*
- `POST/GET /v3/lipsyncs` · `GET/PATCH/DELETE /v3/lipsyncs/{id}` · `POST /v3/lipsyncs/batches` · `GET …/batches/{id}` · `GET /v3/lipsyncs/statuses`

*Video Agent (prompt to video)*
- `POST /v3/video-agents` · `GET /v3/video-agents` · `GET /v3/video-agents/styles`
- `GET /v3/video-agents/{session_id}` · `POST /v3/video-agents/{session_id}` (send message) · `GET …/resources/{resource_id}` · `GET …/videos` · `POST …/stop`
- Legacy `POST /v1/video_agent/generate`

*Custom Agents*
- `GET /v3/custom-agents` · `GET /v3/custom-agents/{agent_id}` · `POST /v3/custom-agents/{agent_id}/videos` · `GET /v3/custom-agents/videos/{video_id}` · `POST /v3/custom-agents/videos/{video_id}/edits`

*Brand*
- Kits: `POST/GET /v3/brand-kits` · `GET/PATCH/DELETE /v3/brand-kits/{id}`
- Glossaries (pronunciations, do-not-translate, forced translations; replaces v1 "brand voice"): `POST/GET /v3/brand-glossaries` · `GET/PATCH/DELETE /v3/brand-glossaries/{id}`

*Assets*
- `POST /v3/assets` (multipart) · `GET /v3/assets` · `GET/DELETE /v3/assets/{id}` · `GET /v3/assets/search` (stock images/icons)
- Direct to S3: `POST /v3/assets/direct-uploads` · `POST /v3/assets/{id}/complete` · `POST/GET/DELETE /v3/assets/{id}/parts`
- Batches: `POST /v3/assets/direct-uploads/batches` · `POST /v3/assets/complete/batches` · `GET /v3/assets/batches/{id}` · `GET /v3/assets/statuses`

*Folders*
- `POST /v3/folders` · `GET /v3/folders/{folder_id}`

*Webhooks*
- `GET /v3/webhooks/event-types` · `GET/POST /v3/webhooks/endpoints` · `PATCH/DELETE /v3/webhooks/endpoints/{id}` · `POST …/{id}/rotate-secret` · `GET /v3/webhooks/events`

*Account and usage*
- `GET /v3/users/me` (`billing_type` = `wallet` | `subscription` | `usage_based`) · `GET /v3/api_keys/self` · `GET /v3/requests` (request log, ≤90 days) · `GET /v3/usage` · legacy `GET /v1/user/me`

*Other job families*
- HyperFrames (HTML/CSS/JS → video): `POST/GET /v3/hyperframes/renders` · `GET/DELETE …/{render_id}`
- Background removal: `POST/GET /v3/background-removals` · `GET/DELETE …/{job_id}`
- AI Clipping: `POST/GET /v3/ai-clipping` · `GET/DELETE …/{job_id}`
- Filler-word removal: `POST /v3/filler-word-removals` · `GET …/{id}`
- Video analysis: `POST /v3/video-analyses` · `GET …/{id}`
- Video quality comparison: `POST /v3/video-quality/comparisons` · `GET …/{id}` · `POST …/batches` · `GET …/batches/{id}`
- Podcasts: `POST/GET /v3/podcasts` · `GET/DELETE /v3/podcasts/{id}`
- Durable Workflows: `POST/GET /v3/workflows` · `GET/PATCH /v3/workflows/{id}` · `POST/GET …/versions` · `GET …/versions/{n}` · `GET /v3/workflows/node-types` · `POST/GET /v3/workflow-runs` · `GET …/{run_id}` · `POST …/{run_id}/cancel` · `GET …/{run_id}/nodes`
- Legacy workflows: `POST /v1/workflows/executions`, `POST /v1/workflows/graph-executions`, `GET /v1/workflows/executions/{id}`, `GET /v1/workflows`

**Personalised video:** there is no dedicated v3 endpoint group. It survives only as the webhook event `personalized_video` and the `entity_id` scoping on webhook endpoints.

**Rate limits [C]** https://developers.heygen.com/docs/usage-limits.md

| Type | Pay-as-you-go / subscription | Enterprise |
|---|---|---|
| Read | 300/min | 1,000/min |
| Write (e.g. `POST /v3/videos`) | 10/s | 30/s |
| Heavy (`POST /v3/assets`) | 30/min | 120/min |
| Status polling | 500/min (600/min per IP) | 1,500/min (1,800/min per IP) |

- Fixed on every plan: the four batch-create endpoints 30/min; HyperFrames renders 5/s; TTS, TTS stream and STS 30/min; HeyGen Image 30 creates/min.
- Limits are per user and per path; a path with an ID is counted per ID.
- A 429 carries `Retry-After`, `X-RateLimit-Limit/Remaining/Reset/Scope`.
- Concurrency: pay-as-you-go 10 concurrent workflows; Enterprise 20, with opt-in burst of +5 to +50 per workflow type billed at 1.5×. https://developers.heygen.com/docs/burst.md

**Error codes [C]** (~110 named codes) https://developers.heygen.com/docs/error-codes.md
- 401: `unauthorized`, `api_key_owner_workspace_access_revoked`
- 402: `insufficient_credit`, `usage_limit_reached`, `trial_limit_exceeded`, `subscription_required`, `plan_upgrade_required`
- 403: `forbidden`, `insufficient_api_key_scope`, `resource_access_denied`, `brand_kit_locked`, `voice_clone_terms_violation`, `phone_verification_required`, `ai_vendor_access_restricted`, `byok_not_supported`, `api_endpoint_disabled`, plus an `encryption_*` family (customer-managed keys)
- 404: `video_/avatar_/voice_/template_/asset_/webhook_/batch_not_found`
- 410: `endpoint_retired`
- 429: `rate_limit_exceeded`, `quota_exceeded`
- 400: `invalid_parameter`, `content_policy_violation`, `avatar_consent_required`, `avatar_expired`, `voice_expired`, `resource_limit_reached`, `resolution_not_allowed`, `script_too_short`, `video_too_long`, `download_failed`, `batch_too_large`, `youtube_video_download_forbidden`
- 409: `conflict`, `request_in_progress`, `resource_not_ready`, `voice_not_ready`, `stale_edit_version`
- 422: `image_processing_failed`, `graph_invalid`, `realistic_human_reference_not_allowed`
- 5xx: `internal_error`, `voice_provider_error`, `bad_gateway`, `gateway_timeout`, `service_unavailable`, `render_not_started`

---

## 2. Streaming / live

**Legacy Interactive Avatar (Streaming API) — retired**
- Sunset stated as 31 Mar 2026 on HeyGen pages (via search snippets; the pages themselves now 404). [C, date not re-read]
- It had `POST /v1/streaming.new`, `.start`, `.task` (`task_type` `talk` = through LLM, `repeat` = say verbatim), `.stop`, `.interrupt`, `.list`, `.create_token`, `streaming/avatar.list`, an `activity_idle_timeout` parameter and a knowledge base. SDK was `@heygen/streaming-avatar`, transport LiveKit v2. [R, from search snippets of now-removed pages]

**LiveAvatar — current [C]** https://docs.liveavatar.com
- Base `https://api.liveavatar.com`. Backend calls use `X-API-KEY`; session-scoped calls use a Bearer JWT session token.
- Transport: a LiveKit (WebRTC) room; `sessions/start` returns `livekit_url`, `livekit_client_token`, `livekit_agent_token` and a `ws_url`.
- **FULL mode** (2 credits/min; Embed is the same rate): LiveAvatar runs VAD, STT, LLM and TTS. The room has three participants (user, managed agent, avatar).
  - `interactivity_type`: `CONVERSATIONAL` | `PUSH_TO_TALK`.
  - STT providers: deepgram, assembly_ai, gladia, elevenlabs.
  - Managed LLM: OpenAI only (gpt-4o, gpt-4o-mini, gpt-5-nano, gpt-5.4-nano as default); custom LLM via `llm-configurations`.
  - TTS providers: ElevenLabs, Fish Audio, Cartesia (bring your own key through Secrets).
  - "Knowledge base" is now a **Context**: prompt, opening text, links, `${var}` dynamic variables (≤50). With no context the avatar is in restricted mode and can only repeat.
  - Session memory via `/v1/memory`.
- **LITE mode** (1 credit/min): you bring STT/LLM/TTS and send PCM 16-bit 24 kHz base64 audio over the WebSocket (≤1 MB per packet).
  - Plugins: LiveKit, Pipecat, Agora, VisionAgents.
  - Connectors: ElevenLabs Agent, Cartesia Agent, OpenAI Realtime / GPT-Live, Gemini Live.
- **Endpoints**
  - Sessions: `POST /v1/sessions/token`, `/start`, `/stop`, `/keep-alive`; `GET /v1/sessions`, `GET /v1/sessions/{id}`, `GET …/transcript`, `DELETE …/events`
  - Avatars: `GET /v1/avatars`, `GET /v1/avatars/public`, `GET/PATCH/DELETE /v1/avatars/{id}`, `POST /v1-alpha/avatars/image`
  - Voice agents: `GET /v1/voice_agents`, `GET/DELETE …/{id}`
  - Voices: `GET /v1/voices`, `POST /v1/voices/third_party`, `GET/PATCH/DELETE …/{id}`, `GET …/{id}/preview`
  - Contexts: `POST/GET /v1/contexts`, `GET/PATCH/DELETE …/{id}`, `POST …/{id}/copy`
  - Memory: `POST/GET /v1/memory`, `GET/DELETE …/{id}`
  - Secrets: `GET/POST /v1/secrets`, `DELETE …/{id}`
  - LLM: `GET/POST /v1/llm-configurations`, `GET/PATCH/DELETE …/{id}`, `GET /v1/llm-models`
  - Other: `GET /v1/languages`, `GET /v1/users/credits`, `POST /v2/embeddings` (iframe embed URL)
- **FULL token body:** `mode`, `avatar_id`, `is_sandbox`, `video_settings{quality, encoding}`, `max_session_duration`, `voice_agent` (or deprecated inline `avatar_persona{voice_id, context_id, language, voice_settings, stt_config, llm_settings}`), `interactivity_type`, `llm_configuration_id`, `dynamic_variables`, `memory`.
  - Quality: `very_high` 1080p, `high` 720p (default), `medium` 480p, `low` 360p. Encoding H264 (VP8 deprecated).
- **Data-channel events (FULL)**
  - Send on `agent-control`: `avatar.interrupt`, `avatar.speak_text`, `avatar.speak_response`, `avatar.start_listening`, `avatar.stop_listening`, `user.start_push_to_talk`, `user.stop_push_to_talk`.
  - Receive on `agent-response`: `user.speak_started/ended`, `avatar.speak_started/ended`, `user.transcription`, `avatar.transcription`, the four PTT acks, `session.stopped{end_reason}`.
  - End reasons: USER_DISCONNECTED, USER_CLOSED, IDLE_TIMEOUT, MAX_DURATION_REACHED, AGENT_HANG_UP, AVATAR_DELETED, NO_CREDITS, SERVER_ERROR, ZOMBIE_SESSION_REAP, DISPATCH_FAILED, UNKNOWN.
- Keep-alive: the SDK's `autoKeepAlive` pings every 60 s.
- Sandbox: `is_sandbox:true` is free and sessions end after ~1 minute.
- Rate limits: 10 req/s per API key; 5 req/s per session token on start/stop/keep-alive.
- Custom avatars: video (2 min footage plus a consent recording; auto voice clone) or image (alpha; 16:9 or 9:16, short side ≥1080 px). Each needs a purchased avatar slot; 1080p training needs Business or Enterprise.

**LiveAvatar pricing [C]**
- Docs table: Free $0 / 10 credits; Essential $99 / 1,100 credits, overage $0.095/credit; Business $475 / 6,000 credits, overage $0.09/credit. https://docs.liveavatar.com/docs/faq/credits.md
- Help article: Essential max session 20 min, 720p custom avatars; Business max session 60 min, 1080p. Concurrency is listed as "Unlimited" on both. One credit ≈ 10 US cents, i.e. FULL ≈ $0.20/min and LITE ≈ $0.10/min. https://help.heygen.com/en/articles/12758516-introducing-liveavatar
- Search snippets of other help articles gave conflicting figures ($19 tier, 5 or 20 concurrent). I did not confirm those.

**How LiveAvatar differs from Interactive Avatar [C]:** separate platform and credit system; avatars are not cross-compatible; old avatar slots do not migrate; it adds LITE mode, plugins/connectors, contexts, memory, secrets (BYOK), embeds and transcripts; a session is not metered during frontend setup.

---

## 3. Webhook events [C]

https://developers.heygen.com/docs/webhook-events.md · https://developers.heygen.com/docs/webhooks.md

- **Event types:** `avatar_video.success|fail`, `avatar_video_gif.success|fail`, `avatar_video_caption.success|fail`, `video_translate.success|fail`, `video_translate.preflight.validation_failed`, `video_translate.preflight.download_failed`, `video_agent.success|fail`, `personalized_video`, `instant_avatar.success|fail` (digital twins), `photo_avatar_generation.success|fail`, `photo_avatar_train.success|fail`, `photo_avatar_add_motion.success|fail`, `proofread_creation.success|fail`, `live_avatar.success|fail`, `hyperframes_video.success|fail`, `ai_clipping.success|fail`, `filler_word_removal.success|fail`, `batch.finished`.
- **Envelope:** `event_id`, `event_type`, `event_data`, `created_at` (ISO 8601).
- **`avatar_video.success` data:** `video_id`, `url` (pre-signed, expires), `gif_download_url`, `video_page_url`, `video_share_page_url`, `folder_id`, `callback_id`. For other events, treat the webhook as a signal and fetch the resource.
- **Create:** `{url (public HTTPS), events[] | null = all, entity_id}` returns `endpoint_id` and a `secret` shown once.
- **Signing:** header `signature` = hex HMAC-SHA256 of the raw body using the endpoint secret. Rotation invalidates the old secret immediately.
- **Delivery:** respond 2xx within 10 s; retries with exponential backoff for up to 24 h; duplicates are possible, so de-duplicate on `video_id` + `event_type` or `callback_id`.
- **Alternative:** a per-request `callback_url` + `callback_id`.
- There is **no webhook for consent**; poll `consent_status`.

---

## 4. SDKs, CLI, MCP, integrations

- **CLI `heygen` [C]:** command groups ai-clipping, asset, audio, avatar, background-removal, brand, filler-word-removal, folder, lipsync, model, template, user, video, video-agent, video-translate. https://developers.heygen.com/commands.md
- **Agent skills [C]:** `heygen-com/skills` (heygen-video, heygen-avatar, heygen-translate) and `heygen-com/liveavatar-agent-skills`.
- **MCP [C]:** remote server `https://mcp.heygen.com/mcp/v1/`, OAuth, billed to web-plan credits. https://developers.heygen.com/mcp/overview.md
  - Video Agent: list_video_agent_sessions, create_video_agent, list_video_agent_styles, get_video_agent_session, send_video_agent_message, get_video_agent_resource, stop_video_agent_session, list_video_agent_session_videos
  - Videos: list_videos, create_video_from_avatar, create_video_from_cinematic_avatar, create_video_from_image, create_video_from_studio, get_video, delete_video, get_video_scenes
  - Templates: list_templates, create_template, get_template, generate_from_template, update_template, delete_template, set_template_variables
  - Audio: search_audio_sounds
  - Translation: list/create/get/update/delete_video_translation, list_video_translation_languages
  - AI clipping: list/create/get/delete_ai_clipping
  - Batches: create_video_batch, get_video_batch, bulk_video_statuses; the same three for video_translation and lipsync; create_asset_upload_batch, complete_asset_batch, get_asset_batch, bulk_asset_statuses
  - User: get_current_user
  - Avatars: list_avatar_groups, create_digital_twin, create_photo_avatar, create_prompt_avatar, list_look_templates, list_avatar_looks, create_look_pack_looks, create_template_looks, get/update/delete_avatar_look, get/update/delete_avatar_group, create_avatar_consent
  - Assets and folders: create_asset_upload, get_asset, delete_asset, complete_asset_upload, create_folder, get_folder
  - Lipsync: list/create/get/update/delete_lipsync
  - Brand: list/create/get/update/delete for both brand_glossary and brand_kit
  - Models: convert_speech, create_speech, list_voices, design_voice, clone_voice, create_professional_voice, get_voice, delete_voice, create_look_remix, get_look_remix, image_to_video, reference_to_video, text_to_video, get_model_video
  - Other: create_filler_word_removal, get_filler_word_removal
  - Per-host guides exist for Claude Code, Claude Web, Codex, Cursor, Gemini CLI, Grok, Lovable, Manus, ChatGPT (plugin) and Superhuman.
- **LiveAvatar SDK [C]:** `@heygen/liveavatar-web-sdk` (github.com/heygen-com/liveavatar-web-sdk; v0.0.19 as of Sep 2026). The old `@heygen/streaming-avatar`, StreamingAvatarSDK and InteractiveAvatarNextJSDemo are legacy; I did not open those repos.
- **Slack app [C]:** generate from Slack; 50 creations/min and 500/hour per workspace. https://developers.heygen.com/docs/slack.md
- **Stripe Projects [C]:** an agent-provisioned API wallet. https://developers.heygen.com/docs/stripe-projects.md
- **Zapier [C]:** https://www.heygen.com/integrations/zapier
  - Triggers: Avatar video success, New video event, Video translation success.
  - Actions: Create video from template, Translate a video, Retrieve shareable link, Create WebM avatar video, Upload an asset.
  - A third-party guide claims "6 triggers, 32 actions", which conflicts. [R]
- **Make [R]:** a render-finished trigger, a "Create avatar video" action and a translate module.
- **HubSpot [R]:** Marketplace app adding the workflow action "Generate a HeyGen personalized video for a contact" (API token, contact properties mapped to template variables).
- **n8n:** named as a partner and listed as a Business-plan integration [C]; the node's operations were not verified.
- Other partner logos on HeyGen's page [C]: Canva, Adobe Express, Airtable, Clay, Salesforce, Notion, Google Drive, Vimeo, Zoom, Intercom, Customer.io, Pabbly, viaSocket, Gamma, Figma, Snowflake, Telegram, Discord and others.

---

## 5. Pricing

**Web plans — https://www.heygen.com/pricing, read 11 Nov 2026 [C]**

| | Free | Creator | Pro | Business | Enterprise |
|---|---|---|---|---|---|
| Price/month | $0 | $29 ($24 annual) | $49 | $149 + $20 per seat | Custom |
| Credits/month | 3 videos | 600 | 1,000 base; tiers up to 100,000 for $4,300 | 1,500 shared | Custom |
| Max video length | 1 min | 30 min | 30 min | 60 min | No maximum |
| Export | — | 1080p | 4K | 4K | — |
| Speed | Standard | Fast | Faster | Faster; 2× Pro concurrency | Fastest |
| Custom video avatars | 1 | 1+ | 1+ | 5 | 10+ |
| Watermark | Yes | No | No | No | No |

- Voice cloning: 1 clone on Free, scaling to unlimited on Enterprise.
- Business adds: shared workspace, centralised billing with top-ups, SAML/SSO, brand kit, SCORM/LMS export, and the n8n/Make/HubSpot/Zapier integrations.
- Enterprise adds: SCIM, member MFA, a dedicated CSM.
- Rollover: one month for monthly plans; until renewal for annual plans.
- Annual prices for Pro ($41) and Business ($119) are [R] (flexprice).
- There is no "Team" plan on the page, but the API's `subscription.plan` enum still lists `free, starter, creator, pro, team, enterprise, business_plus`. [C]

**Credit burn per minute — [R], flexprice.io reading HeyGen's table on 9 Oct 2026** https://flexprice.io/pricing-index/heygen
- Avatar III: video look 4, photo look 7.
- Avatar IV: photo look 16, video look 31.
- Avatar V: 48.
- Custom expressive motion: +40.
- Video Agent: 40 standard, 120 with Seedance.
- Translation: 4 without lipsync, 6 Speed, 10 Precision.
- Upscale: 1 credit/s to 1080p, 2 credits/s to 4K.
- Generate Look 1; image asset 2; custom model training 60.
- Other blogs quote "Avatar III 3/min, Avatar IV 20/min"; those look like older figures.

**API pricing**
- Pay-as-you-go USD wallet, no subscription. Credits expire after 12 months. The old API Pro/Scale plans are legacy (30-day credits, no auto-renew). No free API credits since Feb 2026. Enterprise is by contract. [C] (help article last updated 9 Nov 2026) https://help.heygen.com/en/articles/10060327-heygen-api-pricing-subscriptions-explained
- Enterprise contract example: Avatar IV at 0.1 credits/s. [C] (burst doc)
- Professional voice clone synthesis: 0.6 API credits per generated minute; slots are bought separately, with 5 trainings per slot per month. [C] (changelog)
- `heygen-voice-1-turbo-free` TTS is free until 30 Nov 2026. [C]
- Per-operation rates [R], and the sources conflict:
  - ≈$0.05 per API credit; $5 minimum top-up; instant voice clone $15 per million characters.
  - Avatar IV photo avatar $2.31–3/min; digital twin $4–4.83/min.
  - Avatar III ≈$1/min.
  - Precision mode $0.10/s.
  - Avatar creation $1 per call; Cinematic Avatar $7 flat; AI Clipping $0.15 per clip.
  - HeyGen Video $0.01/s at 480p (a promo rate).
  - Do not plan against any single one of these.

LiveAvatar pricing is in section 2.

---

## 6. Limits [C]

- **Script:** ≤5,000 characters per avatar request. Audio input ≤10 min.
- **Video Agent:** prompt 1–10,000 characters; ≤20 attachments.
- **Video:** ≤50 scenes; ≤30 min **per scene** (a single-scene avatar/image video is therefore ≤30 min). Avatar videos render at 25 fps. Width and height 128–4,096 px. Default resolution 720p (1080p for studio).
- **HeyGen Video model:** 5–30 s clips (5–15 s through MCP).
- **Batch:** ≤100 items.
- **Inputs by URL to `POST /v3/videos`:** video 100 MB (MP4/WebM), image 50 MB, audio 50 MB; under 2K resolution; must be publicly reachable.
- **Uploads:** simple upload 50 MB (images 32 MB). Direct to S3: 200 MB for video/image/PDF/SRT, 1.5 GB for audio, 1 GiB for a HyperFrames zip. The presigned URL lasts 24 h. Inline base64: 5–16 MB.
- **Retention:** an `asset_id` never expires until deleted. Video download URLs are pre-signed and expire (re-fetch from the GET). Request logs and usage cover 90 days.
- **Voice clones:** instant uses only the first 3 min of one recording (≤100 MiB). Professional needs 1–10 recordings totalling ≥20 min.
- **Consent:** webcam link valid 24 h; an uploaded consent clip must be under 35 s.
- **Queue priority:** by plan (Standard → Fastest), per the pricing page.

---

## 7. Trust and safety

- **Digital-twin consent [C]** https://developers.heygen.com/docs/avatar-consent.md
  - Required before any digital twin renders (`avatar_consent_required`).
  - Three levels: (1) webcam recording on HeyGen's hosted page, with a spoken passcode, for everyone; (2) uploaded consent video, Enterprise only; (3) consent flow waived under a signed indemnity, Enterprise only.
  - The consent clip must be the same person as the training footage (identity-matched), show one visible face, have clear audio, and run under 35 s. It is validated "semantically" in any language.
  - `consent_status`: pending → accepted | rejected. A rejection sets the group to `failed` with `error.code moderation_failed`. Review "usually completes within a few minutes".
  - **Photo and prompt avatars have no consent check and no consent record**; the docs put that responsibility on the customer.
  - The Model API rejects reference videos containing a realistic human face (`realistic_human_reference_not_allowed`): the user must verify identity and create an avatar instead.
  - Other gates in the error catalogue: `phone_verification_required`, `voice_clone_terms_violation`.
- **Moderation policy [C]** (effective 25 Jul 2024) https://www.heygen.com/moderation-policy
  - Never allowed: violence/terrorism, fraud and scams, restricted goods (weapons, alcohol, gambling), harassment, CSAM, self-harm, sexual content, mis/disinformation (elections, health), hate speech, **political content including campaigning and lobbying**, IP infringement.
  - Public figures and celebrities need explicit consent; celebrity or candidate voices also need HeyGen's prior written approval.
  - No avatars or voice clones of anyone under 18. Deceased persons need documented authorisation.
  - The depicted person can demand removal at any time.
  - Enforcement: automated flagging plus human moderators; block, notify, suspend, or report to authorities; appeals by email, with a different moderator where possible.
  - On the API, moderation shows up as `content_policy_violation`.
- **Terms [C]** (last updated 16 Oct 2026) https://www.heygen.com/terms
  - 18+ only. California law. Payments non-refundable.
  - Only the account holder's employees, affiliates and contractors may use an account; no third parties; one Free account per user.
  - Users must not present output as wholly human-made or omit AI disclosure where the law requires it.
  - No building competing products and no benchmarking.
  - **Training:** on Creator/Pro/Business the user grants a licence that includes training HeyGen's models; Enterprise data is excluded by default; others can opt out through the privacy team.
  - Output ownership: paid plans own it; Free output is licensed for non-commercial use only.
- **Watermark and disclosure:** visible watermark on Free only [C]. C2PA or invisible watermarking on exports is **not confirmed** by any HeyGen page I could read; one removal-tool vendor claims it [R]. A HeyGen blog notes the EU AI Act machine-readable-marking grace period runs to 2 Dec 2026.
- **Security [C]** https://www.heygen.com/security
  - SOC 2 Type II, GDPR, CCPA, EU-US Data Privacy Framework, "EU AI Act" (as listed). No ISO 27001 or HIPAA claim.
  - TLS 1.2+ and AES-256. Annual third-party penetration test.
  - All data stored in the US on AWS.
  - Trust portal: https://security.heygen.com.

---

## 8. Enterprise and admin

- **Workspace roles [C]:** Super Admin (everything, including removing content, purchases and invites), Developer (create content plus API access), Creator (create content only), Viewer. https://help.heygen.com/en/articles/9468098-collaboration-and-access-control-with-workspaces
- **Project/folder sharing:** Private, Specific Collaborators (Editor / Viewer / Proofreader), or All Collaborators.
- **Sub-workspaces:** own members, permissions, avatar slots, credit budget, API keys and templates; billing shared or separate.
- **Joining rules:** anyone on the domain, domain users with approval, or invite only. Domain discovery does not work for public email domains.
- **Identity:** SAML SSO from Business up, with just-in-time provisioning via a verified domain. SCIM and member MFA are Enterprise.
- **Audit logs:** user and admin actions, viewable by Enterprise customers.
- **Brand controls:** brand kits lockable (`brand_kit_locked`) and shareable view-only to sub-workspaces; brand glossaries; Enterprise can restrict who creates brand kits.
- **Approvals:** the enterprise page claims "approval rules" and "Nothing ships unreviewed"; no mechanism is documented.
- **Enterprise extras:** zero data retention option, no training by contract, 99.9% uptime SLA with service credits, named team, BYOK encryption (from the error codes), burst concurrency, custom rate limits. https://www.heygen.com/enterprise
- **Usage reporting:** `platform.heygen.com/usage` (Activity tab, burst panel), `GET /v3/usage` and `GET /v3/requests` (90 days, day/hour buckets, per API key).
- **Data residency:** US only; no EU region found.

---

## 9. Could not verify

- The official per-operation API rate card (behind login). All per-second and per-minute API prices are third-party and conflicting.
- The official web credit-burn table: the help article's table did not render, so the figures come from flexprice.
- LiveAvatar idle-timeout value, per-plan concurrency (help article says "Unlimited"; other snippets say 5 or 20), avatar slot counts and prices, and Enterprise terms. `liveavatar.com/pricing` returned 404.
- The exact legacy Interactive Avatar shut-off: the deprecation and migration pages now 404, and the help article 12998652 also 404s.
- C2PA / content credentials / invisible watermark on exports.
- Whether consent uses a true liveness check beyond the spoken passcode and identity match, and how much of consent review is human.
- A full permissions matrix, the audit-log schema and export, and how approval workflows work.
- Zapier's full action list (5 actions on HeyGen's page vs "32" from a third party); Make and n8n module lists; the HubSpot listing.
- Video retention period and how long download URLs live.
- ISO 27001/42001, HIPAA, and any EU data residency: no claim found.
- Per-plan voice-clone numeric limits (the page only says "expanded / maximum / unlimited").
- GitHub repo contents (the HeyGen-Official / heygen-com orgs were not opened; the GitHub connector failed to connect in this session).
- g2.com's API pricing article (403).

Downloaded source files are in `(session scratch, not kept)` (`openapi.json`, `la/openapi.json`, `g/*.md`, `la/*.md`). Nothing was written to the repo.
