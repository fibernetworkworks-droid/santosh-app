"""v0.890 HOOLA COMPUTER - one section, two computers (Hoola PC + her PC), each with its OWN chats that never mix with
her Hoola chats, a turn in a computer chat always works on that computer, her 'Use my PC' switch, one voice call."""
import types

from fastapi.testclient import TestClient


def _c(env):
    from app.main import app
    return TestClient(app)


def test_computer_chats_stay_out_of_her_chats(env):
    c = _c(env)
    home = c.post("/api/conversations").json()["id"]
    hid = c.post("/api/computer/hoola/chats").json()["id"]
    assert c.post("/api/computer/hoola/chats").json() == {"id": hid, "reused": True}   # an empty one is reused
    ids = [x["id"] for x in c.get("/api/conversations").json()["conversations"]]
    assert home in ids and hid not in ids                    # never in her normal chat list
    rows = c.get("/api/computer/hoola/chats").json()["chats"]
    assert [r["id"] for r in rows] == [hid]
    assert c.get("/api/computer/mine/chats").json()["chats"] == []   # the two computers never share chats
    from app import convs
    convs.mark("default", hid, "message")
    assert convs.current("default") != hid                   # a computer chat is never 'the chat she is in'


def test_turn_in_a_computer_chat_always_works_on_that_computer(env):
    c = _c(env)
    hid = c.post("/api/computer/hoola/chats").json()["id"]
    c.put("/api/computer/mine", json={"on": True})
    mid = c.post("/api/computer/mine/chats").json()["id"]
    from app.agent import where
    assert where.remember(hid, "Chrome kholo aur mere PC pe aadhaar download karo") == "hoolapc"
    assert "HOOLA PC chat" in where.note("hoolapc", hid)
    assert where.remember(mid, "Hoola ke apne PC pe karo") == "pc"
    assert "YOUR PC chat" in where.note("pc", mid)
    assert where._asked(hid, "hoolapc") and where._asked(mid, "pc")   # pick.py reads these as her own choice
    home = c.post("/api/conversations").json()["id"]
    assert where.remember(home, "kuch bhi likho") == ""      # an ordinary chat is unchanged


def test_use_my_pc_switch_and_pairing(env):
    c = _c(env)
    st = c.get("/api/computer").json()
    assert st["mine"]["on"] is False and st["mine"]["download"].endswith("SantoshDesktop.exe")
    assert c.post("/api/computer/mine/chats").status_code == 409   # off = no Your PC chats yet
    r = c.post("/api/computer/mine/pair").json()
    assert len(r["code"]) == 6 and r["code"].isdigit() and r["download"]
    assert c.get("/api/computer").json()["mine"]["on"] is True
    assert c.put("/api/computer/mine", json={"on": False}).json() == {"on": False}
    assert c.get("/api/computer/nope/chats").status_code == 404


def test_workspace_shows_the_task_a_call_started(env, monkeypatch):
    c = _c(env)
    from app.pc import operator as pcop
    from app import callconv
    done = types.SimpleNamespace(done=lambda: False)
    op = pcop.Op(id="pcop_x1", tenant="default", conv="conv_call1", task="Aadhaar download", kind="hoola_pc")
    op.task_obj = done
    monkeypatch.setitem(pcop.OPS, op.id, op)
    monkeypatch.setattr(callconv, "is_call", lambda conv: conv == "conv_call1")
    run = c.get("/api/computer").json()["hoola"]["running"]
    assert run["session_id"] == "pcop_x1" and run["from"] == "call" and run["task"] == "Aadhaar download"
    assert c.get("/api/computer").json()["mine"]["running"] is None   # a Hoola PC task never shows under Your PC


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.905.0")
