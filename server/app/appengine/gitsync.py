"""v0.839 GITHUB DO TARAF (L14 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L14"): an App Engine app and ONE branch of a GitHub
repository, in both directions - plus bringing in a project from a ZIP or from another builder's repository.

- LINK (her tap): the repo (made private if missing, with her fine-grained token typed only in the app - the same sealed
  token the website export uses) and its branch (the default branch; one branch only).
- PUSH (her tap): one commit with the whole project (fast-forward only - never forced). Refused while the repository has
  commits she has not pulled ("pull first"). Files nobody changed are not uploaded again.
- PULL (her tap): a THREE-WAY merge by file against the commit last synced: a file only GitHub changed comes across; a file only
  the app changed stays; a file BOTH changed is a named conflict she settles (the app's or GitHub's) before anything applies.
  Every incoming file goes through the SAME laws as a write by Hoola (paths, safety, design drift, vetted imports): a pull is
  all-or-nothing and names file:line + token for the first problems. Files Hoola keeps locked (package.json, vite config,
  the tokens and Cloud files ...) and files that are not text are never overwritten; they are listed, kept apart, and the push
  keeps GitHub's own copy of them.
- IMPORT: a new app from a ZIP (this app's own export, a GitHub "Download ZIP", another builder's export) or from a GitHub
  repository. Here a file that breaks the laws is NOT brought in and is listed with the reason (a foreign project rarely obeys
  the design tokens) - the rest is, and Hoola can be asked to fix the listed ones.
- NEVER synced: her data and Cloud rules (server-side, `cloud/`), her visitors' rows, secrets (a file with one is refused),
  node_modules, dist, hidden files. Not built: several branches, pull requests, webhooks (pulling is her tap)."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import zipfile
from typing import Any

from ..db import now
from ..site import github as GH
from . import rules as RL
from . import service as AE

MAX_FILES_SYNC, MAX_BYTES_SYNC = 600, 8 * 1024 * 1024
ZIP_MAX, ZIP_UNPACKED, ZIP_ENTRIES = 8 * 1024 * 1024, 16 * 1024 * 1024, 1500


class SyncError(Exception):
    def __init__(self, msg: str, code: int = 400, data: Any = None):
        super().__init__(msg)
        self.code, self.data = code, data


def blob_sha(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def _cfg_path(r):
    return AE.pdir(r.tenant_id, r.id) / "github.json"


def config(r) -> dict[str, Any]:
    try:
        return json.loads(_cfg_path(r).read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cfg(r, c: dict[str, Any]) -> None:
    _cfg_path(r).parent.mkdir(parents=True, exist_ok=True)
    _cfg_path(r).write_text(json.dumps(c, ensure_ascii=False))


def _gh(tenant: str) -> GH.Gh:
    try:
        return GH.Gh(GH._token(tenant))
    except GH.GithubError as e:
        raise SyncError(str(e))


def _call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except GH.GithubError as e:
        raise SyncError(str(e), 502)


def _syncable(rel: str) -> bool:
    parts = rel.split("/")
    return not (any(x.startswith(".") for x in parts) or "node_modules" in parts or parts[0] == "dist")


def local_files(r) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for p in AE._files(r):
        rel = AE._rel(r, p)
        if _syncable(rel):
            out[rel] = p.read_bytes()
    return out


def _secret_in(text: str) -> str:
    from . import saboot as SB
    for rx, what in SB.SECRETS:
        if rx.search(text):
            return what
    return ""


# ------------------------------------------------------------------ status (local only, no network)
def status(r) -> dict[str, Any]:
    c = config(r)
    if not c.get("repo"):
        return {"linked": False, "say": "Not linked to a GitHub repository."}
    man = c.get("manifest") or {}
    ign = c.get("ignored") or {}
    now_ = {k: blob_sha(v) for k, v in local_files(r).items()}
    changes = [{"path": k, "what": "added" if k not in man else "changed"} for k, s in sorted(now_.items()) if man.get(k) != s and k not in ign]
    changes += [{"path": k, "what": "removed"} for k in sorted(man) if k not in now_ and k not in ign and k.lower() != "readme.md"]
    return {"linked": True, "repo": f"{c['owner']}/{c['repo']}", "branch": c.get("branch", ""), "private": c.get("private", True),
            "head": (c.get("head") or "")[:10], "synced_at": c.get("at", ""), "changes": changes[:200], "changed": len(changes),
            "kept_apart": sorted(ign)[:50],
            "url": f"https://github.com/{c['owner']}/{c['repo']}",
            "say": (f"{len(changes)} change(s) not pushed yet." if changes else "Everything here is on GitHub as of the last sync.")}


# ------------------------------------------------------------------ link / unlink
def link(tenant: str, ref: str, repo: str, private: bool = True, confirm: bool = False, create: bool = True) -> dict[str, Any]:
    if not confirm:
        raise SyncError("Linking to GitHub is your tap in the Studio (confirm).", 403)
    r = AE._load(tenant, ref)
    gh = _gh(tenant)
    me = _call(gh.me)
    name = str(repo or "").strip()
    owner = str(me.get("login") or "")
    if "/" in name:
        owner, name = name.split("/", 1)
    name = re.sub(r"[^A-Za-z0-9._-]", "-", name)[:90].strip("-.")
    if not name:
        raise SyncError("Give the repository a name, e.g. my-shop-app.")
    info = _call(gh.req, "GET", f"/repos/{owner}/{name}", None, True)
    created = False
    if info is None:
        if not create or owner != me.get("login"):
            raise SyncError(f"The repository {owner}/{name} was not found.", 404)
        info = _call(gh.req, "POST", "/user/repos", {"name": name, "private": bool(private), "auto_init": True,
                                                         "description": "App made with Hoola"})
        created = True
    branch = info.get("default_branch") or "main"
    cfg = {"owner": owner, "repo": name, "branch": branch, "private": bool(info.get("private", private)), "head": "", "manifest": {},
           "ignored": {}, "at": now().isoformat(), "created": created}
    if created:                         # the fresh repository holds only its own first commit: nothing to pull
        ref_ = _call(gh.req, "GET", f"/repos/{owner}/{name}/git/ref/heads/{branch}", None, True)
        cfg["head"] = ((ref_ or {}).get("object") or {}).get("sha", "")
        cfg["fresh"] = True
    _save_cfg(r, cfg)
    return {**status(r), "created": created,
            "say": (f"Linked to {owner}/{name} (new, {'private' if cfg['private'] else 'PUBLIC'}). Push when you are ready." if created
                    else f"Linked to the existing {owner}/{name} ({branch}). Pull first to bring its files in.")}


def unlink(tenant: str, ref: str) -> dict[str, Any]:
    r = AE._load(tenant, ref)
    _cfg_path(r).unlink(missing_ok=True)
    return {"linked": False, "say": "Unlinked. Nothing on GitHub or in the app was changed."}


# ------------------------------------------------------------------ remote reads
def _remote(gh: GH.Gh, c: dict[str, Any]) -> tuple[str, dict[str, str]]:
    """(head commit sha, {path: blob sha} of the branch's files)."""
    o, n, b = c["owner"], c["repo"], c["branch"]
    ref = _call(gh.req, "GET", f"/repos/{o}/{n}/git/ref/heads/{b}", None, True)
    head = ((ref or {}).get("object") or {}).get("sha", "")
    if not head:
        return "", {}
    com = _call(gh.req, "GET", f"/repos/{o}/{n}/git/commits/{head}")
    tree = _call(gh.req, "GET", f"/repos/{o}/{n}/git/trees/{com['tree']['sha']}?recursive=1")
    if tree.get("truncated"):
        raise SyncError("The repository is too large to read in one go (over 100,000 files); use a smaller repository.")
    return head, {e["path"]: e["sha"] for e in tree.get("tree", []) if e.get("type") == "blob"}


def _blob(gh: GH.Gh, c: dict[str, Any], sha: str) -> bytes:
    d = _call(gh.req, "GET", f"/repos/{c['owner']}/{c['repo']}/git/blobs/{sha}")
    return base64.b64decode(d.get("content", "")) if d.get("encoding") == "base64" else str(d.get("content", "")).encode()


def _why_not(r, rel: str, sha_size: int | None = None) -> str:
    """'' if a pulled file may be written, else the reason it is kept apart."""
    try:
        RL.writable(rel)
    except RL.RuleError as e:
        return str(e)
    return ""


# ------------------------------------------------------------------ the plan (what a pull would do)
def plan(r, c: dict[str, Any], remote: dict[str, str], adopt: bool = False) -> dict[str, Any]:
    base = {} if adopt else (c.get("manifest") or {})
    ign = c.get("ignored") or {}
    local = {k: blob_sha(v) for k, v in local_files(r).items()}
    take, delete, conflicts, keep_apart, same = {}, [], [], {}, 0
    for path in sorted(set(remote) | set(base) | set(local)):
        b, rs, ls = base.get(path), remote.get(path), local.get(path)
        if path.lower() == "readme.md" and ls is None:
            continue                                             # the repository's README is GitHub's own; the app has none
        if rs == b:
            continue                                             # GitHub did not touch it
        if rs is not None and ign.get(path) == rs:
            continue                                             # kept apart already, unchanged
        if ls == rs:
            same += 1
            continue
        why = _why_not(r, path)
        if not why and rs is not None and RL.ext(path) not in RL.TEXT_EXT:
            why = "not a text file"
        if why:
            if rs is not None:
                keep_apart[path] = {"sha": rs, "why": why}
            continue
        local_changed = (ls != b) and not adopt
        if local_changed:
            conflicts.append({"item": path, "say": path, "site": "removed" if ls is None else "changed",
                              "github": "removed" if rs is None else "changed"})
        elif rs is None:
            delete.append(path)
        else:
            take[path] = rs
    return {"take": take, "delete": delete, "conflicts": conflicts, "kept_apart": keep_apart, "already_same": same,
            "changed": [{"item": p, "say": p, "what": "added" if p not in local else "changed"} for p in take]
                       + [{"item": p, "say": p, "what": "removed"} for p in delete]}


def compare(tenant: str, ref: str) -> dict[str, Any]:
    r = AE._load(tenant, ref)
    c = config(r)
    if not c.get("repo"):
        raise SyncError("Not linked to a GitHub repository.", 409)
    head, remote = _remote(_gh(tenant), c)
    pl = plan(r, c, remote)
    return {"remote_moved": head != c.get("head", ""), "changed": pl["changed"], "conflicts": pl["conflicts"],
            "kept_apart": {k: v["why"] for k, v in pl["kept_apart"].items()}, "local": status(r)["changes"][:100]}


# ------------------------------------------------------------------ writing incoming files (same laws as a write by Hoola)
def apply_files(r, files: dict[str, bytes], strict: bool) -> dict[str, Any]:
    """Write incoming files. strict = all or nothing (a pull); else the passing ones are written and the rest listed (an import)."""
    ok, refused = {}, []
    deps = AE._deps(r)
    for rel, raw in files.items():
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            refused.append({"file": rel, "why": "not a text file"})
            continue
        if not text.endswith("\n"):
            text += "\n"
        if len(text.encode("utf-8")) > RL.MAX_FILE:
            refused.append({"file": rel, "why": f"over {RL.MAX_FILE // 1000} KB"})
            continue
        sec = _secret_in(text)
        if sec:
            refused.append({"file": rel, "why": f"contains {sec}; secrets are never brought into an app"})
            continue
        probs = RL.check_file(rel, text, deps)
        if probs:
            refused.append({"file": rel, "why": RL.say(probs, 2)})
            continue
        ok[rel] = text
    if strict and refused:
        raise SyncError("Not pulled - these incoming files break the app's rules (nothing was changed): "
                        + "; ".join(f"{x['file']}: {x['why']}" for x in refused[:5])
                        + (f" ... and {len(refused) - 5} more" if len(refused) > 5 else ""), 422, {"refused": refused})
    if len(AE._files(r)) + sum(1 for k in ok if not (AE.src_dir(r) / k).exists()) > RL.MAX_FILES:
        raise SyncError(f"That would take the app over {RL.MAX_FILES} files.", 422)
    with AE._lock(r.id):
        for rel, text in ok.items():
            AE._write(r, rel, text)
    return {"written": sorted(ok), "refused": refused}


# ------------------------------------------------------------------ pull / push
def pull(tenant: str, ref: str, resolutions: dict[str, str] | None = None, confirm: bool = False, adopt: bool = False) -> dict[str, Any]:
    if not confirm:
        raise SyncError("Pulling from GitHub is your tap in the Studio (confirm).", 403)
    r = AE._load(tenant, ref)
    c = config(r)
    if not c.get("repo"):
        raise SyncError("Not linked to a GitHub repository.", 409)
    gh = _gh(tenant)
    head, remote = _remote(gh, c)
    pl = plan(r, c, remote, adopt=adopt)
    res = {str(k): str(v) for k, v in (resolutions or {}).items()}
    open_ = [x for x in pl["conflicts"] if res.get(x["item"]) not in ("site", "github")]
    if open_:
        raise SyncError("Not pulled - both the app and GitHub changed: " + "; ".join(x["say"] for x in open_) +
                        ". Choose the app's or GitHub's for each, then pull again.", 409, {"conflicts": pl["conflicts"]})
    take = dict(pl["take"])
    delete = list(pl["delete"])
    for x in pl["conflicts"]:
        if res[x["item"]] == "github":
            if remote.get(x["item"]) is None:
                delete.append(x["item"])
            else:
                take[x["item"]] = remote[x["item"]]
    files = {p: _blob(gh, c, sha) for p, sha in take.items()}
    out = apply_files(r, files, strict=not adopt)
    with AE._lock(r.id):
        for p in delete:
            f = AE._path_in(r, p)
            if f.exists():
                f.unlink()
                AE._save(r.id, dirty=True)
                AE.schedule_build(r.tenant_id, r.id)
    ign = {p: v["sha"] for p, v in pl["kept_apart"].items()}
    for x in out["refused"]:
        if x["file"] in remote:
            ign[x["file"]] = remote[x["file"]]
    for p, s in (c.get("ignored") or {}).items():          # still kept apart while GitHub's copy is the same
        if remote.get(p) == s:
            ign[p] = s
    c.update(head=head, manifest=dict(remote), ignored=ign, at=now().isoformat(), fresh=False)
    _save_cfg(r, c)
    kept = [x["say"] for x in pl["conflicts"] if res.get(x["item"]) == "site"]
    n = len(out["written"]) + len(delete)
    return {**status(r), "pulled": True, "written": out["written"], "removed": delete, "refused": out["refused"],
            "kept_apart_count": len(ign),
            "say": (f"Pulled {n} file(s) from GitHub; the preview rebuilds." if n else "Nothing new on GitHub.")
                   + (f" Kept the app's own for: {', '.join(kept)}." if kept else "")
                   + (f" {len(out['refused'])} incoming file(s) were not brought in (listed)." if out["refused"] else "")
                   + (f" {len(pl['kept_apart'])} file(s) Hoola keeps locked or that are not text were left alone." if pl["kept_apart"] else "")}


def push(tenant: str, ref: str, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        raise SyncError("Pushing to GitHub is your tap in the Studio (confirm).", 403)
    r = AE._load(tenant, ref)
    c = config(r)
    if not c.get("repo"):
        raise SyncError("Not linked to a GitHub repository.", 409)
    if not int(r.version or 0):
        raise SyncError("Build the app first; there is nothing to push yet.", 409)
    gh = _gh(tenant)
    head, remote = _remote(gh, c)
    if head != c.get("head", "") or (not c.get("head") and remote):
        raise SyncError("GitHub has commits that are not in the app yet. Pull first (Compare shows what), then push.", 409)
    local = local_files(r)
    if len(local) > MAX_FILES_SYNC or sum(len(v) for v in local.values()) > MAX_BYTES_SYNC:
        raise SyncError("The project is too large to push in one commit.", 413)
    for rel, raw in local.items():
        try:
            sec = _secret_in(raw.decode("utf-8"))
        except UnicodeDecodeError:
            sec = ""
        if sec:
            raise SyncError(f"Not pushed - {rel} contains {sec}. Remove it first; secrets are never sent to GitHub.", 422)
    man, ign = c.get("manifest") or {}, c.get("ignored") or {}
    tree, new_sha = [], {}
    o, n = c["owner"], c["repo"]
    for rel, raw in sorted(local.items()):
        s = blob_sha(raw)
        if rel in ign:                                           # GitHub's own copy stays
            tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": ign[rel]})
            continue
        if man.get(rel) != s:
            b = _call(gh.req, "POST", f"/repos/{o}/{n}/git/blobs", {"content": base64.b64encode(raw).decode(), "encoding": "base64"})
            s = b["sha"]
        tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": s})
        new_sha[rel] = s
    for rel, s in ign.items():                                   # kept-apart files that exist only on GitHub
        if rel not in local:
            tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": s})
    if not any(t["path"].lower() == "readme.md" for t in tree):
        b = _call(gh.req, "POST", f"/repos/{o}/{n}/git/blobs", {"content": f"# {r.name}\n\nMade with Hoola.\n", "encoding": "utf-8"})
        tree.append({"path": "README.md", "mode": "100644", "type": "blob", "sha": b["sha"]})
    now_man = {t["path"]: t["sha"] for t in tree}
    if head and now_man == remote:
        return {**status(r), "pushed": False, "say": "Nothing to push: GitHub already has exactly these files."}
    t = _call(gh.req, "POST", f"/repos/{o}/{n}/git/trees", {"tree": tree})
    cm = _call(gh.req, "POST", f"/repos/{o}/{n}/git/commits",
               {"message": f"Hoola: {r.name} v{r.version}", "tree": t["sha"], "parents": [head] if head else []})
    if head:
        _call(gh.req, "PATCH", f"/repos/{o}/{n}/git/refs/heads/{c['branch']}", {"sha": cm["sha"], "force": False})
    else:
        _call(gh.req, "POST", f"/repos/{o}/{n}/git/refs", {"ref": f"refs/heads/{c['branch']}", "sha": cm["sha"]})
    c.update(head=cm["sha"], manifest=now_man, at=now().isoformat(), fresh=False)
    _save_cfg(r, c)
    return {**status(r), "pushed": True, "commit": cm["sha"], "url": f"https://github.com/{o}/{n}",
            "say": f"Pushed v{r.version} to {o}/{n} ({c['branch']}) as one commit."}


# ------------------------------------------------------------------ ZIP: export and import
def export_zip(tenant: str, ref: str) -> tuple[str, bytes]:
    r = AE._load(tenant, ref)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, raw in sorted(local_files(r).items()):
            z.writestr(rel, raw)
    return f"{r.slug}.zip", buf.getvalue()


def read_zip(data: bytes) -> dict[str, bytes]:
    """The files of a ZIP, safely: no path out of the folder, no links, limits on size and count. One wrapping folder is removed."""
    if len(data) > ZIP_MAX:
        raise SyncError(f"The ZIP is over {ZIP_MAX // 1048576} MB.", 413)
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise SyncError("That is not a ZIP file.")
    infos = [i for i in z.infolist() if not i.is_dir()]
    if len(infos) > ZIP_ENTRIES or sum(i.file_size for i in infos) > ZIP_UNPACKED:
        raise SyncError("The ZIP is too large to import (too many files or too much unpacked data).", 413)
    out: dict[str, bytes] = {}
    for i in infos:
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            continue                                            # a symbolic link is never followed
        raw_parts = i.filename.replace("\\", "/").split("/")
        if ".." in raw_parts or i.filename.startswith(("/", "\\")):
            continue                                            # a path that climbs out of the folder is dropped, never tidied
        try:
            rel = RL.norm(i.filename)
        except RL.RuleError:
            continue
        if any(x in ("node_modules", ".git") for x in rel.split("/")):
            continue
        out[rel] = z.read(i)
    tops = {k.split("/")[0] for k in out}
    if len(tops) == 1 and all("/" in k for k in out) and "package.json" not in out and next(iter(tops)) not in ("src", "public"):
        pre = next(iter(tops)) + "/"
        out = {k[len(pre):]: v for k, v in out.items()}
    return out


def _import_into(tenant: str, name: str, files: dict[str, bytes], brief: str) -> dict[str, Any]:
    if not any(k == "package.json" for k in files) and not any(k.startswith("src/") for k in files):
        raise SyncError("This does not look like a web app project (no package.json and no src/ folder).")
    app = AE.create(tenant, name or "Imported app", brief)
    r = AE._load(tenant, app["id"])
    pkg_note = ""
    try:
        theirs = set((json.loads(files["package.json"].decode()).get("dependencies") or {})) if "package.json" in files else set()
        have = AE._deps(r)
        extra = sorted(theirs - have)
        if extra:
            pkg_note = ("Packages the project uses that this app does not have: " + ", ".join(extra[:12]) +
                        ". Only Hoola's vetted packages can be added (action=add_dependency); files that import the others are listed.")
    except (ValueError, UnicodeDecodeError):
        pass
    use = {k: v for k, v in files.items() if _syncable(k)}
    skipped = {}
    for k in list(use):
        why = _why_not(r, k)
        if why:
            skipped[k] = why
            del use[k]
    out = apply_files(r, use, strict=False)
    return {"app": AE.get(tenant, r.id), "id": r.id, "imported": out["written"], "refused": out["refused"],
            "kept_apart": skipped, "packages": pkg_note,
            "say": f"Imported {len(out['written'])} file(s) into a new app; {len(out['refused'])} did not follow Hoola's rules and were left out (listed), "
                   f"{len(skipped)} are files Hoola keeps itself." + (" " + pkg_note if pkg_note else "")}


def import_zip(tenant: str, name: str, data: bytes) -> dict[str, Any]:
    return _import_into(tenant, name, read_zip(data), "Imported from a ZIP")


def import_github(tenant: str, name: str, repo: str, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        raise SyncError("Importing from GitHub is your tap in the Studio (confirm).", 403)
    gh = _gh(tenant)
    me = _call(gh.me)
    owner, _, rname = str(repo or "").strip().partition("/")
    if not rname:
        owner, rname = str(me.get("login") or ""), owner
    info = _call(gh.req, "GET", f"/repos/{owner}/{rname}", None, True)
    if info is None:
        raise SyncError(f"The repository {owner}/{rname} was not found (or the token cannot read it).", 404)
    c = {"owner": owner, "repo": rname, "branch": info.get("default_branch") or "main"}
    head, remote = _remote(gh, c)
    if not remote:
        raise SyncError("That repository has no files yet.", 409)
    if len(remote) > 1500:
        raise SyncError("That repository has too many files to import.", 413)
    files = {}
    for p, sha in remote.items():
        if not _syncable(p):
            continue
        if RL.ext(p) in RL.TEXT_EXT or p in ("package.json",):
            files[p] = _blob(gh, c, sha)
    out = _import_into(tenant, name or rname, files, f"Imported from github.com/{owner}/{rname}")
    r = AE._load(tenant, out["id"])
    cfg = {**c, "private": bool(info.get("private", True)), "head": head, "manifest": dict(remote), "at": now().isoformat(),
           "ignored": {p: remote[p] for p in remote if p not in out["imported"] and _syncable(p)}}
    _save_cfg(r, cfg)
    out["linked"] = f"{owner}/{rname}"
    out["say"] += f" Linked to {owner}/{rname}: push sends your changes back."
    return out
