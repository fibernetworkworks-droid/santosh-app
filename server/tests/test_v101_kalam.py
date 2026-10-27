"""v0.101 Kalam Sahayak (content writer): her brand voice, her facts only, claims checked (web + law), publishing only on
her tap (WordPress / email card / Hoola page / she pastes it herself)."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import EmailDraft, Event, session
from tests.test_life import conv_ctx

T = "default"
PROMPTS: list[tuple[str, str]] = []


def _K():
    from app.kalam import service as K
    return K


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


BLOG = ("# Fibre internet ghar ke liye\n\nIn today's fast-paced world, internet zaroori hai. Hamara 100 Mbps plan Rs 499 mahina hai.\n\n"
        "## Kyun fibre\n\nHum Akola ke No. 1 internet provider hain.\n\n[Aapka apna anubhav: ...]\n\n## Sampark\n\nCall karein.")


@pytest.fixture
def fake_ai(monkeypatch):
    K = _K()
    PROMPTS.clear()

    def ai(system, prompt, max_tokens=3000):
        PROMPTS.append((system, prompt))
        if "You study how" in system:
            return json.dumps({"summary": "Seedhi, dosti wali Hinglish, aap", "person": "aap", "notes": ["chhote vaakya"],
                               "phrases": ["bilkul tension mat lijiye"], "avoid": ["sasta"]})
        if "edited a draft" in system:
            return json.dumps({"notes": ["Lambi bhumika nahi; seedha kaam ki baat"]})
        if "You check one claim" in system:
            if "10 guna" in prompt:
                return json.dumps({"verdict": "contradicted", "why": "TRAI data alag kehta hai", "url": "https://example.org/trai"})
            return json.dumps({"verdict": "supported", "why": "mila", "url": "https://example.org/x"})
        if "Suggest content ideas" in system:
            return json.dumps({"ideas": [{"title": "Diwali par fibre offer", "kind": "email", "why": "tyohar", "date": ""}]})
        if "You revise a draft" in system:
            cur = json.loads(prompt.split("CURRENT DRAFT (JSON):\n", 1)[1])
            body = cur["body"].replace("Hum Akola ke No. 1 internet provider hain.", "Akola mein 2,000 ghar humse jude hain.")
            return json.dumps({"title": cur["title"], "body": body, "meta": cur["meta"], "notes": []})
        if "careful content writer" in system:
            if "KIND: product" in prompt:
                return json.dumps({"title": "Aai's Kesar Shrikhand 500 g", "body": "- Asli kesar\n- 500 g dabba\n\nGhar jaisa shrikhand.",
                                   "meta": {"meta_title": "Kesar Shrikhand 500 g", "search_keywords": ["shrikhand"]}, "notes": []})
            if "KIND: email" in prompt:
                return json.dumps({"title": "Diwali offer", "body": "Namaste,\n\nIs Diwali 20% chhoot. [Offer ki aakhri tareekh]\n\nAsha",
                                   "meta": {"subject": "Diwali par 20% chhoot", "preheader": "Sirf hamare graahakon ke liye"},
                                   "notes": []})
            if "KIND: social" in prompt:
                return json.dumps({"title": "Naya plan", "body": "Naya 100 Mbps plan aa gaya!",
                                   "meta": {"captions": {"instagram": "Naya plan aa gaya #fibre", "x": "Naya plan"}}, "notes": []})
            return json.dumps({"title": "Fibre internet ghar ke liye", "body": BLOG,
                               "meta": {"meta_title": "Fibre internet Akola: 100 Mbps Rs 499",
                                        "meta_description": "Akola mein ghar ke liye fibre internet: 100 Mbps plan Rs 499 mahina, "
                                                            "jaldi installation aur local support. Aaj hi call karein.",
                                        "slug": "Fibre Internet Akola", "image_ideas": [{"idea": "router photo", "alt": ""}]},
                               "notes": ["apna anubhav jodiye"]})
        return "{}"
    monkeypatch.setattr(K, "_ai", ai)

    async def search_any(q):
        return {"query": q, "answer": "", "sources": [{"title": "x", "url": "https://example.org/x"}],
                "excerpts": [{"title": "x", "url": "https://example.org/x", "excerpts": ["some text"]}]}
    from app import web
    monkeypatch.setattr(web, "search_any", search_any)
    return ai


def test_helpers():
    K = _K()
    h = K.to_html("# T\n\n<script>alert(1)</script> **b** [ok](https://a.in) [bad](javascript:x)\n\n- a\n- b\n\n| a | b |\n|---|---|\n| 1 | 2 |")
    assert "<script>" not in h and "&lt;script&gt;" in h and '<a href="https://a.in">ok</a>' in h and "javascript" not in h
    assert "<ul><li>a</li><li>b</li></ul>" in h and "<td>1</td>" in h
    assert K.guess_kind("diwali offer ka email likho") == "email"
    assert K.guess_kind("is saree ka amazon listing") == "product"
    assert K.guess_kind("blog: fibre vs airfiber") == "blog"
    c = K.claims_of("Yeh tel diabetes theek karta hai. Hum India ke No. 1 brand hain. Daam Rs 299.")
    kinds = {k for x in c for k in x["kinds"]}
    assert {"disease", "superlative", "price"} <= kinds
    assert K.blanks("Hello [naam] aur [link](https://x.in)") == ["[naam]"]


def test_voice_write_and_checks(env, fake_ai):
    K = _K()
    K.save_settings(T, business="Asha Fibernet", dont_words=["sasta"], address="Akot, Akola 444101", cta="Call karein",
                    contact="98xxxxxx10")
    K.add_fact(T, "100 Mbps plan Rs 499 mahina", "rate card")
    v = K.learn_voice(T, text="Namaste! Bilkul tension mat lijiye, aapka connection 24 ghante mein lag jayega. Aap call kariye.")
    assert v["voice"]["person"] == "aap" and "sasta" in v["voice"]["avoid"]
    r = K.write(T, "Blog likho: ghar ke liye fibre internet kyun", keyword="fibre internet")
    p = r["piece"]
    assert p["kind"] == "blog" and p["number"] == "C-0001"
    wp = [x for x in PROMPTS if "careful content writer" in x[0]][-1][1]
    assert "NEVER use: sasta" in wp and "100 Mbps plan Rs 499" in wp and "bilkul tension mat lijiye" in wp
    assert "fast-paced" not in p["body"]                      # filler opener dropped
    assert p["meta"]["slug"] == "fibre-internet-akola"
    items = p["checks"]["items"]
    assert any(i["level"] == "block" and i["area"] == "khaali" for i in items)      # her experience still blank
    assert any(i["area"] == "daava" and "No 1" in i["text"] for i in items)        # superlative needs proof
    backed = [c for c in p["checks"]["claims"] if "499" in c["text"]]
    assert backed and backed[0]["verdict"] == "backed"
    assert any(e["number"] == "C-0001" for e in _events("kalam_piece"))


def test_revise_edit_learn_check_and_publish_page(env, fake_ai):
    K = _K()
    K.save_settings(T, business="Asha Fibernet")
    p = K.write(T, "Blog: fibre internet")["piece"]
    r = K.revise(T, p["id"], "No. 1 wali line hata kar asli ginti likho")
    assert "2,000 ghar" in r["piece"]["body"]
    body = r["piece"]["body"].replace("[Aapka apna anubhav: ...]", "Maine 2019 mein pehla connection khud lagaya tha.")
    body += "\n\nFibre copper se 10 guna tez hai."
    e = K.edit(T, p["id"], body=body)
    assert e["learned"] and "Lambi bhumika" in K.settings(T)["voice"]["learned"][0]
    with pytest.raises(K.KalamError):
        K.decide_publish(T, p["id"], True)                  # nothing asked yet
    blocked = K.publish_request(T, p["id"], "page")
    assert blocked["status"] == "blocked" and any("galat" in b["text"] for b in blocked["blockers"])
    K.edit(T, p["id"], body=body.replace("\n\nFibre copper se 10 guna tez hai.", ""))
    req = K.publish_request(T, p["id"], "page")
    assert req["status"] == "waiting"
    card = _events("kalam_publish")[-1]
    assert card["where_label"].startswith("Hoola") and card["hash"]
    with pytest.raises(K.KalamError):
        K.decide_publish(T, p["id"], True, card_hash="old")
    done = K.decide_publish(T, p["id"], True, card_hash=card["hash"])
    url = done["published"]["url"]
    token = url.rsplit("/", 1)[1]
    html = K.page_by_token(token)
    assert html and "2019" in html and "<script" not in html
    from app import main
    with TestClient(main.app) as c:
        resp = c.get(f"/api/kalam/page/{token}")
        assert resp.status_code == 200 and "default-src 'none'" in resp.headers["content-security-policy"]
    with pytest.raises(K.KalamError):
        K.revise(T, p["id"], "kuch badlo")                  # published = locked
    K.unpublish_page(T, p["id"])
    assert K.page_by_token(token) is None


def test_changed_after_card_needs_new_card(env, fake_ai):
    K = _K()
    p = K.write(T, "Blog: fibre")["piece"]
    K.edit(T, p["id"], body=p["body"].replace("[Aapka apna anubhav: ...]", "Mera anubhav."))
    assert K.publish_request(T, p["id"], "copy", where="instagram")["status"] == "waiting"
    K.edit(T, p["id"], body="# Naya\n\nBilkul alag text.")
    with pytest.raises(K.KalamError):
        K.decide_publish(T, p["id"], True)
    assert K.get(T, p["id"])["status"] == "draft"


def test_product_page_legal_metrology_and_disease(env, fake_ai):
    K = _K()
    p = K.write(T, "Kesar shrikhand ka product page", kind="product", product={"generic_name": "Shrikhand", "net_quantity": "500 g"})["piece"]
    lm = [i for i in p["checks"]["items"] if i["area"] == "kanoon"]
    assert lm and lm[0]["level"] == "block" and "MRP" in lm[0]["text"] and "FSSAI" in lm[0]["text"]
    full = {"maker": "Aai Foods, Akola", "generic_name": "Shrikhand", "net_quantity": "500 g", "mrp": "Rs 180", "made_on": "10/2026",
            "origin": "India", "care": "Aai Foods, 9800000000, care@aai.in", "fssai": "11521999000123", "best_before": "15 din"}
    p2 = K.write(T, "Kesar shrikhand product page", kind="product", product=full)["piece"]
    assert not [i for i in p2["checks"]["items"] if i["area"] == "kanoon"]
    K.edit(T, p2["id"], body=p2["body"] + "\n\nYeh shrikhand diabetes theek karta hai.")
    p3 = K.get(T, p2["id"])
    assert any(i["level"] == "block" and "Magic Remedies" in i["fix"] for i in p3["checks"]["items"])


def test_email_goes_to_the_normal_email_card(env, fake_ai):
    K = _K()
    p = K.write(T, "Diwali offer ka email")["piece"]
    assert p["kind"] == "email" and p["meta"]["subject"]
    assert any(i["area"] == "email" and "pata" in i["text"] for i in p["checks"]["items"])
    with pytest.raises(K.KalamError):
        K.publish_request(T, p["id"], "email", to=["a@x.com"])          # blank still there
    K.edit(T, p["id"], body=p["body"].replace("[Offer ki aakhri tareekh]", "Offer 2 Nov tak."))
    with pytest.raises(K.KalamError):
        K.publish_request(T, p["id"], "email", to=["not-an-email"])
    K.save_settings(T, address="Akot, Akola 444101", business="Asha Fibernet")
    r = K.publish_request(T, p["id"], "email", to=["a@x.com", "b@y.com"])
    assert r["status"] == "waiting"
    with session() as s:
        d = s.scalars(select(EmailDraft)).first()
        assert d.to_addr == "a@x.com" and "b@y.com" in d.bcc_addr and "UNSUBSCRIBE" in d.body and "Akola 444101" in d.body
        assert d.status == "pending"
        d.status = "sent"
    assert K.get(T, p["id"])["status"] == "published"
    assert _events("email_draft")


def test_social_paid_needs_ad_first_line(env, fake_ai):
    K = _K()
    p = K.write(T, "Insta post: naya plan, sponsored by Router Co", kind="social", paid=True)["piece"]
    assert all(v.startswith("#Ad") for v in p["meta"]["captions"].values()) and p["body"].startswith("#Ad")
    q = K.write(T, "Insta post naya plan", kind="social")["piece"]
    K.edit(T, q["id"], body=q["body"] + " In partnership with Router Co.")
    assert any(i["level"] == "block" and "#Ad" in i["text"] for i in K.get(T, q["id"])["checks"]["items"])


def test_copying_from_a_source_is_blocked(env, fake_ai, monkeypatch):
    K = _K()
    src = ("Hamara fibre network poore shehar mein faila hai aur har ghar tak seedha optical cable aati hai jisse speed kabhi kam "
           "nahi hoti aur barish mein bhi connection bana rehta hai kyunki fibre par paani ka asar nahi padta hai yeh sach hai")
    p = K.write(T, "Blog: fibre")["piece"]
    with session() as s:
        row = s.get(K.KalamPiece, p["id"])
        row.sources = json.dumps([{"label": "competitor.in", "text": src, "url": "https://competitor.in"}])
    K.edit(T, p["id"], body=p["body"] + "\n\n" + src)
    assert any(i["area"] == "naya" and i["level"] == "block" for i in K.get(T, p["id"])["checks"]["items"])


def test_wordpress_publish_on_her_tap(env, fake_ai, monkeypatch):
    K = _K()
    calls = []

    def wp(method, url, user, pw, body=None):
        calls.append((method, url, user, pw, body))
        return {"id": 77, "link": "https://ashafibernet.in/fibre", "status": (body or {}).get("status", "")}
    monkeypatch.setattr(K, "_wp_request", wp)
    from app import web
    monkeypatch.setattr(web, "_check_url", lambda u: u)
    with pytest.raises(K.KalamError):
        K.set_wordpress(T, "http://ashafibernet.in", "asha", "abcd efgh ijkl mnop qrst uvwx")
    with pytest.raises(K.KalamError):
        K.set_wordpress(T, "https://ashafibernet.in", "asha", "mypassword")
    K.set_wordpress(T, "https://ashafibernet.in", "asha", "abcd efgh ijkl mnop qrst uvwx")
    st = K.settings(T)
    assert st["wordpress"]["ready"] and "abcd" not in json.dumps(st)
    p = K.write(T, "Blog: fibre")["piece"]
    K.edit(T, p["id"], body=p["body"].replace("[Aapka apna anubhav: ...]", "Mera anubhav."))
    r = K.publish_request(T, p["id"], "wordpress", status="future", when="kal 10 baje")
    assert r["status"] == "waiting" and r["card"]["opts"]["date"].endswith("10:00:00")
    assert len(calls) == 1                                # only the login test so far: nothing posted before her tap
    done = K.decide_publish(T, p["id"], True, card_hash=r["card"]["hash"])
    m, url, user, pw, body = calls[-1]
    assert m == "POST" and url.endswith("/wp-json/wp/v2/posts") and pw == "abcd efgh ijkl mnop qrst uvwx"
    assert body["status"] == "future" and "<h2>" in body["content"] and body["slug"] == "fibre-internet-akola"
    assert done["published"]["url"] == "https://ashafibernet.in/fibre"
    K.result(T, p["id"], views=900, clicks=40, orders=3)
    K.write(T, "Blog: airfiber")
    assert "Her best performing" in [x for x in PROMPTS if "careful content writer" in x[0]][-1][1]


def test_tools_wiring_and_api(env, fake_ai):
    from app import voice
    from app.agent import prompts
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    ctx = conv_ctx()

    def run(tool, **a):
        return asyncio.run(HANDLERS[tool](ctx, **a))
    r = run("kalam", action="write", brief="Diwali offer ka email")
    num = r["piece"]["number"]
    assert run("kalam_dekho", what="piece", piece=num)["kind"] == "email"
    assert run("kalam", action="check", piece=num)["summary"]["claims"] >= 1
    assert run("kalam_dekho", what="ideas")["ideas"]
    with pytest.raises(ToolError):
        run("kalam", action="wordpress", url="https://x.in")          # password never through chat
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["kalam"](staff, action="settings", business="x"))
    assert run("kalam", action="repurpose", piece=num, kinds=["social"])["made"][0]["kind"] == "social"
    assert roles.duty_of("kalam") == "content_writing" and roles.kind_of("kalam_dekho") == "read"
    assert roles.PRESETS["content"]["role"] == "content_writer"
    assert "kalam" in voice.VOICE_TOOL_NAMES
    assert "Content writing" in prompts.SYSTEM if hasattr(prompts, "SYSTEM") else True
    from app import main
    with TestClient(main.app) as c:
        assert "kalam" in c.get("/healthz").json()["features"]
        c.put("/api/kalam/settings", json={"business": "Asha Fibernet", "tone": ["dosti wala"]})
        w = c.post("/api/kalam/write", json={"brief": "Blog: fibre", "kind": "blog"}).json()["piece"]
        assert c.get(f"/api/kalam/pieces/{w['id']}").json()["title"]
        assert c.post(f"/api/kalam/pieces/{w['id']}/check", json={}).json()["summary"]["web_checked"]
        f = c.post(f"/api/kalam/pieces/{w['id']}/files", json={}).json()["files"]
        assert {"docx", "html", "md"} <= set(f)
        assert c.post(f"/api/kalam/pieces/{w['id']}/publish", json={"dest": "nowhere"}).status_code == 400
        assert len(c.get("/api/kalam").json()["pieces"]) >= 3
        assert c.get("/api/kalam/page/nope").status_code == 404
        assert c.delete(f"/api/kalam/pieces/{w['id']}").status_code == 200
