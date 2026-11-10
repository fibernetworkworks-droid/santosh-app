"""v0.407 ABHI ABHI (App Sahayak Pillar C, Phase 49): real time for the native apps.

One SSE stream per open app, fed by the journal (every write, every path, every worker process): live list rows filtered by
each list's read rule (a customer never hears about another customer's order), instant chat to that thread only, presence
(customers see staff only) and typing (scoped to one thread), Last-Event-ID replay after a reconnect (too many missed =
reset), a Postgres commit that lands out of order is still delivered, limits (sign-in needed, streams per account), her own
owner view, and both kits carry the live client."""
import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app" / "appmaker"


def _events(body: str) -> list[dict]:
    out = []
    for block in body.split("\n\n"):
        data = [ln[6:] for ln in block.split("\n") if ln.startswith("data: ")]
        if data:
            ev = json.loads("\n".join(data))
            ids = [ln[4:] for ln in block.split("\n") if ln.startswith("id: ")]
            if ids:
                ev["_id"] = ids[0]
            out.append(ev)
    return out


def _shop(droid_env):
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")):
        _acct(c, api, e, n)
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    hs = {n: _login(c, api, f"{n.lower()}@example.com", n) for n in ("Asha", "Neha", "Ravi")}
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    ids = {n: mem[f"{n.lower()}@example.com"]["id"] for n in ("Asha", "Neha", "Ravi")}
    return c, aid, api, hs, p1, ids


def _listen(api_path, headers, out, key):
    from app.main import app
    out[key] = TestClient(app).get(api_path, headers=headers)


def test_live_stream_filters_every_event_by_the_read_rule(droid_env, monkeypatch):
    from app.appmaker import live as LV
    monkeypatch.setattr(LV, "STREAM_SECONDS", 3.5)
    c, aid, api, hs, p1, ids = _shop(droid_env)
    assert c.get(f"{api}/live").status_code == 401                           # no anonymous streams
    got: dict = {}
    ts = [threading.Thread(target=_listen, args=(f"{api}/live", hs[n], got, n)) for n in ("Asha", "Ravi")]
    ts.append(threading.Thread(target=_listen, args=(f"/api/apps/{aid}/live", {}, got, "owner")))
    for t in ts:
        t.start()
    time.sleep(1.0)
    on = c.get(f"{api}/live/presence", headers=hs["Neha"]).json()["online"]    # a customer sees the shop's staff, not Asha
    assert {x["name"] for x in on} == {"Ravi", "Shop"} and all(x["staff"] for x in on), on
    assert all(len(x["member"]) < 20 and x["member"].startswith("staff:") for x in on)
    assert {x["name"] for x in c.get(f"{api}/live/presence", headers=hs["Ravi"]).json()["online"]} == {"Asha", "Shop"}
    on_r = {x["name"]: x for x in c.get(f"{api}/live/presence", headers=hs["Ravi"]).json()["online"]}
    assert on_r["Asha"]["member"] == ids["Asha"]                               # staff see who exactly
    on_her = {x["name"] for x in c.get(f"/api/apps/{aid}/live/presence").json()["online"]}
    assert on_her == {"Asha", "Ravi"}
    o_n = c.post(f"{api}/c/orders", json={"name": "Neha", "phone": "9876500001", "cart": [{"id": p1["id"], "qty": 1}]},
                 headers=hs["Neha"]).json()
    o_a = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876500002", "cart": [{"id": p1["id"], "qty": 2}]},
                 headers=hs["Asha"]).json()
    c.post(f"{api}/chat", json={"text": "Kab aayega?"}, headers=hs["Asha"])
    c.post(f"{api}/chat", json={"text": "Neha ka sawaal"}, headers=hs["Neha"])
    assert c.post(f"{api}/live/typing", json={}, headers=hs["Neha"]).json()["ok"]
    assert c.post(f"{api}/live/typing", json={"thread": ids["Asha"]}, headers=hs["Ravi"]).json()["ok"]
    assert c.post(f"{api}/live/typing", json={}, headers=hs["Ravi"]).status_code == 400   # staff must name the thread
    c.post(f"{api}/chat/{ids['Asha']}", json={"text": "Shaam tak"}, headers=hs["Ravi"])
    c.patch(f"/api/apps/{aid}/data/orders/{o_a['id']}", json={"status": "Out for delivery"})   # her console moves it
    for t in ts:
        t.join(15)
    asha, ravi, her = (_events(got[k].text) for k in ("Asha", "Ravi", "owner"))
    for k in ("Asha", "Ravi", "owner"):
        assert got[k].status_code == 200 and got[k].headers["content-type"].startswith("text/event-stream")
        assert got[k].headers.get("x-accel-buffering") == "no"
    assert asha[0]["type"] == "hello" and asha[-1] == {"type": "bye", "why": "again"}
    rows_a = [e for e in asha if e["type"] == "row"]
    assert rows_a and {e["id"] for e in rows_a} == {o_a["id"]}, rows_a                 # never Neha's order
    assert all(e["_id"].startswith("j") for e in rows_a) and rows_a[0]["row"]["mine"] is True
    assert not any(k.startswith("_") for e in rows_a for k in e["row"])               # nothing internal leaves
    chats_a = [e["text"] for e in asha if e["type"] == "chat"]
    assert chats_a == ["Kab aayega?", "Shaam tak"], chats_a                            # her thread only
    assert [e for e in asha if e["type"] == "typing"] == [{"type": "typing", "thread": ids["Asha"], "name": "Ravi", "staff": True}]
    rows_r = {e["id"] for e in ravi if e["type"] == "row"}
    assert {o_a["id"], o_n["id"]} <= rows_r                                            # staff see every order
    assert [e["text"] for e in ravi if e["type"] == "chat"] == ["Kab aayega?", "Neha ka sawaal", "Shaam tak"]
    assert [e["name"] for e in ravi if e["type"] == "typing"] == ["Neha"]               # not his own
    moved = [e for e in her if e["type"] == "row" and e["id"] == o_a["id"]]
    assert moved and moved[-1]["status"] == "Out for delivery" and moved[-1]["op"] == "update"
    assert any(e["type"] == "row" and e["id"] == o_a["id"] and e.get("status") == "Out for delivery" for e in asha)


def test_reconnect_replays_what_was_missed(droid_env, monkeypatch):
    import asyncio

    from app.appmaker import live as LV
    from app.appmaker.backup import AppJournal
    from app.appmaker.models import AppProject
    from app.db import session
    from app.site import webapp as W
    from sqlalchemy import select
    c, aid, api, hs, p1, ids = _shop(droid_env)
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
        last = s.scalar(select(AppJournal.id).order_by(AppJournal.id.desc()).limit(1)) or 0
    o_n = c.post(f"{api}/c/orders", json={"name": "Neha", "phone": "9876500001", "cart": [{"id": p1["id"], "qty": 1}]},
                 headers=hs["Neha"]).json()
    o_a = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876500002", "cart": [{"id": p1["id"], "qty": 1}]},
                 headers=hs["Asha"]).json()

    def who(n):
        return W.Who(W.member_of("app:" + aid, hs[n]["Authorization"][7:]))

    loop = asyncio.new_event_loop()
    try:
        sub_a = LV.Sub(r, who("Asha"), None, loop)
        sub_r = LV.Sub(r, who("Ravi"), None, loop)
        evs, upto, reset = LV.replay(sub_a, f"j{last}")
        assert not reset and {e["id"] for e in evs if e["type"] == "row"} == {o_a["id"]}   # created + priced = 2 events, 1 row
        evs_r, upto_r, _ = LV.replay(sub_r, f"j{last}")
        assert {o_n["id"], o_a["id"]} <= {e["id"] for e in evs_r if e["type"] == "row"} and upto_r == upto >= last + 2
        assert LV.replay(sub_a, f"j{upto}")[0] == []
        assert LV.replay(sub_a, "nonsense") == ([], 0, False)
        monkeypatch.setattr(LV, "REPLAY_MAX", 1)                 # too many missed: one reset, the phone reloads its lists
        assert LV.replay(sub_r, f"j{last}")[2] is True
        # colls filter: a stream that watches only products hears nothing about orders
        sub_p = LV.Sub(r, who("Ravi"), {"products"}, loop)
        assert [e for e in LV.replay(sub_p, f"j{last}")[0] if e["type"] == "row"] == []
    finally:
        loop.close()
    # the route takes Last-Event-ID: the missed order comes first, before anything new
    monkeypatch.setattr(LV, "STREAM_SECONDS", 1.0)
    monkeypatch.setattr(LV, "REPLAY_MAX", 300)
    body = c.get(f"{api}/live", headers={**hs["Asha"], "Last-Event-ID": f"j{last}"}).text
    evs = _events(body)
    assert evs[0]["type"] == "hello" and evs[1]["type"] == "row" and evs[1]["id"] == o_a["id"]


def test_late_commit_is_still_delivered_and_presence_expires(droid_env, monkeypatch):
    """Postgres can commit journal id 12 before id 11: the gap is asked for again and 11 still arrives."""
    import asyncio

    from app.appmaker import live as LV
    from app.appmaker.backup import AppJournal, ensure_table
    from app.appmaker.models import AppProject
    from app.db import session
    from app.site import webapp as W
    from sqlalchemy import select
    c, aid, api, hs, p1, ids = _shop(droid_env)
    ensure_table()
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
        top = s.scalar(select(AppJournal.id).order_by(AppJournal.id.desc()).limit(1)) or 0
    site = "app:" + aid
    loop = asyncio.new_event_loop()
    try:
        sub = LV.Sub(r, W.Who(owner=True), None, loop)
        hub = LV.Hub()
        hub.subs[site] = {sub}
        hub.cur_j = top
        row = json.dumps({"name": "Late", "phone": "9876500009", "status": "New"})
        with session() as s:                                   # id top+2 commits first
            s.add(AppJournal(id=top + 2, site_id=site, row_id="row_b", coll="orders", op="insert", owner="", after=row, created=""))
        hub.tick()
        assert top + 1 in hub.gaps and hub.cur_j == top + 2
        with session() as s:                                   # then the slower transaction, id top+1
            s.add(AppJournal(id=top + 1, site_id=site, row_id="row_a", coll="orders", op="insert", owner="", after=row, created=""))
        hub.tick()
        assert not hub.gaps
        loop.run_until_complete(asyncio.sleep(0))
        got = []
        while not sub.q.empty():
            got.append(sub.q.get_nowait())
        assert [e["id"] for e in got if e["type"] == "row"] == ["row_b", "row_a"]
        # presence: a 'here' then silence -> offline after its time
        monkeypatch.setattr(LV, "HERE_TTL", 0.2)
        LV._write_signal(site, ids["Asha"], "Asha Rao", False, "here", "s1")
        hub.tick()
        time.sleep(0.3)
        hub.tick()
        loop.run_until_complete(asyncio.sleep(0))
        pres = []
        while not sub.q.empty():
            pres.append(sub.q.get_nowait())
        assert [(e["name"], e["online"]) for e in pres if e["type"] == "presence"] == [("Asha", True), ("Asha", False)]
    finally:
        loop.close()


def test_limits_and_queue_overflow(droid_env, monkeypatch):
    import asyncio

    from app.appmaker import live as LV
    from app.appmaker.models import AppProject
    from app.db import session
    from app.site import webapp as W
    c, aid, api, hs, p1, ids = _shop(droid_env)
    monkeypatch.setattr(LV, "MAX_PER_MEMBER", 0)
    r = c.get(f"{api}/live", headers=hs["Asha"])
    assert r.status_code == 429 and "taaza" in r.json()["error"]
    with session() as s:
        app_row = s.get(AppProject, aid)
        s.expunge(app_row)
    loop = asyncio.new_event_loop()
    try:                                                      # a phone too far behind gets ONE reset, not a flood
        monkeypatch.setattr(LV, "QUEUE", 3)
        sub = LV.Sub(app_row, W.Who(owner=True), None, loop)
        for i in range(10):
            sub.put({"type": "row", "seq": i, "id": str(i)})
        loop.run_until_complete(asyncio.sleep(0))
        got = []
        while not sub.q.empty():
            got.append(sub.q.get_nowait())
        assert got == [{"type": "reset", "why": "behind"}]
    finally:
        loop.close()


def test_kits_carry_the_live_client():
    kt = (ROOT / "android/template/app/src/main/java/hoola/kit/Live.kt").read_text()
    sw = (ROOT / "ios/template/Sources/Kit/Live.swift").read_text()
    for src in (kt, sw):
        assert "/live" in src and "Last-Event-ID" in src and "/live/typing" in src and "reset" in src
    assert "fun stream(" in (ROOT / "android/template/app/src/main/java/hoola/kit/Backend.kt").read_text()
    from app.appmaker.android import gen as AG
    from app.appmaker.android import prompts as AP
    from app.appmaker.ios import gen as IG
    from app.appmaker.ios import prompts as IP
    assert "Live.start(" in AG.main_activity_kt({"app": {}})
    assert "LiveDot" in AP.__dict__.get("SYSTEM", "") + json.dumps([v for v in AP.__dict__.values() if isinstance(v, str)])
    assert "LiveDot" in IP.KIT_SHEET
    assert "Live.shared" in IG.app_swift({})
    pro = (ROOT / "android/template/app/src/main/java/hoola/kit/Pro.kt").read_text()
    assert "Live.chatTick" in pro and "TypingLine(member)" in pro and "Live.typingNow(member)" in pro
    pro_s = (ROOT / "ios/template/Sources/Kit/Pro.swift").read_text()
    assert "live.chatTick" in pro_s and "TypingLine(thread: member)" in pro_s and "live.typingNow(member)" in pro_s
    assert "live.revOf(coll)" in (ROOT / "ios/template/Sources/Kit/Accounts.swift").read_text()
    assert "Live.rev(coll)" in (ROOT / "android/template/app/src/main/java/hoola/kit/Backend.kt").read_text()
