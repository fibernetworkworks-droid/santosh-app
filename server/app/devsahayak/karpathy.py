"""v0.999 KARPATHY RULES for Hoola Code (owner: "feed this properly to hoola code thus to perform well. first check it
perfectly").

Source: github.com/forrestchang/andrej-karpathy-skills (also published as multica-ai/andrej-karpathy-skills), MIT,
commit 2c60614 - four rules written from Andrej Karpathy's notes on how coding models go wrong: they assume silently,
overcomplicate, change code next to the task, and stop at "looks done". The repo is only text (a CLAUDE.md, a skill, a
Cursor rule and examples); no code was taken.

What Hoola Code already did before this file (checked line by line against engine.SYSTEM):
  - read before changing, smallest change in the repo's style, prove it with a test that fails first, one question for
    a vague ask, delete scratch files, the repo formatter's whole-file rewrites put back (fmt.py).
What was missing, and is added here:
  1. THINK FIRST: say the assumptions it made, name two readings instead of picking one quietly, say so when a simpler
     way exists. The done tool gets an `assumptions` field; it is shown to her under the answer and in the PR.
  2. SIMPLE FIRST: no features, settings, abstractions or impossible-case handling she did not ask for.
  3. SURGICAL: no tidying of code next to the task; dead code is mentioned, not deleted; only orphans of its own change
     are removed. Checked IN CODE too (`drive_by`): a hunk that only changes layout (indent, spaces, quote style) or
     deletes an existing comment is named before done, once a round, and on show_diff.
  4. GOAL FIRST: every to-do step carries how it will be checked ("... -> check: ...").
The same rules reach the reviewers (own review, reality checker), editing agents and the old step loop.
Switch: `dev_karpathy` (default on).
"""
from __future__ import annotations

import difflib
import re
from typing import Any

CREDIT = "(adapted from andrej-karpathy-skills, MIT)"

RULES = """HOW TO CHANGE CODE (four rules """ + CREDIT + """ - they lean towards care; a trivial one-line job needs judgment, not ceremony):
1. Think before coding. Do not assume quietly. If her request can be read two ways, say both and ask, instead of picking
   one. If a simpler way than hers exists, say so before building the bigger one. When you go ahead on something she did
   not say (a file format, a field, the scope), put it in done `assumptions` so she sees it.
2. Simple first. Write the least code that solves what she asked. No extra features, options, settings or "flexibility"
   she did not ask for; no abstraction for code used once; no error handling for cases that cannot happen. If you wrote
   200 lines and 50 would do, rewrite it. Ask yourself: would a senior engineer call this overcomplicated?
3. Surgical changes. Touch only what the task needs. Do not "improve" nearby code, comments or formatting, and do not
   refactor what is not broken. Match the file's style even if you would write it differently. Unrelated dead code you
   notice: mention it in explain, do not delete it. Remove only the imports, variables and functions YOUR change made
   unused. Every changed line should trace back to her request.
4. Goal first. Turn the task into checks you can run: a bug = a test that reproduces it, then make it pass; "add
   validation" = tests for the bad inputs, then make them pass; a refactor = tests pass before and after. In todo_write
   give each step its check: "Fix the date parser -> check: test_parse_date passes"."""

SUB_RULES = ("When you change code: the least code that does the job, no features / options / abstractions nobody asked "
             "for, nothing next to the job tidied or reformatted, the file's own style kept, and only the leftovers of "
             "YOUR change removed. " + CREDIT)

SELF_REVIEW_EXTRA = (" Also check (5): every changed line should trace back to the task: reformatting or tidying of code next to it, a "
                     "refactor of something that was not broken, or features / settings / abstractions nobody asked for "
                     "are a comment (medium) - and so is code a senior engineer would call overcomplicated for what it does "
                     + CREDIT + ".")

REALITY_EXTRA = ("\nOne kind of extra IS a gap " + CREDIT + ": code the request did not ask for - a feature, setting or "
                 "abstraction nobody wanted, or a rewrite / reformat of code next to the task. Name it with file:line.")

# her own words asking for layout work: then layout changes are the task, not drive-by
LAYOUT_ASK = re.compile(r"(?i)\b((re-?)?format\w*|re-?indent\w*|indent\w*|whitespace|white space|lint\w*|prettier|black|ruff|"
                        r"style|tidy|clean ?up|cleanup|refactor\w*|quotes?|spaces?|tabs?|beautif\w*)\b")

_HASH = (".py", ".pyi", ".sh", ".bash", ".rb", ".yml", ".yaml", ".toml", ".r", ".pl", ".ps1", ".tf", ".cfg", ".conf", ".ini")
_SLASH = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".kt", ".kts", ".swift", ".go", ".dart", ".c", ".h",
          ".cc", ".cpp", ".hpp", ".cs", ".rs", ".scala", ".php", ".css", ".scss", ".less")


def on() -> bool:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), "dev_karpathy", True)
        return True if v is None else bool(v)
    except Exception:  # noqa: BLE001
        return True


def _norm(lines: list[str]) -> str:
    """The text with layout taken out: no whitespace at all, one quote style."""
    return re.sub(r"\s+", "", "".join(lines)).replace("'", '"').replace("`", '"')


def _comment(path: str, line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    p = path.lower()
    if p.endswith(_HASH):
        return s.startswith("#") and not s.startswith("#!")
    if p.endswith(_SLASH):
        return s.startswith(("//", "/*", "*", "*/"))
    if p.endswith((".html", ".htm", ".xml", ".vue", ".svelte", ".md")):
        return s.startswith("<!--")
    if p.endswith(".sql"):
        return s.startswith("--")
    return False


def _runs(old: list[str], new: list[str]):
    """Changed runs between two versions of a file: (old_start, removed lines, new_start, added lines)."""
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            yield i1, old[i1:i2], j1, new[j1:j2]


def _scan(path: str, old: list[str], new: list[str], nums: list[int] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def at(j: int) -> int:
        if nums is None:
            return j + 1
        return nums[j] if j < len(nums) else (nums[-1] + 1 if nums else 1)
    for i1, rem, j1, add in _runs(old, new):
        if any(x == _CUT for x in rem + add) or not any(x.strip() for x in rem + add):
            continue                                       # blank lines only (too small to name) / across two hunks
        if rem and add and _norm(rem) == _norm(add):
            out.append({"path": path, "line": at(j1), "what": f"only layout changed ({len(add)} line"
                        f"{'s' if len(add) != 1 else ''}: indent / spaces / quotes)"})
        elif rem and not add and all(_comment(path, x) or not x.strip() for x in rem):
            out.append({"path": path, "line": at(j1), "what": f"an existing comment was deleted ({len(rem)} line"
                        f"{'s' if len(rem) != 1 else ''})"})
    return out


def drive_by_files(before: dict[str, str], after: dict[str, str], skip: set[str] | None = None) -> list[dict[str, Any]]:
    """Hunks that do not change what the code does: layout only (indent, spacing, trailing spaces, quote style) or an
    existing comment deleted with nothing else in that spot. New files are never checked (all their lines are new),
    and files in `skip` (the repo's own formatter changed them) are left alone. Returns [{path, line, what}]."""
    skip = skip or set()
    out: list[dict[str, Any]] = []
    for path, new_text in after.items():
        old_text = before.get(path)
        if old_text is None or new_text is None or old_text == new_text or path in skip:
            continue
        out += _scan(path, old_text.splitlines(), new_text.splitlines())
        if len(out) >= 40:
            break
    return out[:40]


_HDR = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_CUT = "\x00hunk"                                          # keeps hunks apart so two far places never join


def drive_by(diff: str, skip: set[str] | None = None) -> list[dict[str, Any]]:
    """The same check on a git diff (the round's change), with the file's real line numbers on the new side."""
    skip = skip or set()
    files: dict[str, dict[str, Any]] = {}
    cur = None
    n = 0
    for ln in (diff or "").splitlines():
        m = _HDR.match(ln)
        if m:
            cur = m.group(2)
            files[cur] = {"old": [], "new": [], "nums": [], "new_file": False}
            continue
        if cur is None:
            continue
        f = files[cur]
        h = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", ln)
        if ln.startswith("new file mode") or ln.startswith("--- /dev/null"):
            f["new_file"] = True
        elif h:
            n = int(h.group(1))
            f["old"].append(_CUT)
            f["new"].append(_CUT)
            f["nums"].append(n)
        elif ln.startswith(("--- ", "+++ ", "index ", "similarity", "rename ", "deleted file", "old mode", "new mode",
                            "Binary files", "\\ No newline")):
            continue
        elif ln.startswith("-"):
            f["old"].append(ln[1:])
        elif ln.startswith("+"):
            f["new"].append(ln[1:])
            f["nums"].append(n)
            n += 1
        elif ln.startswith(" ") or ln == "":
            f["old"].append(ln[1:])
            f["new"].append(ln[1:])
            f["nums"].append(n)
            n += 1
    out: list[dict[str, Any]] = []
    for path, f in files.items():
        if f["new_file"] or path in skip:
            continue
        out += _scan(path, f["old"], f["new"], f["nums"])
        if len(out) >= 40:
            break
    return out[:40]


def gate_text(items: list[dict[str, Any]]) -> str:
    return ("Not finished yet - these changes do not change what the code does, so they look like tidying she did not "
            "ask for " + CREDIT + ":\n" + "\n".join(f"- {x['path']}:{x['line']} {x['what']}" for x in items[:12]) +
            "\nPut them back as they were, unless her request asked for them or your change really needed them - then "
            "keep them and say why in explain. Then call done again.")


def show_note(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return ("\n\nNote " + CREDIT + ": these spots change only layout or delete an existing comment - put them back unless "
            "she asked for them:\n" + "\n".join(f"- {x['path']}:{x['line']} {x['what']}" for x in items[:8]))


def asked_for_layout(words: str) -> bool:
    return bool(LAYOUT_ASK.search(words or ""))


def with_assumptions(explain: str, assumptions: str) -> str:
    """Her answer shows what Hoola assumed (Karpathy rule 1: say it, do not hide it)."""
    a = " ".join(str(assumptions or "").split())[:400]
    if not a or a.lower() in ("none", "nothing", "-", "n/a", "no"):
        return explain
    if a.lower() in (explain or "").lower():
        return explain
    return (explain.rstrip() + "\n\n" if (explain or "").strip() else "") + f"**I assumed:** {a}"
