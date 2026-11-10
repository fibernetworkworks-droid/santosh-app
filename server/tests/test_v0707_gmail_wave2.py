"""v0.707 GMAIL WAVE 2: the audit's open items (docs/tests/GMAIL_AUDIT_2026-11-08.md)."""
from __future__ import annotations

import json

import httpx
import pytest

from app.mailbox import gmail
from app.mailbox.base import MailError, NotConnected


def _box(handler):
    return gmail.GmailBox("k", "me@x.com", lambda fresh: "tok", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_settings_google_never_grants_say_so_not_reconnect():
    def h(req):
        return httpx.Response(403, text='{"error":{"message":"Request had insufficient authentication scopes."}}')
    with pytest.raises(MailError) as e:
        _box(h)._req("POST", "/settings/forwardingAddresses", json={})
    assert "Workspace" in str(e.value) and "dobara jodiye" not in str(e.value)
    with pytest.raises(MailError) as e:
        _box(h)._req("DELETE", "/messages/abc")
    assert "Trash" in str(e.value)
    with pytest.raises(MailError) as e:
        _box(h)._req("GET", "/messages")
    assert "dobara jodiye" in str(e.value)          # an ordinary missing scope still says reconnect


def test_expired_login_is_not_connected(monkeypatch):
    from app.mailbox import accounts as A

    class C:
        def post(self, url, data=None):
            return httpx.Response(400, text='{"error":"invalid_grant"}')
    monkeypatch.setattr(A, "_http", C())
    with pytest.raises(NotConnected) as e:
        A._post("https://x", {})
    assert "dobara jodiye" in str(e.value) and "invalid_grant" not in str(e.value)


def test_ids_for_pages_and_caps():
    pages = {None: (["a", "b"], "p2"), "p2": (["c"], None)}

    def h(req):
        ids, nxt = pages[req.url.params.get("pageToken")]
        body = {"messages": [{"id": i} for i in ids]}
        if nxt:
            body["nextPageToken"] = nxt
        return httpx.Response(200, json=body)
    ids, more = _box(h).ids_for("promotions")
    assert ids == ["a", "b", "c"] and more is False


def test_bulk_act_by_filter_in_one_call(env, monkeypatch):
    from app.mailbox import service as ms
    done = {}

    class B:
        kind, address, key = "gmail", "me@x.com", "k"

        def ids_for(self, folder, search, cap):
            done["q"] = (folder, search)
            return ["m1", "m2", "m3"], False

        def archive(self, ids):
            done["archived"] = ids
    monkeypatch.setattr(ms, "get_box", lambda t, a=None: B())
    out = ms.act_query("default", "archive", "promotions")
    assert out["count"] == 3 and done["archived"] == ["m1", "m2", "m3"] and done["q"] == ("promotions", None)
    with pytest.raises(MailError):
        ms.act_query("default", "trash", "promotions")


def test_batch_modify_chunks_at_1000():
    n = {"c": 0}

    def h(req):
        n["c"] += 1
        assert len(json.loads(req.content)["ids"]) <= 1000
        return httpx.Response(200, json={})
    _box(h)._modify([str(i) for i in range(2500)], remove=["INBOX"])
    assert n["c"] == 3


def test_tool_wiring():
    from app.agent import email_tools as et
    sch = next(t for t in et.EMAIL_TOOLS if t["name"] == "email_action")
    assert sch["input_schema"]["required"] == ["action"] and "source_folder" in sch["input_schema"]["properties"]
    src = open("app/agent/email_tools.py").read()
    assert 'startswith("eml_")' in src and "many_recipients" in src and "ms.thread, ctx.tenant_id, str(id), 15, 1500" in src


def test_prune_clears_sooner_for_glm(monkeypatch):
    # v0.724 GLM clears at 30k (was 12k), still sooner than Claude (40k): three old 12k results pass it
    from app.agent import prune
    monkeypatch.setattr(prune, "_glm_on", lambda: True)
    hist = []
    for i in range(6):
        hist.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"t{i}", "name": "email_check", "input": {}}]})
        hist.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": "x" * 12000}]})
    out = prune.clear_old(hist)
    assert len(str(out)) < len(str(hist)) * 0.7


def test_glm_compacts_earlier(monkeypatch):
    from app.agent import context
    from app import glmdoor
    monkeypatch.setattr(glmdoor, "active", lambda: True)
    monkeypatch.setattr(context, "FIXED_SEEN", {"claude": 30000})
    # v0.724 the GLM cap (pinned 40k in conftest) is conversation room ON TOP of the system prompt + tools
    assert abs(context.budget("claude") - (40000 + 30000)) <= 1 and context.window("claude") < 200000
