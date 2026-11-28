"""v0.999.329 UI/UX PRO MAX, BROUGHT UP TO DATE AND USED WHERE THINGS ARE BUILT (owner: "GO BUILD 1 2 3 4"):

1. the vendored engine + data = upstream 11ca2b3 (141 UX rules incl. form errors + maps, 23 stacks, exact hex lookup);
2. the UX rules reach the builders: the React writer's custom sections, the HTML section writer, Hoola's per-turn App
   Engine summary, the critic (rules to judge + rules code checks in the custom sections, sent back as rewrites), and a
   UX check named on every App Engine page write (told, never refused);
3. uiux_design passes the dials, the design tokens and a preview page (into her chat as a file card);
4. Hoola's own map screens follow the map rules (console riders map, the phone kit map, a website's map).
"""
import asyncio
import json
import os
import re
from pathlib import Path

import pytest

from app.coder import uiux_tool, uxrules as UX
from tests.test_v0486_hoola_uiux_skill import _Ctx, desk  # noqa: F401  (fixture)
from tests.test_v0999_322_bolt_ideas import gate_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

APP = Path(__file__).resolve().parents[1] / "app"
DATA = APP / "coder" / "uiux" / "data"


# ---------------------------------------------------------------- 1. the engine is upstream 11ca2b3
def test_engine_and_data_are_the_new_upstream():
    cat = json.loads((DATA / "catalog-summary.json").read_text())["counts"]
    assert cat["uxGuidelines"] == 141 and cat["stacks"] == 23 and cat["palettes"] == 194
    assert (DATA / "stacks" / "pyside6-qss.csv").is_file()
    assert (APP / "coder" / "uiux" / "scripts" / "preview.py").is_file()
    issues = {r["Issue"] for r in UX.rows()}
    assert {"Never Block Paste", "Preserve Input After Failed Submit", "Map Attribution Visible"} <= issues
    assert "11ca2b3" in (APP / "coder" / "uiux" / "PROVENANCE.md").read_text()
    out = uiux_tool._run_engine(["#2563EB", "--domain", "color", "-n", "1"])
    assert "#2563EB" in out and "Found:** 1" in out             # a hex finds its palette


# ---------------------------------------------------------------- 3. the tool passes what the engine can do
def test_args_carry_dials_tokens_preview_and_drop_bad_dials():
    a = uiux_tool._build_args("spa", True, None, None, 3, False, None, None, "/v", variance=12, motion=3,
                              density="x", tokens="css", preview_dir="/v/p", lang="ar", direction="rtl")
    assert a[:2] == ["spa", "--design-system"] and "--variance" not in a and "--density" not in a
    assert a[a.index("--motion") + 1] == "3" and a[a.index("--tokens") + 1] == "css"
    assert a[a.index("--output-dir") + 1] == "/v/p" and "--preview" in a and "rtl" in a
    p = uiux_tool._build_args("spa", True, None, None, 3, True, "Spa", None, "/v", preview_dir="")
    assert "--preview" in p and p[p.index("--output-dir") + 1] == "/v" and "--force" not in p


def test_tool_tokens_and_honest_refusals(desk):
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="beauty spa wellness", design_system=True, tokens="css"))
    assert r["tokens"] == "css" and "--color-primary:" in r["text"]
    assert "only with design_system" in asyncio.run(uiux_tool.uiux_design(_Ctx(), query="spa", domain="ux", motion=4))["error"]
    assert "tokens format" in asyncio.run(uiux_tool.uiux_design(_Ctx(), query="spa", design_system=True, tokens="scss"))["error"]
    assert "language tag" in asyncio.run(uiux_tool.uiux_design(_Ctx(), query="spa", design_system=True, lang="x; rm"))["error"]
    s = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="desktop app dark theme", stack="pyside6-qss"))
    assert s["mode"] == "stack:pyside6-qss" and "Found:" in s["text"]


def test_preview_page_lands_in_her_chat_from_her_vault(desk, monkeypatch):
    from app import chatfiles
    from app.events import bus
    sent = []
    monkeypatch.setattr(bus, "publish", lambda conv, kind, payload: sent.append((conv, kind, payload)))
    r = asyncio.run(uiux_tool.uiux_design(_Ctx(), query="arabic bakery shop", design_system=True, preview=True,
                                          lang="ar", direction="rtl", project="Bakery"))
    assert r["preview"].get("file_id"), r
    conv, kind, card = sent[-1]
    assert (conv, kind) == ("c1", "pc_file") and card["source"] == "uiux" and card["name"].endswith(".html")
    page = chatfiles._meta(T, card["file_id"])
    assert page
    vault = uiux_tool.tenant_outdir(T)
    assert any(Path(vault, "previews").rglob("preview.html"))       # written inside her own vault
    # a path the engine printed outside her vault is never shared
    assert uiux_tool._preview_file("Design system preview: /etc/passwd.html", [vault]) is None


# ---------------------------------------------------------------- 2. the rules where things are built
def test_topics_and_rule_blocks():
    assert UX.topics_of("contact-block: Get in touch") == ["forms"]
    assert UX.topics_of("hero: Fresh bread daily") == []
    assert UX.topics_of("<div data-hoola-map> find us") == ["maps"]
    assert "data_maps" in UX.topics_of("maplibre choropleth by region")
    b = UX.block(["forms", "maps"])
    assert "Preserve Input After Failed Submit" in b and "Map Attribution Visible" in b and len(b) <= UX.CHARS
    assert UX.prompt_for("hero section") == ""


def test_code_problems_name_their_rule_and_pass_good_code():
    bad = ('<form><input placeholder="Your email" name="email" onPaste={(e) => e.preventDefault()} />'
           '<Button type="submit" disabled={!valid}>Send</Button></form>')
    got = " ".join(UX.code_problems(bad))
    for rule in ("Never Block Paste", "Submit Button Not Pre-Disabled", "Input Labels", "Input Types"):
        assert rule in got
    good = ('<form><label htmlFor="e">Email</label><input id="e" name="email" type="email" />'
            '<button type="submit" disabled={sending}>Send</button></form>')
    assert UX.code_problems(good) == []
    m = UX.code_problems("new maplibregl.Map({container: 'm', attributionControl: false, keyboard: false}); p.setHTML(x)")
    assert {x.split(":")[0] for x in m} == {"Map Attribution Visible", "Map Keyboard and Non-Drag Navigation",
                                            "Safe Map Popup Content", "Map Text Alternative"}


def test_the_writers_get_the_rules_for_what_a_section_holds():
    from app.appengine import writer as W
    from app.site import service as S
    sec = {"type": "custom_enquiry", "label": "An enquiry form for wedding cakes", "heading": "Ask us"}
    assert "Preserve Input After Failed Submit" in W.ux_rules(sec) and W.ux_rules({"type": "custom_story", "label": "Our story"}) == ""
    assert "Map Text Alternative" in S._ux_rules({"type": "map_hours", "brief": "where we are"})
    src = (APP / "appengine" / "writer.py").read_text()
    assert "prompt += ux_rules(s)" in src
    assert "_section_prompt(r, slug, s, others, extra) + _ux_rules(s)" in (APP / "site" / "service.py").read_text()


def test_the_critic_judges_the_rules_and_code_checks_send_a_rewrite():
    from app.appengine import critic as CR
    rows = [{"sec": "home:custom_enquiry", "page": "home", "type": "custom_enquiry", "block": "custom",
             "component": "EnquirySection"}, {"sec": "home:map_hours", "page": "home", "type": "map_hours",
                                               "block": "map_hours"}]
    code = {"src/components/sections/EnquirySection.tsx": '<form><input placeholder="Phone" name="phone" />'
                                                        '<Button type="submit" disabled={!ok}>Send</Button></form>'}
    m = CR.ux_measure(code, rows)
    assert m and m[0]["fix"] == "rewrite" and m[0]["sec"] == "home:custom_enquiry" and "Input Labels" in m[0]["why"]
    done, notes = CR.apply({}, m, rows, {})
    assert notes == {"home:custom_enquiry": m[0]["why"]}            # the writer rewrites it with the rule named
    t = CR.ux_text(rows)
    assert "judge only what the screenshots show" in t and "Map Attribution Visible" in t and "Input Labels" in t
    src = (APP / "appengine" / "critic.py").read_text()
    assert "measure(sh, rows) + ux_measure(cur[\"code\"], rows)" in src and "ux = ux_text(rows, code)" in src and "code=cur[\"code\"]" in src


def test_app_engine_write_names_the_ux_check_and_the_summary_carries_the_rules(gate_env, monkeypatch):
    from app.appengine import service as AE
    from app.agent import turnmode as TM
    a = AE.create(T, name="Cake orders", brief="orders")
    res = AE.write(T, a["id"], "src/pages/Order.tsx",
                   'export default function Order() {\n  return (<form><input placeholder="Your email" name="email" />'
                   '<button type="submit" disabled={!ok}>Send</button></form>);\n}\n')
    assert res["ux"] and "UX check (fix these)" in res["say"] and "Input Types" in res["say"]
    tok = TM.APP.set(a["id"])
    try:
        blk = AE.prompt_block(T)
    finally:
        TM.APP.reset(tok)
    assert "UX RULES for what this holds" in blk and "Preserve Input After Failed Submit" in blk
    assert AE.ux_check("src/components/ui/input.tsx", "<input />") == []      # the kit's parts are building blocks


def test_every_kit_page_block_already_follows_the_checked_rules():
    from app.appengine import service as AE
    root = APP / "appengine" / "template"
    bad = {}
    for f in root.rglob("*.tsx"):
        rel = f.relative_to(root).as_posix()
        p = AE.ux_check(rel, f.read_text("utf-8"))
        if p:
            bad[rel] = p
    assert bad == {}                                  # screen-board's add button is no longer pre-disabled


# ---------------------------------------------------------------- 4. Hoola's own map screens
def test_hoolas_map_screens_follow_the_map_rules():
    js = (APP / "static" / "console" / "build.js").read_text()
    assert 'class="stmap" role="region"' in js and 'role="img" aria-label="Riders on shift"' not in js
    assert "stmaplist" in js and "m.togglePopup()" in js and "d.tabIndex = 0" in js
    kt = (APP / "appmaker" / "android" / "template" / "app" / "src" / "main" / "java" / "hoola" / "kit" / "Track.kt").read_text()
    assert 'role="region" aria-label="Map"' in kt and "el.tabIndex=0" in kt and "mk.togglePopup()" in kt
    assert "semantics { contentDescription = said }" in kt and "import androidx.compose.ui.semantics.semantics" in kt
    html = kt[kt.index('MAP_HTML = """'):kt.index('</html>"""')]
    assert "$" not in html                           # a Kotlin raw string: no stray template
    for code in (js[js.index("async function ridersMap"):js.index("async function loadAppData")], html):
        assert "attributionControl: false" not in code and "keyboard: false" not in code and ".setHTML(" not in code
    site = (APP / "site" / "assets" / "hoola-site.js").read_text()
    assert "hs-map-cap" in site and "'Map' + (where ? ': ' + where.textContent : '')" in site
