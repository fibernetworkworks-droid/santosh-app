"""v0.999.71 D6 THE REFERENCE LIBRARY (docs/WEB_DESIGN_ENGINE_PLAN.md phase D6, P3): Hoola's own references only (owner
decision 4) - every section of a site the D5 critic reviewed (the design choice, no words), the kit's blocks, and the
sites she says she likes (a pattern: one picture, its colours, her note - never copied). The writer starts from the
references that agree, custom sections get her own best sections + kit blocks as examples, the critic sees her liked
sites, and every reviewed site teaches the next. Done-line: the design score up again vs D5 (a LIVE card)."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from app.appengine import critic as C
from app.appengine import refs as RF
from app.appengine import writer as W
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_AUTOFIX", "true")    # conftest switches these off for the older suites
    monkeypatch.setenv("SITE_CRITIC", "true")
    monkeypatch.setenv("SITE_REFS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _pages():
    return [{"slug": "home", "title": "Home", "for": "public", "sections": [
        {"type": "hero", "heading": "Fresh bread every morning", "line": "Baked in Pune since 1998", "cta": "Order now"},
        {"type": "services_grid", "heading": "What we bake", "items": ["Pav - soft rolls", "Nankhatai - butter biscuits"]},
        {"type": "faq", "heading": "Questions", "items": ["Do you deliver? - Yes, in Kothrud"]},
        {"type": "contact_block", "heading": "Visit us"}]}]


def _rows(variant="numbered", tone=""):
    return [{"page": "home", "sec": "home:0", "block": "hero", "variant": "split", "tone": ""},
            {"page": "home", "sec": "home:1", "block": "services_grid", "variant": variant, "tone": tone},
            {"page": "home", "sec": "home:2", "block": "faq", "variant": "accordion", "tone": ""},
            {"page": "home", "sec": "home:3", "block": None, "why": "left out"}]


def _png(colour=(30, 60, 200)) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (320, 200), colour).save(b, "JPEG")
    return b.getvalue()


# ---------------------------------------------------------------- 1. learning: the design choice, never her words
def test_a_reviewed_site_is_learned_as_design_choices_only(env):
    n = RF.learn("t1", "ae_a", 3, _rows(), score=8.5, critic="claude-x", purpose="business", kind="brochure",
                 field="bakery", direction="warm_local")
    assert n == 3                                                   # the left-out section is not a reference
    from sqlalchemy import select
    from app.db import session
    with session() as s:
        got = list(s.scalars(select(RF.AppRef).where(RF.AppRef.app == "ae_a")))
    cols = {c.name for c in RF.AppRef.__table__.columns}
    assert not ({"heading", "words", "text", "brief", "copy"} & cols)          # no column could hold her words
    assert {(r.block, r.variant, r.position) for r in got} == {("hero", "split", 0), ("services_grid", "numbered", 1),
                                                              ("faq", "accordion", 2)}
    assert RF.learn("t1", "ae_a", 4, _rows("cards"), score=7.0, critic="claude-x") == 3   # its newest review replaces it
    with session() as s:
        got = list(s.scalars(select(RF.AppRef).where(RF.AppRef.app == "ae_a")))
    assert len(got) == 3 and {r.version for r in got} == {4}
    assert RF.keep("t1", "ae_a") == 3 and RF.keep("t2", "ae_a") == 0          # only her own site is hers to keep
    RF.learn("t1", "ae_a", 5, _rows(), score=7.5, critic="claude-x")
    with session() as s:
        assert all(r.kept for r in s.scalars(select(RF.AppRef).where(RF.AppRef.app == "ae_a")))   # a kept site stays kept
    assert RF.learn("t1", "ae_b", 1, _rows(), score=None, critic="x") == 0     # no score = nothing learned


def test_suggest_needs_agreement_a_good_score_and_a_gain(env):
    for i in range(2):
        RF.learn("t1", f"ae_{i}", 1, _rows("numbered"), score=9.0, critic="claude-x", purpose="business")
    kw = dict(tenant="t9", purpose="business", current=("cards", "surface"), allowed_variants=["numbered"],
              allowed_tones=["plain", "ink"])
    assert RF.suggest("services_grid", **kw) is None                           # 2 sites: not enough agreement
    RF.learn("t1", "ae_2", 1, _rows("numbered"), score=9.0, critic="claude-x", purpose="business")
    sg = RF.suggest("services_grid", **kw)
    assert sg and sg["variant"] == "numbered" and sg["rows"] == 3 and "reviewed sites" in sg["why"]
    assert RF.suggest("services_grid", **{**kw, "allowed_variants": []}) is None   # a layout it cannot draw: never
    for i in range(3):                                                         # low scores never teach
        RF.learn("t1", f"ae_low{i}", 1, _rows("cards", "plain"), score=5.0, critic="claude-x")
    assert RF.suggest("services_grid", **{**kw, "current": ("numbered", "")}) is None
    for i in range(3):                                                         # the writer's own choice scores as well: kept
        RF.learn("t1", f"ae_c{i}", 1, _rows("cards", "surface"), score=8.9, critic="claude-x", purpose="business")
    assert RF.suggest("services_grid", **kw) is None


def test_a_scripted_critics_rows_teach_only_their_own_account(env):
    for i in range(3):
        RF.learn("__card__", f"ae_s{i}", 1, _rows("numbered"), score=9.0, critic=RF.SCRIPTED)
    kw = dict(current=("cards", "surface"), allowed_variants=["numbered"], allowed_tones=[])
    assert RF.suggest("services_grid", tenant="her", **kw) is None
    assert RF.suggest("services_grid", tenant="__card__", **kw)["variant"] == "numbered"


def test_the_writer_starts_from_the_references(env):
    for i in range(3):
        RF.learn("t1", f"ae_{i}", 1, _rows("numbered", "ink"), score=9.0, critic="claude-x", purpose="business",
                 direction="warm_local")
    ctx = W.Ctx("Sunrise Bakery", _pages(), {"phone": "+91 90000 00001"}, "s", None)
    design, used = RF.prior("her", _pages(), ctx, purpose="business", direction="warm_local")
    sv = design.get("home:1") or {}
    assert sv.get("tone") == "ink" and used and used[0]["sec"] == "home:1" and "reviewed sites" in used[0]["why"]
    code, rows = W.page_file(_pages()[0], ctx, {}, design)
    r1 = next(r for r in rows if r["sec"] == "home:1")
    assert r1["tone"] == "ink" and r1["variant"] in ("numbered", "cards")
    assert "home:0" not in design                                              # the hero had no agreeing references


# ---------------------------------------------------------------- 2. examples for a custom section
def test_custom_sections_learn_from_her_own_best_sections_and_the_kit(ae_env, monkeypatch):
    from app.appengine import service as AE
    app = AE.create(T, name="Sunrise Bakery", brief="a bakery", render="site")
    code = ('import { Section, Container, SectionHead } from "@/components/blocks/_kit";\n'
            'export default function OurPromiseSection() {\n  return (<Section block="custom_promise"><Container>'
            '<SectionHead title="Our promise" intro="Baked at 5 every morning" /></Container></Section>);\n}\n')
    AE.write(T, app["id"], "src/components/sections/OurPromiseSection.tsx", code)
    RF.learn(T, app["id"], 1, [{"page": "home", "sec": "home:1", "block": "custom", "component": "OurPromiseSection"}],
             score=8.8, critic="claude-x", purpose="business")
    ex = RF.examples(T, {"type": "custom_promise", "label": "Our promise"}, "business")
    assert ex[0]["what"].startswith("one of your own sections") and "Baked at 5" in ex[0]["code"]
    assert any("the kit's" in e["what"] for e in ex) and len(ex) <= RF.MAX_EXAMPLES
    assert all("export const sample" not in e["code"] for e in ex if "kit" in e["what"])   # never the kit's sample words
    other = RF.examples("someone_else", {"type": "custom_promise", "label": "Our promise"})
    assert all("Baked at 5" not in e["code"] for e in other)                   # her code never teaches another account
    txt = RF.examples_text(ex)
    assert "never copy their words" in txt
    seen = []

    def model(system, prompt):
        seen.append(prompt)
        raise RuntimeError("no model here")
    pages = [{"slug": "home", "title": "Home", "for": "public", "sections": [
        {"type": "hero", "heading": "Sunrise"}, {"type": "custom_promise", "label": "Our promise"}]}]
    W.write_app(T, app["id"], pages, name="Sunrise Bakery", model=model, examples=lambda s: txt,
                likes="SITES SHE LIKES (patterns only - never copy their words, pictures or code):\n- example.com")
    assert seen and "EXAMPLES OF HOOLA'S OWN SECTIONS" in seen[0] and "SITES SHE LIKES" in seen[0]


# ---------------------------------------------------------------- 3. the sites she likes
def test_the_sites_she_likes_are_patterns_on_public_addresses_only(env, monkeypatch):
    monkeypatch.setattr("app.qa.runner.is_public", lambda h: h.endswith(".com"))
    with pytest.raises(RF.RefError) as e:
        RF.add_link("her", "http://192.168.1.10/admin", shot=_png())
    assert "public" in str(e.value)
    with pytest.raises(RF.RefError):
        RF.add_link("her", "ftp://example.com", shot=_png())
    v = RF.add_link("her", "lovely-bakery.com", "warm and calm", shot=_png((200, 90, 40)))
    assert v["url"] == "https://lovely-bakery.com" and v["host"] == "lovely-bakery.com" and v["colours"][0].startswith("#C")
    with pytest.raises(RF.RefError) as e:
        RF.add_link("her", "https://lovely-bakery.com", shot=_png())
    assert e.value.code == 409
    lk = RF.likes("her")
    assert "lovely-bakery.com: warm and calm" in lk["text"] and "never copy" in lk["text"]
    assert len(lk["pictures"]) == 1 and "never copy it" in lk["pictures"][0][0]
    assert RF.likes("someone_else") == {"pictures": [], "text": ""}            # hers only
    assert RF.link_shot("her", v["id"])[:2] == b"\xff\xd8"
    with pytest.raises(RF.RefError):
        RF.link_shot("someone_else", v["id"])
    for i in range(RF.MAX_LINKS - 1):
        RF.add_link("her", f"site{i}.com", shot=_png())
    with pytest.raises(RF.RefError) as e:
        RF.add_link("her", "one-more.com", shot=_png())
    assert "Up to" in str(e.value)
    assert RF.remove_link("her", v["id"])["ok"] and len(RF.links("her")) == RF.MAX_LINKS - 1
    with pytest.raises(RF.RefError):
        RF.remove_link("someone_else", RF.links("her")[0]["id"])


def test_the_picture_of_a_liked_site_never_reaches_a_private_address(env, monkeypatch):
    """The capture blocks every request to a non-public host (a page that loads from 127.0.0.1 gets nothing)."""
    import http.server
    import socketserver
    import threading
    hits = []

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):  # noqa: N802
            hits.append(self.path)
            body = b"<html><body style='background:#123456'><img src='/secret.png'>hi</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/"
        monkeypatch.setattr("app.qa.runner.is_public", lambda h: False)
        with pytest.raises(Exception):
            RF.capture(url)                                                    # the page itself is refused
        assert hits == []
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- 4. the loop uses and feeds the library
def test_the_loop_starts_from_references_and_teaches_the_next_site(ae_env):
    _box()
    from app.appengine import service as AE
    from app.quality import designcard as DC
    for i in range(3):
        RF.learn("someone", f"ae_old{i}", 1, _rows("numbered", "ink"), score=9.2, critic="claude-x", purpose="business",
                 direction="warm_local")
    app = AE.create(T, name="Sunrise Bakery", brief="a bakery", render="site")
    rep = C.improve(T, app["id"], _pages(), name="Sunrise Bakery", facts={"phone": "+91 90000 00001"}, seed="s",
                    purpose="business", direction="warm_local", field="bakery", hero=False,
                    critic=lambda *a: {"scores": {c: 8 for c in DC.CRITERIA}, "design": 8.0, "fixes": []})
    assert rep["passed"] and rep["refs"]["used"] >= 1 and rep["refs"]["learned"] >= 3
    assert any(u["sec"] == "home:1" and u.get("tone") == "ink" for u in rep["refs"]["choices"])
    home = (AE.src_dir(AE._load(T, app["id"])) / "src" / "pages" / "HomePage.tsx").read_text()
    assert 'tone="ink"' in home.split('data-sec="home:1"')[1].split("</div>")[0]
    assert "from Hoola's references" in C.say(rep)
    from sqlalchemy import select
    from app.db import session
    with session() as s:                                                       # the scripted critic teaches only itself
        mine = list(s.scalars(select(RF.AppRef).where(RF.AppRef.app == app["id"])))
    assert mine and all(r.critic == RF.SCRIPTED and r.field == "bakery" and r.direction == "warm_local" for r in mine)


# ---------------------------------------------------------------- 5. wiring
def test_wiring():
    main = (ROOT / "server/app/main.py").read_text()
    for path in ('"/api/appengine-refs"', '"/api/appengine-refs/links"', '"/api/appengine-refs/links/{rid}"',
                 '"/api/appengine-refs/links/{rid}/shot"'):
        assert path in main
    assert "RF.keep(tenant, r.id)" in (ROOT / "server/app/appengine/service.py").read_text()
    assert "appengine import refs as _appengine_refs" in (ROOT / "server/app/db.py").read_text()
    proto = (ROOT / "server/app/site/prototype.py").read_text()
    assert 'field=str(spec.get("field_hint")' in proto and "direction=str(gdir)" in proto
    js = (ROOT / "server/app/static/console/webstudio.js").read_text()
    assert 'data-form="like-add"' in js and "like-del" in js and "/api/appengine-refs" in js
    from app.config import get_settings
    assert get_settings().site_refs
    wf = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert "site_refs_card_try)" in wf and "SITE_REFS=false" in wf and "--d5 data/quality/critic_card_try.json" in wf


def test_the_card_compares_with_d5_only_when_both_are_live():
    from app.appengine import writercard as WC
    live = {"kind": "live", "summary": {"review": {"score": 7.6}}}
    assert WC.against_d5(live, {"kind": "live", "summary": {"review": {"score": 7.1}}})["beaten"] is True
    assert WC.against_d5(live, {"kind": "free", "summary": {"review": {"score": 7.1}}})["beaten"] is None
    assert WC.against_d5({"kind": "free", "summary": {"review": {"score": 9}}}, None)["beaten"] is None
    rv = WC._review_sum([{"score": 8.0, "refs_used": 2, "refs_learned": 5}, {"score": 7.0, "refs_used": 0}])["review"]
    assert rv["refs_used"] == 2 and rv["sites_with_refs"] == 1 and rv["refs_learned"] == 5
