"""v0.634 TEZ DIMAAG (owner: Gemini + Haiku slow; her 15:27 call: 3-5 s before every first step, 21 s on one ask). A call's
brain turn reads only the checkpoint + the last few exchanges (not the whole chat), and is never a held 'hard' turn."""
import types

from app.agent import santosh


def _hist(n):
    out = []
    for i in range(n):
        out.append({"role": "user", "content": f"sawaal {i}"})
        out.append({"role": "assistant", "content": [{"type": "text", "text": f"jawab {i}"}]})
    return out


def test_brain_turn_reads_only_recent_exchanges():
    st = types.SimpleNamespace(voice_brain_history=3, chat_context="claude")
    hist = _hist(40) + [{"role": "user", "content": "abhi ka sawaal"}]
    state = {"turn_start": len(hist) - 1}
    tok = santosh.VOICE_BRAIN_NOW.set(True)
    try:
        msgs = santosh._request(hist, "sys", [], "claude", "c1", state, st)
    finally:
        santosh.VOICE_BRAIN_NOW.reset(tok)
    texts = [str(m["content"]) for m in msgs]
    assert len(msgs) == 7 and "sawaal 37" in texts[0] and "abhi ka sawaal" in texts[-1]
    assert not any("sawaal 5'" in t or "'sawaal 5" in t for t in texts)


def test_chat_turn_keeps_the_whole_chat(env):
    from app.config import get_settings
    hist = _hist(10) + [{"role": "user", "content": "abhi"}]
    msgs = santosh._request(hist, "sys", [], "claude", "c1", {"turn_start": len(hist) - 1}, get_settings())
    assert len(msgs) == len(hist)


def test_brain_turn_is_never_hard():
    import inspect
    src = inspect.getsource(santosh)
    assert 'getattr(settings, "hard_detect", True) and not VOICE_BRAIN_NOW.get()' in src
