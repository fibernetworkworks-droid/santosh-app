"""v0.999.104 the first PORTAL exam on Hoola PC (real sites, read-only): 9/15. From the step records: 3 sites refused the
cloud computer and Hoola said so plainly (UAE portal, ACRA bizfile 403, EPFO) - counted apart now as an honest hand-off
for her PC, never a pass; 2 were the exam's (its 'do not fill anything' forbade the asked search; a cookie banner question
stopped Companies House) - searching is allowed now and a cookie-consent question alone is answered on the portal set;
weak page checks made firmer (an IRS home page mentioning 'refund' passed)."""
from __future__ import annotations

import asyncio
import re

from app.quality import pccard as PC
from app.quality import pccard_portal as P
from tests.test_v0999_67_ultimate_p0 import _FakeOp, _FakeOperator, dirs  # noqa: F401


def test_portal_set_v1_allows_search_and_answers_cookies():
    assert P.SET_V == 1 and len(P.TASKS) == 15 and all(t["cookies"] and not t.get("approve") for t in P.TASKS)
    assert "searching the site is fine" in P.TASKS[0]["ask"] and "do not submit or pay" in P.TASKS[0]["ask"]
    irs = next(t for t in P.TASKS if t["id"] == "us_irs_refund")
    assert not PC.check(irs["check"], {"page": "IRS home - refunds, forms, payments"})[0]
    assert PC.check(irs["check"], {"page": "Where's My Refund? Check your refund status"})[0]


class _PortalOp(_FakeOperator):
    def __init__(self):
        super().__init__()
        self.decided = []

    async def start(self, tenant, conv, ask, **k):
        self.n += 1
        sid = f"pcop_{self.n}"
        if "bizfile" in ask:
            op = _FakeOp(sid, "partial", "bizfile.gov.sg is blocked for this cloud computer: 403 Request blocked")
        else:
            op = _FakeOp(sid, "needs_confirm")
            op.pending = {"id": f"p{self.n}", "what": ("Accept the cookie banner?" if "company-information" in ask
                                                       else "Submit the search form and pay the fee?")}
        self.OPS[sid] = op
        return {"session_id": sid}

    def decide(self, tenant, sid, pid, yes):
        op = self.OPS[sid]
        self.decided.append(op.pending["what"])
        op.pending, op.status, op.summary = None, "done", "TESCO PLC company number 00445790"
        op.done_event.set()
        return True

    async def _pc(self, op, action, args=None, **k):
        return {"active_window": "", "windows": [], "title": "", "url": "", "text": "403 ERROR The request could not be satisfied"}


def test_card_answers_only_cookie_questions_and_counts_honest_blocks(dirs, monkeypatch):  # noqa: F811
    fake = _PortalOp()
    monkeypatch.setenv("QUALITY_DIR", str(dirs / "q"))
    monkeypatch.setattr(PC, "_op_mod", lambda: fake)
    monkeypatch.setattr(PC, "_resolve", lambda t, p: {"device_id": "hp1", "name": "Hoola PC", "kind": "hoola_pc"})
    monkeypatch.setattr(PC, "_online", lambda t, d: True)
    monkeypatch.setattr(PC, "POLL_S", 0.01)
    card = asyncio.run(PC.run_card("t", "Hoola PC", ids=["uk_companies_tesco", "sg_bizfile", "us_sam_search"],
                                   set_name="portal", save_card=False))
    rows = {r["id"]: r for r in card["rows"]}
    assert rows["uk_companies_tesco"]["ok"] and fake.decided == ["Accept the cookie banner?"]
    assert rows["us_sam_search"]["status"] == "needs_confirm" and "pay the fee" in rows["us_sam_search"]["approval_asked"]
    assert rows["sg_bizfile"]["blocked_said"] and not rows["sg_bizfile"]["ok"]
    assert card["summary"]["blocked_said"] == 1
    assert "blocked by the site + said so: 1" in PC.lines(card)[0] if hasattr(PC, "lines") else True
