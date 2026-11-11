"""v0.808 WAPAS (L7 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L7"): every version can come back, before launch too.

Until now a version kept only its BUILT files, so going back worked only for the live address (hosting.rollback). Now
every version also keeps its SOURCE - the section files (html / css / js of every section) and the site row's plan,
look (tokens + design kit) and facts - in `<site>/snaps/v<N>/` (small: JSON only; photos and media stay where they are
and are never deleted by a restore).

- restore(ver): the working copy goes back to that version's source and a NEW version is made from it ("Restored v3"),
  so History stays a straight line and the restore itself can be undone by restoring the version before it. What
  visitors sent (enquiries, orders, app rows) is DATA and is never touched - said every time.
- bookmark(ver, name): a name on a version she wants to find again (empty = removed).
- diff(ver, against): what changed in the code between two versions, file by file (readable code, unified diff).
- A version made before this release has no source kept: it says so plainly (it can still go on the live address
  from History if it was published)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..db import session
from . import build as B
from . import code as CD
from .models import Site, SiteVersion

KEEP = ("plan", "look", "facts", "styles", "style", "languages")
MAX_DIFF = 60_000


class WapasError(Exception):
    pass


def snap_dir(tenant: str, site_id: str, ver: int) -> Path:
    return B.site_dir(tenant, site_id) / "snaps" / f"v{int(ver)}"


def snapshot(r: Site, ver: int) -> None:
    """Called by service._make_version right after the version number is given."""
    d = snap_dir(r.tenant_id, r.id, ver)
    if d.exists():
        shutil.rmtree(d)
    (d / "sections").mkdir(parents=True)
    for f in (B.src_dir(r.tenant_id, r.id) / "sections").glob("*.json"):
        shutil.copy2(f, d / "sections" / f.name)
    (d / "meta.json").write_text(json.dumps({k: getattr(r, k, None) for k in KEEP}))


def has(tenant: str, site_id: str, ver: int) -> bool:
    return (snap_dir(tenant, site_id, ver) / "meta.json").exists()


def _site(tenant: str, ref: str) -> Site:
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    return r


def _sections_of(tenant: str, site_id: str, ver: int) -> dict[str, dict[str, Any]]:
    out = {}
    for f in sorted((snap_dir(tenant, site_id, ver) / "sections").glob("*.json")):
        try:
            out[f.stem] = json.loads(f.read_text())
        except ValueError:
            continue
    return out


def restore(tenant: str, ref: str, ver: int, note: str = "") -> dict[str, Any]:
    from . import service as S
    r = _site(tenant, ref)
    ver = int(ver)
    with session() as s:
        ok = s.scalars(select(SiteVersion).where(SiteVersion.site_id == r.id, SiteVersion.version == ver)).first()
    if not ok:
        raise WapasError(f"There is no v{ver}.")
    if not has(tenant, r.id, ver):
        raise WapasError(f"v{ver} was made before versions kept their source, so the site cannot be put back to it here. "
                         "If it was published, History > Put live can still show it on your address.")
    if S.busy(r.id) or r.status in ("building", "checking", "looks", "planned"):
        raise WapasError("The website is working on something; restore when it is ready.")
    if ver == int(r.version or 0):
        return {**S.view(r, False), "restored": False, "say": f"You are already on v{ver}."}
    d = snap_dir(tenant, r.id, ver)
    meta = json.loads((d / "meta.json").read_text())
    src = B.src_dir(tenant, r.id) / "sections"
    for f in src.glob("*.json"):
        f.unlink()
    for f in (d / "sections").glob("*.json"):
        shutil.copy2(f, src / f.name)
    fields = {k: meta[k] for k in KEEP if meta.get(k) is not None}      # stored as the row keeps them (JSON text)
    S._save(r.id, **fields)
    S._edits_path(r).write_text("[]")                         # the hand-edit Undo stack belonged to the other version
    S._after_edit(S._load(r.id), note or f"Restored v{ver}")
    return {**S.view(S._load(r.id), False), "restored": True, "from": ver,
            "say": f"Putting the site back to v{ver} - it becomes a new version you can undo from History. "
                   "Enquiries, orders and other data visitors sent are not touched."}


def bookmark(tenant: str, ref: str, ver: int, name: str) -> dict[str, Any]:
    r = _site(tenant, ref)
    name = " ".join(str(name or "").split())[:80]
    with session() as s:
        v = s.scalars(select(SiteVersion).where(SiteVersion.site_id == r.id, SiteVersion.version == int(ver))).first()
        if v is None:
            raise KeyError(ver)
        v.bookmark = name
    return {"version": int(ver), "bookmark": name, "say": f"Bookmarked v{ver}: {name}" if name else f"Bookmark removed from v{ver}."}


def diff(tenant: str, ref: str, ver: int, against: int | None = None) -> dict[str, Any]:
    r = _site(tenant, ref)
    ver = int(ver)
    if not has(tenant, r.id, ver):
        raise WapasError(f"v{ver} was made before versions kept their source; its changes cannot be listed.")
    if against is None:
        against = next((v for v in range(ver - 1, 0, -1) if has(tenant, r.id, v)), 0)
    against = int(against or 0)
    if against and not has(tenant, r.id, against):
        raise WapasError(f"v{against} was made before versions kept their source.")
    a = _sections_of(tenant, r.id, against) if against else {}
    b = _sections_of(tenant, r.id, ver)
    files, total = [], 0
    for key in sorted(set(a) | set(b)):
        for part in CD.PARTS:
            path = CD.path_of(key, part)
            x = CD.read(path, a, "")["code"] if key in a else ""
            y = CD.read(path, b, "")["code"] if key in b else ""
            if x == y:
                continue
            dtext = CD.diff(path, x, y)
            add = sum(1 for ln in dtext.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
            rem = sum(1 for ln in dtext.splitlines() if ln.startswith("-") and not ln.startswith("---"))
            total += len(dtext)
            files.append({"path": path, "added": add, "removed": rem, "state": "new" if not x else "removed" if not y else "changed",
                          "diff": dtext if total <= MAX_DIFF else ""})
    ka = json.loads(json.loads((snap_dir(tenant, r.id, against) / "meta.json").read_text()).get("look") or "{}") if against else {}
    kb = json.loads(json.loads((snap_dir(tenant, r.id, ver) / "meta.json").read_text()).get("look") or "{}")
    look = [k for k in ("bg", "surface", "ink", "primary", "accent", "radius", "head", "body")
            if (ka.get("tokens") or {}).get(k) != (kb.get("tokens") or {}).get(k)] if against else []
    return {"version": ver, "against": against, "files": files, "design_changed": look,
            "say": (f"{len(files)} file(s) changed from v{against} to v{ver}" if against else f"v{ver} is the first kept version")
            + (f"; design tokens changed: {', '.join(look)}" if look else "") + ("." if files or look else " - nothing in the code.")}
