"""HTTP API for the Santosh app, the Meta webhook, and the demo chat page."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
from urllib.parse import quote
import json
import re
import logging
import threading
import time
import shutil
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from . import campaigns as camp
from . import worker
from .agent import run_turn
from .config import get_settings
from .db import Conversation, Message, init_db, session
from .events import bus
from .leads import import_leads

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("santosh.api")
STATIC = Path(__file__).parent / "static"
MAX_UPLOAD = 10 * 1024 * 1024
APP_VERSION = "0.746.0"   # VIDEO LEARNER REDESIGN v0.746.0 (built as 0.745; their WEB + APP PAGES took 0.745.0 - REBASE PROTOCOL, both kept) (owner: "make all screen perfect and all feature functional" -> the approved canvas -> "go"): the Video Learner is four screens in plain English - home (teach by link / upload / drop, learned tasks with YouTube thumbnails, Proven / Learned / Notes / Could not learn, filters), watching (the video plays, Hoola's notes stream in AS GEMINI WRITES THEM - seekh._stream_text, every [m:ss] jumps the video, the five real stages, Stop keeps nothing), learned task (steps with their video moments, Before you start / Watch out / Not seen, a form built from what the task needs, Re-learn / Remove), and doing it (the run's own live steps on the page, a card that needs her -> Answer, then Did it work? -> Proven, scored on the procedure too); new doors /api/seekh/console/stop, task (GET / DELETE), proven; failed watches stay on the list with their reason and never count toward today; console CSP allows only i.ytimg.com thumbnails and the youtube-nocookie player; switch seekh_live_notes. Previous: WEB + APP PAGES v0.745.0 (owner: "DEPLOY IT IN REAL WEBSITE hoola.ainewtika.com" -> GO): the Hoola website now shows what the product does - two new pages on the same drawn-console language as home/employee/network/studio (same nav, same chrome, GSAP scroll, strict CSP, no third-party files): /websites walks the Web Studio as drawn scenes - the brief, the plan, the three looks, the live build, the 12 launch checks and the launch card; /apps walks the App Studio - the plan card, the three looks of the Home screen, the prototype and the store steps; every page's nav now links Websites + Apps (home, employee, network, studio get the links too); both pages point their CTA at their own studio (/console/web, /console/apps); test_website.py pins the pages, the strict CSP on both, the studio deep links and the plain-script rule. Previous: SEEDHA SEND v0.744.0 (owner screenshot: "REMOVE THE AVATAR FACE AND CHAT PANEL SEND BUTTON IS GOING OUT OF PANEL"): the v0.740 model chip (up to 200px) could not shrink, so the Send button sat 12px past the composer edge at every width - the chip now gives up room first (name ellipsis), every other control keeps its size; the avatar face on the home greeting is hidden (console_human). Previous: SAAF INSAANI v0.743.0 (owner: "DO NOT CHANGE EXISTING DESIGN BUT MAKE IT MORE USER FRIENDLY AND HUMAN MADE NATIVE" -> "GO" on the canvas): the console keeps its layout, colours and fonts and talks like a person - home greets her by the time of day and says in one sentence what is waiting / running; work cards show the real step + time so far and a bar only when the job reports real progress; the sidebar badge says "1 needs you" / "2 working"; spend reads "Rs 412 of Rs 2,000"; reply actions Copy / Quote / Ask again / Good answer / Not right; every approval says "Slide to approve" / "Not now" + "Nothing happens until you approve."; one-colour start icons; no emoji headings; the placeholder gives a real example; AI Employees cards name what a role needs. Switch console_human (default on; conftest pins it off for older suites). Previous: AIHUBMIX v0.742.0 (owner: "AIHubMix -- LETS DO IT"): AIHubMix's free models - coding-glm-5.3-flash-free (the same GLM 5.3 Flash), gemini / gpt-5.5 / qwen free variants - usable with ONLY AIHUBMIX_API_KEY in .env: in the console dropdown as "aihubmix:<model>" (shown Free), and as the WHOLE server's model by GLM_MODEL=aihubmix:coding-glm-5.3-flash-free (chat, background jobs, Web Studio, the SDK door) - llm.glm_ready / model_in_force read GLM_MODEL's provider; names like coding-...-free are matched to the same model in OpenRouter's catalogue, so pictures / tools / window come from GLM 5.3 Flash's own list; its rate limit (10 a minute, 100 a day, 1M tokens a day shared) is said plainly. Previous: MORE PROVIDERS v0.741.0 (owner: "CHECK ALL MORE FREE POWERFUL OPTION" -> "GO"): the model dropdown also lists models from Google Gemini / Groq / Mistral / NVIDIA / Z.ai, written "<provider>:<model>" in chat_models (agent/providers.py: each provider's OpenAI-compatible endpoint, its key ONLY in .env - GEMINI_CHAT_API_KEY so chat never spends the prepaid voice GEMINI_API_KEY); a model is listed only when its provider has a key; her turn goes to that provider with its own key and a plain request (no provider-specific reasoning field); each model is described from the same model in OpenRouter's public catalogue, and one nobody can describe is treated as text only (never sent pictures); the dropdown shows the provider where free / paid is not known; offered on any OpenAI-style chat (not only OpenRouter). Previous: MODEL DROPDOWN v0.740.0 (owner: "IN WEB CONSOLE LETS USER CHOOSE THE MODEL VIA DROPDOWN"): a model chip in the console composer opens a menu of the OWNER's model list (GLM_MODEL + chat_models, default three free OpenRouter models), each described from its own OpenRouter list (free or paid, reads pictures, takes tools; a model with no tools is shown but cannot be picked); her pick is saved per user (data/model_choice) and her whole turn runs on it through the v0.739 model profile (llm.MODEL_NOW: the model sent, picture / PDF routing, reasoning field, window); a model the owner removes falls back to the default; GET /api/model/choices, PUT /api/model/choice; only offered when the chat runs on OpenRouter; switch chat_model_choice. Previous: MODEL PROFILE v0.739.0 (owner: "WHY EVERY NEW MODEL NEED UPDATE IN CODE EVERY TIME --- WHY IT IS NOT GENERALIZE" -> "GO"): what the chat model can do is READ from OpenRouter's own model list at start and once a day (agent/modelprofile.py: input kinds, accepted parameters, context window, price; kept in memory + on disk) instead of being written into the code per provider - pictures go to the model only when its list says it reads them, the reasoning field is sent only when it takes one, the chat window follows the model's own, a model without tools is named loudly at start, a model's own "reasoning is mandatory" error is learned and remembered; a list that cannot be read keeps the old settings; GET /api/model/profile + healthz chat_model_reads; switch model_profile. A new model = GLM_MODEL in .env + a restart. Previous: PARITY 1 + 9a + 12 v0.738.0 (owner: "TILL I TOPUP -- CONTINUE OUR THIS WORK" on the parity table): gap 1 every message reaches the model (chat_every_message: the research-plan gate no longer answers for it; stop words still stop the work at once but the model writes the reply; the OTP / CAPTCHA hand-over stays before the model); gap 9a one way to make a file (chat_files_by_code: pylab keeps .docx / .pptx / .pdf too - python-docx, python-pptx, reportlab - and the core prompt says files are made with code, doc_studio only for a designed report); gap 12 the phone app can edit an earlier message and ask the last reply again (long-press menu, the console's own /edit and /retry routes). Previous: KEY LIMIT SAID v0.737.0 (owner: "READ" on the errors log after her photo test): the real cause of the GLM pause was her OpenRouter key reaching its $10 spending limit (403 "Key limit exceeded (total limit)") - every GLM call fails until it is raised; the owner now reads "The OpenRouter key has reached its spending limit - raise it at openrouter.ai > Settings > Keys" instead of "something went wrong" (others get the outage line). Previous: GLM PAUSE FIX v0.736.0 (owner: a photo + "WHOS IMAGE ID THIS" answered "Sorry, something went wrong just now"): while GLM is the only chat model a pause of the safety switch refused EVERY chat call for 10 minutes (the chat stayed on GLM, the request code still said no) - now a paused GLM is still asked (glm_pause_one_model = true brings the old refusal back); with the Claude fallback off the SDK door no longer moves picture reading / background calls to Claude during a pause (its credit is out); a pause / empty answer reads "busy, try again", not "something went wrong"; healthz names the chat model with "(paused)" instead of "claude". Previous: ALL GLM v0.735.0 (owner: "WE WILL TEST ONE BY ONE MOVE EVERY THINH ON GLM 5.3 FLASH"): the last Claude-only jobs move onto GLM-5.3-Flash, each behind its own switch - pictures go to GLM as pictures (glm_images; OpenRouter lists image input for z-ai/glm-5.3-flash), a PDF goes as its own text (pypdf) or, when it is a scan, its first pages as pictures (glm_pdf, pypdfium2, glm_pdf_max_chars 60000 / glm_pdf_max_pages 8), the website architect is no longer forced onto Opus (architect_opus False), and a GLM failure at the SDK door says it is busy instead of answering on Claude (claude_all_glm_fallback False); each switch on in .env = the old routing. Previous: TRAPS + LIVE FIXES v0.734.0 (owner: "FIX TRAPS" after the first live parity card, GLM-5.3-Flash 88.1/100, 35/60): the small fixed prompt gains three rules - an unclear "send it to him" gets ONE question naming what is missing, an impossible ask (the past, the physical world) is said plainly in the first sentence with the nearest real help, and reshaping words already in the chat (table, bullets, shorter, example, a caption) is plain writing with no tool; the request dump finally writes on the live server (the sweep compared a naive row time with an aware cutoff and failed every write); parity card rubric v2 (artifact / graphic / make_document = making, web_fetch = web, a plan written first is fair) + set v2 (an honest "cannot be booked" is not a booking claim). Previous: CLAUDE PARITY MEDIUM v0.733.0 (owner: "GO MEDIUM" on the parity table): gap 4 adaptive thinking (chat_thinking_adaptive: every chat turn may think - greeting low, ordinary medium, hard / long / big high; OpenRouter reasoning streamed to the folded Soch card, never saved or resent, answer room kept); gap 5 the plain loop (chat_plain_loop: the answer ends the turn - no generic self-check, no reviewer on ordinary hard answers, no after-turn draft check; only a false action claim / an unset reminder / done-with-every-tool-failed is fixed, BEFORE she sees it, the draft wiped and the fix written in the same reply; research dossier fix kept); gap 10 one memory (chat_one_memory: memory on her newest message ~10.6k -> ~0.6k chars - one SINCE YOUR LAST REPLY note + skill names; diary / recent words / facts by meaning / old chats / coder primer / the 9k skills list fetched with yaad_khojo, which now also searches the diary). Previous: CLAUDE PARITY 0-6 v0.732.0 (owner: "WE WILL KEEP GLM 5.3 FLASH AS PRIMARY FOR ALL FOR NOW --- PHASE 0 + 1" then "GO VIA THIS --- LARGE ISSUE FIRST" on docs/CLAUDE_PARITY_PLAN.md): Phase 0 the parity card (60 scored conversations, python -m app.quality parity --check|--live) + the request dump (GET /api/conversations/{id}/request/{turn}: what the model really received); Phase 1 one model per chat (chat_one_model: the chat brain GLM-5.3-Flash for every step, asked again when busy, never switched mid-chat; PDFs still go to Claude); Phase 2 a small fixed system prompt (chat_small_prompt: 52-62k -> ~9k chars, byte-identical every turn, everything else fetched by tools, cache split after the core); Phase 3 clean tools (chat_core_tools: ~22 core tools in view, one web_fetch reader, English descriptions, tight family admission, head+tail results, clean errors); Phase 4 long work in the turn (chat_work_in_turn: crews + research inline, 20 min / 200 calls); Phase 5 answer only (chat_answer_only: no ledger line or stapled notes, the ledger in the steps row); Phase 6 artifacts the Claude way (chat_artifact_direct: the new artifact tool create / update / rewrite, the chat model writes the page, streamed draft, Undo); registry 620. Previous: SAB ENGLISH wave 3 + phone v0.731.0 (built as 0.730 - their SHILP MANCH took 0.730.0, REBASE PROTOCOL, both kept; owner: "GO PHONE and GO WAVE 3 -- in parallel"): the phone app is English (213 Dart files ~10,600 strings, Kotlin notifications / tile / widget / manifest; i18n lookup keys kept so Hindi / Marathi phones keep their language; pc_screen.dart frozen) and the model's own working text is English (system prompt + reply rulebook with the two lang.apply anchors unchanged, ~1,100 tool descriptions / errors / hints, nudges + wake texts + memory blocks, the voice call persona and quiet notes); every detector that reads her Hinglish kept; protocol markers kept; 9 parallel agents merged and compared suite-for-suite with v0.729.0. Previous: v0.730.0: SHILP MANCH - the ArtCraft generation lane, their Omni API behind her tool (owner: "MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS" after the READ of github.com/storytold/artcraft - 'the IDE for artists', MIT/Apache-2.0; planned at v0.686.0, the dev chain ran on to v0.729.0 SAB ENGLISH wave 2 while SHILP sat planned - REBASE PROTOCOL, rebuilt fresh on their 53ab8a366 v0.729.0 tip, their base kept whole; shilp = craft): ONE tool `shilp`, SIX actions over EXACTLY the surface their public doc proves (their _docs/artcraft_omni_api.md, base https://api.storyteller.ai - their doc's own emphasis: NOT api.getartcraft.com): video (POST /v1/omni_api/generate/video - model, prompt, duration_seconds, aspect_ratio, negative_prompt, resolution, generate_audio, start/end frame image urls + reference image/video/audio url lists -> an inference job token) | image (POST /v1/omni_api/generate/image) | job (GET /v1/omni_api/job_status/job/{token} - their states ride raw: pending/started/attempt_failed still run, complete_success/complete_failure/dead/cancelled_by_user/cancelled_by_system terminal; the finished media at state.maybe_result.media_links.cdn_url) | jobs (the batch, up to 25 tokens) | status + models (zero network; the curated 62-model catalog from their public README, dated). THE LAWS: BYOK owner-level (config artcraft_api_key, VPS .env only - ARTCRAFT_API_KEY, never chat/repo/envelope; API access gated per account by the ArtCraft team) | money is hers (every generate spends credits; 402 -> PAYMENT, FINAL, never retried; the tool description says only on her explicit ask) | idempotency minted here (fresh UUID4 per call, returned in the envelope, caller tokens ignored) | reference urls cross the lane's own wall BEFORE any byte moves (http(s) only per their rule, no embedded credentials, no loopback/RFC1918/link-local/reserved/metadata hosts - internal endpoints never land in their logs; shape problems BAD_INPUT, wall refusals NOT_ALLOWED) | URL inputs only (their *_media_tokens fields accepted ONLY to be refused BY NAME with their own mutual-exclusivity rule quoted - the upload endpoints are not in the public doc, nothing invented) | caps refuse never clamp (prompt 8000, refs 20/field, url 2048, batch 25) | one network seam _http (tests monkeypatch exactly it, the suite offline; lazy httpx, zero new pip) | one envelope {schema_version, ok, tool, action, ..., meta{elapsed_ms, backend}, error{code, message, hint}}; kill switch shilp_enabled default on; ALL strings English (the standing rule). DOORS: the toolbelt door (agent/tools.py registry 617 -> 618, 618 = 617 + 1 shilp) + the MCP stdio door (server/app/shilp/mcp_server.py, the kaan wire: line-delimited JSON-RPC 2.0 protocol 2025-06-18, one tool shilp, dispatch through agent.shilp_tools._sync so the doors can never drift, serverInfo hoola-shilp). Tests: NEW test_v0730_shilp.py (43, zero network, the seam fake records every call so the tests assert method/url/body/auth not just outcomes): envelope shape, unknown action, kill switch, status zero-network + keyless + never-leaks-the-key, NEED_SETUP on every network action keyless, models 62 complete, the media-token mutual-exclusivity refusal, the 12-case reference-url wall table (loopback/RFC1918/link-local/metadata/credentials/ftp/file/garbage - all refused before the seam), the 20-ref + 8000-prompt caps refusing, video/image happy paths asserting the POST url + Bearer key + body + minted UUID4, fresh idempotency per call, their 401 -> AUTH / 402 -> PAYMENT-final / 400 rides their words, their doc's own pending + complete_success example states mapped verbatim, complete_failure honest with the credits note, job-token shape, batch happy + cap + shape, registry 618 pin, enum pin, APP_VERSION pin, purity (no top-level httpx), the MCP door (initialize hoola-shilp + tools/list one tool + the six-action enum + tools/call riding the same dispatch + NEED_SETUP through the door). Zero new pip, zero new keys (BYOK rides HER key), zero Flutter change. Server-only deploy = owner's vps-ops dispatch. NOT VERIFIED live: her first real generation (needs HER ArtCraft key in the VPS .env - action=status shows the setup directions); the zero-network status/models ride the deploy. Previous: SAB ENGLISH wave 2 v0.729.0 (owner: "GO WAVE 2"): the text that reaches her WITHOUT the model is English - phone notifications (push.render, ~200), chat lines the server writes itself (errors, timeouts, stop / cancel, a finished job's line, the notes under a reply, plan card words, ~60), approval / payment / connect cards, HTTP errors and greetings (~250), and approval card titles + desk messages across the connectors and rent / event / logistics / front-office / architecture desks (~700); the word lists that read her Hinglish are untouched, model instructions stay for wave 3, frozen PC files untouched; test assertions moved to the new text. Previous: SAB ENGLISH v0.728.0 (owner: "MAKE ENTIRE HOOLA IN ENGLISH - MOST IMPORTANT"), wave 1 = what she sees most: one switch hoola_language (en default, auto = answer in her own language as before); the two language rules the model reads (system prompt + reply rulebook) say clear simple English whatever language she writes in (app/lang.py); all 644 working-row step labels in English (agent/labels_en.py, read through lang.label everywhere a label is shown); a voice call is locked to Indian English; measured ~18.7k server and ~4.2k phone lines with Hinglish words for the next waves; 7 tests. Previous: VAADA PAKKA v0.727.0 (owner, screenshot: Hoola said "Now starting one fresh, simple demo-only NetMitra build." and, asked "WHERE TO CHECK THAT", "Starting one fresh ... build now." - no build ever started, so no page card: "HOW USER WILL KNOW THAT WORKING IS GOING OR NOT"): the v0.311 promise guard knew "I'll / let me / kar raha hoon" but not an English line with no "I" ("Now starting...", "Starting ... now", "Rebuilding it now", "On it"), and it only ran in a turn that had already used a tool; both holes closed - such a reply is sent back once to DO it (the build starts, its card shows), at most twice a turn; 11 tests. Previous: PAGE CARD NARROW v0.726.0 (owner, screenshot: "CHECK WHEN SIDE SECTION WIDTH MOVES --- THE CARD GET MESSY"): with the side panel open the chat column is ~340 px while the window stays wide, and the v0.725 page card followed the WINDOW - Share / Open stayed on the right, the summary was squeezed to a 36 px column and the title to 0 px; the card now sizes by its own width (container query hpcard): under 520 px the buttons take their own row under the text, under 340 px the picture hides, the title wraps to two lines; browser test at 1180-1700 px with the panel open (fails on the old CSS); 2 tests. Previous: PAGE CARD v0.725.0 (owner, screenshot of "Build an interactive web UI · Page": "DONT HAVE A TIMING AND WORK IN PROGRESS ETC --- SHOW ME HERE A PREMIUM AND PERFECT CARD" -> preview -> GO): the page card is one card in every state - while it is made a live clock from the server's start time, the usual time, the real step (writing / checking), a moving bar (no made-up percentage) and Stop; ready = a small picture, what the page holds, version, how long it took, Share + Open; not made = the reason in plain words + Try again; the builder now reports its step, start and duration and can be stopped (POST /api/artifacts/{id}/stop); 6 tests incl. a browser walk. Previous: CLAUDE JAISA v0.724.0 (owner: "GLM IS NOT ISSUE... MIGHT BE ISSUE IN OUR CODE --- CHECK IT PROPERLY" -> "MAKE IT 1 MILLION CONTEXT WINDOW FOR EVERY CHAT" -> "MAKE IT EXACTLY AS CLAUDE CHAT DOES ENTIRE MSG HANDLING"): measured - with GLM on, the 40k-token chat cap counted the system prompt + tools (~33k tokens), leaving the conversation ~7k, so every real chat was shortened / dropped on every turn; now every chat has a 1,000,000-token window (a smaller real window is learned from the model's own too-long error and retried once), no GLM cap (if set, it is conversation room on top of the fixed part), GLM clears old tool results at 30k not 12k chars; and every message reaches the full model like Claude chat - no quick no-tools lane answering from 10 lines (its pair was kept out of the history), no bare "haan" approving a card before the model reads it; 9 tests. Previous: PICHHLA SAWAAL v0.723.0 (her "YES" to Hoola's own "Want me to make a full PDF report?" got "Koi pending approval card nahi mila ... YES kis cheez ke liye tha": when the chat no longer fit the GLM door's 40k-token cap the safety net shortened the previous exchange too and a shortened reply kept only its first 1,500 characters, so the closing question was gone and haan_karo looked like the meaning of a bare yes): a shortened reply keeps its head AND its end, the exchange right before her message stays in the rich form and is never dropped, haan_karo says a yes to your own question is not its job; 5 tests. Previous: JAWAB HI JAWAB v0.722.0 (her $5M AI SaaS ask was handed to a background agent team; its full answer sat in the team record and never reached the chat, and the follow-up turn listed every project on her desk instead): a finished team's follow-up now fetches the deliverables (agent_status check) and writes THE ANSWER in the chat, a follow-up talks only about its own job, kaam_status in a follow-up turn sees only that chat; 4 tests. Previous: EK HI KAAM-ROW v0.721.0 (owner, two screenshots: 'IT HAS 2 WORKING... THING IN CHAT SPACE. SHOW ME A PERFECT SINGLE WORKING.. ALSO DONT SHOW THE BACKEND FEED FREQUENTLY HIDE IT IN DROPDOWN' -> preview -> 'DONT SHOW A STEPS JUST A DROPDOWN ARROW' -> GO) = a working turn drew TWO rows - the live 'Working' step list and the 'Working on it... 31s' line; now ONE row: the 3D mark, what Hoola is doing now (the running step's own words, swapped in softly), the clock and a small arrow; the step list sits folded under that row and opens only on her tap (kept open for the reply if she opened it); when the words start or the turn ends it folds where the work happened into 'Worked for Ns' + the same arrow, no step count (replay: 'Worked' + arrow); checked in a real browser with real step events; 2 tests. Previous: HALKA NISHAAN v0.720.0 (owner, sidebar screenshot: 'CHECK THE LOGO IS DARK -- MAKE IT LIGHT LOGO -- AS ALREADY DEVLOPED DONT KEEP THAT RING ON IT') = the console sidebar / sign-in logo was the navy app icon (hoola-logo.png) with a magenta ring (box-shadow); it is now the LIGHT mark - static/hoola-mark.png, the same one drawing (mark.js) rendered on transparent by tool/make_mark.js, no navy square, no ring, no round crop; the app icon / favicon keep the navy (a launcher needs a background); checked in a real browser, light + dark; 2 tests. Previous: SAAF COMPOSER v0.719.0 (owner, screenshot: 'when any artifact, pdf, doc open in right side panel chat typing section icon gets misplaced ... all content must remain intact not misplaced'; built after their SEEKH MANCH ON THE CONSOLE took 0.718.0, both kept) = with the side panel / studio open the chat column is ~250-560 px and the composer row squeezed every button to 21 px, broke Deep research / Hoola PC onto two lines and pushed Send out of the box; the composer now sizes by ITS OWN width (v2.css container query 'composer'): buttons never shrink, chip words never wrap (icons under 520 px, their own line under 280 px), the name label hides under 640 px, mic / call / stop / send stay flush right; checked in a real browser at 1180-1700 px, landing + docked; 2 tests. Previous: SEEKH MANCH ON THE CONSOLE v0.718.0 (owner: 'NOW WE WILL DEVELOP A CONSOLE PAGE FOR IT - CHECK THE EXISTING CONSOLE DESIGN AND IN AI EMPLOYEE SECTION BUILD THE HOOLA AI VIDEO LEARNER. In that, a panel where user can load a video and HOOLA AI will see this and note in REALTIME. Once done, HOOLA AI will prepare a MEMORY for this. And IN THIS PAGE ONLY user will tell HOOLA to PERFORM THIS TASK NOW - then HOOLA will use HIS BROWSER for doing that task' + 'PERFECT START THE DEPLOYMENT' on the prototype shown in chat; built as v0.716.0, their NAYA ROOP took 0.716.0 and their FILE CARD SAHI took 0.717.0 while it sat built - REBASE PROTOCOL onto their 5964cdda7 tip, their code kept whole, the console files hand-merged [their 0.717.0 stamps + mark.js kept, my view + tag re-applied], all kept) = v0.713's learn-from-a-video gets its console page, the HOOLA AI Video Learner, opening from the AI Employees hub (a wide feature card beside 'Your team'; no new sidebar row - the v0.456 law). THE PANEL (static/console/seekh.js + the #v-seekh view): load a video three ways (a YouTube link / Shorts / direct URL typed, or a video FILE picked - it uploads through the chat file lane, 25 MB, and rides as a file_id); Watch & Learn starts the job and the page shows the REAL pipeline live - a five-step stepper (Pehchana -> Video dekh rahi hoon -> Notes likh rahi hoon -> Steps ban rahi hoon -> Memory) with each step's real elapsed stamp, and HOOLA KI NOTES, the perception text her Gemini eyes returned (the [m:ss] moments included) paced in word by word; every stage shown is a real on_stage boundary of seekh.watch, never a guess. When the watch lands, the MEMORY card shows what was kept: the title, website/other kind, the steps each with its :ss] evidence chip, preconditions, gotchas, unsure, the confidence meter and the honesty line (learned is NOT proven - the first real run verifies it); below, 'Seekhe hue kaam' lists every past watch with its recipe badge. PERFORM THIS TASK NOW lives on the SAME page: her instruction plus the kaam's variables become ONE honest chat turn through the same /api/conversations/{id}/messages the composer uses - the task runs through the agent, the computer operator reads the draft recipe at job start and drives ITS OWN browser, sending still asks her tap; the panel stays put, shows the sent state and offers Live activity + Chat. SERVER: NEW seekh_console.py (/api/seekh/console/*: POST watch -> job id, GET progress?id= the 1.2 s pulse, GET watches the memory list with caps; key-protected, tenant-scoped, one watch at a time per tenant - a second start ADOPTS the running job, a page reload re-adopts it; in-process ring, a restart drops jobs but the learned kaam lives in the two real memories) + seekh.watch grew ONLY an additive on_stage callback (classify/fetch/notes/distill_start/distill/memory/done; a no-op for the tool and every existing test, a broken sink never breaks the watch). No new tool (registry stays 617), no new pip, no new keys, no new settings; the frozen PC zone untouched (the lane never imports the operator stack, pinned by test). Tests: test_v0718_seekh_console.py (25: lane guards, the job lifecycle with the doors patched at the module seam, stage order, adoption, honest errors, the console files, the pins; born as v0716 in the collision round, ships as v0718) + the v0713 suite re-run green; Previous: FILE CARD SAHI v0.717.0 = the made-file card drawn the way she approved (owner: screenshot of a live PDF card stacked in a column - "MAKE IT SAME AS DESIGNED IN PREVIOUS PLAN"): the old .cd rule (flex-direction:column) won over v0.716 hmfile, so the page picture, name and buttons stacked centred; now one row (picture, name + type / size, Open + a download icon), "Use as reference" left off file cards, a doubled name ("Report_pdf.pdf") shows once; checked in a real browser; 1 test; Previous: NAYA ROOP v0.716.0 = her new Hoola logo + the chat feel she picked on the preview page (owner: "0 :: PERFECT, 1 : Calm, 2 : Hoola mark, 3 : Fade with soft focus, 4 / 5 / 6 recommended"): ONE drawing (static/console/mark.js) feeds every surface - tool/make_mark.js renders the navy master + the four phone layers + the status-bar silhouette and tool/make_logo.py builds every size from the master; the thinking mark is 3D (T3 tilt + half turn + rest, T1 opposite orbits, T2 signal breath, glossy core in front) in the console working row + the Plan card and on the phone (lib/ui/hoola_mark.dart, 4 layer PNGs, still under reduced motion); Calm pace 34 ms a word on both; the newest words land out of a soft focus (md.js Live soft, per-word age so the fade survives re-renders, code never wrapped); a made PDF / Word / Excel / Slides file is one card (page picture + type tag, name, size, Open / Download); live tool steps as rows (spinner -> drawn tick) that fold into "Worked for Ns · n steps" when words start; the long-job goal card is a Plan card that ticks itself off; her bubble rises in; 10 tests incl. a real-browser check; Previous: SCREENS FIRST v0.715.0 (built as 0.714; their HAR CHAT ALAG took 0.714.0 - REBASE PROTOCOL, both kept) = why the Web Studio still showed a landing page for a portal after v0.709-v0.712 (owner: 'STILL SAME :: CHECK HOW LOVABLE AND EMERGENT HANDLE THIS' -> research -> 'GO' on points 1 + 2): the plan was the site's structure, but every page was still BUILT from a marketing-only section library (hero / services / pricing / reviews) and the three looks showed only the home top (a 'strong distinct hero' + two sections); Lovable / Emergent start from the app's real screens filled with mock data and show those. Now nine APP SCREEN types (dashboard, data table, form, record detail, board, calendar, approvals queue, sign-in, settings; taxonomy.SCREENS, listed apart in section_lines) are what the architect plans a system with, the plan names its MAIN SCREEN (main_screen, a depth check for portals / web apps / marketplaces, 'Main screen' pill on the Studio plan), a system's home = a compact app front door + that main screen, the looks show it (screens first, at least one even at SITE_LOOK_SECTIONS=1, APP_LOOK_NOTE instead of the marketing hero note), the writer draws a real screen with marked sample rows (SCREEN_NOTE: data-hoola-screen + data-sample + a 'Sample data' chip, no form element, Hoola's own sign-in), and sample rows never go live (the launch check counts [data-sample]); 5 tests. Previous: HAR CHAT ALAG v0.714.0 = every chat on its own (owner: "WHY OTHER CHAT MSG IS COME IN OTHER SESSION CHAT ... DAILY COWORKER MSG SHOULD NOT BE MERGED WITH NEW CHAT OR ANY OTHER CHAT. KEEP EVERY SESSION INDEPENDENT"): ROOT CAUSE - every background message (AI-employee desks' daily reports via net.home_conv, new-mail notes, calendar alerts, Google reconnect notices, crawl failures, re-homed reminders / routines) went to convs.current = the chat she had OPEN (the console marks the open chat on every stream), so a fresh chat filled with daily-coworker news and the brain answered her real ask with a status report; now convs.notice_chat = the running turn's own chat, else her ONE pinned "Hoola updates" chat (convs.updates_chat, kind updates), routines + the morning briefing run there, and a chat turn reads only ITS OWN chat's jobs (kaamwatch.block strict), cards (card_news_block conversation_id), diary jobs and coder work notes (fence.own_chat); her facts stay shared; switch chat_alone (default on; off = the old rule); 8 tests; Previous: SEEKH MANCH v0.713.0 = learn a way of working by WATCHING a video (owner: 'NOW LETS WORK ON A HOOLA AI AGENT THAT WILL SEE THE YOUTUBVIDEO FROM LINK, SHORTS, MP4 OR ANY VIDEO FORMAT. EXAMPLE FEELING THE FORM OR ANY WORK --- AI WILL LEARN THAT TRAIN ITSELF KEEP IN MEMORY AND IF TASK GIVEN RELATED TO IT IT WILL PERFORM SMOOTHLY' + 'GO' on the SEEKH MANCH plan; built as v0.711.0, their SIRF JO POOCHA CHAT took 0.711.0 and their HAR PROMPT KA PLAN took 0.712.0 while it sat built - REBASE PROTOCOL onto their tip, all kept): ONE new tool `seekh_video` (family seekh, tools 616 -> 617), NEW server/app/seekh.py (the bridge) + agent/seekh_tools.py + procedures.save_video; the eyes and the memories already ship and are only READ - youtube/service.gemini_video for links, the videoedit/brain inline-bytes pattern for attached files, the procedures memory (hint() injects it into every owner turn), the operator recipe box (find() reads it at every job start, Memory.save versions and backs up); the pipeline: classify (YouTube link / Shorts / chat file_id / direct URL) -> perceive (Gemini, the way-of-working ask) -> distill (Claude through brain.think, strict JSON, one re-ask on validation problems then the honest salvage) -> store (a procedure row + an operator recipe DRAFT with runs=0 and a DRAFT note - a proven recipe is never clobbered) -> recall is automatic (hint + 'Recipes that may fit'), and the first good real run overwrites the draft with reality (from_trace); LAWS: every step carries its [m:ss] evidence or is demoted to gotchas, no literal personal value is ever kept (digits masked, values become {variables}), learned is not proven until one real run has worked, caps (seekh_max_per_day=20, file 200 MB / 30 min) + the seekh_enabled kill switch; zero new pip, zero new keys, the frozen PC zone untouched; 40 offline tests test_v0713_seekh_manch.py; Previous: HAR PROMPT KA PLAN v0.712.0 (built as 0.711; their SIRF JO POOCHA CHAT took 0.711.0 - REBASE PROTOCOL, both kept) = why every prompt still gave a landing-page plan after v0.710: the Studio's DEFAULT Build mode asked the architect only for portal / dashboard / login words and sent every other ask to the library's page set for its business type (Home / About / Services / Gallery / Contact, shown as 'The plan is ready'); now every Build ask is planned by the architect on Opus and built at once on her Build tap (studio_build_architect), a brochure gets no data draft or 'lists not added' warning, a failed plan falls back to the plain path saying so, and the section writer is no longer told every site is a small-business page; Previous: v0.711.0 SIRF JO POOCHA CHAT (her 9 Nov ask "AI agent jo YouTube video dekh ke seekhe..." was answered with "Good morning. Quick state: 4 site spec cards waiting..." - my v0.704 card news put the WAITING cards list into EVERY chat turn, so the model opened with a status report instead of her ask): the waiting list now rides only when her words are about pending work / cards (events._ASKS_PENDING), the answered-cards note is marked background and never the opening; webstudio untouched. Previous: ARCHITECT OPUS v0.710.0 = her live server answered the website architect's plan from GLM-5.3-Flash (CLAUDE_ALL_GLM, 45 s clock) with every fallback forced to Haiku (claude_one_model), so every ask came back as the same generic landing-page set; the plan call (draft, deepen, revise) now runs on Opus - the GLM door (glmdoor.CLAUDE_ONLY) and the one-model rule stand aside for it (switch architect_opus) - and every plan logs one 'architect first/final' line; Previous: PLAN KA DHAANCHA v0.709.0 (built as 0.708; their GMAIL WAVE 2 took 0.708.0 - REBASE PROTOCOL, both kept) = the approved plan IS the site's structure (its pages + sections, not the library's marketing set) + the architect plans deep (code-sized simple/standard/complex, every page section by section, journeys, quality, phases, risks, depth checks + one deepen round) + Build mode gives a system ask the same deep plan; Previous: v0.708.0 GMAIL WAVE 2 (built as 0.707.0; their SEEDHA WORKSPACE took 0.707.0 - REBASE PROTOCOL, both kept; owner: "GO WAVE 2" on docs/tests/GMAIL_AUDIT_2026-11-08.md): bulk by filter in ONE call (email_action source_folder / query, server pages up to 500, batchModify chunked at 1,000); Workspace-only settings + delete-forever say "not possible" instead of "dobara jodiye"; an expired linked-mailbox login (invalid_grant) = NotConnected with the plain reconnect line; snooze also moves the rest of the conversation and says when it failed; eml_ card ids refused by email_drafts with the replace_id hint; draft edit resolves names; >10 visible recipients warned; email_thread newest 15 x 1,500; GLM door clears old tool results past 12k chars and compacts the chat at 40k tokens; queued-to-send wording; webstudio untouched. Previous: v0.707.0 SEEDHA WORKSPACE (built as 0.694; their v0.694-v0.706 landed while it was built - REBASE PROTOCOL, all kept; owner: "even when ask for website in plan mode it just starts a plan making down that search with no proper work... why it is not landing on workspace... make a proper fix with perfect smooth transition in pages"): (1) "Build this plan" never dies on the data draft any more - the architect's approve used to 422 "Data ka draft abhi theek nahi" and build NOTHING whenever the plan's lists / rules draft had a problem; now the website is built and the lists + rules wait for their own fix (said in the answer: App & data tab, 'Data dobara'); (2) the Web Studio AND the App Studio move to the workspace the moment she sends (her words in the chat, a live work card on the real clock, a skeleton of the plan / site) instead of sitting on the home under a dotted line for up to a minute - the real plan / website / app opens in the same place, a failure goes back home with her words still in the box and the reason under it; "Build this plan" turns into "Starting the build" at once with a working line in the chat; every page arrives with a short fade-up (still under reduced motion); 4 tests incl. two real-browser walks with a slow plan. Previous: v0.706.0 GMAIL GEHRI JAANCH (owner: "GO DEEP IN GMAIL --- FIND ALL POSSIBLE FLAWS"; three audits, docs/tests/GMAIL_AUDIT_2026-11-08.md): one pooled Gmail client + metadata fetched 8 at a time + token read once (email_check was 7-27 s), slim email rows + more flag + 12k cap (the model saw 6 of 50), thread trash refused without a card, email_thread works on a reply id, watcher history page 2, 429 / 5xx retried, typo address named, email_draft replace_id, reply from the right mailbox, comma names, Bcc kept on edit, primary tab; webstudio untouched. Previous: v0.705.0 LOOP BAND (her harness log 13:39-13:46: "saare promotion mail archive kar do" looped ~40 rounds for 7 minutes beside a live call - an archived Gmail mail keeps its category label, so folder=promotions kept returning the mails just archived, and every round had new inputs so the same-call breaker never fired): Gmail inbox tabs (promotions / social / updates / forums / primary) now mean category + in:inbox, email_threads says so, and the breaker pauses the 13th call of the same tool once and stops the 31st (a parallel batch counts once); webstudio untouched. Previous: v0.704.0 CARD KI KHABAR CHAT MEIN (owner: "WHEN ANY TASK LANDS ON CARD AND USER PRESS SEND, APPROVE ETC --- HOOLA DONT KNOW THAT CARD ACTIVITY IS DONE" + "FOR EVERY WORK IT TAKES TIME"): her Send tap arrives as email_sent, a different kind, so the email draft looked pending for ever (events.CARD_ALIAS makes it one card); every chat turn now hears the cards she answered since the last reply + the ones still waiting (events.card_news_block, was call-only since v0.651); the chat turn reads diary / job state / card news / coder memory in PARALLEL under chat_memory_s 6 s (they ran one after another) and logs "chat memory N s"; webstudio untouched. Previous: v0.703.0 TOOL ARGS MAAF (her G8 log: GLM called kaam_plan step without state x3 and email_draft without to x2, the goal stuck and the "doosra tareeka" loop ran; a missing step state now = done when a note/made is given else current, state synonyms mapped, email_draft takes recipient/email/to_email aliases and a missing to names the exact retry; webstudio untouched). Previous: v0.702.0 GLM SIRF DIKHTE AUZAAR (her G8 run: every GLM step read ~70k tokens, slow, timed out, fell to Claude): Claude tool search sends ~650 tools with ~60 in view (defer_loading for the rest) but the GLM door sent every deferred tool in FULL; now GLM gets only the tools in view + the ones tool_search loaded in the chat (tool_reference blocks become a text line naming the tool); webstudio untouched; 3 tests. Previous: v0.701.0 v0.701.0 PAKKA ATTACHMENT (owner: "GO FIX 1 2 3 + SHEET IMPORT" after the attachment-flow audit): a mail draft keeps its OWN copy of every attached file (data/mail_attach, content-addressed, swept after mail_keep_days 70), so a next-day Bhejo / a scheduled send / a multi-day bulk no longer meets the 24-hour chat-file sweep (the frozen PC cleanup is untouched); Drive attachments go through drive.service.fetch - the drive_find "<account>~<id>" ref works, a Google Sheet goes as a real .xlsx (format: pdf on ask), the 25 MB check runs before the download; sheet_create source={drive_file} imports an Excel / CSV / Google Sheet straight from Drive; webstudio untouched; 11 tests. Previous: v0.700.0 v0.700.0 REASONING ZAROORI (her live OpenRouter check: z-ai/glm-5.3-flash answers 400 "Reasoning is mandatory for this endpoint and cannot be disabled" to {"reasoning":{"enabled":false}}): the SAB GLM door on OpenRouter now always sends {"reasoning":{"effort":"low","exclude":true}} and room() adds the reasoning room there too, so no request is refused first and retried; webstudio untouched; 4 tests. Previous: v0.699.0 v0.699.0 GLM VIA OPENROUTER (owner: "lets go with glm 5.3 flash - via openrouter", after the NVIDIA free GLM never answered her key and OpenRouter dropped the :free slug): with GLM_BASE_URL on openrouter.ai the SAB GLM door sends OpenRouter's OWN reasoning field ({"reasoning":{"enabled":false}} by default = fast + cheap; GLM_THINKING=enabled -> effort low, reasoning excluded, room added), never Z.ai's thinking or NVIDIA's reasoning_effort; a 400/422 on any reasoning field is asked again plain; label GLM (OpenRouter); webstudio untouched; 4 tests. Previous: v0.698.0 v0.698.0 OMNIROUTE SAB KE LIYE (owner: "check omniroute" -> "go"): with OMNIROUTE_URL set, the SDK door that answers every Claude call (claude_all_glm) now uses the OmniRoute gateway on her VPS (its combo, its own provider fallbacks) instead of one GLM endpoint - claude_all_brain pins glm | omniroute, "" = OmniRoute when it is set up; the safety switch is per brain (llm.BREAKERS: 2 failures -> that brain skipped 10 min, Claude answers), one OmniRoute request waits omniroute_timeout_s (90 s, it may try two providers inside it), the no-compression header still rides every request, pictures stay with Claude on OmniRoute; glmdoor check names the brain it tests. Official API-key providers only (OpenRouter free GLM-5.3-Flash, NVIDIA Nemotron, Anthropic) - never OpenCode / Kilo free tiers (client-only terms) or consumer-subscription logins; 2 tests. Previous: v0.697.0 NVIDIA NEMOTRON (her live NVIDIA tests: GLM-5.3-Flash / DeepSeek V4.1 Flash / MiniMax M3.1 Flash hang 25-120 s with 0 bytes on her key, the older names are end-of-life (410) or 404, and only NVIDIA's Nemotron models answer - nemotron-3.5-super-vl-120b-a12b 0.54 s, nemotron-3.5-lightning-30b-a3b 2.0 s, nemotron-3-ultra-550b-a55b 5.2 s, each made the right get_weather tool call): GLM's own reasoning fields (reasoning_effort, chat_template_kwargs.clear_thinking) are sent only to a GLM model, any other NVIDIA model gets a plain OpenAI request (the live chat stream path has no ask-again, so a refused field would have sent every turn to Claude); the same door, the same safety switch; 1 test. Previous: v0.696.0 GLM SAFETY SWITCH (owner's first live NVIDIA test: the key lists z-ai/glm-5.3-flash but every chat call hung 120 s with 0 bytes - with SAB GLM on, every turn would have waited out GLM's timeout before Claude answered): one GLM request waits at most glm_timeout_s (45 s, connect 10 s), a timed-out GLM request is never retried, and after glm_breaker_fails (2) failures in a row GLM is SKIPPED for glm_pause_s (600 s) - llm.cheap_brain and the SDK door (glmdoor.active) go straight to Claude, then GLM is tried again; /api/agent/stats sab_glm shows paused + the breaker; 2 tests. Previous: v0.695.0 SAB GLM + FINAL JAANCH (owner: "NOW GO AGAIN DEEP CHECK THE HOOLA ALL PARAMETERS ..." then "NOW LETS USE GLM 5.3 FLASH FOR ALL USE --- AS NVIDIA PROVIDING FREE API ... FIND THE WAY"; their WEB CLONE took 0.694 - REBASE PROTOCOL, all kept): SAB GLM - with claude_all_glm on, every Claude call at the one SDK door (usage.install: create + stream, async + sync) is answered by the GLM brain - NVIDIA's free hosted z-ai/glm-5.3-flash at integrate.api.nvidia.com/v1 (app/glmdoor.py hands back a real anthropic Message, tool calls as real blocks, tool_choice mapped, server-side tools dropped); NVIDIA requests send reasoning_effort low + clear_thinking and add room to max_tokens (its reasoning cannot be switched off and counts inside max_tokens), a 400 on those fields asks again without them, Z.ai's thinking field is not sent there; pictures go to NVIDIA GLM (image_url), PDFs to Claude; GLM down / 429 = the same call on Claude (claude_all_glm_fallback) when a Claude key is set; counted once at GLM price; python -m app.glmdoor check + vps-ops glm_check; /api/agent/stats sab_glm. FINAL JAANCH - the AI video studio's names were overwritten by the construction Studio desk import (video_studio rode every turn, "ai video" opened the shot-brief desk; own names + cstudio family now), skill-pack stamps consumed only after a clean install (30 seeders), the leads free card counts tool asks only, the hub 84 pin + the GLM tool-turn pin + the one-model stream pin healed, docs/FINAL_TEST_PLAN.md; 11 tests. Previous: v0.694.0 WEB CLONE (built as 0.621.0; their chain took 0.621.0 - 0.693.0 while it sat built - and the sandbox recycle ate the first rebuild mid-flight, the 0.682.0 lane precedent, so this is the rebuilt-from-spec lane: REBASE PROTOCOL onto their 8c11c130d HOOLA APP STUDIO tip, all kept, their story chain verbatim) (owner: "DOES ALL WORK DONE -- DOES NOW HOOLA AI WILL CLONE ANY WEBSITE PERFECTLY" -> the deploy ask "PERFECT IS IT DEPLOYED"): ONE new tool `web_clone` (family webclone, tools 615 -> 616; the family opens only on clone words - admit.py EXTRA_KEYS webclone + INTENTS "web clone" entry, bare "clone" parked in _GENERIC so "git clone this repo" never misroutes and "site banao" stays the website builder; modes learn / migrate / archive; NOTHING is ever published). NEW server/app/webclone/ three-stage pipeline - capture.py (headless Chromium via playwright: post-JS DOM snapshot, linked + inline CSS kept per-file with /* src */ markers, <img> + srcset + CSS-declared webfonts / background-images downloaded locally under caps MAX_ASSETS 400 / MAX_ASSET_MB 25, favicons, JS bundles kept for REA, screenshots 1280x800 + 390x844, manifest.json; SSRF law reuses scrape_tools._guard_url on the page URL AND every asset fetch - private / loopback / metadata addresses never fetched; CaptureError on hard fails), endpoints_adapter.py (zips the bundle and reuses appcheck.endpoints extract + summary -> {counts, top_hosts, urls, api_paths, ips} functional map; live example.com: 3 urls incl. iana.org, svg logo rebuilt with viewBox / numeric width / camelCase attrs), assemble.py (HTML -> JSX: bs4 list attrs joined with spaces, style={{...}} double-brace law with duplicate inline props last-wins (CSS cascade), full HTML->React attr casing map + NUMERIC_PROPS unquoted, significant whitespace emitted as {"..."} string expressions (JSX trims bare text at newlines), svg lane: whitelist elements + camelCase attr remap viewbox -> viewBox, animate/script dropped; per-file CSS rewrite via _css_chunks - captured url()s -> /assets, uncaptured -> FULL absolute origin URL (webpack resolves relative refs as modules and the build dies); asset map keyed by absolute URL AND URL path so root-relative srcs remap; srcset candidates rewritten one by one; captured <html>/<body> class / id / dir carried into layout.tsx; page renders a FRAGMENT - no injected <main>; emits a Next.js app-router project: package.json, next.config.mjs (images unoptimized), tsconfig.json, layout.tsx + page.tsx + globals.css, public/assets, README (the honest line) + ENDPOINTS.md). VERIFIED: offline fixture suite (16 test functions / 21 cases, zero network, zero browser) + the live check (example.com captured + assembled for real, 3 endpoint urls found). HONEST LINE: not pixel-perfect on JS-heavy sites; static / semi-static pages are. Limits live in the generated README (original JS behaviour static, single page) and the tool refuses republishing a third party's live brand (_looks_like_own_or_reference + description law - learn / migrate / archive yes, brand theft no). Neighbour pins healed: 30 len(TOOLS) 615 -> 616 files (19 bare + 11 len(tools.TOOLS)), the w35 comment keeps its chain and appends + 1 web_clone; their quoted version pins re-swept 0.693.0 -> 0.694.0 / 0.694.0+693 across the suite (224 files), ZERO residual; ALL the story pins pass on the new story: the six line-35 pins (TRACE / GRAPH / AGENT / HUB + init_chat_model + KAAN PACK / ADOPT / AEP 1.0 + PARITY) and the slice pins (officehours HOOLA MIDDLEWARE + server/app/aep, crew HOOLA RETRIEVE + aep/retrieve.py, magic21 index() + retriever). Tests: NEW server/tests/test_v0621_webclone.py (16 functions / 21 cases, zero network, zero browser: converter units, svg lane, css rewrite + chunk markers, asset path keys, srcset rewrite, root-attr carry, fragment law, project completeness, scan shape, SSRF refusals, brand refusal, registration 616, admit routing positives and the git-clone / site-banao negatives). pubspec 0.694.0+693. Mirrors: CLAUDE.md chain head, docs/HISTORY.md section (newest-first per their convention), docs/WORKLOG.md entry. Deploy: server-only = owner's vps-ops dispatch; the deployed box still runs 0.685.0 - the paste-in runtime patch (deploy_webclone_pastein.sh) carries the same seams against it. Previous: # v0.693.0 HOOLA APP STUDIO (built as 0.688; their v0.689-v0.692 landed while it was built - REBASE PROTOCOL, all kept; owner: prototype of all 14 pages -> "GO BUILD THE APP STUDIO"): the native-app builder as its own full-screen app at /console/apps, the Web Studio's twin - own sidebar (New app, Home, Search, All apps, Starred, App ideas, Starred + Recent with a rename / star / delete menu), home = one line + Build | Plan (Build sends her Haan when the plan has no open question so the 3 looks start; Plan stops at the plan), the 1 crore+ idea library with audience filter; a workspace per app = her own Hoola thread for THAT app (never the home chat) + the live work card + Plan / Looks / Screens / Prototype | Android / iPhone / Store | Data / Business / Health / Settings (+ History), every button on the existing /api/apps routes (screen images fetched with her token, Design pakka sends the server's hash, Play production / App Store review / rollout steps / deletes ask first and send her_tap only from her tap, the Play service-account key chosen as a file and sealed on the server); NEW appmaker/activity.py = every app job's progress lines as server-timed English steps (looks, every screen with a count, checks, fixes, Kotlin per screen, compile rounds, phone check, iPhone build, TestFlight) through one fail-open hook each in service._work and the android / ios _put; the app view carries activity + builds at a glance; console sidebar row App Development; chat app cards gain Open in App Studio; 6 tests incl. a real-browser walk of every page on a real designed app. Previous: v0.692.0 CALL PAR TEAM (owner: "lets work on hoola ai multi agent call during call during a long task" -> GO; their LEADS DESK EMPTY took 0.690-0.691 - REBASE PROTOCOL, all kept): the background-crew cap COUNTS crews (it compared an id string with a number - a TypeError whenever a crew ran), long-job rounds scheduled from a call run as chat work (no quick-voice Haiku / 8 exchanges / no thinking carried into every round), a call question that did not touch the open job is answered instead of being pulled into it, a crew report that waited out a busy call is still said on the call, spoken crew results carry whole sentences (700 / 3000 / 1500, digest 600), "agents band karo" stops a background crew (kaamstop native stop), on a call kaam_plan add / show / step reach the job running in the chat the call came from, live agent-by-agent progress of every crew in the job block + agent_status, a cap of 8 inline agents per HER (team_tenant_inline_max), a crew asked for on a call works like a chat crew and a research ask gets the research rules, fixed lines in her avatar's forms, two quick asks never pick the same call record (pick + claim under one lock); 10 tests. Previous: v0.691.0 LEADS DESK EMPTY (owner: "it stuck on loading" + their screenshot of the desk stuck at "Loading…"): the desk rendered "Loading…" FOREVER with all three first-load fetches 200 (their second screenshot; reproduced end-to-end in a real browser against the real app - login, hub, Business, Open desk, the rejection caught): ROOT CAUSE `ReferenceError: empty is not defined at Object.leads` - the desk called `empty(...)`, the EDUCATION desk's LOCAL helper (a const inside async function edu(el)), invisible from the leads desk; the first paint put the Loading div up, the render threw before the first innerHTML assignment, the promise rejected unhandled, and a desk with a green network tab looked dead; THE FIX: the desk carries its own `empty` (the same helper, the same pattern every desk uses for its own); THE GUARD: NEW test_v0690_leads_desk_scope.py (3, zero network) - the desk's own empty pinned, and every function the desk body calls must be REACHABLE (a destructured param of the HoolaEmployees wrapper, a definition at the wrapper's own scope, or a definition inside the desk body itself - a helper living only inside another desk's closure fails the test), plus the v0.689 route-seam law re-asserted through it; THE PROOF: the browser walk re-run after the fix - the desk renders fully (the pitch, the Seekh trust tag, the five KPIs with the 20,000/day cap named, all five lanes Built, the store line, Recent runs, the Outreach ledger), zero unhandled rejections. NOT VERIFIED unchanged: the desk answers real APIs on the deployed server, no lane has answered the real world yet. Previous head v0.690.0 MANN KI BAAT (built as 0.686; their EK LAKH ALAG WEBSITE / LEADS EMPLOYEE / KAAM MANCH / LEADS DESK SEAM took 0.686-0.689 - REBASE PROTOCOL, all kept; owner: "GO WAVE 13" - the last wave of the third deep audit: analysis, monitoring and feeling): a research report is held and checked on EVERY turn that writes from a dossier (goal round, routine, call), pylab having run no longer passes the maths check (the draft's figures must be in what the tools printed), the corrected answer is checked again and still-failing figures are said plainly under it, the reviewer is not the writer's own Haiku (hard_check_independent), /healthz says not ok when the worker is stuck (worker.BEAT / health, a hung slot cut at worker_slot_timeout_s), the loop watchdog runs from start and shows in /api/agent/stats; a female avatar's "Kaam ho gaya" stays right (gendered changes only her own forms), the fixed lines follow her avatar and nobody calls her "Owner", non-urgent pushes wait out her quiet hours (push_night_hold; her reminders, cards and alarms never wait; awake = never held), her mood is heard (chat rule + call persona), no "Aur kuch karna hai?" fallback / OFFICE HOURS interview for an unclear ask / "phir bolna", an error after tools ran warns before a blind repeat, the same background error once a night; 16 tests. Previous: v0.689.0 LEADS DESK SEAM (owner: "NOW A PERFECT LEAD DESK FOR IT" + their screenshot of the desk showing a red "Not Found"): the desk's first load was Promise.all([GET /api/leads/overview, GET /api/leads/runs?limit=12, GET /api/leads/outreach?limit=100]) but the server's overview route is GET /api/leads (the router itself is the overview since v0.544) - one 404 killed the Promise.all, the catch painted the message red, six of seven routes worked and the desk still looked dead on open; THE FIX: the desk calls the canonical GET /api/leads now (one line in employees.js; no new route, no alias, no second name for the same thing); THE GUARD: NEW test_v0688_leads_desk_seam.py (4, zero network) - it extracts EVERY api('METHOD', '/api/leads...') call from the console sources and asserts each (method, path) against the REAL FastAPI route table, asserts the ghost route gone from the sources, and FIRES the desk's exact first-load trio over the TestClient (200/200/200 with the key, 401 without; the overview carrying the store/usage/caps/lanes/lanes_built/store_backend/never/one_question/store_boundary keys the desk renders) - the v0.687 test had checked each side SEPARATELY so the broken seam passed both; the seam is checked WHOLE now, proven the honest way (with the old call restored the seam file fails 3/4); test_v0687's surface pin healed to the canonical path (it had pinned the bug). NOT VERIFIED unchanged: the desk answers real APIs on the deployed server, no lane has answered the real world yet. Previous head v0.689.0 LEADS DESK SEAM (owner: "NOW A PERFECT LEAD DESK FOR IT" + their screenshot of the desk showing a red "Not Found"): the desk's first load was Promise.all([GET /api/leads/overview, GET /api/leads/runs?limit=12, GET /api/leads/outreach?limit=100]) but the server's overview route is GET /api/leads (the router itself is the overview since v0.544) - one 404 killed the Promise.all, the catch painted the message red, six of seven routes worked and the desk still looked dead on open; THE FIX: the desk calls the canonical GET /api/leads now (one line in employees.js; no new route, no alias, no second name for the same thing); THE GUARD: NEW test_v0688_leads_desk_seam.py (4, zero network) - it extracts EVERY api('METHOD', '/api/leads...') call from the console sources and asserts each (method, path) against the REAL FastAPI route table, asserts the ghost route gone from the sources, and FIRES the desk's exact first-load trio over the TestClient (200/200/200 with the key, 401 without; the overview carrying the store/usage/caps/lanes/lanes_built/store_backend/never/one_question/store_boundary keys the desk renders) - the v0.687 test had checked each side SEPARATELY so the broken seam passed both; the seam is checked WHOLE now, proven the honest way (with the old call restored the seam file fails 3/4); test_v0687's surface pin healed to the canonical path (it had pinned the bug). NOT VERIFIED unchanged: the desk answers real APIs on the deployed server, no lane has answered the real world yet. Previous head v0.693.0: KAAM MANCH - the work-discipline layer, the OWL port (owner: "GO" on the OWL deploy plan, after the end-to-end READ of github.com/camel-ai/owl @ 2df367e - Apache-2.0, external PRs welcome; planned at v0.686.0, the dev chain took v0.686.0 EK LAKH ALAG WEBSITE and v0.687.0 LEADS EMPLOYEE while KAAM sat planned - REBASE PROTOCOL, re-slotted on their c78c2164c v0.687.0 tip, their base kept whole; registry stays 615 - a laws layer, not a family; zero upstream code, zero new pip, zero new keys, zero Flutter change). THREE SURFACES, all behind kaam_enabled (default on; kaam_ledger_enabled for the receipt alone; off = byte-identical behaviour, tested): TIPS - the specialist workers' search/verify/code heuristics (broad-then-narrow, snippet-is-not-a-number, name-your-sources, if-one-road-fails, code-is-not-work-until-you-RUN-it, done-means-PROVEN) as a house-written block appended to the system prompt ALWAYS (after the family cut, never admission-dropped; the v0.221 byte-identity contract re-pinned to the new truth) | DONE - the <TASK_DONE> law in code: _pakka_check's free backstop - a strong done-claim (ho gaya / ban gaya / bhej diya / complete... with a work-noun guard and negation respect) while EVERY real call failed sets the correction note, no model call, no loop | LEDGER - one (Kaam: steps/calls/plan/done) work-receipt note row under the answer when tools ran (pure arithmetic over the turn's own state, per-tool cap 12, never raises; NO token count - state holds none and a made-up number is worse than none, the after_call law). The caps/loop machinery was NOT ported: the house already owns stricter ones (kaam_plan goal mode v0.187, 24/80 steps, the replan breaker, Pakka kaam v0.78). Tests: NEW test_v0688_kaam_manch.py (32, zero network): the tips, the ledger, the done law, the wiring, the pins (registry 615 unchanged, no kaam tool, module purity stdlib-re-only, fresh-interpreter inertness, APP_VERSION, pubspec); sibling battery green on the swept tree; the jharokha 22 reds PROVEN pre-existing on pristine origin/main with a stash run (this sandbox's missing Chromium, never this diff's lanes). Server-only deploy; desktop untouched. Previous: v0.687.0 LEADS EMPLOYEE (owner: "PERFECT NOW CHECK IN AI EMPLOYE :: BUSINESS SECTION IN WEB CONSOLVE ---- AND PUT THE LEAD GENEARTION AI EMPLOYEE IN THAT SECTION" - the AI Employees hub's Business department): the P0-P5 leads engine (docs/LEADS_PLAN.md) joins the Hub as the Lead Generation employee (key leads, live, default group Business) with its own Leads Desk in the web console - the desk reads the REAL /api/leads/* surface (the overview's lanes and caps, the runs, the rows store with search + per-row opt-out, the outreach ledger) and carries the TWO-TAP hand-off (the confirm card names rows / rows_without_phone / opt_out_excluded and creates nothing until the second tap builds the list) + the DPO forget; the six leads tools stay open to every user (no is_hired gate - the EDU_OPEN law, tested); registry stays 615 (no new tool). Previous head v0.687.0 LEADS EMPLOYEE (owner: "PERFECT NOW CHECK IN AI EMPLOYE :: BUSINESS SECTION IN WEB CONSOLVE ---- AND PUT THE LEAD GENEARTION AI EMPLOYEE IN THAT SECTION" - the AI Employees hub's Business department): the P0-P5 leads engine (docs/LEADS_PLAN.md) joins the Hub as the Lead Generation employee (key leads, live, default group Business) with its own Leads Desk in the web console - the desk reads the REAL /api/leads/* surface (the overview's lanes and caps, the runs, the rows store with search + per-row opt-out, the outreach ledger) and carries the TWO-TAP hand-off (the confirm card names rows / rows_without_phone / opt_out_excluded and creates nothing until the second tap builds the list) + the DPO forget; the six leads tools stay open to every user (no is_hired gate - the EDU_OPEN law, tested); registry stays 615 (no new tool). Previous head v0.686.0 EK LAKH ALAG WEBSITE (owner, after v0.683 showed 100 'Sweet shop' cards in a row: "world wide website template across every field ... not just a small business ... 1 lakh unique templates, 1 lakh website, not same name everywhere"): the Web Studio Templates (webstudio.js) = 1,00,000 UNIQUE websites - 1,000 subjects in 50 world sectors (site/world.py: SaaS, AI, developer tools, security, enterprise, finance, fintech, health, schools, universities, media, gaming, climate, non-profits, civic, crafts ...) x 10 positionings x 10 world cities (Mumbai, Bengaluru, Dubai, London, New York, Singapore, Sydney, Toronto, Nairobi, Berlin), each its own business with its own working name (330 roots, 1,00,000 different names), a website type that suits its sector (6 of 10 types per sector) and a design style (all 10 used); neighbours always differ in sector, name and style; site/templates.py composes card + deep prompt on demand (who visits, goal, pages, home sections, must-work features, positioning, design, content, SEO, build quality, sector rules, never-invent), each <= 2,000 chars and guard-clean (all 1,00,000 checked); search by name / subject / positioning / city / sector / type / style + sector, website-type, style filters; Use sends the sector's library field + the type's goal + the style; 7 tests incl. a browser walk. Previous head v0.685.0 TEESRI JAANCH (owner: the third deep audit - "NOW AGAIN GO DEEP --- CHECK THE HOOLA AI WORKFLOW, TOOL CHOOSE, SKILLS, ANALYSIS, MONITORING, MEMORY, CONTEXT, PERFECT END TO END LONG TASK, RELIBILITY, FEELING --- FIND FLAWS IN IT" -> 47 flaws in 5 waves -> "GO WAVE 9" ... "GO WAVE 12"; built as 0.681, their LEADS ENGINE / EK LAKH PROMPT / KALA MANCH took 0.681-0.684 - REBASE PROTOCOL, all kept): WAVE 9 TURANT - coder work lists + batch routes per tenant (one user's list rode every user's primer), a bulk WhatsApp send only on HER words in this turn (create_campaign auto_send / confirm_send) and a one-person WhatsApp ask never opens the campaign tools, SAB HAIKU covers streamed calls (live chat ran Opus while the log said Haiku) + streamed Web Studio sections counted, research workers hold the price of calls in flight, only the operator hears "recharge Anthropic" (customers / staff / callers hear a neutral outage line, no code / ref aloud), an overloaded one-model call falls back to another model once, a failed job report and a failed staff task are failures, the minute is out of the cached system prompt (every turn re-wrote the whole chat to the cache). WAVE 10 LAMBA KAAM - a cleared old tool result keeps its head + links / ids + figures, crew deliverables keep their share (24k), "haan aage badho" moves only the budget clock (budget_at), a tool: check reads every round of the job, her answer resumes a job that asked her, the waiting-on-her check sees past the step chatter, one queued round at a time, the right file kind for a page / row check, stale paused jobs rested, research / Dhara / crawl give-ups are told. WAVE 11 YAAD PAKKI - a call keeps the small talk after its first brain ask, facts by meaning ride before focus / diary in the memory block, "pin code" / "income tax" / "home loan DSA" are ordinary facts, a fallback checkpoint keeps the previous one whole, compaction / summary reads off the event loop, a never-compacted chat gives the call brain its summary, coder notes follow her Session, a bare "haan" is never learned. WAVE 12 SAHI AUZAAR - bank statement / credit card bill / phone slow / blog reach the right tools, ambiguous words match whole words only (cab book, blood pressure, credit, troubleshoot, clipboard, LinkedIn, homework), skills match on name + description with 2+ words, dead keyword families re-homed, lane rules for overlapping tools, a read skill marks the tools that are not ours. 67 new tests (test_v0681-0684); every regression found by the wide run (510 files) fixed or proven pre-existing on their own tip. Previous: v0.684.0 LEADS ENGINE P0-P5 (owner: "P5 (outreach handoff + CI load proof)"; docs/LEADS_PLAN.md; built as v0.540-v0.545 on the v0.539 base while the dev chain shipped its own v0.540-v0.683, never pushed - REBASE PROTOCOL twice: rebuilt on their v0.671.0 tip, re-merged onto their v0.680.0 tip, re-landed on their v0.681.0 KALA MANCH, re-merged onto their v0.683.0 EK LAKH PROMPT tip as they pushed on, ALL their work kept, the six leads tools ride their registry): the engine GATHERS, it never contacts anyone. P0 the app/leads/ package (lead_runs/lead_contacts/lead_outreach/lead_cap_days/lead_list_refs - one business one row, provenance as ROW COLUMNS, the identity ladder kgmid > cid > place_id > phone_e164 > name+address, opt_out the campaign desk honours, forget = the DPO duty, LeadsCapped at plan time) + rules.py (the LANES ladder, LANE_BUILT refusals BY NAME - no stub, no pretending; STORE_BOUNDARY facts only) + the CSV importer inside the package (their import_leads/SAMPLE_PREFIX call sites untouched). P1 the OFFICIAL lanes: run_indiamart (IndiaMART's OWN MCP server via the existing app/indiamart.py, one BUSINESS one row, free) + run_places (Google Places through the EXISTING maps tools ONLY - resolve, nearby, place_details bought per place under leads_places_details_per_run=50 and the mapsbill cap, NO second Google client proven by source pin; Nearby's 20-ceiling beaten by place_cells() tiling; MapsCapped mid-list ABORTS with the cap named, mid-details only stops the buying). P2 ENRICH: one bounded crawl-brain pass per kept row's OWN website through the EXISTING scrape stack (SSRF guard, robots gate, 1 req/s/site, 3 pages/site), emails + hostname socials, DNS->MX grades pakka/sadak_tak/galat, NO SMTP probe, ONE billed cheap-brain pick validated against candidates (no model = deterministic rank, pick=rule), fills EMPTY slots only, LEADS_ENRICH_ROWS_PER_RUN=100 refuses at plan time. P3 SCRAPE: the Google Maps PUBLIC LISTING grid (gmaps_parse - every field position a named constant, ids by SHAPE kgmid>place_id>cid, loud tripwire, FACTS ONLY; grid.py zoom ladder + 400-cell ceiling + MEASURED choose_zoom; scrape.py existing fetch stack, 1 s politeness, robots on non-Google hosts) behind a PER-TENANT OPT-IN OFF BY DEFAULT (set_scrape_optin - her act), grid checkpointed per cell (resume continues, DONE resume = zero fetches), block/CAPTCHA hard-aborts naming the vendor, and THE CLAUDE.md RULE TEXT AMENDMENT (public business-listing scrape allowed by the owner's explicit ask of 5 Nov 2026 under walls no session may move; the free card reads CLAUDE.md to prove it - rule_text_amended). P4 VENDOR + SCALE: vendor.py config-gated (LEADS_VENDOR_NAME/_BASE_URL/_API_KEY/_PRICE_PER_ROW_INR/_TERMS_ACK - until she names it the lane is ABSENT and asks refuse naming the config), priced on the card BEFORE the run (estimate over LEADS_VENDOR_RUN_CAP_INR = refused card), ONE call never retried, every row MUST carry its own source_url, 401 aborts without printing the key, bill = vendor-reported cost else the estimate and says which; scale.py store_backend() names sqlite | postgresql honestly, enrich_fanout() over the HOOLA GRAPH (dispatch -> 4 chunks -> the JOIN barrier, <= leads_enrich_fanout_max=4 in flight, writes after the barrier ONE WRITER AT A TIME, serial the default); rules.LANE_BUILT = all five lanes, the plan section 4 ladder COMPLETE. P5 OUTREACH HANDOFF + PROOF: campaign_list is TWO TAPS (first = the CONFIRM CARD creating NOTHING, confirm=true builds), create_campaign re-checks every leads-store copy and an opt_out row NEVER joins the send queue (all-opted-out = a refusal, not an empty campaign); the outreach LEDGER writes at the moment of truth on both desks (worker.send_batches -> campaign_sent via note_campaign_sends, mailbox.send_draft -> email_sent via note_email_sends matched by the row's own email - an address the store never saw records nothing), vocabulary rules.OUTREACH_KINDS/DESKS checked at every write, readable via outreach_log + GET /api/leads/outreach + leads_export action=outreach_log, a forgotten row's events stay (the history is not the person); THE CI LOAD PROOF on the DEFAULT caps: 5,000 rows end-to-end - kept, counted by the day ledger, exported with provenance, handed off with consent False, ledger readable - and a 5,001-row ask REFUSED at plan time with the cap named; leadscard sets v1-v6; tests test_v0540_leads_store/card + test_v0541_leads_official + test_v0542_leads_enrich + test_v0543_leads_scrape + test_v0544_leads_scale + test_v0545_leads_outreach, zero network, fakes at the module boundaries. NOT VERIFIED, said plainly: the engine has answered fakes and fixtures only - no live Google query, no live IndiaMART run, no live vendor, no real WhatsApp/email send; her first live run on each lane is the true confirmation. AEP train so far: HOOLA CORE (P1), HOOLA TRACE (P2), HOOLA GRAPH (P3, interrupt/checkpointers), HOOLA AGENT (P4), HOOLA MIDDLEWARE (P5, server/app/aep/middleware.py), HOOLA RETRIEVE (P6, aep/retrieve.py + aep_vectors: the index()/aindex() dedup flow, the retrievers as Runnables firing the retriever span) - P7 HUB -> P8 the 100% PARITY audit, P9 ADOPT; AEP train so far: HOOLA CORE (P1), HOOLA TRACE (P2), HOOLA GRAPH (P3, interrupt/checkpointers), HOOLA AGENT (P4), HOOLA MIDDLEWARE (P5, server/app/aep/middleware.py), HOOLA RETRIEVE (P6, aep/retrieve.py + aep_vectors: the index()/aindex() dedup flow, the retrievers as Runnables firing the retriever span) - P7 HUB -> P8 the 100% PARITY audit, P9 ADOPT; Previous: v0.682.0: KAAN W6 FIX - the unlock guard's engine seam made honest (owner: "W6 (quotas + retention -> unlocks real voiceprint diarization) -- start" - the first live W6 check on the VPS crashed at kaan/status: limits.voiceprint_ready did ok, why = VE.available() but the pre-existing voiceid engine contract is a PLAIN BOOL available() -> bool (only the kaan engine's EN.available() is the tuple pair) - TypeError: cannot unpack non-iterable bool object, so NOT ONE W6 number surfaced; the W6 suite stayed 195/195 green because its three engine patches assumed the same wrong tuple shape - the tests inherited the bug, the classic seam lesson) - THE FIX: W6 adapts to THEIR lane as-is (the house law: their base kept whole, nothing invented) - limits.py consumes the bool and composes the honest why itself (sherpa_onnx or the CAM++/TitaNet speaker models in voiceid_models_dir are missing), the voiceid lane untouched (main.py feature flag, voiceid service status + mode guard keep their bool), the three W6 test patches healed to the real contract lambda: True, NEW regression test speaking the REAL unpatched contract (isinstance bool + voiceprint_ready returns (False, why) with nothing patched - the test that would have caught the crash), quota + retention paths untouched. Version ritual: ritual_v0682.py swept 0.681.0 -> 0.682.0 (+681) across the test files (version tokens + the pubspec-string pins), pubspec, the console cache-buster stamps (the v0179 law: stamps == APP_VERSION), ZERO registry change (609 stands - W6 FIX adds no tools), ZERO pip; CLAUDE.md current-version line + the Current state bullet, docs/HISTORY.md section, docs/WORKLOG.md task. Server-only deploy = owner's vps-ops dispatch; desktop untouched - old APKs keep working. NOT VERIFIED live: the W6 retest on the VPS rides this deploy (the same single-line check, now past status). Previous: v0.681.0: KALA MANCH - the T5 knowledge-skill catalog family (planned at 0.669.0; the dev chain took 0.669.0 (HOOLA AURA) through 0.680.0 (HOOLA ADOPT) while KALA sat planned - REBASE PROTOCOL, re-slotted on their 00aa1dac9 v0.680.0 tip, their base kept whole, the version layer re-applied coherently 0.680.0/+679 -> 0.681.0/+680, ritual_v0681.py) (owner: "GO" on the google/skills deploy plan, after the READ of github.com/google/skills - Apache-2.0, fork-and-remix sanctioned): the T5 tier beside the four brothers - the knowledge tier. ONE tool `kala` (registry 608 -> 609, v0.680 added no tools), IDEA-ONLY: zero upstream code, zero new pip, zero new keys. FIVE ACTIONS, every answer ONE envelope {schema_version, ok, tool, action, ..., meta{elapsed_ms, backend}, error{code, message, hint}}: catalog (index.json fetched BYTE-EXACT behind a 5-min in-process TTL cache (kala_catalog_ttl_seconds=300), narrowed by a case-insensitive regex over name+description, 25-cap with the honest total_matches, the no-query alphabetical-bias note - the upstream README's own warning; a broken regex degrades to a literal find, never a crash) | read (one SKILL.md by its EXACT catalog name, fetched fresh on every read, 12k cap with the honest truncation note, an unknown name NOT_FOUND naming the catalog - never inferred from the name, the routing rule's law) | references (a skill's references/<file>.md deep-dive derived from its entrypoint and re-allowlisted, 8k cap, a 404 = honest NOT_FOUND, a ../ traversal refused before ANY fetch) | list (the predictable family prefixes - gke-, agent-platform-, google-cloud-solution-, google-cloud-waf-, secops- ... - with the family table, an unknown prefix empty + the table, never invented) | status (zero network: upstream, cache state including the last fetch error, caps, laws). THE LAWS: GET only, forever; EVERY url crosses TWO walls - the house scrape-lane SSRF guard AND this lane's own one-host allowlist (https://raw.githubusercontent.com only, one path shape: index.json | skills/<domain>/<skill>/SKILL.md | .../references/<file>.md - refused by name NOT_ALLOWED; a poisoned catalog entry pointing elsewhere is refused too, cached text is never trusted); the catalog is cached, the documents are NEVER cached (fetching is the normal path, the upstream's own law); NO SKILL.MD SCRIPT EVER EXECUTES server-side - documents are read, never run; text passes operator.browser mask_ids like every scraping surface; ONE network seam (_http_get) every public byte rides - tests monkeypatch exactly that and the suite stays offline; the attribution UA hoola-kala/0.681 (+google-skills catalog; Apache-2.0 remixed; idea-only); kill switch kala_enabled (off = every action NEED_SETUP, honest), default on. prompts.py Kala bullet beside the four brothers. Tests: NEW test_v0681_kala_manch.py (34, zero network, the fake seam pops scripted answers, an autouse fixture keeps the cache cold): envelope shape, status zero-network + cold-cache honesty, kill switch, catalog (regex narrow, case-insensitive, cap+note, no-query bias note, broken regex literal, the cache really caching - second call no seam, TTL expiry refetches, bad JSON = UPSTREAM and told in status), read (byte-exact body + description, unknown name NOT_FOUND never-guess, honest truncation, TOO_BIG, the PAN mask, empty name), references (entrypoint-derived url, 404 = NOT_FOUND, traversal refused pre-network, non-SKILL.md entrypoint refused), list (known prefix, unknown prefix + families, empty prefix), the allowlist (six refusals by name + the house paths accepted + a poisoned catalog entry refused), the SSRF guard wired (loopback + file:// through the real house guard, zero DNS), timeout mapping, unknown action, the attribution tag, purity (no top-level httpx), registry 609 pin, enum pin, APP_VERSION pin. RE-SHIP VERIFICATION in the sandbox: kala 34 + duniya 39 + sandarbh/bhandar 78 + jharokha 27 = 178 in one battery on the swept tree. Version ritual: ritual_v0681.py swept 0.680.0 -> 0.681.0 (+680) across the test files (version tokens + the pubspec-string pins), pubspec, the console cache-buster stamps (the v0179 law: stamps == APP_VERSION), the registry pins 608 -> 609 with the arithmetic note (the kaan_w5 comment-shaped pin healed), the aep1 pin-on-the-pin riding the same replacement, ZERO residual; CLAUDE.md current-version line + the Current state bullet, docs/HISTORY.md section, docs/WORKLOG.md task. Server-only deploy = owner's vps-ops dispatch; desktop untouched - old APKs keep working; no new pip; one new kill switch, default on. NOT VERIFIED live: the first real catalog fetch + SKILL.md read on the VPS - the public upstream is coded to its documented shape and the suite is fully scripted; her first "google ka GKE skill laao" is the live test. Previous: v0.680.0: HOOLA ADOPT - the product's first live lane ON the AEP, P9 of the HOOLA plan (owner: "CURRENTLY HOOLA DONT USE AEP IT NEED USER AUTH" then "CONTINUE"; built as 0.610.0 on the v0.600.0 base - the dev chain took 0.611-0.672 while P9 sat built, REBASE PROTOCOL three times (their v0.670.0 KAAN W6, their v0.671.0 NAAM AUR NAMOONA, their v0.672.0 DOOSRI JAANCH landed mid-push), their base kept whole, the version layer re-applied coherently 0.672.0/+678 -> 0.680.0/+679. THE AUTH LAW the owner named, made real: POST /api/aep/turn/{conversation_id} runs one real turn of HOOLA ON the AEP behind require_key + current_tenant - a signed-in product user or the legacy owner key; anonymous callers refused the moment the server has a key; the conversation must belong to the caller's tenant (_conv_or_404). THE LANE: server/app/agent/aeptune.py (the adoption seam, ZERO new deps, the AEP stays inert) - map_history folds the product history rows into AEP messages (text blocks join, card-only bubbles skip, the yaad law held: the user row saves as a str so exchanges() starts); build_agent compiles aep.create_agent (P4) over hoola_brain_factory (P7 - the production OmniRoute/GLM/Claude brain, imported lazily per call); the default ride is Nudge + Curator (P5 - her words stay hers, tool noise folds), delegate/skills-primer opt-in; chat memory rides the SqliteSaver checkpointer on the conversation thread (P3, the CHECKPOINT-MERGE law); every span lands in the P2 tracer (the run explorer sees the lane root "hoola-aep-turn") and the vault sink joins when aep_trace is flipped; the reply lands in the same conversation + SSE feed (typing on/off, the assistant message sourced "aep") so the phone renders it like any other turn; usage.bind meters the lane; a brain failure fails LOUDLY (502, the detail carries the error) and the typing dots ALWAYS go away. THE PRODUCTION LOOP IS UNTOUCHED - run_turn keeps serving every existing client; this lane is opt-in per call, old APKs keep working, the registry stays 608 (no tools, no flags from the lane), voice untouched, Mera PC freeze respected; deploy is the owner's dispatch. Tests: NEW test_v0610_hoola_adopt.py (15, zero network, the brain injected never the live llm): map_history shapes, the default ride, the end-to-end turn (reply + handles), history seeding, chat memory across two turns through the checkpoint, the tracer root + run_id, the vault sink flip law, the route auth (401 anonymous / 404 foreign conversation), the route end to end (rows land, SSE carries the turn), the failure lane, the inertness probe (fresh interpreter: zero threads/env/files - the P1 law re-run on the adoption seam), the version pins. Previous: v0.672.0 DOOSRI JAANCH (owner: the second deep audit - "NOW AGAIN GO TO DEEP IN HOOLA AI AND CHECK ... FLAWS ... SMOOTHNESS, CONFUSION, HALLUCINATION, PERFECTION, CONSISTENCY, PERSISTENCY, RELIABILITY" -> 37 flaws found -> "GO WAVE 5" ... "GO WAVE 8"; the four waves were built as 0.663-0.667 and re-versioned 0.665-0.668 while other sessions took 0.663-0.671 (STUDIO JAANCH, ASLI SAMAY, JHAROKHA, KAAN W5, PREMIUM STUDIO, DUNIYA, HOOLA AURA, KAAN W6, NAAM AUR NAMOONA) - REBASE PROTOCOL, all kept, shipped together as ONE release; the wave stories follow): v0.668.0 SAAF SCREEN (owner: "GO WAVE 8" of the second deep audit - smoothness on her screen; built as 0.667): a step cut by the turn's time limit says so on its card (no spinner for ever); a corrected reply goes out once (only the correction line is sent and saved - it showed twice on the phone); the typing dots are refreshed on the clock while a turn really runs (a busy turn was never "idle", so they vanished at 75 s); the "Ek second..." line is a placeholder on the phone (removed by the real reply, never spoken, never a chat heal); an event that reaches the live stream late is read back from the database in order instead of dropped; the chat history is read off the event loop (5,000 rows froze the whole server for a moment). Previous: v0.667.0 SAHI JAGAH (owner: "GO WAVE 7" of the second deep audit; built as 0.665): an outside-channel chat (WhatsApp / Telegram / Slack / Teams) is never "the chat she is in" (mail alerts and browser answers no longer go out on Telegram); a reminder / routine / briefing set on a voice call belongs to the chat behind it; one in a deleted chat moves to the chat she is in; medicine / bill / birthday reminders are spoken on a call, ring her, say late as late and keep their day; a monthly repeat keeps its own day (anchor_day: 31 Jan -> 28 Feb -> 31 Mar); a wake report or routine holding the chat never swallows her new message (she waits her turn); "server dobara chalu hua" only after a real restart; a long text in a tool result is shortened in place so every key after it survives. Previous: v0.666.0 KAAM EK BAAR (owner: "GO WAVE 6"; built as 0.664): the late-reminder quiet hours really read her time zone (my v0.662 TypeError, swallowed - a late reminder still rang at 3 am); a timed-out tool is said to be maybe still running and a send / submit / order is never repeated unchecked; a send the phone retries after a restart runs once (turn_inbox.seen); routines, Dobara, edits and form answers ride the turn inbox (TurnInbox.actor); a reply given before the chat lock stays out of the model history while another turn runs; kaam_status stop never runs in parallel; a channel reply is marked sent only after it went (3 tries); a reminder is advanced before it is said. Previous: v0.665.0 SACH KA HISAAB (owner: "GO WAVE 5" of the second deep audit; built as 0.663 - their STUDIO JAANCH took 0.663.0 and their ASLI SAMAY 0.664.0, REBASE PROTOCOL twice, all kept - Hoola never says something false): a tool result with ok False / status failed or refused is a failure (santosh.tool_failure, voice._fails) - a failed render no longer reads as done; every claim in a reply is judged against a tool of ITS kind (mail needs a send tool, not a reminder; sub-agents / browser / PC / MCP back any) and a true report of earlier work ("haan, bhej diya tha", a wake report, her "gaya kya?") is backed by the last 7 days of this chat's tool log instead of being called a lie; the tool-less quick lane never says done and hands any request for work to the running job; a call's "mail bhej diya" after a failed / read-only / unrelated tool is corrected (a running tool count replaces the capped list length); future / offer words excuse a claim only before it, "PDF / website bana diya" and "order place kar diya" are claims; a call job that only talked is not relayed as "ho gaya"; the server's own plan closes as blocked_on_her on a question and failed on a failure, never all-steps-done; the step cap always says the job is unfinished (outcome partial) and an empty ending after failed tools never says "Kaam ho gaya"; a goal round keeps a stuck outcome; done = verified counts only rows made since the goal began; a figure deep in a tool result backs the reply; facts Hoola guessed are listed apart from hers, dated, to be checked with her first. Previous: v0.671.0 NAAM AUR NAMOONA (owner: "when website show preview it must show some dummy value not empty data ... before building give a self Hoola AI defined website brand name - like Lovable does"): (1) a site asked for without a business name is named BEFORE anything is built (site/service.py brand_name: her own words when they name the business, else one quick model call for a short brandable Indian name + tagline, else a house fallback; facts.name_by=hoola, view name_by; no more "what is the name?" question); the Web Studio (webstudio.js) shows "Named by Hoola" + Rename, and a rename before the build becomes the business name on the pages; (2) the preview never shows a yellow [phone] / [price]: the model writes data-eg samples and build.samples() shows a believable sample for every blank (house samples by label otherwise), on built pages and the live canvas, marked as a sample - it stays a blank underneath, so the launch check still waits for her real value; 6 tests (built as 0.670; their KAAN W6 took 0.670.0 - REBASE PROTOCOL, both kept). Previous: v0.670.0 KAAN W6 - HISAAB AUR SAFAI (built as 0.667.0; their console-stamp + PREMIUM STUDIO took 0.667.0, DUNIYA MANCH 0.668.0 and HOOLA AURA 0.669.0 while W6 sat built - REBASE PROTOCOL, rebuilt fresh on their 0d89877bc tip, ALL their work kept intact, the version layer re-applied coherently 0.669.0/+675 -> 0.670.0/+676, ritual_0670.py) (owner: "W6 (quotas + retention -> unlocks real voiceprint diarization) -- start" on the kaan plan - Wave W6 of the WhisperAI feed, after W0 v0.601.0, W1 v0.613.0, W2 v0.619.0, W3 v0.639.0, W4 v0.659.0 and W5 v0.666.0 proved live on the box): the accountability layer her audio runs on, then the unlock it buys. NEW server/app/kaan/limits.py - month_usage (finished kn_ duration_s per calendar month, per tenant; a live session's seconds count ONCE, by the kn_ row its stop writes - never double-counted), check_quota_file (the ffprobe estimate runs BEFORE the engine spends; duration 0.0 - ffprobe absent - never blocks, the finished row still counts honestly), check_quota_live_start (no new session once the cap is hit), retention_sweep (kn_ rows past KAAN_RETENTION_DAYS go - pinned rows survive, the column W0 baked for exactly this; live sessions past the cutoff go WITH their spine PCM files; the last sweep is surfaced in status), voiceprint_ready (the unlock guard). NEW server/app/kaan/voiceprint.py - diarize=voiceprint at transcribe time: DI.cut_turns cuts the timeline, each turn's audio slice is embedded ONCE and scored against HER enrolled Awaaz Pehchaan prints through voiceid.service (the identify threshold+margin law, nothing invented, nothing stored twice); sure matches get the person's name, unsure turns stay unnamed - no guessing; a technical failure degrades to an honest note and the transcript survives; the guard refuses BEFORE the engine burns a transcription (KAAN_VOICEPRINT=1 AND KAAN_RETENTION_DAYS>0 - voiceprints are biometric, matching audio with them is only allowed where retention is bounded). pause_turns also rides fresh audio now (the W1 law on new recordings). WIRING: service.transcribe_file grows the diarize param (quota before the engine, voiceprint guard before the engine, speakers stored into row.speakers + named in the note); live.start refuses at the cap; api.py transcribe grows the diarize Form field (the honest 400 carries the service's own words); kaan_tools schema grows the diarize enum (18 actions UNCHANGED, registry stays their 608 - W6 adds dials, not tools); worker.py kaan_jobs (daily throttle, mirrors eventlog_jobs) calls the sweep. CONFIG: kaan_quota_audio_min=0, kaan_retention_days=0, kaan_voiceprint=False - all default OFF, her box keeps everything until she says otherwise. ZERO new tables, ZERO new pip. The W6 plan's third leg - a fresh read of whisperai.com's live prices (7 Nov 2026): Free $0 (5 min/mo), Premium $14.99/mo (120 min, rollover to 360), Business Pro $24.99/mo unlimited, Enterprise $75/mo (5 seats), Developer API $99/mo (10k API min); their single-file cap 10 h, live sessions 12 h, MCP connector is a paid-tier feature - kaan's answer stays local-first: no per-minute meter at all unless SHE sets the cap, same 5 GB ceiling, 2 h live sessions, MCP/HTTP doors free, and the one thing none of their tiers sell: speaker names from voiceprints she enrolled and owns. Tests: NEW test_v0667_kaan_w6.py (26, the file name keeps the first-build number, the v0.566 precedent; zero network, zero torch, scripted engine + the seams - _duration_of, VP._people, VP._identify, VS.pcm16k - the W5 house-safe patching lesson): quota (default unlimited, finished-rows-only metering, over-cap refusal naming the reset date, within-cap pass, ffprobe-absent honesty, live start at cap + counted once at stop), retention (0 = honest no-op, old unpinned swept + fresh kept, pinned survive, spine files removed, last-sweep block, worker daily throttle), voiceprint (off refuses naming the switch, needs bounded retention, needs enrolment, names sure turns only + persists + notes, technical failure keeps the transcript, pause_turns fresh, unknown value refuses), surfaces (status blocks, HTTP diarize param + honest 400, pinned in rows, registry/enum untouched, MCP door rides the same KS, no new tables, APP_VERSION). Green on the merged tree: kaan chain W0-W6 (153) + their DUNIYA MANCH + AURA suites re-run as the merge proof; the soorat tone red is WORKTREE-PROVEN pre-existing (_TonedCall.conv - not W6's lane). ritual_0670.py swept the version layer 0.669.0 -> 0.670.0 (+676) across the test files (their 0.669.0 layer, my built-as 0.667.0 file included), ZERO residual; CLAUDE.md + HISTORY + WORKLOG mirrors on top of their entries. Server-only deploy = owner's vps-ops dispatch; desktop untouched - old APKs keep working; Mera PC freeze respected. NOT VERIFIED live: the first quota/retention/voiceprint checks on the VPS - the bake block rides the deploy. Previous: v0.669.0 HOOLA AURA (owner: "a perfect animated hoola brand shade in background - smooth, soft" -> preview -> GO): the Web Studio home (webstudio.js / webstudio.css) gets four heavily blurred light pools in the house gradient (peach #FFD9A8, saffron #FF9A3C, magenta #C055F5, violet #8B6CFF) drifting on their own 26-38 s loops behind the headline, masked to fade out before the cards; dimmer in dark (.22), still under reduced motion, smaller on phones, never takes a click, home only; 2 tests incl. a browser walk light + dark. Previous: v0.668.0 DUNIYA MANCH - the T4 keyless-public-web family (built as 0.667.0; their PREMIUM STUDIO took 0.667.0 while T4 sat built and pushed - REBASE PROTOCOL #13, both kept, the version layer re-applied coherently 0.667.0/+673 -> 0.668.0/+674, ritual_0668.py on top of their tip) (owner: 'T4' - the fourth and last tier of download/HOOLA_MCP_FEED.json; the ladder was three for three after JHAROKHA v0.665 - T1 SANDARBH, T2 BHANDAR, T3 JHAROKHA - and this closes it): the no-login / no-key public-web rows land backend-only as ONE GET-only tool `duniya` (registry 607 -> 608), IDEA-ONLY from the modelcontextprotocol/servers fetch reference ('Web content fetching capabilities for LLMs') + the no-key public-API rows the feed's T4 tier named (Wikipedia / Open-Meteo / Hacker News / Frankfurter / Free Dictionary / arXiv), zero upstream code, zero new pip (httpx is the house's), zero new keys. EIGHT ACTIONS, every answer ONE envelope {schema_version, ok, tool, action, ..., meta{elapsed_ms, backend}, error{code, message, hint}}: fetch (one public http(s) url -> readable text, scripts and styles stripped by a stdlib parser, the final url after redirects told honestly, an honest truncation note at the 12k cap, TOO_BIG past the 500k download cap, non-text content-types refused naming jharokha) | wikipedia (search + the top hit's summary in any language edition; the courtesy summary is never fatal) | weather (Open-Meteo geocode + forecast, WMO codes named in words, days clamped 1-7) | hn (Algolia story search with the story_* fallbacks) | currency (Frankfurter latest or by date; the amount folded into the answer told both ways - rate AND result) | dictionary (meanings, definitions capped 2, the 404 = NOT_FOUND honesty) | arxiv (the Atom export parsed with the stdlib, no new pip) | status (zero network: the backends, caps and laws). THE LAWS: GET only, forever - never POST/PUT/DELETE, never an Authorization header, never a cookie; the named backends' urls are code constants and EVERY url - the free fetch one AND the constants - goes through the house's own scrape-lane SSRF guard (public hosts only; loopback / RFC1918 / link-local / metadata never fetched); ONE network seam (_http_get) every public byte rides - tests monkeypatch exactly that and the whole suite stays offline; text passes operator.browser mask_ids like every scraping surface; kill switch duniya_enabled (off = every action NEED_SETUP, honest). Config: duniya_enabled=True. prompts.py Duniya bullet beside the three brothers. Tests: NEW test_v0667_duniya_manch.py (39, zero network, the fake seam pops scripted answers): the envelope shape, status zero-network, the kill switch, fetch (strips scripts/styles, json pretty, redirect final url, honest truncation, TOO_BIG, non-text refused, the PAN mask riding the text, the guard REALLY wired between the ask and the web), the SSRF guard itself (loopback / metadata / file:// / ftp://), wikipedia (search+summary in order, no-results NOT_FOUND with no courtesy call, summary failure not fatal, input laws), weather (geocode+forecast, WMO words, the clamp, unknown place), hn (shape + fallbacks + the hn_url built), currency (rate/result both ways, the historical date in the path, input laws, missing pair), dictionary (capped definitions, 404 = NOT_FOUND), arxiv (Atom parse, empty feed, broken Atom), upstream timeout mapping, purity (no top-level httpx), registry 608 pin, enum pin, APP_VERSION pin. Version ritual: built as 0.667.0 (scripts/ritual_0667.py, 217 files swept) and re-versioned 0.668.0 on their PREMIUM STUDIO base (scripts/ritual_0668.py: the suites + pubspec + the console cache-busters swept 0.667.0 -> 0.668.0, ZERO residual), registry pins 607 -> 608 with the note, CLAUDE.md current-version line, docs/WORKLOG.md Task 40, docs/HISTORY.md section. Server-only deploy: old APKs keep working; no new pip; one new kill switch, default on. THE FEED'S TIER LADDER IS FOUR FOR FOUR: T1 SANDARBH (reference) v0.586/0.590, T2 BHANDAR (local core) v0.618/0.620, T3 JHAROKHA (local browser) v0.664/0.665, T4 DUNIYA (keyless public web) v0.667. Previous: v0.667.0 PREMIUM STUDIO (owner: "GO THROUGH FIGMA FOR DESIGN MAKE A WEB PANEL MORE PREMIUM ... SHOW ME THE DESIGN FIRST" -> the Figma file 'Hoola Web Studio - Premium redesign' (landing, workspace building live, chat finished, type & colour) -> "GO BUILD THE DESIGN"): the Web Studio rebuilt to that design - one serif (Literata) for the 52 px headline and everything Hoola says, the sans for everything she taps, JetBrains Mono for timers and counts; warm paper + ink palette, violet only for working now, green for done, red only for LIVE; weights stop at 600. Home: 'New - Watch your website being built, live' eyebrow, the serif headline, the ask card with Use my old site / From a screenshot and a dark round send, a dark New website button with Cmd/Ctrl K (a real shortcut from anywhere in the Studio), recent sites with their status under the name, site cards with a tint and 'Edited N ago'. Workspace: mark / name / status, 'Every change is saved as a version', dark Publish; her request opens the chat; Hoola's name + time above each reply; the live work card (what is being built, step n with its own %, the whole clock, progress, every step's own time and count, N parts writing at once, Pause); after a build 'Worked for' + 'Version N is ready' + Go live + three next steps; the live canvas gets a red LIVE tag, page pills and a browser frame. No behaviour removed; light + dark. Previous: v0.666.0 KAAN W5 - BOLI KE TEEN DARWAZE (built as 0.663.0; their STUDIO JAANCH took 0.663.0, ASLI SAMAY 0.664.0 and JHAROKHA MANCH 0.665.0 while W5 sat built and pushed - REBASE PROTOCOL twice, rebuilt fresh on their 7a47d9952 tip, ALL their work kept intact every time: the first rebase had silently dropped their main.py side (sites_live + the live-build routes) and THEIR OWN suite caught it on re-run (ImportError: sites_live) - main.py rebuilt from their file with exactly two additions, my APP_VERSION story and the kaan router mount; the version layer re-applied coherently 0.663.0/+669 -> 0.666.0/+672, ritual_0666.py, ZERO residual) (owner: 'W5 - MCP + API + extension audio' on the kaan plan - Wave W5 of the WhisperAI feed, after W0 v0.601.0, W1 v0.613.0, W2 v0.619.0, W3 v0.639.0 and W4 v0.659.0 proved live on the box): one brain, three doors. NEW server/app/kaan/api.py - the REST door (the drive/forms/photos factory pattern: _kaan_router(require_key, current_tenant), mounted beside the quicklane): /api/kaan/status + list + search + vocab CRUD + transcribe (upload) + per-transcript get / export (download=1 = raw bytes with Content-Disposition) / style / minutes / diarize / to_gyaan + live start / chunk / stop / get / list - the SAME KS functions the kaan tool calls, the SAME gates (audio ingest rides kaan_audio; reads gate-free by the W1 law), tenant-scoped by the SAME auth, so her paired browser extension and console reach kaan over plain HTTPS. NEW server/app/kaan/mcp_server.py - the MCP door (stdio, line-delimited JSON-RPC 2.0, protocol 2025-06-18 - the wire the house MCP client aep.mcp speaks; zero new pip): exactly ONE tool `kaan` with the 18-action enum (the house law travels with the door - actions, not tools), dispatch THROUGH agent.kaan_tools._sync so the MCP door can never drift from the tool door, actor=owner by construction (it runs on her box with her env - pairing an MCP client here is pairing a device), honest refusals come back as isError content (never a crash), imports lazy (no kaan_tools/gyaan/engine at module load - the inertness law). Run: python -m app.kaan.mcp_server (HOOLA_TENANT env picks the tenant). THE EXTENSION AUDIO: desktop/ext/hoola-extension grows its ears (v1.9.0 -> 1.10.0, manifest +tabCapture +offscreen) - MV3 service workers cannot touch MediaRecorder, so NEW offscreen.html/offscreen.js consumes the tabCapture streamId, records audio/webm in 2s slices and POSTs each to /api/kaan/live/{sid}/chunk with the device Bearer; background.js grows captions-start/captions-stop (getMediaStreamId in the click's gesture context, offscreen createDocument with reason USER_MEDIA, the session lifecycle rides the SAME /api/kaan/live endpoints); popup grows the Live captions section (start/stop, captions_tail poll every 3s, the transcript link on stop). REGISTRY 606 -> 607 IS THEIR JHAROKHA GROWTH, NOT W5'S - W5 still adds transport doors, zero new actions (the kaan enum stays 18, the tool description untouched inside its 1200-char diet). status() grew the api+mcp+ext block (three doors named, MCP run line included). Tests: NEW test_v0663_kaan_w5.py (zero network, zero torch, scripted engine): HTTP transcribe end-to-end + gate-off 400 with the honest line + export download bytes == the service text + style/minutes/diarize/to_gyaan over HTTP + vocab CRUD + 401 without a key + tenant isolation + live start/chunk/stop over HTTP + the status route; MCP initialize/tools-list (1 tool, 18 actions)/tools-call (status, export srt, to_gyaan idempotent, unknown action -> isError)/unknown method -32601/parse error -32700/purity (no httpx/requests in either new module; importing mcp_server loads no engine); extension source pins (manifest permissions, offscreen MediaRecorder + chunk POST, background message kinds, popup captions_tail poll); APP_VERSION 0.666.0. Previous: # v0.664.0 ASLI SAMAY (owner: "WHEN WEBSITE IS BUILDING CAN USER SEE REALTIME WEBSITE BUILD VISUALLY" -> "NOT JUST A PREVIEW A REAL TIME BUILDING" -> "GO R1 TO R5"): the website is built in front of her - R1 every section Opus writes (page parts, look tops, fix rounds, changes) is STREAMED (same request, same tokens; `site/stream.py` pulls the half-written html / css out of the arriving JSON into a live slot, a retry clears it, the saved section is checked exactly as before) and GET /api/sites/{ref}/live sends only the added characters; R2 the Studio's live canvas = the real site (preview `__build/`) with every section in a slot and the unwritten ones as places they will grow into, each section growing word by word with a cursor and a 'Writing: Menu' tag, half-written code never runs (scripts / handlers / javascript: links removed, sandboxed frame, `assets/hoola-build.js`), Follow keeps the part being written in view, a page strip; R3 Code shows each part typing out, parallel parts each in a tab, 'Designing this section…' while Opus thinks; R4 the three looks grow side by side (`__build/__look/<i>/` in each look's own colours) and the chosen look stays on screen through the build; R5 a change to a built site (her chat, a fix round) switches the screen to the live build at its first word, then 'New version vN is ready' + Before / after (preview `__v/<n>/`). Switch SITE_LIVE_STREAM. Previous: v0.664.0 ASLI SAMAY (owner: "WHEN WEBSITE IS BUILDING CAN USER SEE REALTIME WEBSITE BUILD VISUALLY" -> "NOT JUST A PREVIEW A REAL TIME BUILDING" -> "GO R1 TO R5"): the website is built in front of her - R1 every section Opus writes (page parts, look tops, fix rounds, changes) is STREAMED (same request, same tokens; `site/stream.py` pulls the half-written html / css out of the arriving JSON into a live slot, a retry clears it, the saved section is checked exactly as before) and GET /api/sites/{ref}/live sends only the added characters; R2 the Studio's live canvas = the real site (preview `__build/`) with every section in a slot and the unwritten ones as places they will grow into, each section growing word by word with a cursor and a 'Writing: Menu' tag, half-written code never runs (scripts / handlers / javascript: links removed, sandboxed frame, `assets/hoola-build.js`), Follow keeps the part being written in view, a page strip; R3 Code shows each part typing out, parallel parts each in a tab, 'Designing this section…' while Opus thinks; R4 the three looks grow side by side (`__build/__look/<i>/` in each look's own colours) and the chosen look stays on screen through the build; R5 a change to a built site (her chat, a fix round) switches the screen to the live build at its first word, then 'New version vN is ready' + Before / after (preview `__v/<n>/`). Switch SITE_LIVE_STREAM. Previous: v0.663.0 STUDIO JAANCH (owner: "go to every section of web studio in hoola web console check every section is fuctional or not end to end"): every Web Studio section walked in a real browser (home, all websites, search, starred, templates, Build + Plan, three looks, chat, preview + edit mode, Code, Cloud, Integrations, Health, Settings, History, Publish, project menu) and what did not work is fixed - Code > Download ZIP / React + Vite now saves the zip to her computer (new GET /api/sites/{ref}/download, `service.export_bytes`; before it only filed it in her Hoola files); Publish > Connect your domain now DRAWS the DNS records it made (they only went to the chat), with 'Haan, add them for me' (her tap with the plan's hash), 'I've added them · check' (three public resolvers) and Undo; Publish no longer gets a 404 for every site without an old site (/moves?quiet=1); History marks the version that is really live after a restore; Health no longer opens with ': 30 din' for an unnamed site. Previous: v0.662.0 KAAM SAAF (owner: "GO" on Wave 4 of the deep audit - coworker polish 9-11, 26-30): every worker slot runs guarded (`worker._slot`: one recurring failure no longer skips reminders / follow-ups after it); a reminder fired 20+ min late (downtime) says so ("der se - yeh 9:30 PM ka tha") and never rings her in the night; a Stop tapped while a turn prepares ends it before anything runs (`_STOP_AT`, STOPPED_IN_PREP); a dead Google sign-in backs off for the background watchers (30 min -> 2 h -> 6 h per token, her own chat ask always retries) and she is TOLD once a day that mail alerts / meeting nudges stopped; the honesty check knows "place / transfer / set / fix ho gaya", "chala gaya", "pahunch gaya", "appointment le liya" and nudges an unbacked "yaad dila dungi"; the stuck-job notice no longer promises a check nobody makes (names a server restart since it last moved); the Kaam list drops a turn that only started a tracked job, read-only questions and routine / goal prompts, and shows the cards waiting for her tap; an outage error is said once per 30 min by background turns (her own turn always hears it) and a 3-day-old card is no longer call news. Previous: v0.661.0 YAAD SAHI (owner: "GO" on Wave 3 of the deep audit - memory accuracy 19-22, 24, 25): memory masks ONLY secret numbers (pii.mask_sensitive: Luhn card, Verhoeff Aadhaar, bank account next to its word, PAN, CVV) - her customers' phone and order numbers stay in summaries, the search index and call news; a fact update carrying a number (new address + PIN code) is kept and replaces the old fact; her PINNED fact changes in place and stays pinned (yaad.update_pinned, both the extractor and remember); "yaad rakhna X" twice = one fact; a standing preference / correction is global (never fenced to the chat it was said in) and replacing a fact retires its same-meaning copies in her other Sessions (retire_copies); memory search applies the Session fence + incognito IN the query (an old memory is no longer lost behind 5,000 newer rows of other chats) and the diary's call-receipt scan is bounded to its days; a second fact inside the 15 s gap waits its turn and a short line about herself ("Mera naam Riya") counts. Previous: v0.660.0 CALL KI YAAD (built as 0.658; their SAAF DIKHE took 0.658 and their KAAN W4 took 0.659, both kept; owner: "Wave 2 (call memory and smoothness): 3, 4, 13-18, 23 -- WORK ON IT NOW"): a call on its own record reads the CHAT it came from (yaad.voice_block: focus, checkpoint, summary, exchanges, facts - plus the record's own words; the call brain gets the chat's checkpoint + facts by meaning); the small 4.5k brief gives each part its share and keeps a checkpoint's HEAD and its pending TAIL; a memory part that misses the 2.5 s wait is NAMED to the brain (check with a tool, never guess) and kept for the next ask (job state never served stale); a "still working" check-in no longer keeps Gemini connected (it parks); a second ask while the first runs goes to a hidden SIDE record with every tool (never the no-tools quick lane), its words + answer copied into the call record; a second santosh_kaam in the same turn carries only its own part; a card the call's own brain ask made is remembered for her tap but not told twice; news still queued (phone away / hang-up / hold) is saved for the next call and a hang-up inside the first wait keeps the job's result; capped news waits for a gap in speech (never over his voice; 3x the cap on a noisy line). Previous: v0.659.0 KAAN W4 - BOLI SE KITAAB (built as 0.656.0; their KAAM DIKHE took 0.656.0, PAKKA KAAM took 0.657.0 and SAAF DIKHE took 0.658.0 while W4 sat built - REBASE PROTOCOL twice, rebuilt fresh on their 2361b78a7 tip, all kept, their story chain verbatim) (owner: 'W4 (exports + translation + Gyaan unlock)' on the kaan plan - Wave W4 of the WhisperAI feed, after W0 v0.601.0 baked live, W1 v0.613.0, W2 v0.619.0 and W3 v0.639.0 proved live on the box): deterministic exports of a STORED transcript + the gyaan unlock, nothing invented. NEW server/app/kaan/exports.py renders srt/vtt/txt/json as PURE serializations (zero deps, zero network - port law + inertness law): SRT/VTT cues are exactly the W3 subtitles lines (ONE code path - captions and exports always agree; word rows split on the W2 phrase rule, no-word rows wrap at 12 words, text-only rows get one honest cue), timestamps hand-rolled with the rounding spill carried up, TXT is the stored text verbatim, JSON is the full row (text + segments + word timings) with sort_keys so the bytes are deterministic; unknown format refuses with the full list, an empty row refuses honestly - all READ-ONLY, gate-free by the W1 law (no audio ingest, the text is already hers). to_gyaan (W4): the transcript's own words go into her gyaan corpus via gyaan.ingest.add_note - the content-hash ref makes it IDEMPOTENT by construction (re-adding the same transcript says "same", never a duplicate doc), the import is lazy so kaan never loads gyaan unless used; nothing generated - gyaan_khojo finds the words now. TRANSLATE was wired at W0 (schema enum -> _sync -> engine ladder, turbo refuses) - W4 proves it end-to-end with a captured engine, the row records task="translate", and the honesty is pinned: whisper translates X->English ONLY, a stored row without audio cannot be re-translated (local-first: W0 keeps no audio). THE GATE MAP: no new switch - export is a read (staff ok like style/get, customers still refused at the door), to_gyaan writes tenant data (owner/approved-only); registry 606 UNCHANGED - actions, not tools; the kaan actions enum grows 16 -> 18 (+export/to_gyaan, the newest-enum precedent) and the description sits inside the 1200-char diet (1190 chars) so W4 stays visible to the agent. status() carries the exports block (four formats + the gate-free + translate honesty line). New W4 strings are ENGLISH (owner instruction); older kaan strings keep the house Hinglish - no churn on shipped lines. Tests: NEW test_v0656_kaan_w4.py (18, zero network, zero torch): SRT/VTT cues == the subtitles lines with comma/dot milliseconds + determinism, TXT verbatim, JSON round-trip + sort_keys determinism, wrapped path + one-cue text-only row + empty-row/unknown-format honest refusals, service export on a stored row with the gate OFF (gate-free read law) + tenant isolation, to_gyaan added/idempotent("same")/honest note/empty refused, translate end-to-end (engine captures task=translate, row records it) + turbo refusal pin + schema enum, actor lanes (staff export ok / staff to_gyaan refused / customer out / owner to_gyaan ok), registry 606 + enum 18 + diet, status exports block, exports.py purity (no httpx/requests/openai/socket/subprocess) + gyaan laziness, APP_VERSION 0.659.0. Neighbours green on the same tree: kaan W3 23 + W2 18 + W1 20 + W0 25 (enum pins healed to the 18-action arithmetic). Ritual: this sweep re-titled the version layer to 0.659.0 (+665), pubspec 0.659.0+665, CLAUDE.md + HISTORY + WORKLOG mirrors. NOT VERIFIED live: the first export + to_gyaan on the VPS - the bake block rides the deploy. Previous: v0.658.0 SAAF DIKHE (owner screenshots: the site chat showed only three dots while Hoola worked, no timing; and the Studio sidebar had no project menu - "IT SHOULD BE SAME AS LOVABLE"): (1) the site chat now shows the turn's real tool steps live (the timeline's step events: label, its own start and end) under "Working · step N" with a timer ticking every second, and every answer keeps "Worked for 42s · 3 steps" with each step's own time; a reload mid-answer picks the live feed up again. FOUND while proving it: a brand-new site chat starts with Hoola's greeting, and the answer check took that greeting as the answer and stopped waiting at once - now only a reply AFTER her own newest line counts. (2) the Studio sidebar like Lovable: Home, Search, All websites, Starred, Templates; Starred + Recent projects each with a menu (Open, Open in new tab, Rename, Add to / Remove from starred, Delete), the same menu on every project card and beside the project name in the workspace, search on All websites; rename = new PATCH /api/sites/{id} {name} (only the list name changes), delete = the existing server delete (a live site is taken off the internet first), stars kept in this browser. Tests: test_v0655_kaam_dikhe.py (+3: rename route, menus + search + chat timer in a browser, live steps -> Worked for with real step times). Previous: v0.657.0 PAKKA KAAM (owner: "Wave 1 (lost work, money): 1, 2, 5, 6, 7, 8, 12 --- FIX THIS" after the deep audit): a restart mid-turn RESUMES the turn (turn_inbox.started_at = the turn really began; answered only by a FINAL reply - a tool step is not an answer; the re-run is told what was done and never repeats it) and a message queued behind another turn is no longer dropped by that turn's reply; an approval card is CLAIMED with one conditional update before its action runs (a second tap = "Already", never a second order) and a run cut by a restart says "pakka nahi pata" instead of "kuch order nahi hua"; run_turn failures are stamped (`santosh.turn_failed_since`) so a failed wake turn sends the honest line with the result link and a failed routine is recorded failed and never spoken as done; a finished job is reported ONCE (the row's own wake turn is no longer "her busy turn", an enqueued report marks the state told); a timed-out turn warns a step may be half done. Previous: v0.656.0 KAAM DIKHE (owner screenshot: the looks panel said "3 looks bana raha hoon 0%" for minutes - "IT MUST SHOW SAME DETAILS LIKE A LOVABLE SHOW"): every real stage of a website job is now a timed step (`site/activity.py`, a small JSON log beside the site's files, written under a lock by the looks' threads): planning the designs, the photos (n/total, running beside), the top of every look (n/total), screenshots, every page for the looks (n/total with the page and part being written), the build's design kit, every page (n/total), checks, fixes, ready - each with its own start and end, a step still running has no end, nothing estimated. The Studio's work panel shows "Working for 2m 14s", the current step's progress and the whole step list with ticks, spinners, counts and times ticking every second (server clock corrected for the screen); the site chat shows the current step + timer and the steps so far, and after the job "Worked for 6m 12s · 9 steps"; polls every 2 s and updates the steps in place (the preview is not reloaded), an opened step list stays open. The build's Hinglish step lines still go to her chat; the Studio shows them in English. Tests: test_v0655_kaam_dikhe.py (3) + the browser walk. Previous: v0.655.0 SACH KA PEHRA (built as 0.654; their BHEJA TO DIKHA took 0.654.0 - both kept) - a "done" reply is checked against what the tools REALLY did: a card / draft waiting for her tap is never "bhej diya / order kar diya / paid" (corrected to "card bheja hai, aapki haan se hoga"), read tools are known by name (47 used to count as actions), only the claim's own clause can excuse it, the missing Hinglish + English claim phrases are known, and on a call Gemini's own unbacked "ho gaya" (no tool, no news just relayed) is corrected out loud at the next pause; v0.654.0 BHEJA TO DIKHA (owner screenshot: pressing send in the Web Studio plan chat "just does nothing"): a plan change is a full Opus/Haiku spec rewrite (up to a minute) and the plan chat showed NOTHING while it ran - no line, no working sign, the text sat in the box - so it looked dead; the home ask box did the same while a plan was written. Now her line lands in the chat at once with "Updating the plan · about a minute" and working dots, the box clears, and on a failure the reason shows in the chat and her words come back to the box; the home box shows "Writing your plan from your words" / "Starting your website" under it and keeps her words on a failure. A browser test slows the revise call and fails on the old code; it also checks a workspace chat line lands at once. Previous: v0.653.0 SACHCHA NATIJA (built as 0.652; their STUDIO BAR SEEDHA took 0.652.0 - both kept) - every task's state is told truthfully on every surface: a turn that hits its time limit or crashes records "stuck" (work diary + Kaam list) and a call never reads an earlier ask's "done" for it; the job watch now understands game, CAD, WhatsApp campaign and coding-task status words (they were silent); a stuck job reads "atka hai" everywhere Hoola looks and a dead one is said once after 2 days; a long call ask says "abhi bhi kar raha hoon" every 2.5 min (3 times max); v0.652.0 STUDIO BAR SEEDHA (owner screenshot: pressing Plan on the Web Studio home dropped the send button to a new line): the ask row stays one line in both modes - the mode note shrinks with an ellipsis instead of wrapping the row, the Plan note is as short as the Build one; a browser test holds the button still at 1240 and 1440 px (it failed on the old code: 42 px drop). Previous: v0.651.0 JAWAB MIL GAYA (built as 0.650; their Web Studio took 0.650.0 - both kept) - a live call learns, quietly, the moment she answers a card on her phone (approve / send / reject): any still-unspoken note about that card is dropped, the call gets a silent note never to ask about it again, and every call brain ask reads the cards that REALLY still wait (their own latest state), so Hoola never says "card par approve kijiye" for a card she already tapped; also a DB read on the event loop removed from the call memory step; v0.650.0 HOOLA WEB STUDIO (built as 0.649; their SACH MEIN ROKO took 0.649.0 - both kept) (owner: "I WANT IT LIKE LOVABLE AND EMERGENT ... A SEPERATE WEB DEVLOPEMENT PANEL WITH ITS OWN SIDE BAR" -> the prototype -> "PERFECT"): the website builder is its own full-screen app at /console/web (static/console/webstudio.*) with its own sidebar; the console's Web Development row opens it and the old in-console panel (webdev.js) is gone. Home: one line + Build | Plan. Build makes the site and accepts its plan at once; Plan shows the architect's plan written from her words as a document, changed in the chat, built only by "Build this plan" (the hash she saw). Either way she first gets THREE FULL LOOKS: every other page of the plan is written ONCE and each look is assembled as the whole site in its own design (site.service._full_looks, SITE_FULL_LOOKS / SITE_FULL_LOOKS_MAX 40), clickable at computer / tablet / phone size, and the build after her pick writes no page again. Workspace = her own Hoola thread per site (Build | Plan) + Preview with visual edit, Code, Cloud, Integrations, Health, Settings, History, Publish. Previous: v0.649.0 SACH MEIN ROKO - "cancel this task" really cancels it on a call, the phone chat and the console: her stop words are caught BEFORE the turn waits behind the busy job, the real stop runs (the turn's Stop + the job's own stop), and every record says stopped (job row "cancelled", its result report skipped, the restart inbox closed, the long job stopped), so the next call never says "kaam chal raha hai" and no late "ho gaya" arrives; kaam_status action=stop for the brain; Gemini may never claim a cancel itself; v0.648.0 KAAM KA HISAAB - her work in one list (running / waiting for her / done in the last 7 days, each row opens its chat or call) on the phone (chat list > Aapka kaam) and the console (Today > Work); a call brain turn reads this week's finished work (two small queries) so "kal jo kaam diya tha" needs no extra step; a call record's notification opens that call; the chat gets recent calls once (through the diary); v0.647.0 ALAG CALL, EK YAAD (built as 0.646; their WEB DEVELOPMENT PANEL 2 took 0.646.0 - both kept) - a voice call gets its OWN record (Calls section on phone + console) when the phone asks (split=1): her words, tool rows, cards and the receipt land there, never in the chat; the record shares the chat's memory scope, a call brain turn reads the chat's last lines and a chat turn reads the last calls' receipts; call notes are keyed by the chat so the next call still opens with them; phone actions still reach her phone; no notification for what she heard on a live call; v0.646.0 WEB DEVELOPMENT PANEL 2 (owner: "the panel is immature and bad with alignment ... clicking the type section borders it with a blue line" + "when I type the prompt it goes to main chat on homepage ... make it perfect end to end"): the panel now works ON ITS OWN - the home ask creates the website here (its own thread first, handed to the server: a site made with no conversation published to her HOME chat, that was the leak), the Workspace walks plan (untick pages, questions, AI cost) -> her Haan -> three looks with real screenshots -> her pick -> the build with progress (polled) -> the live preview (computer / phone) -> changes; every site has its OWN Hoola thread inside the panel for shop / payments / booking / languages; "Move my old site" + "Screenshot" read the design in the panel (ownership proof shown when asked); one border on the ask card (no inner focus line), own `wdp-` prefix (the Game Desk's `#app .wd-body` had been wrapping the page), layout wraps by the room it has; a real-browser test checks no two buttons overlap and none clips its words in every tab, light + dark + phone. Previous: v0.645.0 KHULA LOOP - the system prompt and context block (about 25 database-backed blocks: the after-sales due list, shop, site, brand...) are built in a thread, not on the event loop (her 17:59 call froze the whole server 2.1 s in aftersales.due while building instructions); v0.644.0 BINA RUKE - a call brain turn no longer waits for the diary / facts read (it missed its 2.5 s wait on every call ask; voice_brain_yaad off by default, yaad_khojo still there); v0.643.0 HAMESHA HAIKU - a call brain turn is always on voice_brain_model (Haiku) even when the question looks like a big / hard job (her 17:44 call asked for Sonnet with a 16k cap); the `claude call` log shows the model actually sent; v0.642.0 SAAF RAASTA - after-turn fact saving runs its on-box embedding search in a thread (it froze the whole server 4.7 s on her call); v0.641.0 PEHLE SE TAIYAAR - the 606 tool schema checks + search index run in a background thread at server start (her first call after a deploy froze the whole server 8.1 s doing them on the loop); the loop watchdog logs the innermost frames on one line; v0.640.0 PAKDO (built as 0.639; their KAAN W3 took 0.639.0 - both kept) - an event-loop watchdog logs WHAT blocks the server (stack + pool queue), the call brain memory reads get their own thread pool, two more prep stages timed; v0.639.0 KAAN W3 APNI BOLI (built as 0.637.0; their KAHAN RUKA took 0.637.0 and TEZ TAIYARI took 0.638.0 while W3 sat built - REBASE PROTOCOL, rebuilt fresh on their f3fab7fc8 tip, all kept, their story chain verbatim) (owner: 'START' + 'always show result in English' on the kaan plan - Wave W3, after W0 v0.601.0 baked live, W1 v0.613.0 diarize+minutes and W2 v0.619.0 live captions proved live on the box): custom vocabulary + style presets, all deterministic, nothing invented. VOCAB (new kaan_vocab table): per-tenant terms with two honest mechanisms - the terms seed whisper's initial_prompt (a SOFT hint: whisper has no hard vocab biasing, from the repo read), and fix_to is a DETERMINISTIC word-boundary case-insensitive replacement applied after the engine, every application counted and named in the row note ('vocab (W3): N term(s) seeded...; deterministic fix(es) applied: term xK') - nothing silent, vocab_list is the audit; vocab_add/vocab_list/vocab_remove actions, upsert case-insensitive (term_key), the prompt capped at 800 chars with the truncated count honest (oldest kept first); transcribe gets vocab=true default, live_start FREEZES the tenant prompt into the session so every rolling pass and the finalize clean pass carry it. STYLES (new kaan/styles.py): verbatim / clean (whitespace, immediate-duplicate collapse, sentence-start caps - no words added or reworded, counts in the note) / subtitles (the W2 phrase rule: >0.6s word gap or sentence ender; wraps at 12 words when the row has no word timestamps) / minutes (the W1 skeleton) / social (hook + key words + action candidates + stats, extractive only) - all read-only, gate-free by the W1 law (no audio ingest; text already hers); status carries the styles + vocab blocks. THE GATE MAP: NO new switch - transcribe/live stay behind kaan_audio, vocab mutations are owner/approved-only, style/vocab_list are reads. Registry 606 UNCHANGED - actions, not tools; the kaan description retightened inside the 1200-char diet (991 chars). New W3 user-facing strings are English (owner instruction); older kaan strings keep the house Hinglish. Tests: NEW test_v0637_kaan_w3.py (23, zero network, zero torch): vocab CRUD roundtrip + case-insensitive upsert + honest validation + tenant isolation + prompt cap + word-boundary counts, transcribe prompt-seed + fix-apply + note + vocab=false raw path, engine initial_prompt signature, all five styles' determinism, gate-free style vs gated transcribe, live prompt freeze across rolling + clean passes, registry 606 + enum 16 + diet, actor lanes, status blocks, module purity + laziness, APP_VERSION 0.639.0.; the rebase ritual re-swept their 0.637/0.638 layers to 0.639.0 (+645) across the suites Previous: v0.638.0 TEZ TAIYARI - a call brain turn reads diary / job state / coder memory in parallel under 2.5 s (was 7.0 s), never waits on her MCP servers (4.5 s), skips the hint lookup (1.8 s); v0.637.0 KAHAN RUKA (built as 0.636; their WEB DEVELOPMENT PANEL took 0.636.0 - both kept) - a call brain turn logs each stage before its first Claude call (`brain prep`), skips the whole-chat compaction, reads 8 exchanges with earlier tool results cut to 1,500 chars; v0.636.0 WEB DEVELOPMENT PANEL (owner: the prototype -> "PERFECT"): the web console gains a Web Development sidebar section (static/console/webdev.js) - a home (one-line ask that goes to chat, four ways to start, her websites, business types) and nine tabs per site (Overview, Build, Edit, Code, Data & logins, Integrations, Publish, Health, Settings). Build / Edit / Code / Data / Shop / Blog / Languages open the EXISTING Website studio beside it (build.js openSite: the same preview, edit mode and code mode); Publish draws the addresses, the launch check card (her tap with the server's hash), the v0.623 old-address redirects (her tick list + hash), rollback and domain connect; Health reads care + ops (visits, enquiries, uptime, HTTPS days, speed bands, visitor errors, backups); Settings saves business details through the answers route and takes down only after confirm; payments, domains, n; v0.635.0 SAAF NAAP - every Claude call logged with its own time + size (`claude call N s`), and a call brain turn never thinks or runs at raised effort; v0.634.0 TEZ DIMAAG - a call brain turn reads the checkpoint + last 12 exchanges (not the whole chat) and is never a held hard turn (her 15:27 call: 3-5 s before every first step, 21 s on one ask); v0.633.0 TEZ JAWAB - on a brain call Gemini answers talk / knowledge itself at once and calls the Haiku brain only for tools / her data, says one line while the brain works (non-blocking), brain wait logged; v0.632.0 KAAN CHHOTA - a brain call keeps only the last few minutes of audio (compression 8k / 4k; her 11:11 call re-read 31k audio tokens = 54% of the bill); v0.631.0 SAB HAIKU - every Claude call (simple to hard, background, routines, engines) runs on claude_one_model = Haiku, enforced at the SDK door; out-of-credit said plainly; v0.630.0 HAIKU DIMAAG - ordinary chat asks on Haiku (hard -> Opus, long -> Sonnet, Haiku failure -> Sonnet) and the voice call brain on Haiku: Gemini Live only hears and speaks (one tool, short persona, no brief); v0.629.0 MCP BHI CHHOTA - on a small-menu call her MCP servers are NAMED, not declared (measured: 32 tools / 52k chars re-read on every reply, more than the whole menu); their work goes to santosh_kaam. Previous: v0.628.0 CHHOTI HIDAYAT - with the small call menu the call gets a short persona (27k -> 7.8k chars, same person / language / safety / routing), one-line tool texts and a 4.5k memory brief; Gemini re-reads all of it on every reply. Previous: v0.627.0 CHHOTA MENU - the call declares only ~60 everyday tools (Gemini Live bills the whole tool list on every reply; 91k -> 37k chars), everything else through santosh_kaam; a call whose phone is away never wakes Gemini for news and is not "live" for reminders. Previous: v0.626.0 PAISA KA HISAAB - a call is metered from Gemini Live's own usage_metadata (the whole context billed on every reply), not the audio-minute estimate that missed most of the bill. Previous: v0.625.0 EK AWAAZ - the pre-rendered TTS clips (ek second acks, murmurs, progress sounds) are off by default: they came from a separate TTS model and sounded like another voice / a radio mid-call; only Gemini Live speaks. Previous: v0.624.0 SAB KAAM CALL PAR - a create_reminder with no reminder ask in her words is refused by code and her real ask (email, search, any job) goes to santosh_kaam; every call tool logged with her words. Previous: v0.623.0 KOI PATA NA KHOYE (built as 0.622; their SAHI SAMAY took 0.622.0 - REBASE PROTOCOL, both kept) (owner: "GO 1 TO 4" after the ai-website-cloner-template read; HER OWN old site only, ownership proved by v0.567): site/moved.py - every old address of her site (sitemap + same-site links) matched to a new page (same slug > words > home flagged as a guess), live 301s only after her tap (hash-bound, rows can be unticked), _redirects.json in every live folder + every publish, hosting.serve answers it and nginx hands its own 404s over via @hoola_moved; keep-my-look (her page list + section order into look 1's brief); her old page vs the new one at 390 / 1280 px with the differences listed; imported photos checked by their bytes. Tests test_v0623_koi_pata.py 8. NOT VERIFIED live. Previous: v0.622.0 SAHI SAMAY + SIRF GEMINI (owner: "CHECK THE EXACT LOGS - WHY SETTING REMINDER HAVING ISSUE" + "SWITCH VOICE TO GEMINI - CHATGPT IS VERY BAD"): her 06:17 call record showed the reminders WERE spoken when due, but SETTING failed - "do minute baad" was refused twice as past and once saved 9 s ahead, "paanch minute baad" saved 2 min ahead, because the call model worked out the clock time itself. create_reminder now takes in_minutes and the SERVER counts it from its own exact clock (when stays for clock times / dates; a past when tells the model to use in_minutes); the call persona says so. And every call runs on Gemini: voice_openai_enabled (default False) - her earlier real-voice pick no longer reaches OpenAI. Tests test_v0622_sahi_samay.py 7. Previous: v0.621.0 YAAD KI GHANTI (owner: "CHECK THE ISSUE REMINDER NOT WORKING VIA VOICE"): with no call live, a due reminder was a chat line + a notification only - Hoola never SAID it and never rang her. Now worker.fire_reminders rings her phone (the GHANTI voice_ring through the bus, so an open app rings from its stream and a closed one from the push) and saves a call followup note, so the call it starts OPENS with the reminder; a live call on any of her chats hears it at the next pause and no ring goes out (voice.tenant_live). Her own reminder ignores the job-ring quiet hours and 2-a-day budget (own cap VOICE_RING_REMINDER_MAX_DAY 12; switch VOICE_RING_REMINDERS). Tests test_v0621_yaad_ki_ghanti.py 6. Previous: v0.620.0 BHANDAR MANCH (built as 0.618.0 - their HAMESHA JUDA took 0.618.0 (tag v0.618.0-b1789) and their KAAN W2 took 0.619.0 (tag v0.619.0-b1791) while BHANDAR sat built - REBASE PROTOCOL #11, rebuilt fresh on their e522b90b0 tip, all kept, their story chain verbatim) (owner: "T2 Local Core -- START" - the T2 tier of download/HOOLA_MCP_FEED.json, the zero-network / zero-login / zero-key local beds, ported IDEA-ONLY onto house rails, zero upstream code, zero new pip, zero new keys; catalog rows evidence-verified verbatim: Aderali06/sqlite-mcp-server "Safe, read-only SQLite MCP server with auto schema discovery, row limits, and structured AI error handling", hannesrudolph/sqlite-explorer-fastmcp "Safe, read-only access to explore and query SQLite databases, with query validation", scoretracker4321/json-mcp-lite "Serve any JSON file (catalogue, FAQ, price list) as read-only list, keyword search and get-by-id tools", micl2e2/code-to-tree "Convert source code into an AST, regardless of language", rafim-dev/mcp-context-condenser "AST-based code outliner, log compressor and context budget analyzer", EdelmarSchneider/permark "Markdown reader and editor that tells coding agents what you are reading", davidan90/time-node-mcp "Timezone-aware date and time operations: IANA timezones, timezone conversion and daylight saving time handling" + the mcp/servers src/time reference shape (get_current_time / convert_time over IANA zones, the home zone named so the model can default to it); awesome-mcp-servers MIT re-verified, mcp/servers MIT->Apache-2.0 transition noted, ZERO code taken either way): ONE new tool `bhandar` (Bhandar = the storehouse; 'matka' was rejected - it sits in the ads gambling blocklist beside 'satta'), registry 605 -> 606 (their 605 + 1, the merged arithmetic), backend-only (no console page, no phone screen, no route), server/app/agent/bhandar_tools.py all-stdlib (sqlite3/json/ast/zoneinfo/pathlib/re) - the hoola AI's own READ-ONLY local-data workbench over THIS tenant's beds, it never writes anywhere: action=beds (discovery: scraping / kgmemory / workspace .db with sizes, mtimes, table counts; CREATES NOTHING), action=sql (ONE read statement - SELECT / WITH / EXPLAIN / read PRAGMA - against a bed named exactly as beds returned it; THREE belts: exactly one statement + the head law, write verbs and write pragmas refused BY NAME before anything runs ('replace' stays legal as a function), then mode=ro - SQLite itself is the wall; rows capped 200 with honest truncation, cells capped 400), action=md (workspace markdown structure: outline with line numbers / links deduped incl. reference defs / stats), action=json (validate with the parse position / typed keys outline / get by dotted path a.b.0.c with the missing hop named; result capped 20k), action=ast (the Python skeleton of a workspace .py: classes + bases + methods, TOP-LEVEL functions with arity + async, imports, assigns - the shape, never the source; SyntaxError honest with its line), action=time (IANA now / convert with honest UTC offsets and DST flags, home zone Asia/Kolkata; zoneinfo is a local database - zero network; the UTC +00:00 falsy-offset bug caught in the first smoke). md/json/ast paths under the sandarbh root law (absolute / dot-dot / binary refused, 200k cap, symlink escapes die in resolve; the read-only lane never mkdirs - the no-create law is pinned). Kill switch bhandar_enabled = off means off (everything is a read: NEED_SETUP). Envelope = the v0.559 discipline shape; admit keys bed-shaped (bare "sql" stays with pgdb, bare "ast"/"json" too loose for substring admit); prompts.py bullet beside Sandarbh Manch. Tests: NEW test_v0618_bhandar_manch.py (40, zero network, per-tenant stores wiped per test; the file name keeps the first-build number, the v0.566 middleware precedent): the whole surface incl. the sql gate (11 refused shapes with reasons), the replace() exception, WITH + EXPLAIN on reads only, SQL_ERROR honesty, bed-name law + tenant isolation, md/json/ast lanes + caps + parse positions, time IST home + the UTC regression + DST honesty + unknown zone, the kill switch, the purity law, registry 606 + enum + APP_VERSION 0.620.0 pins. Suites on the merged tree: bhandar 40 + their kaan_w2 18 + kaan_w1 20 + kaan 25 + sandarbh 38 + reach 45 + spec sutra 31 + auzaar 12 (every one of the 606 tools passes JSON-Schema-2020-12) + aep1 10 + omnipack 27 + construction w3 24 / w35 17 / w4 20 + ek_yaad 10 + bahar 10 - the v0617 2 reds WORKTREE-PROVEN pre-existing (the sandbox's missing Playwright binary, the documented environment red class). Ritual on the merged tree: scripts/ritual_0620.py swept 208 test files (their 0.619.0 layer -> 0.620.0, +625 -> +626, registry pins 605 -> 606 in all three shapes, ZERO residual; the v0.605 version-number coincidence preserved); pubspec 0.620.0+626; APP_VERSION story; CLAUDE.md current-version line; docs/WORKLOG.md + docs/HISTORY.md mirrors (both lanes' entries kept). Server-only deploy = owner's vps-ops dispatch (healthz grep 0.620.0); desktop untouched - old APKs keep working; Mera PC freeze respected. RECOVERY NOTE: the sandbox recycled mid-task (repo snapshot reset to v0.491, feed files + upstream clones lost) - origin fetch restored the chain, the feed pipeline + T2 evidence re-derived from the recipes. Previous: v0.619.0 KAAN W2 (their story, chain intact). Previous: v0.619.0 KAAN W2 - LIVE CAPTIONS (built as 0.618.0; their HAMESHA JUDA took 0.618.0 - REBASE PROTOCOL, rebuilt on their tip, all kept) (owner: 'START' on the kaan plan - Wave W2 of the WhisperAI feed, after W0 v0.601.0 baked live and W1 v0.613.0 diarize+minutes proved live on the box): rolling live captions over a PCM spine. NEW server/app/kaan/live.py: start opens a kl_ session (model default base - fast on CPU for rolling passes; the ladder validates every override); chunk decodes ANY container (MediaRecorder webm/opus, wav, mp3) to 16k mono s16le via ffmpeg stdin-pipe and APPENDS it to one spine file per session (data/kaan_live/<id>.pcm - mixed chunks are fine because each decodes on its own), then runs ONE rolling pass on [watermark - 0.5s overlap, end]: the window is cut by BYTE OFFSET (exact by construction: 16k x 2 bytes) and wrapped into a wav with the stdlib wave module - no subprocess; accepted words must start at/after the watermark (EPS 0.02s) so whisper's overlap repeats are trimmed (the honest line names the borderline-slip risk), phrases split on a >0.6s word gap or a sentence ender, the watermark advances to the window end on every pass that ran so silence is never re-scanned; MIN_WINDOW 1.5s keeps tiny chunks from burning a pass (stop still catches a >=0.3s tail); stop closes the session (idempotent) and writes ONE kn_ transcript row (source='live') that diarize/minutes already read, with the OPTIONAL bounded clean pass finalize_model= (<= 10 min audio, MAX_FINALIZE_S 600) for batch quality. CAPS: chunk 5 MB, 2000 chunks, 2h session. THE GATE MAP: start/chunk are AUDIO INGEST - the kaan_audio gate owns them (no new switch); stop is bookkeeping on audio already on her server (the W1 law) plus the optional clean pass; live actions are owner/approved-only (they write and ingest); registry 605 UNCHANGED - actions, not tools - and the kaan description tightened to sit inside the 1200-char diet so W2 stays visible to the agent. status() carries the live block (default_model, active count, spine privacy line). Tests: NEW test_v0618_kaan_w2.py (18, zero network, zero torch, real-ffmpeg test skips when absent): gate refusals, start/default-model/bad-model, rolling pass + watermark trim + no dupes (the scripted engine re-speaks every window so the trim is genuinely exercised), small-window guard + stop tail, phrase gap/ender split, chunk guards (empty/oversize/cap), stop idempotent, silence honesty, finalize batch + bounded + ladder-validated, tenant isolation, registry 605 + enum + diet description, status live block, actor lanes, module purity + laziness, APP_VERSION 0.618.0. NOT VERIFIED live: the first real phone-chunk session on the VPS - the bake block rides the deploy.Previous: v0.618.0 HAMESHA JUDA (built as 0.617.0; their KUCHH NA CHHOOTE took 0.617.0 - REBASE PROTOCOL, both kept; owner: "VOICE CALL IS SOUL OF OUR PRODUCT ... ONCE CALL CONNECTED IT REMAINS CONNECTED TILL USER DONT DISCONNECT IT ... REPLY WHEN WORK DONE, GIVE REMINDERS ... 24/7" -> "START"): Gemini Live bills every second of audio sent, silence included (~Rs 26 an hour per open call, ~Rs 630 a day), so a quiet call now PARKS - Gemini closes after VOICE_PARK_AFTER_S 90 with nobody speaking and nothing running, the call to Hoola stays live, and her voice (first 5 s kept), a typed line, a job result, a card or a reminder brings Gemini back on the same resumption handle; a long hold and a lost phone PARK instead of ending the call (phone waits VOICE_PARK_GRACE_S 900, not 25 s); a due reminder, the morning briefing and an automatic job result are now SPOKEN on a live call (they never reached it before); real voice (OpenAI) moves its 50-minute session only at a pause; the phone re-dials by itself after a server update (fresh call on the same chat, continued) and keeps trying 14 min after a network loss; scorecard counts parked minutes / parks / wakes. Tests test_v0617_hamesha_juda.py 9. Previous: v0.617.0 KUCHH NA CHHOOTE + PEXELS KA NAAM (built as 0.616.0; the dev's BAHAR SE BAAT took 0.616.0 - REBASE PROTOCOL, both kept; owner: 'go' on the Hallmark read, docs/research/hallmark/00_READ.md; Nutlope/hallmark MIT, ideas only, own code): (1) Pexels photos are now CREDITED on every built page as the Pexels API guidelines ask - 'Photos provided by Pexels' linked + each photographer linked to the photo page (credit_name / credit_url kept with the photo; older photos read the name back from their credit text; only pexels.com links written) - the credit had been stored since v0.292 but never shown; (2) NEW site/kept.py: a change in her words is compared with the version before it - phone / WhatsApp / email links per page, forms + their fields, page links and the pieces Hoola wires in (shop, posts, chart, booking, map...) must still be there; what she asked to remove and pages the change removed are not reported; never blocking, never auto-edited: kept.lost + a warning per item + one line to her ('wapas lagao'); switch site_kept. Tests test_v0617_kuchh_na_chhoote.py (5). NOT VERIFIED: no live Pexels call or live Opus change build through it yet. Previous: v0.616.0 BAHAR SE BAAT (owner: "More places to talk to Hoola" -> WhatsApp + Telegram + Slack + Teams, "Only me"): her own Hoola from outside apps - WhatsApp through HER WhatsApp Business number (Meta official Cloud API; her paired number goes to Hoola, every other sender stays a customer on the business inbox; never personal WhatsApp), Telegram through her own bot (secret-token webhook, private chat only), Slack through her own app (signed Events API, DMs only), Teams through her own Azure Bot (Bot Framework JWT checked, personal chat only); a 6-digit pairing code (15 min, 5 tries) binds ONE sender per channel, everyone else gets nothing; one chat per channel on the same turn pipeline (same memory, tools, cards), replies sent back once each (worker forwards jobs that finish later; WhatsApp only inside the 24 h window; OTP / PIN text never sent out; tap cards stay in the app); `app/bahar.py`, /api/bahar + /webhooks/bahar/*, phone Profile > Bahar se baat. Tests test_v0616_bahar.py 10. Previous: v0.615.0 YAAD SE + SUDHAAR YAAD (owner: "GO 1 2" after the Dots / Grok memory comparison; built as 0.612.0, the dev chain took 0.612-0.614 - REBASE PROTOCOL, all kept): (1) YAAD SE = Grok's book icon - the memory a reply really leaned on (turn-block facts, recalled past chats, yaad_khojo hits; only what the reply echoes, so the note never lies) is published as ONE memory_used note under the reply (a past chat by its title), console <details> + phone MemoryUsedChip, every line forgettable via POST /api/memory/unremember (fact + its copies / work note / graph + page lines; a past chat gets Conversation.no_recall - it stays in her list, only its index goes and search filters it for good); (2) SUDHAAR YAAD = Grok Bot / Dots "learns how you like things done": the extractor and the live prompt keep a CORRECTION as a standing WHEN / WANT preference so she never corrects the same thing twice. Tests test_v0612_yaad_se.py 9. Previous: v0.614.0: CONSTRUCTION WAVE 4 - the remaining seats (owner: 'GO WAVE 4'; built as 0.586.0 on the v0.585.0 tree - their dev chain took 0.586-0.613 while it sat built, COLLISIONS #8 + #9, REBASE PROTOCOL twice, their base kept whole, the version layer re-applied coherently 0.613.0/+619 -> 0.614.0/+620; the full wave story is preserved in the git commit): five NEW desks (const_land #1-6 / const_plan with criticality never computed / const_ehs / const_studio / const_learn), six desk extensions (approvals screener #33, QS cost plan+VE+GST #40-89, contracts LD+arbitration #48-50, tender purchase+expediting+EXIM #57-59-60, quality material tests #76, customer sales+AFS+handover+investor #94-99), the FM rows #102-108 riding the EXISTING property/society seats via the new const_fm tools + fm_work duty, four tag-only rows (#7/#13/#100/#101), TIER_C 33 -> 40, india pack 19 rows, registry 581 -> 605 on the merged tree, register coverage 119/123 - ONLY the four design disciplines (8/14/15/17) stay with DESIGN_DESK_PLAN.md. AEP train so far: HOOLA CORE (P1), HOOLA TRACE (P2), HOOLA GRAPH (P3, interrupt/checkpointers), HOOLA AGENT (P4), HOOLA MIDDLEWARE (P5, server/app/aep/middleware.py), HOOLA RETRIEVE (P6, aep/retrieve.py + aep_vectors: the index()/aindex() dedup flow, the retrievers as Runnables firing the retriever span) - P7 HUB -> P8 the 100% parity audit next; Previous: v0.613.0 KAAN W1 - TURN KHOJ + MEETING MINUTES (built as 0.607.0; the dev chain + parallel waves took 0.607-0.612 while W1 sat built and verified - RETAIL WAVES 2+3, YAAD KE KHAANE x2, BIMA ASSIST, BIMA RISK; REBASE PROTOCOL twice, all kept, rebuilt fresh on their 0.612.0 tip, registry 588 -> 593 theirs) (owner: 'START' on the kaan plan - Wave W1 of the WhisperAI feed, after W0 v0.601.0 KAAN PACK shipped and BAKED LIVE on the VPS: engine ready, jfk.flac through kaan word-exact, KAAN_AUDIO=1): diarization + meeting minutes as TWO ACTIONS on the SAME one tool `kaan` (registry 593 UNCHANGED - actions, not tools). NEW server/app/kaan/diarize.py: HONEST turn attribution from the transcript's own timeline - pauses are the only truthful signal because W0 stores no audio (local-first: the temp file dies when the engine is done); a gap > PAUSE_S 0.8s between consecutive WORDS (word timings when the engine gave them, else segment gaps) cuts a TURN boundary; turns stay UNNAMED until the owner names them (names={'1': 'Gupta ji'} - unknown names surface, blanks ignored); NO voiceprint claim anywhere - real acoustic diarization (the sherpa-onnx voiceid path) needs STORED audio, a W6 retention decision, never smuggled in; deterministic (same segments in -> same turns out), MAX_TURNS 400 cap with truncated flag. NEW server/app/kaan/meeting.py: the DETERMINISTIC minutes skeleton - per-turn stats (words, word_share, seconds), content keywords (en+hi stopword-light, top 8), action-item CANDIDATES by cue words with turn attribution (bhej/check/kal/will/need to/karna...) - candidates, never decisions; zero model calls, zero network; the prose summary is Santosh's job on top. service.py: diarize_transcript persists turns into row.speakers (the W0 column waited for exactly this) + returns the row id, minutes() reads it back, _row grew `speakers` (additive), status() carries the diarize block (method + honesty note). THE GATE MAP: stored-id diarize is GATE-FREE (no audio ingest - the text is already hers) but kill-switched (kaan_diarize default ON, KAAN_DIARIZE=0 par band); fresh-audio diarize (file_id/data) rides transcribe_file so the AUDIO gate owns it; minutes is a read - open to staff like list/get, refused to customers; diarize is owner/approved-only (it writes the row). ADMIT KEYS stay TIGHT: + meeting minutes / minutes bana / minutes likh / minutes chahiye / kaun bola / kaun bola tha / kaun kaun bole / kaun bol raha - bare 'minute'/'minutes' stays OUT so '10 minute ruko' can never admit the family (the trap is pinned). Tests: NEW test_v0607_kaan_w1.py (18, zero network, zero torch): pause-turn cutting + determinism, word-gap cuts inside one segment, custom pause_s, names/unknown-names/blank-name honesty, empty segments + 450-segment cap, stored-row persistence + W0 read shape untouched, fresh-audio gate refusal + whole-pipeline happy path, the kill switch (env flip + cache_clear, status tells the truth), tenant isolation (diarize AND minutes), minutes structure/stats/keywords/cue-candidates with turn attribution, minutes without diarization (one-turn fallback) + on silence (stays silence) + unknown id, minutes is pure (no httpx/requests/openai/whisper in source), registry 593 + enum pin, actor lanes (staff reads OK / staff diarize refused / customer refused / no-id honest line), admit keys + the minute trap, laziness laws for both new modules, APP_VERSION 0.613.0. W0 suite pins healed: actions enum grows diarize+minutes, the story token rides (the newest-story precedent); count pins healed to their merged arithmetic 593. Neighbour sweeps on the rebased tree: voice / frames / avatar films / AEP / YAAD SACH / SAAF NAZAR / registry pinners green; 1 pre-existing red DOCUMENTED untouched (test_v0512/v0514/v0495 story-window markers left the 20k window during the dev chain's own 0.601-0.606 re-version sweeps - stash-proven red at clean d7d34ee05, the v0.479 precedent). Version ritual 0.613.0: APP_VERSION story, pubspec 0.613.0+619, pins swept 0.612.0 -> 0.613.0 (+618 -> +619) across the suites (101 full-string + 203 bare on the pre-rebase count), console stamps untouched (server-only release, the 0.476 precedent), WORKLOG mirror entry. Waves W2-W6 (live-call captions, styles + vocab, exports + Gyaan unlock, MCP + API + extension audio, quotas + retention) wait for their own START. Previous: # v0.612.0 BIMA RISK (owner: "GO NEXT WAVE" -> Health insurance register Wave 3, pricing / underwriting / fraud signals): bimarisk/ engines (experience tables with thin groups marked, observed price trend, chain-ladder run-off triangle as a working paper, premium-vs-cost fairness gaps and jumps, underwriting triage from HER rules with the rule + manual page + loading shown and any decline rule turned into a human referral, provider outliers vs peer median, overlapping stays, geo plausibility, cashless-upgrade flags, a neutral case file with the allegation left blank, fraud-model flag-rate / false-positive / override audit, scheme anomalies); ONE new tool bima_risk (registry 593, family bimarisk, owner / staff only, voice via kaam) in the Health Insurance hub group; declines, prices, loads, reserves, signs off, blacklists and accuses NO ONE, refuses religion / caste / gender / locality / name as a rule or rating factor, stores and shares nothing; 5 tests. Previous: v0.611.0 YAAD KE KHAANE (owner: "FIRST WE COMPLETE MEMORY / CONTEXT WORK"; built as 0.609.0, their v0.609.0 and v0.610.0 BIMA ASSIST landed first - REBASE PROTOCOL, both kept) = the rest of the Claude memory comparison: (3) the live model WRITES memory as it chats (prompt: remember one short fact, replaces=<id> for an update, look old things up with yaad_khojo) and the background extractor stays out of a turn that already kept / forgot a fact (life_tools.SAVED_THIS_TURN) - one writer per turn; (4) the controls Claude has: a per-Session "use my main memory" switch (Project.use_main_memory, fence.main_memory_ok: off = only that Session's own facts + pinned, no main page / graph; PATCH /api/projects/{id}, console Session page checkbox), an opt-in "Sensitive baatein bhi" (Profile.memory_sensitive, fact_ok(sensitive=): health / faith / politics may be kept, money / IDs / secrets / criminal / immigration / self-harm never), and "Saari yaad mitao" on the phone memory page (POST /api/memory/reset); + vps-ops memory_quiz / memory_quiz_haiku (the long-chat quiz in one click, QUALITY_MODEL honoured). Tests test_v0609_yaad_ke_khaane.py 8. Previous: v0.610.0 BIMA ASSIST (owner: "GO NEXT WAVE" -> Health insurance register Wave 2, assists with a named human decider): bimaassist/ engines (plan side-by-side with no recommendation, material-fact prompts, proposal completeness, coverage and waiting-period checks with each line tied to the clause text she supplies, pre-auth checks, query-reply drafts from the chart, medical timeline with gaps, rejection and grievance letter drafts that refuse to exist without a clause, ombudsman packet index and dates, policy-wording and mis-selling reviews, FHIR R4 Claim skeleton, code map from her own table); ONE new tool bima_assist (registry 592, family bimaassist, voice via kaam, four self-help actions open to a policyholder) in the Health Insurance hub group; decides, signs, sends, files and submits NOTHING, stores nothing, periods from memory marked verify; 6 tests. Previous: v0.609.0 BIMA DESK (owner: "GO NEXT WAVE" -> Health insurance register Wave 1, customer side + admin): bimadesk/ engines (claim document checklist for cashless or reimbursement with filing deadlines, itemised payable worksheet with tariff caps, room-rent proportion, co-pay, deductible and the gap to the settled amount, settlement vs payment match with duplicate UTRs, claim ageing against a timeline she sets, renewal reminders, grievance triage with due dates, rejection-appeal outline, status-update drafts, KYC format checks with masked Aadhaar); ONE new tool bima_desk (registry 591, family bimadesk, voice via kaam, three policyholder actions open to a customer) + hub group Health Insurance; decides NO claim, files / sends / stores nothing, gives no medical or legal advice, periods from memory marked verify; 7 tests. Previous: v0.608.0 EK YAAD + JUST IN TIME (owner: "go 1 and 2" after the Claude vs Hoola memory comparison; built as 0.605.0, the dev chain took 0.605-0.607 while it was tested - REBASE PROTOCOL, all kept): (1) ONE memory door like Claude's one memory per scope - app/memory.py search_all (facts + past chats/calls/jobs + Coder work notes + knowledge graph + her Mere baare mein page in ONE search, every hit labelled with its store, the Session fence / incognito / her recall switch held), everything (GET /api/memory/everything = one view) and reset_all (POST /api/memory/reset confirm=RESET = Claude's reset; her chats and skills stay); yaad_khojo IS the door and rides every turn (CORE_TOOLS); (2) JUST IN TIME (Anthropic: the smallest set of high-signal tokens; Claude looks old chats up by a tool call): a maybe-related old chat (score >= 0.62) no longer rides every message - only her own pointer at the past brings old chats in, the rest is one yaad_khojo call; the system prompt carries the 15 newest facts instead of 40 (setting memory_recent_facts; measured under half the old block on 60 facts), pinned facts all, meaning-matched facts per message. Tests test_v0605_ek_yaad.py 10. Previous: v0.607.0 RETAIL WAVES 2 + 3 (owner: "Retail Waves 2 and 3" on the Retail & e-commerce register): WAVE 2 retailgrowth/ (loyalty lists for opted-in customers only, markdown steps inside HER floor and MRP, unit economics, ABC range review, price rule check on competitor prices she gives, scheme accrual vs claims, retailer credit exposure on HER multiple with no personal attributes, beat visit order, working-capital cycle, delivery batches) + WAVE 3 retailtrust/ (fraud rule hits, return-abuse list, review authenticity signals, seller KYC format + GSTIN check-digit checks, dark-pattern audit, grievance deadline clock, Legal Metrology label checklist, delivery-promise audit, AI override rates, price fairness across segments); TWO new tools retail_growth + retail_trust (registry 590, families retailgrowth / retailtrust, owner / staff only, voice via kaam) + two hub employees in Retail & E-commerce; proposals and rule hits only - changes no price / limit / listing, bans, removes, refunds and accuses no one, scrapes nothing, stores nothing; 7 tests. Previous: # v0.606.0 SAAF NAZAR (built as 0.602.0; the dev chain took 0.602-0.605 while it sat built - REBASE PROTOCOL, both kept) - the AI-look check on every website (owner: 'GO' on the Impeccable read, docs/research/impeccable/00_READ.md; pbakaus/impeccable Apache-2.0, ideas only, own code, THIRD_PARTY_NOTICES.md): NEW site/look.py reads every built page + the section / kit CSS for 29 reflex tells of AI-made pages (overused fonts, cream page, gradient text, violet gradients, radial halos, glow and hard offset shadows, side-tab borders, nested cards, icon tile above every heading, eyebrow / kicker labels, 01/02/03 labels, bounce easing, marquee, stripes, grid backgrounds, buzzwords, theater phrasing, em-dash overuse, emoji icons, italic serif hero, justified / all-caps / tight / tiny / wrongly tracked body text, skipped headings, broken images), each with its page and section; gate 11 'AI look' = WARN only, never blocks a launch; the per-section tells go into the build's FIRST fix round once so the builder cleans its own reflexes before she sees them; THE BRIEF WINS (her words pin a tell, her own design / brand colours / colours she asked for switch the font + colour tells off; choose_look now keeps 'mine'); page modes persuade / operate / read / experience judge pages differently. Builder defaults fixed at the source: no style default uses an overused font any more (5 styles moved: editorial_calm dmserif_dm, bold_modern bricolage_dm, minimal_swiss archivo_dm, tech_gradient urbanist_mukta, corporate_trust manrope_dm - old pairs kept for existing sites and her design), no default marquee / gradient glow / small-caps or numbered labels, the section writer is no longer taught an eyebrow class and carries a CRAFT FLOOR, the design kit has no eyebrow part, 'at least two motion attributes per section' replaced by motion with purpose, the footer's h3s are h2s (the 404 page skipped a level). Tests test_v0606_saaf_nazar.py (11, calibrated: every rule fires on its planted fault, a well-made page gives zero findings). Existing sites keep their stored look until rebuilt. NOT VERIFIED: no live build with real Opus has run through the new prompt and round-0 look fix. Previous: v0.605.0 DUKAAN DESK (owner: "GO NEXT WAVE" -> Retail & e-commerce register Wave 1, kirana and small online seller copilots): retaildesk/ shop (daily summary, weekly forecast with HER festival multipliers, reorder with the formula shown + expiring + dead stock + cash stuck, margin / selling-above-MRP check, licence + GST date calendar, oversell across channels) + online (return-risk score with reasons, settlement vs sales reconcile, product-claim check, landed-cost compare, shop-scam signals, CGST/SGST/IGST split); ONE new tool dukaan_desk (registry 588, family retaildesk, voice via kaam, the two shopper actions open to a customer) + hub group Retail & E-commerce; changes no price / order / refund / listing, publishes and files nothing, blocks no customer, stores nothing; 6 tests. Previous: # v0.603.0 RISK DESK (owner: "Wave 3 (markets, lending decisions, order placement)" on the Banking & Finance register): riskdesk/ orders (order TICKET with flags against HER limits and charges only from rates she gives - placed:false always; mandate drift / concentration / margin use with rebalance PROPOSALS) + credit (underwriting rule hits and reason codes from HER policy, rules on religion / caste / gender / locality refused; key fact statement draft; DPD / SMA / NPA-suggested ageing; ECL working paper) + valuation (DCF + sensitivity grid) + watch (payment-velocity rule hits, round-trip trade flags); ONE new tool risk_desk (registry 587, family riskdesk, owner only, voice via kaam) + hub entry in Finance & Banking; places NO order, decides NO loan, blocks NOTHING, says no buy / sell, stores nothing; 7 tests. Previous: # v0.602.0 VITT SAHAYAK (owner: "GO NEXT WAVE" on the Banking & Finance register, Wave 2 = institution assists with a named decider): finops/ goals (SIP per low/mid/high ASSUMED scenario, inflation, advance-tax dates) + tax (TDS in her books vs 26AS / AIS rows) + ledger (receivables / payables ageing, PO-receipt-invoice three-way match) + aml (alert triage on HER thresholds with a draft narrative, name screening against HER watch list with explained scores, no built-in list) + credit (ratios + memo draft checked against HER policy floors); ONE new tool vitt_sahayak (registry 586, family finops, voice via kaam, aml / sanctions / credit owner-only) + hub entry in Finance & Banking; stateless, files nothing, approves nothing, moves no money; 10 tests. Previous: # v0.601.0 KAAN PACK (built as 0.589.0; TWO mid-push collisions - their v0.600.0 AEP 1.0 and v0.590.0 SANDARBH MANCH both landed while W0 sat built; REBASE PROTOCOL twice onto their fresh heads, both kept, re-versioned twice, registry 584 -> 585) (owner: "START" on the WhisperAI feed plan - whisperai.com's 17 features are all wrapper-layer around the open model, so the MIT openai-whisper engine comes in as a DEPENDENCY, never vendored code - the port law): Wave W0, the transcription core. NEW server/app/kaan/: engine.py (openai-whisper behind one hand-built interface - model ladder tiny 39M / base 74M / small 244M / medium 769M / turbo 809M ~8x NO-translate / large-v3 1550M; the engine's OWN published guards passed explicitly - temperature 0.0->1.0, compression_ratio 2.4, logprob -1.0, no_speech 0.6; word_timestamps=True = the DTW alignment path; LAZY import - importing app.kaan never loads whisper, INERTNESS LAW), service.py (AUDIO gate kaan_audio default OFF -> honest bake line, ext list mp3..mkv, 5 GB ceiling, ffprobe duration best-effort, silence reported as silence "khamoshi" never filled in, store + get + list + search), models.py (kaan_transcripts: text / segments / words / speakers-for-W1). ONE tool `kaan` (registry 585 = their 584 + 1; actions transcribe / status / list / get / search; family kaan; admitted on transcript / transcribe / sun-kar / likhawat / srt words - bare "kaan" kept OUT, "makaan" contains it; voice rides santosh_kaam via VOICE_VIA_KAAM, GHANTI rings when a long file finishes), hub entry "Kaan (transcription)" in the new "Voice, Meetings & Transcription" group (never: audio never leaves the server, gate stays off until KAAN_AUDIO=1, silence is never guessed). LOCAL FIRST: no API key on this path, audio and transcripts stay on the VPS; retention lands in W6. Tests: NEW test_v0589_kaan.py (25, zero network, a scripted engine - the voice_openai connect-swap pattern): round-trip store/read/search, word timestamps, silence honesty, tenant isolation, every guard, the model-card ladder pinned, turbo-translate refusal, lazy-import proof, admit keys incl. the sunwai-makaan traps, hub entry, table on init; count pins healed to the merged arithmetic on both rebase rounds; the story-token pins ride this story (the newest-story precedent). Waves W1-W6 (diarization + meeting notes, live-call captions, styles + vocab, exports + Gyaan unlock, MCP + API + extension audio, quotas + retention) wait for their own START. Previous: v0.600.0 HOOLA AEP 1.0 (theirs - P8, the 100% parity audit + the openwiki analog, the train's LAST phase), v0.590.0 SANDARBH MANCH (theirs - the T1 reference family: confined tenant workspace + kg-memory graph, IDEA-ONLY), v0.589.0 HOOLA HUB (theirs - P7: the init_chat_model router, the BYOK adapter, the MCP client adapter, the conformance suite), v0.588.0 PAISA SAHAYAK (theirs), v0.587.0 EXCEL BINA NAAM, v0.586.0 SAHI KHARCHA (full chain in git history). Previous: v0.610.0 BIMA ASSIST (owner: "GO NEXT WAVE" -> Health insurance register Wave 2, assists with a named human decider): bimaassist/ engines (plan side-by-side with no recommendation, material-fact prompts, proposal completeness, coverage and waiting-period checks with each line tied to the clause text she supplies, pre-auth checks, query-reply drafts from the chart, medical timeline with gaps, rejection and grievance letter drafts that refuse to exist without a clause, ombudsman packet index and dates, policy-wording and mis-selling reviews, FHIR R4 Claim skeleton, code map from her own table); ONE new tool bima_assist (registry 592, family bimaassist, voice via kaam, four self-help actions open to a policyholder) in the Health Insurance hub group; decides, signs, sends, files and submits NOTHING, stores nothing, periods from memory marked verify; 6 tests. Previous: v0.609.0 BIMA DESK (owner: "GO NEXT WAVE" -> Health insurance register Wave 1, customer side + admin): bimadesk/ engines (claim document checklist for cashless or reimbursement with filing deadlines, itemised payable worksheet with tariff caps, room-rent proportion, co-pay, deductible and the gap to the settled amount, settlement vs payment match with duplicate UTRs, claim ageing against a timeline she sets, renewal reminders, grievance triage with due dates, rejection-appeal outline, status-update drafts, KYC format checks with masked Aadhaar); ONE new tool bima_desk (registry 591, family bimadesk, voice via kaam, three policyholder actions open to a customer) + hub group Health Insurance; decides NO claim, files / sends / stores nothing, gives no medical or legal advice, periods from memory marked verify; 7 tests. Previous: v0.608.0 EK YAAD + JUST IN TIME (owner: "go 1 and 2" after the Claude vs Hoola memory comparison; built as 0.605.0, the dev chain took 0.605-0.607 while it was tested - REBASE PROTOCOL, all kept): (1) ONE memory door like Claude's one memory per scope - app/memory.py search_all (facts + past chats/calls/jobs + Coder work notes + knowledge graph + her Mere baare mein page in ONE search, every hit labelled with its store, the Session fence / incognito / her recall switch held), everything (GET /api/memory/everything = one view) and reset_all (POST /api/memory/reset confirm=RESET = Claude's reset; her chats and skills stay); yaad_khojo IS the door and rides every turn (CORE_TOOLS); (2) JUST IN TIME (Anthropic: the smallest set of high-signal tokens; Claude looks old chats up by a tool call): a maybe-related old chat (score >= 0.62) no longer rides every message - only her own pointer at the past brings old chats in, the rest is one yaad_khojo call; the system prompt carries the 15 newest facts instead of 40 (setting memory_recent_facts; measured under half the old block on 60 facts), pinned facts all, meaning-matched facts per message. Tests test_v0605_ek_yaad.py 10. Previous: v0.607.0 RETAIL WAVES 2 + 3 (owner: "Retail Waves 2 and 3" on the Retail & e-commerce register): WAVE 2 retailgrowth/ (loyalty lists for opted-in customers only, markdown steps inside HER floor and MRP, unit economics, ABC range review, price rule check on competitor prices she gives, scheme accrual vs claims, retailer credit exposure on HER multiple with no personal attributes, beat visit order, working-capital cycle, delivery batches) + WAVE 3 retailtrust/ (fraud rule hits, return-abuse list, review authenticity signals, seller KYC format + GSTIN check-digit checks, dark-pattern audit, grievance deadline clock, Legal Metrology label checklist, delivery-promise audit, AI override rates, price fairness across segments); TWO new tools retail_growth + retail_trust (registry 590, families retailgrowth / retailtrust, owner / staff only, voice via kaam) + two hub employees in Retail & E-commerce; proposals and rule hits only - changes no price / limit / listing, bans, removes, refunds and accuses no one, scrapes nothing, stores nothing; 7 tests. Previous: # v0.606.0 SAAF NAZAR (built as 0.602.0; the dev chain took 0.602-0.605 while it sat built - REBASE PROTOCOL, both kept) - the AI-look check on every website (owner: 'GO' on the Impeccable read, docs/research/impeccable/00_READ.md; pbakaus/impeccable Apache-2.0, ideas only, own code, THIRD_PARTY_NOTICES.md): NEW site/look.py reads every built page + the section / kit CSS for 29 reflex tells of AI-made pages (overused fonts, cream page, gradient text, violet gradients, radial halos, glow and hard offset shadows, side-tab borders, nested cards, icon tile above every heading, eyebrow / kicker labels, 01/02/03 labels, bounce easing, marquee, stripes, grid backgrounds, buzzwords, theater phrasing, em-dash overuse, emoji icons, italic serif hero, justified / all-caps / tight / tiny / wrongly tracked body text, skipped headings, broken images), each with its page and section; gate 11 'AI look' = WARN only, never blocks a launch; the per-section tells go into the build's FIRST fix round once so the builder cleans its own reflexes before she sees them; THE BRIEF WINS (her words pin a tell, her own design / brand colours / colours she asked for switch the font + colour tells off; choose_look now keeps 'mine'); page modes persuade / operate / read / experience judge pages differently. Builder defaults fixed at the source: no style default uses an overused font any more (5 styles moved: editorial_calm dmserif_dm, bold_modern bricolage_dm, minimal_swiss archivo_dm, tech_gradient urbanist_mukta, corporate_trust manrope_dm - old pairs kept for existing sites and her design), no default marquee / gradient glow / small-caps or numbered labels, the section writer is no longer taught an eyebrow class and carries a CRAFT FLOOR, the design kit has no eyebrow part, 'at least two motion attributes per section' replaced by motion with purpose, the footer's h3s are h2s (the 404 page skipped a level). Tests test_v0606_saaf_nazar.py (11, calibrated: every rule fires on its planted fault, a well-made page gives zero findings). Existing sites keep their stored look until rebuilt. NOT VERIFIED: no live build with real Opus has run through the new prompt and round-0 look fix. Previous: v0.605.0 DUKAAN DESK (owner: "GO NEXT WAVE" -> Retail & e-commerce register Wave 1, kirana and small online seller copilots): retaildesk/ shop (daily summary, weekly forecast with HER festival multipliers, reorder with the formula shown + expiring + dead stock + cash stuck, margin / selling-above-MRP check, licence + GST date calendar, oversell across channels) + online (return-risk score with reasons, settlement vs sales reconcile, product-claim check, landed-cost compare, shop-scam signals, CGST/SGST/IGST split); ONE new tool dukaan_desk (registry 588, family retaildesk, voice via kaam, the two shopper actions open to a customer) + hub group Retail & E-commerce; changes no price / order / refund / listing, publishes and files nothing, blocks no customer, stores nothing; 6 tests. Previous: # v0.603.0 RISK DESK (owner: "Wave 3 (markets, lending decisions, order placement)" on the Banking & Finance register): riskdesk/ orders (order TICKET with flags against HER limits and charges only from rates she gives - placed:false always; mandate drift / concentration / margin use with rebalance PROPOSALS) + credit (underwriting rule hits and reason codes from HER policy, rules on religion / caste / gender / locality refused; key fact statement draft; DPD / SMA / NPA-suggested ageing; ECL working paper) + valuation (DCF + sensitivity grid) + watch (payment-velocity rule hits, round-trip trade flags); ONE new tool risk_desk (registry 587, family riskdesk, owner only, voice via kaam) + hub entry in Finance & Banking; places NO order, decides NO loan, blocks NOTHING, says no buy / sell, stores nothing; 7 tests. Previous: # v0.602.0 VITT SAHAYAK (owner: "GO NEXT WAVE" on the Banking & Finance register, Wave 2 = institution assists with a named decider): finops/ goals (SIP per low/mid/high ASSUMED scenario, inflation, advance-tax dates) + tax (TDS in her books vs 26AS / AIS rows) + ledger (receivables / payables ageing, PO-receipt-invoice three-way match) + aml (alert triage on HER thresholds with a draft narrative, name screening against HER watch list with explained scores, no built-in list) + credit (ratios + memo draft checked against HER policy floors); ONE new tool vitt_sahayak (registry 586, family finops, voice via kaam, aml / sanctions / credit owner-only) + hub entry in Finance & Banking; stateless, files nothing, approves nothing, moves no money; 10 tests. Previous: # v0.601.0 KAAN PACK (built as 0.589.0; TWO mid-push collisions - their v0.600.0 AEP 1.0 and v0.590.0 SANDARBH MANCH both landed while W0 sat built; REBASE PROTOCOL twice onto their fresh heads, both kept, re-versioned twice, registry 584 -> 585) (owner: "START" on the WhisperAI feed plan - whisperai.com's 17 features are all wrapper-layer around the open model, so the MIT openai-whisper engine comes in as a DEPENDENCY, never vendored code - the port law): Wave W0, the transcription core. NEW server/app/kaan/: engine.py (openai-whisper behind one hand-built interface - model ladder tiny 39M / base 74M / small 244M / medium 769M / turbo 809M ~8x NO-translate / large-v3 1550M; the engine's OWN published guards passed explicitly - temperature 0.0->1.0, compression_ratio 2.4, logprob -1.0, no_speech 0.6; word_timestamps=True = the DTW alignment path; LAZY import - importing app.kaan never loads whisper, INERTNESS LAW), service.py (AUDIO gate kaan_audio default OFF -> honest bake line, ext list mp3..mkv, 5 GB ceiling, ffprobe duration best-effort, silence reported as silence "khamoshi" never filled in, store + get + list + search), models.py (kaan_transcripts: text / segments / words / speakers-for-W1). ONE tool `kaan` (registry 585 = their 584 + 1; actions transcribe / status / list / get / search; family kaan; admitted on transcript / transcribe / sun-kar / likhawat / srt words - bare "kaan" kept OUT, "makaan" contains it; voice rides santosh_kaam via VOICE_VIA_KAAM, GHANTI rings when a long file finishes), hub entry "Kaan (transcription)" in the new "Voice, Meetings & Transcription" group (never: audio never leaves the server, gate stays off until KAAN_AUDIO=1, silence is never guessed). LOCAL FIRST: no API key on this path, audio and transcripts stay on the VPS; retention lands in W6. Tests: NEW test_v0589_kaan.py (25, zero network, a scripted engine - the voice_openai connect-swap pattern): round-trip store/read/search, word timestamps, silence honesty, tenant isolation, every guard, the model-card ladder pinned, turbo-translate refusal, lazy-import proof, admit keys incl. the sunwai-makaan traps, hub entry, table on init; count pins healed to the merged arithmetic on both rebase rounds; the story-token pins ride this story (the newest-story precedent). Waves W1-W6 (diarization + meeting notes, live-call captions, styles + vocab, exports + Gyaan unlock, MCP + API + extension audio, quotas + retention) wait for their own START. Previous: v0.600.0 HOOLA AEP 1.0 (theirs - P8, the 100% parity audit + the openwiki analog, the train's LAST phase), v0.590.0 SANDARBH MANCH (theirs - the T1 reference family: confined tenant workspace + kg-memory graph, IDEA-ONLY), v0.589.0 HOOLA HUB (theirs - P7: the init_chat_model router, the BYOK adapter, the MCP client adapter, the conformance suite), v0.588.0 PAISA SAHAYAK (theirs), v0.587.0 EXCEL BINA NAAM, v0.586.0 SAHI KHARCHA (full chain in git history). Previous: v0.665.0 JHAROKHA MANCH (built as 0.664.0 - their ASLI SAMAY took 0.664.0 while JHAROKHA sat built - REBASE PROTOCOL #12, both kept; owner: "T3 Local Browser --- CONTINUE"): the T3 tier of download/HOOLA_MCP_FEED.json - the zero-login / zero-key browser rows - lands backend-only as ONE tool `jharokha` (registry 606 -> 607), the agent's OWN headless Chromium driven one deterministic action per call, IDEA-ONLY from microsoft/playwright-mcp ("browser automation capabilities using Playwright ... through structured accessibility snapshots, bypassing the need for screenshots or visually-tuned models") + the modelcontextprotocol/servers Puppeteer archived reference ("Browser automation and web scraping"), both MIT, both catalog-description-verified; zero upstream code, zero new pip (the browser is the house's own playwright>=1.48 + chromium from Motion v0.63 / Computer Operator v0.67), zero new keys. NINE ACTIONS, every answer ONE envelope {schema_version, ok, tool, action, ..., meta{elapsed_ms, browser}, error{code, message, hint}}: open (SSRF-guarded public http(s) through the house's own scrape-lane guard - loopback / RFC1918 / link-local / 169.254 metadata never fetched - plus the lane's inert local about:blank / data:text/html scratch pages, capped 16k) | snapshot (the page's interactive tree with refs e1, e2... + its visible text capped 4k - the playwright-mcp law: a fresh snapshot rides EVERY answer, refs live only until the page changes) | click (ONE real click through a ref: get_by_role(role, name).nth(n) with the TAG verified before the click so a stale ref cannot land on a stranger; stale or unknown = honest NOT_FOUND naming the fresh-snapshot hint) | type (fill textbox / searchbox / contenteditable, a combobox takes select_option, submit=true presses Enter after) | press (ONE named key from the printed allowlist - Enter, Tab, Escape, Backspace, Delete, arrows, Home/End/PageUp/PageDown/Space, or one character; no chords, no scripts) | console (this browser's own tail: page logs + uncaught pageerrors, capped 40 x 200 chars, clear=true empties) | tabs (list | select | new | close, capped 4 - closing the last tab shuts the browser) | screenshot (ONE PNG into data/jharokha/<tenant>/, path + bytes back, never base64; over 5 MB = honest TOO_BIG) | close (RAM hygiene; the next open relaunches clean). THE LAWS: the refs come from a house-sized DOM walk (playwright 1.57 has no page.accessibility) - role + name + nth among the same, re-runnable, tag-verifiable, 250 refs max; RAM discipline (MEM-CURE): at most 2 tenant browsers alive server-wide (an extra tenant = honest BUSY), at most 4 tabs each, an idle reaper closes any browser idle > 180 s on its 30 s tick and again defensively before every action; ONE owner daemon loop owns all of playwright forever (its objects are loop-bound), actions submitted thread-safe and awaited with a 60 s belt, serialized per tenant with one lock; ephemeral by design - no profile, no cookies on disk, nothing shared across tenants; the tree lines / page text / console messages pass operator.browser mask_ids like every scraping surface (navigation truth page.url + title and local file paths do not - masked hrefs would be unreadable and the model clicks by ref); no evaluate, no downloads, no file://, no uploads, no credentials - the agentic door for those stays the Computer Operator (browser_worker); kill switch jharokha_enabled (off = every action NEED_SETUP, honest), and a server without the browser stack says NEED_SETUP naming the setup command. Tests: NEW test_v0664_jharokha_manch.py (27) - a real headless Chromium, every page a data:text/html scratch page so the whole suite is OFFLINE: the open + snapshot shape, a click that really changes the page, unknown + stale refs, type + submit through a form's onsubmit, select_option through the combobox, the press allowlist, the console tail + clear, the tabs lifecycle + the 4-tab cap, the screenshot landing with real bytes, the guard (loopback / metadata / file:// / ftp:// / non-html data: / over-cap data: / empty url), no-page honesty on a fresh tenant, close honest both ways, the kill switch, the idle reaper (stale closed, next open relaunches), the global cap (a second tenant = BUSY), tenant isolation, the 250-ref walk cap, the envelope shape, registry 607 pin, the enum pin, APP_VERSION pin. Version ritual 0.664.0 -> 0.665.0 (the re-version onto their ASLI SAMAY base; the first pass scripts/ritual_v0664.py + scripts/repair_pins_v0664.py for the 12 expression-form pins the blanket replace had bent, the re-version + compression pass scripts/ritual_v0665*.py): pubspec 0.665.0+671, pins ->0.665.0(+671) (the APP_VERSION asserts + the pubspec-string pins + registry 606 -> 607 with the note appended, incl. the two meta-pins omnipack's bare count and aep1's pin-on-the-pin + the console cache-busters, zero residual), CLAUDE.md current-version line + this section, docs/WORKLOG.md Task 39, docs/HISTORY.md section. Server-only deploy: old APKs keep working; no new pip; one new kill switch, default on. Previous: v0.664.0 ASLI SAMAY (their - the website is built in front of her - R1 every section Opus writes (page parts, look tops, fix rounds, changes) is STREAMED (same request, same tokens; `site/stream.py` pulls the half-written html / css out of the arriving JSON into a live slot, a retry clears it, the saved section is checked exactly as before) and GET /api/sites/{ref}/live sends only the added characters; R2 the Studio's live canvas = the real site (preview `__build/`) with every section in a slot and the unwritten ones as places they will grow into, each section growing word by word with a cursor and a 'Writing: Menu' tag, half-written code never runs (scripts / handlers / javascript: links removed, sandboxed frame, `assets/hoola-build.js`), Follow keeps the part being written in view, a page strip; R3 Code shows each part typing out, parallel parts each in a tab, 'Designing this section…' while Opus thinks; R4 the three looks grow side by side (`__build/__look/<i>/` in each look's own colours) and the chosen look stays on screen through the build; R5 a change to a built site (her chat, a fix round) switches the screen to the live build at its first word, then 'New version vN is ready' + Before / after (preview `__v/<n>/`). Switch SITE_LIVE_STREAM.) Previous: v0.663.0 STUDIO JAANCH (owner: 'go to every section of web studio in hoola web console check every section is fuctional or not end to end'): every Web Studio (webstudio) section walked in a real browser; fixed Download ZIP / React (new GET /api/sites/{ref}/download), Publish draws the DNS records + her apply tap + a 3-resolver check + Undo, no /moves 404, History marks the live version, Health name fallback; 3 tests, v0.662.0 KAAM SAAF (Wave 4 of the flaw audit: guarded worker slots, late reminders said late + no night ring, Stop during prep kept, Google backoff for background watchers + a daily notice, honest Kaam list; 19 tests), v0.661.0 YAAD SAHI (Wave 3: phone / order numbers kept, pinned facts update, corrections everywhere), v0.660.0 CALL KI YAAD (Wave 2: calls read the chat, side records, no dead-air billing, hang-up notes saved), v0.659.0 KAAN W4 BOLI SE KITAAB (transcript exports srt/vtt/txt/json + to_gyaan + the translate proof), v0.658.0 SAAF DIKHE (Studio chat live steps + timer, project menu), v0.657.0 PAKKA KAAM (Wave 1: restart resumes, one-tap cards, honest failures), v0.656.0 KAAM DIKHE (the Studio shows every build step with live timers), v0.655.0 SACH KA PEHRA (no false 'done'), v0.654.0 BHEJA TO DIKHA (a sent line shows at once), v0.653.0 SACHCHA NATIJA (truthful task states), v0.652.0 STUDIO BAR SEEDHA (the ask row stays one line), v0.651.0 JAWAB MIL GAYA (a call knows when she answers a card), v0.650.0 HOOLA WEB STUDIO (the website builder as its own app, three full looks), v0.649.0 SACH MEIN ROKO (a real cancel on every surface), v0.648.0 KAAM KA HISAAB (one work list), v0.647.0 ALAG CALL, EK YAAD (calls on their own record), v0.646.0 WEB DEVELOPMENT PANEL 2, v0.645.0 KHULA LOOP, v0.644.0 BINA RUKE, v0.643.0 HAMESHA HAIKU, v0.642.0 SAAF RAASTA, v0.641.0 PEHLE SE TAIYAAR, v0.640.0 PAKDO, v0.639.0 KAAN W3 APNI BOLI (per-tenant whisper vocab + five transcript styles), v0.638.0 TEZ TAIYARI, v0.637.0 KAHAN RUKA, v0.636.0 WEB DEVELOPMENT PANEL, v0.624-v0.635 = the other sessions' voice / Haiku / timing work (their own lines in git history), v0.623.0 KOI PATA NA KHOYE (301s + keep-my-look + photo byte checks), v0.622.0 SAHI SAMAY + SIRF GEMINI (relative reminders counted by the server + calls Gemini-only), v0.621.0 YAAD KI GHANTI (a due reminder rings her and is spoken), v0.620.0 BHANDAR MANCH (the T2 local-core family, owner 'T2 Local Core -- START': ONE tool `bhandar` - beds | sql | md | json | ast | time - READ-ONLY over the tenant's own SQLite beds + workspace markdown / JSON / AST + IANA time, the three-belt sql gate ending in mode=ro, IDEA-ONLY from the no-credential local-bed rows of download/HOOLA_MCP_FEED.json; built as 0.618.0, REBASE PROTOCOL #11), v0.618.0 HAMESHA JUDA (the 24/7 call that parks Gemini when quiet), v0.617.0 KUCHH NA CHHOOTE + PEXELS KA NAAM, v0.616.0 BAHAR SE BAAT (her Hoola from WhatsApp / Telegram / Slack / Teams), v0.615.0 YAAD SE + SUDHAAR YAAD, v0.614.0 CONSTRUCTION WAVE 4 (five NEW desks + six desk extensions, registry 605), v0.612.0 BIMA RISK, v0.611.0 YAAD KE KHAANE, v0.610.0 BIMA ASSIST, v0.609.0 BIMA DESK, v0.608.0 EK YAAD + JUST IN TIME, v0.607.0 RETAIL WAVES 2+3, v0.606.0 SAAF NAZAR + DUKAAN DESK, v0.604.0 YAAD SACH, v0.603.0 RISK DESK, v0.602.0 VITT SAHAYAK, v0.601.0 KAAN PACK (WhisperAI W0), v0.600.0 HOOLA AEP 1.0 (their P8, the train's LAST phase: the 100% parity audit as server/app/aep/audit.py - 230/230 verified LIVE, the openwiki analog; the whole train: P1 CORE 0.510 (the langchain-core clone as server/app/aep), P2 TRACE 0.520 (the LangSmith layer as server/app/aep/tracers.py), P3 GRAPH 0.530 (the state-graph engine as server/app/aep/graph.py), P4 AGENT 0.549 (create_agent as server/app/aep/agent.py), P5 MIDDLEWARE 0.566 (HOOLA MIDDLEWARE - the 24 hooks as server/app/aep/middleware.py), P6 RETRIEVE 0.580 (HOOLA RETRIEVE - the retrieval layer as server/app/aep/retrieve.py: Document/Embeddings, the sqlite-first vector store, RecordManager + index()/aindex() with the content-hash dedup, the text splitters, the retrievers), P7 HUB 0.589 (init_chat_model + the BYOK adapter + the MCP client adapter + conformance as server/app/aep/{hub,load,mcp,conformance}.py), P8 AEP 1.0 0.600), v0.590.0 SANDARBH MANCH (the T1 reference family, owner 'T1 Reference - deploye it for hoola - only in backend for hoola ai': `workspace` (the confined per-tenant file desk) + `kgmemory` (the knowledge-graph memory), the modelcontextprotocol/servers idea IDEA-ONLY, registry 584), v0.589.0 HOOLA HUB, v0.587.0 PAISA SAHAYAK, v0.569.0 SPEC SUTRA (the spec-driven ladder, one `speckit` tool, the github/spec-kit idea IDEA-ONLY), v0.559.0 REACH MANCH (the Agent-Reach discipline layer - one `reach` tool, one envelope, ordered backends with health memory + cooldowns; the v0.559 discipline shape every idea-lane since rides) [full chains in git history].

def _quiet_http_logs() -> None:
    """v0.190.1 P0: every TV-catalog health probe logged an INFO line to stderr - thousands per refresh,
    the error log and the disk drowned while the box crawled. Warnings and above still come through.
    Tool traffic is unaffected: inbound access is uvicorn.access, a different logger, untouched."""
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

def _mark_jobs_on_stop_signal() -> int:
    """v0.343 A deploy (pm2 restart = SIGINT / SIGTERM) must never fail a running website build. v0.332 marked the jobs at
    the END of the app's shutdown - but the server waits there for long-lived connections (live chat streams, PC links)
    and is force-stopped ("Aborted!" in the deploy log), so that step never ran. Now the marking happens the moment the
    stop signal arrives, then uvicorn's own handler carries on as before. Returns how many signals were wrapped."""
    import signal
    import threading
    if threading.current_thread() is not threading.main_thread():
        return 0                                          # signals belong to the main thread (tests run lifespan elsewhere)
    n = 0
    for sig in (signal.SIGINT, signal.SIGTERM):
        old = signal.getsignal(sig)
        if getattr(old, "_hoola_marks_jobs", False):
            continue

        def handler(signum, frame, _old=old):
            try:
                from .site import service as _site_service
                _site_service.mark_clean_stop()
            except Exception:
                log.exception("website jobs not marked on stop signal")
            if callable(_old):
                _old(signum, frame)
            elif _old == signal.SIG_DFL:
                signal.signal(signum, signal.SIG_DFL)
                signal.raise_signal(signum)
        handler._hoola_marks_jobs = True
        try:
            signal.signal(sig, handler)
            n += 1
        except (ValueError, OSError):
            log.info("stop signal %s not wrapped", sig)
    return n


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _mark_jobs_on_stop_signal()   # v0.343 a deploy marks running website jobs at the signal, not at the (often aborted) end
    _quiet_http_logs()
    from . import authcheck as _authcheck
    _authcheck.warn_if_open()  # v0.391 an empty API_KEY = a request with no login acts as the owner: say so loudly in the log
    from . import usage as _usage
    _usage.install()          # v0.98 every Claude / Gemini call is counted (owner, feature, cost)
    try:   # v0.641 the 606 tool schemas are checked in the background at start, never on the first turn's loop
        from .agent import toolsearch as _ts_warm
        _ts_warm.warm()
        if get_settings().model_profile:   # v0.739 read what the chat model can do, off the event loop
            from .agent import modelprofile as _mp_warm
            _mp_warm.refresh_in_background()
            from . import modelchoice as _mc_warm
            _mc_warm.warm()
    except Exception:
        log.exception("tool warm-up not started")
    try:   # wave 13: the loop watchdog runs from start (it used to start only on the first call brain turn)
        from . import looplag as _looplag
        _looplag.start()
    except Exception:
        log.exception("looplag not started")
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run_forever(stop))
    if get_settings().logo_warm:
        from .bazar import logos
        logos.warm_in_background()   # fetch every plugin logo once, gently, so the Connect tab is quick
    if get_settings().tv_refresh:
        from .tv import catalog as tv_catalog
        tv_catalog.refresh_in_background()   # Hoola TV: re-check the free channels every night
    if get_settings().video_edit_worker:
        from .videoedit import service as video_service
        video_service.resume_pending()        # v0.65 edits that were running when the server restarted
    if get_settings().ifsc_refresh:
        from .india import ifsc
        ifsc.refresh_in_background()          # v0.59 IFSC branch details, once a month
    try:                                       # v0.137 Tech suite modules read these from the environment
        import os as _os
        from .cyber import service as _cyber_svc
        _st = get_settings()
        _cyber_svc.SLEEP_BETWEEN_S = float(_st.cyber_sleep_between_s or 0)
        if _st.cyber_certin_feed:
            _os.environ.setdefault("CYBER_CERTIN_FEED", _st.cyber_certin_feed)
        if not _st.devops_llm:
            _os.environ.setdefault("DEVOPS_LLM", "false")
        if not _st.customs_llm:                 # v0.139 Safar suite
            _os.environ.setdefault("CUSTOMS_LLM", "false")
        if not _st.contracts_llm:               # v0.150 Kanoon suite
            _os.environ.setdefault("CONTRACTS_LLM", "false")
        for _k, _v in (("COURIER_DIR", _st.courier_dir), ("COURIER_BLUEDART_BASE", _st.courier_bluedart_base),
                       ("LOGISTICS_DIR", _st.logistics_dir), ("SITESUP_DIR", _st.sitesup_dir),
                       ("MOTIONDESK_DIR", _st.motiondesk_dir), ("PHOTOASSIST_DIR", _st.photoassist_dir), ("GRAPHIC_DIR", _st.graphic_dir)):
            if _v:
                _os.environ.setdefault(_k, _v)
        if _st.courier_poll_min:
            from .courier import service as _courier_svc
            _courier_svc.POLL_MIN = int(_st.courier_poll_min)
    except Exception:
        log.exception("tech suite settings")
    from .operator import service as operator_service
    operator_service.MAIN_LOOP = asyncio.get_running_loop()   # v0.67 Computer Operator jobs run on this loop
    if get_settings().operator_worker:
        operator_service.resume_pending()     # a restart closes the browser: those jobs stop honestly
    if get_settings().studio_on and get_settings().operator_worker:
        from .studio import service as studio_service
        asyncio.ensure_future(studio_service.resume_all())   # v0.68 AI video shots already submitted keep being followed
    yield
    try:                         # v0.330 a deploy is not a crash: running website jobs continue after the restart
        from .site import service as _site_service
        _site_service.mark_clean_stop()
    except Exception:
        log.exception("website clean stop")
    stop.set()
    await task
    _usage.flush()               # v0.98 counted calls are not lost on a restart
    try:
        await operator_service.shutdown()
    except Exception:
        pass


app = FastAPI(title="Santosh Core", version=APP_VERSION, lifespan=lifespan)


@app.middleware("http")
async def _hosted_sites(request: Request, call_next):
    """v0.122 Websites Hoola launched are served from this server by their hostname (free Hoola address or her domain)."""
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if host and "." in host and not host.startswith(("127.", "localhost")):
        from .site import hosting as _hosting
        hm = _hosting.host_map()
        if host in hm:
            if request.method in ("GET", "HEAD"):
                res = await asyncio.to_thread(_hosting.serve, host, request.url.path,
                                              request.headers.get("user-agent") or "",
                                              request.headers.get("if-none-match") or "",
                                              request.headers.get("x-hoola-edge") == "1")
                if res is not None:
                    code, body, ctype, headers = res
                    return Response(content=b"" if request.method == "HEAD" or code == 304 else body, status_code=code,
                                    media_type=ctype, headers=headers)
            elif not request.url.path.startswith("/api/site-forms/"):
                # v0.223 a site's address never reaches Hoola's API: only its own enquiry form may POST here (before,
                # every non-GET fell through, e.g. POST https://her-domain/api/console/login answered)
                return Response(content=b"not found", status_code=404, media_type="text/plain")
    return await call_next(request)


@app.middleware("http")
async def _app_ops(request: Request, call_next):
    """v0.546 CHALTA KAAM (Pillar L): how fast her app's own backend answers, and what fails.

    One funnel for all ~80 /api/app-api/ routes: the real thing on every call, nothing to remember to switch on.
    A telemetry failure never touches the answer - the request is served either way.
    """
    path = request.url.path
    if not path.startswith("/api/app-api/"):
        return await call_next(request)
    t0 = time.monotonic()
    status = 500
    try:
        res = await call_next(request)
        status = res.status_code
        return res
    finally:
        try:
            from .appmaker import ops as OPS
            parts = path.split("/")
            OPS.seen(parts[3] if len(parts) > 3 else "", (time.monotonic() - t0) * 1000, status, path)
        except Exception:                                   # noqa: BLE001
            pass


@app.middleware("http")
async def _usage_scope(request: Request, call_next):
    """v0.98 Model calls made while serving this request are counted for its owner (resolved only if a model is called)
    and for a feature named by the path."""
    from . import usage

    def who() -> str:
        try:
            return _resolve_tenant(request)
        except Exception:
            return ""
    usage.bind(feature=usage.feature_for_path(request.url.path), resolver=who)
    return await call_next(request)


def _operator_ok() -> bool:
    try:
        from .operator.service import available
        return available()
    except Exception:
        return False


def _pg_ok() -> bool:
    try:
        import psycopg  # noqa: F401
        return True
    except ImportError:
        return False


def _blender_ok() -> bool:
    try:
        from .blender3d.sandbox import find
        return bool(find())
    except Exception:
        return False


def _qa_ok() -> bool:
    try:
        from .qa.runner import available
        return available() == ""
    except Exception:
        return False


def _bearer(request: Request) -> str:
    # v0.391 header only: a key or login token in the address (?key=) lands in nginx logs and browser history; no Hoola
    # client sends one there (phone, Android, console and both desktop apps all use the Authorization header)
    return request.headers.get("authorization", "").removeprefix("Bearer ").strip()


def current_tenant(request: Request) -> str:
    """Resolve the caller: a product session token -> that user; the legacy API key -> 'default'."""
    t = _resolve_tenant(request)
    from . import offline
    offline.touch(t)   # any call from the phone means it is online
    return t


def _resolve_tenant(request: Request) -> str:
    from . import accounts
    tok = _bearer(request)
    st = get_settings()
    if st.api_key and tok and hmac.compare_digest(tok, st.api_key):
        return st.tenant_id
    uid = accounts.tenant_for_session(tok) if tok else None
    if uid:
        return accounts.tenant_of_user(uid)
    if not st.api_key:
        return st.tenant_id
    raise HTTPException(401, "Sign in first")


def require_key(request: Request) -> None:
    from . import accounts
    key = get_settings().api_key
    got = request.headers.get("authorization", "").removeprefix("Bearer ").strip()   # v0.391 never ?key= (see _bearer)
    if key and got and hmac.compare_digest(got, key):
        return
    if got and accounts.tenant_for_session(got):   # a signed-in product user
        return
    if not key:
        return
    raise HTTPException(401, "Missing or wrong API key")


def _conv_or_404(conversation_id: str, tenant: str) -> Conversation:
    with session() as s:
        c = s.get(Conversation, conversation_id)
        if not c or c.tenant_id != tenant or c.deleted:     # v0.162 a deleted chat is gone from links too
            raise HTTPException(404, "Conversation not found")
        return c


# ---------------- health + demo page ----------------
@app.get("/healthz")
def healthz():
    st = get_settings()
    from .voice import MALE_VOICES
    from . import mail
    from .voiceid import engine as _vid_engine
    features = ["routines", "voice", "web", "bazar", "avatar", "bluetooth", "chat_files", "public_apis", "reels", "employee", "procedures", "darzi", "chai", "office", "lekhak", "mobile_shop", "phone_doctor", "gst", "payroll", "finance", "audit", "telecall", "insurance", "seo", "kalam", "thok", "niryat", "ads", "franchise", "theka", "brand", "website", "hoola_screen", "app_design", "app_android", "seva", "helpdesk", "shikayat", "aftersales", "feedback", "wapsi", "samudaay", "gyaan", "kaam_watch", "app_ideas", "devsahayak", "itadmin", "isp_noc", "cyber", "devops", "docwriter", "app_review", "product", "customs", "travel", "warehouse", "fleet", "courier", "drivers", "logistics", "propagent", "rentdesk", "site_supervisor", "interior", "archassist", "society", "vakil", "legal_research", "compliance", "contracts", "cosec", "notary", "pidesk", "dpo", "front_office", "eventplan", "shaadi", "tourguide", "homestay", "banquet", "edit_desk", "motiondesk", "patrakar", "photoassist", "artistmgr", "kitab", "podcast", "influencer", "graphic"] + (["film_desk"] if shutil.which("ffmpeg") else []) + (["qa"] if _qa_ok() else []) + (["callcentre"] if st.public_base_url and st.gemini_api_key else []) + (["video_editor"] if shutil.which("ffmpeg") else []) + (["blender_3d"] if _blender_ok() else []) + (["postgres"] if _pg_ok() else []) + (["computer_operator"] if _operator_ok() else []) + (["video_studio"] if shutil.which("ffmpeg") and get_settings().studio_on else []) + (["voiceid"] if _vid_engine.available() else []) + (["realtime_voice", "google_search"] if st.gemini_api_key else []) + (["side_talk"] if st.gemini_api_key and st.voice_side_talk else []) \
        + (["email"] if (mail.configured() or __import__("app.mailbox.accounts", fromlist=["x"]).oauth_ready("google")
                         or __import__("app.mailbox.accounts", fromlist=["x"]).oauth_ready("microsoft")) else []) + (["calendar"] if (__import__("app.gcal", fromlist=["x"]).configured()
                            or __import__("app.cal.accounts", fromlist=["x"]).oauth_ready()) else []) \
        + (["drive"] if __import__("app.gdrive", fromlist=["x"]).configured() else []) \
        + (["sheets"] if __import__("app.sheets.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["gdrive"] if __import__("app.drive.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["forms"] if __import__("app.forms.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["slides"] if __import__("app.slides.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["photos"] if __import__("app.photos.accounts", fromlist=["x"]).oauth_ready() else []) \
        + (["youtube"] if (st.youtube_api_key or __import__("app.youtube.accounts", fromlist=["x"]).oauth_ready()) else []) \
        + (["maps"] if __import__("app.maps", fromlist=["x"]).configured() else []) \
        + (["browser"] if __import__("app.browser", fromlist=["x"]).configured() else []) \
        + (["push"] if __import__("app.push", fromlist=["x"]).configured() else [])
    from . import accounts
    _wk = worker.health()          # wave 13: "ok" is false when the worker is stuck (it used to say ok regardless)
    return {"ok": bool(_wk.get("ok", True)), "worker": _wk, "app": "Hoola", "version": app.version, "google_login": accounts.oauth_configured(),
            "dry_run": st.wa_dry_run, "model": st.anthropic_model,
            "chat_brain": __import__("app.agent.llm", fromlist=["x"]).describe(),
            "chat_model_reads": _model_reads(),
            "brain_configured": bool(st.anthropic_api_key), "features": features,
            "voices": [{"id": k, "style": v} for k, v in MALE_VOICES.items()], "voice_default": st.voice_default,
            "bazar": {"packs": len(__import__("app.bazar.packs.registry", fromlist=["x"]).registry().packs),
                      "bills_live": __import__("app.bazar.config", fromlist=["x"]).get_settings().bills_live,
                      "mcp_directory": len(__import__("app.bazar.directory", fromlist=["x"]).servers()),
                      "agent_army": len(__import__("app.bazar.agents", fromlist=["x"]).agents())}}


def _model_reads() -> list[str] | str:
    """v0.739 what the chat model reads, from its own OpenRouter list ('unknown' when not read / switched off)."""
    try:
        from .agent import modelprofile as _mp
        return _mp.get().get("inputs") if _mp.known() else "unknown"
    except Exception:
        return "unknown"


@app.get("/api/model/profile", dependencies=[Depends(require_key)])
def model_profile_view():
    """v0.739 what the configured chat model can do (pictures, tools, reasoning, window, price), as read from its list."""
    from .agent import modelprofile as _mp
    return _mp.summary()


class ModelChoiceIn(BaseModel):
    model: str = ""


@app.get("/api/model/choices", dependencies=[Depends(require_key)])
def model_choices(tenant: str = Depends(current_tenant)):
    """v0.740 the composer dropdown: the owner's model list, each described from its own OpenRouter list."""
    from . import modelchoice
    return modelchoice.view(tenant)


@app.put("/api/model/choice", dependencies=[Depends(require_key)])
def model_choice_set(body: ModelChoiceIn, tenant: str = Depends(current_tenant)):
    """v0.740 her pick ('' = the default); her next message runs on it."""
    from . import modelchoice
    try:
        return modelchoice.choose(tenant, body.model)
    except modelchoice.ChoiceError as e:
        raise HTTPException(400, str(e))


@app.post("/api/model/profile/refresh", dependencies=[Depends(require_key)])
async def model_profile_refresh():
    """v0.739 read the model's list again now (after GLM_MODEL changed and the server restarted, or to check)."""
    from .agent import modelprofile as _mp
    await asyncio.to_thread(_mp.refresh)
    return _mp.summary()


# ----------------------------------------------------------------------------- Hoola website on the Hoola server
_SITE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
             "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; "
             "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
_SITE_HEADERS = {"Content-Security-Policy": _SITE_CSP, "X-Content-Type-Options": "nosniff",
                 "Referrer-Policy": "strict-origin-when-cross-origin", "X-Frame-Options": "DENY",
                 "Cache-Control": "public, max-age=300"}


def _site_page(slug: str):
    return FileResponse(STATIC / "site" / f"{slug}.html", media_type="text/html", headers=_SITE_HEADERS)


@app.get("/")
def index():
    """The Hoola website (home). Every page has a Console button -> /console/. Websites Hoola launched for owners are
    served before this by their own hostnames (_hosted_sites)."""
    return _site_page("home")


@app.get("/employee")
def site_employee():
    return _site_page("employee")


@app.get("/network")
def site_network():
    return _site_page("network")


@app.get("/studio")
def site_studio():
    """v0.349 The Create Studio page of the Hoola website (real studio screens in static/site/studio/)."""
    return _site_page("studio")


@app.get("/websites")
def site_websites():
    """v0.739 The Web Development page of the Hoola website: the Web Studio (/console/web) shown in drawn
    scenes - the brief, the plan, the three looks, the live build, the checks and the launch card."""
    return _site_page("websites")


@app.get("/apps")
def site_apps():
    """v0.739 The App Development page of the Hoola website: the App Studio (/console/apps) shown in drawn
    scenes - the plan card, the three looks of the Home screen, the prototype and the store steps."""
    return _site_page("apps")


@app.get("/api/site/showcase")
async def site_showcase():
    """v0.349 Public: which showcase slots have a real Hoola-made picture / clip (the owner makes them in Create > Engines >
    Showcase). The website's samples wall swaps its drawn scenes for these; nothing else of the owner's studio is shown."""
    from .studio import showcase
    return JSONResponse({"slots": await asyncio.to_thread(showcase.manifest)}, headers={"Cache-Control": "public, max-age=300"})


@app.get("/api/site/showcase/{slot}/{kind}")
async def site_showcase_file(slot: str, kind: str):
    from .studio import showcase
    try:
        f = await asyncio.to_thread(showcase.file_for, slot, kind)
    except showcase.ShowcaseError:
        raise HTTPException(404, "Not made yet")
    return FileResponse(f, headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"})


@app.get("/chat")
def old_web_chat():
    """The old one-page web chat (API key in the browser) that used to be at /. The Hoola Console replaces it."""
    return FileResponse(STATIC / "index.html")


@app.get("/download")
async def download_app():
    """Website download buttons: always the newest Android APK from the GitHub releases (cached 10 min); if GitHub
    can't be reached, the releases page."""
    from . import appupdate
    try:
        latest = await asyncio.to_thread(appupdate.latest)
    except Exception:
        latest = None
    url = (latest or {}).get("apk_url") or f"https://github.com/{appupdate._repo()}/releases"
    if not str(url).startswith("https://github.com/"):
        url = "https://github.com/fibernetworkworks-droid/santosh-app/releases"
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "no-store"})


# ----------------------------------------------------------------------------- v0.127 Hoola Screen (view-only second screen)
@app.get("/api/screen/link")
def screen_link(request: Request, days: int = 30, tenant: str = Depends(current_tenant)):
    from . import screen
    base = get_settings().public_base_url or str(request.base_url).rstrip("/")
    return screen.link(tenant, base, days)


@app.post("/api/screen/revoke")
def screen_revoke(tenant: str = Depends(current_tenant)):
    from . import screen
    return screen.revoke(tenant)


@app.get("/api/screen/preview")
def screen_preview(tenant: str = Depends(current_tenant)):
    from . import screen
    return screen.board(tenant)


@app.get("/api/screen/{token}/board")
def screen_board(token: str):
    """Public but read-only: the signed link is the only key; nothing can be changed from here."""
    from . import screen
    try:
        t = screen.tenant_of(token)
    except screen.ScreenError as e:
        raise HTTPException(403, str(e))
    return JSONResponse(screen.board(t), headers={"Cache-Control": "no-store"})


@app.get("/screen/{token}")
def screen_page(token: str):
    from . import screen
    try:
        screen.tenant_of(token)
    except screen.ScreenError as e:
        return HTMLResponse(f"<meta name=viewport content='width=device-width'><body style='font:20px system-ui;"
                            f"background:#0d1017;color:#eee;padding:40px'>{e}</body>", status_code=403)
    return HTMLResponse(screen.page(), headers={
        "Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                   "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'"})


@app.get("/terms")
def terms():
    """v0.342 Terms of service (Play / App Store listing, Google OAuth consent screen, sign-up)."""
    return FileResponse(STATIC / "terms.html")


@app.get("/privacy")
def privacy():
    """Privacy policy (Play listing link): what each permission is used for, incl. v0.84 payment-alert reading."""
    return FileResponse(STATIC / "privacy.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------------- conversations ----------------
MESSAGE_MAX = 32000   # v0.227.2 long pasted briefs (was 4000 -> 422); Text column, the model reads it whole

class NewMessage(BaseModel):
    text: str = Field(min_length=1, max_length=MESSAGE_MAX)
    voice: bool = False   # spoken in voice mode: Santosh answers short and speakable
    client_id: str | None = Field(default=None, max_length=64)   # same id again = the phone retrying a send; run it once
    files: list[str] = Field(default_factory=list, max_length=6)   # file_ids from /conversations/{id}/files


# (tenant, conversation, client_id) of recent sends, so a retry after a timeout never makes Santosh act twice
_SEEN_SENDS: "OrderedDict[tuple[str, str, str], float]" = OrderedDict()


def _already_sent(tenant: str, conversation_id: str, client_id: str | None) -> bool:
    if not client_id:
        return False
    now = time.monotonic()
    while _SEEN_SENDS and (len(_SEEN_SENDS) > 2000 or now - next(iter(_SEEN_SENDS.values())) > 600):
        _SEEN_SENDS.popitem(last=False)
    key = (tenant, conversation_id, client_id)
    if key in _SEEN_SENDS:
        return True
    _SEEN_SENDS[key] = now
    return False


@app.post("/api/conversations", dependencies=[Depends(require_key)])
def create_conversation(tenant: str = Depends(current_tenant), project_id: str = "", reuse: bool = False,
                        incognito: bool = False):
    # (tenant stays the FIRST argument: /api/bootstrap calls create_conversation(tenant) directly)
    if project_id:   # v0.164 "Naya chat" inside one of her projects
        from . import projects
        if not projects.enabled():
            raise HTTPException(404, "Projects are off (CHAT_PROJECTS)")
        try:
            projects.get(tenant, project_id)
        except projects.ProjectError as e:
            raise HTTPException(e.status, str(e))
    if reuse and not incognito:   # v0.233 the console's New chat: her newest untouched empty chat instead of one more "Naya chat"
        cid = _untouched_chat(tenant, project_id)
        if cid:
            from . import convs
            convs.mark(tenant, cid, "new")
            return {"id": cid, "reused": True}
    with session() as s:
        c = Conversation(tenant_id=tenant, project_id=project_id or None, incognito=True if incognito else None)
        s.add(c)
        s.flush()
        cid = c.id
    from .avatar.service import persona   # v0.244 her avatar's own name (was always "Santosh")
    greeting = f"Hello! I am {persona(tenant)[0]}, your AI coworker. What shall we get done today?"
    if incognito:   # v0.250 she must see it is incognito from the first line
        greeting = (f"🕶 Incognito chat. I am {persona(tenant)[0]} - what is said here will not go into your memory "
                    "and other chats will not know about it. Tell me, what would you like to do?")
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=greeting, display=greeting,
                      in_history=False, delivered_to_agent=True))
    bus.publish(cid, "message", {"role": "assistant", "text": greeting, "source": "greeting"})
    from . import convs
    convs.mark(tenant, cid, "new")
    if not incognito:   # v0.473 HOOLA CODER: a new chat opens a memory session - an INCOGNITO chat
        try:            # never does (her own promise: "yahan ki baatein yaad mein nahi jayengi")
            from . import coder
            coder.session_started(tenant, cid, "chat")
        except Exception:
            pass
    return {"id": cid, "incognito": bool(incognito)}


def _untouched_chat(tenant: str, project_id: str = "") -> str:
    """Her newest chat that nothing has happened in yet: only the greeting, no message of hers, no card, no note
    (a chat a background note already landed in is NOT untouched). Same session (project) only, never archived /
    deleted. Looks at her 5 newest chats, so a New chat tap is one small query."""
    from sqlalchemy import or_
    from .db import Event
    with session() as s:
        from .callconv import not_call   # v0.646 a call record is never reused as an empty chat
        q = select(Conversation.id).where(Conversation.tenant_id == tenant, not_call(),
                                          or_(Conversation.archived.is_(None), Conversation.archived.is_(False)),
                                          or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))
        q = q.where(Conversation.project_id == project_id) if project_id else \
            q.where(or_(Conversation.project_id.is_(None), Conversation.project_id == ""))
        for (cid,) in s.execute(q.order_by(Conversation.created_at.desc()).limit(5)).all():
            evs = s.execute(select(Event.kind, Event.payload).where(Event.conversation_id == cid).limit(3)).all()
            if all(k == "message" and (p or {}).get("source") == "greeting" for k, p in evs) and not \
                    s.execute(select(func.count(Message.id)).where(Message.conversation_id == cid,
                                                                   Message.role == "user")).scalar():
                return cid
    return ""



@app.post("/api/conversations/{conversation_id}/stop", dependencies=[Depends(require_key)])
def stop_turn(conversation_id: str, tenant: str = Depends(current_tenant)):
    """Rokiye: Hoola stops the task after the step it is on (nothing new starts).
    v0.186: an open goal of this chat stops with it (the goal card shows stopped)."""
    _conv_or_404(conversation_id, tenant)
    from .agent.santosh import stop
    stop(conversation_id)
    return {"stopped": True}

@app.get("/api/conversations/{conversation_id}/context", dependencies=[Depends(require_key)])
def get_context(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.237 FULL CLAUDE MODE: how full this chat's model window is (the last measured call, else an estimate),
    which form went out (full = word for word, net = oldest shortened, squeezed = after a 'too long'), and the gauge."""
    _conv_or_404(conversation_id, tenant)
    from .agent import context as _ctx
    return {"context": _ctx.reading(conversation_id), "gauge": _ctx.health()}

class AboutBody(BaseModel):
    text: str = Field(default="", max_length=4000)


class MemorySwitches(BaseModel):
    auto: bool | None = None      # "Khud yaad rakhna": Hoola picks up facts / writes her page by itself
    recall: bool | None = None    # "Purani chats se yaad": search, recent chats, her page
    sensitive: bool | None = None  # v0.609 "Sensitive baatein bhi": health / religion / politics... may be kept


@app.get("/api/memory/about", dependencies=[Depends(require_key)])
def about_get(tenant: str = Depends(current_tenant)):
    """v0.250 "Mere baare mein": the memory page Hoola keeps about her (+ her two switches)."""
    from . import aboutme, fence
    return {"about": aboutme.get(tenant), "switches": fence.prefs(tenant), "max_chars": aboutme.MAX_CHARS}


@app.put("/api/memory/about", dependencies=[Depends(require_key)])
def about_put(body: AboutBody, tenant: str = Depends(current_tenant)):
    """Her edit of the page (her words win over Hoola's next rebuild)."""
    from . import aboutme
    return {"about": aboutme.set_text(tenant, body.text)}


@app.delete("/api/memory/about", dependencies=[Depends(require_key)])
def about_delete(tenant: str = Depends(current_tenant)):
    from . import aboutme
    return {"about": aboutme.set_text(tenant, "")}


@app.post("/api/memory/about/rebuild", dependencies=[Depends(require_key)])
async def about_rebuild(tenant: str = Depends(current_tenant)):
    """Rewrite the page now from what is new (her tap)."""
    from . import aboutme
    v = await aboutme.rebuild(tenant, force=True)
    return {"about": v or aboutme.get(tenant), "changed": v is not None}


@app.get("/api/memory/settings", dependencies=[Depends(require_key)])
def memory_switches_get(tenant: str = Depends(current_tenant)):
    from . import fence
    return {"switches": fence.prefs(tenant)}


@app.put("/api/memory/settings", dependencies=[Depends(require_key)])
def memory_switches_put(body: MemorySwitches, tenant: str = Depends(current_tenant)):
    """v0.250 her memory switches (Claude's memory settings): stored on her profile."""
    from . import fence, life
    from .db import Profile
    life.get_profile(tenant)   # makes the row
    with session() as s:
        p = s.get(Profile, tenant)
        if body.auto is not None:
            p.memory_auto = bool(body.auto)
        if body.recall is not None:
            p.memory_recall = bool(body.recall)
        if body.sensitive is not None:
            p.memory_sensitive = bool(body.sensitive)
    return {"switches": fence.prefs(tenant)}


@app.get("/api/context/report", dependencies=[Depends(require_key)])
def context_report(days: int = 7, tenant: str = Depends(current_tenant)):
    """v0.246 FULL CLAUDE MODE proof, live: compactions per reason (+ average tokens before / after), how full her
    chats were at their last model call, the gauge's learned ratios and the Session fence counters."""
    from datetime import datetime, timedelta, timezone
    from .agent import compact, context
    from . import convs as _convs, fence
    compact.ensure_table()
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(int(days or 7), 90)))
    with session() as s:
        rows = s.execute(select(compact.ChatCompact.reason, func.count(), func.avg(compact.ChatCompact.tokens_before),
                                func.avg(compact.ChatCompact.tokens_after))
                         .where(compact.ChatCompact.tenant_id == tenant, compact.ChatCompact.status != "draft",
                                compact.ChatCompact.created_at >= since)
                         .group_by(compact.ChatCompact.reason)).all()
    mine = set(_convs.ids(tenant, 400))
    chats = sorted(({"conversation_id": c, "percent": r.get("percent"), "form": r.get("form"), "brain": r.get("brain"),
                     "real": r.get("real")} for c, r in context.LAST.items() if c in mine),
                   key=lambda x: -(x["percent"] or 0))[:20]
    return {"days": days,
            "compactions": [{"reason": r, "count": n, "avg_tokens_before": int(b or 0), "avg_tokens_after": int(a or 0)}
                            for r, n, b, a in rows],
            "chats": chats, "gauge": context.health(), "compact": compact.health(),
            "fence": {"on": fence.enabled(), **fence.STATS}}


@app.get("/api/conversations/{conversation_id}/compact", dependencies=[Depends(require_key)])
def get_compact(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.242 FULL CLAUDE MODE Phase 2: this chat's checkpoint summary (what the model reads in place of the older
    part) and its last few compactions."""
    _conv_or_404(conversation_id, tenant)
    from .agent import compact
    return {"active": compact.active(conversation_id), "recent": compact.recent(conversation_id),
            "health": compact.health()}


@app.post("/api/conversations/{conversation_id}/compact", dependencies=[Depends(require_key)])
async def post_compact(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.242 'Chat chhoti karo' (Claude's /compact): write the checkpoint now. Refused while Hoola works in this chat."""
    _conv_or_404(conversation_id, tenant)
    from .agent import compact
    from .agent.santosh import _locks
    if not compact.enabled():
        raise HTTPException(409, "Compaction is off (CHAT_CONTEXT=hoola or CHAT_COMPACT=false)")
    lk = _locks[conversation_id]
    if lk.locked():
        raise HTTPException(409, "Hoola is working in this chat right now - try again when the reply is done")
    async with lk:
        v = await compact.run(conversation_id, tenant, "manual")
    if v is None:
        return {"compact": None, "say": "Chat abhi chhoti hi hai - saar banane layak purani baatein nahi hain."}
    return {"compact": v}


@app.get("/api/conversations/{conversation_id}/goal", dependencies=[Depends(require_key)])
def get_goal(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.186 the working (or newest) goal of this chat, for the phone's goal card."""
    _conv_or_404(conversation_id, tenant)
    from .agent import goal
    v = goal.active_for(conversation_id)
    if v is None:
        with goal.session() as s:
            r = s.scalars(select(goal.GoalRun).where(goal.GoalRun.conversation_id == conversation_id)
                          .order_by(goal.GoalRun.updated_at.desc())).first()
            v = goal._row_view(r) if r is not None else None
    return {"goal": v}

@app.post("/api/conversations/{conversation_id}/goal/stop", dependencies=[Depends(require_key)])
def stop_goal(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.186 Rokiye for the goal only: the plan stops, the chat itself stays free."""
    _conv_or_404(conversation_id, tenant)
    from .agent import goal
    goal.mark_stopped(conversation_id)
    return {"stopped": True}

@app.post("/api/conversations/{conversation_id}/goal/continue", dependencies=[Depends(require_key)])
def continue_goal(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.223 'Aage badhao' on a long job that stopped to ask after its budget ran out: the SAME job carries on
    from where it stopped, with a fresh budget (done steps kept). 409 when nothing is waiting for that."""
    _conv_or_404(conversation_id, tenant)
    from .agent import goal
    v = goal.continue_now(tenant, conversation_id)
    if v is None:
        raise HTTPException(409, "No job in this chat is waiting for 'shall I go on?'.")
    return {"goal": v}

@app.get("/api/conversations/{conversation_id}/messages", dependencies=[Depends(require_key)])
def list_messages(conversation_id: str, limit: int = 0, tenant: str = Depends(current_tenant)):
    _conv_or_404(conversation_id, tenant)
    with session() as s:
        q = select(Message).where(Message.conversation_id == conversation_id, Message.display.is_not(None))
        if limit > 0:   # v0.62 the bubble / widget only need the last few
            rows = list(reversed(s.scalars(q.order_by(Message.id.desc()).limit(min(limit, 200))).all()))
        else:
            rows = s.scalars(q.order_by(Message.id)).all()
        return {"messages": [{"id": r.id, "role": r.role, "text": r.display, "at": r.created_at.isoformat()} for r in rows]}


@app.get("/api/conversations/{conversation_id}/harness-events", dependencies=[Depends(require_key)])
def harness_events(conversation_id: str, after: int = 0, limit: int = 100, tenant: str = Depends(current_tenant)):
    """v0.193 the harness session log of this chat (agent/eventlog.py): the machine-readable story of its turns -
    tools run, results, agents deployed, wakes. Read-only, for the console and debugging; the brain reads the same
    rows through the session_log tool."""
    _conv_or_404(conversation_id, tenant)
    from .agent import eventlog
    rows = eventlog.recent(conversation_id, limit=min(max(int(limit or 100), 1), 400))
    rows = [r for r in rows if r["id"] > after]
    return {"events": rows, "last_id": rows[-1]["id"] if rows else after}


@app.get("/api/conversations/{conversation_id}/request", dependencies=[Depends(require_key)])
def request_dump_list(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.732 PARITY Phase 0: the turns whose model requests were kept (newest request_dump_turns), with their brains."""
    _conv_or_404(conversation_id, tenant)
    from . import reqdump
    return {"turns": reqdump.turns(conversation_id, tenant), "on": reqdump.on()}


@app.get("/api/conversations/{conversation_id}/request/{turn}", dependencies=[Depends(require_key)])
def request_dump_turn(conversation_id: str, turn: str, tenant: str = Depends(current_tenant)):
    """v0.732 PARITY Phase 0: exactly what the model received on that turn (number 1..n, -1 = newest, or the turn id):
    every step's system prompt text, tool names, messages, brain / model and max_tokens - secrets masked."""
    _conv_or_404(conversation_id, tenant)
    from . import reqdump
    got = reqdump.turn(conversation_id, tenant, turn)
    if got is None:
        raise HTTPException(404, "No request kept for that turn")
    return got


@app.post("/api/conversations/{conversation_id}/messages", status_code=202, dependencies=[Depends(require_key)])
async def post_message(conversation_id: str, body: NewMessage, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    _conv_or_404(conversation_id, tenant)
    from . import turn_inbox as _ti0
    if (body.client_id and await asyncio.to_thread(_ti0.seen, tenant, conversation_id, body.client_id)) \
            or _already_sent(tenant, conversation_id, body.client_id):
        return {"accepted": True, "duplicate": True}
    from . import chatfiles, convs, turn_inbox
    convs.mark(tenant, conversation_id, "message")   # v0.158 this is the chat she is in: notes and cards come here
    context = chatfiles.context(tenant, body.files) if body.files else ""
    shown = chatfiles.shown(tenant, body.files) if body.files else []
    bus.publish(conversation_id, "message", {"role": "user", "text": body.text, "source": "user",
                                             **({"client_id": body.client_id} if body.client_id else {}),
                                             **({"files": shown} if shown else {})})
    ti_id = turn_inbox.accept(tenant, conversation_id, body.text, bool(body.voice), context, body.client_id or "")
    if context:
        background.add_task(turn_inbox.run_owned, ti_id, conversation_id, body.text, tenant, bool(body.voice),
                            context=context, client_id=body.client_id or "")   # v0.173 steering: take-back while queued
    else:
        background.add_task(turn_inbox.run_owned, ti_id, conversation_id, body.text, tenant, bool(body.voice),
                            client_id=body.client_id or "")
    return {"accepted": True}


@app.post("/api/conversations/{conversation_id}/files", dependencies=[Depends(require_key)])
async def chat_file(conversation_id: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """The chat / voice-call paperclip: ANY file (photo, PDF, video, Excel...), kept as the owner's file so Hoola can
    read it and send it on. A CSV / Excel with a phone column is also imported as a leads list (no error if not)."""
    _conv_or_404(conversation_id, tenant)
    from . import chatfiles
    data = await file.read(chatfiles.MAX_BYTES + 1)
    try:
        return await asyncio.to_thread(chatfiles.store, tenant, file.filename or "file", data, file.content_type or "")
    except chatfiles.FileError as e:
        raise HTTPException(413 if len(data) > chatfiles.MAX_BYTES else 400, str(e))


REPLAY_MAX = 3000   # v0.158 more events than this to catch up = the app reloads the chat in order instead


@app.get("/api/conversations/{conversation_id}/events", dependencies=[Depends(require_key)])
async def events(conversation_id: str, request: Request, after: int = 0, live: int = 0,
                 tenant: str = Depends(current_tenant)):
    """Server-sent events: everything after `after` (this chat + cards from her other chats), then live.

    v0.158: the catch-up is paged until it reaches now (it used to send the oldest 500 and then skip the rest), a
    `replay_end` marker tells the app when catching up is over (no more guessing with a timer), and a gap too big to
    catch up sends `resync` so the app reloads the chat in order instead of showing a broken one.

    v0.161 `live=1`: also the reply being written (reply_start / delta / delta_reset / reply_end, never stored, sent
    without an SSE id). Without it (older apps) the stream is exactly as before."""
    _conv_or_404(conversation_id, tenant)
    from . import convs
    last = int(request.headers.get("last-event-id") or after or 0)
    q = bus.subscribe(conversation_id, tenant)
    convs.mark(tenant, conversation_id, "stream")

    async def gen():
        try:
            sent = last
            if last > 0:
                total = 0
                while True:
                    page = await asyncio.to_thread(bus.backlog, conversation_id, sent, 500, tenant)
                    for ev in page:
                        sent = ev["id"]
                        yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    total += len(page)
                    if len(page) < 500:
                        break
                    if total >= REPLAY_MAX:   # away too long: reload the chat in order
                        sent = await asyncio.to_thread(bus.last_id, conversation_id, tenant)
                        yield f"data: {json.dumps({'id': 0, 'kind': 'resync', 'payload': {'why': 'gap'}})}\n\n"
                        break
            else:
                sent = await asyncio.to_thread(bus.last_id, conversation_id, tenant)   # the app loads /timeline first
            yield f"data: {json.dumps({'id': 0, 'kind': 'replay_end', 'payload': {'last': sent}})}\n\n"
            typed_at = time.monotonic()
            while True:
                if await request.is_disconnected():
                    break
                # v0.668 the typing refresh runs on the CLOCK (every ~45 s while a turn really runs), not only after
                # four idle 15 s waits: a busy turn sends step events every few seconds, so the stream was never idle
                # and the phone cleared the dots at 75 s while Hoola was still working - she thought it had stopped
                if live and time.monotonic() - typed_at >= 45:
                    typed_at = time.monotonic()
                    try:                      # (a crashed turn stops refreshing -> they clear)
                        from .agent.santosh import turn_running
                        if turn_running(conversation_id):
                            yield f"data: {json.dumps({'id': 0, 'kind': 'typing', 'payload': {'on': True}, 'live': True})}\n\n"
                    except Exception:
                        pass
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    from . import offline
                    offline.touch(tenant)   # the stream is still open: the phone is online
                    yield ": ping\n\n"
                    continue
                if ev.get("live"):
                    if live:
                        yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    continue
                if ev["id"] <= sent:
                    continue
                if ev["id"] > sent + 1:
                    # v0.668 an event published from a worker thread can reach this queue AFTER a newer one published on
                    # the loop - the high-water mark then dropped it for good (a card / message seen only on a reload).
                    # On a gap the events in between are read back from the database first, in order.
                    try:
                        gap = await asyncio.to_thread(bus.backlog, conversation_id, sent, 50, tenant)
                    except Exception:
                        gap = []
                    for g in gap:
                        if sent < g["id"] < ev["id"]:
                            sent = g["id"]
                            yield f"id: {g['id']}\ndata: {json.dumps(g, ensure_ascii=False)}\n\n"
                sent = ev["id"]
                yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            bus.unsubscribe(conversation_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/conversations/{conversation_id}/live", dependencies=[Depends(require_key)])
def chat_live(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.161 the reply being written right now ({turn, seg, seq, text}) so a reload continues it; 204 when none."""
    _conv_or_404(conversation_id, tenant)
    from . import livereply
    snap = livereply.snapshot(conversation_id)
    return snap if snap else Response(status_code=204)


@app.post("/api/conversations/{conversation_id}/retry", status_code=202, dependencies=[Depends(require_key)])
async def chat_retry(conversation_id: str, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    """v0.161 Dobara: her last message runs again and the new answer replaces the last reply (the old one is kept in
    the database as a branch). Nothing already sent / paid is repeated without a new card (see livereply.RETRY_NOTE)."""
    _conv_or_404(conversation_id, tenant)
    from . import chats, convs, livereply
    try:   # v0.162 CHAT_SESSIONS: the old reply stays as version 1 of 2 (‹ › arrows) instead of being replaced
        text, context = chats.retry(conversation_id) if chats.enabled() else livereply.prepare_retry(conversation_id)
    except (livereply.RetryError, chats.ChatError) as e:
        raise HTTPException(e.status, str(e))
    convs.mark(tenant, conversation_id, "message")
    from . import turn_inbox   # v0.666 Dobara rides the inbox: a restart re-runs it instead of losing it
    ti_id = turn_inbox.accept(tenant, conversation_id, text, False, context or "", "")
    background.add_task(turn_inbox.run_owned, ti_id, conversation_id, text, tenant, False, context=context or "")
    return {"accepted": True, "text": text}


class FeedbackIn(BaseModel):
    turn: str = Field(min_length=1, max_length=40)
    value: str = Field(max_length=8)
    note: str = Field(default="", max_length=500)


@app.post("/api/conversations/{conversation_id}/feedback", dependencies=[Depends(require_key)])
def chat_feedback(conversation_id: str, body: FeedbackIn, tenant: str = Depends(current_tenant)):
    """v0.161 thumbs up / down on one reply (counted in the usage report)."""
    _conv_or_404(conversation_id, tenant)
    from . import livereply
    try:
        return livereply.feedback(tenant, conversation_id, body.turn, body.value, body.note)
    except livereply.RetryError as e:
        raise HTTPException(e.status, str(e))


@app.get("/api/conversations/{conversation_id}/timeline", dependencies=[Depends(require_key)])
def chat_timeline(conversation_id: str, limit: int = 60, before: int = 0, steps: bool = False, own: bool = False,
                  tenant: str = Depends(current_tenant)):
    """v0.158 the chat in order: messages and each card once where it first appeared, in its latest state (cards from
    her other chats too), newest page last; `before` = the page before that event id.
    v0.171 `steps=1` (the console): tool-call step events ride along so the transcript keeps what each turn did."""
    _conv_or_404(conversation_id, tenant)
    from .events import timeline
    return timeline(conversation_id, tenant, limit, before, steps=steps, own=own)


@app.get("/api/conversations/{conversation_id}/timeline/head", dependencies=[Depends(require_key)])
def chat_timeline_head(conversation_id: str, n: int = 40, tenant: str = Depends(current_tenant)):
    """v0.158 the app's self-check: the newest story ids in order (missing / out of order on the phone = reload)."""
    _conv_or_404(conversation_id, tenant)
    from .events import head
    return head(conversation_id, tenant, n)


def _export_name(conv: Conversation, ext: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (conv.title or "hoola-chat")).strip("-").lower()[:40] or "hoola-chat"
    return f"{slug}-{time.strftime('%Y%m%d-%H%M')}.{ext}"


@app.get("/api/conversations/{conversation_id}/export", dependencies=[Depends(require_key)])
def chat_export(conversation_id: str, fmt: str = "md", tenant: str = Depends(current_tenant)):
    """v0.171 the whole chat as one file (console: Export). `fmt=md` reads like the chat itself — her messages,
    Hoola's replies and the steps of each turn in order; `fmt=json` keeps every stored event for keeping/backup.
    Live-only noise (typing, deltas, think) was never stored, so it is simply absent; cards from her other chats
    and old retry branches are marked as what they are, never shown as reply text."""
    if not (get_settings().console_v2 or get_settings().console_stream):
        raise HTTPException(404, "Export is off (CONSOLE_V2)")
    conv = _conv_or_404(conversation_id, tenant)
    from .db import Event
    from .events import LIVE_ONLY
    from .avatar.service import persona
    with session() as s:
        rows = s.scalars(select(Event).where(Event.conversation_id == conversation_id).order_by(Event.id)).all()
        rows = [e for e in rows if e.kind not in ("typing", "log")]      # pure noise never belongs in a file
    avatar = persona(tenant)[0] or "Hoola"
    when = lambda iso: (iso or "")[:16].replace("T", " ")                # noqa: E731  2026-10-25 16:20
    if fmt == "json":
        import json as _json
        body = _json.dumps({
            "conversation": conversation_id, "title": conv.title or "", "tenant": tenant,
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "version": APP_VERSION,
            "events": [{"id": e.id, "kind": e.kind, "at": e.created_at.isoformat() if e.created_at else None,
                        "payload": e.payload} for e in rows],
        }, ensure_ascii=False, default=str, indent=1)
        return Response(body, media_type="application/json; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{_export_name(conv, "json")}"'})
    out = [f"# {conv.title or 'Hoola chat'}", "", f"> {avatar} ki chat · export {time.strftime('%d %b %Y, %H:%M')} · Hoola Console", ""]
    n_steps = 0
    for e in rows:
        p = e.payload if isinstance(e.payload, dict) else {}
        at = when(e.created_at.isoformat() if e.created_at else None)
        if e.kind == "message":
            text = str(p.get("text") or "").strip()
            if not text or p.get("replaced_by") or p.get("taken_back"):
                continue                  # empty shell, the old retry branch, or a message she took back
            who = "Aap" if p.get("role") == "user" else avatar
            files = p.get("files") or []
            head = f"## {who} · {at}"
            if p.get("edited"):
                head += " · (badla hua)"
            out += [head, "", text, ""]
            for f in files:
                name = f.get("name") if isinstance(f, dict) else str(f)
                if name:
                    out += [f"- 📎 {name}", ""]
            n_steps = 0
        elif e.kind == "step":
            if p.get("state") == "running":
                continue                                  # the done / error step of the same call follows it
            mark = "✓" if p.get("state") == "done" else "✕"
            line = f"- {mark} {p.get('label') or p.get('tool') or 'kadam'} `{p.get('tool') or ''}`"
            brief = p.get("args") or []
            if brief:                                     # v0.171 what was asked (already masked server-side)
                line += " — " + ", ".join(f"{k} {v}" for k, v in brief[:4])
            elif p.get("detail"):
                line += f" — {p['detail']}"
            if not n_steps:
                out += ["**Kadam**", ""]
            out += [line]
            n_steps += 1
        elif e.kind not in LIVE_ONLY and e.kind != "message":
            out += [f"_(card: {e.kind})_"] if out and out[-1] == "" else []
    md = "\n".join(out).rstrip() + "\n"
    return Response(md, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{_export_name(conv, "md")}"'})


@app.get("/api/conversations", dependencies=[Depends(require_key)])
def chat_list(limit: int = 40, archived: bool = False, tenant: str = Depends(current_tenant)):
    """v0.158 her old chats (newest activity first): nothing is lost when she starts a new one.
    v0.162 CHAT_SESSIONS: one query, pinned first, titles, archive list (`archived=true`), busy flags."""
    from . import chats, convs
    if chats.enabled():
        return {"conversations": chats.chat_list(tenant, archived, limit), "current": convs.current(tenant)}
    return {"conversations": convs.chats(tenant, limit), "current": convs.current(tenant)}


@app.get("/api/calls", dependencies=[Depends(require_key)])
def calls_list(limit: int = 40, origin: str = "", tenant: str = Depends(current_tenant)):
    """v0.646 ALAG CALL: the Calls section - each voice call's own record (newest first). Open one like a chat
    (GET /api/conversations/<id>/events): transcript, tool rows, cards and the receipt are all there."""
    from . import callconv
    return {"calls": callconv.recent(tenant, origin=origin[:40] or None, limit=limit)}


@app.get("/api/conversations/search", dependencies=[Depends(require_key)])
def chat_search(q: str = "", tenant: str = Depends(current_tenant)):
    """v0.162 titles and message text of her chats; each hit has the event id to jump to.
    v0.178 backed by the FTS5 index (chatsearch): prefix words, Hinglish / Devanagari, bm25 rank, real snippets."""
    from . import chats
    if not chats.enabled():
        raise HTTPException(404, "Chat search is off (CHAT_SESSIONS)")
    return {"results": chats.search(tenant, q[:200])}


@app.get("/api/conversations/{conversation_id}/find", dependencies=[Depends(require_key)])
def chat_find(conversation_id: str, q: str = "", tenant: str = Depends(current_tenant)):
    """v0.178 in-chat find (console Ctrl+F): every live match of this chat in document order + a total count, so the
    find bar can walk 3/17 with the arrows and jumpTo can load older pages on the way."""
    _conv_or_404(conversation_id, tenant)
    from . import chatsearch, chats
    if not chats.enabled():
        raise HTTPException(404, "Chat search is off (CHAT_SESSIONS)")
    return chatsearch.find_in_chat(tenant, conversation_id, q[:200])


class ChatPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    pinned: bool | None = None
    archived: bool | None = None
    project_id: str | None = Field(default=None, max_length=40)    # v0.164 "" / null = out of the project


def _chats_on():
    from . import chats
    if not chats.enabled():
        raise HTTPException(404, "Many chats is off (CHAT_SESSIONS)")
    return chats


@app.patch("/api/conversations/{conversation_id}", dependencies=[Depends(require_key)])
def chat_patch(conversation_id: str, body: ChatPatchIn, tenant: str = Depends(current_tenant)):
    """v0.162 rename / pin / archive. v0.164 project_id: into / out of one of her projects."""
    out: dict = {}
    if "project_id" in body.model_fields_set:
        from . import projects
        if not projects.enabled():
            raise HTTPException(404, "Projects are off (CHAT_PROJECTS)")
        try:
            out = projects.set_chat(tenant, conversation_id, body.project_id or None)
        except projects.ProjectError as e:
            raise HTTPException(e.status, str(e))
        if not ({"title", "pinned", "archived"} & body.model_fields_set):
            return out
    chats = _chats_on()
    try:
        return {**out, **chats.patch(tenant, conversation_id, body.title, body.pinned, body.archived)}
    except chats.ChatError as e:
        raise HTTPException(e.status, str(e))


@app.delete("/api/conversations/{conversation_id}", dependencies=[Depends(require_key)])
def chat_delete(conversation_id: str, tenant: str = Depends(current_tenant)):
    """v0.162 soft delete (the console asks first): gone from the list, search and links; rows kept."""
    chats = _chats_on()
    _conv_or_404(conversation_id, tenant)
    try:
        return chats.delete(tenant, conversation_id)
    except chats.ChatError as e:
        raise HTTPException(e.status, str(e))


class ChatEditIn(BaseModel):
    event_id: int
    text: str = Field(min_length=1, max_length=MESSAGE_MAX)


async def _edited_turn(conversation_id: str, text: str, tenant: str, parent: int | None) -> None:
    from . import turn_inbox   # v0.666 an edited message rides the inbox: a restart re-runs it instead of losing it
    ti_id = await asyncio.to_thread(turn_inbox.accept, tenant, conversation_id, text, False, "", "")
    await turn_inbox.run_owned(ti_id, conversation_id, text, tenant, False)
    if parent:
        from .db import Message
        with session() as s:   # the new version of her message points to the one she edited
            row = s.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.role == "user",
                                                  Message.in_history.is_(True), Message.parent_id.is_(None),
                                                  Message.id > parent).order_by(Message.id)).first()
            if row is not None:
                row.parent_id = parent


@app.post("/api/conversations/{conversation_id}/edit", status_code=202, dependencies=[Depends(require_key)])
def chat_edit(conversation_id: str, body: ChatEditIn, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    """v0.162 her message edited: a new version from there (the old one stays, ‹ 1/2 ›); the new text runs as a turn."""
    chats = _chats_on()
    _conv_or_404(conversation_id, tenant)
    try:
        b = chats.edit(conversation_id, body.event_id, body.text)
    except chats.ChatError as e:
        raise HTTPException(e.status, str(e))
    from . import convs
    convs.mark(tenant, conversation_id, "message")
    ev = bus.publish(conversation_id, "message", {"role": "user", "text": body.text.strip(), "source": "user",
                                                  "edited": True, "branch": b["group"]})
    chats.started(conversation_id, b["group"], ev["id"])
    background.add_task(_edited_turn, conversation_id, body.text.strip(), tenant, b.get("parent"))
    return {"accepted": True, **b, "event_id": ev["id"]}


class ChatBranchIn(BaseModel):
    group: int
    index: int


class TakebackIn(BaseModel):
    client_id: str = Field(min_length=8, max_length=64)


@app.post("/api/conversations/{conversation_id}/takeback", dependencies=[Depends(require_key)])
def chat_takeback(conversation_id: str, body: TakebackIn, tenant: str = Depends(current_tenant)):
    """v0.173 she takes back a message that is still only queued (Hoola busy with the previous kaam): it never
    reaches the model and its bubble leaves the chat. The turn already running with it cannot be taken back
    (Rokiye is for that)."""
    _conv_or_404(conversation_id, tenant)
    from .agent import santosh
    if santosh.message_running(conversation_id, body.client_id):
        raise HTTPException(409, "This message is already running. Tap 'Stop' to stop it.")
    from .db import Event
    with session() as s:
        rows = s.scalars(select(Event).where(Event.conversation_id == conversation_id, Event.kind == "message")
                         .order_by(Event.id.desc()).limit(80)).all()
        hit = next((e for e in rows if isinstance(e.payload, dict) and e.payload.get("client_id") == body.client_id
                    and e.payload.get("role") == "user" and not e.payload.get("taken_back")), None)
        if hit is None:
            raise HTTPException(404, "That message was not found (maybe it was already taken back).")
        hit.payload = {**hit.payload, "taken_back": True}
        eid = hit.id
    santosh.hold_message(conversation_id, body.client_id)
    return {"taken": True, "event_id": eid}


@app.post("/api/conversations/{conversation_id}/branch", dependencies=[Depends(require_key)])
def chat_branch(conversation_id: str, body: ChatBranchIn, tenant: str = Depends(current_tenant)):
    """v0.162 ‹ / ›: show another version of an edited message or a re-asked reply (nothing is lost)."""
    chats = _chats_on()
    _conv_or_404(conversation_id, tenant)
    try:
        return chats.switch(conversation_id, body.group, body.index)
    except chats.ChatError as e:
        raise HTTPException(e.status, str(e))


@app.post("/api/conversations/{conversation_id}/open", dependencies=[Depends(require_key)])
def chat_open(conversation_id: str, tenant: str = Depends(current_tenant)):
    _conv_or_404(conversation_id, tenant)
    from . import convs
    convs.mark(tenant, conversation_id, "open")
    return {"ok": True}


class ChatHealIn(BaseModel):
    kind: str = Field(default="resync", max_length=16)
    reason: str = Field(default="", max_length=300)
    data: dict = Field(default_factory=dict)


@app.post("/api/chat/heal", dependencies=[Depends(require_key)])
def chat_heal(body: ChatHealIn, tenant: str = Depends(current_tenant)):
    """The app found its chat different from the server's and reloaded it: kept for Hoola Jaanch."""
    from . import convs
    data = {k: v for k, v in (body.data or {}).items() if isinstance(v, (int, float, str, bool))}
    return convs.heal_report(tenant, "resync", body.reason, data)


@app.get("/api/chat/health", dependencies=[Depends(require_key)])
def chat_health(tenant: str = Depends(current_tenant)):
    from . import convs
    return convs.health(tenant)


@app.get("/api/chat/waiting", dependencies=[Depends(require_key)])
def chat_waiting(tenant: str = Depends(current_tenant)):
    """Cards in any of her chats that wait for her now."""
    from .events import waiting_cards
    return {"waiting": waiting_cards(tenant, 40)}


class CallCardsIn(BaseModel):
    conversation_id: str = Field(default="", max_length=40)
    cards: list[dict] = Field(default_factory=list, max_length=30)


@app.get("/api/voice/card_rules", dependencies=[Depends(require_key)])
def voice_card_rules(tenant: str = Depends(current_tenant)):
    """v0.158 card kinds that stay out of her calls (learned from what she closed unused before)."""
    from . import convs
    return convs.call_rules(tenant)


@app.post("/api/voice/calls/{call_id}/cards", dependencies=[Depends(require_key)])
async def voice_call_cards(call_id: str, body: CallCardsIn, tenant: str = Depends(current_tenant)):
    """The app reports which cards a call showed and what she did with them; Hoola learns what to keep out."""
    from . import convs
    conv = body.conversation_id if body.conversation_id and convs.tenant_of(body.conversation_id) == tenant else ""
    return await asyncio.to_thread(convs.call_report, tenant, call_id[:40], body.cards, conv)


# ---------------- leads ----------------
@app.post("/api/leads/upload", dependencies=[Depends(require_key)])
async def upload_leads(file: UploadFile = File(...), conversation_id: str | None = Form(None), tenant: str = Depends(current_tenant)):
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File is larger than 10 MB")
    try:
        res = import_leads(file.filename or "leads.csv", data, tenant)
    except ValueError as e:
        raise HTTPException(400, str(e))
    out = res.as_dict()
    if conversation_id:
        _conv_or_404(conversation_id, tenant)
        bus.publish(conversation_id, "upload", {"filename": file.filename, **out})
    return out


# ---------------- campaigns ----------------
@app.get("/api/campaigns/{campaign_id}", dependencies=[Depends(require_key)])
def get_campaign(campaign_id: str):
    try:
        return camp.campaign_view(campaign_id)
    except camp.CampaignError as e:
        raise HTTPException(404, str(e))


class CampaignAction(BaseModel):
    action: str = Field(pattern="^(pause|resume|cancel|send)$")


@app.post("/api/campaigns/{campaign_id}/action", dependencies=[Depends(require_key)])
def campaign_action(campaign_id: str, body: CampaignAction):
    try:
        v = camp.campaign_view(campaign_id)
        if body.action == "send":
            return camp.confirm_send(campaign_id)
        if body.action == "pause":
            return camp.set_campaign_status(campaign_id, "paused", "Paused from the app")
        if body.action == "resume" and v["status"] == "paused":
            return camp.set_campaign_status(campaign_id, "sending" if v["template"]["status"] == "APPROVED" else "awaiting_approval")
        if body.action == "cancel":
            return camp.set_campaign_status(campaign_id, "cancelled", "Cancelled from the app")
        return v
    except camp.CampaignError as e:
        raise HTTPException(404, str(e))


# ---------------- Meta webhook ----------------
@app.get("/webhooks/whatsapp")
def verify_webhook(request: Request):
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and hmac.compare_digest(p.get("hub.verify_token", ""), get_settings().wa_verify_token):
        return PlainTextResponse(p.get("hub.challenge", ""))
    raise HTTPException(403, "Verify token does not match")


def _signature_ok(secret: str, raw: bytes, header: str | None) -> bool:
    if not secret:
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@app.post("/webhooks/whatsapp")
async def receive_webhook(request: Request):
    raw = await request.body()
    if not _signature_ok(get_settings().wa_app_secret, raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(401, "Bad signature")
    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "Body is not JSON")
    updates: list[dict] = []
    for entry in payload.get("entry", []):
        for ch in entry.get("changes", []):
            field, value = ch.get("field"), ch.get("value") or {}
            if field == "messages":
                from .employee import inbox as biz_inbox
                try:   # v0.616 BAHAR SE BAAT: HER own messages to her business number go to Hoola, not the customer inbox
                    from . import bahar
                    for lid, wa, txt, mid in bahar.whatsapp_take(value):
                        bahar.spawn(bahar.incoming(lid, wa, txt, mid))
                except Exception:
                    logging.getLogger("santosh.webhook").exception("bahar whatsapp")
                try:   # Hoola Employee: customers writing to a business number (never breaks campaign tracking)
                    biz_inbox.receive(value)
                    biz_inbox.statuses(value.get("statuses") or [])
                except Exception:
                    logging.getLogger("santosh.webhook").exception("employee inbox webhook")
                updates.extend(value.get("statuses") or [])
                for m in value.get("messages") or []:
                    updates.append({"reply_from": m.get("from"), "text": (m.get("text") or {}).get("body")})
            elif field == "message_template_status_update":
                camp.apply_template_status(str(value.get("message_template_id")), value.get("event", ""), value.get("reason"))
    if updates:
        for cid in camp.apply_message_status(updates):
            camp.publish_campaign(cid)
    return {"ok": True}


# ---------------- v0.616 BAHAR SE BAAT: her own Hoola from WhatsApp / Telegram / Slack / Teams ----------------
class BaharIn(BaseModel):
    token: str = ""            # Telegram bot token
    bot_token: str = ""        # Slack xoxb-
    signing_secret: str = ""   # Slack
    app_id: str = ""           # Azure Bot (Teams)
    app_password: str = ""
    app_tenant: str = ""


def _bahar_base(request: Request) -> str:
    return (get_settings().public_base_url or str(request.base_url)).rstrip("/")


@app.get("/api/bahar", dependencies=[Depends(require_key)])
def bahar_list(request: Request, tenant: str = Depends(current_tenant)):
    from . import bahar
    return {"channels": bahar.links(tenant, _bahar_base(request))}


@app.post("/api/bahar/{channel}", dependencies=[Depends(require_key)])
async def bahar_setup(channel: str, body: BaharIn, request: Request, tenant: str = Depends(current_tenant)):
    from . import bahar
    try:
        return await bahar.setup(tenant, channel, body.model_dump(), _bahar_base(request))
    except bahar.BaharError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/bahar/{channel}", dependencies=[Depends(require_key)])
def bahar_remove(channel: str, tenant: str = Depends(current_tenant)):
    from . import bahar
    if not bahar.remove(tenant, channel):
        raise HTTPException(404, "This channel is not connected.")
    return {"ok": True}


@app.post("/webhooks/bahar/telegram/{hook}")
async def bahar_telegram(hook: str, request: Request):
    from . import bahar
    link = bahar._link_by_hook("telegram", hook)
    want = bahar._open(link.secret).get("header", "") if link else ""
    if not want or not hmac.compare_digest(want, request.headers.get("x-telegram-bot-api-secret-token", "")):
        raise HTTPException(403, "Not this bot")
    try:
        got = bahar.telegram_read(json.loads(await request.body() or b"{}"))
    except ValueError:
        raise HTTPException(400, "Body is not JSON")
    if got:
        bahar.spawn(bahar.incoming(link.id, got[0], got[1], got[2], got[3]))
    return {"ok": True}


@app.post("/webhooks/bahar/slack/{hook}")
async def bahar_slack(hook: str, request: Request):
    from . import bahar
    link = bahar._link_by_hook("slack", hook)
    raw = await request.body()
    sec = bahar._open(link.secret) if link else {}
    if not sec.get("signing_secret") or not bahar.slack_sig_ok(
            sec["signing_secret"], request.headers.get("x-slack-request-timestamp", ""), raw,
            request.headers.get("x-slack-signature", "")):
        raise HTTPException(401, "Bad signature")
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "Body is not JSON")
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge", "")}
    got = bahar.slack_read(body, (link.meta or {}).get("bot_user", ""))
    if got:
        bahar.spawn(bahar.incoming(link.id, got[0], got[1], got[2], got[3]))
    return {"ok": True}


@app.post("/webhooks/bahar/teams/{hook}")
async def bahar_teams(hook: str, request: Request):
    from . import bahar
    link = bahar._link_by_hook("teams", hook)
    if link is None:
        raise HTTPException(404, "Not found")
    try:
        act = json.loads(await request.body() or b"{}")
    except ValueError:
        raise HTTPException(400, "Body is not JSON")
    sec = bahar._open(link.secret)
    if not bahar.teams_verify(request.headers.get("authorization", ""), sec.get("app_id", ""), act.get("serviceUrl", "")):
        raise HTTPException(401, "Bad token")
    got = bahar.teams_read(act)
    if got:
        bahar.spawn(bahar.incoming(link.id, got[0], got[1], got[2], got[3]))
    return {}


# ---------------- daily life (used by the Santosh phone app) ----------------
from . import life  # noqa: E402
from .db import DeviceAction, ListItem, MemoryFact, Profile, Reminder, as_utc, now  # noqa: E402


@app.get("/api/reminders", dependencies=[Depends(require_key)])
def get_reminders(include_done: bool = False, tenant: str = Depends(current_tenant)):
    return {"reminders": life.upcoming_reminders(tenant, include_done=include_done)}


@app.post("/api/reminders/{reminder_id}/cancel", dependencies=[Depends(require_key)])
def cancel_reminder_api(reminder_id: str, tenant: str = Depends(current_tenant)):
    with session() as s:
        r = s.get(Reminder, reminder_id)
        if not r or r.tenant_id != tenant:
            raise HTTPException(404, "Reminder not found")
        r.status = "cancelled"
        conv = r.conversation_id
    reminders = life.upcoming_reminders(tenant)
    bus.publish(conv, "reminders", {"reminders": reminders})
    return {"reminders": reminders}


# ---------------- accounts (product: Sign in with Google) ----------------
@app.get("/auth/google/start")
def google_start(app_session: bool = True, web: bool = False, apps: bool = False):
    """The app opens this; we redirect to Google's consent screen. web=1 = the Hoola Console (v0.142): sign-in with
    name + email only; web=1&apps=1 = the console's "Google apps jodiye" (Gmail, Drive, Calendar, Docs, Sheets)."""
    from . import accounts
    try:
        return RedirectResponse(accounts.start_google(web=web, apps=apps))
    except accounts.AuthError as e:
        raise HTTPException(503, str(e))


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    """Google returns here. We store tokens and hand the app a session token via a deep link."""
    from . import accounts
    from .mailbox.accounts import is_link_state
    if is_link_state(request.query_params.get("state", "")):   # "connect my Gmail" from the app, not a sign-in
        return await _finish_mail_link(request)
    from .cal.accounts import is_link_state as is_cal_state
    if is_cal_state(request.query_params.get("state", "")):    # "connect my Google Calendar"
        return await _finish_cal_link(request)
    from .sheets.accounts import is_link_state as is_sheets_state
    if is_sheets_state(request.query_params.get("state", "")):  # "connect my Google Sheets"
        return await _finish_sheets_link(request)
    from .seo.service import is_link_state as is_seo_state
    if is_seo_state(request.query_params.get("state", "")):     # "connect my Search Console" (read-only)
        return await _finish_seo_link(request)
    from .youtube.accounts import is_link_state as is_youtube_state
    if is_youtube_state(request.query_params.get("state", "")):  # "connect my YouTube channel"
        return await _finish_youtube_link(request)
    from .ads.gads import is_link_state as is_gads_state
    if is_gads_state(request.query_params.get("state", "")):     # v0.401 "connect my Google Ads" (YouTube ads)
        from .ads import gads
        q = request.query_params
        if q.get("error"):
            return _linked_page("Google Ads", "social", None, q.get("error") or "")
        try:
            v = await asyncio.to_thread(gads.finish_link, q.get("code", ""), q.get("state", ""))
        except gads.GAdsError as e:
            return _linked_page("Google Ads", "social", None, str(e))
        return _linked_page("Google Ads", "social", v["email"] + (" - " + ", ".join(v["accounts"][:3]) if v["accounts"] else ""))
    from .slides.accounts import is_link_state as is_slides_state
    if is_slides_state(request.query_params.get("state", "")):  # "connect my Google Slides"
        return await _finish_slides_link(request)
    from .photos.accounts import is_link_state as is_photos_state
    if is_photos_state(request.query_params.get("state", "")):  # "connect my Google Photos"
        from .photos.api import finish_page as photos_finish
        return await photos_finish(request)
    from .drive.accounts import is_link_state as is_drive_state
    if is_drive_state(request.query_params.get("state", "")):   # "connect my Google Drive"
        from .drive.api import finish_page as drive_finish
        return await drive_finish(request)
    from .feedback.gbp import is_link_state as is_fb_state
    if is_fb_state(request.query_params.get("state", "")):      # v0.133 "connect my Business Profile reviews" (Feedback Sahayak)
        from .feedback.api import finish_page as fb_finish
        return await fb_finish(request)
    from .itadmin.connectors import is_link_state as is_ita_state
    if is_ita_state(request.query_params.get("state", "")):     # v0.137 "connect my Google Workspace admin" (IT Admin Sahayak)
        from .itadmin.api import finish_page as ita_finish
        return await ita_finish(request)
    from .forms.accounts import is_link_state as is_form_state
    if is_form_state(request.query_params.get("state", "")):    # "connect my Google Forms"
        from .forms.api import finish_page as forms_finish
        return await forms_finish(request)
    code = request.query_params.get("code")
    state = request.query_params.get("state", "")
    err = request.query_params.get("error")
    from .console import service as console
    web = console.is_web_state(state)
    if err:
        if web:   # she pressed Cancel on Google's screen: back to the console, not a bare error page
            msg = "Google sign-in band kiya gaya." if err == "access_denied" else f"Google sign-in nahi hua ({err[:40]})."
            return RedirectResponse("/console/?error=" + quote(msg), headers=_CONSOLE_NOREF)
        return HTMLResponse(f"<h3>Sign-in cancelled</h3><p>{err}</p>", status_code=400)
    if not code:
        raise HTTPException(400, "Missing code")
    try:
        res = await accounts.finish_google(code, state)
    except accounts.AuthError as e:
        if web:
            return RedirectResponse("/console/?error=" + quote(str(e)[:160]), headers=_CONSOLE_NOREF)
        return HTMLResponse(f"<h3>Sign-in nahi hua</h3><p>{e}</p>", status_code=400)
    if web:   # v0.142 Hoola Console: a one-time code, never the session token, goes into the URL
        apps = "&google=apps" if state.startswith(console.WEB_STATE + "g.") else ""
        return RedirectResponse("/console/?code=" + console.issue_code(res["session_token"]) + apps, headers=_CONSOLE_NOREF)
    scheme = get_settings().app_redirect_scheme
    deep = f"{scheme}://auth?session={res['session_token']}"
    # the app registers this scheme; the page also shows the token in case the link doesn't auto-open
    html = f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">
<h2>Santosh se juda! ✅</h2><p>{res['email']}</p>
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>location.href={deep!r};</script></body>"""
    return HTMLResponse(html)


class LocationIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(None, ge=0)


@app.put("/api/location", dependencies=[Depends(require_key)])
def put_location(body: LocationIn, tenant: str = Depends(current_tenant)):
    """The phone's position, so 'near me', directions and cab pickup use where the user actually is."""
    from . import maps
    maps.save_location(tenant, body.lat, body.lng, body.accuracy_m)
    return {"ok": True}


@app.get("/api/me", dependencies=[Depends(require_key)])
def api_me(request: Request):
    from . import accounts
    tok = _bearer(request)
    uid = accounts.tenant_for_session(tok) if tok else None
    if not uid:
        return {"signed_in": False, "tenant": current_tenant(request)}
    info = accounts.user_info(uid)
    return {"signed_in": True, **(info or {})}


@app.post("/api/logout", dependencies=[Depends(require_key)])
def api_logout(request: Request):
    from . import accounts
    accounts.logout(_bearer(request))
    return {"ok": True}


@app.delete("/api/connections/{provider}", dependencies=[Depends(require_key)])
def api_disconnect(provider: str, request: Request):
    from . import accounts
    uid = accounts.tenant_for_session(_bearer(request))
    if not uid:
        raise HTTPException(401, "Sign in first")
    return {"disconnected": accounts.disconnect(uid, provider)}


# ---------------------------------------------------------------- v0.142 Hoola Console (web app at /console)
_CONSOLE_NOREF = {"Referrer-Policy": "no-referrer", "Cache-Control": "no-store"}
_CONSOLE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https://tiles.openfreemap.org https://i.ytimg.com; media-src 'self' blob:; "
                "connect-src 'self' https://tiles.openfreemap.org; "   # v0.412 the riders map's open map tiles (OpenFreeMap)
                # v0.745 the Video Learner: a YouTube thumbnail per learned task + the privacy-enhanced player
                "worker-src 'self' blob:; frame-src 'self' blob: https://www.youtube-nocookie.com; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


@app.get("/console")
@app.get("/console/")
@app.get("/console/c/{conversation_id}")
def console_page(conversation_id: str = "", legacy: bool = False):
    """The Hoola Console: chat-first web app on the same APIs as the phone (login: Google or Hoola ID + password).
    v0.162 /console/c/<id> = a link to one chat (same page; the page opens that chat).
    v0.170 Console v2 (CONSOLE_V2, default on): the Night-Glass v2 shell serves the same address and the same APIs;
    ?legacy=1 (or CONSOLE_V2=false) serves the previous console page unchanged."""
    st = get_settings()
    page = "index.html" if (legacy or not st.console_v2) else "v2.html"
    return FileResponse(STATIC / "console" / page, headers={
        **_CONSOLE_NOREF, "Content-Security-Policy": _CONSOLE_CSP, "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff", "Permissions-Policy": "microphone=(self), camera=(), geolocation=()"})


@app.get("/console/web")
@app.get("/console/web/")
def web_studio_page():
    """v0.649 HOOLA WEB STUDIO: the website builder as its own full-screen app (own sidebar, chat + live preview, the
    three full looks). Same sign-in as the console (its token in this browser), same APIs, same strict CSP."""
    return FileResponse(STATIC / "console" / "webstudio.html", headers={
        **_CONSOLE_NOREF, "Content-Security-Policy": _CONSOLE_CSP, "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff", "Permissions-Policy": "microphone=(), camera=(), geolocation=()"})


@app.get("/console/apps")
@app.get("/console/apps/")
def app_studio_page():
    """v0.693 HOOLA APP STUDIO: the native-app builder as its own full-screen app (the Web Studio's twin: own sidebar,
    a Hoola thread per app, Plan / Looks / Screens / Prototype / Android / iPhone / Store / Data / Business / Health /
    Settings). Same sign-in as the console (its token in this browser), same APIs, same strict CSP."""
    return FileResponse(STATIC / "console" / "appstudio.html", headers={
        **_CONSOLE_NOREF, "Content-Security-Policy": _CONSOLE_CSP, "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff", "Permissions-Policy": "microphone=(), camera=(), geolocation=()"})


@app.get("/api/console/config")
def console_config():
    from . import accounts
    st = get_settings()
    return {"app": "Hoola", "version": app.version, "google": accounts.oauth_configured(), "password": True,
            "v2": bool(st.console_v2),
            "stream": bool(st.console_v2 or st.console_stream), "sessions": bool(st.console_v2 or st.chat_sessions),
            "panel": bool(st.console_v2 or st.side_panel), "projects": bool(st.console_v2 or st.chat_projects),
            "human": bool(getattr(st, "console_human", False))}


@app.get("/api/console/stream", dependencies=[Depends(require_key)])
async def console_stream(request: Request, after: int = 0, tenant: str = Depends(current_tenant)):
    """v0.162 ONE stream for all her chats (CHAT_SESSIONS): every event of every chat, tagged `conv`, including the
    reply being written (live-only, no SSE id). The console switches chats without reconnecting, so work in one chat
    never stops when she opens another, and every chat that works gets a busy badge."""
    _chats_on()
    last = int(request.headers.get("last-event-id") or after or 0)
    q = bus.subscribe_account(tenant)

    async def gen():
        try:
            sent = last
            if last > 0:
                total = 0
                while True:
                    page = await asyncio.to_thread(bus.backlog_account, tenant, sent, 500)
                    for ev in page:
                        sent = ev["id"]
                        yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    total += len(page)
                    if len(page) < 500:
                        break
                    if total >= REPLAY_MAX:
                        sent = await asyncio.to_thread(bus.last_account_id, tenant)
                        yield f"data: {json.dumps({'id': 0, 'kind': 'resync', 'payload': {'why': 'gap'}})}\n\n"
                        break
            else:
                sent = await asyncio.to_thread(bus.last_account_id, tenant)
            yield f"data: {json.dumps({'id': 0, 'kind': 'replay_end', 'payload': {'last': sent}})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    from . import offline
                    offline.touch(tenant)
                    yield ": ping\n\n"
                    continue
                if ev.get("live"):
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    continue
                if ev["id"] <= sent:
                    continue
                sent = ev["id"]
                yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            bus.unsubscribe_account(tenant, q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class ConsoleLoginIn(BaseModel):
    handle: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


def _client_ip(request: Request) -> str:
    """nginx's X-Real-IP ($remote_addr) only; a client-sent X-Forwarded-For is not trusted."""
    return (request.headers.get("x-real-ip", "").strip() or (request.client.host if request.client else "") or "?")[:64]


@app.post("/api/console/login")
def console_login(body: ConsoleLoginIn, request: Request):
    from .console import service as console
    try:
        return console.login(body.handle, body.password, _client_ip(request))
    except console.ConsoleError as e:
        raise HTTPException(e.status, str(e))


class ConsoleCodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)


@app.post("/api/console/exchange")
def console_exchange(body: ConsoleCodeIn):
    from .console import service as console
    try:
        return {"session_token": console.exchange(body.code)}
    except console.ConsoleError as e:
        raise HTTPException(e.status, str(e))


class ConsolePasswordIn(BaseModel):
    password: str = Field(default="", max_length=200)
    current: str = Field(default="", max_length=200)
    remove: bool = False


@app.put("/api/console/password", dependencies=[Depends(require_key)])
def console_password(body: ConsolePasswordIn, tenant: str = Depends(current_tenant)):
    from .console import service as console
    try:
        if body.remove:
            return {"removed": console.remove_password(tenant, body.current)}
        return console.set_password(tenant, body.password, body.current)
    except console.ConsoleError as e:
        raise HTTPException(e.status, str(e))


@app.get("/api/console/me", dependencies=[Depends(require_key)])
def console_me(tenant: str = Depends(current_tenant)):
    from .console import service as console
    from .employee import hire
    return {**console.me(tenant), "arena": tenant == get_settings().tenant_id,   # v0.312 the owner's Arena screen
            "employees": hire.hired_keys(tenant)}                               # v0.317 desks appear only for hired employees


@app.get("/api/console/conversations", dependencies=[Depends(require_key)])
def console_conversations(limit: int = 40, archived: bool = False, project: str = "", tenant: str = Depends(current_tenant)):
    from . import chats
    if chats.enabled():   # v0.162 one query instead of 2 per chat; pinned first, titles, busy (v0.164 + project filter)
        return {"conversations": chats.chat_list(tenant, archived, max(limit, 200), project[:40], hide_empty=True)}
    from .console import service as console
    return {"conversations": console.conversations(tenant, limit)}


@app.get("/api/console/pending", dependencies=[Depends(require_key)])
def console_pending(tenant: str = Depends(current_tenant)):
    from .console import service as console
    return {"pending": console.pending(tenant)}


_CARD_SKIP = {"message", "typing", "step", "work"}


@app.get("/api/console/conversations/{conversation_id}/recent", dependencies=[Depends(require_key)])
def console_recent(conversation_id: str, n: int = 60, tenant: str = Depends(current_tenant)):
    """Opening an old chat: the cursor to stream from, and the latest state of its last cards (newest per card id)."""
    _conv_or_404(conversation_id, tenant)
    from .db import Event
    with session() as s:
        last = s.scalar(select(func.max(Event.id)).where(Event.conversation_id == conversation_id)) or 0
        rows = s.scalars(select(Event).where(Event.conversation_id == conversation_id, Event.kind.not_in(_CARD_SKIP))
                         .order_by(Event.id.desc()).limit(max(1, min(n, 200)) * 3)).all()
        seen, cards = set(), []
        for e in rows:
            p = e.payload if isinstance(e.payload, dict) else {}
            key = (e.kind, str(p.get("id") or p.get("task_id") or e.id))
            if key in seen:
                continue
            seen.add(key)
            cards.append({"id": e.id, "kind": e.kind, "payload": p, "at": e.created_at.isoformat()})
            if len(cards) >= n:
                break
    return {"last_event_id": last, "cards": list(reversed(cards))}


@app.get("/api/console/today", dependencies=[Depends(require_key)])
def console_today(tenant: str = Depends(current_tenant)):
    from .console import service as console
    return console.today(tenant)


# ---------------------------------------------------------------- PC bridge (Santosh Desktop)
class PairIn(BaseModel):
    code: str
    name: str = "PC"
    os: str = ""


class PcSearchIn(BaseModel):
    query: str
    kind: str = "any"


class PcPullIn(BaseModel):
    path: str


def _pc_device(request: Request):
    from .pc import service as pcs
    tok = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    dev = pcs.device_for_token(tok)
    if dev is None:
        raise HTTPException(401, "This PC is not paired (or was removed). Pair it again from the Santosh app.")
    return dev


def _pc_err(e: Exception):
    from .pc.hub import PcOffline
    if isinstance(e, PcOffline):
        raise HTTPException(409, "PC offline hai. PC on karke Santosh Desktop kholiye.")
    raise HTTPException(400, str(e))


@app.post("/api/pc/pair/start", dependencies=[Depends(require_key)])
def pc_pair_start(tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    return pcs.pair_start(tenant)


@app.post("/api/pc/pair")
def pc_pair(body: PairIn, request: Request):
    from .pc import service as pcs
    try:
        return pcs.pair_finish(body.code, body.name, body.os, request.client.host if request.client else "")
    except pcs.PairError as e:
        raise HTTPException(400, str(e))


@app.websocket("/api/pc/ws")
async def pc_ws(ws: WebSocket):
    from fastapi import WebSocketDisconnect
    from .pc import service as pcs
    from .pc.hub import hub
    tok = ws.headers.get("authorization", "").removeprefix("Bearer ").strip() or ws.query_params.get("token", "")
    dev = pcs.device_for_token(tok)
    await ws.accept()
    if dev is None:
        await ws.close(code=4401)
        return
    try:
        await hub.serve(ws, dev.id, dev.tenant_id)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("pc socket failed")


@app.post("/api/pc/files")
async def pc_upload(request: Request, file: UploadFile = File(...), path: str = Form(""),
                    direction: str = Form("to_phone")):
    """The PC uploads a file the phone asked for. v0.202 PC-to-PC bridge: the Hoola PC uploads with
    direction "to_pc" so the USER'S personal PC can fetch it into her Santosh Inbox; every old desktop
    sends no direction and keeps "to_phone" (a phone download card) exactly as before."""
    from .pc import service as pcs
    dev = _pc_device(request)
    if direction not in ("to_phone", "to_pc"):   # unknown value = the safe old behaviour
        direction = "to_phone"
    try:
        row = await pcs.store_upload(file, dev.tenant_id, dev.id, direction, path)
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    return {"file_id": row.id, "name": row.name, "size": row.size}


@app.get("/api/pc/files/{file_id}")
def pc_download(file_id: str, exp: int = 0, sig: str = ""):
    """Signed, expiring link the phone opens to download a PC file."""
    from .pc import service as pcs
    if not pcs.check_sig(file_id, exp, sig):
        raise HTTPException(403, "This link expired. Ask Santosh to send the file again.")
    f = pcs.get_file(file_id)
    if f is None or f.direction != "to_phone" or not Path(f.stored_path).exists():
        raise HTTPException(404, "File no longer available")
    return FileResponse(f.stored_path, filename=f.name)


@app.get("/api/pc/fetch/{file_id}")
def pc_fetch(file_id: str, request: Request):
    """The PC downloads a file the phone sent to it."""
    from .pc import service as pcs
    dev = _pc_device(request)
    f = pcs.get_file(file_id)
    if f is None or f.direction != "to_pc" or f.tenant_id != dev.tenant_id or not Path(f.stored_path).exists():
        raise HTTPException(404, "File not found")
    return FileResponse(f.stored_path, filename=f.name)


@app.get("/api/pc/devices", dependencies=[Depends(require_key)])
def pc_devices(tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    return {"devices": pcs.devices(tenant)}


@app.delete("/api/pc/devices/{device_id}", dependencies=[Depends(require_key)])
async def pc_remove(device_id: str, tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    from .pc.hub import hub
    ok = pcs.revoke(tenant, device_id)
    if ok:
        await hub.kick(tenant, device_id)
    return {"removed": ok}


@app.get("/api/pc/jobs", dependencies=[Depends(require_key)])
def pc_jobs(limit: int = 50, tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    return {"jobs": pcs.jobs(tenant, limit)}


@app.get("/api/pc/hoola", dependencies=[Depends(require_key)])
def pc_hoola_devices(tenant: str = Depends(current_tenant)):
    """v0.205 HOOLA PC AND MERA PC ARE DIFFERENT SECTIONS: the phone's own "Hoola ka PC" section
    feeds from here — ONLY the Hoola PC (Hoola's own cloud container), never the user's personal
    PCs; /api/pc/devices stays personal-only (the v0.201 rule untouched), this is its mirror."""
    from .pc import service as pcs
    return {"devices": pcs.hoola_devices(tenant)}


@app.get("/api/pc/hoola/jobs", dependencies=[Depends(require_key)])
def pc_hoola_jobs(limit: int = 50, tenant: str = Depends(current_tenant)):
    from .pc import service as pcs
    return {"jobs": pcs.hoola_jobs(tenant, limit)}


@app.post("/api/pc/search", dependencies=[Depends(require_key)])
async def pc_search(body: PcSearchIn, tenant: str = Depends(current_tenant)):
    from .pc.hub import hub
    try:   # v0.200 Mera PC = user personal PC: search is HER PC's job, never the Hoola PC's
        return await hub.call_personal(tenant, "search", {"query": body.query, "kind": body.kind, "limit": 30})
    except Exception as e:
        _pc_err(e)


@app.post("/api/pc/pull", dependencies=[Depends(require_key)])
async def pc_pull(body: PcPullIn, tenant: str = Depends(current_tenant)):
    """Phone asks for one PC file; returns a download link."""
    from .pc import service as pcs
    from .pc.hub import hub
    try:   # v0.200 Mera PC = user personal PC: pull is HER PC's job, never the Hoola PC's
        out = await hub.call_personal(tenant, "send_file", {"path": body.path})
    except Exception as e:
        _pc_err(e)
    f = pcs.get_file(out.get("file_id", ""))
    if f is None or f.tenant_id != tenant:
        raise HTTPException(502, "The file did not arrive from the PC")
    return pcs.public_file(f)


@app.post("/api/pc/send", dependencies=[Depends(require_key)])
async def pc_send(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """Phone sends a file to the PC's Santosh Inbox folder."""
    from .pc import service as pcs
    from .pc.hub import hub
    if not hub.has_personal(tenant):   # v0.200 Mera PC = user personal PC: send targets HER PC only
        raise HTTPException(409, "PC offline hai. PC on karke Santosh Desktop kholiye.")
    try:
        row = await pcs.store_upload(file, tenant, "", "to_pc")
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    try:
        return await hub.call_personal(tenant, "save_file", {"file_id": row.id, "name": row.name, "url": f"/api/pc/fetch/{row.id}"})
    except Exception as e:
        _pc_err(e)


# v0.487 W3 - the PC -> Hoola TEXT LANE (the quick-ask lane): a PAIRED device (the desktop, the
# browser extension paired through the same /api/pc/pair flow) sends a typed ask / a page into her
# conversation and reads the answer back. NEW surface beside the PC block - no existing PC endpoint,
# setting or behaviour is touched (the Mera PC freeze stands; the owner's W3 ask named this lane).
from .quicklane import router as quicklane_router               # noqa: E402
app.include_router(quicklane_router)                            # POST /api/pc/quickask (+ /messages)
# v0.663.0 KAAN W5 - the HTTP + MCP doors beside the agent tool: the SAME KS functions, the SAME
# gates (audio ingest rides kaan_audio; reads gate-free by the W1 law), tenant-scoped by the SAME
# auth (API key, product session, or a paired device token - the extension pairs through
# /api/pc/pair like any PC). The MCP door lives in kaan/mcp_server.py (stdio, run on demand).
from .kaan.api import _kaan_router as _kaan_api_router          # noqa: E402
app.include_router(_kaan_api_router(require_key, current_tenant))   # /api/kaan/* (W5)


@app.get("/api/voice/check", dependencies=[Depends(require_key)])
async def voice_check(tenant: str = Depends(current_tenant)):
    """v0.150 Connect to Gemini Live the way her calls do and say which part it refuses (and heal it)."""
    from . import voicecheck
    return await voicecheck.run(tenant)


@app.get("/api/voice/stats", dependencies=[Depends(require_key)])
def voice_stats(tenant: str = Depends(current_tenant)):
    """How human the calls sound, in numbers: how fast he starts answering, reply length, questions, interruptions,
    silent tool runs. Recent calls since the server started."""
    from . import callrating
    from . import voice as v
    from . import callquality
    q = callquality.quality(tenant, 30, list(v.STATS))   # v0.231 saved calls (survive restarts) + grades
    return {**v.stats_summary(tenant), "ratings": callrating.summary(tenant),   # v0.98 her own 👍 / 👎 too
            "quality": {k: q[k] for k in ("overall", "say", "targets", "alert")},
            "ack_tts_fallbacks": v.TTS_FALLBACKS["count"],
            "clips_rejected": v.CLIP_REJECTED["count"]}   # v0.250 clips that read their English ask aloud   # v0.234 clips the call's own TTS could not render


class VoiceEngineBody(BaseModel):
    engine: str


@app.get("/api/maps/usage", dependencies=[Depends(require_key)])
def maps_usage(tenant: str = Depends(current_tenant)):
    """v0.449 PAISA PEHLE: today's Google Maps spend, the free allowance left this month, the daily cap and
    how many calls it has refused. `assumed_tier` and `unsourced_skus` say where our price table is a guess
    rather than a sourced rate, so a wrong estimate is visible instead of silent."""
    from . import mapsbill
    return mapsbill.usage(tenant)


@app.get("/api/voice/engine", dependencies=[Depends(require_key)])
def voice_engine(tenant: str = Depends(current_tenant)):
    """v0.264 which engine her next call uses (gemini default / openai real voice), why, and the month's spend."""
    from . import voiceengine
    return voiceengine.view(tenant)


@app.put("/api/voice/engine", dependencies=[Depends(require_key)])
def voice_engine_set(body: VoiceEngineBody, tenant: str = Depends(current_tenant)):
    from . import voiceengine
    try:
        return voiceengine.choose(tenant, body.engine.strip().lower())
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/voice/quality", dependencies=[Depends(require_key)])
def voice_quality(days: int = 30, tenant: str = Depends(current_tenant)):
    """v0.231 VOICE PHASE 4: call-quality numbers saved per call (survive deploys), a grade per call with the
    problems in plain words, the same roll-up per app version (did this release sound better?), and her ear test."""
    from . import callquality
    from . import voice as v
    return callquality.quality(tenant, max(1, min(days, 180)), list(v.STATS))


@app.get("/api/voice/eartest", dependencies=[Depends(require_key)])
def voice_eartest(tenant: str = Depends(current_tenant)):
    """v0.231 the ear test + real-phone checklist for THIS app version, with her marks."""
    from . import callquality
    return callquality.eartest(tenant)


class EarMark(BaseModel):
    result: str
    note: str = Field("", max_length=300)


@app.post("/api/voice/eartest/{test_id}", dependencies=[Depends(require_key)])
def voice_eartest_mark(test_id: str, body: EarMark, tenant: str = Depends(current_tenant)):
    """v0.231 she marks one scenario pass / fail / skip (clear = undo) for this app version."""
    from . import callquality
    try:
        return callquality.eartest_mark(tenant, test_id, body.result, body.note)
    except KeyError:
        raise HTTPException(404, "No such test")
    except ValueError as e:
        raise HTTPException(400, str(e))


class CallRate(BaseModel):
    good: bool
    reasons: list[str] = Field(default_factory=list)
    seconds: int = 0


@app.post("/api/voice/calls/{call_id}/rating", dependencies=[Depends(require_key)])
def voice_rate(call_id: str, body: CallRate, tenant: str = Depends(current_tenant)):
    """v0.98 her one tap after a call: good / not good + what went wrong."""
    from . import callrating
    return callrating.rate(tenant, call_id, body.good, body.reasons, body.seconds)


# ---- v0.119 "<name> ne kya seekha": how she speaks, words misheard before, her words (numbers and words only) ----
class VoiceLearnBody(BaseModel):
    learn: bool


class VoiceWordBody(BaseModel):
    term: str = Field(min_length=2, max_length=60)


class VoiceFixBody(BaseModel):
    heard: str = Field(min_length=1, max_length=80)
    meant: str = Field(min_length=1, max_length=80)


def _vs_call(fn, *a):
    from . import voicestyle
    try:
        return fn(*a)
    except voicestyle.StyleError as e:
        raise HTTPException(400, str(e))


@app.get("/api/voice/learned", dependencies=[Depends(require_key)])
def voice_learned(tenant: str = Depends(current_tenant)):
    from . import voicestyle
    v = voicestyle.view(tenant)
    v["say"] = voicestyle.say(tenant)
    return v


@app.put("/api/voice/learned", dependencies=[Depends(require_key)])
def voice_learned_set(body: VoiceLearnBody, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return voicestyle.set_learn(tenant, body.learn)


@app.delete("/api/voice/learned", dependencies=[Depends(require_key)])
def voice_learned_forget(part: str = "all", tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return _vs_call(voicestyle.forget, tenant, part)


@app.post("/api/voice/learned/words", dependencies=[Depends(require_key)])
def voice_word_add(body: VoiceWordBody, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return _vs_call(voicestyle.add_word, tenant, body.term, "her")


@app.delete("/api/voice/learned/words/{word_id}", dependencies=[Depends(require_key)])
def voice_word_remove(word_id: int, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    if not voicestyle.remove_word(tenant, word_id):
        raise HTTPException(404, "Word not found")
    return {"ok": True}


@app.post("/api/voice/learned/fixes", dependencies=[Depends(require_key)])
def voice_fix_add(body: VoiceFixBody, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return _vs_call(voicestyle.note_fix, tenant, body.heard, body.meant, True)


@app.post("/api/voice/learned/fixes/{fix_id}/confirm", dependencies=[Depends(require_key)])
def voice_fix_confirm(fix_id: int, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    return _vs_call(voicestyle.confirm_fix, tenant, fix_id)


@app.delete("/api/voice/learned/fixes/{fix_id}", dependencies=[Depends(require_key)])
def voice_fix_remove(fix_id: int, tenant: str = Depends(current_tenant)):
    from . import voicestyle
    if not voicestyle.remove_fix(tenant, fix_id):
        raise HTTPException(404, "Correction not found")
    return {"ok": True}


class UsageLimit(BaseModel):
    month_inr: float | None = Field(default=None, ge=0, le=10_000_000)
    month_usd: float | None = Field(default=None, ge=0, le=100_000)


@app.get("/api/usage", dependencies=[Depends(require_key)])
def usage_get(days: int = 30, tenant: str = Depends(current_tenant)):
    """v0.98 Kharcha: what Hoola's AI cost this owner (per day, per feature, per model), the month vs her limit."""
    from . import usage
    return usage.report(tenant, days)


@app.put("/api/usage/limit", dependencies=[Depends(require_key)])
def usage_limit(body: UsageLimit, tenant: str = Depends(current_tenant)):
    from . import usage
    if body.month_inr is None and body.month_usd is None:
        raise HTTPException(400, "give month_inr or month_usd (0 = no limit)")
    return usage.set_limit(tenant, month_usd=body.month_usd, month_inr=body.month_inr)


@app.get("/api/usage/all", dependencies=[Depends(require_key)])
def usage_all(days: int = 30, tenant: str = Depends(current_tenant)):
    """The server owner's view: spend per owner (counts only). Only for the main account."""
    from . import usage
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "Only for the server owner")
    return {"tenants": usage.all_tenants(days), "usd_inr": usage.usd_inr()}


@app.websocket("/api/voice/ws")
async def voice_ws(ws: WebSocket, conv: str = "", voice: str = "", lang: str = "hi-IN", resume: str = "",
                   split: str = ""):
    """Realtime voice call (Baat tab). See app/voice.py for the protocol. `resume` re-joins a call whose phone
    connection dropped (network change) instead of starting a new one."""
    from . import voice as v
    st = get_settings()
    got = ws.headers.get("authorization", "").removeprefix("Bearer ").strip()   # v0.391 header / subprotocol only, never ?key=
    # v0.142 browsers can't set headers on a WebSocket: the console sends "hoola, hoola-key.<token>" as subprotocols
    protos = [p.strip() for p in ws.headers.get("sec-websocket-protocol", "").split(",") if p.strip()]
    sub = "hoola" if "hoola" in protos else None
    if not got:
        got = next((p[len("hoola-key."):] for p in protos if p.startswith("hoola-key.")), "")
    from . import accounts
    if st.api_key and got and hmac.compare_digest(got, st.api_key):
        tenant = st.tenant_id
    elif got and accounts.tenant_for_session(got):
        tenant = accounts.tenant_of_user(accounts.tenant_for_session(got))
    elif not st.api_key:
        tenant = st.tenant_id
    else:
        await ws.close(code=4401)
        return
    with session() as s:
        c = s.get(Conversation, conv)
        ok = bool(c and c.tenant_id == tenant)
    if not ok:
        await ws.close(code=4404)
        return
    await ws.accept(subprotocol=sub)
    if resume:
        call = v.CALLS.get(resume)
        from . import callconv as _cc   # v0.646 a split call lives on its own record: match the chat behind both
        if call is None or call.tenant != tenant or _cc.chat_of(call.conv) != _cc.chat_of(conv) or call.closed.is_set():
            await ws.send_text(json.dumps({"type": "error", "code": "gone", "message": "Pichli call ab chalu nahi hai."}))
            await ws.close(code=4410)
            return
        reader = await call.attach(ws)
        try:
            await reader   # until this connection drops again or the user hangs up
        except Exception:
            pass
        return
    # v0.646 ALAG CALL: a phone that knows the Calls section (split=1) gets the call on its OWN record; the chat she
    # called from stays the chat (same memory scope). An older APK (no split) keeps the call on the chat, as before.
    if split == "1" and st.call_split:
        from . import callconv as _cc
        try:
            conv = await asyncio.to_thread(_cc.open_for, tenant, conv, "")
        except Exception:
            log.exception("call record could not be made; the call runs on the chat")
    from . import voiceengine   # v0.264 two engines: OpenAI "real voice" only when she picked it and it is allowed
    engine, why = voiceengine.pick(tenant)
    if engine == "openai":
        from .voice_openai import OpenAICall
        await v.serve(OpenAICall(ws, conv, voice, lang, tenant))
        return
    if why:
        log.info("voice call for %s runs on Gemini: %s", tenant, why)
    if not st.gemini_api_key:
        await ws.send_text(json.dumps({"type": "error", "message": "Server par GEMINI_API_KEY set nahi hai."}))
        await ws.close()
        return
    await v.serve(v.Call(ws, conv, voice, lang, tenant))


@app.get("/api/emails/pending", dependencies=[Depends(require_key)])
def pending_emails(tenant: str = Depends(current_tenant)):
    from .db import EmailDraft
    from .mailbox import service as ms
    with session() as s:
        rows = s.scalars(select(EmailDraft).where(EmailDraft.tenant_id == tenant, EmailDraft.status.in_(("pending", "scheduled")))
                         .order_by(EmailDraft.created_at)).all()
        return {"emails": [ms.draft_view(d) for d in rows]}


class EmailEdit(BaseModel):
    to: str | None = None
    cc: str | None = None
    bcc: str | None = None
    subject: str | None = None
    body: str | None = None
    send_now: bool = False          # ignore the scheduled time and send at once


@app.post("/api/emails/{draft_id}/send", dependencies=[Depends(require_key)])
async def send_email_draft(draft_id: str, body: EmailEdit | None = None, tenant: str = Depends(current_tenant)):
    """The user approved (optionally after editing). Sends now, or schedules when the draft has a send time."""
    from .mailbox import service as ms
    from .mailbox.base import MailError
    edits = body.model_dump(exclude_none=True) if body else {}
    if edits.pop("send_now", False):
        edits["send_at"] = None
    try:
        return await asyncio.to_thread(ms.send_draft, tenant, draft_id, edits)
    except LookupError:
        raise HTTPException(404, "Draft not found")
    except MailError as e:
        raise HTTPException(502, str(e))


@app.post("/api/emails/{draft_id}/cancel", dependencies=[Depends(require_key)])
def cancel_email_draft(draft_id: str, tenant: str = Depends(current_tenant)):
    from .db import EmailDraft
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if not d or d.tenant_id != tenant:
            raise HTTPException(404, "Draft not found")
        if d.status in ("pending", "scheduled", "failed"):
            d.status = "cancelled"
        conv = d.conversation_id
    bus.publish(conv, "email_sent", {"id": draft_id, "status": "cancelled"})
    return {"status": "cancelled"}


@app.post("/api/emails/{draft_id}/attachments", dependencies=[Depends(require_key)])
async def add_email_attachment(draft_id: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """The user adds a file from the phone to a draft before sending."""
    from .db import EmailDraft
    from .mailbox import service as ms
    from .mailbox.base import MailError
    from .pc import service as pcs
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if not d or d.tenant_id != tenant:
            raise HTTPException(404, "Draft not found")
        if d.status not in ("pending", "failed"):
            raise HTTPException(409, "This email can no longer be changed")
    try:
        row = await pcs.store_upload(file, tenant, "", "mail")
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        current = [{"file_id": a["file_id"]} if a.get("type") == "file" else
                   {"email_id": a["email_id"], "attachment_id": a["attachment_id"]} if a.get("type") == "email" else
                   {"artifact_id": a["artifact_id"]} for a in (d.attachments or [])]
    try:
        atts = await asyncio.to_thread(ms.describe_attachments, tenant, current + [{"file_id": row.id}])
    except MailError as e:
        raise HTTPException(413, str(e))
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        d.attachments = atts
        view, conv = ms.draft_view(d), d.conversation_id
    bus.publish(conv, "email_draft", view)
    return view


@app.delete("/api/emails/{draft_id}/attachments/{index}", dependencies=[Depends(require_key)])
def remove_email_attachment(draft_id: str, index: int, tenant: str = Depends(current_tenant)):
    from .db import EmailDraft
    from .mailbox import service as ms
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if not d or d.tenant_id != tenant:
            raise HTTPException(404, "Draft not found")
        atts = list(d.attachments or [])
        if 0 <= index < len(atts) and d.status in ("pending", "failed"):
            atts.pop(index)
            d.attachments = atts or None
        view, conv = ms.draft_view(d), d.conversation_id
    bus.publish(conv, "email_draft", view)
    return view


# ---------------- mailboxes (Gmail / Outlook by sign-in, any email by app password) ----------------
@app.get("/api/mail/accounts", dependencies=[Depends(require_key)])
def mail_accounts(tenant: str = Depends(current_tenant)):
    from .mailbox import accounts as ma
    return {"accounts": ma.views(tenant),
            "can_link": {"google": ma.oauth_ready("google"), "microsoft": ma.oauth_ready("microsoft")}}


class ImapIn(BaseModel):
    address: str
    password: str
    name: str = ""
    imap_host: str = ""
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 0


@app.post("/api/mail/accounts/imap", dependencies=[Depends(require_key)])
async def mail_connect_imap(body: ImapIn, tenant: str = Depends(current_tenant)):
    from .mailbox import accounts as ma
    from .mailbox.base import MailError
    try:
        await asyncio.to_thread(ma.connect_imap, tenant, body.address, body.password, body.name, body.imap_host,
                                body.imap_port, body.smtp_host, body.smtp_port)
    except MailError as e:
        raise HTTPException(400, str(e))
    return {"accounts": ma.views(tenant)}


@app.get("/api/mail/accounts/link", dependencies=[Depends(require_key)])
def mail_link(provider: str, login_hint: str = "", tenant: str = Depends(current_tenant)):
    """The app opens the returned URL in the browser; the provider sends the user back to our callback."""
    from .mailbox import accounts as ma
    from .mailbox.base import MailError
    try:
        return {"url": ma.start_link(tenant, provider, login_hint)}
    except MailError as e:
        raise HTTPException(503, str(e))


class MailAccountEdit(BaseModel):
    signature: str | None = None
    default: bool | None = None


@app.patch("/api/mail/accounts/{key}", dependencies=[Depends(require_key)])
def mail_account_edit(key: str, body: MailAccountEdit, tenant: str = Depends(current_tenant)):
    from .mailbox import accounts as ma
    from .mailbox.base import MailError
    try:
        if body.signature is not None:
            ma.set_signature(tenant, key, body.signature)
        if body.default:
            ma.set_default(tenant, key)
    except MailError as e:
        raise HTTPException(400, str(e))
    return {"accounts": ma.views(tenant)}


@app.delete("/api/mail/accounts/{key}", dependencies=[Depends(require_key)])
def mail_account_remove(key: str, tenant: str = Depends(current_tenant)):
    from .mailbox import accounts as ma
    if not ma.remove(tenant, key):
        raise HTTPException(404, "Mailbox not found")
    return {"accounts": ma.views(tenant)}


# ---------------- v0.183.0 Gmail's own settings (vacation / aliases / auto-forward) for the Email screen ----------------
@app.get("/api/mail/settings", dependencies=[Depends(require_key)])
async def mail_settings(account: str = "", tenant: str = Depends(current_tenant)):
    """Read-only view: vacation reply, send-as aliases and auto-forwarding of the (first) Gmail mailbox,
    plus scope_ok = whether this mailbox granted gmail.settings.basic (else a reconnect is needed for settings)."""
    from .mailbox import service as ms
    from .mailbox.base import MailError
    try:
        return await asyncio.to_thread(ms.settings_status, tenant, account or None)
    except MailError as e:
        raise HTTPException(400, str(e))


# ---------------- v0.182.0 rules / watch / mute / snooze (the app's Email screen) ----------------
@app.get("/api/mail/rules", dependencies=[Depends(require_key)])
def mail_rules(tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    return {"rules": sync.rules_list(tenant), "watch": sync.watch_views(tenant), "muted": sync.muted(tenant),
            "snoozed": sync.snooze_list(tenant), "searches": sync.searches_list(tenant)}


class MailRuleIn(BaseModel):
    name: str = ""
    match: dict = {}
    actions: dict = {}


@app.post("/api/mail/rules", dependencies=[Depends(require_key)])
def mail_rule_create(body: MailRuleIn, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    from .mailbox.base import MailError
    try:
        return sync.rule_create(tenant, body.name, body.match, body.actions)
    except MailError as e:
        raise HTTPException(400, str(e))


class MailRuleEdit(BaseModel):
    enabled: bool


@app.patch("/api/mail/rules/{rid}", dependencies=[Depends(require_key)])
def mail_rule_edit(rid: str, body: MailRuleEdit, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    from .mailbox.base import MailError
    try:
        return sync.rule_edit(tenant, rid, body.enabled)
    except MailError as e:
        raise HTTPException(404, str(e))


@app.delete("/api/mail/rules/{rid}", dependencies=[Depends(require_key)])
def mail_rule_remove(rid: str, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    if not sync.rule_delete(tenant, rid):
        raise HTTPException(404, "Rule not found")
    return {"rules": sync.rules_list(tenant)}


class MailWatchIn(BaseModel):
    mode: str
    account: str | None = None


@app.post("/api/mail/watch", dependencies=[Depends(require_key)])
def mail_watch(body: MailWatchIn, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    from .mailbox.base import MailError
    try:
        return {"watch": sync.set_watch_mode(tenant, body.mode, body.account)}
    except MailError as e:
        raise HTTPException(400, str(e))


class MailMuteIn(BaseModel):
    add: str = ""
    clear: bool = False


@app.post("/api/mail/mute", dependencies=[Depends(require_key)])
def mail_mute(body: MailMuteIn, tenant: str = Depends(current_tenant)):
    from .mailbox import sync
    return {"muted": sync.mute_edit(tenant, add=[x for x in body.add.split(",") if x.strip()], clear=body.clear)}


@app.delete("/api/mail/snoozes/{sid}", dependencies=[Depends(require_key)])
def mail_snooze_cancel(sid: str, tenant: str = Depends(current_tenant)):
    """Cancel = the mail comes back to the inbox right now (unread)."""
    from .mailbox import sync
    if not sync.snooze_cancel(tenant, sid):
        raise HTTPException(404, "Snooze not found")
    return {"snoozed": sync.snooze_list(tenant)}


def _mail_linked_page(view: dict | None, error: str = "") -> HTMLResponse:
    scheme = get_settings().app_redirect_scheme
    deep = f"{scheme}://mail?ok={0 if error else 1}"
    import html as _h
    msg = (f"<h2>Email Santosh se juda! ✅</h2><p>{_h.escape(view['address'])}</p>" if view else
           f"<h3>Email nahi juda</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def _finish_mail_link(request: Request) -> HTMLResponse:
    from .mailbox import accounts as ma
    from .mailbox.base import MailError
    if request.query_params.get("error"):
        return _mail_linked_page(None, request.query_params.get("error_description") or request.query_params["error"])
    try:
        view = await asyncio.to_thread(ma.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except MailError as e:
        return _mail_linked_page(None, str(e))
    return _mail_linked_page(view)


# ---------------- Google Calendar ----------------
def _cal_page(address: str | None, error: str = "") -> HTMLResponse:
    import html as _h
    scheme = get_settings().app_redirect_scheme
    deep = f"{scheme}://calendar?ok={0 if error else 1}"
    msg = (f"<h2>Google Calendar Santosh se juda! ✅</h2><p>{_h.escape(address or '')}</p>" if not error else
           f"<h3>Calendar nahi juda</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def _finish_cal_link(request: Request) -> HTMLResponse:
    from .cal import accounts as ca
    from .cal.google import CalError
    if request.query_params.get("error"):
        return _cal_page(None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(ca.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except CalError as e:
        return _cal_page(None, str(e))
    return _cal_page(view["address"])


def _cal_state(tenant: str) -> dict:
    from .cal import accounts as ca
    from .cal import service as cs
    out = {"accounts": ca.views(tenant), "can_link": ca.oauth_ready(), "prefs": cs.prefs(tenant), "calendars": []}
    try:
        out["calendars"] = [{k: c[k] for k in ("ref", "name", "account", "primary", "reading", "default", "role", "color")}
                            for c in cs.all_calendars(tenant)]
    except Exception as e:
        out["error"] = str(e)
    return out


@app.get("/api/calendar/accounts", dependencies=[Depends(require_key)])
def calendar_accounts(tenant: str = Depends(current_tenant)):
    return _cal_state(tenant)


@app.get("/api/calendar/link", dependencies=[Depends(require_key)])
def calendar_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
    from .cal import accounts as ca
    from .cal.google import CalError
    try:
        return {"url": ca.start_link(tenant, login_hint)}
    except CalError as e:
        raise HTTPException(503, str(e))


class CalPrefsIn(BaseModel):
    read_calendars: list[str] | None = None
    default_calendar: str | None = None
    alert_minutes: int | None = None
    default_account: str | None = None


@app.patch("/api/calendar/prefs", dependencies=[Depends(require_key)])
def calendar_prefs(body: CalPrefsIn, tenant: str = Depends(current_tenant)):
    from .cal import accounts as ca
    from .cal import service as cs
    from .cal.google import CalError
    try:
        if body.default_account:
            ca.set_default(tenant, body.default_account)
        kw = {}
        if body.read_calendars is not None:
            kw["read_calendars"] = body.read_calendars or None
        if body.default_calendar is not None:
            kw["default_calendar"] = body.default_calendar
        if body.alert_minutes is not None:
            kw["alert_minutes"] = max(0, min(body.alert_minutes, 120))
        if kw:
            cs.set_prefs(tenant, **kw)
    except CalError as e:
        raise HTTPException(400, str(e))
    return _cal_state(tenant)


@app.delete("/api/calendar/accounts/{key}", dependencies=[Depends(require_key)])
def calendar_remove(key: str, tenant: str = Depends(current_tenant)):
    from .cal import accounts as ca
    if not ca.remove(tenant, key):
        raise HTTPException(404, "Calendar not found")
    return _cal_state(tenant)


# ---------------- Google Sheets ----------------
def _linked_page(what: str, host: str, address: str | None, error: str = "") -> HTMLResponse:
    import html as _h
    deep = f"{get_settings().app_redirect_scheme}://{host}?ok={0 if error else 1}"
    msg = (f"<h2>{what} Santosh se juda! ✅</h2><p>{_h.escape(address or '')}</p>" if not error else
           f"<h3>{what} nahi juda</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def _finish_sheets_link(request: Request) -> HTMLResponse:
    from .sheets import accounts as sa
    from .sheets.client import SheetError
    if request.query_params.get("error"):
        return _linked_page("Google Sheets", "sheets", None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(sa.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except SheetError as e:
        return _linked_page("Google Sheets", "sheets", None, str(e))
    return _linked_page("Google Sheets", "sheets", view["address"])


def _sheets_state(tenant: str) -> dict:
    from .sheets import accounts as sa
    from .sheets import service as ss
    return {"accounts": sa.views(tenant), "can_link": sa.oauth_ready(), "recent": ss.recent(tenant)}


@app.get("/api/sheets/accounts", dependencies=[Depends(require_key)])
def sheets_accounts(tenant: str = Depends(current_tenant)):
    return _sheets_state(tenant)


@app.get("/api/sheets/link", dependencies=[Depends(require_key)])
def sheets_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
    from .sheets import accounts as sa
    from .sheets.client import SheetError
    try:
        return {"url": sa.start_link(tenant, login_hint)}
    except SheetError as e:
        raise HTTPException(503, str(e))


@app.delete("/api/sheets/accounts/{key}", dependencies=[Depends(require_key)])
def sheets_remove(key: str, tenant: str = Depends(current_tenant)):
    from .sheets import accounts as sa
    if not sa.remove(tenant, key):
        raise HTTPException(404, "Account not found")
    return _sheets_state(tenant)


# ---------------- YouTube ----------------
async def _finish_youtube_link(request: Request) -> HTMLResponse:
    from .youtube import accounts as ya
    from .youtube.client import YTError
    if request.query_params.get("error"):
        return _linked_page("YouTube", "youtube", None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(ya.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except YTError as e:
        return _linked_page("YouTube", "youtube", None, str(e))
    return _linked_page("YouTube", "youtube", (view.get("channel") or "") + " · " + view["address"])


def _youtube_state(tenant: str) -> dict:
    from .youtube import accounts as ya
    st = get_settings()
    return {"accounts": ya.views(tenant), "can_link": ya.oauth_ready(), "public_search": bool(st.youtube_api_key),
            "can_watch": bool(st.gemini_api_key)}


# ---------------- v0.277 INDIAMART: product pictures + one product's full record (IndiaMART's own MCP, read-only)
@app.get("/api/indiamart/img")
async def indiamart_img(u: str = "", s: str = ""):
    """Signed picture proxy (the console allows only its own origin): IndiaMART image hosts only, never an open proxy."""
    from . import indiamart as im
    if not im.img_ok(u, s):
        raise HTTPException(404, "not found")
    try:
        body, ctype = await im.fetch_image(u)
    except Exception:
        raise HTTPException(404, "not found")
    return Response(content=body, media_type=ctype, headers={"Cache-Control": "public, max-age=86400",
                                                             "X-Content-Type-Options": "nosniff"})


@app.get("/api/indiamart/product/{pid}", dependencies=[Depends(require_key)])
async def indiamart_product(pid: str, tenant: str = Depends(current_tenant)):
    from . import indiamart as im
    try:
        return await im.detail(pid)
    except im.IndiaMartError as e:
        raise HTTPException(502, str(e))


@app.get("/api/youtube/accounts", dependencies=[Depends(require_key)])
def youtube_accounts(tenant: str = Depends(current_tenant)):
    return _youtube_state(tenant)


@app.get("/api/youtube/link", dependencies=[Depends(require_key)])
def youtube_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
    from .youtube import accounts as ya
    from .youtube.client import YTError
    try:
        return {"url": ya.start_link(tenant, login_hint)}
    except YTError as e:
        raise HTTPException(503, str(e))


@app.delete("/api/youtube/accounts/{key}", dependencies=[Depends(require_key)])
def youtube_remove(key: str, tenant: str = Depends(current_tenant)):
    from .youtube import accounts as ya
    if not ya.remove(tenant, key):
        raise HTTPException(404, "Account not found")
    return _youtube_state(tenant)


# ---------------- Google Slides ----------------
async def _finish_slides_link(request: Request) -> HTMLResponse:
    from .slides import accounts as sla
    from .slides.client import SlidesError
    if request.query_params.get("error"):
        return _linked_page("Google Slides", "slides", None, request.query_params["error"])
    try:
        view = await asyncio.to_thread(sla.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except SlidesError as e:
        return _linked_page("Google Slides", "slides", None, str(e))
    return _linked_page("Google Slides", "slides", view["address"])


def _slides_state(tenant: str) -> dict:
    from .slides import accounts as sla
    from .slides import service as slv
    return {"accounts": sla.views(tenant), "can_link": sla.oauth_ready(), "recent": slv.recent(tenant)}


@app.get("/api/slides/accounts", dependencies=[Depends(require_key)])
def slides_accounts(tenant: str = Depends(current_tenant)):
    return _slides_state(tenant)


@app.get("/api/slides/link", dependencies=[Depends(require_key)])
def slides_link(login_hint: str = "", tenant: str = Depends(current_tenant)):
    from .slides import accounts as sla
    from .slides.client import SlidesError
    try:
        return {"url": sla.start_link(tenant, login_hint)}
    except SlidesError as e:
        raise HTTPException(503, str(e))


@app.delete("/api/slides/accounts/{key}", dependencies=[Depends(require_key)])
def slides_remove(key: str, tenant: str = Depends(current_tenant)):
    from .slides import accounts as sla
    if not sla.remove(tenant, key):
        raise HTTPException(404, "Account not found")
    return _slides_state(tenant)


# ---------------- Hoola Network: avatars talk to avatars ----------------
class NetMeIn(BaseModel):
    handle: str | None = None
    discoverable: bool | None = None
    phone: str | None = None


class NetConnectIn(BaseModel):
    to: str = ""
    invite: str = ""
    relation: str = "friend"
    note: str = ""


class NetAnswerIn(BaseModel):
    action: str
    relation: str = ""


class NetLinkIn(BaseModel):
    vip: bool | None = None
    nick: str | None = None
    relation: str | None = None
    verified: bool | None = None


class NetDecideIn(BaseModel):
    action: str
    slot: int | None = None
    minutes: int | None = None
    note: str = ""


class NetSendIn(BaseModel):
    to: str
    kind: str = "message"
    body: dict = Field(default_factory=dict)
    thread_id: str = ""
    handle: bool = False
    goal: str = ""


class NetReplyIn(BaseModel):
    text: str


def _net(fn, *a, **kw):
    from .net import identity as idn
    from .net import service as net
    try:
        return fn(*a, **kw)
    except (net.NetError, idn.IdError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/net/me", dependencies=[Depends(require_key)])
def net_me(tenant: str = Depends(current_tenant)):
    from .net import service as net
    out = _net(net.me, tenant)
    return {k: v for k, v in out.items() if k != "public_key"}


@app.put("/api/net/me", dependencies=[Depends(require_key)])
def net_me_put(body: NetMeIn, tenant: str = Depends(current_tenant)):
    from .net import identity as idn
    if body.handle:
        _net(idn.set_handle, tenant, body.handle)
    if body.discoverable is not None:
        _net(idn.set_discovery, tenant, body.phone, body.discoverable)
    return net_me(tenant)


@app.post("/api/net/invite", dependencies=[Depends(require_key)])
def net_invite(tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.invite, tenant)


@app.get("/api/net/find", dependencies=[Depends(require_key)])
def net_find(q: str, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return {"results": _net(net.find, tenant, q)}


@app.post("/api/net/connect", dependencies=[Depends(require_key)])
def net_connect(body: NetConnectIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.connect, tenant, body.to, body.invite, body.relation, body.note)


@app.get("/api/net/connections", dependencies=[Depends(require_key)])
def net_connections(status: str = "", tenant: str = Depends(current_tenant)):
    from .net import service as net
    return {"connections": _net(net.connections, tenant, status)}


@app.post("/api/net/connections/{lid}", dependencies=[Depends(require_key)])
def net_answer(lid: str, body: NetAnswerIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.answer_connect, tenant, lid, body.action, body.relation)


@app.patch("/api/net/connections/{lid}", dependencies=[Depends(require_key)])
def net_link_patch(lid: str, body: NetLinkIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.update_link, tenant, lid, vip=body.vip, nick=body.nick, relation=body.relation, verified=body.verified)


@app.get("/api/net/inbox", dependencies=[Depends(require_key)])
def net_inbox(tenant: str = Depends(current_tenant)):
    from .net import service as net
    return {"waiting": _net(net.inbox, tenant), "counts": net.counts(tenant)}


@app.post("/api/net/inbox/{mid}", dependencies=[Depends(require_key)])
def net_decide(mid: str, body: NetDecideIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.decide, tenant, mid, body.action, body.slot, body.minutes, body.note)


@app.post("/api/net/send", dependencies=[Depends(require_key)])
def net_send(body: NetSendIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.send, tenant, body.to, body.kind, body.body, "", body.thread_id, body.handle, body.goal)


@app.post("/api/net/upload", dependencies=[Depends(require_key)])
async def net_upload(file: UploadFile = File(...), to: str = Form(""), thread_id: str = Form(""), text: str = Form(""),
                     tenant: str = Depends(current_tenant)):
    """v0.43 The owner attaches a real photo / video / PDF / any file in a Hoola chat. Their own tap = consent."""
    from .mailbox import service as ms
    from .net import service as net
    from .net.share import MAX_MB
    data = await file.read(MAX_MB * 1024 * 1024 + 1)
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"The file is bigger than {MAX_MB} MB; send a Drive link.")
    if not data:
        raise HTTPException(400, "File khaali hai.")
    if thread_id and not to:
        to = _net(net.thread, tenant, thread_id)["peer"]
    if not to:
        raise HTTPException(400, "Kise bhejna hai (to / thread_id)?")
    row = await asyncio.to_thread(ms.store_bytes, tenant, file.filename or "file", data)
    return await asyncio.to_thread(_net, net.send, tenant, to, "file", {"file_id": row.id, "text": text[:2000]},
                                   (text or row.name)[:80], thread_id, False, "")


class NetMakeIn(BaseModel):
    kind: str = "pdf"           # pdf | image
    title: str = ""
    content: str = ""


@app.post("/api/net/make", dependencies=[Depends(require_key)])
async def net_make(body: NetMakeIn, tenant: str = Depends(current_tenant)):
    """The avatar makes a document / picture; the app shows it and the owner decides to send it (nothing goes out)."""
    from .net import handle
    from .net.share import local_view
    f = await asyncio.to_thread(_net, handle.make_file, tenant, "image" if body.kind == "image" else "pdf", body.title,
                                body.content)
    return f | (await asyncio.to_thread(local_view, tenant, f["file_id"]))


@app.post("/api/net/messages/{mid}/think", dependencies=[Depends(require_key)])
async def net_think(mid: str, tenant: str = Depends(current_tenant)):
    """'Hoola, isse dekh ke batao': look at the attachment again and suggest replies, right now."""
    from .net import enrich
    return await asyncio.to_thread(enrich.run, tenant, mid)


# ---------------- v0.65 Hoola Video Editor ----------------
class VideoStart(BaseModel):
    file_ids: list[str] = Field(default_factory=list, max_length=8)
    brief: str = Field(default="", max_length=3000)
    platform: str = "reel"
    length_s: int | None = None
    captions: bool = True
    logo_file_id: str = ""
    music_file_id: str = ""
    title: str = ""
    conversation_id: str = ""


class VideoChange(BaseModel):
    instruction: str = Field(min_length=1, max_length=1500)


def _video_call(fn, *a, **k):
    from .videoedit.service import VideoError
    try:
        return fn(*a, **k)
    except VideoError as e:
        raise HTTPException(400, str(e))


@app.get("/api/video/jobs", dependencies=[Depends(require_key)])
def video_jobs(tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return {"jobs": vs.listing(tenant), "platforms": [{"id": k, **v} for k, v in vs.PLATFORMS.items()]}


@app.post("/api/video/jobs", dependencies=[Depends(require_key)])
def video_start(body: VideoStart, tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return _video_call(vs.start, tenant, body.file_ids, body.brief, body.platform, body.length_s, body.captions,
                       body.logo_file_id, body.music_file_id, body.title, body.conversation_id)


@app.get("/api/video/jobs/{job_id}", dependencies=[Depends(require_key)])
def video_job(job_id: str, tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return _video_call(vs.get, tenant, job_id)


@app.post("/api/video/jobs/{job_id}/revise", dependencies=[Depends(require_key)])
def video_revise(job_id: str, body: VideoChange, tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return _video_call(vs.revise, tenant, job_id, body.instruction)


@app.post("/api/video/jobs/{job_id}/cancel", dependencies=[Depends(require_key)])
def video_cancel(job_id: str, tenant: str = Depends(current_tenant)):
    from .videoedit import service as vs
    return _video_call(vs.cancel, tenant, job_id)


@app.get("/api/video/files/{job_id}/{name}")
def video_file(job_id: str, name: str, exp: int = 0, sig: str = ""):
    """Signed, expiring link to a finished video / its frames (opened by the phone's player or browser)."""
    from .videoedit import service as vs
    p = vs.file_for(job_id, name, exp, sig)
    if p is None:
        raise HTTPException(404, "This video link is old or wrong.")
    media = "video/mp4" if p.suffix == ".mp4" else "image/png" if p.suffix == ".png" else None
    return FileResponse(str(p), media_type=media, filename=p.name)


@app.get("/api/google/status", dependencies=[Depends(require_key)])
def google_status(live: bool = True, tenant: str = Depends(current_tenant)):
    """v0.70 Why her Google Drive / Gmail / Calendar do (not) work, with the fix (no tokens shown)."""
    from . import google_check
    return google_check.diagnose(tenant, live)


# ---------------- v0.68 Hoola Video Studio ----------------
class StudioDecide(BaseModel):
    yes: bool
    proof: dict | None = None      # v0.97 fingerprint signature from her phone (approvekey)


@app.get("/api/studio", dependencies=[Depends(require_key)])
def studio_home(tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    projects = []
    for x in ss.listing(tenant)[:30]:
        try:
            projects.append(ss.view(tenant, ss._load(tenant, x["project"])))
        except Exception:
            pass
    st = get_settings()
    return {"available": ss.available(), "ready": ss.ready_providers(tenant), "projects": projects,
            "month_spent_usd": ss.month_spent(tenant), "month_limit_usd": st.studio_month_usd, "usd_inr": st.studio_usd_inr,
            "can_paint": bool(st.gemini_api_key), "lyria": ss.lyria_ready(), "voices": list(ss.VOICES),
            "styles": list(ss.catalog.STYLES), "moods": list(ss.MOODS),
            "models": _studio_models(tenant)}


def _studio_models(tenant: str) -> list[dict]:
    """v0.259 the Create Studio model picker: the studio's real models, with readiness and the rupee rate."""
    from .studio import service as ss
    try:
        return [{k: m.get(k) for k in ("model", "label", "ready", "inr_per_second", "durations_s")} for m in ss.models(tenant)]
    except Exception:
        log.exception("studio models")
        return []


class StudioPrice(BaseModel):
    model: str = Field(default="", max_length=80)
    seconds: int = Field(default=8, ge=1, le=60)
    resolution: str = Field(default="1080p", max_length=8)
    audio: bool = True
    takes: int = Field(default=1, ge=1, le=4)
    kind: str = Field(default="scene", max_length=12)
    auto: str = Field(default="quality", pattern="^(quality|value|cheap)$")   # v0.263


# ---------------------------------------------------------------- v0.329 SHOWCASE: real Hoola-made pictures / clips on the studio pages
@app.get("/api/studio/showcase", dependencies=[Depends(require_key)])
async def studio_showcase(tenant: str = Depends(current_tenant)):
    """Which studio cards have a real picture / clip (every account's studio shows them); the owner also gets her panel."""
    from .studio import showcase
    out: dict = {"slots": await asyncio.to_thread(showcase.manifest)}
    if tenant == get_settings().tenant_id:
        out["owner"] = await asyncio.to_thread(showcase.status)
    return out


@app.post("/api/studio/showcase/{action}", dependencies=[Depends(require_key)])
async def studio_showcase_act(action: str, tenant: str = Depends(current_tenant)):
    """Owner only. setup = the hidden showcase film (free); pictures / clips = the NORMAL price cards for it - nothing is
    made or charged until she taps Haan on the card (+ phone fingerprint at /api/studio/approvals)."""
    from .studio import service as ss
    from .studio import showcase
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "The showcase is made by the owner")
    fn = {"setup": showcase.setup, "pictures": showcase.ask_pictures, "clips": showcase.ask_clips}.get(action)
    if not fn:
        raise HTTPException(400, "action = setup | pictures | clips")
    try:
        if action != "setup":
            await showcase.setup()
        return await fn()
    except (showcase.ShowcaseError, ss.StudioJobError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/studio/showcase/file/{slot}", dependencies=[Depends(require_key)])
def studio_showcase_file(slot: str, kind: str = "pic"):
    from .studio import showcase
    try:
        f = showcase.file_for(slot, kind)
    except showcase.ShowcaseError as e:
        raise HTTPException(404, str(e))
    return FileResponse(f, media_type="video/mp4" if kind == "clip" else ("image/png" if f.suffix == ".png" else "image/jpeg"),
                        headers={"Cache-Control": "private, max-age=86400"})


@app.get("/api/studio/apis", dependencies=[Depends(require_key)])
async def studio_apis(fresh: int = 0):
    """v0.308 Which real engine behind Create is switched on (ready / no key / key refused / unreachable), each checked
    with one free provider call; keys are never returned. fresh=1 re-checks (at most once a minute)."""
    from .studio import apis
    if fresh and apis._CACHE.get("at", 0) > time.time() - 60:
        fresh = 0
    return await apis.report(bool(fresh))


@app.get("/api/studio/models", dependencies=[Depends(require_key)])
async def studio_models(tenant: str = Depends(current_tenant)):
    """v0.262 Every video model for her picker, with rupee prices per resolution (and the market Hoola cannot call yet).
    v0.263: prices re-read when older than a day, the price moves, and her own clips per model."""
    from .studio import service as ss
    return await ss.catalogue_fresh(tenant)


@app.post("/api/studio/models/refresh", dependencies=[Depends(require_key)])
async def studio_models_refresh(tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.models_refresh)(tenant)


@app.post("/api/studio/price", dependencies=[Depends(require_key)])
def studio_price(body: StudioPrice, tenant: str = Depends(current_tenant)):
    """v0.262 The live price on the Create button (the same rate table the price card and the run use)."""
    from .studio import service as ss
    try:
        return ss.clip_price(tenant, body.model, body.seconds, body.resolution, body.audio, body.takes, body.kind, body.auto)
    except ss.StudioJobError as e:
        raise HTTPException(400, str(e))


@app.get("/api/studio/projects/{name}/quote", dependencies=[Depends(require_key)])
def studio_quote(name: str, quality: str = "", model: str = "", compare: str = "", tenant: str = Depends(current_tenant)):
    """v0.262 What the next paid run of this film would cost, shot by shot, before anything is asked or spent."""
    from .studio import service as ss
    try:
        st = ss.studio_sync(tenant)
        p = ss._load(tenant, name)
        q = quality or ss.prefs_of(p)["quality"]
        cmp = [x for x in compare.split(",") if x][:3] or None              # v0.263 ?compare=a,b
        return ss.quote(st, p, q if q in ("draft", "final", "premium") else "final", None, 1, model or None, cmp)
    except (ss.StudioJobError, ss.StudioError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/studio/projects/{name}", dependencies=[Depends(require_key)])
def studio_project(name: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    try:
        return ss.view(tenant, ss._load(tenant, name))
    except ss.StudioJobError as e:
        raise HTTPException(404, str(e))


@app.post("/api/studio/approvals/{approval_id}", dependencies=[Depends(require_key)])
async def studio_decide(approval_id: str, body: StudioDecide, tenant: str = Depends(current_tenant)):
    """Her tap on a price card: only now does a paid generation start (capped at the shown price)."""
    from .studio import service as ss
    if body.yes:
        _fingerprint(tenant, "studio", approval_id, body.proof)
    try:
        return await ss.decide(tenant, approval_id, body.yes)
    except ss.StudioJobError as e:
        raise HTTPException(400, str(e))


@app.post("/api/studio/projects/{name}/assemble", dependencies=[Depends(require_key)])
async def studio_assemble(name: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    try:
        return await ss.assemble(tenant, name)
    except ss.StudioJobError as e:
        raise HTTPException(400, str(e))


class StudioNew(BaseModel):          # v0.157 the app's "Naya video" form
    name: str = Field(min_length=2, max_length=60)
    brief: str = Field(default="", max_length=2000)
    aspect: str = "9:16"
    style: str = "reel"
    language: str = "Hindi"
    seconds: int = Field(default=30, ge=2, le=600)   # v0.310 the Video page offers 4 s / 5 s clips (was ge=6 -> 422)
    voice: str = ""                  # v0.159 male | female
    captions: bool = True
    caption_style: str = "bold"
    music: str = ""                  # a mood (Lyria, paid in the same card) or "" = none
    quality: str = "final"
    model: str = Field(default="", max_length=80)        # v0.262 her model pick ("" = Hoola Auto)
    resolution: str = Field(default="", max_length=8)    # v0.262 her resolution pick ("" = by quality)
    auto: str = Field(default="quality", pattern="^(quality|value|cheap)$")   # v0.263 how Hoola Auto chooses
    then: str = Field(default="", pattern="^(|generate|preview)$")   # v0.309 Video page: price card / free preview once planned
    variants: int = Field(default=1, ge=1, le=4)
    compare: list[str] | None = None


class StudioPlan(BaseModel):
    brief: str = Field(default="", max_length=2000)
    seconds: int = Field(default=30, ge=2, le=600)   # v0.310 the Video page offers 4 s / 5 s clips (was ge=6 -> 422)


class StudioRun(BaseModel):
    quality: str = "preview"
    shot_ids: list[str] | None = None
    variants: int = Field(default=1, ge=1, le=4)
    model: str | None = Field(default=None, max_length=80)     # v0.259 Create Studio's model picker ('' / None = best per shot)
    compare: list[str] | None = Field(default=None, max_length=3)   # v0.263 the same shots by 2-3 models, one card


class StudioPick(BaseModel):
    shot_id: str
    take: int


class StudioShot(BaseModel):
    prompt: str | None = Field(default=None, max_length=1500)
    dialogue: str | None = Field(default=None, max_length=600)
    caption: str | None = Field(default=None, max_length=120)
    duration: int | None = Field(default=None, ge=2, le=30)
    kind: str | None = None
    camera: str | None = None
    characters: list[str] | None = Field(default=None, max_length=6)
    transition: str | None = None
    speaker: str | None = None
    model: str | None = Field(default=None, max_length=80)        # v0.262 a model for this scene only


class StudioMusic(BaseModel):
    mood: str = "upbeat"
    volume: float = 0.25
    file_id: str = ""                # v0.159 her own licensed song


class StudioVoiceover(BaseModel):
    shot_id: str
    text: str = Field(default="", max_length=600)
    file_id: str = ""


class StudioCharacter(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=400)
    file_ids: list[str] = Field(default_factory=list, max_length=4)
    consent: bool = False
    voice: str = ""
    kind: str = "person"             # v0.159 person | place | product


class StudioSettings(BaseModel):
    voice: str | None = None
    captions: bool | None = None
    caption_style: str | None = None
    music: str | None = None
    quality: str | None = None
    logo_position: str | None = None
    style: str | None = None
    music_volume: float | None = Field(default=None, ge=0, le=1)
    model: str | None = Field(default=None, max_length=80)        # v0.262 "" = Hoola Auto
    resolution: str | None = Field(default=None, max_length=8)
    auto: str | None = Field(default=None, pattern="^(quality|value|cheap)$")   # v0.263
    cast_skip: bool | None = None    # v0.311 "No fixed characters": the film goes on without a cast
    pics_skip: bool | None = None    # v0.312 no opening pictures: the shots are made from the words


class StudioAddShot(BaseModel):
    prompt: str = Field(default="", max_length=1500)
    duration: int = Field(default=5, ge=2, le=30)
    kind: str = "scene"
    camera: str | None = None
    dialogue: str | None = Field(default=None, max_length=600)
    caption: str | None = Field(default=None, max_length=120)
    characters: list[str] = Field(default_factory=list, max_length=6)
    after: str = ""


class StudioRedo(BaseModel):
    change: str = Field(default="", max_length=300)
    quality: str = ""


class StudioImprove(BaseModel):
    brief: str = Field(min_length=1, max_length=2000)
    language: str = "Hindi"
    seconds: int = Field(default=30, ge=2, le=600)   # v0.310 the Video page offers 4 s / 5 s clips (was ge=6 -> 422)
    kind: str = Field(default="video", pattern="^(video|image)$")   # v0.304 image = the Image page's Enhance


class StudioLogo(BaseModel):
    file_id: str
    position: str = "top-right"


def _studio_call(fn):
    async def run(*a, **k):
        from .studio import service as ss
        try:
            return await fn(*a, **k)
        except (ss.StudioJobError, ss.StudioError) as e:
            raise HTTPException(400, str(e))
    return run


@app.post("/api/studio/projects", dependencies=[Depends(require_key)])
async def studio_new(body: StudioNew, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    v = await _studio_call(ss.create)(tenant, body.name, body.aspect, body.style, body.language, body.brief, "",
                                      {"voice": body.voice, "captions": body.captions, "caption_style": body.caption_style,
                                       "music": body.music, "quality": body.quality, "model": body.model,
                                       "resolution": body.resolution, "auto": body.auto})
    if body.brief.strip():
        await _studio_call(ss.plan)(tenant, v["project"], body.brief, body.seconds, "")
        if body.then:           # v0.309 the server waits for its own storyboard, then makes the price card (or free preview)
            name, prev = v["project"], body.then == "preview"
            ss.after_plan(tenant, name, lambda: ss.generate(
                tenant, name, "preview" if prev else body.quality, None, 1 if prev else body.variants,
                body.model or None, "", None if prev or not body.compare or len(body.compare) < 2 else body.compare))
    return ss.view(tenant, ss._load(tenant, v["project"]))


@app.post("/api/studio/projects/{name}/plan", dependencies=[Depends(require_key)])
async def studio_plan(name: str, body: StudioPlan, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.plan)(tenant, name, body.brief, body.seconds, "")


@app.post("/api/studio/projects/{name}/keyframes", dependencies=[Depends(require_key)])
async def studio_keyframes(name: str, body: StudioRun, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.keyframes)(tenant, name, body.shot_ids)


@app.post("/api/studio/projects/{name}/generate", dependencies=[Depends(require_key)])
async def studio_generate(name: str, body: StudioRun, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.generate)(tenant, name, body.quality, body.shot_ids, body.variants, body.model or None, "",
                                           body.compare or None)


@app.post("/api/studio/projects/{name}/pick", dependencies=[Depends(require_key)])
async def studio_pick(name: str, body: StudioPick, tenant: str = Depends(current_tenant)):
    from .studio import service as ss

    async def go():
        st = await ss.studio(tenant)
        r = st.pick(name, body.shot_id, body.take)
        ss._changed(tenant, name)
        return r
    return await _studio_call(go)()


@app.patch("/api/studio/projects/{name}/shots/{shot_id}", dependencies=[Depends(require_key)])
async def studio_shot(name: str, shot_id: str, body: StudioShot, tenant: str = Depends(current_tenant)):
    from .studio import service as ss

    async def go():
        st = await ss.studio(tenant)
        st.shot_update(name, shot_id, body.model_dump(exclude_none=True))
        ss._changed(tenant, name)
        return ss.view(tenant, ss._load(tenant, name))
    return await _studio_call(go)()


@app.post("/api/studio/projects/{name}/music", dependencies=[Depends(require_key)])
async def studio_music(name: str, body: StudioMusic, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.music)(tenant, name, body.mood, body.file_id, body.volume)


@app.post("/api/studio/projects/{name}/voiceover", dependencies=[Depends(require_key)])
async def studio_voiceover(name: str, body: StudioVoiceover, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    await _studio_call(ss.voiceover)(tenant, name, body.shot_id, body.text, body.file_id)
    return ss.view(tenant, ss._load(tenant, name))


@app.post("/api/studio/projects/{name}/characters", dependencies=[Depends(require_key)])
async def studio_character(name: str, body: StudioCharacter, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    if body.file_ids:
        return await _studio_call(ss.character)(tenant, name, body.name, body.description, body.file_ids, body.consent, body.voice,
                                                body.kind)
    return await _studio_call(ss.character_generate)(tenant, name, body.name, body.description, body.kind, body.voice)


@app.post("/api/studio/projects/{name}/settings", dependencies=[Depends(require_key)])
async def studio_settings(name: str, body: StudioSettings, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.settings)(tenant, name, body.model_dump(exclude_none=True))


@app.post("/api/studio/projects/{name}/shots", dependencies=[Depends(require_key)])
async def studio_add_shot(name: str, body: StudioAddShot, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    d = body.model_dump(exclude_none=True)
    after = d.pop("after", "")
    return await _studio_call(ss.add_shot)(tenant, name, d, after)


@app.delete("/api/studio/projects/{name}/shots/{shot_id}", dependencies=[Depends(require_key)])
async def studio_delete_shot(name: str, shot_id: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.delete_shot)(tenant, name, shot_id)


@app.post("/api/studio/projects/{name}/shots/{shot_id}/redo", dependencies=[Depends(require_key)])
async def studio_redo_shot(name: str, shot_id: str, body: StudioRedo, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.redo_shot)(tenant, name, shot_id, body.change, body.quality)


@app.post("/api/studio/projects/{name}/shots/{shot_id}/line", dependencies=[Depends(require_key)])
async def studio_line(name: str, shot_id: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.speak_line)(tenant, name, shot_id)


@app.post("/api/studio/projects/{name}/cancel", dependencies=[Depends(require_key)])
async def studio_cancel(name: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.cancel)(tenant, name)


@app.post("/api/studio/projects/{name}/logo", dependencies=[Depends(require_key)])
async def studio_logo(name: str, body: StudioLogo, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    await _studio_call(ss.logo)(tenant, name, body.file_id, body.position)
    return ss.view(tenant, ss._load(tenant, name))


@app.delete("/api/studio/projects/{name}", dependencies=[Depends(require_key)])
async def studio_hide(name: str, tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.hide)(tenant, name)


@app.post("/api/studio/improve", dependencies=[Depends(require_key)])
async def studio_improve(body: StudioImprove):
    from .studio import service as ss
    return await _studio_call(ss.improve_brief)(body.brief, body.language, body.seconds, body.kind)


@app.get("/api/studio/voice_sample", dependencies=[Depends(require_key)])
async def studio_voice_sample(voice: str = "male", language: str = "Hindi", tenant: str = Depends(current_tenant)):
    from .studio import service as ss
    return await _studio_call(ss.voice_sample)(tenant, voice, language)


# ---------------------------------------------------------------- v0.259 CREATE STUDIO (song / voice / dub / image jobs)
class CreateJob(BaseModel):
    kind: str = Field(pattern="^(image|cast|song|voice|dub)$")
    name: str = Field(default="", max_length=40)              # cast
    conversation_id: str = Field(default="", max_length=80)    # the chat that also gets the result cards
    title: str = Field(default="", max_length=80)
    prompt: str = Field(default="", max_length=4000)         # image
    file_ids: list[str] = Field(default_factory=list, max_length=4)
    aspect: str = Field(default="", max_length=8)
    quality: str = Field(default="fast", max_length=8)
    style: str = Field(default="", max_length=60)
    count: int = Field(default=1, ge=1, le=4)
    brief: str = Field(default="", max_length=1200)          # song
    genre: str = Field(default="", max_length=60)
    language: str = Field(default="Hindi", max_length=30)
    vocals: str = Field(default="duet", max_length=20)
    mood: str = Field(default="", max_length=60)
    bpm: int = Field(default=0, ge=0, le=220)
    seconds: int = Field(default=0, ge=0, le=600)
    lyrics: str = Field(default="", max_length=3000)
    text: str = Field(default="", max_length=5000)           # voice
    voice: str = Field(default="", max_length=40)
    speed: float = Field(default=1.0, ge=0.6, le=1.6)
    file_id: str = Field(default="", max_length=80)          # dub
    languages: list[str] = Field(default_factory=list, max_length=4)
    keep_sound: bool = True


@app.get("/api/create", dependencies=[Depends(require_key)])
def create_home(tenant: str = Depends(current_tenant)):
    from .create import service as cs
    return {"ready": cs.ready(), "voices": cs.voices(), "styles": list(cs.STYLES), "languages": list(cs.LANGS)}


@app.post("/api/create/jobs", dependencies=[Depends(require_key)])
async def create_job(body: CreateJob, tenant: str = Depends(current_tenant)):
    from .create import jobs
    if body.conversation_id:
        _conv_or_404(body.conversation_id, tenant)
    try:
        return jobs.start(tenant, body.kind, body.model_dump(), body.conversation_id)
    except jobs.JobError as e:
        raise HTTPException(400, str(e))


class CreateWrite(BaseModel):
    kind: str = Field(pattern="^(script|lyrics)$")
    brief: str = Field(min_length=4, max_length=3000)
    format: str = Field(default="", max_length=40)
    length: str = Field(default="", max_length=20)
    language: str = Field(default="Hinglish", max_length=30)
    tone: str = Field(default="", max_length=40)
    genre: str = Field(default="", max_length=60)
    mood: str = Field(default="", max_length=60)
    title: str = Field(default="", max_length=80)


@app.post("/api/create/write", dependencies=[Depends(require_key)])
async def create_write(body: CreateWrite, tenant: str = Depends(current_tenant)):
    """v0.259 the Script writer / Write-with-Hoola lyrics: the words come back to the page; a script is also kept."""
    from . import usage
    from .create import jobs, service as cs
    try:
        with usage.scope(tenant, "create"):
            text = await cs.write(body.kind, body.brief, body.format, body.length, body.language, body.tone, body.genre, body.mood)
    except cs.CreateError as e:
        raise HTTPException(400, str(e))
    item = None
    if body.kind == "script":
        it = jobs.keep(tenant, "script", body.title or ("Script · " + body.brief[:40]), ".txt", text.encode("utf-8"),
                       {"format": body.format, "length": body.length, "language": body.language, "tone": body.tone})
        item = {k: v for k, v in it.items() if k != "file"}
    return {"text": text, "item": item}


@app.put("/api/create/items/{item_id}/text", dependencies=[Depends(require_key)])
async def create_item_text(item_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her edits to a kept script (plain text, up to 40 000 characters)."""
    from .create import jobs
    text = str((body or {}).get("text") or "")[:40000]
    try:
        path, it = jobs.item_file(tenant, item_id)
    except jobs.JobError as e:
        raise HTTPException(404, str(e))
    if it["kind"] != "script":
        raise HTTPException(400, "Only the script can be changed")
    path.write_text(text, encoding="utf-8")
    return {"ok": True, "size": len(text.encode("utf-8"))}


@app.get("/api/create/jobs", dependencies=[Depends(require_key)])
def create_jobs(tenant: str = Depends(current_tenant)):
    from .create import jobs
    return {"jobs": jobs.recent(tenant)}


@app.get("/api/create/jobs/{job_id}", dependencies=[Depends(require_key)])
def create_job_get(job_id: str, tenant: str = Depends(current_tenant)):
    from .create import jobs
    try:
        return jobs.get(tenant, job_id)
    except jobs.JobError as e:
        raise HTTPException(404, str(e))


@app.get("/api/create/items", dependencies=[Depends(require_key)])
def create_items(kind: str = "", tenant: str = Depends(current_tenant)):
    from .create import jobs
    items = jobs.shelf(tenant)
    if kind:
        items = [i for i in items if i["kind"] == kind]
    return {"items": [{k: v for k, v in i.items() if k != "file"} for i in items[:300]]}


@app.get("/api/create/items/{item_id}", dependencies=[Depends(require_key)])
def create_item_file(item_id: str, tenant: str = Depends(current_tenant)):
    from .create import jobs
    try:
        path, it = jobs.item_file(tenant, item_id)
    except jobs.JobError as e:
        raise HTTPException(404, str(e))
    return FileResponse(path, media_type=it["mime"], headers={"Cache-Control": "private, max-age=86400",
                                                              "X-Content-Type-Options": "nosniff",
                                                              "Content-Security-Policy": "default-src 'none'; sandbox"})


@app.delete("/api/create/items/{item_id}", dependencies=[Depends(require_key)])
def create_item_delete(item_id: str, tenant: str = Depends(current_tenant)):
    from .create import jobs
    if not jobs.forget(tenant, item_id):
        raise HTTPException(404, "This creation was not found")
    return {"ok": True}


@app.get("/api/studio/files/{tenant_key}/{exp}/{sig}/{name}")
def studio_file(tenant_key: str, exp: str, sig: str, name: str):
    """Signed links to her finished videos / sheets (the app's player and download need no header)."""
    from .studio import service as ss
    f = ss.file_for(tenant_key, exp, sig, name)
    if f is None:
        raise HTTPException(404, "link expired or wrong")
    return FileResponse(f)


@app.get("/api/studio/media/{tenant_key}/media/{sig}/{exp}/{name}")
def studio_media(tenant_key: str, sig: str, exp: str, name: str):
    """Short-lived signed links to character photos, only for a video provider that needs a URL (STUDIO_IMAGE_MODE=public)."""
    from .studio import service as ss
    f = ss.studio_sync(tenant_key).verify_media(sig, exp, name)
    if f is None:
        raise HTTPException(404, "no")
    return FileResponse(f)


# ---------------- v0.67 Hoola Computer Operator ----------------
class OperatorStart(BaseModel):
    task: str = Field(min_length=6, max_length=3000)
    start_url: str = Field(default="", max_length=1000)
    file_ids: list[str] = Field(default_factory=list, max_length=8)
    conversation_id: str = ""


class OperatorAnswer(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    answer: str = Field(default="", max_length=500)   # OTP / CAPTCHA / her secret: typed into the page, never stored


class OperatorInput(BaseModel):
    kind: str = Field(pattern="^(click|type|key)$")
    x: float = 0
    y: float = 0
    text: str = Field(default="", max_length=500)
    key: str = Field(default="", max_length=20)


def _op_call(fn, *a, **k):
    from .operator.service import OperatorJobError
    try:
        return fn(*a, **k)
    except OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.get("/api/operator", dependencies=[Depends(require_key)])
def operator_home(tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    return {"available": ops.available(), "active": ops.active(tenant), "tasks": ops.listing(tenant, 20),
            "recipes": [{k: r.get(k) for k in ("name", "task", "site", "variables", "runs", "updated", "version")}
                        for r in ops.recipes(tenant)]}


@app.post("/api/operator/tasks", dependencies=[Depends(require_key)])
def operator_start(body: OperatorStart, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    return _op_call(ops.start, tenant, body.task, body.start_url, body.file_ids, body.conversation_id)


@app.get("/api/operator/tasks/{task_id}", dependencies=[Depends(require_key)])
def operator_task(task_id: str, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    return _op_call(ops.get, tenant, task_id)


@app.post("/api/operator/tasks/{task_id}/cancel", dependencies=[Depends(require_key)])
def operator_cancel(task_id: str, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    return _op_call(ops.cancel, tenant, task_id)


@app.get("/api/operator/frame", dependencies=[Depends(require_key)])
async def operator_frame(tenant: str = Depends(current_tenant)):
    """The live view: a picture of the job's browser right now (the phone polls it while the job runs)."""
    from .operator import service as ops
    try:
        b = await ops.frame(tenant)
    except ops.OperatorJobError as e:
        raise HTTPException(404, str(e))
    return Response(b, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.post("/api/operator/input", dependencies=[Depends(require_key)])
async def operator_input(body: OperatorInput, tenant: str = Depends(current_tenant)):
    """Her own hands in the live view (tap / type / key): never logged as text, never shown to the model."""
    from .operator import service as ops
    try:
        return await ops.owner_input(tenant, body.kind, body.x, body.y, body.text, body.key)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.post("/api/operator/requests/{request_id}", dependencies=[Depends(require_key)])
async def operator_answer(request_id: str, body: OperatorAnswer, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    try:
        return await ops.resolve(tenant, request_id, body.status, body.answer)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.get("/api/operator/requests/{request_id}/captcha", dependencies=[Depends(require_key)])
async def operator_captcha(request_id: str, tenant: str = Depends(current_tenant)):
    """v0.76 the CAPTCHA picture for her phone (she may be far from the computer)."""
    from .operator import service as ops
    try:
        b = await ops.captcha_image(tenant, request_id)
    except ops.OperatorJobError as e:
        raise HTTPException(404, str(e))
    return Response(b, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.post("/api/operator/requests/{request_id}/captcha/refresh", dependencies=[Depends(require_key)])
async def operator_captcha_refresh(request_id: str, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    try:
        return await ops.captcha_refresh(tenant, request_id)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.get("/api/operator/requests/{request_id}/captcha/solve", dependencies=[Depends(require_key)])
async def operator_captcha_solve(request_id: str, tenant: str = Depends(current_tenant)):
    """v0.78 Hoola reads the CAPTCHA (OCR) and returns the solved text for owner confirmation."""
    from .operator import service as ops
    try:
        return await ops.captcha_solve(tenant, request_id)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.post("/api/operator/requests/{request_id}/captcha/fill", dependencies=[Depends(require_key)])
async def operator_captcha_fill(request_id: str, body: OperatorAnswer, tenant: str = Depends(current_tenant)):
    """v0.78 After the owner confirms / corrects the CAPTCHA answer, type it into the box."""
    from .operator import service as ops
    try:
        return await ops.captcha_fill(tenant, request_id, body.answer)
    except ops.OperatorJobError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/operator/recipes/{name}", dependencies=[Depends(require_key)])
def operator_forget(name: str, tenant: str = Depends(current_tenant)):
    from .operator import service as ops
    if not ops.forget_recipe(tenant, name):
        raise HTTPException(404, "no such recipe")
    return {"ok": True}


@app.get("/api/app/latest", dependencies=[Depends(require_key)])
async def app_latest(current: str = "", force: bool = False):
    """v0.62 Newest phone-app release (GitHub APK build): version, apk_url, size, sha256, notes, available."""
    from . import appupdate
    if force:
        await asyncio.to_thread(appupdate.latest, True)
    return await asyncio.to_thread(appupdate.check, current)


@app.get("/api/device/keepalive", dependencies=[Depends(require_key)])
async def device_keepalive(brand: str = ""):
    """v0.49 Steps for this phone maker so Hoola keeps running in the background (dontkillmyapp.com, CC BY 4.0)."""
    from . import keepalive
    out = await asyncio.to_thread(keepalive.steps, brand)
    return out | {"checklist": keepalive.checklist(brand), "family": keepalive.family(brand)}


class BgHealth(BaseModel):
    brand: str = ""
    model: str = ""
    sdk: int = 0
    battery_optimized: bool = False
    background_restricted: bool = False
    standby_bucket: int = 0
    notifications: bool = True
    exits: list[dict] = []


@app.post("/api/device/bg_health", dependencies=[Depends(require_key)])
def device_bg_health(body: BgHealth, tenant: str = Depends(current_tenant)):
    """v0.56 The phone says what Android knows (battery saver, restricted, standby bucket, how the app was last stopped);
    the answer is plain-word problems + this phone family's checklist."""
    from . import keepalive
    return keepalive.save_health(tenant, body.model_dump())


@app.get("/api/device/bg_health", dependencies=[Depends(require_key)])
def device_bg_health_last(tenant: str = Depends(current_tenant)):
    from . import keepalive
    return keepalive.last_health(tenant)


# ---------------- v0.47 Public APIs (github.com/public-apis/public-apis) ----------------
@app.get("/api/publicapis", dependencies=[Depends(require_key)])
def publicapis_find(q: str = "", cat: str = "", auth: str = "any", limit: int = 30, tenant: str = Depends(current_tenant)):
    from .publicapis import service as pa
    out = pa.find(q, cat, auth if auth in ("any", "none", "key") else "any", max(1, min(limit, 60)), tenant)
    return out | {"total": len(pa.catalog()), "categories": pa.categories() if not q and not cat else []}


class PublicApiKeyIn(BaseModel):
    key: str = Field(min_length=4, max_length=500)
    place: str = "query"
    field: str = ""


@app.put("/api/publicapis/{api_id}/key", dependencies=[Depends(require_key)])
def publicapis_key(api_id: str, body: PublicApiKeyIn, tenant: str = Depends(current_tenant)):
    """The owner types an API's key in the app (sealed on the server; the avatar never sees it)."""
    from .publicapis import service as pa
    try:
        return pa.save_key(tenant, api_id, body.key, body.place, body.field)
    except pa.ApiError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/publicapis/{api_id}/key", dependencies=[Depends(require_key)])
def publicapis_key_delete(api_id: str, tenant: str = Depends(current_tenant)):
    from .publicapis import service as pa
    return pa.delete_key(tenant, api_id)


@app.get("/api/publicapis/keys", dependencies=[Depends(require_key)])
def publicapis_keys(tenant: str = Depends(current_tenant)):
    from .publicapis import service as pa
    return {"keys": pa.list_keys(tenant)}


@app.post("/api/net/outbox/{oid}", dependencies=[Depends(require_key)])
def net_outbox(oid: str, body: NetAnswerIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.outbox_decide, tenant, oid, body.action)


@app.get("/api/net/threads", dependencies=[Depends(require_key)])
def net_threads(tenant: str = Depends(current_tenant)):
    from .net import service as net
    return {"threads": _net(net.threads, tenant)}


@app.get("/api/net/threads/{tid}", dependencies=[Depends(require_key)])
def net_thread(tid: str, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.thread, tenant, tid)


class NetHandleIn(BaseModel):
    action: str = "start"       # start | stop
    goal: str = ""


@app.post("/api/net/threads/{tid}/handle", dependencies=[Depends(require_key)])
def net_handle(tid: str, body: NetHandleIn, tenant: str = Depends(current_tenant)):
    """'Tum sambhalo' on a whole conversation from the thread screen (or take it back)."""
    from .net import handle
    from .net import service as net
    t = _net(net.thread, tenant, tid)
    if body.action == "start":
        handle.start(tenant, t["id"], body.goal.strip()[:500] or t.get("goal") or "Baat ko aage badhao, mere niyam ke andar.")
    else:
        handle._set_mode(tenant, t["id"], "relay")
    return _net(net.thread, tenant, tid)


@app.post("/api/net/threads/{tid}/reply", dependencies=[Depends(require_key)])
def net_reply(tid: str, body: NetReplyIn, tenant: str = Depends(current_tenant)):
    from .net import service as net
    return _net(net.reply, tenant, tid, body.text)


class GroupIn(BaseModel):
    name: str
    emoji: str = ""
    members: list[str] = Field(default_factory=list)


class GroupPostIn(BaseModel):
    kind: str = "message"
    text: str = ""
    title: str = ""
    assign_to: str = ""
    due: str = ""
    file_id: str = ""


class GroupActIn(BaseModel):
    action: str
    who: str = ""
    mute: str = ""
    answer: str = ""


@app.get("/api/net/groups", dependencies=[Depends(require_key)])
def net_groups(tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return {"groups": _net(grp.groups, tenant)}


@app.post("/api/net/groups", dependencies=[Depends(require_key)])
def net_group_create(body: GroupIn, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.create, tenant, body.name, body.emoji, body.members)


@app.get("/api/net/groups/{gid}", dependencies=[Depends(require_key)])
def net_group(gid: str, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.detail, tenant, gid)


@app.post("/api/net/groups/{gid}/post", dependencies=[Depends(require_key)])
def net_group_post(gid: str, body: GroupPostIn, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.post, tenant, gid, body.kind, body.text, body.title, body.assign_to, body.file_id, body.due)


@app.post("/api/net/groups/{gid}/act", dependencies=[Depends(require_key)])
def net_group_act(gid: str, body: GroupActIn, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    a = body.action
    if a == "invite":
        return _net(grp.invite, tenant, gid, body.who)
    if a == "remove":
        return _net(grp.remove, tenant, gid, body.who)
    if a == "leave":
        return _net(grp.leave, tenant, gid)
    if a == "mute":
        return _net(grp.set_mute, tenant, gid, body.mute)
    if a == "answer_invite":
        return _net(grp.answer_invite, tenant, gid, body.answer or "accept")
    if a == "digest":
        return _net(grp.digest, tenant, gid, 24)
    raise HTTPException(400, "action?")


@app.post("/api/net/group-posts/{pid}/task", dependencies=[Depends(require_key)])
def net_group_task(pid: str, body: NetAnswerIn, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.task_answer, tenant, pid, body.action)


@app.post("/api/net/group-posts/{pid}/file", dependencies=[Depends(require_key)])
def net_group_file(pid: str, tenant: str = Depends(current_tenant)):
    from .net import groups as grp
    return _net(grp.take_file, tenant, pid)


class SamajIn(BaseModel):
    name: str
    topic: str = ""
    description: str = ""
    visibility: str = "open"
    emoji: str = ""


class SamajPostIn(BaseModel):
    kind: str
    data: dict = Field(default_factory=dict)


class SamajActIn(BaseModel):
    action: str
    helpful: bool = True
    mod_action: str = ""
    who: str = ""
    reason: str = ""
    mute: str = ""


class LessonActIn(BaseModel):
    action: str
    communities: list[str] = Field(default_factory=list)
    text: str = ""


@app.get("/api/net/learned", dependencies=[Depends(require_key)])
def net_learned(tenant: str = Depends(current_tenant)):
    from .net import learning as lrn
    return {"lessons": lrn.lessons(tenant), "skills": lrn.skills(tenant)}


@app.post("/api/net/learned/{lid}", dependencies=[Depends(require_key)])
def net_lesson_act(lid: str, body: LessonActIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    from .net import learning as lrn
    if body.action == "forget":
        return _net(lrn.forget, tenant, lid)
    if body.action == "share":
        cids = body.communities or [c["cid"] for c in sam.my_communities(tenant) if c["status"] == "active"]
        return _net(lrn.share, tenant, lid, cids, body.text)
    if body.action == "dont_share":
        return _net(lrn.decline_share, tenant, lid)
    raise HTTPException(400, "action?")


@app.post("/api/net/skills/{sid}", dependencies=[Depends(require_key)])
def net_skill_act(sid: str, body: NetAnswerIn, tenant: str = Depends(current_tenant)):
    from .net import learning as lrn
    return _net(lrn.set_skill, tenant, sid, body.action)


@app.get("/api/net/samaj", dependencies=[Depends(require_key)])
def net_samaj(q: str = "", tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return {"mine": sam.my_communities(tenant), "directory": sam.directory(tenant, q)}


@app.post("/api/net/samaj", dependencies=[Depends(require_key)])
def net_samaj_create(body: SamajIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return _net(sam.create, tenant, body.name, body.topic, body.description, body.visibility, body.emoji)


@app.get("/api/net/samaj/{cid}", dependencies=[Depends(require_key)])
def net_samaj_detail(cid: str, kind: str = "", tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return _net(sam.detail, tenant, cid, kind)


@app.post("/api/net/samaj/{cid}/join", dependencies=[Depends(require_key)])
def net_samaj_join(cid: str, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return _net(sam.join, tenant, cid)


@app.post("/api/net/samaj/{cid}/post", dependencies=[Depends(require_key)])
def net_samaj_post(cid: str, body: SamajPostIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    return _net(sam.post, tenant, cid, body.kind, body.data)


@app.post("/api/net/samaj/{cid}/act", dependencies=[Depends(require_key)])
def net_samaj_act(cid: str, body: SamajActIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    if body.action == "leave":
        return _net(sam.leave, tenant, cid)
    if body.action == "mute":
        return _net(sam.set_mute, tenant, cid, body.mute)
    if body.action == "moderate_member":
        return _net(sam.moderate, tenant, cid, body.mod_action, "", body.who)
    raise HTTPException(400, "action?")


@app.post("/api/net/samaj-items/{iid}", dependencies=[Depends(require_key)])
def net_samaj_item(iid: str, body: SamajActIn, tenant: str = Depends(current_tenant)):
    from .net import community as sam
    if body.action == "rate":
        return _net(sam.rate, tenant, iid, body.helpful)
    if body.action == "report":
        return _net(sam.report, tenant, iid, body.reason)
    if body.action == "install":
        return _net(sam.install_skill, tenant, iid)
    if body.action == "moderate":
        it, c = _net(sam._my_item, tenant, iid)
        return _net(sam.moderate, tenant, c.cid, body.mod_action, iid, "")
    raise HTTPException(400, "action?")


class BizIn(BaseModel):
    name: str | None = None
    category: str | None = None
    area: str | None = None
    about: str | None = None
    hours: str | None = None
    catalog: list | None = None
    public: bool | None = None
    ticket_prefix: str | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None
    auto_assign: bool | None = None
    team: list[str] | None = None


class TicketIn(BaseModel):
    status: str = ""
    note: str = ""
    to: str = ""


class ChainActIn(BaseModel):
    action: str
    to: str = ""
    note: str = ""


class ComplainIn(BaseModel):
    business: str
    text: str
    kind: str = "complain"


@app.get("/api/net/business", dependencies=[Depends(require_key)])
def net_business(tenant: str = Depends(current_tenant)):
    from .net import business as biz
    return {"business": biz.profile(tenant), "tickets": biz.tickets(tenant) if biz.profile(tenant) else [],
            "my_tickets": biz.my_tickets(tenant)}


@app.put("/api/net/business", dependencies=[Depends(require_key)])
def net_business_put(body: BizIn, tenant: str = Depends(current_tenant)):
    from .net import business as biz
    return _net(biz.setup, tenant, **{k: v for k, v in body.model_dump().items() if v is not None})


@app.post("/api/net/business/verify", dependencies=[Depends(require_key)])
def net_business_verify(body: TicketIn, udyam: str = "", tenant: str = Depends(current_tenant)):
    from .net import business as biz
    return _net(biz.request_verification, tenant, body.note, udyam)


@app.get("/api/net/businesses", dependencies=[Depends(require_key)])
def net_businesses(q: str = "", category: str = "", tenant: str = Depends(current_tenant)):
    from .net import business as biz
    return {"businesses": biz.directory(tenant, q, category)}


@app.post("/api/net/businesses/contact", dependencies=[Depends(require_key)])
def net_business_contact(body: ComplainIn, tenant: str = Depends(current_tenant)):
    from .net import business as biz
    from .net import service as net
    if body.kind == "complain":
        return _net(biz.complain, tenant, body.business, body.text)
    addr = _net(biz.contact, tenant, body.business)
    k = {"quote": "ask", "order": "order"}.get(body.kind, "ask")
    return _net(net.send, tenant, addr, k, {"text": ({"quote": "Quote chahiye: ", "order": "Order: "}.get(body.kind, "")) + body.text})


@app.post("/api/net/tickets/{number}", dependencies=[Depends(require_key)])
def net_ticket(number: str, body: TicketIn, tenant: str = Depends(current_tenant)):
    from .net import business as biz
    if body.to:
        return _net(biz.assign, tenant, number, body.to, body.note)
    return _net(biz.update_ticket, tenant, number, body.status, body.note)


@app.get("/api/net/chains", dependencies=[Depends(require_key)])
def net_chains(tenant: str = Depends(current_tenant)):
    from .net import chain as chn
    return {"chains": chn.chains(tenant)}


@app.post("/api/net/chains/{cid}", dependencies=[Depends(require_key)])
def net_chain_act(cid: str, body: ChainActIn, tenant: str = Depends(current_tenant)):
    from .net import chain as chn
    return _net(chn.act, tenant, cid, body.action, body.to, body.note)


@app.get("/api/net/operator/verifications", dependencies=[Depends(require_key)])
def net_operator_queue(tenant: str = Depends(current_tenant)):
    from .net import business as biz
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "Server operator only")
    return {"requests": biz.verification_queue()}


@app.post("/api/net/operator/verifications/{biz_tenant}", dependencies=[Depends(require_key)])
def net_operator_verify(biz_tenant: str, body: NetAnswerIn, bank_name_ok: bool = False,
                        tenant: str = Depends(current_tenant)):
    from .net import business as biz
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "Server operator only")
    return _net(biz.operator_verify, biz_tenant, body.action == "approve", bank_name_ok)


# ---------------------------------------------------------------- v0.102 Hoola Deals (buy / sell between avatars)
class DealAskIn(BaseModel):
    to: str
    items: list = Field(default_factory=list)
    mode: str = "pickup"
    need_by: str = ""
    note: str = ""
    title: str = ""
    area: str = ""


class DealActIn(BaseModel):
    lines: list | None = None
    note: str = ""
    reason: str = ""
    valid_minutes: int | None = None
    ready_by: str = ""
    place: str = ""
    minutes: int | None = None
    code: str = ""
    v: int | None = None
    mode: str = ""
    proof: dict | None = None
    # v0.106 money / dispute
    amount: float | None = None
    utr: str = ""
    collect: dict | None = None
    pay: str = ""
    resolution: str = ""
    accept: bool = True
    yes: bool = False
    items: list | None = None
    # v0.113 bookings / job card
    slot: str = ""
    address: str = ""
    slots: list | None = None
    estimate: dict | None = None
    eta_minutes: int | None = None
    summary: str = ""
    warranty_days: int | None = None
    covers: str = ""
    purpose: str = "resched"
    ids_yes: list | None = None
    ids_no: list | None = None


class StockIn(BaseModel):
    items: list = Field(default_factory=list)


@app.get("/api/net/deals", dependencies=[Depends(require_key)])
def net_deals(state: str = "", role: str = "", tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return {"deals": dl.deals(tenant, state, role)}


@app.post("/api/net/deals", dependencies=[Depends(require_key)])
def net_deal_ask(body: DealAskIn, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return _net(dl.ask, tenant, body.to, body.items, body.mode, body.need_by, body.note, body.title, body.area)


@app.get("/api/net/deals/catalog", dependencies=[Depends(require_key)])
def net_deal_catalog(to: str, tenant: str = Depends(current_tenant)):
    """v0.105 a seller's price list, asked through her avatar (only what that seller shares)."""
    from .net import deal as dl
    return _net(dl.catalog_of, tenant, to)


@app.get("/api/net/deals/{deal_id}", dependencies=[Depends(require_key)])
def net_deal_get(deal_id: str, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return _net(dl.show, tenant, deal_id)


@app.post("/api/net/deals/{deal_id}/{action}", dependencies=[Depends(require_key)])
def net_deal_act(deal_id: str, action: str, body: DealActIn, tenant: str = Depends(current_tenant)):
    """Her taps on a deal card. `confirm` is the only way an order is placed (fingerprint-signed once a phone is set up)."""
    from .net import deal as dl
    if action == "confirm":
        _fingerprint(tenant, "deal", deal_id, body.proof)
        return _net(dl.confirm, tenant, deal_id, body.v, body.mode, by_tap=True, pay=body.pay, slot=body.slot,
                    address=body.address)
    if action == "send_quote":
        return _net(dl.send_quote, tenant, deal_id, body.lines, body.note, body.valid_minutes, slots=body.slots,
                    estimate=body.estimate)
    if action == "accept":
        return _net(dl.accept, tenant, deal_id, body.ready_by, body.note)
    if action == "reject":
        return _net(dl.reject, tenant, deal_id, body.reason or body.note)
    if action == "packing":
        return _net(dl.packing, tenant, deal_id, body.note)
    if action == "ready":
        return _net(dl.mark_ready, tenant, deal_id, body.place, body.minutes, body.note)
    if action == "handed_over":
        return _net(dl.handed_over, tenant, deal_id, body.code, body.note, body.collect)
    if action == "cancel":
        return _net(dl.cancel, tenant, deal_id, body.reason or body.note)
    from .net import dealpay as dp                       # v0.106 money, cancel requests, the check, disputes
    from .net import mandate as md                       # v0.112 "is baar rok do" on a standing-order run
    from .net import job as jb                           # v0.113 the service job card
    acts = {
        "pay_link": lambda: dp.pay_link(tenant, deal_id),
        "trust_payee": lambda: dp.trust_payee(tenant, deal_id),
        "paid": lambda: dp.claim_paid(tenant, deal_id, body.utr),
        "pay_request": lambda: dp.request_payment(tenant, deal_id, body.amount),
        "received": lambda: dp.received(tenant, deal_id, body.amount, body.mode or "upi", body.utr),
        "refund": lambda: dp.refund(tenant, deal_id, body.amount, body.utr),
        "ok": lambda: dp.all_ok(tenant, deal_id),
        "dispute": lambda: dp.dispute(tenant, deal_id, body.reason or "other", body.items, body.note),
        "resolve": lambda: dp.resolve(tenant, deal_id, body.resolution, body.amount, body.note),
        "dispute_close": lambda: dp.dispute_close(tenant, deal_id, body.accept, body.note),
        "cancel_answer": lambda: dp.cancel_answer(tenant, deal_id, body.yes, body.note),
        "standing_hold": lambda: md.hold_once(tenant, deal_id),
        # v0.113 job card (approve / pick_slot = her tap here)
        "on_the_way": lambda: jb.on_the_way(tenant, deal_id, body.eta_minutes, body.note),
        "arrived": lambda: jb.arrived(tenant, deal_id, body.note),
        "estimate": lambda: jb.estimate(tenant, deal_id, body.lines or body.items),
        "approve": lambda: jb.approve(tenant, deal_id, body.ids_yes, body.ids_no, by_tap=True),
        "done": lambda: jb.done(tenant, deal_id, body.summary or body.note, body.warranty_days, body.covers),
        "offer_slots": lambda: jb.offer_slots(tenant, deal_id, body.purpose, body.slots),
        "pick_slot": lambda: jb.pick_slot(tenant, deal_id, body.slot, by_tap=True),
        "resched": lambda: jb.ask_resched(tenant, deal_id, body.note),
        "warranty": lambda: jb.claim(tenant, deal_id, body.note),
        "warranty_done": lambda: jb.warranty_done(tenant, deal_id, body.summary or body.note),
    }
    if action in acts:
        return _net(acts[action])
    raise HTTPException(400, "action: confirm, send_quote, accept, reject, packing, ready, handed_over, cancel, "
                             + ", ".join(acts))


@app.post("/api/net/deals/{deal_id}/photo", dependencies=[Depends(require_key)])
async def net_deal_photo(deal_id: str, file: UploadFile = File(...), stage: str = Form("after"),
                         tenant: str = Depends(current_tenant)):
    """v0.113 a proof photo of the work (camera / gallery) -> kept for the job + sent to the customer's Hoola."""
    from .net import job as jb
    data = await file.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "The photo is bigger than 12 MB.")
    return _net(jb.add_photo, tenant, deal_id, data, file.filename or "photo.jpg", stage)


@app.get("/api/net/deals/{deal_id}/photos/{pid}", dependencies=[Depends(require_key)])
def net_deal_photo_get(deal_id: str, pid: str, tenant: str = Depends(current_tenant)):
    from .net import job as jb
    return FileResponse(_net(jb.photo_file, tenant, deal_id, pid), media_type="image/jpeg")


class BookIn(BaseModel):
    to: str
    what: str
    items: list = Field(default_factory=list)
    when: str = ""
    area: str = ""
    note: str = ""
    at: str = ""


@app.post("/api/net/bookings", dependencies=[Depends(require_key)])
def net_book(body: BookIn, tenant: str = Depends(current_tenant)):
    """v0.113 ask a service / appointment (only the work, area and preferred time go; the address only at booking)."""
    from .net import deal as dl
    return _net(dl.ask, tenant, body.to, body.items, "pickup", "", body.note, "", body.area,
                service={"what": body.what, "when": body.when, "area": body.area, "at": body.at})


@app.get("/api/net/bookings", dependencies=[Depends(require_key)])
def net_bookings(role: str = "", tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return {"bookings": [d for d in dl.deals(tenant, "", role, 120) if d.get("service")]}


@app.get("/api/net/service_rules", dependencies=[Depends(require_key)])
def net_service_rules(tenant: str = Depends(current_tenant)):
    from .net import booking as bk
    return bk.rules_view(tenant) | {"free_slots": bk.free_slots(tenant)}


@app.put("/api/net/service_rules", dependencies=[Depends(require_key)])
def net_service_rules_put(body: dict, tenant: str = Depends(current_tenant)):
    from .net import booking as bk
    allowed = ("days", "open_at", "close_at", "slot_minutes", "capacity", "lead_minutes", "horizon_days", "visit_fee",
               "visit_gst", "visit_adjust", "at", "warranty_days", "prefix", "closed_on")
    return _net(bk.set_rules, tenant, **{k: body[k] for k in allowed if k in body})


@app.get("/api/net/deals/{deal_id}/receipt.pdf", dependencies=[Depends(require_key)])
def net_deal_receipt(deal_id: str, tenant: str = Depends(current_tenant)):
    """v0.106 the bill + receipts of one deal, made from this side's own record."""
    from .net import dealpay as dp
    pdf = _net(dp.receipt_pdf, tenant, deal_id)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="hoola-{deal_id}.pdf"'})


class KhataIn(BaseModel):
    to: str
    limit: float | None = None
    days: int | None = None
    status: str = "active"
    amount: float | None = None
    mode: str = "upi"
    utr: str = ""


# ---------------------------------------------------------------- v0.112 compare, trust, standing orders, offers
class RfqIn(BaseModel):
    to: list = Field(default_factory=list)
    items: list = Field(default_factory=list)
    mode: str = "pickup"
    need_by: str = ""
    note: str = ""
    title: str = ""
    window_minutes: int | None = None
    on: bool = True


@app.post("/api/net/rfqs", dependencies=[Depends(require_key)])
def net_rfq_start(body: RfqIn, tenant: str = Depends(current_tenant)):
    from .net import rfq as rq
    return _net(rq.start, tenant, body.to, body.items, body.mode, body.need_by, body.note, body.title, body.window_minutes)


@app.get("/api/net/rfqs", dependencies=[Depends(require_key)])
def net_rfqs(all: bool = False, tenant: str = Depends(current_tenant)):
    from .net import rfq as rq
    return {"compares": rq.rfqs(tenant, not all)}


@app.get("/api/net/rfqs/{rfq_id}", dependencies=[Depends(require_key)])
def net_rfq(rfq_id: str, tenant: str = Depends(current_tenant)):
    from .net import rfq as rq
    return _net(rq.show, tenant, rfq_id)


@app.post("/api/net/rfqs/{rfq_id}/{action}", dependencies=[Depends(require_key)])
def net_rfq_act(rfq_id: str, action: str, body: RfqIn, tenant: str = Depends(current_tenant)):
    from .net import rfq as rq
    if action == "split":
        return _net(rq.set_split, tenant, rfq_id, body.on)
    if action == "close":
        return _net(rq.close, tenant, rfq_id)
    raise HTTPException(400, "action: split, close")


class TrustIn(BaseModel):
    to: str
    level: str = "trusted"
    reason: str = "spam"
    kind: str = ""


@app.get("/api/net/trust", dependencies=[Depends(require_key)])
def net_trust(to: str, tenant: str = Depends(current_tenant)):
    from .net import service as net
    from .net import trust as tr
    peer = _net(net.resolve, tenant, to) if not to.startswith("hl_") else to
    return tr.tier(tenant, peer)


@app.put("/api/net/trust", dependencies=[Depends(require_key)])
def net_trust_put(body: TrustIn, tenant: str = Depends(current_tenant)):
    from .net import trust as tr
    return _net(tr.set_trust, tenant, body.to, body.level)


@app.post("/api/net/trust/report", dependencies=[Depends(require_key)])
def net_trust_report(body: TrustIn, tenant: str = Depends(current_tenant)):
    from .net import trust as tr
    return _net(tr.report, tenant, body.to, body.reason, body.kind)


class MandateIn(BaseModel):
    to: str = ""
    items: list = Field(default_factory=list)
    days: list | str = Field(default_factory=list)
    at: str = "09:00"
    max_total: float | None = None
    until: str = ""
    tolerance_pct: float | None = None
    pay: str = ""
    hold_minutes: int | None = None
    title: str = ""
    mode: str = "pickup"
    proof: dict | None = None


@app.get("/api/net/mandates", dependencies=[Depends(require_key)])
def net_mandates(tenant: str = Depends(current_tenant)):
    from .net import mandate as md
    return {"standing_orders": md.mandates(tenant)}


@app.post("/api/net/mandates", dependencies=[Depends(require_key)])
def net_mandate_create(body: MandateIn, tenant: str = Depends(current_tenant)):
    from .net import mandate as md
    return _net(md.create, tenant, body.to, body.items, body.days, body.at, body.max_total, body.until, body.tolerance_pct,
                body.pay, body.hold_minutes, body.title, body.mode)


@app.post("/api/net/mandates/{mid}/{action}", dependencies=[Depends(require_key)])
def net_mandate_act(mid: str, action: str, body: MandateIn, tenant: str = Depends(current_tenant)):
    """`sign` / `resume` = HER tap that turns the rule on (fingerprint-signed once a phone is set up)."""
    from .net import mandate as md
    if action in ("sign", "resume"):
        _fingerprint(tenant, "mandate", mid, body.proof)
        return _net(md.sign, tenant, mid, by_tap=True)
    if action in ("pause", "stop"):
        return _net(md.set_state, tenant, mid, action)
    if action == "run":
        return _net(md.run_now, tenant, mid)
    raise HTTPException(400, "action: sign, pause, resume, stop, run")


class PromoIn(BaseModel):
    to: str = ""
    title: str = ""
    text: str = ""
    items: list | None = None
    valid_days: int = 7


@app.get("/api/net/promos", dependencies=[Depends(require_key)])
def net_promos(tenant: str = Depends(current_tenant)):
    from .net import promo as pr
    return {"offers": pr.inbox(tenant), "opted_in": pr.my_optins(tenant)}


@app.get("/api/net/promos/audience", dependencies=[Depends(require_key)])
def net_promo_audience(tenant: str = Depends(current_tenant)):
    from .net import promo as pr
    return pr.audience(tenant)


@app.post("/api/net/promos/{action}", dependencies=[Depends(require_key)])
def net_promo_act(action: str, body: PromoIn, tenant: str = Depends(current_tenant)):
    """optin / optout (the buyer), preview / send (the seller; send = her tap)."""
    from .net import promo as pr
    if action == "optin":
        return _net(pr.opt_in, tenant, body.to)
    if action == "optout":
        return _net(pr.opt_out, tenant, body.to)
    if action == "preview":
        return _net(pr.preview, tenant, body.title, body.text, body.items, body.valid_days)
    if action == "send":
        return _net(pr.send_offer, tenant, body.title, body.text, body.items, body.valid_days, by_tap=True)
    raise HTTPException(400, "action: optin, optout, preview, send")


@app.post("/api/net/promos/{promo_id}/{action}", dependencies=[Depends(require_key)])
def net_promo_item(promo_id: str, action: str, body: PromoIn, tenant: str = Depends(current_tenant)):
    from .net import promo as pr
    if action == "order":
        return _net(pr.order_from, tenant, promo_id, body.items)
    if action == "dismiss":
        return _net(pr.dismiss, tenant, promo_id)
    raise HTTPException(400, "action: order, dismiss")


class DostiIn(BaseModel):
    on: bool | None = None
    who: str | None = None
    chosen: list[str] | None = None
    share_work: bool | None = None
    share_skills: bool | None = None
    share_videos: str | None = None
    daily_max: int | None = None
    to: str = ""
    text: str = ""
    thread_id: str = ""
    share: bool = False
    what: str = ""
    why: str = ""
    action: str = ""
    file_id: str = ""
    status: str | None = None
    shared: bool | None = None
    title: str | None = None
    summary: str | None = None
    learned: str | None = None
    category: str = "other"


@app.get("/api/net/dosti", dependencies=[Depends(require_key)])
def net_dosti(tenant: str = Depends(current_tenant)):
    """v0.160 Dosti: her setting, the work diary, friends' chats, what friends shared, doc requests."""
    from .net import dosti as ds
    _net(ds.sync, tenant)
    return ds.overview(tenant)


@app.put("/api/net/dosti", dependencies=[Depends(require_key)])
def net_dosti_set(body: DostiIn, tenant: str = Depends(current_tenant)):
    from .net import dosti as ds
    return _net(ds.set_settings, tenant, on=body.on, who=body.who, chosen=body.chosen, share_work=body.share_work,
                share_skills=body.share_skills, share_videos=body.share_videos, daily_max=body.daily_max)


@app.post("/api/net/dosti/{action}", dependencies=[Depends(require_key)])
def net_dosti_act(action: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    """talk (to | thread_id, text, share) / doc_ask (to, what, why) / diary (add: title, summary, learned, category) /
    share_now / sync."""
    from .net import dosti as ds
    if action == "talk":
        return _net(ds.talk, tenant, body.to, body.text, body.thread_id, body.share)
    if action == "doc_ask":
        return _net(ds.ask_doc, tenant, body.to, body.what, body.why)
    if action == "diary":
        return _net(ds.add_experience, tenant, body.title or "", body.summary or "", body.learned or "", body.category)
    if action == "share_now":
        return {"friends_told": _net(ds.share_learnings, tenant, True)}
    if action == "sync":
        return {"new": _net(ds.sync, tenant, 10)}
    raise HTTPException(400, "action: talk, doc_ask, diary, share_now, sync")


@app.post("/api/net/dosti/threads/{thread_id}/{action}", dependencies=[Depends(require_key)])
def net_dosti_thread(thread_id: str, action: str, tenant: str = Depends(current_tenant)):
    from .net import dosti as ds
    if action not in ("pause", "resume"):
        raise HTTPException(400, "action: pause, resume")
    return _net(ds.pause, tenant, thread_id, action == "pause")


@app.patch("/api/net/dosti/diary/{exp_id}", dependencies=[Depends(require_key)])
def net_dosti_diary(exp_id: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    from .net import dosti as ds
    return _net(ds.update_experience, tenant, exp_id, status=body.status, shared=body.shared, title=body.title,
                summary=body.summary, learned=body.learned)


@app.post("/api/net/dosti/diary/{exp_id}/{action}", dependencies=[Depends(require_key)])
def net_dosti_video(exp_id: str, action: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    """video = make the explainer video of this skill; send_video = to a friend (this tap is her consent)."""
    from .net import dosti as ds
    if action == "video":
        return _net(ds.make_video, tenant, exp_id)
    if action == "send_video":
        return _net(ds.send_video, tenant, exp_id, body.to, by_tap=True)
    raise HTTPException(400, "action: video, send_video")


@app.post("/api/net/dosti/docs/{ask_id}", dependencies=[Depends(require_key)])
def net_dosti_doc(ask_id: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    """Her tap on a document request: send (file_id) or decline. The only way a requested document goes out."""
    from .net import dosti as ds
    return _net(ds.doc_answer, tenant, ask_id, body.action, body.file_id, by_tap=True)


@app.post("/api/net/dosti/items/{item_id}", dependencies=[Depends(require_key)])
def net_dosti_item(item_id: str, body: DostiIn, tenant: str = Depends(current_tenant)):
    """Her yes / no on a skill a friend's avatar shared (learn | decline)."""
    from .net import dosti as ds
    return _net(ds.item_answer, tenant, item_id, body.action, by_tap=True)


@app.get("/api/net/khata", dependencies=[Depends(require_key)])
def net_khata(tenant: str = Depends(current_tenant)):
    from .net import khata as kh
    return kh.book(tenant)


@app.post("/api/net/khata/{action}", dependencies=[Depends(require_key)])
def net_khata_act(action: str, body: KhataIn, tenant: str = Depends(current_tenant)):
    from .net import khata as kh
    acts = {
        "open": lambda: kh.open_account(tenant, body.to, body.limit if body.limit is not None else 0, body.days or 15,
                                        body.status),
        "request": lambda: kh.request(tenant, body.to, body.amount),
        "received": lambda: kh.received(tenant, body.to, body.amount, body.mode, body.utr),
        "pay_link": lambda: kh.pay_link(tenant, body.to),
        "trust_payee": lambda: kh.trust_payee(tenant, body.to),
        "paid": lambda: kh.claim_paid(tenant, body.to, body.utr),
    }
    if action not in acts:
        raise HTTPException(400, "action: " + ", ".join(acts))
    return _net(acts[action])


@app.get("/api/net/stock", dependencies=[Depends(require_key)])
def net_stock(q: str = "", tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return {"stock": dl.stock(tenant, q), "rules": dl.rules_view(tenant)}


@app.put("/api/net/stock", dependencies=[Depends(require_key)])
def net_stock_put(body: StockIn, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return _net(dl.set_stock, tenant, body.items)


@app.delete("/api/net/stock/{item}", dependencies=[Depends(require_key)])
def net_stock_delete(item: str, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return _net(dl.remove_stock, tenant, item)


@app.post("/api/net/stock/import", dependencies=[Depends(require_key)])
async def net_stock_import(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "The file is bigger than 10 MB.")
    return _net(dl.import_stock, tenant, file.filename or "stock.csv", data)


class PickActIn(BaseModel):
    short: list | None = None
    code: str = ""
    note: str = ""
    collect: dict | None = None


@app.get("/api/net/picks", dependencies=[Depends(require_key)])
def net_picks(all: bool = False, tenant: str = Depends(current_tenant)):
    from .net import pick as pk
    return {"picks": pk.picks(tenant, not all)}


@app.post("/api/net/picks/{pick_id}/{action}", dependencies=[Depends(require_key)])
def net_pick_act(pick_id: str, action: str, body: PickActIn, tenant: str = Depends(current_tenant)):
    from .net import pick as pk
    if action in ("packing", "packed", "short"):
        return _net(pk.mark, tenant, pick_id, action, body.short, body.note)
    if action == "handover":
        return _net(pk.handover, tenant, pick_id, body.code, body.collect)
    raise HTTPException(400, "action: packing, packed, short, handover")


@app.get("/api/net/deal_rules", dependencies=[Depends(require_key)])
def net_deal_rules(tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    return dl.rules_view(tenant)


@app.put("/api/net/deal_rules", dependencies=[Depends(require_key)])
def net_deal_rules_put(body: dict, tenant: str = Depends(current_tenant)):
    from .net import deal as dl
    allowed = ("auto_quote", "auto_quote_max", "auto_accept", "auto_accept_max", "valid_minutes", "place", "pickup_minutes",
               "prefix", "trusted", "catalog", "show_stock", "auto_ready", "packers", "pay_before", "counter_ok", "khata",
               "cancel_minutes", "dispute_hours", "upi_id", "payee_name", "auto_accept_who")
    return _net(dl.set_rules, tenant, **{k: body[k] for k in allowed if k in body})


@app.post("/hooks/hoola/{handle}/ticket")
async def net_ticket_webhook(handle: str, request: Request):
    """The business's own system (FNW Flow, a CRM...) updates a Hoola ticket. Body {ticket, status, note}, signed:
    X-Hoola-Signature: sha256=<HMAC-SHA256(secret, body)>."""
    from .net import business as biz
    from .net import identity as idn
    row = idn.by_handle(handle)
    if row is None:
        raise HTTPException(404, "not found")
    raw = await request.body()
    try:
        return biz.webhook_in(row.tenant_id, raw, request.headers.get("x-hoola-signature", ""))
    except Exception as e:
        raise HTTPException(400, str(e)[:120])


# ---------------- Hoola federation (other Hoola servers) and A2A discovery ----------------
@app.get("/.well-known/hoola.json")
def hoola_server_card():
    from .net import federation as fed
    return fed.server_card()


@app.get("/.well-known/agent-card.json")
@app.get("/.well-known/agent.json")
def hoola_agent_card():
    from .net import a2a
    return a2a.agent_card()


@app.post("/hoola/inbox")
async def hoola_inbox(request: Request):
    from .net import federation as fed
    raw = await request.body()
    if len(raw) > 512 * 1024:
        raise HTTPException(413, "too big")
    try:
        return await asyncio.to_thread(fed.inbox, dict(request.headers), raw)
    except fed.FedError as e:
        raise HTTPException(401, str(e))


@app.get("/hoola/lookup")
def hoola_lookup(handle: str):
    from .net import federation as fed
    c = fed.public_lookup(handle)
    if c is None:
        raise HTTPException(404, "not found")
    return c


@app.get("/hoola/share/{sid}")
def hoola_share(sid: str, request: Request):
    from urllib.parse import quote
    from .net import federation as fed
    from .net.service import NetError
    try:
        name, mime, data, sha = fed.serve_share(dict(request.headers), sid, request.query_params.get("for", ""))
    except (fed.FedError, NetError) as e:
        raise HTTPException(403, str(e))
    return Response(content=data, media_type=mime or "application/octet-stream",
                    headers={"X-Hoola-Name": quote(name), "X-Hoola-SHA256": sha})


async def _a2a_call(request: Request, v1: bool):
    from .net import a2a
    if not get_settings().a2a_inbound:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32004, "message": "A2A is off on this server"}})
    raw = await request.body()
    if len(raw) > 256 * 1024:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Request too large"}})
    try:
        body = json.loads(raw.decode() or "null")
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
    ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "")
    out = await asyncio.to_thread(a2a.rpc, body, dict(request.headers), ip, v1,
                                  request.query_params.get("A2A-Version", ""))
    return JSONResponse(out, headers={"A2A-Version": "1.0" if v1 else "0.3"})


@app.post("/a2a")
async def hoola_a2a(request: Request):
    """A2A 0.3 names (message/send, tasks/get, tasks/cancel) and 1.0 names both work here (v0.116)."""
    return await _a2a_call(request, False)


@app.post("/a2a/v1")
async def hoola_a2a_v1(request: Request):
    """v0.116 A2A 1.0 JSON-RPC (SendMessage, GetTask, ListTasks, CancelTask)."""
    return await _a2a_call(request, True)


@app.get("/a2a/help", response_class=PlainTextResponse)
def hoola_a2a_help():
    from .net import a2a
    return a2a.help_text()


# ---------------- v0.116 A2A 1.0 (her side), hand-offs (AA, ABDM, DigiLocker), ONDC listing ----------------
def _ho(fn, *a, **kw):
    from .handoff.aa import HandoffError
    from .net import service as net
    try:
        return fn(*a, **kw)
    except (net.NetError, HandoffError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/a2a", dependencies=[Depends(require_key)])
def a2a_home(tenant: str = Depends(current_tenant)):
    from .net import a2a
    from .net import federation as fed
    return {"mode": a2a.mode(tenant), "tasks": a2a.tasks(tenant), "outs": a2a.outs(tenant),
            "card": fed.my_base() + "/.well-known/agent-card.json", "endpoint": fed.my_base() + "/a2a/v1"}


@app.put("/api/a2a/mode", dependencies=[Depends(require_key)])
def a2a_mode(body: dict, tenant: str = Depends(current_tenant)):
    from .net import a2a
    return _ho(a2a.set_mode, tenant, str(body.get("mode") or ""))


@app.get("/api/a2a/tasks/{tid}", dependencies=[Depends(require_key)])
def a2a_task(tid: str, tenant: str = Depends(current_tenant)):
    from .net import a2a
    return _ho(a2a.show, tenant, tid)


@app.post("/api/a2a/tasks/{tid}/{action}", dependencies=[Depends(require_key)])
def a2a_task_act(tid: str, action: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """Her taps on an outside agent's request: reply / quote / accept / reject / ready / handed_over / cancel."""
    from .net import a2a
    b = body or {}
    acts = {"reply": lambda: a2a.reply(tenant, tid, str(b.get("text") or ""), by_tap=True),
            "draft_reply": lambda: a2a.prepare_reply(tenant, tid, str(b.get("text") or "")),
            "quote": lambda: a2a.send_quote(tenant, tid, b.get("lines"), str(b.get("note") or ""), b.get("valid_minutes")),
            "accept": lambda: a2a.accept(tenant, tid, str(b.get("note") or "")),
            "reject": lambda: a2a.reject(tenant, tid, str(b.get("reason") or "")),
            "ready": lambda: a2a.mark_ready(tenant, tid, str(b.get("place") or "")),
            "handed_over": lambda: a2a.handed_over(tenant, tid, str(b.get("code") or "")),
            "cancel": lambda: a2a.cancel_order(tenant, tid, str(b.get("reason") or ""))}
    if action not in acts:
        raise HTTPException(404, "action")
    return _ho(acts[action])


@app.post("/api/a2a/discover", dependencies=[Depends(require_key)])
def a2a_discover(body: dict, tenant: str = Depends(current_tenant)):
    from .net import a2a
    return _ho(a2a.discover, str(body.get("url") or ""))


@app.post("/api/a2a/out", dependencies=[Depends(require_key)])
def a2a_out_new(body: dict, tenant: str = Depends(current_tenant)):
    from .net import a2a
    return _ho(a2a.draft, tenant, str(body.get("url") or ""), str(body.get("text") or ""), body.get("data"),
               str(body.get("task_of") or ""))


@app.post("/api/a2a/out/{oid}/{action}", dependencies=[Depends(require_key)])
def a2a_out_act(oid: str, action: str, tenant: str = Depends(current_tenant)):
    """'Bhejo' (her tap) / drop / poll a message to an outside agent."""
    from .net import a2a
    if action == "send":
        return _ho(a2a.send, tenant, oid, by_tap=True)
    if action == "drop":
        return _ho(a2a.drop, tenant, oid)
    if action == "poll":
        return _ho(a2a.poll, tenant, oid)
    raise HTTPException(404, "action")


@app.get("/api/handoff", dependencies=[Depends(require_key)])
def handoff_home(tenant: str = Depends(current_tenant)):
    from .handoff import aa, abdm, digilocker, ondc
    return {"aa": aa.consents(tenant), "aa_apps": aa.apps(), "abdm": abdm.consents(tenant), "abdm_topics": list(abdm.HELP),
            "digilocker": digilocker.status(tenant), "ondc": ondc.readiness(tenant)}


@app.post("/api/handoff/aa/review", dependencies=[Depends(require_key)])
def handoff_aa_review(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import aa
    keys = ("requester", "for_what", "purpose_code", "fi_types", "data_from", "data_to", "months", "fetch_type", "frequency",
            "consent_mode", "data_life", "expiry", "aa_app", "text")
    return _ho(aa.review, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/handoff/aa/{cid}/mark", dependencies=[Depends(require_key)])
def handoff_aa_mark(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import aa
    return _ho(aa.mark, tenant, cid, str(body.get("status") or ""), body.get("revoke_after_days"))


@app.delete("/api/handoff/aa/{cid}", dependencies=[Depends(require_key)])
def handoff_aa_forget(cid: str, tenant: str = Depends(current_tenant)):
    from .handoff import aa
    return _ho(aa.forget, tenant, cid)


@app.post("/api/handoff/abdm/review", dependencies=[Depends(require_key)])
def handoff_abdm_review(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import abdm
    keys = ("requester", "purpose", "hi_types", "data_from", "data_to", "expiry", "for_whom", "visit")
    return _ho(abdm.review, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/handoff/abdm/{cid}/mark", dependencies=[Depends(require_key)])
def handoff_abdm_mark(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import abdm
    return _ho(abdm.mark, tenant, cid, str(body.get("status") or ""), body.get("revoke_after_days"))


@app.delete("/api/handoff/abdm/{cid}", dependencies=[Depends(require_key)])
def handoff_abdm_forget(cid: str, tenant: str = Depends(current_tenant)):
    from .handoff import abdm
    return _ho(abdm.forget, tenant, cid)


@app.get("/api/handoff/abdm/help", dependencies=[Depends(require_key)])
def handoff_abdm_help(topic: str = "", tenant: str = Depends(current_tenant)):
    from .handoff import abdm
    return abdm.explain(topic)


@app.get("/api/digilocker", dependencies=[Depends(require_key)])
def digilocker_status(tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return digilocker.status(tenant)


@app.post("/api/digilocker/start", dependencies=[Depends(require_key)])
def digilocker_start(body: dict | None = None, tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return _ho(digilocker.start, tenant, str((body or {}).get("doctype") or ""))


@app.get("/api/digilocker/callback", response_class=HTMLResponse)
def digilocker_callback(code: str = "", state: str = "", error: str = ""):
    """DigiLocker sends her back here after she signed in on its own page (public: the random state is the key)."""
    import html as _h
    from .handoff import digilocker
    from .handoff.aa import HandoffError
    try:
        res = digilocker.callback(code, state, error)
        msg = res["say"]
    except HandoffError as e:
        msg = str(e)
    return HTMLResponse("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                        "<title>Hoola · DigiLocker</title><body style='font-family:sans-serif;padding:24px'>"
                        f"<h3>Hoola</h3><p>{_h.escape(msg)}</p><p><a href='santosh://home'>Hoola kholiye</a></p>",
                        headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"})


@app.get("/api/digilocker/issued", dependencies=[Depends(require_key)])
def digilocker_issued(tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return {"issued": _ho(digilocker.issued, tenant)}


@app.post("/api/digilocker/fetch", dependencies=[Depends(require_key)])
def digilocker_fetch(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return _ho(digilocker.fetch, tenant, str(body.get("uri") or ""))


@app.delete("/api/digilocker", dependencies=[Depends(require_key)])
def digilocker_disconnect(tenant: str = Depends(current_tenant)):
    from .handoff import digilocker
    return _ho(digilocker.disconnect, tenant)


@app.get("/api/ondc", dependencies=[Depends(require_key)])
def ondc_home(tenant: str = Depends(current_tenant)):
    from .handoff import ondc
    return ondc.readiness(tenant) | {"domains": ondc.DOMAINS}


@app.put("/api/ondc", dependencies=[Depends(require_key)])
def ondc_setup(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import ondc
    keys = ("on", "domain", "seller_app", "store_name", "gstin", "fssai", "care", "pincodes", "radius_km", "ship_minutes",
            "returnable", "return_days", "cancellable", "cod", "fulfilment")
    return _ho(ondc.setup, tenant, **{k: body[k] for k in keys if k in body})


@app.put("/api/ondc/items", dependencies=[Depends(require_key)])
def ondc_item(body: dict, tenant: str = Depends(current_tenant)):
    from .handoff import ondc
    return _ho(ondc.set_item, tenant, str(body.get("item") or ""), **{k: body[k] for k in ondc.ITEM_KEYS if k in body})


@app.post("/api/ondc/export", dependencies=[Depends(require_key)])
def ondc_export(tenant: str = Depends(current_tenant)):
    from .events import bus
    from .handoff import ondc
    from .net.service import home_conv
    res = _ho(ondc.export, tenant)
    bus.publish(home_conv(tenant), "pc_file", {**res["file"], "source": "ondc"})
    return res


@app.get("/c/{code}", response_class=HTMLResponse)
def net_invite_page(code: str):
    """What a phone camera opens from a Hoola QR: who is inviting, and a button into the Hoola app."""
    import html as _h
    from .net import identity as idn
    from .net.models import Invite
    from .db import session as _s
    with _s() as s:
        inv = s.get(Invite, code)
        owner = inv.tenant_id if inv else None
    if not owner:
        body = "<h2>Yeh invite purana ho gaya</h2><p>Naya QR ya link maangiye.</p>"
    else:
        c = idn.my_card(owner)
        who = _h.escape(idn.label(c))
        deep = f"santosh://connect?c={_h.escape(code)}"
        body = (f"<h2>{who}</h2><p>@{_h.escape(c['handle'])} aapke Hoola se judna chahte hain.</p>"
                f"<p><a class=b href='{deep}'>Hoola app mein kholiye</a></p>"
                "<p class=s>Hoola nahi hai? <a href='https://github.com/fibernetworkworks-droid/santosh-app/releases/latest'>"
                "Yahan se download kijiye</a>, phir yeh link dobara kholiye.</p>")
    return HTMLResponse("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                        "<title>Hoola</title><style>body{font-family:system-ui,sans-serif;background:#0B0A1A;color:#F4F2FF;"
                        "max-width:520px;margin:auto;padding:32px 20px}a{color:#FFB15C}.b{display:inline-block;padding:14px 22px;"
                        "background:#FFB15C;color:#1B1030;border-radius:14px;text-decoration:none;font-weight:700}.s{color:#B9B3DA}"
                        f"</style><h1>Hoola</h1>{body}")


# ---------------- Awaaz Pehchaan: who is talking (owner / family), voice lock ----------------
class VoiceIdModeIn(BaseModel):
    mode: str


class VoiceIdEnrolIn(BaseModel):
    name: str
    relation: str
    gender: str | None = None
    level: str | None = None


class VoiceIdMemberIn(BaseModel):
    level: str | None = None
    name: str | None = None


def _vid(fn, *a, **kw):
    from .voiceid import service as vs
    try:
        return fn(*a, **kw)
    except vs.VoiceIdError as e:
        raise HTTPException(400, str(e))


@app.get("/api/voiceid", dependencies=[Depends(require_key)])
def voiceid_get(tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    return vs.overview(tenant)


@app.put("/api/voiceid/mode", dependencies=[Depends(require_key)])
def voiceid_mode(body: VoiceIdModeIn, tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    return {"mode": _vid(vs.set_mode, tenant, body.mode)}


@app.post("/api/voiceid/enrol", dependencies=[Depends(require_key)])
def voiceid_enrol_start(body: VoiceIdEnrolIn, tenant: str = Depends(current_tenant)):
    """A one-time script with a code; the person reads it aloud themselves in the app."""
    from .voiceid import service as vs
    return _vid(vs.start_enrol, tenant, body.name, body.relation, body.gender, body.level)


@app.post("/api/voiceid/enrol/{enrol_id}", dependencies=[Depends(require_key)])
async def voiceid_enrol_finish(enrol_id: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    data = await file.read(12 * 1024 * 1024 + 1)
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "The recording is too big.")
    return await asyncio.to_thread(_vid, vs.finish_enrol, tenant, enrol_id, data)


@app.patch("/api/voiceid/members/{member_id}", dependencies=[Depends(require_key)])
def voiceid_member_update(member_id: str, body: VoiceIdMemberIn, tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    return _vid(vs.update, tenant, member_id, body.level, body.name)


@app.delete("/api/voiceid/members/{member_id}", dependencies=[Depends(require_key)])
def voiceid_member_delete(member_id: str, tenant: str = Depends(current_tenant)):
    from .voiceid import service as vs
    if not vs.delete(tenant, member_id):
        raise HTTPException(404, "This person was not found.")
    return {"deleted": True}


# ---------------- Hoola avatar: name, gender, voice, Mere Niyam ----------------
class AvatarIn(BaseModel):
    name: str | None = None
    gender: str | None = None
    voice: str | None = None
    setup_done: bool | None = None
    rules: dict | None = None
    look: str | None = None


class RulesTextIn(BaseModel):
    text: str


@app.get("/api/avatar", dependencies=[Depends(require_key)])
def avatar_get(tenant: str = Depends(current_tenant)):
    from .avatar import service as av
    return av.get(tenant)


@app.put("/api/avatar", dependencies=[Depends(require_key)])
def avatar_put(body: AvatarIn, tenant: str = Depends(current_tenant)):
    from .avatar import service as av
    try:
        return av.save(tenant, body.name, body.gender, body.voice, body.setup_done, body.rules, body.look)
    except av.AvatarError as e:
        raise HTTPException(400, str(e))


@app.get("/api/avatar/looks", dependencies=[Depends(require_key)])
def avatar_looks(gender: str = "f"):
    """The 3D looks an avatar can wear: 100 female (f001..) or 100 male (m001..) looks from around the world.
    For a male avatar "" (the original Santosh) is the default and always allowed."""
    from .avatar import service as av
    g = gender if gender in ("m", "f") else "f"
    return {"gender": g, "default": av.DEFAULT_LOOK[g], "looks": [x for x in av.looks() if x["id"][0] == g]}


@app.post("/api/avatar/rules/parse", dependencies=[Depends(require_key)])
async def avatar_rules_parse(body: RulesTextIn, tenant: str = Depends(current_tenant)):
    """Owner's own words -> proposed rules (not saved until PUT /api/avatar with rules)."""
    from .avatar import service as av
    try:
        cur = av.get(tenant)
        rules = await av.parse_rules(body.text, cur["rules"])
    except av.AvatarError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(503, "Could not understand the rule just now; pick it yourself from below.")
    return {"rules": rules, "rules_summary": av.rules_summary(rules, cur["name"])}


# ---------------- App Jaanch (REA static checks of APK / EXE files; nothing is run) ----------------
@app.get("/api/appcheck", dependencies=[Depends(require_key)])
def appcheck_state(tenant: str = Depends(current_tenant)):
    from .appcheck import service as acs
    return acs.status() | {"history": acs.history(tenant)}


@app.post("/api/appcheck/upload", dependencies=[Depends(require_key)])
async def appcheck_upload(file: UploadFile = File(...), conversation_id: str = Form(""), tenant: str = Depends(current_tenant)):
    import asyncio
    from .appcheck import service as acs
    from .appcheck.runner import ReaError
    from .pc import service as pcs
    if not acs.status()["enabled"]:
        raise HTTPException(503, "App Check is not running on the server right now.")
    try:
        row = await pcs.store_upload(file, tenant, "", "to_phone", limit_mb=get_settings().appcheck_max_mb)
    except pcs.PairError as e:
        raise HTTPException(413, str(e))
    try:
        return await asyncio.to_thread(acs.check, tenant, conversation_id, {"file_id": row.id})
    except (acs.CheckError, ReaError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/appcheck/{cid}", dependencies=[Depends(require_key)])
def appcheck_get(cid: str, tenant: str = Depends(current_tenant)):
    from .appcheck import service as acs
    try:
        return acs.get(tenant, cid)
    except acs.CheckError as e:
        raise HTTPException(404, str(e))


from .notebook.api import make_router as _notebook_router  # noqa: E402

app.include_router(_notebook_router(require_key, current_tenant))

from .quality.api import make_router as _quality_router  # noqa: E402

app.include_router(_quality_router(require_key))
from .interactive.api import router as _interactive_router
app.include_router(_interactive_router(require_key, current_tenant))   # live-talk ticket (the engine key never reaches a browser)

from .drive.api import make_router as _drive_router  # noqa: E402
from .forms.api import make_router as _forms_router  # noqa: E402

app.include_router(_drive_router(require_key, current_tenant))
app.include_router(_forms_router(require_key, current_tenant))
from .photos.api import make_router as _photos_router  # noqa: E402

app.include_router(_photos_router(require_key, current_tenant))

# v0.133 Seva suite: 7 customer-support Sahayaks (each module owns its /api/<mod>/* routes)
from .seva.api import make_router as _seva_router  # noqa: E402
from .helpdesk.api import make_router as _helpdesk_router  # noqa: E402
from .shikayat.api import make_router as _shikayat_router  # noqa: E402
from .aftersales.api import make_router as _aftersales_router  # noqa: E402
from .feedback.api import make_router as _feedback_router  # noqa: E402
from .wapsi.api import make_router as _wapsi_router  # noqa: E402
from .samudaay.api import make_router as _samudaay_router  # noqa: E402
from .callcentre.api import make_router as _callcentre_router  # noqa: E402

for _mk in (_seva_router, _helpdesk_router, _shikayat_router, _aftersales_router, _feedback_router, _wapsi_router,
            _samudaay_router, _callcentre_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.137 Tech suite: 9 Technology & software Sahayaks (each module owns its /api/<mod>/* routes; the few public ones
# - ispnoc / devops collectors, docwriter / product published pages - verify their own signature / token in code)
from .devsahayak.api import make_router as _devsahayak_router  # noqa: E402
from .qa.api import make_router as _qa_router  # noqa: E402
from .itadmin.api import make_router as _itadmin_router  # noqa: E402
from .ispnoc.api import make_router as _ispnoc_router  # noqa: E402
from .cyber.api import make_router as _cyber_router  # noqa: E402
from .devops.api import make_router as _devops_router  # noqa: E402
from .docwriter.api import make_router as _docwriter_router  # noqa: E402
from .appreview.api import make_router as _appreview_router  # noqa: E402
from .product.api import make_router as _product_router  # noqa: E402

for _mk in (_devsahayak_router, _qa_router, _itadmin_router, _ispnoc_router, _cyber_router, _devops_router,
            _docwriter_router, _appreview_router, _product_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.139 Safar suite: 7 Logistics, transport & travel Sahayaks (all routes key-protected under /api/<mod>/*; no public routes)
from .customs.api import make_router as _customs_router  # noqa: E402
from .travel.api import make_router as _travel_router  # noqa: E402
from .warehouse.api import make_router as _warehouse_router  # noqa: E402
from .fleet.api import make_router as _fleet_router  # noqa: E402
from .ownmap_api import make_router as _ownmap_router  # noqa: E402  (v0.468)
from .research.api import make_router as _research_router  # noqa: E402  (v0.476 R5: research cost + runs)
from .courier.api import make_router as _courier_router  # noqa: E402
from .drivers.api import make_router as _drivers_router  # noqa: E402
from .logistics.api import make_router as _logistics_router  # noqa: E402

for _mk in (_customs_router, _travel_router, _warehouse_router, _fleet_router, _ownmap_router, _research_router, _courier_router, _drivers_router, _logistics_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.540 LEADS NEEV: the lead generation engine's foundation (plan first: docs/LEADS_PLAN.md, owner "P0 BUILD").
# Key-protected /api/leads/* - the run, the store, the export, the campaign-list hand-off (consent=False), forget.
# P0 runs L0 (her data) only; the engine never contacts anyone.
from .leads.api import make_router as _leads_router  # noqa: E402

app.include_router(_leads_router(require_key, current_tenant))

# v0.144 Makaan suite: 6 Real estate & construction Sahayaks (all under /api/<mod>/*, key-protected; the ONLY public routes are
# propagent's listing page /api/propagent/page/{token}[/photo/{n}], which check their own random token)
from .propagent.api import make_router as _propagent_router  # noqa: E402
from .rentdesk.api import make_router as _rentdesk_router  # noqa: E402
from .sitesup.api import make_router as _sitesup_router  # noqa: E402
from .interior.api import make_router as _interior_router  # noqa: E402
from .archassist.api import make_router as _archassist_router  # noqa: E402
from .society.api import make_router as _society_router  # noqa: E402

for _mk in (_propagent_router, _rentdesk_router, _sitesup_router, _interior_router, _archassist_router, _society_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.150 Kanoon suite: 8 Law, compliance & safety Sahayaks (all under /api/<mod>/*, key-protected; no public routes)
from .vakil.api import make_router as _vakil_router  # noqa: E402
from .legalres.api import make_router as _legalres_router  # noqa: E402
from .compliance.api import make_router as _compliance_router  # noqa: E402
from .contracts.api import make_router as _contracts_router  # noqa: E402
from .cosec.api import make_router as _cosec_router  # noqa: E402
from .notary.api import make_router as _notary_router  # noqa: E402
from .pidesk.api import make_router as _pidesk_router  # noqa: E402
from .dpo.api import make_router as _dpo_router  # noqa: E402

for _mk in (_vakil_router, _legalres_router, _compliance_router, _contracts_router, _cosec_router, _notary_router, _pidesk_router, _dpo_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.381 Shiksha suite Phase 0 + 1: education foundation + Pathyakram (curriculum & exam designer), key-protected
from .shiksha.api import make_router as _shiksha_router  # noqa: E402
from .pathyakram.api import make_router as _pathyakram_router  # noqa: E402

from .guru.api import make_router as _guru_router  # noqa: E402  (Shiksha Phase 2: personal tutor)

from .daftar.api import make_router as _daftar_router  # noqa: E402  (Shiksha Phase 3: school office)

from .shodh.api import make_router as _shodh_router  # noqa: E402  (Shiksha Phase 4: research assistant)

for _mk in (_shiksha_router, _pathyakram_router, _guru_router, _daftar_router, _shodh_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.415 Prayogshala (3D practical labs): the catalogue is public teaching material (no user data), read without a key
from .prayog.api import make_router as _prayog_router  # noqa: E402

app.include_router(_prayog_router(require_key, current_tenant))   # catalogue public; /api/prayog/ask needs the key

# v0.152 Mehmaan suite: 6 Hospitality, events & tourism Sahayaks (under /api/<mod>/*, key-protected; homestay's router also holds
# the public calendar feed /api/homestay-ical/{tenant}/{token}.ics, which checks its own random token)
from .frontoffice.api import make_router as _frontoffice_router  # noqa: E402
from .eventplan.api import make_router as _eventplan_router  # noqa: E402
from .shaadi.api import make_router as _shaadi_router  # noqa: E402
from .tourguide.api import make_router as _tourguide_router  # noqa: E402
from .homestay.api import make_router as _homestay_router  # noqa: E402
from .banquet.api import make_router as _banquet_router  # noqa: E402

for _mk in (_frontoffice_router, _eventplan_router, _shaadi_router, _tourguide_router, _homestay_router, _banquet_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.156 Kala suite: 10 Media, design & creative Sahayaks (under /api/<mod>/*, key-protected; podcast's router also holds two
# PUBLIC routes that check their own random feed token: GET /api/podcast/feed/{token}.xml and /api/podcast/pub/{token}/{ep}/{name})
from .editdesk.api import make_router as _editdesk_router  # noqa: E402
from .motiondesk.api import make_router as _motiondesk_router  # noqa: E402
from .filmdesk.api import make_router as _filmdesk_router  # noqa: E402
from .patrakar.api import make_router as _patrakar_router  # noqa: E402
from .photoassist.api import make_router as _photoassist_router  # noqa: E402
from .graphic.api import make_router as _graphic_router  # noqa: E402
from .artistmgr.api import make_router as _artistmgr_router  # noqa: E402
from .kitab.api import make_router as _kitab_router  # noqa: E402
from .podcast.api import make_router as _podcast_router  # noqa: E402
from .influencer.api import make_router as _influencer_router  # noqa: E402

for _mk in (_editdesk_router, _motiondesk_router, _filmdesk_router, _patrakar_router, _photoassist_router, _graphic_router,
            _artistmgr_router, _kitab_router, _podcast_router, _influencer_router):
    app.include_router(_mk(require_key, current_tenant))

# v0.141 3D Studio (Blender in a locked box): /api/blender3d/*; the signed file route checks its own signature
from .blender3d.api import make_router as _blender3d_router  # noqa: E402

app.include_router(_blender3d_router(require_key, current_tenant))
# v0.370 GAME DESK (Godot 4 games built + test-played in a locked box): /api/game/* and the secret play links /play/<token>/
from .gamedesk.api import make_router as _game_router  # noqa: E402

app.include_router(_game_router(require_key, current_tenant))

# v0.147 Hoola Postgres (her own database: reads READ ONLY, changes only on her tap): /api/pgdb/*
from .pgdb.api import make_router as _pgdb_router  # noqa: E402

app.include_router(_pgdb_router(require_key, current_tenant))

# v0.134 Gyaan (knowledge base / agentic RAG): /api/gyaan/*
from .gyaan.api import make_router as _gyaan_router  # noqa: E402

app.include_router(_gyaan_router(require_key, current_tenant))

# v0.473 Hoola Coder (persistent session memory): /api/coder/*
from .coder.service import make_router as _coder_router  # noqa: E402

app.include_router(_coder_router(require_key, current_tenant))


# v0.716 SEEKH MANCH ON THE CONSOLE (the HOOLA AI Video Learner panel): /api/seekh/console/* - the watch
# job with live stages, the progress pulse and the learned-kaam list. PERFORM is not an endpoint: the panel
# composes one honest chat turn, so the task runs through the agent and the computer operator's own browser.
from .seekh_console import make_router as _seekh_console_router  # noqa: E402

app.include_router(_seekh_console_router(require_key, current_tenant))


# v0.486.0 BYOX SKILL PACK: /api/byox/categories and /api/byox/guide/{slug} (restored v0.492.0: dropped by a merge)
from .byox.guide import get_guide, list_categories as _byox_list  # noqa: E402


@app.get("/api/byox/categories", dependencies=[Depends(require_key)])
async def byox_categories(q: str = ""):
    return {"categories": _byox_list(q)}


@app.get("/api/byox/guide/{slug}", dependencies=[Depends(require_key)])
async def byox_guide(slug: str, level: str = "standard", language: str = ""):
    return get_guide(slug, level=level, language=language)


@app.get("/auth/microsoft/callback")
async def microsoft_callback(request: Request):
    return await _finish_mail_link(request)


@app.get("/api/routines", dependencies=[Depends(require_key)])
def get_routines(tenant: str = Depends(current_tenant)):
    from . import life
    return {"routines": life.active_routines(tenant)}


@app.post("/api/routines/{routine_id}/cancel", dependencies=[Depends(require_key)])
def cancel_routine_api(routine_id: str, tenant: str = Depends(current_tenant)):
    from . import life
    from .db import Routine
    with session() as s:
        r = s.get(Routine, routine_id)
        if not r or r.tenant_id != tenant:
            raise HTTPException(404, "Routine not found")
        r.status = "cancelled"
        conv = r.conversation_id
    bus.publish(conv, "routines", {"routines": life.active_routines(tenant)})
    return {"cancelled": routine_id}


@app.get("/api/lists", dependencies=[Depends(require_key)])
def get_lists(tenant: str = Depends(current_tenant)):
    from datetime import datetime
    tz = life.tz_of(tenant)
    day_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    with session() as s:
        rows = s.scalars(select(ListItem).where(ListItem.tenant_id == tenant, ListItem.done.is_(False))
                         .order_by(ListItem.list_name, ListItem.id)).all()
        out: dict[str, list[dict]] = {}
        for r in rows:
            out.setdefault(r.list_name, []).append({"id": r.id, "text": r.text})
        # v0.177: what she finished TODAY stays visible — the daily completed feed (tenant-local day)
        done_rows = s.scalars(select(ListItem).where(ListItem.tenant_id == tenant, ListItem.done.is_(True),
                                                     ListItem.done_at >= day_start)
                              .order_by(ListItem.done_at.desc())).all()
        done_today = [{"id": r.id, "text": r.text, "list_name": r.list_name,
                       "done_at": as_utc(r.done_at).isoformat() if r.done_at else None} for r in done_rows]
        return {"lists": out, "done_today": done_today}


@app.post("/api/lists/items/{item_id}/done", dependencies=[Depends(require_key)])
def tick_item(item_id: int, tenant: str = Depends(current_tenant)):
    with session() as s:
        it = s.get(ListItem, item_id)
        if not it or it.tenant_id != tenant:
            raise HTTPException(404, "Item not found")
        it.done = True
        it.done_at = now()          # v0.177: stamped so the daily completed feed can show it
    return get_lists()


@app.post("/api/lists/items/{item_id}/undo", dependencies=[Depends(require_key)])
def undo_item(item_id: int, tenant: str = Depends(current_tenant)):
    """v0.177: ticked the wrong thing? One tap puts it back on the list (and out of done-today)."""
    with session() as s:
        it = s.get(ListItem, item_id)
        if not it or it.tenant_id != tenant:
            raise HTTPException(404, "Item not found")
        it.done = False
        it.done_at = None
    return get_lists()


@app.get("/api/memory", dependencies=[Depends(require_key)])
def get_memory(tenant: str = Depends(current_tenant)):
    facts = life.memory_facts(tenant, 500)
    used = sum(len(f.text) for f in facts if f.pinned)
    return {"facts": [{"id": f.id, "text": f.text, "pinned": bool(f.pinned), "auto": getattr(f, "source", None) == "auto",
                       "created_at": f.created_at.isoformat()}   # v0.165 home "aaj kya seekha" filters today's facts
                      for f in facts],
            "pinned_chars": used, "pinned_max": life.PINNED_CHARS, "in_prompt": life.recent_facts()}


@app.get("/api/memory/everything", dependencies=[Depends(require_key)])
def memory_everything(tenant: str = Depends(current_tenant)):
    """v0.605 EK YAAD: one view of everything Hoola remembers about her, store by store."""
    from . import memory
    return memory.everything(tenant)


class UnrememberIn(BaseModel):
    source: str = Field(default="", max_length=10)
    id: int | None = None
    conversation_id: str = Field(default="", max_length=64)
    text: str = Field(default="", max_length=800)


@app.post("/api/memory/unremember", dependencies=[Depends(require_key)])
def memory_unremember(body: UnrememberIn, tenant: str = Depends(current_tenant)):
    """v0.612 YAAD SE: 'Bhool jao' on one memory a reply used (a fact, a past chat, a work note, a graph / page line)."""
    from . import memory
    out = memory.unremember(tenant, body.source, body.id, body.conversation_id, body.text)
    if not out.get("ok") and out.get("why") == "not found":
        raise HTTPException(404, "This memory was not found.")
    return out


class MemoryResetIn(BaseModel):
    confirm: str = ""


@app.post("/api/memory/reset", dependencies=[Depends(require_key)])
def memory_reset(body: MemoryResetIn, tenant: str = Depends(current_tenant)):
    """v0.605 EK YAAD: Claude's 'reset memory' - every store forgets her (her chats stay). Needs confirm='RESET'."""
    if (body.confirm or "").strip().upper() != "RESET":
        raise HTTPException(400, "To erase all memory, send confirm='RESET'. Your chats will not be deleted.")
    from . import memory
    return {"ok": True, "removed": memory.reset_all(tenant)}


class PinIn(BaseModel):
    pinned: bool


@app.patch("/api/memory/{fact_id}", dependencies=[Depends(require_key)])
def pin_memory(fact_id: int, body: PinIn, tenant: str = Depends(current_tenant)):
    """'Hamesha yaad': a pinned fact is always in Hoola's mind (short; the rest is searched when needed)."""
    try:
        life.pin_fact(tenant, fact_id, body.pinned)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return get_memory(tenant)


# ---------------- v0.108 Hoola ki yaad (search everything) + Document desk / Sheet Milaan ----------------
@app.get("/api/yaad", dependencies=[Depends(require_key)])
def yaad_search(q: str = "", days: int = 0, kind: str = "", tenant: str = Depends(current_tenant)):
    from . import yaad
    if not q.strip():
        from .agent import context as _ctx
        return {"health": {**yaad.health(tenant), "context": _ctx.health()}, "hits": []}
    return {"hits": yaad.search(tenant, q, 20, days or None, [kind] if kind else None)}


@app.get("/api/docdesk", dependencies=[Depends(require_key)])
def docdesk_all(conv: str = "", tenant: str = Depends(current_tenant)):
    from . import docdesk as dd
    files = dd.job_files(tenant, conv) if conv else dd.job_files(tenant)
    return {"files": [dd._view(f, i) for i, f in enumerate(files, start=1)], "edits": dd.edits(tenant)}


@app.get("/api/docdesk/edits/{edit_id}", dependencies=[Depends(require_key)])
def docdesk_edit(edit_id: str, tenant: str = Depends(current_tenant)):
    from . import docdesk as dd
    try:
        return dd.full_result(tenant, edit_id)
    except dd.DeskError as e:
        raise HTTPException(404, str(e))


class DeskDecideIn(BaseModel):
    yes: bool
    options: dict | None = None


@app.post("/api/docdesk/edits/{edit_id}/decide", dependencies=[Depends(require_key)])
async def docdesk_decide(edit_id: str, body: DeskDecideIn, tenant: str = Depends(current_tenant)):
    """Her tap on a Sheet Milaan / document-edit card: Haan = the new copy goes to her PC's Santosh Inbox (and opens)."""
    from . import docdesk as dd
    try:
        return await dd.decide(tenant, edit_id, body.yes, body.options)
    except dd.DeskError as e:
        raise HTTPException(400, str(e))


# ---------------- v0.63 seekhe hue kaam + circuit breaker numbers ----------------
class ProcedureIn(BaseModel):
    active: bool | None = None
    title: str | None = None
    steps: list[str] | None = None


@app.get("/api/procedures", dependencies=[Depends(require_key)])
def procedures_list(tenant: str = Depends(current_tenant)):
    from . import procedures
    return {"procedures": procedures.listing(tenant)}


@app.patch("/api/procedures/{pid}", dependencies=[Depends(require_key)])
def procedures_edit(pid: str, body: ProcedureIn, tenant: str = Depends(current_tenant)):
    from . import procedures
    try:
        return procedures.update(tenant, pid, body.active, body.title, body.steps)
    except procedures.ProcedureError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/procedures/{pid}", dependencies=[Depends(require_key)])
def procedures_delete(pid: str, tenant: str = Depends(current_tenant)):
    from . import procedures
    try:
        procedures.delete(tenant, pid)
    except procedures.ProcedureError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.get("/api/jaanch", dependencies=[Depends(require_key)])
async def hoola_jaanch(tenant: str = Depends(current_tenant)):
    """v0.92 Hoola Jaanch: every part checked live (about 10 s) + the last 14 days of real work."""
    from . import jaanch
    return await jaanch.run(tenant)


@app.get("/api/jaanch/report", dependencies=[Depends(require_key)])
def hoola_jaanch_report(days: int = 14, tenant: str = Depends(current_tenant)):
    from . import jaanch
    return jaanch.report(tenant, max(1, min(days, 60)))


@app.get("/api/kaam", dependencies=[Depends(require_key)])
async def kaam_get(q: str = "", tenant: str = Depends(current_tenant)):
    """v0.136 the live state of her long jobs (working / waiting for her / done / failed), as Hoola sees it."""
    from . import kaamwatch
    out = await asyncio.to_thread(kaamwatch.status, tenant, q[:80])
    out["stats"] = dict(kaamwatch.STATS)
    return out


@app.get("/api/kaam/list", dependencies=[Depends(require_key)])
async def kaam_list(days: int = 7, tenant: str = Depends(current_tenant)):
    """v0.648 KAAM KA HISAAB: her work in one list - running, waiting for her, finished in the last `days` days; every
    row names the chat or call record it came from (the phone's Kaam sheet, the console's Today > Work)."""
    from . import kaamlist
    return await asyncio.to_thread(kaamlist.listing, tenant, days)


@app.get("/api/agent/stats", dependencies=[Depends(require_key)])
def agent_stats():
    from . import procedures
    from .agent.breaker import STATS
    from .agent import pakka
    from . import callreceipt, scrub, web
    from .agent import santosh as _s
    from .aep import vault_sink
    from .aep.tracers import GLOBAL_STORE
    from . import looplag
    from . import glmdoor
    return {"loop": dict(looplag.STATS), "worker": worker.health(), "sab_glm": glmdoor.status(),
            "breaker": {k: STATS.get(k, 0) for k in ("steer", "constrain", "stop")}, "procedures": dict(procedures.STATS),
            "pakka": dict(pakka.STATS), "halts": dict(_s.HALTS), "scrubbed": scrub.STATS["scrubbed"],
            "parallel": dict(web.PARALLEL_STATS), "call_receipts": dict(callreceipt.STATS),
            # v0.520.0 HOOLA TRACE: the honest counters of the self-hosted LangSmith layer
            "aep_trace": {"enabled": vault_sink.trace_enabled(), "store": len(GLOBAL_STORE),
                          **{k: v for k, v in vault_sink.STATS.items()}}}


# --- v0.520.0 HOOLA TRACE: the run-tree explorer (flag-gated, fail-closed) ---


@app.get("/api/aep/runs", dependencies=[Depends(require_key)])
def aep_runs(limit: int = 20, source: str = "memory", tenant: str = Depends(current_tenant)):
    """Recent runs of the AEP tracer layer: the process ring (source=memory, default)
    or the vault observations typed 'aep_run' (source=vault). aep_trace OFF = fail-closed."""
    from .aep import tracers, vault_sink
    if not vault_sink.trace_enabled():
        return {"ok": False, "error": "aep_trace is switched off - bake, then flip (the trace_flip vps-ops job)"}
    limit = max(1, min(int(limit), 200))
    if source == "vault":
        rows = vault_sink.vault_runs(tenant, limit)
        return {"ok": True, "source": "vault", "count": len(rows), "runs": rows}
    runs = [r.to_dict() for r in tracers.GLOBAL_STORE.recent(limit)]
    return {"ok": True, "source": "memory", "count": len(runs),
            "stats": dict(vault_sink.STATS), "runs": runs}


@app.get("/api/aep/runs/{run_id}", dependencies=[Depends(require_key)])
def aep_run_tree(run_id: str, tenant: str = Depends(current_tenant)):
    """One run nested with its children - the run-tree explorer node. A numeric id
    falls back to the vault row when the process ring does not have it."""
    from .aep import tracers, vault_sink
    if not vault_sink.trace_enabled():
        return {"ok": False, "error": "aep_trace is switched off - bake, then flip (the trace_flip vps-ops job)"}
    tree = tracers.global_tracer().tree(run_id)
    if tree is not None:
        return {"ok": True, "source": "memory", "run": tree}
    obs = vault_sink.vault_run_by_id(tenant, int(run_id)) if run_id.isdigit() else None
    if obs is None:
        return {"ok": False, "error": "no such run"}
    return {"ok": True, "source": "vault", "run": obs}


class AepTurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    brain: str = Field(default="auto", max_length=20)


@app.post("/api/aep/turn/{conversation_id}", dependencies=[Depends(require_key)])
async def aep_turn_route(conversation_id: str, body: AepTurnIn, tenant: str = Depends(current_tenant)):
    """v0.680.0 HOOLA ADOPT: one real turn of HOOLA run ON the AEP - create_agent over the house
    graph (P4), the production brain injected through hoola_brain_factory (P7), nudge+curator
    riding every model call (P5), the P2 tracer attached, chat memory through the conversation's
    thread. THE AUTH LAW the owner named: require_key + current_tenant - a signed-in product user
    or the legacy owner key; anonymous callers refused the moment the server has a key; the
    conversation must belong to the caller's tenant. The reply lands in the same conversation +
    SSE feed like any other turn; the production loop (run_turn) is untouched - this lane is
    opt-in per call, never a silent behavior change."""
    _conv_or_404(conversation_id, tenant)
    from . import usage
    from .agent import aeptune
    from .agent.santosh import _load_history, _save
    usage.bind(tenant, "chat")
    history = _load_history(conversation_id)   # BEFORE the user row lands - never doubled
    _save(conversation_id, "user", body.text, display=body.text)   # the yaad law: a user row starts the exchange as a str
    bus.publish(conversation_id, "message", {"role": "user", "text": body.text})
    bus.publish(conversation_id, "typing", {"on": True})
    try:
        turn = await aeptune.aep_turn(conversation_id, body.text, tenant,
                                      brain=body.brain, history=history)
    except Exception as e:   # noqa: BLE001 - the lane fails loudly, typing always goes away
        bus.publish(conversation_id, "typing", {"on": False})
        raise HTTPException(502, f"aep turn failed: {e}")
    bus.publish(conversation_id, "typing", {"on": False})
    _save(conversation_id, "assistant", [{"type": "text", "text": turn.reply}], display=turn.reply)
    bus.publish(conversation_id, "message", {"role": "assistant", "text": turn.reply, "source": "aep"})
    return {"ok": True, "reply": turn.reply, "run_id": turn.run_id, "thread_id": turn.thread_id,
            "ms": turn.ms, "middleware": turn.middleware, "tools": turn.tools}


class ShopOrderIn(BaseModel):
    what: str
    site: str = ""
    budget: str = ""
    when: str = ""
    address: str = ""
    notes: str = ""
    compare: list[str] = []
    conversation_id: str = ""


@app.get("/api/shop/sites", dependencies=[Depends(require_key)])
def shop_sites():
    """v0.80 Order karo: sites Hoola can order / book from."""
    from .shop import sites
    return {"sites": sites.listing()}


@app.get("/api/shop/orders", dependencies=[Depends(require_key)])
def shop_orders(tenant: str = Depends(current_tenant)):
    from .shop import service as shop
    return {"orders": shop.orders(tenant)}


@app.post("/api/shop/orders", dependencies=[Depends(require_key)])
def shop_order_new(body: ShopOrderIn, tenant: str = Depends(current_tenant)):
    from .shop import service as shop
    try:
        return shop.order(tenant, body.what, body.conversation_id, body.site, body.budget, body.when, body.address,
                          body.notes, [c.lower() for c in body.compare])
    except shop.ShopError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------- v0.82 Darzi Sahayak (tailor / boutique coworker)
class DarziOrderIn(BaseModel):
    customer: str = ""
    name: str = ""
    phone: str = ""
    items: list[dict] = []
    deliver_on: str = ""
    trial_on: str = ""
    advance: float | None = None
    notes: str = ""
    photos: list[str] = []
    force: bool = False
    conversation_id: str = ""


class DarziOrderPatch(BaseModel):
    deliver_on: str = ""
    trial_on: str = ""
    notes: str = ""
    items: list[dict] | None = None
    force: bool = False


class DarziStatusIn(BaseModel):
    status: str
    note: str = ""
    conversation_id: str = ""


class DarziMoneyIn(BaseModel):
    amount: float | None = None
    how: str = ""
    note: str = ""
    reason: str = ""
    text: str = ""
    conversation_id: str = ""


class DarziMeasureIn(BaseModel):
    customer: str = ""
    name: str = ""
    phone: str = ""
    garment: str
    values: dict | str = {}
    person: str = ""
    note: str = ""
    unit: str = ""


class DarziCustomerIn(BaseModel):
    name: str
    phone: str = ""
    notes: str = ""


class DarziQuoteIn(BaseModel):
    approve: bool
    price: float | None = None
    to_list: bool | None = None


class DarziCheckIn(BaseModel):
    items: list[dict] = []
    deliver_on: str = ""
    trial_on: str = ""
    customer: str = ""


def _darzi(fn, *a, **k):
    from .darzi import service as darzi
    try:
        return fn(*a, **k)
    except darzi.DarziError as e:
        raise HTTPException(400, str(e))


@app.get("/api/darzi/today", dependencies=[Depends(require_key)])
def darzi_today(date: str = "", tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.day, tenant, date)


@app.get("/api/darzi/orders", dependencies=[Depends(require_key)])
def darzi_orders(status: str = "open", customer: str = "", tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return {"orders": _darzi(darzi.orders, tenant, status, customer, 150)}


@app.post("/api/darzi/orders", dependencies=[Depends(require_key)])
def darzi_order_new(body: DarziOrderIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.new_order, tenant, body.items, body.customer, body.name, body.phone, body.deliver_on, body.trial_on,
                  body.advance, body.notes, body.photos, body.force, by="owner", conv=body.conversation_id)


@app.get("/api/darzi/orders/{order_id}", dependencies=[Depends(require_key)])
def darzi_order_get(order_id: str, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.get_order, tenant, order_id)


@app.patch("/api/darzi/orders/{order_id}", dependencies=[Depends(require_key)])
def darzi_order_patch(order_id: str, body: DarziOrderPatch, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.update_order, tenant, order_id, body.deliver_on, body.trial_on, body.notes, body.items, body.force)


@app.post("/api/darzi/orders/{order_id}/status", dependencies=[Depends(require_key)])
def darzi_order_status(order_id: str, body: DarziStatusIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.set_status, tenant, order_id, body.status, body.note, conv=body.conversation_id)


@app.post("/api/darzi/orders/{order_id}/pay", dependencies=[Depends(require_key)])
def darzi_order_pay(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.pay, tenant, order_id, body.amount, body.how)


@app.post("/api/darzi/orders/{order_id}/deliver", dependencies=[Depends(require_key)])
def darzi_order_deliver(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.deliver, tenant, order_id, body.amount, body.note, conv=body.conversation_id)


@app.post("/api/darzi/orders/{order_id}/cancel", dependencies=[Depends(require_key)])
def darzi_order_cancel(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.cancel, tenant, order_id, body.reason)


@app.get("/api/darzi/orders/{order_id}/slip", dependencies=[Depends(require_key)])
def darzi_order_slip(order_id: str, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    data = _darzi(darzi.slip_pdf, tenant, order_id)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="order-{order_id}.pdf"'})


@app.post("/api/darzi/orders/{order_id}/slip", dependencies=[Depends(require_key)])
def darzi_order_slip_file(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.slip_file, tenant, order_id, body.conversation_id)


@app.post("/api/darzi/orders/{order_id}/ready", dependencies=[Depends(require_key)])
def darzi_order_ready(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.ready_card, tenant, order_id, body.conversation_id)


@app.post("/api/darzi/orders/{order_id}/send_business", dependencies=[Depends(require_key)])
async def darzi_order_send_business(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    """Her tap: the 'ready' message through the official business WhatsApp (24 h window)."""
    from .darzi import service as darzi
    try:
        return await darzi.send_ready_business(tenant, order_id, body.text)
    except darzi.DarziError as e:
        raise HTTPException(400, str(e))


@app.post("/api/darzi/orders/{order_id}/told", dependencies=[Depends(require_key)])
def darzi_order_told(order_id: str, body: DarziMoneyIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.mark_told, tenant, order_id, body.how or "whatsapp")


@app.get("/api/darzi/customers", dependencies=[Depends(require_key)])
def darzi_customers(q: str = "", tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return {"customers": darzi.customers(tenant, q, 300)}


@app.post("/api/darzi/customers", dependencies=[Depends(require_key)])
def darzi_customer_new(body: DarziCustomerIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.customer_upsert, tenant, body.name, body.phone, body.notes)


@app.get("/api/darzi/customers/{customer_id}", dependencies=[Depends(require_key)])
def darzi_customer_get(customer_id: str, history: bool = False, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    out = _darzi(darzi.measures, tenant, customer_id, "", "", "", history)
    out["orders"] = darzi.orders(tenant, "all", customer_id, 30)
    return out


@app.post("/api/darzi/measures", dependencies=[Depends(require_key)])
def darzi_measure_new(body: DarziMeasureIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.save_measure, tenant, body.customer, body.garment, body.values, body.person, body.note, body.unit,
                  "app", body.name, body.phone)


@app.get("/api/darzi/quotes", dependencies=[Depends(require_key)])
def darzi_quotes(status: str = "pending", tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return {"quotes": darzi.quotes(tenant, status)}


@app.post("/api/darzi/quotes/{quote_id}", dependencies=[Depends(require_key)])
def darzi_quote_decide(quote_id: str, body: DarziQuoteIn, tenant: str = Depends(current_tenant)):
    """Her Haan / Mana on a price Hoola prepared (only from her tap)."""
    from .darzi import service as darzi
    return _darzi(darzi.decide_quote, tenant, quote_id, body.approve, body.price, body.to_list)


@app.get("/api/darzi/settings", dependencies=[Depends(require_key)])
def darzi_settings_get(tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return darzi.settings(tenant)


@app.put("/api/darzi/settings", dependencies=[Depends(require_key)])
def darzi_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    keys = ("enabled", "shop_name", "unit", "pieces_per_day", "closed_days", "rush_percent", "min_days", "prices", "rules",
            "remeasure_months", "ready_template", "morning_time")
    return _darzi(darzi.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.get("/api/darzi/garments", dependencies=[Depends(require_key)])
def darzi_garments():
    from .darzi import garments
    return {"garments": garments.listing()}


@app.post("/api/darzi/check", dependencies=[Depends(require_key)])
def darzi_check(body: DarziCheckIn, tenant: str = Depends(current_tenant)):
    from .darzi import service as darzi
    return _darzi(darzi.check, tenant, body.items, body.deliver_on, body.trial_on, body.customer)


# ---------------------------------------------------------------- v0.84 Galla + Chai Sahayak (chai stall coworker)
class GallaAlertsIn(BaseModel):
    items: list[dict] = []


class GallaCashIn(BaseModel):
    amount: float
    date: str = ""
    hour: int | None = None
    note: str = ""


class ChaiPlanIn(BaseModel):
    for_date: str = ""
    conversation_id: str = ""


class ChaiDecideIn(BaseModel):
    approve: bool
    conversation_id: str = ""


class ChaiStockIn(BaseModel):
    milk_l: float | None = None
    sugar_kg: float | None = None
    tea_kg: float | None = None


class ChaiFeedbackIn(BaseModel):
    for_date: str = ""
    milk_left_l: float | None = None
    ran_out_at: str = ""
    sugar_left_kg: float | None = None
    tea_left_kg: float | None = None
    cash: float | None = None
    bought_milk_l: float | None = None


def _galla(fn, *a, **k):
    from .chai import service as chai
    from .galla import service as galla
    try:
        return fn(*a, **k)
    except (galla.GallaError, chai.ChaiError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/galla/alerts", dependencies=[Depends(require_key)])
def galla_alerts(body: GallaAlertsIn, tenant: str = Depends(current_tenant)):
    """From her phone: 'money received' alerts of the payment apps she picked, already reduced to amount / time / app /
    payer's first name / last 4 of the reference (the full notification never leaves the phone)."""
    from .galla import service as galla
    return galla.ingest_alerts(tenant, body.items)


@app.get("/api/galla/today", dependencies=[Depends(require_key)])
def galla_today(date: str = "", tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return _galla(galla.day_summary, tenant, date)


@app.get("/api/galla/hours", dependencies=[Depends(require_key)])
def galla_hours(days: int = 28, tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return galla.best_hours(tenant, max(1, min(120, days)))


@app.get("/api/galla/recent", dependencies=[Depends(require_key)])
def galla_recent(tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return {"payments": galla.recent(tenant, 80)}


@app.post("/api/galla/cash", dependencies=[Depends(require_key)])
def galla_cash(body: GallaCashIn, tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return _galla(galla.add_cash, tenant, body.amount, body.date, body.hour, body.note)


@app.post("/api/galla/entries/{entry_id}/void", dependencies=[Depends(require_key)])
def galla_void(entry_id: str, tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return _galla(galla.void, tenant, entry_id)


@app.post("/api/galla/statement", dependencies=[Depends(require_key)])
async def galla_statement(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "The statement is bigger than 10 MB.")
    return _galla(galla.import_statement, tenant, file.filename or "statement.csv", data)


@app.get("/api/galla/settings", dependencies=[Depends(require_key)])
def galla_settings_get(tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return galla.settings(tenant)


@app.put("/api/galla/settings", dependencies=[Depends(require_key)])
def galla_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .galla import service as galla
    return _galla(galla.save_settings, tenant, body.get("apps"), body.get("open_hour"), body.get("close_hour"))


@app.get("/api/chai/settings", dependencies=[Depends(require_key)])
def chai_settings_get(tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    return chai.settings(tenant)


@app.put("/api/chai/settings", dependencies=[Depends(require_key)])
def chai_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    keys = ("enabled", "stall_name", "menu", "other_pct", "cash_pct", "safety_pct", "milk_packet_ml", "typical_cups",
            "suppliers", "rules", "plan_time", "milk_factor")
    return _galla(chai.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/chai/stock", dependencies=[Depends(require_key)])
def chai_stock(body: ChaiStockIn, tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    return _galla(chai.set_stock, tenant, body.milk_l, body.sugar_kg, body.tea_kg)


@app.post("/api/chai/plan", dependencies=[Depends(require_key)])
async def chai_plan_make(body: ChaiPlanIn, tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    weather = None
    try:
        from .life import weather_for
        weather = await weather_for(tenant)
    except Exception:
        weather = None
    return await asyncio.to_thread(_galla, chai.plan_tomorrow, tenant, body.for_date, weather, body.conversation_id)


@app.get("/api/chai/plan", dependencies=[Depends(require_key)])
def chai_plan_get(date: str = "", tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    return {"plan": _galla(chai.get_plan, tenant, date)}


@app.post("/api/chai/orders/{order_id}", dependencies=[Depends(require_key)])
def chai_order_decide(order_id: str, body: ChaiDecideIn, tenant: str = Depends(current_tenant)):
    """Her Haan / Mana on a stock order Hoola prepared (only from her tap)."""
    from .chai import service as chai
    return _galla(chai.decide_order, tenant, order_id, body.approve, body.conversation_id)


@app.post("/api/chai/feedback", dependencies=[Depends(require_key)])
def chai_feedback(body: ChaiFeedbackIn, tenant: str = Depends(current_tenant)):
    from .chai import service as chai
    return _galla(chai.feedback, tenant, body.for_date, body.milk_left_l, body.ran_out_at, body.sugar_left_kg,
                  body.tea_left_kg, body.cash, body.bought_milk_l)
# ---------------------------------------------------------------- v0.85 Daftar Sahayak (office manager)
def _office(fn, *a, **k):
    from .office import service as office
    try:
        return fn(*a, **k)
    except office.OfficeError as e:
        raise HTTPException(400, str(e))


@app.get("/api/office", dependencies=[Depends(require_key)])
def office_all(tenant: str = Depends(current_tenant)):
    """Everything for the Daftar screen in one call."""
    from .office import service as office
    return {"today": office.day(tenant), "settings": office.settings(tenant), "items": office.items(tenant),
            "tickets": office.tickets(tenant, "all")[:60], "renewals": office.renewals(tenant, status="all"),
            "deadlines": office.deadlines(tenant, "all")[:80], "petty": office.petty(tenant), "bills": office.bills(tenant, False)[:60],
            "spends": office.spends(tenant, "all")[:40], "vendors": office.vendors(tenant), "starters": office.starters(tenant)}


@app.get("/api/office/today", dependencies=[Depends(require_key)])
def office_today(tenant: str = Depends(current_tenant)):
    from .office import service as office
    return office.day(tenant)


@app.put("/api/office/settings", dependencies=[Depends(require_key)])
def office_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    keys = ("enabled", "office_name", "morning_time", "note_day", "note_time", "windows", "lead_days", "safety_days",
            "month_budget", "team", "rules")
    return _office(office.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/office/items", dependencies=[Depends(require_key)])
def office_item(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.item_upsert, tenant, str(body.get("name") or ""), body.get("qty"), str(body.get("unit") or ""),
                   body.get("min_qty"), body.get("lead_days"), str(body.get("vendor") or ""), body.get("price"),
                   str(body.get("location") or ""), "owner")


@app.post("/api/office/items/{item_id}/use", dependencies=[Depends(require_key)])
def office_item_use(item_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.use, tenant, item_id, body.get("qty"), str(body.get("note") or ""), "owner")


@app.post("/api/office/items/{item_id}/restock", dependencies=[Depends(require_key)])
def office_item_restock(item_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.restock, tenant, item_id, body.get("qty"), body.get("price"), str(body.get("vendor") or ""), "owner")


@app.post("/api/office/reorder", dependencies=[Depends(require_key)])
def office_reorder(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.reorder, tenant, body.get("names") or None, str(body.get("conversation_id") or ""))


@app.post("/api/office/tickets", dependencies=[Depends(require_key)])
def office_ticket_new(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.ticket_new, tenant, str(body.get("title") or ""), str(body.get("asset") or ""),
                   str(body.get("category") or ""), str(body.get("priority") or ""), str(body.get("vendor") or ""),
                   str(body.get("assigned_to") or ""), body.get("photos") or [], "owner", str(body.get("conversation_id") or ""))


@app.patch("/api/office/tickets/{ticket_id}", dependencies=[Depends(require_key)])
def office_ticket_patch(ticket_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.ticket_update, tenant, ticket_id, str(body.get("status") or ""), str(body.get("note") or ""),
                   str(body.get("vendor") or ""), str(body.get("assigned_to") or ""), body.get("cost"), "owner",
                   str(body.get("conversation_id") or ""))


@app.post("/api/office/renewals", dependencies=[Depends(require_key)])
def office_renewal_new(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.renewal_add, tenant, str(body.get("name") or ""), str(body.get("due_on") or ""),
                   str(body.get("kind") or ""), body.get("every_months"), body.get("amount"), str(body.get("vendor") or ""),
                   str(body.get("notes") or ""), body.get("files") or [], str(body.get("notice_by") or ""))


@app.post("/api/office/renewals/{renewal_id}/done", dependencies=[Depends(require_key)])
def office_renewal_done(renewal_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.renewal_done, tenant, renewal_id, body.get("paid"), str(body.get("next_due") or ""),
                   str(body.get("note") or ""))


@app.post("/api/office/renewals/{renewal_id}/pay", dependencies=[Depends(require_key)])
def office_renewal_pay(renewal_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.renewal_pay, tenant, renewal_id, body.get("amount"), str(body.get("conversation_id") or ""))


@app.post("/api/office/deadlines", dependencies=[Depends(require_key)])
def office_deadline_new(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.deadline_add, tenant, str(body.get("title") or ""), str(body.get("due_on") or ""),
                   str(body.get("owner") or ""), str(body.get("note") or ""))


@app.post("/api/office/deadlines/{deadline_id}/done", dependencies=[Depends(require_key)])
def office_deadline_done(deadline_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.deadline_done, tenant, deadline_id, bool(body.get("dropped")))


@app.post("/api/office/nudge", dependencies=[Depends(require_key)])
def office_nudge(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.nudge, tenant, str(body.get("deadline") or ""), str(body.get("owner") or ""),
                   str(body.get("conversation_id") or ""))


@app.post("/api/office/petty", dependencies=[Depends(require_key)])
def office_petty(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.petty_add, tenant, body.get("amount"), str(body.get("what") or ""), str(body.get("kind") or "out"),
                   str(body.get("by") or ""), str(body.get("on") or ""), str(body.get("bill") or ""))


@app.post("/api/office/bills", dependencies=[Depends(require_key)])
def office_bill(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.bill_add, tenant, str(body.get("vendor") or ""), body.get("amount"), str(body.get("number") or ""),
                   str(body.get("bill_date") or ""), str(body.get("due_on") or ""), body.get("gst"), str(body.get("what") or ""),
                   str(body.get("file_id") or ""))


@app.post("/api/office/bills/{bill_id}/paid", dependencies=[Depends(require_key)])
def office_bill_paid(bill_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.bill_paid, tenant, bill_id, str(body.get("on") or ""))


@app.post("/api/office/vendors", dependencies=[Depends(require_key)])
def office_vendor(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.vendor_upsert, tenant, str(body.get("name") or ""), str(body.get("phone") or ""),
                   str(body.get("email") or ""), str(body.get("category") or ""), str(body.get("gstin") or ""),
                   str(body.get("notes") or ""), str(body.get("id") or ""), body.get("udyam"))


@app.post("/api/office/spends", dependencies=[Depends(require_key)])
def office_spend_new(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.spend_request, tenant, str(body.get("title") or ""), body.get("amount"), str(body.get("kind") or "other"),
                   str(body.get("vendor") or ""), str(body.get("why") or ""), str(body.get("conversation_id") or ""))


@app.post("/api/office/spends/{spend_id}", dependencies=[Depends(require_key)])
def office_spend_decide(spend_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her Haan / Mana on a spend card (only from her tap). Approve never pays: she pays in her own app."""
    from .office import service as office
    return _office(office.decide_spend, tenant, spend_id, bool(body.get("approve")), body.get("amount"), str(body.get("note") or ""))


@app.post("/api/office/note", dependencies=[Depends(require_key)])
def office_note(body: dict, tenant: str = Depends(current_tenant)):
    from .office import service as office
    return _office(office.weekly_note, tenant, bool(body.get("file", True)), str(body.get("conversation_id") or ""))


# ---------------------------------------------------------------- v0.87 Lekhak Sahayak (typist + translator)
def _lekhak(fn, *a, **k):
    from .lekhak import service as lekhak
    try:
        return fn(*a, **k)
    except lekhak.LekhakError as e:
        raise HTTPException(400, str(e))


@app.get("/api/lekhak", dependencies=[Depends(require_key)])
def lekhak_all(q: str = "", tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return {"docs": lekhak.docs(tenant, q, 80), "contacts": lekhak.contacts(tenant), "settings": lekhak.settings(tenant),
            "kinds": lekhak.KINDS, "langs": lekhak.LANGS}


@app.get("/api/lekhak/docs/{doc_id}", dependencies=[Depends(require_key)])
def lekhak_doc(doc_id: str, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.get_doc, tenant, doc_id)


@app.post("/api/lekhak/write", dependencies=[Depends(require_key)])
async def lekhak_write(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.write_letter, tenant, str(body.get("dictation") or ""), str(body.get("kind") or ""),
                                   str(body.get("lang") or ""), str(body.get("to") or ""), body.get("to_lines"),
                                   str(body.get("subject") or ""), str(body.get("reference") or ""), body.get("enclosures"),
                                   str(body.get("file_id") or ""), "app", str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/translate", dependencies=[Depends(require_key)])
async def lekhak_translate(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.translate, tenant, str(body.get("text") or ""), str(body.get("to") or ""),
                                   str(body.get("src") or ""), str(body.get("file_id") or ""), str(body.get("doc") or ""),
                                   str(body.get("register") or "formal"), True, str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/grammar", dependencies=[Depends(require_key)])
async def lekhak_grammar(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.fix_grammar, tenant, str(body.get("text") or ""), str(body.get("lang") or ""),
                                   str(body.get("doc") or ""), str(body.get("file_id") or ""), str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/type", dependencies=[Depends(require_key)])
async def lekhak_type(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.type_text, tenant, str(body.get("text") or ""), str(body.get("file_id") or ""),
                                   str(body.get("lang") or ""), str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/krutidev", dependencies=[Depends(require_key)])
def lekhak_krutidev(body: dict):
    from .lekhak import service as lekhak
    return lekhak.krutidev(str(body.get("text") or ""), str(body.get("to") or "unicode"))


@app.post("/api/lekhak/docs/{doc_id}/revise", dependencies=[Depends(require_key)])
async def lekhak_revise(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.revise, tenant, doc_id, str(body.get("instruction") or ""),
                                   str(body.get("conversation_id") or ""))


@app.put("/api/lekhak/docs/{doc_id}", dependencies=[Depends(require_key)])
def lekhak_edit(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """She edited the text herself in the app."""
    from .lekhak import service as lekhak
    return _lekhak(lekhak.edit, tenant, doc_id, str(body.get("text") or ""), body.get("parts"), str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/docs/{doc_id}/files", dependencies=[Depends(require_key)])
async def lekhak_files(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.make_files, tenant, doc_id, str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/docs/{doc_id}/sign_request", dependencies=[Depends(require_key)])
def lekhak_sign_request(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.sign_request, tenant, doc_id, str(body.get("conversation_id") or ""))


@app.post("/api/lekhak/docs/{doc_id}/sign", dependencies=[Depends(require_key)])
async def lekhak_sign(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on the sign card (only from the app): approve + mode paper | image, the card's hash."""
    from .lekhak import service as lekhak
    return await asyncio.to_thread(_lekhak, lekhak.decide_sign, tenant, doc_id, bool(body.get("approve")),
                                   str(body.get("mode") or "paper"), str(body.get("conversation_id") or ""), str(body.get("hash") or ""))


@app.post("/api/lekhak/docs/{doc_id}/copy", dependencies=[Depends(require_key)])
def lekhak_copy(doc_id: str, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.copy_doc, tenant, doc_id)


@app.post("/api/lekhak/docs/{doc_id}/share", dependencies=[Depends(require_key)])
def lekhak_share(doc_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.share_draft, tenant, doc_id, str(body.get("phone") or ""), str(body.get("email") or ""))


@app.post("/api/lekhak/contacts", dependencies=[Depends(require_key)])
def lekhak_contact(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    return _lekhak(lekhak.contact_save, tenant, str(body.get("name") or ""), body.get("lines"), str(body.get("lang") or ""),
                   str(body.get("email") or ""), str(body.get("phone") or ""))


@app.put("/api/lekhak/settings", dependencies=[Depends(require_key)])
def lekhak_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .lekhak import service as lekhak
    keys = ("my_name", "my_lines", "my_phone", "place", "gender", "lang", "letterhead", "keep", "rules", "glossary", "digits", "sign_file")
    return _lekhak(lekhak.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.88 Mobile Dukaan Sahayak (recharge + repair shop)
class MShopJobIn(BaseModel):
    name: str = ""
    phone: str = ""
    brand: str = ""
    model: str = ""
    imei: str = ""
    problem: str = ""
    faults: list[str] = []
    accessories: list[str] = []
    condition: str = ""
    promised_on: str = ""
    estimate: float | None = None
    advance: float | None = None
    proof: str = ""
    technician: str = ""
    force: bool = False
    conversation_id: str = ""


class MShopActIn(BaseModel):
    status: str = ""
    note: str = ""
    name: str = ""
    price: float | None = None
    cost: float | None = None
    warranty_days: int | None = None
    labour: float | None = None
    approve: bool = False
    total: float | None = None
    amount: float | None = None
    how: str = ""
    promised_on: str = ""
    technician: str = ""
    imei: str = ""
    proof: str = ""
    estimate: float | None = None
    force: bool = False
    conversation_id: str = ""


class MShopRechargeIn(BaseModel):
    number: str
    amount: float
    operator: str = ""
    validity_days: int | None = None
    name: str = ""
    plan: str = ""
    via: str = ""
    date: str = ""


def _mshop(fn, *a, **k):
    from .mshop import service as mshop
    try:
        return fn(*a, **k)
    except mshop.MShopError as e:
        raise HTTPException(400, str(e))


@app.get("/api/mshop/today", dependencies=[Depends(require_key)])
def mshop_today(tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return mshop.day(tenant)


@app.get("/api/mshop/jobs", dependencies=[Depends(require_key)])
def mshop_jobs(status: str = "open", q: str = "", tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return {"jobs": mshop.jobs(tenant, status, q, 200)}


@app.post("/api/mshop/jobs", dependencies=[Depends(require_key)])
def mshop_job_new(body: MShopJobIn, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return _mshop(mshop.new_job, tenant, body.name, body.phone, body.brand, body.model, body.imei, body.problem, body.faults,
                  body.accessories, body.condition, body.promised_on, body.estimate, body.advance, body.proof, [],
                  body.technician, body.force, "owner", body.conversation_id)


@app.post("/api/mshop/check", dependencies=[Depends(require_key)])
def mshop_check(body: MShopJobIn, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return _mshop(mshop.check_job, tenant, body.problem, body.faults, body.brand, body.model, body.imei, body.phone,
                  body.promised_on, body.proof)


@app.get("/api/mshop/jobs/{job_id}", dependencies=[Depends(require_key)])
def mshop_job_get(job_id: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return _mshop(mshop.get_job, tenant, job_id)


@app.post("/api/mshop/jobs/{job_id}/photos", dependencies=[Depends(require_key)])
async def mshop_photo_add(job_id: str, file: UploadFile = File(...), kind: str = Form("in"), note: str = Form(""),
                          tenant: str = Depends(current_tenant)):
    """A photo of the phone (camera in the app): kept in the shop's own store as warranty proof."""
    from .mshop import service as mshop
    data = await file.read()
    return _mshop(mshop.add_photo, tenant, job_id, data, file.filename or "photo.jpg", kind, note)


@app.post("/api/mshop/jobs/{job_id}/{action}", dependencies=[Depends(require_key)])
def mshop_job_act(job_id: str, action: str, body: MShopActIn, tenant: str = Depends(current_tenant)):
    """status | part | bill | decide (her Haan on the bill, only from her tap) | customer_ok | pay | deliver | update | ready | slip"""
    from .mshop import service as mshop
    conv = body.conversation_id
    if action == "status":
        return _mshop(mshop.set_status, tenant, job_id, body.status, body.note, conv=conv)
    if action == "part":
        return _mshop(mshop.add_part, tenant, job_id, body.name, body.price, body.cost, body.warranty_days, body.labour)
    if action == "bill":
        return _mshop(mshop.prepare_bill, tenant, job_id, conv)
    if action == "decide":
        return _mshop(mshop.decide_bill, tenant, job_id, body.approve, body.total, conv)
    if action == "customer_ok":
        return _mshop(mshop.customer_agreed, tenant, job_id, body.estimate)
    if action == "pay":
        return _mshop(mshop.pay, tenant, job_id, body.amount, body.how)
    if action == "deliver":
        return _mshop(mshop.deliver, tenant, job_id, body.amount, body.note, conv=conv)
    if action == "update":
        return _mshop(mshop.update_job, tenant, job_id, body.promised_on, body.note, body.technician, body.imei, body.proof,
                      body.estimate, body.force)
    if action == "ready":
        return _mshop(mshop.ready_card, tenant, job_id, conv)
    if action == "estimate_message":
        return _mshop(mshop.estimate_message, tenant, job_id)
    if action == "slip":
        return _mshop(mshop.slip_file, tenant, job_id, conv)
    raise HTTPException(404, "Unknown action")


@app.get("/api/mshop/jobs/{job_id}/slip.pdf", dependencies=[Depends(require_key)])
def mshop_job_slip(job_id: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return Response(_mshop(mshop.slip_pdf, tenant, job_id), media_type="application/pdf")


@app.get("/api/mshop/photos/{photo_id}", dependencies=[Depends(require_key)])
def mshop_photo_get(photo_id: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    path, mime = _mshop(mshop.photo_file, tenant, photo_id)
    return FileResponse(path, media_type=mime)


@app.get("/api/mshop/warranty", dependencies=[Depends(require_key)])
def mshop_warranty(q: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return mshop.warranty(tenant, q)


@app.post("/api/mshop/recharges", dependencies=[Depends(require_key)])
def mshop_recharge_new(body: MShopRechargeIn, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return _mshop(mshop.add_recharge, tenant, body.number, body.amount, body.operator, body.validity_days, body.name,
                  body.plan, body.via, body.date)


@app.get("/api/mshop/recharges", dependencies=[Depends(require_key)])
def mshop_recharges(date: str = "", tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return {"day": _mshop(mshop.recharges_day, tenant, date), "recent": mshop.recent_recharges(tenant, 80),
            "due": mshop.due_recharges(tenant)}


@app.post("/api/mshop/recharges/{recharge_id}/{action}", dependencies=[Depends(require_key)])
def mshop_recharge_act(recharge_id: str, action: str, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    if action == "reminded":
        return _mshop(mshop.mark_reminded, tenant, recharge_id)
    if action == "void":
        return _mshop(mshop.void_recharge, tenant, recharge_id)
    raise HTTPException(404, "Unknown action")


@app.get("/api/mshop/settings", dependencies=[Depends(require_key)])
def mshop_settings_get(tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    return mshop.settings(tenant)


@app.put("/api/mshop/settings", dependencies=[Depends(require_key)])
def mshop_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .mshop import service as mshop
    keys = ("enabled", "shop_name", "gstin", "gst_on", "prices", "warranty", "fix_days", "jobs_per_day", "unclaimed_days",
            "commission", "remind_days", "terms", "ready_template", "rules", "morning_time")
    return _mshop(mshop.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.90 Phone Doctor
def _pdoc(fn, *a, **k):
    from .phonedoc import service as pdoc
    try:
        return fn(*a, **k)
    except pdoc.PhoneDocError as e:
        raise HTTPException(400, str(e))


@app.get("/api/phonedoc/issues", dependencies=[Depends(require_key)])
def phonedoc_issues():
    from .phonedoc import service as pdoc
    return {"issues": pdoc.issues()}


@app.post("/api/phonedoc/check", dependencies=[Depends(require_key)])
def phonedoc_check(body: dict, tenant: str = Depends(current_tenant)):
    """The Hoola app posts the phone's own state (settings, battery, storage, network; no personal content)."""
    from .phonedoc import service as pdoc
    return _pdoc(pdoc.save_snapshot, tenant, body.get("snapshot") if isinstance(body.get("snapshot"), dict) else body)


@app.get("/api/phonedoc/cases", dependencies=[Depends(require_key)])
def phonedoc_cases(status: str = "", tenant: str = Depends(current_tenant)):
    from .phonedoc import service as pdoc
    return {"cases": pdoc.cases(tenant, status, 40)}


@app.post("/api/phonedoc/cases", dependencies=[Depends(require_key)])
def phonedoc_start(body: dict, tenant: str = Depends(current_tenant)):
    from .phonedoc import service as pdoc
    snap = body.get("snapshot") if isinstance(body.get("snapshot"), dict) else None
    if snap and not str(body.get("for_whom") or "").strip():
        _pdoc(pdoc.save_snapshot, tenant, snap)
    return _pdoc(pdoc.start, tenant, str(body.get("text") or ""), str(body.get("issue") or ""), str(body.get("for_whom") or ""),
                 str(body.get("device") or ""), str(body.get("app_package") or ""), snap)


@app.get("/api/phonedoc/cases/{case_id}", dependencies=[Depends(require_key)])
def phonedoc_case(case_id: str, tenant: str = Depends(current_tenant)):
    from .phonedoc import service as pdoc
    return _pdoc(pdoc.get_case, tenant, case_id)


@app.post("/api/phonedoc/cases/{case_id}/{action}", dependencies=[Depends(require_key)])
def phonedoc_case_action(case_id: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    from .phonedoc import service as pdoc
    if action == "step":
        return _pdoc(pdoc.step, tenant, case_id, str(body.get("step_id") or ""), str(body.get("result") or ""), str(body.get("note") or ""))
    if action == "recheck":
        snap = body.get("snapshot") if isinstance(body.get("snapshot"), dict) else None
        if snap:
            _pdoc(pdoc.save_snapshot, tenant, snap)
        return _pdoc(pdoc.recheck, tenant, case_id, snap)
    if action == "escalate":
        return _pdoc(pdoc.escalate, tenant, case_id, str(body.get("kind") or ""), bool(body.get("make_job")), str(body.get("phone") or ""))
    if action == "close":
        return _pdoc(pdoc.close, tenant, case_id)
    raise HTTPException(404, "step | recheck | escalate | close")


# ---------------------------------------------------------------- v0.117 Theka Sahayak (contractor)
def _tk(fn, *a, **k):
    from .theka import service as tk
    try:
        return fn(*a, **k)
    except (tk.ThekaError, ValueError) as e:
        raise HTTPException(400, str(e))


_TK_TENDER = ("dept", "portal", "ref", "value", "emd", "emd_mode", "prebid", "last_date", "opening", "status", "have", "our_quote", "l1", "emd_back", "notes")
_TK_PROJECT = ("client", "govt", "agreement_no", "value", "start", "end", "dlp_months", "gst_rate", "retention_pct", "sd_pct", "it_tds_pct", "gst_tds",
               "cess_pct", "mob_advance", "mob_pct", "deviation_pct", "bg_no", "bg_amount", "bg_valid_to", "insurance_valid_to", "completed_on", "status")


@app.get("/api/theka/day", dependencies=[Depends(require_key)])
def theka_day(tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return {**_tk(tk.day, tenant), "settings": tk.settings(tenant), "tenders": tk.tenders(tenant), "projects": tk.projects(tenant),
            "receivables": tk.receivables(tenant)}


@app.post("/api/theka/settings", dependencies=[Depends(require_key)])
def theka_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    keys = ("firm", "gstin", "individual", "udyam", "registration", "registration_valid_to", "address", "morning_time")
    return _tk(tk.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/theka/tenders", dependencies=[Depends(require_key)])
def theka_tender(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.save_tender, tenant, str(body.get("name") or ""), str(body.get("tender") or ""), **{k: body[k] for k in _TK_TENDER if k in body})


@app.post("/api/theka/projects", dependencies=[Depends(require_key)])
def theka_project(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.save_project, tenant, str(body.get("name") or ""), str(body.get("project") or ""), **{k: body[k] for k in _TK_PROJECT if k in body})


@app.get("/api/theka/projects/{pid}", dependencies=[Depends(require_key)])
def theka_project_get(pid: str, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return {**_tk(tk.project_view, tenant, pid), "boq": _tk(tk.boq_items, tenant, pid), "stock": _tk(tk.stock, tenant, pid)}


@app.post("/api/theka/projects/{pid}/boq", dependencies=[Depends(require_key)])
async def theka_boq_upload(pid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    data = await file.read()
    return _tk(tk.boq, tenant, pid, None, data, file.filename or "boq.csv")


@app.post("/api/theka/projects/{pid}/{action}", dependencies=[Depends(require_key)])
def theka_project_act(pid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """measure | ra_bill | material | diary | eot"""
    from .theka import service as tk
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    conv = g("conversation_id")
    if action == "measure":
        return _tk(tk.measure, tenant, pid, g("item"), body.get("qty"), g("detail"), g("day"), g("by"))
    if action == "ra_bill":
        return _tk(tk.ra_bill, tenant, pid, g("upto"), bool(body.get("final")), conv)
    if action == "material":
        return _tk(tk.material, tenant, pid, g("item"), body.get("qty"), body.get("rate"), bool(body.get("used")), g("day"), g("note"))
    if action == "diary":
        return _tk(tk.diary, tenant, pid, body.get("labour") or 0, g("work"), g("hindrance"), body.get("lost_hours"), bool(body.get("by_client")), g("day"))
    if action == "eot":
        return _tk(tk.eot_letter, tenant, pid, conv)
    raise HTTPException(404, "measure | ra_bill | material | diary | eot")


@app.post("/api/theka/bills/{bid}", dependencies=[Depends(require_key)])
def theka_bill_status(bid: str, body: dict, tenant: str = Depends(current_tenant)):
    """status submitted (her Haan, only from her tap) | passed | paid"""
    from .theka import service as tk
    return _tk(tk.bill_status, tenant, bid, str(body.get("status") or ""), body.get("amount"), str(body.get("on") or ""))


@app.post("/api/theka/subs", dependencies=[Depends(require_key)])
def theka_sub(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.save_sub, tenant, str(body.get("name") or ""), str(body.get("phone") or ""), body.get("individual"), body.get("pan_ok"),
               str(body.get("work") or ""), body.get("retention_pct"))


@app.post("/api/theka/sub_bills", dependencies=[Depends(require_key)])
def theka_sub_bill(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.sub_bill, tenant, str(body.get("sub") or ""), body.get("amount"), str(body.get("project") or ""), str(body.get("day") or ""),
               str(body.get("note") or ""))


@app.post("/api/theka/register", dependencies=[Depends(require_key)])
def theka_register(body: dict, tenant: str = Depends(current_tenant)):
    from .theka import service as tk
    return _tk(tk.register_file, tenant, str(body.get("conversation_id") or ""))


# ---------------------------------------------------------------- v0.115 Franchise Sahayak (franchise owner)
def _fr(fn, *a, **k):
    from .franchise import service as fr
    try:
        return fn(*a, **k)
    except (fr.FrError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/franchise/day", dependencies=[Depends(require_key)])
def franchise_day(tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return {**_fr(fr.day, tenant), "outlets": fr.outlets(tenant), "agreements": fr.agreements(tenant), "settings": fr.settings(tenant),
            "statements": fr.statements(tenant)}


@app.post("/api/franchise/settings", dependencies=[Depends(require_key)])
def franchise_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.save_settings, tenant, **{k: body[k] for k in ("company", "state", "tds_applies", "morning_time") if k in body})


@app.post("/api/franchise/agreements", dependencies=[Depends(require_key)])
def franchise_agreement(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    keys = ("franchisor", "contact", "royalty_pct", "marketing_pct", "tech_fee", "min_guarantee", "base", "foreign", "franchisor_state",
            "due_day", "start", "term_years", "lock_in_years", "notice_months", "checklist", "notes")
    return _fr(fr.save_agreement, tenant, str(body.get("brand") or ""), **{k: body[k] for k in keys if k in body})


@app.post("/api/franchise/outlets", dependencies=[Depends(require_key)])
def franchise_outlet(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _fr(fr.save_outlet, tenant, g("name"), g("brand"), g("city"), g("opened_on"), body.get("rent"), g("lease_end"),
               body.get("escalation_pct"), g("escalation_on"), body.get("targets"), g("manager_phone"))


@app.post("/api/franchise/sales", dependencies=[Depends(require_key)])
def franchise_sale(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.add_sale, tenant, str(body.get("outlet") or ""), body.get("net"), str(body.get("day") or ""), body.get("gross"),
               body.get("discount"), body.get("gst"), body.get("orders"), body.get("channels"))


@app.post("/api/franchise/sales/import", dependencies=[Depends(require_key)])
async def franchise_import(file: UploadFile = File(...), outlet: str = Form(""), tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    data = await file.read()
    return _fr(fr.import_sales, tenant, outlet, data, file.filename or "sales.csv")


@app.post("/api/franchise/costs", dependencies=[Depends(require_key)])
def franchise_cost(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.add_cost, tenant, str(body.get("outlet") or ""), str(body.get("kind") or "other"), body.get("amount"),
               str(body.get("month") or ""), str(body.get("note") or ""))


@app.post("/api/franchise/statements", dependencies=[Depends(require_key)])
def franchise_statement(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.statement, tenant, str(body.get("brand") or ""), str(body.get("month") or ""), str(body.get("conversation_id") or ""))


@app.post("/api/franchise/statements/{sid}/{action}", dependencies=[Depends(require_key)])
def franchise_statement_act(sid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """approve (her Haan, only from her tap) | paid"""
    from .franchise import service as fr
    if action == "approve":
        return _fr(fr.approve_statement, tenant, sid)
    if action == "paid":
        return _fr(fr.mark_paid, tenant, sid, str(body.get("on") or ""))
    raise HTTPException(404, "approve | paid")


@app.post("/api/franchise/licences", dependencies=[Depends(require_key)])
def franchise_licence(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.save_licence, tenant, str(body.get("outlet") or ""), str(body.get("kind") or "other"), str(body.get("valid_to") or ""),
               str(body.get("number") or ""), str(body.get("note") or ""))


@app.post("/api/franchise/audits", dependencies=[Depends(require_key)])
def franchise_audit(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.audit, tenant, str(body.get("outlet") or ""), body.get("failed"), body.get("items"), str(body.get("kind") or "daily"),
               str(body.get("day") or ""), str(body.get("note") or ""))


@app.post("/api/franchise/pnl_file", dependencies=[Depends(require_key)])
def franchise_pnl_file(body: dict, tenant: str = Depends(current_tenant)):
    from .franchise import service as fr
    return _fr(fr.pnl_file, tenant, str(body.get("month") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/franchise/{what}", dependencies=[Depends(require_key)])
def franchise_read(what: str, outlet: str = "", month: str = "", tenant: str = Depends(current_tenant)):
    """pnl | compare | licences | dates"""
    from .franchise import service as fr
    fns = {"pnl": lambda: fr.pnl(tenant, outlet, month), "compare": lambda: fr.compare(tenant, month), "licences": lambda: fr.licences(tenant),
           "dates": lambda: {"dates": fr.dates_watch(tenant)}}
    if what not in fns:
        raise HTTPException(404, "pnl | compare | licences | dates")
    return _fr(fns[what])


# ---------------------------------------------------------------- v0.110 Niryat Sahayak (exporter)
def _nir(fn, *a, **k):
    from .niryat import service as nr
    try:
        return fn(*a, **k)
    except (nr.NiryatError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/niryat/day", dependencies=[Depends(require_key)])
def niryat_day(tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return {**_nir(nr.day, tenant), "settings": nr.settings(tenant)}


@app.post("/api/niryat/settings", dependencies=[Depends(require_key)])
def niryat_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    keys = ("firm", "address", "iec", "gstin", "phone", "email", "ad_bank", "lut_no", "rcmc", "rcmc_valid_to", "prefix", "morning_time")
    return _nir(nr.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.get("/api/niryat/buyers", dependencies=[Depends(require_key)])
def niryat_buyers(tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return {"buyers": nr.buyers(tenant)}


@app.post("/api/niryat/buyers", dependencies=[Depends(require_key)])
def niryat_buyer_save(body: dict, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _nir(nr.save_buyer, tenant, g("name"), g("buyer"), g("country"), g("address"), g("email"), g("phone"), g("currency"),
                g("pay_terms"), body.get("credit_days"), g("notes"))


@app.get("/api/niryat/shipments", dependencies=[Depends(require_key)])
def niryat_shipments(status: str = "", buyer: str = "", tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return {"shipments": _nir(nr.shipments, tenant, status, buyer)}


@app.post("/api/niryat/shipments", dependencies=[Depends(require_key)])
def niryat_pi(body: dict, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _nir(nr.proforma, tenant, g("buyer"), body.get("lines"), g("text"), g("incoterm") or "FOB", g("place"), body.get("fx"),
                body.get("freight"), body.get("insurance"), g("gst_mode") or "lut", g("port_loading"), g("port_discharge"), g("mode") or "sea",
                g("currency"), g("conversation_id"))


@app.get("/api/niryat/shipments/{sid}", dependencies=[Depends(require_key)])
def niryat_shipment(sid: str, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return _nir(nr.get_shipment, tenant, sid)


@app.post("/api/niryat/shipments/{sid}/{action}", dependencies=[Depends(require_key)])
def niryat_act(sid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """send_pi / confirm (her Haan, only from her tap) | shipped | receive | cancel"""
    from .niryat import service as nr
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    if action == "send_pi":
        return _nir(nr.pi_draft, tenant, sid)
    if action == "confirm":
        return _nir(nr.confirm, tenant, sid, g("inv_date"), body.get("fx"), g("conversation_id"))
    if action == "shipped":
        return _nir(nr.shipped, tenant, sid, g("sb_no"), g("sb_date"), g("bl_no"), g("ship_date"), body.get("fx"))
    if action == "receive":
        return _nir(nr.receive, tenant, sid, body.get("amount"), body.get("inr"), g("on"), g("ref"))
    if action == "cancel":
        return _nir(nr.cancel, tenant, sid, g("reason"))
    raise HTTPException(404, "send_pi | confirm | shipped | receive | cancel")


@app.get("/api/niryat/realisation", dependencies=[Depends(require_key)])
def niryat_realisation(tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return nr.realisation(tenant)


@app.post("/api/niryat/register", dependencies=[Depends(require_key)])
def niryat_register(body: dict, tenant: str = Depends(current_tenant)):
    from .niryat import service as nr
    return _nir(nr.register_file, tenant, str(body.get("conversation_id") or ""))


# ---------------------------------------------------------------- v0.107 Thok Sahayak (wholesale trader)
def _thok(fn, *a, **k):
    from .thok import service as th
    try:
        return fn(*a, **k)
    except (th.ThokError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/thok/day", dependencies=[Depends(require_key)])
def thok_day(tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {**_thok(th.day, tenant), "settings": th.settings(tenant), "route": _thok(th.route_plan, tenant)}


@app.post("/api/thok/settings", dependencies=[Depends(require_key)])
def thok_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    keys = ("firm", "gstin", "address", "phone", "bank", "terms", "aato", "last_fy_turnover", "prefix", "credit_days", "morning_time")
    return _thok(th.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.get("/api/thok/parties", dependencies=[Depends(require_key)])
def thok_parties(kind: str = "", route: str = "", tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {"parties": _thok(th.parties, tenant, kind, route)}


@app.post("/api/thok/parties", dependencies=[Depends(require_key)])
def thok_party_save(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _thok(th.save_party, tenant, g("name"), g("party"), g("kind"), g("phone"), g("gstin"), g("address"), body.get("credit_limit"),
                 body.get("credit_days"), g("route"), body.get("msme"), body.get("pan_ok"), body.get("opening"), body.get("whatsapp_ok"),
                 g("notes"), g("state"))


@app.get("/api/thok/parties/{pid}", dependencies=[Depends(require_key)])
def thok_party(pid: str, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.party_view, tenant, pid)


@app.post("/api/thok/parties/{pid}/statement", dependencies=[Depends(require_key)])
def thok_statement(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.statement_file, tenant, pid, str(body.get("conversation_id") or ""))


@app.get("/api/thok/items", dependencies=[Depends(require_key)])
def thok_items(q: str = "", tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {"items": _thok(th.items, tenant, q)}


@app.post("/api/thok/items", dependencies=[Depends(require_key)])
def thok_item_save(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.save_item, tenant, str(body.get("name") or ""), body.get("price"), body.get("gst_pct"), str(body.get("unit") or ""),
                 body.get("qty"), str(body.get("hsn") or ""), body.get("cost"), str(body.get("supplier") or ""), body.get("lead_days"),
                 body.get("low_at"), body.get("tiers"))


@app.get("/api/thok/orders", dependencies=[Depends(require_key)])
def thok_orders(status: str = "", party: str = "", tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {"orders": _thok(th.orders, tenant, status, party)}


@app.post("/api/thok/orders", dependencies=[Depends(require_key)])
def thok_order_new(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.take_order, tenant, str(body.get("party") or ""), str(body.get("text") or ""), body.get("lines"),
                 str(body.get("note") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/thok/orders/{oid}", dependencies=[Depends(require_key)])
def thok_order_get(oid: str, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.get_order, tenant, oid)


@app.post("/api/thok/orders/{oid}/{action}", dependencies=[Depends(require_key)])
def thok_order_act(oid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """bill (her Haan, only from her tap) | cancel | invoice"""
    from .thok import service as th
    conv = str(body.get("conversation_id") or "")
    if action == "bill":
        return _thok(th.bill, tenant, oid, str(body.get("bill_date") or ""), body.get("lines"), conv)
    if action == "cancel":
        return _thok(th.cancel_order, tenant, oid, str(body.get("reason") or ""))
    if action == "invoice":
        return _thok(th.invoice_file, tenant, oid, conv)
    raise HTTPException(404, "bill | cancel | invoice")


@app.post("/api/thok/receive", dependencies=[Depends(require_key)])
def thok_receive(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _thok(th.receive, tenant, g("party"), body.get("amount"), g("mode") or "cash", g("on"), g("cheque_no"), g("cheque_date"),
                 g("bank"), g("note"))


@app.post("/api/thok/cheques/{pid}", dependencies=[Depends(require_key)])
def thok_cheque(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.cheque, tenant, pid, str(body.get("status") or ""), str(body.get("memo_date") or ""), str(body.get("reason") or ""))


@app.get("/api/thok/payments", dependencies=[Depends(require_key)])
def thok_payments(party: str = "", status: str = "", tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return {"payments": _thok(th.payments, tenant, party, status)}


@app.post("/api/thok/purchases", dependencies=[Depends(require_key)])
def thok_purchase(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.purchase, tenant, str(body.get("supplier") or ""), str(body.get("text") or ""), body.get("lines"),
                 str(body.get("bill_no") or ""), str(body.get("bill_date") or ""), body.get("agreed_days"), body.get("paid"))


@app.post("/api/thok/pay_supplier", dependencies=[Depends(require_key)])
def thok_pay_supplier(body: dict, tenant: str = Depends(current_tenant)):
    from .thok import service as th
    return _thok(th.pay_supplier, tenant, str(body.get("supplier") or ""), body.get("amount"), str(body.get("mode") or "neft"),
                 str(body.get("on") or ""), str(body.get("note") or ""))


@app.get("/api/thok/{what}", dependencies=[Depends(require_key)])
def thok_read(what: str, route: str = "", days: int = 30, tenant: str = Depends(current_tenant)):
    """outstanding | reminders | payables | reorder | margins | route"""
    from .thok import service as th
    fns = {"outstanding": lambda: th.outstanding(tenant, route), "reminders": lambda: th.reminder_drafts(tenant, route),
           "payables": lambda: th.payables(tenant), "reorder": lambda: th.reorder(tenant), "margins": lambda: th.margins(tenant, days),
           "route": lambda: th.route_plan(tenant, route)}
    if what not in fns:
        raise HTTPException(404, "outstanding | reminders | payables | reorder | margins | route")
    return _thok(fns[what])


# ---------------------------------------------------------------- v0.103 SEO Sahayak
def _seo(fn, *a, **k):
    from .seo import service as seo
    try:
        return fn(*a, **k)
    except (seo.SeoError, ValueError) as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------- v0.317 HIRE AN EMPLOYEE + the SEO Employee desk
def _hire_call(fn, *a, **k):
    from .employee import hire
    from .seo import service as seo
    try:
        return fn(*a, **k)
    except (hire.HireError, seo.SeoError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/employees", dependencies=[Depends(require_key)])
def employees_catalog(tenant: str = Depends(current_tenant)):
    from .employee import hire
    return {"employees": hire.catalog(tenant), "hired": hire.hired_keys(tenant)}


@app.post("/api/employees/{key}/hire", dependencies=[Depends(require_key)])
def employees_hire(key: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    from .employee import hire
    return _hire_call(hire.hire, tenant, key, str((body or {}).get("trust") or "seekh"))


@app.post("/api/employees/{key}/{action}", dependencies=[Depends(require_key)])
def employees_action(key: str, action: str, tenant: str = Depends(current_tenant)):
    from .employee import hire
    fn = {"pause": hire.pause, "resume": hire.resume, "leave": hire.leave}.get(action)
    if fn is None:
        raise HTTPException(404, "action: pause | resume | leave")
    return _hire_call(fn, tenant, key)


@app.put("/api/employees/{key}/settings", dependencies=[Depends(require_key)])
def employees_settings(key: str, body: dict, tenant: str = Depends(current_tenant)):
    from .employee import hire
    allowed = {k: body[k] for k in ("trust", "max_pages", "report_to") if k in body}
    return _hire_call(hire.save_settings, tenant, key, **allowed)


def _intel_call(fn, *a, **k):
    from .seo import dfs, intel
    try:
        return fn(*a, **k)
    except (intel.IntelError, dfs.DfsError) as e:
        raise HTTPException(400, str(e))


def _intel_bg(tenant: str, site: str, what: str, fn, *a, **k):
    """Long intel jobs (AI answers, Maps grid, exact positions) run in the background; the result lands on the SEO desk feed."""
    import threading
    from .seo import intel

    def go():
        try:
            r = fn(*a, **k)
            text, level = str(r.get("say") or f"{what} done."), "info"
        except Exception as e:   # noqa: BLE001
            text, level = f"{what}: {e}", "warn"
        try:
            from .seo import desk
            desk._event(tenant, intel._site(tenant, site)["id"], "run", level, text)
        except Exception:   # noqa: BLE001
            pass
    threading.Thread(target=go, daemon=True).start()
    return {"started": True, "say": f"{what} shuru - natija SEO desk par aayega."}


@app.get("/api/seo/intel", dependencies=[Depends(require_key)])
def seo_intel(site: str = "", tenant: str = Depends(current_tenant)):
    """v0.542 SEO INTEL: tracked keywords, AI visibility, Maps grids, DataForSEO status + this month's spend."""
    from .seo import intel
    return _intel_call(intel.view, tenant, site)


@app.post("/api/seo/intel/settings", dependencies=[Depends(require_key)])
def seo_intel_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .seo import intel
    b = dict(body or {})
    return _intel_call(intel.save_settings, tenant, str(b.pop("site", "") or ""), **b)


@app.post("/api/seo/intel/track", dependencies=[Depends(require_key)])
def seo_intel_track(body: dict, tenant: str = Depends(current_tenant)):
    """{keywords: [...], remove: false} - keywords she wants followed in Google (up to 100)."""
    from .seo import intel
    b = body or {}
    kws = b.get("keywords") if isinstance(b.get("keywords"), list) else [x for x in str(b.get("keywords") or "").split("\n")]
    fn = intel.untrack if b.get("remove") else intel.track
    return _intel_call(fn, tenant, kws, str(b.get("site") or ""))


@app.post("/api/seo/intel/ranks/{source}", dependencies=[Depends(require_key)])
async def seo_intel_ranks(source: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """gsc = Search Console positions now (free) | serp = exact Google positions through DataForSEO (her key, costs)."""
    from .seo import intel
    b = body or {}
    site = str(b.get("site") or "")
    if source == "gsc":
        return await asyncio.to_thread(_intel_call, intel.pull_gsc, tenant, site, int(b.get("days") or 28))
    if source == "serp":
        kws = b.get("keywords") if isinstance(b.get("keywords"), list) else None
        return _intel_bg(tenant, site, "Exact Google positions", intel.check_serp, tenant, site, kws)
    raise HTTPException(404, "source: gsc | serp")


@app.post("/api/seo/intel/ai/{action}", dependencies=[Depends(require_key)])
async def seo_intel_ai(action: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """prompts {prompts: [...]} | suggest | run {engines?} | prompt {id, active, remove}"""
    from .seo import intel
    b = body or {}
    site = str(b.get("site") or "")
    if action == "prompts":
        texts = b.get("prompts") if isinstance(b.get("prompts"), list) else str(b.get("prompts") or "").split("\n")
        return _intel_call(intel.add_prompts, tenant, texts, site)
    if action == "prompt":
        return _intel_call(intel.set_prompt, tenant, str(b.get("id") or ""), b.get("active"), bool(b.get("remove")))
    if action == "suggest":
        return await asyncio.to_thread(_intel_call, intel.suggest_prompts, tenant, site)
    if action == "run":
        eng = b.get("engines") if isinstance(b.get("engines"), list) else None
        _intel_call(intel.prompts, tenant, site)
        return _intel_bg(tenant, site, "AI answers check", intel.run_ai, tenant, site, eng)
    raise HTTPException(404, "action: prompts | prompt | suggest | run")


@app.post("/api/seo/intel/maps/{action}", dependencies=[Depends(require_key)])
async def seo_intel_maps(action: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """find {query} -> her place on Google Maps | place {place} | grid {keyword, size, km}"""
    from .seo import intel
    b = body or {}
    site = str(b.get("site") or "")
    if action == "find":
        return await asyncio.to_thread(_intel_call, intel.find_place, tenant, site, str(b.get("query") or ""))
    if action == "place":
        return _intel_call(intel.choose_place, tenant, b.get("place") if isinstance(b.get("place"), dict) else {}, site)
    if action == "grid":
        return _intel_bg(tenant, site, "Maps grid", intel.run_grid, tenant, str(b.get("keyword") or ""), site,
                         b.get("size"), b.get("km"))
    raise HTTPException(404, "action: find | place | grid")


@app.post("/api/seo/intel/dataforseo", dependencies=[Depends(require_key)])
async def seo_intel_dfs_login(body: dict, tenant: str = Depends(current_tenant)):
    """Her DataForSEO login + API password, typed in the app (never in chat): checked free, sealed, never returned."""
    from .seo import dfs, intel
    b = body or {}
    sid = _intel_call(intel._site, tenant, str(b.get("site") or ""))["id"]
    return await asyncio.to_thread(_intel_call, dfs.save_login, tenant, sid, str(b.get("login") or ""), str(b.get("password") or ""))


@app.delete("/api/seo/intel/dataforseo", dependencies=[Depends(require_key)])
def seo_intel_dfs_forget(site: str = "", tenant: str = Depends(current_tenant)):
    from .seo import dfs, intel
    return dfs.forget_login(tenant, _intel_call(intel._site, tenant, site)["id"])


@app.post("/api/seo/intel/dfs/{what}", dependencies=[Depends(require_key)])
async def seo_intel_dfs(what: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """overview {domain} | competitors {domain} | gap {competitor} | backlinks {domain} - DataForSEO, her key, costs."""
    from .seo import dfs, intel
    b = body or {}
    sv = _intel_call(intel._site, tenant, str(b.get("site") or ""))
    dom = str(b.get("domain") or "") or sv["domain"]
    calls = {"overview": lambda: dfs.domain_overview(tenant, sv["id"], dom),
             "competitors": lambda: {"competitors": dfs.competitors(tenant, sv["id"], dom)},
             "gap": lambda: dfs.gap(tenant, sv["id"], sv["domain"], str(b.get("competitor") or "")),
             "backlinks": lambda: dfs.backlinks(tenant, sv["id"], dom)}
    if what not in calls:
        raise HTTPException(404, "what: overview | competitors | gap | backlinks")
    if what == "gap" and not b.get("competitor"):
        raise HTTPException(400, "Which competitor to compare with? (domain)")
    out = await asyncio.to_thread(_intel_call, calls[what])
    return {**out, "spend": dfs.status(tenant, sv["id"])}


@app.post("/api/seo/intel/keywords", dependencies=[Depends(require_key)])
async def seo_intel_keywords(body: dict, tenant: str = Depends(current_tenant)):
    """Keyword ideas with monthly searches: her Google Ads Keyword Planner (free, official) when linked, else DataForSEO."""
    from .seo import intel
    b = body or {}
    seeds = b.get("seeds") if isinstance(b.get("seeds"), list) else [x.strip() for x in str(b.get("seeds") or "").split(",") if x.strip()]
    return await asyncio.to_thread(_intel_call, intel.keyword_research, tenant, seeds, str(b.get("site") or ""))


@app.post("/api/seo/onboard", dependencies=[Depends(require_key)])
def seo_onboard(body: dict, tenant: str = Depends(current_tenant)):
    from .seo import desk

    def lst(v):
        if isinstance(v, str):
            return [x.strip() for x in v.replace("\n", ",").split(",") if x.strip()]
        return [str(x) for x in (v or [])]
    wd = body.get("weekday")
    return _hire_call(desk.onboard, tenant, str(body.get("url") or ""), str(body.get("name") or ""), str(body.get("city") or ""),
                lst(body.get("services")), str(body.get("goal") or ""), str(body.get("customers") or ""), lst(body.get("cities")),
                lst(body.get("competitors")), str(body.get("trust") or "seekh"), int(wd) if wd not in (None, "") else None,
                str(body.get("morning_time") or ""))


@app.get("/api/seo/desk", dependencies=[Depends(require_key)])
def seo_desk(site: str = "", tenant: str = Depends(current_tenant)):
    from .seo import desk
    return _hire_call(desk.desk_view, tenant, site)


@app.post("/api/seo/roadmap/approve", dependencies=[Depends(require_key)])
def seo_roadmap_approve(body: dict | None = None, tenant: str = Depends(current_tenant)):
    from .seo import desk
    return _hire_call(desk.approve_roadmap, tenant, str((body or {}).get("site") or ""))


@app.post("/api/seo/roadmap/item/{item_id}", dependencies=[Depends(require_key)])
def seo_roadmap_item(item_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .seo import desk
    return _hire_call(desk.set_item, tenant, item_id, str(body.get("status") or ""))


@app.post("/api/seo/run/{job}", dependencies=[Depends(require_key)])
def seo_run(job: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """'Run now' on the desk: the job starts in the background and its result lands on the desk / in chat."""
    import threading
    from .employee import hire
    from .seo import desk
    from .seo import service as seo
    if job not in ("first", "hourly", "daily", "weekly", "monthly", "roadmap", "index", "speed_history", "indexnow"):
        raise HTTPException(404, "job: first | hourly | daily | weekly | monthly | roadmap | index | speed_history | indexnow")
    if not hire.is_hired(tenant, desk.KEY):
        raise HTTPException(400, "The SEO Specialist is not hired yet.")
    sid = _hire_call(lambda: seo.sites(tenant) and desk.desk_view(tenant, str((body or {}).get("site") or ""))["site"]["id"])
    if not sid:
        raise HTTPException(400, "First onboarding: the website address.")
    if job == "roadmap":
        return _hire_call(desk.build_roadmap, tenant, sid)
    if job == "indexnow":             # v0.319 her IndexNow key + is the file live on her site
        return _hire_call(desk.indexnow_key, tenant, str((body or {}).get("site") or ""))
    threading.Thread(target=lambda: desk.run_now(tenant, sid, job), daemon=True).start()
    return {"started": job, "site": sid}


# ---------------------------------------------------------------- v0.353 SOCIAL MEDIA MANAGER (employee 2)
def _social_call(fn, *a, **k):
    from .employee import hire
    from .social import desk as social
    try:
        return fn(*a, **k)
    except (hire.HireError, social.SocialError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/social/desk", dependencies=[Depends(require_key)])
def social_desk_view(tenant: str = Depends(current_tenant)):
    from .social import desk as social
    return social.desk_view(tenant)


@app.post("/api/social/onboard", dependencies=[Depends(require_key)])
def social_onboard(body: dict, tenant: str = Depends(current_tenant)):
    from .social import desk as social
    b = body or {}
    langs = b.get("languages")
    if isinstance(langs, str):
        langs = [x.strip() for x in langs.split(",") if x.strip()]
    return _social_call(social.onboard, tenant, business=str(b.get("business") or ""), city=str(b.get("city") or ""),
                        sells=str(b.get("sells") or ""), customers=str(b.get("customers") or ""), goal=str(b.get("goal") or ""),
                        languages=langs, trust=str(b.get("trust") or ""), website=str(b.get("website") or ""),
                        facts=str(b.get("facts") or ""))


@app.get("/api/social/connect/{platform}", dependencies=[Depends(require_key)])
def social_connect(platform: str, tenant: str = Depends(current_tenant)):
    from .social import desk as social
    return {"url": _social_call(social.connect_url, tenant, platform)}


async def _social_callback(request: Request, platform: str) -> HTMLResponse:
    from .social import desk as social
    what = "Instagram" if platform == "instagram" else "Facebook Page"
    q = request.query_params
    if q.get("error") or q.get("error_reason"):
        return _linked_page(what, "social", None, q.get("error_description") or q.get("error_reason") or q.get("error") or "")
    try:
        v = await asyncio.to_thread(social.finish_link, platform, q.get("code", ""), q.get("state", ""))
    except social.SocialError as e:
        return _linked_page(what, "social", None, str(e))
    return _linked_page(what, "social", ", ".join(v["accounts"]))


@app.get("/api/social/instagram/callback")
async def social_instagram_callback(request: Request):
    """Instagram Login sends her back here (this exact URL is saved in Hoola's Meta app)."""
    return await _social_callback(request, "instagram")


@app.get("/api/social/facebook/callback")
async def social_facebook_callback(request: Request):
    """Facebook Login for Business sends her back here (saved in Hoola's Meta app)."""
    return await _social_callback(request, "facebook")


@app.get("/api/social/linkedin/callback")
async def social_linkedin_callback(request: Request):
    """v0.384 LinkedIn sends her back here (this exact URL is saved in Hoola's LinkedIn app as an authorized redirect)."""
    from .social import desk as social
    from .social import linkedin
    q = request.query_params
    if q.get("error"):
        return _linked_page("LinkedIn", "social", None, q.get("error_description") or q.get("error") or "")
    try:
        v = await asyncio.to_thread(linkedin.finish, q.get("code", ""), q.get("state", ""))
    except social.SocialError as e:
        return _linked_page("LinkedIn", "social", None, str(e))
    return _linked_page("LinkedIn", "social", ", ".join(v["accounts"]))


@app.get("/api/social/whatsapp/start", response_class=HTMLResponse)
def social_whatsapp_start(s: str = ""):
    """v0.384 Hoola's page that opens Meta's WhatsApp Embedded Signup (Meta's JS SDK must run on Hoola's own domain)."""
    from .db import MailLinkState, session as _sess
    from .social import wabiz
    with _sess() as ss:
        row = ss.get(MailLinkState, s) if s else None
        ok = row is not None and row.provider == "social_wh"
    if not ok:
        return _linked_page("WhatsApp Business", "social", None, "Yeh link purana ho gaya. Social Desk se dobara Connect dabaiye.")
    return HTMLResponse(wabiz.start_page(s))


@app.get("/api/social/whatsapp/es.js")
def social_whatsapp_js():
    from .social import wabiz
    return Response(wabiz.ES_JS, media_type="application/javascript", headers={"Cache-Control": "no-store"})


@app.post("/api/social/whatsapp/finish")
async def social_whatsapp_finish(body: dict):
    """v0.384 the Embedded Signup page hands over Meta's one-time code + her WABA / number ids. The one-time state is the
    proof it is her (it was made by her Connect tap, 30 minutes, single use)."""
    from .social import desk as social
    from .social import wabiz
    from .social.meta import MetaError
    b = body or {}
    try:
        return await asyncio.to_thread(wabiz.finish, str(b.get("state") or ""), str(b.get("code") or ""),
                                       str(b.get("waba_id") or ""), str(b.get("phone_number_id") or ""))
    except (social.SocialError, MetaError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/social/meta/deletion")
async def social_meta_deletion(request: Request):
    """Meta's data-deletion callback (and deauthorize): a person removed Hoola in their Facebook / Instagram settings -
    every account of theirs and the posts Hoola read are deleted. Meta signs the request with the app secret."""
    from .social import desk as social
    from .social import meta as M
    form = await request.form()
    try:
        r = await asyncio.to_thread(social.meta_deletion, str(form.get("signed_request") or ""))
    except M.MetaError as e:
        raise HTTPException(400, str(e))
    base = get_settings().public_base_url.rstrip("/")
    return {"url": f"{base}/api/social/meta/deletion/{r['confirmation_code']}", "confirmation_code": r["confirmation_code"]}


@app.post("/api/social/meta/deauthorize")
async def social_meta_deauthorize(request: Request):
    return await social_meta_deletion(request)


@app.get("/api/social/meta/deletion/{code}", response_class=HTMLResponse)
def social_meta_deletion_status(code: str):
    import html as _h
    return HTMLResponse(f"<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><body style='font-family:"
                        f"system-ui;padding:32px;max-width:640px;margin:auto'><h2>Hoola: data deletion</h2><p>Request "
                        f"<b>{_h.escape(code[:40])}</b>: the connected Instagram / Facebook accounts and the posts Hoola read "
                        f"from them have been deleted.</p><p>Questions: build@ainewtika.com</p></body>")


@app.post("/api/social/accounts/{aid}/disconnect", dependencies=[Depends(require_key)])
def social_disconnect(aid: str, tenant: str = Depends(current_tenant)):
    from .social import desk as social
    return _social_call(social.disconnect, tenant, aid)


@app.post("/api/social/calendar/approve", dependencies=[Depends(require_key)])
def social_calendar_approve(tenant: str = Depends(current_tenant)):
    from .social import desk as social
    return _social_call(social.approve_calendar, tenant)


@app.post("/api/social/posts/{pid}", dependencies=[Depends(require_key)])
def social_post_edit(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .social import desk as social
    b = body or {}
    return _social_call(social.set_post, tenant, pid, status=str(b.get("status") or ""), caption=b.get("caption"),
                        hook=b.get("hook"), slot=b.get("slot"), hashtags=b.get("hashtags"),
                        platforms=b.get("platforms") if isinstance(b.get("platforms"), list) else None)


@app.post("/api/social/media", dependencies=[Depends(require_key)])
async def social_media_upload(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """v0.355 her photo / video for a post (the bytes must really be a picture / MP4; pictures kept as JPEG)."""
    from .social import publish as SP
    data = await file.read()
    return await asyncio.to_thread(_social_call, SP.add_asset, tenant, data, file.filename or "")


@app.post("/api/social/posts/{pid}/media", dependencies=[Depends(require_key)])
def social_post_media(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .social import publish as SP
    ids = [str(x) for x in (body or {}).get("assets") or []]
    return _social_call(SP.attach, tenant, pid, ids, append=not bool((body or {}).get("replace")))


@app.delete("/api/social/posts/{pid}/media/{aid}", dependencies=[Depends(require_key)])
def social_post_media_remove(pid: str, aid: str, tenant: str = Depends(current_tenant)):
    from .social import publish as SP
    return _social_call(SP.detach, tenant, pid, aid)


@app.post("/api/social/posts/{pid}/poster", dependencies=[Depends(require_key)])
async def social_post_poster(pid: str, tenant: str = Depends(current_tenant)):
    """v0.355 a poster for this post from her Brand kit (final quality, no PROOF mark), attached to the post."""
    from .social import publish as SP
    return await asyncio.to_thread(_social_call, SP.make_poster, tenant, pid)


@app.post("/api/social/posts/{pid}/publish", dependencies=[Depends(require_key)])
def social_post_publish(pid: str, tenant: str = Depends(current_tenant)):
    """v0.355 Publish now = her tap is her OK for exactly this post. Checks first (here, so she sees why at once), then
    sends in the background (a Reel can take a minute while Instagram processes it); the result lands on the post."""
    import threading
    from .social import desk as social
    from .social import publish as SP
    with social.session() as s:
        p = s.get(social.SocialPost, pid)
        if p is None or p.tenant_id != tenant:
            raise HTTPException(404, "This post was not found.")
        bad = SP.problems(p)
    if bad:
        raise HTTPException(400, " ".join(bad))

    def _go():
        try:
            SP.publish_post(tenant, pid, by_tap=True)
        except social.SocialError as e:
            social._event(tenant, "alert", "bad", f"Could not post: {str(e)[:200]}")
    threading.Thread(target=_go, daemon=True).start()
    return {"started": pid}


@app.get("/api/social/media/{aid}")
def social_media_file(aid: str, e: str = "", s: str = ""):
    """The picture / video behind a short-lived signed link (Instagram / Facebook fetch it from here while publishing)."""
    from .social import desk as social
    from .social import publish as SP
    try:
        path, mime = SP.open_signed(aid, e, s)
    except social.SocialError as err:
        raise HTTPException(404, str(err))
    return FileResponse(path, media_type=mime)


@app.post("/api/social/settings", dependencies=[Depends(require_key)])
def social_settings(body: dict, tenant: str = Depends(current_tenant)):
    """v0.369 {paused: bool} pause / resume all posting + automatic replies; {stop: true} = emergency stop (pause + every
    queued post back to draft); {quiet: [23, 7]} = hours when no plan post goes out on its own."""
    from .social import pulse
    b = body or {}
    return _social_call(pulse.set_settings, tenant, paused=b.get("paused") if isinstance(b.get("paused"), bool) else None,
                        quiet=b.get("quiet") if isinstance(b.get("quiet"), list) else None, stop=b.get("stop") is True,
                        reason=str(b.get("reason") or ""),
                        yt_kids=b.get("yt_kids") if isinstance(b.get("yt_kids"), bool) else None,
                        yt_playlist=b.get("yt_playlist") if isinstance(b.get("yt_playlist"), str) else None)


@app.post("/api/social/growth/watch", dependencies=[Depends(require_key)])
def social_growth_watch(body: dict, tenant: str = Depends(current_tenant)):
    """v0.383 the hashtags (<= 5) and competitor usernames (<= 5) she watches."""
    from .social import growth
    b = body or {}
    return _social_call(growth.set_watch, tenant, hashtags=b.get("hashtags") if isinstance(b.get("hashtags"), list) else None,
                        competitors=b.get("competitors") if isinstance(b.get("competitors"), list) else None)


@app.post("/api/social/ugc/{uid}/{action}", dependencies=[Depends(require_key)])
async def social_ugc_action(uid: str, action: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """v0.383 a customer's post that tags her: ask (a polite comment from her account) | permission {granted, proof} |
    repost (credited calendar draft, only after a recorded yes) | ignore."""
    from .social import growth
    b = body or {}
    if action == "ask":
        return await asyncio.to_thread(_social_call, growth.ugc_ask, tenant, uid, str(b.get("text") or ""))
    if action == "permission":
        return _social_call(growth.ugc_permission, tenant, uid, b.get("granted") is True, str(b.get("proof") or ""))
    if action == "repost":
        return await asyncio.to_thread(_social_call, growth.ugc_repost, tenant, uid)
    if action == "ignore":
        return _social_call(growth.ugc_ignore, tenant, uid)
    raise HTTPException(404, "action: ask | permission | repost | ignore")


@app.post("/api/social/creator/check", dependencies=[Depends(require_key)])
async def social_creator_check(body: dict, tenant: str = Depends(current_tenant)):
    """v0.383 a creator / business handle's public numbers + fake-follower signals (+ the ASCI #ad check of a caption)."""
    from .social import growth
    b = body or {}
    return await asyncio.to_thread(_social_call, growth.creator_check, tenant, str(b.get("username") or ""), str(b.get("caption") or ""))


def _gads_call(fn, *a, **k):
    from .ads import gads
    try:
        return fn(*a, **k)
    except gads.GAdsError as e:
        raise HTTPException(400, str(e))


@app.get("/api/social/ytads", dependencies=[Depends(require_key)])
def social_ytads(tenant: str = Depends(current_tenant)):
    """v0.401 YouTube ads (plan Y2): her Google Ads link, ad accounts, drafts."""
    from .ads import gads
    return gads.view(tenant)


@app.get("/api/social/ytads/connect", dependencies=[Depends(require_key)])
def social_ytads_connect(tenant: str = Depends(current_tenant)):
    from .ads import gads
    return {"url": _gads_call(gads.connect_url, tenant)}


@app.post("/api/social/ytads/account", dependencies=[Depends(require_key)])
async def social_ytads_account(body: dict, tenant: str = Depends(current_tenant)):
    """{customer_id} = which of her ad accounts runs the YouTube ads."""
    from .ads import gads
    return await asyncio.to_thread(_gads_call, gads.choose, tenant, str((body or {}).get("customer_id") or ""))


@app.post("/api/social/ytads/read", dependencies=[Depends(require_key)])
async def social_ytads_read(tenant: str = Depends(current_tenant)):
    """Her YouTube campaigns' last 30 days (also into the Ads desk's report rows)."""
    from .ads import gads
    return await asyncio.to_thread(_gads_call, gads.read, tenant)


@app.post("/api/social/ytads/drafts", dependencies=[Depends(require_key)])
def social_ytads_new(body: dict, tenant: str = Depends(current_tenant)):
    """A new Google ad draft {kind: youtube (video_id) | search | pmax, daily, days, final_url...} - stays in Hoola (v0.425)."""
    from .ads import gads
    b = dict(body or {})
    vid, kind = str(b.pop("video_id", "") or ""), str(b.pop("kind", "") or "youtube")
    return _gads_call(gads.new_draft, tenant, vid, kind, **b)


@app.post("/api/social/ytads/ideas", dependencies=[Depends(require_key)])
async def social_ytads_ideas(body: dict, tenant: str = Depends(current_tenant)):
    """v0.425 Google Keyword Planner ideas {seeds: [...], url, cities: [...], lang} - read-only, nothing is created."""
    from .ads import gads
    b = body or {}
    seeds = b.get("seeds") if isinstance(b.get("seeds"), list) else []
    cities = b.get("cities") if isinstance(b.get("cities"), list) else []
    return await asyncio.to_thread(_gads_call, gads.keyword_ideas, tenant, seeds, str(b.get("url") or ""), cities,
                                   str(b.get("lang") or "en"))


@app.post("/api/social/ytads/drafts/{did}", dependencies=[Depends(require_key)])
def social_ytads_edit(did: str, body: dict, tenant: str = Depends(current_tenant)):
    from .ads import gads
    return _gads_call(gads.set_draft, tenant, did, **(body or {}))


@app.post("/api/social/ytads/drafts/{did}/{action}", dependencies=[Depends(require_key)])
async def social_ytads_action(did: str, action: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """check (Google validates, free) | create (in her account, PAUSED) | start (her tap + confirm: spends) | pause."""
    from .ads import gads
    b = body or {}
    fn = {"check": gads.check, "create": gads.create, "pause": gads.pause}.get(action)
    if action == "start":
        return await asyncio.to_thread(_gads_call, gads.start, tenant, did, b.get("confirm") is True)
    if fn is None:
        raise HTTPException(404, "action: check | create | start | pause")
    return await asyncio.to_thread(_gads_call, fn, tenant, did)


def _mads_call(fn, *a, **k):
    from .ads import metaads
    try:
        return fn(*a, **k)
    except metaads.MetaAdsError as e:
        raise HTTPException(400, str(e))


@app.get("/api/ads/meta/connect", dependencies=[Depends(require_key)])
def ads_meta_connect(tenant: str = Depends(current_tenant)):
    """v0.417 META ADS (A1): Facebook Login with ads_management + ads_read on Hoola's Meta app (replaces the pasted token)."""
    from .ads import metaads
    return {"url": _mads_call(metaads.connect_url, tenant)}


@app.get("/api/ads/meta/callback")
async def ads_meta_callback(request: Request):
    """Facebook Login sends her back here (this exact URL is saved in the HOOLA Meta app's Valid OAuth Redirect URIs)."""
    from .ads import metaads
    q = request.query_params
    if q.get("error") or q.get("error_reason"):
        return _linked_page("Facebook ads", "ads", None, q.get("error_description") or q.get("error_reason") or q.get("error") or "")
    try:
        v = await asyncio.to_thread(metaads.finish_link, q.get("code", ""), q.get("state", ""))
    except metaads.MetaAdsError as e:
        return _linked_page("Facebook ads", "ads", None, str(e))
    return _linked_page("Facebook ads", "ads", ", ".join(v["accounts"][:3]) or "No ad account found in this login")


@app.get("/api/ads/metaads", dependencies=[Depends(require_key)])
def ads_metaads(tenant: str = Depends(current_tenant)):
    """Her Facebook login, ad accounts, Pages and Facebook / Instagram ad drafts."""
    from .ads import metaads
    return metaads.view(tenant)


@app.post("/api/ads/metaads/account", dependencies=[Depends(require_key)])
def ads_metaads_account(body: dict, tenant: str = Depends(current_tenant)):
    """{account: act_..., page: <page id>} = which ad account pays and which Page the ads run as."""
    from .ads import metaads
    b = body or {}
    return _mads_call(metaads.choose, tenant, str(b.get("account") or ""), str(b.get("page") or ""))


@app.get("/api/ads/metaads/posts", dependencies=[Depends(require_key)])
async def ads_metaads_posts(tenant: str = Depends(current_tenant)):
    """Her Page's recent posts (to Boost one)."""
    from .ads import metaads
    return {"posts": await asyncio.to_thread(_mads_call, metaads.page_posts, tenant)}


@app.post("/api/ads/metaads/drafts", dependencies=[Depends(require_key)])
def ads_metaads_new(body: dict, tenant: str = Depends(current_tenant)):
    """A new Facebook / Instagram ad draft {goal: whatsapp|messenger|instagram|website|boost, ...} - stays in Hoola."""
    from .ads import metaads
    b = dict(body or {})
    return _mads_call(metaads.new_draft, tenant, str(b.pop("goal", "") or "whatsapp"), **b)


@app.post("/api/ads/metaads/drafts/{did}", dependencies=[Depends(require_key)])
def ads_metaads_edit(did: str, body: dict, tenant: str = Depends(current_tenant)):
    from .ads import metaads
    return _mads_call(metaads.set_draft, tenant, did, **(body or {}))


@app.post("/api/ads/metaads/drafts/{did}/{action}", dependencies=[Depends(require_key)])
async def ads_metaads_action(did: str, action: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """check (Meta validates, free) | create (in her account, all PAUSED) | start (her tap + confirm: spends) | pause."""
    from .ads import metaads
    b = body or {}
    fn = {"check": metaads.check, "create": metaads.create, "pause": metaads.pause}.get(action)
    if action == "start":
        return await asyncio.to_thread(_mads_call, metaads.start, tenant, did, b.get("confirm") is True)
    if fn is None:
        raise HTTPException(404, "action: check | create | start | pause")
    return await asyncio.to_thread(_mads_call, fn, tenant, did)


@app.get("/api/social/inbox", dependencies=[Depends(require_key)])
def social_inbox_view(box: str = "needs", tenant: str = Depends(current_tenant)):
    """v0.368 her comments + DMs: needs (waiting for her) | leads | complaints | done."""
    from .social import inbox
    return inbox.view(tenant, box if box in ("needs", "leads", "complaints", "done") else "needs")


@app.post("/api/social/inbox/{item}/reply", dependencies=[Depends(require_key)])
async def social_inbox_reply(item: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap: the reply goes out now (her text, or the draft as it stands). DMs only inside Meta's 24-hour window."""
    from .social import inbox
    return await asyncio.to_thread(_social_call, inbox.reply, tenant, item, str((body or {}).get("text") or ""))


@app.post("/api/social/inbox/{item}/hide", dependencies=[Depends(require_key)])
async def social_inbox_hide(item: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """Hide (or {hidden: false} = show again) a comment. Hoola never deletes."""
    from .social import inbox
    hidden = (body or {}).get("hidden", True) is not False
    return await asyncio.to_thread(_social_call, inbox.hide, tenant, item, hidden)


@app.post("/api/social/inbox/{item}", dependencies=[Depends(require_key)])
def social_inbox_set(item: str, body: dict, tenant: str = Depends(current_tenant)):
    """Ignore / bring back ({status: ignored|drafted}) or edit the draft ({draft})."""
    from .social import inbox
    b = body or {}
    return _social_call(inbox.set_item, tenant, item, status=str(b.get("status") or ""),
                        draft=b.get("draft") if isinstance(b.get("draft"), str) else None)


@app.post("/api/social/run/{job}", dependencies=[Depends(require_key)])
def social_run(job: str, tenant: str = Depends(current_tenant)):
    """'Run now' on the desk: first check / refresh numbers / weekly note / rewrite the calendar draft (background)."""
    import threading
    from .employee import hire
    from .social import desk as social
    if job not in ("first", "hourly", "daily", "weekly", "plan", "publish", "inbox", "morning", "monthly", "growth"):
        raise HTTPException(404, "job: first | hourly | daily | weekly | plan | publish | inbox | morning | monthly | growth")
    if not hire.is_hired(tenant, social.KEY):
        raise HTTPException(400, "The Social Media Manager is not hired yet.")
    if not social.accounts(tenant):
        raise HTTPException(400, "First connect Instagram or a Facebook Page.")
    threading.Thread(target=lambda: social.run_now(tenant, job), daemon=True).start()
    return {"started": job}


async def _finish_seo_link(request: Request) -> HTMLResponse:
    from .seo import service as seo
    if request.query_params.get("error"):
        return _linked_page("Search Console", "seo", None, request.query_params["error"])
    try:
        v = await asyncio.to_thread(seo.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except seo.SeoError as e:
        return _linked_page("Search Console", "seo", None, str(e))
    return _linked_page("Search Console", "seo", v["address"])


@app.get("/api/seo/summary", dependencies=[Depends(require_key)])
def seo_summary(site: str = "", tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    if not seo.sites(tenant):
        return {"site": None, "gsc": seo.gsc_status(tenant)}
    return _seo(seo.summary, tenant, site)


@app.post("/api/seo/site", dependencies=[Depends(require_key)])
def seo_site(body: dict, tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    biz = {k: body.get(k) for k in ("city", "state", "street", "pin", "phone", "schema_type", "hours", "price_range")}
    return _seo(seo.save_site, tenant, str(body.get("url") or ""), str(body.get("name") or ""), str(body.get("site") or ""),
                body.get("services"), **biz)


@app.get("/api/seo/tasks", dependencies=[Depends(require_key)])
def seo_tasks(site: str = "", status: str = "open", tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    return {"tasks": _seo(seo.tasks, tenant, site, status)}


@app.post("/api/seo/tasks/{tid}", dependencies=[Depends(require_key)])
def seo_task(tid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    return _seo(seo.close_task, tenant, tid, str(body.get("status") or "done"))


@app.get("/api/seo/drafts", dependencies=[Depends(require_key)])
def seo_drafts(site: str = "", tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    return {"drafts": _seo(seo.drafts, tenant, site)}


@app.post("/api/seo/drafts/{did}", dependencies=[Depends(require_key)])
def seo_draft_ok(did: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her Haan (only from her tap): the draft is final; she puts it on her site / profile."""
    from .seo import service as seo
    return _seo(seo.approve_draft, tenant, did, str(body.get("text") or ""))


@app.post("/api/seo/{action}", dependencies=[Depends(require_key)])
def seo_act(action: str, body: dict, tenant: str = Depends(current_tenant)):
    """audit | speed | performance | brief | schema | gbp_post | review_reply | report | keywords"""
    from .seo import service as seo
    site, conv = str(body.get("site") or ""), str(body.get("conversation_id") or "")
    if action == "audit":
        return _seo(seo.crawl, tenant, site, int(body.get("max_pages") or 25), conv)
    if action == "speed":
        return _seo(seo.pagespeed, tenant, site, str(body.get("url") or ""), str(body.get("strategy") or "mobile"))
    if action == "performance":
        return _seo(seo.performance, tenant, site, int(body.get("days") or 28), conv)
    if action == "brief":
        return _seo(seo.content_brief, tenant, str(body.get("keyword") or ""), site, conv)
    if action == "schema":
        return _seo(seo.schema_draft, tenant, site, conv)
    if action == "gbp_post":
        return _seo(seo.gbp_post, tenant, str(body.get("topic") or ""), str(body.get("offer") or ""), site, conv)
    if action == "review_reply":
        return _seo(seo.review_reply, tenant, str(body.get("review") or ""), int(body.get("stars") or 0), str(body.get("reviewer") or ""), site, conv)
    if action == "report":
        return _seo(seo.report_file, tenant, site, conv)
    if action == "keywords":
        return _seo(seo.keyword_plan, tenant, site)
    raise HTTPException(404, "unknown action")


@app.get("/api/seo/gsc/link", dependencies=[Depends(require_key)])
def seo_gsc_link(tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    try:
        return {"url": seo.start_link(tenant)}
    except seo.SeoError as e:
        raise HTTPException(503, str(e))


@app.delete("/api/seo/gsc", dependencies=[Depends(require_key)])
def seo_gsc_remove(tenant: str = Depends(current_tenant)):
    from .seo import service as seo
    from .db import session as _ses
    with _ses() as s:
        g = s.get(seo.SeoGoogle, tenant)
        if g:
            s.delete(g)
    return seo.gsc_status(tenant)


# ---------------------------------------------------------------- v0.98 Bima Sahayak (insurance agent)
def _ins(fn, *a, **k):
    from .insure import service as ins
    try:
        return fn(*a, **k)
    except (ins.InsError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/insurance/summary", dependencies=[Depends(require_key)])
def insurance_summary(days: int = 15, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return {"book": ins.book(tenant), "renewals": ins.renewals(tenant, days), "claims": ins.claims(tenant),
            "birthdays": ins.birthdays(tenant, 7)["birthdays"], "settings": ins.settings(tenant)}


@app.get("/api/insurance/clients", dependencies=[Depends(require_key)])
def insurance_clients(tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return {"clients": ins.clients(tenant)}


@app.post("/api/insurance/clients", dependencies=[Depends(require_key)])
def insurance_client_save(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _ins(ins.save_client, tenant, g("name"), g("client"), g("phone"), g("dob"), g("gender"), g("city"), body.get("metro"),
                body.get("income"), body.get("family"), body.get("liabilities"), body.get("goals"), body.get("savings"),
                body.get("whatsapp_ok"), g("notes"))


@app.get("/api/insurance/clients/{cid}/needs", dependencies=[Depends(require_key)])
def insurance_needs(cid: str, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.needs, tenant, cid)


@app.get("/api/insurance/policies", dependencies=[Depends(require_key)])
def insurance_policies(client: str = "", state: str = "", tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return {"policies": _ins(ins.policies, tenant, client, state)}


@app.post("/api/insurance/policies", dependencies=[Depends(require_key)])
def insurance_policy_save(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    g = lambda k: str(body.get(k) or "")  # noqa: E731
    return _ins(ins.save_policy, tenant, g("client"), g("insurer"), g("plan"), g("type"), g("number"), g("start"), g("mode"),
                body.get("premium"), body.get("cover"), g("next_due"), nominee=g("nominee"), commission_pct=body.get("commission_pct"),
                group=body.get("group"), members=body.get("members"), pay_link=g("pay_link"), policy=g("policy"), status=g("status"))


@app.post("/api/insurance/policies/{pid}/paid", dependencies=[Depends(require_key)])
def insurance_paid(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.premium_paid, tenant, pid, str(body.get("paid_on") or ""))


@app.post("/api/insurance/policies/{pid}/reminded", dependencies=[Depends(require_key)])
def insurance_reminded(pid: str, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.mark_reminded, tenant, pid)


@app.post("/api/insurance/import", dependencies=[Depends(require_key)])
async def insurance_import(file: UploadFile = File(...), insurer: str = Form(""), tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    data = await file.read()
    return _ins(ins.import_policies, tenant, "", data, file.filename or "renewals.csv", insurer)


@app.get("/api/insurance/reminders", dependencies=[Depends(require_key)])
def insurance_reminders(days: int = 15, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.reminder_drafts, tenant, days)


@app.post("/api/insurance/advice/{aid}", dependencies=[Depends(require_key)])
def insurance_advice(aid: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her Haan (only from her tap) turns the recommendation into a client message draft she sends."""
    from .insure import service as ins
    return _ins(ins.approve_advice, tenant, aid, bool(body.get("approve", True)))


@app.post("/api/insurance/claims", dependencies=[Depends(require_key)])
def insurance_claim_new(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.start_claim, tenant, str(body.get("policy") or ""), str(body.get("kind") or "other"), str(body.get("event_on") or ""),
                body.get("amount"))


@app.post("/api/insurance/claims/{cid}", dependencies=[Depends(require_key)])
def insurance_claim_update(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.update_claim, tenant, cid, body.get("have"), str(body.get("status") or ""), str(body.get("insurer_ref") or ""),
                str(body.get("filed_on") or ""), body.get("settled_amount"), str(body.get("note") or ""))


@app.post("/api/insurance/book_file", dependencies=[Depends(require_key)])
def insurance_book_file(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    return _ins(ins.book_file, tenant, str(body.get("conversation_id") or ""))


@app.post("/api/insurance/settings", dependencies=[Depends(require_key)])
def insurance_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .insure import service as ins
    keys = ("agent_name", "agent_code", "remind_days", "morning_time", "enabled")
    return _ins(ins.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.96 Auditor's Assistant
def _aud(fn, *a, **k):
    from .audit import service as aud
    try:
        return fn(*a, **k)
    except (aud.AuditError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/audit/engagements", dependencies=[Depends(require_key)])
def audit_engagements(tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return {"engagements": aud.engagements(tenant)}


@app.post("/api/audit/engagements", dependencies=[Depends(require_key)])
def audit_engagement_new(body: dict, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.new_engagement, tenant, str(body.get("client") or ""), str(body.get("kind") or "statutory"), str(body.get("fy") or ""),
                str(body.get("entity") or "firm"), body.get("approval_limit"))


@app.get("/api/audit/engagements/{eid}", dependencies=[Depends(require_key)])
def audit_engagement_get(eid: str, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.get, tenant, eid)


@app.post("/api/audit/engagements/{eid}/upload/{what}", dependencies=[Depends(require_key)])
async def audit_upload(eid: str, what: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """what = tb | tb_prev | daybook"""
    from .audit import service as aud
    data = await file.read()
    if what in ("tb", "tb_prev"):
        return _aud(aud.import_tb, tenant, eid, "", data, file.filename or "tb.xlsx", what == "tb_prev")
    if what == "daybook":
        return _aud(aud.import_daybook, tenant, eid, "", data, file.filename or "daybook.xlsx")
    raise HTTPException(404, "tb | tb_prev | daybook")


@app.get("/api/audit/engagements/{eid}/findings", dependencies=[Depends(require_key)])
def audit_findings(eid: str, status: str = "", tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return {"findings": _aud(aud.findings, tenant, eid, status)}


@app.post("/api/audit/engagements/{eid}/{action}", dependencies=[Depends(require_key)])
def audit_act(eid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """run | materiality | facts | sample | confirmations | approve_confirmations (her Haan, only from her tap) | queries |
    asked | rep_letter | workpapers | letters | samples"""
    from .audit import service as aud
    conv = str(body.get("conversation_id") or "")
    if action == "run":
        return _aud(aud.run_tests, tenant, eid, conv)
    if action == "materiality":
        return _aud(aud.plan_materiality, tenant, eid, str(body.get("benchmark") or ""), body.get("pct"), str(body.get("risk") or "normal"))
    if action == "facts":
        keys = ("turnover", "cash_receipts_pct", "cash_payments_pct", "profession", "paid_up", "holding_or_sub", "status", "approval_limit")
        return _aud(aud.set_facts, tenant, eid, **{k: body[k] for k in keys if k in body})
    if action == "sample":
        return _aud(aud.make_sample, tenant, eid, str(body.get("population") or ""), str(body.get("method") or "mus"),
                    int(body.get("size") or 25), int(body.get("confidence") or 95))
    if action == "samples":
        return {"samples": _aud(aud.samples, tenant, eid)}
    if action == "confirmations":
        return _aud(aud.make_confirmations, tenant, eid, int(body.get("top") or 10), body.get("min_amount"))
    if action == "letters":
        return _aud(aud.confirmation_letters, tenant, eid)
    if action == "approve_confirmations":
        return _aud(aud.approve_confirmations, tenant, eid, bool(body.get("approve", True)))
    if action == "queries":
        return _aud(aud.query_list, tenant, eid)
    if action == "asked":
        return _aud(aud.mark_asked, tenant, eid)
    if action == "rep_letter":
        return _aud(aud.rep_letter, tenant, eid)
    if action == "workpapers":
        return _aud(aud.workpapers, tenant, eid, conv)
    raise HTTPException(404, "unknown action")


@app.post("/api/audit/findings/{fid}", dependencies=[Depends(require_key)])
def audit_finding_close(fid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.close_finding, tenant, fid, str(body.get("status") or ""), str(body.get("note") or ""), bool(body.get("remember")))


@app.post("/api/audit/samples/{sid}", dependencies=[Depends(require_key)])
def audit_sample_result(sid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.sample_result, tenant, sid, str(body.get("status") or ""), str(body.get("note") or ""))


@app.post("/api/audit/confirms/{cid}", dependencies=[Depends(require_key)])
def audit_confirm_reply(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .audit import service as aud
    return _aud(aud.confirmation_reply, tenant, cid, body.get("amount"), str(body.get("note") or ""))


# ---------------------------------------------------------------- v0.95 Financial Analyst
def _fin(fn, *a, **k):
    from .analyst import service as fin
    try:
        return fn(*a, **k)
    except (fin.FinError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/finance/books", dependencies=[Depends(require_key)])
async def finance_books(file: UploadFile = File(...), label: str = Form(""), start: str = Form(...), end: str = Form(...),
                        tenant: str = Depends(current_tenant)):
    """Tally trial balance / P&L / balance sheet export -> statements, ratios, insights."""
    from .analyst import service as fin
    data = await file.read()
    return _fin(fin.import_books, tenant, label, start, end, "", data, file.filename or "tb.xlsx")


@app.post("/api/finance/bank", dependencies=[Depends(require_key)])
async def finance_bank(file: UploadFile = File(...), account: str = Form(""), tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    data = await file.read()
    return _fin(fin.import_bank, tenant, "", data, file.filename or "statement.csv", account)


@app.get("/api/finance/analysis", dependencies=[Depends(require_key)])
def finance_analysis(snapshot: str = "", tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.analyse, tenant, snapshot)


@app.get("/api/finance/periods", dependencies=[Depends(require_key)])
def finance_periods(tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return {"periods": fin.snapshots(tenant)}


@app.get("/api/finance/cash", dependencies=[Depends(require_key)])
def finance_cash(tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.cash, tenant)


@app.get("/api/finance/aging", dependencies=[Depends(require_key)])
def finance_aging(kind: str = "receivable", tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.aging, tenant, "payable" if kind == "payable" else "receivable")


@app.post("/api/finance/items", dependencies=[Depends(require_key)])
def finance_item_add(body: dict, tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.add_item, tenant, str(body.get("kind") or "receivable"), str(body.get("party") or ""), body.get("amount"),
                str(body.get("bill") or ""), str(body.get("bill_date") or ""), body.get("credit_days"), str(body.get("phone") or ""),
                bool(body.get("msme")), body.get("agreed_days"))


@app.post("/api/finance/loan_check", dependencies=[Depends(require_key)])
def finance_loan_check(body: dict, tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return _fin(fin.loan_check, tenant, body.get("amount"), body.get("rate") or 10, float(body.get("years") or 5),
                body.get("projected_turnover"), str(body.get("snapshot") or ""))


@app.post("/api/finance/act/{action}", dependencies=[Depends(require_key)])
def finance_act(action: str, body: dict, tenant: str = Depends(current_tenant)):
    """report | share (her Haan, only from her tap) | reminders | advance_tax"""
    from .analyst import service as fin
    if action == "report":
        return _fin(fin.report, tenant, str(body.get("snapshot") or ""), str(body.get("conversation_id") or ""))
    if action == "share":
        return _fin(fin.approve_share, tenant, str(body.get("snapshot") or ""), bool(body.get("approve")), str(body.get("to") or ""))
    if action == "reminders":
        return _fin(fin.reminder_drafts, tenant)
    if action == "advance_tax":
        return _fin(fin.advance_tax, tenant, body.get("profit"), str(body.get("snapshot") or ""))
    raise HTTPException(404, "report | share | reminders | advance_tax")


@app.get("/api/finance/settings", dependencies=[Depends(require_key)])
def finance_settings_get(tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    return fin.settings(tenant)


@app.put("/api/finance/settings", dependencies=[Depends(require_key)])
def finance_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .analyst import service as fin
    keys = ("business", "entity", "budget", "tax_paid", "morning_time", "enabled")
    return _fin(fin.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.94 Payroll Officer
def _pay(fn, *a, **k):
    from .payroll import service as pay
    try:
        return fn(*a, **k)
    except (pay.PayError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/payroll/today", dependencies=[Depends(require_key)])
def payroll_today(tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return pay.calendar(tenant)


@app.get("/api/payroll/employees", dependencies=[Depends(require_key)])
def payroll_employees(all: bool = False, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return {"employees": pay.employees(tenant, not all)}


@app.post("/api/payroll/employees", dependencies=[Depends(require_key)])
def payroll_employee_save(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    keys = ("phone", "gender", "dob", "doj", "designation", "pay", "gross", "uan", "esic_ip", "pan", "account", "ifsc", "regime",
            "declared", "prev_income", "prev_tds", "pf_member", "eps_member", "pf_on_full", "fixed_term", "alias")
    return _pay(pay.save_employee, tenant, str(body.get("name") or ""), str(body.get("employee") or ""), **{k: body[k] for k in keys if k in body})


@app.post("/api/payroll/attendance", dependencies=[Depends(require_key)])
def payroll_attendance(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.set_attendance, tenant, str(body.get("period") or ""), body.get("entries") or [])


@app.post("/api/payroll/attendance/import", dependencies=[Depends(require_key)])
async def payroll_attendance_import(file: UploadFile = File(...), period: str = Form(...), tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    data = await file.read()
    return _pay(pay.import_attendance, tenant, period, data, file.filename or "attendance.csv")


@app.post("/api/payroll/advances", dependencies=[Depends(require_key)])
def payroll_advance(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.add_advance, tenant, str(body.get("employee") or ""), body.get("amount"), body.get("emi"), str(body.get("given_on") or ""),
                str(body.get("note") or ""))


@app.get("/api/payroll/runs", dependencies=[Depends(require_key)])
def payroll_runs(tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return {"runs": pay.runs(tenant)}


@app.post("/api/payroll/runs", dependencies=[Depends(require_key)])
def payroll_run_make(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.prepare_run, tenant, str(body.get("period") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/payroll/runs/{run_id}", dependencies=[Depends(require_key)])
def payroll_run_get(run_id: str, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.get_run, tenant, run_id)


@app.post("/api/payroll/runs/{run_id}/{action}", dependencies=[Depends(require_key)])
def payroll_run_act(run_id: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """decide (her Haan, only from her tap) | files | paid (after she paid) | drafts"""
    from .payroll import service as pay
    conv = str(body.get("conversation_id") or "")
    if action == "decide":
        return _pay(pay.decide, tenant, run_id, bool(body.get("approve")), str(body.get("note") or ""), conv)
    if action == "files":
        return _pay(pay.files, tenant, run_id, conv)
    if action == "paid":
        return _pay(pay.mark_paid, tenant, run_id, str(body.get("paid_on") or ""), "owner", conv)
    if action == "drafts":
        return _pay(pay.payslip_drafts, tenant, run_id)
    raise HTTPException(404, "decide | files | paid | drafts")


@app.post("/api/payroll/leaving", dependencies=[Depends(require_key)])
def payroll_leaving(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return _pay(pay.full_and_final, tenant, str(body.get("employee") or ""), str(body.get("last_day") or ""), body.get("leave_days") or 0,
                body.get("notice_recovery") or 0, body.get("other") or 0, bool(body.get("death_or_disability")),
                str(body.get("conversation_id") or ""))


@app.get("/api/payroll/settings", dependencies=[Depends(require_key)])
def payroll_settings_get(tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    return pay.settings(tenant)


@app.put("/api/payroll/settings", dependencies=[Depends(require_key)])
def payroll_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .payroll import service as pay
    keys = ("enabled", "company", "state", "pf_on", "pf_code", "esi_on", "esi_code", "tan", "min_wage", "days_basis", "pay_account",
            "pay_ifsc", "morning_time")
    return _pay(pay.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.93 GST Sahayak
def _gst(fn, *a, **k):
    from .gstp import service as gstp
    try:
        return fn(*a, **k)
    except (gstp.GstError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/gst/today", dependencies=[Depends(require_key)])
def gst_today(tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return gstp.calendar(tenant)


@app.get("/api/gst/clients", dependencies=[Depends(require_key)])
def gst_clients(tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return {"clients": gstp.clients(tenant)}


@app.post("/api/gst/clients", dependencies=[Depends(require_key)])
def gst_client_save(body: dict, tenant: str = Depends(current_tenant)):
    """Add / update a client. A portal password is never accepted or stored."""
    from .gstp import service as gstp
    if any(k in body for k in ("password", "portal_password", "otp")):
        raise HTTPException(400, "Hoola does not keep the portal password / OTP.")
    return _gst(gstp.add_client, tenant, str(body.get("name") or ""), str(body.get("gstin") or ""), str(body.get("scheme") or ""),
                body.get("aato"), str(body.get("portal_user") or ""), str(body.get("login_as") or ""), str(body.get("contact_name") or ""),
                str(body.get("contact_phone") or ""), body.get("fee"), str(body.get("notes") or ""), body.get("einvoice"),
                str(body.get("client") or ""))


@app.get("/api/gst/bills", dependencies=[Depends(require_key)])
def gst_bills(client: str, period: str = "", direction: str = "", tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return {"bills": _gst(gstp.docs, tenant, client, period, direction)}


@app.post("/api/gst/bills", dependencies=[Depends(require_key)])
def gst_bill_add(body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    line = {k: body.get(k) for k in ("txval", "rate", "hsn", "desc", "qty", "uqc", "igst", "cgst", "sgst", "cess")}
    return _gst(gstp.add_doc, tenant, str(body.get("client") or ""), str(body.get("direction") or "out"), str(body.get("number") or ""),
                body.get("date"), str(body.get("party_gstin") or ""), str(body.get("party_name") or ""), str(body.get("pos") or ""),
                body.get("items"), str(body.get("kind") or "inv"), bool(body.get("rcm")), str(body.get("irn") or ""),
                str(body.get("category") or ""), str(body.get("paid_on") or ""), body.get("value"), "app", bool(body.get("replace")), **line)


@app.delete("/api/gst/bills/{bill_id}", dependencies=[Depends(require_key)])
def gst_bill_delete(bill_id: str, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return _gst(gstp.delete_doc, tenant, bill_id)


@app.post("/api/gst/import", dependencies=[Depends(require_key)])
async def gst_import(file: UploadFile = File(...), client: str = Form(...), direction: str = Form("out"), period: str = Form(""),
                     tenant: str = Depends(current_tenant)):
    """A sales / purchase register (Tally / Vyapar / Excel / CSV)."""
    from .gstp import service as gstp
    data = await file.read()
    return _gst(gstp.import_register, tenant, client, direction, "", data, file.filename or "register.csv", period)


@app.post("/api/gst/2b", dependencies=[Depends(require_key)])
async def gst_2b(file: UploadFile = File(...), client: str = Form(...), period: str = Form(...), tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    data = await file.read()
    return _gst(gstp.import_2b, tenant, client, period, "", data, file.filename or "gstr2b.json")


@app.get("/api/gst/reconcile", dependencies=[Depends(require_key)])
def gst_reconcile(client: str, period: str, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return _gst(gstp.reconcile, tenant, client, period)


@app.post("/api/gst/ims", dependencies=[Depends(require_key)])
def gst_ims(body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    if body.get("apply"):
        return _gst(gstp.ims_apply, tenant, str(body.get("client") or ""), str(body.get("period") or ""), str(body.get("conversation_id") or ""))
    return _gst(gstp.ims_decide, tenant, str(body.get("client") or ""), str(body.get("period") or ""), body.get("decisions") or {})


@app.get("/api/gst/returns", dependencies=[Depends(require_key)])
def gst_returns(client: str = "", period: str = "", status: str = "", tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return {"returns": _gst(gstp.returns, tenant, client, period, status)}


@app.post("/api/gst/returns", dependencies=[Depends(require_key)])
def gst_prepare(body: dict, tenant: str = Depends(current_tenant)):
    """Prepare gstr1 | gstr3b | cmp08 for a client + period."""
    from .gstp import service as gstp
    kind, c, p, conv = str(body.get("kind") or "gstr1"), str(body.get("client") or ""), str(body.get("period") or ""), str(body.get("conversation_id") or "")
    if kind == "gstr1":
        return _gst(gstp.prepare_gstr1, tenant, c, p, conv)
    if kind == "gstr3b":
        return _gst(gstp.prepare_gstr3b, tenant, c, p, body.get("other_reversal"), conv)
    if kind == "cmp08":
        return _gst(gstp.prepare_cmp08, tenant, c, p, body.get("turnover"), conv)
    raise HTTPException(400, "kind: gstr1 | gstr3b | cmp08")


@app.get("/api/gst/returns/{return_id}", dependencies=[Depends(require_key)])
def gst_return(return_id: str, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return _gst(gstp.get_return, tenant, return_id)


@app.get("/api/gst/returns/{return_id}/gstr1.json", dependencies=[Depends(require_key)])
def gst_return_json(return_id: str, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    from .db import session as _sess
    with _sess() as s:
        r = s.get(gstp.GstReturn, return_id)
        if not r or r.tenant_id != tenant or not r.portal_json:
            raise HTTPException(404, "No JSON")
        return Response(r.portal_json, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="GSTR1_{r.period}.json"'})


@app.post("/api/gst/returns/{return_id}/{action}", dependencies=[Depends(require_key)])
def gst_return_act(return_id: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """decide (her Haan, only from her tap) | file | filed | json | tax_message"""
    from .gstp import service as gstp
    conv = str(body.get("conversation_id") or "")
    if action == "decide":
        return _gst(gstp.decide, tenant, return_id, bool(body.get("approve")), str(body.get("note") or ""), conv)
    if action == "file":
        return _gst(gstp.file_return, tenant, return_id, conv)
    if action == "filed":
        return _gst(gstp.mark_filed, tenant, return_id, str(body.get("arn") or ""), str(body.get("filed_on") or ""), "owner", conv)
    if action == "json":
        return _gst(gstp.return_file, tenant, return_id, conv)
    if action == "tax_message":
        return _gst(gstp.tax_message_draft, tenant, return_id)
    raise HTTPException(404, "decide | file | filed | json | tax_message")


@app.post("/api/gst/drafts", dependencies=[Depends(require_key)])
def gst_drafts(body: dict, tenant: str = Depends(current_tenant)):
    """ask_bills (to the client) | suppliers (missing in 2B)"""
    from .gstp import service as gstp
    if str(body.get("kind")) == "suppliers":
        return _gst(gstp.supplier_drafts, tenant, str(body.get("client") or ""), str(body.get("period") or ""))
    return _gst(gstp.client_request_draft, tenant, str(body.get("client") or ""), str(body.get("period") or ""))


@app.get("/api/gst/notices", dependencies=[Depends(require_key)])
def gst_notices(status: str = "open", tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return {"notices": gstp.notices(tenant, status)}


@app.post("/api/gst/notices", dependencies=[Depends(require_key)])
def gst_notice_add(body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return _gst(gstp.add_notice, tenant, str(body.get("client") or ""), str(body.get("form") or ""), str(body.get("issued_on") or ""),
                str(body.get("ref") or ""), str(body.get("text") or ""), body.get("amount"), str(body.get("due_on") or ""))


@app.post("/api/gst/notices/{notice_id}/{action}", dependencies=[Depends(require_key)])
def gst_notice_act(notice_id: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    if action == "draft":
        return _gst(gstp.notice_draft, tenant, notice_id)
    if action == "status":
        return _gst(gstp.notice_status, tenant, notice_id, str(body.get("status") or ""))
    raise HTTPException(404, "draft | status")


@app.get("/api/gst/settings", dependencies=[Depends(require_key)])
def gst_settings_get(tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    return gstp.settings(tenant)


@app.put("/api/gst/settings", dependencies=[Depends(require_key)])
def gst_settings_put(body: dict, tenant: str = Depends(current_tenant)):
    from .gstp import service as gstp
    keys = ("enabled", "practitioner", "enrolment", "morning_time", "remind_days")
    return _gst(gstp.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.99 Telecaller Sahayak (a person makes every call)
def _tele(fn, *a, **k):
    from .telecall import service as tele
    try:
        return fn(*a, **k)
    except tele.TeleError as e:
        raise HTTPException(400, str(e))


@app.get("/api/telecall", dependencies=[Depends(require_key)])
def tele_all(assigned: str = "", tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return {"list": tele.call_list(tenant, 0, assigned), "report": tele.report(tenant, 1), "settings": tele.settings(tenant),
            "outcomes": {k: v[0] for k, v in tele.OUTCOMES.items()}, "purposes": tele.PURPOSES}


@app.get("/api/telecall/leads", dependencies=[Depends(require_key)])
def tele_leads(q: str = "", stage: str = "", tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return {"leads": tele.leads(tenant, q, stage, 300)}


@app.post("/api/telecall/leads", dependencies=[Depends(require_key)])
def tele_add(body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.add_lead, tenant, str(body.get("name") or ""), str(body.get("phone") or ""),
                 str(body.get("source") or "enquiry"), str(body.get("purpose") or "sales"), str(body.get("need") or ""),
                 str(body.get("notes") or ""), str(body.get("city") or ""), str(body.get("language") or ""), body.get("amount"),
                 body.get("consent"), str(body.get("assigned") or ""), str(body.get("next_when") or ""))


@app.post("/api/telecall/import", dependencies=[Depends(require_key)])
def tele_import(body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.import_list, tenant, str(body.get("list_id") or ""), str(body.get("file_id") or ""),
                 str(body.get("source") or ""), str(body.get("purpose") or "sales"), str(body.get("assigned") or ""))


@app.get("/api/telecall/leads/{lead_id}", dependencies=[Depends(require_key)])
def tele_lead(lead_id: str, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.get_lead, tenant, lead_id)


@app.patch("/api/telecall/leads/{lead_id}", dependencies=[Depends(require_key)])
def tele_update(lead_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    keys = ("name", "need", "city", "language", "assigned", "notes", "purpose", "interest", "stage", "amount", "consent",
            "next_when", "reason")
    return _tele(tele.update_lead, tenant, lead_id, **{k: body[k] for k in keys if k in body})


@app.post("/api/telecall/leads/{lead_id}/script", dependencies=[Depends(require_key)])
async def tele_script(lead_id: str, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return await asyncio.to_thread(_tele, tele.make_script, tenant, lead_id)


@app.post("/api/telecall/leads/{lead_id}/call", dependencies=[Depends(require_key)])
def tele_start(lead_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """She tapped Call: note the time; the APP opens the phone's own dialer. The server never dials."""
    from .telecall import service as tele
    return _tele(tele.start_call, tenant, lead_id, str(body.get("by") or "owner"))


@app.post("/api/telecall/calls/{call_id}/log", dependencies=[Depends(require_key)])
async def tele_log_call(call_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return await asyncio.to_thread(_tele, tele.log_call, tenant, "", call_id, str(body.get("outcome") or ""),
                                   str(body.get("notes") or ""), str(body.get("next_when") or ""), body.get("seconds"),
                                   str(body.get("interest") or ""), body.get("amount"), str(body.get("file_id") or ""),
                                   str(body.get("by") or "owner"), "app", str(body.get("conversation_id") or ""))


@app.post("/api/telecall/leads/{lead_id}/log", dependencies=[Depends(require_key)])
async def tele_log_lead(lead_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return await asyncio.to_thread(_tele, tele.log_call, tenant, lead_id, "", str(body.get("outcome") or ""),
                                   str(body.get("notes") or ""), str(body.get("next_when") or ""), body.get("seconds"),
                                   str(body.get("interest") or ""), body.get("amount"), str(body.get("file_id") or ""),
                                   str(body.get("by") or "owner"), "app", str(body.get("conversation_id") or ""))


@app.post("/api/telecall/leads/{lead_id}/dnd", dependencies=[Depends(require_key)])
def tele_dnd(lead_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.mark_dnd, tenant, lead_id, bool(body.get("wrong")))


@app.delete("/api/telecall/leads/{lead_id}", dependencies=[Depends(require_key)])
def tele_forget(lead_id: str, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return _tele(tele.forget, tenant, lead_id)


@app.get("/api/telecall/report", dependencies=[Depends(require_key)])
def tele_report(days: int = 1, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    return tele.report(tenant, max(1, min(90, days)))


@app.put("/api/telecall/settings", dependencies=[Depends(require_key)])
def tele_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .telecall import service as tele
    keys = ("enabled", "business", "caller_name", "pitch", "segment", "start_hour", "end_hour", "daily_goal", "max_attempts",
            "record_calls", "registered", "language", "rules", "dont_say", "team", "morning_time")
    return _tele(tele.save_settings, tenant, **{k: body[k] for k in keys if k in body})


# ---------------------------------------------------------------- v0.111 Ads Sahayak (performance marketer; ad money on her tap)
def _ads(fn, *a, **k):
    from .ads import service as ads
    try:
        return fn(*a, **k)
    except ads.AdsError as e:
        raise HTTPException(400, str(e))


@app.get("/api/ads", dependencies=[Depends(require_key)])
async def ads_all(tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(ads.everything, tenant)


@app.get("/api/ads/report", dependencies=[Depends(require_key)])
async def ads_report(days: int = 30, platform: str = "", tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(ads.analyse, tenant, max(1, min(365, days)), platform)


@app.post("/api/ads/import", dependencies=[Depends(require_key)])
async def ads_import(file: UploadFile | None = File(None), file_id: str = Form(""), platform: str = Form(""),
                     start: str = Form(""), end: str = Form(""), conversation_id: str = Form(""),
                     tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    data = await file.read() if file is not None else None
    if data is not None and len(data) > 30 * 1024 * 1024:
        raise HTTPException(413, "The report is bigger than 30 MB.")
    return await asyncio.to_thread(_ads, ads.import_report, tenant, file_id, data, (file.filename if file else "report.csv"),
                                   platform, start, end, conversation_id)


@app.post("/api/ads/plan", dependencies=[Depends(require_key)])
async def ads_plan(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(_ads, ads.make_plan, tenant, int(body.get("days") or 14), str(body.get("conversation_id") or ""),
                                   float(body.get("extra") or 0))


@app.get("/api/ads/changes", dependencies=[Depends(require_key)])
def ads_changes(status: str = "", tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return {"changes": ads.changes(tenant, status, 100)}


@app.post("/api/ads/changes/{cid}/decide", dependencies=[Depends(require_key)])
async def ads_decide(cid: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on a change card. A change that spends more needs her phone's fingerprint once one is set up."""
    from .ads import service as ads
    yes = bool(body.get("yes"))
    if yes:
        _fingerprint(tenant, "ads", cid, body.get("proof"))
    after = body.get("after")
    return await asyncio.to_thread(_ads, ads.decide_change, tenant, cid, yes, float(after) if after not in (None, "") else None,
                                   str(body.get("conversation_id") or ""))


@app.post("/api/ads/changes/{cid}/done", dependencies=[Depends(require_key)])
def ads_done(cid: str, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return _ads(ads.mark_done, tenant, cid)


@app.post("/api/ads/copies", dependencies=[Depends(require_key)])
async def ads_copies(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(_ads, ads.write_copies, tenant, str(body.get("brief") or ""), str(body.get("platform") or "meta"),
                                   str(body.get("campaign") or ""), int(body.get("n") or 4), str(body.get("lang") or ""),
                                   str(body.get("landing") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/ads/tests", dependencies=[Depends(require_key)])
def ads_tests(tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return {"tests": ads.tests(tenant, 60)}


@app.post("/api/ads/tests/{tid}/{action}", dependencies=[Depends(require_key)])
def ads_test_act(tid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    if action == "live":
        return _ads(ads.test_live, tenant, tid, body.get("labels"))
    if action == "result":
        return _ads(ads.test_result, tenant, tid, body.get("results") if isinstance(body.get("results"), dict) else None)
    raise HTTPException(404, "unknown action")


@app.post("/api/ads/sales", dependencies=[Depends(require_key)])
def ads_sale(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return _ads(ads.add_sale, tenant, str(body.get("campaign") or ""), int(body.get("count") or 0), float(body.get("value") or 0),
                str(body.get("day") or ""), str(body.get("platform") or ""), str(body.get("note") or ""))


@app.put("/api/ads/settings", dependencies=[Depends(require_key)])
def ads_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    keys = ("enabled", "business", "segment", "offer", "target_cpl", "target_roas", "avg_order", "margin_pct", "close_pct",
            "month_budget", "max_step_pct", "report_day", "report_time", "rules")
    return _ads(ads.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.put("/api/ads/meta", dependencies=[Depends(require_key)])
async def ads_meta(body: dict, tenant: str = Depends(current_tenant)):
    """Her own Meta ad account: account id + a system-user token (typed in the app only; sealed, never shown again)."""
    from .ads import service as ads
    return await asyncio.to_thread(_ads, ads.set_meta, tenant, str(body.get("account") or ""), str(body.get("token") or ""))


@app.delete("/api/ads/meta", dependencies=[Depends(require_key)])
def ads_meta_off(tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return ads.forget_meta(tenant)


@app.post("/api/ads/meta/fetch", dependencies=[Depends(require_key)])
async def ads_meta_fetch(body: dict, tenant: str = Depends(current_tenant)):
    from .ads import service as ads
    return await asyncio.to_thread(_ads, ads.fetch_meta, tenant, int(body.get("days") or 14), str(body.get("conversation_id") or ""))


# ---------------------------------------------------------------- v0.121 Website Sahayak (plan, looks, live build, checks, preview)
def _site(fn, *a, **k):
    from .site import service as S
    try:
        return fn(*a, **k)
    except S.SiteError as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, f"not found: {e}")


@app.get("/api/sites", dependencies=[Depends(require_key)])
async def sites_all(tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(S.everything, tenant)


@app.post("/api/sites", dependencies=[Depends(require_key)])
async def sites_new(body: dict, tenant: str = Depends(current_tenant)):
    """{brief, name, goal, style, answers {name, phone, ...}, client, conversation_id}"""
    from .site import service as S
    ans = body.get("answers") if isinstance(body.get("answers"), dict) else None
    brief = str(body.get("brief") or "")
    if body.get("deep") and not body.get("field"):     # v0.711 the Studio's Build mode: EVERY ask gets the architect's plan
        from .config import get_settings
        from .site import architect as AR
        if getattr(get_settings(), "studio_build_architect", True) or AR.wants_plan(brief):
            return await asyncio.to_thread(_site_logic, AR.build_now, tenant, brief, str(body.get("conversation_id") or ""))
    return await asyncio.to_thread(_site, S.new, tenant, str(body.get("brief") or ""), str(body.get("conversation_id") or ""),
                                   str(body.get("name") or ""), str(body.get("field") or ""), str(body.get("goal") or ""),
                                   str(body.get("style") or ""), ans, str(body.get("client") or ""))


@app.get("/api/site-templates", dependencies=[Depends(require_key)])
async def site_templates(q: str = "", sector: str = "", kind: str = "", style: str = "", offset: int = 0, limit: int = 30):
    """v0.686 the Web Studio's 1,00,000 UNIQUE website templates (1,000 subjects in 50 world sectors x 10 positionings x
    10 cities, each with its own name, website type and style), searchable by words, sector, website type and style."""
    from .site import templates as TP
    return await asyncio.to_thread(TP.search, q, sector, kind, style, offset, limit)


@app.get("/api/site-templates/{tid}", dependencies=[Depends(require_key)])
async def site_template(tid: str):
    from .site import templates as TP
    try:
        return await asyncio.to_thread(TP.prompt, tid)
    except (KeyError, ValueError):
        raise HTTPException(404, "No such template.")


@app.get("/api/sites-library", dependencies=[Depends(require_key)])
async def sites_library(industry: str = "", q: str = "", offset: int = 0, limit: int = 60):
    from .site import library as L
    return await asyncio.to_thread(L.browse, industry, q, max(1, min(limit, 200)), max(0, offset))


@app.get("/api/sites-library/brief", dependencies=[Depends(require_key)])
async def sites_library_brief(field: str, goal: str = "", style: str = ""):
    from .site import library as L
    try:
        return await asyncio.to_thread(L.brief, field, goal, style)
    except KeyError:
        raise HTTPException(404, "field not found")


@app.get("/api/sites-library/understand", dependencies=[Depends(require_key)])
async def sites_library_understand(q: str):
    from .site import library as L
    return await asyncio.to_thread(L.understand, q)


@app.get("/api/sites/{ref}", dependencies=[Depends(require_key)])
async def sites_get(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.get, tenant, ref)


@app.patch("/api/sites/{ref}", dependencies=[Depends(require_key)])
async def sites_rename(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.658 rename a project in the Web Studio list ({name}); nothing on the website itself changes."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.rename, tenant, ref, str(body.get("name") or ""))


@app.delete("/api/sites/{ref}", dependencies=[Depends(require_key)])
async def sites_delete(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.delete, tenant, ref)


@app.post("/api/sites/{ref}/answers", dependencies=[Depends(require_key)])
async def sites_answers(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import service as S
    ans = body.get("answers") if isinstance(body.get("answers"), dict) else {}
    return await asyncio.to_thread(_site, S.answer, tenant, ref, ans)


@app.post("/api/sites/{ref}/plan", dependencies=[Depends(require_key)])
async def sites_plan_ok(ref: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """Her tap: 'Haan, aage badho' on the plan card -> 3 looks."""
    from .site import service as S
    body = body or {}
    pages = body.get("pages") if isinstance(body.get("pages"), list) else None
    return await asyncio.to_thread(_site, S.approve_plan, tenant, ref, str(body.get("conversation_id") or ""), pages)


@app.post("/api/sites/{ref}/look", dependencies=[Depends(require_key)])
async def sites_look(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on one of the 3 looks {index, colors_from?} -> the build starts."""
    from .site import service as S
    cf = body.get("colors_from")
    return await asyncio.to_thread(_site, S.choose_look, tenant, ref, int(body.get("index") or 0),
                                   int(cf) if cf is not None and str(cf).lstrip("-").isdigit() else None,
                                   str(body.get("conversation_id") or ""))


@app.post("/api/sites/{ref}/change", dependencies=[Depends(require_key)])
async def sites_change(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.change, tenant, ref, str(body.get("instruction") or ""),
                                   str(body.get("conversation_id") or ""))


# ---- v0.295 editing like Lovable: her own hands in the preview, no AI, every change undoable
@app.post("/api/sites/{ref}/edit-mode", dependencies=[Depends(require_key)])
async def sites_edit_mode(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.edit_mode, tenant, ref)


@app.post("/api/sites/{ref}/edit", dependencies=[Depends(require_key)])
async def sites_edit(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """One change she made in the edit preview: {k: 'page__type', e: element number, op: text|link|image|remove, value}."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.edit_element, tenant, ref, str(body.get("k") or ""), str(body.get("e") or ""),
                                   str(body.get("op") or ""), str(body.get("value") or ""))


@app.post("/api/sites/{ref}/theme", dependencies=[Depends(require_key)])
async def sites_theme(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.set_theme, tenant, ref, body.get("tokens") if isinstance(body.get("tokens"), dict) else body)


@app.post("/api/sites/{ref}/undo", dependencies=[Depends(require_key)])
async def sites_undo(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.undo_edit, tenant, ref)


@app.get("/api/sites/{ref}/edits", dependencies=[Depends(require_key)])
async def sites_edits(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.edits, tenant, ref)


@app.post("/api/sites/{ref}/stop", dependencies=[Depends(require_key)])
async def sites_stop(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.stop, tenant, ref)


@app.post("/api/sites/{ref}/resume", dependencies=[Depends(require_key)])
async def sites_resume(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.resume, tenant, ref)


@app.post("/api/sites/{ref}/photo", dependencies=[Depends(require_key)])
async def sites_photo(ref: str, file: UploadFile = File(...), about: str = Form(""), tenant: str = Depends(current_tenant)):
    from .site import service as S
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "The photo is bigger than 25 MB")
    return await asyncio.to_thread(_site, S.add_photo, tenant, ref, data, "", about, "")


@app.post("/api/sites/{ref}/lottie", dependencies=[Depends(require_key)])
async def sites_lottie(ref: str, file: UploadFile = File(...), name: str = Form(""), tenant: str = Depends(current_tenant)):
    """v0.568 her own Lottie JSON animation (checked: real Lottie, <= 1.5 MB, embedded images only, no expressions)."""
    from .site import service as S
    data = await file.read(1_600_000)
    return await asyncio.to_thread(_site, S.add_lottie, tenant, ref, data, "", name)


@app.get("/api/sites/{ref}/lottie", dependencies=[Depends(require_key)])
async def sites_lottie_list(ref: str, tenant: str = Depends(current_tenant)):
    from .site import build as B
    from .site import lottie as LT
    from .site import service as S

    def go():
        with __import__("app.db", fromlist=["session"]).session() as s:
            r = S._find(s, tenant, ref)
            sid = r.id
        return {"builtins": list(LT.BUILTINS), "hers": LT.hers(B.src_dir(tenant, sid)),
                "scenes_3d": ["orb", "knot", "particles", "waves", "blocks"]}
    return await asyncio.to_thread(_site, go)


@app.post("/api/sites/{ref}/media", dependencies=[Depends(require_key)])
async def sites_media(ref: str, file: UploadFile = File(...), about: str = Form(""), tenant: str = Depends(current_tenant)):
    """v0.338 a video / audio / download file of hers for the site (Edit mode puts it on a page)."""
    from .site import service as S
    data = await file.read(60 * 1024 * 1024 + 1)
    if len(data) > 60 * 1024 * 1024:
        raise HTTPException(413, "The file is bigger than 60 MB; make the video smaller and send it again.")
    return await asyncio.to_thread(_site, S.add_media, tenant, ref, data, file.filename or "file", about)


@app.post("/api/sites/{ref}/export", dependencies=[Depends(require_key)])
async def sites_export(ref: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    from .site import service as S
    fmt = "react" if str((body or {}).get("format") or "") == "react" else "zip"       # v0.305 React (Vite) project too
    return await asyncio.to_thread(_site, S.export, tenant, ref, fmt)


@app.get("/api/sites/{ref}/live", dependencies=[Depends(require_key)])
async def sites_live(ref: str, since: int = 0, tenant: str = Depends(current_tenant)):
    """v0.664 ASLI SAMAY: the live build stream. Each event = the sections that changed since the last one; a section's
    HTML only grows while it is written, so after the first event only the new characters travel (`ha` / `ca` = added,
    a full `h` / `c` when it was rewritten or finished). Ends after ~10 min; the Studio reconnects with `since`."""
    from .site import service as S
    from .site import stream as ST
    v = await asyncio.to_thread(_site, S.get, tenant, ref)
    sid = v["id"]

    async def gen():
        sent: dict[str, tuple[str, str, str]] = {}
        seq, started, quiet = int(since or 0), time.time(), 0.0
        yield ": open\n\n"
        while time.time() - started < 600:
            snap = await asyncio.to_thread(ST.wait, sid, seq, 15.0)
            if snap["seq"] <= seq:
                quiet += 15
                yield ": ping\n\n"
                continue
            seq = snap["seq"]
            out = []
            for sl in snap["slots"]:
                k, h, c = sl["key"], sl.get("html") or "", sl.get("css") or ""
                ev = {kk: sl.get(kk) for kk in ("key", "label", "page", "look", "kind", "state", "at", "end")}
                h0, c0, st0 = sent.get(k, ("", "", ""))
                growing = st0 in ("think", "write") and sl["state"] in ("think", "write")
                if growing and h0 and h.startswith(h0):
                    ev["ho"], ev["ha"] = len(h0), h[len(h0):]
                else:
                    ev["h"] = h
                if growing and c0 and c.startswith(c0):
                    ev["co"], ev["ca"] = len(c0), c[len(c0):]
                else:
                    ev["c"] = c
                sent[k] = (h, c, sl["state"])
                out.append(ev)
            yield "data: " + ST.dumps({"seq": seq, "slots": out, "looks": snap["looks"]}) + "\n\n"
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.get("/api/sites/{ref}/download", dependencies=[Depends(require_key)])
async def sites_download(ref: str, format: str = "zip", tenant: str = Depends(current_tenant)):
    """v0.663 the Studio's Download ZIP / React + Vite: the zip itself, straight to her computer (with her key)."""
    from urllib.parse import quote

    from .site import service as S
    name, data = await asyncio.to_thread(_site, S.export_bytes, tenant, ref, "react" if format == "react" else "zip")
    return Response(content=data, media_type="application/zip", headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}", "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff"})


@app.get("/api/sites/{ref}/leads", dependencies=[Depends(require_key)])
async def sites_leads(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return {"leads": await asyncio.to_thread(_site, S.leads, tenant, ref)}


@app.get("/api/sites/{ref}/shots/{name:path}", dependencies=[Depends(require_key)])
async def sites_shot(ref: str, name: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    try:
        f = await asyncio.to_thread(S.shot_file, tenant, ref, name)
    except (S.SiteError, ValueError):
        raise HTTPException(404, "not found")
    return FileResponse(f, headers={"Cache-Control": "private, max-age=300"})


@app.get("/api/site-preview/{token}")
async def site_preview_root(token: str):
    return RedirectResponse(f"/api/site-preview/{token}/", status_code=307)


@app.get("/api/site-preview/{token}/{path:path}")
async def site_preview(token: str, path: str = ""):
    """Public, by its random token: the live preview of a site being built (noindex, strict CSP)."""
    from .site import service as S
    try:
        data, ctype, headers = await asyncio.to_thread(S.preview_file, token, path)
    except S.SiteError:
        raise HTTPException(404, "not found")
    # v0.160 the console shows it in a sandboxed frame (opaque origin): its own fonts / files must load from there
    return Response(content=data, media_type=ctype, headers={**headers, "Access-Control-Allow-Origin": "*"})


_SITE_FORM_CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS",
                   "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400"}


@app.options("/api/site-forms/{site_id}")
async def site_form_cors(site_id: str):
    return Response(status_code=204, headers=_SITE_FORM_CORS)


@app.post("/api/site-ops/{site_id}/beacon")
async def site_ops_beacon(site_id: str, request: Request):
    """v0.564 Public: a visitor's browser reports this page's JavaScript errors / real load timings (sendBeacon, text/plain;
    no cookie, no id). Counted into day totals and bands only; an unknown site or a flood is silently dropped."""
    from .site import ops as OPS
    raw = await request.body()
    ip = (request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip") or
          (request.client.host if request.client else ""))
    try:
        await asyncio.to_thread(OPS.record, site_id, raw[:OPS.MAX_BODY + 1], ip)
    except Exception:                                    # noqa: BLE001 - a beacon never errors back at a visitor
        log.debug("site ops beacon failed", exc_info=True)
    return Response(status_code=204)


@app.post("/api/site-forms/{site_id}")
async def site_form(site_id: str, request: Request):
    """Public: a visitor's enquiry from a Hoola-built site -> her lead (honeypot, rate limits, no cookies)."""
    from .site import service as S
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "bad form")
    ip = (request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip") or
          (request.client.host if request.client else ""))
    try:
        out = await asyncio.to_thread(S.form_post, site_id, body, ip)
    except S.SiteError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400, headers=_SITE_FORM_CORS)
    return JSONResponse(out, headers=_SITE_FORM_CORS)


# ---- v0.305 web apps on her website: members, data, staff panel (public endpoints answer the site's app script)
_SITE_APP_CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
                  "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Max-Age": "86400"}


def _app_call(fn, request: Request | None = None):
    from .site import webapp as W
    try:
        return JSONResponse(fn(), headers={**_SITE_APP_CORS, "Cache-Control": "no-store"})
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code, headers=_SITE_APP_CORS)


def _app_who(site_id: str, request: Request):
    from .site import webapp as W
    tok = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
    return W.Who(W.member_of(site_id, tok) if tok else None)


def _ip(request: Request) -> str:
    return (request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip") or
            (request.client.host if request.client else ""))


@app.options("/api/site-app/{site_id}/{rest:path}")
async def site_app_cors(site_id: str, rest: str):
    return Response(status_code=204, headers=_SITE_APP_CORS)


def _site_tok(request: Request) -> str:
    return (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()


async def _site_pub(site_id: str, op: str, request: Request, body: dict | None = None, **kw):
    """v0.407 EK DIMAAG: every public web-app call of a website - the v0.305 engine for a plain site, the App Sahayak
    backend + DIMAAG logic for a linked one (site/applink.py). The site's pages keep the same addresses."""
    from .site import applink as AL
    tok, ip = _site_tok(request), _ip(request)
    kw.setdefault("ua", (request.headers.get("user-agent") or "")[:160])     # v0.434 the sessions list names the device
    return await asyncio.to_thread(_app_call, lambda: AL.call(site_id, op, tok, body or {}, ip, **kw))


@app.get("/api/site-app/{site_id}/schema")
async def site_app_schema(site_id: str, request: Request):
    return await _site_pub(site_id, "schema", request)


@app.post("/api/site-app/{site_id}/signup")
async def site_app_signup(site_id: str, request: Request):
    return await _site_pub(site_id, "signup", request, await _json_body(request))


@app.post("/api/site-app/{site_id}/login")
async def site_app_login(site_id: str, request: Request):
    return await _site_pub(site_id, "login", request, await _json_body(request))


@app.get("/api/site-app/{site_id}/me")
async def site_app_me(site_id: str, request: Request):
    return await _site_pub(site_id, "me", request)


@app.post("/api/site-app/{site_id}/logout")
async def site_app_logout(site_id: str, request: Request):
    return await _site_pub(site_id, "logout", request)


@app.get("/api/site-app/{site_id}/c/{key}")
async def site_app_rows(site_id: str, key: str, request: Request):
    return await _site_pub(site_id, "rows", request, key=key)


@app.post("/api/site-app/{site_id}/c/{key}")
async def site_app_create(site_id: str, key: str, request: Request):
    return await _site_pub(site_id, "create", request, await _json_body(request), key=key)


@app.patch("/api/site-app/{site_id}/c/{key}/{row_id}")
async def site_app_update(site_id: str, key: str, row_id: str, request: Request):
    return await _site_pub(site_id, "update", request, await _json_body(request), key=key, row_id=row_id)


@app.delete("/api/site-app/{site_id}/c/{key}/{row_id}")
async def site_app_delete(site_id: str, key: str, row_id: str, request: Request):
    return await _site_pub(site_id, "delete", request, key=key, row_id=row_id)


@app.get("/api/site-app/{site_id}/c/{key}/{row_id}/related/{rel}")
async def site_app_related(site_id: str, key: str, row_id: str, rel: str, request: Request):
    """v0.407 a row's linked records (an order's lines, a class's students) - linked sites only."""
    return await _site_pub(site_id, "related", request, key=key, row_id=row_id, rel=rel)


@app.get("/api/site-app/{site_id}/members")
async def site_app_members(site_id: str, request: Request):
    """Staff page: the site's members (staff / admin members only)."""
    return await _site_pub(site_id, "members", request)


@app.get("/api/site-app/{site_id}/stats")
async def site_app_stats(site_id: str, request: Request, days: int = 30):
    """v0.357 the staff panel's dashboard: rows a day, status mix, sums (staff / admin members only)."""
    return await _site_pub(site_id, "stats", request, days=days)


@app.post("/api/site-app/{site_id}/members/{member_id}/role")
async def site_app_role(site_id: str, member_id: str, request: Request):
    return await _site_pub(site_id, "role", request, await _json_body(request), member_id=member_id)


@app.get("/api/site-app/{site_id}/approvals")
async def site_app_approvals(site_id: str, request: Request):
    """v0.407 the approvals waiting for this person (maker-checker; linked sites only)."""
    return await _site_pub(site_id, "approvals", request)


@app.post("/api/site-app/{site_id}/approvals/{appr_id}")
async def site_app_decide(site_id: str, appr_id: str, request: Request):
    return await _site_pub(site_id, "decide", request, await _json_body(request), appr_id=appr_id)


# v0.434 LOGIN AUR SURAKSHA: phone OTP, staff 2FA, sessions, her data (export / delete), audit log, permissions, uploads
@app.post("/api/site-app/{site_id}/otp/start")
async def site_app_otp_start(site_id: str, request: Request):
    return await _site_pub(site_id, "otp_start", request, await _json_body(request))


@app.post("/api/site-app/{site_id}/otp/verify")
async def site_app_otp_verify(site_id: str, request: Request):
    return await _site_pub(site_id, "otp_verify", request, await _json_body(request))


@app.post("/api/site-app/{site_id}/2fa/login")
async def site_app_2fa_login(site_id: str, request: Request):
    return await _site_pub(site_id, "2fa_login", request, await _json_body(request))


@app.post("/api/site-app/{site_id}/2fa/{step}")
async def site_app_2fa(site_id: str, step: str, request: Request):
    if step not in ("start", "confirm", "off"):
        raise HTTPException(404, "not found")
    return await _site_pub(site_id, "2fa_" + step, request, await _json_body(request))


@app.get("/api/site-app/{site_id}/sessions")
async def site_app_sessions(site_id: str, request: Request):
    return await _site_pub(site_id, "sessions", request)


@app.post("/api/site-app/{site_id}/sessions/{sid}/end")
async def site_app_session_end(site_id: str, sid: str, request: Request):
    return await _site_pub(site_id, "session_end", request, sid=sid)


@app.post("/api/site-app/{site_id}/logout-all")
async def site_app_logout_all(site_id: str, request: Request):
    return await _site_pub(site_id, "logout_all", request)


@app.get("/api/site-app/{site_id}/me/export")
async def site_app_export(site_id: str, request: Request):
    return await _site_pub(site_id, "export", request)


@app.post("/api/site-app/{site_id}/me/delete")
async def site_app_delete_me(site_id: str, request: Request):
    return await _site_pub(site_id, "delete_me", request)


@app.get("/api/site-app/{site_id}/audit")
async def site_app_audit(site_id: str, request: Request, limit: int = 200, coll: str = ""):
    return await _site_pub(site_id, "audit", request, limit=limit, coll=coll)


@app.get("/api/site-app/{site_id}/matrix")
async def site_app_matrix(site_id: str, request: Request):
    return await _site_pub(site_id, "matrix", request)


@app.post("/api/site-app/{site_id}/upload")
async def site_app_upload(site_id: str, request: Request):
    raw = await request.body()
    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(413, "The file is too big (up to 12 MB).")
    return await _site_pub(site_id, "upload", request, raw=raw)


@app.get("/api/site-app/{site_id}/file/{fid}")
async def site_app_file(site_id: str, fid: str, request: Request):
    """v0.434 a photo / PDF from a form, for whoever may see it (the page fetches it with the login header)."""
    from .appmaker import backend as BE
    from .site import applink as AL
    from .site import service as S
    from .site import webapp as W

    def go():
        r, _ = S.public_app(site_id)
        p = AL.project(r)
        if p is None:
            raise W.AppError("not found", 404)
        return BE.file_for(p, fid, AL._who(site_id, p, _site_tok(request)))
    try:
        path = await asyncio.to_thread(go)
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code, headers=_SITE_APP_CORS)
    from fastapi.responses import FileResponse
    import mimetypes as _mt                          # v0.581 a lesson's video plays with its own type (was always image/jpeg)
    kind = "application/pdf" if str(path).endswith(".pdf") else (_mt.guess_type(str(path))[0] or "image/jpeg")
    return FileResponse(path, media_type=kind, headers={**_SITE_APP_CORS, "Cache-Control": "private, max-age=300"})


@app.get("/api/site-app/{site_id}/c/{key}/{row_id}/document")
async def site_app_document(site_id: str, key: str, row_id: str, request: Request):
    """v0.581 the row's PDF (a course certificate) - only for someone who may read that row, only when its shart holds."""
    from .appmaker.logic import engine as LE
    from .site import applink as AL
    from .site import service as S
    from .site import webapp as W

    def go():
        r, _ = S.public_app(site_id)
        p = AL.project(r)
        if p is None:
            raise W.AppError("not found", 404)
        return LE.document_pdf(p, key, row_id, AL._who(site_id, p, _site_tok(request)))
    try:
        pdf, title = await asyncio.to_thread(go)
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code, headers=_SITE_APP_CORS)
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", title)[:60].strip("-") or "document"
    return Response(content=pdf, media_type="application/pdf",
                    headers={**_SITE_APP_CORS, "Cache-Control": "private, no-store",
                             "Content-Disposition": f'attachment; filename="{name}.pdf"'})


@app.post("/api/site-app/{site_id}/fn/{name}")
async def site_app_fn(site_id: str, name: str, request: Request):
    """v0.407 a callable locked function of the site's logic (its own tests passed before it went live)."""
    return await _site_pub(site_id, "fn", request, await _json_body(request), name=name)


async def _json_body(request: Request) -> dict:
    try:
        b = await request.json()
        return b if isinstance(b, dict) else {}
    except Exception:
        return {}


# owner side (her Hoola login): design the app, see / change the data, members and roles
def _site_logic(fn, *a):
    from .site import service as S
    from .site import webapp as W
    try:
        return fn(*a)
    except W.AppError as e:
        raise HTTPException(e.code, str(e))
    except S.SiteError as e:
        raise HTTPException(400, str(e))
    except Exception as e:                       # v0.407 the Architect's own refusals carry their HTTP code
        from .site import architect as AR
        if isinstance(e, AR.ArchError):
            raise HTTPException(e.code, str(e))
        raise


@app.get("/api/sites/{ref}/logic", dependencies=[Depends(require_key)])
async def sites_logic(ref: str, tenant: str = Depends(current_tenant)):
    """v0.407 EK DIMAAG: the website app's logic (App Sahayak's DIMAAG on the linked project), its draft, its log."""
    from .site import applink as AL
    return await asyncio.to_thread(_site_logic, AL.logic_view, tenant, ref)


@app.post("/api/sites/{ref}/logic/draft", dependencies=[Depends(require_key)])
async def sites_logic_draft(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her words -> relations / formulas / rules / workflows / approvals drafted + checked (nothing live yet)."""
    from .site import applink as AL
    return await asyncio.to_thread(_site_logic, AL.logic_draft, tenant, ref, str(body.get("words") or ""))


@app.post("/api/sites/{ref}/logic/apply", dependencies=[Depends(require_key)])
async def sites_logic_apply(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """ONLY her tap: the draft she saw (by its hash) goes live on the site + its app."""
    from .site import applink as AL
    return await asyncio.to_thread(_site_logic, AL.logic_apply, tenant, ref, str(body.get("hash") or ""))


@app.get("/api/sites/{ref}/audit", dependencies=[Depends(require_key)])
async def sites_audit(ref: str, limit: int = 100, tenant: str = Depends(current_tenant)):
    """v0.434 her website app's audit log (every change, who made it) + the permissions matrix."""
    from .site import applink as AL
    return await asyncio.to_thread(_site_logic, AL.owner_audit, tenant, ref, max(1, min(limit, 500)))


@app.post("/api/sites/{ref}/link-app", dependencies=[Depends(require_key)])
async def sites_link_app(ref: str, tenant: str = Depends(current_tenant)):
    from .site import applink as AL
    return await asyncio.to_thread(_site_logic, AL.link, tenant, ref)


@app.get("/api/site-architect", dependencies=[Depends(require_key)])
async def site_architect_list(tenant: str = Depends(current_tenant)):
    """v0.407 HOOLA ARCHITECT: her spec cards (waiting / built)."""
    from .site import architect as AR
    return {"specs": await asyncio.to_thread(AR.specs, tenant)}


@app.post("/api/site-architect", dependencies=[Depends(require_key)])
async def site_architect_new(body: dict, tenant: str = Depends(current_tenant)):
    """{words, conversation_id}: her ONE line -> the full spec card (pages, users, data, rules, features). Nothing built."""
    from .site import architect as AR
    return await asyncio.to_thread(_site_logic, AR.draft, tenant, str(body.get("words") or ""),
                                   str(body.get("conversation_id") or ""))


@app.get("/api/site-architect/{ref}", dependencies=[Depends(require_key)])
async def site_architect_card(ref: str, tenant: str = Depends(current_tenant)):
    from .site import architect as AR
    return await asyncio.to_thread(_site_logic, AR.card, tenant, ref)


@app.post("/api/site-architect/{ref}/data", dependencies=[Depends(require_key)])
async def site_architect_data(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{words}: redo ONLY the data + rules part of the card with her change."""
    from .site import architect as AR
    return await asyncio.to_thread(_site_logic, AR.redraft_data, tenant, ref, str(body.get("words") or ""))


@app.post("/api/site-architect/{ref}/revise", dependencies=[Depends(require_key)])
async def site_architect_revise(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.414 {words}: her change to ANY part of the card; after the build only what it touches is rebuilt / drafted."""
    from .site import architect as AR
    return await asyncio.to_thread(_site_logic, AR.revise, tenant, ref, str(body.get("words") or ""))


@app.post("/api/sites/{ref}/phone-app", dependencies=[Depends(require_key)])
async def sites_phone_app(ref: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """v0.414 the website's app as an Android / iPhone app design on the SAME project + data (App Sahayak's plan card)."""
    from .site import applink as AL
    return await asyncio.to_thread(_site_logic, AL.phone_app, tenant, ref, str((body or {}).get("conversation_id") or ""))


@app.post("/api/site-architect/{ref}/approve", dependencies=[Depends(require_key)])
async def site_architect_approve(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """ONLY her tap: {hash (the card she saw), modules [pages, users, data, logic, features]} -> Hoola builds it."""
    from .site import architect as AR
    mods = body.get("modules") if isinstance(body.get("modules"), list) else None
    return await asyncio.to_thread(_site_logic, AR.approve, tenant, ref, str(body.get("hash") or ""), mods,
                                   str(body.get("conversation_id") or ""))


@app.post("/api/sites/{ref}/app-design", dependencies=[Depends(require_key)])
async def sites_app_design(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.design_app, tenant, ref, str(body.get("words") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/sites/{ref}/app", dependencies=[Depends(require_key)])
async def sites_app_info(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.app_info, tenant, ref)


def _site_app(fn, *a):
    from .site import webapp as W
    try:
        return _site(fn, *a)
    except W.AppError as e:
        raise HTTPException(e.code, str(e))


@app.get("/api/sites/{ref}/app/rows/{key}", dependencies=[Depends(require_key)])
async def sites_app_rows(ref: str, key: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site_app, S.app_rows, tenant, ref, key)


@app.patch("/api/sites/{ref}/app/rows/{key}/{row_id}", dependencies=[Depends(require_key)])
async def sites_app_row_update(ref: str, key: str, row_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site_app, S.app_row_update, tenant, ref, key, row_id, body)


@app.delete("/api/sites/{ref}/app/rows/{key}/{row_id}", dependencies=[Depends(require_key)])
async def sites_app_row_delete(ref: str, key: str, row_id: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site_app, S.app_row_delete, tenant, ref, key, row_id)


@app.get("/api/sites/{ref}/app/members", dependencies=[Depends(require_key)])
async def sites_app_members(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site_app, S.app_members, tenant, ref)


@app.post("/api/sites/{ref}/app/members/{member_id}/role", dependencies=[Depends(require_key)])
async def sites_app_role(ref: str, member_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site_app, S.app_role, tenant, ref, member_id, str(body.get("role") or ""))


# ---- v0.306 HOOLA DESIGN ARENA: fixed briefs built + judged, runs compared, blind duels vs other builders (owner only)
def _arena_owner(tenant: str) -> None:
    if tenant != get_settings().tenant_id:
        raise HTTPException(403, "Design Arena is only for the Hoola owner.")


def _arena(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- v0.376 PROOF: 100-page builds and rival crawls, measured the same way (owner only)
@app.get("/api/arena/proofs", dependencies=[Depends(require_key)])
async def arena_proofs(tenant: str = Depends(current_tenant)):
    from .site import proof as PR
    _arena_owner(tenant)
    from .config import get_settings

    def go():
        return {"proofs": PR.proofs(), "max_inr": float(getattr(get_settings(), "site_arena_max_inr", 3000) or 3000),
                "briefs": [{"id": b["id"], "name": b["name"], "city": b["city"], "features": b["features"], "lang": b["lang"]}
                           for b in PR.big_set()]}
    return await asyncio.to_thread(_arena, go)


@app.post("/api/arena/proofs", dependencies=[Depends(require_key)])
async def arena_proof_start(body: dict, tenant: str = Depends(current_tenant)):
    from .site import proof as PR
    _arena_owner(tenant)
    return await asyncio.to_thread(_arena, PR.start, str(body.get("brief_id") or ""), float(body.get("budget_inr") or 0))


@app.post("/api/arena/proofs/rival", dependencies=[Depends(require_key)])
async def arena_proof_rival(body: dict, tenant: str = Depends(current_tenant)):
    from .site import proof as PR
    _arena_owner(tenant)
    return await asyncio.to_thread(_arena, PR.rival, str(body.get("brief_id") or ""), str(body.get("builder") or ""),
                                   str(body.get("url") or ""))


@app.get("/api/arena/proofs/compare", dependencies=[Depends(require_key)])
async def arena_proof_compare(a: str, b: str, tenant: str = Depends(current_tenant)):
    from .site import proof as PR
    _arena_owner(tenant)
    return await asyncio.to_thread(_arena, lambda: {"a": PR.get(a), "b": PR.get(b),
                                                    **PR.compare(PR.get(a)["card"], PR.get(b)["card"])})


@app.post("/api/arena/proofs/{pid}/stop", dependencies=[Depends(require_key)])
async def arena_proof_stop(pid: str, tenant: str = Depends(current_tenant)):
    from .site import proof as PR
    _arena_owner(tenant)
    return await asyncio.to_thread(_arena, PR.stop, pid)


@app.post("/api/arena/start", dependencies=[Depends(require_key)])
async def arena_start(body: dict, tenant: str = Depends(current_tenant)):
    from .site import arena as A
    _arena_owner(tenant)
    return await asyncio.to_thread(_arena, A.start, int(body.get("n") or 12), int(body.get("seed") or 1),
                                   float(body.get("budget_inr") or 0), str(body.get("note") or ""))


@app.get("/api/arena/runs", dependencies=[Depends(require_key)])
async def arena_runs(tenant: str = Depends(current_tenant)):
    from .site import arena as A
    _arena_owner(tenant)
    return {"runs": await asyncio.to_thread(A.runs), "duels": await asyncio.to_thread(A.duel_table),
            "recent_duels": await asyncio.to_thread(A.recent_duels), "max_inr": get_settings().site_arena_max_inr}


@app.get("/api/arena/runs/{run_id}", dependencies=[Depends(require_key)])
async def arena_run(run_id: str, tenant: str = Depends(current_tenant)):
    from .site import arena as A
    _arena_owner(tenant)
    run = next((x for x in await asyncio.to_thread(A.runs, 200) if x["run"] == run_id), None)
    if run is None:
        raise HTTPException(404, "run not found")
    cards = await asyncio.to_thread(A.items, run_id)
    return {**run, "items": [{**{k: v for k, v in c.items() if k != "dna"}, **A.brief_info(c.get("brief", ""))} for c in cards],
            "say": A.report_text(run["summary"]) if run["summary"] else "Abhi chal raha hai."}


@app.post("/api/arena/runs/{run_id}/stop", dependencies=[Depends(require_key)])
async def arena_stop(run_id: str, tenant: str = Depends(current_tenant)):
    from .site import arena as A
    _arena_owner(tenant)
    return await asyncio.to_thread(_arena, A.stop, run_id)


@app.get("/api/arena/compare", dependencies=[Depends(require_key)])
async def arena_compare(a: str, b: str, tenant: str = Depends(current_tenant)):
    from .site import arena as A
    _arena_owner(tenant)
    rs = {x["run"]: x for x in await asyncio.to_thread(A.runs, 200)}
    if a not in rs or b not in rs:
        raise HTTPException(404, "run not found")
    return {"a": a, "b": b, **A.compare(rs[a]["summary"], rs[b]["summary"])}


@app.get("/api/arena/briefs", dependencies=[Depends(require_key)])
async def arena_briefs(n: int = 12, seed: int = 1, tenant: str = Depends(current_tenant)):
    from .site import arena as A
    _arena_owner(tenant)
    return {"set": A.SET_V, "total": len(A.brief_set()), "briefs": A.pick(max(1, min(n, 1000)), seed)}


@app.get("/api/arena/shot/{site_id}", dependencies=[Depends(require_key)])
async def arena_shot(site_id: str, w: str = "390", tenant: str = Depends(current_tenant)):
    """v0.312 the home-page screenshot of an Arena site for the console's score cards (Arena sites only)."""
    from .site import arena as A
    _arena_owner(tenant)
    img = await asyncio.to_thread(A.shot, site_id, w)
    if not img:
        raise HTTPException(404, "screenshot not found")
    return Response(img, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@app.post("/api/arena/duel", dependencies=[Depends(require_key)])
async def arena_duel(body: dict, tenant: str = Depends(current_tenant)):
    """A blind duel: the same brief built by another builder (her own build there, its public address) vs Hoola's."""
    from .site import arena as A
    _arena_owner(tenant)
    return await asyncio.to_thread(_arena, A.duel, str(body.get("brief_id") or ""), str(body.get("rival") or "other"),
                                   str(body.get("url") or ""), str(body.get("site") or ""))


# ---- v0.351 DUKAAN: her online shop (public endpoints answer the site's cart script; owner endpoints need her login)
_SHOP_CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400"}


def _shop_call(fn):
    from .site import shop as SH
    try:
        return JSONResponse({"ok": True, **fn()}, headers={**_SHOP_CORS, "Cache-Control": "no-store"})
    except SH.ShopError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code, headers=_SHOP_CORS)


@app.options("/api/site-shop/{site_id}/{rest:path}")
async def site_shop_cors(site_id: str, rest: str):
    return Response(status_code=204, headers=_SHOP_CORS)


@app.get("/api/site-shop/{site_id}/products")
async def site_shop_products(site_id: str):
    """Public: her live prices and what is in stock (never stock counts beyond in / out)."""
    from .site import service as S
    from .site import shop as SH

    def go():
        _r, cfg = S.shop_public(site_id)
        if not cfg["on"]:
            raise SH.ShopError("shop off", 404)
        from .site import shoppay as SP                        # v0.446 online payment on? + verified-buyer stars
        return {"products": [{k: p[k] for k in ("slug", "title", "price", "price_text", "unit", "in_stock")} for p in SH.products(site_id)],
                "online": bool(cfg.get("online")), "ratings": SP.reviews(site_id)["summary"]}
    return await asyncio.to_thread(_shop_call, go)


@app.post("/api/site-shop/{site_id}/order")
async def site_shop_order(site_id: str, request: Request):
    """Public: a customer's checkout. Prices, totals and stock are worked out on the server."""
    from .site import service as S
    try:
        body = await request.json()
    except Exception:
        body = {}
    body = body if isinstance(body, dict) else {}
    return await asyncio.to_thread(_shop_call, lambda: S.shop_order(site_id, body, _ip(request)))


@app.get("/api/site-shop/{site_id}/order/{number}")
async def site_shop_track(site_id: str, number: str, t: str = ""):
    from .site import service as S
    return await asyncio.to_thread(_shop_call, lambda: S.shop_track(site_id, number, t))


@app.post("/api/site-shop/{site_id}/order/{number}/paid")
async def site_shop_paid(site_id: str, number: str, request: Request):
    """Public: the customer says they paid by UPI (UTR). The shop still checks its own account and confirms."""
    from .site import service as S
    try:
        body = await request.json()
    except Exception:
        body = {}
    body = body if isinstance(body, dict) else {}
    return await asyncio.to_thread(_shop_call, lambda: S.shop_paid(site_id, number, str(body.get("token") or ""),
                                                                   str(body.get("utr") or ""), _ip(request)))


# v0.446 DUKAAN PAISA: coupons, online payment again, verified-buyer reviews (public) + her side (connect, refund, reviews)
async def _shop_body(request: Request) -> dict:
    try:
        b = await request.json()
    except Exception:
        b = {}
    return b if isinstance(b, dict) else {}


@app.post("/api/site-shop/{site_id}/coupon")
async def site_shop_coupon(site_id: str, request: Request):
    from .site import shoppay as SP
    b = await _shop_body(request)
    return await asyncio.to_thread(_shop_call, lambda: SP.coupon_check(site_id, str(b.get("code") or ""), b.get("items")))


@app.post("/api/site-shop/{site_id}/order/{number}/pay")
async def site_shop_pay_again(site_id: str, number: str, request: Request):
    from .site import shoppay as SP
    b = await _shop_body(request)
    return await asyncio.to_thread(_shop_call, lambda: SP.again(site_id, number, str(b.get("token") or "")))


@app.post("/api/site-shop/{site_id}/order/{number}/review")
async def site_shop_review(site_id: str, number: str, request: Request):
    from .site import shoppay as SP
    b = await _shop_body(request)
    return await asyncio.to_thread(_shop_call, lambda: SP.review(site_id, number, str(b.get("token") or ""), str(b.get("slug") or ""),
                                                                 b.get("stars"), str(b.get("text") or "")))


@app.get("/api/site-shop/{site_id}/reviews")
async def site_shop_reviews(site_id: str, slug: str = ""):
    from .site import shoppay as SP
    return await asyncio.to_thread(_shop_call, lambda: SP.reviews(site_id, slug))


def _shop_owner(fn, *a):
    from .site import shop as SH
    from .site import webapp as W
    try:
        return fn(*a)
    except SH.ShopError as e:
        raise HTTPException(e.code, str(e))
    except W.AppError as e:
        raise HTTPException(e.code, str(e))


# ---- v0.538 HOOLA CMS (web Step 6 part 2, W8): her team - writers / editors / publishers - drafts, review, schedule, history
def _cms_call(fn):
    from .site import cms as CM
    from .site import webapp as W
    try:
        return JSONResponse(fn(), headers={**_SITE_APP_CORS, "Cache-Control": "no-store"})
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code, headers=_SITE_APP_CORS)
    except CM.CmsError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code)


def _cms_site(site_id: str) -> str:
    from .site import service as S
    from .site import webapp as W
    from .site.models import Site
    from .db import session as _s
    with _s() as s:
        if s.get(Site, site_id) is None:
            raise W.AppError("not found", 404)
    return site_id


def _cms_who(site_id: str, request: Request):
    from .site import cms as CM
    _cms_site(site_id)
    return CM.who(site_id, _site_tok(request))


@app.get("/cms/{site_id}/", response_class=HTMLResponse)
async def cms_page(site_id: str):
    """Her team's own page (works without her Hoola login): invite / login, drafts, page texts, review, publish, history."""
    page = (STATIC / "cms" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(page.replace("__SITE__", re.sub(r"[^A-Za-z0-9_-]", "", site_id)),
                        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex", "X-Frame-Options": "DENY",
                                 "Referrer-Policy": "no-referrer",          # the invite link never leaks in a Referer
                                 "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                                            "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
                                                            "form-action 'none'; frame-ancestors 'none'"})


@app.post("/api/site-cms/{site_id}/accept")
async def site_cms_accept(site_id: str, request: Request):
    from .site import cms as CM
    b = await _json_body(request)
    return await asyncio.to_thread(_cms_call, lambda: CM.accept(_cms_site(site_id), str(b.get("invite") or ""),
                                                                str(b.get("password") or ""), str(b.get("name") or "")))


@app.post("/api/site-cms/{site_id}/login")
async def site_cms_login(site_id: str, request: Request):
    from .site import cms as CM
    b = await _json_body(request)
    return await asyncio.to_thread(_cms_call, lambda: CM.login(_cms_site(site_id), str(b.get("email") or ""),
                                                               str(b.get("password") or ""), _ip(request)))


@app.get("/api/site-cms/{site_id}/home")
async def site_cms_home(site_id: str, request: Request, status: str = ""):
    """Me + the pages + the drafts I may see + the blog's posts (to edit one)."""
    from .site import blog as BL
    from .site import cms as CM

    def go():
        w = _cms_who(site_id, request)
        return {"me": CM._me(w.m), "pages": CM.pages(site_id), "drafts": CM.drafts(site_id, w, status),
                "posts": [{"slug": p["slug"], "title": p["title"], "status": p["status"]} for p in BL.posts(site_id)]}
    return await asyncio.to_thread(_cms_call, go)


@app.get("/api/site-cms/{site_id}/page/{slug:path}")
async def site_cms_page_texts(site_id: str, slug: str, request: Request):
    from .site import cms as CM

    def go():
        _cms_who(site_id, request)
        return {"texts": CM.page_texts(site_id, slug)}
    return await asyncio.to_thread(_cms_call, go)


@app.get("/api/site-cms/{site_id}/post/{slug}")
async def site_cms_post(site_id: str, slug: str, request: Request):
    from .site import blog as BL
    from .site import cms as CM

    def go():
        _cms_who(site_id, request)
        p = next((x for x in BL.posts(site_id) if x["slug"] == slug), None)
        if p is None:
            raise CM.CmsError("Post nahi mila.", 404)
        return {"post": {k: p.get(k) for k in ("slug", "title", "body", "excerpt", "category", "status")}}
    return await asyncio.to_thread(_cms_call, go)


@app.get("/api/site-cms/{site_id}/drafts/{did}")
async def site_cms_draft(site_id: str, did: str, request: Request):
    from .site import cms as CM
    return await asyncio.to_thread(_cms_call, lambda: CM.draft(site_id, _cms_who(site_id, request), did))


@app.post("/api/site-cms/{site_id}/drafts")
async def site_cms_draft_new(site_id: str, request: Request):
    from .site import cms as CM
    b = await _json_body(request)
    return await asyncio.to_thread(_cms_call, lambda: CM.save(site_id, _cms_who(site_id, request), b))


@app.put("/api/site-cms/{site_id}/drafts/{did}")
async def site_cms_draft_save(site_id: str, did: str, request: Request):
    from .site import cms as CM
    b = await _json_body(request)
    return await asyncio.to_thread(_cms_call, lambda: CM.save(site_id, _cms_who(site_id, request), b, did))


@app.post("/api/site-cms/{site_id}/drafts/{did}/move")
async def site_cms_draft_move(site_id: str, did: str, request: Request):
    """{to: review | approved | returned | published | scheduled | withdrawn, note?, when?}"""
    from .site import cms as CM
    b = await _json_body(request)
    return await asyncio.to_thread(_cms_call, lambda: CM.move(site_id, _cms_who(site_id, request), did, str(b.get("to") or ""),
                                                              str(b.get("note") or ""), str(b.get("when") or "")))


@app.get("/api/site-cms/{site_id}/history")
async def site_cms_history(site_id: str, request: Request, kind: str = "", target: str = ""):
    from .site import cms as CM

    def go():
        _cms_who(site_id, request)
        return {"history": CM.history(site_id, kind, target)}
    return await asyncio.to_thread(_cms_call, go)


@app.post("/api/site-cms/{site_id}/history/{rid}/restore")
async def site_cms_restore(site_id: str, rid: str, request: Request):
    from .site import cms as CM
    return await asyncio.to_thread(_cms_call, lambda: CM.restore(site_id, rid, _cms_who(site_id, request)))


def _cms_owner(tenant: str, ref: str):
    from .site import catalog as CAT
    return CAT._site(tenant, ref).id


@app.get("/api/sites/{ref}/cms", dependencies=[Depends(require_key)])
async def sites_cms(ref: str, tenant: str = Depends(current_tenant)):
    """Her view: the team, every draft, the history."""
    from .site import cms as CM

    def go():
        sid = _cms_owner(tenant, ref)
        w = CM.Who(owner=True, site_id=sid)
        return {"team": CM.team(sid), "drafts": CM.drafts(sid, w), "history": CM.history(sid)[:40], "site_id": sid}
    return await asyncio.to_thread(_cat_call, go)


@app.post("/api/sites/{ref}/cms/invite", dependencies=[Depends(require_key)])
async def sites_cms_invite(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap {email, name, role}: a one-time invite link to share (7 days)."""
    from .site import cms as CM
    b = body or {}
    base = (get_settings().public_base_url or "").rstrip("/")
    return await asyncio.to_thread(_cat_call, lambda: CM.invite(_cms_owner(tenant, ref), str(b.get("email") or ""),
                                                                 str(b.get("name") or ""), str(b.get("role") or "writer"), base))


@app.post("/api/sites/{ref}/cms/team/{mid}", dependencies=[Depends(require_key)])
async def sites_cms_member(ref: str, mid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import cms as CM
    b = body or {}
    return await asyncio.to_thread(_cat_call, lambda: CM.set_member(_cms_owner(tenant, ref), mid, str(b.get("role") or ""),
                                                                     bool(b.get("remove"))))


@app.post("/api/sites/{ref}/cms/drafts/{did}/move", dependencies=[Depends(require_key)])
async def sites_cms_move(ref: str, did: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her own tap on a team draft: approve / send back / publish now / schedule."""
    from .site import cms as CM
    b = body or {}

    def go():
        sid = _cms_owner(tenant, ref)
        return CM.move(sid, CM.Who(owner=True, site_id=sid), did, str(b.get("to") or ""), str(b.get("note") or ""), str(b.get("when") or ""))
    return await asyncio.to_thread(_cat_call, go)


@app.post("/api/sites/{ref}/cms/history/{rid}/restore", dependencies=[Depends(require_key)])
async def sites_cms_restore(ref: str, rid: str, tenant: str = Depends(current_tenant)):
    from .site import cms as CM

    def go():
        sid = _cms_owner(tenant, ref)
        return CM.restore(sid, rid, CM.Who(owner=True, site_id=sid))
    return await asyncio.to_thread(_cat_call, go)


# ---- v0.534 BADA CATALOGUE (web Step 6, W8): her products / doctors / properties from her file / Sheet / dataset -> pages
def _cat_call(fn, *a, **kw):
    from .site import catalog as CAT
    from .site import service as S
    from .site import webapp as W
    try:
        return fn(*a, **kw)
    except CAT.CatalogError as e:
        raise HTTPException(e.code, str(e))
    except S.SiteError as e:
        raise HTTPException(400, str(e))
    except W.AppError as e:                          # v0.534 the team CMS / webapp refusals carry their code
        raise HTTPException(e.code, str(e))
    except Exception as e:                           # her Sheet not joined / not found: said plainly
        if type(e).__name__ in ("NotConnected", "SheetError", "DataError"):
            raise HTTPException(400, str(e))
        raise


@app.get("/api/sites/{ref}/catalog", dependencies=[Depends(require_key)])
async def sites_catalog(ref: str, tenant: str = Depends(current_tenant)):
    from .site import catalog as CAT
    return await asyncio.to_thread(_cat_call, CAT.lists, tenant, ref)


@app.post("/api/sites/{ref}/catalog/preview", dependencies=[Depends(require_key)])
async def sites_catalog_preview(ref: str, request: Request, tenant: str = Depends(current_tenant)):
    """A file (multipart: file, coll, label, item_label, mapping JSON) or JSON {coll, sheet, tab | dataset, mapping}.
    Nothing is written: the answer says what WOULD happen; her Apply tap (with its hash) writes it."""
    from .site import catalog as CAT
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("multipart/"):
        form = await request.form()
        up = form.get("file")
        if up is None or not hasattr(up, "read"):
            raise HTTPException(400, "Choose a file (CSV / Excel).")
        raw = await up.read()
        b = {k: str(form.get(k) or "") for k in ("coll", "label", "item_label", "mapping")}
        try:
            mapping = json.loads(b["mapping"]) if b["mapping"] else None
        except ValueError:
            mapping = None

        def go():
            rows = CAT.parse_file(raw, getattr(up, "filename", "") or "")
            return CAT.preview(tenant, ref, b["coll"], rows, mapping, b["label"], b["item_label"], "file")
        return await asyncio.to_thread(_cat_call, go)
    b = await _json_body(request)

    def go2():
        if b.get("sheet"):
            rows, src = CAT.from_sheet(tenant, str(b["sheet"]), str(b.get("tab") or "") or None), "sheet"
        elif b.get("dataset"):
            rows, src = CAT.from_dataset(tenant, str(b["dataset"])), "dataset"
        else:
            raise CAT.CatalogError("File, Google Sheet ya dataset - koi ek chahiye.")
        return CAT.preview(tenant, ref, str(b.get("coll") or ""), rows, b.get("mapping") if isinstance(b.get("mapping"), dict) else None,
                           str(b.get("label") or ""), str(b.get("item_label") or ""), src)
    return await asyncio.to_thread(_cat_call, go2)


@app.post("/api/sites/{ref}/catalog/apply", dependencies=[Depends(require_key)])
async def sites_catalog_apply(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap {hash, replace?}: the preview she saw is written (replace = items not in the file are hidden, never deleted)."""
    from .site import catalog as CAT
    from .site import service as S
    b = body or {}

    def go():
        out = CAT.apply(tenant, ref, str(b.get("hash") or ""), bool(b.get("replace")))
        r = CAT._site(tenant, ref)
        if r.version:                                # her tap: the next checked version carries the pages (going live = her launch)
            S._after_edit(S._load(r.id), f"catalogue: {out['coll']}")
            out["say"] = out["say"].split(" Website ki")[0] + " Nayi version ban rahi hai (jaanch ke baad); live karna aapke tap se."
        return out
    return await asyncio.to_thread(_cat_call, go)


@app.post("/api/sites/{ref}/catalog/images", dependencies=[Depends(require_key)])
async def sites_catalog_images(ref: str, tenant: str = Depends(current_tenant)):
    """Fetch + resize the photos not made yet (resumes; runs in the background)."""
    from .site import catalog as CAT

    def go():
        r = CAT._site(tenant, ref)
        CAT.start_images(r.id)
        return CAT.lists(tenant, ref)
    return await asyncio.to_thread(_cat_call, go)


@app.delete("/api/sites/{ref}/catalog/{coll}", dependencies=[Depends(require_key)])
async def sites_catalog_remove(ref: str, coll: str, tenant: str = Depends(current_tenant)):
    from .site import catalog as CAT
    return await asyncio.to_thread(_cat_call, CAT.remove, tenant, ref, coll)

@app.post("/api/sites/{ref}/payments/connect", dependencies=[Depends(require_key)])
async def sites_payments_connect(ref: str, tenant: str = Depends(current_tenant)):
    """v0.446 her website's online payments live on its app project: link it, then the app pay routes take her keys."""
    from .site import shoppay as SP
    return await asyncio.to_thread(_shop_owner, SP.connect, tenant, ref)


@app.post("/api/sites/{ref}/shop/orders/{number}/refund", dependencies=[Depends(require_key)])
async def sites_shop_refund(ref: str, number: str, body: dict, tenant: str = Depends(current_tenant)):
    """HER tap only: refund a website order paid online {amount? (rupees, blank = all that is left), why}."""
    from .site import shoppay as SP
    b = body or {}
    return await asyncio.to_thread(_shop_owner, SP.refund, tenant, ref, number, b.get("amount"), str(b.get("why") or ""))


@app.get("/api/sites/{ref}/shop/reviews", dependencies=[Depends(require_key)])
async def sites_shop_reviews(ref: str, tenant: str = Depends(current_tenant)):
    from .site import shoppay as SP
    return {"reviews": await asyncio.to_thread(_shop_owner, SP.owner_reviews, tenant, ref)}


@app.post("/api/sites/{ref}/shop/reviews/{rid}", dependencies=[Depends(require_key)])
async def sites_shop_review_hide(ref: str, rid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import shoppay as SP
    return await asyncio.to_thread(_shop_owner, SP.hide_review, tenant, ref, rid, bool((body or {}).get("hide", True)))


# v0.452 DUKAAN PLUS: GST invoices for website orders, marketplace sellers, Shiprocket, opted-in cart reminders, AutoPay
@app.get("/api/site-app/{site_id}/pay/plans")
async def site_app_pay_plans(site_id: str, request: Request):
    return await _site_pub(site_id, "pay_plans", request)


@app.post("/api/site-app/{site_id}/pay/plans/{key}/subscribe")
async def site_app_pay_subscribe(site_id: str, key: str, request: Request):
    return await _site_pub(site_id, "pay_subscribe", request, key=key)


@app.get("/api/site-app/{site_id}/pay/subs")
async def site_app_pay_subs(site_id: str, request: Request):
    return await _site_pub(site_id, "pay_subs", request)


@app.post("/api/site-app/{site_id}/pay/subs/{sid}/cancel")
async def site_app_pay_cancel(site_id: str, sid: str, request: Request):
    return await _site_pub(site_id, "pay_cancel", request, sid=sid)


# ---- v0.459 ABHI ABHI WEBSITE (web Step 5, W6 + W7): live channel, live chat, presence, clinic queue, browser notifications,
# inbound webhooks - all on the website's linked app (site/livesite.py, appmaker/live.py, appmaker/baat.py, site/webpush.py).
@app.get("/api/site-app/{site_id}/live")
async def site_app_live(site_id: str, request: Request, colls: str = ""):
    """The website's live stream for a signed-in member (Bearer token in the header; ?last=j<id> replays a reconnect)."""
    from .appmaker import live as LV
    from .site import applink as AL
    from .site import livesite as LS
    from .site import webapp as W
    tok = _site_tok(request)

    def go():
        p, w = AL.live_open(site_id, tok)
        LV.admit(p, w)
        return p, w
    try:
        p, w = await asyncio.to_thread(go)
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code, headers=_SITE_APP_CORS)
    last = request.headers.get("last-event-id") or request.query_params.get("last") or ""
    member = w.m.id if w.m else ""
    return StreamingResponse(LV.stream(p, w, tok, colls, last, gone=request.is_disconnected,
                                       check=lambda: LS.still(site_id, p, tok, member)),
                             media_type="text/event-stream",
                             headers={**_SITE_APP_CORS, "Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/site-app/{site_id}/live/typing")
async def site_app_live_typing(site_id: str, request: Request):
    return await _site_pub(site_id, "typing", request, await _json_body(request))


@app.get("/api/site-app/{site_id}/live/presence")
async def site_app_live_presence(site_id: str, request: Request):
    return await _site_pub(site_id, "presence", request)


@app.get("/api/site-app/{site_id}/chat")
async def site_app_chat(site_id: str, request: Request, member: str = ""):
    """A member: her own thread. Staff: every thread (member= one thread)."""
    if member:
        return await _site_pub(site_id, "chat_thread", request, member=member)
    if request.query_params.get("all"):
        return await _site_pub(site_id, "chat_threads", request)
    return await _site_pub(site_id, "chat_mine", request)


@app.post("/api/site-app/{site_id}/chat")
async def site_app_chat_write(site_id: str, request: Request):
    return await _site_pub(site_id, "chat_write", request, await _json_body(request))


@app.post("/api/site-app/{site_id}/chat/{member}")
async def site_app_chat_reply(site_id: str, member: str, request: Request):
    return await _site_pub(site_id, "chat_reply", request, await _json_body(request), member=member)


@app.get("/api/site-app/{site_id}/push/key")
async def site_app_push_key(site_id: str, request: Request):
    return await _site_pub(site_id, "push_key", request)


@app.post("/api/site-app/{site_id}/push/subscribe")
async def site_app_push_sub(site_id: str, request: Request):
    """Only after the visitor's own tap AND the browser's permission (consent: true)."""
    return await _site_pub(site_id, "push_sub", request, await _json_body(request))


@app.post("/api/site-app/{site_id}/push/unsubscribe")
async def site_app_push_unsub(site_id: str, request: Request):
    return await _site_pub(site_id, "push_unsub", request, await _json_body(request))


@app.get("/api/site-app/{site_id}/queue")
async def site_app_queue(site_id: str, request: Request, mine: int = 0, staff: int = 0):
    """Public: the board (numbers only). mine=1: my token. staff=1: today's list with names (staff only)."""
    return await _site_pub(site_id, "queue_mine" if mine else "queue_staff" if staff else "queue_board", request)


@app.post("/api/site-app/{site_id}/queue/{step}")
async def site_app_queue_step(site_id: str, step: str, request: Request):
    ops = {"take": "queue_take", "add": "queue_add", "call": "queue_call", "mark": "queue_mark"}
    if step not in ops:
        return JSONResponse({"ok": False, "error": "not found"}, status_code=404, headers=_SITE_APP_CORS)
    return await _site_pub(site_id, ops[step], request, await _json_body(request))


@app.get("/api/site-app/{site_id}/queue/live")
async def site_app_queue_live(site_id: str, request: Request):
    """The public board as a stream (no login: numbers only), for the waiting-room TV and the site's own pages."""
    from .site import applink as AL
    from .site import livesite as LS
    from .site import webapp as W
    ip = _ip(request)

    def go():
        p = AL.queue_project(site_id)
        LS.board_admit(ip)
        return p
    try:
        p = await asyncio.to_thread(go)
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code, headers=_SITE_APP_CORS)
    return StreamingResponse(LS.board_stream(p, ip, gone=request.is_disconnected), media_type="text/event-stream",
                             headers={**_SITE_APP_CORS, "Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/site-app/{site_id}/queue/board", response_class=HTMLResponse)
async def site_app_queue_board(site_id: str):
    """A full-screen live board for the clinic's TV: now serving, next, how many wait. No names, no phones."""
    from .site import applink as AL
    from .site import livesite as LS
    from .site import webapp as W
    try:
        p = await asyncio.to_thread(AL.queue_project, site_id)
        label = (await asyncio.to_thread(LS.cfg, p)).get("label") or "Queue"
    except W.AppError:
        return HTMLResponse("<!doctype html><title>Not found</title><p>Not found.</p>", status_code=404)
    return HTMLResponse(LS.board_page(site_id, label), headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})


@app.post("/api/dhara/hook/{token}")
async def dhara_hook(token: str, request: Request):
    """v0.502 DHARA webhook trigger: her outside service calls the workflow in. The token is checked
    sha256-hashed against the workflow row; the body lands as {{vars.body}}; the run is queued with a
    checkpoint (the worker executes it). Rate: one run per 6 s per workflow (10/min ceiling)."""
    from .agent import dhara_tools
    raw = await request.body()
    if len(raw) > 256_000:
        return JSONResponse({"ok": False, "error": "body bohot bada"}, status_code=413)
    try:
        body = json.loads(raw or b"{}")
        if not isinstance(body, dict):
            body = {"body": body}
    except Exception:
        body = {"raw": raw[:8000].decode("utf-8", "ignore")}
    out = await asyncio.to_thread(dhara_tools.webhook_enqueue, token, body)
    return JSONResponse({"ok": out["ok"], "run_id": out.get("run_id"), "workflow": out.get("workflow"),
                         "error": out.get("error")}, status_code=int(out.get("status") or 500))


@app.post("/api/site-app/{site_id}/hook/{key}")
async def site_app_hook(site_id: str, key: str, request: Request):
    """Her outside service tells the website's app something (signed with HER secret; the payload is data)."""
    raw = (await request.body())[:1_000_000]
    return await _site_pub(site_id, "hook", request, key=key, raw=raw, headers=dict(request.headers))


# her own controls (console / phone): the queue of any of her apps or linked websites, by app id / number
@app.get("/api/apps/{ref}/queue", dependencies=[Depends(require_key)])
async def apps_queue(ref: str, tenant: str = Depends(current_tenant)):
    from .site import livesite as LS
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: LS.staff_view(_be_data(tenant, ref), W.Who(owner=True)))


@app.put("/api/apps/{ref}/queue", dependencies=[Depends(require_key)])
async def apps_queue_settings(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import livesite as LS
    from .site import webapp as W

    def go():
        p = _be_data(tenant, ref)
        LS.save_cfg(p, body or {})
        return LS.staff_view(p, W.Who(owner=True))
    return await asyncio.to_thread(_be_owner_call, go)


@app.post("/api/apps/{ref}/queue/{step}", dependencies=[Depends(require_key)])
async def apps_queue_step(ref: str, step: str, body: dict, tenant: str = Depends(current_tenant)):
    """{name, phone} add · {token?} call (next) · {token, status} mark."""
    from .site import livesite as LS
    from .site import webapp as W
    b, who = body or {}, W.Who(owner=True)

    def go():
        p = _be_data(tenant, ref)
        if step == "add":
            return LS.add(p, who, b)
        if step == "call":
            n = b.get("token")
            return LS.call_next(p, who, int(n) if str(n or "").isdigit() else None)
        if step == "mark":
            return LS.mark(p, who, int(b.get("token") or 0), str(b.get("status") or ""))
        raise W.AppError("not found", 404)
    return await asyncio.to_thread(_be_owner_call, go)


@app.get("/api/apps/{ref}/push", dependencies=[Depends(require_key)])
async def apps_push(ref: str, tenant: str = Depends(current_tenant)):
    """How many browsers said yes to notifications on this app's website (never who)."""
    from .appmaker import backend as BE
    from .site import webpush as WP
    return await asyncio.to_thread(_be_owner_call, lambda: WP.status(BE.bid(_be_data(tenant, ref))))


def _pdf_resp(go):
    from .site import shop as SH
    try:
        data, name = go()
    except SH.ShopError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code, headers=_SHOP_CORS)
    return Response(data, media_type="application/pdf", headers={**_SHOP_CORS, "Cache-Control": "private, no-store",
                                                                 "Content-Disposition": f'inline; filename="{name}.pdf"'})


@app.get("/api/site-shop/{site_id}/order/{number}/invoice")
async def site_shop_invoice(site_id: str, number: str, t: str = "", doc: str = ""):
    """The buyer's own GST invoice / credit note (by the order's private link)."""
    from .site import shop as SH
    from .site import shopplus as SPL
    from .db import session as _ses

    def go():
        with _ses() as s:
            SH._mine(s, site_id, number, t)
        return SPL.invoice_pdf(site_id, number, "credit" if doc == "credit" else "")
    return await asyncio.to_thread(_pdf_resp, go)


@app.get("/api/site-shop/{site_id}/order/{number}/track")
async def site_shop_courier_track(site_id: str, number: str, t: str = ""):
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_call, lambda: SPL.track(site_id, number, t))


@app.post("/api/site-shop/{site_id}/vendor/apply")
async def site_shop_vendor_apply(site_id: str, request: Request):
    from .site import shopplus as SPL
    b = await _shop_body(request)
    return await asyncio.to_thread(_shop_call, lambda: SPL.apply_vendor(site_id, b, _ip(request)))


@app.get("/api/site-shop/{site_id}/vendor/{token}")
async def site_shop_vendor_portal(site_id: str, token: str):
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_call, lambda: SPL.vendor_portal(site_id, token))


@app.post("/api/site-shop/{site_id}/vendor/{token}/product")
async def site_shop_vendor_product(site_id: str, token: str, request: Request):
    from .site import shopplus as SPL
    b = await _shop_body(request)
    return await asyncio.to_thread(_shop_call, lambda: SPL.vendor_add_product(site_id, token, b))


@app.get("/api/site-shop/{site_id}/seller", response_class=HTMLResponse)
async def site_shop_seller_page(site_id: str):
    """The seller page (apply + the private seller dashboard when ?k=<their link>)."""
    from .site import shopplus as SPL
    return HTMLResponse(SPL.SELLER_PAGE.replace("__API__", f"/api/site-shop/{site_id}"),
                        headers={"Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                                            "connect-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'"})


@app.post("/api/site-shop/{site_id}/cart/remind")
async def site_shop_cart_hold(site_id: str, request: Request):
    from .site import shopplus as SPL
    b = await _shop_body(request)
    return await asyncio.to_thread(_shop_call, lambda: SPL.hold_cart(site_id, b, _ip(request)))


@app.post("/api/site-shop/{site_id}/cart/stop")
async def site_shop_cart_stop(site_id: str, request: Request):
    from .site import shopplus as SPL
    b = await _shop_body(request)
    return await asyncio.to_thread(_shop_call, lambda: SPL.stop_cart(site_id, str(b.get("token") or "")))


@app.get("/api/sites/{ref}/shop/orders/{number}/invoice", dependencies=[Depends(require_key)])
async def sites_shop_invoice(ref: str, number: str, doc: str = "", gstin: str = "", tenant: str = Depends(current_tenant)):
    """Her tax invoice (buyer GSTIN optional, for a B2B bill) / credit note of a website order."""
    from .site import shopplus as SPL

    def go():
        return SPL.invoice_pdf(SPL._site_id(tenant, ref), number, "credit" if doc == "credit" else "", gstin.strip().upper()[:15])
    return await asyncio.to_thread(_pdf_resp, go)


@app.get("/api/sites/{ref}/shop/vendors", dependencies=[Depends(require_key)])
async def sites_shop_vendors(ref: str, tenant: str = Depends(current_tenant)):
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_owner, SPL.vendors, tenant, ref)


@app.post("/api/sites/{ref}/shop/vendors/{vid}", dependencies=[Depends(require_key)])
async def sites_shop_vendor_set(ref: str, vid: str, body: dict, tenant: str = Depends(current_tenant)):
    """HER tap: approve / block a seller, their commission %, their Razorpay Route linked account."""
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_owner, SPL.set_vendor, tenant, ref, vid, body or {})


@app.post("/api/sites/{ref}/shop/products/{slug}/approve", dependencies=[Depends(require_key)])
async def sites_shop_product_ok(ref: str, slug: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_owner, SPL.approve_product, tenant, ref, slug, bool((body or {}).get("ok", True)))


@app.put("/api/sites/{ref}/shop/courier", dependencies=[Depends(require_key)])
async def sites_shop_courier(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her Shiprocket API user (typed here only, checked with a real login, sealed, returned by no route)."""
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_owner, SPL.set_courier, tenant, ref, body or {})


@app.get("/api/sites/{ref}/shop/courier", dependencies=[Depends(require_key)])
async def sites_shop_courier_view(ref: str, tenant: str = Depends(current_tenant)):
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_owner, lambda: SPL.courier_view(SPL._site_id(tenant, ref)))


@app.post("/api/sites/{ref}/shop/orders/{number}/ship", dependencies=[Depends(require_key)])
async def sites_shop_ship(ref: str, number: str, tenant: str = Depends(current_tenant)):
    """HER tap: Shiprocket order + AWB + label for a confirmed order."""
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_owner, SPL.ship, tenant, ref, number)


@app.get("/api/sites/{ref}/shop/carts", dependencies=[Depends(require_key)])
async def sites_shop_carts(ref: str, tenant: str = Depends(current_tenant)):
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_owner, SPL.carts, tenant, ref)


@app.post("/api/sites/{ref}/shop/carts/{cid}/reminded", dependencies=[Depends(require_key)])
async def sites_shop_cart_reminded(ref: str, cid: str, tenant: str = Depends(current_tenant)):
    from .site import shopplus as SPL
    return await asyncio.to_thread(_shop_owner, SPL.mark_reminded, tenant, ref, cid)


@app.get("/api/sites/{ref}/shop", dependencies=[Depends(require_key)])
async def sites_shop(ref: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.shop_info, tenant, ref)


@app.post("/api/sites/{ref}/shop", dependencies=[Depends(require_key)])
async def sites_shop_setup(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her shop: {settings: {on, cod, pickup, delivery, free_above, min_order, pincodes, upi}, products: [...], from_lists}."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.shop_setup, tenant, ref,
                                   body.get("settings") if isinstance(body.get("settings"), dict) else None,
                                   body.get("products") if isinstance(body.get("products"), list) else None,
                                   bool(body.get("from_lists")))


@app.get("/api/sites/{ref}/shop/orders", dependencies=[Depends(require_key)])
async def sites_shop_orders(ref: str, status: str = "", tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.shop_orders, tenant, ref, status)


@app.post("/api/sites/{ref}/shop/orders/{number}", dependencies=[Depends(require_key)])
async def sites_shop_move(ref: str, number: str, body: dict, tenant: str = Depends(current_tenant)):
    """HER tap on an order: confirmed (after she sees the money) / packed / shipped / delivered / cancelled."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.shop_move, tenant, ref, number, str(body.get("to") or ""))


# ---- v0.301 bookings from her website: her real free slots (public, read-only) + a visitor's request (public)
_SITE_SLOT_CORS = {**_SITE_FORM_CORS, "Access-Control-Allow-Methods": "GET, POST, OPTIONS"}


@app.options("/api/site-forms/{site_id}/slots")
@app.options("/api/site-forms/{site_id}/book")
async def site_booking_cors(site_id: str):
    return Response(status_code=204, headers=_SITE_SLOT_CORS)


@app.get("/api/site-forms/{site_id}/slots")
async def site_slots(site_id: str):
    """Public: the next free times from her own booking book (no names, no booked details - only free times)."""
    from .site import service as S
    try:
        out = await asyncio.to_thread(S.site_slots, site_id)
    except Exception:
        out = {"slots": []}
    return JSONResponse(out, headers={**_SITE_SLOT_CORS, "Cache-Control": "no-store"})


@app.post("/api/site-forms/{site_id}/book")
async def site_book(site_id: str, request: Request):
    """Public: a visitor asks for one of her free times -> a booking REQUEST she confirms or declines."""
    from .site import service as S
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "bad form")
    ip = (request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip") or
          (request.client.host if request.client else ""))
    try:
        out = await asyncio.to_thread(S.book_post, site_id, body, ip)
    except S.SiteError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400, headers=_SITE_SLOT_CORS)
    return JSONResponse({"ok": bool(out.get("ok"))}, headers=_SITE_SLOT_CORS)


@app.post("/api/sites-bookings/{lead_id}/decide", dependencies=[Depends(require_key)])
async def site_booking_decide(lead_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """HER tap: confirm or decline a website booking request."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.booking_decide, tenant, lead_id, bool(body.get("yes")))


# ---------------------------------------------------------------- v0.122 Website hosting: launch, rollback, her domain, DNS
def _host(fn, *a, **k):
    from .site import dns as D
    from .site import hosting as H
    from .site import service as S
    try:
        return fn(*a, **k)
    except (H.HostError, D.DnsError, S.SiteError) as e:
        raise HTTPException(400, str(e))
    except Exception as e:                       # v0.123 domain errors carry plain words too
        from .site import domains as DM
        if isinstance(e, DM.DomainError):
            raise HTTPException(400, str(e))
        raise


@app.get("/api/sites/{ref}/hosting", dependencies=[Depends(require_key)])
async def sites_hosting(ref: str, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.status, tenant, ref)


@app.post("/api/sites/{ref}/launch-request", dependencies=[Depends(require_key)])
async def sites_launch_request(ref: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    body = body or {}
    return await asyncio.to_thread(_host, H.launch_request, tenant, ref, body.get("free", True) is not False,
                                   str(body.get("conversation_id") or ""))


@app.post("/api/sites/{ref}/launch", dependencies=[Depends(require_key)])
async def sites_launch(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on 'Haan, live karo' (the card's hash must match the checked version and addresses)."""
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.launch, tenant, ref, str(body.get("hash") or ""), body.get("free", True) is not False)


@app.post("/api/sites/{ref}/rollback-request", dependencies=[Depends(require_key)])
async def sites_rollback_request(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.rollback_request, tenant, ref, int(body.get("version") or 0))


@app.post("/api/sites/{ref}/rollback", dependencies=[Depends(require_key)])
async def sites_rollback(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.rollback, tenant, ref, int(body.get("version") or 0), str(body.get("hash") or ""))


@app.post("/api/sites/{ref}/takedown", dependencies=[Depends(require_key)])
async def sites_takedown(ref: str, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.take_down, tenant, ref)


@app.post("/api/sites/{ref}/domain", dependencies=[Depends(require_key)])
async def sites_domain(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.connect_domain, tenant, ref, str(body.get("domain") or ""),
                                   str(body.get("conversation_id") or ""), str(body.get("primary") or ""))


@app.post("/api/sites/{ref}/primary", dependencies=[Depends(require_key)])
async def sites_primary(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.280 her choice of the main address of her domain (root or www); the other redirects to it."""
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.set_primary, tenant, ref, str(body.get("host") or ""))


@app.post("/api/sites-dns/{plan_id}/apply", dependencies=[Depends(require_key)])
async def sites_dns_apply(plan_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap on the DNS card."""
    from .site import hosting as H
    return await asyncio.to_thread(_host, H.dns_apply, tenant, plan_id, str(body.get("hash") or ""))


@app.post("/api/sites-dns/{plan_id}/undo", dependencies=[Depends(require_key)])
async def sites_dns_undo(plan_id: str, tenant: str = Depends(current_tenant)):
    from .site import dns as D
    return await asyncio.to_thread(_host, D.undo, tenant, plan_id)


@app.get("/api/sites-dns/{plan_id}/check", dependencies=[Depends(require_key)])
async def sites_dns_check(plan_id: str, tenant: str = Depends(current_tenant)):
    from .site import dns as D
    return await asyncio.to_thread(_host, D.check, tenant, plan_id)


@app.post("/api/sites/{ref}/email-dns", dependencies=[Depends(require_key)])
async def sites_email_dns(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{domain, provider google|zoho, report_to} -> a DNS plan card for email at her domain (applied on her tap)."""
    from .site import dns as D
    from .site import service as S

    def go():
        with __import__("app.db", fromlist=["session"]).session() as s:
            r = S._find(s, tenant, ref)
            sid = r.id
        d = D.norm_domain(str(body.get("domain") or ""))
        return D.make_plan(tenant, sid, d, D.email_records(d, str(body.get("provider") or ""), str(body.get("report_to") or "")),
                           "email")
    return await asyncio.to_thread(_host, go)


@app.get("/api/sites-keys", dependencies=[Depends(require_key)])
async def sites_keys(tenant: str = Depends(current_tenant)):
    from .site import dns as D
    return {"keys": await asyncio.to_thread(D.keys, tenant)}


@app.put("/api/sites-keys/{provider}", dependencies=[Depends(require_key)])
async def sites_key_set(provider: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her own Cloudflare / Porkbun key, typed in the app only (never in chat); verified, then sealed."""
    from .site import dns as D
    return await asyncio.to_thread(_host, D.set_key, tenant, provider, str(body.get("token") or ""), str(body.get("secret") or ""))


@app.delete("/api/sites-keys/{provider}", dependencies=[Depends(require_key)])
async def sites_key_forget(provider: str, tenant: str = Depends(current_tenant)):
    from .site import dns as D
    return await asyncio.to_thread(_host, D.forget_key, tenant, provider)


@app.get("/api/hosting/ask")
async def hosting_ask(domain: str = ""):
    """For an optional Caddy in front (on-demand TLS): 200 only for hostnames of launched Hoola sites."""
    from .site import hosting as H
    # v0.224 the cached map (refreshed every 20 s and on every launch): a public endpoint must not force a DB read +
    # folder sync on every call
    # v0.280 a direct-mode domain only once its records point here (H.ask_ok)
    return Response(status_code=200 if await asyncio.to_thread(H.ask_ok, domain) else 404)


@app.get("/api/sites-uptime")
async def sites_uptime_list(request: Request):
    """v0.224 the outside uptime checker (GitHub Actions, off this server) asks which addresses to open. Needs
    SITES_UPTIME_KEY in the X-Uptime-Key header; without the setting the endpoint does not exist."""
    from .site import hosting as H
    if not H.uptime_key_ok(request.headers.get("x-uptime-key", "")):
        raise HTTPException(404, "Not Found")
    return {"hosts": await asyncio.to_thread(H.uptime_targets)}


@app.post("/api/sites-uptime")
async def sites_uptime_report(request: Request):
    from .site import hosting as H
    if not H.uptime_key_ok(request.headers.get("x-uptime-key", "")):
        raise HTTPException(404, "Not Found")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "bad json")
    results = body.get("results") if isinstance(body, dict) else None
    if not isinstance(results, list):
        raise HTTPException(400, "a results list is needed")
    return {"ok": True, "recorded": await asyncio.to_thread(H.outside_report, [r for r in results if isinstance(r, dict)])}


# ---------------------------------------------------------------- v0.123 Domains (ideas, live price, buy on her fingerprint tap)
@app.get("/api/sites-domains", dependencies=[Depends(require_key)])
async def sites_domains(tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    from .site import dns as D
    return {"domains": await asyncio.to_thread(DM.domains, tenant), "keys": await asyncio.to_thread(D.keys, tenant),
            "month_spent_inr": await asyncio.to_thread(DM._month_spent, tenant), "month_limit_inr": DM._ceiling()}


@app.post("/api/sites-domains/ideas", dependencies=[Depends(require_key)])
async def sites_domain_ideas(body: dict, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    return await asyncio.to_thread(_host, DM.suggest, tenant, str(body.get("site") or ""), str(body.get("name") or ""),
                                   str(body.get("city") or ""))


@app.post("/api/sites-domains/check", dependencies=[Depends(require_key)])
async def sites_domain_check(body: dict, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    doms = [str(d) for d in (body.get("domains") or [])][:20]
    return {"results": await asyncio.to_thread(_host, DM.check, tenant, doms)}


@app.post("/api/sites-domains/request", dependencies=[Depends(require_key)])
async def sites_domain_request(body: dict, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    return await asyncio.to_thread(_host, DM.buy_request, tenant, str(body.get("site") or ""), str(body.get("domain") or ""),
                                   bool(body.get("auto_renew")), "",
                                   body.get("registrant") if isinstance(body.get("registrant"), dict) else None)


@app.post("/api/sites-domains/{oid}/buy", dependencies=[Depends(require_key)])
async def sites_domain_buy(oid: str, body: dict, tenant: str = Depends(current_tenant)):
    """ONLY her tap on the domain card; fingerprint-signed once a phone key is set up (money, no refunds)."""
    from .site import domains as DM
    _fingerprint(tenant, "domain", oid, body.get("proof"))
    return await asyncio.to_thread(_host, DM.buy, tenant, oid, str(body.get("hash") or ""))


@app.post("/api/sites-domains/{oid}/cancel", dependencies=[Depends(require_key)])
async def sites_domain_cancel(oid: str, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    return await asyncio.to_thread(_host, DM.cancel, tenant, oid)


@app.post("/api/sites-domains/kyc", dependencies=[Depends(require_key)])
async def sites_domain_kyc(body: dict, tenant: str = Depends(current_tenant)):
    from .site import domains as DM
    return await asyncio.to_thread(_host, DM.kyc_done, tenant, str(body.get("domain") or ""))


# ---------------------------------------------------------------- v0.124 Website care + agency + GitHub export
def _care(fn, *a, **k):
    from .site import github as GH
    try:
        return _host(fn, *a, **k)
    except GH.GithubError as e:
        raise HTTPException(400, str(e))


@app.get("/api/sites/{ref}/code", dependencies=[Depends(require_key)])
async def sites_code(ref: str, path: str = "", tenant: str = Depends(current_tenant)):
    """v0.373 CODE MODE: the site's files (no path) or one file's code."""
    from .site import service as S
    if path:
        return await asyncio.to_thread(_site, S.code_read, tenant, ref, path)
    return await asyncio.to_thread(_site, S.code_tree, tenant, ref)


@app.put("/api/sites/{ref}/code", dependencies=[Depends(require_key)])
async def sites_code_write(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her own hand on one file {path, code}: cleaned like any build, one Undo step, then a checked version."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.code_write, tenant, ref, str(body.get("path") or ""), str(body.get("code") or ""))


@app.post("/api/sites/{ref}/code/ask", dependencies=[Depends(require_key)])
async def sites_code_ask(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her words -> Opus changes the code (a site job); read the result at /code/task/<task>."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.code_ask, tenant, ref, str(body.get("instruction") or ""),
                                   str(body.get("path") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/sites/{ref}/code/task/{task}", dependencies=[Depends(require_key)])
async def sites_code_task(ref: str, task: str, tenant: str = Depends(current_tenant)):
    from .site import service as S
    return await asyncio.to_thread(_site, S.code_task, tenant, ref, task)


@app.get("/api/sites/{ref}/blog", dependencies=[Depends(require_key)])
async def sites_blog(ref: str, tenant: str = Depends(current_tenant)):
    """v0.366 BLOG: her posts (published / scheduled / hidden) + the site's languages."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.blog_info, tenant, ref)


@app.post("/api/sites/{ref}/blog/{slug}", dependencies=[Depends(require_key)])
async def sites_blog_act(ref: str, slug: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap in the Blog tab: hide / show / delete / cover (the change reaches her live address too)."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.blog_act, tenant, ref, slug, str(body.get("action") or ""),
                                   str(body.get("cover") or ""), True)


@app.post("/api/sites/{ref}/languages", dependencies=[Depends(require_key)])
async def sites_languages(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.366 BHASHAYEN: the site's extra languages (up to 4; [] = only the first)."""
    from .site import service as S
    return await asyncio.to_thread(_site, S.set_languages, tenant, ref, body.get("languages") or [])


@app.get("/api/sites/{ref}/dashboard", dependencies=[Depends(require_key)])
async def sites_dashboard(ref: str, days: int = 30, tenant: str = Depends(current_tenant)):
    """v0.357 DASHBOARD: her website's numbers per day (visits, enquiries, orders, sales, web-app records) for charts."""
    from .site import dash as SD
    return await asyncio.to_thread(_care, SD.dashboard, tenant, ref, max(7, min(days, 365)))


def _inspire(fn, *a, **k):
    from .site import inspire as IN
    from .site import service as S
    try:
        return fn(*a, **k)
    except IN.InspireError as e:
        return JSONResponse({"ok": False, "detail": str(e), "error": str(e), **e.extra}, status_code=e.code)
    except S.SiteError as e:
        raise HTTPException(400, str(e))


@app.post("/api/site-design/read", dependencies=[Depends(require_key)])
async def site_design_read(request: Request, tenant: str = Depends(current_tenant)):
    """v0.567 KOI BHI DESIGN: a PREVIEW of a design from her screenshot (multipart file / file_id), her Figma file (url)
    or her OWN old website (url, ownership proven). Nothing on any site changes."""
    from .site import inspire as IN
    ct = request.headers.get("content-type", "")
    if ct.startswith("multipart/"):
        form = await request.form()
        up = form.get("file")
        data = await up.read() if up is not None and hasattr(up, "read") else None
        return await asyncio.to_thread(_inspire, IN.read, tenant, "screenshot", "", str(form.get("file_id") or ""), data)
    b = await request.json()
    return await asyncio.to_thread(_inspire, IN.read, tenant, str(b.get("source") or ""), str(b.get("url") or ""),
                                   str(b.get("file_id") or ""))


@app.post("/api/site-design/use", dependencies=[Depends(require_key)])
async def site_design_use(body: dict, tenant: str = Depends(current_tenant)):
    """v0.567 HER tap: the previewed design goes on a site (new when none named); look 1 is then hers."""
    from .site import inspire as IN
    b = body or {}
    return await asyncio.to_thread(_inspire, IN.use, tenant, str(b.get("token") or ""), str(b.get("site") or ""), "",
                                   str(b.get("brief") or ""), bool(b.get("keep")))


def _moved(fn, *a, **k):
    from .site import moved as MV
    from .site import service as S
    try:
        return fn(*a, **k)
    except MV.MovedError as e:
        return JSONResponse({"ok": False, "detail": str(e), "error": str(e)}, status_code=e.code)
    except S.SiteError as e:
        raise HTTPException(400, str(e))


@app.get("/api/sites/{ref}/moves", dependencies=[Depends(require_key)])
async def sites_moves(ref: str, quiet: int = 0, tenant: str = Depends(current_tenant)):
    """v0.622 KOI PATA NA KHOYE: her old site's addresses -> the new pages (a proposal; nothing served until her tap).
    v0.663 quiet=1 (the Studio's Publish view): a site with no old site answers {"none": true}, not a 404."""
    from .site import moved as MV
    out = await asyncio.to_thread(_moved, MV.propose, tenant, ref)
    if quiet and isinstance(out, JSONResponse) and out.status_code == 404:
        return {"none": True, "rows": []}
    return out


@app.post("/api/sites/{ref}/moves", dependencies=[Depends(require_key)])
async def sites_moves_apply(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """HER tap: the list she saw (hash) becomes live 301s; `drop` = rows she unticked, `change` = {old: new page path}."""
    from .site import moved as MV
    b = body or {}
    return await asyncio.to_thread(_moved, MV.apply, tenant, ref, str(b.get("hash") or ""),
                                   [str(x) for x in (b.get("drop") or [])][:500],
                                   {str(k): str(v) for k, v in (b.get("change") or {}).items()} if isinstance(b.get("change"), dict) else None)


@app.post("/api/sites/{ref}/compare-old", dependencies=[Depends(require_key)])
async def sites_compare_old(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.622 her old page next to the new one at the same width; the differences listed for her."""
    from .site import moved as MV
    b = body or {}
    return await asyncio.to_thread(_moved, MV.compare, tenant, ref, str(b.get("old") or "/"), str(b.get("page") or ""))


@app.get("/api/sites/{ref}/compare-old/{name}", dependencies=[Depends(require_key)])
async def sites_compare_old_file(ref: str, name: str, tenant: str = Depends(current_tenant)):
    from .site import moved as MV
    try:
        data = await asyncio.to_thread(MV.compare_file, tenant, ref, name)
    except MV.MovedError as e:
        raise HTTPException(e.code, str(e))
    return Response(content=data, media_type="image/png" if name.endswith(".png") else "application/json")


@app.get("/api/site-design/figma", dependencies=[Depends(require_key)])
async def site_design_figma(tenant: str = Depends(current_tenant)):
    from .site import inspire as IN
    return await asyncio.to_thread(IN.figma_status, tenant)


@app.put("/api/site-design/figma", dependencies=[Depends(require_key)])
async def site_design_figma_set(body: dict, tenant: str = Depends(current_tenant)):
    """v0.567 her Figma personal access token, typed in the console only; sealed on arrival, returned by no route."""
    from .site import inspire as IN
    return await asyncio.to_thread(_inspire, IN.set_figma_token, tenant, str((body or {}).get("token") or ""))


@app.delete("/api/site-design/figma", dependencies=[Depends(require_key)])
async def site_design_figma_forget(tenant: str = Depends(current_tenant)):
    from .site import inspire as IN
    return await asyncio.to_thread(IN.forget_figma, tenant)


@app.get("/api/sites/{ref}/ops", dependencies=[Depends(require_key)])
async def sites_ops(ref: str, days: int = 30, tenant: str = Depends(current_tenant)):
    """v0.564 CHALTI WEBSITE: visitors' errors, real-visit speed (p75 bands), AI cost, backup + restore test."""
    from .site import ops as OPS
    return await asyncio.to_thread(_care, OPS.owner_view, tenant, ref, max(1, min(days, 90)))


@app.get("/api/sites/{ref}/care", dependencies=[Depends(require_key)])
async def sites_care(ref: str, days: int = 30, tenant: str = Depends(current_tenant)):
    from .site import care as SC
    return await asyncio.to_thread(_care, SC.report, tenant, ref, max(1, min(days, 365)))


@app.get("/api/sites-clients", dependencies=[Depends(require_key)])
async def sites_clients(tenant: str = Depends(current_tenant)):
    from .site import care as SC
    return {"clients": await asyncio.to_thread(SC.clients, tenant)}


@app.post("/api/sites/{ref}/assign", dependencies=[Depends(require_key)])
async def sites_assign(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import care as SC
    return await asyncio.to_thread(_care, SC.assign, tenant, ref,
                                   body.get("client") if "client" in body else None, body.get("staff") if "staff" in body else None)


@app.get("/api/sites/{ref}/github", dependencies=[Depends(require_key)])
async def sites_github_list(ref: str, tenant: str = Depends(current_tenant)):
    from .site import github as GH
    from .site import service as S

    def run():
        with session() as s:
            sid = S._find(s, tenant, ref).id
        return {"exports": GH.exports(tenant, sid)}
    return await asyncio.to_thread(_care, run)


@app.post("/api/sites/{ref}/github-request", dependencies=[Depends(require_key)])
async def sites_github_request(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .site import github as GH
    return await asyncio.to_thread(_care, GH.request, tenant, ref, str(body.get("repo") or ""), body.get("private", True) is not False)


@app.post("/api/sites-github/{eid}/push", dependencies=[Depends(require_key)])
async def sites_github_push(eid: str, body: dict, tenant: str = Depends(current_tenant)):
    """ONLY her tap on the GitHub card."""
    from .site import github as GH
    return await asyncio.to_thread(_care, GH.push, tenant, eid, str(body.get("hash") or ""))


@app.post("/api/sites-github/{eid}/cancel", dependencies=[Depends(require_key)])
async def sites_github_cancel(eid: str, tenant: str = Depends(current_tenant)):
    from .site import github as GH
    return await asyncio.to_thread(_care, GH.cancel, tenant, eid)


# ---------------------------------------------------------------- v0.128 App Sahayak (every screen designed + prototype first)
def _appd(fn, *a, **k):
    from .appmaker import service as A
    try:
        return fn(*a, **k)
    except A.AppError as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, f"not found: {e}")


@app.get("/api/apps", dependencies=[Depends(require_key)])
async def apps_all(tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.everything, tenant)


@app.post("/api/apps", dependencies=[Depends(require_key)])
async def apps_new(body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    ans = body.get("answers") if isinstance(body.get("answers"), dict) else None
    return await asyncio.to_thread(_appd, A.new, tenant, str(body.get("brief") or ""), str(body.get("conversation_id") or ""),
                                   str(body.get("name") or ""), str(body.get("field") or ""), str(body.get("goal") or ""),
                                   str(body.get("style") or ""), ans, str(body.get("idea") or ""))


@app.get("/api/apps-ideas", dependencies=[Depends(require_key)])
async def apps_ideas(q: str = "", field: str = "", goal: str = "", aud: str = "", offset: int = 0, limit: int = 30):
    """v0.136 the 1 crore app idea list: her words -> the best precise idea + near ones; or walk the list page by page."""
    from .appmaker import ideas as I

    def go():
        out = I.browse(q, field, goal, aud, offset, limit)
        if q and not offset:
            u = I.understand(q, field, goal)
            out["best"] = u.get("idea")
            out["near"] = u.get("alternatives", [])
            out["ask"] = u.get("ask", "")
        out["all_ideas"] = I.total()
        return out
    return await asyncio.to_thread(go)


@app.get("/api/apps-ideas/{idea_id}", dependencies=[Depends(require_key)])
async def apps_idea(idea_id: str):
    from .appmaker import ideas as I
    try:
        return await asyncio.to_thread(I.idea, idea_id)
    except KeyError:
        raise HTTPException(404, "idea not found")


@app.get("/api/apps-library", dependencies=[Depends(require_key)])
async def apps_library(industry: str = "", q: str = "", offset: int = 0, limit: int = 60):
    from .appmaker import library as AL
    return await asyncio.to_thread(AL.browse, industry, q, max(1, min(limit, 200)), max(0, offset))


@app.get("/api/apps-library/brief", dependencies=[Depends(require_key)])
async def apps_library_brief(field: str, goal: str = "", style: str = ""):
    from .appmaker import library as AL
    try:
        return await asyncio.to_thread(AL.brief, field, goal, style)
    except KeyError:
        raise HTTPException(404, "field not found")


@app.get("/api/apps-library/understand", dependencies=[Depends(require_key)])
async def apps_library_understand(q: str):
    from .appmaker import library as AL
    return await asyncio.to_thread(AL.understand, q)


@app.get("/api/apps/{ref}", dependencies=[Depends(require_key)])
async def apps_get(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.get, tenant, ref)


@app.delete("/api/apps/{ref}", dependencies=[Depends(require_key)])
async def apps_delete(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.delete, tenant, ref)


@app.get("/api/apps/{ref}/spec", dependencies=[Depends(require_key)])
async def apps_spec(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.spec, tenant, ref)


@app.get("/api/apps/{ref}/blueprint", dependencies=[Depends(require_key)])
async def apps_blueprint(ref: str, tenant: str = Depends(current_tenant)):
    """v0.131: data tables, org levels, roles matrix, approval chain, login plan, phone features with store status, files."""
    from .appmaker import service as A
    return await asyncio.to_thread(_appd, A.blueprint, tenant, ref)


@app.get("/api/apps/{ref}/blueprint/{name}", dependencies=[Depends(require_key)])
async def apps_blueprint_file(ref: str, name: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    try:
        data, ctype = await asyncio.to_thread(A.blueprint_file, tenant, ref, name)
    except A.AppError:
        raise HTTPException(404, "not found")
    headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
    if name.endswith(".html"):
        headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; frame-ancestors *"
    return Response(content=data, media_type=ctype, headers=headers)


@app.get("/api/apps-catalog/{kind}", dependencies=[Depends(require_key)])
async def apps_catalog(kind: str, q: str = ""):
    """archetypes | capabilities | login | screens | roles (v0.131 complex apps)."""
    def go():
        from .appmaker import auth as AU
        from .appmaker import capabilities as CP
        from .appmaker import datamodel as DM
        from .appmaker import library as AL
        from .appmaker import orgmodel as OM
        from .appmaker import taxonomy as TX
        if kind == "archetypes":
            return {"archetypes": [{"id": k, "label": g["label"], "hi": g["hi"], "brief": g["brief"], "modules": g["modules"],
                                    "roles": [OM.ROLES[r]["label"] for r in g["roles"]], "screens": len(g["screens"]),
                                    "levels": OM.LEVELS[g["levels"]], "money": g["money"], "fields": len(AL.pro_fields(k))}
                                   for k, g in TX.GOALS.items() if g.get("complex")], "counts": AL.counts()}
        if kind == "capabilities":
            ql = q.lower()
            return {"capabilities": [c for c in CP.catalog() if not ql or ql in (c["label"] + " " + c["hi"] + " " + c["id"]).lower()],
                    "legend": {"play": CP.PLAY_LABEL, "ios": CP.IOS_LABEL}, "counts": CP.counts()}
        if kind == "login":
            return {"methods": AU.METHODS, "policy": AU.POLICY}
        if kind == "screens":
            return {"screens": [{"id": k, "label": v["label"], "hi": v["hi"], "why": v["why"], "pro": bool(v.get("pro")),
                                 "designs": len(v["variants"])} for k, v in TX.SCREENS.items()], "code": TX.CODE_SCREENS}
        if kind == "roles":
            return {"roles": OM.ROLES, "templates": OM.BASE, "levels": OM.LEVELS, "scopes": OM.SCOPE_LABEL, "rules": OM.RULES,
                    "modules": DM.MODULES}
        raise HTTPException(404, "unknown catalogue")
    return await asyncio.to_thread(go)


@app.post("/api/apps/{ref}/{action}", dependencies=[Depends(require_key)])
async def apps_act(ref: str, action: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """answers | plan (her Haan) | look (her choice) | change | approve (her 'Design pakka' tap, with the card's hash) | stop | resume."""
    from .appmaker import service as A
    body = body or {}
    conv = str(body.get("conversation_id") or "")
    if action == "answers":
        ans = body.get("answers") if isinstance(body.get("answers"), dict) else {}
        return await asyncio.to_thread(_appd, A.answer, tenant, ref, ans)
    if action == "plan":
        drop = body.get("drop") if isinstance(body.get("drop"), list) else None
        return await asyncio.to_thread(_appd, A.approve_plan, tenant, ref, conv, drop)
    if action == "look":
        cf = body.get("colors_from")
        return await asyncio.to_thread(_appd, A.choose_look, tenant, ref, int(body.get("index") or 0),
                                       int(cf) if cf is not None else None, conv)
    if action == "change":
        return await asyncio.to_thread(_appd, A.change, tenant, ref, str(body.get("instruction") or ""), conv)
    if action == "approve":
        return await asyncio.to_thread(_appd, A.approve, tenant, ref, str(body.get("hash") or ""))
    if action == "stop":
        return await asyncio.to_thread(_appd, A.stop, tenant, ref)
    if action == "resume":
        return await asyncio.to_thread(_appd, A.resume, tenant, ref)
    if action == "android":
        from .appmaker.android import service as AN
        only = [str(x) for x in body.get("redo") or [] if isinstance(x, str)][:60] if isinstance(body.get("redo"), list) else None
        return await asyncio.to_thread(_appd, AN.build, tenant, ref, conv, only)
    if action == "bhasha":                    # v0.347 the languages her app carries (from the next build)
        from .appmaker import i18n as I18
        langs = body.get("langs") if isinstance(body.get("langs"), list) else []
        return await asyncio.to_thread(_appd, I18.set_langs, tenant, ref, [str(x) for x in langs])
    if action == "match":                     # v0.343 design se milao: scores, Opus differences, fix = rebuild those screens
        from .appmaker import match as MT
        return await asyncio.to_thread(_appd, MT.check, tenant, ref, str(body.get("platform") or "android"), bool(body.get("fix")), conv)
    if action == "github":                    # v0.342 her app's code in HER GitHub: the card (her tap on it pushes)
        from .appmaker import code as CODE
        return await asyncio.to_thread(_code, CODE.request, tenant, ref, str(body.get("repo") or ""),
                                       body.get("private", True) is not False, conv)
    if action == "ios":                       # v0.332 IPHONE: kind sim (simulator check) | testflight (her Apple account)
        from .appmaker.ios import service as IO
        only = [str(x) for x in body.get("redo") or [] if isinstance(x, str)][:60] if isinstance(body.get("redo"), list) else None
        return await asyncio.to_thread(_appd, IO.build, tenant, ref, conv, str(body.get("kind") or "sim"), only)
    if action == "rollback":                  # v0.325 an older build again, under a new version
        from .appmaker.android import service as AN
        return await asyncio.to_thread(_appd, AN.rollback, tenant, ref, int(body.get("build") or 0), conv)
    if action == "data_change":               # v0.325 her data change (add / hide / label a field)
        from .appmaker import backend as BE
        from .site import webapp as W

        def go_dc():
            try:
                return BE.change_schema(_be_data(tenant, ref), body.get("ops") if isinstance(body.get("ops"), dict) else {},
                                        str(body.get("words") or ""))
            except W.AppError as e:
                raise HTTPException(e.code, str(e))
        return await asyncio.to_thread(_appd, go_dc)
    if action == "fix_crash":                 # v0.325 her tap on a crash from users' phones (same path as the tool)
        from .agent.app_tools import _act
        from .agent.tools import Ctx, ToolError
        from .site import webapp as W

        def go():
            try:
                return _act(Ctx(tenant_id=tenant, conversation_id=conv), "fix_crash", {"app": ref, "crash": str(body.get("crash") or "")})
            except (ToolError, W.AppError) as e:
                raise HTTPException(400, str(e))
        return await asyncio.to_thread(_appd, go)
    raise HTTPException(404, "unknown action")


@app.get("/api/apps/{ref}/android", dependencies=[Depends(require_key)])
async def apps_android(ref: str, tenant: str = Depends(current_tenant)):
    """v0.132: the native Android build of an approved design (screens in Kotlin, compile rounds, APK / project ZIP)."""
    from .appmaker.android import service as AN
    return await asyncio.to_thread(_appd, AN.get, tenant, ref)


@app.get("/api/apps/{ref}/android/{what}", dependencies=[Depends(require_key)])
async def apps_android_file(ref: str, what: str, tenant: str = Depends(current_tenant)):
    from .appmaker.android import service as AN
    try:
        if what == "zip":
            f, name = await asyncio.to_thread(AN.zip_file, tenant, ref)
            return FileResponse(f, media_type="application/zip", filename=name, headers={"Cache-Control": "private, no-store"})
        if what == "apk":
            f, name = await asyncio.to_thread(AN.apk_file, tenant, ref)
            return FileResponse(f, media_type="application/vnd.android.package-archive", filename=name,
                                headers={"Cache-Control": "private, no-store"})
    except AN.AS.AppError as e:
        raise HTTPException(404, str(e))
    raise HTTPException(404, "not found")


@app.get("/api/apps/{ref}/android/qa/{name}", dependencies=[Depends(require_key)])
async def apps_android_qa(ref: str, name: str, tenant: str = Depends(current_tenant)):
    """v0.325 HOOLA QA: a screen's picture from the device check of the latest build."""
    from .appmaker.android import service as AN
    try:
        f = await asyncio.to_thread(AN.qa_shot, tenant, ref, name)
    except AN.AS.AppError:
        raise HTTPException(404, "not found")
    return FileResponse(f, media_type="image/png", headers={"Cache-Control": "private, max-age=600"})


@app.get("/api/apps/{ref}/ios", dependencies=[Depends(require_key)])
async def apps_ios(ref: str, tenant: str = Depends(current_tenant)):
    """v0.332 IPHONE: the iPhone build of an approved design (SwiftUI screens, Mac compile, simulator check, TestFlight)."""
    from .appmaker.ios import service as IO
    return await asyncio.to_thread(_appd, IO.get, tenant, ref)


@app.get("/api/apps/{ref}/ios/qa/{name}", dependencies=[Depends(require_key)])
async def apps_ios_qa(ref: str, name: str, tenant: str = Depends(current_tenant)):
    """v0.332 a screen's picture from the iPhone simulator check of the latest build."""
    from .appmaker.ios import service as IO
    try:
        f = await asyncio.to_thread(IO.qa_shot, tenant, ref, name)
    except IO.AS.AppError:
        raise HTTPException(404, "not found")
    return FileResponse(f, media_type="image/png", headers={"Cache-Control": "private, max-age=600"})


@app.get("/api/app-ios-zip/{token}/{name}")
async def app_ios_zip(token: str, name: str):
    """Public by its random token (7 days): the Xcode project of her iPhone app (open on a Mac)."""
    from .appmaker.ios import service as IO
    try:
        f = await asyncio.to_thread(IO.zip_by_token, token, name)
    except IO.IosError:
        raise HTTPException(404, "not found")
    return FileResponse(f, media_type="application/zip", filename=name, headers={"Cache-Control": "private, no-store"})


@app.get("/api/app-apk/{token}/{name}")
async def app_apk(token: str, name: str):
    """Public by its random token (7 days): the preview APK her phone's installer downloads (sha256 checked on the phone)."""
    from .appmaker.android import service as AN
    try:
        f = await asyncio.to_thread(AN.apk_by_token, token, name)
    except AN.AndroidError:
        raise HTTPException(404, "not found")
    return FileResponse(f, media_type="application/vnd.android.package-archive", filename=name,
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@app.get("/api/app-zip/{token}/{name}")
async def app_zip(token: str, name: str):
    """Public by its random token (7 days): the Android Studio project of her app (open on a laptop)."""
    from .appmaker.android import service as AN
    try:
        f = await asyncio.to_thread(AN.file_by_token, token, name, "zip")
    except AN.AndroidError:
        raise HTTPException(404, "not found")
    return FileResponse(f, media_type="application/zip", filename=name, headers={"Cache-Control": "private, no-store"})


@app.get("/api/app-content/{app_key}")
async def app_content(app_key: str):
    """Public, read only: what an installed Hoola-made app shows (her public facts + public products; samples marked)."""
    from .appmaker.android import service as AN
    try:
        data = await asyncio.to_thread(AN.content, app_key)
    except AN.AndroidError:
        raise HTTPException(404, "not found")
    return JSONResponse(data, headers={"Cache-Control": "public, max-age=60"})


# ---- v0.314 ASLI APP: each native app's own backend. The installed app talks to /api/app-api/<app_key>/... (accounts,
# lists, rules checked on every call); she runs the same data from her Hoola (/api/apps/<ref>/data ...).
def _be_call(fn):
    from .site import webapp as W
    try:
        return JSONResponse(fn(), headers={"Cache-Control": "no-store"})
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code)


def _be_app(app_key: str, request: Request | None = None):
    from .appmaker import backend as BE
    r = BE.by_key(app_key)
    tok = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip() if request is not None else ""
    return r, BE.who(r, tok)


@app.get("/api/app-api/{app_key}/schema")
async def app_api_schema(app_key: str):
    from .appmaker import backend as BE
    return await asyncio.to_thread(_be_call, lambda: BE.public_schema(BE.by_key(app_key)))


def _ua_of(request: Request) -> str:
    return (request.headers.get("user-agent") or "")[:160]


@app.post("/api/app-api/{app_key}/signup")
async def app_api_signup(app_key: str, request: Request):
    """v0.455 the sign-up records the DPDP consent tick and this login as a session she can end."""
    from .appmaker import backend as BE
    from .appmaker import sign as SG
    body, ip, ua = await _json_body(request), _ip(request), _ua_of(request)
    return await asyncio.to_thread(_be_call, lambda: SG.password_signup(BE.by_key(app_key), body, ua, ip))


@app.post("/api/app-api/{app_key}/login")
async def app_api_login(app_key: str, request: Request):
    """v0.455 a staff account with 2FA on gets {need_2fa, ticket} here and finishes at /login/2fa."""
    from .appmaker import backend as BE
    from .appmaker import sign as SG
    body, ip, ua = await _json_body(request), _ip(request), _ua_of(request)
    return await asyncio.to_thread(_be_call, lambda: SG.password_login(BE.by_key(app_key), body, ua, ip))


# ---- v0.455 SURAKSHIT LOGIN (App Sahayak Pillar I): phone OTP, Google / Apple checked on the SERVER, sessions she can
# end, staff 2FA, her own data (DPDP). The engine is the website's (site/security.py) on the same backend id.
@app.post("/api/app-api/{app_key}/login/otp")
async def app_api_login_otp(app_key: str, request: Request):
    from .appmaker import backend as BE
    from .appmaker import sign as SG
    body, ip = await _json_body(request), _ip(request)
    return await asyncio.to_thread(_be_call, lambda: SG.otp_start(BE.by_key(app_key), str(body.get("phone") or ""), ip))


@app.post("/api/app-api/{app_key}/login/otp/check")
async def app_api_login_otp_check(app_key: str, request: Request):
    from .appmaker import backend as BE
    from .appmaker import sign as SG
    body, ip, ua = await _json_body(request), _ip(request), _ua_of(request)
    return await asyncio.to_thread(_be_call, lambda: SG.otp_verify(BE.by_key(app_key), body, ua, ip))


@app.get("/api/app-api/{app_key}/login/nonce")
async def app_api_login_nonce(app_key: str):
    """One single-use nonce per Google / Apple attempt (the app passes it to the provider, the server checks it back)."""
    from .appmaker import backend as BE
    from .appmaker import sign as SG
    return await asyncio.to_thread(_be_call, lambda: SG.nonce(BE.by_key(app_key)))


@app.post("/api/app-api/{app_key}/login/{provider}")
async def app_api_login_social(app_key: str, provider: str, request: Request):
    """Google / Apple: the app sends the provider's ID token; this server checks its signature, audience and nonce."""
    from .appmaker import backend as BE
    from .appmaker import sign as SG
    body, ip, ua = await _json_body(request), _ip(request), _ua_of(request)
    if provider == "2fa":
        return await asyncio.to_thread(_be_call, lambda: SG.two_fa_login(BE.by_key(app_key), str(body.get("ticket") or ""),
                                                                         str(body.get("code") or ""), ua, ip))
    if provider not in ("google", "apple"):
        return JSONResponse({"ok": False, "error": "login: google / apple / 2fa"}, status_code=404)
    return await asyncio.to_thread(_be_call, lambda: SG.social_login(BE.by_key(app_key), provider, body, ua, ip))


@app.get("/api/app-api/{app_key}/security")
async def app_api_security(app_key: str, request: Request):
    """The member's own security page in the app: her logins, 2FA, what consent she gave."""
    from .appmaker import sign as SG

    def go():
        r, w = _be_app(app_key, request)
        tok = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        return SG.my_security(r, w, tok)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/security/{what}")
async def app_api_security_do(app_key: str, what: str, request: Request):
    from .appmaker import sign as SG
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        if what == "end":
            return SG.end_session(r, w, str(body.get("id") or ""))
        if what == "end-all":
            return SG.end_everywhere(r, w)
        if what == "2fa-start":
            return SG.two_fa_start(r, w)
        if what == "2fa-on":
            return SG.two_fa_confirm(r, w, str(body.get("code") or ""))
        if what == "2fa-off":
            return SG.two_fa_off(r, w, str(body.get("code") or ""))
        raise SG.SignError("security: end / end-all / 2fa-start / 2fa-on / 2fa-off", 404)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/my-data")
async def app_api_my_data(app_key: str, request: Request):
    """DPDP: this account downloads everything of its own, from inside the app."""
    from .appmaker import sign as SG

    def go():
        r, w = _be_app(app_key, request)
        return SG.my_data(r, w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/me")
async def app_api_me(app_key: str, request: Request):
    from .site import webapp as W

    def go():
        r, w = _be_app(app_key, request)
        from .appmaker import rollout as RO               # v0.540 this phone's feature switches, decided HERE
        return {"me": W.view_member(w.m) if w.m else None,
                "flags": RO.for_member(r, w.m.id if w.m else "")}
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/logout")
async def app_api_logout(app_key: str, request: Request):
    from .appmaker import backend as BE
    from .site import webapp as W

    def go():
        r, w = _be_app(app_key, request)
        if w.m:
            W.logout_all(BE.bid(r), w.m)
        return {"ok": True}
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/delete-me")
async def app_api_delete_me(app_key: str, request: Request):
    """In-app account deletion (Play + App Store rule): the account and every row it made are removed."""
    from .appmaker import backend as BE

    def go():
        r, w = _be_app(app_key, request)
        return BE.delete_me(r, w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/c/{coll}")
async def app_api_rows(app_key: str, coll: str, request: Request, q: str = "", status: str = "", limit: int = 200,
                       offset: int = 0, mine: int = 0):
    """v0.319 + q (search any field), status filter, limit / offset paging; v0.352 mine=1 = only the rows given to me."""
    from .appmaker import backend as BE

    def go():
        r, w = _be_app(app_key, request)
        return {"rows": BE.rows(r, coll, w, limit, q, status, offset, bool(mine))}
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/team")
async def app_api_team(app_key: str, request: Request):
    """v0.352 KAAM BAANTO: the staff names for the assign buttons (staff only, no e-mails) + each one's open work."""
    from .appmaker import backend as BE

    def go():
        r, w = _be_app(app_key, request)
        return BE.team(r, w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/c/{coll}/{row_id}/rate")
async def app_api_rate(app_key: str, coll: str, row_id: str, request: Request):
    """v0.353 RAAY: the customer rates her own finished row once {"stars": 1-5, "note": "..."}."""
    from .appmaker import backend as BE
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return BE.rate(r, coll, row_id, body.get("stars"), str(body.get("note") or ""), w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/push-token")
async def app_api_push_token(app_key: str, request: Request):
    """v0.367 TURANT: this phone's Firebase push token for the signed-in account (instant notifications)."""
    from .appmaker import turant as TU
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return TU.register(r, w, str(body.get("token") or ""), str(body.get("platform") or "android"))
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/chat")
async def app_api_chat(app_key: str, request: Request, all: int = 0):
    """v0.378 BAAT: her own thread with the shop; all=1 (staff) = every customer thread with unread counts."""
    from .appmaker import baat as BT

    def go():
        r, w = _be_app(app_key, request)
        return BT.threads(r, w) if all else BT.mine(r, w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/chat")
async def app_api_chat_write(app_key: str, request: Request):
    """v0.378 a customer's message to the shop {text, order?}."""
    from .appmaker import baat as BT
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return BT.write(r, w, str(body.get("text") or ""), str(body.get("order") or ""))
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/chat/{member}")
async def app_api_chat_thread(app_key: str, member: str, request: Request):
    """v0.378 staff: one customer's thread (marks her messages read)."""
    from .appmaker import baat as BT

    def go():
        r, w = _be_app(app_key, request)
        return BT.thread(r, w, member)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/chat/{member}")
async def app_api_chat_reply(app_key: str, member: str, request: Request):
    """v0.378 staff reply {text}."""
    from .appmaker import baat as BT
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return BT.reply(r, w, member, str(body.get("text") or ""))
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/khata")
async def app_api_khata(app_key: str, request: Request, all: int = 0):
    """v0.359 KHATA: her own udhaar balance + entries; all=1 (staff) = every customer who owes."""
    from .appmaker import khata as KH

    def go():
        r, w = _be_app(app_key, request)
        return KH.dues(r, w) if all else KH.mine(r, w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/khata/{member}")
async def app_api_khata_one(app_key: str, member: str, request: Request):
    """v0.359 staff: one customer's khata."""
    from .appmaker import khata as KH
    from .site import webapp as W

    def go():
        r, w = _be_app(app_key, request)
        if not w.staff:
            raise W.AppError("Yeh sirf staff ke liye hai.", 403)
        return KH.summary(r, member)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/khata/{member}/pay")
async def app_api_khata_pay(app_key: str, member: str, request: Request):
    """v0.359 staff: the customer paid {amount, mode cash|upi|card|bank|other, note} (recorded only)."""
    from .appmaker import khata as KH
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return KH.payment(r, member, body.get("amount"), str(body.get("mode") or "cash"), str(body.get("note") or ""), w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/c/{coll}/{row_id}/slot")
async def app_api_change_slot(app_key: str, coll: str, row_id: str, request: Request):
    """v0.377 CHHUTTI: move an order to another free slot {slot} (her customer before the cut-off, staff any time)."""
    from .appmaker import delivery as DL
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return DL.change_slot(r, coll, row_id, str(body.get("slot") or ""), w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/slots")
async def app_api_slots(app_key: str, request: Request):
    """v0.371 SLOT: the delivery slots with room (today + the days ahead), for the cart."""
    from .appmaker import delivery as DL

    def go():
        r, _w = _be_app(app_key, request)
        return DL.available(r)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/coupon")
async def app_api_coupon(app_key: str, request: Request):
    """v0.358 COUPON: the cart's check {code, cart} -> {ok, discount, total, why} (nothing counted; the order applies it again)."""
    from .appmaker import backend as BE
    from .appmaker import coupon as CP
    from .site import webapp as W
    body, ip = await _json_body(request), _ip(request)

    def go():
        r, w = _be_app(app_key, request)
        W.rate(f"cp|{BE.bid(r)}|{w.id or ip}", 30, 600)
        return CP.check(r, str(body.get("code") or ""), body.get("cart"), w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/c/{coll}/{row_id}/receipt-link")
async def app_api_receipt_link(app_key: str, coll: str, row_id: str, request: Request):
    """v0.354 RASEED: a 15-minute signed address of the receipt PDF (the app opens it in the phone's browser)."""
    from .appmaker import receipt as RC

    def go():
        r, w = _be_app(app_key, request)
        return RC.link(r, coll, row_id, w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/receipt/{coll}/{row_id}")
async def app_api_receipt(app_key: str, coll: str, row_id: str, e: str = "", s: str = ""):
    """v0.354 the receipt PDF behind a signed link (no login in the browser; the signature is bound to app + list + row)."""
    from .appmaker import backend as BE
    from .appmaker import receipt as RC
    from .site import webapp as W

    def go():
        r = BE.by_key(app_key)
        data = RC.by_link(r, coll, row_id, e, s)
        return data, RC.filename(r, RC._load(r, coll, row_id)[1])
    try:
        data, name = await asyncio.to_thread(go)
    except W.AppError as er:
        return JSONResponse({"ok": False, "error": str(er)}, status_code=er.code)
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="{name}"', "Cache-Control": "private, no-store",
        "Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"})


@app.post("/api/app-api/{app_key}/c/{coll}/{row_id}/assign")
async def app_api_assign(app_key: str, coll: str, row_id: str, request: Request):
    """v0.352 give a row to a staff member {"to": member id}, take it {"to": "me"}, give it back {"to": ""}."""
    from .appmaker import backend as BE
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return BE.assign(r, coll, row_id, str(body.get("to") or ""), w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/files")
async def app_api_upload(app_key: str, request: Request):
    """v0.319 a photo from the app (raw image body, 6 MB at most): stored re-encoded (no EXIF / GPS), answers its id."""
    from .appmaker import backend as BE
    raw = await request.body()
    ip = _ip(request)
    ctype = request.headers.get("content-type") or ""

    def go():
        r, w = _be_app(app_key, request)
        return BE.upload(r, w, raw, ip, ctype)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/files/{fid}/link")
async def app_api_file_link(app_key: str, fid: str, request: Request):
    """v0.425 RANG: a 15-minute signed address for the phone's own video / audio / PDF player (no token in it)."""
    from .appmaker import backend as BE
    def go():
        r, w = _be_app(app_key, request)
        return BE.media_link(r, fid, w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/media/{tok}")
async def app_api_media(app_key: str, tok: str):
    from .appmaker import backend as BE
    from .site import webapp as W
    try:
        f = await asyncio.to_thread(lambda: BE.media_file(BE.by_key(app_key), tok))
    except W.AppError:
        raise HTTPException(404, "not found")
    return FileResponse(f, media_type=BE.MEDIA_MIME.get(f.suffix, "application/octet-stream"),
                        headers={"Cache-Control": "private, max-age=900", "X-Content-Type-Options": "nosniff",
                                 "Content-Security-Policy": "sandbox", "Referrer-Policy": "no-referrer"})


@app.get("/api/app-api/{app_key}/files/{fid}")
async def app_api_file(app_key: str, fid: str, request: Request):
    from .appmaker import backend as BE
    from .site import webapp as W
    try:
        r, w = await asyncio.to_thread(_be_app, app_key, request)
        f = await asyncio.to_thread(BE.file_for, r, fid, w)
    except W.AppError:
        raise HTTPException(404, "not found")
    if f.suffix in (".mp4", ".mov", ".m4a"):     # v0.425 RANG: video / voice note for the phone's own player (range requests)
        return FileResponse(f, media_type=BE.MEDIA_MIME[f.suffix], headers={"Cache-Control": "private, max-age=3600",
                                                                            "X-Content-Type-Options": "nosniff",
                                                                            "Content-Security-Policy": "sandbox"})
    if str(f).endswith(".pdf"):                  # v0.346 a PDF is only ever a download, never opened in a page
        return FileResponse(f, media_type="application/pdf", filename=f"{fid}.pdf",
                            headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff",
                                     "Content-Security-Policy": "sandbox", "Content-Disposition": f'attachment; filename="{fid}.pdf"'})
    return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400",
                                                             "X-Content-Type-Options": "nosniff"})


@app.post("/api/app-api/{app_key}/crash")
async def app_api_crash(app_key: str, request: Request):
    """v0.325 HOOLA QA: a crash an installed app kept from its last run (no login; nothing personal in it)."""
    from .appmaker import backend as BE
    body, ip = await _json_body(request), _ip(request)
    return await asyncio.to_thread(_be_call, lambda: BE.crash(BE.by_key(app_key), body, ip))


@app.get("/api/app-api/{app_key}/latest")
async def app_api_latest(app_key: str):
    """v0.325 the installed app's update check: the newest build's version, What's new, the APK address."""
    from .appmaker import backend as BE
    from .appmaker.android import service as AN
    return await asyncio.to_thread(_be_call, lambda: AN.latest(BE.by_key(app_key)))


@app.get("/api/app-api/{app_key}/apk")
async def app_api_apk(app_key: str):
    """v0.325 the newest APK of this app (public like the app itself: whoever has the app may update it)."""
    from .appmaker import backend as BE
    from .appmaker.android import service as AN
    from .site import webapp as W
    try:
        f, name = await asyncio.to_thread(lambda: AN.apk_current(BE.by_key(app_key)))
    except (W.AppError, AN.AndroidError):
        raise HTTPException(404, "not found")
    return FileResponse(f, media_type="application/vnd.android.package-archive", filename=name,
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.get("/api/app-api/{app_key}/privacy", response_class=HTMLResponse)
async def app_api_privacy(app_key: str):
    """v0.330 the app's privacy policy page (the URL Play Console asks for)."""
    from .appmaker import backend as BE
    from .appmaker.android import store as ST
    from .site import webapp as W
    try:
        return HTMLResponse(await asyncio.to_thread(lambda: ST.privacy_html(BE.by_key(app_key))))
    except W.AppError:
        raise HTTPException(404, "not found")


@app.get("/api/app-api/{app_key}/delete-account", response_class=HTMLResponse)
async def app_api_delete_page(app_key: str):
    """v0.330 how to delete the account (Play's required data-deletion URL)."""
    from .appmaker import backend as BE
    from .appmaker.android import store as ST
    from .site import webapp as W
    try:
        return HTMLResponse(await asyncio.to_thread(lambda: ST.delete_html(BE.by_key(app_key))))
    except W.AppError:
        raise HTTPException(404, "not found")


@app.get("/api/app-api/{app_key}/support", response_class=HTMLResponse)
async def app_api_support(app_key: str):
    """v0.338 the app's support page (the Support URL App Store Connect requires)."""
    from .appmaker import backend as BE
    from .appmaker.ios import appstore as AP
    from .site import webapp as W
    try:
        return HTMLResponse(await asyncio.to_thread(lambda: AP.support_html(BE.by_key(app_key))))
    except W.AppError:
        raise HTTPException(404, "not found")


@app.get("/api/app-api/{app_key}/updates")
async def app_api_updates(app_key: str, request: Request, since: str = ""):
    """v0.319 the app's background check: her rows that moved (customer) / new orders (staff) since `since`."""
    from .appmaker import backend as BE

    def go():
        r, w = _be_app(app_key, request)
        return BE.updates(r, w, since)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/stats")
async def app_api_stats(app_key: str, request: Request, days: int = 14):
    """v0.340 the staff dashboard of an installed app: counts, status mix, rows per day, money total (staff only)."""
    from .appmaker import backend as BE

    def go():
        r, w = _be_app(app_key, request)
        return BE.stats(r, w, days)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/c/{coll}/{row_id}/paid")
async def app_api_paid(app_key: str, coll: str, row_id: str, request: Request):
    """v0.319 the customer says she paid by UPI (+ the UPI reference): the owner checks her own bank, Hoola never sees money."""
    from .appmaker import backend as BE
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return BE.mark_paid(r, coll, row_id, str(body.get("utr") or ""), w)
    return await asyncio.to_thread(_be_call, go)


# ---- v0.382 DIMAAG (App Phases 43-46): the app's logic engine - approvals inbox, a row's linked children, callable functions
@app.get("/api/app-api/{app_key}/approvals")
async def app_api_approvals(app_key: str, request: Request, all: int = 0):
    """Approvals this person can decide (+ the ones they asked for); staff with all=1 see the history too."""
    from .appmaker.logic import engine as LE

    def go():
        r, w = _be_app(app_key, request)
        if w.m is None:
            from .site import webapp as W
            raise W.AppError("Pehle login kijiye.", 401)
        return {"approvals": LE.approvals(r, w, bool(all))}
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/approvals/{appr_id}")
async def app_api_decide(app_key: str, appr_id: str, request: Request):
    """{decision: approve|reject, note}: one step of the chain; the maker can never approve their own ask."""
    from .appmaker.logic import engine as LE
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        if w.m is None:
            from .site import webapp as W
            raise W.AppError("Pehle login kijiye.", 401)
        return LE.decide(r, appr_id, str(body.get("decision") or ""), str(body.get("note") or ""), w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/c/{coll}/{row_id}/related/{rel}")
async def app_api_related(app_key: str, coll: str, row_id: str, rel: str, request: Request):
    """A row's linked children (an order's lines, a class's students) that this person may read."""
    from .appmaker.logic import engine as LE

    def go():
        r, w = _be_app(app_key, request)
        return LE.related(r, coll, row_id, rel, w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/fn/{name}")
async def app_api_fn(app_key: str, name: str, request: Request):
    """A custom function she marked callable (price / EMI calculator): runs in the locked interpreter, reads no data."""
    from .appmaker.logic import engine as LE
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        args = body.get("args") if isinstance(body.get("args"), list) else []
        return LE.call_public(r, name, args, w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/c/{coll}")
async def app_api_create(app_key: str, coll: str, request: Request):
    from .appmaker import backend as BE
    body, ip = await _json_body(request), _ip(request)

    def go():
        r, w = _be_app(app_key, request)
        return BE.create(r, coll, body, w, ip)
    return await asyncio.to_thread(_be_call, go)


@app.patch("/api/app-api/{app_key}/c/{coll}/{row_id}")
async def app_api_update(app_key: str, coll: str, row_id: str, request: Request):
    from .appmaker import backend as BE
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return BE.update(r, coll, row_id, body, w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/c/{coll}/{row_id}")
async def app_api_update_post(app_key: str, coll: str, row_id: str, request: Request):
    """The same change as PATCH: Android's HttpURLConnection has no PATCH, the app's outbox posts updates here."""
    return await app_api_update(app_key, coll, row_id, request)


@app.delete("/api/app-api/{app_key}/c/{coll}/{row_id}")
async def app_api_delete(app_key: str, coll: str, row_id: str, request: Request):
    from .appmaker import backend as BE

    def go():
        r, w = _be_app(app_key, request)
        return BE.delete(r, coll, row_id, w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/members")
async def app_api_members(app_key: str, request: Request):
    """Staff screen inside the app: the app's accounts (staff / admin accounts only)."""
    from .appmaker import backend as BE
    from .site import webapp as W

    def go():
        r, w = _be_app(app_key, request)
        if not w.staff:
            raise W.AppError("Iski ijaazat nahi.", 403)
        return {"members": BE.members(r), "admin": bool(w.m and w.m.role == "admin")}
    return await asyncio.to_thread(_be_call, go)


# ---- v0.407 ABHI ABHI (App Sahayak Pillar C): real time for the native apps - one SSE stream per open app.
def _live_stream(r, w, token: str, request: Request, colls: str):
    from .appmaker import live as LV
    last = request.headers.get("last-event-id") or request.query_params.get("last") or ""
    return StreamingResponse(LV.stream(r, w, token, colls, last, gone=request.is_disconnected), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/app-api/{app_key}/live")
async def app_api_live(app_key: str, request: Request, colls: str = ""):
    """Live lists / order status / chat / presence / typing for a signed-in account (Bearer token in the header). Events are
    filtered by each list's read rule; Last-Event-ID replays what a reconnect missed. 429 = too many streams (the app keeps
    its normal refresh)."""
    from .appmaker import live as LV
    from .site import webapp as W

    def go():
        r, w = _be_app(app_key, request)
        LV.admit(r, w)
        return r, w
    try:
        r, w = await asyncio.to_thread(go)
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code)
    tok = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
    return _live_stream(r, w, tok, request, colls)


@app.post("/api/app-api/{app_key}/live/typing")
async def app_api_live_typing(app_key: str, request: Request):
    """{thread?}: 'typing...' in a chat thread (a customer: her own; staff: the customer's member id)."""
    from .appmaker import live as LV
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return LV.typing(r, w, str(body.get("thread") or ""))
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/live/presence")
async def app_api_live_presence(app_key: str, request: Request):
    """Who is online now (a customer sees whether the shop's staff are online; staff see everyone)."""
    from .appmaker import live as LV

    def go():
        r, w = _be_app(app_key, request)
        return LV.online(r, w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/apps/{ref}/live", dependencies=[Depends(require_key)])
async def apps_live(ref: str, request: Request, colls: str = "", tenant: str = Depends(current_tenant)):
    """Her own live view of one app (console / phone): every list, every chat, who is online."""
    from .appmaker import live as LV
    from .site import webapp as W
    try:
        r = await asyncio.to_thread(_be_owner, tenant, ref)
        w = W.Who(owner=True)
        LV.admit(r, w)
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code)
    except Exception:
        return JSONResponse({"ok": False, "error": "App nahi mila."}, status_code=404)
    return _live_stream(r, w, "", request, colls)


@app.get("/api/apps/{ref}/live/presence", dependencies=[Depends(require_key)])
async def apps_live_presence(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import live as LV
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: LV.online(_be_data(tenant, ref), W.Who(owner=True)))


@app.post("/api/apps/{ref}/live/typing", dependencies=[Depends(require_key)])
async def apps_live_typing(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her 'typing...' in a customer's chat thread {thread}."""
    from .appmaker import live as LV
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: LV.typing(_be_data(tenant, ref), W.Who(owner=True),
                                                                     str((body or {}).get("thread") or "")))


# ---- v0.412 NAKSHA LIVE (App Sahayak Pillar D): rider shifts, positions, live tracking of one order, riders on a map.
@app.get("/api/app-api/{app_key}/track/me")
async def app_api_track_me(app_key: str, request: Request):
    from .appmaker import track as TR
    return await asyncio.to_thread(_be_call, lambda: TR.mine(*_be_app(app_key, request)))


@app.post("/api/app-api/{app_key}/track/shift")
async def app_api_track_shift(app_key: str, request: Request):
    """{on}: a staff account starts / ends its shift (positions are accepted only while it is on)."""
    from .appmaker import track as TR
    body = await _json_body(request)
    return await asyncio.to_thread(_be_call, lambda: TR.shift(*_be_app(app_key, request), bool(body.get("on"))))


@app.post("/api/app-api/{app_key}/track/pos")
async def app_api_track_pos(app_key: str, request: Request):
    """{lat, lng, acc?, speed?, heading?} from the rider's phone while the shift is on."""
    from .appmaker import track as TR
    body = await _json_body(request)
    return await asyncio.to_thread(_be_call, lambda: TR.position(*_be_app(app_key, request), body))


@app.get("/api/app-api/{app_key}/track/c/{coll}/{row_id}")
async def app_api_track_order(app_key: str, coll: str, row_id: str, request: Request):
    """The customer's own order (or staff): rider position, distance, ETA (an estimate), near / arrived."""
    from .appmaker import track as TR
    return await asyncio.to_thread(_be_call, lambda: TR.order(*_be_app(app_key, request), coll, row_id))


@app.get("/api/app-api/{app_key}/track/riders")
async def app_api_track_riders(app_key: str, request: Request):
    from .appmaker import track as TR
    return await asyncio.to_thread(_be_call, lambda: TR.riders(*_be_app(app_key, request)))


@app.get("/api/apps/{ref}/track", dependencies=[Depends(require_key)])
async def apps_track(ref: str, tenant: str = Depends(current_tenant)):
    """Her tracking switch + every rider on shift."""
    from .appmaker import track as TR
    from .site import webapp as W

    def go():
        r = _be_data(tenant, ref)
        return {**TR.settings(r), **TR.riders(r, W.Who(owner=True))}
    return await asyncio.to_thread(_be_owner_call, go)


@app.put("/api/apps/{ref}/track", dependencies=[Depends(require_key)])
async def apps_track_save(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap: {on, coll, statuses} - which list is tracked and which statuses mean 'on the way'."""
    from .appmaker import track as TR
    return await asyncio.to_thread(_be_owner_call, lambda: TR.save_settings(_be_data(tenant, ref), body or {}))


@app.get("/api/apps/{ref}/track/c/{coll}/{row_id}", dependencies=[Depends(require_key)])
async def apps_track_order(ref: str, coll: str, row_id: str, tenant: str = Depends(current_tenant)):
    from .appmaker import track as TR
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: TR.order(_be_data(tenant, ref), W.Who(owner=True), coll, row_id))


def html_escape(s: str) -> str:
    import html as _h
    return _h.escape(s)


# ---- v0.419 PAISA (App Sahayak Pillar E): online payments through HER gateway. Paid only from the gateway's word.
@app.get("/api/app-api/{app_key}/pay/c/{coll}/{row_id}")
async def app_api_pay_row(app_key: str, coll: str, row_id: str, request: Request):
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_call, lambda: PY.row_info(*_be_app(app_key, request), coll, row_id))


@app.post("/api/app-api/{app_key}/pay/c/{coll}/{row_id}/start")
async def app_api_pay_start(app_key: str, coll: str, row_id: str, request: Request):
    """The customer's own unpaid order -> her gateway order for the SERVER's total -> {path} of the pay page."""
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_call, lambda: PY.start(*_be_app(app_key, request), coll, row_id))


@app.get("/api/app-api/{app_key}/pay/p/{tok}", response_class=HTMLResponse)
async def app_api_pay_page(app_key: str, tok: str):
    """The pay page (signed link, 30 min): the gateway's own checkout. Shows nothing secret."""
    from .appmaker import backend as BE
    from .appmaker import pay as PY
    from .site import webapp as W
    try:
        body = await asyncio.to_thread(lambda: PY.page(BE.by_key(app_key), tok))
    except W.AppError as e:
        return HTMLResponse(f"<!doctype html><meta charset=utf-8><p style='font:16px system-ui;padding:24px'>{html_escape(str(e))}</p>",
                            status_code=e.code, headers={"Content-Security-Policy": "default-src 'none'"})
    return HTMLResponse(body, headers={"Content-Security-Policy": PY.PAGE_CSP, "Cache-Control": "no-store",
                                       "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"})


@app.get("/api/app-api/{app_key}/pay/s/{tok}")
async def app_api_pay_state(app_key: str, tok: str):
    from .appmaker import backend as BE
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_call, lambda: PY.page_state(BE.by_key(app_key), tok))


@app.post("/api/app-api/{app_key}/pay/webhook")
async def app_api_pay_webhook(app_key: str, request: Request):
    """Her gateway calls this. Nothing happens unless the signature verifies with HER secret."""
    from .appmaker import backend as BE
    from .appmaker import pay as PY
    raw = await request.body()
    if len(raw) > 512_000:
        return JSONResponse({"ok": False}, status_code=413)
    hdrs = dict(request.headers)
    return await asyncio.to_thread(_be_call, lambda: PY.webhook(BE.by_key(app_key), hdrs, raw))


@app.get("/api/app-api/{app_key}/pay/plans")
async def app_api_pay_plans(app_key: str):
    from .appmaker import backend as BE
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_call, lambda: PY.plans(BE.by_key(app_key)))


@app.post("/api/app-api/{app_key}/pay/plans/{key}/subscribe")
async def app_api_pay_subscribe(app_key: str, key: str, request: Request):
    """The customer starts AutoPay on a plan; she authorises the mandate on the gateway's own page."""
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_call, lambda: PY.subscribe(*_be_app(app_key, request), key))


@app.get("/api/app-api/{app_key}/pay/subs")
async def app_api_pay_subs(app_key: str, request: Request):
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_call, lambda: PY.my_subs(*_be_app(app_key, request)))


@app.post("/api/app-api/{app_key}/pay/subs/{sid}/cancel")
async def app_api_pay_sub_cancel(app_key: str, sid: str, request: Request):
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_call, lambda: PY.cancel_sub(*_be_app(app_key, request), sid))


@app.get("/api/apps/{ref}/pay", dependencies=[Depends(require_key)])
async def apps_pay(ref: str, tenant: str = Depends(current_tenant)):
    """Her payments page: gateway (never the keys), webhook address, payments + refunds, plans, AutoPay, split rule."""
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_owner_call, lambda: PY.status(_be_data(tenant, ref)))


@app.put("/api/apps/{ref}/pay/keys", dependencies=[Depends(require_key)])
async def apps_pay_keys(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{gateway, keys: {...}, test}: typed in the app, checked with the gateway, sealed; returned by no route."""
    from .appmaker import pay as PY
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: PY.set_keys(_be_data(tenant, ref), str(b.get("gateway") or ""),
                                                                       b.get("keys") if isinstance(b.get("keys"), dict) else {},
                                                                       bool(b.get("test"))))


@app.delete("/api/apps/{ref}/pay/keys", dependencies=[Depends(require_key)])
async def apps_pay_keys_forget(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_owner_call, lambda: PY.forget_keys(_be_data(tenant, ref)))


@app.post("/api/apps/{ref}/pay/{pid}/refund", dependencies=[Depends(require_key)])
async def apps_pay_refund(ref: str, pid: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap only {amount? (rupees, blank = the rest), why, her_tap: true}."""
    from .appmaker import pay as PY
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: PY.refund(_be_data(tenant, ref), pid, b.get("amount"),
                                                                     str(b.get("why") or ""), bool(b.get("her_tap"))))


@app.post("/api/apps/{ref}/pay/refunds/{fid}/check", dependencies=[Depends(require_key)])
async def apps_pay_refund_check(ref: str, fid: str, tenant: str = Depends(current_tenant)):
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_owner_call, lambda: PY.refund_check(_be_data(tenant, ref), fid))


@app.get("/api/apps/{ref}/pay/settlements", dependencies=[Depends(require_key)])
async def apps_pay_settlements(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_owner_call, lambda: PY.settlements(_be_data(tenant, ref)))


@app.post("/api/apps/{ref}/pay/link", dependencies=[Depends(require_key)])
async def apps_pay_link(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{amount, purpose, name?, phone?, her_tap: true} -> a payment link she sends herself."""
    from .appmaker import pay as PY
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: PY.link(_be_data(tenant, ref), b.get("amount"), str(b.get("purpose") or ""),
                                                                   str(b.get("name") or ""), str(b.get("phone") or ""), bool(b.get("her_tap"))))


@app.post("/api/apps/{ref}/pay/plans", dependencies=[Depends(require_key)])
async def apps_pay_plan_add(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{name, amount, period: week|month|year, count, her_tap: true}"""
    from .appmaker import pay as PY
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: PY.add_plan(_be_data(tenant, ref), str(b.get("name") or ""), b.get("amount"),
                                                                       str(b.get("period") or ""), b.get("count"), bool(b.get("her_tap"))))


@app.delete("/api/apps/{ref}/pay/plans/{key}", dependencies=[Depends(require_key)])
async def apps_pay_plan_drop(ref: str, key: str, tenant: str = Depends(current_tenant)):
    from .appmaker import pay as PY
    return await asyncio.to_thread(_be_owner_call, lambda: PY.drop_plan(_be_data(tenant, ref), key))


@app.post("/api/apps/{ref}/pay/subs/{sid}/cancel", dependencies=[Depends(require_key)])
async def apps_pay_sub_cancel(ref: str, sid: str, tenant: str = Depends(current_tenant)):
    from .appmaker import pay as PY
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: PY.cancel_sub(_be_data(tenant, ref), W.Who(owner=True), sid))


@app.put("/api/apps/{ref}/pay/split", dependencies=[Depends(require_key)])
async def apps_pay_split(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{vendors: [{key, name, account}], rules: [{vendor, percent}], her_tap: true} - her approved payout rule."""
    from .appmaker import pay as PY
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: PY.set_split(_be_data(tenant, ref), b.get("vendors") or [], b.get("rules") or [],
                                                                        bool(b.get("her_tap"))))


# ---- v0.424 JODO (App Sahayak Pillar F): declared connectors (couriers, SMS, WhatsApp, e-mail, Google, accounts, KYC).
@app.post("/api/app-api/{app_key}/connect/{key}/run")
async def app_api_connect_run(app_key: str, key: str, request: Request):
    """A staff button in the app {row}: only an approved action she allowed staff to run."""
    from .appmaker import connect as CN
    body = await _json_body(request)
    return await asyncio.to_thread(_be_call, lambda: CN.staff_run(*_be_app(app_key, request), key, str(body.get("row") or "")))


@app.post("/api/app-api/{app_key}/hook/{key}")
async def app_api_connect_hook(app_key: str, key: str, request: Request):
    """Her outside service calls the app. Nothing happens unless the signature verifies with the hook's secret."""
    from .appmaker import backend as BE
    from .appmaker import connect as CN
    raw = await request.body()
    if len(raw) > 256_000:
        return JSONResponse({"ok": False}, status_code=413)
    hdrs = dict(request.headers)
    return await asyncio.to_thread(_be_call, lambda: CN.hook(BE.by_key(app_key), key, hdrs, raw))


# ---- v0.435 PARIVAAR (App Sahayak Pillar H): one backend, several apps (customer / delivery partner / partner shop /
# staff) + the web admin. The partner app's jobs screen and the web admin talk to these; every rule is checked in
# appmaker/family.py on the server, never by the app.
@app.get("/api/app-api/{app_key}/partner/me")
async def app_api_partner_me(app_key: str, request: Request):
    from .appmaker import family as FA

    def go():
        r, w = _be_app(app_key, request)
        return FA.me(r, w, FA.kind_for_key(app_key))
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/partner/request")
async def app_api_partner_request(app_key: str, request: Request):
    from .appmaker import family as FA

    def go():
        r, w = _be_app(app_key, request)
        return FA.request(r, w, FA.kind_for_key(app_key))
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/partner/jobs")
async def app_api_partner_jobs(app_key: str, request: Request):
    from .appmaker import family as FA

    def go():
        r, w = _be_app(app_key, request)
        return FA.jobs(r, w, app_key)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/partner/jobs/{row_id}/take")
async def app_api_partner_take(app_key: str, row_id: str, request: Request):
    from .appmaker import family as FA

    def go():
        r, w = _be_app(app_key, request)
        return FA.take(r, w, row_id)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/partner/jobs/{row_id}/step")
async def app_api_partner_step(app_key: str, row_id: str, request: Request):
    from .appmaker import family as FA
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return FA.step(r, w, row_id, str(body.get("status") or ""))
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/admin/overview")
async def app_api_admin_overview(app_key: str, request: Request):
    from .appmaker import family as FA

    def go():
        r, w = _be_app(app_key, request)
        return FA.admin_overview(r, w)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/admin/members")
async def app_api_admin_members(app_key: str, request: Request):
    from .appmaker import family as FA

    def go():
        r, w = _be_app(app_key, request)
        return {"members": FA.admin_members(r, w)}
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/admin/members/{member}/role")
async def app_api_admin_role(app_key: str, member: str, request: Request):
    from .appmaker import family as FA
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return FA.admin_role(r, w, member, str(body.get("role") or ""))
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/admin/partners")
async def app_api_admin_partners(app_key: str, request: Request):
    from .appmaker import family as FA

    def go():
        r, w = _be_app(app_key, request)
        return FA.admin_partners(r, w)
    return await asyncio.to_thread(_be_call, go)


@app.post("/api/app-api/{app_key}/admin/partners/{pid}")
async def app_api_admin_partner(app_key: str, pid: str, request: Request):
    from .appmaker import family as FA
    body = await _json_body(request)

    def go():
        r, w = _be_app(app_key, request)
        return FA.admin_decide(r, w, pid, body)
    return await asyncio.to_thread(_be_call, go)


@app.get("/api/app-api/{app_key}/admin/export/{coll}")
async def app_api_admin_export(app_key: str, coll: str, request: Request):
    from .appmaker import family as FA
    from .site import webapp as W

    def go():
        r, w = _be_app(app_key, request)
        return FA.export_csv(r, coll, w)
    try:
        text, name = await asyncio.to_thread(go)
    except W.AppError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=e.code)
    return Response(text.encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store",
                             "X-Content-Type-Options": "nosniff"})


_ADMIN_CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
              "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


@app.get("/app-admin/{app_key}")
async def app_admin_page(app_key: str):
    """The business's web admin: a page that signs in with an app staff / admin account and talks only to its own
    /api/app-api/<app_key>/ addresses (the server checks every rule)."""
    import re as _re
    if not _re.fullmatch(r"ak[0-9a-f]{8,38}", app_key or ""):
        raise HTTPException(404, "not found")
    return FileResponse(STATIC / "appadmin" / "index.html", media_type="text/html",
                        headers={"Content-Security-Policy": _ADMIN_CSP, "Cache-Control": "no-cache", "X-Frame-Options": "DENY",
                                 "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"})


@app.get("/api/apps/{ref}/sign", dependencies=[Depends(require_key)])
async def apps_sign(ref: str, tenant: str = Depends(current_tenant)):
    """v0.455 her login + security card: which ways are on, her client ids (masked where long), the permissions matrix,
    the audit log, and the last security gate."""
    from .appmaker import gates as GT
    from .appmaker import sign as SG

    def go():
        r = _be_data(tenant, ref)
        return {**SG.view(r), "gate": GT.last(r)}
    return await asyncio.to_thread(_be_owner_call, go)


@app.put("/api/apps/{ref}/sign", dependencies=[Depends(require_key)])
async def apps_sign_save(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker import sign as SG
    return await asyncio.to_thread(_be_owner_call, lambda: SG.save_settings(_be_data(tenant, ref), body or {}))


@app.post("/api/apps/{ref}/security/check", dependencies=[Depends(require_key)])
async def apps_security_check(ref: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """v0.455 run the security gates on the newest build (a failing gate blocks the store upload)."""
    from .appmaker import gates as GT
    b = body or {}
    return await asyncio.to_thread(_be_owner_call,
                                   lambda: GT.scan(_be_owner(tenant, ref), str(b.get("platform") or "android")))


@app.get("/api/apps/{ref}/family", dependencies=[Depends(require_key)])
async def apps_family(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import family as FA
    return await asyncio.to_thread(_be_owner_call, lambda: FA.view(_be_owner(tenant, ref)))


@app.post("/api/apps/{ref}/family/face", dependencies=[Depends(require_key)])
async def apps_family_face(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap: a delivery partner / partner shop / staff / customer app on the SAME backend (its own plan card next)."""
    from .appmaker import family as FA
    return await asyncio.to_thread(_be_owner_call, lambda: FA.add_face(tenant, ref, str(body.get("kind") or ""),
                                                                       str(body.get("words") or ""), str(body.get("conv") or "")))


@app.put("/api/apps/{ref}/family/settings", dependencies=[Depends(require_key)])
async def apps_family_settings(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker import family as FA
    return await asyncio.to_thread(_be_owner_call, lambda: FA.save_settings(_be_data(tenant, ref), body))


@app.post("/api/apps/{ref}/family/partners/{pid}", dependencies=[Depends(require_key)])
async def apps_family_partner(ref: str, pid: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her Haan / Na / remove on a delivery partner or partner shop."""
    from .appmaker import family as FA
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: FA.admin_decide(_be_data(tenant, ref), W.Who(owner=True), pid, body))


@app.get("/api/apps/{ref}/connect", dependencies=[Depends(require_key)])
async def apps_connect(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import connect as CN
    return await asyncio.to_thread(_be_owner_call, lambda: CN.status(_be_data(tenant, ref)))


@app.post("/api/apps/{ref}/connect/pack", dependencies=[Depends(require_key)])
async def apps_connect_pack(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{pack, settings, secrets}: secrets sealed at once; the drafted actions wait for her approval tap."""
    from .appmaker import connect as CN
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: CN.apply_pack(_be_data(tenant, ref), str(b.get("pack") or ""),
                                                                         b.get("settings") if isinstance(b.get("settings"), dict) else {},
                                                                         b.get("secrets") if isinstance(b.get("secrets"), dict) else {}))


@app.put("/api/apps/{ref}/connect/actions", dependencies=[Depends(require_key)])
async def apps_connect_action(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker import connect as CN
    return await asyncio.to_thread(_be_owner_call, lambda: CN.save_action(_be_data(tenant, ref), (body or {}).get("action") or {}))


@app.post("/api/apps/{ref}/connect/actions/{key}/approve", dependencies=[Depends(require_key)])
async def apps_connect_approve(ref: str, key: str, body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker import connect as CN
    return await asyncio.to_thread(_be_owner_call, lambda: CN.approve(_be_data(tenant, ref), key, bool((body or {}).get("her_tap"))))


@app.delete("/api/apps/{ref}/connect/actions/{key}", dependencies=[Depends(require_key)])
async def apps_connect_action_drop(ref: str, key: str, tenant: str = Depends(current_tenant)):
    from .appmaker import connect as CN
    return await asyncio.to_thread(_be_owner_call, lambda: CN.remove_action(_be_data(tenant, ref), key))


@app.post("/api/apps/{ref}/connect/actions/{key}/run", dependencies=[Depends(require_key)])
async def apps_connect_run(ref: str, key: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her tap {row?, her_tap: true}: run an approved action now (a test on one entry)."""
    from .appmaker import connect as CN
    from .site import webapp as W
    b = body or {}

    def go():
        if not b.get("her_tap"):
            raise W.AppError("Sirf aapke tap se.", 403)
        return CN.run(_be_data(tenant, ref), key, str(b.get("row") or ""), "her_tap", wait=True)
    return await asyncio.to_thread(_be_owner_call, go)


@app.put("/api/apps/{ref}/connect/secrets/{name}", dependencies=[Depends(require_key)])
async def apps_connect_secret(ref: str, name: str, body: dict, tenant: str = Depends(current_tenant)):
    """{value}: typed in the app, sealed at once, returned by no route."""
    from .appmaker import connect as CN
    return await asyncio.to_thread(_be_owner_call, lambda: CN.set_secret(_be_data(tenant, ref), name, str((body or {}).get("value") or "")))


@app.delete("/api/apps/{ref}/connect/secrets/{name}", dependencies=[Depends(require_key)])
async def apps_connect_secret_drop(ref: str, name: str, tenant: str = Depends(current_tenant)):
    from .appmaker import connect as CN
    return await asyncio.to_thread(_be_owner_call, lambda: CN.forget_secret(_be_data(tenant, ref), name))


@app.put("/api/apps/{ref}/connect/hooks", dependencies=[Depends(require_key)])
async def apps_connect_hook_save(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker import connect as CN
    return await asyncio.to_thread(_be_owner_call, lambda: CN.save_hook(_be_data(tenant, ref), (body or {}).get("hook") or {}))


@app.delete("/api/apps/{ref}/connect/hooks/{key}", dependencies=[Depends(require_key)])
async def apps_connect_hook_drop(ref: str, key: str, tenant: str = Depends(current_tenant)):
    from .appmaker import connect as CN
    return await asyncio.to_thread(_be_owner_call, lambda: CN.remove_hook(_be_data(tenant, ref), key))


# ---- v0.425 RANG (App Sahayak Pillar G): custom native components (Kotlin + Swift) - house rules in code, her tap, build-proved.
@app.get("/api/apps/{ref}/components", dependencies=[Depends(require_key)])
async def apps_components(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import custom as CU
    return await asyncio.to_thread(_be_owner_call, lambda: CU.listing(_be_owner(tenant, ref)))


@app.post("/api/apps/{ref}/components/draft", dependencies=[Depends(require_key)])
async def apps_component_draft(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{words}: Opus drafts one component (Kotlin + Swift); refused when a house rule fails. Waits for her approval."""
    from .appmaker import custom as CU
    return await asyncio.to_thread(_be_owner_call, lambda: CU.draft(_be_owner(tenant, ref), str((body or {}).get("words") or "")))


@app.post("/api/apps/{ref}/components/{name}/approve", dependencies=[Depends(require_key)])
async def apps_component_approve(ref: str, name: str, body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker import custom as CU
    return await asyncio.to_thread(_be_owner_call, lambda: CU.approve(_be_owner(tenant, ref), name, bool((body or {}).get("her_tap"))))


@app.delete("/api/apps/{ref}/components/{name}", dependencies=[Depends(require_key)])
async def apps_component_drop(ref: str, name: str, tenant: str = Depends(current_tenant)):
    from .appmaker import custom as CU
    return await asyncio.to_thread(_be_owner_call, lambda: CU.remove(_be_owner(tenant, ref), name))


def _be_owner(tenant: str, ref: str):
    from .appmaker import service as A
    with A.session() as s:
        r = A._find(s, tenant, ref)
        s.expunge(r)
    return r


def _be_data(tenant: str, ref: str):
    """v0.435 PARIVAAR: the app whose DATA she means - a rider / shop / staff app runs on its main app's backend."""
    from .appmaker import family as FA
    return FA.home(_be_owner(tenant, ref))


def _be_owner_call(fn):
    from .site import webapp as W
    try:
        return _appd(fn)
    except W.AppError as e:
        raise HTTPException(e.code, str(e))


@app.get("/api/apps/{ref}/data", dependencies=[Depends(require_key)])
async def apps_data(ref: str, tenant: str = Depends(current_tenant)):
    """Her app's backend: lists, fields, rules, counts, the address the installed app talks to."""
    from .appmaker import backend as BE
    return await asyncio.to_thread(_be_owner_call, lambda: BE.owner_view(_be_data(tenant, ref)))


@app.get("/api/apps/{ref}/data/{coll}", dependencies=[Depends(require_key)])
async def apps_data_rows(ref: str, coll: str, tenant: str = Depends(current_tenant)):
    from .appmaker import backend as BE
    return await asyncio.to_thread(_be_owner_call, lambda: {"rows": BE.owner_rows(_be_data(tenant, ref), coll)})


@app.patch("/api/apps/{ref}/data/{coll}/{row_id}", dependencies=[Depends(require_key)])
async def apps_data_update(ref: str, coll: str, row_id: str, body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker import backend as BE
    return await asyncio.to_thread(_be_owner_call, lambda: BE.owner_update(_be_data(tenant, ref), coll, row_id, body))


@app.post("/api/apps/{ref}/data/{coll}/{row_id}/credit-note", dependencies=[Depends(require_key)])
async def apps_credit_note(ref: str, coll: str, row_id: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """v0.356 WAPSI: her credit note for an invoiced row (a return / a wrong bill), full value, with her reason."""
    from .appmaker import gst as G
    return await asyncio.to_thread(_be_owner_call, lambda: G.credit(_be_data(tenant, ref), coll, row_id,
                                                                    str((body or {}).get("reason") or "")))


@app.get("/api/apps/{ref}/turant", dependencies=[Depends(require_key)])
async def apps_turant(ref: str, tenant: str = Depends(current_tenant)):
    """v0.367 TURANT: instant notifications for this app's Android phones (on / off, phones registered)."""
    from .appmaker import turant as TU
    return await asyncio.to_thread(_be_owner_call, lambda: TU.view(_be_owner(tenant, ref)))


@app.put("/api/apps/{ref}/turant/ios", dependencies=[Depends(require_key)])
async def apps_turant_ios(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.368 her Apple push key {key_id, team_id, p8} (sealed, never returned) or {clear: true}."""
    from .appmaker import turant as TU
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: TU.clear_ios_key(_be_owner(tenant, ref)) if b.get("clear")
                                   else TU.set_ios_key(_be_owner(tenant, ref), str(b.get("key_id") or ""), str(b.get("team_id") or ""),
                                                       str(b.get("p8") or "")))


@app.put("/api/apps/{ref}/turant", dependencies=[Depends(require_key)])
async def apps_turant_set(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.367 her tap: {on: true} registers the app in Hoola's Firebase project (next build carries it); {on: false} = off."""
    from .appmaker import turant as TU
    return await asyncio.to_thread(_be_owner_call, lambda: TU.enable(_be_owner(tenant, ref)) if (body or {}).get("on")
                                   else TU.disable(_be_owner(tenant, ref)))


# ---- v0.396 APNA DATABASE: an app's data in HER own database (Supabase, Neon, RDS ... any PostgreSQL-wire)
@app.get("/api/apps/{ref}/owndb", dependencies=[Depends(require_key)])
async def apps_owndb(ref: str, tenant: str = Depends(current_tenant)):
    """The link, her connected databases (Profile > Postgres database), the provider list, sync lag."""
    from .appmaker import owndb as OD
    return await asyncio.to_thread(_be_owner_call, lambda: OD.status(_be_data(tenant, ref)))


@app.post("/api/owndb/conns", dependencies=[Depends(require_key)])
async def owndb_conn_add(body: dict, tenant: str = Depends(current_tenant)):
    """v0.404 her database typed in the APP {kind: postgres|mysql|mongodb|firestore, name, secret}: checked (public host,
    encrypted), test-connected, sealed; never returned, logged or shown to the model."""
    from .appmaker import owndb_conns as OC
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: OC.add(tenant, str(b.get("kind") or ""), str(b.get("name") or ""),
                                                                  str(b.get("secret") or b.get("dsn") or "")))


@app.delete("/api/owndb/conns/{cid}", dependencies=[Depends(require_key)])
async def owndb_conn_remove(cid: str, tenant: str = Depends(current_tenant)):
    from .appmaker import owndb_conns as OC
    return await asyncio.to_thread(_be_owner_call, lambda: OC.remove(tenant, cid))


@app.post("/api/apps/{ref}/owndb/link", dependencies=[Depends(require_key)])
async def apps_owndb_link(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """HER TAP {conn, mode: primary|mirror}: backup, her tables, every row copied, counts compared, then live."""
    from .appmaker import owndb as OD
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: OD.link(_be_data(tenant, ref), str(b.get("conn") or ""),
                                                                   str(b.get("mode") or "primary")))


@app.post("/api/apps/{ref}/owndb/unlink", dependencies=[Depends(require_key)])
async def apps_owndb_unlink(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import owndb as OD
    return await asyncio.to_thread(_be_owner_call, lambda: OD.unlink(_be_data(tenant, ref)))


@app.post("/api/apps/{ref}/owndb/verify", dependencies=[Depends(require_key)])
async def apps_owndb_verify(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import owndb as OD
    return await asyncio.to_thread(_be_owner_call, lambda: OD.verify(_be_data(tenant, ref)))


@app.post("/api/apps/{ref}/owndb/sync", dependencies=[Depends(require_key)])
async def apps_owndb_sync(ref: str, tenant: str = Depends(current_tenant)):
    """Sync now: pending writes there, her outside edits back (instead of waiting up to 20 s)."""
    from .appmaker import owndb as OD

    def go():
        r = _be_data(tenant, ref)
        o = OD.cfg(r, fresh=True)
        if not o:
            raise OD.OwnDbError("Yeh app kisi database se judi nahi hai.", 404)
        n = OD.tick(force=True)
        return {"ok": True, "synced": n, **OD.status(_be_data(tenant, ref))}
    return await asyncio.to_thread(_be_owner_call, go)


# ---- v0.390 PAKKI NEEV: her app's data - backups, point-in-time restore (her tap), export, usage + limits
@app.get("/api/apps/{ref}/backups", dependencies=[Depends(require_key)])
async def apps_backups(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import backup as BK
    return await asyncio.to_thread(_be_owner_call, lambda: {"backups": BK.snapshots(_be_data(tenant, ref))})


@app.post("/api/apps/{ref}/backups/now", dependencies=[Depends(require_key)])
async def apps_backup_now(ref: str, tenant: str = Depends(current_tenant)):
    """A snapshot now (her button)."""
    from .appmaker import backup as BK
    return await asyncio.to_thread(_be_owner_call, lambda: BK.snapshot(_be_data(tenant, ref), "by hand", "manual"))


@app.post("/api/apps/{ref}/backups/preview", dependencies=[Depends(require_key)])
async def apps_backup_preview(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """{at: "YYYY-MM-DDTHH:MM" IST} or {name}: what a restore would change - nothing is changed."""
    from .appmaker import backup as BK
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: BK.preview(_be_data(tenant, ref), str(b.get("at") or ""), str(b.get("name") or "")))


@app.post("/api/apps/{ref}/backups/restore", dependencies=[Depends(require_key)])
async def apps_backup_restore(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """HER TAP: the app's rows back to a snapshot {name} or a minute {at} (a safety snapshot is taken first)."""
    from .appmaker import backup as BK
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: BK.restore(_be_data(tenant, ref), str(b.get("at") or ""),
                                                                      str(b.get("name") or ""), bool(b.get("members"))))


@app.get("/api/apps/{ref}/export", dependencies=[Depends(require_key)])
async def apps_export(ref: str, tenant: str = Depends(current_tenant)):
    """Her data as a ZIP: a CSV per list + data.json + accounts (never a password)."""
    from .appmaker import backup as BK

    def go():
        r = _be_data(tenant, ref)
        return r, BK.export(r)
    r, data = await asyncio.to_thread(_be_owner_call, go)
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", f"{r.name or 'app'}-{r.number}-data").strip("-") + ".zip"
    return Response(data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}"',
                                                                  "Cache-Control": "no-store"})


@app.get("/api/apps/{ref}/usage", dependencies=[Depends(require_key)])
async def apps_usage(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import meter as MT
    return await asyncio.to_thread(_be_owner_call, lambda: MT.usage(_be_data(tenant, ref)))


@app.put("/api/apps/{ref}/usage", dependencies=[Depends(require_key)])
async def apps_usage_set(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her limits {rows, files_mb, writes_day} (never above the ceiling, never below what is used)."""
    from .appmaker import meter as MT
    return await asyncio.to_thread(_be_owner_call, lambda: MT.set_limits(_be_data(tenant, ref), body or {}))


# ---- v0.382 DIMAAG: her side of the app's logic (Opus drafts, the checker proves, HER tap applies)
@app.get("/api/apps/{ref}/logic", dependencies=[Depends(require_key)])
async def apps_logic(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker.logic import service as LS
    return await asyncio.to_thread(_be_owner_call, lambda: LS.view(_be_data(tenant, ref)))


@app.post("/api/apps/{ref}/logic/draft", dependencies=[Depends(require_key)])
async def apps_logic_draft(ref: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """{words}: Opus writes the logic for this app's real lists; checked; kept as a DRAFT (her live app unchanged)."""
    from .appmaker.logic import service as LS
    return await asyncio.to_thread(_be_owner_call, lambda: LS.draft(_be_data(tenant, ref), str((body or {}).get("words") or "")))


@app.delete("/api/apps/{ref}/logic/draft", dependencies=[Depends(require_key)])
async def apps_logic_discard(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker.logic import service as LS
    return await asyncio.to_thread(_be_owner_call, lambda: LS.discard(_be_data(tenant, ref)))


@app.post("/api/apps/{ref}/logic/apply", dependencies=[Depends(require_key)])
async def apps_logic_apply(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """HER TAP: {hash} = the exact draft she saw goes live (new lists / fields first, then the logic, then a recompute)."""
    from .appmaker.logic import service as LS
    return await asyncio.to_thread(_be_owner_call, lambda: LS.apply(_be_data(tenant, ref), str((body or {}).get("hash") or "")))


@app.put("/api/apps/{ref}/logic", dependencies=[Depends(require_key)])
async def apps_logic_save(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """The console editor {logic, lists, fields}: the same checker; saved + applied only when it has zero errors."""
    from .appmaker.logic import service as LS
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: LS.save(_be_data(tenant, ref), b.get("logic") or {}, b.get("lists"), b.get("fields")))


@app.post("/api/apps/{ref}/logic/switch", dependencies=[Depends(require_key)])
async def apps_logic_switch(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    from .appmaker.logic import service as LS
    return await asyncio.to_thread(_be_owner_call, lambda: LS.switch(_be_data(tenant, ref), bool((body or {}).get("on"))))


@app.post("/api/apps/{ref}/logic/test", dependencies=[Depends(require_key)])
async def apps_logic_test(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """Try a formula {coll, expr, row} on a real row - nothing saved."""
    from .appmaker.logic import service as LS
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: LS.test(_be_data(tenant, ref), str(b.get("coll") or ""),
                                                                   str(b.get("expr") or ""), str(b.get("row") or "")))


@app.post("/api/apps/{ref}/logic/run/{name}", dependencies=[Depends(require_key)])
async def apps_logic_run(ref: str, name: str, tenant: str = Depends(current_tenant)):
    """Run one scheduled job now (her button)."""
    from .appmaker.logic import engine as LE
    return await asyncio.to_thread(_be_owner_call, lambda: LE.run_schedule(_be_data(tenant, ref), name, force=True))


@app.get("/api/apps/{ref}/logic/audit", dependencies=[Depends(require_key)])
async def apps_logic_audit(ref: str, row: str = "", limit: int = 100, tenant: str = Depends(current_tenant)):
    from .appmaker.logic import engine as LE
    return await asyncio.to_thread(_be_owner_call, lambda: {"audit": LE.audit_list(_be_data(tenant, ref), limit, row)})


@app.get("/api/apps/{ref}/approvals", dependencies=[Depends(require_key)])
async def apps_approvals(ref: str, all: int = 0, tenant: str = Depends(current_tenant)):
    from .appmaker.logic import engine as LE
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: {"approvals": LE.approvals(_be_data(tenant, ref), W.Who(owner=True), bool(all))})


@app.post("/api/apps/{ref}/approvals/{appr_id}", dependencies=[Depends(require_key)])
async def apps_decide(ref: str, appr_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """Her decision on an approval step {decision: approve|reject, note} (the owner may decide any step)."""
    from .appmaker.logic import engine as LE
    from .site import webapp as W
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: LE.decide(_be_data(tenant, ref), appr_id, str(b.get("decision") or ""),
                                                                     str(b.get("note") or ""), W.Who(owner=True)))


@app.get("/api/apps/{ref}/variants", dependencies=[Depends(require_key)])
async def apps_variants(ref: str, tenant: str = Depends(current_tenant)):
    """v0.362 VARIANTS: each product's sizes (name + own price)."""
    from .appmaker import variants as VR
    return await asyncio.to_thread(_be_owner_call, lambda: VR.view(_be_data(tenant, ref)))


@app.put("/api/apps/{ref}/variants", dependencies=[Depends(require_key)])
async def apps_variants_set(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.362 one product's sizes {product: id or name, variants: [{name, price}]} ([] removes them)."""
    from .appmaker import variants as VR
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: VR.save(_be_data(tenant, ref), str(b.get("product") or ""), b.get("variants")))


@app.get("/api/apps/{ref}/hisaab", dependencies=[Depends(require_key)])
async def apps_hisaab(ref: str, month: str = "", download: int = 0, tenant: str = Depends(current_tenant)):
    """v0.361 HISAAB: the month's summary (download=1: ZIP of CSVs - sales, invoices, credit notes, HSN, rates, khata)."""
    from .appmaker import hisaab as HS

    def go():
        r = _be_data(tenant, ref)
        if download:
            return HS.zip_bytes(r, month)
        rep = HS.build(r, month)
        return {k: rep[k] for k in ("month", "summary", "say", "counts")}
    out = await asyncio.to_thread(_be_owner_call, go)
    if not download:
        return out
    data, name, _rep = out
    return Response(data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}"',
                                                                 "Cache-Control": "private, no-store"})


@app.get("/api/apps/{ref}/tally", dependencies=[Depends(require_key)])
async def apps_tally(ref: str, month: str = "", tenant: str = Depends(current_tenant)):
    """v0.374 TALLY EXPORT: the month's invoices + credit notes as Tally XML vouchers (Import > Vouchers in her Tally)."""
    from .appmaker import tally as TL
    data, name, _n = await asyncio.to_thread(_be_owner_call, lambda: TL.file_bytes(_be_data(tenant, ref), month))
    return Response(data, media_type="application/xml", headers={"Content-Disposition": f'attachment; filename="{name}"',
                                                                 "Cache-Control": "private, no-store"})


@app.put("/api/apps/{ref}/tally", dependencies=[Depends(require_key)])
async def apps_tally_names(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.374 her Tally ledger names {party, sales, cgst, sgst, igst, round}."""
    from .appmaker import tally as TL
    return await asyncio.to_thread(_be_owner_call, lambda: TL.set_names(_be_data(tenant, ref), body))


@app.get("/api/apps/{ref}/gstr1", dependencies=[Depends(require_key)])
async def apps_gstr1(ref: str, month: str = "", tenant: str = Depends(current_tenant)):
    """v0.373 GSTR-1 FILE: the month's GSTR-1 JSON (GST offline tool shape) from her invoices + credit notes. Nothing is filed."""
    from .appmaker import gstr1 as GR
    data, name = await asyncio.to_thread(_be_owner_call, lambda: GR.file_bytes(_be_data(tenant, ref), month))
    return Response(data, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{name}"',
                                                                  "Cache-Control": "private, no-store"})


@app.get("/api/apps/{ref}/delivery", dependencies=[Depends(require_key)])
async def apps_delivery(ref: str, tenant: str = Depends(current_tenant)):
    """v0.360 DELIVERY: fee, free above, PIN codes, opening hours."""
    from .appmaker import delivery as DL
    return await asyncio.to_thread(_be_owner_call, lambda: DL.view(_be_data(tenant, ref)))


@app.put("/api/apps/{ref}/delivery", dependencies=[Depends(require_key)])
async def apps_delivery_set(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.360 set them ({off: true} = no delivery rules); v0.371 {slots: [{label, start, end, cap}], days, cutoff} = time slots."""
    from .appmaker import delivery as DL
    b = body or {}
    if "holidays" in b:                                  # v0.377 her holidays
        return await asyncio.to_thread(_be_owner_call, lambda: DL.save_holidays(_be_data(tenant, ref), b.get("holidays")))
    if "slots" in b:
        return await asyncio.to_thread(_be_owner_call, lambda: DL.save_slots(_be_data(tenant, ref), b.get("slots"), b.get("days"), b.get("cutoff")))
    return await asyncio.to_thread(_be_owner_call, lambda: DL.save(_be_data(tenant, ref), body))


@app.get("/api/apps/{ref}/chat", dependencies=[Depends(require_key)])
async def apps_chat(ref: str, member: str = "", tenant: str = Depends(current_tenant)):
    """v0.378 BAAT: her customers' threads (member= one thread)."""
    from .appmaker import baat as BT
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: BT.thread(_be_data(tenant, ref), W.Who(owner=True), member) if member
                                   else BT.threads(_be_data(tenant, ref), W.Who(owner=True)))


@app.post("/api/apps/{ref}/chat/{member}", dependencies=[Depends(require_key)])
async def apps_chat_reply(ref: str, member: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.378 her reply to a customer - only from her own tap {text, her_tap: true}."""
    from .appmaker import baat as BT
    from .site import webapp as W
    b = body or {}
    return await asyncio.to_thread(_be_owner_call, lambda: BT.reply(_be_data(tenant, ref), W.Who(owner=True), member,
                                                                    str(b.get("text") or ""), bool(b.get("her_tap"))))


@app.get("/api/apps/{ref}/khata", dependencies=[Depends(require_key)])
async def apps_khata(ref: str, member: str = "", tenant: str = Depends(current_tenant)):
    """v0.359 KHATA: who owes how much (member= one customer's entries)."""
    from .appmaker import khata as KH
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: KH.summary(_be_data(tenant, ref), member) if member
                                   else KH.dues(_be_data(tenant, ref), W.Who(owner=True)))


@app.get("/api/apps/{ref}/khata-yaad", dependencies=[Depends(require_key)])
async def apps_khata_yaad(ref: str, tenant: str = Depends(current_tenant)):
    """v0.375 KHATA YAAD: customers who owe + the ready reminder (wa.me link for her own phone, template allowed or not)."""
    from .appmaker import khata as KH
    return await asyncio.to_thread(_be_owner_call, lambda: KH.reminders(_be_data(tenant, ref)))


@app.post("/api/apps/{ref}/khata-yaad/{member}", dependencies=[Depends(require_key)])
async def apps_khata_yaad_send(ref: str, member: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.375 her tap: the reminder through her WhatsApp Business number with her approved UTILITY template {template, her_tap}."""
    from .appmaker import khata as KH
    from .site import webapp as W
    b = body or {}
    r = await asyncio.to_thread(_be_owner_call, lambda: _be_data(tenant, ref))
    try:
        return await KH.send_reminder(r, member, str(b.get("template") or ""), bool(b.get("her_tap")))
    except W.AppError as e:
        raise HTTPException(e.code, str(e))


@app.post("/api/apps/{ref}/khata/{member}/pay", dependencies=[Depends(require_key)])
async def apps_khata_pay(ref: str, member: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.359 she records a customer's payment (cash / UPI ...; money never moves here)."""
    from .appmaker import khata as KH
    from .site import webapp as W
    return await asyncio.to_thread(_be_owner_call, lambda: KH.payment(_be_data(tenant, ref), member, (body or {}).get("amount"),
                                                                      str((body or {}).get("mode") or "cash"),
                                                                      str((body or {}).get("note") or ""), W.Who(owner=True)))


@app.get("/api/apps/{ref}/coupons", dependencies=[Depends(require_key)])
async def apps_coupons(ref: str, tenant: str = Depends(current_tenant)):
    """v0.358 COUPON: her discount codes (uses, customers, live or not)."""
    from .appmaker import coupon as CP
    return await asyncio.to_thread(_be_owner_call, lambda: CP.view(_be_data(tenant, ref)))


@app.put("/api/apps/{ref}/coupons", dependencies=[Depends(require_key)])
async def apps_coupons_set(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.358 make / change / delete one code."""
    from .appmaker import coupon as CP
    return await asyncio.to_thread(_be_owner_call, lambda: CP.save(_be_data(tenant, ref), body))


@app.get("/api/apps/{ref}/stock", dependencies=[Depends(require_key)])
async def apps_stock(ref: str, tenant: str = Depends(current_tenant)):
    """v0.357 STOCK: each product's stock + warning level (blank = unlimited)."""
    from .appmaker import stock as SK
    return await asyncio.to_thread(_be_owner_call, lambda: SK.view(_be_data(tenant, ref)))


@app.put("/api/apps/{ref}/stock", dependencies=[Depends(require_key)])
async def apps_stock_set(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.357 set stock {items: {product id: {qty: n | null, low: n}}}."""
    from .appmaker import stock as SK
    return await asyncio.to_thread(_be_owner_call, lambda: SK.set_items(_be_data(tenant, ref), (body or {}).get("items") or {}))


@app.get("/api/apps/{ref}/gst", dependencies=[Depends(require_key)])
async def apps_gst(ref: str, tenant: str = Depends(current_tenant)):
    """v0.355 GST BILL: her GST details for this app (GSTIN, legal name, default rate / HSN, per-product HSN + rate)."""
    from .appmaker import gst as G
    return await asyncio.to_thread(_be_owner_call, lambda: G.view(_be_data(tenant, ref)))


@app.put("/api/apps/{ref}/gst", dependencies=[Depends(require_key)])
async def apps_gst_set(ref: str, body: dict, tenant: str = Depends(current_tenant)):
    """v0.355 set them; gstin "" = plain receipts again (issued invoice numbers are kept)."""
    from .appmaker import gst as G
    return await asyncio.to_thread(_be_owner_call, lambda: G.set_settings(_be_data(tenant, ref), body))


@app.get("/api/apps/{ref}/data/{coll}/{row_id}/receipt", dependencies=[Depends(require_key)])
async def apps_data_receipt(ref: str, coll: str, row_id: str, doc: str = "", tenant: str = Depends(current_tenant)):
    """v0.354 RASEED: her copy of a finished row's receipt PDF (v0.356 doc=invoice: the original invoice behind a credit note)."""
    from .appmaker import receipt as RC

    def go():
        r = _be_data(tenant, ref)
        doc_ = "invoice" if doc == "invoice" else ""
        data = RC.for_owner(r, coll, row_id, doc_)
        row = RC._load(r, coll, row_id)[1]
        name = RC.filename(r, row)
        if doc_ and name.startswith("credit-note-"):
            inv = RC.BE._j(row.data, {}).get("_inv_no", "")
            name = f"invoice-{inv.replace('/', '-')}.pdf"
        return data, name
    data, name = await asyncio.to_thread(_be_owner_call, go)
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "private, no-store",
        "Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"})


@app.get("/api/apps/{ref}/files/{fid}", dependencies=[Depends(require_key)])
async def apps_data_file(ref: str, fid: str, tenant: str = Depends(current_tenant)):
    """v0.319 a photo her app's users sent (for her data view)."""
    from .appmaker import backend as BE
    from .site import webapp as W
    try:
        r = await asyncio.to_thread(_be_owner, tenant, ref)
        f = await asyncio.to_thread(BE.file_for, r, fid, W.Who(owner=True))
    except (W.AppError, HTTPException):
        raise HTTPException(404, "not found")
    except Exception:
        raise HTTPException(404, "not found")
    if str(f).endswith(".pdf"):                  # v0.346
        return FileResponse(f, media_type="application/pdf", filename=f"{fid}.pdf",
                            headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff",
                                     "Content-Security-Policy": "sandbox", "Content-Disposition": f'attachment; filename="{fid}.pdf"'})
    return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@app.get("/api/apps/{ref}/store", dependencies=[Depends(require_key)])
async def apps_store(ref: str, tenant: str = Depends(current_tenant)):
    """v0.330 Play Store launch: steps, package, account (masked), listing, bundle, releases, data safety, the pages."""
    from .appmaker.android import store as ST
    return await asyncio.to_thread(_appd, ST.get, tenant, ref)


@app.post("/api/apps/{ref}/store/{what}", dependencies=[Depends(require_key)])
async def apps_store_act(ref: str, what: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """setup {package} | credentials {json} (her Play service-account key: sealed, never shown) | forget | listing {regen, edit}
    | build | publish {track, her_tap} - production only from her tap in the app (her_tap=true is sent by the app's button)."""
    from .appmaker.android import store as ST
    body = body or {}
    if what == "setup":
        return await asyncio.to_thread(_appd, ST.setup, tenant, ref, str(body.get("package") or ""))
    if what == "credentials":
        raw = body.get("json")
        return await asyncio.to_thread(_appd, ST.set_credentials, tenant, ref, raw if isinstance(raw, str) else json.dumps(raw or {}))
    if what == "forget":
        return await asyncio.to_thread(_appd, ST.forget_credentials, tenant, ref)
    if what == "listing":
        return await asyncio.to_thread(_appd, ST.listing, tenant, ref, bool(body.get("regen")),
                                       body.get("edit") if isinstance(body.get("edit"), dict) else None)
    if what == "listing_lang":                   # v0.372 her own words for one language's listing
        return await asyncio.to_thread(_appd, ST.listing_lang, tenant, ref, str(body.get("lang") or ""),
                                       body.get("values") if isinstance(body.get("values"), dict) else {})
    if what == "build":
        return await asyncio.to_thread(_appd, ST.build_bundle, tenant, ref)
    if what == "publish":
        return await asyncio.to_thread(_appd, ST.publish, tenant, ref, str(body.get("track") or "internal"), bool(body.get("her_tap")))
    raise HTTPException(404, "unknown")


def _code(fn, *a, **k):
    from .appmaker import code as CODE
    from .site import github as GH
    try:
        return fn(*a, **k)
    except (CODE.CodeError, GH.GithubError) as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, f"not found: {e}")


@app.get("/api/apps/{ref}/bhasha", dependencies=[Depends(require_key)])
async def apps_bhasha(ref: str, tenant: str = Depends(current_tenant)):
    """v0.347 the app's languages, the ones it can carry, how many words, translated share per language."""
    from .appmaker import i18n as I18
    return await asyncio.to_thread(_appd, I18.get, tenant, ref)


@app.get("/api/apps/{ref}/match", dependencies=[Depends(require_key)])
async def apps_match(ref: str, tenant: str = Depends(current_tenant)):
    """v0.343 how close each real app screen (Android / iPhone device check) is to her approved design (0-100 + notes)."""
    from .appmaker import match as MT
    return await asyncio.to_thread(_appd, MT.get, tenant, ref)


@app.get("/api/apps/{ref}/github", dependencies=[Depends(require_key)])
async def apps_github(ref: str, tenant: str = Depends(current_tenant)):
    """v0.342 her app's code in HER GitHub: linked token?, repo name, cards / pushes, commits made."""
    from .appmaker import code as CODE
    return await asyncio.to_thread(_code, CODE.view, tenant, ref)


@app.get("/api/apps/{ref}/appstore", dependencies=[Depends(require_key)])
async def apps_appstore(ref: str, tenant: str = Depends(current_tenant)):
    """v0.338 App Store launch: steps, listing, privacy + support pages, App Privacy answers, one-time steps, submissions."""
    from .appmaker.ios import appstore as AP
    return await asyncio.to_thread(_appd, AP.get, tenant, ref)


@app.post("/api/apps/{ref}/appstore/{what}", dependencies=[Depends(require_key)])
async def apps_appstore_act(ref: str, what: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """listing {regen, edit} | push (listing + screenshots + build onto App Store Connect, via her builds repo) |
    submit {her_tap} - Submit for Review only from her tap in the app (the app's button sends her_tap=true)."""
    from .appmaker.ios import appstore as AP
    body = body or {}
    if what == "listing":
        return await asyncio.to_thread(_appd, AP.listing, tenant, ref, bool(body.get("regen")),
                                       body.get("edit") if isinstance(body.get("edit"), dict) else None)
    if what == "push":
        return await asyncio.to_thread(_appd, AP.push, tenant, ref)
    if what == "submit":
        return await asyncio.to_thread(_appd, AP.submit, tenant, ref, bool(body.get("her_tap")))
    raise HTTPException(404, "unknown")


@app.get("/api/apps/{ref}/store-cert", dependencies=[Depends(require_key)])
async def apps_store_cert(ref: str, tenant: str = Depends(current_tenant)):
    """The upload certificate (public part), if Play Console asks for it."""
    from .appmaker.android import store as ST
    try:
        data, name = await asyncio.to_thread(ST.upload_cert, tenant, ref)
    except ST.StoreError:
        raise HTTPException(404, "not found")
    return Response(data, media_type="application/x-pem-file", headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ---- v0.546 CHALTA KAAM (App Sahayak Pillar L): the app AFTER it ships - use, speed, failures, cost, alerts.
@app.get("/api/apps/{ref}/ops", dependencies=[Depends(require_key)])
async def apps_ops(ref: str, days: int = 14, tenant: str = Depends(current_tenant)):
    """Users, orders, errors, latency (estimated from bins), 30-day cost, crashes + ANRs, limits, open alerts."""
    from .appmaker import ops as OPS
    return await asyncio.to_thread(_be_owner_call,
                                   lambda: OPS.dashboard(_be_owner(tenant, ref), max(1, min(days, 90))))


@app.post("/api/apps/{ref}/ops/{what}", dependencies=[Depends(require_key)])
async def apps_ops_act(ref: str, what: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """estimate {job} = what the next big job cost HER last times | alerts = run the rules now (her chat gets one
    line per kind per day) | flush = write out what the workers measured."""
    from .appmaker import ops as OPS
    b = body or {}
    if what == "estimate":
        r = _be_owner(tenant, ref)
        return await asyncio.to_thread(_be_owner_call, lambda: OPS.estimate(r, str(b.get("job") or "build")))
    if what == "alerts":
        r = _be_owner(tenant, ref)
        return await asyncio.to_thread(_be_owner_call, lambda: OPS.watch(r))
    if what == "flush":
        return await asyncio.to_thread(_be_owner_call, lambda: (OPS.flush(), {"ok": True})[1])
    raise HTTPException(404, "unknown ops action")


# ---- v0.542 NAKSHA (App Sahayak Pillar K): her one line -> a spec -> the app, one module at a time.
@app.get("/api/apps/{ref}/naksha", dependencies=[Depends(require_key)])
async def apps_naksha(ref: str, tenant: str = Depends(current_tenant)):
    """The whole plan with each module's state (waiting / approved / built / changed) and the changelog."""
    from .appmaker import architect as AR
    return await asyncio.to_thread(_be_owner_call, lambda: AR.card(_be_owner(tenant, ref)))


@app.post("/api/apps/{ref}/naksha/{what}", dependencies=[Depends(require_key)])
async def apps_naksha_act(ref: str, what: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """plan {words} | answer {ask, said} | approve {module, hash} = HER TAP on one module | build {module} |
    revise {words} = the change edits the spec and only the touched modules are rebuilt."""
    from .appmaker import architect as AR
    b = body or {}
    r = _be_owner(tenant, ref)
    if what == "plan":
        return await asyncio.to_thread(_be_owner_call, lambda: AR.plan(r, str(b.get("words") or "")))
    if what == "answer":
        return await asyncio.to_thread(_be_owner_call,
                                       lambda: AR.answer(r, str(b.get("ask") or ""), str(b.get("said") or "")))
    if what == "approve":
        return await asyncio.to_thread(_be_owner_call,
                                       lambda: AR.approve(r, str(b.get("module") or ""), str(b.get("hash") or "")))
    if what == "build":
        return await asyncio.to_thread(_be_owner_call, lambda: AR.build(r, str(b.get("module") or "")))
    if what == "revise":
        return await asyncio.to_thread(_be_owner_call, lambda: AR.revise(r, str(b.get("words") or "")))
    raise HTTPException(404, "unknown naksha action")


# ---- v0.540 JAANCH (App Sahayak Pillar J): the app is proved, and a new version goes out a few users at a time.
# NOTE the two path segments: a single-segment POST would be eaten by the /api/apps/{ref}/{action} catch-all above.
@app.get("/api/apps/{ref}/jaanch", dependencies=[Depends(require_key)])
async def apps_jaanch(ref: str, tenant: str = Depends(current_tenant)):
    """Pillar J's card: scenario tests, rule checks, load, and what real phones reported (+ what was NOT checked)."""
    from .appmaker import quality as QA
    return await asyncio.to_thread(_be_owner_call, lambda: QA.card(_be_owner(tenant, ref)))


@app.post("/api/apps/{ref}/jaanch/{what}", dependencies=[Depends(require_key)])
async def apps_jaanch_act(ref: str, what: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """stories {words} = Opus writes them | keep {hash} = her tap makes them the app's test set | run | cases |
    rules | all | load {customers} (hundreds of accounts on the twin: asked for, never a side effect)."""
    from .appmaker import quality as QA
    b = body or {}
    r = _be_owner(tenant, ref)
    if what == "stories":
        return await asyncio.to_thread(_be_owner_call, lambda: QA.draft(r, str(b.get("words") or "")))
    if what == "keep":
        return await asyncio.to_thread(_be_owner_call, lambda: QA.keep(r, str(b.get("hash") or "")))
    if what == "run":
        return await asyncio.to_thread(_be_owner_call, lambda: QA.run(r, base=str(b.get("base") or "")))
    if what == "cases":
        return await asyncio.to_thread(_be_owner_call, lambda: QA.rule_cases(r))
    if what == "rules":
        return await asyncio.to_thread(_be_owner_call, lambda: QA.rules_run(r))
    if what == "all":
        return await asyncio.to_thread(_be_owner_call, lambda: QA.run_all(r, base=str(b.get("base") or "")))
    if what == "load":
        return await asyncio.to_thread(_be_owner_call,
                                       lambda: QA.load(r, int(b.get("customers") or 200), str(b.get("base") or "")))
    raise HTTPException(404, "unknown jaanch action")


@app.get("/api/apps/{ref}/rollout", dependencies=[Depends(require_key)])
async def apps_rollout(ref: str, tenant: str = Depends(current_tenant)):
    """v0.540 the staged rollout on Play + her feature switches."""
    from .appmaker import rollout as RO
    return await asyncio.to_thread(_appd, RO.view, tenant, ref)


@app.post("/api/apps/{ref}/rollout/{what}", dependencies=[Depends(require_key)])
async def apps_rollout_act(ref: str, what: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
    """flag {key, on, percent, label} | unflag {key} - instant, no build.
    start {her_tap} | advance {her_tap} | halt {why} | rollback {her_tap} - Play's staged release (production = her tap)."""
    from .appmaker import rollout as RO
    b = body or {}
    if what == "flag":
        r = _be_owner(tenant, ref)
        return await asyncio.to_thread(_be_owner_call, lambda: RO.set_flag(
            r, str(b.get("key") or ""), b.get("on") if isinstance(b.get("on"), bool) else None,
            int(b["percent"]) if isinstance(b.get("percent"), (int, float)) else None, str(b.get("label") or "")))
    if what == "unflag":
        r = _be_owner(tenant, ref)
        return await asyncio.to_thread(_be_owner_call, lambda: RO.drop_flag(r, str(b.get("key") or "")))
    if what == "start":
        return await asyncio.to_thread(_appd, RO.start, tenant, ref, bool(b.get("her_tap")),
                                       float(b.get("fraction") or RO.STAGES[0]))
    if what == "advance":
        return await asyncio.to_thread(_appd, RO.advance, tenant, ref, bool(b.get("her_tap")),
                                       float(b.get("fraction") or 0))
    if what == "halt":
        return await asyncio.to_thread(_appd, RO.halt, tenant, ref, str(b.get("why") or ""))
    if what == "rollback":
        return await asyncio.to_thread(_appd, RO.rollback, tenant, ref, bool(b.get("her_tap")))
    raise HTTPException(404, "unknown rollout action")


@app.get("/api/apps/{ref}/crashes", dependencies=[Depends(require_key)])
async def apps_crashes(ref: str, tenant: str = Depends(current_tenant)):
    """v0.325 crashes on her app users' phones, grouped (same exception + same app frames), newest problems first."""
    from .appmaker import backend as BE
    return await asyncio.to_thread(_be_owner_call, lambda: {"crashes": BE.crashes(_be_owner(tenant, ref))[:100]})


@app.get("/api/apps/{ref}/members", dependencies=[Depends(require_key)])
async def apps_members(ref: str, tenant: str = Depends(current_tenant)):
    from .appmaker import backend as BE
    return await asyncio.to_thread(_be_owner_call, lambda: {"members": BE.members(_be_data(tenant, ref))})


@app.post("/api/apps/{ref}/members/{member_id}/role", dependencies=[Depends(require_key)])
async def apps_member_role(ref: str, member_id: str, body: dict, tenant: str = Depends(current_tenant)):
    """She makes an account staff / admin (a new account of a staff app sees nothing until she does)."""
    from .appmaker import backend as BE
    return await asyncio.to_thread(_be_owner_call, lambda: BE.set_role(_be_data(tenant, ref), member_id,
                                                                       str(body.get("role") or "")))


@app.get("/api/apps/{ref}/shots/{name:path}", dependencies=[Depends(require_key)])
async def apps_shot(ref: str, name: str, tenant: str = Depends(current_tenant)):
    from .appmaker import service as A
    try:
        f = await asyncio.to_thread(A.shot_file, tenant, ref, name)
    except (A.AppError, ValueError):
        raise HTTPException(404, "not found")
    return FileResponse(f, headers={"Cache-Control": "private, max-age=300"})


@app.get("/api/app-preview/{token}")
async def app_preview_root(token: str):
    return RedirectResponse(f"/api/app-preview/{token}/", status_code=307)


@app.get("/api/app-preview/{token}/{path:path}")
async def app_preview(token: str, path: str = ""):
    """Public, by its random token: the tap-through prototype of an app design (noindex, strict CSP, no network)."""
    from .appmaker import service as A
    try:
        data, ctype, headers = await asyncio.to_thread(A.preview_file, token, path)
    except A.AppError:
        raise HTTPException(404, "not found")
    return Response(content=data, media_type=ctype, headers={**headers, "Access-Control-Allow-Origin": "*"})


# ---------------------------------------------------------------- v0.118 Brand Sahayak (brand designer; final artwork on her tap)
def _brand(fn, *a, **k):
    from .brand import service as brand
    try:
        return fn(*a, **k)
    except brand.BrandError as e:
        raise HTTPException(400, str(e))


@app.get("/api/brand", dependencies=[Depends(require_key)])
async def brand_all(tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return await asyncio.to_thread(brand.everything, tenant)


@app.get("/api/brand/designs", dependencies=[Depends(require_key)])
async def brand_designs(status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return {"designs": await asyncio.to_thread(brand.designs, tenant, status, q)}


@app.post("/api/brand/designs", dependencies=[Depends(require_key)])
async def brand_make(body: dict, tenant: str = Depends(current_tenant)):
    """{brief, kind, sizes, festival, photo (file_id), layout, words {headline, sub, offer, cta, date, body}, ai_background, template}"""
    from .brand import service as brand
    words = body.get("words") if isinstance(body.get("words"), dict) else None
    return await asyncio.to_thread(_brand, brand.make, tenant, str(body.get("brief") or ""), str(body.get("kind") or ""),
                                   body.get("sizes"), str(body.get("festival") or ""), str(body.get("photo") or ""),
                                   str(body.get("layout") or ""), words, bool(body.get("ai_background")),
                                   str(body.get("template") or ""), str(body.get("conversation_id") or ""))


@app.get("/api/brand/designs/{ref}", dependencies=[Depends(require_key)])
async def brand_design(ref: str, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return await asyncio.to_thread(_brand, brand.get, tenant, ref)


@app.delete("/api/brand/designs/{ref}", dependencies=[Depends(require_key)])
async def brand_delete(ref: str, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return await asyncio.to_thread(_brand, brand.delete, tenant, ref)


@app.post("/api/brand/designs/{ref}/photo", dependencies=[Depends(require_key)])
async def brand_photo(ref: str, file: UploadFile = File(...), conversation_id: str = Form(""),
                      tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "The photo is bigger than 25 MB.")
    return await asyncio.to_thread(_brand, brand.set_photo, tenant, ref, "", data, conversation_id)


@app.post("/api/brand/designs/{ref}/{action}", dependencies=[Depends(require_key)])
async def brand_act(ref: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """revise {instruction} | edit {fields, layout} | resize {sizes, add} | approve {force} (sends the card) |
    decide {yes, hash, reason} (ONLY her tap on the card) | copy | template {on}"""
    from .brand import service as brand
    conv = str(body.get("conversation_id") or "")
    if action == "revise":
        return await asyncio.to_thread(_brand, brand.revise, tenant, ref, str(body.get("instruction") or ""), conv)
    if action == "edit":
        fields = body.get("fields") if isinstance(body.get("fields"), dict) else {}
        return await asyncio.to_thread(_brand, brand.edit, tenant, ref, fields, str(body.get("layout") or ""), conv)
    if action == "resize":
        return await asyncio.to_thread(_brand, brand.resize, tenant, ref, body.get("sizes"), body.get("add", True) is not False, conv)
    if action == "approve":
        return await asyncio.to_thread(_brand, brand.request_approval, tenant, ref, bool(body.get("force")), conv)
    if action == "decide":
        return await asyncio.to_thread(_brand, brand.decide, tenant, ref, bool(body.get("yes")), str(body.get("hash") or ""),
                                       str(body.get("reason") or ""), conv)
    if action == "copy":
        return await asyncio.to_thread(_brand, brand.copy_design, tenant, ref)
    if action == "template":
        return await asyncio.to_thread(_brand, brand.copy_design, tenant, ref, body.get("on", True) is not False)
    raise HTTPException(400, "action = revise | edit | resize | approve | decide | copy | template")


@app.get("/api/brand/files/{design_id}/{name}", dependencies=[Depends(require_key)])
def brand_file(design_id: str, name: str, download: bool = False, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    path, mime = _brand(brand.file_path, tenant, design_id, name)
    return FileResponse(path, media_type=mime, filename=name if download else None)


@app.get("/api/brand/kit", dependencies=[Depends(require_key)])
async def brand_kit(tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return await asyncio.to_thread(brand.kit, tenant)


@app.put("/api/brand/kit", dependencies=[Depends(require_key)])
async def brand_kit_save(body: dict, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    keys = ("name", "tagline", "colors", "contact", "font", "tone", "rule", "rules", "state", "language", "nudge", "nudge_days")
    return await asyncio.to_thread(_brand, brand.save_kit, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/brand/logo", dependencies=[Depends(require_key)])
async def brand_logo(file: UploadFile | None = File(None), file_id: str = Form(""), clean_bg: bool = Form(False),
                     tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    data = await file.read() if file is not None else None
    if data is not None and len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "The logo is bigger than 15 MB.")
    return await asyncio.to_thread(_brand, brand.set_logo, tenant, data, file_id, (file.filename if file else "logo.png"), clean_bg)


@app.get("/api/brand/logo", dependencies=[Depends(require_key)])
def brand_logo_get(tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    path, mime = _brand(brand.logo_file, tenant)
    return FileResponse(path, media_type=mime)


@app.get("/api/brand/festivals", dependencies=[Depends(require_key)])
async def brand_festivals(days: int = 60, tenant: str = Depends(current_tenant)):
    from .brand import service as brand
    return {"festivals": await asyncio.to_thread(brand.upcoming, tenant, max(1, min(370, days)))}


# ---------------------------------------------------------------- v0.101 Kalam Sahayak (content writer; publishing on her tap)
def _kalam(fn, *a, **k):
    from .kalam import service as kalam
    try:
        return fn(*a, **k)
    except kalam.KalamError as e:
        raise HTTPException(400, str(e))


@app.get("/api/kalam", dependencies=[Depends(require_key)])
def kalam_all(tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return kalam.everything(tenant)


@app.get("/api/kalam/pieces", dependencies=[Depends(require_key)])
def kalam_pieces(kind: str = "", status: str = "", q: str = "", tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return {"pieces": kalam.pieces(tenant, kind, status, q, 120)}


@app.post("/api/kalam/write", dependencies=[Depends(require_key)])
async def kalam_write(body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return await asyncio.to_thread(_kalam, kalam.write, tenant, str(body.get("brief") or ""), str(body.get("kind") or ""),
                                   str(body.get("title") or ""), str(body.get("keyword") or ""), body.get("words"),
                                   str(body.get("lang") or ""), str(body.get("audience") or ""), body.get("file_ids"),
                                   body.get("urls"), body.get("product") if isinstance(body.get("product"), dict) else None,
                                   str(body.get("experience") or ""), bool(body.get("paid")), str(body.get("conversation_id") or ""))


@app.get("/api/kalam/pieces/{pid}", dependencies=[Depends(require_key)])
def kalam_get(pid: str, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return _kalam(kalam.get, tenant, pid)


@app.put("/api/kalam/pieces/{pid}", dependencies=[Depends(require_key)])
async def kalam_edit(pid: str, body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return await asyncio.to_thread(_kalam, kalam.edit, tenant, pid, body.get("body"), body.get("title"),
                                   body.get("meta") if isinstance(body.get("meta"), dict) else None)


@app.delete("/api/kalam/pieces/{pid}", dependencies=[Depends(require_key)])
def kalam_delete(pid: str, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return _kalam(kalam.delete, tenant, pid)


@app.post("/api/kalam/pieces/{pid}/{action}", dependencies=[Depends(require_key)])
async def kalam_action(pid: str, action: str, body: dict, tenant: str = Depends(current_tenant)):
    """revise | check | publish | decide (her tap on the publish card) | repurpose | files | result | copy | unpage"""
    from .kalam import service as kalam
    conv = str(body.get("conversation_id") or "")
    if action == "revise":
        return await asyncio.to_thread(_kalam, kalam.revise, tenant, pid, str(body.get("instruction") or ""), conv)
    if action == "check":
        return await asyncio.to_thread(_kalam, kalam.check, tenant, pid, body.get("web", True) is not False, conv)
    if action == "publish":
        return await asyncio.to_thread(_kalam, kalam.publish_request, tenant, pid, str(body.get("dest") or ""),
                                       str(body.get("where") or ""), body.get("to"), str(body.get("status") or "publish"),
                                       str(body.get("when") or ""), bool(body.get("force")), conv)
    if action == "decide":
        return await asyncio.to_thread(_kalam, kalam.decide_publish, tenant, pid, bool(body.get("yes")),
                                       str(body.get("note") or ""), str(body.get("url") or ""), conv, str(body.get("hash") or ""))
    if action == "repurpose":
        return await asyncio.to_thread(_kalam, kalam.repurpose, tenant, pid, body.get("kinds"), conv)
    if action == "files":
        return await asyncio.to_thread(_kalam, kalam.make_files, tenant, pid, conv)
    if action == "result":
        return _kalam(kalam.result, tenant, pid, body.get("views"), body.get("clicks"), body.get("orders"),
                      str(body.get("url") or ""), str(body.get("note") or ""))
    if action == "copy":
        return _kalam(kalam.copy_piece, tenant, pid)
    if action == "unpage":
        return _kalam(kalam.unpublish_page, tenant, pid)
    raise HTTPException(404, "unknown action")


@app.get("/api/kalam/ideas", dependencies=[Depends(require_key)])
async def kalam_ideas(days: int = 45, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return await asyncio.to_thread(kalam.ideas, tenant, max(7, min(120, days)))


@app.put("/api/kalam/settings", dependencies=[Depends(require_key)])
def kalam_settings(body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    keys = ("enabled", "business", "about", "audience", "language", "address", "contact", "website", "cta", "tone", "do_words",
            "dont_words", "rules", "ai_note", "facts")
    return _kalam(kalam.save_settings, tenant, **{k: body[k] for k in keys if k in body})


@app.post("/api/kalam/facts", dependencies=[Depends(require_key)])
def kalam_fact(body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return _kalam(kalam.add_fact, tenant, str(body.get("fact") or ""), str(body.get("source") or ""))


@app.post("/api/kalam/voice", dependencies=[Depends(require_key)])
async def kalam_voice(body: dict, tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return await asyncio.to_thread(_kalam, kalam.learn_voice, tenant, str(body.get("text") or ""), body.get("file_ids"),
                                   body.get("urls"))


@app.put("/api/kalam/wordpress", dependencies=[Depends(require_key)])
async def kalam_wordpress(body: dict, tenant: str = Depends(current_tenant)):
    """Her own site: url + username + an Application Password (typed in the app only; sealed, never shown again)."""
    from .kalam import service as kalam
    return await asyncio.to_thread(_kalam, kalam.set_wordpress, tenant, str(body.get("url") or ""), str(body.get("user") or ""),
                                   str(body.get("app_password") or ""))


@app.delete("/api/kalam/wordpress", dependencies=[Depends(require_key)])
def kalam_wordpress_off(tenant: str = Depends(current_tenant)):
    from .kalam import service as kalam
    return kalam.forget_wordpress(tenant)


@app.get("/api/kalam/page/{token}")
def kalam_page(token: str):
    """A page she published with her Haan (public link)."""
    from .kalam import service as kalam
    html_text = kalam.page_by_token(token)
    if not html_text:
        raise HTTPException(404, "Page not found")
    return HTMLResponse(html_text, headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:",
                                            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})


@app.get("/api/agent/tasks", dependencies=[Depends(require_key)])
def agent_tasks(limit: int = 50, tenant: str = Depends(current_tenant)):
    """v0.78 Kaam ka hisaab: every task with its outcome, steps, failures, fixes used, and what was left."""
    from .agent import pakka
    return pakka.runs(tenant, limit)


@app.get("/api/agent/lessons", dependencies=[Depends(require_key)])
def agent_lessons(tenant: str = Depends(current_tenant)):
    """v0.78 Seekhe hue hal: failure -> what worked, learned from her own tasks."""
    from .agent import pakka
    return {"lessons": pakka.listing(tenant)}


@app.delete("/api/agent/lessons/{lid}", dependencies=[Depends(require_key)])
def agent_lesson_delete(lid: str, tenant: str = Depends(current_tenant)):
    from .agent import pakka
    if not pakka.forget(tenant, lid):
        raise HTTPException(404, "Not found")
    return {"ok": True}


@app.delete("/api/memory/{fact_id}", dependencies=[Depends(require_key)])
def delete_memory(fact_id: int, tenant: str = Depends(current_tenant)):
    with session() as s:
        f = s.get(MemoryFact, fact_id)
        if not f or f.tenant_id != tenant:
            raise HTTPException(404, "Not found")
        text = f.text
        s.delete(f)
    from . import yaad   # v0.603 BHOOL JAO HAR JAGAH: her tap removes the copies in every memory too
    yaad.forget_everywhere(tenant, text)
    return get_memory(tenant)


class ProfileIn(BaseModel):
    name: str | None = Field(None, max_length=120)
    city: str | None = Field(None, max_length=120)
    language: str | None = Field(None, max_length=32)
    timezone: str | None = Field(None, max_length=64)
    briefing_time: str | None = Field(None, pattern=r"^(\d{2}:\d{2}|off)$")
    conversation_id: str | None = None


def _profile_out(p: Profile) -> dict:
    return {"name": p.name, "city": p.city, "language": p.language, "timezone": p.timezone,
            "briefing_time": p.briefing_time}


@app.get("/api/profile", dependencies=[Depends(require_key)])
def get_profile_api(tenant: str = Depends(current_tenant)):
    return _profile_out(life.get_profile(tenant))


@app.put("/api/profile", dependencies=[Depends(require_key)])
def put_profile(body: ProfileIn, tenant: str = Depends(current_tenant)):
    life.get_profile(tenant)
    with session() as s:
        p = s.get(Profile, tenant)
        if body.name is not None:
            p.name = body.name.strip() or None
        if body.city is not None and body.city.strip() != (p.city or ""):
            p.city, p.lat, p.lon = body.city.strip() or None, None, None
        if body.language is not None:
            p.language = body.language
        if body.timezone:
            from zoneinfo import ZoneInfo
            try:
                ZoneInfo(body.timezone)
            except Exception:
                raise HTTPException(400, "Unknown time zone")
            p.timezone = body.timezone
        if body.briefing_time is not None:
            p.briefing_time = None if body.briefing_time == "off" else body.briefing_time
            p.last_briefing_date = None
            if body.conversation_id:
                p.briefing_conversation_id = body.conversation_id
        return _profile_out(p)


class ActionResult(BaseModel):
    ok: bool
    detail: str | None = Field(None, max_length=500)


@app.get("/api/device-actions/pending", dependencies=[Depends(require_key)])
def pending_actions(tenant: str = Depends(current_tenant)):
    """The phone asks this on start, so actions created while it was offline still run (within 15 minutes)."""
    with session() as s:
        rows = s.scalars(select(DeviceAction).where(DeviceAction.tenant_id == tenant,
                                                    DeviceAction.status == "pending").order_by(DeviceAction.created_at)).all()
        return {"actions": [{"id": a.id, "type": a.type, **a.payload} for a in rows]}


class BtResultIn(BaseModel):
    ok: bool
    result: dict = Field(default_factory=dict)
    error: str = ""


@app.post("/api/bt/requests/{rid}/result", dependencies=[Depends(require_key)])
def bt_result(rid: str, body: BtResultIn, tenant: str = Depends(current_tenant)):
    from .bt import service as bt
    try:
        return bt.report(tenant, rid, body.ok, body.result, body.error)
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.get("/api/bt/requests/{rid}", dependencies=[Depends(require_key)])
def bt_get(rid: str, tenant: str = Depends(current_tenant)):
    from .bt import service as bt
    try:
        return bt.get(tenant, rid)
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.post("/api/device-actions/{action_id}/result", dependencies=[Depends(require_key)])
def action_result(action_id: str, body: ActionResult, tenant: str = Depends(current_tenant)):
    with session() as s:
        a = s.get(DeviceAction, action_id)
        if not a or a.tenant_id != tenant:
            raise HTTPException(404, "Action not found")
        if a.status != "pending":
            return {"status": a.status}
        a.status = "done" if body.ok else "failed"
        a.result = body.detail
        conv, typ, status = a.conversation_id, a.type, a.status
    bus.publish(conv, "device_action_result", {"id": action_id, "type": typ, "status": status, "detail": body.detail})
    if status == "failed":
        from .events import notify
        notify(conv, f"This could not be done on the phone ({typ.replace('_', ' ')}): {body.detail or 'a permission or app problem'}. "
                     "Please check the permissions for Santosh in the phone settings.")
    return {"status": status}


# ---------------- Santosh Bazar (159 packs) ----------------
from .bazar import service as bazar  # noqa: E402
from .bazar.connectors.base import ToolError as BazarError  # noqa: E402


def _bz(fn, *a, **k):
    try:
        return fn(*a, **k)
    except BazarError as e:
        raise HTTPException(400, str(e))
    except PermissionError:
        raise HTTPException(403, "Not allowed for this shop")


def _maybe_tenant(request: Request) -> str | None:
    try:
        return current_tenant(request)
    except HTTPException:
        return None


# Home devices ("Ghar"): speaker / TV / AC on the phone + SmartThings, LG ThinQ, Home Connect
from .bazar.api import devices as bz_devices  # noqa: E402
app.include_router(bz_devices.router, dependencies=[Depends(require_key)])
from .bazar.api.composio import make_router as _composio_router  # noqa: E402  v0.276 apps via Composio

app.include_router(_composio_router(require_key, current_tenant))
from .engineering.api import make_router as _eng_router  # noqa: E402  v0.357 Engineering Desk (CAD Engineer)

app.include_router(_eng_router(require_key, current_tenant))
from .archdesk.api import make_router as _arch_router  # noqa: E402  v0.410 Architecture Desk (Principal Software Architect)

app.include_router(_arch_router(require_key, current_tenant))
app.include_router(bz_devices.public)


@app.get("/api/bazar/catalog", dependencies=[Depends(require_key)])
def bazar_catalog(tenant: str = Depends(current_tenant)):
    return _bz(bazar.catalog, tenant)


@app.get("/api/bazar/find", dependencies=[Depends(require_key)])
def bazar_find_api(q: str = "", category: str = "", tenant: str = Depends(current_tenant)):
    return _bz(bazar.find, tenant, q, category)


class BazarDecision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    proof: dict | None = None      # v0.97 fingerprint signature from her phone (approvekey)


def _fingerprint(tenant: str, kind: str, target: str, proof: dict | None) -> None:
    """v0.97 A money card needs HER phone's fingerprint signature once a phone is set up (428 = ask the phone)."""
    from . import approvekey as ak
    try:
        if ak.needed(tenant, kind, target):
            ak.verify(tenant, kind, target, proof)
    except ak.ApproveError as e:
        code = str(e)
        if code in ("fingerprint_needed", "fingerprint_invalid"):
            raise HTTPException(428, code)
        raise HTTPException(400, code)


class FormAnswer(BaseModel):
    values: dict = Field(default_factory=dict)


@app.get("/api/forms/{form_id}", dependencies=[Depends(require_key)])
def form_get(form_id: str, tenant: str = Depends(current_tenant)):
    from . import askform
    try:
        return askform.get(tenant, form_id)
    except askform.FormError as e:
        raise HTTPException(404, str(e))


def _form_reply(tenant: str, conv: str, agent_text: str, shown: str, background: BackgroundTasks) -> str:
    """Her answers continue the job: inside a live call they go to the call; otherwise as her next chat message."""
    if not conv:
        return "none"
    try:
        from .voice import inject
        if inject(conv, agent_text):
            bus.publish(conv, "message", {"role": "user", "text": shown, "source": "form"})
            return "call"
    except Exception:
        log.exception("form -> call failed")
    bus.publish(conv, "message", {"role": "user", "text": shown, "source": "form"})
    from . import turn_inbox   # v0.666 her form answers continue a waiting job: never lost to a restart
    ti_id = turn_inbox.accept(tenant, conv, shown, False, agent_text or "", "")
    background.add_task(turn_inbox.run_owned, ti_id, conv, shown, tenant, False, context=agent_text or "")
    return "chat"


@app.post("/api/forms/{form_id}/answer", dependencies=[Depends(require_key)])
def form_answer(form_id: str, body: FormAnswer, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    from . import askform
    try:
        v, agent_text, shown = askform.answer(tenant, form_id, body.values)
    except askform.FormError as e:
        raise HTTPException(400, str(e))
    with session() as s:
        from .askform import AskForm
        conv = s.get(AskForm, form_id).conversation_id
    return {**v, "went_to": _form_reply(tenant, conv, agent_text, shown, background)}


@app.post("/api/forms/{form_id}/cancel", dependencies=[Depends(require_key)])
def form_cancel(form_id: str, background: BackgroundTasks, tenant: str = Depends(current_tenant)):
    from . import askform
    try:
        v, agent_text = askform.cancel(tenant, form_id)
    except askform.FormError as e:
        raise HTTPException(404, str(e))
    if agent_text:
        with session() as s:
            from .askform import AskForm
            conv = s.get(AskForm, form_id).conversation_id
        _form_reply(tenant, conv, agent_text, "Form band kiya", background)
    return v


class ApproveKeyAdd(BaseModel):
    device_id: str = Field(min_length=4, max_length=80)
    public_key: str = Field(min_length=40, max_length=2000)
    label: str = Field(default="", max_length=120)
    strongbox: bool = False
    proof: dict | None = None


class ApproveProof(BaseModel):
    proof: dict | None = None


class ApproveChallengeReq(BaseModel):
    kind: str = Field(pattern="^(bazar|studio|remove|endorse)$")
    target: str = Field(min_length=1, max_length=2200)


@app.get("/api/approvekey", dependencies=[Depends(require_key)])
def approvekey_get(tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    return ak.devices(tenant)


@app.post("/api/approvekey/devices", dependencies=[Depends(require_key)])
def approvekey_add(body: ApproveKeyAdd, tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    try:
        return ak.register(tenant, body.device_id, body.public_key, body.label, body.strongbox, body.proof)
    except ak.ApproveError as e:
        raise HTTPException(400, str(e))


@app.post("/api/approvekey/devices/{device_id}/remove", dependencies=[Depends(require_key)])
def approvekey_remove(device_id: str, body: ApproveProof, tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    try:
        return ak.remove(tenant, device_id, body.proof)
    except ak.ApproveError as e:
        raise HTTPException(400, str(e))


@app.post("/api/approvekey/devices/{device_id}/cancel", dependencies=[Depends(require_key)])
def approvekey_cancel(device_id: str, tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    try:
        return ak.cancel(tenant, device_id)
    except ak.ApproveError as e:
        raise HTTPException(400, str(e))


@app.post("/api/approvekey/challenge", dependencies=[Depends(require_key)])
def approvekey_challenge(body: ApproveChallengeReq, tenant: str = Depends(current_tenant)):
    from . import approvekey as ak
    try:
        return ak.challenge(tenant, body.kind, body.target)
    except ak.ApproveError as e:
        raise HTTPException(400, str(e))


@app.get("/api/bazar/approvals/pending", dependencies=[Depends(require_key)])
def bazar_pending(tenant: str = Depends(current_tenant)):
    return {"approvals": bazar.pending_approvals(tenant)}


@app.post("/api/bazar/approvals/{approval_id}", dependencies=[Depends(require_key)])
async def bazar_decide(approval_id: str, body: BazarDecision, tenant: str = Depends(current_tenant)):
    if body.decision == "approve":
        await asyncio.to_thread(_fingerprint, tenant, "bazar", approval_id, body.proof)
    try:
        return await asyncio.to_thread(bazar.decide, tenant, approval_id, body.decision)
    except BazarError as e:
        raise HTTPException(400, str(e))


class UpiResultBody(BaseModel):
    txn_ref: str = Field(max_length=40)
    response: str = Field(default="", max_length=2000)   # the UPI app's own answer (NPCI response string)
    result: str = Field(default="", max_length=20)       # ok | cancelled | none (what Android reported)
    package: str = Field(default="", max_length=120)
    answer: str = Field(default="", max_length=8)        # her word on the card: done | not


@app.post("/api/bazar/upi/result", dependencies=[Depends(require_key)])
async def bazar_upi_result(body: UpiResultBody, tenant: str = Depends(current_tenant)):
    """v0.109 After 'Paisa bhejo': the phone reports what the UPI app said, or she taps Ho gaya / Nahi hua."""
    from .bazar import upiresult
    return await asyncio.to_thread(_bz, upiresult.record, tenant, body.txn_ref, body.response, body.result,
                                   body.package, body.answer)


@app.get("/api/bazar/activity", dependencies=[Depends(require_key)])
def bazar_activity_api(tenant: str = Depends(current_tenant)):
    return bazar.activity(tenant)


@app.get("/api/bazar/files", dependencies=[Depends(require_key)])
def bazar_files(tenant: str = Depends(current_tenant)):
    """PDFs Santosh made for this user (GST invoices, quotations, salary slips, rent receipts, resumes)."""
    return {"files": bazar.list_docs(tenant)}


@app.get("/api/bazar/files/{doc_id}", dependencies=[Depends(require_key)])
def bazar_file(doc_id: str, tenant: str = Depends(current_tenant)):
    hit = bazar.get_doc(tenant, doc_id)
    if hit is None:
        raise HTTPException(404, "Not found")
    return FileResponse(hit[0], media_type="application/pdf", filename=hit[1])


@app.get("/api/bazar/files/{doc_id}/link", dependencies=[Depends(require_key)])
def bazar_file_fresh_link(doc_id: str, tenant: str = Depends(current_tenant)):
    """A fresh signed link for the chat card (the one in the card expires after a day)."""
    if bazar.get_doc(tenant, doc_id) is None:
        raise HTTPException(404, "Not found")
    return {"url": bazar.file_link(doc_id)}


@app.get("/api/bazar/files/{doc_id}/dl")
def bazar_file_link(doc_id: str, exp: int = 0, sig: str = ""):
    """Signed, expiring link from the chat card (opened in the phone's PDF viewer, which sends no auth header)."""
    if not bazar.check_file_sig(doc_id, exp, sig):
        raise HTTPException(403, "This link expired. Open the file from the Santosh app.")
    hit = bazar.get_doc(None, doc_id)
    if hit is None:
        raise HTTPException(404, "File no longer available")
    return FileResponse(hit[0], media_type="application/pdf", filename=hit[1])


class BazarSettingsIn(BaseModel):
    cap_per_order_rupees: float | None = Field(None, ge=0, le=5000)
    cap_per_day_rupees: float | None = Field(None, ge=0, le=20000)
    pincode: str | None = Field(None, max_length=10)
    address: str | None = Field(None, max_length=400)
    language: str | None = None
    phone: str | None = Field(None, max_length=16)


@app.get("/api/bazar/settings", dependencies=[Depends(require_key)])
def bazar_settings_get(tenant: str = Depends(current_tenant)):
    return bazar.get_user_settings(tenant)


@app.put("/api/bazar/settings", dependencies=[Depends(require_key)])
def bazar_settings_put(body: BazarSettingsIn, tenant: str = Depends(current_tenant)):
    return _bz(bazar.set_user_settings, tenant, body.model_dump(exclude_none=True))


class BazarContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    upi_id: str = ""
    phone: str = ""
    relation: str = ""


@app.get("/api/bazar/contacts", dependencies=[Depends(require_key)])
def bazar_contacts(tenant: str = Depends(current_tenant)):
    return {"contacts": bazar.list_contacts(tenant)}


@app.post("/api/bazar/contacts", dependencies=[Depends(require_key)])
def bazar_contact_add(body: BazarContactIn, tenant: str = Depends(current_tenant)):
    return _bz(bazar.add_contact, tenant, body.name, body.upi_id, body.phone, body.relation)


# ---------------- Hoola Reels: share a reel to Hoola, turn it into something useful ----------------
class ReelLookIn(BaseModel):
    text: str


class ReelNoteIn(BaseModel):
    note: str = ""


class ReelRemindIn(BaseModel):
    when: str                      # local time, e.g. 2026-10-21T19:00
    text: str = ""


class ReelShopIn(BaseModel):
    items: list[str] = []


def _reel(fn, *a):
    from .reels import service as rs
    try:
        return fn(*a)
    except rs.ReelError as e:
        raise HTTPException(400, str(e))


@app.post("/api/reels/look", dependencies=[Depends(require_key)])
async def reel_look(body: ReelLookIn, tenant: str = Depends(current_tenant)):
    """A reel link shared from Instagram / YouTube / Facebook / Snapchat / Moj / Josh / ShareChat."""
    from .reels import service as rs
    return await asyncio.to_thread(_reel, rs.look_link, tenant, body.text[:4000])


@app.post("/api/reels/look_file", dependencies=[Depends(require_key)])
async def reel_look_file(file: UploadFile = File(...), text: str = Form(""), tenant: str = Depends(current_tenant)):
    """The owner's own screen recording / screenshot of a reel (for apps that don't share the video)."""
    from .reels import service as rs
    data = await file.read(rs.MAX_FILE + 1)
    return await asyncio.to_thread(_reel, rs.look_file, tenant, file.filename or "reel.mp4", file.content_type or "",
                                   data, text[:4000])


@app.get("/api/reels", dependencies=[Depends(require_key)])
def reels_saved(q: str = "", tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    return {"reels": rs.saved(tenant, q)}


# ---------------- Hoola Employee (v0.58): role, team, trust per duty, audit, pause, daily report ----------------
class EmployeeIn(BaseModel):
    enabled: bool | None = None
    preset: str | None = None
    upi_id: str | None = None
    upi_name: str | None = None
    slot_minutes: int | None = None
    inbox_on: bool | None = None
    role: str | None = None
    duties: list[str] | None = None
    business_name: str | None = None
    business_kind: str | None = None
    about: str | None = None
    hours: dict | None = None
    after_hours: str | None = None
    report_time: str | None = None
    rules: str | None = None
    reply_to_staff: bool | None = None


class EmployeePauseIn(BaseModel):
    paused: bool = True


class MemberIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    role: str | None = None
    duties: list[str] | None = None
    active: bool | None = None


class TrustIn(BaseModel):
    level: str | None = None
    per_day: int | None = None


class AskDecisionIn(BaseModel):
    approve: bool


class WrongIn(BaseModel):
    note: str = ""


class JobSheetIn(BaseModel):
    text: str = ""


def _emp(fn, *a, **kw):
    from .employee import service as emp
    try:
        return fn(*a, **kw)
    except emp.EmployeeError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------- v0.358 Enterprise Systems & ERP (ten jobs)
def _ent(fn, *a, **kw):
    from .enterprise import service as ent
    try:
        return fn(*a, **kw)
    except ent.EnterpriseError as e:
        raise HTTPException(400, str(e))


@app.get("/api/enterprise", dependencies=[Depends(require_key)])
def enterprise_get(tenant: str = Depends(current_tenant)):
    """All ten jobs in one call: what exists for her, and what every job is / where it stops."""
    from .enterprise import service as ent
    return _ent(ent.overview, tenant)


@app.get("/api/enterprise/{role}", dependencies=[Depends(require_key)])
def enterprise_role(role: str, tenant: str = Depends(current_tenant)):
    from .enterprise import service as ent
    return _ent(lambda: {"day": ent.day(tenant, role), "settings": ent.settings(tenant, role),
                         "systems": ent.systems(tenant, role), "projects": ent.projects(tenant, role),
                         "papers": ent.artifacts(tenant, role), "items": ent.items(tenant, role)})


@app.put("/api/enterprise/{role}/settings", dependencies=[Depends(require_key)])
def enterprise_settings(role: str, body: dict, tenant: str = Depends(current_tenant)):
    from .enterprise import service as ent
    return _ent(ent.save_settings, tenant, role, **{k: v for k, v in (body or {}).items()
                                                    if k in ("company", "env_default", "rules")})


@app.post("/api/enterprise/{role}/connect", dependencies=[Depends(require_key)])
def enterprise_connect(role: str, body: dict, tenant: str = Depends(current_tenant)):
    """She links her OWN system from the app; the credential stays with Composio / the system's own OAuth."""
    from .enterprise import service as ent
    b = body or {}
    return _ent(ent.connect, tenant, role, str(b.get("system") or ""), str(b.get("env") or ""),
                str(b.get("account") or ""), str(b.get("note") or ""))


@app.delete("/api/enterprise/{role}/connect/{system}", dependencies=[Depends(require_key)])
def enterprise_disconnect(role: str, system: str, tenant: str = Depends(current_tenant)):
    from .enterprise import service as ent
    return _ent(ent.disconnect, tenant, role, system)


@app.get("/api/enterprise/{role}/paper/{ref}", dependencies=[Depends(require_key)])
def enterprise_paper(role: str, ref: str, tenant: str = Depends(current_tenant)):
    from .enterprise import service as ent
    return _ent(ent.artifact, tenant, role, ref)


def _entrun(fn, *a, **kw):
    from .enterprise import run as entrun
    try:
        return fn(*a, **kw)
    except entrun.RunError as e:
        raise HTTPException(400, str(e))


@app.get("/api/enterprise/{role}/endpoint", dependencies=[Depends(require_key)])
def enterprise_endpoints(role: str, tenant: str = Depends(current_tenant)):
    """Her own systems for this job: address, which environment, and the key MASKED. The key itself is sealed
    and is never returned by any route - not here, not anywhere."""
    from .enterprise import run as entrun
    return _entrun(lambda: {"systems": entrun.endpoints(tenant, role),
                            "jod_sakte_hain": _ent_systems(role)})


def _ent_systems(role: str):
    # v0.399 FIX: rules.systems_for already returns the full dict per system ({key, label, how, note}); the
    # first cut looped over it as if it were a list of NAMES and called SYSTEMS.get(<dict>), which raises
    # TypeError: unhashable type - so the console Systems page 500'd the moment it was opened. The test that
    # shipped with it only asserted the ROUTE EXISTED, never called it. A route that exists is not a route
    # that works; test_v0396_connect now calls this for five roles and checks the shape.
    from .enterprise import rules as entrules
    return [{"system": s.get("key", ""), "label": s.get("label") or s.get("key", ""),
             "how": s.get("how") or "own", "note": s.get("note") or ""}
            for s in entrules.systems_for(role)]


@app.post("/api/enterprise/{role}/endpoint", dependencies=[Depends(require_key)])
def enterprise_endpoint_set(role: str, body: dict, tenant: str = Depends(current_tenant)):
    """THE ONE DOOR for an enterprise credential.

    It exists only here, on a route the APP calls, because the chat refuses to take a key and should: a secret
    pasted into a conversation is in the history, in the model's context and in any export of either. What
    arrives here is sealed immediately (`bazar.security.vault`), stored encrypted, and read back out only
    inside the HTTP call that uses it. Nothing returns it - this route answers with the MASKED form.
    """
    from .enterprise import run as entrun
    b = body or {}
    return _entrun(entrun.set_endpoint, tenant, role, str(b.get("system") or ""),
                   str(b.get("base_url") or ""), str(b.get("auth") or ""),
                   str(b.get("auth_kind") or "bearer"), str(b.get("env") or "test"),
                   str(b.get("header_name") or ""), str(b.get("note") or ""))


@app.post("/api/enterprise/{role}/endpoint/{system}/verify", dependencies=[Depends(require_key)])
def enterprise_endpoint_verify(role: str, system: str, tenant: str = Depends(current_tenant)):
    """Ask her real system whether it works. READ-ONLY - it writes nothing.

    This is the first call in the whole suite that ever reaches a customer tenant, so it reports what the
    endpoint actually ANSWERED rather than a green tick: whether the address replied, whether the credential
    got past authentication (401 and 403 told apart), and whether the things a WRITE will need later - a CSRF
    token, an ETag, a check-out - can be had at all."""
    from .enterprise import run as entrun
    return _entrun(entrun.verify, tenant, role, system)


@app.delete("/api/enterprise/{role}/endpoint/{system}", dependencies=[Depends(require_key)])
def enterprise_endpoint_forget(role: str, system: str, tenant: str = Depends(current_tenant)):
    """Forget the address and the sealed key. Her runs and papers are untouched."""
    from .enterprise import run as entrun
    return _entrun(entrun.forget_endpoint, tenant, role, system)


@app.get("/api/enterprise/{role}/runs", dependencies=[Depends(require_key)])
def enterprise_runs(role: str, tenant: str = Depends(current_tenant)):
    from .enterprise import run as entrun
    return _entrun(lambda: {"runs": entrun.runs(tenant, role)})


@app.get("/api/enterprise/{role}/run/{run_id}", dependencies=[Depends(require_key)])
def enterprise_run_status(role: str, run_id: str, tenant: str = Depends(current_tenant)):
    """One write run: how far it got, what failed, and which rows nobody can be sure about."""
    from .enterprise import run as entrun
    return _entrun(entrun.status, tenant, run_id)


@app.post("/api/enterprise/{role}/run/{run_id}/resolve", dependencies=[Depends(require_key)])
def enterprise_run_resolve(role: str, run_id: str, body: dict,
                           tenant: str = Depends(current_tenant)):
    """Her answer on a row whose reply never arrived: did it land in the system or not?

    Hoola refuses to decide this itself - a retry can post the same record twice - so the row waits here
    until a person has looked. landed=true closes the row WITHOUT sending anything; landed=false puts it
    back in the queue for exactly one more attempt."""
    from .enterprise import run as entrun
    if "landed" not in body:
        raise HTTPException(400, "landed true/false is required.")
    return _entrun(entrun.resolve, tenant, run_id, int(body.get("n") or 0), bool(body.get("landed")))


@app.post("/api/enterprise/{role}/deploy/validate", dependencies=[Depends(require_key)])
def enterprise_deploy_validate(role: str, body: dict, tenant: str = Depends(current_tenant)):
    """Salesforce config deploy, step 1 of 3: the dry run. Components are checked and the tests run in her
    org, and nothing is committed. This is the only documented way to change what Tooling API refuses to
    touch in a live org (CustomField, CustomObject, Apex) or cannot write at all (Profile, PermissionSet)."""
    from .enterprise import run as entrun
    comps = body.get("components")
    if not isinstance(comps, list) or not comps:
        raise HTTPException(400, "components are needed: [{type, name, body}].")
    return _entrun(entrun.deploy_validate, tenant, role, comps, str(body.get("test_level") or ""))


@app.get("/api/enterprise/{role}/deploy/{deploy_id}", dependencies=[Depends(require_key)])
def enterprise_deploy_status(role: str, deploy_id: str, tenant: str = Depends(current_tenant)):
    """Step 2: poll. A deploy with tests takes minutes, so the id is kept and polled - never resubmitted."""
    from .enterprise import run as entrun
    return _entrun(entrun.deploy_status, tenant, role, deploy_id)


@app.post("/api/enterprise/{role}/deploy/{deploy_id}/go", dependencies=[Depends(require_key)])
def enterprise_deploy_go(role: str, deploy_id: str, body: dict | None = None,
                         tenant: str = Depends(current_tenant)):
    """Step 3: HER TAP. Quick-deploys the validation she just saw, without re-running its tests (valid 10
    days). A production org needs the word 'production' as well, like every other live write."""
    from .enterprise import run as entrun
    b = body or {}
    return _entrun(entrun.deploy_go, tenant, role, deploy_id, "owner", str(b.get("confirm_env") or ""))


@app.get("/api/employee", dependencies=[Depends(require_key)])
def employee_get(tenant: str = Depends(current_tenant)):
    """Everything the Employee screen needs in one call."""
    from .employee import service as emp
    from .employee import inbox as biz_inbox
    from .employee.roles import DUTIES, LEVEL_LABEL, LEVELS, PRESETS, ROLES
    p = emp.profile(tenant)
    return {"profile": p, "status": emp.status(tenant), "trust": emp.trust(tenant) if p else [], "team": emp.team(tenant),
            "asks": emp.asks(tenant) if p else [],
            "roles": [{"id": k, "label": v["label"], "say": v["say"], "duties": v["duties"]} for k, v in ROLES.items()],
            "duties": [{"id": k, "label": v["label"], "say": v["say"]} for k, v in DUTIES.items()],
            "levels": [{"id": x, "label": LEVEL_LABEL[x]} for x in LEVELS],
            "presets": [{"id": k, "label": v["label"], "role": v["role"], "about_hint": v["about_hint"]} for k, v in PRESETS.items()],
            "inbox": biz_inbox.summary(tenant) if p else None}


@app.put("/api/employee", dependencies=[Depends(require_key)])
def employee_put(body: EmployeeIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.setup, tenant, **body.model_dump())


@app.post("/api/employee/pause", dependencies=[Depends(require_key)])
def employee_pause(body: EmployeePauseIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.set_pause, tenant, body.paused, "owner")


@app.get("/api/employee/team", dependencies=[Depends(require_key)])
def employee_team(tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return {"team": emp.team(tenant)}


@app.post("/api/employee/team", dependencies=[Depends(require_key)])
def employee_team_add(body: MemberIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.add_member, tenant, body.name or "", body.phone or "", body.address or "", body.role or "staff",
                body.duties or [])


@app.patch("/api/employee/team/{member_id}", dependencies=[Depends(require_key)])
def employee_team_edit(member_id: str, body: MemberIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.update_member, tenant, member_id, **body.model_dump())


@app.delete("/api/employee/team/{member_id}", dependencies=[Depends(require_key)])
def employee_team_remove(member_id: str, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    _emp(emp.remove_member, tenant, member_id)
    return {"ok": True}


@app.put("/api/employee/trust/{duty}", dependencies=[Depends(require_key)])
def employee_trust(duty: str, body: TrustIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.set_trust, tenant, duty, body.level, body.per_day)


@app.get("/api/employee/asks", dependencies=[Depends(require_key)])
def employee_asks(status: str = "pending", tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return {"asks": emp.asks(tenant, status)}


@app.post("/api/employee/asks/{ask_id}", dependencies=[Depends(require_key)])
async def employee_decide(ask_id: str, body: AskDecisionIn, tenant: str = Depends(current_tenant)):
    """The owner's Haan / Mana on something Hoola wanted to do on its own."""
    from .employee import service as emp
    try:
        return await emp.decide(tenant, ask_id, body.approve)
    except emp.EmployeeError as e:
        raise HTTPException(400, str(e))


@app.get("/api/employee/audit", dependencies=[Depends(require_key)])
def employee_audit(limit: int = 100, duty: str = "", day: str = "", tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return {"entries": _emp(emp.audit, tenant, limit, duty, day)}


@app.post("/api/employee/audit/{entry_id}/wrong", dependencies=[Depends(require_key)])
def employee_wrong(entry_id: str, body: WrongIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.mark_wrong, tenant, entry_id, body.note)


@app.get("/api/employee/report", dependencies=[Depends(require_key)])
def employee_report(day: str = "", tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    try:
        return emp.report(tenant, day)
    except ValueError:
        raise HTTPException(400, "day: YYYY-MM-DD")


@app.get("/api/employee/job_sheet", dependencies=[Depends(require_key)])
def employee_sheet(tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return emp.job_sheet(tenant)


@app.put("/api/employee/job_sheet", dependencies=[Depends(require_key)])
def employee_sheet_put(body: JobSheetIn, tenant: str = Depends(current_tenant)):
    from .employee import service as emp
    return _emp(emp.set_job_sheet, tenant, body.text)


@app.get("/api/employee/tasks", dependencies=[Depends(require_key)])
def employee_tasks(tenant: str = Depends(current_tenant)):
    from .employee import network
    return {"tasks": network.tasks(tenant)}


# ---------------- Hoola Employee v0.59: business WhatsApp inbox, appointments, dues, presets ----------------
class EmployeeSendIn(BaseModel):
    text: str = ""


class EmployeeHumanIn(BaseModel):
    human: bool = True
    note: str | None = None


class ChannelIn(BaseModel):
    phone_number_id: str
    display_number: str = ""
    token: str = ""


class ApptIn(BaseModel):
    start: str
    name: str = ""
    phone: str = ""
    note: str = ""


class ApptStatusIn(BaseModel):
    status: str


class DueIn(BaseModel):
    name: str = ""
    phone: str
    amount: float
    due_date: str = ""
    note: str = ""


class DueEditIn(BaseModel):
    status: str | None = None
    promised_on: str | None = None


def _inb(fn, *a, **kw):
    from .employee import inbox
    try:
        return fn(*a, **kw)
    except inbox.InboxError as e:
        raise HTTPException(400, str(e))


@app.get("/api/employee/presets", dependencies=[Depends(require_key)])
def employee_presets():
    from .employee.roles import PRESETS
    return {"presets": [{"id": k, "label": v["label"], "role": v["role"], "about_hint": v["about_hint"], "rules": v["rules"]}
                        for k, v in PRESETS.items()]}


@app.get("/api/employee/inbox", dependencies=[Depends(require_key)])
def employee_inbox(q: str = "", tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return {"contacts": inbox.contacts(tenant, q), "summary": inbox.summary(tenant)}


@app.get("/api/employee/inbox/{contact_id}", dependencies=[Depends(require_key)])
def employee_inbox_thread(contact_id: str, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.thread, tenant, contact_id)


@app.post("/api/employee/inbox/{contact_id}/send", dependencies=[Depends(require_key)])
async def employee_inbox_send(contact_id: str, body: EmployeeSendIn, tenant: str = Depends(current_tenant)):
    """The owner's own reply to a customer (she typed and tapped send: that is the confirmation)."""
    from .employee import inbox
    try:
        return await inbox.send(tenant, contact_id, body.text, by="owner")
    except inbox.InboxError as e:
        raise HTTPException(400, str(e))


@app.post("/api/employee/inbox/{contact_id}/human", dependencies=[Depends(require_key)])
def employee_inbox_human(contact_id: str, body: EmployeeHumanIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.set_human, tenant, contact_id, body.human, body.note)


@app.post("/api/employee/inbox/{contact_id}/answer", dependencies=[Depends(require_key)])
async def employee_inbox_answer(contact_id: str, tenant: str = Depends(current_tenant)):
    """Ask Hoola to answer this customer now (after the owner gave the chat back)."""
    from .employee import inbox
    _inb(inbox.thread, tenant, contact_id, 1, mark_read=False)      # 400 when it is not this owner's customer
    sent = await inbox.answer(tenant, contact_id)
    return {"sent": sent}


@app.get("/api/employee/channels", dependencies=[Depends(require_key)])
def employee_channels(tenant: str = Depends(current_tenant)):
    from .employee import inbox
    st = get_settings()
    return {"channels": inbox.channels(tenant), "webhook": "/webhooks/whatsapp", "server_number_owner": st.wa_inbox_tenant == tenant}


@app.put("/api/employee/channels", dependencies=[Depends(require_key)])
def employee_channel_set(body: ChannelIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.set_channel, tenant, body.phone_number_id, body.display_number, body.token)


@app.delete("/api/employee/channels/{phone_number_id}", dependencies=[Depends(require_key)])
def employee_channel_remove(phone_number_id: str, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    _inb(inbox.remove_channel, tenant, phone_number_id)
    return {"ok": True}


@app.get("/api/employee/slots", dependencies=[Depends(require_key)])
def employee_slots(date: str = "", days: int = 3, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    try:
        return {"free": inbox.free_slots(tenant, date, days)}
    except ValueError:
        raise HTTPException(400, "date: YYYY-MM-DD")


@app.get("/api/employee/appointments", dependencies=[Depends(require_key)])
def employee_appts(day: str = "", tenant: str = Depends(current_tenant)):
    from .employee import inbox
    try:
        return {"appointments": inbox.appointments(tenant, day)}
    except ValueError:
        raise HTTPException(400, "day: YYYY-MM-DD")


@app.post("/api/employee/appointments", dependencies=[Depends(require_key)])
def employee_appt_add(body: ApptIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.book, tenant, body.start, body.name, body.phone, "", body.note, "owner")


@app.patch("/api/employee/appointments/{appt_id}", dependencies=[Depends(require_key)])
def employee_appt_edit(appt_id: str, body: ApptStatusIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.set_appointment, tenant, appt_id, body.status)


@app.get("/api/employee/dues", dependencies=[Depends(require_key)])
def employee_dues(status: str = "", tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return {"dues": inbox.dues(tenant, status), "summary": inbox.dues_summary(tenant)}


@app.post("/api/employee/dues", dependencies=[Depends(require_key)])
def employee_due_add(body: DueIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.add_due, tenant, body.name, body.phone, body.amount, body.due_date, body.note)


@app.patch("/api/employee/dues/{due_id}", dependencies=[Depends(require_key)])
def employee_due_edit(due_id: str, body: DueEditIn, tenant: str = Depends(current_tenant)):
    from .employee import inbox
    return _inb(inbox.set_due, tenant, due_id, body.status, body.promised_on)


@app.post("/api/employee/dues/import", dependencies=[Depends(require_key)])
async def employee_dues_import(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    from .employee import inbox
    data = await file.read(2_000_001)
    if len(data) > 2_000_000:
        raise HTTPException(413, "CSV 2 MB tak.")
    return _inb(inbox.import_dues, tenant, data)


# reel scroll analysis (Usage Access numbers + the owner's own history download)
class ScrollSyncIn(BaseModel):
    days: list[dict] = []


class ScrollBudgetIn(BaseModel):
    minutes: int = 0


@app.post("/api/reels/scroll/sync", dependencies=[Depends(require_key)])
def scroll_sync(body: ScrollSyncIn, tenant: str = Depends(current_tenant)):
    from .reels import scroll
    return scroll.sync(tenant, body.days)


@app.get("/api/reels/scroll/report", dependencies=[Depends(require_key)])
def scroll_report(days: int = 7, tenant: str = Depends(current_tenant)):
    from .reels import scroll
    return scroll.report(tenant, days)


@app.post("/api/reels/scroll/budget", dependencies=[Depends(require_key)])
def scroll_budget(body: ScrollBudgetIn, tenant: str = Depends(current_tenant)):
    from .reels import scroll
    return scroll.set_budget(tenant, body.minutes)


@app.post("/api/reels/scroll/import", dependencies=[Depends(require_key)])
async def scroll_import(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """The owner's own Instagram 'Download your information' / Google Takeout YouTube history (zip, json or html)."""
    from .reels import scroll
    data = await file.read(scroll.MAX_IMPORT + 1)
    try:
        return await asyncio.to_thread(scroll.import_history, tenant, file.filename or "history", data)
    except scroll.ScrollError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/reels/scroll", dependencies=[Depends(require_key)])
def scroll_forget(tenant: str = Depends(current_tenant)):
    from .reels import scroll
    return scroll.forget(tenant)


@app.get("/api/reels/{reel_id}", dependencies=[Depends(require_key)])
def reel_get(reel_id: str, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    try:
        return rs.get(tenant, reel_id)
    except rs.ReelError as e:
        raise HTTPException(404, str(e))


@app.post("/api/reels/{reel_id}/save", dependencies=[Depends(require_key)])
def reel_save(reel_id: str, body: ReelNoteIn, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    return _reel(rs.save, tenant, reel_id, body.note)


@app.delete("/api/reels/{reel_id}/save", dependencies=[Depends(require_key)])
def reel_unsave(reel_id: str, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    return rs.unsave(tenant, reel_id)


@app.post("/api/reels/{reel_id}/remind", dependencies=[Depends(require_key)])
async def reel_remind(reel_id: str, body: ReelRemindIn, tenant: str = Depends(current_tenant)):
    from .agent.life_tools import create_reminder
    from .agent.tools import Ctx, ToolError
    from .reels import service as rs
    v = await asyncio.to_thread(_reel, rs.get, tenant, reel_id)
    text = (body.text.strip() or f"Reel: {v['title'] or 'jo save ki thi'}")[:400]
    if v["url"] and v["url"] not in text:
        text = f"{text} ({v['url']})"
    try:
        r = await create_reminder(Ctx(tenant, await asyncio.to_thread(_tv_conv, tenant)), text, body.when)
    except ToolError as e:
        raise HTTPException(400, str(e))
    return {"reminder": r, "say": f"Theek hai, {r.get('when') or body.when} ko yaad dila dunga."}


@app.post("/api/reels/{reel_id}/shop", dependencies=[Depends(require_key)])
async def reel_shop(reel_id: str, body: ReelShopIn, tenant: str = Depends(current_tenant)):
    """Products / ingredients of the reel -> the shopping list (+ plain search links to compare and buy)."""
    from .agent.life_tools import list_add
    from .agent.tools import Ctx
    from .reels import service as rs
    items = await asyncio.to_thread(_reel, rs.shop_items, tenant, reel_id, body.items or None)
    if not items:
        raise HTTPException(400, "No buyable item was found in this reel.")
    r = await list_add(Ctx(tenant, await asyncio.to_thread(_tv_conv, tenant)), "shopping", items)
    return {"list": r["list"], "added": r["added"], "items": r["items"],
            "say": f"{len(r['added'])} cheezein shopping list mein daal di." if r["added"] else "Yeh sab pehle se list mein hai."}


@app.get("/api/reels/{reel_id}/share", dependencies=[Depends(require_key)])
def reel_share(reel_id: str, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    return _reel(rs.share_text, tenant, reel_id)


@app.post("/api/reels/{reel_id}/check", dependencies=[Depends(require_key)])
async def reel_check(reel_id: str, tenant: str = Depends(current_tenant)):
    from .reels import service as rs
    try:
        return await rs.fact_check(tenant, reel_id)
    except rs.ReelError as e:
        raise HTTPException(400, str(e))


# ---------------- v0.75 Pehchaan Locker: ID numbers (encrypted; masked unless she taps "dikhao") ----------------
class IdIn(BaseModel):
    kind: str
    number: str
    person: str = "self"
    note: str = ""


def _idv(fn, *a):
    from . import idvault
    try:
        return fn(*a)
    except idvault.VaultError as e:
        raise HTTPException(400, str(e))


@app.get("/api/ids", dependencies=[Depends(require_key)])
def ids_list(tenant: str = Depends(current_tenant)):
    from . import idvault
    return {"ids": idvault.list_(tenant), "kinds": idvault.KINDS, "people": idvault.PERSON_LABEL}


@app.post("/api/ids", dependencies=[Depends(require_key)])
def ids_save(body: IdIn, tenant: str = Depends(current_tenant)):
    from . import idvault
    return _idv(idvault.save, tenant, body.kind, body.number, body.person, body.note)


@app.post("/api/ids/{rid}/reveal", dependencies=[Depends(require_key)])
def ids_reveal(rid: str, tenant: str = Depends(current_tenant)):
    from . import idvault
    return _idv(idvault.reveal, tenant, rid)


@app.delete("/api/ids/{rid}", dependencies=[Depends(require_key)])
def ids_delete(rid: str, tenant: str = Depends(current_tenant)):
    from . import idvault
    return _idv(idvault.delete, tenant, rid)


# ---------------- v0.69 crash reports from the phone ----------------
class CrashIn(BaseModel):
    kind: str = ""
    text: str = ""
    during_call: bool = False


def _crash_file(tenant: str):
    from pathlib import Path
    p = Path("data") / "crashes"
    p.mkdir(parents=True, exist_ok=True)
    return p / (re.sub(r"[^A-Za-z0-9_-]", "_", tenant)[:60] + ".jsonl")


@app.post("/api/app/crash", dependencies=[Depends(require_key)])
def app_crash(body: CrashIn, tenant: str = Depends(current_tenant)):
    """Why the app closed by itself (stack trace or Android's exit record). Kept: the newest 50 per owner."""
    rec = {"at": time.time(), "kind": body.kind[:20], "during_call": body.during_call, "text": body.text[:20000]}
    f = _crash_file(tenant)
    lines = f.read_text(encoding="utf-8").splitlines()[-49:] if f.exists() else []
    lines.append(json.dumps(rec, ensure_ascii=False))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logging.getLogger("santosh.crash").warning("app crash (%s, call=%s): %s", rec["kind"], body.during_call,
                                               body.text[:400].replace("\n", " | "))
    return {"ok": True}


@app.get("/api/app/crashes", dependencies=[Depends(require_key)])
def app_crashes(tenant: str = Depends(current_tenant)):
    f = _crash_file(tenant)
    rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()] if f.exists() else []
    return {"crashes": rows[::-1]}


# ---------------- Hoola Motion: animated reels written as code, rendered to MP4 ----------------
class MotionPlanIn(BaseModel):
    kind: str
    brief: str


class MotionMakeIn(BaseModel):
    kind: str
    data: dict = {}
    brief: str = ""
    aspect: str = "9:16"
    music: str = "upbeat"


class MotionYoutubeIn(BaseModel):
    title: str = ""
    privacy: str = "private"


def _mo(fn, *a):
    from .motion import service as mo
    try:
        return fn(*a)
    except mo.MotionError as e:
        raise HTTPException(400, str(e))


@app.get("/api/motion/kinds", dependencies=[Depends(require_key)])
def motion_kinds(tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return mo.kinds()


@app.post("/api/motion/plan", dependencies=[Depends(require_key)])
async def motion_plan(body: MotionPlanIn, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return await asyncio.to_thread(_mo, mo.plan, body.kind, body.brief)


@app.post("/api/motion/videos", dependencies=[Depends(require_key)])
async def motion_make(body: MotionMakeIn, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return await asyncio.to_thread(_mo, mo.create, tenant, body.kind, body.data, body.aspect, body.music, body.brief)


@app.get("/api/motion/videos", dependencies=[Depends(require_key)])
def motion_list(tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return {"videos": mo.list_(tenant)}


@app.get("/api/motion/videos/{vid}", dependencies=[Depends(require_key)])
def motion_get(vid: str, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    try:
        return mo.get(tenant, vid)
    except mo.MotionError as e:
        raise HTTPException(404, str(e))


@app.delete("/api/motion/videos/{vid}", dependencies=[Depends(require_key)])
def motion_delete(vid: str, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    return _mo(mo.delete, tenant, vid)


@app.post("/api/motion/videos/{vid}/youtube", dependencies=[Depends(require_key)])
async def motion_youtube(vid: str, body: MotionYoutubeIn, tenant: str = Depends(current_tenant)):
    from .motion import service as mo
    conv = await asyncio.to_thread(_tv_conv, tenant)
    return await asyncio.to_thread(_mo, mo.to_youtube, tenant, conv, vid, body.title, body.privacy)


@app.get("/api/motion/files/{name}")
def motion_file(name: str, exp: int = 0, sig: str = ""):
    """Signed link (no login header needed, so the phone's video player and share can use it)."""
    from fastapi.responses import FileResponse
    from .motion import service as mo
    m = re.fullmatch(r"(mv_[A-Za-z0-9]+)\.(mp4|jpg)", name)
    if not m or not mo.check_sig(m.group(1), m.group(2), exp, sig):
        raise HTTPException(403, "The link is old.")
    p = mo.file_path(m.group(1), m.group(2))
    if p is None:
        raise HTTPException(404, "Video not found.")
    return FileResponse(p, media_type="video/mp4" if m.group(2) == "mp4" else "image/jpeg",
                        filename=f"hoola-{m.group(1)}.{m.group(2)}" if m.group(2) == "mp4" else None)


# ---------------- Hoola TV: free official live channels, on the phone or the TV ----------------
class TvCastIn(BaseModel):
    channel: str
    tv: str = ""


def _tv_conv(tenant: str) -> str:
    from .bazar.service import latest_conversation
    with session() as s:
        return latest_conversation(s, tenant) or ""


@app.get("/api/tv/channels", dependencies=[Depends(require_key)])
def tv_channels(q: str = "", category: str = "", country: str = "", offset: int = 0, limit: int = 90,
                tenant: str = Depends(current_tenant)):
    """Channels worldwide. country = 'IN' / 'US'... ('' = whole world, India first); paged with offset/limit."""
    from .tv import catalog
    data = catalog.load()
    page = catalog.search(q, category, country, limit=max(1, min(limit, 200)), offset=max(0, offset))
    out = {**page, "offset": offset, "updated": data.get("updated", 0)}
    if offset == 0:
        out["categories"] = catalog.categories(country)
        out["countries"] = catalog.countries()
    return out


@app.get("/api/tv/channels/{cid}", dependencies=[Depends(require_key)])
def tv_channel_detail(cid: str, tenant: str = Depends(current_tenant)):
    from .tv import service as tvs
    try:
        return tvs.detail(cid)
    except tvs.TvError as e:
        raise HTTPException(404, str(e))


@app.post("/api/tv/cast", dependencies=[Depends(require_key)])
async def tv_cast(body: TvCastIn, tenant: str = Depends(current_tenant)):
    """Play a channel on the Chromecast / Android TV on the phone's Wi-Fi (the phone does it and reports back)."""
    from .tv import service as tvs
    try:
        return await tvs.play_on_tv(tenant, await asyncio.to_thread(_tv_conv, tenant), body.channel, body.tv)
    except tvs.TvError as e:
        raise HTTPException(404, str(e))


@app.post("/api/tv/stop", dependencies=[Depends(require_key)])
async def tv_stop(tenant: str = Depends(current_tenant)):
    from .tv import service as tvs
    return await tvs.stop_on_tv(tenant, await asyncio.to_thread(_tv_conv, tenant))


@app.get("/api/logo/{kind}/{key}")
async def plugin_logo(kind: str, key: str):
    """A plugin's / MCP server's real logo (from the brand's own site, cached as a 256 px PNG). Public: logos are
    public and phones load them as plain images; only things in Hoola's own lists are ever looked up."""
    from .bazar import logos
    if kind not in ("pack", "feat", "gh", "mcp", "tv", "dir", "cmp") or len(key) > 120:
        raise HTTPException(404, "no logo")
    png = await asyncio.to_thread(logos.logo, kind, key)
    if not png:
        raise HTTPException(404, "no logo")
    return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=2592000"})


@app.get("/api/bazar/connections", dependencies=[Depends(require_key)])
def bazar_connections(tenant: str = Depends(current_tenant)):
    return {"apps": bazar.connections(tenant)}


@app.post("/api/bazar/connections/{pack_id}/link", dependencies=[Depends(require_key)])
async def bazar_link(pack_id: str, tenant: str = Depends(current_tenant)):
    try:
        return {"url": await asyncio.to_thread(bazar.link_start, tenant, pack_id)}
    except BazarError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/bazar/connections/{pack_id}", dependencies=[Depends(require_key)])
def bazar_unlink(pack_id: str, tenant: str = Depends(current_tenant)):
    return {"unlinked": _bz(bazar.unlink, tenant, pack_id)}


class McpAddIn(BaseModel):
    url: str
    name: str = ""
    ref: str = ""
    key: str = ""
    key_header: str = ""


class McpKeyIn(BaseModel):
    key: str
    header: str = ""


@app.get("/api/bazar/mcp", dependencies=[Depends(require_key)])
def bazar_mcp_list(tenant: str = Depends(current_tenant)):
    return {"servers": _bz(bazar.mcp_list, tenant)}


@app.get("/api/bazar/mcp/avatar", dependencies=[Depends(require_key)])
async def bazar_mcp_avatar(tenant: str = Depends(current_tenant)):
    """What the avatar knows about the owner's MCP servers right now: status and the tools it can call."""
    from .agent import mcp_live
    snap = await asyncio.to_thread(mcp_live.snapshot, tenant)
    return {"servers": [{"pack_id": x["pack_id"], "name": x["name"], "status": x["status"], "error": x["error"],
                         "tools": [t["name"] for t in x["tools"]]} for x in snap]}


class FeaturedIn(BaseModel):
    url: str = ""
    key: str = ""
    key_header: str = ""
    readonly: bool | None = None          # v0.143 GitHub MCP: only read tools
    toolsets: list[str] | None = None     # v0.143 GitHub MCP toolsets / v0.145 Supabase feature groups
    project: str | None = None            # v0.145 Supabase project ref


@app.get("/api/bazar/mcp/featured", dependencies=[Depends(require_key)])
def bazar_mcp_featured(tenant: str = Depends(current_tenant)):
    return {"connectors": _bz(bazar.mcp_featured, tenant)}


@app.post("/api/bazar/mcp/featured/{fid}", dependencies=[Depends(require_key)])
async def bazar_mcp_connect(fid: str, body: FeaturedIn, tenant: str = Depends(current_tenant)):
    try:
        return await asyncio.to_thread(bazar.mcp_connect_featured, tenant, fid, body.url, body.key, body.key_header,
                                       readonly=body.readonly, toolsets=body.toolsets, project=body.project)
    except BazarError as e:
        raise HTTPException(400, str(e))


class OneTapIn(BaseModel):
    ref: str
    keys: dict[str, str] = {}
    accept_caution: bool = False


@app.post("/api/bazar/mcp/one_tap", dependencies=[Depends(require_key)])
async def bazar_mcp_one_tap(body: OneTapIn, tenant: str = Depends(current_tenant)):
    """v0.154 'Ek tap mein jodo': hosted servers join directly, npm / PyPI ones run on the MCP runner box. Keys only
    from the app (never chat)."""
    try:
        return await asyncio.to_thread(bazar.mcp_one_tap, tenant, body.ref, body.keys, body.accept_caution)
    except BazarError as e:
        raise HTTPException(400, str(e))


@app.get("/api/bazar/mcp/runner", dependencies=[Depends(require_key)])
async def bazar_mcp_runner():
    from .bazar import runner as mcp_runner
    return await asyncio.to_thread(mcp_runner.health)


@app.get("/api/bazar/mcp/directory", dependencies=[Depends(require_key)])
def bazar_mcp_directory(q: str = "", field: str = "", limit: int = 20):
    return _bz(bazar.mcp_directory, q, field, max(1, min(limit, 50)))


@app.post("/api/bazar/mcp", dependencies=[Depends(require_key)])
async def bazar_mcp_add(body: McpAddIn, tenant: str = Depends(current_tenant)):
    try:
        return await asyncio.to_thread(bazar.mcp_add, tenant, body.url, body.name, body.ref, body.key, body.key_header)
    except BazarError as e:
        raise HTTPException(400, str(e))


@app.put("/api/bazar/mcp/{pack_id}/key", dependencies=[Depends(require_key)])
def bazar_mcp_key(pack_id: str, body: McpKeyIn, tenant: str = Depends(current_tenant)):
    return _bz(bazar.mcp_set_key, tenant, pack_id, body.key, body.header)


class McpToolIn(BaseModel):
    enabled: bool | None = None
    ask: bool | None = None


@app.get("/api/bazar/mcp/{pack_id}/tools", dependencies=[Depends(require_key)])
async def bazar_mcp_tools(pack_id: str, tenant: str = Depends(current_tenant)):
    """v0.91 Every tool of a server she added, with her on / off and "pehle poochho" switches."""
    return await asyncio.to_thread(_bz, bazar.mcp_tools, tenant, pack_id)


@app.patch("/api/bazar/mcp/{pack_id}/tools/{tool}", dependencies=[Depends(require_key)])
async def bazar_mcp_tool_set(pack_id: str, tool: str, body: McpToolIn, tenant: str = Depends(current_tenant)):
    return await asyncio.to_thread(_bz, bazar.mcp_tool_set, tenant, pack_id, tool, body.enabled, body.ask)


@app.delete("/api/bazar/mcp/{pack_id}", dependencies=[Depends(require_key)])
def bazar_mcp_remove(pack_id: str, tenant: str = Depends(current_tenant)):
    return {"removed": _bz(bazar.mcp_remove, tenant, pack_id)}


@app.get("/bazar/link/callback")
async def bazar_link_callback(state: str = "", code: str = "", error: str = ""):
    from html import escape
    scheme = get_settings().app_redirect_scheme
    if error or not code:
        msg, ok = f"Linking was cancelled ({escape(error or 'no code')}).", False
    else:
        try:
            _, name = await asyncio.to_thread(bazar.link_finish, state, code)
            msg, ok = f"{escape(name)} is now linked to Santosh.", True
        except BazarError as e:
            msg, ok = escape(str(e)), False
    link = f"{scheme}://bazar?linked={'1' if ok else '0'}"
    from fastapi.responses import HTMLResponse
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:sans-serif;padding:32px;text-align:center"><h2>{'✅' if ok else '⚠️'} {msg}</h2>
<p><a href="{link}" style="font-size:18px">Back to Santosh</a></p><script>setTimeout(()=>location.href="{link}",800)</script>""")


class BazarTokenIn(BaseModel):
    tenant: str
    provider: str
    access_token: str = Field(min_length=8)
    expires_in: int | None = None


@app.post("/api/bazar/admin/connections")
def bazar_admin_link(body: BazarTokenIn, request: Request):
    st = get_settings()
    if not st.api_key or not hmac.compare_digest(_bearer(request), st.api_key):
        raise HTTPException(401, "Admin API key required")
    _bz(bazar.link_token, body.tenant, body.provider, body.access_token, body.expires_in)
    return {"linked": body.provider}


@app.post("/bazar/webhooks/payment")
async def bazar_payment_webhook(request: Request):
    raw = await request.body()
    if not bazar.verify_webhook(raw, request.headers.get("x-signature", "")):
        raise HTTPException(401, "Bad or missing signature (set BAZAR_WEBHOOK_SECRET)")
    try:
        data = json.loads(raw)
        ref, status = str(data["txn_ref"]), str(data.get("status", "")).upper()
    except Exception:
        raise HTTPException(422, "Body must be JSON with txn_ref and status")
    return await asyncio.to_thread(lambda: _bz(bazar.payment_confirmed, ref, status == "SUCCESS", str(data.get("provider_ref", ""))))


@app.post("/api/bazar/dev/simulate-payment/{txn_ref}", dependencies=[Depends(require_key)])
def bazar_simulate(txn_ref: str, ok: bool = True):
    from .bazar.config import get_settings as bz_settings
    if bz_settings().env != "dev":
        raise HTTPException(404, "Not found")
    return _bz(bazar.payment_confirmed, txn_ref, ok, "SIMULATED")


# merchants: a shop manages its orders with its own X-Shop-Token (shown once at onboarding)
class ShopIn(BaseModel):
    template_id: str
    name: str = Field(min_length=2, max_length=160)
    owner_phone: str
    upi_id: str
    city: str = ""
    pincodes: list[str] = []
    aliases: list[str] = []
    languages: list[str] = ["mr", "hi", "en"]
    min_order_rupees: float = 0
    delivery_fee_rupees: float = 0
    slots: list[str] = []


class ShopItemIn(BaseModel):
    name: str
    price_rupees: float = Field(gt=0)
    unit: str = "pc"
    unit_qty: float = 1.0
    aliases: list[str] = []
    in_stock: bool = True
    kind: str = "product"


class OrderUpdateIn(BaseModel):
    status: str | None = None
    paid: bool = False


class DueIn(BaseModel):
    customer_ref: str
    amount_rupees: float = Field(gt=0)
    customer_phone: str = ""
    description: str = ""
    due_on: str | None = None


@app.post("/api/bazar/shops", dependencies=[Depends(require_key)])
def bazar_create_shop(body: ShopIn, tenant: str = Depends(current_tenant)):
    return _bz(bazar.create_shop, tenant, body.model_dump())


@app.get("/bazar/shops")
def bazar_list_shops(template: str | None = None, pincode: str | None = None):
    return bazar.list_shops(template, pincode)


@app.post("/bazar/shops/{shop_id}/items")
def bazar_shop_items(shop_id: str, items: list[ShopItemIn], request: Request):
    return _bz(bazar.add_items, shop_id, [i.model_dump() for i in items], _maybe_tenant(request), request.headers.get("x-shop-token"))


@app.get("/bazar/shops/{shop_id}/orders")
def bazar_shop_orders(shop_id: str, request: Request, status: str | None = None):
    return _bz(bazar.shop_orders, shop_id, _maybe_tenant(request), request.headers.get("x-shop-token"), status)


@app.post("/bazar/shops/{shop_id}/orders/{order_id}")
def bazar_shop_order_update(shop_id: str, order_id: str, body: OrderUpdateIn, request: Request):
    return _bz(bazar.update_order, shop_id, order_id, body.status, body.paid, _maybe_tenant(request),
               request.headers.get("x-shop-token"))


@app.post("/bazar/shops/{shop_id}/dues")
def bazar_shop_dues(shop_id: str, dues: list[DueIn], request: Request):
    return _bz(bazar.upload_dues, shop_id, [d.model_dump() for d in dues], _maybe_tenant(request), request.headers.get("x-shop-token"))


# ---------------- Santosh Shopping: orders, MCP tokens, ONDC callbacks, Commerce MCP at /mcp/commerce ----------------
from .bazar.api import commerce as bazar_commerce  # noqa: E402

bazar_commerce.mount(app, require_key, current_tenant)


# ---------------- catch-up: what Santosh did while the phone was off ----------------
@app.get("/api/catchup", dependencies=[Depends(require_key)])
def catchup(since: str, tenant: str = Depends(current_tenant)):
    from datetime import datetime, timezone
    try:
        t = datetime.fromisoformat(since.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(400, "since must be an ISO time")
    with session() as s:
        convs = [c.id for c in s.scalars(select(Conversation).where(Conversation.tenant_id == tenant)).all()]
        rows = s.scalars(select(Message).where(Message.conversation_id.in_(convs), Message.role == "assistant",
                                               Message.in_history.is_(False), Message.created_at > t)
                         .order_by(Message.id).limit(60)).all() if convs else []
        items = [{"text": r.display or "", "at": r.created_at.isoformat()} for r in rows if (r.display or "").strip()]
    pending = bazar.pending_approvals(tenant)
    return {"items": items, "pending": pending, "count": len(items)}


# ---------------- Aaj ka Din: one call for the home card — weather + today's meetings + next reminder ----------------
_day_weather: dict[str, tuple[float, dict]] = {}   # tenant → (fetched_at, weather; {} = last fetch failed)


@app.get("/api/day", dependencies=[Depends(require_key)])
async def day(tenant: str = Depends(current_tenant)):
    """v0.166 premium Aaj ka Din card: mausam (cached 15 min), aaj ki baaki meetings, agla reminder — one round trip."""
    from datetime import datetime, timedelta
    from . import gcal
    tz = life.tz_of(tenant)
    now = datetime.now(tz)
    out: dict = {"weather": None, "events": [], "next_reminder": None}

    hit = _day_weather.get(tenant)
    if hit and now.timestamp() - hit[0] < 900:
        out["weather"] = hit[1] or None
    else:
        try:
            w = await life.weather_for(tenant)
            _day_weather[tenant] = (now.timestamp(), w)
            out["weather"] = w
        except Exception:
            _day_weather[tenant] = (now.timestamp(), {})   # short-circuit failures too — never hammer open-meteo

    if gcal.configured():   # aaj ki meetings jo abhi baaqi hain (ya abhi chal rahi hain)
        try:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            views = await gcal.agenda(start, start + timedelta(days=1), keep_raw=True)
            evs: list[dict] = []
            for v in views:
                if v.get("all_day"):
                    continue
                try:
                    st = datetime.fromisoformat(v["_start_raw"])
                    en = datetime.fromisoformat(v["_end_raw"]) if v.get("_end_raw") else None
                    running = st <= now and (en is None or en > now)
                    if en is not None and en <= now:
                        continue   # khatam ho chuki
                    evs.append({"title": v.get("title") or "(no title)", "start": v.get("start") or "",
                                "location": (v.get("location") or "").strip(),
                                "attendees": len(v.get("attendees") or []),
                                "starts_in_mins": None if running else max(0, int((st - now).total_seconds() // 60)),
                                "running": running})
                except Exception:
                    continue
                if len(evs) >= 3:
                    break
            out["events"] = evs
        except Exception:
            pass

    try:
        rem = life.upcoming_reminders(tenant, limit=1)
        out["next_reminder"] = rem[0] if rem else None
    except Exception:
        pass
    return out


# ---------------- "Hey Santosh" wake word (runs on the phone; the server only hands out the keyword) ----------------
def _wake_file():
    import os
    st = get_settings()
    f = st.wake_keyword_file.strip()
    return f if f and os.path.isfile(f) else ""


@app.get("/api/wake", dependencies=[Depends(require_key)])
def wake_config(tenant: str = Depends(current_tenant)):
    """Santosh Wake (our own on-device model). The app has the model built in; the server can push a newer one
    (WAKE_KEYWORD_FILE = path to a hey_santosh.onnx from wakeword/train.py) and tune the threshold."""
    import os
    st = get_settings()
    f = _wake_file()
    custom = bool(f) and f.endswith(".onnx")
    sens = min(max(st.wake_sensitivity, 0.0), 1.0)
    return {"available": True, "engine": "santosh-wake", "threshold": round(min(0.9, max(0.25, 1.1 - sens)), 3),
            "sensitivity": sens, "custom_model": custom, "version": str(int(os.path.getmtime(f))) if custom else "builtin"}


@app.get("/api/wake/keyword", dependencies=[Depends(require_key)])
def wake_keyword(tenant: str = Depends(current_tenant)):
    f = _wake_file()
    if not f:
        raise HTTPException(404, "No keyword file")
    if not f.endswith(".onnx"):
        raise HTTPException(404, "WAKE_KEYWORD_FILE must be a hey_santosh.onnx (Santosh Wake)")
    return FileResponse(f, media_type="application/octet-stream", filename="hey_santosh.onnx")


# ------------------------------------------------------------------ v0.164 projects, "Kaam ke folder" (CHAT_PROJECTS)
def _projects_on():
    from . import projects
    if not projects.enabled():
        raise HTTPException(404, "Projects are off (CHAT_PROJECTS)")
    return projects


def _proj_call(fn, *a):
    from . import projects
    try:
        return fn(*a)
    except projects.ProjectError as e:
        raise HTTPException(e.status, str(e))


class ProjectIn(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    instructions: str | None = Field(default=None, max_length=8000)
    memory: str | None = Field(default=None, max_length=8000)
    emoji: str | None = Field(default=None, max_length=8)
    use_main_memory: bool | None = None   # v0.609: off = this Session uses only its own memory


@app.get("/api/projects", dependencies=[Depends(require_key)])
def projects_list(tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return {"projects": p.list_for(tenant)}


@app.post("/api/projects", status_code=201, dependencies=[Depends(require_key)])
def projects_create(body: ProjectIn, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.create, tenant, body.name or "", body.instructions or "", body.emoji or "")


@app.get("/api/projects/{pid}", dependencies=[Depends(require_key)])
def projects_get(pid: str, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.get, tenant, pid)


@app.patch("/api/projects/{pid}", dependencies=[Depends(require_key)])
def projects_patch(pid: str, body: ProjectIn, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.patch, tenant, pid, body.name, body.instructions, body.memory, body.emoji,
                      body.use_main_memory)


@app.delete("/api/projects/{pid}", dependencies=[Depends(require_key)])
def projects_delete(pid: str, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.delete, tenant, pid)


@app.post("/api/projects/{pid}/files", status_code=201, dependencies=[Depends(require_key)])
async def projects_file(pid: str, file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
    """A file for the project (kept until she removes it; big ones are searched through her Gyaan)."""
    p = _projects_on()
    data = await file.read(p.MAX_FILE + 1)
    return await asyncio.to_thread(_proj_call, p.add_file, tenant, pid, file.filename or "file", data)


@app.delete("/api/projects/{pid}/files/{fid}", dependencies=[Depends(require_key)])
def projects_file_delete(pid: str, fid: str, tenant: str = Depends(current_tenant)):
    p = _projects_on()
    return _proj_call(p.remove_file, tenant, pid, fid)


# ------------------------------------------------------------------ v0.163 side panel (SIDE_PANEL)
def _panel_on():
    from . import panel
    if not panel.enabled():
        raise HTTPException(404, "Side panel is off (SIDE_PANEL)")
    return panel


def _panel_call(fn, *a):
    from . import panel
    try:
        return fn(*a)
    except panel.PanelError as e:
        raise HTTPException(e.status, str(e))


@app.get("/api/panel/library", dependencies=[Depends(require_key)])
def panel_library(kind: str = "", q: str = "", tenant: str = Depends(current_tenant)):
    """Banaya hua: every page, file, picture, video, website and app Hoola made for her (newest first)."""
    panel = _panel_on()
    return {"items": panel.library(tenant, kind[:10], q[:100])}


@app.get("/api/panel/files/{file_id}/info", dependencies=[Depends(require_key)])
def panel_file_info(file_id: str, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.file_info, tenant, file_id)


@app.get("/api/panel/files/{file_id}", dependencies=[Depends(require_key)])
def panel_file(file_id: str, download: int = 0, tenant: str = Depends(current_tenant)):
    """Her file with her login. Only images / video / audio / PDF are viewable; everything else is a download."""
    panel = _panel_on()
    data, mt, name, viewable = _panel_call(panel.file_bytes, tenant, file_id)
    from urllib.parse import quote
    disp = "inline" if viewable and not download else "attachment"
    return Response(content=data, media_type=mt, headers={
        "Content-Disposition": f"{disp}; filename*=UTF-8''{quote(name)}", "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store", "Content-Security-Policy": "default-src 'none'; img-src 'self'; media-src 'self'"
        if disp == "inline" and not mt.endswith("pdf") else "default-src 'none'; sandbox"})


@app.get("/api/panel/files/{file_id}/text", dependencies=[Depends(require_key)])
def panel_file_text(file_id: str, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.file_text, tenant, file_id)


@app.get("/api/panel/files/{file_id}/pdf", dependencies=[Depends(require_key)])
def panel_file_pdf(file_id: str, tenant: str = Depends(current_tenant)):
    """Word / Excel / PowerPoint as a PDF to look at (Gotenberg on the server)."""
    panel = _panel_on()
    pdf = _panel_call(panel.file_pdf, tenant, file_id)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": "inline", "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@app.get("/api/panel/pages/{aid}/source", dependencies=[Depends(require_key)])
def panel_page_source(aid: str, version: int = 0, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.page_source, tenant, aid, version)


@app.get("/api/panel/pages/{aid}/view", dependencies=[Depends(require_key)])
def panel_page_view(aid: str, version: int = 0, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.page_view, tenant, aid, version)


class PanelShareIn(BaseModel):
    kind: str = Field(max_length=8)
    id: str = Field(min_length=1, max_length=64)
    conversation_id: str = Field(default="", max_length=40)


@app.post("/api/panel/share", dependencies=[Depends(require_key)])
def panel_share(body: PanelShareIn, tenant: str = Depends(current_tenant)):
    """Share = a Haan card first (nothing is public until she taps it)."""
    panel = _panel_on()
    if body.conversation_id:
        _conv_or_404(body.conversation_id, tenant)
    return _panel_call(panel.ask_share, tenant, body.conversation_id, body.kind, body.id)


class PanelDecideIn(BaseModel):
    approve: bool


@app.post("/api/panel/share/{sid}", dependencies=[Depends(require_key)])
def panel_share_decide(sid: str, body: PanelDecideIn, tenant: str = Depends(current_tenant)):
    panel = _panel_on()
    return _panel_call(panel.decide_share, tenant, sid, body.approve)


# ------------------------------------------------------------------ Santosh Artifacts
class ArtShareIn(BaseModel):
    on: bool = True


class ArtStateIn(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: object = None


class ArtAskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ArtReviseIn(BaseModel):
    request: str = Field(min_length=2, max_length=4000)


@app.get("/api/artifacts", dependencies=[Depends(require_key)])
def artifacts_list(tenant: str = Depends(current_tenant)):
    from . import artifacts
    return {"artifacts": artifacts.list_for(tenant)}


@app.get("/api/artifacts/{aid}", dependencies=[Depends(require_key)])
def artifact_detail(aid: str, tenant: str = Depends(current_tenant)):
    from . import artifacts
    d = artifacts.detail(tenant, aid)
    if d is None:
        raise HTTPException(404, "Not found")
    return d


@app.get("/api/artifacts/{aid}/view", dependencies=[Depends(require_key)])
def artifact_view_link(aid: str, version: int = 0, tenant: str = Depends(current_tenant)):
    from . import artifacts
    a = artifacts.get(tenant, aid)
    if a is None or not a.version:
        raise HTTPException(404, "Page not ready yet")
    v = version if 0 < version <= a.version else a.version
    return {"url": artifacts.view_url(aid, v), "version": v}


@app.post("/api/artifacts/{aid}/share", dependencies=[Depends(require_key)])
def artifact_share(aid: str, body: ArtShareIn, tenant: str = Depends(current_tenant)):
    from . import artifacts
    r = artifacts.set_share(tenant, aid, body.on)
    if r is None:
        raise HTTPException(404, "Not found")
    return r


@app.post("/api/artifacts/{aid}/stop", dependencies=[Depends(require_key)])
def artifact_stop(aid: str, tenant: str = Depends(current_tenant)):
    """v0.725 PAGE CARD: Stop while a page is being made (the last ready version stays)."""
    from . import artifacts
    if artifacts.get(tenant, aid) is None:
        raise HTTPException(404, "Not found")
    return {"stopped": artifacts.stop(tenant, aid)}


@app.post("/api/artifacts/{aid}/undo", dependencies=[Depends(require_key)])
def artifact_undo(aid: str, tenant: str = Depends(current_tenant)):
    """parity Phase 6: Undo in the panel - the version before the newest comes back as a new version."""
    from . import artifacts
    try:
        r = artifacts.undo(tenant, aid)
    except artifacts.EditError as e:
        raise HTTPException(409, str(e))
    if r is None:
        raise HTTPException(404, "Not found")
    return r


@app.delete("/api/artifacts/{aid}", dependencies=[Depends(require_key)])
def artifact_delete(aid: str, tenant: str = Depends(current_tenant)):
    from . import artifacts
    if not artifacts.delete(tenant, aid):
        raise HTTPException(404, "Not found")
    return {"ok": True}


@app.get("/api/artifacts/{aid}/state", dependencies=[Depends(require_key)])
def artifact_state(aid: str, tenant: str = Depends(current_tenant)):
    from . import artifacts
    st = artifacts.state_all(tenant, aid)
    if st is None:
        raise HTTPException(404, "Not found")
    return {"state": st}


@app.put("/api/artifacts/{aid}/state", dependencies=[Depends(require_key)])
def artifact_state_set(aid: str, body: ArtStateIn, tenant: str = Depends(current_tenant)):
    from . import artifacts
    try:
        artifacts.state_set(tenant, aid, body.key, body.value)
    except KeyError:
        raise HTTPException(404, "Not found")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/artifacts/{aid}/ask", dependencies=[Depends(require_key)])
async def artifact_ask(aid: str, body: ArtAskIn, tenant: str = Depends(current_tenant)):
    from . import artifacts
    try:
        return {"answer": await artifacts.ask(tenant, aid, body.question)}
    except KeyError:
        raise HTTPException(404, "Not found")
    except ValueError as e:
        raise HTTPException(429 if "sawaal" in str(e) else 400, str(e))
    except Exception as e:
        raise HTTPException(503, f"Santosh cannot answer right now ({type(e).__name__})")


@app.post("/api/artifacts/{aid}/revise", dependencies=[Depends(require_key)])
async def artifact_revise(aid: str, body: ArtReviseIn, tenant: str = Depends(current_tenant)):
    from . import artifacts
    a = artifacts.get(tenant, aid)
    if a is None:
        raise HTTPException(404, "Not found")
    try:
        await artifacts.make(tenant, a.conversation_id, body.request, artifact_id=aid, wait=0)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(409, str(e))
    return {"status": "building"}


@app.get("/a/{aid}/{version}")
def artifact_page(aid: str, version: int, exp: int = 0, sig: str = "", panel: int = 0):
    """The owner's signed, expiring link (opened inside the app). Sandboxed: the page can't reach Santosh's API."""
    from . import artifacts
    from .db import Artifact, session as dbs
    if not artifacts.check(aid, version, exp, sig):
        raise HTTPException(403, "Link expired. Open it again from the Santosh app.")
    with dbs() as s:
        a = s.get(Artifact, aid)
        if a is None or a.deleted:
            raise HTTPException(404, "Not found")
        tenant = a.tenant_id
    page = artifacts.latest_html(aid, version)
    if page is None:
        raise HTTPException(404, "Not found")
    state = artifacts.state_all(tenant, aid) or {}
    return HTMLResponse(artifacts.render(aid, version, page, state, panel=bool(panel)), headers=artifacts.headers())


@app.get("/s/{token}")
def artifact_shared(token: str):
    """Public share link (latest version). Saved data is never included; it stays private to the owner."""
    from . import artifacts
    a = artifacts.by_share(token)
    if a is None or not a.version:
        raise HTTPException(404, "This link is off or doesn't exist")
    page = artifacts.latest_html(a.id, a.version) or ""
    return HTMLResponse(artifacts.render(a.id, a.version, page, None), headers=artifacts.headers())


# ------------------------------------------------------------------ push notifications (Firebase Cloud Messaging)
class PushTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=300)
    platform: str = "android"


@app.post("/api/push/token", dependencies=[Depends(require_key)])
def push_token(body: PushTokenIn, tenant: str = Depends(current_tenant)):
    from . import push
    push.register(tenant, body.token, body.platform)
    return {"ok": True, "push": push.configured()}


@app.delete("/api/push/token", dependencies=[Depends(require_key)])
def push_token_delete(body: PushTokenIn, tenant: str = Depends(current_tenant)):
    from . import push
    push.unregister(tenant, body.token)
    return {"ok": True}


# ------------------------------------------------------------------ Santosh Browser live view
_browser_memo: OrderedDict = OrderedDict()      # v0.190.1 P0: (kind, tenant, sid) -> (at, value), TTL 1 s
_BROWSER_MEMO_S = 1.0
_BROWSER_MEMO_MAX = 512
_browser_memo_lock = threading.Lock()


def _browser_memo_get(key: tuple):
    hit = None
    with _browser_memo_lock:
        pair = _browser_memo.get(key)
        if pair:
            at, val = pair
            if time.time() - at <= _BROWSER_MEMO_S:
                hit = val
            else:
                _browser_memo.pop(key, None)
    return hit


def _browser_memo_put(key: tuple, val) -> None:
    with _browser_memo_lock:
        _browser_memo[key] = (time.time(), val)
        _browser_memo.move_to_end(key)
        while len(_browser_memo) > _BROWSER_MEMO_MAX:
            _browser_memo.popitem(last=False)


@app.get("/api/browser/{sid}/live", dependencies=[Depends(require_key)])
def browser_live(sid: str, tenant: str = Depends(current_tenant)):
    hit = _browser_memo_get(("live", tenant, sid))   # v0.190.1 P0: the live page was polled ~90 rps during the
    if hit is not None:                              # load spiral - every hit is a fresh thread + dict read; a
        return hit                                   # 1 s memo caps the pile-up without changing what she sees
    from . import browser
    if sid.startswith("pcop_"):
        from .pc import operator
        op = operator.get(tenant, sid)
        if op is None:
            raise HTTPException(404, "not found")
        out = op.live()
    else:
        try:
            out = browser.live(tenant, sid)
        except browser.BrowserError as e:
            raise HTTPException(404, str(e))
    _browser_memo_put(("live", tenant, sid), out)
    return out


@app.get("/api/browser/{sid}/frame", dependencies=[Depends(require_key)])
def browser_frame(sid: str, tenant: str = Depends(current_tenant)):
    hit = _browser_memo_get(("frame", tenant, sid))  # same 1 s memo - the JPEG bytes are immutable
    if hit is not None:
        return Response(hit, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
    from . import browser
    if sid.startswith("pcop_"):
        from .pc import operator
        op = operator.get(tenant, sid)
        if op is None or not op.frame:
            raise HTTPException(404, "no frame yet")
        img = op.frame
    else:
        try:
            img = browser.frame(tenant, sid)
        except browser.BrowserError as e:
            raise HTTPException(404, str(e))
    _browser_memo_put(("frame", tenant, sid), img)
    return Response(img, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.post("/api/browser/{sid}/stop", dependencies=[Depends(require_key)])
def browser_stop(sid: str, tenant: str = Depends(current_tenant)):
    from . import browser
    if sid.startswith("pcop_"):
        from .pc import operator
        if not operator.stop(tenant, sid):
            raise HTTPException(404, "not found")
        return {"session_id": sid, "status": "cancelled"}
    try:
        return browser.cancel(tenant, sid)
    except browser.BrowserError as e:
        raise HTTPException(404, str(e))


# ------------------------------------------------------------------ Santosh Agent Army (open-source agents catalogue)
@app.get("/api/agents/directory", dependencies=[Depends(require_key)])
def agents_directory(q: str = "", field: str = "", kind: str = "", tier: str = "", limit: int = 30):
    from .bazar import agents
    return {"agents": agents.search(q, field, kind, tier, limit), "total": len(agents.agents())}


@app.get("/api/agents/fields", dependencies=[Depends(require_key)])
def agents_fields():
    from .bazar import agents
    return agents.stats()


@app.get("/api/agents/item/{ref}", dependencies=[Depends(require_key)])
def agents_item(ref: str):
    from .bazar import agents
    a = agents.get(ref)
    if a is None:
        raise HTTPException(404, "Not found")
    return a


# ------------------------------------------------------------------ v0.98 one call at app open
@app.get("/api/bootstrap", dependencies=[Depends(require_key)])
def bootstrap(request: Request, conv: str = "", new: bool = False, incognito: bool = False,
              tenant: str = Depends(current_tenant)):
    """Everything the app needs to open, in one round trip (it used to wait for 8 calls one after another): server
    health, the chat to use (hers if still valid, else a new one), account, lists, routines, avatar, actions the phone
    still has to run, and this month's AI spend vs her limit."""
    out: dict = {"health": healthz()}
    cid = ""
    if conv:
        with session() as s:
            c = s.get(Conversation, conv)
            if c is not None and c.tenant_id == tenant:
                cid = c.id
    from . import convs
    if not cid and not new:
        cid = convs.current(tenant)    # v0.158 sign-in / re-install / cleared app: her last chat, not an empty new one
    out["conversation_id"] = cid or create_conversation(tenant, incognito=incognito)["id"]   # v0.250 incognito new chat
    out["conversation_new"] = not cid
    from .fence import is_incognito
    out["incognito"] = is_incognito(out["conversation_id"])
    convs.mark(tenant, out["conversation_id"], "app")
    for key, fn in (("me", lambda: api_me(request)), ("lists", lambda: get_lists(tenant)),
                    ("routines", lambda: get_routines(tenant)["routines"]), ("avatar", lambda: avatar_get(tenant)),
                    ("pending_actions", lambda: pending_actions(tenant)["actions"])):
        try:
            out[key] = fn()
        except Exception as e:      # one part failing must not stop the app from opening
            log.warning("bootstrap %s failed: %s", key, e)
            out[key] = None
    try:
        from . import usage
        st = usage.state(tenant)
        inr = usage.usd_inr()
        out["usage"] = {"spent_inr": round(st["spent_usd"] * inr, 2), "limit_inr": round(st["limit_usd"] * inr, 2),
                        "pct": st["pct"], "warn": st["warn"], "over": st["over"]}
    except Exception:
        out["usage"] = None
    return out