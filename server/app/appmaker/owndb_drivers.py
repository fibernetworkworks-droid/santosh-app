"""v0.397 APNA DATABASE 2: one interface, four kinds of her database.

    ensure(r, o, lists)             her tables / collections (+ indexes) - additive, safe to run again
    push(r, o, lists, entries)      Hoola's writes -> hers (field-level), each row stamped with `_hv` = the fingerprint of
                                    the values Hoola last wrote
    accounts(r, o, rows)            the app's accounts (never a password hash)
    outside(r, o, lists)            what SHE changed outside Hoola -> ({coll: [row]}, [(coll, id)] deleted)
    count(r, o, coll) / close(aid)

How "changed outside" is seen without Postgres triggers (PlanetScale / TiDB have no triggers; Firestore and MongoDB are
not SQL): a row whose current values no longer match its `_hv` was edited outside; a row without `_hv` was added outside.
  MySQL family: `_updated TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)` (a column property, works everywhere) -> one indexed
                query per list per sync; deletes = ids that were there at the last check and are gone now (every 5 min).
  MongoDB:      a change stream (Atlas / any replica set) on each collection, drained every sync (resume token kept);
                a standalone server = a capped rotating scan instead.
  Firestore:    a live listener per collection (her database pushes changes; re-reading every document every minute
                would cost her real money in reads).
Hoola-shaped ids (`row_<12 hex>`): an outside add with another id (Mongo ObjectId, Firestore auto-id) is re-keyed once."""
from __future__ import annotations

import hashlib
import json
import logging
import queue
import re
import threading
import time
from datetime import date, datetime
from typing import Any

from . import owndb_conns as OC

log = logging.getLogger(__name__)
ROW_ID = re.compile(r"^row_[0-9a-f]{12}$")
BATCH = 500


# ---------------------------------------------------------------- values + the fingerprint (same on every kind)
def norm(f: dict, v: Any) -> Any:
    """One comparable form of a field value, whatever the database handed back."""
    t = f.get("type")
    if v is None or v == "":
        return False if t == "yes_no" else ""
    if t == "number":
        try:
            x = float(v)
        except (TypeError, ValueError):
            return str(v)
        return int(x) if x == int(x) and abs(x) < 1e15 else round(x, 6)
    if t == "yes_no":
        return bool(v) if not isinstance(v, str) else v.strip().lower() in ("1", "true", "yes", "haan")
    if t == "date":
        if isinstance(v, (date, datetime)):
            return v.isoformat()[:10]
        return str(v)[:10]
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def hv(fields: list[dict], vals: dict) -> str:
    return hashlib.sha1(json.dumps([[f["key"], norm(f, vals.get(f["key"]))] for f in fields], ensure_ascii=False,
                                   sort_keys=True).encode()).hexdigest()


def split(fields: list[dict], data: dict) -> tuple[dict, dict]:
    keys = {f["key"] for f in fields}
    return {f["key"]: norm(f, data.get(f["key"])) for f in fields}, {k: v for k, v in data.items() if k not in keys}


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def new_id() -> str:
    import uuid
    return "row_" + uuid.uuid4().hex[:12]


def tname(o: dict, coll: str) -> str:
    """Her table / collection name: `<schema>__<list>` (`_hoola_<name>` lists keep their own prefix)."""
    base = ("_hoola_" + coll.lstrip("_")) if coll.startswith("_") else coll
    return f"{o['schema']}__{base}"[:64]


# ================================================================ MySQL family
MY_TYPES = {"number": "DECIMAL(24,6)", "date": "DATE", "yes_no": "TINYINT(1)", "ref": "VARCHAR(40)"}


class MySQL:
    kind = "mysql"

    def __init__(self):
        self.known: dict[tuple[str, str], set[str]] = {}
        self.checked: dict[tuple[str, str], float] = {}

    def conn(self, r, o):
        from . import owndb as OD
        _v, d = OD._secret(o)
        return OC.mysql_connect(d)

    @staticmethod
    def q(n: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", n):
            raise OC.OwnDbConnError(f"naam '{n}' database mein nahi chalega")
        return f"`{n}`"

    def _cols(self, cur, db: str, table: str) -> set[str]:
        cur.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", (db, table))
        return {x[0] for x in cur.fetchall()}

    def ensure(self, r, o, lists):
        c = self.conn(r, o)
        try:
            cur = c.cursor()
            cur.execute("SELECT DATABASE()")
            db = cur.fetchone()[0]
            for coll, fields in lists.items():
                T = self.q(tname(o, coll))
                cur.execute(f"CREATE TABLE IF NOT EXISTS {T} (id VARCHAR(40) NOT NULL PRIMARY KEY, owner_id VARCHAR(40) NOT NULL DEFAULT '', "
                            "created_at DATETIME(6) NULL, _updated TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6), "
                            "_hv CHAR(40) NULL, _hoola LONGTEXT NULL, KEY ix_upd (_updated)) DEFAULT CHARSET=utf8mb4")
                have = self._cols(cur, db, tname(o, coll))
                for f in fields:
                    if f["key"] not in have:
                        cur.execute(f"ALTER TABLE {T} ADD COLUMN {self.q(f['key'])} {MY_TYPES.get(f['type'], 'TEXT')} NULL")
                        if f.get("type") == "ref":
                            cur.execute(f"ALTER TABLE {T} ADD KEY {self.q(('ix_' + f['key'])[:60])} ({self.q(f['key'])})")
            cur.execute(f"CREATE TABLE IF NOT EXISTS {self.q(o['schema'] + '___hoola_accounts')} (id VARCHAR(40) NOT NULL PRIMARY KEY, "
                        "email VARCHAR(200) NOT NULL DEFAULT '', name VARCHAR(200) NOT NULL DEFAULT '', role VARCHAR(20) NOT NULL DEFAULT 'member', "
                        "created_at DATETIME(6) NULL) DEFAULT CHARSET=utf8mb4")
            c.commit()
        finally:
            c.close()
        return {"tables": len(lists)}

    def _generic(self, cur, o, coll):
        cur.execute(f"CREATE TABLE IF NOT EXISTS {self.q(tname(o, coll))} (id VARCHAR(40) NOT NULL PRIMARY KEY, "
                    "owner_id VARCHAR(40) NOT NULL DEFAULT '', created_at DATETIME(6) NULL, data LONGTEXT NULL) DEFAULT CHARSET=utf8mb4")

    def _val(self, f, v):
        v = norm(f, v)
        if v == "" or v is None:
            return None
        if f.get("type") == "yes_no":
            return 1 if v else 0
        if f.get("type") == "date":
            try:
                return date.fromisoformat(str(v)[:10])
            except ValueError:
                return None
        return v

    def push(self, r, o, lists, entries, conn=None):
        c = conn or self.conn(r, o)
        n = 0
        try:
            cur = c.cursor()
            for op, rid, coll, owner, before, after, created in entries:
                T = self.q(tname(o, coll))
                if op == "delete":
                    cur.execute(f"DELETE FROM {T} WHERE id = %s", (rid,))
                    n += 1
                    continue
                new = _j(after, {})
                created_dt = _dt(created)
                if coll not in lists:
                    self._generic(cur, o, coll)
                    cur.execute(f"INSERT INTO {T} (id, owner_id, created_at, data) VALUES (%s, %s, %s, %s) "
                                "ON DUPLICATE KEY UPDATE owner_id = VALUES(owner_id), data = VALUES(data)",
                                (rid, owner or "", created_dt, json.dumps(new, ensure_ascii=False)))
                    n += 1
                    continue
                fields = lists[coll]
                cols, own = split(fields, new)
                changed = list(cols) if op != "update" else [k for k, v in cols.items() if v != split(fields, _j(before, {}))[0].get(k)]
                names = ["id", "owner_id", "created_at", "_hv", "_hoola"] + [f["key"] for f in fields]
                vals = [rid, owner or "", created_dt, hv(fields, new), json.dumps(own, ensure_ascii=False)] + \
                       [self._val(f, new.get(f["key"])) for f in fields]
                upd = ["_hv = VALUES(_hv)", "_hoola = VALUES(_hoola)"] + [f"{self.q(k)} = VALUES({self.q(k)})" for k in changed]
                cur.execute(f"INSERT INTO {T} ({', '.join(self.q(x) for x in names)}) VALUES ({', '.join(['%s'] * len(names))}) "
                            f"ON DUPLICATE KEY UPDATE {', '.join(upd)}", vals)
                n += 1
            if conn is None:
                c.commit()
        except Exception:
            if conn is None:
                c.rollback()
            raise
        finally:
            if conn is None:
                c.close()
        return n

    def accounts(self, r, o, rows):
        c = self.conn(r, o)
        try:
            cur = c.cursor()
            T = self.q(o["schema"] + "___hoola_accounts")
            for x in rows:
                cur.execute(f"INSERT INTO {T} (id, email, name, role, created_at) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE "
                            "email = VALUES(email), name = VALUES(name), role = VALUES(role)", (x[0], x[1], x[2], x[3], x[4]))
            if rows:
                cur.execute(f"DELETE FROM {T} WHERE id NOT IN ({', '.join(['%s'] * len(rows))})", [x[0] for x in rows])
            else:
                cur.execute(f"DELETE FROM {T}")
            c.commit()
        finally:
            c.close()

    def outside(self, r, o, lists, cursors):
        changed: dict[str, list] = {}
        gone: list[tuple[str, str]] = []
        c = self.conn(r, o)
        try:
            cur = c.cursor()
            for coll, fields in lists.items():
                T = self.q(tname(o, coll))
                since = cursors.get(coll) or "1970-01-02 00:00:00"
                names = ["id", "owner_id", "created_at", "_updated", "_hv"] + [f["key"] for f in fields]
                cur.execute(f"SELECT {', '.join(self.q(x) for x in names)} FROM {T} WHERE _updated > %s ORDER BY _updated LIMIT {BATCH}", (since,))
                for row in cur.fetchall():
                    x = dict(zip(names, row))
                    cursors[coll] = str(x["_updated"])
                    vals = {f["key"]: x.get(f["key"]) for f in fields}
                    if x.get("_hv") and x["_hv"] == hv(fields, vals):
                        continue                              # Hoola's own write
                    changed.setdefault(coll, []).append({"id": x["id"], "owner_id": x["owner_id"] or "", "created_at": x["created_at"], **vals})
                key = (r.id, coll)
                if time.time() - self.checked.get(key, 0) > 300:
                    self.checked[key] = time.time()
                    cur.execute(f"SELECT id FROM {T}")
                    now_ids = {x[0] for x in cur.fetchall()}
                    if key in self.known:
                        gone += [(coll, i) for i in self.known[key] - now_ids]
                    self.known[key] = now_ids
        finally:
            c.close()
        return changed, gone

    def count(self, r, o, coll):
        c = self.conn(r, o)
        try:
            cur = c.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {self.q(tname(o, coll))}")
            return int(cur.fetchone()[0])
        finally:
            c.close()

    def close(self, aid):
        for k in [k for k in self.known if k[0] == aid]:
            self.known.pop(k, None)
            self.checked.pop(k, None)


def _dt(s: Any):
    if not s:
        return None
    if isinstance(s, datetime):
        return s.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(s)).replace(tzinfo=None)
    except ValueError:
        return None


# ================================================================ MongoDB
class Mongo:
    kind = "mongodb"

    def __init__(self):
        self.clients: dict[str, Any] = {}
        self.dbname: dict[str, str] = {}
        self.streams: dict[tuple[str, str], Any] = {}
        self.scan_at: dict[tuple[str, str], Any] = {}
        self.ours: set[str] = set()

    def db(self, r, o):
        cl = self.clients.get(r.id)
        if cl is None:
            from . import owndb as OD
            _v, d = OD._secret(o)
            cl = self.clients[r.id] = OC.mongo_client(d)
            self.dbname[r.id] = d["db"]
        return cl[self.dbname[r.id]]

    def prime(self, r, o, lists):
        """At link time: start watching now, so an outside change right after linking is not missed."""
        import pymongo
        db = self.db(r, o)
        for coll in lists:
            key = (r.id, coll)
            if key in self.streams or key in self.scan_at:
                continue
            try:
                self.streams[key] = db[tname(o, coll)].watch(full_document="updateLookup")
            except pymongo.errors.PyMongoError:
                self.scan_at[key] = None

    def ensure(self, r, o, lists):
        db = self.db(r, o)
        for coll, fields in lists.items():
            col = db[tname(o, coll)]
            for f in fields:
                if f.get("type") == "ref":
                    col.create_index(f["key"])
            col.create_index("_hv")
        db[o["schema"] + "___hoola_accounts"].create_index("email")
        return {"tables": len(lists)}

    def _val(self, f, v):
        v = norm(f, v)
        return None if v == "" and f.get("type") != "text" else v

    def push(self, r, o, lists, entries, conn=None):
        from pymongo import DeleteOne, UpdateOne
        db = self.db(r, o)
        ops: dict[str, list] = {}
        for op, rid, coll, owner, before, after, created in entries:
            name = tname(o, coll)
            if op == "delete":
                ops.setdefault(name, []).append(DeleteOne({"_id": rid}))
                continue
            new = _j(after, {})
            if coll not in lists:
                ops.setdefault(name, []).append(UpdateOne({"_id": rid}, {"$set": {"owner_id": owner or "", "created_at": created, "data": new}}, upsert=True))
                continue
            fields = lists[coll]
            cols, own = split(fields, new)
            if op == "update":
                oldc = split(fields, _j(before, {}))[0]
                cols = {k: v for k, v in cols.items() if v != oldc.get(k)}
            sets = {**{k: self._val(next(f for f in fields if f["key"] == k), v) for k, v in cols.items()},
                    "owner_id": owner or "", "created_at": created, "_hoola": own, "_hv": hv(fields, new)}
            ops.setdefault(name, []).append(UpdateOne({"_id": rid}, {"$set": sets}, upsert=True))
        n = 0
        for name, lst in ops.items():
            if lst:
                db[name].bulk_write(lst, ordered=True)
                n += len(lst)
        return n

    def accounts(self, r, o, rows):
        db = self.db(r, o)
        col = db[o["schema"] + "___hoola_accounts"]
        ids = [x[0] for x in rows]
        for x in rows:
            col.update_one({"_id": x[0]}, {"$set": {"email": x[1], "name": x[2], "role": x[3],
                                                     "created_at": x[4].isoformat() if x[4] else None}}, upsert=True)
        col.delete_many({"_id": {"$nin": ids}})

    def outside(self, r, o, lists, cursors):
        import pymongo
        db = self.db(r, o)
        changed: dict[str, list] = {}
        gone: list[tuple[str, str]] = []
        for coll, fields in lists.items():
            name = tname(o, coll)
            key = (r.id, coll)
            docs, deleted = [], []
            st = self.streams.get(key)
            if st is None and key not in self.scan_at:
                try:
                    kw = {"full_document": "updateLookup"}
                    if cursors.get(coll):
                        kw["resume_after"] = cursors[coll]
                    st = self.streams[key] = db[name].watch(**kw)
                except pymongo.errors.PyMongoError as e:     # standalone server: no change streams
                    log.info("mongo change stream unavailable (%s): scanning", e)
                    self.scan_at[key] = None
                    cursors.pop(coll, None)
            if st is not None:
                for _ in range(BATCH):
                    ev = st.try_next()
                    if ev is None:
                        break
                    if ev.get("operationType") == "delete":
                        deleted.append(str(ev["documentKey"]["_id"]))
                    elif ev.get("fullDocument") is not None:
                        docs.append(ev["fullDocument"])
                if st.resume_token is not None:
                    cursors[coll] = st.resume_token
            else:                                             # capped rotating scan
                after = self.scan_at.get(key)
                q = {"_id": {"$gt": after}} if after is not None else {}
                batch = list(db[name].find(q).sort("_id", 1).limit(2000))
                self.scan_at[key] = batch[-1]["_id"] if len(batch) == 2000 else None
                docs = batch
            for d in docs:
                did = str(d.get("_id"))
                if did in self.ours:
                    self.ours.discard(did)
                    continue
                vals = {f["key"]: d.get(f["key"]) for f in fields}
                if d.get("_hv") and d["_hv"] == hv(fields, vals):
                    continue
                if not ROW_ID.match(did):                    # added outside with a Mongo id: re-key once
                    nid = new_id()
                    doc = {k: v for k, v in d.items() if k != "_id"}
                    self.ours.update({nid, did})
                    db[name].insert_one({"_id": nid, **doc})
                    db[name].delete_one({"_id": d["_id"]})
                    did = nid
                changed.setdefault(coll, []).append({"id": did, "owner_id": d.get("owner_id") or "",
                                                     "created_at": d.get("created_at"), **vals})
            gone += [(coll, i) for i in deleted if i not in self.ours]
        return changed, gone

    def count(self, r, o, coll):
        return int(self.db(r, o)[tname(o, coll)].count_documents({}))

    def close(self, aid):
        for k in [k for k in self.streams if k[0] == aid]:
            try:
                self.streams.pop(k).close()
            except Exception:                                # noqa: BLE001
                pass
        for k in [k for k in self.scan_at if k[0] == aid]:
            self.scan_at.pop(k, None)
        cl = self.clients.pop(aid, None)
        self.dbname.pop(aid, None)
        if cl is not None:
            cl.close()


# ================================================================ Firebase (Firestore)
class Firestore:
    kind = "firestore"

    def __init__(self):
        self.clients: dict[str, Any] = {}
        self.watch: dict[tuple[str, str], Any] = {}
        self.q: dict[tuple[str, str], queue.Queue] = {}
        self.ours: set[str] = set()
        self._lock = threading.Lock()

    def client(self, r, o):
        cl = self.clients.get(r.id)
        if cl is None:
            from . import owndb as OD
            _v, d = OD._secret(o)
            cl = self.clients[r.id] = OC.firestore_client(d)
        return cl

    def col(self, r, o, coll):
        base = ("_hoola_" + coll.lstrip("_")) if coll.startswith("_") else coll
        return self.client(r, o).collection("hoola_apps").document(o["schema"]).collection(base)

    def ensure(self, r, o, lists):
        self.client(r, o).collection("hoola_apps").document(o["schema"]).set(
            {"app": f"{r.name} ({r.number})", "lists": sorted(lists)}, merge=True)
        return {"tables": len(lists)}

    def _val(self, f, v):
        v = norm(f, v)
        return None if v == "" and f.get("type") != "text" else v

    def push(self, r, o, lists, entries, conn=None):
        cl = self.client(r, o)
        batch, n = cl.batch(), 0
        for op, rid, coll, owner, before, after, created in entries:
            ref = self.col(r, o, coll).document(rid)
            if op == "delete":
                self.ours.add(rid)
                batch.delete(ref)
            else:
                new = _j(after, {})
                if coll not in lists:
                    batch.set(ref, {"owner_id": owner or "", "created_at": created, "data": new}, merge=True)
                else:
                    fields = lists[coll]
                    cols, own = split(fields, new)
                    if op == "update":
                        oldc = split(fields, _j(before, {}))[0]
                        cols = {k: v for k, v in cols.items() if v != oldc.get(k)}
                    sets = {**{k: self._val(next(f for f in fields if f["key"] == k), v) for k, v in cols.items()},
                            "owner_id": owner or "", "created_at": created, "_hoola": own, "_hv": hv(fields, new)}
                    batch.set(ref, sets, merge=True)
            n += 1
            if n % 450 == 0:
                batch.commit()
                batch = cl.batch()
        batch.commit()
        return n

    def accounts(self, r, o, rows):
        col = self.col(r, o, "_accounts")
        ids = {x[0] for x in rows}
        for x in rows:
            col.document(x[0]).set({"email": x[1], "name": x[2], "role": x[3], "created_at": x[4].isoformat() if x[4] else None})
        for d in col.list_documents(page_size=500):
            if d.id not in ids:
                d.delete()

    def _listen(self, r, o, coll):
        key = (r.id, coll)
        with self._lock:
            if key in self.watch:
                return self.q[key]
            qq = self.q[key] = queue.Queue(maxsize=20000)

            def on_snap(_docs, changes, _read_time, qq=qq):
                for ch in changes:
                    try:
                        qq.put_nowait((ch.type.name, ch.document.id, ch.document.to_dict() if ch.type.name != "REMOVED" else None))
                    except queue.Full:
                        log.warning("firestore change queue full")
            self.watch[key] = self.col(r, o, coll).on_snapshot(on_snap)
            return qq

    def outside(self, r, o, lists, cursors):
        changed: dict[str, list] = {}
        gone: list[tuple[str, str]] = []
        for coll, fields in lists.items():
            qq = self._listen(r, o, coll)
            col = None
            for _ in range(5 * BATCH):
                try:
                    kind, did, d = qq.get_nowait()
                except queue.Empty:
                    break
                if kind == "REMOVED":
                    if did in self.ours:
                        self.ours.discard(did)
                    else:
                        gone.append((coll, did))
                    continue
                if did in self.ours and not ROW_ID.match(did):
                    continue
                vals = {f["key"]: (d or {}).get(f["key"]) for f in fields}
                if (d or {}).get("_hv") and d["_hv"] == hv(fields, vals):
                    continue
                if not ROW_ID.match(did):                     # added outside with a Firestore auto-id: re-key once
                    col = col or self.col(r, o, coll)
                    nid = new_id()
                    self.ours.add(did)                         # only the OLD id's removal is ours - a later delete of
                    col.document(nid).set(d or {})             # the new row outside must still be seen
                    col.document(did).delete()
                    did = nid
                changed.setdefault(coll, []).append({"id": did, "owner_id": (d or {}).get("owner_id") or "",
                                                     "created_at": (d or {}).get("created_at"), **vals})
        return changed, gone

    def count(self, r, o, coll):
        q = self.col(r, o, coll)
        try:
            res = q.count().get()
            return int(res[0][0].value)
        except Exception:                                    # noqa: BLE001 - an older emulator: count by listing ids
            return sum(1 for _ in q.list_documents(page_size=1000))

    def close(self, aid):
        with self._lock:
            for k in [k for k in self.watch if k[0] == aid]:
                try:
                    self.watch.pop(k).unsubscribe()
                except Exception:                            # noqa: BLE001
                    pass
                self.q.pop(k, None)
        self.clients.pop(aid, None)


DRIVERS = {"mysql": MySQL(), "mongodb": Mongo(), "firestore": Firestore()}
