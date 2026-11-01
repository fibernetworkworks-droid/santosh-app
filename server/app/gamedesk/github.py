"""v0.386 Studio Project -> HER GitHub: the live version's Godot project + DESIGN.md + TASKS.md (the board) +
DECISIONS.md + CHANGELOG.md (every version and the task it came from), one new commit per export. Same card and same
tap as the website / app export (site/github.py): her own token typed only in the app; nothing goes until she taps."""
from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..db import now, session
from . import service as G
from . import studio as S


def _load(tenant: str, ref: str) -> S.GameStudio:
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def stage(r: S.GameStudio) -> tuple[Path, int, str, int]:
    g = G._get(r.tenant_id, r.game_id)
    good = G._good(g)
    if not good:
        raise S.StudioError("Abhi koi chalne wala version nahi; pehle game banne dijiye.")
    live = good[-1]
    src = G._vdir(g, live["n"]) / "proj"
    dest = G._pdir(r.tenant_id, g.id) / "github"
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    n = 0
    for p in sorted(src.iterdir()):
        if p.is_file() and p.suffix in (".gd", ".godot", ".tscn", ".cfg"):
            shutil.copy2(p, dest / p.name)
            n += 1
    with session() as s:
        tasks = S._tasks(s, r.id)
        decs = s.scalars(select(S.GameDecision).where(S.GameDecision.studio_id == r.id).order_by(S.GameDecision.at)).all()
        board = ["# Tasks", ""]
        for m in r.milestones or S.MILESTONES:
            mine = [t for t in tasks if t.milestone == m["key"] and t.status != "dropped"]
            if mine:
                board += [f"## {m['name']}", ""] + [f"- [{'x' if t.status == 'done' else ' '}] {t.number} {t.title} ({t.status})"
                                                    for t in mine] + [""]
        dec = ["# Decisions", ""] + [f"- {d.at.date().isoformat() if d.at else ''} {d.text}" + (f" - {d.why}" if d.why else "")
                                     for d in decs]
    by_id = {t.id: t for t in tasks}
    log = ["# Changelog", ""]
    for v in reversed(g.versions or []):
        if not v.get("ok"):
            continue
        t = by_id.get(v.get("task") or "")
        log.append(f"- v{v['n']} ({str(v.get('at') or '')[:10]})" + (f" {t.number} {t.title}" if t else f" {v.get('words') or 'first build'}")
                   + (" - sent back" if v.get("rejected") else ""))
    (dest / "DESIGN.md").write_text(g.design or "")
    (dest / "TASKS.md").write_text("\n".join(board) + "\n")
    (dest / "DECISIONS.md").write_text("\n".join(dec) + "\n")
    (dest / "CHANGELOG.md").write_text("\n".join(log) + "\n")
    (dest / "README.md").write_text(f"# {r.title}\n\n{r.goal}\n\nMade with Hoola Studio on Godot 4 (godotengine.org, MIT). "
                                    "Open project.godot in the Godot editor 4.7+.\n")
    (dest / ".gitignore").write_text(".godot/\nbuild/\n*.import\n")
    n += 6
    h = hashlib.sha256()
    for p in sorted(dest.iterdir()):
        h.update(p.name.encode())
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return dest, n, h.hexdigest()[:24], int(live["n"])


def request(tenant: str, ref: str, repo: str = "", private: bool = True, conv: str = "") -> dict[str, Any]:
    from ..site import github as GH
    r = _load(tenant, ref)
    _folder, n, fp, ver = stage(r)
    me = GH.Gh(GH._token(tenant)).me()
    from ..site.hosting import slug_for
    name = re.sub(r"[^A-Za-z0-9._-]", "-", (repo or (slug_for(r.title or r.number) + "-game")).strip())[:90].strip("-.") or "hoola-game"
    with session() as s:
        o = GH.SiteGithubExport(tenant_id=tenant, site_id="game:" + r.id, version=ver, owner=str(me.get("login") or ""),
                                repo=name, private=bool(private), files=n)
        s.add(o)
        s.flush()
        o.hash = GH._hash(o, fp)
        s.flush()
        s.expunge(o)
    card = {"kind": "github", "id": o.id, "game": {"id": r.id, "number": r.number, "title": r.title},
            "repo": f"{o.owner}/{o.repo}", "private": o.private, "version": ver, "files": n, "hash": o.hash,
            "say": (f"{r.title} ka code (version {ver}, {n} files: Godot project + tasks + decisions) aapke GitHub "
                    f"'{o.owner}/{o.repo}' mein daalun? " + ("Private: sirf aap dekh payengi." if o.private else
                                                             "PUBLIC: koi bhi dekh sakta hai.") + " Aapki haan chahiye."),
            "push": True}
    from ..seo.service import _publish
    _publish(tenant, "site_github", card, conv or r.conversation_id)
    return card


def push(tenant: str, o: Any, hash_: str) -> dict[str, Any]:
    """ONLY her tap (site.github.push routes a 'game:' export here): one new commit on top of the branch."""
    import base64
    from ..site import github as GH
    r = _load(tenant, o.site_id[5:])
    folder, _n, fp, _v = stage(r)
    if hash_ != GH._hash(o, fp):
        raise GH.GithubError("Game ka naya version aa gaya; naya card mangiye ('game code GitHub mein daalo').")
    gh = GH.Gh(GH._token(tenant))
    GH._set(o.id, status="pushing")
    try:
        repo = gh.req("GET", f"/repos/{o.owner}/{o.repo}", ok404=True)
        if repo is None:
            repo = gh.req("POST", "/user/repos", {"name": o.repo, "private": o.private, "auto_init": True,
                                                   "description": f"{r.title} - game made with Hoola"})
        branch = repo.get("default_branch") or "main"
        ref = gh.req("GET", f"/repos/{o.owner}/{o.repo}/git/ref/heads/{branch}", ok404=True)
        parent = ((ref or {}).get("object") or {}).get("sha")
        tree = []
        for p in sorted(folder.iterdir()):
            blob = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/blobs",
                          {"content": base64.b64encode(p.read_bytes()).decode(), "encoding": "base64"})
            tree.append({"path": p.name, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        t = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/trees", {"tree": tree})
        c = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/commits",
                   {"message": f"{r.title}: version {o.version} (Hoola Studio)", "tree": t["sha"], "parents": [parent] if parent else []})
        if ref:
            gh.req("PATCH", f"/repos/{o.owner}/{o.repo}/git/refs/heads/{branch}", {"sha": c["sha"], "force": False})
        else:
            gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": c["sha"]})
    except GH.GithubError as e:
        GH._set(o.id, status="failed", error=str(e))
        raise
    url = f"https://github.com/{o.owner}/{o.repo}"
    GH._set(o.id, status="done", url=url)
    S._decide(r, f"Code GitHub mein gaya (version {o.version})", url, by="hoola")
    say = f"{r.title} ka code GitHub mein chala gaya (version {o.version}): {url}"
    from ..seo.service import _publish
    _publish(tenant, "site_github", {"kind": "github_done", "id": o.id, "url": url, "say": say, "push": False,
                                     "at": now().isoformat()}, r.conversation_id)
    return {"ok": True, "url": url, "commit": c["sha"], "say": say}
