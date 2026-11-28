"""python -m app.diagram setup | check [--quick] | status

setup   fetch the draw.io editor (sha-256 checked) - the only download; archify and diagram-design ship in git
check   D1's proof on THIS server: every engine's own checks on its own examples + one PNG from each engine
          archify         every example through its four gates (--quick: 3 of them)
          diagram-design  self_check + verify_geometry on all its example files
          draw.io         the editor loads a diagram and exports a PNG
status  what is installed (commits, node, browser, draw.io) - reads only"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

from . import drawio as DR
from . import runners as R
from . import vendor as V

SAMPLE_DRAWIO = ('<mxfile><diagram name="check"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
                 '<mxCell id="a" value="Browser" style="rounded=1;" vertex="1" parent="1"><mxGeometry x="20" y="20" '
                 'width="120" height="50" as="geometry"/></mxCell><mxCell id="b" value="API" style="rounded=1;" '
                 'vertex="1" parent="1"><mxGeometry x="220" y="20" width="120" height="50" as="geometry"/></mxCell>'
                 '<mxCell id="e" edge="1" source="a" target="b" parent="1"><mxGeometry relative="1" as="geometry"/>'
                 '</mxCell></root></mxGraphModel></diagram></mxfile>')


# archify's OWN example files that its own strictest rule turns away (checked 28 Nov 2026 at b42e7d7): each is a tall
# 720x900 canvas, so showcase delivery reports composition/viewport-height and the standard browser check reports the
# page overflowing. That is upstream data, not Hoola's setup - listed here (never hidden) and expected to fail that way.
KNOWN_UPSTREAM = {
    "async-job-roundtrip.sequence.json": "composition/viewport-height",
    "event-stream.dataflow.json": "composition/viewport-height",
    "incident-response.workflow.json": "composition/viewport-height",
    "release-delivery.workflow.json": "composition/viewport-height",
}


def status() -> dict:
    return {"engines": V.status(), "node": R.node_bin() or "MISSING (node >= 18 needed for archify)",
            "browser": R.chrome_path() or "MISSING", "drawio_editor": {"ready": DR.ready(), "dir": str(DR.editor_dir()),
                                                                      "pinned": V.drawio_pin()["version"]},
            "types": {"archify": len(V.archify_types()), "diagram-design": len(V.dd_types())}}


def check(quick: bool = False) -> dict:
    out: dict = {"ok": True}
    work = Path(tempfile.mkdtemp(prefix="hoola-diagram-check-"))
    # archify
    ex = V.archify_examples()
    if quick:
        seen, pick = set(), []
        for k, f in ex:
            if k not in seen:
                seen.add(k)
                pick.append((k, f))
        ex = pick[:3]
    a_fail, known = {}, {}
    t0 = time.time()
    for k, f in ex:
        q = (json.loads(f.read_text("utf-8")).get("meta") or {}).get("quality_profile") or "standard"
        r = R.archify_finalize(k, f, work / "archify" / f.stem.replace(".", "-"), slug=f.stem.split(".")[0],
                               quality="showcase" if q == "showcase" else "standard")
        if r["ok"]:
            continue
        if KNOWN_UPSTREAM.get(f.name) in r.get("codes", []):
            known[f.name] = "upstream example: tall canvas, archify's own rule turns it away (" + KNOWN_UPSTREAM[f.name] + ")"
        else:
            a_fail[f.name] = r["problems"][:3] or [r["said"]]
    first = R.archify_finalize("architecture", V.ARCHIFY / "examples" / "web-app.architecture.json", work / "a-png",
                               slug="web-app")
    a_png = R.page_png(first["html"], work / "archify.png") if first["ok"] else {"ok": False}
    out["archify"] = {"examples": len(ex), "passed": len(ex) - len(a_fail) - len(known), "failed": a_fail,
                      "known_upstream": known,
                      "png": bool(a_png.get("ok")), "seconds": round(time.time() - t0, 1)}
    # diagram-design
    t0 = time.time()
    files = V.dd_examples()
    d = R.dd_check(files)
    b_png = R.dd_png(V.DD / "assets" / "example-architecture.html", work / "diagram-design.png")
    out["diagram-design"] = {"examples": len(files), "passed": len(files) - len(d["failed"]),
                             "failed": {Path(k).name: v[:3] for k, v in list(d["failed"].items())[:20]},
                             "png": bool(b_png.get("ok")), "seconds": round(time.time() - t0, 1)}
    # draw.io
    if DR.ready():
        c = R.drawio_png(SAMPLE_DRAWIO, work / "drawio.png")
        out["drawio"] = {"editor": True, "png": bool(c.get("ok")), "said": c.get("said", "")}
    else:
        out["drawio"] = {"editor": False, "png": False, "said": "not set up - run: python -m app.diagram setup"}
    out["ok"] = (not a_fail and out["archify"]["png"] and not d["failed"] and out["diagram-design"]["png"]
                 and out["drawio"]["png"])
    out["pictures"] = str(work)
    return out


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "status"
    if cmd == "setup":
        r = DR.setup(force="--force" in argv)
        print(r["said"])
        return 0 if r["ok"] else 1
    if cmd == "check":
        r = check(quick="--quick" in argv)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        print("DIAGRAM CHECK:", "PASS" if r["ok"] else "FAIL")
        return 0 if r["ok"] else 1
    print(json.dumps(status(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
