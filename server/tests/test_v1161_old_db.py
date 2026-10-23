"""v0.116.1 An old database (made before later versions added NOT NULL columns) must upgrade itself.

Before: `_add_missing_columns` skipped NOT NULL columns, so e.g. hoola_links.trust (v0.112) never reached older VPS
databases and every Hoola Network screen answered 500."""
from fastapi.testclient import TestClient
from sqlalchemy import text

from tests.test_net import _connect


def test_old_database_gets_not_null_columns_and_network_screens_work(env):
    _connect()
    from app import db
    from app.net import deal as dl
    dl.set_stock("default", [{"name": "Parle-G", "unit": "carton", "price": 400, "gst_pct": 5, "qty": 20}])
    eng = db._engine
    dropped = [("hoola_links", "trust"), ("hoola_stock", "tiers"), ("hoola_stock", "public"), ("hoola_deal_rules", "a2a")]
    with eng.begin() as c:
        for t, col in dropped:
            c.execute(text(f'ALTER TABLE {t} DROP COLUMN "{col}"'))
    db._add_missing_columns(eng)
    from sqlalchemy import inspect
    insp = inspect(eng)
    for t, col in dropped:
        assert col in {c["name"] for c in insp.get_columns(t)}, (t, col)
    with eng.begin() as c:
        assert c.execute(text("SELECT trust FROM hoola_links")).scalars().all()[0] == ""
        assert c.execute(text("SELECT tiers, public FROM hoola_stock")).first() == ("[]", 1)
    from app import main
    with TestClient(main.app) as cl:
        for p in ("/api/net/me", "/api/net/connections", "/api/net/inbox", "/api/net/threads", "/api/net/groups",
                  "/api/net/deals", "/api/net/stock"):
            assert cl.get(p).status_code == 200, p
        assert cl.get("/api/net/stock").json()["stock"][0]["tiers"] == []
