"""P0 kinds of work and where each one's quality comes from (plan section 2 + 8.1, research 01-05).

A board is (config, category) in the LMArena dataset `lmarena-ai/leaderboard-dataset` (CC-BY-4.0). Rating boards
(Elo-style `rating`) and score boards (`score` + `rank`, the agent boards) are both read; `cut.py` puts them on one
"points below the best" scale.
"""
from __future__ import annotations

LEVELS = ["LOW", "MID", "HIGH", "MAX", "ULTRA"]
# plan 8.2.5 / D10: quality bands below the best model of the kind (points), top level first
BANDS = [("ULTRA", 0, 25), ("MAX", 25, 50), ("HIGH", 50, 80), ("MID", 80, 120), ("LOW", 120, 190)]
PER_LEVEL = 4            # up to 4 per level = up to 20 per kind (D10)
MIN_POOL = 10            # a kind under this is a warning (D10)

# needs: "tools" = tool calling, "structured" = structured output, "img_in" = takes pictures, "doc_in" = files/pictures
KINDS: dict[str, dict] = {
    "chat":       {"boards": [("text", "overall")], "out": "text"},
    "write":      {"boards": [("text", "creative_writing")], "out": "text"},
    "summarise":  {"boards": [("text", "longer_query"), ("text", "overall")], "out": "text"},
    "reason":     {"boards": [("text", "math"), ("text", "hard_prompts")], "out": "text"},
    "code":       {"boards": [("webdev", "overall"), ("text", "coding")], "out": "text", "need": "tools"},
    "tools":      {"boards": [("agent", "overall"), ("agent_tool_hallucination", "overall")], "out": "text",
                   "need": "tools"},
    "extract":    {"boards": [("text", "instruction_following")], "out": "text", "need": "structured",
                   "proxy": "no public extraction board; instruction following stands in"},
    "read.long":  {"boards": [("text", "longer_query")], "out": "text"},
    "facts":      {"boards": [("text_factuality", "overall"), ("search_factuality", "overall")], "out": "text"},
    "research":   {"boards": [("search", "overall"), ("search_factuality", "overall")], "out": "text", "need": "tools"},
    "write.lang": {"boards": [("text", "non_english")], "out": "text",
                   "languages": ["spanish", "chinese", "french", "german", "japanese", "korean", "russian", "polish"],
                   "proxy": "Indian languages: no public text board yet (research 03) - the pooled non-English vote"},
    "read.image": {"boards": [("vision", "overall"), ("vision", "ocr")], "out": "text", "need": "img_in"},
    "read.pdf":   {"boards": [("document", "overall")], "out": "text", "need": "doc_in"},
    "image.make": {"boards": [("text_to_image", "overall")], "out": "image"},
    "image.edit": {"boards": [("image_edit", "overall")], "out": "image", "need": "img_in"},
    "video.make": {"boards": [("text_to_video", "overall"), ("image_to_video", "overall")], "out": "video"},
    # voice + music: not in the LMArena data - Indian voice from voiceofindia.ai (read monthly), the rest hand-kept
    "speech.in.indian":  {"live": "voi_stt"},
    "speech.out.indian": {"live": "voi_tts"},
    "speech.in":  {"manual": True},
    "speech.out": {"manual": True},
    "music.make": {"manual": True},
}
# kinds that read another kind's table (plan section 2)
SAME = {"route": "chat", "plan": "reason", "code.small": "code", "check": "facts", "translate": "write.lang"}
# kinds the Box does not rank yet
NOT_RANKED = {"embed": "Hoola keeps its current embedder (no reusable embedding board in the feed yet)"}
