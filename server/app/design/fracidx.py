"""Fractional index strings: the order of siblings (contract section 1.3).

A key is a string over 0-9 A-Z a-z (which is also ASCII order) compared as a PLAIN STRING - the same in Python
and in the browser - and a key made here never ends in "0", so there is always room below it. This module follows
the scheme of `HD.frac` in hd-core.js, so a layer the server adds (a template, the AI) sits in the list as if a
browser had added it:

    a short counting head ("a1", "a2" ... "az", "b01" ...; below "a1": "Zz", "Zy" ...) so that adding at the top or
    the bottom 50,000 times still gives 4-character keys, plus a fraction tail for inserts in between ("a1V").

Only the ORDER is a contract between the two sides, not the exact keys: a neighbour of any other shape is
accepted (the plain string midpoint, or a one-digit step at an open end). `between` never raises - an order that
looks wrong (a >= b) still gets a usable key, exactly as in the browser.
"""
from __future__ import annotations

DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(DIGITS)
_VAL = {c: i for i, c in enumerate(DIGITS)}
_SMALLEST = "A" + "0" * 26
_FIRST = "a1"


def _digit(ch: str) -> int:
    value = _VAL.get(ch)
    if value is not None:
        return value
    return next((i for i in range(BASE - 1, -1, -1) if DIGITS[i] <= ch), 0)      # a foreign character


def _mid(a: str, b: str | None) -> str:
    """A string strictly between a ("" = lowest) and b (None = highest) in plain string order; never ends in "0"."""
    out, i = "", 0
    while True:
        ca = _digit(a[i]) if i < len(a) else 0
        if b is None:
            cb = BASE
        elif i < len(b):
            cb = _digit(b[i])
        else:
            return out + "V"                         # b is a + zeros: there is no room, stay next to it
        if ca == cb:
            out += DIGITS[ca]
            i += 1
            continue
        if cb < ca:
            return out + DIGITS[ca] + "V"            # not a < b: keep going, never raise
        if cb - ca > 1:
            return out + DIGITS[(ca + cb + 1) >> 1]
        if b is not None and len(b) > i + 1:
            return out + DIGITS[cb]
        out += DIGITS[ca]
        i += 1
        b = None


def _step_after(a: str) -> str:
    """One digit step above a key that is not in the counting shape (cheap repeated adds)."""
    head = 0
    while head < len(a) and _digit(a[head]) == BASE - 1:
        head += 1
    return a + "1" if head == len(a) else a[:head] + DIGITS[_digit(a[head]) + 1]


def _step_before(b: str) -> str:
    """One digit step below a key that is not in the counting shape."""
    head = 0
    while head < len(b) and _digit(b[head]) == 0:
        head += 1
    if head == len(b):
        return _mid("", b)
    d = _digit(b[head])
    return b[:head] + DIGITS[d - 1] if d > 1 else b[:head] + "0z"


def _head_len(key: str) -> int:
    """Length of the integer head: its first letter says how many digits follow ("a" 1, "b" 2 ...; "Z" 1, "Y" 2 ...)."""
    c = ord(key[0])
    if 97 <= c <= 122:
        return c - 97 + 2
    if 65 <= c <= 90:
        return 90 - c + 2
    return 0


def valid(key: object) -> bool:
    """A key in this module's own shape (integer head + optional fraction that does not end in "0")."""
    if not isinstance(key, str) or not key or key == _SMALLEST:
        return False
    head = _head_len(key)
    if not head or len(key) < head or any(c not in _VAL for c in key[1:]):
        return False
    return not (len(key) > head and key[-1] == "0")


def _inc1(head: str) -> str | None:
    first, digits = head[0], list(head[1:])
    for i in range(len(digits) - 1, -1, -1):
        value = _VAL[digits[i]] + 1
        if value < BASE:
            digits[i] = DIGITS[value]
            return first + "".join(digits)
        digits[i] = "0"
    if first == "Z":
        return "a0"
    if first == "z":
        return None
    nxt = chr(ord(first) + 1)
    if nxt > "a":
        digits.append("0")
    else:
        digits.pop()
    return nxt + "".join(digits)


def _dec1(head: str) -> str | None:
    first, digits = head[0], list(head[1:])
    for i in range(len(digits) - 1, -1, -1):
        value = _VAL[digits[i]] - 1
        if value >= 0:
            digits[i] = DIGITS[value]
            return first + "".join(digits)
        digits[i] = "z"
    if first == "a":
        return "Zz"
    if first == "A":
        return None
    prev = chr(ord(first) - 1)
    if prev < "Z":
        digits.append("z")
    else:
        digits.pop()
    return prev + "".join(digits)


def _inc(head: str) -> str | None:
    """The next counting head that does not end in "0"; None above the largest one."""
    nxt = _inc1(head)
    return _inc1(nxt) if nxt is not None and nxt[-1] == "0" else nxt


def _dec(head: str) -> str | None:
    """The counting head before this one that does not end in "0"; None below the smallest one."""
    prev = _dec1(head)
    return _dec1(prev) if prev is not None and prev[-1] == "0" else prev


def _key_between(a: str | None, b: str | None) -> str:
    if a is None:
        if b is None:
            return _FIRST
        ib = b[:_head_len(b)]
        if ib == _SMALLEST:
            return ib + _mid("", b[len(ib):])
        if ib < b:
            return ib
        prev = _dec(ib)
        return _mid("", b) if prev is None else prev
    ia = a[:_head_len(a)]
    fa = a[len(ia):]
    if b is None:
        nxt = _inc(ia)
        return ia + _mid(fa, None) if nxt is None else nxt
    ib = b[:_head_len(b)]
    if ia == ib:
        return ia + _mid(fa, b[len(ib):])
    nxt = _inc(ia)
    if nxt is not None and nxt < b:
        return nxt
    return ia + _mid(fa, None)


def between(a: str | None, b: str | None) -> str:
    """A key k with a < k < b. None (or "") = no neighbour on that side."""
    a, b = a or None, b or None
    if a is not None and b is not None:
        if a == b:
            return a + "V"                           # two equal keys: nothing fits, go right after them
        if a > b:
            a, b = b, a
    if (a is None or valid(a)) and (b is None or valid(b)):
        key = _key_between(a, b)
        if key[-1] != "0":
            return key
    elif b is None:
        return _FIRST if a < _FIRST else _step_after(a)          # on top of a key of another shape
    elif a is None:
        return _FIRST if b > _FIRST else _step_before(b)         # under a key of another shape
    return _mid(a or "", b)


def n_between(a: str | None, b: str | None, n: int) -> list[str]:
    """n keys in rising order, all between a and b."""
    if n <= 0:
        return []
    if n == 1:
        return [between(a, b)]
    a, b = a or None, b or None
    if b is None:
        out = [between(a, None)]
        while len(out) < n:
            out.append(between(out[-1], None))
        return out
    if a is None:
        out = [between(None, b)]
        while len(out) < n:
            out.append(between(None, out[-1]))
        return out[::-1]
    half = n >> 1
    mid = between(a, b)
    return n_between(a, mid, half) + [mid] + n_between(mid, b, n - half - 1)
