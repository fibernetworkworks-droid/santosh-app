"""v0.199 BLOCK 2 — BOL-KAR-HAAN ka tool (voice-to-voice alag):

v0.191 ne passive _approval_listen diya tha (boli ke shabdon par regex chalta hai) — par woh sirf wahi pakadta
hai jo approval_words ke shabdon mein aaye. Live call mein woh bhi hota hai: uski haan apne andaaz mein aati hai
("theek hai bhai, jaisa tumhe theek lage", "haan kar do aur jaldi karo" 10-shabd wali, context se hi samajh aati
hai) — regex miss karta hai, card atka rehta hai, op timeout par mar jata hai. BLOCK 2: ab MODEL khud `haan_karo`
tool call karta hai jab usne SUNA/context se samjha ki usne isi call ke kaam ki manzoori de di.

Safety (owner: "Paise wala (tier 3 / UPI / bank OTP) hamesha tap + fingerprint only — voice se kabhi nahi"):
  1. voice_pending STRUCTURAL: money approvals is list mein aati hi nahi (amount / tier>=3 / UPI-card-wallet-pay-
     bank pay_method / title-items mein money shabd) — approve karne ko kuch money-wala hota hi nahi;
  2. money_risk uske bol mein bhi pakadta hai ("haan pay kar do" -> card-only jawab);
  3. voice-lock: haan_karo TRUSTED/FAMILY mein nahi — owner ki awaaz ke alawa server khud rok deta hai.
"""
import asyncio
from datetime import timedelta

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


@pytest.fixture
def pcop_pending(api):
    """Is call (conversation) ki pending PC operator step manzoori: Op memory mein atka, Approval DB mein pending."""
    from app.bazar.db import Approval, Task
    from app.bazar.service import ensure_user
    from app.db import session
    from app.pc import operator
    t = api["settings"].tenant_id
    conv = _conv(t)
    op = operator.Op(id="pcop_tool1", tenant=t, conv=conv, task="dominos par pizza order karna hai")
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


def _ctx(tenant, conv):
    from app.agent.tools import Ctx
    return Ctx(tenant, conv)


# ---------------------------------------------------------------- 1. the tool itself
def test_tool_approves_this_calls_pending(pcop_pending):
    """Model ne haan_karo call kiya (uski haan context se samajh aayi): isi call ki pending manzoori approve,
    atka op aage badhta hai — bina tap, bina boli ke shabdon ke gate ke."""
    from app.agent.tools import dispatch
    from app.bazar.db import Approval
    from app.db import session
    got = asyncio.run(dispatch("haan_karo", {"heard": "theek hai bhai, jaisa tumhe theek lage"},
                               _ctx(pcop_pending["tenant"], pcop_pending["conv"])))
    assert got.get("status") == "approved", got
    assert "order place" in (got.get("title") or "")
    with session() as s:
        assert s.get(Approval, pcop_pending["approval_id"]).decision == "approved"
    assert pcop_pending["op"].approved is True
    assert pcop_pending["op"].decision.is_set()


def test_tool_is_call_scoped(pcop_pending):
    """DOOSRI baat-cheet ki pending manzoori ko yeh tool NAHI chhoota — sirf isi call ke job ki."""
    from app.agent.tools import dispatch
    from app.bazar.db import Approval, Task
    from app.bazar.service import ensure_user
    from app.db import session
    t, conv = pcop_pending["tenant"], pcop_pending["conv"]
    other = _conv(t)                                   # doosri call, uski apni pending manzoori
    with session() as s:
        u = ensure_user(s, t)
        task = Task(user_id=u.id, text="site ka kaam", conversation_id=other)
        s.add(task)
        s.flush()
        ap2 = Approval(task_id=task.id, user_id=u.id, tier=2, title="site: 'Pay' dabana hai",
                       amount_paise=0, conversation_id=other,
                       action={"executor": "browser"}, items=[])
        s.add(ap2)
        s.flush()
        ap2id = ap2.id
    got = asyncio.run(dispatch("haan_karo", {"heard": "haan kar do"}, _ctx(t, conv)))
    assert got.get("status") == "approved"
    with session() as s:
        assert s.get(Approval, ap2id).decision == "pending"    # doosri call ki manzoori adhoori
        assert s.get(Approval, pcop_pending["approval_id"]).decision == "approved"


def test_tool_young_window_and_executor_filters(pcop_pending):
    """voice_pending ke purane gates tool par bhi: 15 min se purani manzoori nahi milti (status none)."""
    from app.agent.tools import dispatch
    from app.bazar.db import Approval
    from app.db import session
    with session() as s:
        ap = s.get(Approval, pcop_pending["approval_id"])
        ap.created_at = now() - timedelta(minutes=20)
    got = asyncio.run(dispatch("haan_karo", {"heard": "haan kar do"},
                               _ctx(pcop_pending["tenant"], pcop_pending["conv"])))
    assert got.get("status") == "none" and pcop_pending["op"].approved is False


# ---------------------------------------------------------------- 2. paise ke gates (owner ka sabse pakka niyam)
@pytest.mark.parametrize("field", ["amount", "tier3", "upi"])
def test_tool_money_pending_unreachable(pcop_pending, field):
    """Money wali manzoori (amount / tier 3 / UPI pay_method) pending ho tab bhi tool use PAHUNCHTI hi nahi:
    approve hone ke liye kuch money-wala hota hi nahi — tier 3 / UPI / bank-OTP hamesha card par."""
    from app.agent.tools import dispatch
    from app.bazar.db import Approval
    from app.db import session
    with session() as s:
        ap = s.get(Approval, pcop_pending["approval_id"])
        if field == "amount":
            ap.amount_paise = 45250
        elif field == "tier3":
            ap.tier = 3
        else:
            ap.pay_method = "upi"
    got = asyncio.run(dispatch("haan_karo", {"heard": "haan kar do"},
                               _ctx(pcop_pending["tenant"], pcop_pending["conv"])))
    assert got.get("status") == "none", got
    with session() as s:
        assert s.get(Approval, pcop_pending["approval_id"]).decision == "pending"
    assert pcop_pending["op"].approved is False


def test_tool_money_words_in_her_words_refused(pcop_pending):
    """Uske bol mein hi paise ke shabd ('haan pay kar do', '₹500 aur daal do'): tool manzoori NAHI karta —
    seedha card-only jawab."""
    from app.agent.tools import dispatch
    from app.bazar.db import Approval
    from app.db import session
    for heard in ["haan pay kar do", "haan, ₹500 aur daal do", "haan otp bol raha hoon"]:
        got = asyncio.run(dispatch("haan_karo", {"heard": heard},
                                   _ctx(pcop_pending["tenant"], pcop_pending["conv"])))
        assert got.get("status") == "money", f"{heard} approved?! {got}"
        with session() as s:
            assert s.get(Approval, pcop_pending["approval_id"]).decision == "pending"
        assert pcop_pending["op"].approved is False


def test_tool_heard_rejection_refused(pcop_pending):
    """Model ne galti se haan_karo call kar diya jabki uske shabd mana kar rahe the: kuch approve NAHI hota."""
    from app.agent.tools import dispatch
    from app.bazar.db import Approval
    from app.db import session
    got = asyncio.run(dispatch("haan_karo", {"heard": "nahi mat karo"},
                               _ctx(pcop_pending["tenant"], pcop_pending["conv"])))
    assert got.get("status") == "no", got
    with session() as s:
        assert s.get(Approval, pcop_pending["approval_id"]).decision == "pending"
    assert pcop_pending["op"].approved is False


def test_tool_no_pending_honest(pcop_pending):
    """Koi pending hi nahi (ya op ka pending khatam): tool sach bolta hai — kuch approve nahi hua, model insist nahi."""
    from app.agent.tools import dispatch
    got = asyncio.run(dispatch("haan_karo", {"heard": "haan"},
                               _ctx(pcop_pending["tenant"], _conv(pcop_pending["tenant"]))))
    assert got.get("status") == "none" and "nahi mili" in got.get("say", "")


# ---------------------------------------------------------------- 3. wiring (call path)
def test_voice_call_wiring():
    """haan_karo call mein DIRECT chalta hai (via_kaam nahi — turant jawab), TOOLS/HANDLERS/LABELS poore,
    aur description mein paise ka patta saaf likha hai."""
    from app import voice
    from app.agent.tools import HANDLERS, TOOLS, TOOL_LABELS
    assert "haan_karo" in voice.VOICE_TOOL_NAMES and not voice.via_kaam("haan_karo")
    spec = next(t for t in TOOLS if t["name"] == "haan_karo")
    assert "NEVER for money" in spec["description"]
    assert callable(HANDLERS["haan_karo"]) and TOOL_LABELS["haan_karo"]
    compact = voice._compact(spec)                     # Gemini ko jata hai chhota hoke — kabhi kat kar khaali na ho
    assert len(compact["description"]) <= 600 and "NEVER for money" in compact["description"]


def test_voice_lock_owner_only():
    """Manzoori owner ki awaaz ka kaam hai: haan_karo TRUSTED/FAMILY mein nahi — doosri awaaz par server khud rokta hai."""
    from app.voiceid.permissions import FAMILY, TRUSTED
    assert "haan_karo" not in FAMILY and "haan_karo" not in TRUSTED


def test_prompt_teaches_the_tool():
    """Call ka prompt bhi sikhata hai: haan_karo sirf pending card par, paise wali kabhi nahi."""
    import inspect
    from app import voice
    src = inspect.getsource(voice)
    assert "call haan_karo so the step moves at once" in src
    assert "NEVER approved by voice" in src
