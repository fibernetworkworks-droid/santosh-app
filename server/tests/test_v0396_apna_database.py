"""v0.396 APNA DATABASE: an app's data runs in HER own PostgreSQL-wire database (Supabase, Neon, RDS ...).
A local Postgres plays her Supabase: link (her tap, backup first, tables, copy, counts), PRIMARY write-through (an app
write lands there inside the request; her database unreachable = the write is refused, nothing half-saved), her edits
OUTSIDE Hoola (update / insert / delete in her table) flow back into the app with the app's logic run and values checked,
field-level merges, a new field = a new column there, MIRROR mode catching up from the journal, unlink keeps the data."""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

PGA = os.environ.get("HOOLA_PG_ADMIN", "")
pytestmark = pytest.mark.skipif(not PGA, reason="HOOLA_PG_ADMIN not set (a Postgres server plays her Supabase)")


def _her_db():
    import psycopg
    from sqlalchemy.engine import make_url
    u = make_url(PGA)
    q = dict(u.query)
    host = u.host or "127.0.0.1"
    port = int(u.port or q.get("port") or 5432)
    name = "her_supabase_" + uuid.uuid4().hex[:8]
    with psycopg.connect(dbname="postgres", user=u.username or "postgres", password=u.password, host=host, port=port,
                         autocommit=True) as c:
        c.execute(f'CREATE DATABASE "{name}"')
    pw = f":{u.password}" if u.password else ""
    return f"postgresql://{u.username or 'postgres'}{pw}@{host}:{port}/{name}?sslmode=disable", name


def _her(dsn):
    import psycopg
    return psycopg.connect(dsn, autocommit=True)


def _setup(droid_env, monkeypatch, mode="primary"):
    monkeypatch.setenv("PGDB_ALLOW_PRIVATE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    c.post(f"{api}/signup", json={"email": "asha@example.com", "password": "pass-asha-1", "name": "Asha"})
    h = {"Authorization": "Bearer " + c.post(f"{api}/login", json={"email": "asha@example.com", "password": "pass-asha-1"}).json()["token"]}
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    o1 = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=h).json()
    dsn, name = _her_db()
    from app.pgdb import service as PG
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        tenant = s.get(AppProject, aid).tenant_id
    pc = PG.add(tenant, "Her Supabase", dsn)
    st = c.get(f"/api/apps/{aid}/owndb").json()
    assert st["linked"] is False and any(p["key"] == "supabase" for p in st["providers"]) and len(st["providers"]) >= 25
    assert st["connections"][0]["name"] == "Her Supabase" and "password" not in str(st["connections"])
    got = c.post(f"/api/apps/{aid}/owndb/link", json={"conn": pc["id"], "mode": mode}).json()
    assert got["mode"] == mode and got["copied"] >= 1 and got["counts"]["orders"] == {"app": 1, "database": 1}, got
    return c, aid, api, h, p1, o1, dsn, got["schema"]


def test_primary_write_through_and_her_edits_come_back(droid_env, monkeypatch):
    c, aid, api, h, p1, o1, dsn, S = _setup(droid_env, monkeypatch)
    with _her(dsn) as hc:
        cols = {r[0]: r[1] for r in hc.execute("SELECT column_name, data_type FROM information_schema.columns "
                                                "WHERE table_schema = %s AND table_name = 'orders'", (S,)).fetchall()}
        assert cols["total"] == "numeric" and cols["name"] == "text" and "_hoola" in cols and "_updated" in cols
        assert hc.execute(f'SELECT count(*) FROM "{S}"._hoola_accounts').fetchone()[0] == 1
        assert "pw" not in [r[0] for r in hc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s "
                                                     "AND table_name='_hoola_accounts'", (S,)).fetchall()]
    # an app write lands in her database inside the same request
    o2 = c.post(f"{api}/c/orders", json={"name": "Ravi", "phone": "9876500000", "cart": [{"id": p1["id"], "qty": 2}]}, headers=h).json()
    with _her(dsn) as hc:
        row = hc.execute(f'SELECT name, phone, total, _by FROM "{S}".orders WHERE id = %s', (o2["id"],)).fetchone()
        assert row[0] == "Ravi" and row[1] == "9876500000" and float(row[2]) == float(o2["total"]) and row[3] == "hoola"
        # she edits OUTSIDE Hoola: a field change, a new row, a delete
        hc.execute(f'UPDATE "{S}".orders SET note = %s WHERE id = %s', ("call before coming", o1["id"]))
        new_id = hc.execute(f"INSERT INTO \"{S}\".orders (name, phone, status, pay, paid) VALUES ('Meena', '9876511111', 'New', "
                            "'Cash on delivery', 'No') RETURNING id").fetchone()[0]
        hc.execute(f'UPDATE "{S}".orders SET status = %s WHERE id = %s', ("Teleported", o2["id"]))      # not a real status
    c.patch(f"/api/apps/{aid}/data/orders/{o1['id']}", json={"status": "Accepted"})                   # app edits another field
    out = c.post(f"/api/apps/{aid}/owndb/sync").json()
    assert out["ok"]
    rows = {x["id"]: x for x in c.get(f"/api/apps/{aid}/data/orders").json()["rows"]}
    assert rows[o1["id"]]["note"] == "call before coming" and rows[o1["id"]]["status"] == "Accepted"   # both edits kept
    assert new_id in rows and rows[new_id]["name"] == "Meena"
    assert rows[o2["id"]]["status"] != "Teleported"                                                     # checked like app input
    with _her(dsn) as hc:
        assert hc.execute(f'SELECT note, status FROM "{S}".orders WHERE id = %s', (o1["id"],)).fetchone() == ("call before coming", "Accepted")
        hc.execute(f'DELETE FROM "{S}".orders WHERE id = %s', (new_id,))
    c.post(f"/api/apps/{aid}/owndb/sync")
    assert new_id not in {x["id"] for x in c.get(f"/api/apps/{aid}/data/orders").json()["rows"]}
    audit = c.get(f"/api/apps/{aid}/logic/audit").json()["audit"]
    kinds = {a["kind"] for a in audit}
    assert {"own_db_linked", "own_db_in", "own_db_refused"} <= kinds
    # a new field in the app = a new column in her table
    from app.appmaker import backend as BE
    BE.change_schema(BE.by_key(api.rsplit("/", 1)[1]), {"add": [{"coll": "orders", "key": "landmark", "label": "Landmark"}]})
    c.post(f"/api/apps/{aid}/owndb/sync")
    with _her(dsn) as hc:
        assert "landmark" in [r[0] for r in hc.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s "
                                                       "AND table_name='orders'", (S,)).fetchall()]
    v = c.post(f"/api/apps/{aid}/owndb/verify").json()
    assert v["ok"], v
    # her database unreachable: the write is REFUSED (nothing half-saved), the app says why
    from app.appmaker import owndb as OD
    real = OD._dsn
    monkeypatch.setattr(OD, "_dsn", lambda o: {**real(o), "port": "1"})
    OD.close_pool(aid)
    before = len(c.get(f"/api/apps/{aid}/data/orders").json()["rows"])
    r = c.post(f"{api}/c/orders", json={"name": "Lost", "phone": "9876522222", "cart": [{"id": p1["id"], "qty": 1}]}, headers=h)
    assert r.status_code == 503 and "database" in r.json()["error"]
    assert len(c.get(f"/api/apps/{aid}/data/orders").json()["rows"]) == before
    monkeypatch.setattr(OD, "_dsn", real)
    assert c.post(f"{api}/c/orders", json={"name": "Back", "phone": "9876533333", "cart": [{"id": p1["id"], "qty": 1}]}, headers=h).status_code == 200
    # unlink: the app runs on Hoola again, her data stays
    c.post(f"/api/apps/{aid}/owndb/unlink")
    assert c.get(f"/api/apps/{aid}/owndb").json()["linked"] is False
    with _her(dsn) as hc:
        assert hc.execute(f'SELECT count(*) FROM "{S}".orders').fetchone()[0] >= 3


def test_mirror_mode_catches_up_and_never_blocks(droid_env, monkeypatch):
    c, aid, api, h, p1, o1, dsn, S = _setup(droid_env, monkeypatch, mode="mirror")
    from app.appmaker import owndb as OD
    monkeypatch.setattr(OD, "_dsn", lambda o: {"host": "127.0.0.1", "port": "1", "dbname": "x", "user": "x", "sslmode": "disable"})
    OD.close_pool(aid)
    o2 = c.post(f"{api}/c/orders", json={"name": "Ravi", "phone": "9876500000", "cart": [{"id": p1["id"], "qty": 1}]}, headers=h)
    assert o2.status_code == 200                                         # her database down never stops the app
    monkeypatch.undo()
    monkeypatch.setenv("PGDB_ALLOW_PRIVATE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    OD.tick(force=True)
    with _her(dsn) as hc:
        assert hc.execute(f'SELECT name FROM "{S}".orders WHERE id = %s', (o2.json()["id"],)).fetchone() == ("Ravi",)
        hc.execute(f'UPDATE "{S}".orders SET note = %s WHERE id = %s', ("outside", o1["id"]))
    OD.tick(force=True)                                                  # mirror = a read copy: outside edits are not pulled
    rows = {x["id"]: x for x in c.get(f"/api/apps/{aid}/data/orders").json()["rows"]}
    assert rows[o1["id"]].get("note", "") != "outside"
    assert c.get(f"/api/apps/{aid}/owndb").json()["lag"] == 0
