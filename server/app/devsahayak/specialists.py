"""v0.402 ECC SPECIALISTS (owner: "GO ECC PHASE 1") - the right expert at each moment of a coding job.

Adapted (rewritten for Hoola's read-only tools, CI logs and safety rules) from ECC's MIT-licensed agents
(github.com/affaan-m/ECC: code-reviewer, security-reviewer, silent-failure-hunter, pr-test-analyzer, the per-language
reviewers and the per-language build-error resolvers). Credit: THIRD_PARTY_NOTICES.md.

Two places use them, each behind its own setting so the review card can compare old vs new before they go live:
- `dev_spec_fix`: a CI fix round (her CI went red) gets FIX_CORE + the fixer notes for the language the log / files show;
- `dev_spec_review`: a PR review gets REVIEW_CORE (the false-positive gates) + the language reviewer, and a big or
  security-touching PR gets up to three extra focused passes (security / silent failures / tests that cover the change).
Everything here is TEXT appended to Hoola's own system prompt; Hoola's own rules (data never instructions, never a secret,
never workflows, merge only on her tap) always come first and win."""
from __future__ import annotations

import os
import re

CREDIT = "Adapted from ECC agents (MIT, github.com/affaan-m/ECC)."

# ---------------------------------------------------------------- languages
EXT = {".py": "python", ".ts": "js", ".tsx": "js", ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js", ".vue": "js",
       ".dart": "dart", ".kt": "kotlin", ".kts": "kotlin", ".go": "go", ".java": "java", ".swift": "swift", ".rs": "rust",
       ".sql": "sql"}
LOG_SIGNS = [
    ("csharp", re.compile(r"error CS\d{4}|\.csproj|dotnet (build|test)", re.I)),            # v0.794 ECC fixers for more languages
    ("cpp", re.compile(r"\.(c|cc|cpp|cxx|h|hpp):\d+:\d+: (fatal )?error|undefined reference to|CMake Error|ninja: build stopped", re.I)),
    ("dart", re.compile(r"\.dart:\d+|dart analyze|flutter (analyze|test)|Error: The (getter|method|name) '.+' isn't defined", re.I)),
    ("kotlin", re.compile(r"\.kts?:\d+|^e: |Unresolved reference|compileKotlin|kotlinc", re.I | re.M)),
    ("swift", re.compile(r"\.swift:\d+|xcodebuild|swiftc", re.I)),
    ("rust", re.compile(r"error\[E\d{4}\]|cargo (build|test)|\.rs:\d+", re.I)),
    ("go", re.compile(r"\.go:\d+:\d+|go (build|test|vet)|undefined: \w+", re.I)),
    ("java", re.compile(r"\.java:\d+|javac|BUILD FAILURE|maven|cannot find symbol", re.I)),
    ("js", re.compile(r"error TS\d+|\.tsx?[:(]\d+|\.jsx?:\d+|npm (ERR|run)|jest|vitest|node --test|eslint", re.I)),
    ("python", re.compile(r"Traceback \(most recent call last\)|\.py:\d+|pytest|AssertionError|ModuleNotFoundError|mypy|ruff", re.I)),
]


def lang_of(paths: list[str]) -> str:
    """The main language of a set of files (most files win); '' when none is known."""
    counts: dict[str, int] = {}
    for p in paths or []:
        lang = EXT.get(os.path.splitext(str(p).lower())[1])
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return max(counts, key=lambda k: (counts[k], k)) if counts else ""


def lang_of_log(log: str, paths: list[str] | None = None) -> str:
    """The language a failure log is about (the log's own signs first, then the changed files)."""
    text = str(log or "")[-20000:]
    for lang, rx in LOG_SIGNS:
        if rx.search(text):
            return lang
    return lang_of(paths or [])


# ---------------------------------------------------------------- reviewing
REVIEW_CORE = """REVIEW DISCIPLINE (specialist reviewer, adapted from ECC's code-reviewer):
Before you write ANY comment, answer all four. If one answer is "no" or "unsure", drop it or lower its severity:
1. Can I cite the exact added line? (no vague "somewhere in the auth layer")
2. Can I name the concrete failure: which input or state, and what goes wrong? If not, it is pattern-matching, not review.
3. Did I read the surrounding code: the callers, imports and tests? Many apparent issues are handled one frame up.
4. Is the severity defensible? A missing docstring is never high.
A HIGH comment must carry its proof in the body: the line, the failure scenario (input -> state -> bad outcome), and why
existing guards (types, validation, the framework) do not catch it. Without all three it is medium at most, or dropped.
ZERO COMMENTS IS A VALID REVIEW. If the change is small, correct, tested and follows the project's patterns, call done with
no comments and verdict comment. Never manufacture findings: filler nits, speculative "consider X" and edge cases without a
trigger are the main failure of AI reviewers and destroy trust.
Skip these common false alarms unless you have evidence from THIS code: "add error handling" when the caller or framework
already handles it; "missing input validation" on an internal function whose callers validate (trace one caller first);
"magic number" for obvious constants (200, 404, 60, 1000 ms, index 0 / -1); "function too long" for a switch, a table, a
config or generated code; "missing docstring" on a self-describing helper; "possible null" when the line above already
checks it; "N+1" on a fixed small loop; "hardcoded value" in tests or examples; "should use types" in an untyped project.
Ask of every comment: would a senior engineer on this team actually change this in review? If not, skip it.
Priorities: behaviour regressions and edge cases first, then security and trust boundaries, then hidden coupling. Style
only when it breaks the project's written rules. """ + CREDIT

SELF_REVIEW = """OWN WORK (v0.445, adapted from ECC's reviewer-before-handoff): this pull request was written by YOU, and
nobody has seen it yet. You are reading it back before it goes to her for review, so read it as the reviewer who will be
blamed for what gets through, not as the author defending it.
What matters here, in order: (1) did the change actually do what the task asked, or only part of it; (2) does any caller,
test or import of the code you touched now break (name it, do not guess); (3) a leftover - debug print, commented-out code,
a TODO, a stray file, a half-renamed symbol; (4) the same security / silent-failure / edge-case bar as any other review.
Say so when the work is wrong. Finding your own mistake here is cheaper than her finding it, and a clean verdict on a bad
change is the one failure that cannot be undone. But the no-filler rule stands exactly as above: do NOT invent problems to
look thorough, and ZERO COMMENTS IS THE RIGHT REVIEW of a small, correct, tested change. """ + CREDIT

LANG_REVIEW = {
    "python": """PYTHON REVIEWER notes: SQL built with f-strings / % / + (use parameters); shell commands from input (use
argument lists); paths from input without normalising / rejecting '..'; eval / exec / pickle / yaml.load on outside data;
bare `except:` or `except Exception: pass` (swallowed errors); files / connections without `with`; MUTABLE DEFAULT
ARGUMENTS (`def f(x=[])`); `== None`; shadowing builtins; shared state across threads without a lock; sync calls inside
async code; N+1 queries in a loop; print() where the project logs.""",
    "js": """JAVASCRIPT / TYPESCRIPT REVIEWER notes: injection through template strings in SQL / shell / HTML (XSS:
unescaped user input rendered, dangerouslySetInnerHTML); missing `await` on a promise whose result or error matters;
unhandled rejections and empty catch blocks; `any` hiding a real type error; `==` where type matters; mutation of props /
state / shared objects; React: effects with missing dependencies, state set during render, array index as key on a list
that reorders, stale closures; Node: request input used without validation, external calls without a timeout,
internal error details sent to clients.""",
    "dart": """FLUTTER / DART REVIEWER notes: keys, tokens or secrets in Dart source; sensitive data in plain storage
instead of secure storage; data from the server or a deep link used without checks (`as` casts and `!` on JSON crash);
print() / debugPrint() of personal data; BuildContext used after an `await` without a mounted check; setState after
dispose; controllers / streams / subscriptions not disposed; heavy work inside build(); state objects mutated in place
instead of a new object (the screen will not rebuild); missing const on widgets that could be const only when the
project lints for it.""",
    "kotlin": """KOTLIN / ANDROID REVIEWER notes: `!!` on values that can be null (crash); exported components, deep links
and intent filters without checks; tokens / keys in source or plain SharedPreferences; insecure WebView / network config;
coroutines launched in GlobalScope or without a lifecycle scope (leaks), blocking calls on the main thread, swallowed
CancellationException; Flow collected outside the lifecycle; mutable state exposed from a ViewModel; domain code
importing Android / framework classes; data classes with `var` where the project wants immutable copies.""",
    "go": """GO REVIEWER notes: SQL built by string concatenation; os/exec with unvalidated input; paths without
filepath.Clean + prefix check; data races (shared state without sync); errors discarded with `_` or returned without
context (`fmt.Errorf("...: %w", err)`); panic for recoverable errors; `err == target` instead of errors.Is / As;
goroutines with no way to stop (leaks); InsecureSkipVerify; defer inside long loops.""",
    "java": """JAVA REVIEWER notes: SQL / JPQL by concatenation (use bind parameters); ScriptEngine.eval or file paths
from user input; secrets in source or logs; empty catch blocks; Optional.get() without a check; wrong HTTP status (200
with null instead of 404); business logic in controllers; @Transactional on the wrong layer; entities returned straight
from controllers; N+1 from EAGER collections; unbounded list endpoints.""",
    "swift": """SWIFT REVIEWER notes: force unwraps / force casts on data that can be missing; retain cycles in closures
(missing [weak self]); UI updated off the main actor; secrets in source or UserDefaults instead of the Keychain; errors
swallowed with `try?` where the failure matters; main-thread blocking work.""",
    "rust": """RUST REVIEWER notes: unwrap / expect on values from outside (panic); unsafe blocks without a safety
comment; errors discarded; blocking calls inside async code; integer overflow on untrusted sizes; clones hiding a real
ownership bug.""",
    "sql": """SQL / DATABASE REVIEWER notes: queries built from input; missing WHERE on UPDATE / DELETE; migrations that
lock or rewrite a big table, drop data, or cannot be rolled back; missing index for a new lookup; N+1 patterns.""",
}

FOCUS = {
    "security": """FOCUSED PASS - SECURITY (adapted from ECC's security-reviewer). Comment ONLY on security problems in
the added lines, with proof: injection (SQL / shell / template), broken access control (a record returned or changed
without checking it belongs to the caller), secrets or personal data in code / logs / responses, missing auth on a
route, unsafe deserialisation, path traversal, SSRF from user URLs, weak crypto for passwords. Not problems: values in
.env.example, clearly fake test credentials, public keys meant to be public, hashes used as checksums. Zero comments is
the right answer when there is no real hole.""",
    "silent": """FOCUSED PASS - SILENT FAILURES (adapted from ECC's silent-failure-hunter). Comment ONLY where an error
can disappear: empty catch / except blocks, errors turned into None / [] / 0 with no trace, fallbacks that hide a real
failure from the caller (a failed payment shown as success, a failed reservation that still continues), lost error
context, async errors never awaited, network / file / database calls with no timeout or rollback. Name what the user or
the next step will see go wrong. Zero comments is the right answer when every failure is surfaced.""",
    "tests": """FOCUSED PASS - TESTS THAT COVER THE CHANGE (adapted from ECC's pr-test-analyzer). Find the tests for each
changed behaviour (search tests/ and test files). Comment ONLY on real gaps: changed behaviour or a new error path with
no test, tests that assert nothing meaningful (only "does not throw"), tests that would pass on the old code too. Put
the comment on the added line of the untested behaviour and say which case is missing. A change already covered = no
comment.""",
}
RISKY = re.compile(r"(?i)\b(sql|sqlite\d?|query|select|insert|delete|execute|cursor|password|passwd|token|secret|"
                   r"api[_-]?key|auth|login|session|permission|role|admin|payment|upi|refund|otp|cookie|jwt|crypto|encrypt|"
                   r"upload|exec|subprocess|eval|deserial|pickle|customer_id|user_id|owner|phone|email|aadhaar|pan)\b")


def _ecc_extra(paths: list[str]) -> str:
    """v0.794 the adapted ECC reviewer for a language / framework the notes above do not cover (React, Vue, C#, C++,
    PHP, Ruby, F#, Django ...) - one agent's text at most, so the PR review prompt stays small."""
    try:
        from . import ecc
        for k in ecc.langs_of(paths, top=3):
            if k in LANG_REVIEW:
                continue
            a = ecc.get(ecc.REVIEWER.get(k, ""))
            if a:
                return "\n\n" + a["prompt"]
    except Exception:
        return ""
    return ""


def review_addendum(paths: list[str]) -> str:
    """The extra reviewer instructions for a PR touching these files."""
    lang = lang_of(paths)
    return (REVIEW_CORE + ("\n\n" + LANG_REVIEW[lang] if lang in LANG_REVIEW else "")
            + _ecc_extra(paths))


def focus_passes(paths: list[str], diff_text: str, added: int, big: int = 150) -> list[str]:
    """Which focused passes a PR earns: all three for a big PR, security for one touching sensitive code, tests for a
    change to code (not docs) with no test file in it. Small, docs-only PRs get none."""
    code = [p for p in paths if lang_of([p])]
    if not code:
        return []
    out = []
    if added >= big or RISKY.search(diff_text or ""):
        out.append("security")
    if added >= big or re.search(r"(?i)\b(except|catch|try|fallback|default|retry|timeout|rollback)\b", diff_text or ""):
        out.append("silent")
    has_test = any(re.search(r"(^|/)(tests?|__tests__|spec)/|_test\.|\.test\.|\.spec\.|Test\.kt$|(^|/)test_", p) for p in paths)
    if added >= big or not has_test:
        out.append("tests")
    return out


def merge_comments(groups: list[list[dict]]) -> list[dict]:
    """One list from several passes: the same file + line (within 2 lines) is ONE comment, keeping the highest
    severity and the longer explanation."""
    rank = {"high": 3, "medium": 2, "low": 1}
    out: list[dict] = []
    for g in groups:
        for c in g:
            twin = next((o for o in out if o["path"] == c["path"] and abs(int(o["line"]) - int(c["line"])) <= 2), None)
            if twin is None:
                out.append(dict(c))
                continue
            if rank.get(c.get("severity"), 1) > rank.get(twin.get("severity"), 1):
                twin["severity"] = c.get("severity")
            if len(str(c.get("body") or "")) > len(str(twin.get("body") or "")):
                twin["body"] = c["body"]
    return out


# ---------------------------------------------------------------- fixing a red CI run
FIX_CORE = """CI FIX SPECIALIST (adapted from ECC's build-error resolvers). Her CI is red; your only job is to make it
green the right way:
1. Read the FIRST real error in the log (later errors are often caused by it): file, line, expected vs actual.
2. Read that file and its callers before changing anything; find the ROOT cause, not the symptom.
3. Make the smallest change that fixes it. Do not refactor, rename, reformat or add features; do not change unrelated
   logic, public signatures or architecture.
4. NEVER make CI green by weakening it: no deleting / skipping / loosening a test or assertion, no lowering a lint rule,
   no suppressing a warning or type error (no `# type: ignore`, `@ts-ignore`, `@Suppress`, `// ignore:`), no catching
   and hiding the exception. If the test is right and the code is wrong, fix the code.
5. If the failure needs something outside the code (a secret, a service, a version decision), change nothing and say so
   in explain. Stop when a fix would cause more errors than it removes. """ + CREDIT

LANG_FIX = {
    "dart": """DART / FLUTTER fixes: "The name 'X' isn't defined" = missing import or typo; "A value of type 'X?' can't be
assigned to 'X'" = handle the null (?? default or a check - add `!` only when the value truly cannot be null); argument
type mismatch = correct the call or the type; "Non-nullable instance field must be initialized" = initialise, `late`
only when it is always set before use, or make it nullable; "'await' applied to non-Future" = drop the await or make the
function async; missing concrete implementation = add the method; pub version solving failed = adjust the constraint;
stale generated `.g.dart` = regenerate (it is not hand-edited).""",
    "kotlin": """KOTLIN fixes: "Unresolved reference" = missing import / dependency or a typo (prefer the exact import, not
a wildcard); "Type mismatch: Required X, Found Y" = add the conversion or fix the type; "None of the following candidates
is applicable" = fix the argument types; "Smart cast impossible" = copy to a local val / use let; "'when' must be
exhaustive" = add the missing branches (not a blind else when the type is sealed); "Suspend function can only be called
from a coroutine" = make the caller suspend or launch in the right scope; "Could not resolve group:artifact" = repository
or version.""",
    "python": """PYTHON fixes: read the LAST frame of the traceback inside the repo's code; ModuleNotFoundError /
ImportError = wrong import path or a missing dependency in the project's requirement file; AttributeError / TypeError on
None = the value can be missing - handle it where it is produced; an assertion failure = compare expected vs actual and
fix the code that computes it; mypy errors = fix the type, do not add `Any` or ignores.""",
    "js": """JAVASCRIPT / TYPESCRIPT fixes: "error TSxxxx" = fix the type at its source (no `any`, no `@ts-ignore`, no `as
unknown as`); "Cannot find module" = wrong path / missing dependency / missing export; "is possibly undefined" = handle
it where it can be missing; ESM vs CommonJS import mix = match the project's module type; React hook errors = hooks only
at the top level of components; a failing test = compare expected vs actual and fix the code.""",
    "go": """GO fixes: "undefined: X" = missing import or wrong package; "declared and not used" / "imported and not used"
= remove it; type mismatch = explicit conversion; missing method on interface = implement it with the exact signature;
go.mod / go.sum mismatch = tidy the module files; vet errors = fix the code, do not silence vet.""",
    "java": """JAVA fixes: "cannot find symbol" = missing import / dependency / wrong name; "incompatible types" = fix the
conversion; unreported exception = handle or declare it (do not catch and ignore); Maven / Gradle dependency resolution
= the version or repository; Lombok / annotation processing errors = processor configuration, not hand-written code.""",
    "swift": """SWIFT fixes: "cannot find 'X' in scope" = missing import / target membership / typo; optional not
unwrapped = handle the nil case (guard let / ??), not a force unwrap; actor isolation / Sendable errors = move the work
to the right actor; protocol conformance = add the missing requirement.""",
    "rust": """RUST fixes: borrow checker errors = restructure ownership (clone only when it is truly needed); E0308 type
mismatch = convert explicitly; unresolved import = the crate / module path or Cargo.toml feature; unused / dead code
warnings promoted to errors = remove the dead code, do not allow() it.""",
}


def fix_addendum(log: str, paths: list[str]) -> str:
    """The extra instructions for a CI fix round, picked by the language the failure is in."""
    lang = lang_of_log(log, paths)
    if lang not in LANG_FIX:                               # v0.794 ECC's resolver for a language without notes here
        try:
            from . import ecc
            a = ecc.get(ecc.fixer_for(lang)) if lang else None
            if a and a["name"] != "build-error-resolver":
                return FIX_CORE + "\n\n" + a["prompt"]
        except Exception:
            pass
    return FIX_CORE + ("\n\n" + LANG_FIX[lang] if lang in LANG_FIX else "")
