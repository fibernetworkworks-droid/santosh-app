"""v0.947 HOOLA AUTO (owner: "IN APP AND WEB CONSOLE THERE WILL BE A SEPERATE SECTION ... HOOLA AUTO IN CODE SECTION" ->
design canvas claude.ai/artifact/1JwAQ3KaPuxzusDHf1UzPz -> "GO BUILD").

What these prove, with a fake model, a fake GitHub and fake Hoola Code sessions:
- INTAKE: 30 questions in 10 sections; her words and the client's are scrubbed of keys, a GitHub token is refused; a
  source's answers arrive as 'found' with where they came from, a disagreeing source makes a CONFLICT she settles.
- THE CLIENT LINK: shown once, only its sha256 kept, one project, no documents or source text ever reach the client,
  a wrong or switched-off link is 404, sign-off is recorded.
- GATES: every gate needs the hash of what she saw; changes re-run that step with her words; G1 -> design -> G2 ->
  G3 -> the project branch is made and sprint 1 starts.
- THE CONDUCTOR: agents start as real Hoola Code sessions on the project branch (never her main branch), at most
  `auto_parallel` at once; a PR joins the project branch only with green / no CI; a PR against another base or red CI
  = needs her; a finished sprint opens G4; the last sprint -> UAT (G6) -> go-live PR (G7) -> handover (G8) -> done.
- HER MAIN BRANCH: changes only through golive_merge with the head sha she saw; red CI needs her written reason.
- THE CAP: past the cost cap every agent stops and the project pauses.
- AGENT CHAT: an in-spec correction goes into the running session; something new becomes a priced change request (G5)
  and nothing is built for it before her yes.
- Another tenant never sees a project.
"""
from __future__ import annotations

import json

import pytest

T = "default"


class FakeGh:
    def __init__(self):
        self.refs, self.merges, self.prs, self.ci = [], [], [], {}
        self.branches = {"me/clinic": {"main": "a" * 40}}

    def repo(self, full):
        return {"default_branch": "main", "description": "clinic"}

    def branch_sha(self, full, branch):
        return self.branches.get(full, {}).get(branch, "")

    def req(self, method, path, body=None, **kw):
        if method == "POST" and path.endswith("/git/refs"):
            full = path.split("/repos/")[1].split("/git/")[0]
            name = body["ref"].replace("refs/heads/", "")
            assert name.startswith("hoola/auto-"), "Hoola Auto only makes its own branch"
            self.branches.setdefault(full, {})[name] = body["sha"]
            self.refs.append((full, name))
            return {}
        raise AssertionError(f"unexpected {method} {path}")

    def checks(self, full, sha):
        state = self.ci.get(sha, "success")
        if state == "none":
            return [], []
        return [{"name": "test", "status": "completed" if state != "pending" else "in_progress",
                 "conclusion": "success" if state == "success" else "failure"}], []

    def merge(self, full, n, sha, method, title):
        self.merges.append((full, n, sha, method))
        return {"merged": True}

    def open_pr(self, full, head, base, title, body, draft=False):
        assert base == "main" and head.startswith("hoola/auto-")
        self.prs.append((full, head, base))
        return {"number": 900 + len(self.prs), "html_url": f"https://github.com/{full}/pull/{900 + len(self.prs)}"}

    def pr(self, full, n):
        return {"head": {"sha": "f" * 40}}

    def workflows(self, full):
        return [{"path": ".github/workflows/ci.yml"}]

    def tree(self, full, sha):
        return [{"path": "README.md", "type": "blob"}, {"path": "app/main.py", "type": "blob"}]

    def file(self, full, path, ref):
        return ("# Clinic\nDoctors 4. Slots of 15 minutes.", "x")


PLAN = {"title": "Clinic booking app", "summary": "Patients book slots.", "scope": [{"title": "Booking", "stories": 2}],
        "out": ["Video calls"], "done_when": "Tests pass and UAT signed.", "assumptions": ["15 minute slots"],
        "stories": [{"id": "S-01", "title": "Book a slot", "acceptance": ["two people never get one slot"]},
                    {"id": "S-02", "title": "Cancel", "acceptance": ["slot frees"]}],
        "tasks": [{"role": "builder_api", "title": "Slot booking API", "detail": "lock", "story": "S-01", "sprint": 1},
                  {"role": "test", "title": "Tests for slot booking", "story": "S-01", "sprint": 1, "depends": [1]},
                  {"role": "devops", "title": "CI and staging", "sprint": 1},
                  {"role": "builder_web", "title": "Cancel screen", "story": "S-02", "sprint": 2},
                  {"role": "architect", "title": "should be dropped", "sprint": 1},
                  {"role": "builder_api", "title": "sprint 9 clamps", "sprint": 9}],
        "sprints": 2, "weeks": 4}
DESIGN = {"architecture": ["FastAPI API", "Postgres"], "data": [{"name": "slots", "fields": ["doctor_id", "start"]}],
          "api": ["POST /book - book a slot"], "screens": [{"name": "Book", "for": "patient", "shows": "free slots"}],
          "risks": [{"risk": "double booking", "plan": "row lock"}], "stack": "FastAPI + Flutter"}


@pytest.fixture
def auto(env, monkeypatch):
    from app.devsahayak import service as DS
    from app.devsahayak.models import DevTask
    from app.db import session
    from app.hoolaauto import service as S
    gh = FakeGh()
    started, running, notes, stopped = [], set(), [], []
    answers = {"next": None}

    def model(system, prompt, max_tokens=8000):
        if "Planner" in system:
            return json.loads(json.dumps(PLAN))
        if "Architect" in system:
            return DESIGN
        if "Intake agent" in system:
            return answers["next"] or {"answers": []}
        if "agent of Hoola Auto" in system:
            return answers["chat"]
        raise AssertionError(system[:60])

    def start_bg(tenant, kind, text, repo="", base="", mode="", env="", **kw):
        with session() as s:
            d = DevTask(tenant_id=tenant, number=f"D-{len(started) + 1:04d}", kind=kind, repo=repo, text=text, status="new",
                        base=base)
            s.add(d)
            s.flush()
            tid = d.id
        started.append({"id": tid, "kind": kind, "repo": repo, "base": base, "mode": mode, "text": text})
        running.add(tid)
        return {"task": {"id": tid}}

    monkeypatch.setattr(S, "model_json", model)
    monkeypatch.setattr(DS, "start_bg", start_bg)
    monkeypatch.setattr(DS, "gh", lambda tenant: gh)
    monkeypatch.setattr(DS, "_token", lambda tenant: "x")
    monkeypatch.setattr(DS, "repos", lambda tenant: [{"repo": "me/clinic", "secrets": [{"host": "api.razorpay.com"}]}])
    monkeypatch.setattr(DS, "running", lambda tid: tid in running)
    monkeypatch.setattr(DS, "stop", lambda tenant, ref: stopped.append(ref) or {"ok": True})

    def add_note(tenant, ref, text, comments=None):
        if ref not in running:
            raise DS.DevError("not working")
        notes.append((ref, text))
        return {"ok": True}
    monkeypatch.setattr(DS, "add_note", add_note)

    def finish(tid, status="pr_open", pr=10, head="h" * 40, base=None, cost_usd=0.0):
        running.discard(tid)
        with session() as s:
            d = s.get(DevTask, tid)
            d.status, d.pr_number, d.head_sha = status, pr, head
            if base is not None:
                d.base = base
            d.changes = json.dumps([{"path": "app/x.py", "added": 10, "removed": 2}])
            d.cost = json.dumps({"usd": cost_usd})

    S.T = dict(gh=gh, started=started, running=running, notes=notes, stopped=stopped, answers=answers, finish=finish)
    yield S


def _project(S, **kw):
    return S.create_project(T, {"name": "Clinic booking app", "client_name": "Sai Dental", "repos": ["me/clinic"], **kw})


def _to_build(S, pid):
    S.send_for_review(T, pid)
    for code in ("G1", "G2", "G3"):
        g = next(x for x in S.gates(T, pid) if x["code"] == code)
        assert g["state"] == "now", code
        S.decide(T, pid, g["id"], True, g["hash"])


# ------------------------------------------------------------------------------------------------ intake
def test_intake_questions_scrub_and_conflicts(auto):
    S = auto
    p = _project(S)
    v = S.intake_view(T, p["id"])
    assert sum(len(sec["fields"]) for sec in v["sections"]) == 30 and len(v["sections"]) == 10
    assert v["next"]["key"] == "goal"                                   # repos is already answered from the project
    out = S.answer(T, p["id"], "payments", "Razorpay. api_key=rzp_live_abcdefghijklmnop123")
    f = {x["key"]: x for sec in out["sections"] for x in sec["fields"]}
    assert "rzp_live_abcdefghijklmnop123" not in f["payments"]["value"] and out["warn"]
    with pytest.raises(S.AutoError):
        S.answer(T, p["id"], "goal", "ghp_" + "a" * 36)
    S.T["answers"]["next"] = {"answers": [{"key": "goal", "value": "Fewer missed appointments", "where": "page 1"},
                                          {"key": "payments", "value": "Cashfree", "where": "page 3"},
                                          {"key": "nonsense", "value": "x"}]}
    S.add_source(T, p["id"], {"kind": "text", "name": "Email from Dr. Sai", "text": "We want fewer missed appointments " * 3},
                 background=False)
    f = {x["key"]: x for sec in S.intake_view(T, p["id"])["sections"] for x in sec["fields"]}
    assert f["goal"]["state"] == "found" and f["goal"]["source_ref"] == "Email from Dr. Sai, page 1"
    assert f["payments"]["state"] == "conflict" and f["payments"]["alt"]["value"] == "Cashfree"
    S.confirm(T, p["id"], "payments", "b")
    f = {x["key"]: x for sec in S.intake_view(T, p["id"])["sections"] for x in sec["fields"]}
    assert f["payments"]["value"] == "Cashfree" and f["payments"]["state"] == "confirmed"
    src = S.sources_view(T, p["id"])
    assert src["sources"][0]["answers"] == 2 and src["counts"]["found"] == 1


def test_client_link_is_one_project_and_never_shows_sources(auto):
    from app.hoolaauto.models import AutoProject
    from app.db import session
    S = auto
    p = _project(S)
    link = S.client_link(T, p["id"])
    tok = link["token"]
    with session() as s:
        row = s.get(AutoProject, p["id"])
        assert tok not in (row.client_hash or "") and row.client_tail == tok[-4:]
    S.T["answers"]["next"] = {"answers": [{"key": "goal", "value": "Fewer no-shows", "where": "p1"}]}
    S.add_source(T, p["id"], {"kind": "text", "name": "secret plan.txt", "text": "INTERNAL margin 40 percent. Fewer no-shows."},
                 background=False)
    v = S.client_view(tok)
    blob = json.dumps(v)
    assert "INTERNAL margin" not in blob and v["project"] == "Clinic booking app"
    assert v["check"][0]["key"] == "goal" and "source" not in v["check"][0]
    out = S.client_answer(tok, "budget", "4 lakh, password: hunter22")
    assert "hunter22" not in json.dumps(out)
    S.client_confirm(tok, "goal")
    S.client_signoff(tok)
    assert S.client_view(tok)["signed"]
    with pytest.raises(S.AutoError) as e:
        S.client_view(tok[:-2] + "zz")
    assert e.value.status == 404
    S.client_link(T, p["id"], on=False)
    with pytest.raises(S.AutoError):
        S.client_view(tok)


# ------------------------------------------------------------------------------------------------ gates
def test_gates_need_the_hash_and_changes_rerun(auto):
    S = auto
    p = _project(S)
    v = S.send_for_review(T, p["id"])
    assert v["phase"] == "review" and v["plan"]["tasks"][-1]["sprint"] == 2            # sprint 9 clamped to 2
    assert all(t["role"] != "architect" for t in v["plan"]["tasks"])                   # a non-session role gets no task
    g1 = next(x for x in S.gates(T, p["id"]) if x["code"] == "G1")
    assert g1["state"] == "now" and g1["body"]["tasks"] == 5
    with pytest.raises(S.AutoError) as e:
        S.decide(T, p["id"], g1["id"], True, "wrong")
    assert e.value.status == 409
    S.decide(T, p["id"], g1["id"], False, g1["hash"], "Add a waiting list")                   # changes = a new plan, G1 again
    g1b = next(x for x in S.gates(T, p["id"]) if x["code"] == "G1")
    assert g1b["state"] == "now"
    S.decide(T, p["id"], g1b["id"], True, g1b["hash"])
    g2 = next(x for x in S.gates(T, p["id"]) if x["code"] == "G2")
    assert g2["state"] == "now" and g2["body"]["stack"] == "FastAPI + Flutter"
    S.decide(T, p["id"], g2["id"], True, g2["hash"])
    g3 = next(x for x in S.gates(T, p["id"]) if x["code"] == "G3")
    assert g3["body"]["tasks"] == 5 and "main branch changes only at G7" in g3["body"]["merge_rule"]
    S.decide(T, p["id"], g3["id"], True, g3["hash"])
    pv = S.project_view(T, p["id"])
    assert pv["phase"] == "build" and pv["branch"].startswith("hoola/auto-clinic-booking-app")
    assert S.T["gh"].refs == [("me/clinic", pv["branch"])]


# ------------------------------------------------------------------------------------------------ the conductor
def test_agents_work_on_the_project_branch_and_sprints_end_at_gates(auto, monkeypatch):
    S = auto
    monkeypatch.setattr(S, "_parallel", lambda: 2)
    p = _project(S)
    pid = p["id"]
    _to_build(S, pid)
    started = S.T["started"]
    branch = S.project_view(T, pid)["branch"]
    assert len(started) == 2                                       # task 2 waits for task 1; the limit is 2
    assert all(x["base"] == branch and x["mode"] == "auto" for x in started)
    assert started[0]["kind"] == "write" and "Builder · API agent" in started[0]["text"] and "Story S-01" in started[0]["text"]
    assert {x["kind"] for x in started} == {"write"}               # builder_api + devops
    m = S.mission(T, pid)
    assert {a["role"]: a["state"] for a in m["agents"]}["builder_api"] in ("working", "queued")
    # a PR against her main branch is never merged by the conductor
    S.T["finish"](started[1]["id"], base="main")
    # the API task: green CI -> joins the project branch
    S.T["finish"](started[0]["id"], pr=11, head="1" * 40)
    S.tick_project(T, pid)
    assert S.T["gh"].merges == [("me/clinic", 11, "1" * 40, "squash")]
    m = S.mission(T, pid)
    t = {x["seq"]: x for x in m["tasks"]}
    assert t[1]["state"] == "done" and t[1]["proof"]["pr"] == 11
    assert t[3]["state"] == "needs" and "not the project branch" in t[3]["why"]
    assert any(n["kind"] == "task" for n in m["needs"])
    assert len(started) == 3 and started[2]["kind"] == "tests"     # task 2 started once its dependency was done
    # red CI = needs her, never merged
    S.T["gh"].ci["2" * 40] = "failure"
    S.T["finish"](started[2]["id"], pr=12, head="2" * 40)
    S.tick_project(T, pid)
    assert len(S.T["gh"].merges) == 1 and {x["seq"]: x for x in S.mission(T, pid)["tasks"]}[2]["state"] == "needs"
    # she fixes both: retry restarts the tasks, then both finish green -> sprint 1 is done -> G4
    for x in S.mission(T, pid)["tasks"]:
        if x["state"] == "needs":
            S.retry_task(T, pid, x["id"])
    for d in S.T["started"][3:]:
        S.T["finish"](d["id"], pr=20, head="3" * 40, base=branch)
    S.tick_project(T, pid)
    g4 = next(x for x in S.gates(T, pid) if x["code"] == "G4")
    assert g4["state"] == "now" and g4["n"] == 1 and len(g4["body"]["done"]) == 3
    n_before = len(S.T["started"])
    S.tick_project(T, pid)
    assert len(S.T["started"]) == n_before                          # nothing new starts while a gate waits
    S.decide(T, pid, g4["id"], True, g4["hash"])
    assert S.project_view(T, pid)["sprint"] == 2 and len(S.T["started"]) == n_before + 2
    for d in S.T["started"][n_before:]:
        S.T["finish"](d["id"], pr=30, head="4" * 40, base=branch)
    S.tick_project(T, pid)
    g4b = next(x for x in S.gates(T, pid) if x["code"] == "G4" and x["n"] == 2)
    S.decide(T, pid, g4b["id"], True, g4b["hash"])
    g6 = next(x for x in S.gates(T, pid) if x["code"] == "G6")
    assert g6["state"] == "now" and S.project_view(T, pid)["phase"] == "uat"
    S.decide(T, pid, g6["id"], True, g6["hash"])
    g7 = S.gate(T, pid, next(x for x in S.gates(T, pid) if x["code"] == "G7")["id"])
    S.decide(T, pid, g7["id"], True, g7["hash"])
    assert S.T["gh"].prs == [("me/clinic", branch, "main")]          # the go-live PR is opened, NOT merged
    assert len(S.T["gh"].merges) == 5                                # only the project-branch merges so far
    docs = S.T["started"][-1]
    assert docs["kind"] == "docs" and docs["base"] == branch
    S.T["finish"](docs["id"], pr=40, head="5" * 40, base=branch)
    S.tick_project(T, pid)
    g8 = next(x for x in S.gates(T, pid) if x["code"] == "G8")
    S.decide(T, pid, g8["id"], True, g8["hash"])
    assert S.project_view(T, pid)["phase"] == "done" and S.list_projects(T)["projects"][0]["pct"] == 100


def test_her_main_branch_needs_the_sha_and_a_reason_for_red_ci(auto):
    S = auto
    p = _project(S)
    pid = p["id"]
    from app.hoolaauto.models import AutoProject
    from app.db import session
    with session() as s:
        row = s.get(AutoProject, pid)
        row.golive, row.phase = json.dumps([{"repo": "me/clinic", "base": "main", "pr": 901, "url": "u", "state": "open"}]), "handover"
    with pytest.raises(S.AutoError) as e:
        S.golive_merge(T, pid, 0, "0" * 12)
    assert e.value.status == 409 and not S.T["gh"].merges
    S.T["gh"].ci["f" * 40] = "failure"
    with pytest.raises(S.AutoError):
        S.golive_merge(T, pid, 0, "f" * 12)
    S.golive_merge(T, pid, 0, "f" * 12, "Client tested on staging, CI flaky")
    assert S.T["gh"].merges == [("me/clinic", 901, "f" * 40, "merge")]


def test_cost_cap_stops_every_agent(auto, monkeypatch):
    S = auto
    p = _project(S)
    pid = p["id"]
    _to_build(S, pid)
    S.update_project(T, pid, {"cap_inr": 100})
    live = [d["id"] for d in S.T["started"]]
    S.T["finish"](live[0], status="new", cost_usd=5.0)               # still working, but Rs 400+ spent
    S.T["running"].add(live[0])
    S.tick_project(T, pid)
    pv = S.project_view(T, pid)
    assert pv["paused"] and set(S.T["stopped"]) >= {live[1]}
    assert any("cost cap" in f["text"] for f in S.mission(T, pid)["feed"])


def test_agent_chat_in_spec_goes_to_the_session_and_new_work_is_a_change(auto):
    S = auto
    p = _project(S)
    pid = p["id"]
    _to_build(S, pid)
    api_task = S.T["started"][0]["id"]
    S.T["answers"]["chat"] = {"kind": "in_spec", "reply": "Changed to 15-minute slots."}
    v = S.message(T, pid, "builder_api", "Use 15-minute slots, not 30.")
    assert S.T["notes"] == [(api_task, "Use 15-minute slots, not 30.")]
    assert v["chat"][-1]["tag"] == "Applied to task 1"
    S.T["answers"]["chat"] = {"kind": "change", "reply": "That is new, so I made it a change request.", "title": "Lunch block",
                              "minutes": 25, "tests": 2}
    n = len(S.T["started"])
    v = S.message(T, pid, "builder_api", "Also block 1 to 2 pm for lunch.")
    ch = v["chat"][-1]["change"]
    assert ch["cr"] == "CR-01" and ch["state"] == "wait" and ch["cost_inr"] > 0 and ch["hash"]
    assert len(S.T["started"]) == n                                  # nothing built before her yes
    S.decide(T, pid, ch["gate"], True, ch["hash"])
    assert any(t["title"].startswith("CR-01") for t in S.mission(T, pid)["tasks"])


def test_other_tenant_and_routes(auto):
    S = auto
    p = _project(S)
    with pytest.raises(S.AutoError) as e:
        S.mission("someone-else", p["id"])
    assert e.value.status == 404
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/auto/c/" + "x" * 30).status_code == 404
    r = c.get("/auto/intake/" + "x" * 30)
    assert r.status_code == 200 and "noindex" in r.headers.get("x-robots-tag", "")
    tok = S.client_link(T, p["id"])["token"]
    assert c.get(f"/api/auto/c/{tok}").json()["project"] == "Clinic booking app"


def test_env_view_says_what_is_and_is_not_connected(auto):
    S = auto
    p = _project(S)
    v = S.env_view(T, p["id"])
    assert v["ready"] and v["repos"][0]["ci"] == "Found" and v["repos"][0]["keys"] == ["api.razorpay.com"]
    assert "No app is connected for reading yet" in v["not_connected"]      # v0.949: apps are readable now
    p2 = S.create_project(T, {"name": "No repo yet"})
    assert p2["phase"] == "setup" and not S.env_view(T, p2["id"])["ready"]
    with pytest.raises(S.AutoError):
        S.send_for_review(T, p2["id"])


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.162"
    assert "0.999.162+1157" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
