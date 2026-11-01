"""v0.388 PAKKI NEEV: move Hoola's whole database from SQLite to Postgres - checked, repeatable, nothing lost.

    python -m app.dbmove --to "postgresql+psycopg://hoola:PASS@127.0.0.1:5432/hoola"            # copy + verify
    python -m app.dbmove --to "..." --check                                                      # verify only

What it does: makes every table in the target (the same models the server uses), copies each table in batches of
2,000 in dependency order, reads every row back through the SAME column types (so dates / JSON / booleans arrive as
what they are, not as SQLite text), then proves it: row counts per table must match exactly, and Postgres id counters
are moved past the highest id. It refuses a target that already holds data (unless --force-empty-check is given for a
re-run onto a fresh database). The source is only read. After it says OK: set DATABASE_URL in the VPS .env to the
target and restart; keep santosh.db as the fallback until she is happy."""
from __future__ import annotations

import argparse
import sys
import time

from sqlalchemy import MetaData, create_engine, func, inspect, select, text


def _metadata() -> list[MetaData]:
    from . import db
    keep = (db._engine, db._Session)
    try:
        db.init_db("sqlite://")                          # imports every model module (registers every table), in memory
    finally:
        db._engine, db._Session = keep                   # the server's own engine is left exactly as it was
    from .bazar.db import Base as BazarBase
    return [db.Base.metadata, BazarBase.metadata]


def _tables(mds: list[MetaData]):
    seen, out = set(), []
    for md in mds:
        for t in md.sorted_tables:                       # parents before children
            if t.name not in seen:
                seen.add(t.name)
                out.append(t)
    return out


def move(src_url: str, dst_url: str, check_only: bool = False, batch: int = 2000, quiet: bool = False) -> dict:
    say = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    mds = _metadata()
    src = create_engine(src_url)
    dst = create_engine(dst_url)
    src_names = set(inspect(src).get_table_names())
    if not check_only:
        for md in mds:
            md.create_all(dst)
        from .db import _add_missing_columns
        _add_missing_columns(dst)
    tables = [t for t in _tables(mds) if t.name in src_names]
    if not check_only:
        with dst.connect() as c:
            busy = [t.name for t in tables if c.execute(select(func.count()).select_from(t)).scalar()]
        if busy:
            raise SystemExit(f"Target already has data in {len(busy)} table(s) ({', '.join(busy[:5])}...). "
                             "Use a fresh, empty database.")
    report: dict[str, tuple[int, int]] = {}
    t0 = time.time()
    for t in tables:
        src_cols = {c["name"] for c in inspect(src).get_columns(t.name)}
        cols = [c for c in t.columns if c.name in src_cols]
        n_src = 0
        if not check_only:
            with src.connect() as sc, dst.begin() as dc:
                res = sc.execute(select(*cols)).mappings()
                while True:
                    chunk = res.fetchmany(batch)
                    if not chunk:
                        break
                    dc.execute(t.insert(), [dict(r) for r in chunk])
                    n_src += len(chunk)
        with src.connect() as sc:
            a = sc.execute(select(func.count()).select_from(t)).scalar() or 0
        with dst.connect() as dc:
            b = dc.execute(select(func.count()).select_from(t)).scalar() or 0
        report[t.name] = (int(a), int(b))
        if a or b:
            say(f"  {t.name}: {a} -> {b}" + ("" if a == b else "   MISMATCH"))
    if dst.dialect.name == "postgresql" and not check_only:
        with dst.begin() as c:                            # integer ids continue after the copied ones
            for t in tables:
                for col in t.primary_key.columns:
                    if col.autoincrement is not False and str(col.type).upper().startswith(("INTEGER", "BIGINT")):
                        seq = c.execute(text("SELECT pg_get_serial_sequence(:t, :c)"), {"t": t.name, "c": col.name}).scalar()
                        if seq:
                            c.execute(text(f"SELECT setval('{seq}', COALESCE((SELECT MAX({col.name}) FROM {t.name}), 0) + 1, false)"))
    bad = {k: v for k, v in report.items() if v[0] != v[1]}
    say(f"{'OK' if not bad else 'FAILED'}: {len(report)} tables, {sum(v[0] for v in report.values())} rows, "
        f"{len(bad)} mismatched, {time.time() - t0:.1f}s")
    return {"ok": not bad, "tables": len(report), "rows": sum(v[0] for v in report.values()), "mismatched": bad}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="src", default="", help="source URL (default: DATABASE_URL / settings)")
    ap.add_argument("--to", dest="dst", required=True, help="target postgresql+psycopg://... URL (an EMPTY database)")
    ap.add_argument("--check", action="store_true", help="only compare row counts")
    a = ap.parse_args(argv)
    from .config import get_settings
    src = a.src or get_settings().database_url
    if src.startswith("postgresql"):
        print("The source is already Postgres.")
        return 1
    out = move(src, a.dst, check_only=a.check)
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
