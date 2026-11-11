# What makes a live AI voice call feel human, and how to measure it

Scope: the conversation and sound features that make synthetic speech in live calls feel human, with numbers where they exist, and how researchers and companies measure "humanness". Researched 11 Nov 2026. Dates are given for every finding. Older findings (before 2023) are marked as older.

## Turn-taking: gap length, variation by language, overlap, and what latency users tolerate

### Takeaway
People answer each other fast: about 200 ms is the typical gap, and language means sit within about a quarter second of each other (Japanese about 7 ms, Danish about 469 ms; older study, 2009). Speech planning takes over 600 ms, so humans start planning the reply while the other person is still talking. Listeners begin to read a pause before a "yes" as reluctance somewhere around 600-800 ms. A typical cascaded voice agent (speech recognition, then language model, then speech synthesis) takes 1,000-1,500 ms. Full-duplex models reach about 200 ms, but they often grab the turn at the wrong moments. So the goal is speed and correct timing together, not raw speed.

### Cited Findings
- Stivers et al. (PNAS 2009, older): 10 languages on five continents, filmed conversations. Every language avoids overlap and keeps silence between turns short. Each language's mean gap falls within about 250 ms of the cross-language mean, and the same factors explain faster or slower replies in every language. — [PubMed abstract](https://pubmed.ncbi.nlm.nih.gov/19553212/); [MPI record](https://forms.mpi.nl/node/50939); [National Geographic summary](https://www.nationalgeographic.com/science/phenomena/2009/06/19/pregnant-pauses-and-rapid-fire-how-do-different-cultures-take-turns-to-talk/)
- Per-language means from that study: Japanese fastest at 7 ms, Danish slowest at 469 ms. — [altalang summary](https://altalang.com/beyond-words/taking-turns-in-conversation/). Other secondary sources give Danish as 489 ms ([arXiv 2505.24736](https://arxiv.org/pdf/2505.24736v1.pdf)) or "around 400 ms" ([Springer Nature community post](https://communities.springernature.com/posts/taking-turns-during-conversation)). I could not open the original paper to check which is right.
- The Moshi paper (Kyutai 2024) gives the average gap in natural conversation across Stivers' 10 languages as 230 ms. — [arXiv 2410.00037](https://arxiv.org/html/2410.00037v1)
- Hoogland et al. (Languages, 2023): mean gap between speakers is 199 ms in Dutch and 242 ms in English. — [doi 10.3390/languages8020115](https://doi.org/10.3390/languages8020115) (via [Deepgram](https://deepgram.com/learn/voice-ai-latency-why-pauses-read-as-hesitation))
- Sakuma et al. (Interspeech 2023): half of human response timings are under 350 ms. End-of-utterance detection plus speech recognition generally take longer than that. — [ISCA archive](https://www.isca-archive.org/interspeech_2023/sakuma23_interspeech.pdf)
- Levinson & Torreira (Frontiers in Psychology 2015, older): gaps are about 200 ms, but producing speech takes over 600 ms. Listeners therefore plan their reply while the current turn is still going and predict where it will end. — [Frontiers](https://www.frontiersin.org/articles/10.3389/fpsyg.2015.00731/full)
- Heldner & Edlund (Journal of Phonetics 2010, older): turn-taking is less precise than conversation analysts often claim, with a wide spread of gaps and overlaps across three corpora. A fixed 500 ms silence threshold, as used in many end-of-utterance detectors, caught only 51.1% of gaps in a Swedish corpus and 47.5% in the HCRC Map Task corpus, and also caught many pauses inside a single speaker's turn. — [paper PDF](https://staff.fnwi.uva.nl/r.fernandezrovira/teaching/cosp/cosp2016/docs/HeldnerEdlund2010.pdf); [bibbase](https://bibbase.org/network/publication/heldner-edlund-pausesgapsandoverlapsinconversations-2010)
- Silence carries meaning (Roberts, Francis & Morgan, Speech Communication 2006, older): in simulated phone calls, raising the silence before a reply from 0 to 600 to 1200 ms made listeners rate the speaker as less willing to agree each time. Silence length was a stronger cue than pitch. — [EMCA wiki](https://emcawiki.net/Roberts2006)
- Roberts, Margutti & Takano (2011, older): English, Italian and Japanese listeners all rated willingness significantly lower at longer silences, though the groups started from different expectations. — [EMCA wiki](https://emcawiki.net/Roberts2011)
- A German replication found willingness dropping especially above a "tolerance threshold" of about 600 ms. — [SDU record](https://portal.findresearcher.sdu.dk/en/publications/how-long-is-too-long-how-pause-features-after-requests-affect-the/). A secondary summary instead puts the drop between 700 and 800 ms ([koji.so](https://www.koji.so/docs/dispreferred-responses-interview-timing)). The exact cut-off is unsettled.
- A 2024 study with Chinese listeners (replicating a Polish one): longer pauses between turns made the responder seem less knowledgeable and less confident. — [doi 10.1075/is.24044.mat](https://doi.org/10.1075/is.24044.mat)
- Conventional cascaded voice pipelines take about 1,000-1,500 ms per turn, at least four times the human baseline (2024 estimate). — [arXiv 2404.16053](https://doi.org/10.48550/arxiv.2404.16053)
- A measured 2026 pipeline: 755 ms time to first audio, of which 296 ms was the language model's time to first token. — [arXiv 2603.05413](https://arxiv.org/html/2603.05413v1)
- Moshi (Kyutai, 2024), a full-duplex model: 160 ms theoretical latency, about 200 ms in practice. It listens and generates sound (speech or silence) at all times. — [arXiv 2410.00037](https://arxiv.org/html/2410.00037v1)
- Industry practice (vendor figures, not peer-reviewed): builders usually budget under 800 ms; one guide calls 800-1,200 ms "acceptable, slightly noticeable"; Deepgram says callers start noticing lag at about 800 ms round trip; and steady latency beats a lower average with spikes ("reliably 900 ms beats an average of 700 with spikes to 2,500"). — [Coval](https://www.coval.dev/blog/how-to-measure-voice-ai-latency-the-complete-guide); [Deepgram](https://deepgram.com/learn/voice-ai-latency-why-pauses-read-as-hesitation); [famulor](https://www.famulor.io/es/blog/ai-voice-agent-latency-how-fast-your-phone-bot-must-reply)
- Deepgram's own figures for end-of-turn detection: about 260 ms p50 at default settings, 1 s p90, 1.5 s p95. Detecting the end of a turn "eagerly" saves about 100-200 ms but costs 50-70% more language-model calls. — [Deepgram](https://deepgram.com/learn/voice-ai-latency-why-pauses-read-as-hesitation)

### Inferences
- A fixed silence timeout cannot match human timing: a 500 ms threshold misses about half of real gaps and cuts into pauses inside a turn. What is needed is an end-of-turn decision based on meaning and prosody (falling pitch, a complete clause), not silence length.
- Around 600-800 ms of silence is where a human listener starts reading meaning into it (hesitation, reluctance). A practical target is p50 time to first audio of 500 ms or less and p95 of 800 ms or less. These numbers are my inference from the studies above, not a measured standard.
- Language means differ by up to about 250 ms, so a single global timing setting will sound a little rushed in some languages and a little slow in others.

### Gaps
- I found no published gap or overlap figures for Hindi, Marathi or other Indian languages; Stivers' sample does not include them. A small measurement on Hinglish calls would be needed.
- I could not get the overall share of overlaps out of Heldner & Edlund; only the abstract and a summary were available.
- I found no peer-reviewed study that measures the latency at which users abandon a voice agent. The 800 ms figure is an industry heuristic.

## Backchannels, fillers, breaths, laughter and pauses: which help and which hurt

### Takeaway
Correct timing is what helps. Backchannels at the right moments ("hmm", "haan", "accha") look more human, while random timing or the wrong rate hurts. Filled pauses ("um", "uh") make a voice sound more authentic and less certain, without a significant loss of naturalness. Sesame's well-received demo deliberately uses breaths, pauses and self-corrections. Reports of "it felt human" are mostly secondary coverage.

### Cited Findings
- Backchannel perception study (University of Twente, "Backchannels: quantity, type and timing matters"): backchannels at their originally performed times and types seemed more human-like than swapped types or random timing. Too few or too many per minute lowered perceived quality. — [UTwente](https://research.utwente.nl/en/publications/backchannels-quantity-type-and-timing-matters/)
- Hirasawa et al. (Eurospeech 1999, older): immediate barge-in backchannels from a system gave some users a negative impression. — [ISCA](https://www.isca-archive.org/eurospeech_1999/hirasawa99_eurospeech.html)
- TalkTive (2022, older adults): an assessor judged about 12% of the system's backchannels inappropriate. Mistaking mumbling for silence produced intrusive prompts. — [arXiv 2202.08216](https://arxiv.org/pdf/2202.08216)
- Full-Duplex-Bench (2025) defines a backchannel as under 1 s and fewer than two words, and scores timing against human placement in a corpus (a lower Jensen-Shannon divergence score means timing closer to humans). Every 2025 system tested scored poorly: JSD 0.896 for Gemini Live up to 0.997 for Freeze-Omni (0 means human-like timing). — [arXiv 2503.04721](https://arxiv.org/html/2503.04721v3)
- Székely et al. (KTH 2019): a voice trained on podcast audio sounded more authentic to listeners when the filled pauses were kept in. — [KTH PDF](https://www.speech.kth.se/tts-demos/is19/szekely2019spontaneous.pdf)
- Dall, Tomalin & Wester (SSW 2016): listeners preferred filled pauses modelled as their own sound unit over inserted silent pauses. — [CSTR PDF](https://www.cstr.ed.ac.uk/downloads/publications/2016/Dall_Tomalin_Wester_SSW2016.pdf)
- Kirkland et al. (Interspeech 2022): inserted filled pauses had the strongest effect on how confident a synthetic utterance sounded, with pitch and rate giving finer control. Inserting them into spontaneous-style utterances caused no significant drop in naturalness. — [KTH PDF](https://www.speech.kth.se/stance/papers/kirkland22_interspeech.pdf)
- Wester et al. (Interspeech 2015): fillers ("uh", "um") changed listeners' ratings of the voice's personality traits. — [CSTR PDF](https://www.cstr.inf.ed.ac.uk/downloads/publications/2015/wester:artificial:IS2015.pdf)
- Text from language models usually lacks disfluencies, which can lower perceived naturalness; Hassan et al. (2024) evaluate inserting them. — [arXiv 2412.12710](https://arxiv.org/pdf/2412.12710)
- VR study (2025): natural fillers improved perceived response time, especially at long delays, while explicit wait indicators did not measurably help. — [doi 10.1145/3719160.3736636](https://doi.org/10.1145/3719160.3736636) (via [Deepgram](https://deepgram.com/learn/voice-ai-latency-why-pauses-read-as-hesitation))
- Sesame (Feb 2025): "voice presence" = emotional intelligence, conversational dynamics (timing, pauses, interruptions, emphasis), awareness of context, and a consistent personality. Coverage says it deliberately adds breaths, pauses and self-corrections. — [Sesame research](https://sesame.com/research); [ISPR coverage](https://ispr.info/2025/03/04/masa-presence-sesame-ai-chatbot-is-crossing-the-uncanny-valley-of-conversational-voice/)

### Inferences
- A filler is useful mostly as cover for latency at the start of a turn ("hmm, ek second"). Fillers also signal uncertainty, so they should not be sprinkled into confident factual answers.
- Backchannels: a few, well timed (at pauses where the speaker's pitch falls), never over her speech at random. A wrongly timed "haan" is likely worse than none (inference; no study tested against a no-backchannel baseline).
- Breath and laughter: I found no controlled study measuring them for live agents. The evidence is Sesame's design choice plus anecdote.

### Gaps
- No controlled evidence found on breath or laughter in synthetic speech for live calls.
- No study found on backchannels or fillers in Indian languages ("haan", "accha", "hmm") in synthetic speech.

## Prosody, emotion and adaptation: what helps and the risk of over-acting

### Takeaway
On isolated sentences, synthetic speech now matches human recordings in naturalness ratings. Given the conversation's context, listeners still prefer the human, so the remaining gap is prosody that fits the context. Adapting to the user (entrainment) can build rapport, but its effect depends on the feature, and too much of it is perceived negatively.

### Cited Findings
- Sesame CSM evaluation (2025): 80 paid raters, CMOS on a 7-point scale on the Expresso dataset. Without context, raters showed no clear preference between generated and human speech, so naturalness is saturated. With the previous 90 s of audio and text as context, raters consistently preferred the human recordings. The model also does not handle turn-taking structure, and quality outside English is poor. — [Sesame research](https://sesame.com/research)
- Sesame's new objective tests: correct pronunciation of homographs (200 samples, e.g. "lead") and consistent pronunciation across turns (200 samples, e.g. "route"). Word error rate and speaker similarity are "saturated". — [Sesame research](https://sesame.com/research)
- Galvez et al. (Speech Communication 2020): 98 Argentine Spanish speakers. A system matching the user's loudness raised trust, while matching pitch lowered it. Too much entrainment can be perceived negatively. — [Columbia PDF](https://www.cs.columbia.edu/speech/PaperFiles/2020/Galvez_speech_communication_2020.pdf)
- Earlier work cited in 2016: a system that shifted its pitch toward the user's mean pitch gained rapport and naturalness. — [Interspeech 2016 PDF](https://www.cs.columbia.edu/speech/PaperFiles/2016/rivka_interspeech_16.pdf)
- Nenkova et al. (2008, human dialogue, older): matching high-frequency words predicted perceived naturalness with 67% accuracy against a 50% baseline, and correlated with task success. — [Columbia PDF](https://www.cs.columbia.edu/~julia/papers/nenkova_al_08.pdf)

### Inferences
- Adaptation should be gentle: match her speaking rate and loudness a little, do not copy her pitch, and do not mirror emotion strongly. Over-acting is a real risk (entrainment "in excess" is perceived negatively).
- An evaluation of voice quality must include conversational context. A sentence-level MOS will say "human-level" when the conversation as a whole does not sound human.

### Gaps
- I found no rigorous study measuring "over-acted" emotional TTS in live agents (for example Hume or OpenAI expressive voices). Vendor material only.
- Speaking-rate adaptation in Indian languages: no evidence found.

## Full-duplex behaviour: listening while speaking, barge-in, and not stopping for noise

### Takeaway
The 2025 benchmarks show a trade-off. End-to-end duplex models (Moshi, dGSLM) answer in about 0.26-0.35 s but take the turn during almost every pause. Gemini Live rarely interrupts a pause, but takes about 1.3 s to answer. No system was good at both.

### Cited Findings
- Full-Duplex-Bench v1 (Lin et al., ASRU 2025) tests four things: handling pauses, backchanneling, smooth turn-taking and user interruption. Takeover rate (TOR) = the share of samples where the model takes the turn rather than staying silent or backchanneling; it should be low during her pauses and high when she interrupts. — [arXiv 2503.04721](https://arxiv.org/html/2503.04721v3)
- Results from v1 (lower TOR is better during pauses; latencies in seconds):
  - Moshi: takes the turn in 0.985 of pauses (synthetic set); answers in 0.265 s; responds to interruptions in 0.257 s, but scores only 0.765/5 for quality after an interruption.
  - Gemini Live: takes the turn in 0.255 of pauses; answers in 1.301 s; 3.376/5 after an interruption, responding in 1.183 s.
  - Freeze-Omni: takes the turn in 0.642 of pauses; answers in 0.953 s; best quality after an interruption at 3.615/5, responding in 1.409 s.
  - dGSLM: takes the turn in 0.934 of pauses; answers in 0.352 s; 0.201/5 after an interruption.
  - — [arXiv 2503.04721](https://arxiv.org/html/2503.04721v3)
- Full-Duplex-Bench v1.5 (2025): simulated overlap — user interruption, user backchannel, the user talking to someone else, and far-field background speech. Measures behaviour labels, stop latency and response latency under overlap, and prosody. Five systems showed two opposite strategies for handling overlap. — [arXiv 2507.23159](https://arxiv.org/html/2507.23159v2)
- Full-Duplex-Bench v2 (ACL 2026 short paper): multi-turn evaluation with an automated examiner covering turn-taking, instruction following and task competence. Full-duplex systems often get confused when interrupted across turns. — [arXiv 2510.07838](https://arxiv.org/pdf/2510.07838); [ACL anthology](https://aclanthology.org/2026.acl-short.4.pdf)
- Instruct-FD (2026) tests whether duplex systems follow instructions about turn-taking. — [arXiv 2607.20460](https://arxiv.org/pdf/2607.20460)
- Mystery-shop data (not peer-reviewed): 34% of customers at AI drive-throughs had to repeat their order, against 22% where humans took orders. — [QSR 2025](https://www.qsrmagazine.com/story/the-2025-qsr-drive-thru-report/)

### Inferences
- A product should measure separately: (a) wrongly taking the turn during her pauses, (b) stopping for a backchannel or for background speech (false barge-in), (c) the time to stop when she really interrupts, and (d) answer quality after an interruption.
- Background speech and someone else talking in the room are separate test cases (v1.5). They matter a lot for phone calls in Indian homes.

### Gaps
- No dedicated background-noise (as opposed to background-speech) category was found in v1.5 or v2. Noise robustness has to be tested by the builder.

## Evaluation: listening tests, preference arenas, turn-taking metrics and latency metrics

### Takeaway
Sentence-level MOS is saturated and misleading for conversation. Use comparative tests (CMOS, or MUSHRA with its known biases fixed) with context, real-user pairwise preference (Talk Arena shows static benchmarks miss what users prefer), turn-taking metrics (TOR, latency, backchannel JSD from Full-Duplex-Bench), and latency distributions (p50/p95 time to first audio, end-of-turn detection time).

### Cited Findings
- Rethinking MUSHRA (Varadhan et al., TMLR, arXiv 2411.12719): in MOS, each system is rated alone, so small differences between similar systems are missed, and it suffers range-equalising bias. CMOS is pairwise and slow. MUSHRA compares many systems at once, but a study of 492 listeners found "reference-matching bias" (penalising systems that beat the human reference) and ambiguity in judgements. Proposed fixes: do not mark which sample is the human reference, and tighten the rating criteria. — [arXiv 2411.12719](https://arxiv.org/html/2411.12719v3)
- Chiang et al. (2023): of more than 80 papers, many describe their listening-test details too thinly, which affects results. — cited in [arXiv 2411.12719](https://arxiv.org/html/2411.12719v3)
- Sesame: CMOS against human recordings, with and without 90 s of context, plus objective homograph and pronunciation-consistency tests. — [Sesame research](https://sesame.com/research)
- Talk Arena (Stanford, 2024-25): 5,000 pairwise Prolific votes on five large audio models, compared with 18 static benchmarks by top-k Kendall tau. It found a gap between static evaluation and actual user preference. — [Hugging Face blog](https://huggingface.co/blog/WillHeld/talk-arena)
- Follow-up (Gan, Held, Yang, 2026 preprint): static benchmarks plateau at about 0.85 correlation with user satisfaction; a regression-selected benchmark ("HUMANS") reaches 0.978. — [arXiv 2605.00022](https://arxiv.org/html/2605.00022v1)
- MTalk-Bench (2025): arena-style and rubric-based evaluation of multi-turn speech-to-speech dialogue, with broadly consistent rankings between the two. — [arXiv 2508.18240](https://arxiv.org/html/2508.18240v2)
- Full-Duplex-Bench metrics: TOR, response latency, backchannel frequency and JSD, interruption TOR, a GPT-4o quality score (0-5) and latency after an interruption; v1.5 adds stop latency under overlap. — [v1](https://arxiv.org/html/2503.04721v3); [v1.5](https://arxiv.org/html/2507.23159v2)
- Industry latency practice: track time to first audio as the main metric, report p95 rather than averages (one example: the same agent at 600 ms p95 in the morning and 1,100 ms p95 at peak). Deepgram's Voice Agent Quality Index puts 40% of its weight on interruptions; agents at 3 s or more of latency scored in the mid-50s. — [Coval](https://www.coval.dev/blog/how-to-measure-voice-ai-latency-the-complete-guide); [Deepgram](https://deepgram.com/learn/voice-ai-latency-why-pauses-read-as-hesitation)

### Inferences
- A practical scorecard for live calls: p50/p95 time to first audio; end-of-turn detection p50/p95; wrong takeovers during her pauses; false barge-ins on backchannels and noise; stop time when she interrupts; repeats per call (the drive-through 34% vs 22% figure is a usable outcome metric); and a periodic blind pairwise preference test against a human recording or the previous version, with conversational context included.
- Pairwise preference among real users of each language is the measure that best tracks "feels human". Static benchmarks and single-sentence MOS should be secondary.

### Gaps
- No public benchmark found that covers turn-taking in Indian languages or code-mixed Hinglish.
- No study found that ties exact latency percentiles to abandonment or satisfaction for voice agents; these are vendor heuristics.
