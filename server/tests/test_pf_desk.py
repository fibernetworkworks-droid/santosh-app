"""PLATFORM ENGINEER DESK: the Platform Engineer's own section, built like the finance desks - its own chat (kind 'platform') with the
desk block and the platform tool in view; Terraform plans (JSON and text: data stores destroyed or replaced and why, open ports,
public databases, Action * on Resource *, protection off, tags, the destroy limit - counts pinned to a straight count); containers
rightsized (recommendations and savings pinned to arithmetic); clusters packed (a pod bigger than any node, losing a zone, the
GKE reserve rule pinned to its published figures); the Backstage catalog scored (owners, on-call, runbooks, broken references,
loops); manifests checked for removed Kubernetes APIs; the CI plan guard really fails on a destroyed database; walked in a browser."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

PLAN = {"format_version": "1.2", "terraform_version": "1.9.5", "resource_changes": [
    {"address": "aws_db_instance.main", "mode": "managed", "type": "aws_db_instance", "change": {"actions": ["delete", "create"], "before": {},
     "after": {"publicly_accessible": True, "storage_encrypted": False, "deletion_protection": False, "skip_final_snapshot": True, "tags": {"env": "prod"}}, "replace_paths": [["engine_version"]]}},
    {"address": "aws_security_group.web", "mode": "managed", "type": "aws_security_group", "change": {"actions": ["update"], "after": {
        "ingress": [{"from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"]}, {"from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}],
        "egress": [{"from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}], "tags": {"env": "prod", "team": "web"}}}},
    {"address": "aws_iam_policy.admin", "mode": "managed", "type": "aws_iam_policy", "change": {"actions": ["create"], "after": {
        "policy": json.dumps({"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}), "tags": {}}}},
    {"address": "aws_s3_bucket.logs", "mode": "managed", "type": "aws_s3_bucket", "change": {"actions": ["delete"], "before": {}, "after": None}},
    {"address": "aws_s3_bucket_policy.logs", "mode": "managed", "type": "aws_s3_bucket_policy", "change": {"actions": ["delete"], "before": {}, "after": None}},
    {"address": "aws_instance.app[0]", "mode": "managed", "type": "aws_instance", "change": {"actions": ["delete", "create"], "after": {"tags": {"env": "prod", "team": "a"}}, "replace_paths": [["ami"]]}},
    {"address": "aws_instance.app[1]", "mode": "managed", "type": "aws_instance", "change": {"actions": ["no-op"], "after": {}}},
    {"address": "data.aws_ami.x", "mode": "data", "type": "aws_ami", "change": {"actions": ["read"]}}]}
PLAN_TEXT = """Terraform will perform the following actions:

  # aws_db_instance.main must be replaced
-/+ resource "aws_db_instance" "main" {
      ~ engine_version = "14.7" -> "15.4" # forces replacement
    }

  # aws_instance.web will be created
  + resource "aws_instance" "web" {}

  # module.vpc.aws_subnet.a["x"] will be destroyed
  - resource "aws_subnet" "a" {}

Plan: 2 to add, 0 to change, 2 to destroy.
"""
RS = """namespace,workload,container,cpu_request,cpu_limit,mem_request,mem_limit,cpu_p95,mem_p95,replicas
shop,api,app,1,2,2Gi,2Gi,150m,1.9Gi,6
shop,worker,app,500m,500m,512Mi,1Gi,480m,800Mi,3
shop,cron,app,,,,,50m,100Mi,1
shop,web,nginx,2,,4Gi,8Gi,100m,300Mi,4"""
CLUSTER = """node m5.xlarge cpu=4 mem=16Gi pods=58 x3 zone=a
node m5.xlarge cpu=4 mem=16Gi pods=58 x3 zone=b
daemonset cpu=100m mem=200Mi
pod api cpu=500m mem=1Gi x20
pod worker cpu=1 mem=3Gi x6"""
CATALOG = """apiVersion: backstage.io/v1alpha1
kind: Group
metadata: {name: payments}
spec: {type: team, children: []}
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: checkout
  description: Takes orders
  annotations: {github.com/project-slug: acme/checkout, pagerduty.com/service-id: P123, backstage.io/techdocs-ref: dir:.}
  links: [{url: https://wiki/runbooks/checkout, title: Runbook}]
spec: {type: service, owner: payments, lifecycle: production, system: shop, dependsOn: [component:legacy-pay, resource:orders-db]}
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata: {name: legacy-pay}
spec: {type: service, owner: team-x, lifecycle: deprecated, dependsOn: [component:checkout]}
---
apiVersion: backstage.io/v1alpha1
kind: System
metadata: {name: shop, description: The shop}
spec: {owner: payments}
"""
MANIFESTS = """# Source: shop/templates/ingress.yaml
apiVersion: networking.k8s.io/v1beta1
kind: Ingress
metadata: {name: web, namespace: shop}
---
apiVersion: batch/v1beta1
kind: CronJob
metadata: {name: nightly}
---
apiVersion: autoscaling/v2beta2
kind: HorizontalPodAutoscaler
metadata: {name: api}
---
apiVersion: flowcontrol.apiserver.k8s.io/v1beta3
kind: FlowSchema
metadata: {name: fs}
---
apiVersion: v1
kind: List
items:
- apiVersion: policy/v1beta1
  kind: PodSecurityPolicy
  metadata: {name: restricted}
- apiVersion: apps/v1
  kind: Deployment
  metadata: {name: api}
"""


@pytest.fixture
def pfc(env):
    from app import pfchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "platform_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_terraform():
    from app.pfdesk import tfplan as TF
    r = TF.analyse(json.dumps(PLAN), max_destroy=1, required_tags="env,team")
    acts = [tuple(rc["change"]["actions"]) for rc in PLAN["resource_changes"] if rc["mode"] == "managed"]
    assert r["actions"] == {"create": acts.count(("create",)), "update": acts.count(("update",)), "delete": acts.count(("delete",)), "replace": acts.count(("delete", "create"))}
    assert r["lost"] == ["aws_db_instance.main", "aws_s3_bucket.logs"]   # the bucket policy is a setting, not data
    texts = " | ".join(i["text"] for i in r["issues"])
    assert "Replaced because of: engine_version" in texts and "port 22" in texts and "443" not in texts.split("port 22")[0][-40:]
    areas = {(i["area"], i["fn"]) for i in r["issues"]}
    assert {("Public", "aws_db_instance.main"), ("Permissions", "aws_iam_policy.admin"), ("Encryption", "aws_db_instance.main"), ("Protection", "aws_db_instance.main"),
            ("Tags", "aws_db_instance.main"), ("Tags", "aws_iam_policy.admin"), ("Replaced", "aws_instance.app[0]"), ("Destroys", "")} <= areas
    assert ("Tags", "aws_security_group.web") not in areas
    ok = TF.analyse(json.dumps({"resource_changes": [{"address": "aws_sg.x", "mode": "managed", "type": "aws_security_group",
                                                       "change": {"actions": ["create"], "after": {"ingress": [{"from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}]}}}]}))
    assert not ok["issues"] and ok["verdict"].startswith("1 to create")
    t = TF.analyse(PLAN_TEXT)
    assert t["actions"] == {"create": 1, "update": 0, "delete": 1, "replace": 1} and t["lost"] == ["aws_db_instance.main"] and t["changes"][0]["why"] == ["engine_version"]
    assert t["changes"][2]["type"] == "aws_subnet" and "JSON" in t["note"]
    assert TF.analyse("No changes. Your infrastructure matches the configuration.")["verdict"] == "No changes"
    for bad in ("", '{"x": 1}', "hello there"):
        with pytest.raises(TF.TfError):
            TF.analyse(bad)


def test_rightsize_and_capacity():
    from app.pfdesk import capacity as CP, rightsize as RS_
    r = RS_.analyse(RS, 0.2, 30, 4)
    by = {x["name"]: x for x in r["rows"]}
    api = by["shop/api/app"]
    assert abs(api["cpu_rec"] - 0.15 * 1.2) < 1e-12 and abs(api["save_cpu"] - (1 - 0.18) * 6) < 1e-9 and "near memory limit" in api["flags"]
    assert abs(api["mem_rec"] - 1.9 * 1.2) < 1e-12 and api["save_mem"] == 0   # it uses nearly all its memory
    web = by["shop/web/nginx"]
    assert abs(web["save_mem"] - (4 - 300 / 1024 * 1.2) * 4) < 1e-9 and "over-provisioned" in web["flags"]
    assert abs(r["save_money"] - (r["save_cpu"] * 30 + r["save_mem"] * 4)) < 1e-9
    assert abs(r["totals"]["cpu_req"] - (1 * 6 + 0.5 * 3 + 2 * 4)) < 1e-12 and abs(r["eff_cpu"] - (0.15 * 6 + 0.48 * 3 + 0.05 + 0.1 * 4) / 15.5) < 1e-12
    assert {"Out of memory", "Throttled", "Too tight", "Over-provisioned", "No requests", "No memory limit"} <= {i["area"] for i in r["issues"]}
    with pytest.raises(RS_.RightsizeError):
        RS_.analyse("workload,cpu_request\na,1")
    rc, rm = CP.reserved(4, 16, None, None)
    assert abs(rc - (0.06 + 0.01 + 0.005 * 2)) < 1e-12 and abs(rm - (0.25 * 4 + 0.2 * 4 + 0.1 * 8 + 100 / 1024)) < 1e-12
    c = CP.plan(CLUSTER)
    assert c["unplaced"] == 0 and c["node_count"] == 6 and c["pods"] == 26
    assert abs(c["req_cpu"] - (0.5 * 20 + 6 + 0.1 * 6)) < 1e-12 and abs(c["cap_cpu"] - 6 * (4 - rc)) < 1e-9
    loss = {l["what"]: l["left"] for l in c["loss"]}
    assert loss["one m5.xlarge (zone a) node"] == 0 and loss["zone a"] > 0
    assert any(i["area"] == "Losing capacity" and i["sev"] == "bad" for i in c["issues"])
    big = CP.plan(CLUSTER + "\npod big cpu=6 mem=8Gi")
    assert big["unplaced"] == 1 and "bigger than any node" in big["issues"][0]["text"]
    exact = CP.plan("node n cpu=4 mem=8Gi pods=10 x2\npod p cpu=1 mem=1Gi x8", reserve_cpu=0.0, reserve_mem=0.0)
    assert exact["unplaced"] == 0 and CP.plan("node n cpu=4 mem=8Gi pods=10 x2\npod p cpu=1 mem=1Gi x9", reserve_cpu=0.0, reserve_mem=0.0)["unplaced"] == 1
    assert CP.plan("node n cpu=64 mem=256Gi pods=3 x1\npod p cpu=100m mem=100Mi x4")["unplaced"] == 1   # pods per node count
    for bad in ("", "pod a cpu=1 mem=1Gi", "node n cpu=4 mem=8Gi", "hello"):
        with pytest.raises(CP.CapacityError):
            CP.plan(bad)


def test_catalog_upgrade_ci(tmp_path):
    from app.pfdesk import catalog as CA, ci as CI, upgrade as UP
    k = CA.analyse(CATALOG)
    by = {x["name"]: x for x in k["rows"]}
    assert by["checkout"]["score"] == 1 and set(by["legacy-pay"]["missing"]) == {"owner_known", "system", "description", "docs", "oncall", "repo", "runbook"}
    assert abs(by["legacy-pay"]["score"] - 2 / 9) < 1e-12 and abs(by["shop"]["score"] - 5 / 7) < 1e-12 and k["loop"] is not None
    areas = {i["area"] for i in k["issues"]}
    assert {"Broken references", "Unknown owner", "Deprecated dependency", "Dependency loop"} <= areas and k["broken"] == [["checkout", "dependsOn", "resource:orders-db"]]
    assert CA.analyse(CATALOG, "owner,oncall")["rows"][-1]["score"] == 1
    with pytest.raises(CA.CatalogError):
        CA.analyse(CATALOG, "owner,colour")
    u = UP.check(MANIFESTS, "1.24", "1.27")
    f = {x["name"]: x for x in u["found"]}
    assert f["shop/web"]["when"] == "already gone" and f["shop/web"]["to"] == "networking.k8s.io/v1"
    assert f["nightly"]["removed"] == "1.25" and f["nightly"]["when"] == "breaks at the target" and f["api"]["removed"] == "1.26" and f["api"]["when"] == "breaks at the target"
    assert f["restricted"]["removed"] == "1.25" and f["fs"]["when"] == "removed later" and u["objects"] == 6 and (u["gone"], u["breaks"], u["later"]) == (1, 3, 1)
    assert UP.check(MANIFESTS, "1.29", "1.29")["gone"] == 4 and UP.check(MANIFESTS)["later"] == 5
    for bad in (("", "", ""), (MANIFESTS, "1.30", "1.29"), (MANIFESTS, "", "2.0"), ("a: [", "", "")):
        with pytest.raises(UP.UpgradeError):
            UP.check(*bad)
    w = CI.workflow("infra/prod", max_destroy=1, protected="aws_route53_zone", var_file="prod.tfvars")
    y = yaml.safe_load(w["yaml"])
    assert y["permissions"]["contents"] == "read" and [s.get("name") for s in y["jobs"]["plan"]["steps"]][-4:] == ["Init", "Plan", "Plan as JSON", "Guard"]
    assert "-var-file=prod.tfvars" in w["yaml"] and "tofu" in CI.workflow(tofu=True)["yaml"]
    code = w["guard"].replace("\n          ", "\n").strip()
    def run(p):
        (tmp_path / "plan.json").write_text(json.dumps(p))
        return subprocess.run([sys.executable, "-I", "-c", code, str(tmp_path / "plan.json")], capture_output=True, text=True,
                              env={"PATH": os.environ.get("PATH", ""), "GITHUB_STEP_SUMMARY": str(tmp_path / "s.md")})
    one = {"resource_changes": [PLAN["resource_changes"][5]]}
    assert run(one).returncode == 0
    out = run(PLAN)
    assert out.returncode == 1 and "aws_db_instance.main would be replaced" in out.stdout and "over the limit of 1" in out.stdout
    assert "aws_s3_bucket_policy.logs would" not in out.stdout and "| aws_s3_bucket.logs | destroy | FAIL |" in (tmp_path / "s.md").read_text()
    zone = {"resource_changes": [{"address": "aws_route53_zone.main", "mode": "managed", "type": "aws_route53_zone", "change": {"actions": ["delete"]}}]}
    assert run(zone).returncode == 1
    for bad in (dict(tf_dir="../x"), dict(tf_version="1.9"), dict(max_destroy="x"), dict(protected="bad type!"), dict(var_file="/etc/x")):
        with pytest.raises(CI.CiError):
            CI.workflow(**bad)


def test_hire_chat_wiring_store_and_guards(pfc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert pfc.summary(T)["hired"] is False and "Hire me from AI Employees" in pfc.greeting(T)
    with pytest.raises(PermissionError):
        pfc.do(T, "add", {"kind": "tfplan", "text": PLAN_TEXT})
    _hire()
    d = pfc.summary(T)
    assert d["hired"] and d["foot"] == pfc.FOOT and {n["go"] for n in d["desk"]["needs"]} >= {"terraform", "settings"}
    chat = pfc.current(T)
    assert pfc.is_platform(chat["id"]) and pfc.owns(T, chat["id"]) and "<platform_desk>" in pfc.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_pfc.is_platform(conversation_id)" in s_ and "adm.admit_families(_pfc.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"platform"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/platform")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "pfdesk.js" in r.text
    html = (root / "server/app/static/console/pfdesk.html").read_text()
    for x in ("chatkit.js", "pfdesk.css", "pfdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/platform')" in (root / "server/app/static/console/v2.js").read_text()
    assert "platform_eng: 'pfdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["platform_eng"]["live"] is True
    from app.agent import admit
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["platform_desk"] in pfc.FAMILIES and "platform_desk" in HANDLERS and "platform" in admit.EXTRA_KEYS
    t1 = pfc.do(T, "add", {"kind": "tfplan", "text": json.dumps(PLAN), "inputs": {"max_destroy": 1}})
    assert t1["number"] == "T-0001" and t1["brief"]["lost"] == 2 and t1["brief"]["bad"] and t1["title"].startswith("Plan: ")
    json.dumps(t1)
    assert any(n["go"] == "terraform/" + t1["id"] for n in pfc.summary(T)["desk"]["needs"])
    r1 = pfc.do(T, "add", {"kind": "rightsize", "text": RS, "inputs": {"cpu_price": 30}})
    assert r1["number"] == "R-0001" and r1["brief"]["containers"] == 4 and r1["brief"]["save_money"] > 0
    c1 = pfc.do(T, "add", {"kind": "capacity", "text": CLUSTER})
    assert c1["number"] == "C-0001" and c1["brief"]["unplaced"] == 0
    s1 = pfc.do(T, "add", {"kind": "catalog", "text": CATALOG})
    assert s1["number"] == "S-0001" and s1["brief"]["scored"] == 3
    u1 = pfc.do(T, "add", {"kind": "upgrade", "text": MANIFESTS, "inputs": {"current": "1.24", "target": "1.27"}})
    assert u1["number"] == "U-0001" and u1["brief"]["breaks"] == 4
    assert pfc.do(T, "ci", {})["missing"] is True
    st = pfc.do(T, "settings", {"max_destroy": 2, "required_tags": "env", "k8s_current": "1.29", "k8s_target": "1.31", "tf_dir": "infra/prod", "tool": "tofu"})
    assert st["max_destroy"] == 2 and st["k8s_target"] == "1.31" and st["tool"] == "tofu"
    w = pfc.do(T, "ci", {})
    assert w["file"] == ".github/workflows/plan-guard.yml" and yaml.safe_load(w["yaml"]) and "tofu plan" in w["yaml"]
    pfc.forget(T)
    assert "1.29 -> 1.31" in pfc.block(T)
    u2 = pfc.do(T, "add", {"kind": "upgrade", "text": MANIFESTS})
    assert u2["result"]["target"] == "1.31" and u2["brief"]["breaks"] == 4 and u2["brief"]["later"] == 1
    mk = pfc.do(T, "mark", {"id": t1["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "terraform/" + t1["id"] for n in pfc.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import platform_tools as PT
    from app.agent.tools import Ctx
    out = asyncio.run(PT.platform_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="capacity", text=CLUSTER))
    assert out["number"] == "C-0002" and out["unplaced"] == 0
    out = asyncio.run(PT.platform_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/plan-guard.yml"
    with pytest.raises(PermissionError):
        pfc.do(T, "settings", {"protected": "my password is hunter2"})
    assert pfc.do(T, "add", {"kind": "tfplan", "text": PLAN_TEXT + "\n# password = hunter2"})["kind"] == "tfplan"
    for bad in ({"tool": "pulumi"}, {"k8s_target": "2.0"}, {"k8s_current": "1.32", "k8s_target": "1.30"}, {"catalog_checks": "owner,colour"}, {"tf_dir": "../x"}, {"headroom": 9}):
        with pytest.raises((pfc.PfDeskError, PermissionError)):
            pfc.do(T, "settings", bad)
    with pytest.raises(pfc.PfDeskError):
        pfc.do(T, "add", {"kind": "capacity", "text": ""})
    with pytest.raises(pfc.PfDeskError):
        pfc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "platform_eng")
    assert pfc.do(T, "get", {"id": t1["id"]})["id"] == t1["id"] and pfc.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        pfc.do(T, "add", {"kind": "capacity", "text": CLUSTER})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def pf_server(pfc, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(pfc, pf_server):
    base, browser, key = pf_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            tag = pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)
            tag.evaluate("el => el.remove()")

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    def put(pg, form, name, text):
        pg.eval_on_selector(f"form[data-form={form}] [name={name}]", "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); }", text)

    def submit(pg, form, text, sel):
        put(pg, form, "text", text)
        pg.click(f"form[data-form={form}] [type=submit]")
        pg.wait_for_selector(sel, timeout=60000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/platform")
    pg.wait_for_selector(".pfk-path", timeout=20000)
    snap(pg, "pf-today-empty-1440")
    go(pg, "#/terraform", "form[data-form=tfplan]")
    put(pg, "tfplan", "max_destroy", "1")
    put(pg, "tfplan", "required_tags", "env, team")
    submit(pg, "tfplan", json.dumps(PLAN, indent=1), "table.pfk-t")
    assert "aws_db_instance.main" in pg.inner_text("#pfPage") and "engine_version" in pg.inner_text("#pfPage") and pg.locator("table.pfk-t tr.bad").count() == 2
    snap(pg, "pf-terraform-1440")
    go(pg, "#/rightsizing", "form[data-form=rightsize]")
    put(pg, "rightsize", "cpu_price", "30")
    put(pg, "rightsize", "mem_price", "4")
    submit(pg, "rightsize", RS, "table.pfk-t")
    assert "near memory limit" in pg.inner_text("#pfPage") and "180m" in pg.inner_text("#pfPage")
    snap(pg, "pf-rightsizing-1440")
    go(pg, "#/capacity", "form[data-form=capacity]")
    submit(pg, "capacity", CLUSTER, ".pfk-nodes")
    assert pg.locator(".pfk-nodes>div").count() == 6 and "zone a" in pg.inner_text("#pfPage")
    snap(pg, "pf-capacity-1440")
    go(pg, "#/catalog", "form[data-form=catalog]")
    submit(pg, "catalog", CATALOG, "table.pfk-sc")
    assert "legacy-pay" in pg.inner_text("#pfPage") and pg.locator(".pfk-x").count() > 0
    snap(pg, "pf-catalog-1440")
    go(pg, "#/upgrades", "form[data-form=upgrade]")
    put(pg, "upgrade", "current", "1.24")
    put(pg, "upgrade", "target", "1.27")
    submit(pg, "upgrade", MANIFESTS, "table.pfk-t")
    assert "networking.k8s.io/v1" in pg.inner_text("#pfPage") and "Breaks at the target" in pg.inner_text("#pfPage")
    snap(pg, "pf-upgrades-1440")
    go(pg, "#/ci", "text=Set the Terraform folder")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=tf_dir]", "infra/prod")
    pg.fill("form[data-form=settings] [name=k8s_target]", "1.31")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=plan-guard.yml")
    snap(pg, "pf-ci-1440")
    go(pg, "#/today", ".pfk-list")
    assert "at risk" in pg.inner_text(".cs-hero")
    snap(pg, "pf-today-1440")
    for route, sel in (("#/today", ".pfk-list"), ("#/terraform", ".pfk-item"), ("#/rightsizing", ".pfk-item"), ("#/capacity", ".pfk-item"), ("#/catalog", ".pfk-item"),
                       ("#/upgrades", ".pfk-item"), ("#/ci", "text=plan-guard.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => !e.closest('pre,textarea,table,svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/terraform", "#/rightsizing", "#/capacity", "#/catalog", "#/upgrades"):
        go(pg, route, ".pfk-item")
        pg.locator(".pfk-item").first.click()
        pg.wait_for_selector(".pfk-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right) + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        snap(pg, "pf-" + route[2:] + "-390")
    assert not errs, errs
