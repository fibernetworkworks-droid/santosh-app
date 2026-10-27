"""v0.149 the voice call declares a slim tool list (the 280-tool list filled Gemini Live's context and calls dropped)."""
import asyncio
import json

from app import voice


def test_voice_tool_list_fits_the_budget():
    specs = voice._tool_specs()
    names = [t["name"] for t in specs]
    size = len(json.dumps(specs, ensure_ascii=False))
    assert size <= voice.VOICE_TOOL_BUDGET, size
    assert len(specs) <= 170, len(specs)
    assert len(names) == len(set(names))
    assert "santosh_kaam" in names and "create_reminder" in names and "music_control" in names
    for n in ("darzi", "darzi_dekho", "society", "gst_dekho", "app_banao", "hoola_deal"):
        assert n not in names and voice.via_kaam(n)
    for t in specs:
        assert len(t["description"]) <= 700
        assert t["name"] == "santosh_kaam" or t["name"] == "side_talk" or t["name"] in voice.VOICE_TOOL_NAMES
    # the live config still builds with them
    cfg = voice.live_config("Puck", "hi", "", None)
    assert len(cfg.tools[0].function_declarations) == len(specs)


def test_a_sahayak_tool_named_in_a_call_goes_to_the_full_brain():
    asked = []

    class Fake:
        user_buf = "Riya ka blouse order likh do"
        _mcp_route = {}

        class ctx:
            place = ""

        def _place(self, request=""):
            return ""

        async def _delegate(self, request):
            asked.append(request)
            return {"status": "working"}

    out = asyncio.run(voice.Call._execute(Fake(), "darzi", {"action": "new_order"}))
    assert out == {"status": "working"}
    assert "Riya ka blouse" in asked[0] and "darzi" in asked[0]
