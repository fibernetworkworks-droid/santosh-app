"""v0.854 PC CONFUSION (owner: "FIRST CHECK DOES IT CONFUSE BETWEEN HOOLA ON PC AND A USER PC" -> "GO FIX PC CONFUSION").

Before: with her PC off and Hoola's own cloud PC on, a 'mere PC' job ran on Hoola's PC by itself; file jobs with no PC
named (save an attachment / Drive file to her PC, document search) went to the LAST CONNECTED PC, which could be Hoola's;
pc_do took a Hoola PC's name; the tool guard never checked pc_do vs hoola_pc_do against the place she named.
"""
import asyncio
import types

import pytest

from app.agent.tools import ToolError

KIND = "hoola_pc"


class FakeWS:
    async def send_text(self, s):
        pass


def _hub(monkeypatch, pcs):
    from app.pc import hub as H
    h = H.Hub()
    monkeypatch.setattr(H, "hub", h)
    for dev, name, kind in pcs:
        c = H.Conn(ws=FakeWS(), device_id=dev, tenant_id="t1")
        c.info = {"name": name, "control": True, **({"kind": kind} if kind else {})}
        h.conns.setdefault("t1", {})[dev] = c
    return h


def test_no_pc_named_never_means_hoolas_pc(monkeypatch):
    h = _hub(monkeypatch, [("dev-her", "Office PC", None), ("dev-hp", "Hoola PC", KIND)])   # Hoola PC connected LAST
    assert h._pick("t1").device_id == "dev-her"
    assert h.is_online("t1") is True
    h2 = _hub(monkeypatch, [("dev-hp", "Hoola PC", KIND)])                                   # only Hoola's PC online
    assert h2._pick("t1") is None and h2.is_online("t1") is False
    assert h2.is_online("t1", kind=KIND) is True and h2._pick("t1", kind=KIND).device_id == "dev-hp"


def test_file_job_to_her_pc_refused_when_only_hoola_pc_is_on(monkeypatch):
    from app.pc.hub import PcOffline
    h = _hub(monkeypatch, [("dev-hp", "Hoola PC", KIND)])
    with pytest.raises(PcOffline):
        asyncio.run(h.call("t1", "save_file", {"name": "x.pdf"}))


def test_her_job_with_her_pc_off_is_not_moved_to_hoolas_pc(monkeypatch):
    from app.pc import operator
    _hub(monkeypatch, [("dev-hp", "Hoola PC", KIND)])
    with pytest.raises(RuntimeError, match="PC_OFFLINE_HOOLA_ON"):
        operator._choose("t1", "", "")
    _hub(monkeypatch, [])
    with pytest.raises(RuntimeError, match="^PC_OFFLINE$"):
        operator._choose("t1", "", "")


def test_pc_do_tool_says_her_pc_is_off_and_asks(monkeypatch):
    from app.pc import operator
    from app.agent import pc_tools

    async def boom(*a, **k):
        raise RuntimeError("PC_OFFLINE_HOOLA_ON")
    monkeypatch.setattr(operator, "start", boom)
    ctx = types.SimpleNamespace(tenant_id="t1", conversation_id="c1")
    with pytest.raises(ToolError, match="ASK"):
        asyncio.run(pc_tools.pc_do(ctx, "Notepad kholo", _wait=0))


def test_pc_do_refuses_a_hoola_pc_name_but_team_device_ids_still_work(monkeypatch):
    from app.pc import operator
    _hub(monkeypatch, [("dev-her", "Office PC", None), ("dev-hp", "Hoola PC 2", KIND)])
    assert operator._choose("t1", "", "office").device_id == "dev-her"
    with pytest.raises(RuntimeError, match="Hoola's own cloud PC"):
        operator._choose("t1", "", "Hoola PC 2")
    assert operator._choose("t1", "", "dev-hp").device_id == "dev-hp"          # pc_team pins by device id
    assert operator._choose("t1", KIND, "Hoola PC 2").device_id == "dev-hp"    # hoola_pc_do by name
    with pytest.raises(RuntimeError, match="PC_NOT_FOUND"):
        operator._choose("t1", KIND, "office")                                  # hoola_pc_do never on her PC


def _ctx(place):
    return types.SimpleNamespace(admit=None, place=place, conversation_id="")


def test_guard_matches_the_tool_to_the_pc_she_named():
    from app.agent import pick
    with pytest.raises(ToolError, match="hoola_pc_do"):
        pick.check("pc_do", {"task": "Notepad kholo"}, _ctx("hoolapc"))
    with pytest.raises(ToolError, match="use pc_do"):
        pick.check("hoola_pc_do", {"task": "Notepad kholo"}, _ctx("pc"))
    pick.check("pc_do", {"task": "Notepad kholo"}, _ctx("pc"))
    pick.check("hoola_pc_do", {"task": "Notepad kholo"}, _ctx("hoolapc"))


def test_pc_do_description_no_longer_offers_a_hoola_pc_name():
    from app.agent import pc_tools
    spec = next(t for t in pc_tools.PC_TOOLS if t["name"] == "pc_do")
    d = spec["input_schema"]["properties"]["pc"]["description"]
    assert "Hoola PC 2" not in d and "hoola_pc_do" in d
