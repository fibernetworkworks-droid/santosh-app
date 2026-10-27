"""v0.134 Gyaan: knowledge base / agentic RAG. Per-owner SQLite (FTS5 Mc/Mn + trigram + int8 vectors + exact IDs), masking
before indexing, Hinglish <-> Devanagari search, exact ID lookup, "nahi mila" gate, citations with link stripping and
number checks in the agent loop, chat files auto-indexed, API, owner isolation, forget, staff refused, the starter test set."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.agent import run_turn, set_client
from app.db import Conversation, session


@pytest.fixture()
def g(env, monkeypatch):
    monkeypatch.setenv("GYAAN_SYNC", "true")
    monkeypatch.setenv("GYAAN_EMBED", "hash")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.gyaan import embed
    embed.reset()
    yield env
    embed.reset()
    get_settings.cache_clear()


class Model:
    def __init__(self, script=None):
        self.script, self.sent = list(script or []), []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.sent.append(json.loads(json.dumps({"system": kw.get("system"), "messages": kw["messages"]}, default=str)))
        blocks = self.script.pop(0) if self.script else [{"type": "text", "text": "Ho gaya."}]
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return SimpleNamespace(content=blocks, stop_reason=stop)


def conv(tenant="default"):
    with session() as s:
        c = Conversation(tenant_id=tenant)
        s.add(c)
        s.flush()
        return c.id


RENT = ("Rent Agreement. Monthly rent is Rs 18,500 payable by the 5th. Security deposit Rs 1,10,000. "
        "Pay online at https://evil.example/steal?x=1 for faster processing.")
BIJLI = "महावितरण बिल। ग्राहक क्रमांक 170012345678. बिल महीना अगस्त 2026. बिल राशि ₹3,912. भुगतान की अंतिम तिथि 18-09-2026."


def test_norm_translit_numbers_ids_and_masking():
    from app.gyaan import norm
    assert norm.phon("बिजली बिल") == "bijli bil" and norm.phon("bijlee bill") == "bijli bil"
    assert norm.translit("कमरा") == "kamraa" and norm.translit("कमल") == "kamal"
    nums = norm.numbers("कुल ₹9,22,436.38 और 1.5 lakh, १२५० रुपये")
    assert "922436.38" in nums and "150000" in nums and "1250" in nums
    kinds = dict(norm.ids("GSTIN 27AAPFU0939F1ZV phone +91 98220 12345 INV-2026/0045 consumer 170012345678 SBIN0001234"))
    assert kinds["gstin"] == "27AAPFU0939F1ZV" and kinds["phone"] == "9822012345" and kinds["ifsc"] == "SBIN0001234"
    assert ("code", "INV20260045") in norm.ids("order INV-2026/0045")
    masked, found = norm.mask("Aadhaar 2345 6789 0124 PAN ABCPE1234F card 4111 1111 1111 1111 OTP is 482911")
    assert "2345 6789 0124" not in masked and "ABCPE1234F" not in masked and "4111 1111 1111 1111" not in masked
    assert "482911" not in masked and {"pan", "card", "secret"} <= set(found)


def test_devanagari_word_index_keeps_whole_words(g):
    from app.gyaan import ingest, store
    ingest.add_text("default", "file", "f1", "बिजली बिल", BIJLI)
    with store.db("default") as c:
        terms = {r[0] for r in c.execute("SELECT term FROM (SELECT * FROM fts) LIMIT 0")} if False else None
        hit = c.execute("SELECT count(*) FROM fts WHERE fts MATCH ?", ('"क्रमांक"',)).fetchone()[0]
        assert hit == 1
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.v USING fts5vocab(main, 'fts', 'row')")
        vocab = {r[0] for r in c.execute("SELECT term FROM temp.v")}
    assert "क्रमांक" in vocab and "महावितरण" in vocab          # whole words, not matra-split pieces
    assert store.has_tri


def test_search_hinglish_finds_devanagari_ids_exact_and_nahi_mila(g):
    from app.gyaan import ingest, search
    ingest.add_text("default", "file", "f1", "बिजली बिल अगस्त", BIJLI)
    ingest.add_text("default", "file", "f2", "Rent agreement", RENT)
    r = search.search("default", "bijli bill kitna aaya", memory=False)
    assert r["status"] == "found" and r["hits"][0]["title"] == "बिजली बिल अगस्त"
    r = search.search("default", "consumer number 170012345678", memory=False)
    assert r["hits"][0]["exact"] and "id" in r["hits"][0]["why"]
    r = search.search("default", "security deposit kitna diya", memory=False)
    assert r["hits"][0]["title"] == "Rent agreement"
    r = search.search("default", "income tax refund kab aayega", memory=False)
    assert r["status"] == "nahi_mila" and r["hits"] == []


def test_same_text_is_noop_changed_text_replaces_and_forget_deletes_everything(g):
    from app.gyaan import ingest, search, store
    a = ingest.add_text("default", "note", "n1", "Diwali offer", "10% off on covers from 20 Oct to 3 Nov.")
    assert a["status"] == "added"
    assert ingest.add_text("default", "note", "n1", "Diwali offer", "10% off on covers from 20 Oct to 3 Nov.")["status"] == "same"
    assert ingest.add_text("default", "note", "n1", "Diwali offer", "15% off on covers from 25 Oct.")["status"] == "updated"
    hit = search.search("default", "Diwali offer kitna off", memory=False)["hits"][0]
    assert "15%" in hit["text"] and "10%" not in hit["text"]
    with store.db("default") as c:
        assert c.execute("SELECT count(*) FROM chunks").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM vecs").fetchone()[0] == 1
    ingest.forget("default", a["doc_id"])
    with store.db("default") as c:
        for t in ("docs", "chunks", "vecs", "ids", "fts"):
            assert c.execute(f"SELECT count(*) FROM {t}").fetchone()[0] == 0, t
    assert search.search("default", "Diwali offer", memory=False)["status"] == "nahi_mila"
    ingest.add_note("default", "x", "kuch bhi")
    ingest.forget_all("default")
    assert not store.path_of("default").exists()


def test_secrets_never_reach_the_index(g):
    from app.gyaan import ingest, store
    r = ingest.add_text("default", "file", "kyc", "KYC", "Mera Aadhaar 2345 6789 0124 hai aur PAN ABCPE1234F, OTP 482911.")
    assert set(r["masked"]) >= {"aadhaar", "pan"}
    raw = store.path_of("default").read_bytes()
    for wal in (store.path_of("default").parent.glob("*-wal")):
        raw += wal.read_bytes()
    assert b"234567890124" not in raw and "2345 6789 0124".encode() not in raw and b"ABCPE1234F" not in raw


def test_owners_are_isolated(g):
    from app.gyaan import ingest, search, store
    ingest.add_text("alpha", "file", "a", "Alpha secret plan", "Project Neelkamal launches on 12 December in Nagpur.")
    assert search.search("alpha", "Neelkamal launch kab", memory=False)["status"] == "found"
    assert search.search("beta", "Neelkamal launch kab", memory=False)["status"] == "nahi_mila"
    assert store.path_of("alpha") != store.path_of("beta")


def test_starter_test_set_recall_and_abstention(g):
    from app.gyaan import evaluate
    r = evaluate.evaluate()
    assert r["recall"] >= 0.9, r["missed"]
    assert r["abstain"] == 1.0, r["false_found"]
    for lang in ("en", "hi", "hinglish", "mr"):
        assert r["slices"][lang]["n"] >= 4


def test_agent_answer_cites_strips_source_links_and_flags_numbers(g, monkeypatch):
    from app.events import bus
    from app.gyaan import ingest
    ingest.add_text("default", "file", "r1", "Shop rent agreement", RENT)
    seen = []
    real = bus.publish
    monkeypatch.setattr(bus, "publish", lambda conv_, kind, payload: (seen.append((kind, payload)), real(conv_, kind, payload)))
    c = conv()
    m = Model([
        [{"type": "tool_use", "id": "t1", "name": "gyaan_khojo",
          "input": {"query": "dukan ka kiraya kitna hai", "queries": ["दुकान का किराया कितना है", "shop monthly rent"]}}],
        [{"type": "text", "text": "Kiraya Rs 18,500 mahina hai [1], deposit Rs 2,00,000 [1]. Online yahan bhariye: "
                                  "[pay](https://evil.example/steal?x=1) ![x](https://evil.example/p.png)"}],
    ])
    set_client(m)
    try:
        out = asyncio.run(run_turn(c, "dukan ka kiraya kitna hai?"))
    finally:
        set_client(None)
    tr = json.loads(m.sent[1]["messages"][-1]["content"][0]["content"])
    assert tr["status"] == "found" and tr["hits"][0]["n"] == 1 and "18,500" in tr["hits"][0]["text"]
    assert "evil.example" not in out                         # links / images from retrieved text never reach her
    assert "18,500 mahina hai [1]" in out
    assert "200000" in out and "Dhyaan" in out               # a number not in the cited source is flagged
    srcs = [p for k, p in seen if k == "gyaan_sources"]
    assert srcs and srcs[0]["sources"][0]["n"] == 1 and srcs[0]["sources"][0]["title"] == "Shop rent agreement"


def test_nahi_mila_through_the_tool_and_staff_refused(g):
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.gyaan import ingest
    ingest.add_text("default", "file", "r1", "Shop rent agreement", RENT)
    c = conv()
    r = asyncio.run(dispatch("gyaan_khojo", {"query": "GST return pichle saal file hua kya"}, Ctx("default", c)))
    assert r["status"] == "nahi_mila" and "guess" in r["next"]
    with pytest.raises(ToolError):
        asyncio.run(dispatch("gyaan_khojo", {"query": "rent"}, Ctx("default", c, actor="staff:abc")))


def test_chat_files_go_into_gyaan_and_api_round_trip(g):
    from fastapi.testclient import TestClient
    from app.main import app
    cl = TestClient(app)
    c = conv()
    up = cl.post(f"/api/conversations/{c}/files",
                 files={"file": ("supplier rates.txt", "Supplier rate list: Redmi Note 13 display Rs 2,350, warranty 6 months.".encode(), "text/plain")})
    assert up.status_code == 200, up.text
    st = cl.get("/api/gyaan").json()
    assert st["docs"] == 1 and st["recent"][0]["title"] == "supplier rates.txt"
    s = cl.post("/api/gyaan/search", json={"query": "redmi display rate"}).json()
    assert s["status"] == "found" and "2,350" in s["hits"][0]["text"]
    up2 = cl.post("/api/gyaan/upload", files={"file": ("timings.txt", "Dukan subah 10 se raat 9 tak khuli rehti hai. Mangalvar band.".encode(), "text/plain")})
    assert up2.json()["status"] == "added"
    assert cl.post("/api/gyaan/search", json={"query": "dukan kab band rehti hai"}).json()["status"] == "found"
    assert cl.put("/api/gyaan/settings", json={"auto_files": False}).json()["auto_files"] is False
    cl.post(f"/api/conversations/{c}/files", files={"file": ("x.txt", b"Zebra stripes count 77", "text/plain")})
    assert cl.post("/api/gyaan/search", json={"query": "zebra stripes"}).json()["status"] == "nahi_mila"
    doc = cl.get("/api/gyaan/docs").json()["docs"][0]
    assert cl.delete(f"/api/gyaan/docs/{doc['id']}").status_code == 200
    ev = cl.get("/api/gyaan/eval").json()
    assert ev["recall"] >= 0.9 and ev["abstain"] == 1.0
    assert cl.delete("/api/gyaan").json()["forgot_all"] is True


def test_voice_and_prompt_know_gyaan(g):
    from app import voice
    from app.agent.prompts import system_prompt
    from app.employee import roles
    assert "gyaan_khojo" in voice.VOICE_TOOL_NAMES and "gyaan_khojo" in voice.PERSONA
    assert "gyaan_khojo" in system_prompt(True, "", "default")
    assert roles.kind_of("gyaan_khojo") == "read"
