"""ONE SHOP step 1 (gap 9 of docs/research/lovable/03_backend_vs_hoola.md, owner: "Full merge, in steps"): her website shop
and her app share one product list and ONE stock count - the project's stock table. Before, each side counted its own
stock, so the last piece could be sold twice (once on the website, once in the phone app)."""
import json

import pytest

from tests.test_v0351_dukaan import _built_shop, _order
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.165"


def _kaju(sid):
    from app.site import shop as SH
    return next(p for p in SH.products(sid, active_only=False) if p["slug"] == "kaju-katli")


def _column(sid, slug):
    from app.db import session
    from app.site import shop as SH
    with session() as s:
        return s.query(SH.SiteShopProduct).filter_by(site_id=sid, slug=slug).one().stock


def test_a_site_with_no_app_keeps_its_own_count(site_env):
    from app.site import service as S
    from app.site import shopjoin as SJ
    sid = _built_shop(S)
    assert SJ.joined(sid) is None
    _order(S, sid, [{"slug": "kaju-katli", "qty": 2}])
    assert _kaju(sid)["stock"] == 1 and _column(sid, "kaju-katli") == 1           # the old path, unchanged


@pytest.fixture()
def joined(site_env):
    from app.site import applink as AL
    from app.site import service as S
    from app.site import shoppay as SP
    sid = _built_shop(S)                                    # Kaju Katli: 3 in stock, Motichoor Laddoo: not counted
    AL.link(T, sid)
    return S, sid, SP.project_of(sid)


def test_the_stock_moves_once_into_the_one_table(joined):
    from app.appmaker import service as AS
    from app.appmaker import stock as SK
    from app.site import shop as SH
    from app.site import shopjoin as SJ
    S, sid, p = joined
    k = _kaju(sid)                                          # the first read moves the count
    assert k["stock"] == 3 and k["in_stock"]
    assert SK.table(p)[k["id"]]["qty"] == 3
    assert sid in json.loads(AS._load(p.id).backend)["shop_stock"]
    assert SJ.move_stock(sid, p) == 0                       # once
    laddoo = next(x for x in SH.products(sid) if x["slug"] == "motichoor-laddoo")
    assert laddoo["stock"] is None and laddoo["in_stock"]   # not counted stays not counted


def test_website_and_app_take_from_the_same_count(joined):
    from app.appmaker import backend as BE
    from app.appmaker import stock as SK
    from app.site import shop as SH
    S, sid, p = joined
    k = _kaju(sid)
    prods = BE._products(p)                                 # her website's products are the app's products
    assert prods[k["id"]]["name"] == "Kaju Katli" and prods[k["id"]]["price"] == 900.0
    o = _order(S, sid, [{"slug": "kaju-katli", "qty": 2}])  # website: 3 -> 1
    assert SK.table(p)[k["id"]]["qty"] == 1
    assert _column(sid, "kaju-katli") == 3                  # the old column is not read or written any more
    SK.reserve(p, BE._cart_lines(p, [{"id": k["id"], "qty": 1}]))   # the phone app's order: 1 -> 0
    with pytest.raises(SH.ShopError) as e:                  # the last piece is gone for the website too
        _order(S, sid, [{"slug": "kaju-katli", "qty": 1}])
    assert e.value.code == 409 and "Kaju Katli" in str(e.value)
    assert SK.table(p)[k["id"]]["qty"] == 0                 # a refused checkout took nothing
    with pytest.raises(SK.StockError):
        SK.reserve(p, BE._cart_lines(p, [{"id": k["id"], "qty": 1}]))
    SH.set_status(sid, o["number"], "cancelled")            # a cancel puts its pieces back into the one count
    assert SK.table(p)[k["id"]]["qty"] == 2
    assert _kaju(sid)["stock"] == 2


def test_her_stock_edits_and_the_phone_app_see_one_number(joined):
    from app.appmaker import stock as SK
    from app.appmaker.android import service as AN
    from app.site import shop as SH
    S, sid, p = joined
    k = _kaju(sid)
    SH.upsert_products(sid, [{"title": "Kaju Katli", "stock": 7}])
    assert SK.table(p)[k["id"]]["qty"] == 7 and _kaju(sid)["stock"] == 7
    SH.upsert_products(sid, [{"title": "Kaju Katli", "stock": "unlimited"}])
    assert k["id"] not in SK.table(p) and _kaju(sid)["stock"] is None
    SH.upsert_products(sid, [{"title": "Kaju Katli", "stock": 5}, {"title": "Soan Papdi", "price": "250", "stock": 4}])
    key = json.loads(p.android or "{}").get("app_key") or ""
    if not key:
        pytest.skip("this project has no phone app key")
    AN._CACHE.pop(key, None)
    got = AN.content(key)
    shown = {x["name"]: x for x in got["lists"]["products"]}
    assert shown["Kaju Katli"]["stock"] == 5 and shown["Soan Papdi"]["stock"] == 4
    assert "products" not in got["demo_lists"]              # her real products replace the sample ones


def test_a_failed_checkout_gives_the_pieces_back(joined, monkeypatch):
    from app.appmaker import stock as SK
    from app.site import shop as SH
    S, sid, p = joined
    k = _kaju(sid)
    real = SH.SiteShopOrder

    class Boom(real):                                       # noqa: D401 - the order row cannot be written
        def __init__(self, *a, **kw):
            raise RuntimeError("disk full")
    monkeypatch.setattr(SH, "SiteShopOrder", Boom)
    with pytest.raises(RuntimeError):
        _order(S, sid, [{"slug": "kaju-katli", "qty": 2}])
    monkeypatch.setattr(SH, "SiteShopOrder", real)
    assert SK.table(p)[k["id"]]["qty"] == 3                 # nothing was lost
