"""CLOUD ENGINEER DESK: the Cloud Engineer's own section, built like the finance desks - its own chat (kind 'cloudeng') with the desk
block and the cloud tool in view; the cloud bill read (FOCUS / CUR-style columns, a spike found and its service named, spend with
no owner tag, credits, mixed currencies refused, the month forecast pinned to its arithmetic); waste found in an inventory (Azure
stopped-not-deallocated, unattached disks, unused addresses, idle and old machines, money only from the table); commitments sized
(the best level pinned to a brute-force search and to the break-even rule); IAM / GCP / Azure policies read; networks checked
(overlaps, outside, too small, open admin ports, a subnet plan); keys refused; the CI access guard really fails; walked in a browser."""
from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from datetime import date, timedelta

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"


def _bill(days=20, spike_day=14, tags=True):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ChargePeriodStart", "ServiceName", "SubAccountName", "RegionName", "BilledCost", "BillingCurrency", "Tags"])
    for d in range(days):
        day = date(2026, 11, 1) + timedelta(d)
        for sv, base, tg in (("Amazon EC2", 100.0, {"team": "web"}), ("Amazon S3", 20.0, {}), ("Amazon RDS", 50.0, {"team": "data"})):
            c = base + (d % 3)          # a small steady wobble
            if sv == "Amazon EC2" and d == spike_day:
                c *= 3
            w.writerow([f"{day}T00:00:00Z", sv, "prod", "us-east-1", f"{c:.2f}", "USD", json.dumps(tg) if tags and tg else ""])
    w.writerow(["2026-11-03T00:00:00Z", "Credits", "prod", "", "-30.00", "USD", ""])
    return out.getvalue()


INVENTORY = """id,type,state,attached,cpu_p95,age_days,size_gb,instance_type,monthly_cost
vol-1,EBS volume,available,no,,40,100,gp2,8.00
vol-2,EBS volume,in-use,i-1,,40,100,gp3,8.00
eip-1,Elastic IP,,no,,10,,,3.65
i-1,EC2 instance,running,,2,200,,m4.large,70.08
i-2,EC2 instance,stopped,,,120,,t3.small,4.00
i-3,EC2 instance,running,,60,30,,m7g.large,60.00
vm-3,Azure virtual machine,Stopped,,,5,,Standard_D2s_v3,60.00
vm-4,Azure virtual machine,Stopped (deallocated),,,5,,Standard_D2s_v5,0
snap-1,snapshot,,,,400,50,,2.50
snap-2,snapshot,,,,20,50,,2.50"""


def _usage(days=14):
    return "time,usage\n" + "\n".join(f"{date(2026, 11, 1) + timedelta(h // 24)} {h % 24:02d}:00,{10 + (5 if 8 <= h % 24 < 20 else 0)}" for h in range(24 * days))


IAM_AWS = json.dumps({"Version": "2012-10-17", "Statement": [
    {"Sid": "Admin", "Effect": "Allow", "Action": "*", "Resource": "*"},
    {"Sid": "Deploy", "Effect": "Allow", "Action": ["s3:*", "iam:PassRole", "iam:CreatePolicyVersion"], "Resource": "*"},
    {"Sid": "Read", "Effect": "Allow", "Action": ["s3:GetObject"], "Resource": "arn:aws:s3:::b/*"},
    {"Sid": "Everything", "Effect": "Allow", "NotAction": ["iam:*"], "Resource": "*"},
    {"Sid": "Public", "Effect": "Allow", "Principal": "*", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::site/*"}]})
TRUST = json.dumps({"Statement": [{"Effect": "Allow", "Principal": {"Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"},
                                   "Action": "sts:AssumeRoleWithWebIdentity", "Condition": {"StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"}}}]})
GCP = json.dumps({"bindings": [{"role": "roles/storage.objectViewer", "members": ["allUsers"]}, {"role": "roles/owner", "members": ["user:a@acme.com", "user:b@gmail.com"]},
                               {"role": "roles/iam.serviceAccountTokenCreator", "members": ["group:dev@acme.com"]}, {"role": "roles/viewer", "members": ["group:all@acme.com"]}]})
AZURE = json.dumps([{"roleDefinitionName": "Owner", "scope": "/subscriptions/0000", "principalName": "ci-bot", "principalType": "ServicePrincipal"},
                    {"roleDefinitionName": "Reader", "scope": "/subscriptions/0000", "principalName": "ana"}])
NET = """vpc prod 10.0.0.0/16
vpc dev 10.0.128.0/17
vpc shared 10.10.0.0/16
subnet a 10.0.1.0/24 vpc=prod zone=a
subnet b 10.0.1.128/25 vpc=prod zone=b
subnet c 10.1.0.0/24 vpc=prod
subnet tiny 10.0.9.0/29 vpc=prod
subnet s1 10.10.0.0/24 vpc=shared
rule ssh in tcp 22 0.0.0.0/0
rule web in tcp 80,443 0.0.0.0/0
rule all in all all 0.0.0.0/0
rule app in tcp 8443 0.0.0.0/0
rule db in tcp 5432 10.0.0.0/16
plan 10.20.0.0/16 zones=3 tiers=public,private,data"""


@pytest.fixture
def clc(env):
    from app import clchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "cloud_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_bill():
    from app.cldesk import bill as B
    r = B.analyse(_bill(), "team", budget=5000)
    assert r["currency"] == "USD" and r["days"] == 20 and r["credits"] == -30.0
    # totals pinned to a straight sum
    gross = sum((100 + d % 3) * (3 if d == 14 else 1) + (20 + d % 3) + (50 + d % 3) for d in range(20))
    assert abs(r["gross"] - gross) < 0.01 and abs(r["total"] - (gross - 30)) < 0.01
    # the spike is found on its day and pinned on EC2
    sp = r["spikes"]
    assert [s["day"] for s in sp] == ["2026-11-15"] and sp[0]["service"] == "Amazon EC2"
    # owner tag: S3 lines have none
    s3 = sum(20 + d % 3 for d in range(20))
    assert abs(r["untagged"] - s3) < 0.01 and {x["name"] for x in r["by"]["owner"]} >= {"web", "data", "(untagged)"}
    # the month forecast = so far + the last 7 days' average x days left
    vals = [x["cost"] for x in r["series"]]
    exp = sum(vals) + sum(vals[-7:]) / 7 * 10
    assert r["month"]["days_left"] == 10 and abs(r["month"]["forecast"] - exp) < 0.01
    assert any(i["area"] == "Budget" for i in r["issues"]) and any(i["area"] == "Credits" for i in r["issues"])
    assert r["by"]["service"][0]["name"] == "Amazon EC2"
    with pytest.raises(B.BillError):
        B.analyse(_bill() + "2026-11-04T00:00:00Z,Amazon S3,prod,us-east-1,1.00,EUR,\n")
    with pytest.raises(B.BillError):
        B.analyse("date,service\n2026-11-01,x")
    # a plain CSV with its own column names, day-first dates, no tags column
    r2 = B.analyse("Date,Service description,Cost\n03/11/2026,Compute Engine,10\n04/11/2026,Compute Engine,12\n", currency="EUR")
    assert r2["currency"] == "EUR" and r2["first"] == "2026-11-03" and r2["total"] == 22


def test_waste_and_commit():
    from app.cldesk import commit as CM, waste as W
    r = W.analyse(INVENTORY, idle_cpu=5, keep_days=90, today="2026-11-28", currency="USD")
    why = {(f["id"], f["why"].split(" ")[0]) for f in r["found"]}
    ids = {f["id"] for f in r["found"]}
    assert {"vol-1", "eip-1", "i-1", "i-2", "vm-3", "snap-1"} <= ids and not ({"vol-2", "i-3", "vm-4", "snap-2"} & {f["id"] for f in r["found"] if "generation" not in f["why"] and f["why"] != "gp2 volume"})
    assert next(f for f in r["found"] if f["id"] == "vm-3")["sev"] == "bad"
    assert any(f["id"] == "i-1" and "older generation" in f["why"] for f in r["found"]) and any(f["id"] == "vol-1" and f["why"] == "gp2 volume" for f in r["found"])
    # money: only the deleted / released ones, from the table
    assert abs(r["save"] - (8.00 + 3.65 + 70.08 + 4.00 + 60.00 + 2.50)) < 0.001
    assert r["counts"]["bad"] == 1 and ("vm-3", "stopped") in why
    with pytest.raises(W.WasteError):
        W.analyse("state,cost\nrunning,1")
    # commitments: the best level pinned to a brute-force search, then to the break-even rule
    u = _usage()
    r = CM.plan(u, od_rate=0.1, commit_rate=0.06, current=12, unit="instances")
    us = [10 + (5 if 8 <= h % 24 < 20 else 0) for h in range(24 * 14)]
    brute = min(((c / 10) * 0.06 * len(us) + sum(max(0, x - c / 10) for x in us) * 0.1, c / 10) for c in range(0, 201))
    assert abs(r["best"]["commit"] - brute[1]) < 1e-9 and abs(r["best"]["cost"] - brute[0]) < 1e-6
    assert r["best"]["commit"] == 10 and abs(r["best"]["save"] - 134.4) < 1e-6 and abs(r["breakeven"] - 0.6) < 1e-12
    cur = r["current"]
    assert abs(cur["util"] - (10 * 12 + 12 * 12) / (12 * 24)) < 1e-9 and any(i["area"] == "Committed above the best level" for i in r["issues"])
    # a cheaper commitment (break-even 40%) makes the daytime peak worth committing: used 50% of the hours
    r = CM.plan(u, od_rate=0.1, commit_rate=0.04)
    assert r["best"]["commit"] == 15 and abs(r["best"]["save"] - (420 - 15 * 0.04 * 336)) < 1e-6
    # spend per hour with a discount
    r = CM.plan("hour,on_demand_spend\n" + "\n".join(f"2026-11-01 {h % 24:02d}:00,{2 + (h % 2)}" for h in range(24)), discount=0.3)
    assert r["money_usage"] and r["best"]["commit"] == 2
    with pytest.raises(CM.CommitError):
        CM.plan(u, od_rate=0.1, commit_rate=0.2)
    with pytest.raises(CM.CommitError):
        CM.plan("time,usage\n2026-11-01 00:00,1")


def test_iam_network_ci(tmp_path):
    from app.cldesk import ci as CI, iam as I, network as N
    r = I.analyse(IAM_AWS)
    areas = [i["area"] for i in r["issues"]]
    assert areas.count("Full admin") == 1 and "PassRole to any role" in areas and "Can raise its own access" in areas and "Allow with NotAction" in areas
    assert "Open to anyone" in areas and r["statements"] == 5 and not next(x for x in r["rows"] if x["where"].endswith("Read"))["flags"]
    assert any(i["area"] == "All actions" and "s3" in i["text"] for i in r["issues"])
    t = I.analyse(TRUST)
    assert t["counts"]["bad"] == 1 and "GitHub" in t["issues"][0]["area"]
    ok = json.loads(TRUST)
    ok["Statement"][0]["Condition"]["StringLike"] = {"token.actions.githubusercontent.com:sub": "repo:acme/app:ref:refs/heads/main"}
    assert I.analyse(json.dumps(ok))["counts"]["bad"] == 0
    g = I.analyse(GCP)
    ga = [i["area"] for i in g["issues"]]
    assert "Open to anyone" in ga and "Basic role" in ga and "Can act as service accounts" in ga and "Personal account" in ga and g["kinds"] == ["gcp"]
    z = I.analyse(AZURE)
    assert z["counts"]["warn"] == 1 and z["flagged"] == 1
    both = I.analyse("## deploy\n" + IAM_AWS + "\n## project\n" + GCP)
    assert both["kinds"] == ["aws", "gcp"] and any(x["where"].startswith("deploy") for x in both["rows"])
    with pytest.raises(I.IamError):
        I.analyse("{not json")
    n = N.analyse(NET)
    na = [i["area"] for i in n["issues"]]
    assert na.count("Networks overlap") == 1 and "Outside its network" in na and "Too small" in na and na.count("Subnets overlap") == 1
    assert na.count("Admin port open") == 1 and na.count("Everything open") == 1 and na.count("Open to the internet") == 1
    sub = {x["name"]: x for x in n["subnets"]}
    assert sub["a"]["usable"] == 251 and sub["s1"]["vpc"] == "shared" and not sub["s1"]["flags"]
    sp = next(x for x in n["space"] if x["vpc"] == "shared")
    assert sp["used"] == 256 and "10.10.1.0/24" in sp["free"]
    p = n["plans"][0]
    assert p["prefix"] == 21 and len(p["subnets"]) == 9 and p["spare_count"] == 32 - 9 and p["subnets"][0]["cidr"] == "10.20.0.0/21"
    import ipaddress
    nets = [ipaddress.ip_network(x["cidr"]) for x in p["subnets"]]
    assert all(not a.overlaps(b) for i, a in enumerate(nets) for b in nets[i + 1:])
    g2 = N.analyse(json.dumps({"SecurityGroups": [{"GroupName": "web", "IpPermissions": [{"IpProtocol": "tcp", "FromPort": 3389, "ToPort": 3389, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
                                                    "IpPermissionsEgress": [{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]}]}))
    assert [i["area"] for i in g2["issues"]] == ["Admin port open"]
    assert N.analyse(NET, provider="gcp")["subnets"][0]["usable"] == 252
    with pytest.raises(N.NetError):
        N.analyse("subnet x 10.0.0.1/24")
    # the CI guard really fails on a wide policy and passes a narrow one
    w = CI.workflow("iam/policies")
    y = yaml.safe_load(w["yaml"])
    assert w["file"] == ".github/workflows/access-guard.yml" and y.get("on", y.get(True))["pull_request"]["paths"] == ["iam/policies/**"] and y["permissions"] == {"contents": "read"}
    code = y["jobs"]["guard"]["steps"][1]["run"]
    (tmp_path / "iam/policies").mkdir(parents=True)
    (tmp_path / "g.py").write_text(code)
    (tmp_path / "iam/policies/read.json").write_text(json.dumps({"Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::b/*"}]}))
    run = lambda: subprocess.run([sys.executable, "g.py"], cwd=tmp_path, capture_output=True, text=True, env={**os.environ, "GITHUB_STEP_SUMMARY": str(tmp_path / "sum.md")})   # noqa: E731
    assert run().returncode == 0
    (tmp_path / "iam/policies/trust.json").write_text(TRUST)
    (tmp_path / "iam/policies/gcp.json").write_text(GCP)
    p_ = run()
    assert p_.returncode == 1 and "GitHub OIDC" in p_.stdout and "everyone" in p_.stdout and "roles/owner" in p_.stdout and "Access guard" in (tmp_path / "sum.md").read_text()
    for bad in ("../x", "/etc"):
        with pytest.raises(CI.CiError):
            CI.workflow(bad)


def test_hire_chat_wiring_store_and_guards(clc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert clc.summary(T)["hired"] is False and "Hire me from AI Employees" in clc.greeting(T)
    with pytest.raises(PermissionError):
        clc.do(T, "add", {"kind": "iam", "text": IAM_AWS})
    _hire()
    d = clc.summary(T)
    assert d["hired"] and d["foot"] == clc.FOOT and {n["go"] for n in d["desk"]["needs"]} >= {"bill", "settings"}
    chat = clc.current(T)
    assert clc.is_cloud(chat["id"]) and clc.owns(T, chat["id"]) and "<cloud_desk>" in clc.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_clc.is_cloud(conversation_id)" in s_ and "adm.admit_families(_clc.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"cloudeng"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/cloud")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "cldesk.js" in r.text
    html = (root / "server/app/static/console/cldesk.html").read_text()
    for x in ("chatkit.js", "cldesk.css", "cldesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/cloud')" in (root / "server/app/static/console/v2.js").read_text()
    assert "cloud_eng: 'cldesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["cloud_eng"]["live"] is True
    from app.agent import admit
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["cloud_desk"] in clc.FAMILIES and "cloud_desk" in HANDLERS and "cloudeng" in admit.EXTRA_KEYS
    b1 = clc.do(T, "add", {"kind": "bill", "text": _bill(), "inputs": {"tag_key": "team", "budget": 4000}})
    assert b1["number"] == "B-0001" and b1["brief"]["spikes"] == 1 and b1["brief"]["bad"] and b1["title"].startswith("Bill: ")
    json.dumps(b1)
    assert any(n["go"] == "bill/" + b1["id"] for n in clc.summary(T)["desk"]["needs"])
    w1 = clc.do(T, "add", {"kind": "waste", "text": INVENTORY, "inputs": {"today": "2026-11-28"}})
    assert w1["number"] == "W-0001" and w1["brief"]["save"] > 140
    c1 = clc.do(T, "add", {"kind": "commit", "text": _usage(), "inputs": {"od_rate": 0.1, "commit_rate": 0.06}})
    assert c1["number"] == "C-0001" and c1["brief"]["best"] == 10
    a1 = clc.do(T, "add", {"kind": "iam", "text": IAM_AWS})
    assert a1["number"] == "A-0001" and a1["brief"]["flagged"] == 4
    n1 = clc.do(T, "add", {"kind": "network", "text": NET})
    assert n1["number"] == "N-0001" and n1["brief"]["subnets"] == 5 and n1["brief"]["plans"] == 1
    assert clc.do(T, "ci", {})["missing"] is True
    st = clc.do(T, "settings", {"currency": "eur", "budget": 3000, "tag_key": "team", "policy_dir": "iam/policies", "provider": "gcp", "od_rate": 0.1, "commit_rate": 0.07})
    assert st["currency"] == "EUR" and st["provider"] == "gcp" and st["policy_dir"] == "iam/policies"
    w = clc.do(T, "ci", {})
    assert w["file"] == ".github/workflows/access-guard.yml" and yaml.safe_load(w["yaml"])
    clc.forget(T)
    assert "owner tag team" in clc.block(T) and "provider gcp" in clc.block(T)
    c2 = clc.do(T, "add", {"kind": "commit", "text": _usage()})
    assert c2["result"]["commit_rate"] == 0.07 and c2["brief"]["best"] == 10
    n2 = clc.do(T, "add", {"kind": "network", "text": NET})
    assert n2["result"]["provider"] == "gcp"
    mk = clc.do(T, "mark", {"id": b1["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "bill/" + b1["id"] for n in clc.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import cloudeng_tools as CT
    from app.agent.tools import Ctx, ToolError
    out = asyncio.run(CT.cloud_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="iam", text=GCP))
    assert out["number"] == "A-0002" and out["flagged"] >= 3
    out = asyncio.run(CT.cloud_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/access-guard.yml"
    # keys are never taken - in a field, in the pasted text, or through the tool
    with pytest.raises(PermissionError):
        clc.do(T, "settings", {"tag_key": "my password is hunter2"})
    with pytest.raises(PermissionError):
        clc.do(T, "add", {"kind": "waste", "text": INVENTORY + "\nkey,aws_secret_access_key = abc,,,,,,,"})
    with pytest.raises(PermissionError):
        clc.do(T, "add", {"kind": "iam", "text": '{"Statement": [], "k": "AKIAABCDEFGHIJKLMNOP"}'})
    with pytest.raises(ToolError):
        asyncio.run(CT.cloud_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="iam", text="-----BEGIN RSA PRIVATE KEY-----\nxx"))
    for bad in ({"provider": "oracle"}, {"currency": "euros"}, {"policy_dir": "../x"}, {"idle_cpu": 150}, {"od_rate": 0.05, "commit_rate": 0.06}, {"discount": 1.5}):
        with pytest.raises((clc.ClDeskError, PermissionError)):
            clc.do(T, "settings", bad)
    with pytest.raises(clc.ClDeskError):
        clc.do(T, "add", {"kind": "network", "text": ""})
    with pytest.raises(clc.ClDeskError):
        clc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "cloud_eng")
    assert clc.do(T, "get", {"id": b1["id"]})["id"] == b1["id"] and clc.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        clc.do(T, "add", {"kind": "network", "text": NET})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def cl_server(clc, monkeypatch):
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


def test_desk_in_a_real_browser(clc, cl_server):
    base, browser, key = cl_server
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
    pg.goto(base + "/console/cloud")
    pg.wait_for_selector(".clk-path", timeout=20000)
    snap(pg, "cl-today-empty-1440")
    go(pg, "#/bill", "form[data-form=bill]")
    put(pg, "bill", "tag_key", "team")
    put(pg, "bill", "budget", "4000")
    submit(pg, "bill", _bill(), "table.clk-t")
    t = pg.inner_text("#clPage")
    assert "Amazon EC2" in t and "2026-11-15" in t and "(untagged)" in t and pg.locator(".cm-line").count() == 1
    snap(pg, "cl-bill-1440")
    go(pg, "#/waste", "form[data-form=waste]")
    put(pg, "waste", "currency", "USD")
    submit(pg, "waste", INVENTORY, "table.clk-t")
    assert "not deallocated" in pg.inner_text("#clPage") and pg.locator("table.clk-t tr.bad").count() == 1
    snap(pg, "cl-waste-1440")
    go(pg, "#/commitments", "form[data-form=commit]")
    put(pg, "commit", "od_rate", "0.1")
    put(pg, "commit", "commit_rate", "0.06")
    put(pg, "commit", "current", "12")
    put(pg, "commit", "unit", "instances")
    submit(pg, "commit", _usage(), "table.clk-t")
    assert "134.4" in pg.inner_text("#clPage") and pg.locator(".clk-chart").count() == 1
    snap(pg, "cl-commitments-1440")
    go(pg, "#/access", "form[data-form=iam]")
    submit(pg, "iam", "## deploy\n" + IAM_AWS + "\n## project\n" + GCP, "table.clk-t")
    assert "PassRole to any role" in pg.inner_text("#clPage") and "allUsers" in pg.inner_text("#clPage")
    snap(pg, "cl-access-1440")
    go(pg, "#/network", "form[data-form=network]")
    submit(pg, "network", NET, "table.clk-t")
    assert "10.20.0.0/21" in pg.inner_text("#clPage") and "SSH 22" in pg.inner_text("#clPage")
    snap(pg, "cl-network-1440")
    go(pg, "#/ci", "text=Set the policy folder")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=policy_dir]", "iam/policies")
    pg.fill("form[data-form=settings] [name=currency]", "USD")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=access-guard.yml")
    snap(pg, "cl-ci-1440")
    go(pg, "#/today", ".clk-list")
    assert "USD" in pg.inner_text(".cs-hero")
    snap(pg, "cl-today-1440")
    for route, sel in (("#/today", ".clk-list"), ("#/bill", ".clk-item"), ("#/waste", ".clk-item"), ("#/commitments", ".clk-item"), ("#/access", ".clk-item"),
                       ("#/network", ".clk-item"), ("#/ci", "text=access-guard.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => !e.closest('pre,textarea,table,svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/bill", "#/waste", "#/commitments", "#/access", "#/network"):
        go(pg, route, ".clk-item")
        pg.locator(".clk-item").first.click()
        pg.wait_for_selector(".clk-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right) + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        snap(pg, "cl-" + route[2:] + "-390")
    assert not errs, errs
