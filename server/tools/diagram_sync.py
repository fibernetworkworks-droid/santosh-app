"""Drop a newer upstream copy of one HOOLA DIAGRAM engine into server/app/diagram/vendor/ - only on the owner's word.

    python server/tools/diagram_sync.py archify <commit>
    python server/tools/diagram_sync.py diagram-design <commit>
    python server/tools/diagram_sync.py drawio-ai <commit>

Clones the engine's repo at that commit into a temporary folder, copies the SAME parts the first copy took (the rules
below; tests, dot-files and zips left out), replaces the vendor folder whole, writes the new commit into VENDOR.json and
runs `python -m app.diagram check --quick`. The vendored files are never edited by hand - a Hoola change goes into
app/diagram/*.py. Review `git diff --stat` before committing; a failing check means the new copy breaks Hoola's wrapper."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
VENDOR = SERVER / "app" / "diagram" / "vendor"
MANIFEST = SERVER / "app" / "diagram" / "VENDOR.json"
SKIP = {"test", "tests", "node_modules", ".gitignore", ".gitattributes", ".git"}

RULES = {   # engine: (repo, [(source in repo, dest under vendor/)], [single files: (source, dest)])
    "archify": ("https://github.com/tt-a1i/archify.git",
                [("archify", "archify"), ("archify-pr", "archify-pr")],
                [(f, f"archify/{f}") for f in ("LICENSE", "LICENSE-MIT", "NOTICE", "THIRD_PARTY_NOTICES.md")]),
    "diagram-design": ("https://github.com/cathrynlavery/diagram-design.git",
                       [("skills/diagram-design", "diagram-design")], [("LICENSE", "diagram-design/LICENSE")]),
    "drawio-ai": ("https://github.com/DayuanJiang/next-ai-draw-io.git",
                  [("packages/mcp-server/src", "drawio-ai/src"), ("packages/mcp-server/shell", "drawio-ai/shell")],
                  [("packages/mcp-server/drawio-files.txt", "drawio-ai/drawio-files.txt"),
                   ("packages/mcp-server/package.json", "drawio-ai/package.json"),
                   ("packages/mcp-server/README.md", "drawio-ai/README.md"), ("LICENSE", "drawio-ai/LICENSE")]),
}


def ignore(_d: str, names: list[str]) -> list[str]:
    return [n for n in names if n in SKIP or n.endswith(".zip")]


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in RULES:
        print(__doc__)
        return 2
    engine, commit = argv
    repo, dirs, files = RULES[engine]
    with tempfile.TemporaryDirectory(prefix="diagram-sync-") as tmp:
        src = Path(tmp) / "src"
        subprocess.run(["git", "clone", "-q", repo, str(src)], check=True)
        subprocess.run(["git", "-C", str(src), "checkout", "-q", commit], check=True)
        full = subprocess.run(["git", "-C", str(src), "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
        tops = {d.split("/")[0] for _, d in dirs} | {d.split("/")[0] for _, d in files}
        for top in tops:
            shutil.rmtree(VENDOR / top, ignore_errors=True)
        for s, d in dirs:
            shutil.copytree(src / s, VENDOR / d, ignore=ignore)
        for s, d in files:
            (VENDOR / d).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / s, VENDOR / d)
    sys.path.insert(0, str(SERVER))
    from app.diagram import vendor as V
    m = json.loads(MANIFEST.read_text("utf-8"))
    m[engine]["commit"] = full
    m[engine]["tree_sha256"] = V.tree_hash(engine)
    m[engine]["files"] = len(V._files(engine))
    MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"{engine} now at {full}. Running the quick check ...")
    return subprocess.run([sys.executable, "-m", "app.diagram", "check", "--quick"], cwd=str(SERVER)).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
