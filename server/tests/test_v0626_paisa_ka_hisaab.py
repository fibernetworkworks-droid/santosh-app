"""v0.626 PAISA KA HISAAB (owner: "i just put rs 500 now it is rs 162 --- by just doing 2 calls"). Gemini Live bills the
whole context on every reply; the old meter counted audio minutes only. Gemini's own usage_metadata is now summed per call."""
from types import SimpleNamespace as N

from app import usage, voice


def _um(text_in, audio_in, audio_out):
    return N(prompt_token_count=text_in + audio_in, response_token_count=audio_out, cached_content_token_count=0,
             thoughts_token_count=0,
             prompt_tokens_details=[N(modality="TEXT", token_count=text_in), N(modality="AUDIO", token_count=audio_in)],
             response_tokens_details=[N(modality="AUDIO", token_count=audio_out)])


def test_every_reply_counts_the_whole_context(env):
    c = N(call_id="c1", stats={}, ctx=N(tenant_id="default"))
    for _ in range(40):                                   # 40 replies, each re-reading ~32k text + 10k audio
        voice.Call._usage_add(c, _um(32000, 10000, 400))
    voice.Call._record_usage(c)
    u = c.stats["gemini_tokens"]
    assert u["replies"] == 40 and u["text_in"] == 1_280_000 and u["audio_in"] == 400_000
    want = usage.cost("gemini-3.8-live", tok_in=1_280_000, audio_in=400_000, audio_out=16_000)
    assert abs(c.stats["cost_usd"] - want) < 1e-6 and c.stats["cost_usd"] > 2.0   # dollars, not the old cents


def test_no_usage_falls_back_to_audio_minutes(env):
    c = N(call_id="c2", stats={}, ctx=N(tenant_id="default"), audio_in_bytes=32000 * 60, audio_out_bytes=48000 * 60)
    voice.Call._record_usage(c)
    assert 0 < c.stats["cost_usd"] < 0.05 and "gemini_tokens" not in c.stats


def test_a_call_with_no_phone_never_wakes_gemini_for_news():
    """v0.627: notes reaching a call whose phone is away used to reconnect Gemini and bill a reply spoken to nobody."""
    import asyncio
    c = N(parked=True, hold=False, ws=None, stats={}, audio=asyncio.Queue(maxsize=10),
          _wake=asyncio.Event(), _held_texts=[])
    c._wake_up = lambda why: voice.Call._wake_up(c, why)
    voice.Call.push(c, "text", "[Kaam update] report ban gayi")
    assert not c._wake.is_set() and c.stats["wakes_held_no_phone"] == 1
    c.ws = object()                                         # her phone is on the call
    voice.Call.push(c, "text", "dusri khabar")
    assert c._wake.is_set()


def test_a_call_waiting_for_her_phone_is_not_live_for_reminders(monkeypatch):
    import threading
    away = N(tenant="t1", closed=threading.Event(), ws=None)
    monkeypatch.setitem(voice.ACTIVE, "conv_x", [(None, away)])
    assert voice.tenant_live("t1") is False                 # the reminder rings her instead of going unheard
    away.ws = object()
    assert voice.tenant_live("t1") is True
