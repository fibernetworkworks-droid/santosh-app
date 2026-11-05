"""v0.556 SEEDHA RAASTA - the owner: "NOW CHECK HOW ALL SURFACES RESPOND FOR SIMPLE TASK AND WHICH MODEL IT USE".

Measured through the REAL chat turn (console and phone share it) with a recording fake model: a simple ask goes to
the chat model (Sonnet 5.5) with the chat budget (2,000 tokens), no thinking, no raised effort, in ONE call. Two waste
paths were found and closed in app/agent/hard.py:
1. a bare sum ("12 aur 15 ka total kitna?") counted as a WORD PROBLEM and ran on Opus at 16,000 tokens with thinking
   at effort high - a word problem now needs a story (12+ words) or 3+ numbers;
2. a plain make / do request with numbers ("50 chairs ka quotation bana do Rs 1200 each") fell into the 'maybe' zone
   and held the reply for the Haiku judge (up to 2.5 s) - a make / do request with no reasoning signal skips it.
Every calibrated hard ask (HARD 50, HOLDOUT 21, hard card 27) stays hard; the voice call stays on Gemini Live."""
import asyncio

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, txt  # noqa: F401

SIMPLE = ["namaste", "Akola mein kal mausam kaisa rahega?", "12 aur 15 ka total kitna?",
          "Kal subah 7 baje yaad dilana dawai leni hai", "Ek chhota birthday message likh do Riya ke liye",
          "50 chairs ka quotation bana do Rs 1200 each, GST alag"]


def test_simple_asks_run_on_the_chat_model_in_one_light_call(gz, monkeypatch):  # noqa: F811
    from app.agent.santosh import run_turn
    for ask in SIMPLE:
        brain = _set_brain(monkeypatch, FakeBrain([([txt("Theek hai, ho gaya.")], "end_turn")] * 4))
        asyncio.run(run_turn(gz["conv"], ask, tenant_id="default"))
        assert len(brain.seen) == 1, ask
        kw = brain.seen[0]
        assert kw["model"] == "claude-sonnet-5-5" and kw["max_tokens"] == 2000, ask
        assert "thinking" not in kw and not (kw.get("extra_body") or {}).get("output_config"), ask


@pytest.mark.parametrize("ask", ["12 aur 15 ka total kitna?", "2 + 2 kitna hota hai",
                                 "50 chairs ka quotation bana do Rs 1200 each, GST alag",
                                 "Make an invoice for Rahul Traders, 20 bags cement at 380 rupees"])
def test_bare_sums_and_make_requests_are_neither_hard_nor_maybe(ask):
    from app.agent import hard
    v = hard.assess(ask)
    assert not v["hard"] and not v["maybe"], v


def test_real_hard_asks_stay_hard():
    from app.agent import hard
    from app.quality import hard_asks, hard_card
    assert all(hard.assess(a["text"] if isinstance(a, dict) else a)["hard"] for a in hard_asks.HARD)
    assert sum(hard.assess(a["text"])["hard"] for a in hard_card.SET) >= 27
    for q in ("Ek gaon mein 100 log hain, har din 2% badhte hain, 1 saal baad kitne honge?",
              "Kitne customers chahiye 1 lakh mahina kamane ke liye agar har order pe 120 bachta hai?",
              "Ek business plan bana do 2 saal ka meri bakery ke liye",
              "Kya mujhe GST ke liye registration lena chahiye ya nahi agar turnover 30 lakh hai?"):
        assert hard.assess(q)["hard"], q


def test_a_call_answers_on_gemini_live_by_default():
    from app.config import get_settings
    from app import voiceengine
    assert get_settings().gemini_live_model == "gemini-3.8-live"
    assert voiceengine.pick("someone-else")[0] == "gemini"          # OpenAI real voice = her trial pick only
