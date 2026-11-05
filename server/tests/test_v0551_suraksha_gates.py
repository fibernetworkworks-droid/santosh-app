"""v0.551 SURAKSHA GATES for websites (web Step 7 part 1 = W11): every build's pages are read (not a sample) for secrets,
outside libraries with known holes (OSV.dev), security headers, OWASP page rules, form safety + honeypot + Turnstile,
WCAG 2.2 AA (file-provable on every page + axe), profession law (DMR cure claims, Bar Council solicitation, FSSAI, NMC
registration, e-commerce seller pages, coaching claims), trackers without consent; a FAIL blocks the launch card."""
import json
import shutil
from pathlib import Path

import httpx
import pytest

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.559.0"


def _built(S):
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    r = S._load(v["id"])
    out = S._assemble_live(r)
    return v["id"], r, out


def _rows(res, gate):
    return [r for r in res["rows"] if r["gate"] == gate]


def _state(res, check_part):
    return next(r["state"] for r in res["rows"] if check_part in r["check"])


def test_a_clean_built_site_passes_every_gate(site_env):
    from app.site import gates as G
    from app.site import service as S
    sid, r, out = _built(S)
    res = G.scan(out, S._ctx(r), {"source": "hoola+axe", "blocking": []}, S.form_endpoint(r))
    fails = [x for x in res["rows"] if x["state"] == "fail"]
    assert not fails, fails
    assert res["pages"] >= 4 and res["ok"]
    assert _state(res, "No key or password") == "pass" and _state(res, "outside library") == "pass"
    assert _state(res, "Security headers") == "pass" and _state(res, "No inline script") == "pass"
    assert _state(res, "honeypot") == "pass"                                   # injected into every enquiry form
    assert _state(res, "Bot protection") in ("warn", "pass")                  # no Turnstile keys here = an honest warning
    assert _state(res, "Cookie banner") == "pass" and _state(res, "Rate limits") == "pass"
    # the version's report carries it, and a pass adds nothing to blocking
    rep = G.merge({"blocking": [], "warnings": [], "passed": True}, res)
    assert rep["passed"] and rep["gates"]["fail"] == 0 and rep["gates"]["rows"]


def _copy(out, tmp_path):
    dst = tmp_path / "s"
    shutil.copytree(out, dst)
    return dst


def _home(dst):
    return dst / "index.html"


def test_each_planted_problem_fails_for_its_own_reason(site_env, tmp_path):
    from app.site import gates as G
    from app.site import service as S
    sid, r, out = _built(S)
    ctx, ep = S._ctx(r), S.form_endpoint(r)

    def plant(fn):
        dst = tmp_path / f"p{len(list(tmp_path.iterdir()))}"
        shutil.copytree(out, dst)
        fn(dst)
        return G.scan(dst, ctx, {}, ep)

    def add(dst, html, page="index.html"):
        f = dst / page
        f.write_text(f.read_text().replace("</main>", html + "</main>"))
    res = plant(lambda d: (d / "assets" / "site.js").write_text("var k='rzp_live_ABCDEFGHIJKLMNOP';"))
    assert _state(res, "No key or password") == "fail" and "Razorpay" in res["rows"][0]["read"]
    assert not res["ok"] and any("chaabi" in b for b in res["blocks"])
    res = plant(lambda d: add(d, "<script>alert(1)</script>"))
    assert _state(res, "No inline script") == "fail"
    res = plant(lambda d: add(d, '<a href="#" onclick="x()">x</a>'))
    assert _state(res, "on*= event") == "fail"
    res = plant(lambda d: add(d, '<script src="https://evil.example/x.js"></script>'))
    assert _state(res, "No outside scripts") == "fail"
    res = plant(lambda d: add(d, '<img src="http://cdn.example/x.jpg" alt="x">'))
    assert _state(res, "No http://") == "fail"
    res = plant(lambda d: add(d, '<iframe src="https://ads.example/frame"></iframe>'))
    assert _state(res, "Frames only") == "fail"
    res = plant(lambda d: add(d, '<a href="https://x.example" target="_blank">x</a>'))
    assert _state(res, "noopener") == "warn" and res["ok"]                     # a warning never blocks
    res = plant(lambda d: add(d, '<form data-hoola-form data-endpoint="https://grabber.example/f"><input name="website">'
                                 '<label>Name <input name="name"></label><button type="submit">Send</button></form>'))
    assert _state(res, "post only to her") == "fail"
    res = plant(lambda d: add(d, '<form><label>P <input type="password" name="p"></label></form>'))
    assert _state(res, "No password box") == "fail"
    res = plant(lambda d: add(d, '<img src="assets/x.jpg">'))
    assert _state(res, "image alt text") == "fail"
    res = plant(lambda d: add(d, '<input name="q">'))
    assert any(x["state"] == "fail" and "label" in x["say"] for x in res["rows"])
    res = plant(lambda d: add(d, '<a href="/x/"></a>'))
    assert any(x["state"] == "fail" and "bina naam" in x["say"] for x in res["rows"])
    res = plant(lambda d: _home(d).write_text(_home(d).read_text().replace(
        'width=device-width,initial-scale=1', 'width=device-width,initial-scale=1,maximum-scale=1')))
    assert any(x["state"] == "fail" and "zoom" in x["say"] for x in res["rows"])
    res = plant(lambda d: add(d, '<p>Loading</p><script async src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>'))
    assert _state(res, "Cookie banner") == "fail" and _state(res, "No outside scripts") == "fail"
    res = plant(lambda d: (d / "_headers").write_text("/*\n  X-Frame-Options: DENY\n"))
    assert _state(res, "Security headers") == "fail"


def test_profession_law_and_trackers(site_env, tmp_path):
    from app.site import gates as G
    from app.site import service as S
    sid, r, out = _built(S)
    ctx, ep = S._ctx(r), S.form_endpoint(r)

    def with_text(words, legal, shop=False):
        dst = tmp_path / f"l{len(list(tmp_path.iterdir()))}"
        shutil.copytree(out, dst)
        f = dst / "index.html"
        f.write_text(f.read_text().replace("</main>", f"<p>{words}</p></main>"))
        return G.scan(dst, {**ctx, "legal": legal, "shop": {"api": "x"} if shop else None}, {}, ep)
    res = with_text("Our herbal course gives a permanent cure for diabetes.", ["dmr"])
    dmr = next(x for x in res["rows"] if "Drugs and Magic Remedies" in x["check"])
    assert dmr["state"] == "fail" and "cure for diabetes" in dmr["read"] and "permanent cure" in dmr["read"]
    assert _state(with_text("We help you manage blood sugar with diet.", ["dmr"]), "Drugs and Magic Remedies") == "pass"
    res = with_text("Best lawyer in Akola, guaranteed bail.", ["bci"])
    assert _state(res, "solicitation") == "fail"
    assert _state(with_text("Fresh mithai daily.", ["fssai"]), "FSSAI") == "warn"
    assert _state(with_text("Fresh mithai daily.", ["fssai"], shop=True), "FSSAI") == "fail"     # selling food online
    assert _state(with_text("FSSAI Lic. No. 11521999000123", ["fssai"], shop=True), "FSSAI") == "pass"
    assert _state(with_text("Dr. Rao, MBBS", ["nmc"]), "registration number") == "warn"
    assert _state(with_text("Dr. Rao, MBBS, Reg. No. 54321 (MMC)", ["nmc"]), "registration number") == "pass"
    assert _state(with_text("100% placement guaranteed for every student.", ["edu"]), "guaranteed-result") == "warn"
    # a tracker WITH a consent banner is allowed
    dst = tmp_path / "t"
    shutil.copytree(out, dst)
    f = dst / "index.html"
    f.write_text(f.read_text().replace("</main>", '<div data-hoola-consent></div><p>fbq(</p></main>'))
    assert _state(G.scan(dst, ctx, {}, ep), "Cookie banner") == "pass"


def test_outside_library_with_a_known_hole_fails_and_osv_down_is_not_a_pass(site_env, tmp_path):
    from app.appmaker import gates as AG
    from app.site import gates as G
    from app.site import service as S
    sid, r, out = _built(S)
    dst = tmp_path / "s"
    shutil.copytree(out, dst)
    (dst / "assets" / "jquery.min.js").write_text("/*! jQuery v1.12.4 | (c) jQuery Foundation */ !function(){}")
    assert G.found_libraries(dst) == [{"ecosystem": "npm", "name": "jquery", "version": "1.12.4"}]
    AG.set_osv(lambda deps: [[{"id": "GHSA-xss-1", "database_specific": {"severity": "HIGH"}}]])
    try:
        assert _state(G.scan(dst, S._ctx(r), {}, ""), "outside library") == "fail"
        AG.set_osv(lambda deps: None)
        res = G.scan(dst, S._ctx(r), {}, "")
        assert _state(res, "outside library") == "not_checked" and res["not_checked"] >= 1
    finally:
        AG.set_osv(None)


def test_a_failing_gate_blocks_the_launch_and_the_console_shows_it(site_env):
    from app.site import gates as G
    from app.site import hosting as H
    from app.site import service as S
    sid, r, out = _built(S)
    (out / "assets" / "site.js").write_text("var k='rzp_live_ABCDEFGHIJKLMNOP';")
    rep = S._gates(S._load(sid), {"source": "hoola", "blocking": [], "warnings": [], "passed": True})
    assert not rep["passed"] and any(b["kind"] == "gate" for b in rep["blocking"])
    from app.db import session
    from app.site.models import Site
    with session() as s:
        row = s.get(Site, sid)
        row.checks = json.dumps(rep)
    assert any("chaabi" in b or "key" in b.lower() for b in H.blockers(S._load(sid)))
    con = (Path(__file__).resolve().parents[1] / "app" / "static/console/build.js").read_text()
    assert "function gatesBlock" in con and "Safety gates" in con


def test_turnstile_box_csp_and_server_check(site_env, monkeypatch):
    from app.config import get_settings
    from app.site import build as B
    from app.site import service as S
    monkeypatch.setattr(get_settings(), "site_turnstile_site", "0x4AAAAsitekey")
    monkeypatch.setattr(get_settings(), "site_turnstile_secret", "0x4AAAAsecret")
    h = B.guard_forms('<form data-hoola-form data-endpoint="x"><label>Name <input name="name"></label>'
                      '<button type="submit">Send</button></form>')
    assert 'class="cf-turnstile" data-sitekey="0x4AAAAsitekey"' in h and 'name="website"' in h
    csp = B.security_headers("https://hoola.example/api/site-forms/s1")["Content-Security-Policy"]
    assert "script-src 'self' https://challenges.cloudflare.com" in csp and "frame-src" in csp
    asked = []

    def cf(req: httpx.Request) -> httpx.Response:
        asked.append(req.content.decode())
        return httpx.Response(200, json={"success": "good" in req.content.decode()})
    monkeypatch.setattr(S, "_TURNSTILE_TRANSPORT", httpx.MockTransport(cf))
    sid, r, out = _built(S)
    with pytest.raises(S.SiteError, match="Robot"):
        S._lead_post(sid, {"name": "A", "phone": "9876543210"}, ip="10.0.0.1")                  # no token
    with pytest.raises(S.SiteError, match="Robot"):
        S._lead_post(sid, {"name": "A", "phone": "9876543210", "cf-turnstile-response": "bad"}, ip="10.0.0.2")
    ok = S._lead_post(sid, {"name": "A", "phone": "9876543210", "cf-turnstile-response": "good-token"}, ip="10.0.0.3")
    assert ok["ok"] and "secret=0x4AAAAsecret" in asked[-1] and "remoteip=10.0.0.3" in asked[-1]
    # off by default: no box, no outside script in the CSP
    monkeypatch.setattr(get_settings(), "site_turnstile_secret", "")
    assert "challenges.cloudflare.com" not in B.security_headers("")["Content-Security-Policy"]
    assert "cf-turnstile" not in B.guard_forms('<form data-hoola-form><button type="submit">x</button></form>')


def test_a_page_problem_names_its_section_so_the_fix_round_can_rewrite_it(site_env, tmp_path):
    import re
    from app.site import gates as G
    from app.site import service as S
    sid, r, out = _built(S)
    dst = tmp_path / "s"
    shutil.copytree(out, dst)
    h = (dst / "index.html").read_text()
    m = re.search(r'<section\b[^>]*\bid="(s-home-[\w-]+)"[^>]*>', h)
    assert m, "sections carry their id"
    (dst / "index.html").write_text(h[:m.end()] + '<img src="assets/x.jpg">' + h[m.end():])
    res = G.scan(dst, S._ctx(r), {}, S.form_endpoint(r))
    row = next(x for x in res["rows"] if "image alt text" in x["check"])
    assert row["state"] == "fail" and row["sections"] == [m.group(1)]
    rep = G.merge({"blocking": [], "warnings": []}, res)
    item = next(b for b in rep["blocking"] if "image alt text" in b["text"])
    assert item["sections"] == [m.group(1)]
    fix = S._fixable(rep, S._ctx(r)["plan"])
    assert any(k.startswith("home__") for k in fix)                         # the fix round will rewrite that section


def test_shop_self_heal_checks_only_its_own_tables():
    """v0.551 the checkout's self-heal inspected every table in the database (~900) on each worker's first checkouts,
    and every thread repeated it until one finished - CI's load proof timed out 114 checkouts. Own tables only, once."""
    import inspect as _i
    from app.site import shop, shoppay, shopplus, webapp
    from app.appmaker import backup
    for mod in (shop, shoppay, shopplus, webapp, backup):
        src = _i.getsource(mod)
        assert "_add_missing_columns(" not in src, mod.__name__
        assert "add_missing_columns_for(" in src, mod.__name__
    for mod, lock in ((shop, "_TABLES_LOCK"), (shoppay, "_LOCK"), (shopplus, "_LOCK"), (webapp, "_TABLES_LOCK")):
        assert hasattr(getattr(mod, lock), "acquire"), mod.__name__
