"""v0.814 what an App Engine write may and may not do - checked in CODE on every write, and on the whole app before
it goes live. Three kinds of rule:

1. PATHS: only src/ (minus the files Hoola locks), public/ (text files), index.html, AGENTS.md and .hoola/plan/*.md;
   no `..`, no hidden files, a short list of file types, a size cap per file and a file count cap per app.
2. SAFETY (always, every file): no eval / new Function / document.write / innerHTML / dangerouslySetInnerHTML, no
   outside script, no call to an outside address (the app reaches data through src/lib/hoola.ts only), and every
   package an import names must be one this app lists (from the vetted set) - never a guessed name.
3. DRIFT (the "design system first" law): colours, corners and fonts only from tokens.css - a hex / rgb / hsl colour,
   a Tailwind palette colour (bg-blue-500, text-white) or a one-off `[value]` class is refused, with the token to use.
4. TASTE (v0.999.51 D1): no transition-all, no browser select / date box / alert, no emoji icons, no gradient on a
   button, at most 3 gradients a file.

A refusal names the file, the line and what to write instead, so the model can fix it in one go."""
from __future__ import annotations

import json
import posixpath
import re
from typing import Any

LOCKED = {"package.json", "package-lock.json", "vite.config.ts", "vitest.config.ts", "vitest.setup.ts", "hoola.plugin.mjs", "tsconfig.json", "src/main.tsx", "src/index.css",
          "src/lib/hoola.ts", "src/lib/utils.ts", "src/styles/tokens.css", "src/lib/cloud.types.ts", "DESIGN.md",
          # v0.999.64 D3: pre-rendering + islands
          "hoola.prerender.mjs", "hoola.render.json", "src/entry-server.tsx", "src/islands-entry.tsx", "src/islands-wake.tsx",
          "src/lib/island.tsx",
          "src/lib/seo.tsx",
          # v0.999.82 D8: the only place a page may keep a value in the visitor's browser (a website on its own address)
          "src/lib/keep.ts",
          # v0.999.82 D8 wave 7: the visitor's sign-in on her website (her members, her rules on Hoola)
          "src/lib/member.ts",
          # v0.999.91 D8 wave 9: the browser-notification worker, served from her website's own address
          "public/hoola-push-sw.js",
          # v0.999.334 numbers / money / dates in the app's country - set with app_engine action=locale, never by hand
          "src/lib/format.ts", "src/lib/locale.ts"}
TEXT_EXT = {".tsx", ".ts", ".css", ".json", ".svg", ".md", ".txt", ".html", ".webmanifest"}
CODE_EXT = {".tsx", ".ts", ".css"}
MAX_FILE = 200_000
MAX_FILES = 400
_PALETTE = ("slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|"
            "violet|purple|fuchsia|pink|rose")
_UTIL = r"(?:bg|text|border(?:-[trblxy])?|ring|ring-offset|from|to|via|fill|stroke|outline|decoration|shadow|accent|caret|divide|placeholder)"
RX_PALETTE = re.compile(rf"(?<![\w-]){_UTIL}-(?:(?:{_PALETTE})-\d{{2,3}}|white|black)(?:/\d{{1,3}})?(?![\w-])")
RX_ARB = re.compile(r"(?<![\w-])(?:[a-z][a-z0-9]*(?:-[a-z0-9]+)*:)*-?[a-z][a-z0-9-]*-\[[^\]\s]+\]")
RX_ARB_OK = re.compile(r"data-\[|aria-\[|supports-\[|group-\[|peer-\[|has-\[|\[&")
RX_HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])")
RX_FUNC = re.compile(r"\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb)\(")
RX_UNSAFE = [
    (re.compile(r"\beval\s*\("), "eval() runs text as code"),
    (re.compile(r"\bnew\s+Function\s*\("), "new Function() runs text as code"),
    (re.compile(r"\bdocument\.write\s*\("), "document.write() is not used in this template"),
    (re.compile(r"\.innerHTML\s*="), "setting innerHTML puts raw HTML on the page; render it with React"),
    (re.compile(r"\.outerHTML\s*="), "setting outerHTML puts raw HTML on the page; render it with React"),
    (re.compile(r"dangerouslySetInnerHTML"), "dangerouslySetInnerHTML puts raw HTML on the page; render it with React"),
    (re.compile(r"""\b(?:fetch|EventSource|WebSocket)\s*\(\s*[`'"](?:https?:|wss?:)?//"""),
     "the app reaches data only through src/lib/hoola.ts (Hoola Cloud), never an outside address"),
    (re.compile(r"""\bimport\s*\(\s*[`'"]https?:"""), "code is never loaded from an outside address"),
    (re.compile(r"""\bfrom\s+[`'"]https?:"""), "code is never loaded from an outside address"),
    (re.compile(r"\bXMLHttpRequest\b"), "the app reaches data only through src/lib/hoola.ts (Hoola Cloud)"),
    (re.compile(r"\b(?:localStorage|sessionStorage|indexedDB)\b|\bdocument\.cookie\b"),
     "the app runs in a sealed frame where browser storage and cookies do not exist - keep data in Hoola Cloud "
     "(hoola.db) or in React state; sign-in is hoola.auth"),
]
RX_IMPORT = re.compile(r"""(?:^|[\s;])(?:import|export)\s+(?:[^'"`;]*?\s+from\s+)?['"]([^'"]+)['"]|\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)""",
                       re.M)
RX_CSS_IMPORT = re.compile(r"""@import\s+(?:url\()?['"]?([^'")\s;]+)""")
RX_SCRIPT = re.compile(r"<script\b[^>]*>", re.I)
RX_SRC = re.compile(r"""\bsrc\s*=\s*['"]([^'"]+)['"]""", re.I)
RX_LINK_HREF = re.compile(r"""<link\b[^>]*\bhref\s*=\s*['"](https?:)?//""", re.I)
HINT = ("use the tokens: bg-bg / bg-surface / bg-primary / text-ink / text-muted / text-primary / border-line / "
        "bg-accent / text-ok / text-warn / text-bad (opacity like bg-ink/40 is fine), and the spacing / type scale "
        "(p-4, text-sm) - change the look of a shared part in its cva variants")


class RuleError(Exception):
    def __init__(self, msg: str, problems: list[dict[str, Any]] | None = None):
        super().__init__(msg)
        self.problems = problems or []


def norm(path: str) -> str:
    p = str(path or "").strip().replace("\\", "/").lstrip("/")
    if p.startswith("./"):
        p = p[2:]
    q = posixpath.normpath(p) if p else ""
    if not q or q == "." or q.startswith("..") or "/../" in f"/{q}/" or "\0" in q:
        raise RuleError(f"'{path}' is not a path inside the app.")
    return q


def ext(path: str) -> str:
    b = path.rsplit("/", 1)[-1]
    return ("." + b.rsplit(".", 1)[-1].lower()) if "." in b else ""


def writable(path: str) -> str:
    """The normalised path if Hoola may write it, else a RuleError saying why and what to do."""
    p = norm(path)
    if p in LOCKED:
        how = {"package.json": "add a package with action=add_dependency",
               "src/styles/tokens.css": "change colours / corners / fonts with action=tokens or action=design_new",
               "DESIGN.md": "change the design with action=design_new (genes) or action=design_import (a whole DESIGN.md)",
               "hoola.render.json": "choose how pages go out with action=render_mode (site or app)"}.get(
                   p, "it is part of the template Hoola keeps")
        raise RuleError(f"{p} is locked: {how}.")
    parts = p.split("/")
    if any(x.startswith(".") for x in parts) and not (p.startswith(".hoola/plan/") and p.endswith(".md") and len(parts) == 3):
        raise RuleError(f"{p}: hidden files are not part of the app (plans go in .hoola/plan/<name>.md).")
    if p not in ("index.html", "AGENTS.md") and parts[0] not in ("src", "public", ".hoola"):
        raise RuleError(f"{p}: app files live in src/ (code), public/ (files served as they are), index.html or AGENTS.md.")
    e = ext(p)
    if e not in TEXT_EXT:
        raise RuleError(f"{p}: a {e or 'no-extension'} file cannot be written here (allowed: {', '.join(sorted(TEXT_EXT))}).")
    if parts[0] == "src" and e not in CODE_EXT | {".json", ".svg", ".md"}:
        raise RuleError(f"{p}: src/ takes .tsx / .ts / .css / .json / .svg files.")
    if p == "index.html" or (parts[0] != "public" and e == ".html"):
        if p != "index.html":
            raise RuleError(f"{p}: the app has one page file (index.html); screens are React pages in src/pages/.")
    return p


def _lines(code: str) -> list[str]:
    return code.splitlines() or [""]


def _strip_comments(line: str) -> str:
    i = line.find("//")
    while i >= 0:                                   # keep "https://" inside a string
        if i == 0 or line[i - 1] not in ":\"'`":
            return line[:i]
        i = line.find("//", i + 2)
    return line


def drift(path: str, code: str) -> list[dict[str, Any]]:
    """Design drift in one file (never tokens.css): raw colours, palette colours, one-off [values]."""
    p, e = norm(path), ext(path)
    if p == "src/styles/tokens.css" or e not in CODE_EXT and p != "index.html":
        return []
    out: list[dict[str, Any]] = []
    for n, raw in enumerate(_lines(code), 1):
        line = _strip_comments(raw) if e in (".ts", ".tsx") else raw
        for m in RX_HEX.finditer(line):
            before = line[max(0, m.start() - 8):m.start()]
            if re.search(r"""(?:href|to|id)=["'{]?$""", before) or before.endswith(("href=", "to=")):
                continue                            # a link to a section (#faq), not a colour
            out.append({"file": p, "line": n, "rule": "raw colour", "found": m.group(0)})
        for m in RX_FUNC.finditer(line):
            out.append({"file": p, "line": n, "rule": "raw colour", "found": line[m.start():m.start() + 18]})
        if e in (".tsx", ".ts", ".html") or e == ".css":
            for m in RX_PALETTE.finditer(line):
                out.append({"file": p, "line": n, "rule": "palette colour", "found": m.group(0)})
            for m in RX_ARB.finditer(line):
                s = m.group(0)
                if RX_ARB_OK.search(s):
                    continue
                if e == ".css" and "@apply" not in line:
                    continue                         # plain CSS has no utility classes; [..] there is a selector
                out.append({"file": p, "line": n, "rule": "one-off value", "found": s})
    return out


def safety(path: str, code: str, deps: set[str]) -> list[dict[str, Any]]:
    p, e = norm(path), ext(path)
    out: list[dict[str, Any]] = []
    if e in (".ts", ".tsx"):
        for n, raw in enumerate(_lines(code), 1):
            line = _strip_comments(raw)
            for rx, why in RX_UNSAFE:
                if rx.search(line):
                    out.append({"file": p, "line": n, "rule": "unsafe", "found": why})
        for m in RX_IMPORT.finditer(code):
            spec = m.group(1) or m.group(2) or ""
            n = code.count("\n", 0, m.start()) + 1
            why = _import_problem(p, spec, deps)
            if why:
                out.append({"file": p, "line": n, "rule": "import", "found": why})
    elif e == ".css":
        for m in RX_CSS_IMPORT.finditer(code):
            spec = m.group(1)
            if spec.startswith(("http:", "https:", "//")):
                out.append({"file": p, "line": code.count("\n", 0, m.start()) + 1, "rule": "unsafe",
                            "found": "CSS is never loaded from an outside address"})
    elif p == "index.html":
        for m in RX_SCRIPT.finditer(code):
            tag = m.group(0)
            src = RX_SRC.search(tag)
            n = code.count("\n", 0, m.start()) + 1
            if not src or src.group(1) != "/src/main.tsx" or "module" not in tag:
                out.append({"file": p, "line": n, "rule": "unsafe",
                            "found": "index.html keeps only its one <script type=\"module\" src=\"/src/main.tsx\">; code goes in src/"})
        for m in RX_LINK_HREF.finditer(code):
            out.append({"file": p, "line": code.count("\n", 0, m.start()) + 1, "rule": "unsafe",
                        "found": "nothing is loaded from an outside address (fonts come from tokens.css)"})
        if re.search(r"\bon[a-z]+\s*=", code, re.I):
            out.append({"file": p, "line": 1, "rule": "unsafe", "found": "no inline event handlers in index.html"})
    elif e == ".svg":
        if re.search(r"<script|\bon[a-z]+\s*=|javascript:", code, re.I):
            out.append({"file": p, "line": 1, "rule": "unsafe", "found": "an SVG file may not carry script"})
    if e == ".json":
        try:
            json.loads(code)
        except ValueError as er:
            out.append({"file": p, "line": 1, "rule": "json", "found": f"not valid JSON: {er}"})
    return out


TEST_PKGS = {"vitest", "@testing-library/react", "@testing-library/dom", "@testing-library/user-event"}


def is_test(path: str) -> bool:
    p = norm(path) if path else ""
    return p.startswith("src/") and bool(re.search(r"\.test\.(ts|tsx)$", p))


def _pkg_of(spec: str) -> str:
    if spec.startswith("@"):
        return "/".join(spec.split("/")[:2])
    return spec.split("/")[0]


def _import_problem(path: str, spec: str, deps: set[str]) -> str:
    if not spec:
        return ""
    if spec.startswith(("./", "../")):
        target = posixpath.normpath(posixpath.join(posixpath.dirname(path), spec))
        if not target.startswith("src/"):
            return f"'{spec}' points outside src/"
        return ""
    if spec.startswith("@/"):
        return ""
    if spec.startswith(("http:", "https:", "//", "/")):
        return f"'{spec}': code is imported from the app's own files or its packages only"
    if spec.startswith("node:"):
        return f"'{spec}': Node's own modules do not run in the browser"
    name = _pkg_of(spec)
    # v0.999.326 the test tools exist only in a test file (src/**/*.test.ts / .tsx); they never ship to visitors
    if name in TEST_PKGS:
        return "" if is_test(path) else (f"'{name}' is for tests only: use it in a file named like Screen.test.tsx")
    if name in deps or name in ("react", "react-dom"):
        return ""
    from .image import VETTED, EXTRA
    if name in EXTRA:
        return f"'{name}' is vetted but not added to this app yet: run action=add_dependency package={name} first"
    if name in VETTED:
        return ""
    return (f"'{name}' is not a vetted package. Use what the template has (react-router-dom, @tanstack/react-query, "
            "react-hook-form, zod, lucide-react, sonner, recharts, date-fns, the src/components/ui kit) or one of: "
            + ", ".join(sorted(EXTRA)))


# v0.999.51 D1 THE KIT: Emergent's hard taste rules, in code (docs/WEB_DESIGN_ENGINE_PLAN.md P1). Each names the kit
# part to use instead, so the model fixes it in one go.
RX_TRANS_ALL = re.compile(r"(?<![\w-])transition-all(?![\w-])|\btransition\s*:\s*all\b|transition-property\s*:\s*all\b")
RX_SELECT = re.compile(r"<select\b")
RX_DATE = re.compile(r"""<[Ii]nput\b[^>]*\btype\s*=\s*[{]?["'](?:date|time|datetime-local|month|week)["']""")
RX_DIALOG = re.compile(r"(?<![\w.$])(?:window\.)?(?:alert|confirm|prompt)\s*\(|\bwindow\.(?:alert|confirm|prompt)\s*\(")
RX_DIALOG_DEF = re.compile(r"(?:function|const|let|var)\s+(?:alert|confirm|prompt)\b|(?<!window)\.(?:alert|confirm|prompt)\s*\(")
RX_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\u2B50\u2B55\u231A\u231B\u23E9-\u23FA\uFE0F]")
RX_GRAD = re.compile(r"(?<![\w-])bg-(?:gradient-to|linear|radial|conic)-[\w-]+|\b(?:linear|radial|conic)-gradient\(")
RX_BTN = re.compile(r"<(?:Button|button)\b")
MAX_GRADIENTS = 3


def taste(path: str, code: str) -> list[dict[str, Any]]:
    """The taste rules (code files only): name what animates, kit parts instead of the browser's own select / date /
    dialogs, icons from lucide-react not emoji, never a gradient on a button and few gradients per file."""
    p, e = norm(path), ext(path)
    if e not in (".tsx", ".ts", ".css"):
        return []
    out: list[dict[str, Any]] = []
    grads = 0
    for n, raw in enumerate(_lines(code), 1):
        line = _strip_comments(raw) if e in (".ts", ".tsx") else raw
        if RX_TRANS_ALL.search(line):
            out.append({"file": p, "line": n, "rule": "taste", "found": "transition-all animates everything (slow, jumpy): "
                        "name what moves - transition-colors / transition-opacity / transition-transform / transition-shadow"})
        g = len(RX_GRAD.findall(line))
        grads += g
        if g and RX_BTN.search(line):
            out.append({"file": p, "line": n, "rule": "taste", "found": "never a gradient on a button: use the Button "
                        "variants (bg-primary)"})
        if e == ".css":
            continue
        if RX_SELECT.search(line):
            out.append({"file": p, "line": n, "rule": "taste", "found": "the browser's own <select> looks different "
                        "everywhere: use the kit's Select from @/components/ui/select"})
        if RX_DATE.search(line):
            out.append({"file": p, "line": n, "rule": "taste", "found": "the browser's own date / time box: use the kit's "
                        "DatePicker from @/components/ui/date-picker"})
        if RX_DIALOG.search(line) and not RX_DIALOG_DEF.search(line):
            out.append({"file": p, "line": n, "rule": "taste", "found": "the browser's own alert / confirm / prompt box: "
                        "use toast from sonner or the kit's AlertDialog"})
        if e == ".tsx" and RX_EMOJI.search(line):
            out.append({"file": p, "line": n, "rule": "taste", "found": f"an emoji ({RX_EMOJI.search(line).group(0)}) is "
                        "not an icon here: use a lucide-react icon"})
    if grads > MAX_GRADIENTS:
        out.append({"file": p, "line": 1, "rule": "taste", "found": f"{grads} gradients in one file (at most "
                    f"{MAX_GRADIENTS}: a gradient is an accent, not the page)"})
    return out


def check_file(path: str, code: str, deps: set[str]) -> list[dict[str, Any]]:
    return safety(path, code, deps) + drift(path, code) + taste(path, code)


def say(problems: list[dict[str, Any]], limit: int = 8) -> str:
    rows = [f"{x['file']}:{x['line']} {x['rule']} - {x['found']}" for x in problems[:limit]]
    more = f" (+{len(problems) - limit} more)" if len(problems) > limit else ""
    tail = f" Fix: {HINT}." if any(x["rule"] in ("raw colour", "palette colour", "one-off value") for x in problems) else ""
    return "; ".join(rows) + more + "." + tail
