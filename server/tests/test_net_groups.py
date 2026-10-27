"""Hoola Network v0.31: Mandali (groups of avatars) with the admin's avatar as hub."""
import pytest

from tests.test_net import _connect, ev


def _three():
    net = _connect()                                     # default (Meghana) <-> kunal (Kunal)
    from app.avatar import service as av
    from app.db import Profile, session
    from app.net import identity as idn
    with session() as s:
        s.merge(Profile(tenant_id="swati", name="Swati"))
    av.save("swati", name="Sakhi", gender="f", rules={"quiet": {"on": False}})
    idn.ensure("swati")
    idn.set_handle("swati", "swati.sales")
    net.connect("default", "@swati.sales", relation="team")
    net.answer_connect("swati", net.connections("swati", "incoming")[0]["id"], "accept")
    return net


def test_group_invite_join_post_and_mute(env):
    net = _three()
    from app.net import groups as grp
    g = grp.create("default", "FNW Field", "🛠", ["Kunal", "@swati.sales"])
    assert len(g["invited"]) == 2 and not g["failed"]
    inv = ev("kunal", "hoola_group")[-1]
    assert inv["event"] == "invite" and inv["name"] == "FNW Field"
    grp.answer_invite("kunal", inv["gid"], "accept")
    grp.answer_invite("swati", g["gid"], "accept")
    d = grp.detail("default", g["gid"])
    assert {m["label"] for m in d["members"]} == {"Meghana ka Santosh", "Kunal ki Meera", "Swati ki Sakhi"}
    assert len(grp.detail("kunal", g["gid"])["members"]) == 3            # members learn the list from the hub
    grp.post("kunal", g["gid"], "message", "GPON drop fix: splitter badla, sab theek")
    assert grp.detail("swati", g["gid"])["posts"][-1]["author"] == "Kunal ki Meera"
    assert grp.detail("kunal", g["gid"])["posts"][-1]["mine"] is True
    assert ev("swati", "hoola_group_post")[-1]["quiet"] is True           # default mute = mentions: no push
    grp.post("default", g["gid"], "message", "Sakhi, kal Goa site ka report bhejna")
    assert ev("swati", "hoola_group_post")[-1]["mention"] is True
    grp.set_mute("swati", g["gid"], "digest")
    n = len(ev("swati", "hoola_group_post"))
    grp.post("kunal", g["gid"], "message", "lunch break")
    assert len(ev("swati", "hoola_group_post")) == n                     # digest only: kept, not shown
    assert len(grp.detail("swati", g["gid"])["posts"]) == 3


def test_tasks_files_and_safety(env, monkeypatch):
    net = _three()
    from app.net import groups as grp
    g = grp.create("default", "FNW Field", members=["Kunal", "@swati.sales"])
    grp.answer_invite("kunal", g["gid"], "accept")
    grp.answer_invite("swati", g["gid"], "accept")
    grp.post("default", g["gid"], "task", "Akola OLT 7 ka backup lo", title="OLT backup", assign_to="Kunal", due="kal")
    t = ev("kunal", "hoola_group_post")[-1]
    assert t["for_me"] and t["kind"] == "task" and t["quiet"] is False
    grp.task_answer("kunal", t["id"], "done")
    assert grp.detail("default", g["gid"])["posts"][-1]["task_status"] == "done"
    assert "poora kiya" in ev("swati", "hoola_group_post")[-1]["text"]
    with pytest.raises(net.NetError, match="aapko nahi"):
        grp.task_answer("swati", grp.detail("swati", g["gid"])["posts"][-1]["id"], "done")
    with pytest.raises(net.NetError, match="OTP"):
        grp.post("kunal", g["gid"], "message", "OTP 482913 hai")
    from app import artifacts

    async def fake(system, prompt, max_tokens=300):
        return "summary"
    monkeypatch.setattr(artifacts, "_llm", fake)
    from app.mailbox import service as ms
    fid = ms.store_bytes("kunal", "site-photo-report.txt", b"Goa site report: 12 ONT installed, 2 pending." * 3, "mail").id
    grp.post("kunal", g["gid"], "file", "Report", file_id=fid)
    fp = [p for p in grp.detail("swati", g["gid"])["posts"] if p["kind"] == "file"][-1]
    assert fp["body"]["name"] == "site-photo-report.txt" and fp["body"]["scan"]["verdict"] == "clear"
    pf = grp.take_file("swati", fp["id"])
    assert pf["name"] == "site-photo-report.txt"
    dg = grp.digest("default", g["gid"])
    assert dg["posts"] >= 2
    grp.leave("swati", g["gid"])
    assert {m["label"] for m in grp.detail("default", g["gid"])["members"]} == {"Meghana ka Santosh", "Kunal ki Meera"}


def test_only_connections_can_be_invited(env):
    net = _connect()
    from app.net import groups as grp
    from app.net import identity as idn
    idn.ensure("stranger")
    idn.set_handle("stranger", "random.person")
    g = grp.create("kunal", "Ghar")
    with pytest.raises(net.NetError, match="juda nahi"):
        grp.invite("kunal", g["gid"], "@random.person")
    with pytest.raises(net.NetError, match="nahi mila|admin"):
        grp.invite("default", g["gid"], "Kunal")
