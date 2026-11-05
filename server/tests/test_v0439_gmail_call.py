"""v0.439 GMAIL POORA CALL PAR: on a voice call every Gmail tool has a way in. Her voice test hit 11 of the 23 Gmail
tools that the call had no tool for (labels, snooze, drafts, filters, vacation, bulk...), so the call said it could not."""
import asyncio
import json

from app import voice
from app.agent import email_tools

DECLARED = {"email_check", "email_read", "email_thread", "email_triage", "email_attachment", "email_draft", "email_forward",
            "email_action", "email_delete", "email_follow_up", "email_contacts", "email_snooze", "email_drafts"}


def test_every_gmail_tool_reaches_a_call():
    names = {t["name"] for t in voice._tool_specs()}
    for t in email_tools.EMAIL_TOOLS:
        n = t["name"]
        assert n in voice.VOICE_TOOL_NAMES, f"{n} is not reachable on a call"
        if n in DECLARED:
            assert n in names and not voice.via_kaam(n), n
        else:
            assert voice.via_kaam(n) and n not in names, n


def test_call_tools_still_fit_and_are_valid():
    specs = voice._tool_specs()
    assert len(json.dumps(specs, ensure_ascii=False)) <= voice.VOICE_TOOL_BUDGET
    for t in specs:
        if t["name"].startswith("email_"):
            assert not voice.schema_problems(t["input_schema"]), t["name"]


def test_persona_names_the_new_mail_tools():
    line = next(l for l in voice.PERSONA.splitlines() if l.startswith("- Email:"))
    for n in ("email_thread", "email_snooze", "email_drafts"):
        assert n in line
    assert "out-of-office" in line and "santosh_kaam" in line


def test_vacation_on_a_call_goes_to_the_full_brain():
    asked = []

    class Fake:
        user_buf = "5 se 10 November tak out of office laga do"
        _mcp_route = {}

        class ctx:
            place = ""

        def _place(self, request=""):
            return ""

        async def _delegate(self, request):
            asked.append(request)
            return {"status": "working"}

    out = asyncio.run(voice.Call._execute(Fake(), "email_vacation", {"action": "set"}))
    assert out == {"status": "working"} and "out of office" in asked[0] and "email_vacation" in asked[0]
