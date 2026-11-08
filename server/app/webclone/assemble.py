"""WEB CLONE stage 2 - assemble: turn the captured bundle into a clean Next.js app-router project.

The page renders a FRAGMENT (an injected <main> broke body>-child selectors on real sites); the
captured <html>/<body> class / id / dir are carried into layout.tsx (python.org keys its CSS off
.js / #nojs). Converter laws: bs4 list attrs joined with spaces, style={{...}} double-brace with
duplicate inline props resolved last-wins (the CSS cascade), the full HTML->React attr casing map
with NUMERIC_PROPS unquoted, significant whitespace emitted as {"..."} string expressions (JSX
trims bare text at newlines), an svg lane (whitelist elements + camelCase attrs, animate/script
dropped). CSS is rewritten per file via _css_chunks: captured url()s -> /assets/<name>,
uncaptured -> the FULL absolute origin URL - webpack resolves relative refs as modules and the
build dies on them. The asset map is keyed by absolute URL AND by URL path, so root-relative
srcs (python.org 404'd every <img> without it) remap too. srcset candidates are rewritten one by
one. Original JS behaviour is static (the honest line lives in the generated README); the
bundles stay in the capture bundle for REA, never emitted into the project.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

# ---------------------------------------------------------------- attribute laws
ATTR_MAP = {
    "class": "className", "for": "htmlFor", "tabindex": "tabIndex", "readonly": "readOnly",
    "maxlength": "maxLength", "minlength": "minLength", "autocomplete": "autoComplete",
    "autofocus": "autoFocus", "autoplay": "autoPlay", "colspan": "colSpan", "rowspan": "rowSpan",
    "contenteditable": "contentEditable", "spellcheck": "spellCheck", "srcset": "srcSet",
    "imagesrcset": "imagesrcSet", "usemap": "useMap", "frameborder": "frameBorder",
    "enctype": "encType", "accept-charset": "acceptCharset", "accesskey": "accessKey",
    "allowfullscreen": "allowFullScreen", "datetime": "dateTime", "dirname": "dirName",
    "formaction": "formAction", "ismap": "isMap", "srcdoc": "srcDoc", "srclang": "srcLang",
    "novalidate": "noValidate", "playsinline": "playsInline", "referrerpolicy": "referrerPolicy",
    "crossorigin": "crossOrigin", "fetchpriority": "fetchPriority", "nomodule": "noModule",
    "cellpadding": "cellPadding", "cellspacing": "cellSpacing", "async": "async", "capture": "capture",
    "scoped": "scoped", "xlink:href": "xlinkHref", "xlink:title": "xlinkTitle", "xml:lang": "xmlLang",
    "xml:space": "xmlSpace", "acceptcharset": "acceptCharset", "checked": "defaultChecked",
    "value": "defaultValue", "selected": "defaultSelected",
}
NUMERIC_PROPS = frozenset({"colspan", "rowspan", "span", "rows", "cols", "width", "height",
                           "size", "maxlength", "minlength", "start", "tabindex", "border"})
SVG_ELEMENTS = frozenset({"svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline",
                          "polygon", "text", "tspan", "defs", "use", "symbol", "title", "desc",
                          "lineargradient", "radialgradient", "stop", "clippath", "mask",
                          "pattern", "marker", "filter", "svg", "feblend", "fecolormatrix",
                          "fecomposite", "feconvolvematrix", "fediffuselighting", "fedisplacementmap",
                          "fedistantlight", "fedropshadow", "feflood", "fefunca", "fefuncb", "fefuncg",
                          "fefuncr", "fegaussianblur", "femerge", "femergenode", "femorphology",
                          "feoffset", "fepointlight", "fespecularlighting", "fespotlight", "fetile",
                          "feturbulence", "image", "switch", "view"})
SVG_CAMEL = {"viewbox": "viewBox", "preserveaspectratio": "preserveAspectRatio",
             "gradientunits": "gradientUnits", "gradienttransform": "gradientTransform",
             "patternunits": "patternUnits", "patterncontentunits": "patternContentUnits",
             "maskunits": "maskUnits", "maskcontentunits": "maskContentUnits",
             "clippathunits": "clipPathUnits", "spreadmethod": "spreadMethod",
             "baseprofile": "baseProfile", "stitchtiles": "stitchTiles", "numoctaves": "numOctaves",
             "stddeviation": "stdDeviation", "glyphref": "glyphRef", "format": "format",
             "textlength": "textLength", "lengthadjust": "lengthAdjust", "refx": "refX", "refy": "refY",
             "markerwidth": "markerWidth", "markerheight": "markerHeight", "startoffset": "startOffset",
             "pathlength": "pathLength", "requiredextensions": "requiredExtensions",
             "systemlanguage": "systemLanguage", "zoomandpan": "zoomAndPan", "k1": "k1", "k2": "k2",
             "k3": "k3", "k4": "k4", "edgemode": "edgeMode", "values": "values"}
DROP_TAGS = frozenset({"script", "animate", "animatetransform", "animatemotion", "set"})
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
                  "param", "source", "track", "wbr"})

_UNITLESS = frozenset({"opacity", "z-index", "flex", "order", "zoom", "font-weight", "line-height",
                       "column-count", "flex-grow", "flex-shrink", "grid-column", "grid-row"})


def _camel_css_prop(prop: str) -> str:
    prop = prop.strip().lower()
    if prop.startswith("-ms-"):
        return "ms" + _camel_css_prop(prop[4:]).capitalize()
    if prop.startswith("-o-"):
        return "O" + _camel_css_prop(prop[3:])
    if prop.startswith("-moz-"):
        return "Moz" + _camel_css_prop(prop[5:])
    if prop.startswith("-webkit-"):
        return "Webkit" + _camel_css_prop(prop[8:])
    return re.sub(r"-([a-z])", lambda m: m.group(1).upper(), prop)


def style_object(style_css: str) -> str:
    """CSS inline text -> React style object source. Duplicate props: last one wins (the cascade)."""
    props: dict[str, str] = {}
    for decl in (style_css or "").split(";"):
        if ":" not in decl:
            continue
        k, v = decl.split(":", 1)
        if k.strip() and v.strip():
            props[_camel_css_prop(k)] = v.strip().replace('"', '\\"').replace("\n", " ")
    parts = []
    for k, v in props.items():
        if v.isdigit() and k.lower() in _UNITLESS:
            parts.append(f"{k}: {v}")
        else:
            parts.append(f'{k}: "{v}"')
    return "{" + ", ".join(parts) + "}"


def _jsx_text(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("{", "&#123;").replace("}", "&#125;")


def _js_str(t: str) -> str:
    return t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _attr_name(name: str, in_svg: bool) -> str | None:
    n = name.lower()
    if n.startswith(("data-", "aria-", "xmlns")):
        return n if n.startswith(("data-", "aria-")) else name
    if in_svg and n in SVG_CAMEL:
        return SVG_CAMEL[n]
    if n in ATTR_MAP:
        return ATTR_MAP[n]
    if "-" in n:                                    # unknown dashed attr -> camelCase per React law
        return re.sub(r"-([a-z])", lambda m: m.group(1).upper(), n)
    return n


def _rewrite_url(raw: str, asset_map: dict[str, str], origin: str) -> str:
    raw = raw.strip()
    if not raw or raw.startswith(("data:", "blob:", "javascript:", "#", "mailto:")):
        return raw
    if raw in asset_map:
        return asset_map[raw]
    p = urlparse(raw)
    if p.scheme or raw.startswith("//"):
        return raw if raw.startswith("//") is False else "https:" + raw
    if p.path and p.path in asset_map:              # root-relative form keyed by path
        return asset_map[p.path]
    absu = urljoin(origin + "/", raw.lstrip("/"))
    return asset_map.get(absu, asset_map.get(urlparse(absu).path, absu))


def _attr_value(el: Tag, name: str, value, asset_map: dict[str, str], origin: str) -> str:
    if isinstance(value, list):                     # bs4 multi-valued attrs (class, rel, ...) join with spaces
        value = " ".join(value)
    value = str(value)
    if name.lower() in ("src", "href", "poster", "data-src", "action"):
        return _rewrite_url(value, asset_map, origin)
    if name.lower() in ("srcset", "imagesrcset"):
        out = []
        for cand in value.split(","):
            cand = cand.strip()
            if not cand:
                continue
            bits = cand.split(" ")
            bits[0] = _rewrite_url(bits[0], asset_map, origin)
            out.append(" ".join(bits))
        return ", ".join(out)
    return value


def render_attrs(el: Tag, asset_map: dict[str, str], origin: str, in_svg: bool = False) -> str:
    """One element's attributes as JSX source. Duplicate inline style props: last wins."""
    style_css = ""
    out: list[str] = []
    for name, value in el.attrs.items():
        if name.lower() == "style":
            style_css = value if isinstance(value, str) else " ".join(value)
            continue
        rn = _attr_name(name, in_svg)
        if rn is None or rn in ("http-equiv",) and False:
            continue
        rv = _attr_value(el, name, value, asset_map, origin)
        if name.lower() in NUMERIC_PROPS and rv.strip().isdigit():
            out.append(f"{rn}={{{int(rv.strip())}}}")
        else:
            out.append(f'{rn}="{rv.replace("&", "&amp;").replace('"', "&quot;")}"')
    if style_css.strip():
        out.append(f"style={{{style_object(style_css)}}}")
    return (" " + " ".join(out)) if out else ""


def _css_chunks(css_text: str, base_url: str, asset_map: dict[str, str], origin: str) -> str:
    """Rewrite every url()/@import in one CSS file: captured -> /assets/<name>, else absolute origin."""
    def repl(m: re.Match) -> str:
        q, raw = m.group(1), m.group(2)
        return f"url({q}{_rewrite_url(raw, asset_map, origin)}{q})"

    def imp(m: re.Match) -> str:
        raw = m.group(2)
        return f"@import {m.group(1)}{_rewrite_url(raw, asset_map, origin)}{m.group(1)}"

    css_text = _CSS_URL.sub(repl, css_text)
    return re.sub(r"@import\s+(['\"])([^'\"]+)\1", imp, css_text)


_CSS_URL = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)")


def _carry_root_attrs(dom: str) -> dict[str, dict[str, str]]:
    """<html>/<body> class / id / dir / lang / data-* - the html.tsx contract (spec law)."""
    soup = BeautifulSoup(dom, "html.parser")
    out: dict[str, dict[str, str]] = {}
    for tag in ("html", "body"):
        el = soup.find(tag)
        if el is None:
            continue
        carry: dict[str, str] = {}
        for name, value in el.attrs.items():
            n = name.lower()
            if n in ("class", "id", "dir", "lang") or n.startswith("data-"):
                carry[_attr_name(name, False)] = " ".join(value) if isinstance(value, list) else str(value)
        out[tag] = carry
    return out


def html_to_jsx(dom: str, asset_map: dict[str, str], origin: str) -> str:
    """The body children as JSX source lines - the page renders a FRAGMENT, no injected <main>."""
    soup = BeautifulSoup(dom, "html.parser")
    body = soup.find("body") or soup
    lines: list[str] = []

    def walk(node, depth: int, in_svg: bool) -> None:
        pad = "  " * depth
        for child in node.children:
            if isinstance(child, Comment):
                continue
            if isinstance(child, NavigableString):
                t = str(child)
                if not t.strip():
                    if t != "\n":                      # significant inner whitespace -> string expr
                        if t.strip() != t and t.strip("\n"):
                            lines.append(f'{pad}{{"{_js_str(t)}"}}')
                    continue
                if t != t.strip() and (t[:1].isspace() or t[-1:].isspace()):
                    lines.append(f'{pad}{{"{_js_str(t)}"}}')   # JSX trims bare text at newlines
                else:
                    lines.append(pad + _jsx_text(t))
                continue
            if not isinstance(child, Tag):
                continue
            tag = (child.name or "div").lower()
            if tag in DROP_TAGS:
                continue
            in_s = in_svg or tag == "svg"
            if tag not in SVG_ELEMENTS and in_svg and tag != "svg":
                continue                                # svg lane: whitelist only
            if tag == "svg" or in_svg:
                if tag not in SVG_ELEMENTS:
                    continue
            attrs = render_attrs(child, asset_map, origin, in_svg=in_s)
            if tag in VOID:
                lines.append(f"{pad}<{tag}{attrs} />")
                continue
            kids = [c for c in child.children if not (isinstance(c, NavigableString) and not str(c).strip())]
            if not kids:
                lines.append(f"{pad}<{tag}{attrs} />")
                continue
            lines.append(f"{pad}<{tag}{attrs}>")
            walk(child, depth + 1, in_s)
            lines.append(f"{pad}</{tag}>")

    walk(body, 2, False)
    return "\n".join(lines)


def build_asset_map(manifest: dict) -> dict[str, str]:
    """Absolute URL AND URL path -> /assets/<name> (python.org 404'd every <img> without the path key)."""
    m: dict[str, str] = {}
    for entry in manifest.get("assets", []) + manifest.get("css_files", []) + manifest.get("js_files", []):
        web = "/assets/" + entry["name"]
        m[entry["url"]] = web
        m[urlparse(entry["url"]).path] = web
    return m


_TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def assemble_project(bundle_dir: Path, project_dir: Path, endpoints_md: str = "") -> dict:
    """Emit the Next.js app-router project from a capture bundle. Returns the summary dict."""
    bundle_dir, project_dir = Path(bundle_dir), Path(project_dir)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    dom = (bundle_dir / "dom.html").read_text(encoding="utf-8")
    origin = manifest["origin"]
    asset_map = build_asset_map(manifest)

    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "app").mkdir(parents=True, exist_ok=True)
    (project_dir / "public/assets").mkdir(parents=True, exist_ok=True)
    for entry in manifest.get("assets", []):
        src = bundle_dir / entry["name"]
        if src.exists():
            (project_dir / "public/assets" / entry["name"]).write_bytes(src.read_bytes())

    # ---- CSS: every captured file rewritten, concatenated in first-seen order, src markers kept
    css_out: list[str] = []
    for entry in manifest.get("css_files", []):
        src = bundle_dir / entry["name"]
        if not src.exists():
            continue
        css_out.append(f"/* src: {entry['url']} */\n" + _css_chunks(src.read_text(encoding="utf-8", errors="replace"),
                                                                   entry["url"], asset_map, origin))
    (project_dir / "app/globals.css").write_text("\n\n".join(css_out), encoding="utf-8")

    # ---- page.tsx: the FRAGMENT
    jsx = html_to_jsx(dom, asset_map, origin)
    (project_dir / "app/page.tsx").write_text(
        "export default function Page() {\n  return (\n    <>\n" + jsx + "\n    </>\n  );\n}\n",
        encoding="utf-8")

    # ---- layout.tsx: root attrs carried
    carry = _carry_root_attrs(dom)
    html_attrs = render_attrs_dict(carry.get("html", {}))
    body_attrs = render_attrs_dict(carry.get("body", {}))
    title = manifest.get("title") or ""
    if not title:
        m = _TITLE_TAG.search(dom)
        title = m.group(1).strip() if m else ""
    (project_dir / "app/layout.tsx").write_text(
        'import type { Metadata } from "next";\nimport "./globals.css";\n\n'
        "export const metadata: Metadata = {\n"
        f'  title: {json.dumps(title)},\n'
        '};\n\n'
        "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
        f"  return (\n    <html{html_attrs}>\n      <body{body_attrs}>{{children}}</body>\n    </html>\n  );\n}}\n",
        encoding="utf-8")

    slug = re.sub(r"[^a-z0-9-]+", "-", (title or "cloned-site").lower()).strip("-")[:40] or "cloned-site"
    (project_dir / "package.json").write_text(json.dumps({
        "name": slug, "private": True,
        "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
        "dependencies": {"next": "14.2.5", "react": "18.3.1", "react-dom": "18.3.1"},
    }, indent=2) + "\n", encoding="utf-8")
    (project_dir / "next.config.mjs").write_text(
        "/** Assets are plain files under /public - the Next Image optimizer would need every origin host allowlisted. */\n"
        "const nextConfig = { images: { unoptimized: true } };\nexport default nextConfig;\n", encoding="utf-8")
    (project_dir / "tsconfig.json").write_text(json.dumps({
        "compilerOptions": {"target": "ES2017", "lib": ["dom", "dom.iterable", "esnext"], "allowJs": True,
                            "skipLibCheck": True, "strict": False, "noEmit": True, "esModuleInterop": True,
                            "module": "esnext", "moduleResolution": "bundler", "resolveJsonModule": True,
                            "isolatedModules": True, "jsx": "preserve", "incremental": True},
        "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
        "exclude": ["node_modules"],
    }, indent=2) + "\n", encoding="utf-8")

    (project_dir / "README.md").write_text(
        f"# {title or 'Cloned site'}\n\n"
        f"Rebuilt from a capture of {manifest['url']} (Hoola web clone, v0.694.0).\\n\\n"
        "## Honest line\\n\\n"
        "- The page is a static rebuild of the post-JS DOM: the ORIGINAL site's JavaScript behaviour "
        "is NOT carried over (forms, menus, fetches stay as they were captured).\\n"
        "- Single page: linked pages were not followed.\\n"
        "- Not pixel-perfect on JS-heavy sites; static / semi-static pages are.\\n"
        "- CSS files keep their `/* src: ... */` origin markers.\\n\\n"
        "```bash\\nnpm install && npm run dev\\n```\\n", encoding="utf-8")
    (project_dir / "ENDPOINTS.md").write_text(endpoints_md or
                                              "Endpoints map is produced next to the project by the adapter.\\n",
                                              encoding="utf-8")

    counts = {"css_files": len(manifest.get("css_files", [])), "assets": len(manifest.get("assets", [])),
              "jsx_lines": jsx.count(chr(10)) + 1}
    summary = {"project": str(project_dir), "title": title, "url": manifest["url"], **counts}
    (project_dir / "clone-summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def render_attrs_dict(d: dict[str, str]) -> str:
    out = []
    for k, v in d.items():
        out.append(f'{k}="{v.replace("&", "&amp;").replace('"', "&quot;")}"')
    return (" " + " ".join(out)) if out else ""
