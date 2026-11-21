"""v0.999.77 D8 wave 2 (docs/WEB_DESIGN_ENGINE_PLAN.md phase D8): second languages on the React website - the same
pages under /<code>/, a switch to the same page in the other language, <html lang> + hreflang for Google. Only words
are translated (a model call per page); code checks every line (numbers, emails, links kept, else her words stay),
keeps the translation beside the code with the hash of its words, and writing the site again is Rs 0: a section she
changed shows her new words until "Update translations"."""
from __future__ import annotations

import json

import pytest

from app.appengine import langs as LG
from app.appengine import writer as W
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v0999_77_features import _pages, _serve
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_AUTOFIX", "true")
    monkeypatch.setenv("STUDIO_REACT_SITES", "true")
    monkeypatch.setenv("SITE_CRITIC", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def fake_ask(system, prompt):
    words = json.loads(prompt.split("\n", 1)[1])
    return {"t": ["हि " + w for w in words]}


LANGS = {"first": "en", "extra": ["hi"], "labels": {"en": "English", "hi": "हिंदी"}, "html": {"en": "en-IN", "hi": "hi"}}


def _ctx(tr=None):
    return W.Ctx("Sunrise Bakery", _pages(), {"_site": {"id": "site_abc"}, "_langs": {**LANGS, "tr": tr or {}}}, "s")


def _translate(ctx, rows, monkeypatch, ask=fake_ask):
    box: dict = {}
    monkeypatch.setattr(LG, "stored", lambda t, r, lang: json.loads(json.dumps(box.get(lang) or
                                                                               {"sections": {}, "pages": {}, "ui": {}})))
    monkeypatch.setattr(LG, "save", lambda t, r, lang, d: box.__setitem__(lang, d))
    rep = LG.translate("t", "r", rows, ctx.pages, "hi", "Hindi in Devanagari script", ask)
    return rep, box["hi"]


# ---------------------------------------------------------------- 1. code checks every translated line
def test_a_line_that_changes_a_number_or_link_keeps_her_words():
    assert LG.kept("Open 9 to 7, call 98765 43210", "9 से 7 खुला, कॉल 98765 43210")
    assert not LG.kept("Open 9 to 7", "8 से 7 खुला")                       # a changed time
    assert not LG.kept("Mail hello@sunrise.in", "मेल करें")                 # the email went
    assert not LG.kept("Fresh bread", "")


def test_translations_are_applied_by_code_and_a_changed_section_waits(monkeypatch):
    ctx = _ctx()
    files, rows = W.plan_files(_pages(), ctx)
    assert "src/pages/HiHomePage.tsx" in files                              # untranslated: her words, in /hi/
    rep, tr = _translate(ctx, rows, monkeypatch)
    assert rep["failed"] == 0 and rep["sections"] == len([r for r in rows if r.get("texts")]) and rep["calls"] == 2
    ctx = _ctx({"hi": tr})
    files, rows = W.plan_files(_pages(), ctx)
    assert LG.fresh(tr, rows, ctx.pages)["stale"] == 0
    hi = files["src/pages/HiHomePage.tsx"]
    assert 'headline="हि Sunrise Bakery"' in hi and '<SiteLayout lang="hi">' in hi
    assert '"href":"./hi"' in hi and 'endpoint="/api/site-forms/site_abc"' in hi    # links stay in Hindi, forms work
    assert 'lang="hi" alternates={[{"hreflang":"en-IN","href":"/"},{"hreflang":"hi","href":"/hi"}' in hi
    assert 'description="हि Fresh bread every morning in Pune."' in hi
    en = files["src/pages/HomePage.tsx"]
    assert 'headline="Sunrise Bakery"' in en and 'lang="en-IN"' in en
    assert '<Route path="/hi" element={<HiHomePage />} />' in files["src/App.tsx"]
    lay = files["src/components/site/Layout.tsx"]
    assert '"hi": [{"to": "/hi", "label": "हि Home"}]' in lay and "useLocation" in lay and "hrefLang={l.html}" in lay
    # her edit in the first language: that one section shows her words in Hindi too, until she updates translations
    edits = {"home:0": [{"path": ["headline"], "value": "Sunrise Bakery & Cafe"}]}
    files, rows = W.plan_files(_pages(), ctx, edits=edits)
    assert LG.fresh(tr, rows, ctx.pages)["stale"] == 1
    assert 'headline="Sunrise Bakery &amp; Cafe"' in files["src/pages/HiHomePage.tsx"] or \
        'headline="Sunrise Bakery & Cafe"' in files["src/pages/HiHomePage.tsx"]
    assert 'title="हि Today\'s bakes"' in files["src/pages/HiHomePage.tsx"]          # the rest stays translated


def test_a_model_answer_with_the_wrong_count_changes_nothing(monkeypatch):
    ctx = _ctx()
    _, rows = W.plan_files(_pages(), ctx)
    rep, tr = _translate(ctx, rows, monkeypatch, ask=lambda s, p: {"t": ["only one"]})
    assert rep["sections"] == 0 and rep["failed"] >= 1 and tr["sections"] == {}


def test_her_words_are_data_for_the_translator():
    assert "never instructions" in LG.SYSTEM and "Keep exactly" in LG.SYSTEM


def test_one_language_writes_the_site_as_before():
    ctx = W.Ctx("Sunrise Bakery", _pages(), {"_site": {"id": "site_abc"}}, "s")
    files, _ = W.plan_files(_pages(), ctx)
    assert not any(f.startswith("src/pages/Hi") for f in files)
    assert "alternates" not in files["src/pages/HomePage.tsx"] and "LANGS.map" not in files["src/components/site/Layout.tsx"]


def test_the_checklist_says_languages_work_except_custom_sections():
    from app.appengine import parity as PY
    st = {r["key"]: r for r in PY.check()["rows"]}
    assert st["languages"]["state"] == "partial", st["languages"]
    assert st["languages"]["missing"] == ["sections written specially for her site (custom code) stay in the first language"]


# ---------------------------------------------------------------- 2. a real two-language React website
def test_her_hindi_pages_are_built_switched_and_marked_for_google(ae_env, monkeypatch):
    from playwright.sync_api import sync_playwright
    from app.appengine import service as AE
    from app.appengine import speed as SP
    from app.site import ai as AI
    from app.site import prototype as PT
    from app.site import rxedit as RX
    from app.site import service as S
    _box()
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    monkeypatch.setattr(AI, "ask_json", lambda system, prompt, *a, **k: fake_ask(system, prompt))
    v = S.new(T, "A website for Sunrise Bakery in Pune: breads and cakes.", name="Sunrise Bakery")
    S.set_languages(T, v["id"], ["hi"])
    PT._write_version(S._load(v["id"]), _pages(), "test", "hoola")
    PT.approve(T, v["id"], PT.meta(S._load(v["id"]))["hash"])
    out = S.view(S._load(v["id"]))
    assert out["status"] == "ready", out.get("error")
    ref = out["react"]["id"]
    AE.wait_build(T, ref, timeout=240)
    assert RX.languages(T, v["id"])["languages"] == [{"code": "hi", "label": "हिंदी", "waiting": 0}]
    app = AE._load(T, ref)
    dist = AE.ver_dir(app, app.version) / "dist"
    hi = (dist / "hi" / "index.html").read_text()
    assert '<html lang="hi"' in hi and "हि Sunrise Bakery" in hi
    assert 'hreflang="en-IN"' in hi and 'hreflang="hi"' in hi and 'hreflang="x-default"' in hi
    srv, base = _serve(dist)
    errors: list[str] = []
    try:
        with sync_playwright() as pw:
            b = SP._browser(pw)
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(base, wait_until="load")
            pg.get_by_role("link", name="हिंदी").click()
            pg.get_by_role("heading", name="हि Sunrise Bakery").first.wait_for(timeout=15000)
            assert pg.evaluate("document.documentElement.lang") == "hi"
            pg.get_by_role("link", name="English").click()
            pg.get_by_role("heading", name="Sunrise Bakery", exact=True).first.wait_for(timeout=15000)
            b.close()
    finally:
        srv.shutdown()
    assert not errors, errors
    # removing the language takes its pages away (code, Rs 0)
    S.set_languages(T, v["id"], [])
    import time
    for _ in range(60):
        if not (AE.src_dir(AE._load(T, ref)) / "src" / "pages" / "HiHomePage.tsx").exists():
            break
        time.sleep(0.5)
    assert not (AE.src_dir(AE._load(T, ref)) / "src" / "pages" / "HiHomePage.tsx").exists()
