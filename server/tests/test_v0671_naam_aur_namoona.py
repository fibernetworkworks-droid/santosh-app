"""v0.671 NAAM AUR NAMOONA (owner: "when website show preview it must show some dummy value not empty data ... before
building give a self Hoola AI defined website brand name - like Lovable does").

1. A website asked for without a business name gets a brand name BEFORE anything is built: her own words when they
   name the business, else one quick model call, else a house fallback. The Studio says "Named by Hoola" + Rename,
   and a rename before the build becomes the business name on the pages too.
2. The preview never shows a yellow [phone] / [price]: every blank shows a believable sample (the model's data-eg,
   else a house sample by label). It stays a blank underneath, so the launch check still blocks until the real value.
"""
from __future__ import annotations

from pathlib import Path

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

D = Path(__file__).resolve().parents[1] / "app"


def test_samples_replace_blanks_but_stay_blanks():
    from app.site import build as B
    h = ('<p>Call <em class="blank" data-eg="99887 66554">[phone]</em>, mail <em class="blank">[email]</em>, '
         'since <em class="blank">[year]</em>, <em class="blank">[secret recipe]</em></p>')
    out = B.samples(h, {"name": "Mithaas & Co", "city": "Akola"})
    assert "99887 66554" in out and "hello@mithaasco.in" in out and ">2015<" in out
    assert "[phone]" not in out and "[email]" not in out
    assert out.count('class="blank eg"') == 3 and 'data-blank="phone"' in out
    assert '<em class="blank">[secret recipe]</em>' in out                 # no believable sample = left as it was
    assert B.samples("<p>no blanks</p>", {}) == "<p>no blanks</p>"
    css = (D / "site" / "assets" / "hoola-site.css").read_text()
    assert ".blank.eg{" in css
    js = (D / "site" / "assets" / "hoola-build.js").read_text()
    assert "em.blank[data-eg]" in js                                      # the live canvas shows samples too
    ai = (D / "site" / "ai.py").read_text()
    assert 'data-eg="a realistic sample"' in ai and "Never leave a list, menu, price table or review row empty" in ai


def test_fill_blanks_reads_sample_blanks():
    from app.site import service as S
    m = S._BLANK.search('x <em class="blank" data-eg="98765 43210">[phone]</em> y')
    assert m and m.group(1) == "phone"


def test_brand_name_her_words_model_and_fallback(site_env, monkeypatch):
    from app.site import ai as AI
    from app.site import service as S
    assert S.brand_name("Sharma Sweets ki website, online order")["name"] == "Sharma Sweets"
    assert S.brand_name("Kale Dental Clinic: booking chahiye")["by"] == "her"
    monkeypatch.setattr(AI, "ask_json", lambda *a, **k: {"name": "Mithaas Ghar", "tagline": "Akola ki asli mithai",
                                                          "from_her_words": False})
    b = S.brand_name("mithai dukaan ki website", "Sweet shop", "Akola")
    assert b == {"name": "Mithaas Ghar", "tagline": "Akola ki asli mithai", "by": "hoola"}
    monkeypatch.setattr(AI, "ask_json", lambda *a, **k: {"name": "https://evil.example"})
    assert S.brand_name("mithai dukaan ki website", "Sweet shop")["name"].endswith("Sweet Shop")
    monkeypatch.setattr(AI, "ask_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    fb = S.brand_name("mithai dukaan ki website", "Sweet shop (mithai)")
    assert fb["by"] == "hoola" and fb["name"].endswith("Sweet Shop") and len(fb["name"]) <= 40


def test_new_site_is_named_before_building_and_rename_reaches_the_pages(site_env, monkeypatch):
    from app.site import ai as AI
    from app.site import service as S
    real = AI.ask_json
    monkeypatch.setattr(AI, "ask_json", lambda system, *a, **k: {"name": "Mithaas Ghar", "tagline": "Har din meetha"}
                        if system.startswith(S.NAME_SYSTEM[:30]) else real(system, *a, **k))
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par", "")
    assert v["name"] == "Mithaas Ghar" and v["name_by"] == "hoola"
    assert v["facts"]["name"] == "Mithaas Ghar" and v["facts"]["tagline"] == "Har din meetha"
    assert not any("naam" in q.lower() for q in v["questions"])            # no 'what is the name?' question
    r = S.rename(T, v["id"], "Annapurna Sweets")
    assert r["name"] == "Annapurna Sweets" and r["name_by"] == "" and r["facts"]["name"] == "Annapurna Sweets"
    own = S.new(T, "Sharma Sweets ki website", "")
    assert own["name"] == "Sharma Sweets" and own["name_by"] == ""


def test_preview_shows_samples_and_launch_still_waits(site_env, monkeypatch):
    from app.site import checks as C
    from app.site import hosting as H
    from app.site import service as S
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots in this test")))
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par", "", name="Sharma Sweets")
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 1)
    r = S._load(v["id"])
    assert r.version >= 1
    page = (Path(S.B.out_dir(r.tenant_id, r.id, r.version)) / "index.html").read_text()
    assert 'class="blank eg"' in page and "[year]" not in page               # the fake writes a [year] blank
    src = (D / "site" / "hosting.py").read_text()
    assert "sample value" in src                                            # launch line names the samples


def test_studio_says_named_by_hoola():
    js = (D / "static" / "console" / "webstudio.js").read_text()
    css = (D / "static" / "console" / "webstudio.css").read_text()
    assert "v.name_by === 'hoola'" in js and "✦ Named by Hoola" in js and 'class="namedby"' in js and "data-menu=" in js
    assert "I named it <b>" in js and ".namedby{" in css
