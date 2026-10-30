"""v0.194 Sidebar sessions: every kaam folder becomes a collapsible section in the console chat list itself.
The owner asked for "a session for every work" — one session for app design, another for research. The pieces:
the session header (chevron collapse + localStorage state, name opens the session page, hover "+" starts a chat
inside, count and a live dot while collapsed), drag a chat row onto a header to move it there and onto "Baaki
chats" to take it out, the slim sessions box (label + "+ Naya"), the session chip on search results, and the
server surface that was already there (projects CRUD + project_id on create/assign) now exercised end to end."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v161_stream import KEY

H = {"Authorization": f"Bearer {KEY}"}
CONSOLE = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


@pytest.fixture
def cs(env, monkeypatch):
    monkeypatch.setenv("CHAT_SESSIONS", "true")
    monkeypatch.setenv("CHAT_PROJECTS", "true")
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    with TestClient(main.app) as c:
        yield c


def _read(name):
    return (CONSOLE / name).read_text()


# ---------- console files carry the phase ----------

def test_chatlist_draws_session_sections():
    js = _read("chatlist.js")
    assert 'data-sec' in js and 'secHead(' in js                        # section headers exist
    assert 'hoola.sessions.v1' in js                                    # collapse state persists
    assert 'Other chats' in js and 'data-rest' in js                    # the unassigned drop zone (v0.221 English chrome)
    assert 'html += (drag ?' in js                                      # the zone is ALWAYS there once sessions exist:
                                                                        # dragging the last chat out always has a target
    assert 'draggable="true"' in js and 'dragstart' in js and "'drop'" in js   # drag a chat onto a header
    assert 'newChatIn' in js and 'openSection' in js                    # the + and name affordances
    assert 'srsec' in js                                                # search result session chip


def test_sessions_box_slim_and_projects_js_speaks_sessions():
    js = _read("projects.js")
    assert '<span>Sessions</span>' in js                                # slim label
    assert 'pjrow' not in js                                            # no duplicate folder rows in the sidebar
    assert 'New session name' in js and 'App design' in js              # create prompt (v0.221 English chrome)
    assert 'New chat in this session' in js and 'Delete session' in js  # session page copy (v0.221 English chrome)
    assert 'ctx.reloadChats?.()' in js                                  # the new session shows up at once


def test_v2_wires_the_session_context():
    js = _read("v2.js")
    assert 'get openSection() { return PJ ? pid => PJ.open(pid) : null; }' in js
    assert 'newChatIn: async pid' in js and 'project_id=' in js


def test_css_styles_the_sessions():
    css = _read("v2.css")
    for sel in ('.sgh', '.sgh .sgn', '.sgb', '.sgh.dropok', '.rcw.dragging', '.srsec', '.sgacts'):
        assert sel in css, sel
    assert '.pjrow' not in css                                          # pruned with its last user


def test_cache_busts_follow_the_version():
    html = _read("v2.html")
    stamps = re.findall(r'\?v=([0-9.]+)', html)
    app = [s for s in stamps if s != "1.4.4"]                           # vendor qrcode keeps its own version
    from app.main import APP_VERSION
    # v0.221 R1: ONE stylesheet + 10 scripts, every one on the release version (no hand tags like &web=)
    assert len(app) == 16 and set(app) == {APP_VERSION}   # v0.243 + theme.js, v0.248 + pdfview.js, v0.259 + studio.js, v0.285 + menu.js, v0.279 + attach.js, stamps
    assert "&web=" not in html and "?web=" not in html


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.301.0"    # conscious-bump guard: moves with every release (bump with pubspec)


def _wrote(*convs):   # v0.236 the console lists a chat only once she wrote in it
    from app.db import Message, session
    with session() as s:
        for cv in convs:
            s.add(Message(conversation_id=cv, role="user", content="hi", display="hi"))


# ---------- the server surface, end to end ----------

def test_session_lifecycle_create_chat_move(cs):
    c = cs
    p = c.post("/api/projects", json={"name": "App design"}, headers=H)
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    # a chat born inside the session (the "+" on the header does exactly this)
    conv = c.post("/api/conversations", params={"project_id": pid}, headers=H).json()["id"]
    _wrote(conv)
    rows = c.get("/api/console/conversations", headers=H).json()["conversations"]
    row = next(r for r in rows if r["id"] == conv)
    assert row["project_id"] == pid                                     # the sidebar can section it
    # rename the session, chat stays
    assert c.patch(f"/api/projects/{pid}", json={"name": "App design v2"}, headers=H).status_code == 200
    assert c.get("/api/projects", headers=H).json()["projects"][0]["name"] == "App design v2"
    # move out ("Baaki chats") and back in via the same PATCH the drag uses
    assert c.patch(f"/api/conversations/{conv}", json={"project_id": ""}, headers=H).status_code == 200
    row = next(r for r in c.get("/api/console/conversations", headers=H).json()["conversations"] if r["id"] == conv)
    assert not row["project_id"]
    assert c.patch(f"/api/conversations/{conv}", json={"project_id": pid}, headers=H).status_code == 200
    row = next(r for r in c.get("/api/console/conversations", headers=H).json()["conversations"] if r["id"] == conv)
    assert row["project_id"] == pid
    # deleting the session leaves the chat alive, outside
    assert c.delete(f"/api/projects/{pid}", headers=H).status_code == 200
    rows = c.get("/api/console/conversations", headers=H).json()["conversations"]
    assert next(r for r in rows if r["id"] == conv)["project_id"] in (None, "")


def test_chat_created_for_unknown_session_is_refused(cs):
    c = cs
    r = c.post("/api/conversations", params={"project_id": "nope123"}, headers=H)
    assert r.status_code == 404
