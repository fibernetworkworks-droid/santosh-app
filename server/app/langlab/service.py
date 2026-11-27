"""The Compiler Construction Engineer's engine: her languages (DSLs) - grammar, interpreter or compiler, golden tests,
checks, fuzzing, a spec with railroad diagrams, editor support and a zip that runs anywhere.

- The grammar is read and checked by OUR OWN parser generator (hoola_lang.py): undefined names, left recursion, loops that
  match nothing, choices that can never win, slow token patterns, unused rules. Parsing runs in-process with a step limit.
- HER interpreter (Python, written by her or by the model) runs ONLY in the locked sandbox (app.pylab.runner: no network, no
  secrets, no server files, CPU / memory / time limits) with a time limit per test - never in Hoola's own process.
- A change the model proposes is kept only when it does not make more tests fail than before; otherwise it waits as a
  proposal she can apply or drop. Every save is a version; any version can come back.
- Nothing here spends money (only model calls, counted as feature 'langlab') and nothing is sent or published.
"""
from __future__ import annotations

import io
import json
import logging
import random
import re
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import ai, railroad
from . import hoola_lang as HL

log = logging.getLogger("santosh.langlab")

KINDS = ("output", "error", "tree")
MAX_TESTS = 200
MAX_INTERP = 60_000
KEEP_VERSIONS = 40
STATS = {"runs": 0, "designs": 0, "improves": 0, "kept": 0, "held": 0}
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="langlab")
_LOCK = threading.Lock()
RUNTIME = Path(__file__).with_name("hoola_lang.py")


class LangLabError(Exception):
    pass


class Lang(Base):
    __tablename__ = "langlab_langs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lng"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    name: Mapped[str] = mapped_column(String(80), default="")
    purpose: Mapped[str] = mapped_column(Text, default="")
    ext: Mapped[str] = mapped_column(String(16), default="")
    start: Mapped[str] = mapped_column(String(60), default="")
    grammar: Mapped[str] = mapped_column(Text, default="")
    interpreter: Mapped[str] = mapped_column(Text, default="")
    tests: Mapped[list] = mapped_column(JSON, default=list)
    versions: Mapped[list] = mapped_column(JSON, default=list)
    last_run: Mapped[dict] = mapped_column(JSON, default=dict)
    fuzz: Mapped[dict] = mapped_column(JSON, default=dict)
    proposal: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="ready")     # designing | improving | ready | failed
    job: Mapped[str] = mapped_column(Text, default="")                    # what the running job is / why it failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LangSettings(Base):
    __tablename__ = "langlab_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    limit_s: Mapped[int] = mapped_column(Integer, default=2)
    fuzz_n: Mapped[int] = mapped_column(Integer, default=40)
    target: Mapped[str] = mapped_column(String(40), default="interpreter")    # interpreter | compiler


_READY: set[int] = set()


def _tables() -> None:
    """Registered in db.init_db AND self-healing here (the first touch after a deploy creates the tables)."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    Lang.__table__.create(eng, checkfirst=True)
    LangSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


# ---------------------------------------------------------------- settings
def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(LangSettings, tenant)
        return {"limit_s": (r.limit_s if r else 2) or 2, "fuzz_n": (r.fuzz_n if r else 40) or 40,
                "target": (r.target if r else "interpreter") or "interpreter", "set": r is not None}


def save_settings(tenant: str, limit_s: Any = None, fuzz_n: Any = None, target: Any = None) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(LangSettings, tenant)
        if r is None:
            r = LangSettings(tenant_id=tenant)
            s.add(r)
        if limit_s not in (None, ""):
            try:
                v = float(limit_s)
            except (TypeError, ValueError):
                raise LangLabError("Time per test: a number of seconds (1 to 10).")
            if not 1 <= v <= 10:
                raise LangLabError("Time per test: 1 to 10 seconds.")
            r.limit_s = int(v)
        if fuzz_n not in (None, ""):
            try:
                n = int(fuzz_n)
            except (TypeError, ValueError):
                raise LangLabError("Example programs per check: 10 to 200.")
            if not 10 <= n <= 200:
                raise LangLabError("Example programs per check: 10 to 200.")
            r.fuzz_n = n
        if target not in (None, ""):
            if target not in ("interpreter", "compiler"):
                raise LangLabError("What a program does when it runs: interpreter (runs it) | compiler (prints code).")
            r.target = target
    return settings(tenant)


# ---------------------------------------------------------------- the grammar
def check_grammar(text: str, start: str = "") -> dict[str, Any]:
    """Read + check a grammar. {ok, errors[], warnings[], rules[], tokens[], keywords[], start}"""
    try:
        g = HL.load(text, start)
    except HL.GrammarError as e:
        return {"ok": False, "errors": [{"line": e.line, "rule": "", "say": e.msg}], "warnings": [], "rules": [], "tokens": [],
                "keywords": [], "start": start}
    c = g.check()
    return {"ok": not c["errors"], "errors": c["errors"], "warnings": c["warnings"], "start": g.start,
            "rules": [{"name": n, "line": r.line, "inline": r.inline, "keep": r.keep, "ebnf": g.ebnf(r.expr)} for n, r in g.rules.items()],
            "tokens": [{"name": n, "pattern": t.pattern, "regex": t.regex, "line": t.line, "example": g.sample_token(n)}
                       for n, t in g.tokens.items()],
            "keywords": sorted(g.keywords), "ignore": g.ignore_src}


def _grammar(lang: dict[str, Any]) -> HL.Grammar:
    try:
        g = HL.load(lang["grammar"], lang.get("start") or "")
    except HL.GrammarError as e:
        raise LangLabError(f"The grammar does not read: {e}")
    c = g.check()
    if c["errors"]:
        raise LangLabError("The grammar has problems: " + "; ".join(x["say"] for x in c["errors"][:3]))
    return g


def parse(tenant: str, lid: str, src: str) -> dict[str, Any]:
    lang = get(tenant, lid)
    g = _grammar(lang)
    t0 = time.perf_counter()
    try:
        tree = g.parse(str(src or ""))
    except HL.ParseError as e:
        return {"ok": False, "error": e.as_dict(), "ms": round((time.perf_counter() - t0) * 1000, 1)}
    return {"ok": True, "tree": HL.sexp(tree), "json": HL.to_json(tree), "ms": round((time.perf_counter() - t0) * 1000, 1)}


def railroads(tenant: str, lid: str) -> list[dict[str, Any]]:
    lang = get(tenant, lid)
    try:
        g = HL.load(lang["grammar"], lang.get("start") or "")
    except HL.GrammarError:
        return []
    return [{"rule": n, "ebnf": g.ebnf(r.expr), "svg": railroad.svg(g.shape(r.expr), styled=False)} for n, r in g.rules.items()]


# ---------------------------------------------------------------- languages
def _view(r: Lang) -> dict[str, Any]:
    tests = list(r.tests or [])
    run = dict(r.last_run or {})
    return {"id": r.id, "number": r.number, "name": r.name, "purpose": r.purpose, "ext": r.ext, "start": r.start,
            "grammar": r.grammar, "interpreter": r.interpreter, "tests": tests, "status": r.status, "job": r.job,
            "versions": [{k: v for k, v in x.items() if k in ("n", "at", "note", "passed", "failed")} for x in (r.versions or [])],
            "version": len(r.versions or []), "last_run": run, "fuzz": dict(r.fuzz or {}), "proposal": dict(r.proposal or {}),
            "passed": run.get("passed", 0), "failed": run.get("failed", 0), "total": len(tests),
            "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else ""}


def langs(tenant: str, limit: int = 60) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        rows = s.scalars(select(Lang).where(Lang.tenant_id == tenant).order_by(Lang.updated_at.desc()).limit(limit)).all()
        return [_view(r) for r in rows]


def _row(s, tenant: str, lid: str) -> Lang:
    r = s.get(Lang, str(lid or ""))
    if r is None or r.tenant_id != tenant:
        q = s.scalars(select(Lang).where(Lang.tenant_id == tenant, Lang.number == str(lid or "").upper())).first()
        if q is None:
            raise LangLabError("No such language.")
        r = q
    return r


def get(tenant: str, lid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        return _view(_row(s, tenant, lid))


def _clean_tests(tests: Any) -> list[dict[str, Any]]:
    out = []
    for t in (tests if isinstance(tests, list) else [])[:MAX_TESTS]:
        if not isinstance(t, dict):
            continue
        src = str(t.get("src") or "")[:20000]
        kind = str(t.get("kind") or "output")
        if kind not in KINDS:
            kind = "output"
        out.append({"id": str(t.get("id") or new_id("t"))[:40], "name": str(t.get("name") or "")[:80] or "Test",
                    "src": src, "kind": kind, "expect": str(t.get("expect") if t.get("expect") is not None else "")[:20000]})
    return out


def _number(s, tenant: str) -> str:
    n = len(s.scalars(select(Lang.id).where(Lang.tenant_id == tenant)).all()) + 1
    return f"L-{n:04d}"


def _snap(r: Lang, note: str) -> None:
    v = list(r.versions or [])
    run = r.last_run or {}
    v.append({"n": (v[-1]["n"] + 1) if v else 1, "at": now().isoformat(), "note": note[:200], "grammar": r.grammar,
              "interpreter": r.interpreter, "start": r.start, "passed": run.get("passed", 0), "failed": run.get("failed", 0)})
    r.versions = v[-KEEP_VERSIONS:]


def create(tenant: str, name: str, purpose: str = "", grammar: str = "", interpreter: str = "", start: str = "",
           tests: Any = None, ext: str = "", note: str = "Started") -> dict[str, Any]:
    _tables()
    name = str(name or "").strip()[:80]
    if not name:
        raise LangLabError("A language needs a name.")
    if len(interpreter or "") > MAX_INTERP:
        raise LangLabError("The interpreter is longer than 60,000 characters.")
    with session() as s:
        r = Lang(tenant_id=tenant, number=_number(s, tenant), name=name, purpose=str(purpose or "")[:600],
                 ext=_ext(ext or name), start=str(start or "")[:60], grammar=str(grammar or ""), interpreter=str(interpreter or ""),
                 tests=_clean_tests(tests), versions=[], status="ready")
        s.add(r)
        s.flush()
        _snap(r, note)
        lid = r.id
    if grammar:
        try:
            run_tests(tenant, lid)
        except LangLabError:
            pass
    return get(tenant, lid)


def _ext(x: str) -> str:
    x = re.sub(r"[^a-z0-9]", "", str(x or "").lower())[:10]
    return x or "dsl"


def save(tenant: str, lid: str, **f: Any) -> dict[str, Any]:
    """Change name / purpose / ext / start / grammar / interpreter. A grammar or interpreter change is a new version."""
    _tables()
    with session() as s:
        r = _row(s, tenant, lid)
        if r.status in ("designing", "improving"):
            raise LangLabError("Hoola is working on this language now - wait for it to finish.")
        code_changed = False
        for k in ("name", "purpose", "ext", "start", "grammar", "interpreter"):
            if k in f and f[k] is not None:
                v = str(f[k])
                if k == "name" and not v.strip():
                    raise LangLabError("A language needs a name.")
                if k == "interpreter" and len(v) > MAX_INTERP:
                    raise LangLabError("The interpreter is longer than 60,000 characters.")
                if k == "ext":
                    v = _ext(v)
                if getattr(r, k) != v:
                    setattr(r, k, v[:80] if k == "name" else v)
                    code_changed |= k in ("grammar", "interpreter", "start")
        r.updated_at = now()
        if code_changed:
            _snap(r, str(f.get("note") or "Changed by hand"))
        lid = r.id
    if code_changed:
        try:
            run_tests(tenant, lid)
        except LangLabError:
            pass
    return get(tenant, lid)


def delete(tenant: str, lid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = _row(s, tenant, lid)
        s.delete(r)
    return {"ok": True, "say": "The language and its tests were removed."}


def restore(tenant: str, lid: str, n: int) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = _row(s, tenant, lid)
        v = next((x for x in (r.versions or []) if int(x.get("n") or 0) == int(n)), None)
        if v is None:
            raise LangLabError("No such version.")
        r.grammar, r.interpreter, r.start = v["grammar"], v["interpreter"], v.get("start") or ""
        r.updated_at = now()
        _snap(r, f"Brought back version {n}")
        lid = r.id
    run_tests(tenant, lid)
    return get(tenant, lid)


# ---------------------------------------------------------------- tests
def test_save(tenant: str, lid: str, t: dict[str, Any]) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = _row(s, tenant, lid)
        tests = list(r.tests or [])
        one = _clean_tests([t])
        if not one:
            raise LangLabError("A test needs a program.")
        x = one[0]
        if not x["src"].strip() and x["kind"] != "error":
            raise LangLabError("A test needs a program.")
        i = next((k for k, y in enumerate(tests) if y["id"] == str(t.get("id") or "")), None)
        if i is None:
            if len(tests) >= MAX_TESTS:
                raise LangLabError(f"At most {MAX_TESTS} tests per language.")
            tests.append(x)
        else:
            tests[i] = x
        r.tests = tests
        r.updated_at = now()
        lid = r.id
    run_tests(tenant, lid)
    return get(tenant, lid)


def test_delete(tenant: str, lid: str, tid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = _row(s, tenant, lid)
        r.tests = [t for t in (r.tests or []) if t["id"] != tid]
        lid = r.id
    run_tests(tenant, lid)
    return get(tenant, lid)


def test_accept(tenant: str, lid: str, tid: str) -> dict[str, Any]:
    """Make what the program gives now its expected answer (her golden approval)."""
    _tables()
    with session() as s:
        r = _row(s, tenant, lid)
        res = {x["id"]: x for x in (r.last_run or {}).get("results") or []}
        tests = [dict(t) for t in (r.tests or [])]          # new dicts: an in-place change is not seen by the JSON column
        hit = False
        for t in tests:
            if t["id"] == tid and tid in res:
                x = res[tid]
                if t["kind"] == "tree":
                    if not x.get("tree"):
                        raise LangLabError("This program does not read, so there is no tree to keep.")
                    t["expect"] = x["tree"]
                elif t["kind"] == "error":
                    t["expect"] = ""
                else:
                    if x.get("outcome") != "ok":
                        raise LangLabError("This program did not run cleanly - fix it or make it an error test.")
                    t["expect"] = x.get("output", "")
                hit = True
        if not hit:
            raise LangLabError("Run the tests first, then keep what a program gives.")
        r.tests = tests
        lid = r.id
    return run_tests(tenant, lid)


def _harness() -> str:
    return r'''
import json, io, sys, time, signal, types, contextlib, traceback
_src = open("hoola_lang.py", encoding="utf-8").read()
H = types.ModuleType("hoola_lang")
exec(compile(_src, "hoola_lang.py", "exec"), H.__dict__)
sys.modules["hoola_lang"] = H
cfg = json.load(open("cases.json", encoding="utf-8"))
g = H.load(open("grammar.hg", encoding="utf-8").read(), cfg["start"])
ns = {"__name__": "interpreter", "Node": H.Node, "Tok": H.Tok, "LangError": H.LangError, "sexp": H.sexp}
load_error = ""
try:
    exec(compile(open("interpreter.py", encoding="utf-8").read(), "interpreter.py", "exec"), ns)
except Exception as e:
    tb = traceback.extract_tb(e.__traceback__)
    ln = getattr(e, "lineno", None) or next((f.lineno for f in reversed(tb) if f.filename == "interpreter.py"), 0)
    load_error = f"{type(e).__name__}: {e}"[:400] + (f" (line {ln})" if ln else "")
run = ns.get("run") if not load_error else None
if not load_error and not callable(run) and cfg["has_code"]:
    load_error = "The interpreter has no def run(tree)."
def _alarm(*a):
    raise TimeoutError()
signal.signal(signal.SIGALRM, _alarm)
sys.setrecursionlimit(4000)
res = []
for c in cfg["cases"]:
    r = {"id": c["id"]}
    try:
        tree = g.parse(c["src"])
    except H.ParseError as e:
        r.update(parsed=False, error=e.as_dict()); res.append(r); continue
    r["parsed"] = True
    r["tree"] = H.sexp(tree)
    if callable(run):
        buf = io.StringIO(); t0 = time.perf_counter()
        signal.setitimer(signal.ITIMER_REAL, cfg["limit"])
        try:
            with contextlib.redirect_stdout(buf):
                run(tree)
            r["outcome"] = "ok"
        except H.LangError as e:
            r["outcome"] = "error"; r["message"] = str(e)[:600]; r["line"] = e.line
        except TimeoutError:
            r["outcome"] = "timeout"; r["message"] = "It ran longer than %s s (an endless loop?)" % cfg["limit"]
        except RecursionError:
            r["outcome"] = "crash"; r["message"] = "RecursionError: the interpreter went too deep"
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            ln = next((f.lineno for f in reversed(tb) if f.filename == "interpreter.py"), 0)
            r["outcome"] = "crash"; r["message"] = f"{type(e).__name__}: {e}"[:600]; r["at"] = ln
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        r["output"] = buf.getvalue()[:20000]; r["ms"] = round((time.perf_counter() - t0) * 1000, 1)
    res.append(r)
print("@@HOOLA@@" + json.dumps({"load_error": load_error, "results": res}))
'''


def _sandbox(lang: dict[str, Any], cases: list[dict[str, Any]], limit_s: int) -> dict[str, Any]:
    from ..pylab import runner
    cfg = {"start": lang.get("start") or "", "limit": float(limit_s), "has_code": bool((lang.get("interpreter") or "").strip()),
           "cases": [{"id": c["id"], "src": c["src"]} for c in cases]}
    files = {"hoola_lang.py": RUNTIME.read_bytes(), "grammar.hg": lang["grammar"].encode(),
             "interpreter.py": (lang.get("interpreter") or "").encode(), "cases.json": json.dumps(cfg).encode()}
    total = min(300, 10 + int(limit_s * max(1, len(cases)) * 1.2))
    try:
        r = runner.run(_harness(), files, timeout_s=total, mem_mb=768)
    except runner.PylabError as e:
        raise LangLabError(str(e))
    out = r.get("stdout") or ""
    i = out.rfind("@@HOOLA@@")
    if i < 0:
        why = r.get("error") or (r.get("stderr") or "")[-400:] or "no answer"
        raise LangLabError(f"The sandbox did not finish: {why}")
    return json.loads(out[i + 9:].strip().splitlines()[0])


def _lines(s: str) -> str:
    return "\n".join(ln.rstrip() for ln in str(s or "").strip().splitlines())


def _judge(t: dict[str, Any], x: dict[str, Any], target: str) -> tuple[str, str]:
    """-> (status, why): pass | fail | new (no expected answer yet)"""
    kind, exp = t["kind"], t.get("expect") or ""
    if kind == "error":
        if not x.get("parsed"):
            msg = x.get("error", {}).get("message", "")
        elif x.get("outcome") == "error":
            msg = x.get("message", "")
        else:
            got = "it read and ran without an error" if x.get("outcome") == "ok" else x.get("message") or x.get("outcome", "")
            return "fail", f"This program should be refused, but {got}."
        if exp and exp.lower() not in msg.lower():
            return "fail", f'The error should mention "{exp}" but said: {msg[:200]}'
        return "pass", msg[:240]
    if not x.get("parsed"):
        return "fail", "It does not read: " + x.get("error", {}).get("message", "")
    if kind == "tree":
        if not exp.strip():
            return "new", "No expected tree yet - keep this one if it is right."
        return ("pass", "") if HL.norm_sexp(exp) == HL.norm_sexp(x.get("tree", "")) else ("fail", "The tree is different.")
    if "outcome" not in x:
        return "fail", "There is no interpreter yet, so nothing runs."
    if x["outcome"] != "ok":
        return "fail", {"error": "It gave an error: ", "crash": "The interpreter crashed: ", "timeout": ""}.get(x["outcome"], "") + \
            (x.get("message") or "")
    if not exp.strip() and not x.get("output", "").strip():
        return "new", "It printed nothing - is that right?"
    if not exp.strip():
        return "new", "No expected output yet - keep this one if it is right."
    return ("pass", "") if _lines(exp) == _lines(x.get("output", "")) else ("fail", "The output is different.")


def _evaluate(tenant: str, lang: dict[str, Any], tests: list[dict[str, Any]]) -> dict[str, Any]:
    st = settings(tenant)
    chk = check_grammar(lang["grammar"], lang.get("start") or "")
    if not chk["ok"]:
        return {"at": now().isoformat(), "grammar_ok": False, "grammar_errors": chk["errors"][:6], "results": [],
                "passed": 0, "failed": len(tests), "new": 0, "load_error": ""}
    cases = [t for t in tests]
    if (lang.get("interpreter") or "").strip():
        raw = _sandbox(lang, cases, st["limit_s"]) if cases else {"load_error": "", "results": []}
    else:
        g = HL.load(lang["grammar"], lang.get("start") or "")
        rr = []
        for c in cases:
            try:
                rr.append({"id": c["id"], "parsed": True, "tree": HL.sexp(g.parse(c["src"]))})
            except HL.ParseError as e:
                rr.append({"id": c["id"], "parsed": False, "error": e.as_dict()})
        raw = {"load_error": "", "results": rr}
    by = {x["id"]: x for x in raw.get("results") or []}
    results, p, f, n = [], 0, 0, 0
    for t in tests:
        x = by.get(t["id"], {"id": t["id"], "parsed": False, "error": {"message": "not run"}})
        if raw.get("load_error") and x.get("parsed"):
            stt, why = "fail", "The interpreter does not load: " + raw["load_error"]
        else:
            stt, why = _judge(t, x, st["target"])
        results.append({**x, "status": stt, "why": why})
        p += stt == "pass"
        f += stt == "fail"
        n += stt == "new"
    return {"at": now().isoformat(), "grammar_ok": True, "grammar_errors": [], "warnings": chk["warnings"][:8],
            "load_error": raw.get("load_error") or "", "results": results, "passed": p, "failed": f, "new": n}


def run_tests(tenant: str, lid: str) -> dict[str, Any]:
    lang = get(tenant, lid)
    STATS["runs"] += 1
    rep = _evaluate(tenant, lang, lang["tests"])
    with session() as s:
        r = _row(s, tenant, lid)
        r.last_run = rep
        v = list(r.versions or [])
        if v:
            v[-1] = {**v[-1], "passed": rep["passed"], "failed": rep["failed"]}
            r.versions = v
    return get(tenant, lid)


def run_program(tenant: str, lid: str, src: str) -> dict[str, Any]:
    """The playground: read + run one program (the run in the sandbox)."""
    lang = get(tenant, lid)
    p = parse(tenant, lid, src)
    if not p["ok"] or not (lang.get("interpreter") or "").strip():
        return {**p, "ran": False}
    raw = _sandbox(lang, [{"id": "play", "src": str(src or "")}], settings(tenant)["limit_s"])
    x = (raw.get("results") or [{}])[0]
    return {**p, "ran": True, "load_error": raw.get("load_error") or "", "outcome": x.get("outcome", ""), "output": x.get("output", ""),
            "message": x.get("message", ""), "line": x.get("line") or x.get("at") or 0, "run_ms": x.get("ms", 0)}


# ---------------------------------------------------------------- fuzzing + speed
def _mutate(src: str, rnd: random.Random, g: HL.Grammar) -> str:
    if not src:
        return rnd.choice(g.literals or ["x"])
    i = rnd.randrange(len(src))
    op = rnd.randrange(4)
    if op == 0:
        return src[:i] + src[i + 1:]
    if op == 1:
        return src[:i] + src[i] + src[i:]
    if op == 2:
        return src[:i] + " " + rnd.choice(g.literals or ["@"]) + " " + src[i:]
    j = rnd.randrange(len(src))
    a, b = sorted((i, j))
    return src[:a] + src[b:b + 1] + src[a + 1:b] + src[a:a + 1] + src[b + 1:] if b > a else src[::-1]


def fuzz(tenant: str, lid: str) -> dict[str, Any]:
    """1) programs made from the grammar must read; 2) broken programs must give a clean error, never crash the interpreter;
    3) how fast it reads."""
    lang = get(tenant, lid)
    g = _grammar(lang)
    st = settings(tenant)
    rnd = random.Random(7)
    made, bad, chars, secs = 0, [], 0, 0.0
    for _ in range(st["fuzz_n"]):
        src = g.sample(rnd, depth=rnd.randint(3, 8))
        made += 1
        t0 = time.perf_counter()
        try:
            g.parse(src)
        except HL.ParseError as e:
            if len(bad) < 6:
                bad.append({"src": src[:400], "error": str(e)[:300]})
            continue
        secs += time.perf_counter() - t0
        chars += len(src)
    seeds = [t["src"] for t in lang["tests"] if t["src"].strip()] or [g.sample(rnd) for _ in range(5)]
    broken, parse_crash = [], []
    for k in range(min(60, st["fuzz_n"] + 20)):
        m = _mutate(rnd.choice(seeds), rnd, g)
        try:
            g.parse(m)
            broken.append(m)
        except HL.ParseError:
            pass
        except Exception as e:   # noqa: BLE001  (a fault in the parser itself)
            parse_crash.append({"src": m[:200], "error": f"{type(e).__name__}: {e}"[:200]})
    crashes: list[dict[str, Any]] = []
    ran = 0
    if (lang.get("interpreter") or "").strip() and broken:
        cases = [{"id": f"f{i}", "src": s} for i, s in enumerate(broken[:30])]
        try:
            raw = _sandbox(lang, cases, min(st["limit_s"], 2))
            by = {c["id"]: c["src"] for c in cases}
            for x in raw.get("results") or []:
                ran += 1
                if x.get("outcome") in ("crash", "timeout"):
                    crashes.append({"src": by.get(x["id"], "")[:300], "outcome": x["outcome"], "error": x.get("message", "")[:300]})
        except LangLabError as e:
            crashes.append({"src": "", "outcome": "sandbox", "error": str(e)[:300]})
    kbps = round(chars / 1024 / secs, 1) if secs > 0 else 0
    rep = {"at": now().isoformat(), "made": made, "unreadable": len(bad), "unreadable_examples": bad, "broken_ran": ran,
           "crashes": len(crashes), "crash_examples": crashes[:6], "parser_faults": parse_crash[:4], "kb_per_s": kbps,
           "ok": not bad and not crashes and not parse_crash}
    with session() as s:
        r = _row(s, tenant, lid)
        r.fuzz = rep
    return rep


# ---------------------------------------------------------------- the model's work (in the background on the desk)
def _gate(tenant: str, actor: str) -> None:
    if not str(actor or "owner").startswith(("owner", "approved", "goal")):
        from .. import usage
        if not usage.allowed(tenant, "routine"):
            raise LangLabError(usage.blocked_text(tenant))


def _try_design(words: str, examples: str, target: str) -> dict[str, Any]:
    d, fix = None, ""
    for _ in range(3):
        d = ai.design(words, examples, target, fix=fix, prev=d)
        chk = check_grammar(str(d.get("grammar") or ""), str(d.get("start") or ""))
        problems = [x["say"] for x in chk["errors"]]
        interp = str(d.get("interpreter") or "")
        if interp:
            try:
                compile(interp, "interpreter.py", "exec")
            except SyntaxError as e:
                problems.append(f"The interpreter does not compile: {e.msg} (line {e.lineno})")
        if not problems:
            d["start"] = chk["start"]
            return d
        fix = "\n".join(problems[:8])
    raise LangLabError("The model could not write a grammar that passes the checks: " + fix[:300])


def design(tenant: str, words: str, examples: str = "", actor: str = "owner", wait: bool = False) -> dict[str, Any]:
    words = str(words or "").strip()
    if len(words) < 8:
        raise LangLabError("Say what the language is for (a few words at least).")
    _gate(tenant, actor)
    st = settings(tenant)
    target = ("print the code it compiles to" if st["target"] == "compiler" else "run the program and print its results")
    if wait:
        from .. import usage
        with usage.scope(tenant, "langlab"):
            d = _try_design(words, str(examples or ""), target)
        STATS["designs"] += 1
        return create(tenant, str(d.get("name") or "My language"), str(d.get("purpose") or words[:300]), str(d.get("grammar") or ""),
                      str(d.get("interpreter") or ""), str(d.get("start") or ""), d.get("tests"), str(d.get("ext") or ""),
                      note="Designed by Hoola")
    _tables()
    with session() as s:
        r = Lang(tenant_id=tenant, number=_number(s, tenant), name="New language", purpose=words[:600], status="designing",
                 job="Designing the grammar, the interpreter and the tests", tests=[], versions=[])
        s.add(r)
        s.flush()
        lid = r.id

    def go():
        try:
            from .. import usage
            with usage.scope(tenant, "langlab"):
                d = _try_design(words, str(examples or ""), target)
            STATS["designs"] += 1
            with session() as s2:
                r2 = s2.get(Lang, lid)
                if r2 is None:
                    return
                r2.name = str(d.get("name") or "My language")[:80]
                r2.purpose = str(d.get("purpose") or words)[:600]
                r2.ext, r2.start = _ext(str(d.get("ext") or r2.name)), str(d.get("start") or "")[:60]
                r2.grammar, r2.interpreter = str(d.get("grammar") or ""), str(d.get("interpreter") or "")[:MAX_INTERP]
                r2.tests = _clean_tests(d.get("tests"))
                r2.job = "Running the tests"
                _snap(r2, "Designed by Hoola")
            run_tests(tenant, lid)
            with session() as s2:
                r2 = s2.get(Lang, lid)
                if r2 is not None:
                    r2.status, r2.job = "ready", ""
        except Exception as e:   # noqa: BLE001
            log.info("langlab design failed: %s", e)
            with session() as s2:
                r2 = s2.get(Lang, lid)
                if r2 is not None:
                    r2.status, r2.job = "failed", str(e)[:400]
    _POOL.submit(go)
    return get(tenant, lid)


def _apply_or_hold(tenant: str, lid: str, d: dict[str, Any], summary: str, before_failed: int, force: bool) -> dict[str, Any]:
    """Run the tests on the proposed grammar + interpreter; keep it only when it does not make more tests fail."""
    lang = get(tenant, lid)
    have = {(t["src"].strip(), t["kind"]) for t in lang["tests"]}
    extra = [t for t in _clean_tests(d.get("tests")) if t["src"].strip() and (t["src"].strip(), t["kind"]) not in have]
    new_tests = lang["tests"] + extra[: max(0, MAX_TESTS - len(lang["tests"]))]
    cand = {**lang, "grammar": str(d.get("grammar") or lang["grammar"]), "interpreter": str(d.get("interpreter") or lang["interpreter"]),
            "start": str(d.get("start") or lang["start"])}
    rep = _evaluate(tenant, cand, new_tests)
    keep = force or (rep["grammar_ok"] and rep["failed"] <= before_failed)
    with session() as s:
        r = _row(s, tenant, lid)
        if keep:
            r.grammar, r.interpreter, r.start, r.tests = cand["grammar"], cand["interpreter"], cand["start"], new_tests
            r.last_run, r.proposal = rep, {}
            _snap(r, summary or "Improved by Hoola")
        else:
            r.proposal = {"grammar": cand["grammar"], "interpreter": cand["interpreter"], "start": cand["start"], "tests": new_tests,
                          "summary": summary, "passed": rep["passed"], "failed": rep["failed"], "before_failed": before_failed,
                          "grammar_ok": rep["grammar_ok"], "at": now().isoformat()}
        r.status, r.job = "ready", ""
        r.updated_at = now()
    STATS["kept" if keep else "held"] += 1
    return {**get(tenant, lid), "kept": keep}


def improve(tenant: str, lid: str, words: str = "", actor: str = "owner", wait: bool = False) -> dict[str, Any]:
    _gate(tenant, actor)
    lang = get(tenant, lid)
    if lang["status"] in ("designing", "improving"):
        raise LangLabError("Hoola is already working on this language.")
    if not lang["grammar"].strip():
        raise LangLabError("This language has no grammar yet.")
    failing = [{"name": t["name"], "src": t["src"][:600], "kind": t["kind"], "expect": t["expect"][:600], "why": x.get("why", ""),
                "got": (x.get("output") or x.get("message") or "")[:600]}
               for t in lang["tests"] for x in (lang["last_run"].get("results") or []) if x["id"] == t["id"] and x.get("status") == "fail"]
    if not failing and not str(words or "").strip():
        raise LangLabError("Every test passes - say what to change.")
    before = int(lang["last_run"].get("failed") or 0)

    def work() -> dict[str, Any]:
        from .. import usage
        fix, d = "", {}
        with usage.scope(tenant, "langlab"):
            for _ in range(2):
                d = ai.improve(lang, str(words or ""), failing, fix=fix)
                chk = check_grammar(str(d.get("grammar") or lang["grammar"]), str(d.get("start") or lang["start"]))
                probs = [x["say"] for x in chk["errors"]]
                try:
                    compile(str(d.get("interpreter") or lang["interpreter"] or "pass"), "interpreter.py", "exec")
                except SyntaxError as e:
                    probs.append(f"The interpreter does not compile: {e.msg} (line {e.lineno})")
                if not probs:
                    break
                fix = "\n".join(probs)
        STATS["improves"] += 1
        return _apply_or_hold(tenant, lid, d, str(d.get("summary") or str(words)[:160]), before, False)

    if wait:
        return work()
    with session() as s:
        r = _row(s, tenant, lid)
        r.status, r.job = "improving", f"Changing it: {str(words or 'make the failing tests pass')[:160]}"

    def go():
        try:
            work()
        except Exception as e:   # noqa: BLE001
            log.info("langlab improve failed: %s", e)
            with session() as s2:
                r2 = s2.get(Lang, lid)
                if r2 is not None:
                    r2.status, r2.job = "ready", ""
                    r2.proposal = {"error": str(e)[:400], "at": now().isoformat()}
    _POOL.submit(go)
    return get(tenant, lid)


def proposal(tenant: str, lid: str, use: bool) -> dict[str, Any]:
    lang = get(tenant, lid)
    p = lang["proposal"]
    if not p:
        raise LangLabError("There is no waiting change.")
    if not use or p.get("error"):
        with session() as s:
            _row(s, tenant, lid).proposal = {}
        return get(tenant, lid)
    return _apply_or_hold(tenant, lid, p, p.get("summary") or "Hoola's change (kept by you)", 0, True)


def add_tests(tenant: str, lid: str, words: str = "", actor: str = "owner") -> dict[str, Any]:
    _gate(tenant, actor)
    lang = get(tenant, lid)
    from .. import usage
    with usage.scope(tenant, "langlab"):
        d = ai.more_tests(lang, str(words or ""))
    have = {(t["src"].strip(), t["kind"]) for t in lang["tests"]}
    new = [dict(t, expect="") if t["kind"] != "error" else t for t in _clean_tests(d.get("tests"))
           if (t["src"].strip() or t["kind"] == "error") and (t["src"].strip(), t["kind"]) not in have]
    room = MAX_TESTS - len(lang["tests"])
    with session() as s:
        r = _row(s, tenant, lid)
        r.tests = list(r.tests or []) + new[:max(0, room)]
    out = run_tests(tenant, lid)
    return {**out, "added": len(new[:max(0, room)])}


# ---------------------------------------------------------------- the spec, editor support, the zip
def spec_md(lang: dict[str, Any]) -> str:
    chk = check_grammar(lang["grammar"], lang["start"])
    res = {x["id"]: x for x in (lang["last_run"].get("results") or [])}
    out = [f"# {lang['name']}", "", lang["purpose"] or "", "",
           f"Files end with `.{lang['ext']}`. Start rule: `{chk.get('start') or lang['start']}`. "
           f"Tests: {lang['passed']} of {lang['total']} pass.", "", "## Words of the language", ""]
    out.append(", ".join(f"`{k}`" for k in chk.get("keywords", [])) or "(none)")
    out += ["", "## Tokens", "", "| Token | Pattern | Example |", "|---|---|---|"]
    for t in chk.get("tokens", []):
        pat = ("/" + t["pattern"] + "/") if t["regex"] else f'"{t["pattern"]}"'
        out.append(f"| {t['name']} | `{pat.replace('|', '\\|')}` | `{t['example'].replace('|', '\\|')}` |")
    if chk.get("ignore"):
        out += ["", "Skipped between tokens: " + ", ".join(f"`/{x}/`" for x in chk["ignore"])]
    out += ["", "## Grammar", ""]
    for r in chk.get("rules", []):
        out += [f"### {r['name']}", "", f"![{r['name']}](railroad/{r['name']}.svg)", "", "```", f"{r['name']} : {r['ebnf']} ;", "```", ""]
    ex = [t for t in lang["tests"] if res.get(t["id"], {}).get("status") == "pass"]
    if ex:
        out += ["## Examples", ""]
        for t in ex[:12]:
            out += [f"### {t['name']}", "", "```", t["src"], "```", ""]
            x = res[t["id"]]
            if t["kind"] == "output" and x.get("output"):
                out += ["Prints:", "", "```", x["output"].rstrip(), "```", ""]
            elif t["kind"] == "error":
                out += [f"Refused: {x.get('why', '')}", ""]
    return "\n".join(out) + "\n"


def textmate(lang: dict[str, Any]) -> dict[str, Any]:
    chk = check_grammar(lang["grammar"], lang["start"])
    kw = chk.get("keywords") or []
    ops = []
    try:
        g = HL.load(lang["grammar"], lang["start"])
        ops = [s for s in g.literals if not re.fullmatch(r"\w+", s)]
    except HL.GrammarError:
        pass
    pats: list[dict[str, Any]] = []
    for x in chk.get("ignore") or []:
        if x.startswith(("#", "//", "--", ";", "%")) or "\\/\\/" in x or x.startswith("\\/"):
            pats.append({"name": "comment.line", "match": x})
    for t in chk.get("tokens") or []:
        p = t["pattern"] if t["regex"] else re.escape(t["pattern"])
        if t["regex"] and p.startswith(('"', "'", '\\"')):
            pats.append({"name": "string.quoted", "match": p})
        elif t["regex"] and "\\d" in p and not re.search(r"[A-Za-z]-", p):
            pats.append({"name": "constant.numeric", "match": p})
    if kw:
        pats.append({"name": "keyword.control", "match": r"\b(?:" + "|".join(re.escape(k) for k in kw) + r")\b"})
    if ops:
        pats.append({"name": "keyword.operator", "match": "|".join(re.escape(o) for o in ops)})
    sid = "source." + lang["ext"]
    return {"name": lang["name"], "scopeName": sid, "fileTypes": [lang["ext"]], "patterns": pats}


def _readme(lang: dict[str, Any]) -> str:
    return (f"# {lang['name']}\n\n{lang['purpose']}\n\nMade with the Hoola Compiler Construction Engineer. Everything here is plain "
            f"Python 3.9+ with no other packages.\n\n- `python cli.py program.{lang['ext']}` reads and runs a program "
            f"(`--tree` prints its tree).\n- `python run_tests.py` runs the golden tests ({lang['total']} of them).\n"
            f"- `SPEC.md` is the language reference with railroad diagrams.\n- `editor/` is a VS Code extension for colours: copy the "
            f"folder into ~/.vscode/extensions/.\n- `grammar.hg` is the grammar, `interpreter.py` what running a program does, "
            f"`hoola_lang.py` the parser.\n")


CLI = r'''"""Read and run a program: python cli.py FILE [--tree]"""
import os, sys, types
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hoola_lang as H

def load():
    g = H.load(open(os.path.join(HERE, "grammar.hg"), encoding="utf-8").read(), START)
    ns = {"__name__": "interpreter", "Node": H.Node, "Tok": H.Tok, "LangError": H.LangError, "sexp": H.sexp}
    exec(compile(open(os.path.join(HERE, "interpreter.py"), encoding="utf-8").read(), "interpreter.py", "exec"), ns)
    return g, ns.get("run")

START = %r

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python cli.py FILE [--tree]")
    g, run = load()
    src = open(sys.argv[1], encoding="utf-8").read()
    try:
        tree = g.parse(src)
    except H.ParseError as e:
        sys.exit(f"{e}\n{e.pointer}")
    if "--tree" in sys.argv or not run:
        print(H.sexp(tree))
    else:
        try:
            run(tree)
        except H.LangError as e:
            sys.exit(f"Error (line {e.line}): {e}")
'''

RUN_TESTS = r'''"""Run the golden tests: python run_tests.py"""
import contextlib, io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hoola_lang as H
from cli import load

g, run = load()
ok = bad = 0
for t in json.load(open(os.path.join(HERE, "tests.json"), encoding="utf-8")):
    got, err = "", ""
    try:
        tree = g.parse(t["src"])
        if t["kind"] == "tree":
            got = H.sexp(tree)
        elif run:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                run(tree)
            got = buf.getvalue()
    except (H.ParseError, H.LangError) as e:
        err = str(e)
    if t["kind"] == "error":
        good = bool(err) and t["expect"].lower() in err.lower()
    elif t["kind"] == "tree":
        good = not err and H.norm_sexp(got) == H.norm_sexp(t["expect"])
    else:
        good = not err and got.strip() == t["expect"].strip()
    ok += good
    bad += not good
    print(("PASS " if good else "FAIL ") + t["name"])
print(f"{ok} passed, {bad} failed")
sys.exit(1 if bad else 0)
'''


def export_zip(tenant: str, lid: str) -> tuple[str, bytes]:
    lang = get(tenant, lid)
    _grammar(lang)
    buf = io.BytesIO()
    base = re.sub(r"[^a-z0-9]+", "-", lang["name"].lower()).strip("-") or "language"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        def put(name: str, data: str | bytes) -> None:
            info = zipfile.ZipInfo(f"{base}/{name}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data if isinstance(data, bytes) else data.encode("utf-8"))
        put("hoola_lang.py", RUNTIME.read_bytes())
        put("grammar.hg", lang["grammar"])
        put("interpreter.py", lang["interpreter"] or "def run(tree):\n    print(sexp(tree))\n")
        put("cli.py", CLI % (lang["start"] or "",))
        put("run_tests.py", RUN_TESTS)
        put("tests.json", json.dumps([{k: t[k] for k in ("name", "src", "kind", "expect")} for t in lang["tests"]], indent=2,
                                     ensure_ascii=False))
        put("SPEC.md", spec_md(lang))
        put("README.md", _readme(lang))
        for rr in railroads(tenant, lid):
            put(f"railroad/{rr['rule']}.svg", railroad.svg(HL.load(lang["grammar"], lang["start"]).shape(
                HL.load(lang["grammar"], lang["start"]).rules[rr["rule"]].expr)))
        tm = textmate(lang)
        lid_ = lang["ext"]
        put(f"editor/syntaxes/{lid_}.tmLanguage.json", json.dumps(tm, indent=2))
        put("editor/language-configuration.json", json.dumps({"brackets": [["(", ")"], ["[", "]"], ["{", "}"]],
                                                              "autoClosingPairs": [["(", ")"], ["[", "]"], ["{", "}"], ['"', '"']]}, indent=2))
        put("editor/package.json", json.dumps({
            "name": f"{base}-language", "displayName": lang["name"], "version": f"0.0.{lang['version']}", "publisher": "hoola",
            "engines": {"vscode": "^1.80.0"}, "categories": ["Programming Languages"],
            "contributes": {"languages": [{"id": lid_, "aliases": [lang["name"]], "extensions": [f".{lid_}"],
                                           "configuration": "./language-configuration.json"}],
                            "grammars": [{"language": lid_, "scopeName": tm["scopeName"], "path": f"./syntaxes/{lid_}.tmLanguage.json"}]}},
            indent=2))
    return f"{base}.zip", buf.getvalue()


def health() -> dict[str, Any]:
    try:
        from ..pylab import runner
        iso = runner.net_isolation()
    except Exception:   # noqa: BLE001
        iso = False
    return {"sandbox": True, "net_isolated": iso, "stats": dict(STATS), "runtime": HL.VERSION}


STARTERS = [
    ("Calculator", "A small calculator with variables: let x = 2 + 3 * 4; print x;",
     r'''%ignore /\s+/
%ignore /#[^\n]*/
program   : statement* ;
statement : "let" NAME "=" expr ";" | "print" expr ";" ;
?expr     : term (("+" | "-") term)* ;
?term     : factor (("*" | "/") factor)* ;
?factor   : NUMBER | NAME | "(" expr ")" | "-" factor ;
NAME      : /[^\W\d]\w*/ ;
NUMBER    : /\d+(\.\d+)?/ ;
''',
     r'''def run(tree):
    env = {}
    def ev(n):
        if isinstance(n, Tok):
            if n.kind == "NUMBER":
                return float(n.text) if "." in n.text else int(n.text)
            if n.text not in env:
                raise LangError(f"'{n.text}' has no value yet", n)
            return env[n.text]
        if n.rule == "factor":
            return -ev(n.children[0])
        v = ev(n.children[0])
        for op, rhs in zip(n.children[1::2], n.children[2::2]):
            r = ev(rhs)
            if op.text == "/" and r == 0:
                raise LangError("division by zero", op)
            v = {"+": v + r, "-": v - r, "*": v * r, "/": v / r}[op.text]
        return v
    for st in tree.children:
        if len(st.children) == 2:
            env[st.children[0].text] = ev(st.children[1])
        else:
            print(ev(st.children[0]))
''',
     [{"name": "Precedence", "src": "print 2 + 3 * 4;", "kind": "output", "expect": "14"},
      {"name": "Variables", "src": "let x = 10; let y = x / 4; print y;", "kind": "output", "expect": "2.5"},
      {"name": "Brackets", "src": "print (2 + 3) * 4;", "kind": "output", "expect": "20"},
      {"name": "Names in any script", "src": "let விலை = 120; print விலை * 2;", "kind": "output", "expect": "240"},
      {"name": "Unknown name", "src": "print z;", "kind": "error", "expect": "no value"},
      {"name": "Divide by zero", "src": "print 1 / 0;", "kind": "error", "expect": "zero"},
      {"name": "Missing ;", "src": "print 1", "kind": "error", "expect": ""}]),
    ("Pricing rules", "Business pricing rules: when total > 1000 then discount 10%;", "", "", []),
    ("Chatbot flow", "A chatbot flow language: states, what the user says, replies and the next state.", "", "", []),
    ("Query language", "A small query language for a product list: find products where price < 500 and stock > 0 sort by price",
     "", "", []),
    ("Config files", "A config file format with sections, keys, numbers, strings, lists and comments - checked for typos.", "", "", []),
    ("Robot moves", "Commands for a small robot or turtle: forward 10, turn left 90, repeat 4 [ ... ] - drawing a path.", "", "", []),
]
