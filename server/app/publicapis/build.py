"""Turn the public API lists into ONE Hoola catalog (v0.749 consolidated).

Sources (both MIT, credited in every find() answer):
  1. github.com/public-apis/public-apis - the README table (the v0.47 base; its ids never change, so remembered recipes
     and saved keys keep pointing at the same API)
  2. github.com/marcelscruz/public-apis - db/resources.json (the list behind publicapis.dev; newer, adds AI, Podcasts...)
An API from source 2 is ADDED only when source 1 does not already have it: same name (letters + digits only), or the
same host when that host belongs to the API itself (shared hosts like github.com / rapidapi.com do not count).

  python -m app.publicapis.build [README.md] [resources.json]       (no arguments: fetch both from GitHub)

Writes app/publicapis/catalog.json.gz: [{id, name, desc, cat, auth, https, cors, link, host, src}].
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

OUT = Path(__file__).with_name("catalog.json.gz")
SRC = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
SRC2 = "https://raw.githubusercontent.com/marcelscruz/public-apis/main/db/resources.json"
SOURCES = {"public-apis": "github.com/public-apis/public-apis (MIT)",
           "publicapis.dev": "github.com/marcelscruz/public-apis (MIT, publicapis.dev)"}
# hosts many different APIs live on: a match there says nothing about being the same API
SHARED_HOSTS = {"github.com", "gitlab.com", "rapidapi.com", "www.rapidapi.com", "docs.google.com", "sites.google.com",
                "www.postman.com", "documenter.getpostman.com", "app.swaggerhub.com", "bitbucket.org", "medium.com",
                "npmjs.com", "www.npmjs.com", "pypi.org", "readme.io", "gitbook.io", "notion.site", "www.notion.so",
                "developer.apple.com", "developers.google.com", "cloud.google.com", "learn.microsoft.com",
                "docs.microsoft.com", "aws.amazon.com", "api.data.gov", "data.gov", "www.data.gov", "apify.com",
                "huggingface.co", "vercel.app", "netlify.app", "herokuapp.com", "web.archive.org"}
_ROW = re.compile(r"^\|\s*\[(.+?)\]\((.+?)\)\s*\|(.*)$")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def parse(md: str) -> list[dict]:
    start = md.find("### Animals")
    md = md[start:] if start >= 0 else md
    cat, out, seen = None, [], set()
    for line in md.splitlines():
        if line.startswith("### "):
            cat = line[4:].strip()
            continue
        m = _ROW.match(line)
        if not (m and cat):
            continue
        cells = [c.strip().strip("`") for c in m.group(3).split("|")]
        if len(cells) < 4:
            continue
        name, link = m.group(1).strip(), m.group(2).strip()
        base = slug(f"{cat}-{name}")
        aid, n = base, 2
        while aid in seen:
            aid, n = f"{base}-{n}", n + 1
        seen.add(aid)
        auth = cells[1] if cells[1] not in ("", "No") else "none"
        out.append({"id": aid, "name": name, "desc": cells[0][:300], "cat": cat, "auth": auth,
                    "https": cells[2].lower() == "yes", "cors": cells[3].lower(), "link": link,
                    "host": (urlparse(link).hostname or "").lower()})
    return out


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def parse_dev(data: dict | list) -> list[dict]:
    """The publicapis.dev list (marcelscruz/public-apis db/resources.json): {count, entries:[{API, Description, Auth,
    Cors, Link, Category}]}. Ids are prefixed 'dev-' so they can never collide with a source-1 id."""
    items = data.get("entries", []) if isinstance(data, dict) else data
    out, seen = [], set()
    for x in items if isinstance(items, list) else []:
        if not isinstance(x, dict):
            continue
        name, link, cat = str(x.get("API") or "").strip(), str(x.get("Link") or "").strip(), str(x.get("Category") or "").strip()
        if not (name and cat and link.startswith(("http://", "https://"))):
            continue
        base = "dev-" + slug(f"{cat}-{name}")
        aid, n = base, 2
        while aid in seen:
            aid, n = f"{base}-{n}", n + 1
        seen.add(aid)
        auth = str(x.get("Auth") or "").strip().strip("`")
        out.append({"id": aid, "name": name[:120], "desc": str(x.get("Description") or "")[:300], "cat": cat,
                    "auth": auth if auth and auth.lower() != "no" else "none",
                    "https": link.startswith("https://"), "cors": str(x.get("Cors") or "unknown").lower(),
                    "link": link, "host": (urlparse(link).hostname or "").lower(), "src": "publicapis.dev"})
    return out


def merge(base: list[dict], extra: list[dict]) -> list[dict]:
    """Source 1 whole (ids untouched) + every source-2 API it does not already have (see the module note)."""
    names = {_key(r["name"]) for r in base}
    hosts = {r["host"] for r in base if r.get("host") and r["host"] not in SHARED_HOSTS}
    out = [{**r, "src": r.get("src") or "public-apis"} for r in base]
    for r in extra:
        k = _key(r["name"])
        if not k or k in names or (r["host"] and r["host"] not in SHARED_HOSTS and r["host"] in hosts):
            continue
        names.add(k)
        if r["host"] and r["host"] not in SHARED_HOSTS:
            hosts.add(r["host"])
        out.append(r)
    return out


def _current() -> list[dict]:
    try:
        return json.loads(gzip.decompress(OUT.read_bytes()))
    except (OSError, ValueError):
        return []


def keep_old(base: list[dict], old: list[dict]) -> list[dict]:
    """Rows of the catalog being replaced whose id the fresh source-1 parse no longer has (upstream renamed or removed
    the entry): kept as they were, so a key she saved or a recipe that worked still finds its API. A row whose NAME is
    back under a new id is not kept twice."""
    ids, by_name = {r["id"] for r in base}, {_key(r["name"]): r for r in base}
    kept = []
    for r in old:
        if r.get("src", "public-apis") != "public-apis" or r["id"] in ids:
            continue
        twin = by_name.get(_key(r["name"]))
        if twin is not None:                     # same API under a new id (e.g. moved category): the old id is an alias
            twin["aka"] = sorted(set(twin.get("aka", [])) | {r["id"]} | set(r.get("aka", [])))
        else:
            kept.append(r)
    return base + kept


def main(argv: list[str]) -> int:
    import httpx
    md = Path(argv[1]).read_text(encoding="utf-8") if len(argv) > 1 else httpx.get(SRC, timeout=60).text
    dev = (json.loads(Path(argv[2]).read_text(encoding="utf-8")) if len(argv) > 2
           else httpx.get(SRC2, timeout=60).json())
    base = parse(md)
    if len(base) < 500:
        print("too few rows in public-apis, not writing", len(base))
        return 1
    base = keep_old(base, _current())            # an API upstream renamed / dropped keeps its id (saved keys, recipes)
    extra = parse_dev(dev)
    if len(extra) < 500:
        print("too few rows in publicapis.dev, not writing", len(extra))
        return 1
    rows = merge(base, extra)
    OUT.write_bytes(gzip.compress(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()))
    print(f"{len(base)} public-apis + {len(rows) - len(base)} new from publicapis.dev = {len(rows)} APIs -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
