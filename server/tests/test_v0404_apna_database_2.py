"""v0.404 APNA DATABASE 2: an app's data in HER MySQL-family (MySQL / MariaDB / PlanetScale / TiDB), MongoDB (Atlas)
or Firebase (Firestore) database - each against a REAL server (MariaDB, a MongoDB replica set, the Firestore emulator).

For every kind: her connection added in the app (sealed), link = her tap (copy + counts), PRIMARY write-through (an app
write lands there inside the request), her edits OUTSIDE Hoola (update / add / delete in her table, collection or
documents - a Mongo ObjectId / Firestore auto-id add is re-keyed to a Hoola id) come back with the values checked, her
database unreachable = the write refused and nothing saved, unlink keeps the data."""
import json
import os
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

MYSQL = os.environ.get("HOOLA_MYSQL_ADMIN", "")          # mysql://root:pass@127.0.0.1:3306
MONGO = os.environ.get("HOOLA_MONGO", "")                # mongodb://127.0.0.1:27017/?directConnection=true
FS = os.environ.get("HOOLA_FIRESTORE_EMU", "")           # 127.0.0.1:8080


def _mysql_db():
    import pymysql
    from urllib.parse import urlparse
    u = urlparse(MYSQL)
    name = "her_" + uuid.uuid4().hex[:8]
    c = pymysql.connect(host=u.hostname, port=u.port or 3306, user=u.username, password=u.password or "", autocommit=True)
    c.cursor().execute(f"CREATE DATABASE `{name}`")
    c.close()
    secret = f"mysql://{u.username}:{u.password}@{u.hostname}:{u.port or 3306}/{name}?ssl=false"
    return secret, name


KINDS = []
if MYSQL:
    KINDS.append("mysql")
if MONGO:
    KINDS.append("mongodb")
if FS:
    KINDS.append("firestore")


def _secret(kind):
    if kind == "mysql":
        return _mysql_db()[0]
    if kind == "mongodb":
        base, _, q = MONGO.partition("?")
        return base.rstrip("/") + "/her_" + uuid.uuid4().hex[:8] + ("?" + q if q else "")
    return json.dumps({"emulator": FS, "project_id": "demo-hoola-" + uuid.uuid4().hex[:6]})


class Her:
    """Her side, written by HER tools (not Hoola): raw driver calls on her own table / collection / documents."""

    def __init__(self, kind, o):
        from app.appmaker import owndb as OD
        from app.appmaker import owndb_conns as OC
        self.kind, self.o = kind, o
        _v, self.d = OC.secret_of(o["tenant"], o["conn"])
        self.OC, self.OD = OC, OD

    def table(self, coll):
        from app.appmaker.owndb_drivers import tname
        return tname(self.o, coll)

    def get(self, coll, rid):
        if self.kind == "mysql":
            c = self.OC.mysql_connect(self.d)
            cur = c.cursor()
            cur.execute(f"SELECT name, note, status FROM `{self.table(coll)}` WHERE id = %s", (rid,))
            x = cur.fetchone()
            c.close()
            return None if x is None else {"name": x[0], "note": x[1], "status": x[2]}
        if self.kind == "mongodb":
            cl = self.OC.mongo_client(self.d)
            x = cl[self.d["db"]][self.table(coll)].find_one({"_id": rid})
            cl.close()
            return x
        cl = self.OC.firestore_client(self.d)
        x = cl.collection("hoola_apps").document(self.o["schema"]).collection(coll).document(rid).get()
        return x.to_dict() if x.exists else None

    def update(self, coll, rid, **kv):
        if self.kind == "mysql":
            c = self.OC.mysql_connect(self.d)
            c.cursor().execute(f"UPDATE `{self.table(coll)}` SET " + ", ".join(f"`{k}` = %s" for k in kv) + " WHERE id = %s",
                               [*kv.values(), rid])
            c.commit()
            c.close()
        elif self.kind == "mongodb":
            cl = self.OC.mongo_client(self.d)
            cl[self.d["db"]][self.table(coll)].update_one({"_id": rid}, {"$set": kv})
            cl.close()
        else:
            self.OC.firestore_client(self.d).collection("hoola_apps").document(self.o["schema"]).collection(coll).document(rid).update(kv)

    def add(self, coll, **kv):
        if self.kind == "mysql":
            rid = "row_" + uuid.uuid4().hex[:12]
            c = self.OC.mysql_connect(self.d)
            c.cursor().execute(f"INSERT INTO `{self.table(coll)}` (id, " + ", ".join(f"`{k}`" for k in kv) + ") VALUES (%s"
                               + ", %s" * len(kv) + ")", [rid, *kv.values()])
            c.commit()
            c.close()
            return rid
        if self.kind == "mongodb":
            cl = self.OC.mongo_client(self.d)
            cl[self.d["db"]][self.table(coll)].insert_one(dict(kv))       # her own ObjectId
            cl.close()
            return None
        self.OC.firestore_client(self.d).collection("hoola_apps").document(self.o["schema"]).collection(coll).add(dict(kv))
        return None

    def delete(self, coll, rid):
        if self.kind == "mysql":
            c = self.OC.mysql_connect(self.d)
            c.cursor().execute(f"DELETE FROM `{self.table(coll)}` WHERE id = %s", (rid,))
            c.commit()
            c.close()
        elif self.kind == "mongodb":
            cl = self.OC.mongo_client(self.d)
            cl[self.d["db"]][self.table(coll)].delete_one({"_id": rid})
            cl.close()
        else:
            self.OC.firestore_client(self.d).collection("hoola_apps").document(self.o["schema"]).collection(coll).document(rid).delete()


def _sync(c, aid, kind):
    from app.appmaker.owndb_drivers import DRIVERS
    if kind == "mysql":
        DRIVERS["mysql"].checked.clear()                  # the 5-minute delete check runs now
    if kind == "firestore":
        time.sleep(1.5)                                   # the listener delivers
    out = c.post(f"/api/apps/{aid}/owndb/sync").json()
    assert out.get("ok"), out
    return {x["id"]: x for x in c.get(f"/api/apps/{aid}/data/orders").json()["rows"]}


@pytest.mark.skipif(not KINDS, reason="no MySQL / MongoDB / Firestore test server set")
@pytest.mark.parametrize("kind", KINDS)
def test_her_database_of_every_kind(droid_env, monkeypatch, kind):
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
    # her database, typed in the app (sealed; the secret never comes back)
    bad = c.post("/api/owndb/conns", json={"kind": kind, "name": "x", "secret": "nonsense"})
    assert bad.status_code == 400
    conn = c.post("/api/owndb/conns", json={"kind": kind, "name": f"Her {kind}", "secret": _secret(kind)}).json()
    assert conn["kind"] == kind and "password" not in json.dumps(conn) and conn["id"].startswith("odc_")
    st = c.get(f"/api/apps/{aid}/owndb").json()
    assert any(x["id"] == conn["id"] for x in st["connections"]) and any(p["kind"] == kind for p in st["providers"])
    got = c.post(f"/api/apps/{aid}/owndb/link", json={"conn": conn["id"], "mode": "primary"}).json()
    assert got["kind"] == kind and got["counts"]["orders"] == {"app": 1, "database": 1}, got
    from app.appmaker import owndb as OD
    her = Her(kind, OD.cfg(aid, fresh=True))
    assert her.get("orders", o1["id"])["name"] == "Asha"
    # an app write lands in her database inside the same request
    o2 = c.post(f"{api}/c/orders", json={"name": "Ravi", "phone": "9876500000", "cart": [{"id": p1["id"], "qty": 2}]}, headers=h).json()
    assert her.get("orders", o2["id"])["name"] == "Ravi"
    _sync(c, aid, kind)                                   # the listener / stream sees Hoola's own writes - all skipped
    # her edits OUTSIDE Hoola
    her.update("orders", o1["id"], note="call before coming")
    her.update("orders", o2["id"], status="Teleported")   # not a real status: refused
    new_id = her.add("orders", name="Meena", phone="9876511111", status="New", pay="Cash on delivery", paid="No")
    rows = _sync(c, aid, kind)
    assert rows[o1["id"]]["note"] == "call before coming"
    assert rows[o2["id"]]["status"] != "Teleported"
    meena = [x for x in rows.values() if x.get("name") == "Meena"]
    assert len(meena) == 1 and meena[0]["id"].startswith("row_")
    if new_id:
        assert meena[0]["id"] == new_id
    assert her.get("orders", meena[0]["id"]) is not None          # re-keyed in her database too (one doc, Hoola id)
    # the app edits another field of the same row: her outside edit stays
    c.patch(f"/api/apps/{aid}/data/orders/{o1['id']}", json={"status": "Accepted"})
    rows = _sync(c, aid, kind)
    assert rows[o1["id"]]["note"] == "call before coming" and rows[o1["id"]]["status"] == "Accepted"
    assert her.get("orders", o1["id"])["status"] == "Accepted"
    # deleted outside -> gone from the app
    her.delete("orders", meena[0]["id"])
    rows = _sync(c, aid, kind)
    assert meena[0]["id"] not in rows
    v = c.post(f"/api/apps/{aid}/owndb/verify").json()
    assert v["ok"], v
    kinds = {a["kind"] for a in c.get(f"/api/apps/{aid}/logic/audit").json()["audit"]}
    assert {"own_db_linked", "own_db_in", "own_db_refused"} <= kinds
    # her database unreachable: refused, nothing saved
    real = OD._secret
    if kind == "firestore":
        from app.appmaker import owndb_drivers as DRV
        monkeypatch.setattr(DRV.DRIVERS["firestore"], "push", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("unreachable")))
    else:
        def broken(o):
            v_, d = real(o)
            return v_, {**d, "port": 1, "uri": "mongodb://127.0.0.1:1/x?directConnection=true&serverSelectionTimeoutMS=500", "hosts": ["127.0.0.1:1"]}
        monkeypatch.setattr(OD, "_secret", broken)
        OD._drv({"kind": kind}).close(aid)
    before = len(c.get(f"/api/apps/{aid}/data/orders").json()["rows"])
    r = c.post(f"{api}/c/orders", json={"name": "Lost", "phone": "9876522222", "cart": [{"id": p1["id"], "qty": 1}]}, headers=h)
    assert r.status_code == 503
    assert len(c.get(f"/api/apps/{aid}/data/orders").json()["rows"]) == before
    monkeypatch.undo()
    monkeypatch.setenv("PGDB_ALLOW_PRIVATE", "true")
    get_settings.cache_clear()
    # unlink: her data stays
    c.post(f"/api/apps/{aid}/owndb/unlink")
    assert c.get(f"/api/apps/{aid}/owndb").json()["linked"] is False
    assert her.get("orders", o1["id"]) is not None
