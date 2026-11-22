"""v0.999.51 1PASSWORD SIGN-INS (owner: "1Password login (Grok Bot) ... LETS WORK ON IT FIRST"): her Hoola vault through a
read-only service account; a matching login is typed only on her tap, never seen by the model; the 2-step code
1Password computes fills the next box on that site; never bank / payment logins; the token never comes back."""
import asyncio
import json
import types

import pytest
from fastapi.testclient import TestClient

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0193_hoola_pc import FakePC, Scripted, _wire, tu
from tests.test_v0885_hoola_pc_pool import KIND, pool_hub  # noqa: F401

NS = types.SimpleNamespace


def _field(fid, ftype, value, code=None, title=""):
    det = NS(content=NS(code=code)) if code else None
    return NS(id=fid, field_type=NS(value=ftype), value=value, details=det, title=title or fid)


GST = NS(id="it1", title="GST portal", category=NS(value="Login"),
         websites=[NS(url="https://services.gst.gov.in/services/login")],
         fields=[_field("username", "Text", "meghana@gst"), _field("password", "Concealed", "Pa55-1P!"),
                 _field("totp", "Totp", "otpauth://...", code="314159")])
BANK = NS(id="it2", title="HDFC", category=NS(value="Login"), websites=[NS(url="https://netbanking.hdfcbank.com")],
          fields=[_field("username", "Text", "u"), _field("password", "Concealed", "p")])
CARD = NS(id="it3", title="Card", category=NS(value="CreditCard"), websites=[NS(url="https://services.gst.gov.in")],
          fields=[])


class FakeOP:
    def __init__(self, vaults=None):
        items = {i.id: i for i in (GST, BANK, CARD)}
        vs = vaults or [NS(id="v1", title="Hoola")]

        async def vlist(*a):
            return vs

        async def ilist(vid, *f):
            return list(items.values())

        async def iget(vid, iid):
            return items[iid]
        self.vaults = NS(list=vlist)
        self.items = NS(list=ilist, get=iget)


@pytest.fixture
def fake_op(monkeypatch):
    from app.pc import onepw
    onepw._CLIENTS.clear()
    seen = []

    async def auth(token):
        seen.append(token)
        if not token.startswith("ops_good"):
            raise onepw.OnePwError("1Password did not accept that token")
        return FakeOP()
    monkeypatch.setattr(onepw, "_client_for_token", auth)
    yield seen
    onepw._CLIENTS.clear()


@pytest.mark.asyncio
async def test_connect_find_open_and_never_money(bz, fake_op):  # noqa: F811
    from app.pc import onepw
    with pytest.raises(onepw.OnePwError):
        await onepw.connect("owner", "not-a-token")
    st = await onepw.connect("owner", "ops_good_123")
    assert st["connected"] and st["vault"] == "Hoola"
    row = onepw._row("owner")
    assert "ops_good" not in row.token_sealed                        # sealed, never stored plain
    hit = await onepw.find("owner", "gst.gov.in", "GST portal")
    assert hit == {"id": "it1", "title": "GST portal", "user": "m***@gst"}
    assert await onepw.find("owner", "hdfcbank.com", "HDFC net banking") is None   # money logins are never offered
    assert await onepw.open_("owner", "it1") == ("meghana@gst", "Pa55-1P!", "314159")
    with pytest.raises(onepw.OnePwError):
        await onepw.open_("owner", "it3")                             # a card item is never read
    assert onepw.disconnect("owner") and not onepw.status("owner")["connected"]


@pytest.mark.asyncio
async def test_several_vaults_means_she_picks_one(bz, fake_op, monkeypatch):  # noqa: F811
    from app.pc import onepw

    async def auth(token):
        return FakeOP([NS(id="v1", title="Hoola"), NS(id="v2", title="Personal")])
    monkeypatch.setattr(onepw, "_client_for_token", auth)
    st = await onepw.connect("owner", "ops_good_x")
    assert not st["connected"] and [v["name"] for v in st["vaults"]] == ["Hoola", "Personal"]
    st = await onepw.connect("owner", "", vault_id="v1")             # the token kept, now the vault chosen
    assert st["connected"] and st["vault"] == "Hoola" and "one vault only" in st["note"]


@pytest.mark.asyncio
async def test_a_task_signs_in_from_1password_on_her_tap_and_gets_the_code(pool_hub, bz, fake_op, monkeypatch):  # noqa: F811
    from app.pc import hands, onepw, operator, pool
    pool.HOME.clear()
    monkeypatch.setattr(pool, "_HOME_LOADED", True)
    await onepw.connect("owner", "ops_good_1")
    pc = FakePC(expect_kind=KIND)

    async def call(tenant, action, args=None, device_id=None, timeout=None, log=True, kind=None):
        if action == "page_text":
            return {"title": "GST", "url": "https://services.gst.gov.in/services/login", "text": ""}
        return await pc.call(tenant, action, args, device_id, timeout, log, kind)
    monkeypatch.setattr(pool_hub, "call", call)
    claude = Scripted([tu(1, "ask_login", site="GST portal"), tu(2, "ask_otp", reason="GST portal", digits=6),
                       tu(3, "done", answer="signed in")])
    _wire(monkeypatch, claude)
    r = await operator.start("owner", "c1", "GST portal par login karo", wait=0, kind=KIND)
    op = operator.get("owner", r["session_id"])
    for _ in range(200):
        if op.login:
            break
        await asyncio.sleep(0.02)
    lg = op.live()["login"]
    assert lg["onepw"] == {"title": "GST portal", "user": "m***@gst"}
    assert not [c for c in pc.calls if c[0] == "control"]           # nothing typed before her tap
    assert hands.give_login(op, lg["id"], "", "", use_onepw=True)
    await asyncio.wait_for(op.done_event.wait(), 15)
    typed = [c[1] for c in pc.calls if c[0] == "control"]
    assert typed == [{"op": "type", "text": "meghana@gst"}, {"op": "key", "keys": "Tab"},
                     {"op": "type", "text": "Pa55-1P!"}, {"op": "type", "text": "314159"}]
    seen = json.dumps([kw.get("messages") for kw in claude.seen], default=str)
    assert "Pa55" not in seen and "314159" not in seen and "meghana@gst" not in seen


def test_routes_never_return_the_token(env, fake_op):
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/computer/1password").json()["connected"] is False
    bad = c.post("/api/computer/1password", json={"token": "ops_bad"})
    assert bad.status_code == 400 and "ops_bad" not in bad.text
    ok = c.post("/api/computer/1password", json={"token": "ops_good_9"}).json()
    assert ok["connected"] and "ops_good" not in json.dumps(ok)
    assert "ops_good" not in c.get("/api/computer/1password").text
    from app.computer import OnePwIn
    assert "ops_" not in repr(OnePwIn(token="ops_secret"))
    assert c.delete("/api/computer/1password").json() == {"ok": True}


def test_requirement_and_version():
    from pathlib import Path
    req = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text()
    assert "onepassword-sdk" in req
    from app.main import APP_VERSION
    assert tuple(map(int, APP_VERSION.split("."))) >= (0, 999, 53)  # numbers, not text: "0.999.100" < "0.999.39" as text
