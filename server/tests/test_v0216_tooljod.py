"""v0.216.0 TOOL-JOD - every tool_use rides with its result; the second 400 is dead.

The owner's report (the day after v0.215.0 NO-PREFILL shipped): 'Maaf kijiye, abhi kuch gadbad ho gayi.
(Error code: 400 - ... "messages.12: tool_use ids were found without tool_result blocks immediately
after: toolu_01BDvvVMZtTnhnxv") --- THIS ERROR IS IT IS SAME'. Same disease family, second symptom:

- v0.213-215's prefill guard appended a TEXT nudge when the array ended with an assistant message - but
  when that final assistant message carried tool_use blocks (a team sub-agent interrupted mid-step by
  Rokiye: asyncio.CancelledError is a BaseException their `except Exception` never caught, so the history
  kept [.., assistant(tool_use)]; or a max_tokens cut inside a tool call), the nudge landed right after
  the unanswered tool_use -> this exact 400, on every retry, for every long work.
- _sanitize's old check was 'is there ANY tool_result in the next message' - a PARTIAL pair (assistant
  asked A+B, only A's result survived the crash window between the two _save calls) passed straight
  through to the API.

Fixes, each tested here: (1) _api_ready in agent/santosh.py - the last line of defence before EVERY model
call: every unanswered tool_use gets an honest synthetic result in the very next user message, mid-array
partial pairs are rebuilt, orphan results are dropped, tool-tailed arrays end with results (not with a
text nudge), all on a COPY; (2) _sanitize is now per-ID, so partial pairs and orphans are repaired at
load time too; (3) clean user-final arrays return the SAME list untouched - byte-identical happy path.
"""
import asyncio
import copy
import json
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

REPO = Path(__file__).resolve().parents[2]

LOST_ID = "toolu_01BDvvVMZtTnhnxv"   # the exact id from the owner's error line
OTHER_ID = "toolu_01AAAAAAAAAAAAAAAA"


def _tu(tid: str, name: str = "gmail_list") -> dict:
    return {"type": "tool_use", "id": tid, "name": name, "input": {}}


def _tr(tid: str, text: str = "natija") -> dict:
    return {"type": "tool_result", "tool_use_id": tid, "content": text}


class _FakeMsg:
    def __init__(self):
        self.content = [{"type": "text", "text": "theek hai, natija dekh liya"}]
        self.stop_reason = "end_turn"


class _FakeMessages:
    def __init__(self, log: list):
        self._log = log

    async def create(self, **kw):
        self._log.append(kw)
        return _FakeMsg()


class _FakeClient:
    def __init__(self):
        self.log: list[dict] = []
        self.messages = _FakeMessages(self.log)


@pytest.fixture()
def claude_only(bz, monkeypatch):
    """Fake Anthropic client + no cheap brain + no self-check, so every call is captured and deterministic."""
    from app.agent import llm, santosh
    from app.config import get_settings

    fake = _FakeClient()
    old = santosh._client
    santosh.set_client(fake)
    monkeypatch.setattr(llm, "cheap_brain", lambda: None)
    st = get_settings()
    old_check = st.agent_self_check
    st.agent_self_check = False
    yield fake, st
    st.agent_self_check = old_check
    santosh.set_client(old)


def _assert_api_valid(msgs: list[dict]) -> None:
    """The API's own contract, asserted: every tool_use answered by the immediately next user message,
    no orphan results, results first in a user message, and the array ends with a user message."""
    assert msgs, "empty array"
    for i, m in enumerate(msgs):
        assert m.get("role") in ("user", "assistant")
        if m.get("role") != "assistant":
            rb = [b for b in m.get("content", []) if isinstance(b, dict) and b.get("type") == "tool_result"] \
                if isinstance(m.get("content"), list) else []
            if rb:
                prev = msgs[i - 1] if i else None
                pids = {b.get("id") for b in (prev.get("content") or [])
                        if isinstance(b, dict) and b.get("type") == "tool_use"} \
                    if prev is not None and prev.get("role") == "assistant" else set()
                assert {b.get("tool_use_id") for b in rb} <= pids, f"orphan result at {i}"
                assert m["content"][0].get("type") == "tool_result", f"results must come first at {i}"
            continue
        ids = [b.get("id") for b in m.get("content", []) if isinstance(b, dict) and b.get("type") == "tool_use"]
        if not ids:
            continue
        assert i + 1 < len(msgs), f"tool_use at {i} has no next message"
        nxt = msgs[i + 1]
        assert nxt.get("role") == "user", f"tool_use at {i} followed by {nxt.get('role')}"
        rids = [b.get("tool_use_id") for b in nxt.get("content", [])
                if isinstance(b, dict) and b.get("type") == "tool_result"]
        assert set(ids) <= set(rids), f"unanswered ids at {i}: {set(ids) - set(rids)}"
    assert msgs[-1].get("role") == "user", "array must end with a user message"


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.319.0"
    assert "0.319.0+359" in (REPO / "pubspec.yaml").read_text()


def test_tool_tailed_array_gets_result_not_text_nudge(claude_only):
    """THE bug: the v0.213 guard met an array ending in assistant(tool_use) and appended its text nudge
    right after it -> 'tool_use ids were found without tool_result blocks immediately after'. Now the
    tail tool_use gets its honest result message instead."""
    from app.agent import santosh
    from app.config import get_settings
    fake, st = claude_only
    history = [
        {"role": "user", "content": "mail check kar"},
        {"role": "assistant", "content": [_tu(LOST_ID), {"type": "text", "text": "dekh raha hoon"}]},
    ]

    async def go():
        return await santosh._call_brain("claude", "system", history, st, tools=[])

    asyncio.run(go())
    sent = fake.log[0]["messages"]
    _assert_api_valid(sent)
    tail = sent[-1]
    assert tail["role"] == "user"
    first = {k: v for k, v in tail["content"][0].items() if k != "cache_control"}   # the shaper's breakpoint rides on it
    assert first == {"type": "tool_result", "tool_use_id": LOST_ID,
                     "is_error": True, "content": santosh.TOOL_RESULT_LOST}


def test_owner_error_shape_messages12(claude_only):
    """The owner's shape: a long, healthy history, then the turn's words, then the interrupted step's
    tool_use - where the old guard dropped its TEXT nudge and the API answered 'messages.12: tool_use
    ids were found without tool_result blocks immediately after'. The sent array now answers that
    tool_use with the honest synthetic result - the 400 is impossible."""
    from app.agent import santosh
    from app.config import get_settings
    fake, st = claude_only
    history: list[dict] = []
    for k in range(3):   # three healthy tool exchanges, strictly alternating
        kid = f"toolu_0{k:02d}x"
        history.append({"role": "user", "content": f"kaam number {k}"})
        history.append({"role": "assistant", "content": [_tu(kid, "gmail_list")]})
        history.append({"role": "user", "content": [_tr(kid), {"type": "text", "text": "aage badho"}]})
        history.append({"role": "assistant", "content": [{"type": "text", "text": f"ho gaya {k}"}]})
    history.append({"role": "user", "content": "aur yeh karo"})                       # this attempt's words
    history.append({"role": "assistant", "content": [_tu(LOST_ID, "gmail_send")]})    # interrupted mid-step

    async def go():
        return await santosh._call_brain("claude", "system", history, st, tools=[])

    asyncio.run(go())
    sent = fake.log[0]["messages"]
    _assert_api_valid(sent)
    for i, m in enumerate(sent):
        if m["role"] == "assistant" and any(b.get("id") == LOST_ID for b in m["content"]
                                            if isinstance(b, dict) and b.get("type") == "tool_use"):
            nxt = sent[i + 1]
            assert nxt["role"] == "user" and nxt["content"][0]["tool_use_id"] == LOST_ID
            assert not any(b.get("type") == "text" for b in nxt["content"])   # no text nudge rides after it
            break
    else:
        pytest.fail("the interrupted step's tool_use never reached the request")


def test_partial_pair_rebuilt_with_synthetic_result(claude_only):
    """A partial pair (assistant asked A+B, only A's result survived the crash window) used to pass the
    old 'any result present' check and 400 on id B. Now the next user message answers BOTH: A's real
    result kept, B gets the honest synthetic one, results first."""
    from app.agent import santosh
    from app.config import get_settings
    fake, st = claude_only
    real_a = _tr(OTHER_ID, "A ka natija")
    history = [
        {"role": "user", "content": "do kaam karo"},
        {"role": "assistant", "content": [_tu(OTHER_ID, "gmail_list"), _tu(LOST_ID, "gmail_list")]},
        {"role": "user", "content": [real_a]},
    ]

    async def go():
        return await santosh._call_brain("claude", "system", history, st, tools=[])

    asyncio.run(go())
    sent = fake.log[0]["messages"]
    _assert_api_valid(sent)
    results = sent[2]["content"]
    assert results[0] is real_a or results[0] == real_a            # A's real result survived
    assert results[1]["tool_use_id"] == LOST_ID and results[1]["is_error"] is True
    assert results[1]["content"] == santosh.TOOL_RESULT_LOST


def test_orphan_result_dropped(claude_only):
    """A result whose call is gone (its assistant message was cut by the window / pruned) errors on its
    own ('unexpected tool_use_id'). It leaves the request; the message's other blocks stay."""
    from app.agent import santosh
    cleaned = santosh._api_ready([
        {"role": "user", "content": "bina call ke result"},
        {"role": "assistant", "content": [{"type": "text", "text": "ji"}]},
        {"role": "user", "content": [_tr("toolu_01ORPHAN"), {"type": "text", "text": "rider"}]},
    ])
    assert [b for b in cleaned[-1]["content"] if b.get("type") == "tool_result"] == []
    assert {"type": "text", "text": "rider"} in cleaned[-1]["content"]
    _assert_api_valid(cleaned)


def test_sanitize_partial_pair_at_load():
    """_sanitize is now per-ID: the DB's partial pair is repaired at LOAD - the assistant keeps only the
    answered call, the result row stays, nothing reaches the API half-paired."""
    from app.agent import santosh
    msgs = [
        {"role": "user", "content": "do kaam karo"},
        {"role": "assistant", "content": [{"type": "text", "text": "dekh raha hoon"}, _tu(OTHER_ID), _tu(LOST_ID)]},
        {"role": "user", "content": [_tr(OTHER_ID)]},
        {"role": "assistant", "content": [{"type": "text", "text": "ho gaya"}]},
    ]
    out = santosh._sanitize(msgs)
    a = out[1]["content"]
    assert OTHER_ID in {b.get("id") for b in a if b.get("type") == "tool_use"}
    assert LOST_ID not in {b.get("id") for b in a if b.get("type") == "tool_use"}
    assert {"type": "text", "text": "dekh raha hoon"} in a
    # load-time output is shape-valid once the call-time shaper has had its pass (it owns the user-last tail)
    _assert_api_valid(santosh._api_ready(out))


def test_sanitize_orphan_result_dropped():
    """Orphan results leave wherever they sit: a results-only message disappears, a rider keeps its text
    (merged into the adjacent same-role turn, the house rule since v0.108)."""
    from app.agent import santosh
    assert santosh._sanitize([{"role": "user", "content": [_tr("toolu_01X")]}]) == []
    out = santosh._sanitize([
        {"role": "user", "content": "pehla"},
        {"role": "user", "content": [_tr("toolu_01ORPHAN"), {"type": "text", "text": "rider"}]},
    ])
    assert len(out) == 1
    assert {"type": "text", "text": "rider"} in out[0]["content"]
    assert not any(b.get("type") == "tool_result" for b in out[0]["content"])


def test_happy_path_untouched(claude_only):
    """Clean user-final arrays: the SAME list object goes out (no copy, no mutation) and the request is
    byte-identical apart from the prompt-cache breakpoint the shaper always adds."""
    from app.agent import santosh
    from app.config import get_settings
    fake, st = claude_only
    history = [
        {"role": "user", "content": "do kaam karo"},
        {"role": "assistant", "content": [_tu(OTHER_ID, "gmail_list")]},
        {"role": "user", "content": [_tr(OTHER_ID), {"type": "text", "text": "aage badho"}]},
    ]
    clean = [{"role": "user", "content": "sawal"}, {"role": "assistant", "content": [{"type": "text", "text": "j"}]},
             {"role": "user", "content": "agla sawal"}]
    assert santosh._api_ready(clean) is clean                  # identity: untouched
    assert santosh._api_ready(history) is history              # healthy pair + rider: untouched too
    snapshot = copy.deepcopy(history)

    async def go():
        return await santosh._call_brain("claude", "system", history, st, tools=[])

    asyncio.run(go())
    sent = fake.log[0]["messages"]
    assert len(sent) == 3                                      # nothing appended, nothing folded
    assert sent[0] == history[0] and sent[1] == history[1]     # pre-breakpoint messages byte-identical
    assert history == snapshot


def test_copies_not_mutates(claude_only):
    """A broken array is repaired on a COPY: the caller's list and every dict inside it are untouched
    (team sub-agents keep appending to their shared history)."""
    from app.agent import santosh
    from app.config import get_settings
    fake, st = claude_only
    history = [
        {"role": "user", "content": "kaam karo"},
        {"role": "assistant", "content": [_tu(LOST_ID)]},
        {"role": "user", "content": [_tr(OTHER_ID)]},      # answers the WRONG id: partial/orphan mix
    ]
    snapshot = copy.deepcopy(history)

    async def go():
        return await santosh._call_brain("claude", "system", history, st, tools=[])

    asyncio.run(go())
    assert history == snapshot
    sent = fake.log[0]["messages"]
    _assert_api_valid(sent)
    assert len(sent) == 3                                  # rebuilt in place, nothing appended beyond the fold


def test_wake_turn_over_crashed_tool_loop(claude_only, bz):
    """End-to-end, the owner's morning: a long job died mid-step (assistant tool_use saved, result row
    never saved - the MEM-CURE OOM window), then the wake turn fires. Load-time _sanitize repairs the
    pair, the wake words ride last, the brain finally hears the report."""
    from app.agent import santosh
    conv = bz["conv"]
    santosh._save(conv, "user", "long kaam shuru karo", display="long kaam shuru karo")
    santosh._save(conv, "assistant", [_tu("toolu_01CRASHED", "gmail_list"),
                                      {"type": "text", "text": "dekh raha hoon"}])
    wake = "[Santosh worker update, not the user] Ek background kaam ka natija abhi aaya hai:\nKaam: Mail sweep\nNatija: poora ho gaya"

    async def go():
        return await santosh.run_turn(conv, wake, tenant_id="default", actor="wake", save_user=False)

    out = asyncio.run(go())
    fake, _st = claude_only
    assert fake.log, "the wake turn never called the model"
    first = fake.log[0]["messages"]
    _assert_api_valid(first)
    assert "background kaam ka natija" in json.dumps(first[-1]["content"], ensure_ascii=False)
    assert "dekh raha hoon" in json.dumps(first, ensure_ascii=False)   # the crashed step's words survive
    assert out.strip() == "theek hai, natija dekh liya"
