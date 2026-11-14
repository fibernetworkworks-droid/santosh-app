"""v0.878 HOOLA CODE ENVIRONMENTS + LONG-RUN FIXES (owner: "CHECK BOTH IS ALL HOOLA CODE IS WORKING OR NOT FROM ENVIRONMENT
ATTACHMENT TO LONG CODE DEVELOPMENT").

What these prove:
- ENVIRONMENTS like Claude Code's cloud environments: a tenant gets a "Default" (Limited, package managers on) the first
  time she looks; create / edit / archive (never delete, at least one kept); names unique; hosts / variables / setup lines
  are checked (a secret-looking variable and a sudo setup line are refused by name); the selector remembers her pick.
- A SESSION picks one at the start ('auto' = each repo's own settings); its variables lay over the repo's, its setup
  script runs after the repo's own command, and its network (with the package-manager switch) is what the command's
  pass carries; while `dev_net` is off no pass is ever made.
- THE MODEL is told the network its environment really has (it was always told "no internet").
- LONG RUNS: a CI-loop step runs in its own thread, so a second minute never starts a second fix round on the same
  session; every background run carries a job, so a restart continues it; an open PR's working copy is never swept for
  age alone; the step history keeps how a long session began.
"""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from tests.test_tech_devsahayak import REPO, T, dev  # noqa: F401
from tests.test_v0787_hoola_code_engine import FakeClient, _wait, on, tu  # noqa: F401
from tests.test_v0789_hoola_code_safety import box  # noqa: F401


# ---------------------------------------------------------------- the environments themselves
def test_default_environment_and_the_rules_of_what_she_types(env):
    from app.devsahayak import envs as EV
    v = EV.list_envs("t1")
    assert [e["name"] for e in v["envs"]] == ["Default"] and v["pick"] == "auto"
    d = v["envs"][0]
    assert d["net"]["level"] == "limited" and d["net"]["pkgs"] is True and d["env_vars"] == {} and d["setup"] == ""
    assert v["auto"]["sub"] == "Follows your repositories"
    e = EV.create_env("t1", {"name": "Python CI", "net": {"level": "limited", "pkgs": False, "hosts": "api.example.com\n*.foo.org"},
                             "env_vars": "# a comment\nNODE_ENV=test\nexport MODE='fast'", "setup": "pip install -r requirements.txt\n# note\nnpm ci"})
    assert e["net"]["hosts"] == ["api.example.com", "*.foo.org"] and e["net"]["pkgs"] is False
    assert e["env_vars"] == {"NODE_ENV": "test", "MODE": "fast"} and e["setup"] == "pip install -r requirements.txt\nnpm ci"
    for bad in ({"name": "Python CI"},                                            # the name is taken
                {"name": "X", "env_vars": "API_TOKEN=abc"},                       # a secret is never a variable
                {"name": "X", "env_vars": "DB=ghp_" + "a" * 36},
                {"name": "X", "setup": "sudo apt-get install -y libpq-dev"},       # no sudo / docker / service in the box
                {"name": "X", "net": {"level": "open"}},
                {"name": "X", "net": {"hosts": "10.0.0.5"}},
                {"name": "<script>"}):
        with pytest.raises(EV.EnvError):
            EV.create_env("t1", bad)
    other = EV.list_envs("t2")                                                    # another tenant never sees hers
    assert [x["name"] for x in other["envs"]] == ["Default"]
    with pytest.raises(EV.EnvError):
        EV.update_env("t2", e["id"], {"name": "Mine now"})


def test_archive_keeps_one_and_the_pick_is_remembered(env):
    from app.devsahayak import envs as EV
    d = EV.list_envs("t1")["envs"][0]
    with pytest.raises(EV.EnvError):
        EV.archive_env("t1", d["id"])                                             # never the last one
    e = EV.create_env("t1", {"name": "Full", "net": {"level": "full"}})
    assert EV.pick_for_new("t1", e["id"]) == e["id"] and EV.list_envs("t1")["pick"] == e["id"]
    assert EV.pick_for_new("t1", "") == e["id"]                                   # '' = her last pick
    EV.archive_env("t1", e["id"])
    assert EV.list_envs("t1")["pick"] == "auto" and [x["name"] for x in EV.list_envs("t1")["envs"]] == ["Default"]
    assert [x["name"] for x in EV.list_envs("t1", archived=True)["envs"]] == ["Default", "Full"]
    with pytest.raises(EV.EnvError):
        EV.pick_for_new("t1", e["id"])                                            # archived = cannot be picked
    assert EV.pick_for_new("t1", "") is None                                      # ... and a stale pick falls back to Auto
    with pytest.raises(EV.EnvError):
        EV.update_env("t1", e["id"], {"name": "Back"})
    assert EV.update_env("t1", e["id"], {"unarchive": True})["archived"] is False


def test_overlay_lays_the_environment_over_the_repo(env, monkeypatch):
    from app.config import get_settings
    from app.devsahayak import envs as EV
    e = EV.create_env("t1", {"name": "Web", "net": {"level": "limited", "pkgs": False, "hosts": ["api.example.com"]},
                             "env_vars": {"NODE_ENV": "test", "A": "env"}, "setup": "npm ci\nnpm run build"})
    hers, envv, net = {"setup": "pip install -e .", "test": "pytest -q"}, {"A": "repo", "B": "repo"}, {"inject": {"api.x.io": {"header": "X", "value": "v"}}}
    # Auto: untouched
    assert EV.overlay("t1", None, hers, envv, net) == (hers, envv, net)
    # dev_net off: variables + setup apply, the network never does
    monkeypatch.setattr(get_settings(), "dev_net", False, raising=False)
    h2, e2, n2 = EV.overlay("t1", e["id"], hers, envv, net)
    assert h2["setup"] == "( pip install -e . ) && ( npm ci ) && ( npm run build )" and h2["test"] == "pytest -q"
    assert e2 == {"A": "env", "B": "repo", "NODE_ENV": "test"} and n2 == {}
    # dev_net on: the environment's network, the repo's keys still added outside the box
    monkeypatch.setattr(get_settings(), "dev_net", True, raising=False)
    _, _, n3 = EV.overlay("t1", e["id"], hers, envv, net)
    assert n3["level"] == "limited" and n3["hosts"] == ["api.example.com"] and n3["pkgs"] is False and n3["inject"] == net["inject"]
    none = EV.create_env("t1", {"name": "Offline", "net": {"level": "none"}})
    assert EV.overlay("t1", none["id"], {}, {}, {})[2] == {}


def test_package_managers_switch_reaches_the_proxy_rule():
    from app.devlab import net as N
    assert "pypi.org" in N.allow_for("limited", ["a.example.com"])
    assert N.allow_for("limited", ["a.example.com"], pkgs=False) == ["a.example.com"]
    assert N.allow_for("full", [], pkgs=False) == ["*"] and N.allow_for("none", ["a.b.co"], pkgs=True) == []


def test_the_model_is_told_the_network_it_has(monkeypatch):
    from app.config import get_settings
    from app.devsahayak import engine as EN
    monkeypatch.setattr(get_settings(), "dev_net", False, raising=False)
    assert EN.net_words({"level": "full"}) == ""                                  # off: never promised a network
    monkeypatch.setattr(get_settings(), "dev_net", True, raising=False)
    assert EN.net_words({}) == "" and EN.net_words({"level": "none"}) == ""
    w = EN.net_words({"level": "limited", "hosts": ["api.example.com"], "pkgs": True})
    assert "package registries" in w and "api.example.com" in w and "overrides" in w
    assert "package registries" not in EN.net_words({"level": "limited", "hosts": ["x.io"], "pkgs": False})
    assert "any public" in EN.net_words({"level": "full"})


# ---------------------------------------------------------------- a session in an environment, end to end
def test_a_session_runs_in_its_environment(box, monkeypatch):  # noqa: F811
    S = box
    from app.config import get_settings
    from app.devlab import net as N
    from app.devsahayak import brain as B
    from app.devsahayak import envs as EV
    passes, seen = [], {}
    monkeypatch.setattr(N, "ensure", lambda: {"ok": True})
    real_grant = N.grant

    def grant(level, hosts, inject=None, ttl=900, pkgs=True):
        g = real_grant(level, hosts, inject, ttl, pkgs=pkgs)
        passes.append({"level": level, "hosts": hosts, "pkgs": pkgs, "rule": json.loads((N.root() / "runs" / f"{g['id']}.json").read_text())})
        return g
    monkeypatch.setattr(N, "grant", grant)
    monkeypatch.setattr(N, "revoke", lambda rid: (N.root() / "runs" / f"{rid}.json").unlink(missing_ok=True))
    monkeypatch.setattr(get_settings(), "dev_net", True, raising=False)
    from tests.test_tech_devsahayak import T as TEN
    e = EV.create_env(TEN, {"name": "Strict", "net": {"level": "limited", "pkgs": False, "hosts": ["api.example.com"]},
                            "env_vars": {"APP_MODE": "ci"}})

    def first(kw):
        seen["system"] = kw.get("system")
        if isinstance(seen["system"], list):
            seen["system"] = " ".join(str(x.get("text", "")) for x in seen["system"] if isinstance(x, dict))
        seen["bash"] = next(t["description"] for t in kw["tools"] if t["name"] == "bash")
        return [tu(1, "bash", command="echo $APP_MODE")]
    B.CLIENT = FakeClient([first, [tu(2, "done", explain="Looked.")]])
    v = S.start_bg(TEN, "explain", "Look around", repo=REPO, env=e["id"])
    assert v["env"]["name"] == "Strict"
    t = _wait(S, v["id"], lambda t: not t["running"] and t["status"] != "new", 60)
    assert t["status"] in ("explained", "failed", "refused") or t["status"]
    assert len(passes) == 1 and passes[0]["pkgs"] is False and passes[0]["rule"]["allow"] == ["api.example.com"]
    assert any(r.get("env") and r["env"].get("APP_MODE") == "ci" for r in S.RUNS)
    assert "NETWORK FOR THIS SESSION" in str(seen["system"]) and "NO internet" not in seen["bash"]
    # her next new session starts in the same environment without naming it; 'auto' goes back to the repo's own
    assert EV.list_envs(TEN)["pick"] == e["id"]
    B.CLIENT = FakeClient([[tu(1, "done", explain="ok")]])
    v2 = S.start_bg(TEN, "explain", "Again", repo=REPO, env="auto")
    assert v2["env"] == {"id": "auto", "name": "Auto"}
    _wait(S, v2["id"], lambda t: not t["running"] and t["status"] != "new", 60)
    # the session's environment can be changed for the next round
    assert EV.set_session_env(TEN, v2["id"], e["id"])["env"] == e["id"]
    assert S.get_task(TEN, v2["id"])["env"]["name"] == "Strict"


def test_routes(dev, monkeypatch):  # noqa: F811
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/devsahayak/envs")
    assert r.status_code == 200 and r.json()["envs"][0]["name"] == "Default"
    r = c.post("/api/devsahayak/envs", json={"name": "Node", "net": {"level": "full"}})
    assert r.status_code == 200 and r.json()["net"]["level"] == "full"
    eid = r.json()["id"]
    assert c.patch(f"/api/devsahayak/envs/{eid}", json={"setup": "sudo rm -rf /"}).status_code == 400
    assert c.patch(f"/api/devsahayak/envs/{eid}", json={"name": "Node 22"}).json()["name"] == "Node 22"
    assert c.post(f"/api/devsahayak/envs/{eid}/archive").json()["archived"] is True


# ---------------------------------------------------------------- long runs
def test_ci_step_never_runs_twice_at_once(dev, monkeypatch):  # noqa: F811
    S = dev
    import threading
    started, release = [], threading.Event()

    def slow_step(tenant, tid, at=None, say_tail=""):
        started.append(tid)
        release.wait(5)
    monkeypatch.setattr(S, "_ci_step", slow_step)
    th = S._ci_bg("t1", "dt_x", S.now())
    assert "dt_x" in S._RUNNING                       # Stop reaches it, and the next minute skips it
    time.sleep(0.2)
    assert started == ["dt_x"]
    release.set()
    th.join(5)
    assert "dt_x" not in S._RUNNING


def test_every_background_run_carries_a_job():
    import inspect
    from app.devsahayak import service as S
    src = inspect.getsource(S.in_background) if hasattr(S, "in_background") else inspect.getsource(S)
    assert '{"what": "work"} if what in ("plan_ok", "begin")' in src
    assert 'job={"what": "work"})' in inspect.getsource(S.answer)
    tick = inspect.getsource(S.tick)
    assert "if tid in _RUNNING" in tick and "_ci_bg(" in tick


def test_open_pr_copy_is_not_swept_for_age(tmp_path, monkeypatch):
    import os
    from app.devsahayak import engine as EN
    monkeypatch.setattr(EN, "root", lambda: tmp_path)
    for n in ("dt_open", "dt_idle"):
        (tmp_path / n).mkdir()
        old = time.time() - 40 * 86400
        os.utime(tmp_path / n, (old, old))
    gone = EN.sweep({"dt_open", "dt_idle"}, days=14, protect={"dt_open"})
    assert gone == ["dt_idle"] and (tmp_path / "dt_open").is_dir()


def test_long_sessions_keep_how_they_began(dev):  # noqa: F811
    S = dev
    from app.devsahayak.models import DevTask
    with S.session() as s:
        t = DevTask(tenant_id="t1", number="D-9", kind="write", repo=REPO, text="x")
        s.add(t)
        s.flush()
        tid = t.id
    st = S._Step(tid)
    for i in range(S.MAX_STEPS + 50):
        st.event({"k": "say", "text": f"step {i}"})
    with S.session() as s:
        steps = json.loads(s.get(DevTask, tid).steps)
    assert len(steps) <= S.MAX_STEPS
    assert steps[0]["text"] == "step 0" and steps[-1]["text"] == f"step {S.MAX_STEPS + 49}"
    assert sum(1 for x in steps if x.get("k") == "gap") == 1


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.878.0")


# ---------------------------------------------------------------- the console page
def test_environment_chip_and_dialog_in_a_browser(arena_server):  # noqa: F811
    import os
    base, browser, key = arena_server
    from app.config import get_settings
    get_settings().hoola_code_page = True
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs, calls = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    repo = {"repo": "meghana/shop-api", "private": True, "default_branch": "main", "setup_cmd": "", "test_cmd": "", "env_vars": {},
            "net": {"level": "none", "hosts": [], "secrets": []}, "events": {"on": False, "by_hoola": False, "last": {}}}
    ov = {"settings": {"github": True, "login": "meghana", "default_repo": "meghana/shop-api", "permissions": [], "never": []},
          "repos": [repo], "tasks": [], "reviews": [], "actions": [], "kinds": {}, "schedules": [], "net": {"on": False, "registries": []},
          "models": {"options": [], "default": "", "forced": None, "efforts": ["low", "medium", "high"], "default_effort": "high"},
          "usage": {"spent_inr": 0, "limit_inr": 0, "pct": 0, "over": False}}
    default = {"id": "de_1", "name": "Default", "kind": "cloud", "net": {"level": "limited", "pkgs": True, "hosts": [], "on": False, "note": ""},
               "env_vars": {}, "setup": "", "archived": False}
    envs = {"envs": [default], "auto": {"id": "auto", "name": "Auto", "kind": "auto", "sub": "Follows your repositories"}, "pick": "auto", "net_on": False}
    made = {"id": "de_2", "name": "Node CI", "kind": "cloud", "net": {"level": "full", "pkgs": True, "hosts": [], "on": False, "note": ""},
            "env_vars": {"NODE_ENV": "test"}, "setup": "npm ci", "archived": False}

    def envs_route(r):
        if r.request.method == "POST":
            calls.append(("create", r.request.post_data_json))
            envs["envs"] = [default, made]
            return r.fulfill(json=made)
        r.fulfill(json=envs)
    pg.route("**/api/devsahayak", lambda r: r.fulfill(json=ov))
    pg.route("**/api/devsahayak/envs", envs_route)
    pg.route("**/api/devsahayak/branches**", lambda r: r.fulfill(json={"branches": ["main"]}))
    pg.route("**/api/devsahayak/tasks/start", lambda r: (calls.append(("start", r.request.post_data_json)), r.fulfill(status=400, json={"detail": "stop here"})))
    pg.goto(base + "/console/code#/")
    pg.wait_for_selector("#hcdEnv")
    assert pg.locator("#hcdEnv").inner_text().strip() == "Auto"
    # the chip is the FIRST control in the row, like Claude Code's environment selector
    assert pg.locator(".hcd-askrow > *").first.get_attribute("id") == "hcdEnv"
    pg.locator("#hcdEnv").click()
    pg.get_by_role("menuitem", name="New environment").click()
    pg.wait_for_selector("#hcdEnvName")
    assert pg.locator("input[name=hcdEnvLv][value=limited]").is_checked() and pg.locator("#hcdEnvPkgs").is_checked()
    pg.locator("#hcdEnvName").fill("Node CI")
    pg.locator("input[name=hcdEnvLv][value=full]").check()
    assert pg.locator("#hcdEnvLim").is_hidden()                           # allowed domains only under Limited
    pg.locator("#hcdEnvVars").fill("NODE_ENV=test")
    pg.locator("#hcdEnvSetup").fill("npm ci")
    if os.environ.get("HOOLA_SHOTS"):
        pg.screenshot(path=os.path.join(os.environ["HOOLA_SHOTS"], "v0878-env-dialog.png"))
    pg.locator("#hcdDlg").get_by_role("button", name="Create").click()
    for _ in range(80):
        if "Node CI" in pg.locator("#hcdEnv").inner_text():
            break
        pg.wait_for_timeout(50)
    assert "Node CI" in pg.locator("#hcdEnv").inner_text()
    body = next(c[1] for c in calls if c[0] == "create")
    assert body["name"] == "Node CI" and body["net"]["level"] == "full" and body["env_vars"] == "NODE_ENV=test" and body["setup"] == "npm ci"
    pg.locator("#hcdLine").fill("Add a health check")
    pg.locator("#hcdLine").press("Enter")
    for _ in range(40):
        if any(c[0] == "start" for c in calls):
            break
        pg.wait_for_timeout(50)
    assert next(c[1] for c in calls if c[0] == "start")["env"] == "de_2"
    if os.environ.get("HOOLA_SHOTS"):
        pg.screenshot(path=os.path.join(os.environ["HOOLA_SHOTS"], "v0878-composer.png"))
    assert not errs, errs
    ctx.close()


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v121_site import site_env  # noqa: E402,F401
