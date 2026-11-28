"""v0.999.334 the Ant Design read, built (github.com/ant-design/ant-design c046700, MIT):
1. Ant's own DESIGN.md is look 84 of the Web Studio catalog ("Enterprise console"), credited to its repo;
2. its business-screen specs (results, errors, empty states, search-and-filter lists, record pages, dashboards,
   settings, long forms) as UX rules for the writers and the critic, and a Result part in the React kit;
3. its number / date / wording specs for every country: @/lib/format + src/lib/locale.ts (app_engine action=locale),
   the kit off its fixed India formats, and code checks for typed currency signs, toFixed on money, fixed locales,
   hand-built dates and 'Submit' / 'Click here' / '!' buttons.

The real build needs the image's packages (HOOLA_APPENGINE_NODE_MODULES); without them that one test skips."""
import gzip
import json
import os
from pathlib import Path

import pytest

from tests.test_v0999_322_bolt_ideas import PLAN, _refused, _tool, gate_env  # noqa: F401  (fixture + helpers)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app"
TPL = ROOT / "appengine" / "template"


# ---------------------------------------------------------------- 1. the catalog
def test_ant_designs_own_design_md_is_look_84_credited_to_its_repo():
    from app.site import designmd as DM
    c = DM.catalog()
    assert c["total"] == 84
    card = next(x for x in c["looks"] if x["id"] == "ant-design")
    assert card["name"] == "Enterprise console" and card["cat"] == "saas" and card["new"] and not card["dark"]
    assert card["t"]["acc"] == "#1677ff" and card["t"]["bg"] == "#ffffff"
    lk = DM.look("ant-design")
    assert "github.com/ant-design/ant-design publishes (MIT)" in lk["source_note"]
    assert "Ant" not in lk["description"] and "the brand" in lk["description"]        # its name never shown as a brand
    assert any("readable button text" in x["message"] for x in lk["lint"])               # 4.1:1 said, and fixed by Hoola
    assert DM.ref_for("ant-design")                                                     # usable as look 1
    lic = (DM.LIB / "LICENSE.txt").read_text()
    assert "github.com/ant-design/ant-design (c046700 2026-11-28)" in lic and "Ant UED" in lic and lic.count("MIT License") == 1


def test_the_catalog_build_keeps_looks_added_from_other_repos(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("dmb", ROOT.parent / "tools" / "designmd_build.py")
    dmb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dmb)
    out = tmp_path / "lib"
    out.mkdir()
    old = {"source": {}, "looks": [{"id": "ant-design", "name": "Enterprise console", "text": "---\nname: x\n---\n",
                                    "from": {"repo": "github.com/ant-design/ant-design"}, "cat": "saas", "src": "ant.design"}]}
    (out / "looks.json.gz").write_bytes(gzip.compress(json.dumps(old).encode()))
    (out / "LICENSE.txt").write_text("old\n\n---------------------------------------------------------------- ant\nANT LICENCE")
    src = tmp_path / "awesome"
    (src / "design-md" / "airbnb").mkdir(parents=True)
    (src / "design-md" / "airbnb" / "DESIGN.md").write_text("---\nname: a\n---\n")
    (src / "README.md").write_text("### E-commerce & Retail\n- [**Airbnb**](https://getdesign.md/airbnb/design-md) - Marketplace. Warm coral\n")
    (src / "LICENSE").write_text("MIT License\n")
    monkeypatch.setattr(dmb, "OUT", out)
    dmb.main(str(src))
    ids = [x["id"] for x in json.loads(gzip.decompress((out / "looks.json.gz").read_bytes()))["looks"]]
    assert ids == ["airbnb", "ant-design"]
    assert "ANT LICENCE" in (out / "LICENSE.txt").read_text()


# ---------------------------------------------------------------- 2. business screens
def test_business_screens_get_their_rules_and_every_rule_fits():
    from app.coder import bizrules as BR, uxrules as U
    assert set(BR.RULES) == {"states", "tables", "detail", "dashboard", "settings", "long_forms", "numbers", "words"}
    for k, rows in BR.RULES.items():
        for r in rows:
            assert r["Issue"] and r["Do"] and len(U._line(r)) <= 170, r
    assert U.topics_of("screen_table") == ["states", "tables", "words"]
    assert "dashboard" in U.topics_of("screen_dashboard") and "settings" in U.topics_of("screen_settings")
    assert "detail" in U.topics_of("screen_detail") and "long_forms" in U.topics_of("screen_form")
    assert "numbers" in U.topics_of("pricing_table") and "numbers" not in U.topics_of("hero")
    assert U.topics_of("hero") == [] and U.topics_of("const rows = items.map((x) => x)") == []   # nothing for most sections
    blk = U.block(U.topics_of("screen_table of invoices with the amount due"))
    assert "Result After Submit" in blk and "Filters Above the List" in blk and "Currency the Country's Way" in blk
    assert "Button Says the Action" in blk and "Hoola's design rules" in blk
    assert len(blk) <= U.CHARS_MAX and blk.count("\n- ") >= 10                  # many topics get a little more room
    old = U.block(["forms", "maps"])                                            # v0.999.330's rules unchanged
    assert "Preserve Input After Failed Submit" in old and "Map Attribution Visible" in old


def test_the_writers_and_the_critic_get_the_screen_rules():
    from app.appengine import critic as CR, writer as W
    from app.site import service as SS
    assert "Filters Above the List" in W.ux_rules({"type": "screen_table", "heading": "Invoices"})
    assert "Result After Submit" in SS._ux_rules({"type": "screen_form", "heading": "Admission"})
    txt = CR.ux_text([{"type": "screen_dashboard", "heading": "Today"}], {})
    assert "Key Numbers First" in txt
    probs = CR.ux_measure({"src/components/sections/Bill.tsx": '<p>Total ₹{total}</p><button type="button">Submit</button>'},
                          [{"block": "custom", "component": "Bill", "sec": "s3", "page": "Home"}])
    assert probs and probs[0]["fix"] == "rewrite" and probs[0]["sec"] == "s3"
    assert any("Currency the Country's Way" in x for x in probs[0]["ux"]) and any("Button Says" in x for x in probs[0]["ux"])


def test_the_result_part_is_in_the_kit_and_passes_the_rules():
    from app.appengine import image as IMG, kit as KIT, rules as RL, service as AE, syntax as SX
    rel = "src/components/ui/result.tsx"
    code = (TPL / rel).read_text()
    assert RL.check_file(rel, code, set(IMG.CORE)) == [] and SX.check(rel, code) in ([], None)
    for st in ("success", "error", "403", "404", "500", "offline"):
        assert f'"{st}"' in code
    assert 'role={loud ? "alert" : "status"}' in code
    assert "result" in KIT.ui_parts() and rel in AE.NEW_KIT
    assert "Result (result" in AE.REACT_PARTS and "Empty (empty" in AE.REACT_PARTS


# ---------------------------------------------------------------- 3. numbers, money, dates, words
def test_the_code_checks_name_the_rule_and_the_fix():
    from app.coder import uxrules as U
    bad = {
        '<p>₹{price}</p>': "typed currency sign",
        'const s = "€" + amount;': "typed currency sign",
        'const s = `£${total}`;': "typed currency sign",
        '<b>Rs. {fee}</b>': "typed currency sign",
        'const t = order.total.toFixed(2);': "toFixed",
        'n.toLocaleString("en-US")': "fixed to one country",
        'new Intl.NumberFormat("en-IN").format(n)': "fixed to one country",
        'const d = `${x.getDate()}/${x.getMonth() + 1}`;': "built by hand",
        '<button type="submit">Submit</button>': "Button Says the Action",
        '<a href="/menu">Click here</a>': "Button Says the Action",
        '<Button>Order now!</Button>': "Calm Tone",
    }
    for code, word in bad.items():
        assert any(word in p for p in U.code_problems(code)), code
    good = ['<p>{money(price)}</p>', '<p>{num(n)}</p>', 'const r = (score / max * 100).toFixed(1);',
            '<button type="submit">Send enquiry</button>', '{ unit: "₹" }', '<p>₹500 off this week</p>',
            'new Intl.DateTimeFormat("en-GB", { timeZone: TIME_ZONE })', 'n.toLocaleString(LOCALE)']
    for code in good:
        assert U.code_problems(code) == [], (code, U.code_problems(code))


def test_the_kit_shows_money_and_numbers_in_the_apps_own_country():
    from app.coder import uxrules as U
    kit = (TPL / "src/components/blocks/_kit.tsx").read_text()
    assert 'return money(n);' in kit and '"₹" + n' not in kit
    fmt = (TPL / "src/lib/format.ts").read_text()
    for f in ("export function money", "export function num", "export function date", "export function range",
              "export function ago", "RelativeTimeFormat", "formatRange"):
        assert f in fmt, f
    seen = []
    for f in (TPL / "src").rglob("*.tsx"):
        if ".test." in f.name or "/ui/" in str(f):
            continue
        txt = f.read_text()
        assert '"en-IN"' not in txt or "schedule" in f.name, f
        assert "Asia/Kolkata" not in txt, f
        seen += [x for x in U.code_problems(txt) if not x.startswith("Input Labels")]
    assert seen == []                                                           # Hoola's own kit follows the rules


def test_her_country_is_set_with_action_locale(gate_env):
    from app.appengine import rules as RL, service as AE
    aid = _tool(action="create", name="Bakery", brief="A bakery in Boston")["id"]
    r = AE._load(T, aid)
    assert "en-IN" in (AE.src_dir(r) / "src/lib/locale.ts").read_text()
    assert "starting choice" in AE._locale_line(r)
    shown = _tool(action="locale", app=aid)                                     # no values = shows it, no plan needed
    assert shown["locale"]["currency"] == "INR"
    assert "Record your plan" in _refused(action="locale", app=aid, locale="en-US", currency="USD")
    _tool(action="blueprint", app=aid, what="a bakery site", users=["visitors"], screens=["home"], data=[],
          out_of_scope=[], questions=[])
    _tool(action="plan", app=aid, **PLAN)
    res = _tool(action="locale", app=aid, locale="en_us", currency="usd", time_zone="America/New_York")
    assert res["locale"] == {"locale": "en-US", "currency": "USD", "time_zone": "America/New_York"}
    r = AE._load(T, aid)
    txt = (AE.src_dir(r) / "src/lib/locale.ts").read_text()
    assert 'LOCALE = "en-US"' in txt and 'CURRENCY = "USD"' in txt and 'TIME_ZONE = "America/New_York"' in txt
    assert "starting choice" not in AE._locale_line(r) and "USD" in AE._locale_line(r)
    assert "not a currency code" in _refused(action="locale", app=aid, currency="dollars")
    assert "not a time zone" in _refused(action="locale", app=aid, time_zone="Moon/Base")
    assert "src/lib/locale.ts" in RL.LOCKED and "src/lib/format.ts" in RL.LOCKED
    AE._refresh_template(r)                                                     # a refresh keeps her country
    assert 'CURRENCY = "USD"' in (AE.src_dir(r) / "src/lib/locale.ts").read_text()
    from app.agent import turnmode as TM
    tok = TM.APP.set(aid)
    try:
        assert "Country: money as USD, numbers and dates the en-US way" in AE.prompt_block(T)
    finally:
        TM.APP.reset(tok)


def test_hoola_is_told_how_to_show_numbers_and_results():
    from app.agent.appengine_tools import APPENGINE_TOOLS
    from app.appengine import writer as W
    desc = APPENGINE_TOOLS[0]["description"]
    assert "action=locale" in desc and "@/lib/format" in desc and "Result" in desc
    props = APPENGINE_TOOLS[0]["input_schema"]["properties"]
    assert {"locale", "currency", "time_zone"} <= set(props) and "locale" in props["action"]["enum"]
    src = Path(W.__file__).read_text()
    assert '"@/lib/format"' in src and "result = Result" in src
    agents = (TPL / "AGENTS.md").read_text()
    assert "`@/lib/format`" in agents and "action=locale" in agents and "`Result`" in agents


@pytest.mark.skipif(not os.environ.get("HOOLA_APPENGINE_NODE_MODULES"), reason="needs the image's packages (HOOLA_APPENGINE_NODE_MODULES)")
def test_a_real_app_shows_dollars_us_dates_and_a_result_page(site_env, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENGINE_DIR", str(tmp_path / "appengine"))
    monkeypatch.setenv("HOOLA_APPENGINE_AUTOBUILD", "0")
    monkeypatch.setenv("APP_ENGINE_RUNNER", "local")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.db import init_db
    init_db()
    from app.appengine import service as AE
    aid = AE.create(T, "Boston bakery", "A bakery")["id"]
    AE.set_locale(T, aid, "en-US", "USD", "America/New_York")
    page = '''import { Seo } from "@/lib/seo";
import { Result } from "@/components/ui/result";
import { money, date, num } from "@/lib/format";
import { Button } from "@/components/ui/button";

export default function Done() {
  return (
    <main>
      <Seo title="Order placed" description="Your order" />
      <p data-t="m">{money(1499)}</p>
      <p data-t="n">{num(1234567)}</p>
      <p data-t="d">{date("2026-11-28T15:00:00Z")}</p>
      <Result status="success" title="Order 1042 is placed" sub="We will call you within an hour." extra={<Button>See your orders</Button>} />
      <Result status="404" />
    </main>
  );
}
'''
    AE.write(T, aid, "src/pages/Done.tsx", page)
    d = AE.src_dir(AE._load(T, aid))
    app = (d / "src/App.tsx").read_text().replace('import { Routes, Route } from "react-router-dom";',
                                                  'import { Routes, Route } from "react-router-dom";\nimport Done from "./pages/Done";')
    AE.write(T, aid, "src/App.tsx", app.replace('<Route path="*"', '<Route path="/done" element={<Done />} />\n      <Route path="*"'))
    home = (d / "src/pages/Home.tsx").read_text()
    AE.write(T, aid, "src/pages/Home.tsx", 'import { Link } from "react-router-dom";\n' + home.replace("</main>", '<Link to="/done">Done</Link></main>', 1))
    b = AE.build(T, aid)
    assert b["built"], b["say"]
    lb = json.loads(AE._load(T, aid).last_build)
    assert lb["types_ok"], lb.get("types")                                       # the whole kit type-checks with format
    r = AE._load(T, aid)
    html = (AE.ver_dir(r, r.version) / "dist" / "done" / "index.html").read_text()
    assert "$1,499" in html and "1,234,567" in html and "Nov 28, 2026" in html, html[-3000:]
    assert "Order 1042 is placed" in html and "This page was not found" in html and 'role="status"' in html
