"""v0.440 PAKKA KAAM: a big job handed over on a voice call (santosh_kaam) is saved in the durable turn inbox before it
starts, like a typed chat message - so a server restart / deploy mid-job re-runs it once (with the same place)
instead of silently losing it, and the call's drop note says a job was still running."""
import asyncio
from datetime import timedelta

from app import turn_inbox, voice
from app.db import now, session


class FakeCall:
    conv = "conv-pk"
    user_buf = ""
    _otp_said: set = set()

    class ctx:
        tenant_id = "default"
        place = ""

    def _place(self, request=""):
        return "pc"

    def _late_result(self, job, request=""):
        pass


def _rows():
    turn_inbox.ensure_table()
    with session() as s:
        return [dict(id=r.id, status=r.status, text=r.text, place=r.place, voice=r.voice)
                for r in s.query(turn_inbox.TurnInbox).filter_by(conversation_id="conv-pk").all()]


def test_a_call_job_is_saved_in_the_inbox_and_runs_with_its_place(env, monkeypatch):
    seen = []

    async def fake_turn(conv, text, tenant=None, voice=False, **kw):
        seen.append((conv, text, kw.get("place", "")))
        return "ho gaya"

    import app.agent as agent
    monkeypatch.setattr(agent, "run_turn", fake_turn)
    out = asyncio.run(voice.Call._delegate(FakeCall(), "Pune ke 5 co-working spaces ki PDF bana do"))
    assert out == {"result": "ho gaya"}
    assert seen == [("conv-pk", "Pune ke 5 co-working spaces ki PDF bana do", "pc")]
    rows = _rows()
    assert len(rows) == 1 and rows[0]["status"] == "done" and rows[0]["place"] == "pc" and rows[0]["voice"] == 0


def test_a_restart_mid_job_re_runs_it_once_with_the_same_place(env, monkeypatch):
    seen = []

    async def fake_turn(conv, text, tenant=None, voice=False, **kw):
        seen.append((text, kw.get("place", ""), kw.get("save_user", True)))
        return "ok"

    import app.agent as agent
    monkeypatch.setattr(agent, "run_turn", fake_turn)
    iid = turn_inbox.accept("default", "conv-pk", "Mere mails ki list Sheet mein daalo", False, "", "", place="pc")
    with session() as s:                  # the process died mid-turn: 'running' for 10 minutes, nothing holds the chat
        r = s.get(turn_inbox.TurnInbox, iid)
        r.status, r.updated_at = "running", now() - timedelta(minutes=10)

    async def go():
        n = await turn_inbox.sweep()
        await asyncio.gather(*list(turn_inbox._BG))
        return n

    assert asyncio.run(go()) == 1
    assert seen == [("Mere mails ki list Sheet mein daalo", "pc", True)]
    assert asyncio.run(turn_inbox.sweep()) == 0           # done now: never a second re-run


def test_drop_note_names_a_job_still_running(env, monkeypatch):
    saved = []
    from app import yaad
    monkeypatch.setattr(yaad, "note_call_drop", lambda conv, tenant, text: saved.append(text))
    c = FakeCall()
    c.recent, c.stats, c._drop_saved, c.tenant = [], {}, False, "default"
    c._otp_said = {"482913"}
    c._kaam_running = {1: "Hotel book karo, OTP 482913 aaya hai"}
    voice.Call._save_drop_note(c)
    assert saved and "ek bada kaam chal raha tha" in saved[0] and "Hotel book karo" in saved[0]
    assert "482913" not in saved[0]
