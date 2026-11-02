"""MASTER ARCHITECT - the Principal Software Architect for any architecture job: six kinds of work (design / assess /
migrate / decide / threat / scale), her repo's module map + cycles from the REAL import lines, boundary rules checked by
code on the repo and on every PR, decision scoring + sensitivity, STRIDE risk scores + coverage, 1x/10x/100x growth
scenarios, OpenAPI contract check, a peer review + one revision of every draft, design checks - all numbers in code."""
import json
from types import SimpleNamespace

import pytest

REPO = {
    "app/orders/api.py": "from app.orders import service\nfrom app.riders.models import Rider\nimport fastapi\n",
    "app/orders/service.py": "from app.payments.client import pay\n",
    "app/payments/client.py": "from app.orders.service import x\nimport requests\n",
    "app/riders/models.py": "import sqlalchemy\n",
    "web/src/pages/cart.ts": "import { api } from '../lib/api'\nimport React from 'react'\n",
    "web/src/lib/api.ts": "export const api = 1\n",
    "README.md": "# Shop",
}

DESIGN = {
    "title": "Shop", "summary": "A **modular monolith**.\n- one DB", "context": {"goals": ["sell"], "users": "buyers"},
    "nfrs": [{"name": "Latency", "target": "fast", "why": "x"}],
    "capacity_inputs": {"dau": 20000, "peak_factor": 3, "write_ratio": 0.2, "source": {"dau": "her"}},
    "components": [{"name": "Orders API", "kind": "service", "responsibility": "orders", "tech": "FastAPI"},
                   {"name": "Payments", "kind": "service", "responsibility": "pay", "tech": "FastAPI"}],
    "adrs": [{"id": "ADR-001", "title": "Postgres", "decision": "Postgres", "alternatives": ["Mongo - no tx"]}],
    "risks": [{"risk": "r", "likelihood": "high", "impact": "high", "mitigation": "m"}],
    "roadmap": [{"phase": "P1", "what": "w", "exit": "e"}], "security": ["OTP"], "failure_modes": [{"what": "w"}],
    "diagrams": [{"name": "Context", "kind": "context", "mermaid": "flowchart LR\n  O[Orders API] --> P[Payments]"}],
    "fitness_rules": [{"name": "Orders do not reach into riders", "from": "app/orders", "must_not_depend_on": "app/riders",
                       "why": "riders own their data"}],
    "api": "openapi: 3.1.0\ninfo: {title: Shop, version: '1'}\npaths:\n  /orders:\n    post:\n      responses:\n        '201': {description: ok}\n",
    "decision": {"question": "Which database?",
                 "criteria": [{"name": "Transactions", "weight": 5}, {"name": "Cost", "weight": 2}],
                 "options": [{"name": "PostgreSQL", "scores": {"Transactions": 5, "Cost": 4}, "pros": ["ACID"]},
                             {"name": "MongoDB", "scores": {"Transactions": 2, "Cost": 4}, "cons": ["no joins"]}],
                 "recommendation": "PostgreSQL"},
    "threats": [{"target": "Orders API", "stride": "S", "threat": "stolen token", "likelihood": "high", "impact": "high",
                 "mitigation": "short tokens", "status": "partial"},
                {"target": "Orders API", "stride": "T", "threat": "price edit", "likelihood": "low", "impact": "high",
                 "mitigation": "server prices", "status": "in place"}],
    "assessment": {"as_is": "one app", "problems": [{"area": "coupling", "finding": "cycle", "evidence": "app/orders <-> app/payments",
                                                     "severity": "high", "fix": "split"}],
                   "scorecard": [{"dimension": "Modularity", "score": 2, "why": "cycle"},
                                 {"dimension": "Security", "score": 4, "why": "ok"}]},
}


class FakeGh:
    def __init__(self):
        self.reviews = []

    def repo(self, full):
        return {"default_branch": "main", "description": "shop"}

    def branch_sha(self, full, branch):
        return "sha1"

    def tree(self, full, sha):
        return [{"path": p, "type": "blob"} for p in REPO]

    def file(self, full, path, ref):
        return REPO.get(path, ""), "b"

    def pr(self, full, n):
        return {"title": "Show rider on order", "body": "", "head": {"sha": "h9"}}

    def pr_files(self, full, n):
        return [{"filename": "app/orders/service.py", "status": "modified", "additions": 1, "deletions": 0,
                 "patch": "@@ -1 +1,2 @@\n from app.payments.client import pay\n+from app.riders.models import Rider"}]

    def open_prs(self, full):
        return []

    def review(self, *a, **k):
        self.reviews.append(a)
        return {"id": 1}


@pytest.fixture()
def M(env, monkeypatch, tmp_path):
    from app.archdesk import diagrams, service
    from app.devsahayak import service as dev
    from app.employee import hire
    monkeypatch.setenv("ARCH_DIR", str(tmp_path / "arch"))
    calls = {"systems": [], "prompts": []}
    gh = FakeGh()
    state = {"peer": {"verdict": "needs_changes", "issues": [{"severity": "high", "area": "NFR", "issue": "latency not measurable",
                                                               "fix": "p95 < 300 ms"}]}}

    def fake_model(system, prompt, max_tokens=16000):
        calls["systems"].append(system[:60])
        calls["prompts"].append(prompt)
        if system.startswith("You are a second Principal Software Architect"):
            return state["peer"]
        if system.startswith("You are the Principal Software Architect who wrote"):
            return {"verdict": "fits", "summary": "ok", "findings": []}
        d = json.loads(json.dumps(DESIGN))
        if "revising YOUR draft" in system:
            d["nfrs"][0]["target"] = "p95 < 300 ms"
        return d

    def fake_render(items, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        res = []
        for i, it in enumerate(items):
            (out_dir / f"d{i + 1}.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>")
            res.append({"name": it.get("name"), "mermaid": diagrams.clean(it.get("mermaid", "")), "ok": True, "error": "",
                        "svg": f"d{i + 1}.svg", "png": ""})
        return res

    pdfs = {}
    monkeypatch.setattr(service, "model_json", fake_model)
    monkeypatch.setattr(service, "_spawn", lambda fn, *a: fn(*a))
    monkeypatch.setattr(service.diagrams, "render", fake_render)

    real_pdf = service._pdf

    def capture_pdf(design, cap, drawn, vdir, facts, extra=None):
        from app.docstudio import htmlpdf

        class P:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def pdf(self, html):
                pdfs["html"] = html
                return b"%PDF fake"
        monkeypatch.setattr(htmlpdf, "Printer", P)
        real_pdf(design, cap, drawn, vdir, facts, extra)
    monkeypatch.setattr(service, "_pdf", capture_pdf)
    monkeypatch.setattr(dev, "gh", lambda tenant: gh)
    monkeypatch.setattr(dev, "_repo", lambda tenant, name="": SimpleNamespace(full_name="meghana/shop"))
    hire.hire("default", "architect")
    return SimpleNamespace(s=service, calls=calls, gh=gh, state=state, pdfs=pdfs)


# ------------------------------------------------------------------ the module map (code, not the model)
def test_module_map_from_real_imports_finds_cycles_and_hotspots():
    from app.archdesk import repomap
    g = repomap.build(REPO)
    edges = {(e["from"], e["to"]) for e in g["edges"]}
    assert ("app/orders", "app/riders") in edges and ("app/orders", "app/payments") in edges
    assert ("app/payments", "app/orders") in edges
    assert ("web/src", "web/src") not in edges                       # same module never an edge
    assert ["app/orders", "app/payments"] in g["cycles"]
    assert g["external_imports"] >= 3                                # fastapi, requests, react, sqlalchemy - counted, not guessed
    assert g["hotspots"][0]["module"] == "app/orders"
    mer = repomap.mermaid(g)
    assert mer.startswith("flowchart LR") and "==>" in mer           # the cycle drawn thick
    from app.archdesk import diagrams
    assert diagrams.clean(mer)


def test_js_go_and_java_imports_resolve_inside_the_repo_only():
    from app.archdesk import repomap
    files = {"web/src/pages/a.ts": "import x from '../lib/b'\nimport y from 'lodash'\n", "web/src/lib/b.ts": "",
             "svc/api/h.go": 'package api\nimport (\n  "fmt"\n  "example.com/shop/svc/store"\n)\n', "svc/store/s.go": "package store",
             "go.mod": "module example.com/shop\n",
             "src/main/java/com/shop/web/A.java": "import com.shop.core.B;\nimport java.util.List;\n",
             "src/main/java/com/shop/core/B.java": ""}
    g = repomap.build(files, depth=4)
    e = {(x["from"], x["to"]) for x in g["edges"]}
    assert ("svc/api", "svc/store") in e
    assert ("src/main/java/com", "src/main/java/com") not in e
    g2 = repomap.build(files, depth=5)
    assert ("src/main/java/com/shop", "src/main/java/com/shop") not in {(x["from"], x["to"]) for x in g2["edges"]}


def test_boundary_rules_on_the_repo_and_on_only_the_lines_a_pr_adds():
    from app.archdesk import repomap
    rules = repomap.clean_rules([{"from": "app/orders/", "must_not_depend_on": "app/riders"}, {"from": "x"}, "junk"])
    assert len(rules) == 1
    now = repomap.check_rules(rules, repomap.build(REPO)["edges"])
    assert now and now[0]["from"] == "app/orders" and now[0]["to"] == "app/riders"
    files = [{"filename": "app/orders/service.py", "patch": " from app.riders.models import Rider\n+import os"}]
    assert repomap.pr_edges(files, list(REPO)) == []                 # an OLD import line is never blamed on the PR
    files[0]["patch"] = "+from app.riders.models import Rider"
    assert repomap.check_rules(rules, repomap.pr_edges(files, list(REPO)))


# ------------------------------------------------------------------ the sums
def test_decision_is_scored_in_code_with_sensitivity_and_named_gaps():
    from app.archdesk import master
    x = master.shape("decide", DESIGN)
    r = master.decide(x["decision"])
    assert r["winner"] == "PostgreSQL" and r["totals"][0]["score"] == round(100 * (5 * 5 + 2 * 4) / (5 * 7), 1)
    assert r["robust"] and not r["missing"]
    d2 = json.loads(json.dumps(DESIGN))
    d2["decision"]["options"][1]["scores"] = {"Transactions": 5}       # Mongo now ties on transactions, Cost missing
    r2 = master.decide(master.shape("decide", d2)["decision"])
    assert r2["missing"] == ["MongoDB / Cost"]
    d3 = json.loads(json.dumps(DESIGN))
    d3["decision"]["options"] = d3["decision"]["options"][:1]
    assert "error" in master.decide(master.shape("decide", d3)["decision"])
    d4 = json.loads(json.dumps(DESIGN))                                 # a close call flips with one weight
    d4["decision"]["options"][1]["scores"] = {"Transactions": 4, "Cost": 5}
    d4["decision"]["criteria"][0]["weight"] = 2
    r4 = master.decide(master.shape("decide", d4)["decision"])
    assert r4["close"] and r4["flips"]


def test_threat_model_scores_and_names_what_was_not_considered():
    from app.archdesk import master
    x = master.shape("threat", {**DESIGN, "threats": DESIGN["threats"] + [{"target": "X", "stride": "Q", "threat": "bad letter"}]})
    assert len(x["threats"]) == 2                                      # an unknown STRIDE letter is dropped, never guessed
    tm = master.threat_model(x["threats"], ["Orders API", "Payments"])
    assert tm["rows"][0]["risk"] == 9 and tm["open_high"] == 1
    assert "Repudiation" in tm["letters_unused"] and "Payments" in tm["uncovered"]
    assert tm["matrix"]["Orders API"]["S"] == 1


def test_growth_scenarios_and_what_breaks_first():
    from app.archdesk import master
    sc = master.scenarios({"dau": 1_000_000, "write_ratio": 0.3, "peak_factor": 4}, {"dau": "her"}, {"db_write_rps": 2000})
    assert [r["x"] for r in sc["rows"]] == [1, 10, 100]
    assert sc["rows"][1]["peak_rps"] == pytest.approx(10 * sc["rows"][0]["peak_rps"])
    whats = {b["what"]: b["at"] for b in sc["breaks"]}
    assert whats["Single database primary"] == "10x"                  # 1M x10 x20 req /86400 x4 x0.3 = 2,778 writes/s > 2,000
    assert "error" in master.scenarios({}, {})
    assert not any(b["what"] == "Single database primary" for b in master.scenarios({"dau": 10}, {})["breaks"])


def test_api_contract_checked_by_parsing_it():
    from app.archdesk import master
    ok = master.check_api(DESIGN["api"])
    assert ok["ok"] and ok["operations"] == 1
    assert master.check_api("```yaml\nopenapi: 3.0.0\npaths:\n  /a:\n    get: {}\n```")["missing_responses"] == ["GET /a"]
    assert not master.check_api("swagger: '2.0'")["ok"]
    assert not master.check_api("a: [unclosed")["ok"]
    assert master.check_api("")["skipped"]


# ------------------------------------------------------------------ the whole job, per kind
def test_kinds_and_repo_rule(M):
    with pytest.raises(M.s.ArchError):
        M.s.start("default", "", "Assess our shop backend for problems please", "", {}, "assess")
    with pytest.raises(M.s.ArchError):
        M.s.start("default", "", "Something big and complex to design here", "", {}, "astrology")


def test_assess_reads_the_repo_maps_it_peer_reviews_and_revises(M):
    v = M.s.start("default", "c1", "Assess our shop backend: what is wrong and what to fix first", "meghana/shop", {}, "assess")
    v = M.s.get("default", v["id"])
    assert v["status"] == "waiting_her" and v["kind"] == "assess"
    x = v["extra"]
    assert x["review"]["revised"] and x["review"]["issues"][0]["issue"] == "latency not measurable"
    assert v["design"]["nfrs"][0]["target"] == "p95 < 300 ms"           # the revision applied the peer's fix
    mm = v["repo_facts"]["module_map"]
    assert ["app/orders", "app/payments"] in mm["cycles"]
    assert any("<module_map>" in p and "app/payments" in p for p in M.calls["prompts"])
    assert any(d["kind"] == "as-is" for d in v["diagrams"])            # the map drawn from the code itself
    assert x["fitness_now"] and x["fitness_now"][0]["to"] == "app/riders"
    assert x["scorecard_result"]["average"] == 3.0 and x["scorecard_result"]["weakest"][0] == "Modularity"
    assert x["api_check"]["ok"] and v["api_yaml"]
    names = {c["check"]: c["ok"] for c in x["checks"]}
    assert names["Every quality target is measurable"] and names["Every problem has evidence from the repo"]
    assert names["Her code follows the design's boundary rules today"] is False
    h = M.pdfs["html"]
    for part in ("Assessment of the system as it is", "Growth scenarios", "Boundary rules", "API contract", "Peer review",
                 "Design checks"):
        assert part in h, part
    assert "Architecture assessment" in h and "peer-reviewed (1 issue(s), fixed)" in h
    md = v["markdown"]
    assert "## Assessment of the system as it is" in md and "## Peer review" in md and "## Design checks (code)" in md


def test_decide_and_threat_jobs_carry_their_sums_into_the_document(M):
    M.state["peer"] = {"verdict": "ready", "issues": []}
    v = M.s.get("default", M.s.start("default", "", "Postgres or Mongo for our orders, payments and stock?", "", {}, "decide")["id"])
    x = v["extra"]
    assert not x["review"]["revised"] and x["decision_result"]["winner"] == "PostgreSQL"
    assert "Winner (computed): PostgreSQL" in M.pdfs["html"] and "Technology decision" in M.pdfs["html"]
    assert sum(1 for s in M.calls["systems"] if s.startswith("You are a Principal Software Architect")) == 1   # no revision
    v2 = M.s.get("default", M.s.start("default", "", "Threat model our shop: phone app, API, payments", "", {}, "threat")["id"])
    assert v2["extra"]["threat_result"]["open_high"] == 1
    assert "Threat model (STRIDE)" in M.pdfs["html"] and "Not considered yet" in M.pdfs["html"]


def test_pr_review_adds_boundary_breaks_found_by_code(M):
    M.state["peer"] = {"verdict": "ready", "issues": []}
    pid = M.s.start("default", "", "Design our shop backend with clear module boundaries", "meghana/shop", {}, "design")["id"]
    M.s.approve("default", pid)
    r = M.s.review_pr("default", pid, 9)
    assert r["verdict"] == "drifts"                                    # the model said 'fits'; code found the break
    top = r["findings"][0]
    assert top["area"] == "boundary (checked by code)" and "app/orders now imports app/riders" in top["finding"]
    assert any("<boundary_breaks>" in p for p in M.calls["prompts"])
    assert not M.gh.reviews                                            # still a draft until her tap


def test_tool_and_route_take_the_kind(M):
    import asyncio

    from app.agent import arch_tools
    ctx = SimpleNamespace(tenant_id="default", conversation_id="c9", actor="owner")
    M.state["peer"] = {"verdict": "ready", "issues": []}
    out = asyncio.run(arch_tools.software_architect(ctx, action="new", kind="decide",
                                                    brief="Postgres or Mongo for our orders and payments?"))
    assert out["kind"] == "decide" and out["decision"]["winner"] == "PostgreSQL" and out["checks"].endswith("pass")
    props = arch_tools.ARCH_TOOLS[0]["input_schema"]["properties"]
    assert props["kind"]["enum"] == ["design", "assess", "migrate", "decide", "threat", "scale"]
    from fastapi.testclient import TestClient

    from app.main import app
    from app.config import get_settings
    c = TestClient(app)
    h = {"Authorization": f"Bearer {get_settings().api_key}"} if get_settings().api_key else {}
    j = c.get("/api/arch/projects", headers=h).json()
    assert j["kinds"]["threat"].startswith("Threat model") and "assess" in j["needs_repo"]
    r = c.post("/api/arch/projects", headers=h, json={"brief": "Scale our shop to 100x the users safely", "kind": "scale",
                                                     "scale": {"dau": 50000}})
    assert r.status_code == 200 and r.json()["kind"] == "scale"


def test_console_and_phone_show_the_master_sections():
    """The console desk and the phone desk both pick the kind and draw the master sections the server sends."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server" / "app" / "static" / "console" / "employees.js").read_text(encoding="utf-8")
    assert "{brief, repo, scale, kind}" in emp and "id=\"arKind\"" in emp and "needs_repo" in emp
    for key in ("decision_result", "threat_result", "scenarios", "x.checks", "x.review", "api_yaml", "kind_title",
                "letters_unused", "module_map", "fitness_now", "scale_plan", "migration", "assessment"):
        assert key in emp, key
    assert "return {hub, desk, social, cad, game, arch};" in emp
    css = (root / "server" / "app" / "static" / "console" / "v2.css").read_text(encoding="utf-8")
    assert ".ar-bars" in css and ".ar-checks" in css
    dart = (root / "lib" / "ui" / "arch_desk.dart").read_text(encoding="utf-8")
    assert "ChoiceChip(" in dart and "_kinds" in dart and "kind: _kind" in dart and "_needsRepo" in dart
    for key in ("'decision_result'", "'threat_result'", "'checks'", "'review'", "'scenarios'", "'api_yaml'", "'kind_title'"):
        assert key in dart, key
    api = (root / "lib" / "api.dart").read_text(encoding="utf-8")
    start = api[api.index("archStart("):api.index("archGet(")]
    assert "String kind = 'design'" in start and "'kind': kind" in start


def test_live_check_runs_master_kinds_and_reports_them(M):
    """`python -m app.archdesk check --kind decide,threat`: each kind runs like hers, as the check tenant, and the
    report shows the master parts (peer review, checks n/m, API, decision winner / threat counts)."""
    from app.archdesk import check as C
    M.state["peer"] = {"verdict": "ready", "issues": []}
    real = M.s._pdf

    def big_pdf(design, cap, drawn, vdir, facts, extra=None):
        real(design, cap, drawn, vdir, facts, extra)
        (vdir / "design.pdf").write_bytes(b"%PDF" + b"x" * 2000)
    import pytest as _p
    mp = _p.MonkeyPatch()
    mp.setattr(M.s, "_pdf", big_pdf)
    for kind in ("decide", "threat", "scale"):
        r = C._step_design(kind)
        assert r["ok"], r
        m = r["master"]
        assert m["kind"] == kind and m["checks"].endswith("pass") and m["api"].startswith("valid")
        assert m["peer_review"].startswith("0 issue(s)")
    assert C._step_design("decide")["master"]["decision"]["winner"] == "PostgreSQL"
    assert C._step_design("threat")["master"]["threats"]["open_high"] == 1
    from app.archdesk.models import ArchProject
    from app.db import session
    from sqlalchemy import select
    with session() as s:
        assert not s.scalars(select(ArchProject).where(ArchProject.tenant_id == C.TENANT)).all()
    mp.undo()
