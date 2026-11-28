"""v0.999 PONYTAIL in Hoola Code (owner: 'now ponytell to hoola code', on DietrichGebert/ponytail, MIT, v5.3.3).

The lazy senior developer: the smallest change that fully solves the task (the ladder: does it need to exist, already in
the repo, the standard library, an installed dependency, one line, only then the minimum), never cutting validation,
data-loss handling, security or accessibility; levels lite / full / ultra / off per session; /ponytail-review,
/ponytail-audit and /ponytail-debt as read-only reports."""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "server" / "app" / "devsahayak"


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.devsahayak import engine as EN
    EN.PERMIT.clear()
    EN.PERM_MODE.clear()
    yield EN


def _ses(EN, files=None):
    ses = EN.Session("t1")
    ses.repo.mkdir(parents=True, exist_ok=True)
    for k, v in (files or {"a.py": "x = 1\n"}).items():
        (ses.repo / k).parent.mkdir(parents=True, exist_ok=True)
        (ses.repo / k).write_text(v)
    EN._git(ses.repo, "init", "-q")
    ses.meta.update({"repo": "o/r", "base": EN._commit(ses.repo, "base"), "hidden": []})
    ses.save_meta()
    return ses


# ---------------------------------------------------------------- the rules and the levels
def test_the_ladder_and_the_never_cut_list_are_in_the_rules():
    from app.devsahayak import ponytail as PT
    t = " ".join(PT.block("full").split())
    for must in ("does it need to exist", "already in this repo", "standard library", "installed dependency",
                 "never add a dependency for a few lines", "one line", "minimum code that works",
                 "grep every caller", "root cause once", "keeps its error handling", "one small test",
                 "shortcut: <the limit>, <when to upgrade>", "NEVER cut", "security, accessibility",
                 "what you skipped or did not check", "Ponytail, MIT"):
        assert must in t, must
    assert PT.block("off") == "" and "push back" in PT.block("ultra") and "let her pick" in PT.block("lite")
    assert len(PT.block("ultra")) < 2900                          # rides every request, cached
    notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
    assert "DietrichGebert/ponytail" in notice


def test_the_level_is_hers_then_the_repo_s_then_the_server_s(ws, monkeypatch):
    from app.config import get_settings
    from app.devsahayak import ponytail as PT
    from app.devsahayak import repoconf as RC
    ses = _ses(ws, {".claude/settings.json": json.dumps({"ponytail": "lite"}), "a.py": "x = 1\n"})
    conf = RC.settings(ses.repo)
    assert conf["ponytail"] == "lite" and PT.level(ses, conf) == "lite"
    assert PT.level(ses, {}) == "full"                                       # the server's default
    ses.meta["ponytail"] = "ultra"
    assert PT.level(ses, conf) == "ultra"                                    # her choice wins
    monkeypatch.setattr(get_settings(), "dev_ponytail", "off")
    assert PT.level(SimpleNamespace(meta={}), {}) == "off"


def test_ponytail_with_no_word_switches_on_or_reports(ws, monkeypatch):
    from app.devsahayak import ponytail as PT
    ses = _ses(ws)
    assert PT.parse_level("/ponytail") == (True, "") and PT.parse_level("/ponytail ULTRA") == (True, "ultra")
    assert PT.parse_level("/ponytail stop") == (True, "off") and PT.parse_level("/ponytail-review") == (False, "")
    assert PT.parse_level("please be /ponytail") == (False, "")
    got = PT.set_level(ses, {}, "off")
    assert got["ponytail"] == "off" and ses.meta["ponytail"] == "off" and "next message" in got["said"]
    got = PT.set_level(ses, {}, "")                                          # off + no word = back on
    assert got["ponytail"] == "full"
    got = PT.set_level(ses, {}, "")                                          # on + no word = just says the level
    assert got["ponytail"] == "full" and "Type /ponytail" in got["said"]
    with pytest.raises(ValueError):
        PT.set_level(ses, {}, "extreme")


# ---------------------------------------------------------------- /ponytail-debt
def test_the_debt_ledger_finds_marked_shortcuts_only(ws):
    from app.devsahayak import ponytail as PT
    ses = _ses(ws, {
        "a.py": "x = 1  # shortcut: a list scan, fine to 1,000 rows, use a dict past that\n",
        "b.js": "const y = 2 // shortcut: no retry\n/* ponytail: one worker, add a queue when jobs overlap */\n",
        "c.md": "Press the keyboard shortcut Ctrl+K to search.\n",
        "d.py": "s = 'shortcut: not a comment'\n"})
    rows = PT.debt(ses.repo)
    got = sorted((r["path"], r["line"], r["no_trigger"]) for r in rows)
    assert got == [("a.py", 1, False), ("b.js", 1, True), ("b.js", 2, False)]
    a = next(r for r in rows if r["path"] == "a.py")
    assert a["limit"] == "a list scan" and "1,000 rows" in a["upgrade"]
    txt = PT.debt_text(rows)
    assert "3 markers, 1 with no trigger." in txt and "[no-trigger]" in txt and "Change NO file" in txt
    assert "Clean ledger" in PT.debt_text([])
    ses2 = _ses(ws, {"e.py": "# TODO: later\n"})
    assert [r["path"] for r in PT.debt(ses2.repo, "TODO")] == ["e.py"]       # her own marker word


# ---------------------------------------------------------------- her message
def test_her_commands_ride_her_message(ws):
    EN = ws
    from app.devsahayak import ponytail as PT
    ses = _ses(EN, {"a.py": "x = 1  # shortcut: tiny, grow later\n"})
    tl = EN.Tools(ses, False)
    tl.conf = {}
    evs = []
    assert "senior developer who gets paged" in EN.her_blocks(tl, ses, "/ponytail-review", evs.append)
    assert "inherited it" in EN.her_blocks(tl, ses, "/ponytail-audit src/", evs.append)
    assert "a.py:1" in EN.her_blocks(tl, ses, "/ponytail-debt", evs.append)
    out = EN.her_blocks(tl, ses, "/ponytail ultra", evs.append)
    assert "Ponytail ultra" in out and PT.level(ses, {}) == "ultra"
    assert [e["name"] for e in evs if e.get("k") == "cmd"] == ["ponytail-review", "ponytail-audit", "ponytail-debt", "ponytail"]
    assert "Must fix" in PT.REVIEW and "If we skip it" in PT.AUDIT and "at most 20" in PT.AUDIT


def _round(EN, monkeypatch, text, ses):
    from app.devsahayak import brain as B
    monkeypatch.setattr(EN.Session, "ensure", lambda self, repo, sha, token: {"reused": True})
    asked = []
    monkeypatch.setattr(EN.Tools, "run", lambda self, name, inp: asked.append(self.ask_only) or "ok")
    steps = iter([[{"type": "tool_use", "id": "r1", "name": "read", "input": {"path": "a.py"}}]]
                 + [[{"type": "tool_use", "id": "d1", "name": "done", "input": {"explain": "Ship."}}]] * 3)
    seen, systems, tool_lists = [], [], []

    def call(system, msgs, tools, **k):
        systems.append(system)
        tool_lists.append([t.get("name") for t in tools])
        seen.append(msgs[-1]["content"])
        return next(steps), "tool_use"
    monkeypatch.setattr(B, "call", call)
    t = SimpleNamespace(id="t1", repo="o/r", kind="fix", text=text, base="main", mode="", tenant_id="", conv="")
    try:
        EN._round(None, t, "tok", "", False, "", (lambda e: None), None, None, "", None, "sha", "", "", ses)
    except Exception:  # noqa: BLE001 - the git parts after done are not what this test checks
        pass
    EN._ASKED = asked
    return seen, systems, tool_lists


def test_a_round_carries_the_ladder_and_an_audit_changes_nothing(ws, monkeypatch):
    EN = ws
    ses = _ses(EN)
    seen, systems, _ = _round(EN, monkeypatch, "add a date picker", ses)
    assert "THE SMALLEST COMPLETE CHANGE" in systems[0]
    ses2 = _ses(EN)
    ses2.meta["ponytail"] = "off"
    ses2.save_meta()
    seen, systems, tools = _round(EN, monkeypatch, "/ponytail-audit", ses2)
    assert "THE SMALLEST COMPLETE CHANGE" not in systems[0]                 # off = left out
    assert "/ponytail-audit" in json.dumps(seen[0])
    assert EN._ASKED and all(EN._ASKED)                                     # a report: the round writes nothing


def test_web_phone_agents_and_review_have_it():
    js = (ROOT / "server/app/static/console/code.js").read_text()
    assert "ponytail: {d:" in js and "/ponytail`" in js and "'ponytail-audit'" in js and "'ponytail-debt'" in js
    assert "ponytail" in (DEV / "api.py").read_text()
    dart = (ROOT / "lib/ui/code/code_assist.dart").read_text()
    assert "('ponytail', " in dart and "codeSentToHoola" in dart and "'ponytail-review'" in dart
    assert "codeSetPonytail" in (ROOT / "lib/ui/code/code_session.dart").read_text()
    claude = (ROOT / "lib/ui/code/code_claude.dart").read_text()
    assert "Future<void> codeSetPonytail" in claude and "withValues" not in claude
    assert "PT.SUB_RULES" in (DEV / "subagent.py").read_text()
    assert "PT.REVIEW_EXTRA" in (DEV / "service.py").read_text()


def test_version():
    from app.main import APP_VERSION
    assert re.match(r"^\d+\.\d+\.\d+", APP_VERSION)
