# Hoola Interactive — the Model Lab

Our own HeyGen + ElevenLabs: a **face engine** (a real-looking person whose lips match the words) and a **voice engine**
(realistic speech + voice cloning in Indian languages), both on one GPU. The plan, the licences and the costs are in
[`docs/INTERACTIVE_AVATAR_PLAN.md`](../docs/INTERACTIVE_AVATAR_PLAN.md).

This folder is **Phase 0–1**: the lab where the models are downloaded, run and measured on a GPU we only pay for by the
second. Nothing in it has run on a GPU yet, so every speed figure in the plan is still the model authors' own.

## What is here

| File | What it is |
|---|---|
| `registry.py` | Every model the lab may touch, with the licence verdict read from its own model card: `commercial` (may ship), `lab_only` (test only, open question in `note`), `refused` (never downloaded). One gate, `check()`, that every download and call passes. |
| `modal_app.py` | The GPU app: three voice engines + the face engine, each in its own container, one shared weights volume, and a key-locked web endpoint (`/health`, `/voice`, `/face/prepare`, `/face/speak`, `/face/forget`). |
| `../server/app/interactive/lab.py` | Hoola's only door to the lab. Address and key come from the VPS `.env`. |
| `../.github/workflows/interactive-lab.yml` | Runs the lab by hand from the Actions tab (`setup`, `prefetch`, `smoke`, `deploy`, `down`). |

## First run, in order

1. **Accounts and secrets** (once). In the repository: Settings → Secrets and variables → Actions, add
   `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` (from the Modal dashboard or `modal token new`), `HOOLA_ENGINE_KEY` (any long
   random string) and `HF_TOKEN` (a Hugging Face token whose account has accepted **AI4Bharat's terms** for
   `ai4bharat/IndicF5` and `ai4bharat/indic-parler-tts`, which are gated downloads).
2. **Actions → Interactive lab → Run workflow → `setup`.** Copies those keys into Modal's own secret store.
3. **`prefetch`.** Downloads the voice weights into the lab's volume. No GPU, so no GPU cost.
4. **`smoke`.** The real test: one Hindi and one English line from each voice model, then one talking clip from
   MuseTalk's own sample face. Download the run's artifact to hear and watch them; `REPORT.txt` carries the timings,
   including **how many times slower than real time** the face render was on that GPU.
5. **`deploy`** when the smoke test looks right. It prints the web address; put it in the VPS `.env`:

   ```
   AVATAR_ENGINE_URL=https://<account>--hoola-lab-web.modal.run
   AVATAR_ENGINE_KEY=<the same HOOLA_ENGINE_KEY>
   ```

6. **`down`** stops the app when you are finished for the day. Containers also stop themselves after 2 idle minutes, so
   an idle lab costs nothing either way.

Pick the GPU on the run form: **T4** cheapest, **L4** the default (inside Modal's free monthly credit),
**A10G / L40S** for the speed tests that decide what the live teacher needs.

## Rules this lab keeps, in code

- **A refused licence never downloads.** `registry.check()` runs before any model loads, and `purpose="ship"` refuses
  the `lab_only` ones as well, so a lab-only model cannot reach a real user by accident.
- **No face without consent.** `face_prepare` takes `ai_generated` (an AI-made person) or `signed:<record id>` (a real
  person who recorded a consent clip). Anything else is refused before a byte is uploaded.
- **Cloned voices stay watermarked.** Chatterbox writes Resemble's Perth watermark into every clip; the lab never turns
  it off.
- **Nothing is kept.** Audio and video pass through; only a prepared face is stored, under its own id, and `forget`
  deletes it.
- **The key is a key.** Address and key live in the VPS `.env` and Modal's secret store, never in the repo, the chat or
  a log line. No key configured = the endpoint answers `401` to everyone.

## Still open (Phase 0's own list)

- `face_parse_bisenet` (MuseTalk's face-parsing helper) and `dwpose` are **lab-only**: their weights' training-data
  terms have not been read. Both must be replaced by commercially licensed models before anything public ships.
- `indicf5` is lab-only for the same reason (MIT weights, training data unread).
- Indian GPU providers' prices are not published; they need quotes before the paid server is chosen.
