"""v0.221 SAHI JAWAB + PATLA PROMPT: one reply rulebook for chat / console / quick lane / voice, and a system prompt
that carries only the guides of the tool families a turn admitted."""
from app.agent import prompts, replystyle
from app.agent.admit import CORE_FAMILIES, plan_for
from app.config import get_settings
from tests.test_bazar import bz  # noqa: F401  (fresh DB + a real conversation)


def test_rulebook_replaces_the_fixed_length_rule():
    s = prompts.SYSTEM
    assert "Two to four sentences in chat" not in s
    assert "{REPLY_RULES}" not in s
    for pin in ("How you understand her", "How you answer", "Answer first", "Length follows the question",
                "Half-clear ask", "Never fill a gap with a made-up fact", "check your draft once",
                "Formatting stays light"):
        assert pin in s, pin
    # the key-values-before-acting rule survived the rewrite
    assert "repeat the key values once" in s


def test_rulebook_has_no_braces_for_voice_format():
    for txt in (replystyle.CHAT, replystyle.VOICE, replystyle.QUICK):
        assert "{" not in txt and "}" not in txt


def test_voice_and_quick_lane_share_the_rules():
    from app import voice
    from app.agent import quick
    for g in ("m", "f"):
        pp = voice.persona_prompt("Meera", g)
        assert "How you understand and answer" in pp
        assert pp.index("How you understand and answer") < pp.index("When to speak")
        pp.format(lang="hi-IN", now="now", context="ctx")      # still a valid format string
    assert replystyle.QUICK in quick.SYSTEM


def test_full_guide_when_no_families():
    assert prompts.system_text(None) == prompts.SYSTEM
    full = prompts.system_prompt(False, "", None)
    assert "GST work (she" in full and "Payroll (" in full


def test_slim_guide_is_much_smaller_and_indexes_the_rest():
    full = len(prompts.SYSTEM)
    t = prompts.system_text(CORE_FAMILIES)
    assert len(t) < full * 0.35, (len(t), full)
    assert "More skills you have" in t and "tool_search" in t
    assert "GST work" in t[t.index("More skills you have"):]          # named in the index, guide not loaded
    assert "GST work (she" not in t
    # core rules always ride
    for pin in ("How you answer", "WHERE a website opens", "LAMBA KAAM", "Internet:", "Your memory"):
        assert pin in t, pin


def test_admitted_family_brings_its_guide():
    st = get_settings()
    gst = plan_for("GST return file karna hai october ka", st)
    t = prompts.system_text(gst.families)
    assert "GST work (she" in t and "Payroll (" not in t
    mail = plan_for("Sharma ji ko mail bhejo report ke saath", st)
    assert "Email (the user's" in prompts.system_text(mail.families)
    assert "Email (the user's" not in prompts.system_text(CORE_FAMILIES)


def test_everyday_words_never_tag_a_block():
    # "gst" / "product" written as plain words in a general rule must not move that rule out of the core
    for text, need, _ in prompts._guide():
        if text.startswith("- Tools load by need"):
            assert need is None


def test_every_block_lands_somewhere():
    # nothing of the guide is lost: kept blocks + indexed labels cover every block
    blocks = prompts._guide()
    assert "\n".join(b for b, _, _ in blocks) == prompts.SYSTEM
    deferred = [lbl for _, need, lbl in blocks if need is not None]
    assert deferred and all(deferred)


def test_agent_loop_sends_the_slim_prompt_and_grows_it_on_tool_search(bz, monkeypatch):
    import asyncio
    from app.agent import santosh
    seen = []

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        sys_text = system if isinstance(system, str) else "".join(b.get("text", "") for b in system)
        seen.append(sys_text)
        if len(seen) == 1:
            return ([{"type": "tool_use", "id": "t1", "name": "tool_search", "input": {"need": "gst return"}}],
                    "tool_use", brain)
        return ([{"type": "text", "text": "Ho gaya."}], "end_turn", brain)

    monkeypatch.setattr(santosh, "_think", fake_think)
    asyncio.run(santosh.run_turn(bz["conv"], "hi kaise ho"))
    assert len(seen) >= 2
    assert "GST work (she" not in seen[0] and len(seen[0]) < len(prompts.SYSTEM) * 0.5
    assert "GST work (she" in seen[1]            # tool_search opened gst -> its guide joined the prompt


def test_prompt_slim_off_sends_the_full_guide(bz, monkeypatch):
    import asyncio
    from app.agent import santosh
    monkeypatch.setenv("PROMPT_SLIM", "false")
    get_settings.cache_clear()
    seen = []

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        seen.append(system if isinstance(system, str) else "".join(b.get("text", "") for b in system))
        return ([{"type": "text", "text": "Theek."}], "end_turn", brain)

    monkeypatch.setattr(santosh, "_think", fake_think)
    try:
        asyncio.run(santosh.run_turn(bz["conv"], "hi"))
    finally:
        get_settings.cache_clear()
    assert "GST work (she" in seen[0]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.281.0"
