"""Wave 13 MANN KI BAAT of the third deep audit (owner: "GO WAVE 13" - analysis, monitoring and feeling).

36 a research report is checked on EVERY turn that writes from a dossier (goal round, routine, call), not only hers
37 pylab having run no longer passes the maths check: the draft's figures must be in what the tools printed
38 the corrected answer is checked again (free checks), and still failing = said plainly under it
39 the reviewer skips the one-model rewrite (it is not the writer's own Haiku)
40 /healthz says not ok when the worker is stuck; a hung slot is cut; the loop watchdog runs from start
41 a female avatar's "Kaam ho gaya" stays right (only her own forms change)
42 the hard-coded lines follow her avatar; nobody calls her "Owner"
43 a non-urgent push is held in her quiet hours, the newest few sent after; her reminders and cards never wait
44 her mood is acknowledged (chat rule + call persona)
45 no "Aur kuch karna hai?" fallback, no OFFICE HOURS interview for an unclear ask, "phir boliye"
46 an error after tools ran warns before a blind repeat
47 the same background error is said once a night, not every 30 minutes
"""
from __future__ import annotations

import asyncio
import inspect
import time
import types

T = "default"


# ---------------------------------------------------------------- 36 research held on every actor
def test_a_research_turn_is_held_whoever_runs_it(monkeypatch):
    from app.agent import santosh
    from app.research import engine
    st = types.SimpleNamespace(hard_check=True)
    state = {"t0": time.time() - 5}
    monkeypatch.setitem(engine.LAST, "r36", {"_delivered": time.time(), "fields": []})
    assert santosh._hard_held(state, st, "r36")                    # a goal round / routine / call with a dossier
    assert not santosh._hard_held(state, st, "nothing-here")
    monkeypatch.setitem(engine.LAST, "r36b", {"_delivered": time.time() - 999})
    assert not santosh._hard_held(state, st, "r36b")               # an older dossier, not this turn's


# ---------------------------------------------------------------- 37 pylab ran but numbers from memory
def test_figures_must_be_in_what_pylab_printed():
    from app.agent import hard
    q = "10 lakh ka loan 9% par 5 saal, EMI kitni?"
    ev = "TOOL pylab input: print(round(emi,2))\nRESULT: 20758.36\n1245501.6"
    ok = hard.code_check(q, "EMI ₹20,758 hogi, total ₹12.46 lakh.", ["calculation"], ["pylab"], ev)
    assert ok == []
    bad = hard.code_check(q, "EMI ₹21,400 hogi, total ₹12,84,000.", ["calculation"], ["pylab"], ev)
    assert bad and "21,400" in bad[0]


# ---------------------------------------------------------------- 38 the corrected answer
def test_the_corrected_answer_is_checked_again():
    from app.agent import santosh
    src = inspect.getsource(santosh._steps_inner)
    assert 'state.get("hard_fixed")' in src and "free_only=True" in src and "HARD_UNSURE" in src
    assert "free_only" in inspect.signature(santosh._hard_check).parameters


# ---------------------------------------------------------------- 39 an independent reviewer
def test_the_reviewer_is_not_rewritten_to_the_writer(monkeypatch):
    from app.agent import hard
    from app import usage
    seen = []

    class Msgs:
        async def create(self, **kw):
            seen.append(usage.ONE_MODEL_BYPASS.get())
            return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text='{"ok": true}')])
    import app.agent.santosh as s
    monkeypatch.setattr(s, "get_client", lambda: types.SimpleNamespace(messages=Msgs()))
    st = types.SimpleNamespace(anthropic_model="claude-sonnet-5-5", hard_check_model="", hard_check_timeout_s=5,
                               hard_check_independent=True)
    assert asyncio.run(hard.review("q", "d", "", st)) == []
    assert seen == [True] and usage.ONE_MODEL_BYPASS.get() is False


# ---------------------------------------------------------------- 40 monitoring
def test_a_stuck_worker_is_not_ok(monkeypatch):
    from app import worker
    monkeypatch.setitem(worker.BEAT, "ticks", 5)
    monkeypatch.setitem(worker.BEAT, "tick_at", time.time())
    monkeypatch.setitem(worker.BEAT, "slot", "")
    assert worker.health()["ok"]
    monkeypatch.setitem(worker.BEAT, "slot", "mail_jobs")
    monkeypatch.setitem(worker.BEAT, "slot_at", time.time() - 3600)
    h = worker.health()
    assert not h["ok"] and h["slot"] == "mail_jobs"


def test_a_hung_slot_is_cut(monkeypatch):
    from app import worker
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "worker_slot_timeout_s", 0.2)

    async def hangs():
        await asyncio.sleep(30)
    n0 = worker.BEAT["slot_timeouts"]
    t = time.time()
    asyncio.run(worker._slot(hangs))
    assert time.time() - t < 5 and worker.BEAT["slot_timeouts"] == n0 + 1


def test_healthz_and_stats_report_the_worker_and_the_loop():
    from app import main
    assert '"ok": bool(_wk.get("ok", True))' in inspect.getsource(main.healthz)
    assert "looplag.STATS" in inspect.getsource(main.agent_stats)
    assert "_looplag.start()" in inspect.getsource(main.lifespan)


# ---------------------------------------------------------------- 41 + 42 her avatar's Hindi
def test_the_work_keeps_its_own_grammar():
    from app.avatar.service import gendered as g
    assert g("Kaam ho gaya.", "f") == "Kaam ho gaya."
    assert g("Ho raha hai", "f") == "Ho raha hai"
    assert g("ho gaya, kal chaar baje ki meeting ban gayi", "f") == "ho gaya, kal chaar baje ki meeting ban gayi"
    assert g("Video dekh raha hoon, main samajh gaya", "f") == "Video dekh rahi hoon, main samajh gayi"
    assert g("main samajh nahi paya", "f") == "main samajh nahi payi"
    assert g("aapko sunaunga", "f") == "aapko sunaungi"
    assert g("Kaam ho gaya.", "m") == "Kaam ho gaya."


def test_the_fixed_lines_follow_her_avatar():
    from app.agent import santosh
    from app.avatar.service import gendered
    assert "Owner" not in santosh.HALTED_TEXT["pause"]
    assert "ruk gayi" in gendered(santosh.HALTED_TEXT["pause"], "f") and "karungi" in gendered(santosh.HALTED_TEXT["pause"], "f")
    assert "bata deti hoon" in gendered(santosh.TIMEOUT_TEXT, "f")
    src = inspect.getsource(santosh._steps_inner)
    assert 'gendered(HALTED_TEXT' in src and 'gendered("Soch badal raha hoon' in src
    assert "gendered(TIMEOUT_TEXT, _gender)" in inspect.getsource(santosh)


def test_the_chat_prompt_speaks_in_her_forms(env):
    from app.agent import prompts
    from app.avatar import service as av
    import app.agent.prompts as P
    real = av.persona
    try:
        av.persona = lambda t: ("Priya", "f")
        sp = prompts.system_prompt(True, "", T)
    finally:
        av.persona = real
    assert "yaad dila dungi" in sp and "yaad dila dunga" not in sp


# ---------------------------------------------------------------- 43 nights
def test_a_night_push_waits_and_her_reminder_does_not(monkeypatch):
    from app import push
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "push_quiet", "0-24")      # always night
    monkeypatch.setattr(get_settings(), "push_night_hold", True)
    monkeypatch.setattr(push, "configured", lambda: True)
    monkeypatch.setattr(push, "_tenant", lambda c: "t-night")
    monkeypatch.setattr(push, "_heard_on_call", lambda *a: False)
    sent = []
    monkeypatch.setattr(push._pool, "submit", lambda fn, t, ev: sent.append(ev["kind"]))
    push._HELD.pop("t-night", None)
    push._AWAKE.pop("t-night", None)
    push.on_event("c", {"kind": "message", "payload": {"role": "assistant", "text": "Report taiyaar hai"}})
    push.on_event("c", {"kind": "message", "payload": {"role": "assistant", "text": "Yaad dila raha hoon: dawai"}})
    push.on_event("c", {"kind": "bazar_approval", "payload": {"title": "x"}})
    assert len(push._HELD["t-night"]) == 1 and len(sent) <= 2
    monkeypatch.setattr(get_settings(), "push_quiet", "0-0")       # morning
    sent.clear()
    push.flush_night()
    assert sent == ["message"] and "t-night" not in push._HELD


def test_awake_she_is_not_held(monkeypatch):
    from app import push
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "push_quiet", "0-24")
    monkeypatch.setattr(push, "configured", lambda: True)
    monkeypatch.setattr(push, "_tenant", lambda c: "t-awake")
    push.on_event("c", {"kind": "message", "payload": {"role": "user", "text": "abhi bhi jaag rahi hoon"}})
    assert not push._hold_for_night("t-awake", {"kind": "message", "payload": {"role": "assistant", "text": "x"}})


# ---------------------------------------------------------------- 44 + 45 feeling and the prompt's own rules
def test_her_mood_is_heard():
    from app.agent import replystyle
    from app import voice
    assert "Her mood counts" in replystyle.CHAT and "{" not in replystyle.CHAT
    assert "Her mood" in voice.PERSONA_BRAIN


def test_no_contradicting_lines():
    from app.agent import santosh, prompts
    src = inspect.getsource(santosh)
    assert 'gendered("Kaam ho gaya. Aur kuch karna hai?"' not in src and 'final_text = "Kaam ho gaya." if ran_tools' in src
    assert "phir bolna" not in src
    assert "uljhan ho)" not in inspect.getsource(prompts)


# ---------------------------------------------------------------- 46 an error after tools
def test_an_error_after_tools_warns_before_a_repeat():
    from app.agent import santosh
    h = [{"role": "user", "content": "mail bhejo"},
         {"role": "assistant", "content": [{"type": "tool_use", "id": "1", "name": "email_send", "input": {}}]}]
    assert santosh._tools_since(h, 1) == ["email_send"] and santosh._tools_since(h, 2) == []
    assert "do baar na jaaye" in santosh.AFTER_TOOLS
    assert "_tools_since(history, _h0)" in inspect.getsource(santosh)


# ---------------------------------------------------------------- 47 background errors at night
def test_the_same_background_error_is_said_once_a_night(monkeypatch):
    from app.agent import santosh
    from app import push
    monkeypatch.setattr(push, "is_quiet_now", lambda t: True)
    santosh._BG_ERR.pop("t-bg", None)
    assert santosh._say_error("t-bg", "routine", "Abhi AI service busy (ref 1)")
    santosh._BG_ERR["t-bg"] = (santosh._BG_ERR["t-bg"][0], time.time() - 3 * 3600)
    assert not santosh._say_error("t-bg", "routine", "Abhi AI service busy (ref 2)")
    monkeypatch.setattr(push, "is_quiet_now", lambda t: False)
    assert santosh._say_error("t-bg", "routine", "Abhi AI service busy (ref 3)")
