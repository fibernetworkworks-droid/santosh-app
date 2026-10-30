"""v0.303 React export (web design Phase 4): the built version as a React + Vite project a developer can carry on with.

Every page of the version becomes a route component (`src/pages/*.jsx`) that renders that page's body exactly as Hoola
built it; the site's CSS, fonts, photos and scripts move to `public/assets`; `src/hoola.js` re-starts the site's motion /
forms / app script after every route change and holds the Hoola API address of the web app (if the site has one), so
logins and data keep working. Nothing secret is in the project: the API is public by design and checks every rule."""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path

BODY = re.compile(r"<body[^>]*>(.*)</body>", re.S | re.I)
TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
SCRIPTS = re.compile(r"<script\b[^>]*src=[^>]*></script>", re.I)


def _route(rel: str) -> str:
    """'index.html' -> '/', 'contact/index.html' -> '/contact/', 'hi/contact/index.html' -> '/hi/contact/'."""
    r = rel[: -len("index.html")]
    return "/" + r


def _comp(i: int) -> str:
    return f"Page{i}"


def react_zip(vdir: Path, name: str, app_api: str = "") -> bytes:
    pages = sorted(p for p in vdir.rglob("index.html") if "assets" not in p.parts)
    slug = re.sub(r"[^a-z0-9-]+", "-", (name or "website").lower()).strip("-") or "website"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        routes = []
        for i, p in enumerate(pages):
            rel = p.relative_to(vdir).as_posix()
            src = p.read_text(encoding="utf-8")
            m = BODY.search(src)
            body = m.group(1) if m else ""
            body = SCRIPTS.sub("", body)
            depth = rel.count("/")
            body = body.replace('="' + "../" * depth + "assets/", '="/assets/') if depth else body.replace('="assets/', '="/assets/')
            title = (TITLE.search(src).group(1).strip() if TITLE.search(src) else name)
            z.writestr(f"src/pages/{_comp(i)}.jsx",
                       "import { useEffect } from 'react';\nimport { restart } from '../hoola.js';\n\n"
                       f"const HTML = {json.dumps(body, ensure_ascii=False)};\n\n"
                       f"export default function {_comp(i)}() {{\n"
                       f"  useEffect(() => {{ document.title = {json.dumps(title, ensure_ascii=False)}; restart(); }}, []);\n"
                       "  return <div className=\"hoola-page\" dangerouslySetInnerHTML={{ __html: HTML }} />;\n}\n")
            routes.append((_route(rel), _comp(i)))
        imports = "".join(f"import {c} from './pages/{c}.jsx';\n" for _r, c in routes)
        rts = "".join(f"        <Route path={json.dumps(r)} element={{<{c} />}} />\n"
                      + (f"        <Route path={json.dumps(r.rstrip('/'))} element={{<{c} />}} />\n" if r != "/" else "")
                      for r, c in routes)
        z.writestr("src/main.jsx", "import React from 'react';\nimport { createRoot } from 'react-dom/client';\n"
                   "import { BrowserRouter, Routes, Route } from 'react-router-dom';\n" + imports +
                   "\ncreateRoot(document.getElementById('root')).render(\n  <BrowserRouter>\n    <Routes>\n" + rts +
                   "    </Routes>\n  </BrowserRouter>\n);\n")
        z.writestr("src/hoola.js", "// The site's own scripts (motion, forms, booking, web app) start again after every route change.\n"
                   f"export const HOOLA_APP_API = {json.dumps(app_api)};\n"
                   "export function restart() {\n"
                   "  setTimeout(() => { window.HoolaSite && window.HoolaSite.start(); window.HoolaApp && window.HoolaApp.start(); }, 0);\n}\n")
        head = (f'<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n'
                f'  <meta name="viewport" content="width=device-width,initial-scale=1">\n  <title>{name}</title>\n'
                '  <link rel="stylesheet" href="/assets/site.css">\n'
                + (f'  <meta name="hoola-app" content="{app_api}">\n' if app_api else "") +
                '</head>\n<body>\n  <div id="root"></div>\n  <script type="module" src="/src/main.jsx"></script>\n'
                '  <script src="/assets/hoola-site.js" defer></script>\n  <script src="/assets/site.js" defer></script>\n'
                + ('  <script src="/assets/hoola-app.js" defer></script>\n' if app_api else "") + '</body>\n</html>\n')
        z.writestr("index.html", head)
        z.writestr("package.json", json.dumps({
            "name": slug, "private": True, "version": "1.0.0", "type": "module",
            "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
            "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1", "react-router-dom": "^6.28.0"},
            "devDependencies": {"@vitejs/plugin-react": "^4.3.4", "vite": "^5.4.11"}}, indent=2))
        z.writestr("vite.config.js", "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\n\n"
                   "export default defineConfig({ plugins: [react()] });\n")
        for f in sorted((vdir / "assets").rglob("*")) if (vdir / "assets").exists() else []:
            if f.is_file():
                z.write(f, "public/assets/" + f.relative_to(vdir / "assets").as_posix())
        for extra in ("robots.txt", "sitemap.xml", "404.html"):
            if (vdir / extra).exists():
                z.write(vdir / extra, "public/" + extra)
        z.writestr("README.md", f"# {name}\n\nBuilt with Hoola, exported as a React + Vite project.\n\n"
                   "```\nnpm install\nnpm run dev\n```\n\nEvery page is a component in `src/pages/` that renders the page "
                   "Hoola built; styles, fonts and photos are in `public/assets/`. "
                   + ("The web app (logins, data) talks to Hoola's API at `src/hoola.js` HOOLA_APP_API; every rule is "
                      "checked on the server.\n" if app_api else "\n"))
    return buf.getvalue()
