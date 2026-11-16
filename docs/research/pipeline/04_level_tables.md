# Pipeline 04 - the level tables, 10-20 models per kind of work (16 Nov 2026, for her approval)

Owner, 16 Nov: "WHY ONLY 3 OR 2 OR 1 MODELS -- WE EVER FIELD WITH MIN 10 MODEL MAX 20 MODELS". Replaces the first copy
(1-3 models per level). Built by `pipe2/build.py` from the LMArena dataset (`lmarena-ai/leaderboard-dataset`, CC-BY-4.0,
boards published 9-12 Nov 2026) + OpenRouter `/api/v1/models?output_modalities=all` (723 models), read 16 Nov 2026.

## How each pool was cut

1. Every board row with at least 200 votes, matched to an OpenRouter model id (exact name, or a hand-checked alias for
   media names like "Dreamina Seedance 2.5 (720p)" = `bytedance/seedance-2.5`).
2. Only models OpenRouter lists **today**, that can take the input and give the output the work needs (tool calling,
   structured output, image input, image / video output), and that were added to OpenRouter after 16 May 2025
   (older models are being retired).
3. Score = the board rating; where a kind reads two board categories, their average.
4. **Levels are quality bands below the best model of that kind**, so LOW really holds the smaller, faster models
   instead of the 20th-best big one: ULTRA within 25 points of the best, MAX 25-50 below, HIGH 50-80, MID 80-120,
   LOW 120-190. Up to 4 models per level = up to 20 per kind.
5. Where a board is too small for bands (documents, images, video), the best 20 are split into five equal groups.
6. Voice and music boards are not in the LMArena data; those pools were cut by hand from the boards named on them.

## Count per kind of work

| Kind | Models |
|---|---|
| chat | 19 |
| write | 20 |
| summarise | 19 |
| reason | 20 |
| code | 19 |
| tools (proxy) | 18 |
| extract (proxy) | 20 |
| read.long | 20 |
| facts + check (proxy) | 19 |
| research (proxy) | 19 |
| write.lang / translate | 18 |
| read.image | 20 |
| read.pdf | 20 |
| image.make | 20 |
| image.edit | 20 |
| video.make | 18 |
| speech.in (world) | 17 |
| speech.in (Indian languages) - only 8 reachable | 8 |
| speech.out (world) | 17 |
| speech.out (Indian languages) - only 4 reachable | 4 |
| music.make - only 2 reachable | 2 |

**Not used for routing:** the score is a quality signal only. Inside a level the Box still ranks by reliability, then
speed, then score (plan section 4). Price is not in it (D5).

## chat - 19 models

Source: LMArena text - overall; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `qwen/qwen3.5-122b-a10b` 1418, `qwen/qwen3-next-80b-a3b-instruct` 1417, `google/gemini-2.5-flash` 1417, `openai/gpt-5.2` 1416 |
| MID | `anthropic/claude-sonnet-4.6` 1458, `google/gemini-2.5-pro` 1458, `openai/gpt-5.6-sol` 1457, `moonshotai/kimi-k2.6` 1455 |
| HIGH | `qwen/qwen3.8-max-0902` 1485, `meta/muse-spark-1.2` 1483, `google/gemini-3.5-flash` 1483, `google/gemini-3.1-pro-preview` 1480 |
| MAX | `anthropic/claude-fable-5.1` 1512, `anthropic/claude-opus-5` 1506, `meta/muse-wonder` 1503, `google/gemini-4-hydrogen` 1502 |
| ULTRA | `google/gemini-4-carbon` 1538, `google/gemini-4-argon` 1530, `anthropic/claude-opus-5.5` 1514 |

## write - 20 models

Source: LMArena text - creative writing; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `z-ai/glm-4.6` 1412, `anthropic/claude-opus-4.1` 1412, `deepseek/deepseek-r1-0528` 1405, `tencent/hy3` 1405 |
| MID | `openai/gpt-5.6-sol` 1451, `qwen/qwen3.7-max` 1447, `deepseek/deepseek-v4-pro-0813` 1446, `anthropic/claude-opus-4.5` 1444 |
| HIGH | `qwen/qwen3.8-max-0902` 1482, `google/gemini-3.5-flash` 1471, `xiaomi/mimo-v2.6-pro` 1468, `meta/muse-spark-1.3` 1467 |
| MAX | `anthropic/claude-opus-4.6` 1504, `anthropic/claude-fable-5` 1494, `anthropic/claude-opus-5` 1494, `google/gemini-3.8-flash` 1493 |
| ULTRA | `google/gemini-4-argon` 1533, `google/gemini-4-carbon` 1532, `anthropic/claude-opus-5.5` 1532, `anthropic/claude-fable-5.1` 1514 |

## summarise - 19 models

Source: LMArena text - longer query + overall; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `qwen/qwen3-235b-a22b-thinking-2507` 1423, `mistralai/mistral-large-2512` 1422, `deepseek/deepseek-v3.2-exp` 1421, `z-ai/glm-4.5` 1421 |
| MID | `moonshotai/kimi-k3.1-pro` 1464, `moonshotai/kimi-k2.6` 1462, `google/gemini-3-flash-preview` 1459, `anthropic/claude-sonnet-4.5` 1457 |
| HIGH | `google/gemini-3.7-flash` 1491, `meta/muse-spark-1.3` 1490, `qwen/qwen3.8-max-0902` 1489, `google/gemini-3.5-flash` 1483 |
| MAX | `anthropic/claude-fable-5.1` 1518, `google/gemini-4-hydrogen` 1513, `anthropic/claude-opus-5` 1511, `anthropic/claude-opus-4.6` 1510 |
| ULTRA | `google/gemini-4-carbon` 1544, `google/gemini-4-argon` 1538, `anthropic/claude-opus-5.5` 1521 |

## reason - 20 models

Source: LMArena text - math + hard prompts; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `z-ai/glm-4.5` 1428, `qwen/qwen3-vl-235b-a22b-instruct` 1427, `anthropic/claude-haiku-5.5` 1427, `qwen/qwen3.5-122b-a10b` 1426 |
| MID | `moonshotai/kimi-k3.1-pro` 1471, `openai/gpt-6.1-sol` 1470, `anthropic/claude-opus-4.5` 1470, `google/gemini-3-flash-preview` 1469 |
| HIGH | `meta/muse-spark-1.3` 1500, `z-ai/glm-5.3-flash` 1497, `google/gemini-3.5-flash` 1497, `meta/muse-wonder` 1496 |
| MAX | `anthropic/claude-opus-5.5` 1526, `anthropic/claude-opus-4.6` 1521, `google/gemini-3.8-flash` 1518, `google/gemini-4-hydrogen` 1513 |
| ULTRA | `google/gemini-4-carbon` 1551, `google/gemini-4-argon` 1543, `anthropic/claude-opus-5` 1529, `anthropic/claude-fable-5.1` 1528 |

## code - 19 models

Source: LMArena text - coding + software/IT; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `openai/gpt-5.2` 1438, `openai/gpt-5.4-mini` 1438, `z-ai/glm-4.5` 1438, `qwen/qwen3.5-122b-a10b` 1436 |
| MID | `moonshotai/kimi-k2.5` 1478, `qwen/qwen3.8-27b` 1477, `stepfun/step-5-preview` 1477, `x-ai/grok-4.5` 1473 |
| HIGH | `meta/muse-spark-1.2` 1506, `z-ai/glm-5.3-flash` 1505, `moonshotai/kimi-k3` 1502, `qwen/qwen3.8-max-0902` 1501 |
| MAX | `xiaomi/mimo-v2.6-pro` 1531, `anthropic/claude-opus-4.6` 1530, `anthropic/claude-opus-5` 1529, `anthropic/claude-fable-5.1` 1526 |
| ULTRA | `google/gemini-4-carbon` 1558, `google/gemini-4-argon` 1541, `anthropic/claude-opus-5.5` 1538 |

## tools (proxy) - 18 models

Source: LMArena text - instruction following + multi-turn; tool calling required on OpenRouter; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `qwen/qwen3.8-27b` 1434, `minimax/minimax-m3` 1433, `google/gemini-3.5-flash-lite` 1432, `tencent/hy3` 1432 |
| MID | `google/gemini-3.5-flash` 1474, `openai/gpt-5.6-sol` 1472, `anthropic/claude-opus-4.5` 1472, `meta/muse-spark-1.1` 1471 |
| HIGH | `meta/muse-wonder` 1504, `anthropic/claude-fable-5` 1504, `google/gemini-4-hydrogen` 1502, `anthropic/claude-opus-4.7` 1502 |
| MAX | `anthropic/claude-opus-5.5` 1519, `anthropic/claude-opus-4.6` 1516, `anthropic/claude-opus-5` 1508, `anthropic/claude-fable-5.1` 1506 |
| ULTRA | `google/gemini-4-carbon` 1554, `google/gemini-4-argon` 1542 |

## extract (proxy) - 20 models

Source: LMArena text - instruction following; structured output required on OpenRouter; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `openai/gpt-5.2-chat` 1417, `mistralai/mistral-medium-3-5` 1416, `anthropic/claude-haiku-4.5` 1414, `deepseek/deepseek-v3.2` 1413 |
| MID | `anthropic/claude-sonnet-4.5` 1459, `meta/muse-spark-1.1` 1457, `openai/gpt-6-astra` 1456, `openai/gpt-5.6-terra` 1455 |
| HIGH | `anthropic/claude-sonnet-5.5` 1487, `google/gemini-3.7-flash` 1485, `moonshotai/kimi-k3` 1484, `qwen/qwen3.8-max-0902` 1483 |
| MAX | `anthropic/claude-fable-5` 1503, `anthropic/claude-opus-4.7` 1498, `meta/muse-wonder` 1494, `google/gemini-3.8-flash` 1493 |
| ULTRA | `google/gemini-4-carbon` 1540, `google/gemini-4-argon` 1536, `anthropic/claude-opus-5.5` 1535, `anthropic/claude-opus-4.6` 1521 |

## read.long - 20 models

Source: LMArena text - longer query; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `deepseek/deepseek-v3.2` 1428, `google/gemma-4-26b-a4b-it` 1428, `reflection/beam-1.0-501b-a23b` 1428, `openai/gpt-5.2-chat` 1427 |
| MID | `moonshotai/kimi-k2.6` 1468, `moonshotai/kimi-k3.1-pro` 1468, `z-ai/glm-5.1` 1467, `x-ai/grok-4.5` 1462 |
| HIGH | `meta/muse-wonder` 1497, `google/gemini-3.7-flash` 1494, `qwen/qwen3.8-max-0902` 1493, `moonshotai/kimi-k3` 1490 |
| MAX | `anthropic/claude-fable-5.1` 1523, `anthropic/claude-opus-4.6` 1518, `anthropic/claude-opus-5` 1516, `anthropic/claude-fable-5` 1510 |
| ULTRA | `google/gemini-4-carbon` 1549, `google/gemini-4-argon` 1547, `anthropic/claude-opus-5.5` 1528, `google/gemini-4-hydrogen` 1524 |

## facts + check (proxy) - 19 models

Source: LMArena text - expert + hard prompts; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `google/gemma-4-26b-a4b-it` 1443, `~deepseek/deepseek-v4-flash-latest` 1443, `openai/gpt-5.2-chat` 1441, `anthropic/claude-opus-4.1` 1441 |
| MID | `qwen/qwen3.7-max` 1486, `z-ai/glm-5.2` 1484, `google/gemini-3.1-pro-preview` 1484, `openai/gpt-5.6-terra` 1482 |
| HIGH | `meta/muse-wonder` 1514, `anthropic/claude-opus-4.7` 1513, `google/gemini-3.7-flash` 1506, `meta/muse-spark-1.3` 1506 |
| MAX | `google/gemini-4-hydrogen` 1539, `anthropic/claude-opus-5` 1539, `anthropic/claude-fable-5.1` 1537, `anthropic/claude-opus-4.6` 1534 |
| ULTRA | `google/gemini-4-carbon` 1566, `google/gemini-4-argon` 1549, `anthropic/claude-opus-5.5` 1543 |

## research (proxy) - 19 models

Source: LMArena text - expert + hard prompts; tool calling required; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `google/gemma-4-26b-a4b-it` 1443, `~deepseek/deepseek-v4-flash-latest` 1443, `openai/gpt-5.2-chat` 1441, `anthropic/claude-opus-4.1` 1441 |
| MID | `qwen/qwen3.7-max` 1486, `z-ai/glm-5.2` 1484, `google/gemini-3.1-pro-preview` 1484, `openai/gpt-5.6-terra` 1482 |
| HIGH | `meta/muse-wonder` 1514, `anthropic/claude-opus-4.7` 1513, `google/gemini-3.7-flash` 1506, `meta/muse-spark-1.3` 1506 |
| MAX | `google/gemini-4-hydrogen` 1539, `anthropic/claude-opus-5` 1539, `anthropic/claude-fable-5.1` 1537, `anthropic/claude-opus-4.6` 1534 |
| ULTRA | `google/gemini-4-carbon` 1566, `google/gemini-4-argon` 1549, `anthropic/claude-opus-5.5` 1543 |

## write.lang / translate - 18 models

Source: LMArena text - non-English; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `deepseek/deepseek-r1-0528` 1412, `reflection/beam-1.0-501b-a23b` 1412, `google/gemini-3.1-flash-lite` 1411, `google/gemini-2.5-flash` 1409 |
| MID | `google/gemini-2.5-pro` 1452, `anthropic/claude-opus-4.8` 1451, `moonshotai/kimi-k3.1-pro` 1450, `deepseek/deepseek-v4.1-flash-1017` 1450 |
| HIGH | `meta/muse-spark-1.3` 1483, `anthropic/claude-fable-5` 1482, `anthropic/claude-opus-4.7` 1480, `meta/muse-spark-1.2` 1478 |
| MAX | `anthropic/claude-fable-5.1` 1507, `anthropic/claude-opus-5.5` 1503, `anthropic/claude-opus-5` 1500, `google/gemini-4-hydrogen` 1495 |
| ULTRA | `google/gemini-4-carbon` 1534, `google/gemini-4-argon` 1523 |

## read.image - 20 models

Source: LMArena vision - overall + OCR; quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `openai/gpt-5-mini` 1201, `google/gemini-2.5-flash-lite` 1200, `openai/gpt-5.4-nano` 1200, `mistralai/mistral-medium-3.1` 1174 |
| MID | `openai/gpt-5.2` 1251, `qwen/qwen3-vl-235b-a22b-instruct` 1250, `mistralai/mistral-large-4-0` 1249, `openai/gpt-5.4-mini` 1249 |
| HIGH | `anthropic/claude-sonnet-5` 1279, `qwen/qwen3.8-27b` 1275, `openai/gpt-5.6-terra` 1273, `google/gemini-3.5-flash-lite` 1273 |
| MAX | `openai/gpt-5.4` 1306, `google/gemini-3.6-flash` 1303, `openai/gpt-5.5` 1300, `google/gemini-3.1-pro-preview` 1300 |
| ULTRA | `anthropic/claude-fable-5` 1331, `anthropic/claude-opus-5.5` 1328, `anthropic/claude-fable-5.1` 1325, `google/gemini-3.8-flash` 1324 |

## read.pdf - 20 models

Source: LMArena document; rank split of the best 20 (board too small for bands).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `meta/muse-spark-1.1` 1464, `google/gemini-3.5-flash` 1462, `anthropic/claude-sonnet-5` 1460, `google/gemini-3.6-flash` 1456 |
| MID | `meta/muse-spark-1.3` 1473, `openai/gpt-5.6-terra` 1468, `openai/gpt-6-astra` 1467, `anthropic/claude-opus-4.5` 1466 |
| HIGH | `openai/gpt-5.6-sol` 1480, `google/gemini-3.7-flash` 1476, `anthropic/claude-opus-4.8` 1475, `openai/gpt-5.4` 1473 |
| MAX | `anthropic/claude-opus-4.7` 1496, `openai/gpt-5.5` 1484, `google/gemini-3.8-flash` 1482, `anthropic/claude-sonnet-4.6` 1482 |
| ULTRA | `anthropic/claude-fable-5.1` 1515, `anthropic/claude-opus-5` 1509, `anthropic/claude-opus-4.6` 1508, `anthropic/claude-fable-5` 1497 |

## image.make - 20 models

Source: LMArena text-to-image; rank split of the best 20 (board too small for bands).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `minimax/minimax-h3-image` 1197, `recraft/recraft-v4.1-utility-pro` 1169, `black-forest-labs/flux.2-max` 1161, `black-forest-labs/flux.2-flex` 1156 |
| MID | `google/gemini-3.1-flash-lite-image` 1249, `bytedance-seed/seedream-5-0-pro` 1248, `google/gemini-3-pro-image` 1246, `qwen/qwen-image-2.1-pro` 1227 |
| HIGH | `meta/muse-image` 1266, `google/gemini-3.1-flash-image` 1256, `qwen/qwen-image-3-pro` 1254, `microsoft/mai-image-2.5` 1252 |
| MAX | `openai/gpt-image-2` 1382, `microsoft/mai-image-2.6` 1330, `google/gemini-nano-banana-2.1` 1328, `x-ai/grok-imagine-image-2.0` 1318 |
| ULTRA | `openai/gpt-image-2.5-sunburst` 1429, `openai/gpt-image-2.6-sunburst` 1406, `openai/gpt-image-2.5-flare` 1398, `openai/gpt-image-2.6-flare` 1384 |

## image.edit - 20 models

Source: LMArena image edit; rank split of the best 20 (board too small for bands).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `bytedance-seed/seedream-4.5` 1302, `bytedance-seed/seedream-5-0-lite` 1293, `google/gemini-2.5-flash-image` 1292, `black-forest-labs/flux.2-max` 1262 |
| MID | `google/gemini-3.1-flash-image` 1387, `qwen/qwen-image-2.1-pro` 1363, `minimax/minimax-h3-image` 1359, `google/gemini-3.1-flash-lite-image` 1313 |
| HIGH | `meta/muse-image` 1401, `microsoft/mai-image-2.5` 1400, `bytedance-seed/seedream-5-0-pro` 1392, `google/gemini-3-pro-image` 1391 |
| MAX | `openai/gpt-image-2.6-flare` 1460, `x-ai/grok-imagine-image-2.0` 1437, `microsoft/mai-image-2.6` 1428, `google/gemini-nano-banana-2.1` 1427 |
| ULTRA | `openai/gpt-image-2.5-sunburst` 1519, `openai/gpt-image-2.5-flare` 1484, `openai/gpt-image-2.6-sunburst` 1476, `openai/gpt-image-2` 1462 |

## video.make - 18 models

Source: LMArena text-to-video + image-to-video; rank split of the best 20 (board too small for bands).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `alibaba/wan-2.6` 1316, `minimax/hailuo-2.3` 1234, `runway/gen-4.5` 1223, `kwaivgi/kling-video-o1` 1201 |
| MID | `google/veo-3.1` 1381, `x-ai/grok-imagine-video` 1376, `google/veo-3.1-fast` 1374, `kwaivgi/kling-v3.0-pro` 1353 |
| HIGH | `black-forest-labs/flux-3-video` 1471, `x-ai/grok-imagine-video-1.5` 1470, `alibaba/happyhorse-1.0` 1436, `alibaba/wan-2.7` 1382 |
| MAX | `bytedance/seedance-2.0` 1482, `alibaba/wan-3.0` 1479, `minimax/hailuo-3` 1475 |
| ULTRA | `google/gemini-omni-1.2-flash` 1522, `google/gemini-omni-1.1-flash` 1500, `bytedance/seedance-2.5` 1487 |

## speech.in (world) - 17 models

Source: AA speech-to-text WER (to 2.6 %) then HF Open ASR average WER (from 5.93 %).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `mistralai/voxtral-small-24b-2507-stt`, `openai/whisper-large-v3`, `mistralai/voxtral-mini-3b-2507`, `openai/whisper-large-v3-turbo` |
| MID | `openai/gpt-transcribe`, `meta/muse-voice-transcribe-1.0`, `nvidia/parakeet-tdt-0.6b-v3`, `qwen/qwen3-asr-0.6b` |
| HIGH | `nvidia/nemotron-3.5-transcribe`, `qwen/qwen3-asr-1.7b`, `assemblyai/universal-3-5-pro` |
| MAX | `mistralai/voxtral-mini-transcribe-3-0`, `x-ai/grok-stt-2.0`, `google/gemini-3.5-transcribe` |
| ULTRA | `microsoft/mai-transcribe-2`, `elevenlabs/scribe-v2`, `mistralai/voxtral-small-transcribe-3-0` |

## speech.in (Indian languages) - only 8 reachable - 8 models

Source: voiceofindia.ai STT (15 Indian languages, OI-WER) + HF Open ASR Hindi WER.

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `nvidia/nemotron-3.5-transcribe`, `assemblyai/universal-3-5-pro` |
| MID | `openai/gpt-transcribe` |
| HIGH | `meta/muse-voice-transcribe-1.0`, `elevenlabs/scribe-v2` |
| MAX | `google/gemini-3.5-transcribe`, `google/gemini-3.8-flash` |
| ULTRA | `microsoft/mai-transcribe-2` |

## speech.out (world) - 17 models

Source: AA text-to-speech arena + TTS Arena V2 (16 Nov 2026).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `elevenlabs/eleven-flash-v2.5`, `google/gemini-3.1-flash-tts-preview`, `hexgrad/kokoro-82m`, `fish-audio/s1` |
| MID | `elevenlabs/eleven-turbo-v2.5`, `qwen/qwen-audio-3.0-tts-plus`, `minimax/speech-2.8-turbo`, `google/gemini-3.8-flash-lite-tts` |
| HIGH | `google/gemini-3.8-flash-tts`, `fish-audio/drama-3`, `elevenlabs/eleven-multilingual-v2` |
| MAX | `minimax/speech-2.8-hd`, `fish-audio/s2-pro`, `speechify/simba-3.5` |
| ULTRA | `elevenlabs/eleven-v4`, `elevenlabs/eleven-v4-turbo`, `elevenlabs/eleven-v3` |

## speech.out (Indian languages) - only 4 reachable - 4 models

Source: voiceofindia.ai TTS vote arena (10 Indian languages).

| Level | Models (OpenRouter id) |
|---|---|
| LOW | (none scored - uses the nearest level) |
| MID | `google/gemini-3.8-flash-lite-tts` |
| HIGH | `google/gemini-3.1-flash-tts-preview` |
| MAX | `google/gemini-3.8-flash-tts` |
| ULTRA | `elevenlabs/eleven-v4` |

## music.make - only 2 reachable - 2 models

Source: Music Arena + AA music.

| Level | Models (OpenRouter id) |
|---|---|
| LOW | `google/lyria-3-clip-preview` |
| MID | (none scored - uses the nearest level) |
| HIGH | `google/lyria-3-pro-preview` |
| MAX | (none scored - uses the nearest level) |
| ULTRA | (none scored - uses the nearest level) |

## Short pools after other providers (research 05, D11)

| Kind | Before | After | Added (provider) |
|---|---|---|---|
| speech.in (Indian) | 8 | **10** -> **20** with direct makers (D12, below) | Amazon Transcribe + Azure (Eden AI) |
| music.make | 2 | **8** | ULTRA Suno v6, Suno v6 Mini (Kie.ai); MAX Mureka V9.5, Lyria 3.5 (fal) + Lyria 3 Pro; HIGH Stable Audio 3 Medium, ElevenLabs Music v2.5 (fal); LOW Lyria 3 Clip |
| speech.out (Indian) | 4 | 4 -> **20** with direct makers (D12, below) | |

**Better models from other providers that join full pools** (the weakest drops to keep 20): video - SkyReels V4
(WaveSpeed, HIGH, only after their written permission), Sora 2 Pro (fal, MID), Vidu Q3 Pro (Replicate / WaveSpeed, MID),
PixVerse V5.6 (fal, LOW); images - Reve 2.1 (fal, HIGH, check it is live), Ideogram 4 (fal, LOW).

**Still below 10 without vendor APIs:** Indian voice out (4) and music (8). The best Indian speech models (Sarvam
Saaras v3 / Bulbul, Bodhan, Cartesia Sonic 3.6, Maya 2) are sold only by the companies themselves - not through
OpenRouter or any multi-model provider.

## Indian voice pools, full boards + direct makers (D12, voiceofindia.ai read in full 16 Nov 2026)

Route: **OR** OpenRouter, **fal / Kie / Eden** multi-model provider, **direct** = the maker's own API.

### speech.in (Indian languages) - 20 models
Board: voiceofindia.ai speech-to-text, 32 models, 21,020 held-out phone samples in 15 languages, OI-WER (lower = better).

| Level | Models (OI-WER, route) |
|---|---|
| ULTRA | Bodhan Indic Transcribe Core 3.39 % (direct), Sarvam Saaras v3 3.69 % (direct), Bodhan Indic Transcribe Flex 4.01 % (direct), Amazon Transcribe 4.69 % (Eden / AWS) |
| MAX | MAI-Transcribe-2 4.79 % (OR), MAI-Transcribe-1.5 4.91 % (OR), Gemini 3.5 Transcribe 5.59 % (OR), ElevenLabs Scribe v2 5.76 % (OR) |
| HIGH | Azure Fast Transcription 5.77 % (Eden / Azure), Maya Transcribe One 5.85 % (direct), Gemini 3.8 Flash 6.25 % (OR), Nemotron 3.5 Transcribe 6.59 % (OR) |
| MID | Azure Realtime Transcription 6.80 % (Azure), Gemini 3 Flash 6.81 % (OR), GPT Transcribe 6.94 % (OR), Gnani Prisma v2.5 7.24 % (direct) |
| LOW | Grok Voice Transcribe 2.0 7.84 % (OR), GPT Live Transcribe 8.42 % (OpenAI direct), Gemma E4B 8.80 % (OR), Deepgram Nova 3 8.94 % (OR) |

Left out: SraVaani (open weights only - would need self-hosting), Grok streaming (same model as Grok 2.0 for this use).

### speech.out (Indian languages) - 20 models
Board: voiceofindia.ai text-to-speech, 23 models, 44,405 blind votes by native listeners in 10 languages.

| Level | Models (Elo, route) |
|---|---|
| ULTRA | ElevenLabs v4 1119 (OR), Gemini 3.8 Flash TTS 1101 (OR), Cartesia Sonic 3.6 1100 (direct), Gemini 3.1 Flash TTS 1084 (OR) |
| MAX | Gemini 3.8 Flash-Lite TTS 1071 (OR), Maya 2 Native 1063 (direct), Cartesia Sonic 3.5 1052 (Together / direct), Gemini 2.5 Pro TTS 1050 (Google direct) |
| HIGH | Murf Falcon 1037 (direct), Gnani Vachana TTS v3 1028 (direct), ElevenLabs v3 1028 (OR), Smallest AI Lightning 3.1 Pro 1026 (direct) |
| MID | Mirai Minds Mira-TTS 1007 (direct), Chariot TTS-v0 988 (direct), Cartesia Sonic 3 982 (Together / direct), Google Chirp 3 HD 972 (Google direct) |
| LOW | Sarvam Bulbul v3 972 (direct), MiniMax Speech 2.8 HD 965 (OR), TeenageWorks Teen-V1 963 (direct), Microsoft MAI Voice 1 924 (Azure / direct) |

Note: Sarvam Bulbul v3 sits LOW on this independent board (972, 9,360 votes) although Sarvam's own numbers put it higher.

## Below 10, said plainly (before research 05)

- **Indian-language speech in (8), Indian-language speech out (4), music (2):** OpenRouter does not carry the other
  scored models. The better ones need direct company routes: speech in - Sarvam Saaras v3, Bodhan Indic Transcribe,
  Amazon Transcribe, Azure Speech, Fonada Kapture, AI4Bharat IndicConformer (self-host); speech out - Cartesia Sonic,
  Maya; music - ACE Music, Suno (no official API found), Mureka, Eleven Music, Stable Audio, Riffusion.
- **Indian-language text:** the `write.lang / translate` pool (18) is ranked on the pooled non-English vote; no board
  ranks Hindi / Marathi / Tamil text yet (research 03).

## Other caveats

- `tools`, `extract`, `facts`, `research` are **proxies** (no live public tool-calling / extraction / search board in the
  CC-BY data); the AA, BFCL-current and Search-arena numbers in research 01 are not in this cut.
- Arena votes alone: newer models it has not scored much (Claude Fable 5.2, GPT-6 Astra, GPT-6.1 Sol) sit low or are
  missing although other boards put them at the top; they move up once a second board is in the feed.
- Name matches checked by hand but not confirmed by the vendor: MiniMax H3 = `minimax/hailuo-3`, Grok Voice Transcribe
  2.0 = `x-ai/grok-stt-2.0`, OpenAudio S2 = `fish-audio/s2-pro`, Qwen-Image 2.1 = `qwen/qwen-image-2.1-pro`.
- Every id above was listed by OpenRouter on 16 Nov 2026 (checked by the script).
