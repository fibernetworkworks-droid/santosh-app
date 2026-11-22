"""ONE SHOP step 2 (gap 9 of docs/research/lovable/03_backend_vs_hoola.md, owner: "GO STEP 2"): every website order is a row
of the app's Orders list, and the two stay in step both ways - a staff move in the app moves the website order by the
website's own rules (a cancel returns stock / coupon / credit note there, once)."""
import json

import pytest

from tests.test_v0351_dukaan import _built_shop, _order
from tests.test_v099919_one_shop import _kaju, joined  # noqa: F401  (fixture)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.155"


def _web(sid, number):
    from app.db import session
    from app.site import shop as SH
    with session() as s:
        o = s.query(SH.SiteShopOrder).filter_by(site_id=sid, number=number).one()
        s.expunge(o)
    return o


def _fresh(p):
    from app.appmaker import service as AS
    return AS._load(p.id)                                   # the project as it is now (the Orders list was added)


def _row(row_id):
    from app.db import session
    from app.site import webapp as W
    with session() as s:
        x = s.get(W.SiteAppRow, row_id)
        return x.coll, x.owner, json.loads(x.data)


def test_a_website_order_is_a_row_of_the_apps_orders_list(joined):
    from app.appmaker import backend as BE
    S, sid, p = joined
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 2}])
    w = _web(sid, o["number"])
    assert w.app_row
    coll, owner, d = _row(w.app_row)
    assert coll == "orders" and owner == ""                 # a guest row: no app member owns it
    assert d["status"] == "New" and d["paid"] == "No" and d["pay"] == "UPI"
    assert d["total"] == 1840.0 and d["name"] == "Asha" and d["phone"] == "9876543210"
    assert "2 x Kaju Katli (1 kg) @ Rs 900" in d["items"] and f"Website order {o['number']}" in d["note"]
    lst = next(c for c in BE.schema(_fresh(p))["collections"] if c["key"] == "orders")
    assert lst["rules"] == BE.STAFF_RULES                   # a website member can never write an order row
    assert any(x["id"] == w.app_row for x in BE.owner_rows(_fresh(p), "orders"))   # her app's Orders list shows it


def test_website_moves_reach_the_row(joined):
    from app.site import shop as SH
    S, sid, p = joined
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])
    SH.tell_paid(sid, o["number"], o["token"], "UTR123456789")
    _, _, d = _row(_web(sid, o["number"]).app_row)
    assert d["paid"] == "Customer says paid" and d["utr"] == "UTR123456789" and d["status"] == "New"
    SH.set_status(sid, o["number"], "confirmed")
    _, _, d = _row(_web(sid, o["number"]).app_row)
    assert d["status"] == "Accepted" and d["paid"] == "Verified"


def test_a_staff_move_in_the_app_moves_the_website_order(joined):
    from app.appmaker import backend as BE
    S, sid, p = joined
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])
    rid = _web(sid, o["number"]).app_row
    BE.owner_update(_fresh(p), "orders", rid, {"status": "Out for delivery"})
    w = _web(sid, o["number"])
    assert w.status == "shipped"                            # along the website's own road: confirmed, packed, shipped
    hist = json.loads(w.history)
    assert [h["to"] for h in hist if "to" in h][-3:] == ["confirmed", "packed", "shipped"]
    assert all(h.get("by") == "app" for h in hist[-3:])
    assert _row(rid)[2]["status"] == "Out for delivery"


def test_a_cancel_in_the_app_is_a_website_cancel_once(joined):
    from app.appmaker import backend as BE
    from app.appmaker import stock as SK
    S, sid, p = joined
    k = _kaju(sid)
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 2}])  # 3 -> 1
    rid = _web(sid, o["number"]).app_row
    BE.owner_update(_fresh(p), "orders", rid, {"status": "Cancelled"})
    assert _web(sid, o["number"]).status == "cancelled"
    assert SK.table(p)[k["id"]]["qty"] == 3                 # the pieces came back by the website's own cancel
    BE.owner_update(_fresh(p), "orders", rid, {"status": "Cancelled"})
    assert SK.table(p)[k["id"]]["qty"] == 3                 # once


def test_a_move_the_website_cannot_make_puts_the_row_back(joined):
    from app.appmaker import backend as BE
    from app.site import shop as SH
    S, sid, p = joined
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])
    for to in ("confirmed", "shipped", "delivered"):
        SH.set_status(sid, o["number"], to)
    rid = _web(sid, o["number"]).app_row
    BE.owner_update(_fresh(p), "orders", rid, {"status": "Cancelled"})     # a delivered website order cannot be cancelled
    assert _web(sid, o["number"]).status == "delivered"
    assert _row(rid)[2]["status"] == "Delivered"            # the row shows what the order really is


def test_her_verified_in_the_app_confirms_a_waiting_upi_order(joined):
    from app.appmaker import backend as BE
    S, sid, p = joined
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])
    rid = _web(sid, o["number"]).app_row
    BE.owner_update(_fresh(p), "orders", rid, {"paid": "Verified"})
    assert _web(sid, o["number"]).status == "confirmed"
    assert _row(rid)[2]["status"] == "Accepted"


def test_a_site_with_no_app_gets_no_row(site_env):
    from app.site import service as S
    sid = _built_shop(S)
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])
    assert not _web(sid, o["number"]).app_row


def test_the_mirror_never_breaks_a_website_order(joined, monkeypatch):
    from app.site import shoporders as SO
    S, sid, p = joined
    monkeypatch.setattr(SO, "ensure_list", lambda p: (_ for _ in ()).throw(RuntimeError("schema locked")))
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])
    assert o["number"] and not _web(sid, o["number"]).app_row
