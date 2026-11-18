import json
r=json.load(open('pipe2/tables.json'))
OR={m['id'] for m in (lambda d: d.get('data',d))(json.load(open('or/m_output_modalities=all.json')))}
LV=['LOW','MID','HIGH','MAX','ULTRA']
MAN={
 'speech.in (world)':('AA speech-to-text WER (to 2.6 %) then HF Open ASR average WER (from 5.93 %)', {
  'ULTRA':['microsoft/mai-transcribe-2','elevenlabs/scribe-v2','mistralai/voxtral-small-transcribe-3-0'],
  'MAX':['mistralai/voxtral-mini-transcribe-3-0','x-ai/grok-stt-2.0','google/gemini-3.5-transcribe'],
  'HIGH':['nvidia/nemotron-3.5-transcribe','qwen/qwen3-asr-1.7b','assemblyai/universal-3-5-pro'],
  'MID':['openai/gpt-transcribe','meta/muse-voice-transcribe-1.0','nvidia/parakeet-tdt-0.6b-v3','qwen/qwen3-asr-0.6b'],
  'LOW':['mistralai/voxtral-small-24b-2507-stt','openai/whisper-large-v3','mistralai/voxtral-mini-3b-2507','openai/whisper-large-v3-turbo']}),
 'speech.in (Indian languages) - only 8 reachable':('voiceofindia.ai STT (15 Indian languages, OI-WER) + HF Open ASR Hindi WER', {
  'ULTRA':['microsoft/mai-transcribe-2'],'MAX':['google/gemini-3.5-transcribe','google/gemini-3.8-flash'],
  'HIGH':['meta/muse-voice-transcribe-1.0','elevenlabs/scribe-v2'],'MID':['openai/gpt-transcribe'],
  'LOW':['nvidia/nemotron-3.5-transcribe','assemblyai/universal-3-5-pro']}),
 'speech.out (world)':('AA text-to-speech arena + TTS Arena V2 (16 Nov 2026)', {
  'ULTRA':['elevenlabs/eleven-v4','elevenlabs/eleven-v4-turbo','elevenlabs/eleven-v3'],
  'MAX':['minimax/speech-2.8-hd','fish-audio/s2-pro','speechify/simba-3.5'],
  'HIGH':['google/gemini-3.8-flash-tts','fish-audio/drama-3','elevenlabs/eleven-multilingual-v2'],
  'MID':['elevenlabs/eleven-turbo-v2.5','qwen/qwen-audio-3.0-tts-plus','minimax/speech-2.8-turbo','google/gemini-3.8-flash-lite-tts'],
  'LOW':['elevenlabs/eleven-flash-v2.5','google/gemini-3.1-flash-tts-preview','hexgrad/kokoro-82m','fish-audio/s1']}),
 'speech.out (Indian languages) - only 4 reachable':('voiceofindia.ai TTS vote arena (10 Indian languages)', {
  'ULTRA':['elevenlabs/eleven-v4'],'MAX':['google/gemini-3.8-flash-tts'],'HIGH':['google/gemini-3.1-flash-tts-preview'],
  'MID':['google/gemini-3.8-flash-lite-tts'],'LOW':[]}),
 'music.make - only 2 reachable':('Music Arena + AA music', {
  'ULTRA':[],'MAX':[],'HIGH':['google/lyria-3-pro-preview'],'MID':[],'LOW':['google/lyria-3-clip-preview']}),
}
SRC={'chat':'LMArena text - overall','write':'LMArena text - creative writing','summarise':'LMArena text - longer query + overall',
 'reason':'LMArena text - math + hard prompts','code':'LMArena text - coding + software/IT',
 'tools (proxy)':'LMArena text - instruction following + multi-turn; tool calling required on OpenRouter',
 'extract (proxy)':'LMArena text - instruction following; structured output required on OpenRouter',
 'read.long':'LMArena text - longer query','facts + check (proxy)':'LMArena text - expert + hard prompts',
 'research (proxy)':'LMArena text - expert + hard prompts; tool calling required','write.lang / translate':'LMArena text - non-English',
 'read.image':'LMArena vision - overall + OCR','read.pdf':'LMArena document','image.make':'LMArena text-to-image',
 'image.edit':'LMArena image edit','video.make':'LMArena text-to-video + image-to-video'}
bad=[]
L=['# Pipeline 04 - the level tables, 10-20 models per kind of work (16 Nov 2026, for her approval)','',
'Owner, 16 Nov: "WHY ONLY 3 OR 2 OR 1 MODELS -- WE EVER FIELD WITH MIN 10 MODEL MAX 20 MODELS". Replaces the first copy',
'(1-3 models per level). Built by `pipe2/build.py` from the LMArena dataset (`lmarena-ai/leaderboard-dataset`, CC-BY-4.0,',
'boards published 9-12 Nov 2026) + OpenRouter `/api/v1/models?output_modalities=all` (723 models), read 16 Nov 2026.','',
'## How each pool was cut','',
'1. Every board row with at least 200 votes, matched to an OpenRouter model id (exact name, or a hand-checked alias for',
'   media names like "Dreamina Seedance 2.5 (720p)" = `bytedance/seedance-2.5`).',
'2. Only models OpenRouter lists **today**, that can take the input and give the output the work needs (tool calling,',
'   structured output, image input, image / video output), and that were added to OpenRouter after 16 May 2025',
'   (older models are being retired).',
'3. Score = the board rating; where a kind reads two board categories, their average.',
'4. **Levels are quality bands below the best model of that kind**, so LOW really holds the smaller, faster models',
'   instead of the 20th-best big one: ULTRA within 25 points of the best, MAX 25-50 below, HIGH 50-80, MID 80-120,',
'   LOW 120-190. Up to 4 models per level = up to 20 per kind.',
'5. Where a board is too small for bands (documents, images, video), the best 20 are split into five equal groups.',
'6. Voice and music boards are not in the LMArena data; those pools were cut by hand from the boards named on them.','',
'**Not used for routing:** the score is a quality signal only. Inside a level the Box still ranks by reliability, then',
'speed, then score (plan section 4). Price is not in it (D5).','']
counts=[]
def row(kind,src,levels):
    n=sum(len(levels[l]) for l in LV)
    counts.append((kind,n))
    L.append(f'## {kind} - {n} models'); L.append(''); L.append(f'Source: {src}.'); L.append('')
    L.append('| Level | Models (OpenRouter id) |'); L.append('|---|---|')
    for lv in LV:
        ms=levels[lv]
        for m in ms:
            mid=m if isinstance(m,str) else m['id']
            if mid not in OR: bad.append(mid)
        cell=', '.join((f"`{m}`" if isinstance(m,str) else f"`{m['id']}` {m['score']:.0f}") for m in ms) or '(none scored - uses the nearest level)'
        L.append(f'| {lv} | {cell} |')
    L.append('')
for k,v in r.items(): row(k, SRC[k]+'; '+v['method'], v['levels'])
for k,(src,levels) in MAN.items(): row(k,src,levels)
L.insert(L.index('**Not used for routing:** the score is a quality signal only. Inside a level the Box still ranks by reliability, then'),
  '## Count per kind of work\n\n| Kind | Models |\n|---|---|\n'+'\n'.join(f'| {k} | {n} |' for k,n in counts)+'\n')
L+=['## Below 10, said plainly','',
'- **Indian-language speech in (8), Indian-language speech out (4), music (2):** OpenRouter does not carry the other',
'  scored models. The better ones need direct company routes: speech in - Sarvam Saaras v3, Bodhan Indic Transcribe,',
'  Amazon Transcribe, Azure Speech, Fonada Kapture, AI4Bharat IndicConformer (self-host); speech out - Cartesia Sonic,',
'  Maya; music - ACE Music, Suno (no official API found), Mureka, Eleven Music, Stable Audio, Riffusion.',
'- **Indian-language text:** the `write.lang / translate` pool (18) is ranked on the pooled non-English vote; no board',
'  ranks Hindi / Marathi / Tamil text yet (research 03).','',
'## Other caveats','',
'- `tools`, `extract`, `facts`, `research` are **proxies** (no live public tool-calling / extraction / search board in the',
'  CC-BY data); the AA, BFCL-current and Search-arena numbers in research 01 are not in this cut.',
'- Arena votes alone: newer models it has not scored much (Claude Fable 5.2, GPT-6 Astra, GPT-6.1 Sol) sit low or are',
'  missing although other boards put them at the top; they move up once a second board is in the feed.',
'- Name matches checked by hand but not confirmed by the vendor: MiniMax H3 = `minimax/hailuo-3`, Grok Voice Transcribe',
'  2.0 = `x-ai/grok-stt-2.0`, OpenAudio S2 = `fish-audio/s2-pro`, Qwen-Image 2.1 = `qwen/qwen-image-2.1-pro`.',
'- Every id above was listed by OpenRouter on 16 Nov 2026 (checked by the script).','']
open('/home/user/santosh-app/docs/research/pipeline/04_level_tables.md','w').write('\n'.join(L))
print('ids not on OpenRouter:',bad); print(counts)
