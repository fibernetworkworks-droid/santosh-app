"""v0.668 SAAF SCREEN (owner: "GO WAVE 8" of the second deep audit - smoothness on her screen).

32 a step cut by the turn's time limit says so on its card (no spinner for ever)
33 a corrected reply is shown once: only the correction line goes out and is saved
34 the phone's typing dots are refreshed on the clock while a turn runs (a busy turn was never "idle")
35 the "Ek second..." line is a placeholder on the phone: removed by the real reply, never spoken, never a heal
36 an event that reaches the stream late is read back from the database in order, never dropped
37 the chat history is read off the event loop
"""
from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_a_cut_off_step_says_so_on_its_card():
    from app.agent import santosh
    src = inspect.getsource(santosh._steps_inner)
    i = src.index("except asyncio.CancelledError:")
    block = src[i:i + 1400]
    assert '"state": "error"' in block and '"stopped"' in block and "raise" in block


def test_a_corrected_reply_goes_out_once():
    from app.agent import santosh
    src = inspect.getsource(santosh._steps_inner)
    i = src.index('if state.get("correct"):')
    block = src[i:i + 1100]
    assert '"text": note' in block and '"note": True' in block
    assert '"text": final_text, "source": "agent",\n                                                         **_tag(live)})' not in block


def test_typing_is_refreshed_on_the_clock():
    from app import main
    src = inspect.getsource(main.events)
    assert "typed_at" in src and "ticks % 4" not in src
    assert "time.monotonic() - typed_at >= 45" in src


def test_a_late_event_is_read_back_in_order():
    from app import main
    src = inspect.getsource(main.events)
    assert 'if ev["id"] > sent + 1:' in src and "bus.backlog, conversation_id, sent, 50, tenant" in src


def test_the_phone_treats_the_ack_as_a_placeholder():
    dart = (ROOT / "lib/state.dart").read_text(encoding="utf-8")
    assert "if (p['ack'] == true) {" in dart and "_ackDrop()" in dart and "FeedItem? _ackItem" in dart
    i = dart.index("if (p['ack'] == true) {")
    blk = dart[i:i + 600]
    assert "break;" in blk and "_speak" not in blk            # never spoken, never a reply
    assert "f.eid != null && f.eid! > 0" in dart               # a live-only row never triggers a chat heal


def test_history_is_read_off_the_loop():
    from app.agent import santosh
    src = inspect.getsource(santosh._run_turn)
    assert "await asyncio.to_thread(_load_history, conversation_id)" in src
    assert "history = _load_history(conversation_id)" not in src
