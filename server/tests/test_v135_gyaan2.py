"""v0.135 Gyaan part 2: names (people / firms in any spelling / script) as a search signal + who-appears-with-whom, public
web pages kept fresh (same-site links, gone pages forgotten, private addresses refused), her own Sahayak records (profile,
Seva FAQ / policy, Kalam facts, price list; drafts never), the model grounding check on cited sentences, backfill for files
added before v0.135, tools + API."""
import asyncio
import json

import pytest

from app.db import Conversation, session


@pytest.fixture()
def g(env, monkeypatch):
    monkeypatch.setenv("GYAAN_SYNC", "true")
    monkeypatch.setenv("GYAAN_EMBED", "hash")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.gyaan import embed, search
    embed.reset()
    search._BACKFILLED.clear()
    yield env
    embed.reset()
    get_settings.cache_clear()


def conv(tenant="default"):
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


def test_names_found_in_three_scripts_and_firms_end_at_their_word():
    from app.gyaan import ents
    got = dict(ents.find("Invoice from Shree Ganesh Traders, Pune. Bill To: Kunal Patil. Date: 12 Oct. Total Rs 4,500"))
    assert got == {"Shree Ganesh Traders": "firm", "Kunal Patil": "name"}
    assert ("Patil Medical Stores", "firm") in ents.find("Patil Medical Stores ka bill aaya")
    deva = dict(ents.find("श्री रमेश गुप्ता जी ने गणेश ट्रेडर्स से माल लिया"))
    assert deva.get("गणेश ट्रेडर्स") == "firm" and any("गुप्ता" in n for n in deva)
    assert ents.find("Dear Sir, Please find attached the GST Invoice for October.") == []
    assert ents.key_of("Shree Ganesh Traders") == ents.key_of("श्री गणेश ट्रेडर्स")      # same key across scripts
    assert ents.find("raju ne gupta ji ko bola") == [("Gupta", "person")]


def test_search_by_name_any_spelling_and_who_appears_with_whom(g):
    from app.gyaan import ingest, search
    ingest.add_note("default", "Gupta ji", "Ramesh Gupta ji ka phone 9822012345 hai. Shree Ganesh Traders unki dukan hai.")
    ingest.add_note("default", "Order", "Shree Ganesh Traders se 20 bori atta aaya, Kunal Patil ne delivery di.")
    ingest.add_note("default", "Bijli", "Bijli ka bill Rs 3,912 aaya.")
    r = search.search("default", "गणेश ट्रेडर्स", ["ganesh traders"])
    assert r["status"] == "found" and "Ganesh Traders" in " ".join(r["names"])
    assert all(h["title"] != "Bijli" for h in r["hits"])
    assert any(h["named"] for h in r["hits"])
    names = {n["name"]: n["docs"] for n in ingest.names("default")}
    assert names.get("Shree Ganesh Traders") == 2
    w = ingest.who("default", "Ganesh Traders")
    assert w["found"] and {d["title"] for d in w["docs"]} == {"Gupta ji", "Order"}
    assert {x["name"] for x in w["related"]} >= {"Kunal Patil"}
    assert ingest.who("default", "Nobody Known")["found"] is False


def test_files_from_before_v0135_get_names_once(g):
    from app.gyaan import ingest, store
    ingest.add_note("default", "Purana", "Lotus Residency ka maintenance Anjali Deshmukh dekhti hain.")
    with store.db("default", write=True) as c:
        c.execute("DELETE FROM ents")
        store.set_meta(c, "ents_v", 0)
    assert ingest.ents_backfill("default") >= 2
    assert {n["name"] for n in ingest.names("default")} >= {"Lotus Residency", "Anjali Deshmukh"}
    assert ingest.ents_backfill("default") == 0                          # done once


def test_web_pages_follow_same_site_refresh_forget_and_refuse_private(g, monkeypatch):
    from app import web
    from app.gyaan import ingest, search
    pages = {
        "https://shop.example/": {"title": "Sharma Sweets", "text": "Sharma Sweets, Akola. Kaju katli Rs 960 kilo. " * 3,
                                  "links": [{"text": "Timings", "url": "https://shop.example/timings"},
                                            {"text": "Out", "url": "https://other.example/x"},
                                            {"text": "Menu pdf", "url": "https://shop.example/menu.pdf"}]},
        "https://shop.example/timings": {"title": "Timings", "text": "Dukan subah 9 se raat 10 tak khuli. Somvar band. " * 3,
                                         "links": []},
    }
    opened = []

    async def fake_open(url):
        opened.append(url)
        if url not in pages:
            raise web.WebError("The website answered with error 404.")
        return {"url": url, **pages[url]}

    def fake_check(url):
        if "127.0.0.1" in url:
            raise web.WebError("That address is not on the public internet, so Santosh won't open it.")
        return url
    monkeypatch.setattr(web, "open_website", fake_open)
    monkeypatch.setattr(web, "_check_url", fake_check)
    r = ingest.add_web("default", "https://shop.example/", follow=3)
    assert r["added"] == 2 and "https://other.example/x" not in opened and not any(u.endswith(".pdf") for u in opened)
    assert search.search("default", "kaju katli ka daam")["status"] == "found"
    st = ingest.status("default")
    w = next(x for x in st["watches"] if x["kind"] == "web")
    assert w["name"] == "Sharma Sweets" and w["files"] == 2
    # the site changes: price updated, timings page gone
    pages["https://shop.example/"]["text"] = "Sharma Sweets, Akola. Kaju katli Rs 1,040 kilo. " * 3
    pages["https://shop.example/"]["links"] = []
    del pages["https://shop.example/timings"]
    r2 = ingest.sync_web("default", w["id"])
    assert r2["updated"] == 1 and r2["removed"] == 1
    hit = search.search("default", "kaju katli")["hits"][0]
    assert "1,040" in hit["text"] and hit["source"] == "web" and hit["link"] == "https://shop.example/"
    with pytest.raises(ingest.GyaanError):
        ingest.add_web("default", "http://127.0.0.1/admin")
    ingest.remove_watch("default", w["id"])
    assert ingest.docs("default", "web") == []


def _records_setup():
    from app.employee.models import EmployeeProfile
    from app.kalam.service import KalamSettings
    from app.net.deal import StockItem
    from app.seva.service import SevaEntry
    with session() as s:
        s.add(EmployeeProfile(tenant_id="default", business_name="Ingle Fiber", business_kind="ISP",
                              about="Ghar aur office ke liye fiber internet", hours=json.dumps({"open": "10:00", "close": "19:00", "days": [0, 1, 2, 3, 4, 5]}),
                              rules="Installation 48 ghante mein"))
        s.add(SevaEntry(tenant_id="default", kind="faq", question="Router kharab ho to?", answer="Router 1 saal warranty mein free badla jayega.", status="live"))
        s.add(SevaEntry(tenant_id="default", kind="policy", question="", answer="Refund 7 din ke andar.", status="draft"))
        s.add(KalamSettings(tenant_id="default", business="Ingle Fiber", facts=json.dumps([{"fact": "5000 se zyada ghar jude hain", "source": "CRM"}])))
        s.add(StockItem(tenant_id="default", key="100 mbps plan", name="100 Mbps plan", unit="month", price=499, gst_pct=18,
                        tiers=[{"min": 12, "price": 449}]))


def test_her_records_become_searchable_drafts_never_and_switch_off_forgets(g):
    from app.gyaan import ingest, search
    _records_setup()
    r = ingest.sync_records("default")
    assert r["added"] == 4                                    # profile, Seva FAQ, Kalam facts, price list (no draft policy)
    assert search.search("default", "router warranty")["status"] == "found"
    price = search.search("default", "100 mbps plan ka daam", sources=["record"])
    assert price["status"] == "found" and "Rs 499" in price["hits"][0]["text"] and "449" in price["hits"][0]["text"]
    assert search.search("default", "refund kitne din mein")["status"] == "nahi_mila"
    assert ingest.sync_records("default")["same"] == 4         # unchanged = no-op
    from app.seva.service import SevaEntry
    with session() as s:
        s.query(SevaEntry).filter(SevaEntry.kind == "faq").delete()
    assert ingest.sync_records("default")["removed"] == 1      # gone there = gone here
    ingest.save_settings("default", records_on=False)
    assert ingest.docs("default", "record") == []
    assert ingest.sync_records("default") == {"status": "off"}


def test_grounding_check_flags_unsupported_sentences_and_skips_quietly(g, monkeypatch):
    from app.agent import pakka
    from app.config import get_settings
    from app.gyaan import answer
    monkeypatch.setenv("GYAAN_GROUND", "true")
    get_settings.cache_clear()
    answer.begin("c1")
    answer.register("c1", [{"chunk_id": 1, "title": "Rent", "source": "file", "text": "Monthly rent is Rs 18,500.", "at": ""}])
    text = "Kiraya Rs 18,500 hai [1]. Makaan malik Sharma ji hain [1]. Aur kuch chahiye?"
    seen = {}

    async def fake_ask(system, body, settings):
        seen["body"] = body
        return '{"unsupported": [2], "why": {"2": "name not in source"}}'
    monkeypatch.setattr(pakka, "_ask", fake_ask)
    out = asyncio.run(answer.ground("c1", text))
    assert out.startswith(text) and "Makaan malik Sharma ji hain" in out.split("(Dhyaan:")[1]
    assert "Aur kuch chahiye" not in seen["body"] and "[1] Rent" in seen["body"]

    async def slow(system, body, settings):
        await asyncio.sleep(5)
    monkeypatch.setenv("GYAAN_GROUND_TIMEOUT_S", "0.05")
    get_settings.cache_clear()
    monkeypatch.setattr(pakka, "_ask", slow)
    assert asyncio.run(answer.ground("c1", text)) == text      # no model in time = answer untouched

    async def all_ok(system, body, settings):
        return '{"unsupported": []}'
    monkeypatch.setattr(pakka, "_ask", all_ok)
    assert asyncio.run(answer.ground("c1", text)) == text
    monkeypatch.setenv("GYAAN_GROUND", "false")
    get_settings.cache_clear()
    monkeypatch.setattr(pakka, "_ask", fake_ask)
    assert asyncio.run(answer.ground("c1", text)) == text


def test_tool_and_api(g, monkeypatch):
    from fastapi.testclient import TestClient
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.main import app
    from app.gyaan import ingest
    ingest.add_note("default", "Party", "Shree Ganesh Traders ka udhaar Rs 12,000.")
    c = conv()
    r = asyncio.run(dispatch("gyaan", {"action": "names"}, Ctx("default", c)))
    assert r["names"][0]["name"] == "Shree Ganesh Traders"
    r = asyncio.run(dispatch("gyaan", {"action": "who", "name": "ganesh traders"}, Ctx("default", c)))
    assert r["found"]
    with pytest.raises(ToolError):
        asyncio.run(dispatch("gyaan", {"action": "records_off"}, Ctx("default", c, actor="staff:x")))
    k = asyncio.run(dispatch("gyaan_khojo", {"query": "Ganesh Traders udhaar"}, Ctx("default", c)))
    assert k["status"] == "found" and "Shree Ganesh Traders" in k["names"]
    cl = TestClient(app)
    assert cl.get("/api/gyaan/names").json()["names"][0]["docs"] == 1
    assert cl.get("/api/gyaan/names/who", params={"name": "Ganesh Traders"}).json()["found"] is True
    assert cl.put("/api/gyaan/settings", json={"records_on": False}).json()["records_on"] is False
    assert cl.post("/api/gyaan/web", json={}).status_code == 400
