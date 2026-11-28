"""v0.999.316 DESIGN.md (owner: getdesign.md + VoltAgent/awesome-design-md -> design canvas -> "GO BUILD").

The server half: Hoola's one DESIGN.md reader (tolerant YAML, older files with no tokens), the checker (Google's lint
rules in plain words), the catalog of 83 looks (MIT), a design as look 1's reference with its rules for the writer and
the critic, the routes, a design riding a new website (Build and Plan), and the App Engine's export / import in the
spec's own shape."""
from __future__ import annotations

import gzip
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture: the architect + the site fake AI)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

T = "default"


def _dm():
    from app.site import designmd as DM
    return DM


# ---------------------------------------------------------------- the catalog
def test_catalog_has_every_usable_look_and_leaves_out_gambling():
    DM = _dm()
    raw = json.loads(gzip.decompress((DM.LIB / "looks.json.gz").read_bytes()))
    assert raw["source"]["licence"] == "MIT" and any("1win" in x for x in raw["source"]["left_out"])
    assert (DM.LIB / "LICENSE.txt").read_text().count("MIT License") == 1
    c = DM.catalog()
    assert c["total"] == 84 and len(c["looks"]) == 84
    assert sum(x["count"] for x in c["cats"] if x["id"] != "all") == 84
    names = [x["name"] for x in c["looks"]]
    assert len(set(names)) == 84                                           # every look its own Hoola name
    brands = {x["brand"].lower() for x in raw["looks"]}
    for x in c["looks"]:
        assert x["name"].lower() not in brands, x["name"]
        t = x["t"]
        assert all(t[k].startswith("#") for k in ("bg", "ink", "acc", "on", "muted", "line")), x["id"]
        assert DM.contrast(t["ink"], t["bg"]) >= 4.5, x["id"]
        assert DM.contrast(t["muted"], t["bg"]) >= 4.5, x["id"]
        assert DM.contrast(t["on"], t["acc"]) >= 4.5, x["id"]
        assert DM.contrast(t["acc"], t["bg"]) >= 3, x["id"]
    assert DM.catalog("fin")["looks"] and all(x["cat"] == "fin" for x in DM.catalog("fin")["looks"])
    assert [x["id"] for x in DM.catalog("", "midnight")["looks"]] == ["linear-app"]


def test_both_modes_are_made_and_readable():
    DM = _dm()
    for x in DM.catalog()["looks"]:
        md = DM.modes(DM._entry(x["id"])["doc"]["roles"])
        assert md["own"] in ("dark", "light")
        for mode in ("dark", "light"):
            m = md[mode]
            assert (DM.lum(m["bg"]) < 0.2) == (mode == "dark"), (x["id"], mode, m["bg"])
            assert DM.contrast(m["ink"], m["bg"]) >= 4.5 and DM.contrast(m["muted"], m["bg"]) >= 4.5, (x["id"], mode)
            assert DM.contrast(m["on_primary"], m["primary"]) >= 4.5, (x["id"], mode)


def test_older_files_and_broken_yaml_are_read():
    DM = _dm()
    tesla = DM._entry("tesla")["doc"]                                    # no tokens: read from its words
    assert not tesla["has_tokens"]
    assert tesla["roles"]["bg"] == "#ffffff" and tesla["roles"]["primary"] == "#3e6ae1" and tesla["roles"]["ink"] == "#171a20"
    lambo = DM._entry("lamborghini")["doc"]["roles"]
    assert lambo["bg"] == "#000000" and lambo["primary"] == "#ffc000"      # the gold CTA, not the logo or the footer
    mc = DM._entry("mastercard")["doc"]["roles"]
    assert mc["bg"] == "#f3f0ee" and mc["primary"] == "#cf4500"           # the logo's red / yellow are never the UI
    repaired = [x["id"] for x in DM.catalog()["looks"] if "yaml-repaired" in DM._entry(x["id"])["doc"]["notes"]]
    assert len(repaired) >= 3                                             # a bare colon in the description
    assert DM._entry("linear-app")["doc"]["fonts"]["display"] == "Linear Display"
    assert DM.head_kind(DM._entry("stripe")["doc"]) == "sans"             # 'sans-serif' at the end is not 'serif'
    assert DM.head_kind(DM._entry("claude")["doc"]) == "serif"


def test_the_checker_speaks_googles_rules_in_plain_words():
    DM = _dm()
    md = """---
name: Test
colors:
  primary: "#ffcc00"
  canvas: "#ffffff"
  ink: "#bbbbbb"
components:
  button: {backgroundColor: "{colors.primary}", textColor: "{colors.nope}"}
---
## Colors
x
## Overview
y
## Colors
z
"""
    rules = {r["rule"]: r for r in DM.lint(DM.parse(md))}
    assert rules["duplicate-section"]["severity"] == "error"
    assert "section-order" in rules and "broken-ref" in rules and "{colors.nope}" in rules["broken-ref"]["message"]
    assert rules["contrast-ratio"]["severity"] == "warning"
    assert "missing-primary" not in rules
    bare = DM.lint(DM.parse("# Hi\n\n## Overview\nNothing here."))
    assert {r["rule"] for r in bare} >= {"no-tokens", "missing-primary", "missing-typography"}
    with pytest.raises(DM.DesignMdError):
        DM.parse("   ")
    chk = DM.check("# Hi\n\n## Overview\nNothing here.")
    assert chk["ok"] is False and "colours" in chk["say"]
    good = DM.check(DM.md_text("notion"))
    assert good["ok"] and good["t"]["bg"].startswith("#") and good["rules_list"]


def test_a_look_never_carries_the_source_brand_into_her_site():
    DM = _dm()
    x = DM.look("linear-app")
    assert "Linear" not in x["prompt"] and "Midnight product" in x["prompt"] and "[your business]" in x["prompt"]
    assert all("linear" not in r.lower() for r in x["rules"]), x["rules"]
    assert all("#010102 (#010102)" not in r for r in x["rules"])
    ref = DM.ref_for(look_id="linear-app")
    assert ref["source"] == "designmd" and ref["look"] == "Midnight product" and ref["dark"] is True
    assert ref["overrides"]["primary"].lower() == "#5e6ad2" and ref["rules"] and "rules:" in ref["notes"]
    assert "linear" not in ref["notes"].lower().replace("linear-gradient", "")
    from app.site import inspire as IN
    note = IN.brief_note(ref)
    assert "THE DESIGN.md SHE CHOSE" in note and "never the source site's name" in note


def test_the_sample_page_runs_nothing_and_fetches_nothing():
    DM = _dm()
    for lid in ("linear-app", "claude", "nike", "tesla"):
        for mode in ("dark", "light"):
            h = DM.sample_page(lid, mode)
            assert "<script" not in h.lower() and "http://" not in h and "https://" not in h
            assert DM.modes(DM._entry(lid)["doc"]["roles"])[mode]["bg"] in h
            assert "[YOUR PRICE]" in h
    assert "text-transform:uppercase" in DM.sample_page("nike")


# ---------------------------------------------------------------- the routes
def test_routes(site_env):
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/site-design/looks").json()
    assert r["total"] == 84 and r["looks"][0]["t"]["bg"]
    one = c.get("/api/site-design/looks/claude").json()
    assert one["name"] == "Warm editorial" and one["own_mode"] == "light" and one["swatches"]["dark"] and one["similar"]
    assert c.get("/api/site-design/looks/nope").status_code == 404
    pg = c.get("/api/site-design/looks/claude/page?mode=dark")
    assert pg.status_code == 200 and "default-src 'none'" in pg.headers["content-security-policy"]
    assert "frame-ancestors 'self'" in pg.headers["content-security-policy"]
    md = c.get("/api/site-design/looks/claude/md")
    assert md.status_code == 200 and md.text.startswith("---") and "attachment" in md.headers["content-disposition"]
    chk = c.post("/api/site-design/md/check", json={"text": md.text}).json()
    assert chk["ok"] and chk["found"]["colours"] >= 4
    assert c.post("/api/site-design/md/check", json={"text": ""}).status_code == 400


def test_a_design_rides_a_new_website_and_reaches_the_writer_and_the_critic(site_env):
    from app.main import app
    from app.site import models as SM
    from app.site import quality as Q
    from app.site import service as S
    from app.db import session
    c = TestClient(app)
    v = c.post("/api/sites", json={"brief": "Sharma Sweets mithai dukaan ki website", "design_look": "linear-app"}).json()
    with session() as s:
        r = s.get(SM.Site, v["id"])
        ref = json.loads(r.facts)["design_ref"]
        assert ref["source"] == "designmd" and ref["look"] == "Midnight product" and ref["dark"] is True
        assert S._md_rules(r) and S._md_rules(r) == ref["rules"][:10]
    assert c.post("/api/sites", json={"brief": "a bakery website", "design_look": "nope"}).status_code == 404
    own = c.post("/api/sites", json={"brief": "a bakery website",
                                     "design_md": "---\nname: Mine\ncolors:\n  primary: \"#0a7c42\"\n  canvas: \"#fffdf7\"\n---\n## Do's and Don'ts\n- Do keep it calm\n"}).json()
    with session() as s:
        ref2 = json.loads(s.get(SM.Site, own["id"]).facts)["design_ref"]
    assert ref2["look"] == "Mine" and ref2["overrides"]["primary"].lower() == "#0a7c42" and ref2["rules"] == ["Do keep it calm"]
    seen = {}

    def ask(system, prompt, *a, **k):
        seen["p"] = prompt
        return "{}"
    import app.site.quality as QQ
    old = QQ.AI.ask
    QQ.AI.ask = ask
    try:
        QQ.critique_on = lambda: True
        Q.critique([b"x"], None, ["hero"], "words", ["Do keep it calm"])
    finally:
        QQ.AI.ask = old
    assert "THE DESIGN.md SHE CHOSE" in seen["p"] and "Do keep it calm" in seen["p"]


def test_plan_mode_keeps_her_design_until_the_build(arch_env):
    from app.main import app
    from app.site import architect as AR
    from app.site import models as SM
    from app.db import session
    c = TestClient(app)
    card = c.post("/api/site-architect", json={"words": "hamare school ka portal - admission, fees, notices",
                                               "design_look": "notion"}).json()
    assert card["her_design"] == "Calm workspace"
    plain = c.post("/api/site-architect", json={"words": "hamare school ka portal - admission, fees"}).json()
    assert plain["her_design"] == ""                                     # the next plan does not inherit it
    v = AR.approve(T, card["id"], card["hash"])
    sid = v.get("site_id") or v.get("id") or v.get("site")
    with session() as s:
        from sqlalchemy import select
        rows = s.scalars(select(SM.Site).where(SM.Site.tenant_id == T)).all()
        refs = [json.loads(r.facts).get("design_ref") or {} for r in rows]
    assert any(x.get("look") == "Calm workspace" for x in refs), (sid, refs)


def test_a_catalog_design_applies_to_an_existing_site_through_the_preview(site_env):
    from app.site import inspire as IN
    from app.site import service as S
    v = S.new(T, "a website for my yoga studio")
    p = IN.read(T, "designmd", "claude")
    assert p["ref"]["source"] == "designmd" and p["token"]
    IN.use(T, p["token"], v["id"])
    from app.db import session
    from app.site import models as SM
    with session() as s:
        ref = json.loads(s.get(SM.Site, v["id"]).facts)["design_ref"]
    assert ref["source"] == "designmd" and ref["look"] == "Warm editorial" and ref["rules"]


# ---------------------------------------------------------------- the App Engine's DESIGN.md
def test_app_engine_export_is_spec_shaped_and_imports_every_catalog_file():
    DM = _dm()
    from app.appengine import genome as GN
    g = GN.generate(seed="md316", direction="tech_gradient", mode="dark")
    md = GN.design_md(g)
    doc = DM.parse(md)
    assert DM.lint(doc) == []                                            # clean under Google's rules
    heads = [s["canon"] for s in doc["sections"] if s["canon"]]
    assert heads == [x for x in DM.SECTION_ORDER if x in heads]
    assert doc["front"]["motion"]["surface-enter"]["duration"].endswith("ms")
    assert GN.from_design_md(md) == g
    for x in DM.catalog()["looks"]:
        h = GN.from_design_md(DM.md_text(x["id"]))
        assert GN.audit(h) == [], x["id"]
        bg = DM._entry(x["id"])["doc"]["roles"]["bg"]
        assert (h["colour"]["mode"] == "dark") == (DM.lum(bg) < 0.2), x["id"]
    lin = GN.from_design_md(DM.md_text("linear-app"))
    assert lin["colour"]["mode"] == "dark"                               # 'canvas', not 'bg'
