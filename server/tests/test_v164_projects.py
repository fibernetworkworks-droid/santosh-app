"""v0.164 Projects, "Kaam ke folder" (CHAT_PROJECTS): create / rename / notes / delete, files kept with the project (small
ones go into the prompt, big ones are searched through Gyaan), a chat in a project gets its instructions + notes + files
in the system prompt (and a chat outside never does), new chat in a project, move chats in / out, list filter."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from tests.test_v161_stream import KEY

H = {"Authorization": f"Bearer {KEY}"}


class SystemSpy:
    """A brain that answers 'ok' and remembers each system prompt it was given."""

    def __init__(self):
        self.systems = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        sys_ = kw.get("system") or ""
        if isinstance(sys_, list):   # v0.190 cache.system_prompt wraps the system prompt in cached text blocks
            sys_ = "".join(b.get("text", "") for b in sys_ if isinstance(b, dict))
        self.systems.append(sys_)
        return SimpleNamespace(content=[{"type": "text", "text": "ok"}], stop_reason="end_turn")


@pytest.fixture
def pj(env, monkeypatch, tmp_path):
    for k, v in (("CHAT_PROJECTS", "true"), ("CHAT_SESSIONS", "true"), ("API_KEY", KEY),
                 ("PROJECTS_DIR", str(tmp_path / "projects"))):
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    with TestClient(main.app) as c:
        yield c


def test_projects_crud_and_chats(pj):
    c = pj
    assert c.get("/api/console/config").json()["projects"] is True
    assert c.post("/api/projects", json={"name": "   "}, headers=H).status_code == 400
    p = c.post("/api/projects", json={"name": "  Shaadi   ka kaam ", "instructions": "Budget 5 lakh", "emoji": "💍"}, headers=H).json()
    assert p["name"] == "Shaadi ka kaam" and p["emoji"] == "💍" and p["chats"] == 0 and p["files"] == 0
    pid = p["id"]
    q = c.post("/api/projects", json={"name": "GST"}, headers=H).json()["id"]
    upd = c.patch(f"/api/projects/{pid}", json={"memory": "Venue: Pune, 12 Dec", "name": "Shaadi"}, headers=H).json()
    assert upd["memory"] == "Venue: Pune, 12 Dec" and upd["instructions"] == "Budget 5 lakh" and upd["name"] == "Shaadi"
    # a new chat in the project, another moved in, then out
    a = c.post(f"/api/conversations?project_id={pid}", headers=H).json()["id"]
    b = c.post("/api/conversations", headers=H).json()["id"]
    assert c.post("/api/conversations?project_id=prj_nope", headers=H).status_code == 404
    assert c.patch(f"/api/conversations/{b}", json={"project_id": pid}, headers=H).json()["project_id"] == pid
    assert c.patch(f"/api/conversations/{b}", json={"project_id": "prj_nope"}, headers=H).status_code == 404
    lst = c.get(f"/api/console/conversations?project={pid}", headers=H).json()["conversations"]
    assert {x["id"] for x in lst} == {a, b} and all(x["project_id"] == pid for x in lst)
    assert c.patch(f"/api/conversations/{b}", json={"project_id": None}, headers=H).json()["project_id"] is None
    assert [x["id"] for x in c.get(f"/api/console/conversations?project={pid}", headers=H).json()["conversations"]] == [a]
    projects = {x["id"]: x for x in c.get("/api/projects", headers=H).json()["projects"]}
    assert projects[pid]["chats"] == 1 and q in projects
    # rename + pin still work together with the project move
    r = c.patch(f"/api/conversations/{a}", json={"title": "Caterer", "pinned": True}, headers=H).json()
    assert r["title"] == "Caterer" and r["pinned"] is True
    # soft delete: the chat stays, it just leaves the project
    assert c.delete(f"/api/projects/{pid}", headers=H).json()["deleted"] is True
    assert c.get(f"/api/projects/{pid}", headers=H).status_code == 404
    from app.db import Conversation, session
    with session() as s:
        assert s.get(Conversation, a).project_id is None and not s.get(Conversation, a).deleted


def test_files_and_the_prompt_of_a_project_chat(pj, monkeypatch):
    c = pj
    pid = c.post("/api/projects", json={"name": "Dukaan", "instructions": "Hamesha GST alag dikhao."}, headers=H).json()["id"]
    c.patch(f"/api/projects/{pid}", json={"memory": "Supplier: Gupta Traders"}, headers=H)
    small = c.post(f"/api/projects/{pid}/files", files={"file": ("rate.txt", "Atta ka rate 42 rupaye kilo".encode())}, headers=H)
    assert small.status_code == 201 and small.json()["chars"] > 10
    big_text = ("Stock register line. " * 1200).encode()
    big = c.post(f"/api/projects/{pid}/files", files={"file": ("register.txt", big_text)}, headers=H).json()
    assert big["chars"] > 16000
    files = c.get(f"/api/projects/{pid}", headers=H).json()["file_list"]
    assert [f["name"] for f in files] == ["rate.txt", "register.txt"]
    from app.config import get_settings
    from pathlib import Path
    assert len(list((Path(get_settings().projects_dir) / pid).iterdir())) == 2          # kept on disk with the project

    from app.agent import run_turn, set_client
    spy = SystemSpy()
    set_client(spy)
    inside = c.post(f"/api/conversations?project_id={pid}", headers=H).json()["id"]
    outside = c.post("/api/conversations", headers=H).json()["id"]
    asyncio.run(run_turn(inside, "atta ka rate?", tenant_id="default"))
    asyncio.run(run_turn(outside, "atta ka rate?", tenant_id="default"))
    sys_in, sys_out = [x for x in spy.systems if not x.startswith("Write a title")]   # (auto titles ask too)
    assert 'project "Dukaan"' in sys_in and "Hamesha GST alag dikhao." in sys_in and "Supplier: Gupta Traders" in sys_in
    assert "Atta ka rate 42 rupaye kilo" in sys_in                                        # small file in full
    assert "register.txt" in sys_in and "gyaan_khojo" in sys_in and "Stock register line. Stock" not in sys_in
    assert "PROJECT" not in sys_out and "Gupta Traders" not in sys_out                    # another chat: nothing
    # a file removed is gone from the prompt and the disk
    assert c.delete(f"/api/projects/{pid}/files/{small.json()['id']}", headers=H).json()["removed"] is True
    from app import projects
    assert "Atta ka rate" not in projects.prompt_block(inside)
    assert len(list((Path(get_settings().projects_dir) / pid).iterdir())) == 1
    # switch off: no project block, endpoints gone
    monkeypatch.setenv("CHAT_PROJECTS", "false")
    monkeypatch.setenv("CONSOLE_V2", "false")   # v0.170 CONSOLE_V2 (default on) turns projects on by itself
    get_settings.cache_clear()
    assert projects.prompt_block(inside) == ""
    assert c.get("/api/projects", headers=H).status_code == 404
    assert c.post(f"/api/conversations?project_id={pid}", headers=H).status_code == 404


def test_project_limits_and_safety(pj):
    c = pj
    pid = c.post("/api/projects", json={"name": "Limits"}, headers=H).json()["id"]
    assert c.post(f"/api/projects/{pid}/files", files={"file": ("empty.txt", b"")}, headers=H).status_code == 400
    other = "prj_" + "0" * 12
    assert c.post(f"/api/projects/{other}/files", files={"file": ("a.txt", b"x")}, headers=H).status_code == 404
    from app.db import session
    from app.projects import Project
    with session() as s:                                               # another owner's project is not hers
        s.get(Project, pid).tenant_id = "someone_else"
    assert c.get(f"/api/projects/{pid}", headers=H).status_code == 404
    assert c.patch(f"/api/projects/{pid}", json={"name": "x"}, headers=H).status_code == 404
