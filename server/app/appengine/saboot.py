"""v0.832 SABOOT (L11 of docs/LOVABLE_STUDIO_PLAN.md, owner: "L11 SABOOT") - nothing is called done that a check did not prove.

Four checks over an App Engine app, all run on THIS server (no model call, Rs 0):

1. RULE TESTS - when an app's Hoola Cloud rules change (or a list is added), the rules are PLAYED against the real
   rule engine (the website-app core, the same code every visitor's call goes through) on a scratch dataset: a visitor,
   two members and an admin try to read / add / change / delete in every list, and each answer must be what the rule
   says (a "own" list must hide one member's entries from another; an "admin" list must refuse a member; ...).
   Plain test on the real engine, not a copy of the rule in the test.
2. BROWSER CHECK - real Chromium opens the app (shell + sealed frame) at PHONE and DESKTOP size: it must show
   something, raise no error, and the Hoola Cloud journey the app itself would make (sign up, add, list, change,
   remove, sign out) must work through the sealed frame. Served in-process (no port), so it also runs on her VPS.
3. QUICK SCAN - on every going-live: Cloud rule audit (a list that lets anyone on the internet read personal fields
   without her recorded yes = FAIL), exposed secrets in the code and the built files, the code rules again, the rule
   tests above. Published only when no FAIL.
4. DEEP SCAN - on demand, before a big launch: everything in the quick scan plus code patterns (unsafe links, plain
   http, lists the code asks for that do not exist, lists nobody can reach), leaks in the built files, and a forced
   fresh browser check. NOT a model review (no model call is connected for it; said on the page).

Said plainly, not hidden: the advisory feed for npm packages is NOT connected - the packages are the fixed vetted set
in Hoola's lock file; and files / functions / live / payments are not built so there is nothing to scan there."""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from . import cloud as CL
from . import rules as RL
from ..db import now, session
from ..site import webapp as W

ORIGIN = "http://hoola.check"
SECRETS = [
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "an API key (sk-...)"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "an AWS access key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "a GitHub token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{15,}\.eyJ[A-Za-z0-9_\-]{15,}\.[A-Za-z0-9_\-]{10,}"), "a signed token (JWT)"),
    (re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd|token)\b[\"']?\s*[:=]\s*[\"'][A-Za-z0-9/+_\-]{16,}[\"']"),
     "a secret written in the code"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "a Google API key"),
]
_RUN = threading.Lock()


# ------------------------------------------------------------------ small helpers
def _file(r) -> Path:
    from . import service as S
    return S.pdir(r.tenant_id, r.id) / "saboot.json"


def load(r) -> dict[str, Any]:
    try:
        return json.loads(_file(r).read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _store(r, key: str, val: dict[str, Any]) -> None:
    d = load(r)
    d[key] = val
    _file(r).parent.mkdir(parents=True, exist_ok=True)
    _file(r).write_text(json.dumps(d, ensure_ascii=False))


def rules_print(r) -> str:
    """What a rule test proved: the lists' rules + field types. A change in any of them makes the proof stale."""
    sch = CL.schema(r)
    out = []
    for x in sch.get("lists") or []:
        out.append([x["key"], bool(x.get("hidden")), x["rules"], [(f["key"], f["type"], bool(f.get("hidden"))) for f in x["fields"]]])
    return json.dumps([out, bool(sch.get("signup", True))], sort_keys=True)


def _item(level: str, where: str, say: str) -> dict[str, str]:
    return {"level": level, "where": where, "say": say}


# ------------------------------------------------------------------ 1. rule tests (the real rule engine, a scratch dataset)
def _ip() -> str:
    """A fresh made-up address per call so the check never trips the sign-up rate limit (5 an hour per address)."""
    h = uuid.uuid4().bytes
    return f"10.{h[0]}.{h[1]}.{h[2]}"


def _scratch(r) -> str:
    return f"ae:{r.id}:t"


def _wipe(sk: str) -> None:
    from sqlalchemy import delete as sqldel
    with session() as s:
        s.execute(sqldel(W.SiteAppRow).where(W.SiteAppRow.site_id == sk))
        s.execute(sqldel(W.SiteAppMember).where(W.SiteAppMember.site_id == sk))


def _try(fn, *a) -> tuple[str, Any]:
    try:
        return "ok", fn(*a)
    except W.AppError as e:
        return ("denied" if e.code in (401, 403) else f"error {e.code}"), None


def rule_tests(r) -> dict[str, Any]:
    """Play every list's rules against the real engine. Returns {ok, checks, failed, ...} and keeps it for the Studio."""
    sch = CL.schema(r)
    core = CL.core_schema(sch)
    sk = _scratch(r)
    checks: list[dict[str, Any]] = []

    def chk(lst: str, name: str, want: str, got: str, note: str = "") -> None:
        checks.append({"list": lst, "check": name, "want": want, "got": got, "ok": want == got, "note": note})

    with _RUN:
        _wipe(sk)
        try:
            W.ensure_tables()
            who = {"anon": W.Who()}
            ids: dict[str, str] = {}
            for n, nm in (("a", "a"), ("b", "b"), ("c", "c")):
                W.signup(sk, {"signup": True}, f"saboot-{nm}@example.com", "Check-pass-12345", nm, _ip())
                with session() as s:
                    from sqlalchemy import select
                    m = s.scalars(select(W.SiteAppMember).where(W.SiteAppMember.site_id == sk, W.SiteAppMember.email == f"saboot-{nm}@example.com")).first()
                    ids[n] = m.id
            W.set_role(sk, ids["c"], "admin")
            with session() as s:
                for n in ("a", "b", "c"):
                    who[n] = W.Who(member=s.get(W.SiteAppMember, ids[n]))
                    s.expunge(who[n].m)
            for c in core["collections"]:
                k, rl = c["key"], c["rules"]
                data = {f["key"]: CL._sample_value(f, 1) for f in c["fields"]}

                def seed_row(owner: str) -> str:
                    with session() as s:
                        row = W.SiteAppRow(site_id=sk, coll=k, owner=owner, data=json.dumps(data, ensure_ascii=False))
                        s.add(row)
                        s.flush()
                        return row.id

                # add
                want_create = {"public": {"anon": "ok", "a": "ok", "c": "ok"}, "member": {"anon": "denied", "a": "ok", "c": "ok"},
                               "admin": {"anon": "denied", "a": "denied", "c": "ok"}}[rl["create"]]
                for who_k, want in want_create.items():
                    got, _ = _try(W.create, sk, core, k, data, who[who_k], _ip(), 50000)
                    chk(k, f"add as {'a visitor' if who_k == 'anon' else 'a member' if who_k == 'a' else 'the admin'}", want, got)
                # read: a's entry
                _wipe_rows(sk, k)
                seed_row(ids["a"])
                want_read = {
                    "public": {"anon": 1, "a": 1, "b": 1, "c": 1},
                    "members": {"anon": "denied", "a": 1, "b": 1, "c": 1},
                    "own": {"anon": "denied", "a": 1, "b": 0, "c": 1},
                    "admin": {"anon": "denied", "a": "denied", "b": "denied", "c": 1},
                }[rl["read"]]
                for who_k, want in want_read.items():
                    st, rows = _try(W.rows, sk, core, k, who[who_k], 50)
                    got = len(rows) if st == "ok" else st
                    label = {"anon": "a visitor", "a": "its owner", "b": "another member", "c": "the admin"}[who_k]
                    chk(k, f"read as {label}", str(want), str(got))
                # change / remove
                for opname, fn in (("change", lambda rid, w: W.update(sk, core, k, rid, data, w)),
                                   ("remove", lambda rid, w: W.delete(sk, core, k, rid, w))):
                    rule = rl["update" if opname == "change" else "delete"]
                    want_w = {"own": {"anon": "denied", "a": "ok", "b": "denied", "c": "ok"},
                              "admin": {"anon": "denied", "a": "denied", "b": "denied", "c": "ok"}}[rule]
                    for who_k, want in want_w.items():
                        rid = seed_row(ids["a"])
                        got, _ = _try(fn, rid, who[who_k])
                        label = {"anon": "a visitor", "a": "its owner", "b": "another member", "c": "the admin"}[who_k]
                        chk(k, f"{opname} as {label}", want, got)
        finally:
            _wipe(sk)
    failed = [c for c in checks if not c["ok"]]
    out = {"ran": True, "ok": not failed, "count": len(checks), "failed": failed[:12], "checks": checks[:200],
           "at": now().isoformat(), "rules": rules_print(r), "schema_version": sch.get("version", 0),
           "lists": len(core["collections"])}
    _store(r, "rule_tests", out)
    return out


def _wipe_rows(sk: str, coll: str) -> None:
    from sqlalchemy import delete as sqldel
    with session() as s:
        s.execute(sqldel(W.SiteAppRow).where(W.SiteAppRow.site_id == sk, W.SiteAppRow.coll == coll))


def rule_tests_current(r) -> dict[str, Any] | None:
    d = load(r).get("rule_tests")
    return d if d and d.get("rules") == rules_print(r) else None


def say_rule_tests(t: dict[str, Any]) -> str:
    if not t.get("lists"):
        return "No saved data yet, so there are no rules to test."
    if t["ok"]:
        return f"Rule tests passed: {t['count']} checks over {t['lists']} list(s) behaved exactly as the rules say."
    f = t["failed"][0]
    return (f"Rule tests FAILED ({len(t['failed'])} of {t['count']}): in '{f['list']}', {f['check']} should have been "
            f"'{f['want']}' but was '{f['got']}'.")


# ------------------------------------------------------------------ 2. the browser check
def _chromium_kw() -> dict[str, Any]:
    exe = os.environ.get("HOOLA_CHROMIUM") or ""
    return {"executable_path": exe} if exe else {}


def _frame_call(fr, op: str, args: dict[str, Any]) -> dict[str, Any]:
    js = """([op, args]) => new Promise(res => {
        const id = 900000 + Math.floor(Math.random() * 90000);
        const h = e => { const d = e.data; if (d && d.hoola === 'cloud-r' && d.id === id) { removeEventListener('message', h); res(d); } };
        addEventListener('message', h);
        parent.postMessage({hoola: 'cloud', id, op, args}, '*');
        setTimeout(() => res({ok: false, error: 'no answer'}), 8000);
    })"""
    return fr.evaluate(js, [op, args])


def _journey(r, fr, notes: list[str]) -> dict[str, Any]:
    """What the app itself does through its sealed frame: sign up, add, list, change, remove, sign out."""
    sch = CL.schema(r)
    core = CL.core_schema(sch)
    pick = next((c for c in core["collections"] if c["rules"]["create"] in ("public", "member")), None)
    out: dict[str, Any] = {"steps": []}

    def step(name: str, ok: bool, say: str = "") -> bool:
        out["steps"].append({"step": name, "ok": ok, "say": say})
        return ok

    sc = _frame_call(fr, "schema", {})
    if not step("reach Hoola Cloud from the app", bool(sc.get("ok")), "" if sc.get("ok") else str(sc.get("error"))):
        return out
    if pick is None:
        notes.append("No list a visitor or member can add to, so the add / change / remove walk was skipped.")
        return out
    email = f"hoola-check-{uuid.uuid4().hex[:8]}@example.com"
    if pick["rules"]["create"] == "member" or pick["rules"]["read"] in ("members", "own"):
        su = _frame_call(fr, "signup", {"email": email, "password": "Check-pass-12345", "name": "Hoola check"})
        if not step("sign up", bool(su.get("ok")), str(su.get("error") or "")):
            return out
        me = _frame_call(fr, "me", {})
        step("stay signed in", bool(me.get("ok") and (me.get("data") or {}).get("me")), str(me.get("error") or ""))
    data = {f["key"]: CL._sample_value(f, 2) for f in pick["fields"]}
    cr = _frame_call(fr, "create", {"list": pick["key"], "data": data})
    if not step(f"add an entry to '{pick['key']}'", bool(cr.get("ok")), str(cr.get("error") or "")):
        return out
    rid = ((cr.get("data") or {}).get("row") or {}).get("id") or ""
    ls = _frame_call(fr, "list", {"list": pick["key"]})
    rows = (ls.get("data") or {}).get("rows") or []
    if pick["rules"]["read"] != "admin":
        step("see it in the list", any(x.get("id") == rid for x in rows), str(ls.get("error") or ""))
    if pick["rules"]["update"] == "own" or pick["rules"]["update"] == "admin":
        up = _frame_call(fr, "update", {"list": pick["key"], "id": rid, "data": data})
        step("change it", bool(up.get("ok")) if pick["rules"]["update"] == "own" else not up.get("ok"),
             str(up.get("error") or "") if pick["rules"]["update"] == "own" else "")
    rm = _frame_call(fr, "remove", {"list": pick["key"], "id": rid})
    step("remove it", bool(rm.get("ok")) if pick["rules"]["delete"] == "own" else not rm.get("ok"), str(rm.get("error") or ""))
    so = _frame_call(fr, "signout", {})
    step("sign out", bool(so.get("ok")))
    return out


def _drop_walk(r) -> None:
    """Remove the check's own accounts and entries from the PREVIEW dataset (they must never look like real people)."""
    from sqlalchemy import delete as sqldel, select
    sk = CL.site_key(r, "preview")
    with session() as s:
        ids = s.scalars(select(W.SiteAppMember.id).where(W.SiteAppMember.site_id == sk, W.SiteAppMember.email.like("hoola-check-%"))).all()
        if ids:
            s.execute(sqldel(W.SiteAppRow).where(W.SiteAppRow.site_id == sk, W.SiteAppRow.owner.in_(ids)))
            s.execute(sqldel(W.SiteAppMember).where(W.SiteAppMember.id.in_(ids)))


def _serve_route(r):
    from . import service as S

    def handler(route):
        req = route.request
        u = urlparse(req.url)
        path = unquote(u.path)
        try:
            m = re.match(r"^/api/app-preview/([^/]+)/?(.*)$", path)
            if m:
                body, mime, hdr = S.preview_file(m.group(1), m.group(2))
                route.fulfill(status=200, body=body, headers={**hdr, "Content-Type": mime})
                return
            m = re.match(r"^/api/cloud/([^/]+)/([a-z_]+)$", path)
            if m and req.method == "POST":
                try:
                    args = json.loads(req.post_data or "{}")
                except ValueError:
                    args = {}
                tok = (req.headers.get("authorization") or "").removeprefix("Bearer ").strip()
                try:
                    out = CL.call(m.group(1), m.group(2), args, tok, _ip())
                    route.fulfill(status=200, body=json.dumps(out), headers={"Content-Type": "application/json"})
                except CL.CloudError as e:
                    route.fulfill(status=getattr(e, "code", 400) or 400, body=json.dumps({"detail": str(e)}),
                                  headers={"Content-Type": "application/json"})
                return
            route.fulfill(status=404, body="not found")
        except Exception as e:                              # noqa: BLE001
            route.fulfill(status=404 if "not found" in str(e) else 500, body=str(e)[:200])
    return handler


def _browser_run(r, out: dict[str, Any]) -> None:
    from playwright.sync_api import sync_playwright
    errs: list[str] = []
    notes: list[str] = out.setdefault("notes", [])
    url = f"{ORIGIN}/api/app-preview/{r.preview_token}/"
    with sync_playwright() as pw:
        b = pw.chromium.launch(**_chromium_kw())
        try:
            for name, vp in (("phone", {"width": 390, "height": 780}), ("desktop", {"width": 1280, "height": 860})):
                ctx = b.new_context(viewport=vp)
                pg = ctx.new_page()
                pg.route(f"{ORIGIN}/**", _serve_route(r))
                seen: list[str] = []
                pg.on("pageerror", lambda e, seen=seen: seen.append("page error: " + str(e)[:160]))
                pg.on("console", lambda m, seen=seen: seen.append("console error: " + m.text[:160])
                      if m.type == "error" and not re.search(r"status of 40[13]\b", m.text) else None)   # 401 / 403 = a rule saying no
                pg.on("requestfailed", lambda q, seen=seen: seen.append("request failed: " + q.url[-80:]))
                res: dict[str, Any] = {"size": name}
                try:
                    pg.goto(url, wait_until="networkidle", timeout=30000)
                    fr = next((x for x in pg.frames if "/__app/" in x.url), None)
                    for _ in range(100):
                        if fr:
                            break
                        pg.wait_for_timeout(100)
                        fr = next((x for x in pg.frames if "/__app/" in x.url), None)
                    if fr is None:
                        raise RuntimeError("the app never opened inside its page")
                    fr.wait_for_function("(() => { const r = document.getElementById('root'); return !!r && (r.children.length > 0 || r.textContent.trim().length > 0); })()", timeout=15000)
                    text = fr.inner_text("body").strip()
                    res["shows_something"] = len(text) > 0
                    wide = fr.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
                    res["fits_width"] = not wide
                    if name == "desktop" and (CL.schema(r).get("lists")):
                        res["journey"] = _journey(r, fr, notes)
                except Exception as e:                      # noqa: BLE001
                    seen.append("could not open: " + str(e)[:200])
                res["errors"] = seen[:6]
                out.setdefault("sizes", []).append(res)
                ctx.close()
        finally:
            b.close()
            _drop_walk(r)
    del errs


def _built_stamp(r) -> int:
    from . import service as S
    try:
        return (S.ver_dir(r, int(r.version or 0)) / "build.json").stat().st_mtime_ns
    except OSError:
        return 0


def browser_check(r, force: bool = False) -> dict[str, Any]:
    """Real Chromium at phone and desktop size. Served in-process; safe to call from any thread."""
    cached = load(r).get("browser")
    key = {"version": int(r.version or 0), "schema_version": CL.schema(r).get("version", 0), "built": _built_stamp(r)}
    if cached and not force and all(cached.get(k) == v for k, v in key.items()):
        return cached
    out: dict[str, Any] = {**key, "ran": False, "at": now().isoformat()}
    if not int(r.version or 0):
        out.update(ok=False, why="Nothing is built yet.")
        return out
    box: dict[str, Any] = {}

    def work() -> None:
        try:
            _browser_run(r, box)
        except Exception as e:                              # noqa: BLE001
            box["crash"] = str(e)[:300]
    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(150)
    if "crash" in box or t.is_alive() or "sizes" not in box:
        out.update(ran=False, ok=None, why="The browser check could not run here: " + (box.get("crash") or "it did not finish in time"))
        return out
    problems = []
    for s in box["sizes"]:
        if not s.get("shows_something"):
            problems.append(f"at {s['size']} size the app shows nothing")
        if s.get("fits_width") is False:
            problems.append(f"at {s['size']} size the page is wider than the screen")
        for e in s.get("errors") or []:
            problems.append(f"at {s['size']} size: {e}")
        for st in ((s.get("journey") or {}).get("steps") or []):
            if not st["ok"]:
                problems.append(f"{st['step']} did not work" + (f" ({st['say']})" if st["say"] else ""))
    out.update(ran=True, ok=not problems, problems=problems[:8], sizes=box["sizes"], notes=box.get("notes", []))
    _store(r, "browser", out)
    return out


def say_browser(b: dict[str, Any]) -> str:
    if not b.get("ran"):
        return b.get("why") or "The browser check did not run."
    if b["ok"]:
        j = next((s.get("journey") for s in b["sizes"] if s.get("journey")), None)
        walk = f" and walked {len(j['steps'])} steps with the saved data" if j else ""
        return f"Browser check passed: opened at phone and desktop size{walk}, no errors."
    return "Browser check FAILED: " + "; ".join(b["problems"][:3]) + "."


# ------------------------------------------------------------------ 3. quick scan  /  4. deep scan
def _src_files(r, v: int):
    from . import service as S
    d = S.ver_dir(r, v) / "src"
    if not d.exists():
        d = S.src_dir(r)
    for p in sorted(d.rglob("*")):
        if p.is_file() and "node_modules" not in p.parts:
            rel = p.relative_to(d).as_posix()
            if RL.ext(rel) in RL.TEXT_EXT:
                yield rel, p


def _secret_scan(r, v: int) -> list[dict[str, str]]:
    from . import service as S
    out = []
    todo = [(rel, p) for rel, p in _src_files(r, v) if rel not in RL.LOCKED]
    dist = S.ver_dir(r, v) / "dist"
    if dist.exists():
        todo += [("dist/" + p.relative_to(dist).as_posix(), p) for p in dist.rglob("*") if p.is_file() and p.suffix in (".js", ".html", ".css")]
    for rel, p in todo:
        try:
            text = p.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for rx, what in SECRETS:
            m = rx.search(text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                out.append(_item("fail", f"{rel}:{line}", f"{what} is written in the app. Anything in the code is public; move the secret out of the app."))
                break
    return out


def _cloud_scan(r) -> list[dict[str, str]]:
    sch = CL.schema(r)
    out = []
    for lst in sch.get("lists") or []:
        if lst.get("hidden"):
            continue
        pers = CL._personal(lst)
        rd, cr = lst["rules"]["read"], lst["rules"]["create"]
        if rd == "public" and pers:
            if lst.get("public_ack"):
                out.append(_item("warn", f"list {lst['key']}", f"Anyone on the internet can read {', '.join(pers)} (you said yes to this)."))
            else:
                out.append(_item("fail", f"list {lst['key']}", f"Anyone on the internet can read {', '.join(pers)} of every entry and you have not said yes to that. "
                                 "Change the rule to 'own' (each member sees their own) or 'admin', or confirm it is meant to be public."))
        elif rd == "members" and pers:
            out.append(_item("warn", f"list {lst['key']}", f"Every signed-in member can read everyone's {', '.join(pers)}."))
        if cr == "public":
            out.append(_item("info", f"list {lst['key']}", "Anyone can add entries without signing in (30 per 10 minutes per visitor)."))
    return out


def quick(r, v: int, with_tests: bool = True) -> dict[str, Any]:
    """The going-live scan. FAIL items block publish; warn / info never do."""
    items = _secret_scan(r, v) + _cloud_scan(r)
    rt = None
    if with_tests and CL.schema(r).get("lists"):
        rt = rule_tests(r)
        if not rt["ok"]:
            f = rt["failed"][0]
            items.append(_item("fail", f"list {f['list']}", say_rule_tests(rt)))
    items.append(_item("info", "packages", "Packages are the fixed set Hoola vets; the outside advisory feed is not connected, so none were checked against it."))
    fails = [x for x in items if x["level"] == "fail"]
    out = {"kind": "quick", "ok": not fails, "fail": len(fails), "warn": sum(x["level"] == "warn" for x in items),
           "items": items, "version": v, "at": now().isoformat()}
    _store(r, "quick", out)
    return out


LINK_BLANK = re.compile(r"target=[\"']_blank[\"'](?![^>]*rel=[\"'][^\"']*noopener)")


def deep(r, v: int) -> dict[str, Any]:
    """On demand before a big launch: the quick scan, code patterns, built-file leaks, list usage, a fresh browser check."""
    q = quick(r, v)
    items = [x for x in q["items"]]
    sch = CL.schema(r)
    keys = {x["key"] for x in sch.get("lists") or [] if not x.get("hidden")}
    used: set[str] = set()
    from . import service as S
    for rel, p in _src_files(r, v):
        if rel in RL.LOCKED:
            continue
        try:
            text = p.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in LINK_BLANK.finditer(text):
            items.append(_item("warn", f"{rel}:{text.count(chr(10), 0, m.start()) + 1}", 'A link opens a new tab without rel="noopener noreferrer".'))
        for m in re.finditer(r"""["']javascript:""", text):
            items.append(_item("fail", f"{rel}:{text.count(chr(10), 0, m.start()) + 1}", "A javascript: link is written in the code."))
        for m in re.finditer(r"""["']http://(?!localhost|127\.0\.0\.1)[^"']+""", text):
            items.append(_item("warn", f"{rel}:{text.count(chr(10), 0, m.start()) + 1}", "A plain http:// address is used; use https://."))
        for m in re.finditer(r"""collection\(\s*["'`]([A-Za-z0-9_\-]+)["'`]\s*\)""", text):
            k = m.group(1)
            used.add(k)
            if k not in keys:
                items.append(_item("fail", f"{rel}:{text.count(chr(10), 0, m.start()) + 1}", f"The code asks for a list '{k}' that this app does not have."))
    for k in sorted(keys - used):
        items.append(_item("info", f"list {k}", "No screen in the app uses this list yet."))
    dist = S.ver_dir(r, v) / "dist"
    if dist.exists() and any(p.suffix == ".map" for p in dist.rglob("*")):
        items.append(_item("warn", "built files", "Source maps are present in this preview build (they are removed from the live build)."))
    b = browser_check(r, force=True)
    if b.get("ran") and not b["ok"]:
        items.append(_item("fail", "browser", say_browser(b)))
    elif not b.get("ran"):
        items.append(_item("warn", "browser", say_browser(b)))
    fails = [x for x in items if x["level"] == "fail"]
    out = {"kind": "deep", "ok": not fails, "fail": len(fails), "warn": sum(x["level"] == "warn" for x in items), "items": items,
           "version": v, "at": now().isoformat(),
           "not_a_model_review": "This deep scan is checks in code; no model reviews the code (not connected)."}
    _store(r, "deep", out)
    return out


def blockers(r, v: int) -> list[str]:
    """What publish_check adds: FAIL items of the quick scan + a failed browser check (one that could not run only warns)."""
    bl = [f"{x['where']}: {x['say']}" for x in quick(r, v)["items"] if x["level"] == "fail"]
    b = browser_check(r)
    if b.get("ran") and not b.get("ok"):
        bl.append(say_browser(b))
    return bl


def overview(r) -> dict[str, Any]:
    d = load(r)
    rt = d.get("rule_tests")
    return {"rule_tests": ({**{k: v for k, v in rt.items() if k not in ("checks", "rules")}, "stale": rt.get("rules") != rules_print(r)} if rt else None),
            "browser": d.get("browser"), "quick": d.get("quick"), "deep": d.get("deep")}
