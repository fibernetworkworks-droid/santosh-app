"""v0.87 Lekhak Sahayak: typist + translator. Letters from her words / voice, nothing invented (facts checked, blanks
listed), translation with locked facts + back-check, grammar with small checked edits, Kruti Dev <-> Unicode, Word + a real
Chromium PDF, signing only on her tap (hash-locked), learning from her edits."""
import asyncio
import io
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"


def _L():
    from app.lekhak import service as L
    return L


LETTER = {"title": "बिजली बिल शिकायत", "to_lines": ["सहायक अभियंता", "महावितरण, अकोट"], "subject": "गलत बिजली बिल के संबंध में",
          "salutation": "महोदय,", "body": ["निवेदन है कि मेरा ग्राहक क्रमांक 310045678901 है।",
                                         "मेरा अक्टूबर का बिल ₹12,500 आया है, जबकि सामान्यतः ₹900 आता है। मीटर नंबर [मीटर नंबर] है।"],
          "thanks": "सधन्यवाद।", "closing": "भवदीया,", "sign_lines": ["सीता पाटील"], "enclosures": ["बिल की प्रति"],
          "missing": ["meter number"], "notes": []}


@pytest.fixture
def fake_ai(monkeypatch):
    L = _L()
    calls = []

    def ai(system, prompt, max_tokens=2500):
        calls.append((system, prompt))
        if "formal letter" in system:
            return json.dumps(LETTER, ensure_ascii=False)
        if "Apply ONLY the change" in system:
            p = json.loads(prompt.split("Letter parts:\n", 1)[1])
            p["subject"] = "अक्टूबर 2026 के गलत बिल के संबंध में"
            p["changed"] = "subject badla"
            return json.dumps(p, ensure_ascii=False)
        if "careful Indian translator" in system:
            # a translator that keeps markers, except one it drops (to prove we notice)
            out = prompt.replace("मेरा नाम", "My name is").replace("है", "")
            return out
        if "literally" in system:
            return "back translation"
        if "Compare an original" in system:
            return json.dumps({"same": False, "differences": ["'jaldi' ka bhaav nahi aaya"]})
        if "proofreader" in system:
            return json.dumps({"edits": [{"from": "मेरी नाम", "to": "मेरा नाम", "why": "ling"},
                                         {"from": "500 रुपये", "to": "5000 रुपये", "why": "galat"},
                                         {"from": "किया था", "to": "किया था।", "why": "viram"}]})
        return "{}"
    monkeypatch.setattr(L, "_ai", ai)
    return calls


def test_dictation_commands_and_facts():
    L = _L()
    t = L.clean_dictation("umm mera mera naam Sita hai comma consumer number 3100 4567 8901 poorn viram naya para bill galat hai")
    assert t.startswith("mera naam Sita hai, consumer number") and "।\n\nbill" in t and "umm" not in t
    assert L.facts_of("Bill ₹12,500 aaya, consumer ३१००४५६७८९०१, mail sita@x.in, ID {id:ab12}") == \
        ["12,500", "310045678901", "sita@x.in", "{id:ab12}"]
    assert L._fact_in("3100 4567 8901", "क्रमांक 310045678901 है")
    assert L.detect_lang("मला विनंती आहे की माझे बिल") == "mr" and L.detect_lang("मुझे निवेदन है कि मेरा") == "hi"
    assert L.detect_lang("mera bill galat hai aap check karo") == "hinglish"
    assert L.nfc("नमस्ते ।  ठीक") == "नमस्ते। ठीक"


def test_krutidev_both_ways():
    from app.lekhak.krutidev import from_unicode, looks_krutidev, to_unicode
    assert to_unicode("fgUnh") == "हिन्दी" and to_unicode("/keZ") == "धर्म" and to_unicode("izkFkZuk i=") == "प्रार्थना पत्र"
    assert to_unicode("Jheku~ rglhynkj] vdksV") == "श्रीमान् तहसीलदार, अकोट"
    for w in ("महाराष्ट्र", "पूर्णिमा", "अध्यक्ष", "विद्यालय", "निवेदन है कि मेरा नाम सीता है।", "क्षेत्र", "शुद्ध"):
        assert to_unicode(from_unicode(w)) == w
    assert looks_krutidev("egksn;] fuosnu gS fd esjk uke lhrk gS") and not looks_krutidev("Dear sir I am writing to you")


def test_letter_from_her_words_checked(env, fake_ai):
    L = _L()
    L.save_settings(T, my_name="सीता पाटील", place="अकोट", gender="f", lang="mr", my_lines=["Khanapur Ves, Akot"])
    L.contact_save(T, "MSEDCL Akot", ["सहायक अभियंता", "महावितरण, अकोट"])
    out = L.write_letter(T, "MSEDCL ko complaint likho, mera consumer number 310045678901 hai, bill 12500 rupaye aaya jabki "
                            "hamesha 900 aata hai, meter number 77001234 hai", lang="hi", to="MSEDCL Akot",
                         conv=conv_ctx().conversation_id)
    d = out["doc"]
    assert d["number"] == "L-0001" and d["kind"] == "complaint" and d["status"] == "draft"
    assert d["parts"]["to_lines"] == ["सहायक अभियंता", "महावितरण, अकोट"]          # address book used
    assert "77001234" in d["checks"]["missing_facts"]                              # model dropped her meter number: caught
    assert "[मीटर नंबर]" in d["checks"]["blanks"]
    assert any("Marathi" in n for n in d["checks"]["notes"])                        # Maharashtra govt office -> Marathi rule
    assert "₹12,500/- = बारह हज़ार पाँच सौ रुपये मात्र" in fake_ai[0][1]            # amount words from our own code
    assert "सेवा में," in d["text"] and "विषय: गलत बिजली बिल" in d["text"] and "संलग्न:" in d["text"]
    assert "77001234" in out["say"] or "Khaali" in out["say"]
    # revise in her words keeps everything else
    r = L.revise(T, "L-0001", "subject mein mahina bhi likho")
    assert r["doc"]["parts"]["subject"].startswith("अक्टूबर 2026") and r["doc"]["parts"]["body"] == d["parts"]["body"]
    assert r["doc"]["versions"] == 2


def test_sign_only_on_her_tap_and_hash_lock(env, fake_ai):
    L = _L()
    L.write_letter(T, "Tehsildar ko application, mera naam Sita, survey number 45/2", lang="hi")
    with pytest.raises(L.LekhakError):                    # blanks still open
        L.sign_request(T, "last") and L.decide_sign(T, "last", True)
    # she fills the blank herself
    doc = L.get_doc(T, "last")
    body = [b.replace("[मीटर नंबर]", "77001234") for b in doc["parts"]["body"]]
    L.edit(T, doc["id"], parts={"body": body, "closing": "भवदीया, सीता"})
    assert any("closing" in x for x in L.settings(T)["style"])                     # learned from her edit
    req = L.sign_request(T, doc["id"])
    assert req["doc"]["status"] == "waiting_sign" and "khud sign nahi" in req["say"]
    h = req["doc"]["checks"]["sign_hash"]
    with pytest.raises(L.LekhakError):
        L.decide_sign(T, doc["id"], True, hash="000000000000")                    # a stale card cannot sign
    with pytest.raises(L.LekhakError):
        L.decide_sign(T, doc["id"], True, mode="image", hash=h)                   # no saved signature picture
    out = L.decide_sign(T, doc["id"], True, mode="paper", hash=h)
    assert out["doc"]["status"] == "signed" and out["files"]["docx"]["file_id"]
    with pytest.raises(L.LekhakError):
        L.revise(T, doc["id"], "kuch badlo")                                       # signed = locked


def test_translation_locks_facts_and_back_checks(env, fake_ai):
    L = _L()
    L.save_settings(T, keep=["Hoola"])
    L.glossary_add(T, "तहसीलदार", "Tahsildar", "en")
    out = L.translate(T, "मेरा नाम सीता है। Hoola ऐप से ₹12,500 का बिल 28/10/2026 को भरा। केस नंबर 45/2026 अदालत में है।", to="english")
    d = out["doc"]
    assert d["kind"] == "translation" and d["status"] == "ready" and d["checks"]["locked"] >= 4
    for keep in ("₹12,500", "28/10/2026", "45/2026", "Hoola"):
        assert keep in d["text"]
    sysmsg = [c[0] for c in fake_ai if "careful Indian translator" in c[0]][0]
    assert "तहसीलदार -> Tahsildar" in sysmsg and "⟦" not in d["text"]
    assert d["checks"]["back_check"]["same"] is False and "farq" in out["say"]
    assert any("certified" in n for n in d["checks"]["notes"]) and d["checks"]["label"].startswith("Draft translation")
    with pytest.raises(L.LekhakError):
        L.translate(T, "hello", to="klingon")


def test_grammar_small_edits_only(env, fake_ai):
    L = _L()
    out = L.fix_grammar(T, "मेरी नाम सीता है। मैंने 500 रुपये जमा किया था", lang="hi")
    c = out["doc"]["checks"]
    assert out["doc"]["text"] == "मेरा नाम सीता है। मैंने 500 रुपये जमा किया था।"
    assert [e["to"] for e in c["edits"]] == ["मेरा नाम", "किया था।"] and c["refused"][0]["to"] == "5000 रुपये"
    assert c["facts_same"] is True


def test_type_krutidev_and_files_with_real_pdf(env, fake_ai):
    L = _L()
    out = L.type_text(T, "egksn;] fuosnu gS fd esjk uke lhrk gS")
    assert out["doc"]["kind"] == "convert" and out["doc"]["text"] == "महोदय, निवेदन है कि मेरा नाम सीता है"
    L.write_letter(T, "Bank ko KYC update ke liye letter, account 1234567890", lang="hi")
    f = L.make_files(T, "last")
    assert f["files"]["docx"]["file_id"]
    docx = L.make_docx("bank", "hi", L.get_doc(T, "last")["parts"])
    from docx import Document
    text = "\n".join(p.text for p in Document(io.BytesIO(docx)).paragraphs)
    assert "विषय:" in text and "सेवा में," in text
    html = L.letter_html("bank", "hi", L.get_doc(T, "last")["parts"])
    pdf = L.make_pdf(html)
    if pdf is None:
        pytest.skip("no Chromium here")
    assert pdf[:4] == b"%PDF" and "pdf" in f["files"]
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    got = "".join(doc[i].get_textpage().get_text_range() for i in range(len(doc))).replace(" ", "")
    doc.close()
    assert "विषय" in got and "सेवामें" in got                                     # real, searchable Devanagari


def test_tools_and_wiring(env, fake_ai):
    from app import voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    ctx = conv_ctx()

    def run(tool, **a):
        return asyncio.run(HANDLERS[tool](ctx, **a))
    assert run("lekhak", action="write", dictation="Principal ko 3 din ki chhutti ki application, 12/11 se 14/11")["doc"]["kind"] == "leave"
    assert run("lekhak_dekho", what="krutidev", text="Hkkjr")["text"] == "भारत"
    assert run("lekhak_dekho", what="krutidev", text="भारत", to="krutidev")["text"] == "Hkkjr"
    assert run("lekhak_dekho", what="docs")["docs"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["lekhak"](staff, action="settings", my_name="x"))
    with pytest.raises(ToolError):
        run("lekhak", action="revise", doc="L-0999", instruction="x")
    assert roles.duty_of("lekhak") == "typing" and roles.kind_of("lekhak_dekho") == "read"
    assert "typing" in roles.role_duties("typist") and roles.PRESETS["typist"]["role"] == "typist"
    assert "lekhak" in voice.VOICE_TOOL_NAMES


def test_api(env, fake_ai):
    from app import main
    with TestClient(main.app) as c:
        assert "lekhak" in c.get("/healthz").json()["features"]
        c.put("/api/lekhak/settings", json={"my_name": "Sita", "lang": "hi"})
        d = c.post("/api/lekhak/write", json={"dictation": "Society secretary ko parking complaint, flat 204"}).json()["doc"]
        assert d["number"] == "L-0001"
        assert c.post(f"/api/lekhak/docs/{d['id']}/revise", json={"instruction": "subject badlo"}).status_code == 200
        assert c.put(f"/api/lekhak/docs/{d['id']}", json={"parts": {"body": ["flat 204 ke saamne parking."]}}).status_code == 200
        r = c.post(f"/api/lekhak/docs/{d['id']}/sign_request", json={}).json()
        h = r["doc"]["checks"]["sign_hash"]
        assert c.post(f"/api/lekhak/docs/{d['id']}/sign", json={"approve": False}).json()["doc"]["status"] == "rejected"
        assert c.post("/api/lekhak/krutidev", json={"text": "fgUnh"}).json()["text"] == "हिन्दी"
        assert c.post("/api/lekhak/grammar", json={"text": "मेरी नाम सीता"}).status_code == 200
        assert c.post("/api/lekhak/contacts", json={"name": "Secretary", "lines": ["Secretary", "Shanti Society"]}).status_code == 200
        allv = c.get("/api/lekhak").json()
        assert allv["docs"] and allv["contacts"] and allv["settings"]["my_name"] == "Sita"
        assert c.post("/api/lekhak/translate", json={"text": "x", "to": ""}).status_code == 400
        del h
