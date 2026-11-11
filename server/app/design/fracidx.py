"""Fractional index strings: the order of siblings (contract section 1.3).

A key is a string over 0-9 A-Z a-z read as the digits of a base-62 fraction (an implied "0." in front), so plain
string comparison IS numeric order - the same in Python and in the browser. A key never ends in "0": that keeps
room below every key, so there is always a key strictly between any two different keys.

`between(a, b)` works on ANY two keys of that alphabet, whoever made them (the browser makes most of them). When
one side is open it steps by one digit instead of halving: appending 1,000 layers costs ~17 characters, not ~170.
"""
from __future__ import annotations

DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(DIGITS)
_VAL = {c: i for i, c in enumerate(DIGITS)}
_FIRST, _LAST = DIGITS[1], DIGITS[-1]


def valid(key: object) -> bool:
    """A key this module can order: non-empty, only the 62 digits, no trailing zero."""
    return isinstance(key, str) and bool(key) and key[-1] != "0" and all(c in _VAL for c in key)


def _mid(a: str, b: str | None) -> str:
    """The shortest key strictly between a ("" = zero) and b (None = one); a < b is given."""
    if b is not None:
        n = 0
        while n < len(b) and (a[n] if n < len(a) else "0") == b[n]:
            n += 1
        if n:
            return b[:n] + _mid(a[n:], b[n:])
    da = _VAL[a[0]] if a else 0
    db = _VAL[b[0]] if b is not None else BASE
    if db - da > 1:
        return DIGITS[(da + db + 1) // 2]
    if b is not None and len(b) > 1:
        return b[0]
    return DIGITS[da] + _mid(a[1:], None)


def _after(a: str) -> str:
    """A key above a, one digit step away (cheap repeated appends)."""
    head = 0
    while head < len(a) and a[head] == _LAST:
        head += 1
    if head == len(a):
        return a + _FIRST
    return a[:head] + DIGITS[_VAL[a[head]] + 1]


def _before(b: str) -> str:
    """A key below b, one digit step away (cheap repeated prepends)."""
    head = 0
    while b[head] == "0":                    # a key never ends in "0", so this stops inside it
        head += 1
    d = _VAL[b[head]]
    if d > 1:
        return b[:head] + DIGITS[d - 1]
    return b[:head] + "0" + _LAST


def between(a: str | None, b: str | None) -> str:
    """A key k with a < k < b. None = no neighbour on that side."""
    if a is not None and not valid(a):
        raise ValueError(f"not a fractional index: {a!r}")
    if b is not None and not valid(b):
        raise ValueError(f"not a fractional index: {b!r}")
    if a is None and b is None:
        return DIGITS[BASE // 2]
    if b is None:
        return _after(a)
    if a is None:
        return _before(b)
    if a >= b:
        raise ValueError(f"no key between {a!r} and {b!r}")
    return _mid(a, b)


def n_between(a: str | None, b: str | None, n: int) -> list[str]:
    """n keys in rising order, all strictly between a and b."""
    if n <= 0:
        return []
    if b is None:                            # an open top: n cheap steps
        out: list[str] = []
        cur = a
        for _ in range(n):
            cur = between(cur, None)
            out.append(cur)
        return out
    mid = between(a, b)
    left = (n - 1) // 2
    return n_between(a, mid, left) + [mid] + n_between(mid, b, n - 1 - left)
