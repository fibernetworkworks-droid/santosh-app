"""Santosh Artifacts: build, versions, sandboxed serving, saved data, share links, ask, isolation, voice/background."""
import asyncio
import re

import pytest
from fastapi.testclient import TestClient

PAGE = """TITLE: EMI Calculator
SUMMARY: Loan EMI with ₹ formatting
<!doctype html><html><head><title>EMI</title></head><body><h1>EMI {v}</h1>
<script>santosh.storage.get('loan').then(function(v){{document.body.dataset.loan=v}})</script>
<p>{pad}</p></body></html>"""


@pytest.fixture
def art(env, monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("SECRET_KEY", "artifact-test-secret-0123456789")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://santosh.example.in")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import accounts, artifacts, main
    from app.db import Conversation, User, session
    calls = []

    async def fake_llm(system, prompt, max_tokens=16000):
        calls.append((system, prompt))
        if "inside the user's page" in system:
            return "Rs 25,000 ka EMI 12 mahine mein lagbhag Rs 2,220."
        if "BROKEN" in prompt:
            raise RuntimeError("model down")
        n = 2 if "CURRENT PAGE" in prompt else 1
        return PAGE.format(v=n, pad="x" * 300)
    monkeypatch.setattr(artifacts, "_llm", fake_llm)
    with session() as s:
        s.add_all([User(id="usr_a", email="a@gmail.com"), User(id="usr_b", email="b@gmail.com")])
    ta, tb = accounts.issue_session("usr_a"), accounts.issue_session("usr_b")
    tenant_a = accounts.tenant_of_user("usr_a")
    with session() as s:
        c = Conversation(tenant_id=tenant_a)
        s.add(c)
        s.flush()
        conv = c.id
    yield {"c": TestClient(main.app), "ha": {"Authorization": f"Bearer {ta}"}, "hb": {"Authorization": f"Bearer {tb}"},
           "tenant": tenant_a, "conv": conv, "calls": calls, "mod": artifacts}
    get_settings.cache_clear()


def _events(conv, kind):
    from sqlalchemy import select
    from app.db import Event, session
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == kind)).all()]


def _tool(art, **args):
    from app.agent.artifact_tools import artifact_make
    from app.agent.tools import Ctx
    return asyncio.run(artifact_make(Ctx(art["tenant"], art["conv"]), **args))


def test_build_view_and_sandbox(art):
    r = _tool(art, request="EMI calculator for a 5 lakh loan, Hinglish labels")
    assert r["status"] == "ready" and r["title"] == "EMI Calculator" and r["version"] == 1
    evs = _events(art["conv"], "artifact")
    assert [e["status"] for e in evs][:1] == ["building"] and evs[-1]["status"] == "ready"
    c, ha = art["c"], art["ha"]
    url = c.get(f"/api/artifacts/{r['id']}/view", headers=ha).json()["url"]
    assert url.startswith("https://santosh.example.in/a/")
    page = c.get(url.replace("https://santosh.example.in", ""))
    assert page.status_code == 200 and "EMI 1" in page.text
    csp = page.headers["content-security-policy"]
    assert csp.startswith("sandbox allow-scripts") and "connect-src 'none'" in csp and "allow-same-origin" not in csp
    assert "window.santosh=" in page.text and page.text.index("window.santosh=") < page.text.index("<h1>")
    bad = re.sub(r"sig=\w+", "sig=deadbeef", url.replace("https://santosh.example.in", ""))
    assert c.get(bad).status_code == 403


def test_revise_keeps_saved_data_and_versions(art):
    c, ha = art["c"], art["ha"]
    r = _tool(art, request="EMI calculator")
    assert c.put(f"/api/artifacts/{r['id']}/state", json={"key": "loan", "value": {"amt": 500000}}, headers=ha).json()["ok"]
    r2 = _tool(art, request="add GST row", artifact_id=r["id"])
    assert r2["version"] == 2
    assert "CURRENT PAGE" in art["calls"][-1][1] and "EMI 1" in art["calls"][-1][1]
    d = c.get(f"/api/artifacts/{r['id']}", headers=ha).json()
    assert [v["version"] for v in d["versions"]] == [2, 1] and d["versions"][0]["note"] == "add GST row"
    assert c.get(f"/api/artifacts/{r['id']}/state", headers=ha).json()["state"] == {"loan": {"amt": 500000}}
    url = c.get(f"/api/artifacts/{r['id']}/view", headers=ha).json()["url"].replace("https://santosh.example.in", "")
    assert '"amt": 500000' in c.get(url).text      # owner's page starts with saved data
    old = c.get(f"/api/artifacts/{r['id']}/view?version=1", headers=ha).json()["url"].replace("https://santosh.example.in", "")
    assert "EMI 1" in c.get(old).text


def test_share_link_is_public_but_never_includes_saved_data(art):
    c, ha = art["c"], art["ha"]
    r = _tool(art, request="milk hisaab tracker")
    c.put(f"/api/artifacts/{r['id']}/state", json={"key": "entries", "value": ["secret-entry"]}, headers=ha)
    s = c.post(f"/api/artifacts/{r['id']}/share", json={"on": True}, headers=ha).json()
    assert s["shared"] and s["share_url"].startswith("https://santosh.example.in/s/")
    pub = c.get(s["share_url"].replace("https://santosh.example.in", ""))
    assert pub.status_code == 200 and "EMI 1" in pub.text and "secret-entry" not in pub.text
    assert "noindex" in pub.headers["x-robots-tag"]
    c.post(f"/api/artifacts/{r['id']}/share", json={"on": False}, headers=ha)
    assert c.get(s["share_url"].replace("https://santosh.example.in", "")).status_code == 404


def test_other_people_cant_touch_it(art):
    c, hb = art["c"], art["hb"]
    r = _tool(art, request="expense tracker")
    for method, path, body in [("get", "", None), ("get", "/view", None), ("get", "/state", None),
                               ("put", "/state", {"key": "x", "value": 1}), ("post", "/share", {"on": True}),
                               ("post", "/ask", {"question": "hi"}), ("post", "/revise", {"request": "make it red"}),
                               ("delete", "", None)]:
        kw = {"json": body} if body is not None else {}
        assert getattr(c, method)(f"/api/artifacts/{r['id']}{path}", headers=hb, **kw).status_code == 404, path
    assert c.get("/api/artifacts", headers=hb).json()["artifacts"] == []


def test_ask_state_limits_and_delete(art):
    c, ha = art["c"], art["ha"]
    r = _tool(art, request="loan helper")
    assert "EMI" in c.post(f"/api/artifacts/{r['id']}/ask", json={"question": "25000 ka EMI?"}, headers=ha).json()["answer"]
    big = {"key": "k", "value": "x" * 70000}
    assert c.put(f"/api/artifacts/{r['id']}/state", json=big, headers=ha).status_code == 400
    c.put(f"/api/artifacts/{r['id']}/state", json={"key": "k", "value": 1}, headers=ha)
    c.put(f"/api/artifacts/{r['id']}/state", json={"key": "k", "value": None}, headers=ha)
    assert c.get(f"/api/artifacts/{r['id']}/state", headers=ha).json()["state"] == {}
    assert c.delete(f"/api/artifacts/{r['id']}", headers=ha).json()["ok"]
    assert c.get(f"/api/artifacts/{r['id']}", headers=ha).status_code == 404


def test_voice_builds_in_background_and_failures_are_reported(art):
    async def go():
        from app.agent.artifact_tools import artifact_make
        from app.agent.tools import Ctx
        ctx = Ctx(art["tenant"], art["conv"])
        r = await artifact_make(ctx, request="quiz on Indian states", _wait=0)
        assert r["status"] == "building"
        for _ in range(50):
            await asyncio.sleep(0.02)
            if art["mod"].get(art["tenant"], r["id"]).status == "ready":
                break
        bad = await artifact_make(ctx, request="BROKEN page please")
        return r, bad
    r, bad = asyncio.run(go())
    assert art["mod"].get(art["tenant"], r["id"]).status == "ready"
    assert bad["status"] == "failed" and "nahi ban paya" in bad["error"]


def test_parse_handles_fences_and_missing_title(art):
    t, s, p = art["mod"].parse("```html\n<!doctype html><html><head><title>Diwali Poster</title></head><body>"
                               + "y" * 300 + "</body></html>\n```")
    assert t == "Diwali Poster" and p.endswith("</html>")
    with pytest.raises(ValueError):
        art["mod"].parse("sorry, I can't")
