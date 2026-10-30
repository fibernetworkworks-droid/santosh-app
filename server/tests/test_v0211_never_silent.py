"""v0.215.0 NEVER SILENT (built as 0.211.0 on the v0.210.0 REA chain; rebased onto the dev's parallel v0.211 SEMANTIC BROWSER + v0.212 Sheets + v0.213 REA-voice chain and RE-VERSIONED 0.215.0 - sixth collision, both works kept): — the five voice-to-voice reliability failures the owner reported BEFORE Phase D
("IT FORGOT THE WORK -- NO PERSISTENT WORK, NO CONSISTENCY, IF STUCK NO REPLY, NOT ABLE TO SOLVE THE ISSUE
ON ITS OWN, IF WE DONT GIVE CALL TO VOICE AI IT NEVER REPLY ON ITS OWN"), root-caused first (Task 6 RCA),
now fixed in-process:

1. NEVER SILENT: Gemini sometimes stops sending anything mid-call - downlink blocks in session.receive()
   forever, the phone shows a connected-but-dead call. New _stall_watch runs beside uplink/downlink:
   one nudge as text, then a forced reconnect (resumable handle keeps the context), then the honest error.
2. NO PERSISTENT WORK: late results (_late_result) and undeliverable tool results (_note_result) were
   DROPPED when the call had closed, and quiet notes died with the session. New yaad call_followup notes
   keep them, and the NEXT call OPENS with the news (greeting followup= wording) - work is postponed,
   never lost. The fresh greeting no longer orders amnesia ("do not bring up anything from before").
3. SELF-SOLVE: one Gemini refusal used to take the whole setup ladder away for 7 DAYS (persisted to
   data/voice_setup.json): calls without compression forgot mid-call, calls without core_tools / with
   no_tools could not DO anything. Soft losses (mcp/vocab/langcodes) stay remembered; heavy losses
   (compression/core_tools/no_tools) self-heal in an hour and are never loaded from disk. Plus the
   AUTO-RESCUE: the same tool failing twice in a call hands the work to the full agent by itself.
4. IT NEVER REPLIES ON ITS OWN: a finished job could reach chat + push + a LIVE call only. kind=voice_ring
   data push (gated: setting off until the native side learns the kind, quiet hours, daily budget, never
   while a call is live) is the server half of the server-initiated ring.
"""
import asyncio
import json
import threading
import time
from collections import Counter
from types import SimpleNamespace

import pytest

import app.yaad as yaad
import app.push as push
from app import voice
from app.config import get_settings
from app.db import Conversation, session
from app.main import APP_VERSION
from app.voice import Call, greeting, SETUP, SETUP_SOFT_MAX, SETUP_STEPS, _AUTO_RESCUE_SKIP


# ---------------- fakes ----------------

class _FakeCall:
    """Just the attributes the touched paths use (the v0.206 watcher pattern)."""

    def __init__(self):
        self.conv, self.tenant = "c_ns", "default"
        self.call_id = "ns_test_call"
        self.closed = asyncio.Event()
        self.hold = ""
        self.stats = {"stall_nudges": 0, "stall_reconnects": 0, "auto_rescues": 0, "orphan_notes": 0}
        self.user_buf = ""
        self._turn_audio = False
        self._tool_runs = 0
        self._last_model_audio = 0.0
        self._last_voice_at = 0.0
        self._last_user_text_at = 0.0
        self._stall_nudged = False
        self._stall_at = 0.0
        self._stall_reconnects = 0
        # v0.220 the tone surface exists but stays empty on this fake (no tag rides the nudge here)
        self._tone, self._tone_at = "", 0.0
        self._tone_now = lambda: voice.Call._tone_now(self)
        self._tone_tag = lambda: voice.Call._tone_tag(self)
        self._auto_rescued = set()
        self.pushed = []
        self.sent_json = []
        self.breaker = SimpleNamespace(fails=Counter())


    def push_news(self, text):                       # v0.230 the news queue; tested in test_v0228
        self.push("text", text)
    def push(self, kind, data, force=False):
        self.pushed.append((kind, data))

    async def send_json(self, obj):
        self.sent_json.append(obj)

    def _orphan_note(self, text):
        voice.Call._orphan_note(self, text)     # the real path, so _note_result/_late_result wiring is tested


class _FakeSession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


def _stalled(c: _FakeCall, ago: float = 30.0):
    """Her turn is open and nobody has said anything for `ago` seconds."""
    c.user_buf = "mera kaam batao"
    t = time.monotonic() - ago
    c._last_voice_at = t
    c._last_user_text_at = t
    c._last_model_audio = 0.0


def _run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def _watch(c, session, seconds=0.08):
    """Run the watchdog on ONE loop for `seconds`, then cancel it (the poll is shrunk inside the loop)."""
    async def _drive():
        old = voice._STALL_POLL_S
        voice._STALL_POLL_S = 0.01
        t = asyncio.ensure_future(voice.Call._stall_watch(c, session))
        try:
            await asyncio.sleep(seconds)
        finally:
            t.cancel()
            voice._STALL_POLL_S = old
            try:
                await t
            except asyncio.CancelledError:
                pass
    _run(_drive())


_NS = SimpleNamespace(voice_stall_watch=True, voice_stall_nudge_s=14, voice_stall_reconnect_s=28,
                      voice_auto_rescue=True, voice_followup_min=720, voice_continuation_min=60,
                      voice_setup_hard_keep_s=3600, voice_safe_setup=True)


# ---------------- 1. the setup ladder heals itself (self-solve) ----------------

def test_setup_soft_max_is_three():
    assert SETUP_SOFT_MAX == 3
    assert SETUP_STEPS[SETUP_SOFT_MAX:] == ("compression", "core_tools", "no_tools")


def test_heavy_loss_never_persists_to_disk(tmp_path, monkeypatch):
    f = tmp_path / "voice_setup.json"
    monkeypatch.setattr(voice, "_setup_file", lambda: f)
    monkeypatch.setattr(voice, "_setup_key", lambda: "k")
    SETUP.update(step=0, key="", at=0.0, loaded=True)
    voice.remember_setup(5)                       # compression+tools gone: memory only
    assert not f.exists()                         # v0.211: never to disk
    assert SETUP["step"] == 5
    voice.remember_setup(2)                       # gentle loss: the file is written as before
    assert f.exists() and json.loads(f.read_text())["step"] == 2


def test_loaded_file_step_is_clamped_to_soft(tmp_path, monkeypatch):
    f = tmp_path / "voice_setup.json"
    f.write_text(json.dumps({"step": 6, "key": "k", "at": time.time()}))   # an old version's 'no tools'
    monkeypatch.setattr(voice, "_setup_file", lambda: f)
    monkeypatch.setattr(voice, "_setup_key", lambda: "k")
    monkeypatch.setattr(voice, "get_settings", lambda: SimpleNamespace(voice_safe_setup=True,
                                                                       voice_setup_hard_keep_s=3600,
                                                                       gemini_live_model="m"))
    import app.voice as v
    monkeypatch.setattr(v, "_setup_key", lambda: "k")
    SETUP.update(step=0, key="", at=0.0, loaded=False)
    assert v.setup_step() == 3                    # tools and compression come back NOW


def test_hard_step_decays_after_an_hour(monkeypatch):
    monkeypatch.setattr(voice, "get_settings", lambda: SimpleNamespace(voice_safe_setup=True,
                                                                       voice_setup_hard_keep_s=3600,
                                                                       gemini_live_model="m"))
    monkeypatch.setattr(voice, "_setup_key", lambda: "k")
    monkeypatch.setattr(voice, "_setup_file", lambda: __import__("pathlib").Path("/nonexistent/ns.json"))
    SETUP.update(step=5, key="k", at=time.time() - 3700, loaded=True)
    assert voice.setup_step() == 0                # heavy loss self-healed: full setup is tried again
    assert SETUP["step"] == 0
    SETUP.update(step=2, key="k", at=time.time() - 3700, loaded=True)
    assert voice.setup_step() == 2                # a gentle loss keeps its 7-day memory


# ---------------- 2. the greeting: news first, no more amnesia ----------------

def test_followup_greeting_opens_with_the_news():
    g = greeting("default", "m", followup="sheet update ho gayi thi, 12 rows")
    assert "natija aaya tha" in g and "sheet update ho gayi thi, 12 rows" in g
    assert "EK chhoti line" in g                  # the news comes FIRST, in one short line


def test_fresh_greeting_allows_continuity():
    g = greeting("default", "m")
    assert "HOOLA KI YAAD" in g and "wahi kaam pe chalte hain" in g
    assert "do not bring up anything from before" not in g   # the amnesia order is GONE


def test_continuation_greeting_unchanged():
    g = greeting("default", "m", continuation="aakhri poori baat: pizza order karna tha")
    assert "KOI NAYA CALL NAHI" in g


def test_run_uses_drop_then_followup():
    src = open(voice.__file__).read()
    assert "take_call_followup" in src and "voice_followup_min" in src
    assert 'drop_kind == "followup"' in src       # the greeting picks the right wording


# ---------------- 3. the never-silent watchdog ----------------

def test_stall_watch_nudges_then_waits(monkeypatch):
    monkeypatch.setattr(voice, "get_settings", lambda: _NS)
    c, s = _FakeCall(), _FakeSession()
    _stalled(c)
    _watch(c, s)
    assert c.stats["stall_nudges"] == 1 and c._stall_nudged
    assert any("System:" in d for k, d in c.pushed)          # the nudge went as a text note
    assert not s.closed and not c.closed.is_set()            # one nudge, then patience


def test_stall_watch_forces_reconnect_after_the_nudge(monkeypatch):
    monkeypatch.setattr(voice, "get_settings", lambda: _NS)
    c, s = _FakeCall(), _FakeSession()
    _stalled(c)
    c._stall_nudged = True
    c._stall_at = time.monotonic() - 30
    _watch(c, s)
    assert s.closed and c.stats["stall_reconnects"] == 1 and not c._stall_nudged


def test_stall_watch_three_reconnects_end_the_call_honestly(monkeypatch):
    monkeypatch.setattr(voice, "get_settings", lambda: _NS)
    c, s = _FakeCall(), _FakeSession()
    _stalled(c)
    c._stall_nudged = True
    c._stall_at = time.monotonic() - 30
    c._stall_reconnects = 2
    _watch(c, s)
    assert c.closed.is_set() and c._stall_reconnects == 3
    assert c.stats["stall_reconnects"] == 1                     # one more event in the call's scorecard
    assert any(m.get("type") == "error" for m in c.sent_json)   # the phone gets the honest error


def test_stall_watch_stays_out_of_tools_and_holds(monkeypatch):
    monkeypatch.setattr(voice, "get_settings", lambda: _NS)
    for setup in (lambda c: setattr(c, "_tool_runs", 1), lambda c: setattr(c, "hold", "phone_call")):
        c, s = _FakeCall(), _FakeSession()
        _stalled(c)
        setup(c)
        _watch(c, s, 0.05)
        assert c.stats["stall_nudges"] == 0 and not s.closed


def test_stall_watch_respects_turn_closed_and_kill_switch(monkeypatch):
    monkeypatch.setattr(voice, "get_settings", lambda: _NS)
    c, s = _FakeCall(), _FakeSession()
    _stalled(c)
    c.closed.set()                                # the call is over: nothing to watch
    _watch(c, s, 0.05)
    assert c.stats["stall_nudges"] == 0
    monkeypatch.setattr(voice, "get_settings", lambda: SimpleNamespace(voice_stall_watch=False))
    c2, s2 = _FakeCall(), _FakeSession()
    _stalled(c2)
    _run(voice.Call._stall_watch(c2, s2))       # kill switch: returns at once, no error
    assert not s2.closed


def test_mark_audio_resets_the_watchdog_clock():
    c = _FakeCall()
    c._stall_nudged, c._stall_reconnects = True, 1
    c._bc_task = None
    c._safe_worked = True
    c._safe = 0
    c._turn_audio = False
    c._turn_end_at = 0.0
    c._last_voice_at = 0.0
    c._latency = None
    c.stats["latency_ms"] = []
    voice.Call._mark_audio(c)
    assert not c._stall_nudged and c._stall_reconnects == 0   # he is back: clock whole


# ---------------- 4. durability: late results are never dropped ----------------

def test_orphan_note_saves_a_call_followup(monkeypatch):
    got = []
    monkeypatch.setattr(yaad, "note_call_followup", lambda conv, tenant, text: got.append((conv, tenant, text)))
    c = _FakeCall()
    voice.Call._orphan_note(c, "x" * 2000)
    assert got and got[0][0] == "c_ns" and got[0][1] == "default"
    assert "x" in got[0][2]                                    # yaad clips it to the focus size (roundtrip test pins that)
    assert c.stats["orphan_notes"] == 1


def test_late_result_on_closed_call_becomes_a_followup(monkeypatch):
    got = []
    monkeypatch.setattr(yaad, "note_call_followup", lambda conv, tenant, text: got.append(text))
    c = _FakeCall()
    c.closed.set()
    async def _job():
        return {"status": "done", "rows": 12}
    async def _drive():
        j = asyncio.ensure_future(_job())
        await j                                  # finish on THIS loop, like a real done-callback
        voice.Call._late_result(c, j, "sheet update karo")
    _run(_drive())
    assert got and "sheet update karo" in got[0] and "rows" in got[0]   # the NEXT call tells her


def test_note_result_on_closed_call_becomes_a_followup(monkeypatch):
    got = []
    monkeypatch.setattr(yaad, "note_call_followup", lambda conv, tenant, text: got.append(text))
    c = _FakeCall()
    c.closed.set()
    voice.Call._note_result(c, "browse_web", {"result": "page khul gaya"})
    assert got and "browse_web" in got[0]


def test_quiet_notes_pending_at_end_are_saved(monkeypatch):
    src = open(voice.__file__).read()
    assert "_quiet_pending" in src and "call ke ant tak yeh notes useh nahi bataye ja sake" in src


def test_followup_notes_roundtrip(env):
    conv = "c_ns_follow"
    with session() as sdb:
        if sdb.get(Conversation, conv) is None:
            sdb.add(Conversation(id=conv, tenant_id="default", title="t"))
    yaad.note_call_followup(conv, "default", "kaam poora hua tha par bataya nahi ja saka")
    yaad.note_call_followup(conv, "default", "doosra natija")
    got = yaad.take_call_followup(conv, 720)
    assert got == "doosra natija"                 # newest first, consumed ONCE
    assert yaad.take_call_followup(conv, 720) == "kaam poora hua tha par bataya nahi ja saka"   # the next call gets the other
    assert yaad.take_call_followup(conv, 720) == ""          # both consumed: nothing waiting


# ---------------- 5. the auto-rescue ----------------

def test_auto_rescue_skip_list_guards_money_and_one_shots():
    for t in ("haan_karo", "side_talk", "computer_operator", "set_phone_alarm", "set_phone_timer",
              "remember", "forget", "list_add", "list_done", "consent_jaanch", "hoola_answer_connect"):
        assert t in _AUTO_RESCUE_SKIP
    assert "browse_web" not in _AUTO_RESCUE_SKIP and "email_draft" not in _AUTO_RESCUE_SKIP


def test_run_tool_wiring_pins():
    src = open(voice.__file__).read()
    assert "self._tool_runs += 1" in src and "self._tool_runs -= 1" in src
    assert "self._breaker.fails.get(name, 0) >= 2" in src
    assert "name not in _AUTO_RESCUE_SKIP" in src and "name not in self._auto_rescued" in src
    assert "get_settings().voice_auto_rescue" in src
    assert "auto_rescue" in src and "santosh_kaam" in src      # the tool answer says the rescue happened


def test_auto_rescue_fast_result_is_told(monkeypatch):
    c = _FakeCall()
    async def _delegate(self, req):
        return {"result": "ho gaya: 12 rows update"}
    c._delegate = _delegate.__get__(c)             # bind as a method
    _run(voice.Call._auto_rescue(c, "sheet update karo", "sheet_milaan"))
    assert any("Auto-rescue" in d for k, d in c.pushed)


def test_auto_rescue_closed_call_saves_followup(monkeypatch):
    got = []
    monkeypatch.setattr(yaad, "note_call_followup", lambda conv, tenant, text: got.append(text))
    c = _FakeCall()
    c.closed.set()
    async def _delegate(self, req):
        return {"result": "ho gaya"}
    c._delegate = _delegate.__get__(c)             # bind as a method
    _run(voice.Call._auto_rescue(c, "sheet update karo", "sheet_milaan"))
    assert got and "auto-rescue" in got[0]


def test_auto_rescue_working_job_keeps_the_late_path(monkeypatch):
    c = _FakeCall()
    async def _delegate(self, req):
        return {"status": "working"}
    c._delegate = _delegate.__get__(c)
    _run(voice.Call._auto_rescue(c, "bada kaam", "browse_web"))
    assert not c.pushed                            # _late_result will tell her when it is done


# ---------------- 6. the server-initiated voice ring (server half) ----------------

def test_voice_ring_is_a_raw_push_kind():
    assert "voice_ring" in push.RAW_KINDS and "voice_ring" in push.PUSH_KINDS
    body = push.build("tok", {"kind": "voice_ring", "id": "kf1", "at": "",
                              "payload": {"reason": "kaam done: sheet", "ref": "kf1", "conv": "c"}})
    assert body["message"]["data"]["kind"] == "voice_ring"
    assert "sheet" in body["message"]["data"]["payload"]


def test_ring_gates(monkeypatch):
    push._RING_DAY.clear()
    now_h = __import__("datetime").datetime.now(__import__("zoneinfo").ZoneInfo("Asia/Kolkata")).hour
    ns = SimpleNamespace(voice_ring=True, voice_ring_max_day=2, voice_ring_quiet="22-8")
    monkeypatch.setattr(push, "get_settings", lambda: ns)
    import app.voice as v
    monkeypatch.setattr(v, "ACTIVE", {})           # no live call
    # a window that surely excludes the current hour (quiet all day except this hour):
    inside = f"{now_h}-{(now_h + 1) % 24}"
    monkeypatch.setattr(push, "get_settings", lambda: SimpleNamespace(voice_ring=True, voice_ring_max_day=2,
                                                                      voice_ring_quiet=inside))
    assert not push._ring_allowed("default", "c1")            # quiet hours now
    # v0.219 hour-independent: the "22-8" default broke these True-asserts whenever the suite ran inside
    # the IST quiet window (22-8) - a wrap-around window excluding the current hour proves the same thing
    outside = f"{(now_h + 1) % 24}-{now_h}"
    monkeypatch.setattr(push, "get_settings", lambda: SimpleNamespace(voice_ring=True, voice_ring_max_day=2,
                                                                      voice_ring_quiet=outside))
    assert push._ring_allowed("default", "c1") is True
    assert push._ring_allowed("default", "c1") is True
    assert push._ring_allowed("default", "c1") is False       # the daily budget is spent (2)
    monkeypatch.setattr(push, "get_settings", lambda: SimpleNamespace(voice_ring=False, voice_ring_max_day=2,
                                                                      voice_ring_quiet="22-8"))
    assert push._ring_allowed("default", "c1") is False       # off = off
    push._RING_DAY.clear()
    monkeypatch.setattr(v, "ACTIVE", {"c1": [("loop", "call")]})   # a live call on this chat
    monkeypatch.setattr(push, "get_settings", lambda: SimpleNamespace(voice_ring=True, voice_ring_max_day=2,
                                                                      voice_ring_quiet="22-8"))
    assert push._ring_allowed("default", "c1") is False       # never ring a phone already talking
    push._RING_DAY.clear()


def test_kaam_followup_rings_when_enabled():
    src = open(__import__("app.kaam_followup", fromlist=["x"]).__file__).read()
    assert "voice_ring" in src and "settings.voice_ring" in src
    assert "_push.on_event" in src


# ---------------- 7. the scorecard carries the reliability numbers ----------------

def test_scorecard_has_reliability_rollups():
    push_stats = {"stall_nudges": 2, "stall_reconnects": 1, "auto_rescues": 1, "orphan_notes": 3}
    for k in push_stats:
        assert f'"{k}"' in open(voice.__file__).read()


def test_version():
    assert APP_VERSION == "0.306.0"
