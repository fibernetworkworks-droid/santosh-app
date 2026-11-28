"""HOOLA UIUX PRO MAX tool (v0.486.0) - the design database as ONE tool.

Owner: "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git ---- READ THIS REPO ---
AND FEED THIS SKILL TO HOOLA AI". Upstream (NextLevelBuilder, v2.15.0) is MIT - the engine
is vendored VERBATIM under coder/uiux/ (scripts + data, pure stdlib Python, zero pip deps,
zero network, zero brain calls): a BM25 search over 80 styles, 194 product palettes,
74 font pairings, 141 UX guidelines, 105 icons, 20 motion presets, 25 chart types and 23
stack CSVs, plus the --design-system aggregator (pattern + style + palette + typography +
effects + anti-patterns for a product brief). PROVENANCE.md carries the exact source.

v0.999.329: the engine + data updated to upstream 11ca2b3 (27 Nov 2026), and the tool now
passes what the engine could already do: the three dials (variance / motion / density),
design tokens (css / dtcg) and a preview page of the design system (right to left too),
which is written into her vault and handed to her chat as a file card she opens.

The seed skill uiux-pro-max.md (skillpack/) teaches her WHEN; this tool is HOW.

Safety rails, all house law:
- coder_enabled + coder_uiux gates (the owner can switch the database off).
- Everything blocking runs in asyncio.to_thread (the scrape-tools pattern).
- One subprocess per call, timeout 30 s, query capped at 400 chars, output capped at 24k.
- --persist writes ONLY under the tenant's own vault dir (never cwd-relative - the
  upstream MASTER.md law), and --force is NEVER passed: an existing MASTER.md is never
  silently overwritten (upstream's own guard does the skip-and-say-so).
- Results are RECOMMENDATIONS, never instructions (upstream's contract, kept verbatim);
  a 0-result search comes back as an honest empty, never fabricated.
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import time

from . import store

ENGINE = os.path.join(os.path.dirname(__file__), "uiux", "scripts")
TIMEOUT_S = 30
QUERY_CAP = 400
OUTPUT_CAP = 24_000

DOMAINS = ("style", "color", "typography", "google-fonts", "chart", "landing", "product",
           "ux", "icons", "gsap", "react", "web", "app-interface")
STACKS = ("react", "nextjs", "vue", "svelte", "astro", "nuxtjs", "nuxt-ui", "angular",
          "laravel", "swiftui", "react-native", "flutter", "jetpack-compose",
          "html-tailwind", "shadcn", "threejs", "javafx", "wpf", "winui", "avalonia",
          "uno", "uwp", "pyside6-qss")
TOKENS = ("css", "dtcg")

UIUX_SCHEMA = {
    "name": "uiux_design",
    "description": (
        "Search the LOCAL UI/UX design database before designing or reviewing any interface: "
        "80 styles, 194 color palettes, 74 font pairings, 141 UX guidelines (incl. form errors and "
        "maps), 25 chart types, 23 stack rulebooks; a hex colour finds its palette. Modes (pick ONE): design_system=true for a whole new page/project "
        "(returns pattern + palette + typography + anti-patterns); domain=<style|color|"
        "typography|ux|chart|landing|icons|gsap|react|web|product|google-fonts|app-interface> "
        "for one focused concern; stack=<react|nextjs|flutter|swiftui|jetpack-compose|html-"
        "tailwind|...> for framework rules. query: 2-5 meaningful words, ONE intent. "
        "persist=true saves the design system as the project's MASTER.md (page= optional "
        "override). With design_system only: variance / motion / density 1-10 dials "
        "(1 = centred, subtle, spacious; 10 = bold, lively, dense), tokens=css|dtcg returns "
        "the design tokens, preview=true puts a preview page of the design system in her chat "
        "(lang / direction=rtl for Arabic, Hebrew, Urdu). Results are recommendations - read "
        "them, then implement."),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string",
                      "description": "2-5 meaningful terms, one dominant intent "
                                     "(e.g. 'keyboard focus modal', 'beauty spa wellness')"},
            "design_system": {"type": "boolean",
                              "description": "true = full product design system (new page/project)"},
            "domain": {"type": "string", "enum": list(DOMAINS),
                       "description": "one focused concern (instead of design_system)"},
            "stack": {"type": "string", "enum": list(STACKS),
                      "description": "framework rulebook (instead of design_system)"},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 10,
                            "description": "rows to return, default 3"},
            "persist": {"type": "boolean",
                        "description": "with design_system: save MASTER.md for retrieval across sessions"},
            "project": {"type": "string", "description": "project name for persist (-p)"},
            "page": {"type": "string", "description": "page-specific override file for persist"},
            "variance": {"type": "integer", "minimum": 1, "maximum": 10,
                         "description": "design_system only: 1 centred/minimal .. 10 bold/asymmetric"},
            "motion": {"type": "integer", "minimum": 1, "maximum": 10,
                       "description": "design_system only: 1 subtle .. 10 complex motion"},
            "density": {"type": "integer", "minimum": 1, "maximum": 10,
                        "description": "design_system only: 1 spacious .. 10 dense / dashboard"},
            "tokens": {"type": "string", "enum": list(TOKENS),
                       "description": "design_system only: return the design tokens as CSS "
                                      "variables (css) or W3C design tokens JSON (dtcg)"},
            "preview": {"type": "boolean",
                        "description": "design_system only: put a preview page of the design "
                                       "system in her chat"},
            "lang": {"type": "string", "description": "preview language tag, e.g. ar, he, ur, hi"},
            "direction": {"type": "string", "enum": ["ltr", "rtl"],
                          "description": "preview text direction"},
        },
        "required": ["query"],
    },
}

UIUX_TOOLS = [UIUX_SCHEMA]
UIUX_LABELS = {"uiux_design": "Searching the design database for styles, palettes and fonts"}
UIUX_HANDLERS: dict = {}


def tenant_outdir(tenant: str) -> str:
    """--output-dir is ALWAYS explicit and ALWAYS inside this tenant's own vault (upstream's
    persistence law: never cwd-relative)."""
    import re
    t = re.sub(r"[^A-Za-z0-9_-]", "_", str(tenant or "default"))[:64] or "default"
    d = os.path.join(store.root(), "uiux", t)
    os.makedirs(d, exist_ok=True)
    return d


def _run_engine(args: list[str], with_err: bool = False):
    """One blocking subprocess; honest stderr on failure; utf-8 forced (the engine's own
    Windows-cp1252 guard made explicit). with_err=True returns (stdout, stderr): with --tokens the
    engine prints its persist / preview notes on stderr."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable, os.path.join(ENGINE, "search.py"), *args],
                           capture_output=True, text=True, timeout=TIMEOUT_S,
                           cwd=ENGINE, env=env)
    except subprocess.TimeoutExpired:
        out = "Error: the design search timed out - narrow the query and retry once"
        return (out, "") if with_err else out
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    if not out:
        last = err.splitlines()
        out = f"Error: the design search returned nothing{(' - ' + last[-1]) if last else ''}"
    return (out, err) if with_err else out


def _dial(v) -> int | None:
    """A 1-10 dial; anything else is left out (never guessed)."""
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 10 else None


def _build_args(query: str, design_system: bool, domain: str | None, stack: str | None,
                max_results: int, persist: bool, project: str | None, page: str | None,
                outdir: str, variance=None, motion=None, density=None, tokens: str | None = None,
                preview_dir: str | None = None, lang: str | None = None,
                direction: str | None = None) -> list[str]:
    args = [query]
    if design_system:
        args.append("--design-system")
    elif domain:
        args += ["--domain", str(domain)]
    elif stack:
        args += ["--stack", str(stack)]
    try:
        n = int(max_results or 3)
    except (TypeError, ValueError):
        n = 3
    args += ["-n", str(max(1, min(10, n)))]
    if design_system:
        for flag, v in (("--variance", variance), ("--motion", motion), ("--density", density)):
            d = _dial(v)
            if d is not None:
                args += [flag, str(d)]
        if tokens in TOKENS:
            args += ["--tokens", tokens]
        if lang:
            args += ["--lang", str(lang)[:12]]
        if direction in ("ltr", "rtl"):
            args += ["--direction", direction]
    if persist and design_system:
        args += ["--persist", "--output-dir", outdir]   # --force is NEVER passed
        if project:
            args += ["-p", str(project)[:80]]
        if page:
            args += ["--page", str(page)[:60]]
        if preview_dir is not None:
            args.append("--preview")                    # lands beside MASTER.md, never overwritten
    elif design_system and preview_dir:
        args += ["--preview", "--output-dir", preview_dir]   # a fresh folder per preview
        if project:
            args += ["-p", str(project)[:80]]
    return args


_PREVIEW_AT = re.compile(r"Design system preview:\s*(\S+\.html)")


def _preview_file(text: str, roots: list[str]) -> str | None:
    """The preview page the engine says it wrote - only when it lies inside her own vault."""
    m = _PREVIEW_AT.search(text or "")
    if not m:
        return None
    path = os.path.realpath(m.group(1))
    for r in roots:
        r = os.path.realpath(r)
        if path.startswith(r + os.sep) and os.path.isfile(path):
            return path
    return None


def _hand_preview(ctx, path: str, title: str) -> dict:
    """The preview page into her chat as a file card she opens (the house pc_file card)."""
    from .. import chatfiles
    from ..events import bus
    tenant = getattr(ctx, "tenant_id", "") or "default"
    with open(path, "rb") as f:
        data = f.read()
    card = chatfiles.store(tenant, "design-system-preview.html", data, "text/html")
    conv = getattr(ctx, "conversation_id", "") or ""
    if conv:
        bus.publish(conv, "pc_file", {**card, "source": "uiux", "title": title})
    return card


async def uiux_design(ctx, query=None, design_system=False, domain=None, stack=None,
                      max_results=3, persist=False, project=None, page=None, variance=None,
                      motion=None, density=None, tokens=None, preview=False, lang=None,
                      direction=None, **_):
    """The one design-database surface. Zero model cost, fail-open honest errors."""
    from ..config import get_settings
    st = get_settings()
    if not getattr(st, "coder_enabled", True) or not getattr(st, "coder_uiux", True):
        return {"error": "the design database is switched off (coder_uiux)"}
    q = str(query or "").strip()[:QUERY_CAP]
    if not q:
        return {"error": "query is required (2-5 meaningful words, one intent)"}
    d = str(domain or "").strip().lower() or None
    s = str(stack or "").strip().lower() or None
    if d and d not in DOMAINS:
        return {"error": f"unknown domain {d!r} - one of: {', '.join(DOMAINS)}"}
    if s and s not in STACKS:
        return {"error": f"unknown stack {s!r} - one of: {', '.join(STACKS)}"}
    tk = str(tokens or "").strip().lower() or None
    if tk and tk not in TOKENS:
        return {"error": f"unknown tokens format {tk!r} - one of: {', '.join(TOKENS)}"}
    dr = str(direction or "").strip().lower() or None
    if dr and dr not in ("ltr", "rtl"):
        return {"error": "direction is ltr or rtl"}
    lg = str(lang or "").strip()
    if lg and not re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})?", lg):
        return {"error": "lang is a language tag such as ar, he, ur or hi"}
    ds = bool(design_system)
    extras = [k for k, v in (("variance", variance), ("motion", motion), ("density", density),
                             ("tokens", tk), ("preview", preview), ("lang", lg),
                             ("direction", dr)) if v]
    if extras and not ds:
        return {"error": f"{', '.join(extras)} work only with design_system=true"}
    outdir = tenant_outdir(getattr(ctx, "tenant_id", "") or "default")
    pdir = None
    if ds and preview:
        pdir = "" if persist else os.path.join(outdir, "previews",
                                               time.strftime("%Y%m%d-%H%M%S") + f"-{os.getpid()}")
        if pdir:
            os.makedirs(pdir, exist_ok=True)
    args = _build_args(q, ds, d if not ds else None, s if not ds else None, max_results,
                       bool(persist), project, page, outdir, variance=variance, motion=motion,
                       density=density, tokens=tk, preview_dir=pdir, lang=lg or None,
                       direction=dr)
    out, err = await asyncio.to_thread(_run_engine, args, True)
    res = {"query": q, "mode": ("design-system" if ds
                                else f"domain:{d}" if d else f"stack:{s}" if s else "auto"),
           "text": out[:OUTPUT_CAP]}
    if tk:
        res["tokens"] = tk
    if ds and preview:
        path = _preview_file(out + "\n" + err, [outdir])
        if path:
            try:
                card = await asyncio.to_thread(_hand_preview, ctx, path,
                                               f"Design system preview - {project or q}"[:80])
                res["preview"] = {"file_id": card.get("file_id", ""),
                                  "note": "the preview page is in her chat as a file card"}
            except Exception as e:  # the design text still answers
                res["preview"] = {"error": f"the preview page could not be shared: {e}"}
        else:
            skipped = "already exists" in (out + err)
            res["preview"] = {"error": ("a preview page for this project is already saved and was "
                                        "not overwritten" if skipped
                                        else "the engine wrote no preview page")}
    return res


UIUX_HANDLERS["uiux_design"] = uiux_design
