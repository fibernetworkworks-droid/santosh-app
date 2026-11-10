"""v0.442 SAB KAAM CALL PAR: on a voice call EVERY Hoola tool is reachable - declared ones directly, everything else via
santosh_kaam. Before this, 122 of 483 chat tools had no route: Gemini naming one got 'Unknown tool', and the persona
gave no hint that santosh_kaam could do them (Sheets formatting, Drive access, campaigns, desks, MoSPI...)."""
import asyncio
import json

from app import voice
from app.agent import tools


def test_every_chat_tool_has_a_route_on_a_call():
    names = {t["name"] for t in tools.TOOLS}
    assert len(names) > 300
    lost = sorted(n for n in names if not voice.call_route(n))
    assert not lost, lost
    declared = {t["name"] for t in voice._tool_specs()}
    for n in names:
        if voice.call_route(n) == "declared":
            assert n in declared, n
    assert voice.call_route("no_such_tool_xyz") == ""


def test_declared_list_did_not_grow():
    specs = voice._tool_specs()
    assert len(json.dumps(specs, ensure_ascii=False)) <= voice.VOICE_TOOL_BUDGET
    assert "sheet_format" not in {t["name"] for t in specs}


def test_persona_sends_unknown_jobs_to_santosh_kaam():
    assert "ANY job you have no tool for on this call" in voice.PERSONA and "Never say 'nahi kar sakta'" in voice.PERSONA


class Fake:
    user_buf = "Sheet ka header bold kar do"
    _mcp_route = {}

    class ctx:
        place = ""

    def _place(self, request=""):
        return ""

    def __init__(self):
        self.asked = []

    async def _delegate(self, request):
        self.asked.append(request)
        return {"status": "working"}


def test_an_undeclared_tool_goes_to_the_full_brain_not_unknown():
    f = Fake()
    out = asyncio.run(voice.Call._execute(f, "sheet_format", {"spreadsheet": "Sales", "format": {"bold": True}}))
    assert out == {"status": "working"} and "Sheet ka header bold" in f.asked[0] and "sheet_format" in f.asked[0]
    out = asyncio.run(voice.Call._execute(Fake(), "no_such_tool_xyz", {}))
    assert out == {"error": "Unknown tool no_such_tool_xyz"}
