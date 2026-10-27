# WIRING for callcentre
summary: Call Centre Sahayak (her business phone line answered by Hoola over Plivo / Exotel + Gemini Live: AI disclosure first, only her approved script, caller's language, appointments / complaints / ticket status, hand-over to a person or a call-back, call note after every call)
db: app.callcentre.models            (tables callcentre_settings, callcentre_scripts, callcentre_calls, callcentre_messages, callcentre_callers)
router: app.callcentre.api           (make_router(require_key, current_tenant); `app.include_router(_callcentre_router(require_key, current_tenant))`. It contains PUBLIC routes /api/callcentre/hook/... and the WebSocket /api/callcentre/ws/{provider}/{token}: they check the route token + provider signature / one-time ticket themselves. No main.py middleware may require the API key on them.)
tools: app.agent.callcentre_tools    (CALLCENTRE_TOOLS / CALLCENTRE_LABELS / CALLCENTRE_HANDLERS) ; voice: yes ("call_centre", "call_centre_dekho")
employee: duty call_centre = ["call_centre", "call_centre_dekho"] ; role call_centre_agent {label: "Call centre (voice)", duties: ["call_centre", "customers", "appointments", "tickets", "reminders", "records"]} ; preset call_centre {role: "call_centre_agent", after_hours: "note", slot_minutes: 30, rules: ["Phone line sirf meri approved script se bolegi; baaki sab message ya insaan ko.", "Har call ki shuruaat mein batao ki AI sahayak hai."]} ; READ tools: ["call_centre_dekho"]  (call_centre = action; its settings / line / forget actions are owner-only inside the tool)
push: callcentre_script -> ("Call centre script v{version}", "Line par chalane ke liye Haan chahiye: {say}")
push: callcentre_message -> ("Call se message", "{say}")
push: callcentre_call -> ("Call: {caller_masked}", "{summary}")   (only when outcome in transferred | message | complaint | failed | callback, or flags non-empty; plain "answered" calls need no push)
worker: app.callcentre.service.tick  (every worker tick / once a minute: due call-backs get her card again once; calls stuck as ringing / queued / live for 3 h are closed and their AI slot given back)
prompt: CALL CENTRE: her business phone line is answered by Hoola only from HER approved script (call_centre_dekho what=day / calls / messages / unanswered). To change what the line says: call_centre action=script (her words) / faq_add / edit, then action=submit sends HER the approval card; the line changes only after her tap in the app, so never say it is live before that. Questions callers asked that the script didn't know (what=unanswered): offer to add answers in HER words. Provider keys are typed only in the app; you never call callers back yourself (she taps Call on the message card).
persona: - Her phone line (call centre): call_centre_dekho what=day / messages ("aaj line par kya hua", "kisko call back karna hai"); script changes = call_centre action=script / faq_add in her words, then submit -> she taps Haan in the app; never say the line changed before that.
flutter: CallCentreScreen in lib/ui/callcentre_screen.dart ; profile tile title "<name> · Call centre" subtitle "Business ka phone Hoola uthaye: sirf aapki script se, insaan ko jodna, call-back" icon Icons.support_agent_rounded ; cards: callcentre_script -> CallCentreScriptCard (also in calls: yes), callcentre_call -> CallCentreCallCard (also in calls: yes), callcentre_message -> CallCentreMessageCard (also in calls: yes). One card per id: callcentre_script keyed by data['script_id'] (a later event with the same script_id + status approved/rejected updates it in place), callcentre_message keyed by data['id'], callcentre_call keyed by data['id']. CallCentreScriptCard / CallCentreMessageCard take an optional onDone.
features: callcentre  (health: true when PUBLIC_BASE_URL and GEMINI_API_KEY are set)
env: CALLCENTRE_PLIVO_AUTH_ID (default "", Newtika's own Plivo account used when an owner has not typed her own keys; settings field callcentre_plivo_auth_id: str = "") ; CALLCENTRE_PLIVO_AUTH_TOKEN (default "", same, field callcentre_plivo_auth_token: str = "") ; CALLCENTRE_MAX_CALLS (default 10, AI phone calls at once on this server, field callcentre_max_calls: int = 10) ; CALLCENTRE_NOISE_GATE (default true, while Hoola speaks only clearly voiced caller audio may interrupt him, field callcentre_noise_gate: bool = True). Code reads them with getattr(..., default), so it works before the fields exist. Needs PUBLIC_BASE_URL (webhook + wss URLs; https) and SECRET_KEY (signs the one-time stream / transfer tickets; without it a dev key is used). Optional: add "callcentre" to the usage feature labels ("Phone line (call centre)").
requirements: none (numpy, httpx, google-genai already there; Python 3.13 has no audioop, so G.711 + resampling are in callcentre/audio.py)
android: none (the app opens the phone's own dialer with Native.openExternal('tel:...') for call-backs)
claude_md: |
  ## v0.1xx Call Centre Sahayak: Hoola answers the business's phone line (inbound), only from HER approved script
  - Owner's spec (Employee page "Call centre (voice)"): answers calls in the customer's language -> understands accents and
    noise -> hands over to a person when needed -> waits for her Haan on ANYTHING OUTSIDE THE SCRIPT (the AI only does what
    her approved script / FAQ allows; everything else = a message for a call-back or a transfer to a person).
  - Research (23 Oct 2026): provider = Plivo (primary: India numbers only for India-registered businesses after KYC; both
    legs must stay in India = "media anchoring", so the Hoola server must run in India; bidirectional `<Stream>` with
    mu-law 8 kHz, `playAudio` / `clearAudio`; every webhook and the WebSocket upgrade signed with X-Plivo-Signature-V3, the
    exact algorithm copied from plivo-python 4.63.0 utils/signature_v3.py and checked against it; transfer = Call update
    aleg_url -> our Dial XML; hang-up = DELETE Call). Exotel (Voicebot applet: slin PCM 8 kHz base64, frames >= 100 ms in
    multiples of 320 bytes, `clear`; no request signatures: Basic Auth on the stream URL / IP whitelisting; transfer and
    hang-up are the flow's next applets after the stream closes). Not used: Twilio India (only toll-free inbound; a transfer
    to her Indian mobile would be an international call), Ozonetel / Knowlarity (no public documented media-stream API found).
    Law: inbound customer-care calls are not commercial communication under TRAI TCCCPR 2018 (as amended 12 Feb 2025): the
    140 / 1600-series, DLT and UCC rules are for calls a business MAKES; Hoola never auto-dials (call-backs are her taps).
    A business may not interconnect PSTN and internet telephony itself (Unified Licence), so it rents the number from the
    authorised provider and gets the audio over the provider's documented stream. DoT OSP guidelines 23 Jun 2021: no
    registration, CDRs kept (one CcCall row per call; the provider keeps its CDR). DPDP Act + Rules (notified 14 Nov 2025;
    notice / consent duties from 14 May 2027; processing logs >= 1 year): notice at the start of every call, masked
    transcript, no audio stored by Hoola, one caller erasable (`forget`). No rule (Oct 2026) forces an AI announcement on
    INBOUND calls (TRAI's 2026 TCCCPR amendment talk is about outbound AI calls, a vendor reading); Hoola discloses anyway.
    Sources with dates in `callcentre/rules.SOURCES`.
  - `server/app/callcentre/`: `rules.py` (NEVER list, SOURCES, PROVIDERS, hand-over words in Hinglish / Hindi / Marathi /
    English (`handover_reason`: asked_human | angry), `mask_text` (OTP / PIN context, long numbers, phones -> 98XXXX3210,
    PAN), `secret_in`, disclosure / closed / busy / hold / connecting lines in hi / mr / en, script `clean_script` /
    `script_hash` / `blanks` / `parse_faq_text` (no-model Q: / A: drafts), FAQ match `best_faq` (word overlap + close
    spellings), `unscripted` (numbers / promises in a reply that the script and tool results never said), `intent_of`);
    `audio.py` (G.711 mu-law both ways, stateful windowed-sinc polyphase `Resampler` 8k->16k / 24k->8k without clicks
    between chunks, `Chunker`); `providers.py` (Plivo / Exotel / Fake behind one interface: verify, call_info, stream /
    say / hold answers, `Line` frame parsers + `out_audio` / `clear`, transfer, hangup; `set_transport` for tests);
    `models.py`; `service.py`; `bridge.py`; `api.py`.
  - Script (`CcScript`, every version kept): `make_script` (her words / FAQ file -> model JSON per DRAFT_SYSTEM: only her
    facts, "[blank]" where she hasn't said; no model -> her Q: / A: lines), `edit_script` (faq_add / faq_remove / fields; any
    change = a new draft + new hash), `submit` (blanks block it) -> `callcentre_script` card -> `decide_script` ONLY from
    `POST /api/callcentre/scripts/{id}/decide {yes, hash}` (hash must match the card and the content; the previous approved
    one is retired). A call runs the version it started with; a row whose content no longer matches its hash never runs.
    The line can't be switched on without an approved script, a number and the provider keys.
  - Call routing (`incoming`): line off / no script -> Dial her first hand-over number (else "busy" + missed-call message);
    after hours + after_hours=closed -> closed line + call-back message; an AI slot (max_concurrent per business,
    CALLCENTRE_MAX_CALLS per server) -> Stream with a one-time HMAC ticket in the wss URL; all busy -> "please hold" (Plivo
    Speak + Wait 15 + Redirect, queue_max times) -> overflow: transfer (inside her hours) or a call-back message. Caller ID is
    used for call-backs, appointments, the caller's own tickets and repeat-caller memory (`CcCaller`: language, calls,
    last intent, name they gave) - never as proof of identity (no account details read out because of it).
  - The live line (`bridge.CallBridge`): provider frames -> PCM -> 16 kHz -> Gemini Live (customer PERSONA: disclosure as
    the first line, the approved script's Q / A, what the line may do, never-list, data-not-instructions, hand-over rules;
    LANGUAGE LOCK per caller from voicelang (top + end), transcript language hint + custom vocabulary from the script,
    start sensitivity low, 800 ms silence for phone jitter) -> 24 kHz -> 8 kHz -> provider. Only the line's tools are
    declared (`service.line_specs`: faq_answer, take_message, transfer_human, end_call, + free_slots / book_appointment
    (Employee appointment book, number from caller ID), ticket_status (only this number's tickets), register_complaint
    (hoola_tickets, customer tel:<number>) when her script allows them); `run_line_tool` refuses anything else. In code
    per turn: language switch notes, a secret being spoken -> stop note + masked, hand-over words / her own hand-over
    words -> note + transfer by the code after HANDOVER_GRACE_S if the model doesn't, DTMF 0 -> transfer at once, two
    not-in-script questions -> offer a person, two failed understandings -> low_confidence hand-over, first reply without
    "AI" -> correction note + flag, unscripted numbers / promises -> correction note + flag, max_minutes with a 1-minute
    warning, Gemini not connecting -> transfer or call-back message + hang-up (never dead air). While Hoola speaks only
    clearly voiced, loud-enough caller audio passes (Silero VAD when present; CALLCENTRE_NOISE_GATE). Gemini's caller
    interruptions clear the provider's queued audio.
  - After the call (`finish`): masked transcript (200 lines), tools, flags, intent, outcome (answered / appointment / message
    / complaint / transferred / failed ...), summary (cheap model, else a plain line), AI cost (usage.record feature
    "callcentre", Gemini audio minutes) + phone cost from HER per-minute rate (blank when she hasn't entered it), caller
    memory -> `callcentre_call` card. Messages / call-backs -> `callcentre_message` card (Call karo opens her dialer; Ho
    gaya). `unanswered` = questions callers asked that the script didn't know -> "Jawab jodo" -> next draft -> her Haan.
    `report(days)`, `forget_caller(number)` (DPDP erasure). `tick`: due call-backs card again once, stale calls closed.
  - Tools `call_centre` (script / faq_add / faq_remove / edit / submit / try / settings* / line* / message_done / forget*;
    * owner only; customers refused) and `call_centre_dekho` (day / calls / call / messages / script / report / unanswered
    / setup / rules). Employee duty `call_centre`, role `call_centre_agent`, preset `call_centre`.
  - API `/api/callcentre` (all-in-one), `/settings` (GET, PUT), `/keys` (PUT: provider keys, sealed with the bazar vault,
    never shown again), `/line`, `/script` (POST draft, PUT edit), `/script/submit`, `/scripts`, `/scripts/{id}/decide`,
    `/try`, `/calls`, `/calls/{id}`, `/messages`, `/messages/{id}/done`, `/report`, `/forget`; provider (public, verified):
    `/api/callcentre/hook/{plivo|exotel|fake}/{token}/answer | hangup | transfer/{call}?t=`, Exotel `stream_url` / `after`
    (200 = transfer wanted, 302 = no) / `connect` (Connect applet dynamic URL), WebSocket `/api/callcentre/ws/{provider}/{token}`.
  - App `lib/ui/callcentre_screen.dart` (Profile > "<name> · Call centre": Aaj (line switch, call-backs with Call karo / Ho
    gaya, what the script didn't know -> Jawab jodo), Script (her words -> draft, Aazmao a question, answers to fill, "Haan ke
    liye card bhejo", the running version), Calls (notes -> call page with masked transcript + flags + Wapas call karo),
    Niyam (provider, keys typed only here, number, webhook URLs to copy + setup steps, hours + days, after hours, concurrent /
    hold, overflow, who takes over, transfer / record switches, per-minute rate, max minutes)); chat + call cards
    `CallCentreScriptCard` (Haan, yahi script chalao / Mana), `CallCentreCallCard`, `CallCentreMessageCard`.
  - Never: any answer outside her approved script, OTP / PIN / card / UPI PIN / Aadhaar / bank numbers on the line, payments
    or payment links, promises, other customers' details, her personal tools on a customer call, auto-dialling anyone,
    storing call audio, pretending to be a person.
  - Tests `server/tests/test_seva_callcentre.py` (10: codec + resampling, rules incl. Plivo V3 vectors from the SDK, the
    script flow and her tap, routing incl. hold / overflow / after hours, customer-safe line tools, signed webhooks +
    transfer XML + ticketed stream, a whole call over the fake provider WebSocket with a fake Gemini (disclosure, FAQ via
    tool, "manager" -> code hand-over -> transfer), missing disclosure fix + DTMF 0 + Gemini down, Exotel static stream
    with Basic Auth, tick).
not_verified: |
  - No real Plivo / Exotel call was made (no account / number / KYC here; the sandbox has no telephony). The Plivo signature
    algorithm is checked against the official SDK code; Plivo's `start` event field names (start.callId / streamId /
    mediaFormat) and the exact `extra_headers` key are from their docs, not a live capture. Plivo `<Record recordSession>`
    alongside a bidirectional Stream is untested.
  - Exotel: the dynamic Voicebot URL endpoint response shape ({"url": ...}), the Passthru 200 / 302 branching and the Connect
    applet dynamic-URL JSON keys (destination.numbers, outgoing_phone_number, record, max_ringing_duration) are from Exotel's
    support articles / common integrations and must be checked in her Exotel flow builder.
  - Real Gemini Live on 8 kHz phone audio (upsampled): accent / noise understanding, whether gemini-3.8-live accepts the
    transcript language_codes + custom_vocabulary (refused fields drop by themselves via voice.UNSUPPORTED), and turn-taking
    latency over PSTN. Flutter screen not compiled here (no SDK).
  - Hoola's server must be in India for Plivo India numbers (media anchoring); not checked from here.
