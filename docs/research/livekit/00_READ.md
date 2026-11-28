# LiveKit Agents, read for Hoola's calls (21 Nov 2026)

Owner: "https://github.com/livekit/agents.git -- NOW READ THIS REPO" (after Pipecat, docs/research/pipecat/00_READ.md).
Read at commit d78f399 (20 Nov 2026), shallow clone. Python framework for real-time voice agents on LiveKit (WebRTC
rooms + SIP). Nothing copied into Hoola.

## Licence (two parts)
- The framework + ~100 plugins: Apache-2.0 - code may be reused with the NOTICE.
- LiveKit's own MODELS (the turn detector, English + multilingual): the LiveKit Model License - free, but ONLY inside
  the LiveKit Agents framework, never standalone or in another framework. RULE for Hoola: do not lift the turn-detector
  model into our bridge. (Pipecat's Smart Turn v3 is the open one we may use.)

## What it is
An AgentSession runs one call: VAD + speech-to-text + LLM + text-to-speech, or a realtime speech model, with Agents
(instructions + tools) that hand over to each other, and Tasks (small agents that collect one thing and return a
result). Runs inside a LiveKit room; phones join through LiveKit SIP. Plugins for ~100 vendors incl. Indian ones
(Sarvam STT / TTS / LLM, Gnani, Vakyam), Gemini / OpenAI realtime, Anthropic, avatars (Tavus, Simli, Anam...).

## What it has that Pipecat did not, and Hoola should take
1. **Answering-machine detection by meaning (`voice/amd`).** It listens to the first words of an outbound call and an
   LLM sorts them into human / IVR menu / voicemail (can leave a message) / mailbox full / uncertain; ringback and
   carrier early audio are ignored until the call is really answered. Hoola's Telecaller uses only the phone
   company's own machine check (not every company has one, and it misses Indian "the number you are calling..."
   messages). Add our own check on the first 3-5 s of text as a second opinion.
2. **IVR navigation (`voice/ivr`).** When a call lands on a phone menu the agent presses keys (DTMF) and a TF-IDF loop
   detector notices the menu repeating and stops. Useful for the Telecaller calling businesses, and for the PC-free way
   of reaching a bank / telecom helpline.
3. **Reply-delay that learns (`voice/endpointing.py` DynamicEndpointing).** The wait before replying moves between a
   floor and a ceiling with each caller's own pauses (a slow speaker gets more time, a quick one less). Simple maths,
   no model - an easy first step before a turn model.
4. **Fillers during long work (`filler_scheduler`) + background audio.** A short spoken filler fires while a slow
   tool runs; optional soft office / typing sound under the call. Hoola turned its own clips off (v0.625 "one
   voice"), so only model-spoken fillers, never pre-recorded ones.
5. **Ready-made collect tasks (`beta/workflows`).** Get a name, phone number, email, address, date of birth, DTMF
   digits - each a small task with confirm-back and its own result; a task group runs several in order. The customer
   line would use name / phone / address / DTMF only. Their credit-card task is the opposite of our rule: Hoola never
   takes a card number on a call - keep refusing it.
6. **Warm transfer (`warm_transfer.py`).** Before handing a caller to a person, the AI calls the person first, tells
   them the summary, and only then joins the caller in. Hoola's hand-over today is a cold transfer or a call-back.
7. **Fallback across models without dropping the call (`realtime_fallback_adapter`, `fallback_adapter`).** If the
   realtime model fails mid-call, the next one takes over with the same conversation. Hoola's customer line hands
   over to a person when Gemini fails to connect; a second model would keep the call.
8. **Keyterm biasing (`keyterm_detection`).** Names of her plans, products and places sent to the speech-to-text so
   they are heard right, and new ones picked up during a call.
9. **Tests and evals (`testing.py`, `simulation.py`, `evals/`).** Run an agent in-process with no phone; judges for
   "did it finish its task" and free instructions; a session report per call. Same idea as Pipecat's simulated
   callers - one V1 card covers both.
10. **Small:** tool search toolset (Hoola has it), session-wide tools that survive a hand-over, an end-call tool, live
    translation sessions (beta), a duplex model interface, a session report.

## What Hoola keeps (better or required)
- Rules in code on the customer line (AI said first, unsaid numbers corrected, OTP / card stopped, forced hand-over,
  time cap), India call laws, her approved knowledge only, money only by her tap - LiveKit gives none of these.
- No LiveKit server needed today: Hoola's bridge speaks to the phone companies directly. Moving to LiveKit would add
  a media server to run (or LiveKit Cloud's bill) for features we can add ourselves.

## Pipecat vs LiveKit for Hoola
Both are good; neither replaces our bridge. Take ideas from both into `callcentre/bridge.py`:
Pipecat = simulated callers, open turn model, idle vs waiting, WhatsApp calling; LiveKit = machine detection by
meaning, IVR keys + loop stop, learning reply delay, collect tasks, warm transfer, model fallback mid-call.
If one day Hoola needs rooms (several people + AI on one call, video avatars), LiveKit is the stronger base.

## Updated suggested work (each needs her GO; V1-V5 from the Pipecat note)
- V1 Call simulation card (both notes).
- V2 Learning reply delay first, then Smart Turn v3 behind a switch.
- V3 Idle vs waiting + model-spoken fillers.
- V4 WhatsApp calling.
- V5 Cascade engine with Sarvam.
- V6 Our own machine / IVR check on outbound calls (first seconds of text) + DTMF menu keys with a loop stop.
- V7 Warm transfer to her / staff, with the summary told first.
- V8 A second model taking over mid-call when Gemini fails.
