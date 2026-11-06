"""v0.630 HAIKU DIMAAG (owner: "HAIKU CAN DO ALL BASIC TASK PERFECTLY" + "SHIFT VOICE BRAIN ON HAIKU -- GEMINI FOR VOICE
ONLY"). An ordinary chat ask runs on Haiku (hard -> Opus, long -> Sonnet as before; a Haiku failure answers on Sonnet).
On a call Gemini Live only hears and speaks: ONE tool (santosh_kaam = the Hoola brain on Haiku with every chat tool),
a short persona, no memory brief - so Gemini re-reads ~2k chars a reply instead of ~14k tokens."""
import asyncio
import json
import types

from app.agent import santosh
from app.config import get_settings


def test_model_for_routes_by_ask():
    st = types.SimpleNamespace(agent_hard_model="claude-opus-5-5", chat_simple_model="claude-haiku-5-5",
                               voice_brain_model="claude-haiku-5-5")
    santosh.SIMPLE_MODEL.update(ok=True)
    assert santosh.model_for(st, hard=False, long_job=False) == "claude-haiku-5-5"
    assert santosh.model_for(st, hard=True, long_job=False) == "claude-opus-5-5"
    assert santosh.model_for(st, hard=False, long_job=True) == ""          # long jobs stay on Sonnet
    assert santosh.model_for(types.SimpleNamespace(chat_simple_model=""), False, False) == ""   # switched off
    tok = santosh.VOICE_BRAIN_NOW.set(True)
    try:
        st.chat_simple_model = ""
        assert santosh.model_for(st, False, False) == "claude-haiku-5-5"   # the call's brain, even with chat off
    finally:
        santosh.VOICE_BRAIN_NOW.reset(tok)


class _Err(Exception):
    pass


def test_haiku_refused_answers_on_sonnet_and_leaves_opus_alone(monkeypatch, env):
    seen = []

    async def create(**kw):
        seen.append(kw["model"])
        if kw["model"] == "claude-haiku-5-5":
            raise _Err("Error code: 404 - not_found_error: model: claude-haiku-5-5")
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text="ok")], stop_reason="end_turn",
                                     usage=None)
    monkeypatch.setattr(santosh, "get_client", lambda: types.SimpleNamespace(messages=types.SimpleNamespace(create=create)))
    santosh.SIMPLE_MODEL.update(ok=True, calls=0, failed=0)
    santosh.HARD_MODEL.update(ok=True, calls=0, failed=0)
    tok = santosh._MODEL_NOW.set("claude-haiku-5-5")
    try:
        asyncio.run(santosh._call_brain("claude", "s", [{"role": "user", "content": "q"}], get_settings(), tools=[]))
    finally:
        santosh._MODEL_NOW.reset(tok)
        ok = santosh.SIMPLE_MODEL["ok"]
        santosh.SIMPLE_MODEL.update(ok=True, calls=0, failed=0)
    assert seen == ["claude-haiku-5-5", "claude-sonnet-5-5"]
    assert ok is False and santosh.HARD_MODEL["ok"] is True


def _brain_on(monkeypatch):
    monkeypatch.setenv("VOICE_BRAIN", "true")
    monkeypatch.setenv("VOICE_LEAN_TOOLS", "true")
    get_settings.cache_clear()


def test_voice_carries_one_tool_and_a_short_persona(monkeypatch):
    from app import voice
    _brain_on(monkeypatch)
    specs = voice._tool_specs()
    p = voice.persona_prompt("Santosh", "m")
    f = voice.persona_prompt("Meera", "f")
    names = [t["name"] for t in specs]
    assert names[0] == "santosh_kaam" and set(names) <= {"santosh_kaam", "side_talk"}
    assert len(json.dumps(specs)) < 3000 and len(p) < 4000
    assert "EXACT words" in p and "Never answer from yourself" in p and "{context}" in p
    assert "You are female" in f and "You are male" not in f
    p.format(lang="Hinglish", now="now", context="ctx")
    from google.genai import types as gt
    assert voice._behavior_kw(gt, "santosh_kaam").get("behavior") in ({}.get("x"), gt.Behavior.BLOCKING)


def test_brain_gets_her_words_on_haiku(monkeypatch, env):
    from app import voice, turn_inbox
    _brain_on(monkeypatch)
    seen = {}

    async def run_owned(inbox_id, conv, text, tenant, voice_, context="", place="", **kw):
        seen.update(text=text, context=context, brain=santosh.VOICE_BRAIN_NOW.get())
        return "Aapke 3 naye mail hain."
    monkeypatch.setattr(turn_inbox, "accept", lambda *a, **k: None)
    monkeypatch.setattr(turn_inbox, "run_owned", run_owned)
    call = voice.Call.__new__(voice.Call)
    call.ctx = types.SimpleNamespace(tenant_id="default", conversation_id="c1", place="")
    call.conv, call.tenant, call.call_id, call.stats = "c1", "default", "t", {}
    call.user_buf, call.recent = "mere last 10 email ka ek line summary do", [("purana sawaal", "x")]
    call._place = lambda request="": ""
    out = asyncio.run(call._execute("santosh_kaam", {"request": "summarise emails"}))
    assert out == {"result": "Aapke 3 naye mail hain."}
    assert seen["text"].startswith("mere last 10 email") and "summarise emails" in seen["text"]
    assert seen["brain"] is True and "BOLA jayega" in seen["context"]
    assert call.stats["brain_turns"] == 1
    assert santosh.VOICE_BRAIN_NOW.get() is False          # never leaks out of the brain's own task
    call.user_buf = ""                                     # a note-driven call never re-runs her OLD ask
    asyncio.run(call._execute("santosh_kaam", {"request": "batao kya hua"}))
    assert seen["text"] == "batao kya hua"


def test_brain_context_is_tiny(monkeypatch):
    from app import voice
    _brain_on(monkeypatch)
    call = voice.Call.__new__(voice.Call)
    ctx, defs = asyncio.run(call._build_context(True))
    assert defs == [] and len(ctx) < 300
