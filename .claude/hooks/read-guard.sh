#!/bin/bash
# Hoola read guard (v0.455) - a PreToolUse hook on Read.
#
# WHY. CLAUDE.md has said since v0.231 that this file "is loaded into EVERY Claude session, so it must stay SHORT
# (target < 30 KB)", because the version history once sat inside it at 1.16 MB (~477k tokens = half the context
# window) and "every session started 'context full'". The history moved to docs/HISTORY.md with the rule "Do NOT read
# it whole. Search it." - but that rule was a SENTENCE, enforced by nothing. docs/HISTORY.md is now 1.9 MB, larger
# than the file that caused the original problem, and one careless whole-file read still ends a session.
#
# WHAT. A whole-file Read of a watched Markdown doc over the size bar is refused, and the answer is the doc's own
# headings WITH THEIR LINE NUMBERS, so the retry reads just the section it wanted. Idea from Claude Code Game Studios
# (MIT, release 1.2.0, `validate-read.sh`); this is our own implementation, and the headings reply differs because
# docs/HISTORY.md has 487 headings - printing them all would itself be the waste we are preventing.
#
# NEVER GETS IN THE WAY - every one of these passes straight through:
#   * a ranged read (offset or limit set) - the thing we are asking for;
#   * allow_large: true - the deliberate "I really do want all of it";
#   * any file under the bar, any non-Markdown file, any tool that is not Read;
#   * anything the guard cannot work out (no parser, odd payload, unreadable file) - it FAILS OPEN, never blocks.
#
# Switches: HOOLA_READ_GUARD=off turns it off; HOOLA_READ_GUARD_KB sets the bar (default 40).
#
# Exit: 2 = refused, and stderr is what Claude is told. 0 = everything else.

[ "${HOOLA_READ_GUARD:-on}" = "off" ] && exit 0

INPUT=$(cat)

# ---------------------------------------------------------------- fast path (builtins only; runs on EVERY Read)
# Most reads are of code, not of a watched doc. Leave before any JSON parsing or process start: a .md has to be in
# the payload at all, and so does a file_path.
case "$INPUT" in
  *'"file_path"'*) ;;
  *) exit 0 ;;
esac
case "$INPUT" in
  *.md*|*.MD*) ;;
  *) exit 0 ;;
esac

# ---------------------------------------------------------------- the payload
_field() {                                    # _field <key> -> value, or empty
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$INPUT" | jq -r --arg k "$1" '(.tool_input[$k] // empty) | tostring' 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$INPUT" | python3 -I -c '
import json,sys
try:
    v=(json.load(sys.stdin).get("tool_input") or {}).get(sys.argv[1])
except Exception:
    v=None
print("" if v is None else v)' "$1" 2>/dev/null
  fi
}

TOOL=""
if command -v jq >/dev/null 2>&1; then
  TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
fi
[ -n "$TOOL" ] && [ "$TOOL" != "Read" ] && exit 0

FILE=$(_field file_path)
[ -n "$FILE" ] || exit 0                      # could not parse: fail open

# a ranged read is exactly what we want people to do
[ -n "$(_field offset)" ] && exit 0
[ -n "$(_field limit)" ] && exit 0
case "$(_field allow_large)" in true|True|1) exit 0 ;; esac

# ---------------------------------------------------------------- is it watched, and is it big?
# Watched: CLAUDE.md anywhere, and any .md under docs/. The size bar does the rest, so a new big doc is covered
# the day it appears and a small one is never touched.
case "$FILE" in
  *.md|*.MD|*.Md|*.mD) ;;
  *) exit 0 ;;
esac
case "$FILE" in
  */CLAUDE.md|CLAUDE.md|*/docs/*|docs/*) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0                      # a missing file is Read's own error to report

BAR_KB=${HOOLA_READ_GUARD_KB:-40}
case "$BAR_KB" in ''|*[!0-9]*) BAR_KB=40 ;; esac
SIZE=$(wc -c <"$FILE" 2>/dev/null) || exit 0
case "$SIZE" in ''|*[!0-9]*) exit 0 ;; esac
[ "$SIZE" -le $((BAR_KB * 1024)) ] && exit 0

# ---------------------------------------------------------------- refuse, and hand back the map
KB=$((SIZE / 1024))
TOTAL=$(grep -c '^#\{1,3\} ' "$FILE" 2>/dev/null || echo 0)
{
  echo "READ GUARD: $FILE is ${KB} KB. A whole-file read of it can cost most of this session's context, which is the"
  echo "exact failure CLAUDE.md records (the history once sat at 1.16 MB and every session started 'context full')."
  echo
  echo "Read the section you need instead:"
  echo "  Read(\"$FILE\", offset: <line>, limit: 120)"
  echo "  grep -n \"<what you are looking for>\" $FILE     # then read around the line it names"
  echo "  Read(\"$FILE\", allow_large: true)                # if you truly need all ${KB} KB"
  echo
  if [ "${TOTAL:-0}" -le 60 ]; then
    echo "Its headings, by line ($TOTAL):"
    grep -n '^#\{1,3\} ' "$FILE" 2>/dev/null | sed 's/^/  /'
  else
    echo "It has $TOTAL headings - too many to list here (listing them would be the same waste). The LAST 40, by line:"
    grep -n '^#\{1,3\} ' "$FILE" 2>/dev/null | tail -40 | sed 's/^/  /'
    echo
    echo "For the rest: grep -n '^#' $FILE | head -60    (or grep for the version / feature you want)"
  fi
} >&2
exit 2
