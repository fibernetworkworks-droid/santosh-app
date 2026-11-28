"""SRE DESK, deeper (v0.999.317): on-call load (pages per person and 12-hour shift, broken nights in her time zone, an even share),
changes and their risk (the four DORA numbers, per service, by weekday, big changes), runbooks checked for what a paged person needs
(destructive commands with no warning, secrets masked, age, alerts with no runbook), toil and its payback, and a GitHub Actions
check for alert rules whose own script fails on exactly the rules the desk names; walked in a browser."""
from __future__ import annotations

import datetime as D
import os
import subprocess
import sys

import pytest
import yaml
from fastapi.testclient import TestClient

from tests.test_sr_desk import T, _hire, sr_server, src   # noqa: F401

PAGES = "time,who,alert,ack_at\n" + "\n".join([
    "2026-11-02T23:10:00Z,asha,DiskFull,2026-11-02T23:14:00Z", "2026-11-03T01:30:00Z,asha,HighErrorRate,2026-11-03T01:50:00Z",
    "2026-11-03T02:10:00Z,asha,HighErrorRate,2026-11-03T02:12:00Z", "2026-11-03T03:00:00Z,asha,Latency,2026-11-03T03:05:00Z",
    "2026-11-04T01:00:00Z,asha,DiskFull,", "2026-11-05T02:00:00Z,asha,DiskFull,", "2026-11-05T10:00:00Z,ben,Latency,2026-11-05T10:02:00Z",
    "2026-11-09T14:00:00Z,ben,HighErrorRate,2026-11-09T14:03:00Z"])


def deploys():
    rows = ["deployed_at,service,result,committed_at,restored_at,commits"]
    for i in range(24):
        t = D.datetime(2026, 11, 2, 10) + D.timedelta(hours=8 * i)
        f = i % 4 == 0
        rows.append(f"{t.isoformat()}Z,{'api' if i % 2 else 'web'},{'rolled back' if f else 'ok'},{(t - D.timedelta(hours=5)).isoformat()}Z,"
                    f"{(t + D.timedelta(minutes=40)).isoformat() + 'Z' if f else ''},{30 if f else 3}")
    return "\n".join(rows)


RUNBOOKS = """## runbooks/high-error-rate.md
# High error rate
## Summary
Errors.
## Diagnosis
```
kubectl logs deploy/api
```
## Mitigation
```
kubectl delete pod -l app=api
rm -rf /var/cache/api
```
password: hunter2xyz
Last reviewed: 2024-01-01
## runbooks/disk.md
# Disk full
## Overview
The disk is filling.
## Impact
Uploads fail.
## Investigate
https://grafana.example/d/disk
```
df -h
```
## Fix
> Warning: this cannot be undone
```
rm -rf /tmp/old
```
## Rollback
Nothing to undo.
## Escalation
team-sre
Last reviewed: 2026-10-01
"""
LINK_RULES = """groups:
- name: a
  rules:
  - alert: HighErrorRate
    expr: x
    annotations:
      runbook_url: https://wiki.example/runbooks/high-error-rate.md
  - alert: DiskFull
    expr: y
  - alert: Ghost
    expr: z
    annotations:
      runbook_url: https://wiki.example/ghost
"""
CI_RULES = """groups:
- name: api
  rules:
  - alert: HighErrorRate
    expr: sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m])) > 0.05
    for: 10m
    labels:
      severity: page
    annotations:
      summary: errors
      runbook_url: https://wiki.example/r/high
  - alert: HighErrorRate
    expr: sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m])) > 0.01
    for: 1h
    labels:
      severity: ticket
    annotations:
      summary: errors, slower
      runbook_url: https://wiki.example/r/high
  - alert: Restarts
    expr: kube_pod_container_status_restarts_total > 3
    annotations:
      summary: restarting
  - record: job:x:rate5m
    expr: sum(rate(x_total[5m]))
"""
TOIL = "task,minutes,per_week,automate_hours\nrestart stuck workers,20,10,8\nrotate certs by hand,60,1,6\nanswer access requests,10,30,40\n"


# ---------------------------------------------------------------- the engine (pure code)
def test_oncall_load():
    from app.sredesk import oncall as OC
    r = OC.load(PAGES, "UTC", 22, 7, 2)
    a, b = r["table"]
    assert (a["who"], a["pages"], b["who"], b["pages"]) == ("asha", 6, "ben", 2)
    assert a["vs_even"] == 1.5 and a["nights_in_a_row"] == 3            # nights of 2, 3 and 4 Nov: 01:00 on the 5th belongs to the 4th
    assert a["night_pages"] == 6 and b["night_pages"] == 0
    assert a["shifts_over"] == 1 and a["worst_shift"] == {"shift": "2026-11-03 am", "pages": 3}
    assert a["ack_median_min"] == 4.5 and r["ack_median_min"] == 3.5     # 4, 20, 2, 5 and 2, 3 minutes
    assert any("nights in a row" in x for x in a["advice"])
    assert r["night_pages"] == 6 and r["shifts_over"] == 1 and "6 at night" in r["verdict"]
    # the same pages in India (UTC+5:30): 23:10 and 01:00 UTC are 04:40 and 06:30 there - night; 01:30, 02:10, 02:00 and 03:00 UTC
    # are 07:00-08:30 - morning
    r2 = OC.load(PAGES, "Asia/Kolkata", 22, 7, 2)
    assert r2["table"][0]["night_pages"] == 2 and r2["table"][1]["night_pages"] == 0
    with pytest.raises(OC.OncallError):
        OC.load("time,alert\n2026-11-02T23:10:00Z,x\n2026-11-03T23:10:00Z,y")
    # a column called 'automate_hours' or 'ack_at' is never taken for the time
    assert OC._col(["automate_hours", "at"], "at") == 1 and OC._col(["automate_hours"], "at") is None


def test_changes_dora():
    from app.sredesk import changes as CH
    r = CH.dora(deploys(), "UTC")
    assert r["deploys"] == 24 and r["failed"] == 6 and r["cfr"] == 0.25
    assert r["lead"] == "5.0 h" and r["restore"] == "40 min"
    assert r["bands"] == {"frequency": "elite", "lead": "elite", "cfr": "high", "restore": "elite"}
    assert {s["service"] for s in r["services"]} == {"api", "web"}
    web = next(s for s in r["services"] if s["service"] == "web")
    assert web["failed"] == 6 and web["cfr"] == 0.5                     # every 4th deploy is a web deploy
    assert r["size"]["large_cfr"] == 1.0 and r["size"]["small_cfr"] == 0.0
    assert any("ship smaller" in i["text"] for i in r["issues"])
    assert "DORA 2021" in r["note"]
    # a column named "failed": yes means the change failed
    r2 = CH.dora("time,failed\n2026-11-01T10:00:00Z,yes\n2026-11-02T10:00:00Z,no\n2026-11-03T10:00:00Z,no\n2026-11-04T10:00:00Z,no")
    assert r2["failed"] == 1 and r2["cfr"] == 0.25
    with pytest.raises(CH.ChangeError):
        CH.dora("time,result\n2026-11-01T10:00:00Z,maybe\n2026-11-02T10:00:00Z,perhaps\n2026-11-03T10:00:00Z,ok")


def test_runbooks_and_toil():
    from app.sredesk import runbook as RB, toil as TL
    r = RB.check(RUNBOOKS, LINK_RULES, 180, D.date(2026, 11, 28))
    hi, disk = r["docs"]
    assert disk["score"] == 100 and not [i for i in disk["issues"] if i["sev"] in ("bad", "warn")]
    assert disk["dangers"][0]["warned"]                                  # rm -rf with a warning beside it is fine
    assert hi["missing"] == ["Impact", "How to undo", "Who to call"]
    t = " | ".join(i["text"] for i in hi["issues"])
    assert "kubectl delete with no namespace" in t and "rm -rf" in t and "hu••••••yz" in t and "hunter2xyz" not in str(r)
    assert "1062 days ago" in t
    st = {x["alert"]: x["state"] for x in r["links"]}
    assert st == {"HighErrorRate": "ok", "DiskFull": "none", "Ghost": "missing"}
    assert r["counts"]["bad"] >= 4
    one = RB.check("# Restart\n```\nsudo systemctl restart api\n```\n")
    assert one["runbooks"] == 1 and one["docs"][0]["missing"]
    with pytest.raises(RB.RunbookError):
        RB.check("  ")
    w = TL.toil(TOIL, 40, 50, 1)
    assert w["hours_week"] == 9.33 and w["share"] == 0.233
    assert [x["task"] for x in w["automate_first"]] == ["restart stuck workers", "rotate certs by hand", "answer access requests"]
    assert w["automate_first"][0]["payback_weeks"] == 2.4
    over = TL.toil(TOIL, 10, 50, 1)
    assert over["issues"][0]["sev"] == "bad"
    log = TL.toil("date,who,task,minutes\n2026-11-02,asha,restart,30\n2026-11-08,ben,access,60\n")
    assert log["shape"] == "log" and log["weeks"] == 1 and {p["who"] for p in log["by_who"]} == {"asha", "ben"}


def test_ci_workflow_runs_the_desks_rules(tmp_path):
    from app.sredesk import ci as CI
    w = CI.workflow("monitoring/**/*.yml", "bad", True, "2.53.0")
    y = yaml.safe_load(w["yaml"])
    on = y.get("on", y.get(True))
    assert on["pull_request"]["paths"][0] == "monitoring/**/*.yml" and y["permissions"] == {"contents": "read"}
    steps = y["jobs"]["rules"]["steps"]
    assert "v2.53.0/prometheus-2.53.0.linux-amd64.tar.gz" in steps[2]["run"]
    (tmp_path / "monitoring").mkdir()
    (tmp_path / "monitoring" / "api.yml").write_text(CI_RULES)
    (tmp_path / "check.py").write_text(steps[1]["run"])
    p = subprocess.run([sys.executable, "-I", "check.py"], cwd=tmp_path, capture_output=True, text=True,
                       env={"GITHUB_STEP_SUMMARY": str(tmp_path / "sum.md"), "PATH": os.environ.get("PATH", "")})
    assert p.returncode == 1, p.stdout + p.stderr
    errs = [ln for ln in p.stdout.splitlines() if ln.startswith("::error")]
    assert len(errs) == 2 and all("Restarts" in e for e in errs)          # no severity + a raw counter; the two HighErrorRate differ in severity
    assert "3 alert(s), 4 finding(s), 2 failing" in p.stdout and "Alert rules check" in (tmp_path / "sum.md").read_text()
    for bad in ("../x/*.yml", "a b"):
        with pytest.raises(CI.CiError):
            CI.workflow(bad)
    with pytest.raises(CI.CiError):
        CI.workflow(promtool_version="latest")
    assert CI.workflow()["promtool"] is None


def test_service_store_settings_and_chat(src):
    from app.sredesk import service as S
    from app import main
    _hire()
    with pytest.raises(S.SreError):
        S.save_settings(T, night_start=22, night_end=22)
    st = S.save_settings(T, shift_max=3, toil_cap=40, week_hours=37.5, rules_glob="alerts/*.yaml", ci_fail="warn", promtool_version="v2.53.0")
    assert (st["shift_max"], st["toil_cap"], st["ci_fail"], st["promtool_version"]) == (3, 40, "warn", "2.53.0")
    with pytest.raises(S.SreError):
        S.save_settings(T, rules_glob="../etc/*")
    a = S.add(T, "oncall", "", PAGES)
    assert a["number"] == "O-0001" and a["result"]["shift_max"] == 3 and a["result"]["shifts_over"] == 0
    c = S.add(T, "changes", "", deploys())
    assert c["number"] == "D-0001" and c["brief"]["cfr"] == 0.25
    k = S.add(T, "runbook", "", RUNBOOKS, {"rules": LINK_RULES})
    assert k["number"] == "K-0001" and k["brief"]["bad"]
    t = S.add(T, "toil", "", TOIL, {"people": 1})
    assert t["number"] == "T-0001" and t["result"]["cap"] == 0.4
    ci = S.ci_for(T)
    assert ci["fail_level"] == "warn" and "alerts/*.yaml" in ci["yaml"]
    v = src.today_view(T)
    assert v["changes"]["cfr"] == 0.25 and v["toil"]["share"] is not None and v["oncall"]["pages"] == 8
    assert any(n["go"].startswith("runbooks/") for n in v["needs"])
    out = src.do(T, "ci", {})
    assert out["file"] == ".github/workflows/alert-rules-check.yml"
    # the agent tool
    import asyncio
    from app.agent.sre_tools import SRE_TOOLS, sre_desk
    enum = SRE_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    assert {"oncall", "changes", "runbook", "toil", "ci"} <= set(enum)

    class Ctx:
        tenant_id = T
    r = asyncio.run(sre_desk(Ctx(), "toil", text=TOIL))
    assert r["tasks"][0]["task"] == "answer access requests" and r["share"] > 0
    with TestClient(main.app) as cl:
        assert cl.get("/console/sre").status_code == 200


def test_new_tabs_in_a_real_browser(src, sr_server):
    base, browser, key = sr_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/sre")
    pg.wait_for_selector(".srk-starts", timeout=20000)
    assert pg.locator("#sdTabs [role=tab], #sdTabs a, #sdTabs button").count() >= 10
    go(pg, "#/oncall", "form[data-form=oncall]")
    pg.fill("form[data-form=oncall] [name=text]", PAGES)
    pg.click("form[data-form=oncall] [type=submit]")
    pg.wait_for_selector("text=Person by person", timeout=30000)
    assert "asha" in pg.inner_text("#srPage") and "nights in a row" in pg.inner_text("#srPage")
    snap(pg, "sr-oncall-1440")
    go(pg, "#/changes", "form[data-form=changes]")
    pg.fill("form[data-form=changes] [name=text]", deploys())
    pg.click("form[data-form=changes] [type=submit]")
    pg.wait_for_selector("text=Against the DORA bands", timeout=30000)
    assert "25%" in pg.inner_text(".cs-hero") and "40 min" in pg.inner_text(".cs-hero")
    snap(pg, "sr-changes-1440")
    go(pg, "#/runbooks", "form[data-form=runbook]")
    pg.fill("form[data-form=runbook] [name=text]", RUNBOOKS)
    pg.fill("form[data-form=runbook] [name=rules]", LINK_RULES)
    pg.click("form[data-form=runbook] [type=submit]")
    pg.wait_for_selector("text=Runbook by runbook", timeout=30000)
    pg.click("details.srk-rule summary")
    assert "hunter2xyz" not in pg.inner_text("#srPage") and "Ghost" in pg.inner_text("#srPage")
    snap(pg, "sr-runbooks-1440")
    go(pg, "#/runbooks", "form[data-form=toil]")
    pg.fill("form[data-form=toil] [name=text]", TOIL)
    pg.click("form[data-form=toil] [type=submit]")
    pg.wait_for_selector("text=Automate first", timeout=30000)
    snap(pg, "sr-toil-1440")
    go(pg, "#/ci", "[data-ci]")
    pg.click("[data-ci]")
    pg.wait_for_selector("text=alert-rules-check.yml", timeout=20000)
    snap(pg, "sr-ci-1440")
    go(pg, "#/today", ".srk-list")
    assert "Change failure" in pg.inner_text(".cs-hero")
    snap(pg, "sr-today2-1440")
    for route, sel in (("#/oncall", ".srk-item"), ("#/changes", ".srk-item"), ("#/runbooks", ".srk-item"), ("#/ci", "[data-ci]"),
                       ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
    go(pg, "#/changes", ".srk-item")
    pg.click(".srk-item")
    pg.wait_for_selector("text=Against the DORA bands", timeout=20000)
    w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert w[0] <= w[1] + 1, w
    snap(pg, "sr-changes-390")
    assert not errs, errs
