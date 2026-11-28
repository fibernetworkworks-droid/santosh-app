"""Clock sums an embedded engineer does by hand: UART baud dividers (fractional like STM32, integer like AVR UBRR) with the real
baud rate and its error, timer prescaler + auto-reload pairs for an exact frequency, PWM resolution, SysTick reload, SPI
power-of-two dividers and ADC step size - one per line, each worked out exactly."""
from __future__ import annotations

import math
import re
from typing import Any


class ClockError(ValueError):
    pass


def _hz(tok: str, what: str) -> float:
    m = re.fullmatch(r"([\d.]+)\s*(hz|khz|mhz|ghz)?", tok.lower())
    if not m:
        raise ClockError(f"{what}: a frequency like 72MHz or 115200 (got {tok}).")
    return float(m.group(1)) * {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9, None: 1}[m.group(2)]


def _sec(tok: str) -> float | None:
    m = re.fullmatch(r"([\d.]+)\s*(ns|us|µs|ms|s)", tok.lower())
    return float(m.group(1)) * {"ns": 1e-9, "us": 1e-6, "µs": 1e-6, "ms": 1e-3, "s": 1.0}[m.group(2)] if m else None


def f_hz(x: float) -> str:
    if x >= 1e6:
        return f"{x / 1e6:.6g} MHz"
    if x >= 1e3:
        return f"{x / 1e3:.6g} kHz"
    return f"{x:.6g} Hz"


def uart(clk: float, baud: float, over: int = 16) -> dict[str, Any]:
    rows = []
    div = clk / (over * baud)
    if div < 1:
        raise ClockError(f"{f_hz(clk)} is too slow for {baud:g} baud with {over}x oversampling.")
    fb = 4 if over == 16 else 3
    mant = int(div)
    frac = round((div - mant) * (1 << fb))
    if frac == 1 << fb:
        mant, frac = mant + 1, 0
    act = clk / (over * (mant + frac / (1 << fb)))
    brr = (mant << 4) | (frac if over == 16 else frac & 7)
    rows.append({"way": f"Fractional divider ({over}x, like STM32 USART)", "setting": f"BRR = 0x{brr:X} (mantissa {mant}, fraction {frac}/{1 << fb})",
                 "actual": act, "error": 100 * (act - baud) / baud})
    ub = round(clk / (over * baud)) - 1
    if ub >= 0:
        act2 = clk / (over * (ub + 1))
        rows.append({"way": f"Integer divider ({over}x, like AVR UBRR{' with U2X' if over == 8 else ''})", "setting": f"UBRR = {ub}", "actual": act2,
                     "error": 100 * (act2 - baud) / baud})
    whole = round(clk / baud)
    act3 = clk / whole
    rows.append({"way": "Plain divider (clock / baud, like many newer UARTs)", "setting": f"DIV = {whole}", "actual": act3, "error": 100 * (act3 - baud) / baud})
    return {"rows": rows}


def timer(clk: float, target: float, bits: int = 16, psc_bits: int = 16) -> dict[str, Any]:
    ticks = clk / target
    top = (1 << bits)
    pmax = (1 << psc_bits)
    opts = []
    for p in range(1, pmax + 1):
        a = ticks / p
        if a > top:
            continue
        if a < 2:
            break
        ar = round(a)
        act = clk / (p * ar)
        err = 100 * (act - target) / target
        opts.append({"psc": p - 1, "arr": ar - 1, "actual": act, "error": err, "res_bits": math.log2(ar)})
        if len(opts) > 4000:
            break
    if not opts:
        raise ClockError(f"{f_hz(target)} cannot be made from {f_hz(clk)} with a {bits}-bit counter and a {psc_bits}-bit prescaler.")
    exact = [o for o in opts if abs(o["error"]) < 1e-9]
    pool = exact or sorted(opts, key=lambda o: (abs(o["error"]), -o["res_bits"]))[:20]
    best = sorted(pool, key=lambda o: (abs(o["error"]) > 1e-9, -o["res_bits"]))
    return {"rows": [{"way": f"PSC = {o['psc']}, ARR = {o['arr']}", "setting": f"counts {o['arr'] + 1} ticks of {f_hz(clk / (o['psc'] + 1))}",
                      "actual": o["actual"], "error": o["error"], "res_bits": round(o["res_bits"], 2)} for o in best[:6]], "exact": bool(exact), "choices": len(exact)}


def pwm(clk: float, target: float, bits: int = 16) -> dict[str, Any]:
    counts = clk / target
    rows = []
    if counts < 2:
        raise ClockError(f"{f_hz(target)} PWM is faster than half of {f_hz(clk)}.")
    if counts <= (1 << bits):
        n = round(counts)
        act = clk / n
        rows.append({"way": "No prescaler", "setting": f"ARR = {n - 1}", "actual": act, "error": 100 * (act - target) / target, "res_bits": round(math.log2(n), 2),
                     "step": 100 / n})
    else:
        p = math.ceil(counts / (1 << bits))
        n = round(counts / p)
        act = clk / (p * n)
        rows.append({"way": f"Prescaler / {p}", "setting": f"PSC = {p - 1}, ARR = {n - 1}", "actual": act, "error": 100 * (act - target) / target,
                     "res_bits": round(math.log2(n), 2), "step": 100 / n})
    return {"rows": rows}


def systick(clk: float, period: float) -> dict[str, Any]:
    reload = round(clk * period) - 1
    rows = []
    if reload < 1:
        raise ClockError("The tick is shorter than one clock.")
    if reload > (1 << 24) - 1:
        for d in (8,):
            r2 = round(clk / d * period) - 1
            if r2 <= (1 << 24) - 1:
                act = (r2 + 1) / (clk / d)
                rows.append({"way": f"Clock / {d}", "setting": f"LOAD = {r2}", "actual": 1 / act, "error": 100 * (act - period) / period})
        if not rows:
            raise ClockError("Longer than SysTick's 24-bit reload can count at this clock.")
    else:
        act = (reload + 1) / clk
        rows.append({"way": "Processor clock", "setting": f"LOAD = {reload}", "actual": 1 / act, "error": 100 * (act - period) / period})
    return {"rows": rows}


def spi(clk: float, target: float) -> dict[str, Any]:
    rows = []
    for k in range(1, 9):
        d = 1 << k
        f = clk / d
        rows.append({"way": f"/ {d}", "setting": f"BR = {k - 1}", "actual": f, "error": 100 * (f - target) / target, "ok": f <= target})
    below = [r for r in rows if r["ok"]]
    pick = below[0] if below else rows[-1]
    return {"rows": [pick] + [r for r in rows if r is not pick][:5], "best": pick}


def adc(bits: int, vref: float) -> dict[str, Any]:
    step = vref / (1 << bits)
    return {"rows": [{"way": f"{bits}-bit, {vref:g} V reference", "setting": f"1 step = {step * 1000:.4g} mV", "actual": None, "error": None,
                      "note": f"Full scale {(1 << bits) - 1} counts; ±½ step quantisation = ±{step * 500:.3g} mV. Real accuracy also needs the reference's tolerance, offset and gain errors."}]}


def analyse(text: str, clock: Any = "") -> dict[str, Any]:
    out, issues = [], []
    default_clk = _hz(str(clock), "Clock") if str(clock or "").strip() else None
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        ln = raw.split("#")[0].strip()
        if not ln:
            continue
        s = re.sub(r"(\d)\s+(hz|khz|mhz|ghz|ns|us|µs|ms|s|v|bit|bits)\b", r"\1\2", ln, flags=re.I)
        toks = re.split(r"[\s,;=]+", s)
        kind = toks[0].lower()
        rest = toks[1:]
        freqs = [t for t in rest if re.fullmatch(r"[\d.]+\s*(?:hz|khz|mhz|ghz)", t.lower())]
        nums = [t for t in rest if re.fullmatch(r"[\d.]+", t)]
        bits = next((int(re.match(r"\d+", t).group()) for t in rest if re.fullmatch(r"\d+-?bits?", t.lower())), None)
        over = 8 if any(t.lower() in ("over8", "x8", "u2x") for t in rest) else 16

        def clk_and(need: int) -> tuple[float, list[float]]:
            vals = [_hz(t, kind) for t in freqs] + [float(t) for t in nums]
            if default_clk and len(vals) == need:
                return default_clk, vals
            if len(vals) < need + 1:
                raise ClockError(f"Line {n}: give the clock and the target, e.g. '{kind} 72MHz " + ("115200" if kind == "uart" else "1kHz") + "'.")
            return vals[0], vals[1:]
        try:
            if kind in ("uart", "usart", "baud", "serial"):
                clk, rest_v = clk_and(1)
                r = uart(clk, rest_v[0], over)
                title = f"UART {rest_v[0]:g} baud from {f_hz(clk)}"
                best = min(r["rows"], key=lambda x: abs(x["error"]))
                for x in r["rows"]:
                    x["state"] = "bad" if abs(x["error"]) > 2 else "warn" if abs(x["error"]) > 1 else "ok"
                if abs(best["error"]) > 2:
                    issues.append({"sev": "bad", "text": f"{title}: the closest divider is {best['error']:+.2f}% off - over the ±2% a UART link tolerates with the other side's error added."})
                elif abs(best["error"]) > 1:
                    issues.append({"sev": "warn", "text": f"{title}: {best['error']:+.2f}% off at best - fine only if the other side is close to exact."})
            elif kind in ("timer", "tim", "freq", "frequency"):
                clk, rest_v = clk_and(1)
                r = timer(clk, rest_v[0], bits or 16)
                title = f"Timer {f_hz(rest_v[0])} from {f_hz(clk)} ({bits or 16}-bit)"
                for x in r["rows"]:
                    x["state"] = "ok" if abs(x["error"]) < 1e-9 else "warn"
                if not r["exact"]:
                    issues.append({"sev": "warn" if abs(r["rows"][0]["error"]) >= 0.1 else "info", "text": f"{title}: no exact setting - the nearest is {r['rows'][0]['error']:+.4f}% off."})
            elif kind == "pwm":
                clk, rest_v = clk_and(1)
                r = pwm(clk, rest_v[0], bits or 16)
                title = f"PWM {f_hz(rest_v[0])} from {f_hz(clk)}"
                for x in r["rows"]:
                    x["state"] = "warn" if x["res_bits"] < 8 else "ok"
                    if x["res_bits"] < 8:
                        issues.append({"sev": "warn", "text": f"{title}: only {x['res_bits']:g} bits of duty resolution ({x['step']:.2g}% a step) - lower the frequency or raise the timer clock."})
            elif kind in ("systick", "tick"):
                per = next((_sec(t) for t in rest if _sec(t) is not None), None)
                if per is None:
                    raise ClockError(f"Line {n}: the tick length, e.g. 'systick 72MHz 1ms'.")
                clk = _hz(freqs[0], "Clock") if freqs else (default_clk or 0)
                if not clk:
                    raise ClockError(f"Line {n}: the clock, e.g. 'systick 72MHz 1ms'.")
                r = systick(clk, per)
                title = f"SysTick {per * 1e3:g} ms from {f_hz(clk)}"
                for x in r["rows"]:
                    x["state"] = "ok" if abs(x["error"]) < 1e-6 else "warn"
            elif kind == "spi":
                clk, rest_v = clk_and(1)
                r = spi(clk, rest_v[0])
                title = f"SPI at most {f_hz(rest_v[0])} from {f_hz(clk)}"
                for x in r["rows"]:
                    x["state"] = "ok" if x is r["best"] else ("bad" if not x["ok"] else "")
            elif kind == "adc":
                v = next((float(t[:-1]) for t in rest if re.fullmatch(r"[\d.]+v", t.lower())), None)
                if not bits or v is None:
                    raise ClockError(f"Line {n}: e.g. 'adc 12bit 3.3V'.")
                r = adc(bits, v)
                title = f"ADC {bits}-bit at {v:g} V"
                for x in r["rows"]:
                    x["state"] = "ok"
            else:
                raise ClockError(f"Line {n}: start with uart, timer, pwm, systick, spi or adc.")
        except ClockError:
            raise
        out.append({"line": n, "kind": kind if kind not in ("usart", "baud", "serial") else "uart", "title": title, **{k: v for k, v in r.items() if k != "best"}})
    if not out:
        raise ClockError("One sum per line, e.g. 'uart 72MHz 115200', 'timer 84MHz 1kHz 16bit', 'pwm 72MHz 20kHz', 'systick 72MHz 1ms', 'spi 48MHz 10MHz', 'adc 12bit 3.3V'.")
    counts = {k: sum(1 for i in issues if i["sev"] == k) for k in ("bad", "warn", "info")}
    verdict = f"{len(out)} sum(s) worked out" + (f": {counts['bad']} out of tolerance, {counts['warn']} to look at." if counts["bad"] or counts["warn"] else ", all within tolerance.")
    return {"results": out, "issues": issues, "counts": counts, "verdict": verdict,
            "note": "Worked out from the clock given - the real clock also carries the crystal's or the internal oscillator's tolerance (an internal RC is often ±1-2%), which adds to a UART's error."}
