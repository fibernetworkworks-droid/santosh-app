"""v0.929 Hoola Code session log (vps-ops `codelog`): the last few Hoola Code sessions read straight from the database,
read-only - her ask, the kind and tier the server chose, every pass, what each step did, Hoola's words, the error.
Nothing is changed. Usage: python codelog.py [sessions] [db path]"""
from __future__ import annotations

import collections
import json
import sqlite3
import sys


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 6
    db = sys.argv[2] if len(sys.argv) > 2 else "santosh.db"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=20)
    con.row_factory = sqlite3.Row
    cols = {r[1] for r in con.execute("PRAGMA table_info(devsahayak_tasks)")}
    want = [c for c in ("number", "kind", "tier", "status", "repo", "text", "error", "explain", "steps", "rounds",
                        "model", "effort", "created_at", "updated_at", "cost") if c in cols]
    rows = con.execute(f"SELECT {', '.join(want)} FROM devsahayak_tasks ORDER BY created_at DESC LIMIT ?", (n,)).fetchall()
    for r in reversed(rows):
        d = dict(r)
        print("=" * 100)
        print(f"{d.get('number')}  kind={d.get('kind')}  tier={d.get('tier')}  status={d.get('status')}  "
              f"rounds={d.get('rounds')}  model={d.get('model') or '-'}  effort={d.get('effort') or '-'}")
        print(f"repo={d.get('repo')}  created={d.get('created_at')}  updated={d.get('updated_at')}  cost={d.get('cost') or '-'}")
        print("ASK:", (d.get("text") or "").replace("\n", " ")[:400])
        try:
            steps = json.loads(d.get("steps") or "[]")
        except ValueError:
            steps = []
        kinds = collections.Counter(str(s.get("k")) for s in steps if isinstance(s, dict))
        print("STEPS:", len(steps), dict(kinds))
        first = last = ""
        for s in steps:
            if not isinstance(s, dict):
                continue
            first = first or str(s.get("at") or "")
            last = str(s.get("at") or last)
            k = s.get("k")
            if k == "pass":
                print(f"  [{str(s.get('at'))[11:19]}] PASS {s.get('name')} {s.get('state')} {s.get('note') or ''} {('ok' if s.get('ok') else 'NOT ok') if 'ok' in s else ''}")
            elif k in ("say", "note"):
                print(f"  [{str(s.get('at'))[11:19]}] {k.upper()}: " + str(s.get("text") or "").replace("\n", " ")[:500])
            elif k in ("read", "edit", "new"):
                print(f"  [{str(s.get('at'))[11:19]}] {k} {s.get('path')}")
            elif k in ("search", "grep", "usages"):
                print(f"  [{str(s.get('at'))[11:19]}] {k} {s.get('q') or s.get('name')} -> {s.get('n')}")
            elif k == "bash":
                print(f"  [{str(s.get('at'))[11:19]}] bash {str(s.get('cmd'))[:160]} rc={s.get('rc')}")
            elif k not in ("think", "ckpt", "list"):
                print(f"  [{str(s.get('at'))[11:19]}] {k} " + json.dumps({x: y for x, y in s.items() if x not in ('k', 'at')})[:200])
        print("TIME:", first[11:19], "->", last[11:19])
        if d.get("explain"):
            print("EXPLAIN:", str(d["explain"]).replace("\n", " ")[:700])
        if d.get("error"):
            print("ERROR:", str(d["error"]).replace("\n", " ")[:500])


if __name__ == "__main__":
    main()
