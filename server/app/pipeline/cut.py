"""P0 cutting rules (plan 8.2 + D10-D12). Pure: the same board rows + catalogue always give the same tables."""
from __future__ import annotations

import time

from . import names as N
from .kinds import BANDS, LEVELS, PER_LEVEL, MIN_POOL

RECENT_S = 548 * 86400          # added to OpenRouter in the last 18 months (older models are being retired)
SCORE_SPAN = 190.0              # a score board's whole range is put on the band window (best = 0, last = 190)


def _fits(m: dict | None, out: str, need: str | None) -> bool:
    """An OpenRouter model that can do the work: gives `out`, takes what `need` asks."""
    if m is None:
        return True                     # a non-OpenRouter route is listed only for the work it does (names.ROUTES)
    a = m.get("architecture") or {}
    outs = set(a.get("output_modalities") or [])
    ins = set(a.get("input_modalities") or [])
    sp = set(m.get("supported_parameters") or [])
    if out not in outs:
        return False
    if need == "tools" and "tools" not in sp:
        return False
    if need == "structured" and not ({"structured_outputs", "response_format"} & sp):
        return False
    if need == "img_in" and "image" not in ins:
        return False
    if need == "doc_in" and not ({"file", "image"} & ins):
        return False
    return True


def _recent(m: dict | None, now: float) -> bool:
    if m is None:
        return True
    created = m.get("created") or 0
    return not created or created >= now - RECENT_S


def board_points(rows: list[dict], idx: dict, by_id: dict, out: str, need: str | None, now: float,
                 min_votes: int = 200) -> dict[str, dict]:
    """One board -> {id: {points, name, route, status, raw}} for the models that can do the work.

    Rating boards: points = best usable rating - rating. Score boards (agent): points by rank across the board's
    usable models, spread over SCORE_SPAN. Several effort settings of one model -> its best row."""
    best: dict[str, dict] = {}
    for r in rows:
        name = str(r.get("model_name") or "")
        mt = N.match(name, idx, by_id)
        if not mt or mt["status"] == "needs_permission":
            continue
        if not _fits(mt["model"], out, need) or not _recent(mt["model"], now):
            continue
        if "rating" in r and r.get("rating") is not None:
            if int(r.get("vote_count") or 0) < min_votes:
                continue
            val, kind = float(r["rating"]), "rating"
        elif r.get("rank") is not None:
            val, kind = -float(r["rank"]), "rank"
        else:
            continue
        cur = best.get(mt["id"])
        if cur is None or val > cur["val"]:
            best[mt["id"]] = {"val": val, "kind": kind, "name": name, "route": mt["route"], "status": mt["status"]}
    if not best:
        return {}
    top = max(v["val"] for v in best.values())
    if next(iter(best.values()))["kind"] == "rating":
        for v in best.values():
            v["points"] = top - v["val"]
    else:
        order = sorted(best, key=lambda k: (-best[k]["val"], k))
        n = max(len(order) - 1, 1)
        for i, k in enumerate(order):
            best[k]["points"] = SCORE_SPAN * i / n
    return best


def combine(per_board: list[dict[str, dict]]) -> list[dict]:
    """Average a model's points over the boards it is on (missing from one board = the others decide, plan 8.2.4)."""
    acc: dict[str, list] = {}
    for b in per_board:
        for mid, v in b.items():
            acc.setdefault(mid, []).append(v)
    out = []
    for mid, vs in acc.items():
        out.append({"id": mid, "points": round(sum(v["points"] for v in vs) / len(vs), 1), "name": vs[0]["name"],
                    "route": vs[0]["route"], "status": vs[0]["status"], "boards": len(vs)})
    if out:
        low = min(x["points"] for x in out)
        for x in out:
            x["points"] = round(x["points"] - low, 1)
    return sorted(out, key=lambda x: (x["points"], x["id"]))


def levels(ranked: list[dict]) -> tuple[dict[str, list], str]:
    """Quality bands (D10); a pool too thin for bands = the best 20 in five equal groups."""
    lv = {name: [x for x in ranked if a <= x["points"] < b][:PER_LEVEL] for name, a, b in BANDS}
    if min(len(v) for v in lv.values()) >= 2:
        return lv, "bands"
    top = ranked[:PER_LEVEL * 5]
    n, base = len(top), len(top) // 5
    sizes = [base] * 5
    for i in [1, 2, 0, 3, 4][: n % 5]:        # spare ones to HIGH, MID, MAX, LOW, ULTRA (top-first order below)
        sizes[i] += 1
    out, p = {}, 0
    for (name, _, _), s in zip(BANDS, sizes):
        out[name] = top[p:p + s]
        p += s
    return out, "rank split"


def ordered_rows(rows: list[dict], key: str, lower_better: bool) -> list[dict]:
    """A non-LMArena board (voiceofindia) as rows the same cutter reads: rating = a rank-preserving number."""
    rs = sorted(rows, key=lambda r: (r[key] if lower_better else -r[key], r["name"]))
    return [{"model_name": r["name"], "rating": float(1000 - i), "vote_count": 10_000} for i, r in enumerate(rs)]


def cut_kind(spec: dict, boards: dict, idx: dict, by_id: dict, now: float | None = None, min_votes: int = 200) -> dict:
    now = now or time.time()
    per = [board_points(boards.get(b, []), idx, by_id, spec.get("out", "text"), spec.get("need"), now, min_votes)
           for b in spec["boards"]]
    ranked = combine(per)
    lv, method = levels(ranked)
    n = sum(len(v) for v in lv.values())
    table = {"levels": {k: [{x: m[x] for x in ("id", "route", "status", "points", "name")} for m in lv[k]]
                        for k in LEVELS},
             "n": n, "method": method, "boards": [f"{c}/{k}" for c, k in spec["boards"]], "warnings": []}
    if spec.get("proxy"):
        table["warnings"].append(spec["proxy"])
    if n < MIN_POOL:
        table["warnings"].append(f"only {n} models (under {MIN_POOL})")
    return table
