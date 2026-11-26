"""v0.999.213 MAIL NEWS ONLY WHEN ASKED (owner, her Hoola updates screenshot: "WHY SHOWING LOT OF UNWANTED EMAIL
UPDATE -- WITHOUT USER ASK"): the watcher posted email_new cards for every connected Google mailbox in its default
mode (vip) - Google's own 'Security alert' for each Connect, company notices Gmail labels important, the same mail
in both mailboxes twice. Now: no cards until she picks a mode; her rules still run; Google's alert about her own
app connection is never announced; one card per mail across her mailboxes."""
import pytest

from app.agent.tools import Ctx
from app.config import get_settings
from app.db import MailSyncState, session
from app.mailbox import sync
from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_email import _raw, run  # noqa: F401
from tests.test_email_phase2 import WatchBox, _focus


@pytest.fixture
def quiet(bz, monkeypatch):  # noqa: F811
    import app.mailbox.accounts as ma
    monkeypatch.setenv("MAIL_WATCH_DEFAULT", "off")
    get_settings.cache_clear()
    b = WatchBox()
    _focus(bz["conv"])
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


def _google_alert(n):
    return _raw(("Google", "no-reply@accounts.google.com"), "meghana@fnw.in", "Security alert",
                f"Hoola was granted access to your Google Account meghana@fnw.in {n}")


def test_default_is_off_no_cards(quiet, bz):  # noqa: F811
    sync.sync_account("default", quiet)                       # calibrate
    quiet.add("601", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Quotation?", "bhej do"), important=True)
    quiet.add("602", _google_alert(1))
    quiet.add("603", _raw(("Workspace", "workspace-noreply@google.com"), "meghana@fnw.in",
                          "[Pricing Update] Changes to Google Workspace API usage limits", "new AI policies"),
              important=True)
    assert sync.sync_account("default", quiet) == 0
    assert _events(bz["conv"], "email_new") == []
    view = sync.watch_views("default")[0]
    assert view["mode"] == "off" and view["chosen"] is False


def test_her_notify_rule_still_tells_her(quiet, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    run("email_rule", {"action": "create", "name": "Bank", "match": {"from": "hdfcbank"}, "actions": {"notify": True}}, ctx)
    sync.sync_account("default", quiet)
    quiet.add("611", _raw(("HDFC", "alerts@hdfcbank.net"), "meghana@fnw.in", "Statement ready", "your statement"))
    quiet.add("612", _raw(("Anjan", "anjan@stranger.in"), "meghana@fnw.in", "Hello?", "kuch"))
    assert sync.sync_account("default", quiet) == 1
    assert [e["subject"] for e in _events(bz["conv"], "email_new")] == ["Statement ready"]


def test_turning_it_on_is_her_choice(quiet, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    run("email_accounts", {"watch_mode": "vip"}, ctx)
    view = sync.watch_views("default")[0]
    assert view["mode"] == "vip" and view["chosen"] is True
    sync.sync_account("default", quiet)
    quiet.add("621", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Rate pakka?", "please confirm"))
    quiet.add("622", _google_alert(2))                               # her own Hoola connection: never a card
    quiet.add("623", _raw(("Workspace", "workspace-noreply@google.com"), "meghana@fnw.in",
                          "[Pricing Update] Changes to API usage limits", "policies"), important=True)
    assert sync.sync_account("default", quiet) == 1
    assert [e["subject"] for e in _events(bz["conv"], "email_new")] == ["Rate pakka?"]


def test_same_mail_in_two_mailboxes_told_once(quiet, bz, monkeypatch):  # noqa: F811
    import app.mailbox.accounts as ma
    run("email_accounts", {"watch_mode": "all"}, Ctx("default", bz["conv"]))
    b2 = WatchBox("mbx_w2", "office@fnw.in")
    monkeypatch.setattr(ma, "boxes", lambda tenant: [quiet, b2] if tenant == "default" else [])
    run("email_accounts", {"watch_mode": "all"}, Ctx("default", bz["conv"]))
    sync.sync_account("default", quiet)
    sync.sync_account("default", b2)
    raw = _raw(("Swati", "swati@fnw.in"), "team@fnw.in", "Meeting kal?", "10 baje")
    quiet.add("631", raw)
    b2.add("931", raw)
    assert sync.sync_account("default", quiet) + sync.sync_account("default", b2) == 1
    assert len(_events(bz["conv"], "email_new")) == 1


def test_version_pin():
    from app.main import APP_VERSION
    assert tuple(int(x) for x in APP_VERSION.split(".")) >= (0, 999, 213)
