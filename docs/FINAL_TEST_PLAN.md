# Hoola — final testing plan (8 Nov 2026, v0.693+)

The deep check before final testing ran on the code of `main`. What the code checks proved, what they fixed, and what
only a real phone / real call / real account can prove are kept apart below. Tick each row on the real app.

## 0. Before you start (5 minutes, once)

1. VPS deploy of the newest `main` (vps-ops > deploy), then open `https://hoola.ainewtika.com/healthz`:
   `ok: true`, the newest version, and a `worker` block with `started: true`. `ok: false` = the background worker is
   stuck — stop and send the `errors` job output.
2. vps-ops > `auth_check` → must say LOCKED (401 without a login).
3. Phone: install the newest APK. Profile > Google Drive > "Google Drive jodiye" (her Google sign-in has been dead
   since 3 Nov — Gmail / Drive / Calendar / Sheets / Business Profile all refuse until this is done).
4. Anthropic credit and Gemini (AI Studio) credit topped up — an empty balance looks like "AI service busy".

## 0b. Switching every brain to GLM 5.3 Flash (OpenRouter, paid - chosen 8 Nov)

`~/apps/santosh-core/.env`: `GLM_API_KEY=<the OpenRouter key>`, `GLM_BASE_URL=https://openrouter.ai/api/v1`,
`GLM_MODEL=z-ai/glm-5.3-flash`, `CHAT_LLM=glm`, `CLAUDE_ALL_GLM=true`, no `OMNIROUTE_URL`; then
`pm2 restart santosh --update-env` and `.venv/bin/python -m app.glmdoor check` -> PAKKA.

## 0c. (older) GLM on NVIDIA, free - her key never got an answer from GLM there

1. build.nvidia.com > sign in (free NVIDIA Developer account, phone check) > model `z-ai/glm-5-3-flash` > Get API Key.
2. Put these in `~/apps/santosh-core/.env` on the VPS (the key ONLY there, never in chat):
   `GLM_API_KEY=nvapi-...`, `GLM_BASE_URL=https://integrate.api.nvidia.com/v1`, `GLM_MODEL=z-ai/glm-5.3-flash`,
   `CHAT_LLM=glm`, `CLAUDE_ALL_GLM=true` (keep `ANTHROPIC_API_KEY` set if you want Claude as the backup).
3. `pm2 restart santosh --update-env`, then vps-ops > `glm_check` -> "PAKKA: GLM answers through the door".
4. Test C1-C10 again on GLM. Gemini Live remains the call's voice.

## 1. Free checks the server can run itself (no model cost)

| vps-ops job | Pass looks like |
|---|---|
| `status` | pm2 online, healthz version = newest |
| `tool_card` | right tool in view 176/176, wrong family 0 |
| `hard_card` | spotted 28/28, pylab in view 28/28 |
| `maps_card` | 26/26, guards 5/5 |
| `research_card` | calibration 11/11, research recognised 20/20 |
| `research_runoff_check` | hoola READY |
| `long_card_status` | set OK |
| `voicecheck` | Gemini key + voice ready |

These were all run in the sandbox on this code and passed (numbers above are the sandbox results).

## 2. Chat (phone + web console) — the same brain

| # | Say / do | Expect |
|---|---|---|
| C1 | "Namaste" | Short warm reply in Hinglish, no tool rows |
| C2 | "Kal subah 9 baje yaad dilana dawai lene ka" | One line confirming the time; reminder in the list |
| C3 | "2 minute baad yaad dilana chai" | Reminder fires in ~2 min (server clock), chat + push |
| C4 | "20 lakh ka home loan 9% par 20 saal, EMI kitni?" | Pylab runs; EMI ≈ ₹17,995; no "lagbhag" guess |
| C5 | "Sharma ji ko quotation PDF banao: 10 chair ₹1,200" | A PDF card, gaps named in ONE line, nothing sent |
| C6 | "Sabko diwali offer WhatsApp kar do" | A campaign DRAFT + "Bhej doon?"; nothing sent until her "haan bhej do" |
| C7 | "Rahul ko whatsapp pe meeting cancel bol do" | Never opens campaigns (one person) |
| C8 | Ask something, tap Stop mid-reply | Stops; the half reply marked stopped |
| C9 | "Teen baar bola, abhi tak nahi hua!" | Owns the delay in a few words, then the real state |
| C10 | Female avatar only: any finished job | "Kaam ho gaya" (not "ho gayi"); "main kar rahi hoon" |

## 3. Long jobs

| # | Do | Expect |
|---|---|---|
| L1 | "5 supplier dhundo, unke daam ki table banao aur Excel do" | Plan card first, steps tick, one Excel, "Kaam ho gaya" |
| L2 | During L1, ask "kal ka mausam?" | Weather answered; L1 keeps running |
| L3 | During L1, "isme GST bhi jodo" | A step is added to the SAME job |
| L4 | During L1, "roko" | Job stops, said once, no later "ho gaya" |
| L5 | A job that needs her (e.g. GST number) | Asks once; her answer puts the same job back to work |

## 4. Voice call (the soul)

| # | Do | Expect |
|---|---|---|
| V1 | Call, "aaj ka mausam?" | Answer in ~2–4 s, one voice only |
| V2 | "Mera calendar batao" | "Ek second" then the answer (needs Google sign-in) |
| V3 | "5 supplier ke daam dhundo, agents laga do" | "Team lag gayi" → later 2–3 spoken sentences of the result |
| V4 | During V3: "agents kahan tak pahunche?" | "3 mein se 2 ho gaye, price wala chal raha hai" |
| V5 | "Agents band karo" | Really stops; no result later |
| V6 | Stay quiet 2 minutes | Call parks (no billing), wakes on her voice |
| V7 | Hang up during a job, call again | The new call opens with the job's result |
| V8 | A reminder due during a call | Spoken on the call, no separate ring |
| V9 | Tap Approve on a card during the call | The call never asks about that card again |

## 5. Night + notifications

| # | Do | Expect |
|---|---|---|
| N1 | A routine result between 22:00–08:00 | No buzz at night; it arrives after 8 am (newest 3) |
| N2 | Her own reminder at 23:00 | Buzzes at 23:00 (never held) |
| N3 | An approval card at night | Arrives at once (never held) |

## 6. Web Studio / App Studio / desks (console)

| # | Do | Expect |
|---|---|---|
| W1 | Web Studio: "Pune ki bakery ki website" | A brand name, 3 full looks, build streams live |
| W2 | Publish → domain | DNS records shown, her tap, 3-resolver check |
| W3 | App Studio: open, describe an app | Its own screen, plan → build (CI) |
| W4 | AI Employees > Leads desk | Loads (no "Not Found", no endless Loading) |

## Fixed by this deep check (code)

- The AI video studio tools lost their family to the construction Studio desk (same variable names): `video_studio`
  rode every turn and "ai video" opened the construction shot-brief desk. Fixed (own names + own family).
- A skill pack was stamped "installed for ever" even when every install crashed — that user never got the pack.
  Now the stamp waits until the installs succeed (all 30 pack seeders).
- The Leads card counted 8 rule asks (no tool to pick) as misses (13/21 looked like a failure; it is 13/13).
- A stale count pin (hub 83 -> 84 since the Lead Generation employee) healed.

## Still NOT verified (needs the real world)

- A real call with a running agent team and a long job (V3–V5).
- A held night push on her real phone (N1).
- Every Google feature (her sign-in is dead).
- Gemini's bill vs Hoola's meter; per-minute cost of a long call.
- Maps / Leads / research / vendor lanes: no live paid call has run on most of them yet.
