"""Legalres Sahayak (legal researcher): old -> new law table, citation / section grounding, research from official pages + Indian
Kanoon API (her sealed key, daily cap) + her files, memo where every point has a verbatim quote, 'nahi mila', no-model fallback,
saved authorities, research log, Word memo, sharing only on her app tap (hash, stale), tools, API, forget."""
import asyncio

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.legalres.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
TOKEN = "abcDEF1234567890ghijKLMN"

BNS_PAGE = ("The Bharatiya Nyaya Sanhita, 2023. CHAPTER XVII OF OFFENCES AGAINST PROPERTY.\n"
            "318. (1) Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived to deliver any "
            "property to any person, is said to cheat.\n"
            "(4) Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, shall be "
            "punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable "
            "to fine.")
JUDGMENT_HTML = ("<html><body><h2>State v. Example Traders</h2><p>The accused was charged under Section 420 of the Indian Penal Code. "
                 "To make out an offence of cheating, dishonest intention must exist at the time of making the promise; a mere "
                 "breach of contract does not by itself amount to cheating. Reliance was placed on (2010) 3 SCC 100.</p></body></html>")
QUOTE_BNS = ("Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, shall be "
             "punished with imprisonment of either description for a term which may extend to seven years")
QUOTE_J = "a mere breach of contract does not by itself amount to cheating"


@pytest.fixture
def lr(env, monkeypatch):
    from app import web
    from app.legalres import service as S
    events, opened, ik_calls = [], [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_gyaan", lambda tenant, q: [{"title": "Client agreement (aapki file)", "url": "", "ref": "f1",
                                                          "text": "Agreement dated 1 March 2025: the supplier promised delivery of 200 bags of cement "
                                                                  "within 15 days; payment of Rs 2 lakh was made in advance."}])

    async def search_any(q):
        return {"query": q, "answer": "IPC 420 is now BNS 318 (model words: never a source)",
                "sources": [{"title": "Some law blog", "url": "https://lawblog.example.com/ipc-420"},
                            {"title": "indiacode.nic.in", "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/xyz"}]}

    async def open_website(url):
        opened.append(url)
        if "grounding-api-redirect" in url:
            return {"url": "https://www.indiacode.nic.in/show-data?actid=bns&section=318", "title": "BNS 2023 - Section 318", "text": BNS_PAGE}
        raise web.WebError("not reachable")

    monkeypatch.setattr(web, "search_any", search_any)
    monkeypatch.setattr(web, "open_website", open_website)

    def ik(request: httpx.Request):
        ik_calls.append(request.url.path)
        assert request.headers["Authorization"] == f"Token {TOKEN}"
        if request.url.path == "/search/":
            return httpx.Response(200, json={"found": "1 - 1 of 1", "docs": [
                {"tid": 111, "title": "State v. Example Traders", "headline": "cheating <b>420</b>", "docsource": "Supreme Court of India"}]})
        if request.url.path == "/doc/111/":
            return httpx.Response(200, json={"doc": JUDGMENT_HTML})
        return httpx.Response(404)

    monkeypatch.setattr(S, "_IK_TRANSPORT", httpx.MockTransport(ik))
    S.EVENTS, S.OPENED, S.IK_CALLS = events, opened, ik_calls
    return S


def good_model(system, prompt):
    assert "[1]" in prompt and "SOURCES" in prompt
    return {"short": "IPC 420 ab BNS 318(4) hai; saza 7 saal tak [1]. Dekhiye AIR 2001 SC 55 bhi.",
            "points": [
                {"text": "BNS Section 318(4): cheating karke property dilwana, saza 7 saal tak + jurmana.", "sources": [2], "quote": QUOTE_BNS},
                {"text": "Sirf contract todna cheating nahi; (2019) 5 SCC 999 mein bhi yahi kaha.", "sources": [3], "quote": QUOTE_J},
                {"text": "Isme Section 999 bhi lagta hai.", "sources": [2], "quote": QUOTE_BNS},
                {"text": "Supplier ne bura irada rakha tha.", "sources": [1], "quote": "the supplier intended to cheat from day one"},
                {"text": "Kuch aur.", "sources": [], "quote": ""}],
            "gaps": ["Is matter mein shuru se dhokha tha ya nahi, yeh evidence par hai."]}


def test_rules_mapping_and_grounding():
    from app.legalres import rules as R
    m = R.map_old("IPC", "420")
    assert m["new_act"] == "BNS" and m["new"] == "318(4)" and m["sure"]
    assert R.map_old("CRPC", "438")["new"] == "482" and R.map_old("IEA", "65B")["new"] == "63"
    assert not R.map_old("IPC", "326")["sure"] and "andaaza" in R.map_old("IPC", "326")["label"]
    assert R.map_old("IPC", "377")["label"] == "hata diya gaya"
    assert [x["old"] for x in R.map_new("BNS", "103(1)")] == ["302"]
    refs = R.find_refs("धारा ३०२ आईपीसी aur CrPC ki dhara 438, plus Evidence Act 65B and 420 IPC")
    assert {(r["act"], r["sec"]) for r in refs} >= {("IPC", "302"), ("CRPC", "438"), ("IEA", "65B"), ("IPC", "420")}
    rows = R.mapping_for("bail under CrPC 438 for IPC 498A")
    assert {r["new"] for r in rows} == {"482", "85"}
    src = R.norm(BNS_PAGE)
    clean, rem = R.ground("Per section 318 and section 999, see (2014) 8 SCC 273.", [src])
    assert "318" in clean and "999" not in clean and "SCC" not in clean and clean.count(R.NEED_CITE) == 2 and len(rem) == 2
    assert R.ground("BNS 420 hai", [src], {"420"})[1] == []
    assert R.quote_ok(QUOTE_BNS, src) and not R.quote_ok("punished with death", src) and not R.quote_ok("whoever", src)
    assert R.official("https://www.indiacode.nic.in/x") and R.official("https://bombayhighcourt.nic.in/") and R.official("https://sci.gov.in/a")
    assert not R.official("https://indiankanoon.org/doc/1/") and not R.official("https://evil.gov.in.example.com/")
    assert R.cite_in_source("(2010) 3 SCC 100", R.norm(JUDGMENT_HTML))


def test_research_end_to_end_grounded(lr, monkeypatch):
    S = lr
    S.set_ik_key(T, TOKEN)
    monkeypatch.setattr(S, "_model_json", good_model)
    out = asyncio.run(S.research(T, "IPC 420 cheating kab banta hai jab supplier maal na de?", client="Patil Traders"))
    memo = out["memo"]
    assert memo["status"] == "found" and out["matter"]["number"] == "LR-0001"
    # sources: her file [1], India Code page via the search redirect [2] (official), IK judgment [3]; the blog was never opened
    srcs = {x["n"]: x for x in S.matter_view(T, "LR-0001")["sources"]}
    assert srcs[1]["via"] == "gyaan" and srcs[2]["official"] and srcs[2]["kind"] == "statute" and srcs[3]["via"] == "ikanoon"
    assert not any("lawblog" in u for u in S.OPENED)
    assert S.IK_CALLS == ["/search/", "/doc/111/"]
    texts = [p["text"] for p in memo["points"]]
    assert len(memo["points"]) == 3                                         # bad quote + no-source point dropped
    assert "318(4)" in texts[0] and not memo["points"][0]["flagged"]
    assert "(2019) 5 SCC 999" not in texts[1] and "[citation chahiye]" in texts[1]
    assert "999" not in texts[2] and "[citation chahiye]" in texts[2]
    assert "AIR 2001 SC 55" not in memo["short"] and "318(4)" in memo["short"]
    whys = " ".join(memo["flags"])
    assert "hubahu" in whys and "padhe gaye source" in whys
    assert {r["old"]: r["new"] for r in memo["mapping"]} == {"420": "318(4)"}
    assert memo["attribution"].startswith("Judgments / search: powered by IKanoon") and memo["ik_used"]
    assert R_disclaimer_in(out["say"])
    st = S.settings(T)
    assert st["ik_today_rs"] == pytest.approx(0.70) and st["ik_ok"]
    v = S.matter_view(T, "LR-0001")
    assert v["spent_rs"] == pytest.approx(0.70) and any(x["kind"] == "memo" for x in v["log"])
    assert [k for k, _ in S.EVENTS] == ["legalres_memo"]
    # saved authority + Word memo
    S.save_authority(T, "LR-0001", 3, "dishonest intention at the start")
    auth = S.authorities(T)
    assert [a["n"] for a in auth] == [3] and auth[0]["matter"] == "LR-0001"
    S.save_authority(T, "LR-0001", 1)
    assert [a["n"] for a in S.authorities(T)] == [3]                           # her file stays inside its matter
    assert {a["n"] for a in S.authorities(T, matter="LR-0001")} == {1, 3}
    f = S.memo_file(T, "LR-0001")
    assert f["file"]["file_id"]
    _, text = S.memo_text(T, "LR-0001")
    assert "Source [2] mein" in text and "| IPC 420 | BNS 318(4) |" in text and "legal advice nahi" in text


def R_disclaimer_in(say):
    from app.legalres import rules as R
    return R.DISCLAIMER in say


def test_nahi_mila_cap_and_no_model(lr, monkeypatch):
    S = lr
    from app import web

    async def nothing(q):
        return {"sources": []}
    monkeypatch.setattr(web, "search_any", nothing)
    monkeypatch.setattr(S, "_gyaan", lambda t, q: [])
    monkeypatch.setattr(S, "_model_json", lambda s, p: pytest.fail("no model call without sources"))
    out = asyncio.run(S.research(T, "Kya mandir trust ke liye koi naya rule 2026 mein aaya?", use_ik=False))
    assert out["memo"]["status"] == "nahi_mila" and out["memo"]["points"] == [] and "nahi mila" in out["memo"]["short"]
    with pytest.raises(S.LegalresError):
        S.share_request(T, out["matter"]["number"], "Adv. Joshi")              # nothing found = nothing to send
    # daily cap: search costs Rs 0.50, cap Rs 0.30 -> no IK call at all
    S.set_ik_key(T, TOKEN)
    S.save_settings(T, ik_day_rs=0.3)
    monkeypatch.setattr(S, "_model_json", lambda s, p: {})                  # model down -> quote-only memo
    S.IK_CALLS.clear()
    out2 = asyncio.run(S.research(T, "cheating under BNS 318", use_web=False, urls=[]))
    assert S.IK_CALLS == [] and "limit" in " ".join(out2["memo"]["notes"])
    # her own file still gives a quote-only memo (no conclusions)
    monkeypatch.setattr(S, "_gyaan", lambda t, q: [{"title": "Notes", "url": "", "ref": "f2", "text": BNS_PAGE}])
    out3 = asyncio.run(S.research(T, "cheating punishment BNS 318", use_web=False, use_ik=False))
    m3 = out3["memo"]
    assert m3["status"] == "found" and not m3["model"] and "Model nahi chala" in m3["short"]
    from app.legalres import rules as R
    assert all(R.quote_ok(p["quote"], R.norm(BNS_PAGE)) for p in m3["points"])
    with pytest.raises(S.LegalresError):
        asyncio.run(S.research(T, "ab"))


def test_share_only_on_her_tap(lr, monkeypatch):
    S = lr
    monkeypatch.setattr(S, "_model_json", good_model)
    asyncio.run(S.research(T, "IPC 420 cheating kab banta hai?", use_ik=False))
    with pytest.raises(S.LegalresError):
        S.share_request(T, "LR-0001", "Adv. Joshi", actor="staff:s1")
    card = S.share_request(T, "LR-0001", "Adv. Joshi", "98765 43210", "whatsapp")
    assert card["status"] == "needs_tap" and card["share"]["status"] == "waiting"
    sid, h = card["share"]["id"], card["share"]["hash"]
    with pytest.raises(S.LegalresError):
        S.decide_share(T, sid, True, h)                                       # not a tap
    # a newer memo after the card makes it stale
    asyncio.run(S.research(T, "IPC 420 aur BNS 318 mein fark?", matter="LR-0001", use_ik=False))
    with pytest.raises(S.LegalresError):
        S.decide_share(T, sid, True, h, by_tap=True)
    assert S.shares(T, "stale")[0]["id"] == sid
    card2 = S.share_request(T, "LR-0001", "Adv. Joshi", "9876543210", "whatsapp")
    with pytest.raises(S.LegalresError):
        S.decide_share(T, card2["share"]["id"], True, "0" * 64, by_tap=True)  # wrong hash
    card3 = S.share_request(T, "LR-0001", "Adv. Joshi", "9876543210", "whatsapp")
    done = S.decide_share(T, card3["share"]["id"], True, card3["share"]["hash"], by_tap=True)
    assert done["share"]["status"] == "shared" and done["file"]["file_id"] and done["links"]["whatsapp"].startswith("https://wa.me/919876543210")
    again = S.decide_share(T, card3["share"]["id"], True, card3["share"]["hash"], by_tap=True)
    assert "pehle hi" in again["say"]
    no = S.share_request(T, "LR-0001", "Client", "", "email")
    assert S.decide_share(T, no["share"]["id"], False, no["share"]["hash"], by_tap=True)["share"]["status"] == "rejected"


def test_tools(lr, monkeypatch):
    S = lr
    from app.agent import legalres_tools as LT
    from app.agent.tools import Ctx, ToolError
    monkeypatch.setattr(S, "_model_json", good_model)
    ctx = conv_ctx()
    out = asyncio.run(LT.legalres(ctx, "research", question="IPC 420 cheating kab banta hai?", use_ik=False))
    assert out["memo"]["status"] == "found"
    with pytest.raises(ToolError):
        asyncio.run(LT.legalres(ctx, "settings", token=TOKEN))
    with pytest.raises(ToolError):
        asyncio.run(LT.legalres(ctx, "research", question="mera token: " + "a" * 40))
    staff = Ctx(T, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(ToolError):
        asyncio.run(LT.legalres(staff, "share", matter="LR-0001", to_name="X"))
    cust = Ctx(T, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(LT.legalres_dekho(cust, "matters"))
    card = asyncio.run(LT.legalres(ctx, "share", matter="LR-0001", to_name="Adv. Joshi", to_contact="9876543210"))
    assert card["status"] == "needs_tap"                                       # a card, never sent by the tool
    assert asyncio.run(LT.legalres_dekho(ctx, "mapping", text="CrPC 438 aur 65B Evidence Act"))["rows"][0]["new"] in ("482", "63")
    assert asyncio.run(LT.legalres_dekho(ctx, "source", matter="LR-0001", n=2))["text"].startswith("The Bharatiya Nyaya")
    assert asyncio.run(LT.legalres(ctx, "note", matter="LR-0001", text="Client se agreement ki copy mangvaani hai"))["say"]
    assert any("agreement" in x["text"] for x in asyncio.run(LT.legalres_dekho(ctx, "log", matter="LR-0001"))["log"])
    with pytest.raises(ToolError):
        asyncio.run(LT.legalres(staff, "forget", matter="LR-0001"))
    assert {t["name"] for t in LT.LEGALRES_TOOLS} == set(LT.LEGALRES_HANDLERS) == set(LT.LEGALRES_LABELS)


def test_api_key_sealed_matters_forget(lr, monkeypatch):
    S = lr
    from app.legalres.api import make_router
    monkeypatch.setattr(S, "_model_json", good_model)
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.put("/api/legalres/key", json={"token": "bad key!"}).status_code == 400
    r = c.put("/api/legalres/key", json={"token": TOKEN}).json()
    assert r["ik_joined"] and r["ik_label"].endswith(TOKEN[-4:]) and TOKEN not in str(r)
    from app.db import session
    from app.legalres.models import LegalresSettings
    with session() as s:
        assert TOKEN not in s.get(LegalresSettings, T).ik_sealed
    assert TOKEN not in str(c.get("/api/legalres").json())
    r = c.post("/api/legalres/research", json={"question": "IPC 420 cheating kab banta hai?"}).json()
    assert r["memo"]["status"] == "found"
    mt = c.get("/api/legalres/matters/LR-0001").json()
    assert len(mt["sources"]) == 3 and mt["memo"]["v"] == 1 and "text" not in mt["sources"][0]
    assert c.get("/api/legalres/mapping", params={"text": "IPC 302"}).json()["rows"][0]["new"] == "103(1)"
    assert c.post("/api/legalres/matters/LR-0001/sources/3/save", json={"note": "key ruling"}).json()["source"]["saved"]
    card = c.post("/api/legalres/matters/LR-0001/share", json={"to_name": "Adv. Joshi", "to_contact": "9876543210"}).json()
    d = c.post(f"/api/legalres/shares/{card['share']['id']}/decide", json={"yes": True, "hash": card["share"]["hash"]}).json()
    assert d["share"]["status"] == "shared"
    assert c.post("/api/legalres/matters/LR-0001/memo/file", json={}).json()["file"]["file_id"]
    assert c.post("/api/legalres/matters/LR-0001/forget").status_code == 400     # must be closed first
    assert c.patch("/api/legalres/matters/LR-0001", json={"status": "closed"}).json()["matter"]["status"] == "closed"
    assert "mita" in c.post("/api/legalres/matters/LR-0001/forget").json()["say"]
    assert c.get("/api/legalres/matters/LR-0001").status_code == 400
    assert S.authorities(T) == []
    assert c.delete("/api/legalres/key").json()["ik_joined"] is False
