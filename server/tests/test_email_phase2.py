"""v0.182.0 "Mail aayi!": the 60-second new-mail watcher (Gmail history.list watermark, expired-history fallback),
first-run silent calibration, watch modes (off / vip / all), inbox rules (label / archive / star / mark_read /
important / mute / notify; forward = a draft, never a send), the mute list, snooze add / wake / cancel,
and OTP digits that never leave the server unmasked."""
import email.utils
from datetime import timedelta as td

import pytest

from app import convs
from app.agent.tools import Ctx, ToolError
from app.db import MailContact, MailSnooze, MailSyncState, now, session
from app.mailbox import mime, sync
from app.mailbox.base import MailError
from app.mailbox.gmail import GmailBox, b64url
from tests.test_bazar import _events, _notices, bz  # noqa: F401
from tests.test_email import _raw, box, run  # noqa: F401


def _focus(conv):
    convs.mark("default", conv, "test")


def _raw_at(frm, to, subject, body, when, **kw):
    """A raw mail with a definite Date header (replaces the one build() set)."""
    import email
    m = email.message_from_bytes(_raw(frm, to, subject, body, **kw))
    del m["Date"]
    m["Date"] = email.utils.format_datetime(when)
    return m.as_bytes()


class WatchBox(GmailBox):
    """A GmailBox that speaks the watcher protocol from memory: profile(), history(), metadata, raw — no HTTP."""

    def __init__(self, key="mbx_w", address="meghana@fnw.in"):
        super().__init__(key, address, lambda force: "tok", "Meghana Ingle", "")
        self.store: dict[str, dict] = {}
        self.hist = 100
        self.added: list[tuple[int, str]] = []   # (history_id, mid) what history.list replays
        self.fail_history = False                # expired / purged historyId
        self.labels: set[str] = set()

    def add(self, mid, raw, unread=True, thread="", important=False):
        self.store[mid] = {"raw": raw, "unread": unread, "thread": thread or "t" + mid, "folder": "inbox",
                           "starred": False, "important": important}
        self.hist += 1
        self.added.append((self.hist, mid))

    # Gmail API surface the watcher touches
    def _req(self, method, path, **kw):
        p = path.split("?")[0]
        params = kw.get("params") or {}
        if isinstance(params, list):
            params = dict(params)
        if method == "GET" and p == "/profile":
            return {"historyId": str(self.hist), "emailAddress": self.address}
        if method == "GET" and p == "/history":
            if self.fail_history:
                raise MailError("Yeh email nahi mila (shayad hata di gayi).")   # a 404 purge looks like this
            start = int(params.get("startHistoryId") or 0)
            out = []
            for h, mid in self.added:
                if h <= start or self.store[mid]["folder"] != "inbox":
                    continue
                m = {"id": mid, "threadId": self.store[mid]["thread"], "historyId": str(h),
                     "labelIds": ["INBOX"] + (["UNREAD"] if self.store[mid]["unread"] else [])}
                out.append({"id": str(h), "messagesAdded": [{"message": m}]})
            return {"history": out, "historyId": str(self.hist)}
        if method == "GET" and p.startswith("/messages/"):
            mid = p.rsplit("/", 1)[-1]
            m = self.store[mid]
            if params.get("format") == "raw":
                return {"raw": b64url(m["raw"]), "id": mid, "threadId": m["thread"]}
            parsed = mime.parse(m["raw"])
            return {"id": mid, "threadId": m["thread"], "snippet": parsed["body"][:140],
                    "labelIds": ["INBOX"] + (["UNREAD"] if m["unread"] else [])
                    + (["IMPORTANT"] if m.get("important") else []),
                    "payload": {"mimeType": "multipart/mixed" if parsed["attachments"] else "text/plain",
                                "headers": [{"name": "From", "value": email.utils.formataddr((parsed["from"], parsed["from_email"]))},
                                            {"name": "To", "value": parsed["to"]},
                                            {"name": "Subject", "value": parsed["subject"]},
                                            {"name": "Date", "value": parsed["date"]},
                                            {"name": "Message-ID", "value": parsed["message_id"]}]}}
        raise MailError(f"WatchBox: unexpected {method} {p}")

    # organising, in memory
    def list(self, folder="inbox", unread_only=False, search=None, limit=10, since=None, snippets=False):
        cut = None
        if since:
            try:
                cut = since.timestamp() - 1        # like Gmail's after: (1s grace for header lag)
            except Exception:
                cut = None
        out = []
        for mid, m in reversed(list(self.store.items())):
            if m["folder"] != folder or (unread_only and not m["unread"]):
                continue
            parsed = mime.parse(m["raw"])
            if cut is not None:
                try:
                    if email.utils.parsedate_to_datetime(parsed["date"]).timestamp() < cut:
                        continue
                except Exception:
                    pass
            out.append({"id": mid, "thread_id": m["thread"], "from": parsed["from"], "from_email": parsed["from_email"],
                        "to": parsed["to"], "subject": parsed["subject"], "date": parsed["date"], "unread": m["unread"],
                        "starred": m["starred"], "snippet": parsed["body"][:200], "bulk": parsed["bulk"],
                        "has_attachments": bool(parsed["attachments"]), "message_id": parsed["message_id"],
                        "important": m["important"]})
        return out[:max(1, min(int(limit or 10), 50))]

    def archive(self, ids):
        for i in ids:
            self.store[i]["folder"] = "archive"

    def mark(self, ids, read):
        for i in ids:
            self.store[i]["unread"] = not read

    def star(self, ids, on):
        for i in ids:
            self.store[i]["starred"] = on

    def move(self, ids, folder):
        for i in ids:
            self.store[i]["folder"] = folder

    def apply_label(self, ids, name):
        self.labels.add(name)


@pytest.fixture
def wbox(bz, monkeypatch):  # noqa: F811
    import app.mailbox.accounts as ma
    b = WatchBox()
    _focus(bz["conv"])
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


def _state(account="mbx_w"):
    with session() as s:
        st = s.get(MailSyncState, ("default", account))
        s.expunge(st) if st else None
        return st


# ---------------- the watcher ----------------
def test_first_run_is_silent_calibration(wbox, bz):  # noqa: F811
    wbox.add("501", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Purana", "pehle se pada hai"))
    wbox.add("502", _raw(("Swati", "swati@fnw.in"), "meghana@fnw.in", "Yeh bhi", "purani"))
    assert sync.sync_account("default", wbox) == 0
    assert _events(bz["conv"], "email_new") == []                 # koi purani mail ka toofan nahi
    st = _state()
    assert st.history_id == str(wbox.hist) and st.last_ts is not None
    assert sync.sync_account("default", wbox) == 0                # quiet tick announces nothing again


def test_history_tick_announces_only_new_mail(wbox, bz):  # noqa: F811
    sync.sync_account("default", wbox)                            # calibrate
    wbox.add("511", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Quotation aayi?",
                         "bhej do jaldi"), important=True)
    wbox.add("512", _raw(("Swati", "swati@fnw.in"), "meghana@fnw.in", "Rate pakka?", "haan"))
    assert sync.sync_account("default", wbox) == 2
    evs = _events(bz["conv"], "email_new")
    assert [e["subject"] for e in evs] == ["Quotation aayi?", "Rate pakka?"]
    assert all(e["id"].startswith("mbx_w~") for e in evs)
    assert _state().history_id == str(wbox.hist)
    assert sync.sync_account("default", wbox) == 0                # watermark aage badh gaya: dobara nahi
    assert len(_events(bz["conv"], "email_new")) == 2


def test_expired_history_falls_back_to_listing(wbox, bz):  # noqa: F811
    sync.sync_account("default", wbox)                            # calibrate
    wbox.fail_history = True                                      # Gmail purged the history window
    wbox.add("521", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Naya zaroori mail",
                         "fallback se aaya, dekh lo?"))
    assert sync.sync_account("default", wbox) == 1
    evs = _events(bz["conv"], "email_new")
    assert len(evs) == 1 and evs[0]["subject"] == "Naya zaroori mail"
    assert _state().history_id == str(wbox.hist)                  # watermark healed from the profile
    assert _state().last_error == ""


def test_vip_mode_gates_strangers_but_not_known_or_otp(wbox, bz):  # noqa: F811
    with session() as s:
        s.add(MailContact(tenant_id="default", email="ramesh@vendor.in", name="Ramesh", sent_to=3, score=5))
    sync.sync_account("default", wbox)                            # calibrate
    wbox.add("531", _raw(("Anjan", "anjan@stranger.in"), "meghana@fnw.in", "Hello there", "koi baat nahi"))
    wbox.add("532", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Aapki yaad", "namaste"))
    wbox.add("533", _raw(("HDFC", "alerts@hdfcbank.net"), "meghana@fnw.in", "Your OTP for login",
                         "Your OTP is 482913. Do not share it."))
    assert sync.sync_account("default", wbox) == 2                # stranger shant, VIP + OTP boli
    evs = _events(bz["conv"], "email_new")
    assert [e["from_email"] for e in evs] == ["ramesh@vendor.in", "alerts@hdfcbank.net"]
    otp = evs[1]
    assert otp["otp"] is True and "482913" not in (otp["subject"] + otp["snippet"]) and "••••" in otp["snippet"]


def test_mode_off_and_all_with_bulk_digest(wbox, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("email_accounts", {"watch_mode": "off"}, ctx)
    assert out["changed"] == ["new-mail announcements: off"]
    wbox.add("541", _raw_at(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Kuch bhi", "off mode",
                            now() - td(minutes=10)))   # 10 minute purani: off ke dour aayi
    assert sync.sync_account("default", wbox) == 0
    assert _events(bz["conv"], "email_new") == []
    run("email_accounts", {"watch_mode": "all"}, ctx)
    wbox.add("542", _raw(("Anjan", "anjan@stranger.in"), "meghana@fnw.in", "Bhi bhej do", "sab dikhao"))
    wbox.add("543", _raw(("Amazon", "store-news@amazon.in"), "meghana@fnw.in", "Diwali sale",
                         "70% off", extra={"List-Unsubscribe": "<mailto:u@amazon.in>"}))
    assert sync.sync_account("default", wbox) == 1
    evs = _events(bz["conv"], "email_new")
    assert [e["subject"] for e in evs if not e.get("digest")] == ["Bhi bhej do"]
    digest = [e for e in evs if e.get("digest")]
    assert digest and digest[0]["count"] == 1 and "newsletter" in digest[0]["subject"]


def test_mute_list_silences_sender(wbox, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("email_accounts", {"mute": "spam@x.in , promo@x.in"}, ctx)
    assert out["changed"] == ["2 senders muted"]
    sync.sync_account("default", wbox)                            # calibrate
    wbox.add("551", _raw(("Spam", "spam@x.in"), "meghana@fnw.in", "Jitni bhi baar", "aaye, shant"))
    wbox.add("552", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Sirf yeh bolo",
                         "notification chahiye"))
    assert sync.sync_account("default", wbox) == 1
    evs = _events(bz["conv"], "email_new")
    assert len(evs) == 1 and evs[0]["from_email"] == "ramesh@vendor.in"
    out = run("email_accounts", {"mute": "clear"}, ctx)
    assert out["muted"] == []


def test_sync_tick_plumbing(wbox, bz, monkeypatch):  # noqa: F811
    with session() as s:
        s.add(MailSyncState(tenant_id="default", account="mbx_w"))    # watcher_tenants picks the tenant up
    assert sync.sync_tick() == 1
    assert _state().history_id == str(wbox.hist)
    assert _state().last_error == ""


# ---------------- rules ----------------
def test_rule_matching_matrix():
    rule = {"from": "hdfcbank", "subject": "otp,login"}
    assert sync.matches(rule, {"from_email": "alerts@hdfcbank.net", "subject": "Your OTP for login", "snippet": "x"})
    assert not sync.matches(rule, {"from_email": "a@b.in", "subject": "Your OTP for login", "snippet": ""})
    assert not sync.matches(rule, {"from_email": "alerts@hdfcbank.net", "subject": "Statement", "snippet": ""})
    assert sync.matches({"has_attachment": True}, {"has_attachments": True})
    assert not sync.matches({"has_attachment": True}, {"has_attachments": False})
    assert sync.matches({"bulk": True}, {"bulk": True})
    assert not sync.matches({"unread": True}, {"unread": False})
    assert sync.matches({"subject": "invoice"}, {"subject": "", "snippet": "invoice attached"})


def test_rule_tool_create_list_pause_delete(bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("email_rule", {"action": "create", "name": "Bank", "match": {"from": "hdfcbank"},
                             "actions": {"label": "Bills", "archive": True}}, ctx)
    assert out["name"] == "Bank" and out["match"]["from"] == "hdfcbank"
    rid = out["id"]
    with pytest.raises(ToolError, match="shart"):
        run("email_rule", {"action": "create", "name": "Khaali", "match": {}, "actions": {"archive": True}}, ctx)
    with pytest.raises(ToolError, match="kaam"):
        run("email_rule", {"action": "create", "name": "Bin kaam", "match": {"from": "x"}}, ctx)
    with pytest.raises(ToolError, match="saath"):
        run("email_rule", {"action": "create", "name": "Ulta", "match": {"from": "x"},
                           "actions": {"mute": True, "notify": True}}, ctx)
    out = run("email_rule", {"action": "pause", "rule_id": rid}, ctx)
    assert out["enabled"] is False and "roka" in out["note"]
    out = run("email_rule", {"action": "resume", "rule_id": rid}, ctx)
    assert out["enabled"] is True
    out = run("email_rule", {"action": "list"}, ctx)
    assert out["rules"] and out["rules"][0]["id"] == rid
    out = run("email_rule", {"action": "delete", "rule_id": rid}, ctx)
    assert out["deleted"] == rid
    assert run("email_rule", {"action": "list"}, ctx)["rules"] == []


def test_rule_test_dry_run(bz, box):  # noqa: F811
    out = run("email_rule", {"action": "create", "name": "Quotation", "match": {"subject": "quotation"},
                             "actions": {"star": True}}, Ctx("default", bz["conv"]))
    res = run("email_rule", {"action": "test", "rule_id": out["id"]}, Ctx("default", bz["conv"]))
    assert res["checked"] == 5
    assert [m["subject"] for m in res["matches"]] == ["Quotation for 10 routers"]
    assert box.msgs["101"]["starred"] is False                    # test ne kuch nahi badla


def test_rule_actions_fire_on_new_mail_quietly(wbox, bz):  # noqa: F811
    run("email_rule", {"action": "create", "name": "Bank", "match": {"from": "hdfcbank"},
                       "actions": {"label": "Bills", "archive": True, "mark_read": True}}, Ctx("default", bz["conv"]))
    sync.sync_account("default", wbox)                            # calibrate
    wbox.add("561", _raw(("HDFC Bank", "alerts@hdfcbank.net"), "meghana@fnw.in", "Statement October",
                         "amount payable 1540"))
    assert sync.sync_account("default", wbox) == 0                # rule chupchaap kaam karta hai
    assert _events(bz["conv"], "email_new") == []
    assert wbox.store["561"]["folder"] == "archive" and wbox.store["561"]["unread"] is False
    assert wbox.labels == {"Bills"}
    rules = run("email_rule", {"action": "list"}, Ctx("default", bz["conv"]))["rules"]
    assert rules[0]["hits"] == 1


def test_rule_notify_makes_a_card_and_forward_makes_draft_not_send(wbox, bz):  # noqa: F811
    run("email_rule", {"action": "create", "name": "Boss ko", "match": {"from": "swati@fnw.in"},
                       "actions": {"notify": True, "forward_to": "boss@fnw.in"}}, Ctx("default", bz["conv"]))
    sync.sync_account("default", wbox)                            # calibrate
    wbox.add("571", _raw(("Swati", "swati@fnw.in"), "meghana@fnw.in", "Aaj chhutti", "main nahi aa rahi"))
    assert sync.sync_account("default", wbox) == 1
    evs = _events(bz["conv"], "email_new")
    assert len(evs) == 1 and evs[0]["from_email"] == "swati@fnw.in"     # notify action: card aaya
    drafts = _events(bz["conv"], "email_draft")
    assert len(drafts) == 1 and drafts[0]["to"] == "boss@fnw.in" and drafts[0]["subject"].startswith("Fwd:")
    assert "Swati" in drafts[0]["body"] and "attachments nahi hain" in drafts[0]["body"]
    with session() as s:
        from app.db import EmailDraft
        d = s.get(EmailDraft, drafts[0]["id"])
        assert d.status == "pending" and d.kind == "forward"      # Bhejo ka intezaar — kabhi khud nahi bheja


def test_rule_mute_suppresses_card(wbox, bz):  # noqa: F811
    run("email_rule", {"action": "create", "name": "Chup", "match": {"subject": "newsletter"},
                       "actions": {"mute": True}}, Ctx("default", bz["conv"]))
    sync.sync_account("default", wbox)
    wbox.add("581", _raw(("Weekly", "news@weekly.in"), "meghana@fnw.in", "Newsletter #12", "bahut saara text"))
    assert sync.sync_account("default", wbox) == 0
    assert _events(bz["conv"], "email_new") == []


# ---------------- snooze ----------------
def test_snooze_add_wake_and_cancel(wbox, bz):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    sync.sync_account("default", wbox)                            # calibrate
    wbox.add("591", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Baad mein dekh lungi",
                         "abhi nahi, 1 ghante baad"))
    out = run("email_snooze", {"action": "add", "email_id": "mbx_w~591", "hours": 1}, ctx)
    assert "wapas aayegi" in out["note"] and wbox.store["591"]["folder"] == "archive"
    lst = run("email_snooze", {"action": "list"}, ctx)["snoozed"]
    assert len(lst) == 1 and lst[0]["subject"] == "Baad mein dekh lungi"
    sid = lst[0]["id"]
    with session() as s:                                          # raat ho gayi: wake time nikal gaya
        s.get(MailSnooze, sid).wake_at = now() - td(minutes=1)
    assert sync.snooze_tick() == 1
    assert wbox.store["591"]["folder"] == "inbox" and wbox.store["591"]["unread"] is True
    assert [e for e in _events(bz["conv"], "email_snooze") if e["status"] == "woken"]
    assert any("Snooze khatam" in n for n in _notices(bz["conv"]))
    wbox.add("592", _raw(("Swati", "swati@fnw.in"), "meghana@fnw.in", "Kal dekho", "cancel test"))
    out = run("email_snooze", {"action": "add", "email_id": "mbx_w~592", "hours": 3}, ctx)
    sid2 = out["id"]
    assert wbox.store["592"]["folder"] == "archive"
    out = run("email_snooze", {"action": "cancel", "snooze_id": sid2}, ctx)
    assert out["cancelled"] == sid2
    assert wbox.store["592"]["folder"] == "inbox" and wbox.store["592"]["unread"] is True
    with pytest.raises(ToolError, match="snooze nahi mila"):
        run("email_snooze", {"action": "cancel", "snooze_id": "snz_nahi"}, ctx)


def test_snooze_needs_a_time_and_min(wbox, bz):  # noqa: F811
    sync.sync_account("default", wbox)
    wbox.add("595", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Kab?", "time do"))
    with pytest.raises(ToolError, match="Kab wapas"):
        run("email_snooze", {"action": "add", "email_id": "mbx_w~595"}, Ctx("default", bz["conv"]))
    from app.mailbox.base import MailError as ME
    with pytest.raises(ME, match="5 minute"):
        sync.snooze_add("default", bz["conv"], "mbx_w~595", now() - td(minutes=2))


# ---------------- version ----------------
def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.278.0"
