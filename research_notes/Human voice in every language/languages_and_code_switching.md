# Natural AI voice across the world's languages: coverage, low-resource languages, accents and code-switching

Research date: 11 Nov 2026. Most sources are 2025-2026. Older facts are marked [older]. Vendor numbers are marked (vendor-reported).

## How many languages do leading ASR / TTS systems cover, and how fast does quality drop for low-resource languages?

### Takeaway
Speech recognition now nominally reaches 1,600+ languages (Meta Omnilingual ASR, Nov 2025), and Meta's older MMS covers TTS for about 1,100. But "covered" and "good" are very different. Quality falls off steeply below roughly 10 hours of training audio. Production real-time voice models cover far fewer languages: Gemini Live native audio lists 24 on Vertex AI.

### Cited Findings
- **Meta Omnilingual ASR** (released 10 Nov 2025): covers 1,600+ languages, 500+ of them never served by any ASR system before. Models range from 300M parameters (for low-power devices) to 7B. It is built for zero-shot extension: a community can add a language with "a handful" of paired samples. — [arXiv 2511.09690](https://arxiv.org/abs/2511.09690)
- Omnilingual quality, as Meta reports it (vendor-reported, via press): character error rate (CER) is under 10% for 78% of languages. Among languages with at least 10 hours of training audio, 95% are under 10% CER. Among languages with less than 10 hours, only 36% are. Apache 2.0 licence. It ships with the Omnilingual ASR Corpus covering 350 underrepresented languages. "Bring your own language" could in theory reach 5,400+ languages. — [The Decoder](https://the-decoder.com/metas-omnilingual-asr-brings-speech-recognition-to-1600-languages/); [OpenSourceForU](https://www.opensourceforu.com/2025/11/metas-omnilingual-asr-brings-1600-languages-to-open-source-speech-ai/). Note: the arXiv abstract itself gives no CER table. It says only "substantial gains ... especially in low-resource conditions" — [arXiv](https://arxiv.org/abs/2511.09690).
- **Meta MMS** [older, 2023]: ASR and TTS for 1,100+ languages, and language ID for 4,000+. It was trained mostly on New Testament readings, because that is the text translated into the most languages. Meta itself says there are few distinct speakers per language. — [Meta AI blog](https://ai.meta.com/blog/multilingual-model-speech-recognition/); [paper PDF](https://research.facebook.com/file/6486163864750413/Scaling-Speech-Technology-to-1,000+-Languages.pdf)
- An AlphaXiv summary of the MMS paper says about 85% of MMS TTS models are intelligible (≤5% CER when transcribed back). I did not check this figure against the paper. — [AlphaXiv](https://alphaxiv.org/overview/2305.13516v1)
- An independent critique of MMS: some languages "sound expressive and human, while others remain robotic or unintelligible." — [Turing](https://www.turing.com/resources/multilingual-tts-systems)
- **Google USM** [older, Mar 2023]: a 2B-parameter model, pre-trained on 12M hours of unlabeled YouTube audio plus 28B sentences of text across 300+ languages, then fine-tuned for ASR in 100+ languages. YouTube captions built on it reach under 30% WER in 73 languages. Google called it "a first step towards 1,000 languages". — [Google Research blog](https://research.google/blog/universal-speech-model-usm-state-of-the-art-speech-ai-for-100-languages/); [arXiv 2303.01037](https://arxiv.org/abs/2303.01037v3)
- USM against Whisper: Google compared the two only on the 18 languages where Whisper large-v2 gets under 40% WER. That choice itself shows how few languages Whisper handled well. — [Google Research blog](https://research.google/blog/universal-speech-model-usm-state-of-the-art-speech-ai-for-100-languages/)
- **Gemini Live API (native audio)**: Vertex AI documents 24 languages with BCP-47 codes. Firebase lists additional languages for 3.x models, and the lists differ by model version. A developer forum reports en-GB being rejected on a native-audio preview model. — [Vertex AI Live API](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api); [configure language/voice](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api/configure-language-voice); [forum](https://discuss.ai.google.dev/t/unsupported-language-code-en-gb-for-gemini-2-5-native-audio-documentation-location-uk-accent-roadmap/123213)
- **Whisper on low-resource languages**: in a 2026 Interspeech paper on South Asian languages, script confusion (the model writing the wrong script or language) pushes Whisper's WER above 100% on three languages. For Pashto, removing outputs in the wrong script cut Whisper-medium's WER from about 165% to about 97%. Transliteration post-processing recovered up to 25 WER points with no retraining. — [Interspeech 2026 paper](https://aghaaliraza.com/publications/2026--Interspeech--Dissecting_ASR_Failures_in_Low-Resource_South_Asian_Languages.pdf)
- A 2025 study found that in low-resource languages, Whisper's decoder puts the correct token at the top less often, with lower confidence and higher entropy. It also notes that WER can hide hallucination. — [arXiv 2509.25516](https://arxiv.org/html/2509.25516v1)

### Inferences
- The practical cliff is training data. Above about 10 hours of transcribed audio, most languages reach usable CER. Below it, about two-thirds do not. This matches the general pattern that pretraining on unlabeled audio plus a small labeled set is what makes long-tail coverage possible.
- TTS lags ASR in reach and naturalness. MMS-style TTS built from one Bible reader per language is intelligible, but it is not "natural" or conversational.
- "Supported" in a real-time voice API is a much narrower list (about 24 for Gemini Live) than in research ASR. A voice product must check the exact model version's language table.

### Gaps
- Whisper's official language count (99, per [the openai/whisper repo](https://github.com/openai/whisper)) and Meta SeamlessM4T / Seamless streaming coverage were not re-verified this session.
- No independent, cross-vendor TTS naturalness benchmark covering hundreds of languages was found.
- I found no per-language Omnilingual CER table, only the summary percentages.

## Indian languages: AI4Bharat, Sarvam, Bhashini, Krutrim — quality, licences, Hinglish

### Takeaway
India has the deepest low-resource speech ecosystem outside English and Chinese. Open models from AI4Bharat (IndicF5 under MIT, Indic Parler-TTS under Apache 2.0 but gated) cover 11 to 21 languages. Sarvam's commercial Bulbul v3 covers 11 languages and claims to lead on telephony audio and code-mixed text. Bhashini, the government platform, serves about 22 to 23 voice languages. Hinglish ASR remains hard: the reported spread is about 27% to 70% WER across models, from a vendor source.

### Cited Findings
- **IndicF5** (AI4Bharat): MIT licence. 11 languages (Assamese, Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi, Tamil, Telugu). Trained on 1,417 hours (Rasa, IndicTTS, LIMMITS, IndicVoices-R). It is a voice-cloning model that needs a reference clip plus that clip's transcript. Unauthorised cloning is prohibited, and access is gated on Hugging Face. The card now recommends a newer model, "Indic-Speak", which covers 22 languages. — [HF model card](https://huggingface.co/ai4bharat/IndicF5)
- **Indic Parler-TTS** (AI4Bharat): Apache 2.0, gated. The voice is controlled by a text description. Its card is internally inconsistent about scope: it claims 21 official languages in one place, and says 18 and "16 + English + Chhattisgarhi" in others. Chhattisgarhi, Kashmiri and Punjabi are listed as unofficial. It has 69 named voices and 12 emotion styles; emotions are officially supported in only 10 languages. Indian English accent is officially supported; British and American are not. Quality is reported as a "Native Speaker Score": Sanskrit 99.79 and Nepali 64→80 after fine-tuning, with Tamil and Marathi the lowest of the major languages. The card says nothing about code-mixed input. — [HF model card](https://huggingface.co/ai4bharat/indic-parler-tts)
- Licence data conflicts across catalogues: the government AIKosh catalogue lists Indic Parler-TTS as MIT, while the HF card says Apache 2.0. — [AIKosh](https://aikosh.indiaai.gov.in/home/models/details/ai4bharat_indic_parler_tts_text_to_speech_model.html)
- **Sarvam Bulbul v3**: 11 languages (en-IN plus 10 Indic), with "22 soon". 30+ or 35+ voices, depending on the page. Speed 0.5–2.0x, 2,500 characters per request, and a claimed latency under 250 ms on 8 kHz telephony audio. — [Sarvam docs](https://docs.sarvam.ai/api/getting-started/models/bulbul); [Sarvam blog](https://sarvam.ai/blogs/bulbul-v3); [voice agents](https://www.sarvam.ai/text-to-speech/voice-agents)
- Bulbul v3 evaluation (vendor-reported): a blind A/B study by Josh Talks with 500+ annotators and 20,000+ votes across 11 languages. ElevenLabs v3 alpha led on full-band audio quality; Bulbul v3 led on 8 kHz telephony and had the fewest missing words and mispronunciations. Its robustness set covers code-mixed and romanised text, numerals, abbreviations and URLs, and Sarvam claims the lowest CER there. Scoring took the minimum CER over several spoken-form variants. Sarvam says the benchmark data is on Hugging Face. — [Sarvam blog](https://sarvam.ai/blogs/bulbul-v3)
- **Bhashini** (MeitY): a secondary aggregator cites MeitY/PIB figures of 36 text languages and 23 voice languages (Jul 2026), up from 22 voice languages in Feb 2026, with more than 4B inferences. Not checked against the PIB primary source. — [productgrowth.in](https://productgrowth.in/numbers/bhashini-languages-supported-india/); [multilingual.com](https://multilingual.com/ai-in-indian-languages/)
- AI4Bharat and IIT Madras "Bodhan" open models: ASR in 27 languages and TTS in 23, reported in secondary coverage. — [Careers360](https://news.careers360.com/iit-madras-bodhan-ai-ai4bharat-launches-four-open-models-indian-languages-digital-public-goods-sovereign-ai-student-teacher-bot)
- **Hinglish ASR**: Hinglish WER ranges from 26.97% to 69.53% across models on the same audio (vendor-reported; Deepgram cites the "SwitchLingua" benchmark). — [Deepgram](https://deepgram.com/blog/hinglish-voice-ai-speech-recognition)
- Shunya Labs, another vendor, cites about 30% WER for standard models on code-switched conversation. — [Vaani/IISc case study](https://vaani.iisc.ac.in/case-studies/shunyalabs)
- Hinglish datasets: HiACC, with adult and child speech, word-level code-switch tags, CC BY-NC 4.0. The paper notes that models trained on monolingual data "struggle with code-switched input". — [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12329218/). IITG-HingCoS [older, 2019]: 25 hours, 9,251 sentences, phone-recorded. — [IIT Guwahati](https://iitg.ac.in/eee/emstlab/HingCoS_Database/HingCoS.html)

### Inferences
- For a Hinglish voice product, the realistic choices are Sarvam (commercial, telephony-tuned, explicitly tested on code-mixed and romanised text) or AI4Bharat open models (permissive licences, but gated and without code-mix claims). Open models fit lab use; read each card's gating and cloning terms before any commercial use.
- The 26.97–69.53% WER spread on identical Hinglish audio means vendor choice matters more for code-switched speech than for monolingual Hindi.

### Gaps
- I found no current primary source for Krutrim's speech models, or for Sarvam Saarika / Saaras / Shuka quality numbers.
- I found no independent, non-vendor Hinglish TTS naturalness study.
- IndicVoices and IndicTrans sizes were not re-verified this session.

## African and other low-resource regions: Masakhane, Lelapa AI, Google, Common Voice

### Takeaway
African speech data is growing quickly through open, community-sourced corpora, especially Google's WAXAL (2026). Commercial products are still narrow: Lelapa's Vulavula offers ASR in 4–5 South African languages, and its TTS is "coming soon".

### Cited Findings
- **Google WAXAL** (2026): launched in Feb 2026 with 21 languages (including Hausa, Yoruba, Acholi and Luganda), more than 11,000 hours of audio, about 1,250 of them transcribed, and over 20 hours of studio TTS audio. By March 2026 Google's blog described 27 Sub-Saharan languages, about 1,846 transcribed ASR hours and 565+ studio TTS hours. Licence CC BY 4.0, hosted on Hugging Face. The counts differ between versions. — [Google Research blog](https://research.google/blog/waxal-a-large-scale-open-resource-for-african-language-speech-technology/); [arXiv 2602.02734](https://arxiv.org/html/2602.02734); [Nairametrics](https://nairametrics.com/2026/02/02/google-launches-waxal-ai-speech-project-in-21-african-languages/)
- **Lelapa AI Vulavula**: speech-to-text and translation for isiZulu, Sesotho, Afrikaans, South African English and African French. Its feature table marks TTS as "coming soon". Swahili and Yoruba are partial or coming; Igbo and Pidgin are not yet available. Lelapa also released InkubaLM, a small model, in 2024. — [Lelapa docs](https://docs.lelapa.ai/overview/introduction); [product overview](https://lelapa.ai/vulavula-product-overview)
- **Sunbird AI** has a Whisper fine-tune for 51 African languages; its card warns of "hallucination or substitution errors, especially for highly low-resource languages". — [Sunbird SALT](https://salt.sunbird.ai/models/asr-whisper-51-african-languages/)
- **Mozilla Common Voice**: Scripted Speech v26.0 (Jun 2026) covers 294 languages, up from 289 in v24.0 (Dec 2025). A Spontaneous Speech track exists as well. — [common-voice/cv-dataset](https://github.com/common-voice/cv-dataset); [Mozilla Discourse](https://discourse.mozilla.org/t/release-live-mcv-scripted-speech-24-0-and-spontaneous-speech-2-0/146740)

### Inferences
- The recurring pattern: crowdsourced or image-prompted natural speech for ASR, plus a small studio set (20–565 hours) for TTS. This is now the template for adding a language. Natural-sounding TTS in a new language needs studio-quality recordings, not just crowd audio.

### Gaps
- I did not fetch Masakhane's speech-specific outputs (for example AfriSpeech, or Masakhane's TTS work). Please verify separately.
- I found no current benchmark comparing African-language TTS across vendors.

## Accent and dialect: native-sounding vs "foreign" accent in TTS

### Takeaway
"Accent leakage" is the main known problem in cross-lingual voice cloning: a cloned voice carries its source language's accent into the target language. Several 2026 papers propose fixes. Product APIs also limit accents through locale lists, for example en-IN vs en-GB.

### Cited Findings
- Zero-shot cloning ties speaker identity to the prompt's native-language habits. Accent leakage persists even in OmniVoice, which covers 600+ languages. The paper proposes training-free, phrase-localised accent control for code-switched TTS. — [arXiv 2609.01016](https://arxiv.org/pdf/2609.01016)
- KIT's IWSLT 2026 cross-lingual cloning submission: source-language phonetics carry into the output, and this gets worse when a single utterance mixes languages. Their fix is language-tag prompting plus RL fine-tuning. — [arXiv 2606.07240](https://arxiv.org/pdf/2606.07240)
- X-Voice: zero-shot cloning across 30 languages, with language IDs injected at both the text level and the time level to reduce leakage. — [arXiv 2605.05611](https://arxiv.org/pdf/2605.05611)
- Accent Analogy Guidance: a training-free fix that subtracts an estimated accent direction while keeping speaker similarity. — [arXiv 2609.29123](https://arxiv.org/pdf/2609.29123)
- A 2026 preprint argues the reference clip carries accent, dialect and prosody as well as timbre. It notes that Qwen3-TTS and CosyVoice 3 report accent drift as a separate evaluation dimension, and that leakage metrics are classifier-based proxies. — [preprints.org 202608.2014](https://www.preprints.org/manuscript/202608.2014)
- Indic Parler-TTS officially supports only an Indian English accent; British and American accents can be prompted but are unsupported. — [HF card](https://huggingface.co/ai4bharat/indic-parler-tts)

### Inferences
- Cloning a Hindi speaker's voice into Tamil, or into English, will by default sound like a Hindi speaker speaking Tamil. To get a native-sounding voice, use a native reference speaker per language, or a model with explicit language-ID or accent control.
- For code-switched sentences, the accent should switch per phrase. That is exactly what the 2609.01016 paper targets, which shows that most systems do not do it yet.

### Gaps
- These are mostly preprints; I read abstracts, not full results.
- I found no source measuring how well ASR handles regional Indian accents, for example Bhojpuri-accented Hindi.

## Techniques and known failure modes (pretraining, transfer, phonemes, text normalisation, scripts, tonal prosody)

### Takeaway
The working recipe is self-supervised multilingual pretraining on unlabeled audio, then fine-tuning on small labeled sets (USM, MMS, Omnilingual). For TTS, add byte- or character-level tokenizers so new scripts can be handled, and a reference clip for cloning. The common failures: wrong-language or wrong-script output, numbers and abbreviations read wrong, and flat or incorrect tone in tonal languages.

### Cited Findings
- Pretraining then fine-tuning: USM pre-trains its encoder on 12M unlabeled hours, then fine-tunes on a smaller labeled set. — [arXiv 2303.01037](https://arxiv.org/abs/2303.01037v3). Omnilingual reaches zero-shot languages from a handful of in-context examples. — [arXiv 2511.09690](https://arxiv.org/abs/2511.09690)
- Script handling: Indic Parler-TTS's prompt tokenizer has a larger vocabulary and byte fallback, so it can extend to new languages. — [HF card](https://huggingface.co/ai4bharat/indic-parler-tts)
- Wrong-language and wrong-script failure: WER above 100% reliably signals output in the wrong language, and transliteration post-processing recovers up to 25 WER points. — [Interspeech 2026](https://aghaaliraza.com/publications/2026--Interspeech--Dissecting_ASR_Failures_in_Low-Resource_South_Asian_Languages.pdf)
- Language ID should run per utterance, not per file, for code-switching (vendor recommendation). — [Gladia](https://www.gladia.io/blog/mastering-multilingual-speech-to-text-code-switching)
- Text normalisation: Sarvam tests TTS on numerals, abbreviations and URLs, and scores against several spoken-form variants because one written number has many valid readings. Their example is ₹8,750 and "15 जनवरी". — [Sarvam blog](https://sarvam.ai/blogs/bulbul-v3)
- Tonal languages: a Vietnamese TTS evaluation argues that a tone-level intelligibility test is needed alongside quality ratings, and that more tonal and prosodic work is needed. — [HAL](https://hal.archives-ouvertes.fr/hal-01621853). Yorùbá tone depends on pitch dynamics within and between syllables, not just pitch level. — [NWU thesis](https://repository.nwu.ac.za/bitstreams/cebcd346-e22b-49b6-a544-a7aade933273/download). In an Efik TTS study (via a secondary summary), all four systems tested struggled with tonal fidelity even when their naturalness was good. — [Modelwire](https://themodelwire.com/article/first-efik-text-to-speech-study-exposes-tonal-synthesis-gaps-in-low-resource-ai-01KWXA8BJYJX9K0BNKCAF8QH3M)
- Hallucination: Sunbird warns that its model may hallucinate or substitute words in very low-resource languages. — [Sunbird](https://salt.sunbird.ai/models/asr-whisper-51-african-languages/)

### Inferences
- A practical design for a multilingual voice product:
  - Lock or hint the language per call or utterance.
  - Use per-language text normalisation before TTS (Indian number grouping, ₹, dates, romanised Hindi).
  - Use a native reference voice per language.
  - Evaluate tonal languages with tone-specific listening tests, not MOS alone.
- Hinglish adds a step: decide per phrase which script and pronunciation to use. Romanised Hindi ("kal milte hain") must be read as Hindi, not spelled out as English.

### Gaps
- I found no primary source comparing phoneme input against grapheme input in modern multilingual TTS.
- I found no source quantifying mispronounced names in Indian TTS.
- No Indian-language text-normalisation library (for example the AI4Bharat or NeMo Indic normalisers) was checked this session.
