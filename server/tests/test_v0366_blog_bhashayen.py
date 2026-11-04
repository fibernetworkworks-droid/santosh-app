"""v0.366 BLOG (built as 0.359) + BHASHAYEN (web design Phase 7 step 3, owner: "START PHASE 3C"): a real blog on her Hoola website and the
site in up to 4 extra languages.

BLOG: Kalam writes the post (her voice, facts checked) and gets one more place to publish, dest "site" = the blog of her
Hoola website; nothing goes up without her Haan on the card. The site then has /blog/ (newest first, 10 a page),
/blog/<post>/ (title, date, reading time, BlogPosting JSON-LD, previous / next, related), /blog/category/<cat>/,
/blog/feed.xml and the latest posts wherever a section placed <div data-hoola-posts>. A post she schedules goes up by
itself at its time; when her live address showed the version before, the new version goes there too.
BHASHAYEN: gu / bn / ta / te / kn / ml / pa / or / ur join en / hi / mr / hinglish; up to 4 extra languages, a language
menu on every page, hreflang alternates + x-default, Urdu right-to-left, blog posts translated too."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from tests.test_life import conv_ctx
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

POST = ("# Diwali ke liye mithai kaise chunein\n\nDiwali par mithai lene se pehle teen baatein dekhiye.\n\n"
        "## Taazgi\n\nHamari kaju katli roz subah banti hai.\n\n- Rang dekhiye\n- Khushboo dekhiye\n\n"
        "<script>alert(1)</script> [hamari dukaan](https://example.com) [bura link](javascript:alert(1))")


def _site(S):
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    return v["id"]


def _piece(K, title="Diwali ke liye mithai kaise chunein", body=POST, category="Tips"):
    from app.db import session
    with session() as s:
        p = K.KalamPiece(tenant_id=T, number="K-1", kind="blog", lang="hinglish", title=title, body=body,
                         meta=json.dumps({"meta_description": "Diwali par sahi mithai chunne ke teen aasaan tareeke.",
                                          "slug": "diwali-mithai", "category": category, "tags": ["Diwali", "Mithai"]}))
        s.add(p)
        s.flush()
        return p.id


@pytest.fixture
def kalam(monkeypatch):
    from app.kalam import service as K
    monkeypatch.setattr(K, "check", lambda *a, **k: {})           # the web fact-check has its own tests
    return K


def test_languages_we_know():
    from app.site import lang as LG
    assert LG.pick("gujarati aur tamil, hi") == ["gu", "ta", "hi"] and LG.pick(["ta", "xx", "ta"]) == ["ta"]
    assert LG.html_lang("hinglish") == "hi-Latn" and LG.html_lang("en") == "en-IN" and LG.html_lang("ta") == "ta"
    assert LG.MAX_EXTRA == 4 and LG.RTL == {"ur"} and {"gu", "bn", "ta", "te", "kn", "ml", "pa", "or", "ur"} <= set(LG.LANGS)


def test_a_post_reaches_her_blog_only_with_her_haan(site_env, kalam):
    from app.site import blog as BL
    from app.site import build as B
    from app.site import service as S
    sid = _site(S)
    ver = S.get(T, sid)["version"]
    pid = _piece(kalam)
    with pytest.raises(kalam.KalamError):                          # a social post is not a blog post
        _p2 = _piece(kalam, title="x")
        from app.db import session
        with session() as s:
            s.get(kalam.KalamPiece, _p2).kind = "social"
        kalam.publish_request(T, _p2, "site", "Sharma Sweets")
    req = kalam.publish_request(T, pid, "site", "Sharma Sweets")
    assert req["status"] == "waiting" and "Aapki website ka blog: Sharma Sweets (abhi)" == req["card"]["where_label"]
    assert BL.posts(sid) == [] and S.get(T, sid)["version"] == ver                 # nothing before her Haan
    with pytest.raises(kalam.KalamError):
        kalam.decide_publish(T, pid, True, card_hash="not-the-card")
    out = kalam.decide_publish(T, pid, True, card_hash=req["card"]["hash"])
    assert "website ke blog par" in out["say"] and out["published"]["slug"] == "diwali-mithai"
    g = S.get(T, sid)
    assert g["version"] == ver + 1
    o = B.out_dir(T, sid, g["version"])
    home, idx = (o / "index.html").read_text(), (o / "blog" / "index.html").read_text()
    post = (o / "blog" / "diwali-mithai" / "index.html").read_text()
    assert 'href="blog/"' in home and 'type="application/rss+xml"' in home                   # Blog in the menu + feed
    assert "Diwali ke liye mithai kaise chunein" in idx and 'href="../blog/diwali-mithai/"' in idx and "<h1>" in idx
    assert post.count("<h1>") == 1 and '"@type": "BlogPosting"' in post and '"wordCount"' in post
    assert "<h2>Taazgi</h2>" in post and "<li>Rang dekhiye</li>" in post and 'content="article"' in post
    assert "<script>alert(1)</script>" not in post and "&lt;script&gt;" in post and "javascript:" not in post
    assert 'href="https://example.com"' in post and ">Tips</a>" in post
    assert (o / "blog" / "category" / "tips" / "index.html").exists()
    feed = (o / "blog" / "feed.xml").read_text()
    assert feed.startswith('<?xml') and "<item><title>Diwali ke liye mithai kaise chunein</title>" in feed
    assert kalam.get(T, pid)["status"] == "published"


def test_scheduled_posts_pages_and_her_taps(site_env, kalam):
    from app.site import blog as BL
    from app.site import build as B
    from app.site import service as S
    sid = _site(S)
    later = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    sch = S.blog_publish(T, sid, {"title": "Holi special", "body": "Holi ki mithai ki list.\n\nGujiya aur malpua.",
                                  "meta": {"category": "Tyohar"}}, later)
    assert sch["post"]["status"] == "scheduled" and "ko website par aayega" in sch["say"]
    v0 = S.get(T, sid)["version"]
    assert not (B.out_dir(T, sid, v0) / "blog").exists()                            # not before its time
    for i in range(11):                                                           # 11 more -> two blog pages
        BL.put(T, sid, {"title": f"Post number {i}", "body": f"Likha hua {i}. " * 30, "meta": {"category": "Tips" if i % 2 else "Khabar"}})
    assert BL.due(datetime.now(timezone.utc)) == []
    assert BL.due(datetime.now(timezone.utc) + timedelta(days=3)) == [(sid, "holi-special")]
    assert S.blog_tick() == 0                                                    # already published by due() above
    S._blog_rebuild(S._load(sid), "test", live=False)
    o = B.out_dir(T, sid, S.get(T, sid)["version"])
    assert (o / "blog" / "holi-special" / "index.html").exists() and (o / "blog" / "page" / "2" / "index.html").exists()
    idx = (o / "blog" / "index.html").read_text()
    assert idx.count('class="hs-post card"') == 10 and 'rel="next" href="../blog/page/2/"' in idx
    assert (o / "blog" / "category" / "khabar" / "index.html").exists() and (o / "blog" / "category" / "tyohar" / "index.html").exists()
    post = (o / "blog" / "post-number-5" / "index.html").read_text()
    assert 'rel="prev"' in post and 'rel="next"' in post and ("Aur padhiye" in post or "More to read" in post)
    # from chat a post can be hidden (a version she makes live) but never deleted; her tap can
    out = S.blog_act(T, sid, "holi-special", "hide")
    assert "live karo" in out["say"]
    with pytest.raises(S.SiteError):
        S.blog_act(T, sid, "holi-special", "delete")
    assert not (B.out_dir(T, sid, S.get(T, sid)["version"]) / "blog" / "holi-special").exists()
    S.blog_act(T, sid, "holi-special", "delete", tapped=True)
    assert all(p["slug"] != "holi-special" for p in BL.posts(sid))
    # a section's <div data-hoola-posts="2"> = her latest posts
    html = BL.latest_cards('<section><div data-hoola-posts="2"></div></section>', BL.live_posts(sid), "", lambda n: "", "en")
    assert html.count('class="hs-post card"') == 2 and 'href="blog/"' in html
    assert "No posts yet." in BL.latest_cards('<div data-hoola-posts></div>', [], "", lambda n: "", "en")


def test_many_languages_menu_hreflang_and_translated_posts(site_env, monkeypatch, kalam):
    from app.site import ai as AI
    from app.site import blog as BL
    from app.site import build as B
    from app.site import lang as LG
    from app.site import service as S
    seen = []

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(LG.TRANSLATE_SYSTEM[:40]):
            lang = prompt.split("TARGET LANGUAGE: ", 1)[1].split(".", 1)[0]
            seen.append(("section", lang))
            return {"html": prompt.split("SECTION HTML:\n", 1)[1]}
        if system.startswith("Translate these website page titles"):
            return {"pages": {}}
        if system.startswith(BL.TRANSLATE_POST[:40]):
            lang = prompt.split("TARGET LANGUAGE: ", 1)[1].split(".", 1)[0]
            seen.append(("post", lang))
            src = json.loads(prompt.split("POST JSON:\n", 1)[1])
            return {"title": f"[{lang[:5]}] {src['title']}", "excerpt": src["excerpt"], "body": src["body"]}
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    sid = _site(S)
    S.blog_publish(T, sid, {"title": "Hamari kahani", "body": "1985 se Akot mein.", "meta": {}})
    with pytest.raises(S.SiteError):
        S.set_languages(T, sid, ["hi", "gu", "ta", "te", "kn"])                  # 4 extra at most
    with pytest.raises(S.SiteError):
        S.set_languages(T, sid, ["klingon"])
    out = S.set_languages(T, sid, ["hi", "tamil", "ur"])
    assert out["languages"][1:] == ["hi", "ta", "ur"]
    g = S.get(T, sid)
    o = B.out_dir(T, sid, g["version"])
    home = (o / "index.html").read_text()
    ta = (o / "ta" / "index.html").read_text()
    ur = (o / "ur" / "contact" / "index.html").read_text()
    assert '<details class="hs-langs">' in home and home.count('class="hs-langs"') == 1
    for code, path in (("hi", "hi/"), ("ta", "ta/"), ("ur", "ur/")):
        assert f'href="{path}" hreflang="{code}"' in home
    assert 'lang="ta"' in ta and 'href="../" hreflang="' in ta and 'aria-current="true">தமிழ்' in ta
    assert '<html lang="ur" dir="rtl">' in ur and 'href="../../contact/"' in ur                 # the same page, back home
    assert {("section", "Tamil in Tamil script"), ("post", "Tamil in Tamil script")} <= set(seen)
    tpost = (o / "ta" / "blog" / "hamari-kahani" / "index.html").read_text()
    assert "[Tamil] Hamari kahani" in tpost and '<html lang="ta"' in tpost
    # hreflang alternates need the real address: the live build has them, with x-default = the first language
    ctx = S._ctx(S._load(sid))
    live = o.parent / "live-check"
    B.assemble({**ctx, "noindex": False}, ctx["plan"], S._sections(S._load(sid)), {}, live, "https://sharma.example", "")
    lh = (live / "ta" / "blog" / "hamari-kahani" / "index.html").read_text()
    for code, path in (("hi-Latn", ""), ("hi", "hi/"), ("ta", "ta/"), ("ur", "ur/")):   # her first language = Hinglish
        assert f'<link rel="alternate" hreflang="{code}" href="https://sharma.example/{path}blog/hamari-kahani/">' in lh
    assert 'hreflang="x-default" href="https://sharma.example/blog/hamari-kahani/"' in lh
    assert "<loc>https://sharma.example/blog/hamari-kahani/</loc>" in (live / "sitemap.xml").read_text()
    assert "<link>https://sharma.example/ta/blog/hamari-kahani/</link>" in (live / "ta" / "blog" / "feed.xml").read_text()
    # back to two languages: one plain link as in v0.301; none = no switch at all
    S.set_languages(T, sid, ["hi"])
    o2 = B.out_dir(T, sid, S.get(T, sid)["version"])
    h2 = (o2 / "index.html").read_text()
    assert 'class="hs-lang" href="hi/" hreflang="hi"' in h2 and "hs-langs" not in h2 and not (o2 / "ta").exists()


def test_api_and_tools(site_env, kalam):
    from fastapi.testclient import TestClient
    from app.agent import kalam_tools as KT
    from app.agent import site_tools as ST
    from app.main import app, current_tenant
    from app.site import service as S
    sid = _site(S)
    S.blog_publish(T, sid, {"title": "Pehla post", "body": "Namaste.", "meta": {}})
    c = TestClient(app)
    b = c.get(f"/api/sites/{sid}/blog").json()
    assert [p["slug"] for p in b["posts"]] == ["pehla-post"] and b["max_extra"] == 4 and any(x["code"] == "ta" for x in b["choices"])
    assert "body" not in b["posts"][0]
    assert c.post(f"/api/sites/{sid}/blog/pehla-post", json={"action": "hide"}).json()["post"]["status"] == "hidden"
    assert c.post(f"/api/sites/{sid}/languages", json={"languages": ["hi"]}).json()["languages"][1:] == ["hi"]
    app.dependency_overrides[current_tenant] = lambda: "someone-else"
    try:
        assert c.get(f"/api/sites/{sid}/blog").status_code in (400, 403, 404)
        assert c.post(f"/api/sites/{sid}/blog/pehla-post", json={"action": "delete"}).status_code in (400, 403, 404)
    finally:
        app.dependency_overrides.pop(current_tenant, None)
    tool = next(t for t in ST.SITE_TOOLS if t["name"] == "website")
    assert {"languages", "blog"} <= set(tool["input_schema"]["properties"]["action"]["enum"])
    assert "kalam action=publish dest=site" in tool["description"]
    assert "dest site|wordpress" in KT.KALAM_TOOLS[0]["description"]


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.494.0"
    assert "0.494.0+538" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
