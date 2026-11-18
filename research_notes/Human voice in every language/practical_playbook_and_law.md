# Practical playbook and law: making a live Gemini Live voice call sound more human

Researched 11 Nov 2026. Primary sources were preferred: Google AI Studio docs, OpenAI and ElevenLabs docs, the FCC, MeitY / PIB. Where only law-firm or vendor commentary was found, it is labelled. Some ai.google.dev pages now redirect (301) to aistudio.google.com/docs/..., and the links below use the new addresses.

## 1. Gemini Live API specifics (models, voices, affective dialog, proactive audio, thinking, language, VAD, compression, resumption, Google best practice)

### Takeaway
The current Live models (Gemini 3.8 Live / 3.8 Live Extended Thinking) set several "human" controls themselves. Affective dialog has been removed, proactive audio is always on, and the native-audio models choose the output language automatically, with no explicit language code. That leaves four main levers: the voice choice, the system instruction, the VAD tuning, and session plumbing (compression plus resumption). The Hoola codebase already follows the 3.x affective rule (CLAUDE.md, "never send enable_affective_dialog to a 3.x live model").

### Cited Findings
- Native-audio Live models listed on the capabilities page: `gemini-3.8-live`, `gemini-3.8-live-extended-thinking`, `gemini-3.1-flash-live-preview`, `gemini-2.5-flash-native-audio-preview-12-2025` — [Google AI Studio: Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities)
- Affective dialog (`enable_affective_dialog`) needs `v1beta`. It is supported only on Gemini 2.5 Flash Live. It has been removed from 3.8 Live and 3.8 Live Extended Thinking, where the field should be omitted, and it is not supported on 3.1 Flash Live Preview — [Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities)
- Proactive audio (`proactivity.proactive_audio`) is always on for 3.8 Live and 3.8 Extended Thinking, and setting it to false returns an error. It is configurable on 2.5 Flash Live and not supported on 3.1 Flash Live Preview — [Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities)
- Thinking settings by model:
  - 3.8 Live does not accept `thinkingLevel`; omit it.
  - 3.8 Live Extended Thinking accepts `low`, `medium` or `high` (not `minimal`), with `includeThoughts` for thought summaries.
  - 3.1 Flash Live Preview accepts `minimal`, `low`, `medium` or `high`, and defaults to `minimal`.
  - 2.5 uses `thinkingBudget`.
  - Source: [Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities)
- Language: the Live API supports 99 languages by BCP-47 code. Native-audio output models pick the language automatically, do not accept an explicit language code, and can be restricted through the system instruction — [Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities). Google's best-practice page says to state the output language in the system prompt and require the model to answer in it "unmistakably" — [Live API best practices](https://aistudio.google.com/docs/live-api/best-practices)
- VAD (`realtime_input_config.automatic_activity_detection`):
  - Fields: `disabled` (default False), `start_of_speech_sensitivity` (e.g. `START_SENSITIVITY_LOW`), `end_of_speech_sensitivity` (e.g. `END_SENSITIVITY_LOW`), `prefix_padding_ms` and `silence_duration_ms`.
  - The page recommends a `silence_duration_ms` of 500–800 ms, with a server default of about 800 ms, and warns that very low values (its example uses 100) can split one utterance into several.
  - `prefix_padding_ms` = 0 can clip the start of words.
  - Source: [Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities)
- Audio formats: input is raw 16-bit little-endian PCM at 16 kHz (`audio/pcm;rate=16000`), and other input rates are resampled. Output is 24 kHz. Native-audio models have a 128k-token context window — [Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities)
- Prebuilt voices (30, with Google's descriptors): Zephyr (Bright), Puck (Upbeat), Charon (Informative), Kore (Firm), Fenrir (Excitable), Leda (Youthful), Orus (Firm), Aoede (Breezy), Callirrhoe (Easy-going), Autonoe (Bright), Enceladus (Breathy), Iapetus (Clear), Umbriel (Easy-going), Algieba (Smooth), Despina (Smooth), Erinome (Clear), Algenib (Gravelly), Rasalgethi (Informative), Laomedeia (Upbeat), Achernar (Soft), Alnilam (Firm), Schedar (Even), Gacrux (Mature), Pulcherrima (Forward), Achird (Friendly), Zubenelgenubi (Casual), Vindemiatrix (Gentle), Sadachbia (Lively), Sadaltager (Knowledgeable), Sulafat (Warm). The voice is set with `speech_config.voice_config.prebuilt_voice_config.voice_name`. This list comes from the TTS page; the Live page points to it rather than repeating it — [Google AI Studio: Speech generation](https://aistudio.google.com/docs/speech-generation); [Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities)
- The 3.8 Flash TTS models support 21 Indian languages, including Hindi, Marathi, Bangla, Gujarati, Kannada, Malayalam, Odia, Punjabi, Tamil, Telugu, Bhojpuri and Maithili. This applies to the TTS models; it was not confirmed for Live voices — [Speech generation](https://aistudio.google.com/docs/speech-generation)
- TTS style advice that also helps when writing Live persona text:
  - Accent, gender and age belong to the voice choice, not the style.
  - Keep style prompts short.
  - Instructions like "keep the voice steady" can increase drift.
  - Pace and rhythm come from punctuation (commas, dashes, ellipses).
  - Source: [Speech generation](https://aistudio.google.com/docs/speech-generation)
- Context window compression: `contextWindowCompression: { slidingWindow: {} }`. Without it, audio-only sessions are capped at 15 minutes (audio+video at 2 minutes); with it, sessions can run without a time limit. A single connection lasts about 10 minutes — [Google AI Studio: Session management](https://aistudio.google.com/docs/live-api/session-management)
- Session resumption: send `sessionResumption: { handle }`. The server returns `SessionResumptionUpdate` messages with `resumable` and `newHandle`. A handle stays valid for 2 hours after the session ends. A `GoAway` message with `timeLeft` arrives before the server cuts the connection — [Session management](https://aistudio.google.com/docs/live-api/session-management)
- Google's best-practice recommendations:
  - One system instruction per agent, ordered persona → conversational rules → tool-call flow → guardrails.
  - A persona with a name, a role and traits. If an accent is specified, also specify the output language.
  - Each tool-call step in its own sentence, with explicit conditions for when to call it.
  - Concrete if-then guardrails.
  - A starting prompt so the agent greets first.
  - Audio sent in 20–40 ms chunks without buffering about one second, and mic audio resampled from 44.1/48 kHz to 16 kHz.
  - The client playback buffer cleared at once on `interrupted: true`.
  - Context compression and resumption enabled.
  - `generationComplete` used to tell when a turn has finished.
  - Audio accumulates about 25 tokens per second, and every turn re-bills the accumulated context.
  - Source: [Live API best practices](https://aistudio.google.com/docs/live-api/best-practices)

### Inferences
- On 3.8 Live, the remaining levers for sounding warmer or more human are the voice, the persona text, VAD timing and interruption handling. Affective and proactive behaviour are not tunable.
- For a Hinglish product, the language lock has to be done in the system instruction (as Hoola already does by locking calls to en-IN / Hinglish rules), because native audio rejects an explicit language code.
- A `silence_duration_ms` near the low end of 500–800 makes replies feel snappier but cuts in on slow speakers. A careful A/B on real calls is warranted; this is untested here.
- Clearing the playback buffer on `interrupted` is the single biggest cue that the agent is "listening like a person". If the client does not do this, it talks over the caller.

### Gaps
- No Google page found lists which prebuilt voices sound best in Hindi or Indian languages in Live, or whether Live supports the "Extended Voice Library" / Voice design voices mentioned on the TTS page.
- The exact `ContextWindowCompressionConfig` field names (trigger tokens, target tokens) were not on the session page. Check the API reference.
- No Google document was found that names a dedicated "natural voice agent" guide beyond the best-practices page.

## 2. Prompting for speech (persona, spoken-form rules, fillers and backchannels, emotion steering)

### Takeaway
All three vendors agree on the main points:
- Use a labelled, sectioned prompt.
- Define the tone once.
- Keep turns short, about 2–3 sentences.
- Write numbers and codes in spoken form.
- Add an explicit variety rule, because models over-copy sample phrases.
- Use one short "action" line before a tool call instead of filler like "Hmm".

### Cited Findings
- OpenAI recommends labelled sections (Role & Objective, Personality & Tone, Tools, Instructions/Rules, Conversation Flow, Safety & Escalation), short bullets, and capitalising key rules. It says to "Pin output to a target language if you see unwanted language switching" and to "Add a Variety rule to reduce robotic phrasing". It warns that the model follows sample phrases very closely. It also found that saying "unintelligible" instead of "inaudible" improved handling of poor audio — [OpenAI Realtime prompting guide (cookbook)](https://developers.openai.com/cookbook/examples/realtime_prompting_guide)
- OpenAI's current voice-prompting guide gives these rules:
  - Preambles are one short sentence that describes the action ("I'll check that order now"). Avoid "Let me think..." or "Hmm...".
  - Replies run 2–3 sentences per turn.
  - Money is spoken in full ("$45.20" → "forty-five dollars and twenty cents").
  - Codes are read character by character (4-1-5).
  - Ask the caller to spell an email address.
  - Mark sample phrases as examples only: "DO NOT ALWAYS USE THESE EXAMPLES, VARY YOUR RESPONSES".
  - "Do not infer language from accent alone".
  - "Ignore short filler sounds, backchannels, and isolated foreign words" when detecting the language.
  - The `speed` parameter changes playback rate only; pacing comes from instructions.
  - Emotion can be steered within a response ("Start your response very happy... Midway, change to sad"), and a steady brand tone can be set with phrasing like "Warm, concise, confident, never fawning".
  - Source: [OpenAI voice prompting guide](https://developers.openai.com/api/docs/guides/voice-prompting)
- ElevenLabs recommends:
  - Separate markdown sections, with tone defined once.
  - "Keep every instruction short, clear, and action-based".
  - A dedicated `# Guardrails` section.
  - Admitting uncertainty instead of guessing.
  - Its FAQ says prompts over 2000 tokens raise latency and cost.
  - Number and symbol normalisation either through the system prompt (no added latency, but the model sometimes fails) or through ElevenLabs' post-generation normaliser (more reliable, with minor added latency).
  - The expected format, with an example, placed in tool parameter descriptions (for emails and similar values).
  - A timeout line: "This is taking longer than expected. I can escalate to a specialist or try again."
  - Source: [ElevenLabs Agents prompting guide](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide)
- Google: the persona has a name, role and traits; guardrails are if-then; output language is stated "unmistakably" — [Live API best practices](https://aistudio.google.com/docs/live-api/best-practices)

### Inferences
- For Hinglish, the same spoken-form rules translate directly: "₹1,249" → "baarah sau unchaas rupaye", OTP and PNR codes digit by digit, dates as "das November". This is an inference from the vendor rules; no vendor document covers Indian numerals.
- Backchannels ("haan", "achha") should be allowed through, but the model must be told not to treat them as a language switch or a turn.
- None of the vendor documents recommends injecting scripted disfluencies ("um") into a speech-to-speech model. OpenAI explicitly advises against filler. Treat "add ums" ideas with suspicion.

### Gaps
- No vendor document was found with Hindi or Indic-specific spoken-form rules, or evidence that backchannel prompting measurably raises perceived naturalness.

## 3. Audio pipeline (AEC, noise suppression, sample rates, jitter, client VAD, WebRTC vs WebSocket, PSTN)

### Takeaway
The most audible "robotic" effects come from the transport and the client, not the model:
- echo that triggers false interruptions,
- buffered audio,
- audio left playing after an interruption.

WebRTC gives built-in echo cancellation, noise suppression and jitter and packet-loss handling. A raw WebSocket stream does not, so a WebSocket client has to supply echo cancellation itself, for example through the platform's own voice-communication audio mode. This is an inference; check what the Hoola Android VoiceAudio path already does.

### Cited Findings
- Pipecat says browser echo cancellation is part of the WebRTC stack and "not available to arbitrary WebSocket streams". It recommends WebRTC when you need built-in echo cancellation, noise reduction or network resilience at scale — [Pipecat: Choosing a transport](https://docs.pipecat.ai/client/concepts/choosing-a-transport)
- LiveKit says WebRTC has acoustic echo cancellation built into browser and native SDKs and handles packet loss and jitter without stalling. This is a vendor claim — [LiveKit: Why WebRTC beats WebSockets](https://livekit.com/blog/why-webrtc-beats-websockets-for-voice-ai-agents)
- Echo cancellation subtracts the agent's own output from the mic signal, which prevents feedback loops and false barge-in — [Stream: WebRTC for AI voice](https://getstream.io/blog/webrtc-ai-voice-video/) (vendor)
- Most real-time apps use WebRTC for media and WebSockets for session control — [Daily: WebSockets and WebRTC](https://www.daily.co/videosaurus/websockets-and-webrtc)
- Gemini wants 16 kHz PCM input and returns 24 kHz output. Send 20–40 ms chunks, do not buffer about one second, and clear playback on interrupt — [Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities); [Live API best practices](https://aistudio.google.com/docs/live-api/best-practices)

### Inferences
- On Android, opening the mic in voice-communication mode turns on the platform's echo cancellation and noise suppression. This is the WebSocket-app equivalent of WebRTC's built-in AEC. It is well known but not verified from an Android doc in this session.
- A phone-network (PSTN) leg is narrowband, typically 8 kHz, which makes any voice sound less natural than the 24 kHz output. Not sourced here.

### Gaps
- No independent latency benchmark comparing WebRTC and WebSocket for Gemini Live was found; every source was a vendor.
- PSTN codec limits and their effect on perceived humanness were not sourced in this pass.

## 4. Hiding latency while a tool or LLM backend works (filler lines; one voice)

### Takeaway
Industry guidance is to have the same realtime voice say one short, varied action line ("checking that now") and then call the tool straight away, and to give a plain-language timeout line if the work runs long. Pre-rendered clips from a different TTS create the "different voice" effect. Hoola already removed these in v0.625 (EK AWAAZ) and kept fillers inside Gemini Live's own voice.

### Cited Findings
- "Before any tool call, say one short line like 'I'm checking that now.' Then call the tool immediately." Keep it to one short sentence that describes the action, with varied wording — [OpenAI voice prompting guide](https://developers.openai.com/api/docs/guides/voice-prompting)
- gpt-realtime-2 generates preambles by default. Test that default before tuning — [OpenAI voice prompting guide](https://developers.openai.com/api/docs/guides/voice-prompting) (per search summary)
- Timeout wording and smaller specialised prompts reduce latency — [ElevenLabs prompting guide](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide)
- Google: describe each tool step and its trigger conditions explicitly. The model does best on single function calls — [Live API best practices](https://aistudio.google.com/docs/live-api/best-practices)
- Project context: CLAUDE.md records that v0.625 turned off pre-rendered acknowledgement clips because a separate TTS made the voice sound like "radio, different voices", and v0.298 turned off the generated "breath". Both confirm the one-voice rule from Hoola's own calls.

### Inferences
- Gemini Live's NON_BLOCKING tool behaviour (already used per v0.229) is the right way to let the voice keep talking while the brain works. Combine it with a single spoken action line and a progress line at roughly 150 s (Hoola's `_still_working`).

### Gaps
- No Google document was found that states a recommended filler or preamble pattern for Live specifically.

## 5. Law and ethics: human-sounding AI voices and cloning

### Takeaway
Four rules shape what the product may do:
- **EU (in force since 2 Aug 2026):** a voice agent must say it is AI at the first interaction, in a way the caller can actually perceive, and an agent must also say on whose behalf it acts.
- **US:** an AI-voice call is an "artificial voice" under the TCPA, so it needs prior consent. Tennessee's ELVIS Act makes unauthorised voice imitation actionable, including against tool makers.
- **India (since 20 Feb 2026):** amended IT Rules require a "prominently prefixed audio disclosure" on synthetic audio, and the DPDP Rules' consent-notice duties start around May 2027.
- **Cloning:** best practice is "own voice only plus a live verification" (ElevenLabs), together with a watermark such as SynthID.

### Cited Findings
- **EU AI Act Article 50(1):**
  - Providers of systems that interact directly with people (chatbots, agents, voice assistants) must tell users they are dealing with AI, unless it is obvious to a reasonably well-informed user.
  - The Commission guidelines say disclosure is due at the latest on first interaction and must be perceivable. Terms and conditions or generic statements do not count.
  - Agents must disclose both their AI nature and the person they act for.
  - The "obvious" exception is read narrowly, especially where children, elderly people or people with disabilities may be in the audience.
  - Source: [Paul Weiss memo](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content) (law-firm summary)
- **EU Article 50(2) and 50(4):**
  - 50(2): synthetic audio must be machine-readably marked. Voice cloners are potentially caught.
  - 50(4): deepfake audio must be disclosed. The Code of Practice requires an audible disclaimer where a visual one is impossible.
  - Article 50 applies from 2 Aug 2026. The Omnibus defers 50(2) for systems already on the market to 2 Dec 2026, and detection interoperability to 2 Feb 2027.
  - Fines are up to €15M or 3% of worldwide turnover.
  - Sources: [Paul Weiss](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content); background in [artificialintelligenceact.eu guide](https://artificialintelligenceact.eu/transparency-rules-article-50/). Some commentators disagree on whether legacy systems get any transition — [Mishcon](https://www.mishcon.com/news/ai-act-transparency-obligations-code-of-practice-and-draft-guidelines)
- **US FCC:** Declaratory Ruling FCC 24-17 (8 Feb 2024, CG Docket 23-362) confirmed that the TCPA's "artificial or prerecorded voice" covers AI voice cloning, so such calls need prior consent. It followed the fake-Biden New Hampshire robocalls. It is not a blanket ban — [FCC](https://www.fcc.gov/document/fcc-makes-ai-generated-voices-robocalls-illegal); [Orrick](https://www.orrick.com/insights/2024/02/Did-the-FCC-Really-Ban-AI-Generated-Voice-Calls-No-But-Restrictions-Apply)
- **Tennessee ELVIS Act (effective 1 July 2024):**
  - Adds voice to Tennessee's right-of-publicity law.
  - Creates liability for making a simulated voice without consent, and for providing tools whose purpose is to make one.
  - Exempts parody, satire and fleeting uses.
  - Source: [Skadden](https://www.skadden.com/insights/publications/2024/04/tennessee-law-addresses-proliferation-of-deepfakes); [Covington](https://www.covingtonblogs.com/2024/04/02/tennessee-enacts-legislation-to-protect-musicians-from-ai-generated-voice-impersonations/)
- **India IT Amendment Rules 2026:**
  - Notified 10 Feb 2026, in force 20 Feb 2026 (one source said 15 Nov 2025; treat that as an error).
  - "Synthetically generated information" means audio or visual content that appears real and is indistinguishable from a natural person or real event. Text-only content and good-faith editing or accessibility tools are excluded.
  - Intermediaries that enable SGI must label visual SGI prominently and give audio SGI a "prominently prefixed audio disclosure".
  - Takedown windows were cut to 3 hours for orders and 2 hours for non-consensual intimate imagery.
  - The draft's 10% watermark size rule was dropped.
  - Sources: [Khaitan & Co](https://www.khaitanco.com/thought-leadership/MeitY-notifies-the-IT-Amendment-Rules-2026); [Business Today](https://www.businesstoday.in/technology/story/govt-tightens-rules-on-ai-generated-content-mandates-labels-and-faster-takedowns-515505-2026-02-10)
- **India DPDP Rules 2025:**
  - Notified 13 or 14 Nov 2025 (sources differ).
  - Rules 3 and 5–16, including notice and consent, apply 18 months after publication, about May 2027.
  - Consent-manager registration (Rule 4) applies later: one source says one year after publication, another says on a date still to be notified.
  - The consent notice must be separate, clear, and state the specific purpose.
  - Sources: [PIB explainer PDF](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf); [SCC Online](https://www.scconline.com/blog/post/2025/12/26/digital-personal-data-protection-rules-2025-key-highlights/)
- **Cloning consent practice:**
  - ElevenLabs lets you make a Professional Voice Clone only of your own voice: "Even with their consent, you cannot clone someone else's voice."
  - Verification uses voice-captcha technology. The speaker reads a specific statement.
  - Instant clones need a consent attestation.
  - Sources: [ElevenLabs help](https://elevenlabs.io/docs/help-center/product/voices/voice-cloning/can-i-create-a-professional-voice-clone-of-someone-elses-voice.md); [ElevenLabs voice cloning API docs](https://elevenlabs.io/docs/eleven-api/concepts/voice-cloning)
- **Watermarking:**
  - Google's SynthID marks Lyria and NotebookLM audio by embedding the watermark in the spectrogram.
  - The Gemini app can check a clip for a SynthID mark.
  - The audio detector is proprietary; only the text watermark is open source.
  - A secondary source claims Live Translate speech is also marked; this is unconfirmed in Google's own docs.
  - Sources: [Google DeepMind SynthID](https://deepmind.google/technologies/synthid/); [ElevenLabs help: audio detector](https://elevenlabs.io/docs/help-center/legal/audio-detector/how-can-i-check-whether-a-piece-of-audio-was-generated-by-eleven-labs)

### Inferences
- **Product rule (safe everywhere):** the avatar says in its first spoken line that it is the owner's AI assistant, and names on whose behalf it acts. This meets EU 50(1) and India's "prefixed audio disclosure" in spirit. For the owner's own calls with her own avatar, disclosure is arguably "obvious". For calls to third parties, such as other businesses or Hoola Network outreach, it is not.
- Any outbound call to a US number with an AI voice needs prior consent under the TCPA.
- Voice cloning for avatars should be limited to the user's own voice, with a live read-aloud check, plus a watermark. This matches Hoola's existing consent stance in HOOLA VOCAL / Interactive.
- Whether India's IT Rules apply to a live one-to-one call, as opposed to published content, is unsettled. The rules target intermediaries and hosted content. A conservative reading still favours a spoken disclosure.

### Gaps
- No FCC follow-up rulemaking on AI-call disclosure was confirmed in this pass (CG Docket 23-362 status unknown).
- Other US state voice laws (e.g. California, the proposed federal NO FAKES Act) were not checked.
- No primary source was found on whether Gemini Live output carries SynthID or C2PA.
- C2PA support for audio was not verified.
- Indian personality-rights case law on voice (Delhi or Bombay High Court orders) was not covered here.
