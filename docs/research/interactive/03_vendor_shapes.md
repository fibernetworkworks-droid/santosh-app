# Vendor request shapes (read from each vendor's own spec, 23 Nov 2026)

Used by `server/app/interactive/vendors.py`. NOT VERIFIED against a live account.

| Vendor | Calls | Auth | Notes |
|---|---|---|---|
| Runway | `POST /v1/avatars` {name, referenceImage (https / runway:// / data URI ≤ 5 MB), personality, voice} → poll `GET /v1/avatars/{id}` READY; `POST /v1/avatar_videos` {model "gwm1_avatars", avatar {type custom, avatarId}, speech {type audio, audio}} → `GET /v1/tasks/{id}` SUCCEEDED `output[0]` | `Authorization: Bearer`, `X-Runway-Version: 2024-11-06` | output links expire 24-48 h; max audio length and price per second not confirmed |
| HeyGen v3 | `POST /v3/assets` (multipart `file`) → asset_id; `POST /v3/videos` {type image, image {type asset_id}, audio_asset_id, engine {type heygen-avatar-6}, resolution} → `data.video_id`; `GET /v3/videos/{id}` completed `video_url` / failed `failure_message` | `x-api-key` | `Idempotency-Key` header replayed 24 h; image must show a face |
| HeyGen LiveAvatar LITE | `POST /v1/sessions/token` {mode LITE, avatar_id} (`X-API-KEY`) → session_token; `POST /v1/sessions/start` (Bearer session token) → livekit_url, livekit_client_token, ws_url | | audio over ws_url `agent.speak` base64 PCM16 24 kHz mono, ~1 s chunks; browser snippet not confirmed |
| Hedra | `POST /v3/files` (multipart) → url (1 h); `POST /v3/models/hedra-character-3` {input {prompt, aspect_ratio, resolution, start_image {source url}, audio}} → job_id; `GET /v3/jobs/{id}/status`; `GET /v3/jobs/{id}` outputs[].url | `Authorization: Key <key_id>:<secret>` | prompt, aspect_ratio, resolution required; price not confirmed |
| Gemini Omni | `POST /v1beta/interactions` {model gemini-omni-1.2-flash, input, response_format {type video, aspect_ratio, resolution, duration "3s".."15s"}} → steps[].content[] type video data (base64) or a files/ uri | `x-goog-api-key` | no audio input, no recognisable people; 720p ≈ $0.07/s |
| Simli | `POST /compose/token` {faceId} → session_token | `x-simli-api-key` | browser simli-client 3.2.0: PCM16 16 kHz mono |
| Anam | `POST /v1/auth/session-token` {personaConfig {avatarId, enableAudioPassthrough true}} → sessionToken | `Authorization: Bearer` | @anam-ai/js-sdk 4.29.3; createAgentAudioInputStream pcm_s16le 24 kHz |
| Tavus | `POST /v2/conversations` {pal_id, conversational_context, custom_greeting} → conversation_url | `x-api-key` | a custom brain lives on the PAL (`POST /v2/pals` layers.llm), not on the conversation |
