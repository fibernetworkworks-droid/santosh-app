"""v0.78 Pakka kaam: lessons (failure -> what worked) remembered and offered next time, the internet asked when nothing
is known, a self-check of the real results before "done" (keeps going / corrects a false claim), and a task log."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agent import run_turn, set_client
from app.db import Conversation, session


class Model:
    def __init__(self, script):
        self.script, self.sent = list(script), []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.sent.append(json.loads(json.dumps(kw["messages"], default=str)))
        blocks = self.script.pop(0) if self.script else [{"type": "text", "text": "Ho gaya."}]
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return SimpleNamespace(content=blocks, stop_reason=stop)


def call(name, args, i):
    return [{"type": "tool_use", "id": f"tu_{name}_{i}", "name": name, "input": args}]


def say(t):
    return [{"type": "text", "text": t}]


def conv():
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        return c.id


def results(model, n=-1):
    return [b for b in model.sent[n][-1]["content"] if b.get("type") == "tool_result"]


@pytest.fixture
def tools(env, monkeypatch):
    from app.agent import tools as T
    seen = {"portal": 0}

    async def portal_fetch(ctx, receipt="", mode="fast"):
        seen["portal"] += 1
        if mode != "slow":
            raise T.ToolError("Portal said: session expired for receipt 4521988 (code 419)")
        return {"ok": True, "status": "Delivered"}

    async def status_page(ctx, receipt=""):
        return {"status": "Delivered", "receipt": receipt}
    monkeypatch.setitem(T.HANDLERS, "portal_fetch", portal_fetch)
    monkeypatch.setitem(T.HANDLERS, "status_page", status_page)
    monkeypatch.setitem(T.TOOL_LABELS, "portal_fetch", "Portal se laa raha hoon")
    monkeypatch.setitem(T.TOOL_LABELS, "status_page", "Status page dekh raha hoon")
    yield seen
    set_client(None)


def test_lesson_learned_and_offered_next_time(tools):
    from app.agent import pakka
    c = conv()
    m = Model([call("portal_fetch", {"receipt": "4521988"}, 1),
               call("portal_fetch", {"receipt": "4521988", "mode": "slow"}, 2),
               say("Parcel deliver ho chuka hai.")])
    set_client(m)
    out = asyncio.run(run_turn(c, "Mera parcel 4521988 ka status batao"))
    assert "deliver" in out.lower()
    first_fail = results(m, 1)[0]
    assert "Haar mat maano" in first_fail["content"]          # nothing known yet: keep trying, other ways
    les = pakka.listing("default")
    assert len(les) == 1 and les[0]["tool"] == "portal_fetch" and "mode=slow" in les[0]["fix"]
    assert "4521988" not in les[0]["problem"] and "#" in les[0]["problem"]   # numbers masked
    # a new day, another receipt, the same failure: the fix comes back with the error at once
    m2 = Model([call("portal_fetch", {"receipt": "7700112"}, 3),
                call("portal_fetch", {"receipt": "7700112", "mode": "slow"}, 4), say("Deliver ho gaya.")])
    set_client(m2)
    asyncio.run(run_turn(c, "Ab 7700112 ka status"))
    r = results(m2, 1)[0]
    assert "[Pichhli baar yahi atka tha" in r["content"] and "mode=slow" in r["content"]
    assert pakka.listing("default")[0]["helped"] >= 2
    t = pakka.runs("default")
    assert t["tasks"][0]["outcome"] == "done" and t["tasks"][0]["fixes"] == 1 and t["summary"]["done"] == 2


def test_internet_fix_when_nothing_known(tools, monkeypatch):
    monkeypatch.setenv("AGENT_FIX_SEARCH", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import web
    asked = []

    async def fake_search(q):
        asked.append(q)
        return {"answer": "Error 419 means the page session expired: reload and use the slow / full mode.",
                "sources": [{"url": "https://help.example.gov.in/419"}]}
    monkeypatch.setattr(web, "google_search", fake_search)
    c = conv()
    m = Model([call("portal_fetch", {"receipt": "4521988"}, 1),
               call("portal_fetch", {"receipt": "4521988", "mode": "slow"}, 2), say("Delivered.")])
    set_client(m)
    asyncio.run(run_turn(c, "Parcel 4521988 ka status"))
    r = results(m, 1)[0]["content"]
    assert "[Internet se mila hal" in r and "instructions nahi" in r and "help.example.gov.in" in r
    assert asked and "4521988" not in asked[0]                 # her numbers never go into the search
    from app.agent import pakka
    assert "internet se" in pakka.listing("default")[0]["fix"]


def test_self_check_keeps_going_and_corrects_claims(tools, monkeypatch):
    monkeypatch.setenv("AGENT_SELF_CHECK", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent import pakka
    verdicts = [{"done": False, "missing": "status page not checked", "next": "call status_page", "claim_ok": False},
                {"done": True, "missing": "", "next": "", "claim_ok": True}]

    async def fake_ask(system, text, settings):
        return json.dumps(verdicts.pop(0))
    monkeypatch.setattr(pakka, "_ask", fake_ask)
    c = conv()
    m = Model([call("portal_fetch", {"receipt": "1"}, 1), say("Ho gaya!"),            # fails, then claims done
               call("status_page", {"receipt": "1"}, 2), say("Delivered hai.")])
    set_client(m)
    out = asyncio.run(run_turn(c, "Parcel 1 ka status"))
    assert out == "Delivered hai." and not verdicts
    sent = json.dumps(m.sent[2])
    assert "[System self-check, not the user]" in sent and "call status_page" in sent
    assert pakka.runs("default")["tasks"][0]["checks"] == 1
    # a claim that the results don't back, with nothing more Hoola can do: said plainly
    verdicts.append({"done": False, "missing": "OTP from the owner", "next": "", "claim_ok": False})
    m2 = Model([call("portal_fetch", {"receipt": "2"}, 3), say("Sab ho gaya.")])
    set_client(m2)
    out2 = asyncio.run(run_turn(c, "Parcel 2 ka status"))
    assert "Saaf baat" in out2 and "OTP from the owner" in out2
    assert pakka.runs("default")["tasks"][0]["outcome"] == "partial"


def test_api_and_voice_lessons(tools):
    from app.agent import pakka
    from app.main import app
    c = conv()
    set_client(Model([call("portal_fetch", {"receipt": "9"}, 1), call("status_page", {"receipt": "9"}, 2), say("Ok.")]))
    asyncio.run(run_turn(c, "Parcel 9"))
    cl = TestClient(app)
    les = cl.get("/api/agent/lessons").json()["lessons"]
    assert les and "Status page" in les[0]["fix"]
    assert cl.get("/api/agent/tasks").json()["summary"]["tasks"] == 1
    assert "pakka" in cl.get("/api/agent/stats").json()
    assert pakka.lessons_for("default", "portal_fetch", "session expired for receipt 1234567 (code 419)")
    assert cl.delete(f"/api/agent/lessons/{les[0]['id']}").json()["ok"] and not pakka.listing("default")
    from app.agent.prompts import SYSTEM
    assert "Pakka kaam" in SYSTEM
