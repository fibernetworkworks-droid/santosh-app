"""v0.440 SOCH KE JAWAB - the live hard card measures for real (owner ran `hardcard --live --judge`: RIGHT 0/28, median
1.0 s, errors 0).

Two faults. (1) The card scored the APOLOGY: a turn whose model call failed returns "Maaf kijiye, abhi kuch gadbad ho
gayi (ref ...)" and that line was scored as an answer, so 28 dead turns read as 28 wrong answers with "errors 0" and the
cause went to 2>/dev/null. Now a turn that published its error / budget line is an ERROR row carrying the server's own
log lines, the card stops after 3 dead turns in a row, and `hardcard --ping` makes one tiny real call per model and
shape. (2) Holding a hard answer for the self-check (v0.436) switched the API call itself to ONE blocking request -
16k tokens + thinking - the only such call in Hoola, and its thinking never reached the Soch card. A held or big answer
now STREAMS from the API; the live reply alone decides what she sees.
"""
import asyncio
import json
import types

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import gz  # noqa: F401


class _Stream:
    def __init__(self, text):
        self.text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        async def gen():
            for ev in (types.SimpleNamespace(type="content_block_start", content_block=types.SimpleNamespace(type="text")),
                       types.SimpleNamespace(type="content_block_delta",
                                             delta=types.SimpleNamespace(type="text_delta", text=self.text))):
                yield ev
        return gen()

    async def get_final_message(self):
        return types.SimpleNamespace(content=[{"type": "text", "text": self.text}], stop_reason="end_turn",
                                     usage=None, model="m")


def _client(seen, text="Jawab"):
    async def create(**kw):
        seen.append(("create", kw))
        return types.SimpleNamespace(content=[{"type": "text", "text": text}], stop_reason="end_turn", usage=None)

    def stream(**kw):
        seen.append(("stream", kw))
        return _Stream(text)
    return types.SimpleNamespace(messages=types.SimpleNamespace(create=create, stream=stream))


def test_a_held_answer_still_streams_from_the_api(env, monkeypatch):
    from app import livereply
    from app.agent import santosh
    from app.config import get_settings
    seen = []
    monkeypatch.setattr(santosh, "get_client", lambda: _client(seen, "EMI 17,994.52"))
    live = livereply.Live("c-held", "default")
    live.block(stream=False)                                  # held for the self-check
    blocks, stop = asyncio.run(santosh._call_brain("claude", "sys", [{"role": "user", "content": "EMI?"}],
                                                   get_settings(), tools=[], live=live, max_tokens=16000))
    assert seen[0][0] == "stream" and blocks[0]["text"] == "EMI 17,994.52"
    assert live.sent == ""                                    # nothing shown: she sees it only after the check


def test_a_big_answer_with_no_live_reply_streams_quietly_and_a_small_one_does_not(env, monkeypatch):
    from app.agent import santosh
    from app.config import get_settings
    seen = []
    monkeypatch.setattr(santosh, "get_client", lambda: _client(seen))
    asyncio.run(santosh._call_brain("claude", "s", [{"role": "user", "content": "x"}], get_settings(), tools=[],
                                    max_tokens=16000))
    asyncio.run(santosh._call_brain("claude", "s", [{"role": "user", "content": "x"}], get_settings(), tools=[],
                                    max_tokens=400))
    assert [k for k, _ in seen] == ["stream", "create"]


def test_a_failed_turn_is_an_error_row_with_its_cause_never_a_score(gz, monkeypatch):  # noqa: F811
    from app.agent import santosh
    from app.quality import hard_card as H

    async def boom(*a, **k):
        raise RuntimeError("Error code: 400 - model claude-opus-5-5 does not support this")
    monkeypatch.setattr(santosh, "_think", boom)
    card = asyncio.run(H.live_card(H.pick(only="emi,cagr,sip,doubling"), tenant="default"))
    assert card["errors"] == 3 and card["answered"] == 0 and card["asks"] == 3 and card["planned"] == 4
    row = card["rows"][0]
    assert "does not support this" in row["error"] and any("error ref" in x for x in row["log"])
    text = "\n".join(H.lines(card))
    assert "STOPPED after 3 of 4" in text and "server's own log lines" in text and "emi: ERROR" in text


def test_ping_reports_each_model_and_shape(env, monkeypatch):
    from app.agent import santosh
    from app.quality import hard_card as H
    seen = []
    cli = _client(seen, "4")
    real = cli.messages.stream

    def stream(**kw):
        if "thinking" in kw and kw.get("model") == "claude-opus-5-5":
            raise RuntimeError("Error code: 400 - thinking.type: adaptive is not supported")
        return real(**kw)
    cli.messages.stream = stream
    monkeypatch.setattr(santosh, "get_client", lambda: cli)
    out = asyncio.run(H.ping())
    joined = "\n".join(out)
    assert "claude-opus-5-5 plain: OK" in joined and "claude-opus-5-5 thinking: FAILED" in joined
    assert "adaptive is not supported" in joined and len(out) == 7          # header + 2 models x 3 shapes


def test_cli_ping_flag(monkeypatch, capsys):
    from app.quality import __main__ as M
    from app.quality import hard_card as H

    async def ping():
        return ["key set: True", "  m plain: OK"]
    monkeypatch.setattr(H, "ping", ping)
    assert M.main(["hardcard", "--ping"]) == 0
    assert "m plain: OK" in capsys.readouterr().out


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.735.0"
    json.dumps({})
