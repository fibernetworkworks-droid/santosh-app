"""v0.404 APNA DATABASE 2: her non-Postgres databases - MySQL family, MongoDB, Firebase (Firestore) - connected safely.

Same rules as v0.147 Postgres: the secret is typed ONLY in the app (never chat), sealed with the bazar vault, never
returned, logged or shown to the model; errors mask the password; the host must be on the public internet (checked IP)
and the connection encrypted. PostgreSQL connections stay in `pgdb_conns` (v0.147); `connections(tenant)` lists both.

  mysql     mysql://user:password@host:3306/db          MySQL, MariaDB, PlanetScale, TiDB Cloud, Aurora MySQL, Azure /
                                                        Google Cloud SQL for MySQL, DigitalOcean, Aiven ... (TLS required)
  mongodb   mongodb+srv://user:password@cluster/db      MongoDB Atlas, self-hosted, Azure Cosmos DB (Mongo API),
            mongodb://user:password@host:27017/db       Amazon DocumentDB (TLS required)
  firestore the service-account JSON of her Firebase project (Project settings > Service accounts > Generate new
            private key) - Hoola writes under hoola_apps/<app>/... only"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session
from ..site import webapp as W

KINDS = ("postgres", "mysql", "mongodb", "firestore")
MAX_CONNS = 10


class OwnDbConnError(W.AppError):
    pass


class OwnConn(Base):
    __tablename__ = "owndb_conns"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("odc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    name: Mapped[str] = mapped_column(String(60), default="")
    label: Mapped[str] = mapped_column(String(200), default="")         # user@host/db - never a password
    sealed: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(12), default="ok")
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_OK = False


def ensure_table() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        OwnConn.__table__.create(_db._engine, checkfirst=True)
        _OK = True


def _vault():
    from ..bazar.security import vault
    return vault()


def _private_ok() -> bool:
    return bool(get_settings().pgdb_allow_private)


def _public(host: str, port: int) -> str:
    """The host must resolve to the public internet (no Hoola-internal / LAN address). Returns the first checked IP."""
    if not host or "/" in host:
        raise OwnDbConnError("Host sahi nahi.")
    h = host.lower()
    if (h in ("localhost", "metadata.google.internal") or h.endswith((".local", ".internal", ".localhost"))) and not _private_ok():
        raise OwnDbConnError("Yeh address Hoola ke server ke andar ka hai; apne database ka public host dijiye.")
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except OSError:
        raise OwnDbConnError(f"Host {host} nahi mila. Spelling dekhiye.")
    ips = []
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (not ip.is_global or ip.is_multicast) and not _private_ok():
            raise OwnDbConnError("Yeh host private network ki taraf jaata hai; Hoola sirf public internet par database se judta hai.")
        ips.append(str(ip))
    if not ips:
        raise OwnDbConnError(f"Host {host} nahi mila.")
    return ips[0]


def mask(s: str, d: dict | None = None) -> str:
    s = str(s or "").strip().splitlines()[0] if str(s or "").strip() else ""
    if d:
        for k in ("password", "private_key"):
            if d.get(k):
                s = s.replace(str(d[k]), "••••")
    s = re.sub(r"((?:mysql|mongodb(?:\+srv)?)://[^:/\s]+:)[^@\s]+@", r"\1••••@", s, flags=re.I)
    s = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "[key]", s, flags=re.S)
    return s[:300]


# ---------------------------------------------------------------- parse each kind
def parse(kind: str, secret: str) -> dict[str, Any]:
    secret = (secret or "").strip()
    if not secret:
        raise OwnDbConnError("Connection khaali hai.")
    if len(secret) > 6000:
        raise OwnDbConnError("Bahut lamba hai.")
    if kind == "mysql":
        u = urlparse(secret)
        if u.scheme not in ("mysql", "mysql+pymysql", "mariadb"):
            raise OwnDbConnError("Roop: mysql://user:password@host:3306/dbname")
        if not u.hostname or not u.username or not (u.path or "/").strip("/"):
            raise OwnDbConnError("Host, user aur database ka naam chahiye (mysql://user:password@host:3306/dbname).")
        q = {k: v[-1] for k, v in parse_qs(u.query).items()}
        return {"kind": "mysql", "host": u.hostname, "port": int(u.port or 3306), "user": unquote(u.username),
                "password": unquote(u.password or ""), "db": unquote(u.path.strip("/")),
                "tls": str(q.get("ssl") or q.get("sslmode") or q.get("ssl-mode") or "required").lower() not in ("false", "0", "disable", "disabled")}
    if kind == "mongodb":
        u = urlparse(secret)
        if u.scheme not in ("mongodb", "mongodb+srv"):
            raise OwnDbConnError("Roop: mongodb+srv://user:password@cluster.mongodb.net/dbname")
        if not u.hostname:
            raise OwnDbConnError("Host chahiye.")
        q = {k: v[-1] for k, v in parse_qs(u.query).items()}
        db = unquote((u.path or "/").strip("/")) or "hoola"
        tls = u.scheme == "mongodb+srv" or str(q.get("tls") or q.get("ssl") or "").lower() == "true"
        return {"kind": "mongodb", "uri": secret, "srv": u.scheme == "mongodb+srv", "host": u.hostname, "port": int(u.port or 27017),
                "user": unquote(u.username or ""), "password": unquote(u.password or ""), "db": db, "tls": tls,
                "hosts": [h.strip() for h in (u.netloc.split("@")[-1]).split(",") if h.strip()]}
    if kind == "firestore":
        try:
            sa = json.loads(secret)
        except ValueError:
            raise OwnDbConnError("Firebase ki service-account JSON file ka poora text chahiye (Project settings > Service accounts).")
        if sa.get("emulator") and _private_ok():            # tests / her own local emulator only
            return {"kind": "firestore", "project_id": str(sa.get("project_id") or "demo-hoola"), "emulator": str(sa["emulator"])}
        if sa.get("type") != "service_account" or not sa.get("project_id") or not sa.get("private_key") or not sa.get("client_email"):
            raise OwnDbConnError("Yeh service-account JSON nahi lagti (type, project_id, client_email, private_key chahiye).")
        return {"kind": "firestore", "project_id": sa["project_id"], "client_email": sa["client_email"], "sa": sa}
    raise OwnDbConnError(f"Database ka prakaar: {', '.join(KINDS)}.")


def label_of(d: dict) -> str:
    if d["kind"] == "firestore":
        return f"firebase:{d['project_id']}" + (" (emulator)" if d.get("emulator") else "")
    if d["kind"] == "mongodb":
        return f"{d.get('user') or ''}@{d['host']}/{d['db']}"
    return f"{d['user']}@{d['host']}:{d['port']}/{d['db']}"


# ---------------------------------------------------------------- open a client per kind (used by the drivers)
def mysql_connect(d: dict, timeout_s: int = 15):
    import pymysql
    ip = _public(d["host"], d["port"])
    kw: dict[str, Any] = {"host": d["host"] if _private_ok() else ip, "port": d["port"], "user": d["user"],
                          "password": d["password"], "database": d["db"], "connect_timeout": 10, "read_timeout": timeout_s,
                          "write_timeout": timeout_s, "autocommit": False, "charset": "utf8mb4"}
    if d.get("tls", True):
        import ssl

        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        kw["ssl"] = ctx
        kw["host"] = d["host"]                               # TLS checks the name; the name was checked public above
    elif not _private_ok():
        raise OwnDbConnError("Internet par bina TLS ke database nahi: ssl chalu rakhiye (PlanetScale / TiDB mein hamesha).")
    try:
        return pymysql.connect(**kw)
    except pymysql.MySQLError as e:
        raise OwnDbConnError(_mysql_err(e, d), 503)


def _mysql_err(e: Exception, d: dict) -> str:
    s = mask(str(e), d)
    if "Access denied" in s:
        return "Database ne user / password mana kar diya."
    if "timed out" in s.lower() or "Can't connect" in s:
        return "Database se jud nahi paya: host / port / firewall dekhiye; Hoola ke server ka IP allow karna pad sakta hai."
    return s


def mongo_client(d: dict, timeout_s: int = 15):
    import pymongo
    hosts = d.get("hosts") or [d["host"]]
    if not d.get("srv"):
        for h in hosts:
            name, _, port = h.partition(":")
            _public(name, int(port or 27017))
    elif not _private_ok():
        import dns.resolver
        for r in dns.resolver.resolve("_mongodb._tcp." + d["host"], "SRV"):
            _public(str(r.target).rstrip("."), int(r.port))
    if not d.get("tls") and not _private_ok():
        raise OwnDbConnError("Internet par bina TLS ke database nahi: tls=true rakhiye (Atlas mein hamesha hota hai).")
    kw = {"serverSelectionTimeoutMS": 10000, "connectTimeoutMS": 10000, "socketTimeoutMS": timeout_s * 1000, "appname": "hoola"}
    if _private_ok() and not d.get("srv"):
        kw["directConnection"] = True
    try:
        return pymongo.MongoClient(d["uri"], **kw)
    except Exception as e:                                  # noqa: BLE001
        raise OwnDbConnError(mask(str(e), d), 503)


def firestore_client(d: dict):
    from google.cloud import firestore
    if d.get("emulator"):
        import os

        from google.auth.credentials import AnonymousCredentials
        os.environ["FIRESTORE_EMULATOR_HOST"] = d["emulator"]
        return firestore.Client(project=d["project_id"], credentials=AnonymousCredentials())
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(d["sa"], scopes=["https://www.googleapis.com/auth/datastore"])
    return firestore.Client(project=d["project_id"], credentials=creds)


def probe(d: dict) -> str:
    """One real round trip. Returns the version text."""
    if d["kind"] == "mysql":
        c = mysql_connect(d)
        try:
            with c.cursor() as cur:
                cur.execute("SELECT VERSION()")
                return str(cur.fetchone()[0])[:80]
        finally:
            c.close()
    if d["kind"] == "mongodb":
        cl = mongo_client(d)
        try:
            info = cl.server_info()
            return f"MongoDB {info.get('version', '')}"
        except Exception as e:                              # noqa: BLE001
            raise OwnDbConnError(mask(str(e), d), 503)
        finally:
            cl.close()
    if d["kind"] == "firestore":
        try:
            cl = firestore_client(d)
            list(cl.collection("hoola_apps").limit(1).stream())
            return "Firestore"
        except Exception as e:                              # noqa: BLE001
            raise OwnDbConnError("Firebase se jud nahi paya: " + mask(str(e), d.get("sa") or {}), 503)
    raise OwnDbConnError("Yeh prakaar nahi.")


# ---------------------------------------------------------------- store
def add(tenant: str, kind: str, name: str, secret: str) -> dict:
    ensure_table()
    kind = (kind or "").strip().lower()
    if kind == "postgres":
        from ..pgdb import service as PG
        try:
            return {**PG.add(tenant, name, secret), "kind": "postgres"}
        except PG.PgError as e:
            raise OwnDbConnError(str(e))
    d = parse(kind, secret)
    ver = probe(d)
    name = re.sub(r"\s+", " ", (name or "").strip())[:60] or label_of(d)
    with session() as s:
        rows = s.scalars(select(OwnConn).where(OwnConn.tenant_id == tenant)).all()
        same = next((x for x in rows if x.name.lower() == name.lower()), None)
        if not same and len(rows) >= MAX_CONNS:
            raise OwnDbConnError(f"{MAX_CONNS} databases tak jod sakte hain; koi purana hataiye.")
        c = same or OwnConn(tenant_id=tenant)
        c.kind, c.name, c.label, c.version = kind, name, label_of(d), ver
        c.sealed = _vault().seal(json.dumps(d))
        c.status, c.last_error = "ok", ""
        if not same:
            s.add(c)
        s.flush()
        out = view(c)
    out["say"] = f"Database '{name}' jud gaya ({out['label']}, {ver})."
    return out


def view(c: OwnConn) -> dict:
    return {"id": c.id, "kind": c.kind, "name": c.name, "label": c.label, "version": c.version, "status": c.status,
            "can_write": True}


def remove(tenant: str, cid: str) -> dict:
    ensure_table()
    with session() as s:
        c = s.get(OwnConn, cid)
        if c is None or c.tenant_id != tenant:
            raise OwnDbConnError("Yeh database nahi mila.", 404)
        name = c.name
        s.delete(c)
    return {"removed": name, "say": f"'{name}' hata diya; uska password Hoola ke paas ab nahi hai."}


def secret_of(tenant: str, cid: str) -> tuple[dict, dict]:
    """(view, the opened secret) for one of her connections - Postgres ones come from pgdb."""
    if cid.startswith("pgc"):
        from ..pgdb import service as PG
        try:
            pc, d = PG._dsn(tenant, cid)
        except PG.PgError as e:
            raise OwnDbConnError(str(e))
        return {"id": pc.id, "kind": "postgres", "name": pc.name, "label": pc.label, "can_write": pc.can_write}, {"kind": "postgres", **d}
    ensure_table()
    with session() as s:
        c = s.get(OwnConn, cid)
        if c is None or c.tenant_id != tenant:
            raise OwnDbConnError("Yeh database nahi mila; app mein dobara jodiye.", 404)
        s.expunge(c)
    try:
        d = json.loads(_vault().open(c.sealed))
    except Exception:                                       # noqa: BLE001
        raise OwnDbConnError("Is database ka saved password khul nahi raha; app mein dobara jodiye.")
    return view(c), d


def connections(tenant: str) -> list[dict]:
    from ..pgdb import service as PG
    out = [{**{k: c.get(k) for k in ("id", "name", "label", "can_write", "status", "version")}, "kind": "postgres"}
           for c in PG.conns(tenant)]
    ensure_table()
    with session() as s:
        out += [view(c) for c in s.scalars(select(OwnConn).where(OwnConn.tenant_id == tenant).order_by(OwnConn.created_at)).all()]
    return out
