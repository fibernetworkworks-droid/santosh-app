"""ONE SHOP step 3 (gap 9 of docs/research/lovable/03_backend_vs_hoola.md, owner: "GO STEP 3"): the orders a website took
before step 2 get their row in the app's Orders list once - oldest first, each with its own date and status - and
nothing is given back or taken again; the customer's private link keeps working."""
import json

from tests.test_v0351_dukaan import _built_shop, _order
from tests.test_v099920_shop_orders import _row, _web
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.144"


def _old_shop():
    """A shop that took three orders before it was joined to its app project."""
    from app.site import service as S
    from app.site import shop as SH
    sid = _built_shop(S)                                    # Kaju Katli 3 in stock
    a = _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])                 # stays new
    b = _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])
    SH.set_status(sid, b["number"], "cancelled")                           # its piece came back (old column)
    c = _order(S, sid, [{"slug": "motichoor-laddoo", "qty": 2}])
    for to in ("confirmed", "shipped", "delivered"):
        SH.set_status(sid, c["number"], to)
    for o in (a, b, c):
        assert not _web(sid, o["number"]).app_row          # before the join: no rows anywhere
    return S, sid, (a, b, c)


def test_old_orders_get_their_rows_once(site_env):
    from app.appmaker import stock as SK
    from app.site import applink as AL
    from app.site import shop as SH
    from app.site import shoporders as SO
    from app.site import shoppay as SP
    S, sid, (a, b, c) = _old_shop()
    AL.link(T, sid)
    p = SP.project_of(sid)
    kaju = next(x for x in SH.products(sid) if x["slug"] == "kaju-katli")   # the count moves: 3 - 1 = 2
    assert kaju["stock"] == 2
    assert SO.catch_up(sid) == 3
    want = {a["number"]: "New", b["number"]: "Cancelled", c["number"]: "Delivered"}
    for o in (a, b, c):
        w = _web(sid, o["number"])
        coll, owner, d = _row(w.app_row)
        assert coll == "orders" and owner == "" and d["status"] == want[o["number"]]
        from app.db import session
        from app.site import webapp as W
        with session() as s:
            got = s.get(W.SiteAppRow, w.app_row).created_at
        assert abs((got.replace(tzinfo=None) - w.created_at.replace(tzinfo=None)).total_seconds()) < 1   # its own date
    assert SK.table(p)[kaju["id"]]["qty"] == 2              # writing down a cancelled order gave nothing back again
    assert SO.catch_up(sid) == 0                            # once
    t = SH.track(sid, a["number"], a["token"])              # the customer's private link still works
    assert t["number"] == a["number"] and t["status"] == "new"


def test_the_worker_catches_up_joined_sites_and_waits_for_the_others(site_env):
    from app.site import applink as AL
    from app.site import shoporders as SO
    S, joined_sid, olds = _old_shop()
    _, alone_sid, _ = _old_shop()                           # this one never joins
    SO._UNJOINED.clear()
    AL.link(T, joined_sid)
    assert SO.catch_up_all() == 3
    assert alone_sid in SO._UNJOINED and joined_sid not in SO._UNJOINED
    assert SO.catch_up_all() == 0                           # nothing left; the lone site is not asked again for 10 minutes
    assert all(_web(joined_sid, o["number"]).app_row for o in olds)


def test_an_order_whose_row_cannot_be_written_is_left_alone_after_three_tries(site_env, monkeypatch):
    from app.site import applink as AL
    from app.site import shoporders as SO
    S, sid, olds = _old_shop()
    AL.link(T, sid)
    SO._FAILED.clear()
    monkeypatch.setattr(SO, "mirror", lambda site_id, oid: "")
    for _ in range(3):
        assert SO.catch_up(sid) == 0
    assert all(SO._FAILED[_web(sid, o["number"]).id] == 3 for o in olds)
    calls = []
    monkeypatch.setattr(SO, "mirror", lambda site_id, oid: calls.append(oid) or "")
    SO.catch_up(sid)
    assert calls == []                                      # not tried again in this process
    SO._FAILED.clear()


def test_a_caught_up_order_moves_from_the_app_like_a_new_one(site_env):
    from app.appmaker import backend as BE
    from app.appmaker import service as AS
    from app.site import applink as AL
    from app.site import shoporders as SO
    from app.site import shoppay as SP
    S, sid, (a, b, c) = _old_shop()
    AL.link(T, sid)
    SO.catch_up(sid)
    p = AS._load(SP.project_of(sid).id)
    BE.owner_update(p, "orders", _web(sid, a["number"]).app_row, {"status": "Packed"})
    w = _web(sid, a["number"])
    assert w.status == "packed" and [h["to"] for h in json.loads(w.history) if "to" in h][-2:] == ["confirmed", "packed"]
