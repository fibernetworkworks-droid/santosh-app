"""v0.999.171 PAYROLL FOR EVERY SIZE - pay as building blocks: each part of a person's pay is a short formula worked out by plain code.

A formula is a small, safe expression over named numbers:

    overtime_hours * (basic / 208) * 1.5
    pieces_made * 12
    late_days >= 3 ? 0.5 * day_pay : 0          (also: 0.5 * day_pay if late_days >= 3 else 0)
    min(advance_left, 2000)

Allowed: numbers, names, + - * / // %, brackets, comparisons, and / or / not, `a ? b : c` or `b if a else c`, and the functions
min, max, round(x, digits), floor, ceil, abs, clamp(x, lo, hi). Nothing else is ever run - no attribute, no index, no import, no
call outside that list. A formula naming a word it does not know is refused when it is saved, with the word named; division by
zero gives 0 and says so. All arithmetic is Decimal, so 0.1 + 0.2 is 0.3."""
from __future__ import annotations

import ast
import math
import re
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any


class FormulaError(ValueError):
    pass


FUNCS = {"min", "max", "round", "floor", "ceil", "abs", "clamp"}
MAX_LEN = 400
_TERNARY = re.compile(r"^(?P<c>[^?]+)\?(?P<a>[^:]+):(?P<b>.+)$")


def snake(name: Any) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")
    return ("p_" + s) if s[:1].isdigit() else s


def _ternary(src: str) -> str:
    """`c ? a : b` (one level, possibly nested on the right) -> Python's `(a) if (c) else (b)`."""
    m = _TERNARY.match(src.strip())
    if not m:
        return src
    return f"({m.group('a').strip()}) if ({m.group('c').strip()}) else ({_ternary(m.group('b').strip())})"


def parse(src: str) -> ast.Expression:
    s = str(src or "").strip()
    if not s:
        raise FormulaError("The formula is empty.")
    if len(s) > MAX_LEN:
        raise FormulaError(f"A formula is at most {MAX_LEN} characters.")
    s = s.replace("×", "*").replace("÷", "/").replace("&&", " and ").replace("||", " or ")
    if "?" in s:
        s = _ternary(s)
    try:
        tree = ast.parse(s, mode="eval")
    except SyntaxError:
        raise FormulaError("The formula could not be read. Use numbers, names, + - * /, brackets, min / max / round, and `a ? b : c`.")
    for n in ast.walk(tree):
        if isinstance(n, (ast.Expression, ast.Load, ast.Name, ast.Constant, ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.IfExp,
                          ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
                          ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
            if isinstance(n, ast.Constant) and not (isinstance(n.value, (int, float)) and not isinstance(n.value, bool)):
                raise FormulaError("Only numbers can be written in a formula.")
            continue
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name) or n.func.id not in FUNCS or n.keywords:
                raise FormulaError("Only these functions can be used: " + ", ".join(sorted(FUNCS)) + ".")
            continue
        raise FormulaError("This formula uses something that is not allowed (" + type(n).__name__ + ").")
    return tree


def check(src: str, known: set[str]) -> list[str]:
    """Words in the formula that are not known numbers (empty = fine)."""
    tree = parse(src)
    used = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            continue
        if isinstance(n, ast.Name) and n.id not in FUNCS:
            used.add(n.id)
    return sorted(used - set(known))


def _d(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    if isinstance(v, bool):
        return Decimal(int(v))
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        raise FormulaError(f"Not a number: {str(v)[:20]}")


def evaluate(src: str, env: dict[str, Any], notes: list[str] | None = None) -> Decimal:
    tree = parse(src)
    vals = {k: _d(v) for k, v in env.items()}

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return _d(n.value)
        if isinstance(n, ast.Name):
            if n.id not in vals:
                raise FormulaError(f"`{n.id}` is not a known number here.")
            return vals[n.id]
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            if isinstance(n.op, ast.Not):
                return Decimal(0 if v else 1)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if b == 0:
                if notes is not None:
                    notes.append("a division by zero counted as 0")
                return Decimal(0)
            if isinstance(n.op, ast.Div):
                return a / b
            if isinstance(n.op, ast.FloorDiv):
                return (a / b).to_integral_value(ROUND_FLOOR)
            return a % b
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for op, r in zip(n.ops, n.comparators):
                right = ev(r)
                ok = {ast.Eq: left == right, ast.NotEq: left != right, ast.Lt: left < right, ast.LtE: left <= right,
                      ast.Gt: left > right, ast.GtE: left >= right}[type(op)]
                if not ok:
                    return Decimal(0)
                left = right
            return Decimal(1)
        if isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                for v in n.values:
                    if not ev(v):
                        return Decimal(0)
                return Decimal(1)
            for v in n.values:
                if ev(v):
                    return Decimal(1)
            return Decimal(0)
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, ast.Call):
            f, args = n.func.id, [ev(x) for x in n.args]
            if f in ("min", "max"):
                if not args:
                    raise FormulaError(f"{f}() needs numbers.")
                return min(args) if f == "min" else max(args)
            if f == "abs":
                return abs(args[0])
            if f in ("floor", "ceil"):
                return args[0].to_integral_value(ROUND_FLOOR if f == "floor" else ROUND_CEILING)
            if f == "round":
                digits = int(args[1]) if len(args) > 1 else 0
                return args[0].quantize(Decimal(1).scaleb(-digits), ROUND_HALF_UP)
            if f == "clamp":
                if len(args) != 3:
                    raise FormulaError("clamp(x, lowest, highest).")
                return max(args[1], min(args[0], args[2]))
        raise FormulaError("This formula uses something that is not allowed.")

    out = ev(tree)
    if not math.isfinite(float(out)):
        raise FormulaError("The formula did not give a number.")
    return out
