"""v0.999.264 THE WORKFLOW LIBRARY: ready-made n8n workflows brought into Hoola Route.

Source: github.com/Zie619/n8n-workflows (MIT licence, added by its owner on 3 Nov 2025). Hoola reads it at ONE fixed
commit, f8639776 (28 Sep 2025): the commit right after it ("Add workflow fixer", 74bdcdc) rewrote every workflow and
dropped their connections, so newer copies have no steps joined to each other. The index (name, category, apps, start,
how much Hoola can do, sha256 of the file) is built once from that commit by tools/n8nlib_build.py and ships here; a
workflow file is fetched from GitHub only when she opens it, checked against its sha256, and kept on the server.

Before anything is shown or saved, keys written into a workflow are taken out (scrub): sign-in blocks, pinned test
data, and any value that looks like a token, key or password become {{env.NAME}} - she adds them under Variables.
The route lands switched OFF, through the same n8n importer as a pasted file (route/n8n.py).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

REPO = "Zie619/n8n-workflows"
COMMIT = "f8639776c97c05e9730c2ec5c97163d76f6d2290"
SOURCE = {"repo": REPO, "url": f"https://github.com/{REPO}", "commit": COMMIT, "commit_date": "2025-09-28",
          "licence": "MIT",
          "why_this_commit": "The next commit (a 'workflow fixer', 29 Sep 2025) rewrote every workflow and dropped how "
                             "their steps are joined; this is the last commit where they are whole."}
RAW = "https://raw.githubusercontent.com/{repo}/{commit}/workflows/{path}"
INDEX_FILE = Path(__file__).with_name("n8nlib_index.json.gz")
BYTES_MAX = 1_000_000
PER_MAX = 60

_INDEX: dict | None = None


class LibError(ValueError):
    pass


def index() -> dict:
    global _INDEX
    if _INDEX is None:
        try:
            _INDEX = json.loads(gzip.decompress(INDEX_FILE.read_bytes()).decode("utf-8"))
        except (OSError, ValueError):
            _INDEX = {"source": SOURCE, "items": []}
        _INDEX["by_id"] = {x["id"]: x for x in _INDEX.get("items") or []}
    return _INDEX


READY = {"ready": "Runs as it is", "check": "Runs - a few things to check", "partial": "Some steps to redo in Hoola"}


def _words(s: str) -> list[str]:
    return [w for w in re.split(r"[^\w]+", str(s or "").lower()) if w]


def search(q: str = "", category: str = "", app: str = "", trigger: str = "", ready: str = "", page: int = 1,
           per: int = 24) -> dict:
    ix = index()
    items = ix.get("items") or []
    words = _words(q)
    out = []
    for x in items:
        if category and x.get("c") != category:
            continue
        if app and app not in (x.get("a") or []):
            continue
        if trigger and x.get("t") != trigger:
            continue
        if ready == "ready" and x.get("r") != "ready":
            continue
        if ready == "runs" and x.get("r") not in ("ready", "check"):
            continue
        if words:
            hay = " ".join([x.get("n", ""), x.get("c", ""), " ".join(x.get("a") or []), x.get("d", "")]).lower()
            name = x.get("n", "").lower()
            if not all(w in hay for w in words):
                continue
            score = sum(3 if w in name else 1 for w in words)
        else:
            score = 0
        rank = {"ready": 0, "check": 1, "partial": 2}.get(x.get("r"), 3)
        out.append((-score, rank, -float(x.get("sh") or 0), x.get("n", ""), x))
    out.sort(key=lambda t: t[:4])
    per = max(1, min(int(per or 24), PER_MAX))
    page = max(1, int(page or 1))
    rows = [t[-1] for t in out]
    cats: dict[str, int] = {}
    apps: dict[str, int] = {}
    trig: dict[str, int] = {}
    readies = {"ready": 0, "check": 0, "partial": 0}
    for x in items:
        cats[x.get("c") or "Other"] = cats.get(x.get("c") or "Other", 0) + 1
        for a in x.get("a") or []:
            apps[a] = apps.get(a, 0) + 1
        trig[x.get("t") or ""] = trig.get(x.get("t") or "", 0) + 1
        readies[x.get("r")] = readies.get(x.get("r"), 0) + 1
    return {"items": [card(x) for x in rows[(page - 1) * per: page * per]], "total": len(rows), "page": page, "per": per,
            "all": len(items), "categories": sorted(([k, v] for k, v in cats.items()), key=lambda kv: -kv[1]),
            "apps": sorted(([k, v] for k, v in apps.items()), key=lambda kv: -kv[1])[:40],
            "triggers": sorted(([k, v] for k, v in trig.items() if k), key=lambda kv: -kv[1]),
            "ready_counts": readies, "source": ix.get("source") or SOURCE, "left_out": ix.get("left_out", 0)}


def card(x: dict) -> dict:
    return {"id": x["id"], "name": x.get("n", ""), "category": x.get("c", ""), "apps": x.get("a") or [],
            "trigger": x.get("t", ""), "nodes": x.get("k", 0), "ready": x.get("r", ""),
            "ready_text": READY.get(x.get("r", ""), ""), "converted": x.get("cv", 0), "to_redo": x.get("ph", 0),
            "description": x.get("d", ""), "file": x.get("p", "")}


def _cache_dir() -> Path:
    d = Path("data") / "n8nlib"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _download(url: str) -> bytes:
    import httpx
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "hoola-route-library"}) as c:
        r = c.get(url)
        if r.status_code != 200:
            raise LibError(f"GitHub answered {r.status_code} for this workflow - try again in a minute")
        data = r.content
    if len(data) > BYTES_MAX:
        raise LibError("This workflow file is too big (over 1 MB)")
    return data


def raw_of(wid: str) -> bytes:
    """The workflow file, byte for byte as it is at the fixed commit (checked against the index's sha256)."""
    x = index()["by_id"].get(str(wid or ""))
    if not x:
        raise LibError("That workflow is not in the library")
    path = _cache_dir() / (x["s"] + ".json")
    if path.exists():
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() == x["s"]:
            return data
    url = RAW.format(repo=REPO, commit=COMMIT, path=quote(x["p"], safe="/"))
    data = _download(url)
    if hashlib.sha256(data).hexdigest() != x["s"]:
        raise LibError("The file GitHub sent is not the one Hoola checked - it was not used")
    path.write_bytes(data)
    return data


# ---------------------------------------------------------------------------- taking keys out
_KEY_NAME = re.compile(r"(api[_-]?key|apikey|access[_-]?key|secret|token|password|passwd|bearer|authorization|"
                       r"private[_-]?key|client[_-]?secret|x-api-key)", re.I)
_SECRET_VAL = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|sk-ant-[A-Za-z0-9_-]{16,}|xox[abposr]-[A-Za-z0-9-]{10,}|"
                         r"gh[pousr]_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|\d{8,10}:[A-Za-z0-9_-]{30,}|"
                         r"(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{16,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,}|"
                         r"AKIA[0-9A-Z]{16}|re_[A-Za-z0-9]{20,}|SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,})")
_PLACEHOLDER = re.compile(r"^(<[^>]*>|\[[^\]]*\]|your[_ -].*|x{4,}.*|\*{3,}|changeme|replace.*|enter.*|\.\.\.)$", re.I)


def _env_name(node: str, key: str, used: set) -> str:
    base = re.sub(r"[^A-Z0-9]+", "_", f"{node}_{key}".upper()).strip("_")[:40] or "KEY"
    base = "N8N_" + base
    out, i = base, 2
    while out in used:
        out, i = f"{base}_{i}", i + 1
    used.add(out)
    return out


def scrub(doc: dict) -> tuple[dict, list[dict]]:
    """A copy of the workflow with sign-ins, pinned data and written-in keys taken out; and what was taken out."""
    doc = json.loads(json.dumps(doc))
    found: list[dict] = []
    used: set = set()
    for k in ("pinData", "staticData", "credentials"):
        doc.pop(k, None)

    def walk(v: Any, node: str, key: str, parent: Any = None) -> Any:
        if isinstance(v, dict):
            # a header / parameter row: {"name": "Authorization", "value": "Bearer ..."}
            if "name" in v and "value" in v and isinstance(v.get("value"), str) and _KEY_NAME.search(str(v["name"])):
                val = v["value"].strip()
                if val and not val.startswith("=") and not _PLACEHOLDER.match(val):
                    nm = _env_name(node, str(v["name"]), used)
                    found.append({"node": node, "field": str(v["name"]), "variable": nm})
                    v = {**v, "value": "={{ $env." + nm + " }}"}
            return {kk: walk(x, node, str(kk), v) for kk, x in v.items()}
        if isinstance(v, list):
            return [walk(x, node, key, v) for x in v]
        if isinstance(v, str):
            s = v.strip()
            if not s or s.startswith("={{ $env."):
                return v
            if _KEY_NAME.search(key) and not s.startswith("=") and not _PLACEHOLDER.match(s) and len(s) >= 6 \
                    and not isinstance(parent, list):
                nm = _env_name(node, key, used)
                found.append({"node": node, "field": key, "variable": nm})
                return "={{ $env." + nm + " }}"
            if _SECRET_VAL.search(s):
                nm = _env_name(node, key or "key", used)
                found.append({"node": node, "field": key, "variable": nm})
                return _SECRET_VAL.sub("{{ $env." + nm + " }}", v if v.startswith("=") else "=" + v)
        return v
    for n in doc.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        n.pop("credentials", None)
        n.pop("webhookId", None)
        if isinstance(n.get("parameters"), dict):
            n["parameters"] = walk(n["parameters"], str(n.get("name") or "step"), "")
    return doc, found


def load(wid: str) -> tuple[dict, list[dict], dict]:
    """(scrubbed workflow, what was taken out, its index row)."""
    from . import n8n as N
    data = raw_of(wid)
    try:
        doc = N.parse(data.decode("utf-8"))
    except (UnicodeDecodeError, N.N8nError) as e:
        raise LibError(f"This workflow could not be read ({e})")
    doc, found = scrub(doc)
    return doc, found, index()["by_id"][wid]


def _notes(plan: dict, found: list[dict], row: dict) -> dict:
    rep = plan.get("report") or {}
    if found:
        names = sorted({f["variable"] for f in found})
        rep.setdefault("notes", []).insert(0, "Keys written into this workflow were taken out. Add them under Variables: "
                                           + ", ".join(names[:12]) + ("" if len(names) <= 12 else f" and {len(names) - 12} more"))
    rep.setdefault("notes", []).append(f"From the n8n workflow library ({REPO}, MIT licence) - file {row['p']}")
    plan["report"] = rep
    plan["counts"] = {k: len(v) for k, v in rep.items()}
    return plan


def preview(wid: str) -> dict:
    """What the workflow becomes in Hoola - nothing is saved."""
    from . import n8n as N
    doc, found, row = load(wid)
    plan = _notes(N.convert(doc), found, row)
    plan["library"] = {**card(row), "source": SOURCE, "taken_out": found,
                       "github": f"https://github.com/{REPO}/blob/{COMMIT}/workflows/{quote(row['p'], safe='/')}"}
    return plan


def use(tenant: str, wid: str, new_name: str = "") -> dict:
    """Bring it in as a new route (switched off)."""
    from . import n8n as N
    doc, found, row = load(wid)
    out = _notes(N.bring_in(tenant, doc, new_name), found, row)
    out["taken_out"] = found
    out["source"] = {**SOURCE, "file": row["p"]}
    return out
