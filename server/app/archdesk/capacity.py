"""v0.410 Capacity maths for the Principal Software Architect - in CODE, never in a prompt.

The model only FILLS IN the inputs (and says for each whether it came from her or is an assumption); every number on
the sheet is computed here, with the formula next to it, so a wrong QPS can never look as confident as a right one.
No daily active users = no sheet (refused, with the reason), never a made-up scale.
"""
from __future__ import annotations

from typing import Any

FIELDS = {                       # name: (label, default when assumed, unit)
    "dau": ("Daily active users", None, "users"),
    "requests_per_user_per_day": ("Requests per user per day", 20.0, "req"),
    "peak_factor": ("Peak / average traffic", 3.0, "x"),
    "write_ratio": ("Share of requests that write", 0.1, ""),
    "avg_response_kb": ("Average response size", 5.0, "KB"),
    "record_kb": ("Stored bytes per write", 1.0, "KB"),
    "retention_days": ("Data kept for", 365.0, "days"),
    "replication": ("Copies of each record", 3.0, "x"),
    "server_rps": ("Requests one app server handles", 500.0, "req/s"),
}


class CapacityError(Exception):
    pass


def _num(v: Any) -> float | None:
    try:
        f = float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return f if f >= 0 else None


def _human_bytes(b: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if b < 1024 or unit == "PB":
            return f"{b:,.1f} {unit}"
        b /= 1024
    return f"{b:,.1f} PB"


def _fmt(v: float) -> str:
    return f"{v:,.0f}" if v >= 100 else f"{v:,.2f}".rstrip("0").rstrip(".")


def compute(inputs: dict[str, Any], sources: dict[str, str] | None = None) -> dict[str, Any]:
    """{inputs: [{key, label, value, unit, source}], rows: [{what, value, formula}], assumed: [labels]}."""
    sources = sources or {}
    vals: dict[str, float] = {}
    shown, assumed = [], []
    for k, (label, default, unit) in FIELDS.items():
        v = _num(inputs.get(k))
        src = str(sources.get(k) or "assumed")      # a number counts as hers ONLY when it is marked hers
        if v is None:
            if default is None:
                raise CapacityError(f"'{label}' is needed - capacity cannot be calculated without it (no guessing).")
            v, src = default, "assumed"
        if src != "her":
            assumed.append(label)
        vals[k] = v
        shown.append({"key": k, "label": label, "value": v, "unit": unit, "source": "her" if src == "her" else "assumed"})
    if vals["dau"] <= 0:
        raise CapacityError("Daily active users must be more than zero.")
    vals["write_ratio"] = min(1.0, vals["write_ratio"])
    req_day = vals["dau"] * vals["requests_per_user_per_day"]
    avg_rps = req_day / 86400
    peak_rps = avg_rps * vals["peak_factor"]
    write_rps = peak_rps * vals["write_ratio"]
    read_rps = peak_rps - write_rps
    store_day = req_day * vals["write_ratio"] * vals["record_kb"] * 1024
    store_total = store_day * vals["retention_days"] * vals["replication"]
    egress = peak_rps * vals["avg_response_kb"] * 1024
    servers = max(1, -(-peak_rps // max(1.0, vals["server_rps"])))
    servers_n1 = int(servers) + 1                    # one spare so a single failure does not take the peak down
    rows = [
        {"what": "Requests per day", "value": _fmt(req_day), "formula": "DAU x requests per user"},
        {"what": "Average requests per second", "value": _fmt(avg_rps), "formula": "requests per day / 86,400"},
        {"what": "Peak requests per second", "value": _fmt(peak_rps), "formula": "average x peak factor"},
        {"what": "Peak writes per second", "value": _fmt(write_rps), "formula": "peak x write share"},
        {"what": "Peak reads per second", "value": _fmt(read_rps), "formula": "peak - writes"},
        {"what": "New data per day", "value": _human_bytes(store_day), "formula": "writes per day x bytes per write"},
        {"what": "Storage for the retention period", "value": _human_bytes(store_total),
         "formula": "data per day x days kept x copies"},
        {"what": "Peak outbound bandwidth", "value": _human_bytes(egress) + "/s", "formula": "peak x response size"},
        {"what": "App servers at peak (N+1)", "value": str(servers_n1),
         "formula": "ceil(peak / one server's capacity) + 1 spare"},
    ]
    return {"inputs": shown, "rows": rows, "assumed": assumed,
            "numbers": {"req_day": req_day, "avg_rps": avg_rps, "peak_rps": peak_rps, "write_rps": write_rps,
                        "storage_bytes": store_total, "egress_bps": egress, "servers": servers_n1}}


def markdown(cap: dict[str, Any]) -> str:
    lines = ["| Input | Value | Source |", "|---|---|---|"]
    for i in cap["inputs"]:
        lines.append(f"| {i['label']} | {_fmt(float(i['value']))} {i['unit']} | "
                     f"{'given by you' if i['source'] == 'her' else 'assumed - please confirm'} |")
    lines += ["", "| Result | Value | How it is worked out |", "|---|---|---|"]
    lines += [f"| {r['what']} | {r['value']} | {r['formula']} |" for r in cap["rows"]]
    if cap["assumed"]:
        lines += ["", "Assumed (not from you): " + ", ".join(cap["assumed"]) + ". Tell me the real numbers and the "
                  "sheet is worked out again."]
    return "\n".join(lines)
