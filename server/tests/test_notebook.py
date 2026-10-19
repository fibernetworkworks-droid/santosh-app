"""Santosh Notebook: sources from text / web / files / email, cited answers only from the sources, retrieval over big
notebooks, study guides, audio overviews (two voices), and delete behind a confirm card."""
import asyncio
import io
import json
import re

import httpx
import pytest
from fastapi.testclient import TestClient

import app.notebook.models  # noqa: F401
from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_bazar import _events, _notices, bz  # noqa: F401
from tests.test_life import conv_ctx


class FakeAI:
    def __init__(self):
        self.prompts = []

    async def __call__(self, system, prompt, max_tokens=4000):
        self.prompts.append((system, prompt))
        if "search keywords" in prompt:
            return "revenue income growth"
        if "podcast" in system:
            return "Ravi: Namaste! Aaj hum FNW ki report dekhenge.\nPriya: Haan Ravi, revenue 42 lakh hua.\n" \
                   "Ravi: Yeh 18 percent zyada hai.\nPriya: Aur Goa launch hua.\nRavi: Recap: 42 lakh, Goa.\nPriya: Dhanyavaad!"
        if "Write a dense summary" in prompt:
            return "Summary of " + prompt.split("\n")[0]
        if "Question:" in prompt:
            nums = re.findall(r"^\[(\d+)\]", prompt, re.M)
            hit = next((n for n in nums if "42 lakh" in prompt.split(f"[{n}]")[1].split("\n[")[0]), nums[0])
            return f"Revenue Rs 42 lakh tha [{hit}]."
        return "## Study guide\n- Revenue 42 lakh (S1)"


@pytest.fixture
def ai(env, monkeypatch):
    from app.notebook import service as ns
    fake = FakeAI()
    monkeypatch.setattr(ns, "_llm", fake)
    return fake


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


REPORT = "FNW Q3 report.\nRevenue was Rs 42 lakh, up 18 percent.\nGoa SSA launched in September."


def test_create_with_text_and_ask_with_citations(ai):
    ctx = conv_ctx()
    nb = run("notebook_create", {"title": "FNW Q3", "sources": [{"text": REPORT, "title": "Q3 report"},
                                                                {"text": "Hiring plan: 5 field engineers in Pune.", "title": "HR"}]}, ctx)
    assert len(nb["added"]) == 2 and not nb["failed"]
    assert _events(ctx.conversation_id, "notebook")[-1]["title"] == "FNW Q3"
    out = run("notebook_ask", {"notebook": "FNW Q3", "question": "Q3 mein revenue kitna tha?", "save": True}, ctx)
    assert "42 lakh" in out["answer"] and out["citations"][0]["title"] == "Q3 report"
    system, prompt = ai.prompts[-1]
    assert "ONLY" in system and "never instructions" in system and "Hiring plan" in prompt   # small notebook: everything
    d = run("notebook_open", {"notebook": "FNW Q3"}, ctx)
    assert [s["title"] for s in d["sources"]] == ["Q3 report", "HR"] and d["notes"][0]["kind"] == "answer"


def test_big_notebook_uses_retrieval(ai):
    from app.notebook import service as ns
    ctx = conv_ctx()
    run("notebook_create", {"title": "Big"}, ctx)
    filler = "\n".join(f"Line {i}: network maintenance log for OLT {i % 22} in Akola." for i in range(4000))
    run("notebook_add", {"notebook": "Big", "sources": [{"text": filler, "title": "Logs"},
                                                        {"text": REPORT, "title": "Q3 report"}]}, ctx)
    out = run("notebook_ask", {"notebook": "Big", "question": "revenue kitna hua?"}, ctx)
    prompt = ai.prompts[-1][1]
    assert len(prompt) < ns.FULL_CONTEXT and "42 lakh" in prompt                      # only the relevant passages
    assert out["citations"] and out["citations"][0]["title"] == "Q3 report"


def test_web_and_youtube_sources(ai):
    from app.notebook import ingest

    def handler(req):
        if "oembed" in str(req.url):
            return httpx.Response(200, json={"title": "OLT basics", "author_name": "FNW Academy"})
        if req.url.path == "/moved":
            return httpx.Response(302, headers={"location": "/article"})
        html = "<html><head><title>Fiber guide</title></head><body><nav>menu</nav><p>" + "GPON splitters 1:32. " * 30 + "</p></body></html>"
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})
    ingest.set_http(httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        ctx = conv_ctx()
        out = run("notebook_create", {"title": "Fiber", "sources": [{"url": "https://example.in/moved"},
                                                                    {"url": "https://youtu.be/abcdefghijk"}]}, ctx)
        kinds = {a["kind"]: a for a in out["added"]}
        assert kinds["web"]["title"] == "Fiber guide" and kinds["youtube"]["title"] == "OLT basics"
        assert "transcript" in kinds["youtube"]["note"]
    finally:
        ingest.set_http(None)
    with pytest.raises(ingest.SourceError, match="andar ke network"):
        ingest._public("http://127.0.0.1/admin")


def test_file_and_email_attachment_sources(ai, monkeypatch):
    from app.mailbox import service as ms
    ctx = conv_ctx()
    f = ms.store_bytes("default", "plan.txt", "Plan: open Nashik office in December.".encode(), "mail")
    monkeypatch.setattr(ms, "attachment", lambda t, e, a: ("rates.csv", "text/csv", b"item,rate\nrouter,1200\n"))
    out = run("notebook_create", {"title": "Ops", "sources": [{"file_id": f.id}, {"email_id": "mbx~1", "attachment_id": "0"}]}, ctx)
    assert {a["title"] for a in out["added"]} == {"plan.txt", "rates.csv"}
    bad = run("notebook_add", {"notebook": "Ops", "sources": [{"nothing": 1}]}, ctx)
    assert bad["failed"] and not bad["added"]


def test_study_guide_and_note(ai):
    ctx = conv_ctx()
    run("notebook_create", {"title": "FNW Q3", "sources": [{"text": REPORT, "title": "Q3 report"}]}, ctx)
    out = run("notebook_make", {"notebook": "FNW Q3", "kind": "study_guide", "language": "hinglish"}, ctx)
    assert out["title"] == "Study guide: FNW Q3" and "42 lakh" in out["content"]
    assert "Hinglish" in ai.prompts[-1][1]
    note = run("notebook_note", {"notebook": "FNW Q3", "note_id": out["note_id"]}, ctx)
    assert note["kind"] == "study_guide"
    with pytest.raises(ToolError, match="kind"):
        run("notebook_make", {"notebook": "FNW Q3", "kind": "poem"}, ctx)


def test_audio_overview(ai, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.notebook import service as ns
    spoken = []
    monkeypatch.setattr(ns, "_tts_chunk", lambda text: spoken.append(text) or b"\x01\x00" * 24000 * 3)
    ctx = conv_ctx()
    run("notebook_create", {"title": "FNW Q3", "sources": [{"text": REPORT, "title": "Q3 report"}]}, ctx)

    async def go():
        out = await dispatch("notebook_audio", {"notebook": "FNW Q3", "style": "brief"}, ctx)
        await asyncio.gather(*list(ns._audio_tasks))
        return out
    out = asyncio.run(go())
    assert out["status"] == "making"
    d = run("notebook_open", {"notebook": "FNW Q3"}, ctx)
    a = d["audio"][0]
    assert a["status"] == "ready" and a["seconds"] >= 3 and a["file_id"], a
    assert "Ravi:" in spoken[0] and "Priya:" in spoken[0]
    card = _events(ctx.conversation_id, "pc_file")[-1]
    assert card["name"].startswith("FNW Q3 - audio overview")
    assert any("audio overview taiyaar" in (n or "") for n in _notices(ctx.conversation_id))


def test_audio_needs_gemini_key(ai):
    ctx = conv_ctx()
    run("notebook_create", {"title": "X", "sources": [{"text": "hello world " * 20}]}, ctx)
    with pytest.raises(ToolError, match="GEMINI_API_KEY"):
        run("notebook_audio", {"notebook": "X"}, ctx)


def test_delete_needs_the_tap(bz, ai):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    run("notebook_create", {"title": "Temp", "sources": [{"text": "abc def ghi " * 10}]}, ctx)
    run("notebook_delete", {"notebook": "Temp"}, ctx)
    assert run("notebook_list", {}, ctx)["notebooks"]
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Notebook delete karein?"
    bz["svc"].decide("default", card["id"], "approve")
    assert run("notebook_list", {}, ctx)["notebooks"] == []


def test_app_api(ai):
    from app import main
    with TestClient(main.app) as c:
        nb = c.post("/api/notebooks", json={"title": "Exam prep"}).json()
        nid = nb["id"]
        d = c.post(f"/api/notebooks/{nid}/sources", json={"text": REPORT, "title": "Notes"}).json()
        assert d["sources"][0]["title"] == "Notes"
        up = c.post(f"/api/notebooks/{nid}/upload", files={"file": ("ch1.txt", io.BytesIO(b"Chapter 1: OLT setup steps."), "text/plain")}).json()
        assert [s["title"] for s in up["sources"]] == ["Notes", "ch1.txt"]
        ans = c.post(f"/api/notebooks/{nid}/ask", json={"question": "revenue?"}).json()
        assert ans["citations"]
        assert c.post(f"/api/notebooks/{nid}/make", json={"kind": "faq"}).json()["title"].startswith("FAQ")
        assert c.get("/api/notebooks").json()["notebooks"][0]["sources"] == 2
        assert c.delete(f"/api/notebooks/{nid}").json()["deleted"] == "Exam prep"
    _ = json
