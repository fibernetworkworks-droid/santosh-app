"""v0.999 THE FEED LIKE CLAUDE CODE (owner, with four screenshots of Claude Code: 'GO DEEP HOW CLAUDE CODE PERFECT REPLY
FOR REQUESTED PROMPT WITH PERFECT FEED IN CLAUDE CODE --- IS THIS SAME IN HOOLA').

Measured side by side in a real browser first. Different, now the same: a fold names what was done ('Ran 5 commands,
read 2 files', in the order the kinds came) instead of 'Worked for 25920m' (its time was measured from the step before it,
so a gap of days showed as the work); the screenshots it took sit small at the end of that line; under the answer a
'Created / Edited / Changed N files' card with each file's lines, See all and Undo; Hoola Code's words in the plain sans
Claude Code uses (the phone already did); the run's time = the time it worked, not the days the session stayed open; the
model's closing answer shaped like Claude Code's (result + what was not verified, bold-labelled points, Tests:, how to
try it) and its narration plain."""
from __future__ import annotations

import base64
import os
import re
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401
from tests.test_v0768_hoola_code_shell import TASKS, _console

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "server/app/static/console/code.js"


def test_the_fold_names_what_was_done_and_never_measures_a_gap():
    js = JS.read_text()
    assert "function workLabel(list)" in js and "'ran ' + plural" not in js
    assert "Worked${isFinite(secs)" not in js                      # the old label with its gap-measured time is gone
    assert "compacted the session" in js and "checked ${n === 1 ? 'the page'" in js
    assert "function shotThumbs(list)" in js and "/shots/${encodeURIComponent(n)}" in js and "{raw: true}" in js
    assert "function filesCard(t)" in js and "'Created' : !made ? 'Edited' : 'Changed'" in js and ">See all<" in js
    assert "data-act=\"rewind\" data-n=\"${back}\"" in js
    css = (ROOT / "server/app/static/console/hoolacode.css").read_text()
    assert "#app .hcd .hck,#app .hcd{--hck-fr:var(--hck-fb)}" in css and ".hcd-thumbs img" in css and ".hcd-files" in css


def test_the_phone_has_the_same_card_and_order():
    d = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "Widget _filesCard(HoolaColors c, Map<String, dynamic> t)" in d and "Future<void> _rewindTo(int n)" in d
    assert "..sort((x, y) => first(x.$1).compareTo(first(y.$1)))" in d and "'compacted the session'" in d
    assert "withValues" not in d and "Color(0x" not in d[d.index("Widget _filesCard"):d.index("Widget _filesCard") + 3000]


def test_the_closing_answer_and_narration_rules():
    from app.devsahayak import engine as E
    s = " ".join(E.SYSTEM.split())
    assert "the way Claude Code ends a job" in s and '"**Tests:**"' in s and "what was NOT verified" in s
    assert "bold label and a colon" in s and "do not list them again" in s
    assert "Bold only a real finding" in s and "most lines need none" in s
    assert "lead with the result" in s and "say that FIRST" in s       # the older promises still stand


STEPS = []


def _add(**k):
    STEPS.append({**k, "at": "2026-11-28T10:%02d:%02d+00:00" % (len(STEPS) // 60, len(STEPS) % 60)})


_add(k="bash", cmd="python3 tools/check.py", did="Ran python3 tools/check.py", rc=0, tail=["ok"])
_add(k="say", text="Now the tests:")
_add(k="bash", cmd="pytest -q", desc="Run the new tests", rc=1, tail=["1 failed"])
_add(k="bash", cmd="pytest -q", desc="Run them again", rc=0, tail=["4 passed"])
_add(k="compact", text="Compacted the session")
_add(k="say", text="Now the screenshots.")
for _i in range(5):
    _add(k="bash", cmd=f"python3 shot.py {_i}", desc=f"Take screenshot {_i}", rc=0, tail=["saved"])
_add(k="read", path="app/memory.py")
_add(k="look", path="/console/embedded", shots=["a.png", "b.png", "c.png", "d.png"], errors=0)
_add(k="say", text="Pages look right.")
_add(k="new", path="app/memory.py", added=358)
_add(k="edit", path="app/main.py", added=4, removed=1)
_add(k="round", secs=95)
_add(k="say", text="The desk is built. **What it does.**\n\n- **Memory:** reads the map file.\n\n**Tests:** 4 passed.\n\nTo try it, deploy.")
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


@pytest.mark.skipif(not os.environ.get("HOOLA_CHROMIUM") and not Path("/opt/pw-browsers/chromium-1243/chrome-linux64/chrome").exists(),
                    reason="no Chromium here")
def test_the_feed_in_a_real_browser(arena_server):  # noqa: F811
    ctx, pg, errs, calls, state = _console(arena_server)
    task = {**TASKS[0], "status": "pr_open", "running": False, "text": "A desk", "steps": STEPS, "notes": [], "log": [], "diff": "",
            "found": {}, "last_n": len(STEPS), "pr_number": 12, "ci": {"state": "success"},
            "files": [{"path": "app/memory.py", "added": 358, "removed": 0}, {"path": "app/main.py", "added": 4, "removed": 1}],
            "file_diffs": [{"path": "app/memory.py", "added": 358, "removed": 0, "new": True}, {"path": "app/main.py", "added": 4, "removed": 1}],
            "ws": {"checkpoints": [{"n": 1, "label": "first"}, {"n": 2, "label": "second"}]}}
    shots = []
    pg.route("**/api/devsahayak/tasks/dt1", lambda r: r.fulfill(json=task))
    pg.route("**/api/devsahayak/tasks/dt1/stream", lambda r: r.fulfill(status=200, headers={"Content-Type": "text/event-stream"}, body=""))
    pg.route("**/api/devsahayak/tasks/dt1/shots/*", lambda r: shots.append(r.request.url) or r.fulfill(status=200, headers={"Content-Type": "image/png"}, body=PNG))
    pg.locator("[data-tid='dt1']").click()
    pg.wait_for_function("() => (document.querySelector('#hcdCol')||{}).textContent && document.querySelector('#hcdCol').textContent.includes('To try it')", timeout=20000)
    folds = [x.strip() for x in pg.locator("#hcdCol .hcd-wgrp .hck-fold > summary .sm").all_text_contents()]
    assert folds == ["Ran python3 tools/check.py", "Ran 2 commands, compacted the session",
                     "Ran 5 commands, read memory.py, checked the page in a browser", "Created memory.py, edited main.py"]
    assert not any("Worked for" in f for f in folds)
    pg.wait_for_function("() => document.querySelectorAll('#hcdCol .hcd-thumbs img[src^=\"blob:\"]').length === 3", timeout=8000)
    assert pg.locator("#hcdCol .hcd-thumbs em").text_content() == "+1" and len(shots) == 3
    card = pg.locator("#hcdCol .hcd-files")
    assert card.locator(".hcd-fh b").text_content() == "Changed 2 files"
    assert card.locator("li").count() == 2 and "+362" in card.locator(".hcd-fall").text_content()
    assert card.locator("[data-act='rewind']").get_attribute("data-n") == "1"         # back to before the newest round
    family = pg.evaluate("() => getComputedStyle(document.querySelector('#hcdCol .hck-txt')).fontFamily")
    assert "Literata" not in family                                                    # the plain sans, like Claude Code
    assert "1 min 35 s" in pg.locator(".hcd-runrc h2").text_content()                  # the time it worked, from its rounds
    card.locator(".hcd-fall").click()                                                  # See all opens the changes
    pg.wait_for_timeout(500)
    assert not errs, errs
    ctx.close()


def test_version():
    from app.main import APP_VERSION
    assert re.match(r"^\d+\.\d+\.\d+", APP_VERSION)
