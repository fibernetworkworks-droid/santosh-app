"""v0.388 PAKKI NEEV (App Sahayak Pillar B, Phases 47-48): the app backend holds under many server processes and can
always be brought back - cross-process locks (file lock on SQLite, advisory locks on Postgres), no lost update of an
app's settings, a phone retry racing itself in two processes = one row, the write journal + snapshots + point-in-time
restore + export, indexed links, usage meters + quotas, the SQLite -> Postgres move, and (HOOLA_LOAD=1) 1,000
customers ordering limited stock at once against 4 server worker processes."""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

SERVER = Path(__file__).resolve().parents[1]
PG = os.environ.get("HOOLA_TEST_PG", "")
PGA = os.environ.get("HOOLA_PG_ADMIN", "")          # a Postgres server for the move target (the source stays SQLite)

COUNTER = r'''
import os, sys, time
sys.path.insert(0, sys.argv[1])
os.environ["DATABASE_URL"] = sys.argv[2]
from app.config import get_settings
get_settings.cache_clear()
if sys.argv[2].startswith("postgresql"):           # only a connection is needed (no tables): advisory locks
    from sqlalchemy import create_engine
    from app import db
    db._engine = create_engine(sys.argv[2])
from app.appmaker import locks as LK
p = sys.argv[3]
for _ in range(int(sys.argv[4])):
    with LK.hold("app:counter"):
        n = int(open(p).read() or 0)
        time.sleep(0.0005)                       # widen the window a lost update would need
        open(p, "w").write(str(n + 1))
'''


def _race(tmp_path, url, procs=3, each=60):
    script = tmp_path / "counter.py"
    script.write_text(COUNTER)
    f = tmp_path / "n.txt"
    f.write_text("0")
    ps = [subprocess.Popen([sys.executable, str(script), str(SERVER), url, str(f), str(each)], cwd=tmp_path) for _ in range(procs)]
    for p in ps:
        assert p.wait(timeout=180) == 0
    return int(f.read_text())


def test_lock_holds_across_processes_sqlite(tmp_path):
    assert _race(tmp_path, f"sqlite:///{tmp_path}/x.db") == 180


@pytest.mark.skipif(not PG, reason="HOOLA_TEST_PG not set")
def test_lock_holds_across_processes_postgres(tmp_path):
    assert _race(tmp_path, PG) == 180


def test_lock_is_reentrant_and_times_out(env):
    from app.appmaker import locks as LK
    with LK.hold("k1"):
        with LK.hold("k1"):                         # the same thread may take it again
            pass
    got = []

    def other():
        try:
            with LK.hold("k2", wait=0.3):
                got.append("in")
        except LK.LockTimeout:
            got.append("timeout")
    with LK.hold("k2"):
        t = threading.Thread(target=other)
        t.start()
        t.join()
    assert got == ["timeout"]


def test_settings_writes_never_overwrite_each_other(droid_env):
    """Stock, coupons, logic and the rest all rewrite one JSON per app: under the per-app lock, from the row as it is NOW."""
    from app.appmaker import backend as BE
    aid, conv, key, be = _built(droid_env)
    r = BE.by_key(key)

    def put(k):
        for i in range(25):
            BE.patch_backend(r, fn=lambda b, k=k, i=i: b.__setitem__(k, i))
    ts = [threading.Thread(target=put, args=(f"k{j}",)) for j in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    fresh = BE.by_key(key)
    got = json.loads(fresh.backend)
    assert all(got.get(f"k{j}") == 24 for j in range(4)) and got.get("schema")


def test_ensure_upgrade_keeps_every_setting(droid_env):
    from app.appmaker import backend as BE
    aid, conv, key, be = _built(droid_env)
    r = BE.by_key(key)
    BE.patch_backend(r, fn=lambda b: (b.update({"v": 1, "stock": {"p1": {"qty": 3}}, "coupons": {"X": {}}})))
    r = BE.by_key(key)
    out = BE.ensure(r)
    assert out["v"] == BE.SCHEMA_V and out["stock"] == {"p1": {"qty": 3}} and out["coupons"] == {"X": {}}


def _app(aid):
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    return r


def test_journal_snapshot_point_in_time_restore_and_export(droid_env, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.appmaker import backup as BK
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    c.post(f"{api}/signup", json={"email": "asha@example.com", "password": "pass-asha-1", "name": "Asha"})
    h = {"Authorization": "Bearer " + c.post(f"{api}/login", json={"email": "asha@example.com", "password": "pass-asha-1"}).json()["token"]}
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    o1 = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=h).json()
    snap = c.post(f"/api/apps/{aid}/backups/now").json()
    assert snap["rows"] >= 1 and snap["kind"] == "manual"
    time.sleep(1.1)
    o2 = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "note": "second", "cart": [{"id": p1["id"], "qty": 2}]}, headers=h).json()
    c.patch(f"/api/apps/{aid}/data/orders/{o1['id']}", json={"status": "Accepted"})
    time.sleep(1.1)
    mid = datetime.now(timezone.utc)
    time.sleep(1.1)
    c.patch(f"/api/apps/{aid}/data/orders/{o1['id']}", json={"status": "Delivered"})
    from app.appmaker import backend as BE
    from app.site import webapp as W
    BE.delete(_app(aid), "orders", o2["id"], W.Who(owner=True))           # her delete from Hoola
    # every write is in the journal (the app's, Hoola's, a delete)
    from sqlalchemy import select

    from app.db import session
    with session() as s:
        ops = [j.op for j in s.scalars(select(BK.AppJournal).where(BK.AppJournal.site_id == "app:" + aid)).all()]
    assert ops.count("insert") >= 2 and "update" in ops and "delete" in ops
    # preview, then restore to the middle minute: o2 back, o1 = Accepted again
    at = mid.astimezone(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%dT%H:%M:%S")
    pv = c.post(f"/api/apps/{aid}/backups/preview", json={"at": at}).json()
    assert pv["come_back"] == 1 and pv["change"] >= 1
    got = c.post(f"/api/apps/{aid}/backups/restore", json={"at": at}).json()
    assert got["came_back"] == 1 and got["safety"]
    rows = {x["id"]: x for x in c.get(f"/api/apps/{aid}/data/orders").json()["rows"]}
    assert o2["id"] in rows and rows[o1["id"]]["status"] == "Accepted"
    # the restore can itself be undone (its safety snapshot)
    back = c.post(f"/api/apps/{aid}/backups/restore", json={"name": got["safety"]}).json()
    rows = {x["id"]: x for x in c.get(f"/api/apps/{aid}/data/orders").json()["rows"]}
    assert back["removed"] == 1 and o2["id"] not in rows and rows[o1["id"]]["status"] == "Delivered"
    lst = c.get(f"/api/apps/{aid}/backups").json()["backups"]
    assert {x["kind"] for x in lst} >= {"manual", "before"}
    # export: a CSV per list + data.json + accounts without passwords
    import io
    import zipfile
    zf = zipfile.ZipFile(io.BytesIO(c.get(f"/api/apps/{aid}/export").content))
    names = set(zf.namelist())
    assert {"orders.csv", "data.json", "accounts.csv", "README.txt"} <= names
    acc = zf.read("accounts.csv").decode()
    from app.db import session as _s
    with _s() as s:
        pw = s.scalars(select(W.SiteAppMember.pw).where(W.SiteAppMember.site_id == "app:" + aid)).first()
    assert "asha@example.com" in acc and pw and pw not in acc and pw not in zf.read("data.json").decode()
    assert BK.daily_tick(force=True) >= 0


def test_links_are_indexed_not_scanned(droid_env):
    from app.appmaker import refs as RF
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    logic = {"relations": [{"name": "lines", "from": "lines", "field": "order", "to": "orders", "label": "Items",
                            "on_delete": "cascade"}],
             "formulas": [{"coll": "orders", "field": "line_total", "expr": "sum(lines.amount)"}]}
    lists = [{"key": "lines", "label": "Lines", "rules": {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"},
              "fields": [{"key": "order", "label": "Order", "type": "ref", "to": "orders"},
                         {"key": "amount", "label": "Amount", "type": "number"}]}]
    fields = [{"coll": "orders", "key": "line_total", "label": "Line total", "type": "number"}]
    assert c.put(f"/api/apps/{aid}/logic", json={"logic": logic, "lists": lists, "fields": fields}).json()["ok"]
    from app.appmaker import backend as BE
    from app.site import webapp as W
    r = BE.by_key(key)
    owner = W.Who(owner=True)
    order = BE.create(r, "orders", {"name": "A", "phone": "9876543210"}, owner)
    before = RF.STATS["lookups"]
    for amt in (10, 20, 30):
        BE.create(r, "lines", {"order": order["id"], "amount": amt}, owner)
    assert RF.child_ids("app:" + r.id, "lines", "order", order["id"]).__len__() == 3
    assert RF.STATS["lookups"] > before
    got = next(x for x in BE.owner_rows(BE.by_key(key), "orders") if x["id"] == order["id"])
    assert got["line_total"] == 60


def test_meter_and_quota(droid_env, monkeypatch):
    notes = []
    from app.appmaker.android import service as AN
    monkeypatch.setattr(AN, "_note", lambda r, t: notes.append(t))
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    c.post(f"{api}/signup", json={"email": "asha@example.com", "password": "pass-asha-1", "name": "Asha"})
    h = {"Authorization": "Bearer " + c.post(f"{api}/login", json={"email": "asha@example.com", "password": "pass-asha-1"}).json()["token"]}
    u = c.get(f"/api/apps/{aid}/usage").json()
    assert u["limits"]["rows"] == 50000 and u["rows"] == 0
    assert c.put(f"/api/apps/{aid}/usage", json={"rows": 0}).status_code == 400
    assert c.put(f"/api/apps/{aid}/usage", json={"rows": 5_000_000}).status_code == 400
    c.put(f"/api/apps/{aid}/usage", json={"rows": 2})
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    for _ in range(2):
        assert c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=h).status_code == 200
    r = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=h)
    assert r.status_code == 507
    u = c.get(f"/api/apps/{aid}/usage").json()
    assert u["rows"] == 2 and u["percent"]["rows"] == 100 and "rows" in u["full"] and u["writes_today"] >= 2
    assert any("100%" in n for n in notes)
    assert c.put(f"/api/apps/{aid}/usage", json={"rows": 1}).status_code == 400          # never below what is used


def test_phone_retry_racing_itself_makes_one_row(droid_env):
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    c.post(f"{api}/signup", json={"email": "asha@example.com", "password": "pass-asha-1", "name": "Asha"})
    h = {"Authorization": "Bearer " + c.post(f"{api}/login", json={"email": "asha@example.com", "password": "pass-asha-1"}).json()["token"]}
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    body = {"name": "Asha", "phone": "9876543210", "cid": "raceCid0000001", "cart": [{"id": p1["id"], "qty": 1}]}
    ids = []

    def go():
        ids.append(TestClient(app).post(f"{api}/c/orders", json=body, headers=h).json()["id"])
    ts = [threading.Thread(target=go) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(set(ids)) == 1 and len(c.get(f"/api/apps/{aid}/data/orders").json()["rows"]) == 1


@pytest.mark.skipif(not PGA, reason="HOOLA_PG_ADMIN not set")
def test_dbmove_sqlite_to_postgres(droid_env, tmp_path):
    """Her real move: a SQLite database with a built app + orders + journal -> a fresh Postgres, every count equal."""
    import uuid

    import psycopg
    from sqlalchemy.engine import make_url
    from app.config import get_settings
    src = get_settings().database_url
    if src.startswith("postgresql"):
        pytest.skip("this run already uses Postgres as the source")
    _built(droid_env)
    u = make_url(PGA)
    q = dict(u.query)
    name = "hoola_move_" + uuid.uuid4().hex[:8]
    with psycopg.connect(dbname="postgres", user=u.username or "postgres", host=q.get("host") or u.host,
                         port=int(q.get("port") or u.port or 5432), autocommit=True) as cn:
        cn.execute(f'CREATE DATABASE "{name}"')
    dst = u.set(database=name).render_as_string(hide_password=False)
    out = subprocess.run([sys.executable, "-m", "app.dbmove", "--from", src, "--to", dst], cwd=SERVER,
                         capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    assert "OK:" in out.stdout and "MISMATCH" not in out.stdout
    again = subprocess.run([sys.executable, "-m", "app.dbmove", "--from", src, "--to", dst], cwd=SERVER,
                           capture_output=True, text=True, timeout=600)
    assert again.returncode != 0 and "already has data" in (again.stdout + again.stderr)   # never onto a busy database


@pytest.mark.skipif(os.environ.get("HOOLA_LOAD") != "1", reason="the load proof runs in CI (HOOLA_LOAD=1)")
def test_thousand_customers_four_worker_processes(droid_env, tmp_path):
    """1,000 customers order a product with 300 in stock at the same moment, every 4th phone retrying; 4 uvicorn worker
    processes on one database. Exactly 300 orders, stock 0 (never below), one row per cid, no server errors."""
    import asyncio
    import socket

    from app.appmaker import backend as BE
    from app.appmaker import loadtest as LT
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    c.put(f"/api/apps/{aid}/stock", json={"items": {p1["id"]: {"qty": 300}}})
    c.put(f"/api/apps/{aid}/usage", json={"rows": 100000})
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    envv = {**os.environ, "PYTHONPATH": str(SERVER), "WORKER_TICK_SECONDS": "3600"}
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port),
                            "--workers", "4", "--log-level", "warning"], cwd=os.getcwd(), env=envv)
    try:
        import httpx
        for _ in range(120):
            try:
                if httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        n = int(os.environ.get("HOOLA_LOAD_CUSTOMERS", "1000"))
        out = asyncio.run(LT.run(f"http://127.0.0.1:{port}", key, p1["id"], customers=n, concurrency=200))
    finally:
        srv.terminate()
        srv.wait(timeout=60)
    print(json.dumps({k: v for k, v in out.items() if k != "order_ids"}, indent=1))
    rows = BE.owner_rows(BE.by_key(key), "orders", 5000)
    left = {p["id"]: p for p in c.get(f"/api/apps/{aid}/stock").json()["products"]}[p1["id"]]["qty"]
    assert out["logged_in"] == n
    assert 500 not in out["codes"]["order"] and 0 not in out["codes"]["order"]
    assert len(rows) == out["orders_ok"] == min(n, 300)                 # nothing oversold, nothing lost
    assert left == 300 - len(rows) and left >= 0
    cids = [json.loads(json.dumps(x)).get("id") for x in rows]
    assert len(set(cids)) == len(cids)
