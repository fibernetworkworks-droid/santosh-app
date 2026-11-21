"""v0.944 HOOLA CODE CHAT LANDING (owner: "LETS WORK ON CHAT CONVERSATION LANDING IN HOOLA CODE CHAT .... FIND THE ISSUE
AND FLAWS" -> "GO").

The closing answer is a message at the end of its round, words she watched never vanish, a long session never drops
the conversation, every step has a stable number, and the phone fetches only what is new."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_live_words_hold_a_repeat_and_stream_a_long_answer_whole():
    from app.devsahayak import engine as EN
    EN.LIVE_TEXT.clear(), EN.LIVE_FULL.clear()
    EN.live_sink("t1", "I will", [])
    assert "t1" not in EN.LIVE_TEXT                                  # v0.962 under 4 words: nothing yet
    said = "I read the login code and the token check is missing in the refresh path of the handler"
    EN.live_sink("t1", "I read the login code", [said])
    assert "t1" not in EN.LIVE_TEXT                                  # starts like a recent message: waits to be sure
    EN.live_sink("t1", said, [said])
    assert "t1" not in EN.LIVE_TEXT                                  # a repeat of what she just read is never shown
    EN.live_sink("t3", "I will read the file", [])
    assert EN.LIVE_TEXT["t3"] == "I will read the file"              # v0.962 a fresh reply shows from its 4th word
    first = "Now I am going to read the login handler and the session store to see where the token goes."
    EN.live_sink("t2", first, [])
    assert EN.LIVE_TEXT["t2"] == first                               # v0.962 every reply streams whole, never cut
    long = first + " " + " ".join(f"Sentence number {i} explains one more part of the fix in plain words." for i in range(12))
    EN.live_sink("t2", long, [])
    assert EN.LIVE_FULL.get("t2") and EN.LIVE_TEXT["t2"] == long      # the answer streams whole, not stuck at 3 lines
    assert EN.clock_words(5) == "5s" and EN.clock_words(192) == "3m 12s" and EN.clock_words(3700) == "1h 01m"


def test_a_long_session_never_folds_away_the_conversation():
    from app.devsahayak import service as S
    steps = [{"k": "read", "n": i} for i in range(S.MAX_STEPS + 300)]
    steps[200] = {"k": "note", "text": "please keep the old colours", "n": 200}
    steps[300] = {"k": "say", "text": "Done with the header.", "n": 300}
    steps[310] = {"k": "round", "secs": 90, "n": 310}
    out = S.fold_steps(steps)
    assert len(out) <= S.STEPS_CEILING
    kinds = {(x["k"], x["n"]) for x in out}
    assert ("note", 200) in kinds and ("say", 300) in kinds and ("round", 310) in kinds
    assert any(x["k"] == "gap" for x in out) and [x["n"] for x in out] == sorted(x["n"] for x in out)   # still in order


def test_steps_get_numbers_and_a_check_fetches_only_new_ones(env):
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db, session
    from app.devsahayak import service as S
    from app.devsahayak.models import DevTask
    init_db()
    with session() as s:
        row = DevTask(tenant_id="ten", repo="a/b", text="fix it", status="new", changes="[]")
        s.add(row)
        s.flush()
        tid = row.id
    st = S._Step(tid)
    for i in range(5):
        st.event({"k": "read", "path": f"f{i}.py"})
    full = S.get_task("ten", tid)
    assert [x["n"] for x in full["steps"]] == [0, 1, 2, 3, 4] and full["last_n"] == 4
    st.event({"k": "say", "text": "Found it."})
    delta = S.get_task("ten", tid, since=4)
    assert [x["k"] for x in delta["steps"]] == ["say"] and delta["steps"][0]["n"] == 5 and delta["last_n"] == 5
    assert "diff" not in delta and "file_diffs" not in delta and "log" not in delta   # the heavy parts stay out


def test_the_engine_makes_the_closing_answer_a_message_and_marks_the_round():
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert 'emit({"k": "say", "text": q[:20000], "final": True})' in eng
    assert 'emit({"k": "round", "secs":' in eng
    assert "if shown or not said_before(txt, recent):" in eng          # words she watched are never dropped
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    assert "since: int | None = None" in api
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "case 'round':" in js and "x => x.final" in js


def test_the_phone_lands_by_step_number_and_asks_only_for_new_steps():
    f = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "{'since': '$_lastN'}" in f and "_load(full: true)" in f
    assert "_landed[key] = _landed.remove('live')!" in f             # v0.964 the words being written hand over to the message carrying them
    assert "k == 'round'" in f and "_roundLine(" in f
    assert "s['final'] == true && question.isNotEmpty" in f          # a question is not drawn twice
    assert "!hasFinal && ex.isNotEmpty" in f                          # older sessions still show their answer
    assert "Color(0x" not in f and "FontWeight.w800" not in f


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.70"' in main
    assert "version: 0.999.70+1068" in (ROOT / "pubspec.yaml").read_text()
