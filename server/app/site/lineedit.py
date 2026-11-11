"""v0.787 CHHOTA BADLAAV (L4 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L4"): small exact changes to a website's code,
the way Lovable's line-replace tool works - instead of asking Opus to write a whole section again for "make the
button grey".

- search: find a piece of text in the site's code files (every section's html / css / js + the design kit), with the
  file and line, so the model knows exactly where it is;
- edit: one exact search -> replace in one file. The search text must appear EXACTLY ONCE (0 = not found, said with
  the closest lines; 2+ = say more of the surrounding text) - nothing is ever changed by a guess. The result goes
  through the SAME cleaner as every build (code.clean / kit.clean), one Undo step, and a version checked on that
  section's page only (service.save_version quick); the full check runs again before the site goes live.
- write: a whole file, for the rare change a search / replace cannot say (the same cleaner, same quick check).
No model call here: an edit costs nothing but the turn that asked for it."""
from __future__ import annotations

import difflib
from typing import Any

from . import code as CD

MAX_SEARCH = 4000
MAX_HITS = 30


class LineEditError(Exception):
    pass


def _files(r) -> dict[str, str]:
    from . import service as S
    secs = S._sections(r)
    out: dict[str, str] = {}
    for key in secs:
        for part in CD.PARTS:
            path = CD.path_of(key, part)
            try:
                out[path] = CD.read(path, secs, "")["code"]
            except CD.CodeError:
                continue
    kit = S._kit_css(r)
    if kit:
        out["design/kit.css"] = CD.read("design/kit.css", secs, kit)["code"]
    return out


def search(r, query: str, limit: int = MAX_HITS) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        raise LineEditError("What should I look for? Give a word, a colour or a class name.")
    ql, hits, total = q.lower(), [], 0
    for path, code in _files(r).items():
        for n, line in enumerate(code.splitlines(), 1):
            if ql in line.lower():
                total += 1
                if len(hits) < limit:
                    hits.append({"file": path, "line": n, "text": line.strip()[:240]})
    return {"query": q, "hits": hits, "total": total,
            "say": (f"{total} place(s) found" + (f", first {len(hits)} shown" if total > len(hits) else "")) if total
            else "Not found in the site's code."}


def _closest(code: str, search: str) -> list[str]:
    lines = code.splitlines()
    first = (search.strip().splitlines() or [""])[0].strip()
    near = difflib.get_close_matches(first, [x.strip() for x in lines], n=3, cutoff=0.5)
    return [x[:200] for x in near]


def edit(tenant: str, ref: str, path: str, find: str, replace: str) -> dict[str, Any]:
    """One exact search / replace in one file; the write path is service.code_write (cleaner, Undo, quick check)."""
    from . import service as S
    if not path:
        raise LineEditError("Which file? Use website_dekho what=search first; it names the file.")
    find, replace = str(find or ""), str(replace or "")
    if not find.strip():
        raise LineEditError("The search text is empty; copy the exact text to change from the file.")
    if len(find) > MAX_SEARCH or len(replace) > MAX_SEARCH * 3:
        raise LineEditError("That is a big change; use action=change (or write the whole file) instead.")
    if find == replace:
        raise LineEditError("The search and the replacement are the same; nothing to change.")
    cur = S.code_read(tenant, ref, path)["code"]
    n = cur.count(find)
    if n == 0:
        near = _closest(cur, find)
        raise LineEditError("The search text is not in " + path + " exactly (spaces and quotes count)."
                            + (" Closest lines: " + " | ".join(near) if near else " Read the file first (website_dekho what=code)."))
    if n > 1:
        raise LineEditError(f"The search text appears {n} times in {path}; include more of the surrounding text so it "
                            "matches exactly once.")
    new = cur.replace(find, replace, 1)
    out = S.code_write(tenant, ref, path, new)
    after = out.get("code") or ""
    diff = CD.diff(path, cur, after)
    landed = bool(diff.strip())
    return {"file": path, "changed": landed, "diff": diff[:12000], "removed": out.get("removed") or [],
            "version_note": "checked on this page only; the full check runs before going live",
            "say": ("Changed " + path + ("; the safety cleaner also removed: " + "; ".join(out["removed"][:3])
                                         if out.get("removed") else "") + ". A new version is being checked on that page.")
            if landed else (out.get("say") or "Nothing changed (the safety cleaner removed it).")}


def write(tenant: str, ref: str, path: str, code: str) -> dict[str, Any]:
    from . import service as S
    if not path:
        raise LineEditError("Which file?")
    if not str(code or "").strip():
        raise LineEditError("The file would be empty; to remove a section use action=change.")
    cur = S.code_read(tenant, ref, path)["code"]
    out = S.code_write(tenant, ref, path, str(code))
    return {"file": path, "changed": out.get("code") != cur, "diff": CD.diff(path, cur, out.get("code") or "")[:12000],
            "removed": out.get("removed") or [], "say": out.get("say") or ""}
