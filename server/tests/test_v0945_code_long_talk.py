"""v0.945 HOOLA CODE LONG TALK (owner: "NOW AGAIN GO DEEP AND FIND FLAWS IN CHAT LANDING DURING LONG CONVERSATION" -> "GO").

A step's own count no longer loses to the step number, going back restores the conversation exactly, condensing keeps
her words, her notes are never cut or dropped, a long session keeps all of its conversation, and a check is light."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _row(S, DevTask, text="fix it"):
    with S.session() as s:
        t = DevTask(tenant_id="ten", repo="a/b", text=text, status="new", changes="[]")
        s.add(t)
        s.flush()
        return t.id


def test_a_steps_own_count_is_kept_beside_its_step_number(env):
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    init_db()
    tid = _row(S, DevTask)
    st = S._Step(tid)
    st.event({"k": "read", "path": "a.py"})
    st.event({"k": "ckpt", "n": 3, "text": "first round"})
    st.event({"k": "search", "q": "total", "n": 12})
    with S.session() as s:
        steps = json.loads(s.get(DevTask, tid).steps)
    assert [x["n"] for x in steps] == [0, 1, 2]
    assert steps[1]["num"] == 3 and steps[2]["num"] == 12          # checkpoint 3, 12 files: not overwritten


def test_writers_from_many_threads_never_lose_a_step(env):
    import threading
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    init_db()
    tid = _row(S, DevTask)
    st = S._Step(tid)
    th = [threading.Thread(target=lambda i=i: [st.event({"k": "read", "path": f"{i}-{j}"}) for j in range(10)]) for i in range(4)]
    [t.start() for t in th]
    [t.join() for t in th]
    with S.session() as s:
        steps = json.loads(s.get(DevTask, tid).steps)
    assert len(steps) == 40 and sorted(x["n"] for x in steps) == list(range(40))


def test_going_back_restores_the_conversation_exactly_even_after_condensing(tmp_path, monkeypatch):
    from app.devsahayak import engine as EN
    monkeypatch.setattr(EN, "folder", lambda tid: tmp_path / tid)
    monkeypatch.setattr(EN, "_commit", lambda repo, msg: "sha1")
    monkeypatch.setattr(EN, "_git", lambda repo, *a: (0, ""))
    ses = EN.Session("t1")
    one = [{"role": "user", "content": "first"}, {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}]
    ses.save_messages(one)
    ses.checkpoint("round 1", len(one))
    # a later round condensed the conversation: the count 2 now points at the wrong place
    ses.save_messages([{"role": "user", "content": "<earlier_in_this_session>\nS\n</earlier_in_this_session>"}] + one * 5)
    ses.checkpoint("round 2", 11)
    ses.rewind(1)
    assert ses.messages() == one
    assert not (tmp_path / "t1" / "messages.cp2.json").exists()       # the undone checkpoint's copy is gone


def test_condensing_keeps_her_words_and_the_earlier_summary(monkeypatch):
    from app.devsahayak import engine as EN
    seen = {}

    def fake_call(system, messages, tools, **k):
        seen["ask"] = messages[0]["content"]
        return [{"type": "text", "text": "SUMMARY-2"}], "end_turn"
    monkeypatch.setattr(EN.B, "call", fake_call)
    msgs = [{"role": "user", "content": "<earlier_in_this_session>\nSUMMARY-1\n</earlier_in_this_session>\nHer own words so far:\n"
                                        "<her_words>\nfix the cart total\n</her_words>\nThat is the summary."}]
    for i in range(12):
        msgs.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"u{i}", "name": "read", "input": {"path": "x"}}]})
        res = [{"type": "tool_result", "tool_use_id": f"u{i}", "content": "x" * 50}]
        if i == 3:
            res.append({"type": "text", "text": "<her_note_while_you_work>\nuse rupees, not dollars\n</her_note_while_you_work>\nTake this"})
        msgs.append({"role": "user", "content": res})
    out = EN.compact(msgs)
    assert "SUMMARY-1" in seen["ask"] and "<earlier_summary>" in seen["ask"]       # handed over whole
    head = out[0]["content"]
    assert "SUMMARY-2" in head and "fix the cart total" in head and "use rupees, not dollars" in head
    # a third condensing still carries both of her messages
    out2 = EN.compact(out + msgs[1:])
    assert "fix the cart total" in out2[0]["content"] and "use rupees, not dollars" in out2[0]["content"]


def test_her_words_are_read_from_every_kind_of_message():
    from app.devsahayak import engine as EN
    m = [{"role": "user", "content": "Task kind: fix. x\n<request>\nfix the cart\n</request>\nmore"},
         {"role": "user", "content": "<her_follow_up>\nmake it blue\n</her_follow_up>\n\n(The working copy is as you left it.)"},
         {"role": "user", "content": "<ci_failure>boom</ci_failure>"}]
    assert EN._her_words(m) == (["fix the cart", "make it blue"], "")


def test_words_that_ask_her_something_are_never_cut():
    from app.devsahayak import engine as EN
    long = "I looked at the cart. " * 6 + "Should the discount apply before tax or after it?"
    assert EN.short_say(long) == long
    assert EN.short_say("One. Two. Three. Four. Five.") == "One. Two. Three."


def test_notes_are_never_cut_or_dropped(env, monkeypatch):
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    init_db()
    tid = _row(S, DevTask)
    monkeypatch.setattr(S, "_RUNNING", {tid})
    long = "please " * 700
    S.add_note("ten", tid, long)
    for i in range(9):
        S.add_note("ten", tid, f"note {i}")
    try:
        S.add_note("ten", tid, "the eleventh")
        raise AssertionError("an eleventh note must wait, not push out the first")
    except S.DevError as e:
        assert "10 of your notes" in str(e)
    with S.session() as s:
        notes = json.loads(s.get(DevTask, tid).notes)
    assert len(notes) == 10 and notes[0] == long.strip()
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "notes = [str(x)[:6000] for x in (inbox() or [])" in eng


def test_a_long_session_keeps_every_message_up_to_the_ceiling():
    from app.devsahayak import service as S
    steps = []
    for i in range(3000):
        steps.append({"k": "say" if i % 3 == 0 else "read", "text": str(i), "n": i})
    out = S.fold_steps(steps)
    assert len(out) <= S.STEPS_CEILING
    kept = {x["n"] for x in out if x["k"] == "say"}
    assert all(i in kept for i in range(1800, 3000, 3))             # the newest 1,300-odd messages all stay
    assert [x["n"] for x in out] == sorted(x["n"] for x in out)


def test_a_check_is_light_and_a_rewind_names_what_it_undid(env):
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    init_db()
    tid = _row(S, DevTask)
    st = S._Step(tid)
    st.event({"k": "say", "text": "a"})
    v = S.get_task("ten", tid, since=0)
    assert "ws" not in v and "diff" not in v and "log" not in v and v["last_n"] == 0 and v["steps"] == []
    src = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert '"from": since' in src and 'x.get("num", -1)) == int(cp["n"])' in src


def test_a_round_the_restart_cut_is_picked_up_without_the_long_wait(monkeypatch):
    from datetime import timedelta
    from app.devsahayak import service as S
    start = S.now() - timedelta(seconds=60)
    monkeypatch.setattr(S, "_PROC_START", start)
    old_beat = {"beat": (start - timedelta(seconds=5)).isoformat()}
    assert S._beat_fresh(old_beat, 180, restart=True) is False                     # from before the restart: cut
    assert S._beat_fresh(old_beat, 180) is True                     # the slow old-loop check keeps its own wait
    assert S._beat_fresh({"beat": S.now().isoformat()}, 180, restart=True) is True


def test_the_phone_keeps_what_she_saw_and_rests_in_the_background():
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "with WidgetsBindingObserver" in ses and "didChangeAppLifecycleState" in ses
    assert "...old,                                       // v0.945" in ses        # a check keeps what it left out
    assert "if (prev != null && !replace)" in ses and "_load(full: true, replace: true)" in ses
    assert "ListView.builder(" in ses and "'say$sn'" in ses and "look${_stepN(s, si)}" in ses
    assert "_sentAt = _lastN;" in ses and "_stepN(s, si) > _sentAt" in ses
    assert "if (full) _wantFull = true;" in ses
    assert "the greyed part above was undone" in ses and "Opacity(opacity: .45" in ses
    assert "ci(s['num'] ?? s['n'])" in ses and "ci(s['n'])" not in ses.replace("ci(s['num'] ?? s['n'])", "")
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "s.num ?? s.n" in js
    assert "Color(0x" not in ses and "FontWeight.w800" not in ses


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.103"' in main
    assert "version: 0.999.103+1098" in (ROOT / "pubspec.yaml").read_text()
