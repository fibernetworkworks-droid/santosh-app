"""v0.648 KAAM KA HISAAB (owner: GO on the work audit's four fixes): one list of running / waiting / finished work for
the phone and the console, a call that knows this week's finished work, a call record's notification opens that call,
and the chat no longer gets the recent calls twice."""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.db import Conversation, session

T = "default"
ROOT = Path(__file__).resolve().parents[2]


def _chat(cid: str, project: str | None = None) -> str:
    with session() as s:
        s.add(Conversation(id=cid, tenant_id=T, project_id=project))
    return cid


def _clear():
    from app import callconv
    callconv._KIND.clear()
    callconv._ORIGIN.clear()


def _job(conv: str, key: str, state: str, title: str, hours_ago: float = 1):
    from app.kaamwatch import KaamJob
    at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    with session() as s:
        s.add(KaamJob(tenant_id=T, conversation_id=conv, key=key, kind="site_board", label="Website", title=title,
                      state=state, status=state, updated_at=at, moved_at=at, started_at=at))


def _run(conv: str, request: str, outcome: str = "done", days_ago: float = 0.5, left: str = ""):
    from app.agent.pakka import TaskRun
    with session() as s:
        s.add(TaskRun(tenant_id=T, request=request, outcome=outcome, steps=3, left=left, conversation_id=conv,
                      created_at=datetime.now(timezone.utc) - timedelta(days=days_ago)))


def test_listing_groups_running_waiting_and_done(env):
    from app import callconv, kaamlist
    _clear()
    _chat("c1")
    rec = callconv.open_for(T, "c1", "")
    _job("c1", "site_board:a", "working", "Bakery site")
    _job("c1", "site_board:b", "waiting", "Clinic site")
    _job(rec, "site_board:c", "done", "Salon site")
    _run("c1", "Sharma ji ko mail bhejo")
    _run("c1", "bahut purana kaam", days_ago=12)        # older than 7 days: not listed
    _run("c1", "bas baat", outcome="talk")              # a talk is not work
    d = kaamlist.listing(T)
    assert [x["title"] for x in d["running"]] == ["Bakery site"]
    assert [x["title"] for x in d["waiting"]] == ["Clinic site"]
    titles = [x["title"] for x in d["done"]]
    assert "Salon site" in titles and "Sharma ji ko mail bhejo" in titles
    assert "bahut purana kaam" not in titles and "bas baat" not in titles
    salon = next(x for x in d["done"] if x["title"] == "Salon site")
    assert salon["from_call"] is True and salon["conversation_id"] == rec
    mail = next(x for x in d["done"] if x["title"] == "Sharma ji ko mail bhejo")
    assert mail["from_call"] is False and mail["say"] == "ho gaya"


def test_call_brief_knows_this_weeks_work_in_its_scope(env):
    from app import callconv, kaamlist
    _clear()
    _chat("home")
    _chat("work", project="clientX")
    rec = callconv.open_for(T, "home", "")
    _run("home", "GST report banao", left="March ka data")
    _job("home", "site_board:z", "done", "Mithai site", hours_ago=30)   # yesterday: beyond the 6 h job block
    _run("work", "client X quote")                                      # another Session: fenced out
    b = kaamlist.brief(T, rec)
    assert "IS HAFTE KA KIYA HUA KAAM" in b
    assert "GST report banao" in b and "baaki: March ka data" in b and "Mithai site" in b
    assert "client X" not in b


def test_call_brain_turn_reads_the_brief():
    from app.agent import santosh
    src = inspect.getsource(santosh._brain_memory)
    assert '("kiya", lambda: _kaamlist.brief(tenant_id, conversation_id))' in src


def test_chat_turn_gets_recent_calls_once_through_the_diary(env):
    from app import callconv, yaad
    from app.agent import santosh
    from app.agent.santosh import _save
    _clear()
    _chat("c9")
    rec = callconv.open_for(T, "c9", "")
    _save(rec, "assistant", [{"type": "text", "text": "[Call receipt] 📞 Call ka hisaab (2 min): bijli bill"}],
          display="📞 Call ka hisaab (2 min): bijli bill")
    d = yaad.diary(T, "c9")
    assert any("bijli bill" in x for x in d["calls"])          # the call record's receipt reaches the chat
    assert "_callconv.recent_block, tenant_id, conversation_id" not in inspect.getsource(santosh)


def test_a_call_records_notification_opens_that_call(env):
    from app import callconv, push
    _clear()
    _chat("c5")
    rec = callconv.open_for(T, "c5", "")
    ev = {"kind": "message", "id": 7, "at": "", "conv": rec, "payload": {"role": "assistant", "text": "Report ready"}}
    msg = push.build("tok", ev, "Hoola")
    assert msg["message"]["data"]["open_conv"] == rec
    chat = push.build("tok", {**ev, "conv": "c5"}, "Hoola")
    assert "open_conv" not in chat["message"]["data"]


def test_phone_opens_the_call_from_the_notification():
    kt = (ROOT / "tool/android/kotlin/Notify.kt").read_text()
    assert 'ACTION_OPEN_CONV = "com.newtika.santosh.OPEN_CONV"' in kt and "openConv(ctx, conv)" in kt
    assert 'd["open_conv"] ?: ""' in (ROOT / "tool/android/kotlin/SantoshPush.kt").read_text()
    ma = (ROOT / "tool/android/kotlin/MainActivity.kt").read_text()
    assert "action == Notify.ACTION_OPEN_CONV" in ma and '"conv:$conv"' in ma
    dart = (ROOT / "lib/main.dart").read_text()
    assert "t.startsWith('conv:')" in dart and "remember: false" in dart


def test_kaam_list_surfaces():
    sheet = (ROOT / "lib/ui/kaam_sheet.dart").read_text()
    assert "kaamList()" in sheet and "Pichhle 7 din mein hua" in sheet and "remember: !call" in sheet
    assert "showKaamSheet(context, app)" in (ROOT / "lib/ui/chat_screen.dart").read_text()
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "drawTodayWork()" in js and "/api/kaam/list" in js and "Done in the last 7 days" in js


def test_kaam_list_route(env):
    from fastapi.testclient import TestClient
    from app.config import get_settings
    from app.main import app
    _clear()
    _chat("c7")
    _run("c7", "invoice banao")
    key = get_settings().api_key
    h = {"Authorization": f"Bearer {key}"} if key else {}
    with TestClient(app) as cl:
        r = cl.get("/api/kaam/list", headers=h)
    assert r.status_code == 200 and r.json()["counts"]["done"] >= 1
