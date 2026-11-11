"""python -m app.gamedesk check   : Godot + Web templates + no-network box + a sample game that builds, exports and plays.
python -m app.gamedesk proof3d [--save] [--tenant ID] : v0.809 Hoola's own 3D game from the Hoola3D kit the whole road on
THIS server (no model): guard, headless play, web export, browser playtest, the test player wins it by keyboard, a real
browser plays it by touch, and the kit's own rules. --save keeps it as a finished game she can open and play."""
import json
import sys

from .service import check

if __name__ == "__main__":
    if sys.argv[1:2] == ["check"]:
        r = check()
        print(json.dumps(r, indent=1, default=str))
        sys.exit(0 if r.get("ok") else 1)
    if sys.argv[1:2] == ["proof3d"]:
        from ..db import init_db
        from . import kit3d
        init_db()
        args = sys.argv[2:]
        tenant = args[args.index("--tenant") + 1] if "--tenant" in args and args.index("--tenant") + 1 < len(args) else ""
        save = "--save" in args
        if save and not tenant:
            tenant = kit3d.newest_tenant()
        r = kit3d.proof(tenant=tenant, save=save)
        print(json.dumps(r, indent=1, default=str))
        print("3D PROOF:", "PASSED" if r.get("ok") else "NOT PASSED", ("- saved for " + tenant) if r.get("game") else "")
        sys.exit(0 if r.get("ok") else 1)
    if sys.argv[1:2] == ["arena"]:
        # v0.813: arena check (free, no model) | arena run [--n 3] [--budget 150] (REAL builds: spends model money,
        # stops at the rupee ceiling) | arena status (the last runs' numbers)
        import time
        from ..db import init_db
        from . import arena as A
        init_db()
        args = sys.argv[2:]

        def _num(flag, default):
            try:
                return float(args[args.index(flag) + 1]) if flag in args else default
            except (ValueError, IndexError):
                return default
        what = args[0] if args else ""
        if what == "check":
            r = A.selfcheck()
            print(json.dumps(r, indent=1, default=str))
            print("GAME ARENA CHECK:", "READY" if r.get("ok") else "NOT READY - " + str(r.get("why") or ""))
            sys.exit(0 if r.get("ok") else 1)
        if what == "status":
            print(json.dumps(A.runs(8), indent=1, default=str, ensure_ascii=False))
            sys.exit(0)
        if what == "run":
            A.finish_running()
            v = A.start(n=int(_num("--n", 3)), seed=int(_num("--seed", 1)), budget_inr=_num("--budget", 150.0),
                        note="started from the command line", background=False)
            A._go(v["id"])
            out = A.view(v["id"])
            print(json.dumps({"run": out.get("number"), "status": out.get("status"), "summary": out.get("summary"),
                              "cards": [{k: c.get(k) for k in ("brief", "genre", "started", "responds", "reached_end", "playable",
                                                                "fps", "errors", "sameness", "inr", "minutes")}
                                        for c in (out.get("cards") or [])]}, indent=1, default=str, ensure_ascii=False))
            sys.exit(0 if out.get("status") == "done" else 1)
    print("usage: python -m app.gamedesk check | proof3d [--save] [--tenant ID] | arena check | arena run [--n 3] [--budget 150] | arena status")
