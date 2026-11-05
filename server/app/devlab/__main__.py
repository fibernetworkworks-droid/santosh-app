"""`python -m app.devlab <check|setup|run|images|prune>` - the lab from the VPS command line, no model involved."""
from __future__ import annotations

import argparse
import json
import sys

from . import box, out, service


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.devlab")
    ap.add_argument("what", choices=["check", "setup", "run", "images", "prune", "grep"])
    ap.add_argument("--repo", default="", help="owner/name (run)")
    ap.add_argument("--ref", default="", help="branch or 40-char sha (run)")
    ap.add_argument("--cmd", default="", help="the command to run (run); omitted = the repo's declared one")
    ap.add_argument("--setup", default="", help="dependency install command (run)")
    ap.add_argument("--token", default="", help="GitHub token for a private repo (run)")
    ap.add_argument("--timeout", type=int, default=0)
    ap.add_argument("--keep", type=int, default=12, help="snapshots to keep (prune)")
    ap.add_argument("--log", default="", help="log path (grep)")
    ap.add_argument("--pattern", default="", help="what to look for (grep)")
    ap.add_argument("--rebuild", action="store_true", help="rebuild the base image from scratch (setup)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.what == "check":
        for line in service.selftest():
            print(line)
        return 0
    if a.what == "setup":
        r = box.build_base(nocache=a.rebuild)
        print(f"{'ok' if r['ok'] else 'FAIL'} {r.get('image')} ({r.get('seconds')}s) {r.get('why', '')}")
        if not r["ok"]:
            print("\n".join(r.get("out", "").splitlines()[-25:]))
        return 0 if r["ok"] else 1
    if a.what == "images":
        for i in box.images():
            print(f"{i['image']:<60} {i['size']:>10}  {i['at']}")
        return 0
    if a.what == "prune":
        gone = box.prune(a.keep)
        print(f"{len(gone)} snapshot hataye" + (": " + ", ".join(gone) if gone else ""))
        return 0
    if a.what == "grep":
        print(out.grep_log(a.log, a.pattern))
        return 0
    if not a.repo:
        print("--repo owner/name chahiye", file=sys.stderr)
        return 2
    r = service.check(a.repo, a.ref, a.token, a.cmd, {"ok": "1"}, a.timeout, a.setup)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2)[:20000])
        return 0 if r.get("ok") else 1
    print(r.get("say") or r.get("why") or "?")
    for k in ("stage", "cmd", "source", "image", "snapshot_cached", "setup_seconds", "total_seconds", "bytes", "cut", "log"):
        if k in r:
            print(f"  {k}: {r[k]}")
    if r.get("shown"):
        print("---- output\n" + r["shown"][:8000])
    if r.get("out"):
        print("---- setup output\n" + str(r["out"])[-3000:])
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
