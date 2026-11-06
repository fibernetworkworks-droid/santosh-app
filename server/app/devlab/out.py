"""v0.456 the lab's output contract: what the model is shown of a command's output, and what it can ask for later.

Measured contract we are copying and correcting (code.claude.com/docs/en/tools-reference): Claude Code streams a
command's output to a file, returns ~30,000 characters inline when the command SUCCEEDS, and only a ~10,000-character
head-and-tail excerpt WITH NO LOG PATH when it FAILS. Our research flagged that as backwards: the failing run is the
one whose full output you want. So here:

  success -> the HEAD (what it did), small, because nobody debugs a pass;
  failure -> the TAIL (the traceback, the assertion, the compiler's last word), larger, PLUS the log path and the real
             byte count, so the model can grep the rest instead of guessing.

A log never leaves the server and is deleted with its run folder."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

PASS_HEAD = 4_000          # characters of a SUCCESSFUL run shown inline
FAIL_TAIL = 24_000         # characters of a FAILED run shown inline (the end of the output)
FAIL_HEAD = 2_000          # ... plus this much of its start (the command line, the collection errors)
GREP_MAX = 8_000           # characters one grep_log answer may return
GREP_LINES = 400           # ... and lines


def shape(text: str, rc: int, log_path: str = "", secs: float = 0.0, timed_out: bool = False) -> dict[str, Any]:
    """The tool result for one run. `shown` is what the model reads; `bytes` is the truth about what was cut."""
    text = text or ""
    n = len(text)
    ok = rc == 0 and not timed_out
    if ok:
        shown = text[:PASS_HEAD]
        cut = n - len(shown)
        if cut > 0:
            shown += f"\n… [{cut} more characters; it passed, so the rest is not shown]"
    elif n <= FAIL_HEAD + FAIL_TAIL:
        shown = text
        cut = 0
    else:
        cut = n - FAIL_HEAD - FAIL_TAIL
        shown = (text[:FAIL_HEAD] + f"\n… [{cut} characters cut from the middle - the WHOLE output is in the log file "
                 f"below; grep it for a test name, a file or an error]\n…\n" + text[-FAIL_TAIL:])
    return {"ok": ok, "exit_code": rc, "timed_out": timed_out, "seconds": round(float(secs), 1),
            "bytes": n, "cut": max(0, cut), "log": log_path, "shown": shown}


def say(res: dict[str, Any], cmd: str) -> str:
    """One line a human (and the model) reads before the output itself."""
    if res.get("timed_out"):
        return f"`{cmd}` {res['seconds']}s ke baad bhi chal raha tha, isliye roka gaya (time limit)."
    if res.get("ok"):
        return f"`{cmd}` PASS ({res['seconds']}s)."
    return f"`{cmd}` FAIL - exit code {res.get('exit_code')} ({res['seconds']}s)."


def grep_log(log_path: str, pattern: str, before: int = 2, after: int = 6, limit: int = GREP_LINES) -> str:
    """Ask a run's own log a second question. Plain substring, or a regex when it compiles; never runs a shell."""
    p = Path(log_path or "")
    if not p.is_file():
        return "That run's log is gone (a log lives only as long as its run folder). Run the check again."
    try:
        text = p.read_text("utf-8", errors="replace")
    except OSError as e:
        return f"log not readable: {e}"
    lines = text.splitlines()
    try:
        rx = re.compile(pattern, re.I)
        hit = lambda s: bool(rx.search(s))          # noqa: E731
    except re.error:
        low = (pattern or "").lower()
        hit = lambda s: low in s.lower()            # noqa: E731
    if not (pattern or "").strip():
        return "Give a pattern to look for (a test name, a file, 'Error', 'assert')."
    out, shown, last = [], 0, -1
    for i, line in enumerate(lines):
        if not hit(line):
            continue
        lo, hi = max(0, i - before), min(len(lines), i + after + 1)
        if lo <= last:
            lo = last + 1
        for j in range(lo, hi):
            out.append(f"{j + 1:>6}  {lines[j]}")
            shown += 1
            if shown >= limit:
                break
        last = hi - 1
        out.append("  --")
        if shown >= limit:
            out.append(f"… more matches not shown (limit {limit} lines)")
            break
    if not out:
        return f"No line of the log matches {pattern!r}. The log has {len(lines)} lines, {len(text)} characters."
    return "\n".join(out)[:GREP_MAX]


def tail(log_path: str, lines: int = 200) -> str:
    p = Path(log_path or "")
    if not p.is_file():
        return "log gone"
    try:
        body = p.read_text("utf-8", errors="replace").splitlines()
    except OSError as e:
        return f"log not readable: {e}"
    return "\n".join(body[-max(1, min(lines, 2000)):])[:GREP_MAX]


def write_log(folder: str, name: str, text: str) -> str:
    """One log file per run, inside the run's own folder."""
    try:
        d = Path(folder)
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', name)[:60] or 'run'}.log"
        p.write_text(text, "utf-8")
        os.chmod(p, 0o600)
        return str(p)
    except OSError:
        return ""
