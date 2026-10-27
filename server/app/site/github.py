"""v0.124 Her site's code in HER GitHub (official REST API, her own fine-grained token typed only in the app): a card with
the repo name, private / public, the version and the files; ONLY her tap pushes. Repo made if missing (private by default),
then one commit through the Git Data API (blobs -> tree -> commit -> branch ref). Nothing else in her account is touched.
Useful for an agency handover or to host it elsewhere later."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from datetime import datetime

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.site")
API = "https://api.github.com"
MAX_FILES, MAX_BYTES = 600, 60 * 1024 * 1024
_TRANSPORT: httpx.BaseTransport | None = None


class GithubError(Exception):
    pass


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


class SiteGithubExport(Base):
    __tablename__ = "site_github_exports"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gh"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    owner: Mapped[str] = mapped_column(String(100), default="")
    repo: Mapped[str] = mapped_column(String(100), default="")
    private: Mapped[bool] = mapped_column(Boolean, default=True)
    files: Mapped[int] = mapped_column(Integer, default=0)
    hash: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(12), default="card")        # card | pushing | done | failed | cancelled
    url: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Gh:
    def __init__(self, token: str):
        if not token:
            raise GithubError("GitHub juda nahi hai: Website > Hosting mein apna GitHub token jodiye (sirf app mein).")
        self.token = token

    def req(self, method: str, path: str, body: Any = None, ok404: bool = False) -> Any:
        try:
            with httpx.Client(timeout=60, transport=_TRANSPORT) as c:
                r = c.request(method, f"{API}{path}", json=body, headers={
                    "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Hoola-Website"})
        except httpx.HTTPError as e:
            raise GithubError(f"GitHub tak nahi pahunch paya: {e.__class__.__name__}")
        if ok404 and r.status_code == 404:
            return None
        if r.status_code >= 400:
            try:
                msg = r.json().get("message", "")
            except ValueError:
                msg = r.text[:200]
            if r.status_code in (401, 403):
                msg += " (token mein is repo par 'Contents: write' / 'Administration: write' ki ijazat chahiye)"
            raise GithubError(f"GitHub: {r.status_code} {msg}")
        return r.json() if r.content else {}

    def me(self) -> dict[str, Any]:
        return self.req("GET", "/user")


def _token(tenant: str) -> str:
    from .dns import key
    return key(tenant, "github")[0]


def repo_name(name: str) -> str:
    from .hosting import slug_for
    return (slug_for(name) + "-website")[:90]


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and not p.name.startswith(".") and "__" not in p.as_posix())


def _ready(p: Path) -> bytes:
    """The preview build says 'noindex'; the exported copy is the real site, so search engines may list it."""
    data = p.read_bytes()
    if p.suffix == ".html":
        return data.replace(b'<meta name="robots" content="noindex">', b"")
    if p.name == "robots.txt":
        return b"User-agent: *\nAllow: /\n"
    return data


def _folder(tenant: str, site_id: str, version: int) -> Path:
    from . import build as B
    return B.out_dir(tenant, site_id, version)


def _hash(o: SiteGithubExport, fp: str) -> str:
    return hashlib.sha256(f"{o.id}|{o.owner}|{o.repo}|{o.private}|{o.version}|{fp}".encode()).hexdigest()[:24]


def request(tenant: str, ref: str, repo: str = "", private: bool = True, conv: str = "") -> dict[str, Any]:
    from . import build as B
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    if not r.version:
        raise GithubError("Pehle website banne dijiye; abhi koi version nahi.")
    me = Gh(_token(tenant)).me()
    name = re.sub(r"[^A-Za-z0-9._-]", "-", (repo or repo_name(r.name or r.number)).strip())[:90].strip("-.") or "hoola-website"
    folder = _folder(tenant, r.id, r.version)
    files = _files(folder)
    size = sum(p.stat().st_size for p in files)
    if not files:
        raise GithubError("Is version ki files nahi mili.")
    if len(files) > MAX_FILES or size > MAX_BYTES:
        raise GithubError(f"Bahut badi site ({len(files)} files, {size // 1048576} MB); ZIP export use kijiye.")
    with session() as s:
        o = SiteGithubExport(tenant_id=tenant, site_id=r.id, version=r.version, owner=str(me.get("login") or ""), repo=name,
                             private=bool(private), files=len(files))
        s.add(o)
        s.flush()
        o.hash = _hash(o, B.fingerprint(folder))
        s.flush()
        s.expunge(o)
    card = {"kind": "github", "id": o.id, "site": S.view(r, False), "repo": f"{o.owner}/{o.repo}", "private": o.private,
            "version": o.version, "files": o.files, "size_kb": size // 1024, "hash": o.hash,
            "say": (f"v{o.version} ki {o.files} files aapke GitHub '{o.owner}/{o.repo}' mein "
                    + ("(private: sirf aap dekh payengi)" if o.private else "(PUBLIC: koi bhi dekh sakta hai)")
                    + " daalun? Aapki haan chahiye."), "push": True}
    S._publish(tenant, "site_github", card, conv or r.conv)
    return card


def push(tenant: str, eid: str, hash_: str) -> dict[str, Any]:
    """ONLY her tap (API)."""
    from . import build as B
    from . import service as S
    with session() as s:
        o = s.get(SiteGithubExport, eid)
        if o is None or o.tenant_id != tenant:
            raise GithubError("Yeh card nahi mila.")
        if o.status != "card":
            raise GithubError(f"Yeh export '{o.status}' hai.")
        s.expunge(o)
    folder = _folder(tenant, o.site_id, o.version)
    if not folder.exists() or hash_ != _hash(o, B.fingerprint(folder)):
        raise GithubError("Card badal gaya; naya card mangiye.")
    gh = Gh(_token(tenant))
    _set(eid, status="pushing")
    try:
        repo = gh.req("GET", f"/repos/{o.owner}/{o.repo}", ok404=True)
        if repo is None:
            repo = gh.req("POST", "/user/repos", {"name": o.repo, "private": o.private, "auto_init": True,
                                                   "description": "Website made with Hoola"})
        branch = repo.get("default_branch") or "main"
        ref = gh.req("GET", f"/repos/{o.owner}/{o.repo}/git/ref/heads/{branch}", ok404=True)
        parent = ((ref or {}).get("object") or {}).get("sha")
        tree = []
        for p in _files(folder):
            blob = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/blobs",
                          {"content": base64.b64encode(_ready(p)).decode(), "encoding": "base64"})
            tree.append({"path": p.relative_to(folder).as_posix(), "mode": "100644", "type": "blob", "sha": blob["sha"]})
        readme = ("# Website\n\nMade with Hoola (Newtika). Static files: open index.html, or host this folder on any static "
                  "host (GitHub Pages, Cloudflare Pages, Netlify).\n")
        b = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/blobs", {"content": readme, "encoding": "utf-8"})
        if not any(t["path"].lower() == "readme.md" for t in tree):
            tree.append({"path": "README.md", "mode": "100644", "type": "blob", "sha": b["sha"]})
        t = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/trees", {"tree": tree})
        c = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/commits",
                   {"message": f"Hoola website v{o.version}", "tree": t["sha"], "parents": [parent] if parent else []})
        if ref:
            gh.req("PATCH", f"/repos/{o.owner}/{o.repo}/git/refs/heads/{branch}", {"sha": c["sha"], "force": False})
        else:
            gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": c["sha"]})
    except GithubError as e:
        _set(eid, status="failed", error=str(e))
        raise
    url = f"https://github.com/{o.owner}/{o.repo}"
    _set(eid, status="done", url=url)
    say = f"v{o.version} GitHub mein chali gayi: {url}"
    S._publish(tenant, "site_github", {"kind": "github_done", "id": eid, "url": url, "say": say, "push": False})
    return {"ok": True, "url": url, "commit": c["sha"], "say": say}


def cancel(tenant: str, eid: str) -> dict[str, Any]:
    with session() as s:
        o = s.get(SiteGithubExport, eid)
        if o is None or o.tenant_id != tenant or o.status != "card":
            raise GithubError("Yeh card band nahi ho sakta.")
        o.status = "cancelled"
    return {"ok": True, "say": "GitHub mein nahi daala."}


def _set(eid: str, **kw) -> None:
    with session() as s:
        o = s.get(SiteGithubExport, eid)
        for k, v in kw.items():
            setattr(o, k, v)


def exports(tenant: str, site_id: str = "") -> list[dict[str, Any]]:
    with session() as s:
        q = select(SiteGithubExport).where(SiteGithubExport.tenant_id == tenant)
        if site_id:
            q = q.where(SiteGithubExport.site_id == site_id)
        return [{"id": o.id, "repo": f"{o.owner}/{o.repo}", "version": o.version, "private": o.private, "status": o.status,
                 "url": o.url, "error": o.error} for o in s.scalars(q.order_by(SiteGithubExport.created_at.desc()).limit(20)).all()]
