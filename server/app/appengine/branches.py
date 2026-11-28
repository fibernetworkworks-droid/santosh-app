"""v0.978 BRANCHES (the second half of L13 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO APP ENGINE BRANCHES AND E8").

A BRANCH is a named copy of an App Engine app to try something without touching the app:
- its OWN working files, its own preview link and its own PREVIEW data (Hoola Cloud keeps branch data apart; the app's
  preview and live data are never touched by a branch) - it never goes live (publish refuses a branch);
- at most MAX_OPEN open per app; a branch of a branch is refused (one level, like the website drafts);
- ACCEPT (her tap in the Studio, confirm) = a THREE-WAY merge BY FILE against the copy of the app taken when the branch started:
  a file only the branch changed comes in, a file only the app changed stays, a file BOTH changed is a NAMED conflict she
  settles (keep the app's / take the branch's) before anything is written. The same for the look (colours / fonts) and for
  Hoola Cloud: the branch's list changes are REPLAYED onto the app as one run (refused = nothing changes, said by name);
  a change that would lose data is never replayed - it waits on the app's own "I accept data loss" card. Packages the branch
  added come in. Then the app rebuilds once (one new version) and the branch is removed;
- the agent may start and list branches; accepting is never the tool's (her tap only).
"""
from __future__ import annotations

import hashlib
import json
import secrets
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..db import session
from . import rules as RL
from . import service as AE
from .models import AppProject, ensure_table

MAX_OPEN = 3
META = "branch.json"
BASE = "base_src"


class BranchError(AE.AppEngineError):
    pass


def _meta_path(b: AppProject) -> Path:
    return AE.pdir(b.tenant_id, b.id) / META


def _meta(b: AppProject) -> dict[str, Any]:
    try:
        return json.loads(_meta_path(b).read_text())
    except (OSError, ValueError):
        return {}


def _base_dir(b: AppProject) -> Path:
    return AE.pdir(b.tenant_id, b.id) / BASE


def open_of(r: AppProject) -> list[AppProject]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(AppProject).where(AppProject.tenant_id == r.tenant_id, AppProject.branch_of == r.id)
                         .order_by(AppProject.created_at)).all()
        for x in rows:
            s.expunge(x)
    return list(rows)


def _parent(b: AppProject) -> AppProject:
    if not b.branch_of:
        raise BranchError(f"App {b.number} is not a branch.", 400)
    return AE._load(b.tenant_id, b.branch_of)


def _branch(tenant: str, ref: str, bref: str) -> tuple[AppProject, AppProject]:
    p = AE._load(tenant, ref)
    if p.branch_of:
        p = AE._load(tenant, p.branch_of)
    for b in open_of(p):
        if b.id == bref or b.slug == bref:
            return p, b
    raise BranchError(f"There is no open branch '{bref}' of app {p.number}.", 404)


def _copy_src(src: Path, dst: Path) -> None:
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("node_modules", "dist"))


def _deps_of(d: Path) -> dict[str, str]:
    try:
        return dict((json.loads((d / "package.json").read_text()).get("dependencies") or {}))
    except (OSError, ValueError):
        return {}


# ------------------------------------------------------------------ start / list / discard
def create(tenant: str, ref: str, name: str = "") -> dict[str, Any]:
    from . import cloud as CL
    p = AE._load(tenant, ref)
    if p.branch_of:
        raise BranchError("This is already a branch; start a branch from the app itself.", 409)
    have = open_of(p)
    if len(have) >= MAX_OPEN:
        raise BranchError(f"App {p.number} already has {MAX_OPEN} open branches (" + ", ".join(b.branch_name or b.id for b in have)
                          + "); accept or discard one first.", 409)
    name = " ".join(str(name or "").split())[:60] or f"Branch {len(have) + 1}"
    if any((b.branch_name or "").lower() == name.lower() for b in have):
        raise BranchError(f"There is already a branch called '{name}'.", 409)
    with session() as s:
        slug = f"{p.slug[:30]}-b{secrets.token_hex(3)}"
        b = AppProject(tenant_id=tenant, number=0, name=f"{p.name} · {name}"[:120], slug=slug, brief=p.brief or "",
                       status="ready" if p.version else "new", look=p.look or "{}", preview_token=secrets.token_urlsafe(24),
                       conversation_id="", branch_of=p.id, branch_name=name, branch_base=int(p.version or 0), dirty=True)
        s.add(b)
        s.flush()
        s.expunge(b)
    with AE._lock(p.id):
        _copy_src(AE.src_dir(p), AE.src_dir(b))
        _copy_src(AE.src_dir(p), _base_dir(b))                 # the app as it was: the merge's common ancestor
        pc = AE.pdir(p.tenant_id, p.id) / "cloud"
        bc = AE.pdir(b.tenant_id, b.id) / "cloud"
        bc.mkdir(parents=True, exist_ok=True)
        for f in ("schema.json", "migrations.json"):
            if (pc / f).exists():
                shutil.copy2(pc / f, bc / f)
        from . import herlocks as HL
        HL.copy_to(p, b)                                       # v0.999.322 her locks come along
        sch = CL.schema(p)
        _meta_path(b).write_text(json.dumps({"base_version": int(p.version or 0), "base_schema": int(sch.get("version") or 0),
                                             "base_look": p.look or "{}", "base_deps": _deps_of(AE.src_dir(p))}))
    seeded = 0
    for lst in CL.schema(b).get("lists") or []:                    # its own preview data: marked samples, never the app's rows
        if not lst.get("hidden"):
            try:
                seeded += CL.seed(b, lst["key"])
            except Exception:                                        # noqa: BLE001 - a sample row is a nicety
                pass
    AE.schedule_build(tenant, b.id)
    return {**view(b), "say": f"Branch '{name}' of app {p.number} started from version {p.version or 0}. It has its own preview"
            + (f" and its own preview data ({seeded} sample rows)" if seeded else "")
            + "; the app and its data are not touched. It never goes live: accept it into the app when you like it."}


def view(b: AppProject) -> dict[str, Any]:
    v = AE.view(AE._load(b.tenant_id, b.id), False)
    return {**v, "branch": {"id": b.id, "name": b.branch_name or "", "of": b.branch_of, "base_version": int(b.branch_base or 0)}}


def listing(tenant: str, ref: str) -> dict[str, Any]:
    p = AE._load(tenant, ref)
    if p.branch_of:
        p = AE._load(tenant, p.branch_of)
    out = []
    for b in open_of(p):
        pl = merge_plan(p, b)
        out.append({**view(b), "changes": pl["counts"], "conflicts": len(pl["conflicts"])})
    return {"app": p.id, "number": p.number, "branches": out, "max": MAX_OPEN}


def discard(tenant: str, ref: str, bref: str, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        raise BranchError("Discarding a branch is your tap in the Studio (confirm).", 403)
    p, b = _branch(tenant, ref, bref)
    AE.delete_app(tenant, b.id)                                     # its files, its preview data, its row
    return {"ok": True, "say": f"Branch '{b.branch_name}' discarded; app {p.number} is as it was."}


# ------------------------------------------------------------------ the merge
def _tree(d: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    if not d.exists():
        return out
    for f in sorted(d.rglob("*")):
        if not f.is_file() or "node_modules" in f.parts:
            continue
        rel = f.relative_to(d).as_posix()
        if rel.startswith("dist/"):
            continue
        try:
            RL.writable(rel)                                          # only HER app's files merge; Hoola's tooling is refreshed
        except RL.RuleError:
            continue
        out[rel] = f.read_bytes()
    return out


def _h(b: bytes | None) -> str | None:
    return None if b is None else hashlib.sha1(b).hexdigest()


def _look(raw: str | None) -> str:
    try:
        return json.dumps(json.loads(raw or "{}"), sort_keys=True)
    except ValueError:
        return "{}"


def _say_file(rel: str) -> str:
    return rel


def merge_plan(p: AppProject, b: AppProject) -> dict[str, Any]:
    """What accepting would do. Nothing is written."""
    from . import cloud as CL
    meta = _meta(b)
    base, ours, theirs = _tree(_base_dir(b)), _tree(AE.src_dir(p)), _tree(AE.src_dir(b))
    incoming, stays, conflicts = [], [], []
    for rel in sorted(set(base) | set(ours) | set(theirs)):
        hb, ho, ht = _h(base.get(rel)), _h(ours.get(rel)), _h(theirs.get(rel))
        if ho == ht or ht == hb:
            if ho != hb:
                stays.append({"id": "file:" + rel, "what": _say_file(rel), "how": "the app changed it"})
            continue
        how = "new in the branch" if hb is None else ("deleted in the branch" if ht is None else "changed in the branch")
        if ho == hb:
            incoming.append({"id": "file:" + rel, "what": _say_file(rel), "how": how, "path": rel,
                             "delete": ht is None})
        else:
            app_how = "deleted in the app" if ho is None else ("new in the app" if hb is None else "changed in the app")
            conflicts.append({"id": "file:" + rel, "what": _say_file(rel), "path": rel, "branch": how, "app": app_how,
                              "delete": ht is None})
    # the look (colours / corners / fonts)
    bl, pl, tl = _look(meta.get("base_look")), _look(p.look), _look(b.look)
    if tl != bl and pl != bl and tl != pl:
        conflicts.append({"id": "look", "what": "The look (colours, corners, fonts)", "branch": "changed in the branch",
                          "app": "changed in the app"})
    elif tl != bl and tl != pl:
        incoming.append({"id": "look", "what": "The look (colours, corners, fonts)", "how": "changed in the branch"})
    # packages the branch added (vetted; package.json itself is Hoola's)
    base_deps = meta.get("base_deps") or {}
    added = sorted(set(_deps_of(AE.src_dir(b))) - set(base_deps) - set(_deps_of(AE.src_dir(p))))
    if added:
        incoming.append({"id": "packages", "what": "Packages", "how": "added in the branch: " + ", ".join(added), "packages": added})
    # Hoola Cloud: the branch's list changes since it started, replayed onto the app
    n0 = int(meta.get("base_schema") or 0)
    bm = [m for m in CL.migrations(b) if int(m.get("n") or 0) > n0]
    pm = [m for m in CL.migrations(p) if int(m.get("n") or 0) > n0]
    cloud = {"branch_changes": sum(len(m.get("changes") or []) for m in bm if not m.get("destructive")),
             "data_loss": sum(len(m.get("changes") or []) for m in bm if m.get("destructive")),
             "app_changes": sum(len(m.get("changes") or []) for m in pm)}
    if cloud["branch_changes"] or cloud["data_loss"]:
        item = {"id": "cloud", "what": "Hoola Cloud lists",
                "how": f"{cloud['branch_changes']} list change(s) from the branch are replayed onto the app as one run"
                       + (f"; {cloud['data_loss']} change(s) that lose data wait on the app's own 'I accept data loss' card"
                          if cloud["data_loss"] else "")}
        if cloud["app_changes"] and cloud["branch_changes"]:
            conflicts.append({**item, "branch": "changed in the branch", "app": f"{cloud['app_changes']} change(s) in the app since"})
        else:
            incoming.append(item)
    behind = int(p.version or 0) - int(meta.get("base_version") or 0)
    return {"incoming": incoming, "stays": stays, "conflicts": conflicts, "cloud": cloud,
            "counts": {"incoming": len(incoming), "stays": len(stays), "conflicts": len(conflicts)},
            "base_version": int(meta.get("base_version") or 0), "app_version": int(p.version or 0), "behind": max(0, behind),
            "say": _say_plan(incoming, conflicts, b)}


def _say_plan(incoming: list, conflicts: list, b: AppProject) -> str:
    if not incoming and not conflicts:
        return f"Branch '{b.branch_name}' has nothing the app does not already have."
    s = f"Accepting '{b.branch_name}' brings in {len(incoming)} change(s)."
    if conflicts:
        s += (f" {len(conflicts)} part(s) changed in BOTH the app and the branch: " + "; ".join(c["what"] for c in conflicts[:6])
              + ". Choose for each: keep the app's or take the branch's.")
    return s


def compare(tenant: str, ref: str, bref: str) -> dict[str, Any]:
    p, b = _branch(tenant, ref, bref)
    return {**merge_plan(p, b), "branch": view(b)}


def accept(tenant: str, ref: str, bref: str, resolutions: dict[str, str] | None = None, confirm: bool = False) -> dict[str, Any]:
    """Only from HER tap in the Studio. A conflict not settled = nothing changes."""
    from . import cloud as CL
    if not confirm:
        raise BranchError("Accepting a branch is your tap in the Studio (confirm).", 403)
    p, b = _branch(tenant, ref, bref)
    res = {str(k): str(v) for k, v in (resolutions or {}).items()}
    plan = merge_plan(p, b)
    open_ = [c for c in plan["conflicts"] if res.get(c["id"]) not in ("site", "branch")]
    if open_:
        raise BranchError("Not accepted - settle these first (keep the app's or take the branch's): "
                          + "; ".join(c["what"] for c in open_), 409, [{"conflict": c["id"], "what": c["what"]} for c in open_])
    take = list(plan["incoming"]) + [c for c in plan["conflicts"] if res.get(c["id"]) == "branch"]
    files = [x for x in take if x["id"].startswith("file:")]
    # 1. check every incoming file first (the app's rules), so nothing is half done
    deps = set(_deps_of(AE.src_dir(p))) | set(_deps_of(AE.src_dir(b)))
    from . import image as IMG
    deps |= set(IMG.DEV)
    writes, deletes, kept = {}, [], []
    for x in files:
        rel = x["path"]
        if x.get("delete"):
            if rel in ("src/App.tsx", "index.html"):
                kept.append(rel)
            else:
                deletes.append(rel)
            continue
        text = (AE.src_dir(b) / rel).read_text("utf-8")
        probs = RL.check_file(rel, text, deps) if RL.ext(rel) in RL.TEXT_EXT else []
        if probs:
            raise BranchError(f"Not accepted - {rel} in the branch breaks the app's rules: " + RL.say(probs, 2), 422, probs)
        writes[rel] = text
    # 2. Hoola Cloud first: one run, refused = nothing at all changes
    notes = []
    cloud_item = next((x for x in take if x["id"] == "cloud"), None)
    if cloud_item:
        n0 = int(_meta(b).get("base_schema") or 0)
        mig = [m for m in CL.migrations(b) if int(m.get("n") or 0) > n0]
        changes = [c for m in mig if not m.get("destructive") for c in (m.get("changes") or [])]
        loss = [c for m in mig if m.get("destructive") for c in (m.get("changes") or [])]
        if changes:
            try:
                CL.apply_changes(p, changes, by=f"branch {b.branch_name}")
            except CL.CloudError as e:
                raise BranchError("Not accepted - the branch's Hoola Cloud list changes do not fit the app any more: "
                                  + str(e) + ". Keep the app's lists (choose 'keep the app's' for Hoola Cloud lists) or "
                                  "change the branch.", 409, [{"conflict": "cloud", "what": "Hoola Cloud lists"}])
        if loss:
            CL.queue_pending(p, loss)
            notes.append(f"{len(loss)} list change(s) that lose data wait on the app's 'I accept data loss' card (Cloud tab)")
    # 3. the look and the packages
    if any(x["id"] == "look" for x in take):
        try:
            lk = json.loads(b.look or "{}")
        except ValueError:
            lk = {}
        AE.set_tokens(tenant, p.id, values=lk.get("values") or {}, palette=lk.get("palette") or "")
    for x in take:
        for pkg in x.get("packages") or []:
            AE.add_dependency(tenant, p.id, pkg)
    # 4. the files, under the app's lock
    with AE._lock(p.id):
        for rel, text in writes.items():
            AE._write(p, rel, text)
        for rel in deletes:
            f = AE.src_dir(p) / rel
            if f.exists():
                f.unlink()
        AE._save(p.id, dirty=True)
    AE.schedule_build(tenant, p.id)
    AE.delete_app(tenant, b.id)
    if kept:
        notes.append("kept " + ", ".join(kept) + " (the app's entry is never deleted)")
    took = len(take)
    return {**AE.view(AE._load(tenant, p.id), False), "accepted": True, "brought_in": took,
            "files_written": sorted(writes), "files_deleted": sorted(deletes),
            "say": f"Branch '{b.branch_name}' accepted into app {p.number}: {took} change(s) came in"
                   + (", " + "; ".join(notes) if notes else "") + ". The app is rebuilding as one new version; the branch is gone."}


def prompt_line(b: AppProject) -> str:
    if not b.branch_of:
        return ""
    return (f"This app is a BRANCH ('{b.branch_name}') of another app: change it freely - nothing reaches the app until she taps "
            "Accept in the Studio, and a branch never goes live.")
