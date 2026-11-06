"""python -m app.gamedesk check : Godot + Web templates + no-network box + a sample game that builds, exports and plays."""
import json
import sys

from .service import check

if __name__ == "__main__":
    if sys.argv[1:2] == ["check"]:
        r = check()
        print(json.dumps(r, indent=1, default=str))
        sys.exit(0 if r.get("ok") else 1)
    print("usage: python -m app.gamedesk check")
