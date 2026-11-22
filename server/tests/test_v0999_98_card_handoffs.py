"""v0.999.100 the third browser exam (28 / 30, false done 0): both failures were the EXAM's - Hoola asked for the code with
ask_otp (the right tool) but the card only answered ask_user, and the copy task needs a sign-in that Hoola now rightly
hands to her private form. On its own practice portal the card now gives the practice code to the OTP box and fills the
private sign-in form the way she would (the model never sees what is typed); the login hand-off task still stops there."""
from __future__ import annotations

import asyncio
import re
import types

from app.quality import pccard as PC
from app.quality import pccard_browser as B
from tests.test_v0999_67_ultimate_p0 import _FakeOp, _FakeOperator, dirs  # noqa: F401


class _HandsOperator(_FakeOperator):
    def __init__(self):
        super().__init__()
        self.otps, self.logins = [], []

    async def start(self, tenant, conv, ask, **k):
        self.n += 1
        sid = f"pcop_{self.n}"
        op = _FakeOp(sid, "needs_confirm")             # keeps running (done_event not set)
        op.status, op.ask_text, op.otp, op.login = "running", ask, None, None
        if "/otp" in ask:
            op.otp = types.SimpleNamespace(id="otp1", status="pending")
        if "/login" in ask:
            op.login = {"id": "pclogin_1", "status": "pending"}
        self.OPS[sid] = op
        return {"session_id": sid}

    def _finish(self, op, task, data):
        from app import practice
        run = re.search(r"/practice/(r[0-9a-f]+)/", op.ask_text).group(1)
        practice.record(run, task, data)
        op.status = "done"
        op.done_event.set()

    def give_otp(self, tenant, rid, value):
        op = next(o for o in self.OPS.values() if o.otp and o.otp.id == rid)
        self.otps.append(value)
        op.otp.status = "approved"
        self._finish(op, "otp", {"phone": "+1 415 555 0100", "code": value})
        return True


def test_card_gives_the_otp_and_fills_the_private_sign_in(dirs, monkeypatch):  # noqa: F811
    fake = _HandsOperator()
    from app.pc import hands

    def give_login(op, rid, user, pw, **k):
        fake.logins.append((rid, user, bool(pw)))
        op.login = {"id": rid, "status": "approved"}
        fake._finish(op, "contact", {"name": "Ana Lopez", "message": "Order code QX-4417"})
        return True
    monkeypatch.setattr(hands, "give_login", give_login)
    monkeypatch.setenv("QUALITY_DIR", str(dirs / "q"))
    monkeypatch.setenv("PRACTICE_BASE_URL", "https://hoola.example")
    monkeypatch.setattr(PC, "_op_mod", lambda: fake)
    monkeypatch.setattr(PC, "_resolve", lambda t, p: {"device_id": "hp1", "name": "Hoola PC", "kind": "hoola_pc"})
    monkeypatch.setattr(PC, "_online", lambda t, d: True)
    monkeypatch.setattr(PC, "POLL_S", 0.01)
    card = asyncio.run(PC.run_card("t", "Hoola PC", ids=["otp_handoff", "copy_between_pages", "login_handoff"],
                                   set_name="browser", save_card=False))
    rows = {r["id"]: r for r in card["rows"]}
    assert rows["otp_handoff"]["ok"] and fake.otps == ["482913"]
    assert rows["copy_between_pages"]["ok"] and rows["copy_between_pages"]["signed_in"] == 1
    assert fake.logins == [("pclogin_1", "demo", True)]                    # once: the login hand-off task is NOT filled
    assert rows["login_handoff"]["ok"] and rows["login_handoff"]["status"] == "sign_in_handed"


def test_set_and_version():
    assert B.SET_V == 3
    t = {x["id"]: x for x in B.TASKS}
    assert t["otp_handoff"]["otp"] == "482913" and t["copy_between_pages"]["sign_in"] == ("demo", "practice-123")
    assert "sign_in" not in t["login_handoff"]
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.135"


def test_portal_exam_has_its_own_job_with_nothing_to_type():
    from pathlib import Path
    wf = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "- pc_card_portal" in wf and "JOB=pc_card; LINES_IN='portal@Hoola PC'" in wf
