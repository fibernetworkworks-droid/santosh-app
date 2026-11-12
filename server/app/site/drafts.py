"""v0.837 DRAFT (L13 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L13", E6): try a big change without touching the site.

A DRAFT is a named copy of the site's working files (its section store, plan, look, facts) with its OWN preview address and
its own Hoola thread, made from the site's current version. She (or Hoola) changes it freely - the real site and anything
live never move. ACCEPT merges the draft back BY SECTION, as a three-way merge against the version the draft started from:
a section only the draft changed comes across; a section only the site changed stays; a section BOTH changed is a CONFLICT -
it is named, never merged silently, and she picks the site's or the draft's for each before anything is applied. The merge
becomes one new version of the site (undo from History like any restore).

Said plainly (differs from Lovable's shared data): a draft has its OWN data. Nothing visitors sent (enquiries, orders, app
rows, members) is copied into a draft and Accept never moves data either way. A draft is never published: it has no address
of its own on the internet; only its preview link (the same private kind the site has).
At most 3 open drafts per site. Discard deletes the draft's files; the site is untouched."""
from __future__ import annotations

import json
import secrets
import shutil
from typing import Any

from sqlalchemy import select

from ..db import session
from . import build as B
from . import wapas as WP
from .models import Site

MAX_OPEN = 3
META = ("plan", "look", "facts", "styles", "languages")
META_SAY = {"plan": "the page structure (pages and their sections)", "look": "the colours, fonts and design kit",
            "facts": "what Hoola knows about the business", "styles": "the offered looks", "languages": "the languages"}


class DraftError(Exception):
    def __init__(self, msg: str, code: int = 400, data: Any = None):
        super().__init__(msg)
        self.code, self.data = code, data


def _parent(tenant: str, ref: str) -> Site:
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    if r.draft_of:
        raise DraftError("This is already a draft; make drafts from the website itself.", 409)
    return r


def _drafts_of(parent_id: str) -> list[Site]:
    with session() as s:
        rows = s.scalars(select(Site).where(Site.draft_of == parent_id).order_by(Site.created_at)).all()
        for x in rows:
            s.expunge(x)
    return list(rows)


def _read_sections(tenant: str, site_id: str) -> dict[str, dict]:
    out = {}
    for f in sorted((B.src_dir(tenant, site_id) / "sections").glob("*.json")):
        try:
            out[f.stem] = json.loads(f.read_text())
        except ValueError:
            continue
    return out


def say_section(key: str) -> str:
    """'about__hero' -> 'About page · hero'."""
    page, _, typ = key.partition("__")
    return f"{page.replace('-', ' ').replace('_', ' ').capitalize() or 'Home'} page" + (f" · {typ.replace('_', ' ')}" if typ else "")


def create(tenant: str, ref: str, name: str) -> dict[str, Any]:
    from . import service as S
    r = _parent(tenant, ref)
    name = " ".join(str(name or "").split())[:60] or "Draft"
    if S.busy(r.id) or r.status in ("building", "checking", "looks", "planned"):
        raise DraftError("The website is working on something; start a draft when it is ready.", 409)
    if not r.version or not WP.has(tenant, r.id, int(r.version)):
        raise DraftError("A draft starts from a built version of the site that kept its source; build the site first (older versions did not keep it).", 409)
    open_ = [d for d in _drafts_of(r.id)]
    if len(open_) >= MAX_OPEN:
        raise DraftError(f"There are already {MAX_OPEN} drafts; accept or discard one first.", 409)
    if any((d.draft_name or "").lower() == name.lower() for d in open_):
        raise DraftError(f"A draft called '{name}' already exists.", 409)
    cols = ("name", "brief", "field", "goal", "style", "styles", "languages", "app", "facts", "answers", "plan", "looks", "look", "photos", "client", "staff")
    with session() as s:
        n = len(open_) + 1
        d = Site(tenant_id=tenant, number=f"{r.number}-D{n}", draft_of=r.id, draft_name=name, draft_base=int(r.version),
                 status="ready", stage="preview", version=0, preview_token=secrets.token_urlsafe(18), conv="",
                 **{c: getattr(r, c) for c in cols})
        s.add(d)
        s.flush()
        did = d.id
    src, dst = B.src_dir(tenant, r.id), B.src_dir(tenant, did)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    S._edits_path(S._load(did)).write_text("[]")
    S._after_edit(S._load(did), f"Draft '{name}' started from v{r.version}")
    return {**S.view(S._load(did), False), "say": f"Draft '{name}' started from v{r.version}. Change it freely - your website is not touched. "
            "It has its own data (nothing visitors sent is in it) and its own private preview link."}


def listing(tenant: str, ref: str) -> dict[str, Any]:
    from . import service as S
    r = _parent(tenant, ref)
    out = []
    for d in _drafts_of(r.id):
        plan = merge_plan(tenant, r, d)
        out.append({"id": d.id, "name": d.draft_name, "base": int(d.draft_base or 0), "version": d.version, "status": d.status,
                    "preview": S.preview_url(d), "changed": plan["changed"], "conflicts": plan["conflicts"],
                    "site_moved": int(r.version or 0) != int(d.draft_base or 0)})
    return {"drafts": out, "max": MAX_OPEN,
            "note": "A draft has its own data: nothing visitors sent is copied in, and Accept never moves data."}


def merge_plan(tenant: str, parent: Site, draft: Site) -> dict[str, Any]:
    """Three-way, by section (and by the design keys): base = the parent's snapshot at the version the draft started from."""
    base_v = int(draft.draft_base or 0)
    if not WP.has(tenant, parent.id, base_v):
        raise DraftError(f"The site's v{base_v} (where this draft started) no longer has its source, so the draft cannot be merged safely.", 409)
    base = WP._sections_of(tenant, parent.id, base_v)
    ours = _read_sections(tenant, parent.id)
    theirs = _read_sections(tenant, draft.id)
    take: dict[str, str] = {}              # key -> 'draft' (apply the draft's) | 'site' (leave)
    conflicts, changed = [], []
    for k in sorted(set(base) | set(ours) | set(theirs)):
        b, o, t = base.get(k), ours.get(k), theirs.get(k)
        if t == b:
            continue                       # the draft did not touch it
        changed.append({"item": k, "say": say_section(k), "what": "added" if b is None else "removed" if t is None else "changed"})
        if o == b or o == t:
            take[k] = "draft"
        else:
            conflicts.append({"item": k, "say": say_section(k), "kind": "section",
                              "site": "removed" if o is None else "changed", "draft": "removed" if t is None else "changed"})
    meta = json.loads((WP.snap_dir(tenant, parent.id, base_v) / "meta.json").read_text())
    for k in META:
        b, o, t = meta.get(k), getattr(parent, k, None), getattr(draft, k, None)
        if t == b or (t is None and b is None):
            continue
        changed.append({"item": "meta:" + k, "say": META_SAY[k].capitalize(), "what": "changed"})
        if o == b or o == t:
            take["meta:" + k] = "draft"
        else:
            conflicts.append({"item": "meta:" + k, "say": META_SAY[k].capitalize(), "kind": "design", "site": "changed", "draft": "changed"})
    return {"take": take, "conflicts": conflicts, "changed": changed}


def accept(tenant: str, ref: str, draft_id: str, resolutions: dict[str, str] | None = None, confirm: bool = False) -> dict[str, Any]:
    from . import service as S
    if not confirm:
        raise DraftError("Merging a draft into the website is your tap in the Studio (confirm).", 403)
    r = _parent(tenant, ref)
    d = next((x for x in _drafts_of(r.id) if x.id == draft_id), None)
    if d is None:
        raise DraftError("That draft is gone.", 404)
    if S.busy(r.id) or S.busy(d.id) or r.status in ("building", "checking", "looks", "planned"):
        raise DraftError("The website or the draft is working on something; accept when it is ready.", 409)
    plan = merge_plan(tenant, r, d)
    res = {str(k): str(v) for k, v in (resolutions or {}).items()}
    open_ = [c for c in plan["conflicts"] if res.get(c["item"]) not in ("site", "draft")]
    if open_:
        raise DraftError("Not merged - both the website and the draft changed: " + "; ".join(c["say"] for c in open_) +
                         ". Choose the website's or the draft's for each, then accept again.", 409, {"conflicts": plan["conflicts"]})
    take = dict(plan["take"])
    for c in plan["conflicts"]:
        take[c["item"]] = res[c["item"]]
    theirs = _read_sections(tenant, d.id)
    sec_dir = B.src_dir(tenant, r.id) / "sections"
    applied = []
    for k, who in take.items():
        if who != "draft":
            continue
        if k.startswith("meta:"):
            continue
        f = sec_dir / f"{k}.json"
        if k in theirs:
            f.write_text(json.dumps(theirs[k]))
        elif f.exists():
            f.unlink()
        applied.append(k)
    fields = {}
    for k in META:
        if take.get("meta:" + k) == "draft":
            fields[k] = getattr(d, k)
            applied.append("meta:" + k)
    if fields:
        S._save(r.id, **fields)
    S._edits_path(r).write_text("[]")
    name = d.draft_name
    S._after_edit(S._load(r.id), f"Merged draft '{name}'")
    shutil.rmtree(B.site_dir(tenant, d.id), ignore_errors=True)
    with session() as s:
        from .models import SiteVersion
        x = s.get(Site, d.id)
        if x:
            for v in s.scalars(select(SiteVersion).where(SiteVersion.site_id == d.id)).all():
                s.delete(v)
            s.delete(x)
    kept = [c["say"] for c in plan["conflicts"] if res.get(c["item"]) == "site"]
    return {**S.view(S._load(r.id), False), "merged": True, "applied": len(applied),
            "say": f"Draft '{name}' merged into the website as a new version ({len(applied)} part(s) came across"
                   + (f"; kept the website's own for: {', '.join(kept)}" if kept else "") + "). Undo it from History. No data was moved."}


def discard(tenant: str, ref: str, draft_id: str) -> dict[str, Any]:
    from . import service as S
    r = _parent(tenant, ref)
    d = next((x for x in _drafts_of(r.id) if x.id == draft_id), None)
    if d is None:
        raise DraftError("That draft is gone.", 404)
    if S.busy(d.id):
        raise DraftError("The draft is working on something; stop it first.", 409)
    shutil.rmtree(B.site_dir(tenant, d.id), ignore_errors=True)
    with session() as s:
        from .models import SiteVersion
        x = s.get(Site, d.id)
        if x:
            for v in s.scalars(select(SiteVersion).where(SiteVersion.site_id == d.id)).all():
                s.delete(v)
            s.delete(x)
    return {"ok": True, "say": f"Draft '{d.draft_name}' discarded. Your website was not touched."}
