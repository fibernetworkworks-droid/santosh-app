"""Moving a country rule up the D3 ladder (FINANCE_GLOBAL_PLAN decision D3).

read     Hoola fetched the official page (one of the pack's official hosts) and the quoted sentence is really on it -> source_read
confirm  a named qualified person confirmed the rule (and may correct its value)                                     -> checked

Both write the country's review file (pack.review_dir()/<CC>.json), never the shipped pack, and leave an audit row. Country rules
are the same for every user, so only the Hoola owner may change them (the routes check that)."""
from __future__ import annotations

import html
import json
import re
from datetime import date, timedelta
from typing import Any, Callable

from . import evidence as EV
from . import pack as P

READ_DAYS = 180
CHECK_DAYS = 365


class ReviewError(ValueError):
    pass


def _host_ok(cc: str, url: str) -> None:
    p = P.load(cc)
    if p is None:
        raise ReviewError(f"No pack for {cc}.")
    if not str(url).startswith("https://"):
        raise ReviewError("The source must be an https address.")
    host = re.sub(r"^https://([^/]+).*$", r"\1", url).lower()
    if not any(host == h or host.endswith("." + h) for h in (x.lower() for x in p["official_hosts"])):
        raise ReviewError(f"{host} is not an official site for {cc}: {', '.join(p['official_hosts'])}.")


def _leaf(cc: str, path: str) -> dict[str, Any]:
    p = P.load(cc)
    node: Any = p["sections"] if p else None
    for k in path.split("."):
        node = node.get(k) if isinstance(node, dict) else None
    if not (isinstance(node, dict) and "status" in node):
        raise ReviewError(f"{cc} has no rule at {path}.")
    return node


def _norm(s: str) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s).strip().lower()


def _write(cc: str, path: str, entry: dict[str, Any]) -> None:
    d = P.review_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{cc}.json"
    cur = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"cc": cc, "rules": {}}
    cur.setdefault("rules", {})[path] = entry
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)
    P.load.cache_clear()
    P.load(cc)   # the merged pack must still validate


def _fetch(url: str) -> str:
    import httpx
    r = httpx.get(url, timeout=20, follow_redirects=True, headers={"User-Agent": "Hoola rule reader"})
    r.raise_for_status()
    return r.text


def read(cc: str, path: str, url: str, quote: str, actor: str = "owner", fetch: Callable[[str], str] | None = None,
         today: date | None = None) -> dict[str, Any]:
    cc = cc.upper()
    _host_ok(cc, url)
    _leaf(cc, path)
    q = _norm(quote)
    if len(q) < 12:
        raise ReviewError("Quote the official sentence that states the rule (at least a few words).")
    page = _norm((fetch or _fetch)(url))
    if q not in page:
        raise ReviewError("That sentence is not on the page, so the rule stays where it is.")
    t = today or date.today()
    _write(cc, path, {"status": "source_read", "source": url, "quote": quote.strip(), "checked_on": t.isoformat(),
                      "review_by": (t + timedelta(days=READ_DAYS)).isoformat()})
    EV.record("platform", "", actor, "pack", f"read {cc} {path}", {"url": url, "quote": quote})
    return {"cc": cc, "path": path, "status": "source_read", "review_by": (t + timedelta(days=READ_DAYS)).isoformat()}


def confirm(cc: str, path: str, checked_by: str, source: str, value: Any = None, quote: str = "", actor: str = "owner",
            today: date | None = None) -> dict[str, Any]:
    cc = cc.upper()
    if len(str(checked_by or "").strip()) < 3:
        raise ReviewError("checked_by: the name and role of the person who confirmed it.")
    _host_ok(cc, source)
    leaf = _leaf(cc, path)
    t = today or date.today()
    e = {"status": "checked", "source": source, "checked_by": str(checked_by).strip(), "checked_on": t.isoformat(),
         "review_by": (t + timedelta(days=CHECK_DAYS)).isoformat(), "quote": quote or leaf.get("quote", "")}
    if value is not None:
        e["value"] = value
    _write(cc, path, e)
    EV.record("platform", "", actor, "pack", f"confirm {cc} {path}", {"by": checked_by, "source": source, "value": value})
    return {"cc": cc, "path": path, "status": "checked", "review_by": e["review_by"]}


def todo(cc: str) -> list[dict[str, Any]]:
    v = P.view(cc)
    return [r for r in v.get("rows", []) if r["status"] != "checked"]
