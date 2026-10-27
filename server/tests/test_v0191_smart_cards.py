"""v0.191 SAMAJHDAR CARD - the approval/result card got a brain (owner's three wishes in one release):

1. "CAPTCHA - ek confirm ke baad apne aap type (recommended)"  -> the PC operator's tapgate auto-approves every
   CAPTCHA after the first one is approved in the same task, and auto-approves nothing-consequence steps with NO
   card at all (RC-A: 2-4 meaningless HAAN cards per pizza task).
2. "Non-money orders (pizza jaisa) - voice haan se approve (recommended)"  -> she SAYS the yes on a call (or types
   it in chat) and the pending NON-MONEY PC/browser approval resolves without a tap (RC-B: nothing approved by
   voice, the op stalled 600s). Money / UPI / bank-OTP / password stay card + PIN only.
3. "NOT ONLY HAAN, ANY KARDO, APPROVE HAI ETC"  -> approval_words.py speaks the whole boli: haan / haan karo /
   kar do / yes / approve hai / confirm / theek hai / manzoor / ok / pakka / bhej do / हाँ कर दो / मंज़ूर है ...
   and a clear 'nahi / mat karo' cancels the young approvals. Rejection always wins over approval.
"""
import asyncio
from types import SimpleNamespace

import pytest

from app.db import now


@pytest.fixture
def api(env, monkeypatch):
    from app import convs
    convs._CACHE.clear()
    yield env
    convs._CACHE.clear()


def _conv(tenant):
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


# ---------------------------------------------------------------- 1. the boli (approval vocabulary)
def test_approval_any_word_owner_directive():
    """NOT ONLY HAAN: every natural way of saying yes resolves the card."""
    from app import approval_words as aw
    for t in ["haan", "haan karo", "haan ji kar do", "approve", "approve hai", "approved",
              "confirm", "confirm karo", "theek hai", "thik hai", "sahi hai", "manzoor hai",
              "ok", "ok kardo", "okay", "yes", "yeah", "sure", "pakka karo", "bhej do", "aage badho",
              "go ahead", "kardo", "kar do ji", "हाँ", "हाँ कर दो", "ठीक है", "मंज़ूर है"]:
        assert aw.is_pure_approval(t), f"pure approval missed: {t}"
        assert aw.is_approval(t), f"approval missed: {t}"


def test_rejection_always_wins():
    from app import approval_words as aw
    for t in ["nahi", "nahin", "mat karo", "mat karna", "rehne do", "cancel karo", "ruko", "rok do",
              "band karo", "chhodo", "no", "nope", "नहीं", "मत करो", "abhi nahi"]:
        assert aw.is_rejection(t), f"rejection missed: {t}"
        assert not aw.is_approval(t), f"rejection read as approval: {t}"
    assert not aw.is_pure_approval("haan nahi") and not aw.is_pure_rejection("haan nahi")
    assert aw.is_pure_rejection("nahi") and aw.is_pure_rejection("mat karo") and aw.is_pure_rejection("नहीं")


def test_lead_yes_with_extra_words_vs_new_command():
    """'haan, address yeh raha' = card resolve + baaki baat brain dekhega; 'pizza order karo' = NEW kaam, nahi."""
    from app import approval_words as aw
    assert aw.approve_lead("haan, address yeh raha") and not aw.is_pure_approval("haan, address yeh raha")
    assert aw.approve_lead("haan par cheese burst bhi add karo")
    assert not aw.approve_lead("pizza order karo")        # a new task, not an approval
    assert not aw.approve_lead("dominos ka site kholo")   # a new task
    assert not aw.approve_lead("haan nahi ruko")


def test_money_risk_never_by_voice():
    from app import approval_words as aw
    for t in ["pay kar do", "₹500", "rs 2500 bhejo", "upi karo", "bank transfer", "card number",
              "cvv", "otp bolo", "password", "payment karna hai"]:
        assert aw.money_risk(t), f"money risk missed: {t}"
    for t in ["order place kar do", "cart mein add karo", "popup band karo", "form bhar do"]:
        assert not aw.money_risk(t), f"benign step read as money: {t}"


# ---------------------------------------------------------------- 2. the tapgate (PC operator)
def _op(captcha_ok=False):
    from app.pc.operator import Op
    return Op(id="pcop_test1", tenant="t1", conv="c1", task="pizza order karo", captcha_ok=captcha_ok)


def test_tapgate_benign_steps_never_make_a_card():
    """RC-A ka ilaaj: popup/cookie/cart/search/form wali step par card NAHI jaata - auto approve."""
    from app.pc.operator import _tapgate
    auto, note = _tapgate(_op(), "popup band kar doon?")
    assert auto and "auto" in note.lower()
    for w in ["cart mein add kar doon?", "cookie banner hata doon? (accept)", "search box mein 'pizza' likh doon?",
              "form bhar doon?", "next page par continue karun?", "tab band kar doon?", "login page kholun?"]:
        auto, _ = _tapgate(_op(), w)
        assert auto, f"benign step asked for a card: {w}"


def test_tapgate_real_decisions_still_get_a_card():
    from app.pc.operator import _tapgate
    for w in ["order place kar doon?", "₹500 pay kar doon?", "WhatsApp par message bhej doon?",
              "file delete kar doon?", "app install kar doon?", "settings change kar doon?"]:
        auto, _ = _tapgate(_op(), w)
        assert not auto, f"real decision auto-approved: {w}"


def test_captcha_once_then_auto_type():
    """Owner: 'CAPTCHA - ek confirm ke baad apne aap type'. Pehli CAPTCHA card maangti hai; uski haan ke baad
    is task ki har CAPTCHA auto-approve (naya task phir se poochhega - captcha_ok har Op ka apna hai)."""
    from app.pc.operator import _tapgate
    op = _op(captcha_ok=False)
    assert not _tapgate(op, "CAPTCHA mein 'Xy7k2' likhu?")[0]      # pehli baar: card
    op.captcha_ok = True
    auto, note = _tapgate(op, "CAPTCHA mein 'Bq4m9' likhu?")
    assert auto and "auto" in note.lower()
    fresh = _op(captcha_ok=False)                                  # agla task: phir ek confirm
    assert not _tapgate(fresh, "CAPTCHA mein 'Bq4m9' likhu?")[0]


# ---------------------------------------------------------------- 3. voice / chat approval path
@pytest.fixture
def pcop_pending(api):
    """A pending PC operator step approval: the Op waits in memory, the Approval row waits in the DB."""
    from app.bazar.db import Approval, Task
    from app.bazar.service import ensure_user
    from app.db import session
    from app.pc import operator
    t = api["settings"].tenant_id
    conv = _conv(t)
    op = operator.Op(id="pcop_pending1", tenant=t, conv=conv, task="dominos par pizza order karna hai")
    op.pending = {"id": "pend1", "what": "order place kar doon?"}
    op.decision = asyncio.Event()
    operator.OPS[op.id] = op
    with session() as s:
        u = ensure_user(s, t)
        task = Task(user_id=u.id, text="pizza order karo", conversation_id=conv)
        s.add(task)
        s.flush()
        ap = Approval(task_id=task.id, user_id=u.id, tier=2, title="Aapka PC: order place kar doon?",
                      payee="Aapka PC", amount_paise=0, conversation_id=conv,
                      action={"executor": "pcop", "pack_id": "pc-operator", "name": "approve_step",
                              "args": {"session_id": op.id, "pending_id": "pend1"}}, items=[])
        s.add(ap)
        s.flush()
        apid = ap.id
    yield {"op": op, "approval_id": apid, "conv": conv, "tenant": t}
    operator.OPS.pop(op.id, None)


def test_voice_approve_resolves_pending_pcop_card(pcop_pending, api):
    """She says 'haan karo' on the call: the card resolves, the stalled PC op moves again. Tap kabhi nahi chahiye."""
    from app.bazar import service
    from app.db import session
    from app.bazar.db import Approval
    got = service.voice_approve(pcop_pending["tenant"], pcop_pending["conv"], "haan karo", False, "voice")
    assert got and got.get("approved")
    with session() as s:
        ap = s.get(Approval, pcop_pending["approval_id"])
        assert ap.decision == "approved"
    assert pcop_pending["op"].approved is True          # the op really continued
    assert pcop_pending["op"].decision.is_set()


def test_voice_approve_any_word(pcop_pending, api):
    """NOT ONLY HAAN: 'approve hai', 'confirm', 'theek hai', 'kar do' - sab chalta hai."""
    from app.bazar import service
    from app.pc import operator
    from app.db import session
    from app.bazar.db import Approval
    from datetime import timedelta
    for i, words in enumerate(["approve hai", "confirm kar do", "theek hai", "kar do", "yes"]):
        with session() as s:                            # har test ke liye ek fresh pending approval
            ap = s.get(Approval, pcop_pending["approval_id"])
            ap.decision = "pending"
            ap.decided_at = None
            ap.created_at = now() - timedelta(seconds=10)
        pcop_pending["op"].approved = False
        pcop_pending["op"].decision = asyncio.Event()
        got = service.voice_approve(pcop_pending["tenant"], pcop_pending["conv"], words, False, "voice")
        assert got and got.get("approved"), f"word not accepted: {words}"
        assert pcop_pending["op"].approved is True


def test_voice_money_words_never_approve(pcop_pending):
    """Money/UPI/OTP wale shabd uske uttar mein: manzoori NAHI hoti - card + PIN par hi (gate untouched)."""
    from app.bazar import service
    from app.db import session
    from app.bazar.db import Approval
    got = service.voice_approve(pcop_pending["tenant"], pcop_pending["conv"], "haan pay kar do", False, "voice")
    assert got and got.get("money")                     # the honest 'yeh card se hoga' line
    with session() as s:
        assert s.get(Approval, pcop_pending["approval_id"]).decision == "pending"
    assert pcop_pending["op"].approved is False


def test_voice_new_command_is_not_an_approval(pcop_pending):
    """'pizza order karo' ek NAYA kaam hai - purani atki manzoori par haan nahi."""
    from app.bazar import service
    got = service.voice_approve(pcop_pending["tenant"], pcop_pending["conv"], "pizza order karo", False, "voice")
    assert got is None and pcop_pending["op"].approved is False


def test_voice_pure_nahi_cancels(pcop_pending):
    """Saaf 'nahi / mat karo': young step manzooriyan cancel - op ko 'NOT approved' milta hai."""
    from app.bazar import service
    from app.db import session
    from app.bazar.db import Approval
    got = service.voice_approve(pcop_pending["tenant"], pcop_pending["conv"], "nahi mat karo", False, "voice")
    assert got and got.get("rejected")
    with session() as s:
        assert s.get(Approval, pcop_pending["approval_id"]).decision == "rejected"


def test_chat_typed_haan_resolves_without_the_brain(pcop_pending, api, monkeypatch):
    """Chat mein likhi pure haan ('haan karo'): card resolve, seedha jawab - brain ka ek bhi call nahi."""
    from app.agent import santosh

    def _boom(*a, **k):   # agar hook na lage aur brain chal pade to test saaf fail ho
        raise AssertionError("the brain must not run for a typed pure approval")
    monkeypatch.setattr(santosh, "_steps", _boom)
    monkeypatch.setattr(santosh, "_think", _boom, raising=False)
    text = asyncio.run(santosh._run_turn(pcop_pending["conv"], "haan karo", pcop_pending["tenant"]))
    assert "manzoor" in text.lower()
    assert pcop_pending["op"].approved is True
    from app.db import session
    from app.bazar.db import Approval
    with session() as s:
        assert s.get(Approval, pcop_pending["approval_id"]).decision == "approved"


def test_card_carries_voice_ok_flag(api):
    """card_of.voice_ok: PC/browser non-money True (hint dikhega), money/koi doosra executor False."""
    from app.bazar.db import Approval, Task
    from app.bazar.service import card_of, ensure_user
    from app.db import session
    t = api["settings"].tenant_id
    with session() as s:
        u = ensure_user(s, t)
        task = Task(user_id=u.id, text="x", conversation_id="")
        s.add(task)
        s.flush()
        pc = Approval(task_id=task.id, user_id=u.id, tier=2, title="Aapka PC: x", amount_paise=0,
                      action={"executor": "pcop"}, items=[])
        br = Approval(task_id=task.id, user_id=u.id, tier=2, title="site: 'Order' dabana hai", amount_paise=0,
                      action={"executor": "browser"}, items=[])
        mn = Approval(task_id=task.id, user_id=u.id, tier=2, title="Amazon order", amount_paise=45000,
                      action={"executor": "pcop"}, items=[])
        other = Approval(task_id=task.id, user_id=u.id, tier=2, title="Bijli bill", amount_paise=0,
                         action={"executor": "commerce"}, items=[])
        for a in (pc, br, mn, other):
            s.add(a)
        s.flush()
        ids = (pc.id, br.id, mn.id, other.id)
    with session() as s:
        cards = [card_of(s.get(Approval, i), None) for i in ids]
    assert cards[0]["voice_ok"] is True and cards[1]["voice_ok"] is True
    assert cards[2]["voice_ok"] is False and cards[3]["voice_ok"] is False


# ---------------------------------------------------------------- 4. result intelligence (kaamwatch)
def test_kaamwatch_browser_needs_confirm_tells_her_to_say_haan():
    """Call mein step atakti hai to woh sun'ti hai 'aapki baari - bol kar haan karo' (koi chat line nahi — card hi
    kahani hai), aur start lines shant (live card already dikh raha hai)."""
    from app.kaamwatch import _decide, shape
    job = shape("browser", {"session_id": "s9", "status": "needs_confirm", "task": "dominos par pizza order",
                            "source": "pc", "site": "Aapka PC"})
    assert job and job["state"] == "waiting" and job["no_start_say"] and job["voice_only"]
    assert "haan karo" in job["waiting_say"]
    line = _decide(SimpleNamespace(told=""), job, "working", False, now())
    assert "aapki baari" in line
    # running steps say NOTHING (the live card is the story)
    run = shape("browser", {"session_id": "s9", "status": "running", "task": "dominos par pizza order", "source": "pc"})
    assert run and run["state"] == "working"
    assert _decide(SimpleNamespace(told=""), run, "running", True, now()) == ""


def test_decide_notify_ok_silence(pcop_pending, api):
    """voice_approve apni ek hi line bolti hai: bazar decide ki notify band (koi doosra result message nahi)."""
    from sqlalchemy import select
    from app.bazar import service
    service.voice_approve(pcop_pending["tenant"], pcop_pending["conv"], "haan karo", False, "voice")
    from app.db import Message, session
    with session() as s:
        rows = s.scalars(select(Message).where(Message.conversation_id == pcop_pending["conv"])).all()
        texts = [r.content or "" for r in rows]
    assert not any("Theek hai, PC par aage badh raha hoon" in t for t in texts), \
        f"the old double notify still fired: {texts}"
