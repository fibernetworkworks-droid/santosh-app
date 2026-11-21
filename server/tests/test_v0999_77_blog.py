"""v0.999.77 D8 wave 2 (docs/WEB_DESIGN_ENGINE_PLAN.md phase D8): her blog on the React website - every published post
is its own pre-rendered page (Google reads it) and the Blog page lists them; a post she publishes, hides or deletes
(in the Studio, from Kalam's card, the CMS team or at its scheduled time) changes the React website by code, Rs 0. The
post's text is turned into plain headings, paragraphs, lists and quotes in code: nothing from the post is drawn as
HTML."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.appengine import parity as PY
from app.appengine import writer as W
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v0999_77_features import _pages, _serve
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_AUTOFIX", "true")
    monkeypatch.setenv("STUDIO_REACT_SITES", "true")
    monkeypatch.setenv("SITE_CRITIC", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


POST_MD = """# Why our dough rests

A slow **rise** gives an [open crumb](https://example.com).
It keeps longer too.

## The three days
- Mixed in the afternoon
- Shaped the next *morning*
1. Baked at dawn

> Good bread cannot be hurried.

<script>alert("x")</script> after the tag
"""


def _post(**kw):
    p = {"slug": "why-our-dough-rests", "title": "Why our dough rests", "excerpt": "A slow rise.", "date": "12 Nov 2026",
         "published_at": "2026-11-12T03:00:00+00:00", "category": "Baking", "author": "Asha", "minutes": 2,
         "body": POST_MD}
    p.update(kw)
    return p


# ---------------------------------------------------------------- 1. the post becomes plain parts, by code
def test_her_post_becomes_plain_parts_never_html():
    parts = W.md_parts(POST_MD)
    kinds = [p["k"] for p in parts]
    assert kinds == ["h2", "p", "h2", "li", "li", "ol", "quote", "p"]
    assert parts[1]["t"] == "A slow rise gives an open crumb. It keeps longer too."
    assert all("<" not in p["t"] and "**" not in p["t"] and "](" not in p["t"] for p in parts)
    assert parts[-1]["t"] == 'alert("x") after the tag'              # words stay words: React draws them as text
    assert len(W.md_parts("para\n\n" * 1000)) == W.MAX_PARTS


def test_posts_are_made_safe_and_the_blog_page_is_added_only_when_needed():
    got = W.posts_of([_post(), _post(slug="../../etc/passwd", title="<b>Bold</b> move"), _post(), {"slug": "x"}, "junk"])
    assert [p["slug"] for p in got] == ["why-our-dough-rests", "etcpasswd"]
    assert got[1]["title"] == "Bold move" and got[0]["iso"] == "2026-11-12"
    pages = _pages()
    same, slug = W.with_blog(pages, [])
    assert same is pages and slug == ""
    more, slug = W.with_blog(pages, got)
    assert slug == "blog" and more[-1]["nav"] == "Blog" and pages == _pages()        # her prototype is never changed
    own = [*pages, {"slug": "blog", "title": "News", "sections": [{"type": "hero", "heading": "x"}]},
           {"slug": "notes", "title": "Notes", "sections": [{"type": "blog_list", "heading": "Notes"}]}]
    assert W.with_blog(own, got) == (own, "notes")                    # her own posts page is the blog


def test_the_writer_makes_a_page_per_post_and_lists_them():
    from app.appengine import image as IMG
    from app.appengine import rules as RL
    ctx = W.Ctx("Sunrise Bakery", _pages(), {"_site": {"id": "site_abc", "posts": [_post(), _post(slug="flour")]}}, "s")
    files, rows = W.plan_files(_pages(), ctx)
    app = files["src/App.tsx"]
    assert '<Route path="/blog" element={<BlogPage />} />' in app
    assert '<Route path="/blog/why-our-dough-rests" element={<BlogPostWhyOurDoughRestsPage />} />' in app
    assert '<Route path="/blog/flour" element={<BlogPostFlourPage />} />' in app
    post = files["src/pages/BlogPostWhyOurDoughRestsPage.tsx"]
    assert 'import post from "@/data/posts/why-our-dough-rests.json";' in post and "<Article {...post.article} />" in post
    assert "dough" not in post.split("export default")[1] and "dangerouslySetInnerHTML" not in post   # her words: data
    data = json.loads(files["src/data/posts/why-our-dough-rests.json"])
    assert data["seo"]["jsonLd"]["@type"] == "BlogPosting" and data["seo"]["jsonLd"]["datePublished"] == "2026-11-12"
    assert {"k": "quote", "t": "Good bread cannot be hurried."} in data["article"]["parts"]
    assert data["article"]["back"] == {"label": "All posts", "href": "./blog"}
    listing = files["src/pages/BlogPage.tsx"]
    assert 'import blogPosts from "@/data/blog.json";' in listing and "posts={blogPosts}" in listing
    rows_data = json.loads(files["src/data/blog.json"])
    assert [x["href"] for x in rows_data] == ["./blog/why-our-dough-rests", "./blog/flour"]
    assert '"to": "/blog", "label": "Blog"' in files["src/components/site/Layout.tsx"]
    assert any(r["page"] == "blog" and r["block"] == "blog_list" for r in rows)
    deps = set(IMG.CORE) | set(IMG.DEV)
    for rel in sorted(files):                       # her words (alert(...) in the post) never trip the code rules
        assert RL.check_file(rel, files[rel], deps) == [], rel
    art = (ROOT / "server/app/appengine/template/src/components/blocks/article.tsx").read_text()
    assert RL.check_file("src/components/blocks/article.tsx", art, deps) == []
    assert "src/components/blocks/article.tsx" in W.kit_files(rows, False, True)
    assert "src/components/blocks/article.tsx" not in W.kit_files(rows, False, False)


def test_no_posts_writes_the_site_as_before():
    ctx = W.Ctx("Sunrise Bakery", _pages(), {"_site": {"id": "site_abc"}}, "s")
    files, _ = W.plan_files(_pages(), ctx)
    assert sorted(files) == ["src/App.tsx", "src/components/site/Layout.tsx", "src/pages/HomePage.tsx",
                             "src/pages/NotFoundPage.tsx"]


def test_the_checklist_says_the_blog_works():
    st = {r["key"]: r for r in PY.check()["rows"]}
    assert st["blog"]["state"] == "works", st["blog"]          # cover photos came in wave 4 (same release)


# ---------------------------------------------------------------- 2. a real React website: publish, read, hide
@pytest.fixture
def blog_site(ae_env, monkeypatch):
    _box()
    from app.site import ai as AI
    from app.site import prototype as PT
    from app.site import service as S
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    v = S.new(T, "A website for Sunrise Bakery in Pune: breads and cakes.", name="Sunrise Bakery")
    PT._write_version(S._load(v["id"]), _pages(), "test", "hoola")
    PT.approve(T, v["id"], PT.meta(S._load(v["id"]))["hash"])
    out = S.view(S._load(v["id"]))
    assert out["status"] == "ready", out.get("error")
    return v["id"], out["react"]["id"]


def test_her_post_reaches_the_react_site_and_leaves_with_a_hide(blog_site):
    from playwright.sync_api import sync_playwright
    from app.appengine import service as AE
    from app.appengine import speed as SP
    from app.site import service as S
    sid, ref = blog_site
    S.blog_publish(T, sid, {"title": "Why our dough rests", "body": POST_MD, "meta": {"category": "Baking"}})
    st = AE.wait_build(T, ref, timeout=240)
    app = AE._load(T, ref)
    assert app.version and not app.dirty, st
    src = AE.src_dir(app) / "src" / "pages"
    assert (src / "BlogPostWhyOurDoughRestsPage.tsx").exists()
    dist = AE.ver_dir(app, app.version) / "dist"
    html = (dist / "blog" / "why-our-dough-rests" / "index.html").read_text()     # pre-rendered: Google reads it
    assert "Why our dough rests" in html and "Good bread cannot be hurried." in html and "<script>alert" not in html
    assert "BlogPosting" in html
    srv, base = _serve(dist)
    errors: list[str] = []
    try:
        with sync_playwright() as pw:
            b = SP._browser(pw)
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(base, wait_until="load")
            pg.get_by_role("link", name="Blog").first.click()
            pg.get_by_role("link", name="Why our dough rests").first.click()
            pg.get_by_role("heading", name="Why our dough rests", level=1).wait_for(timeout=15000)
            assert pg.get_by_text("Mixed in the afternoon").is_visible()
            pg.get_by_role("link", name="All posts").first.click()
            pg.get_by_role("heading", name="Blog").first.wait_for(timeout=15000)
            b.close()
    finally:
        srv.shutdown()
    assert not errors, errors
    S.blog_act(T, sid, "why-our-dough-rests", "hide", tapped=True)                # off the site: its page goes too
    AE.wait_build(T, ref, timeout=240)
    assert not (src / "BlogPostWhyOurDoughRestsPage.tsx").exists()
    assert "/blog/why-our-dough-rests" not in (AE.src_dir(AE._load(T, ref)) / "src" / "App.tsx").read_text()
