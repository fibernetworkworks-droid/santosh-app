"""v0.999 PLUGINS for Hoola Code, Claude Code's way (owner: "CHECK AGAIN HOOLA CODE IS 100% SAME AS CLAUDE CODE" -> "GO ALL").

A Claude Code plugin is a folder (usually a GitHub repo) with `commands/`, `agents/`, `skills/`, `hooks/hooks.json`,
`.mcp.json` and `.claude-plugin/plugin.json`; a MARKETPLACE is a repo whose `.claude-plugin/marketplace.json` lists
several plugins in its own sub-folders. She adds one by its public GitHub link (her tap): Hoola copies it once to her own
plugin shelf on the server, each plugin can be switched on or off, and the ones that are on join EVERY session of hers -
their commands in the / menu, their agents beside the repo's, their skills, their hooks (run in the locked box like the
repo's own) and their remote MCP servers. Nothing in a plugin runs on Hoola's server; links (symlinks) are dropped; the
copy is capped at 20 MB and 20 plugins."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

MAX_BYTES = 20_000_000
MAX_PLUGINS = 20
GH_URL = re.compile(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


class PluginError(Exception):
    pass


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(s or ""))[:60] or "x"


def shelf(tenant: str) -> Path:
    return Path("data") / "devsahayak" / "plugins" / _safe(tenant)


def _index(tenant: str) -> dict[str, Any]:
    f = shelf(tenant) / "plugins.json"
    try:
        return json.loads(f.read_text()) if f.is_file() else {}
    except ValueError:
        return {}


def _save(tenant: str, idx: dict[str, Any]) -> None:
    d = shelf(tenant)
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / ".plugins.json.tmp"
    tmp.write_text(json.dumps(idx, indent=1))
    os.replace(tmp, d / "plugins.json")


def _what(root: Path) -> dict[str, int]:
    n = lambda pat: len(list(root.glob(pat)))  # noqa: E731
    return {"commands": n("commands/**/*.md"), "agents": n("agents/*.md"), "skills": n("skills/*/SKILL.md"),
            "hooks": int((root / "hooks" / "hooks.json").is_file()), "mcp": int((root / ".mcp.json").is_file())}


def listing(tenant: str) -> list[dict[str, Any]]:
    out = []
    for name, p in sorted(_index(tenant).items()):
        root = shelf(tenant) / name
        out.append({"name": name, "url": p.get("url", ""), "description": p.get("description", ""), "enabled": bool(p.get("enabled")),
                    "version": p.get("version", ""), "has": _what(root) if root.is_dir() else {}})
    return out


def roots(tenant: str) -> list[Path]:
    """The folders of her plugins that are switched on (what every session of hers reads)."""
    if not tenant:
        return []
    return [shelf(tenant) / n for n, p in sorted(_index(tenant).items()) if p.get("enabled") and (shelf(tenant) / n).is_dir()]


def _copy(src: Path, dst: Path) -> None:
    """A plain copy: no .git, no links, at most MAX_BYTES."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d != ".git" and not os.path.islink(os.path.join(dirpath, d))]
        rel = Path(dirpath).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.is_symlink() or not p.is_file():
                continue
            total += p.stat().st_size
            if total > MAX_BYTES:
                raise PluginError("This plugin is bigger than 20 MB.")
            shutil.copyfile(p, dst / rel / fn)


def _clone(url: str, into: Path) -> None:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(into.parent), "GIT_TERMINAL_PROMPT": "0",
           "GIT_CONFIG_NOSYSTEM": "1", "LANG": "C.UTF-8"}
    r = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "protocol.file.allow=never", "clone", "-q", "--depth", "1",
                        "--no-tags", url, str(into)], capture_output=True, text=True, timeout=90, env=env)
    if r.returncode != 0:
        raise PluginError("Could not download it from GitHub (is the repo public?): " + (r.stderr or "").strip()[:200])


def _meta(root: Path) -> dict[str, Any]:
    try:
        j = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
        return j if isinstance(j, dict) else {}
    except (OSError, ValueError):
        return {}


def add(tenant: str, url: str, clone=_clone) -> list[dict[str, Any]]:
    """Add a plugin (or every plugin of a marketplace) from its public GitHub link. Returns her plugin list."""
    url = str(url or "").strip()
    m = GH_URL.match(url)
    if not m:
        raise PluginError("Paste the plugin's GitHub link, like https://github.com/owner/repo.")
    idx = _index(tenant)
    tmp = Path(tempfile.mkdtemp(prefix="hoola-plugin-"))
    try:
        clone(f"https://github.com/{m.group(1)}/{m.group(2)}.git", tmp / "src")
        src = tmp / "src"
        found: list[tuple[str, Path, dict[str, Any]]] = []
        mk = src / ".claude-plugin" / "marketplace.json"
        if mk.is_file():
            try:
                market = json.loads(mk.read_text())
            except ValueError:
                market = {}
            for pl in (market.get("plugins") or [])[:MAX_PLUGINS]:
                srcp = pl.get("source") if isinstance(pl, dict) else None
                if not isinstance(srcp, str) or not srcp.startswith("./"):
                    continue                                 # a plugin kept in another repo: add that repo's link instead
                root = (src / srcp).resolve()
                if not root.is_dir() or not root.is_relative_to(src.resolve()):
                    continue
                found.append((str(pl.get("name") or root.name), root, {**_meta(root), **{k: pl[k] for k in ("description", "version") if k in pl}}))
        else:
            found.append((str(_meta(src).get("name") or m.group(2)), src, _meta(src)))
        if not found:
            raise PluginError("No plugin was found in that repo (no .claude-plugin/plugin.json or marketplace.json).")
        if len(idx) + len(found) > MAX_PLUGINS:
            raise PluginError(f"At most {MAX_PLUGINS} plugins.")
        for name, root, meta in found:
            key = _safe(name).lower()
            dst = shelf(tenant) / key
            if dst.exists():
                shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            _copy(root, dst)
            idx[key] = {"url": url, "description": str(meta.get("description") or "")[:300], "version": str(meta.get("version") or "")[:40],
                        "enabled": True}
        _save(tenant, idx)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return listing(tenant)


def set_enabled(tenant: str, name: str, on: bool) -> list[dict[str, Any]]:
    idx = _index(tenant)
    if name not in idx:
        raise PluginError("No such plugin.")
    idx[name]["enabled"] = bool(on)
    _save(tenant, idx)
    return listing(tenant)


def remove(tenant: str, name: str) -> list[dict[str, Any]]:
    idx = _index(tenant)
    if name not in idx:
        raise PluginError("No such plugin.")
    idx.pop(name)
    shutil.rmtree(shelf(tenant) / _safe(name), ignore_errors=True)
    _save(tenant, idx)
    return listing(tenant)
