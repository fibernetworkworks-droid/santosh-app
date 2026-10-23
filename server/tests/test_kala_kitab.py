"""Kitab Sahayak: chapters from her manuscript, edit passes as tracked suggestions that change her text ONLY on her tap
(numbers / names never changed, rejections remembered), style sheet + consistency, Word tracked changes, permissions log with
public domain (life + 60), similarity against her sources, ISBN check digits + checklist + legal deposit, pitch with [blank]s
blocked and sent only on her tap, royalty by code from HER contract slabs vs the statement, KDP / POD maths from her numbers,
freelance invoice + delivery cards, worker reminders, DPDP forget, tools + API."""
import io
import json
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.kitab.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)

MS = """Chapter 1
Meera ne darwaza khola. Woh  bahut thaki thi.
Raat ke 11 baje the. Meera ne chai banayi , aur khidki par baith gayi.
Mira ko yaad aaya ki usne 3 chitthiyan likhni thi.

Chapter 2
Agle din Meera bazaar gayi gayi. Wahan usne apni dost Asha se baat ki.
"Zindagi ek safar hai, suhana, yahan kal kya ho kisne jaana, yahan kal kya ho kisne jaana" gaana radio par baj raha tha.
"""

HI = "अध्याय १\nराम ने दरवाज़ा खोला. वह बहुत थका था.\nवह  घर गया। उसने दरवाजा बंद किया।\n"


@pytest.fixture
def kb(env, monkeypatch):
    from app.kitab import service as S
    events, stored = [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=3000: "")
    clk = {"t": NOW}
    monkeypatch.setattr(S, "clock", lambda: clk["t"])
    S.EVENTS, S.STORED, S.CLK = events, stored, clk
    return S


def _book(S, **kw):
    S.save_settings(T, name="Sunita Kale", lang="en", upi_id="sunita@okaxis", email="sunita@example.com")
    b = S.book_save(T, title="Chai aur Chitthiyan", kind="fiction", lang="en", **kw)["book"]
    S.import_text(T, b["number"], MS)
    return b


def _ch(S, book, n=1):
    v = S.book_view(T, book)
    return next(c for c in v["chapter_list"] if c["n"] == n)["id"]


def test_rules():
    from app.kitab import rules as R
    parts = R.split_chapters(MS)
    assert [p[0] for p in parts] == ["Chapter 1", "Chapter 2"]
    assert R.split_chapters("bas ek kahani hai bina heading ke")[0][0] == "Chapter 1"
    assert R.lang_of(HI) == "hi" and R.lang_of("मी घरी आहे आणि तो नाही आला होता. आम्ही मला सांगितले होते.") == "mr" and R.lang_of(MS) == "en"
    assert R.words("राम ने दरवाज़ा खोला।") == 4
    sug = R.code_checks("Woh  bahut thaki thi. Meera ne chai banayi , aur gayi gayi.", "en")
    kinds = {(s["kind"], s["src"], s["dst"]) for s in sug}
    assert ("spacing", "  ", " ") in kinds and ("spacing", " ,", ",") in kinds and ("repeat", "gayi gayi", "gayi") in kinds
    hi = R.code_checks(HI, "hi")
    assert any(s["src"] == "." and s["dst"] == "।" for s in hi)          # danda by default in Hindi
    mr = R.code_checks("तो घरी आला। मग गेला.", "mr")
    assert any(s["src"] == "।" and s["dst"] == "." for s in mr)          # Marathi default = period
    ig = R.code_checks("Woh  thaki", "en", {"ignore": [["  ", " "]]})
    assert not any(s["src"] == "  " for s in ig)                         # her "no" remembered
    v = R.variants("Meera came. Then Mira left. The colour and the color. दरवाज़ा और दरवाजा", {})
    words = [set(x["words"]) for x in v]
    assert {"colour", "color"} in words and {"दरवाज़ा", "दरवाजा"} in words and {"Meera", "Mira"} in words
    q = R.quotes(MS)
    assert q and q[0]["kind"] == "lyrics"
    assert R.isbn_ok("978-93-5442-123-0") is False and R.isbn_ok("9780306406157") and R.isbn_ok("0-306-40615-2")
    assert R.pd_india(1941, 2026) is True and R.pd_india(1970, 2026) is False and R.pd_india(None, 2026) is None
    slabs = R.clean_slabs([{"upto": 2000, "pct": 7.5}, {"pct": 10}])
    assert R.royalty(slabs, 1500, 1000, 200) == round(500 * 200 * 0.075 + 500 * 200 * 0.10, 2)
    assert R.royalty(slabs, 0, 100, None) is None
    k = R.ebook_kdp(799, "70", 5)
    assert k["plan"] == "35" and k["royalty"] == round(0.35 * 799, 2)
    assert R.ebook_kdp(199, "70", 3, select=True)["royalty"] == round(0.7 * 196, 2)
    assert R.ebook_kdp(199, "70")["royalty"] is None                    # no delivery number = no guess
    assert R.pod(250, None, 50)["royalty"] is None and R.pod(300, 120, 50)["royalty"] == 90.0
    sim = R.similarity("ek do teen char paanch chhe saat aath nau das", "kuch aur ek do teen char paanch chhe saat aath bhi")
    assert sim["pct"] > 30 and sim["longest"] >= 6


def test_passes_are_suggestions_only_her_tap_changes_text(kb, monkeypatch):
    S = kb
    b = _book(S)
    cid = _ch(S, b["number"], 1)
    before = S.chapter_view(T, cid)["text"]
    out = S.run_pass(T, cid, "proof")
    assert out["made"] >= 2 and "badla nahi" in out["say"]
    assert S.chapter_view(T, cid)["text"] == before                     # nothing changed by the pass
    # the tool cannot apply: accept makes a card
    from app.agent.kitab_tools import KITAB_HANDLERS
    import asyncio
    ctx = conv_ctx()
    r = asyncio.run(KITAB_HANDLERS["kitab"](ctx, action="accept", book=b["number"], chapter="1"))
    assert r["status"] == "needs_tap" and r["card"]["kind"] == "accept"
    assert S.chapter_view(T, cid)["text"] == before
    with pytest.raises(S.KitabError):
        S.decide(T, r["card"]["id"], True, r["card"]["hash"])          # not by_tap
    with pytest.raises(S.KitabError):
        S.decide_suggestions(T, cid, [x["id"] for x in S.suggestions(T, cid)], True, "x", by_tap=False)
    # she edits the chapter after the card -> the card goes stale
    S.chapter_save(T, cid, before + "\nNayi line.")
    with pytest.raises(S.KitabError):
        S.decide(T, r["card"]["id"], True, r["card"]["hash"], by_tap=True)
    # fresh card, her tap applies exactly those changes
    r2 = S.accept_request(T, cid)
    d = S.decide(T, r2["card"]["id"], True, r2["card"]["hash"], by_tap=True)
    txt = S.chapter_view(T, cid)["text"]
    assert d["card"]["status"] == "approved" and "Woh bahut" in txt and "banayi, aur" in txt
    assert len(S.chapter_view(T, cid)["versions"]) >= 2                # old versions kept
    # app tap on single suggestions needs the hash of the text she sees
    cid2 = _ch(S, b["number"], 2)
    S.run_pass(T, cid2, "proof")
    sg = S.suggestions(T, cid2)
    rep = next(x for x in sg if x["kind"] == "repeat")
    with pytest.raises(S.KitabError):
        S.decide_suggestions(T, cid2, [rep["id"]], True, "wrong", by_tap=True)
    h = S.chapter_view(T, cid2)["hash"]
    S.decide_suggestions(T, cid2, [rep["id"]], True, h, by_tap=True)
    assert "bazaar gayi. " in S.chapter_view(T, cid2)["text"]


def test_model_edits_guarded_and_rejections_remembered(kb, monkeypatch):
    S = kb
    b = _book(S)
    cid = _ch(S, b["number"], 1)
    edits = {"edits": [
        {"from": "Raat ke 11 baje the.", "to": "Raat ke 12 baje the.", "why": "x", "kind": "word"},       # changes a number
        {"from": "Meera ne darwaza khola.", "to": "Sita ne darwaza khola.", "why": "y", "kind": "word"},   # changes a name
        {"from": "khidki par baith gayi", "to": "khidki ke paas baith gayi", "why": "behtar", "kind": "clarity"},
        {"from": "not in text", "to": "x", "why": "z"}]}
    monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=3000: json.dumps(edits))
    out = S.run_pass(T, cid, "line")
    assert out["made"] == 1 and len(out["refused"]) == 2
    sg = S.suggestions(T, cid)
    assert sg[0]["to"] == "khidki ke paas baith gayi" and sg[0]["pass"] == "line"
    S.reject(T, cid, [sg[0]["number"]], remember=True)
    assert S.suggestions(T, cid) == []
    out2 = S.run_pass(T, cid, "line")
    assert out2["made"] == 0                                             # same suggestion never comes back
    # developmental: letter + queries tied to exact quotes, no replacement
    dev = {"letter": "Achhi shuruaat. Meera kaun hai, thoda aur batayiye.", "queries": [{"quote": "Mira ko yaad aaya", "note": "Meera ya Mira?"}]}
    monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=3000: json.dumps(dev))
    d = S.run_pass(T, cid, "developmental")
    v = S.chapter_view(T, cid)
    assert d["made"] == 1 and v["letter"].startswith("Achhi") and v["suggestions"][0]["query"] is True
    with pytest.raises(S.KitabError):
        S.accept_request(T, cid, kinds=["query"])                       # queries can't be "applied"
    # no model -> developmental falls back to honest counts
    monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=3000: "")
    assert "Model abhi nahi chala" in S.run_pass(T, cid, "developmental")["letter"]


def test_style_sheet_tracked_word_and_hindi(kb):
    S = kb
    b = _book(S)
    c = S.consistency(T, b["number"])
    assert any({"Meera", "Mira"} == set(v["words"]) for v in c["variants"])
    S.style_save(T, b["number"], characters=[{"name": "Meera", "note": "nayika, 34 saal"}], choose="Meera")
    cid = _ch(S, b["number"], 1)
    S.run_pass(T, cid, "copy")
    assert any(x["from"] == "Mira" and x["to"] == "Meera" for x in S.suggestions(T, cid))
    out = S.export(T, b["number"], "tracked")
    name, data = S.STORED[-1]
    assert name.endswith("_tracked.docx") and "Track Changes" in out["say"]
    import zipfile
    xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode()
    assert "<w:del " in xml and "<w:ins " in xml and 'w:author="Hoola"' in xml and "Mira" in xml
    S.export(T, b["number"], "style")
    S.export(T, b["number"], "register")
    assert S.STORED[-1][0].endswith("_register.xlsx")
    # Hindi book: danda + nukta variants
    hb = S.book_save(T, title="राम की कहानी", lang="hi", kind="fiction")["book"]
    S.import_text(T, hb["number"], HI)
    hc = _ch(S, hb["number"], 1)
    S.run_pass(T, hc, "proof")
    sg = S.suggestions(T, hc)
    assert any(x["to"] == "।" for x in sg) and any(x["from"] == "  " for x in sg)
    assert any({"दरवाज़ा", "दरवाजा"} == set(v["words"]) for v in S.consistency(T, hb["number"])["variants"])


def test_permissions_isbn_checklist_similarity(kb, monkeypatch):
    S = kb
    b = _book(S)
    sc = S.permissions_scan(T, b["number"])
    assert sc["added"] == 1
    p = S.permissions(T, b["number"])["permissions"][0]
    assert p["kind"] == "lyrics" and len(p["excerpt"].split()) <= 12
    assert S.permissions_scan(T, b["number"])["added"] == 0            # deduped
    r = S.permission_save(T, b["number"], p["number"], status="public_domain", death_year=1990)
    assert r["permission"]["status"] == "needed" and "60 saal" in r["say"]
    with pytest.raises(S.KitabError):
        S.permission_request(T, b["number"], p["number"])               # holder first
    S.permission_save(T, b["number"], p["number"], holder="Saregama (music publisher)", contact="rights@example.com",
                      source="film song, lyricist", credit="Lyrics courtesy ...")
    card = S.permission_request(T, b["number"], p["number"])
    d = S.decide(T, card["card"]["id"], True, card["card"]["hash"], by_tap=True)
    assert d["draft"]["mailto"].startswith("mailto:rights@example.com") and S.permissions(T, b["number"])["permissions"][0]["status"] == "asked"
    with pytest.raises(S.KitabError):
        S.checklist_set(T, b["number"], "permissions", "done")          # can't tick while one is pending
    with pytest.raises(S.KitabError):
        S.isbn_set(T, b["number"], "paperback", "978-93-5442-123-0")
    S.isbn_set(T, b["number"], "paperback", "9780306406157")
    with pytest.raises(S.KitabError):
        S.isbn_set(T, b["number"], "ebook", "978-0-306-40615-7")        # same ISBN for two formats
    v = S.verso(T, b["number"])
    assert any("978-03-06406-15-7" in x for x in v["lines"]) and v["blanks"] >= 1
    S.book_save(T, b["number"], status="published", published_on="2026-10-01")
    cl = {i["key"]: i for i in S.checklist(T, b["number"])["items"]}
    assert cl["legal_deposit"]["due"] == "2026-10-31"
    sim = S.similarity_check(T, b["number"], text="Raat ke 11 baje the. Meera ne chai banayi , aur khidki par baith gayi.")
    assert sim["sources"][0]["flag"] and "signal" in sim["say"]

    async def fake_search(q):
        return {"sources": [{"url": "https://example.org/x", "title": "X"}, {"url": "javascript:alert(1)"}]}
    monkeypatch.setattr(S, "_web_search", fake_search)
    monkeypatch.setattr("app.kitab.rules.distinct_sentences", lambda t, k=3: ["Meera ne chai banayi aur khidki par baith gayi raat ko"])
    w = S.similarity_check(T, b["number"], web=True)
    assert [h["url"] for h in w["web"]] == ["https://example.org/x"]


def test_pitch_blanks_block_and_send_on_tap(kb, monkeypatch):
    S = kb
    b = _book(S)
    x = S.submission_save(T, b["number"], to="Kahani Press", kind="publisher", email="sub@kahanipress.example", exclusive=True)["submission"]
    r = S.pitch_request(T, b["number"], x["number"])
    assert r["status"] == "blanks" and r["pitch"]["blanks"] >= 1 and not [k for k, _ in S.EVENTS if k == "kitab_card"]
    # the model may not invent numbers: "sold 5000 copies" isn't in her facts -> blanked
    S.pitch_edit(T, b["number"], x["number"], letter="Dear Kahani Press,\nMy novel sold 5000 copies.\nRegards, Sunita", synopsis="Meera ki kahani.")
    with pytest.raises(S.KitabError):
        S.decide(T, "nope", True, "h", by_tap=True)
    r2 = S.pitch_request(T, b["number"], x["number"])
    assert r2["status"] == "needs_tap"
    y = S.submission_save(T, b["number"], to="Agent Two", email="a2@example.com")["submission"]
    S.submission_save(T, b["number"], y["number"], status="sent", sent_on="2026-07-01")
    S.pitch_edit(T, b["number"], x["number"], subject="Submission: Chai aur Chitthiyan")
    r3 = S.pitch_request(T, b["number"], x["number"])                 # state changed -> new card with the exclusive warning
    assert r3["card"]["show"]["warnings"]
    d = S.decide(T, r3["card"]["id"], True, r3["card"]["hash"], by_tap=True)
    assert d["draft"]["mailto"].startswith("mailto:sub@kahanipress.example") and d["files"]
    subs = {s["number"]: s for s in S.submissions(T, b["number"])}
    assert subs[x["number"]]["status"] == "sent" and subs[x["number"]]["follow_on"] == "2027-01-21"
    # pitch generator scrubs numbers not in her facts
    with S.session() as s:
        bk = s.get(S.KitabBook, b["id"])
        sub = s.get(S.KitabSubmission, subs[y["number"]]["id"])
        monkeypatch.setattr(S, "_ai", lambda system, prompt, max_tokens=3000: json.dumps(
            {"subject": "Novel", "letter": "Won 3 awards and sold 9000 copies.", "synopsis": "s"}))
        p = S._pitch(bk, sub, 1200, "Sunita")
    assert "9000" not in p["letter"] and "[blank]" in p["letter"]


def test_royalty_contract_platforms(kb):
    S = kb
    b = _book(S)
    with pytest.raises(S.KitabError):
        S.contract_save(T, b["number"], rates=[{"format": "paperback"}], actor="staff:x")
    out = S.contract_save(T, b["number"], publisher="Kahani Press", rates=[{"format": "paperback", "basis": "mrp",
                          "slabs": [{"upto": 2000, "pct": 7.5}, {"pct": 10}]}, {"format": "ebook", "basis": "net", "slabs": [{"pct": 25}]}],
                          advance=10000, period_months=6)
    assert "5 saal" in out["say"] and "sirf India" in out["say"]
    a = S.statement_add(T, b["number"], "Apr-Sep 2026", "paperback", units=1600, returns=100, price=250, stated=28000,
                        period_end="2026-09-30")
    assert a["statement"]["expected"] == round(1500 * 250 * 0.075, 2) and a["diff"] == round(28000 - 28125, 2) and "kam" in a["say"]
    a2 = S.statement_add(T, b["number"], "Oct-Mar 2027", "paperback", units=1000, price=250, period_end="2027-03-31")
    assert a2["statement"]["expected"] == round(500 * 250 * 0.075 + 500 * 250 * 0.10, 2)   # crosses the 2000 slab
    e = S.statement_add(T, b["number"], "Apr-Sep 2026", "ebook", units=100, period_end="2026-09-30")
    assert e["statement"]["expected"] is None and "net receipts" in e["say"]
    roy = S.royalties(T, b["number"])
    assert roy["advance"] == 10000 and roy["earned_out"] is True
    assert S.platform_calc("kdp", 199, "70", 3, True)["royalty"] == round(0.7 * 196, 2)
    assert S.platform_calc("pod", 300, print_cost=None, share_pct=50)["royalty"] is None


def test_freelance_invoice_deliver_tick_forget_tools_api(kb):
    S = kb
    S.save_settings(T, name="Sunita Kale", gstin="", upi_id="sunita@okaxis", rate={"per": "word", "amount": 0.5})
    b = S.book_save(T, title="Client ki Kitaab", mine=False, client={"name": "Ravi Joshi", "phone": "9876543210", "email": "ravi@example.com"},
                    deadline="2026-10-25")["book"]
    S.import_text(T, b["number"], MS)
    e = S.estimate(T, b["number"])
    assert e["amount"] == round(e["words"] * 0.5, 2)
    inv = S.invoice_request(T, b["number"])
    sh = inv["card"]["show"]
    assert sh["gst"] is None and sh["upi"].startswith("upi://pay?pa=sunita%40okaxis") and inv["status"] == "needs_tap"
    d = S.decide(T, inv["card"]["id"], True, inv["card"]["hash"], by_tap=True)
    assert d["draft"]["wa"].startswith("https://wa.me/919876543210") and d["file_id"]
    cid = _ch(S, b["number"], 1)
    S.run_pass(T, cid, "proof")
    dl = S.deliver_request(T, b["number"])
    dd = S.decide(T, dl["card"]["id"], True, dl["card"]["hash"], by_tap=True)
    assert len(dd["files"]) == 2
    # worker: deadline in 2 days + morning note once
    S.EVENTS.clear()
    S.tick(datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc))
    kinds = [k for k, _ in S.EVENTS]
    assert "kitab_alert" in kinds and "kitab_day" in kinds
    S.EVENTS.clear()
    S.tick(datetime(2026, 10, 23, 6, 0, tzinfo=timezone.utc))
    assert not S.EVENTS                                                  # once each
    with pytest.raises(S.KitabError):
        S.forget(T, b["number"])
    S.book_save(T, b["number"], status="done")
    S.forget(T, b["number"])
    assert S.book_view(T, b["number"])["client"] == {"name": "Client (hataya)"}
    # tools: staff can't do owner-only; customers refused; reads work
    import asyncio
    from app.agent.kitab_tools import KITAB_HANDLERS, KITAB_TOOLS
    from app.agent.tools import Ctx, ToolError
    for t in KITAB_TOOLS:
        props = t["input_schema"]["properties"]
        assert all(r in props for r in t["input_schema"]["required"])
    ctx = conv_ctx()
    staff = Ctx(ctx.tenant_id, ctx.conversation_id, actor="staff:e1")
    with pytest.raises(ToolError):
        asyncio.run(KITAB_HANDLERS["kitab"](staff, action="contract", book=b["number"]))
    with pytest.raises(ToolError):
        asyncio.run(KITAB_HANDLERS["kitab"](Ctx(ctx.tenant_id, ctx.conversation_id, actor="customer:x"), action="book", title="x"))
    assert asyncio.run(KITAB_HANDLERS["kitab_dekho"](ctx, what="rules"))["sources"]
    assert asyncio.run(KITAB_HANDLERS["kitab_dekho"](ctx, what="books"))["books"]
    # API
    from app.kitab.api import make_router
    app_ = FastAPI()
    app_.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app_)
    assert c.get("/api/kitab").status_code == 200
    nb = c.post("/api/kitab/books", json={"title": "API Book", "lang": "en"}).json()["book"]
    assert c.post(f"/api/kitab/books/{nb['number']}/import", json={"text": MS}).status_code == 200
    ch = c.get(f"/api/kitab/books/{nb['number']}").json()["chapter_list"][0]
    c.post(f"/api/kitab/chapters/{ch['id']}/pass", json={"pass": "proof"})
    cv = c.get(f"/api/kitab/chapters/{ch['id']}").json()
    ids = [s["id"] for s in cv["suggestions"]][:2]
    r = c.post(f"/api/kitab/chapters/{ch['id']}/suggestions/decide", json={"ids": ids, "yes": True, "hash": cv["hash"]})
    assert r.status_code == 200 and r.json()["applied"] >= 1
    assert c.post(f"/api/kitab/chapters/{ch['id']}/suggestions/decide", json={"ids": ids, "yes": True, "hash": "old"}).status_code == 400
    assert c.post("/api/kitab/books/K-999/import", json={"text": "x y z"}).status_code == 400
