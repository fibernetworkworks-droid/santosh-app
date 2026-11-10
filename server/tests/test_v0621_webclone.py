"""v0.694.0 WEB CLONE - 20 cases (16 functions), ZERO network, ZERO browser.

The rebuild-from-spec lane (the sandbox recycle ate the first build mid-flight; the spec is the
commit message): capture -> endpoints -> assemble. Every check here runs offline on fixtures:
the converter units (attr casing, class join, style double-brace with duplicate-props last-wins,
whitespace string expressions), the svg lane, the per-file CSS rewrite with its src markers, the
asset map keyed by absolute URL AND path, srcset rewrite, root-attr carry, the fragment law,
project completeness, the endpoints scan shape, SSRF refusals, the brand-refusal law,
registration 616, admit routing positives and the git-clone / site-banao negatives."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

from app.webclone import assemble, capture, endpoints_adapter  # noqa: E402
from app.webclone.assemble import build_asset_map, html_to_jsx  # noqa: E402

ORIGIN = "https://example.org"


def _mini_site(tmp_path: Path) -> Path:
    """A tiny captured bundle: dom + one css + manifest with two assets."""
    b = tmp_path / "bundle"
    b.mkdir(parents=True)
    (b / "dom.html").write_text(
        '<!doctype html><html lang="en" class="js no-js"><head><title>Mini Site</title></head>'
        '<body id="top" class="theme-dark"><header class="wrap"><h1 style="color: red; color: blue; '
        'margin-top: 4px">Mini</h1>'
        '<img src="/img/hero.png" srcset="/img/hero.png 1x, https://cdn.example.org/img/hero@2x.png 2x">'
        '<svg viewBox="0 0 24 24" class="ico"><path d="M4 4h16v16H4z"/><animate attributeName="x" dur="1s"/>'
        '</svg><p>  spaced  text  </p><a href="/docs/guide.html">guide</a></body></html>', encoding="utf-8")
    (b / "css0001.css").write_text(
        "body{background:url(/img/bg.png)}h1{color:red}\n@import url(/css/more.css)\n", encoding="utf-8")
    (b / "manifest.json").write_text(json.dumps({
        "url": ORIGIN + "/", "origin": ORIGIN, "title": "Mini Site", "dom_chars": 300,
        "css_files": [{"name": "css0001.css", "url": ORIGIN + "/css/main.css"}],
        "assets": [{"name": "img-hero.png", "url": ORIGIN + "/img/hero.png", "kind": "img"},
                   {"name": "img-hero-2.png", "url": "https://cdn.example.org/img/hero@2x.png", "kind": "img"},
                   {"name": "img-bg.png", "url": ORIGIN + "/img/bg.png", "kind": "css-ref"}],
        "js_files": [], "skipped": [], "notes": [],
    }), encoding="utf-8")
    for name in ("img-hero.png", "img-hero-2.png", "img-bg.png"):   # the captured bytes themselves
        (b / name).write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    return b


def test_attr_casing_and_numeric_props():
    dom = '<table><td colspan="2" rowspan="3" tabindex="0"></td></table><label for="x">n</label>'
    jsx = html_to_jsx("<html><body>" + dom + "</body></html>", {}, ORIGIN)
    assert "colSpan={2}" in jsx and "rowSpan={3}" in jsx and "tabIndex={0}" in jsx
    assert 'htmlFor="x"' in jsx


def test_class_list_joined_and_style_double_brace():
    dom = '<p class="a b" style="color: red; margin-top: 4px">x</p>'
    jsx = html_to_jsx("<html><body>" + dom + "</body></html>", {}, ORIGIN)
    assert 'className="a b"' in jsx
    assert 'style={{color: "red", marginTop: "4px"}}' in jsx


def test_duplicate_style_props_last_wins():
    dom = '<h1 style="color: red; color: blue">t</h1>'
    jsx = html_to_jsx("<html><body>" + dom + "</body></html>", {}, ORIGIN)
    assert 'color: "red"' not in jsx and 'color: "blue"' in jsx


def test_significant_whitespace_as_string_expr():
    dom = "<p>  spaced  text  </p>"
    jsx = html_to_jsx("<html><body>" + dom + "</body></html>", {}, ORIGIN)
    assert '{"  spaced  text  "}' in jsx


def test_svg_lane():
    dom = '<svg viewBox="0 0 24 24"><path d="M4 4"/><animate attributeName="x"/></svg>'
    jsx = html_to_jsx("<html><body>" + dom + "</body></html>", {}, ORIGIN)
    assert 'viewBox="0 0 24 24"' in jsx and "<path" in jsx
    assert "animate" not in jsx


def test_css_rewrite_captured_and_uncaptured(tmp_path):
    b = _mini_site(tmp_path)
    m = json.loads((b / "manifest.json").read_text())
    amap = build_asset_map(m)
    css = (b / "css0001.css").read_text()
    out = assemble._css_chunks(css, m["css_files"][0]["url"], amap, ORIGIN)
    assert "url(/assets/img-bg.png)" in out                     # captured -> /assets
    assert "url(https://example.org/css/more.css)" in out       # uncaptured -> absolute origin


def test_css_src_markers_kept(tmp_path):
    b = _mini_site(tmp_path)
    proj = tmp_path / "proj"
    assemble.assemble_project(b, proj)
    globals_css = (proj / "app/globals.css").read_text()
    assert "/* src: " + ORIGIN + "/css/main.css */" in globals_css


def test_asset_map_keys_absolute_and_path():
    m = {"assets": [{"name": "a.png", "url": "https://h.test/x/a.png", "kind": "img"}]}
    amap = build_asset_map(m)
    assert amap["https://h.test/x/a.png"] == "/assets/a.png"
    assert amap["/x/a.png"] == "/assets/a.png"


def test_srcset_candidates_rewritten_one_by_one(tmp_path):
    b = _mini_site(tmp_path)
    proj = tmp_path / "proj"
    assemble.assemble_project(b, proj)
    page = (proj / "app/page.tsx").read_text()
    assert 'srcSet="/assets/img-hero.png 1x, /assets/img-hero-2.png 2x"' in page  # both candidates captured


def test_root_attrs_carried_into_layout(tmp_path):
    b = _mini_site(tmp_path)
    proj = tmp_path / "proj"
    assemble.assemble_project(b, proj)
    layout = (proj / "app/layout.tsx").read_text()
    assert '<html lang="en" className="js no-js">' in layout
    assert '<body id="top" className="theme-dark">' in layout


def test_fragment_law_no_injected_main(tmp_path):
    b = _mini_site(tmp_path)
    proj = tmp_path / "proj"
    assemble.assemble_project(b, proj)
    page = (proj / "app/page.tsx").read_text()
    assert page.count("<>") == 1 and "<main" not in page and "<body" not in page


def test_project_completeness(tmp_path):
    b = _mini_site(tmp_path)
    proj = tmp_path / "proj"
    summary = assemble.assemble_project(b, proj, endpoints_md="# ep\n")
    for rel in ("package.json", "next.config.mjs", "tsconfig.json", "app/layout.tsx",
                "app/page.tsx", "app/globals.css", "README.md", "ENDPOINTS.md",
                "public/assets/img-hero.png", "clone-summary.json"):
        assert (proj / rel).exists(), rel
    pkg = json.loads((proj / "package.json").read_text())
    assert pkg["dependencies"]["next"] and (proj / "public/assets/img-bg.png").exists()
    assert summary["title"] == "Mini Site"


def test_endpoints_scan_shape(tmp_path):
    b = _mini_site(tmp_path)
    ep = endpoints_adapter.scan(b, "mini")
    for key in ("counts", "top_hosts", "urls", "api_paths", "ips"):
        assert key in ep
    assert ep["kind"] == "webclone-capture"
    assert any("example.org" in h for h in ep["top_hosts"])


def test_guard_url_refuses_private_and_loopback():
    from app.agent.scrape_tools import _guard_url
    for bad in ("http://127.0.0.1/x", "http://10.0.0.5/x", "http://169.254.169.254/latest/meta-data/",
                "http://[::1]/", "ftp://h.test/x"):
        with pytest.raises(Exception):
            _guard_url(bad)
    assert _guard_url("https://example.org/").startswith("https://")


def test_capture_asset_fetch_skips_private():
    import httpx
    got = capture._fetch(httpx.Client(), "http://127.0.0.1:9/secret")
    assert got is None                              # guard raises inside -> asset-level skip


def test_brand_refusal_law():
    from app.agent.webclone_tools import _looks_like_own_or_reference
    assert _looks_like_own_or_reference("https://www.amazon.in/gp")[0] is True
    assert _looks_like_own_or_reference("https://github.com/fnw")[0] is True
    ok, _ = _looks_like_own_or_reference("https://myshop.example.com", own_domains=("myshop.example.com",))
    assert ok is False
    assert _looks_like_own_or_reference("https://example.org")[0] is False


def test_tool_description_carries_the_laws():
    from app.agent.webclone_tools import WEBCLONE_TOOLS
    d = WEBCLONE_TOOLS[0]["description"]
    for law in ("learn", "migrate", "archive", "NOTHING is ever published", "not pixel-perfect",
                "git clone", "brand theft"):
        assert law in d, law


def test_registration_616():
    from app.agent.tools import FAMILY_OF, HANDLERS, TOOLS, TOOL_LABELS
    assert len(TOOLS) == 622, "617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 615 (their v0.693.0 base keeps 615) + 1 web_clone (v0.694.0 WEB CLONE)"
    assert TOOL_LABELS.get("web_clone") and HANDLERS.get("web_clone")
    assert FAMILY_OF["web_clone"] == "webclone"


def test_admit_routing_positives():
    from app.agent import admit
    for ask in ("is site ko clone kar do: https://example.com", "website clone kar do meri purani site ka",
                "web clone https://example.org"):
        why = admit.route(ask)
        assert why.get("webclone"), ask


def test_admit_negatives_git_clone_and_site_banao():
    from app.agent import admit
    assert not admit.route("git clone this repo").get("webclone")
    assert not admit.route("site banao mere business ke liye").get("webclone")


def test_honest_line_in_notes_and_readme(tmp_path):
    b = _mini_site(tmp_path)
    proj = tmp_path / "proj"
    assemble.assemble_project(b, proj)
    readme = (proj / "README.md").read_text()
    assert "NOT pixel-perfect" in readme.replace("pixel-perfect", "pixel-perfect") or "not pixel-perfect" in readme.lower()
    assert "static" in readme.lower()
