"""v0.999 SUPERPOWERS for Hoola Code (owner: "https://github.com/obra/superpowers.git --- read this first then make hoola
code more powerfull with this").

Source: obra/superpowers v7.0.2 (commit 22f0b46, MIT, Jesse Vincent), read whole: 15 skills + their prompts and
references. Hoola already carried an older condensed copy (v0.499, `coder/skillpack/sp-*.md`) - but only for the CHAT's
skill desk: Hoola Code never listed them, never picked one, and nothing enforced their rules. What this file adds:

1. Hoola Code's OWN skill library (`devsahayak/superpowers/*.md`): 13 of the skills rewritten for Hoola Code's tools
   (agent / isolation=worktree / agent_worktree / todo_write / ask_user / done; merging is her tap). Left out:
   using-superpowers (it is the rule below) and diagnosing-superpowers (it debugs the plugin itself).
2. THE RULE (using-superpowers): every skill's name + when-to-use rides in the fixed prompt; before acting, a skill that
   fits is read with the skill tool and followed, announced in one line. Her words and the repo's rules win.
3. PICKED IN CODE, not left to memory: her round's kind and words choose the process skills (a bug -> systematic-
   debugging + test-driven-development, a change -> test-driven-development, reviewers' comments -> receiving-code-
   review) and their full text rides with her message, once per session. Her commands /brainstorm, /write-plan and
   /execute-plan load brainstorming / writing-plans / subagent-driven-development (or executing-plans).
4. TWO IRON LAWS CHECKED IN CODE: (a) verification-before-completion - done that claims passing / fixed / works after
   code was edited and no test or build command passed since that edit is sent back once to run it fresh; (b)
   systematic-debugging's 3-fix rule - the third failing test run in a row, each after a fix attempt (an edit outside the
   tests), tells it to stop fixing and question the approach or ask her.
Switch: `dev_superpowers` (default on).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

CREDIT = "(adapted from Superpowers, MIT)"
DIR = Path(__file__).with_name("superpowers")
_CACHE: dict[str, dict[str, str]] = {}

TEST_CMD = re.compile(r"(?i)(^|[\s;&|(])(pytest|py\.test|python3? -m (pytest|unittest)|tox|nox|(npm|pnpm|yarn|bun)( run)? "
                      r"(test|build|lint|typecheck|check)\b|npx (jest|vitest|tsc|eslint|playwright)|jest|vitest|mocha|"
                      r"go (test|build|vet)|cargo (test|build|check|clippy)|mvn|gradle|\./gradlew|flutter (test|analyze)|"
                      r"dart (test|analyze)|make (test|check|build|lint)|rspec|bundle exec rake|phpunit|ctest|dotnet "
                      r"(test|build)|tsc|ruff|mypy|eslint|swift (test|build)|xcodebuild)\b")
TEST_PATH = re.compile(r"(?i)(^|/)(tests?|spec|__tests__)(/|$)|(^|/)test_[^/]*$|_test\.\w+$|\.(test|spec)\.\w+$")
DOC_PATH = re.compile(r"(?i)\.(md|mdx|rst|txt|adoc)$|(^|/)docs?/")
CLAIM = re.compile(r"(?i)\b(all )?(tests? )?(pass(es|ed|ing)?|green|fixed|works?|working|succeed(s|ed)?|"
                   r"build(s)? (fine|ok|clean)|verified|done)\b")
NOT_RUN = re.compile(r"(?i)\b(not run|nothing (was )?run|none run|no (tests?|checks?|commands?) (were |was )?run|didn'?t run|"
                     r"did not run|could ?n[o']t (run|be run)|cannot run|can'?t run|unable to run|no tests?( exist| in)|"
                     r"not (be )?(checked|verified|tested)|untested)\b")
BUG = re.compile(r"(?i)\b(bug|error|exception|traceback|stack ?trace|crash\w*|fail(s|ed|ing|ure)?|broken|not working|"
                 r"doesn'?t work|regression|flaky|wrong (result|value|output)|500|segfault|panic)\b")
CHANGE = re.compile(r"(?i)\b(add|implement|build|create|make|support|change|refactor|rewrite|feature|new)\b")


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def on() -> bool:
    return bool(_set("dev_superpowers", True))


def skills() -> dict[str, dict[str, str]]:
    """Every built-in skill: {name: {description, when, body}}."""
    if _CACHE:
        return _CACHE
    for f in sorted(DIR.glob("*.md")):
        txt = f.read_text("utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
        if not m:
            continue
        head = dict(re.findall(r"(?m)^(\w+):\s*(.*)$", m.group(1)))
        name = head.get("name") or f.stem
        _CACHE[name] = {"description": head.get("description", ""), "when": head.get("when", ""), "body": m.group(2).strip()}
    return _CACHE


def get(name: str) -> dict[str, str] | None:
    n = str(name or "").strip().lower()
    n = n.split(":", 1)[1] if n.startswith("superpowers:") else n
    return skills().get(n)


RULE = """HOOLA CODE'S SKILLS """ + CREDIT + """ - how to work, by kind of work. Before you act on her message (before
exploring, before a clarifying question): if a skill below fits even a little, read it whole with the skill tool
(name=superpowers:<name>) and follow it; say in your first sentence "Using <skill> to <purpose>". Process skills come
first (systematic-debugging before any fix, brainstorming before building something whose shape is still open), then the
rest. A skill already given in this session (inside <skill name=...>) is the current text - follow it, do not re-read.
Her words and the repo's own rules come before a skill; a trivial one-line change needs judgment, not ceremony."""


def system_block() -> str:
    if not on():
        return ""
    rows = [f"- superpowers:{k}: {v['description']}" for k, v in skills().items()]
    return RULE + "\n" + "\n".join(rows)


def _one(name: str) -> str:
    sk = get(name)
    return f'<skill name="superpowers:{name}" given="by Hoola for this kind of work">\n{sk["body"]}\n</skill>' if sk else ""


def command(words: str) -> str:
    """Her /brainstorm, /write-plan, /execute-plan: the skill it loads, '' otherwise."""
    m = re.match(r"^\s*/(brainstorm|write-plan|execute-plan)\b", words or "", re.I)
    if not m:
        return ""
    return {"brainstorm": "brainstorming", "write-plan": "writing-plans", "execute-plan": "execute"}[m.group(1).lower()]


def pick(kind: str, words: str, follow_up: str = "") -> list[str]:
    """The process skills this round should carry, in the order to follow them."""
    words = words or ""
    cmd = command(words)
    if cmd == "execute":
        try:
            from . import subagent as SA
            return ["subagent-driven-development" if SA.on() else "executing-plans", "verification-before-completion"]
        except Exception:  # noqa: BLE001
            return ["executing-plans", "verification-before-completion"]
    if cmd:
        return [cmd]
    if "<pr_review_comments>" in (follow_up or "") or re.search(r"(?i)\breview (comments?|feedback)\b", words):
        return ["receiving-code-review", "verification-before-completion"]
    kind = str(kind or "")
    if kind in ("explain", "docs") or re.match(r"^\s*/(security-review|ponytail-|review\b)", words):
        return []
    out = []
    if kind == "fix" or BUG.search(words):
        out.append("systematic-debugging")
    if kind in ("fix", "write", "feature", "tests") or CHANGE.search(words) or out:
        out.append("test-driven-development")
    if out:
        out.append("verification-before-completion")
    return out


def auto_block(t: Any, words: str, follow_up: str, ses: Any, emit: Any) -> str:
    """The full text of the skills picked for this round that this session has not been given yet."""
    if not on():
        return ""
    given = set((getattr(ses, "meta", {}) or {}).get("sp_given") or [])
    names = [n for n in pick(getattr(t, "kind", ""), words, follow_up) if get(n)]
    cmd = command(words)
    new = [n for n in names if n not in given or (cmd and n == names[0])]   # her command always loads its skill again
    if not new:
        return ""
    budget, parts = int(_set("dev_superpowers_chars", 9000) or 9000), []
    for n in new:
        txt = _one(n)
        if parts and sum(len(p) for p in parts) + len(txt) > budget:
            break
        parts.append(txt)
        given.add(n)
        try:
            emit({"k": "skill", "name": n, "auto": not cmd})
        except Exception:  # noqa: BLE001
            pass
    ses.meta["sp_given"] = sorted(given)
    ses.save_meta()
    lead = (f"<her_command>/{words.strip().split()[0][1:]}</her_command>\nShe asked for this way of working: follow the "
            "skill below step by step.\n" if cmd else "")
    return lead + "\n".join(parts)


# ---------------------------------------------------------------- the two iron laws, checked in code
class Tracker:
    """Per round: code edits, test / build runs and failed fix attempts (kept on the Tools object)."""

    def __init__(self) -> None:
        self.code_edits = 0              # edits to code files (not docs) this round
        self.fix_edits = 0               # edits outside the tests (a fix attempt)
        self.last_ok_at = -1             # code_edits when a test / build command last passed
        self.fail_mark = 0               # fix_edits at the last failing run
        self.failed_fixes = 0
        self.told = False
        self.ran = 0

    def edit(self, path: str) -> None:
        p = str(path or "")
        if not p or DOC_PATH.search(p):
            return
        self.code_edits += 1
        if not TEST_PATH.search(p):
            self.fix_edits += 1

    def bash(self, cmd: str, rc: Any) -> str:
        """After a bash run: a note for the model when the 3-fix rule is reached, else ''."""
        if not TEST_CMD.search(cmd or "") or rc is None:
            return ""
        self.ran += 1
        if rc == 0:
            self.last_ok_at, self.failed_fixes, self.told = self.code_edits, 0, False
            return ""
        if self.fix_edits > self.fail_mark:          # a fix was tried since the last failing run, and it still fails
            self.failed_fixes += 1
        self.fail_mark = self.fix_edits
        limit = int(_set("dev_superpowers_fix_limit", 3) or 3)
        if self.failed_fixes >= limit and not self.told:
            self.told = True
            return (f"\n\n[{self.failed_fixes} fixes in a row have not made this pass " + CREDIT + ". STOP fixing. Per "
                    "systematic-debugging: go back to the root cause - read the whole error again, trace where the bad "
                    "value comes from, compare with code that works. Each fix showing a new problem elsewhere means the "
                    "approach is wrong, not the line. If you cannot find the cause, tell her what you found and tried "
                    "and ask her ONE question in done; do not try a fourth fix without that.]")
        return ""

    def unproven_claim(self, finish: dict[str, Any]) -> bool:
        """done says passing / fixed / works, code changed since the last passing test or build run, and it does not
        say the check could not be run."""
        if self.code_edits == 0 or self.last_ok_at >= self.code_edits:
            return False
        said = f"{finish.get('explain') or ''} {finish.get('test_plan') or ''}"
        if NOT_RUN.search(said) or str(finish.get("explain") or "").rstrip().endswith("?"):
            return False
        return bool(CLAIM.search(said))


def proof_text(tr: Tracker) -> str:
    why = ("you never ran a test or build command that passed" if tr.last_ok_at < 0 else
           "you changed code after the last test or build run that passed")
    return ("Not finished yet " + CREDIT + " - verification before completion: your answer says it works / passes, but "
            + why + ". Run the proving command now (the tests for what you changed, and the build or linter the repo "
            "uses), read the whole output, and put the command and its result in test_plan. If it cannot run in the box, "
            "say so plainly instead of claiming it passes. Then call done again.")


def hidden_copies(names: list[str]) -> set[str]:
    """Her chat-desk copies of the older Superpowers pack (sp-<name>) that the built-in skills replace in Hoola Code."""
    built = set(skills())
    return {n for n in names if n.startswith("sp-") and (n[3:] in built or n[3:].replace("finishing-a-development-branch",
                                                                                            "finishing-a-branch") in built
                                                          or n[3:] == "using-git-worktrees" or n[3:] == "using-superpowers")}
