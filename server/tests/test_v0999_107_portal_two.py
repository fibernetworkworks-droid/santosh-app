"""v0.999.108 second portal exam (11/15, 2 cloud blocks said): the World Bank showed a Cloudflare 'verify you are human'
box and Hoola asked her to click it - a right hand-off, counted apart now; SAM.gov (and irs.gov last time) went silent
for 6 minutes after the 2nd step: pc_trace now prints the server's own PC log lines of each failed job by time, which
say whether a model step, a screenshot or an action took the minutes."""
from __future__ import annotations

import asyncio
import json

from app.quality import pccard as PC
from tests.test_v0999_67_ultimate_p0 import _FakeOp, _FakeOperator, dirs  # noqa: F401


class _AskOp(_FakeOperator):
    async def start(self, tenant, conv, ask, **k):
        self.n += 1
        sid = f"pcop_{self.n}"
        op = _FakeOp(sid, "needs_confirm")
        op.status = "running"
        op.ask = {"id": "a1", "question": "Cloudflare 'Verify you are human' is showing - can you click it?"}
        self.OPS[sid] = op
        return {"session_id": sid}

    async def _pc(self, op, action, args=None, **k):
        return {"active_window": "", "windows": [], "title": "", "url": "", "text": "Just a moment... Performing security check"}


def test_a_human_check_handed_to_her_is_counted_apart(dirs, monkeypatch):  # noqa: F811
    fake = _AskOp()
    monkeypatch.setenv("QUALITY_DIR", str(dirs / "q"))
    monkeypatch.setattr(PC, "_op_mod", lambda: fake)
    monkeypatch.setattr(PC, "_resolve", lambda t, p: {"device_id": "hp1", "name": "Hoola PC", "kind": "hoola_pc"})
    monkeypatch.setattr(PC, "_online", lambda t, d: True)
    monkeypatch.setattr(PC, "POLL_S", 0.01)
    card = asyncio.run(PC.run_card("t", "Hoola PC", ids=["wb_gdp"], set_name="portal", save_card=False))
    r = card["rows"][0]
    assert not r["ok"] and r["human_check"] and "Verify you are human" in r["asked_q"]
    assert card["summary"]["human_check"] == 1


def test_trace_reader_shows_the_server_log_of_a_failed_job(tmp_path, monkeypatch):
    from app.quality import pctrace_read as R
    q, tr = tmp_path / "quality", tmp_path / "trace" / "t1" / "pcop_sam"
    q.mkdir(parents=True)
    tr.mkdir(parents=True)
    (q / "pccard-1.json").write_text(json.dumps({"exam": "portal", "rows": [
        {"id": "us_sam_search", "ok": False, "status": "timeout", "job": "pcop_sam"}]}))
    (tr / "meta.json").write_text(json.dumps({"job": "pcop_sam", "status": "cancelled", "started": 1795315000,
                                              "ended": 1795315360}))
    log = tmp_path / "err.log"
    log.write_text("2026-11-22 02:36:41,000 INFO santosh.pc: pc brain qwen27 q step 2 4.1s stop=tool_use\n"
                   "2026-11-22 02:36:45,000 INFO santosh.pc: pc step 3 screen 300.2s\n"
                   "2026-11-22 02:40:00,000 INFO santosh.x: something else\n"
                   "2026-11-22 05:00:00,000 INFO santosh.pc: pc act other click 1.0s\n")
    monkeypatch.setenv("PCTRACE_LOG", str(log))
    out = "\n".join(R.report(q / "pccard-1.json", tmp_path / "trace"))
    assert "server log while it ran" in out and "pc step 3 screen 300.2s" in out
    assert "something else" not in out and "pc act other" not in out
