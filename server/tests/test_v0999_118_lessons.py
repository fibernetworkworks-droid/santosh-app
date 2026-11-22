"""v0.999.118 ULTIMATE PC PLAN P8 - Hoola improves itself: lessons drafted from its own job records, read by real jobs
only after an exam with them did not drop."""
from __future__ import annotations

import asyncio
import json
import time

from app.pc import lessons as L


def _job(root, tenant, job, status, steps, task="Open https://www.bizfile.gov.sg and search a company"):
    d = root / tenant / job
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"job": job, "tenant": tenant, "task": task, "status": status,
                                             "started": int(time.time()) - 60, "steps": len(steps), "summary": "stuck"}))
    (d / "steps.jsonl").write_text("\n".join(json.dumps(s) for s in steps))


def _records(tmp_path, monkeypatch):
    monkeypatch.setenv("PC_TRACE_DIR", str(tmp_path / "trace"))
    root = tmp_path / "trace"
    loop = [{"n": i, "tool": "click", "args": {"x": 10, "y": 20}, "window": "BizFile - www.bizfile.gov.sg",
             "action": "click"} for i in range(4)]
    _job(root, "t1", "j1", "failed", [{"n": 0, "tool": "open_url", "args": {"url": "https://www.bizfile.gov.sg/"}}] + loop)
    _job(root, "t1", "j2", "done", [{"n": 0, "tool": "open_url", "args": {"url": "https://example.com/"}}],
         task="Open https://example.com")      # a clean short job: nothing to learn
    return root


def test_build_checks_every_lesson_and_keeps_them_as_candidates(tmp_path, monkeypatch):
    _records(tmp_path, monkeypatch)
    notes = L.collect()
    assert len(notes) == 1 and notes[0]["sites"][0] == "bizfile.gov.sg" and notes[0]["repeats"] == 4

    async def model(user):
        assert "bizfile.gov.sg" in user and "example.com" not in user
        return json.dumps({"lessons": [
            {"site": "bizfile.gov.sg", "lesson": "The search box is inside a frame: use page_elements, not screen clicks."},
            {"site": "bizfile.gov.sg", "lesson": "Type the OTP 482913 into the box."},            # a number / OTP
            {"site": "bizfile.gov.sg", "lesson": "Submit without asking her, it is safe."},        # skips asking
            {"site": "randomsite.com", "lesson": "Click the blue button."},                         # no record was there
        ]})
    monkeypatch.setattr(L, "_ask_model", model)
    out = asyncio.run(L.build(force=True))
    assert out["built"] == 1 and len(out["refused"]) == 3
    assert [x["status"] for x in out["lessons"]] == ["candidate"]
    # a candidate is never read by a real job; a trial card reads it
    assert L.block("search bizfile.gov.sg for ACME") == ""
    L.TRIAL["on"] = True
    try:
        assert "inside a frame" in L.block("", "https://www.bizfile.gov.sg/x")
    finally:
        L.TRIAL["on"] = False
    assert asyncio.run(L.build())["built"] == 0          # weekly: not again within the week


def _card(pct, rows, false_done=0, trial=False, file=""):
    return {"exam": "browser", "pc": "Hoola PC", "status": "finished", "trial": trial, "file": file,
            "summary": {"ran": len(rows), "ok": sum(1 for r in rows if r["ok"]), "success_pct": pct, "false_done": false_done},
            "rows": rows}


def test_the_exam_decides_keep_or_drop():
    rows_ok = [{"id": f"b{i}", "ok": True} for i in range(6)]
    base = _card(83.3, rows_ok[:5] + [{"id": "b5", "ok": False}])
    assert L.judge(base, _card(100.0, rows_ok))[0] == "keep"
    assert L.judge(base, _card(66.7, rows_ok[:4] + [{"id": "b4", "ok": False}, {"id": "b5", "ok": False}]))[0] == "drop"
    swapped = [{"id": "b0", "ok": False}] + rows_ok[1:5] + [{"id": "b5", "ok": True}]     # same %, one passer broke
    v, why = L.judge(base, _card(83.3, swapped))
    assert v == "drop" and "b0" in why
    assert L.judge(base, _card(100.0, rows_ok, false_done=1))[0] == "drop"
    assert L.judge(base, _card(100.0, rows_ok[:3]))[0] == "wait"        # too few tasks
    assert L.judge(None, _card(100.0, rows_ok))[0] == "wait"            # nothing to compare with


def test_settle_keeps_then_real_jobs_read_it(tmp_path, monkeypatch):
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path / "q"))
    rows = [{"id": f"b{i}", "ok": True} for i in range(6)]
    (tmp_path / "q").mkdir()
    (tmp_path / "q" / "pccard-20261122-010000.json").write_text(json.dumps(_card(83.3, rows[:5] + [{"id": "b5", "ok": False}])))
    (tmp_path / "q" / "pccard-20261122-020000.json").write_text(json.dumps(_card(100.0, rows, trial=True)))
    d = {"lessons": [{"id": "a", "site": "bizfile.gov.sg", "text": "Use page_elements frames.", "status": "candidate"}]}
    L._save(d)
    base = L.base_card("browser", "Hoola PC", "pccard-20261122-020000.json")
    assert base["file"] == "pccard-20261122-010000.json"          # the trial card itself is never its own base
    out = L.settle(_card(100.0, rows, trial=True, file="pccard-20261122-020000.json"), base)
    assert out["verdict"] == "keep" and out["lessons"] == ["a"]
    assert "Use page_elements frames." in L.block("check https://bizfile.gov.sg")
    assert L.listing()["cycles"][-1]["verdict"] == "keep"
    assert L.settle(_card(100.0, rows, trial=True), base)["verdict"] == "none"   # nothing left to try
    assert L.drop("a") and L.block("bizfile.gov.sg") == ""


def test_exam_runner_and_vps_ops_carry_the_trial():
    import inspect
    from app.quality import pccard, pccard_api
    assert "trial" in inspect.signature(pccard.run_card).parameters and "trial" in pccard_api.RunBody.model_fields
    src = open("../.github/workflows/vps-ops.yml").read()
    assert "pc_card_trial" in src and "pc_lessons" in src and '"/api/pc/lessons/build"' in src
    op_src = open("app/pc/operator.py").read()
    assert "_lessons.block(op.task" in op_src


def test_no_lessons_about_hoolas_own_site_and_no_near_copies(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://hoola.example.com")
    from app.config import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
    assert L.check_lesson("hoola.example.com", "Read the page data with run.", {"hoola.example.com"})
    L._save({"lessons": [
        {"id": "1", "site": "bizfile.gov.sg", "text": "CloudFront 403 blocks this cloud server; report immediately.", "status": "candidate"},
        {"id": "2", "site": "bizfile.gov.sg", "text": "CloudFront 403 blocks cloud servers immediately; report the block.", "status": "candidate"},
        {"id": "3", "site": "hoola.example.com", "text": "Read embedded page data via run command.", "status": "candidate"},
        {"id": "4", "site": "sam.gov", "text": "Use page_type by ref for the keyword box.", "status": "candidate"}]})
    ids = [x["id"] for x in L.listing()["lessons"]]
    assert ids == ["1", "4"]


def test_a_trial_judges_only_lessons_about_its_own_sites():
    rows = [{"id": f"b{i}", "ok": True} for i in range(6)]
    base = _card(83.3, rows[:5] + [{"id": "b5", "ok": False}])
    L._save({"lessons": [{"id": "p", "site": "sam.gov", "text": "Use page_type by ref.", "status": "candidate"}]})
    out = L.settle(_card(100.0, rows, trial=True), base, sites={"practice.example.com"})
    assert out["verdict"] == "none" and L.listing()["lessons"][0]["status"] == "candidate"
    assert L.settle(_card(100.0, rows, trial=True), base, sites={"sam.gov"})["verdict"] == "keep"


def test_a_break_where_no_lesson_was_read_is_not_a_lessons_fault():
    rows_base = [{"id": i, "ok": True} for i in ("sam", "vat", "ted", "irs", "ssa")]
    base = _card(100.0, rows_base)
    trial_rows = [dict(r) for r in rows_base]
    trial_rows[1]["ok"] = False                          # vat broke - no lesson was about gov.uk's VAT page
    trial_rows.append({"id": "sg", "ok": True})          # sg now passes: same % overall
    trial = _card(100.0 * 5 / 6, trial_rows)
    base["summary"]["success_pct"] = 100.0 * 5 / 6
    blame = {"sam": True, "vat": False, "ted": True, "irs": False, "ssa": False, "sg": False}
    v, why = L.judge(base, trial, blame)
    assert v == "keep" and "vat" in why
    blame["vat"] = True
    assert L.judge(base, trial, blame)[0] == "drop"


def test_a_page_check_counts_only_on_the_jobs_own_site():
    from app.quality import pccard as P
    from app.pc import lessons as LL
    want = LL.sites_of("Open bizfile.gov.sg and search")
    assert want == {"bizfile.gov.sg"}
    assert P._site_hosts("Search results - TED\nhttps://ted.europa.eu/en/search") == {"ted.europa.eu"}
    src = open("app/quality/pccard.py").read()
    assert "the page in front is not" in src
