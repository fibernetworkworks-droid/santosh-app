"""v0.787 CHHOTA BADLAAV (L4 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L4"): small exact changes to a website's code
(search -> one exact replace, no AI rewrite) and tiered checks (a one-section change is checked on its own page only;
the full check runs again before the site goes live)."""
import asyncio
import json
import time

import pytest

from tests.test_life import conv_ctx
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def _site(S):
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    return v["id"]


def _fake_checks(monkeypatch, calls):
    """The browser check as a recorder: a full run checks every page, a quick run only the pages it is given."""
    from app.site import checks as C

    def run(out, plan, shots_dir=None, video=True, only=None, quick=False):
        pages = list(only) if only else [p["slug"] for p in plan.get("pages", [])]
        calls.append({"only": list(only or []), "quick": quick})
        rep = {"pages": {p: {"issues": [], "warnings": [], "blanks": 0, "samples": 0, "checked": "quick" if quick else "full"}
                         for p in pages}, "blocking": [], "warnings": [], "scores": {"js_kb": 10}, "source": "hoola"}
        rep["passed"] = True
        return rep
    monkeypatch.setattr(C, "run", run)


def test_search_names_file_and_line(site_env):
    from app.site import lineedit as LE
    from app.site import service as S
    sid = _site(S)
    r = S._load(sid)
    hit = LE.search(r, "Sharma Sweets")
    assert hit["total"] >= 1 and all({"file", "line", "text"} <= set(h) for h in hit["hits"])
    assert all(h["file"].startswith(("pages/", "design/")) for h in hit["hits"])
    assert "Sharma Sweets" in hit["hits"][0]["text"] or "sharma sweets" in hit["hits"][0]["text"].lower()
    assert LE.search(r, "zzz-not-here")["total"] == 0
    with pytest.raises(LE.LineEditError):
        LE.search(r, "  ")


def test_exact_edit_once_or_refused(site_env, monkeypatch):
    calls = []
    _fake_checks(monkeypatch, calls)
    from app.site import lineedit as LE
    from app.site import service as S
    sid = _site(S)
    path = "pages/home/hero.html"
    code = S.code_read(T, sid, path)["code"]
    first = code.splitlines()[0]
    with pytest.raises(LE.LineEditError, match="not in"):
        LE.edit(T, sid, path, "<p>words that are nowhere</p>", "x")
    twice = "<"                                                                         # surely more than once
    with pytest.raises(LE.LineEditError, match="appears"):
        LE.edit(T, sid, path, twice, "[")
    with pytest.raises(LE.LineEditError):
        LE.edit(T, sid, path, first, first)
    with pytest.raises(LE.LineEditError):
        LE.edit(T, sid, "", first, "x")
    ver = S.get(T, sid)["version"]
    out = LE.edit(T, sid, path, first, first.replace("<section", '<section data-tone="grey"', 1))
    assert out["changed"] and "data-tone" in out["diff"] and S.get(T, sid)["version"] == ver + 1
    assert 'data-tone="grey"' in S.code_read(T, sid, path)["code"]
    S.undo_edit(T, sid)                                                                  # one Undo step
    assert 'data-tone' not in S.code_read(T, sid, path)["code"]
    bad = LE.edit(T, sid, path, first, first + '<script>alert(1)</script>')               # the same cleaner as every build
    assert "<script" not in S.code_read(T, sid, path)["code"] and bad["removed"]


def test_quick_check_then_full_before_live(site_env, monkeypatch):
    calls = []
    _fake_checks(monkeypatch, calls)
    from app.site import hosting as H
    from app.site import lineedit as LE
    from app.site import service as S
    sid = _site(S)
    S.save_version(sid, "a full check first")                                             # the base: a full report
    assert json.loads(S._load(sid).checks)["tier"] == "full"
    calls.clear()
    path = next(f["path"] for g in S.code_tree(T, sid)["files"] for f in g["files"]
                if f["path"].startswith("pages/contact/") and f["path"].endswith(".html"))
    line = S.code_read(T, sid, path)["code"].splitlines()[0]
    LE.edit(T, sid, path, line, line.replace("<section", '<section data-tone="grey"', 1))
    assert calls and calls[-1] == {"only": ["contact"], "quick": True}                   # only the touched page
    rep = json.loads(S._load(sid).checks)
    assert rep["tier"] == "quick" and rep["checked_pages"] == ["contact"]
    assert rep["pages"]["home"]["checked"] == "full" and rep["pages"]["contact"]["checked"] == "quick"   # others kept
    r = S._load(sid)
    assert any("quick check only" in b for b in H.blockers(r))                          # cannot go live yet
    assert H.update_live(T, sid) is None
    monkeypatch.setattr(H, "free_host", lambda r: "sharma.example.test")
    card = H.launch_request(T, sid)                                                      # her Go live -> the full check
    assert calls[-1] == {"only": [], "quick": False}
    assert json.loads(S._load(sid).checks)["tier"] == "full" and not any("quick check only" in b for b in card["blockers"])


def test_switch_off_and_no_base_mean_full(site_env, monkeypatch):
    calls = []
    _fake_checks(monkeypatch, calls)
    from app.site import service as S
    sid = _site(S)
    S._save(sid, checks={})                             # no full report to stand on -> a quick ask gets the full check
    S.save_version(sid, "x", quick=["home"])
    assert calls[-1] == {"only": [], "quick": False} and json.loads(S._load(sid).checks)["tier"] == "full"
    S.save_version(sid, "x", quick=["home"])            # with the base: quick
    assert calls[-1] == {"only": ["home"], "quick": True}
    monkeypatch.setenv("SITE_QUICK_CHECKS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    S.save_version(sid, "y", quick=["home"])
    assert calls[-1] == {"only": [], "quick": False}


def test_quick_merge_keeps_untouched_pages_and_journeys():
    from app.site import service as S
    prev = {"source": "hoola", "pages": {"home": {"issues": [{"kind": "h1", "text": "home h1"}], "warnings": []},
                                         "contact": {"issues": [{"kind": "link", "text": "old contact link"}], "warnings": []}},
            "blocking": [{"kind": "h1", "text": "home h1"}, {"kind": "link", "text": "old contact link"},
                         {"kind": "journey", "text": "Visitor test failed: cart"}],
            "warnings": [], "scores": {"performance": 95, "blanks": 2}, "gates": {"rows": []}}
    q = {"pages": {"contact": {"issues": [], "warnings": [], "blanks": 0}}, "blocking": [], "warnings": [], "scores": {"js_kb": 9}}
    m = S._quick_merge(prev, q, ["contact"])
    texts = [b["text"] for b in m["blocking"]]
    assert "old contact link" not in texts and "home h1" in texts and "Visitor test failed: cart" in texts
    assert m["scores"]["performance"] == 95 and m["scores"]["js_kb"] == 9 and m["tier"] == "quick" and not m["passed"]


def test_agent_tool_actions_and_plan_mode(site_env, monkeypatch):
    calls = []
    _fake_checks(monkeypatch, calls)
    from app.agent import site_tools as ST
    from app.agent import turnmode as TM
    from app.agent.tools import Ctx, ToolError
    from app.site import service as S
    sid = _site(S)
    ctx = Ctx(tenant_id=T, conversation_id=conv_ctx().conversation_id)
    found = asyncio.run(ST.website_dekho(ctx, "search", site=sid, q="Sharma Sweets"))
    assert found["total"] >= 1
    path = "pages/home/hero.html"
    line = S.code_read(T, sid, path)["code"].splitlines()[0]
    out = asyncio.run(ST.website(ctx, "edit_lines", site=sid, file=path, search=line,
                                 replace=line.replace("<section", '<section data-x="1"', 1)))
    assert out["changed"]
    with pytest.raises(ToolError, match="not in"):
        asyncio.run(ST.website(ctx, "edit_lines", site=sid, file=path, search="nope nope nope", replace="x"))
    schema = ST.SITE_TOOLS[0]["input_schema"]["properties"]
    assert {"edit_lines", "write_file"} <= set(schema["action"]["enum"]) and "search" in ST.SITE_TOOLS[1]["input_schema"][
        "properties"]["what"]["enum"]
    assert "SMALL EXACT CHANGES FIRST" in ST.SITE_TOOLS[0]["description"]
    TM.begin("[Web console mode: plan]")                                    # Plan / Chat: looking yes, changing no
    try:
        assert TM.allowed("website_dekho") and not TM.allowed("website")
    finally:
        TM.begin("")


def test_real_quick_check_is_fast(site_env, monkeypatch):
    """The measured target: a one-section change is checked in seconds (real Chromium, one page) - well under the 20 s
    the plan sets for 'make the button grey'."""
    from app.site import checks as C
    if C.available():
        pytest.skip("no Chromium here: " + C.available())
    from app.site import lineedit as LE
    from app.site import service as S
    sid = _site(S)
    S.save_version(sid, "full base")
    rep = json.loads(S._load(sid).checks)
    if rep.get("source") in (None, "", "none"):
        pytest.skip("the browser check could not run here")
    path = "pages/home/hero.html"
    line = S.code_read(T, sid, path)["code"].splitlines()[0]
    t0 = time.monotonic()
    LE.edit(T, sid, path, line, line.replace("<section", '<section data-tone="grey"', 1))
    took = time.monotonic() - t0
    rep = json.loads(S._load(sid).checks)
    assert rep["tier"] == "quick" and rep["checked_pages"] == ["home"]
    assert took < 20, took
    print(f"quick check of one page: {rep.get('quick_s')} s, whole edit {took:.1f} s")


def test_studio_says_which_check_ran(site_env, monkeypatch):
    calls = []
    _fake_checks(monkeypatch, calls)
    from pathlib import Path
    from app.site import service as S
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "webstudio.js").read_text()
    assert "S(chk.tier) === 'quick'" in js and "the full check runs before going live" in js
    sid = _site(S)
    S.save_version(sid, "base")
    S.save_version(sid, "small", quick=["home"])
    v = S.view(S._load(sid))
    assert v["checks"]["tier"] == "quick" and v["checks"]["checked_pages"] == ["home"]
