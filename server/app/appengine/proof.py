"""v0.814 the L8 proof card: the five card asks built in the box, end to end, through the SAME tool the model uses.

For each ask: create (the template) -> write its files with app_engine action=write (every rule applies) -> build in
the box -> the preview is served -> a real Chromium opens it (no page errors, her words on screen, one click works)
-> her tap publishes it -> /apps/<name>/ serves the same app. Plus the planted writes the rules must refuse.
No model is called: this proves the engine, not a model's code. `python -m app.appengine proof`."""
from __future__ import annotations

import asyncio
import http.server
import os
import socketserver
import threading
import time
from typing import Any

from . import proof_apps as PA
from . import service as AE

TENANT = "__aeproof__"


def _ctx():
    from ..agent.tools import Ctx
    return Ctx(tenant_id=TENANT, conversation_id="", actor="owner")


def _tool(**kw) -> dict[str, Any]:
    from ..agent.appengine_tools import app_engine
    return asyncio.run(app_engine(_ctx(), **kw))


class _H(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):  # noqa: N802
        """v0.827 the Hoola Cloud calls the app's shell makes (the same CL.call the real route uses)."""
        import json
        from . import cloud as CL
        parts = self.path.split("?", 1)[0].split("/")
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b"{}"
        tok = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        try:
            if parts[1:3] != ["api", "cloud"]:
                raise CL.CloudError("not found", 404)
            out, code = CL.call(parts[3], parts[4], json.loads(body or b"{}"), tok, "127.0.0.1"), 200
        except CL.CloudError as e:
            out, code = {"detail": str(e)}, e.code
        data = json.dumps(out).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        p = self.path.split("?", 1)[0]
        try:
            if p.startswith("/api/app-preview/"):
                rest = p[len("/api/app-preview/"):]
                tok, _, path = rest.partition("/")
                data, ctype, hdr = AE.preview_file(tok, path)
            elif p.startswith("/apps/"):
                slug, _, path = p[len("/apps/"):].partition("/")
                data, ctype, hdr = AE.live_file(slug, path)
            else:
                raise AE.AppEngineError("not found", 404)
        except AE.AppEngineError as e:
            self.send_response(e.code if e.code in (403, 404) else 404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        for k, v in hdr.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def _server() -> tuple[socketserver.ThreadingTCPServer, int]:
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _app_frame(pg):
    """v0.827 every app runs in a sealed frame inside its Hoola shell: the walk reads and clicks THAT frame."""
    for _ in range(150):
        f = next((x for x in pg.frames if "/__app/" in x.url), None)
        if f is not None:
            try:
                f.wait_for_load_state("networkidle", timeout=10000)
            except Exception:                           # noqa: BLE001
                pass
            return f
        pg.wait_for_timeout(100)
    raise RuntimeError("the app frame never appeared inside its shell")


def _walk(url: str, must: list[str], click: tuple[str, str] | None, fill: dict[str, str] | None = None,
          after_fill: str = "", submit: str = "") -> dict[str, Any]:
    from playwright.sync_api import sync_playwright
    exe = os.environ.get("HOOLA_CHROMIUM") or ""
    errs: list[str] = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(**({"executable_path": exe} if exe else {}))
        try:
            pg = b.new_page(viewport={"width": 1280, "height": 860})
            pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
            pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None)
            t0 = time.time()
            pg.goto(url, wait_until="networkidle")
            fr = _app_frame(pg)
            fr.wait_for_selector("#root *", timeout=15000)
            text = fr.inner_text("body")
            tags = fr.evaluate("document.querySelectorAll('[data-hs]').length")
            helper = fr.evaluate("!!document.querySelector('script[src$=\"__hoola/preview.js\"]')")
            shell_clean = pg.evaluate("!document.querySelector('[data-hs]') && !!document.querySelector('meta[name=hoola-app]')")
            sealed = fr.evaluate("(() => { try { localStorage.getItem('x'); return false; } catch (e) { return true; } })()")
            seen = [w for w in must if w in text]
            clicked = None
            if click:
                fr.get_by_role("button", name=click[0]).first.click() if fr.get_by_role("button", name=click[0]).count() \
                    else fr.get_by_role("tab", name=click[0]).first.click()
                fr.wait_for_timeout(400)
                clicked = click[1] in fr.inner_text("body")
            filled = None
            if fill:
                for sel, val in fill.items():
                    fr.fill(sel, val)
                fr.get_by_role("button", name=submit).first.click()
                try:
                    fr.get_by_text(after_fill).first.wait_for(timeout=10000)
                    filled = True
                except Exception:                       # noqa: BLE001 - the card says it did not arrive
                    filled = False
            phone = b.new_page(viewport={"width": 390, "height": 800})
            phone.goto(url, wait_until="networkidle")
            pf = _app_frame(phone)
            pf.wait_for_selector("#root *", timeout=15000)
            sw = pf.evaluate("document.documentElement.scrollWidth")
            return {"errors": errs, "seen": seen, "missing": [w for w in must if w not in seen], "clicked": clicked,
                    "load_s": round(time.time() - t0, 2), "phone_overflow": sw > 392, "source_tags": tags, "helper": helper,
                    "shell_clean": shell_clean, "sealed": sealed, "filled": filled}
        finally:
            b.close()


def _rules_hold(r) -> bool:
    """The server, not the page, decides: a visitor may add a request but not read any; a signed-up member may not
    read others' requests; she (owner) reads them all."""
    from . import cloud as CL
    k = CL.key_of(r, "preview")
    try:
        CL.call(k, "list", {"list": "requests"})
        return False                                     # an anonymous visitor read the list
    except CL.CloudError as e:
        if e.code != 401:
            return False
    CL.call(k, "create", {"list": "requests", "data": {"name": "Rule check", "mobile": "9123456780", "date": "2026-12-02", "slot": "evening"}})
    tok = CL.call(k, "signup", {"email": "rulecheck@example.com", "password": "a-long-password", "name": "R"})["token"]
    try:
        CL.call(k, "list", {"list": "requests"}, tok)
        return False                                     # a plain member read everyone's requests
    except CL.CloudError as e:
        if e.code != 403:
            return False
    try:
        CL.call(k, "update", {"list": "requests", "id": "x", "data": {"status": "booked"}}, tok)
        return False
    except CL.CloudError:
        pass
    return any(x["name"] == "Rule check" for x in CL.owner_rows(r, "preview", "requests"))


def _apart(r) -> bool:
    """Preview and live are different data: live started empty (no sample, no preview row), got only its own visitor."""
    from . import cloud as CL
    live = CL.owner_rows(r, "live", "requests")
    prev = CL.owner_rows(r, "preview", "requests")
    return (len(live) == 1 and live[0]["name"] == "Asha Patil" and not any(x.get("sample") for x in live)
            and any(x.get("sample") for x in prev) and any(x["name"] == "Asha Patil" for x in prev)
            and not CL.members(r, "live"))


def run(browser: bool = True, keep: bool = False) -> dict[str, Any]:
    from ..db import init_db
    init_db()
    os.environ.setdefault("HOOLA_APPENGINE_AUTOBUILD", "0")
    rows, srv, port = [], None, 0
    if browser:
        srv, port = _server()
    traps = {"refused": 0, "total": len(PA.TRAPS), "leaked": []}
    try:
        for ask in PA.ASKS:
            row: dict[str, Any] = {"ask": ask["key"], "name": ask["name"]}
            t0 = time.time()
            try:
                app = _tool(action="create", name=ask["name"], brief=ask["brief"], palette=ask["palette"])
                aid = app["id"]
                if ask.get("cloud"):                    # v0.827 the app's Hoola Cloud lists, before the code that uses them
                    _tool(action="cloud_change", app=aid, changes=ask["cloud"])
                for path, code in ask["files"].items():
                    _tool(action="write", app=aid, path=path, code=code)
                if ask["key"] == "tasks":
                    for path, code, _rule in PA.TRAPS:
                        try:
                            _tool(action="write", app=aid, path=path, code=code)
                            traps["leaked"].append(path)
                        except Exception:              # noqa: BLE001 - a refusal is the expected answer
                            traps["refused"] += 1
                b = _tool(action="build", app=aid)
                r = AE._load(TENANT, aid)
                lb = AE.logs(TENANT, aid)["last_build"]
                row.update(built=bool(b.get("built")), version=r.version, build_s=lb.get("seconds"), types_ok=lb.get("types_ok"),
                           problems=(lb.get("build_problems") or [])[:3] + (lb.get("types") or [])[:3])
                chk = AE.check_all(r)
                row["rules_ok"] = chk["ok"]
                fill = ask.get("fill")
                sub = (ask.get("click") or ("", ""))[0]
                if browser and row["built"]:
                    row["preview"] = _walk(f"http://127.0.0.1:{port}/api/app-preview/{r.preview_token}/", ask["must"], ask.get("click"),
                                           fill, ask.get("after_fill", ""), sub)
                if ask.get("cloud"):
                    row["rules_hold"] = _rules_hold(r)
                if row["built"]:
                    pub = AE.publish(TENANT, aid, r.version, confirm=True)
                    row["live"] = pub["live_url"]
                    if browser:
                        row["live_walk"] = _walk(f"http://127.0.0.1:{port}{pub['live_url']}", ask["must"][:1], None,
                                                 fill, ask.get("after_fill", ""), sub)
                    if ask.get("cloud") and browser:
                        row["datasets_apart"] = _apart(AE._load(TENANT, aid))
                row["total_s"] = round(time.time() - t0, 1)
            except Exception as e:                     # noqa: BLE001 - the card says what broke
                row["error"] = f"{type(e).__name__}: {e}"[:400]
            rows.append(row)
    finally:
        if srv:
            srv.shutdown()
        if not keep:
            for a in AE.list_(TENANT):
                try:
                    AE.unpublish(TENANT, a["id"], confirm=True)
                    AE.delete_app(TENANT, a["id"])
                except Exception:                      # noqa: BLE001
                    pass

    def good(x):
        p = x.get("preview") or {}
        return (x.get("built") and x.get("types_ok") and x.get("rules_ok") and not x.get("error")
                and x.get("rules_hold", True) and x.get("datasets_apart", True)
                and (not browser or (not p.get("errors") and not p.get("missing") and p.get("clicked") and not p.get("phone_overflow")
                                     and p.get("source_tags") and p.get("helper")                       # v0.825 click -> source in the preview
                                     and p.get("sealed") and p.get("shell_clean") and p.get("filled") is not False  # v0.827
                                     and not (x.get("live_walk") or {}).get("source_tags") and not (x.get("live_walk") or {}).get("helper")
                                     and not (x.get("live_walk") or {}).get("errors") and not (x.get("live_walk") or {}).get("missing"))))
    ok = sum(1 for x in rows if good(x))
    secs = [x["build_s"] for x in rows if x.get("build_s")]
    return {"apps_ok": ok, "apps": len(rows), "traps_refused": traps["refused"], "traps": traps["total"],
            "traps_leaked": traps["leaked"], "build_s_median": sorted(secs)[len(secs) // 2] if secs else None,
            "browser": browser, "rows": rows,
            "verdict": "PASS" if ok == len(rows) and traps["refused"] == traps["total"] else "FAIL"}
