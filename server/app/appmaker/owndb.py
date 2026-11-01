"""v0.396 APNA DATABASE (App Sahayak Pillar B, own database per app): an app's data runs in HER OWN database -
Supabase, Neon, AWS RDS / Aurora, Google Cloud SQL / AlloyDB, Azure, DigitalOcean, Aiven, Render, Railway, Timescale,
CockroachDB, YugabyteDB ... any PostgreSQL-wire database she connects (Profile > Postgres database, v0.147: typed only
in the app, sealed, public host only with the checked IP pinned, SSL required).

  * Her tables: one SCHEMA per app (`hoola_a_0001`), one real TABLE per list with real column types (number -> numeric,
    date -> date, yes / no -> boolean, the rest text), an index on every link, `_hoola_accounts` (never a password hash),
    `_hoola_<name>` for Hoola's own lists (udhaar, approvals, chat), `_hoola_deleted` (what was deleted outside).
    She can query them, build dashboards, add her own RLS / users - they are hers.
  * Two modes:
      primary  - her database is where the data LIVES: every write from the app reaches it inside the same request
                 (Hoola's commit waits for hers; if her database cannot be reached, the write is refused with a plain
                 message - nothing is half-saved), and what she edits there (Supabase table editor, SQL, another tool)
                 flows back into the app within a minute, checked like any app input, with the app's logic run on it.
      mirror   - Hoola stays the main copy; every write is sent to her database within a minute (her database being
                 down never stops her app). A read copy for reports, BI, other software.
  * Linking is HER TAP: a backup first, then her tables, then every row copied, then the counts compared - only then
    "live". Unlinking stops the sync; the data stays in BOTH places. Field-level updates (only the columns that changed),
    so an edit she makes outside and an edit in the app on other fields of the same row both survive.
Text in her database is DATA, never instructions; Hoola's own control values (stock taken, coupon use, assignment ...)
never come back from outside."""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from ..db import now, session
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"pushed": 0, "push_failed": 0, "pulled": 0, "pull_refused": 0, "deleted_outside": 0, "linked": 0}
SKIP = {"_audit", "_refs_v1", "_push"}
TYPES = {"number": "numeric", "date": "date", "yes_no": "boolean"}
BATCH = 500
MODES = ("primary", "mirror")

# the PostgreSQL-wire databases she can bring (how to copy the connection string; every one = the same code path)
PROVIDERS = [
    {"kind": "postgres", "key": "supabase", "name": "Supabase", "how": "Project > Connect > Session pooler (IPv4) URI, port 5432; or Direct connection",
     "note": "Use the Session pooler (5432) - the Transaction pooler (6543) works too (Hoola never uses prepared statements)."},
    {"kind": "postgres", "key": "neon", "name": "Neon", "how": "Dashboard > Connection details > Connection string (pooled or direct)", "note": ""},
    {"kind": "postgres", "key": "aws_rds", "name": "Amazon RDS for PostgreSQL", "how": "RDS > Databases > Connectivity: endpoint + port; your master or app user",
     "note": "Allow Hoola's server IP in the security group (inbound 5432)."},
    {"kind": "postgres", "key": "aws_aurora", "name": "Amazon Aurora PostgreSQL", "how": "Cluster writer endpoint + port", "note": "Writer endpoint, not reader."},
    {"kind": "postgres", "key": "gcp_cloudsql", "name": "Google Cloud SQL (PostgreSQL)", "how": "Instance > Public IP + an authorised network", "note": "Add Hoola's server IP under Authorised networks."},
    {"kind": "postgres", "key": "gcp_alloydb", "name": "Google AlloyDB", "how": "Public IP on the primary instance", "note": ""},
    {"kind": "postgres", "key": "azure", "name": "Azure Database for PostgreSQL", "how": "Server > Connection strings (psql) + firewall rule", "note": "Firewall: allow Hoola's server IP."},
    {"kind": "postgres", "key": "digitalocean", "name": "DigitalOcean Managed PostgreSQL", "how": "Cluster > Connection details > Connection string", "note": "Trusted sources: add Hoola's server IP."},
    {"kind": "postgres", "key": "aiven", "name": "Aiven for PostgreSQL", "how": "Service > Overview > Service URI", "note": ""},
    {"kind": "postgres", "key": "render", "name": "Render PostgreSQL", "how": "Database > External Database URL", "note": ""},
    {"kind": "postgres", "key": "railway", "name": "Railway PostgreSQL", "how": "Postgres service > Variables > DATABASE_PUBLIC_URL", "note": ""},
    {"kind": "postgres", "key": "timescale", "name": "Timescale Cloud", "how": "Service > Connection info (service URL)", "note": ""},
    {"kind": "postgres", "key": "crunchy", "name": "Crunchy Bridge", "how": "Cluster > Connection > URL", "note": ""},
    {"kind": "postgres", "key": "tembo", "name": "Tembo", "how": "Instance > Connection string", "note": ""},
    {"kind": "postgres", "key": "xata", "name": "Xata (Postgres)", "how": "Database > Connect > PostgreSQL connection string", "note": ""},
    {"kind": "postgres", "key": "nile", "name": "Nile", "how": "Database > Connection string", "note": ""},
    {"kind": "postgres", "key": "heroku", "name": "Heroku Postgres", "how": "Data > Settings > View credentials (URI)", "note": ""},
    {"kind": "postgres", "key": "fly", "name": "Fly.io Postgres", "how": "fly postgres connect / public IPv4 + flycast", "note": "Needs a public address."},
    {"kind": "postgres", "key": "vercel", "name": "Vercel Postgres (Neon)", "how": "Storage > your database > .env.local POSTGRES_URL_NON_POOLING", "note": ""},
    {"kind": "postgres", "key": "koyeb", "name": "Koyeb Postgres", "how": "Database > Connection details", "note": ""},
    {"kind": "postgres", "key": "scaleway", "name": "Scaleway Managed PostgreSQL", "how": "Instance > Connection", "note": ""},
    {"kind": "postgres", "key": "ovh", "name": "OVHcloud Managed PostgreSQL", "how": "Service > General information > URI", "note": ""},
    {"kind": "postgres", "key": "alibaba", "name": "Alibaba Cloud ApsaraDB for PostgreSQL", "how": "Instance > Database connection (public endpoint)", "note": ""},
    {"kind": "postgres", "key": "tencent", "name": "Tencent Cloud PostgreSQL", "how": "Instance > Public network address", "note": ""},
    {"kind": "postgres", "key": "huawei", "name": "Huawei Cloud RDS for PostgreSQL", "how": "Instance > EIP address", "note": ""},
    {"kind": "postgres", "key": "cockroach", "name": "CockroachDB Cloud", "how": "Cluster > Connect > General connection string",
     "note": "PostgreSQL-compatible; triggers for outside edits need CockroachDB 24.3+ (else use mirror mode)."},
    {"kind": "postgres", "key": "yugabyte", "name": "YugabyteDB Aeon", "how": "Cluster > Connect > connection string", "note": "PostgreSQL-compatible."},
    {"kind": "postgres", "key": "selfhost", "name": "Her own PostgreSQL (VPS / office server)", "how": "postgresql://user:password@public-host:5432/db?sslmode=require",
     "note": "A public address with SSL; a private / LAN database is refused."},
]
PROVIDERS += [
    {"kind": "mysql", "key": "planetscale", "name": "PlanetScale (MySQL)", "how": "Database > Connect > Connect with: General (host, username, password) -> mysql://user:password@host/db",
     "note": "TLS is always on. No triggers needed: Hoola uses a timestamp column + its own fingerprint."},
    {"kind": "mysql", "key": "tidb", "name": "TiDB Cloud (Serverless / Dedicated)", "how": "Cluster > Connect > General -> mysql://user:password@gateway...:4000/db", "note": ""},
    {"kind": "mysql", "key": "mysql_rds", "name": "Amazon RDS / Aurora MySQL", "how": "Endpoint + port 3306; allow Hoola's server IP in the security group", "note": ""},
    {"kind": "mysql", "key": "mysql_gcp", "name": "Google Cloud SQL for MySQL", "how": "Public IP + Authorised networks", "note": ""},
    {"kind": "mysql", "key": "mysql_azure", "name": "Azure Database for MySQL", "how": "Server > Connect + firewall rule", "note": ""},
    {"kind": "mysql", "key": "mysql_do", "name": "DigitalOcean Managed MySQL", "how": "Cluster > Connection details", "note": ""},
    {"kind": "mysql", "key": "mariadb", "name": "MariaDB / MySQL on her own server", "how": "mysql://user:password@public-host:3306/db (TLS on)", "note": ""},
    {"kind": "mysql", "key": "aiven_mysql", "name": "Aiven for MySQL", "how": "Service > Overview > Service URI", "note": ""},
    {"kind": "mongodb", "key": "atlas", "name": "MongoDB Atlas", "how": "Database > Connect > Drivers -> mongodb+srv://user:password@cluster.../dbname",
     "note": "Network Access: allow Hoola's server IP. Outside edits are seen live through change streams."},
    {"kind": "mongodb", "key": "mongo_self", "name": "MongoDB on her own server", "how": "mongodb://user:password@public-host:27017/db?tls=true",
     "note": "A replica set gives live change streams; a single server is checked by a slower scan."},
    {"kind": "mongodb", "key": "cosmos_mongo", "name": "Azure Cosmos DB for MongoDB", "how": "Connection strings > Primary connection string", "note": ""},
    {"kind": "mongodb", "key": "documentdb", "name": "Amazon DocumentDB", "how": "Cluster > Connectivity (tls=true)", "note": "Needs a public endpoint / SSH tunnel host."},
    {"kind": "firestore", "key": "firebase", "name": "Firebase (Cloud Firestore)", "how": "Project settings > Service accounts > Generate new private key -> paste the whole JSON",
     "note": "Hoola writes only under hoola_apps/<app>/...; her app's own Firestore data is never touched."},
]


class OwnDbError(W.AppError):
    pass


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


# ---------------------------------------------------------------- the link (cached for the commit hook)
_CFG: dict[str, tuple[float, dict | None]] = {}


def cfg(r_or_id: AppProject | str, fresh: bool = False) -> dict | None:
    """The app's link {conn, tenant, mode, schema, status, cursor...} or None. Cached 20 s (the hook runs on every commit)."""
    aid = r_or_id if isinstance(r_or_id, str) else r_or_id.id
    hit = _CFG.get(aid)
    if hit and not fresh and time.time() - hit[0] < 20:
        return hit[1]
    from .. import db as _db
    out = None
    if _db._engine is not None:
        with _db._engine.connect() as c:                 # its own connection: safe from inside another session's commit
            row = c.execute(select(AppProject.backend, AppProject.tenant_id).where(AppProject.id == aid)).first()
        if row is not None:
            o = (_j(row[0], {}) or {}).get("owndb")
            if isinstance(o, dict) and o.get("status") in ("copying", "live"):
                out = {**o, "tenant": row[1]}
    _CFG[aid] = (time.time(), out)
    return out


def _forget(aid: str) -> None:
    _CFG.pop(aid, None)


def schema_name(r: AppProject) -> str:
    return "hoola_" + re.sub(r"[^a-z0-9]+", "_", str(r.number or r.id).lower()).strip("_")[:40]


def _ident(name: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", name):
        raise OwnDbError(f"naam '{name}' database mein nahi chalega")
    return '"' + name + '"'


def table_of(coll: str) -> str:
    return ("_hoola_" + coll.lstrip("_")) if coll.startswith("_") else coll


# ---------------------------------------------------------------- connections (a small pool per app)
_POOL: dict[str, list] = {}
_PLOCK = threading.Lock()


def _kind(o: dict) -> str:
    return str(o.get("kind") or "postgres")


def _drv(o: dict):
    """The driver for a non-Postgres database (MySQL family / MongoDB / Firestore); None = Postgres (this module)."""
    if _kind(o) == "postgres":
        return None
    from . import owndb_drivers as DRV
    return DRV.DRIVERS[_kind(o)]


def _secret(o: dict) -> tuple[dict, dict]:
    from . import owndb_conns as OC
    return OC.secret_of(o["tenant"], o["conn"])


def _dsn(o: dict) -> dict:
    from ..pgdb import service as PG
    c, d = PG._dsn(o["tenant"], o["conn"])
    return d


class _Conn:
    def __init__(self, aid: str, o: dict, timeout_s: int = 15):
        self.aid, self.o, self.t = aid, o, timeout_s
        self.c = None

    def __enter__(self):
        with _PLOCK:
            pool = _POOL.setdefault(self.aid, [])
            while pool and self.c is None:
                c = pool.pop()
                if not c.closed and c.info.transaction_status == 0:
                    self.c = c
                else:
                    try:
                        c.close()
                    except Exception:            # noqa: BLE001
                        pass
        if self.c is None:
            import psycopg

            from ..pgdb import service as PG
            d = _dsn(self.o)
            try:
                self.c = psycopg.connect(**PG._connect_kw(d), autocommit=False, prepare_threshold=None,
                                         keepalives=1, keepalives_idle=30)
            except psycopg.Error as e:
                raise OwnDbError(PG._err(e, d), 503)
        cur = self.c.cursor()
        cur.execute(f"SET LOCAL statement_timeout = {int(self.t * 1000)}")
        cur.execute("SET LOCAL lock_timeout = 8000")
        cur.execute("SELECT set_config('hoola.by', 'hoola', true)")      # her triggers mark these rows as Hoola's
        return self.c

    def __exit__(self, et, ev, tb):
        c, self.c = self.c, None
        if c is None:
            return False
        try:
            if et is None:
                c.commit()
            else:
                c.rollback()
        except Exception:                        # noqa: BLE001
            try:
                c.close()
            except Exception:                    # noqa: BLE001
                pass
            return False
        with _PLOCK:
            pool = _POOL.setdefault(self.aid, [])
            if len(pool) < 4 and not c.closed:
                pool.append(c)
            else:
                c.close()
        return False


def close_pool(aid: str) -> None:
    with _PLOCK:
        for c in _POOL.pop(aid, []):
            try:
                c.close()
            except Exception:                    # noqa: BLE001
                pass


# ---------------------------------------------------------------- her tables
TOUCH = """CREATE OR REPLACE FUNCTION {s}._hoola_touch() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW._updated := clock_timestamp();
  NEW._by := coalesce(nullif(current_setting('hoola.by', true), ''), 'outside');
  IF NEW._by = 'outside' THEN
    NEW._out := clock_timestamp();       -- changed OUTSIDE Hoola: a later Hoola write never hides it
  END IF;
  RETURN NEW;
END $$"""
GONE = """CREATE OR REPLACE FUNCTION {s}._hoola_gone() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO {s}._hoola_deleted(tbl, id, by) VALUES (TG_TABLE_NAME, OLD.id,
    coalesce(nullif(current_setting('hoola.by', true), ''), 'outside'));
  RETURN OLD;
END $$"""
NEW_ID = "('row_' || substr(md5(random()::text || clock_timestamp()::text), 1, 12))"


def _lists(r: AppProject) -> dict[str, list[dict]]:
    from . import backend as BE
    return {c["key"]: [f for f in c["fields"]] for c in BE.schema(r)["collections"]}


def ensure_schema(r: AppProject, conn, s: str) -> dict[str, int]:
    """Her schema + a table per list (+ new columns for new fields) - additive, safe to run again."""
    S = _ident(s)
    cur = conn.cursor()
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {S}")
    cur.execute(f"CREATE TABLE IF NOT EXISTS {S}._hoola_meta (key text PRIMARY KEY, value text NOT NULL DEFAULT '')")
    cur.execute(f"CREATE TABLE IF NOT EXISTS {S}._hoola_deleted (seq bigserial PRIMARY KEY, tbl text NOT NULL, id text NOT NULL, "
                f"by text NOT NULL DEFAULT 'outside', at timestamptz NOT NULL DEFAULT clock_timestamp())")
    cur.execute(TOUCH.format(s=S))
    cur.execute(GONE.format(s=S))
    cur.execute(f"CREATE TABLE IF NOT EXISTS {S}._hoola_accounts (id text PRIMARY KEY, email text NOT NULL DEFAULT '', "
                f"name text NOT NULL DEFAULT '', role text NOT NULL DEFAULT 'member', created_at timestamptz)")
    made = {"tables": 0, "columns": 0}
    for coll, fields in _lists(r).items():
        T = _ident(coll)
        cur.execute(f"CREATE TABLE IF NOT EXISTS {S}.{T} (id text PRIMARY KEY DEFAULT {NEW_ID}, owner_id text NOT NULL DEFAULT '', "
                    f"created_at timestamptz NOT NULL DEFAULT now(), _updated timestamptz NOT NULL DEFAULT clock_timestamp(), "
                    f"_by text NOT NULL DEFAULT 'outside', _hoola jsonb NOT NULL DEFAULT '{{}}'::jsonb)")
        made["tables"] += 1
        cur.execute(f"ALTER TABLE {S}.{T} ADD COLUMN IF NOT EXISTS _out timestamptz")
        for f in fields:
            cur.execute(f"ALTER TABLE {S}.{T} ADD COLUMN IF NOT EXISTS {_ident(f['key'])} {TYPES.get(f['type'], 'text')}")
            made["columns"] += 1
            if f.get("type") == "ref":
                cur.execute(f"CREATE INDEX IF NOT EXISTS {_ident(('ix_' + coll + '_' + f['key'])[:60])} ON {S}.{T} ({_ident(f['key'])})")
        cur.execute(f"CREATE INDEX IF NOT EXISTS {_ident(('ix_' + coll + '__out')[:60])} ON {S}.{T} (_out)")
        cur.execute(f"DROP TRIGGER IF EXISTS _hoola_touch ON {S}.{T}")
        cur.execute(f"CREATE TRIGGER _hoola_touch BEFORE INSERT OR UPDATE ON {S}.{T} FOR EACH ROW EXECUTE FUNCTION {S}._hoola_touch()")
        cur.execute(f"DROP TRIGGER IF EXISTS _hoola_gone ON {S}.{T}")
        cur.execute(f"CREATE TRIGGER _hoola_gone AFTER DELETE ON {S}.{T} FOR EACH ROW EXECUTE FUNCTION {S}._hoola_gone()")
    be = _j(r.backend, {})
    cur.execute(f"INSERT INTO {S}._hoola_meta(key, value) VALUES ('app', %s), ('schema_rev', %s) ON CONFLICT (key) DO UPDATE "
                "SET value = EXCLUDED.value", (f"{r.name} ({r.number})", str(be.get("rev") or 0)))
    return made


def _generic(conn, s: str, coll: str) -> None:
    S, T = _ident(s), _ident(table_of(coll))
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {S}.{T} (id text PRIMARY KEY, owner_id text NOT NULL DEFAULT '', created_at timestamptz, "
                f"_updated timestamptz NOT NULL DEFAULT clock_timestamp(), _by text NOT NULL DEFAULT 'outside', "
                f"data jsonb NOT NULL DEFAULT '{{}}'::jsonb)")


# ---------------------------------------------------------------- values both ways
def _to_col(f: dict, v: Any) -> Any:
    if v is None or v == "":
        return None
    t = f.get("type")
    if t == "number":
        try:
            return Decimal(str(v))
        except Exception:                        # noqa: BLE001
            return None
    if t == "yes_no":
        return bool(v) if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "haan")
    if t == "date":
        try:
            return date.fromisoformat(str(v)[:10])
        except ValueError:
            return None
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def _from_col(f: dict, v: Any) -> Any:
    if v is None:
        return "" if f.get("type") != "yes_no" else False
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10] if f.get("type") == "date" else v.isoformat()
    return v


def _row_cols(coll: str, fields: list[dict], data: dict) -> tuple[dict, dict]:
    """Hoola row data -> (her typed columns, Hoola's own `_` values kept in _hoola)."""
    keys = {f["key"]: f for f in fields}
    cols = {k: _to_col(f, data.get(k)) for k, f in keys.items()}
    own = {k: v for k, v in data.items() if k not in keys}
    return cols, own


# ---------------------------------------------------------------- push (Hoola -> her database)
def push(r: AppProject, o: dict, entries: list[tuple], conn=None) -> int:
    """entries = [(op, row_id, coll, owner, before_json, after_json, created_iso)] -> upserts / deletes in HER tables.
    Updates write only the columns that changed (field-level: her outside edits to other fields survive)."""
    if not entries:
        return 0
    lists = _lists(r)
    d = _drv(o)
    if d is not None:                                    # v0.404 MySQL family / MongoDB / Firestore
        try:
            n = d.push(r, o, lists, [e for e in entries if e[2] not in SKIP])
        except Exception as e:
            from . import owndb_conns as OC
            raise OwnDbError(OC.mask(str(e)), 503)
        STATS["pushed"] += n
        return n
    s = o["schema"]
    S = _ident(s)

    def go(c):
        cur = c.cursor()
        done = 0
        for op, rid, coll, owner, before, after, created in entries:
            if coll in SKIP:
                continue
            T = _ident(table_of(coll))
            if op == "delete":
                cur.execute(f"DELETE FROM {S}.{T} WHERE id = %s", (rid,))
                done += 1
                continue
            new = _j(after, {})
            if coll not in lists:                     # Hoola's own lists: one jsonb row
                _generic(c, s, coll)
                cur.execute(f"INSERT INTO {S}.{T} (id, owner_id, created_at, data) VALUES (%s, %s, %s, %s::jsonb) "
                            "ON CONFLICT (id) DO UPDATE SET owner_id = EXCLUDED.owner_id, data = EXCLUDED.data",
                            (rid, owner or "", created or None, json.dumps(new, ensure_ascii=False)))
                done += 1
                continue
            cols, own = _row_cols(coll, lists[coll], new)
            if op == "update":
                old = _j(before, {})
                ocols, oown = _row_cols(coll, lists[coll], old)
                changed = [k for k in cols if cols[k] != ocols.get(k)]
                own_changed = own != oown
            else:
                changed, own_changed = list(cols), True
            names = ["id", "owner_id", "created_at", "_hoola"] + list(cols)
            vals = [rid, owner or "", created or None, json.dumps(own, ensure_ascii=False)] + [cols[k] for k in cols]
            upd = [f"{_ident(k)} = EXCLUDED.{_ident(k)}" for k in changed] + (["_hoola = EXCLUDED._hoola"] if own_changed else [])
            upd = upd or ["owner_id = EXCLUDED.owner_id"]
            ph = "%s, %s, %s, %s::jsonb" + (", " + ", ".join(["%s"] * len(cols)) if cols else "")
            cur.execute(f"INSERT INTO {S}.{T} ({', '.join(_ident(n) for n in names)}) VALUES ({ph}) "
                        f"ON CONFLICT (id) DO UPDATE SET {', '.join(upd)}", vals)
            done += 1
        return done
    if conn is not None:
        n = go(conn)
    else:
        with _Conn(r.id, o) as c:
            n = go(c)
    STATS["pushed"] += n
    return n


_ACC: dict[str, int] = {}


def push_accounts(r: AppProject, o: dict, conn, force: bool = False) -> int:
    """The app's accounts (id, e-mail, name, role - never a password hash), only when they changed."""
    with session() as s:
        mems = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == "app:" + r.id)).all()
        rows = [(m.id, m.email, m.name, m.role, m.created_at) for m in mems]
    sig = hash(tuple((a, b, c, d) for a, b, c, d, _ in rows))
    if not force and _ACC.get(r.id) == sig:
        return 0
    _ACC[r.id] = sig
    if _drv(o) is not None:
        _drv(o).accounts(r, o, rows)
        return len(rows)
    S = _ident(o["schema"])
    cur = conn.cursor()
    for x in rows:
        cur.execute(f"INSERT INTO {S}._hoola_accounts (id, email, name, role, created_at) VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, name = EXCLUDED.name, role = EXCLUDED.role", x)
    cur.execute(f"DELETE FROM {S}._hoola_accounts WHERE NOT (id = ANY(%s))", ([x[0] for x in rows],))
    return len(rows)


# the commit hook: in PRIMARY mode Hoola's commit waits for her database
@event.listens_for(Session, "before_commit")
def _write_through(sess: Session) -> None:
    if sess.info.get("owndb_off"):
        return
    try:
        sess.flush()                                     # the journal hook runs here and fills sess.info["owndb"]
    except Exception:                                    # noqa: BLE001 - the commit itself will raise it
        return
    todo = sess.info.pop("owndb", None)
    if not todo:
        return
    by_app: dict[str, list[tuple]] = {}
    marks: dict[str, list] = {}
    for aid, entry, j in todo:
        by_app.setdefault(aid, []).append(entry)
        if j is not None:
            marks.setdefault(aid, []).append(j)
    for aid, entries in by_app.items():
        o = cfg(aid)
        if not o or o.get("mode") != "primary" or o.get("status") != "live":
            continue
        with session() as s2:
            r = s2.get(AppProject, aid)
            s2.expunge(r)
        try:
            push(r, o, entries)
            for j in marks.get(aid, []):                 # the catch-up never sends these again (it would undo her
                j.pushed = True                          # outside edits made in between)
        except Exception as e:                           # noqa: BLE001 - refuse the write; nothing is half-saved
            STATS["push_failed"] += 1
            log.warning("own database write-through failed for %s: %s", aid, e)
            _note_error(aid, str(e))
            raise OwnDbError("Aapka database (" + str(o.get("label") or "database") + ") abhi jawab nahi de raha; yeh entry "
                             "save nahi hui. Thodi der baad dobara koshish kijiye.", 503)


def stash(sess: Session, site: str, entry: tuple, journal=None) -> None:
    """Called by the journal hook for every app-row write: queued for the write-through at commit."""
    if sess.info.get("owndb_off") or not site.startswith("app:"):
        return
    aid = site[4:]
    o = cfg(aid)
    if o and o.get("mode") == "primary" and o.get("status") == "live":
        sess.info.setdefault("owndb", []).append((aid, entry, journal))


def _note_error(aid: str, err: str) -> None:
    try:
        from . import backend as BE
        with session() as s:
            r = s.get(AppProject, aid)
            s.expunge(r)
        BE.patch_backend(r, fn=lambda b: isinstance(b.get("owndb"), dict) and b["owndb"].update(
            {"last_error": err[:300], "error_at": now().isoformat()}))
    except Exception:                                    # noqa: BLE001
        log.debug("owndb note error", exc_info=True)


# ---------------------------------------------------------------- pull (her edits outside -> the app)
def pull(r: AppProject, o: dict) -> dict[str, int]:
    """Rows she inserted / changed / deleted OUTSIDE Hoola since the last look -> the app (validated, logic run)."""
    from .logic import engine as LE
    lists = _lists(r)
    S = _ident(o["schema"])
    cur_pull = dict(o.get("pull") or {})
    got: dict[str, list] = {}
    gone: list = []
    dseq = int(o.get("pull_deleted") or 0)
    drv = _drv(o)
    if drv is not None:                                  # v0.404: fingerprint / change stream / listener per kind
        got, pairs = drv.outside(r, o, lists, cur_pull)
        gone = [(0, coll, rid) for coll, rid in pairs]
    else:
        with _Conn(r.id, o) as c:
            cur = c.cursor()
            for coll, fields in lists.items():
                since = cur_pull.get(coll) or "1970-01-01T00:00:00+00:00"
                cols = ["id", "owner_id", "created_at", "_out"] + [f["key"] for f in fields]
                cur.execute(f"SELECT {', '.join(_ident(x) for x in cols)} FROM {S}.{_ident(coll)} WHERE _out > %s "
                            f"ORDER BY _out LIMIT {BATCH}", (since,))
                rows = cur.fetchall()
                if rows:
                    got[coll] = [dict(zip(cols, x)) for x in rows]
            cur.execute(f"SELECT seq, tbl, id FROM {S}._hoola_deleted WHERE by = 'outside' AND seq > %s ORDER BY seq LIMIT {BATCH}", (dseq,))
            gone = cur.fetchall()
    out = {"changed": 0, "created": 0, "deleted": 0, "refused": 0}
    site = "app:" + r.id
    sch_colls = {c: {f["key"]: f for f in fs} for c, fs in lists.items()}
    from . import backend as BE
    cc_of = {c["key"]: c for c in BE.schema(r)["collections"]}
    owner = W.Who(owner=True)
    for coll, rows in got.items():
        for x in rows:
            if "_out" in x:
                cur_pull[coll] = x["_out"].isoformat() if isinstance(x["_out"], datetime) else str(x["_out"])
            rid = str(x["id"])
            if not re.fullmatch(r"row_[0-9a-f]{12}", rid):
                out["refused"] += 1
                LE.audit(r, "own_db_refused", coll=coll, row=rid[:40], what="outside row id not a Hoola id")
                continue
            vals = {k: _from_col(f, x.get(k)) for k, f in sch_colls[coll].items()}
            with session() as s:
                s.info["owndb_off"] = True                     # never echo it straight back through the write-through
                row = s.get(W.SiteAppRow, rid)
                if row is not None and (row.site_id != site or row.coll != coll):
                    out["refused"] += 1
                    continue
                old = _j(row.data, {}) if row is not None else None
                try:
                    if row is None:
                        clean = W._clean(cc_of[coll], vals, owner)
                    else:
                        changed = {k: v for k, v in vals.items() if old.get(k, "") != v}
                        clean = W._clean(cc_of[coll], changed, owner, partial=True)
                except W.AppError as e:
                    out["refused"] += 1
                    STATS["pull_refused"] += 1
                    LE.audit(r, "own_db_refused", coll=coll, row=rid, what=f"outside value refused: {e}")
                    continue
                if row is None:
                    made_at = x.get("created_at")
                    if isinstance(made_at, str):
                        try:
                            made_at = datetime.fromisoformat(made_at)
                        except ValueError:
                            made_at = None
                    s.add(W.SiteAppRow(id=rid, site_id=site, coll=coll, owner=str(x.get("owner_id") or ""),
                                       data=json.dumps(clean, ensure_ascii=False),
                                       created_at=made_at if isinstance(made_at, datetime) else now(), updated_at=now()))
                    out["created"] += 1
                elif clean:
                    d = {**old, **clean}                        # Hoola's own `_` values stay Hoola's
                    row.data, row.updated_at = json.dumps(d, ensure_ascii=False), now()
                    out["changed"] += 1
                else:
                    continue
            STATS["pulled"] += 1
            LE.audit(r, "own_db_in", coll=coll, row=rid, by="her database", what="edited outside Hoola")
            try:
                if old is None:
                    LE.after_create(r, coll, rid, owner)
                else:
                    LE.after_update(r, coll, rid, {**old, "id": rid}, None)
            except Exception:                                   # noqa: BLE001
                log.debug("logic after outside edit", exc_info=True)
    for seq, tbl, rid in gone:
        dseq = max(dseq, int(seq))
        coll = tbl if tbl in lists else None
        if coll is None:
            continue
        with session() as s:
            s.info["owndb_off"] = True
            row = s.get(W.SiteAppRow, rid)
            if row is None or row.site_id != site or row.coll != coll:
                continue
            d = {**_j(row.data, {}), "id": rid, "owner_id": row.owner}
            s.delete(row)
        out["deleted"] += 1
        STATS["deleted_outside"] += 1
        LE.audit(r, "own_db_in", coll=coll, row=rid, by="her database", what="deleted outside Hoola")
        try:
            LE.after_delete(r, coll, rid, d, None)
        except Exception:                                       # noqa: BLE001
            log.debug("logic after outside delete", exc_info=True)

    def put(b):
        if isinstance(b.get("owndb"), dict):
            b["owndb"]["pull"] = cur_pull
            b["owndb"]["pull_deleted"] = dseq
            b["owndb"]["last_pull"] = now().isoformat()
    BE.patch_backend(r, fn=put)
    return out


# ---------------------------------------------------------------- link / unlink / status (her taps)
def _ensure(r: AppProject, o: dict) -> dict:
    if _drv(o) is not None:
        return _drv(o).ensure(r, o, _lists(r))
    with _Conn(r.id, o, 60) as c:
        return ensure_schema(r, c, o["schema"])


def _accounts(r: AppProject, o: dict, force: bool = False) -> int:
    if _drv(o) is not None:
        return push_accounts(r, o, None, force)
    with _Conn(r.id, o, 60) as c:
        return push_accounts(r, o, c, force)


def _journal_max(site: str) -> int:
    from . import backup as BK
    BK.ensure_table()
    with session() as s:
        return int(s.scalar(select(BK.AppJournal.id).where(BK.AppJournal.site_id == site).order_by(BK.AppJournal.id.desc()).limit(1)) or 0)


def _catch_up(r: AppProject, o: dict, cursor: int, limit: int = 20 * BATCH) -> int:
    """Every journal entry after `cursor` -> her database (idempotent upserts), in batches. Returns the new cursor."""
    from . import backup as BK
    site = "app:" + r.id
    left = limit
    while left > 0:
        with session() as s:
            js = s.scalars(select(BK.AppJournal).where(BK.AppJournal.site_id == site, BK.AppJournal.id > cursor)
                           .order_by(BK.AppJournal.id).limit(BATCH)).all()
            entries = [(j.op, j.row_id, j.coll, j.owner, j.before, j.after, j.created) for j in js if not j.pushed]
            ids = [j.id for j in js]
        if not ids:
            break
        push(r, o, entries)
        cursor = ids[-1]
        left -= len(entries)
    return cursor


def link(r: AppProject, conn_ref: str, mode: str = "primary", by: str = "owner") -> dict:
    """HER TAP: this app's data into her database (backup first, tables, copy, counts compared, then live)."""
    from . import backend as BE
    from . import backup as BK
    from . import owndb_conns as OC
    mode = mode if mode in MODES else "primary"
    if cfg(r, fresh=True):
        raise OwnDbError("Yeh app pehle se ek database se judi hai; pehle 'Alag karo' dabaiye.", 409)
    try:
        pv, _d = OC.secret_of(r.tenant_id, conn_ref)
    except W.AppError as e:
        raise OwnDbError(str(e), 400)
    if pv.get("can_write") is False:
        raise OwnDbError(f"'{pv['name']}' ka user sirf padh sakta hai; tables banane / likhne wala user dijiye.", 400)

    class _PC:                                           # the view as attributes (name / id / label)
        id, name, label = pv["id"], pv["name"], pv["label"]
    pc = _PC
    s = schema_name(r)
    BK.snapshot(r, f"before linking to {pc.name}", "before")
    jid0 = _journal_max("app:" + r.id)
    o = {"conn": pc.id, "kind": pv["kind"], "tenant": r.tenant_id, "label": pc.label, "name": pc.name, "mode": mode, "schema": s,
         "status": "copying", "cursor": jid0, "linked_at": now().isoformat(), "by": by}
    try:
        made = _ensure(r, o)
        BE.patch_backend(r, set_={"owndb": {k: v for k, v in o.items() if k != "tenant"}})
        _forget(r.id)
        site = "app:" + r.id
        with session() as ss:
            rows = ss.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site)).all()
            entries = [("insert", x.id, x.coll, x.owner or "", "", x.data or "{}",
                        x.created_at.isoformat() if x.created_at else None) for x in rows if x.coll not in SKIP]
        for i in range(0, len(entries), BATCH):
            if _drv(o) is not None:
                push(r, o, entries[i:i + BATCH])
            else:
                with _Conn(r.id, o, 60) as c:
                    push(r, o, entries[i:i + BATCH], c)
        _accounts(r, o, force=True)
        if _drv(o) is not None and hasattr(_drv(o), "prime"):
            _drv(o).prime(r, o, _lists(r))
        cursor = _catch_up(r, o, jid0)
        check = verify(r, o)
    except Exception as e:
        BE.patch_backend(r, fn=lambda b: b.pop("owndb", None))
        _forget(r.id)
        if isinstance(e, W.AppError):
            raise
        log.exception("own database link failed")
        raise OwnDbError(f"Database se jodte waqt galti: {str(e)[:200]}", 502)
    if not check["ok"]:
        BE.patch_backend(r, fn=lambda b: b.pop("owndb", None))
        _forget(r.id)
        raise OwnDbError("Copy ke baad ginti mel nahi khayi: " + "; ".join(check["mismatch"][:4]) + ". App pehle jaisi chal rahi hai.", 502)

    def live(b):
        b["owndb"].update({"status": "live", "cursor": cursor, "copied": len(entries), "live_at": now().isoformat(), "last_error": ""})
    BE.patch_backend(r, fn=live)
    _forget(r.id)
    STATS["linked"] += 1
    try:
        from .logic import engine as LE
        LE.audit(r, "own_db_linked", by=by, what=f"{pc.name} ({pc.label}) schema {s}, {mode}, {len(entries)} rows")
    except Exception:                                    # noqa: BLE001
        pass
    return {"schema": s, "kind": o["kind"], "mode": mode, "copied": len(entries), "tables": made["tables"], "counts": check["counts"],
            "say": (f"App ka data ab aapke database '{pc.name}' mein (schema {s}): {len(entries)} entries copy, ginti mel khayi. "
                    + ("Har nayi entry pehle wahin save hogi; wahan kiya badlav app mein aa jayega." if mode == "primary"
                       else "Har badlav ek minute ke andar wahan pahunchega (copy mode)."))}


def unlink(r: AppProject, by: str = "owner") -> dict:
    from . import backend as BE
    o = cfg(r, fresh=True)
    if not o:
        raise OwnDbError("Yeh app kisi database se judi nahi hai.", 404)
    BE.patch_backend(r, fn=lambda b: b.__setitem__("owndb", {**(b.get("owndb") or {}), "status": "off", "off_at": now().isoformat()}))
    _forget(r.id)
    close_pool(r.id)
    if _drv(o) is not None:
        _drv(o).close(r.id)
    try:
        from .logic import engine as LE
        LE.audit(r, "own_db_unlinked", by=by, what=o.get("name", ""))
    except Exception:                                    # noqa: BLE001
        pass
    return {"ok": True, "say": "App ab Hoola ke database par chal rahi hai. Aapke database mein data waisa hi rakha hai (kuch mita nahi)."}


def verify(r: AppProject, o: dict | None = None) -> dict:
    """Counts per list: the app vs her tables."""
    o = o or cfg(r, fresh=True)
    if not o:
        raise OwnDbError("Yeh app kisi database se judi nahi hai.", 404)
    site = "app:" + r.id
    from sqlalchemy import func
    with session() as s:
        mine = dict(s.execute(select(W.SiteAppRow.coll, func.count()).where(W.SiteAppRow.site_id == site)
                              .group_by(W.SiteAppRow.coll)).all())
    lists = _lists(r)
    theirs: dict[str, int] = {}
    if _drv(o) is not None:
        for coll in lists:
            theirs[coll] = _drv(o).count(r, o, coll)
    else:
        S = _ident(o["schema"])
        with _Conn(r.id, o) as c:
            cur = c.cursor()
            for coll in lists:
                cur.execute(f"SELECT count(*) FROM {S}.{_ident(coll)}")
                theirs[coll] = int(cur.fetchone()[0])
    counts = {coll: {"app": int(mine.get(coll, 0)), "database": theirs.get(coll, 0)} for coll in lists}
    mismatch = [f"{k}: app {v['app']} / database {v['database']}" for k, v in counts.items() if v["app"] != v["database"]]
    return {"ok": not mismatch, "counts": counts, "mismatch": mismatch}


def status(r: AppProject) -> dict:
    be = _j(r.backend, {})
    o = be.get("owndb") if isinstance(be.get("owndb"), dict) else None
    from . import owndb_conns as OC
    out = {"linked": bool(o and o.get("status") in ("copying", "live")), "link": o, "providers": PROVIDERS,
           "connections": OC.connections(r.tenant_id),
           "stats": dict(STATS)}
    if o and o.get("status") == "live":
        out["lag"] = max(0, _journal_max("app:" + r.id) - int(o.get("cursor") or 0))
    return out


# ---------------------------------------------------------------- the worker (every ~20 s)
_last = 0.0


def tick(force: bool = False) -> int:
    global _last
    if not force and time.time() - _last < 20:
        return 0
    _last = time.time()
    from . import backend as BE
    with session() as s:
        apps = s.scalars(select(AppProject).where(AppProject.backend.like('%"owndb"%'))).all()
        for a in apps:
            s.expunge(a)
    n = 0
    for r in apps:
        o = cfg(r, fresh=True)
        if not o or o.get("status") != "live":
            continue
        try:
            be = _j(r.backend, {})
            if str(be.get("rev") or 0) != str(o.get("schema_rev") or ""):
                _ensure(r, o)                                 # a new list / field in the app -> new table / column there
            _accounts(r, o)
            cursor = _catch_up(r, o, int(o.get("cursor") or 0))
            got = pull(r, o) if o.get("mode") == "primary" else {}

            def put(b, cursor=cursor, rev=str(be.get("rev") or 0)):
                if isinstance(b.get("owndb"), dict):
                    b["owndb"].update({"cursor": cursor, "schema_rev": rev, "last_sync": now().isoformat(), "last_error": ""})
            BE.patch_backend(r, fn=put)
            _forget(r.id)
            n += 1 + sum((got or {}).values())
        except Exception as e:                            # noqa: BLE001 - one app never stops the others
            log.warning("own database sync failed for %s: %s", r.id, e)
            _note_error(r.id, str(e))
    return n
