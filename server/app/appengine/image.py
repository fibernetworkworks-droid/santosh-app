"""v0.814 APP ENGINE 1 (L8 of docs/LOVABLE_STUDIO_PLAN.md): the one image every App Engine build runs in.

- Built ONCE per server from `node:22-bookworm-slim` with every VETTED package already installed in /opt/tpl
  (`npm ci` from the committed lock file - the exact same versions on every machine, nothing `@latest`).
- A project build then runs with NO network at all: it never installs anything; its node_modules is the image's.
- A project's package.json lists only what it uses; `add_dependency` may add a name from VETTED only (the v0.497
  prog-library-registry law: never a guessed package name). Growing VETTED = a code change + an image rebuild.
- The Dockerfile text lives here (the v0.532 lesson: the VPS deploy copies `server/app` only), and the build writes it,
  package.json and the lock file into a temp folder, so it works from wherever the code runs."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

IMAGE = "hoola-appengine:base"
IMAGE_REV = "3"                       # bump with any change below; status compares it with the built image
HERE = Path(__file__).resolve().parent
LOCK = HERE / "image" / "package-lock.json"

# The template's own dependencies (every new project's package.json carries these).
CORE = {
    "react": "18.3.1", "react-dom": "18.3.1", "react-router-dom": "7.18.5", "@tanstack/react-query": "5.105.0",
    "react-hook-form": "7.91.0", "zod": "4.6.7", "@hookform/resolvers": "5.9.2", "lucide-react": "1.62.0",
    "sonner": "2.0.8", "recharts": "3.10.1", "date-fns": "4.4.0", "clsx": "2.1.1",
    "class-variance-authority": "0.7.1", "tailwind-merge": "3.7.0", "@radix-ui/react-slot": "1.5.0",
    "@radix-ui/react-dialog": "1.3.1", "@radix-ui/react-tabs": "1.2.1", "@radix-ui/react-label": "2.1.17",
    # v0.999.51 D1 THE KIT (docs/WEB_DESIGN_ENGINE_PLAN.md): the full shadcn-style kit in src/components/ui + the 39
    # section blocks use these, so every new app carries them (unused ones are not in the bundle).
    "@radix-ui/react-select": "2.4.1", "@radix-ui/react-popover": "1.3.1", "@radix-ui/react-switch": "1.4.1",
    "@radix-ui/react-checkbox": "1.4.1", "@radix-ui/react-tooltip": "1.4.1", "@radix-ui/react-accordion": "1.3.1",
    "@radix-ui/react-dropdown-menu": "2.2.1", "embla-carousel-react": "8.6.0",
    "@radix-ui/react-avatar": "1.3.1", "@radix-ui/react-separator": "1.2.0", "@radix-ui/react-scroll-area": "1.4.0",
    "@radix-ui/react-toggle": "1.2.1", "@radix-ui/react-toggle-group": "1.2.1", "@radix-ui/react-radio-group": "1.5.1",
    "@radix-ui/react-slider": "1.6.1", "@radix-ui/react-progress": "1.2.1", "@radix-ui/react-hover-card": "1.2.1",
    "@radix-ui/react-navigation-menu": "1.4.1", "@radix-ui/react-collapsible": "1.2.1",
    "@radix-ui/react-alert-dialog": "1.2.1", "@radix-ui/react-aspect-ratio": "1.2.0",
    "@radix-ui/react-context-menu": "2.4.1", "@radix-ui/react-menubar": "1.2.1",
    "cmdk": "1.1.1", "vaul": "1.1.2", "input-otp": "1.5.0", "react-day-picker": "9.14.0",
    # v0.999.326 from the awesome-react read: real data tables, a crash guard, QR codes, week / month calendars, flowcharts,
    # PDFs made in the browser, formatted text, shared state - each behind a kit part (src/components/ui), MIT / ISC, each
    # the newest release at least two weeks old when added
    "@tanstack/react-table": "9.3.1", "react-error-boundary": "6.1.6", "qrcode.react": "4.2.0",
    "react-big-calendar": "1.20.0", "@xyflow/react": "12.12.1", "@react-pdf/renderer": "4.9.0",
    "markdown-to-jsx": "9.10.6", "zustand": "5.1.0",
}
DEV = {
    "vite": "7.3.7", "@vitejs/plugin-react": "5.2.0", "tailwindcss": "4.3.3", "@tailwindcss/vite": "4.3.3",
    "typescript": "5.9.3", "@types/react": "18.3.31", "@types/react-dom": "18.3.7", "@types/node": "22.20.5",
    # v0.999.326 tests in the box: Hoola writes small tests for a screen and runs them (app_engine action=test)
    "vitest": "5.1.0", "@testing-library/react": "16.3.3", "@testing-library/dom": "10.4.2",
    "@testing-library/user-event": "14.6.10", "jsdom": "31.0.1", "@types/react-big-calendar": "1.16.3",
}
# Vetted extras: in the image, added to a project only by add_dependency (one word = one reason).
EXTRA = {
    "motion": ("12.43.0", "animation (the kit itself animates with CSS only)"),
}
VETTED = {**CORE, **{k: v[0] for k, v in EXTRA.items()}}

DOCKERFILE_TEXT = r"""# v0.999.51 Hoola App Engine - the build image (rev 3: the full kit + the awesome-react parts + tests in the box). Built once per server by `python -m app.appengine setup`.
# Every vetted package is installed here from the committed lock file; a project build runs with --network none.
FROM node:22-bookworm-slim
LABEL hoola.appengine.rev="3"
ENV NODE_ENV=development NPM_CONFIG_FUND=false NPM_CONFIG_AUDIT=false NPM_CONFIG_UPDATE_NOTIFIER=false
WORKDIR /opt/tpl
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund && npm cache clean --force && chown -R root:root /opt/tpl && chmod -R a+rX /opt/tpl
USER node
WORKDIR /tmp
CMD ["node", "-e", "console.log('hoola-appengine ready', process.version)"]
"""


def image_package() -> dict[str, Any]:
    """The package.json the image installs: core + vetted extras + the build tools."""
    return {"name": "hoola-appengine-image", "private": True, "version": "1.0.0", "type": "module",
            "dependencies": dict(sorted(VETTED.items())), "devDependencies": dict(sorted(DEV.items()))}


def project_package(name: str = "hoola-app") -> dict[str, Any]:
    return {"name": name, "private": True, "version": "0.0.0", "type": "module",
            "scripts": {"dev": "vite", "build": "vite build", "check": "tsc --noEmit -p tsconfig.json"},
            "dependencies": dict(sorted(CORE.items())), "devDependencies": dict(sorted(DEV.items()))}


def build_files(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "Dockerfile").write_text(DOCKERFILE_TEXT, "utf-8")
    (dest / "package.json").write_text(json.dumps(image_package(), indent=2) + "\n", "utf-8")
    (dest / "package-lock.json").write_bytes(LOCK.read_bytes())


PREBUILT_DOCKERFILE = DOCKERFILE_TEXT.replace(
    "COPY package.json package-lock.json ./\nRUN npm ci --no-audit --no-fund && npm cache clean --force && chown -R root:root /opt/tpl && chmod -R a+rX /opt/tpl",
    "COPY package.json package-lock.json ./\nCOPY node_modules ./node_modules\nRUN chown -R root:root /opt/tpl && chmod -R a+rX /opt/tpl")


def build(nocache: bool = False, prebuilt: str = "") -> dict[str, Any]:
    """`prebuilt` = a node_modules folder made by `npm ci` from THIS lock file on the host (for a server whose docker
    build cannot reach the npm registry; the same versions either way - the lock file decides)."""
    import shutil
    from ..devlab import box
    d = box.docker()
    if not d:
        return {"ok": False, "why": "docker is not on this server"}
    if not LOCK.exists():
        return {"ok": False, "why": "the lock file is missing from the code (appengine/image/package-lock.json)"}
    if prebuilt and not (Path(prebuilt) / "vite" / "package.json").exists():
        return {"ok": False, "why": f"{prebuilt} is not a node_modules folder made from the lock file"}
    with tempfile.TemporaryDirectory(prefix="hoola-appengine-build-") as tmp:
        build_files(Path(tmp))
        if prebuilt:
            (Path(tmp) / "Dockerfile").write_text(PREBUILT_DOCKERFILE, "utf-8")
            shutil.copytree(prebuilt, Path(tmp) / "node_modules", symlinks=True)
        argv = [d, "build", "-t", IMAGE] + (["--no-cache"] if nocache else []) + [tmp]
        rc, txt, secs = box._run(argv, 2400)
    return {"ok": rc == 0, "seconds": round(secs, 1), "image": IMAGE, "out": txt[-4000:],
            "why": "" if rc == 0 else "the image did not build (read the log)"}


def rev() -> str:
    from ..devlab import box
    d = box.docker()
    if not d:
        return ""
    rc, out, _ = box._run([d, "image", "inspect", IMAGE, "--format", "{{index .Config.Labels \"hoola.appengine.rev\"}}"], 25)
    t = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
    return "" if rc != 0 or t in ("<no value>", "<nil>") else t[:12]
