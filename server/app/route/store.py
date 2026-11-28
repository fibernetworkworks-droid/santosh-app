"""v0.999.254 MAKE PARITY - DATA STORES (Make's Data store app, own code).

A data store is her own small table that every route can read and write between runs: a name, an optional
structure (fields with a type, some required) and records, each with a unique key. It lives in the per-tenant
dhara.db beside the routes.

Step type "store" (field "op"), the Make modules:
  add        Add / replace a record        (key optional: a new id is made; overwrite: false refuses an old key)
  update     Update a record               (fields merged; insert_missing: true makes it when there is none)
  get        Get a record                  (output {exists, key, data})
  exists     Check the existence of a record
  delete     Delete a record
  delete_all Delete all records            (needs confirm: true on the step - nothing is wiped by accident)
  search     Search records                (filter on fields, sort, limit up to 3,200 - Make's own ceiling)
  count      Count records                 (with an optional filter)
  increment  Add to a number field at once (one write; a counter that survives every run)

Writes made by a run are kept in the run's undo list, so the Rollback error directive really takes them back
(Make's ACID data store). Commit, a finished run and the route setting auto_commit end that list.
Limits: 50 stores, 10 MB per store (her choice, default 1 MB), 64 KB per record, 200-character keys.
"""
from __future__ import annotations

import csv
import io
import json
import re
import time
import uuid
from typing import Any

STORES_MAX = 50
SIZE_DEFAULT_KB = 1024
SIZE_MAX_KB = 10 * 1024
RECORD_MAX = 64 * 1024
KEY_MAX = 200
SEARCH_MAX = 3200
FIELDS_MAX = 60
TYPES = ("text", "number", "boolean", "date", "array", "collection", "any")
OPS = ("add", "update", "get", "exists", "delete", "delete_all", "search", "count", "increment")
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


class StoreError(ValueError):
    pass


def _con(tenant: str):
    from ..agent import dhara_tools as D
    con = D._con(tenant)
    con.execute("CREATE TABLE IF NOT EXISTS ds_stores (name TEXT PRIMARY KEY, structure TEXT DEFAULT '[]', "
                "max_kb INTEGER DEFAULT 1024, note TEXT DEFAULT '', created_at REAL, updated_at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS ds_records (store TEXT, key TEXT, data TEXT, created_at REAL, updated_at REAL, "
                "PRIMARY KEY (store, key))")
    return con


def _name(v: Any) -> str:
    n = str(v or "").strip().lower().replace(" ", "_").replace("-", "_")
    if not _NAME.match(n):
        raise StoreError("A data store name is 1-40 letters, digits or _ and starts with a letter, like customers")
    return n


def check_structure(fields: Any) -> list[dict]:
    if fields in (None, "", []):
        return []
    if isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except ValueError:
            raise StoreError("The structure must be a list of fields like [{\"name\": \"email\", \"type\": \"text\"}]")
    if not isinstance(fields, list):
        raise StoreError("The structure must be a list of fields")
    if len(fields) > FIELDS_MAX:
        raise StoreError(f"Up to {FIELDS_MAX} fields in a data store")
    out, seen = [], set()
    for f in fields:
        if isinstance(f, str):
            f = {"name": f}
        if not isinstance(f, dict) or not str(f.get("name") or "").strip():
            raise StoreError("Every field needs a name")
        nm = str(f["name"]).strip()[:60]
        if nm in seen:
            raise StoreError(f"The field '{nm}' is there twice")
        seen.add(nm)
        tp = str(f.get("type") or "text").lower()
        if tp not in TYPES:
            raise StoreError(f"Field '{nm}': the type is one of {', '.join(TYPES)}")
        out.append({"name": nm, "type": tp, "required": bool(f.get("required")), "label": str(f.get("label") or "")[:80]})
    return out


# ---------------------------------------------------------------- the stores
def stores(tenant: str) -> list[dict]:
    con = _con(tenant)
    try:
        rows = con.execute("SELECT s.*, (SELECT COUNT(*) FROM ds_records r WHERE r.store = s.name) AS n, "
                           "(SELECT COALESCE(SUM(LENGTH(r.data)), 0) FROM ds_records r WHERE r.store = s.name) AS bytes "
                           "FROM ds_stores s ORDER BY s.name").fetchall()
    finally:
        con.close()
    return [{"name": r["name"], "structure": json.loads(r["structure"] or "[]"), "max_kb": int(r["max_kb"] or SIZE_DEFAULT_KB),
             "note": r["note"] or "", "records": int(r["n"] or 0), "used_kb": round(int(r["bytes"] or 0) / 1024, 1),
             "updated_at": r["updated_at"]} for r in rows]


def get_store(tenant: str, name: str) -> dict | None:
    n = _name(name)
    for s in stores(tenant):
        if s["name"] == n:
            return s
    return None


def save_store(tenant: str, name: str, structure: Any = None, max_kb: Any = None, note: str = "") -> dict:
    n = _name(name)
    st = check_structure(structure)
    try:
        kb = int(max_kb) if max_kb not in (None, "") else SIZE_DEFAULT_KB
    except (TypeError, ValueError):
        raise StoreError("The size is a number of KB")
    kb = max(16, min(kb, SIZE_MAX_KB))
    con = _con(tenant)
    try:
        had = con.execute("SELECT 1 FROM ds_stores WHERE name = ?", (n,)).fetchone()
        if had is None:
            if con.execute("SELECT COUNT(*) FROM ds_stores").fetchone()[0] >= STORES_MAX:
                raise StoreError(f"Up to {STORES_MAX} data stores")
            con.execute("INSERT INTO ds_stores (name, structure, max_kb, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (n, json.dumps(st), kb, str(note or "")[:300], time.time(), time.time()))
        else:
            con.execute("UPDATE ds_stores SET structure = ?, max_kb = ?, note = ?, updated_at = ? WHERE name = ?",
                        (json.dumps(st), kb, str(note or "")[:300], time.time(), n))
        con.commit()
    finally:
        con.close()
    return get_store(tenant, n)


def drop_store(tenant: str, name: str) -> None:
    n = _name(name)
    con = _con(tenant)
    try:
        con.execute("DELETE FROM ds_records WHERE store = ?", (n,))
        con.execute("DELETE FROM ds_stores WHERE name = ?", (n,))
        con.commit()
    finally:
        con.close()


def _need(tenant: str, name: str) -> dict:
    s = get_store(tenant, name)
    if s is None:
        raise StoreError(f"There is no data store '{name}' - make it on the Data stores page first")
    return s


def _coerce(st: list[dict], data: dict, partial: bool) -> dict:
    if not isinstance(data, dict):
        raise StoreError("A record is an object of field: value")
    if not st:
        return data
    names = {f["name"]: f for f in st}
    extra = [k for k in data if k not in names]
    if extra:
        raise StoreError(f"Not in this data store's structure: {', '.join(extra[:5])}")
    out = {}
    for k, v in data.items():
        tp = names[k]["type"]
        if v in (None, ""):
            out[k] = None
            continue
        try:
            if tp == "number":
                from ..agent.dhara_data import _num
                v = _num(v)
            elif tp == "boolean":
                v = v if isinstance(v, bool) else str(v).strip().lower() in ("true", "yes", "1", "on")
            elif tp == "date":
                from ..agent.dhara_data import _dt, _iso
                v = _iso(_dt(v))
            elif tp == "array" and not isinstance(v, list):
                raise StoreError(f"'{k}' must be a list")
            elif tp == "collection" and not isinstance(v, dict):
                raise StoreError(f"'{k}' must be an object")
            elif tp == "text" and not isinstance(v, str):
                v = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
        except StoreError:
            raise
        except Exception:   # noqa: BLE001
            raise StoreError(f"'{k}' is not a {tp}")
        out[k] = v
    if not partial:
        miss = [f["name"] for f in st if f["required"] and out.get(f["name"]) in (None, "")]
        if miss:
            raise StoreError(f"Required and empty: {', '.join(miss)}")
    return out


def _key(v: Any) -> str:
    k = str(v if v is not None else "").strip()
    if not k:
        raise StoreError("The record needs a key")
    if len(k) > KEY_MAX:
        raise StoreError(f"A key is up to {KEY_MAX} characters")
    return k


def _room(con, s: dict, key: str, blob: str) -> None:
    if len(blob) > RECORD_MAX:
        raise StoreError("A record is over 64 KB")
    used = con.execute("SELECT COALESCE(SUM(LENGTH(data)), 0) FROM ds_records WHERE store = ? AND key != ?",
                       (s["name"], key)).fetchone()[0]
    if int(used) + len(blob) > s["max_kb"] * 1024:
        raise StoreError(f"The data store '{s['name']}' is full ({s['max_kb']} KB) - make it bigger or delete records")


def _row(con, store: str, key: str) -> dict | None:
    r = con.execute("SELECT data FROM ds_records WHERE store = ? AND key = ?", (store, key)).fetchone()
    return None if r is None else json.loads(r["data"] or "{}")


def _write(con, s: dict, key: str, data: dict | None, undo: list | None) -> None:
    before = _row(con, s["name"], key)
    if data is None:
        con.execute("DELETE FROM ds_records WHERE store = ? AND key = ?", (s["name"], key))
    else:
        blob = json.dumps(data, ensure_ascii=False, default=str)
        _room(con, s, key, blob)
        con.execute("INSERT INTO ds_records (store, key, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(store, key) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
                    (s["name"], key, blob, time.time(), time.time()))
    if undo is not None and len(undo) < 5000:
        undo.append([s["name"], key, before])


def _match(rec: dict, f: Any, depth: int = 0) -> bool:
    from ..agent import dhara_tools as D
    if f in (None, {}, ""):
        return True
    if depth > 4 or not isinstance(f, dict):
        return False
    if "all" in f:
        return all(_match(rec, x, depth + 1) for x in (f.get("all") or []))
    if "any" in f:
        return any(_match(rec, x, depth + 1) for x in (f.get("any") or []))
    fld = str(f.get("field") or f.get("left") or "").strip().strip("{}").strip()
    if fld.startswith("record."):
        fld = fld[7:]
    from ..agent.dhara_data import _get
    left = rec.get("key") if fld == "key" else _get(rec.get("data") or {}, fld)
    right = f.get("value", f.get("right"))
    return D._one(left, str(f.get("op") or "eq"), right, bool(f.get("ci")))


def records(tenant: str, name: str, flt: Any = None, sort: str = "", order: str = "asc", limit: int = 100,
            offset: int = 0) -> tuple[list[dict], int]:
    s = _need(tenant, name)
    con = _con(tenant)
    try:
        rows = con.execute("SELECT key, data, created_at, updated_at FROM ds_records WHERE store = ? ORDER BY key",
                           (s["name"],)).fetchall()
    finally:
        con.close()
    recs = [{"key": r["key"], "data": json.loads(r["data"] or "{}"), "created_at": r["created_at"],
             "updated_at": r["updated_at"]} for r in rows]
    hit = [r for r in recs if _match(r, flt)]
    if sort:
        from ..agent.dhara_data import _get
        k = (lambda r: r["key"]) if sort == "key" else (lambda r: _get(r["data"], sort))
        try:
            hit.sort(key=lambda r: (k(r) is None, k(r)), reverse=str(order).lower() == "desc")
        except TypeError:
            hit.sort(key=lambda r: str(k(r)), reverse=str(order).lower() == "desc")
    total = len(hit)
    lim = max(1, min(int(limit or 100), SEARCH_MAX))
    return hit[int(offset or 0):int(offset or 0) + lim], total


def put(tenant: str, name: str, key: Any, data: dict, undo: list | None = None, merge: bool = False) -> dict:
    s = _need(tenant, name)
    k = _key(key)
    con = _con(tenant)
    try:
        cur = _row(con, s["name"], k)
        new = dict(cur or {}) if merge else {}
        new.update(_coerce(s["structure"], data, partial=merge and cur is not None))
        if merge and cur is not None:
            _coerce(s["structure"], new, partial=False)
        _write(con, s, k, new, undo)
        con.commit()
    finally:
        con.close()
    return {"key": k, "data": new}


def remove(tenant: str, name: str, key: Any, undo: list | None = None) -> bool:
    s = _need(tenant, name)
    k = _key(key)
    con = _con(tenant)
    try:
        had = _row(con, s["name"], k) is not None
        if had:
            _write(con, s, k, None, undo)
            con.commit()
    finally:
        con.close()
    return had


def clear(tenant: str, name: str, undo: list | None = None) -> int:
    s = _need(tenant, name)
    con = _con(tenant)
    try:
        rows = con.execute("SELECT key FROM ds_records WHERE store = ?", (s["name"],)).fetchall()
        for r in rows:
            _write(con, s, r["key"], None, undo)
        con.commit()
    finally:
        con.close()
    return len(rows)


def undo_all(tenant: str, undo: list) -> int:
    """Rollback: put back what this run changed, newest first. Returns how many writes were taken back."""
    n = 0
    con = _con(tenant)
    try:
        for store, key, before in reversed(list(undo or [])):
            if before is None:
                con.execute("DELETE FROM ds_records WHERE store = ? AND key = ?", (store, key))
            else:
                con.execute("INSERT INTO ds_records (store, key, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?) "
                            "ON CONFLICT(store, key) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
                            (store, key, json.dumps(before, ensure_ascii=False, default=str), time.time(), time.time()))
            n += 1
        con.commit()
    finally:
        con.close()
    return n


# ---------------------------------------------------------------- the step
def validate(step: dict, sid: str) -> None:
    from ..agent.tools import ToolError
    op = str(step.get("op") or "")
    if op not in OPS:
        raise ToolError(f"Step '{sid}': a data store step needs op = one of: {', '.join(OPS)}")
    if not str(step.get("store") or "").strip():
        raise ToolError(f"Step '{sid}': name the data store")
    if "{{" not in str(step["store"]):
        try:
            _name(step["store"])
        except StoreError as e:
            raise ToolError(f"Step '{sid}': {e}")
    if op in ("get", "exists", "delete", "increment") and step.get("key") in (None, ""):
        raise ToolError(f"Step '{sid}': {op} needs the record's key")
    if op in ("update",) and step.get("key") in (None, ""):
        raise ToolError(f"Step '{sid}': update needs the record's key")
    if op in ("add", "update") and not isinstance(step.get("data"), (dict, str)):
        raise ToolError(f"Step '{sid}': {op} needs data - an object of field: value")
    if op == "delete_all" and step.get("confirm") is not True:
        raise ToolError(f"Step '{sid}': deleting every record needs confirm: true on the step")
    if op == "increment" and not str(step.get("field") or "").strip():
        raise ToolError(f"Step '{sid}': increment needs the number field to add to")
    if step.get("limit") not in (None, "") and "{{" not in str(step.get("limit")):
        try:
            if not 1 <= int(step["limit"]) <= SEARCH_MAX:
                raise ValueError
        except (TypeError, ValueError):
            raise ToolError(f"Step '{sid}': limit is 1-{SEARCH_MAX}")


def run(tenant: str, step: dict, ctx: dict, resolve) -> Any:
    R = (lambda v: resolve(v, ctx))
    op = str(step.get("op"))
    name = str(R(step.get("store")) or "")
    undo = None if ctx.get("_test_step") else ctx.setdefault("_store_undo", [])
    data = R(step.get("data")) if step.get("data") is not None else {}
    if isinstance(data, str):
        try:
            data = json.loads(data) if data.strip() else {}
        except ValueError:
            raise StoreError("data must be an object of field: value")
    if op == "add":
        key = R(step.get("key"))
        key = str(uuid.uuid4()) if key in (None, "") else key
        if step.get("overwrite") is False or str(step.get("overwrite")).lower() == "false":
            con = _con(tenant)
            try:
                if _row(con, _name(name), _key(key)) is not None:
                    raise StoreError(f"A record with the key '{key}' is already there (overwrite is off)")
            finally:
                con.close()
        return put(tenant, name, key, data, undo)
    if op == "update":
        key = _key(R(step.get("key")))
        con = _con(tenant)
        try:
            cur = _row(con, _name(name), key)
        finally:
            con.close()
        if cur is None and not step.get("insert_missing"):
            raise StoreError(f"There is no record '{key}' to update (turn on 'Make it if missing')")
        return put(tenant, name, key, data, undo, merge=True)
    if op in ("get", "exists"):
        key = _key(R(step.get("key")))
        _need(tenant, name)
        con = _con(tenant)
        try:
            cur = _row(con, _name(name), key)
        finally:
            con.close()
        if op == "exists":
            return {"exists": cur is not None, "key": key}
        return {"exists": cur is not None, "key": key, "data": cur}
    if op == "delete":
        return {"deleted": remove(tenant, name, R(step.get("key")), undo), "key": str(R(step.get("key")))}
    if op == "delete_all":
        return {"deleted": clear(tenant, name, undo)}
    if op in ("search", "count"):
        flt = R(step.get("filter")) if step.get("filter") is not None else None
        lim = step.get("limit")
        lim = int(R(lim)) if lim not in (None, "") else (SEARCH_MAX if op == "count" else 100)
        rows, total = records(tenant, name, flt, str(R(step.get("sort")) or ""), str(step.get("order") or "asc"),
                              lim if op == "search" else SEARCH_MAX)
        if op == "count":
            return {"count": total}
        return [{"key": r["key"], **(r["data"] or {})} for r in rows]
    if op == "increment":
        key = _key(R(step.get("key")))
        fld = str(R(step.get("field")))
        from ..agent.dhara_data import _num
        by = _num(R(step.get("by")) if step.get("by") not in (None, "") else 1)
        s = _need(tenant, name)
        con = _con(tenant)
        try:
            con.execute("BEGIN IMMEDIATE")
            cur = _row(con, s["name"], key) or {}
            try:
                v = _num(cur.get(fld) or 0) + by
            except Exception:   # noqa: BLE001
                raise StoreError(f"'{fld}' is not a number in record '{key}'")
            new = dict(cur)
            new[fld] = v
            _coerce(s["structure"], {fld: v}, partial=True)
            _write(con, s, key, new, undo)
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
        return {"key": key, "value": v, "data": new}
    raise StoreError("Unknown data store step")


# ---------------------------------------------------------------- CSV in and out (the page)
def export_csv(tenant: str, name: str) -> str:
    s = _need(tenant, name)
    rows, _ = records(tenant, name, None, "", "asc", SEARCH_MAX)
    cols = [f["name"] for f in s["structure"]] or sorted({k for r in rows for k in (r["data"] or {})})
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["key"] + cols)
    for r in rows:
        w.writerow([r["key"]] + [(json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else "" if v is None else v)
                                 for v in (r["data"].get(c) for c in cols)])
    return buf.getvalue()


def import_csv(tenant: str, name: str, text: str) -> dict:
    """Rows of a CSV (first line = field names; a 'key' column, else new keys). Checked against the structure; the
    first bad row stops it with its line number, nothing half-written."""
    s = _need(tenant, name)
    rd = list(csv.DictReader(io.StringIO(str(text or ""))))
    if len(rd) > SEARCH_MAX * 3:
        raise StoreError("Up to 9,600 rows at a time")
    con = _con(tenant)
    n = 0
    try:
        for i, row in enumerate(rd, start=2):
            key = (row.pop("key", "") or "").strip() or str(uuid.uuid4())
            data = {k: v for k, v in row.items() if k is not None}
            for f in s["structure"]:
                if f["type"] in ("array", "collection") and isinstance(data.get(f["name"]), str) and data[f["name"]].strip():
                    try:
                        data[f["name"]] = json.loads(data[f["name"]])
                    except ValueError:
                        raise StoreError(f"Line {i}: '{f['name']}' is not valid JSON")
            try:
                clean = _coerce(s["structure"], data, partial=False)
            except StoreError as e:
                raise StoreError(f"Line {i}: {e}")
            _write(con, s, _key(key), clean, None)
            n += 1
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return {"imported": n}
