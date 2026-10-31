"""v0.315 BADI WEBSITE (web design Phase 6 step 1): a big site is planned as a whole site map by Opus - designed pages in
menu groups, sub pages, and LISTS (collections) whose items become pages from ONE designed template, filled by code.
These tests drive the real builder with a fake Opus: the site map is cleaned to what the builder can trust, a 60-page
site builds with AI calls only for designed sections (never per item), every item page is filled (no {{placeholder}}
left, a value nobody gave shows as a [blank], attributes stay valid), big-site navigation (grouped menu, breadcrumbs,
search index, sitemap) works, every internal link resolves, chat can add list items without new AI sections, and
section ids with '-' in the page slug map back for fix rounds."""
import json
import re

import pytest

from tests.test_v121_site import T, good_section, site_env, _sid  # noqa: F401  (fixture)

SWEETS = ["Kaju Katli", "Motichoor Laddoo", "Rasgulla", "Gulab Jamun", "Soan Papdi", "Peda", "Barfi", "Jalebi",
          "Rasmalai", "Mysore Pak", "Besan Laddoo", "Kalakand", "Cham Cham", "Malpua", "Ghevar", "Imarti",
          "Balushahi", "Petha", "Sandesh", "Khaja", "Shrikhand", "Modak", "Anarsa", "Chikki", "Til Laddoo",
          "Coconut Barfi", "Milk Cake", "Dodha Barfi", "Kesar Peda", "Dry Fruit Roll", "Pista Roll", "Angoori Rabdi",
          "Kheer Kadam", "Rajbhog", "Chhena Poda", "Lassi", "Shahi Tukda", "Gajar Halwa", "Moong Dal Halwa", "Pinni",
          "Kulfi", "Falooda", "Badam Halwa", "Kaju Roll", "Anjeer Barfi"]
AREAS = ["Akot Bazar", "Station Road", "Civil Lines", "Ram Nagar", "Gandhi Chowk"]


def _sitemap_raw():
    return {"pages": [
        {"slug": "home", "title": "Sharma Sweets", "nav": "Home", "sections": [
            {"type": "hero", "design": "big"}, {"type": "products_grid"}, {"type": "reviews"}, {"type": "cta_band"}]},
        {"slug": "our-story", "title": "Our story", "nav": "Story", "group": "About", "sections": [
            {"type": "hero"}, {"type": "timeline_history"}, {"type": "team"}]},
        {"slug": "how-we-make", "title": "How we make sweets", "nav": "Kitchen", "group": "About", "parent": "our-story",
         "sections": [{"type": "process_steps"}]},
        {"slug": "gift-boxes", "title": "Gift boxes", "nav": "Gifts", "group": "Shop", "sections": [{"type": "offers_banner"}]},
        {"slug": "contact", "title": "Contact", "nav": "Contact", "sections": [{"type": "hero"}, {"type": "contact_block"}, {"type": "map_hours"}]},
        {"slug": "privacy", "title": "should be dropped (legal is Hoola's)"},
        {"slug": "our-story", "title": "duplicate slug, dropped"},
        {"slug": "bad", "title": "Bad types", "group": "Shop", "sections": [{"type": "not_a_type"}, {"type": "faq"}, {"type": "faq"}]}],
        "collections": [
            {"key": "sweets", "label": "Our sweets", "item_label": "Sweet", "group": "Shop",
             "fields": [{"key": "price", "label": "Price"}, {"key": "made_with", "label": "Made with"}, {"key": "title", "label": "x"}],
             "items": [{"title": n, "data": {"made_with": "desi ghee" if i % 2 == 0 else "", "price": ""}} for i, n in enumerate(SWEETS)],
             "template": [{"type": "hero", "design": "item header"}, {"type": "features_split"}, {"type": "cta_band"}]},
            {"key": "areas", "label": "Areas we deliver", "fields": [{"key": "time", "label": "Delivery time"}],
             "items": [{"title": a, "data": {"time": "45 min"}} for a in AREAS], "template": [{"type": "hero"}, {"type": "coverage_areas"}]},
            {"key": "empty", "label": "No items", "items": []}],
        "notes": "About / Shop / lists"}


class BigFake:
    """Opus stand-in: the site map call gets a site map; template sections get {{placeholders}} (text + an attribute)."""
    def __init__(self, base, raw=None):
        self.base, self.raw, self.maps = base, raw or _sitemap_raw(), 0

    def __call__(self, system, prompt, max_tokens=6000, kind="build", **kw):
        from app.site import sitemap as SM
        if system.startswith(SM.SITEMAP_SYSTEM[:40]):
            self.maps += 1
            assert "PAGES WANTED: about 60" in prompt and "SECTION TYPES:" in prompt
            return json.loads(json.dumps(self.raw))
        out = self.base(system, prompt, max_tokens, kind)
        m = re.search(r"SECTION_ID: ([\w-]+)", prompt)
        if m and "THIS IS A TEMPLATE" in prompt and out.get("html"):
            sid = m.group(1)
            fields = re.findall(r"\{\{(\w+)\}\} for", prompt)
            add = "".join(f'<p class="f-{f}">{{{{{f}}}}}</p>' for f in fields)
            out = {**out, "html": out["html"].replace(
                "</div></section>", f'<p class="itm" aria-label="About {{{{title}}}}">{{{{title}}}}</p>{add}'
                                   '<a class="back" href="../">All</a></div></section>')}
        if m and "INTERNAL LINKS" in prompt and out.get("html") and "hero" not in m.group(1):
            hrefs = re.findall(r"= ((?:\.\./)*[\w-]*/?|\./)(?:;|\.$)", prompt.split("INTERNAL LINKS", 1)[1].split("\n", 1)[0])
            if hrefs:
                out = {**out, "html": out["html"].replace("</div></section>", f'<a class="nx" href="{hrefs[0]}">Next</a></div></section>')}
        return out


def test_wanted_and_clean_rules(monkeypatch):
    monkeypatch.setenv("SITE_MAX_PAGES", "30")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import library as L
    from app.site import service as S
    from app.site import sitemap as SM
    assert SM.wanted("mujhe 100 pages ki website chahiye") == 30           # capped at the maximum
    assert SM.wanted("60 page wali site") == 30 and SM.wanted("badi website banao") == 25
    assert SM.wanted("bakery ki website") == 0 and SM.wanted("5 pages") == 0
    br = L.brief("sweet_shop")
    base = S.make_plan(br, {})
    plan = SM.clean(_sitemap_raw(), br, base, 30)
    slugs = [p["slug"] for p in plan["pages"]]
    assert slugs[0] == "home" and slugs.count("our-story") == 1 and "privacy" in slugs and "empty" not in slugs
    assert slugs.count("privacy") == 1                                      # her map's 'privacy' dropped, Hoola's kept
    bad = next(p for p in plan["pages"] if p["slug"] == "bad")
    assert [s["type"] for s in bad["sections"]] == ["hero", "faq"]           # unknown type gone, duplicate gone, hero first
    assert next(p for p in plan["pages"] if p["slug"] == "how-we-make")["parent"] == "our-story"
    sw = next(c for c in plan["collections"] if c["key"] == "sweets")
    assert [f["key"] for f in sw["fields"]] == ["price", "made_with"]        # 'title' is reserved
    z = SM.counts(plan)
    assert z["total"] <= 30 + z["legal"] and z["designed"] + z["items"] <= 30   # items trimmed to the room left
    tpl = next(p for p in plan["pages"] if p.get("template_of") == "sweets")
    assert tpl["slug"] == "sweets-item" and [s["type"] for s in tpl["sections"]] == ["hero", "features_split", "cta_band"]
    assert any(p["slug"] == "sweets" and p.get("collection") == "sweets" for p in plan["pages"])   # listing page added
    # filling: text escaped, a missing value = visible blank, attributes never get a tag
    item = {"title": "Kaju <Katli>", "data": {"price": "", "made_with": "ghee"}}
    h = SM.fill_attr_safe('<img alt="{{title}} {{price}}"><p>{{title}} {{price}} {{made_with}}</p>', item, sw["fields"])
    assert 'alt="Kaju &lt;Katli&gt; "' in h and "Kaju &lt;Katli&gt; <em class=\"blank\">[Price]</em> ghee" in h
    get_settings.cache_clear()


def test_a_60_page_site_builds_from_one_template(site_env, monkeypatch):
    from app.site import ai as AI
    from app.site import build as B
    from app.site import checks as C
    from app.site import service as S
    from app.site import sitemap as SM
    fake = BigFake(site_env)
    monkeypatch.setattr(AI, "ask_json", fake)
    v = S.new(T, "Sharma Sweets, Akot: 60 pages wali website chahiye, har mithai ka alag page", name="Sharma Sweets",
              answers={"phone": "9876543210"})
    assert fake.maps == 1 and v["size"]["items"] == len(SWEETS) + len(AREAS) and not v["mapping"]
    assert "site map taiyaar" in v["say"] and v["estimate"]["pages"] == v["size"]["total"]
    plan = json.loads(S._load(v["id"]).plan)
    n_sections = sum(len(p["sections"]) for p in plan["pages"])
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    r = S._load(v["id"])
    assert r.status == "ready", r.error
    built = [c for c in site_env.calls if c[0] == "section"]
    assert len({c[1] for c in built}) <= n_sections                          # AI per designed section, never per item
    out = S._assemble_live(r)
    pages = sorted(p.parent.relative_to(out).as_posix() for p in out.rglob("index.html"))
    for n in SWEETS:
        assert f"sweets/{SM.slug(n)}" in pages
    assert all(f"areas/{SM.slug(a)}" in pages for a in AREAS) and "sweets-item" not in pages
    every = "".join(p.read_text() for p in out.rglob("*.html"))
    assert "{{" not in every                                                  # every placeholder filled
    kaju = (out / "sweets" / "kaju-katli" / "index.html").read_text()
    assert '<p aria-label="About Kaju Katli" class="itm">Kaju Katli</p>' in kaju    # attribute AND text filled
    assert '<em class="blank">[Price]</em>' in kaju and "desi ghee" in kaju     # nobody gave a price: a visible blank
    assert 'href="../../assets/site.css"' in kaju                            # two levels deep
    assert 'class="hs-crumbs' in kaju and ">Our sweets</a>" in kaju and 'aria-current="page">Kaju Katli<' in kaju
    home = (out / "index.html").read_text()
    assert 'class="hs-dd' in home and ">About</button>" in home and "hs-search-b" in home
    assert 'href="our-story/"' in home and 'href="how-we-make/"' in home     # a sub page sits in its group's list
    listing = (out / "sweets" / "index.html").read_text()
    assert listing.count('class="hs-item"') == len(SWEETS) and 'href="../sweets/kaju-katli/"' in listing
    idx = json.loads((out / "assets" / "search.json").read_text())
    assert len(idx) == len(pages) - (1 if "404" in pages else 0) and any(x["u"] == "sweets/kaju-katli/" for x in idx)
    assert C.link_scan(out) == []                                             # every internal link resolves
    chk = json.loads(r.checks)
    assert chk["scores"]["pages_total"] == len(pages) and chk["scores"]["pages_checked"] < len(pages)
    # the launch copy: sitemap.xml lists every page, breadcrumbs are in JSON-LD
    site = {**S._ctx(r), "noindex": False}
    res = B.assemble(site, plan, S._sections(r), {}, out.parent / "launch-test", "https://sharmasweets.in")
    sm = (out.parent / "launch-test" / "sitemap.xml").read_text()
    assert sm.count("<url>") == res["pages"] and "https://sharmasweets.in/sweets/kaju-katli/" in sm
    assert '"BreadcrumbList"' in (out.parent / "launch-test" / "sweets" / "kaju-katli" / "index.html").read_text()


def test_chat_adds_list_items_without_new_sections(site_env, monkeypatch):
    from app.site import ai as AI
    from app.site import service as S
    fake = BigFake(site_env)
    monkeypatch.setattr(AI, "ask_json", fake)
    v = S.new(T, "Sharma Sweets 60 pages website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    before = len([c for c in site_env.calls if c[0] == "section"])
    site_env.change = {"say": "Do nayi mithai jod raha hoon.", "items_add": [
        {"collection": "sweets", "title": "Kaju Pista Roll", "data": {"price": "₹900 / kg"}},
        {"collection": "sweets", "title": "Kaju Katli", "data": {}},            # already there: ignored
        {"collection": "nope", "title": "X"}],
        "items_remove": [{"collection": "areas", "title": "Gandhi Chowk"}]}
    S.change(T, v["id"], "Kaju Pista Roll add karo, price 900 kilo; Gandhi Chowk hatao")
    r = S._load(v["id"])
    assert r.status == "ready", r.error
    assert len([c for c in site_env.calls if c[0] == "section"]) == before    # no section rewritten
    out = S._assemble_live(r)
    new = (out / "sweets" / "kaju-pista-roll" / "index.html").read_text()
    assert "₹900 / kg" in new and not (out / "areas" / "gandhi-chowk").exists()
    assert json.loads(r.plan)["collections"][0]["items"][-1]["title"] == "Kaju Pista Roll"


def test_fix_rounds_map_ids_with_dashes():
    from app.site import service as S
    plan = {"pages": [{"slug": "our-story", "sections": [{"type": "timeline_history"}]},
                      {"slug": "sweets-item", "template_of": "sweets", "sections": [{"type": "hero"}]}]}
    rep = {"blocking": [{"text": "contrast", "sections": ["s-our-story-timeline-history", "s-sweets-item-hero"]}]}
    assert S._fixable(rep, plan) == {"our-story__timeline_history": ["contrast"], "sweets-item__hero": ["contrast"]}


def test_small_sites_unchanged():
    from app.site import build as B
    plan = {"pages": [{"slug": "home"}, {"slug": "about", "title": "About"}, {"slug": "privacy", "title": "Privacy"}]}
    assert [p["slug"] for p in B.nav_pages(plan)] == ["home", "about"] and B.rel_of("about") == "../"
    assert B.rel_of("sweets/kaju") == "../../" and B._ok_href("../../contact/") and not B._ok_href("../../x y")


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.316.0"
    assert "0.316.0+356" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
