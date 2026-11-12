"""v0.864 R4 (docs/HOOLA_APP_REDESIGN_PLAN.md): approval notifications carry Yes / Not now ONLY for confirm cards that
move no money; anything unsure gets no buttons and she opens the app (the route checks again on the tap)."""
from __future__ import annotations

from pathlib import Path

from app import push

ROOT = Path(__file__).resolve().parents[2]
OK = {"id": "ap1", "status": "pending", "money": False, "title": "Send the Diwali offer to 40 customers", "tier": 1}


def _ev(p):
    return {"kind": "bazar_approval", "id": 9, "at": "", "payload": p}


def test_quick_yes_only_for_no_money_pending_cards():
    assert push.quick_yes(OK)
    for bad in (
        {**OK, "money": True},
        {k: v for k, v in OK.items() if k != "money"},      # unsure = no buttons
        {**OK, "amount": "Rs 499"},
        {**OK, "pay_method": "UPI"},
        {**OK, "needs_pin": True},
        {**OK, "demo": True},
        {**OK, "tier": 3},
        {**OK, "status": "approved"},
        {**OK, "result": {"message": "done"}},
        {**OK, "id": ""},
    ):
        assert not push.quick_yes(bad), bad


def test_push_build_sets_yes_card():
    out = push.build("tok", _ev(OK))
    assert out["message"]["data"]["yes_card"] == "ap1"
    money = push.build("tok", _ev({**OK, "money": True, "amount": "Rs 499"}))
    assert "yes_card" not in money["message"]["data"]


def test_phone_side_is_wired():
    kt = (ROOT / "tool/android/kotlin/CardActionReceiver.kt").read_text()
    assert "/api/bazar/approvals/" in kt and "428" in kt
    notify = (ROOT / "tool/android/kotlin/Notify.kt").read_text()
    assert "setAuthenticationRequired(true)" in notify and "yesCard" in notify
    assert 'd["yes_card"]' in (ROOT / "tool/android/kotlin/SantoshPush.kt").read_text()
    assert ".CardActionReceiver" in (ROOT / "tool/AndroidManifest.xml").read_text()
    card = (ROOT / "lib/ui/chat/hoola_card.dart").read_text()
    assert "showApproveSheet" in card   # money still goes through the slide / fingerprint sheet
