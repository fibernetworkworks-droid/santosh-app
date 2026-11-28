"""How long the battery lasts: the device's states as currents and how often each runs (sleep all the time, measure 120 ms every
minute, send by radio 30 ms every 10 minutes) turned into the average current, the charge used a day, the battery life with the
usable share and self-discharge, which state uses the most, the peak the battery must deliver, and what each change would buy."""
from __future__ import annotations

import re
from typing import Any



class PowerError(ValueError):
    pass


CUR = {"na": 1e-6, "ua": 1e-3, "µa": 1e-3, "ma": 1.0, "a": 1000.0}
TIME = {"us": 1e-6, "µs": 1e-6, "ms": 1e-3, "s": 1.0, "sec": 1.0, "min": 60.0, "m": 60.0, "h": 3600.0, "hr": 3600.0, "hour": 3600.0, "hours": 3600.0,
        "d": 86400.0, "day": 86400.0, "days": 86400.0, "w": 604800.0, "week": 604800.0, "mins": 60.0, "minute": 60.0, "minutes": 60.0, "secs": 1.0,
        "second": 1.0, "seconds": 1.0}
BASE_WORDS = re.compile(r"\b(?:sleep|idle|standby|base|quiescent|always|deep\s*sleep|shutdown|off|leak(?:age)?|background|stop|hibernate)\b", re.I)


def _cur(tok: str) -> float | None:
    m = re.fullmatch(r"([\d.]+)\s*(na|ua|µa|ma|a)", tok.lower())
    return float(m.group(1)) * CUR[m.group(2)] if m else None


def _time(tok: str) -> float | None:
    m = re.fullmatch(r"([\d.]+)\s*(us|µs|ms|s|sec|secs|seconds?|mins?|minutes?|m|h|hr|hours?|d|days?|w|week)", tok.lower())
    return float(m.group(1)) * TIME[m.group(2)] if m else None


def parse(text: str) -> list[dict[str, Any]]:
    out = []
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        ln = raw.split("#")[0].strip()
        if not ln:
            continue
        s = re.sub(r"(\d)\s+(na|ua|µa|ma|a|us|µs|ms|s|sec|secs|min|mins|minutes?|h|hr|hours?|days?|d)\b", r"\1\2", ln, flags=re.I)
        s = re.sub(r"\s*=\s*", " ", s)
        toks = re.split(r"[\s,;]+", s)
        name, cur, dur, per = [], None, None, None
        k = 0
        while k < len(toks):
            t = toks[k]
            tl = t.lower()
            if cur is None and _cur(t) is not None:
                cur = _cur(t)
            elif tl in ("every", "each", "period") and k + 1 < len(toks) and _time(toks[k + 1]) is not None:
                per = _time(toks[k + 1])
                k += 1
            elif re.fullmatch(r"[\d.]+(?:x|times)?", tl) and k + 2 < len(toks) and toks[k + 1].lower() in ("per", "a", "/", "times", "x") or re.fullmatch(r"[\d.]+(?:/|x/|times/)(?:h|hr|hour|d|day|min|m|s|week)", tl):
                mm = re.fullmatch(r"([\d.]+)(?:x|times)?(?:/|x/|times/)?(h|hr|hour|d|day|min|m|s|week)?", tl)
                count = float(mm.group(1))
                unit = mm.group(2)
                j = k + 1
                while not unit and j < len(toks) and j <= k + 3:
                    w = toks[j].lower().rstrip(".")
                    if w in TIME:
                        unit = w
                        break
                    j += 1
                if not unit or count <= 0:
                    raise PowerError(f"Line {n}: say how often, e.g. 'every 10min' or '24 times a day'.")
                per = TIME[unit] / count
                k = j
            elif dur is None and cur is not None and _time(t) is not None:
                dur = _time(t)
            elif cur is None and dur is None and per is None:
                name.append(t)
            elif _time(t) is not None and per is None and dur is not None:
                per = _time(t)
            k += 1
        nm = " ".join(name).strip() or f"line {n}"
        if cur is None:
            raise PowerError(f"Line {n} ({nm}): needs a current such as 4.5mA or 2uA.")
        base = dur is None and per is None
        if not base and dur is None:
            raise PowerError(f"Line {n} ({nm}): how long it runs each time, e.g. '120ms every 60s'.")
        if not base and per is None:
            if BASE_WORDS.search(nm):
                base = True
            else:
                raise PowerError(f"Line {n} ({nm}): how often it runs, e.g. 'every 10min' - or leave out the duration if it is on all the time.")
        if not base and dur > per:
            raise PowerError(f"Line {n} ({nm}): runs {tfmt(dur * 1e6)} but repeats every {tfmt(per * 1e6)}.")
        out.append({"name": nm[:60], "mA": cur, "dur": None if base else dur, "per": None if base else per, "base": base, "line": n})
    if not out:
        raise PowerError("One state per line - e.g. 'sleep 2uA', 'measure 4.5mA 120ms every 60s', 'radio 45mA 30ms every 10min'.")
    if len(out) > 60:
        raise PowerError("Up to 60 lines.")
    return out


def _life(avg: float, cap: float, usable: float, sd_year: float) -> float | None:
    if avg <= 0 and sd_year <= 0:
        return None
    i_sd = cap * sd_year / 100 / 8760.0
    return cap * usable / 100 / (avg + i_sd)


def _avg(rows: list[dict[str, Any]], mult: dict[int, float] | None = None) -> float:
    mult = mult or {}
    active = sum(r["dur"] / (r["per"] * mult.get(i, 1)) for i, r in enumerate(rows) if not r["base"])
    base = sum(r["mA"] for r in rows if r["base"])
    return sum(r["mA"] * r["dur"] / (r["per"] * mult.get(i, 1)) for i, r in enumerate(rows) if not r["base"]) + base * max(0.0, 1 - active)


def tfmt(us: float) -> str:
    sec = us / 1e6
    if sec >= 86400:
        return f"{sec / 86400:.3g} days"
    if sec >= 3600:
        return f"{sec / 3600:.3g} h"
    if sec >= 120:
        return f"{sec / 60:.3g} min"
    if sec >= 1:
        return f"{sec:.3g} s"
    if sec >= 1e-3:
        return f"{sec * 1e3:.3g} ms"
    return f"{sec * 1e6:.3g} µs"


def human(h: float | None) -> str:
    if h is None:
        return "-"
    if h >= 8760 * 2:
        return f"{h / 8760:.1f} years"
    if h >= 24 * 60:
        return f"{h / 24 / 30.44:.1f} months"
    if h >= 48:
        return f"{h / 24:.1f} days"
    return f"{h:.1f} hours"


def analyse(text: str, capacity_mah: Any = 0, usable_pct: Any = 80, self_discharge: Any = 2, volts: Any = 3.0, peak_ma: Any = 0, target: Any = "") -> dict[str, Any]:
    rows = parse(text)

    def num(v: Any, what: str, lo: float, hi: float, default: float) -> float:
        if v in (None, ""):
            return default
        try:
            x = float(v)
        except (TypeError, ValueError):
            raise PowerError(f"{what}: a number.")
        if not lo <= x <= hi:
            raise PowerError(f"{what}: {lo:g} to {hi:g}.")
        return x
    cap = num(capacity_mah, "Battery capacity (mAh)", 0, 1e7, 0)
    usable = num(usable_pct, "Usable share (%)", 1, 100, 80)
    sd = num(self_discharge, "Self-discharge (% a year)", 0, 100, 2)
    v = num(volts, "Battery voltage", 0.5, 60, 3.0)
    pk = num(peak_ma, "Battery's largest pulse (mA)", 0, 1e6, 0)
    tgt = None
    if str(target or "").strip():
        mt = re.fullmatch(r"\s*([\d.]+)\s*(y|yr|years?|m|months?|d|days?|h|hours?)?\s*", str(target).lower())
        if not mt:
            raise PowerError("Target life: e.g. 2 years, 6 months, 30 days.")
        u = (mt.group(2) or "y")[0]
        tgt = float(mt.group(1)) * {"y": 8760, "m": 730.5, "d": 24, "h": 1}[u]
    duty = sum(r["dur"] / r["per"] for r in rows if not r["base"])
    if duty > 1:
        raise PowerError(f"The active states add up to {100 * duty:.0f}% of the time - more than all of it.")
    avg = _avg(rows)
    base_sum = sum(r["mA"] for r in rows if r["base"])
    parts = []
    for i, r in enumerate(rows):
        share = (r["mA"] * r["dur"] / r["per"]) if not r["base"] else r["mA"] * max(0.0, 1 - duty)
        parts.append({**r, "avg": share, "pct": round(100 * share / avg, 1) if avg else 0, "duty": round(100 * r["dur"] / r["per"], 4) if not r["base"] else None,
                      "per_day": round(86400 / r["per"], 2) if not r["base"] else None, "mAh_day": share * 24})
    parts.sort(key=lambda x: -x["avg"])
    life = _life(avg, cap, usable, sd) if cap else None
    life_nosd = cap * usable / 100 / avg if cap and avg else None
    peak = max((r["mA"] for r in rows if not r["base"]), default=0) + 0.0
    issues: list[dict[str, Any]] = []
    whatif = []
    for i, r in enumerate(rows):
        if r["base"]:
            alt = [dict(x) for x in rows]
            alt[i]["mA"] = r["mA"] / 2
            a2 = _avg(alt)
            whatif.append({"change": f"Halve {r['name']} ({r['mA'] * 1000:.3g} µA → {r['mA'] * 500:.3g} µA)", "avg": a2, "life": _life(a2, cap, usable, sd) if cap else None})
        else:
            a2 = _avg(rows, {i: 2})
            whatif.append({"change": f"{r['name']} half as often (every {tfmt(r['per'] * 2e6)})", "avg": a2, "life": _life(a2, cap, usable, sd) if cap else None})
            alt = [dict(x) for x in rows]
            alt[i]["dur"] = r["dur"] / 2
            a3 = _avg(alt)
            whatif.append({"change": f"{r['name']} done in half the time ({tfmt(r['dur'] * 5e5)})", "avg": a3, "life": _life(a3, cap, usable, sd) if cap else None})
    whatif.sort(key=lambda x: x["avg"])
    whatif = whatif[:6]
    top = parts[0]
    if top["pct"] >= 50:
        issues.append({"sev": "info", "text": f"{top['name']} uses {top['pct']}% of the charge" + ("" if top["base"] else f" ({top['per_day']:g} times a day, {tfmt(top['dur'] * 1e6)} each)") + " - that is where saving pays."})
    if base_sum and base_sum * max(0, 1 - duty) / avg > 0.3:
        issues.append({"sev": "info", "text": f"Sleep / always-on current is {100 * base_sum * (1 - duty) / avg:.0f}% of the average - check every regulator, pull-up and sensor left powered in sleep."})
    if pk and peak > pk:
        issues.append({"sev": "bad", "text": f"The largest burst draws {peak:g} mA but the battery is given as {pk:g} mA at most - the voltage will sag and the device can brown out."})
    elif peak >= 10 and cap and cap <= 300:
        issues.append({"sev": "warn", "text": f"Bursts of {peak:g} mA from a {cap:g} mAh cell - a coin cell's real capacity drops a lot at high pulse current; add a capacitor across it or check the maker's pulse curve."})
    if sd and life and life > 8760 * 2:
        issues.append({"sev": "info", "text": f"Self-discharge ({sd:g}% a year) shortens the life from {human(life_nosd)} to {human(life)}."})
    if tgt and life is not None:
        if life < tgt:
            need = cap * usable / 100 / tgt - cap * sd / 100 / 8760
            issues.append({"sev": "bad", "text": f"{human(life)} is short of the {human(tgt)} target - the average must come down to {max(need, 0) * 1000:.3g} µA (now {avg * 1000:.3g} µA)."})
        else:
            issues.append({"sev": "info", "text": f"Meets the {human(tgt)} target with {100 * (life / tgt - 1):.0f}% to spare."})
    if not cap:
        issues.append({"sev": "info", "text": "Set the battery's capacity in mAh to see the life."})
    counts = {k: sum(1 for i in issues if i["sev"] == k) for k in ("bad", "warn", "info")}
    verdict = f"Average {avg * 1000:.4g} µA ({avg * 24:.3g} mAh a day)" + (f" - about {human(life)} on {cap:g} mAh" if life else "") + "."
    return {"rows": parts, "avg_mA": avg, "avg_uA": round(avg * 1000, 4), "mAh_day": avg * 24, "mWh_day": avg * 24 * v, "duty_pct": round(100 * duty, 4),
            "life_h": life, "life": human(life), "life_nosd_h": life_nosd, "peak_mA": peak, "capacity": cap, "usable": usable, "self_discharge": sd,
            "volts": v, "target_h": tgt, "whatif": whatif, "issues": issues, "counts": counts, "verdict": verdict,
            "note": ("Each state's current is counted only while it runs; the always-on lines fill the rest of the time. Measure the currents on the board (a current "
                     "probe or a power analyser over a whole cycle) - datasheet typicals are often far below real sleep current. Capacity falls in the cold and at "
                     "high pulse currents; the usable share covers the cut-off voltage and ageing.")}
