"""v0.691.0 LEADS DESK EMPTY - the desk rendered 'Loading…' FOREVER with all three fetches 200 (the owner's
second screenshot; reproduced end-to-end in a real browser against the real app). ROOT CAUSE, caught live:
`ReferenceError: empty is not defined at Object.leads` - the desk called `empty(...)`, which is the EDUCATION
desk's LOCAL helper (`const empty = ...` inside `async function edu(el)`), invisible from the leads desk. The
first paint put the Loading div up; the render threw before the first `innerHTML =`; the promise rejected
unhandled; the desk looked dead while the network tab was green. The string-presence tests never ran the JS,
so they passed both this and the v0.688 route bug.

THE FIX: the desk carries its own `empty` (the same helper, the same pattern edu uses).
THE GUARD: NEW test_v0690_leads_desk_scope.py - every function the desk body calls must be REACHABLE: a
destructured param of the HoolaEmployees wrapper, a definition at the wrapper's own scope, or a definition
inside the desk body itself. A helper that lives only inside ANOTHER desk's closure fails this test.

Zero network."""
from __future__ import annotations

import re
from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
EMP = (CON / "employees.js").read_text(encoding="utf-8")

JS_KEYWORDS_AND_BUILTINS = {
    "if", "for", "while", "switch", "catch", "function", "return", "typeof", "new", "await", "async",
    "fetch", "encodeURIComponent", "decodeURIComponent", "String", "Number", "Boolean", "Object", "Array",
    "Date", "Promise", "parseInt", "parseFloat", "isNaN", "JSON", "Math", "Set", "Map", "AbortController",
    "setTimeout", "clearTimeout", "setInterval", "clearInterval", "require", "console", "alert", "confirm",
    "localStorage", "sessionStorage", "location", "history", "navigator", "window", "document",
    # method-shaped words that can also appear bare in templates stay excluded only when called on a dot;
    # these appear bare in the desk body as plain calls and must be checked like any other name:
}


def desk_body() -> str:
    start = EMP.index("async function leads(el)")
    return EMP[start:]


def wrapper_params() -> set[str]:
    m = re.search(r"window\.HoolaEmployees = function \(\{([^}]*)\}", EMP)
    return {p.strip().split(":")[0].strip() for p in m.group(1).split(",") if p.strip()}


# ------------------------------------------------------- the fix itself, pinned
def test_the_desk_carries_its_own_empty_helper():
    body = desk_body()
    assert "const empty = t => `<p class=\"muted em-small\">${esc(t)}</p>`;" in body
    # the desk really calls it (the fix is not dead code)
    assert body.count("empty('") + body.count("empty(`") >= 3
    # and the module scope does NOT define one the desk could have been assuming
    assert not re.search(r"^  (const|function) empty\b", EMP, re.M)


# ------------------------------------- the guard: every helper the desk calls must be REACHABLE
def test_every_function_the_desk_calls_is_reachable():
    body = desk_body()
    params = wrapper_params()
    called = set(re.findall(r"(?<![\w.$])([a-z_][a-z0-9_]*)\(", body))   # real calls: no space before ( (prose says "today (cap")
    unreachable = []
    for name in sorted(called - JS_KEYWORDS_AND_BUILTINS):
        if name in params:
            continue
        if re.search(rf"^  (const|let|var|function) {name}\b", EMP, re.M):   # the wrapper's own scope
            continue
        if re.search(rf"\b(const|let|var|function) {name}\b", body):          # defined inside the desk itself
            continue
        unreachable.append(name)
    assert not unreachable, f"the desk calls helpers it cannot see: {unreachable}"


# ------------------------------------- the seam test from v0.689 still holds (routes vs sources)
def test_the_seam_law_still_stands():
    from tests.test_v0689_leads_desk_seam import desk_calls, route_table, THE_FIRST_LOAD  # noqa: PLC0415
    table = route_table()
    for path, method in desk_calls():
        assert (path, method) in table, f"console calls {method} {path} - no such route"
    calls = set(desk_calls())
    for path, method in THE_FIRST_LOAD:
        assert (path, method) in calls
