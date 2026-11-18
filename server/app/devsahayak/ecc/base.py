"""v0.794 ECC AGENTS - the shape of one adapted agent (shared by every part file of the catalogue).

Every agent here is TEXT adapted (condensed and rewritten for Hoola Code's tools, locked box and safety rules) from the
MIT-licensed agent files of ECC by Affaan Mustafa (github.com/affaan-m/ECC, v2.2.3, commit d2ef268). No ECC code runs
inside Hoola. Credit: THIRD_PARTY_NOTICES.md."""
from __future__ import annotations

from typing import Any

# What an agent may touch inside a Hoola Code session:
#   read = read / glob / grep / ls only (it cannot change anything and cannot run commands)
#   run  = read + bash in the locked box (tests, linters, builds - no internet), still no file changes
#   edit = run + edit / multi_edit / write (the same guards as the main coder: no secrets, no links, no workflows)
TOOL_LEVELS = ("read", "run", "edit")
GROUPS = ("review", "fix", "build", "plan", "explore", "quality", "domain")   # build = v0.814 implementers (The Agency)


def A(name: str, title: str, group: str, tools: str, when: str, prompt: str,
      langs: tuple[str, ...] = (), files: str = "", words: str = "", ecc: str = "") -> dict[str, Any]:
    """One catalogue entry.
    name   ECC's own agent name (kebab-case), the id the coder uses: agent(type="react-reviewer", ...)
    title  short English name for her page ("React reviewer")
    group  one of GROUPS
    tools  one of TOOL_LEVELS
    when   one line: when the coder should hand work to it (shown to the coder in its agent list)
    prompt the adapted instructions (plain English, 600-2,600 characters)
    langs  language keys it serves (python, js, react, vue, dart, kotlin, java, go, rust, swift, cpp, csharp, fsharp,
           php, ruby, sql, perl, arkts) - used to suggest the right reviewer / fixer for a repo or a failure log
    files  a regular expression over changed file paths that makes it relevant ('' = none)
    words  a regular expression over her request that makes it relevant ('' = none)
    ecc    the ECC file it came from (defaults to agents/<name>.md)"""
    assert group in GROUPS, group
    assert tools in TOOL_LEVELS, tools
    return {"name": name, "title": title, "group": group, "tools": tools, "when": " ".join(when.split()),
            "prompt": prompt.strip(), "langs": tuple(langs), "files": files, "words": words,
            "ecc": ecc or f"agents/{name}.md"}
