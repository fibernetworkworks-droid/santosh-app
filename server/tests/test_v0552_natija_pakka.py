"""v0.552 NATIJA PAKKA (built as 0.551) - the owner: "NOW CHECK FOR ALL 3 --- WHEN RESULT COME FROM ANY TASK DOES IT REPLY RELIABLY".

The finished-job report (kaamwatch -> kaam_followup -> a wake turn / a one-shot line -> notify = Message + SSE to the
console and the phone + FCM push, and a quiet note into her live call) was traced end to end. One rule lost news:
v0.260's `_answered_since` skipped the report whenever ANY real assistant reply landed after the job finished - so a
background job that finished while she was asking about something else was never told (only its card), and when two
jobs finished close together, the first job's wake report swallowed the second job's news.

Now a reply counts as THIS job's report only when the turn that wrote it began before the job started (that turn
ran the job - the 29 Oct duplicate stays fixed) and it is not another job's own wake report.
"""
from datetime import timedelta


def _seed(conv_id="c-natija", tenant="t-natija"):
    from app.db import Conversation, session
    with session() as s:
        s.add(Conversation(id=conv_id, tenant_id=tenant))
    return conv_id, tenant


def _msg(conv, role, text, at, in_history=True):
    from app.db import Message, session
    with session() as s:
        m = Message(conversation_id=conv, role=role, content=text, display=text, in_history=in_history)
        m.created_at = at
        s.add(m)


def _job(tenant, conv, key, started):
    from app import kaamwatch
    from app.db import session
    with session() as s:
        s.add(kaamwatch.KaamJob(tenant_id=tenant, conversation_id=conv, key=key, kind=key.split(":")[0],
                                label="Research", title="competitor prices", state="done",
                                started_at=started, moved_at=started, updated_at=started))


LONG = "Ji, GST return ki aakhri tareekh 20 November hai, aur aapke teen bill abhi baaki hain - main list bana deta hoon."


def test_an_unrelated_reply_no_longer_swallows_the_news(env):
    from app import kaam_followup as K
    from app.db import now
    conv, tenant = _seed()
    t0 = now() - timedelta(minutes=10)
    _job(tenant, conv, "research_run:r1", t0)                         # a background job started at t0
    _msg(conv, "user", "GST ki date kya hai?", t0 + timedelta(minutes=5))   # she asks something ELSE later
    finished = t0 + timedelta(minutes=6)                              # the job finishes during that turn
    _msg(conv, "assistant", LONG, t0 + timedelta(minutes=7))          # the turn answers her GST question
    assert K._answered_since(conv, finished, key="research_run:r1", tenant=tenant) is False   # the news still goes


def test_the_turn_that_ran_the_job_still_counts_as_the_report(env):
    """The 29 Oct duplicate stays fixed: she asked, the turn ran the job and answered it - no second report."""
    from app import kaam_followup as K
    from app.db import now
    conv, tenant = _seed("c-natija2")
    t0 = now() - timedelta(minutes=10)
    _msg(conv, "user", "Competitor ke daam nikalo", t0)              # her ask starts the turn
    _job(tenant, conv, "research_run:r2", t0 + timedelta(seconds=20))  # the turn starts the job
    finished = t0 + timedelta(minutes=3)
    _msg(conv, "assistant", "Competitor ke daam: A 1200, B 1350, C 990 - sabse sasta C hai, link neeche.", t0 + timedelta(minutes=4))
    assert K._answered_since(conv, finished, key="research_run:r2", tenant=tenant) is True


def test_another_jobs_wake_report_does_not_swallow_this_one(env):
    from app import kaam_followup as K
    from app.db import now, session
    conv, tenant = _seed("c-natija3")
    t0 = now() - timedelta(minutes=10)
    _msg(conv, "user", "Do kaam karo", t0)                            # long ago, before both jobs
    _job(tenant, conv, "video_job:v1", t0 + timedelta(minutes=1))
    _job(tenant, conv, "app_android:a1", t0 + timedelta(minutes=1))
    finished = t0 + timedelta(minutes=8)
    wake_at = t0 + timedelta(minutes=8, seconds=20)
    _msg(conv, "assistant", "Video edit ho gaya - 45 second ka reel taiyaar hai, link chat mein hai.", wake_at)
    K.ensure_table()
    with session() as s:                                              # that reply WAS the video job's wake report
        s.add(K.KaamFollowup(tenant_id=tenant, conversation_id=conv, key="video_job:v1", state="done",
                             status="sent", sent_at=wake_at + timedelta(seconds=2)))
    assert K._answered_since(conv, finished, key="app_android:a1", tenant=tenant) is False


def test_old_callers_and_empty_chats_keep_working(env):
    from app import kaam_followup as K
    from app.db import now
    assert K._answered_since("missing-conv", None) is False
    assert K._answered_since("conv-that-does-not-exist", now()) is False


def test_send_passes_the_job_identity():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "app" / "kaam_followup.py").read_text()
    assert '_answered_since(conv, getattr(r, "created_at", None), key=key, tenant=tenant)' in src


def _pending_row(conv, tenant, key, age_s, tries=0):
    from app import kaam_followup as K
    from app.db import now, session
    K.ensure_table()
    with session() as s:
        r = K.KaamFollowup(tenant_id=tenant, conversation_id=conv, key=key, kind="video_job", label="Video edit",
                           title="Ad reel", state="done", status="pending", tries=tries)
        r.created_at = now() - timedelta(seconds=age_s)
        s.add(r)
        s.flush()
        return r.id


def test_a_running_turn_holds_the_report_longer_than_50_seconds(env, monkeypatch):
    import asyncio
    from app import kaam_followup as K
    from app.db import session
    conv, tenant = _seed("c-wait1")
    fid = _pending_row(conv, tenant, "video_job:w1", age_s=90, tries=6)   # the old rule fired at tries 5 (~50 s)
    sent = []
    monkeypatch.setattr(K, "_turn_running", lambda c: True)
    monkeypatch.setattr(K, "notify", lambda c, t: sent.append(t))
    asyncio.run(K.tick())
    with session() as s:
        r = s.get(K.KaamFollowup, fid)
        assert r.status == "pending" and not sent        # still waiting for her turn to end: the real report follows


def test_past_the_wait_the_honest_line_still_goes(env, monkeypatch):
    import asyncio
    from app import kaam_followup as K
    from app.db import session
    conv, tenant = _seed("c-wait2")
    fid = _pending_row(conv, tenant, "video_job:w2", age_s=K._wait_s() + 5, tries=20)
    sent = []
    monkeypatch.setattr(K, "_turn_running", lambda c: True)
    monkeypatch.setattr(K, "notify", lambda c, t: sent.append(t))
    asyncio.run(K.tick())
    with session() as s:
        assert s.get(K.KaamFollowup, fid).status == "sent"
    assert sent and "Ad reel" in sent[0]                  # never lost


def test_postpones_can_never_strand_a_report():
    from app import kaam_followup as K
    assert K._MAX_TRIES * 10 > K._wait_s()               # ~10 s ticks: the wait ends before the cap is reached
