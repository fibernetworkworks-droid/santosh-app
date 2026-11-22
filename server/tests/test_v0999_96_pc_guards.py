"""v0.999.97 the second browser exam on page engine 2 (28 / 30) - its two wrong 'done's fixed:
1. told 'sign in with the demo account shown on the page', Hoola TYPED the password: a password box is now refused by
   code on both PCs (server + Hoola PC agent 1.9.1); the private sign-in form (ask_login) is the way, and the exam counts
   it as the clean hand-off;
2. the 3-step wizard put the street into 'Full name': a ref whose element is hidden now (the step moved on) is never
   used - the model is told to list the page again."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_v0999_93_ultimate_p1 import _do, _Fake, chrome_page  # noqa: F401
from app.pc import operator as op_mod

ROOT = Path(__file__).resolve().parents[2]


def test_hoola_pc_refuses_a_password_box_and_a_hidden_ref(chrome_page):  # noqa: F811
    act, open_, ref, recs = chrome_page
    open_("login")
    els = act.do_page_elements()["elements"]
    pw = next(e["ref"] for e in els if e.get("type") == "password")
    with pytest.raises(Exception, match="PASSWORD box"):
        act.do_page_type(pw, "practice-123")
    r = act.do_page_fill_form([{"ref": ref("username"), "text": "demo"}, {"ref": pw, "text": "practice-123"}])
    assert r["filled"] == 1 and "PASSWORD box" in r["results"][1]["err"]
    act.do_page_click(ref("sign in"))
    assert "login" not in recs()
    open_("wizard")
    name = ref("full name")
    act.do_page_type(name, "Kwame Mensah")
    act.do_page_click(ref("next"))                     # step 1 is hidden now; the old ref must not be typed into
    with pytest.raises(Exception, match="gone"):
        act.do_page_type(name, "12 Harbour Road")


def test_the_server_refuses_too_on_both_pcs():
    f = _Fake({"title": "Login", "elements": [{"ref": 1, "role": "input", "name": "Username"},
                                              {"ref": 2, "role": "input", "name": "Password", "type": "password"}]})
    op = op_mod.Op(id="t1", tenant="ten1", conv="c1", task="x")
    import asyncio
    real = op_mod._pc

    async def patched(o, action, args=None, timeout=30, log=True):
        return await f(o, action, args, timeout, log)
    op_mod._pc = patched
    try:
        asyncio.run(op_mod._do(op, "page_elements", {}))
        assert op.pw_refs == {2}
        out = asyncio.run(op_mod._do(op, "page_type", {"ref": 2, "text": "practice-123"}))
        assert out.startswith("REFUSED: that is a PASSWORD box") and "ask_login" in out
        out = asyncio.run(op_mod._do(op, "page_fill_form", {"entries": [{"ref": 1, "text": "demo"}, {"ref": 2, "text": "x"}]}))
        assert out == op_mod.PW_REFUSED
        assert [c[0] for c in f.calls] == ["page_elements"]          # nothing was sent to the PC
    finally:
        op_mod._pc = real


def test_the_private_sign_in_form_is_the_clean_hand_off():
    from app.quality import pccard as PC
    from app.quality import pccard_browser as B
    t = next(x for x in B.TASKS if x["id"] == "login_handoff")
    assert PC.check(t["check"], {"server": {}, "since": 1, "status": "sign_in_handed", "answer": ""})[0]
    assert not PC.check(t["check"], {"server": {"login": {"ok": True, "_at": 5}}, "since": 1,
                                     "status": "done", "answer": "Signed in, the order code is QX-4417"})[0]
    src = (ROOT / "server" / "app" / "quality" / "pccard.py").read_text()
    assert '"sign_in_handed"' in src and 'lg.get("status") == "pending"' in src


def test_versions():
    src = (ROOT / "desktop-linux" / "agent.py").read_text()
    assert re.search(r'VERSION = "1\.9\.[1-9]"', src) and "PW_REFUSED" in src
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.157"
