"""v0.223 DRAFT JAANCH: the last look at a reply. Free in code inside the turn (a claim with nothing behind it),
and one small check after the words are already on her screen (an unbacked figure, a part of her question missed).
The code only GATES; the model is the only thing that may speak."""
import asyncio

from app.agent import draftcheck, santosh
from app.config import get_settings
from tests.test_bazar import bz  # noqa: F401  (fresh DB + a real conversation)


def _st(**kw):
    return {"calls": kw.pop("calls", []), **kw}


# ---------------------------------------------------------------- 1. a claim with nothing behind it (free)

def test_a_claim_with_nothing_behind_it_is_caught_then_said_plainly():
    st = _st()
    nudge = draftcheck.fake_done(st, "Ho gaya - Sharma ji ko mail bhej diya hai.")
    assert "nothing that could do it ran" in nudge and "NOT done" in nudge
    assert "correct" not in st
    # it claims again after the nudge: the honest line is added after the words she already read
    assert draftcheck.fake_done(st, "Mail bhej diya.") == ""
    assert st["correct"] == draftcheck.SAID and "hua nahi hai" in st["correct"]


def test_a_claim_about_her_or_in_the_future_is_not_a_claim():
    for text in ("Aapne bhej diya hai to theek hai.",
                 "Card par haan karte hi mail bhej diya jayega.",
                 "Chahiye to main bhej doon?",
                 "Maine abhi tak mail nahi bheja hai.",
                 "Baad mein bhej diya jayega.",
                 # a plan / list / draft is legitimately "bana diya" inside the reply itself, with no tool behind it
                 "Maine aapke liye ek plan bana diya hai.",
                 "Poori list ban gayi hai, dekh lijiye."):
        assert draftcheck.claims_done(text) == "", text
        assert draftcheck.fake_done(_st(), text) == "", text


def test_a_real_tool_run_is_never_called_a_fake_claim_but_a_read_is():
    done = [{"tool": "email_send", "ok": True, "result": "sent"}]
    assert draftcheck.nothing_ran(done) is False
    assert draftcheck.fake_done(_st(calls=done), "Mail bhej diya.") == ""
    # a search / a Sahayak read / a failed send did nothing
    for calls in ([{"tool": "google_search", "ok": True, "result": "..."}],
                  [{"tool": "gst_dekho", "ok": True, "result": "..."}],
                  [{"tool": "remember", "ok": True}],
                  [{"tool": "email_send", "ok": False, "error": "no account"}]):
        assert draftcheck.nothing_ran(calls) is True, calls
        assert draftcheck.fake_done(_st(calls=calls), "Mail bhej diya.") != ""


def test_goal_mode_keeps_its_own_truth(bz, monkeypatch):
    """A kaam_plan goal has its own steps and its own honest "X/Y steps ho gaye" line (v0.186), so the free claim
    check stays out of its way and never spends an extra round there."""
    from app.agent.breaker import Breaker
    st = {"calls": [{"tool": "kaam_plan", "ok": True}], "breaker": Breaker(), "goal": {"goal": "Report banao"}}
    out = asyncio.run(santosh._pakka_check(st, "Report taiyaar hai, bhej diya.", get_settings(), False, bz["conv"]))
    assert out == "" and "correct" not in st
    assert santosh._goal_open(st, bz["conv"], get_settings()) is True
    assert santosh._goal_open({"calls": []}, bz["conv"], get_settings()) is False
    # outside goal mode the very same reply IS caught
    st2 = {"calls": [{"tool": "kaam_plan", "ok": True}], "breaker": Breaker()}
    assert asyncio.run(santosh._pakka_check(st2, "Report taiyaar hai, bhej diya.", get_settings(), False, bz["conv"]))


# ---------------------------------------------------------------- 2. the free gate

def test_hard_facts_are_the_concrete_ones_only():
    f = draftcheck.hard_facts("Rs 4,500 ka bill 15/11 ko 4 baje tak, order 10045678, 2.5 lakh saal ka, 18% GST, 3 item")
    d = [draftcheck._digits(x) for x in f]
    for want in ("4500", "1511", "4", "10045678", "2.5".replace(".", "")):
        assert want in d, (want, f)
    assert "18" not in d and "3" not in d          # a percentage and a small count are never a hard fact


def test_a_figure_that_came_from_a_real_source_is_not_loose():
    src = draftcheck.sources_text("Atta ka rate 4500 hai?",
                                  [{"tool": "thok_dekho", "ok": True, "result": "bill no 10045678 dated 15/11"}])
    assert draftcheck.loose_facts("Rs 4,500, bill 10045678, 15/11 ko.", src) == []
    loose = draftcheck.loose_facts("Rs 9,900 bhi lagega.", src)
    assert loose and draftcheck._digits(loose[0]) == "9900"


def test_the_gate_spends_nothing_when_there_is_nothing_to_check():
    before = dict(draftcheck.STATS)
    assert draftcheck.worth_checking("kaise ho", "Badhiya! Aap kaise hain? Sab theek chal raha hai yahan.", []) is None
    assert draftcheck.worth_checking("hi", "Theek.", []) is None                       # too short to judge
    assert draftcheck.worth_checking("kitna hua", "Rs 500 hua.\n\n(Dhyaan: dekh lijiye.)", []) is None
    assert draftcheck.STATS["gated"] == before["gated"]
    # a figure nothing backs, or a two-part question: worth one small look
    g = draftcheck.worth_checking("bill kitna hua", "Total Rs 7,250 hua hai, kal tak de dijiye.", [])
    assert g and draftcheck._digits(g["loose"][0]) == "7250" and g["parts"] is False
    g2 = draftcheck.worth_checking("GST kab bharna hai? Aur late fee kitni hai?",
                                   "GSTR-3B 20 tareekh tak bhar dijiye.", [])
    assert g2 and g2["parts"] is True


def test_many_parts_reads_her_real_question():
    assert draftcheck.many_parts("yeh kya hai? aur woh kaise karun?") is True
    assert draftcheck.many_parts("1. rate batao\n2. stock bhi") is True
    assert draftcheck.many_parts("mujhe rate aur stock dono batao") is False


# ---------------------------------------------------------------- 3. only the model speaks

def _model(monkeypatch, answer: str, slow: float = 0.0):
    from app.agent import pakka
    seen = []

    async def fake_ask(system, text, settings):
        seen.append(text)
        if slow:
            await asyncio.sleep(slow)
        return answer

    monkeypatch.setattr(pakka, "_ask", fake_ask)
    return seen


def _after(conv, ask, reply, calls=None, tenant=None):
    st = {"calls": calls or []}
    return asyncio.run(draftcheck.after_turn(conv, tenant, ask, reply, st, get_settings()))


def test_a_figure_hoola_worked_out_never_becomes_a_warning(bz, monkeypatch):
    # 3 x 150 = 450: the total is loose in code (the digits are nowhere), the model says it is fine -> silence
    seen = _model(monkeypatch, '{"ok": true, "missed": "", "unsupported": []}')
    out = _after(bz["conv"], "3 bori ka kitna hua", "Teen bori, Rs 150 wali: total Rs 450 hua.",
                 [{"tool": "thok_dekho", "ok": True, "result": "atta Rs 150 per bori"}])
    assert out == "" and len(seen) == 1                      # it looked once, and said nothing


def test_an_unbacked_figure_gets_one_honest_note_in_chat_and_in_the_call(bz, monkeypatch):
    from app.db import Message, session
    _model(monkeypatch, '{"ok": false, "missed": "", "unsupported": ["Rs 7,250"]}')
    said = []
    from app import kaamwatch
    monkeypatch.setattr(kaamwatch, "_voice", lambda t, c, s: said.append(s))
    out = _after(bz["conv"], "bill kitna hua", "Total Rs 7,250 hua hai.", tenant="t1")
    assert out.startswith("(Dhyaan: Rs 7,250") and "khud dekh lijiye" in out
    with session() as s:
        rows = [m for m in s.query(Message).filter(Message.conversation_id == bz["conv"]).all()
                if m.display and m.display.startswith("(Dhyaan:")]
    assert len(rows) == 1 and rows[0].in_history is False    # a note, never part of the model's own history
    assert said and said[0].startswith("Dhyaan:")


def test_the_note_can_only_name_figures_the_code_also_saw(bz, monkeypatch):
    # the model names a figure that IS backed (150 came from the tool): the note refuses to carry it
    _model(monkeypatch, '{"ok": false, "missed": "", "unsupported": ["Rs 150"]}')
    out = _after(bz["conv"], "rate kya hai", "Rate Rs 150 hai, kal Rs 7,250 ka order bhej doon?",
                 [{"tool": "thok_dekho", "ok": True, "result": "atta Rs 150"}])
    assert out == ""


def test_a_name_is_checked_in_code_too(bz, monkeypatch):
    # a person the model flags: dropped when her own words name them, kept when they are nowhere in the sources
    _model(monkeypatch, '{"ok": false, "missed": "", "unsupported": ["Sharma ji"]}')
    draftcheck._SPOKE.pop(bz["conv"], None)
    assert _after(bz["conv"], "Sharma ji ko Rs 7,250 ka bill bhejo?", "Sharma ji ko Rs 7,250 bhej raha hoon.") == ""
    out = _after(bz["conv"], "bill kis-kis ka hai? aur total?", "Sharma ji ka Rs 7,250 hai.")
    assert out.startswith("(Dhyaan: Sharma ji")


def test_a_missed_part_of_her_question_gets_an_honest_line(bz, monkeypatch):
    _model(monkeypatch, '{"ok": false, "missed": "late fee kitni hai", "unsupported": []}')
    out = _after(bz["conv"], "GST kab bharna hai? Aur late fee kitni hai?", "GSTR-3B 20 tareekh tak bhar dijiye.")
    assert out == "(Ek baat reh gayi: late fee kitni hai - bataun?)"


def test_the_note_never_chatters(bz, monkeypatch):
    _model(monkeypatch, '{"ok": false, "missed": "", "unsupported": ["Rs 7,250"]}')
    draftcheck._SPOKE.pop(bz["conv"], None)
    spoke = [bool(_after(bz["conv"], "kitna", "Total Rs 7,250 hua hai.")) for _ in range(6)]
    assert spoke.count(True) == get_settings().draft_check_max_hour


def test_quiet_when_she_stopped_when_the_switch_is_off_and_when_the_month_is_over(bz, monkeypatch):
    seen = _model(monkeypatch, '{"ok": false, "unsupported": ["Rs 7,250"]}')
    draftcheck._SPOKE.pop(bz["conv"], None)
    santosh._stopped.add(bz["conv"])
    try:
        assert _after(bz["conv"], "kitna", "Total Rs 7,250 hua hai.") == ""
    finally:
        santosh._stopped.discard(bz["conv"])
    assert _after(bz["conv"], "kitna", "Maaf kijiye, abhi kuch gadbad ho gayi. Rs 7,250") == ""
    from app import usage
    monkeypatch.setattr(usage, "allowed", lambda t, f: False)
    assert _after(bz["conv"], "kitna", "Total Rs 7,250 hua hai.", tenant="t1") == ""
    assert seen == []                                        # not one model call was spent
    monkeypatch.setenv("DRAFT_CHECK", "false")
    get_settings.cache_clear()
    try:
        assert _after(bz["conv"], "kitna", "Total Rs 7,250 hua hai.") == ""
        assert seen == []
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------- 4. the turn never waits for it

def test_the_reply_never_waits_for_the_check(bz, monkeypatch):
    import time
    from app.agent import pakka
    draftcheck._SPOKE.pop(bz["conv"], None)
    notes, checked_at = [], []
    from app import events
    monkeypatch.setattr(events, "notify", lambda c, t, campaign_id=None: notes.append(t))

    async def slow_ask(system, text, settings):
        if system is not draftcheck.CHECK_SYSTEM:      # the memory's own little model call, not ours
            return ""
        await asyncio.sleep(0.6)
        checked_at.append(time.time())
        return '{"ok": false, "missed": "", "unsupported": ["Rs 7,250"]}'

    monkeypatch.setattr(pakka, "_ask", slow_ask)

    async def fake_think(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        return ([{"type": "text", "text": "Total Rs 7,250 hua hai."}], "end_turn", brain)

    monkeypatch.setattr(santosh, "_think", fake_think)

    async def go():
        out = await santosh.run_turn(bz["conv"], "bill kitna hua")
        back = time.time()
        for t in list(santosh._BG):
            try:
                await asyncio.wait_for(t, 10)
            except Exception:
                pass
        return out, back

    out, back = asyncio.run(go())
    assert out == "Total Rs 7,250 hua hai."
    # the reply was back before the check had even finished thinking: the turn never waits for it
    assert checked_at and back < checked_at[0], (back, checked_at)
    assert any(n.startswith("(Dhyaan: Rs 7,250") for n in notes), notes


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.299.0"
