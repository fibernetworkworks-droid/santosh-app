"""HOOLA UIUX PRO MAX tool (v0.486.0) - the design database as ONE tool.

Owner: "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git ---- READ THIS REPO ---
AND FEED THIS SKILL TO HOOLA AI". Upstream (NextLevelBuilder, v2.15.0) is MIT - the engine
is vendored VERBATIM under coder/uiux/ (scripts + data, pure stdlib Python, zero pip deps,
zero network, zero brain calls): a BM25 search over 79 styles, 192 product palettes,
74 font pairings, 119 UX guidelines, 105 icons, 17 GSAP presets, 25 chart types and 22
stack CSVs, plus the --design-system aggregator (pattern + style + palette + typography +
effects + anti-patterns for a product brief). PROVENANCE.md carries the exact source.

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
import subprocess
import sys

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
          "uno", "uwp")

UIUX_SCHEMA = {
    "name": "uiux_design",
    "description": (
        "Search the LOCAL UI/UX design database before designing or reviewing any interface: "
        "79 styles, 192 color palettes, 74 font pairings, 119 UX guidelines, 25 chart types, "
        "22 stack rulebooks. Modes (pick ONE): design_system=true for a whole new page/project "
        "(returns pattern + palette + typography + anti-patterns); domain=<style|color|"
        "typography|ux|chart|landing|icons|gsap|react|web|product|google-fonts|app-interface> "
        "for one focused concern; stack=<react|nextjs|flutter|swiftui|jetpack-compose|html-"
        "tailwind|...> for framework rules. query: 2-5 meaningful words, ONE intent. "
        "persist=true saves the design system as the project's MASTER.md (page= optional "
        "override). Results are recommendations - read them, then implement."),
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
        },
        "required": ["query"],
    },
}

UIUX_TOOLS = [UIUX_SCHEMA]
UIUX_LABELS = {"uiux_design": "Design database se style/palette/font talash raha hoon"}
UIUX_HANDLERS: dict = {}


def tenant_outdir(tenant: str) -> str:
    """--output-dir is ALWAYS explicit and ALWAYS inside this tenant's own vault (upstream's
    persistence law: never cwd-relative)."""
    import re
    t = re.sub(r"[^A-Za-z0-9_-]", "_", str(tenant or "default"))[:64] or "default"
    d = os.path.join(store.root(), "uiux", t)
    os.makedirs(d, exist_ok=True)
    return d


def _run_engine(args: list[str]) -> str:
    """One blocking subprocess; honest stderr on failure; utf-8 forced (the engine's own
    Windows-cp1252 guard made explicit)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable, os.path.join(ENGINE, "search.py"), *args],
                           capture_output=True, text=True, timeout=TIMEOUT_S,
                           cwd=ENGINE, env=env)
    except subprocess.TimeoutExpired:
        return "Error: the design search timed out - narrow the query and retry once"
    out = (p.stdout or "").strip()
    if not out:
        err = (p.stderr or "").strip().splitlines()
        out = f"Error: the design search returned nothing{(' - ' + err[-1]) if err else ''}"
    return out


def _build_args(query: str, design_system: bool, domain: str | None, stack: str | None,
                max_results: int, persist: bool, project: str | None, page: str | None,
                outdir: str) -> list[str]:
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
    if persist and design_system:
        args += ["--persist", "--output-dir", outdir]   # --force is NEVER passed
        if project:
            args += ["-p", str(project)[:80]]
        if page:
            args += ["--page", str(page)[:60]]
    return args


async def uiux_design(ctx, query=None, design_system=False, domain=None, stack=None,
                      max_results=3, persist=False, project=None, page=None, **_):
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
    outdir = tenant_outdir(getattr(ctx, "tenant_id", "") or "default")
    args = _build_args(q, bool(design_system), d if not design_system else None,
                       s if not design_system else None, max_results, bool(persist),
                       project, page, outdir)
    out = await asyncio.to_thread(_run_engine, args)
    return {"query": q, "mode": ("design-system" if design_system
                                 else f"domain:{d}" if d else f"stack:{s}" if s else "auto"),
            "text": out[:OUTPUT_CAP]}


UIUX_HANDLERS["uiux_design"] = uiux_design
