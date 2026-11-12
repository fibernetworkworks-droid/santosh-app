"""v0.858 PC FLOW (owner, after ordering a pizza on her PC: 'VERY CONFUSE BETWEEN MERA PC AND HOOLA ON PC ... it opens
EDGE not CHROME ... wandering between 3 Edge, Chrome on user PC, Chrome on Hoola own PC' + 'it must ask the user
which pizza do you want' + 'more real-time voice'): the browser she names is the one used, her follow-ups go INTO the
running task (never a new task / another computer), the task asks her real choices (ask_user) and her chat / call
answer goes straight back in, and a live call hears the milestones."""
import asyncio
import types

import pytest

from app.pc import brain, operator


def tu(i, tool, **a):
    return {"type": "tool_use", "id": f"t{i}", "name": tool, "input": a}


def test_named_browser_words():
    n = operator._named_browser
    assert n("OPEN THE CHROM BROWSER AND ORDER A PIZZA FROM SWIGGY") == "chrome"
    assert n("Chrome mein swiggy kholo") == "chrome"
    assert n("edge nahi, chrome mein karo") == "chrome"
    assert n("not edge, use chrome") == "chrome"
    assert n("microsoft edge mein kholo") == "edge"
    assert n("firefox me") == "firefox"
    assert n("swiggy se pizza order karo") == ""
    assert n("chrome nahi") == ""


def _fake_desktop(monkeypatch, front="Microsoft Edge"):
    calls, state = [], {"win": front, "typed": ""}

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        args = args or {}
        if action == "screen":
            return {"image_b64": "QUJD", "width": 1280, "height": 720, "active_window": state["win"], "windows": [state["win"]]}
        if action == "page_text":
            return {"text": "Swiggy - Order food online"}
        calls.append((args.get("op") or action, dict(args)))
        if action == "open_app":
            state["win"] = "New Tab - Google Chrome"
        if args.get("op") == "type":
            state["typed"] = args.get("text", "")
        if args.get("op") == "key" and args.get("keys") == "enter" and state["typed"]:
            state["win"] = "Swiggy - Google Chrome"
        return {"ok": True}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(operator.asyncio, "sleep", lambda s: real_sleep(0))
    return calls, state


def test_open_url_uses_the_browser_she_named(monkeypatch):
    calls, state = _fake_desktop(monkeypatch, front="Microsoft Edge")
    op = operator.Op(id="b1", tenant="default", conv="c", task="Chrome kholo aur Swiggy se pizza order karo")
    op.browser, op.browser_src = operator._named_browser(op.task), "said"
    out = asyncio.run(operator._do(op, "open_url", {"url": "swiggy.com"}))
    names = [c[0] for c in calls]
    assert ("open_app", {"name": "Google Chrome"}) in calls
    assert "open_url" not in names                         # the desktop's 'first running browser' path is NOT used
    assert names.index("open_app") < names.index("key")    # Chrome first, then the address
    # a freshly opened Chrome already shows a blank New Tab: no second empty tab
    assert {"op": "key", "keys": "ctrl+t"} not in [c[1] for c in calls]
    assert {"op": "key", "keys": "delete"} in [c[1] for c in calls]   # inline autocomplete cleared before Enter
    assert "Google Chrome" in out and "Swiggy" in out


def test_named_browser_already_in_front_is_not_opened_again(monkeypatch):
    calls, _ = _fake_desktop(monkeypatch, front="Gmail - Google Chrome")
    op = operator.Op(id="b2", tenant="default", conv="c", task="chrome mein swiggy")
    op.browser = "chrome"
    asyncio.run(operator._do(op, "open_url", {"url": "https://www.swiggy.com"}))
    assert not [c for c in calls if c[0] == "open_app"]


def test_no_browser_named_keeps_the_old_path(monkeypatch):
    calls, _ = _fake_desktop(monkeypatch)
    op = operator.Op(id="b3", tenant="default", conv="c", task="swiggy kholo")
    asyncio.run(operator._do(op, "open_url", {"url": "swiggy.com"}))
    assert [c for c in calls if c[0] == "open_url"]


def _loop(monkeypatch, turns, during=None):
    """Drive the real loop; `during(op)` runs once the task asked her something."""
    seen = []

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        if action == "screen":
            return {"image_b64": "QUJD", "width": 1280, "height": 720, "active_window": "Swiggy - Google Chrome", "windows": []}
        return {"ok": True}
    monkeypatch.setattr(operator, "_pc", fake_pc)
    monkeypatch.setattr(operator, "SETTLE_S", {})
    monkeypatch.setattr(operator, "_event", lambda op: None)
    monkeypatch.setattr(operator, "_work", lambda op, name: None)
    script = iter(turns)

    async def think(op, client, messages, params, retry):
        seen.append([str(messages[-1]["content"])])
        return brain.Reply(content=next(script), stop="tool_use")
    monkeypatch.setattr(brain, "think", think)

    async def do(op, name, a):
        return "ok"
    monkeypatch.setattr(operator, "_do", do)
    from app.agent import santosh
    monkeypatch.setattr(santosh, "get_client", lambda: None)
    notes = []
    monkeypatch.setattr(santosh, "_save", lambda conv, role, content, display=None, **k: notes.append(display))
    from app.pc import memory
    monkeypatch.setattr(memory, "remember", lambda *a, **k: None)
    monkeypatch.setattr(memory, "prompt_block", lambda *a, **k: "")
    spoken = []
    from app import voice
    monkeypatch.setattr(voice, "inject", lambda conv, text: spoken.append(text) or 1)
    op = operator.Op(id="pcop_flow", tenant="t_flow", conv="c_flow", task="Swiggy se pizza order karo")

    async def main():
        operator._loop = asyncio.get_running_loop()
        op.task_obj = asyncio.create_task(operator._run(op))
        operator.OPS[op.id] = op
        if during:
            for _ in range(200):
                await asyncio.sleep(0)
                if op.ask is not None:
                    break
            during(op)
        await op.task_obj
    try:
        asyncio.run(main())
    finally:
        operator.OPS.pop(op.id, None)
    return op, seen, notes, spoken


def test_ask_user_waits_for_her_chat_answer(monkeypatch):
    got = {}

    def answer(op):
        assert operator.pending_ask("t_flow") is op
        got["r"] = operator.answer_from_chat("t_flow", "c_flow", "Farmhouse wala")
    op, seen, notes, spoken = _loop(monkeypatch, [
        [tu(1, "ask_user", question="Kaunsa pizza chahiye?", options=["Margherita - Rs 239", "Farmhouse - Rs 459"])],
        [tu(2, "done", answer="Farmhouse cart mein")],
    ], during=answer)
    assert got["r"]["ok"] and "Farmhouse" in got["r"]["say"]
    assert any("Kaunsa pizza" in (n or "") and "2. Farmhouse - Rs 459" in (n or "") for n in notes)   # options in chat
    assert any("Kaunsa pizza" in t for t in spoken)                                                    # asked on the call
    assert any('HER ANSWER: "Farmhouse wala"' in t for t in seen[-1])
    assert op.status == "done" and op.ask is None


def test_her_new_words_reach_the_running_task(monkeypatch):
    def steer(op):
        pass
    turns = [[tu(1, "wait", seconds=1)], [tu(2, "done", answer="ok")]]

    async def fake_pc(op, action, args=None, timeout=40, log=True):
        if action == "screen":
            return {"image_b64": "QUJD", "width": 1, "height": 1, "active_window": "x", "windows": []}
        return {"ok": True}
    op = operator.Op(id="pcop_n", tenant="t_n", conv="c_n", task="Swiggy se pizza")
    op.task_obj = types.SimpleNamespace(done=lambda: False)
    operator.OPS[op.id] = op
    try:
        assert operator.tell("t_n", "c_n", "Chrome mein karo, Edge mein nahi") is op
        assert op.browser == "chrome"
        msgs = [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]}]
        operator._take_notes(op, msgs)
        last = msgs[-1]["content"][-1]["text"]
        assert "HER NEW WORDS" in last and "Chrome mein karo" in last and "Google Chrome" in last
        assert op.notes == []
    finally:
        operator.OPS.pop(op.id, None)


def test_stop_words_are_never_an_answer(monkeypatch):
    op = operator.Op(id="pcop_s", tenant="t_s", conv="c_s", task="x")
    op.ask = {"id": "a", "question": "?", "options": [], "at": 1}
    operator.OPS[op.id] = op
    try:
        assert operator.answer_from_chat("t_s", "c_s", "band karo") is None
        assert operator.answer_from_chat("t_none", "c", "Margherita") is None    # nothing waiting -> normal chat
    finally:
        operator.OPS.pop(op.id, None)


def test_pc_do_follow_up_steers_the_running_task(monkeypatch):
    from app.agent import pc_tools
    op = operator.Op(id="pcop_r", tenant="t_r", conv="c_r", task="Swiggy se pizza")
    op.task_obj = types.SimpleNamespace(done=lambda: False)
    operator.OPS[op.id] = op
    started = []

    async def start(*a, **k):
        started.append(a)
        return {"status": "running", "session_id": "new"}
    monkeypatch.setattr(operator, "start", start)
    ctx = types.SimpleNamespace(tenant_id="t_r", conversation_id="c_r")
    try:
        r = asyncio.run(pc_tools.pc_do(ctx, "Chrome mein kholo aur order karo", _wait=0))
        assert r["steered"] and r["session_id"] == "pcop_r" and not started
        assert op.notes and op.browser == "chrome"
        r = asyncio.run(pc_tools.pc_do(ctx, "Tally kholo", fresh=True))     # a really new job still starts fresh
        assert started
    finally:
        operator.OPS.pop(op.id, None)


def test_chat_stays_on_her_pc_while_her_task_runs():
    from app.agent import pick, where
    from app.agent.tools import ToolError
    op = operator.Op(id="pcop_w", tenant="t_w", conv="c_w", task="Swiggy se pizza")
    op.task_obj = types.SimpleNamespace(done=lambda: False)
    operator.OPS[op.id] = op
    try:
        assert where.working("c_w") == "pc"
        ctx = types.SimpleNamespace(admit=None, place="", conversation_id="c_w")
        with pytest.raises(ToolError, match="HER OWN PC"):
            pick.check("hoola_pc_do", {"task": "chrome kholo aur pizza order karo"}, ctx)
        ctx.place = "hoolapc"                                   # she names Hoola's PC in this message: allowed
        pick.check("hoola_pc_do", {"task": "chrome kholo"}, ctx)
    finally:
        operator.OPS.pop(op.id, None)
    assert where.working("c_w") != "pc" or where._WORK.get("c_w")


def test_call_hears_milestones_but_not_every_click(monkeypatch):
    spoken = []
    from app import voice
    monkeypatch.setattr(voice, "inject", lambda conv, text: spoken.append(text) or 1)
    op = operator.Op(id="v", tenant="t", conv="c", task="x")
    op.action = "Chrome khol raha hoon"
    operator._speak(op, "click")
    assert not spoken
    operator._speak(op, "open_app")
    operator._speak(op, "open_url")             # within 12 s: not twice
    assert len(spoken) == 1 and "Chrome khol raha hoon" in spoken[0]


def test_prompt_says_ask_her_choices_and_keep_her_browser():
    assert "SHE DECIDES THE CHOICES" in operator.SYSTEM and "ask_user" in operator.SYSTEM
    assert "THE BROWSER SHE NAMED" in operator.SYSTEM
    assert any(t["name"] == "ask_user" for t in operator.TOOLS)


def test_call_answer_goes_straight_into_the_pc_task(monkeypatch):
    """On a call her spoken answer is caught from her own words (like a spoken OTP), Gemini need not pass it on."""
    from app import voice
    op = operator.Op(id="pcop_c", tenant="t_c", conv="c_c", task="pizza")
    op.ask = {"id": "a", "question": "Kaunsa pizza?", "options": [], "at": 1}
    operator.OPS[op.id] = op
    pushed = []
    call = types.SimpleNamespace(tenant="t_c", conv="c_c", stats={}, push=lambda k, t: pushed.append(t),
                                 _prev_turn_end=__import__("time").time())   # the question was spoken in an earlier turn
    try:
        assert voice.Call._pcask_listen(call, "Farmhouse wala lo") is True
        assert op.answer == "Farmhouse wala lo" and pushed and "already went to the PC task" in pushed[0]
        assert voice.Call._pcask_listen(call, "aur kuch") is False          # nothing waiting any more
    finally:
        operator.OPS.pop(op.id, None)


def test_call_brain_ask_answers_with_her_words_only():
    op = operator.Op(id="pcop_b", tenant="t_b", conv="c_b", task="pizza")
    op.ask = {"id": "a", "question": "?", "options": [], "at": 1}
    operator.OPS[op.id] = op
    try:
        assert operator.answer_from_chat("t_b", "c_b", "Margherita\n(Call ne samjha: margherita pizza)")
        assert op.answer == "Margherita"
    finally:
        operator.OPS.pop(op.id, None)


def test_call_reading_never_turns_her_pc_into_hoolas():
    """A call ask = her words + '(Call ne samjha: ...)'. Gemini talks TO her, so its 'aapke PC' is HER PC."""
    from app.agent import where
    assert where.place("mere PC pe Chrome kholo\n(Call ne samjha: aapke PC par Chrome kholna)") == "pc"
    assert where.place("Chrome kholo aur pizza mangao\n(Call ne samjha: aapke PC par Chrome kholna)") == "pc"
    assert where.place("Hoola ke PC par kholo\n(Call ne samjha: aapke PC par)") == "hoolapc"   # her words win
    assert where.place("aapke PC pe kholo") == "hoolapc"                                        # chat unchanged


def test_call_voice_knows_it_can_work_on_her_pc():
    from app import voice
    assert "NEVER say you cannot access or control her PC" in voice.PERSONA_BRAIN
    assert "HER PC" in voice.BRAIN_DELEGATE["description"]
    voice.PERSONA_BRAIN.format(context="x")      # still a valid template


def test_call_pc_ask_the_voice_answered_itself_goes_to_the_brain(monkeypatch):
    """Live call log: 3 turns, 0 tools, 'I cannot access your PC'. A PC ask is never left to the voice model."""
    from app import voice
    from app.pc import hub
    monkeypatch.setattr(hub.hub, "is_online", lambda t, *a, **k: True)
    monkeypatch.setattr(voice, "get_settings", lambda: types.SimpleNamespace(voice_brain=True))
    sent, pushed = [], []

    async def main():
        async def delegate(req):
            sent.append(req)
            return {"result": "Chrome khol diya"}
        call = types.SimpleNamespace(tenant="t", conv="c", stats={}, call_id="x", _tools=set(),
                                     push=lambda k, t: pushed.append(t), push_news=lambda t: pushed.append(t),
                                     _delegate=delegate, _PC_ASK=voice.Call._PC_ASK, _PC_DO=voice.Call._PC_DO,
                                     _ASKS_BACK=voice.Call._ASKS_BACK)
        assert voice.Call._pc_rescue(call, "Mere PC pe Chrome kholo aur Swiggy se pizza order karo") is True
        await asyncio.gather(*list(call._tools))
        assert voice.Call._pc_rescue(call, "aaj mausam kaisa hai") is False      # not a PC ask
        assert voice.Call._pc_rescue(call, "band karo") is False
    asyncio.run(main())
    assert sent == ["Mere PC pe Chrome kholo aur Swiggy se pizza order karo"]
    assert any("Hoola CAN work on her PC" in p for p in pushed) and any("Chrome khol diya" in p for p in pushed)


def test_chat_order_on_her_account_site_asks_before_hoolas_browser(monkeypatch):
    from app.agent import pick
    from app.agent.tools import ToolError
    from app.pc import hub
    ctx = types.SimpleNamespace(admit=None, place="", conversation_id="c_o", tenant_id="t_o")
    monkeypatch.setattr(hub.hub, "is_online", lambda t, *a, **k: True)
    with pytest.raises(ToolError, match="aapke PC par karun"):
        pick.check("computer_operator", {"action": "start", "task": "Swiggy se pizza order karo"}, ctx)
    pick.check("computer_operator", {"action": "start", "task": "IRCTC PNR status dekho"}, ctx)   # no order: fine
    ctx.place = "hoola"                                                                              # she named it
    pick.check("computer_operator", {"action": "start", "task": "Swiggy se pizza order karo"}, ctx)
    monkeypatch.setattr(hub.hub, "is_online", lambda t, *a, **k: False)
    ctx.place = ""
    pick.check("browse_web", {"task": "Amazon pe order karo"}, ctx)                               # PC off: as before


def test_no_browser_named_and_none_open_uses_chrome_not_background_edge(monkeypatch):
    """Her Swiggy test: no window of any browser open, Edge running in the background -> the desktop took Edge."""
    calls, _ = _fake_desktop(monkeypatch, front="Program Manager")
    from app.pc import memory
    monkeypatch.setattr(memory, "recall", lambda t: [])
    op = operator.Op(id="d1", tenant="default", conv="c", task="Swiggy se pizza order karo")
    op.browser, op.browser_src = operator._browser_for("default", op.task)
    assert (op.browser, op.browser_src) == ("chrome", "default")
    asyncio.run(operator._do(op, "open_url", {"url": "swiggy.com"}))
    assert ("open_app", {"name": "Google Chrome"}) in calls and not [c for c in calls if c[0] == "open_url"]


def test_remembered_browser_and_open_window_win_over_the_default(monkeypatch):
    from app.pc import memory
    monkeypatch.setattr(memory, "recall", lambda t: [{"task": "Edge mein gmail kholo"}, {"task": "notepad kholo"}])
    assert operator._browser_for("t", "swiggy kholo") == ("edge", "remembered")
    calls, _ = _fake_desktop(monkeypatch, front="WhatsApp - Microsoft Edge")
    op = operator.Op(id="d2", tenant="t", conv="c", task="swiggy kholo")
    op.window = "WhatsApp - Microsoft Edge"                     # what the last screenshot showed in front
    op.browser, op.browser_src = "chrome", "default"
    asyncio.run(operator._do(op, "open_url", {"url": "swiggy.com"}))
    # she named none now and is USING Edge: a new tab in that Edge window, never a new Chrome / Edge window
    assert not [c for c in calls if c[0] in ("open_app", "open_url")]
    assert {"op": "key", "keys": "ctrl+t"} in [c[1] for c in calls]


def test_default_chrome_missing_never_falls_back_to_the_default_browser(monkeypatch):
    # v0.862: the desktop's own open_url hands a link to Windows = her DEFAULT browser (Edge); on her PC it is never
    # used - the model gets the error and brings her browser forward itself
    calls, state = _fake_desktop(monkeypatch, front="Program Manager")

    async def no_chrome(op, action, args=None, timeout=40, log=True):
        if action == "open_app":
            raise RuntimeError("not installed")
        if action == "screen":
            return {"image_b64": "QUJD", "width": 1, "height": 1, "active_window": "Program Manager", "windows": []}
        calls.append((args or {}).get("op") or action)
        return {"ok": True}
    monkeypatch.setattr(operator, "_pc", no_chrome)
    op = operator.Op(id="d3", tenant="t", conv="c", task="swiggy kholo")
    op.browser, op.browser_src = "chrome", "default"
    out = asyncio.run(operator._do(op, "open_url", {"url": "swiggy.com"}))
    assert "open_url" not in calls and out.startswith("ERROR")


def test_edge_title_with_zero_width_space_is_edge():
    assert operator._browser_of("Swiggy - Personal - Microsoft\u200bEdge") == "edge"
    assert operator._browser_of("Gmail - Google Chrome") == "chrome"
    assert operator._browser_of("Notepad") == ""


def test_browser_words_in_ordinary_speech_are_not_picks():
    n = operator._named_browser
    assert n("cutting edge design banao") == "" and n("Chrome extension install karo") == ""
    assert n("OPEN THE CHROM BROWSER") == "chrome" and n("Edge mein kholo") == "edge"


def test_answer_only_from_this_chat_and_not_a_question_back():
    op = operator.Op(id="pcop_q", tenant="t_q", conv="c_q", task="pizza")
    op.ask = {"id": "a", "question": "Kaunsa?", "options": ["Margherita - Rs 239", "Farmhouse - Rs 459"], "at": 1}
    operator.OPS[op.id] = op
    try:
        assert operator.answer_from_chat("t_q", "other_chat", "Farmhouse") is None        # another chat: not hers
        assert operator.answer_from_chat("t_q", "c_q", "kitna time lagega?") is None      # a question back
        assert operator.answer_from_chat("t_q", "c_q", "ek minute") is None
        assert operator.answer_from_chat("t_q", "c_q", "2") and op.answer == "2"
    finally:
        operator.OPS.pop(op.id, None)


def test_haan_to_hoolas_pc_question_names_her_pc():
    from app.agent import where
    where.offer("c_y", "pc")
    assert where.remember("c_y", "haan karo") == "pc"
    assert where.remember("c_z", "haan") == ""                       # no question asked there


def test_chrome_kholo_names_her_pc_when_online():
    from app.agent import where
    assert where.browser_ask("Chrome kholo aur Swiggy se pizza order karo")
    assert not where.browser_ask("apne chrome mein dekho")            # Hoola's own browser
    assert not where.browser_ask("cutting edge design")


def test_finished_task_releases_the_chat():
    from app.agent import where
    where.touch("c_r", "pc")
    where.release("c_r", "cancelled")
    assert where.working("c_r") == "" and where.current("c_r") == ""
