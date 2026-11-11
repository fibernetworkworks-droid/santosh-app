"""v0.807 HOOLA CODE DESIGN PASS (owner: "DESIGN STILL LOOK OLD AND STALE --- MAKE IT PERFECTLY ALLINED ... PREMIUM ...
LIKE CLAUDE CODE WEB PORTAL ... SHOW ME ALL PAGES").

One design system for the whole page (the block "HOOLA CODE (code.js) - THE DESIGN SYSTEM" in v2.css). This test walks
EVERY page in a real browser with full, realistic data and MEASURES what "aligned" means, so it cannot drift again:
- one control height: every button / chip / field on the page is 34px (small ones 28px, the two composer buttons 36px);
- things that sit in one row share one centre line;
- the marks of the steps sit on one vertical line, and so do the page title and the cards under it;
- nothing is smaller than 12px, nothing heavier than 600, no all-caps;
- nothing pushes a page sideways, at a wide window, a narrow one, in light and in dark;
- motion happens once and is off under "reduce motion".
With HOOLA_SHOTS set it saves a picture of every page (that is what she is shown)."""
from __future__ import annotations

import os

from datetime import datetime, timedelta, timezone

T0 = datetime.now(timezone.utc) - timedelta(minutes=24)
AT = T0.isoformat()


def _base(**kw):
    t = {"id": "dt1", "number": "D-0101", "kind": "fix", "repo": "meghana/shop-api", "status": "pr_open", "title": "Empty cart crashes the total",
         "running": False, "stopping": False, "archived": False, "at": AT, "updated": AT, "ci": {}, "checks": [], "proof": {}, "self_review": {},
         "plan": {}, "pr_number": 0, "pr_url": "", "branch": "", "tier": "", "auto_fix": True, "question": "", "base": "main", "mode": "auto",
         "model": "", "effort": "high", "attach": [], "cost": {}, "text": "", "notes": [], "log": [], "found": {}, "hash": "", "explain": "", "risk": "",
         "error": "", "rounds": 0, "steps": [], "files": [], "file_diffs": [], "diff": "", "can_continue": False, "ws": {"exists": False}, "hint": "",
         "share": {"on": False, "path": "", "until": ""}, "sched_id": "", "pr_comments": [], "refs": [], "group": []}
    t.update(kw)
    return t


def _s(k, sec, **kw):
    return {"k": k, "at": (T0 + timedelta(seconds=sec)).isoformat(), **kw}


DIFF = ("@@ -1,9 +1,10 @@\n def total(items):\n     \"\"\"The cart total in paise.\"\"\"\n     s = 0\n     for it in items:\n         s += it[\"price\"] * it[\"qty\"]\n"
        "-    return s / len(items)\n+    if not items:\n+        return 0\n+    return s\n \n \n def tax(amount, rate=0.18):\n")
TEST_DIFF = "@@ -4,3 +4,7 @@\n     assert total([{\"price\": 10, \"qty\": 2}]) == 20\n+\n+\n+def test_empty_cart_is_zero():\n+    assert total([]) == 0\n"


def tasks():
    done = _base(
        text="The cart total crashes when the cart is empty. Here is the error:\nZeroDivisionError: division by zero (app/calc.py, line 6)",
        pr_number=12, pr_url="https://github.com/meghana/shop-api/pull/12", branch="hoola/d-0101-empty-cart", ci={"state": "success"},
        self_review={"verdict": "ok"}, proof={"state": "proven_local"}, rounds=1, cost={"calls": 14, "inr": 18.4}, hint="Add a test for a cart with one item",
        explain="total() divided the sum by the number of items, so an empty cart divided by zero. It now returns 0 for an empty cart and the plain sum otherwise. "
                "I added a test that fails on the old code and passes on the new one.",
        risk="A caller that relied on the old average would now get the sum - I found none in the repo.",
        files=[{"path": "app/calc.py", "added": 3, "removed": 1}, {"path": "tests/test_calc.py", "added": 4, "removed": 0}],
        file_diffs=[{"path": "app/calc.py", "added": 3, "removed": 1, "diff": DIFF, "why": "an empty cart returns 0"},
                    {"path": "tests/test_calc.py", "added": 4, "removed": 0, "diff": TEST_DIFF, "why": "the test that proves it"}],
        pr_comments=[{"id": "l1", "who": "ravi", "path": "app/calc.py", "line": 7, "text": "Should None be treated like an empty cart too?"}],
        ws={"exists": True, "live": False, "hidden": [".env"], "changed": [], "mb": 3, "slots": {"limit": 2, "running": 0}, "choices": [],
            "todos": [{"content": "Find where the total is computed", "status": "completed"}, {"content": "Write the failing test", "status": "completed"},
                      {"content": "Fix total() and run the tests", "status": "completed"}],
            "checkpoints": [{"n": 1, "label": "The cart total crashes"}, {"n": 2, "label": "Handle None items too"}]},
        steps=[_s("pass", 2, name="plan", state="start", note="reads only"), _s("pass", 18, name="plan", state="end", note="3 steps planned", ok=True),
               _s("think", 20, text="The traceback points at app/calc.py line 6. If items is empty, len(items) is 0. Why is it dividing at all? The docstring says total, not average."),
               _s("rules", 22, paths=["AGENTS.md"]), _s("read", 25, path="app/calc.py"), _s("search", 31, q="total(", n=4), _s("read", 36, path="tests/test_calc.py"),
               _s("say", 40, text="The total is divided by the number of items, which is the bug - a total is a sum. I will write the failing test first."),
               _s("edit", 52, path="tests/test_calc.py", added=4, removed=0, diff=["+def test_empty_cart_is_zero():", "+    assert total([]) == 0"]),
               _s("bash", 66, cmd="python3 -m pytest -q tests/test_calc.py", rc=1, seconds=2.1, tail=["E   ZeroDivisionError: division by zero", "1 failed, 1 passed in 0.31s"]),
               _s("edit", 80, path="app/calc.py", added=3, removed=1, diff=["-    return s / len(items)", "+    if not items:", "+        return 0", "+    return s"]),
               _s("bash", 94, cmd="python3 -m pytest -q", rc=0, seconds=3.4, tail=["14 passed in 1.92s"]),
               _s("ckpt", 96, n=1), _s("pass", 100, name="review", state="start", note="Hoola reads its own pull request"),
               _s("pass", 128, name="review", state="end", note="clean", ok=True)])
    run = _base(id="dt2", number="D-0102", title="Add coupons to checkout", kind="write", status="new", running=True, mode="ask",
                text="Add percentage coupons to checkout. A coupon has a code, a percent and a last date.", notes=["Also add a test for an expired coupon"],
                ws={"exists": True, "live": True, "hidden": [], "changed": [], "mb": 3, "slots": {"limit": 2, "running": 1}, "choices": [], "checkpoints": [],
                    "todos": [{"content": "Read how the cart computes prices", "status": "completed"}, {"content": "Add the Coupon model", "status": "in_progress"},
                              {"content": "Apply it in checkout + tests", "status": "pending"}]},
                steps=[_s("read", 5, path="app/cart.py"), _s("read", 9, path="app/models.py"), _s("search", 14, q="discount", n=2),
                       _s("todo", 18, items=[{"content": "Read how the cart computes prices", "status": "completed"}, {"content": "Add the Coupon model", "status": "in_progress"},
                                             {"content": "Apply it in checkout + tests", "status": "pending"}]),
                       _s("new", 30, path="app/coupons.py", added=28, removed=0, diff=["+class Coupon:", "+    code: str", "+    percent: int"])])
    plan = _base(id="dt3", number="D-0103", title="Move orders to their own module", kind="write", status="plan_wait", tier="large", hash="h1", mode="plan",
                 text="Move everything about orders out of app/shop.py into app/orders/ without changing behaviour.",
                 plan={"goal": "app/orders/ owns orders; app/shop.py only imports from it.", "files": [{"path": "app/orders/__init__.py", "why": "new package"},
                       {"path": "app/shop.py", "why": "imports move"}], "steps": ["Create app/orders/ with models and service", "Move the functions, keep the old names as imports",
                       "Run the whole test suite"], "done_when": ["pytest passes", "app/shop.py has no order logic left"], "risk": "Circular imports between shop and orders."})
    ask = _base(id="dt4", number="D-0104", title="Round prices", status="explained", question="Should prices round half up (2.5 -> 3) or to the nearest even number (2.5 -> 2)?",
                explain="Should prices round half up (2.5 -> 3) or to the nearest even number (2.5 -> 2)?", text="Make the prices round properly", can_continue=True,
                ws={"exists": True, "live": False, "hidden": [], "changed": [], "mb": 2, "slots": {"limit": 2, "running": 0}, "todos": [], "checkpoints": [],
                    "choices": ["Half up", "Nearest even"]})
    merged = _base(id="dt5", number="D-0099", title="Faster product search", status="merged", pr_number=11, files=[{"path": "app/search.py", "added": 40, "removed": 12}])
    failed = _base(id="dt6", number="D-0098", title="Upgrade the payment library", status="failed", error="GitHub refused the push: the token may not write to this repo.",
                   repo="meghana/shop-web", text="Upgrade the payment library to v4")
    return [run, plan, ask, done, merged, failed]


def overview(ts):
    repos = [{"repo": "meghana/shop-api", "private": True, "default_branch": "main", "language": "Python", "setup_cmd": "pip install -r requirements.txt",
              "test_cmd": "python3 -m pytest -q", "env_vars": {"APP_ENV": "test"}, "net": {"level": "limited", "hosts": ["api.pay.example.com"],
              "secrets": [{"host": "api.pay.example.com", "header": "Authorization", "prefix": "Bearer", "at": AT}]}, "events": {"on": True, "by_hoola": True, "last": {"event": "issues", "at": AT}}},
             {"repo": "meghana/shop-web", "private": False, "default_branch": "main", "language": "TypeScript", "setup_cmd": "", "test_cmd": "", "env_vars": {},
              "net": {"level": "none", "hosts": [], "secrets": []}, "events": {"on": False, "by_hoola": False, "last": {}}}]
    sched = [{"id": "ds1", "title": "Update the dependencies", "repo": "meghana/shop-api", "base": "", "kind": "auto", "mode": "ask", "days": "weekdays", "at": "09:00",
              "text": "Update the dependencies that have a security fix, run the tests, and say what changed.", "enabled": True, "when": "Monday to Friday at 09:00",
              "next_run": (T0 + timedelta(hours=19)).isoformat(), "last_run": AT, "last_task": "dt5", "last_note": "", "trigger": True, "event": "", "filter": {},
              "runs": [{"id": "dt5", "number": "D-0099", "title": "Scheduled: Update the dependencies", "status": "merged", "pr_number": 11, "at": AT},
                       {"id": "dt1", "number": "D-0101", "title": "Scheduled: Update the dependencies", "status": "pr_open", "pr_number": 12, "at": AT}]},
             {"id": "ds2", "title": "Fix issues labelled hoola", "repo": "meghana/shop-api", "base": "", "kind": "auto", "mode": "ask", "days": "off", "at": "09:00",
              "text": "Fix what the issue describes, with a test.", "enabled": True, "when": "When an issue gets the label 'hoola'", "next_run": "", "last_run": "",
              "last_task": "", "last_note": "", "trigger": False, "event": "issue_labeled", "filter": {"label": "hoola", "who": "me"}, "runs": []}]
    reviews = [{"id": "rv1", "status": "draft", "repo": "meghana/shop-api", "pr_number": 9, "pr_title": "Add coupons", "author": "ravi", "at": AT, "url": "https://github.com/x/y/pull/9",
                "hash": "h", "suggest": "REQUEST_CHANGES", "summary": "The coupon is applied before tax, but the old code applied discounts after tax. One test is missing.",
                "findings": [{"severity": "high", "path": "app/checkout.py", "line": 41, "body": "The discount is applied before tax; invoices will not match."}],
                "comments": [{"severity": "medium", "path": "tests/test_checkout.py", "line": 12, "body": "No test for an expired coupon."}]}]
    return {"settings": {"github": True, "login": "meghana", "token_label": "fine-grained", "default_repo": "meghana/shop-api", "ask_before_pr": True, "draft_pr": True,
                         "allow_workflows": False, "archive_after_merge": True, "merge_method": "squash", "review_post": "draft", "max_files": 20, "max_lines": 1500,
                         "rules": "Type hints on every new function.", "permissions": ["Contents: write", "Pull requests: write", "Actions: read"],
                         "never": ["never pushes to your default branch", "never merges by itself", "never touches secrets"]},
            "repos": repos, "tasks": ts, "reviews": reviews, "actions": [], "kinds": {}, "schedules": sched, "net": {"on": True, "registries": ["pypi.org"]},
            "models": {"options": [{"id": "claude-opus-5-5", "label": "Opus 5.5"}, {"id": "claude-sonnet-5-5", "label": "Sonnet 5.5"}], "default": "claude-opus-5-5",
                       "forced": None, "efforts": ["low", "medium", "high"], "default_effort": "high"},
            "usage": {"spent_inr": 412, "limit_inr": 2000, "pct": 20.6, "over": False}}


JS_MEASURE = """() => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && !e.closest('[hidden]'); };
  const all = s => [...document.querySelectorAll(s)].filter(vis);
  const h = e => Math.round(e.getBoundingClientRect().height * 10) / 10;
  const out = {bad: []};
  all('.hcd-btn').forEach(b => { const want = b.classList.contains('sm') ? (b.closest('.hcd-row') ? 24 : 28) : 34; if (Math.abs(h(b) - want) > 0.6) out.bad.push(`button "${b.textContent.trim().slice(0, 24)}" is ${h(b)}px, not ${want}`); });
  all('.hcd-chip').forEach(c => { if (Math.abs(h(c) - 34) > 0.6) out.bad.push(`chip "${c.textContent.trim().slice(0, 20)}" is ${h(c)}px`); });
  all('.hcd-f input:not([type=checkbox]), .hcd-f select, .hcd-inline > input, .hcd-search, .hcd-dlg input, .hcd-dlg select').forEach(i => { if (Math.abs(h(i) - 34) > 0.6) out.bad.push(`field ${i.name || i.id || i.placeholder} is ${h(i)}px`); });
  all('.hcd-send, .hcd-plus, .hcd-stop').forEach(b => { if (Math.abs(h(b) - 36) > 0.6) out.bad.push(`composer button is ${h(b)}px`); });
  // one row = one centre line
  all('.hcd-acts, .hcd-inline, .hcd-askrow, .hcd-dlgb, .hcd-top, .hcd-ph').forEach(row => { const kids = [...row.children].filter(vis).filter(k => !k.classList.contains('hcd-flex')); const lines = {};
    kids.forEach(k => { const r = k.getBoundingClientRect(); const key = Math.round(r.top / 20); (lines[key] = lines[key] || []).push(r.top + r.height / 2); });
    Object.values(lines).forEach(cs => { if (Math.max(...cs) - Math.min(...cs) > 1.5) out.bad.push(`a row in .${row.className.split(' ')[0]} is off its centre line by ${(Math.max(...cs) - Math.min(...cs)).toFixed(1)}px`); }); });
  // the marks of the steps: one vertical line (top-level steps of the reading column)
  const xs = [...document.querySelectorAll('#hcdCol > .hcd-step > .hcd-ic, #hcdCol > .hcd-fold > .hcd-ic, #hcdCol > .hcd-fin > .hcd-step > .hcd-ic, #hcdCol > .hcd-fin > .hcd-fold > .hcd-ic')].filter(vis)
    .map(e => [e.parentElement.parentElement.id === 'hcdCol' ? 'a' : 'b', Math.round(e.getBoundingClientRect().left)]);
  ['a', 'b'].forEach(g => { const v = [...new Set(xs.filter(x => x[0] === g).map(x => x[1]))]; if (v.length > 1) out.bad.push(`step marks are on ${v.length} different lines: ${v.join(', ')}`); });
  // the title of a page and the cards under it start on one line
  const page = document.querySelector('.hcd-page'); if (page) { const ls = [...page.children].filter(vis).map(c => Math.round(c.getBoundingClientRect().left)); if (new Set(ls).size > 1) out.bad.push('page blocks start at ' + [...new Set(ls)].join(', ')); }
  // type: nothing under 12px, nothing over 600, no all-caps
  [...document.querySelectorAll('.hcd *')].filter(vis).forEach(e => { if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return; const s = getComputedStyle(e);
    if (parseFloat(s.fontSize) < 11.5) out.bad.push(`"${e.textContent.trim().slice(0, 20)}" is ${s.fontSize}`);
    if (+s.fontWeight > 600) out.bad.push(`"${e.textContent.trim().slice(0, 20)}" is weight ${s.fontWeight}`);
    if (s.textTransform === 'uppercase') out.bad.push(`"${e.textContent.trim().slice(0, 20)}" is all-caps`); });
  // nothing pushes the page sideways, no button leaves its card
  const d = document.documentElement; if (d.scrollWidth > d.clientWidth + 1) out.bad.push(`the page is ${d.scrollWidth - d.clientWidth}px wider than the window`);
  all('.hcd-rc, .hcd-card, .hcd-recap, .hcd-dlg, .hcd-ask2').forEach(card => { const cr = card.getBoundingClientRect(); [...card.querySelectorAll('.hcd-btn, .hcd-chip, input, select')].filter(vis).forEach(b => { const r = b.getBoundingClientRect();
    if (r.right > cr.right + 1 || r.left < cr.left - 1) out.bad.push(`"${(b.textContent || b.name || '').trim().slice(0, 20)}" leaves its card`); }); });
  return out;
}"""


def test_every_page_is_on_one_scale_and_lines_up(arena_server):  # noqa: F811
    base, browser, key = arena_server
    from app.config import get_settings
    get_settings().hoola_code_page = True
    shots = os.environ.get("HOOLA_SHOTS")
    ts = tasks()
    ov = overview(ts)
    seen = []

    def page(w=1440, h=900, dark=False, reduce=False):
        ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme="dark" if dark else "light",
                                  reduced_motion="reduce" if reduce else "no-preference", device_scale_factor=2 if shots else 1)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}');" + ("localStorage.setItem('hoola.theme','dark');" if dark else ""))
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/api/devsahayak", lambda r: r.fulfill(json=ov))
        pg.route("**/api/devsahayak/tasks?**", lambda r: r.fulfill(json={"tasks": ts}))
        pg.route("**/api/devsahayak/branches**", lambda r: r.fulfill(json={"branches": ["main", "release", "staging"]}))
        for t in ts:
            pg.route(f"**/api/devsahayak/tasks/{t['id']}", (lambda tt: lambda r: r.fulfill(json=tt))(t))
        pg.route("**/api/devsahayak/tasks/dt1/share", lambda r: r.fulfill(json={"on": True, "path": "/console/code/shared/" + "t" * 43, "until": "2026-11-18T10:00:00+00:00"}))
        return ctx, pg, errs

    def check(pg, name, errs):
        pg.wait_for_timeout(450)                      # the page-in motion is over; what is measured is the resting page
        got = pg.evaluate(JS_MEASURE)
        seen.append(name)
        if shots:
            pg.screenshot(path=os.path.join(shots, f"d-{len(seen):02d}-{name}.png"))
        assert got["bad"] == [], (name, got["bad"][:8])
        assert errs == [], (name, errs)

    ctx, pg, errs = page()
    # 1 home
    pg.goto(base + "/console/code")
    pg.wait_for_selector("#hcdLine")
    assert pg.locator("#hcdStarts .hcd-start").count() == 4
    check(pg, "home", errs)
    pg.locator('[data-act="starter"]').first.click()
    assert pg.locator("#hcdLine").input_value() == "Fix this bug: " and pg.evaluate("document.activeElement.id") == "hcdLine"
    # 2 a finished session
    pg.goto(base + "/console/code#/s/dt1")
    pg.wait_for_selector("#hcdRail .hcd-rc")
    check(pg, "session-done", errs)
    pg.locator('[data-fold="work"]').click()
    pg.locator('[data-menu="title"]').click()
    pg.get_by_role("menuitemradio", name="Thinking").first.click()
    pg.wait_for_selector(".hcd-think")
    check(pg, "session-steps-thinking", errs)
    # 3 the Changes pane with a comment being written
    pg.locator('#hcdTop [data-act="changes"]').click()
    pg.wait_for_selector("#hcdDv .hcd-dl.add")
    pg.locator("#hcdDv .hcd-dl.add").first.hover()
    pg.locator("#hcdDv .hcd-dl.add .hcd-cadd").first.click()
    pg.locator("#hcdCText").fill("Treat None like an empty cart too")
    check(pg, "changes-pane", errs)
    pg.keyboard.press("Enter")
    pg.locator('[data-act="pclose"]').click()
    # 4 working
    pg.goto(base + "/console/code#/s/dt2")
    pg.wait_for_selector(".hcd-work")
    check(pg, "session-working", errs)
    # 5 a plan that waits
    pg.goto(base + "/console/code#/s/dt3")
    pg.wait_for_selector("#hcdYes")
    check(pg, "session-plan", errs)
    # 6 Hoola asks
    pg.goto(base + "/console/code#/s/dt4")
    pg.wait_for_selector("#hcdChoices")
    check(pg, "session-question", errs)
    # 7 a dialog
    pg.goto(base + "/console/code#/s/dt1")
    pg.wait_for_selector("#hcdRail .hcd-rc")
    pg.locator('[data-menu="title"]').click()
    pg.get_by_role("menuitem", name="Share a read-only link").click()
    pg.wait_for_selector("#hcdDlg[open]")
    check(pg, "dialog", errs)
    pg.locator("#hcdDlg").get_by_role("button", name="Cancel").click()
    # 8-11 the pages
    for name, hash_, sel in (("scheduled", "#/scheduled", "#hcdSchedF"), ("reviews", "#/reviews", "#hcdRevNew"), ("settings", "#/settings", "#hcdTok"), ("all-sessions", "#/all", "#hcdAllF")):
        pg.goto(base + "/console/code" + hash_)
        pg.wait_for_selector(sel)
        if name == "all-sessions":
            pg.wait_for_selector(".hcd-arow")
        check(pg, name, errs)
    ctx.close()
    # dark, the same scale
    ctx, pg, errs = page(dark=True)
    pg.goto(base + "/console/code")
    pg.wait_for_selector("#hcdLine")
    check(pg, "dark-home", errs)
    pg.goto(base + "/console/code#/s/dt1")
    pg.wait_for_selector("#hcdRail .hcd-rc")
    check(pg, "dark-session", errs)
    pg.goto(base + "/console/code#/settings")
    pg.wait_for_selector("#hcdTok")
    check(pg, "dark-settings", errs)
    ctx.close()
    # a narrow window (a phone held upright)
    ctx, pg, errs = page(390, 844)
    pg.goto(base + "/console/code")
    pg.wait_for_selector("#hcdLine")
    check(pg, "narrow-home", errs)
    pg.goto(base + "/console/code#/s/dt1")
    pg.wait_for_selector("#hcdCol .hcd-me")
    check(pg, "narrow-session", errs)
    ctx.close()
    # motion: a page comes in once; with "reduce motion" nothing moves at all
    ctx, pg, errs = page()
    pg.goto(base + "/console/code")
    pg.wait_for_selector("#hcdLine")
    pg.wait_for_timeout(500)
    assert pg.evaluate("() => { document.querySelector('[data-go=scheduled]').click(); return document.querySelector('#hcdBody').classList.contains('hcd-enter'); }") is True
    pg.wait_for_selector("#hcdSchedF")
    pg.wait_for_timeout(500)
    assert pg.evaluate("document.querySelector('#hcdBody').classList.contains('hcd-enter')") is False     # a later repaint will not move
    ctx.close()
    ctx, pg, errs = page(reduce=True)
    pg.goto(base + "/console/code#/s/dt2")
    pg.wait_for_selector(".hcd-pulse")
    assert pg.evaluate("getComputedStyle(document.querySelector('.hcd-pulse')).animationName") == "none"
    assert pg.evaluate("getComputedStyle(document.querySelector('.hcd-btn')).transitionDuration") in ("0s", "")
    ctx.close()


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v121_site import site_env  # noqa: E402,F401
