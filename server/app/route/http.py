"""v0.999.254 MAKE PARITY - THE WEB REQUEST STEP, at the level of Make's HTTP app (v4), own code.

Make's three modules, as one step type "http" (field "action"):
  request   Make a request   GET HEAD POST PUT PATCH DELETE OPTIONS; headers; query; body as JSON, a form
                             (x-www-form-urlencoded), multipart/form-data with files, or her own raw text with a
                             content type; parse the answer or keep it as text; pagination (offset, page, next
                             link, cursor) with the items path and a limit; timeout 1-300 s; redirects (max 10)
                             on or off; cookies shared with the route's other web requests in the same run; ask
                             for compressed answers; "return an error if the request fails" (4xx / 5xx = a failed
                             step) on or off.
  download   Download a file the answer is kept as a file (24 hours) - its file id goes on to later steps.
  resolve    Resolve URL     follows the redirects and gives the address it ends at.

Sign-ins stay the saved ones (v0.999.246): Basic, API key, bearer, OAuth access token - sent only to their own
site, never carried across a redirect to another site. Every hop passes the private-address guard. Answers are
capped (100,000 characters of text; 25 MB for a file).
"""
from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urljoin, urlsplit

METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
BODY_TYPES = ("none", "json", "form", "multipart", "raw")
ACTIONS = ("request", "download", "resolve")
PAGINATION = ("none", "offset", "page", "url", "cursor")
TEXT_CAP = 100_000
FILE_CAP = 25 * 1024 * 1024
PAGES_MAX = 100
ITEMS_MAX = 10_000


class HttpError(ValueError):
    pass


def validate(step: dict, sid: str) -> None:
    from ..agent.tools import ToolError
    act = str(step.get("action") or "request")
    if act not in ACTIONS:
        raise ToolError(f"Step '{sid}': a web request's action is one of: {', '.join(ACTIONS)}")
    if not str(step.get("url") or "").strip():
        raise ToolError(f"Step '{sid}': a web request needs an address (url)")
    m = str(step.get("method") or "GET").upper()
    if "{{" not in m and m not in METHODS:
        raise ToolError(f"Step '{sid}': the method is one of {', '.join(METHODS)}")
    bt = str(step.get("body_type") or "")
    if bt and bt not in BODY_TYPES:
        raise ToolError(f"Step '{sid}': the body type is one of {', '.join(BODY_TYPES)}")
    if bt == "raw" and not str(step.get("content_type") or "").strip():
        raise ToolError(f"Step '{sid}': a raw body needs its content type (like application/xml)")
    for k in ("headers", "query", "form"):
        if step.get(k) not in (None, "") and not isinstance(step.get(k), (dict, str)):
            raise ToolError(f"Step '{sid}': {k} must be an object of name: value")
    if step.get("files") not in (None, "", []) and not isinstance(step.get("files"), (list, str)):
        raise ToolError(f"Step '{sid}': files must be a list like [{{field: 'file', file_id: '...'}}]")
    t = step.get("timeout")
    if t not in (None, "") and "{{" not in str(t):
        try:
            if not 1 <= int(t) <= 300:
                raise ValueError
        except (TypeError, ValueError):
            raise ToolError(f"Step '{sid}': the timeout is 1-300 seconds")
    pg = step.get("pagination")
    if pg not in (None, "", {}):
        if not isinstance(pg, dict) or str(pg.get("type") or "none") not in PAGINATION:
            raise ToolError(f"Step '{sid}': pagination type is one of {', '.join(PAGINATION)}")
        if str(pg.get("type")) != "none" and not str(pg.get("items") or "").strip() and str(pg.get("type")) != "url":
            raise ToolError(f"Step '{sid}': pagination needs the items path (where the list is in each answer)")
    if step.get("auth") not in (None, "") and not __import__("re").match(r"^[A-Za-z_][A-Za-z0-9_]{0,49}$", str(step["auth"])):
        raise ToolError(f"Step '{sid}': auth must be the name of a saved sign-in")


def _obj(v: Any, what: str) -> dict:
    if v in (None, ""):
        return {}
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            raise HttpError(f"{what} must be an object of name: value")
    if not isinstance(v, dict):
        raise HttpError(f"{what} must be an object of name: value")
    return v


def _num_or(v: Any, d: int) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


def _dig(obj: Any, path: str) -> Any:
    from ..agent.dhara_data import _get
    return _get(obj, str(path or "").strip())


async def run(tenant: str, step: dict, ctx: dict, resolve) -> dict:
    import httpx
    from ..agent import scrape_tools as st
    R = (lambda v: resolve(v, ctx))
    act = str(step.get("action") or "request")
    url = str(R(step.get("url")) or "").strip()
    guard = await asyncio.to_thread(st._guard_url, url)
    method = str(R(step.get("method")) or ("POST" if step.get("body") not in (None, "") and act == "request" else "GET")).upper()
    if act == "resolve":
        method = "HEAD" if str(step.get("method") or "").upper() == "HEAD" else "GET"
    if method not in METHODS:
        raise HttpError(f"'{method}' is not a method (use {', '.join(METHODS)})")
    headers = {str(k): str(v) for k, v in _obj(R(step.get("headers")), "headers").items()}
    plain = dict(headers)
    if step.get("auth"):
        from . import workspace as WS
        try:
            guard, headers = await asyncio.to_thread(WS.apply_auth, tenant, str(step["auth"]), guard, headers)
        except WS.WorkspaceError as e:
            raise HttpError(str(e))
    if step.get("compressed"):
        headers.setdefault("Accept-Encoding", "gzip, deflate")
    query = {str(k): ("" if v is None else v if isinstance(v, (str, int, float)) else json.dumps(v))
             for k, v in _obj(R(step.get("query")), "query").items()}
    bt = str(step.get("body_type") or ("json" if step.get("body") not in (None, "") else "none"))
    if method in ("GET", "HEAD") and bt != "none" and step.get("body") in (None, "") and not step.get("form"):
        bt = "none"
    kw: dict[str, Any] = {}
    if bt == "json":
        jb = R(step.get("body"))
        if isinstance(jb, str) and jb.strip()[:1] in ("{", "["):   # typed in the page's box: the JSON she wrote, as JSON
            try:
                jb = json.loads(jb)
            except ValueError:
                raise HttpError("The body is not valid JSON - check its brackets and quotes")
        kw["json"] = jb
    elif bt == "form":
        kw["data"] = {str(k): ("" if v is None else str(v)) for k, v in _obj(R(step.get("form") if step.get("form") not in (None, "") else step.get("body")), "form").items()}
    elif bt == "raw":
        b = R(step.get("body"))
        kw["content"] = (b if isinstance(b, str) else json.dumps(b, ensure_ascii=False)).encode("utf-8")
        headers["Content-Type"] = str(R(step.get("content_type")) or "text/plain")
    elif bt == "multipart":
        kw["data"] = {str(k): ("" if v is None else str(v)) for k, v in _obj(R(step.get("form")), "form").items()}
        files = R(step.get("files")) or []
        if isinstance(files, str):
            try:
                files = json.loads(files)
            except ValueError:
                raise HttpError("files must be a list of {field, file_id}")
        up = []
        from ..mailbox import service as ms
        for f in files if isinstance(files, list) else [files]:
            if not isinstance(f, dict) or not f.get("file_id"):
                raise HttpError("Each file needs its file id (from an earlier step)")
            try:
                row = ms._file_row(tenant, str(f["file_id"]))
                data = open(row.stored_path, "rb").read()
            except Exception as e:   # noqa: BLE001
                raise HttpError(f"The file {f.get('file_id')} is not there any more ({str(e)[:80]})")
            up.append((str(f.get("field") or "file"), (str(f.get("name") or row.name or "file"), data,
                                                       str(f.get("mime") or "application/octet-stream"))))
        kw["files"] = up
    timeout = float(R(step.get("timeout")) or 40)
    timeout = max(1.0, min(timeout, 300.0))
    follow = step.get("redirects") is not False and str(step.get("redirects")).lower() != "false"
    jar = ctx.setdefault("_cookies", {}) if step.get("share_cookies") else None
    fail = step.get("fail_on_error") is not False and str(step.get("fail_on_error")).lower() != "false"
    parse = step.get("parse") is not False and str(step.get("parse")).lower() != "false"

    def one(u: str, q: dict) -> "httpx.Response":
        url_now, meth, hdrs, body_kw = u, method, dict(headers), dict(kw)
        home = (urlsplit(guard).hostname or "").lower()
        hops: list[str] = []
        for _hop in range(11):
            ck = {k: v for k, v in (jar or {}).get((urlsplit(url_now).hostname or "").lower(), {}).items()} if jar is not None else None
            r = httpx.request(meth, url_now, params=q if not hops else None, headers=hdrs, timeout=timeout,
                              follow_redirects=False, cookies=ck, **body_kw)
            if jar is not None:
                host = (urlsplit(url_now).hostname or "").lower()
                for c in r.cookies.jar:
                    jar.setdefault(host, {})[c.name] = c.value
                    if len(jar[host]) > 50:
                        break
            loc = r.headers.get("location")
            if not follow or r.status_code not in (301, 302, 303, 307, 308) or not loc:
                r._hoola_hops = hops        # noqa: SLF001
                return r
            nxt = st._guard_url(urljoin(url_now, loc))
            hops.append(nxt)
            if (urlsplit(nxt).hostname or "").lower() != home:
                hdrs = {k: v for k, v in plain.items() if k.lower() not in ("authorization", "cookie")}
            if r.status_code in (301, 302, 303) and meth not in ("GET", "HEAD"):
                meth, body_kw = "GET", {}
            url_now = nxt
        raise HttpError("the site sent the request round more than 10 redirects")

    def shape(r) -> dict:
        ct = r.headers.get("content-type", "")
        out: dict[str, Any] = {"status": r.status_code, "headers": {k.lower(): v for k, v in r.headers.items()},
                               "url": str(r.url), "redirects": len(getattr(r, "_hoola_hops", []))}
        if method == "HEAD":
            return out
        parsed = None
        if parse and ("json" in ct or r.content[:1] in (b"{", b"[")):
            try:
                parsed = r.json()
            except Exception:   # noqa: BLE001
                parsed = None
        out["json"] = parsed
        out["text"] = None if parsed is not None else r.text[:TEXT_CAP]
        if parsed is None and parse and ("xml" in ct):
            try:
                from ..agent.dhara_data import _text
                out["data"] = _text({"action": "xml_to_data", "value": r.text[:TEXT_CAP]}, lambda v: v)
            except Exception:   # noqa: BLE001
                pass
        return out

    def go() -> dict:
        if act == "resolve":
            r = one(guard, query)
            return {"url": str(r.url), "status": r.status_code, "redirects": len(getattr(r, "_hoola_hops", []))}
        if act == "download":
            r = one(guard, query)
            if fail and r.status_code >= 400:
                return {"status": r.status_code, "_fail": f"the site answered {r.status_code}"}
            data = r.content
            if len(data) > FILE_CAP:
                raise HttpError("The file is over 25 MB")
            name = str(R(step.get("name")) or "").strip()
            if not name:
                cd = r.headers.get("content-disposition", "")
                import re
                m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd)
                name = (m.group(1) if m else (urlsplit(str(r.url)).path.rsplit("/", 1)[-1] or "download"))[:120]
            from ..agent.dhara_data import _store
            f = _store(tenant, name, data)
            return {"status": r.status_code, "file": f, "file_id": f.get("file_id"), "name": f.get("name"),
                    "size": len(data), "content_type": r.headers.get("content-type", "")}
        pg = step.get("pagination") or {}
        ptype = str(pg.get("type") or "none") if isinstance(pg, dict) else "none"
        if ptype == "none":
            out = shape(one(guard, query))
            if fail and out["status"] >= 400:
                out["_fail"] = f"the site answered {out['status']}"
            return out
        # pagination (Make's four kinds): every page's items gathered into one list
        items_path = str(pg.get("items") or "")
        limit = max(1, min(int(R(pg.get("limit")) or 1000), ITEMS_MAX))
        size = pg.get("size")
        q = dict(query)
        if size not in (None, ""):
            q[str(pg.get("size_param") or "limit")] = R(size)
        off = int(R(pg.get("start")) or (1 if ptype == "page" else 0)) if ptype in ("offset", "page") else 0
        token = R(pg.get("start")) if ptype == "cursor" else None
        u = guard
        items: list = []
        pages = []
        for n in range(PAGES_MAX):
            if ptype == "offset":
                q[str(pg.get("param") or "offset")] = off
            elif ptype == "page":
                q[str(pg.get("param") or "page")] = off
            elif ptype == "cursor" and token not in (None, ""):
                q[str(pg.get("param") or "cursor")] = token
            r = one(u, q)
            sh = shape(r)
            if fail and sh["status"] >= 400:
                return {**sh, "_fail": f"the site answered {sh['status']} on page {n + 1}",
                        "items": items, "pages": len(pages)}
            body = sh.get("json") if sh.get("json") is not None else sh.get("data")
            got = _dig(body, items_path) if items_path else body
            got = got if isinstance(got, list) else ([] if got is None else [got])
            pages.append(sh["status"])
            items.extend(got[:max(0, limit - len(items))])
            if len(items) >= limit or not got:
                break
            if size not in (None, "") and ptype in ("offset", "page") and len(got) < int(_num_or(R(size), 0)):
                break                                    # a short page is the last one
            if ptype == "offset":
                off += len(got)
            elif ptype == "page":
                off += 1
            elif ptype == "cursor":
                token = _dig(body, str(pg.get("next") or "next_cursor"))
                if token in (None, ""):
                    break
            elif ptype == "url":
                nxt = _dig(body, str(pg.get("next") or "next")) if pg.get("next") else None
                if not nxt:
                    import re
                    m = re.search(r'<([^>]+)>;\s*rel="?next"?', r.headers.get("link", ""))
                    nxt = m.group(1) if m else None
                if not nxt:
                    break
                u = st._guard_url(urljoin(str(r.url), str(nxt)))
                q = {}
        return {"status": pages[-1] if pages else 0, "items": items, "count": len(items), "pages": len(pages)}

    return await asyncio.to_thread(go)
