"""v0.999 REWIND LIKE CLAUDE CODE (owner: 'Rewind just the code or just the conversation --- WORK ON IT'): going back to a
checkpoint asks WHAT goes back - code and conversation, the conversation only (the files keep every change), or the code
only (the conversation stays). A partial rewind keeps the later checkpoints, so she can go forward again, and the next
round is told what changed under it."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ses(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    s = EN.Session("t1")
    s.repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=s.repo, check=True)
    msgs = []
    for i in (1, 2, 3):
        (s.repo / "a.txt").write_text(f"version {i}\n")
        if i == 3:
            (s.repo / "new.txt").write_text("added late\n")
        msgs += [{"role": "user", "content": f"ask {i}"}, {"role": "assistant", "content": f"did {i}"}]
        s.save_messages(list(msgs))
        s.checkpoint(f"round {i}", len(msgs))
    return s


def test_code_only_puts_the_files_back_and_keeps_the_conversation(ses):
    from app.devsahayak import engine as EN
    EN.rewind("t1", 1, "code")
    s = EN.Session("t1")
    assert (s.repo / "a.txt").read_text() == "version 1\n" and not (s.repo / "new.txt").exists()
    assert len(s.messages()) == 6 and len(s.meta["checkpoints"]) == 3          # conversation + later checkpoints kept
    assert "FILES back to checkpoint 1" in s.meta["pending_note"]
    EN.rewind("t1", 3, "code")                                                 # and forward again
    assert (EN.Session("t1").repo / "a.txt").read_text() == "version 3\n"


def test_conversation_only_keeps_every_file_change(ses):
    from app.devsahayak import engine as EN
    EN.rewind("t1", 1, "conversation")
    s = EN.Session("t1")
    assert [m["content"] for m in s.messages()] == ["ask 1", "did 1"]
    assert (s.repo / "a.txt").read_text() == "version 3\n" and (s.repo / "new.txt").exists()
    assert len(s.meta["checkpoints"]) == 3 and "CONVERSATION back to checkpoint 1" in s.meta["pending_note"]


def test_both_is_the_old_rewind(ses):
    from app.devsahayak import engine as EN
    EN.rewind("t1", 2)
    s = EN.Session("t1")
    assert (s.repo / "a.txt").read_text() == "version 2\n" and len(s.messages()) == 4
    assert len(s.meta["checkpoints"]) == 2 and "pending_note" not in s.meta


def test_the_next_round_is_told_once(ses):
    from app.devsahayak import engine as EN
    EN.rewind("t1", 1, "code")
    s = EN.Session("t1")
    tl = EN.Tools(s, False)
    tl.conf = {"hooks": {}}
    got = EN.her_blocks(tl, s, "carry on", lambda ev: None)
    assert "<rewind_note>" in got and "FILES back to checkpoint 1" in got
    assert "<rewind_note>" not in EN.her_blocks(tl, EN.Session("t1"), "carry on", lambda ev: None)


def test_the_route_takes_what_and_the_screens_offer_it():
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert 'str(b.get("what") or "both")' in api and 'Choose what goes back' in svc and '"what": what' in svc
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "Conversation only" in js and "Code only" in js and "Never mind" in js and "{n, what: r}" in js
    d = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "'Conversation only'" in d and "'Code only'" in d and "'what': what" in d and "Put the files back" in d


import json  # noqa: E402
import os  # noqa: E402

from tests.test_v0312_arena_screen import arena_server  # noqa: F401,E402
from tests.test_v121_site import site_env  # noqa: F401,E402


@pytest.mark.skipif(not os.environ.get("HOOLA_CHROMIUM") and not Path("/opt/pw-browsers/chromium-1243/chrome-linux64/chrome").exists(),
                    reason="no Chromium here")
def test_the_page_asks_what_goes_back(arena_server):  # noqa: F811
    from tests.test_v0768_hoola_code_shell import TASKS, _console, _shot
    ctx, pg, errs, calls, state = _console(arena_server)
    cps = [{"n": 1, "label": "round 1"}, {"n": 2, "label": "round 2"}, {"n": 3, "label": "round 3"}]
    task = {**TASKS[0], "running": False, "steps": [{"k": "rewind", "n": 1, "what": "code", "at": "2026-11-10T10:00:02+00:00"}],
            "notes": [], "log": [], "diff": "", "found": {}, "last_n": 0, "ws": {"exists": True, "checkpoints": cps}}
    sent = []
    pg.route("**/api/devsahayak/tasks/dt1", lambda r: r.fulfill(json=task))
    pg.route("**/api/devsahayak/tasks/dt1/stream", lambda r: r.fulfill(status=200, headers={"Content-Type": "text/event-stream"}, body=""))
    pg.route("**/api/devsahayak/tasks/dt1/rewind", lambda r: sent.append(r.request.post_data_json) or r.fulfill(json=task))
    pg.locator("[data-tid='dt1']").click()
    pg.wait_for_selector("[data-act='rewind']")
    assert "Put the files back to checkpoint 1." in pg.locator("#hcdCol").text_content()
    pg.locator("[data-act='rewind'][data-n='1']").click()
    pg.wait_for_selector("#hcdDlg[open] .hcd-rwopt")
    d = pg.locator("#hcdDlg").text_content()
    assert "Code and conversation" in d and "Conversation only" in d and "Code only" in d and "Never mind" in d
    _shot(pg, "rewind")
    pg.locator("#hcdDlg button[value='conversation']").click()
    pg.wait_for_timeout(500)
    assert sent == [{"n": 1, "what": "conversation"}]
    assert not errs, errs
    ctx.close()
