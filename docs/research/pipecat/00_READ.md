# Pipecat, read for Hoola's calls (21 Nov 2026)

Owner: "https://github.com/pipecat-ai/pipecat.git --- NOW READ THIS REPO" (after the Chatwoot read).
Read at commit e752543 (20 Nov 2026), shallow clone. Python framework by Daily for real-time voice / video agents.
Nothing copied into Hoola yet.

## Licence
BSD 2-Clause for the whole repo: code may be reused or the package (`pipecat-ai`) used as a library, keeping the
notice. Some plug-ins it calls are paid services (Krisp noise / turn models, every cloud STT / TTS / LLM) - free
alternatives exist in the repo (Silero VAD, RNNoise, Smart Turn v3 open model, Whisper, Piper / Kokoro TTS).

## What it is
Everything in a call is a FRAME (audio, text, interruption, tool call...) flowing through a PIPELINE of processors:
transport in -> speech-to-text -> context -> LLM -> text-to-speech -> transport out, or one speech-to-speech model
(Gemini Live, OpenAI Realtime, Ultravox) in the middle. ~70 vendors as swappable services (incl. Sarvam for Indian
languages, Deepgram, ElevenLabs, Cartesia, Gemini, Anthropic, OpenRouter, Qwen), transports WebRTC / WebSocket /
SIP / LiveKit / Daily / WhatsApp, phone serializers for Twilio, Plivo, Exotel, Telnyx, Vonage, Genesys, jambonz.

## How Hoola does calls today
- Her own calls: `voice.py` / `voice_openai.py` = one speech-to-speech model (Gemini Live; OpenAI / Grok / Phonic as
  choices), the Hoola brain behind `santosh_kaam`, news queue, parking, scorecards.
- Telecaller / customer line: `callcentre/bridge.py` = phone WebSocket (8 kHz) <-> Gemini Live, turn end = Gemini's
  own silence detection at 800 ms + Hoola's VAD gate; rules in code (says AI first, numbers checked, hand-over,
  OTP stopped, time limit). `callcentre/providers.py` = 9 phone companies.
So Hoola already has most of what a call needs. Pipecat is useful for the parts below.

## What Pipecat has that Hoola should take (in order of value)
1. **Simulated callers + a judge (`pipecat/evals/`).** A scenario = a persona ("an angry customer whose bill doubled,
   speaks Hindi") + a goal + success rules; a persona LLM holds the whole conversation with the bot by itself and
   ends the call with `end_call`; a separate judge marks each rule with a probability and the reasons; scripted
   scenarios too, re-judging saved conversations without re-running. Hoola's Telecaller, Customer Support and call
   voice are all "NOT VERIFIED with a real call" - this is how to test them every release without a phone or money
   (text mode first, audio later). Biggest gain.
2. **Turn-taking that is not just silence.** Smart Turn v3 = a small open model (ONNX, runs on the server CPU, no
   key) that hears whether the person has FINISHED speaking, not just paused - fewer "he cut me off" and fewer long
   waits than a fixed 800 ms. Also: the LLM marks each reply complete / incomplete so a half sentence waits;
   a speculation gate (start the reply early, release it only when the turn is confirmed); mute rules (no
   barge-in during the first greeting / while a tool runs).
3. **Idle vs waiting (`turns/user_idle_controller.py`, `wait_reassurance`).** Silence after the bot speaks is two
   different things: the customer is idle (gently ask "are you there?") or the customer is WAITING on background
   work (say one short "still checking" line, or stay silent - the model may answer with a silent mark). Hoola has
   only the 150 s "still working" line on her own calls; the customer line has neither.
4. **Long tools on a live call (`async_tool_messages`).** A tool marked "do not cancel on interruption" keeps
   running while talk goes on; the context gets started / progress / final notes and the model gets a cancel tool
   for each. Same idea as Hoola's santosh_kaam + news queue, but as a written protocol - good for the Support desk's
   live lookups on the phone.
5. **WhatsApp voice calls (`transports/whatsapp/`).** The WhatsApp Cloud API (official) lets a customer CALL the
   business WhatsApp number; Pipecat answers it over WebRTC. Hoola's business inbox takes WhatsApp text only. For
   India this is a large channel for the Telecaller and Customer Support - and no phone-number rental.
6. **A cascade option.** speech-to-text -> any LLM -> text-to-speech, each vendor swappable, Sarvam for Indian
   languages. Useful when Gemini Live is weak in a language, too costly per minute, or when the call must run on
   the tier's model; also gives exact transcripts and word times.
7. **Expressive (alpha).** Perception (how the person sounded - tone, speech rate) passed to the model, and
   expression tags the TTS can perform. Later, after 1-5.
8. **Smaller things:** latency observers per turn (user stopped -> bot first sound), noise filters (RNNoise free),
   DTMF aggregation, context summarizer, a SIP transport straight to a trunk, Flows (nodes with their own prompt +
   tools = Telecaller "call steps"), a multi-agent bus with jobs (Hoola has crews).

## What Hoola already does better / differently
- Rules in code on the customer line (AI said first, unsaid numbers corrected, OTP / card stopped, forced hand-over,
  time cap) - Pipecat gives the pipe, not these laws.
- Answers only from her approved knowledge; money only by her tap; India call laws (consent, hours, do-not-call).
- One memory across chat and calls, parking a quiet call to save money, scorecards per call.

## Suggested work (each needs her GO)
- V1 Call simulation card: 30 scenarios (Hindi / English / Marathi, angry / confused / asks for a person / tries to
  give an OTP / asks a refund) against the Telecaller and Support phone line in text mode, judged in code where it
  can be (said AI, handed over, no OTP, no unsaid number) + a judge model for the rest. vps-ops `call_sim_card`.
- V2 Smart Turn v3 on the customer line behind a switch, measured by V1 + real calls (cut-offs, wait time).
- V3 Idle vs waiting on both call kinds.
- V4 WhatsApp calling for the business number (official Cloud API; needs Meta to enable calling on her number).
- V5 Cascade engine option with Sarvam for Indian languages, priced per minute before use.
Decision for her: use Pipecat as a library inside the customer line, or take its ideas into Hoola's own bridge
(suggest: ideas into our bridge for V2-V3, the library only if V4 / V5 need its WebRTC + vendor services).
