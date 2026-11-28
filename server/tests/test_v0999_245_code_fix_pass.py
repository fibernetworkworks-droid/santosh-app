"""v0.999.245 HOOLA CODE FIX PASS (owner: read the whole Hoola Code section -> "GO FIX ALL THEN SHOW DESIGN PROTOTYPE"):
the bugs the read found, each held by a test - the page's leftover merge marker, the id two parts shared, the side-panel
choice that was never kept, "Private" sharing that made a public link, the narrow-window bar; the pull request's untrue
"nothing was executed" line + its broken heading; five settings read but never defined, two defined but never read;
her server helper's rules (access, folders, admin commands, time limit) enforced by the helper, "Look only" really look
only, and auto-off enforced by Hoola's server."""
from __future__ import annotations

import importlib.util
import re
from datetime import timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"


def test_the_page_has_no_merge_marker_and_no_shared_ids():
    css = (CON / "hoolacode.css").read_text()
    assert not re.search(r"^(<<<<<<<|=======|>>>>>>>)", css, re.M)
    js = (CON / "code.js").read_text()
    ids = re.findall(r'id="(hcd[A-Za-z0-9]+)"', js)
    assert ids.count("hcdQ") == 1 and 'id="hcdQual"' in js          # the question card and the credits line apart
    assert "$('#hcdQ')" not in js
    rail = next(l for l in js.splitlines() if "rail: ['on', 'off'].includes(p.rail)" in l)
    assert not rail.split("rail:")[0].strip().startswith("//") and "//" not in rail.split("rail:")[0]   # code, not a comment


def test_private_sharing_makes_no_link_and_the_wording_matches():
    js = (CON / "code.js").read_text()
    share = js[js.index("async function shareDialog"):js.index("// ------------------------------------------------------------------ reviews")]
    first = share[:share.index("const url = location.origin")]
    assert "input[name=hcdVis][value=link]" in first and "It stays private - no link was made." in first
    assert "'en-IN'" not in js
    assert "'Rules and limits'" not in js and "Wait for my tap" not in js and ">Open the PR<" not in js
    assert "kv('Model'" not in js                                    # no model row beside a page with no model picker
    assert "function sideFresh" in js and "setInterval(sideFresh, 20000)" in js


def test_narrow_window_rules():
    css = (CON / "hoolacode.css").read_text()
    tail = css[css.rindex("HOOLA CODE FIX PASS"):]
    assert ".hcd-cpmeta{width:calc(100% - 48px);max-width:760px" in tail
    assert '.hcd[data-side="min"] .hcd-side [data-tid]{display:none}' in tail and ".hcd-top{height:auto" in tail
    assert "var(--fm," not in css


def test_the_pull_request_text_is_true():
    from app.devsahayak import service as S
    src = Path(S.__file__).read_text()
    assert "nothing was executed on Hoola's server" not in src
    assert "** (by Hoola Code, for review)" in src and "*** (by Hoola Code" not in src
    assert "ran in a locked box on Hoola's server" in src
    wiring = (Path(S.__file__).parent / "WIRING.md").read_text()
    assert "repo code never runs on Hoola's server" not in wiring and "no public routes" not in wiring


def test_settings_are_defined_and_read(monkeypatch):
    from app.config import Settings, get_settings
    for name, default in (("dev_auto_continue", 3), ("dev_session_inr_cap", 1500.0), ("dev_ci_poll_s", 60),
                          ("dev_plan_remind_h", 2.0), ("dev_unclear_steps", 10)):
        assert getattr(Settings(), name) == default, name
    monkeypatch.setenv("DEV_LAB_TIMEOUT", "120")
    monkeypatch.setenv("DEV_LAB_KEEP", "3")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    from app.devlab import box
    assert box.check_timeout() == 120
    seen = []
    monkeypatch.setattr(box, "images", lambda: [{"image": f"hoola-lab-r{i}", "at": i} for i in range(6)])
    monkeypatch.setattr(box, "forget", lambda im: seen.append(im) or True)
    assert len(box.prune()) == 3
    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.fixture
def vps(env, monkeypatch):
    monkeypatch.setenv("DEV_VPS", "true")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://hoola.example.com")
    from app.config import get_settings
    get_settings.cache_clear()  # type: ignore[attr-defined]
    import app.devsahayak.models  # noqa: F401
    from app.db import init_db
    init_db()
    from app.devsahayak import vps as V
    return V


def test_look_only_never_queues_a_change_and_auto_off_is_enforced(vps):
    V = vps
    t = "tenantfx"
    start = V.pair_start(t, "Box")
    sid = start["id"]
    got = V.enroll(start["code"], {"os": "Ubuntu"})
    assert got["config"]["poll_s"] == 20                              # the helper reads it from the config
    V.set_access(t, sid, access="look", folders=["~/apps/x"])
    r = V.propose(t, sid, "git pull", "~/apps/x", "update")
    assert r["state"] == "refused" and "Look only" in r["reason"]
    assert V.propose(t, sid, "df -h", "~/apps/x")["state"] == "allowed"
    assert V.check_in(got["token"])["remove"] is False
    from app.db import session
    from app.devsahayak.models import DevServer, DevServerCmd
    from app.db import now
    with session() as s:                                               # nothing asked of it for longer than her 7 days
        for c in s.query(DevServerCmd).filter(DevServerCmd.server_id == sid):
            c.created_at = now() - timedelta(days=9)
        s.get(DevServer, sid).created_at = now() - timedelta(days=30)
    assert V.check_in(got["token"])["remove"] is True


def _agent():
    spec = importlib.util.spec_from_file_location("hoola_vps_agent", ROOT / "deploy/hoola-vps/agent.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_helper_enforces_her_rules_itself(tmp_path, monkeypatch):
    A = _agent()
    assert A.AGENT_VER == "1.1.0"
    home = tmp_path / "home"
    (home / "apps" / "x").mkdir(parents=True)
    (home / "other").mkdir()
    monkeypatch.setattr(A, "_home", lambda user="hoola": str(home))
    monkeypatch.setattr(A, "log", lambda m: None)
    A.CONF.update(access="look", folders=["~/apps/x"], admin_cmds=[], cmd_timeout_s=5)
    code, out = A.run_job({"cmd": "touch made.txt", "folder": "~/apps/x"})
    assert code == 126 and "look only" in out and not (home / "apps/x/made.txt").exists()
    assert A.run_job({"cmd": "ls", "folder": "~/other"})[0] == 126                     # outside her folders
    assert A.run_job({"cmd": "echo hi", "folder": "~/apps/x"})[0] == 0
    A.CONF.update(access="ask", folders=[])
    code, out = A.run_job({"cmd": "systemctl restart nginx", "folder": "~", "admin": True})
    assert code == 126 and "did not tick" in out
    A.CONF.update(admin_cmds=["systemctl restart nginx"])
    assert A.not_allowed({"cmd": "systemctl restart nginx", "admin": True}, str(home)) == ""
    A.CONF.update(cmd_timeout_s=1, admin_cmds=[])
    code, out = A.run_job({"cmd": "sleep 30", "folder": "~"})
    assert code == 124                                                                 # her time limit, not 900 s
    assert A.run_job({"cmd": "rm -rf /", "folder": "~"})[0] == 126                     # the never-list still first
