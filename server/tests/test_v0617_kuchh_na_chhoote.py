"""v0.617 KUCHH NA CHHOOTE + PEXELS KA NAAM (from the Hallmark read, docs/research/hallmark/00_READ.md).

1. A change in her words is compared with the version before it: her phone / WhatsApp / email links, forms and their
   fields, page links and the pieces Hoola wires in (shop products, blog posts, charts, booking...) must still be there.
   What went missing is NAMED (warning + kept.lost + a line to her), never blocking, never auto-edited; what she asked
   to remove is not reported; a page the change itself took away is not reported as a lost link.
2. Pexels photos are CREDITED on every built page, as the Pexels API guidelines ask: 'Photos provided by Pexels'
   linked to pexels.com, and each photographer named with a link to the photo page (older photos keep their name
   from the credit text they already had)."""
import json
from pathlib import Path

import httpx

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.822.0"


OLD = """<html><body><nav><a href="./">Home</a><a href="menu/">Menu</a><a href="contact/">Contact</a></nav>
<section id="s-home-hero"><a href="tel:+919876543210">Call</a> <a href="https://wa.me/919876543210?text=hi">WhatsApp</a>
<a href="mailto:hello@sharma.in">Mail</a><div data-hoola-posts="3"></div><figure data-hoola-chart="bar"></figure></section>
<section id="s-home-form"><form data-hoola-form><input name="name"><input name="phone"><textarea name="message"></textarea>
<input class="hp" name="website"></form></section></body></html>"""


def _site(tmp: Path, name: str, html: dict[str, str]) -> Path:
    d = tmp / name
    for rel, h in html.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(h)
    return d


def test_what_went_missing_is_named(tmp_path):
    from app.site import kept as KP
    old = _site(tmp_path, "old", {"index.html": OLD, "menu/index.html": "<h1>Menu</h1>", "contact/index.html": "<h1>C</h1>"})
    new_html = (OLD.replace('<a href="tel:+919876543210">Call</a>', "")
                .replace('<input name="phone">', "").replace('<figure data-hoola-chart="bar"></figure>', ""))
    new = _site(tmp_path, "new", {"index.html": new_html, "menu/index.html": "<h1>Menu</h1>", "contact/index.html": "<h1>C</h1>"})
    res = KP.check(old, new, "hero ka heading bada karo")
    kinds = {(x["kind"], x["what"]) for x in res["lost"]}
    assert res["checked"] and ("phone", "+919876543210") in kinds and ("field", "phone") in kinds
    assert any(k == "hook" and w.startswith("data-hoola-chart") for k, w in kinds)
    assert not any(k in ("whatsapp", "email", "form", "page") for k, _w in kinds)       # those stayed
    assert "website" not in {w for k, w in kinds if k == "field"}                         # the honeypot is Hoola's own
    line = KP.say_line(res["lost"])
    assert "+919876543210" in line and "wapas lagao" in line
    # the same change, but SHE asked for the phone to go: the phone link + field are not reported
    asked = KP.check(old, new, "phone number hata do website se")
    assert not any(x["kind"] in ("phone", "field") for x in asked["lost"])
    assert any(x["kind"] == "hook" for x in asked["lost"])                                # the chart she did not mention


def test_a_page_the_change_removed_is_not_a_lost_link(tmp_path):
    from app.site import kept as KP
    old = _site(tmp_path, "o", {"index.html": OLD, "menu/index.html": "m", "contact/index.html": "c"})
    new = _site(tmp_path, "n", {"index.html": OLD.replace('<a href="menu/">Menu</a>', ""), "contact/index.html": "c"})
    assert not [x for x in KP.check(old, new, "")["lost"] if x["kind"] == "page"]
    # with no earlier version there is nothing to compare, said so
    assert KP.check(tmp_path / "none", new, "") == {"checked": False, "lost": [], "why": "no earlier version to compare"}


def test_wired_into_a_change_build(site_env):
    from app.site import build as B
    from app.site import service as S
    from tests.test_v0551_suraksha_gates import _built
    sid, r, live = _built(S)
    cur = S._load(sid)
    assert cur.version >= 1 and (B.out_dir(cur.tenant_id, cur.id, cur.version) / "index.html").exists()
    idx = live / "index.html"
    h = idx.read_text()
    assert "tel:" in h
    idx.unlink()                                                     # a rebuild writes fresh files (versions are hard links)
    idx.write_text(h.replace("tel:", "nottel:"))                     # the rewrite dropped every call link
    out = S._kept(cur, {"warnings": []}, "naya offer section jodo")
    assert out["kept"]["checked"] and any(x["kind"] == "phone" for x in out["kept"]["lost"])
    assert any(w["kind"] == "kept" and "phone call link" in w["text"] for w in out["warnings"])
    assert "blocking" not in out or not any(b.get("kind") == "kept" for b in out.get("blocking") or [])
    ok = S._kept(cur, {"warnings": []}, "phone number hatao")
    assert not any(x["kind"] == "phone" for x in ok["kept"]["lost"])
    src = Path(S.__file__).read_text()
    assert "if only:" in src and "_kept(r, report," in src               # only a change in her words, never the first build


def test_pexels_credit_is_kept_and_shown(site_env, monkeypatch):
    from app.config import get_settings
    from app.site import build as B
    from app.site import pictures as P
    from app.site import service as S

    def answer(req: httpx.Request) -> httpx.Response:
        if req.url.host == "api.pexels.com":
            return httpx.Response(200, json={"photos": [{"photographer": "Asha Rao", "url": "https://www.pexels.com/photo/sweets-123/",
                                                          "photographer_url": "https://www.pexels.com/@asha",
                                                          "src": {"large2x": "https://images.pexels.com/x.jpg"}}]})
        return httpx.Response(200, content=b"\xff\xd8jpegbytes")
    P.set_transport(httpx.MockTransport(answer))
    monkeypatch.setattr(get_settings(), "pexels_api_key", "k", raising=False)
    try:
        data, credit = P._stock_picture({"about": "mithai", "aspect": "16:9"})
    finally:
        P.set_transport(None)
    assert credit["credit_name"] == "Asha Rao" and credit["credit_url"] == "https://www.pexels.com/photo/sweets-123/"
    assert credit["credit"] == "Photo: Asha Rao / Pexels"
    # a site with one new-style and one older photo: both photographers named, the Pexels link shown once
    from tests.test_v0551_suraksha_gates import _built
    sid, r, live = _built(S)
    from app.db import session
    from app.site.models import Site
    with session() as s:
        row = s.get(Site, sid)
        row.photos = json.dumps([{"name": "a", "source": "pexels", **credit},
                                 {"name": "b", "source": "pexels", "credit": "Photo: Ravi K / Pexels"},
                                 {"name": "c", "ai": True, "source": "ai"}])
    cr = S._photo_credits(S._load(sid))
    assert [c["name"] for c in cr] == ["Asha Rao", "Ravi K"] and cr[1]["url"] == ""
    html = B.photo_credits({"photo_credits": cr})
    assert 'Photos provided by <a href="https://www.pexels.com"' in html
    assert '<a href="https://www.pexels.com/photo/sweets-123/" rel="noopener">Asha Rao</a>' in html and "Ravi K" in html
    assert B.photo_credits({"photo_credits": []}) == ""
    out = S._assemble_live(S._load(sid))
    page = (out / "index.html").read_text()
    assert "Photos provided by" in page and "Asha Rao" in page and "AI-generated" in page
    # an unsafe link is never written as a link
    assert "javascript" not in B.photo_credits({"photo_credits": [{"name": "X", "url": "javascript:alert(1)"}]})
