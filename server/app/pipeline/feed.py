"""P0 THE FEED (plan section 8 + 10): public leaderboards -> one dated tables file a day.

`run()` reads every board the kinds need (LMArena dataset + OpenRouter's catalogue, daily; voiceofindia.ai, monthly),
matches names to the ids the Box calls, cuts 10-20 models per kind into LOW..ULTRA by quality bands (cut.py), and saves
`data/pipeline/tables-<date>.json` + `current.json` + `changes.jsonl` (store.py). It reads only public data: no model
call, no money, no key. Nothing reads these tables to choose a model yet (P1+).

CLI (vps-ops `pipeline_feed`): `python -m app.pipeline.feed [--dry]`.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from ..config import get_settings
from . import cut as C
from . import names as N
from . import sources as S
from . import store
from .kinds import KINDS, LEVELS, MIN_POOL, NOT_RANKED, SAME

log = logging.getLogger("santosh.pipeline")
HERE = Path(__file__).parent


def _s(name: str, default: Any) -> Any:
    return getattr(get_settings(), name, default)


def _voi(kind: str, warnings: list[str]) -> tuple[list[dict], str]:
    """voiceofindia rows for 'tts' / 'stt': this month's read, else a fresh browser read, else the last good read,
    else the copy shipped with the code (16 Nov 2026). Returns (rows, read_on)."""
    days = float(_s("pipeline_voi_days", 30) or 30)
    got = store.cache_get(f"voi_{kind}", days * 86400)
    if got:
        return got["rows"], got["read_on"]
    try:
        rows = S.voi_tts() if kind == "tts" else S.voi_stt()
        if len(rows) >= 10:
            day = dt.date.today().isoformat()
            store.cache_put(f"voi_{kind}", {"rows": rows, "read_on": day})
            return rows, day
        warnings.append(f"voiceofindia {kind}: the page gave only {len(rows)} rows - kept the last read")
    except Exception as e:   # noqa: BLE001 - a browser problem never stops the feed
        warnings.append(f"voiceofindia {kind}: not read ({str(e)[:120]}) - kept the last read")
    old = store.cache_get(f"voi_{kind}", float("inf"))
    if old:
        return old["rows"], old["read_on"]
    text = (HERE / "snapshot" / f"voi_{kind}.txt").read_text()
    rows = S.parse_voi_tts(text) if kind == "tts" else S.parse_voi_stt(text)
    return rows, "2026-11-16"


def _voi_table(kind: str, by_id: dict, warnings: list[str]) -> dict:
    rows, read_on = _voi("tts" if kind == "speech.out.indian" else "stt", warnings)
    key, lower = ("elo", False) if kind == "speech.out.indian" else ("wer", True)
    ranked, skipped = [], []
    for i, r in enumerate(sorted(rows, key=lambda r: (r[key] if lower else -r[key], r["name"]))):
        k = N.norm(r["name"])
        if k in N.VOI_OR and N.VOI_OR[k] in by_id:
            e = {"id": N.VOI_OR[k], "route": "openrouter", "status": "ready"}
        elif k in N.ROUTES and N.ROUTES[k]["status"] != "needs_permission":
            e = {x: N.ROUTES[k][x] for x in ("id", "route", "status")}
        else:
            skipped.append(r["name"])
            continue
        ranked.append({**e, "points": float(len(ranked)), "name": r["name"], "score": r[key]})
    lv, method = C.levels(ranked)
    n = sum(len(v) for v in lv.values())
    t = {"levels": {k: lv[k] for k in LEVELS}, "n": n, "method": method,
         "boards": [f"voiceofindia.ai/{'tts' if 'out' in kind else 'stt'} read {read_on}"], "warnings": [],
         "not_reachable": skipped}
    if n < MIN_POOL:
        t["warnings"].append(f"only {n} models (under {MIN_POOL})")
    return t


def _manual(kind: str, by_id: dict, warnings: list[str]) -> dict:
    m = json.loads((HERE / "manual.json").read_text())
    p = m[kind]
    lv = {}
    for name in LEVELS:
        lv[name] = [{"id": i, "route": r, "status": "ready", "points": None, "name": i} for i, r in p["levels"][name]]
        for e in lv[name]:
            if e["route"] == "openrouter" and e["id"] not in by_id:
                warnings.append(f"{kind}: {e['id']} is no longer on OpenRouter")
    n = sum(len(v) for v in lv.values())
    t = {"levels": lv, "n": n, "method": "hand-kept", "boards": [p["source"] + f" (read {m['read_on']})"],
         "warnings": []}
    age = (dt.date.today() - dt.date.fromisoformat(m["read_on"])).days
    if age > int(_s("pipeline_manual_days", 90) or 90):
        t["warnings"].append(f"hand-kept pool is {age} days old - read its boards again")
    return t


KEEP = ("model_name", "rating", "score", "rank", "vote_count", "leaderboard_publish_date", "category")


def _slim(rows: list[dict]) -> list[dict]:
    return [{k: r[k] for k in KEEP if k in r} for r in rows]


def _read_boards(needed: list[tuple], warnings: list[str]) -> tuple[dict[tuple, list], list[str]]:
    """Every board the kinds need. The boards are kept on disk with the dataset's commit: the same commit = no
    re-read (most days one call). A board that cannot be read uses its last good read, said plainly; only a board
    never read before stays empty. Returns (boards, boards still missing)."""
    try:
        sha = S.dataset_sha()
    except Exception as e:   # noqa: BLE001
        sha = ""
        warnings.append(f"dataset version not read ({str(e)[:80]}) - reading every board")
    last = store.cache_get("lmarena_boards", float("inf")) or {}
    kept: dict[str, list] = last.get("boards") or {}
    if sha and last.get("sha") == sha and all(f"{c}/{k}" in kept for c, k in needed):
        return {b: kept[f"{b[0]}/{b[1]}"] for b in needed}, []
    S.reset()
    boards: dict[tuple, list] = {}
    missing: list[str] = []
    fresh: dict[str, list] = {}
    for b in needed:
        key = f"{b[0]}/{b[1]}"
        try:
            boards[b] = _slim(S.board(*b))
            fresh[key] = boards[b]
        except Exception as e:   # noqa: BLE001
            if key in kept:
                boards[b] = kept[key]
                warnings.append(f"board {key} not read ({str(e)[:80]}) - used its last good read")
            else:
                boards[b] = []
                missing.append(key)
                warnings.append(f"board {key} not read: {str(e)[:120]}")
    if fresh:
        store.cache_put("lmarena_boards", {"sha": sha if not missing and len(fresh) == len(needed) else "",
                                           "boards": {**kept, **fresh}})
    return boards, missing


def models_info(tables: dict, by_id: dict) -> dict[str, dict]:
    """v0.961 P1: what each OpenRouter model in the tables can do - window, inputs, outputs, tools, structured output -
    so choosing (plan 4, step 1) never calls OpenRouter while a message waits."""
    out: dict[str, dict] = {}
    for t in tables.values():
        views = [t] + list((t.get("by_language") or {}).values())
        for v in views:
            for lv in (v.get("levels") or {}).values():
                for m in lv:
                    info = by_id.get(m.get("id")) if m.get("route") == "openrouter" else None
                    if not info or m["id"] in out:
                        continue
                    a = info.get("architecture") or {}
                    sp = set(info.get("supported_parameters") or [])
                    out[m["id"]] = {"ctx": int(info.get("context_length") or 0),
                                    "ins": sorted(a.get("input_modalities") or []),
                                    "outs": sorted(a.get("output_modalities") or []),
                                    "tools": "tools" in sp,
                                    "structured": bool({"structured_outputs", "response_format"} & sp)}
    return out


def run(write: bool = True, now: float | None = None) -> dict:
    """One feed run under the lock (a second run at the same time is refused, not doubled)."""
    try:
        with store.lock():
            return _run(write, now)
    except store.Busy:
        log.warning("pipeline feed: another run is going - skipped")
        return {"busy": True, "doc": None, "changes": []}


def _run(write: bool, now: float | None) -> dict:
    now = now or time.time()
    warnings: list[str] = []
    min_votes = int(_s("pipeline_min_votes", 200) or 200)
    cat = S.openrouter()
    idx = N.index(cat)
    by_id = {m["id"]: m for m in cat if m.get("id")}

    needed = sorted({b for spec in KINDS.values() for b in spec.get("boards", [])}
                    | {("text", lang) for lang in KINDS["write.lang"].get("languages", [])})
    boards, missing = _read_boards(needed, warnings)
    dates: dict[str, str] = {}
    for b in needed:
        d = next((r.get("leaderboard_publish_date") for r in boards[b] if r.get("leaderboard_publish_date")), "")
        if d:
            dates[f"{b[0]}/{b[1]}"] = str(d)
    stale = int(_s("pipeline_stale_board_days", 21) or 21)
    for b, d in dates.items():
        try:
            if d and (dt.date.today() - dt.date.fromisoformat(d[:10])).days > stale:
                warnings.append(f"board {b} last published {d[:10]} - older than {stale} days")
        except ValueError:
            pass

    old = (store.read_current() or {}).get("tables") or {}
    tables: dict[str, dict] = {}
    for kind, spec in KINDS.items():
        if spec.get("live"):
            tables[kind] = _voi_table(kind, by_id, warnings)
        elif spec.get("manual"):
            tables[kind] = _manual(kind, by_id, warnings)
        else:
            t = C.cut_kind(spec, boards, idx, by_id, now, min_votes)
            if t["n"] == 0 and (old.get(kind) or {}).get("n"):   # every board failed: keep yesterday's, said plainly
                t = {**old[kind], "warnings": (old[kind].get("warnings") or []) + ["boards not read - kept the last table"]}
            if spec.get("languages"):
                t["by_language"] = {lang: C.cut_kind({**spec, "boards": [("text", lang)]}, boards, idx, by_id, now,
                                                     min_votes) for lang in spec["languages"]}
            tables[kind] = t
    for alias, target in SAME.items():
        tables[alias] = {"same_as": target}
    for kind, why in NOT_RANKED.items():
        tables[kind] = {"not_ranked": why}

    for kind, t in tables.items():
        for w in t.get("warnings") or []:
            if w.startswith("only "):
                warnings.append(f"{kind}: {w}")
    doc = {"models": models_info(tables, by_id), "read_on": dt.date.fromtimestamp(now).isoformat(), "made_at": dt.datetime.fromtimestamp(now).isoformat(),
           "version": 1, "board_dates": dates, "openrouter_models": len(cat), "tables": tables, "warnings": warnings,
           "complete": not missing, "missing_boards": missing}
    changes = store.save(doc) if write else []
    counts = " ".join(f"{k}={t['n']}" for k, t in tables.items() if "n" in t)
    log.warning("pipeline feed %s: %s | %d changes (%d big) | %d warnings", doc["read_on"], counts, len(changes),
                sum(1 for c in changes if c.get("big")), len(warnings))
    for w in warnings:
        log.warning("pipeline feed warning: %s", w)
    return {"doc": doc, "changes": changes}


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    r = run(write="--dry" not in argv)
    if r.get("busy"):
        print("pipeline feed: another run is going right now (the server's own daily run) - try again in a few minutes")
        return 0
    d = r["doc"]
    print(f"pipeline feed {d['read_on']} - {d['openrouter_models']} OpenRouter models")
    for kind, t in d["tables"].items():
        if "n" not in t:
            print(f"  {kind:18s} -> {t.get('same_as') or t.get('not_ranked')}")
            continue
        top = ", ".join(m["id"] for m in t["levels"]["ULTRA"][:2])
        print(f"  {kind:18s} {t['n']:2d} models ({t['method']})  ULTRA: {top}")
    print(f"changes: {len(r['changes'])} (big: {sum(1 for c in r['changes'] if c.get('big'))})")
    for c in r["changes"][:40]:
        print("  ", c)
    print(f"complete: {d['complete']}" + (f" (boards never read: {', '.join(d['missing_boards'])})"
                                         if d["missing_boards"] else ""))
    print(f"warnings: {len(d['warnings'])}")
    for w in d["warnings"]:
        print("  -", w)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
