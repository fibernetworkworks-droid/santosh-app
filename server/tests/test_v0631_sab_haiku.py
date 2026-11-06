"""v0.631 SAB HAIKU (owner: "DO EVERY THING HAIKU FOR NOW --- SIMPLE TO HARD"): every Claude call runs on claude_one_model,
enforced at the SDK door; an out-of-credit error says so plainly."""
import asyncio
import types

from app import usage
from app.config import get_settings


def test_every_claude_model_is_moved(monkeypatch):
    monkeypatch.setenv("CLAUDE_ONE_MODEL", "claude-haiku-5-5")
    get_settings.cache_clear()
    for m in ("claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1"):
        assert usage.one_model({"model": m, "max_tokens": 5})["model"] == "claude-haiku-5-5"
    assert usage.one_model({"model": "gemini-3.8-flash"})["model"] == "gemini-3.8-flash"   # Gemini untouched
    monkeypatch.setenv("CLAUDE_ONE_MODEL", "")
    get_settings.cache_clear()
    assert usage.one_model({"model": "claude-opus-5-5"})["model"] == "claude-opus-5-5"     # switched off


def test_the_sdk_door_sends_haiku(monkeypatch):
    monkeypatch.setenv("CLAUDE_ONE_MODEL", "claude-haiku-5-5")
    get_settings.cache_clear()
    usage.install()
    from anthropic import AsyncAnthropic
    seen = []

    async def fake_post(self, *a, **kw):
        seen.append(kw.get("body", {}).get("model"))
        raise RuntimeError("stop")
    import anthropic._base_client as bc
    monkeypatch.setattr(bc.AsyncAPIClient, "post", fake_post)
    c = AsyncAnthropic(api_key="x")
    try:
        asyncio.run(c.messages.create(model="claude-opus-5-5", max_tokens=5, messages=[{"role": "user", "content": "q"}]))
    except RuntimeError:
        pass
    assert seen == ["claude-haiku-5-5"]


def test_out_of_credit_is_said_plainly():
    from app.agent.santosh import _friendly_error
    e = Exception("Error code: 400 - {'error': {'message': 'Your credit balance is too low to access the Anthropic API.'}}")
    assert "credit khatam" in _friendly_error(e)
