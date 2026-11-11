"""python -m app.gamedesk check   : Godot + Web templates + no-network box + a sample game that builds, exports and plays.
python -m app.gamedesk proof3d [--save] [--tenant ID] : v0.806 Hoola's own 3D game from the Hoola3D kit the whole road on
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
    print("usage: python -m app.gamedesk check | proof3d [--save] [--tenant ID]")
